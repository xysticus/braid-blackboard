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
