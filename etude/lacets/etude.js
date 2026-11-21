'use strict';
// Le banc d'essai du film des lacets (mode « conforme » de la page publique) : le même calcul (web/travail.js, qui charge
// web/ardoise_lib.js), un seul film, un canvas de 1600 × 1600 (les images sont calculées dans 800 × 800 : échelle 2), un lecteur
// pas à pas, les lignes de construction et les tangentes des arcs aux points où ils les rencontrent.
// Rien ici n'est déployé : la page publique est dans web/.

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

const MAX_BRINS = 6;      // les limites du film conforme (web/ardoise.js)
const MAX_LETTRES = 14;
const IMAGES_PAR_LETTRE = 48;   // nombre_images_conforme de ocaml/web/ardoise_web.ml
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
  construction: true, tangentes: true, points: true, fantomes: true, libre: false, sansMaillage: false, maillage: false, reprise: null, ips: 25, vue: null,
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

function segments(ctx, s, opacites) {
  const alpha = ctx.globalAlpha;
  ctx.strokeStyle = '#999';
  ctx.lineWidth = 2.2;
  for (let j = 0; 4 * j + 3 < s.length; j++) {
    ctx.globalAlpha = alpha * (opacites ? opacites[j] : 1);
    ctx.beginPath(); ctx.moveTo(s[4 * j], s[4 * j + 1]); ctx.lineTo(s[4 * j + 2], s[4 * j + 3]); ctx.stroke();
  }
  ctx.globalAlpha = alpha;
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
  if (etat.construction && image.construction) segments(ctx, image.construction, image.opacites);
  image.lacets.forEach((p, i) => { ctx.strokeStyle = PALETTE[i % PALETTE.length]; ctx.lineWidth = 3.5; trace(ctx, p); });
  disques(ctx, image.trous, 4, '#000');
  disques(ctx, image.clou, 4, '#000');
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
  const j = Math.floor((k - 1) / IMAGES_PAR_LETTRE), m = ((k - 1) % IMAGES_PAR_LETTRE) + 1;
  return `lettre ${j + 1}/${etat.mot.length} (${nomLettre(etat.mot[j])}), pas ${m}/${IMAGES_PAR_LETTRE}` + (m === IMAGES_PAR_LETTRE ? ' : image clé' : '');
}

function va(k) {
  k = Math.max(0, Math.min(etat.total - 1, Math.round(k)));
  etat.k = k;
  dessine(k);
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
  $('lettre-moins').onclick = () => pas(-IMAGES_PAR_LETTRE);
  $('lettre-plus').onclick = () => pas(IMAGES_PAR_LETTRE);
  $('joue').onclick = () => (etat.lecture ? arrete() : joue());
  $('curseur').oninput = (e) => { arrete(); va(Number(e.target.value)); };
  $('numero').onchange = (e) => { arrete(); va(Number(e.target.value) - 1); };
  const redessine = () => { if (etat.images.length) dessine(etat.k); };
  $('c-construction').onchange = (e) => { etat.construction = e.target.checked; redessine(); };
  $('c-tangentes').onchange = (e) => { etat.tangentes = e.target.checked; redessine(); };
  $('c-points').onchange = (e) => { etat.points = e.target.checked; redessine(); };
  $('c-maillage').onchange = (e) => { etat.maillage = e.target.checked; redessine(); };
  $('c-sans-maillage').onchange = (e) => { etat.sansMaillage = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // essai : les arcs ne sont plus retenus par les arêtes du maillage
  $('c-libre').onchange = (e) => { etat.libre = e.target.checked; etat.reprise = etat.k; lance(etat.mot); };   // recalcule le film, et revient à la même image
  $('c-fantomes').onchange = (e) => { etat.fantomes = e.target.checked; redessine(); };
  $('vitesse').onchange = (e) => { etat.ips = Number(e.target.value); };
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input[type=text], input[type=number], select') || etat.images.length < 2) return;
    const lettre = e.shiftKey ? IMAGES_PAR_LETTRE : 1;
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

function lance(mot) {
  if (etat.travailleur) etat.travailleur.terminate();
  arrete();
  etat.mot = mot; etat.images = []; etat.total = 0; etat.k = 0; etat.vue = null;
  efface();
  $('commandes').hidden = true;
  $('mot-titre').textContent = mot.map(nomLettre).join(' ');
  $('etat-calcul').innerHTML = '<progress max="1" value="0"></progress><span>calcul…</span>';
  let w;
  try { w = new Worker('../../web/travail.js'); } catch (e) {
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
      etat.total = etat.images.length;
      etat.vue = calculeVue(etat.images);
      $('etat-calcul').innerHTML = d.message ? `<span class="attention">${d.message}</span>` : '';
      $('curseur').max = String(etat.total - 1);
      $('numero').max = String(etat.total);
      $('commandes').hidden = false;
      const demande = new URLSearchParams(location.search).get('image');   // ?image=N : s'ouvre sur l'image N (captures)
      va(etat.reprise !== null ? etat.reprise : demande ? Number(demande) - 1 : 0);
      etat.reprise = null;
    }
  };
  w.postMessage({ mode: etat.sansMaillage ? 'conforme_sans_maillage' : etat.libre ? 'conforme_libre' : 'conforme', mot });   // libre : les arcs ne passent plus par les fantômes (voir Raccord.lignes ~sans_fantomes)
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
  if (new URLSearchParams(location.search).has('libre')) { etat.libre = true; $('c-libre').checked = true; }   // ?libre : les arcs libres au départ (captures)
  brancheCommandes();
  let minuterie = null;
  champ.addEventListener('input', () => { clearTimeout(minuterie); minuterie = setTimeout(() => miseAJour(champ.value), 400); });
  const depart = decodeURIComponent(location.hash.slice(1)) || EXEMPLES[7].mot.join(' ');
  champ.value = depart;
  miseAJour(depart);
});
