import functools
import itertools
import operator
import math
import cairo


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

def calcule_autofn_de_tresse(tresse):
    '''Calcule l'automorphisme du groupe libre associé à une tresse.
    La tresse est donnée par la liste de ses générateurs.'''
    auto = morphisme_identite(5 if not(tresse) else max(map(operator.abs, tresse)))
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

# le type pour une intersection (numéro du brin, numéro du trou, position sur le brin)
# si le numéro du brin est nul, c'est un trou de numéro le numéro du trou
# si le numéro du trou est nul c'est un brin de position le numéro du brin 
# position sur le brin 0 est relié au clou en bas. position sur le brin
# valant longueur du brin en arcs est relié au clou.
# la parité de l'index indique si on insère en haut ou en bas. Pair en haut impair en bas.
# algo : on part de l'intersection de départ. On se déplace à gauche ou à droite 
# en fonction du signe de l'arc suivant vers le trou ciblé.  On stocke les arcs croisés qui sont 
# du côté de notre arc (nord ou sud c'est la parité de la position sur le brin qui le dit).
# On enlève du stock si on croise l'autre extrémité.
# Une fois le trou cible dépassé si le stock est vide, on a trouvé l'intersection d'arrivée.
# la parité de la position sur le brin indique quelle moitié on considère.
# on sait par le pied de départ de l'arc autour de quoi on a tourné par le 
# pied d'arrivée autour du quel on tourne à l'arrivée
# A la fin on a un tableau d'intersections.
# Pour finalement parcourir un brin il faut retrouver chacune des intersections et noter son index
# on fait un dictionnaire avec comme clées les triplet no bnrin, no trou, position et comme valeur l'index

def insere_arc(droite, index_droite, arc, index_arc):
    def arc_neutre(dep,arr):
        return min(abs(dep),abs(arr)), max(abs(dep),abs(arr))

    (depart, arrivee) = arc
    sens = 1 if depart > 0 else -1 # On se déplace à gauche ou à droite 
                                    # en fonction du signe de l'arc suivant vers le trou ciblé.
    i = abs(depart)  # on part de l'intersection de départ.
    ensemble = set()
    trou_atteind = False

    while True:
        (brin, trou, position) = droite[index_droite]
        trou_atteind = trou == abs(arrivee)

        if len(ensemble) == 0: break 
        i += sens
    
    return droite

