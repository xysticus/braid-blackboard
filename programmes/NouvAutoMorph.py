import functools
import itertools
import operator
import math
import cairo
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

def image_auto_de_tresse(tresse, nb_trous=None, hauteur=400, largeur=400, largeur_brin=4, en_couleur=True):
    '''Surface Cairo des images des générateurs de fn par l'automorphisme de la tresse.'''
    auto = calcule_autofn_de_tresse(tresse, nb_trous)
    lacets = [intervalles(mot) for mot in auto]
    rang_point, rang_trou, nb_rangs = abscisses(lacets, len(lacets))

    pas = (largeur - 40) / (nb_rangs - 1)
    def x(rang): return 20 + rang * pas
    y_axe = 0.4 * hauteur
    x_clou, y_clou = largeur / 2, hauteur - 10
    y_sous_arcs = hauteur - 40 # le chemin vers le clou passe sous tous les arcs du bas

    # on aplatit les arcs pour qu'ils tiennent en hauteur
    rayon_max = max(abs(x(rang_point[(i, j)]) - x(rang_point[(i, j + 1)])) / 2
                    for i, lacet in enumerate(lacets) for j in range(len(lacet) - 1))
    aplati = min(1, (y_axe - 10) / rayon_max, (y_sous_arcs - y_axe - 5) / rayon_max)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, largeur, hauteur)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.set_line_width(largeur_brin)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    couleurs = [(1, 0, 0), (0, .7, 0), (0, 0, 1), (.7, .7, 0), (.7, 0, .7), (0, .7, .7)]
    if not en_couleur: couleurs = [(0, 0, 0)]

    def demi_ellipse(x1, x2, en_haut):
        ctx.save()
        ctx.translate((x1 + x2) / 2, y_axe)
        ctx.scale(abs(x2 - x1) / 2, abs(x2 - x1) / 2 * aplati)
        depart = math.pi if x1 < x2 else 0
        if en_haut == (x1 < x2): ctx.arc(0, 0, 1, depart, depart + math.pi)
        else: ctx.arc_negative(0, 0, 1, depart, depart - math.pi)
        ctx.restore()

    for i, lacet in enumerate(lacets):
        xs = [x(rang_point[(i, j)]) for j in range(len(lacet))]
        ctx.set_source_rgb(*couleurs[i % len(couleurs)])
        ctx.move_to(x_clou, y_clou)
        ctx.curve_to(xs[0], y_clou, xs[0], y_clou, xs[0], y_sous_arcs)
        ctx.line_to(xs[0], y_axe)
        for j in range(len(lacet) - 1):
            demi_ellipse(xs[j], xs[j + 1], j % 2 == 0)
        ctx.line_to(xs[-1], y_sous_arcs)
        ctx.curve_to(xs[-1], y_clou, xs[-1], y_clou, x_clou, y_clou)
        ctx.stroke()

    ctx.set_source_rgb(0, 0, 0)
    for rang in rang_trou.values():
        ctx.arc(x(rang), y_axe, largeur_brin, 0, 2 * math.pi)
        ctx.fill()
    ctx.arc(x_clou, y_clou, largeur_brin, 0, 2 * math.pi)
    ctx.fill()

    return surface

def dessine_auto_de_tresse(tresse, fichier, **options):
    '''Dessine en PNG les images des générateurs de fn par l'automorphisme de la tresse.'''
    image_auto_de_tresse(tresse, **options).write_to_png(fichier)

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
