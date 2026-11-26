'use strict';
// La tresse en 3D, en WebGL 2 écrit à la main, sans dépendance. Voir etude_idees_pedagogiques.md (« la 3D ») et README.md.
//
// Le repère : x suit les positions des brins (de gauche à droite), y monte (le temps descend : la première lettre est en
// haut), z vient vers la personne qui regarde de face. Une position (X, Y) du film des méandres, y vers le bas de l'écran,
// devient (x = X, z = Y). Les deux conventions de la page s'en déduisent :
//   - de face, on voit le diagramme de tresse : pour σ_i positif, le brin qui va de droite à gauche passe devant ;
//   - de dessus, on voit le film : σ_i positif est un demi-tour horaire.
//
// Une tranche par lettre, séparée de ses voisines par un disque ; un seul grand cylindre contient la tresse. Dans la
// tranche de σ_i, les brins aux positions i et i + 1 font un demi-tour en cercle autour de l'axe vertical du milieu ;
// les autres descendent tout droit.
//
// Unités : l'écart entre deux positions voisines vaut 1.

const Vue3D = (() => {
  const HAUTEUR_TRANCHE = 1.5;
  const RAYON_BRIN = 0.11;
  const RAYON_SECTEUR = 0.5 + 1.8 * RAYON_BRIN;     // le petit cylindre d'un croisement
  const PAS_PAR_TRANCHE = 40;                       // échantillons d'un brin sur la hauteur d'une tranche
  const COTES_BRIN = 20;                            // côtés de la section d'un brin
  const COTES_CERCLE = 96;                          // côtés des disques et des cylindres
  const CHAMP = 30 * Math.PI / 180;                 // champ vertical de la caméra
  const SITE_MAX = Math.PI / 2 - 0.001;

  const nbBrins = (mot) => mot.reduce((a, k) => Math.max(a, Math.abs(k)), 0) + 1;

  // ------------------------------------------------------------ la géométrie de la tresse (sans WebGL)

  // L'adoucissement du demi-tour : vitesse nulle aux deux disques, le brin y est donc vertical et les tranches se raccordent.
  const adoucit = (t) => t * t * (3 - 2 * t);

  // Pour chaque brin (numéroté par sa position de départ, qui fixe sa couleur), la suite de ses points de haut en bas.
  // Renvoie { n, m, hauteur, brins: [[[x, y, z], …], …], secteurs: [{ x, haut, bas }] } ; la tresse est centrée en (0, 0, 0).
  function geometrie(mot) {
    const n = nbBrins(mot), m = mot.length, hauteur = Math.max(m, 1) * HAUTEUR_TRANCHE;
    const xDe = (position) => position - (n - 1) / 2;
    const yDe = (tranche) => hauteur / 2 - tranche * HAUTEUR_TRANCHE;
    const occupant = Array.from({ length: n }, (_, i) => i);     // occupant[position] = brin qui s'y trouve
    const brins = Array.from({ length: n }, (_, i) => [[xDe(i), yDe(0), 0]]);
    const secteurs = [];
    for (let j = 0; j < Math.max(m, 1); j++) {
      const k = mot[j] || 0, i = Math.abs(k) - 1;
      for (let position = 0; position < n; position++) {
        const brin = brins[occupant[position]];
        for (let p = 1; p <= PAS_PAR_TRANCHE; p++) {
          const t = p / PAS_PAR_TRANCHE, y = yDe(j + t);
          if (k !== 0 && (position === i || position === i + 1)) {
            // le brin de gauche part de l'angle π, celui de droite de l'angle 0 ; ils tournent de π, dans le sens de k
            const angle = (position === i ? Math.PI : 0) + Math.sign(k) * Math.PI * adoucit(t);
            brin.push([xDe(i + 0.5) + 0.5 * Math.cos(angle), y, 0.5 * Math.sin(angle)]);
          } else brin.push([xDe(position), y, 0]);
        }
      }
      if (k !== 0) {
        [occupant[i], occupant[i + 1]] = [occupant[i + 1], occupant[i]];
        secteurs.push({ x: xDe(i + 0.5), haut: yDe(j), bas: yDe(j + 1) });
      }
    }
    return { n, m, hauteur, brins, secteurs, rayon: (n - 1) / 2 + 0.7, disques: Array.from({ length: m + 1 }, (_, j) => yDe(j)) };
  }

  // ------------------------------------------------------------ vecteurs et matrices

  const moins = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const vectoriel = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const scalaire = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const unitaire = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };

  // matrices 4 × 4 rangées par colonnes, comme les veut WebGL
  function produit(a, b) {
    const c = new Float32Array(16);
    for (let col = 0; col < 4; col++)
      for (let lig = 0; lig < 4; lig++)
        for (let k = 0; k < 4; k++) c[4 * col + lig] += a[4 * k + lig] * b[4 * col + k];
    return c;
  }

  function perspective(champ, rapport, pres, loin) {
    const f = 1 / Math.tan(champ / 2);
    return new Float32Array([f / rapport, 0, 0, 0, 0, f, 0, 0, 0, 0, (loin + pres) / (pres - loin), -1, 0, 0, 2 * loin * pres / (pres - loin), 0]);
  }

  // La caméra tourne autour du centre : azimut (autour de la verticale, 0 : de face) et site (hauteur, π/2 : de dessus).
  function camera(azimut, site, distance) {
    const arriere = [Math.cos(site) * Math.sin(azimut), Math.sin(site), Math.cos(site) * Math.cos(azimut)];
    const droite = [Math.cos(azimut), 0, -Math.sin(azimut)];
    const dessus = vectoriel(arriere, droite);
    const oeil = arriere.map((c) => c * distance);
    const matrice = new Float32Array([
      droite[0], dessus[0], arriere[0], 0, droite[1], dessus[1], arriere[1], 0, droite[2], dessus[2], arriere[2], 0,
      -scalaire(droite, oeil), -scalaire(dessus, oeil), -scalaire(arriere, oeil), 1]);
    return { matrice, oeil, droite, dessus, arriere };
  }

  // ------------------------------------------------------------ maillages : { positions, normales, indices }

  // Le tube autour d'un brin. La tangente n'est jamais parallèle à z (le brin descend toujours) : le repère de la section
  // se calcule en chaque point, sans torsion. Les deux bouts sont fermés.
  function tube(points) {
    const positions = [], normales = [], indices = [];
    const tangentes = points.map((_, i) => unitaire(moins(points[Math.min(i + 1, points.length - 1)], points[Math.max(i - 1, 0)])));
    // aux deux bouts, le brin est vertical
    tangentes[0] = tangentes[tangentes.length - 1] = [0, -1, 0];
    points.forEach((p, i) => {
      const u = unitaire(vectoriel(tangentes[i], [0, 0, 1])), v = vectoriel(tangentes[i], u);
      for (let c = 0; c < COTES_BRIN; c++) {
        const a = 2 * Math.PI * c / COTES_BRIN;
        const d = [0, 1, 2].map((q) => Math.cos(a) * u[q] + Math.sin(a) * v[q]);
        positions.push(p[0] + RAYON_BRIN * d[0], p[1] + RAYON_BRIN * d[1], p[2] + RAYON_BRIN * d[2]);
        normales.push(...d);
      }
    });
    for (let i = 0; i + 1 < points.length; i++)
      for (let c = 0; c < COTES_BRIN; c++) {
        const a = i * COTES_BRIN + c, b = i * COTES_BRIN + (c + 1) % COTES_BRIN;
        indices.push(a, a + COTES_BRIN, b, b, a + COTES_BRIN, b + COTES_BRIN);
      }
    for (const [bout, anneau, normale] of [[points[0], 0, [0, 1, 0]], [points[points.length - 1], points.length - 1, [0, -1, 0]]]) {
      const centre = positions.length / 3;
      positions.push(...bout); normales.push(...normale);
      for (let c = 0; c < COTES_BRIN; c++) {
        const q = 3 * (anneau * COTES_BRIN + c);
        positions.push(positions[q], positions[q + 1], positions[q + 2]); normales.push(...normale);
      }
      for (let c = 0; c < COTES_BRIN; c++) indices.push(centre, centre + 1 + c, centre + 1 + (c + 1) % COTES_BRIN);
    }
    return { positions, normales, indices };
  }

  const cercle = (c) => [Math.cos(2 * Math.PI * c / COTES_CERCLE), Math.sin(2 * Math.PI * c / COTES_CERCLE)];

  // La paroi d'un cylindre vertical d'axe (x, ·, 0), sans ses deux bases.
  function paroi(x, rayon, haut, bas) {
    const positions = [], normales = [], indices = [];
    for (let c = 0; c <= COTES_CERCLE; c++) {
      const [co, si] = cercle(c);
      for (const y of [haut, bas]) { positions.push(x + rayon * co, y, rayon * si); normales.push(co, 0, si); }
    }
    for (let c = 0; c < COTES_CERCLE; c++) indices.push(2 * c, 2 * c + 1, 2 * c + 2, 2 * c + 2, 2 * c + 1, 2 * c + 3);
    return { positions, normales, indices };
  }

  // Un disque horizontal plein, et son bord (une ligne fermée).
  function disque(x, rayon, y) {
    const positions = [x, y, 0], normales = [0, 1, 0], indices = [];
    for (let c = 0; c < COTES_CERCLE; c++) {
      const [co, si] = cercle(c);
      positions.push(x + rayon * co, y, rayon * si); normales.push(0, 1, 0);
      indices.push(0, 1 + c, 1 + (c + 1) % COTES_CERCLE);
    }
    return { positions, normales, indices };
  }

  function bord(x, rayon, y) {
    const d = disque(x, rayon, y);
    d.indices = [];
    for (let c = 0; c < COTES_CERCLE; c++) d.indices.push(1 + c, 1 + (c + 1) % COTES_CERCLE);
    return d;
  }

  // ------------------------------------------------------------ WebGL

  const SOMMETS = `#version 300 es
    layout(location = 0) in vec3 position;
    layout(location = 1) in vec3 normale;
    uniform mat4 matrice;
    out vec3 vNormale;
    out vec3 vPosition;
    void main() { vNormale = normale; vPosition = position; gl_Position = matrice * vec4(position, 1.0); }`;

  // mode 0 : un brin éclairé (la lumière suit la caméra) ; mode 1 : une paroi de verre, plus visible sur ses bords ;
  // mode 2 : une couleur unie (disques et bords)
  const FRAGMENTS = `#version 300 es
    precision mediump float;
    uniform vec4 couleur;
    uniform int mode;
    uniform vec3 oeil;
    uniform vec3 lumiere;
    in vec3 vNormale;
    in vec3 vPosition;
    out vec4 sortie;
    void main() {
      if (mode == 2) { sortie = couleur; return; }
      vec3 n = normalize(vNormale);
      vec3 vue = normalize(oeil - vPosition);
      if (mode == 1) {
        float rasant = 1.0 - abs(dot(n, vue));
        sortie = vec4(couleur.rgb, couleur.a * (0.25 + 2.5 * rasant * rasant * rasant));
        return;
      }
      float diffus = max(dot(n, lumiere), 0.0);
      float reflet = pow(max(dot(n, normalize(lumiere + vue)), 0.0), 40.0);
      sortie = vec4(couleur.rgb * (0.42 + 0.62 * diffus) + vec3(0.25 * reflet), couleur.a);
    }`;

  function programme(gl) {
    const p = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER, SOMMETS], [gl.FRAGMENT_SHADER, FRAGMENTS]]) {
      const s = gl.createShader(type);
      gl.shaderSource(s, source);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      gl.attachShader(p, s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  function charge(gl, maillage) {
    const vao = gl.createVertexArray(), tampons = [];
    gl.bindVertexArray(vao);
    [maillage.positions, maillage.normales].forEach((donnees, attribut) => {
      const t = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, t);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(donnees), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(attribut);
      gl.vertexAttribPointer(attribut, 3, gl.FLOAT, false, 0, 0);
      tampons.push(t);
    });
    const t = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, t);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint32Array(maillage.indices), gl.STATIC_DRAW);
    tampons.push(t);
    gl.bindVertexArray(null);
    return { vao, tampons, taille: maillage.indices.length };
  }

  const rvb = (hexa) => [1, 3, 5].map((i) => parseInt(hexa.slice(i, i + 2), 16) / 255);

  // ------------------------------------------------------------ la vue : un canvas, une tresse, une caméra

  // cree(canvas, { survol }) : survol(j) est appelé quand la personne désigne le croisement de la lettre j (ou null).
  // Renvoie null si le navigateur n'a pas WebGL 2.
  function cree(canvas, { survol = () => {} } = {}) {
    const gl = canvas.getContext('webgl2', { antialias: true, premultipliedAlpha: false });
    if (!gl) return null;
    let prog, uniformes;
    let geo = null, couleurs = [], teintes = { fond: '#ffffff', verre: '#808080', accent: '#2f6fde' };
    let maillages = null;
    let azimut = 0.45, site = 0.3, zoom = 1;
    let designe = null;            // la lettre mise en évidence
    let demande = false;

    function initialise() {
      prog = programme(gl);
      uniformes = {};
      for (const nom of ['matrice', 'couleur', 'mode', 'oeil', 'lumiere']) uniformes[nom] = gl.getUniformLocation(prog, nom);
    }

    function libere() {
      if (!maillages) return;
      for (const m of [maillages.paroi, ...maillages.brins, ...maillages.disques, ...maillages.bords, ...maillages.secteurs.flatMap((s) => Object.values(s))]) {
        gl.deleteVertexArray(m.vao);
        m.tampons.forEach((t) => gl.deleteBuffer(t));
      }
      maillages = null;
    }

    function construit() {
      libere();
      if (!geo) return;
      const haut = geo.hauteur / 2;
      maillages = {
        brins: geo.brins.map((points) => charge(gl, tube(points))),
        paroi: charge(gl, paroi(0, geo.rayon, haut, -haut)),
        disques: geo.disques.map((y) => charge(gl, disque(0, geo.rayon, y))),
        bords: geo.disques.map((y) => charge(gl, bord(0, geo.rayon, y))),
        secteurs: geo.secteurs.map((s) => ({
          paroi: charge(gl, paroi(s.x, RAYON_SECTEUR, s.haut, s.bas)),
          haut: charge(gl, bord(s.x, RAYON_SECTEUR, s.haut)),
          bas: charge(gl, bord(s.x, RAYON_SECTEUR, s.bas)),
          disqueHaut: charge(gl, bord(0, geo.rayon, s.haut)),
          disqueBas: charge(gl, bord(0, geo.rayon, s.bas)),
        })),
      };
    }

    // La distance à laquelle la sphère qui contient la tresse tient dans l'image (zoom = 1) ; une tresse longue et vue de
    // face tient mieux que sa sphère : on cadre sa hauteur et sa largeur, avec une marge pour la rotation.
    function distance() {
      const rapport = canvas.clientWidth / Math.max(canvas.clientHeight, 1);
      const t = Math.tan(CHAMP / 2);
      return (Math.max(0.56 * geo.hauteur / t, 1.12 * geo.rayon / (t * rapport)) + geo.rayon) / zoom;
    }

    function vue() {
      const d = distance(), c = camera(azimut, site, d), englobante = Math.hypot(geo.rayon, geo.hauteur / 2) + 1;
      const rapport = canvas.width / Math.max(canvas.height, 1);
      return { ...c, matrice: produit(perspective(CHAMP, rapport, Math.max(0.1, d - englobante), d + englobante), c.matrice) };
    }

    function trace(m, couleur, alpha, mode, primitive = gl.TRIANGLES) {
      gl.uniform4f(uniformes.couleur, ...rvb(couleur), alpha);
      gl.uniform1i(uniformes.mode, mode);
      gl.bindVertexArray(m.vao);
      gl.drawElements(primitive, m.taille, gl.UNSIGNED_INT, 0);
    }

    function dessine() {
      demande = false;
      const dpr = window.devicePixelRatio || 1;
      const l = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
      if (canvas.width !== l || canvas.height !== h) { canvas.width = l; canvas.height = h; }
      gl.viewport(0, 0, l, h);
      gl.clearColor(...rvb(teintes.fond), 1);
      gl.depthMask(true);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      if (!maillages) return;
      const v = vue();
      gl.useProgram(prog);
      gl.uniformMatrix4fv(uniformes.matrice, false, v.matrice);
      gl.uniform3f(uniformes.oeil, ...v.oeil);
      gl.uniform3f(uniformes.lumiere, ...unitaire([0, 1, 2].map((q) => 0.8 * v.arriere[q] + 0.55 * v.dessus[q] - 0.35 * v.droite[q])));

      // les brins, opaques
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      maillages.brins.forEach((m, i) => trace(m, couleurs[i % couleurs.length], 1, 0));

      // le verre, par-dessus : il ne masque pas ce qui est derrière lui
      gl.enable(gl.BLEND);
      gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
      trace(maillages.paroi, teintes.verre, 0.07, 1);
      maillages.disques.forEach((m) => trace(m, teintes.verre, 0.035, 2));
      maillages.bords.forEach((m) => trace(m, teintes.verre, 0.4, 2, gl.LINES));
      const s = designe === null ? null : maillages.secteurs[designe];
      if (s) {
        trace(s.paroi, teintes.accent, 0.22, 1);
        for (const m of [s.haut, s.bas, s.disqueHaut, s.disqueBas]) trace(m, teintes.accent, 1, 2, gl.LINES);
      }
      gl.depthMask(true);
      gl.bindVertexArray(null);
    }

    function redessine() {
      if (!demande) { demande = true; requestAnimationFrame(dessine); }
    }

    // La lettre dont le petit cylindre est le premier coupé par le rayon qui part de l'œil et passe au point (cx, cy) de
    // la fenêtre ; null s'il n'en coupe aucun.
    function croisementSous(cx, cy) {
      if (!geo || geo.secteurs.length === 0) return null;
      const cadre = canvas.getBoundingClientRect(), v = vue(), t = Math.tan(CHAMP / 2);
      const u = (2 * (cx - cadre.left) / cadre.width - 1) * t * cadre.width / cadre.height;
      const w = (1 - 2 * (cy - cadre.top) / cadre.height) * t;
      const r = [0, 1, 2].map((q) => u * v.droite[q] + w * v.dessus[q] - v.arriere[q]);
      let meilleur = null, proche = Infinity;
      geo.secteurs.forEach((s, j) => {
        const ox = v.oeil[0] - s.x, oz = v.oeil[2];
        const touches = [];
        const a = r[0] * r[0] + r[2] * r[2], b = ox * r[0] + oz * r[2], c = ox * ox + oz * oz - RAYON_SECTEUR ** 2;
        if (a > 1e-12 && b * b - a * c >= 0) {          // la paroi
          for (const signe of [-1, 1]) {
            const d = (-b + signe * Math.sqrt(b * b - a * c)) / a, y = v.oeil[1] + d * r[1];
            if (y <= s.haut && y >= s.bas) touches.push(d);
          }
        }
        if (Math.abs(r[1]) > 1e-12) {                   // les deux bases (la vue de dessus)
          for (const y of [s.haut, s.bas]) {
            const d = (y - v.oeil[1]) / r[1];
            if (Math.hypot(ox + d * r[0], oz + d * r[2]) <= RAYON_SECTEUR) touches.push(d);
          }
        }
        for (const d of touches) if (d > 0 && d < proche) { proche = d; meilleur = j; }
      });
      return meilleur;
    }

    // ---------------------------------------------------------- tourner et zoomer : souris, molette, doigts

    const pointeurs = new Map();
    let parcouru = 0;
    const ecartDoigts = () => { const [a, b] = [...pointeurs.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
    const zoome = (facteur) => { zoom = Math.min(12, Math.max(0.4, zoom * facteur)); redessine(); };

    canvas.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      canvas.setPointerCapture(e.pointerId);
      if (pointeurs.size === 0) parcouru = 0; else parcouru = Infinity;     // deux doigts : ce n'est pas un toucher
      pointeurs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    });
    canvas.addEventListener('pointermove', (e) => {
      const p = pointeurs.get(e.pointerId);
      if (!p) { if (e.pointerType === 'mouse') survol(croisementSous(e.clientX, e.clientY)); return; }
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      if (pointeurs.size === 2) {
        const avant = ecartDoigts();
        p.x = e.clientX; p.y = e.clientY;
        if (avant > 0) zoome(ecartDoigts() / avant);
      } else if (pointeurs.size === 1) {
        p.x = e.clientX; p.y = e.clientY;
        parcouru += Math.hypot(dx, dy);
        azimut -= dx * 0.008;
        site = Math.min(SITE_MAX, Math.max(-SITE_MAX, site + dy * 0.008));
        redessine();
      }
    });
    const relache = (e) => {
      if (!pointeurs.delete(e.pointerId)) return;
      // un clic ou un toucher sans glisser désigne un croisement (au doigt, il n'y a pas de survol)
      if (e.type === 'pointerup' && pointeurs.size === 0 && parcouru < 6) survol(croisementSous(e.clientX, e.clientY));
    };
    canvas.addEventListener('pointerup', relache);
    canvas.addEventListener('pointercancel', relache);
    canvas.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && pointeurs.size === 0) survol(null); });
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      zoome(Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015)));
    }, { passive: false });
    canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); maillages = null; });
    canvas.addEventListener('webglcontextrestored', () => { initialise(); construit(); redessine(); });
    new ResizeObserver(redessine).observe(canvas);

    initialise();
    return {
      montre(mot, nouvellesCouleurs) {
        geo = geometrie(mot);
        couleurs = nouvellesCouleurs;
        designe = null;
        zoom = 1;
        construit();
        redessine();
      },
      teinte(nouvelles) { teintes = { ...teintes, ...nouvelles }; redessine(); },
      designe(j) { if (j !== designe) { designe = j; redessine(); } },
      oriente(a, s, z = zoom) { azimut = a; site = Math.min(SITE_MAX, Math.max(-SITE_MAX, s)); zoom = z; redessine(); },
      croisementSous,
    };
  }

  return { cree, geometrie, nbBrins };
})();

if (typeof module !== 'undefined') module.exports = Vue3D;
