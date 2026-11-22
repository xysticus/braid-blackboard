// Le Web Worker : charge la bibliothèque OCaml compilée (ardoise_lib.js, voir construit.sh), calcule l'image fixe
// puis le film d'un mode, et envoie les images au fil de l'eau. Un worker par mode ; la page le tue (terminate)
// quand le mot change.
//
// Le film conforme (modes conforme et conforme_detendu) est réparti sur des workers auxiliaires : voir filmReparti.
// Une éventuelle requête (?v=… : le banc d'essai l'ajoute pour échapper au cache du navigateur) est transmise à la bibliothèque
// et aux workers auxiliaires, pour qu'ils soient de la même version que ce fichier.
const VERSION = self.location.search || '';
importScripts('ardoise_lib.js' + VERSION);

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

// Le film conforme (détendu ou non, avec ou sans « +etude ») est réparti sur des workers auxiliaires (ce même fichier) :
// - par lettres : chaque lettre ne dépend que de son état de départ ; les lettres sont données une à une aux auxiliaires
//   à mesure qu'ils se libèrent (message « lettre ») ;
// - pour le film détendu, les lettres sont calculées sans détente, et chaque image du raccord revient brute (en nombres
//   double précision) ; sa détente (Detente, la partie longue) est confiée à son tour à un auxiliaire (message « detend »).
// Ce worker calcule l'image clé de départ et rend les images à la page dans l'ordre.
function filmReparti(mode, mot) {
  const detendu = mode.startsWith('conforme_detendu');
  const base = mode.replace('conforme_detendu', 'conforme');
  const fixe = self.ardoise.statique(mode, mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const pretes = [], brutes = new Map();
  let suivante = 0, total = 0, douteuses = 0, croisements = 0, erreur = null, enCours = 0, aDetendre = 0, prochaine = 0;
  const aFaire = mot.map((_, k) => k);
  const aides = [];
  const termine = () => {
    aides.forEach((w) => w.terminate());
    if (erreur) { postMessage({ type: 'fini', message: erreur, erreur: true }); return; }
    const parties = [];
    if (douteuses) parties.push(`film fait, mais ${douteuses} image(s) douteuse(s) (mots ou croisements)`);
    if (croisements) parties.push(`${croisements} croisement(s) après la détente`);
    postMessage({ type: 'fini', message: parties.join(' ; '), erreur: false });
  };
  const rend = () => {
    while (pretes[suivante] !== undefined) {
      const f = pretes[suivante];
      pretes[suivante] = undefined;
      postMessage({ type: 'image', image: f, k: suivante, total }, tampons(f));
      suivante++;
    }
    if (enCours === 0 && aDetendre === 0 && aFaire.length === 0 && (erreur || suivante === total)) termine();
  };
  const donneLettre = (w) => {
    if (erreur || aFaire.length === 0) return;
    w.postMessage({ type: 'lettre', mode: base, mot, k: aFaire.shift(), brutes: detendu });
    enCours++;
  };
  // l'image clé de départ, ici
  const r0 = self.ardoise.film_lettres(base, mot, [], true, (im, k, t) => { total = t; pretes[k] = enFloat32(im); });
  if (r0.erreur) { postMessage({ type: 'fini', message: r0.erreur, erreur: true }); return; }
  rend();
  const nb = Math.max(1, Math.min(8, self.navigator.hardwareConcurrency || 2));
  for (let i = 0; i < nb; i++) {
    const w = new Worker('travail.js' + VERSION);
    w.onmessage = (ev) => {
      const d = ev.data;
      if (d.type === 'image') { pretes[d.k] = d.image; rend(); return; }
      if (d.type === 'brute') {   // une image du raccord à détendre : au prochain auxiliaire, à tour de rôle
        brutes.set(d.k, d.image);
        aDetendre++;
        aides[prochaine++ % nb].postMessage({ type: 'detend', k: d.k, lacets: d.image.lacets, trous: d.image.trous, clou: d.image.clou, force: forceDetente(d.k), ecart: 0 });
        return;
      }
      if (d.type === 'detendue') {
        const im = brutes.get(d.k);
        brutes.delete(d.k);
        if (d.erreur) erreur = d.erreur; else { im.lacets = d.lacets; croisements += d.croisements; }
        aDetendre--;
        pretes[d.k] = enFloat32(im);
        rend();
        return;
      }
      // une lettre finie : son bilan, puis la suivante
      enCours--;
      if (d.erreur) { erreur = d.erreur; aFaire.length = 0; }
      douteuses += d.douteuses || 0;
      donneLettre(w);
      rend();
    };
    aides.push(w);
  }
  aides.forEach(donneLettre);
}

// Le film de la triangulation détendu (mode triangulation_detendu, banc d'essai) : chaque image se calcule à partir de la
// précédente, on ne peut donc pas répartir les lettres ; ce worker calcule le film, et la détente de chaque image (intensité
// constante 1, écart des brins du film) est confiée à tour de rôle à des workers auxiliaires. Images rendues dans l'ordre.
function triangulationDetendue(mot) {
  const fixe = self.ardoise.statique('triangulation', mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const nb = Math.max(1, Math.min(8, (self.navigator.hardwareConcurrency || 2) - 1));
  const aides = [], enAttente = new Map(), pretes = [];
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
  for (let i = 0; i < nb; i++) {
    const w = new Worker('travail.js' + VERSION);
    w.onmessage = (ev) => {
      const r = ev.data;
      const im = enAttente.get(r.k);
      enAttente.delete(r.k);
      if (!r.erreur) { im.lacets = r.lacets; croisements += r.croisements; }
      revenues++;
      pretes[r.k] = enFloat32(im);
      rend();
    };
    aides.push(w);
  }
  const message = self.ardoise.film('triangulation', mot, (im, k, t) => {
    total = t;
    enAttente.set(k, im);
    aides[envoyees % nb].postMessage({ type: 'detend', k, lacets: im.lacets, trous: im.trous, clou: im.clou, force: 1, ecart: im.ecart || 0 });
    envoyees++;
  });
  messageFilm = message || '';
  rend();
}

onmessage = (e) => {
  const d = e.data;
  if (d.type === 'lettre') {   // un worker auxiliaire : une lettre du film conforme
    const r = self.ardoise.film_lettres(d.mode, d.mot, [d.k], false, (im, k) => {
      if (d.brutes && forceDetente(k) > 0) { postMessage({ type: 'brute', image: im, k }); return; }   // à détendre : en double précision
      const f = enFloat32(im);
      postMessage({ type: 'image', image: f, k }, tampons(f));
    });
    postMessage({ type: 'lettre', k: d.k, douteuses: r.douteuses || 0, erreur: r.erreur });
    return;
  }
  if (d.type === 'detend') {   // un worker auxiliaire : la détente d'une image
    const r = self.ardoise.detend(d.lacets, d.trous, d.clou, d.force, d.ecart || 0);
    postMessage({ type: 'detendue', k: d.k, lacets: r.lacets, croisements: r.croisements || 0, erreur: r.erreur });
    return;
  }
  const { mode, mot } = d;
  if (/^conforme(_detendu)?(\+etude)?$/.test(mode) && typeof Worker !== 'undefined') { filmReparti(mode, mot); return; }
  if (mode === 'triangulation_detendu' && typeof Worker !== 'undefined') { triangulationDetendue(mot); return; }
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
