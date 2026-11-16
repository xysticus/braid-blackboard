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

### Essai fait (2026-11-16) : la triangulation pendant le raccord, en cordes près des trous seulement

`programmes/Raccord.py`, `film_conforme(..., raccord='triangulation')`.

- Maillage : un bord convexe hors de l'image, les trous, le clou (`maillage_du_raccord`), de Delaunay, les arêtes
  retournées entre deux pas. Transport du dessin par l'application affine par triangles (`transporte`) : une vraie
  isotopie. Le dessin de départ est transporté vers l'avant sur la fenêtre, le dessin d'arrivée vers l'arrière ; au
  bord de la fenêtre on retrouve exactement les dessins conformes, sans saut.
- À chaque image, les deux dessins sont coupés par les arêtes (`coupe`), bigones annulés : mêmes suites d'arêtes,
  pieds en correspondance. Deux pièges : le clou est le point base, pas un trou (un lacet peut tourner autour en
  partant), donc les traversées des arêtes du clou en tête et en queue ne comptent pas ; les pieds des arcs conformes
  sont des points doublés posés exactement sur l'axe, d'où de faux bigones si l'on ne reconnaît pas le doublon à sa
  place sur l'arête.
- Passage : les pieds glissent sur leurs arêtes (ordre gardé). Un triangle qui touche un des deux trous qui tournent,
  ou qui contient un bigone, passe en cordes (tension, glissement en cordes, courbure) ; les autres triangles mélangent
  directement leurs morceaux de départ et d'arrivée, qui y restent (triangle convexe). Le choix se fait par triangle :
  un essai par morceau faisait croiser une corde et une courbe du même triangle (30 croisements). Phases resserrées au
  milieu de la fenêtre (0,3 → 0,42 tension, 0,42 → 0,58 glissement, 0,58 → 0,7 courbure).
- Résultat : 0 croisement et mots justes sur toutes les images des deux tresses d'essai (le mélange : 7 images fautives
  sur la tresse chargée). Garanti pendant le glissement ; la tension et la courbure, et le mélange des triangles
  lointains, sont des mélanges vérifiés numériquement. Coût visuel : autour des deux trous, des polygones pendant une
  image ou deux au cœur de la fenêtre (le maillage n'a que les trous pour sommets : les cordes sont longues). Un
  premier essai, tout en cordes sur toute la fenêtre, était bien plus anguleux.
- Congés (demande de l'utilisateur) : les morceaux en cordes consécutifs d'un lacet forment une suite tracée comme
  une ligne brisée dont les coudes sur les pieds sont arrondis (`arrondit`, comme `Film.polyligne`) ; les deux bouts
  de la suite, où elle rejoint un morceau courbe, ne bougent pas. Les images du cœur de la fenêtre n'ont plus de
  polygones, seulement de légers coins aux bouts des suites. Toujours 0 croisement sur les deux tresses (les congés
  ne sont pas garantis, vérifiés numériquement).
- Coins aux bouts des suites de cordes : le début de la première corde (la fin de la dernière) est remplacé par une
  paire d'arcs (`deux_arcs`) tangente à l'arc qui arrive au pied et à la corde, sur au plus la moitié de la corde
  (`arrondit(..., depart, arrivee)`) : plus de rupture de tangente entre arcs conformes et cordes. Toujours 0
  croisement sur les deux tresses.

### Essai fait (2026-11-16) : les brins lointains en vrais demi-cercles

Mesure, à quatre instants de chaque lettre, de l'écart entre les arcs conformes dont les deux pieds sont sur la même
demi-droite extérieure (à gauche de L ou à droite de R) et les demi-cercles exacts de mêmes pieds : médiane 0,2 px
(tresse de référence, 116 arcs) et 0,25 px (tresse chargée, 180 arcs) ; au plus 2,3 px et 5,3 px, pour de grands arcs
qui passent près du bloc, là où les brins ne sont espacés que de quelques pixels. Conclusion : pas la peine. Loin du
bloc, la carte conforme donne déjà des demi-cercles à l'œil, et forcer les demi-cercles exacts là où elle s'en écarte
risquerait des croisements.

### Adoucir le raccord (2026-11-16)

La sensation râpeuse venait de phases trop courtes : la fenêtre (30 % du mouvement) ne durait qu'une dizaine
d'images, et la mise en cordes resserrée au milieu en prenait à peine plus d'une. Fenêtre portée à 50 %, phases
étalées sur toute la fenêtre (tension 0 → 0,35, glissement 0,35 → 0,65, courbure 0,65 → 1) : chaque changement de
forme dure 4 ou 5 images. Trois corrections pour garder 0 anomalie :

- traversées : un pied posé sur une arête était, selon l'arrondi du transport (plus long), compté dans un dessin et
  manqué dans l'autre ; chaque point est maintenant classé d'un côté de l'arête (un point sur l'arête compte toujours
  du même côté), une traversée est un changement de côté ;
- arrondis : un congé (ou une paire d'arcs de jonction) reste dans un disque centré sur son coude de rayon 0,9 × la
  distance au trou le plus proche ; règle continue, donc arrondis voisins emboîtés (un resserrement au cas par cas
  faisait se croiser deux brins voisins) ;
- mélange triangle par triangle : mélanger d'un seul tenant une suite de cordes arrondies avec les arcs d'arrivée
  faisait passer le lacet par-dessus un trou autour duquel il s'enroule (mots faux), même si les deux courbes étaient
  du bon côté ; les cordes arrondies sont coupées là où elles traversent les arêtes des pieds (`decoupe_aux_aretes`),
  et chaque morceau est mélangé avec celui du même triangle, convexe, dont les trous sont les sommets.

0 anomalie (mots, croisements) sur les deux tresses d'essai.

## Piste 1 bis : une triangulation de Delaunay partout, vue comme une surface hyperbolique (idée de l'utilisateur)

**Idée.** Garder la triangulation mobile tout le temps et partout (comme `Triangulation.py`, dont la topologie est
garantie par l'isotopie), mais dessiner les lacets en arcs, en se servant des cercles circonscrits des triangles de
Delaunay (vides de tout autre sommet).

**Le lien.** Les sommets étant des trous, on peut les voir comme des pointes à l'infini d'une surface hyperbolique.
Dans son cercle circonscrit, un triangle de Delaunay est un triangle idéal (sommets à l'infini) du plan hyperbolique :
en modèle de Klein, ses côtés droits sont des géodésiques, et les géodésiques d'un lacet sont des cordes (nos cordes de
raccord) ; en modèle de Poincaré, les géodésiques sont des arcs orthogonaux au cercle, mais les côtés du triangle idéal
sont alors eux aussi des arcs, pas les arêtes droites. Théorie connue (de mémoire, à vérifier) : coordonnées de Penner,
triangulations idéales, Rivin ; « applications conformes discrètes » et polyèdres hyperboliques idéaux (Bobenko,
Pinkall, Springborn), où les retournements de Delaunay assurent l'existence de l'uniformisation discrète.

**Ce qu'on y gagnerait.** La version discrète de la piste 1, sans équation aux dérivées partielles : à chaque instant
un dessin unique et tendu de chaque lacet (sa géodésique), plus de ligne brisée ni de raccord, et l'absence de
croisement serait un théorème (des lacets disjoints ont des géodésiques disjointes).

**Difficultés.**

- Recollement d'un triangle à l'autre : les deux triangles d'une arête ont deux cercles circonscrits différents ; pour
  qu'un lacet se continue à travers l'arête, il faut le recollement des triangles idéaux, donné par les coordonnées de
  cisaillement (logarithme d'un birapport des quatre sommets du quadrilatère). Il faut donc calculer la géodésique sur
  la surface recollée, puis la redessiner dans les triangles, pas dessiner chaque triangle à part.
- Arcs et triangles : un arc de Poincaré entre deux points de deux côtés peut bomber au-delà du triangle près d'un
  sommet ; la garantie « deux cordes dont les pieds ne s'entrelacent pas ne se croisent pas » ne se transpose pas
  telle quelle à un dessin par triangles.
- Le clou est un point base, pas une pointe : les lacets y aboutissent (arcs géodésiques d'une pointe à elle-même
  autour des trous, ou clou traité comme une pointe supplémentaire).

**Premier pas possible.** Sur une image fixe : calculer les coordonnées de cisaillement de la triangulation de
Delaunay des trous et du clou, tendre un lacet (donné par sa suite d'arêtes) en géodésique de la surface idéale, et le
dessiner ; comparer à l'image clé en demi-cercles.

## Piste 1 ter : sans clou, des arcs entre trous (idée de l'utilisateur, « quotienter » le clou)

**Idée.** Le lacet x_i (du clou autour du trou i) est le bord d'un voisinage mince de l'arc qui va du clou au trou i :
l'image de l'arc par la tresse donne celle du lacet. On remplace le clou par n trous fixes f_1 ... f_n, rangés là où
était le clou (ils peuvent glisser sur leur ligne pour la mise en page), et chaque lacet par l'arc de f_i au trou
voyageur m_i. La tresse ne fait bouger que les trous voyageurs ; tant que les trous fixes restent groupés près du bord,
l'action sur ces arcs équivaut à l'action d'Artin sur F_n. Ce sont les diagrammes de courbes (Fenn, Greene, Rolfsen,
Rourke, Wiest ; livre de Dehornoy, de mémoire).

**Ce qu'on y gagnerait.**

- Plus de point base : tous les objets vont d'un trou à un trou (plus de traversées d'arêtes du clou à retirer, de
  descentes, de départ perpendiculaire, de lacets qui se rejoignent tous en un point). Un arc peut tourner autour de
  ses extrémités sans changer de classe : ses traversées des arêtes de ses bouts, en tête et en queue, ne comptent pas.
- La piste 1 bis devient naturelle : un arc entre deux pointes a un représentant géodésique unique, et les arcs entre
  pointes sont exactement les arêtes des triangulations idéales.
- Deux fois moins de traits : un arc est un brin, un lacet deux.

**Ce que ça change.** On voit n arcs accrochés à leur trou fixe au lieu de boucles qui reviennent au clou ; si l'on
tient aux boucles, on dessine le bord d'un ruban autour de chaque arc (deux rubans d'arcs disjoints sont disjoints).
Le mot d'un arc se lit sur son ruban comme celui du lacet.

**Premier essai.** Dans la triangulation mobile (`Triangulation.py`, isotopie garantie) : trous fixes sur une ligne en
bas, arcs de départ verticaux, demi-tours des trous voyageurs, arcs dessinés seuls ou en rubans.

**Premier essai fait (2026-11-16)** : `programmes/Arcs.py`, `film_arcs` → `imgs/film_arcs_*.mp4` (arcs seuls) et
`imgs/film_rubans_*.mp4` (rubans). `FilmArcs` réutilise de `Film` le maillage, la tension et le dessin en congés (clou
neutralisé), avec un maillage de Delaunay des trous voyageurs et fixes (`maillage_du_raccord`, clou facultatif). Arcs
de départ verticaux ; demi-tours à place fixe (trous régulièrement espacés, pas encore de disposition proportionnelle).
Mots relus sur les rubans (`lit_mot`, demi-droites des trous voyageurs) justes après chaque lettre, sur la tresse de
référence et la tresse chargée ; calcul très rapide (0,5 s pour la tresse chargée sans dessin, 7 s pour les deux films).
Le ruban est parcouru côté droit à l'aller (sinon on lit les mots inverses) ; sa demi-largeur est le tiers de l'écart
entre brins. Espacement proportionnel ajouté ensuite : à chaque image clé, largeur de chaque intervalle de l'axe proportionnelle
à 1 + le nombre d'arcs qui le traversent (la moitié de celui des lacets, connu par `etat_de_tresse`) ; entre les
images clés, les largeurs suivent une interpolation d'Hermite monotone (Fritsch–Carlson, `pchip`) à travers toutes les
images clés : vitesse continue d'une lettre à l'autre (une interpolation linéaire par lettre ferait un à-coup à chaque
image clé), largeurs toujours positives (deux trous ne s'inversent jamais). Le demi-tour se fait autour du milieu des
deux places qui glissent, à vitesse angulaire constante. Le mouvement des arcs, très doux (« soft », dit
l'utilisateur), vient d'un seul mouvement continu, d'une seule manière de dessiner et de l'absence de clou. Reste :
la piste 1 bis avec ces arcs entre pointes.

### Essai fait (2026-11-16) : la piste 1 bis avec les arcs entre pointes

`programmes/Geodesiques.py`, `FilmArcs(..., hyperbolique=True)`, `film_arcs(..., hyperbolique=True)` →
`imgs/film_geodesiques_*.mp4`.

- Métrique : chaque triangle de Delaunay, dans son cercle circonscrit, est un triangle idéal du modèle de Klein
  (distance de Hilbert, demi-logarithme d'un birapport avec les points où la droite coupe le cercle). Le long d'une
  arête commune, les deux triangles induisent la même distance (Hilbert sur un segment ne dépend que de ses
  extrémités) : recollement tel quel, sans coordonnées de cisaillement à calculer ; tous les sommets sont des pointes.
- Géodésique d'un arc : même suite d'arêtes (celle de la triangulation mobile), pieds choisis pour minimiser la
  longueur hyperbolique (descente coordonnée par coordonnée, section dorée sur la fraction de chaque pied ; aux bouts,
  la pointe remplacée par un point à ε sur la bissectrice du coin). Dans le film, deux tours par sous-pas au lieu de
  `Film.tend`.
- Résultats : l'ordre des pieds sur les arêtes se conserve tout seul (0 changement : des arcs disjoints ont des
  géodésiques disjointes), mots relus justes après chaque lettre sur les deux tresses d'essai. Plus lent (film de la
  tresse de référence en 50 s au lieu de quelques secondes).
- Allure : chaque trou est une pointe qui repousse les brins ; ils gardent une distance naturelle aux trous et les
  contournent par de larges courbes, sans écart imposé (la tension euclidienne les plaque contre les trous). Dessin :
  cordes de Klein (droites dans chaque triangle), coudes arrondis comme d'habitude. Essai écarté : tracer dans chaque
  triangle l'arc orthogonal au cercle circonscrit (géodésique de Poincaré du même disque) : bosses et boucles près des
  trous, chaque triangle ayant son propre cercle.
- À voir : la métrique dépend de la triangulation (elle change à chaque retournement d'arête de Delaunay ; est-ce
  visible ?), et du bord convexe hors de l'image, dont les sommets sont aussi des pointes.

### Essai fait (2026-11-16) : le diagramme de courbes

`Arcs.DiagrammeCourbes`, `film_arcs(..., classe=DiagrammeCourbes, lisere=True)` → `imgs/film_diagramme_*.mp4` (et
`imgs/film_diagramme_geodesiques_*.mp4` avec `hyperbolique=True`). Poussée à fond, l'idée des trous fixes donne le
diagramme de courbes de la littérature : un seul point fixe, au bout gauche de l'axe, et pour arcs les segments de
l'axe (du point fixe au premier trou, puis d'un trou au suivant), que la tresse emporte. Plus rien n'est accroché en
bas ; au départ l'image est l'axe lui-même. Trous fixes sur l'axe : seulement groupés à un bout ; intercalés entre les
trous voyageurs, ils seraient dans le disque d'un demi-tour et l'on calculerait une autre tresse.

- Vérification : le premier arc est le lacet x_1 (son ruban, relu par `lit_mot`, donne l'image de x_1) ; juste après
  chaque lettre sur six tresses, dont la tresse chargée, avec les deux tensions. Les autres arcs vont d'un trou à
  l'autre (pas de mot de F_n direct).
- Arcs de départ : segments de l'axe légèrement bombés pour la découpe par les arêtes, que la tension redresse.
- Dessin « liseré » (idée de l'utilisateur) : chaque arc en blanc large (0,85 × l'écart) avec un liseré de couleur
  fin au milieu ; sur fond blanc, impression d'un écart entre brins voisins.
- Coût : tension euclidienne, 15 s pour le film de la tresse chargée ; géodésiques, 7 min 30.
- Géodésiques sur la tresse chargée : les brins parallèles se confondent en un seul trait loin des trous (des
  géodésiques voisines se rapprochent exponentiellement dans les parties minces de la surface) ; illisible. La
  tension euclidienne, avec son écart minimal, reste la bonne pour les tresses chargées ; les géodésiques ne valent
  que pour les tresses légères.

**À faire (idée de l'utilisateur)** : refaire le bouquet avec le diagramme de courbes (qui donne beaucoup de formes) ;
le bouquet actuel doit son existence au clou (les lacets qui en partent font les tiges).

**Trous fixes rapprochés** (`FilmArcs(..., ecart_fixes=30)`, film `imgs/film_rubans_charge.mp4`) : groupés au milieu du
bas, on se rapproche du clou. Trop serrés (14 px), les arêtes qui descendent d'un trou voyageur vers les trous fixes
forment des triangles très minces où la tension se dérègle : les brins qui contournent le trou y sont tirés en pointe
(une « goutte »). À 30 px, plus de goutte.

**Trous fixes groupés au bout gauche de l'axe** (`FilmArcs(..., fixes='gauche')`, films `imgs/film_rubans_gauche_*.mp4`) :
f_n le plus à gauche, f_1 le plus près du premier trou ; l'arc de f_k à m_k passe sous m_1 ... m_(k-1), comme le lacet
x_k depuis le clou (arcs de départ en demi-ellipses emboîtées sous l'axe, intervalles [f_k, m_k] emboîtés). Mots
relus justes après chaque lettre sur six tresses, dont la tresse chargée. Rien d'accroché en bas.

**À examiner (remarque de l'utilisateur)** : `imgs/rubans/film_charge.mp4`, à la fin, hémisphère sud au niveau du
troisième trou : un petit effet de bossage disgracieux sur les brins.
