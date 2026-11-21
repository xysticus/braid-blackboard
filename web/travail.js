// Le Web Worker : charge la bibliothèque OCaml compilée (ardoise_lib.js, voir construit.sh), calcule l'image fixe
// puis le film d'un mode, et envoie les images au fil de l'eau. Un worker par mode ; la page le tue (terminate)
// quand le mot change.
//
// Le film détendu (mode conforme_detendu, éventuellement +etude) est réparti : ce worker calcule le film conforme, et la
// détente des images du raccord (la partie longue) est confiée à des workers auxiliaires (ce même fichier, message
// « detend »), un par cœur disponible. Les images sont rendues à la page dans l'ordre.
importScripts('ardoise_lib.js');

// Un champ qui est un tableau de nombres devient un Float32Array, un tableau de tableaux (les lacets) un tableau de
// Float32Array ; les nombres restent des nombres.
function enFloat32(image) {
  const r = {};
  for (const [nom, v] of Object.entries(image)) {
    if (Array.isArray(v) && v.length > 0 && Array.isArray(v[0])) r[nom] = v.map((l) => Float32Array.from(l));
    else if (Array.isArray(v)) r[nom] = Float32Array.from(v);
    else r[nom] = v;
  }
  return r;
}

function tampons(image) {
  const t = [];
  for (const v of Object.values(image)) {
    if (v instanceof Float32Array) t.push(v.buffer);
    else if (Array.isArray(v)) v.forEach((l) => t.push(l.buffer));
  }
  return t;
}

// L'intensité de la détente à l'image k du film (k = 0 : l'image clé de départ), comme Film_conforme.film ~detente : 4 poids
// (1 − poids), le poids étant celui du raccord (48 images par lettre, nombre_images_conforme ; fenêtre 0,5).
const IMAGES_PAR_LETTRE = 48;
const lisse = (u) => u * u * (3 - 2 * u);
function forceDetente(k) {
  if (k === 0) return 0;
  const n = (k - 1) % IMAGES_PAR_LETTRE + 1;
  const s = lisse(n / IMAGES_PAR_LETTRE);
  const poids = lisse(Math.min(1, Math.max(0, (s - 0.25) / 0.5)));
  return poids > 0 && poids < 1 ? 4 * poids * (1 - poids) : 0;
}

function filmDetenduReparti(mode, mot) {
  const base = mode.replace('conforme_detendu', 'conforme');
  const fixe = self.ardoise.statique(base, mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const nb = Math.max(1, Math.min(8, (self.navigator.hardwareConcurrency || 2) - 1));
  const aides = [];
  const enAttente = new Map();      // k → l'image conforme, en attendant ses lacets détendus
  const pretes = [];                // k → l'image à rendre
  let suivante = 0, total = 0, envoyees = 0, revenues = 0, croisements = 0, messageFilm = null;
  const rend = () => {
    while (pretes[suivante] !== undefined) {
      const f = pretes[suivante];
      pretes[suivante] = undefined;
      postMessage({ type: 'image', image: f, k: suivante, total }, tampons(f));
      suivante++;
    }
    if (messageFilm !== null && revenues === envoyees && suivante === total) {
      aides.forEach((w) => w.terminate());
      let message = messageFilm;
      if (croisements) message = (message ? message + ' ; ' : '') + `${croisements} croisement(s) après la détente`;
      postMessage({ type: 'fini', message, erreur: false });
    }
  };
  const recoit = (ev) => {
    const r = ev.data;
    const im = enAttente.get(r.k);
    enAttente.delete(r.k);
    if (!r.erreur) { im.lacets = r.lacets; croisements += r.croisements; }
    revenues++;
    pretes[r.k] = enFloat32(im);
    rend();
  };
  for (let i = 0; i < nb; i++) { const w = new Worker('travail.js'); w.onmessage = recoit; aides.push(w); }
  // le film conforme ; ses images à détendre partent aux auxiliaires (qui travaillent pendant que le film se calcule)
  const message = self.ardoise.film(base, mot, (im, k, t) => {
    total = t;
    const force = forceDetente(k);
    if (force > 0) {
      enAttente.set(k, im);
      aides[envoyees % nb].postMessage({ type: 'detend', k, lacets: im.lacets, trous: im.trous, clou: im.clou, force });
      envoyees++;
    } else {
      pretes[k] = enFloat32(im);
      rend();
    }
  });
  messageFilm = message || '';
  rend();
}

onmessage = (e) => {
  const d = e.data;
  if (d.type === 'detend') {   // un worker auxiliaire : la détente d'une image
    const r = self.ardoise.detend(d.lacets, d.trous, d.clou, d.force);
    postMessage({ k: d.k, lacets: r.lacets, croisements: r.croisements || 0, erreur: r.erreur });
    return;
  }
  const { mode, mot } = d;
  if (/^conforme_detendu(\+etude)?$/.test(mode) && typeof Worker !== 'undefined') { filmDetenduReparti(mode, mot); return; }
  const fixe = self.ardoise.statique(mode, mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const message = self.ardoise.film(mode, mot, (im, k, total) => {
    const f = enFloat32(im);
    postMessage({ type: 'image', image: f, k, total }, tampons(f));
  });
  postMessage({ type: 'fini', message, erreur: false });
};
