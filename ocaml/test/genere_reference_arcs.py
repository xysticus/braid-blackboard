'''Écrit reference_arcs.json : sorties de Arcs.py et Raccord.py pour comparer la réécriture OCaml (étape 4 : films
d'arcs, diagramme de courbes, maillage à bord convexe).
- "pchip" : cas tirés au hasard (pentes, et une valeur interpolée).
- "films" : pour chaque méthode (comme METHODES de Arcs.py) et chaque tresse d'essai, les données du film au départ
  (maillage, trous, largeurs) et, après chaque lettre jouée en 12 images, l'état (positions, triangles, courbes,
  places), les mots relus et un résumé des rubans.
Les arêtes à retourner sont cherchées dans l'ordre de l'OCaml (`cherche_arete_dans_l_ordre`).
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference_arcs.py'''
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, 'python')
import Triangulation
from Arcs import FilmArcs, DiagrammeCourbes, pchip, hermite


def cherche_arete_dans_l_ordre(self):
    '''`Maillage.cherche_arete_a_retourner`, arêtes parcourues dans l'ordre de l'OCaml (arêtes rangées ; pour les deux
    triangles d'une arête, le plus grand d'abord, comme la liste construite par `Maillage.aretes` en OCaml).
    L'ordre du Python est celui d'un set de frozensets, qui dépend de l'histoire des insertions (il change même après
    un deepcopy). Quand plusieurs arêtes sont à retourner en même temps, l'ordre des retournements change les courbes
    (les points de l'arête retournée disparaissent) : jusqu'à 3 % d'une arête, que la tension efface ensuite peu à
    peu. Avec les points alignés de l'axe (trous fixes à gauche, diagramme), il peut même changer la triangulation
    (points cocycliques). On fixe donc l'ordre pour comparer exactement.'''
    aretes = self.aretes()
    for (a, c) in sorted(aretes):
        tris = sorted(aretes[(a, c)], key=lambda t: sorted(t), reverse=True)
        if len(tris) != 2: continue
        b, d = [next(iter(t - {a, c})) for t in tris]
        if self.cotangente(b, a, c) + self.cotangente(d, a, c) >= -1e-9: continue
        if not self.convexe(a, b, c, d): continue
        if (min(b, d), max(b, d)) in aretes: continue
        return a, b, c, d
    return None


Triangulation.Maillage.cherche_arete_a_retourner = cherche_arete_dans_l_ordre


def noeud(n):
    return [int(n[1])] if n[0] == 'v' else [int(n[1]), int(n[2]), float(n[3])]


def resume(p):
    p = np.asarray(p, dtype=float)
    return {'n': len(p), 'somme': p.sum(axis=0).tolist(), 'echantillon': p[::25].tolist()}


def etat(film):
    m = film.maillage
    return {'pos': m.pos.tolist(), 'triangles': sorted(sorted(int(s) for s in t) for t in m.triangles),
            'courbes': [[noeud(n) for n in c] for c in film.courbes], 'places': [int(s) for s in film.places],
            'mots': film.mots(), 'rubans': [resume(film.ruban(k)) for k in range(len(film.courbes))]}


hasard = random.Random(2026)
reference = {'pchip': [], 'films': []}
for _ in range(30):
    lignes, colonnes = hasard.randint(1, 8), hasard.randint(1, 4)
    y = np.array([[hasard.uniform(0, 1) for _ in range(colonnes)] for _ in range(lignes)])
    t = hasard.uniform(0, lignes - 1)
    m = pchip(y)
    reference['pchip'].append({'y': y.tolist(), 'pentes': m.tolist(), 't': t, 'valeur': np.atleast_1d(hermite(y, m, t)).tolist()})

METHODES = {'rubans': (FilmArcs, dict(ecart_fixes=30)), 'rubans_gauche': (FilmArcs, dict(fixes='gauche')),
            'arcs': (FilmArcs, {}), 'diagramme': (DiagrammeCourbes, {})}
for methode, (classe, options) in METHODES.items():
    for tresse in ([4, 3, -1, -1, 2, -4, 1], [1, -2, 1, -2, 1, -2, 3, -1, 2]):
        film = classe(tresse, **options)
        depart = etat(film)
        depart.update({'voyageurs': [int(s) for s in film.voyageurs], 'fixes': [int(s) for s in film.fixes],
                       'largeurs': film.largeurs.tolist(), 'pentes': film.pentes.tolist(),
                       'places_au_temps': [film.places_au_temps(T).tolist() for T in (0, 0.3, 1.5, len(tresse))]})
        etats = []
        for sigma in tresse:
            film.lettre(sigma, images=12)
            etats.append(etat(film))
        reference['films'].append({'methode': methode, 'tresse': tresse, 'depart': depart, 'etats': etats})

with open(os.path.join(os.path.dirname(__file__), 'reference_arcs.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(reference, f, separators=(',', ':'))
