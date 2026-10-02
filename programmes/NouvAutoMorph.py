import bisect
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

# Action algébrique de σ_i sur l'état, sans repasser par les mots de fn.
# L'état : les abscisses des trous (croissantes) et, pour chaque lacet, les abscisses de ses points sur l'axe
# dans l'ordre du lacet. L'arc du point j au point j+1 est en haut si j est pair (le lacet part du clou par en
# dessous) ; le premier et le dernier point descendent au clou. Seul l'ordre des abscisses compte.
#
# σ_i fait tourner d'un demi-tour un disque qui contient les trous i et i+1 et ce qui est entre eux (le bloc) ;
# dans une couronne mince autour du bloc, les arcs qui sortent du bloc s'enroulent d'un demi-tour.
# Combinatoirement :
# - les points du bloc (intervalle i) sont réfléchis par rapport au centre du bloc ;
# - chaque arc qui sort du bloc (une extrémité dans le bloc, l'autre dehors ou au clou) reçoit un point nouveau,
#   là où son enroulement coupe l'axe : pour σ_i positif (demi-tour horaire à l'écran), à droite du bloc
#   pour un arc du haut, à gauche pour un arc du bas ou une descente au clou ; l'inverse pour σ_i⁻¹ ;
# - d'un même côté, les points nouveaux sont dans l'ordre des extrémités intérieures de leurs arcs
#   (les arcs sortent du disque dans l'ordre de leur emboîtement, la couronne transforme cet ordre de sortie
#   en ordre sur l'axe).
# On obtient un état non réduit : deux points consécutifs d'un lacet dans le même intervalle forment un bigone,
# que l'on supprime (au-dessus comme au-dessous de l'axe le plan est simplement connexe).

def etat_de_tresse(tresse, nb_trous=None):
    '''État calculé depuis les mots de fn : rangs des trous et des points des lacets.'''
    lacets = [intervalles(mot) for mot in calcule_autofn_de_tresse(tresse, nb_trous)]
    rang_point, rang_trou, _ = abscisses(lacets, len(lacets))
    return ([rang_trou[k] for k in range(1, len(lacets) + 1)],
            [[rang_point[(i, j)] for j in range(len(lacet))] for i, lacet in enumerate(lacets)])

def intervalle(x, trous):
    '''Indice de l'intervalle de l'abscisse x : nombre de trous à sa gauche.'''
    return bisect.bisect(trous, x)

def normalise(etat):
    '''Remplace les abscisses par leurs rangs (même ordre).'''
    trous, lacets = etat
    rang = {x: r for r, x in enumerate(sorted(trous + [x for lacet in lacets for x in lacet]))}
    return [rang[x] for x in trous], [[rang[x] for x in lacet] for lacet in lacets]

def agit(etat, sigma, detail=False):
    '''État non réduit après le demi-tour du bloc des trous i et i+1 (voir plus haut).
    detail : renvoie aussi, pour chaque lacet, {indice d'un point nouveau : indice de l'arc qui l'a reçu}.'''
    trous, lacets = etat
    i = abs(sigma)
    a, b = trous[i - 1], trous[i]
    def dedans(x): return x is not None and a < x < b

    # les arcs qui sortent du bloc, rangés par côté : (extrémité intérieure, lacet, indice de l'arc)
    # l'arc d'indice j va du point j au point j+1 ; j = -1 et j = len - 1 sont les descentes au clou
    sorties = {'droite': [], 'gauche': []}
    for l, lacet in enumerate(lacets):
        points = [None] + lacet + [None] # None : le clou
        for j in range(-1, len(lacet)):
            p, q = points[j + 1], points[j + 2]
            if dedans(p) == dedans(q): continue
            en_haut = j % 2 == 0 and 0 <= j < len(lacet) - 1
            cote = 'droite' if en_haut == (sigma > 0) else 'gauche'
            sorties[cote].append((p if dedans(p) else q, l, j))

    # abscisses des points nouveaux, juste à droite du trou i+1 ou juste à gauche du trou i
    tous = trous + [x for lacet in lacets for x in lacet]
    voisin_droit = min([x for x in tous if x > b], default=b + 1)
    voisin_gauche = max([x for x in tous if x < a], default=a - 1)
    nouveau = {}
    for cote, debut, fin in (('droite', b, voisin_droit), ('gauche', voisin_gauche, a)):
        arcs = sorted(sorties[cote])
        for r, (_, l, j) in enumerate(arcs):
            nouveau[(l, j)] = debut + (fin - debut) * (r + 1) / (len(arcs) + 1)

    centre = (a + b) / 2
    resultat, origines = [], []
    for l, lacet in enumerate(lacets):
        nouveau_lacet, origine = [], {}
        for j in range(-1, len(lacet)):
            if j >= 0: nouveau_lacet.append(2 * centre - lacet[j] if dedans(lacet[j]) else lacet[j])
            if (l, j) in nouveau:
                origine[len(nouveau_lacet)] = j
                nouveau_lacet.append(nouveau[(l, j)])
        resultat.append(nouveau_lacet)
        origines.append(origine)
    return ((trous, resultat), origines) if detail else (trous, resultat)

def reduit(etat):
    '''Supprime les bigones : deux points consécutifs d'un lacet dans le même intervalle s'annulent.'''
    trous, lacets = etat
    resultat = []
    for lacet in lacets:
        pile = []
        for x in lacet:
            if pile and intervalle(pile[-1], trous) == intervalle(x, trous): pile.pop()
            else: pile.append(x)
        resultat.append(pile)
    return trous, resultat

def verifie_action(tresse):
    '''En partant de la tresse vide et en appliquant les lettres une à une, sans les mots de fn,
    on doit retrouver à chaque pas l'état calculé depuis les mots.'''
    nb_trous = max(map(operator.abs, tresse)) + 1
    etat = etat_de_tresse([], nb_trous)
    for k, sigma in enumerate(tresse):
        etat = normalise(reduit(agit(etat, sigma)))
        if etat != etat_de_tresse(tresse[:k + 1], nb_trous): return False
    return True

assert verifie_action([1])
assert verifie_action([-1])
assert verifie_action([1, 1, 2, 2])
assert verifie_action([4, 3, -1, -1, 2, -4, 1])
assert verifie_action([1, -2, 1, -2, 1, -2, 3, -1, 2])


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

def peint(polylignes, trous, clou, hauteur=400, largeur=400, largeur_brin=4, en_couleur=True, axe=None):
    '''Surface Cairo du dessin donné en polylignes ; axe : polyligne de l'axe, tracée en gris sous les lacets.'''
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, largeur, hauteur)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if axe is not None:
        ctx.set_line_width(max(1.5, 0.8 * largeur_brin))
        ctx.set_source_rgb(.45, .45, .45)
        ctx.move_to(*axe[0])
        for p in axe[1:]: ctx.line_to(*p)
        ctx.stroke()
    ctx.set_line_width(largeur_brin)

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

# Le film algébrique : chaque lettre est une suite de mouvements élémentaires sur l'état, chacun continu.
# 1. réespacement (les abscisses changent, leur ordre non : les demi-cercles ne se croisent jamais) pour vider
#    une marge autour du bloc des trous i et i+1 ;
# 2. demi-tour du bloc ; dans la marge, une couronne où seuls les arcs qui sortent du bloc s'enroulent ;
# 3. retouche du dessin tordu vers le dessin de l'état non réduit (agit), morceau par morceau ;
# 4. suppression des bigones par vagues : les deux points d'un bigone le plus intérieur glissent l'un vers l'autre,
#    puis les arcs qui les entouraient se fondent en un seul ;
# 5. réespacement vers la mise en page de l'image clé suivante.

def demi_ellipse(x1, x2, en_haut, y_axe, aplati, pas=1.5):
    '''Polyligne de la demi-ellipse de x1 à x2, au-dessus ou au-dessous de l'axe.'''
    r = abs(x2 - x1) / 2
    phi = np.linspace(0, math.pi, max(6, math.ceil(math.pi * r / pas)))
    milieu = (x1 + x2) / 2
    return np.column_stack((milieu + (x1 - milieu) * np.cos(phi),
                            y_axe + (-1 if en_haut else 1) * aplati * r * np.sin(phi)))

def a_la_meme_longueur(p, q, n=None):
    '''Les deux polylignes rééchantillonnées par abscisse curviligne avec le même nombre de points.'''
    def longueurs(points): return np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
    lp, lq = longueurs(p), longueurs(q)
    n = n or max(len(p), len(q), 2)
    def reechantillonne(points, cumul):
        s = np.linspace(0, cumul[-1], n)
        return np.column_stack((np.interp(s, cumul, points[:, 0]), np.interp(s, cumul, points[:, 1])))
    return reechantillonne(p, lp), reechantillonne(q, lq)

def melange(p, q, s):
    p, q = a_la_meme_longueur(p, q)
    return (1 - s) * p + s * q

def dessin_etat(etat, hauteur=400, largeur=400, disque=None, fusions=None, s=0, bosses=()):
    '''Dessin d'un état aux abscisses quelconques (seul leur ordre compte pour la topologie).
    disque : (centre, rayon) en unités d'abscisse, place réservée au demi-tour d'un bloc (le cadre, l'aplatissement
    et l'éventail vers le clou en tiennent compte).
    fusions : pour chaque lacet, {indice d'arc : abscisses des points fusionnés sur cet arc,
    'debut' / 'fin' : abscisses des points fusionnés avant le premier / après le dernier point}, dessinés au temps s
    du passage de la chaîne d'arcs à l'arc unique.
    bosses : déformations de l'axe (x1, x2, en_haut, amplitude) en unités d'abscisse : demi-ellipse sur [x1, x2]
    (aplatie comme les arcs), multipliée par l'amplitude. L'axe dessiné est dans geo['axe'].
    Renvoie (morceaux : pour chaque lacet la liste des polylignes de ses arcs bout à bout, descentes comprises,
    positions des trous, clou, géométrie).'''
    trous, lacets = etat
    tous = list(trous) + [x for lacet in lacets for x in lacet]
    pmin, pmax = min(tous), max(tous)
    if disque: pmin, pmax = min(pmin, disque[0] - disque[1]), max(pmax, disque[0] + disque[1])
    pas = (largeur - 40) / (pmax - pmin)
    def X(p): return 20 + (p - pmin) * pas
    y_axe = 0.4 * hauteur
    x_clou, y_clou = largeur / 2, hauteur - 10
    fusions = fusions or [{} for _ in lacets]

    # on aplatit les arcs pour qu'ils tiennent en hauteur, en laissant de la place à l'éventail vers le clou
    rayons = ([], [])
    for l, lacet in enumerate(lacets):
        for j in range(len(lacet) - 1):
            rayons[j % 2].append(abs(lacet[j + 1] - lacet[j]) / 2 * pas)
            rayons[j % 2].extend(abs(x - lacet[j]) / 2 * pas for x in fusions[l].get(j, []))
    if disque:
        for r in rayons: r.append(disque[1] * pas)
    rayon_haut, rayon_bas = max(rayons[0]), max(rayons[1], default=0)
    aplati = min(1, (y_axe - 10) / rayon_haut, (hauteur - 70 - y_axe) / max(rayon_bas, 1))
    y_sous = y_axe + rayon_bas * aplati + 8 # le chemin vers le clou passe sous tous les arcs du bas

    def demi(x1, x2, en_haut): return demi_ellipse(x1, x2, en_haut, y_axe, aplati)

    def descente(xp, y_haut=y_axe):
        '''Du clou au point (xp, y_haut) : arc de cercle (ou quart d'ellipse étiré) vers (xp, y_sous), vertical
        en ce point, puis segment vertical. Les centres sont sur l'horizontale y_sous : pas de croisement.'''
        d, h = xp - x_clou, y_clou - y_sous
        if abs(d) < 1e-6: bas = np.array([(x_clou, y_clou)])
        else:
            etire = max(1, abs(d) / h)
            d = d / etire
            centre = (d * d - h * h) / (2 * d)
            rayon = abs(d - centre)
            alpha = np.linspace(math.atan2(h, -centre), 0 if d > centre else math.pi, 40)
            bas = np.column_stack((x_clou + etire * (centre + rayon * np.cos(alpha)), y_sous + rayon * np.sin(alpha)))
        n = max(2, math.ceil((y_sous - y_haut) / 2))
        return np.concatenate((bas, np.column_stack((np.full(n, xp), np.linspace(y_sous, y_haut, n)))))

    def chaine(points, en_haut):
        return np.concatenate([demi(x1, x2, en_haut) for x1, x2 in zip(points[:-1], points[1:])])

    def fusion_arcs(x1, m, x2, en_haut, s):
        '''Passage au temps s des arcs x1 → m → x2 (du même côté, se touchant en m) à l'arc x1 → x2,
        en balayant la région entre eux, qui est vide.'''
        if min(x1, x2) < m < max(x1, x2):
            # arcs côte à côte : on mélange les profondeurs, la plus grande demi-ellipse les contient
            p = demi(x1, x2, en_haut)
            c1, r1, c2, r2 = (x1 + m) / 2, abs(m - x1) / 2, (m + x2) / 2, abs(x2 - m) / 2
            x = p[:, 0]
            petit = np.where((x - m) * (x1 - m) > 0, np.sqrt(np.clip(r1 * r1 - (x - c1) ** 2, 0, None)),
                             np.sqrt(np.clip(r2 * r2 - (x - c2) ** 2, 0, None)))
            grand = np.abs(p[:, 1] - y_axe) / aplati
            p[:, 1] = y_axe + (-1 if en_haut else 1) * aplati * ((1 - s) * petit + s * grand)
            return p
        # arcs emboîtés : le point de contact glisse vers l'extrémité la plus proche
        bout = x1 if abs(x1 - m) < abs(x2 - m) else x2
        xs = m + s * (bout - m)
        return np.concatenate((demi(x1, xs, en_haut), demi(xs, x2, en_haut)))

    def fusion_descente(m, b, s):
        '''Passage au temps s de « descente en m puis arc du bas de m à b » à « descente en b » : le pied de la
        descente glisse de m vers b, remonte jusqu'à l'arc puis le suit ; on reste sous l'arc, dans une région vide.'''
        c, r = (m + b) / 2, abs(b - m) / 2
        if r < 1e-9: return descente(b)
        xs = m + s * (b - m)
        phi_s = math.acos(np.clip((xs - c) / (m - c), -1, 1))
        phi = np.linspace(phi_s, math.pi, max(2, math.ceil(math.pi * r / 1.5)))
        arc = np.column_stack((c + (m - c) * np.cos(phi), y_axe + aplati * r * np.sin(phi)))
        return np.concatenate((descente(xs, arc[0, 1]), arc))

    morceaux = []
    for l, lacet in enumerate(lacets):
        xs = [X(p) for p in lacet]
        f = {k: [X(x) for x in v] for k, v in fusions[l].items()}
        m = []
        # une seule fusion à un endroit : balayage exact ; plusieurs à la suite : mélange simple
        if 'debut' in f and len(f['debut']) == 1: m.append(fusion_descente(f['debut'][0], xs[0], s))
        elif 'debut' in f: m.append(melange(np.concatenate((descente(f['debut'][0]), chaine(f['debut'] + xs[:1], False))),
                                            descente(xs[0]), s))
        else: m.append(descente(xs[0]))
        for j in range(len(lacet) - 1):
            if j in f and len(f[j]) == 1: m.append(fusion_arcs(xs[j], f[j][0], xs[j + 1], j % 2 == 0, s))
            elif j in f: m.append(melange(chaine([xs[j]] + f[j] + [xs[j + 1]], j % 2 == 0),
                                          demi(xs[j], xs[j + 1], j % 2 == 0), s))
            else: m.append(demi(xs[j], xs[j + 1], j % 2 == 0))
        if 'fin' in f and len(f['fin']) == 1: m.append(fusion_descente(f['fin'][0], xs[-1], s)[::-1])
        elif 'fin' in f: m.append(melange(np.concatenate((chaine(xs[-1:] + f['fin'], False), descente(f['fin'][-1])[::-1])),
                                          descente(xs[-1])[::-1], s))
        else: m.append(descente(xs[-1])[::-1])
        morceaux.append(m)

    axe = np.column_stack((np.linspace(5, largeur - 5, largeur), np.full(largeur, y_axe)))
    for x1, x2, en_haut, amplitude in bosses:
        x1, x2 = X(x1), X(x2)
        c, r = (x1 + x2) / 2, abs(x2 - x1) / 2
        hauteur_bosse = aplati * np.sqrt(np.clip(r * r - (axe[:, 0] - c) ** 2, 0, None))
        axe[:, 1] += (-1 if en_haut else 1) * amplitude * hauteur_bosse
    geo = {'X': X, 'pmin': pmin, 'pas': pas, 'y_axe': y_axe, 'aplati': aplati, 'axe': axe}
    return morceaux, np.array([(X(p), y_axe) for p in trous]), np.array((x_clou, y_clou)), geo

def polylignes(morceaux):
    return [np.concatenate(m) for m in morceaux]

def mise_en_page_avec_marge(etat, sigma):
    '''Abscisses (même ordre) laissant autour du bloc des trous i et i+1 une couronne vide, assez large pour
    les arcs qui sortent du bloc. Renvoie (état, disque du demi-tour (centre, rayon intérieur, rayon extérieur)).'''
    trous, lacets = etat
    i = abs(sigma)
    a, b = trous[i - 1], trous[i]
    centre, r = (a + b) / 2, (b - a) / 2
    _, origines = agit(etat, sigma, detail=True)
    nb_sorties = sum(len(o) for o in origines)
    r_int, r_ext = r + 0.5, r + 1.5 + nb_sorties
    gauche = max([x for x in trous + [x for l in lacets for x in l] if x < a], default=None)
    droite = min([x for x in trous + [x for l in lacets for x in l] if x > b], default=None)
    dg = max(0, gauche - (centre - r_ext - 0.5)) if gauche is not None else 0
    dd = max(0, (centre + r_ext + 0.5) - droite) if droite is not None else 0
    def decale(x): return x - dg if x < a else x + dd if x > b else x
    return ([decale(x) for x in trous], [[decale(x) for x in l] for l in lacets]), (centre, r_int, r_ext)

def interpole(etat1, etat2, t):
    '''Réespacement : abscisses interpolées entre deux états de même structure.'''
    return ([(1 - t) * x + t * y for x, y in zip(etat1[0], etat2[0])],
            [[(1 - t) * x + t * y for x, y in zip(l1, l2)] for l1, l2 in zip(etat1[1], etat2[1])])

def demi_tour(morceaux, trous, geo, disque, sigma, t):
    '''Les morceaux et les trous après rotation de t demi-tour du bloc (disque en unités d'abscisse).
    La rotation se fait avant aplatissement : un demi-cercle du bloc reste un demi-cercle.'''
    centre, r_int, r_ext = disque
    c = np.array((geo['X'](centre), geo['y_axe']))
    pas, aplati = geo['pas'], geo['aplati']
    angle = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * t
    def f(points):
        p = points.copy()
        p[:, 1] = c[1] + (p[:, 1] - c[1]) / aplati
        p = tourne(p, c, np.array((r_int * pas,) * 2), np.array((r_ext * pas,) * 2), angle)
        p[:, 1] = c[1] + (p[:, 1] - c[1]) * aplati
        return p
    return [[f(m) for m in lacet] for lacet in morceaux], f(trous)

def coupe_sur_l_axe(points, geo, disque):
    '''Point où la polyligne tordue traverse l'axe dans la couronne : (indice où couper, abscisse en unités).'''
    centre, r_int, r_ext = disque
    y = points[:, 1] - geo['y_axe']
    for k in range(1, len(points) - 2):
        if (y[k] < 0) != (y[k + 1] < 0):
            x = points[k, 0] + (points[k + 1, 0] - points[k, 0]) * y[k] / (y[k] - y[k + 1])
            u = geo['pmin'] + (x - 20) / geo['pas']
            if r_int - 0.25 <= abs(u - centre) <= r_ext + 0.25: return k + 1, u
    raise ValueError("l'arc tordu ne traverse pas l'axe dans la couronne")

def bigones_interieurs(etat):
    '''Bigones les plus intérieurs (deux points consécutifs d'un lacet dans le même intervalle, voisins sur l'axe),
    sans point commun : {lacet : liste d'indices j (le bigone est j, j+1)}.'''
    trous, lacets = etat
    axe = sorted(trous + [x for l in lacets for x in l])
    rang = {x: r for r, x in enumerate(axe)}
    resultat = {}
    for l, lacet in enumerate(lacets):
        j = 0
        while j < len(lacet) - 1:
            u, v = lacet[j], lacet[j + 1]
            if intervalle(u, trous) == intervalle(v, trous) and abs(rang[u] - rang[v]) == 1:
                resultat.setdefault(l, []).append(j)
                j += 2
            else: j += 1
    return resultat

def retire_bigones(etat, bigones):
    '''État sans les bigones (déjà rétrécis : leurs deux points ont la même abscisse) et fusions pour le dessin.'''
    trous, lacets = etat
    nouveaux, fusions = [], []
    for l, lacet in enumerate(lacets):
        retires = set(bigones.get(l, []))
        garde, fusion, en_attente = [], {}, []
        j = 0
        while j < len(lacet):
            if j in retires:
                en_attente.append(lacet[j])
                j += 2
                continue
            if en_attente: fusion['debut' if not garde else len(garde) - 1] = en_attente
            en_attente = []
            garde.append(lacet[j])
            j += 1
        if en_attente: fusion['fin'] = en_attente
        nouveaux.append(garde)
        fusions.append(fusion)
    return (trous, nouveaux), fusions

def marges_des_bigones(etat, bigones):
    '''Pour chaque bigone (l, j), la marge que le segment peut prendre de chaque côté du capuchon :
    un tiers de l'écart au voisin sur l'axe (point ou trou) le plus proche, donc la bosse ne touche aucun trou.'''
    trous, lacets = etat
    axe = sorted(trous + [x for l in lacets for x in l])
    marges = {}
    for l, js in bigones.items():
        for j in js:
            u, v = sorted((lacets[l][j], lacets[l][j + 1]))
            k, m = axe.index(u), axe.index(v)
            ecarts = [u - axe[k - 1]] if k > 0 else []
            ecarts += [axe[m + 1] - v] if m + 1 < len(axe) else []
            marges[(l, j)] = min(ecarts + [1]) / 3
    return marges

def film_de_tresse_algebrique(tresse, fichier, duree=40, pause=500, hauteur=400, largeur=400,
                              images=None, **options):
    '''GIF animé : chaque σ_i agit sur l'état par mouvements élémentaires continus (voir plus haut).
    L'axe est dessiné : pendant le demi-tour, les trous i et i+1 le quittent et s'y reposent échangés ;
    pour chaque vague de bigones, le segment se bombe par-dessus (ou par-dessous) chaque capuchon,
    lacets immobiles, puis redescend en l'écrasant ; les arcs restés de l'autre côté fusionnent.
    images : nombre d'images par phase.'''
    images = {'marge': 10, 'demi_tour': 24, 'retouche': 8, 'bosse': 6, 'presse': 8, 'fusion': 6, 'final': 12}              | (images or {})
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    cadre = {'hauteur': hauteur, 'largeur': largeur}
    def lisse(u): return u * u * (3 - 2 * u)
    dessins, durees = [], []
    def ajoute(morceaux, trous, clou, axe, d=duree):
        dessins.append((polylignes(morceaux), trous, clou, axe))
        durees.append(d)
    def ajoute_etat(etat, d=duree, **dessin):
        m, t, c, geo = dessin_etat(etat, **dessin, **cadre)
        ajoute(m, t, c, geo['axe'], d)

    etat = etat_de_tresse([], nb_trous)
    ajoute_etat(etat, pause)
    for k, sigma in enumerate(tresse):
        # 1. marge autour du bloc
        avec_marge, disque = mise_en_page_avec_marge(etat, sigma)
        for n in range(1, images['marge'] + 1):
            u = lisse(n / images['marge'])
            ajoute_etat(interpole(etat, avec_marge, u), disque=(disque[0], u * disque[2]))
        reserve = (disque[0], disque[2])
        # 2. demi-tour du bloc ; l'axe ne bouge pas
        morceaux, trous, clou, geo = dessin_etat(avec_marge, disque=reserve, **cadre)
        for n in range(1, images['demi_tour'] + 1):
            m, t = demi_tour(morceaux, trous, geo, disque, sigma, lisse(n / images['demi_tour']))
            ajoute(m, t, clou, geo['axe'])
        tordus, trous_tordus = m, t
        # 3. retouche vers l'état non réduit, dont les points nouveaux sont là où les arcs tordus coupent l'axe
        non_reduit, origines = agit(avec_marge, sigma, detail=True)
        coupes = {}
        for l, origine in enumerate(origines):
            for indice, j in origine.items():
                coupes[(l, j + 1)] = coupe_sur_l_axe(tordus[l][j + 1], geo, disque)
                non_reduit[1][l][indice] = coupes[(l, j + 1)][1]
        assert normalise(non_reduit) == normalise(agit(avec_marge, sigma)), "l'ordre des points nouveaux"
        depart = []
        for l, lacet in enumerate(tordus):
            morceaux_l = []
            for j, morceau in enumerate(lacet):
                if (l, j) in coupes:
                    k_coupe = coupes[(l, j)][0]
                    morceaux_l += [morceau[:k_coupe + 1], morceau[k_coupe:]]
                else: morceaux_l.append(morceau)
            depart.append(morceaux_l)
        arrivee, _, _, geo = dessin_etat(non_reduit, disque=reserve, **cadre)
        for n in range(1, images['retouche'] + 1):
            u = lisse(n / images['retouche'])
            ajoute([[melange(p, q, u) for p, q in zip(dl, al)] for dl, al in zip(depart, arrivee)],
                   trous_tordus, clou, geo['axe'])
        # 4. vagues de bigones : le segment monte par-dessus le capuchon, puis l'écrase en redescendant
        etat = non_reduit
        while bigones := bigones_interieurs(etat):
            marges = marges_des_bigones(etat, bigones)
            def bosses(etat_courant, amplitude, retrait):
                return [(min(etat_courant[1][l][j], etat_courant[1][l][j + 1]) - retrait * marges[(l, j)],
                         max(etat_courant[1][l][j], etat_courant[1][l][j + 1]) + retrait * marges[(l, j)],
                         j % 2 == 0, amplitude) for l, js in bigones.items() for j in js]
            for n in range(1, images['bosse'] + 1):
                ajoute_etat(etat, disque=reserve, bosses=bosses(etat, lisse(n / images['bosse']), 1))
            retreci = (etat[0], [list(l) for l in etat[1]])
            for l, js in bigones.items():
                for j in js:
                    milieu = (etat[1][l][j] + etat[1][l][j + 1]) / 2
                    retreci[1][l][j] = retreci[1][l][j + 1] = milieu
            for n in range(1, images['presse'] + 1):
                u = lisse(n / images['presse'])
                courant = interpole(etat, retreci, u)
                ajoute_etat(courant, disque=reserve, bosses=bosses(courant, 1, 1 - u))
            etat, fusions = retire_bigones(retreci, bigones)
            for n in range(1, images['fusion'] + 1):
                ajoute_etat(etat, disque=reserve, fusions=fusions, s=lisse(n / images['fusion']))
        # 5. mise en page de l'image clé suivante : les segments s'allongent ou raccourcissent
        cle = etat_de_tresse(tresse[:k + 1], nb_trous)
        assert normalise(etat) == cle, "l'état réduit doit être celui de l'image clé"
        for n in range(1, images['final'] + 1):
            u = lisse(n / images['final'])
            ajoute_etat(interpole(etat, cle, u), disque=(disque[0], (1 - u) * disque[2]))
        etat = cle
        durees[-1] = pause
    durees[-1] = 3 * pause

    images_pil = [en_image_pil(peint(m, t, c, hauteur, largeur, axe=a, **options)) for m, t, c, a in dessins]
    images_pil[0].save(fichier, save_all=True, append_images=images_pil[1:], duration=durees, loop=0)

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

dessine_auto_de_tresse([1, 1, 2, 2], './imgs/nouv_1122.png')
dessine_auto_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/nouv_43m1m12m41.png', largeur_brin=3)
film_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/film_43m1m12m41.gif', largeur_brin=3)
film_de_tresse_algebrique([4, 3, -1, -1, 2, -4, 1], './imgs/film_continu_43m1m12m41.gif', largeur_brin=3)
