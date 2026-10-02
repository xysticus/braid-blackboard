import functools
import itertools
import operator
import math
import cairo
import numpy as np
from PIL import Image


def morphisme_identite(abs_max_de_tresse):
    '''Renvoie le morphisme identite pour une tresse avec abs_max_de_tresse
    comme générateur qui a la plus grosse valeur absolue'''
    return [[e] for e in range(1, abs_max_de_tresse + 2)]

def inverse(mot):
    return [-e for e in reversed(mot)]

def conjugaison_locale (sigma, images):
    '''Sert à calculer l'automorphisme de fn associé à une tresse.
    L'automorphisme est donné par l'image de chaque des générateurs.
    Ces images sont rangées dans le tableau "images".
    A l'index i on trouve l'image de x_(i+1) '''
    xi = abs(sigma)
    x1 = images[xi - 1]
    x2 = images[xi]
    if sigma > 0: 
        images[xi - 1] = x1 + x2 + inverse(x1) # on conjugue à droite
        images[xi] = x1
    else:
        images[xi - 1] = x2
        images[xi] = inverse(x2) + x1 + x2 # on conjugue à gauche
        
def simplifie(mot_de_fn): 
    '''Simplifie entièrement un mot de fn
    Travaille par effet de bord'''
    i = 0 
    while i < len(mot_de_fn) - 1: 
        if mot_de_fn[i] == -mot_de_fn[i + 1]: 
            del mot_de_fn[i:i+2] 
            i-=1 
            if i < 0: i = 0 
        else: i+=1
            
applatir = itertools.chain.from_iterable

def calcule_autofn_de_tresse(tresse, nb_trous=None):
    '''Calcule l'automorphisme du groupe libre associé à une tresse.
    La tresse est donnée par la liste de ses générateurs.
    Par défaut le nombre de trous est déduit de la tresse.'''
    if nb_trous is None: nb_trous = 6 if not(tresse) else max(map(operator.abs, tresse)) + 1
    auto = morphisme_identite(nb_trous - 1)
    # on avance sur la tresse par composition (donc à l'envers)
    for sigma in reversed(tresse): conjugaison_locale(sigma, auto) 
    for a in auto: simplifie(a)

    return auto


# Dessin des automorphismes de fn

def calcule_arcs(liste):
    '''Prend une liste de générateurs de fn et calcule les arcs correspondant.
    Les arcs du haut aux indices pairs ceux du bas aux indices impairs.
    Renvoie une liste de couples qui est la liste des extrémités des arcs.
    Le signe des extrémités des arcs donne le sens de l'arc.'''
    debut = liste[0]
    courant = liste[0]
    resultat = []
    for i in range(1,len(liste)):
        match liste[i]:
            # on est sur une suite monotone, on continue
            case t if t - courant == 1: courant = t

            # une suite monotone se termine faut écrire les arcs 
            case t : 
                resultat.append((debut, courant)) # on écrit l'arc du haut

                # pour l'arc du bas ça se complique
                signe_bas = 1 if abs(t) - abs(courant) < 0 else - 1 # on calcule le sens de l'arc

                # bon bhen là c'est des cas à gérer en fonction du fait que l'on arrive
                # par le dedans de l'arc du bas ou pas et de si on est à gauche ou à droite.
                if signe_bas < 0:
                    tt = abs(courant) + 1 if courant > 0 else abs(courant)
                    qq = abs(t) - 1 if t > 0 else abs(t)
                else:
                    tt = abs(courant) if courant > 0 else abs(courant) - 1
                    qq = abs(t) if t > 0 else abs(t) + 1
                resultat.append((tt * signe_bas, qq * signe_bas)) # on écrit l'arc du bas en rajoutant son signe                         
                courant = t
                debut = t

    # on écrit le dernier arc. C'est un arc du haut.
    resultat.append((debut, courant))
    return resultat

# tests sur la tresse compliquée
t = calcule_autofn_de_tresse([1,1,2,2])
print(t)

d = calcule_arcs(t[0]) 
print(d)

print(calcule_arcs(t[1]))

print(calcule_arcs(t[2]))

def dedans_extrm(l,start,a,b,extrm,f_extrm):
    for i in range(start,len(l)-1,2):
        match l[i] , l[i+1]:
            case x,y if x>a and x< b and y>a and y<b: extrm = f_extrm(extrm, x, y)
    return extrm

assert dedans_extrm([4, 6, 1, 5, 4, 7, 4, 5], 0, 1, 6, 0, max) == 5

assert dedans_extrm([4, 6, 1, 4, 4, 7, 4, 4], 0, 1, 6, 0, max) == 4

assert dedans_extrm([4, 6, 1, 5, 4, 7, 4, 5], 1, 1, 6, 0, max) == 5

assert dedans_extrm([4, 6, 1, 5, 4, 7, 4, 5], 0, 1, 6, 1, min) == 1

assert dedans_extrm([4, 6, 1, 5, 4, 7, 3, 5], 0, 1, 6, 10, min) == 3

def decale(liste, index):
    return list(map(lambda x: x+1 if x >= index else x, liste))

decale([1,2,5,2,2,5,5,3],3)

# Positionnement des intersections par comparaison de deux points.
# Deux points dans le même intervalle : on suit les deux courbes côte à côte jusqu'à ce qu'elles
# se séparent. Là où elles se séparent on sait laquelle est à gauche. Chaque arc parcouru
# en parallèle inverse l'ordre (les arcs sont emboîtés). Il suffit ensuite de trier chaque intervalle.

def intervalles(mot):
    '''Suite des intervalles où le lacet d'un mot de fn coupe l'axe.
    L'intervalle k est entre le trou k et le trou k+1 (l'intervalle 0 est à gauche du trou 1).
    De l'indice 2i à 2i+1 c'est un arc du haut, de 2i+1 à 2i+2 un arc du bas.
    Le premier et le dernier point sont reliés au clou par le bas.'''
    def bouts(arc_du_haut):
        debut, fin = arc_du_haut
        return (debut - 1, fin) if debut > 0 else (-debut, -fin - 1)
    return list(applatir(bouts(arc) for arc in calcule_arcs(mot)[::2]))

assert intervalles([1]) == [0, 1]
assert intervalles([-2]) == [2, 1]
assert intervalles([1, 2, 3, 2, -3, -2, -1]) == [0, 3, 1, 2, 3, 0]

def voisin(lacet, j, en_haut):
    '''Indice du point relié au point j du lacet par l'arc du haut (ou du bas).
    None si c'est le clou.'''
    if en_haut: return j ^ 1
    k = j + 1 if j % 2 else j - 1
    return k if 0 <= k < len(lacet) else None

def suit_en_parallele(lacets, p, q, en_haut):
    '''Compare p et q en partant vers le haut (ou vers le bas).
    -1 si p est à gauche de q, 1 à droite, 0 si les deux courbes arrivent ensemble au clou.'''
    signe = 1
    while True:
        k = lacets[p[0]][p[1]]
        jp = voisin(lacets[p[0]], p[1], en_haut)
        jq = voisin(lacets[q[0]], q[1], en_haut)
        if jp is None and jq is None: return 0
        # le clou est en dessous de tous les arcs du bas : un point relié au clou n'est jamais englobé
        if jp is None: return -signe if lacets[q[0]][jq] > k else signe
        if jq is None: return signe if lacets[p[0]][jp] > k else -signe
        a, b = lacets[p[0]][jp], lacets[q[0]][jq]
        if a != b:
            meme_cote = (a > k) == (b > k)
            # du même côté, l'arc qui va le plus loin englobe l'autre ;
            # de côtés opposés, celui qui part à gauche est à gauche
            p_a_gauche = a > b if meme_cote else a < b
            return -signe if p_a_gauche else signe
        p, q = (p[0], jp), (q[0], jq)
        signe = -signe
        en_haut = not en_haut

def compare_points(lacets, p, q):
    '''Ordre gauche-droite de deux points d'un même intervalle.
    Un point est un couple (numéro du lacet, indice dans le lacet).'''
    if p == q: return 0
    for en_haut in (True, False):
        r = suit_en_parallele(lacets, p, q, en_haut)
        if r: return r
    raise ValueError(f'points indiscernables {p} {q}')

def abscisses(lacets, nb_trous):
    '''Rang sur l'axe de chaque point et de chaque trou, de gauche à droite.
    Renvoie (rang des points, rang des trous, nombre total de rangs).'''
    par_intervalle = {}
    for i, lacet in enumerate(lacets):
        for j, k in enumerate(lacet):
            par_intervalle.setdefault(k, []).append((i, j))
    cle = functools.cmp_to_key(functools.partial(compare_points, lacets))
    rang_point, rang_trou, r = {}, {}, 0
    for k in range(nb_trous + 1):
        for p in sorted(par_intervalle.get(k, []), key=cle):
            rang_point[p] = r
            r += 1
        if k < nb_trous:
            rang_trou[k + 1] = r
            r += 1
    return rang_point, rang_trou, r

def croisements(lacets, rang_point):
    '''Liste des paires d'arcs qui se croisent. Vide si le dessin est correct.'''
    def corde(i, j, k): return tuple(sorted((rang_point[(i, j)], rang_point[(i, k)])))
    haut, bas, au_clou = [], [], []
    for i, lacet in enumerate(lacets):
        for j in range(len(lacet) - 1):
            (haut if j % 2 == 0 else bas).append(corde(i, j, j + 1))
        au_clou += [rang_point[(i, 0)], rang_point[(i, len(lacet) - 1)]]
    resultat = []
    for cordes in (haut, bas):
        resultat += [(c1, c2) for c1, c2 in itertools.combinations(cordes, 2)
                     if c1[0] < c2[0] < c1[1] < c2[1] or c2[0] < c1[0] < c2[1] < c1[1]]
    resultat += [(c, x) for c in bas for x in au_clou if c[0] < x < c[1]]
    return resultat

def verifie(tresse):
    lacets = [intervalles(mot) for mot in calcule_autofn_de_tresse(tresse)]
    rang_point, _, _ = abscisses(lacets, len(lacets))
    return croisements(lacets, rang_point) == []

assert verifie([])
assert verifie([1, 1, 2, 2])
assert verifie([4, 3, -1, -1, 2, -4, 1])
assert verifie([1, -2, 1, -2, 1, -2, 3, -1, 2])

def subdivise(points, pas=2):
    '''Ajoute des points sur les segments trop longs, pour que la torsion les courbe bien.'''
    resultat = [points[:1]]
    for p, q in zip(points[:-1], points[1:]):
        n = max(1, math.ceil(np.hypot(*(q - p)) / pas))
        resultat.append(p + np.outer(np.arange(1, n + 1) / n, q - p))
    return np.concatenate(resultat)

def geometrie_auto_de_tresse(tresse, nb_trous=None, hauteur=400, largeur=400):
    '''Dessin des images des générateurs de fn par l'automorphisme de la tresse, en polylignes.
    Renvoie (polylignes des lacets, positions des trous de gauche à droite, position du clou).
    Chaque polyligne part du clou et y revient.'''
    auto = calcule_autofn_de_tresse(tresse, nb_trous)
    lacets = [intervalles(mot) for mot in auto]
    rang_point, rang_trou, nb_rangs = abscisses(lacets, len(lacets))

    pas = (largeur - 40) / (nb_rangs - 1)
    def x(rang): return 20 + rang * pas
    y_axe = 0.4 * hauteur
    x_clou, y_clou = largeur / 2, hauteur - 10

    # on aplatit les arcs pour qu'ils tiennent en hauteur, en laissant de la place à l'éventail vers le clou
    def rayons(parite): return [abs(x(rang_point[(i, j)]) - x(rang_point[(i, j + 1)])) / 2
                                for i, lacet in enumerate(lacets) for j in range(parite, len(lacet) - 1, 2)]
    rayon_haut, rayon_bas = max(rayons(0)), max(rayons(1), default=0)
    aplati = min(1, (y_axe - 10) / rayon_haut, (hauteur - 70 - y_axe) / max(rayon_bas, 1))
    y_sous_arcs = y_axe + rayon_bas * aplati + 8 # le chemin vers le clou passe sous tous les arcs du bas

    # Cairo sert seulement à construire les chemins, que l'on récupère aplatis en polylignes
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    ctx.set_tolerance(0.05)

    def demi_ellipse(x1, x2, en_haut):
        ctx.save()
        ctx.translate((x1 + x2) / 2, y_axe)
        ctx.scale(abs(x2 - x1) / 2, abs(x2 - x1) / 2 * aplati)
        depart = math.pi if x1 < x2 else 0
        if en_haut == (x1 < x2): ctx.arc(0, 0, 1, depart, depart + math.pi)
        else: ctx.arc_negative(0, 0, 1, depart, depart - math.pi)
        ctx.restore()

    def arc_du_clou(xp, vers_le_clou):
        '''Arc de cercle entre le clou et le point (xp, y_sous_arcs), vertical en ce point.
        Les centres sont tous sur l'horizontale y_sous_arcs : deux de ces cercles ne se recoupent
        qu'au clou et en son symétrique au-dessus, donc les arcs ne se croisent pas.
        Si le point est trop loin, le cercle passerait sous le clou : on étire alors un quart de cercle
        en quart d'ellipse (quarts d'ellipse emboîtés de même centre).'''
        d, h = xp - x_clou, y_clou - y_sous_arcs
        if abs(d) < 1e-6:
            ctx.line_to(x_clou, y_clou if vers_le_clou else y_sous_arcs)
            return
        etire = max(1, abs(d) / h)
        d = d / etire
        centre = (d * d - h * h) / (2 * d) # abscisse relative au clou, dans le repère étiré
        rayon = abs(d - centre)
        a_point = 0 if d > centre else math.pi
        a_clou = math.atan2(h, -centre)
        ctx.save()
        ctx.translate(x_clou, y_sous_arcs)
        ctx.scale(etire, 1)
        if vers_le_clou: (ctx.arc if a_point == 0 else ctx.arc_negative)(centre, 0, rayon, a_point, a_clou)
        else: (ctx.arc_negative if a_point == 0 else ctx.arc)(centre, 0, rayon, a_clou, a_point)
        ctx.restore()

    polylignes = []
    for i, lacet in enumerate(lacets):
        xs = [x(rang_point[(i, j)]) for j in range(len(lacet))]
        ctx.move_to(x_clou, y_clou)
        arc_du_clou(xs[0], False)
        ctx.line_to(xs[0], y_axe)
        for j in range(len(lacet) - 1):
            demi_ellipse(xs[j], xs[j + 1], j % 2 == 0)
        ctx.line_to(xs[-1], y_sous_arcs)
        arc_du_clou(xs[-1], True)
        points = np.array([p for genre, p in ctx.copy_path_flat() if genre != cairo.PATH_CLOSE_PATH])
        ctx.new_path()
        polylignes.append(subdivise(points))

    trous = np.array(sorted((x(rang), y_axe) for rang in rang_trou.values()))
    return polylignes, trous, np.array((x_clou, y_clou))

def peint(polylignes, trous, clou, hauteur=400, largeur=400, largeur_brin=4, en_couleur=True):
    '''Surface Cairo du dessin donné en polylignes.'''
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, largeur, hauteur)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.set_line_width(largeur_brin)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    couleurs = [(1, 0, 0), (0, .7, 0), (0, 0, 1), (.7, .7, 0), (.7, 0, .7), (0, .7, .7)]
    if not en_couleur: couleurs = [(0, 0, 0)]

    for i, points in enumerate(polylignes):
        ctx.set_source_rgb(*couleurs[i % len(couleurs)])
        ctx.move_to(*points[0])
        for p in points[1:]: ctx.line_to(*p)
        ctx.stroke()

    ctx.set_source_rgb(0, 0, 0)
    for p in list(trous) + [clou]:
        ctx.arc(*p, largeur_brin, 0, 2 * math.pi)
        ctx.fill()

    return surface

def image_auto_de_tresse(tresse, nb_trous=None, hauteur=400, largeur=400, largeur_brin=4, en_couleur=True):
    '''Surface Cairo des images des générateurs de fn par l'automorphisme de la tresse.'''
    return peint(*geometrie_auto_de_tresse(tresse, nb_trous, hauteur, largeur),
                 hauteur, largeur, largeur_brin, en_couleur)

def dessine_auto_de_tresse(tresse, fichier, **options):
    '''Dessine en PNG les images des générateurs de fn par l'automorphisme de la tresse.'''
    image_auto_de_tresse(tresse, **options).write_to_png(fichier)

# Le mouvement continu d'un σ_i : une région autour des trous i et i+1 tourne d'un demi-tour.
# Les points tournent le long d'ellipses emboîtées : en dedans de l'ellipse intérieure tout tourne d'un bloc,
# entre les deux ellipses la rotation s'amortit en douceur, au-delà de l'extérieure rien ne bouge.
# L'ellipse extérieure s'arrête avant les autres trous mais descend loin sous l'axe, pour que les brins
# qui vont au clou aient de la place pour s'enrouler. Les ellipses étant emboîtées, c'est un homéomorphisme.

SENS_DE_SIGMA = 1 # signe de l'angle (dans le repère de Cairo, y vers le bas) pour σ_i positif

def ellipses_de_torsion(trous, i, clou):
    '''Centre et demi-axes (horizontal, vertical) des ellipses intérieure et extérieure pour σ_i.'''
    xs = trous[:, 0]
    a, b = xs[i - 1], xs[i]
    r = (b - a) / 2
    ecarts = ([a - xs[i - 2]] if i >= 2 else []) + ([xs[i + 1] - b] if i + 1 < len(xs) else [])
    marge = min(ecarts, default=2 * r)
    centre = np.array(((a + b) / 2, trous[0, 1]))
    h = clou[1] - centre[1] # le clou doit rester dehors
    interieure = np.array((r + 0.15 * marge, min(r + 0.15 * marge, 0.6 * h)))
    exterieure = np.array((r + 0.9 * marge, 0.9 * h))
    return centre, interieure, exterieure

def tourne(points, centre, interieure, exterieure, angle):
    '''Rotation d'angle « angle » le long des ellipses, entière dans l'ellipse intérieure,
    amortie jusqu'à 0 sur l'ellipse extérieure.'''
    d = points - centre
    # u : indice de l'ellipse intermédiaire (de demi-axes interpolés) qui passe par le point, par dichotomie
    def dehors(u): return ((d / (interieure + np.outer(u, exterieure - interieure))) ** 2).sum(axis=1) > 1
    bas, haut = np.zeros(len(d)), np.ones(len(d))
    for _ in range(30):
        milieu = (bas + haut) / 2
        plus_loin = dehors(milieu)
        bas, haut = np.where(plus_loin, milieu, bas), np.where(plus_loin, haut, milieu)
    u = np.where(dehors(np.zeros(len(d))), (bas + haut) / 2, 0)
    axes = np.where((u > 0)[:, None], interieure + np.outer(u, exterieure - interieure), interieure)
    v = 1 - u
    theta = angle * v * v * (3 - 2 * v) * ~dehors(np.ones(len(d)))
    c, s = np.cos(theta), np.sin(theta)
    e = d / axes # coordonnées où l'ellipse devient un cercle
    return centre + axes * np.column_stack((c * e[:, 0] - s * e[:, 1], s * e[:, 0] + c * e[:, 1]))

def tord(geometrie, sigma, t):
    '''Dessin tordu par σ_sigma au temps t ∈ [0, 1] (t = 1 : demi-tour complet).'''
    polylignes, trous, clou = geometrie
    ellipses = ellipses_de_torsion(trous, abs(sigma), clou)
    angle = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * t
    return [tourne(p, *ellipses, angle) for p in polylignes], tourne(trous, *ellipses, angle), clou

def lit_mot(points, trous):
    '''Mot de fn d'une polyligne : on note x_j (ou x_j⁻¹) à chaque traversée de gauche à droite
    (ou de droite à gauche) de la demi-droite qui monte du trou j.'''
    mot = []
    for p, q in zip(points[:-1], points[1:]):
        for j, (xt, yt) in enumerate(trous, 1):
            if (p[0] < xt) != (q[0] < xt):
                y = p[1] + (q[1] - p[1]) * (xt - p[0]) / (q[0] - p[0])
                if y < yt: mot.append(j if q[0] >= xt else -j)
    simplifie(mot)
    return mot

def verifie_torsion(tresse):
    '''Le dessin de chaque préfixe, tordu d'un demi-tour par la lettre suivante,
    doit se lire comme l'automorphisme du préfixe suivant.'''
    nb_trous = max(map(operator.abs, tresse)) + 1
    for k, sigma in enumerate(tresse):
        geometrie = geometrie_auto_de_tresse(tresse[:k], nb_trous)
        polylignes, _, _ = tord(geometrie, sigma, 1)
        # au demi-tour les trous i et i+1 ont échangé leurs places : on lit avec les positions de départ
        mots = [lit_mot(p, geometrie[1]) for p in polylignes]
        if mots != calcule_autofn_de_tresse(tresse[:k + 1], nb_trous): return False
    return True

assert all(lit_mot(p, t) == m for p, t, m in
           zip(geometrie_auto_de_tresse([4, 3, -1, -1, 2, -4, 1])[0],
               [geometrie_auto_de_tresse([4, 3, -1, -1, 2, -4, 1])[1]] * 5,
               calcule_autofn_de_tresse([4, 3, -1, -1, 2, -4, 1])))
assert verifie_torsion([1])
assert verifie_torsion([-1])
assert verifie_torsion([4, 3, -1, -1, 2, -4, 1])
assert verifie_torsion([1, -2, 1, -2, 1, -2, 3, -1, 2])

def passages(points, trous):
    '''Passages d'une polyligne sur l'axe des trous, simplifiés : deux passages consécutifs dans le même
    intervalle s'annulent (au-dessus comme au-dessous de l'axe le plan est simplement connexe).
    Renvoie la liste des (indice fractionnaire dans la polyligne, intervalle) qui restent.'''
    y_axe = trous[0, 1]
    dessus = points[:, 1] < y_axe
    pile = []
    for j in np.nonzero(dessus[:-1] != dessus[1:])[0]:
        p, q = points[j], points[j + 1]
        f = (y_axe - p[1]) / (q[1] - p[1])
        intervalle = np.searchsorted(trous[:, 0], p[0] + f * (q[0] - p[0]))
        if pile and pile[-1][1] == intervalle: pile.pop()
        else: pile.append((j + f, intervalle))
    return pile

def entre_reperes(points, reperes, longueurs_morceaux):
    '''Rééchantillonne la polyligne : entre deux repères consécutifs (indices fractionnaires),
    le nombre de points donné, régulièrement espacés.'''
    cumul = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
    abscisse = np.interp(reperes, np.arange(len(points)), cumul)
    s = np.concatenate([np.linspace(a, b, m, endpoint=False)
                        for a, b, m in zip(abscisse[:-1], abscisse[1:], longueurs_morceaux)] + [abscisse[-1:]])
    return np.column_stack((np.interp(s, cumul, points[:, 0]), np.interp(s, cumul, points[:, 1])))

def correspondance(cle, cle_suivante, sigma, pas=1.5):
    '''Met en correspondance point à point les lacets de deux images clés consécutives.
    Les passages sur l'axe du dessin tordu d'un demi-tour, une fois simplifiés, sont exactement ceux de l'image
    suivante : ce sont des repères communs. Entre deux repères on répartit les points à la même vitesse.
    Renvoie les deux listes de polylignes rééchantillonnées (même nombre de points lacet par lacet).'''
    tordus, _, _ = tord(cle, sigma, 1)
    avant, apres = [], []
    for p, p_tordu, q in zip(cle[0], tordus, cle_suivante[0]):
        rp, rq = passages(p_tordu, cle[1]), passages(q, cle_suivante[1])
        if [i for _, i in rp] != [i for _, i in rq]:
            raise ValueError(f'passages différents {rp} {rq}')
        rp = [0] + [f for f, _ in rp] + [len(p) - 1]
        rq = [0] + [f for f, _ in rq] + [len(q) - 1]
        def longueurs(points, reperes):
            cumul = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
            return np.diff(np.interp(reperes, np.arange(len(points)), cumul))
        m = [max(2, math.ceil(max(a, b) / pas)) for a, b in zip(longueurs(p, rp), longueurs(q, rq))]
        avant.append(entre_reperes(p, rp, m))
        apres.append(entre_reperes(q, rq, m))
    return avant, apres

def glisse(points, trous, trous_arrivee, clou, t):
    '''Déformation horizontale du plan qui amène au temps t ∈ [0, 1] chaque trou vers sa place d'arrivée
    (affine par morceaux entre les trous, fixe au bord du cadre, amortie jusqu'à rien au niveau du clou).
    À hauteur fixée, x ↦ x' est croissante : c'est un homéomorphisme, il ne crée aucun croisement.'''
    depart = np.concatenate(([-1e4], np.sort(trous[:, 0]), [1e4]))
    arrivee = np.concatenate(([-1e4], np.sort(trous_arrivee[:, 0]), [1e4]))
    x = points[:, 0]
    nouveau_x = np.interp(x, depart, (1 - t) * depart + t * arrivee)
    y_axe = trous[0, 1]
    u = np.clip((clou[1] - points[:, 1]) / (clou[1] - y_axe), 0, 1)
    poids = u * u * (3 - 2 * u)
    return np.column_stack((x + poids * (nouveau_x - x), points[:, 1]))

def mouvement(cle, cle_suivante, sigma, t, lacets=None, part_torsion=0.7):
    '''Dessin au temps t ∈ [0, 1] du passage d'une image clé à la suivante par σ_sigma.
    Jusqu'à part_torsion, les trous i et i+1 tournent d'un demi-tour (tord) et en même temps tous les trous
    glissent vers leur place dans l'image suivante (glisse) : deux homéomorphismes, donc pas de croisement.
    Ensuite le dessin tordu se fond dans l'image suivante (correspondance par les passages sur l'axe).
    lacets : la correspondance des points (calculée si absente).'''
    avant, apres = lacets or correspondance(cle, cle_suivante, sigma)
    def lisse(u): return u * u * (3 - 2 * u)
    torsion = lisse(min(1, t / part_torsion))
    polylignes, trous, clou = tord((avant, cle[1], cle[2]), sigma, torsion)
    polylignes = [glisse(p, cle[1], cle_suivante[1], clou, torsion) for p in polylignes]
    trous = glisse(trous, cle[1], cle_suivante[1], clou, torsion)
    w = lisse(max(0, (t - part_torsion) / (1 - part_torsion)))
    return [(1 - w) * p + w * q for p, q in zip(polylignes, apres)], trous, clou

def en_image_pil(surface):
    '''Convertit une surface Cairo ARGB32 en image PIL (Cairo range les pixels en BGRA).'''
    return Image.frombuffer('RGBA', (surface.get_width(), surface.get_height()), bytes(surface.get_data()),
                            'raw', 'BGRA', surface.get_stride()).convert('RGB')

def film_de_tresse(tresse, fichier, duree=700, **options):
    '''GIF animé : une image par préfixe de la tresse (images clés du film).
    Le nombre de trous est fixé par la tresse entière pour garder le même cadre.
    duree : temps d'affichage de chaque image en millisecondes, la dernière reste deux fois plus.'''
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    images = [en_image_pil(image_auto_de_tresse(tresse[:k], nb_trous, **options))
              for k in range(len(tresse) + 1)]
    durees = [duree] * len(tresse) + [2 * duree]
    images[0].save(fichier, save_all=True, append_images=images[1:], duration=durees, loop=0)

def film_continu_de_tresse(tresse, fichier, images_par_lettre=36, duree=40, pause=500,
                           hauteur=400, largeur=400, **options):
    '''GIF animé où chaque σ_i fait tourner les trous i et i+1 l'un autour de l'autre et entraîne les lacets,
    d'une image clé à la suivante en un seul mouvement (voir mouvement).
    duree : millisecondes par image ; pause : arrêt sur chaque image clé.'''
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    cles = [geometrie_auto_de_tresse(tresse[:k], nb_trous, hauteur, largeur) for k in range(len(tresse) + 1)]

    dessins, durees = [], []
    for k, sigma in enumerate(tresse):
        dessins.append(cles[k])
        durees.append(pause)
        lacets = correspondance(cles[k], cles[k + 1], sigma)
        for n in range(1, images_par_lettre):
            dessins.append(mouvement(cles[k], cles[k + 1], sigma, n / images_par_lettre, lacets))
            durees.append(duree)
    dessins.append(cles[-1])
    durees.append(3 * pause)

    images = [en_image_pil(peint(*d, hauteur, largeur, **options)) for d in dessins]
    images[0].save(fichier, save_all=True, append_images=images[1:], duration=durees, loop=0)

dessine_auto_de_tresse([1, 1, 2, 2], './imgs/nouv_1122.png')
dessine_auto_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/nouv_43m1m12m41.png', largeur_brin=3)
film_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/film_43m1m12m41.gif', largeur_brin=3)
film_continu_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/film_continu_43m1m12m41.gif', largeur_brin=3)
