# CLAUDE.md

## Qui tu es, ce que tu vises

Tu es un mathématicien amateur qui aime représenter la théorie des tresses par des dessins et des films.

Ce que tu sais déjà faire :
- figurer un mot de tresse par les croisements de brins, à la manière classique ;
- représenter l'automorphisme du groupe libre associé à une tresse
  (J. Birman, *Braids, Links, and Mapping Class Groups*).

Le but : **un film** où les méandres du groupe libre se dessinent de manière continue au fil de la tresse,
et pas seulement une image figée pour un mot donné.

On code en Python, on dessine avec Cairo (pycairo).

## Le projet

« Ardoise à tresse » : dessiner des éléments du groupe de tresses d'Artin B_n.
Deux représentations :
- le diagramme de tresse classique (`dessine_tresse([4, -2, 3, -2])`) ;
- l'action d'Artin de la tresse sur le groupe libre F_n, dessinée comme des lacets
  autour de n trous (`dessine_auto_de_tresse(...)`).

Référence mathématique : *Le calcul des tresses*, P. Dehornoy.
Conventions de signe comparées à celles de l'article *Des matrices pour des tresses* (Images des mathématiques, 2026) :
`conventions_de_signe.md` (β de l'article = β⁻¹ chez nous ; on garde nos conventions).

## Organisation

- `ipynbks/` : notebooks historiques (ipycanvas pour le canvas HTML5, `AutoMorphCairo.ipynb` en pycairo).
  Liens Binder dans le README, ne pas casser leurs chemins. `Ardoise.ipynb` : un cahier qui se lit seul. Il écrit
  le travail sur le mot de tresse (action d'Artin : `conjugaison_locale`, `simplifie`, `calcule_autofn_de_tresse`, recopiés
  de `tresses.py`, sans test ; diagramme de tresse en pycairo), explique les quatre films, puis son
  ardoise (dernière cellule). La plomberie est dans `python/Interface.py` : lecture du mot écrit (`lis_mot`, mêmes limites :
  8 brins et 40 lettres, 6 brins et 14 lettres pour les lacets et la triangulation), douze exemples, lecteur `ipywidgets`
  (curseur et bouton de lecture : ni vidéo ni `ffmpeg`), un film par fonction (`film_diagramme_de_courbes`, `film_lacets`
  — `dessins_conforme` + `surface_conforme` de `Conforme.py`, que `film_conforme` utilise aussi —, `film_triangulation`,
  `film_rubans`) et la classe `Ardoise` (champ, menu, onglets calculés à la demande ; on lui donne la fonction du
  diagramme et celle de l'action). Notebook commité sans sorties ; pas de test automatique de l'interface (essayée par une
  exécution `nbconvert` d'une cellule par action).
- `python/AutoMorphPNG.py` : version script complète (pycairo → PNG) de l'algorithme de dessin
  des automorphismes. Sert de référence fonctionnelle.
- `python/tresses.py` : **base commune** importée par les deux scripts suivants : mots de F_n et action d'Artin
  (`calcule_autofn_de_tresse`), état d'un méandre (`intervalles`, `abscisses`, `etat_de_tresse`), action algébrique
  de σ_i (`agit`, `reduit`), dessin d'un état (`dessin_etat`, `peint`, `image_auto_de_tresse`), relecture des mots
  (`lit_mot`), arcs de cercle raccordés (`deux_arcs`), images (`en_image_pil`, `gif_en_mp4`). Ses `assert` tournent
  à chaque import (rapide).
- `python/NouvAutoMorph.py` : films successifs à partir de l'état (image par image, algébrique, simultané, essais
  en arcs) : voir plus bas. `from tresses import *` ; lancé (`__main__`), il écrit ses images et ses films.
- `python/Triangulation.py` : **le film actuel** (triangulation mobile, point 11 plus bas), `film_triangule`.
- `python/Conforme.py` : film par représentation conforme (point 13 plus bas), `film_conforme`.
- `python/Raccord.py` : raccord par triangulation mobile du film conforme (`raccord='triangulation'`).
- `python/Arcs.py` : essai sans clou, des arcs entre trous fixes et trous voyageurs (piste 1 ter de
  `pistes_film_conforme.md`), `film_arcs` ; `hyperbolique=True` tend les arcs en géodésiques
  (`python/Geodesiques.py`, piste 1 bis : métrique de Klein des triangles de Delaunay) ; `DiagrammeCourbes` :
  le diagramme de courbes (arcs = segments de l'axe, un seul point fixe à gauche), dessin `lisere=True` ;
  `fixes='gauche'` : trous fixes groupés au bout gauche de l'axe au lieu d'en bas ; `ecart_fixes` (≥ 30 px en bas).
- `python/Escargot.py` : un escargot fait de rubans (trous fixes à gauche, chorégraphie libre : anneau qui tourne
  pour la coquille, tête, yeux), `film_escargot` → `imgs/escargot/film.mp4`.
- `ocaml/` : réécriture en OCaml (`plan_ocaml.md`), sous WSL. Étape 1 faite : `lib/tresses.ml` (lettres, mots
  réduits en type privé `Reduit.t`, action d'Artin). Étape 2 faite : `lib/triangulation.ml` (`Maillage` en
  structure persistante, arêtes et triangles en types privés rangés, noeuds de courbe en type somme,
  `maillage_initial`). Étape 3 faite : `lib/film.ml` (mouvement des trous, `tend`, `polyligne` en congés, `mots` ;
  `lit_mot` et `deux_arcs` dans `lib/tresses.ml`, points dans `lib/geometrie.ml`). Une lettre jouée en OCaml depuis
  un état du Python redonne l'état suivant du Python à 1e-15 près ; 0,3 s pour les deux films d'essai (4,5 s en
  Python). Étape 3 bis faite : le méandre dans `lib/tresses.ml` (`intervalles`, `compare_points`, `abscisses`,
  `etat_de_tresse`, `agit`, `reduit`, `dessin_etat` sans ses options d'animation), `noeuds_de_polyligne` dans
  `lib/triangulation.ml`, `Film.cree` (le `Film.__init__` du Python) : tout le film se calcule en OCaml.
  Étape 5 faite (avant la 4) : `dessin/dessin.ml`, bibliothèque à part qui seule dépend de cairo2 (`peint`,
  `cadre`, `film_triangule`), et `bin/films.ml` (`dune exec bin/films.exe` → `imgs/film_triangule_*_ocaml.mp4`,
  identiques octet pour octet au Python, 6 s au lieu de 12 ; ffmpeg pris dans l'environnement conda). Les arêtes
  grises sont tracées dans l'ordre rangé des deux côtés : là où elles se recouvrent, l'anticrénelage dépend de
  l'ordre, et un pixel d'écart suffit à changer l'encodage AV1. cairo2 demande `sudo apt install libcairo2-dev
  pkg-config`.
  Étape 4 faite : `lib/raccord.ml` (`maillage_du_raccord`), `lib/arcs.ml` (`FilmArcs` et `DiagrammeCourbes` dans
  un même type `Arcs.t`, sans la tension hyperbolique ; `Film.tend_courbes` et `Film.polyligne_de_courbe`
  remplacent l'héritage), `bin/arcs.ml` → `imgs/<méthode>/film_*_ocaml.mp4`, identiques octet pour octet au
  Python (21 s au lieu de 55). Étape 6 faite : `lib/escargot.ml` (chorégraphie libre, `deplace`), `Dessin.cadre_escargot`,
  `bin/escargot.ml` → `imgs/escargot/film_ocaml.mp4`, identique octet pour octet au Python (4,5 s au lieu de 8,4). `Maillage.cherche_arete_a_retourner` parcourt les arêtes dans un ordre
  déterministe, le même en Python et en OCaml (arêtes rangées) : l'ordre d'un set changeait les courbes quand
  plusieurs arêtes étaient à retourner au même pas.
  Étape 7 faite : le film conforme (`lib/conforme.ml` : carte de Schwarz–Christoffel et `Lettre` ; `lib/raccord.ml` :
  `RaccordTriangule` ; `lib/film_conforme.ml` : la boucle et `nb_croisements` ; `Dessin.film_conforme`),
  `bin/conforme.ml` → `imgs/conforme/film_*_ocaml.mp4`, identiques octet pour octet au Python (41 s au lieu de 1 min 35),
  seulement avec le raccord par triangulation (le défaut).
  Étape 8 faite : le premier bouquet (`lib/bouquet.ml` : la classe `Pousse` de `python/Bouquet.py`, `test/test_bouquet.ml`,
  concordant à 1e-6 près ; 0,8 s au lieu de 30 s). L'escargot et le bouquet sont dans la page web (section « Un peu de
  poésie »), dessinés en canvas par `web/ardoise.js` (le dessin Cairo n'est pas traduit pour le bouquet).
  `dune test` dans `ocaml/` compare au Python (`test/reference_*`, écrits par
  `python ocaml/test/genere_reference*.py`). Travailler dans le clone
  côté Linux (`~/dev/braid-blackboard` sous WSL) : dune ne construit pas sur `/mnt/c` (pas de socket Unix). Le proxy
  (`http_proxy`, `https_proxy`) est dans `~/.profile` de WSL, et dans `http.proxy` du git global de WSL (un
  `wsl.exe bash -c` ne lit pas `~/.profile` : sans cela, `git push` restait bloqué). Switch opam local `ocaml/_opam` (ignoré par git) :
  les dépendances sont déclarées dans `ocaml/dune-project` (dune en tire `ardoise.opam`), installation depuis
  `ocaml/` par `opam switch create . ocaml-base-compiler.5.4.1 --deps-only --with-test --with-dev-setup` ; le hook
  de shell d'opam choisit ce switch dans `ocaml/`. Le Python tourne dans le même clone (miniforge et l'environnement
  `braid-blackboard` installés dans WSL).
  Aussi installé sous Fedora (machine personnelle, 2026-11-17) : `sudo dnf install opam` (cairo-devel, pkgconf,
  bubblewrap, gcc déjà présents), `opam init --bare --shell-setup --enable-shell-hook`, puis le même
  `opam switch create .` dans `ocaml/`. `dune test` passe (40 tests) ; films de la triangulation et de l'escargot
  identiques octet pour octet au Python avec le ffmpeg de conda (`FFMPEG=…/envs/braid-blackboard/bin/ffmpeg`).
- `web/` : **l'ardoise à tresse en page web** (étude : `etude_page_web.md`, mode d'emploi : `web/README.md`). Page statique
  HTML + JavaScript + canvas ; le calcul est celui de `ocaml/lib/` compilé par js_of_ocaml (`ocaml/web/ardoise_web.ml`,
  `web/construit.sh` → `web/ardoise_lib.js`, suivi par git : le relancer avant de commiter quand l'OCaml change), un Web Worker par mode de méandre (diagramme, conforme,
  rubans, et le film de la triangulation mobile sans le maillage gris), films en polylignes redessinées sur le canvas. Voir un résultat : `python3 -m http.server` dans `web/` ;
  déploiement : `web/deploie.sh` (rsync vers la cible de `web/deploie.conf`, local et non suivi par git ; règle de cache : `web/README.md`).
  Publiée aussi sur GitHub Pages (`https://xysticus.github.io/braid-blackboard/`) par `.github/workflows/pages.yml`, lancé
  par chaque push touchant `web/` (21 s ; il copie seulement les fichiers). `ardoise_lib.js` est dans git : le hook `.githooks/pre-push`
  (activé par `git config core.hooksPath .githooks`, à refaire après un clone) reconstruit le JS avant chaque push et refuse de
  pousser s'il a changé (le commiter, puis repousser). `git publie` (alias local vers `web/publie.sh`) = `git push` puis
  `web/deploie.sh` : seul un push met à jour GitHub Pages ; le serveur personnel n'est mis à jour que par `deploie.sh`.
  Sous JavaScript, pas de récursion non terminale sur de longues listes (`List.concat`, `List.fold_right`) : la pile est
  petite.
- `imgs/` : images du README. `*.png` est dans `.gitignore` : les images du README existantes sont suivies,
  les nouvelles sorties ne le sont pas. Un sous-répertoire par méthode (`imgs/conforme/`, `imgs/diagramme/`,
  `imgs/rubans/`, `imgs/rubans_gauche/`), chacun avec un README (introduction, mathématiques, commandes) et un
  `apercu.jpg` suivi ; les films (`film_*.mp4`, ignorés) y sont écrits par `python python/Conforme.py` et
  `python python/Arcs.py [rubans] [rubans_gauche] [diagramme]`.

## L'algorithme actuel du méandre (`AutoMorphPNG.py`)

Il marche, mais il est compliqué. Les étapes :

1. `calcule_autofn_de_tresse` : images réduites des générateurs x_i par la tresse (action d'Artin).
2. `decoupeuse` + `generatrice_haut` / `generatrice_bas` : chaque mot est coupé en suites croissantes
   consécutives (`[1,2,3]` = on passe au-dessus des trous 1, 2, 3). Chaque suite donne un arc du haut,
   chaque transition entre deux suites donne un arc du bas.
3. `trie_arcs` / `compare_arcs` : les arcs de *tous* les mots sont triés par emboîtement (le plus intérieur d'abord).
4. `arc_exact` + `positiver` : on numérote les passages sur l'axe horizontal dans chaque intervalle entre trous
   (compteurs gauche/droite, positions signées, puis renormalisées).
5. `cherche_debuts` + `chemine` : on recolle les arcs en lacets en alternant nord et sud.
6. `situe` : conversion en demi-cercles (centre, rayon, angles), puis tracé Cairo.

Ce qui le rend fragile : l'ordre d'emboîtement (`compare_arcs`) n'est pas un ordre total quand des arcs se croisent ;
les positions sont d'abord relatives, puis renormalisées ; on perd l'information « quel arc vient de quel mot »
et il faut la reconstruire. Surtout, le dessin est recalculé d'un bloc pour un mot : il n'y a pas d'état
intermédiaire à animer.

## Le nouvel algorithme, plus simple (`NouvAutoMorph.py`)

Il dessine maintenant les méandres et donne la même topologie qu'`AutoMorphPNG.py`.

1. `calcule_arcs(mot)` puis `intervalles(mot)` : chaque lacet devient la suite des intervalles où il coupe l'axe
   (l'intervalle k est entre le trou k et le trou k+1). De l'indice 2i à 2i+1 c'est un arc du haut, de 2i+1 à 2i+2
   un arc du bas ; le premier et le dernier point sont reliés au clou par le bas.
2. `compare_points` / `suit_en_parallele` : ordre gauche-droite de deux points du même intervalle. On suit les deux
   courbes côte à côte jusqu'à ce qu'elles se séparent ; chaque arc parcouru en parallèle inverse l'ordre (arcs emboîtés).
   Le clou est sous tous les arcs du bas. Si les deux courbes arrivent ensemble au clou, on repart dans l'autre sens.
3. `abscisses` : tri de chaque intervalle avec cette comparaison, puis rang global sur l'axe des points et des trous.
4. `dessine_auto_de_tresse(tresse, fichier)` : demi-ellipses entre points consécutifs, alternativement en haut
   et en bas ; descente verticale vers le clou sous tous les arcs.
5. `croisements` / `verifie` : contrôle qu'aucun arc n'en croise un autre. Les `assert verifie(...)` servent de tests.
6. `film_de_tresse(tresse, fichier)` : GIF (Pillow) des images de chaque préfixe `tresse[:k]`, avec un nombre
   de trous fixé par la tresse entière (`calcule_autofn_de_tresse(tresse, nb_trous)`). `image_auto_de_tresse`
   renvoie la surface Cairo ; `dessine_auto_de_tresse` l'écrit en PNG.
   Le dessin passe par `dessin_etat(etat_de_tresse(...))` (polylignes numpy, positions des trous et du clou) et
   `peint` (trace les polylignes). `lit_mot` relit le mot d'un lacet dessiné (traversées des demi-droites qui montent
   des trous) ; `verifie_dessin` contrôle ainsi le dessin contre les mots.
7. **Action algébrique de σ_i sur l'état** (`agit`, `reduit`) : l'état est fait des abscisses des trous et, pour chaque
   lacet, des abscisses de ses points sur l'axe (seul l'ordre compte ; `etat_de_tresse` le calcule depuis les mots,
   `normalise` le ramène aux rangs). σ_i fait tourner d'un demi-tour le bloc (trous i, i+1 et intervalle i) :
   les points du bloc sont réfléchis ; chaque arc qui sort du bloc (ou descente au clou) reçoit un point nouveau,
   pour σ_i positif à droite du bloc si c'est un arc du haut, à gauche sinon (l'inverse pour σ_i⁻¹) ; d'un même côté,
   les points nouveaux sont dans l'ordre des extrémités intérieures de leurs arcs. Puis `reduit` supprime les bigones
   (deux points consécutifs d'un lacet dans le même intervalle). `verifie_action` part de la tresse vide et applique
   les lettres sans les mots : on retrouve l'état des mots à chaque pas (testé aussi sur 300 tresses aléatoires ;
   le test échoue si l'on inverse la règle du côté ou de l'ordre).
8. `film_de_tresse_algebrique(tresse, fichier)` → `imgs/film_continu_*.gif` : chaque lettre est une suite de
   mouvements élémentaires sur l'état, dessinés par `dessin_etat` (demi-ellipses entre abscisses réelles, place
   réservée au disque du demi-tour, fusions en cours) : (1) réespacement vers `mise_en_page_avec_marge` (couronne vide
   autour du bloc) ; (2) `demi_tour` : rotation rigide du bloc, amortie dans la couronne, faite avant aplatissement ;
   seuls les arcs qui sortent du bloc s'enroulent, les autres lacets ne bougent pas ; hors de la couronne l'axe
   ne bouge pas, le segment i tourne avec les trous, les morceaux des segments voisins accrochés aux deux trous
   (voués à disparaître) sont emportés par le centre de rotation : ils tournent et glissent vers lui en rétrécissant,
   pendant que les nouveaux poussent depuis le bord de la couronne
   (`axe_pendant_demi_tour`) ; (3) retouche morceau par morceau
   vers le dessin de l'état non réduit, dont les points nouveaux sont là où les arcs tordus coupent l'axe
   (`coupe_sur_l_axe` ; un `assert` vérifie que cet ordre est celui de `agit`) ; (4) vagues de bigones
   (`bigones_interieurs`, `retire_bigones`) : ce sont les segments de l'axe qui travaillent ; le segment se bombe
   par-dessus (ou par-dessous) le capuchon, lacets immobiles (`bosses` de `dessin_etat`, demi-ellipse qui englobe le
   capuchon et s'arrête avant les voisins sur l'axe : `marges_des_bigones`), puis redescend en l'écrasant (les deux
   points glissent l'un vers l'autre) ; ensuite balayage exact de la région vide (`fusion_arcs`, `fusion_descente`) ;
   (5) réespacement vers l'image clé (un `assert` vérifie l'état). L'axe est tracé en gris sous les lacets (`peint`).
   Pourquoi pas « lacets figés, puis tout aplatir à la fin » : un bigone peut former un doigt qui passe sous un trou
   voisin ; le segment, accroché à ce trou, ne peut pas le contourner en restant un graphe y = f(x).
   Les segments ne peuvent pas non plus faire le demi-tour : σ_i échange les trous i et i+1, le segment i-1
   devrait changer d'extrémité.
   Réespacer ne crée jamais de croisement : deux demi-cercles se croisent ssi leurs extrémités s'entrelacent.
   Sens : σ_i positif = demi-tour horaire à l'écran (`SENS_DE_SIGMA = 1`, y vers le bas) ; l'`assert` sur l'ordre
   des points nouveaux échoue avec l'autre sens.
9. `film_de_tresse_simultane(tresse, fichier)` → `imgs/film_simultane_*.gif` : **un seul mouvement par lettre**,
   rien ne reste à régler une fois les trous en place (ni bigone à résorber, ni réespacement).
   - Pas de mou : un bigone de l'état non réduit est toujours (point nouveau, bout extérieur Q de son arc), avec Q
     dans l'intervalle voisin du bloc, du côté où l'arc s'enroule ; ces Q sont les points les plus proches du bloc
     (un `assert` le vérifie). `mise_en_page_du_demi_tour` les range avant de tordre : les « doigts » (les deux arcs
     de Q vont dans le bloc) entrent dans le disque rigide, les « passants » (un seul arc) dans la couronne, où ils
     ne tournent qu'en partie et quittent l'axe. Tous les brins traversent la couronne en s'éloignant du centre :
     la torsion les enroule sans créneaux.
   - Deux dessins du même instant u : D_u = H_u(image clé k rangée pour σ), A_u = H_(u-1)(image clé k+1 rangée pour
     σ⁻¹) (`dessin_pendant_demi_tour`). Les passants de l'un sont les points nouveaux de l'autre ; les points communs
     ont les mêmes abscisses dans les deux rangements. L'image est leur mélange de poids u entre points communs
     (`entre_points_communs`). Le rangement se fait pendant le premier tiers de la rotation, le retour aux
     abscisses de l'image clé pendant le dernier (`part_du_rangement`).
   - `verifie=True` relit le mot de chaque lacet sur chaque image (`lit_mot`, trous triés par abscisse : mots de
     l'image clé k avant la verticale, k+1 après).
   - À ne pas refaire : détordre un dessin en demi-cercles dont des points sont dans la couronne (H_(u-1) du dessin
     de l'état non réduit) donne des brins crénelés.
   - Limites : le mélange est linéaire, donc de légères ondulations en milieu de rotation, et pas de preuve
     d'absence de croisement (aucun sur les tresses lisibles essayées ; deux images fautives sur
     `[1,-2,1,-2,1,-2,3,-1,2]`, 140 points sur l'axe).
10. **Essais en arcs de cercle** (demande : plus de courbes libres, uniquement des arcs de cercle qui partent et
    arrivent sur les segments noirs — l'axe et le segment qui tourne — traversés à angle droit). Obstacle : un arc
    perpendiculaire à deux droites sécantes est centré sur leur intersection, donc un brin qui va du segment
    tournant à l'axe ne peut être un seul arc que si ses deux bouts sont à la même distance du centre. Choix
    retenu : une paire d'arcs raccordés avec la même tangente (`deux_arcs`, `lieu_des_raccords`) pour ces brins.
    Deux essais, ni l'un ni l'autre au point (lignes commentées en fin de script, sorties `imgs/essai_*.gif`) :
    - `film_de_tresse_simultane(..., en_arcs=True)` (`lacet_en_arcs`, `segments_en_noeuds`) : on mélange les noeuds
      des deux dessins D_u et A_u (position et direction) et on les relie par des paires d'arcs. Plus d'ondulations,
      mots relus corrects, mais des croisements sur environ une image sur dix des lettres chargées : D_u et A_u
      s'enroulent différemment autour du bloc, leurs noeuds se correspondent mal.
    - `film_de_tresse_en_arcs` : construction directe, sans mélange ni couronne. Points du bloc et doigts sur le
      segment tournant, les autres sur l'axe, demi-cercles entre points d'un même segment, une paire d'arcs par brin
      qui sort du bloc ; le raccord part du passant (ou arrive au point nouveau). Propre en milieu de rotation,
      mais près des images clés des arcs géants sortent du cadre, des brins se croisent, et `verifie` échoue :
      la règle qui place le raccord est à revoir.

11. **Triangulation mobile** (`python/Triangulation.py`, `film_triangule` → `imgs/film_triangule_*.mp4`) : plus d'axe
    ni de couronne. Sommets : trous, clou, extrémités de l'axe, sommets des bords haut et bas à la verticale des
    trous (décalés de 0,31 px pour ne pas être sur le clou). Un lacet est une suite de points sur les arêtes
    (fraction de l'arête), deux points consécutifs dans un même triangle. σ_i : les trous i, i+1 tournent d'un demi-tour,
    les points suivent leur arête, les sommets des bords croisent sans se rejoindre (écart √((r cos θ)² + (g sin θ)²)).
    Les arêtes non de Delaunay sont retournées (`Maillage.delaunay`, `retourne`) : les points de l'arête disparaissent,
    chaque corde qui sépare les deux nouveaux triangles coupe la nouvelle diagonale (`courbe_apres_flip`), la forme ne
    change pas. Aucune réduction de bigones à faire. Dessin : arcs de cercle (`deux_arcs`) entre points d'arêtes,
    sans angle droit imposé. `verifie_triangulation` relit les mots (`lit_mot`) après chaque lettre : bon sur la tresse
    chargée du point 9 et sur 30 tresses aléatoires.
    **Triangulation de départ en deux bandes** (`maillage_initial`) : bande du haut (bord haut → axe, arcs du haut) et
    bande du bas (axe → bord bas, arcs du bas et arrivée des brins au clou). Chaque bande est une échelle de triangles
    entre deux rangées ; les rangées du haut et du bas ont un sommet à la verticale de chaque trou, et le clou est un
    sommet du bord bas (si un trou est à la verticale du clou, le clou est son sommet du bord bas). Un maillage plus fin
    n'a rien apporté. Le dessin de départ est étiré au-dessus de l'axe pour remplir la bande du haut (un brin n'occupe
    que les triangles qu'il traverse). **Plus de bande du bas séparée ni de pointe au clou** : essai précédent (clou en
    pointe de degré 2 sous une base, protégé contre tout flip) qui gardait le départ et l'arrivée de chaque lacet
    dans un même triangle ; il forçait tous les brins à traverser une seule arête puis une bande entière (zigzags
    près du clou) et empêchait de résorber des triangles écrasés. Maintenant le départ et l'arrivée d'un lacet ne sont
    plus forcément dans le même triangle, mais restent voisins autour du clou et la tension les garde proches.
    **Disposition proportionnelle** (`Film.disposition`) : à chaque image clé, la largeur de chaque intervalle de l'axe
    (y compris les deux de gauche et de droite) est proportionnelle à 1 + le nombre de brins qui le traversent
    (compté dans l'état : il égale les croisements réels de l'axe sur le dessin, vérifié à chaque image clé), donc
    l'écart `s` entre deux points consécutifs de l'axe est le même partout ; la verticale suit le même écart (les brins
    se tassent près des trous). Pendant la lettre, les trous glissent de la disposition de l'image clé k à celle du
    milieu de la lettre (`Film.milieux` : disposition de l'état non réduit `agit(état k, σ)`, qui compte les brins
    passant de chaque côté du bloc pendant le demi-tour), puis à celle de l'image clé k+1 (`Film.abscisses`,
    interpolation douce ; centre et rayon du demi-tour suivent ; le clou garde sa place relative entre ses deux
    voisins du bord bas), toujours un seul mouvement par lettre. Sans la disposition du milieu, la bande de droite de
    la tresse de référence (1 brin avant et après σ₄⁻¹) était trop étroite pour le jaune qui fait le tour de la paire
    pendant le demi-tour : il recouvrait le bleu. L'écart `ecart` de `tend` est celui de la disposition
    (interpolé), le trait est au plus 70 % de cet écart. Le dessin de départ est replacé sur la disposition 0 par une
    transformation affine par morceaux des abscisses. Plus la tresse est chargée, plus `s` est petit (2,8 px à la 7ᵉ
    lettre de la tresse chargée).
    **Film** : 800 × 800 par défaut (longueurs en pixels réglées pour 400 et multipliées par `largeur / 400`).
    **Vitesse constante** (`Film.lettre`, `chemin_des_trous`) : les trous avancent de `VITESSE` = 6 pixels par image
    (chemin cumulé de l'ensemble des trous) ; le temps de la lettre est reparamétré par la longueur de ce chemin, et
    une lettre dure (longueur du chemin) / vitesse images (53 à 177 images sur la tresse de référence), 2 sous-pas par
    image. Le glissement des trous (`abscisses`) est linéaire par morceaux (un adoucissement les arrêtait au milieu
    et aux bouts de chaque lettre ; une interpolation courbe pourrait intervertir deux trous voisins). Pas de pause
    entre les lettres, seulement sur la première et la dernière image. `film_triangule`
    écrit le MP4 au fil du calcul par un tube vers ffmpeg (un GIF de cette taille ne tiendrait pas en mémoire) ;
    `Film.lettre(..., rendu=f)` appelle f avec chaque image, sans rendu rien n'est dessiné (tests plus rapides).
    **Tension dès la première image** : 400 pas de `tend` dans `Film.__init__`.
    **Dessin en droites et congés** (`Film.polyligne`) : la ligne brisée des points, chaque coude arrondi par un congé
    (arc de cercle tangent aux deux segments, qui prend au plus la moitié du plus court) : rien que des droites et des
    arcs, sans point d'inflexion. Un brin tendu reste droit jusqu'à son coude ; les enroulements, faits de petits
    coudes réguliers autour d'un trou, sont des cercles. 0 croisement sur toutes les images clés des deux tresses
    d'essai, et sur une image sur quatre des deux films ; les brins ne se touchent que dans l'éventail du clou. Essais écartés : une direction par point (corde entre les voisins) et une paire d'arcs (`deux_arcs`) par
    segment : un brin droit qui tourne d'un coup en un point fait un S dans le segment qui précède (zigzags des brins
    extérieurs, 2 à 8 croisements par image clé) ; imposer la perpendiculaire au rayon aux points « plaqués » contre un
    trou (36 croisements : deux brins voisins d'un faisceau qui quitte un enroulement n'ont pas le même statut).
    **Brins attachés au clou** : leur premier (dernier) passage sur l'axe (`portions_du_clou`) est remplacé dans le
    dessin par deux points de part et d'autre de l'axe, sur la verticale si le brin traverse l'axe à moins de 45° de la
    verticale (poids décroissant avec l'angle), sinon dans la direction du brin : ils partent de l'axe
    perpendiculairement sans faire de cran quand, pendant un demi-tour, ils traversent l'axe en biais.
    Essai abandonné : tirer les points de ces brins vers un chemin imposé (arc de cercle centré sur l'axe, vertical au
    départ, de rayon κ × éloignement à la verticale du clou, puis tangente jusqu'au clou ; avec ou sans descente
    verticale jusque sous les arcs du bas). Ces chemins ne se croisent pas entre eux (vérifié numériquement), mais
    ils ignorent les arcs du bas qui enjambent la colonne du clou : ces arcs étaient écrasés contre les brins du clou,
    la profondeur « sous les arcs » s'emballait (rétroaction), jusqu'à 60 croisements par image.
    Réespacement continu (`Film.tend`, taux 0,15 par sous-pas) : plus de répartition uniforme sur les arêtes (elle étalait les brins sur toute la longueur,
    trop loin des trous). `Film.tend` : chaque point est tiré vers l'endroit de son arête où ses deux voisins sont
    alignés avec lui (le brin se tend), puis, arête par arête, les points gardent leur ordre, restent à `ecart`
    les uns des autres perpendiculairement aux brins (ecart / sinus le long d'une arête traversée en biais, sinus
    borné à 0,3 : dans un triangle plat, l'écart le long de l'arête ne suffisait pas) et à `ecart` des sommets
    (régression monotone bornée, `monotone`).
    Les brins se tassent à écart fixe près des trous et laissent du vide au-delà, comme les demi-cercles emboîtés des
    images clés (écart régulier sur l'axe, remplissage vertical qui part des trous). L'ordre sur chaque arête est
    conservé, donc pas de croisement des cordes.
    croisement. Les cordes ne se croisent jamais ; avant les congés, les arcs lissés se croisaient parfois (jusqu'à 194 sans la tension). Essais sans effet : tangente « bissectrice » (pire), remplacer un arc qui sort de son triangle par la corde (140 croisements : la corde coupe les arcs voisins du faisceau), tout le triangle en cordes (44 → 36 seulement : les croisements restants sont des arcs qui se coupent à l'intérieur d'un même triangle). Pour détecter un croisement, ignorer les
    intersections aux extrémités (les brins se rejoignent au clou).

12. **Morphing de lacets : un bouquet qui pousse** (idée du 2026-11-14, prototype `python/Bouquet.py`, séparé du
    travail sur les tresses). Une tresse est un mouvement de n points dans le disque ; nos demi-tours sur l'axe n'en
    sont qu'un cas. Si les trous suivent des chemins quelconques (une « chorégraphie » : position de chaque trou à
    chaque instant), les lacets sont emportés par la déformation du plan qui accompagne ce mouvement : un morphing
    de lacets, topologie exacte comme dans le film des tresses (triangulation mobile, flips, tension, congés).
    Déjà prêt : `Maillage`, `tend`, le dessin en congés ne dépendent pas de l'axe. Dépend de l'axe : le mouvement
    (`place`, dispositions), le départ perpendiculaire des brins du clou, la relecture des mots (`lit_mot`,
    demi-droites verticales). Seule contrainte : deux trous ne se rencontrent jamais.
    Le bouquet : des trous qui montent depuis le clou tirent des lacets (tiges) ; des groupes de trous qui tournent
    les uns autour des autres enroulent les lacets en rosaces (chaque tour ajoute une couche de pétales) ; couleurs
    qui virent du vert (tige) à la couleur de la fleur ; éventuellement régions entre lacets remplies (pétales
    pleins), tension relâchée pour un rendu plus végétal. Visée : les documentaires en image par image (time-lapse)
    qui montrent une plante pousser jour après jour, côté « surgissant ».
    **Prototype** (`python/Bouquet.py`, `film_bouquet` → `imgs/bouquet.mp4`, portrait 3:4 810 × 1080, 15,5 s,
    calcul ~35 s, 35 trous ; têtes données par (abscisse, hauteur au-dessus du sol)) :
    `Pousse` hérite de `Film` (état de départ d'une tresse à n brins, puis `y_axe = -inf` pour couper le départ
    perpendiculaire des brins du clou). Les trous dorment en rang serré sous une terre épaisse (la graine) : les
    pousses surgissent du sol. Chaque plante (`fleur`, `feuille`) monte le long d'une tige de Bézier en oscillant
    (nutation). **Éclosion** (idée de l'utilisateur) : une fleur = 5 sépales et 4 pétales rangés par angle de 250° à
    -70° (avec un écart de 2,3 px, à 240°/-60° les lacets des sépales du bas se séparaient de nouveau de la tige) (le bas reste ouvert pour la tige ; à 210°/-30°, les lacets des sépales du bas filaient droit vers le clou,
    lignes isolées à côté des tiges) ; les sépales forment une cage qui ne tourne pas, les pétales tournent
    d'un tour à l'intérieur (les lacets s'enroulent en couches : le bourgeon), puis sortent entre les sépales ; les
    couches, retenues par les sépales, gonflent en lobes pincés entre eux : la fleur sort du bourgeon au lieu de le
    gonfler. Essais écartés : sépales qui tournent avec les pétales (ils sont alors à l'intérieur des couches et ne
    retiennent rien : contour convexe sans vallée) ; trop de trous ou un écart de 6 px (faisceaux de 450 px de large) ;
    tension très relâchée (taux 0,06 : grands drapés) ; 3 pétales (triangle) ; 2 tours de bourgeon (trop de couches).
    Réglages : écart 2,3 px (tiges moins épaisses), trait 1,4 px, taux 0,12 (tension un peu relâchée), rayons bourgeon 20, sépales 52,
    fleur 100 ; montée sans croisement de trous grâce au passage par un demi-cercle dans l'ordre de la graine
    (distance minimale contrôlée). Feuille : deux trous sur un segment qui s'allonge ; les feuilles sont aux deux bouts de la graine, tournées vers
    l'extérieur (entre deux fleurs, une feuille coupait le chemin d'une tige et la faisait plier). Dessin : fond bleu clair, pas de
    sol (les tiges convergent vers le clou en bas de l'image ; hauteurs des têtes comptées depuis le bas), lacets (trait 2 px) remplis d'une couleur transparente puis tracés ; verts pour les
    tiges et les feuilles ; une fleur est peinte en deux fois (`secteur_de_fleur` : disque de 2,6 × son rayon autour
    de la tête, privé d'un coin de 50° dans la direction de la tige, qui ne commence qu'au-delà des sépales : sinon
    le vert de la tige montait en pointe jusqu'au cœur) : en vert hors du secteur, et dans le secteur
    en bicolore, blanc au centre puis de la couleur de la fleur, qui remplace le vert du bouton à l'éclosion (le vert
    disparaît des fleurs, la couleur ne descend pas sur les tiges) ; chaque image calculée montrée deux fois, lumière
    constante (une variation d'une image à l'autre faisait clignoter). Essai abandonné à la demande de l'utilisateur (copie hors dépôt) : une calanque (cailloux de
    calcaire faits de lacets enroulés, sable, pluie, bulbe d'où sortent les plantes), traits épais, fond noir. `insere_sommet` (sommet ajouté dans un triangle, cordes
    recoupées) et l'anneau de satellites ne servent plus (ils arrondissaient les corolles de la première version).
    **Bouquet en diagramme de courbes** (`PousseDiagramme`, `film_bouquet(..., classe=PousseDiagramme)` →
    `imgs/bouquet_diagramme.mp4`) : la graine est l'axe d'un diagramme de courbes, points au sol entre les plantes ;
    arcs du sol aux sépales du bas (tiges), sépale-pétale-sépale dans les fleurs (pétales en V, striés par le
    bourgeon), limbe des feuilles. Voir `pistes_film_conforme.md`.
    Retouche de `Triangulation.py` pour 35 trous : si les trois décalages habituels du bord bas sont trop près du
    clou, on prend celui qui en éloigne le plus (films des tresses inchangés).
    **Maillage grossier** (2026-11-19, OCaml seulement, `Film.cree ~grossier:true`, utilisé par la page web) : maillage de
    Delaunay des films d'arcs (`Raccord.maillage_du_raccord` : trous, clou, bord convexe hors de l'image) à la place des deux
    bandes en échelle ; plus de rangées de bord ni de brins du clou perpendiculaires. Les brins s'enroulent en polygones
    concentriques autour du trou contourné et partent du clou en éventail droit ; plus robuste (0 échec sur 400 mots jusqu'à
    6 brins et 14 lettres). Les films MP4 et le Python restent sur l'échelle.
    **Flips par traversées** (2026-11-19, OCaml seulement, option `par_traversees` de `Film.lettre` ; essayée sur l'échelle, puis
    écartée au profit du maillage grossier, avec lequel elle dégrade le dessin) :
    `Maillage.delaunay_par_traversees` retourne aussi une arête quand le flip diminue le nombre de points des courbes sur la
    diagonale (à égalité, Delaunay ; garde-fous : triangle > 150° toujours retourné, pas d'angle > 120° créé) ; les brins du
    clou partent en éventail droit vers le faisceau au lieu de monter le long d'arêtes qu'ils traversent en biais. Pas dans le
    Python ni dans les films MP4 de référence (`test/test_traversees.ml` : mots relus justes).
    Autre retouche (2026-11-19, aussi en OCaml, `Film.cree`) : un décalage du bord bas n'est retenu que s'il laisse tous les
    sommets du bord dans le cadre, dans toutes les dispositions de la tresse (avec 24 px, le sommet du dernier trou allait sur
    le coin droit : « triangle retourné » sur une tresse aléatoire sur quatre à 5 brins et 12 lettres). Films des tresses d'essai
    inchangés. Reste, pour moins d'un mot sur cent, un triangle retourné (deux trous voisins et un bout de l'axe alignés à une image
    clé), évité le plus souvent en rejouant avec plus de sous-pas (`web/`). Option `cadre` de `Film.cree` : fausse pour le bouquet.

13. **Film par représentation conforme** (`python/Conforme.py`, `film_conforme` → `imgs/conforme/film_*.mp4`). Idée de l'utilisateur (2026-11-16) : relier les trous qui tournent aux trous voisins par des segments,
    et s'en servir comme pieds d'arcs, pour tendre les lacets « flasques » du film simultané.
    - Pendant σ_i, l'axe se plie en ligne brisée L–A–B–R (A, B : trous i, i+1 ; L, R : voisins, ou points virtuels
      au bord de l'image). Elle reste simple de 0 jusqu'à juste avant la fin du demi-tour, où L–A passe par B ; ses
      pieds sont exactement les points de l'image clé k. L–B–A–R porte de même l'image clé k+1, de juste après le
      début jusqu'à la fin. Un changement à mi-chemin est inévitable : un cadre fixe (l'axe entier + le segment qui
      tourne, la « croix ») donne des descriptions différentes depuis k et depuis k+1, à chaque lettre (vérifié).
    - Dessin d'un état sur sa ligne brisée : `Carte`, Schwarz–Christoffel du demi-plan sur la région au-dessus (et,
      par symétrie, au-dessous). Antécédents des sommets par Newton sur les longueurs des côtés ; tables du bord avec
      changement de variable aux singularités ; images par intégration de dz/dw le long du chemin, l'erreur répartie
      entre les deux pieds connus. Un arc est l'image du demi-cercle entre les antécédents de ses pieds : perpendiculaire
      aux segments, jamais de croisement (bijection conforme). Sur l'axe droit la carte est une translation : les
      images clés sont les demi-cercles habituels (0,02 px près).
    - Descentes au clou : la géodésique du demi-plan du bas, arc du cercle orthogonal à l'axe passant par le pied et
      l'antécédent du clou (deux se recoupent seulement au clou ; aucune ne croise un arc du bas tant que le clou est
      hors des demi-cercles, vérifié par `assert`). Les images clés de ce film ont donc des descentes en arcs.
      Essais écartés : descentes verticales dans le demi-plan (les pieds près d'un coin convexe ont des antécédents
      serrés, leurs descentes restaient collées jusqu'au clou) ; glissement en S sous les arcs (crans).
    - Raccord autour de la verticale (`fenetre` = 0,5 du mouvement depuis le raccord par triangulation ; 0,3 avant) : les cinq segments L–A, A–B, B–R, L–B, A–R ont
      leurs sommets aux trous, donc la suite minimale des traversées d'un lacet est la même dans les deux dessins.
      `traversees` + `sans_bigones` (deux traversées successives d'une même arête bordent un bigone vide : on les
      annule) donnent les morceaux correspondants, mélangés un à un (`raccorde`). Un bigone d'un dessin est apparié
      au point de l'autre dessin à la même fraction de longueur du morceau : il se résorbe vers ce point. (Mélanger
      tout le morceau par longueur d'arc faisait des bosses ; apparier au point le plus proche, des encoches.)
    - Si les arcs sortent par le haut en cours de demi-tour, l'aplatissement est réduit pour l'image (`reduction`).
    - Rendu : seulement les lacets et les trous (`construction=True` trace aussi l'axe et la ligne brisée en gris :
      leurs changements brusques donnaient une sensation râpeuse) ; pas de pause entre les lettres.
    - Taille : 800 × 800 avec des marges de 60 px (`marge` : dessin fait dans le cadre intérieur puis décalé), traits
      de 3 px (référence) et 2 px (chargée), comme à 400 × 400. MP4 écrit directement par un tube vers ffmpeg.
    - `Carte.image` part d'un point du bord loin des antécédents des sommets : partir d'une singularité rendait
      l'intégration bruitée et le Newton du clou oscillait.
    - `verifie=True` relit les mots et compte les croisements entre lacets (`nb_croisements`, paquets de segments
      à rectangles englobants). Tresse de référence : 0 anomalie. Tresse chargée `[1,-2,1,-2,1,-2,3,-1,2]` :
      7 images à quelques croisements, au milieu du raccord des lettres 6 et 7 (seule étape sans garantie : le
      mélange ; encoches près des trous qui tournent, brins extérieurs tassés). Environ 1 min 30 pour les deux.
    - Limites : légers resserrements près des coins convexes (convergence des géodésiques).
    - `raccord='triangulation'`, **raccord par défaut** (`python/Raccord.py`, essai du 2026-11-16) : pendant la fenêtre, les deux dessins
      sont transportés sur une triangulation mobile (trous, clou, bord convexe hors de l'image), les pieds glissent
      sur les arêtes ; cordes seulement dans les triangles qui touchent les trous qui tournent (ou contiennent un
      bigone), coudes des cordes arrondis par des congés (`arrondit`), jonctions avec les arcs conformes tangentes (paire d'arcs),
      mélange direct ailleurs. Fenêtre de 0,5 et phases étalées sur toute la fenêtre (le raccord serré au milieu
      donnait une sensation râpeuse) ; mélanges triangle par triangle (sinon un lacet passait par-dessus un trou). 0 croisement sur les
      deux tresses d'essai ; près des trous qui tournent, une ou deux images en droites et arcs. Détails dans `pistes_film_conforme.md`.

Convention de composition : `calcule_autofn_de_tresse` parcourt la tresse à l'envers, donc
auto(`tresse[:k+1]`) = φ_σ ∘ auto(`tresse[:k]`) avec σ = `tresse[k]`. L'image k+1 s'obtient en tordant les trous i, i+1
de l'image k : le dessin du préfixe suivant est bien l'image du dessin courant par la torsion.

L'ancienne idée d'insertion point par point (`decale`, `dedans_extrm`) est décrite dans `git show f2fdb1c` et
`git show 4b2d4f4` ; le code a été retiré.

## Prochaines étapes

Objectif : le film (b), où σ_i fait tourner continûment les trous i et i+1 l'un autour de l'autre
et entraîne les lacets.

1. ~~**Film image par image.**~~ Fait : `film_de_tresse` → `imgs/film_*.gif`. Les trous gardent leur nombre mais
   bougent horizontalement d'une image à l'autre (l'espacement dépend du nombre de points sur l'axe).
2. ~~**Mouvement continu d'un σ_i.**~~ Fait, puis remplacé par la version algébrique (3).
3. ~~**Faire agir σ_i directement sur l'état.**~~ Fait : `agit` / `reduit` et `film_de_tresse_algebrique`.
   Les essais géométriques précédents (torsion puis fondu linéaire, mélanges) sont dans l'historique git
   (`505776e`, `cba60c8`) : le fondu créait des croisements, il est remplacé par les vagues de bigones.
   Limites : quand il y a beaucoup de points sur l'axe les brins sont très serrés ; la retouche (3) est un mélange
   linéaire (pas de preuve d'absence de croisement, mais les deux dessins sont proches) ; les fusions de plusieurs
   bigones à la suite dans un même lacet sont aussi un mélange linéaire.
4. ~~**Tout en un seul mouvement.**~~ Fait : `film_de_tresse_simultane` (point 9). Reste : lisser les ondulations
   (mélange en coordonnées polaires dans la couronne ?), puis retirer `film_de_tresse_algebrique` si le film
   simultané le remplace.
5. **Ménage.** Fait (code mort retiré : `decale`, `dedans_extrm`, `geometrie_auto_de_tresse`, ancienne torsion par
   ellipses). Reste éventuellement : passer les `assert` en tests pytest.

Sur un nouvel ordinateur : `git pull`, puis `conda env create -f environment.yml` (ou `conda env update -f
environment.yml --prune` si l'environnement existe déjà).

## Conventions

- Code, identifiants, commentaires et messages de commit **en français**. Garder ce style.
- Une tresse = liste d'entiers non nuls : `k` pour σ_k, `-k` pour σ_k⁻¹.
- Un mot de F_n = liste d'entiers non nuls : `i` pour x_i, `-i` pour x_i⁻¹.
- Un automorphisme = liste des images des générateurs (`images[i]` est l'image de x_(i+1)).
- Plusieurs fonctions travaillent par effet de bord (`simplifie`, `conjugaison_locale`) : le docstring le signale.
- **IMPÉRATIF : ne rien écrire de sensible dans ce dépôt, qui est public** (GitHub). Ni l'existence, ni le nom, ni l'adresse du
  serveur personnel de l'utilisateur ; ni identifiant de connexion, chemin d'hébergement, clé, mot de passe ou détail
  d'installation ; ni dans les fichiers, ni dans les docs, ni dans les messages de commit, ni dans les sorties collées. Ces détails
  vont dans des fichiers locaux ignorés par git (`web/deploie.conf`, `web/*.local.md`) ; on dit seulement « un serveur personnel ».
  Aucun élément privé non plus : ni adresse mail (seule l'adresse masquée `noreply` de GitHub est permise, dans les commits),
  ni chemin qui contient un nom d'utilisateur (écrire `~/...` ou un chemin relatif au dépôt), ni nom de machine, ni nom
  d'employeur. L'historique a été réécrit le 2026-11-19 pour en retirer de telles mentions ; vérifier le diff et le message
  avant chaque commit et chaque poussée.
- Python ≥ 3.10 requis (`match`/`case` utilisés).
- OCaml (`ocaml/`) : mêmes noms qu'en Python pour les fonctions et les types traduits (`mot_de_fn`,
  `simplifie`, `conjugaison_locale`, `calcule_autofn_de_tresse`…) ; si la signature diffère (argument, effet de bord),
  le commentaire le dit. Attention : le `agit` du Python est l'action sur l'état d'un méandre, pas l'action d'Artin.
- Deux usages pour chaque script : module (on l'importe, rien ne s'exécute) et exemples (on le lance) : les tests
  (`assert`), les `print` d'essai et la fabrication des images et des films sont sous `if __name__ == "__main__":`
  dans `NouvAutoMorph.py` et `Triangulation.py`. `tresses.py`, sans exemples, garde ses `assert` au niveau du module
  (rapides, ils vérifient la base à chaque import).

## Environnement

Conda (miniforge), environnement `braid-blackboard` défini dans `environment.yml` :

```
conda env create -f environment.yml      # première installation
conda env update -f environment.yml --prune   # après modification
conda activate braid-blackboard
```

Sans activer : `conda run -n braid-blackboard python ...`

## Lancer

Depuis la racine du dépôt (les chemins de sortie comme `./imgs/...` sont relatifs au répertoire courant) :

```
python python/Triangulation.py   # le film actuel : vérifie les assert, écrit imgs/film_triangule_*.mp4
python -c "import sys; sys.path.insert(0, 'python'); import Triangulation as T; T.film_triangule([1, 2, -1], 'imgs/f.mp4')"   # un autre film
python python/NouvAutoMorph.py   # vérifie les assert, écrit imgs/nouv_*.png, imgs/film_*.gif, imgs/film_continu_*.gif (film algébrique) et imgs/film_simultane_*.gif, plus leurs .mp4
python python/Conforme.py        # film conforme : imgs/conforme/film_*.mp4, 800 × 800 (avec vérification)
python python/Arcs.py            # rubans, rubans_gauche, diagramme (ou l'une d'elles en argument) : imgs/<méthode>/film_*.mp4
python python/AutoMorphPNG.py    # écrit imgs/a43m1m12m41nv.png
python -m jupyterlab ipynbks/        # notebooks (pas « jupyter lab » : il prend le premier jupyter-lab.exe du PATH, éventuellement d'un autre environnement)
```
