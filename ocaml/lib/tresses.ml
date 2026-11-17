(* Tresses et groupe libre. Voir tresses.mli pour le rôle de chaque fonction. *)

type signe = Plus | Moins

type lettre = { indice : int; signe : signe }

let oppose = function Plus -> Moins | Moins -> Plus

let inverse_lettre l = { l with signe = oppose l.signe }

let lettre_de_entier i =
  if i > 0 then { indice = i; signe = Plus }
  else if i < 0 then { indice = -i; signe = Moins }
  else invalid_arg "lettre_de_entier : 0 n'est pas une lettre"

let entier_de_lettre { indice; signe } =
  match signe with Plus -> indice | Moins -> -indice

type mot = lettre list

(* Renverser et inverser chaque lettre, en une seule passe : rev_map renverse déjà. *)
let inverse m = List.rev_map inverse_lettre m

module Reduit = struct
  type t = mot

  (* Réduction libre par une pile. On lit le mot de gauche à droite ; la pile contient le préfixe déjà lu,
     réduit, à l'envers (sa dernière lettre en tête). Une lettre qui annule la tête de pile la fait disparaître,
     sinon on l'empile. Invariant : la pile est toujours un mot réduit, donc à la fin aussi.
     Le Python ([simplifie]) fait la même chose sur place, en reculant d'un cran après chaque suppression. *)
  let de_mot m =
    let empile pile l =
      match pile with
      | tete :: reste when tete = inverse_lettre l -> reste
      | _ -> l :: pile
    in
    List.rev (List.fold_left empile [] m)

  (* Les facteurs sont réduits, mais leurs jonctions peuvent se simplifier : on réduit la concaténation. *)
  let produit ms = de_mot (List.concat ms)

  (* L'inverse d'un mot réduit est réduit. *)
  let inverse = inverse
end

type tresse = lettre list

type automorphisme = Reduit.t array

let identite n = Array.init n (fun i -> Reduit.de_mot [ { indice = i + 1; signe = Plus } ])

(* Le Python modifie le tableau en place ; ici on rend un nouveau tableau. On réduit à chaque lettre au lieu
   de tout réduire à la fin : la réduction libre donne le même mot réduit dans les deux cas, et les mots restent
   courts. *)
let agit sigma auto =
  let i = sigma.indice - 1 in
  if i < 0 || i + 1 >= Array.length auto then
    invalid_arg "agit : σ_i demande les trous i et i+1";
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

let auto_de_tresse ?nb_trous tresse =
  let n =
    match nb_trous, tresse with
    | Some n, _ -> n
    | None, [] -> 6
    | None, _ -> 1 + List.fold_left (fun m l -> max m l.indice) 0 tresse
  in
  (* fold_right parcourt la tresse à l'envers : auto(σ₁…σ_k) = φ_σ₁ ∘ … ∘ φ_σ_k appliqué à l'identité. *)
  List.fold_right agit tresse (identite n)

let tresse_de_entiers = List.map lettre_de_entier
let entiers_de_mot = List.map entier_de_lettre
