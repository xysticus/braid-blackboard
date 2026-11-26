'use strict';
// Le méandre du disque qui descend : une image du film conforme (800 × 800, y vers le bas) portée sur le disque de la vue 3D
// (x suit les positions, z vient vers la personne qui regarde de face ; unité : l'écart entre deux positions). Sans WebGL.
//
// La hauteur : l'image f du film (48 par lettre) est à f / 48 tranches sous le haut de la tresse. Le temps de la lettre dans
// le film, s = 3t² − 2t³ avec t = n / 48, est aussi la loi de l'angle du demi-tour d'un brin à la hauteur t de sa tranche.
//
// Le plan : dans le film, les trous sont irrégulièrement espacés et le demi-tour est aplati. On déforme donc chaque image :
// à chaque hauteur y, x ↦ x' est strictement croissante, et y ↦ z est strictement croissante et ne dépend pas de x. C'est un
// homéomorphisme du plan : il ne crée aucun croisement et ne fait passer aucun lacet de l'autre côté d'un trou. Il est
// choisi pour que les trous tombent exactement sur les brins, et il est continu d'une image à l'autre (aux images clés, il
// ne dépend que des places des trous).

const Disque = (() => {
  const IMAGES_PAR_LETTRE = 48;
  const COTE = 800;               // le cadre des images du film
  const DEMI_HAUTEUR = 400;       // l'écart à l'axe, en pixels du film, qui tombe à z = ±profondeur(n)
  // la demi-profondeur du dessin : elle grandit avec le nombre de brins, comme la largeur du disque
  const profondeur = (n) => Math.max(1.6, 0.46 * n);
  const BORD = 0.9;               // les bords gauche et droit du cadre, au-delà des positions extrêmes
  const FIXE_A = 260, FIXE_DE = 390;   // vers le clou (en bas), x ne dépend plus des trous : le clou reste au milieu, devant
  const PAS_MAX = 6;              // les segments plus longs (en pixels du film) sont découpés : la déformation les courbe

  const lisse = (t) => t * t * (3 - 2 * t);

  // La loi de base de la profondeur : concave, pour que les petits lacets près de l'axe restent visibles autour des brins.
  const base = (d, P) => { const u = d / DEMI_HAUTEUR; return P * 3 * u / (1 + 2 * u); };

  // La lettre (de 0) et le temps de la lettre pour l'image f ; l'image 48 k est la fin de la lettre k − 1.
  function instant(f) {
    const k = f === 0 ? 0 : Math.floor((f - 1) / IMAGES_PAR_LETTRE);
    return { k, s: lisse((f - IMAGES_PAR_LETTRE * k) / IMAGES_PAR_LETTRE) };
  }

  // Les abscisses des trous d'une image clé, de gauche à droite.
  const places = (image) => Array.from(image.trous).filter((_, q) => q % 2 === 0).sort((a, b) => a - b);

  // Interpolation affine par morceaux, croissante ; ancres : [[x, x'], …] rangées par x croissant.
  function parMorceaux(ancres, x) {
    let j = 0;
    while (j + 2 < ancres.length && x > ancres[j + 1][0]) j++;
    const [a, b] = ancres[j], [c, d] = ancres[j + 1];
    return b + (x - a) * (d - b) / (c - a);
  }

  // La déformation de l'image f. cle0 et cle1 : les images clés qui encadrent sa lettre (48 k et 48 (k + 1)).
  function deformation(mot, f, image, cle0, cle1) {
    const n = image.trous.length / 2, { k, s } = instant(f);
    const g = Math.abs(mot[k]) - 1, theta = Math.PI * s;         // les trous qui tournent : places g et g + 1 au début de la lettre
    const trou = (p) => [image.trous[2 * p], image.trous[2 * p + 1]];
    const xDe = (p) => p - (n - 1) / 2, P = profondeur(n);
    const p0 = places(cle0), p1 = places(cle1);
    const rayon = (1 - s) * (p0[g + 1] - p0[g]) / 2 + s * (p1[g + 1] - p1[g]) / 2;
    const centre = (trou(g)[0] + trou(g + 1)[0]) / 2;
    const yAxe = (trou(g)[1] + trou(g + 1)[1]) / 2;

    const ancres = [[0, xDe(0) - BORD]];
    for (let p = 0; p < n; p++) {
      if (p === g) ancres.push([centre - rayon, xDe(g)]);
      else if (p === g + 1) ancres.push([centre + rayon, xDe(g + 1)]);
      else ancres.push([trou(p)[0], xDe(p)]);
    }
    ancres.push([COTE, xDe(n - 1) + BORD]);
    const demiLargeur = (n - 1) / 2 + BORD;
    const fixe = (x) => (x - COTE / 2) * demiLargeur / (COTE / 2);

    // la profondeur : la loi de base, corrigée pour que l'écart a des trous qui tournent tombe à b = ½ sin θ
    const a = base(Math.abs(trou(g)[1] - yAxe), P), b = 0.5 * Math.sin(theta);
    const corrige = (z) => {
      if (a < 1e-6 || b < 1e-6) return z;
      return z <= a ? z * b / a : b + (z - a) * (P - b) / (P - a);
    };

    return (x, y) => {
      const d = y - yAxe, w = Math.min(1, Math.max(0, (d - FIXE_A) / (FIXE_DE - FIXE_A)));
      return [(1 - w) * parMorceaux(ancres, x) + (w > 0 ? w * fixe(x) : 0), Math.sign(d) * corrige(base(Math.abs(d), P))];
    };
  }

  // Une ligne brisée à plat (x, y, x, y, …) du film → à plat (x, z, x, z, …) sur le disque.
  function porte(deforme, ligne) {
    const r = [];
    for (let q = 0; q < ligne.length; q += 2) {
      if (q > 0) {
        const x0 = ligne[q - 2], y0 = ligne[q - 1], morceaux = Math.ceil(Math.hypot(ligne[q] - x0, ligne[q + 1] - y0) / PAS_MAX);
        for (let j = 1; j < morceaux; j++)
          r.push(...deforme(x0 + (ligne[q] - x0) * j / morceaux, y0 + (ligne[q + 1] - y0) * j / morceaux));
      }
      r.push(...deforme(ligne[q], ligne[q + 1]));
    }
    return r;
  }

  // Le contenu du disque à l'image f : { lacets: [[x, z, …], …], trous: [x, z, …], clou: [x, z] }.
  function meandre(mot, f, image, cle0, cle1) {
    const deforme = deformation(mot, f, image, cle0, cle1);
    const points = (plat) => { const r = []; for (let q = 0; q < plat.length; q += 2) r.push(...deforme(plat[q], plat[q + 1])); return r; };
    return { lacets: Array.from(image.lacets, (l) => porte(deforme, l)), trous: points(image.trous), clou: points(image.clou) };
  }

  return { IMAGES_PAR_LETTRE, instant, meandre };
})();

if (typeof module !== 'undefined') module.exports = Disque;
