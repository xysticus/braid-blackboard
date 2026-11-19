// Le Web Worker : charge la bibliothèque OCaml compilée (ardoise_lib.js, voir construit.sh), calcule l'image fixe
// puis le film d'un mode, et envoie les images au fil de l'eau. Un worker par mode ; la page le tue (terminate)
// quand le mot change.
importScripts('ardoise_lib.js');

function enFloat32(image) {
  return {
    lacets: Array.from(image.lacets, (l) => Float32Array.from(l)),
    trous: Float32Array.from(image.trous),
    fixes: Float32Array.from(image.fixes),
    clou: Float32Array.from(image.clou),
    ecart: image.ecart,
  };
}

function tampons(image) {
  return [...image.lacets.map((l) => l.buffer), image.trous.buffer, image.fixes.buffer, image.clou.buffer];
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
