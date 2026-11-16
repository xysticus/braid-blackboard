"""Raccord par triangulation mobile, pour le film conforme (piste « la triangulation pendant le raccord »,
`pistes_film_conforme.md`).

Pendant la fenêtre de raccord d'une lettre, le film conforme passe du dessin de l'état k (sur L–A–B–R) au dessin de
l'état k+1 (sur L–B–A–R). Au lieu de mélanger les deux dessins, on les fait vivre sur un maillage dont les sommets sont
les trous, le clou et des points d'un bord convexe hors de l'image :

1. transport : quand les trous bougent, chaque triangle est déformé par l'application affine qui suit ses sommets
   (les arêtes qui cessent d'être de Delaunay sont retournées entre deux pas, sans rien changer au dessin). C'est une
   déformation continue du plan (une isotopie) : un dessin sans croisement le reste. Le dessin de départ est
   transporté du début à la fin de la fenêtre, le dessin d'arrivée de la fin vers le début ;
2. à chaque image de la fenêtre, on a donc deux dessins des mêmes lacets sur le même maillage. Les sommets étant les
   trous (et le clou), la suite des arêtes traversées par un lacet, bigones annulés, est la même pour les deux
   (`assert`) : leurs pieds sur les arêtes se correspondent un à un, dans le même ordre sur chaque arête ;
3. le passage : le dessin de départ se tend en cordes entre ses pieds (`tend_en_cordes`) ; les pieds glissent sur
   leurs arêtes de leur place de départ à leur place d'arrivée (l'ordre sur chaque arête est gardé, et deux cordes d'un
   triangle dont les extrémités ne s'entrelacent pas ne se croisent pas : aucun croisement, par construction) ; puis
   les cordes se courbent en dessin d'arrivée. Au bord de la fenêtre on retrouve exactement les dessins conformes.
"""
import math
import numpy as np

from Triangulation import Maillage, croix
from tresses import deux_arcs


def maillage_du_raccord(trous, clou, largeur, hauteur, marge=40, par_cote=6):
    """Maillage de Delaunay dont les sommets sont un bord convexe (rectangle bombé de `marge` pixels hors de l'image,
    `par_cote` points par côté), les trous puis le clou. Renvoie (maillage, indices des trous, indice du clou)."""
    x0, y0, x1, y1 = -marge, -marge, largeur + marge, hauteur + marge
    bord = []
    for k in range(par_cote): # le bord tourne dans le sens horaire de l'écran ; bombé pour être strictement convexe
        u = k / par_cote
        bosse = 3 * math.sin(math.pi * u)
        bord.append((x0 + u * (x1 - x0), y0 - bosse))
    for k in range(par_cote):
        u = k / par_cote
        bord.append((x1 + 3 * math.sin(math.pi * u), y0 + u * (y1 - y0)))
    for k in range(par_cote):
        u = k / par_cote
        bord.append((x1 - u * (x1 - x0), y1 + 3 * math.sin(math.pi * u)))
    for k in range(par_cote):
        u = k / par_cote
        bord.append((x0 - 3 * math.sin(math.pi * u), y1 - u * (y1 - y0)))
    triangles = [(0, k, k + 1) for k in range(1, len(bord) - 1)] # éventail d'un polygone strictement convexe
    m = Maillage(bord, triangles)
    ordre = sorted(range(len(trous)), key=lambda p: (trous[p][0], trous[p][1]))
    indices = [None] * len(trous)
    for p in ordre: indices[p] = insere(m, trous[p])
    i_clou = insere(m, clou)
    m.delaunay([])
    return m, indices, i_clou


def insere(m, p):
    """Ajoute le sommet p au maillage (sans courbes) : le triangle qui le contient est coupé en trois, ou, s'il est
    sur une arête, les deux triangles qui la bordent sont coupés en deux. Renvoie l'indice du sommet."""
    p = np.asarray(p, dtype=float)
    v = len(m.pos)
    m.pos = np.vstack((m.pos, p))
    for t in list(m.triangles):
        a, b, c = sorted(t)
        s = [croix(m.pos[y] - m.pos[x], p - m.pos[x]) for x, y in ((a, b), (b, c), (c, a))]
        echelle = max(np.hypot(*(m.pos[b] - m.pos[a])), np.hypot(*(m.pos[c] - m.pos[b])), 1.0)
        nuls = [abs(x) < 1e-9 * echelle for x in s]
        if all(x > 0 or z for x, z in zip(s, nuls)) or all(x < 0 or z for x, z in zip(s, nuls)):
            if not any(nuls):
                nouveaux = [(a, b, v), (b, c, v), (c, a, v)]
                retires = [t]
            else: # sur une arête : on coupe aussi le triangle voisin
                x, y = [(a, b), (b, c), (c, a)][nuls.index(True)]
                autre = [u for u in m.triangles if u != t and {x, y} <= u]
                retires = [t] + autre
                z = next(iter(t - {x, y}))
                nouveaux = [(x, z, v), (y, z, v)]
                if autre: w = next(iter(autre[0] - {x, y})); nouveaux += [(x, w, v), (y, w, v)]
            for u in retires:
                m.triangles.remove(u)
                del m.signes[u]
            for u in nouveaux:
                u = frozenset(u)
                m.triangles.add(u)
                m.signes[u] = m.signe(u)
            return v
    raise ValueError("sommet hors du maillage")


def localise(triangles, pos, X):
    """Pour chaque point de X (m × 2), un triangle qui le contient (le plus « intérieur » si plusieurs) et ses
    coordonnées barycentriques : (indices des sommets m × 3, coordonnées m × 3)."""
    T = np.array([sorted(t) for t in triangles])
    A, B, C = pos[T[:, 0]], pos[T[:, 1]], pos[T[:, 2]]
    v0, v1 = B - A, C - A
    det = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
    d = X[None, :, :] - A[:, None, :]
    l1 = (d[..., 0] * v1[:, None, 1] - d[..., 1] * v1[:, None, 0]) / det[:, None]
    l2 = (v0[:, None, 0] * d[..., 1] - v0[:, None, 1] * d[..., 0]) / det[:, None]
    l0 = 1 - l1 - l2
    pire = np.minimum(np.minimum(l0, l1), l2)
    k = np.argmax(pire, axis=0)
    r = np.arange(len(X))
    assert pire[k, r].min() > -1e-6, "point hors du maillage"
    return T[k], np.column_stack((l0[k, r], l1[k, r], l2[k, r]))


def transporte(lignes, triangles, avant, apres):
    """Images des lignes par l'application affine par triangles qui envoie les positions avant sur apres."""
    tailles = [len(l) for l in lignes]
    X = np.concatenate(lignes)
    S, L = localise(triangles, avant, X)
    Y = (L[:, :, None] * apres[S]).sum(axis=1)
    return np.split(Y, np.cumsum(tailles)[:-1])


def coupe(points, triangles, pos, clou, brutes=False):
    """Traversées des arêtes par une polyligne qui part du clou et y revient, bigones annulés : liste de
    (position le long de la polyligne, arête (u, v) avec u < v, fraction de u vers v). Le clou n'est pas un trou mais
    le point base des lacets : un lacet peut tourner autour de lui en partant (ou en arrivant) sans changer de classe,
    donc les traversées des arêtes du clou en tête et en queue de la suite ne comptent pas, on les retire (le lacet
    rejoint alors le clou par une corde dans un triangle de l'étoile du clou)."""
    aretes = {tuple(sorted(e)) for t in triangles for e in ((a, b) for a in t for b in t if a < b)}
    trouves = []
    for (u, v) in aretes:
        s = pos[v] - pos[u]
        longueur = math.hypot(*s)
        # côté de chaque point par rapport à la droite de l'arête ; un point posé sur l'arête (pied d'un arc, à
        # l'arrondi près) compte toujours du même côté : une traversée est un changement de côté, jamais doublée ni
        # manquée par un pied posé exactement sur l'arête
        cote = (s[0] * (points[:, 1] - pos[u][1]) - s[1] * (points[:, 0] - pos[u][0])) / longueur
        dessus = cote >= -1e-7
        k = np.nonzero(dessus[:-1] != dessus[1:])[0]
        if len(k) == 0: continue
        t = cote[k] / (cote[k] - cote[k + 1])
        X = points[k] + t[:, None] * (points[k + 1] - points[k])
        w = ((X - pos[u]) @ s) / (longueur * longueur)
        for kk, tt, ww in zip(k, t, w):
            if 1e-9 < ww < 1 - 1e-9: trouves.append((kk + tt, (u, v), ww))
    trouves.sort(key=lambda x: x[0])
    propres = trouves
    pile = []
    for x in propres:
        if pile and pile[-1][1] == x[1]: pile.pop()
        else: pile.append(x)
    while pile and clou in pile[0][1]: pile.pop(0)
    while pile and clou in pile[-1][1]: pile.pop()
    return (pile, propres) if brutes else pile


def point_en(points, position):
    k = min(int(position), len(points) - 2)
    return points[k] + (position - k) * (points[k + 1] - points[k])

def morceau(points, a, b):
    interieurs = [points[v] for v in range(math.floor(a) + 1, math.ceil(b)) if a < v < b]
    return np.array([point_en(points, a)] + interieurs + [point_en(points, b)])

def reechantillonne(points, n):
    cumul = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(points, axis=0).T))))
    if cumul[-1] == 0: return np.repeat(points[:1], n, axis=0)
    s = np.linspace(0, cumul[-1], n)
    return np.column_stack((np.interp(s, cumul, points[:, 0]), np.interp(s, cumul, points[:, 1])))

def tend_en_cordes(points, coupes, poids):
    """Dessin d'un lacet tendu en cordes au poids donné : chaque morceau entre deux pieds consécutifs (bigones
    compris) est mélangé avec la corde qui relie ses deux pieds (0 : le dessin, 1 : les cordes)."""
    bornes = [0.0] + [c[0] for c in coupes] + [len(points) - 1.0]
    morceaux = []
    for a, b in zip(bornes[:-1], bornes[1:]):
        m = morceau(points, a, b)
        n = max(len(m), 2)
        m = reechantillonne(m, n)
        corde = np.linspace(m[0], m[-1], n)
        morceaux.append((1 - poids) * m + poids * corde)
    return np.concatenate([morceaux[0]] + [m[1:] for m in morceaux[1:]])


def arrondit(points, part=0.5, depart=None, arrivee=None, trous=None):
    """La ligne brisée des points, chaque coude arrondi par un congé : arc de cercle tangent aux deux segments, qui en
    prend au plus `part` du plus court (comme `Film.polyligne` du film triangulé). Les deux bouts ne bougent pas.
    depart (arrivee) : direction unitaire de la courbe qui arrive au premier point (qui part du dernier) ; le début
    du premier segment (la fin du dernier) est alors remplacé par une paire d'arcs tangente à cette courbe et au
    segment, sur au plus `part` du segment : plus de coin à la jonction. trous : chaque arrondi (congé ou paire
    d'arcs) reste dans un disque centré sur son coude de rayon 0,9 × la distance du coude au trou le plus proche :
    il ne passe jamais de l'autre côté d'un trou, et la règle étant continue, deux brins voisins enroulés autour du
    même trou ont des arrondis voisins, emboîtés."""
    points = [np.asarray(p, dtype=float) for p in points]
    trous = np.zeros((0, 2)) if trous is None else np.asarray(trous, dtype=float)
    def rayon_libre(v): return 0.9 * np.hypot(*(trous - v).T).min() if len(trous) else math.inf
    dessin = [points[0]]
    if depart is not None and len(points) > 1:
        corde = points[1] - points[0]
        lg = math.hypot(*corde)
        if lg > 1e-9 and depart @ (corde / lg) < 1 - 1e-9:
            c = min(part * lg, rayon_libre(points[0]) / 2) # une paire d'arcs ne sort pas d'un disque de rayon ~ 2c
            dessin = list(deux_arcs(points[0], depart, points[0] + c * corde / lg, corde / lg))
    for a, v, b in zip(points[:-2], points[1:-1], points[2:]):
        la, lb = math.hypot(*(a - v)), math.hypot(*(b - v))
        if la < 1e-9 or lb < 1e-9:
            dessin.append(v)
            continue
        ua, ub = (a - v) / la, (b - v) / lb
        if ua @ ub < -1 + 1e-9: # pas de coude
            dessin.append(v)
            continue
        c = min(part * min(la, lb), rayon_libre(v))
        dessin.extend(deux_arcs(v + c * ua, -ua, v + c * ub, ub))
    if arrivee is not None and len(points) > 1:
        corde = points[-1] - points[-2]
        lg = math.hypot(*corde)
        if lg > 1e-9 and arrivee @ (corde / lg) < 1 - 1e-9:
            c = min(part * lg, rayon_libre(points[-1]) / 2)
            dessin.extend(deux_arcs(points[-1] - c * corde / lg, corde / lg, points[-1], arrivee))
            return np.array(dessin)
    dessin.append(points[-1])
    return np.array(dessin)


def decoupe_aux_aretes(points, aretes, pos):
    """Coupe la polyligne là où elle traverse successivement les arêtes données (une traversée par arête, dans
    l'ordre) ; renvoie les morceaux (un de plus que d'arêtes), ou None si une traversée manque."""
    morceaux, debut = [], 0.0
    for (u, v) in aretes:
        s = pos[v] - pos[u]
        cote = s[0] * (points[:, 1] - pos[u][1]) - s[1] * (points[:, 0] - pos[u][0])
        dessus = cote >= 0
        trouve = None
        for k in range(int(debut), len(points) - 1):
            if dessus[k] != dessus[k + 1]:
                t = cote[k] / (cote[k] - cote[k + 1])
                X = points[k] + t * (points[k + 1] - points[k])
                w = ((X - pos[u]) @ s) / (s @ s)
                if 0 < w < 1 and k + t > debut:
                    trouve = k + t
                    break
        if trouve is None: return None
        morceaux.append(morceau(points, debut, trouve))
        debut = trouve
    morceaux.append(morceau(points, debut, len(points) - 1.0))
    return morceaux


class RaccordTriangule:
    """Raccord d'une lettre entre les temps s_a (dessin de départ, réduction r_a) et s_b (dessin d'arrivée, r_b).
    positions(s, r) : positions à l'écran des trous physiques au temps s avec la réduction r. temps : les temps des
    images de la fenêtre, croissants, strictement entre s_a et s_b. tournants : les deux trous physiques qui tournent.
    phases : dans la fenêtre (poids de 0 à 1), début et fin de la mise en cordes, puis début et fin du retour aux
    arcs (voir `lignes`)."""

    def __init__(self, positions, clou, largeur, hauteur, s_a, r_a, depart, s_b, r_b, arrivee, temps, tournants,
                 sous_pas=8, phases=(0.0, 0.35, 0.65, 1.0)):
        self.clou_ecran = np.asarray(clou, dtype=float)
        def reduction(s): return r_a + (r_b - r_a) * (s - s_a) / (s_b - s_a)
        # tous les temps du transport : ceux des images, et des sous-pas entre eux
        reperes = [s_a] + list(temps) + [s_b]
        self.instants = [s_a]
        self.image_de = {}
        for j in range(len(reperes) - 1):
            for k in range(1, sous_pas + 1):
                self.instants.append(reperes[j] + (reperes[j + 1] - reperes[j]) * k / sous_pas)
            if j < len(temps): self.image_de[j] = len(self.instants) - 1
        # passage avant : le maillage suit les trous ; on garde (triangles après retournements, positions)
        m, self.i_trous, self.i_clou = maillage_du_raccord(positions(s_a, r_a), clou, largeur, hauteur)
        etats = [(list(m.triangles), m.pos.copy())]
        for s in self.instants[1:]:
            for p, v in enumerate(self.i_trous): m.pos[v] = positions(s, reduction(s))[p]
            assert m.valide(), "triangle retourné pendant le raccord : augmenter sous_pas"
            m.delaunay([])
            etats.append((list(m.triangles), m.pos.copy()))
        self.etats = etats
        # le dessin de départ transporté vers l'avant ; le dessin d'arrivée vers l'arrière
        J = len(etats) - 1
        self.depart, self.arrivee = {0: depart}, {J: arrivee}
        D = depart
        for j in range(1, J + 1):
            D = transporte(D, etats[j - 1][0], etats[j - 1][1], etats[j][1])
            self.depart[j] = D
        A = arrivee
        for j in range(J, 0, -1):
            A = transporte(A, etats[j - 1][0], etats[j][1], etats[j - 1][1])
            self.arrivee[j - 1] = A
        self.reduction = reduction
        self.tournants = {self.i_trous[p] for p in tournants}
        self.phases = phases

    def lignes(self, f, poids):
        """Lacets de l'image f de la fenêtre au poids donné (0 : départ, 1 : arrivée). Un lacet est découpé en morceaux
        entre ses pieds sur les arêtes (bigones annulés) ; les pieds des deux dessins se correspondent un à un.
        - Avant phases[0] : le dessin de départ transporté ; après phases[3] : celui d'arrivée.
        - Les pieds glissent sur leurs arêtes entre phases[1] et phases[2] (l'ordre sur chaque arête est gardé).
        - Les morceaux d'un triangle qui touche un des deux trous qui tournent, ou qui contient un bigone, passent
          tous par la corde (le choix se fait par triangle : une corde et une courbe du même triangle se croiseraient),
          les coudes des cordes consécutives arrondis par des congés (`arrondit`) : il se tend de phases[0] à phases[1], reste une corde pendant le glissement (deux cordes d'un même
          triangle dont les pieds ne s'entrelacent pas ne se croisent pas), et se courbe de phases[2] à phases[3].
        - Les morceaux des autres triangles, loin du demi-tour, passent directement du morceau de départ à celui d'arrivée pendant
          le glissement : le mélange de deux courbes d'un triangle reste dans ce triangle (il est convexe).
        Renvoie (lignes, anomalies)."""
        j = self.image_de[f]
        triangles, pos = self.etats[j]
        p0, p1, p2, p3 = self.phases
        tension = lisse(min(1, max(0, (poids - p0) / (p1 - p0))))
        glisse = lisse(min(1, max(0, (poids - p1) / (p2 - p1))))
        courbe = lisse(min(1, max(0, (poids - p2) / (p3 - p2))))
        # premier passage : les morceaux de chaque lacet, avec leur triangle (les sommets de leurs deux arêtes)
        anomalies, decoupes, en_cordes = [], [], set()
        for l, (D, A) in enumerate(zip(self.depart[j], self.arrivee[j])):
            (cd, bd), (ca, ba) = coupe(D, triangles, pos, self.i_clou, True), coupe(A, triangles, pos, self.i_clou, True)
            if [c[1] for c in cd] != [c[1] for c in ca]:
                anomalies.append((l, 'traversées différentes'))
                decoupes.append(None)
                continue
            bornes_d = [0.0] + [c[0] for c in cd] + [len(D) - 1.0]
            bornes_a = [0.0] + [c[0] for c in ca] + [len(A) - 1.0]
            sommets = [{self.i_clou}] + [set(c[1]) for c in cd] + [{self.i_clou}]
            morceaux = []
            for m in range(len(bornes_d) - 1):
                triangle = frozenset(sommets[m] | sommets[m + 1])
                bigone = any(bornes_d[m] < x[0] < bornes_d[m + 1] for x in bd) or \
                         any(bornes_a[m] < x[0] < bornes_a[m + 1] for x in ba)
                # un triangle passe en cordes s'il touche un trou qui tourne ou s'il contient un bigone : tous ses
                # morceaux sont alors traités de la même façon (une corde et une courbe du même triangle se croiseraient)
                if bigone or triangle & self.tournants: en_cordes.add(triangle)
                morceaux.append((triangle, reechantillonne(morceau(D, bornes_d[m], bornes_d[m + 1]), 60),
                                 reechantillonne(morceau(A, bornes_a[m], bornes_a[m + 1]), 60),
                                 cd[m][1] if m < len(cd) else None)) # arête du pied de fin du morceau
            decoupes.append(morceaux)
        # second passage : les formes. Les morceaux en cordes consécutifs d'un lacet forment une suite, tracée comme
        # une ligne brisée dont les coudes (sur les pieds) sont arrondis par des congés ; ses deux bouts, où elle
        # rejoint des morceaux courbes, ne bougent pas
        resultat = []
        for l, morceaux in enumerate(decoupes):
            if morceaux is None:
                resultat.append(self.depart[j][l] if poids < 0.5 else self.arrivee[j][l])
                continue
            def tangente(courbe, au_debut):
                """Direction unitaire de la courbe à son début (en partant) ou à sa fin (en arrivant)."""
                pts = courbe if not au_debut else courbe[::-1]
                for k in range(len(pts) - 2, -1, -1):
                    d = pts[-1] - pts[k]
                    if math.hypot(*d) > 1e-6: return (d / math.hypot(*d)) * (1 if not au_debut else -1)
                return None
            courbes = {m: (1 - glisse) * pd + glisse * pa for m, (triangle, pd, pa, _) in enumerate(morceaux)
                       if triangle not in en_cordes}
            formes, m = [], 0
            while m < len(morceaux):
                if m in courbes:
                    formes.append(courbes[m])
                    m += 1
                    continue
                debut = m
                while m < len(morceaux) and m not in courbes: m += 1
                suite = morceaux[debut:m]
                pieds = [(1 - glisse) * suite[0][1][0] + glisse * suite[0][2][0]] + \
                        [(1 - glisse) * pd[-1] + glisse * pa[-1] for _, pd, pa, _ in suite]
                # jonctions avec les morceaux courbes voisins : leurs tangentes aux pieds
                avant = tangente(courbes[debut - 1], False) if debut - 1 in courbes else None
                apres = tangente(courbes[m], True) if m in courbes else None
                cordes = arrondit(np.array(pieds), depart=avant, arrivee=apres, trous=pos[self.i_trous])
                if 0 < glisse < 1: forme = cordes
                else:
                    # mélange triangle par triangle : les cordes arrondies sont coupées là où elles traversent les
                    # arêtes des pieds, et chaque morceau est mélangé avec le morceau du même triangle ; le mélange de
                    # deux courbes d'un triangle reste dans ce triangle, il ne passe jamais par-dessus un trou (un
                    # mélange d'un seul tenant le long de la suite le pouvait)
                    q = 1 if glisse == 0 else 2
                    poids_cordes = tension if glisse == 0 else 1 - courbe
                    parts = decoupe_aux_aretes(cordes, [x[3] for x in suite[:-1]], pos)
                    if parts is None: # repli : cordes droites, sans arrondi
                        parts = [np.array((x[q][0], x[q][-1])) for x in suite]
                    melanges = []
                    for x, r in zip(suite, parts):
                        n = max(len(x[q]), len(r))
                        melanges.append((1 - poids_cordes) * reechantillonne(x[q], n) + poids_cordes * reechantillonne(r, n))
                    forme = np.concatenate([melanges[0]] + [y[1:] for y in melanges[1:]])
                formes.append(forme)
            resultat.append(np.concatenate([formes[0]] + [x[1:] for x in formes[1:]]))
        return resultat, anomalies


def lisse(u): return u * u * (3 - 2 * u)
