(** Le maillage à bord convexe de [python/Raccord.py] : étape 4 du plan OCaml (voir [plan_ocaml.md]), pour les
    films d'arcs ([Arcs]). L'étape 7c y ajoute le raccord du film conforme par triangulation mobile (la classe
    [RaccordTriangule] et ses outils). *)

open Triangulation

val insere : Maillage.t -> point -> Maillage.t * sommet
(** Ajoute le sommet p au maillage (sans courbes) : le triangle qui le contient est coupé en trois, ou, s'il est
    sur une arête, les deux triangles qui la bordent sont coupés en deux. Rend le nouveau maillage et l'indice du
    sommet (le dernier). Le Python modifie le maillage en place. Lève [Invalid_argument] si p est hors du
    maillage. *)

val maillage_du_raccord :
  ?marge:float -> ?par_cote:int -> point list -> point option -> float -> float -> Maillage.t * sommet list * sommet option
(** [maillage_du_raccord trous clou largeur hauteur] : maillage de Delaunay dont les sommets sont un bord convexe
    (rectangle bombé de [marge] = 40 pixels hors de l'image, [par_cote] = 6 points par côté), les trous puis le
    clou s'il y en a un. Les trous sont insérés de gauche à droite : leurs indices ne suivent pas l'ordre de la
    liste. Rend (maillage, indice de chaque trou dans l'ordre de la liste, indice du clou). *)

(** {1 Le raccord du film conforme (étape 7c)} *)

val transporte : point array list -> Triangle.t list -> point array -> point array -> point array list
(** [transporte lignes triangles avant apres] : images des lignes par l'application affine par triangles qui envoie
    les positions [avant] sur [apres] ([localise] et [transporte] du Python). Lève [Failure] si un point est hors du
    maillage. *)

type traversee = { position : float; arete : Arete.t; fraction : float }
(** Une traversée d'arête par une polyligne : position le long de la polyligne (indice du segment + fraction), arête,
    fraction de u vers v. *)

val coupe : point array -> Maillage.t -> sommet -> traversee list * traversee list
(** [coupe points maillage clou] : (suite réduite, toutes les traversées) des arêtes par une polyligne qui part du clou
    et y revient. La suite réduite annule les bigones et ne garde pas les traversées des arêtes du clou en tête et en
    queue. (La [coupe] du Python avec [brutes=True].) *)

val point_en : point array -> float -> point
val morceau : point array -> float -> float -> point array
(** Le morceau de la polyligne entre deux positions. *)

val reechantillonne : point array -> int -> point array
(** La polyligne en n points régulièrement espacés le long de sa longueur. *)

val arrondit : ?part:float -> ?depart:point -> ?arrivee:point -> trous:point array -> point array -> point array
(** La ligne brisée, coudes arrondis par des congés, jonctions tangentes aux directions [depart] et [arrivee], chaque
    arrondi tenu à l'écart des trous. *)

val decoupe_aux_aretes : point array -> Arete.t list -> point array -> point array list option
(** Coupe la polyligne aux traversées successives des arêtes données ; [None] si l'une manque. *)

type raccord
(** Le raccord d'une lettre ([RaccordTriangule] du Python) : le maillage à chaque instant de la fenêtre, et les
    dessins de départ et d'arrivée transportés jusqu'à chacun. *)

val raccord :
  ?sous_pas:int ->
  ?phases:float * float * float * float ->
  positions:(float -> float -> point array) ->
  clou:point ->
  largeur:float ->
  hauteur:float ->
  s_a:float ->
  r_a:float ->
  depart:point array list ->
  s_b:float ->
  r_b:float ->
  arrivee:point array list ->
  temps:float array ->
  tournants:int list ->
  unit ->
  raccord
(** [positions s r] : positions à l'écran des trous physiques au temps s avec la réduction r. [temps] : les temps des
    images de la fenêtre, strictement entre [s_a] et [s_b]. [tournants] : les deux trous physiques qui tournent.
    Lève [Failure] si un triangle se retourne entre deux sous-pas. *)

val reduction : raccord -> float -> float
(** La réduction (aplatissement supplémentaire) au temps s : interpolée entre [r_a] et [r_b]. *)

val aretes_du_maillage : raccord -> int -> (point * point) list
(** Les arêtes du maillage de l'image f de la fenêtre, comme couples de positions. *)

val lignes : ?sans_fantomes:bool -> ?libre:bool -> raccord -> int -> float -> point array list * (int * string) list
(** [lignes r f poids] : les lacets de l'image f de la fenêtre au poids donné (0 : départ, 1 : arrivée), et les
    anomalies (lacet, message) : traversées différentes entre les deux dessins. [sans_fantomes] (faux par défaut) : les
    cordes ne passent plus par les pieds posés sur les arêtes entre trous de la plus claire des deux lignes de construction
    (celle dont l'opacité est <= 1/2) : ces « points fantômes » n'imposent ni leur tangente ni leur position. [libre] (faux par
    défaut, implique [sans_fantomes]) : les cordes ne sont plus une ligne brisée aux coudes arrondis mais des paires d'arcs entre
    pieds, un pied sur la ligne la plus foncée imposant sa position et sa tangente (perpendiculaire à la ligne) ; voir [forme_libre]. *)
