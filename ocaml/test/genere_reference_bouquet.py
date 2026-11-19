'''Écrit reference_bouquet.json : sorties de Bouquet.py (le premier bouquet, la classe Pousse) pour comparer la réécriture
OCaml (étape 8 : lib/bouquet.ml).
- "plantes" : à cinq instants, pour chaque plante du bouquet : centre, phases, positions des trous, direction de la tige ;
- "images" : l'état de la triangulation après les images 0, 1, 10, 40, 80, 120, 169 du film (la boucle de film_bouquet :
  t = n × 0,08 s, 169 images) : positions des trous, et pour chaque lacet un résumé de sa polyligne (nombre de points, un
  point sur 25, dernier point, somme).
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_bouquet.py   (une vingtaine de secondes)'''
import copy
import json
import os
import sys

import numpy as np

sys.path.insert(0, 'python')
from Bouquet import BOUQUET, Pousse


def resume(p):
    p = np.asarray(p, dtype=float)
    return {'n': len(p), 'somme': p.sum(axis=0).tolist(), 'echantillon': p[::25].tolist(), 'dernier': p[-1].tolist()}


groupes = copy.deepcopy(BOUQUET)
pousse = Pousse(groupes)
reference = {'plantes': [], 'images': []}
for t in (0.5, 3.0, 6.0, 9.0, 13.5):
    for n, g in enumerate(pousse.groupes):
        trous = (pousse.trous_de_feuille if g['sorte'] == 'feuille' else pousse.trous_de_fleur)(n, t)
        reference['plantes'].append({
            'n': n, 't': t, 'centre': pousse.centre(n, t).tolist(), 'phases': list(pousse.phases(g, t)),
            'trous': [list(map(float, p)) for p in trous], 'tige': pousse.direction_de_tige(n).tolist()})
pas = 2 / 25
nombre = round(13.5 / pas)
demandees = (0, 1, 10, 40, 80, 120, nombre)
for n in range(nombre + 1):
    t = n * pas
    if n: pousse.deplace(*pousse.cibles(t), pas_max=2 * pousse.e)
    if n in demandees:
        reference['images'].append({'n': n, 't': t, 'positions': pousse.positions().tolist(),
                                    'lignes': [resume(l) for l in pousse.polylignes()]})
with open(os.path.join(os.path.dirname(__file__), 'reference_bouquet.json'), 'w') as f:
    json.dump(reference, f)
print(len(reference['plantes']), 'plantes,', len(reference['images']), 'images')
