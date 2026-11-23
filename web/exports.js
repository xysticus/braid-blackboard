// Les exports de l'image en cours d'un lecteur : PNG, SVG, JSON (menu « ⤓ » de la barre du lecteur). Voir etude_exploitation_des_images.md.
// Tout se calcule dans le navigateur : rien n'est envoyé nulle part. Les films sont gardés sous forme de polylignes, on redessine donc
// à n'importe quelle taille sans perte (listeDeTrace et dessineListe, ardoise.js).
//
// L'escargot et les iris (films sans tresse) sont des œuvres du projet : leurs exports portent la licence CC BY 4.0 et nous attribuent
// (LICENCES.md). Les images faites à partir d'un mot de la personne portent seulement une mention discrète « Créé avec Ardoise à tresse ».

const URL_PROJET = 'https://github.com/xysticus/braid-blackboard';
const URL_LICENCES = URL_PROJET + '/blob/master/LICENCES.md';
const URL_CC_BY = 'https://creativecommons.org/licenses/by/4.0/';
const CITATION = `Ardoise à tresse (braid-blackboard), xysticus, ${URL_PROJET}, licence CC BY 4.0 (contenus) / MIT (code)`;
const MODES_LIBRES = new Set(['escargot', 'bouquet']);
const NOMS_DE_VUE = { conforme: 'lacets', diagramme: 'diagramme', rubans: 'rubans', triangulation: 'triangulation', escargot: 'escargot', bouquet: 'iris' };

// ---------------------------------------------------------------- outils

const TABLE_CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

// Le CRC-32 d'une suite d'octets (celui des blocs PNG, et plus tard des en-têtes de zip).
function crc32(octets, debut = 0, fin = octets.length) {
  let c = 0xffffffff;
  for (let i = debut; i < fin; i++) c = TABLE_CRC[(c ^ octets[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const nombre3 = (x) => Math.round(x * 1000) / 1000;

function echappeXML(t) {
  return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function telecharge(blob, nom) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nom;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

// Le mot écrit en ASCII, sans caractères spéciaux : [1, -2, 1] → « 1_-2_1 ».
const motEnAscii = (lettres) => lettres.join('_');

// ardoise-<mot>-<vue>-image<k>.<ext> (l'escargot et les iris n'ont pas de mot).
function nomDeFichier(lecteur, ext, suffixe = null) {
  const vue = NOMS_DE_VUE[lecteur.mode] || lecteur.mode;
  const mot = MODES_LIBRES.has(lecteur.mode) ? '' : motEnAscii(lecteur.lettres) + '-';
  return `ardoise-${mot}${vue}-${suffixe || 'image' + (lecteur.indice() + 1)}.${ext}`;
}

// Les mentions, selon la nature de l'image : { titre, description, auteur?, licence? }.
function mentions(lecteur, indice = lecteur.indice()) {
  const k = indice + 1, n = lecteur.images.length;
  if (MODES_LIBRES.has(lecteur.mode)) {
    const nom = lecteur.mode === 'escargot' ? 'L\'escargot : une spirale de rubans' : 'La floraison des Iris';
    return { titre: `${nom} (image ${k} sur ${n})`, description: CITATION, auteur: 'xysticus', licence: 'CC BY 4.0 ' + URL_CC_BY };
  }
  const mot = lecteur.lettres.map(nomLettre).join('');
  return { titre: `Tresse ${mot}, vue « ${NOMS_DE_VUE[lecteur.mode]} », image ${k} sur ${n}`, description: `Créé avec Ardoise à tresse, ${URL_PROJET}` };
}

// ---------------------------------------------------------------- PNG

// Ajoute des blocs iTXt (texte UTF-8) juste après l'en-tête IHDR d'un fichier PNG. entrees : [[mot-clé, texte], …].
function ajouteTextesPNG(octets, entrees) {
  const enc = new TextEncoder();
  const blocs = entrees.map(([cle, texte]) => {
    const c = enc.encode(cle), t = enc.encode(texte);
    // mot-clé, 0, indicateur de compression 0, méthode 0, langue (vide) 0, mot-clé traduit (vide) 0, texte
    const donnees = new Uint8Array(c.length + 5 + t.length);
    donnees.set(c, 0);
    donnees.set(t, c.length + 5);
    const bloc = new Uint8Array(12 + donnees.length);   // longueur, type, données, crc
    const vue = new DataView(bloc.buffer);
    vue.setUint32(0, donnees.length);
    bloc.set(enc.encode('iTXt'), 4);
    bloc.set(donnees, 8);
    vue.setUint32(8 + donnees.length, crc32(bloc, 4, 8 + donnees.length));
    return bloc;
  });
  const apres = 8 + 25;   // la signature (8 octets) et le bloc IHDR (25 octets)
  const total = octets.length + blocs.reduce((s, b) => s + b.length, 0);
  const sortie = new Uint8Array(total);
  sortie.set(octets.subarray(0, apres), 0);
  let o = apres;
  for (const b of blocs) { sortie.set(b, o); o += b.length; }
  sortie.set(octets.subarray(apres), o);
  return sortie;
}

function canvasEnBlob(canvas, type = 'image/png') {
  return new Promise((ok, ko) => canvas.toBlob((b) => (b ? ok(b) : ko(new Error('toBlob : image vide ou trop grande'))), type));
}

// Dessine l'image en cours du lecteur sur un canvas hors écran, `echelle` fois plus grand ; fond transparent en option
// (sauf pour l'escargot et les iris, dont le fond fait partie du dessin).
function dessineExport(c, lecteur, echelle, transparent, indice) {
  const image = lecteur.images[indice];
  if (lecteur.mode === 'escargot') dessineEscargot(c, image, echelle);
  else if (lecteur.mode === 'bouquet') dessineBouquet(c, image, echelle);
  else {
    const liste = listeDeTrace(image, lecteur.mode, lecteur.vue, lecteur.construction);
    if (transparent) liste.fond = null;
    dessineListe(c, liste, echelle * lecteur.canvas.width / TAILLE_REFERENCE);
  }
}

function canvasDExport(lecteur, echelle, transparent, indice = lecteur.indice()) {
  const c = document.createElement('canvas');
  c.width = Math.round(lecteur.canvas.width * echelle);
  c.height = Math.round(lecteur.canvas.height * echelle);
  dessineExport(c, lecteur, echelle, transparent, indice);
  return c;
}

// Les octets du PNG de l'image `indice` du film, avec ses mentions (auteur et licence pour l'escargot et les iris).
async function octetsPNG(lecteur, echelle, transparent, indice = lecteur.indice()) {
  const blob = await canvasEnBlob(canvasDExport(lecteur, echelle, transparent, indice));
  const m = mentions(lecteur, indice);
  const textes = [['Title', m.titre], ['Software', 'Ardoise à tresse (braid-blackboard)'], ['Source', URL_PROJET]];
  if (m.auteur) textes.push(['Author', m.auteur], ['Copyright', `© xysticus, ${m.licence}`], ['License', m.licence], ['Description', m.description]);
  return ajouteTextesPNG(new Uint8Array(await blob.arrayBuffer()), textes);
}

async function exportePNG(lecteur, echelle, transparent) {
  telecharge(new Blob([await octetsPNG(lecteur, echelle, transparent)], { type: 'image/png' }), nomDeFichier(lecteur, 'png'));
}

// ---------------------------------------------------------------- zip des images clés

// Un zip « stocké » (sans compression : les PNG le sont déjà) : pour chaque fichier un en-tête local, les octets, puis le répertoire
// central et la fin de répertoire. fichiers : [{ nom, octets }]. Noms en UTF-8 (indicateur 0x0800).
function construitZip(fichiers) {
  const enc = new TextEncoder();
  const d = new Date();
  const heure = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  const date = ((Math.max(1980, d.getFullYear()) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  const morceaux = [], central = [];
  let position = 0;
  for (const f of fichiers) {
    const nom = enc.encode(f.nom), crc = crc32(f.octets), n = f.octets.length;
    const local = new Uint8Array(30 + nom.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true); lv.setUint16(6, 0x0800, true); lv.setUint16(8, 0, true);
    lv.setUint16(10, heure, true); lv.setUint16(12, date, true); lv.setUint32(14, crc, true);
    lv.setUint32(18, n, true); lv.setUint32(22, n, true); lv.setUint16(26, nom.length, true); lv.setUint16(28, 0, true);
    local.set(nom, 30);
    const c = new Uint8Array(46 + nom.length);
    const cv = new DataView(c.buffer);
    cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true); cv.setUint16(8, 0x0800, true); cv.setUint16(10, 0, true);
    cv.setUint16(12, heure, true); cv.setUint16(14, date, true); cv.setUint32(16, crc, true);
    cv.setUint32(20, n, true); cv.setUint32(24, n, true); cv.setUint16(28, nom.length, true);
    cv.setUint32(42, position, true);   // le décalage de l'en-tête local
    c.set(nom, 46);
    central.push(c);
    morceaux.push(local, f.octets);
    position += local.length + n;
  }
  const tailleCentral = central.reduce((s, c) => s + c.length, 0);
  const fin = new Uint8Array(22);
  const fv = new DataView(fin.buffer);
  fv.setUint32(0, 0x06054b50, true); fv.setUint16(8, fichiers.length, true); fv.setUint16(10, fichiers.length, true);
  fv.setUint32(12, tailleCentral, true); fv.setUint32(16, position, true);
  return new Blob([...morceaux, ...central, fin], { type: 'application/zip' });
}

// Les L + 1 images clés (l'état de départ, puis l'état après chaque lettre) en PNG : cle-0.png, cle-1.png… `progres(j, total)` est
// appelé avant chaque image ; on rend la main au navigateur entre deux images pour que la page reste vivante.
async function exporteZipCles(lecteur, echelle, transparent, progres) {
  const cles = lecteur.chapitres;
  const chiffres = String(cles.length - 1).length;
  const fichiers = [];
  for (let j = 0; j < cles.length; j++) {
    progres(j + 1, cles.length);
    await new Promise((ok) => setTimeout(ok, 0));
    fichiers.push({ nom: `cle-${String(j).padStart(chiffres, '0')}.png`, octets: await octetsPNG(lecteur, echelle, transparent, cles[j]) });
  }
  telecharge(construitZip(fichiers), nomDeFichier(lecteur, 'zip', 'images-cles'));
}

// ---------------------------------------------------------------- film MP4 AV1

// Le navigateur sait-il fabriquer de l'AV1 ? On le lui demande une fois ; sinon l'entrée du menu est grisée (tous les autres exports restent).
const SAIT_FAIRE_DE_L_AV1 = (async () => {
  try {
    if (typeof VideoEncoder === 'undefined' || typeof VideoFrame === 'undefined') return false;
    const s = await VideoEncoder.isConfigSupported({ codec: 'av01.0.04M.08', width: 800, height: 800, bitrate: 3e6, framerate: 25 });
    return !!s.supported;
  } catch (e) { return false; }
})();

// seq_level_idx du plus petit niveau AV1 dont la taille d'image maximale contient l'image (2.0, 2.1, 3.0, 3.1, 4.0, 5.0, 6.0).
function niveauAV1(largeur, hauteur) {
  const surface = largeur * hauteur;
  for (const [max, niveau] of [[147456, 0], [278784, 1], [665856, 4], [1065024, 5], [2359296, 8], [8912896, 12]]) if (surface <= max) return niveau;
  return 16;
}

// Le bandeau de fin de l'escargot et des iris : « Ardoise à tresse — xysticus — CC BY 4.0 » (une vidéo se sépare facilement de ses métadonnées).
function dessineGenerique(c) {
  const ctx = c.getContext('2d');
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const taille = c.width / 30, haut = 2.4 * taille;
  ctx.fillStyle = 'rgba(20, 24, 32, 0.78)';
  ctx.fillRect(0, c.height - haut, c.width, haut);
  ctx.fillStyle = '#fff';
  ctx.font = `600 ${taille}px system-ui, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('Ardoise à tresse — xysticus — CC BY 4.0', c.width / 2, c.height - haut / 2);
}

// Le film MP4 AV1 : chaque image du film est dessinée à l'échelle voulue, encodée par le VideoEncoder du navigateur, puis emballée (mp4.js).
// 25 images par seconde (12,5 pour les iris) à cadence constante, 0,5 s sur la première image et 1,5 s sur la dernière (des images répétées) ;
// une image clé toutes les 50 images.
// Pour l'escargot et les iris, un générique de fin (2 s) suit la dernière image. `progres(i, n)` est appelé avant chaque image ;
// `signal` (AbortSignal) interrompt le travail : l'encodeur est fermé, rien ne reste.
async function exporteFilm(film, echelle, progres, signal) {
  const libre = MODES_LIBRES.has(film.mode);
  const largeur = Math.round(film.canvas.width * echelle), hauteur = Math.round(film.canvas.height * echelle);
  if (largeur % 2 || hauteur % 2) throw new Error('la taille du film doit être paire');
  const niveau = niveauAV1(largeur, hauteur);
  const config = {
    codec: `av01.0.${String(niveau).padStart(2, '0')}M.08`, width: largeur, height: hauteur,
    bitrate: Math.max(1e6, Math.round(3e6 * largeur * hauteur / 640000)), framerate: film.ips, latencyMode: 'realtime',
  };
  const verdict = await VideoEncoder.isConfigSupported(config);
  if (!verdict.supported) throw new Error('ce navigateur ne sait pas fabriquer de l\'AV1 à cette taille');

  // le programme du film : une entrée par image du FILM, toutes de la même durée (cadence constante). Les pauses (0,5 s sur la première image,
  // 1,5 s sur la dernière, 2 s de générique pour l'escargot et les iris) sont des images répétées, pas un échantillon long : les lecteurs
  // (VLC) ne respectent pas la durée du dernier échantillon et coupaient le film avant la fin ; une image répétée ne coûte que quelques octets.
  const n = film.images.length;
  const image = Math.round(1000 / film.ips);
  const repete = (ms) => Math.max(0, Math.round(ms / image) - 1);   // images en plus de l'image elle-même
  const programme = [];
  film.images.forEach((_, i) => {
    const fois = 1 + (i === 0 ? repete(500) : i === n - 1 && !libre ? repete(1500) : 0);
    for (let r = 0; r < fois; r++) programme.push({ i, duree: image, generique: false });
  });
  if (libre) for (let r = 0; r < 1 + repete(2000); r++) programme.push({ i: n - 1, duree: image, generique: true });

  const morceaux = [];
  let erreurEncodeur = null;
  const encodeur = new VideoEncoder({
    output: (m) => { const octets = new Uint8Array(m.byteLength); m.copyTo(octets); morceaux.push({ octets, cle: m.type === 'key', ts: m.timestamp }); },
    error: (e) => { erreurEncodeur = e; },
  });
  const ferme = () => { try { if (encodeur.state !== 'closed') encodeur.close(); } catch (e) { /* déjà fermé */ } };
  const interrompu = () => { if (signal && signal.aborted) { ferme(); throw new DOMException('Export annulé', 'AbortError'); } };
  try {
    encodeur.configure(config);
    const c = document.createElement('canvas');
    c.width = largeur;
    c.height = hauteur;
    let temps = 0;   // en microsecondes
    for (let k = 0; k < programme.length; k++) {
      interrompu();
      if (erreurEncodeur) throw erreurEncodeur;
      progres(k + 1, programme.length);
      const p = programme[k], avant = programme[k - 1];
      if (!avant || avant.i !== p.i || avant.generique !== p.generique) {   // une image répétée n'est pas redessinée
        dessineExport(c, film, echelle, false, p.i);   // pas de transparence dans l'AV1 : le fond est plein
        if (p.generique) dessineGenerique(c);
      }
      const cadre = new VideoFrame(c, { timestamp: temps, duration: p.duree * 1000 });
      encodeur.encode(cadre, { keyFrame: k % 50 === 0 });
      cadre.close();
      temps += p.duree * 1000;
      // on rend la main au navigateur (page vivante, annulation possible) et on ne laisse pas l'encodeur s'engorger
      do { await new Promise((ok) => setTimeout(ok, 0)); interrompu(); } while (encodeur.encodeQueueSize > 6);
    }
    await encodeur.flush();
    interrompu();
    if (erreurEncodeur) throw erreurEncodeur;
  } finally {
    ferme();
  }
  if (morceaux.length !== programme.length) throw new Error(`l'encodeur a rendu ${morceaux.length} images au lieu de ${programme.length}`);
  morceaux.sort((a, b) => a.ts - b.ts);
  const m = mentions(film, n - 1);
  const mentionsMP4 = libre
    ? { droits: `© xysticus, ${m.licence}`, titre: m.titre, commentaire: CITATION }
    : { commentaire: m.description };
  return construitMP4({
    largeur, hauteur, niveau,
    echantillons: morceaux.map((x, k) => ({ octets: x.octets, cle: x.cle, duree: programme[k].duree })),
    mentions: mentionsMP4,
  });
}

// ---------------------------------------------------------------- SVG

// Douglas–Peucker sur une polyligne à plat (x, y, x, y, …) : garde les points à plus de `tolerance` du segment qui les relie.
function simplifie(p, tolerance) {
  const n = p.length / 2;
  if (n <= 2) return Array.from(p);
  const garde = new Uint8Array(n);
  garde[0] = garde[n - 1] = 1;
  const pile = [[0, n - 1]];
  const t2 = tolerance * tolerance;
  while (pile.length) {
    const [a, b] = pile.pop();
    const ax = p[2 * a], ay = p[2 * a + 1], dx = p[2 * b] - ax, dy = p[2 * b + 1] - ay;
    const l2 = dx * dx + dy * dy;
    let pire = -1, indice = -1;
    for (let i = a + 1; i < b; i++) {
      const ex = p[2 * i] - ax, ey = p[2 * i + 1] - ay;
      let d2;
      if (l2 === 0) d2 = ex * ex + ey * ey;
      else {
        const u = Math.max(0, Math.min(1, (ex * dx + ey * dy) / l2));
        const fx = ex - u * dx, fy = ey - u * dy;
        d2 = fx * fx + fy * fy;
      }
      if (d2 > pire) { pire = d2; indice = i; }
    }
    if (pire > t2) { garde[indice] = 1; pile.push([a, indice], [indice, b]); }
  }
  const r = [];
  for (let i = 0; i < n; i++) if (garde[i]) r.push(p[2 * i], p[2 * i + 1]);
  return r;
}

const points2 = (p) => { const s = []; for (let k = 0; k + 1 < p.length; k += 2) s.push(`${nombre3(p[k])},${nombre3(p[k + 1])}`); return s.join(' '); };

// Le SVG de la liste de tracé (la même que celle du canvas : le SVG montre ce qu'on voit). Pas de texte dans l'image, donc pas de polices.
function svgDeListe(liste, largeur, hauteur, m) {
  const sortie = [];
  sortie.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${largeur} ${hauteur}" width="${largeur}" height="${hauteur}">`);
  sortie.push(`<title>${echappeXML(m.titre)}</title>`);
  sortie.push(`<desc>${echappeXML(m.description)}</desc>`);
  if (liste.fond) sortie.push(`<rect width="${largeur}" height="${hauteur}" fill="${liste.fond}"/>`);
  const v = liste.vue;
  sortie.push(`<g${v ? ` transform="matrix(${nombre3(v.s)} 0 0 ${nombre3(v.s)} ${nombre3(v.tx)} ${nombre3(v.ty)})"` : ''} fill="none" stroke-linecap="round" stroke-linejoin="round">`);
  for (const e of liste.elements) {
    if (e.type === 'ligne') {
      if (e.pts.length < 4) continue;
      sortie.push(`<polyline points="${points2(simplifie(e.pts, 0.15))}" stroke="${e.couleur}" stroke-width="${nombre3(e.largeur)}"/>`);
    } else if (e.type === 'segments') {
      const s = e.pts;
      if (!e.opacites) {
        let d = '';
        for (let k = 0; k + 3 < s.length; k += 4) d += `M${nombre3(s[k])} ${nombre3(s[k + 1])}L${nombre3(s[k + 2])} ${nombre3(s[k + 3])}`;
        sortie.push(`<path d="${d}" stroke="${e.couleur}" stroke-width="${nombre3(e.largeur)}"/>`);
      } else {
        for (let j = 0; 4 * j + 3 < s.length; j++) {   // un segment à la fois : chacun a sa propre opacité
          if (!(e.opacites[j] > 0.004)) continue;
          sortie.push(`<path d="M${nombre3(s[4 * j])} ${nombre3(s[4 * j + 1])}L${nombre3(s[4 * j + 2])} ${nombre3(s[4 * j + 3])}" stroke="${e.couleur}" stroke-width="${nombre3(e.largeur)}" stroke-opacity="${nombre3(e.opacites[j])}"/>`);
        }
      }
    } else if (e.type === 'disques') {
      for (let k = 0; k + 1 < e.pts.length; k += 2) sortie.push(`<circle cx="${nombre3(e.pts[k])}" cy="${nombre3(e.pts[k + 1])}" r="${nombre3(e.rayon)}" fill="${e.couleur}" stroke="none"/>`);
    }
  }
  sortie.push('</g>', '</svg>');
  return sortie.join('\n') + '\n';
}

function exporteSVG(lecteur, transparent) {
  const liste = listeDeTrace(lecteur.images[lecteur.indice()], lecteur.mode, lecteur.vue, lecteur.construction);
  if (transparent) liste.fond = null;
  const texte = svgDeListe(liste, lecteur.canvas.width, lecteur.canvas.height, mentions(lecteur));
  telecharge(new Blob([texte], { type: 'image/svg+xml' }), nomDeFichier(lecteur, 'svg'));
}

// ---------------------------------------------------------------- JSON

// Les nombres des tableaux (Float32Array, tableaux de Float32Array) arrondis au millième : pour retracer avec matplotlib, pgfplots, etc.
function pourJSON(v) {
  if (v instanceof Float32Array || v instanceof Float64Array) return Array.from(v, nombre3);
  if (Array.isArray(v)) return v.map(pourJSON);
  if (typeof v === 'number') return nombre3(v);
  return v;
}

function exporteJSON(lecteur) {
  const image = lecteur.images[lecteur.indice()];
  const m = mentions(lecteur);
  const sortie = {};
  if (m.auteur) Object.assign(sortie, { auteur: m.auteur, licence: m.licence, source: URL_PROJET, citation: CITATION });
  else Object.assign(sortie, { cree_avec: 'Ardoise à tresse', source: URL_PROJET });
  if (!MODES_LIBRES.has(lecteur.mode)) Object.assign(sortie, { mot: lecteur.lettres.slice(), vue: NOMS_DE_VUE[lecteur.mode] });
  else sortie.vue = NOMS_DE_VUE[lecteur.mode];
  sortie.image = lecteur.indice() + 1;
  sortie.images = lecteur.images.length;
  sortie.cadre = [lecteur.canvas.width, lecteur.canvas.height];
  if (lecteur.vue) sortie.zoom = { echelle: nombre3(lecteur.vue.s), tx: nombre3(lecteur.vue.tx), ty: nombre3(lecteur.vue.ty) };
  if (!MODES_LIBRES.has(lecteur.mode)) Object.assign(sortie, { couleurs: PALETTE.slice(), fond: FOND });
  // tous les champs de l'image (lacets, trous, clou, points fixes, lignes de construction…), sans les champs d'étude du banc d'essai
  for (const [nom, valeur] of Object.entries(image)) {
    if (nom === 'chapitres' || nom === 'maillage' || nom === 'etude' || nom === 'ab') continue;
    sortie[nom] = pourJSON(valeur);
  }
  telecharge(new Blob([JSON.stringify(sortie)], { type: 'application/json' }), nomDeFichier(lecteur, 'json'));
}

// ---------------------------------------------------------------- le menu « ⤓ Exporter »

// Rend l'élément à mettre dans la barre du lecteur : un bouton qui ouvre le menu (au clic ; Échap ou un clic ailleurs le ferme et
// rend le focus au bouton).
function menuExport(lecteur) {
  const libre = MODES_LIBRES.has(lecteur.mode);
  const id = 'export-' + lecteur.mode;
  const zone = document.createElement('span');
  zone.className = 'export';
  const tailles = [1, 2, 4].map((e) => `<option value="${e}"${e === 2 ? ' selected' : ''}>${lecteur.canvas.width * e} × ${lecteur.canvas.height * e}</option>`).join('');
  zone.innerHTML =
    `<button type="button" class="bouton-export" aria-haspopup="true" aria-expanded="false" aria-controls="${id}" title="Exporter l'image en cours" aria-label="Exporter l'image en cours">⤓</button>` +
    `<div class="menu-export" id="${id}" role="group" aria-label="Exporter l'image en cours" hidden>` +
    `<label>Taille des images <select class="taille">${tailles}</select></label>` +
    (libre ? '' : `<label><input type="checkbox" class="transparent"> fond transparent</label>`) +
    `<button type="button" data-export="png">Image PNG</button>` +
    (libre ? '' : `<button type="button" data-export="svg">Image SVG</button>`) +
    `<button type="button" data-export="json">Données JSON</button>` +
    `<label>Taille du film <select class="taille-film">${[1, 2].map((e) => `<option value="${e}"${e === 1 ? ' selected' : ''}>${lecteur.canvas.width * e} × ${lecteur.canvas.height * e}</option>`).join('')}</select></label>` +
    `<button type="button" data-export="film" title="Un film MP4 (AV1), fabriqué par ton navigateur : rien n'est envoyé nulle part">Film MP4 AV1</button>` +
    `<p class="av1-export" hidden></p>` +
    (lecteur.aDesChapitres() ? `<button type="button" data-export="zip" title="Une image PNG par image clé : l'état de départ, puis l'état après chaque lettre">Images clés (zip, ${lecteur.chapitres.length} images)</button>` : '') +
    (libre ? `<p class="licence-export">Ces images sont sous licence <a href="${URL_CC_BY}" target="_blank" rel="noopener">CC BY 4.0</a> : cite xysticus et le projet (<a href="${URL_LICENCES}" target="_blank" rel="noopener">licences</a>).</p>` : '') +
    `<p class="progression-export" role="status" hidden></p>` +
    `<progress class="barre-export" hidden></progress>` +
    `<button type="button" class="annuler-export" hidden>Annuler</button>` +
    `<p class="erreur-export" role="alert" hidden></p>` +
    `</div>`;
  const bouton = zone.querySelector('.bouton-export');
  const menu = zone.querySelector('.menu-export');
  const erreur = zone.querySelector('.erreur-export');
  const progression = zone.querySelector('.progression-export');
  const barre = zone.querySelector('.barre-export');
  const annuler = zone.querySelector('.annuler-export');
  const boutonFilm = zone.querySelector('button[data-export=film]');
  const phraseAV1 = zone.querySelector('.av1-export');
  let controle = null;   // l'AbortController de l'export en cours (le menu ne se ferme pas pendant ce temps ; Échap l'annule)
  SAIT_FAIRE_DE_L_AV1.then((oui) => {
    if (oui) return;
    boutonFilm.disabled = true;
    boutonFilm.dataset.indisponible = '1';
    phraseAV1.textContent = 'Ton navigateur ne sait pas fabriquer de l\'AV1 : essaie Firefox ou Chrome. Les autres exports restent disponibles.';
    phraseAV1.hidden = false;
  });
  const ferme = (rendFocus) => {
    if (controle) return;   // un export est en cours : on l'annule (Échap, bouton), on ne ferme pas
    menu.hidden = true;
    bouton.setAttribute('aria-expanded', 'false');
    document.removeEventListener('pointerdown', dehors, true);
    document.removeEventListener('keydown', touche, true);
    if (rendFocus) bouton.focus();
  };
  const dehors = (e) => { if (!zone.contains(e.target)) ferme(false); };
  const touche = (e) => { if (e.key === 'Escape') { e.stopPropagation(); if (controle) controle.abort(); else ferme(true); } };
  const ouvre = () => {
    lecteur.arrete();   // on exporte l'image qu'on voit
    erreur.hidden = true;
    progression.hidden = true;
    menu.hidden = false;
    bouton.setAttribute('aria-expanded', 'true');
    document.addEventListener('pointerdown', dehors, true);
    document.addEventListener('keydown', touche, true);
    menu.querySelector('button').focus();
  };
  bouton.onclick = () => (menu.hidden ? ouvre() : ferme(true));
  menu.querySelectorAll('button[data-export]').forEach((b) => {
    b.onclick = async () => {
      const echelle = Number(menu.querySelector('.taille').value);
      const case_ = menu.querySelector('.transparent');
      const transparent = !!case_ && case_.checked;
      const boutons = menu.querySelectorAll('button[data-export]');
      boutons.forEach((x) => { x.disabled = true; });
      erreur.hidden = true;
      controle = new AbortController();
      annuler.hidden = false;
      annuler.onclick = () => controle.abort();
      try {
        if (b.dataset.export === 'film') {
          // une photo du film : un nouveau mot pendant l'export ne le mélange pas
          const photo = { mode: lecteur.mode, images: lecteur.images, vue: lecteur.vue, construction: lecteur.construction, lettres: lecteur.lettres.slice(), canvas: lecteur.canvas, ips: lecteur.ips };
          barre.hidden = false;
          const blob = await exporteFilm(photo, Number(menu.querySelector('.taille-film').value), (j, n) => {
            progression.textContent = `image ${j} sur ${n}…`;
            progression.hidden = false;
            barre.max = n;
            barre.value = j;
          }, controle.signal);
          telecharge(blob, nomDeFichier(lecteur, 'mp4', 'film'));
        } else if (b.dataset.export === 'png') await exportePNG(lecteur, echelle, transparent);
        else if (b.dataset.export === 'zip') {
          await exporteZipCles(lecteur, echelle, transparent, (j, n) => { progression.textContent = `image clé ${j} sur ${n}…`; progression.hidden = false; });
        }
        else if (b.dataset.export === 'svg') exporteSVG(lecteur, transparent);
        else exporteJSON(lecteur);
        controle = null;
        ferme(true);
      } catch (e) {
        if (e && e.name === 'AbortError') { erreur.textContent = 'Export annulé.'; } else { erreur.textContent = 'Export impossible : ' + e.message; }
        erreur.hidden = false;
      } finally {
        controle = null;
        boutons.forEach((x) => { x.disabled = !!x.dataset.indisponible; });
        progression.hidden = true;
        barre.hidden = true;
        annuler.hidden = true;
      }
    };
  });
  return zone;
}
