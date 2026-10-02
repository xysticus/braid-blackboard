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
- `programmes/NouvAutoMorph.py` : **réimplémentation en cours** (travail actif), avec un algorithme plus simple :
  voir plus bas.
- `programmes/tortue.py` : simple exemple turtle, hors sujet.
- `imgs/` : images du README. `*.png` est dans `.gitignore` : les images du README existantes sont suivies,
  les nouvelles sorties ne le sont pas.

## L'algorithme actuel du méandre (`AutoMorphPNG.py`)

Il marche, mais il est compliqué. Les étapes :

1. `calcule_autofn_de_tresse` : images réduites des générateurs x_i par la tresse (action d'Artin).
2. `decoupeuse` + `generatrice_haut` / `generatrice_bas` : chaque mot est coupé en suites croissantes
   consécutives (`[1,2,3]` = on passe au-dessus des trous 1, 2, 3). Chaque suite donne un arc du haut,
   chaque transition entre deux suites donne un arc du bas.
3. `trie_arcs` / `compare_arcs` : les arcs de *tous* les mots sont triés par emboîtement (le plus intérieur d'abord).
4. `arc_exact` + `positiver` : on numérote les passages sur l'axe horizontal dans chaque intervalle entre trous
   (compteurs gauche/droite, positions signées, puis renormalisées).
5. `cherche_debuts` + `chemine` : on recolle les arcs en lacets en alternant nord et sud.
6. `situe` : conversion en demi-cercles (centre, rayon, angles), puis tracé Cairo.

Ce qui le rend fragile : l'ordre d'emboîtement (`compare_arcs`) n'est pas un ordre total quand des arcs se croisent ;
les positions sont d'abord relatives, puis renormalisées ; on perd l'information « quel arc vient de quel mot »
et il faut la reconstruire. Surtout, le dessin est recalculé d'un bloc pour un mot : il n'y a pas d'état
intermédiaire à animer.

## Le nouvel algorithme, plus simple (`NouvAutoMorph.py`)

Il dessine maintenant les méandres et donne la même topologie qu'`AutoMorphPNG.py`.

1. `calcule_arcs(mot)` puis `intervalles(mot)` : chaque lacet devient la suite des intervalles où il coupe l'axe
   (l'intervalle k est entre le trou k et le trou k+1). De l'indice 2i à 2i+1 c'est un arc du haut, de 2i+1 à 2i+2
   un arc du bas ; le premier et le dernier point sont reliés au clou par le bas.
2. `compare_points` / `suit_en_parallele` : ordre gauche-droite de deux points du même intervalle. On suit les deux
   courbes côte à côte jusqu'à ce qu'elles se séparent ; chaque arc parcouru en parallèle inverse l'ordre (arcs emboîtés).
   Le clou est sous tous les arcs du bas. Si les deux courbes arrivent ensemble au clou, on repart dans l'autre sens.
3. `abscisses` : tri de chaque intervalle avec cette comparaison, puis rang global sur l'axe des points et des trous.
4. `dessine_auto_de_tresse(tresse, fichier)` : demi-ellipses entre points consécutifs, alternativement en haut
   et en bas ; descente verticale vers le clou sous tous les arcs.
5. `croisements` / `verifie` : contrôle qu'aucun arc n'en croise un autre. Les `assert verifie(...)` servent de tests.
6. `film_de_tresse(tresse, fichier)` : GIF (Pillow) des images de chaque préfixe `tresse[:k]`, avec un nombre
   de trous fixé par la tresse entière (`calcule_autofn_de_tresse(tresse, nb_trous)`). `image_auto_de_tresse`
   renvoie la surface Cairo ; `dessine_auto_de_tresse` l'écrit en PNG.
   Le dessin passe par `geometrie_auto_de_tresse` (polylignes numpy : chemins Cairo aplatis par `copy_path_flat`
   puis subdivisés, positions des trous et du clou) et `peint` (trace les polylignes).
7. `film_continu_de_tresse(tresse, fichier)` : le film continu. Pour chaque lettre, `tord` fait tourner d'un
   demi-tour la région autour des trous i et i+1 (`ellipses_de_torsion` / `tourne` : rotation le long d'ellipses
   emboîtées, entière dans l'ellipse intérieure, amortie jusqu'à l'extérieure, qui évite les autres trous et le clou),
   et `glisse` (déformation horizontale monotone, amortie vers le clou) amène en même temps tous les trous à leur
   place dans l'image suivante : sur les 70 % premiers du temps (`mouvement`), deux homéomorphismes, pas de croisement.
   Ensuite fondu linéaire vers l'image clé suivante. Les points se correspondent grâce à `correspondance` :
   les passages sur l'axe (`passages`, simplifiés en annulant deux passages consécutifs dans le même intervalle)
   du dessin tordu d'un demi-tour sont exactement ceux de l'image suivante ; ce sont des repères,
   entre lesquels on rééchantillonne par abscisse curviligne (`entre_reperes`).
   `lit_mot` relit le mot d'une polyligne (traversées des demi-droites qui montent des trous) ;
   `verifie_torsion` contrôle que chaque image clé tordue d'un demi-tour se lit comme le préfixe suivant.
   Sens : σ_i positif = demi-tour horaire à l'écran (`SENS_DE_SIGMA = 1`, repère Cairo y vers le bas) ;
   le test échoue avec l'autre sens.

Convention de composition : `calcule_autofn_de_tresse` parcourt la tresse à l'envers, donc
auto(`tresse[:k+1]`) = φ_σ ∘ auto(`tresse[:k]`) avec σ = `tresse[k]`. L'image k+1 s'obtient en tordant les trous i, i+1
de l'image k : le dessin du préfixe suivant est bien l'image du dessin courant par la torsion.

`decale` et `dedans_extrm` viennent de l'ancienne idée d'insertion point par point (description dans
`git show f2fdb1c` et `git show 4b2d4f4`). Ils ne sont plus utilisés.

Prochaine étape, le film : l'état « lacets + ordre des points sur l'axe » est celui sur lequel σ_i devra agir
continûment. Les images de chaque préfixe de la tresse sont les images clés.

## Prochaines étapes

Objectif : le film (b), où σ_i fait tourner continûment les trous i et i+1 l'un autour de l'autre
et entraîne les lacets.

1. ~~**Film image par image.**~~ Fait : `film_de_tresse` → `imgs/film_*.gif`. Les trous gardent leur nombre mais
   bougent horizontalement d'une image à l'autre (l'espacement dépend du nombre de points sur l'axe).
2. ~~**Mouvement continu d'un σ_i.**~~ Fait : `film_continu_de_tresse` → `imgs/film_continu_*.gif`.
   Limites : le fondu final crée des croisements quand le demi-tour a beaucoup enroulé les brins
   (σ_2 et σ_1 de [4, 3, -1, -1, 2, -4, 1]) ; les lacets voisins sont entraînés par la torsion puis relâchés
   par le fondu. Essais écartés : mélanger image tordue de t et image suivante détordue de 1 - t (cartésien
   ou polaire), mélanger puis détordre ; tous font des croisements.
   Piste : remplacer le fondu par une détente physique (raccourcissement et lissage des brins, répulsion
   entre brins et par les trous, petits pas), qui garde la topologie par construction (scipy `cKDTree`).
3. **À plus long terme.** Faire agir σ_i directement sur l'état « lacets + ordre des points sur l'axe »,
   sans repasser par les mots de F_n. Le dessin calculé depuis le mot sert alors de test.
4. **Ménage.** Supprimer `decale` et `dedans_extrm` (inutilisés) ; éventuellement passer les `assert` en tests pytest.

Sur un nouvel ordinateur : `git pull`, puis `conda env create -f environment.yml` (ou `conda env update -f
environment.yml --prune` si l'environnement existe déjà).

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
python programmes/NouvAutoMorph.py   # vérifie les assert, écrit imgs/nouv_*.png, imgs/film_*.gif et imgs/film_continu_*.gif
python programmes/AutoMorphPNG.py    # écrit imgs/a43m1m12m41nv.png
jupyter lab ipynbks/                  # notebooks
```
