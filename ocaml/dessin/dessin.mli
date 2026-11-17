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
