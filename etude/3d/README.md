# Banc d'essai de la vue 3D

Document de travail, **non déployé**. La demande et les réponses de forme sont dans `etude_idees_pedagogiques.md` (« la 3D »).

```
python3 -m http.server          # à la racine du dépôt
# puis http://127.0.0.1:8000/etude/3d/   (#mot dans l'adresse : /etude/3d/#1 -2)
```

`?azimut=0&site=90&zoom=1.6` (degrés) fixe le point de vue au départ, `&lettre=2` met la deuxième lettre en évidence (captures).

## Le disque qui descend (2026-11-26)

Un disque horizontal se place à toute hauteur de la tresse (curseur, ou ▶ à 25 images par seconde) et porte le **méandre à cette hauteur** : les brins le
percent aux trous, chaque lacet entoure le brin de sa couleur, et la descente est le film. Sous le disque, les brins sont pleins ; au-dessus, en fantômes.
La lettre où se trouve le disque est soulignée. « Vue de dessus » montre le film. La case décochée rend la vue d'avant. `?image=72` place le disque au départ.

- **Les images** sont celles du film conforme détendu de la page (`web/travail.js`, mode `conforme_detendu`, 48 par lettre) : le banc calcule donc
  maintenant en OCaml. Limites de ce film : 6 brins et 14 lettres ; au-delà, la tresse s'affiche sans disque. Le disque avance dans une lettre quand
  celle-ci est entièrement calculée.
- **La hauteur** : l'image f est à f / 48 tranches sous le haut. Le temps du film dans une lettre, 3t² − 2t³, est la loi de l'angle du demi-tour des brins, et le
  sens est le même (σᵢ : horaire vu de dessus) : rien à ajuster.
- **Le plan** (`disque.js`) : dans le film, les trous sont irrégulièrement espacés (48 à 262 px sur les mots mesurés) et le demi-tour est aplati. Chaque image
  est déformée par x ↦ x' croissante à chaque hauteur et y ↦ z croissante, indépendante de x : un homéomorphisme du plan, donc ni croisement créé ni trou
  sauté, choisi pour que les trous tombent sur les brins, et continu d'une image à l'autre. La 3D de la tresse n'a pas changé. En profondeur, la loi est concave
  (les petits lacets restent visibles autour des brins) ; vers le clou, x ne dépend plus des trous (le clou reste au milieu, devant). Le cylindre est élargi
  pour que le méandre y tienne. Les proportions du dessin diffèrent donc de celles du film 2D.

## Les fichiers

- `vue3d.js` : la vue, **sans lien avec la page** (réutilisable par la page publique). `Vue3D.geometrie(mot)` calcule les brins (sans WebGL, testable
  avec Node) ; `Vue3D.cree(canvas, { survol })` rend `{ montre(mot, couleurs), teinte({ fond, verre, accent }), designe(j), oriente(azimut, site, zoom), croisementSous(x, y) }`,
  ou `null` sans WebGL 2.
- `disque.js` : le méandre du disque, d'après une image du film conforme (sans WebGL, testable avec Node) : `Disque.meandre(mot, f, image, clé0, clé1)`.
  Dans la vue : `disqueMeandre({ tranche, lacets, trous, clou })`.
- `page.js`, `index.html`, `style.css` : la page du banc (saisie, tresses d'exemple, mot cliquable). La liste `EXEMPLES` est la **quatrième** à garder alignée
  avec `web/ardoise.js`, `etude/lacets/etude.js` et `python/Interface.py`. La page emploie `web/travail.js` pour le film du disque ; la vue, aucun calcul OCaml.

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
- 2026-11-26, avant le disque : la 3D a été essayée sur téléphone par l'utilisateur (« c'est ok »).

## Vérifié pour le disque (2026-11-26)

- Node, 6 mots de 2 à 6 brins, toutes les images : trous à 0,001 au plus des brins (rayon d'un brin : 0,11) ; une image sur quatre : nombres d'enroulement de
  chaque lacet autour de chaque trou identiques avant et après la déformation. Sur 3 mots, une image sur quatre : chaque lacet entoure le brin de sa couleur, et lui seul.
- Firefox sans écran, `1 -2 1 -2` et `4 3 -1 -1 2 -4 1` : captures du canvas de côté et de dessus ; lecture, pause, arrêt en bas, case décochée, mot hors
  limites, mot changé pendant le calcul ; mise en page à 390 px. (`--screenshot` laisse le canvas WebGL vide : la page de test lit `toDataURL` dans une
  `requestAnimationFrame` et envoie l'image au serveur de test.)
- Sur téléphone, essai de l'utilisateur : « c'est ok ». La durée du calcul et la mémoire n'ont pas été mesurées.
