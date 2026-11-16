# Ardoise à tresse

Un notebook pour dessiner des éléments du groupe de tresse (Artin braid group).

<p align="center"><img src="imgs/bouquet_iris.jpg" alt="Trois iris faits de lacets" width="420"></p>

<p align="center"><em>Action d'Artin du groupe des tresses sur le groupe fondamental du disque troué,
ou croissance d'iris des calanques dans F₃₅. Il n'y a que 35 lacets.</em></p>

Le bouquet est un film (`programmes/Bouquet.py`) : les trous d'un disque bougent, et les 35 lacets qui les
entourent, transportés sans jamais se couper, poussent en tiges puis éclosent en fleurs.

Exemple du dessin de la tresse ![4 -2 3 -2](CodeCogsEqn1.gif) avec l'appel `dessine_tresse([4, -2, 3, -2])`:

![Une tresse](imgs/4m23m2.png)

Accéder au notebook : [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/xysticus/braid-blackboard/master?filepath=ipynbks/CanvasTresseOmbre.ipynb)

Et maintenant la représentation d'Artin avec un exemple.

![Une tresse](imgs/auto_h2.png)

Accéder au notebook : [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/xysticus/braid-blackboard/master?filepath=ipynbks/CanvasAutoMorph.ipynb)

C'est [ipycanvas](https://github.com/martinRenou/ipycanvas) qui est utilisé pour dessiner sur le canvas [HTML5](https://fr.wikipedia.org/wiki/Canvas_(HTML)).

## Le film des méandres

Au lieu d'une image figée pour une tresse donnée, `programmes/Triangulation.py` fabrique un film : à chaque lettre
σ_i, les trous i et i+1 tournent d'un demi-tour l'un autour de l'autre et entraînent continûment les lacets, qui
dessinent au fil du film l'automorphisme du groupe libre associé à la tresse.

```
python programmes/Triangulation.py   # depuis la racine du dépôt : écrit imgs/film_triangule_*.mp4
```

Le principe :

- le disque est découpé en triangles dont les sommets sont les trous, le clou et des points des bords ;
- un lacet est une suite de points posés sur les arêtes ; quand les trous bougent, les triangles se déforment et les
  points suivent leurs arêtes ; quand un triangle devient trop plat, on change de triangulation (retournement
  d'arête, critère de Delaunay) sans changer la forme des lacets ;
- les lacets sont tendus comme des élastiques : ils s'enroulent en arcs de cercle autour des trous et vont en ligne
  droite d'un enroulement à l'autre ;
- les mots du groupe libre relus sur chaque image sont vérifiés contre le calcul algébrique.

### Parenté avec le morphing

Ce film rappelle le **morphing** (ou morphose), ces images qui se transforment progressivement en d'autres, rendues
célèbres au début des années 1990 (le clip *Black or White* de Michael Jackson, des génériques de télévision).
Le morphing combine deux opérations :

1. une **déformation géométrique** (*warping*) : des points de correspondance sont placés sur les deux images et l'on
   déforme continûment la première pour amener ses points sur ceux de la seconde ;
2. un **fondu enchaîné** : pendant la déformation, les couleurs des deux images se mélangent progressivement.

Une méthode classique de déformation consiste justement à trianguler les points de correspondance (souvent par
Delaunay) et à déformer chaque triangle par une application affine pendant que ses sommets se déplacent : c'est
exactement ce que fait notre triangulation mobile, dont les sommets sont les trous.

La différence est que le film ne fait que la première opération, sans fondu : les lacets sont transportés par une
déformation continue du plan (une isotopie), et c'est ce qui garde leur topologie exacte. Les premiers essais, qui
mélangeaient linéairement deux dessins (une sorte de fondu), créaient des croisements entre lacets.

## Le film conforme

Une autre manière de faire le film, qui garde l'allure des images fixes : des arcs posés perpendiculairement sur
l'axe, sans courbe libre.

```
python programmes/Conforme.py   # depuis la racine du dépôt : écrit imgs/film_conforme_*.mp4 (800 × 800)
```

<p align="center"><img src="imgs/simultane_conforme.jpg" alt="Le même instant de la même tresse : à gauche des
lacets ondulés, à droite des lacets tendus" width="660"></p>

<p align="center"><em>Le même instant de la tresse σ₄σ₃σ₁⁻¹σ₁⁻¹σ₂σ₄⁻¹σ₁, au milieu du demi-tour de σ₂ : à gauche
le film simultané, où deux dessins sont mélangés pendant tout le demi-tour, à droite le film conforme.</em></p>

Le principe :

- pendant que les trous A et B tournent, l'axe se plie en ligne brisée : il va de chaque trou voisin à l'un des deux
  trous qui tournent, et passe par le segment qui les relie. Les lacets traversent ces segments, et leurs points
  de traversée servent de pieds aux arcs ;
- au début du demi-tour, l'axe plié passe par A puis B, et porte exactement les points de l'image de départ ; à la
  fin, il passe par B puis A, et porte ceux de l'image d'arrivée. Quand les deux trous sont à la verticale l'un de
  l'autre, on passe d'un dessin à l'autre, morceau par morceau entre les traversées de ces segments ;
- pour tracer les arcs sur l'axe plié, on utilise une **représentation conforme**, une transformation du plan qui
  conserve les angles (formule de Schwarz–Christoffel) : elle envoie le demi-plan sur la région au-dessus (ou
  au-dessous) de la ligne brisée. On trace des demi-cercles dans le demi-plan, comme dans les images fixes, et la
  transformation les emporte sur la ligne brisée. Les arcs arrivent donc perpendiculairement aux segments, et deux
  arcs ne peuvent pas se croiser ;
- les demi-cercles sont les « droites » du demi-plan de Poincaré : leurs images sont les chemins les plus tendus
  possible, et les lacets ne sont plus flasques. Les descentes vers le clou sont, elles aussi, de ces géodésiques ;
- le passage d'un dessin à l'autre, à mi-chemin, se fait sur une triangulation mobile, comme dans le film des
  méandres : les deux dessins y sont transportés par la déformation du plan, puis, autour des deux trous qui
  tournent, tendus en droites arrondies dont les pieds glissent sur les arêtes sans changer d'ordre ;
- comme pour la triangulation, les mots du groupe libre et l'absence de croisements sont vérifiés sur chaque image.

Mon livre de chevet sur les tresses : "[Le calcul des tresses](https://www.decitre.fr/livres/le-calcul-des-tresses-9782916352794.html)", [Patrick Dehornoy](https://www.decitre.fr/auteur/198862/Patrick+Dehornoy), Calvage & Mounet, Collection.-Nano
