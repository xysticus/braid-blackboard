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

from tresses import * # base commune : mots, état, dessin d'un état, arcs, images

# tests sur la tresse compliquée
t = calcule_autofn_de_tresse([1,1,2,2])
print(t)

d = calcule_arcs(t[0]) 
print(d)

print(calcule_arcs(t[1]))

print(calcule_arcs(t[2]))

# Le film algébrique : chaque lettre est une suite de mouvements élémentaires sur l'état, chacun continu.
# 1. réespacement (les abscisses changent, leur ordre non : les demi-cercles ne se croisent jamais) pour vider
#    une marge autour du bloc des trous i et i+1 ;
# 2. demi-tour du bloc ; dans la marge, une couronne où seuls les arcs qui sortent du bloc s'enroulent ;
# 3. retouche du dessin tordu vers le dessin de l'état non réduit (agit), morceau par morceau ;
# 4. suppression des bigones par vagues : les deux points d'un bigone le plus intérieur glissent l'un vers l'autre,
#    puis les arcs qui les entouraient se fondent en un seul ;
# 5. réespacement vers la mise en page de l'image clé suivante.


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
film_de_tresse_simultane([4, 3, -1, -1, 2, -4, 1], './imgs/film_simultane_43m1m12m41.gif', largeur_brin=3)
gif_en_mp4('./imgs/film_43m1m12m41.gif')
gif_en_mp4('./imgs/film_continu_43m1m12m41.gif')
gif_en_mp4('./imgs/film_simultane_43m1m12m41.gif')
# essais en arcs de cercle, pas encore au point (croisements) : décommenter pour les produire
# film_de_tresse_simultane([4, 3, -1, -1, 2, -4, 1], './imgs/essai_noeuds_43m1m12m41.gif', largeur_brin=3, en_arcs=True)
# film_de_tresse_en_arcs([4, 3, -1, -1, 2, -4, 1], './imgs/essai_arcs_43m1m12m41.gif', largeur_brin=3)
