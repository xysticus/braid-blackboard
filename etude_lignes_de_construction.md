# Étude : des lignes de construction en option dans les lecteurs de film

Idée : comme le lecteur des films (`lecteur` dans `python/Interface.py`) est le nôtre, on peut offrir pour chaque film une
case « lignes de construction ». Elle montre, sous le sujet, ce qui sert à le fabriquer (l'axe et la ligne brisée,
la triangulation…). Ce serait un deuxième jeu d'images, calculé en même temps que le film, et le lecteur passerait de l'un
à l'autre. Cette page dit ce qui existe, ce que cela coûte (mesuré) et ce qu'on propose. Rien n'est implémenté.

## Ce qui existe déjà, film par film

| Film | Lignes de construction | Où | Pour en faire un deuxième jeu |
|---|---|---|---|
| Lacets | l'axe et la ligne brisée L–A–B–R, en gris | `surface_conforme(..., construction=True)` : les données sont déjà dans chaque dessin | rien à recalculer : on rend chaque dessin deux fois |
| Triangulation | les arêtes de la triangulation, en gris | `Film.cadre(avec_arêtes=True)` | `Film.lettre` ne passe à `rendu` que la surface : il faut une petite retouche pour obtenir les deux (l'écart `ecart`, nécessaire à `cadre`, reste interne à `lettre`) |
| Rubans | les arêtes de la triangulation | `FilmArcs.cadre(avec_aretes=True)` | `rendu` reçoit le film : on appelle `cadre` deux fois, sans retouche |
| Courbes | les arêtes de la triangulation | idem (`DiagrammeCourbes` hérite de `FilmArcs`) | idem |
| Escargot, bouquet | rien : leur `dessine` est écrit pour eux | — | à écrire ; et une triangulation de 35 trous n'éclaire pas grand-chose : à ne pas faire d'abord |

Dans tous les cas, les lignes de construction sont déjà tracées **avant** le sujet (`peint` trace l'axe d'abord,
`FilmArcs.cadre` les arêtes d'abord) : elles passent dessous, comme voulu.

## Ce que coûte un deuxième jeu d'images

Mesures sur `[1, -2, 1, -2, 3]`, images de 800 × 800, PNG :

| Film | Images | Temps du film seul | Temps en plus pour le jeu avec construction | Poids du jeu seul | Poids du jeu avec construction |
|---|---|---|---|---|---|
| Rubans | 301 | 5,3 s | +5,4 s (le rendu PNG double) | 17 Mo | 29 Mo |
| Courbes | 300 | — | — (10,0 s pour les deux jeux) | 8 Mo | 20 Mo |
| Lacets | 241 | 6,3 s de calcul + 4,8 s de rendu | +4,9 s (le calcul n'est pas refait) | 22 Mo | 24 Mo |
| Triangulation | 525 | — | environ +21 s (41 ms par image avec arêtes) | 159 Ko par image au plus | 231 Ko par image au plus |

Le calcul du film ne change pas : c'est le rendu et l'encodage PNG qui doublent (une image de rubans prend 20 ms à
rendre et à encoder). Pour un mot long (limite de l'ardoise : 40 lettres pour les rubans et les courbes), compter en
proportion : de l'ordre de 40 s de rendu en plus et plus de 200 Mo de PNG en mémoire pour les rubans.

## Deux façons de faire

**A. Deux jeux complets** : le jeu du sujet seul, et un jeu « sujet + construction », chaque image déjà composée. Le
lecteur ne fait que choisir dans quelle liste il prend l'image.

**B. Deux couches** : un jeu du sujet sur fond transparent, un jeu de la construction seule, superposés par le lecteur
(deux `Image` dans une même case d'une grille). Cela ressemble davantage à l'idée « la construction avant le sujet ». Mais :
- une couche de construction seule n'est pas légère : pour les rubans 86 Ko par image (contre 128 Ko pour sujet +
  construction composés), pour la triangulation 59 Ko ; deux couches pèsent autant que deux jeux, voire plus ;
- il faut un fond transparent dans `peint`, `FilmArcs.cadre`, `Film.cadre` et `surface_conforme` ;
- le noyau envoie deux images à chaque pas de lecture, et la superposition est à essayer côté navigateur.

**Recommandation : A.** Plus simple, aucun changement de dessin, pas de risque de superposition ; la mémoire est du
même ordre que B. B n'aurait d'intérêt que pour modifier le style de la construction sans refaire le sujet.

## Ce que ferait A

- `lecteur(images, construction=None)` : si `construction` est donné (même longueur), une case « Lignes de construction »
  sous le curseur ; cocher change la liste d'où vient l'image affichée, à la même position. Pas de case pour l'escargot et
  le bouquet.
- Dans chaque film (`film_rubans`, `film_diagramme_de_courbes`, `film_lacets`, `film_triangulation`), la boucle qui fabrique
  les images en fabrique deux listes ; un paramètre `avec_construction=True` permet de la sauter (rendu et mémoire
  divisés par deux).
- La retouche de `Film.lettre` pour la triangulation : appeler `rendu` avec les deux surfaces (sans et avec arêtes), ou lui
  donner l'écart.
- Le calcul se fait en même temps que le film : la case est disponible dès que le lecteur apparaît. Elle n'ajoute rien à
  l'attente au-delà du rendu en plus (la barre de progression reste celle du film).

## Questions ouvertes

- **Doit-on toujours calculer le deuxième jeu ?** C'est ce qui est demandé (« en même temps que le film »), et la case est
  alors immédiate. Mais tout le monde ne la coche pas : le rendu double pour rien. Variante : une case « avec lignes de
  construction » dans l'ardoise, à cocher *avant* d'ouvrir l'onglet ; la cocher après obligerait à recalculer le film.
- **Que montrer pour les rubans et les courbes ?** Les arêtes de la triangulation sont ce que tend le dessin, mais elles
  disent peu à qui ne connaît pas la méthode. Les trous fixes et les segments qui portent les arcs seraient plus parlants ;
  à décider en regardant des images.
- **Les mots longs** : même limite de l'ardoise que pour les films seuls ? La mémoire du navigateur et du noyau double.
- **Lisibilité** : en gris clair et trait fin, comme `construction=True` des lacets ; vérifier que les arêtes ne noient pas
  le sujet quand la tresse est chargée.
