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

**Publication GitHub Pages : une panne passagère à connaître (2026-11-22, corrigée le 2026-11-23).** Il arrive que le workflow échoue à l'étape de dépôt
(`deploy-pages`) avec « No artifacts named "github-pages" were found for this workflow run » (« Found 0 artifact(s) ») : l'archive du site vient d'être créée et
l'API de GitHub ne la voit pas encore (course de vitesse ; aucun incident annoncé). Le 2026-11-23, cela a échoué à presque chaque push. **Le workflow fait maintenant une
pause de 20 s avant le dépôt** (étape « Laisse l'archive devenir visible » de `.github/workflows/pages.yml`). Si l'échec revient malgré tout : ne **pas** faire
`gh run rerun <numéro> --failed` (il envoie une deuxième archive `github-pages` dans le même lancement, et le dépôt refuse alors deux archives) ; lancer à neuf par
`gh workflow run "Page web" --ref master` (le workflow a `workflow_dispatch`), au besoin après quelques minutes. Le serveur personnel, lui, n'en dépend pas (`web/deploie.sh`).

**Tresses personnalisées (2026-11-22).** Le bloc « les tresses mémorisées » de `web/ardoise.js` (mémoire, cartes, pastilles, export et
import JSON) est décrit dans `web/README.md` ; décisions et raisons : `etude_tresses_personnalisees.md`. La palette et le fond sont
des variables globales (`PALETTE`, `FOND`, `fondDe`) lues au dessin : changer une couleur redessine (`recolore`), sans calcul.

**Lecteurs : chapitres et exports (2026-11-23).** `dessineImage` est coupée en `listeDeTrace` (quoi tracer, avec la palette et le fond courants) et
`dessineListe` (le dessin, à l'échelle voulue) : le canvas, le PNG et le SVG lisent la même liste. OCaml met un champ `chapitres` sur l'image 0 de
chaque film d'un mot (les numéros d'image où commence chaque lettre, puis la dernière image : `avec_chapitres` dans `ocaml/web/ardoise_web.ml`) ;
pour la triangulation, ils sont relevés pendant l'essai silencieux (`prepare_triangulation`). `web/exports.js` est dans les listes de fichiers du
workflow `pages.yml` et de `web/deploie.sh` : en ajouter un autre oblige à les mettre à jour toutes les deux. Détail et suite des étapes :
`etude_exploitation_des_images.md`.

**Le film MP4 AV1 (2026-11-23).** `exporteFilm` (`web/exports.js`) dessine chaque image du film à l'échelle voulue (`dessineExport`), la confie au
`VideoEncoder` du navigateur (AV1, `latencyMode: 'realtime'`, image clé toutes les 50 images, 3 Mb/s pour 800 × 800) et `construitMP4` (`web/mp4.js`)
emballe les morceaux : `moov` avant `mdat`, un seul bloc d'échantillons, **cadence constante** (25 images par seconde, 12,5 pour les iris). Les
pauses (0,5 s sur la première image, 1,5 s sur la dernière, 2 s de générique) sont des **images répétées**, pas un échantillon long : VLC ne respecte
pas la durée du dernier échantillon et coupait le film avant la fin (vu le 2026-11-23). Le mode `'quality'` de Firefox donnait un flux compliqué
(plusieurs images cachées par unité, des unités de 3 octets `show_existing_frame`) ; `'realtime'` donne une image affichée par unité. Firefox ne donne pas la description `av1C` : on la fabrique (profil 0, 4:2:0 à 8 bits, niveau tiré de la taille
de l'image) et on y met l'OBU « sequence header » de la première image clé ; les OBU « temporal delimiter » sont retirées des échantillons. Pour l'escargot et les
iris : un générique de fin de 2 s (une image de plus) et les mentions `cprt` (norme ISO) et `©cpy` (forme QuickTime, la seule que `ffprobe` lise) ; pour un mot,
seulement un commentaire « Créé avec Ardoise à tresse ». Vérification : `ffprobe` (codec `av1`, nombre d'images, durée, étiquettes), `ffmpeg -i f.mp4 -f null -`
(décodage sans erreur) et le PSNR d'images décodées contre les PNG exportés (35 à 39 dB). Pas de transparence dans l'AV1 : le fond est plein.
**Essayé seulement dans Firefox** (Chrome et Edge doivent marcher, Safari ne sait pas faire d'AV1). Lu par `ffmpeg` et par VLC (Windows) : les trois films
vont jusqu'au bout. Windows Media Player ne l'ouvre pas : il lui faut le décodeur AV1 de Windows (« Extension vidéo AV1 », du Microsoft Store).

**La page en cartes, et le tag v1.7 (2026-11-23).** Le haut de la page est une seule carte, « Mot courant » : le champ de saisie, le mot en notation
mathématique, l'état du mot (`metsAJourEtatMot` : exemple fourni, enregistré, pas enregistré), la note de la tresse enregistrée, les couleurs, et deux
boutons, « Tresses ▾ » (la liste des exemples et des tresses enregistrées, qui s'ouvre en menu sous deux titres) et « Enregistrer » (`enregistreCourant`).
**Rien n'est enregistré sans ce bouton** (le mot tapé ne crée plus d'entrée) ; les couleurs ne se changent que sur une tresse enregistrée. L'aide d'écriture
et les limites sont dans un `<details>` ; les explications des méandres et de « Un peu de poésie » sont dans des « Les coulisses » repliées ; l'avertissement
des limites (`etatLimites`) n'apparaît que si le mot les dépasse. Le diagramme de tresse porte, à droite, la colonne des générateurs (σ₁, σ₂⁻¹…).
Les exemples sont au nombre de douze (voir `etude_page_web.md`, §7) ; l'exemple de départ est désigné par son mot (`1 -2`), pas par son numéro.
Le tag `v1.7` marque cet état (lecteurs, exports, cartes, exemples) : c'est la version à déployer sur un serveur personnel (`git checkout v1.7`, puis
`web/deploie.sh`).

