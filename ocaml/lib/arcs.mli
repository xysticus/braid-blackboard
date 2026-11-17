(** Films d'arcs entre trous, sans clou : étape 4 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de [python/Arcs.py] (piste 1 ter de [pistes_film_conforme.md]) : classes [FilmArcs] (un arc du
    trou fixe f_i au trou voyageur m_i, que l'on peut dessiner en ruban : son bord est le lacet x_i) et
    [DiagrammeCourbes] (le diagramme de courbes : les segments de l'axe, un seul point fixe à gauche).

    Les arcs sont posés sur la triangulation mobile ([Triangulation]) d'un maillage à bord convexe
    ([Raccord.maillage_du_raccord]), tendus par [Film.tend_courbes] et dessinés en droites et congés par
    [Film.polyligne_de_courbe] : en Python, ces classes héritent de [Film] et neutralisent son clou
    ([y_axe = -inf]) ; ici elles appellent seulement les deux fonctions dont elles ont besoin.

    Pas traduit : la tension hyperbolique ([hyperbolique=True], [python/Geodesiques.py]). Choix : persistant, comme
    [Film]. *)

open Triangulation

(** {1 Outils} *)

val coupe_arc : point array -> Maillage.t -> sommet -> sommet -> courbe
(** [coupe_arc points maillage debut fin] : la suite des arêtes coupées par une polyligne qui va du sommet [debut]
    au sommet [fin], bigones annulés ; un arc peut tourner autour de ses extrémités sans changer de classe, donc les
    traversées des arêtes de ses bouts, en tête et en queue, sont retirées. *)

val pchip : float array array -> float array array
(** Pentes de l'interpolation cubique d'Hermite monotone (Fritsch–Carlson) des valeurs [y.(k)] aux temps
    0, 1, 2… (chaque colonne à part) : la courbe ne dépasse jamais les valeurs entre deux temps, et sa dérivée est
    continue. *)

val hermite : float array array -> float array array -> float -> float array
(** [hermite y m t] : valeur au temps t de l'interpolation d'Hermite de valeurs [y] et de pentes [m]. *)

(** {1 Le film} *)

type fixes =
  | Bas  (** Trous fixes sur une ligne en bas, arcs de départ droits. *)
  | Gauche
      (** Trous fixes groupés sur l'axe, à gauche des trous voyageurs (f_n le plus à gauche), arcs de départ en
          demi-ellipses emboîtées sous l'axe. *)

type genre =
  | Arcs of fixes  (** [FilmArcs] : un arc f_i → m_i par générateur. *)
  | Diagramme  (** [DiagrammeCourbes] : les segments de l'axe. *)

type t = {
  genre : genre;
  hauteur : float;
  largeur : float;
  n : int;  (** Nombre de trous voyageurs. *)
  y_trous : float;  (** Hauteur de l'axe. *)
  largeurs : float array array;
      (** Pour chaque image clé, la largeur de chaque intervalle de l'axe (extrémités comprises), en fraction de
          la largeur utile : proportionnelle à 1 + la moitié du nombre de brins des lacets qui le traversent. *)
  pentes : float array array;  (** [pchip largeurs]. *)
  marge : float;
  marge_gauche : float;
  maillage : Maillage.t;
  voyageurs : sommet array;  (** [voyageurs.(i)] : le sommet de m_(i+1). *)
  fixes : sommet array;
  places : sommet array;  (** Le trou voyageur à chaque place de l'axe, de gauche à droite. *)
  numero : int;  (** Lettres déjà faites. *)
  courbes : courbe list;
  ecart : float;
}

val cree : ?hauteur:float -> ?largeur:float -> ?ecart:float -> ?ecart_fixes:float -> ?fixes:fixes -> Tresses.tresse -> t
(** Le constructeur [FilmArcs(tresse, ...)] (800 × 800, écart 6, trous fixes en bas par défaut). [ecart_fixes] :
    écart entre les trous fixes (en bas : groupés au milieu, par défaut répartis sur la largeur ; à gauche : 20 par
    défaut). Les arcs de départ sont découpés par [coupe_arc], puis 100 pas de tension. *)

val cree_diagramme : ?hauteur:float -> ?largeur:float -> ?ecart:float -> Tresses.tresse -> t
(** Le constructeur [DiagrammeCourbes(tresse, ...)] : point fixe au bout gauche de l'axe, arcs de départ = les
    segments de l'axe (un peu bombés pour la découpe, la tension les redresse). *)

val places_au_temps : t -> float -> float array
(** Abscisses des n places de l'axe au temps T (T = k : image clé k). *)

val lettre : ?images:int -> ?sous_pas:int -> ?taux:float -> ?rendu:(t -> unit) -> t -> Tresses.sigma Tresses.lettre -> t
(** Demi-tour des trous aux places i et i+1 (σ_i), à vitesse angulaire constante autour du milieu des deux places,
    pendant que toutes les places glissent ([places_au_temps]) ; 60 images de 3 sous-pas par défaut. *)

val polyligne : t -> int -> point array
(** L'arc k dessiné en droites et congés. *)

val ruban : ?largeur:float -> t -> int -> point array
(** Bord d'un ruban autour de l'arc k ([ecart] / 3 de large par défaut) : un lacet du trou fixe autour du trou
    voyageur, qui revient au trou fixe, dans le sens des mots de [lit_mot]. *)

val mots : t -> Tresses.Reduit.t list
(** Les mots relus sur les rubans (trous voyageurs triés par abscisse) ; pour le diagramme, seulement celui du
    premier arc (le lacet x_1), la seule vérification directe. *)

val verifie_arcs : ?ecart_fixes:float -> ?fixes:fixes -> Tresses.tresse -> bool
(** Après chaque lettre (12 images), les mots relus sur les rubans sont ceux de [calcule_autofn_de_tresse]. *)

val verifie_diagramme : Tresses.tresse -> bool
(** Après chaque lettre, le mot relu sur le ruban du premier arc est l'image de x_1. *)
