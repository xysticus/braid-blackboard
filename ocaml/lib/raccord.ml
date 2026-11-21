(* Le maillage à bord convexe. Voir raccord.mli. *)

open Geometrie
open Triangulation

let insere m p =
  let pos = m.Maillage.pos in
  let v = Array.length pos in
  let contient t =
    let a, b, c = (t : Triangle.t :> sommet * sommet * sommet) in
    let s = List.map (fun (x, y) -> croix (pos.(y) -: pos.(x)) (p -: pos.(x))) [ (a, b); (b, c); (c, a) ] in
    let echelle = List.fold_left Float.max 1. [ norme (pos.(b) -: pos.(a)); norme (pos.(c) -: pos.(b)) ] in
    let nuls = List.map (fun x -> Float.abs x < 1e-9 *. echelle) s in
    let tous signe = List.for_all2 (fun x nul -> signe x || nul) s nuls in
    if tous (fun x -> x > 0.) || tous (fun x -> x < 0.) then Some (a, b, c, nuls) else None
  in
  let triangles = Maillage.triangles m in
  match List.find_map (fun t -> Option.map (fun r -> (t, r)) (contient t)) triangles with
  | None -> invalid_arg "Raccord.insere : sommet hors du maillage"
  | Some (t, (a, b, c, nuls)) ->
    let retires, nouveaux =
      match List.find_index Fun.id nuls with
      | None -> ([ t ], [ Triangle.v a b v; Triangle.v b c v; Triangle.v c a v ])
      | Some j ->
        (* sur une arête : on coupe aussi le triangle voisin *)
        let x, y = List.nth [ (a, b); (b, c); (c, a) ] j in
        let cote = Arete.v x y in
        let autres = List.filter (fun u -> u <> t && List.mem cote (Triangle.aretes u)) triangles in
        let z = Triangle.oppose t cote in
        ( t :: autres,
          [ Triangle.v x z v; Triangle.v y z v ]
          @ List.concat_map (fun u -> let w = Triangle.oppose u cote in [ Triangle.v x w v; Triangle.v y w v ]) autres )
    in
    (* les orientations des triangles gardés n'ont pas changé (les sommets n'ont pas bougé) : les recalculer
       toutes revient au même *)
    let gardes = List.filter (fun u -> not (List.mem u retires)) triangles in
    (Maillage.cree (Array.append pos [| p |]) (gardes @ nouveaux), v)

let maillage_du_raccord ?(marge = 40.) ?(par_cote = 6) trous clou largeur hauteur =
  let x0 = -.marge and y0 = -.marge and x1 = largeur +. marge and y1 = hauteur +. marge in
  (* le bord tourne dans le sens horaire de l'écran ; bombé pour être strictement convexe *)
  let cote f = List.init par_cote (fun k -> let u = float k /. float par_cote in f u (3. *. Float.sin (Float.pi *. u))) in
  let bord =
    cote (fun u bosse -> { x = x0 +. (u *. (x1 -. x0)); y = y0 -. bosse })
    @ cote (fun u bosse -> { x = x1 +. bosse; y = y0 +. (u *. (y1 -. y0)) })
    @ cote (fun u bosse -> { x = x1 -. (u *. (x1 -. x0)); y = y1 +. bosse })
    @ cote (fun u bosse -> { x = x0 -. bosse; y = y1 -. (u *. (y1 -. y0)) })
  in
  let nb = List.length bord in
  (* éventail d'un polygone strictement convexe *)
  let m = Maillage.cree (Array.of_list bord) (List.init (nb - 2) (fun k -> Triangle.v 0 (k + 1) (k + 2))) in
  let trous = Array.of_list trous in
  let ordre = List.stable_sort (fun p q -> compare (trous.(p).x, trous.(p).y) (trous.(q).x, trous.(q).y))
      (List.init (Array.length trous) Fun.id) in
  let indices = Array.make (Array.length trous) 0 in
  let m = List.fold_left (fun m p -> let m, v = insere m trous.(p) in indices.(p) <- v; m) m ordre in
  let m, i_clou = match clou with None -> (m, None) | Some c -> let m, v = insere m c in (m, Some v) in
  let m, _ = Maillage.delaunay m [] in
  (m, Array.to_list indices, i_clou)

(* --- Le raccord du film conforme par triangulation mobile (étape 7c) --- *)

let lisse u = u *. u *. (3. -. (2. *. u))

(* Image d'un point par l'application affine par triangles qui envoie les positions avant sur apres : le triangle
   qui le contient (le plus « intérieur » si plusieurs : la plus grande des plus petites coordonnées barycentriques),
   puis les mêmes coordonnées barycentriques dans le triangle déplacé (localise et transporte du Python). *)
let transporte_point triangles avant apres x =
  let meilleur = ref None and pire_max = ref Float.neg_infinity in
  List.iter
    (fun t ->
      let a, b, c = (t : Triangle.t :> sommet * sommet * sommet) in
      let pa = avant.(a) in
      let v0 = avant.(b) -: pa and v1 = avant.(c) -: pa in
      let det = croix v0 v1 in
      let d = x -: pa in
      let l1 = ((d.x *. v1.y) -. (d.y *. v1.x)) /. det and l2 = ((v0.x *. d.y) -. (v0.y *. d.x)) /. det in
      let l0 = 1. -. l1 -. l2 in
      let pire = Float.min (Float.min l0 l1) l2 in
      if pire > !pire_max then begin
        pire_max := pire;
        meilleur := Some (a, b, c, l0, l1, l2)
      end)
    triangles;
  if !pire_max <= -1e-6 then failwith "Raccord.transporte : point hors du maillage";
  match !meilleur with
  | Some (a, b, c, l0, l1, l2) ->
      { x = (l0 *. apres.(a).x) +. (l1 *. apres.(b).x) +. (l2 *. apres.(c).x);
        y = (l0 *. apres.(a).y) +. (l1 *. apres.(b).y) +. (l2 *. apres.(c).y) }
  | None -> failwith "Raccord.transporte : maillage vide"

let transporte lignes triangles avant apres = List.map (Array.map (transporte_point triangles avant apres)) lignes

type traversee = { position : float; arete : Arete.t; fraction : float }
(* Une traversée d'arête par une polyligne : la position le long de la polyligne (indice du segment + fraction),
   l'arête, la fraction de u vers v où elle est traversée. *)

(* Traversées des arêtes par une polyligne qui part du clou et y revient : (suite réduite, toutes les traversées).
   Un point posé sur une arête compte toujours du même côté (une traversée est un changement de côté). La suite
   réduite annule les bigones (deux traversées successives d'une même arête) et ne garde pas les traversées des arêtes
   du clou en tête et en queue (le clou est le point base, un lacet peut tourner autour en partant). *)
let coupe points m clou =
  let pos = m.Maillage.pos in
  let n = Array.length points in
  let trouvees = ref [] in
  Aretes.iter
    (fun arete _ ->
      let u, v = (arete : Arete.t :> sommet * sommet) in
      let s = pos.(v) -: pos.(u) in
      let longueur = Float.hypot s.x s.y in
      let cote = Array.map (fun p -> ((s.x *. (p.y -. pos.(u).y)) -. (s.y *. (p.x -. pos.(u).x))) /. longueur) points in
      for k = 0 to n - 2 do
        if cote.(k) >= -1e-7 <> (cote.(k + 1) >= -1e-7) then begin
          let t = cote.(k) /. (cote.(k) -. cote.(k + 1)) in
          let xk = points.(k) +: (t *: (points.(k + 1) -: points.(k))) in
          let w = scalaire (xk -: pos.(u)) s /. (longueur *. longueur) in
          if 1e-9 < w && w < 1. -. 1e-9 then trouvees := { position = float_of_int k +. t; arete; fraction = w } :: !trouvees
        end
      done)
    (Maillage.aretes m);
  let toutes = List.stable_sort (fun a b -> compare a.position b.position) (List.rev !trouvees) in
  let pile =
    List.fold_left (fun pile t -> match pile with x :: reste when x.arete = t.arete -> reste | _ -> t :: pile) [] toutes |> List.rev
  in
  let touche_clou t = let u, v = (t.arete : Arete.t :> sommet * sommet) in u = clou || v = clou in
  let rec sans_tete = function x :: reste when touche_clou x -> sans_tete reste | l -> l in
  (List.rev (sans_tete (List.rev (sans_tete pile))), toutes)

(* Le point de la polyligne à une position (indice du segment + fraction). *)
let point_en points position =
  let k = min (int_of_float position) (Array.length points - 2) in
  points.(k) +: ((position -. float_of_int k) *: (points.(k + 1) -: points.(k)))

(* Le morceau de la polyligne entre les positions a <= b. *)
let morceau points a b =
  let interieurs =
    List.filter_map
      (fun v -> if a < float_of_int v && float_of_int v < b then Some points.(v) else None)
      (List.init (max 0 (int_of_float (Float.ceil b) - (int_of_float (Float.floor a) + 1))) (fun i -> int_of_float (Float.floor a) + 1 + i))
  in
  Array.of_list ((point_en points a :: interieurs) @ [ point_en points b ])

(* La polyligne rééchantillonnée en n points régulièrement espacés le long de sa longueur. *)
let reechantillonne points n =
  let longueurs = Array.init (Array.length points - 1) (fun i -> norme (points.(i + 1) -: points.(i))) in
  let cumul = Conforme.cumul_depuis_zero longueurs in
  let total = cumul.(Array.length cumul - 1) in
  if total = 0. then Array.make n points.(0)
  else
    let xs = Array.map (fun p -> p.x) points and ys = Array.map (fun p -> p.y) points in
    Array.map (fun s -> { x = Conforme.interp s cumul xs; y = Conforme.interp s cumul ys }) (Conforme.linspace 0. total n)

(* La ligne brisée des points, chaque coude arrondi par un congé (arc tangent aux deux segments, sur au plus [part] du
   plus court). depart (arrivee) : direction unitaire de la courbe qui arrive au premier point (qui part du dernier) ;
   le début du premier segment (la fin du dernier) devient alors une paire d'arcs tangente à cette courbe : pas de coin
   à la jonction. Chaque arrondi reste dans un disque centré sur son coude de rayon 0,9 × la distance au trou le plus
   proche : il ne passe jamais de l'autre côté d'un trou. *)
let arrondit ?(part = 0.5) ?depart ?arrivee ~trous points =
  let n = Array.length points in
  let rayon_libre v = 0.9 *. Array.fold_left (fun a t -> Float.min a (norme (t -: v))) Float.infinity trous in
  let dessin = ref [ [| points.(0) |] ] in
  (match depart with
  | Some d when n > 1 ->
      let corde = points.(1) -: points.(0) in
      let lg = norme corde in
      if lg > 1e-9 && scalaire d ((1. /. lg) *: corde) < 1. -. 1e-9 then begin
        let c = Float.min (part *. lg) (rayon_libre points.(0) /. 2.) in
        let u = (1. /. lg) *: corde in
        dessin := [ Tresses.deux_arcs points.(0) d (points.(0) +: (c *: u)) u ]
      end
  | _ -> ());
  for i = 1 to n - 2 do
    let a = points.(i - 1) and v = points.(i) and b = points.(i + 1) in
    let la = norme (a -: v) and lb = norme (b -: v) in
    if la < 1e-9 || lb < 1e-9 then dessin := [| v |] :: !dessin
    else
      let ua = (1. /. la) *: (a -: v) and ub = (1. /. lb) *: (b -: v) in
      if scalaire ua ub < -1. +. 1e-9 then dessin := [| v |] :: !dessin
      else
        let c = Float.min (part *. Float.min la lb) (rayon_libre v) in
        dessin := Tresses.deux_arcs (v +: (c *: ua)) (oppose ua) (v +: (c *: ub)) ub :: !dessin
  done;
  let fin =
    match arrivee with
    | Some d when n > 1 ->
        let corde = points.(n - 1) -: points.(n - 2) in
        let lg = norme corde in
        if lg > 1e-9 && scalaire d ((1. /. lg) *: corde) < 1. -. 1e-9 then
          let c = Float.min (part *. lg) (rayon_libre points.(n - 1) /. 2.) in
          let u = (1. /. lg) *: corde in
          Some (Tresses.deux_arcs (points.(n - 1) -: (c *: u)) u points.(n - 1) d)
        else None
    | _ -> None
  in
  let fin = match fin with Some arcs -> arcs | None -> [| points.(n - 1) |] in
  Array.concat (List.rev (fin :: !dessin))

(* Coupe la polyligne là où elle traverse successivement les arêtes données (une traversée par arête, dans l'ordre) ;
   les morceaux (un de plus que d'arêtes), ou None si une traversée manque. *)
let decoupe_aux_aretes points aretes pos =
  let n = Array.length points in
  let rec suite debut morceaux = function
    | [] -> Some (List.rev (morceau points debut (float_of_int (n - 1)) :: morceaux))
    | arete :: reste -> (
        let u, v = (arete : Arete.t :> sommet * sommet) in
        let s = pos.(v) -: pos.(u) in
        let cote = Array.map (fun p -> (s.x *. (p.y -. pos.(u).y)) -. (s.y *. (p.x -. pos.(u).x))) points in
        let trouve = ref None and k = ref (int_of_float debut) in
        while !trouve = None && !k < n - 1 do
          (if cote.(!k) >= 0. <> (cote.(!k + 1) >= 0.) then
             let t = cote.(!k) /. (cote.(!k) -. cote.(!k + 1)) in
             let xk = points.(!k) +: (t *: (points.(!k + 1) -: points.(!k))) in
             let w = scalaire (xk -: pos.(u)) s /. scalaire s s in
             if 0. < w && w < 1. && float_of_int !k +. t > debut then trouve := Some (float_of_int !k +. t));
          incr k
        done;
        match !trouve with None -> None | Some t -> suite t (morceau points debut t :: morceaux) reste)
  in
  suite 0. [] aretes

type raccord = {
  image_de : int array;  (** pour chaque image de la fenêtre, l'indice de son instant *)
  etats : (Triangle.t list * point array) array;  (** triangles (après retournements) et positions, à chaque instant *)
  i_trous : sommet list;
  i_clou : sommet;
  depart : point array list array;  (** le dessin de départ transporté jusqu'à chaque instant *)
  arrivee : point array list array;  (** le dessin d'arrivée ramené à chaque instant *)
  reduction : float -> float;
  tournants : sommet list;  (** les deux trous qui tournent (sommets du maillage) *)
  i_satellites : sommet list;  (** les sommets ajoutés autour des deux trous qui tournent (aucun par défaut) *)
  voisins : sommet option * sommet option;  (** les trous L et R, voisins des deux qui tournent (aucun au bord de l'image) *)
  phases : float * float * float * float;
}

(* Le raccord d'une lettre entre les temps s_a (dessin de départ, réduction r_a) et s_b (dessin d'arrivée, r_b).
   positions s r : positions à l'écran des trous physiques au temps s avec la réduction r ; temps : les temps des
   images de la fenêtre, croissants, strictement entre s_a et s_b ; tournants : les deux trous physiques qui
   tournent. Le maillage (bord convexe, trous, clou) suit les trous de sous-pas en sous-pas en retournant ses arêtes ;
   le dessin de départ est transporté vers l'avant, celui d'arrivée vers l'arrière (RaccordTriangule du Python). *)
let raccord ?(sous_pas = 8) ?(phases = (0., 0.35, 0.65, 1.)) ?(satellites = 0) ~positions ~clou ~largeur ~hauteur ~s_a ~r_a ~depart ~s_b ~r_b
    ~arrivee ~temps ~tournants () =
  let reduction s = r_a +. ((r_b -. r_a) *. (s -. s_a) /. (s_b -. s_a)) in
  let reperes = Array.concat [ [| s_a |]; temps; [| s_b |] ] in
  let instants = ref [ s_a ] and image_de = ref [] in
  for j = 0 to Array.length reperes - 2 do
    for k = 1 to sous_pas do
      instants := (reperes.(j) +. ((reperes.(j + 1) -. reperes.(j)) *. float_of_int k /. float_of_int sous_pas)) :: !instants
    done;
    if j < Array.length temps then image_de := (List.length !instants - 1) :: !image_de
  done;
  let instants = Array.of_list (List.rev !instants) and image_de = Array.of_list (List.rev !image_de) in
  let physiques = positions s_a r_a in
  let nb_trous = Array.length physiques in
  (* Essai : [satellites] sommets supplémentaires sur un cercle autour de chacun des deux trous qui tournent, qui les suivent
     (même décalage tout au long de la fenêtre) ; le rayon est 30 % de la plus petite distance de ces trous à un autre trou
     pendant la fenêtre. Le maillage a ainsi beaucoup d'arêtes courtes autour d'eux, et un lacet qui s'enroule y fait un
     polygone à beaucoup de côtés. *)
  let decalages =
    if satellites <= 0 then []
    else
      let dmin = ref Float.infinity in
      Array.iter
        (fun s ->
          let p = positions s (reduction s) in
          List.iter (fun t -> Array.iteri (fun u q -> if u <> t then dmin := Float.min !dmin (norme (q -: p.(t)))) p) tournants)
        instants;
      let rayon = 0.3 *. !dmin in
      List.concat_map
        (fun t ->
          List.init satellites (fun k ->
              let angle = (2. *. Float.pi *. (float_of_int k +. 0.5)) /. float_of_int satellites in
              (t, { x = rayon *. cos angle; y = rayon *. sin angle })))
        tournants
  in
  let aux_depart = List.map (fun (t, d) -> physiques.(t) +: d) decalages in
  let m, tous, i_clou = maillage_du_raccord (Array.to_list physiques @ aux_depart) (Some clou) largeur hauteur in
  let i_trous = List.filteri (fun q _ -> q < nb_trous) tous and i_satellites = List.filteri (fun q _ -> q >= nb_trous) tous in
  let i_clou = Option.get i_clou in
  let etats = Array.make (Array.length instants) (Maillage.triangles m, m.pos) in
  let m = ref m in
  for j = 1 to Array.length instants - 1 do
    let s = instants.(j) in
    let nouvelles = Array.copy !m.Maillage.pos in
    let p = positions s (reduction s) in
    List.iteri (fun q v -> nouvelles.(v) <- p.(q)) i_trous;
    List.iteri (fun q v -> let t, d = List.nth decalages q in nouvelles.(v) <- p.(t) +: d) i_satellites;
    let deplace = Maillage.deplace !m nouvelles in
    if not (Maillage.valide deplace) then failwith "triangle retourné pendant le raccord : augmenter sous_pas";
    let apres, _ = Maillage.delaunay deplace [] in
    m := apres;
    etats.(j) <- (Maillage.triangles apres, apres.pos)
  done;
  let nb = Array.length instants in
  let dep = Array.make nb depart and arr = Array.make nb arrivee in
  for j = 1 to nb - 1 do
    let triangles, avant = etats.(j - 1) in
    dep.(j) <- transporte dep.(j - 1) triangles avant (snd etats.(j))
  done;
  for j = nb - 1 downto 1 do
    let triangles, avant = etats.(j - 1) in
    arr.(j - 1) <- transporte arr.(j) triangles (snd etats.(j)) avant
  done;
  { image_de; etats; i_trous; i_clou; depart = dep; arrivee = arr; reduction;
    tournants = List.map (List.nth i_trous) tournants; i_satellites;
    voisins =
      (match tournants with
       | [ a; b ] ->
           ( (if a > 0 then Some (List.nth i_trous (a - 1)) else None),
             if b + 1 < List.length i_trous then Some (List.nth i_trous (b + 1)) else None )
       | _ -> (None, None));
    phases }

let reduction r s = r.reduction s

(* Direction unitaire d'une courbe à son début (en partant, au_debut) ou à sa fin (en arrivant). *)
let tangente courbe au_debut =
  let pts = if au_debut then Array.init (Array.length courbe) (fun i -> courbe.(Array.length courbe - 1 - i)) else courbe in
  let n = Array.length pts in
  let rec cherche k =
    if k < 0 then None
    else
      let d = pts.(n - 1) -: pts.(k) in
      let l = norme d in
      if l > 1e-6 then Some ((if au_debut then -1. else 1.) *: ((1. /. l) *: d)) else cherche (k - 1)
  in
  cherche (n - 2)

(* Les arêtes du maillage à l'image f de la fenêtre, comme couples de points (pour les montrer). *)
let aretes_du_maillage r f =
  let triangles, pos = r.etats.(r.image_de.(f)) in
  let m = Maillage.cree pos triangles in
  Aretes.fold (fun arete _ acc -> let u, v = (arete : Arete.t :> sommet * sommet) in (pos.(u), pos.(v)) :: acc) (Maillage.aretes m) []

let melange q a b = ((1. -. q) *: a) +: (q *: b)

(* Les arêtes « fantômes » au poids donné : les arêtes entre trous qui portent la plus claire des deux lignes de construction, la ligne
   de départ L–A–B–R (opacité 1 − poids) ou celle d'arrivée L–B–A–R (opacité poids). La plus claire (opacité <= 1/2) n'impose rien :
   ni sa tangente ni sa position. *)
let aretes_fantomes r poids =
  match (r.tournants, r.voisins) with
  | [ a; b ], (l, rr) ->
      let e x y = match (x, y) with Some x, Some y -> [ Arete.v x y ] | _ -> [] in
      (if poids >= 0.5 then e l (Some a) @ e (Some b) rr else []) @ if poids <= 0.5 then e l (Some b) @ e (Some a) rr else []
  | _ -> []

(* Les arêtes entre trous qui portent la plus foncée des lignes de construction, au poids donné : A–B (toujours pleine) et la ligne
   de départ (L–A, B–R) avant le milieu, celle d'arrivée (L–B, A–R) après. Une rencontre sur elles impose sa position et sa
   tangente (l'arc passe perpendiculairement à la ligne). A–B n'est pas dans la liste : un pied sur A–B impose seulement son
   passage (sa tangente imposée faisait des S quand la courbe l'aborde en oblique). *)
let aretes_sombres r poids =
  match (r.tournants, r.voisins) with
  | [ a; b ], (l, rr) ->
      let e x y = match (x, y) with Some x, Some y -> [ Arete.v x y ] | _ -> [] in
      (if poids < 0.5 then e l (Some a) @ e (Some b) rr else []) @ if poids > 0.5 then e l (Some b) @ e (Some a) rr else []
  | _ -> []

(* La forme libre d'une suite de pieds (le départ et l'arrivée de la suite, et les pieds intérieurs avec l'arête qu'ils traversent) :
   la courbe n'est plus une ligne brisée qui se plie à chaque pied : seuls les pieds sur une arête sombre sont des « ancres »
   (position et tangente imposées) ; entre deux ancres, les pieds libres sont reliés par la ligne brisée aux coudes arrondis.
   - le départ et l'arrivée de la suite : la tangente de la courbe voisine (avant, apres), sinon la corde ;
   - un pied sur une arête sombre impose sa position et sa tangente : la perpendiculaire à l'arête, dans le sens de la marche ;
   - un pied sur une autre arête (côtés du clou ou du bord) n'est pas une ancre : il reste un point de passage de la ligne brisée.
   Les points fantômes (pieds sur l'arête la plus claire) ne sont pas là : [sans_pieds_fantomes] les a retirés avant. Aux ancres, la
   courbe est tangente (une paire d'arcs, [arrondit]) : pas de coin. *)
let forme_libre ~sombre ~pos ~trous ?avant ?apres pieds aretes =
  let n = Array.length pieds in
  if n < 2 then pieds
  else
    let unitaire d = let l = norme d in if l < 1e-12 then None else Some ((1. /. l) *: d) in
    let aretes = Array.of_list aretes in
    (* les ancres : le départ, l'arrivée, et les pieds posés sur une arête sombre ; leur tangente (le sens de la marche) *)
    let tangente_sombre i =
      if i - 1 < Array.length aretes && sombre aretes.(i - 1) then
        let u, v = (aretes.(i - 1) : Arete.t :> sommet * sommet) in
        let s = pos.(v) -: pos.(u) in
        match (unitaire { x = -.s.y; y = s.x }, unitaire (pieds.(i + 1) -: pieds.(i - 1))) with
        | Some nrm, Some corde -> Some (if scalaire nrm corde >= 0. then nrm else oppose nrm)
        | _ -> None
      else None
    in
    let ancres = ref [ (0, avant) ] in
    for i = 1 to n - 2 do
      match tangente_sombre i with Some t -> ancres := (i, Some t) :: !ancres | None -> ()
    done;
    let ancres = Array.of_list (List.rev ((n - 1, apres) :: !ancres)) in
    (* entre deux ancres, la ligne brisée des pieds libres aux coudes arrondis (des cercles, jamais d'à-coup de courbure),
       tangente aux ancres. Essai écarté : remplacer la paire d'arcs de départ par un tronçon droit dans la direction imposée
       (point virtuel sur la tangente, un seul congé) : plus de S, mais des coins marqués et des croisements (3 images
       douteuses sur 1 -2 1 -2, aucune avec la paire d'arcs). *)
    let morceaux =
      List.init (Array.length ancres - 1) (fun k ->
          let i, ti = ancres.(k) and j, tj = ancres.(k + 1) in
          arrondit ?depart:ti ?arrivee:tj ~trous (Array.sub pieds i (j - i + 1)))
    in
    Array.concat (List.hd morceaux :: List.map (fun m -> Array.sub m 1 (Array.length m - 1)) (List.tl morceaux))

(* Essai « sans maillage » : les seuls repères d'une suite sont son départ, son arrivée et les pieds sur les lignes de construction
   (les pieds posés sur les autres arêtes du maillage ont été retirés par [sans_pieds_si]). Entre deux repères consécutifs, une paire
   d'arcs (deux_arcs) : un pied sur une ligne sombre impose sa tangente (la perpendiculaire à la ligne, dans le sens de la marche), un pied
   sur A–B seulement son passage (la tangente est la corde de ses voisins). Rien ne retient plus les arcs : ils peuvent être immenses. *)
let forme_arcs ~sombre ~pos ?avant ?apres pieds aretes =
  let n = Array.length pieds in
  if n < 2 then pieds
  else
    let unitaire d = let l = norme d in if l < 1e-12 then None else Some ((1. /. l) *: d) in
    let aretes = Array.of_list aretes in
    let tangente i =
      if i = 0 then (match avant with Some d -> Some d | None -> unitaire (pieds.(1) -: pieds.(0)))
      else if i = n - 1 then (match apres with Some d -> Some d | None -> unitaire (pieds.(n - 1) -: pieds.(n - 2)))
      else
        match unitaire (pieds.(i + 1) -: pieds.(i - 1)) with
        | None -> None
        | Some corde ->
            if i - 1 < Array.length aretes && sombre aretes.(i - 1) then
              let u, v = (aretes.(i - 1) : Arete.t :> sommet * sommet) in
              let s = pos.(v) -: pos.(u) in
              match unitaire { x = -.s.y; y = s.x } with
              | Some nrm -> Some (if scalaire nrm corde >= 0. then nrm else oppose nrm)
              | None -> Some corde
            else Some corde
    in
    let morceaux =
      List.init (n - 1) (fun i ->
          match (tangente i, tangente (i + 1)) with
          | Some t0, Some t1 -> Tresses.deux_arcs pieds.(i) t0 pieds.(i + 1) t1
          | _ -> [| pieds.(i); pieds.(i + 1) |])
    in
    Array.concat (List.hd morceaux :: List.map (fun m -> Array.sub m 1 (Array.length m - 1)) (List.tl morceaux))

(* Fusionne les morceaux consécutifs d'une suite en cordes qui se rejoignent sur une arête [retire] : le pied y est supprimé, la corde
   ne passe plus par ce point. Chaque morceau : (triangle, départ, arrivée, arête de sortie). *)
let sans_pieds_si retire suite =
  let joint p q = Array.append p (Array.sub q 1 (Array.length q - 1)) in
  Array.of_list
    (List.rev
       (Array.fold_left
          (fun acc ((_, pd, pa, a) as x) ->
            match acc with
            | (t, pd0, pa0, Some e) :: reste when retire e -> (t, joint pd0 pd, joint pa0 pa, a) :: reste
            | _ -> x :: acc)
          [] suite))

(* Lacets de l'image f de la fenêtre au poids donné (0 : départ, 1 : arrivée), et les anomalies (lacet, message).
   Chaque lacet est découpé en morceaux entre ses pieds sur les arêtes ; les pieds des deux dessins se correspondent
   un à un. Les pieds glissent sur leurs arêtes entre phases 1 et 2 (l'ordre sur chaque arête est gardé). Les morceaux
   d'un triangle qui touche un des trous qui tournent, ou qui contient un bigone, passent par les cordes : tension
   (phases 0 → 1), glissement en cordes arrondies, courbure (phases 2 → 3) ; les autres passent directement du morceau de
   départ à celui d'arrivée pendant le glissement (le mélange de deux courbes d'un triangle reste dans ce triangle). *)
let lignes ?(sans_fantomes = false) ?(libre = false) ?(sans_maillage = false) r f poids =
  let sans_fantomes = sans_fantomes || libre || sans_maillage in
  let j = r.image_de.(f) in
  let triangles, pos = r.etats.(j) in
  let maillage = Maillage.cree pos triangles in
  let p0, p1, p2, p3 = r.phases in
  let rampe a b = lisse (Float.min 1. (Float.max 0. ((poids -. a) /. (b -. a)))) in
  let tension = rampe p0 p1 and glisse = rampe p1 p2 and courbe = rampe p2 p3 in
  let trous = Array.of_list (List.map (fun v -> pos.(v)) r.i_trous) in
  let anomalies = ref [] and en_cordes = Hashtbl.create 16 in
  (* premier passage : les morceaux de chaque lacet, avec leur triangle (les sommets de leurs deux arêtes) *)
  let decoupes =
    List.mapi
      (fun l (d, a) ->
        let cd, bd = coupe d maillage r.i_clou and ca, ba = coupe a maillage r.i_clou in
        if List.map (fun c -> c.arete) cd <> List.map (fun c -> c.arete) ca then begin
          anomalies := (l, "traversées différentes") :: !anomalies;
          None
        end
        else
          let bornes pts c = Array.of_list ((0. :: List.map (fun c -> c.position) c) @ [ float_of_int (Array.length pts - 1) ]) in
          let bd_ = bornes d cd and ba_ = bornes a ca in
          let sommets =
            Array.of_list (([ r.i_clou ] :: List.map (fun c -> let u, v = (c.arete : Arete.t :> sommet * sommet) in [ u; v ]) cd) @ [ [ r.i_clou ] ])
          in
          let cda = Array.of_list cd in
          Some
            (List.init (Array.length bd_ - 1) (fun k ->
                 let triangle = List.sort_uniq compare (sommets.(k) @ sommets.(k + 1)) in
                 let dedans bornes x = bornes.(k) < x.position && x.position < bornes.(k + 1) in
                 let bigone = List.exists (dedans bd_) bd || List.exists (dedans ba_) ba in
                 if bigone || List.exists (fun t -> List.mem t triangle) (r.tournants @ r.i_satellites) then Hashtbl.replace en_cordes triangle ();
                 ( triangle,
                   reechantillonne (morceau d bd_.(k) bd_.(k + 1)) 60,
                   reechantillonne (morceau a ba_.(k) ba_.(k + 1)) 60,
                   if k < Array.length cda then Some cda.(k).arete else None ))))
      (List.combine r.depart.(j) r.arrivee.(j))
  in
  (* second passage : les formes ; les morceaux en cordes consécutifs forment une suite, tracée en ligne brisée aux
     coudes arrondis, raccordée en tangence aux morceaux courbes voisins *)
  let resultat =
    List.mapi
      (fun l decoupe ->
        match decoupe with
        | None -> if poids < 0.5 then List.nth r.depart.(j) l else List.nth r.arrivee.(j) l
        | Some morceaux ->
            let morceaux = Array.of_list morceaux in
            let nb = Array.length morceaux in
            let courbe_de k =
              let triangle, pd, pa, _ = morceaux.(k) in
              if Hashtbl.mem en_cordes triangle then None else Some (Array.map2 (melange glisse) pd pa)
            in
            let courbes = Array.init nb courbe_de in
            let formes = ref [] and k = ref 0 in
            while !k < nb do
              match courbes.(!k) with
              | Some c ->
                  formes := c :: !formes;
                  incr k
              | None ->
                  let debut = !k in
                  while !k < nb && courbes.(!k) = None do
                    incr k
                  done;
                  let suite = Array.sub morceaux debut (!k - debut) in
                  let suite =
                    if sans_maillage then (
                      (* ne restent que les pieds sur les lignes de construction : A–B et la ligne foncée *)
                      let gardees = (match r.tournants with [ a; b ] -> [ Arete.v a b ] | _ -> []) @ aretes_sombres r poids in
                      sans_pieds_si (fun e -> not (List.mem e gardees)) suite)
                    else if sans_fantomes then (let f = aretes_fantomes r poids in sans_pieds_si (fun e -> List.mem e f) suite)
                    else suite
                  in
                  let _, pd0, pa0, _ = suite.(0) in
                  let pieds =
                    Array.append [| melange glisse pd0.(0) pa0.(0) |]
                      (Array.map (fun (_, pd, pa, _) -> melange glisse pd.(Array.length pd - 1) pa.(Array.length pa - 1)) suite)
                  in
                  let avant = if debut > 0 then Option.bind courbes.(debut - 1) (fun c -> tangente c false) else None in
                  let apres = if !k < nb then Option.bind courbes.(!k) (fun c -> tangente c true) else None in
                  let cordes =
                    if sans_maillage then
                      let sombres = aretes_sombres r poids in
                      let aretes = List.filter_map (fun (_, _, _, a) -> a) (Array.to_list (Array.sub suite 0 (Array.length suite - 1))) in
                      forme_arcs ~sombre:(fun e -> List.mem e sombres) ~pos ?avant ?apres pieds aretes
                    else if libre then
                      let sombres = aretes_sombres r poids in
                      let aretes = List.filter_map (fun (_, _, _, a) -> a) (Array.to_list (Array.sub suite 0 (Array.length suite - 1))) in
                      forme_libre ~sombre:(fun e -> List.mem e sombres) ~pos ~trous ?avant ?apres pieds aretes
                    else arrondit ?depart:avant ?arrivee:apres ~trous pieds
                  in
                  let forme =
                    if 0. < glisse && glisse < 1. then cordes
                    else
                      (* mélange triangle par triangle : les cordes arrondies coupées aux arêtes des pieds, chaque
                         morceau mélangé avec celui du même triangle *)
                      let vraie (_, pd, pa, _) = if glisse = 0. then pd else pa in
                      let poids_cordes = if glisse = 0. then tension else 1. -. courbe in
                      let aretes = List.filter_map (fun (_, _, _, a) -> a) (Array.to_list (Array.sub suite 0 (Array.length suite - 1))) in
                      let parts =
                        match decoupe_aux_aretes cordes aretes pos with
                        | Some parts -> parts
                        | None -> Array.to_list (Array.map (fun x -> let v = vraie x in [| v.(0); v.(Array.length v - 1) |]) suite)
                      in
                      let melanges =
                        List.map2
                          (fun x rr ->
                            let v = vraie x in
                            let n = max (Array.length v) (Array.length rr) in
                            Array.map2 (melange poids_cordes) (reechantillonne v n) (reechantillonne rr n))
                          (Array.to_list suite) parts
                      in
                      Array.concat (List.hd melanges :: List.map (fun m -> Array.sub m 1 (Array.length m - 1)) (List.tl melanges))
                  in
                  formes := forme :: !formes
            done;
            let formes = List.rev !formes in
            Array.concat (List.hd formes :: List.map (fun m -> Array.sub m 1 (Array.length m - 1)) (List.tl formes)))
      decoupes
  in
  (resultat, List.rev !anomalies)
