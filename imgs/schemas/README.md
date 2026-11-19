# Schémas d'explication des méthodes de dessin

Six petits schémas SVG (440 × 250, couleurs de la page) pour les infobulles de la page web (le « ? » à côté de chaque titre) : le diagramme de tresse, l'action sur le groupe libre, et un par méthode de dessin des méandres :

| fichier | méthode | ce qu'il montre |
|---|---|---|
| `tresse.svg` | diagramme de tresse | un croisement σᵢ et son inverse (quel brin passe dessus), puis σ₁σ₂⁻¹ lu de haut en bas |
| `fn.svg` | action sur F_n | les lacets x₁ et x₂ avant et après σ₁, et x₁ ↦ x₁x₂x₁⁻¹, x₂ ↦ x₁ (dessiné avec le moteur réel : `schema_fn.js`) |
| `diagramme.svg` | diagramme de courbes | un point fixe à gauche ; les arcs sont les segments de l'axe, que le demi-tour des trous 2 et 3 emporte |
| `lacets.svg` | lacets conformes | des demi-cercles du demi-plan, et leurs images par la transformation conforme : des arcs à angle droit autour des sommets de la ligne brisée L–A–B–R |
| `triangulation.svg` | triangulation mobile | un maillage, des points sur ses arêtes (deux brins emboîtés autour d'un trou, départ au clou) ; les trous tournent et les brins se tendent |
| `rubans.svg` | rubans | un ruban par trou voyageur, du trou fixe (la « queue ») au trou voyageur ; après le demi-tour, les rubans s'enroulent |

Générés par `genere_schemas.py` (Python seul, rien à installer) : `python imgs/schemas/genere_schemas.py` ; `fn.svg` par `node imgs/schemas/schema_fn.js`
(après `web/construit.sh`). Les deux scripts écrivent aussi dans `web/schemas/`, d'où la page les charge.
Aperçu : `apercu.png` (fabriqué avec `rsvg-convert`, ignoré par git comme les autres PNG).
