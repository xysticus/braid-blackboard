// Le Web Worker : charge la bibliothèque OCaml compilée (ardoise_lib.js, voir construit.sh), calcule l'image fixe
// puis le film d'un mode, et envoie les images au fil de l'eau. Un worker par mode ; la page le tue (terminate)
// quand le mot change.
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

onmessage = (e) => {
  const { mode, mot } = e.data;
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
