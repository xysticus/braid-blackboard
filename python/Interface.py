'''Interface `ipywidgets` de l'ardoise (notebook `ipynbks/Ardoise.ipynb`) : lecture d'un mot de tresse écrit à la main, lecteur
de film (curseur et bouton de lecture), les quatre films de lacets (diagramme de courbes, lacets conformes, triangulation
mobile, rubans), l'escargot et le bouquet, et l'ardoise elle-même (`Ardoise`). Ne contient aucun calcul sur les tresses : il les demande à `Conforme.py`,
`Arcs.py` et `Triangulation.py`, et au notebook pour le diagramme de tresse et l'action sur le groupe libre.
Module : rien ne s'exécute à l'import.'''

import functools
import re
import weakref
from io import BytesIO

import ipywidgets as widgets
from IPython.display import display

from Conforme import dessins_conforme, surface_conforme
from Arcs import FilmArcs, DiagrammeCourbes
from Triangulation import Film

# La couleur de x_i : celle de son lacet dans les films (`tresses.peint`) et de son brin dans le diagramme de tresse.
COULEURS = [(1, 0, 0), (0, .7, 0), (0, 0, 1), (.7, .7, 0), (.7, 0, .7), (0, .7, .7)]

EXEMPLES = [
    ('σ₁', [1], 'le demi-tour le plus simple'),
    ('Δ₅', [1, 2, 3, 4, 1, 2, 3, 1, 2, 1], 'demi-tour positif à 5 brins'),
    ('Δ₅⁻¹', [-1, -2, -1, -3, -2, -1, -4, -3, -2, -1], 'demi-tour négatif à 5 brins'),
    ('(σ₁σ₂)³', [1, 2, 1, 2, 1, 2], 'tour complet à 3 brins : conjugaison par x₁x₂x₃'),
    ('σ₁σ₂σ₁σ₂⁻¹σ₁⁻¹σ₂⁻¹', [1, 2, 1, -2, -1, -2], 'un mot qui vaut la tresse nulle'),
    ('σ₂σ₁σ₂⁻¹', [2, 1, -2], 'même tresse que la suivante'),
    ('σ₁⁻¹σ₂σ₁', [-1, 2, 1], 'même tresse que la précédente'),
    ('σ₁σ₂⁻¹', [1, -2], 'courte, mais pseudo-Anosov'),
    ('(σ₁σ₂⁻¹)³', [1, -2, 1, -2, 1, -2], '6 lettres, 51 dans F₃ : croissance exponentielle'),
    ('σ₁σ₂σ₃σ₄', [1, 2, 3, 4], 'la rotation de 5 trous'),
    ('σ₄σ₃σ₁⁻²σ₂σ₄⁻¹σ₁', [4, 3, -1, -1, 2, -4, 1], 'une tresse à enroulements décroissants'),
    ('σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂', [1, -2, 1, -2, 1, -2, 3, -1, 2], 'une tresse à nombreux enroulements'),
]

# Les limites évitent les calculs trop longs.
MAX_BRINS, MAX_LETTRES = 8, 40
MAX_BRINS_LACETS, MAX_LETTRES_LACETS = 6, 14    # celles des films « lacets » et « triangulation »

INDICES = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
EXPOSANTS = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')


def nb_brins(mot):
    return max(map(abs, mot), default=0) + 1


def lis_mot(texte):
    """La tresse (liste d'entiers) écrite dans le texte : « 1 -2 3 », « σ1 σ2^-1 », « σ₁σ₂⁻¹ » ou « s1^3 s2 » (un exposant
    répète la lettre). ValueError, avec un message, si on ne la comprend pas ou si elle dépasse les limites."""
    t = texte.strip()
    if not t: return []
    t = t.translate(INDICES).replace('⁻', '^-').translate(EXPOSANTS)
    t = re.sub(r'[{}]', '', t)
    t = re.sub(r'[σΣsS,;]', ' ', t)
    t = re.sub(r'\s*\^\s*', '^', t)
    mot = []
    for jeton in t.split():
        m = re.fullmatch(r'(-?)(\d+)(?:\^(-?)(\d+))?', jeton)
        if not m: raise ValueError(f'je ne comprends pas « {jeton} »')
        indice = int(m[2])
        if indice == 0: raise ValueError("σ₀ n'existe pas : les indices commencent à 1")
        signe, fois = (-1 if m[1] == '-' else 1), 1
        if m[4] is not None:
            fois = int(m[4])
            if m[3] == '-': signe = -signe
            if fois > MAX_LETTRES: raise ValueError(f'exposant trop grand dans « {jeton} »')
        mot += [signe * indice] * fois
        if len(mot) > 10 * MAX_LETTRES: break
    if len(mot) > MAX_LETTRES: raise ValueError(f'{len(mot)} lettres : au plus {MAX_LETTRES} sont acceptées')
    if nb_brins(mot) > MAX_BRINS:
        raise ValueError(f'{nb_brins(mot)} brins : au plus {MAX_BRINS} sont acceptés (σ₁ … σ{MAX_BRINS - 1})')
    return mot


def hors_limites_des_lacets(mot):
    """Les raisons pour lesquelles les films « lacets » et « triangulation » ne sont pas calculés (liste vide s'ils
    le sont)."""
    raisons = []
    if nb_brins(mot) > MAX_BRINS_LACETS: raisons.append(f'{nb_brins(mot)} brins (limite : {MAX_BRINS_LACETS})')
    if len(mot) > MAX_LETTRES_LACETS: raisons.append(f'{len(mot)} lettres (limite : {MAX_LETTRES_LACETS})')
    return raisons


def mot_en_latex(tresse):
    return ''.join(f'\\sigma_{{{abs(k)}}}' + ('^{-1}' if k < 0 else '') for k in tresse) or '1'


def mot_en_texte(mot):
    return ''.join(f'x{abs(g)}' + ('⁻¹' if g < 0 else '') for g in mot) or '1'


# ---------------------------------------------------------------- les films

def png(surface):
    """Les octets du PNG d'une surface Cairo."""
    tampon = BytesIO()
    surface.write_to_png(tampon)
    return tampon.getvalue()


LECTEURS = weakref.WeakSet()    # les lecteurs créés (voir `en_calcul`)


def lecteur(images, largeur=500, ms=40):
    """Un film : la suite d'images (octets PNG), avec un bouton de lecture et un curseur (une image toutes les ms
    millisecondes, 25 images par seconde par défaut)."""
    vue = widgets.Image(value=images[0], format='png', width=largeur)
    jeu = widgets.Play(min=0, max=len(images) - 1, step=1, interval=ms, value=0)
    curseur = widgets.IntSlider(min=0, max=len(images) - 1, value=0, readout=False,
                                layout=widgets.Layout(width=f'{largeur - 120}px'))
    widgets.jslink((jeu, 'value'), (curseur, 'value'))          # la lecture avance le curseur
    curseur.observe(lambda changement: setattr(vue, 'value', images[changement['new']]), names='value')
    boite = widgets.VBox([vue, widgets.HBox([jeu, curseur])])
    LECTEURS.add(boite)
    return boite


def en_calcul(film):
    """Décorateur des fonctions qui calculent un film. Pendant le calcul, le noyau ne répond plus : un lecteur déjà affiché
    ferait avancer son curseur sans changer d'image. On le cache jusqu'à la fin du calcul ; le nouveau lecteur n'existe
    qu'une fois le film prêt."""
    @functools.wraps(film)
    def calcule(*arguments, **options):
        caches = [l for l in LECTEURS if l.layout.display != 'none']
        for l in caches: l.layout.display = 'none'
        try:
            return film(*arguments, **options)
        finally:
            for l in caches: l.layout.display = None
    return calcule


@en_calcul
def film_diagramme_de_courbes(tresse):
    """Un seul point fixe, à gauche ; les arcs sont les segments de l'axe, que la tresse emporte (`Arcs.DiagrammeCourbes`)."""
    film = DiagrammeCourbes(tresse)
    images = [png(film.cadre(lisere=True))]
    for sigma in tresse:
        film.lettre(sigma, rendu=lambda f: images.append(png(f.cadre(lisere=True))))
    return lecteur(images)


@en_calcul
def film_lacets(tresse):
    """Les lacets par représentation conforme (`Conforme.dessins_conforme`)."""
    dessins, durees, anomalies = dessins_conforme(tresse, hauteur=800, largeur=800, marge=60)
    return lecteur([png(surface_conforme(d, 800, 800, 60, largeur_brin=3)) for d in dessins])


@en_calcul
def film_triangulation(tresse):
    """Les lacets sur une triangulation mobile (`Triangulation.Film`), sans tracer ses arêtes."""
    film = Film(tresse)
    images = [png(film.cadre(ecart=film.dispositions[0][1], avec_arêtes=False))]
    for sigma in tresse:
        film.lettre(sigma, avec_arêtes=False, rendu=lambda surface: images.append(png(surface)))
    return lecteur(images)


@en_calcul
def film_rubans(tresse):
    """Les lacets sans clou : le bord d'un ruban tendu entre un trou fixe et son trou voyageur (`Arcs.FilmArcs`)."""
    film = FilmArcs(tresse, ecart_fixes=30)
    images = [png(film.cadre(rubans=True))]
    for sigma in tresse:
        film.lettre(sigma, rendu=lambda f: images.append(png(f.cadre(rubans=True))))
    return lecteur(images)


@en_calcul
def film_escargot(duree=12.0, images_par_seconde=25):
    """Un escargot fait de rubans : trous fixes à gauche, chorégraphie libre (`Escargot.Escargot`). Pas de mot de tresse."""
    from Escargot import Escargot
    escargot = Escargot()
    images = [png(escargot.dessine(0.0))]
    for n in range(1, round(duree * images_par_seconde) + 1):
        t = n / images_par_seconde
        escargot.deplace(escargot.choregraphie(t), pas_max=2 * escargot.e)
        images.append(png(escargot.dessine(t)))
    return lecteur(images, largeur=640, ms=round(1000 / images_par_seconde))


@en_calcul
def film_bouquet(duree=13.5, images_par_seconde=25, saccade=2):
    """Un bouquet d'iris qui pousse : les trous montent depuis le clou et tirent des lacets (`Bouquet.Pousse`). Pas de mot de
    tresse. Chaque image calculée est montrée `saccade` fois (l'aspect image par image des films de plantes qui poussent)."""
    import copy
    from Bouquet import Pousse, BOUQUET
    pousse = Pousse(copy.deepcopy(BOUQUET))
    pas = saccade / images_par_seconde
    images = [png(pousse.dessine(0.0))]
    for n in range(1, round(duree / pas) + 1):
        pousse.deplace(*pousse.cibles(n * pas), pas_max=2 * pousse.e)
        images.append(png(pousse.dessine(n * pas)))
    return lecteur(images, largeur=420, ms=round(1000 * pas))


def a_la_demande(film, etiquette='Calculer le film'):
    """Un bouton qui calcule le film (une fonction sans argument) au clic, puis montre son lecteur à la place du bouton.
    Tant qu'on ne clique pas, rien ne se calcule : « exécuter toutes les cellules » reste rapide."""
    bouton = widgets.Button(description=etiquette, button_style='primary')
    sortie = widgets.Output()

    def clic(_):
        bouton.disabled = True
        sortie.clear_output()
        with sortie:
            display(widgets.HTML('Calcul en cours…'))
        try:
            resultat = film()
            bouton.layout.display = 'none'
        except Exception as erreur:
            resultat = widgets.HTML(f'<span style="color:#b00020">Le calcul a échoué : {type(erreur).__name__} {erreur}</span>')
            bouton.disabled = False
        sortie.clear_output()
        with sortie:
            display(resultat)

    bouton.on_click(clic)
    return widgets.VBox([bouton, sortie])


# (titre de l'onglet, fonction, limité par MAX_BRINS_LACETS et MAX_LETTRES_LACETS)
FILMS = [('Courbes', film_diagramme_de_courbes, False),
         ('Lacets', film_lacets, True),
         ('Triangulation', film_triangulation, True),
         ('Rubans', film_rubans, False)]


# ---------------------------------------------------------------- l'ardoise

class Ardoise:
    """Un champ pour le mot, un menu d'exemples, le diagramme de tresse et l'action sur le groupe libre tout de suite, puis
    un onglet par film, calculé quand on l'ouvre.
    diagramme(tresse) : la surface Cairo du diagramme de tresse ; images_de_tresse(tresse) : l'image de chaque générateur
    x_i par la tresse (une liste de mots)."""

    def __init__(self, diagramme, images_de_tresse, mot='1 -2 1 -2 3'):
        self.diagramme, self.images_de_tresse = diagramme, images_de_tresse
        self.etat = {'mot': None, 'faits': set(), 'choix': False}    # le mot dessiné, les onglets déjà calculés
        self.champ = widgets.Text(value=mot, description='Mot :', continuous_update=False,
                                  placeholder='1 -2 3   ou   σ1 σ2^-1   ou   s1^3 s2', layout=widgets.Layout(width='520px'))
        self.menu = widgets.Dropdown(options=[('(un exemple)', -1)] + [(nom, i) for i, (nom, _, _) in enumerate(EXEMPLES)],
                                     value=-1, description='Exemples :')
        self.bouton = widgets.Button(description='Dessiner', button_style='primary')
        self.message = widgets.HTML()
        self.limites = widgets.HTML(
            f'<small>Limites : <b>{MAX_BRINS} brins</b> (σ₁ … σ{MAX_BRINS - 1}) et <b>{MAX_LETTRES} lettres</b>. '
            f'Au-delà de <b>{MAX_BRINS_LACETS} brins</b> ou de <b>{MAX_LETTRES_LACETS} lettres</b>, les films « lacets » et '
            f'« triangulation » ne sont pas calculés (les autres le sont).</small>')
        self.mot_math = widgets.HTMLMath()
        self.image = widgets.Image(format='png')
        self.action = widgets.HTML()
        self.onglets = widgets.Tab(children=[widgets.Output() for _ in FILMS])
        self.onglets.titles = [titre for titre, _, _ in FILMS]
        self.champ.observe(self._champ_change, names='value')
        self.menu.observe(self._choisit, names='value')
        self.bouton.on_click(self.dessine)
        self.onglets.observe(lambda changement: self.calcule_onglet(changement['new']), names='selected_index')

    def affiche(self):
        """Montre l'ardoise et dessine le mot du champ."""
        display(widgets.VBox([self.champ, widgets.HBox([self.menu, self.bouton]), self.message, self.limites, self.mot_math,
                              widgets.HBox([self.image, self.action]), self.onglets]))
        self.dessine()

    def action_en_html(self, tresse):
        """Les images des générateurs x_i, une ligne par x_i, dans la couleur du lacet."""
        lignes = []
        for i, image in enumerate(self.images_de_tresse(tresse), start=1):
            r, v, b = (round(255 * c) for c in COULEURS[(i - 1) % len(COULEURS)])
            lignes.append(f'<span style="color:rgb({r},{v},{b})">x{i}  ↦  {mot_en_texte(image)}</span>')
        return '<pre style="white-space:pre-wrap;max-width:460px">' + '\n'.join(lignes) + '</pre>'

    def calcule_onglet(self, k):
        """Calcule le film de l'onglet k pour le mot dessiné, si ce n'est pas déjà fait."""
        mot = self.etat['mot']
        if mot is None or k in self.etat['faits']: return
        self.etat['faits'].add(k)
        titre, fabrique, limite = FILMS[k]
        sortie = self.onglets.children[k]
        sortie.clear_output()
        raisons = hors_limites_des_lacets(mot) if limite else []
        if raisons:
            with sortie:
                display(widgets.HTML(f'Ce mot a {" et ".join(raisons)} : trop pour ce film. Les autres films sont calculés.'))
            return
        with sortie:
            display(widgets.HTML('Calcul en cours…'))
        try:
            resultat = fabrique(mot)
        except Exception as erreur:
            resultat = widgets.HTML(f'<span style="color:#b00020">Le calcul a échoué : {type(erreur).__name__} {erreur}</span>')
        sortie.clear_output()
        with sortie:
            display(resultat)

    def dessine(self, *_, legende=None):
        """Lit le champ ; si le mot est bon, dessine le diagramme et l'action, et vide les onglets."""
        try:
            mot = lis_mot(self.champ.value)
        except ValueError as erreur:
            self.message.value = f'<span style="color:#b00020">{erreur}</span>'
            return
        if not mot:
            self.message.value = 'Écrire au moins une lettre.'
            return
        self.etat['mot'], self.etat['faits'] = mot, set()
        brins, lettres = nb_brins(mot), len(mot)
        self.message.value = (f'Ce mot : <b>{brins} brins</b>, <b>{lettres} lettre{"s" if lettres > 1 else ""}</b>.'
                              + (' <span style="color:#b36b00">Les films « lacets » et « triangulation » ne sont pas calculés '
                                 'pour ce mot.</span>' if hors_limites_des_lacets(mot) else '')
                              + (f' <i>{legende}</i>' if legende else ''))
        self.mot_math.value = f'${mot_en_latex(mot)}$'
        self.image.value = png(self.diagramme(mot))
        self.action.value = self.action_en_html(mot)
        for sortie in self.onglets.children: sortie.clear_output()
        self.calcule_onglet(self.onglets.selected_index)

    def _choisit(self, changement):
        i = changement['new']
        if i < 0: return
        self.etat['choix'] = True                      # le champ change : ne pas dessiner deux fois
        self.champ.value = ' '.join(map(str, EXEMPLES[i][1]))
        self.etat['choix'] = False
        self.dessine(legende=EXEMPLES[i][2])

    def _champ_change(self, changement):
        if self.etat['choix']: return
        self.menu.value = -1
        self.dessine()
