# Banc d'essai du film des lacets

Document de travail, **non déployé** (ni GitHub Pages, ni serveur personnel : le workflow et `web/deploie.sh` ne copient que des fichiers de `web/`).

Une page, `index.html`, avec les mêmes tresses d'essai que la page publique et un seul film, celui des lacets (mode « conforme »), en 1600 × 1600 :

- lecteur pas à pas : image précédente / suivante, une lettre en arrière / en avant, début, fin, curseur, saut à une image, lecture à 2, 5, 12 ou 25 images par seconde ; le numéro de l'image, la lettre (σᵢ) et le pas dans la lettre sont affichés ;
- lignes de construction (l'axe et la ligne brisée L–A–B–R, estompées pendant le raccord) ;
- tangentes aux arcs, aux points où un lacet coupe une ligne de construction visible (opacité ≥ 15 %) : direction du segment de la polyligne du lacet qui traverse. Pendant le raccord (deux lignes de construction qui s'estompent l'une dans l'autre), les rencontres sur la ligne la plus claire (opacité ≤ 50 %) sont éphémères : un petit cercle gris, sans tangente ; seule la ligne la plus foncée (et les lignes pleines : l'axe, A–B) impose sa tangente.

Le calcul est celui de `web/` (`web/travail.js` charge `web/ardoise_lib.js`, qu'on reconstruit par `web/construit.sh`). Voir la page :

```
python3 -m http.server          # à la racine du dépôt
# puis http://127.0.0.1:8000/etude/lacets/   (#mot dans l'adresse : /etude/lacets/#1 -2 ; ?image=N ouvre sur l'image N)
```

Clavier : ← et → (une image), Maj + ← et Maj + → (une lettre), Début, Fin, espace.
