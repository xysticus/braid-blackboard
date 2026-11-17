(** Tresses et groupe libre : étape 1 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de la partie algébrique de [programmes/tresses.py] : mots de F_n, réduction, action d'Artin. *)

(** {1 Lettres et alphabets}

    Une lettre est un générateur ou son inverse. Deux alphabets : x_i, x_i⁻¹ pour les mots de F_n, σ_i, σ_i⁻¹ pour
    les tresses. En Python ce sont des entiers non nuls ([i] ou [-i]) : ici, l'entier nul n'a pas de représentant.

    Le paramètre ['alphabet] de [lettre] est un {e type fantôme} : il n'apparaît dans aucun champ, il n'existe qu'à la
    compilation. [x lettre] et [sigma lettre] ont la même représentation, mais le compilateur refuse de les confondre :
    une tresse passée là où l'on attend un mot de F_n est une erreur de type, par exemple

    {[
      let t : tresse = tresse_de_entiers [ 1; -2 ]
      let _ = Reduit.simplifie t
    ]}
    {v
Error: The value t has type tresse = sigma lettre list
       but an expression was expected of type mot_de_fn = x lettre list
       Type sigma lettre is not compatible with type x lettre
       Type sigma is not compatible with type x
    v}
    (message abrégé : le compilateur préfixe chaque type par [Ardoise.Tresses.] ; l'exemple complet est dans
    [ocaml/exemples/confusion.ml]).

    Les fonctions qui ne dépendent pas de l'alphabet ([inverse_lettre], [inverse], [entiers_de_mot]) sont
    polymorphes en ['alphabet] : écrites une fois, elles servent aux deux. *)

type x
(** L'alphabet de F_n. Type vide : il ne sert qu'à étiqueter. *)

type sigma
(** L'alphabet des tresses. *)

type signe = Plus | Moins

type 'alphabet lettre = { indice : int; signe : signe }
(** [indice] ≥ 1. *)

val inverse_lettre : 'a lettre -> 'a lettre

val lettre_de_entier : int -> 'a lettre
(** [lettre_de_entier 3] = x_3 ou σ_3 selon le type attendu, [lettre_de_entier (-3)] = x_3⁻¹ ou σ_3⁻¹.
    Lève [Invalid_argument] sur 0. *)

val entier_de_lettre : 'a lettre -> int

(** {1 Mots de F_n} *)

type mot_de_fn = x lettre list

val inverse : 'a lettre list -> 'a lettre list
(** (a b c)⁻¹ = c⁻¹ b⁻¹ a⁻¹, dans les deux alphabets. *)

(** Les mots réduits de F_n (sans x x⁻¹ ni x⁻¹ x côte à côte) : la forme normale de F_n, deux mots réduits
    sont égaux ssi ils représentent le même élément. Rien de tel pour les tresses (relations σ₁σ₂σ₁ = σ₂σ₁σ₂,
    σ₁σ₃ = σ₃σ₁) : [Reduit] n'accepte que l'alphabet [x].

    Le type est privé : on ne peut en fabriquer un qu'en réduisant, donc tout [Reduit.t] est réduit. On peut le lire
    comme un [mot_de_fn] (coercion [:>]). *)
module Reduit : sig
  type t = private mot_de_fn

  val simplifie : mot_de_fn -> t
  (** Réduction libre. *)

  val produit : t list -> t
  (** Produit réduit de mots réduits. *)

  val inverse : t -> t
end

(** {1 Tresses et action d'Artin} *)

type tresse = sigma lettre list
(** σ_i est [{indice = i; signe = Plus}]. *)

type automorphisme = Reduit.t array
(** [a.(i)] est l'image de x_(i+1), comme [images[i]] en Python. *)

val morphisme_identite : int -> automorphisme
(** [morphisme_identite n] : x_i ↦ x_i pour i = 1..n. Différence avec le Python : on donne le nombre de
    générateurs n, le Python donne le plus grand indice de la tresse (n - 1). *)

val conjugaison_locale : sigma lettre -> automorphisme -> automorphisme
(** Composition par l'automorphisme d'Artin de σ :
    σ_i⁺ : (u, v) ↦ (u v u⁻¹, u), σ_i⁻ : (u, v) ↦ (v, v⁻¹ u v), où u, v sont les images de x_i, x_(i+1).
    Différence avec le Python : pas d'effet de bord, on rend un nouveau tableau. (Ne pas confondre avec le
    [agit] du Python, qui est l'action de σ_i sur l'état d'un méandre.) *)

val calcule_autofn_de_tresse : ?nb_trous:int -> tresse -> automorphisme
(** Parcourt la tresse à l'envers, comme le Python. Par défaut, nb_trous = 1 + le plus grand indice
    (6 pour la tresse vide, comme en Python). *)

(** {1 Entrées et sorties en entiers, pour comparer au Python} *)

val tresse_de_entiers : int list -> tresse
val mot_de_fn_de_entiers : int list -> mot_de_fn
val entiers_de_mot : 'a lettre list -> int list
