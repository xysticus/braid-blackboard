(* Films d'arcs entre trous. Voir arcs.mli. *)

open Geometrie
open Triangulation

let coupe_arc points m debut fin =
  let pos = m.Maillage.pos in
  let n = Array.length points in
  (* toutes les traversées, repérées par leur place le long de la polyligne (k + t : entre les points k et k+1) *)
  let trouves =
    Aretes.fold
      (fun e _ acc ->
        let u, v = (e : Arete.t :> sommet * sommet) in
        let s = pos.(v) -: pos.(u) in
        let cote = Array.map (fun p -> croix s (p -: pos.(u))) points in
        let dessus = Array.map (fun c -> c >= -1e-7 *. norme s) cote in
        let acc = ref acc in
        for k = 0 to n - 2 do
          if dessus.(k) <> dessus.(k + 1) then begin
            let t = cote.(k) /. (cote.(k) -. cote.(k + 1)) in
            let x = points.(k) +: (t *: (points.(k + 1) -: points.(k))) in
            let w = scalaire (x -: pos.(u)) s /. scalaire s s in
            if 1e-9 < w && w < 1. -. 1e-9 then acc := (float k +. t, Sur_arete (e, w)) :: !acc
          end
        done;
        !acc)
      (Maillage.aretes m) []
  in
  let trouves = List.stable_sort (fun (a, _) (b, _) -> compare a b) (List.rev trouves) in
  (* deux traversées successives de la même arête bordent un bigone : on les annule *)
  let arete = function Sur_arete (e, _) -> Some e | Sommet _ -> None in
  let pile =
    List.fold_left
      (fun pile (_, noeud) ->
        match pile with
        | dessus :: reste when arete dessus = arete noeud -> reste
        | _ -> noeud :: pile)
      [] trouves
  in
  let touche s noeud = match noeud with Sur_arete (e, _) -> let u, v = (e :> sommet * sommet) in u = s || v = s | Sommet _ -> false in
  let rec retire s = function noeud :: reste when touche s noeud -> retire s reste | l -> l in
  (* la pile a la fin en tête *)
  let milieu = List.rev (retire fin pile) in
  (Sommet debut :: retire debut milieu) @ [ Sommet fin ]

let pchip y =
  let nb = Array.length y in
  if nb < 2 then Array.map (Array.map (fun _ -> 0.)) y
  else begin
    let colonnes = Array.length y.(0) in
    let d = Array.init (nb - 1) (fun k -> Array.init colonnes (fun j -> y.(k + 1).(j) -. y.(k).(j))) in
    let m = Array.map (Array.map (fun _ -> 0.)) y in
    for j = 0 to colonnes - 1 do
      for k = 1 to nb - 2 do
        let a = d.(k - 1).(j) and b = d.(k).(j) in
        m.(k).(j) <- (if a *. b > 0. then 2. *. a *. b /. (a +. b) else 0.)
      done;
      (* pentes des bouts : la pente de départ est celle du segment du bout, ramenée à 0 si elle est de signe
         contraire et bornée à trois fois le segment (pas de dépassement) ; comme le Python, qui calcule ainsi *)
      List.iter
        (fun (k, dk) ->
          let pente = dk in
          m.(k).(j) <-
            (if pente *. dk <= 0. then 0. else Float.min (Float.abs pente) (3. *. Float.abs dk) *. Float.copy_sign 1. dk))
        [ (0, d.(0).(j)); (nb - 1, d.(nb - 2).(j)) ]
    done;
    m
  end

let hermite y m t =
  let nb = Array.length y in
  if nb = 1 then Array.copy y.(0)
  else begin
    let k = min (int_of_float t) (nb - 2) in
    let u = t -. float k in
    (* u ** 3 comme le Python (un seul arrondi, pas celui de u *. u *. u) *)
    let u2 = u *. u and u3 = Float.pow u 3. in
    let h00 = (2. *. u3) -. (3. *. u2) +. 1. and h10 = u3 -. (2. *. u2) +. u
    and h01 = (-2. *. u3) +. (3. *. u2) and h11 = u3 -. u2 in
    Array.init (Array.length y.(k)) (fun j ->
        (h00 *. y.(k).(j)) +. (h10 *. m.(k).(j)) +. (h01 *. y.(k + 1).(j)) +. (h11 *. m.(k + 1).(j)))
  end

type fixes = Bas | Gauche
type genre = Arcs of fixes | Diagramme

type t = {
  genre : genre;
  hauteur : float;
  largeur : float;
  n : int;
  y_trous : float;
  largeurs : float array array;
  pentes : float array array;
  marge : float;
  marge_gauche : float;
  maillage : Maillage.t;
  voyageurs : sommet array;
  fixes : sommet array;
  places : sommet array;
  numero : int;
  courbes : courbe list;
  ecart : float;
}

(* Les places de l'axe au temps T, sans le film (le constructeur s'en sert avant de l'avoir). *)
let places largeurs pentes ~gauche ~marge ~largeur t =
  let w = Array.map (fun x -> Float.max x 1e-6) (hermite largeurs pentes t) in
  let somme = Array.fold_left ( +. ) 0. w in
  let cumul = ref 0. in
  Array.init (Array.length w - 1) (fun j ->
      cumul := !cumul +. (w.(j) /. somme);
      gauche +. ((largeur -. gauche -. marge) *. !cumul))

let places_au_temps film t =
  places film.largeurs film.pentes ~gauche:film.marge_gauche ~marge:film.marge ~largeur:film.largeur t

let nb_trous tresse = 1 + List.fold_left (fun m (l : Tresses.sigma Tresses.lettre) -> max m l.indice) 1 tresse

(* Espacement proportionnel : à chaque image clé, la largeur de chaque intervalle de l'axe (extrémités comprises)
   est proportionnelle à 1 + le nombre d'arcs qui le traversent (la moitié de celui des lacets). *)
let largeurs_des_images n tresse =
  Array.init (List.length tresse + 1) (fun k ->
      let etat = Tresses.etat_de_tresse ~nb_trous:n (List.filteri (fun j _ -> j < k) tresse) in
      let comptes = Array.make (n + 1) 0 in
      List.iter (Array.iter (fun x -> let i = Tresses.intervalle x etat.trous in comptes.(i) <- comptes.(i) + 1)) etat.lacets;
      let w = Array.map (fun c -> 1. +. (float c /. 2.)) comptes in
      let somme = Array.fold_left ( +. ) 0. w in
      Array.map (fun x -> x /. somme) w)

(* Les largeurs des images clés, le maillage (trous voyageurs à leurs places de départ, puis trous fixes), sans
   courbes encore : commun aux deux constructeurs. *)
let construit ~genre ~hauteur ~largeur ~ecart ~y_trous ~marge_gauche ~n tresse places_fixes =
  let largeurs = largeurs_des_images n tresse in
  let pentes = pchip largeurs in
  let marge = 30. in
  let voyageurs = Array.map (fun x -> { x; y = y_trous }) (places largeurs pentes ~gauche:marge_gauche ~marge ~largeur 0.) in
  let maillage, indices, _ = Raccord.maillage_du_raccord (Array.to_list voyageurs @ places_fixes) None largeur hauteur in
  let indices = Array.of_list indices in
  let voyageurs = Array.sub indices 0 n and fixes = Array.sub indices n (Array.length indices - n) in
  { genre; hauteur; largeur; n; y_trous; largeurs; pentes; marge; marge_gauche; maillage; voyageurs; fixes;
    places = Array.copy voyageurs; numero = 0; courbes = []; ecart }

let tension film taux = { film with courbes = Film.tend_courbes ~portee_sinus:(3. *. film.ecart) film.maillage film.courbes taux film.ecart }

(* Pose les arcs de départ (les extrémités, et la polyligne qui les relie) puis 100 pas de tension. *)
let pose film extremites polyligne_de_depart =
  let pos = film.maillage.Maillage.pos in
  let courbes = List.map (fun (a, b) -> coupe_arc (polyligne_de_depart pos.(a) pos.(b)) film.maillage a b) extremites in
  let rec tend k film = if k = 0 then film else tend (k - 1) (tension film 0.3) in
  tend 100 { film with courbes }

let cree ?(hauteur = 800.) ?(largeur = 800.) ?(ecart = 6.) ?ecart_fixes ?(fixes = Bas) tresse =
  let n = nb_trous tresse in
  let y_trous = (match fixes with Bas -> 0.42 | Gauche -> 0.3) *. hauteur and y_fixes = hauteur -. 60. in
  let e = Option.value ecart_fixes ~default:20. in
  let marge_gauche = match fixes with Bas -> 30. | Gauche -> 30. +. (float n *. e) in
  let places_fixes =
    List.init n (fun k ->
        let k' = float k and n' = float n in
        match (fixes, ecart_fixes) with
        | Gauche, _ -> { x = 15. +. ((n' -. 1. -. k') *. e); y = y_trous } (* f_1 à droite, f_n à gauche *)
        | Bas, None -> { x = ((k' +. 1.) *. largeur /. (n' +. 1.)) +. 0.37; y = y_fixes }
        | Bas, Some e -> { x = (largeur /. 2.) +. ((k' -. ((n' -. 1.) /. 2.)) *. e) +. 0.37; y = y_fixes })
  in
  let film = construit ~genre:(Arcs fixes) ~hauteur ~largeur ~ecart ~y_trous ~marge_gauche ~n tresse places_fixes in
  (* arcs de départ : de f_i à m_i, en ligne droite (trous fixes en bas) ou en demi-ellipse sous l'axe (à gauche :
     les intervalles [f_k, m_k] sont emboîtés, donc les demi-ellipses de même aplatissement ne se croisent pas) *)
  let depart p q =
    match fixes with
    | Gauche ->
      let c = (p.x +. q.x) /. 2. and r = (q.x -. p.x) /. 2. in
      Array.map (fun phi -> { x = c +. (r *. Float.cos phi); y = y_trous +. (0.8 *. r *. Float.sin phi) })
        (Tresses.linspace Float.pi 0. 300)
    | Bas -> Array.map (fun t -> p +: (t *: (q -: p))) (Tresses.linspace 0. 1. 200)
  in
  pose film (List.init n (fun k -> (film.fixes.(k), film.voyageurs.(k)))) depart

let cree_diagramme ?(hauteur = 800.) ?(largeur = 800.) ?(ecart = 6.) tresse =
  let n = nb_trous tresse in
  let y_trous = 0.5 *. hauteur in
  let film = construit ~genre:Diagramme ~hauteur ~largeur ~ecart ~y_trous ~marge_gauche:30. ~n tresse [ { x = 15.; y = y_trous } ] in
  (* arcs de départ : les segments de l'axe, un peu bombés vers le haut pour la découpe *)
  let bouts = Array.append film.fixes film.voyageurs in
  let depart p q =
    Array.map (fun u -> (p +: (u *: (q -: p))) -: { x = 0.; y = 4. *. Float.sin (Float.pi *. u) }) (Tresses.linspace 0. 1. 200)
  in
  pose film (List.init n (fun k -> (bouts.(k), bouts.(k + 1)))) depart

let lettre ?(images = 60) ?(sous_pas = 3) ?(taux = 0.15) ?rendu film (sigma : Tresses.sigma Tresses.lettre) =
  let i = sigma.indice - 1 in
  let a = film.places.(i) and b = film.places.(i + 1) in
  let sens = Film.sens_de_sigma *. (match sigma.signe with Tresses.Plus -> 1. | Tresses.Moins -> -1.) in
  let nb = images * sous_pas in
  let rec boucle pas film =
    if pas > nb then film
    else begin
      let u = float pas /. float nb in
      let x = places_au_temps film (float film.numero +. u) in
      let pos = Array.copy film.maillage.Maillage.pos in
      Array.iteri (fun j h -> pos.(h) <- { x = x.(j); y = film.y_trous }) film.places;
      let milieu = { x = (x.(i) +. x.(i + 1)) /. 2.; y = film.y_trous } and r = (x.(i + 1) -. x.(i)) /. 2. in
      let c = Float.cos (Float.pi *. u) and s = Float.sin (Float.pi *. u) in
      pos.(a) <- milieu +: (r *: { x = -.c; y = -.sens *. s });
      pos.(b) <- milieu +: (r *: { x = c; y = sens *. s });
      if pas = nb then begin
        pos.(a) <- { x = x.(i + 1); y = film.y_trous };
        pos.(b) <- { x = x.(i); y = film.y_trous }
      end;
      let maillage = Maillage.deplace film.maillage pos in
      if not (Maillage.valide maillage) then failwith "triangle retourné : augmenter sous_pas";
      let maillage, courbes = Maillage.delaunay maillage film.courbes in
      (* sinus mesuré à distance : pas de marches dans les éventails de triangles minces *)
      let film = tension { film with maillage; courbes } taux in
      (match rendu with Some f when pas mod sous_pas = 0 -> f film | _ -> ());
      boucle (pas + 1) film
    end
  in
  let film = boucle 1 film in
  let places = Array.copy film.places in
  places.(i) <- b;
  places.(i + 1) <- a;
  { film with places; numero = film.numero + 1 }

let polyligne film k = Film.polyligne_de_courbe film.maillage (List.nth film.courbes k)

let ruban ?largeur film k =
  let largeur = Option.value largeur ~default:(film.ecart /. 3.) in
  let brut = polyligne film k in
  (* points confondus avec le précédent retirés *)
  let p =
    Array.of_list
      (List.filteri (fun i q -> i = 0 || norme (q -: brut.(i - 1)) > 1e-9) (Array.to_list brut))
  in
  let nb = Array.length p in
  (* tangente : différences centrées (le np.gradient du Python), décentrées aux bouts *)
  let d =
    Array.init nb (fun i ->
        let t =
          if i = 0 then p.(1) -: p.(0)
          else if i = nb - 1 then p.(nb - 1) -: p.(nb - 2)
          else 0.5 *: (p.(i + 1) -: p.(i - 1))
        in
        (1. /. Float.max (norme t) 1e-12) *: t)
  in
  let normale = Array.map (fun t -> { x = -.t.y; y = t.x }) d in
  (* près des bouts, la largeur va à zéro côté trou fixe (le ruban part du trou fixe) *)
  let long = Array.make nb 0. in
  for i = 1 to nb - 1 do long.(i) <- long.(i - 1) +. norme (p.(i) -: p.(i - 1)) done;
  let l = Array.map (fun s -> largeur *. Float.min 1. (s /. 20.)) long in
  let gauche = Array.init nb (fun i -> p.(i) +: (l.(i) *: normale.(i)))
  and droite = Array.init nb (fun i -> p.(i) -: (l.(i) *: normale.(i))) in
  let bout = p.(nb - 1) in
  let g = gauche.(nb - 1) -: bout in
  let a0 = Float.atan2 g.y g.x in
  let tour = Array.map (fun t -> bout +: (largeur *: { x = Float.cos (a0 -. t); y = Float.sin (a0 -. t) })) (Tresses.linspace 0. Float.pi 30) in
  let rev a = Array.of_list (List.rev (Array.to_list a)) in
  rev (Array.concat [ gauche; tour; rev droite ])

let mots film =
  let trous = List.sort compare (Array.to_list (Array.map (fun s -> film.maillage.Maillage.pos.(s)) film.voyageurs)) in
  let lit k = Tresses.lit_mot (ruban film k) trous in
  match film.genre with Arcs _ -> List.init film.n lit | Diagramme -> [ lit 0 ]

let verifie cree premiers tresse =
  let film = cree tresse in
  let n = film.n in
  let rec boucle film k = function
    | [] -> true
    | sigma :: reste ->
      let film = lettre ~images:12 film sigma in
      let attendu = Array.to_list (Tresses.calcule_autofn_de_tresse ~nb_trous:n (List.filteri (fun j _ -> j <= k) tresse)) in
      let attendu = List.filteri (fun j _ -> j < premiers n) attendu in
      mots film = attendu && boucle film (k + 1) reste
  in
  boucle film 0 tresse

let verifie_arcs ?ecart_fixes ?fixes tresse = verifie (cree ?ecart_fixes ?fixes) Fun.id tresse
let verifie_diagramme tresse = verifie (fun t -> cree_diagramme t) (fun _ -> 1) tresse
