"""Sans clou : des arcs entre trous (piste 1 ter de `pistes_film_conforme.md`, premier essai).

Le lacet x_i, du clou autour du trou i, est le bord d'un voisinage mince de l'arc du clou au trou i. On remplace le clou
par n trous fixes f_1 ... f_n sur une ligne en bas (là où était le clou), et chaque lacet par l'arc de f_i au trou
voyageur m_i. La tresse ne fait bouger que les trous voyageurs (demi-tours sur l'axe, comme dans les autres films) ;
les arcs sont posés sur la triangulation mobile de `Triangulation.py` (isotopie : les retournements d'arête ne changent
pas leur forme), tendus et dessinés en droites et congés. On peut dessiner les arcs seuls, ou le bord d'un ruban autour
de chacun : on retrouve alors les lacets, et l'on relit leurs mots pour vérifier.
"""
import math, operator, subprocess
import numpy as np
import cairo

from Triangulation import Film, croix
from Raccord import maillage_du_raccord
from tresses import calcule_autofn_de_tresse, lit_mot, en_image_pil, ENCODEUR

SENS_DE_SIGMA = 1 # comme dans les autres films : σ_i positif = demi-tour horaire à l'écran
COULEURS = [(0.85, 0.15, 0.15), (0.10, 0.60, 0.15), (0.15, 0.25, 0.85), (0.75, 0.60, 0.05), (0.65, 0.15, 0.65),
            (0.05, 0.60, 0.65)]


def coupe_arc(points, maillage, debut, fin):
    """Suite des arêtes coupées par une polyligne qui va du sommet debut au sommet fin, bigones annulés ; un arc peut
    tourner autour de ses extrémités sans changer de classe, donc les traversées des arêtes de ses bouts, en tête et en
    queue, sont retirées. Renvoie les noeuds de `Triangulation` : [('v', debut), ('e', u, v, w) ..., ('v', fin)]."""
    pos = maillage.pos
    trouves = []
    for (u, v) in maillage.aretes():
        s = pos[v] - pos[u]
        cote = s[0] * (points[:, 1] - pos[u][1]) - s[1] * (points[:, 0] - pos[u][0])
        dessus = cote >= -1e-7 * math.hypot(*s)
        k = np.nonzero(dessus[:-1] != dessus[1:])[0]
        if len(k) == 0: continue
        t = cote[k] / (cote[k] - cote[k + 1])
        X = points[k] + t[:, None] * (points[k + 1] - points[k])
        w = ((X - pos[u]) @ s) / (s @ s)
        for kk, tt, ww in zip(k, t, w):
            if 1e-9 < ww < 1 - 1e-9: trouves.append((kk + tt, ('e', u, v, ww)))
    trouves.sort(key=lambda x: x[0])
    pile = []
    for _, n in trouves:
        if pile and pile[-1][1:3] == n[1:3]: pile.pop()
        else: pile.append(n)
    while pile and debut in pile[0][1:3]: pile.pop(0)
    while pile and fin in pile[-1][1:3]: pile.pop()
    return [('v', debut)] + pile + [('v', fin)]


class FilmArcs(Film):
    """Les arcs f_i → m_i sur la triangulation mobile. On ne garde de `Film` que le maillage, la tension et le dessin
    (le clou est neutralisé : y_axe = -inf)."""

    def __init__(self, tresse, hauteur=800, largeur=800, ecart=6):
        self.hauteur, self.largeur = hauteur, largeur
        self.n = n = max(map(operator.abs, tresse), default=1) + 1
        self.pas_trous = largeur / (n + 1)
        self.y_trous, self.y_fixes = 0.42 * hauteur, hauteur - 60
        voyageurs = [((k + 1) * self.pas_trous, self.y_trous) for k in range(n)]
        fixes = [((k + 1) * self.pas_trous + 0.37, self.y_fixes) for k in range(n)] # pas à la verticale exacte
        self.maillage, indices, _ = maillage_du_raccord(voyageurs + fixes, None, largeur, hauteur)
        self.voyageurs, self.fixes = indices[:n], indices[n:]
        self.places = list(self.voyageurs) # le trou voyageur à chaque place de l'axe, de gauche à droite
        # arcs de départ : segments verticaux de f_i à m_i
        self.courbes = []
        for f, m in zip(self.fixes, self.voyageurs):
            points = np.linspace(self.maillage.pos[f], self.maillage.pos[m], 200)
            self.courbes.append(coupe_arc(points, self.maillage, f, m))
        self.ecart = ecart
        self.dispositions, self.etape, self.y_axe = [(None, ecart)], 0, -math.inf # neutralise le clou de Film
        for _ in range(100): self.tend(0.3, ecart)

    def lettre(self, sigma, images=60, sous_pas=3, taux=0.15, rendu=None):
        """Demi-tour des trous aux places i et i+1 (σ_i), images régulières en angle."""
        i = abs(sigma) - 1
        a, b = self.places[i], self.places[i + 1]
        pa, pb = self.maillage.pos[a].copy(), self.maillage.pos[b].copy()
        milieu, r = (pa + pb) / 2, (pb[0] - pa[0]) / 2
        sens = SENS_DE_SIGMA * (1 if sigma > 0 else -1)
        for pas in range(1, images * sous_pas + 1):
            theta = math.pi * pas / (images * sous_pas)
            c, s = math.cos(theta), math.sin(theta)
            self.maillage.pos[a] = milieu + r * np.array((-c, -sens * s))
            self.maillage.pos[b] = milieu + r * np.array((c, sens * s))
            if pas == images * sous_pas: self.maillage.pos[a], self.maillage.pos[b] = pb, pa
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            self.tend(taux, self.ecart)
            if rendu and pas % sous_pas == 0: rendu(self)
        self.places[i], self.places[i + 1] = b, a

    def ruban(self, k, largeur=None):
        """Bord d'un ruban autour de l'arc k : un lacet du trou fixe autour du trou voyageur, qui revient au trou fixe
        (côté droit de l'arc à l'aller, demi-cercle autour du trou voyageur, côté gauche au retour : le sens des
        lacets, celui des mots de `lit_mot`)."""
        largeur = self.ecart / 3 if largeur is None else largeur # deux rubans voisins ne se touchent pas
        P = self.polyligne(k)
        P = P[np.concatenate(([True], np.hypot(*np.diff(P, axis=0).T) > 1e-9))]
        d = np.gradient(P, axis=0)
        d /= np.maximum(np.hypot(*d.T), 1e-12)[:, None]
        normale = np.column_stack((-d[:, 1], d[:, 0]))
        # près des bouts, la largeur va à zéro côté trou fixe (le ruban part du trou fixe)
        long = np.concatenate(([0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))))
        l = largeur * np.minimum(1, long / 20)
        gauche, droite = P + l[:, None] * normale, P - l[:, None] * normale
        bout = P[-1]
        a0 = math.atan2(*(gauche[-1] - bout)[::-1])
        tour = bout + largeur * np.column_stack((np.cos(a0 - np.linspace(0, math.pi, 30)),
                                                 np.sin(a0 - np.linspace(0, math.pi, 30))))
        return np.concatenate((gauche, tour, droite[::-1]))[::-1]

    def mots(self):
        """Mots relus sur les rubans (demi-droites qui montent des trous voyageurs, triés par abscisse)."""
        trous = sorted(map(tuple, self.maillage.pos[self.voyageurs]))
        return [lit_mot(self.ruban(k), trous) for k in range(self.n)]

    def cadre(self, rubans=False, largeur_brin=2.5, avec_aretes=False):
        l, h = self.largeur, self.hauteur
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, l, h)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        if avec_aretes:
            ctx.set_source_rgb(0.8, 0.8, 0.8)
            ctx.set_line_width(0.7)
            for u, v in self.maillage.aretes():
                ctx.move_to(*self.maillage.pos[u]); ctx.line_to(*self.maillage.pos[v]); ctx.stroke()
        ctx.set_line_width(largeur_brin)
        for k in range(self.n):
            P = self.ruban(k) if rubans else self.polyligne(k)
            ctx.set_source_rgb(*COULEURS[k % len(COULEURS)])
            ctx.move_to(*P[0])
            for q in P[1:]: ctx.line_to(*q)
            ctx.stroke()
        for liste, gris in ((self.voyageurs, 0.0), (self.fixes, 0.55)):
            ctx.set_source_rgb(gris, gris, gris)
            for v in liste:
                ctx.arc(*self.maillage.pos[v], 4, 0, 2 * math.pi)
                ctx.fill()
        return surface


def verifie_arcs(tresse, **options):
    """Après chaque lettre, les mots relus sur les rubans sont ceux de calcule_autofn_de_tresse."""
    film = FilmArcs(tresse, **options)
    for k, sigma in enumerate(tresse):
        film.lettre(sigma, images=12)
        if film.mots() != calcule_autofn_de_tresse(tresse[:k + 1], film.n): return False
    return True


def film_arcs(tresse, fichier, rubans=False, pause=0.5, **options):
    """Film MP4 (AV1, 25 images/s) des arcs (ou de leurs rubans), écrit au fil du calcul par ffmpeg."""
    film = FilmArcs(tresse, **options)
    l, h = film.largeur, film.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', '25', '-i', '-', *ENCODEUR, fichier], stdin=subprocess.PIPE)
    def ecrit(f, fois=1):
        surface = f.cadre(rubans)
        surface.flush()
        donnees = bytes(surface.get_data())
        for _ in range(fois): ffmpeg.stdin.write(donnees)
    ecrit(film, round(25 * pause))
    for sigma in tresse: film.lettre(sigma, rendu=ecrit)
    ecrit(film, round(75 * pause))
    ffmpeg.stdin.close()
    ffmpeg.wait()


if __name__ == "__main__":
    assert verifie_arcs([1])
    assert verifie_arcs([1, -2, 1])
    assert verifie_arcs([4, 3, -1, -1, 2, -4, 1])
    film_arcs([4, 3, -1, -1, 2, -4, 1], './imgs/film_arcs_43m1m12m41.mp4')
    film_arcs([4, 3, -1, -1, 2, -4, 1], './imgs/film_rubans_43m1m12m41.mp4', rubans=True)
