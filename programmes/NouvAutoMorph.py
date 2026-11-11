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

# tests sur la tresse compliquée
t = calcule_autofn_de_tresse([1,1,2,2])
print(t)

d = calcule_arcs(t[0]) 
print(d)

print(calcule_arcs(t[1]))

print(calcule_arcs(t[2]))

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

SENS_DE_SIGMA = 1 # signe de l'angle (dans le repère de Cairo, y vers le bas) pour σ_i positif

def tourne(points, centre, r_int, r_ext, angle):
    '''Rotation d'angle « angle » autour du centre, entière jusqu'au rayon r_int, amortie en douceur jusqu'à 0
    au rayon r_ext. L'angle ne dépend que de la distance au centre : c'est un homéomorphisme.'''
    d = points - centre
    u = np.clip((r_ext - np.hypot(d[:, 0], d[:, 1])) / (r_ext - r_int), 0, 1)
    theta = angle * u * u * (3 - 2 * u)
    c, s = np.cos(theta), np.sin(theta)
    return centre + np.column_stack((c * d[:, 0] - s * d[:, 1], s * d[:, 0] + c * d[:, 1]))

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
        p = tourne(p, c, r_int * pas, r_ext * pas, angle)
        p[:, 1] = c[1] + (p[:, 1] - c[1]) * aplati
        return p
    return [[f(m) for m in lacet] for lacet in morceaux], f(trous)

def axe_pendant_demi_tour(geo, disque, r, trous_tournes, i, t, largeur):
    '''Morceaux de l'axe au temps t du demi-tour (r : demi-écart des trous i et i+1). Hors de la couronne l'axe ne bouge pas. Le segment i tourne,
    rigide entre les trous i et i+1. Les morceaux des segments i-1 et i+1 accrochés à ces trous (jusqu'au bord de la
    couronne) sont voués à disparaître : le centre de rotation les emporte, ils tournent avec lui et glissent vers lui
    en rétrécissant (distances au centre multipliées par 1 - t) ; les nouveaux morceaux poussent depuis le bord de la
    couronne et rejoignent les trous quand ils se reposent sur l'axe.'''
    centre, _, r_ext = disque
    X, y = geo['X'], geo['y_axe']
    c = np.array((X(centre), y))
    a, b = trous_tournes[i - 1], trous_tournes[i]
    def vieux(trou): return np.array((c + (trou - c) * (1 - t), c + (trou - c) * r_ext / r * (1 - t)))
    pousse = (r_ext - r) * geo['pas'] * t
    return [np.array(((5, y), (X(centre - r_ext), y))), np.array(((X(centre + r_ext), y), (largeur - 5, y))),
            np.array((a, b)), vieux(a), vieux(b),
            np.array(((X(centre - r_ext), y), (X(centre - r_ext) + pousse, y))),
            np.array(((X(centre + r_ext), y), (X(centre + r_ext) - pousse, y)))]

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
    L'axe est dessiné : pendant le demi-tour, le segment i tourne avec les trous i et i+1, les morceaux des
    segments voisins accrochés à ces trous tournent et rétrécissent, les nouveaux poussent (axe_pendant_demi_tour) ;
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
        # 2. demi-tour du bloc ; le segment i tourne avec les trous, les morceaux voués à disparaître aussi
        morceaux, trous, clou, geo = dessin_etat(avec_marge, disque=reserve, **cadre)
        for n in range(1, images['demi_tour'] + 1):
            u = lisse(n / images['demi_tour'])
            m, t = demi_tour(morceaux, trous, geo, disque, sigma, u)
            ajoute(m, t, clou, axe_pendant_demi_tour(geo, disque, disque[1] - 0.5, t, abs(sigma), u, largeur))
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

# Le film simultané : le demi-tour dure toute la lettre et rien ne reste à régler une fois les trous en place.
# 1. Pas de mou. Un bigone de l'état non réduit est toujours fait d'un point nouveau et du bout extérieur Q de son
#    arc, quand Q est dans l'intervalle voisin du bloc, du côté où l'arc s'enroule. Ces points Q sont les plus proches
#    du bloc. Avant de tordre, on les range : les « doigts » (les deux arcs de Q vont dans le bloc : Q contourne un
#    trou) entrent dans le disque rigide et tournent avec lui ; les « passants » (un seul arc va dans le bloc) entrent
#    dans la couronne, où ils ne tournent qu'en partie et quittent l'axe : le lacet passe sans faire de capuchon.
#    Tous les brins traversent alors la couronne en s'éloignant du centre : la torsion les enroule sans créneaux.
# 2. Deux dessins du même instant u : D_u = H_u(image clé k, rangée pour σ) et A_u = H_(u-1)(image clé k+1, rangée
#    pour σ⁻¹), où H_t est la rotation de t demi-tour, amortie dans la couronne. Les passants de l'un sont les
#    points nouveaux de l'autre. D_u est exact au départ, A_u à l'arrivée : l'image est leur mélange, de poids u,
#    entre points communs. Le rangement (et le retour aux abscisses de l'image clé) se fait pendant la rotation.
# Le mélange est linéaire : pas de preuve d'absence de croisement, mais les deux dessins sont proches.

def mise_en_page_du_demi_tour(etat, sigma):
    """Abscisses (même ordre) rangées pour le demi-tour du bloc des trous i et i+1 : doigts à côté des trous,
    passants dans la couronne, le reste au-delà. Renvoie (état, disque (centre, rayon intérieur, rayon extérieur),
    ensemble des passants (lacet, indice du point), ensemble des points qui tournent avec le bloc)."""
    trous, lacets = etat
    i = abs(sigma)
    a, b = trous[i - 1], trous[i]
    centre, r = (a + b) / 2, (b - a) / 2
    limites = {'gauche': (trous[i - 2] if i >= 2 else -math.inf, a), 'droite': (b, trous[i + 1] if i + 1 < len(trous) else math.inf)}
    def dans_bloc(x): return x is not None and a < x < b
    doigts, passants = {'gauche': [], 'droite': []}, {'gauche': [], 'droite': []}
    for l, lacet in enumerate(lacets):
        points = [None] + lacet + [None] # None : le clou
        for j, x in enumerate(lacet):
            # l'arc d'indice pair est en haut : pour j pair c'est celui qui suit le point, sinon celui qui précède
            bout_haut, bout_bas = (points[j + 2], points[j]) if j % 2 == 0 else (points[j], points[j + 2])
            for cote, (x1, x2) in limites.items():
                if not x1 < x < x2: continue
                # l'arc que l'enroulement ramène de ce côté : pour σ positif, arc du haut à droite, du bas à gauche
                ramene, autre = (bout_haut, bout_bas) if (cote == 'droite') == (sigma > 0) else (bout_bas, bout_haut)
                if dans_bloc(ramene): (doigts if dans_bloc(autre) else passants)[cote].append((abs(x - centre), l, j))
    for cote, (x1, x2) in limites.items():
        proches = sorted((abs(x - centre), l, j) for l, lacet in enumerate(lacets) for j, x in enumerate(lacet) if x1 < x < x2)
        assert proches[:len(doigts[cote]) + len(passants[cote])] == sorted(doigts[cote]) + sorted(passants[cote]), \
               "les doigts puis les passants sont les points les plus proches du bloc"
    rigides = {(l, j) for cote in doigts for _, l, j in doigts[cote]} \
              | {(l, j) for l, lacet in enumerate(lacets) for j, x in enumerate(lacet) if dans_bloc(x)}
    nb_sorties = sum(((l, j) in rigides) != ((l, j + 1) in rigides)
                     for l, lacet in enumerate(lacets) for j in range(-1, len(lacet)))
    r_int = r + max(len(doigts['gauche']), len(doigts['droite'])) + 0.5
    r_ext = r_int + 1 + nb_sorties
    place = {}
    for cote, signe in (('gauche', -1), ('droite', 1)):
        for rang, (_, l, j) in enumerate(sorted(doigts[cote]), 1): place[(l, j)] = centre + signe * (r + rang)
        for rang, (_, l, j) in enumerate(sorted(passants[cote]), 1):
            place[(l, j)] = centre + signe * (r_int + (r_ext - r_int) * rang / (len(passants[cote]) + 1))
    dehors = trous[:i - 1] + trous[i + 1:] + [x for l, lacet in enumerate(lacets) for j, x in enumerate(lacet)
                                             if (l, j) not in place and not dans_bloc(x)]
    # le reste est posé juste au-delà de la couronne : les points communs à cette image clé et à la suivante ont
    # ainsi les mêmes abscisses (au demi-tour du bloc près) dans les deux rangements
    dg = max([x - (centre - r_ext - 0.5) for x in dehors if x < a], default=0)
    dd = max([(centre + r_ext + 0.5) - x for x in dehors if x > b], default=0)
    def decale(x): return x - dg if x < a else x + dd if x > b else x
    return (([decale(x) for x in trous], [[place.get((l, j), decale(x)) for j, x in enumerate(lacet)] for l, lacet in enumerate(lacets)]),
            (centre, r_int, r_ext), {(l, j) for cote in passants for _, l, j in passants[cote]}, rigides)

def dessin_pendant_demi_tour(etat, sigma, rangement, t, **cadre):
    """Dessin de l'état (une image clé) rangé dans la proportion « rangement » pour le demi-tour, puis tourné de
    t demi-tour. Tant que le rangement n'est pas fini, la couronne s'arrête avant les autres trous.
    Renvoie un dictionnaire : morceaux, trous, clou, geo, disque, passants, etat (abscisses dessinées),
    tangente (fonction : sens de parcours d'un lacet à l'un de ses points)."""
    page, (centre, r_int, r_ext), passants, _ = mise_en_page_du_demi_tour(etat, sigma)
    e = interpole(etat, page, rangement)
    i = abs(sigma)
    a, b = e[0][i - 1], e[0][i]
    ecart = min([a - x for x in e[0][:i - 1]] + [x - b for x in e[0][i + 1:]], default=math.inf)
    ext = min(r_ext, (b - a) / 2 + ecart - 0.5)
    disque = (centre, min(r_int, ext - 0.25), ext)
    morceaux, trous, clou, geo = dessin_etat(e, disque=(centre, rangement * r_ext), **cadre)
    morceaux, trous = demi_tour(morceaux, trous, geo, disque, sigma, t)
    angle = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * t
    def tangente(l, j):
        """Sens de parcours du lacet l à son point j, avant aplatissement : la verticale (vers le haut si l'arc
        qui suit est en haut), tournée comme le point."""
        u = min(1, max(0, (disque[2] - abs(e[1][l][j] - centre)) / (disque[2] - disque[1])))
        theta = angle * u * u * (3 - 2 * u)
        signe = -1 if j % 2 == 0 else 1
        return np.array((-math.sin(theta) * signe, math.cos(theta) * signe))
    return {'morceaux': morceaux, 'trous': trous, 'clou': clou, 'geo': geo, 'disque': disque, 'passants': passants,
            'etat': e, 'tangente': tangente}

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

def point_a_la_fraction(points, f):
    """Point de la polyligne à la fraction f de sa longueur, et direction de la polyligne en ce point."""
    cumul = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
    k = min(max(int(np.searchsorted(cumul, f * cumul[-1])), 1), len(points) - 1)
    q = (f * cumul[-1] - cumul[k - 1]) / max(cumul[k] - cumul[k - 1], 1e-12)
    d = points[min(k + 1, len(points) - 1)] - points[max(k - 2, 0)]
    return points[k - 1] + q * (points[k] - points[k - 1]), d / max(math.hypot(*d), 1e-12)

def segments_en_noeuds(dessin, l):
    """Le lacet l d'un dessin_pendant_demi_tour, découpé d'un point commun au suivant. Tout est donné avant
    aplatissement. Pour chaque segment : 'points' (polyligne ; pour les deux descentes, seulement la partie au-dessus
    du pied), 'bas' (du clou au pied, pour les descentes), 'noeuds' (passants du segment : fraction de la longueur,
    position, direction), 'debut' et 'fin' (position, direction), 'bords' (fractions de la longueur où le segment
    traverse le bord extérieur de la couronne)."""
    geo, morceaux, tangente = dessin['geo'], dessin['morceaux'][l], dessin['tangente']
    passants = {j for ll, j in dessin['passants'] if ll == l}
    n = len(morceaux) - 1
    centre = np.array((geo['X'](dessin['disque'][0]), geo['y_axe']))
    rayon = dessin['disque'][2] * geo['pas']
    def releve(points):
        q = points.copy()
        q[:, 1] = geo['y_axe'] + (q[:, 1] - geo['y_axe']) / geo['aplati']
        return q
    def segment(pieces, debut, fin, bas=None):
        """pieces : (polyligne, point où elle finit, sens +1 ou -1 du parcours) ; debut, fin : None pour un pied."""
        points = np.concatenate([q for q, _, _ in pieces])
        longueurs = np.cumsum([np.hypot(*np.diff(q, axis=0).T).sum() for q, _, _ in pieces])
        noeuds = [(longueurs[k] / longueurs[-1], q[-1], sens * tangente(l, j))
                  for k, (q, j, sens) in enumerate(pieces[:-1])]
        bouts = [(points[0 if k == 0 else -1], bout[1] * tangente(l, bout[0])) if bout is not None
                 else point_a_la_fraction(points, k) for k, bout in enumerate((debut, fin))]
        # là où le segment traverse le bord de la couronne : au-delà, il ne tourne pas
        cumul = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
        ecart = np.hypot(*(points - centre).T) - rayon
        bords = [(cumul[k] + (cumul[k + 1] - cumul[k]) * ecart[k] / (ecart[k] - ecart[k + 1])) / cumul[-1]
                 for k in np.nonzero(ecart[:-1] * ecart[1:] < 0)[0]]
        return {'points': points, 'bas': bas, 'noeuds': noeuds, 'debut': bouts[0], 'fin': bouts[1], 'bords': bords}
    def pied(j):
        return len(geo['descente'](geo['X'](dessin['etat'][1][l][j]), geo['y_sous'])) - 2
    communs = [j for j in range(n) if j not in passants]
    segments = []
    # du clou au premier point commun
    k = pied(0)
    pieces = [(releve(morceaux[0][k:]), 0, 1)] + [(releve(morceaux[j]), j, 1) for j in range(1, communs[0] + 1)]
    segments.append(segment(pieces, None, (communs[0], 1), bas=morceaux[0][:k + 1]))
    for j1, j2 in zip(communs[:-1], communs[1:]):
        segments.append(segment([(releve(morceaux[j]), j, 1) for j in range(j1 + 1, j2 + 1)], (j1, 1), (j2, 1)))
    # du dernier point commun au clou : on le parcourt à l'envers, comme la première descente
    k = pied(n - 1)
    pieces = [(releve(morceaux[n][::-1][k:]), n - 1, -1)] \
             + [(releve(morceaux[j][::-1]), j - 1, -1) for j in range(n - 1, communs[-1], -1)]
    segments.append(segment(pieces, None, (communs[-1], -1), bas=morceaux[n][::-1][:k + 1]) | {'a_l_envers': True})
    return segments

def lacet_en_arcs(depart, arrivee, l, s):
    """Le lacet l, mélange de poids s des dessins depart et arrivee, tracé en arcs de cercle : les noeuds (points
    communs, passants de l'un ou de l'autre, traversées du bord de la couronne, pieds des descentes) sont mélangés,
    position et direction, puis reliés par deux_arcs. Les descentes sans passant (points qui ne tournent pas) restent des mélanges de polylignes."""
    def mele(a, b):
        (pa, ta), (pb, tb) = a, b
        ecart = math.atan2(ta[0] * tb[1] - ta[1] * tb[0], ta @ tb)
        c, d = math.cos(s * ecart), math.sin(s * ecart)
        return (1 - s) * pa + s * pb, np.array((c * ta[0] - d * ta[1], d * ta[0] + c * ta[1]))
    aplati = (1 - s) * depart['geo']['aplati'] + s * arrivee['geo']['aplati']
    y_axe = depart['geo']['y_axe']
    morceaux = []
    for sd, sa in zip(segments_en_noeuds(depart, l), segments_en_noeuds(arrivee, l), strict=True):
        if sd['bas'] is not None and not sd['noeuds'] and not sa['noeuds']:
            def entier(seg, geo):
                haut = seg['points'].copy()
                haut[:, 1] = y_axe + (haut[:, 1] - y_axe) * geo['aplati']
                return np.concatenate((seg['bas'], haut[1:]))
            ligne = melange(entier(sd, depart['geo']), entier(sa, arrivee['geo']), s)
        else:
            noeuds = [mele(sd['debut'], sa['debut'])]
            # les fractions de longueur des deux dessins se correspondent, bord de la couronne sur bord de la couronne
            fd, fa = ([0] + seg['bords'] + [1] if len(sd['bords']) == len(sa['bords']) else [0, 1] for seg in (sd, sa))
            vrais = [(f, mele((q, t), point_a_la_fraction(sa['points'], np.interp(f, fd, fa)))) for f, q, t in sd['noeuds']] \
                    + [(np.interp(f, fa, fd), mele(point_a_la_fraction(sd['points'], np.interp(f, fa, fd)), (q, t)))
                       for f, q, t in sa['noeuds']] \
                    + [(f, mele(point_a_la_fraction(sd['points'], f), point_a_la_fraction(sa['points'], g)))
                       for f, g in zip(fd[1:-1], fa[1:-1])]
            noeuds += [noeud for _, noeud in sorted(vrais, key=lambda x: x[0])] + [mele(sd['fin'], sa['fin'])]
            ligne = np.concatenate([deux_arcs(p0, t0, p1, t1) for (p0, t0), (p1, t1) in zip(noeuds[:-1], noeuds[1:])])
            ligne[:, 1] = y_axe + (ligne[:, 1] - y_axe) * aplati
            if sd['bas'] is not None: ligne = np.concatenate((melange(sd['bas'], sa['bas'], s), ligne))
        morceaux.append(ligne[::-1] if sd.get('a_l_envers') else ligne)
    return np.concatenate(morceaux)

def entre_points_communs(morceaux, passants):
    """Les morceaux d'un lacet recollés en polylignes qui vont d'un point commun au suivant
    (passants : indices des points du lacet qui ne sont pas communs aux deux images clés)."""
    segments, courant = [], []
    for j, morceau in enumerate(morceaux):
        courant.append(morceau)
        if j < len(morceaux) - 1 and j not in passants:
            segments.append(np.concatenate(courant))
            courant = []
    return segments + [np.concatenate(courant)]

def film_de_tresse_simultane(tresse, fichier, duree=40, pause=500, hauteur=400, largeur=400,
                             images=48, part_du_rangement=0.3, verifie=False, en_arcs=False, **options):
    """GIF animé : pour chaque σ_i, un seul mouvement (voir plus haut). Pendant que les trous i et i+1 tournent,
    les lacets sont entraînés sans prendre de mou et les abscisses passent de celles de l'image clé à celles
    de la suivante. images : nombre d'images par lettre ; part_du_rangement : part du mouvement pendant laquelle
    les abscisses se rangent (au début) ou rejoignent l'image clé (à la fin).
    verifie : relit le mot de chaque lacet sur chaque image (lent).
    en_arcs (essai) : au lieu de mélanger les courbes, mélange leurs noeuds et les relie par des arcs de cercle
    (lacet_en_arcs) : plus d'ondulations, mais des croisements sur les lettres chargées."""
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    cadre = {'hauteur': hauteur, 'largeur': largeur}
    def lisse(u): return u * u * (3 - 2 * u)
    dessins, durees = [], []

    cle = etat_de_tresse([], nb_trous)
    m, t, c, geo = dessin_etat(cle, **cadre)
    dessins.append((polylignes(m), t, c, geo['axe']))
    durees.append(pause)
    for k, sigma in enumerate(tresse):
        i = abs(sigma)
        suivante = etat_de_tresse(tresse[:k + 1], nb_trous)
        mots = [calcule_autofn_de_tresse(tresse[:k + j], nb_trous) for j in (0, 1)]
        for n in range(1, images + 1):
            u = n / images
            s = lisse(u)
            depart = dessin_pendant_demi_tour(cle, sigma, lisse(min(1, u / part_du_rangement)), s, **cadre)
            arrivee = dessin_pendant_demi_tour(suivante, -sigma, lisse(min(1, (1 - u) / part_du_rangement)), 1 - s, **cadre)
            td, ta, clou, gd, ga, dd, da = (depart['trous'], arrivee['trous'], depart['clou'], depart['geo'],
                                            arrivee['geo'], depart['disque'], arrivee['disque'])
            ta[[i - 1, i]] = ta[[i, i - 1]] # les deux trous ont échangé leurs places dans l'image clé suivante
            if en_arcs: lignes = [lacet_en_arcs(depart, arrivee, l, s) for l in range(len(cle[1]))]
            else:
                lignes = []
                for l in range(len(cle[1])):
                    bouts = [entre_points_communs(d['morceaux'][l], {j for ll, j in d['passants'] if ll == l})
                             for d in (depart, arrivee)]
                    assert len(bouts[0]) == len(bouts[1]), "les deux images clés ont les mêmes points communs"
                    lignes.append(np.concatenate([melange(p, q, s) for p, q in zip(*bouts)]))
            trous = (1 - s) * td + s * ta
            if verifie:
                en_ordre = sorted(trous.tolist())
                # quand les deux trous sont à la verticale l'un de l'autre, les mots ne sont pas définis
                assert abs(trous[i - 1][0] - trous[i][0]) < 1e-6 or [lit_mot(p, en_ordre) for p in lignes] in mots, \
                       f"lettre {k}, image {n} : mots des lacets"
            # l'axe (voir axe_pendant_demi_tour), avec le centre et le rayon de la couronne mélangés eux aussi
            y = gd['y_axe']
            c = np.array(((1 - s) * gd['X'](dd[0]) + s * ga['X'](da[0]), y))
            rayon = (1 - s) * dd[2] * gd['pas'] + s * da[2] * ga['pas']
            a, b = trous[i - 1], trous[i]
            r = np.hypot(*(b - a)) / 2
            def vieux(trou): return np.array((c + (trou - c) * (1 - s), c + (trou - c) * rayon / r * (1 - s)))
            pousse = (rayon - r) * s
            axe = [np.array(((5, y), (c[0] - rayon, y))), np.array(((c[0] + rayon, y), (largeur - 5, y))),
                   np.array((a, b)), vieux(a), vieux(b),
                   np.array(((c[0] - rayon, y), (c[0] - rayon + pousse, y))),
                   np.array(((c[0] + rayon, y), (c[0] + rayon - pousse, y)))]
            dessins.append((lignes, trous, clou, axe))
            durees.append(duree)
        cle = suivante
        durees[-1] = pause
    durees[-1] = 3 * pause

    images_pil = [en_image_pil(peint(m, t, c, hauteur, largeur, axe=a, **options)) for m, t, c, a in dessins]
    images_pil[0].save(fichier, save_all=True, append_images=images_pil[1:], duration=durees, loop=0)

# Le film en arcs de cercle : plus de courbes libres. Les segments noirs sont l'axe horizontal et le segment qui
# tourne (les trous i et i+1, les points du bloc et les doigts). Chaque point d'un lacet est sur un segment noir et
# le traverse à angle droit. Entre deux points du même segment, un demi-cercle (qui tourne avec le segment, ou qui ne
# bouge pas). Un brin qui sort du bloc, d'un point du segment tournant à un point de l'axe, est une paire d'arcs
# de cercle raccordés avec la même tangente : au départ le raccord est le passant de l'image clé (qui quitte
# l'axe), ou à l'arrivée le point nouveau de l'image clé suivante (qui s'y pose) ; entre-temps il garde sa place
# sur le lieu des raccords. Les abscisses passent de celles de l'image clé à celles de la suivante pendant
# la rotation. Aucune preuve d'absence de croisement : verifie relit les mots, à contrôler image par image.

def film_de_tresse_en_arcs(tresse, fichier, duree=40, pause=500, hauteur=400, largeur=400,
                           images=48, verifie=False, **options):
    """GIF animé en arcs de cercle (voir plus haut). images : nombre d'images par lettre.
    verifie : relit le mot de chaque lacet sur chaque image (lent)."""
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    cadre = {'hauteur': hauteur, 'largeur': largeur}
    def lisse(u): return u * u * (3 - 2 * u)
    dessins, durees = [], []
    cle = etat_de_tresse([], nb_trous)
    m, t, c, geo = dessin_etat(cle, **cadre)
    dessins.append((polylignes(m), t, c, geo['axe']))
    durees.append(pause)
    for k, sigma in enumerate(tresse):
        i = abs(sigma)
        suivante = etat_de_tresse(tresse[:k + 1], nb_trous)
        etats = (cle, suivante)
        geos = [dessin_etat(e, **cadre)[3] for e in etats]
        clou = np.array((largeur / 2, hauteur - 10))
        y_axe = geos[0]['y_axe']
        roles = [mise_en_page_du_demi_tour(e, sg) for e, sg in zip(etats, (sigma, -sigma))]
        centres = [(e[0][i - 1] + e[0][i]) / 2 for e in etats]
        nb_doigts = roles[0][1][1] - (cle[0][i] - cle[0][i - 1]) / 2 - 0.5
        communs = [[[j for j in range(len(lacet)) if (l, j) not in role[2]] for l, lacet in enumerate(e[1])]
                   for e, role in zip(etats, roles)]
        assert [len(x) for x in communs[0]] == [len(x) for x in communs[1]], "mêmes points communs"
        sens = SENS_DE_SIGMA * (1 if sigma > 0 else -1)

        def cadre_a(s):
            """Au temps s : (pixel du centre, angle, aplatissement, niveau sous les arcs du bas)."""
            def mele(nom): return (1 - s) * geos[0][nom] + s * geos[1][nom]
            return ((1 - s) * geos[0]['X'](centres[0]) + s * geos[1]['X'](centres[1]), sens * math.pi * s,
                    mele('aplati'), mele('y_sous'))
        def sur_le_segment(rayon, s):
            """Point du segment tournant à la distance signée rayon (en pixels) du centre, avant aplatissement."""
            x_centre, angle, _, _ = cadre_a(s)
            return np.array((x_centre + rayon * math.cos(angle), y_axe + rayon * math.sin(angle)))
        def abscisse(l, quel, j, s=None):
            """Pixel sur l'axe du point j du lacet l dans l'image clé quel (0 ou 1) ; avec s, mélange des deux images
            clés pour le point commun de rang j."""
            if s is None: return geos[quel]['X'](etats[quel][1][l][j])
            return (1 - s) * abscisse(l, 0, communs[0][l][j]) + s * abscisse(l, 1, communs[1][l][j])
        def noeud(l, rang, s):
            """Position (avant aplatissement) et sens de parcours du point commun de rang donné du lacet l."""
            j0, j1 = communs[0][l][rang], communs[1][l][rang]
            vers = np.array((0, -1 if j0 % 2 == 0 else 1))
            if (l, j0) not in roles[0][3]: return np.array((abscisse(l, None, rang, s), y_axe)), vers
            x0, x1 = cle[1][l][j0], suivante[1][l][j1]
            rayon = (1 - s) * abs(x0 - centres[0]) * geos[0]['pas'] + s * abs(x1 - centres[1]) * geos[1]['pas']
            angle = cadre_a(s)[1]
            c_, s_ = math.cos(angle), math.sin(angle)
            return (sur_le_segment(rayon * (1 if x0 > centres[0] else -1), s),
                    np.array((c_ * vers[0] - s_ * vers[1], s_ * vers[0] + c_ * vers[1])))
        def pied(l, bout, s):
            """Pied (avant aplatissement) de la descente du bout (0 : début, -1 : fin) du lacet l, sous son
            premier (dernier) point, commun ou non."""
            x = (1 - s) * abscisse(l, 0, bout % len(cle[1][l])) + s * abscisse(l, 1, bout % len(suivante[1][l]))
            _, _, aplati, y_sous = cadre_a(s)
            return np.array((x, y_axe + (y_sous - y_axe) / aplati))
        haut = np.array((0, -1))

        # où se raccordent les deux arcs de chaque brin qui sort du bloc : au passant (image clé de départ, s = 0)
        # ou au point nouveau (image clé d'arrivée, s = 1)
        raccords = {}
        for l in range(len(cle[1])):
            nb = len(communs[0][l])
            for rang in range(-1, nb):
                # ecarts : nombre de points non communs entre ce point commun (ou le clou) et le suivant
                bornes = [[-1] + c_[l] + [len(e[1][l])] for c_, e in zip(communs, etats)]
                ecarts = [b[rang + 2] - b[rang + 1] - 1 for b in bornes]
                assert sum(ecarts) <= 1, "au plus un passant ou un point nouveau par brin"
                if sum(ecarts) == 0: continue
                quel = ecarts.index(1)
                s = float(quel)
                j = bornes[quel][rang + 1] + 1
                vrai = np.array((abscisse(l, quel, j), y_axe))
                if rang == -1: bouts = (pied(l, 0, s), haut) + noeud(l, 0, s)
                elif rang == nb - 1: bouts = noeud(l, rang, s) + (pied(l, -1, s), -haut)
                else: bouts = noeud(l, rang, s) + noeud(l, rang + 1, s)
                raccords[(l, rang)] = (min(0.98, max(0.02, lieu_des_raccords(*bouts)[0](vrai))), quel)

        for n in range(1, images + 1):
            s = lisse(n / images)
            x_centre, angle, aplati, y_sous = cadre_a(s)
            def aplatit(points):
                q = np.array(points, dtype=float)
                q[..., 1] = y_axe + (q[..., 1] - y_axe) * aplati
                return q
            def brin(p0, t0, p1, t1, raccord):
                """Paire d'arcs dont le raccord glisse de sa place dans l'image clé (raccord = (place, image clé))
                vers la place d'équilibre, atteinte au tiers du mouvement."""
                if raccord is None: return deux_arcs(p0, t0, p1, t1)
                j = raccord_egal(p0, t0, p1, t1)
                if j is None: return deux_arcs(p0, t0, p1, t1, raccord[0])
                poids = lisse(min(1, 3 * abs(s - raccord[1])))
                return deux_arcs(p0, t0, p1, t1, (1 - poids) * raccord[0] + poids * lieu_des_raccords(p0, t0, p1, t1)[0](j))
            lignes = []
            for l in range(len(cle[1])):
                nb = len(communs[0][l])
                morceaux = []
                for rang in range(-1, nb):
                    if rang in (-1, nb - 1):
                        bout = 0 if rang == -1 else -1
                        p = pied(l, bout, s)
                        bas = descente_au_clou(p[0], y_sous, y_sous, *clou)[:-1]
                        if (l, rang) in raccords:
                            q, t = noeud(l, rang + 1 if bout == 0 else rang, s)
                            ligne = np.concatenate((bas, aplatit(brin(p, haut, q, t if bout == 0 else -t, raccords[(l, rang)]))))
                        else:
                            ligne = descente_au_clou(p[0], y_axe, y_sous, *clou)
                        morceaux.append(ligne if bout == 0 else ligne[::-1])
                    else:
                        morceaux.append(aplatit(brin(*noeud(l, rang, s), *noeud(l, rang + 1, s), raccords.get((l, rang)))))
                lignes.append(np.concatenate(morceaux))
            # les trous : les deux du bloc sur le segment tournant, les autres sur l'axe
            rayon = (1 - s) * (cle[0][i] - cle[0][i - 1]) / 2 * geos[0]['pas'] + s * (suivante[0][i] - suivante[0][i - 1]) / 2 * geos[1]['pas']
            trous = np.array([((1 - s) * geos[0]['X'](x0) + s * geos[1]['X'](x1), y_axe) for x0, x1 in zip(*[e[0] for e in etats])])
            trous[i - 1], trous[i] = sur_le_segment(-rayon, s), sur_le_segment(rayon, s)
            trous = aplatit(trous)
            if verifie:
                mots = [calcule_autofn_de_tresse(tresse[:k + q], nb_trous) for q in (0, 1)]
                en_ordre = sorted(trous.tolist())
                assert abs(trous[i - 1][0] - trous[i][0]) < 1e-6 or [lit_mot(q, en_ordre) for q in lignes] in mots, \
                       f"lettre {k}, image {n} : mots des lacets"
            # les segments noirs : l'axe de part et d'autre du bloc, et le segment tournant (trous et doigts)
            bout = rayon + (nb_doigts + 0.5) * ((1 - s) * geos[0]['pas'] + s * geos[1]['pas'])
            axe = [np.array(((5, y_axe), (x_centre - bout, y_axe))), np.array(((x_centre + bout, y_axe), (largeur - 5, y_axe))),
                   aplatit((sur_le_segment(-bout, s), sur_le_segment(bout, s)))]
            dessins.append((lignes, trous, clou, axe))
            durees.append(duree)
        cle = suivante
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

dessine_auto_de_tresse([1, 1, 2, 2], './imgs/nouv_1122.png')
dessine_auto_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/nouv_43m1m12m41.png', largeur_brin=3)
film_de_tresse([4, 3, -1, -1, 2, -4, 1], './imgs/film_43m1m12m41.gif', largeur_brin=3)
film_de_tresse_algebrique([4, 3, -1, -1, 2, -4, 1], './imgs/film_continu_43m1m12m41.gif', largeur_brin=3)
film_de_tresse_simultane([4, 3, -1, -1, 2, -4, 1], './imgs/film_simultane_43m1m12m41.gif', largeur_brin=3)
gif_en_mp4('./imgs/film_43m1m12m41.gif')
gif_en_mp4('./imgs/film_continu_43m1m12m41.gif')
gif_en_mp4('./imgs/film_simultane_43m1m12m41.gif')
# essais en arcs de cercle, pas encore au point (croisements) : décommenter pour les produire
# film_de_tresse_simultane([4, 3, -1, -1, 2, -4, 1], './imgs/essai_noeuds_43m1m12m41.gif', largeur_brin=3, en_arcs=True)
# film_de_tresse_en_arcs([4, 3, -1, -1, 2, -4, 1], './imgs/essai_arcs_43m1m12m41.gif', largeur_brin=3)
