(* Le pont entre la bibliothèque et la page web. Un seul objet global, [ardoise], avec trois fonctions :

     ardoise.analyse(mot)                       → { n, fn }       les images des générateurs de F_n
     ardoise.statique(mode, mot)                → image            l'image fixe d'un mode
     ardoise.film(mode, mot, rendu) → string                       le film, image par image ; "" si tout va bien

   mot : tableau d'entiers non nuls (σ_k : k, σ_k⁻¹ : -k). mode : "conforme", "triangulation", "diagramme" ou "rubans" (méandres d'une
   tresse), ou "escargot" ou "bouquet" (films sans tresse : le mot est ignoré, les images ont d'autres champs, voir
   image_escargot et image_bouquet).
   Une image : { lacets : [[x0, y0, x1, y1, …], …], trous : [x, y, …], fixes : [x, y, …], clou : [x, y],
   ecart : nombre } dans un cadre de 800 × 800. [rendu] est appelé avec (image, numéro, total) pour chaque image du
   film. Les échecs (tresse vide, limites, exceptions du calcul) reviennent en texte, jamais en exception JS : le
   Web Worker les affiche. *)

open Js_of_ocaml
open Ardoise
open Geometrie

(* Le message d'une exception, sans les échappements de Printexc (qui écrit les accents en \195\160…). *)
let message = function Invalid_argument m | Failure m -> m | e -> Printexc.to_string e

let marge = 60.
let cote = 800.

(* Limites de la page : au-delà, le conforme n'est pas calculé (l'étude en donne les temps). *)
let max_brins = 8
let max_lettres = 40
let max_brins_conforme = 6
let max_lettres_conforme = 14

let tresse_de_js (mot : float Js.js_array Js.t) =
  let entiers = Array.to_list (Array.map int_of_float (Js.to_array mot)) in
  if List.exists (fun k -> k = 0) entiers then invalid_arg "une lettre nulle";
  Tresses.tresse_de_entiers entiers

let nb_brins tresse = List.fold_left (fun a (l : Tresses.sigma Tresses.lettre) -> max a l.indice) 0 tresse + 1

let verifie_limites ?(conforme = false) tresse =
  if tresse = [] then invalid_arg "mot vide : c'est la tresse nulle, il n'y a rien à dessiner";
  let n = nb_brins tresse and l = List.length tresse in
  if n > max_brins || l > max_lettres then
    invalid_arg (Printf.sprintf "limites de la page : %d brins et %d lettres au plus" max_brins max_lettres);
  if conforme && (n > max_brins_conforme || l > max_lettres_conforme) then
    invalid_arg
      (Printf.sprintf "ce film (conforme ou triangulation) est limité à %d brins et %d lettres" max_brins_conforme max_lettres_conforme)

(* Polyligne ou liste de points → tableau JS plat. *)
let plat points =
  let a = Array.make (2 * Array.length points) 0. in
  Array.iteri (fun k p -> a.(2 * k) <- p.x; a.((2 * k) + 1) <- p.y) points;
  Js.array a

let image ?(decalage = { x = 0.; y = 0. }) ?(fixes = [||]) ?(ecart = 6.) ?(brin = 3.5) lacets trous clou =
  let d = Array.map (fun p -> p +: decalage) in
  Js.Unsafe.obj
    [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.map (fun l -> plat (d l)) lacets))));
       ("trous", Js.Unsafe.inject (plat (d trous)));
       ("fixes", Js.Unsafe.inject (plat (d fixes)));
       ("clou", Js.Unsafe.inject (plat (d [| clou |])));
       ("ecart", Js.Unsafe.inject (Js.number_of_float ecart));
       ("brin", Js.Unsafe.inject (Js.number_of_float brin)) |]

(* --- mots de F_n --- *)

let analyse mot =
  try
    let tresse = tresse_de_js mot in
    let n = if tresse = [] then 2 else nb_brins tresse in
    let images = Tresses.calcule_autofn_de_tresse ~nb_trous:n tresse in
    let mots = Array.map (fun m -> Js.array (Array.of_list (List.map float_of_int (Tresses.entiers_de_mot (m : Tresses.Reduit.t :> Tresses.mot_de_fn))))) images in
    Js.Unsafe.obj [| ("n", Js.Unsafe.inject n); ("fn", Js.Unsafe.inject (Js.array mots)); ("erreur", Js.Unsafe.inject (Js.string "")) |]
  with e ->
    Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

(* --- conforme --- *)

let image_conforme decalage (im : Film_conforme.image) = image ~decalage im.lignes im.trous im.clou

let methode_arcs = function
  | "rubans" -> ((fun t -> Arcs.cree ~ecart_fixes:30. t), true)
  | "diagramme" -> ((fun t -> Arcs.cree_diagramme t), false)
  | m -> invalid_arg ("mode inconnu : " ^ m)

let image_arcs rubans (film : Arcs.t) =
  let pos = film.maillage.Triangulation.Maillage.pos in
  let lacets = List.mapi (fun k _ -> if rubans then Arcs.ruban film k else Arcs.polyligne film k) film.courbes in
  image ~fixes:(Array.map (fun s -> pos.(s)) film.fixes) ~ecart:film.ecart lacets (Array.map (fun s -> pos.(s)) film.voyageurs) { x = -100.; y = -100. }

(* --- la triangulation mobile (lib/film.ml, le film de Dessin.film_triangule sans le maillage gris) --- *)

(* Le trait suit l'écart entre brins : au plus 70 % de cet écart (brins serrés : trait plus fin), comme Dessin.cadre. *)
let image_triangulation (film : Film.t) ecart =
  let brin = Float.min (3. *. film.largeur /. 400.) (Float.max 1. (0.7 *. ecart)) in
  let pos = film.maillage.Triangulation.Maillage.pos in
  image ~brin (Film.polylignes film) (Film.positions_des_trous film) pos.(film.clou)

(* Joue le film en appelant [rendu film ecart numéro] à chaque image (le départ : numéro 0). *)
let joue_triangulation tresse ~sous_pas ~rendu =
  let film = Film.cree ~hauteur:cote ~largeur:cote tresse in
  rendu film film.dispositions.(0).ecart 0;
  let k = ref 0 in
  ignore
    (List.fold_left
       (fun film sigma -> fst (Film.lettre ~sous_pas ~rendu:(fun f e -> incr k; rendu f e !k) film sigma))
       film tresse)

(* Un triangle peut se retourner entre deux sous-pas (sur environ une tresse aléatoire de 12 lettres à 5 brins sur
   quatre, plus de sous-pas n'y change rien) : on essaie 2, 4 puis 8 sous-pas par image, sans rien dessiner, ce qui donne
   aussi le nombre d'images et la dernière image (l'image fixe). *)
let prepare_triangulation tresse =
  let essai sous_pas =
    let derniere = ref None and n = ref 0 in
    try
      joue_triangulation tresse ~sous_pas ~rendu:(fun f e k -> n := k; derniere := Some (f, e));
      Option.map (fun d -> (sous_pas, !n, d)) !derniere
    with Failure _ -> None
  in
  match List.find_map essai [ 2; 4; 8 ] with
  | Some r -> r
  | None -> failwith "la triangulation ne passe pas ce mot (un triangle se retourne) : essaie un autre mot"

let nombre_images_arcs = 60
let nombre_images_conforme = 48

let statique_tresse mode mot =
  try
    let tresse = tresse_de_js mot in
    match Js.to_string mode with
    | "triangulation" ->
        verifie_limites ~conforme:true tresse;
        let _, _, (film, ecart) = prepare_triangulation tresse in
        image_triangulation film ecart
    | "conforme" ->
        verifie_limites tresse;
        image_conforme { x = marge; y = marge } (Film_conforme.image_finale ~hauteur:cote ~largeur:cote ~marge tresse)
    | m ->
        verifie_limites tresse;
        let cree, rubans = methode_arcs m in
        let film = List.fold_left (fun f s -> Arcs.lettre f s) (cree tresse) tresse in
        image_arcs rubans film
  with e -> Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

let film_tresse mode mot rendu =
  try
    let tresse = tresse_de_js mot in
    let appelle im k total = ignore (Js.Unsafe.fun_call rendu [| Js.Unsafe.inject im; Js.Unsafe.inject k; Js.Unsafe.inject total |]) in
    (match Js.to_string mode with
    | "triangulation" ->
        verifie_limites ~conforme:true tresse;
        let sous_pas, total, _ = prepare_triangulation tresse in
        joue_triangulation tresse ~sous_pas ~rendu:(fun f e k -> appelle (image_triangulation f e) k (total + 1));
        Js.string ""
    | "conforme" ->
        verifie_limites ~conforme:true tresse;
        let total = 1 + (nombre_images_conforme * List.length tresse) in
        let k = ref 0 in
        let anomalies =
          Film_conforme.film ~verifie:true ~hauteur:cote ~largeur:cote ~marge
            ~rendu:(fun im -> appelle (image_conforme { x = marge; y = marge } im) !k total; incr k)
            tresse
        in
        if anomalies <> [] then
          Js.string (Printf.sprintf "film fait, mais %d image(s) douteuse(s) (mots ou croisements)" (List.length anomalies))
        else Js.string ""
    | m ->
        verifie_limites tresse;
        let cree, rubans = methode_arcs m in
        let total = 1 + (nombre_images_arcs * List.length tresse) in
        let k = ref 0 in
        let rendu f = appelle (image_arcs rubans f) !k total; incr k in
        let depart = cree tresse in
        rendu depart;
        ignore (List.fold_left (fun f s -> Arcs.lettre ~images:nombre_images_arcs ~rendu f s) depart tresse);
        Js.string "")
  with e -> Js.string (message e)

(* --- l'escargot : un film sans mot de tresse (lib/escargot.ml), 960 × 640, 12 s à 25 images par seconde --- *)

(* Tout ce que le dessin lit dans l'état (Dessin.cadre_escargot) : les polylignes des arcs, le disque de la coquille
   (centre et rayon), les positions des deux yeux, leur facteur d'apparition. *)
let image_escargot (esc : Escargot.t) t =
  let c = Escargot.centre_coquille esc t in
  let rayon =
    Escargot.rayon_anneau esc t +. (((float esc.anneau *. Escargot.tours_faits esc t) +. 1.5) *. esc.ecart)
  in
  let pos = esc.maillage.Triangulation.Maillage.pos in
  let yeux = Array.init 2 (fun j -> pos.(esc.voyageurs.(esc.anneau + 1 + j))) in
  let nombre x = Js.Unsafe.inject (Js.number_of_float x) in
  Js.Unsafe.obj
    [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.init esc.n (fun k -> plat (Escargot.polyligne esc k))))));
       ("coquille", Js.Unsafe.inject (Js.array [| c.x; c.y; rayon |]));
       ("yeux", Js.Unsafe.inject (plat yeux));
       ("apparition", nombre (Escargot.lisse ((t -. 9.) /. 2.)));
       ("ecart", nombre esc.ecart);
       ("e", nombre esc.e);
       ("anneau", Js.Unsafe.inject esc.anneau);
       ("largeur", nombre esc.largeur);
       ("hauteur", nombre esc.hauteur) |]

let images_par_seconde_escargot = 25.
let nombre_images_escargot = 300

(* [toutes = false] : seule la dernière image est construite (l'image fixe de la page) *)
let film_escargot ~toutes appelle =
  let rec boucle n esc =
    if n <= nombre_images_escargot then begin
      let t = float n /. images_par_seconde_escargot in
      let esc = if n > 0 then Escargot.deplace esc (Escargot.choregraphie esc t) (2. *. esc.e) else esc in
      if toutes || n = nombre_images_escargot then appelle (image_escargot esc t) n (nombre_images_escargot + 1);
      boucle (n + 1) esc
    end
  in
  boucle 0 (Escargot.cree ())

(* --- le premier bouquet (lib/bouquet.ml), 810 × 1080, 13,5 s : une image calculée tous les 0,08 s --- *)

(* Ce que le dessin lit (Bouquet.dessine du Python) : les polylignes des 35 lacets, la plante de chaque lacet, et pour
   chaque plante 11 nombres : sorte (1 fleur, 0 feuille), centre, angle de la tige, éclosion, rayon de la fleur et des
   sépales (pixels), rayon du dégradé vert, couleur de la fleur. *)
let image_bouquet (p : Bouquet.t) t =
  let plantes =
    Array.concat
      (List.init (Array.length p.groupes) (fun n ->
           let g = p.groupes.(n) in
           let c = Bouquet.centre p n t in
           let d = Bouquet.direction_de_tige p n in
           let _, _, eclosion = Bouquet.phases g t in
           match g with
           | Bouquet.Fleur f ->
               let r, v, b = f.couleur in
               [| 1.; c.x; c.y; Float.atan2 d.y d.x; eclosion; f.rayon_fleur *. p.e; f.rayon_sepales *. p.e; 60. *. p.e; r; v; b |]
           | Bouquet.Feuille f -> [| 0.; c.x; c.y; Float.atan2 d.y d.x; eclosion; 0.; 0.; f.longueur *. p.e; 0.; 0.; 0. |]))
  in
  let nombre x = Js.Unsafe.inject (Js.number_of_float x) in
  Js.Unsafe.obj
    [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.map plat (Bouquet.polylignes p)))));
       ("plante", Js.Unsafe.inject (Js.array (Array.map float_of_int (Bouquet.plante_du_lacet p))));
       ("plantes", Js.Unsafe.inject (Js.array plantes));
       ("e", nombre p.e);
       ("largeur", nombre p.largeur);
       ("hauteur", nombre p.hauteur) |]

let pas_du_bouquet = 0.08
let nombre_images_bouquet = 169

let film_bouquet ~toutes appelle =
  let rec boucle n p =
    if n <= nombre_images_bouquet then begin
      let t = float n *. pas_du_bouquet in
      let p = if n > 0 then Bouquet.deplace p (Bouquet.choregraphie p t) (2. *. p.e) else p in
      if toutes || n = nombre_images_bouquet then appelle (image_bouquet p t) n (nombre_images_bouquet + 1);
      boucle (n + 1) p
    end
  in
  boucle 0 (Bouquet.cree Bouquet.bouquet)

(* --- les entrées : un mode, qui est un méandre de tresse ou une scène sans tresse --- *)

(* L'image fixe d'une scène sans tresse : la dernière image du film (le calcul est court : de 0,3 à 2 s) *)
let statique_libre film =
  let derniere = ref None in
  try
    film ~toutes:false (fun im _ _ -> derniere := Some im);
    match !derniere with Some im -> im | None -> failwith "pas d'image"
  with e -> Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

let statique mode mot =
  match Js.to_string mode with
  | "escargot" -> statique_libre film_escargot
  | "bouquet" -> statique_libre film_bouquet
  | _ -> statique_tresse mode mot

let film mode mot rendu =
  match Js.to_string mode with
  | ("escargot" | "bouquet") as m -> (
      try
        let appelle im k total =
          ignore (Js.Unsafe.fun_call rendu [| Js.Unsafe.inject im; Js.Unsafe.inject k; Js.Unsafe.inject total |])
        in
        if m = "escargot" then film_escargot ~toutes:true appelle else film_bouquet ~toutes:true appelle;
        Js.string ""
      with e -> Js.string (message e))
  | _ -> film_tresse mode mot rendu

let () =
  Js.Unsafe.set Js.Unsafe.global (Js.string "ardoise")
    (Js.Unsafe.obj
       [| ("analyse", Js.Unsafe.inject (Js.wrap_callback analyse));
          ("statique", Js.Unsafe.inject (Js.wrap_callback statique));
          ("film", Js.Unsafe.inject (Js.wrap_callback film)) |])
