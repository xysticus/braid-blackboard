# Banc d'essai de la vue 3D

Document de travail, **non déployé**. La demande et les réponses de forme sont dans `etude_idees_pedagogiques.md` (« la 3D »).

```
python3 -m http.server          # à la racine du dépôt
# puis http://127.0.0.1:8000/etude/3d/   (#mot dans l'adresse : /etude/3d/#1 -2)
```

`?azimut=0&site=90&zoom=1.6` (degrés) fixe le point de vue au départ, `&lettre=2` met la deuxième lettre en évidence (captures).

## Les fichiers

- `vue3d.js` : la vue, **sans lien avec la page** (réutilisable par la page publique). `Vue3D.geometrie(mot)` calcule les brins (sans WebGL, testable
  avec Node) ; `Vue3D.cree(canvas, { survol })` rend `{ montre(mot, couleurs), teinte({ fond, verre, accent }), designe(j), oriente(azimut, site, zoom), croisementSous(x, y) }`,
  ou `null` sans WebGL 2.
- `page.js`, `index.html`, `style.css` : la page du banc (saisie, tresses d'exemple, mot cliquable). La liste `EXEMPLES` est la **quatrième** à garder alignée
  avec `web/ardoise.js`, `etude/lacets/etude.js` et `python/Interface.py`. Aucun calcul OCaml.

## Choix (2026-11-26)

WebGL 2 à la main (aucune dépendance) ; banc à part ; **demi-tour en cercle** dans chaque tranche.

- **Repère** : x suit les positions, y monte (la première lettre en haut), z vient vers la personne qui regarde de face. Une position (X, Y) du film des
  méandres devient (x = X, z = Y). **De face**, on voit le diagramme de tresse (σᵢ : le brin qui va de droite à gauche passe devant) ; **de dessus**, le film
  (σᵢ : demi-tour horaire).
- L'angle du demi-tour suit 3t² − 2t³ : le brin est vertical aux deux disques, les tranches se raccordent sans coin. Il y a de ce fait un court
  segment presque droit de part et d'autre de chaque disque.
- Réglages en tête de `vue3d.js` : hauteur d'une tranche 1,5 (écart entre positions : 1), rayon d'un brin 0,11, petit cylindre d'un croisement 0,70.
- Un grand cylindre de verre (plus visible sur ses bords), un disque très pâle entre deux tranches. La mise en évidence montre le petit cylindre du
  croisement et colore les bords des deux disques de sa tranche. Les brins ne changent pas.
- Désignation : le rayon sous le pointeur est coupé avec les petits cylindres, le plus proche l'emporte. À la souris, le survol suffit ; au doigt, un
  toucher sans glisser.
- Interaction : glisser pour tourner (azimut libre, site de −90° à +90°), molette ou deux doigts pour zoomer. Le zoom est centré sur le milieu de la
  tresse, sans déplacement : sur une tresse longue, on ne peut pas aller voir de près le haut ou le bas.

## Vérifié (2026-11-26)

- Node, sur 5 tresses : distance minimale entre brins 1,000 (diamètre 0,22), positions d'arrivée conformes à la permutation, bon brin devant à chaque
  croisement.
- Firefox sans écran (Playwright) : aucune erreur ; survol d'une lettre, désignation des quatre croisements de `1 -2 1 -2` vu de face, rotation à la souris,
  molette ; thèmes clair et sombre ; pas de défilement horizontal à 390 px.
- **Pas essayé** : un vrai téléphone (rotation au doigt, pincement, toucher), la perte du contexte WebGL, un autre navigateur.
