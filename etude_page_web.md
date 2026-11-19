# L'ardoise à tresse en page web : étude

Demande (2026-11-19) : une page statique, pour PC, en JavaScript et canvas. Un champ pour écrire un mot de tresse, une
douzaine de tresses à choisir, et pour le mot choisi :

1. le mot en notation mathématique, non réduit, tel que l'utilisateur l'a écrit (σ₁σ₂⁻¹…) ;
2. le diagramme de tresse classique, générateurs de haut en bas ;
3. le mot de F_n associé (l'image de chaque x_i) en notation F_n ;
4. les méandres en trois modes (diagramme, conforme, rubans), d'abord en images fixes ;
5. les films calculés en tâche de fond, qui remplacent les images fixes quand ils sont prêts.

Cette étude ne change aucun code du dépôt. Elle répond à : de quoi dispose-t-on, que faut-il écrire, comment relier les
deux, qu'est-ce qui peut mal tourner.

## 1. Ce qu'on a déjà, ce qui manque

| Élément de la page | Où c'est aujourd'hui | État |
|---|---|---|
| Lecture du mot, mot affiché en σ | nulle part | à écrire (JS) |
| Diagramme classique de haut en bas | `ipynbks/CanvasTresse*.ipynb` (`dessine_tresse`, **ipycanvas = déjà l'API canvas HTML5**) | à porter en JS presque ligne à ligne ; absent d'OCaml |
| Mot de F_n (images des x_i) | `Tresses.calcule_autofn_de_tresse` (OCaml) | prêt ; l'affichage (MathML) est à écrire |
| Méandre conforme | `Conforme`, `Raccord`, `Film_conforme` (OCaml) | prêt, calcul seul |
| Méandres diagramme et rubans | `Arcs` (OCaml) | prêt, calcul seul |
| Dessin des trois modes | `Dessin.peint`, `Dessin.cadre_arcs`, `cadre_escargot` (Cairo) | à réécrire en canvas 2D (environ 120 lignes) |

Le calcul est donc fait et vérifié (identique au Python à 1e-11 près, films identiques octet pour octet). Ce qui reste :
l'interface, trois dessins, le diagramme classique, et le pont entre le calcul et le navigateur.

## 2. Choix de technologie : compiler l'OCaml ou le retraduire à la main ?

Tu proposes de partir de l'OCaml pour traduire. Deux manières :

**A. js_of_ocaml (ou wasm_of_ocaml) : on compile la bibliothèque telle quelle.** Rien à retraduire.
- `ocaml/lib/` (2 450 lignes) n'a aucune dépendance C : Cairo et `Unix` ne sont que dans `dessin/` et `bin/`. Il n'utilise
  que `Array`, `List`, `Hashtbl`, `Complex`, `Float`, `Printf` : tout cela existe en js_of_ocaml.
- `js_of_ocaml` 6.5.0 est dans opam (`ocaml >= 4.13`, `dune >= 3.20` ; ton dune est en 3.25).
- Une seule source de vérité : un correctif dans `raccord.ml` profite à la fois aux films MP4 et à la page. Les 83 tests de
  référence restent valables, on peut même les rejouer sous node sur le code compilé.
- Une fine couche `ocaml/web/ardoise_web.ml` expose quelques fonctions (`calcule_conforme mot` …) qui renvoient des
  tableaux de flottants ; tout le reste (interface, dessin) est du JS écrit à la main.
- Contre : une chaîne d'outils de plus ; le JS produit est illisible (c'est du code généré), 133 Ko en release ; les
  `int` de js_of_ocaml font 32 bits, pas 63 (aucun calcul de la bibliothèque n'approche 2³¹, à vérifier pendant l'essai).
  Les exceptions (`Pas_de_convergence`, `Clou_dans_un_demi_cercle`…) passent sans problème.

**B. Retraduction à la main en JavaScript.** Environ 2 500 lignes de JS à écrire et à déboguer, en perdant les types qui
rendaient visibles les invariants (types privés rangés, `Reduit.t`, noeuds en type somme). Deux copies du même algorithme
à maintenir. Il faudrait refaire les comparaisons avec le Python étape par étape : on peut réutiliser les
`reference_*.json`, mais c'est de nouveau toute l'étape 7 à valider. Avantage : du JS lisible, aucune chaîne d'outils.

**Recommandation : A**, avec un essai d'une heure avant de s'engager : installer `js_of_ocaml`, compiler `lib/`, lancer
un calcul conforme sous node, comparer à la référence JSON. Si cela passe, la suite est du JS d'interface. Si cela coince
(taille, vitesse, un détail de runtime), on bascule sur B, et le travail déjà fait en OCaml sert de spécification.

Dépôt : ajouter `js_of_ocaml-compiler` et `js_of_ocaml` aux dépendances de `ocaml/dune-project`.

**Résultat de l'essai (2026-11-19) : A passe.** `js_of_ocaml-compiler` 6.5.0 installé dans le switch local (rien d'autre),
`lib/` compilée telle quelle (`(modes exe js)`), film conforme complet de la tresse de référence (337 images, vérification
comprise) rejoué sous node 24 :

| | natif | JS (dev) | JS (`--profile release`) |
|---|---|---|---|
| temps | 7,3 s | 25,5 s | **11,1 s** (1,5 × le natif) |
| somme des coordonnées de toutes les images | 1574854318,018783808 | …018784046 | …018784046 |
| anomalies | 0 | 0 | 0 |
| taille du JS | | 2,9 Mo | **133 Ko (44 Ko compressé)** |

Mêmes 337 images, mêmes sommes à 1e-16 relatif (les derniers chiffres de `pow` complexe diffèrent, comme prévu), même
résultat avec la tresse (σ₁σ₂⁻¹)³ (289 images, 0 anomalie). Les `int` 32 bits n'ont gêné nulle part. Le facteur à
prévoir est donc d'environ 1,5, et non de 2 à 4 : un demi-tour à 5 brins (10 lettres) devrait prendre de 20 à 30 s.

## 3. Le calcul : ce que ça coûte (mesuré en OCaml natif)

Tresses tirées au hasard, 12 par ligne, film conforme complet avec vérification (mots relus, croisements), sans dessin :

| brins | lettres | temps moyen | exceptions | anomalies |
|---|---|---|---|---|
| 3 | 4 | 1,8 s | 0 | 0 |
| 3 | 8 | 5,8 s | 0 | 0 |
| 4 | 6 | 4,4 s | 0 | 0 |
| 4 | 10 | 13,2 s | 0 | 0 |
| 5 | 8 | 7,8 s | 0 | 0 |
| 5 | 12 | 22,5 s | 0 | 0 |
| 6 | 10 | 12,4 s | 0 | 0 |

- **Robustesse : 84 tresses aléatoires sur 84 sans exception ni anomalie** (mots relus justes, aucun croisement). C'était
  la grande inquiétude pour un champ libre : le film conforme n'avait été essayé que sur deux tresses. Pas de garantie
  pour autant (le raccord n'est pas prouvé) : la page doit tout de même attraper les exceptions et dire « film
  indisponible pour ce mot » sans casser le reste.
- Le conforme coûte de 0,4 à 2 s **par lettre** (cartes de Schwarz–Christoffel par image) : c'est lui qui demande un travail
  de fond.
- **Diagramme et rubans sont presque gratuits** : 0,0 à 0,2 s pour tout le calcul (3 à 6 brins, jusqu'à 20 lettres).
  Les 21 s du film d'arcs étaient dans le dessin Cairo et l'encodage, pas dans le calcul. Dans le navigateur, ces deux
  films seront donc prêts presque tout de suite.
- En JavaScript, facteur mesuré 1,5 (essai de la section 2) :
  un demi-tour à 5 brins (10 lettres, environ 15 s natif) prendrait environ 25 s. Acceptable en tâche de fond avec
  une barre de progression, pas autrement. Limite proposée : 6 brins et 14 lettres pour le conforme ; au-delà, seulement
  les images fixes et les deux autres films.

## 4. Un film = des polylignes, pas une vidéo

Le MP4 était la sortie d'un pipeline Cairo + ffmpeg. Dans le navigateur, on n'en a pas besoin : `Film_conforme.film`
appelle déjà `~rendu` avec chaque image sous la forme `{ lignes : point array list; trous; clou }`, et `Arcs.lettre` fait
de même. On garde ces polylignes (un `Float32Array` par image) et le lecteur les redessine sur le canvas.

- Le film est vectoriel : net à toute taille, aucune compression, lecture image par image, arrêt, curseur, boucle.
- Mémoire (estimation) : environ 40 Ko par image conforme, 400 images pour une tresse de 9 lettres, soit 16 Mo. Raisonnable.
- **Le remplacement de l'image fixe est naturel** : l'image fixe est la première (ou la dernière) image du film, dessinée
  par la même fonction. Quand les images arrivent, le lecteur remplace l'image fixe sans changement de style.
- Images fixes : conforme = `Conforme.dessin` de l'état final (deux cartes, quelques ms) ; diagramme et rubans = dernière
  image du film (0,2 s). Le diagramme de tresse classique et le mot de F_n sont immédiats.

## 5. Architecture proposée

```
ocaml/web/ardoise_web.ml      points d'entrée js_of_ocaml : analyse, images fixes, un film image par image
web/index.html, ardoise.css  page statique
web/ardoise.js               interface : champ, liste, MathML, diagramme de tresse, lecteurs canvas
web/travail.js               Web Worker : charge ardoise_lib.js, calcule, envoie les images au fil de l'eau
web/ardoise_lib.js           produit par dune (js_of_ocaml), non suivi par git ou construit à la publication
```

- **Un Web Worker par film** (trois en tout, selon `navigator.hardwareConcurrency`) : l'interface reste fluide et le
  conforme n'attend pas les deux autres. Messages `{ mode, k, n }` pour la progression, `{ mode, images }` par paquets
  (une lettre à la fois).
- **Changer de mot** : on tue les workers en cours (`terminate`) et on repart. Un petit cache par mot (en mémoire) évite
  de recalculer si l'on revient à un mot déjà vu.
- **Publication** : une page statique. Un workflow GitHub Pages qui construit `ardoise_lib.js` existe
  (`.github/workflows/pages.yml` : la construction réussit en 19 minutes, dont 17 pour compiler OCaml ; Pages n'est pas
  activé). Le déploiement visé : test en local, puis serveur personnel servi par Caddy (section 11).

### Données entre le calcul et le dessin
Une image = `{ lacets : Float32Array[], trous : Float32Array, clou : [x, y] }`, repère de la page 800 × 800 comme
aujourd'hui (le canvas fait la mise à l'échelle). Les couleurs et les épaisseurs restent côté JS (elles viennent de
`peint`, `couleurs_arcs`).

## 6. L'interface (PC)

```
┌────────────────────────────────────────────────────────────────┐
│ Ardoise à tresse                                                │
│ [ champ : 1 -2 3 -1 2 ........ ]  [tresses d'exemple  ▾ ]       │
│ σ₁ σ₂⁻¹ σ₃ σ₁⁻¹ σ₂      (le mot tel qu'écrit, non réduit)        │
├──────────────┬─────────────────────────────────────────────────┤
│ diagramme    │ images de x₁ … x_n par la tresse (F_n)           │
│ classique    │ x₁ ↦ x₁x₂x₁⁻¹ , x₂ ↦ …                           │
│ (haut→bas)   │                                                  │
├──────────────┴──────────┬──────────────┬───────────────────────┤
│ méandres : diagramme    │ conforme     │ rubans                │
│ (image fixe → film)     │ (calcul 63 %)│ (film prêt ▶ ⏸ ───●)  │
└─────────────────────────┴──────────────┴───────────────────────┘
```

- Écriture admise : `1 -2 3`, `s1 s2^-1`, `σ1σ2⁻¹`, `1,-2,3`. L'affichage se fait dès la frappe.
- La notation mathématique en **MathML** (supporté nativement par les navigateurs actuels) : pas de bibliothèque à
  charger, ce qui garde la page autonome et hors ligne.
- Garde-fous : n ≥ 2 brins (σ_k avec k ≥ 1), entiers non nuls, taille maximale (voir section 3). Le mot vide est une
  tresse valide (identité) : à traiter à part car `Film_conforme.film` fait `List.hd` sur la tresse.
- Pas de réduction du mot affiché (tu l'as demandé), mais on pourra ajouter ensuite un bouton « réduit » ou une ligne
  « équivalent à … » (le groupe est de présentation connue, mais la forme normale de Garside est un autre chantier).

## 7. Une douzaine de tresses à proposer

Longueur de l'image de F_n = somme des longueurs des mots images des x_i (mesurée) : elle dit si la tresse est « chargée »
en action sur le disque percé.

| # | Tresse | Brins | Lettres | Long. F_n | Pourquoi |
|---|---|---|---|---|---|
| 1 | σ₁ | 2 | 1 | 4 | le demi-tour le plus simple |
| 2 | Δ₅ = (σ₁σ₂σ₃σ₄)(σ₁σ₂σ₃)(σ₁σ₂)σ₁ | 5 | 10 | 25 | demi-tour positif à 5 brins : tous les trous échangés |
| 3 | Δ₅⁻¹ (mot inverse) | 5 | 10 | 25 | le même, dans l'autre sens |
| 4 | (σ₁σ₂)³ = Δ₃² | 3 | 6 | 19 | tour complet à 3 brins : action = conjugaison par x₁x₂x₃ |
| 5 | σ₁σ₂σ₁σ₂⁻¹σ₁⁻¹σ₂⁻¹ | 3 | 6 | 3 | un mot non vide qui vaut la tresse nulle (relation de tresse) : le film revient à son point de départ |
| 6 | σ₂σ₁σ₂⁻¹ | 3 | 3 | 9 | deux mots, une même tresse (voir 7) |
| 7 | σ₁⁻¹σ₂σ₁ | 3 | 3 | 9 | même tresse que 6 : même automorphisme, films différents |
| 8 | σ₁σ₂⁻¹ | 3 | 2 | 7 | la plus courte tresse « pseudo-Anosov » : action déjà riche |
| 9 | (σ₁σ₂⁻¹)³ | 3 | 6 | 51 | croissance exponentielle des mots : 6 lettres, 51 lettres dans F_n |
| 10 | σ₁σ₂σ₃σ₄ | 5 | 4 | 13 | la rotation de 5 trous : une chaîne qui tourne |
| 11 | σ₄σ₃σ₁⁻¹σ₁⁻¹σ₂σ₄⁻¹σ₁ | 5 | 7 | 21 | la tresse de référence des films |
| 12 | σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂ | 4 | 9 | 94 | la tresse chargée des films |

Sur « des tresses courtes mais avec une action sur le disque complexe » : j'ai compris « courtes, mais dont l'action sur
le disque (percé) est compliquée », d'où 8 et 9 (et 12). Si tu pensais à autre chose (les trous dans le plan complexe,
la représentation de Burau…), dis-le avant que je fige la liste.

## 8. Étapes proposées

1. ~~**Essai js_of_ocaml.**~~ Fait : A retenue (section 2).
2. ~~**Pont** : `ocaml/web/ardoise_web.ml` et le Worker.~~ Fait (2026-11-19).
3. ~~**Page minimale** : champ, mot en MathML, mot de F_n, diagramme classique, liste des 12 tresses.~~ Fait (`web/`).
4. ~~**Lecteurs canvas** pour les trois modes, remplacement image fixe → film, progression.~~ Fait. Les 12 tresses d'exemple
   passent sans erreur ni anomalie dans les trois modes (essai sous node).
5. **Finitions** : annulation d'un calcul quand on change de mot, cache, messages d'erreur, déploiement sur serveur personnel (Caddy).

Chaque étape est visible dans le navigateur ; la 1 décide de tout le reste.

## 8 bis. Ce que l'essai a appris

- La pile de JavaScript est petite : `List.concat` (non récursive terminale) dans `Tresses.lit_mot` débordait sur les
  polylignes de plusieurs milliers de points (tresse chargée, lettre 7). Remplacé par `List.concat_map` : même résultat,
  films natifs toujours identiques octet pour octet. Une pile agrandie (`node --stack-size`) fait passer le calcul mais le
  rend quatre fois plus lent (le ramasse-miettes parcourt toute la pile) : il fallait corriger, pas contourner.
- Temps JS mesurés seuls : tresse chargée 39 s (natif 24 s, soit un facteur 1,6).

## 9. Risques

- **Vitesse en JS** du conforme (facteur mesuré : 1,5) : atténué par les Workers, la limite de taille et la progression.
- **Mots longs ou beaucoup de brins** : le temps croît avec les lettres et les brins (section 3) ; limite à fixer.
- **Raccord non prouvé** : il pourrait rester un mot qui plante ou croise. Le calcul est déjà protégé par la vérification
  des mots et des croisements, qu'on pourrait garder activée côté web pour dire « film non fiable ».
- **Taille de page** : 133 Ko de JS produit en release (44 Ko compressé).
- **Dessin** : le canvas 2D n'a pas l'anticrénelage de Cairo à l'identique ; sans importance visuelle, mais plus de
  comparaison octet pour octet des images (les polylignes, elles, restent comparables au Python).

## 10. Questions à trancher

1. A (js_of_ocaml) ou B (retraduction) ? Je recommande A après l'essai de la section 8.
2. La liste de la section 7 te convient-elle ? Faut-il un tour complet à 4 ou 5 brins, ou plus de tresses négatives ?
3. Limite de taille du mot libre : 6 brins et 14 lettres pour le conforme te va-t-elle ?
4. Les films du bouquet et de l'escargot ne sont pas dans la page (ils n'ont pas de mot de tresse) : on les laisse de côté ?

## 11. Déploiement sur serveur personnel (étude du 2026-11-19, rien n'a été modifié sur le serveur)

Constat (lecture seule par ssh) : Caddy actif, `/etc/caddy/Caddyfile` appartenant à root (modifier et recharger
demande sudo, avec mot de passe). Le site **`le site`** sert déjà `/chemin/du/site` (dossier à toi) : une page
d'accueil `index.html` et un dossier par application (les autres applications du site), avec compression (`encode zstd gzip`), en-têtes de sécurité, cache de longue durée pour `/<app>/assets/…`
(fichiers à empreinte) et `no-cache` pour les pages d'entrée (`index.html`, `sw.js`, manifeste).

**Option A (recommandée) : `l'adresse du site`.** Aucun DNS, aucun nouveau certificat. Il suffit de copier
`web/` dans `/chemin/du/site/ardoise/` (dossier créable sans sudo). Les chemins de la page sont relatifs : les Web Workers
et `ardoise_lib.js` se chargent sous ce sous-chemin sans changement. Seul souci : nos fichiers (`ardoise.js`,
`travail.js`, `ardoise_lib.js`, `ardoise.css`) n'ont pas d'empreinte et ne sont pas sous `assets/` : Caddy envoie
`ETag` et `Last-Modified`, donc un navigateur peut les garder quelques heures par heuristique et servir un vieux JS après
un redéploiement. Une petite addition au Caddyfile, dans le bloc `le site`, règle cela (revalidation à chaque
visite, réponse 304 presque gratuite) :

```
	# Ardoise à tresse : fichiers sans empreinte, revérifiés à chaque visite (ETag)
	@ardoise path /ardoise/*.js /ardoise/*.css /ardoise/*.svg
	header @ardoise Cache-Control "no-cache"
```

puis `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy` (à faire par toi ; sauvegarde
habituelle : `Caddyfile.avant-…`). Sans cette addition, tout marche, avec le risque de cache. On peut aussi ajouter une
entrée « Ardoise à tresse » dans `/chemin/du/site/index.html` (la page d'accueil des applications, à ta main).

**Option B : `un sous-domaine`.** Un enregistrement DNS en plus, un bloc `un sous-domaine { root * … file_server
encode zstd gzip }` dans le Caddyfile (sudo), certificat automatique. Plus propre pour l'adresse, plus de travail ; rien
n'y gagne la page.

**Mise en place proposée (A).** Un script `web/deploie.sh` : `construit.sh` (compile `ardoise_lib.js` chez toi, en
quelques secondes), puis `rsync -av --delete` de `index.html`, `ardoise.css`, `ardoise.js`, `travail.js`,
`ardoise_lib.js`, `favicon.svg` vers `utilisateur@serveur:/chemin/du/site/ardoise/`. Pas de compilation sur le serveur
(inutile d'y installer OCaml) ; le dépôt git du serveur (`depot-nu`) reste le simple dépôt qu'il est. Le test en local
(`python3 -m http.server` dans `web/`) garde sa place avant chaque envoi.

Décisions à prendre : A ou B ; ajoute-t-on la règle de cache au Caddyfile (recommandé) ; une carte dans l'accueil des
applications.

## 11 bis. La triangulation mobile, quatrième méandre (2026-11-19)

Ajoutée à la demande de l'utilisateur (le film « avec le clou » des films de départ, même moteur que le bouquet) : mode
`triangulation` du pont, polylignes en droites et congés, maillage gris masqué, titre « Action sur le groupe libre et sa
triangulation ». Calcul très rapide (0,1 à 2 s en JavaScript pour les 12 exemples, qui passent tous), mais jusqu'à 1 255 images
(32 Mo) : mêmes limites que le conforme. Le film peut échouer sur certaines tresses (un triangle se retourne : 14 tresses
aléatoires sur 60 à 5 brins et 12 lettres, sans remède par plus de sous-pas) : une piste pour plus tard.

## 12. L'escargot et le premier bouquet dans la page (étude du 2026-11-19 ; fait le même jour : escargot par le pont, bouquet par la voie 2, traduit en OCaml)

Ni l'un ni l'autre n'a de mot de tresse : ce sont des films à chorégraphie libre (des trous qui suivent des chemins, des
lacets emportés par la triangulation mobile). Ils n'iraient donc pas dans la grille des trois méandres, mais dans une
section à part (« Un peu de poésie », d'abord appelée « Hors des tresses ») avec chacun son panneau, son image fixe puis son film, calculé en tâche de fond par
le même mécanisme (Web Worker, polylignes, lecteur).

**Escargot : tout est déjà en OCaml.** `lib/escargot.ml` (130 lignes : `cree`, `choregraphie`, `deplace`, `polyligne`) et
le film identique octet pour octet au Python (4,5 s natif pour 300 images). Il reste :
1. un point d'entrée dans `ocaml/web/ardoise_web.ml` : `ardoise.escargot(rendu)`, qui appelle `deplace` à chaque image
   et envoie, par image, les polylignes des 7 courbes, le centre et le rayon de la coquille, les positions des yeux et leur
   facteur d'apparition (ce que `Dessin.cadre_escargot` lit dans l'état) ;
2. le dessin en canvas, port de `cadre_escargot` (60 lignes) : dégradé de fond, corps puis coquille par-dessus avec un
   découpage (`clip`) par le disque de la coquille, règle pair-impair pour la partie hors coquille (le canvas sait faire :
   `ctx.clip('evenodd')`), traits cernés, yeux ;
3. le temps de calcul attendu en JS : de 5 à 8 s (facteur 1,5 sur le natif, mesuré ailleurs).
Travail : une séance, sans risque particulier. Taille de données : 300 images × 7 courbes, de l'ordre de 10 Mo en flottants
32 bits (réductible : une image sur deux suffit pour le lecteur).

**Premier bouquet (iris) : seulement en Python.** `python/Bouquet.py` (516 lignes) : la classe `Pousse` (hérite de `Film`),
la chorégraphie des fleurs et des feuilles (`phases`, `centre` en Bézier avec nutation, `trous_de_fleur`, `trous_de_feuille`,
`cibles`), `deplace`, et un dessin en Cairo assez riche (fond en dégradé, lacets remplis en transparence, secteur de la
fleur découpé, dégradés radiaux vert → blanc → couleur de la fleur qui éclot). Le film de référence : 810 × 1080, 13,5 s,
169 images calculées, 35 trous, environ 35 s en Python. Deux voies :

- **Voie 1, calculer en Python une fois et servir les données.** Un script écrit, pour chaque image, les polylignes des 35
  lacets et les positions des centres, des phases et des couleurs ; la page les charge (fichier de plusieurs Mo, à
  compresser) et le lecteur canvas redessine (port du dessin Cairo : dégradés radiaux, `clip`, transparence : tout existe en
  canvas 2D). Aucune traduction du calcul : quelques heures, plus une séance pour le dessin. Pas de calcul dans le
  navigateur (le film est fixe de toute façon : il n'y a pas de mot à saisir), et il se charge d'un coup. Inconvénient :
  un fichier de données de quelques Mo à déployer, et la chorégraphie reste en Python.
- **Voie 2, traduire `Bouquet.py` en OCaml** (étape 8 du plan : `Pousse`, ses chorégraphies, `deplace`, comparaison au Python
  par des références, film identique octet pour octet), puis le même pont que l'escargot. Plus long (deux ou trois séances,
  avec la vérification pour 35 trous : le décalage du bord bas près du clou est dans `Film.decalage_bas`, mais n'a jamais été
  essayé à cette taille en OCaml). Gain : le calcul vit dans le navigateur, on peut changer des réglages (couleurs, nombre de
  pétales, durée) à la volée, et le bouquet rejoint l'ensemble réécrit en OCaml.

**Recommandation** : l'escargot d'abord (voie directe) ; pour le bouquet, la voie 1 d'abord (il apparaît dans la page vite),
la voie 2 plus tard si l'envie de faire varier les fleurs vient. Dans les deux cas, la section « Un peu de poésie » partage le
lecteur de films de la page (qui lit déjà des suites d'images en polylignes) : il suffit d'y ajouter un type de dessin par
film (escargot, bouquet) à côté des trois des méandres.

**Autres points** : les couleurs de ces deux films sont les leurs (marron et vert pour l'escargot, bleu clair et couleurs de
fleurs pour le bouquet) : la palette commune des tresses ne s'y applique pas. Pour le bouquet, des images fixes de 152 × 205
mm à 300 dpi existent déjà (`imgs/bouquet_152x205.jpg`, `imgs/bouquet_iris.jpg`) : l'image fixe de la page peut être un de ces
fichiers (ou un dessin canvas de la dernière image) en attendant le film. Enfin, une version plus simple de repli pour les
deux : une balise `<video>` sur les MP4 existants (AV1 : bien lu par Firefox et Chrome, moins par Safari), sans calcul ni
canvas, mais sans le côté vectoriel.
