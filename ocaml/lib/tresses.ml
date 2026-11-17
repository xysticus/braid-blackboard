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
  let mot = List.concat (List.init (max 0 (n - 1)) (fun k -> lettres_du_segment points.(k) points.(k + 1))) in
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
