# Banc d'essai du film des lacets

Document de travail, **non déployé** (ni GitHub Pages, ni serveur personnel : le workflow et `web/deploie.sh` ne copient que des fichiers de `web/`).

Une page, `index.html`, avec les mêmes tresses d'essai que la page publique et un seul film, celui des lacets (mode « conforme »), en 1600 × 1600 :

- lecteur pas à pas : image précédente / suivante, une lettre en arrière / en avant, début, fin, curseur, saut à une image, lecture à 2, 5, 12 ou 25 images par seconde ; le numéro de l'image, la lettre (σᵢ) et le pas dans la lettre sont affichés ;
- lignes de construction (l'axe et la ligne brisée L–A–B–R, estompées pendant le raccord) ;
- tangentes aux arcs, aux points où un lacet coupe une ligne de construction (opacité > 0) : direction du segment de la polyligne du lacet qui traverse. Pendant le raccord (deux lignes de construction qui s'estompent l'une dans l'autre), les rencontres sur la ligne la plus claire (opacité ≤ 50 %) sont éphémères : un point fantôme (petit cercle gris clair, sans tangente, case « points fantômes » : il n'impose ni sa tangente ni sa position, l'arc l'induit) ; seule la ligne la plus foncée (et les lignes pleines : l'axe, A–B) impose sa tangente.

Le calcul est celui de `web/` (`web/travail.js` charge `web/ardoise_lib.js`, qu'on reconstruit par `web/construit.sh`). Voir la page :

```
python3 -m http.server          # à la racine du dépôt
# puis http://127.0.0.1:8000/etude/lacets/   (#mot dans l'adresse : /etude/lacets/#1 -2 ; ?image=N ouvre sur l'image N)
```

Clavier : ← et → (une image), Maj + ← et Maj + → (une lettre), Début, Fin, espace.

Case « maillage » : les arêtes de la triangulation du raccord (trous, clou, bord convexe hors de l'image), pendant le raccord seulement ; hors du raccord le dessin est conforme et il n'y a pas de maillage.

Case « arcs libres » : recalcule le film avec le mode `conforme_libre` (`Raccord.lignes ~sans_fantomes:true`) : pendant le raccord, les cordes ne passent plus par les pieds posés sur les arêtes de la plus claire des deux lignes de construction ; l'arc est induit par ses extrémités et ses tangentes ; un pied sur la ligne foncée impose sa position et sa tangente perpendiculaire à la ligne, sauf sur A–B, où seule la position est imposée (une tangente imposée y faisait des S quand la courbe arrive en oblique ; ne plus imposer non plus la position ajoutait des images douteuses). Sur la tresse chargée, le film sans la case reste préférable. Sans la case : le film de la page publique.

Case « sans maillage » (essai) : mode `conforme_sans_maillage` (`Raccord.lignes ~sans_maillage:true`) : pendant le raccord, les pieds posés sur les arêtes du maillage qui ne portent pas une ligne de construction sont retirés ; les repères restants (départ, arrivée, pieds sur A–B et sur la ligne foncée) sont reliés par des paires d'arcs, sans que rien ne les retienne : des arcs immenses sont possibles. Pour voir ce que la triangulation impose aux lacets.

Case « satellites » (essai) : mode `conforme_satellites` (`Raccord.raccord ~satellites:8`) : 8 sommets de plus, sur un cercle de rayon 30 % de la plus petite distance entre trous, autour de chacun des deux trous qui tournent ; ils les suivent. Le maillage a beaucoup d'arêtes courtes autour d'eux (case « maillage » pour les voir). Les mots relus et les croisements sont vérifiés comme pour les autres modes.

Case « pur » (essai, mode `conforme_pur`, `Conforme.dessin_pur`) : **la projection conforme seule**, sans maillage, sans raccord, sans détente.
À chaque image, les pieds des lacets (points rouges) sont posés sur la ligne brisée de construction : le départ sur L–A–B–R jusqu'à la
verticale (poids ½ du raccord), l'arrivée sur L–B–A–R ensuite (les lignes de construction passent d'une à l'autre d'un coup). Deux pieds
consécutifs sont reliés par un arc de cercle de la bonne courbure (flèche = aplatissement × demi-corde, comme la demi-ellipse des images
clés), du côté du haut ou du bas selon la parité, **sans souci des tangentes** ; les deux bouts descendent au clou en ligne droite. Les
croisements sont permis : l'essai sert à voir les erreurs de la projection seule (le compte des images douteuses s'affiche à la fin du
calcul ; `?pur` coche la case au départ). **Les deux phases sont confondues** : à chaque image, on dessine les cinq lignes de construction (L–A–B–R et L–B–A–R, à pleine opacité), le dessin du départ (trait plein, pieds rouges) et celui de l'arrivée (pointillés, pieds orange), même là où l'un n'existe pas encore ou plus (ligne brisée qui se recoupe). Le compte des images douteuses ne porte alors que sur le dessin du départ. Case « marqueurs » : le **trajet de chaque point** du départ à l'arrivée (disque = départ, cercle = arrivée, trait entre les deux), selon son rôle dans l'action de σ (`Tresses.agit_origines`, `Tresses.bigones`, `Conforme.trajets`) : rouge, il glisse avec son trou (hors du bloc qui tourne) ; orange, il tourne avec le bloc ; vert, il naît sur un arc qui entre dans le bloc ou en sort (il part de son point père) ; noir, il s'annule avec un voisin (bigone : les deux vont au milieu de leurs départs). Les points rouges et orange du plein et du pointillé ne sont alors plus tracés. Case « transformation » : **le lacet qui se transforme** de l'état k (plein) à l'état k+1 (pointillé), `Conforme.dessin_morph`. Chaque point de l'état non réduit après σ est à (1 − w) de son départ et w de son arrivée, w étant le temps de la lettre (0 : image clé de départ, 1 : image clé suivante) ; deux points consécutifs sont reliés par un arc de cercle dont le côté (à gauche ou à droite de la marche) passe de celui de l'état k à celui de l'état k+1 ; les points qui s'annulent en queue (ou en tête) de lacet se rétractent le long du lacet jusqu'à leur voisin survivant ; un point né qui s'annule avec un point ancien se fond dans lui ; sur la seconde moitié, le chemin qui passe par des points qui s'annulent est fondu, à égale longueur, dans l'arc direct entre leurs deux voisins survivants. Le trait épais en couleur est la transformation ; le plein et le pointillé sont estompés. À w = 0 on retrouve le plein, à w = 1 le pointillé (vérifié par la distance entre les deux courbes).
Avec « pur », les tangentes, les points et les fantômes sont décochés au départ (on peut les recocher) et les cases qui n'y jouent pas (maillage, sans maillage, satellites, projection, arcs libres, détendu, régions) sont grisées ; sans « pur », ce sont plein, pointillé, transformation et marqueurs. Le banc affiche `t` (0 : état k, 1 : état k+1) à côté du numéro de l'image. Avec « détendu » (coché par défaut), la transformation est détendue comme le film de la page (`Detente.detend`, intensité 4 t (1 − t) : nulle aux images clés) : les arcs s'écartent des trous et des autres lacets ; le calcul est réparti sur plusieurs workers (`filmPurDetenduParImages` dans `web/travail.js` : `2 3 1 4 3 2` en 17 s). Les images clés (début et fin de lettre) sont celles des arcs de cercle, non les images conformes.

## Essai : le raccord par régions, sans maillage (Python)

`essai_regions.py` (depuis la racine du dépôt) : à la verticale, le plan est coupé en quatre régions (le haut, le bas avec le
clou, les deux triangles L–Bas–T et R–T–Bas) et chaque morceau de lacet y est l'image d'un demi-cercle par la représentation
conforme de la région. `python etude/lacets/essai_regions.py "1 -2 1 -2" 2` écrit la comparaison avec le maillage à l'image du
milieu de la lettre 2 ; `python etude/lacets/essai_regions.py film "1 -2 1 -2" sortie.mp4 [fenetre=0.5] [rampe=0.25] [construction]`
écrit le film du raccord par régions (images dans `imgs/`, ignoré par git). Sur la tresse chargée, 5 images sur 432 ont des
croisements, toutes dans les rampes de mélange aux deux bouts de la fenêtre.

Dans la page du banc, la case « régions (précalculé) » joue ces images à la place du calcul OCaml, pour les mots dont le fichier
`regions/<mot>.json` existe (les lettres séparées par `_` : `1_-2_1_-2.json`). Elle est grisée sinon. Pour en fabriquer un :
`python etude/lacets/essai_regions.py exporte "1 -2 1 -2" etude/lacets/regions/1_-2_1_-2.json` (une minute pour 4 lettres, quatre
pour la tresse chargée, dont le fichier fait 11 Mo : il est ignoré par git). Ces films n'ont pas de journal ni de plans w : le
panneau « La projection » est masqué.

## Essai : le film détendu pendant le raccord (Python)

`essai_lissage.py` (depuis la racine du dépôt) : on garde le film conforme actuel, topologiquement juste, et on le détend
pendant la fenêtre du raccord par un court flot de courbure contraint. Chaque brin est rééchantillonné ; la tension (chaque
point va vers le milieu de ses voisins) arrondit les coins et efface les zigzags ; une répulsion entre brins (écart 6 px) et
entre brins et trous (12 px) garde les écarts et empêche les croisements ; elle s'éteint près du clou. L'intensité vaut
4 poids (1 − poids) : nulle aux bords de la fenêtre (images clés intactes, film continu), maximale au milieu.
`python etude/lacets/essai_lissage.py "1 -2 1 -2 1 -2" 264` compare une image ; `python etude/lacets/essai_lissage.py film
"1 -2 1 -2 1 -2"` écrit le film vérifié (`imgs/essai_lissage_film_*.mp4`). Réglages en arguments : `PAS=4 ITERATIONS=400
ECART=6 RAYON_TROU=12 …`. La détente est portée en OCaml (`ocaml/lib/detente.ml`, les mêmes points à 1e-6 près) : la case
« détendu » du banc la fait calculer par la page (mode `conforme_detendu`), pour n'importe quel mot.

## Le film de la triangulation « à l'envers »

Option « triangulation à l'envers » du sélecteur « film » (ou `?envers`) : on part du méandre complet (l'image n), on tire sur les brins
(les trous reculent d'une lettre, les brins se tendent sur le maillage) jusqu'aux brins du début, puis on **joue ce film à l'envers** : les
lacets font des chemins qui contournent des trous qui n'existent pas encore. OCaml (`triangulation_envers` dans `ocaml/web/ardoise_web.ml`)
calcule le film du mot suivi de son inverse (le méandre se construit, puis se défait ; `Film.cree` a besoin du mot entier) et ne rend que
le retour ; `filmEnvers` dans `web/travail.js` le renverse. La limite (6 brins, 14 lettres) porte sur le mot, pas sur le mot doublé. Calcul
très rapide : pas de détente (1 061 images pour la tresse chargée en 2,5 s).

## Cordes sur chevilles : la rétractation sans maillage

Option « cordes sur chevilles (rétractation) » du sélecteur « film » (ou `?cordes`) : même départ (le méandre complet du retour de « faire et
défaire »), mais les brins ne sont plus posés sur un maillage. Les lacets sont des **cordes** et les trous des **chevilles** : à chaque image
les trous reculent comme dans le film maillé, poussent les cordes (garde radiale de `Detente`), et la tension seule les rétracte le long
de leur propre chemin (`Detente.detend`, chaque image part de la précédente : calcul séquentiel, `filmCordes` dans `web/travail.js`, 11 s pour
459 images avec 30 itérations par image ; 36 s avec les 150 de la détente de la page, qui ne sont pas nécessaires ici). Les voisins ne remplissent pas expressément la place laissée : tous les lacets se tendent et laissent un vide. Mesuré sur `1 -2 1 -2` :
mêmes nombres d'enroulement que le film maillé sur 115 images échantillonnées sur 115 (une sur quatre), aucune erreur de détente. On joue le tout à l'envers.

Variante « cordes, tension locale » (`?cordeslocales`, réglage `portee` de `Detente`, exposé par `ardoise.detend_local`) : la tension
n'agit qu'à moins de 100 px d'un trou (elle s'éteint jusqu'à 200 px) ; le lacet **se referme derrière le trou** et garde sa forme ailleurs :
du vide seulement le long du passage des trous. Mêmes nombres d'enroulement que le film maillé (115 images sur 115), 40 s.

## Le film de la triangulation

Le sélecteur « film » choisit entre les lacets conformes (vue 2 de la page), la triangulation (vue 3, `?triangulation`) et le
diagramme de courbes (vue 1, `?diagramme`, points fixes en gris). « détendu »
s'applique aux trois (pour la triangulation et le diagramme, sur toutes les images, avec l'écart de leurs brins) ; les cases qui ne concernent que les
lacets conformes (fantômes, maillage, sans maillage, satellites, projection, arcs libres, régions) sont grisées. Le banc crée son
worker avec `travail.js?v=<heure>` : il joue toujours les scripts du disque, pas ceux du cache du navigateur.
