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


ECART_BRINS = 6 # écart minimal en pixels entre deux brins sur une arête
DEGAGEMENT_TROUS = 10 # distance minimale en pixels entre un brin et un sommet, sur une arête

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

    def __init__(self, pos, triangles, proteges=()):
        self.proteges = set(proteges) # sommets qui ne gagnent jamais d'arête (le clou)
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
            if {b, d} & self.proteges: continue
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
    '''Triangulation de départ en trois bandes horizontales, rangées de haut en bas :
    - le bord haut, un sommet à la verticale de chaque trou (et les coins) ;
    - l'axe (extrémités et trous) : entre les deux, la bande des arcs du haut ;
    - une rangée sous l'axe (à 60 % de la distance de l'axe à la base), un sommet à la verticale de chaque trou : bande des arcs du bas ;
    - la base, sous laquelle pend le clou : bande du clou. Le clou est une pointe de degré 2 dont l'unique triangle
    contient les départs et les arrivées de tous les lacets, et il ne gagne jamais d'arête (`proteges`).
    Chaque bande est découpée en une échelle de triangles (zigzag entre les deux rangées), puis les arêtes non de
    Delaunay sont retournées. Les rangées alignées (haut et bas) ont les coins en plus : indice k + 1 pour le trou k.
    Renvoie (maillage, indices des trous, du clou, rangée alignée du haut, du bas).'''
    y_axe = trous[0][1] + DECALAGE_AXE
    xs_alignes = [0] + [x + DECALAGE_BORD for x, _ in trous] + [largeur]
    pts = []
    def ajoute(p): pts.append(p); return len(pts) - 1
    def rangee(y, xs): return [ajoute((x, y)) for x in xs]

    haut = rangee(3, xs_alignes)
    axe = [ajoute((0, y_axe))] + [ajoute((x, y_axe)) for x, _ in trous] + [ajoute((largeur, y_axe))]
    y_base = clou[1] - 14
    bas = rangee(y_axe + 0.6 * (y_base - y_axe), xs_alignes)
    demi_base = 90 # les brins quittent le clou avec au moins 12,9° d'élévation : les côtés de la pointe font moins (14/90)
    base = rangee(y_base, [0, clou[0] - demi_base, clou[0] + demi_base, largeur])
    triangles = []
    for r1, r2 in zip((haut, axe, bas), (axe, bas, base)):
        r1 = sorted(r1, key=lambda i: pts[i][0])
        r2 = sorted(r2, key=lambda i: pts[i][0])
        i = j = 0
        while i < len(r1) - 1 or j < len(r2) - 1:
            avance_1 = j == len(r2) - 1 or (i < len(r1) - 1 and pts[r1[i + 1]][0] <= pts[r2[j + 1]][0])
            if avance_1: triangles.append((r1[i], r1[i + 1], r2[j])); i += 1
            else: triangles.append((r1[i], r2[j], r2[j + 1])); j += 1
    nail = ajoute(tuple(clou))
    triangles.append((base[1], base[2], nail))
    m = Maillage(pts, triangles, proteges={nail})
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
        lignes = polylignes(morceaux)
        # le dessin de départ est aplati : on l'étire au-dessus de l'axe pour qu'il occupe la bande du haut
        y_axe, y_min = self.maillage.pos[self.trous[0]][1], min(p[:, 1].min() for p in lignes)
        etirement = (y_axe - 14) / (y_axe - y_min)
        for p in lignes: p[:, 1] = np.where(p[:, 1] < y_axe, y_axe - (y_axe - p[:, 1]) * etirement, p[:, 1])
        self.courbes = [noeuds_de_polyligne(p, self.maillage, self.clou) for p in lignes]

    def tend(self, taux, ecart=ECART_BRINS, degagement=DEGAGEMENT_TROUS):
        '''Un pas de tension des lacets. Chaque point est tiré, d'une fraction taux du chemin, vers l'endroit de son
        arête où ses deux voisins sont alignés avec lui (le brin se tend) ; puis, arête par arête, les points gardent
        leur ordre et restent à `ecart` pixels les uns des autres et à `degagement` pixels des sommets (projection
        d'une régression monotone bornée), moins si l'arête est trop courte. Les brins se tassent donc à écart fixe là
        où ils sont tirés, près des trous, et laissent du vide au-delà ; l'ordre sur chaque arête ne change pas, donc
        aucun croisement.'''
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
            for j, x in enumerate(monotone(cibles)):
                x = min(max(x, marge), longueur - marge - (m - 1) * g)
                _, k, i = liste[j]
                self.courbes[k][i] = ('e', u, v, (x + j * g) / longueur)

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

    def lettre(self, sigma, images=24, sous_pas=6, taux=0.15):
        '''Un demi-tour (σ_i : sens de SENS_DE_SIGMA) ; renvoie les images (surfaces Cairo) du mouvement.'''
        depart = self.maillage.pos.copy()
        resultat = []
        trous_depart = list(self.trous)
        for pas in range(1, images * sous_pas + 1):
            self.trous[:] = trous_depart
            self.place(None, sigma, pas / (images * sous_pas), depart)
            assert self.maillage.valide(), "triangle retourné : augmenter sous_pas"
            self.maillage.delaunay(self.courbes)
            self.tend(taux)
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
        if not depart_et_arrivee_ensemble(film): return False
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

def depart_et_arrivee_ensemble(film):
    '''Le premier et le dernier point de chaque lacet sont sur la même arête : la seule qui borde le triangle du clou.'''
    return all(c[1][1:3] == c[-2][1:3] for c in film.courbes) and len({c[1][1:3] for c in film.courbes}) == 1

assert verifie_triangulation([1])
assert verifie_triangulation([1, -2, 1])
assert verifie_triangulation([4, 3, -1, -1, 2, -4, 1])
