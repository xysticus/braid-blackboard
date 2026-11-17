(** Transport et tension : étapes 3 et 3 bis du plan OCaml (voir [plan_ocaml.md]).
    Traduction de la classe [Film] de [programmes/Triangulation.py] : les trous tournent ([trous_au_temps],
    [place], [abscisses], [chemin_des_trous], [lettre]), les points des lacets suivent leurs arêtes, les flips
    gardent la triangulation de Delaunay, les brins se tendent ([monotone], [tend]) ; dessin en droites et congés
    ([portions_du_clou], [polyligne]) et relecture des mots ([mots]).

    Le constructeur [cree] ([Film.__init__] du Python) part du dessin d'un état de méandre ([etat_de_tresse],
    [dessin_etat] de [Tresses], [noeuds_de_polyligne] de [Triangulation], [disposition]).

    Choix : toujours persistant. [place], [tend] et [lettre] rendent un nouveau film ; seuls les tableaux de
    positions et de courbes sont recopiés à chaque sous-pas (quelques dizaines de sommets, quelques centaines de
    noeuds). *)

open Triangulation

val sens_de_sigma : float
(** [SENS_DE_SIGMA] = 1 : σ_i positif fait tourner la paire dans le sens horaire à l'écran (y vers le bas). *)

val vitesse_par_defaut : float
(** [VITESSE] = 6 : pixels parcourus par l'ensemble des trous à chaque image, pour 800 pixels de large. *)

val monotone : float list -> float list
(** Régression monotone croissante (moindres carrés) : on empile les valeurs en blocs, et deux blocs voisins
    dans le mauvais ordre fusionnent en leur moyenne pondérée. *)

type disposition = { abscisses : float array; ecart : float }
(** Le tuple [(xs, ecart)] du Python : abscisses des trous de gauche à droite, écart entre deux brins. *)

type t = {
  hauteur : float;
  largeur : float;
  nb_trous : int;
  dispositions : disposition array;  (** Une par image clé. *)
  milieux : disposition array;  (** Une par lettre : au milieu du demi-tour. *)
  etape : int;  (** Indice de l'image clé courante. *)
  maillage : Maillage.t;
  trous : sommet array;  (** [trous.(j)] : le sommet du trou à la place j (de gauche à droite). *)
  clou : sommet;
  haut : sommet array;  (** Rangée du bord haut, coins compris. *)
  bas : sommet array;  (** Rangée du bord bas, coins compris. *)
  decalage_bas : float;
  place_du_clou : int * float;  (** Le clou est entre [bas.(j)] et [bas.(j + 1)], à la fraction f. *)
  y_axe : float;
  courbes : courbe list;
}

val tend : ?degagement:float -> ?portee_sinus:float -> t -> float -> float -> t
(** [tend film taux ecart] : un pas de tension. Chaque point est tiré, d'une fraction [taux] du chemin, vers
    l'endroit de son arête où ses deux voisins sont alignés avec lui ; puis, arête par arête, les points gardent
    leur ordre et restent à [ecart] les uns des autres perpendiculairement aux brins (ecart / sinus le long de
    l'arête, sinus borné à 0,3) et à [degagement] (par défaut [ecart]) des sommets. [portee_sinus] > 0 : le sinus
    est mesuré avec des points du brin à au moins cette distance. *)

val trous_au_temps : t -> Tresses.sigma Tresses.lettre -> float -> point array * float array * float * float * float
(** [(positions des trous de gauche à droite, abscisses des places, milieu, rayon, angle)] au temps u de la
    lettre : glissement des places ([abscisses]) et demi-tour de la paire. *)

val place : t -> Tresses.sigma Tresses.lettre -> float -> t
(** Les sommets au temps u : trous, bords (qui se croisent sans se rejoindre), clou. À u = 1, les deux trous
    échangent leurs places et l'on passe à l'image clé suivante. *)

val abscisses : t -> float -> disposition
(** Au temps u de la lettre courante : interpolation linéaire de l'image clé vers le milieu de la lettre, puis
    du milieu vers l'image clé suivante. *)

val chemin_des_trous : ?echantillons:int -> t -> Tresses.sigma Tresses.lettre -> float array * float array
(** (temps échantillonnés, longueur cumulée du chemin parcouru par l'ensemble des trous). *)

val lettre :
  ?images:int -> ?sous_pas:int -> ?taux:float -> ?vitesse:float -> ?rendu:(t -> float -> unit) ->
  t -> Tresses.sigma Tresses.lettre -> t * int
(** Un demi-tour à vitesse constante : à chaque sous-pas, [place], contrôle qu'aucun triangle ne s'est retourné
    (sinon [Failure]), [delaunay], [tend]. [rendu film ecart] est appelé à chaque image (tous les [sous_pas]
    sous-pas). Rend le film et le nombre d'images. *)

val portions_du_clou : t -> courbe -> ((int * int) * float) list
(** Les deux bouts d'une courbe attachés au clou : [((début, fin), x)], les indices [début .. fin - 1] des points
    avant le premier passage au-dessus de l'axe (puis après le dernier), et l'abscisse du passage. *)

val polyligne : ?lisse:bool -> ?part_du_conge:float -> t -> int -> point array
(** La polyligne dessinée de la courbe k : la ligne brisée de ses points (sans [lisse]), ou, avec, chaque coude
    arrondi par un congé (paire d'arcs tangents aux deux segments, au plus [part_du_conge] du plus court), et les
    brins du clou qui partent de l'axe perpendiculairement. *)

val polylignes : ?lisse:bool -> t -> point array list
val positions_des_trous : t -> point array

val mots : ?lisse:bool -> t -> Tresses.Reduit.t list
(** Les mots relus sur le dessin ([lit_mot], trous triés par abscisse). *)

(** {1 Le constructeur} *)

val disposition : int -> float -> Tresses.etat -> disposition
(** [disposition nb_trous largeur etat] : la largeur de chaque intervalle de l'axe (y compris les deux des bords)
    est proportionnelle à 1 + le nombre de brins qui le traversent, donc l'écart entre deux points consécutifs de
    l'axe est le même partout. (Une méthode en Python, qui lit [nb_trous] et [largeur] dans le film.) *)

val cree : ?hauteur:float -> ?largeur:float -> ?tension:int -> Tresses.tresse -> t
(** Le constructeur [Film(tresse, hauteur, largeur)] (800 × 800 par défaut) : dispositions des images clés et des
    milieux de lettre, dessin de départ ([dessin_etat]) replacé sur la disposition 0 et étiré dans la bande du
    haut, maillage de départ, courbes ([noeuds_de_polyligne]), puis [tension] pas de tension (400 par défaut,
    comme le Python, qui n'a pas cet argument). *)
