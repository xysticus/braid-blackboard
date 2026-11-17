"""Piste 1 bis (`pistes_film_conforme.md`), avec les arcs entre pointes de `Arcs.py` : tendre les arcs en géodésiques
d'une métrique hyperbolique tirée de la triangulation.

La métrique. Chaque triangle de la triangulation de Delaunay, vu dans son cercle circonscrit, est un triangle idéal du
modèle de Klein : distance de Hilbert d(x, y) = ½ log( |a y| |b x| / (|a x| |b y|) ), a et b étant les points où la
droite xy coupe le cercle (a du côté de x). Le long d'une arête commune, les deux triangles induisent la même distance
(la distance de Hilbert sur un segment ne dépend que de ses extrémités) : les triangles se recollent tels quels, et
tous les sommets (les trous, et les points du bord) sont des pointes à l'infini.

La géodésique d'un arc. Sa suite d'arêtes traversées (donnée par la triangulation mobile) est gardée ; ses pieds sur
ces arêtes sont choisis pour minimiser la longueur hyperbolique (`tend_hyperbolique`, descente coordonnée par
coordonnée : chaque pied minimise la somme des distances à ses deux voisins). Aux bouts, le pied voisin d'une pointe
est relié à un point de la bissectrice du coin à distance ε de la pointe (la longueur jusqu'à la pointe est infinie,
mais sa variation ne l'est pas). Des arcs disjoints ont des géodésiques disjointes : l'ordre des pieds sur chaque
arête se conserve (vérifié).

Le dessin. Dans chaque triangle, la géodésique de Klein est une droite ; on peut la tracer telle quelle (cordes) ou,
pour des arcs, par l'arc orthogonal au cercle circonscrit entre les deux pieds (la géodésique de Poincaré du même
disque).
"""
import math
import numpy as np

from Triangulation import croix


def cercle_circonscrit(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
    uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
    o = np.array((ux, uy))
    return o, math.hypot(*(a - o))

def hilbert(x, y, o, R):
    """Distance de Klein (Hilbert) entre x et y dans le disque de centre o et de rayon R."""
    d = y - x
    L = math.hypot(*d)
    if L < 1e-12: return 0.0
    u = d / L
    # x + t u sur le cercle : t² + 2 t (u·(x - o)) + |x - o|² - R² = 0
    p, q = u @ (x - o), (x - o) @ (x - o) - R * R
    disc = max(p * p - q, 0.0)
    t1, t2 = -p - math.sqrt(disc), -p + math.sqrt(disc) # t1 < 0 (côté x), t2 > L (côté y)
    ax, ay, bx, by = -t1, L - t1, t2, t2 - L
    if ax <= 0 or by <= 0: return math.inf
    return 0.5 * math.log((ay * bx) / (ax * by))


class Geodesiques:
    """Tension hyperbolique des courbes d'un film (`Film` ou `FilmArcs`) : mêmes noeuds (('v', sommet) aux bouts,
    ('e', u, v, w) sur les arêtes), autres pieds."""

    def __init__(self, film, epsilon=1e-3):
        self.film, self.epsilon = film, epsilon

    def triangle(self, n1, n2):
        """Les trois sommets du triangle qui contient le morceau entre les noeuds n1 et n2."""
        s = ({n1[1]} if n1[0] == 'v' else set(n1[1:3])) | ({n2[1]} if n2[0] == 'v' else set(n2[1:3]))
        assert len(s) == 3, "morceau hors d'un triangle"
        return sorted(s)

    def disque(self, tri):
        cle = tuple(tri)
        pos = self.film.maillage.pos
        return cercle_circonscrit(pos[tri[0]], pos[tri[1]], pos[tri[2]])

    def point(self, noeud, voisin):
        """Position d'un noeud ; une pointe (sommet) est remplacée par un point à distance ε (relative) de la pointe,
        sur la bissectrice du coin du triangle qu'elle forme avec le noeud voisin."""
        m = self.film.maillage
        if noeud[0] == 'e': return m.position(noeud)
        p = m.pos[noeud[1]]
        _, u, v, _ = voisin
        a, b = m.pos[u] - p, m.pos[v] - p
        bis = a / math.hypot(*a) + b / math.hypot(*b)
        echelle = min(math.hypot(*a), math.hypot(*b))
        return p + self.epsilon * echelle * bis / math.hypot(*bis)

    def longueur_locale(self, courbe, i, w):
        """Somme des distances hyperboliques du pied i (à la fraction w) à ses deux voisins."""
        m = self.film.maillage
        n = courbe[i]
        x = (1 - w) * m.pos[n[1]] + w * m.pos[n[2]]
        total = 0.0
        for j in (i - 1, i + 1):
            voisin = courbe[j]
            y = self.point(voisin, n) if voisin[0] == 'v' else m.position(voisin)
            o, R = self.disque(self.triangle(voisin, n))
            total += hilbert(x, y, o, R)
        return total

    def tend(self, tours=30, precision=1e-7):
        """Descente coordonnée par coordonnée : chaque pied minimise (section dorée sur sa fraction) sa longueur locale."""
        or_ = (math.sqrt(5) - 1) / 2
        for _ in range(tours):
            deplacement = 0.0
            for k, courbe in enumerate(self.film.courbes):
                for i in range(1, len(courbe) - 1):
                    n = courbe[i]
                    a, b = 1e-6, 1 - 1e-6
                    c, d = b - or_ * (b - a), a + or_ * (b - a)
                    fc, fd = self.longueur_locale(courbe, i, c), self.longueur_locale(courbe, i, d)
                    while b - a > precision:
                        if fc < fd: b, d, fd = d, c, fc; c = b - or_ * (b - a); fc = self.longueur_locale(courbe, i, c)
                        else: a, c, fc = c, d, fd; d = a + or_ * (b - a); fd = self.longueur_locale(courbe, i, d)
                    w = (a + b) / 2
                    deplacement = max(deplacement, abs(w - n[3]))
                    courbe[i] = ('e', n[1], n[2], w)
            if deplacement < 1e-6: break
        return deplacement

    def ordre_garde(self):
        """Les pieds de deux courbes sur une même arête gardent-ils l'ordre donné ? Renvoie le nombre d'arêtes où
        l'ordre a changé par rapport à `self.ordres` (relevé par `releve_ordres`)."""
        return sum(1 for e, o in self.ordres_actuels().items() if self.ordres.get(e) != o)

    def ordres_actuels(self):
        par_arete = {}
        for k, courbe in enumerate(self.film.courbes):
            for i, n in enumerate(courbe):
                if n[0] == 'e': par_arete.setdefault(n[1:3], []).append((n[3], k, i))
        return {e: [x[1:] for x in sorted(l)] for e, l in par_arete.items()}

    def releve_ordres(self): self.ordres = self.ordres_actuels()

    def polyligne(self, k, poincare=True, n=24):
        """Dessin de la courbe k : dans chaque triangle, la corde entre les pieds (géodésique de Klein), ou l'arc
        orthogonal au cercle circonscrit entre les pieds (géodésique de Poincaré du même disque)."""
        m = self.film.maillage
        courbe = self.film.courbes[k]
        pts = [m.position(x) for x in courbe]
        morceaux = []
        for i in range(len(courbe) - 1):
            p, q = pts[i], pts[i + 1]
            if not poincare:
                morceaux.append(np.array((p, q)))
                continue
            o, R = self.disque(self.triangle(courbe[i], courbe[i + 1]))
            morceaux.append(arc_orthogonal(p, q, o, R, n))
        return np.concatenate([morceaux[0]] + [x[1:] for x in morceaux[1:]])


def arc_orthogonal(p, q, o, R, n=24):
    """Arc de cercle de p à q orthogonal au cercle (o, R) : il passe aussi par l'inverse de p dans ce cercle. Si les
    trois points sont alignés (p, q sur un diamètre), la droite."""
    pp = o + (R * R) * (p - o) / max((p - o) @ (p - o), 1e-12) # inverse de p
    # cercle par p, q, pp
    d = 2 * croix(q - p, pp - p)
    if abs(d) < 1e-9 * max(1.0, (q - p) @ (q - p)): return np.linspace(p, q, n)
    c, r = cercle_circonscrit(p, q, pp)
    a0, a1 = math.atan2(*(p - c)[::-1]), math.atan2(*(q - c)[::-1])
    # le petit arc de p à q (celui qui ne passe pas par pp)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    t = a0 + da * np.linspace(0, 1, n)
    return c + r * np.column_stack((np.cos(t), np.sin(t)))
