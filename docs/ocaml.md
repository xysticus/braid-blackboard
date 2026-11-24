# OCaml : la réécriture, l'état des étapes et l'installation

Le détail de `ocaml/` (étapes 1 à 8 faites, tests, installation sous WSL et sous Fedora). Sorti de `CLAUDE.md` sans
changement de texte (la puce est devenue un paragraphe). Plan : `plan_ocaml.md` ; explications du code : `ocaml/explications.md`.

`ocaml/` : réécriture en OCaml (`plan_ocaml.md`), sous WSL. Étape 1 faite : `lib/tresses.ml` (lettres, mots
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
Lignes de construction (2026-11-20, pour la page web) : `Conforme.aretes` (l'axe et L–A, A–B, B–R, L–B, A–R, comparée au Python
par `dune test`) et `Film_conforme.construction` (chaque image porte ses segments avec leur opacité, fondus du raccord compris) ;
le dessin Cairo et les MP4 ne les tracent pas.
Détente du raccord (2026-11-21) : `lib/detente.ml`, traduction de `detend` de `etude/lacets/essai_lissage.py` (rééchantillonnage,
tension, répulsion entre brins et trous, pas borné, voisins par une grille au lieu de paquets de distances : même ensemble de paires).
`Film_conforme.film ~detente` l'applique pendant le raccord avec l'intensité 4 poids (1 − poids) ; `~premiere ~lettres` ne calcule
qu'une partie du film (chaque lettre ne dépend que de son état de départ : la page en répartit les lettres sur plusieurs workers).
`test/test_detente.ml` : mêmes points que le Python à 1e-6 près sur deux images (`reference_detente.json`, écrit par
`genere_reference_detente.py`), et le film détendu de (σ₁σ₂⁻¹)³ sans anomalie. Le film non détendu et ses 83 tests sont inchangés.
Détente sans faille (2026-11-22, tag v1.3), en OCaml comme en Python : dilatation radiale de départ autour des trous (le dessin commence
hors de leur zone ; une boucle plus petite que le pas, rééchantillonnée, pouvait ne plus contenir son trou) ; barrière des trous et
anti-croisement entre brins par **retour à la position précédente** (un segment qui s'approcherait trop d'un trou, ou deux segments qui
se croiseraient, reprennent leur position d'avant : un dessin juste ne peut pas devenir faux ; pousser le segment le pouvait) ; retouche
des points au lieu du rééchantillonnage (découpe des segments longs par des points pris sur eux, fusion seulement si la corde ne
s'approche pas d'un trou, retouche refaite sans fusion si une corde a coupé un brin) ; voisins par une grille à listes chaînées (le tri
est lent sous JS). Réglages de la triangulation (`ardoise_web.ml`, `detend`) : écart du film, rayon des trous égal à l'écart,
répulsion 4, 150 itérations. Vérifié sur les deux tresses d'essai, triangulation et lacets conformes détendus : 0 croisement, 0 trou
traversé (nombres d'enroulement de chaque lacet autour de chaque trou, avant et après), 0 image douteuse.
Vitesse de la détente (2026-11-22) : les garde-fous coûtaient surtout l'anti-croisement, qui testait toutes les paires de points proches à
chaque itération. Un point ne bougeant que de `pas_max` par itération, deux segments ne peuvent se croiser avant la prochaine recherche
(toutes les 8 itérations) que s'ils sont à moins de 16 `pas_max` + 1 l'un de l'autre : on dresse cette liste de **segments candidats**,
par une grille sur les milieux des segments (chaque paire n'y est vue qu'une fois, sans table de hachage), et l'anti-croisement ne teste
qu'eux ; la répulsion entre brins n'a plus que les paires à moins de `ecart + 16 pas_max`. Mêmes décisions qu'avant (le test contre le
Python, qui teste toutes les paires, passe à 1e-6) ; image 769 de la triangulation de la chargée : 24 s → 3,6 s ; image 264 des lacets :
3,9 s → 1,5 s. Pas de `Float.hypot` ni de `**` dans les boucles chaudes sous js_of_ocaml (lents), pas d'allocation de listes par paire.
La dilatation de départ laisse en place les bouts des courbes (2026-11-22, v1.4) : le diagramme de courbes est détendu lui aussi,
ses arcs finissant sur un trou ou un point fixe ; vérifié (0 croisement, 0 trou ni point fixe traversé : l'arc d'origine suivi de
l'arc détendu à l'envers n'entoure aucun obstacle).
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

**Newton de l'antécédent d'un point intérieur (2026-11-25).** `Conforme.antecedent` (l'antécédent du clou dans la carte du bas) pouvait
lever `Pas_de_convergence` alors que Newton oscillait à moins d'un pixel du but : sa précision est limitée quand le point est loin des sommets (0,08 px
pour le clou dans l'état de `4 3 -4 2 1`, lettre σ₁ à l'image 15). Il rend maintenant le meilleur point rencontré si l'erreur est sous 0,5 px, et
n'abandonne que sinon. Trouvé par le méandre témoin du banc d'essai (le mot `4 3 -4 2 1 -2 -2`, que les trous écrivent pour `4 3 -1 -1 2 -4 1`) ;
aucun changement quand Newton converge (les tests contre le Python passent).
