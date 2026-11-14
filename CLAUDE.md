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
- `programmes/tresses.py` : **base commune** importée par les deux scripts suivants : mots de F_n et action d'Artin
  (`calcule_autofn_de_tresse`), état d'un méandre (`intervalles`, `abscisses`, `etat_de_tresse`), action algébrique
  de σ_i (`agit`, `reduit`), dessin d'un état (`dessin_etat`, `peint`, `image_auto_de_tresse`), relecture des mots
  (`lit_mot`), arcs de cercle raccordés (`deux_arcs`), images (`en_image_pil`, `gif_en_mp4`). Ses `assert` tournent
  à chaque import (rapide).
- `programmes/NouvAutoMorph.py` : films successifs à partir de l'état (image par image, algébrique, simultané, essais
  en arcs) : voir plus bas. `from tresses import *` ; lancé (`__main__`), il écrit ses images et ses films.
- `programmes/Triangulation.py` : **le film actuel** (triangulation mobile, point 11 plus bas), `film_triangule`.
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
   Le dessin passe par `dessin_etat(etat_de_tresse(...))` (polylignes numpy, positions des trous et du clou) et
   `peint` (trace les polylignes). `lit_mot` relit le mot d'un lacet dessiné (traversées des demi-droites qui montent
   des trous) ; `verifie_dessin` contrôle ainsi le dessin contre les mots.
7. **Action algébrique de σ_i sur l'état** (`agit`, `reduit`) : l'état est fait des abscisses des trous et, pour chaque
   lacet, des abscisses de ses points sur l'axe (seul l'ordre compte ; `etat_de_tresse` le calcule depuis les mots,
   `normalise` le ramène aux rangs). σ_i fait tourner d'un demi-tour le bloc (trous i, i+1 et intervalle i) :
   les points du bloc sont réfléchis ; chaque arc qui sort du bloc (ou descente au clou) reçoit un point nouveau,
   pour σ_i positif à droite du bloc si c'est un arc du haut, à gauche sinon (l'inverse pour σ_i⁻¹) ; d'un même côté,
   les points nouveaux sont dans l'ordre des extrémités intérieures de leurs arcs. Puis `reduit` supprime les bigones
   (deux points consécutifs d'un lacet dans le même intervalle). `verifie_action` part de la tresse vide et applique
   les lettres sans les mots : on retrouve l'état des mots à chaque pas (testé aussi sur 300 tresses aléatoires ;
   le test échoue si l'on inverse la règle du côté ou de l'ordre).
8. `film_de_tresse_algebrique(tresse, fichier)` → `imgs/film_continu_*.gif` : chaque lettre est une suite de
   mouvements élémentaires sur l'état, dessinés par `dessin_etat` (demi-ellipses entre abscisses réelles, place
   réservée au disque du demi-tour, fusions en cours) : (1) réespacement vers `mise_en_page_avec_marge` (couronne vide
   autour du bloc) ; (2) `demi_tour` : rotation rigide du bloc, amortie dans la couronne, faite avant aplatissement ;
   seuls les arcs qui sortent du bloc s'enroulent, les autres lacets ne bougent pas ; hors de la couronne l'axe
   ne bouge pas, le segment i tourne avec les trous, les morceaux des segments voisins accrochés aux deux trous
   (voués à disparaître) sont emportés par le centre de rotation : ils tournent et glissent vers lui en rétrécissant,
   pendant que les nouveaux poussent depuis le bord de la couronne
   (`axe_pendant_demi_tour`) ; (3) retouche morceau par morceau
   vers le dessin de l'état non réduit, dont les points nouveaux sont là où les arcs tordus coupent l'axe
   (`coupe_sur_l_axe` ; un `assert` vérifie que cet ordre est celui de `agit`) ; (4) vagues de bigones
   (`bigones_interieurs`, `retire_bigones`) : ce sont les segments de l'axe qui travaillent ; le segment se bombe
   par-dessus (ou par-dessous) le capuchon, lacets immobiles (`bosses` de `dessin_etat`, demi-ellipse qui englobe le
   capuchon et s'arrête avant les voisins sur l'axe : `marges_des_bigones`), puis redescend en l'écrasant (les deux
   points glissent l'un vers l'autre) ; ensuite balayage exact de la région vide (`fusion_arcs`, `fusion_descente`) ;
   (5) réespacement vers l'image clé (un `assert` vérifie l'état). L'axe est tracé en gris sous les lacets (`peint`).
   Pourquoi pas « lacets figés, puis tout aplatir à la fin » : un bigone peut former un doigt qui passe sous un trou
   voisin ; le segment, accroché à ce trou, ne peut pas le contourner en restant un graphe y = f(x).
   Les segments ne peuvent pas non plus faire le demi-tour : σ_i échange les trous i et i+1, le segment i-1
   devrait changer d'extrémité.
   Réespacer ne crée jamais de croisement : deux demi-cercles se croisent ssi leurs extrémités s'entrelacent.
   Sens : σ_i positif = demi-tour horaire à l'écran (`SENS_DE_SIGMA = 1`, y vers le bas) ; l'`assert` sur l'ordre
   des points nouveaux échoue avec l'autre sens.
9. `film_de_tresse_simultane(tresse, fichier)` → `imgs/film_simultane_*.gif` : **un seul mouvement par lettre**,
   rien ne reste à régler une fois les trous en place (ni bigone à résorber, ni réespacement).
   - Pas de mou : un bigone de l'état non réduit est toujours (point nouveau, bout extérieur Q de son arc), avec Q
     dans l'intervalle voisin du bloc, du côté où l'arc s'enroule ; ces Q sont les points les plus proches du bloc
     (un `assert` le vérifie). `mise_en_page_du_demi_tour` les range avant de tordre : les « doigts » (les deux arcs
     de Q vont dans le bloc) entrent dans le disque rigide, les « passants » (un seul arc) dans la couronne, où ils
     ne tournent qu'en partie et quittent l'axe. Tous les brins traversent la couronne en s'éloignant du centre :
     la torsion les enroule sans créneaux.
   - Deux dessins du même instant u : D_u = H_u(image clé k rangée pour σ), A_u = H_(u-1)(image clé k+1 rangée pour
     σ⁻¹) (`dessin_pendant_demi_tour`). Les passants de l'un sont les points nouveaux de l'autre ; les points communs
     ont les mêmes abscisses dans les deux rangements. L'image est leur mélange de poids u entre points communs
     (`entre_points_communs`). Le rangement se fait pendant le premier tiers de la rotation, le retour aux
     abscisses de l'image clé pendant le dernier (`part_du_rangement`).
   - `verifie=True` relit le mot de chaque lacet sur chaque image (`lit_mot`, trous triés par abscisse : mots de
     l'image clé k avant la verticale, k+1 après).
   - À ne pas refaire : détordre un dessin en demi-cercles dont des points sont dans la couronne (H_(u-1) du dessin
     de l'état non réduit) donne des brins crénelés.
   - Limites : le mélange est linéaire, donc de légères ondulations en milieu de rotation, et pas de preuve
     d'absence de croisement (aucun sur les tresses lisibles essayées ; deux images fautives sur
     `[1,-2,1,-2,1,-2,3,-1,2]`, 140 points sur l'axe).
10. **Essais en arcs de cercle** (demande : plus de courbes libres, uniquement des arcs de cercle qui partent et
    arrivent sur les segments noirs — l'axe et le segment qui tourne — traversés à angle droit). Obstacle : un arc
    perpendiculaire à deux droites sécantes est centré sur leur intersection, donc un brin qui va du segment
    tournant à l'axe ne peut être un seul arc que si ses deux bouts sont à la même distance du centre. Choix
    retenu : une paire d'arcs raccordés avec la même tangente (`deux_arcs`, `lieu_des_raccords`) pour ces brins.
    Deux essais, ni l'un ni l'autre au point (lignes commentées en fin de script, sorties `imgs/essai_*.gif`) :
    - `film_de_tresse_simultane(..., en_arcs=True)` (`lacet_en_arcs`, `segments_en_noeuds`) : on mélange les noeuds
      des deux dessins D_u et A_u (position et direction) et on les relie par des paires d'arcs. Plus d'ondulations,
      mots relus corrects, mais des croisements sur environ une image sur dix des lettres chargées : D_u et A_u
      s'enroulent différemment autour du bloc, leurs noeuds se correspondent mal.
    - `film_de_tresse_en_arcs` : construction directe, sans mélange ni couronne. Points du bloc et doigts sur le
      segment tournant, les autres sur l'axe, demi-cercles entre points d'un même segment, une paire d'arcs par brin
      qui sort du bloc ; le raccord part du passant (ou arrive au point nouveau). Propre en milieu de rotation,
      mais près des images clés des arcs géants sortent du cadre, des brins se croisent, et `verifie` échoue :
      la règle qui place le raccord est à revoir.

11. **Triangulation mobile** (`programmes/Triangulation.py`, `film_triangule` → `imgs/film_triangule_*.mp4`) : plus d'axe
    ni de couronne. Sommets : trous, clou, extrémités de l'axe, sommets des bords haut et bas à la verticale des
    trous (décalés de 0,31 px pour ne pas être sur le clou). Un lacet est une suite de points sur les arêtes
    (fraction de l'arête), deux points consécutifs dans un même triangle. σ_i : les trous i, i+1 tournent d'un demi-tour,
    les points suivent leur arête, les sommets des bords croisent sans se rejoindre (écart √((r cos θ)² + (g sin θ)²)).
    Les arêtes non de Delaunay sont retournées (`Maillage.delaunay`, `retourne`) : les points de l'arête disparaissent,
    chaque corde qui sépare les deux nouveaux triangles coupe la nouvelle diagonale (`courbe_apres_flip`), la forme ne
    change pas. Aucune réduction de bigones à faire. Dessin : arcs de cercle (`deux_arcs`) entre points d'arêtes,
    sans angle droit imposé. `verifie_triangulation` relit les mots (`lit_mot`) après chaque lettre : bon sur la tresse
    chargée du point 9 et sur 30 tresses aléatoires.
    **Triangulation de départ en deux bandes** (`maillage_initial`) : bande du haut (bord haut → axe, arcs du haut) et
    bande du bas (axe → bord bas, arcs du bas et arrivée des brins au clou). Chaque bande est une échelle de triangles
    entre deux rangées ; les rangées du haut et du bas ont un sommet à la verticale de chaque trou, et le clou est un
    sommet du bord bas (si un trou est à la verticale du clou, le clou est son sommet du bord bas). Un maillage plus fin
    n'a rien apporté. Le dessin de départ est étiré au-dessus de l'axe pour remplir la bande du haut (un brin n'occupe
    que les triangles qu'il traverse). **Plus de bande du bas séparée ni de pointe au clou** : essai précédent (clou en
    pointe de degré 2 sous une base, protégé contre tout flip) qui gardait le départ et l'arrivée de chaque lacet
    dans un même triangle ; il forçait tous les brins à traverser une seule arête puis une bande entière (zigzags
    près du clou) et empêchait de résorber des triangles écrasés. Maintenant le départ et l'arrivée d'un lacet ne sont
    plus forcément dans le même triangle, mais restent voisins autour du clou et la tension les garde proches.
    **Disposition proportionnelle** (`Film.disposition`) : à chaque image clé, la largeur de chaque intervalle de l'axe
    (y compris les deux de gauche et de droite) est proportionnelle à 1 + le nombre de brins qui le traversent
    (compté dans l'état : il égale les croisements réels de l'axe sur le dessin, vérifié à chaque image clé), donc
    l'écart `s` entre deux points consécutifs de l'axe est le même partout ; la verticale suit le même écart (les brins
    se tassent près des trous). Pendant la lettre, les trous glissent de la disposition de l'image clé k à celle du
    milieu de la lettre (`Film.milieux` : disposition de l'état non réduit `agit(état k, σ)`, qui compte les brins
    passant de chaque côté du bloc pendant le demi-tour), puis à celle de l'image clé k+1 (`Film.abscisses`,
    interpolation douce ; centre et rayon du demi-tour suivent ; le clou garde sa place relative entre ses deux
    voisins du bord bas), toujours un seul mouvement par lettre. Sans la disposition du milieu, la bande de droite de
    la tresse de référence (1 brin avant et après σ₄⁻¹) était trop étroite pour le jaune qui fait le tour de la paire
    pendant le demi-tour : il recouvrait le bleu. L'écart `ecart` de `tend` est celui de la disposition
    (interpolé), le trait est au plus 70 % de cet écart. Le dessin de départ est replacé sur la disposition 0 par une
    transformation affine par morceaux des abscisses. Plus la tresse est chargée, plus `s` est petit (2,8 px à la 7ᵉ
    lettre de la tresse chargée).
    **Film** : 800 × 800 par défaut (longueurs en pixels réglées pour 400 et multipliées par `largeur / 400`).
    **Vitesse constante** (`Film.lettre`, `chemin_des_trous`) : les trous avancent de `VITESSE` = 6 pixels par image
    (chemin cumulé de l'ensemble des trous) ; le temps de la lettre est reparamétré par la longueur de ce chemin, et
    une lettre dure (longueur du chemin) / vitesse images (53 à 177 images sur la tresse de référence), 2 sous-pas par
    image. Le glissement des trous (`abscisses`) est linéaire par morceaux (un adoucissement les arrêtait au milieu
    et aux bouts de chaque lettre ; une interpolation courbe pourrait intervertir deux trous voisins). Pas de pause
    entre les lettres, seulement sur la première et la dernière image. `film_triangule`
    écrit le MP4 au fil du calcul par un tube vers ffmpeg (un GIF de cette taille ne tiendrait pas en mémoire) ;
    `Film.lettre(..., rendu=f)` appelle f avec chaque image, sans rendu rien n'est dessiné (tests plus rapides).
    **Tension dès la première image** : 400 pas de `tend` dans `Film.__init__`.
    **Dessin en droites et congés** (`Film.polyligne`) : la ligne brisée des points, chaque coude arrondi par un congé
    (arc de cercle tangent aux deux segments, qui prend au plus la moitié du plus court) : rien que des droites et des
    arcs, sans point d'inflexion. Un brin tendu reste droit jusqu'à son coude ; les enroulements, faits de petits
    coudes réguliers autour d'un trou, sont des cercles. 0 croisement sur toutes les images clés des deux tresses
    d'essai, et sur une image sur quatre des deux films ; les brins ne se touchent que dans l'éventail du clou. Essais écartés : une direction par point (corde entre les voisins) et une paire d'arcs (`deux_arcs`) par
    segment : un brin droit qui tourne d'un coup en un point fait un S dans le segment qui précède (zigzags des brins
    extérieurs, 2 à 8 croisements par image clé) ; imposer la perpendiculaire au rayon aux points « plaqués » contre un
    trou (36 croisements : deux brins voisins d'un faisceau qui quitte un enroulement n'ont pas le même statut).
    **Brins attachés au clou** : leur premier (dernier) passage sur l'axe (`portions_du_clou`) est remplacé dans le
    dessin par deux points de part et d'autre de l'axe, sur la verticale si le brin traverse l'axe à moins de 45° de la
    verticale (poids décroissant avec l'angle), sinon dans la direction du brin : ils partent de l'axe
    perpendiculairement sans faire de cran quand, pendant un demi-tour, ils traversent l'axe en biais.
    Essai abandonné : tirer les points de ces brins vers un chemin imposé (arc de cercle centré sur l'axe, vertical au
    départ, de rayon κ × éloignement à la verticale du clou, puis tangente jusqu'au clou ; avec ou sans descente
    verticale jusque sous les arcs du bas). Ces chemins ne se croisent pas entre eux (vérifié numériquement), mais
    ils ignorent les arcs du bas qui enjambent la colonne du clou : ces arcs étaient écrasés contre les brins du clou,
    la profondeur « sous les arcs » s'emballait (rétroaction), jusqu'à 60 croisements par image.
    Réespacement continu (`Film.tend`, taux 0,15 par sous-pas) : plus de répartition uniforme sur les arêtes (elle étalait les brins sur toute la longueur,
    trop loin des trous). `Film.tend` : chaque point est tiré vers l'endroit de son arête où ses deux voisins sont
    alignés avec lui (le brin se tend), puis, arête par arête, les points gardent leur ordre, restent à `ecart`
    les uns des autres perpendiculairement aux brins (ecart / sinus le long d'une arête traversée en biais, sinus
    borné à 0,3 : dans un triangle plat, l'écart le long de l'arête ne suffisait pas) et à `ecart` des sommets
    (régression monotone bornée, `monotone`).
    Les brins se tassent à écart fixe près des trous et laissent du vide au-delà, comme les demi-cercles emboîtés des
    images clés (écart régulier sur l'axe, remplissage vertical qui part des trous). L'ordre sur chaque arête est
    conservé, donc pas de croisement des cordes.
    croisement. Les cordes ne se croisent jamais ; avant les congés, les arcs lissés se croisaient parfois (jusqu'à 194 sans la tension). Essais sans effet : tangente « bissectrice » (pire), remplacer un arc qui sort de son triangle par la corde (140 croisements : la corde coupe les arcs voisins du faisceau), tout le triangle en cordes (44 → 36 seulement : les croisements restants sont des arcs qui se coupent à l'intérieur d'un même triangle). Pour détecter un croisement, ignorer les
    intersections aux extrémités (les brins se rejoignent au clou).

Convention de composition : `calcule_autofn_de_tresse` parcourt la tresse à l'envers, donc
auto(`tresse[:k+1]`) = φ_σ ∘ auto(`tresse[:k]`) avec σ = `tresse[k]`. L'image k+1 s'obtient en tordant les trous i, i+1
de l'image k : le dessin du préfixe suivant est bien l'image du dessin courant par la torsion.

L'ancienne idée d'insertion point par point (`decale`, `dedans_extrm`) est décrite dans `git show f2fdb1c` et
`git show 4b2d4f4` ; le code a été retiré.

## Prochaines étapes

Objectif : le film (b), où σ_i fait tourner continûment les trous i et i+1 l'un autour de l'autre
et entraîne les lacets.

1. ~~**Film image par image.**~~ Fait : `film_de_tresse` → `imgs/film_*.gif`. Les trous gardent leur nombre mais
   bougent horizontalement d'une image à l'autre (l'espacement dépend du nombre de points sur l'axe).
2. ~~**Mouvement continu d'un σ_i.**~~ Fait, puis remplacé par la version algébrique (3).
3. ~~**Faire agir σ_i directement sur l'état.**~~ Fait : `agit` / `reduit` et `film_de_tresse_algebrique`.
   Les essais géométriques précédents (torsion puis fondu linéaire, mélanges) sont dans l'historique git
   (`505776e`, `cba60c8`) : le fondu créait des croisements, il est remplacé par les vagues de bigones.
   Limites : quand il y a beaucoup de points sur l'axe les brins sont très serrés ; la retouche (3) est un mélange
   linéaire (pas de preuve d'absence de croisement, mais les deux dessins sont proches) ; les fusions de plusieurs
   bigones à la suite dans un même lacet sont aussi un mélange linéaire.
4. ~~**Tout en un seul mouvement.**~~ Fait : `film_de_tresse_simultane` (point 9). Reste : lisser les ondulations
   (mélange en coordonnées polaires dans la couronne ?), puis retirer `film_de_tresse_algebrique` si le film
   simultané le remplace.
5. **Ménage.** Fait (code mort retiré : `decale`, `dedans_extrm`, `geometrie_auto_de_tresse`, ancienne torsion par
   ellipses). Reste éventuellement : passer les `assert` en tests pytest.

Sur un nouvel ordinateur : `git pull`, puis `conda env create -f environment.yml` (ou `conda env update -f
environment.yml --prune` si l'environnement existe déjà).

## Conventions

- Code, identifiants, commentaires et messages de commit **en français**. Garder ce style.
- Une tresse = liste d'entiers non nuls : `k` pour σ_k, `-k` pour σ_k⁻¹.
- Un mot de F_n = liste d'entiers non nuls : `i` pour x_i, `-i` pour x_i⁻¹.
- Un automorphisme = liste des images des générateurs (`images[i]` est l'image de x_(i+1)).
- Plusieurs fonctions travaillent par effet de bord (`simplifie`, `conjugaison_locale`) : le docstring le signale.
- Python ≥ 3.10 requis (`match`/`case` utilisés).
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

## Lancer

Depuis la racine du dépôt (les chemins de sortie comme `./imgs/...` sont relatifs au répertoire courant) :

```
python programmes/Triangulation.py   # le film actuel : vérifie les assert, écrit imgs/film_triangule_*.mp4
python -c "import sys; sys.path.insert(0, 'programmes'); import Triangulation as T; T.film_triangule([1, 2, -1], 'imgs/f.mp4')"   # un autre film
python programmes/NouvAutoMorph.py   # vérifie les assert, écrit imgs/nouv_*.png, imgs/film_*.gif, imgs/film_continu_*.gif (film algébrique) et imgs/film_simultane_*.gif, plus leurs .mp4
python programmes/AutoMorphPNG.py    # écrit imgs/a43m1m12m41nv.png
jupyter lab ipynbks/                  # notebooks
```
