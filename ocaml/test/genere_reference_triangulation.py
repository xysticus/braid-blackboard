'''Écrit reference_triangulation.json : sorties de Triangulation.py pour comparer la réécriture OCaml (étape 2).
- "delaunay" : maillage_initial sur des trous tirés au hasard ; triangles finaux (la triangulation de Delaunay est
  unique pour des points en position générale : la comparaison ne dépend pas de l'ordre des flips).
- "flips" : courbe_apres_flip sur les lacets du film des deux tresses d'essai, avec des flips imposés (arêtes
  intérieures dont le quadrilatère est convexe, Delaunay ou non) ; seules les courbes modifiées sont écrites.
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_triangulation.py'''
import json
import os
import random
import sys

sys.path.insert(0, 'python')
from Triangulation import Film, maillage_initial


def noeud(n):
    return [int(n[1])] if n[0] == 'v' else [int(n[1]), int(n[2]), float(n[3])]


def triangles(m):
    return sorted(sorted(int(s) for s in t) for t in m.triangles)


def cas_delaunay(hasard):
    n = hasard.randint(2, 8)
    xs = sorted(hasard.sample(range(30, 770), n))
    trous = [(float(x) + hasard.random(), 400.0) for x in xs]
    clou = (hasard.uniform(30, 770), 700.0)
    decalage = hasard.choice([0.31, 6.0, -6.0])
    m, t, c, haut, bas = maillage_initial(trous, clou, 800, 800, decalage)
    return {'trous': trous, 'clou': clou, 'decalage_bas': decalage, 'triangles': triangles(m),
            'indices_trous': list(map(int, t)), 'clou_indice': int(c), 'haut': list(map(int, haut)),
            'bas': list(map(int, bas))}


def cas_flips(film, nb):
    m = film.maillage
    quads = []
    for (a, c), tris in sorted(m.aretes().items()):
        if len(tris) != 2: continue
        b, d = [next(iter(t - {a, c})) for t in tris]
        if m.convexe(a, b, c, d): quads.append((int(a), int(b), int(c), int(d)))
    choisis = quads[:: max(1, len(quads) // nb)][:nb]
    flips = []
    for q in choisis:
        apres = {}
        for k, courbe in enumerate(film.courbes):
            nouvelle = m.courbe_apres_flip(courbe, *q)
            if nouvelle != courbe: apres[k] = [noeud(n) for n in nouvelle]
        flips.append({'quad': q, 'courbes_apres': apres})
    return {'pos': m.pos.tolist(), 'triangles': triangles(m),
            'courbes': [[noeud(n) for n in c] for c in film.courbes], 'flips': flips}


hasard = random.Random(2026)
reference = {'delaunay': [cas_delaunay(hasard) for _ in range(40)], 'flips': []}
for tresse in ([4, 3, -1, -1, 2, -4, 1], [1, -2, 1, -2, 1, -2, 3, -1, 2]):
    film = Film(tresse)
    garder = {0, 1, len(tresse) // 2, len(tresse)}
    if 0 in garder: reference['flips'].append(cas_flips(film, 4))
    for k, sigma in enumerate(tresse, start=1):
        film.lettre(sigma)
        if k in garder: reference['flips'].append(cas_flips(film, 4))

with open(os.path.join(os.path.dirname(__file__), 'reference_triangulation.json'), 'w', encoding='utf-8',
          newline='\n') as f:
    json.dump(reference, f, separators=(',', ':'))
