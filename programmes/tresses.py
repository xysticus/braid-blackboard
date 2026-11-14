'''Base commune des dessins de tresses : action d'Artin sur le groupe libre F_n (mots), état d'un méandre
(abscisses des trous et des points des lacets sur l'axe), action algébrique de σ_i sur l'état (`agit`, `reduit`),
dessin d'un état en demi-ellipses (`dessin_etat`, `peint`), relecture des mots sur un dessin (`lit_mot`), arcs de
cercle raccordés (`deux_arcs`), conversions d'images (`en_image_pil`, `gif_en_mp4`).
Importée par NouvAutoMorph.py et Triangulation.py. Les `assert` au niveau du module servent de tests.'''

import bisect
import functools
import itertools
import operator
import math
import shutil
import subprocess
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


def peint(polylignes, trous, clou, hauteur=400, largeur=400, largeur_brin=4, en_couleur=True, axe=None):
    '''Surface Cairo du dessin donné en polylignes ; axe : polyligne de l'axe (ou liste de morceaux),
    tracée en gris sous les lacets.'''
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, largeur, hauteur)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if axe is not None:
        ctx.set_line_width(max(1.5, 0.8 * largeur_brin))
        ctx.set_source_rgb(.45, .45, .45)
        for morceau in (axe if isinstance(axe, list) else [axe]):
            ctx.move_to(*morceau[0])
            for p in morceau[1:]: ctx.line_to(*p)
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
    morceaux, trous, clou, _ = dessin_etat(etat_de_tresse(tresse, nb_trous), hauteur, largeur)
    return peint(polylignes(morceaux), trous, clou, hauteur, largeur, largeur_brin, en_couleur)

def dessine_auto_de_tresse(tresse, fichier, **options):
    '''Dessine en PNG les images des générateurs de fn par l'automorphisme de la tresse.'''
    image_auto_de_tresse(tresse, **options).write_to_png(fichier)

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

def descente_au_clou(xp, y_haut, y_sous, x_clou, y_clou):
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

    def descente(xp, y_haut=y_axe): return descente_au_clou(xp, y_haut, y_sous, x_clou, y_clou)

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
    geo = {'X': X, 'pmin': pmin, 'pas': pas, 'y_axe': y_axe, 'aplati': aplati, 'axe': axe,
           'y_sous': y_sous, 'descente': descente}
    return morceaux, np.array([(X(p), y_axe) for p in trous]), np.array((x_clou, y_clou)), geo

def polylignes(morceaux):
    return [np.concatenate(m) for m in morceaux]

def lit_mot(points, trous):
    '''Mot de fn d'une polyligne : on note x_j (ou x_j⁻¹) à chaque traversée de gauche à droite
    (ou de droite à gauche) de la demi-droite qui monte du trou j.'''
    mot = []
    for p, q in zip(points[:-1], points[1:]):
        lettres = [] # (place sur le segment, lettre) : un segment peut traverser plusieurs demi-droites
        for j, (xt, yt) in enumerate(trous, 1):
            if (p[0] < xt) != (q[0] < xt):
                place = (xt - p[0]) / (q[0] - p[0])
                if p[1] + (q[1] - p[1]) * place < yt: lettres.append((place, j if q[0] >= xt else -j))
        mot.extend(lettre for _, lettre in sorted(lettres))
    simplifie(mot)
    return mot

def verifie_dessin(tresse):
    '''Le dessin de la tresse, relu par les demi-droites qui montent des trous, redonne les mots de fn.'''
    morceaux, trous, _, _ = dessin_etat(etat_de_tresse(tresse))
    return [lit_mot(p, trous) for p in polylignes(morceaux)] == calcule_autofn_de_tresse(tresse)

assert verifie_dessin([4, 3, -1, -1, 2, -4, 1])
assert verifie_dessin([1, -2, 1, -2, 1, -2, 3, -1, 2])


def arc_de_cercle(p, t, m, pas=1.5):
    """Polyligne de l'arc de cercle qui part de p dans la direction t (unitaire) et arrive en m."""
    w = m - p
    corde = math.hypot(*w)
    phi = 2 * math.atan2(t[0] * w[1] - t[1] * w[0], t[0] * w[0] + t[1] * w[1]) # angle dont l'arc tourne
    if corde < 1e-9 or abs(math.sin(phi / 2)) < 1e-9:
        return np.array((p, m))
    rayon = corde / (2 * math.sin(phi / 2))
    centre = p + rayon * np.array((-t[1], t[0]))
    a = np.linspace(0, phi, max(3, math.ceil(abs(rayon * phi) / pas)))
    d = p - centre
    return centre + np.column_stack((np.cos(a) * d[0] - np.sin(a) * d[1], np.sin(a) * d[0] + np.cos(a) * d[1]))

def raccord_egal(p0, t0, p1, t1):
    """Raccord de la paire d'arcs de p0 (direction t0) à p1 (direction t1) à égale distance des deux tangentes
    extrêmes ; None si les données sont alignées."""
    v, t = p1 - p0, t0 + t1
    a = 2 * (1 - t0 @ t1)
    if abs(a) > 1e-9: d = (-(v @ t) + math.sqrt((v @ t) ** 2 + a * (v @ v))) / a
    elif abs(v @ t1) > 1e-9: d = (v @ v) / (4 * (v @ t1))
    else: return None
    return (p0 + d * t0 + p1 - d * t1) / 2

def lieu_des_raccords(p0, t0, p1, t1):
    """Les raccords possibles d'une paire d'arcs de p0 (direction t0) à p1 (direction t1) sont sur un cercle qui
    passe par p0 et p1. Renvoie (place : point → fraction du chemin de p0 à p1 le long de ce cercle,
    point : fraction → point)."""
    j = raccord_egal(p0, t0, p1, t1)
    v = p1 - p0
    aire = 0 if j is None else (j[0] - p0[0]) * v[1] - (j[1] - p0[1]) * v[0]
    if abs(aire) < 1e-7 * (v @ v): # données alignées : le lieu est la droite
        return (lambda q: ((q - p0) @ v) / (v @ v)), (lambda f: p0 + f * v)
    # centre du cercle par p0, j, p1
    a, b = j - p0, v
    centre = p0 + np.array((b[1] * (a @ a) - a[1] * (b @ b), a[0] * (b @ b) - b[0] * (a @ a))) / (2 * (a[0] * b[1] - a[1] * b[0]))
    def angle(q): return math.atan2(q[1] - centre[1], q[0] - centre[0])
    a0 = angle(p0)
    tour = 2 * math.pi
    total = (angle(p1) - a0) % tour
    if (angle(j) - a0) % tour > total: total -= tour # on va de p0 à p1 en passant par j
    def place(q):
        d = (angle(q) - a0) % tour
        return (d if total > 0 else d - tour) / total
    rayon = math.hypot(*(p0 - centre))
    return place, (lambda f: centre + rayon * np.array((math.cos(a0 + f * total), math.sin(a0 + f * total))))

def deux_arcs(p0, t0, p1, t1, raccord=None):
    """Polyligne de p0 (direction t0) à p1 (direction t1) : deux arcs de cercle raccordés avec la même tangente.
    raccord : fraction du lieu_des_raccords où ils se rejoignent ; par défaut à égale distance des deux tangentes
    extrêmes. C'est un seul arc de cercle quand il en existe un, par exemple un demi-cercle entre deux points
    d'une même droite traversée à angle droit."""
    j = raccord_egal(p0, t0, p1, t1) if raccord is None else lieu_des_raccords(p0, t0, p1, t1)[1](raccord)
    if j is None: return np.array((p0, p1))
    return np.concatenate((arc_de_cercle(p0, t0, j), arc_de_cercle(p1, -t1, j)[::-1]))


def en_image_pil(surface):
    '''Convertit une surface Cairo ARGB32 en image PIL (Cairo range les pixels en BGRA).'''
    return Image.frombuffer('RGBA', (surface.get_width(), surface.get_height()), bytes(surface.get_data()),
                            'raw', 'BGRA', surface.get_stride()).convert('RGB')

def gif_en_mp4(fichier_gif):
    '''Convertit un GIF en MP4 (VP9) à côté de lui avec ffmpeg, à 25 images/s (les durées des images
    du GIF sont gardées, pause finale comprise). VP9 plutôt que H.264 : codec libre, lu par le VLC
    de Fedora qui n'a pas H.264. Réglage rapide de l'encodeur (sinon VP9 est très lent).
    Les dimensions sont arrondies au pair (exigé par yuv420p). Ne fait rien si ffmpeg est absent.'''
    if shutil.which('ffmpeg') is None:
        print("ffmpeg introuvable :", fichier_gif, "n'est pas converti en MP4")
        return
    fichier_mp4 = fichier_gif.removesuffix('.gif') + '.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', fichier_gif,
                    '-vf', 'fps=25,scale=trunc(iw/2)*2:trunc(ih/2)*2', '-pix_fmt', 'yuv420p',
                    '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0',
                    '-deadline', 'realtime', '-cpu-used', '8', '-row-mt', '1',
                    '-movflags', '+faststart', fichier_mp4], check=True)
