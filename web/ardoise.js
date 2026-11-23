'use strict';
// L'interface de l'ardoise : lecture du mot, notation en MathML, diagramme de tresse classique, action sur F_n, et les
// trois lecteurs de méandres (image fixe, puis film quand le Web Worker a fini). Le calcul est en OCaml, compilé
// (ardoise_lib.js), et tourne dans travail.js.

// ---------------------------------------------------------------- les tresses d'exemple

const EXEMPLES = [
  { nom: 'σ₁', mot: [1], legende: 'le demi-tour le plus simple' },
  { nom: 'Δ₅', mot: [1, 2, 3, 4, 1, 2, 3, 1, 2, 1], legende: 'demi-tour positif à 5 brins' },
  { nom: 'Δ₅⁻¹', mot: [-1, -2, -1, -3, -2, -1, -4, -3, -2, -1], legende: 'demi-tour négatif à 5 brins' },
  { nom: '(σ₁σ₂)³', mot: [1, 2, 1, 2, 1, 2], legende: 'tour complet à 3 brins : conjugaison par x₁x₂x₃' },
  { nom: 'σ₁σ₂σ₁σ₂⁻¹σ₁⁻¹σ₂⁻¹', mot: [1, 2, 1, -2, -1, -2], legende: 'un mot qui vaut la tresse nulle' },
  { nom: 'σ₂σ₁σ₂⁻¹', mot: [2, 1, -2], legende: 'même tresse que la suivante' },
  { nom: 'σ₁⁻¹σ₂σ₁', mot: [-1, 2, 1], legende: 'même tresse que la précédente' },
  { nom: 'σ₁σ₂⁻¹', mot: [1, -2], legende: 'courte, mais pseudo-Anosov' },
  { nom: '(σ₁σ₂⁻¹)³', mot: [1, -2, 1, -2, 1, -2], legende: '6 lettres, 51 dans F₃ : croissance exponentielle' },
  { nom: 'σ₂σ₃σ₁σ₄σ₃σ₂', mot: [2, 3, 1, 4, 3, 2], legende: 'tresse simple à 5 brins : la permutation (1 3)(2 5)' },
  { nom: 'σ₄σ₃σ₁⁻²σ₂σ₄⁻¹σ₁', mot: [4, 3, -1, -1, 2, -4, 1], legende: 'une tresse à enroulements décroissants' },
  { nom: 'σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂', mot: [1, -2, 1, -2, 1, -2, 3, -1, 2], legende: 'une tresse à nombreux enroulements' },
];

const MAX_BRINS = 8;     // les limites de la page (les mêmes que dans ocaml/web/ardoise_web.ml)
const MAX_LETTRES = 40;
const MAX_BRINS_CONFORME = 6;     // les films des lacets (conforme et triangulation)
const MAX_LETTRES_CONFORME = 14;

// Une seule palette pour toutes les vues : le brin i du diagramme de tresse, le lacet image de x_i dans les quatre films
// et la ligne x_i ↦ … de l'action sur F_n ont la même couleur (les variables CSS --c0 … --c7 de ardoise.css, un peu
// éclaircies en thème sombre, reprennent ces teintes pour le texte).
const PALETTE_DEFAUT = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6', '#0d9aa6', '#e6761a', '#6b4fbb'];
const FOND_DEFAUT = '#ffffff';
// Les couleurs courantes : celles de la tresse mémorisée sélectionnée (voir « les tresses mémorisées »), sinon celles par défaut.
// Le fond est celui des canvas du diagramme de tresse et des quatre méandres ; l'escargot et les iris gardent le leur.
let PALETTE = PALETTE_DEFAUT.slice();
let FOND = FOND_DEFAUT;
const fondDe = (mode) => (mode === 'escargot' || mode === 'bouquet' ? '#fff' : FOND);

// ---------------------------------------------------------------- lecture du mot

const EXPOSANTS = { '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9' };

// Renvoie { mot: [entiers] } ou { erreur: "…" }. Accepte « 1 -2 3 », « σ1 σ2^-1 », « σ₁σ₂⁻¹ », « s1^3 s2 ».
function lisMot(texte) {
  let t = texte.trim();
  if (t === '') return { mot: [] };
  t = t.replace(/[₀-₉]/g, (c) => String(c.charCodeAt(0) - 0x2080))
       .replace(/⁻/g, '^-')
       .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, (c) => EXPOSANTS[c])
       .replace(/[{}]/g, '')
       .replace(/[σΣsS,;]/g, ' ')
       .replace(/\s*\^\s*/g, '^');
  const mot = [];
  for (const jeton of t.split(/\s+/).filter(Boolean)) {
    const m = /^(-?)(\d+)(?:\^(-?)(\d+))?$/.exec(jeton);
    if (!m) return { erreur: `je ne comprends pas « ${jeton} »` };
    const indice = Number(m[2]);
    if (indice === 0) return { erreur: 'σ₀ n\'existe pas : les indices commencent à 1' };
    let signe = m[1] === '-' ? -1 : 1;
    let fois = 1;
    if (m[4] !== undefined) {
      fois = Number(m[4]);
      if (m[3] === '-') signe = -signe;
      if (fois > MAX_LETTRES) return { erreur: `exposant trop grand dans « ${jeton} »` };
    }
    for (let j = 0; j < fois; j++) mot.push(signe * indice);
    if (mot.length > 10 * MAX_LETTRES) break;
  }
  const brins = mot.reduce((a, k) => Math.max(a, Math.abs(k)), 0) + 1;
  if (mot.length > MAX_LETTRES) return { erreur: `${mot.length} lettres : la page en accepte ${MAX_LETTRES} au plus` };
  if (brins > MAX_BRINS) return { erreur: `${brins} brins : la page en accepte ${MAX_BRINS} au plus (σ₁ … σ${MAX_BRINS - 1})` };
  return { mot };
}

const nbBrins = (mot) => mot.reduce((a, k) => Math.max(a, Math.abs(k)), 0) + 1;

// ---------------------------------------------------------------- notation mathématique (MathML)

const MOINS = '<mrow><mo>−</mo><mn>1</mn></mrow>';

function sigmaMath(k) {
  const i = Math.abs(k);
  return k > 0
    ? `<math><msub><mi>σ</mi><mn>${i}</mn></msub></math>`
    : `<math><msubsup><mi>σ</mi><mn>${i}</mn>${MOINS}</msubsup></math>`;
}

// x_i^p ; p = 1 : x_i sans exposant
function xMath(i, p) {
  if (p === 1) return `<math><msub><mi>x</mi><mn>${i}</mn></msub></math>`;
  const exposant = p < 0 ? `<mrow><mo>−</mo><mn>${-p}</mn></mrow>` : `<mn>${p}</mn>`;
  return `<math><msubsup><mi>x</mi><mn>${i}</mn>${exposant}</msubsup></math>`;
}

// Un mot de F_n (entiers) en puissances : x₁ x₁ x₂⁻¹ → x₁² x₂⁻¹. Le mot vide est 1.
function motFnMath(mot) {
  if (mot.length === 0) return '<math><mn>1</mn></math>';
  const morceaux = [];
  for (const k of mot) {
    const i = Math.abs(k), s = Math.sign(k);
    const dernier = morceaux[morceaux.length - 1];
    if (dernier && dernier.i === i && Math.sign(dernier.p) === s) dernier.p += s;
    else morceaux.push({ i, p: s });
  }
  return morceaux.map(({ i, p }) => xMath(i, p)).join('');
}

function afficheMot(mot) {
  const zone = document.getElementById('mot-math');
  const info = document.getElementById('mot-info');
  if (mot.length === 0) {
    zone.innerHTML = '<math><mn>1</mn></math>';
    info.textContent = 'Mot vide : la tresse nulle (ou écris un mot).';
    return;
  }
  zone.innerHTML = mot.map(sigmaMath).join('');
  const n = nbBrins(mot);
  info.innerHTML = `${mot.length} lettre${mot.length > 1 ? 's' : ''}, ${n} brins : un élément de <math><msub><mi>B</mi><mn>${n}</mn></msub></math> ; le mot est montré tel qu'il est écrit, sans réduction.`;
}

// ---------------------------------------------------------------- l'action sur F_n

function afficheFn(mot, ardoise) {
  const zone = document.getElementById('fn-images');
  const titre = document.getElementById('titre-fn');
  if (mot.length === 0) { titre.innerHTML = ''; zone.textContent = ''; return; }
  const r = ardoise.analyse(mot);
  if (r.erreur) { zone.textContent = r.erreur; return; }
  titre.innerHTML = `<math><msub><mi>F</mi><mn>${r.n}</mn></msub></math>`;
  const lignes = [];
  Array.from(r.fn).forEach((image, j) => {
    const entiers = Array.from(image);
    const identite = entiers.length === 1 && entiers[0] === j + 1;
    lignes.push(`<div class="fn-ligne${identite ? ' identite' : ''}" style="color: var(--c${j % PALETTE.length})">${xMath(j + 1, 1)}<span class="fleche">↦</span>` +
      `<span class="mot">${motFnMath(entiers)}</span></div>`);
  });
  zone.innerHTML = lignes.join('');
}

// ---------------------------------------------------------------- le diagramme de tresse classique

// Les générateurs de haut en bas, un brin par couleur qui suit son brin d'un croisement à l'autre ; au croisement
// σ_k positif le brin qui va de droite à gauche passe dessus (comme dans les notebooks, ipynbks/CanvasTresse*.ipynb).

function dessineTresse(canvas, mot) {
  const brins = nbBrins(mot);
  const maille = Math.max(18, Math.min(52, 560 / Math.max(mot.length, 1)));
  const marge = 16;
  // à droite, une colonne : le générateur de chaque ligne (σ₁, σ₂⁻¹…), aligné sur son croisement
  const police = Math.max(11, Math.min(16, maille * 0.5));
  const colonne = 3.2 * police;
  const largeurDiagramme = (brins - 1) * maille + 2 * marge;
  const largeur = largeurDiagramme + colonne;
  const hauteur = mot.length * maille + 2 * marge;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(largeur * dpr);
  canvas.height = Math.round(hauteur * dpr);
  canvas.style.width = largeur + 'px';
  canvas.style.height = hauteur + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = FOND;
  ctx.fillRect(0, 0, largeur, hauteur);
  ctx.lineCap = 'butt';
  const brin = Math.max(2.2, maille / 9), trou = maille / 3;
  const couleurs = Array.from({ length: brins }, (_, i) => PALETTE[i % PALETTE.length]);

  const diagonale = (x0, x1, couleur) => {
    const trace = (largeurTrait, couleurTrait, d) => {
      ctx.beginPath();
      ctx.strokeStyle = couleurTrait;
      ctx.lineWidth = largeurTrait;
      ctx.moveTo(x0, -d);
      ctx.bezierCurveTo(x0, maille / 2, x1, maille / 2, x1, maille + d);
      ctx.stroke();
    };
    trace(trou, FOND, 0);        // le liseré de la couleur du fond coupe ce qui passe dessous
    trace(brin, couleur, 1);
  };

  // le texte est de la couleur la plus lisible sur le fond choisi
  ctx.fillStyle = luminance(FOND) > 0.4 ? '#4a5160' : '#d6dae3';
  ctx.font = `${police}px system-ui, sans-serif`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  mot.forEach((k, ligne) => ctx.fillText(nomLettre(k), largeurDiagramme + 4, marge + (ligne + 0.5) * maille));

  mot.forEach((k, ligne) => {
    const col = Math.abs(k) - 1;
    ctx.save();
    ctx.translate(marge, marge + ligne * maille);
    for (let i = 0; i < brins; i++) {
      if (i === col) {
        const gd = () => diagonale(i * maille, (i + 1) * maille, couleurs[col]);
        const dg = () => diagonale((i + 1) * maille, i * maille, couleurs[col + 1]);
        if (k > 0) { gd(); dg(); } else { dg(); gd(); }
      } else if (i !== col + 1) {
        ctx.beginPath();
        ctx.strokeStyle = couleurs[i];
        ctx.lineWidth = brin;
        ctx.moveTo(i * maille, 0);
        ctx.lineTo(i * maille, maille);
        ctx.stroke();
      }
    }
    ctx.restore();
    [couleurs[col], couleurs[col + 1]] = [couleurs[col + 1], couleurs[col]];
  });
}

// ---------------------------------------------------------------- dessin d'une image de méandre


function trace(ctx, p) {
  if (p.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(p[0], p[1]);
  for (let k = 2; k < p.length; k += 2) ctx.lineTo(p[k], p[k + 1]);
  ctx.stroke();
}

function disques(ctx, p, rayon, couleur) {
  ctx.fillStyle = couleur;
  for (let k = 0; k < p.length; k += 2) {
    ctx.beginPath();
    ctx.arc(p[k], p[k + 1], rayon, 0, 2 * Math.PI);
    ctx.fill();
  }
}

// ---- l'escargot : port de Dessin.cadre_escargot (ocaml/dessin/dessin.ml)

const rgb = (r, v, b, a = 1) => `rgba(${Math.round(r * 255)}, ${Math.round(v * 255)}, ${Math.round(b * 255)}, ${a})`;
const COQUILLE = [rgb(0.47, 0.29, 0.14), rgb(0.86, 0.75, 0.56), rgb(0.33, 0.19, 0.09), rgb(0.70, 0.52, 0.30)];
const CHAIR = rgb(0.74, 0.65, 0.52);
const CERNE = rgb(0.24, 0.15, 0.08);

// `echelle` : 1 pour un canvas de la taille du film ; 2, 4… pour une image plus grande (export) : le dessin est le même, agrandi.
function dessineEscargot(canvas, im, echelle = 1) {
  const ctx = canvas.getContext('2d');
  ctx.setTransform(echelle, 0, 0, echelle, 0, 0);
  const l = canvas.width / echelle, h = canvas.height / echelle;
  const fond = ctx.createLinearGradient(0, 0, 0, h);
  fond.addColorStop(0, rgb(0.66, 0.80, 0.52));
  fond.addColorStop(1, rgb(0.38, 0.58, 0.30));
  ctx.fillStyle = fond;
  ctx.fillRect(0, 0, l, h);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const [cx, cy, rayon] = im.coquille;
  // d'abord le corps (hors de la coquille), puis la coquille par-dessus ; les arcs des yeux ne montent pas dans la coquille
  for (const dedans of [false, true]) {
    im.lacets.forEach((p, k) => {
      if (dedans && k >= im.anneau) return;
      ctx.save();
      ctx.beginPath();
      if (dedans) {
        ctx.arc(cx, cy, rayon, 0, 2 * Math.PI);
        ctx.clip();
      } else {
        ctx.rect(0, 0, l, h);
        ctx.moveTo(cx + rayon, cy);
        ctx.arc(cx, cy, rayon, 0, 2 * Math.PI);
        ctx.clip('evenodd');
      }
      const epaisseur = dedans ? 0.8 * im.ecart : 1.5 * im.ecart;   // le corps : chair épaisse
      ctx.strokeStyle = CERNE;
      ctx.lineWidth = epaisseur + 1.6 * im.e;
      trace(ctx, p);
      ctx.strokeStyle = dedans ? COQUILLE[k % COQUILLE.length] : CHAIR;
      ctx.lineWidth = epaisseur;
      trace(ctx, p);
      ctx.restore();
    });
  }
  if (im.apparition > 0) {   // les yeux
    for (let j = 0; j < im.yeux.length; j += 2) {
      const x = im.yeux[j], y = im.yeux[j + 1];
      ctx.fillStyle = rgb(0.12, 0.08, 0.05, im.apparition);
      ctx.beginPath(); ctx.arc(x, y, 6 * im.e, 0, 2 * Math.PI); ctx.fill();
      ctx.fillStyle = rgb(1, 1, 1, im.apparition);
      ctx.beginPath(); ctx.arc(x + 2 * im.e, y - 2 * im.e, 1.8 * im.e, 0, 2 * Math.PI); ctx.fill();
    }
  }
}

// ---- le bouquet : port de Pousse.dessine (python/Bouquet.py)

const VERT = [0.26, 0.56, 0.24], SOMBRE = [0.16, 0.38, 0.16], BLANC = [1, 1, 1];
const melange = (u, a, b) => a.map((x, i) => (1 - u) * x + u * b[i]);

// Chemin de la région où l'on peint la fleur : grand disque autour de la tête privé d'un coin de 50° dans la direction de
// la tige, ce coin ne commençant qu'au-delà des sépales (la couleur ne descend pas sur la tige).
function secteurDeFleur(ctx, cx, cy, tige, rayonFleur, rayonSepales) {
  const R = 2.6 * rayonFleur, r = 1.1 * rayonSepales, demi = 25 * Math.PI / 180;
  ctx.arc(cx, cy, R, tige + demi, tige - demi + 2 * Math.PI);
  ctx.arc(cx, cy, r, tige - demi, tige + demi);
  ctx.closePath();
}

// Le lacet rempli d'une couleur transparente (0,16), puis tracé.
function traceFerme(ctx, p, motif, largeur) {
  if (p.length < 4) return;
  ctx.beginPath();
  ctx.moveTo(p[0], p[1]);
  for (let k = 2; k < p.length; k += 2) ctx.lineTo(p[k], p[k + 1]);
  ctx.closePath();
  ctx.save();
  ctx.globalAlpha = 0.16;
  ctx.fillStyle = motif;
  ctx.fill();
  ctx.restore();
  ctx.lineWidth = largeur;
  ctx.strokeStyle = motif;
  ctx.stroke();
}

function dessineBouquet(canvas, im, echelle = 1) {
  const ctx = canvas.getContext('2d');
  ctx.setTransform(echelle, 0, 0, echelle, 0, 0);
  const l = canvas.width / echelle, h = canvas.height / echelle, e = im.e;
  const fond = ctx.createLinearGradient(0, 0, 0, h);
  fond.addColorStop(0, rgb(0.62, 0.80, 0.95));
  fond.addColorStop(1, rgb(0.82, 0.91, 0.98));
  ctx.fillStyle = fond;
  ctx.fillRect(0, 0, l, h);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const largeur = 2 * e;
  im.lacets.forEach((p, k) => {
    const o = 11 * im.plante[k];
    const [sorte, cx, cy, tige, eclosion, rayonFleur, rayonSepales, rayonMotif, cr, cv, cb] = im.plantes.subarray(o, o + 11);
    const motif = ctx.createRadialGradient(cx, cy, 0, cx, cy, rayonMotif);
    motif.addColorStop(0, rgb(...VERT));
    motif.addColorStop(1, rgb(...SOMBRE));
    if (sorte === 0) { traceFerme(ctx, p, motif, largeur); return; }   // une feuille
    // une fleur : vert hors du secteur de la fleur...
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, l, h);
    secteurDeFleur(ctx, cx, cy, tige, rayonFleur, rayonSepales);
    ctx.clip('evenodd');
    traceFerme(ctx, p, motif, largeur);
    ctx.restore();
    // ... et dans le secteur, du vert du bouton au blanc et à la couleur de la fleur qui éclot
    const interieur = melange(eclosion, VERT, BLANC);
    const exterieur = melange(eclosion, VERT, [cr, cv, cb]);
    const fleur = ctx.createRadialGradient(cx, cy, 0, cx, cy, 2.6 * rayonFleur);
    fleur.addColorStop(0, rgb(...interieur));
    fleur.addColorStop(0.21, rgb(...interieur));
    fleur.addColorStop(0.42, rgb(...exterieur));
    fleur.addColorStop(1, rgb(...exterieur));
    ctx.save();
    ctx.beginPath();
    secteurDeFleur(ctx, cx, cy, tige, rayonFleur, rayonSepales);
    ctx.clip();
    traceFerme(ctx, p, fleur, largeur);
    ctx.restore();
  });
}

// Étendue (x et y minimaux et maximaux) des lacets, des trous et du clou d'une image, ou de plusieurs.
function etendue(images) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const parcourt = (p) => {
    for (let k = 0; k < p.length; k += 2) {
      if (p[k] < x0) x0 = p[k];
      if (p[k] > x1) x1 = p[k];
      if (p[k + 1] < y0) y0 = p[k + 1];
      if (p[k + 1] > y1) y1 = p[k + 1];
    }
  };
  for (const im of images) {
    im.lacets.forEach(parcourt);
    parcourt(im.trous);
    // les films d'arcs (diagramme de courbes, rubans) n'ont pas de clou : le leur est un point factice hors du cadre, qui ne doit
    // pas dicter le zoom ; ce sont leurs trous fixes, dessinés, qui comptent
    if (im.fixes && im.fixes.length > 0) parcourt(im.fixes);
    else parcourt(im.clou);
  }
  return { x0, y0, x1, y1 };
}

// La vue qui fait tenir l'étendue dans le canvas (avec une marge) : un recul seulement, jamais un agrandissement. Les
// brins d'un faisceau très chargé sortent parfois du cadre : on dézoome (la même vue pour tout le film).
function vueDe(canvas, images, mode) {
  if (mode === 'escargot' || mode === 'bouquet') return null;   // des images d'une autre forme, qui tiennent dans le cadre
  const e = etendue(images);
  const marge = 14;
  const w = e.x1 - e.x0, h = e.y1 - e.y0;
  if (!(w > 0) || !(h > 0)) return null;
  const hors = e.x0 < marge || e.y0 < marge || e.x1 > canvas.width - marge || e.y1 > canvas.height - marge;
  if (!hors) return null;
  const s = Math.min(1, (canvas.width - 2 * marge) / w, (canvas.height - 2 * marge) / h);
  return { s, tx: canvas.width / 2 - s * (e.x0 + e.x1) / 2, ty: canvas.height / 2 - s * (e.y0 + e.y1) / 2 };
}

// Les films qui ont des lignes de construction facultatives (image.construction : des segments à plat, x0, y0, x1, y1, …,
// et, quand ils s'estompent, image.opacites : un nombre par segment) : la case « lignes de construction » du lecteur les
// trace en gris sous les lacets. Elles ne comptent pas dans `etendue` (le zoom ne dépend que des lacets, des trous et du clou).
// Pour chaque film, une phrase dit ce que sont ces lignes : elle s'ouvre dans la bulle du « ? » à côté de la case « construction »
// (au survol, au clavier ou à l'appui).
const MODES_AVEC_CONSTRUCTION = new Map([
  ['triangulation', 'Le maillage (une triangulation) sur lequel les brins sont posés : il se déplace avec les trous, et les brins le suivent et se tendent ; le dessin est ensuite détendu (les brins s\'arrondissent).'],
  ['diagramme', 'Le maillage (une triangulation) sur lequel les arcs sont posés et tendus : il se déplace avec les trous ; le dessin est ensuite détendu (les arcs s\'arrondissent).'],
  ['rubans', 'Le maillage (une triangulation) sur lequel les arcs, au centre des rubans, sont posés et tendus : il se déplace avec les trous.'],
  ['conforme', 'L\'axe et la ligne brisée L–A–B–R sur lesquels le dessin est construit. Pendant le demi-tour, la ligne de départ et celle d\'arrivée s\'estompent l\'une dans l\'autre, et le dessin passe alors par une triangulation mobile, puis se détend : les brins s\'arrondissent et s\'espacent.'],
]);
const GRIS_CONSTRUCTION = '#999';
const TRAIT_CONSTRUCTION = 2.2;   // pour un canvas de 800 de large, comme les lacets

function traceSegments(ctx, s, couleur, largeur, opacites = null) {
  ctx.strokeStyle = couleur;
  ctx.lineWidth = largeur;
  if (!opacites) {
    ctx.beginPath();
    for (let k = 0; k + 3 < s.length; k += 4) {
      ctx.moveTo(s[k], s[k + 1]);
      ctx.lineTo(s[k + 2], s[k + 3]);
    }
    ctx.stroke();
    return;
  }
  const alpha = ctx.globalAlpha;
  for (let j = 0; 4 * j + 3 < s.length; j++) {   // un segment à la fois : chacun a sa propre opacité
    ctx.globalAlpha = alpha * opacites[j];
    ctx.beginPath();
    ctx.moveTo(s[4 * j], s[4 * j + 1]);
    ctx.lineTo(s[4 * j + 2], s[4 * j + 3]);
    ctx.stroke();
  }
  ctx.globalAlpha = alpha;
}

// La taille de référence des vues d'un mot : les coordonnées des images (et des listes de tracé) sont celles d'un cadre de 800 × 800.
const TAILLE_REFERENCE = 800;

// La liste de ce qu'on trace pour une image (lacets, trous, clou, lignes de construction), avec les couleurs et le fond
// COURANTS : { fond, vue, elements }. Chaque élément est { type: 'ligne' | 'segments' | 'disques', pts, couleur, largeur | rayon,
// opacites? }, en coordonnées de l'image ; `vue` (zoom commun au film) est appliquée au dessin, pas aux points. C'est la
// base commune du canvas, du PNG, du SVG et de la vidéo : un seul endroit sait comment une vue se dessine.
// (L'escargot et les iris ont leur propre dessin : voir dessineEscargot et dessineBouquet.)
function listeDeTrace(image, mode, vue = null, construction = false) {
  const elements = [];
  if (construction && image.construction) {
    elements.push({ type: 'segments', pts: image.construction, couleur: GRIS_CONSTRUCTION, largeur: TRAIT_CONSTRUCTION, opacites: image.opacites || null });
  }
  image.lacets.forEach((p, i) => {
    const couleur = PALETTE[i % PALETTE.length];
    if (mode === 'conforme' || mode === 'triangulation') {
      // la triangulation : trait plus fin quand les brins sont serrés
      elements.push({ type: 'ligne', pts: p, couleur, largeur: mode === 'triangulation' ? image.brin : 3.5 });
    } else if (mode === 'diagramme') {
      // liseré de la couleur du fond : les brins voisins restent lisibles
      elements.push({ type: 'ligne', pts: p, couleur: FOND, largeur: 0.85 * image.ecart });
      elements.push({ type: 'ligne', pts: p, couleur, largeur: 2.2 });
    } else {
      elements.push({ type: 'ligne', pts: p, couleur, largeur: 2.5 });
    }
  });
  if (mode === 'conforme' || mode === 'triangulation') {
    const r = mode === 'triangulation' ? image.brin : 4;
    elements.push({ type: 'disques', pts: image.trous, rayon: r, couleur: '#000' });
    elements.push({ type: 'disques', pts: image.clou, rayon: r, couleur: '#000' });
  } else {
    elements.push({ type: 'disques', pts: image.fixes, rayon: 4, couleur: '#8c8c8c' });
    elements.push({ type: 'disques', pts: image.trous, rayon: 4, couleur: '#000' });
  }
  return { fond: FOND, vue, elements };
}

// Dessine une liste de tracé sur un canvas. `echelle` : 1 pour un canvas de 800 × 800 ; pour une image plus grande (export), on passe
// canvas.width / 800 : les épaisseurs et les rayons suivent. `fond` : fond plein, sauf `liste.fond` nul (fond transparent).
function dessineListe(canvas, liste, echelle = canvas.width / TAILLE_REFERENCE) {
  const ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (liste.fond) {
    ctx.fillStyle = liste.fond;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  const v = liste.vue;
  if (v) ctx.setTransform(echelle * v.s, 0, 0, echelle * v.s, echelle * v.tx, echelle * v.ty);
  else ctx.setTransform(echelle, 0, 0, echelle, 0, 0);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const e of liste.elements) {
    if (e.type === 'segments') traceSegments(ctx, e.pts, e.couleur, e.largeur, e.opacites);
    else if (e.type === 'ligne') { ctx.strokeStyle = e.couleur; ctx.lineWidth = e.largeur; trace(ctx, e.pts); }
    else if (e.type === 'disques') disques(ctx, e.pts, e.rayon, e.couleur);
  }
}

function dessineImage(canvas, image, mode, vue = null, construction = false) {
  if (mode === 'escargot') { dessineEscargot(canvas, image); return; }
  if (mode === 'bouquet') { dessineBouquet(canvas, image); return; }
  dessineListe(canvas, listeDeTrace(image, mode, vue, construction), 1);
}

// ---------------------------------------------------------------- un lecteur : image fixe, puis film

const IMAGES_PAR_SECONDE = 25;
// 0,5 s sur la première image, puis le film se joue une fois et s'arrête sur la dernière (this.pauseDebut, en images)

class Lecteur {
  constructor(parent, mode, titre, largeur = 800, hauteur = 800, ips = IMAGES_PAR_SECONDE, schema = null) {
    this.mode = mode;
    this.ips = ips;                                  // images du film par seconde
    this.pauseDebut = Math.round(0.5 * ips);         // 0,5 s sur la première image
    const panneau = document.createElement('div');
    panneau.className = 'panneau';
    panneau.innerHTML = `<h3>${titre}</h3><canvas width="${largeur}" height="${hauteur}" style="aspect-ratio: ${largeur} / ${hauteur}"></canvas><div class="etat"></div>`;
    parent.appendChild(panneau);
    if (schema) panneau.querySelector('h3').appendChild(aideSchema(schema));
    this.canvas = panneau.querySelector('canvas');
    this.etat = panneau.querySelector('.etat');
    this.images = [];
    this.lettres = [];                               // le mot de la tresse (entiers) : une lettre par chapitre ; vide pour l'escargot et les iris
    this.chapitres = null;                           // les indices d'image où commence chaque lettre, puis la dernière image (L + 1 nombres), reçus avec l'image 0
    this.fixe = null;
    this.vue = null;
    this.lecture = false;
    this.t = 0;
    this.derniere = 0;
    this.construction = new URLSearchParams(location.search).has('construction');   // la case ; ?construction : cochée au départ (captures)
    this.efface();
  }

  efface() {
    const ctx = this.canvas.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = fondDe(this.mode);
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  // Les couleurs ou le fond ont changé : on redessine ce qui est à l'écran (aucun calcul : les films sont des polylignes).
  recolore() {
    if (this.mode === 'escargot' || this.mode === 'bouquet') return;
    if (this.images.length >= 2 && this.curseur) this.montre();
    else if (this.fixe) dessineImage(this.canvas, this.fixe, this.mode, this.vue, this.construction);
    else this.efface();
  }

  // Un nouveau mot : on repart de zéro.
  recommence() {
    this.arrete();
    this.images = [];
    this.chapitres = null;
    this.fixe = null;
    this.vue = null;
    this.t = 0;
    this.efface();
    this.etat.innerHTML = '<progress max="1" value="0"></progress><span>calcul…</span>';
  }

  // Une vue qui attend son tour de calcul (les films se calculent l'un après l'autre) : le cadre garde son image fixe, si elle est déjà là.
  enAttente() {
    this.etat.innerHTML = '<span>en attente (les films se calculent l\'un après l\'autre)</span>';
  }

  // Le calcul de cette vue commence : la barre de progression, sans effacer l'image fixe.
  debute() {
    this.etat.innerHTML = '<progress max="1" value="0"></progress><span>calcul…</span>';
  }

  // Vue non calculée (mot hors des limites de cette vue) : un message dans le cadre, rien n'est lancé.
  indisponible(lignes) {
    this.arrete();
    this.images = [];
    this.fixe = null;
    this.vue = null;
    this.efface();
    const ctx = this.canvas.getContext('2d');
    ctx.fillStyle = '#626b7d';
    ctx.textAlign = 'center';
    ctx.font = '600 34px system-ui, sans-serif';
    const texte = lignes.join(' ');
    const mots = texte.split(' ');
    const rangees = [];
    let courante = '';
    for (const m of mots) {
      const essai = courante ? courante + ' ' + m : m;
      if (ctx.measureText(essai).width > this.canvas.width - 120 && courante) { rangees.push(courante); courante = m; } else courante = essai;
    }
    rangees.push(courante);
    const y0 = this.canvas.height / 2 - (rangees.length - 1) * 24;
    rangees.forEach((r, i) => ctx.fillText(r, this.canvas.width / 2, y0 + i * 48));
    this.etat.innerHTML = '<span class="attention">vue non calculée pour ce mot</span>';
  }

  vide(texte) {
    this.arrete();
    this.images = [];
    this.fixe = null;
    this.efface();
    this.etat.innerHTML = `<span>${texte}</span>`;
  }

  recoitFixe(image) {
    this.fixe = image;
    this.vue = vueDe(this.canvas, [image], this.mode);
    dessineImage(this.canvas, image, this.mode, this.vue, this.construction);
  }

  recoitImage(image, k, total) {
    this.images.push(image);
    if (k === 0 && image.chapitres) this.chapitres = Array.from(image.chapitres, Math.round);   // le contrat : OCaml donne le début de chaque lettre
    const barre = this.etat.querySelector('progress');
    if (barre) {
      barre.value = (k + 1) / total;
      this.etat.querySelector('span').textContent = `film : ${Math.round(100 * (k + 1) / total)} %`;
    }
  }

  fini(message, erreur) {
    if (erreur || this.images.length < 2) {
      this.etat.innerHTML = `<span class="ko">${message || 'film indisponible'}</span>`;
      return;
    }
    this.vue = vueDe(this.canvas, this.images, this.mode);   // une vue pour tout le film : pas de saut de zoom d'une image à l'autre
    this.prepareLecteur(message);
    if (new URLSearchParams(location.search).has('fin')) {   // ?fin : pas de lecture, sur la dernière image (pour les captures)
      this.t = this.duree() - 1;
      this.arrete();
      this.montre();
      return;
    }
    this.joue();
  }

  prepareLecteur(message) {
    const duree = this.duree();
    this.etat.innerHTML = `<button type="button" class="avant" title="image précédente (←)" aria-label="image précédente">|◀</button>` +
      `<button type="button" class="lecture" title="lecture / pause">⏸</button>` +
      `<button type="button" class="apres" title="image suivante (→)" aria-label="image suivante">▶|</button>` +
      `<span class="glissiere"><input type="range" min="0" max="${duree - 1}" step="1" value="0" aria-label="position dans le film"></span>` +
      (MODES_AVEC_CONSTRUCTION.has(this.mode)
        ? `<label><input type="checkbox" class="construction"${this.construction ? ' checked' : ''}> construction</label><span class="emplacement-aide"></span>`
        : '') +
      `<span class="numero-image" aria-live="polite"></span>` +
      (message ? `<span class="ko" title="${message}">⚠</span>` : '') +
      (this.aDesChapitres() ? `<div class="chapitres" role="group" aria-label="Chapitres : une lettre du mot par bouton"></div>` : '');
    this.bouton = this.etat.querySelector('button.lecture');
    this.numero = this.etat.querySelector('.numero-image');
    // ◀ et ▶ : une image du film, en pause, sans boucler ; l'appui prolongé répète
    const pasAPas = (bouton, sens) => {
      let delai = null, repete = null;
      const stoppe = () => { clearTimeout(delai); clearInterval(repete); };
      const un = () => { this.arrete(); this.vaA(this.indice() + sens); };
      bouton.onpointerdown = (e) => { if (e.button) return; un(); delai = setTimeout(() => { repete = setInterval(un, 40); }, 400); };
      for (const ev of ['pointerup', 'pointerleave', 'pointercancel']) bouton.addEventListener(ev, stoppe);
      bouton.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); un(); } };
    };
    pasAPas(this.etat.querySelector('button.avant'), -1);
    pasAPas(this.etat.querySelector('button.apres'), +1);
    this.canvas.tabIndex = 0;   // ← / → image par image quand le cadre a le focus
    this.canvas.onkeydown = (e) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        this.arrete();
        const sens = e.key === 'ArrowRight' ? 1 : -1;
        if (e.shiftKey) this.vaAuChapitre(sens); else this.vaA(this.indice() + sens);
      }
    };
    this.curseur = this.etat.querySelector('input[type=range]');
    const case_ = this.etat.querySelector('input.construction');
    if (case_) case_.onchange = () => { this.construction = case_.checked; this.montre(); };
    const place = this.etat.querySelector('.emplacement-aide');
    if (place) place.replaceWith(aideBulle('construction-' + this.mode, 'Lignes de construction : explication',
      `<span class="texte-bulle"><b>Lignes de construction.</b> ${MODES_AVEC_CONSTRUCTION.get(this.mode)}</span>`));
    this.bouton.onclick = () => (this.lecture ? this.arrete() : this.joue());
    this.bouton.title = 'lecture / pause (relance le film s\'il est fini)';
    this.curseur.oninput = () => { this.arrete(); this.t = Number(this.curseur.value); this.montre(); };
    this.numero.after(menuExport(this));   // le menu « ⤓ » des exports (exports.js)
    this.prepareChapitres();
  }

  // Les chapitres sont utilisables si le mot a des lettres et que le film en a donné les débuts (L + 1 nombres, dans le film).
  aDesChapitres() {
    const c = this.chapitres, L = this.lettres.length;
    return L > 0 && !!c && c.length === L + 1 && c[L] <= this.images.length - 1;
  }

  // La rangée de boutons (un par lettre) et les repères sur la glissière.
  prepareChapitres() {
    this.rangee = this.etat.querySelector('.chapitres');
    if (!this.rangee) return;
    const c = this.chapitres, L = this.lettres.length;
    const max = this.duree() - 1;
    this.boutonsLettres = this.lettres.map((lettre, j) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = nomLettre(lettre);
      b.title = `lettre ${j + 1} sur ${L} : ${nomLettre(lettre)} (image ${c[j] + 1})`;
      b.setAttribute('aria-label', `lettre ${j + 1} : ${nomLettre(lettre)}, à l'image ${c[j] + 1}`);
      b.onclick = () => { this.arrete(); this.vaA(c[j]); };
      this.rangee.appendChild(b);
      return b;
    });
    const glissiere = this.etat.querySelector('.glissiere');
    for (let j = 0; j <= L; j++) {   // un repère à chaque début de lettre, et un à la fin
      const p = 100 * (c[j] === 0 ? 0 : this.pauseDebut + c[j]) / max;
      const repere = document.createElement('span');
      repere.className = 'repere';
      repere.style.left = `calc(${p}% + ${8 - 0.16 * p}px)`;   // la poignée (16 px) ne va pas jusqu'aux bouts de la glissière
      glissiere.appendChild(repere);
    }
  }

  // Le chapitre (la lettre) de l'image k : le dernier dont le début est atteint ; sur la dernière image, la dernière lettre.
  chapitreDe(k) {
    const c = this.chapitres, L = this.lettres.length;
    let j = 0;
    while (j + 1 < L && c[j + 1] <= k) j++;
    return j;
  }

  // Maj + ← / → : de lettre en lettre. ← revient d'abord au début de la lettre en cours, puis à la lettre d'avant.
  vaAuChapitre(sens) {
    if (!this.aDesChapitres()) return;
    const c = this.chapitres, k = this.indice(), j = this.chapitreDe(k), L = this.lettres.length;
    let cible;
    if (sens > 0) cible = k >= c[L] ? c[L] : c[j + 1];
    else cible = k > c[j] ? c[j] : c[Math.max(0, j - 1)];
    this.vaA(cible);
  }

  // le nombre de positions de t, de 0 à duree() - 1 : la pause du début sur l'image 0, puis une position par image ; la dernière position est la dernière image
  duree() { return this.pauseDebut + this.images.length; }

  // Le numéro (à partir de 0) de l'image du film montrée à l'instant t : t compte aussi la pause du début.
  indice() {
    return this.t < this.pauseDebut ? 0 : Math.min(this.images.length - 1, Math.floor(this.t - this.pauseDebut));
  }

  // Va à l'image k (bornée : pas de bouclage) ; l'image 0 est aussi la pause du début.
  vaA(k) {
    k = Math.max(0, Math.min(this.images.length - 1, k));
    this.t = k === 0 ? 0 : this.pauseDebut + k;
    this.montre();
  }

  montre() {
    const k = this.indice();
    dessineImage(this.canvas, this.images[k], this.mode, this.vue, this.construction);
    if (this.curseur) this.curseur.value = String(Math.floor(this.t));
    if (this.numero) this.numero.textContent = `image ${k + 1} / ${this.images.length}`;
    if (this.boutonsLettres) {
      const j = this.chapitreDe(k);
      this.boutonsLettres.forEach((b, i) => {
        b.classList.toggle('courante', i === j);
        if (i === j) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
      });
    }
  }

  joue() {
    if (this.images.length < 2) return;
    if (this.t >= this.duree() - 1) this.t = 0;   // relancer un film fini : on repart du début
    this.lecture = true;
    if (this.bouton) this.bouton.textContent = '⏸';
    this.derniere = performance.now();
    const pas = (maintenant) => {
      if (!this.lecture) return;
      this.t += (maintenant - this.derniere) * this.ips / 1000;
      this.derniere = maintenant;
      if (this.t >= this.duree() - 1) {   // fin : on reste sur la dernière image
        this.t = this.duree() - 1;
        this.montre();
        this.arrete();
        return;
      }
      this.montre();
      requestAnimationFrame(pas);
    };
    requestAnimationFrame(pas);
  }

  arrete() {
    this.lecture = false;
    if (this.bouton) this.bouton.textContent = '▶';
  }
}

// ---------------------------------------------------------------- les infobulles : un petit schéma par méthode de dessin

const SCHEMAS = {
  tresse: ['Diagramme de tresse', 'Un croisement σᵢ et son inverse σᵢ⁻¹, puis l\'exemple σ₁σ₂⁻¹ lu de haut en bas.'],
  fn: ['Action sur le groupe libre', 'Les lacets x₁ et x₂ avant et après σ₁ : x₁ ↦ x₁x₂x₁⁻¹ et x₂ ↦ x₁.'],
  diagramme: ['Diagramme de courbes', 'Un point fixe à gauche ; les arcs sont les segments de l\'axe, que le demi-tour de deux trous emporte. La case « lignes de construction » trace le maillage en gris.'],
  lacets: ['Lacets conformes', 'Le dessin est l\'image de demi-cercles du demi-plan par la transformation conforme : des arcs à angle droit autour des sommets de la ligne brisée L–A–B–R. Pendant le demi-tour, il passe par une triangulation mobile et se détend : les brins s\'arrondissent et s\'espacent. La case « lignes de construction » trace l\'axe et cette ligne brisée, qui s\'estompent pendant le demi-tour.'],
  triangulation: ['Triangulation mobile', 'Un maillage et des points sur ses arêtes ; quand les trous tournent, les brins suivent et se tendent. La case « lignes de construction » trace le maillage en gris.'],
  rubans: ['Rubans', 'Un ruban par trou voyageur, du trou fixe (la queue) au trou voyageur ; après le demi-tour, les rubans s\'enroulent.'],
};

// Un bouton « ? » qui montre le schéma au survol et au clavier (Tab). Rend l'élément à ajouter près d'un titre.
// Un « ? » qui ouvre une bulle : au survol, au clavier ou à l'appui. `contenu` est le HTML de la bulle (un schéma ou un texte).
function aideBulle(id, libelle, contenu) {
  const zone = document.createElement('span');
  zone.className = 'aide-schema';
  zone.dataset.schema = id;
  zone.innerHTML = `<button type="button" class="bouton-aide" aria-label="${libelle}" aria-describedby="bulle-${id}">?</button>` +
    `<span class="bulle" role="tooltip" id="bulle-${id}"><span class="cadre">${contenu}</span></span>`;
  const bulle = zone.querySelector('.bulle');
  const ajuste = () => {   // reste dans la fenêtre
    bulle.style.left = '0px';
    const r = bulle.getBoundingClientRect();
    let dx = 0;
    if (r.right > window.innerWidth - 8) dx = window.innerWidth - 8 - r.right;
    if (r.left + dx < 8) dx = 8 - r.left;
    bulle.style.left = dx + 'px';
  };
  const bouton = zone.querySelector('.bouton-aide');
  bouton.setAttribute('aria-expanded', 'false');
  zone.addEventListener('mouseenter', ajuste);
  zone.addEventListener('focusin', ajuste);
  // un appui sur « ? » ouvre la bulle (et ferme les autres) ; un appui ailleurs, Échap ou un défilement la ferment (il n'y a pas de survol au toucher)
  bouton.addEventListener('click', (e) => {
    e.stopPropagation();
    const ouvre = !zone.classList.contains('ouverte');
    fermeLesBulles();
    if (ouvre) { zone.classList.add('ouverte'); bouton.setAttribute('aria-expanded', 'true'); ajuste(); }
  });
  zone.addEventListener('keydown', (e) => { if (e.key === 'Escape') { fermeLesBulles(); e.target.blur(); } });
  if (new URLSearchParams(location.search).get('aide') === id) { zone.classList.add('ouverte'); setTimeout(ajuste, 0); }   // ?aide=… : bulle ouverte (captures)
  return zone;
}

// La bulle d'un titre : le schéma de la méthode de dessin.
function aideSchema(id) {
  const [titre, alt] = SCHEMAS[id];
  return aideBulle(id, `Schéma explicatif : ${titre}`, `<img src="schemas/${id}.svg" alt="${alt}" width="440" height="250">`);
}

function fermeLesBulles() {
  document.querySelectorAll('.aide-schema.ouverte').forEach((z) => {
    z.classList.remove('ouverte');
    const b = z.querySelector('.bouton-aide');
    if (b) b.setAttribute('aria-expanded', 'false');
  });
}
document.addEventListener('click', fermeLesBulles);
document.addEventListener('touchstart', (e) => { if (!e.target.closest('.aide-schema')) fermeLesBulles(); }, { passive: true });
window.addEventListener('scroll', fermeLesBulles, { passive: true });

function ajouteAides() {
  document.querySelectorAll('[data-schema]').forEach((t) => t.appendChild(aideSchema(t.dataset.schema)));
}

// ---------------------------------------------------------------- la page

// Les quatre vues principales, dans l'ordre de l'affichage (deux par ligne) et du calcul : les films se calculent l'un après l'autre
// (chacun se répartit déjà sur tous les cœurs : voir lanceCalculs).
const MODES = [
  { id: 'conforme', titre: 'Action sur le groupe libre et ses lacets', schema: 'lacets', limite: true },
  { id: 'diagramme', titre: 'Diagramme de courbes', schema: 'diagramme' },
  { id: 'rubans', titre: 'Action sur le groupe libre et ses rubans', schema: 'rubans' },
  { id: 'triangulation', titre: 'Action sur le groupe libre et sa triangulation', schema: 'triangulation', limite: true },
];

let lecteurs = [];
let travailleurs = [];
let lecteursLibres = [];   // les films sans mot de tresse (l'escargot) : lancés une fois, indépendants du mot
let travailleursLibres = [];
let ardoisePrincipale = null;   // la bibliothèque dans le fil principal : pour l'action sur F_n (instantanée)

function arreteTravailleurs() {
  travailleurs.forEach((w) => w.terminate());
  travailleurs = [];
}

// Le mode de calcul d'une vue, quand il diffère de son nom : les lacets sont le film conforme détendu pendant le raccord, la
// triangulation et le diagramme de courbes sont détendus sur toutes leurs images (Detente ; travail.js répartit la détente sur
// plusieurs workers).
const MODE_DE_CALCUL = { conforme: 'conforme_detendu', triangulation: 'triangulation_detendu', diagramme: 'diagramme_detendu' };

// Un Web Worker pour un mode et un lecteur ; rend le worker (ou null si le navigateur refuse, par exemple en file://).
// `suite` est appelée une fois, quand le film est fini (ou que le calcul a échoué) : c'est elle qui lance la vue suivante.
function demarreTravailleur(mode, mot, lecteur, suite) {
  let w;
  let finie = false;
  const termine = () => { if (!finie) { finie = true; if (suite) suite(); } };
  try {
    w = new Worker('travail.js');
  } catch (e) {
    lecteur.vide('Ouvre la page par un serveur (python -m http.server dans web/), pas en file://.');
    return null;
  }
  w.onerror = () => { lecteur.vide('le calcul a échoué (ardoise_lib.js introuvable ? voir construit.sh)'); termine(); };
  w.onmessage = (e) => {
    const d = e.data;
    if (d.type === 'statique') lecteur.recoitFixe(d.image);
    else if (d.type === 'image') lecteur.recoitImage(d.image, d.k, d.total);
    else if (d.type === 'fini') { lecteur.fini(d.message, d.erreur); w.terminate(); termine(); }   // le worker a fini : il libère ses auxiliaires
  };
  w.postMessage({ mode: MODE_DE_CALCUL[mode] || mode, mot });
  return w;
}

let generationCalculs = 0;   // un nouveau mot abandonne la file de calcul en cours

// L'image fixe d'une vue qui attend : un petit worker ne la calcule que pour l'afficher tout de suite (le film arrive à son tour).
function demarreFixe(mode, mot, lecteur) {
  let w;
  try { w = new Worker('travail.js'); } catch (e) { return null; }
  w.onmessage = (e) => {
    if (e.data.type === 'statique') lecteur.recoitFixe(e.data.image);
    else if (e.data.type === 'fixe-fini') w.terminate();
  };
  w.postMessage({ type: 'fixe', mode: MODE_DE_CALCUL[mode] || mode, mot });
  return w;
}

// Les vues se calculent l'une après l'autre, dans l'ordre de MODES : chaque film occupe déjà tous les cœurs (travail.js répartit
// ses lettres et sa détente sur des workers auxiliaires), et quatre films à la fois se gêneraient. Les vues qui attendent le disent.
function lanceCalculs(mot) {
  arreteTravailleurs();
  const generation = ++generationCalculs;
  lecteurs.forEach((l) => { l.recommence(); l.lettres = mot; });
  const brins = nbBrins(mot), lettres = mot.length;
  const trop = [];
  if (brins > MAX_BRINS_CONFORME) trop.push(`${brins} brins (limite : ${MAX_BRINS_CONFORME})`);
  if (lettres > MAX_LETTRES_CONFORME) trop.push(`${lettres} lettres (limite : ${MAX_LETTRES_CONFORME})`);
  const file = [];
  MODES.forEach((m, j) => {
    if (m.limite && trop.length) {   // les vues « lacets » et « triangulation » sont limitées : on le dit au lieu de lancer un calcul trop long
      lecteurs[j].indisponible([`Ce mot a ${trop.join(' et ')} : trop pour cette vue.`, 'Les autres vues sont calculées.']);
      return;
    }
    file.push(j);
  });
  file.slice(1).forEach((j) => {
    lecteurs[j].enAttente();
    const w = demarreFixe(MODES[j].id, mot, lecteurs[j]);
    if (w) travailleurs.push(w);
  });
  const suivante = () => {
    if (generation !== generationCalculs) return;   // le mot a changé entre-temps
    const j = file.shift();
    if (j === undefined) return;
    lecteurs[j].debute();
    const w = demarreTravailleur(MODES[j].id, mot, lecteurs[j], suivante);
    if (w) travailleurs.push(w); else suivante();
  };
  suivante();
}

const LIBRES = [
  { id: 'escargot', titre: 'L\'escargot : une spirale de rubans', largeur: 960, hauteur: 640, ips: 25 },
  { id: 'bouquet', titre: 'La floraison des Iris', largeur: 810, hauteur: 1080, ips: 12.5 },
];

// Les films sans tresse ne dépendent pas du mot : on les lance une seule fois, au chargement.
function lanceLibres() {
  const zone = document.getElementById('panneaux-libres');
  lecteursLibres = LIBRES.map((m) => new Lecteur(zone, m.id, m.titre, m.largeur, m.hauteur, m.ips));
  LIBRES.forEach((m, j) => {
    lecteursLibres[j].recommence();
    const w = demarreTravailleur(m.id, [], lecteursLibres[j]);
    if (w) travailleursLibres.push(w);
  });
}

let motCourant = null;

function mise_a_jour(texte, { immediat } = {}) {
  const r = lisMot(texte);
  const erreur = document.getElementById('erreur');
  if (r.erreur) {
    erreur.textContent = r.erreur + (motCourant !== null && motCourant !== '' ? ' (les résultats ci-dessous sont ceux du dernier mot valide)' : '');
    erreur.hidden = false;
    document.body.classList.toggle('mot-invalide', motCourant !== null);
    etatLimites(null);
    return;
  }
  erreur.hidden = true;
  document.body.classList.remove('mot-invalide');
  const mot = r.mot;
  const cle = mot.join(' ');
  const memorisee = entreeCourante();
  if (memorisee && motEnTexte(memorisee.mot) !== cle) choisis(null);   // le mot n'est plus celui de la tresse mémorisée sélectionnée
  const identique = cle === motCourant;
  motCourant = cle;
  metsAJourSelection();
  if (identique) return;
  motEntiers = mot;
  afficheCouleurs();
  try { history.replaceState(null, '', mot.length ? '#' + encodeURIComponent(cle) : location.pathname); } catch (e) { /* file:// */ }
  afficheMot(mot);
  etatLimites(mot);
  const classique = document.getElementById('canvas-classique');
  if (mot.length === 0) {
    classique.width = classique.height = 0;
    document.getElementById('fn-images').textContent = '';
    document.getElementById('titre-fn').innerHTML = '';
    arreteTravailleurs();
    lecteurs.forEach((l) => l.vide('rien à dessiner'));
    return;
  }
  dessineTresse(classique, mot);
  afficheFn(mot, ardoisePrincipale);
  lanceCalculs(mot);
}

// La bibliothèque dans le fil principal : ardoise_lib.js est aussi chargé en <script>, pour l'action sur F_n
// (quelques microsecondes) ; le gros du calcul reste dans les workers.
function chargeBibliotheque() {
  return new Promise((ok, ko) => {
    const s = document.createElement('script');
    s.src = 'ardoise_lib.js';
    s.onload = () => ok(window.ardoise);
    s.onerror = () => ko(new Error('ardoise_lib.js introuvable : lancer web/construit.sh'));
    document.head.appendChild(s);
  });
}

function afficheLimites() {
  const l = document.getElementById('limites');
  if (!l) return;
  l.innerHTML = `Limites de la page : <b>${MAX_BRINS} brins</b> (σ<sub>1</sub> … σ<sub>${MAX_BRINS - 1}</sub>) et <b>${MAX_LETTRES} lettres</b>. ` +
    `Au-delà de <b>${MAX_BRINS_CONFORME} brins</b> ou de <b>${MAX_LETTRES_CONFORME} lettres</b>, les vues « lacets » et « triangulation » ne sont pas calculées ` +
    `(les autres vues le sont).`;
}

// L'avertissement, seulement quand une vue est limitée (le nombre de lettres et de brins est dans la ligne de afficheMot).
function etatLimites(mot) {
  const e = document.getElementById('etat-limites');
  if (!e) return;
  e.textContent = '';
  if (!mot || mot.length === 0) return;
  // les chiffres du mot sont déjà dans la ligne « n lettres, p brins » (afficheMot) : ici, seulement l'avertissement
  const brins = nbBrins(mot), lettres = mot.length;
  const trop = [];
  if (brins > MAX_BRINS_CONFORME) trop.push(`${brins} brins (limite : ${MAX_BRINS_CONFORME})`);
  if (lettres > MAX_LETTRES_CONFORME) trop.push(`${lettres} lettres (limite : ${MAX_LETTRES_CONFORME})`);
  if (trop.length) e.innerHTML = `<span class="attention">Ce mot a ${trop.join(' et ')} : les vues « lacets » et « triangulation » ne sont pas calculées.</span>`;
}

// ---------------------------------------------------------------- les tresses mémorisées

// Les tresses que la personne a saisies, gardées dans le navigateur (localStorage), à la suite des tresses d'exemple : chacune a son
// texte libre, ses couleurs (une par brin) et son fond. Voir etude_tresses_personnalisees.md.
const CLE_MEMOIRE = 'ardoise.tresses';
const MAX_TRESSES = 30, MAX_TEXTE = 100;
const memoire = { courant: null, tresses: [], disponible: true };   // courant : l'id de l'entrée sélectionnée, ou null
let motEntiers = [];          // le mot affiché

const COULEUR_VALIDE = /^#[0-9a-fA-F]{6}$/;
const couleursParDefaut = (n) => PALETTE_DEFAUT.slice(0, n);
const motEnTexte = (mot) => mot.join(' ');
const SOUS = '₀₁₂₃₄₅₆₇₈₉';
const nomLettre = (k) => 'σ' + String(Math.abs(k)).replace(/\d/g, (c) => SOUS[Number(c)]) + (k < 0 ? '⁻¹' : '');
const nomMot = (mot) => mot.map(nomLettre).join('');
// Un espace sans chasse avant chaque σ : le nom d'une carte se coupe entre deux lettres, jamais au milieu d'une (σ₂⁻¹).
const coupable = (nom) => nom.replace(/(?!^)σ/g, '\u200Bσ');

// Une entrée lue (du navigateur ou d'un fichier) : { id, mot, texte, couleurs, fond } nettoyée, ou { erreur } avec la raison.
function validerEntree(e) {
  if (!e || typeof e !== 'object') return { erreur: 'ce n\'est pas une tresse' };
  const mot = e.mot;
  if (!Array.isArray(mot) || mot.length === 0 || mot.length > MAX_LETTRES) return { erreur: `le mot doit avoir de 1 à ${MAX_LETTRES} lettres` };
  if (!mot.every((k) => Number.isInteger(k) && k !== 0 && Math.abs(k) <= MAX_BRINS - 1)) return { erreur: `le mot ne contient pas que des entiers non nuls de valeur absolue au plus ${MAX_BRINS - 1}` };
  const n = nbBrins(mot);
  if (!Array.isArray(e.couleurs) || e.couleurs.length !== n || !e.couleurs.every((c) => typeof c === 'string' && COULEUR_VALIDE.test(c)))
    return { erreur: `il faut ${n} couleurs (#rrggbb), une par brin` };
  if (typeof e.fond !== 'string' || !COULEUR_VALIDE.test(e.fond)) return { erreur: 'le fond doit être une couleur (#rrggbb)' };
  const texte = e.texte === undefined || e.texte === null ? '' : e.texte;
  if (typeof texte !== 'string') return { erreur: 'le texte doit être une chaîne' };
  return { id: typeof e.id === 'string' ? e.id : null, mot: mot.slice(), texte: texte.slice(0, MAX_TEXTE), couleurs: e.couleurs.map((c) => c.toLowerCase()), fond: e.fond.toLowerCase() };
}

function nouvelId() {
  let id;
  do { id = 't' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5); } while (memoire.tresses.some((e) => e.id === id));
  return id;
}

function chargeMemoire() {
  try {
    const brut = localStorage.getItem(CLE_MEMOIRE);
    if (!brut) return;
    const j = JSON.parse(brut);
    if (!j || j.version !== 1 || !Array.isArray(j.tresses)) return;
    for (const e of j.tresses) {
      const v = validerEntree(e);
      if (v.erreur || !v.id || memoire.tresses.length >= MAX_TRESSES || memoire.tresses.some((x) => x.id === v.id)) continue;
      memoire.tresses.push(v);
    }
    memoire.courant = typeof j.courant === 'string' && memoire.tresses.some((e) => e.id === j.courant) ? j.courant : null;
  } catch (e) { memoire.disponible = false; }
}

function ecrisMemoire() {
  try {
    localStorage.setItem(CLE_MEMOIRE, JSON.stringify({ version: 1, courant: memoire.courant, tresses: memoire.tresses }));
    return true;
  } catch (e) {
    if (memoire.disponible) {
      memoire.disponible = false;
      annonce('La mémoire du navigateur n\'est pas disponible : tes tresses ne seront pas gardées quand tu fermeras la page.');
    }
    return false;
  }
}

let minuterieAnnonce = null;
function annonce(texte) {
  const zone = document.getElementById('memoire-info');
  if (!zone) return;
  zone.textContent = texte;
  clearTimeout(minuterieAnnonce);
  if (texte) minuterieAnnonce = setTimeout(() => { zone.textContent = ''; }, 9000);
}

const entreeCourante = () => memoire.tresses.find((e) => e.id === memoire.courant) || null;

// Les couleurs courantes deviennent celles de l'entrée (null : les couleurs par défaut) ; les variables CSS --c0 … --c7 portent les
// couleurs du texte de l'action sur F_n (posées en ligne seulement quand elles diffèrent du défaut : le thème sombre garde les siennes).
function appliqueCouleurs(entree) {
  PALETTE = PALETTE_DEFAUT.map((c, i) => (entree && entree.couleurs[i] ? entree.couleurs[i] : c));
  FOND = entree ? entree.fond : FOND_DEFAUT;
  recolore();
}

function appliqueCss() {
  const racine = document.documentElement.style;
  PALETTE.forEach((c, i) => {
    if (c.toLowerCase() !== PALETTE_DEFAUT[i]) racine.setProperty('--c' + i, c); else racine.removeProperty('--c' + i);
  });
}

// Redessine tout ce qui dépend des couleurs ou du fond : rien à recalculer.
function recolore() {
  appliqueCss();
  const classique = document.getElementById('canvas-classique');
  if (classique && motEntiers.length) dessineTresse(classique, motEntiers);
  lecteurs.forEach((l) => l.recolore());
}

// La tresse sélectionnée change (null : un exemple ou un mot qui n'est pas mémorisé).
function choisis(entree) {
  memoire.courant = entree ? entree.id : null;
  appliqueCouleurs(entree);
  ecrisMemoire();
  metsAJourSelection();
  afficheCouleurs();
}

// Ce qu'est le mot courant : une tresse enregistrée, un exemple fourni, ou un mot tapé qui n'est pas enregistré. Le bouton « Enregistrer »
// n'est actif que pour un mot qui ne l'est pas encore ; la note (modifiable) n'existe que pour une tresse enregistrée.
function metsAJourEtatMot() {
  const zone = document.getElementById('etat-mot');
  if (!zone) return;
  const bouton = document.getElementById('enregistrer-mot');
  const ligne = document.getElementById('ligne-note'), note = document.getElementById('note-mot');
  const entree = entreeCourante();
  const fournie = EXEMPLES.find((e) => motEnTexte(e.mot) === motCourant);
  if (!motCourant) zone.textContent = '';
  else if (entree) zone.textContent = '· enregistré dans tes tresses';
  else if (fournie) zone.textContent = '· exemple fourni : ' + fournie.legende;
  else zone.textContent = '· pas enregistré';
  bouton.disabled = !motCourant || !!entree;
  bouton.title = entree ? 'Ce mot est déjà enregistré dans tes tresses' : 'Enregistrer ce mot dans tes tresses (pour le colorer, le noter, le retrouver)';
  ligne.hidden = !entree;
  if (entree && document.activeElement !== note) note.value = entree.texte;
}

// Enregistre le mot courant dans les tresses de la personne (un exemple apporte sa légende comme note), puis envoie le focus sur la note.
function enregistreCourant() {
  if (motEntiers.length === 0 || entreeCourante()) return;
  const fournie = EXEMPLES.find((e) => motEnTexte(e.mot) === motEnTexte(motEntiers));
  const n = creeEntree({ mot: motEntiers, texte: fournie ? fournie.legende : '' });
  if (!n) return;
  ajouteCarte(n);
  choisis(n);
  annonce(`Tresse ${nomMot(n.mot)} enregistrée dans tes tresses.`);
  const note = document.getElementById('note-mot');
  if (note) note.focus();
}

// La note de la tresse enregistrée, modifiée dans la carte « Mot courant » (Entrée valide, Échap annule) ; la liste la montre sous le nom.
function metsAJourLegende(entree) {
  const carte = document.querySelector(`#exemples .perso[data-id="${entree.id}"]`);
  const l = carte && carte.querySelector('.legende');
  if (l) { l.textContent = entree.texte; l.hidden = !entree.texte; }
}

// ---- le menu « Tresses » : la liste des exemples et des tresses gardées s'ouvre sous le bouton, au clic
function fermeMenuTresses(rendFocus) {
  const menu = document.getElementById('menu-tresses'), bouton = document.getElementById('bouton-tresses');
  if (!menu || menu.hidden) return;
  menu.hidden = true;
  bouton.setAttribute('aria-expanded', 'false');
  document.removeEventListener('pointerdown', clicDehorsTresses, true);
  document.removeEventListener('keydown', toucheTresses, true);
  if (rendFocus) bouton.focus();
}
const clicDehorsTresses = (e) => { if (!document.getElementById('menu-tresses').contains(e.target) && !document.getElementById('bouton-tresses').contains(e.target)) fermeMenuTresses(false); };
const toucheTresses = (e) => { if (e.key === 'Escape') { e.stopPropagation(); fermeMenuTresses(true); } };
function ouvreMenuTresses() {
  const menu = document.getElementById('menu-tresses');
  menu.hidden = false;
  document.getElementById('bouton-tresses').setAttribute('aria-expanded', 'true');
  document.addEventListener('pointerdown', clicDehorsTresses, true);
  document.addEventListener('keydown', toucheTresses, true);
  const cible = menu.querySelector('.exemple.choisie .principal') || menu.querySelector('.exemple .principal');
  if (cible) { cible.focus({ preventScroll: true }); cible.scrollIntoView({ block: 'nearest' }); }
}

function metsAJourSelection() {
  metsAJourEtatMot();
  document.querySelectorAll('#exemples .exemple').forEach((carte) => {
    const choisie = carte.classList.contains('perso') ? carte.dataset.id === memoire.courant : memoire.courant === null && carte.dataset.mot === (motCourant || '');
    carte.classList.toggle('choisie', choisie);
    carte.querySelector('.principal').setAttribute('aria-pressed', String(choisie));
  });
}

// Une nouvelle entrée en fin de liste ; null (avec un message) quand la liste est pleine.
function creeEntree({ mot, texte = '', couleurs, fond }) {
  if (memoire.tresses.length >= MAX_TRESSES) {
    annonce(`${MAX_TRESSES} tresses mémorisées au plus : efface-en une avant d'en garder une autre.`);
    return null;
  }
  const v = validerEntree({ mot, texte, couleurs: couleurs || couleursParDefaut(nbBrins(mot)), fond: fond || FOND_DEFAUT });
  if (v.erreur) return null;
  v.id = nouvelId();
  memoire.tresses.push(v);
  return v;
}

function selectionneMot(mot, entree) {
  const champ = document.getElementById('mot');
  champ.value = motEnTexte(mot);
  choisis(entree);
  mise_a_jour(champ.value, { immediat: true });
}

// ---- les cartes (les exemples fournis, puis les tresses mémorisées)

function bouton(classe, texte, etiquette, titre) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'outil ' + classe;
  b.textContent = texte;
  b.setAttribute('aria-label', etiquette);
  b.title = titre || etiquette;
  return b;
}

function ajouteCarte(entree) {
  const carte = cartePerso(entree);
  document.getElementById('liste-perso').appendChild(carte);
  metsAJourListeVide();
  return carte;
}

// « Mes tresses » est vide : une phrase le dit et dit quoi faire.
function metsAJourListeVide() {
  const vide = document.querySelectorAll('#liste-perso .exemple').length === 0;
  document.getElementById('aucune-tresse').hidden = !vide;
}

function carteFournie(e) {
  const carte = document.createElement('div');
  carte.className = 'exemple';
  carte.dataset.mot = motEnTexte(e.mot);
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'principal';
  b.title = motEnTexte(e.mot);
  b.innerHTML = `<span class="nom">${coupable(e.nom)}</span><span class="legende">${e.legende}</span>`;
  b.onclick = () => { selectionneMot(e.mot, null); fermeMenuTresses(true); };
  const outils = document.createElement('span');
  outils.className = 'outils';
  const d = bouton('dupliquer', '⧉', `Dupliquer la tresse ${e.nom} dans mes tresses`, 'Dupliquer dans mes tresses');
  d.onclick = () => dupliqueEntree({ mot: e.mot, texte: e.legende, couleurs: null, fond: null });
  outils.appendChild(d);
  carte.append(b, outils);
  return carte;
}

function apercuCouleurs(entree) {
  const a = document.createElement('span');
  a.className = 'apercu';
  a.setAttribute('aria-hidden', 'true');
  entree.couleurs.forEach((c) => { const p = document.createElement('i'); p.style.background = c; a.appendChild(p); });
  const f = document.createElement('i');
  f.className = 'carre';
  f.style.background = entree.fond;
  a.appendChild(f);
  return a;
}

function cartePerso(entree) {
  const carte = document.createElement('div');
  carte.className = 'exemple perso';
  carte.dataset.id = entree.id;
  carte.dataset.mot = motEnTexte(entree.mot);
  const nom = nomMot(entree.mot);
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'principal';
  b.title = motEnTexte(entree.mot);
  const span = document.createElement('span');
  span.className = 'nom';
  span.textContent = coupable(nom);
  b.appendChild(span);
  const legende = document.createElement('span');
  legende.className = 'legende';
  legende.textContent = entree.texte;
  legende.hidden = !entree.texte;
  b.appendChild(legende);
  b.onclick = () => { selectionneMot(entree.mot, entree); fermeMenuTresses(true); };
  const outils = document.createElement('span');
  outils.className = 'outils';
  carte.append(b, outils);
  rendsOutils(carte, entree);
  carte.appendChild(apercuCouleurs(entree));
  return carte;
}

// Les boutons ⧉ et ✕ d'une carte mémorisée.
function rendsOutils(carte, entree) {
  const outils = carte.querySelector('.outils');
  outils.textContent = '';
  const nom = nomMot(entree.mot);
  const d = bouton('dupliquer', '⧉', `Dupliquer la tresse ${nom}`, 'Dupliquer');
  d.onclick = () => dupliqueEntree(entree);
  const x = bouton('effacer', '✕', `Effacer la tresse ${nom}`, 'Effacer');
  x.onclick = () => demandeEffacement(carte, entree);
  outils.append(d, x);
}

// L'effacement se confirme sur la carte même (« Effacer ? Oui Non »), le focus sur « Non » ; Échap annule.
function demandeEffacement(carte, entree) {
  const outils = carte.querySelector('.outils');
  outils.textContent = '';
  const question = document.createElement('span');
  question.className = 'confirme';
  question.setAttribute('role', 'alert');
  question.textContent = 'Effacer ? ';
  const oui = document.createElement('button');
  oui.type = 'button'; oui.className = 'outil oui'; oui.textContent = 'Oui';
  const non = document.createElement('button');
  non.type = 'button'; non.className = 'outil non'; non.textContent = 'Non';
  question.append(oui, non);
  outils.appendChild(question);
  non.focus();
  const annule = () => { rendsOutils(carte, entree); const x = carte.querySelector('.effacer'); if (x) x.focus(); };
  non.onclick = annule;
  carte.onkeydown = (ev) => { if (ev.key === 'Escape' && carte.querySelector('.confirme')) { ev.preventDefault(); annule(); } };
  oui.onclick = () => {
    const i = memoire.tresses.indexOf(entree);
    if (i < 0) return;
    const etait = memoire.courant === entree.id;
    const suivante = carte.nextElementSibling || carte.previousElementSibling;
    memoire.tresses.splice(i, 1);
    carte.remove();
    metsAJourListeVide();
    if (etait) choisis(null); else ecrisMemoire();
    annonce(`Tresse ${nomMot(entree.mot)} effacée.`);
    const cible = suivante && suivante.querySelector('.principal');
    (cible || document.getElementById('mot')).focus();
  };
}

// Dupliquer : une copie en fin de liste (pour un exemple : sa légende comme texte, les couleurs par défaut), sélectionnée.
function dupliqueEntree(source) {
  const n = creeEntree({ mot: source.mot, texte: source.texte, couleurs: source.couleurs ? source.couleurs.slice() : null, fond: source.fond });
  if (!n) return;
  const carte = ajouteCarte(n);
  selectionneMot(n.mot, n);
  carte.scrollIntoView({ block: 'nearest' });
  carte.querySelector('.principal').focus();
  annonce(`Tresse ${nomMot(n.mot)} dupliquée dans tes tresses.`);
}

// ---- les pastilles de couleur (dans la carte « Le mot ») : une par brin, puis le carré du fond

function luminance(couleur) {
  const c = [1, 3, 5].map((i) => parseInt(couleur.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contraste(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((u, v) => v - u);
  return (x + 0.05) / (y + 0.05);
}

// Un brin dont la couleur est presque celle du fond disparaît : un ⚠ le dit (un conseil, pas un blocage).
function metsAJourAlertes() {
  document.querySelectorAll('#pastilles .brin').forEach((span) => {
    const c = span.querySelector('input').value;
    span.querySelector('.alerte').hidden = contraste(c, FOND) >= 3;
  });
}

let imageDemandee = false;
function redessineVues() {   // au plus un redessin par image d'écran pendant qu'on déplace le curseur du sélecteur de couleur
  if (imageDemandee) return;
  imageDemandee = true;
  requestAnimationFrame(() => { imageDemandee = false; recolore(); metsAJourAlertes(); });
}

function afficheCouleurs() {
  const zone = document.getElementById('couleurs');
  if (!zone) return;
  if (motEntiers.length === 0) { zone.hidden = true; return; }
  zone.hidden = false;
  const entree = entreeCourante();
  const actif = entree !== null;
  const pastilles = document.getElementById('pastilles');
  pastilles.textContent = '';
  const n = nbBrins(motEntiers);
  const regle = (input, appliquer) => {
    input.addEventListener('input', () => { appliquer(input.value.toLowerCase()); redessineVues(); });
    input.addEventListener('change', () => {   // la fin du geste : on enregistre
      if (!entree) return;
      entree.couleurs = PALETTE.slice(0, nbBrins(entree.mot));
      entree.fond = FOND;
      ecrisMemoire();
      const carte = document.querySelector(`#exemples .perso[data-id="${entree.id}"]`);
      if (carte) carte.querySelector('.apercu').replaceWith(apercuCouleurs(entree));
    });
  };
  for (let i = 0; i < n; i++) {
    const span = document.createElement('span');
    span.className = 'brin';
    const input = document.createElement('input');
    input.type = 'color';
    input.className = 'pastille';
    input.value = PALETTE[i];
    input.disabled = !actif;
    input.setAttribute('aria-label', `Couleur du brin ${i + 1}`);
    input.title = `Couleur du brin ${i + 1}`;
    regle(input, (c) => { PALETTE[i] = c; });
    const alerte = document.createElement('span');
    alerte.className = 'alerte';
    alerte.textContent = '⚠';
    alerte.hidden = true;
    alerte.title = 'Cette couleur est presque celle du fond : le brin sera difficile à voir.';
    span.append(input, alerte);
    pastilles.appendChild(span);
  }
  const fond = document.createElement('input');
  fond.type = 'color';
  fond.className = 'pastille fond';
  fond.value = FOND;
  fond.disabled = !actif;
  fond.setAttribute('aria-label', 'Couleur du fond');
  fond.title = 'Couleur du fond';
  regle(fond, (c) => { FOND = c; });
  pastilles.appendChild(fond);
  document.getElementById('enregistrer-courante').hidden = actif;
  document.getElementById('couleurs-aide').textContent = actif ? '' : 'Pour changer les couleurs, enregistre d\'abord cette tresse dans tes tresses.';
  metsAJourAlertes();
}

// ---- exporter et importer ses tresses (un fichier JSON : { version, tresses: [{ mot, texte, couleurs, fond }] })

function exporteTresses() {
  const contenu = { version: 1, tresses: memoire.tresses.map(({ mot, texte, couleurs, fond }) => ({ mot, texte, couleurs, fond })) };
  const blob = new Blob([JSON.stringify(contenu, null, 2) + '\n'], { type: 'application/json' });
  const lien = document.createElement('a');
  lien.href = URL.createObjectURL(blob);
  lien.download = 'mes-tresses.json';
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  setTimeout(() => URL.revokeObjectURL(lien.href), 2000);
  annonce(memoire.tresses.length ? `${memoire.tresses.length} tresse${memoire.tresses.length > 1 ? 's' : ''} exportée${memoire.tresses.length > 1 ? 's' : ''} dans mes-tresses.json.` : 'Aucune tresse mémorisée : le fichier est vide.');
}

// Tout est validé avant d'écrire quoi que ce soit : un fichier invalide est refusé en entier, avec la raison.
function importeTresses(texte) {
  let j;
  try { j = JSON.parse(texte); } catch (e) { annonce('Fichier refusé : ce n\'est pas du JSON.'); return; }
  if (!j || j.version !== 1 || !Array.isArray(j.tresses)) { annonce('Fichier refusé : ce n\'est pas un fichier de tresses (version 1 attendue).'); return; }
  const lues = [];
  for (let i = 0; i < j.tresses.length; i++) {
    const v = validerEntree(j.tresses[i]);
    if (v.erreur) { annonce(`Fichier refusé : tresse ${i + 1} : ${v.erreur}.`); return; }
    lues.push(v);
  }
  const meme = (a, b) => motEnTexte(a.mot) === motEnTexte(b.mot) && a.texte === b.texte && a.fond === b.fond && a.couleurs.join() === b.couleurs.join();
  let ajoutees = 0, deja = 0, trop = 0;
  for (const v of lues) {
    if (memoire.tresses.some((e) => meme(e, v))) { deja++; continue; }
    const n = memoire.tresses.length >= MAX_TRESSES ? null : Object.assign(v, { id: nouvelId() });
    if (!n) { trop++; continue; }
    memoire.tresses.push(n);
    ajouteCarte(n);
    ajoutees++;
  }
  if (ajoutees) ecrisMemoire();
  annonce(`${ajoutees} tresse${ajoutees > 1 ? 's' : ''} importée${ajoutees > 1 ? 's' : ''}` + (deja ? `, ${deja} déjà présente${deja > 1 ? 's' : ''}` : '') +
    (trop ? `, ${trop} ignorée${trop > 1 ? 's' : ''} (plafond de ${MAX_TRESSES} tresses)` : '') + '.');
}

async function demarre() {
  afficheLimites();
  ajouteAides();
  chargeMemoire();
  const exemples = document.getElementById('liste-exemples'), perso = document.getElementById('liste-perso');
  EXEMPLES.forEach((e) => exemples.appendChild(carteFournie(e)));
  memoire.tresses.forEach((e) => perso.appendChild(cartePerso(e)));
  metsAJourListeVide();
  const panneaux = document.getElementById('panneaux');
  lecteurs = MODES.map((m) => new Lecteur(panneaux, m.id, m.titre, 800, 800, undefined, m.schema));
  const champ = document.getElementById('mot');
  try {
    ardoisePrincipale = await chargeBibliotheque();
  } catch (e) {
    const erreur = document.getElementById('erreur');
    erreur.textContent = e.message;
    erreur.hidden = false;
    return;
  }
  lanceLibres();
  let minuterie = null;
  champ.addEventListener('input', () => {
    clearTimeout(minuterie);
    minuterie = setTimeout(() => mise_a_jour(champ.value), 400);
  });
  champ.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); clearTimeout(minuterie); mise_a_jour(champ.value, { immediat: true }); } });
  document.getElementById('enregistrer-courante').onclick = enregistreCourant;
  document.getElementById('enregistrer-mot').onclick = enregistreCourant;
  const noteMot = document.getElementById('note-mot');
  noteMot.onchange = () => {
    const entree = entreeCourante();
    if (!entree) return;
    entree.texte = noteMot.value.trim().slice(0, MAX_TEXTE);
    noteMot.value = entree.texte;
    ecrisMemoire();
    metsAJourLegende(entree);
  };
  noteMot.onkeydown = (ev) => {
    const entree = entreeCourante();
    if (ev.key === 'Enter') { ev.preventDefault(); noteMot.blur(); }
    else if (ev.key === 'Escape' && entree) { noteMot.value = entree.texte; noteMot.blur(); }
  };
  const boutonTresses = document.getElementById('bouton-tresses');
  boutonTresses.onclick = () => (document.getElementById('menu-tresses').hidden ? ouvreMenuTresses() : fermeMenuTresses(true));
  document.getElementById('exporter-tresses').onclick = exporteTresses;
  const fichier = document.getElementById('importer-tresses');
  document.getElementById('importer-bouton').onclick = () => fichier.click();
  fichier.onchange = () => {
    const f = fichier.files[0];
    fichier.value = '';
    if (!f) return;
    if (f.size > 1e6) { annonce('Fichier refusé : il est trop gros (plus d\'un Mo).'); return; }
    const lecteur = new FileReader();
    lecteur.onload = () => importeTresses(String(lecteur.result));
    lecteur.onerror = () => annonce('Le fichier n\'a pas pu être lu.');
    lecteur.readAsText(f);
  };
  if (!memoire.disponible) annonce('La mémoire du navigateur n\'est pas disponible : tes tresses ne seront pas gardées quand tu fermeras la page.');
  // le mot de départ : celui du lien ; sinon la dernière tresse mémorisée sélectionnée ; sinon un exemple
  const lien = decodeURIComponent(location.hash.slice(1));
  const sauvee = entreeCourante();
  let entree = null, depart;
  if (lien) {
    depart = lien;
    const lu = lisMot(lien);
    if (sauvee && !lu.erreur && motEnTexte(lu.mot) === motEnTexte(sauvee.mot)) entree = sauvee;
  } else if (sauvee) {
    depart = motEnTexte(sauvee.mot);
    entree = sauvee;
  } else {
    depart = motEnTexte(EXEMPLES[7].mot);
  }
  champ.value = depart;
  choisis(entree);
  mise_a_jour(depart);
}

window.addEventListener('DOMContentLoaded', demarre);
