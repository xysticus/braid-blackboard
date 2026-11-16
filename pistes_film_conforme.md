# Film conforme : ce qui est garanti, et les pistes pour le reste

`programmes/Conforme.py`, `film_conforme`. Voir aussi le point 13 de `CLAUDE.md`.

## Où en est-on

Pendant σ_i, les trous A (i) et B (i+1) font un demi-tour. L'axe se plie en ligne brisée :

- **L–A–B–R** (L, R : trous voisins, ou points virtuels au bord) porte exactement les points de l'image clé k ;
  elle reste simple de 0 jusqu'à juste avant la fin du demi-tour (à la fin, L–A passe par B) ;
- **L–B–A–R** porte de même ceux de l'image clé k+1, de juste après le début jusqu'à la fin.

Chaque état est dessiné sur sa ligne brisée par une représentation conforme de Schwarz–Christoffel (`Carte`) :
des demi-cercles dans le demi-plan, emportés sur la région au-dessus (ou au-dessous) de la ligne brisée. Autour de
la verticale (fenêtre de 0,3 du mouvement), on passe du premier dessin au second par un mélange, morceau par
morceau entre les traversées des cinq segments L–A, A–B, B–R, L–B, A–R (`raccorde`).

## Ce qui est garanti

Hors de la fenêtre de raccord, l'absence de croisement découle de trois faits :

1. deux demi-cercles sur une droite se croisent si et seulement si leurs extrémités s'entrelacent, et les pieds
   sont posés dans l'ordre de l'état ;
2. la représentation conforme est une bijection de la région : des courbes disjointes le restent ;
3. les descentes au clou sont des géodésiques du demi-plan (arcs de cercle orthogonaux à l'axe passant par
   l'antécédent du clou) : deux d'entre elles ne se recoupent qu'au clou, et aucune ne croise un arc du bas tant
   que le clou est hors des demi-cercles (contrôlé par un `assert`).

Vérifié : zéro croisement hors de la fenêtre, sur la tresse de référence et sur la tresse chargée
`[1,-2,1,-2,1,-2,3,-1,2]`.

Réserve numérique : près d'un coin convexe, les géodésiques se resserrent fortement ; sur une tresse plus chargée,
deux brins pourraient s'approcher plus près que l'erreur d'intégration de la carte.

## Ce qui n'est pas garanti

Le passage d'un dessin à l'autre est un **mélange linéaire** de deux dessins, pas une déformation du plan (une
isotopie) : aucun théorème ne dit que la moyenne de deux dessins sans croisement est sans croisement. Sur la tresse
chargée, 7 images au milieu des lettres 6 et 7 ont quelques croisements (encoches près des trous qui tournent,
brins extérieurs tassés). Les deux dessins sont des géodésiques de deux régions différentes (au-dessus de L–A–B–R,
au-dessus de L–B–A–R), donc des courbes différentes, même s'ils représentent les mêmes lacets.

Le passage lui-même est inévitable : un cadre fixe (l'axe entier plus le segment qui tourne) donne, pour chaque
lettre, des descriptions différentes depuis l'image clé k et depuis l'image clé k+1 (vérifié). Ce qui n'est pas
inévitable, c'est de le faire par un mélange.

## Piste 1 : les géodésiques de la sphère trouée

**Idée.** Le plan privé des n trous et du clou (plus le point à l'infini) est une sphère à n+2 pointes ; elle porte
une métrique hyperbolique complète, unique. Chaque lacet (arc du clou au clou autour des trous) y a un représentant
géodésique unique. Quand les trous bougent, la métrique change continûment et les géodésiques aussi ; des lacets
disjoints ont des géodésiques disjointes.

**Ce qu'on y gagne.** Plus de cadre, plus de ligne brisée, plus de basculement ni de mélange : le dessin à chaque
instant est canonique, et l'absence de croisement est un théorème. Les images clés changent d'allure (ce ne sont
plus des demi-cercles sur l'axe), mais restent tendues.

**Ce qu'il faut calculer.** L'uniformisation : un revêtement du demi-plan de Poincaré sur la sphère trouée, ou
directement la métrique conforme ρ(z)|dz| de courbure -1 (équation de Liouville Δ log ρ = ρ², avec des pointes aux
trous, au clou et à l'infini). Pistes numériques :

- résoudre l'équation de Liouville sur une grille ou un maillage (la triangulation mobile de `Triangulation.py`
  peut servir), avec le comportement imposé près des pointes (ρ ~ 1 / (|z - p| log|z - p|)) ;
- puis tendre chaque lacet dans cette métrique : la tension discrète de `Film.tend` (triangulation) devient une
  descente de la longueur hyperbolique.

**Difficultés.** C'est le morceau le plus lourd : précision près des pointes, coût à chaque image. Les géodésiques
plongent vers les pointes d'une façon que le dessin devra adoucir. À essayer d'abord sur une image fixe.

## Piste 2 : remplacer le mélange par une petite isotopie

**Idée.** Pendant la fenêtre, transporter le dessin de départ par une déformation du plan qui l'amène sur le dessin
d'arrivée, comme les bascules d'arête de la triangulation (« la forme ne change pas » au moment de la bascule,
puis la tension déplace les points).

**Une façon de faire.** À la verticale, les cinq segments forment un quadrilatère L-A-R-B et sa diagonale A–B, tous
leurs sommets aux trous. La suite des traversées de chaque lacet y est unique (après annulation des bigones,
`sans_bigones`), et les deux dessins l'ont en commun.

1. Au début de la fenêtre, on garde le dessin de départ et l'on note ses points de traversée des cinq segments.
2. On fait glisser ces points le long des segments jusqu'aux points de traversée du dessin d'arrivée. Sur chaque
   segment, l'ordre est le même aux deux bouts, donc un glissement linéaire le garde.
3. Entre deux points consécutifs, le morceau reste dans une seule région (un des deux triangles, ou la région du
   haut ou du bas). On le redessine à chaque instant dans cette région à partir de ses deux pieds, par exemple par
   la représentation conforme de la région elle-même : un triangle, ou une région bordée par la ligne brisée.
   Pas de croisement dans une région, par la même règle des demi-cercles.

Il reste à régler :

- les bigones (allers-retours par-dessus une arête) : à résorber avant le glissement, de l'intérieur vers
  l'extérieur, comme les vagues de bigones du film algébrique ;
- les raccords entre le dessin avant la fenêtre (sur L–A–B–R) et le dessin redessiné par régions : ils ne
  coïncident pas exactement, il faut donc entrer dans la fenêtre par un dessin qui est déjà celui « par régions ».
  Le plus simple serait de dessiner par régions du quadrilatère pendant tout le demi-tour, sauf près des bouts où
  les triangles s'aplatissent.

**Difficultés.** Beaucoup de cas particuliers à traiter à la main (bigones, entrée et sortie de la fenêtre), mais
avec des outils qu'on a déjà (`Carte`, `traversees`, `sans_bigones`), et sans nouveau calcul lourd. C'est la piste
la plus courte pour supprimer les défauts actuels ; la piste 1 est la plus propre.
