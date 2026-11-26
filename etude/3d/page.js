'use strict';
// Le banc d'essai de la vue 3D : la page (saisie, exemples, mot dont chaque lettre répond à son croisement). La vue elle-même
// est dans vue3d.js, sans lien avec la page. Rien ici n'est déployé : la page publique est dans web/.

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

const MAX_BRINS = 8;      // les limites de la page publique (web/ardoise.js) ; la 3D ne calcule rien de coûteux
const MAX_LETTRES = 40;
const PALETTE = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6', '#0d9aa6', '#e6761a', '#6b4fbb'];

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

// ---------------------------------------------------------------- le mot et les croisements, liés dans les deux sens

let vue = null, motCourant = null;

function met_en_evidence(j) {
  vue.designe(j);
  [...$('mot-lettres').children].forEach((b, i) => b.classList.toggle('designee', i === j));
}

function afficheLettres(mot) {
  const zone = $('mot-lettres');
  zone.textContent = '';
  mot.forEach((k, j) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = nomLettre(k); b.title = `lettre ${j + 1} : sa tranche, comptée depuis le haut`;
    b.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') met_en_evidence(j); });
    b.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') met_en_evidence(null); });
    b.addEventListener('focus', () => met_en_evidence(j));
    b.addEventListener('click', () => met_en_evidence(j));
    zone.appendChild(b);
  });
}

function miseAJour(texte) {
  const r = lisMot(texte);
  const erreur = $('erreur');
  if (r.erreur) { erreur.textContent = r.erreur; erreur.hidden = false; return; }
  erreur.hidden = true;
  if (r.mot.length === 0) return;
  const cle = r.mot.join(' ');
  document.querySelectorAll('.exemple').forEach((b) => b.classList.toggle('choisie', b.dataset.mot === cle));
  if (cle === motCourant) return;
  motCourant = cle;
  try { history.replaceState(null, '', '#' + encodeURIComponent(cle)); } catch (e) { /* file:// */ }
  afficheLettres(r.mot);
  vue.montre(r.mot, PALETTE);
}

// Le fond et les teintes du verre suivent le thème de la page.
function appliqueTheme() {
  const style = getComputedStyle(document.documentElement);
  const lit = (nom) => style.getPropertyValue(nom).trim();
  vue.teinte({ fond: lit('--carte'), verre: lit('--doux'), accent: lit('--accent') });
}

window.addEventListener('DOMContentLoaded', () => {
  vue = Vue3D.cree($('toile'), { survol: met_en_evidence });
  if (!vue) { $('sans-webgl').hidden = false; $('toile').hidden = true; return; }
  appliqueTheme();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', appliqueTheme);
  const champ = $('mot');
  EXEMPLES.forEach((e) => {
    const d = document.createElement('div');
    d.className = 'exemple'; d.dataset.mot = e.mot.join(' ');
    d.innerHTML = `<button type="button" class="principal" title="${e.mot.join(' ')}"><span class="nom">${e.nom}</span><span class="legende">${e.legende}</span></button>`;
    d.firstChild.onclick = () => { champ.value = d.dataset.mot; miseAJour(champ.value); };
    $('exemples').appendChild(d);
  });
  let minuterie = null;
  champ.addEventListener('input', () => { clearTimeout(minuterie); minuterie = setTimeout(() => miseAJour(champ.value), 400); });
  const depart = decodeURIComponent(location.hash.slice(1)) || '1 -2 1 -2';
  champ.value = depart;
  miseAJour(depart);
  // ?azimut=…&site=…&zoom=…&lettre=… (en degrés, la lettre comptée à partir de 1) : un point de vue fixé, pour les captures
  const q = new URLSearchParams(location.search);
  if (q.has('azimut') || q.has('site') || q.has('zoom'))
    vue.oriente(Number(q.get('azimut') || 0) * Math.PI / 180, Number(q.get('site') || 0) * Math.PI / 180, Number(q.get('zoom') || 1));
  if (q.has('lettre')) met_en_evidence(Number(q.get('lettre')) - 1);
});
