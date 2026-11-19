'''Petits schémas d'explication pour les infobulles de la page web : le diagramme de tresse classique, les quatre méthodes de dessin
des méandres (diagramme de courbes, lacets conformes, triangulation, rubans). L'action sur F_n (fn.svg) vient de schema_fn.js (moteur réel). SVG, 440 × 250, mêmes couleurs que la page (PALETTE de
web/ardoise.js). Chaque schéma : à gauche l'état de départ, à droite après un demi-tour de deux trous (ou ce que fait la méthode).
Lancer : python imgs/schemas/genere_schemas.py   (écrit les .svg à côté du script ; les aperçus .png sont ignorés par git)'''
import math
import os

ICI = os.path.dirname(os.path.abspath(__file__))
COULEURS = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6']
ENCRE, GRIS, FIN = '#1d2330', '#8c8c8c', '#c9c6bd'


def entete(titre):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 250" width="440" height="250" font-family="system-ui, -apple-system, 'Segoe UI', sans-serif" font-size="12">
<title>{titre}</title>
<defs>
<marker id="pointe" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ENCRE}"/></marker>
</defs>
<rect width="440" height="250" fill="#ffffff"/>
'''


def pied():
    return '</svg>\n'


def trou(x, y, r=5, fixe=False):
    return f'<circle cx="{x:g}" cy="{y:g}" r="{r}" fill="{GRIS if fixe else ENCRE}"/>\n'


def texte(x, y, t, ancre='middle', taille=12, couleur=ENCRE, style=''):
    return f'<text x="{x:g}" y="{y:g}" text-anchor="{ancre}" font-size="{taille}" fill="{couleur}" {style}>{t}</text>\n'


def chemin(d, couleur, largeur=4, opacite=1, extra='', cap='round'):
    return f'<path d="{d}" fill="none" stroke="{couleur}" stroke-width="{largeur}" stroke-linecap="{cap}" stroke-linejoin="round" opacity="{opacite}" {extra}/>\n'


def fleche(x1, y1, x2, y2, legende=''):
    s = f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" stroke="{ENCRE}" stroke-width="1.6" fill="none" marker-end="url(#pointe)"/>\n'
    if legende:
        s += texte((x1 + x2) / 2, y1 - 8, legende, taille=11)
    return s


def demi_tour(cx, cy, r, decalage=14, ry=None):
    '''Flèche courbe qui fait le tour de deux trous (demi-cercle au-dessus, du trou de gauche au trou de droite, sens horaire).'''
    return (f'<path d="M{cx - r:g},{cy - decalage:g} A{r:g},{ry if ry else r:g} 0 0 1 {cx + r:g},{cy - decalage:g}" stroke="{ENCRE}" stroke-width="1.6" fill="none"'
            ' stroke-dasharray="4 3" marker-end="url(#pointe)"/>\n')


def ecrit(nom, contenu):
    # le schéma est écrit ici et copié pour la page web (web/schemas/)
    for dossier in (ICI, os.path.join(ICI, '..', '..', 'web', 'schemas')):
        os.makedirs(dossier, exist_ok=True)
        with open(os.path.join(dossier, nom), 'w') as f: f.write(contenu)


# ---------------------------------------------------------------------------------------------------------------- diagramme

def diagramme():
    y = 150
    s = entete('Diagramme de courbes')
    # à gauche : un point fixe, trois trous sur l'axe ; les arcs sont les segments de l'axe
    xs = [28, 78, 128, 178]
    for k in range(3): s += chemin(f'M{xs[k]},{y} L{xs[k + 1]},{y}', COULEURS[k], 6)
    s += trou(xs[0], y, 6, fixe=True) + ''.join(trou(x, y) for x in xs[1:])
    s += texte(xs[0], y + 26, 'point fixe', taille=11, couleur=GRIS)
    for k, x in enumerate(xs[1:], 1): s += texte(x, y + 26, str(k), taille=12)
    s += demi_tour((xs[2] + xs[3]) / 2, y, 36)
    s += texte(103, 40, 'départ', taille=14, style='font-weight="600"')
    s += texte(103, 58, 'les arcs sont les segments de l\'axe', taille=12, couleur='#626b7d')
    # flèche
    s += fleche(200, 135, 240, 135, 'σ₂')
    # à droite : après le demi-tour des trous 2 et 3 (le trou 2 est passé par-dessus, le 3 par-dessous)
    d = 240
    x = [xx + d for xx in xs]          # x[0] fixe, x[1] trou 1, x[2], x[3]
    s += chemin(f'M{x[0]},{y} L{x[1]},{y}', COULEURS[0], 6)
    s += chemin(f'M{x[1]},{y} C{x[1] + 22},{y - 62} {x[3] - 22},{y - 62} {x[3]},{y}', COULEURS[1], 6)   # passe par-dessus le trou 3
    s += chemin(f'M{x[3]},{y} L{x[2]},{y}', COULEURS[2], 6)                                              # entre les deux trous échangés
    s += trou(x[0], y, 6, fixe=True) + trou(x[1], y) + trou(x[2], y) + trou(x[3], y)
    s += texte(x[1], y + 26, '1', taille=12) + texte(x[2], y + 26, '3', taille=12) + texte(x[3], y + 26, '2', taille=12)
    s += texte(x[0] + 0.5 * (x[3] - x[0]), 40, 'après le demi-tour', taille=14, style='font-weight="600"')
    s += texte(x[0] + 0.5 * (x[3] - x[0]), 58, 'les arcs suivent les trous', taille=12, couleur='#626b7d')
    s += texte(220, 232, 'un seul point fixe, à gauche : la tresse emporte les arcs', taille=12, couleur='#626b7d')
    return s + pied()


# ---------------------------------------------------------------------------------------------------------------- rubans

def rubans():
    ya, yf = 100, 195
    s = entete('Rubans')
    xs = [50, 100, 150]
    for k, x in enumerate(xs): s += chemin(f'M{x},{yf} L{x},{ya}', COULEURS[k], 7, 0.9)
    s += ''.join(trou(x, ya) for x in xs) + ''.join(trou(x, yf, 5, fixe=True) for x in xs)
    for k, x in enumerate(xs, 1): s += texte(x, ya - 12, str(k), taille=12)
    s += texte(18, yf + 4, 'fixes', ancre='start', taille=11, couleur=GRIS)
    s += texte(14, ya + 4, '', taille=11)
    s += demi_tour((xs[1] + xs[2]) / 2, ya - 32, 25, 0, 16)
    s += texte(100, 26, 'départ', taille=14, style='font-weight="600"')
    s += texte(100, 44, 'un ruban par trou voyageur', taille=12, couleur='#626b7d')
    s += fleche(190, 135, 230, 135, 'σ₂')
    d = 240
    x1, x2, x3 = [x + d for x in xs]
    # trou 2 passé par-dessus à droite, trou 3 passé par-dessous à gauche
    s += chemin(f'M{x1},{yf} L{x1},{ya}', COULEURS[0], 7, 0.9)
    s += chemin(f'M{x2},{yf} C{x2},{yf - 45} {x2 - 14},{ya + 40} {x2 - 14},{ya} C{x2 - 14},{ya - 45} {x3},{ya - 50} {x3},{ya}', COULEURS[1], 7, 0.9)
    s += chemin(f'M{x3},{yf} L{x3},{ya + 42} C{x3},{ya + 20} {x2},{ya + 22} {x2},{ya}', COULEURS[2], 7, 0.9)
    s += ''.join(trou(x, ya) for x in (x1, x2, x3)) + ''.join(trou(x, yf, 5, fixe=True) for x in (x1, x2, x3))
    s += texte(x1, ya - 12, '1', taille=12) + texte(x2, ya - 12, '3', taille=12) + texte(x3, ya - 12, '2', taille=12)
    s += texte(x2, 26, 'après le demi-tour', taille=14, style='font-weight="600"')
    s += texte(x2, 44, 'les rubans s\'enroulent', taille=12, couleur='#626b7d')
    s += texte(220, 236, 'chaque ruban va d\'un trou fixe (la « queue ») à un trou voyageur', taille=12, couleur='#626b7d')
    return s + pied()


# ---------------------------------------------------------------------------------------------------------------- triangulation

def triangulation():
    s = entete('Triangulation mobile')
    # sommets (repère local du panneau : 0..190 × 0..230), trous A, B, D, clou C, bord P0..P4
    P = {'P0': (0, 40), 'P1': (95, 30), 'P2': (190, 40), 'P3': (0, 212), 'P4': (190, 212),
         'A': (40, 112), 'B': (95, 112), 'D': (150, 112), 'C': (95, 190)}
    aretes = [('P0', 'P1'), ('P1', 'P2'), ('P2', 'P4'), ('P4', 'P3'), ('P3', 'P0'), ('A', 'P0'), ('A', 'P1'), ('A', 'P3'), ('A', 'B'),
              ('A', 'C'), ('B', 'P1'), ('B', 'C'), ('B', 'D'), ('D', 'P1'), ('D', 'P2'), ('D', 'P4'), ('D', 'C'), ('C', 'P3'), ('C', 'P4')]

    def tourne(p, centre, angle):
        c, sn = math.cos(angle), math.sin(angle)
        x, y = p[0] - centre[0], p[1] - centre[1]
        return (centre[0] + c * x - sn * y, centre[1] + sn * x + c * y)

    def apres():
        Q = dict(P)
        milieu = ((P['A'][0] + P['B'][0]) / 2, (P['A'][1] + P['B'][1]) / 2)
        Q['A'], Q['B'] = tourne(P['A'], milieu, math.radians(55)), tourne(P['B'], milieu, math.radians(55))
        return Q
    Q = apres()
    # le lacet : de C autour du trou A, il coupe les quatre arêtes en A (autres que AC) ; deux brins emboîtés (fractions de A vers l'autre bout)
    coupes = [('A', 'B'), ('A', 'P1'), ('A', 'P0'), ('A', 'P3')]
    brins = [0.38, 0.62]

    def point(Pos, e, f):
        (x0, y0), (x1, y1) = Pos[e[0]], Pos[e[1]]
        return (x0 + f * (x1 - x0), y0 + f * (y1 - y0))

    def dessin_panneau(Pos, dx, tendu):
        t = ''
        for a, b in aretes:
            t += chemin(f'M{Pos[a][0] + dx:g},{Pos[a][1]:g} L{Pos[b][0] + dx:g},{Pos[b][1]:g}', FIN, 1.4)
        for k, f in enumerate(brins):
            pts = [Pos['C']] + [point(Pos, e, f) for e in coupes] + [Pos['C']]
            pts = [(x + dx, y) for x, y in pts]
            if tendu:      # tendu : lignes droites, coudes arrondis (congés)
                d = f'M{pts[0][0]:g},{pts[0][1]:g}'
                for i in range(1, len(pts) - 1):
                    a, v, b = pts[i - 1], pts[i], pts[i + 1]
                    la, lb = math.dist(a, v), math.dist(b, v)
                    c = 0.45 * min(la, lb)
                    pa = (v[0] + (a[0] - v[0]) * c / la, v[1] + (a[1] - v[1]) * c / la)
                    pb = (v[0] + (b[0] - v[0]) * c / lb, v[1] + (b[1] - v[1]) * c / lb)
                    d += f' L{pa[0]:g},{pa[1]:g} Q{v[0]:g},{v[1]:g} {pb[0]:g},{pb[1]:g}'
                d += f' L{pts[-1][0]:g},{pts[-1][1]:g}'
            else:          # lâche : lignes brisées entre les points des arêtes
                d = 'M' + ' L'.join(f'{x:g},{y:g}' for x, y in pts)
            t += chemin(d, COULEURS[k], 3)
            if not tendu:
                for x, y in pts[1:-1]: t += f'<circle cx="{x:g}" cy="{y:g}" r="3" fill="#ffffff" stroke="{COULEURS[k]}" stroke-width="1.8"/>\n'
        for n in ('A', 'B', 'D'): t += trou(Pos[n][0] + dx, Pos[n][1])
        t += trou(Pos['C'][0] + dx, Pos['C'][1], 6)
        return t
    # le panneau de gauche est décalé de 10, celui de droite de 240
    s += dessin_panneau(P, 10, False)
    s += fleche(200, 135, 232, 135, 'σ₂')
    s += dessin_panneau(Q, 240, True)
    s += texte(10 + 95, 20, 'départ', taille=14, style='font-weight="600"')
    s += texte(240 + 95, 20, 'après un demi-tour', taille=14, style='font-weight="600"')
    s += texte(10 + 95, 238, 'des points sur les arêtes', taille=12, couleur='#626b7d')
    s += texte(240 + 95, 238, 'les brins se tendent', taille=12, couleur='#626b7d')
    s += texte(P['C'][0] + 10 + 9, P['C'][1] + 4, 'clou', ancre='start', taille=11, couleur=ENCRE)
    return s + pied()


# ---------------------------------------------------------------------------------------------------------------- lacets conformes

def conforme():
    s = entete('Lacets conformes')
    y = 175
    # à gauche : demi-plan, demi-cercles (images clés) autour de deux points A et B de la droite
    A, B = 62, 140
    for k, r in enumerate((13, 27, 41)):
        s += chemin(f'M{A - r},{y} A{r},{r} 0 0 1 {A + r},{y}', COULEURS[k], 3.2)
    for k, r in enumerate((13, 27)):
        s += chemin(f'M{B - r},{y} A{r},{r} 0 0 1 {B + r},{y}', COULEURS[k + 2 if k + 2 < 5 else 0], 3.2)
    s += f'<path d="M12,{y} L188,{y}" stroke="{ENCRE}" stroke-width="1.6"/>\n'
    s += trou(A, y) + trou(B, y)
    s += texte(A, y + 20, 'A', taille=12) + texte(B, y + 20, 'B', taille=12)
    s += texte(100, 26, 'demi-plan', taille=14, style='font-weight="600"')
    s += texte(100, 44, 'des demi-cercles', taille=12, couleur='#626b7d')
    s += fleche(198, 125, 240, 125)
    s += texte(219, 104, 'transformation', taille=11) + texte(219, 117, 'conforme', taille=11)
    # à droite : la région au-dessus de la ligne brisée L–A–B–R ; les images des demi-cercles sont des arcs perpendiculaires aux segments
    L, Ap, Bp, R = (244, 208), (296, 208), (334, 104), (432, 132)
    s += f'<path d="M{L[0]},{L[1]} L{Ap[0]},{Ap[1]} L{Bp[0]},{Bp[1]} L{R[0]},{R[1]}" stroke="{ENCRE}" stroke-width="1.6" fill="none" stroke-linejoin="round"/>\n'

    def unit(p, q):
        d = (q[0] - p[0], q[1] - p[1]); n = math.hypot(*d); return (d[0] / n, d[1] / n)

    def arc(P, nP, Qp, nQ, k, couleur):
        c1 = (P[0] + k * nP[0], P[1] + k * nP[1]); c2 = (Qp[0] + k * nQ[0], Qp[1] + k * nQ[1])
        return chemin(f'M{P[0]:g},{P[1]:g} C{c1[0]:g},{c1[1]:g} {c2[0]:g},{c2[1]:g} {Qp[0]:g},{Qp[1]:g}', couleur, 3.2)

    def normale(u): return (u[1], -u[0])                     # vers le haut de l'écran pour une ligne qui va vers la droite
    u1, u2, u3 = unit(L, Ap), unit(Ap, Bp), unit(Bp, R)

    def autour(centre, u_in, u_out, rayon, couleur):
        '''Arc de cercle centré sur le sommet, de la ligne qui arrive à celle qui repart, du côté de la région (à gauche de la marche) :
        il coupe les deux segments à angle droit.'''
        a1 = math.degrees(math.atan2(-u_in[1], -u_in[0]))
        a2 = math.degrees(math.atan2(u_out[1], u_out[0]))
        while a2 <= a1: a2 += 360
        p = (centre[0] + rayon * math.cos(math.radians(a1)), centre[1] + rayon * math.sin(math.radians(a1)))
        q = (centre[0] + rayon * math.cos(math.radians(a2)), centre[1] + rayon * math.sin(math.radians(a2)))
        grand = 1 if a2 - a1 > 180 else 0
        return chemin(f'M{p[0]:g},{p[1]:g} A{rayon:g},{rayon:g} 0 {grand} 1 {q[0]:g},{q[1]:g}', couleur, 3.2)
    for k, r in enumerate((14, 26, 38)):                     # autour de A : de L–A à A–B
        s += autour(Ap, u1, u2, r, COULEURS[k])
    for k, r in enumerate((13, 24)):                         # autour de B : de A–B à B–R
        s += autour(Bp, u2, u3, r, COULEURS[k + 2])
    s += trou(Ap[0], Ap[1]) + trou(Bp[0], Bp[1])
    s += texte(Ap[0] + 6, Ap[1] + 18, 'A', taille=12) + texte(Bp[0] + 22, Bp[1] + 30, 'B', ancre='start', taille=12)
    s += texte(L[0] + 2, L[1] + 18, 'L', taille=12) + texte(R[0] - 6, R[1] + 16, 'R', ancre='end', taille=12)
    s += texte(340, 26, 'ligne brisée L–A–B–R', taille=14, style='font-weight="600"')
    s += texte(340, 44, 'les trous qui tournent, bout à bout', taille=12, couleur='#626b7d')
    s += texte(220, 240, 'à chaque instant, le dessin est calculé d\'un coup (arcs exacts, à angle droit)', taille=12, couleur='#626b7d')
    return s + pied()



# ---------------------------------------------------------------------------------------------------------------- diagramme de tresse

def croisement(x0, x1, y0, m, couleur):
    '''Un brin qui va de x0 en haut à x1 en bas : un liseré blanc (il coupe ce qui passe dessous), puis le brin.'''
    d = f'M{x0:g},{y0 - 1:g} C{x0:g},{y0 + m / 2:g} {x1:g},{y0 + m / 2:g} {x1:g},{y0 + m + 1:g}'
    return chemin(d, '#ffffff', 11, 1, cap='butt') + chemin(d, couleur, 4.5, 1, cap='butt')


def ligne_de_tresse(xs, y0, m, k, signe, couleurs):
    '''Une ligne du diagramme : le croisement σ_k (signe +1) ou σ_k⁻¹ (-1) entre les colonnes k et k + 1 (0 pour la première) ; renvoie le dessin
    et les couleurs des colonnes après le croisement. Au croisement positif, le brin qui va de droite à gauche passe dessus.'''
    t = ''
    for i, x in enumerate(xs):
        if i == k:
            gd = croisement(xs[k], xs[k + 1], y0, m, couleurs[k])          # de gauche à droite
            dg = croisement(xs[k + 1], xs[k], y0, m, couleurs[k + 1])      # de droite à gauche
            t += (gd + dg) if signe > 0 else (dg + gd)
        elif i != k + 1:
            t += chemin(f'M{x:g},{y0:g} L{x:g},{y0 + m:g}', couleurs[i], 4.5, 1, cap='butt')
    nouvelles = list(couleurs)
    nouvelles[k], nouvelles[k + 1] = couleurs[k + 1], couleurs[k]
    return t, nouvelles


def tresse():
    s = entete('Diagramme de tresse')
    # à gauche : les deux croisements, σ_i et son inverse
    s += texte(100, 26, 'un croisement', taille=14, style='font-weight="600"')
    s += texte(100, 44, 'deux brins qui s\'échangent', taille=12, couleur='#626b7d')
    for cx, signe, nom, legende in ((48, 1, 'σᵢ', 'le brin de droite'), (152, -1, 'σᵢ⁻¹', 'le brin de gauche')):
        d, _ = ligne_de_tresse([cx - 17, cx + 17], 70, 90, 0, signe, [COULEURS[0], COULEURS[1]])
        s += d
        s += texte(cx, 182, nom, taille=16, style='font-weight="600"')
        s += texte(cx, 202, legende, taille=11, couleur='#626b7d')
        s += texte(cx, 216, 'passe dessus', taille=11, couleur='#626b7d')
    # à droite : un exemple, σ₁ σ₂⁻¹, lu de haut en bas
    s += texte(335, 26, 'un mot de tresse', taille=14, style='font-weight="600"')
    s += texte(335, 44, 'lu de haut en bas : σ₁ σ₂⁻¹', taille=12, couleur='#626b7d')
    xs = [285, 335, 385]
    couleurs = [COULEURS[0], COULEURS[1], COULEURS[2]]
    y = 62
    d, couleurs = ligne_de_tresse(xs, y, 70, 0, 1, couleurs); s += d
    d, couleurs = ligne_de_tresse(xs, y + 70, 70, 1, -1, couleurs); s += d
    s += texte(240, y + 40, 'σ₁', taille=14, style='font-weight="600"') + texte(240, y + 110, 'σ₂⁻¹', taille=14, style='font-weight="600"')
    s += f'<path d="M424,{y + 5} L424,{y + 125}" stroke="{ENCRE}" stroke-width="1.6" fill="none" marker-end="url(#pointe)"/>\n'
    s += texte(220, 240, 'un brin de même couleur du haut au bas : les couleurs suivent les brins', taille=12, couleur='#626b7d')
    return s + pied()


if __name__ == "__main__":
    ecrit('diagramme.svg', diagramme())
    ecrit('rubans.svg', rubans())
    ecrit('triangulation.svg', triangulation())
    ecrit('lacets.svg', conforme())
    ecrit('tresse.svg', tresse())
    print('écrit : diagramme.svg, rubans.svg, triangulation.svg, lacets.svg, tresse.svg (ici et dans web/schemas/)')
