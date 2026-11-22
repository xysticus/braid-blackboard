"""Essai (document de travail) : détendre le dessin du raccord par un court flot de courbure contraint.

Le film conforme actuel (`Conforme.dessins_conforme`, raccord par triangulation mobile) est topologiquement juste et sans
croisement, mais pendant le raccord les brins sont un peu carrés autour des trous qui tournent et ondulent par endroits. On
garde ce dessin comme point de départ, et on le détend : chaque brin est rééchantillonné à pas régulier, puis on itère

  - la tension (flot de courbure discret : chaque point va vers le milieu de ses deux voisins), qui arrondit les coins et
    efface les zigzags, en raccourcissant un peu les brins ;
  - la répulsion entre points de brins différents (et entre passages éloignés d'un même brin) plus proches que `ecart`, et
    entre un brin et un trou plus proche que `rayon_trou` : elle garde un écart minimal et empêche tout croisement ;

avec un pas par itération borné (un brin ne peut pas sauter par-dessus un autre ni par-dessus un trou). Près du clou, où
tous les brins se rejoignent, la répulsion s'éteint. L'intensité est `force` ∈ [0, 1] : le film l'applique avec
4 poids (1 − poids), nulle aux bords de la fenêtre du raccord et maximale au milieu : les images clés et le reste du film
sont inchangés, et le film reste continu (un nombre fixe d'itérations d'une transformation continue).

Depuis la racine du dépôt :
  python etude/lacets/essai_lissage.py "1 -2 1 -2 1 -2" 264      comparaison à l'image 264 (imgs/essai_lissage_*.png)
  python etude/lacets/essai_lissage.py film "1 -2 1 -2 1 -2"     le film (imgs/essai_lissage_film_*.mp4), vérifié

La détente est portée en OCaml (ocaml/lib/detente.ml, mêmes résultats à 1e-6 près, test/test_detente.ml) : la page la
calcule elle-même (mode « conforme_detendu », case « détendu » du banc).
"""
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Conforme import dessins_conforme, surface_conforme, nb_croisements, lisse  # noqa: E402
from tresses import calcule_autofn_de_tresse, lit_mot, en_image_pil, ENCODEUR  # noqa: E402

PAS = 4.0            # pas du rééchantillonnage, en pixels (image de 800, marge comprise ou non : le dessin est dans le cadre intérieur)
ECART = 6.0          # écart minimal entre deux brins
RAYON_TROU = 12.0    # distance minimale d'un brin à un trou
RAYON_CLOU = 150.0   # près du clou, la répulsion s'éteint (les brins s'y rejoignent)
CALME_CLOU = 40.0    # et la détente aussi, progressivement : le faisceau qui arrive au clou garde sa forme
ITERATIONS = 400
TENSION = 0.25       # part du chemin vers le milieu des deux voisins, par itération (stable sous 0,5)
REPULSION = 0.5
PAS_MAX = 0.3        # déplacement maximal d'un point par itération


def reechantillonne(P, pas):
    """La polyligne P à pas régulier (les deux bouts gardés)."""
    l = np.concatenate(([0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))))
    n = max(2, int(round(l[-1] / pas)) + 1)
    t = np.linspace(0, l[-1], n)
    return np.column_stack((np.interp(t, l, P[:, 0]), np.interp(t, l, P[:, 1])))


def distance_segment(a, b, c):
    """Distance du point c au segment [a, b]."""
    ab = b - a
    t = min(1.0, max(0.0, float(np.dot(c - a, ab) / max(float(np.dot(ab, ab)), 1e-12))))
    return float(np.hypot(*(a + t * ab - c)))


def retouche(P, pas, trous, fusion=True):
    """Garde des points à peu près réguliers sans jamais rapprocher la courbe d'un trou (le rééchantillonnage, qui remplace la
    courbe par des cordes, coupe à l'intérieur des boucles serrées ; répété, il amenait un brin sur son trou) : les segments plus
    longs que 1,5 pas sont découpés par des points pris sur eux (la courbe ne bouge pas) ; un point dont un segment est plus court
    qu'un demi-pas est retiré (fusion) seulement si la corde qui le remplace ne dépasse pas 1,2 pas (sinon elle serait redécoupée) et
    n'est pas plus près d'un trou que les deux segments retirés. Une corde peut couper un brin voisin : `detend` vérifie après coup et
    refait la retouche sans fusion."""
    pts = [P[0]]
    for q in P[1:]:
        p = pts[-1]
        L = float(np.hypot(*(q - p)))
        k = int(math.ceil(L / pas)) if L > 1.5 * pas else 1
        for j in range(1, k): pts.append(p + (q - p) * (j / k))
        pts.append(q)
    garde = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, m, b = garde[-1], pts[i], pts[i + 1]
        if fusion and min(np.hypot(*(m - a)), np.hypot(*(b - m))) < 0.5 * pas and np.hypot(*(b - a)) <= 1.2 * pas and \
           all(distance_segment(a, b, c) >= min(distance_segment(a, m, c), distance_segment(m, b, c)) for c in trous):
            continue
        garde.append(m)
    garde.append(pts[-1])
    return np.array(garde)


def croisement_existe(X, bouts, I, J, clou, pas):
    """Deux segments de brins se croisent-ils (parmi les voisins des paires proches I, J ; hors des 12 px autour du clou) ?"""
    if not len(I): return False
    ok_seg = np.zeros(len(X), bool)
    dans = np.ones(len(X) - 1, bool); dans[bouts[1:-1] - 1] = False
    ok_seg[np.nonzero(dans)[0]] = True
    loin = np.hypot(*(X - clou).T) > 12
    proches = np.hypot(*(X[I] - X[J]).T) < 4 * pas
    I, J = I[proches], J[proches]
    sa = np.concatenate((I - 1, I, I - 1, I)); sb = np.concatenate((J - 1, J - 1, J, J))
    v = (sa >= 0) & (sb >= 0) & (sa < len(X) - 1) & (sb < len(X) - 1)
    sa, sb = sa[v], sb[v]
    v = ok_seg[sa] & ok_seg[sb] & (np.abs(sa - sb) > 1) & loin[sa] & loin[sa + 1] & loin[sb] & loin[sb + 1]
    sa, sb = sa[v], sb[v]
    p0, d1 = X[sa], X[sa + 1] - X[sa]
    q0, d2 = X[sb], X[sb + 1] - X[sb]
    den = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    w = q0 - p0
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (w[:, 0] * d2[:, 1] - w[:, 1] * d2[:, 0]) / den
        u = (w[:, 0] * d1[:, 1] - w[:, 1] * d1[:, 0]) / den
    return bool(((den != 0) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)).any())


def paires_proches(X, lacet, indice, rayon, ecart_indices):
    """Les paires (i, j), i < j, de points à moins de `rayon`, sauf deux points voisins d'un même brin (indices à moins de
    `ecart_indices`). Par paquets, avec un tri sur x pour ne comparer que des points proches en abscisse."""
    ordre = np.argsort(X[:, 0])
    Xs = X[ordre]
    I, J = [], []
    n = len(Xs)
    debut = np.searchsorted(Xs[:, 0], Xs[:, 0] - rayon, side='left')
    fin = np.searchsorted(Xs[:, 0], Xs[:, 0] + rayon, side='right')
    taille = 512
    for a in range(0, n, taille):
        b = min(n, a + taille)
        lo, hi = debut[a:b].min(), fin[a:b].max()
        lo = max(lo, a)   # seulement j > i dans l'ordre trié (on ne compte chaque paire qu'une fois)
        if hi <= lo: continue
        d = np.hypot(Xs[a:b, None, 0] - Xs[None, lo:hi, 0], Xs[a:b, None, 1] - Xs[None, lo:hi, 1])
        ii, jj = np.nonzero(d < rayon)
        ii, jj = ii + a, jj + lo
        garde = jj > ii
        I.append(ordre[ii[garde]]); J.append(ordre[jj[garde]])
    if not I: return np.zeros(0, int), np.zeros(0, int)
    I, J = np.concatenate(I), np.concatenate(J)
    meme = (lacet[I] == lacet[J]) & (np.abs(indice[I] - indice[J]) < ecart_indices)
    return I[~meme], J[~meme]


def detend(lignes, trous, clou, force, iterations=None):
    """Le dessin détendu (voir le docstring du module) ; force ∈ [0, 1] (0 : le dessin rééchantillonné, inchangé à l'œil)."""
    iterations = ITERATIONS if iterations is None else iterations
    if force <= 0: return [np.array(l, float) for l in lignes]
    # avant de rééchantillonner, éloigner des trous les points trop proches : une boucle plus petite que le pas, rééchantillonnée,
    # peut ne plus contenir son trou (le brin l'aurait sauté avant même la première itération). Dilatation radiale autour de chaque
    # trou, la distance r devenant r + force b (1 − r / 2b) en deçà de 2b (b : la barrière) : elle garde l'ordre des distances,
    # aucun brin n'en croise un autre ni ne passe par-dessus le trou ; nulle à force 0 (le film reste continu).
    barriere = max(0.6 * RAYON_TROU, 0.75 * PAS)
    lignes = [np.array(l, float) for l in lignes]
    for c in np.asarray(trous, float):
        for l in lignes:
            D = l - c
            r = np.hypot(*D.T)
            pres = (r < 2 * barriere) & (r > 1e-9)
            pres[0] = pres[-1] = False   # les bouts restent en place (ceux des arcs sont sur un trou ou un point fixe)
            if pres.any():
                nouveau = r[pres] + force * barriere * (1 - r[pres] / (2 * barriere))
                l[pres] = c + D[pres] * (nouveau / r[pres])[:, None]
    brins = [reechantillonne(l, PAS) for l in lignes]
    tailles = [len(b) for b in brins]
    X = np.concatenate(brins)
    lacet = np.concatenate([np.full(n, k) for k, n in enumerate(tailles)])
    indice = np.concatenate([np.arange(n) for n in tailles])
    bouts = np.cumsum([0] + tailles)
    fixe = np.zeros(len(X), bool)
    fixe[bouts[:-1]] = True; fixe[bouts[1:] - 1] = True     # les deux bouts de chaque brin (au clou)
    precedent = np.arange(len(X)) - 1; suivant = np.arange(len(X)) + 1
    precedent[bouts[:-1]] = bouts[:-1]; suivant[bouts[1:] - 1] = bouts[1:] - 1
    trous = np.asarray(trous, float); clou = np.asarray(clou, float)
    ecart_indices = int(math.ceil(2.5 * ECART / PAS)) + 2
    # les paires sont cherchées toutes les 8 itérations : dans l'intervalle, deux points se rapprochent d'au plus 16 PAS_MAX ; on
    # les cherche donc jusqu'à 1,6 ECART + 16 PAS_MAX, sinon deux brins pourraient passer sous ECART sans se repousser
    for it in range(iterations):
        if it % 8 == 0:
            I, J = paires_proches(X, lacet, indice, 1.6 * ECART + 16 * PAS_MAX, ecart_indices)
        F = TENSION * ((X[precedent] + X[suivant]) / 2 - X)
        # répulsion entre brins, éteinte près du clou
        if len(I):
            D = X[I] - X[J]
            d = np.hypot(*D.T)
            proche_clou = np.minimum(np.hypot(*(X[I] - clou).T), np.hypot(*(X[J] - clou).T))
            ecart = ECART * np.clip(proche_clou / RAYON_CLOU, 0, 1)
            actif = (d < ecart) & (d > 1e-9)
            if actif.any():
                f = (REPULSION * (ecart[actif] - d[actif]) / d[actif])[:, None] * D[actif] / 2
                np.add.at(F, I[actif], f); np.add.at(F, J[actif], -f)
        # répulsion des trous
        for c in trous:
            D = X - c
            d = np.hypot(*D.T)
            actif = (d < RAYON_TROU) & (d > 1e-9)
            if actif.any(): F[actif] += (REPULSION * (RAYON_TROU - d[actif]) / d[actif])[:, None] * D[actif]
        F *= force * np.clip((np.hypot(*(X - clou).T) - 10) / (CALME_CLOU - 10), 0, 1)[:, None]
        n = np.hypot(*F.T)
        trop = n > PAS_MAX
        F[trop] *= (PAS_MAX / n[trop])[:, None]
        F[fixe] = 0
        precedent_X = X
        X = X + F
        # la barrière des trous : un segment qui passerait plus près d'un trou que `barriere`, en s'en rapprochant, reprend sa position
        # d'avant (ses deux bouts). Revenir à une position juste ne peut ni croiser un brin voisin ni sauter le trou (pousser le segment
        # le pouvait), et la distance d'un segment à un trou, une fois sous la barrière, ne diminue plus. On recommence tant qu'un
        # retour en arrière en a fait passer un autre sous la barrière.
        barriere = max(0.6 * RAYON_TROU, 0.75 * PAS)
        dans_brin = np.ones(len(X) - 1, bool)
        dans_brin[bouts[1:-1] - 1] = False
        ia = np.nonzero(dans_brin)[0]
        def distances(Y, c):
            A, B = Y[ia], Y[ia + 1]
            AB = B - A
            t = np.clip(((c - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
            return np.hypot(*(A + t[:, None] * AB - c).T)
        avant = [distances(precedent_X, c) for c in trous]
        for _ in range(20):
            retour = np.zeros(len(X), bool)
            for c, da in zip(trous, avant):
                dn = distances(X, c)
                fautif = (dn < barriere) & (dn < da - 1e-12)
                retour[ia[fautif]] = True; retour[ia[fautif] + 1] = True
            retour &= np.any(X != precedent_X, axis=1)
            if not retour.any(): break
            X = X.copy(); X[retour] = precedent_X[retour]
        # pas de croisement entre brins : si un segment en croise un autre (d'un autre brin, ou un passage éloigné du même), les
        # points des deux reprennent leur position d'avant ; le dessin de départ n'en a pas, il n'en aura donc jamais. Les segments
        # qui se croisent ont des bouts à moins d'un pas et demi : ils sont dans les paires proches.
        if len(I):
            ok_seg = np.zeros(len(X), bool); ok_seg[ia] = True     # le segment s (points s, s + 1) existe
            loin_clou = np.hypot(*(X - clou).T) > 12
            for _ in range(20):
                sa = np.concatenate((I - 1, I, I - 1, I)); sb = np.concatenate((J - 1, J - 1, J, J))
                v = (sa >= 0) & (sb >= 0) & (sa < len(X) - 1) & (sb < len(X) - 1)
                sa, sb = sa[v], sb[v]
                v = ok_seg[sa] & ok_seg[sb] & (np.abs(sa - sb) > 1) & loin_clou[sa] & loin_clou[sa + 1] & loin_clou[sb] & loin_clou[sb + 1]
                sa, sb = sa[v], sb[v]
                if not len(sa): break
                p0, d1 = X[sa], X[sa + 1] - X[sa]
                q0, d2 = X[sb], X[sb + 1] - X[sb]
                den = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
                w = q0 - p0
                with np.errstate(divide='ignore', invalid='ignore'):
                    t = (w[:, 0] * d2[:, 1] - w[:, 1] * d2[:, 0]) / den
                    u = (w[:, 0] * d1[:, 1] - w[:, 1] * d1[:, 0]) / den
                croise = (den != 0) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
                if not croise.any(): break
                retour = np.zeros(len(X), bool)
                for s_ in (sa[croise], sa[croise] + 1, sb[croise], sb[croise] + 1): retour[s_] = True
                retour &= np.any(X != precedent_X, axis=1)
                if not retour.any(): break
                X = X.copy(); X[retour] = precedent_X[retour]
        # retoucher les points : toutes les 25 itérations, et dès qu'un segment dépasse 2 PAS (les croisements sont bloqués plus haut,
        # mais leur détection suppose des segments assez courts pour que leurs bouts soient dans les paires proches)
        longueurs = np.hypot(*np.diff(X, axis=0).T)
        longueurs[bouts[1:-1] - 1] = 0
        if (it % 25 == 24 or longueurs.max() > 2 * PAS) and it < iterations - 1:
            ancien_X, anciens_bouts = X, bouts
            brins = [retouche(X[bouts[k]:bouts[k + 1]], PAS, trous) for k in range(len(tailles))]
            nb = np.cumsum([0] + [len(b) for b in brins]); Xn = np.concatenate(brins)
            ln = np.concatenate([np.full(len(b), k) for k, b in enumerate(brins)]); idn = np.concatenate([np.arange(len(b)) for b in brins])
            In, Jn = paires_proches(Xn, ln, idn, 1.6 * ECART + 16 * PAS_MAX, ecart_indices)
            if croisement_existe(Xn, nb, In, Jn, clou, PAS):   # une fusion a fait couper un brin voisin : retouche sans fusion
                brins = [retouche(ancien_X[anciens_bouts[k]:anciens_bouts[k + 1]], PAS, trous, fusion=False) for k in range(len(tailles))]
            tailles = [len(b) for b in brins]
            X = np.concatenate(brins)
            lacet = np.concatenate([np.full(n, k) for k, n in enumerate(tailles)])
            indice = np.concatenate([np.arange(n) for n in tailles])
            bouts = np.cumsum([0] + tailles)
            fixe = np.zeros(len(X), bool); fixe[bouts[:-1]] = True; fixe[bouts[1:] - 1] = True
            precedent = np.arange(len(X)) - 1; suivant = np.arange(len(X)) + 1
            precedent[bouts[:-1]] = bouts[:-1]; suivant[bouts[1:] - 1] = bouts[1:] - 1
            I, J = paires_proches(X, lacet, indice, 1.6 * ECART + 16 * PAS_MAX, ecart_indices)
    return [X[bouts[k]:bouts[k + 1]] for k in range(len(tailles))]


def _detend_travail(args):
    lignes, trous, clou, f = args
    return detend(lignes, trous, clou, f)


def force_de_l_image(n, images=48, fenetre=0.5):
    """L'intensité à l'image n d'une lettre (1 … images) : 4 poids (1 − poids), le poids étant celui du raccord."""
    s = lisse(n / images)
    poids = lisse(min(1, max(0, (s - (0.5 - fenetre / 2)) / fenetre)))
    return 4 * poids * (1 - poids)


def dessins_detendus(tresse, hauteur=800, largeur=800, marge=60, seulement=None, verifie=True):
    """Les dessins du film conforme, détendus pendant le raccord. seulement : les numéros d'image (comme dans la page, à
    partir de 1) à calculer. Rend (dessins, durées, anomalies)."""
    dessins, durees, _ = dessins_conforme(tresse, hauteur=hauteur, largeur=largeur, marge=marge)
    nb = max(map(abs, tresse)) + 1
    # les images à détendre : indépendantes, calculées en parallèle sur tous les cœurs
    travaux = []
    for k, (lignes, trous, clou, axe) in enumerate(dessins):
        if seulement is not None and k + 1 not in seulement: continue
        f = 0.0 if k == 0 else force_de_l_image((k - 1) % 48 + 1)
        if f > 0: travaux.append((k, lignes, trous, clou, f))
    detendues = {}
    if travaux:
        import multiprocessing
        with multiprocessing.get_context('fork').Pool(min(len(travaux), os.cpu_count() or 1)) as pool:
            for k, lignes in zip([t[0] for t in travaux], pool.imap(_detend_travail, [t[1:] for t in travaux], chunksize=1)):
                detendues[k] = lignes
    res, anomalies = [], []
    for k, (lignes, trous, clou, axe) in enumerate(dessins):
        numero = k + 1
        if seulement is not None and numero not in seulement: continue
        nouvelles = detendues.get(k, lignes)
        if verifie and k > 0:
            lettre = (k - 1) // 48
            mots = [calcule_autofn_de_tresse(tresse[:lettre + j], nb) for j in (0, 1)]
            en_ordre = sorted(np.asarray(trous).tolist())
            i = abs(tresse[lettre])
            if abs(trous[i - 1][0] - trous[i][0]) > 1e-6 and [lit_mot(p, en_ordre) for p in nouvelles] not in mots:
                anomalies.append((numero, 'mots'))
            c = nb_croisements(nouvelles, clou)
            if c: anomalies.append((numero, f'{c} croisements'))
        res.append((nouvelles, trous, clou, axe))
    return res, durees, anomalies


def compare(mot, numero, hauteur=800, largeur=800, marge=60):
    from PIL import Image
    avant, _, _ = dessins_conforme(mot, hauteur=hauteur, largeur=largeur, marge=marge)
    apres, _, anomalies = dessins_detendus(mot, hauteur, largeur, marge, seulement={numero})
    print('image', numero, ': force %.2f' % force_de_l_image((numero - 2) % 48 + 1), anomalies)
    m = Image.new('RGB', (2 * largeur, hauteur), 'white')
    m.paste(en_image_pil(surface_conforme(avant[numero - 1], hauteur, largeur, marge, False, largeur_brin=3)).convert('RGB'), (0, 0))
    m.paste(en_image_pil(surface_conforme(apres[0], hauteur, largeur, marge, False, largeur_brin=3)).convert('RGB'), (largeur, 0))
    nom = '_'.join(map(str, mot)) + f'_image{numero}' + ''.join(f'_{a}' for a in sys.argv[3:])
    os.makedirs('imgs', exist_ok=True)
    m.save(f'imgs/essai_lissage_{nom}.png')
    print(f'écrit imgs/essai_lissage_{nom}.png (à gauche le film actuel, à droite détendu)')


def ecrit_json(mot, dessins, anomalies, fichier, marge=60, tolerance=0.15):
    """Les images au format du banc d'essai (comme `essai_regions.exporte`) : coordonnées de l'image de 800 × 800, marge
    comprise, lacets simplifiés à `tolerance` pixel près."""
    import json
    from essai_regions import simplifie
    plat = lambda pts: [round(float(v), 1) for v in (np.asarray(pts) + marge).ravel()]
    images = []
    for k, (lignes, trous, clou, axe) in enumerate(dessins):
        if k == 0:
            na = len(axe) - 3
            axe = axe[:na] + [axe[na + 1], axe[na], axe[na + 2]]
        else:
            na = len(axe) - 5
        construction, opacites = [], []
        for x in axe:
            seg, alpha = (x if isinstance(x, tuple) else (x, 1.0))
            if alpha <= 0: continue
            construction += plat(seg); opacites.append(round(float(alpha), 3))
        images.append({'lacets': [plat(simplifie(np.asarray(l, float), tolerance)) for l in lignes], 'trous': plat(trous), 'clou': plat([clou]),
                       'construction': construction, 'opacites': opacites, 'ab': na})
    os.makedirs(os.path.dirname(fichier) or '.', exist_ok=True)
    with open(fichier, 'w') as f:
        json.dump({'mot': mot, 'methode': 'detendu', 'anomalies': [list(map(str, a)) for a in anomalies], 'images': images},
                  f, separators=(',', ':'))


def film(mot, fichier, hauteur=800, largeur=800, marge=60, construction=False, json_banc=None):
    dessins, durees, anomalies = dessins_detendus(mot, hauteur, largeur, marge)
    if json_banc: ecrit_json(mot, dessins, anomalies, json_banc, marge)
    ffmpeg = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{largeur}x{hauteur}',
                               '-r', '25', '-i', '-', *ENCODEUR, fichier], stdin=subprocess.PIPE)
    for d, ms in zip(dessins, durees):
        donnees = bytes(surface_conforme(d, hauteur, largeur, marge, construction, largeur_brin=3).get_data())
        for _ in range(max(1, round(ms / 40))): ffmpeg.stdin.write(donnees)
    ffmpeg.stdin.close()
    ffmpeg.wait()
    return anomalies


if __name__ == '__main__':
    for a in [a for a in sys.argv if '=' in a]:   # réglages : PAS=3 ITERATIONS=300 …
        nom, valeur = a.split('=')
        globals()[nom] = type(globals()[nom])(float(valeur)) if nom in globals() else None
    REGLAGES = [a for a in sys.argv if '=' in a]
    sys.argv = [a for a in sys.argv if '=' not in a] + REGLAGES
    if len(sys.argv) > 1 and sys.argv[1] == 'film':
        mot = [int(x) for x in sys.argv[2].split()]
        fichier = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].endswith('.mp4') else 'imgs/essai_lissage_film_' + '_'.join(map(str, mot)) + '.mp4'
        anomalies = film(mot, fichier, construction='construction' in sys.argv)
        print(fichier, ':', len(anomalies), 'anomalies', anomalies[:30])
        sys.exit()
    mot = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1 -2 1 -2 1 -2').split()]
    compare(mot, int(sys.argv[2]) if len(sys.argv) > 2 and '=' not in sys.argv[2] else 264)
