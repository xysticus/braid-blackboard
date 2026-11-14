'''Film des lacets de l'automorphisme d'Artin par une triangulation mobile.

Les sommets sont les trous, le clou, des sommets sur les bords haut et bas (à la verticale des trous) et les
extrémités de l'axe. Un lacet est une suite de points posés sur les arêtes (à une fraction de la longueur de
l'arête), et deux points consécutifs sont dans un même triangle. Quand les trous i et i+1 tournent l'un autour
de l'autre, les sommets bougent, les points suivent leur arête, et quand une arête cesse d'être de Delaunay
(par exemple quand deux trous passent à la verticale l'un de l'autre) on la retourne : les lacets sont
recalculés dans les nouveaux triangles sans changer de forme. Les lacets sont tendus (`Film.tend`) : ils se
tassent autour des trous et vont en ligne droite d'un enroulement à l'autre. Le dessin est tracé en arcs de cercle
(`deux_arcs`) entre les points des arêtes, un par triangle traversé : arcs centrés sur le trou pour les
enroulements, droites pour les brins tendus ; les brins attachés au clou partent de l'axe perpendiculairement.'''

import math, operator, os, subprocess
import numpy as np
import cairo

# Les fonctions de NouvAutoMorph.py : le script lance ses films à la fin du fichier, on n'en charge que le début.
_chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NouvAutoMorph.py')
with open(_chemin, encoding='utf-8') as _f:
    _source = _f.read().split("dessine_auto_de_tresse([1, 1, 2, 2]")[0]
exec(compile(_source, _chemin, 'exec'))

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
        self.dispositions = [self.disposition(tresse[:k]) for k in range(len(tresse) + 1)]
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

    def disposition(self, tresse):
        '''(abscisses des trous, écart entre brins) de l'image clé de la tresse : la largeur de chaque intervalle de
        l'axe (y compris les deux de gauche et de droite) est proportionnelle à 1 + le nombre de brins qui le
        traversent, donc l'écart entre deux points consécutifs de l'axe (et entre deux brins ailleurs) est le même
        partout.'''
        trous, lacets = etat_de_tresse(tresse, self.nb_trous)
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
        les points gardent leur ordre et restent à `ecart` pixels les uns des autres et à `degagement` (par défaut
        ecart) pixels des sommets (projection d'une régression monotone bornée), moins si l'arête est trop courte.
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
                par_arete.setdefault((u, v), []).append((w + taux * (min(max(cible, 0), 1) - w), k, i))
        for (u, v), liste in par_arete.items():
            longueur = math.hypot(*(pos[v] - pos[u]))
            liste.sort()
            m = len(liste)
            marge = min(degagement, 0.3 * longueur)
            g = min(ecart, max(longueur - 2 * marge, 0) / (m + 1))
            cibles = [w * longueur - j * g for j, (w, _, _) in enumerate(liste)]
            finals = [min(max(x, marge), longueur - marge - (m - 1) * g) + j * g for j, x in enumerate(monotone(cibles))]
            for j, final in enumerate(finals):
                _, k, i = liste[j]
                self.courbes[k][i] = ('e', u, v, final / longueur)

    def polyligne(self, k, lisse=True):
        '''Polyligne dessinée de la courbe k : une paire d'arcs de cercle raccordés avec la même tangente
        (`deux_arcs`) entre deux points consécutifs, la direction en un point étant celle de la corde entre ses deux
        voisins. Autour d'un trou, les points sont à égale distance sur des arêtes qui rayonnent : cette corde est
        perpendiculaire au rayon et les enroulements sont des arcs de cercle centrés sur le trou ; un brin tendu
        entre deux enroulements est droit. (Imposer la perpendiculaire au rayon aux seuls points « plaqués » contre le
        trou fait davantage de croisements : deux brins voisins d'un faisceau qui quitte un enroulement n'ont pas le
        même statut.) Les brins attachés au clou partent
        de l'axe perpendiculairement : on ajoute leur premier (dernier) passage sur l'axe, avec la verticale pour
        direction.'''
        courbe = self.courbes[k]
        pts = [self.maillage.position(n) for n in courbe]
        if not lisse: return np.array(pts)
        directions = [None] * len(pts) # None : direction de la corde entre les voisins
        # passages sur l'axe des brins du clou, insérés entre deux points (de la fin vers le début)
        insertions = []
        # le premier passage est entre les points i1 - 1 et i1 (indices = range(1, i1)), le dernier entre i2 et
        # i2 + 1 (indices = range(i2 + 1, ...)) : on l'insère à l'indice i1, ou i2 + 1
        for n, (indices, x) in enumerate(self.portions_du_clou(courbe)):
            insertions.append((indices.stop if n == 0 else indices.start, np.array((x, self.y_axe))))
        for i, q in sorted(insertions, key=lambda e: -e[0]):
            if np.hypot(*(q - pts[i - 1])) < 1e-6 or np.hypot(*(q - pts[i])) < 1e-6: continue
            pts.insert(i, q)
            directions.insert(i, np.array((0.0, -1.0)))
        tangentes = []
        for i, t in enumerate(directions):
            corde = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            if t is None: t = corde
            norme = math.hypot(*t)
            t = t / norme if norme > 1e-12 else np.array((1.0, 0.0))
            tangentes.append(t if t @ corde >= 0 else -t)
        morceaux = [deux_arcs(pts[i], tangentes[i], pts[i + 1], tangentes[i + 1]) for i in range(len(pts) - 1)]
        return np.concatenate([morceaux[0]] + [m[1:] for m in morceaux[1:]])

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

    def place(self, sigma, u):
        '''Place les sommets au temps u de la lettre σ (vers l'image clé suivante) : les trous glissent de la
        disposition de l'image clé courante à la suivante, et les deux trous de σ font en plus un demi-tour autour
        de leur milieu (centre et rayon eux aussi interpolés).'''
        m, i, n = self.maillage, abs(sigma) - 1, self.nb_trous
        xs0, xs1 = self.dispositions[self.etape][0], self.dispositions[self.etape + 1][0]
        x = [(1 - u) * a + u * b for a, b in zip(xs0, xs1)] # abscisses de chaque place, de gauche à droite
        milieu = (1 - u) * (xs0[i] + xs0[i + 1]) / 2 + u * (xs1[i] + xs1[i + 1]) / 2
        r = (1 - u) * (xs0[i + 1] - xs0[i]) / 2 + u * (xs1[i + 1] - xs1[i]) / 2
        theta = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * u
        c, s = math.cos(theta), math.sin(theta)
        for j, h in enumerate(self.trous): m.pos[h] = (x[j], self.y_axe)
        a, b = self.trous[i], self.trous[i + 1]
        m.pos[a] = (milieu - r * c, self.y_axe - r * s)
        m.pos[b] = (milieu + r * c, self.y_axe + r * s)
        # les sommets des bords se croisent sans jamais se rejoindre
        ecart = math.hypot(r * c, 0.4 * r * s)
        bords = list(x)
        bords[i], bords[i + 1] = milieu - ecart, milieu + ecart
        for rangee, decalage in ((self.haut, DECALAGE_BORD), (self.bas, self.decalage_bas)):
            for j in range(n): m.pos[rangee[j + 1]][0] = bords[j] + decalage
        j, f = self.place_du_clou
        m.pos[self.clou][0] = m.pos[self.bas[j]][0] + f * (m.pos[self.bas[j + 1]][0] - m.pos[self.bas[j]][0])
        if u == 1:
            m.pos[a], m.pos[b] = (xs1[i + 1], self.y_axe), (xs1[i], self.y_axe)
            self.trous[i], self.trous[i + 1] = b, a
            self.etape += 1

    def lettre(self, sigma, images=96, sous_pas=2, taux=0.15, largeur_brin=None, rendu=None):
        '''Un demi-tour (σ_i : sens de SENS_DE_SIGMA). rendu : fonction appelée avec chaque image (surface Cairo) ;
        sans elle, rien n'est dessiné.'''
        ecart0, ecart1 = self.dispositions[self.etape][1], self.dispositions[self.etape + 1][1]
        for pas in range(1, images * sous_pas + 1):
            u = pas / (images * sous_pas)
            self.place(sigma, u)
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            self.tend(taux, (1 - u) * ecart0 + u * ecart1)
            if rendu and pas % sous_pas == 0:
                rendu(self.cadre(largeur_brin=largeur_brin, ecart=(1 - u) * ecart0 + u * ecart1))


SENS_DE_SIGMA = 1


def verifie_triangulation(tresse, images=12, **options):
    '''Après chaque lettre, les mots relus sur le dessin sont ceux de calcule_autofn_de_tresse
    (dessin en arcs de cercle et en cordes).'''
    film = Film(tresse, **options)
    for k, sigma in enumerate(tresse):
        film.lettre(sigma, images)
        attendu = calcule_autofn_de_tresse(tresse[:k + 1], film.nb_trous)
        if film.mots() != attendu or film.mots(False) != attendu: return False
    return True

def film_triangule(tresse, fichier, images=96, pause=0.5, largeur_brin=None, **options):
    '''Film MP4 (VP9, 25 images/s), écrit au fil du calcul par ffmpeg : un demi-tour continu par lettre, `images`
    images par lettre (le film est proportionnel à la longueur de la tresse), pause en secondes sur chaque image
    clé (trois fois plus sur la dernière), triangulation en gris.'''
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
    for n, sigma in enumerate(tresse):
        derniere = []
        def rendu(surface):
            if derniere: ecrit(derniere.pop())
            derniere.append(surface)
        film.lettre(sigma, images, largeur_brin=largeur_brin, rendu=rendu)
        ecrit(derniere.pop(), round(25 * pause * (3 if n == len(tresse) - 1 else 1)))
    ffmpeg.stdin.close()
    ffmpeg.wait()

assert verifie_triangulation([1])
assert verifie_triangulation([1, -2, 1])
assert verifie_triangulation([4, 3, -1, -1, 2, -4, 1])
