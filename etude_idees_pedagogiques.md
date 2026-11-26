# Idées pédagogiques (étude : l'activité 2 et la vue 3D sont faites dans des bancs d'essai, le reste n'est pas commencé)

Idées de l'utilisateur (2026-11-25), notées telles quelles pour y revenir. Elles s'appuient sur ce que la page et le banc d'essai savent déjà faire (diagramme
de tresse, méandres, mot écrit par le mouvement des trous, curseurs : voir `etude/lacets/README.md`). **L'activité 2 est faite dans le banc d'essai** (2026-11-26, tag `banc-libre`, option « mouvement libre » : voir la section ci-dessous) ; les autres ne sont pas commencées.

## Activités à proposer

1. **Écrire le mot que représente un diagramme de tresse.** On montre un diagramme (croisements de brins), la personne écrit le mot en σᵢ et σᵢ⁻¹ ; la page vérifie.
2. **Écrire le mot qui découle d'un mouvement libre des trous.** La personne déplace les trous à sa guise (les curseurs du banc en sont une première version : un trou
   qui coulisse dans son lacet) ; le mot s'écrit des lettres qu'ils engendrent (un trou qui passe devant ou derrière un autre) ; on peut demander à la personne de l'écrire elle-même avant
   de comparer. **« Mouvement libre » = sans contrainte de lacets** : les trous se déplacent comme on veut, et **deux trous qui échangent leur position par un générateur
   se tournent autour par des arcs de cercle** (le demi-tour de σᵢ, celui du film conforme). Reste à définir la manipulation (glisser un trou vers son voisin pour les faire tourner ?
   sens horaire ou anti-horaire selon le geste, signe de la lettre).
3. **Réduire un mot.** Simplifier un mot de tresse (σσ⁻¹, commutations σᵢσⱼ = σⱼσᵢ pour |i − j| ≥ 2, relation σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁) ; la page peut vérifier chaque étape par l'action sur F_n
   (deux mots égaux ont les mêmes lacets : c'est le contrôle « les méandres sont égaux » du banc).
4. **Relier des ensembles : d'un côté des mots, de l'autre les méandres associés.** Un jeu d'appariement : plusieurs mots (dont des mots différents qui donnent la même tresse) et
   plusieurs méandres, à relier.

## Une nouvelle représentation : la 3D

Les générateurs engendrent la **forme 3D de la tresse par tranches : une tranche pour chaque générateur** (chaque lettre du mot ajoute sa tranche, comme les images clés du film
ajoutent une lettre à la fois). Précisions de l'utilisateur (2026-11-25) :

- **Les brins évoluent dans un tube, de haut en bas.**
- **Les tranches se superposent en faisant correspondre les brins** (la sortie d'une tranche est l'entrée de la suivante). Elles sont **marquées discrètement**, parce
  qu'elles correspondent aux générateurs.
- **Interaction : tourner la vue, et éventuellement zoomer et dézoomer.** Rien d'autre.
- **100 % côté client**, comme le reste de la page. Cible : **Firefox d'abord**, le bureau, et les téléphones si possible.
- **Technique : à choisir** (l'utilisateur ne sait pas). Oui, une page web fait de la 3D côté client avec **WebGL** (Firefox le gère, WebGL 2 compris, bureau et mobile). Pistes : une
  bibliothèque comme three.js copiée dans `web/` (comme `exports.js`, pas de CDN) ; WebGL à la main (quelques centaines de lignes : tubes, un éclairage simple, une caméra orbitale) ;
  ou une projection en perspective sur un canvas 2D (sans dépendance, moins joli, suffisant pour des tubes ?). À trancher quand on s'y met, en pesant le poids du fichier à
  déployer et le comportement sur téléphone.
- **Réponses de l'utilisateur (2026-11-25) aux questions de forme :**
  - **Le seul cylindre vertical « discret » est celui qui contient toute la tresse.** Les brins ne sont pas en hélice autour de lui.
  - **Les brins peuvent être vus en hélice, mais autour de chaque générateur** : chaque tranche est un secteur cylindrique, où deux brins se tournent autour l'un de l'autre.
  - **Un croisement, c'est juste deux brins qui font chacun leur route dans l'espace 3D pour atteindre le prochain disque séparateur entre deux générateurs.** Ce sont ces
    disques qui séparent les tranches (les marques discrètes).
  - **Les brins gardent leur couleur de haut en bas** (les couleurs des lacets de la page).
  - **Mise en évidence réciproque** entre le secteur cylindrique d'un croisement et la lettre du mot : survoler ou toucher l'un met l'autre en évidence, dans les deux sens.
- Reste à choisir : la technique (voir plus haut), le tracé exact des deux routes d'un croisement (arcs de cercle autour de l'axe du secteur, comme le demi-tour du film
  conforme ?), l'espacement des disques, et la façon de tourner la vue au doigt sur téléphone.

## État de la 3D (2026-11-26, banc d'essai)

Première version dans `etude/3d/` (détail, choix et vérifications : `etude/3d/README.md`), pas encore dans la page publique. Choisis : **WebGL 2 à la main**,
banc à part, **demi-tour en cercle** dans chaque tranche ; l'écart entre disques et la rotation au doigt sont des premiers réglages, **pas encore essayés sur téléphone**.

## Liens avec l'existant

- La vérification par l'action sur F_n (`ardoise.analyse`, comparaison des mots de F_n) sert aux activités 2, 3 et 4.
- Le mot écrit par le mouvement des trous (`filmRetraction`, `demarreCurseurs` dans `web/travail.js`) sert à l'activité 2.
- Le diagramme de tresse et les méandres sont déjà dessinés par la page ; la 3D serait une quatrième représentation.

## État de l'activité 2, le mouvement libre (2026-11-26, banc d'essai, tag `banc-libre`)

Faite dans le banc (`etude/lacets/`, option « mouvement libre » ou `?libre`), pas encore dans la page publique :
- 2 à 6 trous alignés sur l'axe, attrapés au pointeur (souris ou doigt) et déplacés **sans contrainte de lacets** ; **aucune trace** ; lâché, un trou **retombe (ou remonte) sur l'axe**,
  puis **tous les trous se répartissent à nouveau équitablement** sur l'axe (même ordre : aucune lettre).
- Un trou qui passe devant ou derrière un voisin écrit une lettre : σᵢ s'il passe au-dessus en allant vers la droite, σᵢ⁻¹ au-dessous ; une lettre qui défait la précédente l'efface. Libellé : « mot écrit par le mouvement des trous ».
- Le **méandre témoin évolue continûment** (l'image u du film conforme de la lettre en cours, la lettre s'écrit à u = 1) et il est **précalculé** (groupe de workers, 24 images par lettre, cache de 40 films).
- Essayé par l'utilisateur : « ça marche bien et c'est agréable à utiliser ».
- **Pas encore fait :** le geste où deux trous échangent leur position en se tournant autour par des arcs de cercle (aujourd'hui le trou suit le pointeur) ; le tour à la main sur téléphone ; l'enchaînement avec les autres activités.
- **Pour la page publique :** revoir le poids du précalcul (workers, mémoire des images sur téléphone), le temps des mots longs (une lettre prend plusieurs secondes), autoriser `film_lettres_rapide` et `sans_limites` (banc seulement aujourd'hui).
