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

## Idées à creuser (2026-11-16)

### Changer d'axe, au moins localement : l'axe des deux trous qui tournent

Dans le repère qui tourne avec A et B, le bloc (les trous A, B et les arcs dont les deux pieds sont sur A–B) ne
bouge pas. L'axe naturel près du bloc est donc la droite qui porte A–B, et loin du bloc c'est l'axe horizontal.
Avec cet axe local, les arcs du bloc seraient de vrais demi-cercles sur A–B, qui tournent d'un bloc. Aujourd'hui,
la carte conforme les déforme un peu, parce qu'elle part de la ligne brisée entière.

Ça a un sens, mais seulement par morceaux. Une représentation conforme égale à une rotation sur un ouvert est
cette rotation partout (prolongement analytique) : on ne peut pas avoir une seule carte qui tourne près du bloc et
ne bouge pas au loin. Il faut donc découper le plan en régions (un disque autour du bloc où l'on tourne, le reste
où l'on garde l'axe horizontal) et raccorder sur le bord. C'est la couronne du film simultané, mais avec des
pieds posés sur le bord au lieu d'une torsion libre. Ça rejoint la piste 2 (redessiner par régions), avec un
découpage différent : le disque du bloc au lieu des triangles du quadrilatère.

### Garder en vrais demi-cercles les brins que le mouvement ne concerne pas

Les arcs dont les deux pieds sont loin du bloc, et qui ne l'entourent pas, n'ont aucune raison de bouger. La carte
conforme est globale : loin de la ligne brisée elle tend vers une translation, mais elle les déforme quand même un
peu et change leur espacement. Les tracer en demi-cercles exacts, fixes, garderait les images clés intactes là où
il ne se passe rien, et laisserait plus de place au reste.

Ça a un sens, avec une précaution. Les arcs qui entourent le bloc (au-dessus de A et B à la fois) sont concernés :
ils doivent s'écarter quand un trou monte. Ceux qui restent sont à l'abri : un arc dont les pieds sont tous deux à
gauche de L (ou à droite de R) et qui n'entoure pas L (ou R). Mais un demi-cercle exact et un arc conforme voisin
ne sont plus garantis disjoints, puisqu'ils ne viennent pas de la même carte. Il faudrait soit vérifier que la
carte est assez proche de la translation à cet endroit, soit (plus propre) découper là aussi le plan : une région
« immobile » où l'on dessine des demi-cercles, et la carte conforme seulement dans la région qui contient le bloc,
avec son bord comme nouvel axe.

Les deux idées vont dans le même sens : remplacer une carte unique pour tout le plan par un découpage en régions,
chacune avec son axe (horizontal immobile, horizontal plié, ou celui de A–B qui tourne), et des pieds posés sur
les bords des régions. Les arcs restent sans croisement dans chaque région par la règle des demi-cercles. Il reste
à faire bouger les bords des régions, et les pieds dessus, sans jamais changer l'ordre des pieds.

### Conclusion : un disque et sa couronne ne gagnent rien

Objection de l'utilisateur, juste : ces régions sont un disque qui tourne dans une couronne, et à la jointure les
pieds des brins sont bien obligés de bouger dans la couronne. On ne gagnerait que si, pour chaque lettre, on
trouvait un disque et une couronne qui n'interfèrent pas. C'est impossible, pour deux raisons :

- **le bord du disque est toujours traversé.** Un cercle qui entoure seulement A et B laisse le clou dehors ; tout
  lacet qui tourne autour de A ou de B part du clou et y revient, donc le traverse au moins deux fois ;
- **le demi-tour agit justement sur ces brins.** Tourner A et B d'un demi-tour dans le disque, c'est un demi-twist
  de Dehn le long de ce cercle : il laisse en place ce qui est dedans et ce qui est dehors, et enroule tout ce qui
  le traverse. Cet enroulement est l'action de σ_i ; on ne choisit que l'endroit où on le met.

Le film simultané le concentre dans une couronne étroite (brins tordus, puis mélange : ondulations). Le film
conforme le répartit sur toute la région, et c'est pour ça que ses lacets paraissent tendus. Un découpage disque +
couronne, même avec de vrais demi-cercles dedans et dehors, remettrait toute la torsion dans la couronne ; le mieux
y serait des spirales régulières (les droites de l'anneau vu comme un rectangle dont on recolle deux côtés), plus
propres que la torsion actuelle, mais toujours une couronne.

Ce qui reste de la seconde idée : vérifier si les brins lointains sont assez proches de demi-cercles pour être
remplacés par des demi-cercles exacts, sans en attendre de place en plus.

### Passer provisoirement à la triangulation pendant le raccord (idée de l'utilisateur)

Plutôt que de mélanger les deux dessins pendant la fenêtre de raccord, passer le temps de la fenêtre à la
triangulation mobile, dont on sait qu'elle fonctionne. C'est la piste 2 avec des triangles et des cordes à la
place des cartes conformes.

- Pendant la fenêtre, un maillage dont les sommets sont les trous, le clou et des points du bord (comme dans
  `Triangulation.py`).
- Au début de la fenêtre, on coupe le dessin conforme de départ par les arêtes du maillage : chaque lacet devient
  une suite de pieds sur les arêtes. Même chose à la fin pour le dessin d'arrivée.
- Les sommets étant des trous, la suite des arêtes traversées par un lacet, après annulation des bigones
  (`sans_bigones`), est la même dans les deux dessins : les pieds se correspondent un à un.
- Chaque pied glisse sur son arête de sa place de départ à sa place d'arrivée ; l'ordre des pieds d'une arête est
  le même aux deux bouts, donc il est gardé.
- Dans chaque triangle, les pieds sont reliés par des cordes droites : un triangle est convexe, et deux cordes dont
  les extrémités ne s'entrelacent pas ne se croisent pas. Aucun croisement par construction : c'est une vraie
  isotopie, plus un mélange.

Ce que ça coûte :

- l'allure change pendant la fenêtre (lignes brisées avec congés, comme le film triangulé, au lieu des arcs
  conformes) ; à l'entrée et à la sortie, la ligne brisée approche le dessin conforme si le maillage est assez fin,
  il resterait un petit saut à juger en mouvement ;
- les trous bougent pendant la fenêtre : retournements d'arête quand un triangle s'aplatit (`Maillage` sait le
  faire, il faut le brancher sur ces pieds) ;
- `Film` (de `Triangulation.py`) part d'une tresse et gère lui-même ses états et sa tension ; il faudrait en
  extraire le maillage et le dessin, et piloter les pieds de l'extérieur (glissement imposé, sans tension).
  C'est le gros du travail.

Ce qu'on y gagne : les images fautives de la tresse chargée disparaissent, avec une garantie, au prix d'un passage
d'environ 0,3 s par lettre à l'allure du film triangulé.
