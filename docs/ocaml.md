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
