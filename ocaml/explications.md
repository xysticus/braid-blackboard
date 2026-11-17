# Le code OCaml, fonction par fonction

Réécriture en OCaml des algorithmes de l'ardoise à tresse (voir [`plan_ocaml.md`](../plan_ocaml.md)). Chaque
fonction porte le nom de la fonction Python qu'elle traduit ; quand la signature diffère (argument, effet de bord),
le `.mli` le dit.

| Module | Traduit | Étape du plan |
|---|---|---|
| [`lib/geometrie.ml`](lib/geometrie.ml) | les opérations numpy sur les points | 3 |
| [`lib/tresses.ml`](lib/tresses.ml) | `programmes/tresses.py` : groupe libre, action d'Artin, méandre, relecture, arcs | 1, 3, 3 bis |
| [`lib/triangulation.ml`](lib/triangulation.ml) | `Maillage`, `maillage_initial`, `noeuds_de_polyligne` de `programmes/Triangulation.py` | 2, 3 bis |
| [`lib/film.ml`](lib/film.ml) | la classe `Film` de `programmes/Triangulation.py` | 3, 3 bis |

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
