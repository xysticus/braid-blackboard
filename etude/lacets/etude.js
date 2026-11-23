'use strict';
// Le banc d'essai du film des lacets (mode « conforme » de la page publique) : le même calcul (web/travail.js, qui charge
// web/ardoise_lib.js), un seul film, un canvas de 1600 × 1600 (les images sont calculées dans 800 × 800 : échelle 2), un lecteur
// pas à pas, les lignes de construction et les tangentes des arcs aux points où ils les rencontrent.
// Rien ici n'est déployé : la page publique est dans web/.

const EXEMPLES = [
  { nom: 'σ₁', mot: [1], legende: 'le demi-tour le plus simple' },
  { nom: 'σ₁σ₃', mot: [1, 3], legende: 'deux générateurs qui commutent : σ₁σ₃ = σ₃σ₁' },
  { nom: 'Δ₅', mot: [1, 2, 3, 4, 1, 2, 3, 1, 2, 1], legende: 'demi-tour positif à 5 brins' },
  { nom: 'Δ₅⁻¹', mot: [-1, -2, -1, -3, -2, -1, -4, -3, -2, -1], legende: 'demi-tour négatif à 5 brins' },
  { nom: '(σ₁σ₂)³', mot: [1, 2, 1, 2, 1, 2], legende: 'tour complet à 3 brins : conjugaison par x₁x₂x₃' },
  { nom: 'σ₁σ₂σ₁σ₂⁻¹σ₁⁻¹σ₂⁻¹', mot: [1, 2, 1, -2, -1, -2], legende: 'un mot qui vaut la tresse nulle' },
  { nom: 'σ₁σ₂⁻¹', mot: [1, -2], legende: 'courte, mais pseudo-Anosov' },
  { nom: '(σ₁σ₂⁻¹)³', mot: [1, -2, 1, -2, 1, -2], legende: '6 lettres, 51 dans F₃ ; sa fermeture : les anneaux de Borroméo' },
  { nom: 'σ₂σ₃σ₁σ₄σ₃σ₂', mot: [2, 3, 1, 4, 3, 2], legende: 'tresse simple à 5 brins : la permutation (1 3)(2 5)' },
  { nom: 'σ₃σ₂σ₁σ₄σ₃σ₂', mot: [3, 2, 1, 4, 3, 2], legende: 'tresse simple à 5 brins : le 5-cycle (1 3 5 2 4)' },
  { nom: 'σ₄σ₃σ₁⁻²σ₂σ₄⁻¹σ₁', mot: [4, 3, -1, -1, 2, -4, 1], legende: 'une tresse à enroulements décroissants' },
  { nom: 'σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂', mot: [1, -2, 1, -2, 1, -2, 3, -1, 2], legende: 'une tresse à nombreux enroulements' },
];

const MAX_BRINS = 6;      // les limites du film conforme (web/ardoise.js)
const MAX_LETTRES = 14;
const IMAGES_PAR_LETTRE = 48;   // nombre_images_conforme de ocaml/web/ardoise_web.ml
// Images par lettre du film affiché : 48 pour les lacets conformes ; pour la triangulation, le nombre de sous-pas du film (tout le film
// se partage également entre les lettres).
const imagesParLettre = () => etat.film !== 'conforme' && etat.mot.length && etat.total > 1 ? Math.round((etat.total - 1) / etat.mot.length) : IMAGES_PAR_LETTRE;
const ECHELLE = 2;              // 1600 / 800
const PALETTE = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6', '#0d9aa6', '#e6761a', '#6b4fbb'];
// Pendant le raccord, la ligne de départ (L–A, B–R : opacité 1 − poids) et la ligne d'arrivée (L–B, A–R : opacité poids) coexistent, l'une
// s'estompant dans l'autre. Les rencontres sur la ligne la plus claire sont éphémères : elles n'imposent pas leur tangente (elles sont
// tracées en gris clair, sans tangente : des points « fantômes », ni leur tangente ni leur position ne sont imposées, c'est l'arc, fixé par ses deux
// extrémités et ses deux tangentes, qui les induit) ; celles de la ligne la plus foncée, et de toutes les lignes pleines (axe, A–B), l'imposent.
// Les fantômes sont tracés même sur une ligne presque effacée (toute ligne que le calcul fournit, c'est-à-dire d'opacité > 0).
const SEUIL_IMPOSE = 0.5;       // une ligne en transition impose ses tangentes si son opacité dépasse ce seuil
const LONGUEUR_TANGENTE = 38;   // en pixels de l'image de 800

// Les icônes des boutons (SVG, même dessin pour un pas en avant et un pas en arrière : un triangle et une barre verticale).
const ICONES = {
  "joue": "<svg viewBox=\"0 0 24 24\" width=\"24\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><polygon points=\"7,5 19,12 7,19\"/></svg>",
  "debut": "<svg viewBox=\"0 0 25 24\" width=\"25\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><rect x=\"3\" y=\"5\" width=\"3\" height=\"14\"/><polygon points=\"14,5 6.5,12 14,19\"/><polygon points=\"22,5 14.5,12 22,19\"/></svg>",
  "lettre-moins": "<svg viewBox=\"0 0 24 24\" width=\"24\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><polygon points=\"12,5 4,12 12,19\"/><polygon points=\"21,5 13,12 21,19\"/></svg>",
  "moins": "<svg viewBox=\"0 0 24 24\" width=\"24\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><rect x=\"4\" y=\"5\" width=\"3\" height=\"14\"/><polygon points=\"20,5 9,12 20,19\"/></svg>",
  "plus": "<svg viewBox=\"0 0 24 24\" width=\"24\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><polygon points=\"4,5 15,12 4,19\"/><rect x=\"17\" y=\"5\" width=\"3\" height=\"14\"/></svg>",
  "lettre-plus": "<svg viewBox=\"0 0 24 24\" width=\"24\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><polygon points=\"3,5 11,12 3,19\"/><polygon points=\"12,5 20,12 12,19\"/></svg>",
  "fin": "<svg viewBox=\"0 0 25 24\" width=\"25\" height=\"20\" aria-hidden=\"true\" fill=\"currentColor\"><polygon points=\"3,5 10.5,12 3,19\"/><polygon points=\"11,5 18.5,12 11,19\"/><rect x=\"19\" y=\"5\" width=\"3\" height=\"14\"/></svg>"
};
const ICONE_PAUSE = '<svg viewBox="0 0 24 24" width="24" height="20" aria-hidden="true" fill="currentColor"><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></svg>';

const $ = (id) => document.getElementById(id);
const EXPOSANTS = { '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9' };
const SOUS = '₀₁₂₃₄₅₆₇₈₉', SUR = '⁰¹²³⁴⁵⁶⁷⁸⁹';
const en = (n, chiffres) => String(n).split('').map((c) => chiffres[Number(c)]).join('');
const nomLettre = (k) => 'σ' + en(Math.abs(k), SOUS) + (k < 0 ? '⁻¹' : '');

// « 1 -2 3 », « σ1 σ2^-1 », « σ₁σ₂⁻¹ », « s1^3 s2 » → { mot } ou { erreur }
function lisMot(texte) {
  let t = texte.trim();
  if (t === '') return { mot: [] };
  t = t.replace(/[₀-₉]/g, (c) => String(c.charCodeAt(0) - 0x2080)).replace(/⁻/g, '^-')
       .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, (c) => EXPOSANTS[c]).replace(/[{}]/g, '').replace(/[σΣsS,;]/g, ' ').replace(/\s*\^\s*/g, '^');
  const mot = [];
  for (const jeton of t.split(/\s+/).filter(Boolean)) {
    const m = /^(-?)(\d+)(?:\^(-?)(\d+))?$/.exec(jeton);
    if (!m) return { erreur: `je ne comprends pas « ${jeton} »` };
    const indice = Number(m[2]);
    if (indice === 0) return { erreur: 'σ₀ n\'existe pas : les indices commencent à 1' };
    let signe = m[1] === '-' ? -1 : 1, fois = 1;
    if (m[4] !== undefined) { fois = Number(m[4]); if (m[3] === '-') signe = -signe; }
    if (fois > MAX_LETTRES) return { erreur: `exposant trop grand dans « ${jeton} »` };
    for (let j = 0; j < fois; j++) mot.push(signe * indice);
    if (mot.length > 10 * MAX_LETTRES) break;
  }
  const brins = mot.reduce((a, k) => Math.max(a, Math.abs(k)), 0) + 1;
  if (mot.length > MAX_LETTRES) return { erreur: `${mot.length} lettres : ce film en accepte ${MAX_LETTRES} au plus` };
  if (brins > MAX_BRINS) return { erreur: `${brins} brins : ce film en accepte ${MAX_BRINS} au plus` };
  return { mot };
}

// ---------------------------------------------------------------- l'état du lecteur

const etat = {
  mot: [], images: [], total: 0, k: 0, lecture: false, derniere: 0, reste: 0, travailleur: null,
  construction: true, tangentes: true, points: true, fantomes: true, libre: false, etude: true, sansMaillage: false, satellites: false, maillage: false, precalcule: null, detendu: true, film: 'conforme', reprise: null, ips: 25, vue: null,
};
const toile = $('toile');

function etenduePartout(images) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const im of images) for (const p of im.lacets) for (let j = 0; j < p.length; j += 2) {
    x0 = Math.min(x0, p[j]); x1 = Math.max(x1, p[j]); y0 = Math.min(y0, p[j + 1]); y1 = Math.max(y1, p[j + 1]);
  }
  return { x0, y0, x1, y1 };
}

// Un zoom arrière seulement si des brins sortent du cadre de 800 × 800 (la même vue pour tout le film).
function calculeVue(images) {
  const e = etenduePartout(images), marge = 14, w = e.x1 - e.x0, h = e.y1 - e.y0;
  if (!(w > 0) || !(h > 0)) return { s: 1, tx: 0, ty: 0 };
  if (e.x0 >= marge && e.y0 >= marge && e.x1 <= 800 - marge && e.y1 <= 800 - marge) return { s: 1, tx: 0, ty: 0 };
  const s = Math.min(1, (800 - 2 * marge) / w, (800 - 2 * marge) / h);
  return { s, tx: 400 - s * (e.x0 + e.x1) / 2, ty: 400 - s * (e.y0 + e.y1) / 2 };
}

// ---------------------------------------------------------------- les tangentes

// Les points où une polyligne de lacet (x0, y0, x1, y1, …) coupe un segment de construction (a → b) : { x, y, dx, dy } avec
// (dx, dy) le vecteur unitaire du segment du lacet qui traverse. Intervalle semi-ouvert sur le lacet : un sommet posé sur la
// ligne n'est compté qu'une fois.
function rencontres(p, a, b) {
  const res = [];
  const ex = b[0] - a[0], ey = b[1] - a[1];
  for (let j = 0; j + 3 < p.length; j += 2) {
    const dx = p[j + 2] - p[j], dy = p[j + 3] - p[j + 1];
    const den = dx * ey - dy * ex;
    if (den === 0) continue;
    const qx = a[0] - p[j], qy = a[1] - p[j + 1];
    const t = (qx * ey - qy * ex) / den;       // sur le lacet
    const u = (qx * dy - qy * dx) / den;       // sur la ligne de construction
    if (t >= 0 && t < 1 && u >= 0 && u <= 1) {
      const n = Math.hypot(dx, dy);
      if (n > 0) res.push({ x: p[j] + t * dx, y: p[j + 1] + t * dy, dx: dx / n, dy: dy / n });
    }
  }
  return res;
}

function toutesRencontres(image) {
  const c = image.construction, o = image.opacites;
  const sortie = [];
  if (!c) return sortie;
  for (let s = 0; 4 * s + 3 < c.length; s++) {
    const impose = !o || o[s] >= 1 - 1e-6 || o[s] > SEUIL_IMPOSE;
    const a = [c[4 * s], c[4 * s + 1]], b = [c[4 * s + 2], c[4 * s + 3]];
    image.lacets.forEach((p, i) => rencontres(p, a, b).forEach((r) => sortie.push({ ...r, lacet: i, segment: s, impose, tangente: impose && !(etat.libre && s === image.ab) })));   // arcs libres : pas de tangente imposée sur A–B (sa position, si)
  }
  return sortie;
}

// ---------------------------------------------------------------- le dessin

function trace(ctx, p) {
  if (p.length < 4) return;
  ctx.beginPath();
  ctx.moveTo(p[0], p[1]);
  for (let j = 2; j < p.length; j += 2) ctx.lineTo(p[j], p[j + 1]);
  ctx.stroke();
}

function disques(ctx, xy, r, couleur) {
  ctx.fillStyle = couleur;
  for (let j = 0; j + 1 < xy.length; j += 2) { ctx.beginPath(); ctx.arc(xy[j], xy[j + 1], r, 0, 2 * Math.PI); ctx.fill(); }
}

function segments(ctx, s, opacites, styles = null) {
  const alpha = ctx.globalAlpha;
  for (let j = 0; 4 * j + 3 < s.length; j++) {
    ctx.strokeStyle = styles ? styles[j].couleur : '#999';
    ctx.lineWidth = styles ? styles[j].largeur : 2.2;
    ctx.globalAlpha = alpha * (opacites ? opacites[j] : 1);
    ctx.beginPath(); ctx.moveTo(s[4 * j], s[4 * j + 1]); ctx.lineTo(s[4 * j + 2], s[4 * j + 3]); ctx.stroke();
  }
  ctx.globalAlpha = alpha;
}

// ---------------------------------------------------------------- l'étude de la projection

const COULEUR_DEPART = '#e69f00', COULEUR_ARRIVEE = '#8e44ad', COULEUR_AB = '#4a4a4a';

// Le style de chaque ligne de construction : les lignes sur lesquelles on projette en couleur (le départ en orange, l'arrivée en violet, A–B
// en gris foncé), l'axe en gris. Après les morceaux de l'axe (indices < ab) viennent A–B, puis, selon la phase : départ L–A, B–R (phase 0),
// arrivée L–B, A–R (phase 2), ou les deux (phase 1 : L–A, B–R, L–B, A–R).
function stylesDeConstruction(image) {
  const n = image.construction.length / 4;
  const styles = [];
  for (let j = 0; j < n; j++) {
    let c = { couleur: '#999', largeur: 2.2 };
    if (j === image.ab) c = { couleur: COULEUR_AB, largeur: 5 };
    else if (j > image.ab) {
      const r = j - image.ab - 1, ph = image.etude.phase;
      const depart = ph === 0 || (ph === 1 && r < 2);
      c = { couleur: depart ? COULEUR_DEPART : COULEUR_ARRIVEE, largeur: 5 };
    }
    styles.push(c);
  }
  return styles;
}

// Les étiquettes L, A, B, R : A et B sont les deux bouts de A–B ; L est le premier point du segment qui suit A–B, R le dernier point du second.
function etiquettes(ctx, image) {
  const c = image.construction, a = image.ab;
  const pt = (seg, fin) => [c[4 * seg + (fin ? 2 : 0)], c[4 * seg + (fin ? 3 : 1)]];
  const pose = (nom, p, couleur) => {
    if (!p || !Number.isFinite(p[0])) return;
    ctx.font = '700 17px system-ui, sans-serif';
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#fff'; ctx.lineWidth = 5; ctx.strokeText(nom, p[0] + 9, p[1] - 9);
    ctx.fillStyle = couleur; ctx.fillText(nom, p[0] + 9, p[1] - 9);
  };
  pose('A', pt(a, false), COULEUR_AB);
  pose('B', pt(a, true), COULEUR_AB);
  if (4 * (a + 1) + 3 < c.length) pose('L', pt(a + 1, false), '#333');
  if (4 * (a + 2) + 3 < c.length) pose('R', pt(a + 2, true), '#333');
}

// Le plan w : les antécédents des sommets de la ligne brisée sur l'axe réel, les demi-cercles dont les arcs sont les images (en haut : arcs
// du haut ; en bas : arcs du bas, en miroir), et l'antécédent du clou dans le demi-plan du bas.
function dessinePlanW(canvas, plan, actif, noms) {
  const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
  if (!plan) return;
  const arcs = [];
  for (let j = 0; j + 3 < plan.arcs.length; j += 4) arcs.push({ lacet: plan.arcs[j], haut: plan.arcs[j + 1] === 1, w0: plan.arcs[j + 2], w1: plan.arcs[j + 3] });
  const xs = [...plan.w, plan.clou[0]];
  arcs.forEach((a) => xs.push(a.w0, a.w1));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let haut = 1, bas = plan.clou[1];
  arcs.forEach((a) => { const r = Math.abs(a.w1 - a.w0) / 2; if (a.haut) haut = Math.max(haut, r); else bas = Math.max(bas, r); });
  const marge = 22;
  const S = Math.min((W - 2 * marge) / Math.max(1, x1 - x0), (H - 2 * marge) / (haut + bas));
  const X = (w) => marge + (w - x0) * S + ((W - 2 * marge) - (x1 - x0) * S) / 2;
  const Y0 = marge + haut * S + ((H - 2 * marge) - (haut + bas) * S) / 2;
  ctx.globalAlpha = actif ? 1 : 0.5;
  ctx.lineCap = 'round';
  ctx.fillStyle = '#f4f6fa'; ctx.fillRect(0, Y0, W, H - Y0);   // le demi-plan du bas, très légèrement teinté
  ctx.strokeStyle = '#777'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, Y0); ctx.lineTo(W, Y0); ctx.stroke();
  arcs.forEach((a) => {
    const m = (a.w0 + a.w1) / 2, r = Math.abs(a.w1 - a.w0) / 2;
    ctx.strokeStyle = PALETTE[a.lacet % PALETTE.length];
    ctx.lineWidth = 2.6;
    ctx.beginPath(); ctx.arc(X(m), Y0, r * S, a.haut ? Math.PI : 0, a.haut ? 2 * Math.PI : Math.PI); ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle;
    [a.w0, a.w1].forEach((w) => { ctx.beginPath(); ctx.arc(X(w), Y0, 3.2, 0, 2 * Math.PI); ctx.fill(); });   // les pieds
  });
  ctx.font = '700 15px system-ui, sans-serif';
  plan.w.forEach((w, j) => {
    ctx.strokeStyle = '#111'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(X(w), Y0 - 9); ctx.lineTo(X(w), Y0 + 9); ctx.stroke();
    ctx.fillStyle = '#111'; ctx.fillText(noms[j] || '', X(w) - 5, Y0 - 13);
  });
  ctx.fillStyle = '#000';
  ctx.beginPath(); ctx.arc(X(plan.clou[0]), Y0 + plan.clou[1] * S, 5, 0, 2 * Math.PI); ctx.fill();
  ctx.font = '12px system-ui, sans-serif';
  ctx.fillText('clou', X(plan.clou[0]) + 8, Y0 + plan.clou[1] * S + 4);
  ctx.fillStyle = '#888'; ctx.fillText('demi-plan du haut', 6, 14); ctx.fillText('demi-plan du bas', 6, H - 8);
  ctx.globalAlpha = 1;
}

// La chronologie d'une lettre : de quand à quand chaque dessin est projeté.
// L'intensité de la détente au pas n d'une lettre (1 … 48), comme Film_conforme.film ~detente et web/travail.js : 4 poids (1 − poids).
function forceDetente(n) {
  if (n <= 0) return 0;
  const lisse = (u) => u * u * (3 - 2 * u);
  const s = lisse(n / IMAGES_PAR_LETTRE);
  const poids = lisse(Math.min(1, Math.max(0, (s - 0.25) / 0.5)));
  return poids > 0 && poids < 1 ? 4 * poids * (1 - poids) : 0;
}

function dessineChrono(canvas, e, pas) {
  const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, N = IMAGES_PAR_LETTRE;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
  const x = (n) => 24 + (W - 48) * n / N;
  const y0 = 34, h = 28;
  ctx.fillStyle = COULEUR_DEPART; ctx.fillRect(x(0), y0, x(e.na) - x(0), h);
  ctx.fillStyle = COULEUR_ARRIVEE; ctx.fillRect(x(e.nb), y0, x(N) - x(e.nb), h);
  const g = ctx.createLinearGradient(x(e.na), 0, x(e.nb), 0); g.addColorStop(0, COULEUR_DEPART); g.addColorStop(1, COULEUR_ARRIVEE);
  ctx.globalAlpha = 0.45; ctx.fillStyle = g; ctx.fillRect(x(e.na), y0, x(e.nb) - x(e.na), h); ctx.globalAlpha = 1;
  ctx.font = '600 13px system-ui, sans-serif'; ctx.fillStyle = '#222';
  ctx.fillText('DÉPART (conforme)', x(0), y0 - 8);
  ctx.textAlign = 'center'; ctx.fillText(etat.detendu ? 'RACCORD (maillage + détente)' : 'RACCORD (maillage)', (x(e.na) + x(e.nb)) / 2, y0 - 8);
  if (etat.detendu) {   // l'intensité de la détente, de 0 (bas de la bande) à 1 (haut)
    ctx.strokeStyle = '#111'; ctx.lineWidth = 1.6; ctx.setLineDash([4, 3]);
    ctx.beginPath();
    for (let n = e.na; n <= e.nb; n++) { const X = x(n), Y = y0 + h - forceDetente(n) * (h - 3); n === e.na ? ctx.moveTo(X, Y) : ctx.lineTo(X, Y); }
    ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.textAlign = 'right'; ctx.fillText('ARRIVÉE (conforme)', x(N), y0 - 8); ctx.textAlign = 'left';
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = '#444';
  [[0, 0], [e.na, e.sa], [e.nb, e.sb], [N, 1]].forEach(([n, s], j) => {
    ctx.textAlign = j === 0 ? 'left' : j === 3 ? 'right' : 'center';
    ctx.fillText(`image ${n}`, x(n), y0 + h + 15); ctx.fillText(`s = ${s.toFixed(3)}`, x(n), y0 + h + 29);
  });
  ctx.textAlign = 'left';
  ctx.strokeStyle = '#000'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(x(pas), y0 - 4); ctx.lineTo(x(pas), y0 + h + 4); ctx.stroke();
  ctx.fillStyle = '#000'; ctx.beginPath(); ctx.moveTo(x(pas), y0 - 4); ctx.lineTo(x(pas) - 5, y0 - 12); ctx.lineTo(x(pas) + 5, y0 - 12); ctx.fill();
}

// La projection tout au long du mot : une bande par lettre (départ orange, raccord dégradé, arrivée violette), le curseur à l'image courante.
// Une image clé (la dernière de la lettre j) est l'arrivée de la lettre j et le départ de la lettre j+1 : la bande orange suivante
// recommence donc sur le même dessin, reprojeté sur la ligne brisée de la lettre suivante.
function dessineChronoMot(canvas, k) {
  const ctx = canvas.getContext('2d'), W = canvas.width, H = canvas.height, N = IMAGES_PAR_LETTRE, L = etat.mot.length;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);
  const x = (n) => 14 + (W - 28) * n / (L * N);
  const y0 = 30, h = 24;
  ctx.font = '600 12px system-ui, sans-serif'; ctx.textAlign = 'center';
  for (let j = 0; j < L; j++) {
    const im = etat.images[j * N + 1], e = im && im.etude;
    if (!e) continue;
    const a = x(j * N), na = x(j * N + e.na), nb = x(j * N + e.nb), b = x((j + 1) * N);
    ctx.fillStyle = COULEUR_DEPART; ctx.fillRect(a, y0, na - a, h);
    ctx.fillStyle = COULEUR_ARRIVEE; ctx.fillRect(nb, y0, b - nb, h);
    const g = ctx.createLinearGradient(na, 0, nb, 0); g.addColorStop(0, COULEUR_DEPART); g.addColorStop(1, COULEUR_ARRIVEE);
    ctx.globalAlpha = 0.45; ctx.fillStyle = g; ctx.fillRect(na, y0, nb - na, h); ctx.globalAlpha = 1;
    ctx.fillStyle = (k >= 1 && Math.floor((k - 1) / N) === j) ? '#000' : '#555';
    ctx.fillText(`${j + 1} · ${nomLettre(etat.mot[j])}`, (a + b) / 2, y0 - 8);
    ctx.fillStyle = '#fff'; ctx.fillRect(b - 1, y0 - 2, 2, h + 4);   // la frontière entre deux lettres
    ctx.fillStyle = '#444'; ctx.font = '11px system-ui, sans-serif';
    ctx.fillText(`${j * N + 1}–${(j + 1) * N + 1}`, (a + b) / 2, y0 + h + 14);
    ctx.font = '600 12px system-ui, sans-serif';
  }
  ctx.textAlign = 'left';
  ctx.strokeStyle = '#000'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(x(k), y0 - 4); ctx.lineTo(x(k), y0 + h + 4); ctx.stroke();
}

function metsAJourProjection(k) {
  const bloc = $('projection'), journal = $('journal');
  if (!etat.etude || !etat.images[k]) { bloc.hidden = true; journal.hidden = true; return; }
  const image = etat.images[k];
  // l'image 0 (l'image clé de départ) n'a pas de journal : on emprunte la chronologie et les plans à l'image suivante
  const e = image.etude || (etat.images[1] && etat.images[1].etude);
  if (!e) { bloc.hidden = true; journal.hidden = true; return; }
  bloc.hidden = false; journal.hidden = false;
  const pas = k === 0 ? 0 : ((k - 1) % IMAGES_PAR_LETTRE) + 1;
  const j = k === 0 ? 0 : Math.floor((k - 1) / IMAGES_PAR_LETTRE), m = k === 0 ? 0 : ((k - 1) % IMAGES_PAR_LETTRE) + 1;
  const relais = [];
  if (m === IMAGES_PAR_LETTRE && j + 1 < etat.mot.length)
    relais.push(`relais : cette image clé (image ${k + 1}) est aussi le départ de la lettre ${j + 2} (${nomLettre(etat.mot[j + 1])}) : le même dessin y est reprojeté, mais sur la ligne brisée L–A–B–R de cette lettre, jusqu'à l'image ${k + 1 + e.na} environ.`);
  if (m === 1 && j > 0)
    relais.push(`relais : l'image ${k} (clé de la lettre ${j}, ${nomLettre(etat.mot[j - 1])}) avait projeté ce même état comme arrivée ; il est ici reprojeté comme départ de la lettre ${j + 1} (${nomLettre(etat.mot[j])}).`);
  if (image.etude && etat.detendu) {
    const f = forceDetente(m);
    relais.unshift(f > 0
      ? `DÉTENTE (film de la page) : intensité ${f.toFixed(3)} = 4 poids (1 − poids), maximale au milieu du raccord : chaque brin est rééchantillonné (pas 4 px), puis 400 itérations de tension (chaque point vers le milieu de ses voisins) et de répulsion (brins à moins de 6 px, éteinte près du clou ; trous à moins de 12 px), pas borné à 0,3 px.`
      : 'DÉTENTE : aucune à cette image (hors du raccord, l\'intensité est nulle) : le dessin est celui de la projection.');
  }
  journal.textContent = (image.etude ? image.etude.journal.concat(relais).join('\n') :
    `image 0 : l'image clé de départ (avant la première lettre) : l'état 0 est projeté sur la ligne brisée L–A–B–R, comme pendant toute la phase 1.\n` +
    `chronologie de la lettre 1 : départ projeté aux images 0 à ${e.na} (s de 0 à ${e.sa.toFixed(4)}) ; raccord aux images ${e.na + 1} à ${e.nb - 1} ; arrivée projetée aux images ${e.nb} à ${IMAGES_PAR_LETTRE} (s de ${e.sb.toFixed(4)} à 1).`);
  $('chrono-mot').hidden = etat.mot.length < 2;
  if (etat.mot.length > 1) dessineChronoMot($('chrono-mot'), k);
  dessineChrono($('chrono'), e, pas);
  const ph = k === 0 ? 0 : e.phase;
  const noms = ['L', 'A', 'B', 'R'];
  dessinePlanW($('plan-depart'), e.depart, ph !== 2, noms);
  dessinePlanW($('plan-arrivee'), e.arrivee, ph !== 0, ['L', 'B', 'A', 'R']);   // dans l'état k+1, les deux trous qui tournent sont échangés : L–B–A–R
  $('plan-depart').style.borderColor = ph !== 2 ? COULEUR_DEPART : '';
  $('plan-arrivee').style.borderColor = ph !== 0 ? COULEUR_ARRIVEE : '';
  $('legende-depart').textContent = ph === 0 ? 'plan w du DÉPART (état k) : projeté sur L–A–B–R, en service' : ph === 1 ? 'plan w du DÉPART : figé à s_a, transporté par le maillage' : 'plan w du DÉPART : plus utilisé (figé à s_a)';
  $('legende-arrivee').textContent = ph === 2 ? 'plan w de l\'ARRIVÉE (état k+1) : projeté sur L–B–A–R, en service' : ph === 1 ? 'plan w de l\'ARRIVÉE : figée à s_b, ramenée en arrière par le maillage' : 'plan w de l\'ARRIVÉE : pas encore utilisé (figé à s_b)';
}

function dessine(k) {
  const image = etat.images[k];
  const ctx = toile.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, toile.width, toile.height);
  const v = etat.vue || { s: 1, tx: 0, ty: 0 };
  ctx.setTransform(ECHELLE * v.s, 0, 0, ECHELLE * v.s, ECHELLE * v.tx, ECHELLE * v.ty);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (etat.maillage && image.maillage && image.maillage.length) {   // les arêtes de la triangulation du raccord (seulement pendant le raccord), sous tout le reste
    ctx.strokeStyle = '#6fa8dc';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    const m = image.maillage;
    for (let j = 0; j + 3 < m.length; j += 4) { ctx.moveTo(m[j], m[j + 1]); ctx.lineTo(m[j + 2], m[j + 3]); }
    ctx.stroke();
  }
  if (etat.construction && image.construction) segments(ctx, image.construction, image.opacites, etat.etude && image.etude ? stylesDeConstruction(image) : null);
  image.lacets.forEach((p, i) => { ctx.strokeStyle = PALETTE[i % PALETTE.length]; ctx.lineWidth = etat.film !== 'conforme' && image.brin ? image.brin : 3.5; trace(ctx, p); });   // la triangulation et le diagramme affinent le trait quand les brins sont serrés
  if (image.fixes && image.fixes.length) disques(ctx, image.fixes, 3, '#888');   // les points fixes du diagramme de courbes
  disques(ctx, image.trous, 4, '#000');
  disques(ctx, image.clou, 4, '#000');
  if (etat.etude && image.etude && etat.construction) etiquettes(ctx, image);
  let n = 0, eph = 0;
  if (etat.tangentes || etat.points || etat.fantomes) {
    const rs = toutesRencontres(image);
    n = rs.length;
    eph = rs.filter((q) => !q.impose).length;
    if (etat.tangentes) {
      for (const r of rs.filter((q) => q.tangente)) {
        const a = [r.x - LONGUEUR_TANGENTE * r.dx, r.y - LONGUEUR_TANGENTE * r.dy], b = [r.x + LONGUEUR_TANGENTE * r.dx, r.y + LONGUEUR_TANGENTE * r.dy];
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 4.2;   // un liseré blanc : la tangente reste lisible sur les lacets voisins
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
        ctx.strokeStyle = '#111'; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      }
    }
    for (const r of rs) {
      if (r.impose ? !etat.points : !etat.fantomes) continue;
      ctx.beginPath(); ctx.arc(r.x, r.y, r.impose ? 4.5 : 5, 0, 2 * Math.PI);
      ctx.fillStyle = r.impose ? '#fff' : 'rgba(200, 200, 200, 0.55)';   // le fantôme : un disque gris clair translucide, le lacet reste visible dessous
      ctx.fill();
      ctx.strokeStyle = r.impose ? PALETTE[r.lacet % PALETTE.length] : '#a8a8a8';
      ctx.lineWidth = r.impose ? 2 : 1.6;
      ctx.stroke();
    }
  }
  $('compte-tangentes').textContent = etat.tangentes || etat.points || etat.fantomes ? `${n} rencontre${n > 1 ? 's' : ''}` + (eph ? ` (dont ${eph} fantôme${eph > 1 ? 's' : ''})` : '') : '';
}

// ---------------------------------------------------------------- le lecteur

function descriptionImage(k) {
  if (k === 0) return 'image de départ (avant la première lettre)';
  const N = imagesParLettre();
  const j = Math.min(etat.mot.length - 1, Math.floor((k - 1) / N)), m = ((k - 1) % N) + 1;
  return `lettre ${j + 1}/${etat.mot.length} (${nomLettre(etat.mot[j])}), pas ${m}/${N}` + (m === N ? ' : image clé' : '');
}

function va(k) {
  k = Math.max(0, Math.min(etat.total - 1, Math.round(k)));
  etat.k = k;
  dessine(k);
  metsAJourProjection(k);
  $('curseur').value = String(k);
  $('numero').value = String(k + 1);
  $('position').textContent = `image ${k + 1} / ${etat.total} · ${descriptionImage(k)}`;
}

function arrete() {
  etat.lecture = false;
  $('joue').innerHTML = ICONES.joue;
}

function joue() {
  if (etat.images.length < 2) return;
  if (etat.k >= etat.total - 1) va(0);
  etat.lecture = true;
  $('joue').innerHTML = ICONE_PAUSE;
  etat.derniere = performance.now();
  etat.reste = 0;
  const pas = (maintenant) => {
    if (!etat.lecture) return;
    etat.reste += (maintenant - etat.derniere) * etat.ips / 1000;
    etat.derniere = maintenant;
    const avance = Math.floor(etat.reste);
    if (avance >= 1) {
      etat.reste -= avance;
      if (etat.k + avance >= etat.total - 1) { va(etat.total - 1); arrete(); return; }
      va(etat.k + avance);
    }
    requestAnimationFrame(pas);
  };
  requestAnimationFrame(pas);
}

const pas = (d) => { arrete(); va(etat.k + d); };

function brancheCommandes() {
  for (const [id, svg] of Object.entries(ICONES)) $(id).innerHTML = svg;
  $('debut').onclick = () => { arrete(); va(0); };
  $('fin').onclick = () => { arrete(); va(etat.total - 1); };
  $('moins').onclick = () => pas(-1);
  $('plus').onclick = () => pas(1);
  $('lettre-moins').onclick = () => pas(-imagesParLettre());
  $('lettre-plus').onclick = () => pas(imagesParLettre());
  $('joue').onclick = () => (etat.lecture ? arrete() : joue());
  $('curseur').oninput = (e) => { arrete(); va(Number(e.target.value)); };
  $('numero').onchange = (e) => { arrete(); va(Number(e.target.value) - 1); };
  const redessine = () => { if (etat.images.length) dessine(etat.k); };
  $('c-construction').onchange = (e) => { etat.construction = e.target.checked; redessine(); };
  $('c-tangentes').onchange = (e) => { etat.tangentes = e.target.checked; redessine(); };
  $('c-points').onchange = (e) => { etat.points = e.target.checked; redessine(); };
  $('c-maillage').onchange = (e) => { etat.maillage = e.target.checked; redessine(); };
  $('c-etude').onchange = (e) => { etat.etude = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // le journal et les plans w : recalcule le film
  $('c-sans-maillage').onchange = (e) => { etat.sansMaillage = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // essai : les arcs ne sont plus retenus par les arêtes du maillage
  $('c-satellites').onchange = (e) => { etat.satellites = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // essai : 8 sommets de plus autour de chacun des deux trous qui tournent
  $('film').onchange = (e) => { etat.film = e.target.value; etat.reprise = null; if (etat.precalcule) { $('c-' + etat.precalcule).checked = false; etat.precalcule = null; } metsAJourOptions(); lance(etat.mot); };   // lacets conformes ou triangulation
  $('c-detendu').onchange = (e) => { etat.detendu = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // la détente du raccord (Detente), calculée par la page
  $('c-libre').onchange = (e) => { etat.libre = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // recalcule le film, et revient à la même image
  PRECALCULES.forEach((sorte) => {   // les films précalculés : une seule case à la fois
    $('c-' + sorte).onchange = (e) => {
      PRECALCULES.forEach((autre) => { if (autre !== sorte) $('c-' + autre).checked = false; });
      etat.precalcule = e.target.checked ? sorte : null; etat.reprise = etat.k; lance(etat.mot);
    };
  });
  $('c-fantomes').onchange = (e) => { etat.fantomes = e.target.checked; redessine(); };
  $('vitesse').onchange = (e) => { etat.ips = Number(e.target.value); };
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input[type=text], input[type=number], select') || etat.images.length < 2) return;
    const lettre = e.shiftKey ? imagesParLettre() : 1;
    if (e.key === 'ArrowRight') { pas(lettre); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { pas(-lettre); e.preventDefault(); }
    else if (e.key === 'Home') { arrete(); va(0); e.preventDefault(); }
    else if (e.key === 'End') { arrete(); va(etat.total - 1); e.preventDefault(); }
    else if (e.key === ' ') { etat.lecture ? arrete() : joue(); e.preventDefault(); }
  });
}

// ---------------------------------------------------------------- le calcul

function efface() {
  const ctx = toile.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, toile.width, toile.height);
}

// Les films précalculés en Python, un fichier JSON par mot : regions/ (essai_regions.py exporte : le raccord par régions).
// Ils remplacent le calcul du film.
const PRECALCULES = ['regions'];
const fichierPrecalcule = (mot, sorte) => sorte + '/' + mot.join('_') + '.json';

// Les cases qui n'ont de sens que pour les lacets conformes (essais du raccord, projection, fantômes des lignes estompées, maillage
// du raccord) : grisées quand le film affiché est la triangulation ou le diagramme de courbes.
const SEULEMENT_CONFORME = ['c-maillage', 'c-sans-maillage', 'c-satellites', 'c-etude', 'c-libre', 'c-fantomes'];

function metsAJourOptions() {
  const tri = etat.film !== 'conforme';
  SEULEMENT_CONFORME.forEach((id) => {
    $(id).disabled = tri;
    $(id).closest('label').title = tri ? 'pas pour ce film (lacets conformes seulement)' : ($(id).closest('label').dataset.titre || '');
  });
  if (tri) PRECALCULES.forEach((sorte) => { $('c-' + sorte).disabled = true; });
  else verifiePrecalcules(etat.mot);
}

function verifiePrecalcules(mot) {
  if (etat.film !== 'conforme') return;   // les films précalculés sont des lacets conformes
  PRECALCULES.forEach((sorte) => {
    $('c-' + sorte).disabled = true;
    fetch(fichierPrecalcule(mot, sorte), { method: 'HEAD' }).then((r) => {
      if (r.ok && etat.mot.join(' ') === mot.join(' ')) $('c-' + sorte).disabled = false;
    }).catch(() => {});
  });
}

function termine(message) {
  etat.total = etat.images.length;
  etat.vue = calculeVue(etat.images);
  $('etat-calcul').innerHTML = message ? `<span class="attention">${message}</span>` : '';
  $('curseur').max = String(etat.total - 1);
  $('numero').max = String(etat.total);
  $('commandes').hidden = false;
  const demande = new URLSearchParams(location.search).get('image');   // ?image=N : s'ouvre sur l'image N (captures)
  va(etat.reprise !== null ? etat.reprise : demande ? Number(demande) - 1 : 0);
  etat.reprise = null;
}

function chargePrecalcule(mot, sorte) {
  return fetch(fichierPrecalcule(mot, sorte)).then((r) => { if (!r.ok) throw new Error('absent'); return r.json(); }).then((d) => {
    if (etat.mot.join(' ') !== mot.join(' ')) return true;   // le mot a changé entre-temps
    etat.images = d.images.map((im) => ({
      lacets: im.lacets.map((l) => Float32Array.from(l)), trous: Float32Array.from(im.trous), fixes: new Float32Array(0), clou: Float32Array.from(im.clou),
      ecart: 6, brin: 3.5, construction: Float32Array.from(im.construction), opacites: Float32Array.from(im.opacites), ab: im.ab, maillage: new Float32Array(0),
    }));
    const n = d.anomalies.length;
    const nom = sorte === 'regions' ? `raccord par régions (précalculé, fenêtre ${d.fenetre}, rampe ${d.rampe})` : 'film détendu pendant le raccord (précalculé)';
    termine(nom + (n ? ` : ${n} image(s) avec des anomalies (voir essai_${sorte === 'regions' ? 'regions' : 'lissage'}.py)` : ' : aucune anomalie'));
    return true;
  }).catch(() => false);
}

function lance(mot) {
  if (etat.travailleur) etat.travailleur.terminate();
  arrete();
  etat.mot = mot; etat.images = []; etat.total = 0; etat.k = 0; etat.vue = null;
  efface();
  $('commandes').hidden = true;
  $('mot-titre').textContent = mot.map(nomLettre).join(' ');
  $('film-titre').textContent = { conforme: 'Lacets conformes', triangulation: 'Triangulation', diagramme: 'Diagramme de courbes' }[etat.film];
  if (etat.precalcule) {
    const sorte = etat.precalcule;
    $('etat-calcul').innerHTML = '<span>chargement des images précalculées…</span>';
    chargePrecalcule(mot, sorte).then((ok) => { if (!ok) { etat.precalcule = null; $('c-' + sorte).checked = false; calcule(mot); } });
    return;
  }
  calcule(mot);
}

function calcule(mot) {
  $('etat-calcul').innerHTML = '<progress max="1" value="0"></progress><span>calcul…</span>';
  let w;
  // ?v= : toujours la version du disque (le banc change souvent), pas celle du cache du navigateur
  try { w = new Worker('../../web/travail.js?v=' + Date.now()); } catch (e) {
    $('etat-calcul').innerHTML = '<span class="ko">Ouvre la page par un serveur (python3 -m http.server à la racine du dépôt), pas en file://.</span>';
    return;
  }
  etat.travailleur = w;
  w.onerror = () => { $('etat-calcul').innerHTML = '<span class="ko">le calcul a échoué (web/ardoise_lib.js introuvable ? voir web/construit.sh)</span>'; };
  w.onmessage = (e) => {
    const d = e.data;
    if (d.type === 'image') {
      etat.images.push(d.image);
      etat.total = d.total;
      const barre = $('etat-calcul').querySelector('progress');
      if (barre) { barre.value = (d.k + 1) / d.total; $('etat-calcul').querySelector('span').textContent = `calcul : ${Math.round(100 * (d.k + 1) / d.total)} %`; }
      if (d.k === 0) { etat.vue = null; dessine(0); }
    } else if (d.type === 'fini') {
      if (d.erreur || etat.images.length < 2) { $('etat-calcul').innerHTML = `<span class="ko">${d.message || 'film indisponible'}</span>`; return; }
      termine(d.message);
    }
  };
  if (etat.film !== 'conforme') { w.postMessage({ mode: etat.film + (etat.detendu ? '_detendu' : ''), mot }); return; }   // triangulation, diagramme
  w.postMessage({ mode: (etat.sansMaillage ? 'conforme_sans_maillage' : etat.satellites ? 'conforme_satellites' : etat.libre ? 'conforme_libre' : etat.detendu ? 'conforme_detendu' : 'conforme') + (etat.etude ? '+etude' : ''), mot });   // libre : les arcs ne passent plus par les fantômes (voir Raccord.lignes ~sans_fantomes)
}

let motCourant = null;

function miseAJour(texte) {
  const r = lisMot(texte);
  const erreur = $('erreur');
  if (r.erreur) { erreur.textContent = r.erreur; erreur.hidden = false; return; }
  erreur.hidden = true;
  if (r.mot.length === 0) return;
  const cle = r.mot.join(' ');
  document.querySelectorAll('.exemple').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mot === cle)));
  if (cle === motCourant) return;
  motCourant = cle;
  verifiePrecalcules(r.mot);
  try { history.replaceState(null, '', '#' + encodeURIComponent(cle)); } catch (e) { /* file:// */ }
  lance(r.mot);
}

window.addEventListener('DOMContentLoaded', () => {
  $('limites').innerHTML = `Limites de ce film : <b>${MAX_BRINS} brins</b> et <b>${MAX_LETTRES} lettres</b>.`;
  const champ = $('mot');
  EXEMPLES.forEach((e) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'exemple'; b.dataset.mot = e.mot.join(' '); b.title = e.mot.join(' ');
    b.innerHTML = `<span class="nom">${e.nom}</span><span class="legende">${e.legende}</span>`;
    b.onclick = () => { champ.value = e.mot.join(' '); miseAJour(champ.value); };
    $('exemples').appendChild(b);
  });
  if (new URLSearchParams(location.search).has('maillage')) { etat.maillage = true; $('c-maillage').checked = true; }   // ?maillage : arêtes du maillage au départ (captures)
  if (new URLSearchParams(location.search).has('sansmaillage')) { etat.sansMaillage = true; $('c-sans-maillage').checked = true; }   // ?sansmaillage (captures)
  if (new URLSearchParams(location.search).has('satellites')) { etat.satellites = true; $('c-satellites').checked = true; }   // ?satellites (captures)
  if (new URLSearchParams(location.search).has('sansprojection')) { etat.etude = false; $('c-etude').checked = false; }   // ?sansprojection (captures)
  if (new URLSearchParams(location.search).has('libre')) { etat.libre = true; $('c-libre').checked = true; }   // ?libre : les arcs libres au départ (captures)
  PRECALCULES.forEach((sorte) => { if (new URLSearchParams(location.search).has(sorte)) { etat.precalcule = sorte; $('c-' + sorte).checked = true; } });   // ?regions : un film précalculé au départ (captures)
  ['triangulation', 'diagramme'].forEach((f) => { if (new URLSearchParams(location.search).has(f)) { etat.film = f; $('film').value = f; } });   // ?triangulation, ?diagramme (captures)
  if (new URLSearchParams(location.search).has('nondetendu')) { etat.detendu = false; $('c-detendu').checked = false; }   // ?nondetendu : le film à maillage seul (captures)
  SEULEMENT_CONFORME.forEach((id) => { const l = $(id).closest('label'); l.dataset.titre = l.title || ''; });   // le titre d'origine, rendu quand on revient aux lacets conformes
  metsAJourOptions();
  brancheCommandes();
  let minuterie = null;
  champ.addEventListener('input', () => { clearTimeout(minuterie); minuterie = setTimeout(() => miseAJour(champ.value), 400); });
  const depart = decodeURIComponent(location.hash.slice(1)) || EXEMPLES[0].mot.join(' ');
  champ.value = depart;
  miseAJour(depart);
});
