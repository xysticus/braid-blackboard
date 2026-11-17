# Réécrire les algorithmes en OCaml, ensemble

But : comprendre chaque algorithme du projet en le réécrivant en OCaml, fonction par fonction, avec une explication
de chacune. L'auteur est plus à l'aise en OCaml qu'en Python ; les types et les structures de données d'OCaml doivent
aider à rendre visibles les invariants que le Python laisse implicites. Sous Linux (OCaml sous Windows : installation
pénible).

## Pourquoi OCaml aide ici

- Les objets sont simples et se typent bien. Un pied de lacet est soit un sommet, soit un point à une fraction d'une
  arête : un type somme, là où le Python écrit des tuples `('v', s)` ou `('e', u, v, w)` que rien ne vérifie.
- Les invariants deviennent visibles : une arête est une paire de sommets rangés, un triangle un ensemble de trois
  sommets, un arc une liste de pieds qui commence et finit sur un sommet. Le filtrage force à traiter chaque cas
  (par exemple un pied posé sur l'arête qu'on retourne).
- Réécrire oblige à comprendre chaque étape.

## Ce qui demandera des choix

Le Python n'est pas si fonctionnel qu'il en a l'air :

- beaucoup d'état modifié sur place : positions des sommets, triangles retournés, pieds des courbes (le retournement
  d'arête et la tension changent les courbes en place) ;
- des calculs vectorisés avec numpy, qui cachent des boucles.

Pour chaque structure, on choisira entre une version persistante (plus claire) et des tableaux mutables (plus proches du
Python, plus rapides).

## Le périmètre, du plus fondamental au plus visuel

1. **Tresses et groupe libre** (`python/tresses.py`) : mots de F_n, réduction (`simplifie`), action d'Artin
   (`conjugaison_locale`, `calcule_autofn_de_tresse`). Court et purement algébrique : idéal pour commencer.
2. **Triangulation mobile** (`python/Triangulation.py`, classe `Maillage`) : sommets, triangles, orientation,
   critère de Delaunay, retournement d'arête et mise à jour des courbes (`courbe_apres_flip`). Le cœur.
3. **Transport et tension** (`Film.tend`, `Film.polyligne`) : les trous bougent, les pieds suivent leurs arêtes, les
   brins se tendent avec un écart minimal ; dessin en droites et congés. Fait (`ocaml/lib/film.ml`).
3 bis. **Le méandre** (`python/tresses.py`, partie « état ») : `calcule_arcs`, `intervalles`, `compare_points`,
   `abscisses`, `etat_de_tresse`, `dessin_etat`, `agit` et `reduit` (action de σ_i sur l'état), puis
   `noeuds_de_polyligne` et `Film.disposition`, `Film.__init__` : de quoi construire l'état de départ du film en OCaml.
   Oublié dans la première version de ce plan. Fait (`Film.cree`) ; `dessin_etat` sans ses options d'animation
   (`disque`, `fusions`, `bosses`) ni `agit` son option `detail`, qui ne servent qu'aux anciens films.
4. **Diagramme de courbes et rubans** (`python/Arcs.py`) : le plus simple des films (environ 600 lignes de Python
   en tout), avec la construction du maillage (`python/Raccord.py`, `maillage_du_raccord`) et la découpe d'une
   polyligne par les arêtes (`coupe_arc`).
5. **Dessin et film** : cairo2 pour le dessin, ffmpeg par un tube pour la vidéo.

Laissé de côté au début : le film conforme (`python/Conforme.py`, cartes de Schwarz–Christoffel : surtout de
l'analyse numérique, qui éloigne des idées centrales), et les anciens films de `python/NouvAutoMorph.py`.

## Comment vérifier

À chaque étape, comparer les sorties OCaml à celles du Python : mêmes mots pour l'algèbre, mêmes pieds après un
retournement, même image à la fin (les deux tresses d'essai : σ₄σ₃σ₁⁻¹σ₁⁻¹σ₂σ₄⁻¹σ₁ et la tresse chargée
σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂).

## Outils

dune pour construire, cairo2 pour dessiner, des tests au fil de l'eau (tests en expect, ou alcotest). Vérifier au
début de la séance qu'OCaml (opam), dune et cairo2 sont installés sous Linux.
