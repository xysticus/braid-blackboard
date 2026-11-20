# Étude : des lignes de construction en option dans les lecteurs de film

Idée : comme le lecteur des films (`lecteur` dans `python/Interface.py`) est le nôtre, on peut offrir pour chaque film une
case « lignes de construction ». Elle montre, sous le sujet, ce qui sert à le fabriquer (l'axe et la ligne brisée,
la triangulation…). Ce serait un deuxième jeu d'images, calculé en même temps que le film, et le lecteur passerait de l'un
à l'autre. Cette page dit ce qui existe, ce que cela coûte (mesuré) et ce qu'on propose. **Fait (2026-11-20) : la case des films de la triangulation, des lacets
et du diagramme de courbes de la page web** (voir « Ce qui est fait » à la fin) ; le reste n'est pas implémenté.
La dernière section, « Sur la page web », transpose l'étude à la page, où le principe est différent (et bien moins cher).

## Ce qui existe déjà, film par film

| Film | Lignes de construction | Où | Pour en faire un deuxième jeu |
|---|---|---|---|
| Lacets | l'axe et la ligne brisée L–A–B–R, en gris | `surface_conforme(..., construction=True)` : les données sont déjà dans chaque dessin | rien à recalculer : on rend chaque dessin deux fois |
| Triangulation | les arêtes de la triangulation, en gris (**le maillage en deux bandes du Python**, voir plus bas : ce n'est pas celui de la page) | `Film.cadre(avec_arêtes=True)` | `Film.lettre` ne passe à `rendu` que la surface : il faut une petite retouche pour obtenir les deux (l'écart `ecart`, nécessaire à `cadre`, reste interne à `lettre`) |
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

## Sur la page web

**Le principe est autre.** La page ne fabrique pas d'images : une « image » est faite de nombres (les polylignes des lacets, la
position des trous), calculés par un Web Worker et redessinés sur un canvas par `dessineImage` (`web/ardoise.js`). Le lecteur
(`Lecteur`) garde toutes les images en mémoire et possède déjà sa barre de progression. Il n'y a donc **pas de deuxième jeu
d'images** : chaque image gagne un champ `construction` (des segments), que `dessineImage` trace *avant* les lacets si une case est
cochée. Cocher ou décocher redessine l'image courante : instantané, sans worker.

### Ce qui existe déjà, film par film

| Film de la page | Lignes de construction | Où dans le code | Pour en faire un champ de l'image |
|---|---|---|---|
| Diagramme de courbes, rubans | les arêtes du maillage grossier | `image_arcs` (`ocaml/web/ardoise_web.ml`) a déjà `film.maillage` | un champ de plus : les arêtes (`Triangulation.Maillage.aretes`) |
| Triangulation | les arêtes du maillage grossier | `image_triangulation` a déjà `film.maillage` | idem (la page ne les trace pas aujourd'hui : « sans le maillage gris ») |
| Lacets | l'axe et la ligne brisée L–A–B–R | **Python seulement** (`Lettre.aretes`, et les opacités de `dessin_axe` pendant le raccord) ; `Film_conforme.image` n'a que `lignes`, `trous`, `clou` | **le seul vrai travail** : porter `aretes` en OCaml (une douzaine de lignes) et les opacités du raccord, avec un test contre la référence Python |
| Escargot, bouquet | rien | — | à ne pas faire |

### Le maillage de la page n'est pas celui du notebook

Le film de la triangulation de la page utilise le **maillage grossier** (`Film.cree ~grossier:true`, OCaml seulement) : un maillage de
Delaunay dont les arêtes partent en étoile de chaque trou et du clou, celui des films d'arcs. Le Python (donc le notebook, et les films
MP4 de référence) garde l'ancien maillage **en deux bandes** : des verticales par les trous et des diagonales. Les deux films de la
triangulation ne se ressemblent donc pas, et leurs lignes de construction non plus. La raison est l'histoire du dépôt : les deux bandes
ont été conçues d'abord ; le maillage grossier est venu avec les films d'arcs, puis a été ajouté à `Film.cree` le 2026-11-19 pour la
page, et n'a **pas été porté en Python** (`grossier` vaut faux par défaut « comme le Python » : les films MP4 de référence restent
identiques octet pour octet entre Python et OCaml). Pour que le notebook montre les mêmes arêtes que la page, il faudrait porter
`grossier` en Python (`Film.__init__`) : un travail à part, qui changerait le film de la triangulation du notebook.

### Essais d'images (2026-11-20)

- **L'arc au centre des rubans** (en trait noir fin) : sans intérêt. Les quatre arcs se superposent aux rubans, et l'on voit le même
  dessin en plus sombre. Écarté.
- **Les arêtes sous les rubans** : presque invisibles avec le style du Python (0,7 px, gris très clair) : des fils fins en éventail.
  C'est surtout le style qui les rend illisibles (voir la comparaison à style identique plus bas).
- **Les arêtes du maillage grossier sous le film de la triangulation, à 3 px** (l'image de la page, tracé gris) : lisibles, et
  elles expliquent le dessin : chaque brin est une suite de points sur des arêtes, et il se plie là où il les traverse. Le trait est
  un peu lourd (il rivalise avec les couleurs) : un gris plus clair et un trait plus fin sont à essayer.
- **Rubans et triangulation, à style identique** (le vrai code OCaml, dessiné comme `dessineImage`, tresse `[1, -2, 1, -2, 3]`) :
  - Les deux maillages sont construits par la même fonction (`Raccord.maillage_du_raccord` : triangulation de Delaunay, bord convexe
    hors de l'image) mais **à partir de points différents** : la triangulation a ses *n* trous et **un seul point en bas, le
    clou** ; les rubans ont leurs *n* trous voyageurs et **n trous fixes espacés de 30 px sur une ligne en bas, sans clou**. Le bas
    des rubans est donc fait de plusieurs petits éventails serrés qui ne bougent pas ; celui de la triangulation d'un seul, qui
    converge vers le clou.
  - **La différence d'aspect vient surtout du nombre de brins à dessiner, pas du maillage.** Le film de la triangulation dessine les
    images des générateurs : pour `[1, -2, 1, -2, 3]`, des mots de 17, 5, 15 et 1 lettres, soit 38 passages autour des trous, et
    des polylignes qui coupent l'axe 52 fois ; chaque passage est un brin de plus à loger. Il les tasse à écart fixe (`ecart`,
    `tend`) et élargit la disposition des trous en proportion : d'où les faisceaux serrés autour des trous. Le film des rubans n'a
    qu'**un arc simple par générateur** (4 ici), sans enroulement : quelques traits fins, et un cadre bien moins rempli (même chose
    sur la tresse de référence à 5 brins : mots de 5, 7, 3, 5 et 1 lettres, soit 21 passages, contre 5 arcs). C'est l'argument du
    diagramme de courbes : un arc par générateur porte la même information que le lacet.
  - **Conséquence pour la construction :** sous un faisceau dense, les arêtes expliquent où les brins se plient ; sous quelques arcs
    simples, il y a presque rien à expliquer. Cela confirme que la triangulation est le premier film à équiper.
  - **Gris clair à 1,5 px** : discret, presque une toile de fond ; trop faible pour les rubans, qui sont fins.
  - **Gris moyen à 2,2 px** : lisible pour les deux films, sans écraser les lacets. C'est le réglage à retenir pour une première version.
  - Pour les rubans, les arêtes se lisent mais disent peu : un ruban suit presque toujours une arête (de son trou fixe à son trou
    voyageur), il ne s'y plie pas.

### Ce que cela coûte (mesuré)

Mesures en OCaml sur `[1, -2, 1, -2, 3]`, dernière image, maillage de la page :

| Film | Points des lacets | Arêtes du maillage | Données en plus |
|---|---|---|---|
| Rubans | 2 544 (5 088 nombres) | 69 (276 nombres) | environ +5 % |
| Diagramme de courbes | 2 092 (4 184 nombres) | 60 (240 nombres) | environ +6 % |
| Triangulation | 7 450 (14 900 nombres) | 60 (240 nombres) | environ +2 % |

Rien à calculer en plus (les positions sont déjà dans le maillage), et 60 à 70 segments à tracer par image : négligeable. On peut
donc **toujours** envoyer la construction ; la case ne commande que le tracé. La question « calculer le deuxième jeu seulement
si demandé » de la section précédente ne se pose pas ici.

**Pourquoi c'est bien moins cher que dans le notebook :** le notebook envoie des images rasterisées (PNG), et un deuxième jeu
double le rendu et la mémoire ; la page envoie des vecteurs, et la construction n'en est qu'un petit supplément.

### Ce que ferait la page

1. `ocaml/web/ardoise_web.ml` : `image` reçoit un champ facultatif `construction` (segments à plat, `x0, y0, x1, y1, …`).
   `travail.js` n'a rien à changer : `enFloat32` convertit déjà les tableaux de nombres.
2. Lacets : le port de `aretes` et des opacités du raccord (voir ci-dessus), avec un test dans `dune test` contre une référence écrite
   par `python ocaml/test/genere_reference_conforme.py`. Les films MP4 d'OCaml ne changent pas.
3. `web/ardoise.js` : `dessineImage` trace `image.construction` en premier, en gris clair et trait fin ; `etendue` (qui décide du
   zoom arrière) **ignore** la construction : l'axe des lacets va à ±10 000 et les arêtes du maillage touchent le bord du cadre,
   et l'un comme l'autre dézoomeraient tout le film ; `Lecteur` reçoit une case par film, qui redessine l'image courante, cachée
   pour l'escargot, le bouquet et les films « indisponibles ».
4. `web/index.html` et `web/ardoise.css` : l'étiquette et le style de la case ; une phrase dans l'infobulle de chaque film.
5. `web/construit.sh` : `ardoise_lib.js` est reconstruit et commité (le hook `pre-push` le refuse sinon).

### Questions ouvertes

- **Quels films ?** Par ordre d'intérêt : la **triangulation** (les arêtes expliquent le dessin), les **lacets** (l'axe et la ligne
  brisée, mais c'est le port le plus lourd). Pour les **rubans** et le **diagramme de courbes**, l'arc au centre est écarté ; les
  arêtes sont celles d'un maillage de même construction que pour la triangulation (voir ci-dessus), et lisibles avec le style plus marqué : à essayer
  avant de décider d'en mettre une case.
- **Lacets : le raccord.** Pendant le raccord, les segments L–A et B–R s'estompent pendant que L–B et A–R apparaissent : si le tracé
  les montre sans estompage, ils sautent. Il faut donc les opacités, d'où le port plus lourd que les autres films.
- **Par défaut décochée.** Et l'état de la case : conservé quand le mot change ? (je pense que oui).
- **Une case par film** (demandé) ou aussi une case commune ?

### Une remarque pour le notebook

Le coût du notebook vient de ce qu'il envoie des PNG. Un lecteur qui redessinerait des polylignes, par exemple sur un canvas
d'`ipycanvas` (déjà dans `environment.yml`), rendrait la construction presque gratuite, comme sur la page. Ce serait un autre
chantier (réécrire dans le notebook le dessin que fait `dessineImage`), à comparer avec la recommandation de la section
précédente (deux jeux d'images complets).

## Ce qui est fait (2026-11-20) : la case du film de la triangulation, sur la page

- `ocaml/web/ardoise_web.ml` : `image` a un champ facultatif `construction` ; le film de la triangulation y met les arêtes du
  maillage (`aretes_a_plat`, segments à plat dans l'ordre rangé des arêtes, 60 segments pour `[1, -2, 1, -2, 3]`). Rien n'est
  recalculé : les positions sont déjà dans le maillage.
- `web/ardoise.js` : `dessineImage` trace `image.construction` avant les lacets (gris `#999`, 2,2 px) quand le lecteur le demande ;
  `Lecteur` a une case « lignes de construction » (seulement pour la triangulation), dont l'état est conservé quand le mot
  change et que `?construction` coche au départ ; `etendue` ignore la construction. `web/ardoise.css` : le style de la case, qui
  passe à la ligne sur écran étroit. L'infobulle de la vue le dit.
- `web/ardoise_lib.js` reconstruit. `dune test` : 83 tests passent.
- **Vérifié dans Edge** (sans fenêtre, sur une page de test qui charge le vrai `ardoise_lib.js` et le vrai `ardoise.js`, sans Web Worker) :
  la case apparaît à côté du curseur ; décochée, l'image est celle d'avant ; cochée par un vrai clic, les arêtes passent sous les lacets,
  sur `[1, -2, 1, -2, 3]` et sur un mot chargé à 9 lettres ; les images passent par la même conversion en `Float32Array` que celle de
  `travail.js` ; la mise en page à 390 px de large tient sur une ligne. **Pas vérifié** : le chemin réel par le Web Worker (les canvas
  de la vraie page étaient encore vides quand la capture a été prise : Edge sans fenêtre n'attend pas les workers) ; la lecture
  animée avec la case cochée.
- **Pas fait** : les rubans, le notebook.

### Les lacets, le même jour

- `ocaml/lib/conforme.ml` : `Conforme.aretes` porte `Lettre.aretes` du Python (les morceaux de l'axe hors du bloc, puis L–A, A–B, B–R, L–B,
  A–R) ; `ocaml/lib/film_conforme.ml` : chaque `image` a un champ `construction`, des segments avec leur opacité (`construction` :
  l'axe et A–B à 1, L–A et B–R à 1 − poids, L–B et A–R à poids, poids étant la part du raccord ; les segments invisibles sont omis).
  Les films MP4 d'OCaml ne les tracent pas : leur dessin est inchangé.
- **Test** : `ocaml/test/genere_reference_conforme.py` écrit aussi les arêtes de `Lettre.aretes` (64 lettres, 4 instants chacune) et
  `test_conforme.ml` les compare à 1e-9 ; un changement de l'ordre des cinq segments fait échouer `lettre 0` (vérifié). `dune test` :
  83 tests passent.
- `ocaml/web/ardoise_web.ml` : `image` a aussi un champ facultatif `opacites` (un nombre par segment) ; `web/ardoise.js` :
  `traceSegments` trace un segment à la fois quand il y a des opacités ; la case a une infobulle par film (le maillage pour la
  triangulation ; l'axe et la ligne brisée L–A–B–R pour les lacets).
- **Ce que la case dit vrai, et ce qu'elle ne dit pas** : hors du raccord, le dessin est la carte conforme de la région au-dessus de la
  ligne brisée, qui en est donc bien le support. Pendant le raccord (la moitié de chaque demi-tour), le dessin passe par une triangulation
  mobile (`Raccord`) ; les deux lignes brisées qui s'estompent l'une dans l'autre sont les références entre lesquelles on raccorde, pas
  le support du dessin à ce moment. Le « ? » à côté de la case « construction » le dit dans une bulle (survol, clavier ou appui ; une phrase sous le lecteur avait été essayée
  d'abord, puis remplacée à la demande de l'utilisateur) : la première version promettait « la ligne brisée sur laquelle le dessin est
  fait », et n'était visible qu'au survol de la case. Pour le diagramme de courbes et la triangulation, c'est exact : les courbes sont des points
  posés sur les arêtes du maillage affiché, qui se déplace, se retourne et tend les courbes à chaque pas.
- **Vérifié dans Edge** (même page de test que pour la triangulation, sur `[1, -2, 1, -2, 3]`) : avant le raccord, la ligne brisée L–A–B–R
  passe par les trous ; au milieu du raccord, le losange L–A–B–R avec ses segments à demi estompés ; à la fin, l'axe droit. Pas vérifié :
  le chemin réel par le Web Worker et la lecture animée (à essayer sur la vraie page).

### Le diagramme de courbes, le même jour

- Décision de l'utilisateur, contre ma recommandation (les arcs *sont* déjà les segments entre les trous, donc la construction n'a rien
  d'équivalent à la ligne brisée des lacets, et les arêtes dominent un dessin de quelques fils fins) : **l'aspect esthétique et dynamique de
  la triangulation qui bouge sous les arcs** justifie la case. Elle trace les arêtes du maillage (`image_arcs`, `aretes_a_plat`) ; pas pour
  les rubans.
- **Un défaut du zoom, révélé par la case** : `image_arcs` envoie un « clou » factice à (−100, −100), hors du cadre, que `etendue` comptait
  comme un vrai point : la vue reculait et décalait le dessin (le diagramme de courbes était petit, tout en bas de son cadre, depuis
  l'origine de la page), et avec les arêtes elle laissait voir le bord du maillage (le rectangle bombé à 40 px hors de l'image).
  Corrigé : pour les films d'arcs, `etendue` compte les trous fixes et non le clou. Le diagramme et les rubans remplissent leur cadre.
- Vérifié dans Edge (page de test) : la case sur le diagramme (image finale et image 30), et les rubans sans case, recentrés.

