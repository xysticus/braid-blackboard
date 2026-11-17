(** Tresses et groupe libre : étape 1 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de la partie algébrique de [programmes/tresses.py] : mots de F_n, réduction, action d'Artin. *)

(** {1 Lettres}

    Une lettre est un générateur ou son inverse. Le même type sert aux deux alphabets :
    x_i, x_i⁻¹ pour les mots de F_n, σ_i, σ_i⁻¹ pour les tresses. En Python ce sont des entiers non nuls
    ([i] ou [-i]) : ici, l'entier nul n'a pas de représentant. *)

type signe = Plus | Moins

type lettre = { indice : int; signe : signe }
(** [indice] ≥ 1. *)

val inverse_lettre : lettre -> lettre

val lettre_de_entier : int -> lettre
(** [lettre_de_entier 3] = x_3, [lettre_de_entier (-3)] = x_3⁻¹. Lève [Invalid_argument] sur 0. *)

val entier_de_lettre : lettre -> int

(** {1 Mots de F_n} *)

type mot = lettre list

val inverse : mot -> mot
(** (a b c)⁻¹ = c⁻¹ b⁻¹ a⁻¹. *)

(** Les mots réduits (sans x x⁻¹ ni x⁻¹ x côte à côte). Le type est privé : on ne peut en fabriquer un
    qu'en réduisant, donc tout [Reduit.t] est réduit. On peut le lire comme une liste (coercion [:>]). *)
module Reduit : sig
  type t = private mot

  val de_mot : mot -> t
  (** Réduction libre. *)

  val produit : t list -> t
  (** Produit réduit de mots réduits. *)

  val inverse : t -> t
end

(** {1 Tresses et action d'Artin} *)

type tresse = lettre list
(** σ_i est [{indice = i; signe = Plus}]. *)

type automorphisme = Reduit.t array
(** [a.(i)] est l'image de x_(i+1), comme [images[i]] en Python. *)

val identite : int -> automorphisme
(** [identite n] : x_i ↦ x_i pour i = 1..n. *)

val agit : lettre -> automorphisme -> automorphisme
(** Composition par l'automorphisme d'Artin de σ (le [conjugaison_locale] du Python, sans effet de bord) :
    σ_i⁺ : (u, v) ↦ (u v u⁻¹, u), σ_i⁻ : (u, v) ↦ (v, v⁻¹ u v), où u, v sont les images de x_i, x_(i+1). *)

val auto_de_tresse : ?nb_trous:int -> tresse -> automorphisme
(** [calcule_autofn_de_tresse] : parcourt la tresse à l'envers. Par défaut, nb_trous = 1 + le plus grand indice
    (6 pour la tresse vide, comme en Python). *)

(** {1 Entrées et sorties en entiers, pour comparer au Python} *)

val tresse_de_entiers : int list -> tresse
val entiers_de_mot : mot -> int list
