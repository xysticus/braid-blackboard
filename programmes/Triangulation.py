'''Film des lacets de l'automorphisme d'Artin par une triangulation mobile.

Les sommets sont les trous, le clou, des sommets sur les bords haut et bas (à la verticale des trous) et les
extrémités de l'axe. Un lacet est une suite de points posés sur les arêtes (à une fraction de la longueur de
l'arête), et deux points consécutifs sont dans un même triangle. Quand les trous i et i+1 tournent l'un autour
de l'autre, les sommets bougent, les points suivent leur arête, et quand une arête cesse d'être de Delaunay
(par exemple quand deux trous passent à la verticale l'un de l'autre) on la retourne : les lacets sont
recalculés dans les nouveaux triangles sans changer de forme. Les lacets sont tendus (`Film.tend`) : ils se
tassent autour des trous et vont en ligne droite d'un enroulement à l'autre. Le dessin est la ligne brisée des
points dont chaque coude est arrondi par un arc de cercle (congé) : des droites et des arcs, les enroulements
étant des cercles autour des trous ; les brins attachés au clou partent de l'axe perpendiculairement.'''

import math, operator, subprocess
import numpy as np

from tresses import (calcule_autofn_de_tresse, etat_de_tresse, intervalle, agit, dessin_etat, polylignes,
                     lit_mot, peint, deux_arcs, en_image_pil)

DECALAGE_AXE = 0.01 # les trous sont un peu sous l'axe de dessin : les points de passage sont strictement au-dessus
DECALAGE_BORD = 0.31 # les sommets des bords ne sont pas exactement à la verticale des trous (le clou y serait)


def croix(u, v): return u[0] * v[1] - u[1] * v[0]

def monotone(valeurs):
    '''Régression monotone croissante (moindres carrés) des valeurs, par mise en commun des blocs voisins.'''
    blocs = []
    for x in valeurs:
        blocs.append([x, 1])
        while len(blocs) > 1 and blocs[-2][0] > blocs[-1][0]:
            (a, na), (b, nb) = blocs[-2], blocs[-1]
            blocs[-2:] = [[(a * na + b * nb) / (na + nb), na + nb]]
    return [moyenne for moyenne, n in blocs for _ in range(n)]

class Maillage:
    '''Triangulation d'un nuage de points : positions et triangles (ensembles de trois indices).'''

    def __init__(self, pos, triangles):
        self.pos = np.array(pos, dtype=float)
        self.triangles = {frozenset(t) for t in triangles}
        self.signes = {t: self.signe(t) for t in self.triangles}

    def signe(self, t):
        a, b, c = sorted(t)
        return 1 if croix(self.pos[b] - self.pos[a], self.pos[c] - self.pos[a]) > 0 else -1

    def aretes(self):
        '''{arête (u, v) avec u < v : triangles qui la bordent}'''
        resultat = {}
        for t in self.triangles:
            a, b, c = sorted(t)
            for e in ((a, b), (a, c), (b, c)): resultat.setdefault(e, []).append(t)
        return resultat

    def valide(self):
        '''Aucun triangle retourné.'''
        return all(self.signe(t) == s for t, s in self.signes.items())

    def convexe(self, a, b, c, d):
        '''Le quadrilatère a, b, c, d est strictement convexe.'''
        p = self.pos
        s = [croix(p[y] - p[x], p[z] - p[y]) for x, y, z in ((a, b, c), (b, c, d), (c, d, a), (d, a, b))]
        return all(x > 1e-9 for x in s) or all(x < -1e-9 for x in s)

    def cotangente(self, sommet, x, y):
        u, v = self.pos[x] - self.pos[sommet], self.pos[y] - self.pos[sommet]
        return (u @ v) / max(abs(croix(u, v)), 1e-12)

    def cherche_arete_a_retourner(self):
        '''Une arête intérieure qui n'est pas de Delaunay (angles opposés de somme > π) et dont on peut
        retourner le quadrilatère, ou None.'''
        for (a, c), tris in self.aretes().items():
            if len(tris) != 2: continue
            b, d = [next(iter(t - {a, c})) for t in tris]
            if self.cotangente(b, a, c) + self.cotangente(d, a, c) >= -1e-9: continue
            if not self.convexe(a, b, c, d): continue
            if any(set(e) == {b, d} for e in self.aretes()): continue
            return a, b, c, d
        return None

    def retourne(self, a, b, c, d, courbes):
        '''Remplace la diagonale ac du quadrilatère abcd par bd ; les courbes sont mises à jour sur place.'''
        self.triangles -= {frozenset((a, b, c)), frozenset((a, c, d))}
        for t in (frozenset((a, b, d)), frozenset((b, c, d))):
            self.triangles.add(t)
            self.signes[t] = self.signe(t)
        for t in list(self.signes):
            if t not in self.triangles: del self.signes[t]
        for k, courbe in enumerate(courbes): courbes[k] = self.courbe_apres_flip(courbe, a, b, c, d)

    def position(self, noeud):
        if noeud[0] == 'v': return self.pos[noeud[1]]
        _, u, v, w = noeud
        return (1 - w) * self.pos[u] + w * self.pos[v]

    def courbe_apres_flip(self, courbe, a, b, c, d):
        '''Une courbe est une liste de noeuds ('v', sommet) ou ('e', u, v, w) (u < v, w : fraction de u vers v),
        deux noeuds consécutifs étant dans un même triangle. Après le flip ac → bd, les points de ac disparaissent
        (la corde relie leurs voisins) et chaque corde qui sépare {ab, da} de {bc, cd} (côtés des deux
        nouveaux triangles) coupe bd en un point nouveau.'''
        e = (min(a, c), max(a, c))
        groupe_arete = {frozenset((a, b)): 0, frozenset((d, a)): 0, frozenset((b, c)): 1, frozenset((c, d)): 1}
        groupe_sommet = {a: 0, c: 1, b: 2, d: 2}
        def groupe(n):
            return groupe_sommet.get(n[1]) if n[0] == 'v' else groupe_arete.get(frozenset(n[1:3]))
        sans = [n for n in courbe if not (n[0] == 'e' and n[1:3] == e)]
        resultat = [sans[0]]
        for u, v in zip(sans[:-1], sans[1:]):
            gu, gv = groupe(u), groupe(v)
            if gu in (0, 1) and gv in (0, 1) and gu != gv:
                resultat.append(self.coupe(u, v, b, d))
            resultat.append(v)
        return resultat

    def coupe(self, u, v, b, d):
        '''Noeud où la corde de u à v coupe l'arête bd.'''
        p, q = self.position(u), self.position(v)
        x, y = (b, d) if b < d else (d, b)
        s = self.pos[y] - self.pos[x]
        r = q - p
        den = croix(r, s)
        w = croix(self.pos[x] - p, r) / den
        assert -1e-6 < w < 1 + 1e-6, "la corde ne coupe pas la nouvelle diagonale"
        return ('e', x, y, min(max(w, 1e-6), 1 - 1e-6))

    def delaunay(self, courbes):
        '''Retourne les arêtes qui ne sont pas de Delaunay jusqu'à ce qu'il n'y en ait plus.'''
        for _ in range(10000):
            quad = self.cherche_arete_a_retourner()
            if quad is None: return
            self.retourne(*quad, courbes)
        raise RuntimeError("les flips ne s'arrêtent pas")


def maillage_initial(trous, clou, hauteur, largeur, decalage_bas=DECALAGE_BORD):
    '''Triangulation de départ en deux bandes horizontales, rangées de haut en bas :
    - le bord haut, un sommet à la verticale de chaque trou (et les coins) ;
    - l'axe (extrémités et trous) : entre les deux, la bande des arcs du haut ;
    - le bord bas, avec le clou dessus et un sommet à la verticale de chaque trou (et les coins) : entre l'axe et lui,
    la bande des arcs du bas, où arrivent aussi les brins du clou.
    Chaque bande est découpée en une échelle de triangles (zigzag entre les deux rangées), puis les arêtes non de
    Delaunay sont retournées (le clou peut gagner des arêtes). Les sommets du bord bas sont décalés de decalage_bas
    pour ne pas être trop près du clou.
    Les rangées alignées (haut et bas) ont les coins en plus : indice k + 1 pour le trou k.
    Renvoie (maillage, indices des trous, du clou, rangée alignée du haut, du bas).'''
    y_axe = trous[0][1] + DECALAGE_AXE
    xs_alignes = [0] + [x + DECALAGE_BORD for x, _ in trous] + [largeur]
    xs_bas = [0] + [x + decalage_bas for x, _ in trous] + [largeur]
    pts = []
    def ajoute(p): pts.append(p); return len(pts) - 1
    def rangee(y, xs): return [ajoute((x, y)) for x in xs]

    haut = rangee(3, xs_alignes)
    axe = [ajoute((0, y_axe))] + [ajoute((x, y_axe)) for x, _ in trous] + [ajoute((largeur, y_axe))]
    nail = ajoute(tuple(clou))
    bas = [ajoute((x, clou[1])) for x in xs_bas]
    triangles = []
    for r1, r2 in zip((haut, axe), (axe, bas + [nail])):
        r1 = sorted(r1, key=lambda i: pts[i][0])
        r2 = sorted(r2, key=lambda i: pts[i][0])
        i = j = 0
        while i < len(r1) - 1 or j < len(r2) - 1:
            avance_1 = j == len(r2) - 1 or (i < len(r1) - 1 and pts[r1[i + 1]][0] <= pts[r2[j + 1]][0])
            if avance_1: triangles.append((r1[i], r1[i + 1], r2[j])); i += 1
            else: triangles.append((r1[i], r2[j], r2[j + 1])); j += 1
    m = Maillage(pts, triangles)
    m.delaunay([])
    return m, axe[1:-1], nail, haut, bas


def noeuds_de_polyligne(points, maillage, clou):
    '''Suite des arêtes coupées par une polyligne qui part et arrive au clou (bigones retirés).'''
    aretes = list(maillage.aretes())
    p, q = points[:-1], points[1:]
    r = q - p
    trouves = []
    for (u, v) in aretes:
        s = maillage.pos[v] - maillage.pos[u]
        den = r[:, 0] * s[1] - r[:, 1] * s[0]
        ok = np.abs(den) > 1e-12
        den = np.where(ok, den, 1)
        du = maillage.pos[u] - p
        t = (du[:, 0] * s[1] - du[:, 1] * s[0]) / den
        w = (du[:, 0] * r[:, 1] - du[:, 1] * r[:, 0]) / den
        sel = ok & (t >= 0) & (t < 1) & (w >= 0) & (w < 1)
        if clou in (u, v): sel[0] = sel[-1] = False
        for k in np.nonzero(sel)[0]: trouves.append((k, t[k], ('e', u, v, w[k])))
    trouves.sort(key=lambda x: (x[0], x[1]))
    pile = []
    for _, _, noeud in trouves:
        if pile and pile[-1][1:3] == noeud[1:3]: pile.pop()
        else: pile.append(noeud)
    return [('v', clou)] + pile + [('v', clou)]


class Film:
    '''Les trous en mouvement, leur triangulation et les lacets posés dessus.'''

    def __init__(self, tresse, hauteur=800, largeur=800):
        self.hauteur, self.largeur = hauteur, largeur
        e = largeur / 400 # échelle des longueurs en pixels (réglées pour 400 × 400)
        self.nb_trous = max(map(operator.abs, tresse), default=1) + 1
        self.dispositions = [self.disposition(etat_de_tresse(tresse[:k], self.nb_trous))
                             for k in range(len(tresse) + 1)]
        # au milieu de chaque lettre : l'état non réduit compte les brins qui passent de chaque côté du bloc
        # pendant le demi-tour (ils doivent y trouver leur place)
        self.milieux = [self.disposition(agit(etat_de_tresse(tresse[:k], self.nb_trous), sigma))
                        for k, sigma in enumerate(tresse)]
        self.etape = 0 # indice de l'image clé courante
        morceaux, trous, clou, _ = dessin_etat(etat_de_tresse([], self.nb_trous), hauteur, largeur)
        # le dessin de départ est replacé sur la disposition de l'image clé 0 : les abscisses sont transformées
        # par la fonction croissante affine par morceaux qui envoie les anciens trous sur les nouveaux
        xs0 = self.dispositions[0][0]
        avant, apres = [0] + [x for x, _ in trous] + [largeur], [0] + xs0 + [largeur]
        lignes = polylignes(morceaux)
        for p in lignes: p[:, 0] = np.interp(p[:, 0], avant, apres)
        clou = (float(np.interp(clou[0], avant, apres)), clou[1])
        trous = [(x, trous[0][1]) for x in xs0]
        self.decalage_bas = next(d for d in (DECALAGE_BORD, 12 * e, -12 * e) if all(abs(x + d - clou[0]) >= 8 * e for x in xs0))
        self.maillage, self.trous, self.clou, self.haut, self.bas = maillage_initial(
            trous, clou, hauteur, largeur, self.decalage_bas)
        self.y_axe = self.maillage.pos[self.trous[0]][1]
        # le clou garde sa place relative entre les deux sommets du bord bas qui l'encadrent
        xs_bas = [self.maillage.pos[i][0] for i in self.bas]
        j = max(k for k in range(len(xs_bas) - 1) if xs_bas[k] <= clou[0])
        self.place_du_clou = (j, (clou[0] - xs_bas[j]) / (xs_bas[j + 1] - xs_bas[j]))
        # le dessin de départ est aplati : on l'étire au-dessus de l'axe pour qu'il occupe la bande du haut
        y_min = min(p[:, 1].min() for p in lignes)
        etirement = (self.y_axe - 14 * e) / (self.y_axe - y_min)
        for p in lignes: p[:, 1] = np.where(p[:, 1] < self.y_axe, self.y_axe - (self.y_axe - p[:, 1]) * etirement, p[:, 1])
        self.courbes = [noeuds_de_polyligne(p, self.maillage, self.clou) for p in lignes]
        # la tension s'applique dès la première image : pas de lacets lâches au départ
        for _ in range(400): self.tend(0.3, self.dispositions[0][1])

    def disposition(self, etat):
        '''(abscisses des trous, écart entre brins) pour un état (celui d'une image clé, ou l'état non réduit du
        milieu d'une lettre) : la largeur de chaque intervalle de l'axe (y compris les deux de gauche et de droite)
        est proportionnelle à 1 + le nombre de brins qui le traversent, donc l'écart entre deux points consécutifs
        de l'axe (et entre deux brins ailleurs) est le même partout.'''
        trous, lacets = etat
        comptes = [0] * (self.nb_trous + 1)
        for lacet in lacets:
            for x in lacet: comptes[intervalle(x, trous)] += 1
        ecart = self.largeur / sum(c + 1 for c in comptes)
        xs, cumul = [], 0
        for c in comptes[:-1]:
            cumul += (c + 1) * ecart
            xs.append(cumul)
        return xs, ecart

    def portions_du_clou(self, courbe):
        '''Pour une courbe, les deux bouts attachés au clou : [(indices des points avant le premier passage sur
        l'axe, abscisse de ce passage), (indices après le dernier, abscisse)].'''
        pts = [self.maillage.position(n) for n in courbe]
        def passage(i, j):
            (x1, y1), (x2, y2) = pts[i], pts[j]
            return x1 + (x2 - x1) * (self.y_axe - y1) / (y2 - y1) if abs(y2 - y1) > 1e-12 else x2
        haut = [i for i, q in enumerate(pts) if q[1] <= self.y_axe]
        if not haut: return []
        i1, i2 = haut[0], haut[-1]
        return [(range(1, i1), passage(i1 - 1, i1)), (range(i2 + 1, len(pts) - 1), passage(i2 + 1, i2))]

    def tend(self, taux, ecart, degagement=None):
        '''Un pas de tension des lacets. Chaque point est tiré, d'une fraction taux du chemin, vers sa cible sur son
        arête : l'endroit où ses deux voisins sont alignés avec lui (le brin se tend). Puis, arête par arête,
        les points gardent leur ordre et restent à `ecart` pixels les uns des autres perpendiculairement aux brins
        (donc à ecart / sinus le long d'une arête traversée en biais, sinus borné à 0,3) et à `degagement` (par
        défaut ecart) pixels des sommets (projection d'une régression monotone bornée), moins si l'arête est trop
        courte.
        Les brins se tassent donc à écart fixe là où ils sont tirés, près des trous, et laissent du vide au-delà ;
        l'ordre sur chaque arête ne change pas, donc aucun croisement.'''
        degagement = ecart if degagement is None else degagement
        pos = self.maillage.pos
        par_arete = {}
        for k, courbe in enumerate(self.courbes):
            for i, n in enumerate(courbe):
                if n[0] != 'e': continue
                u, v, w = n[1], n[2], n[3]
                d = pos[v] - pos[u]
                p, q = self.maillage.position(courbe[i - 1]), self.maillage.position(courbe[i + 1])
                den = croix(d, q - p)
                cible = croix(p - pos[u], q - p) / den if abs(den) > 1e-9 else w
                # sinus de l'angle sous lequel le brin traverse l'arête
                sinus = abs(den) / max(math.hypot(*d) * math.hypot(*(q - p)), 1e-12)
                par_arete.setdefault((u, v), []).append((w + taux * (min(max(cible, 0), 1) - w), k, i, sinus))
        for (u, v), liste in par_arete.items():
            longueur = math.hypot(*(pos[v] - pos[u]))
            liste.sort()
            m = len(liste)
            marge = min(degagement, 0.3 * longueur)
            # écart le long de l'arête entre deux points voisins : ecart / sinus, pour que les brins restent à ecart
            # l'un de l'autre perpendiculairement même s'ils traversent l'arête en biais (triangle plat)
            ecarts = [ecart / max((liste[j - 1][3] + liste[j][3]) / 2, 0.3) for j in range(1, m)]
            place = max(longueur - 2 * marge, 0)
            if sum(ecarts) > place * m / (m + 1): # pas la place : on réduit tous les écarts
                ecarts = [g * place * m / (m + 1) / sum(ecarts) for g in ecarts]
            cumul = [0.0]
            for g in ecarts: cumul.append(cumul[-1] + g)
            cibles = [liste[j][0] * longueur - cumul[j] for j in range(m)]
            finals = [min(max(x, marge), longueur - marge - cumul[-1]) + cumul[j] for j, x in enumerate(monotone(cibles))]
            for j, final in enumerate(finals):
                _, k, i, _ = liste[j]
                self.courbes[k][i] = ('e', u, v, final / longueur)

    def polyligne(self, k, lisse=True, part_du_conge=0.5):
        '''Polyligne dessinée de la courbe k : la ligne brisée de ses points, dont chaque coude est arrondi par un
        congé, arc de cercle tangent aux deux segments, qui en prend au plus `part_du_conge` (la moitié par défaut :
        deux congés voisins se touchent sans se chevaucher). Le dessin n'est fait que de droites et d'arcs, sans
        point d'inflexion : un brin tendu reste droit jusqu'à son coude, les enroulements, faits de petits coudes
        réguliers autour d'un trou, sont des cercles. (Avec une direction par point et une paire d'arcs par segment,
        un brin droit qui tourne d'un coup en un point fait un S dans le segment qui précède.)
        Les brins attachés au clou partent de l'axe perpendiculairement : leur premier (dernier) passage sur l'axe
        est remplacé par deux points de part et d'autre de l'axe, sur la verticale si le brin traverse l'axe à peu
        près verticalement (pendant un demi-tour il peut le traverser en biais : on suit alors sa direction).'''
        courbe = self.courbes[k]
        pts = [self.maillage.position(n) for n in courbe]
        if not lisse: return np.array(pts)
        # passages sur l'axe des brins du clou : le premier est entre les points i1 - 1 et i1
        # (indices = range(1, i1)), le dernier entre i2 et i2 + 1 (indices = range(i2 + 1, ...))
        insertions = []
        for n, (indices, x) in enumerate(self.portions_du_clou(courbe)):
            i = indices.stop if n == 0 else indices.start
            insertions.append((i, np.array((x, self.y_axe)), n == 0))
        ecart = self.dispositions[self.etape][1]
        for i, q, premier in sorted(insertions, key=lambda e: -e[0]):
            voisins = min(abs(q[1] - pts[i - 1][1]), abs(q[1] - pts[i][1]))
            if voisins < 1e-6: continue
            # direction au passage : la verticale si le brin traverse l'axe à moins de 45° de la verticale (poids
            # décroissant avec l'angle), sinon celle du brin : on ne crée pas de cran pendant les demi-tours
            segment = pts[i] - pts[i - 1]
            segment = segment / math.hypot(*segment)
            verticale = np.array((0.0, math.copysign(1.0, segment[1])))
            poids = max(0.0, 1 - math.acos(min(1.0, abs(segment[1]))) / (math.pi / 4))
            d = poids * verticale + (1 - poids) * segment
            d = d / math.hypot(*d)
            delta = min(ecart, 0.3 * voisins) / max(abs(d[1]), 1e-3)
            pts[i:i] = [q - delta * d, q + delta * d]
        dessin = [pts[0]]
        for a, v, b in zip(pts[:-2], pts[1:-1], pts[2:]):
            la, lb = math.hypot(*(a - v)), math.hypot(*(b - v))
            if la < 1e-9 or lb < 1e-9:
                dessin.append(v)
                continue
            ua, ub = (a - v) / la, (b - v) / lb
            if ua @ ub < -1 + 1e-9: # pas de coude
                dessin.append(v)
                continue
            c = part_du_conge * min(la, lb)
            p1, p2 = v + c * ua, v + c * ub
            dessin.extend(deux_arcs(p1, -ua, p2, ub))
        dessin.append(pts[-1])
        return np.array(dessin)

    def polylignes(self, lisse=True):
        return [self.polyligne(k, lisse) for k in range(len(self.courbes))]

    def positions_des_trous(self):
        return self.maillage.pos[self.trous]

    def mots(self, lisse=True):
        trous = sorted(map(tuple, self.positions_des_trous()))
        return [lit_mot(p, trous) for p in self.polylignes(lisse)]

    def cadre(self, lisse=True, largeur_brin=None, avec_arêtes=True, ecart=None):
        if largeur_brin is None: largeur_brin = 3 * self.largeur / 400
        if ecart is not None: largeur_brin = min(largeur_brin, max(1, 0.7 * ecart)) # brins serrés : trait plus fin
        arêtes = [self.maillage.pos[list(e)] for e in self.maillage.aretes()] if avec_arêtes else None
        return peint(self.polylignes(lisse), self.positions_des_trous(), self.maillage.pos[self.clou],
                     self.hauteur, self.largeur, largeur_brin, axe=arêtes)

    def trous_au_temps(self, sigma, u):
        '''(positions des trous de gauche à droite au temps u de la lettre σ, abscisses des places, milieu et rayon
        du demi-tour, angle) : les trous glissent de la disposition de l'image clé courante à celle du milieu de la
        lettre puis à celle de l'image clé suivante (`abscisses`), et les deux trous de σ font en plus un demi-tour
        autour de leur milieu. Ne modifie rien.'''
        i = abs(sigma) - 1
        x = self.abscisses(u)[0] # abscisses de chaque place, de gauche à droite
        milieu, r = (x[i] + x[i + 1]) / 2, (x[i + 1] - x[i]) / 2
        theta = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * u
        positions = np.array([(xj, self.y_axe) for xj in x])
        positions[i] = (milieu - r * math.cos(theta), self.y_axe - r * math.sin(theta))
        positions[i + 1] = (milieu + r * math.cos(theta), self.y_axe + r * math.sin(theta))
        return positions, x, milieu, r, theta

    def place(self, sigma, u):
        '''Place les sommets au temps u de la lettre σ (`trous_au_temps`) ; à u = 1, les deux trous de σ échangent
        leurs places et l'on passe à l'image clé suivante.'''
        m, i, n = self.maillage, abs(sigma) - 1, self.nb_trous
        positions, x, milieu, r, theta = self.trous_au_temps(sigma, u)
        for j, h in enumerate(self.trous): m.pos[h] = positions[j]
        # les sommets des bords se croisent sans jamais se rejoindre
        ecart = math.hypot(r * math.cos(theta), 0.4 * r * math.sin(theta))
        bords = list(x)
        bords[i], bords[i + 1] = milieu - ecart, milieu + ecart
        for rangee, decalage in ((self.haut, DECALAGE_BORD), (self.bas, self.decalage_bas)):
            for j in range(n): m.pos[rangee[j + 1]][0] = bords[j] + decalage
        j, f = self.place_du_clou
        m.pos[self.clou][0] = m.pos[self.bas[j]][0] + f * (m.pos[self.bas[j + 1]][0] - m.pos[self.bas[j]][0])
        if u == 1:
            xs1 = self.dispositions[self.etape + 1][0]
            a, b = self.trous[i], self.trous[i + 1]
            m.pos[a], m.pos[b] = (xs1[i + 1], self.y_axe), (xs1[i], self.y_axe)
            self.trous[i], self.trous[i + 1] = b, a
            self.etape += 1

    def abscisses(self, u):
        '''(abscisses des places, écart) au temps u de la lettre courante : interpolation linéaire de l'image clé
        à la disposition du milieu de la lettre pendant la première moitié, puis de celle-ci à l'image clé suivante
        (linéaire : un adoucissement arrêterait les trous au milieu et aux bouts de la lettre ; une interpolation
        courbe pourrait intervertir deux trous voisins).'''
        (xa, ea), (xm, em), (xb, eb) = self.dispositions[self.etape], self.milieux[self.etape], \
            self.dispositions[self.etape + 1]
        if u <= 0.5: (x0, e0), (x1, e1), v = (xa, ea), (xm, em), 2 * u
        else: (x0, e0), (x1, e1), v = (xm, em), (xb, eb), 2 * u - 1
        return [(1 - v) * a + v * b for a, b in zip(x0, x1)], (1 - v) * e0 + v * e1

    def chemin_des_trous(self, sigma, echantillons=800):
        '''(temps u échantillonnés, longueur cumulée du chemin parcouru par l'ensemble des trous) pendant la lettre σ.'''
        us = np.linspace(0, 1, echantillons + 1)
        positions = np.array([self.trous_au_temps(sigma, u)[0] for u in us])
        pas = np.hypot(*np.moveaxis(np.diff(positions, axis=0), 2, 0)).sum(axis=1)
        return us, np.concatenate(([0], np.cumsum(pas)))

    def lettre(self, sigma, images=None, sous_pas=2, taux=0.15, largeur_brin=None, rendu=None, vitesse=None):
        '''Un demi-tour (σ_i : sens de SENS_DE_SIGMA). Les trous avancent à vitesse constante : le temps de la lettre
        est reparamétré par la longueur du chemin parcouru par l'ensemble des trous, et sans `images` imposé, la
        lettre dure (longueur du chemin) / vitesse images (vitesse en pixels par image, par défaut VITESSE à
        l'échelle de la largeur) : les petits mouvements sont courts, les grands longs, sans à-coup d'une lettre à
        l'autre. rendu : fonction appelée avec chaque image (surface Cairo) ; sans elle, rien n'est dessiné.
        Renvoie le nombre d'images.'''
        us, longueurs = self.chemin_des_trous(sigma)
        if images is None:
            vitesse = vitesse or VITESSE * self.largeur / 800
            images = max(4, round(longueurs[-1] / vitesse))
        temps = np.interp(np.linspace(0, longueurs[-1], images * sous_pas + 1)[1:], longueurs, us)
        temps[-1] = 1.0
        for pas, u in enumerate(temps, 1):
            ecart = self.abscisses(u)[1]
            self.place(sigma, u)
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            self.tend(taux, ecart)
            if rendu and pas % sous_pas == 0: rendu(self.cadre(largeur_brin=largeur_brin, ecart=ecart))
        return images


SENS_DE_SIGMA = 1
VITESSE = 6 # pixels parcourus par l'ensemble des trous à chaque image (pour 800 pixels de large)


def verifie_triangulation(tresse, images=12, **options):
    '''Après chaque lettre, les mots relus sur le dessin sont ceux de calcule_autofn_de_tresse
    (dessin en arcs de cercle et en cordes).'''
    film = Film(tresse, **options)
    for k, sigma in enumerate(tresse):
        film.lettre(sigma, images)
        attendu = calcule_autofn_de_tresse(tresse[:k + 1], film.nb_trous)
        if film.mots() != attendu or film.mots(False) != attendu: return False
    return True

def film_triangule(tresse, fichier, vitesse=None, pause=0.5, largeur_brin=None, **options):
    '''Film MP4 (VP9, 25 images/s), écrit au fil du calcul par ffmpeg : un demi-tour continu par lettre, les trous
    avançant à vitesse constante (`Film.lettre`), donc la durée d'une lettre est proportionnelle au chemin parcouru
    par les trous. Pas de pause entre les lettres ; `pause` secondes sur la première image, trois fois plus sur la
    dernière. Triangulation en gris.'''
    film = Film(tresse, **options)
    l, h = film.largeur, film.hauteur
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra',
                               '-s', f'{l}x{h}', '-r', '25', '-i', '-', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                               '-pix_fmt', 'yuv420p', '-c:v', 'libvpx-vp9', '-crf', '24', '-b:v', '0',
                               '-deadline', 'realtime', '-cpu-used', '8', '-row-mt', '1', fichier],
                              stdin=subprocess.PIPE)
    def ecrit(surface, fois=1):
        surface.flush()
        donnees = bytes(surface.get_data())
        for _ in range(fois): ffmpeg.stdin.write(donnees)
    ecrit(film.cadre(largeur_brin=largeur_brin, ecart=film.dispositions[0][1]), round(25 * pause))
    derniere = []
    def rendu(surface):
        if derniere: ecrit(derniere.pop())
        derniere.append(surface)
    for sigma in tresse: film.lettre(sigma, largeur_brin=largeur_brin, rendu=rendu, vitesse=vitesse)
    ecrit(derniere.pop(), round(25 * 3 * pause))
    ffmpeg.stdin.close()
    ffmpeg.wait()

if __name__ == "__main__":
    # tests et exemples, lancés seulement quand le script est exécuté (pas à l'import) ; depuis la racine du dépôt
    assert verifie_triangulation([1])
    assert verifie_triangulation([1, -2, 1])
    assert verifie_triangulation([4, 3, -1, -1, 2, -4, 1])
    film_triangule([4, 3, -1, -1, 2, -4, 1], './imgs/film_triangule_43m1m12m41.mp4')
    film_triangule([1, -2, 1, -2, 1, -2, 3, -1, 2], './imgs/film_triangule_charge.mp4')
