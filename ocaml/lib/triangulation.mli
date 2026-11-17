(** Triangulation mobile : étape 2 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de la classe [Maillage] et de [maillage_initial] de [programmes/Triangulation.py] : triangles,
    orientation, critère de Delaunay, retournement d'arête (flip) et mise à jour des courbes posées sur les arêtes.
    Le mouvement des trous, la tension et le dessin sont dans [Film] (étape 3).

    Choix : structure {e persistante}. Le Python modifie le maillage et les courbes en place ([retourne]) ; ici
    [retourne] et [delaunay] rendent un nouveau maillage et de nouvelles courbes, et [deplace] un maillage aux
    sommets déplacés. *)

(** {1 Géométrie} *)

type point = Geometrie.point = { x : float; y : float }
(** Le même type que [Geometrie.point] (égalité de types exposée : on peut passer l'un pour l'autre). *)

val croix : point -> point -> float
(** Produit vectoriel (déterminant) de deux vecteurs : > 0 si on tourne dans le sens direct de u vers v. *)

(** {1 Sommets, arêtes, triangles}

    Un sommet est un indice dans le tableau des positions. En Python, une arête est un tuple [(u, v)] avec
    [u < v] et un triangle un [frozenset] de trois indices : ce sont des conventions que rien ne vérifie. Ici les
    deux types sont privés : on ne les fabrique qu'avec [Arete.v] et [Triangle.v], qui rangent les sommets ; deux
    écritures d'une même arête sont donc égales. *)

type sommet = int

module Arete : sig
  type t = private sommet * sommet
  (** [(u, v)] avec [u < v]. *)

  val v : sommet -> sommet -> t
  (** [v a b] = [v b a]. Lève [Invalid_argument] si [a = b]. *)

  val compare : t -> t -> int
end

module Triangle : sig
  type t = private sommet * sommet * sommet
  (** Les trois sommets rangés. *)

  val v : sommet -> sommet -> sommet -> t
  val compare : t -> t -> int

  val aretes : t -> Arete.t list
  (** Les trois côtés. *)

  val oppose : t -> Arete.t -> sommet
  (** Le sommet qui n'est pas sur l'arête ([next(iter(t - {a, c}))] en Python). *)
end

module Triangles : Map.S with type key = Triangle.t
module Aretes : Map.S with type key = Arete.t

(** {1 Courbes posées sur les arêtes} *)

(** Un noeud de courbe. En Python : [('v', s)] ou [('e', u, v, w)]. *)
type noeud =
  | Sommet of sommet
  | Sur_arete of Arete.t * float
      (** Point de l'arête (u, v) à la fraction w de u vers v, 0 < w < 1. *)

type courbe = noeud list
(** Deux noeuds consécutifs sont dans un même triangle. *)

(** {1 Le maillage} *)

type orientation = Direct | Indirect
(** Le [signe] du Python vaut 1 ou -1. *)

(** Le maillage : positions des sommets, et pour chaque triangle son orientation à la création (le [signes] du
    Python ; ses clés sont les triangles, que le Python garde aussi à part dans [triangles]). *)
module Maillage : sig
  type t = private { pos : point array; signes : orientation Triangles.t }

  val cree : point array -> Triangle.t list -> t
  (** Le constructeur [Maillage(pos, triangles)]. *)

  val deplace : t -> point array -> t
  (** Le même maillage, sommets à de nouvelles positions (le Python écrit dans [m.pos]). Les orientations
      notées à la création des triangles restent : [valide] dit ensuite si un triangle s'est retourné. *)

  val triangles : t -> Triangle.t list

  val signe : t -> Triangle.t -> orientation
  (** Orientation actuelle du triangle (sommets dans l'ordre rangé). *)

  val aretes : t -> Triangle.t list Aretes.t
  (** Pour chaque arête, les triangles qui la bordent (un ou deux). *)

  val valide : t -> bool
  (** Aucun triangle retourné : chaque triangle a gardé son orientation. *)

  val convexe : t -> sommet -> sommet -> sommet -> sommet -> bool
  (** Le quadrilatère a, b, c, d est strictement convexe. *)

  val cotangente : t -> sommet -> sommet -> sommet -> float
  (** Cotangente de l'angle en [sommet] du triangle ([sommet], x, y). *)

  val cherche_arete_a_retourner : t -> (sommet * sommet * sommet * sommet) option
  (** Une arête intérieure ac qui n'est pas de Delaunay (angles opposés en b et d de somme > π), dont le
      quadrilatère abcd est convexe et bd pas déjà une arête : [Some (a, b, c, d)]. *)

  val position : t -> noeud -> point

  val coupe : t -> noeud -> noeud -> sommet -> sommet -> noeud
  (** Le noeud où la corde de u à v coupe l'arête bd. Lève [Failure] si elle ne la coupe pas. *)

  val courbe_apres_flip : t -> courbe -> sommet -> sommet -> sommet -> sommet -> courbe
  (** La courbe après le flip ac → bd : ses points sur ac disparaissent (la corde relie leurs voisins), et chaque
      corde qui va du côté de a (arêtes ab, da, sommet a) au côté de c (arêtes bc, cd, sommet c) coupe bd en un
      point nouveau. La forme de la courbe ne change pas. *)

  val retourne : t -> sommet -> sommet -> sommet -> sommet -> courbe list -> t * courbe list
  (** Remplace la diagonale ac du quadrilatère abcd par bd. *)

  val delaunay : t -> courbe list -> t * courbe list
  (** Retourne les arêtes qui ne sont pas de Delaunay jusqu'à ce qu'il n'y en ait plus. Lève [Failure] après
      10 000 flips. *)
end

(** {1 Le maillage de départ} *)

val decalage_axe : float
(** [DECALAGE_AXE] : les trous sont un peu sous l'axe de dessin. *)

val decalage_bord : float
(** [DECALAGE_BORD] : les sommets des bords ne sont pas exactement à la verticale des trous. *)

type maillage_initial = {
  maillage : Maillage.t;
  trous : sommet list;
  clou : sommet;
  haut : sommet list;  (** Rangée du bord haut : coins et un sommet à la verticale de chaque trou. *)
  bas : sommet list;  (** Rangée du bord bas, sans le clou. *)
}
(** Le Python rend un tuple [(maillage, trous, clou, haut, bas)]. *)

val maillage_initial :
  ?decalage_bas:float -> point list -> point -> float -> float -> maillage_initial
(** [maillage_initial trous clou hauteur largeur] : triangulation de départ en deux bandes (bord haut → axe,
    axe → bord bas avec le clou), chacune en échelle de triangles, puis [delaunay]. [hauteur] ne sert pas
    (comme en Python, où les bords sont placés par le clou et par y = 3). *)

val noeuds_de_polyligne : point array -> Maillage.t -> sommet -> courbe
(** [noeuds_de_polyligne points maillage clou] : la courbe (suite des arêtes coupées) d'une polyligne qui part du
    clou et y revient, bigones retirés. *)
