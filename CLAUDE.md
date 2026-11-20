# CLAUDE.md

## Qui tu es, ce que tu vises

Tu es un mathématicien amateur qui aime représenter la théorie des tresses par des dessins et des films.

Ce que tu sais déjà faire :
- figurer un mot de tresse par les croisements de brins, à la manière classique ;
- représenter l'automorphisme du groupe libre associé à une tresse
  (J. Birman, *Braids, Links, and Mapping Class Groups*).

Le but : **un film** où les méandres du groupe libre se dessinent de manière continue au fil de la tresse,
et pas seulement une image figée pour un mot donné.

On code en Python, on dessine avec Cairo (pycairo).

## Le projet

« Ardoise à tresse » : dessiner des éléments du groupe de tresses d'Artin B_n.
Deux représentations :
- le diagramme de tresse classique (`dessine_tresse([4, -2, 3, -2])`) ;
- l'action d'Artin de la tresse sur le groupe libre F_n, dessinée comme des lacets
  autour de n trous (`dessine_auto_de_tresse(...)`).

Référence mathématique : *Le calcul des tresses*, P. Dehornoy.
Conventions de signe comparées à celles de l'article *Des matrices pour des tresses* (Images des mathématiques, 2026) :
`conventions_de_signe.md` (β de l'article = β⁻¹ chez nous ; on garde nos conventions).
Étude (rien d'implémenté) d'une case « lignes de construction » dans les lecteurs de film du notebook : `etude_lignes_de_construction.md`.

## Organisation

- `ipynbks/` : notebooks historiques (ipycanvas pour le canvas HTML5, `AutoMorphCairo.ipynb` en pycairo ; liens Binder dans le
  README, ne pas casser leurs chemins) et `Ardoise.ipynb`, la page web en Python (la plomberie est dans `python/Interface.py` ;
  détail : `ipynbks/README`). **Un notebook se commite sans sorties** : « Edit → Clear All Outputs » avant de commiter (JupyterLab
  les enregistre à chaque sauvegarde) ; ne pas modifier le fichier pendant qu'il est ouvert dans JupyterLab.
- `python/AutoMorphPNG.py` : version script complète (pycairo → PNG) de l'algorithme de dessin
  des automorphismes. Sert de référence fonctionnelle.
- `python/tresses.py` : **base commune** importée par les scripts suivants : mots de F_n et action d'Artin
  (`calcule_autofn_de_tresse`), état d'un méandre (`intervalles`, `abscisses`, `etat_de_tresse`), action algébrique
  de σ_i (`agit`, `reduit`), dessin d'un état (`dessin_etat`, `peint`, `image_auto_de_tresse`), relecture des mots
  (`lit_mot`), arcs de cercle raccordés (`deux_arcs`), images (`en_image_pil`, `gif_en_mp4`). Ses `assert` tournent
  à chaque import (rapide).
- `python/NouvAutoMorph.py` : films successifs à partir de l'état (image par image, algébrique, simultané, essais
  en arcs : points 1 à 10 de `docs/algorithmes_python.md`). `from tresses import *` ; lancé (`__main__`), il écrit ses images et ses films.
- `python/Triangulation.py` : **le film actuel** (triangulation mobile, point 11 de `docs/algorithmes_python.md`), `film_triangule`.
- `python/Conforme.py` : film par représentation conforme (point 13 de `docs/algorithmes_python.md`), `film_conforme` ;
  `python/Raccord.py` : son raccord par triangulation mobile.
- `python/Arcs.py` : essai sans clou, des arcs entre trous fixes et trous voyageurs (piste 1 ter de
  `pistes_film_conforme.md`), `film_arcs` ; `DiagrammeCourbes` : le diagramme de courbes ; `hyperbolique=True`
  (`python/Geodesiques.py`), `fixes='gauche'`, `ecart_fixes`.
- `python/Escargot.py` : un escargot fait de rubans, `film_escargot` → `imgs/escargot/film.mp4` ; `python/Bouquet.py` : le bouquet
  qui pousse (point 12 de `docs/algorithmes_python.md`) ; `python/Interface.py` : l'interface `ipywidgets` du notebook.
- `ocaml/` : réécriture en OCaml (`plan_ocaml.md` ; étapes faites, tests, installation : `docs/ocaml.md`). Travailler dans le
  clone côté Linux (`~/dev/braid-blackboard` sous WSL) : dune ne construit pas sur `/mnt/c` (pas de socket Unix). `dune test`
  dans `ocaml/` compare au Python (`test/reference_*`, écrits par `python ocaml/test/genere_reference*.py`). Switch opam local
  `ocaml/_opam` (ignoré par git, dépendances dans `ocaml/dune-project`). Mêmes noms qu'en Python (voir Conventions).
- `web/` : **l'ardoise à tresse en page web** (mode d'emploi : `web/README.md`, étude : `etude_page_web.md`, fabrication et
  publication : `docs/page_web.md`). Le calcul est celui de `ocaml/lib/` compilé par js_of_ocaml : `web/construit.sh` →
  `web/ardoise_lib.js`, **suivi par git** : le hook `.githooks/pre-push` (à activer par `git config core.hooksPath .githooks`)
  le reconstruit avant chaque push et refuse de pousser s'il a changé (le commiter, puis repousser). Un push qui touche `web/`
  met à jour GitHub Pages.
- `imgs/` : images du README. `*.png` est dans `.gitignore` : les images du README existantes sont suivies,
  les nouvelles sorties ne le sont pas. Un sous-répertoire par méthode (`imgs/conforme/`, `imgs/diagramme/`,
  `imgs/rubans/`, `imgs/rubans_gauche/`), chacun avec un README et un `apercu.jpg` suivi ; les films (`film_*.mp4`, ignorés)
  y sont écrits par `python python/Conforme.py` et `python python/Arcs.py [rubans] [rubans_gauche] [diagramme]`.

## Le détail est ailleurs

- `docs/algorithmes_python.md` : les algorithmes des scripts Python, points 1 à 13 (méandre, action algébrique, films simultané,
  triangulation mobile, bouquet, représentation conforme).
- `docs/ocaml.md` : état des étapes OCaml, installation. `docs/page_web.md` : fabrication, publication et déploiement de la page.
- `docs/prochaines_etapes.md` : objectifs et avancement du film des méandres.
- `pistes_film_conforme.md`, `plan_ocaml.md`, `etude_page_web.md`, `conventions_de_signe.md` (β de l'article *Des matrices pour des
  tresses* = β⁻¹ chez nous : on garde nos conventions), `etude_lignes_de_construction.md` (lignes de construction facultatives, notebook et page web : faite pour les films de la triangulation
et des lacets de la page web ; le reste est à l'étude).

## Conventions

- Code, identifiants, commentaires et messages de commit **en français**. Garder ce style.
- Une tresse = liste d'entiers non nuls : `k` pour σ_k, `-k` pour σ_k⁻¹.
- Un mot de F_n = liste d'entiers non nuls : `i` pour x_i, `-i` pour x_i⁻¹.
- Un automorphisme = liste des images des générateurs (`images[i]` est l'image de x_(i+1)).
- Plusieurs fonctions travaillent par effet de bord (`simplifie`, `conjugaison_locale`) : le docstring le signale.
- **IMPÉRATIF : ne rien écrire de sensible dans ce dépôt, qui est public** (GitHub). Ni l'existence, ni le nom, ni l'adresse du
  serveur personnel de l'utilisateur ; ni identifiant de connexion, chemin d'hébergement, clé, mot de passe ou détail
  d'installation ; ni dans les fichiers, ni dans les docs, ni dans les messages de commit, ni dans les sorties collées. Ces détails
  vont dans des fichiers locaux ignorés par git (`web/deploie.conf`, `web/*.local.md`) ; on dit seulement « un serveur personnel ».
  Aucun élément privé non plus : ni adresse mail (seule l'adresse masquée `noreply` de GitHub est permise, dans les commits),
  ni chemin qui contient un nom d'utilisateur (écrire `~/...` ou un chemin relatif au dépôt), ni nom de machine, ni nom
  d'employeur. L'historique a été réécrit le 2026-11-19 pour en retirer de telles mentions ; vérifier le diff et le message
  avant chaque commit et chaque poussée.
- Python ≥ 3.10 requis (`match`/`case` utilisés).
- OCaml (`ocaml/`) : mêmes noms qu'en Python pour les fonctions et les types traduits (`mot_de_fn`,
  `simplifie`, `conjugaison_locale`, `calcule_autofn_de_tresse`…) ; si la signature diffère (argument, effet de bord),
  le commentaire le dit. Attention : le `agit` du Python est l'action sur l'état d'un méandre, pas l'action d'Artin.
- Deux usages pour chaque script : module (on l'importe, rien ne s'exécute) et exemples (on le lance) : les tests
  (`assert`), les `print` d'essai et la fabrication des images et des films sont sous `if __name__ == "__main__":`
  dans `NouvAutoMorph.py` et `Triangulation.py`. `tresses.py`, sans exemples, garde ses `assert` au niveau du module
  (rapides, ils vérifient la base à chaque import).

## Environnement

Conda (miniforge), environnement `braid-blackboard` défini dans `environment.yml` :

```
conda env create -f environment.yml      # première installation
conda env update -f environment.yml --prune   # après modification
conda activate braid-blackboard
```

Sans activer : `conda run -n braid-blackboard python ...`

Sur un nouvel ordinateur : `git pull`, puis `conda env create -f environment.yml` (ou `conda env update -f
environment.yml --prune` si l'environnement existe déjà).

## Lancer

Depuis la racine du dépôt (les chemins de sortie comme `./imgs/...` sont relatifs au répertoire courant) :

```
python python/Triangulation.py   # le film actuel : vérifie les assert, écrit imgs/film_triangule_*.mp4
python -c "import sys; sys.path.insert(0, 'python'); import Triangulation as T; T.film_triangule([1, 2, -1], 'imgs/f.mp4')"   # un autre film
python python/NouvAutoMorph.py   # vérifie les assert, écrit imgs/nouv_*.png, imgs/film_*.gif, imgs/film_continu_*.gif (film algébrique) et imgs/film_simultane_*.gif, plus leurs .mp4
python python/Conforme.py        # film conforme : imgs/conforme/film_*.mp4, 800 × 800 (avec vérification)
python python/Arcs.py            # rubans, rubans_gauche, diagramme (ou l'une d'elles en argument) : imgs/<méthode>/film_*.mp4
python python/AutoMorphPNG.py    # écrit imgs/a43m1m12m41nv.png
python -m jupyterlab ipynbks/        # notebooks (pas « jupyter lab » : il prend le premier jupyter-lab.exe du PATH, éventuellement d'un autre environnement)
```
