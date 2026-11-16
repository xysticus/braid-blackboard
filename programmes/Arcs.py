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
from tresses import calcule_autofn_de_tresse, etat_de_tresse, intervalle, lit_mot, en_image_pil, ENCODEUR

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


def pchip(y):
    """Pentes de l'interpolation cubique d'Hermite monotone (Fritsch–Carlson) des valeurs y aux temps 0, 1, 2, ... :
    la courbe ne dépasse jamais les valeurs entre deux temps (donc reste positive si elles le sont), et sa dérivée est
    continue."""
    y = np.asarray(y, dtype=float)
    if len(y) < 2: return np.zeros_like(y)
    d = np.diff(y, axis=0)
    m = np.zeros_like(y)
    m[0], m[-1] = d[0], d[-1]
    interieur = (d[:-1] * d[1:]) > 0
    m[1:-1] = np.where(interieur, 2 * d[:-1] * d[1:] / np.where(interieur, d[:-1] + d[1:], 1), 0)
    for k in (0, -1): # pentes des bouts : pas de dépassement
        m[k] = np.where(m[k] * d[k] <= 0, 0, np.minimum(np.abs(m[k]), 3 * np.abs(d[k])) * np.sign(d[k]))
    return m

def hermite(y, m, T):
    """Valeur au temps T de l'interpolation d'Hermite de valeurs y et pentes m aux temps 0, 1, 2, ..."""
    k = min(int(T), len(y) - 2) if len(y) > 1 else 0
    if len(y) == 1: return y[0]
    u = T - k
    h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
    return h00 * y[k] + h10 * m[k] + h01 * y[k + 1] + h11 * m[k + 1]


class FilmArcs(Film):
    """Les arcs f_i → m_i sur la triangulation mobile. On ne garde de `Film` que le maillage, la tension et le dessin
    (le clou est neutralisé : y_axe = -inf)."""

    def __init__(self, tresse, hauteur=800, largeur=800, ecart=6, hyperbolique=False, ecart_fixes=None, fixes='bas'):
        """fixes : 'bas' (trous fixes sur une ligne en bas, arcs de départ droits) ou 'gauche' (trous fixes groupés
        sur l'axe, à gauche de tous les trous voyageurs, f_n le plus à gauche : l'arc de f_k à m_k passe sous m_1 ...
        m_(k-1), comme le lacet x_k depuis le clou ; arcs de départ en demi-ellipses emboîtées sous l'axe).
        ecart_fixes : écart en pixels entre les trous fixes (en bas : groupés au milieu, par défaut régulièrement
        répartis sur la largeur ; à gauche : 20 par défaut)."""
        self.hauteur, self.largeur = hauteur, largeur
        self.n = n = max(map(operator.abs, tresse), default=1) + 1
        self.y_trous, self.y_fixes = (0.42 if fixes == 'bas' else 0.3) * hauteur, hauteur - 60
        # espacement proportionnel : à chaque image clé, largeur de chaque intervalle de l'axe (extrémités comprises)
        # proportionnelle à 1 + le nombre d'arcs qui le traversent (la moitié de celui des lacets) ; entre les images
        # clés, les largeurs glissent par une interpolation lisse et monotone (vitesse continue d'une lettre à l'autre,
        # largeurs toujours positives : deux trous ne s'inversent jamais)
        largeurs = []
        for k in range(len(tresse) + 1):
            trous, lacets = etat_de_tresse(tresse[:k], n)
            comptes = [0] * (n + 1)
            for lacet in lacets:
                for x in lacet: comptes[intervalle(x, trous)] += 1
            w = np.array([1 + c / 2 for c in comptes])
            largeurs.append(w / w.sum())
        self.largeurs = np.array(largeurs)
        self.pentes = pchip(self.largeurs)
        self.marge = 30
        self.marge_gauche = 30 if fixes == 'bas' else 30 + n * (ecart_fixes or 20)
        voyageurs = [(x, self.y_trous) for x in self.places_au_temps(0)]
        if fixes == 'gauche':
            e = ecart_fixes or 20
            places_fixes = [(15 + (n - 1 - k) * e, self.y_trous) for k in range(n)] # f_1 à droite, f_n à gauche
        elif ecart_fixes is None: places_fixes = [((k + 1) * largeur / (n + 1) + 0.37, self.y_fixes) for k in range(n)]
        else: places_fixes = [(largeur / 2 + (k - (n - 1) / 2) * ecart_fixes + 0.37, self.y_fixes) for k in range(n)]
        self.maillage, indices, _ = maillage_du_raccord(voyageurs + places_fixes, None, largeur, hauteur)
        self.voyageurs, self.fixes = indices[:n], indices[n:]
        self.places = list(self.voyageurs) # le trou voyageur à chaque place de l'axe, de gauche à droite
        self.numero = 0 # lettres déjà faites
        # arcs de départ : de f_i à m_i, en ligne droite (trous fixes en bas) ou en demi-ellipse sous l'axe (à gauche :
        # les intervalles [f_k, m_k] sont emboîtés, donc les demi-ellipses de même aplatissement ne se croisent pas)
        self.courbes = []
        for f, m in zip(self.fixes, self.voyageurs):
            p, q = self.maillage.pos[f], self.maillage.pos[m]
            if fixes == 'gauche':
                c, r = (p[0] + q[0]) / 2, (q[0] - p[0]) / 2
                phi = np.linspace(math.pi, 0, 300)
                points = np.column_stack((c + r * np.cos(phi), self.y_trous + 0.8 * r * np.sin(phi)))
            else: points = np.linspace(p, q, 200)
            self.courbes.append(coupe_arc(points, self.maillage, f, m))
        self.ecart = ecart
        self.dispositions, self.etape, self.y_axe = [(None, ecart)], 0, -math.inf # neutralise le clou de Film
        # tension : euclidienne (`Film.tend`, alignement des voisins et écart minimal) ou hyperbolique (géodésiques de la
        # métrique de Klein de la triangulation, `Geodesiques` : les brins se rangent d'eux-mêmes)
        self.geodesiques = None
        if hyperbolique:
            from Geodesiques import Geodesiques
            self.geodesiques = Geodesiques(self)
            self.geodesiques.tend(tours=60)
        else:
            for _ in range(100): self.tend(0.3, ecart, portee_sinus=3 * ecart)

    def places_au_temps(self, T):
        """Abscisses des n places de l'axe au temps T (T = k : image clé k)."""
        w = np.maximum(hermite(self.largeurs, self.pentes, T), 1e-6)
        w = w / w.sum()
        gauche = getattr(self, 'marge_gauche', self.marge)
        return gauche + (self.largeur - gauche - self.marge) * np.cumsum(w)[:-1]

    def lettre(self, sigma, images=60, sous_pas=3, taux=0.15, rendu=None):
        """Demi-tour des trous aux places i et i+1 (σ_i), à vitesse angulaire constante, autour du milieu des deux
        places, pendant que toutes les places glissent (`places_au_temps`)."""
        i = abs(sigma) - 1
        a, b = self.places[i], self.places[i + 1]
        sens = SENS_DE_SIGMA * (1 if sigma > 0 else -1)
        for pas in range(1, images * sous_pas + 1):
            u = pas / (images * sous_pas)
            x = self.places_au_temps(self.numero + u)
            for j, h in enumerate(self.places): self.maillage.pos[h] = (x[j], self.y_trous)
            milieu, r = np.array(((x[i] + x[i + 1]) / 2, self.y_trous)), (x[i + 1] - x[i]) / 2
            c, s = math.cos(math.pi * u), math.sin(math.pi * u)
            self.maillage.pos[a] = milieu + r * np.array((-c, -sens * s))
            self.maillage.pos[b] = milieu + r * np.array((c, sens * s))
            if pas == images * sous_pas:
                self.maillage.pos[a], self.maillage.pos[b] = (x[i + 1], self.y_trous), (x[i], self.y_trous)
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            if self.geodesiques: self.geodesiques.tend(tours=2, precision=1e-5)
            else: self.tend(taux, self.ecart, portee_sinus=3 * self.ecart) # sinus mesuré à distance : pas de marches dans
                # les éventails de triangles minces (bossage)
            if rendu and pas % sous_pas == 0: rendu(self)
        self.places[i], self.places[i + 1] = b, a
        self.numero += 1

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

    def cadre(self, rubans=False, largeur_brin=2.5, avec_aretes=False, lisere=False):
        """Image : arcs (ou rubans) en couleur ; lisere : chaque arc tracé en blanc large avec un liseré de couleur fin
        au milieu (sur fond blanc, impression d'un écart entre brins voisins)."""
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
        for k in range(len(self.courbes)):
            P = self.ruban(k) if rubans else self.polyligne(k)
            traits = [((1, 1, 1), 0.85 * self.ecart), (COULEURS[k % len(COULEURS)], 1.3)] if lisere else \
                     [(COULEURS[k % len(COULEURS)], largeur_brin)]
            for couleur, largeur in traits:
                ctx.set_source_rgb(*couleur)
                ctx.set_line_width(largeur)
                ctx.move_to(*P[0])
                for q in P[1:]: ctx.line_to(*q)
                ctx.stroke()
        for liste, gris in ((self.voyageurs, 0.0), (self.fixes, 0.55)):
            ctx.set_source_rgb(gris, gris, gris)
            for v in liste:
                ctx.arc(*self.maillage.pos[v], 4, 0, 2 * math.pi)
                ctx.fill()
        return surface


class DiagrammeCourbes(FilmArcs):
    """Diagramme de courbes : un seul point fixe, au bout gauche de l'axe, et pour arcs les segments de l'axe (du point
    fixe au premier trou, puis d'un trou au suivant), que la tresse emporte. Ils portent la même information que
    l'action d'Artin. Au départ, le dessin est l'axe lui-même ; rien n'est accroché en bas."""

    def __init__(self, tresse, hauteur=800, largeur=800, ecart=6, hyperbolique=False):
        self.hauteur, self.largeur = hauteur, largeur
        self.n = n = max(map(operator.abs, tresse), default=1) + 1
        self.y_trous = 0.5 * hauteur
        largeurs = []
        for k in range(len(tresse) + 1):
            trous, lacets = etat_de_tresse(tresse[:k], n)
            comptes = [0] * (n + 1)
            for lacet in lacets:
                for x in lacet: comptes[intervalle(x, trous)] += 1
            w = np.array([1 + c / 2 for c in comptes])
            largeurs.append(w / w.sum())
        self.largeurs = np.array(largeurs)
        self.pentes = pchip(self.largeurs)
        self.marge = 30
        voyageurs = [(x, self.y_trous) for x in self.places_au_temps(0)]
        fixe = (self.marge / 2, self.y_trous)
        self.maillage, indices, _ = maillage_du_raccord(voyageurs + [fixe], None, largeur, hauteur)
        self.voyageurs, self.fixes = indices[:n], indices[n:]
        self.places = list(self.voyageurs)
        self.numero = 0
        # arcs de départ : les segments de l'axe, un peu bombés vers le haut pour la découpe (la tension les redresse)
        bouts = [self.fixes[0]] + list(self.voyageurs)
        self.courbes = []
        for a, b in zip(bouts[:-1], bouts[1:]):
            p, q = self.maillage.pos[a], self.maillage.pos[b]
            u = np.linspace(0, 1, 200)
            points = p + u[:, None] * (q - p) - np.column_stack((0 * u, 4 * np.sin(np.pi * u)))
            self.courbes.append(coupe_arc(points, self.maillage, a, b))
        self.ecart = ecart
        self.dispositions, self.etape, self.y_axe = [(None, ecart)], 0, -math.inf
        self.geodesiques = None
        if hyperbolique:
            from Geodesiques import Geodesiques
            self.geodesiques = Geodesiques(self)
            self.geodesiques.tend(tours=60)
        else:
            for _ in range(100): self.tend(0.3, ecart, portee_sinus=3 * ecart)

    def mots(self):
        """Mot relu sur le ruban du premier arc (du point fixe au premier trou), qui est le lacet x_1 : la seule
        vérification directe (les autres arcs vont d'un trou à l'autre)."""
        trous = sorted(map(tuple, self.maillage.pos[self.voyageurs]))
        return [lit_mot(self.ruban(0), trous)]


def verifie_diagramme(tresse, **options):
    """Après chaque lettre, le mot relu sur le ruban du premier arc est l'image de x_1."""
    film = DiagrammeCourbes(tresse, **options)
    for k, sigma in enumerate(tresse):
        film.lettre(sigma, images=12)
        if film.mots()[0] != calcule_autofn_de_tresse(tresse[:k + 1], film.n)[0]: return False
    return True


def verifie_arcs(tresse, **options):
    """Après chaque lettre, les mots relus sur les rubans sont ceux de calcule_autofn_de_tresse."""
    film = FilmArcs(tresse, **options)
    for k, sigma in enumerate(tresse):
        film.lettre(sigma, images=12)
        if film.mots() != calcule_autofn_de_tresse(tresse[:k + 1], film.n): return False
    return True


def film_arcs(tresse, fichier, rubans=False, pause=0.5, lisere=False, classe=None, **options):
    """options : celles de FilmArcs (ou de la classe donnée, par exemple DiagrammeCourbes), dont hyperbolique=True
    (géodésiques)."""
    """Film MP4 (AV1, 25 images/s) des arcs (ou de leurs rubans), écrit au fil du calcul par ffmpeg."""
    film = (classe or FilmArcs)(tresse, **options)
    l, h = film.largeur, film.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', '25', '-i', '-', *ENCODEUR, fichier], stdin=subprocess.PIPE)
    def ecrit(f, fois=1):
        surface = f.cadre(rubans, lisere=lisere)
        surface.flush()
        donnees = bytes(surface.get_data())
        for _ in range(fois): ffmpeg.stdin.write(donnees)
    ecrit(film, round(25 * pause))
    for sigma in tresse: film.lettre(sigma, rendu=ecrit)
    ecrit(film, round(75 * pause))
    ffmpeg.stdin.close()
    ffmpeg.wait()


TRESSES = (([4, 3, -1, -1, 2, -4, 1], '43m1m12m41'), ([1, -2, 1, -2, 1, -2, 3, -1, 2], 'charge'))

# les méthodes : (vérification, options du film)
METHODES = {
    'rubans': (lambda t: verifie_arcs(t, ecart_fixes=30), dict(rubans=True, ecart_fixes=30)),
    'rubans_gauche': (lambda t: verifie_arcs(t, fixes='gauche'), dict(rubans=True, fixes='gauche')),
    'diagramme': (verifie_diagramme, dict(classe=DiagrammeCourbes, lisere=True)),
}

if __name__ == "__main__":
    # depuis la racine du dépôt : python programmes/Arcs.py [rubans] [rubans_gauche] [diagramme] (toutes par défaut) ;
    # vérifie les mots puis écrit imgs/<méthode>/film_*.mp4
    import os, sys
    for methode in sys.argv[1:] or list(METHODES):
        verifie, options = METHODES[methode]
        os.makedirs(f'./imgs/{methode}', exist_ok=True)
        for tresse, nom in TRESSES:
            assert verifie(tresse), f"{methode} : mots faux sur {tresse}"
            film_arcs(tresse, f'./imgs/{methode}/film_{nom}.mp4', **options)
            print(methode, nom, 'fait')
