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
web/construit.sh                  # compile la bibliothèque : web/ardoise_lib.js (non suivi par git)
cd web && python3 -m http.server  # puis http://localhost:8000/
```

Il faut un serveur : les Web Workers ne se chargent pas depuis `file://`. `construit.sh` demande js_of_ocaml dans le switch
opam de `ocaml/` (`opam install js_of_ocaml js_of_ocaml-compiler`, déclarés dans `ocaml/dune-project`).

## Publication

- **Test en local** : `web/construit.sh`, puis `python3 -m http.server` dans `web/`.
- **serveur personnel** (option A de l'étude) : `web/deploie.sh` construit `ardoise_lib.js` chez soi puis copie la page par rsync dans
  `/chemin/du/site/ardoise/` (sans sudo) ; elle est servie par Caddy sur `l'adresse du site`.
  `web/deploie.sh -n` : essai à blanc. Une fois, avec sudo, ajouter au bloc `le site` du Caddyfile la règle de
  cache (fichiers sans empreinte, revérifiés à chaque visite) :

  ```
  	# Ardoise à tresse : fichiers sans empreinte, revérifiés à chaque visite (ETag)
  	@ardoise path /ardoise/*.js /ardoise/*.css /ardoise/*.svg
  	header @ardoise Cache-Control "no-cache"
  ```

  puis `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`.
- `.github/workflows/pages.yml` : un workflow GitHub Pages (construit `ardoise_lib.js` chez GitHub, 19 minutes dont 17 pour
  compiler OCaml). Il est resté dans le dépôt, en déclenchement manuel seulement (onglet Actions → Page web → Run workflow) ; le déploiement visé est serveur personnel.

Le film de la triangulation utilise le maillage grossier des films d'arcs (`Film.cree ~grossier:true`) : les arêtes partent
en étoile de chaque trou, les brins s'enroulent autour du trou contourné et partent du clou en éventail.

## Les fichiers

- `index.html`, `ardoise.css`, `favicon.svg` (un croisement du diagramme de tresse) : la page ;
- `ardoise.js` : lecture du mot (`1 -2 3`, `σ1 σ2^-1`, `σ₁σ₂⁻¹`, `s1^3`), MathML, diagramme classique, lecteurs de films ;
- `travail.js` : le Web Worker (image fixe, puis images du film envoyées une à une) ;
- `ardoise_lib.js` : produit par `construit.sh`.

Les méandres qui sortent du cadre (une tresse chargée, à la triangulation) sont recadrés : zoom arrière seulement, une même
vue pour tout le film (`vueDe` dans `ardoise.js`), calculée sur toutes ses images dès que le film est fini.

`index.html?fin` : pas de lecture automatique, les films s'arrêtent sur leur dernière image (pour les captures d'écran).

## Limites

8 brins et 40 lettres au plus pour la page ; les films des lacets (conforme : de 0,4 à 2 s par lettre ; triangulation :
rapide, mais jusqu'à 1 300 images et 30 Mo en mémoire) sont limités à 6 brins et 14 lettres. Le film de la triangulation
essaie 2, 4 puis 8 sous-pas par image (un triangle plat peut se retourner à 2) et, si tout échoue, le dit dans le panneau :
moins d'un mot aléatoire sur cent dans les limites ne passe pas (0 sur 900 dans un essai, 2 sur 300 dans un autre), aucun des
12 exemples. Ces limites sont dans `ardoise.js` et `ocaml/web/ardoise_web.ml`.

Sous JavaScript la pile est petite : pas de récursion non terminale sur des listes de la taille d'une polyligne
(`List.concat` dans `lit_mot` l'a fait déborder ; remplacé par `List.concat_map`).
