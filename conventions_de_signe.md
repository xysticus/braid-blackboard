# Conventions de signe : l'ardoise et « Des matrices pour des tresses »

Comparaison des conventions de l'ardoise avec celles de l'article de Hoel Queffelec,
*Des matrices pour des tresses*, Images des mathématiques, vol. 4 (2026), p. 211-222,
doi : [10.60868/d940-ak86](https://images.math.cnrs.fr/des-matrices-pour-des-tresses/).
L'article raconte la preuve de la fidélité de la représentation de Burau pour 4 brins
(V. Bharathram, J. S. Birman, T. E. Brendle, *The Burau representation of the braid group is faithful for n = 4*,
arXiv : 2607.05283). Ses figures montrent les mêmes vues que l'ardoise : diagramme de brins, points mobiles dans des
disques empilés, arcs entre les points (diagramme de courbes).

**En bref : le σ₂⁻¹σ₁ de l'article est notre `[-1, 2]`. Une tresse β de l'article correspond à notre β⁻¹.**
On garde les conventions de l'ardoise ; cette page sert à traduire.

## Les conventions de l'ardoise

- Une tresse est une liste lue comme le scénario d'un film : la première lettre joue la première.
- Le diagramme de brins (`dessine_tresse`, notebooks `ipynbks/CanvasTresse*.ipynb`) est dessiné de haut en bas,
  la première lettre en haut. Pour σ_i positif, le brin qui va d'en haut à droite vers en bas à gauche passe devant.
- Dans les films, σ_i positif est un demi-tour **horaire** des trous i et i+1 à l'écran (`SENS_DE_SIGMA = 1`,
  y vers le bas). C'est bien le mouvement qu'on voit en lisant le diagramme de haut en bas : les deux conventions
  sont cohérentes entre elles.
- Action d'Artin (`conjugaison_locale`, `python/tresses.py`) : σ_i envoie x_i sur x_i x_(i+1) x_i⁻¹ et x_(i+1) sur
  x_i ; σ_i⁻¹ envoie x_i sur x_(i+1) et x_(i+1) sur x_(i+1)⁻¹ x_i x_(i+1). C'est la convention de Birman,
  *Braids, Links, and Mapping Class Groups*.
- Composition : auto(`[a₁, …, aₙ]`) = φ_aₙ ∘ … ∘ φ_a₁. La correspondance entre une liste et son automorphisme
  renverse l'ordre (`calcule_autofn_de_tresse` parcourt la tresse avec `reversed`).

## Les conventions de l'article

- Le produit αβ pose α au-dessus de β (figure 3), et la tresse se lit **de bas en haut** : dans σ₂⁻¹σ₁, la lettre de
  droite, σ₁, agit la première (figure 5). C'est la lecture de la composition des fonctions, f ∘ g, où g agit
  d'abord.
- Le croisement de σ_i a le **même dessin** que chez nous (figure 4) : le brin qui va d'en bas à gauche vers en haut
  à droite passe dessus. À mot écrit égal, les deux diagrammes de brins sont identiques.
- Lu en montant, ce croisement est un demi-tour **antihoraire** des points i et i+1 dans le disque. On le voit sans
  ambiguïté sur la figure 7 : après σ₁, l'arc bleu passe au-dessus du point vert, donc le point qui était en
  position 2 est venu en position 1 par le haut. La figure 5 le confirme : dans les disques empilés, le point vert
  passe devant.
- Les arcs (les « spaghettis ») sont poussés en avant par le mouvement des points, comme nos lacets.
- Matrices de Burau réduites, en q, une colonne par arc élémentaire entre deux points voisins (figure 6).
  Pour 4 brins :
  M(σ₁) = ((−q, −1, 0), (0, 1, 0), (0, 0, 1)), M(σ₂) = ((1, 0, 0), (−q, −q, −1), (0, 0, 1)),
  M(σ₃) = ((1, 0, 0), (0, 1, 0), (0, −q, 1)) (les lignes sont données dans l'ordre).
  β ↦ M(β) est un morphisme : M(αβ) = M(α)·M(β).

## Deux choix indépendants

Une convention de signe pour les tresses, c'est deux choix.

**1. L'ordre des lettres.** L'article écrit le mot comme une composition : la dernière lettre agit la première.
C'est commode pour l'algèbre, puisque le mot se recopie tel quel en produit de matrices. L'ardoise écrit le mot dans
l'ordre du temps, ce qui est commode pour un film, mais la correspondance avec les automorphismes renverse alors
l'ordre. Une fois traduites en composition, les deux écritures coïncident : notre `[1, -2]` donne
φ_σ₂⁻¹ ∘ φ_σ₁, c'est-à-dire l'écriture σ₂⁻¹σ₁ de l'article.

**2. Le demi-tour qu'on appelle σ_i.** Le même dessin de croisement, lu en descendant chez nous, en montant dans
l'article, donne deux demi-tours de sens opposés : horaire chez nous, antihoraire dans l'article.
Le σ_i de l'article est notre σ_i⁻¹.

Ce n'est donc pas l'ordre des lettres qui nous sépare, c'est le sens du demi-tour. Les deux décalages ensemble
donnent la règle : renverser le sens du temps change une tresse en son inverse, β de l'article = β⁻¹ chez nous.
Ainsi (σ₂⁻¹σ₁)⁻¹ = σ₁⁻¹σ₂, notre `[-1, 2]`.

## Vérification sur le diagramme de courbes

La page web dessine pour `1 -2` la figure 5 de l'article (disque du haut) **retournée de haut en bas** :

| Arc de départ | Article, σ₂⁻¹σ₁ | Page web, `1 -2` |
|---|---|---|
| positions 1–2 (orange) | de la position 1 à la position 3, **au-dessus** de la position 2 | de la position 1 à la position 3, **sous** la position 2 (vert) |
| positions 2–3 (bleu clair) | de la position 1, par le haut, autour de la position 3 par la droite, retour à la position 2 | même chemin par le bas (bleu) |

Les mouvements le confirment. Dans l'article : σ₁ en sens antihoraire, puis σ₂⁻¹ en sens horaire sur les
positions 2 et 3. Dans la page : σ₁ en sens horaire, puis σ₂⁻¹ en sens antihoraire. Ce sont les mêmes mouvements
renversés par la symétrie haut-bas. Pour retrouver la figure telle quelle, entrer `-1 2` dans la page.

Différences de mise en scène, sans effet sur la convention : notre diagramme de courbes a un point fixe **à gauche**
(son arc, le rouge de la page, n'a pas d'équivalent dans la figure), l'article un brin fixe **à droite** (le jaune,
avec l'arc violet entre les positions 3 et 4). Nos arcs sont des lignes brisées tendues avec des congés : seule la
topologie se compare.

## Ce qui n'est pas vérifié

- La page avec `-1 2` n'a pas été comparée à la figure à l'œil : la correspondance vient du raisonnement ci-dessus et
  de la comparaison de `1 -2` avec la figure retournée.
- Burau : le calcul de Fox sur notre action d'Artin devrait redonner les matrices de l'article, au remplacement près
  de σ_i par σ_i⁻¹ (donc de q par q⁻¹, ou d'une transposition). Pas encore calculé : voir « À faire » ci-dessous.

## À faire : vérifier la correspondance avec Burau par le calcul de Fox

Les matrices de l'article (figure 6) sont la représentation de Burau **réduite**. Nos images d'automorphismes
(`calcule_autofn_de_tresse`) en donnent la version non réduite, par le calcul de Fox :

1. dériver chaque mot image φ(x_i) par rapport à chaque générateur x_j, avec ∂(uv) = ∂u + u·∂v et ∂(x⁻¹) = −x⁻¹ ;
2. remplacer chaque x_j par la variable t : on obtient une matrice n × n à coefficients dans ℤ[t, t⁻¹], la ligne i
   venant de φ(x_i) ;
3. passer à la forme réduite (taille n − 1) pour comparer avec l'article.

Exemple pour σ₁ (x₁ ↦ x₁x₂x₁⁻¹, x₂ ↦ x₁) : ∂(x₁x₂x₁⁻¹)/∂x₁ = 1 − t, ∂(x₁x₂x₁⁻¹)/∂x₂ = t, ∂x₁/∂x₁ = 1,
∂x₁/∂x₂ = 0, d'où la matrice [[1 − t, t], [1, 0]] : la matrice de Burau classique de σ₁.

Comparer ensuite les matrices de nos σ_i avec celles de l'article, en tenant compte des décalages de conventions :
σ_i échangé avec σ_i⁻¹ (sens du temps, voir plus haut), variable t ou q inversée, transposition (l'article met les
images en colonnes, le calcul de Fox ci-dessus les met en lignes). Si elles coïncident à ce changement près, la
correspondance de signes est établie sur un résultat chiffré, et pas seulement par le raisonnement sur les figures.
Une fonction de quelques dizaines de lignes de Python suffirait (polynômes de Laurent en t), avec un test sur les trois
générateurs de B₄.

## Si l'on voulait suivre l'article

Changer seulement le sens du demi-tour suffirait : `SENS_DE_SIGMA = -1` et la règle de `conjugaison_locale`
inversée. Notre `[1, -2]` donnerait alors les images de leur σ₂⁻¹σ₁, avec le mot écrit dans le même ordre. Mais
cela touche les tests, les films de référence, le code OCaml et la page web : on ne le fait pas.
