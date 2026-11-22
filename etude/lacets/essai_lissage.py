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
    brins = [reechantillonne(np.asarray(l, float), PAS) for l in lignes]
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
        X = X + F
        # la barrière des trous : aucun point plus près d'un trou que `barriere` (la répulsion n'est qu'une force, que la tension des
        # boucles serrées peut vaincre) ; des segments de longueur sous 2 barriere ne peuvent alors pas passer par-dessus un trou
        barriere = max(0.6 * RAYON_TROU, 0.75 * PAS)
        # sur les segments, pas seulement les points : deux points écartés par la répulsion peuvent laisser entre eux un segment
        # qui enjambe le trou ; un segment trop proche est repoussé en bloc (ses deux bouts du même vecteur). Un segment ne bougeant
        # que de PAS_MAX par itération, il ne peut plus passer par-dessus un trou.
        dans_brin = np.ones(len(X) - 1, bool)
        dans_brin[bouts[1:-1] - 1] = False
        ia = np.nonzero(dans_brin)[0]
        for c in trous:
            A, B = X[ia], X[ia + 1]
            AB = B - A
            t = np.clip(((c - A) * AB).sum(1) / np.maximum((AB * AB).sum(1), 1e-12), 0, 1)
            V = A + t[:, None] * AB - c
            ds = np.hypot(*V.T)
            proche = (ds < barriere) & (ds > 1e-9)
            if proche.any():
                pousse = V[proche] * (np.minimum(barriere - ds[proche], PAS_MAX) / ds[proche])[:, None]   # pas plus que PAS_MAX : sinon le segment saute par-dessus un brin voisin
                deplacement = np.zeros_like(X)
                np.add.at(deplacement, ia[proche], pousse); np.add.at(deplacement, ia[proche] + 1, pousse)
                compte = np.zeros(len(X)); np.add.at(compte, ia[proche], 1); np.add.at(compte, ia[proche] + 1, 1)
                bouge = (compte > 0) & ~fixe
                X[bouge] += deplacement[bouge] / compte[bouge][:, None]
        # rééchantillonner pour garder des points réguliers : toutes les 25 itérations, et dès qu'un segment dépasse 1,5 PAS (la
        # répulsion n'agit qu'entre les points : deux longs segments pourraient se croiser, leurs points restant écartés)
        longueurs = np.hypot(*np.diff(X, axis=0).T)
        longueurs[bouts[1:-1] - 1] = 0
        if (it % 25 == 24 or longueurs.max() > 1.5 * PAS) and it < iterations - 1:
            brins = [reechantillonne(X[bouts[k]:bouts[k + 1]], PAS) for k in range(len(tailles))]
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
