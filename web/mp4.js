// Un emballeur MP4 minimal : un seul flux vidéo AV1, tous les échantillons dans un seul bloc `mdat`, `moov` avant `mdat` (lecture
// pendant le téléchargement). Écrit pour l'export du film (exports.js), sans bibliothèque : voir etude_exploitation_des_images.md, §6.
//
// Ce que Firefox donne à la sortie de VideoEncoder pour l'AV1 : un « temporal unit » par image (OBUs au format « low overhead »), SANS la
// description `av1C` que le conteneur exige. On la fabrique : quatre octets tirés du nom du codec (profil 0, niveau, 4:2:0 à 8 bits), suivis
// de l'OBU « sequence header » trouvée dans la première image clé. Les OBUs « temporal delimiter » sont retirées des échantillons (le
// conteneur remplace leur rôle).

// (tout est dans une fonction : seul `construitMP4` est visible des autres scripts)
const EMBALLEUR_MP4 = (() => {
const u8 = (...a) => Uint8Array.from(a);
const u16 = (n) => u8((n >> 8) & 255, n & 255);
const u32 = (n) => u8((n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255);
const zeros = (n) => new Uint8Array(n);
const utf8 = (s) => new TextEncoder().encode(s);

function concat(parts) {
  const total = parts.reduce((s, p) => s + p.length, 0);
  const r = new Uint8Array(total);
  let o = 0;
  for (const p of parts) { r.set(p, o); o += p.length; }
  return r;
}

// Le type d'une boîte : quatre octets, un par caractère (Latin-1 : « © » = 0xA9, que l'UTF-8 coderait sur deux octets).
const typeBoite = (t) => u8(...Array.from(t, (c) => c.charCodeAt(0)));

function boite(type, ...parts) {
  const corps = concat(parts);
  return concat([u32(8 + corps.length), typeBoite(type), corps]);
}
const boiteComplete = (type, version, drapeaux, ...parts) => boite(type, u8(version, (drapeaux >> 16) & 255, (drapeaux >> 8) & 255, drapeaux & 255), ...parts);

const MATRICE_UNITE = concat([u32(0x00010000), zeros(12), u32(0x00010000), zeros(12), u32(0x40000000)]);
const LANGUE_INDETERMINEE = 0x55c4;   // « und » : trois lettres sur 5 bits chacune

// ---------------------------------------------------------------- les OBUs de l'AV1

// Découpe un « temporal unit » en OBUs : [{ type, debut, fin }] (la fin de la dernière OBU sans taille est la fin des données).
function decoupeOBUs(d) {
  const r = [];
  let i = 0;
  while (i < d.length) {
    const debut = i;
    const entete = d[i++];
    const type = (entete >> 3) & 15;
    if (entete & 4) i++;   // octet d'extension
    let taille;
    if (entete & 2) {   // champ de taille (LEB128)
      taille = 0;
      for (let k = 0; k < 8; k++) {
        const b = d[i++];
        taille |= (b & 0x7f) << (7 * k);
        if (!(b & 0x80)) break;
      }
    } else taille = d.length - i;
    i += taille;
    r.push({ type, debut, fin: Math.min(i, d.length) });
  }
  return r;
}

// L'échantillon du conteneur : les OBUs de l'image sans les « temporal delimiter » (type 2).
function echantillonDe(d) {
  return concat(decoupeOBUs(d).filter((o) => o.type !== 2).map((o) => d.subarray(o.debut, o.fin)));
}

// L'OBU « sequence header » (type 1) d'une image clé, ou null.
function enTeteDeSequence(d) {
  const o = decoupeOBUs(d).find((x) => x.type === 1);
  return o ? d.subarray(o.debut, o.fin) : null;
}

// Les octets de la boîte `av1C` : marqueur et version, profil et niveau, 4:2:0 à 8 bits, puis l'en-tête de séquence (configOBUs).
// `niveau` : l'indice de niveau (seq_level_idx_0) du nom du codec, « av01.0.<niveau>M.08 ».
function av1C(niveau, enTete) {
  return concat([u8(0x81, niveau & 31, 0x0c, 0x00), enTete || new Uint8Array(0)]);
}

// ---------------------------------------------------------------- le fichier

// echantillons : [{ octets (un temporal unit tel que rendu par l'encodeur), cle (image clé), duree (en millisecondes) }]
// mentions : { droits? (copyright), titre?, commentaire? } écrites dans `udta`.
function construitMP4({ largeur, hauteur, niveau, echantillons, mentions = {} }) {
  const echs = echantillons.map((e) => ({ octets: echantillonDe(e.octets), cle: e.cle, duree: e.duree }));
  const premiere = echantillons.find((e) => e.cle);
  const enTete = premiere ? enTeteDeSequence(premiere.octets) : null;
  const echelleTemps = 1000;   // des millisecondes
  const duree = echs.reduce((s, e) => s + e.duree, 0);

  // stts : des séries d'échantillons de même durée
  const series = [];
  for (const e of echs) {
    const derniere = series[series.length - 1];
    if (derniere && derniere[1] === e.duree) derniere[0]++; else series.push([1, e.duree]);
  }
  const syncs = [];
  echs.forEach((e, i) => { if (e.cle) syncs.push(i + 1); });

  const nomCompresseur = concat([u8(0), zeros(31)]);
  const entree = boite('av01',
    zeros(6), u16(1),                                // réservé, indice de la référence de données
    u16(0), u16(0), zeros(12),                       // pré-défini, réservé, pré-défini
    u16(largeur), u16(hauteur), u32(0x00480000), u32(0x00480000), u32(0), u16(1),
    nomCompresseur, u16(0x0018), u16(0xffff),
    boite('av1C', av1C(niveau, enTete)));

  const udta = (() => {
    const bs = [];
    const texteMP4 = (type, t) => { const o = utf8(t); return boite(type, u16(o.length), u16(0x15c7), o); };   // 0x15C7 : « eng »
    if (mentions.droits) {
      bs.push(boiteComplete('cprt', 0, 0, u16(LANGUE_INDETERMINEE), utf8(mentions.droits), u8(0)));   // la boîte du standard ISO
      bs.push(texteMP4('©cpy', mentions.droits));   // la forme QuickTime, que ffmpeg et ffprobe lisent (ils lisent mal la précédente)
    }
    if (mentions.titre) bs.push(texteMP4('©nam', mentions.titre));
    if (mentions.commentaire) bs.push(texteMP4('©cmt', mentions.commentaire));
    return bs.length ? boite('udta', ...bs) : new Uint8Array(0);
  })();

  const moov = (decalageDonnees) => boite('moov',
    boiteComplete('mvhd', 0, 0, u32(0), u32(0), u32(echelleTemps), u32(duree), u32(0x00010000), u16(0x0100), zeros(10), MATRICE_UNITE, zeros(24), u32(2)),
    boite('trak',
      boiteComplete('tkhd', 0, 3, u32(0), u32(0), u32(1), u32(0), u32(duree), zeros(8), u16(0), u16(0), u16(0), u16(0), MATRICE_UNITE, u32(largeur << 16), u32(hauteur << 16)),
      boite('mdia',
        boiteComplete('mdhd', 0, 0, u32(0), u32(0), u32(echelleTemps), u32(duree), u16(LANGUE_INDETERMINEE), u16(0)),
        boiteComplete('hdlr', 0, 0, u32(0), typeBoite('vide'), zeros(12), utf8('Ardoise a tresse'), u8(0)),
        boite('minf',
          boiteComplete('vmhd', 0, 1, u16(0), zeros(6)),
          boite('dinf', boiteComplete('dref', 0, 0, u32(1), boiteComplete('url ', 0, 1))),
          boite('stbl',
            boiteComplete('stsd', 0, 0, u32(1), entree),
            boiteComplete('stts', 0, 0, u32(series.length), ...series.map(([n, d]) => concat([u32(n), u32(d)]))),
            boiteComplete('stss', 0, 0, u32(syncs.length), ...syncs.map(u32)),
            boiteComplete('stsc', 0, 0, u32(1), u32(1), u32(echs.length), u32(1)),
            boiteComplete('stsz', 0, 0, u32(0), u32(echs.length), ...echs.map((e) => u32(e.octets.length))),
            boiteComplete('stco', 0, 0, u32(1), u32(decalageDonnees)))))),
    udta);

  const ftyp = boite('ftyp', typeBoite('isom'), u32(512), typeBoite('isom'), typeBoite('iso2'), typeBoite('av01'), typeBoite('mp41'));
  const taille = moov(0).length;   // la taille de moov ne dépend pas du décalage : on la mesure, puis on le règle
  const decalage = ftyp.length + taille + 8;   // 8 : l'en-tête de mdat
  const donnees = concat(echs.map((e) => e.octets));
  return new Blob([ftyp, moov(decalage), u32(8 + donnees.length), typeBoite('mdat'), donnees], { type: 'video/mp4' });
}

  return { construitMP4 };
})();
const { construitMP4 } = EMBALLEUR_MP4;
