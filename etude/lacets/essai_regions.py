"""Essai (document de travail) : le raccord de la lettre à la verticale, par régions et sans maillage.

À la verticale (s = 0,5), A–B est vertical et les cinq segments L–A, A–B, B–R, L–B, A–R ont tous leurs sommets aux trous.
Le plan est coupé en quatre régions : le haut (au-dessus de L–T–R, T étant celui de A et B qui est en haut), le bas
(au-dessous de L–Bas–R, avec le clou) et les deux triangles L–Bas–T et R–T–Bas. Chaque lacet est la suite de ses
traversées des arêtes ; entre deux traversées, son morceau est dans une seule région, où l'on le dessine comme l'image
d'un demi-cercle par la représentation conforme de la région (Schwarz–Christoffel : `Carte` pour le haut et le bas,
un triangle pour les deux triangles).

Les pieds (la place des traversées sur les arêtes) sont la moyenne des fractions des deux dessins conformes de la
verticale (l'état k sur L–A–B–R, l'état k+1 sur L–B–A–R), dont les suites minimales de traversées sont les mêmes.

Depuis la racine du dépôt :   python etude/lacets/essai_regions.py [mot] [numéro de lettre]
écrit imgs/essai_regions_*.png (non suivi par git) : à gauche le maillage actuel à la même image, à droite les régions.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
import subprocess  # noqa: E402
from Conforme import (Carte, Lettre, demi_cercle, traversees, sans_bigones, nb_croisements, dessins_conforme,  # noqa: E402
                      surface_conforme, raccorde, lisse)
from tresses import etat_de_tresse, en_image_pil, calcule_autofn_de_tresse, lit_mot, ENCODEUR  # noqa: E402

# ---------------------------------------------------------------- le triangle : le demi-plan sur un triangle

_X, _P = np.polynomial.legendre.leggauss(80)


def _integrale(haut, p, q):
    """∫_0^haut (1 − s^(1/p))^(q−1) ds / p : la partie de B(x; p, q) quand x ≤ 1/2, avec haut = x^p (changement de
    variable t = s^(1/p), qui enlève la singularité en 0)."""
    if haut <= 0: return 0.0
    # on coupe en morceaux géométriques : près de 0, s^(1/p) n'est pas lisse
    bornes = [0.0] + [haut * 2.0 ** (-k) for k in range(12, 0, -1)] + [haut]
    total = 0.0
    for a, b in zip(bornes[:-1], bornes[1:]):
        s = (b - a) / 2 * _X + (b + a) / 2
        total += (b - a) / 2 * np.sum(_P * (1 - s ** (1 / p)) ** (q - 1))
    return total / p


def beta_incomplete(a, b, x):
    """B(x; a, b) = ∫_0^x t^(a−1) (1−t)^(b−1) dt, pour 0 ≤ x ≤ 1."""
    complet = math.gamma(a) * math.gamma(b) / math.gamma(a + b)
    if x <= 0.5: return _integrale(x ** a, a, b)
    return complet - _integrale((1 - x) ** b, b, a)


TABLE = 1500   # nœuds de la table de B(x; a, b)


class TableBeta:
    """Fraction de B(x; a, b) / B(1; a, b) et son inverse (par une table dense en x)."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.complet = math.gamma(a) * math.gamma(b) / math.gamma(a + b)
        u = np.linspace(0, 1, TABLE)
        self.x = (1 - np.cos(np.pi * u)) / 2
        self.f = np.array([beta_incomplete(a, b, x) for x in self.x]) / self.complet

    def inverse(self, fraction):
        """x tel que B(x; a, b) / B(1; a, b) = fraction. La table donne un départ, mais près de 0 ou de 1 elle est trop
        grossière (x vaut f^(1/a), avec 1/a grand dans un angle aigu) : on résout exactement, par la méthode de Newton
        en t = x^a (ou s = (1−x)^b), où la fonction est presque linéaire, gardée par une dichotomie."""
        a, b, C = self.a, self.b, self.complet
        cible = fraction * C
        if cible <= beta_incomplete(a, b, 0.5):
            t = _resous(a, b, cible, 0.5 ** a)
            return t ** (1 / a)
        s = _resous(b, a, C - cible, 0.5 ** b)
        return 1 - s ** (1 / b)


def _resous(p, q, cible, borne):
    """t dans [0, borne] tel que _integrale(t, p, q) = cible (fonction croissante, de dérivée (1 − t^(1/p))^(q−1) / p)."""
    bas, haut = 0.0, borne
    t = min(max(cible * p, 1e-300), borne)   # B(x) ≈ x^p / p près de 0
    for _ in range(60):
        e = _integrale(t, p, q) - cible
        if e > 0: haut = t
        else: bas = t
        d = (1 - t ** (1 / p)) ** (q - 1) / p
        suivant = t - e / d if d > 0 else (bas + haut) / 2
        if not (bas < suivant < haut): suivant = (bas + haut) / 2
        if abs(suivant - t) <= 1e-13 * t: return suivant
        t = suivant
    return t


class Triangle:
    """Le demi-plan sur le triangle P0 P1 P2 (sens direct) : f'(w) = K w^(a−1) (1−w)^(b−1), les sommets étant les
    images de 0, 1 et ∞, a, b, c = α0/π, α1/π, α2/π les angles. Côtés : P0P1 ↔ [0, 1] ; P1P2 ↔ [1, ∞[ ;
    P2P0 ↔ ]−∞, 0]."""

    def __init__(self, P0, P1, P2):
        self.P = (P0, P1, P2)
        def angle(u, v, w):  # angle en u entre uv et uw
            return abs(math.atan2(((v - u).conjugate() * (w - u)).imag, ((v - u).conjugate() * (w - u)).real))
        self.a, self.b, self.c = (angle(P0, P1, P2) / math.pi, angle(P1, P2, P0) / math.pi, angle(P2, P0, P1) / math.pi)
        self.K = (P1 - P0) / (math.gamma(self.a) * math.gamma(self.b) / math.gamma(self.a + self.b))
        self.t_ab = TableBeta(self.a, self.b)
        self.t_cb = TableBeta(self.c, self.b)
        self.t_ac = TableBeta(self.a, self.c)

    def antecedent_bord(self, cote, fraction):
        """Antécédent réel du point du côté (0 : P0→P1, 1 : P1→P2, 2 : P2→P0) à cette fraction de sa longueur."""
        fraction = min(max(fraction, 1e-9), 1 - 1e-9)
        if cote == 0: return self.t_ab.inverse(fraction)
        if cote == 1: return 1 / max(self.t_cb.inverse(1 - fraction), 1e-12)
        u = self.t_ac.inverse(1 - fraction)
        return -u / max(1 - u, 1e-12)

    def position_bord(self, cote, fraction):
        P0, P1, P2 = self.P
        Q0, Q1 = ((P0, P1), (P1, P2), (P2, P0))[cote]
        return Q0 + fraction * (Q1 - Q0)

    def derivee(self, W):
        W = W.real + 1j * np.maximum(W.imag, 0.0)
        return self.K * W ** (self.a - 1) * (1 - W) ** (self.b - 1)

    def chemin(self, W, z0, z1):
        W = W[np.concatenate(([True], np.diff(W) != 0))]
        z = z0 + np.concatenate(([0], np.cumsum(self.derivee((W[1:] + W[:-1]) / 2) * np.diff(W))))
        lg = np.concatenate(([0], np.cumsum(np.abs(np.diff(z)))))
        if lg[-1] > 0: z = z + (z1 - z[-1]) * lg / lg[-1]
        return z


FINESSE = 0.05   # distance du premier point du demi-cercle, en part de la distance du pied au sommet le plus proche
POINTS = 240


def demi_cercle_fin(w0, w1, sommets=(), derivee=None, n=None):
    """Comme `demi_cercle`, mais les points sont resserrés géométriquement vers chaque bout, jusqu'à une distance de
    l'ordre du vingtième de celle du bout au sommet de la région le plus proche (`sommets` : leurs antécédents) : un pied
    près d'un sommet fait tourner l'image en spirale, et des points resserrés seulement en cosinus laissent des
    croisements numériques entre deux arcs voisins. On ne descend pas plus bas que nécessaire : des segments minuscules
    posés sur une arête échappent à la détection des traversées (`traversees`)."""
    n = n or POINTS
    m, rho = (w0 + w1) / 2, abs(w1 - w0) / 2
    def t_min(e):
        d = min([abs(e - v) for v in sommets] + [0.05 * abs(e)], default=rho)   # + le sommet à l'infini (triangles)
        t = max(FINESSE * d / (math.pi * rho), 1e-10)
        if derivee is not None:   # le premier segment de l'image doit rester assez long (0,05 pixel) pour qu'on y voie la traversée
            t = max(t, 0.05 / (max(abs(derivee(np.array([e + 0j]))[0]), 1e-300) * math.pi * rho))
        return min(t, 0.02)
    def moitie(e):
        return 0.5 * np.geomspace(t_min(e) * 2, 1, n // 2)
    h0, h1 = moitie(w0), moitie(w1)
    u = np.concatenate(([0.0], h0 / 1, 1 - h1[::-1][1:], [1.0]))
    u = np.unique(u)
    phi0 = math.pi if w0 < w1 else 0.0
    return m + rho * np.exp(1j * (phi0 + (math.pi - 2 * phi0) * u))


# ---------------------------------------------------------------- les régions

# les deux régions voisines de chaque sorte d'arête
REGIONS = {'G': ('H', 'B'), 'D': ('H', 'B'), 'LT': ('H', 'T1'), 'TR': ('H', 'T2'), 'LB': ('B', 'T1'), 'BR': ('B', 'T2'),
           'TB': ('T1', 'T2')}


def dessins_de_verticale(L, s):
    """Les deux dessins conformes de la verticale (l'état k et l'état k+1), avec la réduction du film à cette image."""
    L.reduction = 1.0
    d = [L.dessin(e, s) for e in (0, 1)]
    y_min = min(l[:, 1].min() for x in d for l in x)
    if y_min < 10:
        L.reduction = (L.y_axe - 10) / (L.y_axe - y_min)
        d = [L.dessin(e, s) for e in (0, 1)]
    return d


def sortes_d_aretes(L, s):
    """Pour chaque arête de `L.aretes(s)` (les morceaux de l'axe, puis L–A, A–B, B–R, L–B, A–R) : (sorte, sens, E0, E1) ;
    sens = -1 si l'arête est parcourue de l'autre bout que celui de la sorte (T→Bas pour A–B quand A est en bas)."""
    axe, (LA, AB, BR, LB, AR) = L.aretes(s)
    L_, A_, B_, R_ = L.ligne(0, s)
    a_en_haut = A_.imag > B_.imag
    res = [('G' if (p[0] + q[0]) / 2 < L_.real else 'D', 1, p, q) for p, q in axe]
    if a_en_haut:   # A = T, B = Bas
        res += [('LT', 1, *LA), ('TB', 1, *AB), ('BR', 1, *BR), ('LB', 1, *LB), ('TR', 1, *AR)]
    else:           # A = Bas, B = T
        res += [('LB', 1, *LA), ('TB', -1, *AB), ('TR', 1, *BR), ('LT', 1, *LB), ('BR', 1, *AR)]
    return res, (L_, A_, B_, R_), a_en_haut


def fractions(L, s, dessin):
    """Les pieds minimaux de chaque lacet d'un dessin conforme de l'instant s : une liste de (arête, fraction de l'arête,
    de E0 vers E1) par lacet. La fraction est invariante par l'aplatissement vertical et suit l'arête quand elle bouge."""
    sortes = sortes_d_aretes(L, s)[0]
    aretes_ecran = [(p, q) for _, _, p, q in sortes]
    res = []
    for lacet in dessin:
        suite = []
        for _, a, P in sans_bigones(traversees(lacet, aretes_ecran))[0]:
            _, _, E0, E1 = sortes[a]
            suite.append((a, float(np.dot(P - E0, E1 - E0) / np.dot(E1 - E0, E1 - E0))))
        res.append(suite)
    return res


def mele(fa, fb, w):
    """Les fractions mélangées (1 − w) fa + w fb, lacet par lacet ; None pour un lacet dont les suites d'arêtes diffèrent."""
    res = []
    for pa, pb in zip(fa, fb):
        if [a for a, _ in pa] != [a for a, _ in pb]: res.append(None)
        else: res.append([(a, (1 - w) * ua + w * ub) for (a, ua), (_, ub) in zip(pa, pb)])
    return res


MORCEAUX = []   # pour le diagnostic : les morceaux de chaque lacet (région, pieds, nombre de points)


def par_regions(L, s, pieds_des_lacets, repli):
    """Les lacets de la lettre à l'instant s, dessinés par régions. pieds_des_lacets : pour chaque lacet, la suite de ses
    traversées (arête de `L.aretes(s)`, fraction), ou None ; repli : les lacets à rendre tels quels dans ce cas, ou si
    la suite est incohérente. Rend (lignes, erreurs)."""
    sortes, (L_, A_, B_, R_), a_en_haut = sortes_d_aretes(L, s)
    T, Bas = (A_, B_) if a_en_haut else (B_, A_)
    aplati, y_axe = L.aplati(s), L.y_axe

    # y vers le haut, avant aplatissement : les sommets des régions
    carte_h = Carte(np.array([L_, T, R_]))
    carte_b = Carte(np.array([L_, Bas, R_]).conj())
    tri = {'T1': Triangle(L_, Bas, T), 'T2': Triangle(R_, T, Bas)}

    def ecran(Z, haut):
        return np.column_stack((Z.real, y_axe - Z.imag * aplati if haut else y_axe + Z.imag * aplati))

    def parametre(a, u):
        """Le paramètre du pied sur l'arête a : l'abscisse sur l'axe, sinon la fraction dans le sens de la sorte."""
        sorte, sens, E0, E1 = sortes[a]
        if sorte in ('G', 'D'): return E0[0] + u * (E1[0] - E0[0])
        return u if sens == 1 else 1 - u

    # un pied : (sorte, paramètre) ; G, D : abscisse ; sinon fraction de l'arête dans le sens de la sorte
    def pied_en(region, sorte, p):
        """(côté de la région, longueur ou fraction, position y-up complexe) du pied dans cette région."""
        if region == 'H':
            if sorte == 'G': return 0, L_.real - p, complex(p, 0)
            if sorte == 'D': return 3, p - R_.real, complex(p, 0)
            if sorte == 'LT': return 1, p * abs(T - L_), L_ + p * (T - L_)
            if sorte == 'TR': return 2, p * abs(R_ - T), T + p * (R_ - T)
        if region == 'B':
            if sorte == 'G': return 0, L_.real - p, complex(p, 0)
            if sorte == 'D': return 3, p - R_.real, complex(p, 0)
            if sorte == 'LB': return 1, p * abs(Bas - L_), L_ + p * (Bas - L_)
            if sorte == 'BR': return 2, p * abs(R_ - Bas), Bas + p * (R_ - Bas)
        if region == 'T1':   # L → Bas → T
            if sorte == 'LB': return 0, p, L_ + p * (Bas - L_)
            if sorte == 'TB': return 1, 1 - p, T + p * (Bas - T)
            if sorte == 'LT': return 2, 1 - p, L_ + p * (T - L_)
        if region == 'T2':   # R → T → Bas
            if sorte == 'TR': return 0, 1 - p, T + p * (R_ - T)
            if sorte == 'TB': return 1, p, T + p * (Bas - T)
            if sorte == 'BR': return 2, p, Bas + p * (R_ - Bas)
        raise ValueError(f"pas de pied {sorte} dans {region}")

    zc = complex(L.clou[0], (L.clou[1] - y_axe) / aplati)
    wc = carte_b.antecedent(zc)

    def descente(w, z):
        a, b = wc.real, wc.imag
        if abs(a - w) < 1e-9 * (1 + abs(b)):
            W = w + 1j * b * (1 - np.cos(np.pi * np.linspace(0, 1, 200) / 2))
        else:
            m = (a * a + b * b - w * w) / (2 * (a - w))
            rho = abs(w - m)
            phi0 = 0.0 if w > m else math.pi
            phi1 = math.atan2(b, a - m)
            u = 1 - np.cos(np.pi * np.linspace(0, 1, 200) / 2)
            W = m + rho * np.exp(1j * (phi0 + (phi1 - phi0) * u))
        return ecran(carte_b.chemin(W, z, zc), False)

    def w_du_pied(region, cote, x):
        if region == 'H': return carte_h.antecedent_bord(cote, x)
        if region == 'B': return carte_b.antecedent_bord(cote, x)
        return tri[region].antecedent_bord(cote, x)

    lignes, erreurs = [], []
    del MORCEAUX[:]
    for l, suite in enumerate(pieds_des_lacets):
        if suite is None:
            erreurs.append((l, 'traversées différentes'))
            lignes.append(repli[l])
            continue
        pieds = [(sortes[a][0], parametre(a, u)) for a, u in suite]
        # le parcours des régions : on part du clou, dans le bas
        region = 'B'
        morceaux = []
        for j, (sorte, p) in enumerate(pieds):
            if region not in REGIONS[sorte]:
                erreurs.append((l, f"traversée {j} ({sorte}) hors de la région {region}"))
                break
            suivante = REGIONS[sorte][1 - REGIONS[sorte].index(region)]
            morceaux.append((region, suivante))
            region = suivante
        else:
            if region != 'B':
                erreurs.append((l, f"le lacet finit dans la région {region}"))
        if erreurs and erreurs[-1][0] == l:
            lignes.append(repli[l])
            continue
        # le dessin : descente, morceaux, descente
        pb0 = pied_en('B', *pieds[0])
        morceau0 = descente(w_du_pied('B', pb0[0], pb0[1]), pb0[2].conjugate())[::-1]
        parties = [morceau0]
        for j in range(len(pieds) - 1):
            reg = morceaux[j][1]   # la région où l'on entre après la traversée j
            c0, x0, z0 = pied_en(reg, *pieds[j])
            c1, x1, z1 = pied_en(reg, *pieds[j + 1])
            w0, w1 = w_du_pied(reg, c0, x0), w_du_pied(reg, c1, x1)
            ws, dv = (carte_h.w, carte_h.derivee) if reg == 'H' else (carte_b.w, carte_b.derivee) if reg == 'B' else ((0.0, 1.0), tri[reg].derivee)
            if reg == 'H':
                parties.append(ecran(carte_h.chemin(demi_cercle_fin(w0, w1, ws, dv), z0, z1), True))
            elif reg == 'B':
                parties.append(ecran(carte_b.chemin(demi_cercle_fin(w0, w1, ws, dv), z0.conjugate(), z1.conjugate()), False))
            else:
                parties.append(ecran(tri[reg].chemin(demi_cercle_fin(w0, w1, ws, dv), z0, z1), True))
        pbn = pied_en('B', *pieds[-1])
        parties.append(descente(w_du_pied('B', pbn[0], pbn[1]), pbn[2].conjugate()))
        lignes.append(np.concatenate(parties))
        MORCEAUX.append([(('descente',), len(morceau0))] + [((morceaux[j][1], pieds[j], pieds[j + 1]), len(parties[j + 1])) for j in range(len(pieds) - 1)] + [(('descente',), len(parties[-1]))])
    return lignes, erreurs


# ---------------------------------------------------------------- le film

def dessins_regions(tresse, images=48, fenetre=0.7, rampe=0.25, hauteur=800, largeur=800, marge=60, duree=40, pause=500):
    """Comme `dessins_conforme`, mais le raccord se fait par régions, sans maillage : hors de la fenêtre (poids 0 ou 1),
    le dessin conforme de l'état k (sur L–A–B–R) ou de l'état k+1 (sur L–B–A–R) ; dedans, le dessin par régions, dont les
    pieds passent des fractions du premier dessin à celles du second. Aux deux bouts de la fenêtre, une rampe (une part
    `rampe` du poids) mélange morceau par morceau (`raccorde`) le dessin conforme et celui des régions, qui ont alors
    les mêmes pieds. Rend (dessins, durées, anomalies) comme `dessins_conforme`."""
    nb = max(map(abs, tresse)) + 1
    h_int, l_int = hauteur - 2 * marge, largeur - 2 * marge
    cle = etat_de_tresse([], nb)
    premiere = Lettre(cle, etat_de_tresse(tresse[:1], nb), tresse[0], h_int, l_int)
    axe, _ = premiere.aretes(0)
    dessins = [(premiere.dessin(0, 0.0), premiere.trous_ecran(0), premiere.clou,
                [np.array(a) for a in axe] + [np.array(a) for a in premiere.aretes(0)[1][:3]])]
    durees, anomalies = [pause], []
    for k, sigma in enumerate(tresse):
        suivante = etat_de_tresse(tresse[:k + 1], nb)
        lettre = Lettre(cle, suivante, sigma, h_int, l_int)
        mots = [calcule_autofn_de_tresse(tresse[:k + j], nb) for j in (0, 1)]
        temps = [lisse(n / images) for n in range(images + 1)]
        poids_de = [lisse(min(1, max(0, (t - (0.5 - fenetre / 2)) / fenetre))) for t in temps]
        dans = [n for n in range(1, images + 1) if 0 < poids_de[n] < 1]
        # les pieds du départ (figé à la dernière image avant la fenêtre) et de l'arrivée (figée à la première après) :
        # les deux dessins conformes ne sont corrects que près de leur bout du demi-tour (loin de lui, la ligne brisée
        # se pince et le dessin croise), alors que la fraction d'un pied sur son arête suit l'arête quand elle bouge
        lettre.reduction = 1.0
        n_a, n_b = dans[0] - 1, dans[-1] + 1
        frac_a = fractions(lettre, temps[n_a], lettre.dessin(0, temps[n_a]))
        frac_b = fractions(lettre, temps[n_b], lettre.dessin(1, temps[n_b]))
        for n in range(1, images + 1):
            s, poids = temps[n], poids_de[n]
            g = lisse(min(1, poids / rampe, (1 - poids) / rampe)) if 0 < poids < 1 else 0.0

            def calcule():
                axe, (LA, AB, BR, LB, AR) = lettre.aretes(s)
                if poids == 0: return lettre.dessin(0, s), axe, (LA, AB, BR, LB, AR)
                if poids == 1: return lettre.dessin(1, s), axe, (LA, AB, BR, LB, AR)
                autre = lettre.dessin(0, s) if poids < 0.5 else lettre.dessin(1, s)   # le seul qui soit correct à cet instant
                reg, erreurs = par_regions(lettre, s, mele(frac_a, frac_b, poids), autre)
                for l, e in erreurs: anomalies.append((k, n, l, e))
                if g >= 1: return reg, axe, (LA, AB, BR, LB, AR)
                res = []
                for l, (p, q) in enumerate(zip(autre, reg)):
                    r = raccorde(p, q, axe + [LA, AB, BR, LB, AR], g)
                    if r is None:
                        anomalies.append((k, n, l, 'rampe : traversées différentes'))
                        r = p if g < 0.5 else q
                    res.append(r)
                return res, axe, (LA, AB, BR, LB, AR)

            lettre.reduction = 1.0
            lignes, axe, (LA, AB, BR, LB, AR) = calcule()
            y_min = min(l[:, 1].min() for l in lignes)
            if y_min < 10:
                lettre.reduction = (lettre.y_axe - 10) / (lettre.y_axe - y_min)
                lignes, axe, (LA, AB, BR, LB, AR) = calcule()
            trous = lettre.trous_ecran(s)
            en_ordre = sorted(trous.tolist())
            if abs(trous[lettre.i - 1][0] - trous[lettre.i][0]) > 1e-6 and [lit_mot(p, en_ordre) for p in lignes] not in mots:
                anomalies.append((k, n, None, 'mots'))
            nbc = nb_croisements(lignes, lettre.clou)
            if nbc: anomalies.append((k, n, nbc, 'croisements'))
            dessin_axe = [np.array(a) for a in axe] + [np.array(AB)] \
                         + [(np.array(a), 1 - poids) for a in (LA, BR)] + [(np.array(a), poids) for a in (LB, AR)]
            dessins.append((lignes, trous, lettre.clou, dessin_axe))
            durees.append(duree)
        cle = suivante
    durees[-1] = 3 * pause
    return dessins, durees, anomalies


def film_regions(tresse, fichier, hauteur=800, largeur=800, marge=60, construction=False, fenetre=0.7, rampe=0.25, **options):
    """Le film (MP4, 25 images/s) ; rend les anomalies."""
    dessins, durees, anomalies = dessins_regions(tresse, fenetre=fenetre, rampe=rampe, hauteur=hauteur, largeur=largeur, marge=marge)
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{largeur}x{hauteur}',
                               '-r', '25', '-i', '-', *ENCODEUR, fichier], stdin=subprocess.PIPE)
    for d, ms in zip(dessins, durees):
        donnees = bytes(surface_conforme(d, hauteur, largeur, marge, construction, largeur_brin=3, **options).get_data())
        for _ in range(max(1, round(ms / 40))): ffmpeg.stdin.write(donnees)
    ffmpeg.stdin.close()
    ffmpeg.wait()
    return anomalies


# ---------------------------------------------------------------- les images

def main(mot, k, hauteur=800, largeur=800, marge=60):
    nom = '_'.join(map(str, mot)) + f'_lettre{k + 1}'
    mot = mot[:k + 1]   # comme `dessins_conforme`, le nombre de trous vient des lettres jusqu'à celle-ci
    nb = max(map(abs, mot)) + 1
    h_int, l_int = hauteur - 2 * marge, largeur - 2 * marge
    lettre = Lettre(etat_de_tresse(mot[:k], nb), etat_de_tresse(mot[:k + 1], nb), mot[k], h_int, l_int)
    d = dessins_de_verticale(lettre, 0.5)
    lignes, erreurs = par_regions(lettre, 0.5, mele(fractions(lettre, 0.5, d[0]), fractions(lettre, 0.5, d[1]), 0.5), d[0])
    print('régions :', len(lignes), 'lacets,', len(erreurs), 'erreurs', erreurs)
    print('croisements :', nb_croisements(lignes, lettre.clou))
    s = 0.5
    trous = lettre.trous_ecran(s)
    axe, (LA, AB, BR, LB, AR) = lettre.aretes(s)
    dessin_axe = [np.array(a) for a in axe] + [np.array(x) for x in (LA, AB, BR, LB, AR)]
    regions = (lignes, trous, lettre.clou, dessin_axe)
    os.makedirs('imgs', exist_ok=True)
    for suffixe, construction in (('', False), ('_construction', True)):
        surface_conforme(regions, hauteur, largeur, marge, construction, largeur_brin=3).write_to_png(f'imgs/essai_regions_{nom}{suffixe}.png')
    # le maillage actuel, à la même image (l'image 24 de la lettre : s = 0,5)
    dessins, _, _ = dessins_conforme(mot[:k + 1], hauteur=hauteur, largeur=largeur, marge=marge)
    surface_conforme(dessins[1 + 48 * k + 23], hauteur, largeur, marge, False, largeur_brin=3).write_to_png(f'imgs/essai_maillage_{nom}.png')
    print('écrit imgs/essai_regions_' + nom + '*.png et imgs/essai_maillage_' + nom + '.png')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'film':   # python etude/lacets/essai_regions.py film "1 -2 1 -2" [sortie.mp4] [construction]
        mot = [int(x) for x in sys.argv[2].split()]
        fichier = sys.argv[3] if len(sys.argv) > 3 else 'imgs/essai_regions_film_' + '_'.join(map(str, mot)) + '.mp4'
        os.makedirs(os.path.dirname(fichier) or '.', exist_ok=True)
        reglages = {a.split('=')[0]: float(a.split('=')[1]) for a in sys.argv if '=' in a}   # fenetre=0.5 rampe=0.25
        anomalies = film_regions(mot, fichier, construction='construction' in sys.argv, **reglages)
        print(fichier, ':', len(anomalies), 'anomalies', anomalies[:30])
        sys.exit()
    mot = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1').split()]
    k = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
    main(mot, k)
