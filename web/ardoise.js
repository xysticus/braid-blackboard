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
  { nom: 'σ₄σ₃σ₁⁻²σ₂σ₄⁻¹σ₁', mot: [4, 3, -1, -1, 2, -4, 1], legende: 'la tresse de référence des films' },
  { nom: 'σ₁σ₂⁻¹σ₁σ₂⁻¹σ₁σ₂⁻¹σ₃σ₁⁻¹σ₂', mot: [1, -2, 1, -2, 1, -2, 3, -1, 2], legende: 'la tresse chargée des films' },
];

const MAX_BRINS = 8;     // les limites de la page (les mêmes que dans ocaml/web/ardoise_web.ml)
const MAX_LETTRES = 40;

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
    lignes.push(`<div class="fn-ligne${identite ? ' identite' : ''}">${xMath(j + 1, 1)}<span class="fleche">↦</span>` +
      `<span class="mot">${motFnMath(entiers)}</span></div>`);
  });
  zone.innerHTML = lignes.join('');
}

// ---------------------------------------------------------------- le diagramme de tresse classique

// Les générateurs de haut en bas, un brin par couleur qui suit son brin d'un croisement à l'autre ; au croisement
// σ_k positif le brin qui va de droite à gauche passe dessus (comme dans les notebooks, ipynbks/CanvasTresse*.ipynb).
const COULEURS_BRINS = ['#2e9e44', '#e6b800', '#ee6fa8', '#d62728', '#1f5fd6', '#f28e2b', '#7a4fc4', '#1aa6a6'];

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
  const couleurs = Array.from({ length: brins }, (_, i) => COULEURS_BRINS[i % COULEURS_BRINS.length]);

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

const COULEURS_CONFORME = ['#ff0000', '#00b300', '#0000ff', '#b3b300', '#b300b3', '#00b3b3'];
const COULEURS_ARCS = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6', '#0d9aa6'];

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

function dessineImage(canvas, image, mode) {
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  image.lacets.forEach((p, i) => {
    if (mode === 'conforme') {
      ctx.strokeStyle = COULEURS_CONFORME[i % COULEURS_CONFORME.length];
      ctx.lineWidth = 3.5;
      trace(ctx, p);
    } else if (mode === 'diagramme') {
      ctx.strokeStyle = '#fff';           // liseré blanc : les brins voisins restent lisibles
      ctx.lineWidth = 0.85 * image.ecart;
      trace(ctx, p);
      ctx.strokeStyle = COULEURS_ARCS[i % COULEURS_ARCS.length];
      ctx.lineWidth = 2.2;
      trace(ctx, p);
    } else {
      ctx.strokeStyle = COULEURS_ARCS[i % COULEURS_ARCS.length];
      ctx.lineWidth = 2.5;
      trace(ctx, p);
    }
  });
  if (mode === 'conforme') {
    disques(ctx, image.trous, 4, '#000');
    disques(ctx, image.clou, 4, '#000');
  } else {
    disques(ctx, image.fixes, 4, '#8c8c8c');
    disques(ctx, image.trous, 4, '#000');
  }
}

// ---------------------------------------------------------------- un lecteur : image fixe, puis film

const IMAGES_PAR_SECONDE = 25;
const PAUSE_DEBUT = 12;   // en images, comme les films MP4 : 0,5 s au début, 1,5 s à la fin
const PAUSE_FIN = 38;

class Lecteur {
  constructor(parent, mode, titre) {
    this.mode = mode;
    const panneau = document.createElement('div');
    panneau.className = 'panneau';
    panneau.innerHTML = `<h3>${titre}</h3><canvas width="800" height="800"></canvas><div class="etat"></div>`;
    parent.appendChild(panneau);
    this.canvas = panneau.querySelector('canvas');
    this.etat = panneau.querySelector('.etat');
    this.images = [];
    this.fixe = null;
    this.lecture = false;
    this.t = 0;
    this.derniere = 0;
    this.efface();
  }

  efface() {
    const ctx = this.canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  // Un nouveau mot : on repart de zéro.
  recommence() {
    this.arrete();
    this.images = [];
    this.fixe = null;
    this.t = 0;
    this.efface();
    this.etat.innerHTML = '<progress max="1" value="0"></progress><span>calcul…</span>';
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
    dessineImage(this.canvas, image, this.mode);
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
    this.prepareLecteur(message);
    this.joue();
  }

  prepareLecteur(message) {
    const duree = this.duree();
    this.etat.innerHTML = `<button type="button" title="lecture / pause">⏸</button>` +
      `<input type="range" min="0" max="${duree - 1}" step="1" value="0" aria-label="position dans le film">` +
      (message ? `<span class="ko" title="${message}">⚠</span>` : '<span class="ok">film</span>');
    this.bouton = this.etat.querySelector('button');
    this.curseur = this.etat.querySelector('input');
    this.bouton.onclick = () => (this.lecture ? this.arrete() : this.joue());
    this.curseur.oninput = () => { this.arrete(); this.t = Number(this.curseur.value); this.montre(); };
  }

  duree() { return PAUSE_DEBUT + (this.images.length - 1) + PAUSE_FIN; }

  montre() {
    const n = this.images.length;
    const k = this.t < PAUSE_DEBUT ? 0 : Math.min(n - 1, Math.floor(this.t - PAUSE_DEBUT));
    dessineImage(this.canvas, this.images[k], this.mode);
    if (this.curseur) this.curseur.value = String(Math.floor(this.t));
  }

  joue() {
    if (this.images.length < 2) return;
    this.lecture = true;
    if (this.bouton) this.bouton.textContent = '⏸';
    this.derniere = performance.now();
    const pas = (maintenant) => {
      if (!this.lecture) return;
      this.t += (maintenant - this.derniere) * IMAGES_PAR_SECONDE / 1000;
      this.derniere = maintenant;
      if (this.t >= this.duree()) this.t = 0;
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

// ---------------------------------------------------------------- la page

const MODES = [
  { id: 'diagramme', titre: 'Diagramme de courbes' },
  { id: 'conforme', titre: 'Représentation conforme' },
  { id: 'rubans', titre: 'Rubans' },
];

let lecteurs = [];
let travailleurs = [];
let ardoisePrincipale = null;   // la bibliothèque dans le fil principal : pour l'action sur F_n (instantanée)

function arreteTravailleurs() {
  travailleurs.forEach((w) => w.terminate());
  travailleurs = [];
}

function lanceCalculs(mot) {
  arreteTravailleurs();
  lecteurs.forEach((l) => l.recommence());
  MODES.forEach((m, j) => {
    let w;
    try {
      w = new Worker('travail.js');
    } catch (e) {
      lecteurs[j].vide('Ouvre la page par un serveur (python -m http.server dans web/), pas en file://.');
      return;
    }
    travailleurs.push(w);
    w.onerror = () => lecteurs[j].vide('le calcul a échoué (ardoise_lib.js introuvable ? voir construit.sh)');
    w.onmessage = (e) => {
      const d = e.data;
      if (d.type === 'statique') lecteurs[j].recoitFixe(d.image);
      else if (d.type === 'image') lecteurs[j].recoitImage(d.image, d.k, d.total);
      else if (d.type === 'fini') lecteurs[j].fini(d.message, d.erreur);
    };
    w.postMessage({ mode: m.id, mot });
  });
}

let motCourant = null;

function mise_a_jour(texte, { immediat } = {}) {
  const r = lisMot(texte);
  const erreur = document.getElementById('erreur');
  if (r.erreur) {
    erreur.textContent = r.erreur;
    erreur.hidden = false;
    return;
  }
  erreur.hidden = true;
  const mot = r.mot;
  const cle = mot.join(' ');
  document.querySelectorAll('.exemple').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mot === cle)));
  if (cle === motCourant) return;
  motCourant = cle;
  try { history.replaceState(null, '', mot.length ? '#' + encodeURIComponent(cle) : location.pathname); } catch (e) { /* file:// */ }
  afficheMot(mot);
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

async function demarre() {
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
  lecteurs = MODES.map((m) => new Lecteur(panneaux, m.id, m.titre));
  const champ = document.getElementById('mot');
  try {
    ardoisePrincipale = await chargeBibliotheque();
  } catch (e) {
    const erreur = document.getElementById('erreur');
    erreur.textContent = e.message;
    erreur.hidden = false;
    return;
  }
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
