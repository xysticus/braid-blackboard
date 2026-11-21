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

**Le film des lacets, détendu et réparti (2026-11-21, tag v1.2).** La vue « lacets » demande au worker le mode de calcul
`conforme_detendu` (`MODE_DE_CALCUL` dans `web/ardoise.js`) : le film conforme détendu pendant le raccord (`ocaml/lib/detente.ml`).
`web/travail.js` répartit ce film (et le mode `conforme` du banc d'essai) sur des workers auxiliaires, autant que de cœurs (8 au
plus) : les lettres leur sont données une à une (`ardoise.film_lettres`), calculées sans détente, et chaque image du raccord revient
en double précision pour être détendue à son tour par un auxiliaire (`ardoise.detend`) ; le worker principal calcule l'image clé de
départ et rend les images dans l'ordre. Mêmes images qu'en un seul worker ; sur 12 cœurs, (σ₁σ₂⁻¹)³ en moins de 24 s et la tresse
chargée en moins de 70 s (au lieu de 80 s et 4 min 45 en un seul worker).
