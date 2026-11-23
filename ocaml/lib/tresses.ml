(* Tresses et groupe libre. Voir tresses.mli pour le rôle de chaque fonction. *)

(* Deux types vides, déclarés sans définition : ils sont distincts et n'ont aucune valeur. Ils ne servent qu'à
   étiqueter les lettres (type fantôme). *)
type x
type sigma

type signe = Plus | Moins

type 'alphabet lettre = { indice : int; signe : signe }

let oppose = function Plus -> Moins | Moins -> Plus

(* L'annotation garde l'alphabet : sans elle, la mise à jour { l with ... } pourrait changer le paramètre
   fantôme, qui n'apparaît dans aucun champ (l'interface l'interdirait de toute façon). *)
let inverse_lettre (l : 'a lettre) : 'a lettre = { l with signe = oppose l.signe }

let lettre_de_entier i =
  if i > 0 then { indice = i; signe = Plus }
  else if i < 0 then { indice = -i; signe = Moins }
  else invalid_arg "lettre_de_entier : 0 n'est pas une lettre"

let entier_de_lettre { indice; signe } =
  match signe with Plus -> indice | Moins -> -indice

type mot_de_fn = x lettre list

(* Renverser et inverser chaque lettre, en une seule passe : rev_map renverse déjà. *)
let inverse m = List.rev_map inverse_lettre m

module Reduit = struct
  type t = mot_de_fn

  (* Réduction libre par une pile. On lit le mot de gauche à droite ; la pile contient le préfixe déjà lu,
     réduit, à l'envers (sa dernière lettre en tête). Une lettre qui annule la tête de pile la fait disparaître,
     sinon on l'empile. Invariant : la pile est toujours un mot réduit, donc à la fin aussi.
     Le simplifie du Python fait la même chose sur place, en reculant d'un cran après chaque suppression ; ici on
     rend un nouveau mot, de type Reduit.t. *)
  let simplifie m =
    let empile pile l =
      match pile with
      | tete :: reste when tete = inverse_lettre l -> reste
      | _ -> l :: pile
    in
    List.rev (List.fold_left empile [] m)

  (* Les facteurs sont réduits, mais leurs jonctions peuvent se simplifier : on réduit la concaténation. *)
  let produit ms = simplifie (List.concat ms)

  (* L'inverse d'un mot réduit est réduit. *)
  let inverse = inverse
end

type tresse = sigma lettre list

type automorphisme = Reduit.t array

let morphisme_identite n = Array.init n (fun i -> Reduit.simplifie [ { indice = i + 1; signe = Plus } ])

(* Le Python modifie le tableau en place ; ici on rend un nouveau tableau. On réduit à chaque lettre au lieu
   de tout réduire à la fin : la réduction libre donne le même mot réduit dans les deux cas, et les mots restent
   courts. *)
let conjugaison_locale sigma auto =
  let i = sigma.indice - 1 in
  if i < 0 || i + 1 >= Array.length auto then
    invalid_arg "conjugaison_locale : σ_i demande les trous i et i+1";
  let u = auto.(i) and v = auto.(i + 1) in
  let u', v' =
    match sigma.signe with
    | Plus -> (Reduit.produit [ u; v; Reduit.inverse u ], u) (* conjugaison à droite *)
    | Moins -> (v, Reduit.produit [ Reduit.inverse v; u; v ]) (* conjugaison à gauche *)
  in
  let a = Array.copy auto in
  a.(i) <- u';
  a.(i + 1) <- v';
  a

(* L'automorphisme de F_n associé à une tresse, en deux temps.
   1. Le nombre de trous n : celui qu'on donne (?nb_trous, argument optionnel : None s'il est absent), sinon
      1 + le plus grand indice de la tresse, puisque σ_i fait bouger les trous i et i+1. La tresse vide n'a pas
      d'indice : le Python prend alors 6 trous, on fait de même pour pouvoir comparer.
   2. On part de l'identité sur n générateurs et on fait agir chaque lettre, la dernière d'abord : c'est une
      composition, φ_(σ₁σ₂…σ_k) = φ_σ₁ ∘ φ_σ₂ ∘ … ∘ φ_σ_k, et c'est φ_σ_k qui touche l'identité en premier.
      fold_right donne exactement cet ordre : avec f = conjugaison_locale,
      fold_right f [σ₁; σ₂; σ₃] id = f σ₁ (f σ₂ (f σ₃ id)).
      (Le Python écrit la même chose avec for sigma in reversed(tresse).)
   Chaque image reste réduite à chaque pas (conjugaison_locale ne fabrique que des Reduit.t). *)
let calcule_autofn_de_tresse ?nb_trous tresse =
  let n =
    match nb_trous, tresse with
    | Some n, _ -> n
    | None, [] -> 6
    | None, _ -> 1 + List.fold_left (fun m l -> max m l.indice) 0 tresse (* plus grand indice *)
  in
  List.fold_right conjugaison_locale tresse (morphisme_identite n)

(* Les annotations choisissent l'alphabet : lettre_de_entier est polymorphe. *)
let tresse_de_entiers l : tresse = List.map lettre_de_entier l
let mot_de_fn_de_entiers l : mot_de_fn = List.map lettre_de_entier l
let entiers_de_mot l = List.map entier_de_lettre l

(* Relecture d'un mot sur un dessin. *)

open Geometrie

(* Chaque trou envoie une demi-droite vers le haut (y décroissant à l'écran). Un segment qui la traverse de gauche
   à droite note x_j, de droite à gauche x_j⁻¹ ; un segment peut en traverser plusieurs : on les note dans l'ordre
   où il les rencontre (place sur le segment). *)
let lit_mot (points : point array) (trous : point list) =
  let lettres_du_segment p q =
    List.mapi (fun j t -> (j + 1, t)) trous
    |> List.filter_map (fun (j, t) ->
           if (p.x < t.x) <> (q.x < t.x) then
             let place = (t.x -. p.x) /. (q.x -. p.x) in
             if p.y +. ((q.y -. p.y) *. place) < t.y then Some (place, if q.x >= t.x then j else -j) else None
           else None)
    |> List.sort compare |> List.map snd
  in
  let n = Array.length points in
  (* concat_map et non concat : List.concat n'est pas récursive terminale, et une polyligne du film a des milliers de
     points (dépassement de pile sous JavaScript) *)
  let mot = List.concat_map (fun k -> lettres_du_segment points.(k) points.(k + 1)) (List.init (max 0 (n - 1)) Fun.id) in
  Reduit.simplifie (mot_de_fn_de_entiers mot)

(* Arcs de cercle. *)

(* linspace du Python : n valeurs de a à b, la dernière exactement b. *)
let linspace a b n =
  let pas = (b -. a) /. float (n - 1) in
  Array.init n (fun k -> if k = n - 1 then b else a +. (float k *. pas))

let arc_de_cercle ?(pas = 1.5) p t m =
  let w = m -: p in
  let corde = norme w in
  let phi = 2. *. Float.atan2 (croix t w) (scalaire t w) in
  if corde < 1e-9 || Float.abs (Float.sin (phi /. 2.)) < 1e-9 then [| p; m |]
  else
    let rayon = corde /. (2. *. Float.sin (phi /. 2.)) in
    let centre = p +: (rayon *: { x = -.t.y; y = t.x }) in
    let d = p -: centre in
    let n = max 3 (int_of_float (Float.ceil (Float.abs (rayon *. phi) /. pas))) in
    Array.map
      (fun a -> centre +: { x = (Float.cos a *. d.x) -. (Float.sin a *. d.y); y = (Float.sin a *. d.x) +. (Float.cos a *. d.y) })
      (linspace 0. phi n)

let raccord_egal p0 t0 p1 t1 =
  let v = p1 -: p0 and t = t0 +: t1 in
  let a = 2. *. (1. -. scalaire t0 t1) in
  let d =
    if Float.abs a > 1e-9 then
      let vt = scalaire v t in
      Some ((-.vt +. Float.sqrt ((vt *. vt) +. (a *. scalaire v v))) /. a)
    else if Float.abs (scalaire v t1) > 1e-9 then Some (scalaire v v /. (4. *. scalaire v t1))
    else None
  in
  Option.map (fun d -> 0.5 *: (p0 +: (d *: t0) +: p1 -: (d *: t1))) d

let deux_arcs p0 t0 p1 t1 =
  match raccord_egal p0 t0 p1 t1 with
  | None -> [| p0; p1 |]
  | Some j ->
    let retour = arc_de_cercle p1 (oppose t1) j in
    let n = Array.length retour in
    Array.append (arc_de_cercle p0 t0 j) (Array.init n (fun k -> retour.(n - 1 - k)))

(* Le méandre : un lacet dessiné comme la suite des intervalles où il coupe l'axe. *)

let calcule_arcs mot =
  match entiers_de_mot mot with
  | [] -> invalid_arg "calcule_arcs : mot vide"
  | premier :: reste ->
    (* debut .. courant : la suite croissante consécutive en cours (un arc du haut) ; quand elle s'arrête, on
       écrit l'arc du haut puis l'arc du bas qui mène au début de la suivante (son signe donne son sens) *)
    let rec parcourt debut courant acc = function
      | [] -> List.rev ((debut, courant) :: acc)
      | t :: reste when t - courant = 1 -> parcourt debut t acc reste
      | t :: reste ->
        let signe_bas = if abs t - abs courant < 0 then 1 else -1 in
        let tt, qq =
          if signe_bas < 0 then
            ((if courant > 0 then abs courant + 1 else abs courant), if t > 0 then abs t - 1 else abs t)
          else ((if courant > 0 then abs courant else abs courant - 1), if t > 0 then abs t else abs t + 1)
        in
        parcourt t t ((tt * signe_bas, qq * signe_bas) :: (debut, courant) :: acc) reste
    in
    parcourt premier premier [] reste

let intervalles mot =
  let bouts (debut, fin) = if debut > 0 then [ debut - 1; fin ] else [ -debut; -fin - 1 ] in
  calcule_arcs mot |> List.filteri (fun k _ -> k mod 2 = 0) |> List.concat_map bouts

let voisin lacet j en_haut =
  if en_haut then Some (j lxor 1)
  else
    let k = if j mod 2 = 1 then j + 1 else j - 1 in
    if 0 <= k && k < Array.length lacet then Some k else None

(* On suit les deux courbes côte à côte ; chaque arc parcouru ensemble inverse l'ordre (arcs emboîtés). *)
let suit_en_parallele lacets p q en_haut =
  let rec suit (lp, ip) (lq, iq) en_haut signe =
    let k = lacets.(lp).(ip) in
    match (voisin lacets.(lp) ip en_haut, voisin lacets.(lq) iq en_haut) with
    | None, None -> 0
    (* le clou est sous tous les arcs du bas : un point relié au clou n'est jamais englobé *)
    | None, Some jq -> if lacets.(lq).(jq) > k then -signe else signe
    | Some jp, None -> if lacets.(lp).(jp) > k then signe else -signe
    | Some jp, Some jq ->
      let a = lacets.(lp).(jp) and b = lacets.(lq).(jq) in
      if a <> b then
        (* du même côté, l'arc qui va le plus loin englobe l'autre ; de côtés opposés, celui qui part à gauche
           est à gauche *)
        let meme_cote = a > k = (b > k) in
        let p_a_gauche = if meme_cote then a > b else a < b in
        if p_a_gauche then -signe else signe
      else suit (lp, jp) (lq, jq) (not en_haut) (-signe)
  in
  suit p q en_haut 1

let compare_points lacets p q =
  if p = q then 0
  else
    match suit_en_parallele lacets p q true with
    | 0 -> (
      match suit_en_parallele lacets p q false with
      | 0 -> failwith "compare_points : points indiscernables"
      | r -> r)
    | r -> r

let abscisses lacets nb_trous =
  let par_intervalle = Array.make (nb_trous + 1) [] in
  Array.iteri (fun i lacet -> Array.iteri (fun j k -> par_intervalle.(k) <- (i, j) :: par_intervalle.(k)) lacet) lacets;
  let rang_point = Hashtbl.create 64 and rang_trou = Array.make nb_trous 0 and r = ref 0 in
  for k = 0 to nb_trous do
    List.iter
      (fun p -> Hashtbl.replace rang_point p !r; incr r)
      (List.sort (compare_points lacets) (List.rev par_intervalle.(k)));
    if k < nb_trous then begin rang_trou.(k) <- !r; incr r end
  done;
  (rang_point, rang_trou, !r)

type croisement = Arcs of (int * int) * (int * int) | Arc_et_descente of (int * int) * int

let croisements lacets rang_point =
  let corde i j k =
    let a = Hashtbl.find rang_point (i, j) and b = Hashtbl.find rang_point (i, k) in
    (min a b, max a b)
  in
  let haut = ref [] and bas = ref [] and au_clou = ref [] in
  Array.iteri
    (fun i lacet ->
      let n = Array.length lacet in
      for j = 0 to n - 2 do
        if j mod 2 = 0 then haut := corde i j (j + 1) :: !haut else bas := corde i j (j + 1) :: !bas
      done;
      au_clou := Hashtbl.find rang_point (i, n - 1) :: Hashtbl.find rang_point (i, 0) :: !au_clou)
    lacets;
  let entrelaces (a1, b1) (a2, b2) = (a1 < a2 && a2 < b1 && b1 < b2) || (a2 < a1 && a1 < b2 && b2 < b1) in
  let rec paires = function
    | [] -> []
    | c :: reste -> List.filter_map (fun c' -> if entrelaces c c' then Some (Arcs (c, c')) else None) reste @ paires reste
  in
  let haut = List.rev !haut and bas = List.rev !bas and au_clou = List.rev !au_clou in
  paires haut @ paires bas
  @ List.concat_map (fun ((a, b) as c) -> List.filter_map (fun x -> if a < x && x < b then Some (Arc_et_descente (c, x)) else None) au_clou) bas

let lacets_de ?nb_trous tresse =
  Array.map (fun m -> Array.of_list (intervalles (m : Reduit.t :> mot_de_fn))) (calcule_autofn_de_tresse ?nb_trous tresse)

let verifie tresse =
  let lacets = lacets_de tresse in
  let rang_point, _, _ = abscisses lacets (Array.length lacets) in
  croisements lacets rang_point = []

(* L'état : abscisses des trous et, pour chaque lacet, abscisses de ses points sur l'axe (seul l'ordre compte). *)
type etat = { trous : float array; lacets : float array list }

let etat_de_tresse ?nb_trous tresse =
  let lacets = lacets_de ?nb_trous tresse in
  let rang_point, rang_trou, _ = abscisses lacets (Array.length lacets) in
  { trous = Array.map float rang_trou;
    lacets = Array.to_list (Array.mapi (fun i l -> Array.mapi (fun j _ -> float (Hashtbl.find rang_point (i, j))) l) lacets) }

(* bisect.bisect : nombre de trous à gauche de x (ou en x). *)
let intervalle x trous = Array.fold_left (fun n t -> if t <= x then n + 1 else n) 0 trous

let normalise etat =
  let tous = List.sort compare (Array.to_list etat.trous @ List.concat_map Array.to_list etat.lacets) in
  let rang = Hashtbl.create 64 in
  List.iteri (fun r x -> Hashtbl.replace rang x (float r)) tous;
  let r x = Hashtbl.find rang x in
  { trous = Array.map r etat.trous; lacets = List.map (Array.map r) etat.lacets }

(* σ_i fait tourner d'un demi-tour le bloc (trous i, i+1 et ce qui est entre eux) : les points du bloc sont
   réfléchis, chaque arc qui sort du bloc reçoit un point nouveau (à droite du bloc pour un arc du haut et σ
   positif, à gauche sinon ; l'inverse pour σ⁻¹), dans l'ordre des extrémités intérieures de ces arcs. *)
type origine = Glisse of int | Tourne of int | Ne of int * int

let agit_origines etat (sigma : sigma lettre) =
  let i = sigma.indice in
  let a = etat.trous.(i - 1) and b = etat.trous.(i) in
  let dedans = function Some x -> a < x && x < b | None -> false in
  (* les arcs qui sortent du bloc : (extrémité intérieure, lacet, indice de l'arc) ; l'arc j va du point j au
     point j + 1, j = -1 et j = n - 1 sont les descentes au clou (None) *)
  let droite = ref [] and gauche = ref [] in
  List.iteri
    (fun l lacet ->
      let n = Array.length lacet in
      let point k = if k < 0 || k >= n then None else Some lacet.(k) in
      for j = -1 to n - 1 do
        let p = point j and q = point (j + 1) in
        if dedans p <> dedans q then begin
          let en_haut = j >= 0 && j mod 2 = 0 && j < n - 1 in
          let cote = if en_haut = (sigma.signe = Plus) then droite else gauche in
          let interieur = match (p, q) with Some x, _ when dedans p -> x | _, Some x -> x | _ -> assert false in
          cote := (interieur, l, j) :: !cote
        end
      done)
    etat.lacets;
  let tous = Array.to_list etat.trous @ List.concat_map Array.to_list etat.lacets in
  let voisin_droit = List.fold_left (fun m x -> if x > b then Float.min m x else m) Float.infinity tous in
  let voisin_droit = if voisin_droit = Float.infinity then b +. 1. else voisin_droit in
  let voisin_gauche = List.fold_left (fun m x -> if x < a then Float.max m x else m) Float.neg_infinity tous in
  let voisin_gauche = if voisin_gauche = Float.neg_infinity then a -. 1. else voisin_gauche in
  let nouveau = Hashtbl.create 16 in
  List.iter
    (fun (sorties, debut, fin) ->
      let arcs = List.sort compare sorties in
      let n = List.length arcs in
      List.iteri
        (fun r (_, l, j) -> Hashtbl.replace nouveau (l, j) (debut +. ((fin -. debut) *. float (r + 1) /. float (n + 1))))
        arcs)
    [ (!droite, b, voisin_droit); (!gauche, voisin_gauche, a) ];
  let centre = (a +. b) /. 2. in
  let lacets =
    List.mapi
      (fun l lacet ->
        let n = Array.length lacet in
        List.concat
          (List.init (n + 1) (fun k ->
               let j = k - 1 in
               (if j >= 0 then [ (if dedans (Some lacet.(j)) then ((2. *. centre) -. lacet.(j), Tourne j) else (lacet.(j), Glisse j)) ] else [])
               @ match Hashtbl.find_opt nouveau (l, j) with
                 | Some x -> [ (x, Ne ((if j >= 0 && dedans (Some lacet.(j)) then j else j + 1), j)) ]
                 | None -> []))
        |> Array.of_list)
      etat.lacets
  in
  ({ etat with lacets = List.map (Array.map fst) lacets }, List.map (Array.map snd) lacets)

let agit etat sigma = fst (agit_origines etat sigma)

(* Deux points consécutifs d'un lacet dans le même intervalle forment un bigone : ils s'annulent (pile). *)
let reduit etat =
  let reduit_lacet lacet =
    Array.fold_left
      (fun pile x ->
        match pile with
        | y :: reste when intervalle y etat.trous = intervalle x etat.trous -> reste
        | _ -> x :: pile)
      [] lacet
    |> List.rev |> Array.of_list
  in
  { etat with lacets = List.map reduit_lacet etat.lacets }

(* Pour chaque lacet de l'état non réduit : le rang du point dans le lacet réduit, ou -1 s'il s'annule (bigone), et son partenaire
   (le point avec lequel il s'annule, -1 sinon). *)
let bigones etat =
  List.map
    (fun lacet ->
      let n = Array.length lacet in
      let rang = Array.make n 0 and partenaire = Array.make n (-1) in
      let pile = ref [] in
      Array.iteri
        (fun k x ->
          match !pile with
          | j :: reste when intervalle lacet.(j) etat.trous = intervalle x etat.trous ->
              pile := reste; rang.(j) <- -1; rang.(k) <- -1; partenaire.(j) <- k; partenaire.(k) <- j
          | _ -> pile := k :: !pile)
        lacet;
      let r = ref 0 in
      Array.iteri (fun k _ -> if rang.(k) >= 0 then begin rang.(k) <- !r; incr r end) lacet;
      (rang, partenaire))
    etat.lacets

let verifie_action tresse =
  let nb_trous = 1 + List.fold_left (fun m (l : sigma lettre) -> max m l.indice) 0 tresse in
  let rec avance etat k = function
    | [] -> true
    | sigma :: reste ->
      let etat = normalise (reduit (agit etat sigma)) in
      etat = etat_de_tresse ~nb_trous (List.filteri (fun j _ -> j <= k) tresse) && avance etat (k + 1) reste
  in
  avance (etat_de_tresse ~nb_trous []) 0 tresse

(* Dessin d'un état : demi-ellipses entre points consécutifs, descentes au clou sous tous les arcs. *)

let demi_ellipse ?(pas = 1.5) x1 x2 en_haut y_axe aplati =
  let r = Float.abs (x2 -. x1) /. 2. and milieu = (x1 +. x2) /. 2. in
  let sens = if en_haut then -1. else 1. in
  Array.map
    (fun phi -> { x = milieu +. ((x1 -. milieu) *. Float.cos phi); y = y_axe +. (sens *. aplati *. r *. Float.sin phi) })
    (linspace 0. Float.pi (max 6 (int_of_float (Float.ceil (Float.pi *. r /. pas)))))

let descente_au_clou xp y_haut y_sous x_clou y_clou =
  let d = xp -. x_clou and h = y_clou -. y_sous in
  let bas =
    if Float.abs d < 1e-6 then [| { x = x_clou; y = y_clou } |]
    else
      let etire = Float.max 1. (Float.abs d /. h) in
      let d = d /. etire in
      let centre = ((d *. d) -. (h *. h)) /. (2. *. d) in
      let rayon = Float.abs (d -. centre) in
      Array.map
        (fun alpha -> { x = x_clou +. (etire *. (centre +. (rayon *. Float.cos alpha))); y = y_sous +. (rayon *. Float.sin alpha) })
        (linspace (Float.atan2 h (-.centre)) (if d > centre then 0. else Float.pi) 40)
  in
  let n = max 2 (int_of_float (Float.ceil ((y_sous -. y_haut) /. 2.))) in
  Array.append bas (Array.map (fun y -> { x = xp; y }) (linspace y_sous y_haut n))

let renverse t = let n = Array.length t in Array.init n (fun k -> t.(n - 1 - k))

type geometrie = { abscisse : float -> float; y_axe : float; aplati : float; y_sous : float }

let geometrie_etat ?(hauteur = 400.) ?(largeur = 400.) etat =
  let tous = Array.to_list etat.trous @ List.concat_map Array.to_list etat.lacets in
  let pmin = List.fold_left Float.min Float.infinity tous and pmax = List.fold_left Float.max Float.neg_infinity tous in
  let pas = (largeur -. 40.) /. (pmax -. pmin) in
  let abscisse p = 20. +. ((p -. pmin) *. pas) in
  let y_axe = 0.4 *. hauteur in
  (* on aplatit les arcs pour qu'ils tiennent en hauteur, en laissant de la place à l'éventail vers le clou *)
  let rayons parite =
    List.concat_map
      (fun lacet -> List.init (max 0 (Array.length lacet - 1)) (fun j -> (j, Float.abs (lacet.(j + 1) -. lacet.(j)) /. 2. *. pas))
                    |> List.filter_map (fun (j, r) -> if j mod 2 = parite then Some r else None))
      etat.lacets
  in
  let rayon_haut = List.fold_left Float.max Float.neg_infinity (rayons 0) in
  let rayon_bas = List.fold_left Float.max 0. (rayons 1) in
  let aplati = Float.min 1. (Float.min ((y_axe -. 10.) /. rayon_haut) ((hauteur -. 70. -. y_axe) /. Float.max rayon_bas 1.)) in
  let y_sous = y_axe +. (rayon_bas *. aplati) +. 8. in
  { abscisse; y_axe; aplati; y_sous }

let dessin_etat ?(hauteur = 400.) ?(largeur = 400.) etat =
  let { abscisse; y_axe; aplati; y_sous } = geometrie_etat ~hauteur ~largeur etat in
  let x_clou = largeur /. 2. and y_clou = hauteur -. 10. in
  let descente xp = descente_au_clou xp y_axe y_sous x_clou y_clou in
  let morceaux =
    List.map
      (fun lacet ->
        let xs = Array.map abscisse lacet and n = Array.length lacet in
        [ descente xs.(0) ]
        @ List.init (n - 1) (fun j -> demi_ellipse xs.(j) xs.(j + 1) (j mod 2 = 0) y_axe aplati)
        @ [ renverse (descente xs.(n - 1)) ])
      etat.lacets
  in
  (morceaux, Array.map (fun p -> { x = abscisse p; y = y_axe }) etat.trous, { x = x_clou; y = y_clou })

let polylignes morceaux = List.map Array.concat morceaux
