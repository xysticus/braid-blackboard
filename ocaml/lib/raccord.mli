(** Le maillage à bord convexe de [python/Raccord.py] : étape 4 du plan OCaml (voir [plan_ocaml.md]), pour les
    films d'arcs ([Arcs]). Seule la construction du maillage est traduite ; le raccord du film conforme reste en
    Python. *)

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
