'''Écrit reference_meandre.json : sorties de la partie « méandre » de tresses.py et du constructeur de Film
(Triangulation.py), pour comparer la réécriture OCaml (étape 3 bis).
- "tresses" : pour des tresses tirées au hasard (et les deux tresses d'essai), les intervalles de chaque lacet et
  l'état (etat_de_tresse) ; puis, pour chaque lettre, agit (état non réduit) et normalise(reduit(...)).
- "dessins" : dessin_etat de quelques états, résumé des polylignes (nombre de points, sommes, un point sur 25).
- "departs" : pour les deux tresses d'essai, les courbes de Film avant la tension (noeuds_de_polyligne) ; l'état
  après la tension est déjà dans reference_film.json.
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_meandre.py'''
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, 'python')
from tresses import (agit, calcule_autofn_de_tresse, dessin_etat, etat_de_tresse, intervalles, normalise,
                     polylignes, reduit)
import Triangulation


def resume(p):
    p = np.asarray(p, dtype=float)
    return {'n': len(p), 'somme': p.sum(axis=0).tolist(), 'echantillon': p[::25].tolist()}


def flottants(etat):
    trous, lacets = etat
    return {'trous': [float(x) for x in trous], 'lacets': [[float(x) for x in l] for l in lacets]}


hasard = random.Random(2026)
essais = [[4, 3, -1, -1, 2, -4, 1], [1, -2, 1, -2, 1, -2, 3, -1, 2]]
tresses = essais + [[hasard.choice([1, -1]) * hasard.randint(1, n - 1) for _ in range(hasard.randint(1, 10))]
                    for n in (hasard.randint(2, 6) for _ in range(60))]

reference = {'tresses': [], 'dessins': [], 'departs': []}
for t in tresses:
    nb = max(map(abs, t)) + 1
    actions = []
    for k, sigma in enumerate(t):
        etat = etat_de_tresse(t[:k], nb)
        non_reduit = agit(etat, sigma)
        actions.append({'agit': flottants(non_reduit), 'reduit': flottants(normalise(reduit(non_reduit)))})
    reference['tresses'].append({
        'tresse': t, 'nb_trous': nb,
        'intervalles': [intervalles(m) for m in calcule_autofn_de_tresse(t, nb)],
        'etat': flottants(etat_de_tresse(t, nb)), 'actions': actions})

for t, taille in ((essais[0], 400), (essais[1], 400), (essais[0], 800), ([], 800)):
    morceaux, trous, clou, _ = dessin_etat(etat_de_tresse(t, 5 if not t else None), taille, taille)
    reference['dessins'].append({'tresse': t, 'taille': taille, 'trous': trous.tolist(), 'clou': clou.tolist(),
                                 'polylignes': [resume(p) for p in polylignes(morceaux)]})

# courbes de départ avant la tension : on rend tend inopérant le temps de construire le film
tend = Triangulation.Film.tend
Triangulation.Film.tend = lambda self, *a, **k: None
for t in essais:
    film = Triangulation.Film(t)
    reference['departs'].append({'tresse': t, 'courbes': [[[int(n[1])] if n[0] == 'v' else [int(n[1]), int(n[2]), float(n[3])]
                                                          for n in c] for c in film.courbes]})
Triangulation.Film.tend = tend

with open(os.path.join(os.path.dirname(__file__), 'reference_meandre.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(reference, f, separators=(',', ':'))
