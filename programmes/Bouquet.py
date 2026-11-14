'''Un bouquet qui pousse : morphing de lacets (prototype).

Les trous ne font plus des demi-tours sur l'axe : ils suivent une chorégraphie libre (position de chaque trou à chaque
instant). Les lacets, posés sur la triangulation mobile de Triangulation.py, sont emportés par la déformation du plan
qui accompagne ce mouvement, et restent tendus. Ici : des groupes de trous montent du clou comme des pousses (les
lacets qui les entourent s'étirent en tiges), puis tournent sur eux-mêmes en s'écartant (les lacets s'enroulent en
rosaces : les fleurs s'ouvrent). Rendu à la manière des films image par image qui montrent une plante pousser.
'''

import math, subprocess
import numpy as np
import cairo

from Triangulation import Film, croix


def lisse(x):
    '''Rampe douce de 0 à 1 sur [0, 1] (0 avant, 1 après).'''
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

def bezier(p0, p1, p2, s):
    '''Point de la courbe de Bézier quadratique p0, p1, p2 au paramètre s.'''
    return (1 - s) ** 2 * p0 + 2 * s * (1 - s) * p1 + s * s * p2


def insere_sommet(maillage, courbes, p):
    '''Ajoute au maillage un sommet au point p, qui coupe en trois le triangle qui le contient ; les courbes sont mises
    à jour sur place sans changer de forme : chaque corde de ce triangle est recoupée par les trois nouvelles arêtes.
    Renvoie l'indice du sommet, ou None si p n'est dans aucun triangle.'''
    pos = maillage.pos
    triangle = None
    for t in maillage.triangles:
        a, b, c = sorted(t)
        s = [croix(pos[y] - pos[x], p - pos[x]) for x, y in ((a, b), (b, c), (c, a))]
        if all(x > 1e-9 for x in s) or all(x < -1e-9 for x in s):
            triangle = (a, b, c)
            break
    if triangle is None: return None
    v = len(pos)
    maillage.pos = np.vstack((pos, p))
    def sommets(n): return {n[1]} if n[0] == 'v' else set(n[1:3])
    # nouvelles cordes : intersections avec va, vb, vc, rangées le long de la corde
    nouvelles = []
    for courbe in courbes:
        resultat = [courbe[0]]
        for u, w in zip(courbe[:-1], courbe[1:]):
            if sommets(u) | sommets(w) == set(triangle):
                q0, q1 = maillage.position(u), maillage.position(w)
                coupes = []
                for x in triangle:
                    r, d = q1 - q0, maillage.pos[x] - p
                    den = croix(r, d)
                    if abs(den) < 1e-12: continue
                    s_corde, s_arete = croix(p - q0, d) / den, croix(p - q0, r) / den
                    if 0 < s_corde < 1 and 0 < s_arete < 1:
                        a_, b_ = (x, v) if x < v else (v, x)
                        fraction = 1 - s_arete if a_ == x else s_arete # fraction de a_ vers b_
                        coupes.append((s_corde, ('e', a_, b_, fraction)))
                resultat.extend(n for _, n in sorted(coupes))
            resultat.append(w)
        nouvelles.append(resultat)
    courbes[:] = nouvelles
    a, b, c = triangle
    maillage.triangles.remove(frozenset(triangle))
    del maillage.signes[frozenset(triangle)]
    for x, y in ((a, b), (b, c), (c, a)):
        t = frozenset((x, y, v))
        maillage.triangles.add(t)
        maillage.signes[t] = maillage.signe(t)
    return v


class Pousse(Film):
    '''Film de lacets dont les trous suivent une chorégraphie libre. On part de l'état de départ du film des tresses
    (lacets autour de trous posés sur l'axe), on rassemble sans le montrer les trous près du clou (la graine), puis on
    fait suivre aux trous la chorégraphie, image par image.'''

    def __init__(self, groupes, hauteur=800, largeur=800, ecart=None):
        '''groupes : liste des fleurs, chacune décrite par un dictionnaire (nombre de trous, tête, départ, couleur...) ;
        les trous sont distribués de gauche à droite.'''
        self.groupes = groupes
        nb_trous = sum(g['trous'] for g in groupes)
        super().__init__([nb_trous - 1], hauteur, largeur) # une tresse de nb_trous brins : seul l'état de départ sert
        e = largeur / 800
        self.ecart = ecart or 7 * e
        clou = self.maillage.pos[self.clou]
        # la graine : les trous en rang serré juste au-dessus du clou
        self.graine = np.array([(clou[0] + (k - (nb_trous - 1) / 2) * 16 * e, clou[1] - 40 * e)
                                for k in range(nb_trous)])
        self.satellites = {}
        self.deplace(list(self.trous), self.graine, pas_max=2 * e)
        self.y_axe = -math.inf # plus d'axe : pas de départ perpendiculaire des brins du clou (portions_du_clou vide)

    def positions(self):
        return self.maillage.pos[self.trous].copy()

    def deplace(self, sommets, cibles, pas_max, taux=0.15):
        '''Amène les sommets donnés en ligne droite à leurs cibles, par sous-pas d'au plus pas_max pixels, en
        retournant les arêtes et en tendant les lacets à chaque sous-pas.'''
        depart = self.maillage.pos[sommets].copy()
        n = max(1, math.ceil(np.hypot(*(np.asarray(cibles) - depart).T).max() / pas_max))
        for s in range(1, n + 1):
            self.maillage.pos[sommets] = depart + (cibles - depart) * s / n
            assert self.maillage.valide(), "triangle retourné : diminuer pas_max"
            self.maillage.delaunay(self.courbes)
            self.tend(taux, self.ecart)

    def etat_du_groupe(self, n, t):
        '''(centre, rayon, rotation, ouverture, montée) de la fleur n au temps t : après son départ, son centre monte de
        la graine à sa tête le long d'une tige courbe (Bézier), en oscillant un peu (les plantes tournent sur
        elles-mêmes en poussant) ; quand la tête est atteinte, la fleur tourne sur elle-même en s'élargissant.'''
        g = self.groupes[n]
        k = sum(x['trous'] for x in self.groupes[:n])
        depart_graine = self.graine[k:k + g['trous']].mean(axis=0)
        tete = np.array(g['tete'], dtype=float) * self.largeur / 800
        controle = np.array((depart_graine[0] + 0.15 * (tete[0] - depart_graine[0]), (depart_graine[1] + tete[1]) / 2))
        montee = lisse((t - g['depart']) / g['duree_montee'])
        centre = bezier(depart_graine, controle, tete, montee)
        # nutation : oscillation latérale, nulle à la graine et à l'arrivée
        centre = centre + np.array((g['nutation'] * math.sin(2 * math.pi * t / 2.7 + n) * math.sin(math.pi * montee), 0))
        ouverture = lisse((t - g['depart'] - g['duree_montee']) / g['duree_ouverture'])
        rayon = ((1 - ouverture) * g['rayon_bouton'] + ouverture * g['rayon_fleur']) * self.largeur / 800
        rotation = (g['sens'] * 2 * math.pi * g['tours'] + g['phase']) * ouverture
        return centre, rayon, rotation, ouverture, montee

    def choregraphie(self, t):
        '''Positions des trous au temps t (secondes) : ceux de chaque fleur, d'abord en bouton (petit demi-cercle ouvert
        vers le haut, dans l'ordre gauche-droite de la graine, pour que les trous sortent du rang sans que leurs
        chemins se croisent), puis sur un cercle régulier qui tourne et s'élargit (la fleur s'ouvre).'''
        resultat, k = [], 0
        for n, g in enumerate(self.groupes):
            m = g['trous']
            centre, rayon, rotation, ouverture, montee = self.etat_du_groupe(n, t)
            sortie = lisse(montee * 5) # au tout début, les trous partent de leur place dans la graine
            for j in range(m):
                demi = math.pi - math.pi * j / max(m - 1, 1)
                regulier = math.pi - 2 * math.pi * j / m
                a = rotation + (1 - ouverture) * demi + ouverture * regulier
                cible = centre + rayon * np.array((math.cos(a), -math.sin(a)))
                resultat.append((1 - sortie) * self.graine[k + j] + sortie * cible)
            k += m
        return np.array(resultat)

    def anneau(self, n, t):
        '''Positions des sommets satellites de la fleur n : un anneau qui tourne avec elle, un peu plus large qu'elle.
        Les enroulements se forment autour de lui et traversent beaucoup de triangles : ils sont ronds.'''
        centre, rayon, rotation, _, _ = self.etat_du_groupe(n, t)
        rayon_anneau = rayon + 3 * self.ecart
        return [centre + rayon_anneau * np.array((math.cos(a), -math.sin(a)))
                for a in rotation + 0.137 + 2 * math.pi * np.arange(SATELLITES) / SATELLITES]

    def cibles(self, t):
        '''(sommets qui bougent, leurs positions au temps t) : les trous et les anneaux déjà posés ; pose les anneaux
        des fleurs qui vont s'ouvrir.'''
        for n, g in enumerate(self.groupes):
            if n not in self.satellites and t >= g['depart'] + g['duree_montee'] - 0.3:
                poses = [insere_sommet(self.maillage, self.courbes, q) for q in self.anneau(n, t)]
                self.satellites[n] = [v for v in poses if v is not None]
                self.maillage.delaunay(self.courbes)
        sommets, positions = list(self.trous), list(self.choregraphie(t))
        for n, vs in self.satellites.items():
            anneau = self.anneau(n, t)
            sommets += vs
            positions += [anneau[q] for q in range(len(vs))]
        return sommets, np.array(positions)

    def dessine(self, t, flou_temps=0.0):
        '''Image au temps t : fond sombre (avec une légère variation de lumière, comme les prises de vue image par
        image), sol, lacets colorés du vert de la tige à la couleur de leur fleur selon la hauteur, trous en
        pistils une fois les fleurs ouvertes.'''
        l, h = self.largeur, self.hauteur
        e = l / 800
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, l, h)
        ctx = cairo.Context(surface)
        lumiere = 1 + flou_temps
        fond = cairo.LinearGradient(0, 0, 0, h)
        fond.add_color_stop_rgb(0, 0.06 * lumiere, 0.07 * lumiere, 0.10 * lumiere)
        fond.add_color_stop_rgb(1, 0.12 * lumiere, 0.12 * lumiere, 0.14 * lumiere)
        ctx.set_source(fond)
        ctx.paint()
        clou = self.maillage.pos[self.clou]
        ctx.set_source_rgb(0.22 * lumiere, 0.15 * lumiere, 0.09 * lumiere) # le sol
        ctx.rectangle(0, clou[1] - 2 * e, l, h)
        ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(2.6 * e)
        vert = np.array((0.30, 0.62, 0.28))
        groupe_du_lacet = [n for n, g in enumerate(self.groupes) for _ in range(g['trous'])]
        trous_au_temps = self.choregraphie(t)
        premier_trou = np.cumsum([0] + [g['trous'] for g in self.groupes])
        for k, points in enumerate(self.polylignes()):
            g = self.groupes[groupe_du_lacet[k]]
            ouverture = lisse((t - g['depart'] - g['duree_montee'] + 0.5) / g['duree_ouverture'])
            fleur = (1 - ouverture) * vert + ouverture * np.array(g['couleur'])
            tete_y = trous_au_temps[premier_trou[groupe_du_lacet[k]]:premier_trou[groupe_du_lacet[k] + 1], 1].mean()
            degrade = cairo.LinearGradient(0, clou[1], 0, tete_y)
            degrade.add_color_stop_rgb(0, *(0.7 * vert))
            degrade.add_color_stop_rgb(0.75, *vert)
            degrade.add_color_stop_rgb(1, *fleur)
            ctx.set_source(degrade)
            ctx.move_to(*points[0])
            for p in points[1:]: ctx.line_to(*p)
            ctx.stroke()
        for k, p in enumerate(self.positions()):
            g = self.groupes[groupe_du_lacet[k]]
            ouverture = lisse((t - g['depart'] - g['duree_montee']) / g['duree_ouverture'])
            if ouverture <= 0: continue
            ctx.set_source_rgba(1.0, 0.85, 0.3, ouverture)
            ctx.arc(*p, 3.5 * e, 0, 2 * math.pi)
            ctx.fill()
        return surface


SATELLITES = 10 # sommets de l'anneau qui tourne avec chaque fleur

BOUQUET = [
    dict(trous=3, tete=(210, 300), depart=0.0, duree_montee=5.0, duree_ouverture=4.0, rayon_bouton=10, rayon_fleur=34,
         tours=1.25, sens=1, phase=0.3, nutation=18, couleur=(0.92, 0.35, 0.50)),
    dict(trous=3, tete=(410, 170), depart=1.0, duree_montee=5.5, duree_ouverture=4.0, rayon_bouton=10, rayon_fleur=38,
         tours=1.5, sens=-1, phase=1.1, nutation=22, couleur=(0.97, 0.78, 0.25)),
    dict(trous=3, tete=(610, 320), depart=2.0, duree_montee=5.0, duree_ouverture=4.0, rayon_bouton=10, rayon_fleur=34,
         tours=1.25, sens=1, phase=2.0, nutation=16, couleur=(0.62, 0.42, 0.90)),
]

def film_bouquet(fichier, groupes=BOUQUET, duree=14.0, images_par_seconde=25, saccade=2, pause=2.0, **options):
    '''Film MP4 du bouquet. saccade : chaque image calculée est montrée ce nombre de fois (aspect image par image des
    films de plantes qui poussent) ; légère variation de lumière d'une image calculée à l'autre.'''
    pousse = Pousse(groupes, **options)
    l, h = pousse.largeur, pousse.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', str(images_par_seconde), '-i', '-', '-pix_fmt', 'yuv420p',
                               '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0', '-deadline', 'realtime',
                               '-cpu-used', '8', '-row-mt', '1', fichier], stdin=subprocess.PIPE)
    hasard = np.random.default_rng(1)
    pas = saccade / images_par_seconde
    nombre = round(duree / pas)
    for n in range(nombre + 1):
        t = n * pas
        if n: pousse.deplace(*pousse.cibles(t), pas_max=2 * l / 800)
        surface = pousse.dessine(t, flou_temps=hasard.normal(0, 0.04))
        surface.flush()
        donnees = bytes(surface.get_data())
        fois = saccade if n < nombre else round(pause * images_par_seconde)
        for _ in range(fois): ffmpeg.stdin.write(donnees)
    ffmpeg.stdin.close()
    ffmpeg.wait()


if __name__ == "__main__":
    film_bouquet('./imgs/bouquet.mp4')
