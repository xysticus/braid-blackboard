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

// Un film détendu sur toutes ses images (modes triangulation_detendu : la vue 3 de la page et le banc ; diagramme_detendu : le banc) :
// chaque image du film de base se calcule à partir de la précédente, on ne peut donc pas répartir les lettres ; ce worker calcule
// le film, et la détente de chaque image (intensité constante 1, écart des brins du film ; obstacles : les trous et les points
// fixes des films d'arcs) est confiée à tour de rôle à des workers auxiliaires. Images rendues dans l'ordre.
const obstacles = (im) => Array.from(im.trous).concat(Array.from(im.fixes || []));

// L'image fixe d'un mode (l'image d'arrivée) ; pour les films détendus sur toutes leurs images, l'image fixe l'est aussi.
function imageFixe(mode, mot) {
  if (mode === 'triangulation_envers') mode = 'triangulation';   // l'image fixe du film à l'envers est le méandre complet, non détendu
  const detendu = /^(triangulation|diagramme)_detendu$/.test(mode);
  const fixe = self.ardoise.statique(detendu ? mode.replace('_detendu', '') : mode, mot);
  if (!fixe.erreur && detendu) {
    const fd = self.ardoise.detend(fixe.lacets, obstacles(fixe), fixe.clou, 1, fixe.ecart || 0);
    if (!fd.erreur) fixe.lacets = fd.lacets;
  }
  return fixe;
}

function filmDetenduParImages(base, mot) {
  const fixe = imageFixe(base + '_detendu', mot);
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
  const message = self.ardoise.film(base, mot, (im, k, t) => {
    total = t;
    enAttente.set(k, im);
    aides[envoyees % nb].postMessage({ type: 'detend', k, lacets: im.lacets, trous: obstacles(im), clou: im.clou, force: 1, ecart: im.ecart || 0 });
    envoyees++;
  });
  messageFilm = message || '';
  rend();
}

// Le film « pur détendu » du banc d'essai (conforme_pur_detendu) : le film pur (sans détente) se calcule ici, et la détente de la
// transformation de chaque image (lacets_morph ; intensité 4 s (1 − s), s étant le temps de la lettre) est confiée à tour de rôle à des
// workers auxiliaires, comme pour la triangulation. Images rendues dans l'ordre.
function filmPurDetenduParImages(mot) {
  const fixe = self.ardoise.statique('conforme_pur', mot);
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
      postMessage({ type: 'fini', message: messageFilm, erreur: false });
    }
  };
  for (let i = 0; i < nb; i++) {
    const w = new Worker('travail.js' + VERSION);
    w.onmessage = (ev) => {
      const r = ev.data;
      const im = enAttente.get(r.k);
      enAttente.delete(r.k);
      if (!r.erreur) im.lacets_morph = r.lacets;
      revenues++;
      pretes[r.k] = enFloat32(im);
      rend();
    };
    aides.push(w);
  }
  const message = self.ardoise.film('conforme_pur', mot, (im, k, t) => {
    total = t;
    if (k === 0) { pretes[0] = enFloat32(im); suivante = 0; rend(); return; }   // l'image clé de départ : rien à détendre
    const s = lisse(((k - 1) % IMAGES_PAR_LETTRE + 1) / IMAGES_PAR_LETTRE);
    enAttente.set(k, im);
    aides[envoyees % nb].postMessage({ type: 'detend', k, lacets: im.lacets_morph, trous: Array.from(im.trous), clou: im.clou, force: 4 * s * (1 - s), ecart: 0 });
    envoyees++;
  });
  messageFilm = message || '';
  rend();
}

// Le film de la triangulation « à l'envers » (banc d'essai, mode triangulation_envers) : on part de l'image n (le méandre complet), on tire
// sur les brins pour atteindre l'image clé n − 1, et ainsi de suite jusqu'aux brins du début. OCaml calcule le film du mot suivi de son
// inverse et rend seulement la seconde moitié (le retour) ; on la joue à l'envers.
function filmEnvers(mot) {
  const fixe = self.ardoise.statique('triangulation', mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const images = [];
  let chapitres = null;
  const message = self.ardoise.film('triangulation_envers', mot, (im, k) => {
    if (k === 0) chapitres = Array.from(im.chapitres);
    images[k] = im;
  });
  if (!chapitres) { postMessage({ type: 'fini', message: message || 'film indisponible', erreur: true }); return; }
  const retour = images.slice().reverse();
  const total = retour.length, dernier = total - 1;
  retour[0].chapitres = chapitres.map((c) => dernier - c).reverse();   // les débuts de lettre, comptés depuis la fin
  retour.forEach((im, k) => {
    const f = enFloat32(im);
    postMessage({ type: 'image', image: f, k, total }, tampons(f));
  });
  postMessage({ type: 'fini', message: message || '', erreur: false });
}

// Le film « cordes sur chevilles » (banc d'essai, mode triangulation_cordes) : comme le film à l'envers, mais sans maillage pour les brins.
// On part du méandre complet ; les trous reculent comme dans le retour du film « faire et défaire » ; les lacets, des cordes, sont poussés
// par les trous (chevilles) et se rétractent le long de leur propre chemin par la tension seule (Detente, sans répulsion entre eux plus que
// d'ordinaire) : chaque image part de la précédente, d'où un calcul séquentiel. On joue le tout à l'envers.
function filmCordes(mot, portee) {   // portee : la tension n'agit qu'autour des trous (le lacet se referme derrière un trou) ; absente : partout
  const fixe = self.ardoise.statique('triangulation', mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const images = [];
  let chapitres = null;
  const message = self.ardoise.film('triangulation_envers', mot, (im, k) => {
    if (k === 0) chapitres = Array.from(im.chapitres);
    images[k] = im;
  });
  if (!chapitres) { postMessage({ type: 'fini', message: message || 'film indisponible', erreur: true }); return; }
  let lacets = images[0].lacets;
  let erreurs = 0;
  for (let k = 1; k < images.length; k++) {
    // 30 itérations par image suffisent (chaque image part de la précédente, déjà presque à l'équilibre) : 150 par défaut, cinq fois plus
    // long pour le même résultat topologique ; 20 itérations ou un pas de 6 px laissent des lacets traverser les trous
    const r = self.ardoise.detend_local(lacets, Array.from(images[k].trous), images[k].clou, 1, images[k].ecart || 0, portee || 1e12, 30, 0);
    if (r.erreur) erreurs++; else lacets = r.lacets;
    images[k].lacets = lacets;
  }
  const retour = images.slice().reverse();
  const total = retour.length, dernier = total - 1;
  retour[0].chapitres = chapitres.map((c) => dernier - c).reverse();
  retour.forEach((im, k) => {
    const f = enFloat32(im);
    postMessage({ type: 'image', image: f, k, total }, tampons(f));
  });
  postMessage({ type: 'fini', message: erreurs ? `${erreurs} image(s) sans détente` : (message || ''), erreur: false });
}

// Le film « rétractation » (banc d'essai, mode retractation) : un dessin fixe, le méandre de l'image n ; on tire en même temps sur tous les
// lacets, proportionnellement à leur longueur : chaque lacet est un ruban dont on efface le bout (à partir du trou qu'il enlace, au milieu de son
// chemin) en remontant vers le clou, et le trou recule dans le ruban en suivant ce bout. Rien d'autre ne bouge : les trous dansent là où le lacet
// les emmène, on ne retrouve pas les lettres du mot. On rend les images à l'envers : le méandre se révèle, les trous avancent dans leurs lacets.
const IMAGES_RETRACTION = 160, RESTE_RETRACTION = 0.97;   // on efface au plus 97 % de chaque lacet
function filmRetraction(mot) {
  const fixe = self.ardoise.statique('conforme', mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const mots = Array.from(self.ardoise.analyse(mot).fn).map((w) => Array.from(w));
  const T = Array.from(fixe.trous);
  const trous = [];
  for (let i = 0; i + 1 < T.length; i += 2) trous.push([T[i], T[i + 1]]);
  const parX = trous.map((t, p) => p).sort((a, b) => trous[a][0] - trous[b][0]);   // le trou j (de 1) : le j-ième de gauche à droite
  // pour chaque lacet : ses points, ses longueurs cumulées, le trou qu'il enlace (la lettre du milieu de son mot) et le point du lacet le plus proche de ce trou (le bout du ruban)
  const rubans = Array.from(fixe.lacets).map((l, i) => {
    const pts = [];
    for (let k = 0; k + 1 < l.length; k += 2) pts.push([l[k], l[k + 1]]);
    const cum = [0];
    for (let k = 1; k < pts.length; k++) cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
    const w = mots[i] || [];
    const j = w.length ? Math.abs(w[(w.length - 1) >> 1]) : i + 1;
    const p = parX[Math.min(trous.length, Math.max(1, j)) - 1];
    let bout = 0, dmin = Infinity;
    pts.forEach((q, k) => { const d = Math.hypot(q[0] - trous[p][0], q[1] - trous[p][1]); if (d < dmin) { dmin = d; bout = k; } });
    return { pts, cum, p, bout, L: cum[cum.length - 1] };
  });
  const point = (r, s) => {   // le point du lacet à l'abscisse curviligne s
    let k = 1;
    while (k < r.cum.length - 1 && r.cum[k] < s) k++;
    const u = r.cum[k] === r.cum[k - 1] ? 0 : (s - r.cum[k - 1]) / (r.cum[k] - r.cum[k - 1]);
    return [r.pts[k - 1][0] + u * (r.pts[k][0] - r.pts[k - 1][0]), r.pts[k - 1][1] + u * (r.pts[k][1] - r.pts[k - 1][1])];
  };
  const images = [];
  for (let n = 0; n < IMAGES_RETRACTION; n++) {
    const t = n / (IMAGES_RETRACTION - 1), u = RESTE_RETRACTION * t * t * (3 - 2 * t);
    const lacets = [], indices = [], nouveaux = trous.map((q) => q.slice());
    rubans.forEach((r, i) => {
      const sBout = r.cum[r.bout];
      const a = sBout * (1 - u), b = sBout + (r.L - sBout) * u;   // le bout efface de a à b
      const debut = [], fin = [];
      for (let k = 0; k < r.pts.length; k++) {
        if (r.cum[k] <= a) debut.push(r.pts[k]);
        if (r.cum[k] >= b) fin.push(r.pts[k]);
      }
      const pa = point(r, a), pb = point(r, b);
      debut.push(pa); fin.unshift(pb);
      lacets.push(debut.flat()); indices.push(i);
      lacets.push(fin.flat()); indices.push(i);
      nouveaux[r.p] = [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2];   // le trou suit le bout du ruban
    });
    images.push({ lacets, trous: nouveaux.flat(), clou: Array.from(fixe.clou), indices, brin: 3.5, ecart: 0 });
  }
  const retour = images.reverse();
  const total = retour.length, L = mot.length;
  retour[0].chapitres = Array.from({ length: L + 1 }, (_, j) => Math.round(j * (total - 1) / L));
  retour.forEach((im, k) => {
    const f = enFloat32(im);
    postMessage({ type: 'image', image: f, k, total }, tampons(f));
  });
  postMessage({ type: 'fini', message: '', erreur: false });
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
  if (d.type === 'fixe') {   // seulement l'image fixe d'un mode : la page l'affiche pendant que les autres films se calculent
    const fixe = imageFixe(d.mode, d.mot);
    if (!fixe.erreur) { const image = enFloat32(fixe); postMessage({ type: 'statique', image }, tampons(image)); }
    postMessage({ type: 'fixe-fini' });
    return;
  }
  const { mode, mot } = d;
  if (/^conforme(_detendu)?(\+etude)?$/.test(mode) && typeof Worker !== 'undefined') { filmReparti(mode, mot); return; }
  if (mode === 'triangulation_envers') { filmEnvers(mot); return; }
  if (mode === 'retractation') { filmRetraction(mot); return; }
  if (mode === 'triangulation_cordes') { filmCordes(mot); return; }
  if (mode === 'triangulation_cordes_locale') { filmCordes(mot, 100); return; }
  if (mode === 'conforme_pur_detendu' && typeof Worker !== 'undefined') { filmPurDetenduParImages(mot); return; }
  if (/^(triangulation|diagramme)_detendu$/.test(mode) && typeof Worker !== 'undefined') { filmDetenduParImages(mode.replace('_detendu', ''), mot); return; }
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
