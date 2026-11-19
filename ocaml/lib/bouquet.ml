(* Le premier bouquet. Voir bouquet.mli. Les opérations suivent l'ordre du Python (mêmes arrondis, à la dernière décimale
   près). *)

open Geometrie
open Triangulation

let lisse = Escargot.lisse

let bezier p0 p1 p2 s =
  (((1. -. s) ** 2.) *: p0) +: (((2. *. s) *. (1. -. s)) *: p1) +: ((s *. s) *: p2)

type fleur = {
  tete : float * float;
  depart : float;
  couleur : float * float * float;
  sens : float;
  nutation : float;
  petales : int;
  duree_montee : float;
  duree_bourgeon : float;
  duree_eclosion : float;
  tours : float;
  rayon_bourgeon : float;
  rayon_sepales : float;
  rayon_fleur : float;
  courbure : float;
}

type feuille = {
  tete : float * float;
  depart : float;
  angle : float;
  longueur : float;
  longueur_bourgeon : float;
  nutation : float;
  duree_montee : float;
  duree_eclosion : float;
  courbure : float;
}

type groupe = Fleur of fleur | Feuille of feuille

let fleur ?(nutation = 18.) ?(sens = 1.) ?(petales = 4) ?(duree_montee = 5.0) ?(duree_bourgeon = 2.0)
    ?(duree_eclosion = 3.5) ?(tours = 1.) ?(rayon_bourgeon = 20.) ?(rayon_sepales = 52.) ?(rayon_fleur = 100.)
    ?(courbure = 0.15) ~tete ~depart ~couleur () =
  Fleur
    { tete; depart; couleur; sens; nutation; petales; duree_montee; duree_bourgeon; duree_eclosion; tours;
      rayon_bourgeon; rayon_sepales; rayon_fleur; courbure }

let feuille ?(longueur = 80.) ?(longueur_bourgeon = 14.) ?(nutation = 8.) ?(duree_montee = 3.5) ?(duree_eclosion = 3.0)
    ?(courbure = 0.5) ~tete ~depart ~angle () =
  Feuille { tete; depart; angle; longueur; longueur_bourgeon; nutation; duree_montee; duree_eclosion; courbure }

let radians x = x *. (Float.pi /. 180.)

(* de gauche à droite dans la graine ; têtes : (abscisse, hauteur au-dessus du sol) dans une image de 800 de large. Les
   feuilles sont aux deux bouts de la graine, tournées vers l'extérieur : entre deux fleurs, une feuille coupait le chemin
   d'une tige et la faisait plier. *)
let bouquet =
  [ feuille ~tete:(110., 130.) ~depart:1.5 ~angle:(radians 150.) ();
    feuille ~tete:(215., 185.) ~depart:2.2 ~angle:(radians 160.) ~longueur:70. ();
    fleur ~tete:(190., 580.) ~depart:0.0 ~couleur:(0.92, 0.35, 0.50) ~sens:1. ();
    fleur ~tete:(415., 770.) ~depart:0.8 ~couleur:(0.97, 0.78, 0.25) ~sens:(-1.) ~nutation:22. ();
    fleur ~tete:(630., 560.) ~depart:1.6 ~couleur:(0.62, 0.42, 0.90) ~sens:1. ~nutation:16. ();
    feuille ~tete:(595., 175.) ~depart:2.6 ~angle:(radians 20.) ~longueur:70. ();
    feuille ~tete:(700., 120.) ~depart:1.8 ~angle:(radians 30.) () ]

let nb_trous_du_groupe = function Feuille _ -> 2 | Fleur f -> (2 * f.petales) + 1

type t = {
  film : Film.t;
  groupes : groupe array;
  largeur : float;
  hauteur : float;
  e : float;
  ecart : float;
  taux : float;
  y_sol : float;
  graine : point array;
  premier : int array;
}

let positions p = Array.map (fun s -> p.film.maillage.Maillage.pos.(s)) p.film.trous

(* Amène les sommets de [film.trous] en ligne droite aux cibles, par sous-pas d'au plus pas_max pixels. *)
let deplace_film (film : Film.t) cibles pas_max ecart taux =
  let pos0 = film.maillage.Maillage.pos in
  let depart = Array.map (fun s -> pos0.(s)) film.trous in
  let plus_long = ref 0. in
  Array.iteri (fun k c -> plus_long := Float.max !plus_long (norme (c -: depart.(k)))) cibles;
  let n = max 1 (int_of_float (Float.ceil (!plus_long /. pas_max))) in
  let rec boucle s (film : Film.t) =
    if s > n then film
    else begin
      let pos = Array.copy film.maillage.Maillage.pos in
      Array.iteri
        (fun k v ->
          let d = cibles.(k) -: depart.(k) in
          pos.(v) <- depart.(k) +: { x = d.x *. float s /. float n; y = d.y *. float s /. float n })
        film.trous;
      let maillage = Maillage.deplace film.maillage pos in
      if not (Maillage.valide maillage) then failwith "triangle retourné : diminuer pas_max";
      let maillage, courbes = Maillage.delaunay maillage film.courbes in
      boucle (s + 1) (Film.tend { film with maillage; courbes } taux ecart)
    end
  in
  boucle 1 film

let cree ?(hauteur = 1080.) ?(largeur = 810.) ?(taux = 0.12) groupes =
  let groupes = Array.of_list groupes in
  let nb_trous = Array.fold_left (fun a g -> a + nb_trous_du_groupe g) 0 groupes in
  (* une tresse de nb_trous brins : seul l'état de départ sert *)
  let film = Film.cree ~hauteur ~largeur [ Tresses.lettre_de_entier (nb_trous - 1) ] in
  let e = largeur /. 800. in
  let ecart = 2.3 *. e in
  let clou = film.maillage.Maillage.pos.(film.clou) in
  (* la graine : les trous en rang serré sous la terre, au-dessus du clou *)
  let y_graine = clou.y -. (30. *. e) in
  let graine =
    Array.init nb_trous (fun k ->
        { x = clou.x +. ((float k -. (float (nb_trous - 1) /. 2.)) *. 10. *. e); y = y_graine })
  in
  let premier = Array.make (Array.length groupes + 1) 0 in
  Array.iteri (fun n g -> premier.(n + 1) <- premier.(n) + nb_trous_du_groupe g) groupes;
  let film = deplace_film film graine (2. *. e) ecart 0.15 in
  { film = { film with y_axe = Float.neg_infinity }; groupes; largeur; hauteur; e; ecart; taux; y_sol = hauteur; graine;
    premier }

let deplace p cibles pas_max = { p with film = deplace_film p.film cibles pas_max p.ecart p.taux }

(* --- la chorégraphie --- *)

let depart_du_groupe = function Fleur f -> f.depart | Feuille f -> f.depart
let duree_montee = function Fleur f -> f.duree_montee | Feuille f -> f.duree_montee
let duree_eclosion = function Fleur f -> f.duree_eclosion | Feuille f -> f.duree_eclosion

let phases g t =
  let t = t -. depart_du_groupe g in
  (* sans durée de bourgeon (une feuille) : 1 pour le bourgeon, 0 pour l'éclosion, comme le g.get du Python *)
  let bourgeon_d, eclosion_d = match g with Fleur f -> (f.duree_bourgeon, f.duree_bourgeon) | Feuille _ -> (1., 0.) in
  let montee = lisse (t /. duree_montee g) in
  let bourgeon = lisse ((t -. duree_montee g) /. bourgeon_d) in
  let eclosion = lisse ((t -. duree_montee g -. eclosion_d) /. duree_eclosion g) in
  (montee, bourgeon, eclosion)

let tete_de p n =
  let x, y = match p.groupes.(n) with Fleur f -> f.tete | Feuille f -> f.tete in
  { x = x *. p.e; y = p.y_sol -. (y *. p.e) }

let graine_du_groupe p n =
  let somme = ref { x = 0.; y = 0. } in
  for k = p.premier.(n) to p.premier.(n + 1) - 1 do somme := !somme +: p.graine.(k) done;
  let m = float (p.premier.(n + 1) - p.premier.(n)) in
  { x = !somme.x /. m; y = !somme.y /. m }

let courbure = function Fleur f -> f.courbure | Feuille f -> f.courbure
let nutation = function Fleur f -> f.nutation | Feuille f -> f.nutation

let controle_de p n =
  let g = graine_du_groupe p n and tete = tete_de p n in
  { x = g.x +. (courbure p.groupes.(n) *. (tete.x -. g.x)); y = (g.y +. tete.y) /. 2. }

let centre p n t =
  let g = p.groupes.(n) in
  let graine = graine_du_groupe p n and tete = tete_de p n in
  let montee, _, _ = phases g t in
  let c = bezier graine (controle_de p n) tete montee in
  c +: { x = nutation g *. p.e *. Float.sin ((2. *. Float.pi *. t /. 2.7) +. float n) *. Float.sin (Float.pi *. montee); y = 0. }

let direction_de_tige p n =
  let d = controle_de p n -: tete_de p n in
  (1. /. norme d) *: d

let ouverture_cage = 320.

let trous_de_fleur p n t =
  match p.groupes.(n) with
  | Feuille _ -> invalid_arg "trous_de_fleur : une feuille"
  | Fleur f as g ->
      let m = nb_trous_du_groupe g in
      let montee, bourgeon, eclosion = phases g t in
      let c = centre p n t in
      let cercle = lisse ((montee *. 1.6) -. 0.6) in
      let rotation = f.sens *. 2. *. Float.pi *. f.tours *. bourgeon in
      Array.init m (fun j ->
          let demi = Float.pi -. (Float.pi *. float j /. float (m - 1)) in
          let final = radians (90. +. (ouverture_cage /. 2.) -. (ouverture_cage *. float j /. float (m - 1))) in
          let a = ((1. -. cercle) *. demi) +. (cercle *. final) in
          let a, rayon =
            if j mod 2 = 0 then (a, ((1. -. cercle) *. f.rayon_bourgeon) +. (cercle *. f.rayon_sepales))
            else (a +. rotation, f.rayon_bourgeon +. (eclosion *. (f.rayon_fleur -. f.rayon_bourgeon)))
          in
          c +: ((rayon *. p.e) *: { x = Float.cos a; y = -.Float.sin a }))

let trous_de_feuille p n t =
  match p.groupes.(n) with
  | Fleur _ -> invalid_arg "trous_de_feuille : une fleur"
  | Feuille f as g ->
      let _, _, eclosion = phases g t in
      let c = centre p n t in
      let direction = { x = Float.cos f.angle; y = -.Float.sin f.angle } in
      let direction = if direction.x < 0. then oppose direction else direction in
      let longueur = (f.longueur_bourgeon +. (eclosion *. (f.longueur -. f.longueur_bourgeon))) *. p.e in
      [| c -: ((longueur /. 2.) *: direction); c +: ((longueur /. 2.) *: direction) |]

let choregraphie p t =
  Array.concat
    (List.init (Array.length p.groupes) (fun n ->
         let g = p.groupes.(n) in
         let cibles = match g with Feuille _ -> trous_de_feuille p n t | Fleur _ -> trous_de_fleur p n t in
         let montee, _, _ = phases g t in
         let sortie = lisse (montee *. 5.) in
         Array.mapi
           (fun j cible -> ((1. -. sortie) *: p.graine.(p.premier.(n) + j)) +: (sortie *: cible))
           cibles))

let polylignes p = List.map (Film.polyligne_de_courbe p.film.maillage) p.film.courbes

let plante_du_lacet p =
  Array.concat (List.init (Array.length p.groupes) (fun n -> Array.make (nb_trous_du_groupe p.groupes.(n)) n))
