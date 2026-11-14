'''Un bouquet qui pousse : morphing de lacets (prototype).

Les trous ne font plus des demi-tours sur l'axe : ils suivent une chorégraphie libre (position de chaque trou à chaque
instant). Les lacets, posés sur la triangulation mobile de Triangulation.py, sont emportés par la déformation du plan
qui accompagne ce mouvement, et sont tendus (mollement). Les trous dorment sous terre (la graine) ; des groupes de
trous en sortent comme des pousses (les lacets qui les entourent s'étirent en tiges). Une fleur : des sépales et des
pétales en alternance sur un petit cercle ; le bourgeon tourne sur lui-même (les lacets s'y enroulent en couches),
puis les sépales s'arrêtent et retiennent le bourgeon pendant que les pétales en sortent : les couches, accrochées
aux sépales, s'étirent en lobes autour des pétales, la fleur éclot. Une feuille : deux trous qui s'écartent sur le
côté. Rendu à la manière des films image par image qui montrent une plante pousser.
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
    (lacets autour de trous posés sur l'axe), on rassemble sans le montrer les trous sous terre près du clou (la
    graine), puis on fait suivre aux trous la chorégraphie, image par image.'''

    def __init__(self, groupes, hauteur=1080, largeur=810, ecart=None, taux=0.12):
        '''groupes : liste de fleurs et de feuilles (dictionnaires, voir BOUQUET) ; leurs trous sont pris de gauche
        à droite dans la graine ; leurs têtes sont données par (abscisse, hauteur au-dessus du sol), en pixels d'une
        image de 800 de large. Format portrait 3:4 par défaut, comme une photo. taux : force de la tension à chaque sous-pas (petite : lacets plus souples, qui
        suivent le mouvement avec retard).'''
        self.groupes = groupes
        for g in groupes: g['trous'] = 2 if g['sorte'] == 'feuille' else 2 * g['petales'] + 1 # sépales : un de plus
        nb_trous = sum(g['trous'] for g in groupes)
        super().__init__([nb_trous - 1], hauteur, largeur) # une tresse de nb_trous brins : seul l'état de départ sert
        self.e = e = largeur / 800
        self.ecart, self.taux = ecart or 2.3 * e, taux
        clou = self.maillage.pos[self.clou]
        # la graine : les trous en rang serré sous la terre, au-dessus du clou
        self.y_graine = clou[1] - 30 * e
        self.y_sol = hauteur # pas de sol dessiné : les hauteurs des têtes sont comptées depuis le bas de l'image
        self.graine = np.array([(clou[0] + (k - (nb_trous - 1) / 2) * 10 * e, self.y_graine) for k in range(nb_trous)])
        self.premier = np.cumsum([0] + [g['trous'] for g in groupes])
        self.deplace(list(self.trous), self.graine, pas_max=2 * e, taux=0.15)
        self.y_axe = -math.inf # plus d'axe : pas de départ perpendiculaire des brins du clou (portions_du_clou vide)

    def positions(self):
        return self.maillage.pos[self.trous].copy()

    def deplace(self, sommets, cibles, pas_max, taux=None):
        '''Amène les sommets donnés en ligne droite à leurs cibles, par sous-pas d'au plus pas_max pixels, en
        retournant les arêtes et en tendant les lacets à chaque sous-pas.'''
        depart = self.maillage.pos[sommets].copy()
        n = max(1, math.ceil(np.hypot(*(np.asarray(cibles) - depart).T).max() / pas_max))
        for s in range(1, n + 1):
            self.maillage.pos[sommets] = depart + (cibles - depart) * s / n
            assert self.maillage.valide(), "triangle retourné : diminuer pas_max"
            self.maillage.delaunay(self.courbes)
            self.tend(self.taux if taux is None else taux, self.ecart)

    def phases(self, g, t):
        '''(montée, bourgeon, éclosion) de la plante g au temps t, chacune de 0 à 1.'''
        t = t - g['depart']
        montee = lisse(t / g['duree_montee'])
        bourgeon = lisse((t - g['duree_montee']) / g.get('duree_bourgeon', 1))
        eclosion = lisse((t - g['duree_montee'] - g.get('duree_bourgeon', 0)) / g['duree_eclosion'])
        return montee, bourgeon, eclosion

    def centre(self, n, t):
        '''Centre de la plante n au temps t : de la graine à sa tête le long d'une tige courbe (Bézier), en oscillant
        un peu (nutation : les plantes tournent sur elles-mêmes en poussant).'''
        g = self.groupes[n]
        graine = self.graine[self.premier[n]:self.premier[n + 1]].mean(axis=0)
        tete = np.array((g['tete'][0] * self.e, self.y_sol - g['tete'][1] * self.e))
        controle = np.array((graine[0] + g.get('courbure', 0.15) * (tete[0] - graine[0]), (graine[1] + tete[1]) / 2))
        montee = self.phases(g, t)[0]
        centre = bezier(graine, controle, tete, montee)
        return centre + np.array((g['nutation'] * self.e * math.sin(2 * math.pi * t / 2.7 + n) * math.sin(math.pi * montee), 0))

    def direction_de_tige(self, n):
        '''Direction (unitaire) de la tige sous la tête de la plante n : celle de la courbe de Bézier à son arrivée,
        retournée.'''
        g = self.groupes[n]
        graine = self.graine[self.premier[n]:self.premier[n + 1]].mean(axis=0)
        tete = np.array((g['tete'][0] * self.e, self.y_sol - g['tete'][1] * self.e))
        controle = np.array((graine[0] + g.get('courbure', 0.15) * (tete[0] - graine[0]), (graine[1] + tete[1]) / 2))
        d = controle - tete
        return d / math.hypot(*d)

    def secteur_de_fleur(self, ctx, n, t):
        '''Chemin de la région où l'on peint la fleur n : grand disque autour de la tête privé d'un coin de 50° dans
        la direction de la tige, ce coin ne commençant qu'au-delà des sépales (la couleur ne descend pas sur la tige,
        et le vert de la tige ne monte pas jusqu'au cœur de la fleur). Chemin simple : grand arc hors du coin,
        rentrée le long d'un bord du coin, petit arc en travers du coin, sortie le long de l'autre bord.'''
        g = self.groupes[n]
        centre, R = self.centre(n, t), 2.6 * g['rayon_fleur'] * self.e
        r = 1.1 * g['rayon_sepales'] * self.e
        tige = math.atan2(*self.direction_de_tige(n)[::-1])
        demi = math.radians(25)
        ctx.arc(*centre, R, tige + demi, tige - demi + 2 * math.pi)
        ctx.arc(*centre, r, tige - demi, tige + demi)
        ctx.close_path()

    def trous_de_fleur(self, n, t):
        '''Trous de la fleur n, rangés par angle décroissant de 250° à -70° (le bas reste ouvert pour la tige ; les
        sépales du bas sont près de l'axe de la tige, pour que leurs lacets longent le faisceau) :
        sépales (rangs pairs) et pétales (rangs impairs) en alternance. Les sépales forment une cage qui ne tourne pas,
        les pétales sont à l'intérieur, sur le petit cercle du bourgeon. Pendant la montée, tous passent du rang de la
        graine à un demi-cercle ouvert vers le haut (dans l'ordre de la graine, sans croisement), puis à cette
        disposition. Le bourgeon : seuls les pétales tournent d'un nombre entier de tours (les lacets s'enroulent en
        couches à l'intérieur de la cage). L'éclosion : les pétales sortent entre les sépales ; les couches, retenues
        par les sépales, gonflent en lobes entre eux.'''
        g = self.groupes[n]
        m = g['trous']
        montee, bourgeon, eclosion = self.phases(g, t)
        centre = self.centre(n, t)
        cercle = lisse(montee * 1.6 - 0.6) # le demi-cercle prend la disposition de la fleur en fin de montée
        rotation = g['sens'] * 2 * math.pi * g['tours'] * bourgeon
        resultat = []
        for j in range(m):
            demi = math.pi - math.pi * j / (m - 1)
            final = math.radians(250 - 320 * j / (m - 1))
            a = (1 - cercle) * demi + cercle * final
            if j % 2 == 0: # sépale
                rayon = (1 - cercle) * g['rayon_bourgeon'] + cercle * g['rayon_sepales']
            else: # pétale
                a += rotation
                rayon = g['rayon_bourgeon'] + eclosion * (g['rayon_fleur'] - g['rayon_bourgeon'])
            resultat.append(centre + rayon * self.e * np.array((math.cos(a), -math.sin(a))))
        return resultat

    def trous_de_feuille(self, n, t):
        '''Les deux trous d'une feuille : sur un segment orienté de la tige vers le bout de la feuille, qui s'allonge
        (la feuille grandit), le trou de gauche de la graine restant à gauche.'''
        g = self.groupes[n]
        montee, _, eclosion = self.phases(g, t)
        centre = self.centre(n, t)
        direction = np.array((math.cos(g['angle']), -math.sin(g['angle'])))
        if direction[0] < 0: direction = -direction
        longueur = (g['longueur_bourgeon'] + eclosion * (g['longueur'] - g['longueur_bourgeon'])) * self.e
        return [centre - longueur / 2 * direction, centre + longueur / 2 * direction]

    def choregraphie(self, t):
        '''Positions des trous au temps t (secondes) ; au tout début de sa montée, chaque trou part de sa place dans
        la graine.'''
        resultat = []
        for n, g in enumerate(self.groupes):
            cibles = (self.trous_de_feuille if g['sorte'] == 'feuille' else self.trous_de_fleur)(n, t)
            sortie = lisse(self.phases(g, t)[0] * 5)
            for j, cible in enumerate(cibles):
                resultat.append((1 - sortie) * self.graine[self.premier[n] + j] + sortie * cible)
        return np.array(resultat)

    def cibles(self, t):
        '''(sommets qui bougent, leurs positions au temps t) : les trous.'''
        return list(self.trous), self.choregraphie(t)

    def trace(self, ctx, points, motif, largeur):
        '''Remplit le lacet d'une couleur transparente puis le trace.'''
        ctx.move_to(*points[0])
        for p in points[1:]: ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source(motif)
        ctx.save()
        ctx.clip_preserve()
        ctx.paint_with_alpha(0.16)
        ctx.restore()
        ctx.set_line_width(largeur)
        ctx.stroke()

    def dessine(self, t, lumiere=1.0):
        '''Image au temps t : fond bleu clair (lumière légèrement variable, comme les prises de vue image par image),
        lacets remplis d'une couleur transparente et tracés : verts pour les tiges et les feuilles ; dans la fleur
        (secteur autour de la tête, sans la tige), blancs au centre puis de la couleur de la fleur, ce bicolore
        apparaissant à l'éclosion. Pas de sol : les tiges partent du bas de l'image.'''
        l, h, e = self.largeur, self.hauteur, self.e
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, l, h)
        ctx = cairo.Context(surface)
        fond = cairo.LinearGradient(0, 0, 0, h)
        fond.add_color_stop_rgb(0, *(np.array((0.62, 0.80, 0.95)) * lumiere))
        fond.add_color_stop_rgb(1, *(np.array((0.82, 0.91, 0.98)) * lumiere))
        ctx.set_source(fond)
        ctx.paint()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        largeur = 2.0 * e
        vert, sombre, blanc = np.array((0.26, 0.56, 0.24)), np.array((0.16, 0.38, 0.16)), np.array((1.0, 1.0, 1.0))
        plante_du_lacet = [n for n, g in enumerate(self.groupes) for _ in range(g['trous'])]
        for k, points in enumerate(self.polylignes()):
            n = plante_du_lacet[k]
            g = self.groupes[n]
            centre = self.centre(n, t)
            motif = cairo.RadialGradient(*centre, 0, *centre, g.get('longueur', 60) * e)
            motif.add_color_stop_rgb(0, *vert)
            motif.add_color_stop_rgb(1, *sombre)
            if g['sorte'] == 'feuille':
                self.trace(ctx, points, motif, largeur)
                continue
            # fleur : vert hors du secteur de la fleur...
            ctx.save()
            ctx.rectangle(0, 0, l, h)
            self.secteur_de_fleur(ctx, n, t)
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            ctx.clip()
            self.trace(ctx, points, motif, largeur)
            ctx.restore()
            # ... et dans le secteur, du vert du bouton au blanc et à la couleur de la fleur qui éclot
            eclosion = self.phases(g, t)[2]
            rf = g['rayon_fleur'] * e
            interieur = (1 - eclosion) * vert + eclosion * blanc
            exterieur = (1 - eclosion) * vert + eclosion * np.array(g['couleur'])
            fleur = cairo.RadialGradient(*centre, 0, *centre, 2.6 * rf)
            fleur.add_color_stop_rgb(0, *interieur)
            fleur.add_color_stop_rgb(0.21, *interieur)
            fleur.add_color_stop_rgb(0.42, *exterieur)
            fleur.add_color_stop_rgb(1, *exterieur)
            ctx.save()
            self.secteur_de_fleur(ctx, n, t)
            ctx.clip()
            self.trace(ctx, points, fleur, largeur)
            ctx.restore()
        return surface


def fleur(tete, depart, couleur, sens=1, nutation=18, **reglages):
    r = dict(sorte='fleur', tete=tete, depart=depart, couleur=couleur, sens=sens, nutation=nutation, petales=4,
             duree_montee=5.0, duree_bourgeon=2.0, duree_eclosion=3.5, tours=1, rayon_bourgeon=20, rayon_sepales=52,
             rayon_fleur=100)
    r.update(reglages)
    return r

def feuille(tete, depart, angle, longueur=80, **reglages):
    r = dict(sorte='feuille', tete=tete, depart=depart, angle=angle, longueur=longueur, longueur_bourgeon=14,
             nutation=8, duree_montee=3.5, duree_eclosion=3.0, courbure=0.5)
    r.update(reglages)
    return r

# de gauche à droite dans la graine ; têtes : (abscisse, hauteur au-dessus du sol) dans une image de 800 de large.
# Les feuilles sont aux deux bouts de la graine, tournées vers l'extérieur : entre deux fleurs, une feuille coupait le
# chemin d'une tige et la faisait plier.
BOUQUET = [
    feuille((110, 130), 1.5, math.radians(150)),
    feuille((215, 185), 2.2, math.radians(160), longueur=70),
    fleur((190, 580), 0.0, (0.92, 0.35, 0.50), sens=1),
    fleur((415, 770), 0.8, (0.97, 0.78, 0.25), sens=-1, nutation=22),
    fleur((630, 560), 1.6, (0.62, 0.42, 0.90), sens=1, nutation=16),
    feuille((595, 175), 2.6, math.radians(20), longueur=70),
    feuille((700, 120), 1.8, math.radians(30)),
]

def film_bouquet(fichier, groupes=BOUQUET, duree=13.5, images_par_seconde=25, saccade=2, pause=2.0, **options):
    '''Film MP4 du bouquet. saccade : chaque image calculée est montrée ce nombre de fois (aspect image par image des
    films de plantes qui poussent) ; lumière constante (une variation d'une image à l'autre faisait clignoter).'''
    pousse = Pousse(groupes, **options)
    l, h = pousse.largeur, pousse.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', str(images_par_seconde), '-i', '-', '-pix_fmt', 'yuv420p',
                               '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0', '-deadline', 'realtime',
                               '-cpu-used', '8', '-row-mt', '1', fichier], stdin=subprocess.PIPE)
    pas = saccade / images_par_seconde
    nombre = round(duree / pas)
    for n in range(nombre + 1):
        t = n * pas
        if n: pousse.deplace(*pousse.cibles(t), pas_max=2 * pousse.e)
        surface = pousse.dessine(t)
        surface.flush()
        donnees = bytes(surface.get_data())
        fois = saccade if n < nombre else round(pause * images_par_seconde)
        for _ in range(fois): ffmpeg.stdin.write(donnees)
    ffmpeg.stdin.close()
    ffmpeg.wait()


def image_bouquet(fichier, largeur_mm=152, hauteur_mm=205, dpi=300, t=13.5, groupes=BOUQUET, **options):
    '''Image du bouquet au temps t (fleurs écloses), pour l'impression : largeur_mm × hauteur_mm à dpi points par
    pouce (152 × 205 mm à 300 dpi : 1795 × 2421 pixels). Le film est recalculé à cette taille (toutes les longueurs
    suivent la largeur) ; JPEG ou PNG selon l'extension, avec la résolution inscrite dans le fichier.'''
    from tresses import en_image_pil
    l, h = round(largeur_mm / 25.4 * dpi), round(hauteur_mm / 25.4 * dpi)
    pousse = Pousse(groupes, hauteur=h, largeur=l, **options)
    pas = 2 / 25
    for n in range(1, round(t / pas) + 1): pousse.deplace(*pousse.cibles(n * pas), pas_max=2 * pousse.e)
    image = en_image_pil(pousse.dessine(t))
    image.save(fichier, dpi=(dpi, dpi), **({'quality': 95, 'subsampling': 0} if fichier.lower().endswith(('.jpg', '.jpeg')) else {}))


if __name__ == "__main__":
    film_bouquet('./imgs/bouquet.mp4')
