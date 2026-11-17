"""Un escargot fait de rubans (méthode des rubans, trous fixes à gauche de l'axe).

Les trous fixes, groupés au bout gauche de l'axe, sont la queue. Chaque arc va d'un trou fixe à un trou voyageur ; au
départ, ce sont des demi-ellipses emboîtées sous l'axe. Puis les trous voyageurs suivent une chorégraphie libre (comme
le bouquet), et la triangulation mobile emporte les arcs (isotopie : jamais de croisement) :

- la coquille : quatre trous en anneau montent au-dessus du corps et tournent ensemble plusieurs tours ; les arcs qui
  y aboutissent s'enroulent autour de l'anneau, chaque tour ajoutant une couche : une spirale ;
- la tête : un trou qui va à l'avant, au sol ; les arcs des yeux passent dessous (il est avant eux sur l'axe) ;
- les yeux : deux trous partent devant la tête puis montent en s'écartant : leurs arcs, retenus sous la tête, s'en
  élèvent en antennes ;
- le corps : les arcs de la tête et des yeux, de la queue à la tête, sous la coquille.
"""
import math, subprocess
import numpy as np
import cairo

from Arcs import FilmArcs, coupe_arc
from Raccord import maillage_du_raccord
from tresses import ENCODEUR


def lisse(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Escargot(FilmArcs):
    """Les arcs de la queue aux trous voyageurs (`FilmArcs` à trous fixes à gauche), et une chorégraphie : coquille en
    anneau qui tourne, yeux qui montent. Longueurs en pixels d'une image de 960 de large."""

    def __init__(self, largeur=960, hauteur=640, ecart=7, anneau=4, tours=3.0):
        self.largeur, self.hauteur = largeur, hauteur
        self.e = e = largeur / 960
        self.anneau, self.tours = anneau, tours
        self.n = n = anneau + 3 # trous de l'anneau, la tête, puis les deux yeux
        self.y_axe0 = 470 * e
        x_fixes = [(200 + 16 * (n - 1 - k)) * e for k in range(n)] # f_n le plus à gauche
        self.depart = np.array([((340 + 50 * k) * e, self.y_axe0) for k in range(anneau)] +
                               [(570 * e, self.y_axe0), (620 * e, self.y_axe0), (660 * e, self.y_axe0)])
        fixes = [(x, self.y_axe0) for x in x_fixes]
        self.maillage, indices, _ = maillage_du_raccord(list(self.depart) + fixes, None, largeur, hauteur)
        self.voyageurs, self.fixes = indices[:n], indices[n:]
        self.places = list(self.voyageurs)
        # arcs de départ : demi-ellipses emboîtées sous l'axe, de f_k à m_k
        self.courbes = []
        for f, m in zip(self.fixes, self.voyageurs):
            p, q = self.maillage.pos[f], self.maillage.pos[m]
            c, r = (p[0] + q[0]) / 2, (q[0] - p[0]) / 2
            phi = np.linspace(math.pi, 0, 300)
            points = np.column_stack((c + r * np.cos(phi), self.y_axe0 + 0.5 * r * np.sin(phi)))
            self.courbes.append(coupe_arc(points, self.maillage, f, m))
        self.ecart = ecart * e
        self.dispositions, self.etape, self.y_axe = [(None, self.ecart)], 0, -math.inf
        self.geodesiques, self.numero = None, 0
        for _ in range(100): self.tend(0.3, self.ecart, portee_sinus=3 * self.ecart)

    # --- la chorégraphie (temps en secondes) ---

    def centre_coquille(self, t):
        e = self.e
        monte = lisse(t / 2.5)
        return np.array(((400 + 40 * monte) * e, self.y_axe0 - (20 + 105 * monte) * e))

    def rayon_anneau(self, t):
        return (12 + 14 * lisse((t - 2.5) / 6.5)) * self.e

    def tours_faits(self, t):
        return self.tours * lisse((t - 2.5) / 6.5)

    def choregraphie(self, t):
        """Positions des trous voyageurs au temps t."""
        e = self.e
        resultat = []
        # l'anneau : d'abord en demi-cercle ouvert vers le bas, dans l'ordre de l'axe (pas de croisement en montant),
        # puis en cercle régulier qui tourne (sens trigonométrique à l'écran : la spirale s'ouvre vers l'arrière)
        sortie = lisse(t / 2.5)
        cercle = lisse((t - 2.0) / 1.5)
        c, r = self.centre_coquille(t), self.rayon_anneau(t)
        rotation = 2 * math.pi * self.tours_faits(t)
        m = self.anneau
        for j in range(m):
            demi = math.pi - math.pi * j / (m - 1) # de gauche à droite, par le haut
            regulier = math.pi - 2 * math.pi * j / m
            a = (1 - cercle) * demi + cercle * regulier + rotation
            cible = c + r * np.array((math.cos(a), -math.sin(a)))
            resultat.append((1 - sortie) * self.depart[j] + sortie * cible)
        # la tête : à l'avant, au sol
        avance = lisse(t / 3.0)
        resultat.append((1 - avance) * self.depart[m] + avance * np.array((660, 452)) * e)
        # les yeux : devant la tête, puis ils montent en s'écartant (les antennes)
        pousse = lisse((t - 8.0) / 3.0)
        for j, (devant, bout) in enumerate((((690, 458), (712, 300)), ((712, 462), (772, 318)))):
            base = (1 - avance) * self.depart[m + 1 + j] + avance * np.array(devant) * e
            resultat.append((1 - pousse) * base + pousse * np.array(bout) * e)
        return np.array(resultat)

    def deplace(self, cibles, pas_max, taux=0.15):
        depart = self.maillage.pos[self.voyageurs].copy()
        n = max(1, math.ceil(np.hypot(*(cibles - depart).T).max() / pas_max))
        for s in range(1, n + 1):
            self.maillage.pos[self.voyageurs] = depart + (cibles - depart) * s / n
            assert self.maillage.valide(), "triangle retourné : diminuer pas_max"
            self.maillage.delaunay(self.courbes)
            self.tend(taux, self.ecart, portee_sinus=3 * self.ecart)

    # --- le dessin ---

    def dessine(self, t):
        """Fond vert ; chaque arc tracé en ruban plein (trait large cerné de brun sombre) : dans la coquille, en bandes
        brun, beige et marron selon l'arc ; ailleurs, couleur chair d'escargot ; les yeux au bout des antennes."""
        l, h, e = self.largeur, self.hauteur, self.e
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, l, h)
        ctx = cairo.Context(surface)
        fond = cairo.LinearGradient(0, 0, 0, h)
        fond.add_color_stop_rgb(0, 0.66, 0.80, 0.52)
        fond.add_color_stop_rgb(1, 0.38, 0.58, 0.30)
        ctx.set_source(fond)
        ctx.paint()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        coquille = [(0.47, 0.29, 0.14), (0.86, 0.75, 0.56), (0.33, 0.19, 0.09), (0.70, 0.52, 0.30)]
        chair, cerne = (0.74, 0.65, 0.52), (0.24, 0.15, 0.08)
        c = self.centre_coquille(t)
        rayon = self.rayon_anneau(t) + (self.anneau * self.tours_faits(t) + 1.5) * self.ecart
        largeur = 0.8 * self.ecart
        def trait(points, couleur, epaisseur):
            ctx.set_source_rgb(*couleur)
            ctx.set_line_width(epaisseur)
            ctx.move_to(*points[0])
            for p in points[1:]: ctx.line_to(*p)
            ctx.stroke()
        lignes = [self.polyligne(k) for k in range(self.n)]
        # d'abord le corps (hors de la coquille), puis la coquille par-dessus
        for dedans in (False, True):
            for k, points in enumerate(lignes):
                ctx.save()
                if dedans:
                    if k >= self.anneau: ctx.restore(); continue # les arcs des yeux ne montent pas dans la coquille
                    ctx.arc(*c, rayon, 0, 2 * math.pi)
                else:
                    ctx.rectangle(0, 0, l, h)
                    ctx.arc(*c, rayon, 0, 2 * math.pi)
                    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
                ctx.clip()
                epaisseur = largeur if dedans else 1.5 * self.ecart # le corps : chair épaisse, les brins se fondent en pied
                trait(points, cerne, epaisseur + 1.6 * e)
                trait(points, coquille[k % len(coquille)] if dedans else chair, epaisseur)
                ctx.restore()
        # les yeux
        apparition = lisse((t - 9.0) / 2.0)
        if apparition > 0:
            for v in self.voyageurs[self.anneau + 1:]:
                p = self.maillage.pos[v]
                ctx.set_source_rgba(0.12, 0.08, 0.05, apparition)
                ctx.arc(*p, 6 * e, 0, 2 * math.pi)
                ctx.fill()
                ctx.set_source_rgba(1, 1, 1, apparition)
                ctx.arc(p[0] + 2 * e, p[1] - 2 * e, 1.8 * e, 0, 2 * math.pi)
                ctx.fill()
        return surface


def film_escargot(fichier, duree=12.0, images_par_seconde=25, pause=2.0, **options):
    """Film MP4 de l'escargot, écrit au fil du calcul par ffmpeg."""
    escargot = Escargot(**options)
    l, h = escargot.largeur, escargot.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', str(images_par_seconde), '-i', '-', *ENCODEUR, fichier],
                              stdin=subprocess.PIPE)
    nombre = round(duree * images_par_seconde)
    for n in range(nombre + 1):
        t = n / images_par_seconde
        if n: escargot.deplace(escargot.choregraphie(t), pas_max=2 * escargot.e)
        surface = escargot.dessine(t)
        surface.flush()
        donnees = bytes(surface.get_data())
        for _ in range(1 if n < nombre else round(pause * images_par_seconde)): ffmpeg.stdin.write(donnees)
    ffmpeg.stdin.close()
    ffmpeg.wait()


if __name__ == "__main__":
    import os
    os.makedirs('./imgs/escargot', exist_ok=True)
    film_escargot('./imgs/escargot/film.mp4')
