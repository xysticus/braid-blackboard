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
