'''Écrit reference_film.json : sorties de Triangulation.py (classe Film) et de tresses.py pour comparer la
réécriture OCaml (étape 3 : transport, tension, dessin en droites et congés).
- "monotone", "deux_arcs" : cas tirés au hasard.
- "films" : pour chaque tresse d'essai, les données fixes du film (dispositions, bords, clou...), l'état de départ
  (Film.__init__ : pas encore traduit en OCaml) et l'état après chaque lettre ; pour certains états, un pas de
  tension (tend) et un résumé des polylignes dessinées (nombre de points, sommes, un point sur 25).
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_film.py'''
import copy
import json
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, 'programmes')
from tresses import deux_arcs
from Triangulation import Film, monotone


def noeud(n):
    return [int(n[1])] if n[0] == 'v' else [int(n[1]), int(n[2]), float(n[3])]


def courbes(film):
    return [[noeud(n) for n in c] for c in film.courbes]


def etat(film):
    m = film.maillage
    return {'pos': m.pos.tolist(), 'triangles': sorted(sorted(int(s) for s in t) for t in m.triangles),
            'courbes': courbes(film), 'trous': [int(t) for t in film.trous], 'etape': film.etape}


def resume(p):
    p = np.asarray(p, dtype=float)
    return {'n': len(p), 'somme': p.sum(axis=0).tolist(), 'echantillon': p[::25].tolist()}


def avec_tension(film, **options):
    f = copy.deepcopy(film)
    f.tend(0.15, f.dispositions[f.etape][1], **options)
    return courbes(f)


def donnees_fixes(film):
    def disp(d): return {'abscisses': [float(x) for x in d[0]], 'ecart': float(d[1])}
    return {'hauteur': film.hauteur, 'largeur': film.largeur, 'nb_trous': film.nb_trous,
            'dispositions': [disp(d) for d in film.dispositions], 'milieux': [disp(d) for d in film.milieux],
            'clou': int(film.clou), 'haut': [int(s) for s in film.haut], 'bas': [int(s) for s in film.bas],
            'decalage_bas': float(film.decalage_bas),
            'place_du_clou': [int(film.place_du_clou[0]), float(film.place_du_clou[1])], 'y_axe': float(film.y_axe)}


def releve(film, avec_details):
    e = etat(film)
    e['mots'] = film.mots()
    if avec_details:
        e['tend'] = avec_tension(film)
        e['tend_portee'] = avec_tension(film, degagement=2.0, portee_sinus=10.0)
        e['polylignes'] = [resume(p) for p in film.polylignes()]
    return e


hasard = random.Random(2026)
reference = {'monotone': [], 'deux_arcs': [], 'films': []}
for _ in range(40):
    v = [hasard.uniform(-5, 5) for _ in range(hasard.randint(0, 12))]
    reference['monotone'].append({'valeurs': v, 'resultat': monotone(v)})
for _ in range(40):
    def unitaire():
        a = hasard.uniform(0, 2 * math.pi)
        return np.array((math.cos(a), math.sin(a)))
    p0, p1 = np.array((hasard.uniform(0, 100), hasard.uniform(0, 100))), np.array((hasard.uniform(0, 100), hasard.uniform(0, 100)))
    t0, t1 = unitaire(), unitaire()
    reference['deux_arcs'].append({'p0': p0.tolist(), 't0': t0.tolist(), 'p1': p1.tolist(), 't1': t1.tolist(),
                                   'resultat': np.asarray(deux_arcs(p0, t0, p1, t1)).tolist()})

for tresse in ([4, 3, -1, -1, 2, -4, 1], [1, -2, 1, -2, 1, -2, 3, -1, 2]):
    film = Film(tresse)
    details = {0, 1, len(tresse)}
    etats, images = [releve(film, True)], []
    for k, sigma in enumerate(tresse, start=1):
        images.append(film.lettre(sigma))
        etats.append(releve(film, k in details))
    reference['films'].append({'tresse': tresse, 'fixe': donnees_fixes(film), 'images': images, 'etats': etats})

with open(os.path.join(os.path.dirname(__file__), 'reference_film.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(reference, f, separators=(',', ':'))
