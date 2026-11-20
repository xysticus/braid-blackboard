# La page web : fabrication, publication, déploiement

Le détail de `web/` côté fabrication et publication. Sorti de `CLAUDE.md` sans changement de texte. Mode d'emploi :
`web/README.md` ; étude et choix : `etude_page_web.md`.

`web/` : **l'ardoise à tresse en page web** (étude : `etude_page_web.md`, mode d'emploi : `web/README.md`). Page statique
HTML + JavaScript + canvas ; le calcul est celui de `ocaml/lib/` compilé par js_of_ocaml (`ocaml/web/ardoise_web.ml`,
`web/construit.sh` → `web/ardoise_lib.js`, suivi par git : le relancer avant de commiter quand l'OCaml change), un Web Worker par mode de méandre (diagramme, conforme,
rubans, et le film de la triangulation mobile sans le maillage gris), films en polylignes redessinées sur le canvas. Voir un résultat : `python3 -m http.server` dans `web/` ;
déploiement : `web/deploie.sh` (rsync vers la cible de `web/deploie.conf`, local et non suivi par git ; règle de cache : `web/README.md`).
Publiée aussi sur GitHub Pages (`https://xysticus.github.io/braid-blackboard/`) par `.github/workflows/pages.yml`, lancé
par chaque push touchant `web/` (21 s ; il copie seulement les fichiers). `ardoise_lib.js` est dans git : le hook `.githooks/pre-push`
(activé par `git config core.hooksPath .githooks`, à refaire après un clone) reconstruit le JS avant chaque push et refuse de
pousser s'il a changé (le commiter, puis repousser). `git publie` (alias local vers `web/publie.sh`) = `git push` puis
`web/deploie.sh` : seul un push met à jour GitHub Pages ; le serveur personnel n'est mis à jour que par `deploie.sh`.
Sous JavaScript, pas de récursion non terminale sur de longues listes (`List.concat`, `List.fold_right`) : la pile est
petite.
