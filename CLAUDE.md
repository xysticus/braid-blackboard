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

## Organisation

- `ipynbks/` : notebooks historiques (ipycanvas pour le canvas HTML5, `AutoMorphCairo.ipynb` en pycairo).
  Liens Binder dans le README, ne pas casser leurs chemins.
- `programmes/AutoMorphPNG.py` : version script complète (pycairo → PNG) de l'algorithme de dessin
  des automorphismes. Sert de référence fonctionnelle.
- `programmes/NouvAutoMorph.py` : **réimplémentation en cours** (travail actif). Nouveau calcul des arcs
  (`calcule_arcs`) et du positionnement des intersections (`dedans_extrm`, `decale`, `continue_trace` inachevé).
- `programmes/tortue.py` : simple exemple turtle, hors sujet.
- `imgs/` : images du README. `*.png` est dans `.gitignore` : les images du README existantes sont suivies,
  les nouvelles sorties ne le sont pas.

## Conventions

- Code, identifiants, commentaires et messages de commit **en français**. Garder ce style.
- Une tresse = liste d'entiers non nuls : `k` pour σ_k, `-k` pour σ_k⁻¹.
- Un mot de F_n = liste d'entiers non nuls : `i` pour x_i, `-i` pour x_i⁻¹.
- Un automorphisme = liste des images des générateurs (`images[i]` est l'image de x_(i+1)).
- Plusieurs fonctions travaillent par effet de bord (`simplifie`, `conjugaison_locale`) : le docstring le signale.
- Python ≥ 3.10 requis (`match`/`case` utilisés).
- Les scripts n'ont pas de `if __name__ == "__main__"` : les tests sont des `assert`/`print` au niveau module,
  exécutés à chaque lancement.

## Environnement

Conda (miniforge), environnement `braid-blackboard` défini dans `environment.yml` :

```
conda env create -f environment.yml      # première installation
conda env update -f environment.yml --prune   # après modification
conda activate braid-blackboard
```

Sans activer : `conda run -n braid-blackboard python ...`

## Lancer

Depuis la racine du dépôt (les chemins de sortie comme `./imgs/...` sont relatifs au répertoire courant) :

```
python programmes/NouvAutoMorph.py   # imprime les arcs et vérifie les assert
python programmes/AutoMorphPNG.py    # écrit imgs/a43m1m12m41nv.png
jupyter lab ipynbks/                  # notebooks
```
