# Le code OCaml, fonction par fonction

Réécriture en OCaml des algorithmes de l'ardoise à tresse (voir [`plan_ocaml.md`](../plan_ocaml.md)). Chaque
fonction porte le nom de la fonction Python qu'elle traduit ; quand la signature diffère (argument, effet de bord),
le `.mli` le dit.

| Module | Traduit | Étape du plan |
|---|---|---|
| [`lib/geometrie.ml`](lib/geometrie.ml) | les opérations numpy sur les points | 3 |
| [`lib/tresses.ml`](lib/tresses.ml) | `python/tresses.py` : groupe libre, action d'Artin, méandre, relecture, arcs | 1, 3, 3 bis |
| [`lib/triangulation.ml`](lib/triangulation.ml) | `Maillage`, `maillage_initial`, `noeuds_de_polyligne` de `python/Triangulation.py` | 2, 3 bis |
| [`lib/film.ml`](lib/film.ml) | la classe `Film` de `python/Triangulation.py` | 3, 3 bis |
| [`lib/raccord.ml`](lib/raccord.ml) | `python/Raccord.py` : `maillage_du_raccord`, `insere` ; le raccord du film conforme (`RaccordTriangule` et ses outils) | 4, 7c |
| [`lib/arcs.ml`](lib/arcs.ml) | `python/Arcs.py` : `FilmArcs`, `DiagrammeCourbes` (sans la tension hyperbolique) | 4 |
| [`lib/escargot.ml`](lib/escargot.ml) | `python/Escargot.py` : la chorégraphie et `deplace` | 6 |
| [`lib/conforme.ml`](lib/conforme.ml) | `python/Conforme.py` : la carte de Schwarz–Christoffel (`Carte`, `demi_cercle`), la lettre (`Lettre`) | 7a, 7b |
| [`dessin/dessin.ml`](dessin/dessin.ml) | `peint`, `Film.cadre`, `film_triangule`, `FilmArcs.cadre`, `film_arcs`, `Escargot.dessine`, `film_escargot` (cairo2, ffmpeg) | 4, 5, 6 |

Les tests (`dune test` dans `ocaml/`) comparent chaque fonction aux sorties du Python, écrites dans
`test/reference_*` par `python ocaml/test/genere_reference*.py`.

**Choix d'ensemble : tout est persistant.** Le Python modifie ses objets sur place (`simplifie`,
`conjugaison_locale`, `Maillage.retourne`, `Film.tend`…) ; ici chaque fonction rend une nouvelle valeur. Les
tableaux et tables de hachage n'apparaissent qu'à l'intérieur d'une fonction, invisibles de l'extérieur.

---

## 1. Géométrie (`geometrie.ml`)

```ocaml
type point = { x : float; y : float }
let ( +: ) p q = ...   let ( -: ) p q = ...   let ( *: ) a p = ...
let croix u v = u.x *. v.y -. u.y *. v.x
```

- **`+:`, `-:`, `*:`, `oppose`** : addition, soustraction, produit par un nombre, opposé. OCaml n'a pas de
  surcharge d'opérateurs (`-` est réservé aux entiers, `-.` aux flottants) : les points ont leurs propres symboles.
  Un enregistrement fait seulement de flottants, comme `{ x; y }`, est rangé « à plat » en mémoire.
- **`croix u v`** : le déterminant de (u, v), l'aire signée du parallélogramme ; positif si l'on tourne dans le sens
  direct de u vers v. Orientation, convexité, intersections : presque tout en dépend.
- **`scalaire`** (le `u @ v` du Python) et **`norme`** (le `math.hypot`).

---

## 2. Tresses et groupe libre (`tresses.ml`, étape 1)

### Lettres et alphabets : un type fantôme

```ocaml
type x          (* alphabet de F_n *)
type sigma      (* alphabet des tresses *)
type signe = Plus | Moins
type 'alphabet lettre = { indice : int; signe : signe }

type mot_de_fn = x lettre list
type tresse = sigma lettre list
```

Une lettre est un générateur ou son inverse : x_i^±1 dans un mot de F_n, σ_i^±1 dans une tresse. En Python, c'est
un entier non nul (`i` ou `-i`) ; ici, l'entier nul n'a pas de représentant, et le signe n'est plus caché dans le
signe de l'entier.

- **`x` et `sigma` sont des types vides** : aucune valeur ne les habite, ils servent seulement d'étiquettes. Comme
  ils sont déclarés séparément, le compilateur les sait distincts.
- **Le paramètre `'alphabet` n'apparaît dans aucun champ** : c'est un *type fantôme*. Une `x lettre` et une
  `sigma lettre` sont le même enregistrement en mémoire, mais le compilateur refuse de les confondre. Passer une
  tresse là où l'on attend un mot de F_n est une erreur de type
  ([`exemples/confusion.ml`](exemples/confusion.ml), qui ne compile pas exprès) :

  ```
  Error: The value t has type tresse = sigma lettre list
         but an expression was expected of type mot_de_fn = x lettre list
         Type sigma is not compatible with type x
  ```

Fonctions communes aux deux alphabets (polymorphes en `'a`, écrites une seule fois) :

- **`inverse_lettre`** : x_i ↦ x_i⁻¹. Annotée `'a lettre -> 'a lettre` : sans l'annotation, la mise à jour
  `{ l with signe = … }` pourrait changer le paramètre fantôme, puisque aucun champ ne le contient.
- **`inverse`** : (a b c)⁻¹ = c⁻¹ b⁻¹ a⁻¹. `List.rev_map` renverse et inverse en une seule passe.
- **`lettre_de_entier`**, **`entier_de_lettre`** : conversions depuis et vers la notation Python ; c'est le type
  attendu qui choisit l'alphabet. **`tresse_de_entiers`** et **`mot_de_fn_de_entiers`** fixent l'alphabet,
  **`entiers_de_mot`** sert aux deux.

### Les mots réduits : un invariant porté par le type

```ocaml
module Reduit : sig
  type t = private mot_de_fn
  val simplifie : mot_de_fn -> t
  val produit : t list -> t
  val inverse : t -> t
end
```

Avec `private`, on peut **lire** un `Reduit.t` comme un mot (`(r :> mot_de_fn)`), mais on ne peut en **fabriquer**
un qu'avec les fonctions du module : tout `Reduit.t` est réduit. Le mot réduit est la **forme normale** de F_n
(deux mots réduits sont égaux si et seulement s'ils représentent le même élément) ; rien de tel pour les tresses,
qui ont des relations en plus (σ₁σ₂σ₁ = σ₂σ₁σ₂, σ₁σ₃ = σ₃σ₁), d'où un `Reduit` qui n'accepte que l'alphabet `x`.

- **`simplifie`** : réduction libre par une pile. On lit le mot de gauche à droite ; la pile contient le préfixe
  déjà lu, réduit, à l'envers. Si la nouvelle lettre annule la tête de pile, on dépile ; sinon on empile. La pile
  reste réduite, et les annulations en cascade (x y y⁻¹ x⁻¹ → mot vide) se font d'elles-mêmes. Le `simplifie` du
  Python fait la même chose sur place (`del` puis recul d'un cran), en temps quadratique.
- **`produit`** : concatène puis réduit, car les jonctions peuvent se simplifier : (x y)·(y⁻¹ z) = x z.
- **`inverse`** : l'inverse d'un mot réduit est réduit, on reste dans le type sans recalculer.

### L'action d'Artin

```ocaml
type automorphisme = Reduit.t array   (* a.(i) : image de x_(i+1) *)
```

- **`morphisme_identite n`** : x_i ↦ x_i pour i = 1…n. (Le Python prend n − 1, le plus grand indice de la tresse.)
- **`conjugaison_locale sigma auto`** : avec u, v les images de x_i et x_(i+1),
  σ_i : (u, v) ↦ (u v u⁻¹, u) et σ_i⁻¹ : (u, v) ↦ (v, v⁻¹ u v). Le filtrage `Plus | Moins` remplace le
  `if sigma > 0`. Deux différences avec le Python : on rend un nouveau tableau (`Array.copy`), et l'on réduit à
  chaque lettre au lieu de tout réduire à la fin (même résultat, la forme réduite est unique, mais les mots restent
  courts). Une garde lève `Invalid_argument` si σ_i ne trouve pas les trous i et i + 1.
- **`calcule_autofn_de_tresse ?nb_trous tresse`** :
  1. le nombre de trous : celui qu'on donne, sinon 1 + le plus grand indice (σ_i fait bouger les trous i et i + 1) ;
     6 pour la tresse vide, comme le Python ;
  2. on part de l'identité et l'on fait agir chaque lettre, **la dernière d'abord** : φ_(σ₁σ₂…σ_k) =
     φ_σ₁ ∘ φ_σ₂ ∘ … ∘ φ_σ_k. `fold_right` donne exactement cet ordre :
     `fold_right f [σ₁; σ₂; σ₃] id = f σ₁ (f σ₂ (f σ₃ id))` (le `for sigma in reversed(tresse)` du Python).

---

## 3. Le méandre (`tresses.ml`, étape 3 bis)

### L'idée

Un lacet (l'image d'un générateur) part du clou, en bas, fait le tour de certains trous et revient au clou. On le
coupe par l'**axe** horizontal qui passe par les trous : entre deux passages, il fait un arc, alternativement
au-dessus et au-dessous. Le dessin se résume à **la suite des intervalles** où le lacet coupe l'axe (l'intervalle k
est entre les trous k et k + 1). Il reste à décider **l'ordre** des points d'un même intervalle, pour que les arcs
ne se croisent pas.

### Du mot aux intervalles

- **`calcule_arcs mot`** : x₁x₂x₃ se lit « passer au-dessus des trous 1, 2, 3 ». Chaque **suite croissante
  consécutive** est un arc du haut ; quand elle s'arrête, on écrit l'arc du haut, puis l'**arc du bas** qui mène à
  la suite suivante (son signe donne son sens, les ±1 de quel côté de chaque trou il passe). La récursion
  `parcourt` porte `debut`, `courant` et les arcs déjà écrits.
- **`intervalles mot`** : on garde les arcs du haut (indices pairs) et chacun donne ses deux bouts : un arc positif
  de debut à fin part de l'intervalle debut − 1 et arrive dans l'intervalle fin (l'inverse pour un arc négatif).
  Du point 2i au point 2i + 1 c'est un arc du haut, de 2i + 1 à 2i + 2 un arc du bas ; le premier et le dernier
  point descendent au clou.

### L'ordre des points sur l'axe

On ne peut pas comparer deux points d'un même intervalle localement, mais on peut **suivre les deux courbes côte
à côte** jusqu'à ce qu'elles se séparent.

- **`voisin lacet j en_haut`** : le point relié au point j par son arc du haut (j xor 1) ou du bas (j ± 1) ;
  **`None`** si l'arc descend au clou.
- **`suit_en_parallele lacets p q en_haut`** : quatre cas.
  - Les deux arrivent au clou : rien à trancher de ce côté (0).
  - Un seul arrive au clou : le clou est sous tous les arcs du bas, un brin qui y descend n'est jamais englobé ;
    le sens de l'autre arc suffit.
  - Les deux arcs aboutissent à des intervalles différents : du même côté, ils sont emboîtés et celui qui va le
    plus loin est à l'extérieur ; de côtés opposés, celui qui part vers la gauche est à gauche.
  - Ils aboutissent au même intervalle : on continue depuis les points d'arrivée, de l'autre côté de l'axe, en
    **inversant le signe** (deux arcs emboîtés partent dans un ordre et arrivent dans l'ordre inverse).
- **`compare_points`** : vers le haut, puis vers le bas ; indiscernables, c'est une erreur.
- **`abscisses lacets nb_trous`** : trie chaque intervalle avec `compare_points` et numérote de gauche à droite
  (points de l'intervalle 0, trou 1, points de l'intervalle 1, trou 2…). Rend le rang de chaque point, de chaque
  trou (`rang_trou.(k)` pour le trou k + 1), et le nombre de rangs.

### Le contrôle

- **`type croisement = Arcs of … | Arc_et_descente of …`** : deux cordes du même côté qui **s'entrelacent**
  (a₁ < a₂ < b₁ < b₂) se croisent (deux demi-cercles sur une droite se croisent si et seulement si leurs extrémités
  alternent) ; ou un arc du bas enjambe le départ d'une descente au clou. Le Python mêle les deux cas dans une
  même liste.
- **`croisements`** teste toutes les paires ; **`verifie tresse`** : aucun croisement.

### L'état et l'action de σ_i

- **`type etat = { trous; lacets }`** : les abscisses des trous et, pour chaque lacet, celles de ses points. Seul
  l'ordre compte.
- **`etat_de_tresse`** : l'état calculé depuis les mots. **`intervalle x trous`** : nombre de trous à gauche de x
  (le `bisect` du Python). **`normalise`** : abscisses remplacées par leurs rangs.
- **`agit etat sigma`** : la torsion de σ_i sur l'état, sans repasser par les mots. Le **bloc** (entre les trous i
  et i + 1) fait un demi-tour :
  1. chaque arc qui sort du bloc (une extrémité dedans, l'autre dehors ou au clou) va s'enrouler et couper l'axe
     une fois de plus : à droite pour un arc du haut avec σ positif, à gauche sinon, l'inverse pour σ⁻¹ ;
  2. de chaque côté, les points nouveaux sont dans l'ordre des extrémités intérieures de leurs arcs (ordre
     d'emboîtement) et placés à intervalles réguliers entre le trou et son voisin (seul l'ordre compte) ;
  3. les points du bloc sont **réfléchis** par rapport à son centre.

  Le résultat est un état **non réduit**. (L'option `detail` du Python n'est pas traduite.)
- **`reduit`** : deux points consécutifs d'un lacet dans le même intervalle bordent un **bigone** (une lentille
  entre l'arc et l'axe, sans trou) : ils s'annulent, avec la même pile que `Reduit.simplifie`.
- **`verifie_action`** : de la tresse vide, `agit` puis `reduit` à chaque lettre, sans jamais calculer de mots ; on
  doit retrouver l'état calculé depuis les mots. La géométrie (`agit`) et l'algèbre (`conjugaison_locale`) disent
  la même chose.

### Le dessin d'un état

- **`demi_ellipse x1 x2 en_haut y_axe aplati`** : demi-cercle de x1 à x2, aplati verticalement.
- **`descente_au_clou xp y_haut y_sous x_clou y_clou`** : arc de cercle depuis le clou, qui arrive à la verticale
  en (xp, y_sous), sous tous les arcs du bas, puis segment vertical jusqu'à l'axe. Le centre est sur l'horizontale
  y_sous (`centre = (d² − h²)/(2d)`) ; trop loin du clou, le cercle devient une ellipse (`etire`). Tous les centres
  étant sur la même horizontale, deux descentes ne se croisent pas.
- **`dessin_etat`** : mise à l'échelle des abscisses, aplatissement (`aplati`, au plus 1) pour que les arcs du
  haut tiennent sous le bord et ceux du bas laissent de la place à l'éventail vers le clou, profondeur `y_sous`
  des descentes, puis pour chaque lacet : descente, demi-ellipses alternées, remontée. (Sans les options `disque`,
  `fusions` et `bosses` du Python, qui ne servent qu'aux anciens films.)
- **`polylignes`** : les morceaux de chaque lacet bout à bout.

---

## 4. Relecture des mots et arcs de cercle (`tresses.ml`, étape 3)

- **`lit_mot points trous`** : chaque trou envoie une demi-droite vers le haut. Un segment qui la traverse de
  gauche à droite note x_j, de droite à gauche x_j⁻¹, dans l'ordre où il les rencontre ; on réduit
  (`Reduit.simplifie`). C'est le contrôle de topologie de tous les tests : le dessin doit redonner les mots de
  `calcule_autofn_de_tresse`.
- **`linspace a b n`** : n valeurs régulières de a à b, la dernière exactement b (comme numpy).
- **`arc_de_cercle p t m`** : l'arc qui part de p avec la tangente t et arrive en m. L'angle tourné est le double de
  l'angle entre t et la corde (angle tangentiel) ; rayon = corde / (2 sin(φ/2)), centre à ce rayon perpendiculairement
  à t ; la corde si l'arc est plat.
- **`raccord_egal p0 t0 p1 t1`** : pour aller de p0 (tangente t0) à p1 (tangente t1) par deux arcs tangents l'un à
  l'autre, il existe toute une famille de raccords ; on prend celui qui est à la même distance d des deux
  tangentes extrêmes (d racine d'une équation du second degré, du premier si les tangentes sont parallèles et de
  même sens) ; `None` si les données sont alignées.
- **`deux_arcs`** : l'arc de p0 au raccord, puis l'arc de p1 au raccord parcouru à l'envers (tangente −t1). Même
  tangente au raccord : la courbe est lisse.

---

## 5. La triangulation (`triangulation.ml`, étape 2)

### Sommets, arêtes, triangles

```ocaml
module Arete : sig type t = private sommet * sommet  val v : sommet -> sommet -> t ... end
module Triangle : sig type t = private sommet * sommet * sommet  val v : ... end
```

- **`Arete.v`**, **`Triangle.v`** rangent les sommets ; comme les types sont privés, c'est le seul moyen d'en
  fabriquer : `Arete.v 7 3 = Arete.v 3 7`. En Python, c'est la convention `(min, max)` répétée à la main et un
  `frozenset`. Le prix : pour lire les deux sommets d'une arête, il faut écrire `(e : Arete.t :> sommet * sommet)`.
- **`Triangle.aretes`** (les trois côtés), **`Triangle.oppose t e`** (le sommet qui n'est pas sur e).
- **`Triangles`**, **`Aretes`** : dictionnaires ordonnés (`Map.Make`), donc parcours déterministes.

### Les courbes posées sur les arêtes

```ocaml
type noeud = Sommet of sommet | Sur_arete of Arete.t * float
type courbe = noeud list
```

Un lacet est une suite de points : le clou au départ et à l'arrivée, sinon un point d'une arête à la fraction w.
Deux noeuds consécutifs sont dans un même triangle (entre eux, une corde). Les arêtes traversées, dans l'ordre,
donnent la topologie ; les fractions ne servent qu'au dessin. Le Python écrit `('v', s)` et `('e', u, v, w)`.

### Le maillage

```ocaml
type t = private { pos : point array; signes : orientation Triangles.t }
type orientation = Direct | Indirect
```

`signes` garde l'orientation de chaque triangle à sa création ; ses clés sont les triangles (le Python garde la
même information deux fois).

- **`cree`** (le constructeur `Maillage(pos, triangles)`), **`deplace`** (mêmes triangles, nouvelles positions),
  **`triangles`**, **`signe`** (orientation actuelle).
- **`aretes`** : pour chaque arête, les triangles qui la bordent (deux à l'intérieur, un au bord).
- **`valide`** : chaque triangle a gardé son orientation. Quand les trous bougent, un triangle qui se retourne
  signale qu'un sommet a traversé une arête au lieu qu'on la retourne à temps.
- **`convexe m a b c d`** : les quatre virages a→b→c, b→c→d, c→d→a, d→a→b tournent dans le même sens (marge 1e-9).
  On ne peut retourner la diagonale que d'un quadrilatère convexe.
- **`cotangente m s x y`** : cot de l'angle en s, (u·v)/|u×v|.

### Le critère de Delaunay

- **`cherche_arete_a_retourner`** : une arête intérieure ac (triangles abc et acd) est de Delaunay si la somme des
  angles opposés en b et d vaut au plus π (d hors du cercle circonscrit à abc), soit cot b + cot d ≥ 0, sans
  calculer d'angle. Candidate : critère violé, abcd convexe, bd pas déjà une arête. La table des arêtes est
  calculée une fois (le Python la recalcule pour chaque candidate). Les triangles de Delaunay sont les plus
  « ronds » : c'est ce qui garde le maillage utilisable quand les trous tournent.
- **`delaunay`** : retourne jusqu'à ce qu'il n'y ait plus rien à retourner (au plus 10 000 flips).

### Le flip et les courbes

- **`position`** : (1 − w)·u + w·v pour un point d'arête.
- **`coupe m u v b d`** : intersection de la corde [u, v] avec bd : p + t·r = pos(x) + w·s, le produit vectoriel
  par r élimine t ; w ramené dans ]0, 1[.
- **`courbe_apres_flip m courbe a b c d`** : on remplace ac par bd sans changer la forme de la courbe.
  1. Chaque noeud reçoit un **côté** : `Cote_a` (a, ou un point de ab ou da), `Cote_c` (c, bc, cd), `Bout_de_bd`
     (b, d), `Ailleurs` (les groupes 0, 1, 2, `None` du Python).
  2. Les points de ac disparaissent : leurs voisins sont reliés directement, dans le quadrilatère.
  3. Entre deux noeuds consécutifs de côtés opposés, la corde traverse bd : on insère le point de coupe. Le
     filtrage `Cote_a, Cote_c | Cote_c, Cote_a -> …` le dit directement.
- **`retourne`** : retire abc et acd, ajoute abd et bcd, transforme les courbes ; rend le nouveau maillage
  (`{ m with signes }` partage le tableau `pos`).

### Le maillage de départ

- **`decalage_axe`** (0,01) et **`decalage_bord`** (0,31) : l'axe un peu sous les trous, les sommets des bords un
  peu à côté de leur verticale.
- **`echelle x r1 r2`** : découpe la bande entre deux rangées triées en triangles, comme une fermeture éclair, en
  avançant sur la rangée dont le point suivant est le plus à gauche (les trois cas du filtrage sont les trois
  branches du Python).
- **`maillage_initial`** : points créés dans l'ordre du Python (mêmes indices), deux bandes (bord haut → axe,
  axe → bord bas avec le clou), puis `delaunay`. Rend un enregistrement `{ maillage; trous; clou; haut; bas }` au
  lieu d'un tuple à cinq éléments. `hauteur` ne sert pas, comme en Python (`_hauteur`).

### De la polyligne à la courbe

- **`noeuds_de_polyligne points maillage clou`** : intersections de la polyligne avec toutes les arêtes (p + t·r =
  u + w·s, t et w dans [0, 1[), sauf celles du premier et du dernier segment avec les arêtes du clou. Triées dans
  l'ordre du parcours ; deux coupes successives de la même arête bordent un bigone vide et s'annulent (pile). La
  courbe part du clou et y revient.

---

## 6. Le film (`film.ml`, étapes 3 et 3 bis)

### Constantes et types

- **`sens_de_sigma`** (1 : σ_i positif tourne dans le sens horaire à l'écran, y vers le bas),
  **`vitesse_par_defaut`** (6 pixels par image pour les trous, à 800 pixels de large).
- **`disposition = { abscisses; ecart }`** (le tuple `(xs, ecart)` du Python).
- **`t`**, le film : dimensions, dispositions des images clés et des milieux de lettre, étape courante, maillage,
  `trous.(j)` (le sommet à la place j), clou, bords, place du clou, axe, courbes. Les attributs de `self` en Python ;
  ici chaque fonction rend un nouveau `t`.

### `monotone` : régression monotone

La suite **croissante** la plus proche (moindres carrés) d'une suite de valeurs : on empile des blocs (moyenne,
effectif) et l'on fusionne les deux derniers tant que l'avant-dernier est au-dessus du dernier. Le filtrage
`(b, nb) :: (a, na) :: reste when a > b` se lit « le dernier est b, l'avant-dernier a, et a > b ».

### `tend` : un pas de tension

**Premier temps, ce que chaque point voudrait** (tout est calculé sur l'état de départ) :

- **la cible** : l'endroit de l'arête où le point et ses deux voisins seraient alignés (intersection de la corde
  [p, q] avec l'arête). Un brin dont chaque point se rapproche de cet alignement se tend comme un élastique ;
- **le souhait** : `w + taux·(cible − w)`, une fraction du chemin seulement, pour une tension progressive ;
- **le sinus** de l'angle de traversée (avec la corde [p, q], ou des points plus lointains si `portee_sinus` > 0 :
  dans un éventail de triangles très minces, les voisins immédiats donnent une direction bruitée).

**Second temps, arête par arête** :

- tri par souhait : l'ordre le long de l'arête ne change jamais, d'où l'absence de croisements ;
- écart voulu entre deux voisins le long de l'arête : `ecart / sinus` (sinus borné à 0,3), pour qu'ils restent à
  `ecart` l'un de l'autre perpendiculairement aux brins ; marge aux sommets ; si la place manque, tous les écarts
  sont réduits dans la même proportion ;
- **l'astuce** : on retire à chaque souhait le cumul des écarts qui le précèdent. « Croissant avec des écarts
  imposés » devient « simplement croissant » : `monotone`, bornes, puis on rajoute les cumuls.

Les brins se tassent à écart fixe là où ils sont tirés, près des trous, et laissent du vide ailleurs.

### Le mouvement des trous

- **`abscisses film u`** : de l'image clé à la disposition du **milieu** de la lettre (qui fait de la place aux
  brins qui font le tour de la paire), puis du milieu à l'image clé suivante ; linéaire exprès (une courbe adoucie
  arrêterait les trous au milieu et aux bouts de la lettre).
- **`trous_au_temps film sigma u`** : les deux trous de σ_i tournent autour de leur milieu d'un angle ±π·u ; les
  autres restent sur l'axe.
- **`place film sigma u`** : pose les trous ; les sommets des bords au-dessus et au-dessous de la paire se croisent
  **sans se rejoindre** (écart √((r cos θ)² + (0,4 r sin θ)²), jamais nul) ; le clou garde sa place relative ; à
  u = 1, les deux trous sont posés exactement et échangent leurs places, l'étape avance.
- **`chemin_des_trous`** : longueur cumulée du chemin des trous sur 801 instants (la table longueur → temps).
- **`interp`** (le `np.interp` du Python) et **`arrondi`** (le `round` du Python, à l'entier pair en cas
  d'égalité) : reproduits pour obtenir les mêmes nombres.

### `lettre` : jouer un σ_i

- nombre d'images : longueur du chemin / vitesse (au moins 4) ;
- **vitesse constante** : on découpe la *longueur* du chemin, pas le temps, en morceaux égaux, convertis en temps
  par `interp` ; le dernier temps est exactement 1 ;
- à chaque sous-pas : écart du moment (lu avant `place`), `place`, contrôle qu'aucun triangle ne s'est retourné
  (sinon les pas sont trop grands : erreur), `delaunay` (les flips mettent les courbes à jour), `tend`, et `rendu`
  tous les `sous_pas` sous-pas.

### Le dessin

- **`portions_du_clou`** : les points au-dessus de l'axe (y ≤ y_axe), le premier et le dernier encadrent les
  passages de l'axe ; pour chaque bout attaché au clou, les indices qui le précèdent (ou le suivent) et l'abscisse
  du passage.
- **`polyligne film k`** :
  - sans lissage, la ligne brisée des noeuds ;
  - avec lissage, d'abord les **départs perpendiculaires** : à chaque passage de l'axe d'un brin du clou, deux
    points de part et d'autre de l'axe, dans une direction mélangée entre la verticale et celle du brin (vers la
    verticale si le brin traverse à moins de 45° d'elle ; sinon on suit le brin, pour ne pas créer de cran pendant
    un demi-tour). On insère du dernier passage au premier pour ne pas décaler les indices ;
  - puis les **congés** : chaque coin v entre a et b est remplacé par `deux_arcs`, tangents aux deux segments, sur
    au plus la moitié du plus court (deux congés voisins se touchent sans se chevaucher). Le dessin n'est fait
    que de droites et d'arcs : les petits coudes réguliers autour d'un trou forment un cercle, un brin tendu reste
    droit jusqu'à son coude.
- **`mots`** : trous triés par abscisse, puis `lit_mot` sur chaque polyligne.

### Le constructeur

- **`disposition nb_trous largeur etat`** : chaque intervalle de l'axe a une largeur proportionnelle à 1 + le
  nombre de brins qui le traversent ; l'écart entre deux brins voisins est le même partout.
- **`cree tresse`** (le `Film.__init__` du Python) :
  1. dispositions des images clés (chaque préfixe) et des milieux de lettre (état **non réduit**, qui compte les
     brins passant de part et d'autre du bloc pendant le demi-tour) ;
  2. dessin de la tresse vide (`dessin_etat`), replacé sur la disposition 0 par une interpolation affine par
     morceaux des abscisses ;
  3. décalage du bord bas loin du clou, maillage de départ, place relative du clou ;
  4. dessin étiré au-dessus de l'axe pour remplir la bande du haut ;
  5. courbes posées sur le maillage (`noeuds_de_polyligne`), puis `?tension` pas de `tend` (400 par défaut, comme
     le Python, qui n'a pas cet argument).

---

## 7. Le dessin et le film (`dessin/dessin.ml`, étape 5)

Une bibliothèque à part, `dessin`, la seule qui dépende de cairo2 : `ardoise` et ses tests compilent sans Cairo.
cairo2 demande la bibliothèque C (`sudo apt install libcairo2-dev pkg-config`), puis `opam install cairo2`.

- **`peint`** : fond blanc, arêtes en gris dessous (`?axe`), lacets en couleur, trous et clou en disques noirs. Les
  appels Cairo sont ceux du Python (`move_to`, `line_to`, `stroke`, `arc`, `fill`), avec un contexte explicite.
  Le Python accepte aussi des morceaux d'axe avec leur opacité : ils ne servent qu'aux anciens films.
- **`cadre`** : l'image du film à un instant (`Film.cadre` du Python). Les arêtes viennent de `Maillage.aretes` ; une
  `Arete.t` est privée, `(a :> int * int)` la lit comme une paire sans pouvoir en fabriquer une.
- **`film_triangule`** : ffmpeg est lancé par `Unix.open_process_args_out`, et chaque image part brute (BGRA, le
  format en mémoire d'une surface Cairo ARGB32) par `Unix.write_bigarray` sur le descripteur du tube, sans copie
  dans une chaîne. Le rendu passé à `Film.lettre` garde l'image précédente et l'écrit quand la suivante arrive :
  la dernière du film, seule, est répétée pendant la pause finale. Les pauses comptent leurs images avec
  `Film.arrondi` (le `round` du Python, au pair : 12 images pour 0,5 s).
- **`bin/films.ml`** : le `__main__` du Python, `dune exec bin/films.exe` depuis `ocaml/` (ffmpeg dans le PATH, ou
  dans la variable `FFMPEG`). Il écrit `imgs/film_triangule_*_ocaml.mp4`.

Les deux films sont identiques octet pour octet à ceux du Python. Il a fallu tracer les arêtes grises dans le même
ordre des deux côtés (l'ordre rangé, `Aretes.bindings`) : là où deux arêtes se recouvrent, le gris anticrénelé,
arrondi à 8 bits, dépend de l'ordre de tracé. Une vingtaine de pixels différaient d'un niveau sur 255, et cela
suffisait pour que l'encodeur AV1, avec perte, fasse d'autres choix sur toute l'image. Le film prend 6 s au lieu de 12 : le calcul ne compte presque plus, l'essentiel est
le dessin et l'encodage AV1.

---

## 8. Les films d'arcs (`raccord.ml`, `arcs.ml`, étape 4)

### Le maillage à bord convexe (`raccord.ml`)

- **`maillage_du_raccord`** : un bord convexe (rectangle bombé de 40 px hors de l'image, 6 points par côté) en
  éventail de triangles, puis les trous insérés un à un de gauche à droite, puis `delaunay`. Les indices des trous
  suivent l'ordre d'insertion, pas celui de la liste : la fonction rend aussi l'indice de chaque trou.
- **`insere`** : le triangle qui contient le point est coupé en trois ; s'il est sur une arête, les deux triangles
  qui la bordent sont coupés en deux. Le Python modifie le maillage en place ; ici on rebâtit un maillage
  (`Maillage.cree`), ce qui recalcule les orientations : elles n'ont pas changé, les sommets n'ayant pas bougé.

### Arcs et diagramme (`arcs.ml`)

- **Pas d'héritage.** En Python, `FilmArcs` hérite de `Film` et neutralise son clou (`y_axe = -inf`) pour garder
  la tension et le dessin. Ici, `Film` expose ces deux fonctions sur un maillage et des courbes (`tend_courbes`,
  `polyligne_de_courbe`, sans clou par défaut), et `Arcs.t` est un enregistrement à lui, sans champ inutile.
  `DiagrammeCourbes`, qui hérite de `FilmArcs` en Python, est le même type avec `genre = Diagramme` : seuls le
  constructeur (`cree_diagramme`) et `mots` (le seul premier arc) diffèrent.
- **`coupe_arc`** : la polyligne de départ devient une courbe posée sur le maillage. Toutes les traversées
  d'arêtes, rangées le long de la polyligne ; une pile annule les bigones (deux traversées successives de la même
  arête) ; on retire en tête et en queue les traversées des arêtes qui touchent les bouts (un arc peut tourner
  autour de ses extrémités sans changer de classe).
- **`pchip`, `hermite`** : les largeurs des intervalles de l'axe glissent d'une image clé à l'autre par une
  interpolation cubique monotone, donc toujours positives : deux trous ne s'inversent jamais. `hermite` calcule
  u³ par `Float.pow`, comme le `u**3` du Python (un seul arrondi).
- **`lettre`**, **`ruban`**, **`mots`** : traductions directes. Le ruban est le bord d'un voisinage de l'arc,
  dont la largeur s'annule près du trou fixe ; on y relit le lacet x_i (`lit_mot`).
- La tension hyperbolique (`hyperbolique=True`, `python/Geodesiques.py`) n'est pas traduite.

### L'ordre des retournements d'arêtes

`delaunay` retourne la première arête mauvaise qu'il trouve. Quand plusieurs arêtes sont à retourner au même
sous-pas, l'ordre compte : chaque retournement retire les points de l'arête retournée, donc les courbes finales
diffèrent (jusqu'à 3 % d'une arête, que la tension efface peu à peu), et avec les points alignés de l'axe
(cocycliques) la triangulation elle-même peut différer. Le Python parcourait les triangles dans l'ordre d'un `set`
de `frozenset`, qui dépend de l'historique des insertions (il change même après un `deepcopy`) : son
`cherche_arete_a_retourner` suit maintenant l'ordre de l'OCaml (arêtes rangées ; pour les deux triangles d'une
arête, le plus grand d'abord, comme la liste que construit `Maillage.aretes`). La comparaison est exacte à 1e-9
près, au départ et lettre par lettre.

### Le dessin

`Dessin.cadre_arcs` et `Dessin.film_arcs`, et `bin/arcs.ml` (le `__main__` de `Arcs.py` : vérification des mots,
puis `imgs/<méthode>/film_*_ocaml.mp4`). Les six films (rubans, rubans à gauche, diagramme, sur les deux tresses
d'essai) sont identiques octet pour octet à ceux du Python, en 21 s au lieu de 55.

## 9. L'escargot (`escargot.ml`, étape 6)

Premier film « chorégraphie libre » en OCaml : pas de tresse, les trous voyageurs suivent des chemins donnés en
fonction du temps (`choregraphie`), et la triangulation mobile emporte les arcs. En Python, `Escargot` hérite de
`FilmArcs` ; ici c'est un type à part, qui n'appelle que les outils dont il a besoin : `Arcs.coupe_arc` pour les
demi-ellipses de départ, `Raccord.maillage_du_raccord`, `Film.tend_courbes`, `Film.polyligne_de_courbe`.

`deplace` amène les trous aux positions de l'image suivante en ligne droite, par sous-pas d'au plus 2 px (le plus
long des déplacements), avec retournements d'arêtes et un pas de tension à chaque sous-pas : c'est `Arcs.lettre`
sans le demi-tour. Les formules suivent l'ordre des opérations du Python (`a * (x, y) * e` est `(a x) e`), et le
dessin (`Dessin.cadre_escargot`) refait les mêmes appels Cairo, jusqu'à l'arc ajouté au rectangle sans nouveau
chemin pour le masque du corps : le film `imgs/escargot/film_ocaml.mp4` (`dune exec bin/escargot.exe`) est
identique octet pour octet à celui du Python, en 4,5 s au lieu de 8,4.

---

## 10. La carte de Schwarz–Christoffel (`conforme.ml`, étape 7a)

Le film conforme dessine les lacets sur une ligne brisée L–A–B–R (l'axe plié par le demi-tour). Pour cela il lui faut
une **représentation conforme** : une transformation du demi-plan supérieur (la variable w) sur la région au-dessus
de la ligne brisée (la variable z), qui conserve les angles. La formule de Schwarz–Christoffel la donne par sa
dérivée :

  dz/dw = Π (w − w_k)^β_k

où les w_k sont les antécédents (réels) des sommets V_k, et β_k = −(angle dont tourne le bord en V_k) / π. Loin des
sommets, z ≈ w + constante : la carte est presque une translation. Toute la difficulté est de trouver les w_k.

**Outils numériques** (les fonctions numpy dont la carte a besoin) :

- **`linspace`**, **`interp`**, **`cumul_depuis_zero`** : `np.linspace`, `np.interp`, et la somme cumulée précédée
  d'un 0. Écrits pour donner exactement les mêmes nombres que numpy (même formule, même ordre des additions).
- **`resous`** : `np.linalg.solve`, la résolution d'un petit système linéaire par l'élimination de Gauss avec pivot
  partiel (au plus trois inconnues ici).

**La carte** (`type carte`, un enregistrement : sommets, longueurs et directions des segments, β, écarts et
antécédents des sommets, tables du bord, delta). C'est la classe `Carte` du Python, construite par `cree` au lieu
de `__init__`.

- **`module_sans beta w t sauf`** : |dz/dw| en des points réels t, sans le facteur du sommet `sauf`.
- **`depuis beta w k sens d n`** : la table du bord à partir de w_k, sur une distance d : des antécédents t et la
  longueur parcourue sur le bord. Près de w_k, |dz/dw| ~ |w − w_k|^β_k est singulier (infini si β_k < 0) ; le
  changement de variable t = w_k + sens · d · s^q, avec q = 1 / (1 + β_k), le rend régulier, et la méthode des trapèzes
  en s suffit.
- **`cotes beta ecarts n`** : les longueurs des segments que donneraient ces écarts entre antécédents (chaque segment
  intégré par ses deux moitiés, depuis chacune de ses extrémités, pour éviter les deux singularités à la fois).
- **`tables_du_bord`** : les tables de tous les morceaux du bord : la demi-droite de gauche, chaque segment (ses deux
  moitiés recollées, puis remises à l'échelle de la vraie longueur du segment), la demi-droite de droite.
- **`cree ?ecarts sommets`** : β à partir des directions des segments ; puis la **méthode de Newton** sur les
  logarithmes des écarts (pour qu'ils restent positifs), jacobienne par différences finies, pas borné à 1, jusqu'à
  ce que les longueurs calculées égalent les vraies à 1e-11 près ; enfin les tables et delta (z − w loin à droite).
  `ecarts` : point de départ (le film réutilise ceux de l'image précédente, presque justes). Lève
  `Pas_de_convergence` après 80 itérations.
- **`antecedent_bord carte morceau longueur`** : l'antécédent réel d'un point du bord, par interpolation dans la
  table du morceau.
- **`bord carte t`** : l'inverse, le point du bord image du réel t.
- **`derivee carte w`** : dz/dw en un point du demi-plan (partie imaginaire ramenée à ≥ 0, et `+. 0.` pour éviter le
  −0, dont l'argument serait −π au lieu de π).
- **`chemin ?z1 carte ws z0`** : les images d'un chemin du demi-plan, en intégrant dz/dw pas à pas (méthode du point
  milieu) depuis z0, image du premier point. Si l'on connaît aussi z1, l'image du dernier point (les deux pieds d'un
  arc, sur le bord), l'erreur d'intégration est répartie le long du chemin, au prorata de la longueur parcourue.
- **`image carte w`** : l'image d'un point intérieur ; on y va en ligne droite depuis un point du bord choisi loin des
  antécédents des sommets (partir d'une singularité rendrait l'intégration bruitée).
- **`antecedent carte z`** : l'inverse, par la méthode de Newton (w ← w − (image(w) − z) / dz/dw), arrêtée à 1e-4 près.
- **`demi_cercle ?n w0 w1`** : le demi-cercle du demi-plan entre deux réels, points resserrés aux extrémités. Un arc
  du film est l'image par `chemin` du demi-cercle entre les antécédents de ses deux pieds : il arrive
  perpendiculairement au bord, et deux arcs ne peuvent pas se croiser (la carte est une bijection).

**Le module d'un complexe** (`module_c`) se calcule par `Float.hypot`, comme `np.abs` ; `Complex.norm` d'OCaml
emploie une autre formule, qui diffère parfois au dernier chiffre.

**Choix OCaml.** Les nombres complexes sont ceux du module `Complex` de la bibliothèque standard ; la carte est un
enregistrement immuable (le Python la modifie en place pendant sa construction). Les boucles de numpy deviennent des
`Array.map` et des boucles `for` sur des tableaux locaux, qui ne sortent pas des fonctions.

**Vérification** (`test/test_conforme.ml`, références de `test/genere_reference_conforme.py`) : 16 vraies cartes du
film (tresse de référence, lettres 1 et 5, quatre instants, haut et bas). β, écarts, antécédents des sommets, delta,
points du bord, images de points intérieurs et demi-cercles emportés concordent avec le Python à 1e-11 près ; les
antécédents de points intérieurs à 1e-3 près (Newton s'arrête à 1e-4).

## 11. Une lettre du film conforme (`conforme.ml`, étape 7b)

Une lettre σ_i va de l'image clé k (l'état `cle`) à l'image clé k+1 (l'état `suivante`). Pendant le demi-tour, les
trous i-1 et i (de 0) tournent ; l'axe se plie en ligne brisée L–A–B–R par leurs voisins.

- **`type lettre`** et **`lettre ?hauteur ?largeur cle suivante sigma`** : la classe `Lettre` du Python. Elle garde
  les deux états, leur géométrie de dessin (`Tresses.geometrie_etat`, sortie pour l'occasion de `dessin_etat`), les
  abscisses à l'écran des trous, et `phys` : le trou physique à chaque place (les places i-1 et i sont échangées dans
  l'état k+1). Le seul champ mutable est `cache` : les écarts de la dernière carte de chaque état, point de départ de
  Newton pour l'image suivante. Le Python modifie aussi `reduction` en place ; ici elle est passée en argument.
- **`trou l p s`** : la position du trou physique p au temps s. Les trous immobiles glissent de leur place dans
  l'image clé k à leur place dans l'image clé k+1 ; les deux trous qui tournent font un demi-tour autour de leur milieu,
  dans le sens donné par le signe de σ. Les places -1 et n sont des points virtuels au bord de l'image.
- **`ligne l e s`** : les quatre sommets de la ligne brisée de l'état e : L, A, B, R.
- **`type pied`**, **`pied l e x s v`** : où poser un point de l'état sur la ligne brisée. Un point d'un des trois
  intervalles du bloc va sur le segment correspondant, à la même fraction ; les autres restent sur l'axe, à la même
  place relative entre les trous qui les encadrent. Le pied dit sur quel morceau du bord il est (0 à 4) et à quelle
  longueur : c'est ce qu'il faut pour son antécédent (`antecedent_bord`).
- **`cartes l e s`** : les cartes du haut et du bas (la ligne brisée symétrique), Newton parti du cache.
- **`aplati l ~reduction s`** : l'aplatissement vertical, mélange de ceux des deux images clés, multiplié par la
  réduction (le film la fixe quand les arcs sortiraient du cadre).
- **`dessin l ~reduction e s`** : les lacets de l'état e à l'écran. Chaque arc est l'image d'un demi-cercle entre les
  antécédents de ses pieds, par la carte du haut (arcs pairs) ou du bas (arcs impairs). Les deux bouts descendent au
  clou par des **géodésiques** du demi-plan du bas : l'arc du cercle orthogonal à l'axe qui passe par le pied et par
  l'antécédent du clou. Deux de ces cercles ne se recoupent qu'au clou, et le clou doit être hors des demi-cercles du
  bas (`Clou_dans_un_demi_cercle` sinon) : les descentes ne croisent rien.
- **`trous_ecran l ~reduction s`** : les trous à l'écran.

**Vérification** : 64 lettres (chaque lettre des deux tresses d'essai, à quatre instants), sur une lettre neuve à
chaque fois (cache vide des deux côtés). Lignes brisées, pieds, aplatissements, trous et points des dessins
concordent avec le Python à 1e-10 près ; au-delà, les puissances complexes de la carte diffèrent de numpy au dernier
chiffre.

## 12. Le raccord par triangulation (`raccord.ml`, étape 7c)

À mi-chemin d'une lettre, le film conforme passe du dessin de l'état k (sur L–A–B–R) au dessin de l'état k+1 (sur
L–B–A–R). Ce passage se fait sur une triangulation mobile, dont les sommets sont un bord convexe hors de l'image,
les trous et le clou.

- **`transporte lignes triangles avant apres`** : l'image des lignes par l'application **affine par triangles** qui
  envoie les positions `avant` sur `apres` : pour chaque point, le triangle qui le contient (le plus « intérieur »
  s'il est sur une arête : la plus grande des plus petites coordonnées barycentriques), puis les mêmes coordonnées
  barycentriques dans le triangle déplacé. C'est une déformation continue du plan (une isotopie) : des lignes sans
  croisement le restent. Le Python ordonne les triangles comme son ensemble (`set`), l'OCaml dans l'ordre rangé ; ils
  ne diffèrent que pour un point posé exactement sur une arête, où les deux triangles donnent la même image.
- **`type traversee`**, **`coupe points maillage clou`** : les traversées des arêtes par un lacet, classées le long
  du lacet. Un point est d'un côté ou de l'autre d'une arête (un point posé dessus compte toujours du même côté) : une
  traversée est un changement de côté, jamais doublée ni manquée. La suite réduite annule les bigones (deux traversées
  successives d'une même arête) et ne garde pas les traversées des arêtes du clou en tête et en queue : le clou est le
  point base, un lacet peut tourner autour en partant. Les sommets étant des trous, cette suite réduite est la même
  pour les deux dessins d'un même lacet : leurs pieds se correspondent un à un.
- **`point_en`**, **`morceau`**, **`reechantillonne`** : un point, un morceau, et un rééchantillonnage régulier d'une
  polyligne.
- **`arrondit`** : la ligne brisée des pieds, chaque coude arrondi par un congé (deux arcs tangents, `deux_arcs`), les
  jonctions avec les morceaux restés courbes faites en tangence, et chaque arrondi tenu à l'écart des trous (dans un
  disque de 0,9 × la distance au trou le plus proche).
- **`decoupe_aux_aretes`** : coupe une polyligne à ses traversées successives d'arêtes données.
- **`raccord ... ()`** (`RaccordTriangule.__init__`) : les instants du transport (les images de la fenêtre et des
  sous-pas entre elles) ; le maillage qui suit les trous d'instant en instant en retournant ses arêtes (un triangle
  retourné entre deux sous-pas est une erreur) ; le dessin de départ transporté vers l'avant, celui d'arrivée vers
  l'arrière. Le type `raccord` est abstrait ; **`reduction r s`** donne la réduction interpolée.
- **`lignes r f poids`** : les lacets de l'image f. Dans chaque triangle, les morceaux de lacet passent soit par les
  cordes (tension, glissement des pieds sur leurs arêtes, courbure), soit directement du départ à l'arrivée ; le choix
  se fait par triangle (une corde et une courbe du même triangle se croiseraient) : les cordes pour les triangles qui
  touchent un trou qui tourne ou contiennent un bigone. Les mélanges se font triangle par triangle (un triangle est
  convexe, et ses sommets sont des trous : un mélange ne peut pas passer par-dessus un trou).

**Vérification** : deux raccords capturés pendant le vrai film Python (lettres 1 et 5 de la tresse de référence, la
seconde avec une réduction qui varie), reconstruits en OCaml à partir des mêmes entrées : mêmes anomalies (aucune),
mêmes nombres de points, points à 1e-11 près sur les 34 images.

## 13. Le film conforme (`film_conforme.ml`, `Dessin.film_conforme`, étape 7d)

Le `film_conforme` du Python est coupé en deux, comme les autres films : le calcul des images dans
`lib/film_conforme.ml` (un module à part, parce que `Raccord` dépend déjà de `Conforme`), le dessin et l'écriture du
MP4 dans `dessin/dessin.ml`. Seul le raccord par triangulation (le défaut) est traduit ; ni le mélange
(`raccord='melange'`), ni le tracé des arêtes de construction, ni le GIF.

- **`film ~hauteur ~largeur ~marge ~rendu tresse`** : la première image est l'image clé 0, dessinée par la carte ;
  puis, pour chaque lettre, 48 images aux temps `lisse (n / 48)`. Hors de la fenêtre (poids 0 ou 1), l'état k ou
  k+1 dessiné par la lettre, aplati davantage si des arcs sortent par le haut (`dessin_reduit` rend les lignes et la
  réduction ; en Python, `lettre.reduction` est un attribut modifié en place, ici un argument). Dans la fenêtre, le
  raccord est construit à la première image, avec la dernière image avant la fenêtre (`precedent`) et la première
  après (dessinée d'avance) ; chaque image de la fenêtre en est tirée (`Raccord.lignes`). `rendu` reçoit chaque
  image au fil du calcul : rien n'est gardé en mémoire.
  Les appels à la carte se font dans l'ordre du Python : le cache des écarts de la lettre se remplit dans le même
  ordre, et les derniers chiffres des dessins en dépendent.
- **`verifie`** : sur chaque image hors de l'instant où les trous qui tournent sont l'un au-dessus de l'autre, les
  mots relus (`lit_mot`, trous rangés par abscisse) doivent être ceux de l'image clé k ou k+1 ; et
  **`nb_croisements`** compte les croisements entre lacets distincts, loin du clou, par paquets de 64 segments dont
  on ne compare que ceux dont les rectangles englobants se chevauchent.
- **`Dessin.film_conforme`** : chaque image est peinte par `peint` après le décalage de la marge, et envoyée à
  ffmpeg ; la première dure 500 ms (12 images à 25 par seconde), la dernière 1,5 s (38), les autres 40 ms.

**Vérification** : `dune exec bin/conforme.exe` écrit les deux films (800 × 800, marges de 60) avec vérification :
0 anomalie, et des MP4 identiques octet pour octet à ceux du Python (avec le même ffmpeg), en 41 s au lieu de
1 min 35. `nb_croisements` est aussi testé sur des cas faits à la main.

## Annexe : pourquoi l'OCaml est au moins 15 fois plus rapide

Les 16 lettres des deux films d'essai prennent 4,5 s en Python, moins de 0,3 s en OCaml, avec le même algorithme
(mêmes nombres au dernier bit près). Le profil du Python : `tend` 86 % du temps, `position` appelée 1,26 million de
fois, `croix` 1,5 million.

1. **numpy n'aide pas sur des vecteurs à deux coordonnées** : l'algorithme avance point par point, et chaque
   `pos[v] - pos[u]` crée un objet tableau pour deux nombres (allocation, vérification des types : un coût fixe
   cent fois plus grand que le calcul).
2. **Python interprète, OCaml compile** : les types sont connus à la compilation, chaque opération devient une
   instruction machine, et `{ x; y }` est rangé à plat.
3. **Les appels de fonction coûtent cher en Python** ; le compilateur OCaml remplace les petites fonctions
   (`croix`, `-:`, `scalaire`) par leur corps.
