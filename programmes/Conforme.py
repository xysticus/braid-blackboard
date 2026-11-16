"""Film des méandres par représentation conforme.

Pendant le demi-tour des trous i et i+1 (A et B), l'axe se plie en ligne brisée : L–A–B–R (L, R : trous voisins,
ou points virtuels au bord de l'image). Cette ligne reste simple de 0 jusqu'à juste avant la fin du demi-tour
(à la fin, L–A passe par B), et les pieds des lacets sur ses segments sont exactement les points de l'image clé k,
dans le même ordre. De même, L–B–A–R porte les points de l'image clé k+1, de juste après le début jusqu'à la fin.

Dessin d'un état sur une ligne brisée : la région au-dessus (et celle au-dessous) est l'image du demi-plan par une
représentation conforme de Schwarz–Christoffel (`Carte`). Chaque arc est l'image d'un demi-cercle du demi-plan entre
les antécédents de ses deux pieds : il part perpendiculairement aux segments, et deux arcs ne se croisent jamais
(la carte est une bijection, deux demi-cercles se croisent ssi leurs extrémités s'entrelacent). Sur l'axe droit,
la carte est une translation : on retrouve exactement les demi-cercles des images clés. Les descentes au clou sont
celles des images clés, faites dans le demi-plan puis transportées.

Première moitié : l'état k sur L–A–B–R ; seconde moitié : l'état k+1 sur L–B–A–R. Autour de la verticale, pendant
une courte fenêtre, on passe de l'un à l'autre. Les cinq segments L–A, A–B, B–R, L–B, A–R ont tous leurs sommets aux
trous : la suite des traversées d'un lacet est la même dans les deux dessins. On mélange les deux dessins morceau
par morceau entre traversées correspondantes (`raccorde`).
"""
import bisect
import math
import operator
import numpy as np

from tresses import (calcule_autofn_de_tresse, etat_de_tresse, dessin_etat, peint, lit_mot, descente_au_clou,
                     melange, en_image_pil, gif_en_mp4)

SENS_DE_SIGMA = 1 # comme dans NouvAutoMorph : σ_i positif = demi-tour horaire à l'écran


class Carte:
    """Représentation conforme de Schwarz–Christoffel du demi-plan supérieur (w) sur la région au-dessus d'une
    ligne brisée (z, y vers le haut) : demi-droite horizontale de -∞ à V_0, segments V_0 ... V_(m-1), demi-droite
    horizontale de V_(m-1) à +∞, V_0 et V_(m-1) à la même hauteur.
    dz/dw = Π (w - w_k)^β_k (β_k = -angle dont tourne le bord en V_k / π), donc z ≈ w + constante loin.
    Morceaux du bord : 0 la demi-droite de gauche (longueur comptée depuis V_0 vers la gauche), p = 1 .. m-1 le
    segment V_(p-1) V_p (depuis V_(p-1)), m la demi-droite de droite (depuis V_(m-1))."""
    N = 300          # points des tables du bord par demi-morceau
    LOIN = 4000.0    # longueur des tables des deux demi-droites (en pixels)

    def __init__(self, sommets, ecarts=None):
        self.V = np.asarray(sommets, dtype=complex)
        cotes = np.diff(self.V)
        self.longueurs = np.abs(cotes)
        self.directions = cotes / self.longueurs
        d = np.concatenate(([1], self.directions, [1]))
        self.beta = -np.angle(d[1:] / d[:-1]) / math.pi
        # antécédents des sommets : on cherche les écarts w_(k+1) - w_k qui donnent les longueurs des segments
        x = np.log(self.longueurs if ecarts is None else ecarts)
        for _ in range(80):
            F = self._cotes(np.exp(x), 120) / self.longueurs - 1
            if np.max(np.abs(F)) < 1e-11: break
            J = np.empty((len(x), len(x)))
            for k in range(len(x)):
                y = x.copy()
                y[k] += 1e-7
                J[:, k] = (self._cotes(np.exp(y), 120) / self.longueurs - 1 - F) / 1e-7
            x = x - np.clip(np.linalg.solve(J, F), -1, 1)
        else:
            raise ValueError("Schwarz–Christoffel : les antécédents des sommets ne convergent pas")
        self.ecarts = np.exp(x)
        self.w = np.concatenate(([0.0], np.cumsum(self.ecarts)))
        self._tables()

    def _module(self, t, w, sauf):
        """|dz/dw| au point réel t, sans le facteur du sommet d'indice sauf."""
        r = np.ones_like(t)
        for j in range(len(w)):
            if j != sauf: r = r * np.abs(t - w[j]) ** self.beta[j]
        return r

    def _depuis(self, w, k, sens, D, N):
        """Table du bord à partir de l'antécédent w_k, dans le sens donné, sur la distance D : (t, longueur cumulée).
        Le changement de variable t = w_k + sens D s^q, q = 1 / (1 + β_k), enlève la singularité en w_k."""
        q = 1 / (1 + self.beta[k])
        s = np.linspace(0, 1, N)
        t = w[k] + sens * D * s ** q
        g = q * D ** (1 + self.beta[k]) * self._module(t, w, k)
        return t, np.concatenate(([0], np.cumsum((g[1:] + g[:-1]) / 2 * np.diff(s))))

    def _cotes(self, ecarts, N):
        w = np.concatenate(([0.0], np.cumsum(ecarts)))
        return np.array([self._depuis(w, k, 1, e / 2, N)[1][-1] + self._depuis(w, k + 1, -1, e / 2, N)[1][-1]
                         for k, e in enumerate(ecarts)])

    def _tables(self):
        w, m, N = self.w, len(self.V), self.N
        self.tables = [self._depuis(w, 0, -1, self.LOIN, 2 * N)]
        for p in range(1, m):
            t1, l1 = self._depuis(w, p - 1, 1, self.ecarts[p - 1] / 2, N)
            t2, l2 = self._depuis(w, p, -1, self.ecarts[p - 1] / 2, N)
            total = l1[-1] + l2[-1]
            l = np.concatenate((l1, (total - l2)[::-1][1:])) * self.longueurs[p - 1] / total
            self.tables.append((np.concatenate((t1, t2[::-1][1:])), l))
        self.tables.append(self._depuis(w, m - 1, 1, self.LOIN, 2 * N))
        # constante de translation : z - w loin à droite
        t, l = self.tables[-1]
        self.delta = self.V[-1].real + l[-1] - t[-1]

    def antecedent_bord(self, morceau, longueur):
        """Antécédent (réel) du point du bord à la longueur donnée sur le morceau."""
        t, l = self.tables[morceau]
        assert 0 <= longueur <= l[-1], "point hors des tables du bord"
        return float(np.interp(longueur, l, t))

    def bord(self, t):
        """Point du bord image du réel t."""
        w, m = self.w, len(self.V)
        if t <= w[0]:
            tt, l = self.tables[0]
            return self.V[0] - np.interp(t, tt[::-1], l[::-1])
        if t >= w[-1]:
            tt, l = self.tables[m]
            return self.V[-1] + np.interp(t, tt, l)
        p = int(np.searchsorted(w, t))
        tt, l = self.tables[p]
        return self.V[p - 1] + np.interp(t, tt, l) * self.directions[p - 1]

    def derivee(self, W):
        W = W.real + 1j * (np.maximum(W.imag, 0) + 0.0) # +0.0 : pas de -0, l'argument d'un réel négatif est π
        r = np.ones_like(W)
        for wk, bk in zip(self.w, self.beta): r = r * (W - wk) ** bk
        return r

    def chemin(self, W, z0, z1=None):
        """Images des points W (un chemin du demi-plan) en intégrant dz/dw depuis z0, image de W[0] ; si l'on connaît
        z1, image de W[-1], l'erreur d'intégration est répartie le long du chemin."""
        W = W[np.concatenate(([True], np.diff(W) != 0))] # points confondus : 0 × ∞ au pied d'une descente
        z = z0 +np.concatenate(([0], np.cumsum(self.derivee((W[1:] + W[:-1]) / 2) * np.diff(W))))
        if z1 is not None:
            lg = np.concatenate(([0], np.cumsum(np.abs(np.diff(z)))))
            if lg[-1] > 0: z = z + (z1 - z[-1]) * lg / lg[-1]
        return z

    def image(self, w):
        """Image d'un point intérieur : on monte verticalement depuis le bord."""
        W = w.real + 1j * np.linspace(0, w.imag, 400) ** 1
        return self.chemin(W, self.bord(w.real))[-1]

    def antecedent(self, z):
        """Antécédent d'un point intérieur (méthode de Newton)."""
        w = complex(z.real - self.delta, max(z.imag, 1.0))
        for _ in range(50):
            e = self.image(w) - z
            if abs(e) < 1e-7: return w
            w = w - e / self.derivee(np.array([w]))[0]
            w = complex(w.real, max(w.imag, 1e-3))
        raise ValueError("antécédent d'un point intérieur : Newton ne converge pas")


def demi_cercle(w0, w1, n=150):
    """Demi-cercle du demi-plan de w0 à w1 (réels), points resserrés aux extrémités."""
    m, rho = (w0 + w1) / 2, abs(w1 - w0) / 2
    phi0 = math.pi if w0 < w1 else 0.0
    phi = phi0 + (math.pi - 2 * phi0) * (1 - np.cos(np.pi * np.linspace(0, 1, n))) / 2
    return m + rho * np.exp(1j * phi)


def lisse(u): return u * u * (3 - 2 * u)


class Lettre:
    """Une lettre σ entre l'image clé k (état cle) et l'image clé k+1 (état suivante).
    Les trous physiques sont numérotés comme dans l'état k ; dans l'état k+1, les indices i-1 et i sont échangés."""

    def __init__(self, cle, suivante, sigma, hauteur=400, largeur=400):
        self.etats = (cle, suivante)
        self.sigma, self.i = sigma, abs(sigma)
        self.hauteur, self.largeur = hauteur, largeur
        self.geos = [dessin_etat(e, hauteur, largeur)[3] for e in self.etats]
        self.H = [[g['X'](x) for x in e[0]] for e, g in zip(self.etats, self.geos)]
        self.n = len(cle[0])
        i = self.i
        self.phys = [list(range(self.n)), list(range(self.n))]
        self.phys[1][i - 1], self.phys[1][i] = i, i - 1
        self.y_axe = self.geos[0]['y_axe']
        self.clou = np.array((largeur / 2, hauteur - 10))
        self.cache = {}
        self.reduction = 1.0

    def melange_geo(self, nom, s): return (1 - s) * self.geos[0][nom] + s * self.geos[1][nom]

    def trou(self, p, s):
        """Position (complexe, y vers le haut, avant aplatissement) du trou physique p ; -1 et n : points virtuels."""
        i, H = self.i, self.H
        if p < 0: return complex(10, 0)
        if p >= self.n: return complex(self.largeur - 10, 0)
        if p not in (i - 1, i):
            return complex((1 - s) * H[0][p] + s * H[1][self.phys[1].index(p)], 0)
        c = (1 - s) * (H[0][i - 1] + H[0][i]) / 2 + s * (H[1][i - 1] + H[1][i]) / 2
        r = (1 - s) * (H[0][i] - H[0][i - 1]) / 2 + s * (H[1][i] - H[1][i - 1]) / 2
        sens = SENS_DE_SIGMA * (1 if self.sigma > 0 else -1)
        theta = math.pi * s
        return c + r * np.exp(1j * ((math.pi - sens * theta) if p == i - 1 else -sens * theta))

    def phys_de(self, e, j):
        return j if j < 0 or j >= self.n else self.phys[e][j]

    def ligne(self, e, s):
        """Sommets de la ligne brisée de l'état e : ses trous i-2, i-1, i, i+1 (ou points virtuels)."""
        return np.array([self.trou(self.phys_de(e, j), s) for j in range(self.i - 2, self.i + 2)])

    def pied(self, e, x, s, V):
        """Pied du point d'abscisse x de l'état e : (morceau, longueur sur le morceau, position)."""
        i, n = self.i, self.n
        trous = self.etats[e][0]
        px = self.geos[e]['X'](x)
        def cle(j): return 10 if j < 0 else self.largeur - 10 if j >= n else self.H[e][j]
        def actuel(j): return self.trou(self.phys_de(e, j), s).real
        q = bisect.bisect(trous, x)
        if i - 1 <= q <= i + 1:
            f = (px - cle(q - 1)) / (cle(q) - cle(q - 1))
            p = q - i + 2
            return p, f * abs(V[p] - V[p - 1]), V[p - 1] + f * (V[p] - V[p - 1])
        if q == 0: xa = actuel(0) - (cle(0) - px)
        elif q == n: xa = actuel(n - 1) + (px - cle(n - 1))
        else:
            f = (px - cle(q - 1)) / (cle(q) - cle(q - 1))
            xa = actuel(q - 1) + f * (actuel(q) - actuel(q - 1))
        if q < i - 1: return 0, V[0].real - xa, complex(xa, 0)
        return 4, xa - V[3].real, complex(xa, 0)

    def cartes(self, e, s):
        V = self.ligne(e, s)
        cartes = []
        for nom, sommets in (('haut', V), ('bas', V.conj())):
            c = Carte(sommets, self.cache.get((e, nom)))
            self.cache[(e, nom)] = c.ecarts
            cartes.append(c)
        return V, cartes

    def dessin(self, e, s):
        """Lacets (polylignes à l'écran) de l'état e dessiné sur sa ligne brisée au temps s."""
        V, (haut, bas) = self.cartes(e, s)
        aplati = self.aplati(s)
        y_axe = self.y_axe
        def ecran(Z, en_haut):
            return np.column_stack((Z.real, y_axe - Z.imag * aplati if en_haut else y_axe + Z.imag * aplati))
        lacets = self.etats[e][1]
        pieds = [[self.pied(e, x, s, V) for x in lacet] for lacet in lacets]
        wh = [[haut.antecedent_bord(p, l) for p, l, _ in pl] for pl in pieds]
        wb = [[bas.antecedent_bord(p, l) for p, l, _ in pl] for pl in pieds]
        zc = complex(self.clou[0], (self.clou[1] - y_axe) / aplati)
        wc = bas.antecedent(zc)
        assert all(abs(wc - (w[j] + w[j + 1]) / 2) > abs(w[j + 1] - w[j]) / 2 for w in wb for j in range(1, len(w) - 1, 2)), \
               "le clou est hors des demi-cercles du bas"
        def descente(w, z):
            """Du pied (antécédent w, image z dans la carte du bas) au clou : la géodésique du demi-plan, arc du cercle
            orthogonal à l'axe qui passe par w et par l'antécédent du clou. Deux de ces cercles ne se recoupent qu'au
            clou (et en son symétrique) ; un demi-cercle du bas qui ne sépare ni le pied ni le clou de l'infini ne les
            sépare pas l'un de l'autre, donc la descente ne le croise pas."""
            a, b = wc.real, wc.imag
            if abs(a - w) < 1e-9 * (1 + abs(b)):
                W = w + 1j * b * (1 - np.cos(np.pi * np.linspace(0, 1, 200) / 2))
            else:
                m = (a * a + b * b - w * w) / (2 * (a - w))
                rho = abs(w - m)
                phi0 = 0.0 if w > m else math.pi
                phi1 = math.atan2(b, a - m)
                u = 1 - np.cos(np.pi * np.linspace(0, 1, 200) / 2) # points resserrés au pied
                W = m + rho * np.exp(1j * (phi0 + (phi1 - phi0) * u))
            return ecran(bas.chemin(W, z, zc), False)
        lignes = []
        for pl, h_, b_ in zip(pieds, wh, wb):
            m = [descente(b_[0], pl[0][2].conjugate())[::-1]]
            for j in range(len(pl) - 1):
                if j % 2 == 0:
                    m.append(ecran(haut.chemin(demi_cercle(h_[j], h_[j + 1]), pl[j][2], pl[j + 1][2]), True))
                else:
                    m.append(ecran(bas.chemin(demi_cercle(b_[j], b_[j + 1]), pl[j][2].conjugate(),
                                              pl[j + 1][2].conjugate()), False))
            m.append(descente(b_[-1], pl[-1][2].conjugate()))
            lignes.append(np.concatenate(m))
        return lignes

    def aplati(self, s):
        """Aplatissement vertical : celui des images clés, mélangé, réduit par self.reduction (fixé image par image
        par le film quand le demi-tour fait sortir les arcs du cadre)."""
        return self.melange_geo('aplati', s) * self.reduction

    def ecran(self, z, s):
        aplati = self.aplati(s)
        return np.array((z.real, self.y_axe - z.imag * aplati))

    def aretes(self, s):
        """Arêtes à l'écran : morceaux de l'axe hors du bloc, puis L–A, A–B, B–R, L–B, A–R (trous physiques)."""
        i, n = self.i, self.n
        def T(p): return self.ecran(self.trou(p, s), s)
        L, A, B, R = T(i - 2), T(i - 1), T(i), T(i + 1)
        gauche = [np.array((-1e4, self.y_axe))] + [T(p) for p in range(0, i - 1)]
        if i - 2 < 0: gauche.append(L)
        droite = [T(p) for p in range(i + 1, n)] + ([R] if i + 1 >= n else []) + [np.array((1e4, self.y_axe))]
        axe = [(p, q) for p, q in zip(gauche[:-1], gauche[1:])] + [(p, q) for p, q in zip(droite[:-1], droite[1:])]
        return axe, [(L, A), (A, B), (B, R), (L, B), (A, R)]

    def trous_ecran(self, s):
        return np.array([self.ecran(self.trou(p, s), s) for p in range(self.n)])


def traversees(points, aretes):
    """Traversées des arêtes par la polyligne : liste triée de (position le long de la polyligne, arête, point)."""
    P0, D = points[:-1], np.diff(points, axis=0)
    res = []
    for a, (E0, E1) in enumerate(aretes):
        F = E1 - E0
        Q = E0 - P0
        den = D[:, 0] * F[1] - D[:, 1] * F[0]
        with np.errstate(divide='ignore', invalid='ignore'):
            t = (Q[:, 0] * F[1] - Q[:, 1] * F[0]) / den
            u = (Q[:, 0] * D[:, 1] - Q[:, 1] * D[:, 0]) / den
        ok = (den != 0) & (t >= -1e-9) & (t < 1 - 1e-9) & (u >= -1e-9) & (u <= 1 + 1e-9)
        for k in np.nonzero(ok)[0]:
            res.append((k + max(t[k], 0), a, P0[k] + t[k] * D[k]))
    res.sort(key=lambda r: r[0])
    # un pied posé sur une arête peut être vu deux fois (fin d'un segment, début du suivant)
    propre = []
    for r in res:
        if propre and propre[-1][1] == r[1] and np.hypot(*(propre[-1][2] - r[2])) < 1e-6: continue
        propre.append(r)
    return propre

def sans_bigones(trav):
    """Annule les traversées successives d'une même arête : entre elles, le lacet et l'arête bordent un bigone vide
    (les sommets des arêtes sont des trous). Reste la suite minimale, la même pour deux dessins du même lacet."""
    pile = []
    for r in trav:
        if pile and pile[-1][1] == r[1]: pile.pop()
        else: pile.append(r)
    return pile

def decoupe(points, trav):
    """Morceaux de la polyligne entre traversées successives."""
    morceaux, avant, p_avant = [], 0.0, points[0]
    for pos, _, p in trav + [(len(points) - 1.0, None, points[-1])]:
        interieurs = [points[v] for v in range(math.floor(avant) + 1, math.ceil(pos)) if avant < v < pos]
        morceaux.append(np.array([p_avant] + interieurs + [p]))
        avant, p_avant = pos, p
    return morceaux

def raccorde(depart, arrivee, aretes, poids):
    """Mélange de deux dessins du même lacet, morceau par morceau entre traversées correspondantes des arêtes ;
    None si les suites de traversées diffèrent."""
    td, ta = sans_bigones(traversees(depart, aretes)), sans_bigones(traversees(arrivee, aretes))
    if [a for _, a, _ in td] != [a for _, a, _ in ta]: return None
    return np.concatenate([melange(p, q, poids) for p, q in zip(decoupe(depart, td), decoupe(arrivee, ta))])


def nb_croisements(lignes, clou, rayon=12):
    """Nombre de croisements entre lacets distincts (hors du voisinage du clou, où ils se rejoignent)."""
    segs = []
    for p in lignes:
        loin = (np.hypot(*(p[:-1] - clou).T) > rayon) & (np.hypot(*(p[1:] - clou).T) > rayon)
        segs.append((p[:-1][loin], p[1:][loin]))
    # paquets de segments avec leur rectangle englobant : on ne compare que les paquets qui se chevauchent
    paquets = []
    for l, (P0, P1) in enumerate(segs):
        for k in range(0, len(P0), 64):
            p0, p1 = P0[k:k + 64], P1[k:k + 64]
            pts = np.concatenate((p0, p1))
            paquets.append((l, p0, p1, pts.min(axis=0), pts.max(axis=0)))
    total = 0
    for x in range(len(paquets)):
        la, P0, P1, mina, maxa = paquets[x]
        for y in range(x + 1, len(paquets)):
            lb, Q0, Q1, minb, maxb = paquets[y]
            if la == lb or (mina > maxb).any() or (minb > maxa).any(): continue
            d, p0, F = (P1 - P0)[:, None, :], P0[:, None, :], Q1 - Q0
            Q = Q0[None, :, :] - p0
            den = d[..., 0] * F[None, :, 1] - d[..., 1] * F[None, :, 0]
            with np.errstate(divide='ignore', invalid='ignore'):
                t = (Q[..., 0] * F[None, :, 1] - Q[..., 1] * F[None, :, 0]) / den
                u = (Q[..., 0] * d[..., 1] - Q[..., 1] * d[..., 0]) / den
            total += int(np.count_nonzero((den != 0) & (t >= 0) & (t < 1) & (u >= 0) & (u < 1)))
    return total


def film_conforme(tresse, fichier, duree=40, pause=500, hauteur=400, largeur=400, images=48, fenetre=0.3,
                  verifie=False, **options):
    """GIF animé (puis MP4) : pour chaque lettre, l'état k sur L–A–B–R, puis l'état k+1 sur L–B–A–R, raccordés
    autour de la verticale pendant la fenêtre (part du mouvement). verifie : relit les mots et compte les croisements
    entre lacets sur chaque image (lent) ; renvoie la liste des anomalies."""
    nb_trous = max(map(operator.abs, tresse), default=5) + 1
    cle = etat_de_tresse([], nb_trous)
    # première image : l'image clé, dessinée elle aussi par la carte (descentes en géodésiques)
    premiere = Lettre(cle, etat_de_tresse(tresse[:1], nb_trous), tresse[0], hauteur, largeur)
    axe, _ = premiere.aretes(0)
    dessins = [(premiere.dessin(0, 0.0), premiere.trous_ecran(0), premiere.clou,
                [np.array(a) for a in axe] + [np.array(a) for a in premiere.aretes(0)[1][:3]])]
    durees = [pause]
    anomalies = []
    for k, sigma in enumerate(tresse):
        suivante = etat_de_tresse(tresse[:k + 1], nb_trous)
        lettre = Lettre(cle, suivante, sigma, hauteur, largeur)
        mots = [calcule_autofn_de_tresse(tresse[:k + j], nb_trous) for j in (0, 1)]
        for n in range(1, images + 1):
            s = lisse(n / images)
            poids = lisse(min(1, max(0, (s - (0.5 - fenetre / 2)) / fenetre)))
            def dessins_de_s():
                return [lettre.dessin(e, s) if p > 0 else None for e, p in ((0, 1 - poids), (1, poids))]
            # si les arcs sortent par le haut, on aplatit davantage (les dessins dans le demi-plan n'en dépendent
            # pas, sauf la place du clou) : continu, et sans effet aux images clés, qui tiennent dans le cadre
            lettre.reduction = 1.0
            essais = dessins_de_s()
            y_min = min(l[:, 1].min() for d in essais if d is not None for l in d)
            if y_min < 10:
                lettre.reduction = (lettre.y_axe - 10) / (lettre.y_axe - y_min)
                essais = dessins_de_s()
            axe, (LA, AB, BR, LB, AR) = lettre.aretes(s)
            if poids == 0: lignes = essais[0]
            elif poids == 1: lignes = essais[1]
            else:
                dep, arr = essais
                lignes = []
                for l, (p, q) in enumerate(zip(dep, arr)):
                    r = raccorde(p, q, axe + [LA, AB, BR, LB, AR], poids)
                    if r is None:
                        anomalies.append((k, n, l, 'traversées différentes'))
                        r = p if poids < 0.5 else q
                    lignes.append(r)
            trous = lettre.trous_ecran(s)
            if verifie:
                en_ordre = sorted(trous.tolist())
                if abs(trous[lettre.i - 1][0] - trous[lettre.i][0]) > 1e-6 and \
                   [lit_mot(p, en_ordre) for p in lignes] not in mots:
                    anomalies.append((k, n, None, 'mots'))
                nb = nb_croisements(lignes, lettre.clou)
                if nb: anomalies.append((k, n, nb, 'croisements'))
            dessin_axe = [np.array(a) for a in axe] + [np.array(AB)] \
                         + [(np.array(a), 1 - poids) for a in (LA, BR)] + [(np.array(a), poids) for a in (LB, AR)]
            dessins.append((lignes, trous, lettre.clou, dessin_axe))
            durees.append(duree)
        cle = suivante
        durees[-1] = pause
    durees[-1] = 3 * pause
    images_pil = [en_image_pil(peint(m, t, c, hauteur, largeur, axe=a, **options)) for m, t, c, a in dessins]
    images_pil[0].save(fichier, save_all=True, append_images=images_pil[1:], duration=durees, loop=0)
    return anomalies


if __name__ == "__main__":
    # depuis la racine du dépôt
    anomalies = film_conforme([4, 3, -1, -1, 2, -4, 1], './imgs/film_conforme_43m1m12m41.gif', largeur_brin=3,
                              verifie=True)
    print(len(anomalies), "anomalies :", anomalies[:20])
    gif_en_mp4('./imgs/film_conforme_43m1m12m41.gif')
