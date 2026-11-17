(** Un escargot fait de rubans : traduction de [python/Escargot.py] (le dessin est dans [Dessin.cadre_escargot]).

    Les trous fixes, groupés au bout gauche de l'axe, sont la queue. Chaque arc va d'un trou fixe à un trou
    voyageur ; au départ, ce sont des demi-ellipses emboîtées sous l'axe (comme [Arcs.cree ~fixes:Gauche]). Puis les
    trous voyageurs suivent une chorégraphie libre, et la triangulation mobile emporte les arcs (isotopie : jamais de
    croisement) :
    - la coquille : un anneau de trous monte au-dessus du corps et tourne plusieurs tours ; les arcs qui y
      aboutissent s'enroulent en spirale, chaque tour ajoutant une couche ;
    - la tête : un trou qui va à l'avant, au sol ; les arcs des yeux passent dessous ;
    - les yeux : deux trous partent devant la tête puis montent en s'écartant (les antennes).

    Pas de tresse ici : le mouvement n'est pas fait de demi-tours sur l'axe. En Python, [Escargot] hérite de
    [FilmArcs] ; ici c'est un type à part, qui se sert des mêmes outils ([Arcs.coupe_arc],
    [Raccord.maillage_du_raccord], [Film.tend_courbes], [Film.polyligne_de_courbe]). Choix : persistant. *)

open Triangulation

val lisse : float -> float
(** Rampe douce de 0 à 1 sur [0, 1] (3x² - 2x³), constante au-dehors. *)

type t = {
  largeur : float;
  hauteur : float;
  e : float;  (** Échelle : longueurs en pixels d'une image de 960 de large, multipliées par [e]. *)
  anneau : int;  (** Nombre de trous de la coquille. *)
  tours : float;  (** Tours faits par la coquille. *)
  n : int;  (** Trous voyageurs : l'anneau, la tête, puis les deux yeux. *)
  y_axe0 : float;  (** Hauteur de l'axe de départ (le sol). *)
  depart : point array;  (** Positions de départ des trous voyageurs. *)
  maillage : Maillage.t;
  voyageurs : sommet array;
  fixes : sommet array;
  courbes : courbe list;  (** [courbes] k : l'arc du trou fixe k au trou voyageur k. *)
  ecart : float;
}

val cree : ?largeur:float -> ?hauteur:float -> ?ecart:float -> ?anneau:int -> ?tours:float -> unit -> t
(** 960 × 640, écart 7, anneau de 4 trous, 3 tours par défaut. Arcs de départ découpés par [Arcs.coupe_arc], puis
    100 pas de tension. *)

(** {1 La chorégraphie (temps en secondes)} *)

val centre_coquille : t -> float -> point
val rayon_anneau : t -> float -> float
val tours_faits : t -> float -> float

val choregraphie : t -> float -> point array
(** Positions des trous voyageurs au temps t. *)

val deplace : ?taux:float -> t -> point array -> float -> t
(** [deplace escargot cibles pas_max] : amène les trous voyageurs aux cibles en ligne droite, par sous-pas d'au plus
    [pas_max] pixels (le plus long des déplacements), avec retournements d'arêtes et un pas de tension (taux 0,15)
    à chaque sous-pas. Lève [Failure] si un triangle se retourne. *)

val polyligne : t -> int -> point array
(** L'arc k dessiné en droites et congés. *)
