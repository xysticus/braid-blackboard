(* Le pont entre la bibliothèque et la page web. Un seul objet global, [ardoise], avec trois fonctions :

     ardoise.analyse(mot)                       → { n, fn }       les images des générateurs de F_n
     ardoise.statique(mode, mot)                → image            l'image fixe d'un mode
     ardoise.film(mode, mot, rendu) → string                       le film, image par image ; "" si tout va bien

   mot : tableau d'entiers non nuls (σ_k : k, σ_k⁻¹ : -k). mode : "conforme", "diagramme" ou "rubans".
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
      (Printf.sprintf "le film conforme est limité à %d brins et %d lettres" max_brins_conforme max_lettres_conforme)

(* Polyligne ou liste de points → tableau JS plat. *)
let plat points =
  let a = Array.make (2 * Array.length points) 0. in
  Array.iteri (fun k p -> a.(2 * k) <- p.x; a.((2 * k) + 1) <- p.y) points;
  Js.array a

let image ?(decalage = { x = 0.; y = 0. }) ?(fixes = [||]) ?(ecart = 6.) lacets trous clou =
  let d = Array.map (fun p -> p +: decalage) in
  Js.Unsafe.obj
    [| ("lacets", Js.Unsafe.inject (Js.array (Array.of_list (List.map (fun l -> plat (d l)) lacets))));
       ("trous", Js.Unsafe.inject (plat (d trous)));
       ("fixes", Js.Unsafe.inject (plat (d fixes)));
       ("clou", Js.Unsafe.inject (plat (d [| clou |])));
       ("ecart", Js.Unsafe.inject (Js.number_of_float ecart)) |]

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

let nombre_images_arcs = 60
let nombre_images_conforme = 48

let statique mode mot =
  try
    let tresse = tresse_de_js mot in
    match Js.to_string mode with
    | "conforme" ->
        verifie_limites tresse;
        image_conforme { x = marge; y = marge } (Film_conforme.image_finale ~hauteur:cote ~largeur:cote ~marge tresse)
    | m ->
        verifie_limites tresse;
        let cree, rubans = methode_arcs m in
        let film = List.fold_left (fun f s -> Arcs.lettre f s) (cree tresse) tresse in
        image_arcs rubans film
  with e -> Js.Unsafe.obj [| ("erreur", Js.Unsafe.inject (Js.string (message e))) |]

let film mode mot rendu =
  try
    let tresse = tresse_de_js mot in
    let appelle im k total = ignore (Js.Unsafe.fun_call rendu [| Js.Unsafe.inject im; Js.Unsafe.inject k; Js.Unsafe.inject total |]) in
    (match Js.to_string mode with
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

let () =
  Js.Unsafe.set Js.Unsafe.global (Js.string "ardoise")
    (Js.Unsafe.obj
       [| ("analyse", Js.Unsafe.inject (Js.wrap_callback analyse));
          ("statique", Js.Unsafe.inject (Js.wrap_callback statique));
          ("film", Js.Unsafe.inject (Js.wrap_callback film)) |])
