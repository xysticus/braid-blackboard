(* Un escargot fait de rubans. Voir escargot.mli. Les calculs suivent l'ordre des opérations du Python (même
   arrondi) : le film est identique octet pour octet. *)

open Geometrie
open Triangulation

let lisse x =
  let x = Float.min (Float.max x 0.) 1. in
  x *. x *. (3. -. (2. *. x))

type t = {
  largeur : float;
  hauteur : float;
  e : float;
  anneau : int;
  tours : float;
  n : int;
  y_axe0 : float;
  depart : point array;
  maillage : Maillage.t;
  voyageurs : sommet array;
  fixes : sommet array;
  courbes : courbe list;
  ecart : float;
}

let tension escargot taux =
  { escargot with
    courbes = Film.tend_courbes ~portee_sinus:(3. *. escargot.ecart) escargot.maillage escargot.courbes taux escargot.ecart }

let cree ?(largeur = 960.) ?(hauteur = 640.) ?(ecart = 7.) ?(anneau = 4) ?(tours = 3.) () =
  let e = largeur /. 960. in
  let n = anneau + 3 in
  let y_axe0 = 470. *. e in
  (* f_n le plus à gauche *)
  let fixes = List.init n (fun k -> { x = (200. +. (16. *. float (n - 1 - k))) *. e; y = y_axe0 }) in
  let depart =
    Array.append
      (Array.init anneau (fun k -> { x = (340. +. (50. *. float k)) *. e; y = y_axe0 }))
      (Array.map (fun x -> { x = x *. e; y = y_axe0 }) [| 570.; 620.; 660. |])
  in
  let maillage, indices, _ = Raccord.maillage_du_raccord (Array.to_list depart @ fixes) None largeur hauteur in
  let indices = Array.of_list indices in
  let voyageurs = Array.sub indices 0 n and fixes = Array.sub indices n n in
  (* arcs de départ : demi-ellipses emboîtées sous l'axe, de f_k à m_k *)
  let pos = maillage.Maillage.pos in
  let courbes =
    List.init n (fun k ->
        let f = fixes.(k) and m = voyageurs.(k) in
        let p = pos.(f) and q = pos.(m) in
        let c = (p.x +. q.x) /. 2. and r = (q.x -. p.x) /. 2. in
        let points =
          Array.map (fun phi -> { x = c +. (r *. Float.cos phi); y = y_axe0 +. (0.5 *. r *. Float.sin phi) })
            (Tresses.linspace Float.pi 0. 300)
        in
        Arcs.coupe_arc points maillage f m)
  in
  let escargot =
    { largeur; hauteur; e; anneau; tours; n; y_axe0; depart; maillage; voyageurs; fixes; courbes; ecart = ecart *. e }
  in
  let rec tend k escargot = if k = 0 then escargot else tend (k - 1) (tension escargot 0.3) in
  tend 100 escargot

(* La chorégraphie. *)

let centre_coquille escargot t =
  let e = escargot.e in
  let monte = lisse (t /. 2.5) in
  { x = (400. +. (40. *. monte)) *. e; y = escargot.y_axe0 -. ((20. +. (105. *. monte)) *. e) }

let rayon_anneau escargot t = (12. +. (14. *. lisse ((t -. 2.5) /. 6.5))) *. escargot.e
let tours_faits escargot t = escargot.tours *. lisse ((t -. 2.5) /. 6.5)

(* (1 - u) p + u q *)
let melange u p q = ((1. -. u) *: p) +: (u *: q)

let choregraphie escargot t =
  let e = escargot.e and m = escargot.anneau in
  (* [a * (x, y) * e] du Python : (a x) e, pas a (x e) *)
  let fois a (x, y) = { x = a *. x *. e; y = a *. y *. e } in
  (* l'anneau : d'abord en demi-cercle ouvert vers le bas, dans l'ordre de l'axe (pas de croisement en montant),
     puis en cercle régulier qui tourne (sens trigonométrique à l'écran : la spirale s'ouvre vers l'arrière) *)
  let sortie = lisse (t /. 2.5) and cercle = lisse ((t -. 2.) /. 1.5) in
  let c = centre_coquille escargot t and r = rayon_anneau escargot t in
  let rotation = 2. *. Float.pi *. tours_faits escargot t in
  let coquille =
    Array.init m (fun j ->
        let demi = Float.pi -. (Float.pi *. float j /. float (m - 1)) (* de gauche à droite, par le haut *)
        and regulier = Float.pi -. (2. *. Float.pi *. float j /. float m) in
        let a = ((1. -. cercle) *. demi) +. (cercle *. regulier) +. rotation in
        let cible = c +: (r *: { x = Float.cos a; y = -.Float.sin a }) in
        melange sortie escargot.depart.(j) cible)
  in
  (* la tête : à l'avant, au sol *)
  let avance = lisse (t /. 3.) in
  let tete = ((1. -. avance) *: escargot.depart.(m)) +: fois avance (660., 452.) in
  (* les yeux : devant la tête, puis ils montent en s'écartant (les antennes) *)
  let pousse = lisse ((t -. 8.) /. 3.) in
  let yeux =
    Array.mapi
      (fun j (devant, bout) ->
        let base = ((1. -. avance) *: escargot.depart.(m + 1 + j)) +: fois avance devant in
        ((1. -. pousse) *: base) +: fois pousse bout)
      [| ((690., 458.), (712., 300.)); ((712., 462.), (772., 318.)) |]
  in
  Array.concat [ coquille; [| tete |]; yeux ]

let deplace ?(taux = 0.15) escargot cibles pas_max =
  let depart = Array.map (fun s -> escargot.maillage.Maillage.pos.(s)) escargot.voyageurs in
  let plus_long = ref 0. in
  Array.iteri (fun k c -> plus_long := Float.max !plus_long (norme (c -: depart.(k)))) cibles;
  let n = max 1 (int_of_float (Float.ceil (!plus_long /. pas_max))) in
  let rec boucle s escargot =
    if s > n then escargot
    else begin
      let pos = Array.copy escargot.maillage.Maillage.pos in
      Array.iteri
        (fun k v ->
          let d = cibles.(k) -: depart.(k) in
          pos.(v) <- depart.(k) +: { x = d.x *. float s /. float n; y = d.y *. float s /. float n })
        escargot.voyageurs;
      let maillage = Maillage.deplace escargot.maillage pos in
      if not (Maillage.valide maillage) then failwith "triangle retourné : diminuer pas_max";
      let maillage, courbes = Maillage.delaunay maillage escargot.courbes in
      boucle (s + 1) (tension { escargot with maillage; courbes } taux)
    end
  in
  boucle 1 escargot

let polyligne escargot k = Film.polyligne_de_courbe escargot.maillage (List.nth escargot.courbes k)
