// Le schéma de l'action de σ₁ sur F_2 (fn.svg), dessiné avec le moteur réel : les lacets x₁ (rouge) et x₂ (vert) avant et après σ₁
// (film conforme de la tresse [1], image de départ et image d'arrivée). Lancer depuis la racine du dépôt, après web/construit.sh :
//   node imgs/schemas/schema_fn.js
const fs = require('fs'), path = require('path');
require(path.join(__dirname, '..', '..', 'web', 'ardoise_lib.js'));
const a = globalThis.ardoise;
let premiere = null, derniere = null;
a.film('conforme', [1], (im, k) => { if (k === 0) premiere = im; derniere = im; });

const COULEURS = ['#d92626', '#1a9926', '#2640d9', '#bf9900', '#a626a6'];
const ENCRE = '#1d2330', GRIS = '#626b7d';
const echelle = 0.235;
const place = (x0) => ({ X: (x) => (x0 + echelle * (x - 60)).toFixed(1), Y: (y) => (52 + echelle * (y - 100)).toFixed(1) });

function panneau(im, x0) {
  const { X, Y } = place(x0);
  let s = '';
  im.lacets.forEach((l, i) => {
    let d = '';
    for (let k = 0; k < l.length; k += 8) d += `${d ? ' L' : 'M'}${X(l[k])},${Y(l[k + 1])}`;
    d += ` L${X(l[l.length - 2])},${Y(l[l.length - 1])}`;
    s += `<path d="${d}" fill="none" stroke="${COULEURS[i]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>\n`;
  });
  for (let k = 0; k < im.trous.length; k += 2) s += `<circle cx="${X(im.trous[k])}" cy="${Y(im.trous[k + 1])}" r="4.5" fill="${ENCRE}"/>\n`;
  s += `<circle cx="${X(im.clou[0])}" cy="${Y(im.clou[1])}" r="5.5" fill="${ENCRE}"/>\n`;
  s += `<text x="${(+X(im.clou[0]) + 9).toFixed(1)}" y="${(+Y(im.clou[1]) + 4).toFixed(1)}" font-size="11" fill="${ENCRE}">clou</text>\n`;
  return s;
}

const texte = (x, y, t, o = {}) => `<text x="${x}" y="${y}" text-anchor="${o.ancre || 'middle'}" font-size="${o.taille || 12}" fill="${o.couleur || ENCRE}" ${o.style || ''}>${t}</text>\n`;
let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 250" width="440" height="250" font-family="system-ui, -apple-system, 'Segoe UI', sans-serif" font-size="12">
<title>Action d'une tresse sur le groupe libre</title>
<defs><marker id="pointe" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${ENCRE}"/></marker></defs>
<rect width="440" height="250" fill="#ffffff"/>
`;
svg += texte(90, 26, 'départ', { taille: 14, style: 'font-weight="600"' }) + texte(90, 44, 'x₁ (rouge) et x₂ (vert)', { couleur: GRIS });
svg += panneau(premiere, 10);
svg += `<path d="M192,125 L236,125" stroke="${ENCRE}" stroke-width="1.6" fill="none" marker-end="url(#pointe)"/>\n` + texte(214, 117, 'σ₁', { taille: 11 });
svg += texte(335, 26, 'après σ₁', { taille: 14, style: 'font-weight="600"' }) + texte(335, 44, 'les lacets ont suivi les trous', { couleur: GRIS });
svg += panneau(derniere, 250);
svg += texte(335, 224, 'x₁ ↦ x₁ x₂ x₁⁻¹', { taille: 14, couleur: COULEURS[0], style: 'font-weight="600"' });
svg += texte(335, 242, 'x₂ ↦ x₁', { taille: 14, couleur: COULEURS[1], style: 'font-weight="600"' });
svg += texte(90, 224, 'des lacets issus du clou,', { couleur: GRIS }) + texte(90, 242, 'un par trou', { couleur: GRIS });
svg += '</svg>\n';
for (const dossier of [__dirname, path.join(__dirname, '..', '..', 'web', 'schemas')]) {
  fs.mkdirSync(dossier, { recursive: true });
  fs.writeFileSync(path.join(dossier, 'fn.svg'), svg);
}
console.log('écrit : fn.svg (ici et dans web/schemas/)', svg.length, 'octets');
