'''Écrit reference_python.txt : pour chaque tresse, l'automorphisme calculé par tresses.py.
Une ligne par tresse : « lettres ; nombre de trous ; image de x_1 / image de x_2 / ... » (entiers séparés par des espaces).
Lancer depuis la racine du dépôt : python ocaml/test/genere_reference.py'''
import os
import random
import sys

sys.path.insert(0, 'python')
from tresses import calcule_autofn_de_tresse

def ligne(tresse, nb_trous):
    auto = calcule_autofn_de_tresse(tresse, nb_trous)
    entiers = lambda l: ' '.join(map(str, l))
    return f"{entiers(tresse)} ; {nb_trous} ; {' / '.join(entiers(m) for m in auto)}"

hasard = random.Random(2026)
tresses = [[], [1], [-1], [1, 1, 2, 2], [4, 3, -1, -1, 2, -4, 1], [1, -2, 1, -2, 1, -2, 3, -1, 2]]
for _ in range(300):
    n = hasard.randint(2, 7)
    tresses.append([hasard.choice([1, -1]) * hasard.randint(1, n - 1) for _ in range(hasard.randint(0, 12))])

with open(os.path.join(os.path.dirname(__file__), 'reference_python.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for t in tresses:
        f.write(ligne(t, 6 if not t else max(map(abs, t)) + 1) + '\n')
