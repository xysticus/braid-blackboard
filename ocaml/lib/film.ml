(* Transport et tension. Voir film.mli pour le rôle de chaque fonction. *)

open Geometrie
open Triangulation

let sens_de_sigma = 1.
let vitesse_par_defaut = 6.

(* Les blocs sont une pile (moyenne, effectif), le dernier bloc en tête ; on fusionne tant que l'avant-dernier
   est au-dessus du dernier. Même calcul que le Python, qui garde les blocs dans une liste. *)
let monotone valeurs =
  let rec fusionne = function
    | (b, nb) :: (a, na) :: reste when a > b ->
      fusionne ((((a *. float na) +. (b *. float nb)) /. float (na + nb), na + nb) :: reste)
    | pile -> pile
  in
  let blocs = List.fold_left (fun pile x -> fusionne ((x, 1) :: pile)) [] valeurs in
  List.concat_map (fun (moyenne, n) -> List.init n (fun _ -> moyenne)) (List.rev blocs)

type disposition = { abscisses : float array; ecart : float }

type t = {
  hauteur : float;
  largeur : float;
  nb_trous : int;
  dispositions : disposition array;
  milieux : disposition array;
  etape : int;
  maillage : Maillage.t;
  trous : sommet array;
  clou : sommet;
  haut : sommet array;
  bas : sommet array;
  decalage_bas : float;
  place_du_clou : int * float;
  y_axe : float;
  courbes : courbe list;
}

let borne x a b = Float.min (Float.max x a) b

(* Un pas de tension, en deux temps comme le Python.
   1. Pour chaque point d'arête, sa nouvelle place souhaitée et le sinus de l'angle sous lequel le brin traverse
      l'arête ; tout est calculé sur l'état de départ, rangé par arête.
   2. Arête par arête : les points gardent leur ordre et leur espacement minimal (régression monotone bornée). *)
let tend_courbes ?degagement ?(portee_sinus = 0.) m courbes taux ecart =
  let degagement = Option.value degagement ~default:ecart in
  let pos = m.Maillage.pos in
  let courbes = Array.of_list (List.map Array.of_list courbes) in
  let par_arete = Hashtbl.create 64 in
  Array.iteri
    (fun k courbe ->
      let points = if portee_sinus > 0. then Array.map (Maillage.position m) courbe else [||] in
      Array.iteri
        (fun i n ->
          match n with
          | Sommet _ -> ()
          | Sur_arete (e, w) ->
            let u, v = (e : Arete.t :> sommet * sommet) in
            let d = pos.(v) -: pos.(u) in
            let p = Maillage.position m courbe.(i - 1) and q = Maillage.position m courbe.(i + 1) in
            let den = croix d (q -: p) in
            (* la place où p, le point et q sont alignés : intersection de la corde [p, q] avec l'arête *)
            let cible = if Float.abs den > 1e-9 then croix (p -: pos.(u)) (q -: p) /. den else w in
            let sinus =
              if portee_sinus > 0. then begin
                let a = ref (i - 1) and b = ref (i + 1) in
                while !a > 0 && norme (points.(!a) -: points.(i)) < portee_sinus do decr a done;
                while !b < Array.length courbe - 1 && norme (points.(!b) -: points.(i)) < portee_sinus do incr b done;
                let corde = points.(!b) -: points.(!a) in
                Float.abs (croix d corde) /. Float.max (norme d *. norme corde) 1e-12
              end
              else Float.abs den /. Float.max (norme d *. norme (q -: p)) 1e-12
            in
            let souhait = w +. (taux *. (borne cible 0. 1. -. w)) in
            Hashtbl.replace par_arete e
              ((souhait, k, i, sinus) :: Option.value (Hashtbl.find_opt par_arete e) ~default:[]))
        courbe)
    courbes;
  Hashtbl.iter
    (fun e liste ->
      let u, v = (e : Arete.t :> sommet * sommet) in
      let longueur = norme (pos.(v) -: pos.(u)) in
      let liste = Array.of_list (List.sort compare liste) in
      let m = Array.length liste in
      let sinus j = let _, _, _, s = liste.(j) in s in
      let marge = Float.min degagement (0.3 *. longueur) in
      (* écart le long de l'arête entre deux voisins : ecart / sinus, pour qu'ils restent à ecart l'un de l'autre
         perpendiculairement aux brins même si ceux-ci traversent l'arête en biais *)
      let ecarts = Array.init (max 0 (m - 1)) (fun j -> ecart /. Float.max ((sinus j +. sinus (j + 1)) /. 2.) 0.3) in
      let place = Float.max (longueur -. (2. *. marge)) 0. in
      let somme = Array.fold_left ( +. ) 0. ecarts in
      let dispo = place *. float m /. float (m + 1) in
      let ecarts = if somme > dispo then Array.map (fun g -> g *. dispo /. somme) ecarts else ecarts in
      let cumul = Array.make m 0. in
      for j = 1 to m - 1 do cumul.(j) <- cumul.(j - 1) +. ecarts.(j - 1) done;
      let total = if m = 0 then 0. else cumul.(m - 1) in
      let cibles = List.init m (fun j -> let souhait, _, _, _ = liste.(j) in (souhait *. longueur) -. cumul.(j)) in
      List.iteri
        (fun j x ->
          let final = Float.min (Float.max x marge) (longueur -. marge -. total) +. cumul.(j) in
          let _, k, i, _ = liste.(j) in
          courbes.(k).(i) <- Sur_arete (e, final /. longueur))
        (monotone cibles))
    par_arete;
  Array.to_list (Array.map Array.to_list courbes)

let tend ?degagement ?portee_sinus film taux ecart =
  { film with courbes = tend_courbes ?degagement ?portee_sinus film.maillage film.courbes taux ecart }

let abscisses film u =
  let a = film.dispositions.(film.etape) and mi = film.milieux.(film.etape)
  and b = film.dispositions.(film.etape + 1) in
  let d0, d1, v = if u <= 0.5 then (a, mi, 2. *. u) else (mi, b, (2. *. u) -. 1.) in
  { abscisses = Array.map2 (fun x0 x1 -> ((1. -. v) *. x0) +. (v *. x1)) d0.abscisses d1.abscisses;
    ecart = ((1. -. v) *. d0.ecart) +. (v *. d1.ecart) }

let signe_de (sigma : Tresses.sigma Tresses.lettre) =
  match sigma.Tresses.signe with Tresses.Plus -> 1. | Tresses.Moins -> -1.

let trous_au_temps film sigma u =
  let i = sigma.Tresses.indice - 1 in
  let x = (abscisses film u).abscisses in
  let milieu = (x.(i) +. x.(i + 1)) /. 2. and r = (x.(i + 1) -. x.(i)) /. 2. in
  let theta = sens_de_sigma *. signe_de sigma *. Float.pi *. u in
  let positions = Array.map (fun xj -> { x = xj; y = film.y_axe }) x in
  positions.(i) <- { x = milieu -. (r *. Float.cos theta); y = film.y_axe -. (r *. Float.sin theta) };
  positions.(i + 1) <- { x = milieu +. (r *. Float.cos theta); y = film.y_axe +. (r *. Float.sin theta) };
  (positions, x, milieu, r, theta)

let place film sigma u =
  let i = sigma.Tresses.indice - 1 and n = film.nb_trous in
  let pos = Array.copy film.maillage.Maillage.pos in
  let positions, x, milieu, r, theta = trous_au_temps film sigma u in
  Array.iteri (fun j h -> pos.(h) <- positions.(j)) film.trous;
  (* les sommets des bords se croisent sans jamais se rejoindre *)
  let ecart = Float.hypot (r *. Float.cos theta) (0.4 *. r *. Float.sin theta) in
  let bords = Array.copy x in
  bords.(i) <- milieu -. ecart;
  bords.(i + 1) <- milieu +. ecart;
  List.iter
    (fun (rangee, decalage) ->
      for j = 0 to n - 1 do
        let s = rangee.(j + 1) in
        pos.(s) <- { (pos.(s)) with x = bords.(j) +. decalage }
      done)
    [ (film.haut, decalage_bord); (film.bas, film.decalage_bas) ];
  let j, f = film.place_du_clou in
  let xa = pos.(film.bas.(j)).x and xb = pos.(film.bas.(j + 1)).x in
  pos.(film.clou) <- { (pos.(film.clou)) with x = xa +. (f *. (xb -. xa)) };
  if u = 1. then begin
    let xs1 = film.dispositions.(film.etape + 1).abscisses in
    let a = film.trous.(i) and b = film.trous.(i + 1) in
    pos.(a) <- { x = xs1.(i + 1); y = film.y_axe };
    pos.(b) <- { x = xs1.(i); y = film.y_axe };
    let trous = Array.copy film.trous in
    trous.(i) <- b;
    trous.(i + 1) <- a;
    { film with maillage = Maillage.deplace film.maillage pos; trous; etape = film.etape + 1 }
  end
  else { film with maillage = Maillage.deplace film.maillage pos }

let chemin_des_trous ?(echantillons = 800) film sigma =
  let us = Tresses.linspace 0. 1. (echantillons + 1) in
  let positions = Array.map (fun u -> let p, _, _, _, _ = trous_au_temps film sigma u in p) us in
  let longueurs = Array.make (echantillons + 1) 0. in
  for k = 1 to echantillons do
    let pas = ref 0. in
    Array.iteri (fun j p -> pas := !pas +. norme (p -: positions.(k - 1).(j))) positions.(k);
    longueurs.(k) <- longueurs.(k - 1) +. !pas
  done;
  (us, longueurs)

(* np.interp : interpolation linéaire de x dans la table (xp, fp), xp croissant. *)
let interp x xp fp =
  let n = Array.length xp in
  if x <= xp.(0) then fp.(0)
  else if x >= xp.(n - 1) then fp.(n - 1)
  else begin
    (* plus grand j tel que xp.(j) <= x *)
    let rec cherche a b = if b - a <= 1 then a else let c = (a + b) / 2 in if xp.(c) <= x then cherche c b else cherche a c in
    let j = cherche 0 (n - 1) in
    let pente = (fp.(j + 1) -. fp.(j)) /. (xp.(j + 1) -. xp.(j)) in
    (pente *. (x -. xp.(j))) +. fp.(j)
  end

(* round du Python : au plus proche, et à l'entier pair en cas d'égalité. *)
let arrondi x =
  let r = Float.round x in
  if Float.abs (x -. Float.trunc x) = 0.5 then 2. *. Float.round (x /. 2.) else r

let lettre ?images ?(sous_pas = 2) ?(taux = 0.15) ?vitesse ?rendu film sigma =
  let us, longueurs = chemin_des_trous film sigma in
  let total = longueurs.(Array.length longueurs - 1) in
  let images =
    match images with
    | Some n -> n
    | None ->
      let vitesse = Option.value vitesse ~default:(vitesse_par_defaut *. film.largeur /. 800.) in
      max 4 (int_of_float (arrondi (total /. vitesse)))
  in
  let nb = images * sous_pas in
  let distances = Tresses.linspace 0. total (nb + 1) in
  let rec boucle pas film =
    if pas > nb then film
    else begin
      let u = if pas = nb then 1. else interp distances.(pas) longueurs us in
      let ecart = (abscisses film u).ecart in
      let film = place film sigma u in
      if not (Maillage.valide film.maillage) then failwith "triangle retourné : augmenter sous_pas";
      let maillage, courbes = Maillage.delaunay film.maillage film.courbes in
      let film = tend { film with maillage; courbes } taux ecart in
      (match rendu with Some f when pas mod sous_pas = 0 -> f film ecart | _ -> ());
      boucle (pas + 1) film
    end
  in
  (boucle 1 film, images)

let portions m y_axe courbe =
  let pts = Array.of_list (List.map (Maillage.position m) courbe) in
  let passage i j =
    let p1 = pts.(i) and p2 = pts.(j) in
    if Float.abs (p2.y -. p1.y) > 1e-12 then p1.x +. ((p2.x -. p1.x) *. (y_axe -. p1.y) /. (p2.y -. p1.y)) else p2.x
  in
  let haut = List.filter (fun i -> pts.(i).y <= y_axe) (List.init (Array.length pts) Fun.id) in
  match haut with
  | [] -> []
  | i1 :: _ ->
    let i2 = List.nth haut (List.length haut - 1) in
    [ ((1, i1), passage (i1 - 1) i1); ((i2 + 1, Array.length pts - 1), passage (i2 + 1) i2) ]

let portions_du_clou film courbe = portions film.maillage film.y_axe courbe

let unitaire u = (1. /. norme u) *: u

let polyligne_de_courbe ?(lisse = true) ?(part_du_conge = 0.5) ?clou m courbe =
  let pts = Array.of_list (List.map (Maillage.position m) courbe) in
  if not lisse then pts
  else begin
    (* passages sur l'axe des brins du clou : le premier entre les points i1 - 1 et i1, le dernier entre i2 et
       i2 + 1 ; on y insère deux points de part et d'autre de l'axe *)
    let insertions, ecart =
      match clou with
      | None -> ([], 0.)
      | Some (y_axe, ecart) ->
        (List.mapi (fun n ((debut, fin), x) -> ((if n = 0 then fin else debut), { x; y = y_axe })) (portions m y_axe courbe),
         ecart)
    in
    let insere pts (i, q) =
      let voisins = Float.min (Float.abs (q.y -. pts.(i - 1).y)) (Float.abs (q.y -. pts.(i).y)) in
      if voisins < 1e-6 then pts
      else begin
        (* direction au passage : la verticale si le brin traverse l'axe à moins de 45° de la verticale (poids
           décroissant avec l'angle), sinon celle du brin *)
        let segment = unitaire (pts.(i) -: pts.(i - 1)) in
        let verticale = { x = 0.; y = Float.copy_sign 1. segment.y } in
        let poids = Float.max 0. (1. -. (Float.acos (Float.min 1. (Float.abs segment.y)) /. (Float.pi /. 4.))) in
        let d = unitaire ((poids *: verticale) +: ((1. -. poids) *: segment)) in
        let delta = Float.min ecart (0.3 *. voisins) /. Float.max (Float.abs d.y) 1e-3 in
        Array.concat [ Array.sub pts 0 i; [| q -: (delta *: d); q +: (delta *: d) |]; Array.sub pts i (Array.length pts - i) ]
      end
    in
    (* de la dernière insertion à la première : les indices des précédentes restent bons *)
    let pts = List.fold_left insere pts (List.stable_sort (fun (i, _) (j, _) -> compare j i) insertions) in
    let n = Array.length pts in
    let coude k =
      let a = pts.(k - 1) and v = pts.(k) and b = pts.(k + 1) in
      let la = norme (a -: v) and lb = norme (b -: v) in
      if la < 1e-9 || lb < 1e-9 then [| v |]
      else
        let ua = (1. /. la) *: (a -: v) and ub = (1. /. lb) *: (b -: v) in
        if scalaire ua ub < -1. +. 1e-9 then [| v |] (* pas de coude *)
        else
          let c = part_du_conge *. Float.min la lb in
          Tresses.deux_arcs (v +: (c *: ua)) (oppose ua) (v +: (c *: ub)) ub
    in
    Array.concat ([ [| pts.(0) |] ] @ List.init (max 0 (n - 2)) (fun k -> coude (k + 1)) @ [ [| pts.(n - 1) |] ])
  end

let polyligne ?lisse ?part_du_conge film k =
  polyligne_de_courbe ?lisse ?part_du_conge ~clou:(film.y_axe, film.dispositions.(film.etape).ecart) film.maillage
    (List.nth film.courbes k)

let polylignes ?lisse film =List.init (List.length film.courbes) (polyligne ?lisse film)
let positions_des_trous film = Array.map (fun s -> film.maillage.Maillage.pos.(s)) film.trous

let mots ?lisse film =
  let trous = List.sort compare (Array.to_list (positions_des_trous film)) in
  List.map (fun p -> Tresses.lit_mot p trous) (polylignes ?lisse film)

(* Le constructeur. *)

(* La largeur de chaque intervalle de l'axe (y compris les deux des bords) est proportionnelle à 1 + le nombre de
   brins qui le traversent : l'écart entre deux points consécutifs de l'axe est le même partout. *)
let disposition nb_trous largeur (etat : Tresses.etat) =
  let comptes = Array.make (nb_trous + 1) 0 in
  List.iter (Array.iter (fun x -> let k = Tresses.intervalle x etat.trous in comptes.(k) <- comptes.(k) + 1)) etat.lacets;
  let ecart = largeur /. float (Array.fold_left (fun s c -> s + c + 1) 0 comptes) in
  let cumul = ref 0. in
  { abscisses = Array.init nb_trous (fun k -> cumul := !cumul +. (float (comptes.(k) + 1) *. ecart); !cumul); ecart }

let cree ?(hauteur = 800.) ?(largeur = 800.) ?(tension = 400) tresse =
  let e = largeur /. 400. in
  let nb_trous = 1 + List.fold_left (fun m (l : Tresses.sigma Tresses.lettre) -> max m l.indice) 1 tresse in
  let prefixe k = List.filteri (fun j _ -> j < k) tresse in
  let etat k = Tresses.etat_de_tresse ~nb_trous (prefixe k) in
  let dispositions = Array.init (List.length tresse + 1) (fun k -> disposition nb_trous largeur (etat k)) in
  (* au milieu de chaque lettre : l'état non réduit compte les brins qui passent de chaque côté du bloc *)
  let milieux = Array.of_list (List.mapi (fun k sigma -> disposition nb_trous largeur (Tresses.agit (etat k) sigma)) tresse) in
  let morceaux, trous, clou = Tresses.dessin_etat ~hauteur ~largeur (etat 0) in
  (* le dessin de départ est replacé sur la disposition 0 : abscisses transformées par la fonction affine par
     morceaux qui envoie les anciens trous sur les nouveaux *)
  let xs0 = dispositions.(0).abscisses in
  let avant = Array.concat [ [| 0. |]; Array.map (fun p -> p.x) trous; [| largeur |] ]
  and apres = Array.concat [ [| 0. |]; xs0; [| largeur |] ] in
  let replace p = { p with x = interp p.x avant apres } in
  let lignes = List.map (Array.map replace) (Tresses.polylignes morceaux) in
  let clou = replace clou in
  let trous = List.map (fun x -> { x; y = trous.(0).y }) (Array.to_list xs0) in
  (* décalage des sommets du bord bas : loin du clou ; si les trous sont trop serrés pour les trois décalages
     habituels, celui qui éloigne le plus les sommets du clou *)
  let distance_au_clou d = Array.fold_left (fun m x -> Float.min m (Float.abs (x +. d -. clou.x))) Float.infinity xs0 in
  let decalage_bas =
    match List.find_opt (fun d -> distance_au_clou d >= 8. *. e) [ decalage_bord; 12. *. e; -12. *. e ] with
    | Some d -> d
    | None ->
      Array.fold_left (fun m d -> if distance_au_clou d > distance_au_clou m then d else m) (-12. *. e)
        (Tresses.linspace (-12. *. e) (12. *. e) 49)
  in
  let mi = maillage_initial ~decalage_bas trous clou hauteur largeur in
  let pos = mi.maillage.Maillage.pos in
  let y_axe = pos.(List.hd mi.trous).y in
  (* le clou garde sa place relative entre les deux sommets du bord bas qui l'encadrent *)
  let xs_bas = Array.of_list (List.map (fun s -> pos.(s).x) mi.bas) in
  let j = ref 0 in
  for k = 0 to Array.length xs_bas - 2 do if xs_bas.(k) <= clou.x then j := k done;
  let place_du_clou = (!j, (clou.x -. xs_bas.(!j)) /. (xs_bas.(!j + 1) -. xs_bas.(!j))) in
  (* le dessin de départ est aplati : on l'étire au-dessus de l'axe pour qu'il occupe la bande du haut *)
  let y_min = List.fold_left (Array.fold_left (fun m p -> Float.min m p.y)) Float.infinity lignes in
  let etirement = (y_axe -. (14. *. e)) /. (y_axe -. y_min) in
  let etire p = if p.y < y_axe then { p with y = y_axe -. ((y_axe -. p.y) *. etirement) } else p in
  let lignes = List.map (Array.map etire) lignes in
  let film =
    { hauteur; largeur; nb_trous; dispositions; milieux; etape = 0; maillage = mi.maillage;
      trous = Array.of_list mi.trous; clou = mi.clou; haut = Array.of_list mi.haut; bas = Array.of_list mi.bas;
      decalage_bas; place_du_clou; y_axe;
      courbes = List.map (fun p -> noeuds_de_polyligne p mi.maillage mi.clou) lignes }
  in
  (* la tension s'applique dès la première image : pas de lacets lâches au départ *)
  let rec tend_n n film = if n = 0 then film else tend_n (n - 1) (tend film 0.3 dispositions.(0).ecart) in
  tend_n tension film
