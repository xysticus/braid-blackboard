# Construire des tresses personnalisées

Étude (rien d'implémenté) : permettre à la personne qui utilise la page `web/` de garder ses propres tresses à la suite des
douze tresses d'exemple, de les annoter, d'en choisir les couleurs et la couleur du fond. Elle complète `etude_page_web.md`.

## Ce qu'on veut

1. **Mémoriser** les tresses librement proposées (saisies dans le champ « Mot de tresse »), à la suite des tresses fournies.
2. **Effacer** une tresse mémorisée par une croix, après confirmation. Les tresses fournies ne s'effacent pas.
3. **Un texte libre par tresse**, au même endroit que la légende des tresses fournies (« le demi-tour le plus simple »…).
4. **Autant de pastilles de couleur que de brins**, pour changer la couleur de chaque brin, et **un petit carré**, de même taille,
   pour la couleur du fond.
5. **Exporter et importer** ses tresses.

## Les règles (décidées le 2026-11-22)

- **Une saisie validée crée toujours une entrée.** Valider = Entrée ou sortie du champ, après avoir *tapé* dans le champ, avec un mot
  valide. Même si le mot existe déjà (parmi les exemples ou parmi les tresses mémorisées) : l'entrée est nouvelle, avec ses couleurs
  par défaut, son texte vide. Pas de doublon « interdit ».
- **Dupliquer** (bouton ⧉ sur chaque carte, exemples fournis compris) crée une entrée **copie** : même mot, même texte, mêmes couleurs
  et même fond (pour un exemple fourni : le texte est sa légende, modifiable). Elle est ajoutée en fin de liste et sélectionnée.
  **C'est la façon d'avoir la même tresse avec d'autres couleurs : on la duplique, puis on colore la copie.** Retaper le mot en
  fait autant, avec les couleurs par défaut.
- **Un clic sur un exemple ou sur une carte ne crée rien** : il sélectionne.
- **Changer une couleur ne crée jamais d'entrée.** Cela met à jour l'entrée en question, celle qui est sélectionnée.
- **Les pastilles et le carré sont à côté de la tresse courante** (dans la carte « Le mot », juste au-dessus des vues : on règle la
  couleur là où on voit l'effet). Ils agissent sur l'entrée sélectionnée ; quand la tresse courante n'est pas une entrée (un exemple,
  ou un mot qui vient du lien `#…`), ils sont grisés, avec à côté un bouton « Dupliquer pour la colorer » : un exemple fourni ne se
  recolore pas, on le duplique d'abord.
- **Plafonds** : 30 entrées, 100 caractères de texte, dits à la personne quand on les atteint ; au plafond, ⧉ et la création sont
  refusées avec ce message.

## Ce que le code fait aujourd'hui (`web/ardoise.js`)

- Les exemples sont le tableau `EXEMPLES` (`nom`, `mot`, `legende`) ; `demarre()` en fait des `<button class="exemple">`.
- **Une seule palette** pour toutes les vues, `PALETTE` (8 couleurs, autant que `MAX_BRINS`) : le brin *i* du diagramme de tresse,
  le lacet image de x_i dans les quatre films et la ligne x_i ↦ … de l'action sur F_n. Les canvas l'emploient au dessin ; le texte
  de l'action sur F_n passe par les variables CSS `--c0 … --c7` (éclaircies en thème sombre).
- **Le fond des canvas** est `'#fff'` en dur (le diagramme de tresse, `dessineImage`, `Lecteur.efface`).
- Les films sont gardés **sous forme de polylignes** et redessinés à chaque image : *changer une couleur ne recalcule rien*, il suffit
  de redessiner (les films prennent de quelques secondes à plusieurs minutes à calculer).
- Aucun usage de `localStorage` pour l'instant.

## Les données

Une clé du `localStorage`, par exemple `ardoise.tresses`, qui contient un objet versionné :

```json
{ "version": 1,
  "courant": "k3f9",
  "tresses": [
    { "id": "k3f9", "mot": [1, -2, 1], "texte": "mon essai",
      "couleurs": ["#d92626", "#1a9926", "#2640d9"], "fond": "#ffffff" }
  ] }
```

- **`id`** identifie l'entrée (le mot ne le peut plus : plusieurs entrées peuvent avoir le même mot). Un compteur ou une courte chaîne
  aléatoire, unique dans la liste.
- **`courant`** : l'entrée sélectionnée quand la page a été quittée, pour la retrouver au chargement (avec ses couleurs). Au chargement,
  un lien `#mot` l'emporte : l'entrée courante n'est reprise que si son mot est celui du lien ; sinon aucune entrée n'est sélectionnée.
- `couleurs` a **autant d'éléments que de brins** (le plus grand indice + 1, au plus 8) ; `fond` est une couleur.
- Tout est enveloppé de `try/catch` : navigation privée, stockage refusé ou plein → la page marche, sans mémoire (et le dit une
  fois). Le stockage est local au navigateur : rien n'est envoyé, rien ne passe par le serveur.

## Créer une entrée : ce qui demande un peu de soin

Il faut distinguer *taper dans le champ* de *remplir le champ* (un clic sur un exemple ou une carte remplit le champ, sans rien créer).
Un drapeau « modifié » se lève à chaque événement `input` de l'utilisateur et retombe à la validation, à une sélection, ou quand
l'entrée est créée. À la validation (Entrée, ou perte du focus) :

- drapeau levé et mot valide → **nouvelle entrée**, sélectionnée (retaper le même mot suffit donc : l'événement `input` lève le drapeau) ;
- drapeau baissé → rien (une simple sortie du champ, ou Entrée deux fois, ne crée rien).

Les couleurs d'une entrée *saisie* sont celles par défaut (pas celles de l'entrée précédente) : c'est prévisible, et on les change
ensuite. Pour « la même, avec une couleur changée », on duplique : la copie garde les couleurs de l'originale.

## L'interface

**Les cartes.** Aujourd'hui une carte est un `<button>` ; elle va recevoir des boutons (dupliquer, effacer) et, pour les tresses
mémorisées, un champ de texte, et un bouton ne peut pas contenir d'éléments interactifs. Donc, **pour toutes les cartes** : un `<div>`
qui contient un bouton principal (le nom : c'est lui qui sélectionne) et, à côté, ⧉ (toutes les cartes) et ✕ (les tresses mémorisées),
puis le texte (le champ libre pour les tresses mémorisées, la légende fixe pour les exemples). Pour reconnaître les tresses mémorisées dans la
liste, la carte montre **les couleurs de l'entrée en petits points sans interaction** (une rangée de points, un carré pour le fond).

```
┌───────────────────────────────┐
│ σ₁σ₂⁻¹σ₁                  ⧉ ✕ │   ← le mot, comme le nom d'une tresse fournie ; ⧉ duplique, ✕ efface
│ mon essai du 22 novembre      │   ← texte libre, modifiable sur place (à la place de la légende)
│ • • •  ▪                      │   ← aperçu des couleurs de l'entrée (le réglage est dans « Le mot »)
└───────────────────────────────┘
```

- **Le nom** : le mot écrit en σ, comme celui des exemples (la fonction existe déjà dans le banc d'essai, `nomLettre`) ; tronqué avec
  des points de suspension s'il est long, le mot entier en `title`.
- **Dupliquer** : `aria-label="Dupliquer la tresse σ₁σ₂⁻¹σ₁"`. Pas de confirmation (rien n'est perdu) ; la copie apparaît en fin de liste,
  sélectionnée, et la liste y défile si besoin.
- **La croix** : `aria-label="Effacer la tresse σ₁σ₂⁻¹σ₁"`. Confirmation **sur place** (la carte devient « Effacer ? Oui Non »,
  le focus va sur « Non ») plutôt que `window.confirm`, qui bloque la page et s'affiche mal sur téléphone. Échap annule. Effacer l'entrée
  sélectionnée ne change pas le champ ni les films, elle perd seulement ses couleurs (retour au défaut).
- **Le texte libre** : un champ discret à la place de la légende, avec une invite grisée (« ajouter une note ») ; enregistré à Entrée
  ou à la sortie du champ, Échap annule.

**La carte « Le mot »** (en dessous des cartes, au-dessus des vues) reçoit, sous le mot en notation mathématique, **la rangée de
pastilles** : `<input type="color">`, une par brin, rondes (`border-radius: 50%`), puis **le carré du fond**, le même contrôle avec un
coin à peine arrondi. Le sélecteur de couleur du système s'ouvre au clic. Chaque contrôle a une étiquette (« Couleur du brin 2 »,
« Couleur du fond »). Pendant qu'on déplace le curseur du sélecteur (événement `input`), les vues se redessinent en direct ; la valeur
est enregistrée à la fin du geste (`change`). Quand l'entrée n'existe pas, les contrôles sont grisés (voir les règles).

**Appliquer les couleurs.** `PALETTE` devient une liste courante (copie de la palette par défaut, remplacée par les couleurs de
l'entrée sélectionnée) ; les variables `--c0 … --c7` sont posées sur `document.documentElement` pour le texte de l'action sur F_n ;
le fond `'#fff'` devient une variable. Un changement redessine le diagramme de tresse, l'action sur F_n et l'image courante de chaque
film (une méthode `recolore()` sur `Lecteur`) : immédiat, sans recalcul. Le fond concerne le diagramme de tresse et les quatre
méandres ; l'escargot et les iris, qui ne dépendent pas du mot, restent comme ils sont.

## Exporter et importer

Un fichier JSON, le même objet que celui du `localStorage` (`version`, `tresses` ; sans `courant`) : « Exporter mes tresses » télécharge
`mes-tresses.json` ; « Importer » lit un fichier choisi par la personne.

- À l'import, on **valide tout** avant d'écrire : version connue, `mot` = liste d'entiers non nuls dans les limites de la page
  (8 brins, 40 lettres), `couleurs` = couleurs valides en nombre égal aux brins, `fond` = couleur valide, `texte` tronqué à 100
  caractères, jamais de HTML (le texte est affiché comme du texte). Un fichier invalide est refusé en entier, avec la raison.
- Les `id` du fichier sont **ignorés** : de nouveaux sont attribués (deux fichiers peuvent avoir les mêmes). Une entrée identique à
  une entrée présente (même mot, même texte, mêmes couleurs, même fond) est sautée : réimporter son propre fichier ne double rien.
- Le plafond de 30 s'applique : ce qui dépasse est dit et ignoré, rien n'est écrit en silence.
- C'est aussi la sauvegarde : la mémoire du navigateur s'efface avec les données du site.

## Points délicats

- **Contraste.** Un brin de la couleur du fond disparaît. Un petit avertissement (⚠) sur la pastille quand le rapport de contraste
  avec le fond est inférieur à 3 : un conseil, pas un blocage.
- **Thème sombre.** Les variables `--cN` sont éclaircies en thème sombre ; une couleur choisie par la personne, posée en ligne,
  l'emporte dans les deux thèmes : c'est son choix, mais un brin sombre sera difficile à lire dans le texte d'action sur F_n.
  Le fond choisi ne touche que les canvas, pas le thème de la page.
- **Partage.** Le lien `#mot` ne porte que le mot, pas les couleurs ; l'export est le moyen de transmettre des couleurs. Plus tard,
  peut-être un paramètre dans le lien.
- **Accessibilité et tactile.** Zones cliquables d'au moins 32 px (croix, pastilles), navigation au clavier dans l'ordre nom → note →
  croix, annonce de la suppression (`aria-live`). Sur téléphone, la rangée de pastilles passe à la ligne au-delà de 6 brins.

## Étapes

1. Module de mémoire (`ardoise.tresses`) : lire, ajouter, supprimer, modifier texte et couleurs, `courant` ; tests à la main dans un
   profil neuf et en navigation privée.
2. Cartes en `div` (nom, ⧉ sur toutes, ✕ et texte libre sur les tresses mémorisées, aperçu des couleurs) ; création à la validation
   (drapeau « modifié ») et par ⧉.
3. Palette et fond courants : `PALETTE`, variables CSS, fond ; `recolore()` sur les lecteurs et sur le diagramme.
4. Pastilles et carré du fond dans la carte « Le mot », aperçu en direct, avertissement de contraste, état grisé.
5. Export / import avec validation.
6. Textes de la page, `web/README.md`, `docs/page_web.md` ; vérification dans Firefox (profil neuf, thèmes clair et sombre, largeur
   de téléphone, navigation privée).
