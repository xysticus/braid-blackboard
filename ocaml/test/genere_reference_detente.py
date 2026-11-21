'''Écrit reference_detente.json : la détente du raccord (etude/lacets/essai_lissage.py, `detend`) pour comparer la réécriture
OCaml (Detente). Deux images du film conforme de (σ₁σ₂⁻¹)³ (800 × 800, marges 60) : l'image 264 (milieu d'un raccord,
force 0,97) et l'image 258 (début de raccord, force faible). Pour chacune : les entrées (lacets, trous, clou, force) et
la sortie (nombre de points de chaque lacet, un point sur 25, le dernier).
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_detente.py'''
import json
import os
import sys

import numpy as np

sys.path.insert(0, 'python')
sys.path.insert(0, 'etude/lacets')
from Conforme import dessins_conforme
from essai_lissage import detend, force_de_l_image

tresse = [1, -2, 1, -2, 1, -2]
dessins, _, _ = dessins_conforme(tresse, hauteur=800, largeur=800, marge=60)
images = []
for numero in (264, 258):
    lignes, trous, clou, _ = dessins[numero - 1]
    force = force_de_l_image((numero - 2) % 48 + 1)
    sortie = detend(lignes, trous, clou, force)
    images.append({
        'numero': numero, 'force': force,
        'lignes': [np.asarray(l).tolist() for l in lignes], 'trous': np.asarray(trous).tolist(), 'clou': np.asarray(clou).tolist(),
        'sortie': [{'n': len(p), 'echantillon': p[::25].tolist(), 'dernier': p[-1].tolist()} for p in sortie],
    })
with open(os.path.join(os.path.dirname(__file__), 'reference_detente.json'), 'w') as f:
    json.dump({'images': images}, f)
print('écrit ocaml/test/reference_detente.json', [(i['numero'], round(i['force'], 3), [s['n'] for s in i['sortie']]) for i in images])
