# La page web : fabrication, publication, déploiement

Le détail de `web/` côté fabrication et publication. Sorti de `CLAUDE.md` sans changement de texte. Mode d'emploi :
`web/README.md` ; étude et choix : `etude_page_web.md`.

`web/` : **l'ardoise à tresse en page web** (étude : `etude_page_web.md`, mode d'emploi : `web/README.md`). Page statique
HTML + JavaScript + canvas ; le calcul est celui de `ocaml/lib/` compilé par js_of_ocaml (`ocaml/web/ardoise_web.ml`,
`web/construit.sh` → `web/ardoise_lib.js`, suivi par git : le relancer avant de commiter quand l'OCaml change), un Web Worker par mode de méandre (conforme, diagramme,
rubans, et le film de la triangulation mobile sans le maillage gris ; calculés l'un après l'autre, voir plus bas), films en polylignes redessinées sur le canvas. Voir un résultat : `python3 -m http.server` dans `web/` ;
déploiement : `web/deploie.sh` (rsync vers la cible de `web/deploie.conf`, local et non suivi par git ; règle de cache : `web/README.md`).
Publiée aussi sur GitHub Pages (`https://xysticus.github.io/braid-blackboard/`) par `.github/workflows/pages.yml`, lancé
par chaque push touchant `web/` (21 s ; il copie seulement les fichiers). `ardoise_lib.js` est dans git : le hook `.githooks/pre-push`
(activé par `git config core.hooksPath .githooks`, à refaire après un clone) reconstruit le JS avant chaque push et refuse de
pousser s'il a changé (le commiter, puis repousser). `git publie` (alias local vers `web/publie.sh`) = `git push` puis
`web/deploie.sh` : seul un push met à jour GitHub Pages ; le serveur personnel n'est mis à jour que par `deploie.sh`.
Sous JavaScript, pas de récursion non terminale sur de longues listes (`List.concat`, `List.fold_right`) : la pile est
petite.

**Le film des lacets, détendu et réparti (2026-11-21, tag v1.2).** La vue « lacets » demande au worker le mode de calcul
`conforme_detendu` (`MODE_DE_CALCUL` dans `web/ardoise.js`) : le film conforme détendu pendant le raccord (`ocaml/lib/detente.ml`).
`web/travail.js` répartit ce film (et le mode `conforme` du banc d'essai) sur des workers auxiliaires, autant que de cœurs (8 au
plus) : les lettres leur sont données une à une (`ardoise.film_lettres`), calculées sans détente, et chaque image du raccord revient
en double précision pour être détendue à son tour par un auxiliaire (`ardoise.detend`) ; le worker principal calcule l'image clé de
départ et rend les images dans l'ordre. Mêmes images qu'en un seul worker ; sur 12 cœurs, (σ₁σ₂⁻¹)³ en moins de 24 s et la tresse
chargée en moins de 70 s (au lieu de 80 s et 4 min 45 en un seul worker).

**La triangulation détendue (2026-11-22, tag v1.3).** La vue « triangulation » demande `triangulation_detendu` : le film de la
triangulation (calculé image après image, il dépend de son histoire) dont chaque image, et l'image fixe, est détendue avec l'écart de
ses brins (`ardoise.detend`, 5ᵉ argument), répartie sur les workers auxiliaires. Plus long que la triangulation brute : environ une
minute pour (σ₁σ₂⁻¹)³, plusieurs minutes pour la tresse chargée ; l'image fixe détendue s'affiche dès le début. Les scripts des workers
ne portent pas de numéro de version : après une mise à jour, recharger en navigation privée ou vider le cache (le banc d'essai, lui,
ajoute `?v=` à `travail.js`, qui le transmet à la bibliothèque et à ses auxiliaires).

**Le diagramme de courbes détendu (2026-11-22, tag v1.4).** La vue « diagramme de courbes » demande `diagramme_detendu` : même détente
image par image que la triangulation (`filmDetenduParImages` dans `web/travail.js`), ses points fixes comptés comme des trous ; la
dilatation de départ de la détente laisse les bouts des courbes en place (ceux des arcs sont sur un trou ou un point fixe). Rapide : peu
de brins. Les rubans ne sont pas détendus : la page n'en reçoit que les bords (deux traits par ruban, que la détente écarterait l'un de
l'autre) ; il faudrait détendre les arcs du centre en OCaml, puis reconstruire les rubans.

**L'ordre et la file de calcul des quatre vues (2026-11-22).** Les quatre méandres sont affichés (et calculés) dans l'ordre : lacets,
diagramme de courbes, rubans, triangulation. Les films se calculent **l'un après l'autre** (`lanceCalculs` dans `web/ardoise.js` : un
nouveau worker ne part que quand le précédent a fini ; chaque film occupe déjà tous les cœurs, quatre à la fois se gêneraient). Les
vues qui attendent affichent « en attente » et leur image fixe, calculée tout de suite par un petit worker (`demarreFixe`, message
`fixe` de `web/travail.js`, `imageFixe`). Un nouveau mot abandonne la file (`generationCalculs`).

**Publication GitHub Pages : une panne passagère à connaître (2026-11-22).** Il arrive que le workflow échoue à l'étape de dépôt (`deploy-pages`)
avec « No artifacts named "github-pages" were found for this workflow run » : c'est un incident de GitHub (l'archive du site, qu'on
vient d'envoyer, est introuvable). Rien à corriger dans le dépôt : `gh run rerun <numéro> --failed` relance l'étape et elle réussit
(vu deux fois). Le serveur personnel, lui, n'en dépend pas (`web/deploie.sh`).
