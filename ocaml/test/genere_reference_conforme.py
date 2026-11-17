'''Écrit reference_conforme.json : sorties de Conforme.py pour comparer la réécriture OCaml (étape 7a : la carte de
Schwarz–Christoffel).
- "cartes" : pour de vraies cartes du film (tresse de référence, lettres 1 et 5, quatre instants, haut et bas), les
  sommets, les β, les écarts et antécédents des sommets, delta, des points du bord, des antécédents de points du
  bord, des images de points intérieurs, des antécédents de points intérieurs et l'image d'un demi-cercle.
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_conforme.py'''
import json
import os
import sys

import numpy as np

sys.path.insert(0, 'python')
from Conforme import Carte, Lettre, demi_cercle
from tresses import etat_de_tresse


def c(z): return [float(z.real), float(z.imag)]


tresse = [4, 3, -1, -1, 2, -4, 1]
nb = max(map(abs, tresse)) + 1
reference = {'cartes': []}
for k in (0, 4):
    cle, suivante = etat_de_tresse(tresse[:k], nb), etat_de_tresse(tresse[:k + 1], nb)
    lettre = Lettre(cle, suivante, tresse[k], 680, 680)
    for s in (0.1, 0.45, 0.55, 0.9):
        e = 0 if s < 0.5 else 1
        V = lettre.ligne(e, s)
        for sommets in (V, V.conj()):
            carte = Carte(sommets)
            w = carte.w
            bords = list(np.linspace(w[0] - 60, w[-1] + 60, 13))
            longueurs = [(p, f * carte.tables[p][1][-1]) for p in range(len(carte.tables)) for f in (0.0, 0.3, 0.7, 0.999)]
            interieurs = [complex(x, y) for x in np.linspace(w[0] - 30, w[-1] + 30, 5) for y in (5.0, 40.0, 120.0)]
            images = [carte.image(z) for z in interieurs]
            cibles = [carte.image(complex((w[0] + w[-1]) / 2 + d, 50.0)) for d in (-40.0, 0.0, 40.0)]
            dc = demi_cercle(w[0] - 20, w[-1] + 20)
            arc = carte.chemin(dc, carte.bord(dc[0].real), carte.bord(dc[-1].real))
            reference['cartes'].append({
                'sommets': [c(z) for z in sommets], 'beta': carte.beta.tolist(), 'ecarts': carte.ecarts.tolist(),
                'w': w.tolist(), 'delta': float(carte.delta),
                'bords': [[float(t), c(carte.bord(t))] for t in bords],
                'antecedents_bord': [[p, float(l), carte.antecedent_bord(p, l)] for p, l in longueurs],
                'images': [[c(z), c(i)] for z, i in zip(interieurs, images)],
                'antecedents': [[c(z), c(carte.antecedent(z))] for z in cibles],
                'demi_cercle': [w[0] - 20, w[-1] + 20, [c(z) for z in arc]]})

with open(os.path.join(os.path.dirname(__file__), 'reference_conforme.json'), 'w') as f:
    json.dump(reference, f)
print(len(reference['cartes']), 'cartes')
