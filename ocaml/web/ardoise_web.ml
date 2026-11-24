(* Le pont entre la bibliothèque et la page web. Un seul objet global, [ardoise], avec trois fonctions :

     ardoise.analyse(mot)                       → { n, fn }       les images des générateurs de F_n
     ardoise.statique(mode, mot)                → image            l'image fixe d'un mode
     ardoise.film(mode, mot, rendu) → string                       le film, image par image ; "" si tout va bien

   mot : tableau d'entiers non nuls (σ_k : k, σ_k⁻¹ : -k). mode : "conforme", "triangulation", "diagramme" ou "rubans" (méandres d'une
   tresse), ou "escargot" ou "bouquet" (films sans tresse : le mot est ignoré, les images ont d'autres champs, voir
   image_escargot et image_bouquet).
   Une image : { lacets : [[x0, y0, x1, y1, …], …], trous : [x, y, …], fixes : [x, y, …], clou : [x, y],
   ecart : nombre } dans un cadre de 800 × 800 ; les films de la triangulation, du diagramme de courbes, des rubans et des lacets
   (conforme) ajoutent construction : [x0, y0, x1, y1, …], les lignes de construction (les arêtes du maillage ; l'axe et la ligne brisée L–A–B–R),
   à tracer en gris sous les lacets si la page le demande (case « lignes de construction »). Les lacets ajoutent aussi
   opacites : [a0, a1, …], l'opacité de chaque segment (ils s'estompent pendant le raccord). [rendu] est appelé avec (image, numéro, total) pour chaque image du
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

(* Le banc d'essai lève les limites pour le méandre témoin (le mot écrit par les trous dépasse vite 14 lettres) ; jamais la page publique. *)
let limites_levees = ref false

let verifie_limites ?(conforme = false) tresse =
  if tresse = [] then invalid_arg "mot vide : c'est la tresse nulle, il n'y a rien à dessiner";
  let n = nb_brins tresse and l = List.length tresse in
  if not !limites_levees then begin
    if n > max_brins || l > max_lettres then
      invalid_arg (Printf.sprintf "limites de la page : %d brins et %d lettres au plus" max_brins max_lettres);
    if conforme && (n > max_brins_conforme || l > max_lettres_conforme) then
      invalid_arg
        (Printf.sprintf "ce film (conforme ou triangulation) est limité à %d brins et %d lettres" max_brins_conforme max_lettres_conforme)
  end

(* Polyligne ou liste de points → tableau JS plat. *)
let plat points =
  let a = Array.make (2 * Array.length points) 0. in
  Array.iteri (fun k p -> a.(2 * k) <- p.x; a.((2 * k) + 1) <- p.y) points;
  Js.array a

let image ?(decalage = { x = 0.; y = 0. }) ?(fixes = [||]) ?(ecart = 6.) ?(brin = 3.5) ?construction ?opacites lacets trous clou =
  let d = Array.map (fun p -> p +: decalage) in
  Js.Unsafe.obj
    (Array.append
       [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.map (fun l -> plat (d l)) lacets))));
          ("trous", Js.Unsafe.inject (plat (d trous)));
          ("fixes", Js.Unsafe.inject (plat (d fixes)));
          ("clou", Js.Unsafe.inject (plat (d [| clou |])));
          ("ecart", Js.Unsafe.inject (Js.number_of_float ecart));
          ("brin", Js.Unsafe.inject (Js.number_of_float brin)) |]
       (Array.append
          (match construction with None -> [||] | Some c -> [| ("construction", Js.Unsafe.inject c) |])
          (match opacites with None -> [||] | Some o -> [| ("opacites", Js.Unsafe.inject o) |])))

(* Les arêtes d'un maillage, en segments à plat (x0, y0, x1, y1, …), dans l'ordre rangé des arêtes. *)
let aretes_a_plat (m : Triangulation.Maillage.t) =
  let pos = m.Triangulation.Maillage.pos in
  let segments =
    Triangulation.Aretes.fold
      (fun (arete : Triangulation.Arete.t) _ acc ->
        let u, v = (arete :> int * int) in
        pos.(v).y :: pos.(v).x :: pos.(u).y :: pos.(u).x :: acc)
      (Triangulation.Maillage.aretes m) []
  in
  Js.array (Array.of_list (List.rev segments))

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

(* Les lignes de construction du film conforme : segments à plat (décalés de la marge) et leur opacité. *)
let construction_conforme decalage (segments : (point * point * float) list) =
  let n = List.length segments in
  let c = Array.make (4 * n) 0. and o = Array.make n 0. in
  List.iteri
    (fun k (p, q, alpha) ->
      let p = p +: decalage and q = q +: decalage in
      c.(4 * k) <- p.x; c.((4 * k) + 1) <- p.y; c.((4 * k) + 2) <- q.x; c.((4 * k) + 3) <- q.y;
      o.(k) <- alpha)
    segments;
  (Js.array c, Js.array o)

let image_conforme decalage (im : Film_conforme.image) =
  let construction, opacites = construction_conforme decalage im.construction in
  let r = image ~decalage ~construction ~opacites im.lignes im.trous im.clou in
  let a = Array.make (4 * List.length im.maillage) 0. in
  List.iteri (fun k (p, q) -> let p = p +: decalage and q = q +: decalage in a.(4 * k) <- p.x; a.((4 * k) + 1) <- p.y; a.((4 * k) + 2) <- q.x; a.((4 * k) + 3) <- q.y) im.maillage;
  Js.Unsafe.set r "maillage" (Js.array a);
  Js.Unsafe.set r "reperes" (Js.array (Array.concat (List.map (fun p -> let p = p +: decalage in [| p.x; p.y |]) im.reperes)));   (* les pieds du mode pur *)
  let plat_lignes ls = Js.array (Array.of_list (List.map (fun p -> Js.array (Array.concat (List.map (fun (q : point) -> let q = q +: decalage in [| q.x; q.y |]) (Array.to_list p)))) ls)) in
  Js.Unsafe.set r "trajets" (Js.array (Array.concat (List.map (fun ((p : point), (q : point), role) -> let p = p +: decalage and q = q +: decalage in [| p.x; p.y; q.x; q.y; float_of_int role |]) im.trajets)));
  Js.Unsafe.set r "lacets_bis" (plat_lignes im.lignes_bis);
  Js.Unsafe.set r "lacets_morph" (plat_lignes im.morph);
  Js.Unsafe.set r "reperes_bis" (Js.array (Array.concat (List.map (fun p -> let p = p +: decalage in [| p.x; p.y |]) im.reperes_bis)));   (* les arêtes du maillage du raccord, à plat, pour le banc d'essai *)
  (match im.etude with
   | None -> ()
   | Some e ->
       let plan (p : Conforme.plan) =
         let plat_z = Array.concat (Array.to_list (Array.map (fun (z : Complex.t) -> [| z.re; z.im |]) p.ligne)) in
         let arcs = Array.concat (List.map (fun (lacet, haut, w0, w1) -> [| float_of_int lacet; (if haut then 1. else 0.); w0; w1 |]) p.arcs) in
         Js.Unsafe.obj
           [| ("w", Js.Unsafe.inject (Js.array p.sommets)); ("clou", Js.Unsafe.inject (Js.array [| p.w_clou.re; p.w_clou.im |]));
              ("arcs", Js.Unsafe.inject (Js.array arcs)); ("ligne", Js.Unsafe.inject (Js.array plat_z)) |]
       in
       let etude =
         Js.Unsafe.obj
           [| ("journal", Js.Unsafe.inject (Js.array (Array.of_list (List.map (fun t -> Js.Unsafe.inject (Js.string t)) e.journal))));
              ("phase", Js.Unsafe.inject e.phase); ("na", Js.Unsafe.inject e.n_a); ("nb", Js.Unsafe.inject e.n_b);
              ("sa", Js.Unsafe.inject e.s_a); ("sb", Js.Unsafe.inject e.s_b);
              ("depart", Js.Unsafe.inject (plan e.plan_depart)); ("arrivee", Js.Unsafe.inject (plan e.plan_arrivee)) |]
       in
       Js.Unsafe.set r "etude" etude);   (* le journal et les plans w (mode +etude), pour le banc d'essai *)
  Js.Unsafe.set r "ab" im.ab;   (* l'indice du segment A–B dans construction : le banc d'essai etude/lacets n'y trace pas de tangente *)
  r

let methode_arcs = function
  | "rubans" -> ((fun t -> Arcs.cree ~ecart_fixes:30. t), true)
  | "diagramme" -> ((fun t -> Arcs.cree_diagramme t), false)
  | m -> invalid_arg ("mode inconnu : " ^ m)

let image_arcs rubans (film : Arcs.t) =
  let pos = film.maillage.Triangulation.Maillage.pos in
  let lacets = List.mapi (fun k _ -> if rubans then Arcs.ruban film k else Arcs.polyligne film k) film.courbes in
  (* les lignes de construction : les arêtes du maillage sur lequel les arcs sont posés (au centre des rubans, pour les rubans) *)
  let construction = aretes_a_plat film.maillage in
  image ~fixes:(Array.map (fun s -> pos.(s)) film.fixes) ~ecart:film.ecart ~construction lacets (Array.map (fun s -> pos.(s)) film.voyageurs)
    { x = -100.; y = -100. }

(* --- la triangulation mobile (lib/film.ml, le film de Dessin.film_triangule sans le maillage gris), sur le maillage
   grossier des films d'arcs (Film.cree ~grossier:true) --- *)

(* Le trait suit l'écart entre brins : au plus 70 % de cet écart (brins serrés : trait plus fin), comme Dessin.cadre. *)
let image_triangulation (film : Film.t) ecart =
  let brin = Float.min (3. *. film.largeur /. 400.) (Float.max 1. (0.7 *. ecart)) in
  let pos = film.maillage.Triangulation.Maillage.pos in
  image ~brin ~construction:(aretes_a_plat film.maillage) (Film.polylignes film) (Film.positions_des_trous film) pos.(film.clou)

(* Joue le film en appelant [rendu film ecart numéro] à chaque image (le départ : numéro 0). *)
let joue_triangulation ?(debut_de_lettre = fun (_ : int) -> ()) tresse ~sous_pas ~rendu =
  let film = Film.cree ~hauteur:cote ~largeur:cote ~grossier:true tresse in
  rendu film film.dispositions.(0).ecart 0;
  let k = ref 0 in
  let film =
    List.fold_left
      (fun film sigma ->
        debut_de_lettre !k;   (* le numéro de l'image de départ de cette lettre (celle d'avant son demi-tour) *)
        fst (Film.lettre ~sous_pas ~rendu:(fun f e -> incr k; rendu f e !k) film sigma))
      film tresse
  in
  debut_de_lettre !k;   (* et la dernière image du film *)
  ignore film

(* Il reste, rarement (de 1 à 3 mots sur 100 à 6 brins et 14 lettres), un triangle plat que la rotation d'une paire retourne :
   un autre pas de temps l'évite le plus souvent. On essaie donc 2, 4 puis 8 sous-pas par image, sans rien dessiner, ce qui
   donne aussi le nombre d'images et la dernière image (l'image fixe). Reste moins d'un mot sur cent qui ne passe pas. *)
let prepare_triangulation tresse =
  let essai sous_pas =
    let derniere = ref None and n = ref 0 and debuts = ref [] in
    try
      joue_triangulation ~debut_de_lettre:(fun k -> debuts := k :: !debuts) tresse ~sous_pas ~rendu:(fun f e k -> n := k; derniere := Some (f, e));
      Option.map (fun d -> (sous_pas, !n, d, Array.of_list (List.rev !debuts))) !derniere
    with Failure _ -> None
  in
  match List.find_map essai [ 2; 4; 8 ] with
  | Some r -> r
  | None -> failwith "la triangulation ne passe pas ce mot (un triangle se retourne) : essaie un autre mot"

let nombre_images_arcs = 60
let nombre_images_conforme = 48

(* Les chapitres d'un film : les numéros des images où commence chaque lettre du mot (la première : 0), puis le numéro de la dernière
   image du film. Un mot de L lettres donne L + 1 nombres. Ils sont portés par l'image 0 du film (champ « chapitres ») : la page
   les lit à la réception de cette image. *)
let avec_chapitres debuts im =
  Js.Unsafe.set im "chapitres" (Js.array (Array.map float_of_int debuts));
  im

(* Quand chaque lettre compte le même nombre d'images (lacets, diagramme, rubans) *)
let chapitres_reguliers ~par_lettre lettres = Array.init (lettres + 1) (fun j -> j * par_lettre)

let statique_tresse mode mot =
  try
    let tresse = tresse_de_js mot in
    let nom = Js.to_string mode in
    let nom = if String.ends_with ~suffix:"+etude" nom then String.sub nom 0 (String.length nom - 6) else nom in
    match nom with
    | "triangulation" ->
        verifie_limites ~conforme:true tresse;
        let _, _, (film, ecart), _ = prepare_triangulation tresse in
        image_triangulation film ecart
    | "conforme" | "conforme_libre" | "conforme_sans_maillage" | "conforme_satellites" | "conforme_detendu" | "conforme_pur" | "conforme_pur_detendu" ->
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
    (* un suffixe « +etude » demande, pour le film conforme, le journal et les plans w de chaque image (banc d'essai) *)
    let nom = Js.to_string mode in
    let etude = String.ends_with ~suffix:"+etude" nom in
    let nom = if etude then String.sub nom 0 (String.length nom - 6) else nom in
    (match nom with
    | "triangulation" ->
        verifie_limites ~conforme:true tresse;
        let sous_pas, total, _, debuts = prepare_triangulation tresse in
        joue_triangulation tresse ~sous_pas ~rendu:(fun f e k ->
            let im = image_triangulation f e in
            if k = 0 then avec_chapitres debuts im;
            appelle im k (total + 1));
        Js.string ""
    | "triangulation_envers" ->
        (* le film du mot suivi de son inverse (le méandre complet se construit, puis se défait lettre par lettre) ; seule la seconde moitié
           est rendue, dans l'ordre du calcul : la page la rejoue à l'envers. La limite porte sur le mot, pas sur le mot doublé. *)
        verifie_limites ~conforme:true tresse;
        let inverse = List.rev_map (fun (l : _ Tresses.lettre) -> { l with Tresses.signe = (match l.signe with Tresses.Plus -> Tresses.Moins | Tresses.Moins -> Tresses.Plus) }) tresse in
        let double = tresse @ inverse in
        let sous_pas, total, _, debuts = prepare_triangulation double in
        let debut = debuts.(List.length tresse) in   (* l'image où commence le retour : le méandre complet *)
        joue_triangulation double ~sous_pas ~rendu:(fun f e k ->
            if k >= debut then begin
              let im = image_triangulation f e in
              if k = debut then ignore (avec_chapitres (Array.init (List.length tresse + 1) (fun j -> debuts.(List.length tresse + j) - debut)) im);
              appelle im (k - debut) (total + 1 - debut)
            end);
        Js.string ""
    | ("conforme" | "conforme_libre" | "conforme_sans_maillage" | "conforme_satellites" | "conforme_detendu" | "conforme_pur" | "conforme_pur_detendu") as mode ->
        (* conforme_libre : les arcs ne passent plus par les points « fantômes » (les pieds sur la plus claire des deux lignes de
           construction pendant le raccord) ; sert au banc d'essai etude/lacets, pas à la page publique *)
        verifie_limites ~conforme:true tresse;
        let total = 1 + (nombre_images_conforme * List.length tresse) in
        let k = ref 0 in
        let anomalies =
          Film_conforme.film ~verifie:true ~sans_fantomes:(mode = "conforme_libre") ~libre:(mode = "conforme_libre") ~sans_maillage:(mode = "conforme_sans_maillage") ~satellites:(if mode = "conforme_satellites" then 8 else 0) ~detente:(mode = "conforme_detendu" || mode = "conforme_pur_detendu") ~pur:(mode = "conforme_pur" || mode = "conforme_pur_detendu") ~etude ~hauteur:cote ~largeur:cote ~marge
            ~rendu:(fun im ->
              let image = image_conforme { x = marge; y = marge } im in
              if !k = 0 then ignore (avec_chapitres (chapitres_reguliers ~par_lettre:nombre_images_conforme (List.length tresse)) image);
              appelle image !k total;
              incr k)
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
        let rendu f =
          let image = image_arcs rubans f in
          if !k = 0 then ignore (avec_chapitres (chapitres_reguliers ~par_lettre:nombre_images_arcs (List.length tresse)) image);
          appelle image !k total;
          incr k
        in
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

(* Une partie du film conforme, pour les workers auxiliaires de travail.js : l'image clé de départ (si premiere) et les
   lettres d'indices [lettres] ; [rendu] reçoit chaque image avec son numéro dans le film entier. Rend le nombre d'images
   douteuses (mots ou croisements), ou un message d'erreur. *)
let film_lettres_gen ~images ~verifie mode mot (lettres : float Js.js_array Js.t) (premiere : bool Js.t) rendu =
  try
    let tresse = tresse_de_js mot in
    let nom = Js.to_string mode in
    let etude = String.ends_with ~suffix:"+etude" nom in
    let nom = if etude then String.sub nom 0 (String.length nom - 6) else nom in
    if not (List.mem nom [ "conforme"; "conforme_libre"; "conforme_sans_maillage"; "conforme_satellites"; "conforme_detendu"; "conforme_pur"; "conforme_pur_detendu" ]) then
      invalid_arg ("film_lettres : mode " ^ nom);
    verifie_limites ~conforme:true tresse;
    let lettres = List.sort compare (List.map int_of_float (Array.to_list (Js.to_array lettres))) in
    let premiere = Js.to_bool premiere in
    let total = 1 + (images * List.length tresse) in
    let numeros =
      ref ((if premiere then [ 0 ] else []) @ List.concat_map (fun k -> List.init images (fun n -> 1 + (images * k) + n)) lettres)
    in
    let anomalies =
      Film_conforme.film ~images ~verifie ~sans_fantomes:(nom = "conforme_libre") ~libre:(nom = "conforme_libre") ~sans_maillage:(nom = "conforme_sans_maillage")
        ~satellites:(if nom = "conforme_satellites" then 8 else 0) ~detente:(nom = "conforme_detendu" || nom = "conforme_pur_detendu") ~pur:(nom = "conforme_pur" || nom = "conforme_pur_detendu") ~etude ~premiere ~lettres ~hauteur:cote ~largeur:cote ~marge
        ~rendu:(fun im ->
          match !numeros with
          | k :: reste ->
              numeros := reste;
              let image = image_conforme { x = marge; y = marge } im in
              if k = 0 then ignore (avec_chapitres (chapitres_reguliers ~par_lettre:images (List.length tresse)) image);
              ignore (Js.Unsafe.fun_call rendu [| Js.Unsafe.inject image; Js.Unsafe.inject k; Js.Unsafe.inject total |])
          | [] -> failwith "film_lettres : une image de trop")
        tresse
    in
    Js.Unsafe.obj [| ("douteuses", Js.Unsafe.inject (List.length anomalies)) |]
  with e -> Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

(* Les images d'une ou plusieurs lettres du film conforme, 48 par lettre et vérifiées (la page et le film). *)
let film_lettres mode mot lettres premiere rendu = film_lettres_gen ~images:nombre_images_conforme ~verifie:true mode mot lettres premiere rendu

(* Pour le méandre témoin du mouvement libre (banc d'essai) : [images] par lettre (moins de 48, donc plus rapide et plus léger) et sans la
   vérification des croisements ; les numéros des images sont ceux d'un film de [images] images par lettre. *)
let film_lettres_rapide mode mot lettres premiere (images : float) rendu =
  film_lettres_gen ~images:(max 2 (int_of_float images)) ~verifie:false mode mot lettres premiere rendu

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

(* La détente d'une image du film conforme (Detente), pour les workers auxiliaires de travail.js : lacets (tableaux plats
   x, y), trous (plat), clou (plat), force ∈ [0, 1]. La détente ne dépend que des positions relatives : les coordonnées de
   la page (décalées de la marge) conviennent. ecart : l'écart minimal entre brins (0 : les réglages de Detente.defaut, écart 6 px et 12 px autour des trous) ; sinon le
   rayon autour des trous lui est égal (le film de la triangulation resserre ses brins près des trous : à 2 écarts, la répulsion
   des trous poussait plusieurs couches de brins à la fois et pouvait en faire passer une par-dessus l'autre). Rend
   { lacets, croisements } (nombre de croisements entre lacets, comme la vérification du film). *)
let detend ?(portee = Float.infinity) ?iterations ?pas (lacets : float Js.js_array Js.t Js.js_array Js.t) (trous : float Js.js_array Js.t) (clou : float Js.js_array Js.t) (force : float) (ecart : float) =
  try
    let points (a : float Js.js_array Js.t) =
      let v = Js.to_array a in
      Array.init (Array.length v / 2) (fun k -> { x = v.(2 * k); y = v.((2 * k) + 1) })
    in
    let lignes = List.map points (Array.to_list (Js.to_array lacets)) in
    let clou = (points clou).(0) in
    let reglages = if ecart > 0. then { Detente.defaut with ecart; rayon_trou = ecart; repulsion = 4.; iterations = 150 } else Detente.defaut in
    let reglages = { reglages with Detente.portee } in
    let reglages = match iterations with Some n -> { reglages with Detente.iterations = n } | None -> reglages in
    let reglages = match pas with Some p -> { reglages with Detente.pas = p } | None -> reglages in
    let sortie = Detente.detend ~reglages lignes (points trous) clou force in
    Js.Unsafe.obj
      [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.map plat sortie))));
         ("croisements", Js.Unsafe.inject (Film_conforme.nb_croisements sortie clou)) |]
  with e -> Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

let () =
  Js.Unsafe.set Js.Unsafe.global (Js.string "ardoise")
    (Js.Unsafe.obj
       [| ("analyse", Js.Unsafe.inject (Js.wrap_callback analyse));
          ("statique", Js.Unsafe.inject (Js.wrap_callback statique));
          ("film", Js.Unsafe.inject (Js.wrap_callback film));
          ("film_lettres", Js.Unsafe.inject (Js.wrap_callback film_lettres));
          ("film_lettres_rapide", Js.Unsafe.inject (Js.wrap_callback film_lettres_rapide));
          ("detend", Js.Unsafe.inject (Js.wrap_callback (fun l t c f e -> detend l t c f e)));
          ("sans_limites", Js.Unsafe.inject (Js.wrap_callback (fun (b : bool Js.t) -> limites_levees := Js.to_bool b)));
          ("detend_local", Js.Unsafe.inject (Js.wrap_callback (fun l t c f e p it pa -> detend ~portee:p ?iterations:(if it > 0. then Some (int_of_float it) else None) ?pas:(if pa > 0. then Some pa else None) l t c f e))) |])
