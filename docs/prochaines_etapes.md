# Prochaines étapes

Objectifs et état d'avancement du film des méandres. Sorti de `CLAUDE.md` sans changement de texte.

Objectif : le film (b), où σ_i fait tourner continûment les trous i et i+1 l'un autour de l'autre
et entraîne les lacets.

1. ~~**Film image par image.**~~ Fait : `film_de_tresse` → `imgs/film_*.gif`. Les trous gardent leur nombre mais
   bougent horizontalement d'une image à l'autre (l'espacement dépend du nombre de points sur l'axe).
2. ~~**Mouvement continu d'un σ_i.**~~ Fait, puis remplacé par la version algébrique (3).
3. ~~**Faire agir σ_i directement sur l'état.**~~ Fait : `agit` / `reduit` et `film_de_tresse_algebrique`.
   Les essais géométriques précédents (torsion puis fondu linéaire, mélanges) sont dans l'historique git
   (`505776e`, `cba60c8`) : le fondu créait des croisements, il est remplacé par les vagues de bigones.
   Limites : quand il y a beaucoup de points sur l'axe les brins sont très serrés ; la retouche (3) est un mélange
   linéaire (pas de preuve d'absence de croisement, mais les deux dessins sont proches) ; les fusions de plusieurs
   bigones à la suite dans un même lacet sont aussi un mélange linéaire.
4. ~~**Tout en un seul mouvement.**~~ Fait : `film_de_tresse_simultane` (point 9). Reste : lisser les ondulations
   (mélange en coordonnées polaires dans la couronne ?), puis retirer `film_de_tresse_algebrique` si le film
   simultané le remplace.
5. **Ménage.** Fait (code mort retiré : `decale`, `dedans_extrm`, `geometrie_auto_de_tresse`, ancienne torsion par
   ellipses). Reste éventuellement : passer les `assert` en tests pytest.
6. ~~**Film des lacets sans défauts au raccord.**~~ Fait (2026-11-21, tag v1.2) : le film conforme détendu pendant le raccord
   (`ocaml/lib/detente.ml`, `pistes_film_conforme.md`), réparti par lettres sur plusieurs workers dans la page.
7. **La rétractation, à proposer dans la page publique (idée de l'utilisateur, version simple dans le banc, 2026-11-24).** Le méandre de
   l'image n reste en place ; on tire sur les lacets l'un après l'autre, en effaçant leur bout jusqu'à leur arrivée sur l'axe, le trou
   étant le centre du demi-cercle qui referme le lacet (`etude/lacets/README.md`, `filmRetraction` dans `web/travail.js`). Pour la
   proposer dans la page, il faut **générer le mot associé** : quand un trou bouge seul, il passe devant et derrière les autres, immobiles ;
   ces passages donnent des lettres, et le mot obtenu doit être équivalent au mot d'origine. L'égalité des mots est difficile chez les
   tresses (formes normales : *Le calcul des tresses*) ; on compare par l'action sur F_n, qui est fidèle : avec le mot généré, on **redessine le méandre
   par la méthode conforme, à côté, et on vérifie à la fin que les deux méandres sont égaux** (facile à implémenter, et pédagogique). Points à régler :
   le signe d'une lettre (quel trou passe devant à l'échange d'ordre selon l'axe), et la configuration de départ de la rétractation (trous aux
   bouchons, pas alignés) qui demande un chemin de référence jusqu'à la ligne droite standard.
   **Fait dans le banc (2026-11-24)** : le mot s'écrit sous le film, à mesure, et ses méandres sont comparés à ceux du mot d'origine (égaux sur
   13 mots essayés) ; les trous sont bien alignés et dans l'ordre au départ. **Fait dans le banc (2026-11-25), idée de l'utilisateur** : un *méandre témoin* à côté, dessiné par
   la méthode conforme avec le mot obtenu, **avec le même timing** : la lettre écrite à l'image k du film de rétractation est jouée dans le film
   conforme à ce moment-là.
   **Fait dans le banc (2026-11-25) : des curseurs pour faire coulisser soi-même les trous** le long de leurs lacets (un curseur par lacet, éventuellement
   crantés sur les rencontres de l'axe) ; le mot s'écrit en direct dans l'ordre des gestes et le méandre témoin suit. Le tirage au hasard du banc
   (`filmRetraction`, mode `rencontres`) en est la version automatique.
