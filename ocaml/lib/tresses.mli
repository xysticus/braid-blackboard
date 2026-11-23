(** Tresses et groupe libre : étape 1 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de la partie algébrique de [python/tresses.py] : mots de F_n, réduction, action d'Artin. *)

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

(** {1 Relecture d'un mot sur un dessin} *)

val lit_mot : Geometrie.point array -> Geometrie.point list -> Reduit.t
(** [lit_mot points trous] : le mot de F_n d'une polyligne. On note x_j (ou x_j⁻¹) à chaque traversée de gauche à
    droite (ou de droite à gauche) de la demi-droite qui monte du trou j (les trous sont numérotés à partir de 1,
    dans l'ordre de la liste), puis on réduit. *)

(** {1 Arcs de cercle raccordés} *)

val linspace : float -> float -> int -> float array
(** [linspace a b n] : n valeurs régulières de a à b (le [np.linspace] du Python). *)

val arc_de_cercle : ?pas:float -> Geometrie.point -> Geometrie.point -> Geometrie.point -> Geometrie.point array
(** [arc_de_cercle p t m] : polyligne de l'arc de cercle qui part de p dans la direction t (unitaire) et arrive en m,
    un point tous les [pas] pixels environ (1,5 par défaut). La corde [p; m] si l'arc est plat. *)

val raccord_egal :
  Geometrie.point -> Geometrie.point -> Geometrie.point -> Geometrie.point -> Geometrie.point option
(** Point de raccord de la paire d'arcs de p0 (direction t0) à p1 (direction t1), à égale distance des deux
    tangentes extrêmes ; [None] si les données sont alignées. *)

val deux_arcs : Geometrie.point -> Geometrie.point -> Geometrie.point -> Geometrie.point -> Geometrie.point array
(** Polyligne de p0 (direction t0) à p1 (direction t1) : deux arcs de cercle raccordés avec la même tangente
    (le [deux_arcs] du Python sans son argument [raccord], qui ne sert pas au film). *)

(** {1 Le méandre}

    Un lacet (l'image d'un générateur) est dessiné comme la suite des intervalles où il coupe l'axe : l'intervalle
    k est entre le trou k et le trou k + 1 (l'intervalle 0 à gauche du trou 1). Du point 2i au point 2i + 1 c'est un
    arc du haut, de 2i + 1 à 2i + 2 un arc du bas ; le premier et le dernier point descendent au clou. *)

val calcule_arcs : mot_de_fn -> (int * int) list
(** Les arcs d'un mot : chaque suite croissante consécutive ([x_1 x_2 x_3] : on passe au-dessus des trous 1, 2, 3)
    donne un arc du haut (indices pairs), chaque transition un arc du bas (indices impairs) ; le signe des
    extrémités donne le sens. Lève [Invalid_argument] sur le mot vide. *)

val intervalles : mot_de_fn -> int list
(** Les intervalles où le lacet du mot coupe l'axe. *)

val voisin : int array -> int -> bool -> int option
(** [voisin lacet j en_haut] : l'indice du point relié au point j par l'arc du haut (ou du bas) ; [None] si c'est
    le clou. *)

val suit_en_parallele : int array array -> int * int -> int * int -> bool -> int
(** Compare deux points (lacet, indice) d'un même intervalle en suivant les deux courbes côte à côte à partir de
    l'arc du haut (ou du bas) : -1 si p est à gauche, 1 à droite, 0 si elles arrivent ensemble au clou. *)

val compare_points : int array array -> int * int -> int * int -> int
(** Ordre gauche-droite de deux points d'un même intervalle (on essaie vers le haut puis vers le bas). *)

val abscisses : int array array -> int -> ((int * int, int) Hashtbl.t * int array * int)
(** [abscisses lacets nb_trous] : rang sur l'axe de chaque point (table indexée par (lacet, indice)), de chaque
    trou ([rang_trou.(k)] pour le trou k + 1 : le Python indexe à partir de 1), et nombre total de rangs. *)

(** Une paire d'arcs qui se croisent : deux cordes [(gauche, droite)] du même côté entrelacées, ou un arc du bas
    qui enjambe le départ d'une descente au clou. *)
type croisement = Arcs of (int * int) * (int * int) | Arc_et_descente of (int * int) * int

val croisements : int array array -> (int * int, int) Hashtbl.t -> croisement list
(** Vide si le dessin est correct. *)

val verifie : tresse -> bool
(** Aucun croisement dans le dessin des lacets de la tresse. *)

type etat = { trous : float array; lacets : float array list }
(** L'état d'un méandre (le tuple [(trous, lacets)] du Python) : abscisses des trous, et pour chaque lacet les
    abscisses de ses points sur l'axe, dans l'ordre du lacet. Seul l'ordre compte. *)

val etat_de_tresse : ?nb_trous:int -> tresse -> etat
(** L'état calculé depuis les mots : rangs des trous et des points. *)

val intervalle : float -> float array -> int
(** Nombre de trous à gauche de x : l'indice de son intervalle. *)

val normalise : etat -> etat
(** Remplace les abscisses par leurs rangs (même ordre). *)

val agit : etat -> sigma lettre -> etat
(** L'état non réduit après le demi-tour du bloc des trous i et i + 1 (le [detail] du Python n'est pas traduit).
    Ne pas confondre avec [conjugaison_locale], l'action d'Artin sur les mots. *)

type origine = Glisse of int | Tourne of int | Ne of int
(** L'origine d'un point de l'état non réduit : un point ancien hors du bloc qui tourne (il glisse avec son trou), un point ancien
    dans le bloc (il tourne), ou un point né sur un arc qui entre dans le bloc ou en sort (l'entier est l'indice de son point père,
    l'extrémité intérieure de l'arc). *)

val agit_origines : etat -> sigma lettre -> etat * origine array list
(** Comme [agit], avec pour chaque lacet l'origine de chacun de ses points. *)

val bigones : etat -> (int array * int array) list
(** Pour chaque lacet d'un état non réduit : le rang de chaque point dans le lacet réduit (-1 s'il s'annule) et son partenaire d'annulation (-1 sinon). *)

val reduit : etat -> etat
(** Supprime les bigones : deux points consécutifs d'un lacet dans le même intervalle s'annulent. *)

val verifie_action : tresse -> bool
(** En partant de la tresse vide et en appliquant les lettres une à une sans les mots, on retrouve à chaque pas
    l'état calculé depuis les mots. *)

(** {1 Dessin d'un état} *)

val demi_ellipse : ?pas:float -> float -> float -> bool -> float -> float -> Geometrie.point array
(** [demi_ellipse x1 x2 en_haut y_axe aplati] : de x1 à x2, au-dessus (ou au-dessous) de l'axe. *)

val descente_au_clou : float -> float -> float -> float -> float -> Geometrie.point array
(** [descente_au_clou xp y_haut y_sous x_clou y_clou] : du clou au point (xp, y_haut), arc de cercle (ou quart
    d'ellipse étiré) vertical en (xp, y_sous), puis segment vertical. *)

type geometrie = { abscisse : float -> float; y_axe : float; aplati : float; y_sous : float }
(** La géométrie du dessin d'un état (le dictionnaire [geo] que rend le [dessin_etat] du Python, réduit à ce qui
    sert) : l'abscisse à l'écran d'un point de l'axe, la hauteur de l'axe, l'aplatissement vertical des arcs, la
    hauteur sous tous les arcs du bas. *)

val geometrie_etat : ?hauteur:float -> ?largeur:float -> etat -> geometrie
(** La géométrie du dessin d'un état, sans le dessin (sert au film conforme). *)

val dessin_etat :
  ?hauteur:float -> ?largeur:float -> etat -> Geometrie.point array list list * Geometrie.point array * Geometrie.point
(** (pour chaque lacet, ses morceaux bout à bout : descente, arcs, remontée ; positions des trous ; clou).
    Sans les options [disque], [fusions] et [bosses] du Python (animations des anciens films), ni la géométrie
    qu'il rend en quatrième. *)

val polylignes : Geometrie.point array list list -> Geometrie.point array list
(** Les morceaux de chaque lacet mis bout à bout. *)
