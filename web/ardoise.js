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
  { nom: 'σ₁σ₂σ₃σ₄', mot: [1, 2, 3, 4], legende: 'la rotation de 5 trous' },
  { nom: 'σ₄σ₃σ₁⁻²σ₂σ₄⁻¹σ₁', mot: [4, 3, -1, -1, 2, -4, 1], legende: 'une tresse à enroulements décroissants' },
  { nom: 'σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂', mot: [1, -2, 1, -2, 1, -2, 3, -1, 2], legende: 'une tresse à nombreux enroulements' },
];

const MAX_BRINS = 8;     // les limites de la page (les mêmes que dans ocaml/web/ardoise_web.ml)
const MAX_LETTRES = 40;
const MAX_BRINS_CONFORME = 6;     // les films des lacets (conforme et triangulation)
const MAX_LETTRES_CONFORME = 14;

// Une seule palette pour toutes les vues : le brin i du diagramme de tresse, le lacet image de x_i dans les trois films
// et la ligne x_i ↦ … de l'action sur F_n ont la même couleur (les variables CSS --c0 … --c7 de ardoise.css, un peu
// éclaircies en thème sombre, reprennent ces teintes pour le texte).
const PALETTE = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6', '#0d9aa6', '#e6761a', '#6b4fbb'];

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
  const largeur = (brins - 1) * maille + 2 * marge;
  const hauteur = mot.length * maille + 2 * marge;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(largeur * dpr);
  canvas.height = Math.round(hauteur * dpr);
  canvas.style.width = largeur + 'px';
  canvas.style.height = hauteur + 'px';
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#fff';
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
    trace(trou, '#fff', 0);      // le liseré blanc coupe ce qui passe dessous
    trace(brin, couleur, 1);
  };

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

function dessineEscargot(canvas, im) {
  const ctx = canvas.getContext('2d');
  const l = canvas.width, h = canvas.height;
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

function dessineBouquet(canvas, im) {
  const ctx = canvas.getContext('2d');
  const l = canvas.width, h = canvas.height, e = im.e;
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
  ['triangulation', 'Le maillage (une triangulation) sur lequel les brins sont posés : il se déplace avec les trous, et les brins le suivent et se tendent.'],
  ['diagramme', 'Le maillage (une triangulation) sur lequel les arcs sont posés et tendus : il se déplace avec les trous.'],
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

function dessineImage(canvas, image, mode, vue = null, construction = false) {
  if (mode === 'escargot') { dessineEscargot(canvas, image); return; }
  if (mode === 'bouquet') { dessineBouquet(canvas, image); return; }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (vue) ctx.setTransform(vue.s, 0, 0, vue.s, vue.tx, vue.ty);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (construction && image.construction) traceSegments(ctx, image.construction, GRIS_CONSTRUCTION, TRAIT_CONSTRUCTION, image.opacites);
  image.lacets.forEach((p, i) => {
    if (mode === 'conforme' || mode === 'triangulation') {
      ctx.strokeStyle = PALETTE[i % PALETTE.length];
      ctx.lineWidth = mode === 'triangulation' ? image.brin : 3.5;   // la triangulation : trait plus fin quand les brins sont serrés
      trace(ctx, p);
    } else if (mode === 'diagramme') {
      ctx.strokeStyle = '#fff';           // liseré blanc : les brins voisins restent lisibles
      ctx.lineWidth = 0.85 * image.ecart;
      trace(ctx, p);
      ctx.strokeStyle = PALETTE[i % PALETTE.length];
      ctx.lineWidth = 2.2;
      trace(ctx, p);
    } else {
      ctx.strokeStyle = PALETTE[i % PALETTE.length];
      ctx.lineWidth = 2.5;
      trace(ctx, p);
    }
  });
  if (mode === 'conforme' || mode === 'triangulation') {
    const r = mode === 'triangulation' ? image.brin : 4;
    disques(ctx, image.trous, r, '#000');
    disques(ctx, image.clou, r, '#000');
  } else {
    disques(ctx, image.fixes, 4, '#8c8c8c');
    disques(ctx, image.trous, 4, '#000');
  }
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
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  // Un nouveau mot : on repart de zéro.
  recommence() {
    this.arrete();
    this.images = [];
    this.fixe = null;
    this.vue = null;
    this.t = 0;
    this.efface();
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
    this.etat.innerHTML = `<button type="button" title="lecture / pause">⏸</button>` +
      `<input type="range" min="0" max="${duree - 1}" step="1" value="0" aria-label="position dans le film">` +
      (MODES_AVEC_CONSTRUCTION.has(this.mode)
        ? `<label><input type="checkbox" class="construction"${this.construction ? ' checked' : ''}> construction</label><span class="emplacement-aide"></span>`
        : '') +
      (message ? `<span class="ko" title="${message}">⚠</span>` : '');
    this.bouton = this.etat.querySelector('button');
    this.curseur = this.etat.querySelector('input[type=range]');
    const case_ = this.etat.querySelector('input.construction');
    if (case_) case_.onchange = () => { this.construction = case_.checked; this.montre(); };
    const place = this.etat.querySelector('.emplacement-aide');
    if (place) place.replaceWith(aideBulle('construction-' + this.mode, 'Lignes de construction : explication',
      `<span class="texte-bulle"><b>Lignes de construction.</b> ${MODES_AVEC_CONSTRUCTION.get(this.mode)}</span>`));
    this.bouton.onclick = () => (this.lecture ? this.arrete() : this.joue());
    this.bouton.title = 'lecture / pause (relance le film s\'il est fini)';
    this.curseur.oninput = () => { this.arrete(); this.t = Number(this.curseur.value); this.montre(); };
  }

  duree() { return this.pauseDebut + (this.images.length - 1); }

  montre() {
    const n = this.images.length;
    const k = this.t < this.pauseDebut ? 0 : Math.min(n - 1, Math.floor(this.t - this.pauseDebut));
    dessineImage(this.canvas, this.images[k], this.mode, this.vue, this.construction);
    if (this.curseur) this.curseur.value = String(Math.floor(this.t));
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
  lacets: ['Lacets conformes', 'Des demi-cercles du demi-plan et leurs images par la transformation conforme : des arcs à angle droit autour des sommets de la ligne brisée L–A–B–R. La case « lignes de construction » trace l\'axe et cette ligne brisée ; pendant le demi-tour, elles s\'estompent et le dessin passe par une triangulation mobile.'],
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

const MODES = [
  { id: 'diagramme', titre: 'Diagramme de courbes', schema: 'diagramme' },
  { id: 'conforme', titre: 'Action sur le groupe libre et ses lacets', schema: 'lacets', limite: true },
  { id: 'triangulation', titre: 'Action sur le groupe libre et sa triangulation', schema: 'triangulation', limite: true },
  { id: 'rubans', titre: 'Action sur le groupe libre et ses rubans', schema: 'rubans' },
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

// Le mode de calcul d'une vue, quand il diffère de son nom : les lacets sont le film conforme détendu pendant le raccord
// (Detente ; travail.js en répartit la détente sur plusieurs workers).
const MODE_DE_CALCUL = { conforme: 'conforme_detendu' };

// Un Web Worker pour un mode et un lecteur ; rend le worker (ou null si le navigateur refuse, par exemple en file://).
function demarreTravailleur(mode, mot, lecteur) {
  let w;
  try {
    w = new Worker('travail.js');
  } catch (e) {
    lecteur.vide('Ouvre la page par un serveur (python -m http.server dans web/), pas en file://.');
    return null;
  }
  w.onerror = () => lecteur.vide('le calcul a échoué (ardoise_lib.js introuvable ? voir construit.sh)');
  w.onmessage = (e) => {
    const d = e.data;
    if (d.type === 'statique') lecteur.recoitFixe(d.image);
    else if (d.type === 'image') lecteur.recoitImage(d.image, d.k, d.total);
    else if (d.type === 'fini') lecteur.fini(d.message, d.erreur);
  };
  w.postMessage({ mode: MODE_DE_CALCUL[mode] || mode, mot });
  return w;
}

function lanceCalculs(mot) {
  arreteTravailleurs();
  lecteurs.forEach((l) => l.recommence());
  const brins = nbBrins(mot), lettres = mot.length;
  const trop = [];
  if (brins > MAX_BRINS_CONFORME) trop.push(`${brins} brins (limite : ${MAX_BRINS_CONFORME})`);
  if (lettres > MAX_LETTRES_CONFORME) trop.push(`${lettres} lettres (limite : ${MAX_LETTRES_CONFORME})`);
  MODES.forEach((m, j) => {
    if (m.limite && trop.length) {   // les vues « lacets » et « triangulation » sont limitées : on le dit au lieu de lancer un calcul trop long
      lecteurs[j].indisponible([`Ce mot a ${trop.join(' et ')} : trop pour cette vue.`, 'Les autres vues sont calculées.']);
      return;
    }
    const w = demarreTravailleur(m.id, mot, lecteurs[j]);
    if (w) travailleurs.push(w);
  });
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
  document.querySelectorAll('.exemple').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mot === cle)));
  if (cle === motCourant) return;
  motCourant = cle;
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

// « Ce mot : N brins, M lettres », avec l'avertissement quand une vue est limitée.
function etatLimites(mot) {
  const e = document.getElementById('etat-limites');
  if (!e) return;
  if (!mot || mot.length === 0) { e.textContent = ''; return; }
  const brins = nbBrins(mot), lettres = mot.length;
  const hors = brins > MAX_BRINS_CONFORME || lettres > MAX_LETTRES_CONFORME;
  e.innerHTML = `Ce mot : <b>${brins} brins</b>, <b>${lettres} lettre${lettres > 1 ? 's' : ''}</b>.` +
    (hors ? ' <span class="attention">Les vues « lacets » et « triangulation » ne sont pas calculées pour ce mot.</span>' : '');
}

async function demarre() {
  afficheLimites();
  ajouteAides();
  const exemples = document.getElementById('exemples');
  EXEMPLES.forEach((e) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'exemple';
    b.dataset.mot = e.mot.join(' ');
    b.title = e.mot.join(' ');
    b.innerHTML = `<span class="nom">${e.nom}</span><span class="legende">${e.legende}</span>`;
    b.onclick = () => { champ.value = e.mot.join(' '); mise_a_jour(champ.value, { immediat: true }); };
    exemples.appendChild(b);
  });
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
  const depart = decodeURIComponent(location.hash.slice(1)) || EXEMPLES[7].mot.join(' ');
  champ.value = depart;
  mise_a_jour(depart);
}

window.addEventListener('DOMContentLoaded', demarre);
