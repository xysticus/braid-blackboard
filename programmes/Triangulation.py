'''Film des lacets de l'automorphisme d'Artin par une triangulation mobile.

Les sommets sont les trous, le clou, des sommets sur les bords haut et bas (à la verticale des trous) et les
extrémités de l'axe. Un lacet est une suite de points posés sur les arêtes (à une fraction de la longueur de
l'arête), et deux points consécutifs sont dans un même triangle. Quand les trous i et i+1 tournent l'un autour
de l'autre, les sommets bougent, les points suivent leur arête, et quand une arête cesse d'être de Delaunay
(par exemple quand deux trous passent à la verticale l'un de l'autre) on la retourne : les lacets sont
recalculés dans les nouveaux triangles sans changer de forme. Le dessin est tracé en arcs de cercle
(`deux_arcs`) entre les points des arêtes, un par triangle traversé.'''

import math, operator, os
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


def maillage_initial(trous, clou, hauteur, largeur):
    '''Triangulation de Delaunay du rectangle : trous sur l'axe, sommets au-dessus et au-dessous de chaque trou
    sur les bords, extrémités de l'axe, clou. Renvoie (maillage, indices des trous, du clou,
    des sommets du bord haut, du bord bas) ; les sommets des bords sont rangés comme les trous, avec les
    coins en plus : indices k + 1 pour le trou k.'''
    n = len(trous)
    y_axe = trous[0][1] + DECALAGE_AXE
    xs = [0] + [x + DECALAGE_BORD for x, _ in trous] + [largeur]
    pts = []
    def ajoute(p): pts.append(p); return len(pts) - 1
    axe = [ajoute((0, y_axe))] + [ajoute((x, y_axe)) for x, _ in trous] + [ajoute((largeur, y_axe))]
    haut = [ajoute((x, 3)) for x in xs]
    bas = [ajoute((x, hauteur - 3)) for x in xs]
    triangles = []
    for rangee in (haut, bas):
        for k in range(n + 1):
            triangles.append((axe[k], axe[k + 1], rangee[k]))
            triangles.append((axe[k + 1], rangee[k], rangee[k + 1]))
    nail = ajoute(tuple(clou))
    m = Maillage(pts, triangles)
    for t in list(m.triangles):
        a, b, c = sorted(t)
        s = [croix(m.pos[y] - m.pos[x], m.pos[nail] - m.pos[x]) for x, y in ((a, b), (b, c), (c, a))]
        if all(x > 0 for x in s) or all(x < 0 for x in s):
            m.triangles.remove(t)
            del m.signes[t]
            for x, y in ((a, b), (b, c), (c, a)):
                m.triangles.add(frozenset((x, y, nail)))
                m.signes[frozenset((x, y, nail))] = m.signe((x, y, nail))
            break
    else: raise ValueError("le clou n'est dans aucun triangle")
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


def polyligne_de_courbe(maillage, courbe, lisse=True):
    '''Polyligne dessinée : des arcs de cercle entre points consécutifs (paires d'arcs raccordées avec la même
    tangente, la direction en un point étant celle de la corde entre ses deux voisins).'''
    pts = [maillage.position(n) for n in courbe]
    if not lisse: return np.array(pts)
    tangentes = []
    for k in range(len(pts)):
        d = pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]
        norme = math.hypot(*d)
        tangentes.append(d / norme if norme > 1e-12 else np.array((1.0, 0.0)))
    morceaux = [deux_arcs(pts[k], tangentes[k], pts[k + 1], tangentes[k + 1]) for k in range(len(pts) - 1)]
    return np.concatenate([morceaux[0]] + [m[1:] for m in morceaux[1:]])


class Film:
    '''Les trous en mouvement, leur triangulation et les lacets posés dessus.'''

    def __init__(self, tresse, hauteur=400, largeur=400):
        self.hauteur, self.largeur = hauteur, largeur
        self.nb_trous = max(map(operator.abs, tresse), default=1) + 1
        morceaux, trous, clou, _ = dessin_etat(etat_de_tresse([], self.nb_trous), hauteur, largeur)
        self.maillage, self.trous, self.clou, self.haut, self.bas = maillage_initial(trous, clou, hauteur, largeur)
        self.courbes = [noeuds_de_polyligne(p, self.maillage, self.clou) for p in polylignes(morceaux)]

    def polylignes(self, lisse=True):
        return [polyligne_de_courbe(self.maillage, c, lisse) for c in self.courbes]

    def positions_des_trous(self):
        return self.maillage.pos[self.trous]

    def mots(self, lisse=True):
        trous = sorted(map(tuple, self.positions_des_trous()))
        return [lit_mot(p, trous) for p in self.polylignes(lisse)]

    def cadre(self, lisse=True, largeur_brin=3, avec_arêtes=True):
        arêtes = [self.maillage.pos[list(e)] for e in self.maillage.aretes()] if avec_arêtes else None
        return peint(self.polylignes(lisse), self.positions_des_trous(), self.maillage.pos[self.clou],
                     self.hauteur, self.largeur, largeur_brin, axe=arêtes)

    def place(self, i, sigma, u, depart):
        '''Place les sommets au temps u du demi-tour des trous i et i+1 (indices 0 ...) : depart = positions
        au début de la lettre.'''
        m, k = self.maillage, abs(sigma) - 1
        a, b = self.trous[k], self.trous[k + 1]
        milieu = (depart[a] + depart[b]) / 2
        r = math.hypot(*(depart[b] - depart[a])) / 2
        theta = SENS_DE_SIGMA * (1 if sigma > 0 else -1) * math.pi * u
        c, s = math.cos(theta), math.sin(theta)
        for h in (a, b):
            d = depart[h] - milieu
            m.pos[h] = milieu + np.array((c * d[0] - s * d[1], s * d[0] + c * d[1]))
        if u == 1:
            m.pos[a], m.pos[b] = depart[b].copy(), depart[a].copy()
            self.trous[k], self.trous[k + 1] = b, a
        # les sommets des bords se croisent sans jamais se rejoindre
        g = 0.4 * r
        ecart = math.hypot(r * c, g * s)
        for rangee in (self.haut, self.bas):
            m.pos[rangee[k + 1]][0] = milieu[0] - ecart
            m.pos[rangee[k + 2]][0] = milieu[0] + ecart

    def lettre(self, sigma, images=24, sous_pas=6):
        '''Un demi-tour (σ_i : sens de SENS_DE_SIGMA) ; renvoie les images (surfaces Cairo) du mouvement.'''
        depart = self.maillage.pos.copy()
        resultat = []
        trous_depart = list(self.trous)
        for pas in range(1, images * sous_pas + 1):
            self.trous[:] = trous_depart
            self.place(None, sigma, pas / (images * sous_pas), depart)
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            if pas % sous_pas == 0: resultat.append(self.cadre())
        return resultat


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

def film_triangule(tresse, fichier, images=24, pause=500, largeur_brin=3, **options):
    '''GIF : un demi-tour continu par lettre, triangulation en gris.'''
    film = Film(tresse, **options)
    cadres = [film.cadre(largeur_brin=largeur_brin)]
    durees = [pause]
    for sigma in tresse:
        cadres += film.lettre(sigma, images)
        durees += [40] * (images - 1) + [pause]
    durees[-1] = 3 * pause
    pil = [en_image_pil(c) for c in cadres]
    pil[0].save(fichier, save_all=True, append_images=pil[1:], duration=durees, loop=0)

assert verifie_triangulation([1])
assert verifie_triangulation([1, -2, 1])
assert verifie_triangulation([4, 3, -1, -1, 2, -4, 1])
