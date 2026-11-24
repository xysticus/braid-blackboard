// Le Web Worker : charge la bibliothèque OCaml compilée (ardoise_lib.js, voir construit.sh), calcule l'image fixe
// puis le film d'un mode, et envoie les images au fil de l'eau. Un worker par mode ; la page le tue (terminate)
// quand le mot change.
//
// Le film conforme (modes conforme et conforme_detendu) est réparti sur des workers auxiliaires : voir filmReparti.
// Une éventuelle requête (?v=… : le banc d'essai l'ajoute pour échapper au cache du navigateur) est transmise à la bibliothèque
// et aux workers auxiliaires, pour qu'ils soient de la même version que ce fichier.
const VERSION = self.location.search || '';
let SANS_LIMITES = false;   // le banc d'essai lève les limites de mots pour le méandre témoin (message sansLimites) ; jamais la page publique
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
    w.postMessage({ type: 'lettre', mode: base, mot, k: aFaire.shift(), brutes: detendu, sansLimites: SANS_LIMITES });
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

// Le film « rétractation » (banc d'essai, mode retractation) : un dessin fixe, le méandre de l'image n ; on tire sur les lacets **l'un après
// l'autre** (le temps de chacun est proportionnel à sa longueur). Chaque lacet est un ruban dont on efface le bout, à partir du trou qu'il
// enlace (la lettre du milieu de son mot de F_n) en remontant vers le clou, mais seulement jusqu'à l'arrivée du lacet sur l'axe (le haut de ses
// deux descentes au clou, qui ne sont pas retirées) : les deux brins du ruban sont raccordés par un bouchon en
// demi-cercle, du côté du bout, et le trou est dans le bouchon (le lacet se referme tout de suite après le trou). Rien d'autre ne bouge :
// on ne retrouve pas les lettres du mot. On rend les images à l'envers : le méandre se révèle lacet après lacet, les trous avancent dans leurs lacets.
const IMAGES_RETRACTION = 240;
// graine : absente, les lacets se tirent dans l'ordre de leur numéro ; présente, dans un ordre tiré au hasard (mélange déterministe, rejouable avec la même graine).
function filmRetraction(mot, graine, ordreMode) {   // ordreMode : « naturel » (défaut sans graine), « entiers » (lacets entiers dans un ordre tiré) ou « morceaux » (tirages par morceaux entrelacés)
  const fixe = self.ardoise.statique('conforme', mot);
  if (fixe.erreur) { postMessage({ type: 'fini', message: fixe.erreur, erreur: true }); return; }
  const image = enFloat32(fixe);
  postMessage({ type: 'statique', image }, tampons(image));
  const mots = Array.from(self.ardoise.analyse(mot).fn).map((w) => Array.from(w));
  const T = Array.from(fixe.trous);
  const trous = [];
  for (let i = 0; i + 1 < T.length; i += 2) trous.push([T[i], T[i + 1]]);
  const parX = trous.map((t, p) => p).sort((a, b) => trous[a][0] - trous[b][0]);   // le trou j (de 1) : le j-ième de gauche à droite
  const lisse = (u) => u * u * (3 - 2 * u);
  // pour chaque lacet : ses points, le trou qu'il enlace, le bout du ruban (le point du lacet le plus proche de ce trou), et pour chaque point
  // du brin d'aller (du clou au bout) le point du brin de retour qui lui fait face (le plus proche), pour que le bouchon relie deux brins voisins
  const rubans = Array.from(fixe.lacets).map((l, i) => {
    const pts = [];
    for (let k = 0; k + 1 < l.length; k += 2) pts.push([l[k], l[k + 1]]);
    const cum = [0];
    for (let k = 1; k < pts.length; k++) cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
    const w = mots[i] || [];
    const j = w.length ? Math.abs(w[(w.length - 1) >> 1]) : i + 1;
    const p = parX[Math.min(trous.length, Math.max(1, j)) - 1];
    // les pieds du lacet sur l'axe (les trous y sont) : les groupes de points à la hauteur de l'axe ; le bout du ruban est l'arc qui passe au-dessus
    // du trou (le plus petit des arcs dont l'intervalle contient le trou), entre deux pieds consécutifs
    const yAxe = trous[0][1];
    const pieds = [];
    for (let k = 0; k < pts.length;) {
      if (Math.abs(pts[k][1] - yAxe) < 1.5) { let m = k; while (m + 1 < pts.length && Math.abs(pts[m + 1][1] - yAxe) < 1.5) m++; pieds.push((k + m) >> 1); k = m + 1; } else k++;
    }
    let jBout = 0, plusPetit = Infinity;
    for (let q = 0; q + 1 < pieds.length; q++) {
      const x0 = Math.min(pts[pieds[q]][0], pts[pieds[q + 1]][0]), x1 = Math.max(pts[pieds[q]][0], pts[pieds[q + 1]][0]);
      if (x0 <= trous[p][0] && trous[p][0] <= x1 && x1 - x0 < plusPetit) { plusPetit = x1 - x0; jBout = q; }
    }
    const ia0 = pieds[jBout], ib0 = pieds[jBout + 1];   // les deux pieds de l'arc du bout
    const k0 = pieds[0], kFin = pieds[pieds.length - 1];   // l'arrivée sur l'axe, en haut des deux descentes
    // pour chaque point du brin d'aller (de k0 à ia0), le point du brin de retour (de ib0 à kFin) qui lui fait face : le plus proche, de façon monotone
    const vis = {};
    let debut = ib0;   // en remontant vers le clou (k décroît), le point qui fait face avance vers la fin du brin de retour (m croît)
    for (let k = ia0; k >= k0; k--) {
      let m = debut, d0 = Infinity;
      for (let q = debut; q <= kFin; q++) { const d = Math.hypot(pts[q][0] - pts[k][0], pts[q][1] - pts[k][1]); if (d < d0) { d0 = d; m = q; } }
      vis[k] = m; debut = m;
    }
    return { pts, cum, p, ia0, ib0, k0, kFin, vis, pieds, jBout, L: cum[cum.length - 1], N: pts.length };
  });
  const bouchon = (r, ia, ib) => {   // un demi-cercle de pts[ia] à pts[ib], du côté du bout (dans le sens de marche du brin d'aller)
    const A = r.pts[ia], B = r.pts[ib];
    const t1 = [r.pts[Math.min(ia + 4, r.ia0)][0] - r.pts[Math.max(ia - 4, 0)][0], r.pts[Math.min(ia + 4, r.ia0)][1] - r.pts[Math.max(ia - 4, 0)][1]];
    const t2 = [r.pts[Math.max(ib - 4, r.ib0)][0] - r.pts[Math.min(ib + 4, r.N - 1)][0], r.pts[Math.max(ib - 4, r.ib0)][1] - r.pts[Math.min(ib + 4, r.N - 1)][1]];
    const d = [t1[0] + t2[0], t1[1] + t2[1]];
    const M = [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2], rayon = Math.hypot(A[0] - B[0], A[1] - B[1]) / 2;
    const phi0 = Math.atan2(A[1] - M[1], A[0] - M[0]);
    const milieu = (sg) => [M[0] + rayon * Math.cos(phi0 + sg * Math.PI / 2), M[1] + rayon * Math.sin(phi0 + sg * Math.PI / 2)];
    const sg = ((milieu(1)[0] - M[0]) * d[0] + (milieu(1)[1] - M[1]) * d[1]) >= 0 ? 1 : -1;
    const arc = [];
    for (let q = 1; q < 14; q++) { const th = sg * Math.PI * q / 14; arc.push([M[0] + rayon * Math.cos(phi0 + th), M[1] + rayon * Math.sin(phi0 + th)]); }
    return { arc, M };
  };
  // Le planning : pour chaque lacet, des morceaux de tirage [t0, t1, de u à u'] (u : la part retirée, de 0 à 1 = arrivée sur l'axe). Naturel : un morceau par
  // lacet, dans l'ordre des numéros ; entiers : idem dans un ordre tiré ; morceaux : chaque lacet est coupé en 2 à 5 morceaux de longueurs tirées, et on
  // change de brin quand on veut (entrelacement tiré, l'ordre propre à chaque lacet est gardé). Le temps d'un morceau est proportionnel à la longueur retirée.
  const mode = graine === undefined || graine === null ? 'naturel' : (ordreMode || 'entiers');   // naturel, entiers, morceaux, rencontres
  let a0 = (graine || 0) >>> 0;
  const hasard = () => { a0 = (a0 + 0x6D2B79F5) >>> 0; let t = a0; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const retire = rubans.map((r) => Math.max(1, (r.cum[r.ia0] - r.cum[r.k0]) + (r.cum[r.kFin] - r.cum[r.ib0])));   // la longueur retirée par un lacet entier
  const files = rubans.map((r, i) => {   // les morceaux de chaque lacet, dans l'ordre
    if (mode === 'rencontres') return Array.from({ length: r.jBout }, (_, j) => [j / r.jBout, (j + 1) / r.jBout]);   // une rencontre avec l'axe par morceau
    if (mode !== 'morceaux') return [[0, 1]];
    const q = 2 + Math.floor(hasard() * 4);
    const coupes = Array.from({ length: q - 1 }, () => hasard()).sort((x, y) => x - y);
    const bornes = [0, ...coupes, 1];
    return bornes.slice(1).map((b, j) => [bornes[j], b]);
  });
  let sequence = [];   // [lacet, de, à]
  if (mode === 'morceaux' || mode === 'rencontres') {   // on choisit un brin au hasard parmi ceux qui ne sont pas finis, on tire son prochain morceau
    const reste = files.map((f) => f.slice());
    while (reste.some((f) => f.length)) {
      const vivants = reste.map((f, i) => (f.length ? i : -1)).filter((i) => i >= 0);
      const i = vivants[Math.floor(hasard() * vivants.length)];
      const [de, a] = reste[i].shift();
      sequence.push([i, de, a]);
    }
  } else {
    const ordreL = rubans.map((r, i) => i);
    if (mode === 'entiers') for (let i = ordreL.length - 1; i > 0; i--) { const j = Math.floor(hasard() * (i + 1)); [ordreL[i], ordreL[j]] = [ordreL[j], ordreL[i]]; }
    sequence = ordreL.map((i) => [i, 0, 1]);
  }
  const poids = sequence.map(([i, de, a]) => {
    const r = rubans[i];
    if (mode !== 'rencontres') return (a - de) * retire[i];
    const q = r.jBout - Math.round(de * r.jBout);   // le pas va du pied q au pied q − 1
    return Math.max(1, 2 * (r.cum[r.pieds[q]] - r.cum[r.pieds[q - 1]]));
  });
  const somme = poids.reduce((x, y) => x + y, 0);
  let t0 = 0;
  const plan = rubans.map(() => []);   // plan[i] : les morceaux {t0, t1, de, a} du lacet i
  sequence.forEach(([i, de, a], j) => { const t1 = t0 + poids[j] / somme; plan[i].push({ t0, t1, de, a }); t0 = t1; });
  const avancement = (i, t) => {   // la part du lacet i retirée au temps t (0 à 1)
    let u = 0;
    for (const m of plan[i]) {
      if (t >= m.t1) u = m.a;
      else { if (t > m.t0) u = m.de + (m.a - m.de) * lisse((t - m.t0) / (m.t1 - m.t0)); break; }
    }
    return u;
  };
  const ordreTirage = sequence.map(([i]) => i).filter((i, j, tab) => tab.indexOf(i) === j);   // l'ordre dans lequel on commence les lacets
  // L'indice du point du brin d'aller où s'arrête le bouchon quand la part retirée est u (0 à 1). Mode « rencontres » : u compte les rencontres du lacet avec
  // l'axe (les pieds) de la pointe vers le clou, et le bouchon va de pied en pied (entre deux pieds : interpolé) ; sinon : linéaire en indice.
  const iaDe = (r, u) => {
    if (mode !== 'rencontres') return Math.round(r.ia0 - u * (r.ia0 - r.k0));
    const q = r.jBout - u * r.jBout, q0 = Math.floor(q), q1 = Math.ceil(q);
    return Math.round(q0 === q1 ? r.pieds[q0] : r.pieds[q0] * (q1 - q) + r.pieds[q1] * (q - q0));
  };
  // les positions des trous au temps t de la rétractation (le centre du bouchon est le milieu de ses deux extrémités) : peu coûteux, sert à lire le mot
  // sur un échantillonnage beaucoup plus fin que les images
  const trousAu = (t) => rubans.map((r, i) => {
    const u = avancement(i, t), ia = iaDe(r, u);
    if (ia >= r.ia0) return trous[r.p].slice();
    const ib = Math.max(r.ib0, Math.min(r.kFin, r.vis[ia]));
    return [(r.pts[ia][0] + r.pts[ib][0]) / 2, (r.pts[ia][1] + r.pts[ib][1]) / 2];
  });
  const images = [];
  for (let n = 0; n < IMAGES_RETRACTION; n++) {
    const t = n / (IMAGES_RETRACTION - 1);
    const lacets = [], nouveaux = trous.map((q) => q.slice());
    rubans.forEach((r) => {
      const u = avancement(rubans.indexOf(r), t);
      const ia = iaDe(r, u);
      if (ia >= r.ia0) { lacets.push(r.pts.flat()); return; }   // pas encore tiré : le lacet entier, le trou à sa place
      const ib = Math.max(r.ib0, Math.min(r.kFin, r.vis[ia]));
      const { arc, M } = bouchon(r, ia, ib);
      lacets.push(r.pts.slice(0, ia + 1).concat(arc, r.pts.slice(ib)).flat());
      nouveaux[r.p] = M;   // le trou est le centre du bouchon
    });
    images.push({ lacets, trous: nouveaux.flat(), clou: Array.from(fixe.clou), brin: 3.5, ecart: 0, _trousLacets: rubans.map((r) => nouveaux[r.p]) });
  }
  const retour = images.reverse();
  const nb = retour.length, L = mot.length;
  retour[0].chapitres = Array.from({ length: L + 1 }, (_, j) => Math.round(j * (nb - 1) / L));
  // Le mot de tresse que les trous écrivent : au départ ils sont alignés dans l'ordre ; chaque fois que deux trous voisins échangent leur ordre
  // selon l'axe, c'est une lettre σ_i (le trou qui va vers la droite passe au-dessus : demi-tour horaire à l'écran, comme σ_i du reste de la page)
  // ou σ_i⁻¹ (il passe au-dessous). Les lettres sont lues dans le sens de lecture du film ; entre deux images, les positions sont interpolées.
  const lettres = [];   // [indice de l'image où la lettre s'écrit, lettre]
  const n = rubans.length;
  const PAS_FIN = 40;   // sous-pas par image : le mouvement réel des trous, pas des cordes entre images
  const depart = trousAu(1);   // au départ du film joué (t = 1) : les trous sont alignés, dans l'ordre
  let ordre = Array.from({ length: n }, (_, i) => i).sort((a, b) => depart[a][0] - depart[b][0]);
  for (let sub = 1; sub <= (nb - 1) * PAS_FIN; sub++) {
    const tau = sub / PAS_FIN;                       // le temps du film joué, en images
    const P = trousAu(Math.max(0, (nb - 1 - tau) / (nb - 1)));
    const nouvel = Array.from({ length: n }, (_, i) => i).sort((a, b) => P[a][0] - P[b][0]);
    let encore = true;
    while (encore) {
      encore = false;
      for (let j = 0; j + 1 < n; j++) {
        const g = ordre[j], d = ordre[j + 1];
        if (nouvel.indexOf(g) > nouvel.indexOf(d)) {   // g passe à droite de d
          lettres.push([Math.ceil(tau), P[g][1] < P[d][1] ? j + 1 : -(j + 1)]);
          ordre[j] = d; ordre[j + 1] = g; encore = true; break;
        }
      }
    }
  }
  const motGenere = lettres.map((x) => x[1]);
  retour[0].lettres = lettres.flat();   // pour le banc : le mot s'écrit sous le film, à mesure
  let message = `mot obtenu (${motGenere.length} lettres)` + (mode === 'rencontres' ? `, un brin au hasard à chaque tirage, le trou va à la prochaine rencontre de l'axe (graine ${graine}, ${sequence.length} tirages, ordre de départ ${ordreTirage.map((i) => i + 1).join(' ')})` : mode === 'morceaux' ? `, lacets tirés par morceaux dans le désordre (graine ${graine}, ${sequence.length} tirages, ordre de départ ${ordreTirage.map((i) => i + 1).join(' ')})` : mode === 'entiers' ? `, lacets tirés dans l'ordre ${ordreTirage.map((i) => i + 1).join(' ')} (graine ${graine})` : '');
  if (motGenere.length && n >= 2) {
    const egal = (m1, m2) => { const a = self.ardoise.analyse(m1), b = self.ardoise.analyse(m2); if (a.erreur || b.erreur) return null; const fa = Array.from(a.fn).map((w) => Array.from(w).join(' ')), fb = Array.from(b.fn).map((w) => Array.from(w).join(' ')); return a.n === b.n && fa.join('|') === fb.join('|'); };
    const e1 = egal(mot, motGenere);
    message += e1 === null ? ' : comparaison impossible (limites de la page)' : e1 ? ' : les méandres sont égaux' : ' : les méandres diffèrent';
    if (e1 === false) message += egal(mot, motGenere.map((x) => -x)) ? ' (égaux avec les signes inversés)' : '';
  }
  retour.forEach((im, k) => {
    delete im._trousLacets;
    const f = enFloat32(im);
    postMessage({ type: 'image', image: f, k, total: nb }, tampons(f));
  });
  postMessage({ type: 'fini', message, erreur: false });
}

onmessage = (e) => {
  const d = e.data;
  if (d.sansLimites) { SANS_LIMITES = true; self.ardoise.sans_limites(true); }
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
  if (mode === 'retractation') { filmRetraction(mot, d.graine, d.ordre); return; }
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
