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

def conjugue_droite(m1, m2):
    return m1 + m2 + inverse(m1)

def conjugue_gauche(m1, m2):
    return inverse(m2) + m1 + m2

def conjugaison_locale (sigma, images):
    '''Sert à calculer l'automorphisme de fn associé à une tresse.
    L'automorphisme est donné par l'image de chaque des générateurs.
    Ces images sont rangées dans le tableau "images".
    A l'index i on trouve l'image de x_(i+1) '''
    xi = abs(sigma)
    x1 = images[xi - 1]
    x2 = images[xi]
    if sigma > 0:
        images[xi - 1] = conjugue_droite(x1, x2)
        images[xi] = x1
    else:
        images[xi - 1] = x2
        images[xi] = conjugue_gauche(x1, x2)
        
def simplifie(mot_de_fn): 
    '''Simplifie entièrement un mot de fn
    Travaille par effet de bord'''
    i = 0 
    while i < len(mot_de_fn) - 1: 
        if mot_de_fn[i] == -mot_de_fn[i + 1]: 
            del mot_de_fn[i:i+2] 
            i-=1 
            if i < 0: 
                i = 0 
        else: 
            i+=1
            
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

def decoupeuse(liste):
    '''Decoupe une liste d'entiers en suites monotones croissantes.'''
    resultat = []
    longueur = len(liste)
    i = 0
    j = 0
    while j < longueur - 1:
        if liste[j] + 1 != liste[j + 1]:
            resultat.append(liste[i:j + 1])
            i = j + 1
        j += 1
    resultat.append(liste[i:j+1])

def nouvelle_decoupe(liste):
    debut = liste[0]
    courant = liste[0]
    resultat = []
    for i in range(1,len(liste)):
        match liste[i]:
            case t if t - courant == 1: courant = t
            case t : 
                resultat.append((debut, courant))
                signe_bas = 1 if abs(t) - abs(courant) < 0 else - 1
                if signe_bas < 0:
                    tt = abs(courant) + 1 if courant > 0 else abs(courant)
                    qq = abs(t) - 1 if t > 0 else abs(t)
                else:
                    tt = abs(courant) if courant > 0 else abs(courant) - 1
                    qq = abs(t) if t > 0 else abs(t) + 1
                resultat.append((tt * signe_bas, qq * signe_bas))                               
                courant = t
                debut = t
    resultat.append((debut, courant))
    return resultat

t = calcule_autofn_de_tresse([1,1,2,2])
print(t)

d = nouvelle_decoupe(t[0]) 
print(d)

print(nouvelle_decoupe(t[1]))

print(nouvelle_decoupe(t[2]))

def generatrice_haut(suites):
    ''' Calcule tous les arcs qui apparaissent dans l'hémisphère nord.
    L'entrée est une liste de suites croissantes
    La sortie une liste d'arcs.'''
    def calcule_arc(suite):
        tete = abs(suite[0])
        queue = abs(suite[-1])
        if suite[0] < 0:
            return (tete, queue -1)
        else:
            return (tete - 1, queue)
    return [calcule_arc(arc) for arc in suites]

def generatrice_bas(suites):
    '''Idem generatrice_haut sauf que là ça calcule les arc de l'hémisphère sud.'''
    def reorganise_paire(x, y):
        if x > 0:
            a = x
        else:
            a = -x - 1
        if y > 0:
            b = y - 1
        else:
            b = -y
        return (a , b)                     
    i = 0
    resultat = []
    encore_deux = len(suites) - 2
    while i <= encore_deux:
        resultat.append(
            reorganise_paire(
                suites[i][-1], suites[i + 1][0]))
        i += 1
    return resultat
