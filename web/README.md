# Ardoise à tresse : la page web

Une page statique (HTML, CSS, JavaScript, canvas). On y écrit un mot de tresse (ou on en choisit un parmi douze) ; elle montre :

1. le mot en notation mathématique, tel qu'il est écrit (MathML) ;
2. le diagramme de tresse classique, de haut en bas ;
3. l'action de la tresse sur le groupe libre F_n (l'image de chaque x_i) ;
4. les méandres en trois modes (diagramme de courbes, représentation conforme, rubans) : d'abord une image fixe, puis le
   film, calculé en tâche de fond par un Web Worker par mode, qui la remplace.

Le calcul est celui de `ocaml/lib/`, compilé en JavaScript par js_of_ocaml (`ocaml/web/ardoise_web.ml` est le pont) ; un
film est une suite de polylignes redessinées sur le canvas, pas une vidéo. Étude et choix : `../etude_page_web.md`.

## Construire et voir

```
web/construit.sh                  # compile la bibliothèque : web/ardoise_lib.js (non suivi par git)
cd web && python3 -m http.server  # puis http://localhost:8000/
```

Il faut un serveur : les Web Workers ne se chargent pas depuis `file://`. `construit.sh` demande js_of_ocaml dans le switch
opam de `ocaml/` (`opam install js_of_ocaml js_of_ocaml-compiler`, déclarés dans `ocaml/dune-project`).

## Publication

`.github/workflows/pages.yml` publie la page sur GitHub Pages à chaque poussée sur `master` qui touche `web/` ou la
bibliothèque OCaml : il installe OCaml 5.4 et js_of_ocaml, lance `construit.sh` (donc `ardoise_lib.js` n'est jamais dans
git) puis dépose `index.html`, `ardoise.css`, `ardoise.js`, `travail.js` et `ardoise_lib.js`. À régler une fois dans le
dépôt GitHub : Settings → Pages → Source : « GitHub Actions ». Les chemins de la page sont relatifs : elle marche sous
`https://<compte>.github.io/braid-blackboard/`.

## Les fichiers

- `index.html`, `ardoise.css` : la page ;
- `ardoise.js` : lecture du mot (`1 -2 3`, `σ1 σ2^-1`, `σ₁σ₂⁻¹`, `s1^3`), MathML, diagramme classique, lecteurs de films ;
- `travail.js` : le Web Worker (image fixe, puis images du film envoyées une à une) ;
- `ardoise_lib.js` : produit par `construit.sh`.

## Limites

8 brins et 40 lettres au plus pour la page ; le film conforme (le plus lent : de 0,4 à 2 s par lettre) est limité à 6 brins
et 14 lettres. Ces limites sont dans `ardoise.js` et `ocaml/web/ardoise_web.ml`.

Sous JavaScript la pile est petite : pas de récursion non terminale sur des listes de la taille d'une polyligne
(`List.concat` dans `lit_mot` l'a fait déborder ; remplacé par `List.concat_map`).
