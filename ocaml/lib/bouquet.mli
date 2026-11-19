(** Le premier bouquet : traduction de la classe [Pousse] de [python/Bouquet.py] (le dessin est dans la page web, voir
    [web/ardoise.js]).

    Les trous ne font plus des demi-tours sur l'axe : ils suivent une chorégraphie libre. Les lacets, posés sur la
    triangulation mobile de [Film], sont emportés par la déformation du plan et tendus mollement. Les trous dorment sous
    terre (la graine, en rang serré au-dessus du clou) ; des groupes de trous en sortent comme des pousses.
    - une {e fleur} : sépales et pétales en alternance sur un petit cercle ; le bourgeon tourne sur lui-même (les lacets
      s'y enroulent en couches), puis les sépales s'arrêtent et retiennent le bourgeon pendant que les pétales en
      sortent : la fleur éclot ;
    - une {e feuille} : deux trous qui s'écartent sur le côté.

    Choix : persistant, comme [Film] et [Escargot]. Les longueurs sont en pixels d'une image de 800 de large, multipliées
    par [e] = largeur / 800. *)

open Geometrie

val lisse : float -> float
val bezier : point -> point -> point -> float -> point
(** [bezier p0 p1 p2 s] : point de la courbe de Bézier quadratique au paramètre s. *)

type fleur = {
  tete : float * float;  (** abscisse, hauteur au-dessus du bas de l'image *)
  depart : float;
  couleur : float * float * float;
  sens : float;
  nutation : float;
  petales : int;
  duree_montee : float;
  duree_bourgeon : float;
  duree_eclosion : float;
  tours : float;
  rayon_bourgeon : float;
  rayon_sepales : float;
  rayon_fleur : float;
  courbure : float;
}

type feuille = {
  tete : float * float;
  depart : float;
  angle : float;  (** radians *)
  longueur : float;
  longueur_bourgeon : float;
  nutation : float;
  duree_montee : float;
  duree_eclosion : float;
  courbure : float;
}

type groupe = Fleur of fleur | Feuille of feuille

val fleur :
  ?nutation:float -> ?sens:float -> ?petales:int -> ?duree_montee:float -> ?duree_bourgeon:float -> ?duree_eclosion:float ->
  ?tours:float -> ?rayon_bourgeon:float -> ?rayon_sepales:float -> ?rayon_fleur:float -> ?courbure:float ->
  tete:float * float -> depart:float -> couleur:float * float * float -> unit -> groupe
(** Les réglages par défaut de [fleur] du Python. *)

val feuille :
  ?longueur:float -> ?longueur_bourgeon:float -> ?nutation:float -> ?duree_montee:float -> ?duree_eclosion:float ->
  ?courbure:float -> tete:float * float -> depart:float -> angle:float -> unit -> groupe

val bouquet : groupe list
(** Le premier bouquet : deux feuilles, trois fleurs (rose, jaune, mauve), deux feuilles. *)

val nb_trous_du_groupe : groupe -> int
(** 2 pour une feuille, 2 × pétales + 1 pour une fleur (un sépale de plus). *)

type t = {
  film : Film.t;  (** le maillage et les courbes (la tresse de départ ne sert qu'à construire l'état initial) *)
  groupes : groupe array;
  largeur : float;
  hauteur : float;
  e : float;
  ecart : float;
  taux : float;
  y_sol : float;
  graine : point array;  (** la place de chaque trou dans la graine, de gauche à droite *)
  premier : int array;  (** [premier.(n)] : le rang du premier trou de la plante n ; un élément de plus *)
}

val cree : ?hauteur:float -> ?largeur:float -> ?taux:float -> groupe list -> t
(** 1080 × 810 (portrait 3:4), taux 0,12 par défaut. Construit l'état de départ d'une tresse à autant de brins que de
    trous, puis rassemble les trous sous terre (la graine) sans le montrer. *)

(** {1 La chorégraphie (temps en secondes)} *)

val phases : groupe -> float -> float * float * float
(** (montée, bourgeon, éclosion) du groupe au temps t, chacune de 0 à 1. *)

val centre : t -> int -> float -> point
(** Centre de la plante n : de la graine à sa tête le long d'une tige de Bézier, en oscillant un peu (nutation). *)

val direction_de_tige : t -> int -> point
(** Direction (unitaire) de la tige sous la tête, celle de la courbe de Bézier à son arrivée, retournée. *)

val trous_de_fleur : t -> int -> float -> point array
val trous_de_feuille : t -> int -> float -> point array

val choregraphie : t -> float -> point array
(** Positions de tous les trous au temps t (de gauche à droite dans la graine). *)

val deplace : t -> point array -> float -> t
(** [deplace pousse cibles pas_max] : amène les trous en ligne droite à leurs cibles par sous-pas d'au plus [pas_max]
    pixels, en retournant les arêtes et en tendant les lacets à chaque sous-pas. Lève [Failure] si un triangle se
    retourne. *)

val positions : t -> point array
val polylignes : t -> point array list
(** Les lacets en droites et congés (sans brin du clou). *)

val plante_du_lacet : t -> int array
(** Pour chaque lacet, la plante dont il entoure un trou. *)
