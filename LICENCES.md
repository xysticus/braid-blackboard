# Licences

Ce dépôt a deux licences, selon la nature des fichiers.

## Le code : licence MIT

Voir [LICENSE](LICENSE). © 2020-2026 xysticus.

Elle couvre le code et les scripts : `python/`, `ocaml/` (bibliothèque, programmes, tests), `web/` (`index.html`, `ardoise.js`, `travail.js`,
`ardoise.css`, scripts `*.sh`), `imgs/schemas/*.py` et `*.js`, `.githooks/`, `.github/`, les notebooks de `ipynbks/` et les fichiers de réglages
(`environment.yml`, `dune-project`…).

`web/ardoise_lib.js` est produit par `web/construit.sh` à partir du code OCaml du dépôt (compilé par js_of_ocaml) : il est sous licence MIT pour la
part qui vient du dépôt. Il embarque aussi le **runtime d'OCaml et celui de js_of_ocaml**, distribués par leurs auteurs sous la licence
LGPL-2.1 ou ultérieure avec l'exception d'édition de liens d'OCaml (`LGPL-2.1-or-later WITH OCaml-LGPL-linking-exception`) : cette exception permet de
distribuer l'ensemble sous d'autres conditions. Leurs textes sont dans les projets d'origine ([OCaml](https://github.com/ocaml/ocaml),
[js_of_ocaml](https://github.com/ocsigen/js_of_ocaml)).

## Les textes, schémas, images et films : licence CC BY 4.0

Voir [LICENSE-CC-BY-4.0.md](LICENSE-CC-BY-4.0.md). © 2020-2026 xysticus.

Elle couvre les textes (`README.md`, `etude_page_web.md`, `plan_ocaml.md`, `pistes_film_conforme.md`, les `README.md` des sous-répertoires de `imgs/`,
`conventions_de_signe.md`, `etude_lignes_de_construction.md`, `CLAUDE.md`, `docs/*.md`), les schémas (`imgs/schemas/*.svg`, `web/schemas/*.svg`, `web/favicon.svg`), les images et aperçus de `imgs/`, et les films produits par les programmes.

Pour citer : « Ardoise à tresse (braid-blackboard), xysticus, https://github.com/xysticus/braid-blackboard, licence CC BY 4.0 (contenus) / MIT (code) ».

## Ce qui n'est pas à moi

- Le livre de référence, *Le calcul des tresses* de Patrick Dehornoy (Calvage & Mounet), et les travaux de J. Birman cités dans le dépôt, sont à leurs auteurs.
- `CodeCogsEqn1.gif` est une image d'équation produite avec le service CodeCogs.
- Les logiciels dont le dépôt dépend (numpy, pycairo, OCaml, dune, cairo2, js_of_ocaml, etc.) gardent leurs propres licences : ils ne sont pas redistribués ici,
  sauf le runtime embarqué dans `web/ardoise_lib.js` (voir plus haut).
