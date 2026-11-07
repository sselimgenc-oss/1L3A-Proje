/* Ofis · çevre ve mobilya sprite'ları (hepsi kodla çizilir; elle yazılmış piksel sanatı, dış varlık yok). */
(function () {
  'use strict';
  const O = window.OFIS, HW = O.HW, HH = O.HH;
  const C = O.C, shade = O.shade, mix = O.mix, mat = O.mat, tspr = O.tspr, fspr = O.fspr, h2 = O.h2;
  const S = (O.S = {});
  const cache = {};
  const memo = (k, f) => cache[k] || (cache[k] = f());
  S.memo = memo;

  const INK = '#2a2230';

  /* ================= ZEMİN ================= */
  const GR = ['#5b9c4e', '#65a755', '#548f48'].map(C);
  const GRD = C('#467c3d'), GRL = C('#79b863');
  function tileGrass(P, sx, sy, x, y) {
    const t = h2(x, y, 3), base = GR[t < 0.34 ? 0 : t < 0.67 ? 1 : 2];
    P.diamond(sx, sy, (px, py) => {
      const n = h2(px, py, 7);
      P.set(px, py, n < 0.06 ? GRD : n > 0.955 ? GRL : base);
    });
    // çimen tutamları ve çiçekler
    for (let i = 0; i < 3; i++) {
      const a = h2(x, y, 20 + i), b = h2(x, y, 40 + i);
      const px = sx + Math.round((a - 0.5) * 30), py = sy + 4 + Math.round(b * 12);
      if (Math.abs(px - sx) / HW + Math.abs(py - sy - HH) / HH < 0.78) { P.set(px, py, GRD); P.set(px + 1, py - 1, GRD); P.set(px + 2, py, GRD); }
    }
    const f = h2(x, y, 99);
    if (f < 0.09) { const px = sx + Math.round((h2(x, y, 5) - 0.5) * 22), py = sy + 6 + Math.round(h2(x, y, 6) * 8); P.set(px, py, f < 0.03 ? '#fff4d6' : f < 0.06 ? '#ffd24a' : '#f5a3c0'); P.set(px, py + 1, '#4b8238'); }
  }
  S.floorGrass = tileGrass;
  const WOODS = {};
  function floorPx(kind, base, base2, gu, gv, px, py) {
    const n = h2(px, py, 11);
    switch (kind) {
      case 'wood': {
        const pl = Math.floor(gv * 3), fr = gv * 3 - pl, t = 0.9 + 0.2 * h2(pl, Math.floor(gu * 0.5 + h2(pl, 1, 2) * 3), 5);
        let c = shade(base, t);
        if (fr < 0.1) c = shade(base, 0.7);
        const sp = Math.floor(gu * 0.5 + h2(pl, 1, 2) * 3); if (Math.abs(gu * 0.5 + h2(pl, 1, 2) * 3 - sp) < 0.03) c = shade(base, 0.72);
        return n > 0.93 ? shade(c, 1.07) : c;
      }
      case 'carpet': return n < 0.1 ? shade(base, 0.93) : n > 0.9 ? shade(base, 1.07) : C(base);
      case 'tile': {
        const a = Math.floor(gu * 2), b = Math.floor(gv * 2), fa = gu * 2 - a, fb = gv * 2 - b;
        if (fa < 0.07 || fb < 0.07) return shade(base, 0.82);
        return ((a + b) & 1) ? C(base2 || base) : C(base);
      }
      case 'concrete': return n < 0.12 ? shade(base, 0.92) : n > 0.9 ? shade(base, 1.06) : C(base);
      case 'stone': {
        const rowi = Math.floor(gv * 2), fr = gv * 2 - rowi, off = (rowi & 1) ? 0.5 : 0, cu = gu * 1 + off, ci = Math.floor(cu), fu = cu - ci;
        if (fr < 0.09 || fu < 0.06) return shade(base, 0.8);
        return shade(base, 0.94 + 0.12 * h2(ci, rowi, 3));
      }
      case 'asph': return n < 0.15 ? shade(base, 0.9) : n > 0.93 ? shade(base, 1.1) : C(base);
      case 'parquet': { // balıksırtı parke (Makam)
        const u = gu * 3, v = gv * 3, i = Math.floor(u), j = Math.floor(v), fu = u - i, fv = v - j, a = (i + j) & 1, f = a ? fv : fu, strip = Math.floor(f * 2), fr = f * 2 - strip;
        let c = shade(base, 0.88 + 0.24 * h2(i, j, strip + 3));
        if (fr < 0.16 || (a ? fu : fv) < 0.08) c = shade(base, 0.66);
        return n > 0.94 ? shade(c, 1.08) : c;
      }
      case 'grate': { // metal ızgara zemin (sunucu odası)
        const u = gu * 4, v = gv * 4, fu = u - Math.floor(u), fv = v - Math.floor(v);
        if (fu < 0.2 || fv < 0.2) return n > 0.9 ? shade(base, 1.55) : shade(base, 1.32);
        return (fu > 0.45 && fv > 0.45) ? shade(base, 0.42) : shade(base, 0.62);
      }
      case 'fayans': { // çay ocağı: desenli seramik
        const u = gu * 3, v = gv * 3, i = Math.floor(u), j = Math.floor(v), fu = u - i, fv = v - j;
        if (fu < 0.07 || fv < 0.07) return shade(base, 0.8);
        if ((i + j) & 1) return (Math.abs(fu - 0.5) + Math.abs(fv - 0.5) < 0.3) ? shade(base2, 1.12) : C(base2);
        return n > 0.96 ? '#ffffff' : C(base);
      }
      case 'deck': { const pl = Math.floor(gv * 4), fr = gv * 4 - pl; if (fr < 0.1) return shade(base, 0.7); const sp = Math.floor(gu * 0.5 + h2(pl, 1, 9) * 3); return Math.abs(gu * 0.5 + h2(pl, 1, 9) * 3 - sp) < 0.04 ? shade(base, 0.74) : shade(base, 0.93 + 0.14 * h2(pl, sp, 4)); }
      case 'water': {
        const w = Math.sin((gu * 2.3 + gv * 1.1) * 3.1) + Math.sin((gu - gv * 1.7) * 4.3), t = (w + 2) / 4;
        let c = mix(base, base2 || base, t < 0.5 ? 0.15 : t < 0.78 ? 0.5 : 0.85);
        if (n > 0.975) c = C('#d8fbff');
        return c;
      }
      default: return C(base);
    }
  }
  S.floorTile = function (P, sx, sy, x, y, kind, base, base2, edge) {
    P.diamond(sx, sy, (px, py, u, v) => {
      let c = floorPx(kind, base, base2, x + u, y + v, px, py);
      if (kind === 'water' && edge) { if (edge.n && v < 0.2) c = shade(c, 0.62); if (edge.w && u < 0.2) c = shade(c, 0.74); }
      P.set(px, py, c);
    });
  };

  /* ================= DUVAR / BÖLME ================= */
  const WALL = '#e8eef0', WALLD = '#c9d4d8';
  /* arka duvar, u yönünde uzanır (v=0 çizgisi); yüzü sol yüz */
  S.wallBH = function (accent, deco, seed) {
    return memo('wBH' + accent + deco + seed, () => tspr(54, I => {
      const m = mat(WALL), P = I.P;
      I.box(0, -0.2, 1, 0, 0, 48, m, { noedge: true });
      // lambri + şerit
      I.fl(0, 1, 0, 0, 13, accent);
      I.fl(0, 1, 0, 13, 15, shade(accent, 1.25));
      I.fl(0, 1, 0, 0, 2, shade(accent, 0.6));
      I.fl(0, 1, 0, 45, 48, WALLD);
      // üst kenar çizgileri
      const a = I.p(0, 0, 48), b = I.p(1, 0, 48), c = I.p(0, -0.2, 48), d = I.p(1, -0.2, 48);
      P.line(a[0], a[1], b[0], b[1], INK); P.line(c[0], c[1], d[0], d[1], shade(WALL, 0.7));
      P.line(a[0], a[1], c[0], c[1], INK); P.line(b[0], b[1], d[0], d[1], INK);
      if (deco === 'win') { winFrame(I, 'L'); }
      if (deco === 'pic') picture(I, 'L', seed);
      if (deco === 'clock') clock(I, 'L');
    }));
  };
  S.wallBV = function (accent, deco, seed) {
    return memo('wBV' + accent + deco + seed, () => tspr(54, I => {
      const m = mat(WALL), P = I.P;
      I.box(-0.2, 0, 0, 1, 0, 48, m, { noedge: true });
      I.fr(0, 0, 1, 0, 13, accent);
      I.fr(0, 0, 1, 13, 15, shade(accent, 1.25));
      I.fr(0, 0, 1, 0, 2, shade(accent, 0.6));
      I.fr(0, 0, 1, 45, 48, WALLD);
      const a = I.p(0, 0, 48), b = I.p(0, 1, 48), c = I.p(-0.2, 0, 48), d = I.p(-0.2, 1, 48);
      P.line(a[0], a[1], b[0], b[1], INK); P.line(c[0], c[1], d[0], d[1], shade(WALL, 0.7));
      P.line(a[0], a[1], c[0], c[1], INK); P.line(b[0], b[1], d[0], d[1], INK);
      if (deco === 'win') { winFrame(I, 'R'); }
      if (deco === 'pic') picture(I, 'R', seed);
      if (deco === 'clock') clock(I, 'R');
    }));
  };
  S.wallCorner = function (accent) {
    return memo('wC' + accent, () => tspr(54, I => {
      const m = mat(WALL), P = I.P;
      I.box(-0.2, -0.2, 0, 0, 0, 48, m, { noedge: true });
      const a = I.p(-0.2, -0.2, 48), b = I.p(0, -0.2, 48), c = I.p(0, 0, 48), d = I.p(-0.2, 0, 48);
      P.poly([a, b, c, d], mat(WALL).t);
      P.line(c[0], c[1], I.p(0, 0, 0)[0], I.p(0, 0, 0)[1], INK);
      I.fl(-0.2, 0, 0, 0, 13, accent); I.fr(0, -0.2, 0, 0, 13, shade(accent, 0.7));
    }));
  };
  function panel(I, side, s0, s1, z0, z1, c) { side === 'L' ? I.fl(s0, s1, 0, z0, z1, c) : I.fr(0, s0, s1, z0, z1, c); }
  function winFrame(I, side) {
    panel(I, side, 0.1, 0.9, 17, 41, '#fbf7ec');       // çerçeve
    panel(I, side, 0.15, 0.85, 19, 39, '#1c2a4a');     // cam (gün ışığı pencere katmanında)
    panel(I, side, 0.08, 0.92, 15, 17, '#c9bfa6');     // denizlik
    panel(I, side, 0.49, 0.51, 19, 39, '#fbf7ec');
  }
  function picture(I, side, seed) {
    const r = O.rng(seed * 77 + 5), cols = ['#d4553b', '#3b82c4', '#e0a93a', '#3aa17a', '#8a63c9'];
    panel(I, side, 0.3, 0.7, 20, 36, '#7a5a3a');
    panel(I, side, 0.34, 0.66, 22, 34, '#f6eedb');
    const c1 = cols[Math.floor(r() * 5)], c2 = cols[Math.floor(r() * 5)];
    panel(I, side, 0.37, 0.52, 23, 31, c1); panel(I, side, 0.48, 0.63, 25, 33, c2);
  }
  function clock(I, side) {
    panel(I, side, 0.42, 0.58, 28, 40, '#f4efe2'); panel(I, side, 0.46, 0.54, 30, 38, '#2a2230');
    panel(I, side, 0.49, 0.51, 31, 36, '#f4efe2');
  }
  /* pencere cam katmanı: gün saatine göre gökyüzü degradesi */
  S.windowGlass = function (side, sky) {
    return memo('wg' + side + sky.key, () => tspr(54, I => {
      const rows = 20;
      for (let i = 0; i < rows; i++) {
        const t = i / (rows - 1), c = mix(sky.top, sky.bot, t);
        panel(I, side, 0.15, 0.85, 39 - i - 0.0, 39 - i + 1, c);
      }
      // güneş/ay
      if (sky.orb) panel(I, side, 0.62, 0.7, 31, 35, sky.orb);
      panel(I, side, 0.49, 0.51, 19, 39, '#fbf7ec');
      // cam parlaması
      panel(I, side, 0.2, 0.26, 21, 34, C('#ffffff30'));
    }));
  };

  /* iç bölme (cam / dolu) */
  S.partH = function (type, accent) { // u boyunca, çizgi v=0 (karonun üst kenarı)
    return memo('pH2' + type + accent, () => tspr(32, I => {
      const P = I.P;
      if (type === 'solid') {
        const m = mat('#d9cdb4');
        I.box(0, -0.06, 1, 0.06, 0, 26, m, { noedge: true });
        I.fl(0, 1, 0.06, 0, 8, accent); I.fl(0, 1, 0.06, 8, 9, shade(accent, 1.3));
        const a = I.p(0, 0.06, 26), b = I.p(1, 0.06, 26); P.line(a[0], a[1], b[0], b[1], INK);
        const c = I.p(0, -0.06, 26), d = I.p(1, -0.06, 26); P.line(c[0], c[1], d[0], d[1], shade('#d9cdb4', 0.7));
        P.line(a[0], a[1], c[0], c[1], INK); P.line(b[0], b[1], d[0], d[1], INK);
      } else {
        const accC = accent;
        I.fl(0, 1, 0.05, 0, 20, C('#8fd0e044'));
        I.fl(0, 1, 0.05, 0, 20, C('#b6eaf322'));
        I.fl(0.1, 0.17, 0.05, 3, 18, C('#ffffff66')); I.fl(0.24, 0.27, 0.05, 3, 18, C('#ffffff48')); I.fl(0.62, 0.7, 0.05, 3, 18, C('#ffffff2a'));
        I.fl(0, 1, 0.05, 0, 2, '#dfe6ee'); I.fl(0, 1, 0.05, 18, 20, shade(accC, 1.25)); I.fl(0, 1, 0.05, 20, 21, '#f4f8fb');
        I.fl(0, 0.04, 0.05, 0, 21, '#e6edf3');
        const a = I.p(0, 0.05, 21), b = I.p(1, 0.05, 21); P.line(a[0], a[1], b[0], b[1], '#ffffff');
        const t1 = I.p(0, -0.05, 21), t2 = I.p(1, -0.05, 21); P.line(t1[0], t1[1], t2[0], t2[1], '#a9bccb');
        const e1 = I.p(0, 0.05, 0), e2 = I.p(0, 0.05, 21); P.line(e1[0], e1[1], e2[0], e2[1], '#c3cedb');
        const f1 = I.p(0, 0.05, 0), f2 = I.p(1, 0.05, 0); P.line(f1[0], f1[1], f2[0], f2[1], '#7e8c9e');
      }
    }));
  };
  S.partV = function (type, accent) { // v boyunca, çizgi u=0
    return memo('pV2' + type + accent, () => tspr(32, I => {
      const P = I.P;
      if (type === 'solid') {
        const m = mat('#d9cdb4');
        I.box(-0.06, 0, 0.06, 1, 0, 26, m, { noedge: true });
        I.fr(0.06, 0, 1, 0, 8, accent); I.fr(0.06, 0, 1, 8, 9, shade(accent, 1.3));
        const a = I.p(0.06, 0, 26), b = I.p(0.06, 1, 26); P.line(a[0], a[1], b[0], b[1], INK);
        const c = I.p(-0.06, 0, 26), d = I.p(-0.06, 1, 26); P.line(c[0], c[1], d[0], d[1], shade('#d9cdb4', 0.7));
        P.line(a[0], a[1], c[0], c[1], INK); P.line(b[0], b[1], d[0], d[1], INK);
      } else {
        const accC = accent;
        I.fr(0.05, 0, 1, 0, 20, C('#8fd0e044'));
        I.fr(0.05, 0, 1, 0, 20, C('#b6eaf322'));
        I.fr(0.05, 0.1, 0.17, 3, 18, C('#ffffff66')); I.fr(0.05, 0.24, 0.27, 3, 18, C('#ffffff48')); I.fr(0.05, 0.62, 0.7, 3, 18, C('#ffffff2a'));
        I.fr(0.05, 0, 1, 0, 2, '#dfe6ee'); I.fr(0.05, 0, 1, 18, 20, shade(accC, 1.25)); I.fr(0.05, 0, 1, 20, 21, '#f4f8fb');
        I.fr(0.05, 0.96, 1, 0, 21, '#e6edf3');
        const a = I.p(0.05, 0, 21), b = I.p(0.05, 1, 21); P.line(a[0], a[1], b[0], b[1], '#ffffff');
        const t1 = I.p(-0.05, 0, 21), t2 = I.p(-0.05, 1, 21); P.line(t1[0], t1[1], t2[0], t2[1], '#a9bccb');
        const e1 = I.p(0.05, 1, 0), e2 = I.p(0.05, 1, 21); P.line(e1[0], e1[1], e2[0], e2[1], '#c3cedb');
        const f1 = I.p(0.05, 0, 0), f2 = I.p(0.05, 1, 0); P.line(f1[0], f1[1], f2[0], f2[1], '#7e8c9e');
      }
    }));
  };
  /* alçak ön duvar (kesit) */
  S.curbH = () => memo('curbH', () => tspr(10, I => {
    const m = mat('#f2ece0'); I.box(0, 1, 1, 1.14, 0, 5, m, { noedge: true });
    const a = I.p(0, 1.14, 5), b = I.p(1, 1.14, 5); I.P.line(a[0], a[1], b[0], b[1], INK);
    const c = I.p(0, 1.14, 0), d = I.p(1, 1.14, 0); I.P.line(c[0], c[1], d[0], d[1], '#a99f8c');
  }));
  S.curbV = () => memo('curbV', () => tspr(10, I => {
    const m = mat('#f2ece0'); I.box(1, 0, 1.14, 1, 0, 5, m, { noedge: true });
    const a = I.p(1.14, 0, 5), b = I.p(1.14, 1, 5); I.P.line(a[0], a[1], b[0], b[1], INK);
    const c = I.p(1.14, 0, 0), d = I.p(1.14, 1, 0); I.P.line(c[0], c[1], d[0], d[1], '#a99f8c');
  }));
  /* kapı çerçevesi (girişte) */
  S.doorPost = () => memo('doorPost', () => tspr(46, I => {
    const m = mat('#e8edf3');
    I.box(0.9, -0.08, 1.12, 0.08, 0, 44, m);
  }));

  /* ================= AĞAÇ / ÇEVRE ================= */
  S.tree = function (kind, seed) {
    return memo('tree' + kind + seed, () => {
      const pal = {
        g: ['#2f6b3a', '#3d8a45', '#56a853', '#86c96a'],
        o: ['#a8431f', '#d1671f', '#eb9230', '#f6c25a'],
        y: ['#9a7a1e', '#c4a02c', '#e2c44a', '#f4e58a'],
        p: ['#1f5a40', '#2a7350', '#3b8c60', '#6bb585']
      }[kind === 'pine' ? 'p' : kind];
      return fspr(60, 84, 30, 74, P => {
        const r = O.rng(seed * 131 + 9);
        P.disc(30, 74, 15, 5.5, O.pk(20, 40, 20, 70));
        if (kind === 'pine') {
          P.rect(28, 60, 4, 14, '#6a4a2e'); P.rect(31, 60, 1, 14, '#503620');
          for (let i = 0; i < 5; i++) {
            const y0 = 58 - i * 11, w = 24 - i * 4;
            for (let y = 0; y < 14; y++) {
              const half = Math.round(w * (y + 1) / 14 / 2 + 1);
              for (let x = -half; x <= half; x++) {
                const t = x < -half * 0.2 ? 2 : x > half * 0.45 ? 0 : 1;
                P.set(30 + x, y0 - 13 + y, pal[t + (r() < 0.08 ? 1 : 0)]);
              }
            }
          }
          P.set(30, 4, pal[3]);
        } else {
          P.rect(28, 54, 4, 20, '#6a4a2e'); P.rect(31, 54, 1, 20, '#4f3520'); P.rect(27, 70, 6, 4, '#6a4a2e');
          const blobs = [[30, 36, 18, 17], [18, 44, 11, 10], [42, 44, 11, 10], [30, 22, 13, 11], [20, 31, 10, 9], [41, 31, 10, 9]];
          blobs.forEach(b => P.disc(b[0] + 1, b[1] + 3, b[2], b[3], pal[0]));
          blobs.forEach(b => P.disc(b[0], b[1], b[2] - 1, b[3] - 1, pal[1]));
          blobs.forEach(b => P.disc(b[0] - 3, b[1] - 3, b[2] - 5, b[3] - 5, pal[2]));
          for (let i = 0; i < 38; i++) {
            const a = r() * 6.28, d = r() * 17, x = 28 + Math.cos(a) * d * 1.05 - 3, y = 31 + Math.sin(a) * d * 0.9 - 3;
            P.set(x, y, pal[3]); P.set(x + 1, y, pal[3]);
          }
          for (let i = 0; i < 20; i++) { const a = r() * 6.28, d = 6 + r() * 12, x = 31 + Math.cos(a) * d, y = 38 + Math.sin(a) * d * 0.8; P.set(x, y, pal[0]); P.set(x + 1, y + 1, pal[0]); }
        }
        P.outline('#22331f');
      });
    });
  };
  S.bush = function (seed, flower) {
    return memo('bush' + seed + flower, () => fspr(36, 28, 18, 22, P => {
      const r = O.rng(seed + 400);
      P.disc(18, 22, 11, 3.5, O.pk(20, 40, 20, 60));
      [[11, 15, 8, 7], [24, 15, 8, 7], [18, 11, 9, 8]].forEach(b => P.disc(b[0], b[1] + 1, b[2], b[3], '#2f6b3a'));
      [[11, 15, 7, 6], [24, 15, 7, 6], [18, 11, 8, 7]].forEach(b => P.disc(b[0], b[1], b[2], b[3], '#3f8c46'));
      [[10, 13, 4, 3], [22, 13, 4, 3], [17, 9, 4, 3]].forEach(b => P.disc(b[0], b[1], b[2], b[3], '#5aae55'));
      if (flower) for (let i = 0; i < 9; i++) { P.set(8 + r() * 20, 6 + r() * 12, flower); }
      P.outline('#22331f');
    }));
  };
  S.lamp = function () {
    return memo('lamp', () => fspr(20, 56, 10, 50, P => {
      P.disc(10, 50, 5, 2, O.pk(0, 0, 0, 50));
      P.rect(9, 12, 2, 38, '#3a4150'); P.rect(6, 8, 8, 4, '#3a4150'); P.rect(7, 10, 6, 2, '#fff2b0');
      P.rect(8, 48, 4, 2, '#2a2f3a');
      P.outline('#1c1f28');
    }));
  };
  S.bench = function (axis) {
    return memo('bench' + axis, () => tspr(18, I => {
      const w = mat('#9a6b3b'), d = mat('#3a4150');
      if (axis === 'u') { I.box(0.1, 0.25, 0.9, 0.35, 0, 6, d, { noedge: true }); I.box(0.05, 0.25, 0.95, 0.75, 6, 9, w); I.box(0.05, 0.22, 0.95, 0.3, 9, 16, w); }
      else { I.box(0.25, 0.1, 0.35, 0.9, 0, 6, d, { noedge: true }); I.box(0.25, 0.05, 0.75, 0.95, 6, 9, w); I.box(0.22, 0.05, 0.3, 0.95, 9, 16, w); }
    }));
  };

  /* avlu: şezlong ve şemsiye */
  S.lounger = function (v) {
    return memo('lounger' + v, () => tspr(22, I => {
      const cush = mat(v === 'a' ? '#2fa3a0' : '#e08a4a'), fr = mat('#f3f5f7');
      I.box(0.1, 0.18, 0.9, 0.82, 3, 5, fr, { noedge: true });
      I.box(0.12, 0.2, 0.9, 0.8, 5, 8, cush);
      I.box(0.08, 0.2, 0.3, 0.8, 8, 13, cush);
      I.box(0.1, 0.18, 0.16, 0.26, 0, 3, fr, { noedge: true }); I.box(0.84, 0.74, 0.9, 0.82, 0, 3, fr, { noedge: true });
    }));
  };
  S.parasol = function () {
    return memo('parasol', () => tspr(54, I => {
      const P = I.P;
      I.box(0.46, 0.46, 0.54, 0.54, 0, 36, mat('#e8ecef'), { noedge: true });
      const c = I.p(0.5, 0.5, 36), top = [c[0], c[1] - 14];
      const ring = [[-18, -1], [0, -10], [18, -1], [0, 9]].map(q => [c[0] + q[0], c[1] + q[1]]);
      const cols = ['#2fa3a0', '#f6f1e4', '#2fa3a0', '#f6f1e4'];
      for (let i = 0; i < 4; i++) P.poly([top, ring[i], ring[(i + 1) % 4]], i === 0 ? shade(cols[i], 1.05) : i === 3 ? shade(cols[i], 0.78) : cols[i]);
      P.outline('#2a2230');
    }, { w: 56 }));
  };

  /* araba: u boyunca iki karo */
  S.car = function (color, seed) {
    return memo('car' + color + seed, () => tspr(24, I => {
      const body = mat(color), P = I.P, glass = mat('#2d3f5c'), tire = mat('#23262e');
      P.disc(I.ax + 20, I.ay + 22, 26, 7, O.pk(0, 0, 0, 55));
      I.box(0.15, 0.12, 0.45, 0.2, 0, 3, tire, { noedge: true }); I.box(1.5, 0.12, 1.85, 0.2, 0, 3, tire, { noedge: true });
      I.box(0.1, 0.1, 1.9, 0.9, 2, 9, body);
      I.box(0.5, 0.16, 1.45, 0.84, 9, 15, glass, { top: shade(color, 1.15) });
      // camlar
      I.fl(0.54, 0.9, 0.84, 9.5, 14, '#9ac6e8'); I.fl(0.98, 1.4, 0.84, 9.5, 14, '#86b4d8');
      I.fr(1.45, 0.2, 0.8, 9.5, 14, '#6e9cc0');
      I.box(0.15, 0.78, 0.4, 0.92, 1, 3, tire, { noedge: true }); I.box(1.5, 0.78, 1.85, 0.92, 1, 3, tire, { noedge: true });
      // farlar
      I.fr(1.9, 0.14, 0.3, 4, 6, '#fff3b0'); I.fr(1.9, 0.7, 0.86, 4, 6, '#fff3b0');
      I.fl(0.12, 0.2, 0.9, 4, 6, '#d04040');
    }, { w: 84, ax: 20 }));
  };

  /* ================= MOBİLYA ================= */
  const WOOD = '#b98a55', WOOD2 = '#8e6238', WHITE = '#e9edf2', STEEL = '#8e9aaa', DARK = '#2c3342';

  /* masa + monitör. dir 'y': monitör ekranı sol yüze (kişi +v tarafında), 'x': sağ yüze (kişi +u tarafında) */
  S.desk = function (dir, wood, seed) {
    return memo('desk' + dir + wood + seed, () => tspr(30, I => {
      const m = mat(wood), dk = mat('#4a3a34'), r = O.rng(seed * 17 + 3);
      [[0.1, 0.1], [0.8, 0.1], [0.1, 0.8], [0.8, 0.8]].forEach(q => I.box(q[0], q[1], q[0] + 0.1, q[1] + 0.1, 0, 7, dk, { noedge: true }));
      I.box(0.03, 0.03, 0.97, 0.97, 7, 10, m);
      // ayrıntı: çekmece çizgisi
      if (dir === 'y') I.fl(0.55, 0.9, 0.97, 7.3, 9.3, shade(wood, 0.78)); else I.fr(0.97, 0.1, 0.45, 7.3, 9.3, shade(wood, 0.78));
      // monitör
      const bz = mat('#242a38');
      if (dir === 'y') {
        I.box(0.44, 0.3, 0.56, 0.4, 10, 12, bz);
        I.box(0.18, 0.2, 0.82, 0.3, 11, 24, bz);
        I.fl(0.22, 0.78, 0.3, 12.5, 22.5, '#161c2c');
      } else {
        I.box(0.6, 0.44, 0.7, 0.56, 10, 12, bz);
        I.box(0.7, 0.18, 0.8, 0.82, 11, 24, bz);
        I.fr(0.8, 0.22, 0.78, 12.5, 22.5, '#161c2c');
      }
      // klavye, fare
      const kb = mat('#cfd6df');
      if (dir === 'y') { I.box(0.28, 0.56, 0.68, 0.76, 10, 11, kb, { noedge: true }); I.box(0.74, 0.62, 0.82, 0.7, 10, 11, mat('#aeb8c4'), { noedge: true }); }
      else { I.box(0.56, 0.28, 0.76, 0.68, 10, 11, kb, { noedge: true }); I.box(0.62, 0.74, 0.7, 0.82, 10, 11, mat('#aeb8c4'), { noedge: true }); }
      // süs: kupa / kâğıt / bitki
      const k = r();
      if (k < 0.33) { const c = ['#d4553b', '#3b82c4', '#e0a93a', '#3aa17a'][Math.floor(r() * 4)]; if (dir === 'y') I.box(0.1, 0.62, 0.2, 0.72, 10, 14, mat(c)); else I.box(0.62, 0.1, 0.72, 0.2, 10, 14, mat(c)); }
      else if (k < 0.66) { if (dir === 'y') I.box(0.82, 0.4, 0.94, 0.55, 10, 11, mat('#f6f1e3'), { noedge: true }); else I.box(0.4, 0.82, 0.55, 0.94, 10, 11, mat('#f6f1e3'), { noedge: true }); }
      else { if (dir === 'y') { I.box(0.12, 0.38, 0.22, 0.48, 10, 13, mat('#c0603a')); I.box(0.1, 0.36, 0.24, 0.5, 13, 16, mat('#4aa55a')); } else { I.box(0.38, 0.12, 0.48, 0.22, 10, 13, mat('#c0603a')); I.box(0.36, 0.1, 0.5, 0.24, 13, 16, mat('#4aa55a')); } }
    }));
  };
  /* ekran katmanı: durum → içerik (dinamik, masa sprite'ının üstüne aynı çıpayla çizilir) */
  S.screen = function (dir, state) {
    return memo('scr' + dir + state, () => tspr(30, I => {
      const P = I.P;
      const f = (s0, s1, z0, z1, c) => dir === 'y' ? I.fl(0.22 + 0.56 * s0, 0.22 + 0.56 * s1, 0.3, z0, z1, c) : I.fr(0.8, 0.22 + 0.56 * s0, 0.22 + 0.56 * s1, z0, z1, c);
      const bg = { up: '#0f2b2e', down: '#2e1418', flat: '#14223c', flash: '#cfefff', staff: '#123046', idle: '#161c2c' }[state];
      f(0, 1, 12.5, 22.5, bg);
      if (state === 'flash') {
        f(0, 1, 12.5, 13.5, '#ffffff'); f(0, 1, 21.5, 22.5, '#ffffff'); f(0.08, 0.92, 15, 20, '#7fd8ff');
        f(0.2, 0.4, 16, 19, '#ffffff');
        return;
      }
      if (state === 'idle') return;
      if (state === 'staff') {
        f(0.08, 0.92, 20, 21.5, '#3fa7d6'); f(0.08, 0.6, 17.5, 19, '#7fd0ee'); f(0.08, 0.75, 15, 16.5, '#7fd0ee'); f(0.08, 0.45, 13.2, 14.5, '#7fd0ee');
        return;
      }
      // mumlar
      const cols = state === 'up' ? ['#3dd68c', '#2bb673'] : state === 'down' ? ['#ff6b6b', '#d94c4c'] : ['#6ea8ff', '#4f86e0'];
      const hs = state === 'up' ? [2, 3, 2.5, 4, 5, 4.5, 6.5] : state === 'down' ? [6.5, 5, 5.5, 4, 3, 3.5, 2] : [4, 3.5, 4.5, 4, 3.5, 4.2, 4];
      hs.forEach((h, i) => { const s = 0.07 + i * 0.13; f(s, s + 0.07, 13.5, 13.5 + h + 1.5, cols[i % 2]); });
      f(0, 1, 12.5, 13.3, shade(cols[1], 0.5));
    }));
  };
  /* sandalye (arkadan görünüm) ve oturan kişi kisiler.js'de */

  S.plant = function (kind) {
    return memo('plant' + kind, () => tspr(kind === 'tall' ? 46 : 30, I => {
      const P = I.P, pot = mat('#c0683a');
      I.box(0.3, 0.3, 0.7, 0.7, 0, kind === 'tall' ? 9 : 6, pot);
      const cx = I.p(0.5, 0.5, kind === 'tall' ? 9 : 6), r = O.rng(kind === 'tall' ? 4 : 8);
      const cols = ['#2f6b3a', '#3d8a45', '#56a853', '#86c96a'];
      if (kind === 'tall') {
        P.rect(cx[0], cx[1] - 14, 1, 14, '#6a4a2e');
        [[0, -22, 9, 8], [-6, -16, 6, 6], [6, -16, 6, 6], [0, -29, 6, 5], [-4, -25, 5, 5], [5, -24, 5, 5]].forEach((b, i) => P.disc(cx[0] + b[0], cx[1] + b[1], b[2], b[3], cols[i % 2]));
        [[-2, -26, 4, 3], [4, -20, 3, 3], [-5, -19, 3, 3]].forEach(b => P.disc(cx[0] + b[0], cx[1] + b[1], b[2], b[3], cols[2]));
        for (let i = 0; i < 10; i++) P.set(cx[0] - 8 + r() * 16, cx[1] - 32 + r() * 18, cols[3]);
      } else {
        [[0, -8, 6, 5], [-5, -5, 4, 4], [5, -5, 4, 4]].forEach((b, i) => P.disc(cx[0] + b[0], cx[1] + b[1], b[2], b[3], cols[i % 2 + 0]));
        [[0, -10, 3, 2]].forEach(b => P.disc(cx[0] + b[0], cx[1] + b[1], b[2], b[3], cols[2]));
        for (let i = 0; i < 4; i++) P.set(cx[0] - 5 + r() * 10, cx[1] - 13 + r() * 8, cols[3]);
      }
      P.outline('#22331f');
    }));
  };
  S.cooler = function () {
    return memo('cooler', () => tspr(38, I => {
      const w = mat('#e6ebf1'); I.box(0.28, 0.28, 0.72, 0.72, 0, 20, w);
      I.fl(0.4, 0.6, 0.72, 8, 12, '#4a90d9'); I.fl(0.4, 0.5, 0.72, 4, 6, '#d94c4c');
      const c = I.p(0.5, 0.5, 20); I.P.disc(c[0], c[1] - 6, 6, 7, '#9fd8ff'); I.P.disc(c[0] - 2, c[1] - 8, 2, 3, '#e9f7ff'); I.P.rect(c[0] - 2, c[1] - 14, 4, 2, '#cfe9fb');
      I.P.outline(INK);
    }));
  };
  S.fridge = function (dir) {
    return memo('fridge' + dir, () => tspr(44, I => {
      const w = mat('#dfe5ec'); I.box(0.12, 0.12, 0.88, 0.88, 0, 40, w);
      if (dir === 'y') { I.fl(0.15, 0.85, 0.88, 22, 22.6, '#8794a6'); I.fl(0.75, 0.82, 0.88, 26, 36, '#8794a6'); I.fl(0.75, 0.82, 0.88, 10, 18, '#8794a6'); }
      else { I.fr(0.88, 0.15, 0.85, 22, 22.6, '#8794a6'); I.fr(0.88, 0.75, 0.82, 26, 36, '#8794a6'); }
    }));
  };
  S.shelf = function (dir, kind, seed) {
    return memo('shelf' + dir + kind + seed, () => tspr(48, I => {
      const bodyM = mat('#a77a4a'), r = O.rng(seed * 31 + 7), P = I.P;
      const H = kind === 'tall' ? 44 : 30;
      I.box(0.06, 0.1, 0.94, 0.9, 0, H, bodyM);
      const rows = kind === 'tall' ? 4 : 3, rh = (H - 4) / rows, bcols = ['#c4452f', '#3b6fb4', '#e0a93a', '#3d9a6e', '#8a63c9', '#e8e0cc', '#d86b8f', '#4aa7b8'];
      for (let k = 0; k < rows; k++) {
        const z0 = 3 + k * rh;
        if (dir === 'y') {
          I.fl(0.1, 0.9, 0.9, z0, z0 + rh - 1, '#3a2a20');
          let u = 0.11;
          while (u < 0.88) {
            const w = 0.05 + r() * 0.05, hh = (rh - 3) * (0.55 + r() * 0.45), box = kind === 'arsiv' && r() < 0.35;
            I.fl(u, u + w, 0.9, z0 + 0.5, z0 + 0.5 + hh, box ? '#d8c39a' : bcols[Math.floor(r() * bcols.length)]);
            u += w + 0.012;
          }
          I.fl(0.06, 0.94, 0.9, z0 - 1.5, z0 - 0.5, shade('#a77a4a', 1.2));
        } else {
          I.fr(0.94, 0.14, 0.86, z0, z0 + rh - 1, '#3a2a20');
          let v = 0.15;
          while (v < 0.84) {
            const w = 0.05 + r() * 0.05, hh = (rh - 3) * (0.55 + r() * 0.45), box = kind === 'arsiv' && r() < 0.35;
            I.fr(0.94, v, v + w, z0 + 0.5, z0 + 0.5 + hh, box ? '#d8c39a' : bcols[Math.floor(r() * bcols.length)]);
            v += w + 0.012;
          }
          I.fr(0.94, 0.1, 0.9, z0 - 1.5, z0 - 0.5, shade('#a77a4a', 1.2));
        }
      }
    }));
  };
  S.rack = function (dir) {
    return memo('rack' + dir, () => tspr(44, I => {
      const m = mat('#2c3342'); I.box(0.1, 0.1, 0.9, 0.9, 0, 40, m);
      for (let k = 0; k < 6; k++) {
        const z0 = 3 + k * 6;
        if (dir === 'y') { I.fl(0.14, 0.86, 0.9, z0, z0 + 4.5, '#3b4558'); I.fl(0.18, 0.5, 0.9, z0 + 1.5, z0 + 3, '#1c2130'); }
        else { I.fr(0.9, 0.14, 0.86, z0, z0 + 4.5, '#3b4558'); I.fr(0.9, 0.18, 0.5, z0 + 1.5, z0 + 3, '#1c2130'); }
      }
    }));
  };
  /* sunucu LED katmanı: durum renkleri (dinamik) */
  S.rackLed = function (dir, color) {
    return memo('led' + dir + color, () => tspr(44, I => {
      for (let k = 0; k < 6; k++) {
        const z = 3 + k * 6 + 2;
        if (dir === 'y') { I.dot(0.6, 0.9, z, color); I.dot(0.68, 0.9, z, color); I.dot(0.76, 0.9, z, k % 2 ? color : '#556070'); }
        else { I.dot(0.9, 0.6, z, color); I.dot(0.9, 0.68, z, color); I.dot(0.9, 0.76, z, k % 2 ? color : '#556070'); }
      }
    }));
  };
  S.safe = function () {
    return memo('safe', () => tspr(34, I => {
      const m = mat('#7b8798'); I.box(0.08, 0.1, 0.92, 0.9, 0, 28, m);
      I.fl(0.14, 0.86, 0.9, 3, 25, '#a3aebd'); I.fl(0.14, 0.86, 0.9, 3, 4, '#5d6878');
      const c = I.p(0.5, 0.9, 15); I.P.disc(c[0], c[1], 5, 4, '#5d6878'); I.P.disc(c[0], c[1], 3.5, 2.8, '#d8dee8'); I.P.set(c[0], c[1] - 1, '#c0392b'); I.P.rect(c[0] - 1, c[1] - 1, 3, 1, '#2a2f3a');
      I.fl(0.6, 0.78, 0.9, 6, 7, '#5d6878');
      I.P.outline(INK);
    }));
  };
  S.coins = function () {
    return memo('coins', () => tspr(20, I => {
      const g = mat('#e8b630');
      [[0.3, 0.35], [0.5, 0.3], [0.45, 0.55]].forEach((q, i) => { for (let k = 0; k < 3 - (i % 2); k++) I.box(q[0], q[1], q[0] + 0.18, q[1] + 0.18, k * 2, k * 2 + 2, g); });
    }));
  };
  S.printer = function () {
    return memo('printer', () => tspr(22, I => {
      I.box(0.2, 0.2, 0.8, 0.8, 0, 12, mat('#d4dae2')); I.box(0.24, 0.24, 0.76, 0.76, 12, 15, mat('#aeb8c6'));
      I.fl(0.3, 0.7, 0.8, 5, 8, '#2c3342'); I.top(0.3, 0.3, 0.7, 0.6, 15.2, '#f6f1e3');
    }));
  };
  S.cabinet = function (dir) {
    return memo('cab' + dir, () => tspr(36, I => {
      I.box(0.15, 0.12, 0.85, 0.88, 0, 30, mat('#9aa5b4'));
      for (let k = 0; k < 3; k++) {
        const z0 = 2 + k * 9;
        if (dir === 'y') { I.fl(0.2, 0.8, 0.88, z0, z0 + 8, '#b3bdca'); I.fl(0.42, 0.58, 0.88, z0 + 4, z0 + 5, '#5d6878'); }
        else { I.fr(0.85, 0.18, 0.82, z0, z0 + 8, '#b3bdca'); I.fr(0.85, 0.42, 0.58, z0 + 4, z0 + 5, '#5d6878'); }
      }
    }));
  };
  S.sofa = function (axis, part, color) { // part: 'l' | 'm' | 'r'
    return memo('sofa' + axis + part + color, () => tspr(24, I => {
      const m = mat(color), dk = mat(shade(color, 0.8));
      if (axis === 'u') {
        I.box(0.02, 0.1, 0.98, 0.9, 0, 8, dk);
        I.box(0.02, 0.1, 0.98, 0.3, 8, 17, m);
        I.box(0.04, 0.3, 0.96, 0.88, 8, 11, mat(shade(color, 1.1)));
        if (part !== 'm') I.box(part === 'l' ? 0.0 : 0.88, 0.1, part === 'l' ? 0.14 : 1.0, 0.9, 8, 14, m);
      } else {
        I.box(0.1, 0.02, 0.9, 0.98, 0, 8, dk);
        I.box(0.1, 0.02, 0.3, 0.98, 8, 17, m);
        I.box(0.3, 0.04, 0.88, 0.96, 8, 11, mat(shade(color, 1.1)));
        if (part !== 'm') I.box(0.1, part === 'l' ? 0.0 : 0.88, 0.9, part === 'l' ? 0.14 : 1.0, 8, 14, m);
      }
    }));
  };
  S.table = function (kind) {
    return memo('table' + kind, () => tspr(24, I => {
      if (kind === 'round') {
        const c = I.p(0.5, 0.5, 11);
        I.box(0.44, 0.44, 0.56, 0.56, 0, 11, mat('#6a4a2e'));
        I.P.disc(c[0], c[1], 14, 7, '#8e6238'); I.P.disc(c[0], c[1] - 1, 14, 6.5, '#c28e57'); I.P.disc(c[0] - 2, c[1] - 2, 8, 3, '#d6a56d');
        // çay bardakları
        [[-6, 0], [5, 1]].forEach(g => { I.P.rect(c[0] + g[0], c[1] + g[1] - 5, 3, 4, '#f4ede0'); I.P.rect(c[0] + g[0], c[1] + g[1] - 5, 3, 2, '#b4442c'); I.P.set(c[0] + g[0] + 1, c[1] + g[1] - 6, '#fff'); });
        I.P.outline('#3a2a20');
      } else {
        I.box(0.1, 0.15, 0.9, 0.85, 4, 8, mat('#b98a55')); I.box(0.15, 0.2, 0.25, 0.3, 0, 4, mat('#4a3a34'), { noedge: true }); I.box(0.75, 0.7, 0.85, 0.8, 0, 4, mat('#4a3a34'), { noedge: true });
      }
    }));
  };
  S.stool = function () {
    return memo('stool', () => tspr(14, I => {
      I.box(0.42, 0.42, 0.58, 0.58, 0, 5, mat('#4a3a34'), { noedge: true });
      const c = I.p(0.5, 0.5, 6); I.P.disc(c[0], c[1], 6, 3, '#d04a36'); I.P.disc(c[0], c[1] - 1, 6, 2.6, '#e8624a'); I.P.outline('#4a1a14');
    }));
  };
  S.counter = function (dir, part) { // mutfak tezgâhı
    return memo('counter' + dir + part, () => tspr(36, I => {
      const w = mat('#d9d2c2'), c = mat('#6aa0c8');
      if (dir === 'u') {
        I.box(0.02, 0.08, 0.98, 0.92, 0, 12, mat('#8e6238'), { noedge: false });
        I.box(0.0, 0.06, 1.0, 0.94, 12, 14, w);
        I.fl(0.1, 0.9, 0.92, 2, 11, '#6d4a2c'); I.fl(0.45, 0.55, 0.92, 7, 9, '#d8dee8');
      } else {
        I.box(0.08, 0.02, 0.92, 0.98, 0, 12, mat('#8e6238'));
        I.box(0.06, 0.0, 0.94, 1.0, 12, 14, w);
        I.fr(0.92, 0.1, 0.9, 2, 11, '#6d4a2c');
      }
      if (part === 'tea') { // semaver: pirinç gövde, musluk, kulplar, üstte demlik
        const cx = I.p(0.5, 0.5, 14), P = I.P, x = cx[0], y = cx[1];
        P.rect(x - 4, y - 14, 9, 11, '#d6a23a'); P.rect(x - 4, y - 14, 3, 11, '#f0ca68'); P.rect(x + 3, y - 14, 2, 11, '#a5771f');
        P.rect(x - 5, y - 12, 1, 6, '#d6a23a'); P.rect(x + 5, y - 12, 1, 6, '#a5771f');
        P.rect(x - 5, y - 15, 11, 2, '#c4922c'); P.rect(x - 4, y - 3, 9, 2, '#8a6218');
        P.rect(x + 5, y - 8, 4, 2, '#cdd3dc'); P.rect(x + 8, y - 6, 1, 2, '#cdd3dc');
        P.rect(x - 3, y - 20, 7, 5, '#f4f6f8'); P.rect(x - 3, y - 18, 7, 1, '#3b82c4'); P.rect(x - 1, y - 22, 3, 2, '#cdd3dc'); P.rect(x + 4, y - 19, 2, 1, '#f4f6f8');
        P.set(x - 3, y - 12, '#fff2b8'); P.set(x - 3, y - 11, '#fff2b8');
        P.rect(x + 9, y - 3, 3, 3, '#f4ede0'); P.rect(x + 9, y - 3, 3, 1, '#b4442c');
        P.outline('#2a2230');
      }
    }));
  };
  S.dice = function () {
    return memo('dice', () => tspr(30, I => {
      const w = mat('#f6f2ea'); I.box(0.18, 0.18, 0.82, 0.82, 0, 24, w);
      [[0.35, 0.5], [0.65, 0.5], [0.5, 0.5]].forEach(a => { const pt = I.p(a[0], 0.82, 12 + (a[0] === 0.5 ? 0 : 0)); });
      const l = [[0.3, 8], [0.7, 8], [0.5, 12], [0.3, 16], [0.7, 16]]; l.forEach(a => { const c = I.p(a[0] + 0.12, 0.82, a[1] + 4); I.P.rect(c[0] - 1, c[1] - 1, 2, 2, '#c0392b'); });
      const t = I.p(0.5, 0.5, 24); I.P.rect(t[0] - 3, t[1] - 1, 2, 2, '#2a2230'); I.P.rect(t[0] + 2, t[1] - 1, 2, 2, '#2a2230');
    }));
  };
  S.bigDesk = function (part) { // makam masası
    return memo('bigdesk' + part, () => tspr(32, I => {
      const m = mat('#6b3f2a'), d = mat('#4a2a1c');
      I.box(0.0, 0.1, 1.0, 0.9, 0, 11, d, { noedge: true });
      I.box(0.0, 0.08, 1.0, 0.92, 11, 13, m);
      I.fl(0.08, 0.92, 0.9, 2, 10, '#5a3322');
      if (part === 'a') {
        I.box(0.35, 0.5, 0.65, 0.7, 13, 16, mat('#2c3342'));       // dizüstü arkası
        I.fl(0.45, 0.55, 0.7, 14, 15, '#9aa5b4');
        I.box(0.1, 0.55, 0.28, 0.75, 13, 15, mat('#f1ead8'), { noedge: true });
      } else {
        I.box(0.55, 0.45, 0.7, 0.6, 13, 20, mat('#2c8c4a'), {}); I.box(0.48, 0.4, 0.78, 0.66, 13, 14, mat('#e8b630')); // lamba
        I.box(0.2, 0.55, 0.4, 0.7, 13, 16, mat('#c0392b'));
      }
    }));
  };
  S.globe = function () {
    return memo('globe', () => tspr(34, I => {
      I.box(0.38, 0.38, 0.62, 0.62, 0, 4, mat('#6b3f2a'));
      const c = I.p(0.5, 0.5, 16); I.P.rect(c[0], c[1] - 2, 1, 14, '#c8a050');
      I.P.disc(c[0], c[1] - 6, 8, 8, '#2f78c4'); I.P.disc(c[0] - 2, c[1] - 7, 3, 3, '#4aa55a'); I.P.disc(c[0] + 3, c[1] - 3, 2, 3, '#4aa55a'); I.P.disc(c[0] - 4, c[1] - 9, 2, 2, '#9bd0f4');
      I.P.outline(INK);
    }));
  };

  S.vending = function () {
    return memo('vending', () => tspr(46, I => {
      I.box(0.1, 0.12, 0.9, 0.9, 0, 42, mat('#c0392b'));
      I.fl(0.18, 0.62, 0.9, 16, 38, '#1c2438');
      [[0.22, 30, '#f5cb5c'], [0.34, 30, '#3d9a6e'], [0.46, 30, '#e8e0cc'], [0.22, 24, '#3b82c4'], [0.34, 24, '#d86b8f'], [0.46, 24, '#f28c28'], [0.22, 18, '#8a63c9'], [0.34, 18, '#e8e0cc'], [0.46, 18, '#f5cb5c']].forEach(a => I.fl(a[0], a[0] + 0.08, 0.9, a[1], a[1] + 4, a[2]));
      I.fl(0.68, 0.84, 0.9, 20, 36, '#8a2a20'); I.fl(0.72, 0.8, 0.9, 28, 30, '#3dd68c'); I.fl(0.7, 0.82, 0.9, 6, 12, '#101520');
    }));
  };
  S.floorLamp = function () {
    return memo('floorLamp', () => fspr(24, 52, 12, 46, P => {
      P.disc(12, 46, 5, 2, O.pk(0, 0, 0, 50));
      P.rect(11, 14, 2, 32, '#5a4a3a'); P.rect(8, 44, 8, 2, '#3a2e2a');
      P.poly([[5, 14], [19, 14], [16, 4], [8, 4]], '#f8e3a8'); P.poly([[5, 14], [19, 14], [18, 12], [6, 12]], '#e8c870'); P.rect(9, 5, 3, 8, '#fff3c8');
      P.outline('#2a2230');
    }));
  };
  S.beanbag = function (color) {
    return memo('bean' + color, () => fspr(28, 20, 14, 16, P => {
      P.disc(14, 16, 11, 3, O.pk(0, 0, 0, 45));
      P.disc(14, 11, 10, 6, shade(color, 0.8)); P.disc(14, 9, 9, 5.5, color); P.disc(11, 7, 4, 2.5, shade(color, 1.25));
      P.outline('#2a2230');
    }));
  };
  S.rugSpot = null;
  S.signpost = function () {
    return memo('signpost', () => fspr(40, 60, 20, 54, P => {
      P.disc(20, 54, 8, 3, O.pk(0, 0, 0, 50));
      P.rect(19, 18, 3, 36, '#6a4a2e');
      P.rect(4, 6, 32, 16, '#f3ead2'); P.rect(4, 6, 32, 2, '#d9c9a0'); P.rect(4, 20, 32, 2, '#c3b184');
      P.rect(8, 12, 18, 2, '#1f3a6e'); P.rect(8, 16, 12, 2, '#1f3a6e'); P.poly([[28, 9], [34, 14], [28, 19]], '#c0392b');
      P.outline('#2a2230');
    }));
  };
  S.rug = null; // zeminde çizilir
  S.board = function (dir) { // yürüyen tahta (beyaz tahta)
    return memo('board' + dir, () => tspr(40, I => {
      I.box(0.1, 0.45, 0.9, 0.55, 0, 3, mat('#8e9aaa'), { noedge: true });
      I.box(0.15, 0.46, 0.85, 0.54, 6, 34, mat('#f4f6f9'));
      I.fl(0.2, 0.8, 0.54, 12, 30, '#fbfbfd');
      I.fl(0.24, 0.5, 0.54, 22, 23, '#d4553b'); I.fl(0.24, 0.66, 0.54, 18, 19, '#3b82c4'); I.fl(0.24, 0.42, 0.54, 14, 15, '#3aa17a');
    }));
  };
  S.turnstile = function () {
    return memo('turnstile', () => tspr(30, I => {
      const m = mat('#aeb8c6'); I.box(0.3, 0.3, 0.7, 0.7, 0, 18, m);
      I.box(0.34, 0.34, 0.66, 0.66, 18, 20, mat('#2c3342'));
      I.fl(0.4, 0.6, 0.7, 12, 15, '#3dd68c');
      I.box(0.2, 0.46, 0.8, 0.54, 20, 22, mat('#8e9aaa'), { noedge: true });
    }));
  };
  S.beacon = function () {
    return memo('beacon', () => tspr(44, I => {
      I.box(0.3, 0.3, 0.7, 0.7, 0, 8, mat('#3a4150')); I.box(0.44, 0.44, 0.56, 0.56, 8, 26, mat('#6a7484'));
      const c = I.p(0.5, 0.5, 26); I.P.disc(c[0], c[1] - 4, 5, 5, '#6b1f1f'); I.P.disc(c[0] - 1, c[1] - 5, 2, 2, '#a83a3a'); I.P.outline(INK);
    }));
  };
  S.box = function (seed) {
    return memo('cbox' + seed, () => tspr(18, I => {
      const m = mat(seed % 2 ? '#c9a46a' : '#b8935a');
      I.box(0.15, 0.2, 0.85, 0.8, 0, 12, m);
      I.fl(0.3, 0.7, 0.8, 5, 9, '#f1e6c8'); I.top(0.45, 0.2, 0.55, 0.8, 12.1, '#a8844f');
    }));
  };
  S.mailbox = function () {
    return memo('mailbox', () => tspr(34, I => {
      I.box(0.44, 0.44, 0.56, 0.56, 0, 12, mat('#6a7484'));
      I.box(0.2, 0.25, 0.8, 0.75, 12, 24, mat('#2f6fb8'));
      I.fl(0.35, 0.65, 0.75, 16, 19, '#0f2c52'); I.box(0.78, 0.35, 0.84, 0.4, 20, 30, mat('#d94c4c'));
    }));
  };
  S.safeBeam = null;
  S.drawer = null;

  /* duvar ekranı katmanı: Haberleşme/Finans/Risk/Tarama vb. içerik dinamik üretilir (world.js) */
})();
