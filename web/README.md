# Ardoise à tresse : la page web

Une page statique (HTML, CSS, JavaScript, canvas). On y écrit un mot de tresse (ou on en choisit un parmi douze) ; elle montre :

1. le mot en notation mathématique, tel qu'il est écrit (MathML) ;
2. le diagramme de tresse classique, de haut en bas ;
3. l'action de la tresse sur le groupe libre F_n (l'image de chaque x_i) ;
4. les méandres en quatre modes (diagramme de courbes, lacets conformes, lacets sur la triangulation mobile, rubans) : d'abord une image fixe, puis le
   film, calculé en tâche de fond par un Web Worker par mode, qui la remplace ;
5. « Un peu de poésie » : l'escargot et le premier bouquet (films sans mot de tresse, lancés une fois au chargement).

Le calcul est celui de `ocaml/lib/`, compilé en JavaScript par js_of_ocaml (`ocaml/web/ardoise_web.ml` est le pont) ; un
film est une suite de polylignes redessinées sur le canvas, pas une vidéo. Étude et choix : `../etude_page_web.md`.

## Construire et voir

```
web/construit.sh                  # compile la bibliothèque : web/ardoise_lib.js (suivi par git : à relancer quand l'OCaml change)
cd web && python3 -m http.server  # puis http://localhost:8000/
```

Il faut un serveur : les Web Workers ne se chargent pas depuis `file://`. `construit.sh` demande js_of_ocaml dans le switch
opam de `ocaml/` (`opam install js_of_ocaml js_of_ocaml-compiler`, déclarés dans `ocaml/dune-project`).

## Publication

- **Test en local** : `web/construit.sh`, puis `python3 -m http.server` dans `web/`.
- **Serveur personnel** : `web/deploie.sh` construit `ardoise_lib.js` chez soi puis copie la page par rsync vers la cible donnée par
  la variable `CIBLE` ou par le fichier local `web/deploie.conf` (non suivi par git, voir le script) ; `web/deploie.sh -n` : essai
  à blanc. Avec Caddy, ajouter au bloc du site qui sert la page une règle de cache (fichiers sans empreinte, revérifiés à chaque
  visite) :

  ```
  	# Ardoise à tresse : fichiers sans empreinte, revérifiés à chaque visite (ETag)
  	@ardoise path /ardoise/*.js /ardoise/*.css /ardoise/*.svg
  	header @ardoise Cache-Control "no-cache"
  ```

  puis valider et recharger Caddy (`caddy validate`, `systemctl reload caddy`).
- **`git publie`** : pousse puis déploie sur le serveur personnel, d'une seule commande (`web/publie.sh` : `git push`, puis `deploie.sh`
  si le push a réussi). L'alias est local : `git config alias.publie '!sh web/publie.sh'` à refaire après un clone. Un simple
  `git push` met à jour GitHub Pages (workflow) mais pas le serveur personnel.
- `.github/workflows/pages.yml` : le workflow GitHub Pages, lancé par chaque push sur `master` qui touche `web/` (et à la main :
  onglet Actions). Il copie seulement les fichiers de `web/` (dont `ardoise_lib.js`, suivi par git) : rien n'est compilé chez GitHub
  (la compilation d'OCaml y prenait 19 minutes). Pour que le JS publié soit toujours à jour, le hook `.githooks/pre-push` lance
  `web/construit.sh` avant chaque push et refuse de pousser si `ardoise_lib.js` a changé (à commiter, puis repousser). À activer
  une fois par clone : `git config core.hooksPath .githooks` ; `git push --no-verify` passe outre (à éviter).

Le film de la triangulation utilise le maillage grossier des films d'arcs (`Film.cree ~grossier:true`) : les arêtes partent
en étoile de chaque trou, les brins s'enroulent autour du trou contourné et partent du clou en éventail.
Son lecteur a une case **« construction »** (les lignes de construction) : elle trace ce maillage en gris (`#999`, 2,2 px) sous les lacets. Les
arêtes viennent du calcul (`image.construction` : des segments à plat, `aretes_a_plat` dans `ocaml/web/ardoise_web.ml`) et sont
tracées par `traceSegments` (`web/ardoise.js`) ; elles ne comptent pas dans le zoom arrière. La case garde son état quand le mot
change. Le film des **lacets** (conforme) a la même case : elle trace l'axe et la ligne brisée L–A–B–R, avec les fondus du raccord
(un « ? » à côté de la case, qui s'ouvre au survol, au clavier ou à l'appui, dit ce que sont ces lignes ; pendant le raccord, le dessin n'est plus fait sur cette ligne mais sur une triangulation mobile : les deux lignes de départ et
d'arrivée sont les références entre lesquelles on raccorde ; `image.opacites`, un nombre par segment ; `Conforme.aretes` et `Film_conforme.construction` en OCaml).
Pendant le raccord, le dessin des lacets est aussi **détendu** (`ocaml/lib/detente.ml`, mode de calcul `conforme_detendu`, `MODE_DE_CALCUL` dans
`web/ardoise.js`) : un court flot de courbure contraint arrondit les brins autour des trous qui tournent et efface les zigzags, une
répulsion garde leurs écarts ; l'intensité est nulle aux bords de la fenêtre (images clés inchangées). `web/travail.js` répartit cette
détente sur des workers auxiliaires, un par cœur (8 au plus), et rend les images dans l'ordre. Les films du **diagramme de courbes** et des **rubans** ont aussi la case : elle trace les arêtes du maillage
sur lequel les arcs sont posés (au centre des rubans), et elles bougent avec les trous. Le zoom (`etendue`) compte les trous fixes des films d'arcs et ignore leur « clou »
factice hors du cadre, qui les faisait reculer à tort (diagramme et rubans). Étude : `etude_lignes_de_construction.md`.

## Les fichiers

- `index.html`, `ardoise.css`, `favicon.svg` (un croisement du diagramme de tresse) : la page ;
- `ardoise.js` : lecture du mot (`1 -2 3`, `σ1 σ2^-1`, `σ₁σ₂⁻¹`, `s1^3`), MathML, diagramme classique, lecteurs de films ;
- `travail.js` : le Web Worker (image fixe, puis images du film envoyées une à une) ;
- `ardoise_lib.js` : produit par `construit.sh`, suivi par git (quelque 167 Ko) ;
- `schemas/*.svg` : les schémas des infobulles (un « ? » près de chaque titre, au survol ou au clavier), copies de `imgs/schemas/` ; `?aide=triangulation` ouvre une bulle sans survol (captures).

Les méandres qui sortent du cadre (une tresse chargée, à la triangulation) sont recadrés : zoom arrière seulement, une même
vue pour tout le film (`vueDe` dans `ardoise.js`), calculée sur toutes ses images dès que le film est fini.

`index.html?fin` : pas de lecture automatique, les films s'arrêtent sur leur dernière image (pour les captures d'écran) ;
`?construction` : la case « construction » est cochée au départ.

Limites affichées sous le champ (« Limites de la page » et « Ce mot : N brins, M lettres », avec avertissement) ; un mot qui dépasse la page
(8 brins, 40 lettres) donne une erreur et grise les résultats, qui restent ceux du dernier mot valide ; un mot qui dépasse les vues « lacets » et
« triangulation » (6 brins, 14 lettres) y affiche un message au lieu de lancer le calcul. Infobulles : au toucher, un appui sur « ? »
les ouvre, un appui ailleurs, Échap ou un défilement les ferment (le survol n'y existe pas).

Adaptation aux petits écrans (`ardoise.css`, deux seuils : 1000 px, une seule colonne ; 640 px, marges réduites, exemples sur deux colonnes,
commandes de lecture plus grandes, infobulle en feuille collée en bas de l'écran) ; testée à 390 px de large.

## Limites

8 brins et 40 lettres au plus pour la page ; les films des lacets (conforme : de 0,4 à 2 s par lettre ; triangulation :
rapide, mais jusqu'à 1 300 images et 30 Mo en mémoire) sont limités à 6 brins et 14 lettres. Le film de la triangulation
essaie 2, 4 puis 8 sous-pas par image (un triangle plat peut se retourner à 2) et, si tout échoue, le dit dans le panneau :
moins d'un mot aléatoire sur cent dans les limites ne passe pas (0 sur 900 dans un essai, 2 sur 300 dans un autre), aucun des
12 exemples. Ces limites sont dans `ardoise.js` et `ocaml/web/ardoise_web.ml`.

Sous JavaScript la pile est petite : pas de récursion non terminale sur des listes de la taille d'une polyligne
(`List.concat` dans `lit_mot` l'a fait déborder ; remplacé par `List.concat_map`).
