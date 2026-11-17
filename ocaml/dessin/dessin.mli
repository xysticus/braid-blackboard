(** Dessin et film : étape 5 du plan OCaml (voir [plan_ocaml.md]).
    Traduction de [peint] et [ENCODEUR] de [python/tresses.py], de [Film.cadre] et [film_triangule] de
    [python/Triangulation.py]. Le dessin se fait avec cairo2, le film est écrit au fil du calcul par un tube vers
    ffmpeg. *)

open Ardoise

type couleur = float * float * float

val couleurs : couleur array
(** Les six couleurs des lacets, reprises dans l'ordre des générateurs. *)

val peint :
  ?hauteur:int -> ?largeur:int -> ?largeur_brin:float -> ?en_couleur:bool -> ?axe:Geometrie.point array list ->
  Geometrie.point array list -> Geometrie.point list -> Geometrie.point -> Cairo.Surface.t
(** [peint polylignes trous clou] : surface Cairo (400 × 400 par défaut) sur fond blanc, les polylignes en
    couleur (en noir sans [en_couleur]), les trous et le clou en disques noirs de rayon [largeur_brin]. [axe] :
    des polylignes tracées en gris sous les lacets (le Python accepte aussi des morceaux avec leur opacité, qui ne
    servent qu'aux anciens films). *)

val cadre : ?lisse:bool -> ?largeur_brin:float -> ?avec_aretes:bool -> ?ecart:float -> Film.t -> Cairo.Surface.t
(** L'image du film à cet instant ([Film.cadre] du Python) : lacets en droites et congés ([Film.polylignes]),
    arêtes de la triangulation en gris. Trait de 3 px pour 400 de large, au plus 70 % de [ecart] (mais au moins
    1 px) : les brins serrés sont plus fins. *)

val encodeur : string list
(** [ENCODEUR] : AV1 (libsvtav1), yuv420p. *)

val film_triangule :
  ?ffmpeg:string -> ?vitesse:float -> ?pause:float -> ?largeur_brin:float -> ?hauteur:float -> ?largeur:float ->
  Tresses.tresse -> string -> unit
(** [film_triangule tresse fichier] : film MP4 à 25 images/s, un demi-tour continu par lettre, les trous avançant
    à vitesse constante ([Film.lettre]). Pas de pause entre les lettres ; [pause] secondes (0,5 par défaut) sur la
    première image, trois fois plus sur la dernière. [ffmpeg] : le programme à lancer (cherché dans le PATH). *)

(** {1 Films d'arcs (étape 4)} *)

val couleurs_arcs : couleur array
(** Les [COULEURS] de [python/Arcs.py], un peu plus sombres que celles des lacets. *)

val cadre_arcs : ?rubans:bool -> ?largeur_brin:float -> ?avec_aretes:bool -> ?lisere:bool -> Arcs.t -> Cairo.Surface.t
(** L'image d'un film d'arcs ([FilmArcs.cadre] du Python) : arcs (ou leurs rubans, avec [rubans]) en couleur,
    trait de 2,5 px ; avec [lisere], chaque arc tracé en blanc large (0,85 × [ecart]) avec un liseré de couleur fin
    au milieu (impression d'un écart entre brins voisins). Trous voyageurs en noir, trous fixes en gris. *)

val film_arcs :
  ?ffmpeg:string -> ?rubans:bool -> ?pause:float -> ?lisere:bool -> ?images:int -> Arcs.t -> Tresses.tresse -> string -> unit
(** [film_arcs film tresse fichier] : film MP4 à 25 images/s, [images] = 60 images par lettre. Le Python prend la
    classe et ses options ; ici on passe le film déjà construit ([Arcs.cree] ou [Arcs.cree_diagramme]). *)

(** {1 L'escargot} *)

val cadre_escargot : Escargot.t -> float -> Cairo.Surface.t
(** L'image de l'escargot au temps t ([Escargot.dessine] du Python) : fond vert ; chaque arc tracé en ruban plein
    (trait large cerné de brun sombre) : dans la coquille (disque autour de l'anneau, qui grandit avec les tours),
    en bandes brun, beige et marron selon l'arc ; ailleurs, couleur chair ; les yeux au bout des antennes. *)

val film_escargot :
  ?ffmpeg:string -> ?duree:float -> ?images_par_seconde:int -> ?pause:float -> Escargot.t -> string -> unit
(** [film_escargot escargot fichier] : film MP4 de [duree] = 12 s à 25 images/s, la dernière image tenue [pause] =
    2 s ; chaque image déplace les trous vers la chorégraphie par sous-pas d'au plus 2 px. *)
