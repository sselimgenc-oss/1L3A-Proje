/* Ofis · piksel çizim çekirdeği.
   Tüm görseller bu dosya ve sprites.js ile kodla üretilir (dış görsel varlık yok; bkz. LISANSLAR.md). */
(function () {
  'use strict';
  const O = (window.OFIS = window.OFIS || {});
  const HW = 20, HH = 10; // izometrik karo: 40x20
  O.HW = HW; O.HH = HH;

  /* ---------- renk ---------- */
  const pk = (r, g, b, a) => ((((a === undefined ? 255 : a) & 255) << 24) | ((b & 255) << 16) | ((g & 255) << 8) | (r & 255)) >>> 0;
  const cache = {};
  function C(h) {
    if (typeof h === 'number') return h;
    if (cache[h] !== undefined) return cache[h];
    let s = h.replace('#', '');
    if (s.length === 3) s = s.replace(/./g, '$&$&');
    if (s.length === 8) { const q = parseInt(s.slice(0, 6), 16), al = parseInt(s.slice(6), 16); return (cache[h] = pk((q >> 16) & 255, (q >> 8) & 255, q & 255, al)); }
    const v = parseInt(s, 16);
    return (cache[h] = pk((v >> 16) & 255, (v >> 8) & 255, v & 255, 255));
  }
  const rr = c => c & 255, gg = c => (c >> 8) & 255, bb = c => (c >> 16) & 255, aa = c => c >>> 24;
  const cl = v => (v < 0 ? 0 : v > 255 ? 255 : v | 0);
  const shade = (c, f) => { c = C(c); return pk(cl(rr(c) * f), cl(gg(c) * f), cl(bb(c) * f), aa(c)); };
  const mix = (a, b, t) => { a = C(a); b = C(b); return pk(cl(rr(a) + (rr(b) - rr(a)) * t), cl(gg(a) + (gg(b) - gg(a)) * t), cl(bb(a) + (bb(b) - bb(a)) * t), 255); };
  const withA = (c, a) => { c = C(c); return pk(rr(c), gg(c), bb(c), a); };
  const css = c => { c = C(c); return 'rgba(' + rr(c) + ',' + gg(c) + ',' + bb(c) + ',' + (aa(c) / 255).toFixed(3) + ')'; };
  /* malzeme: sol yüz = taban renk, üst açık, sağ koyu */
  function mat(base) {
    const l = C(base);
    return { t: mix(shade(l, 1.18), '#fff6e0', 0.1), l: l, r: shade(l, 0.68), e: shade(l, 0.38), h: mix(shade(l, 1.4), '#ffffff', 0.18) };
  }
  Object.assign(O, { C, pk, shade, mix, withA, css, mat, unpack: c => [rr(c), gg(c), bb(c), aa(c)] });

  /* ---------- rastgele ---------- */
  O.rng = function (seed) {
    let a = seed >>> 0;
    return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  };
  O.h2 = function (x, y, s) { let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul((s || 0) | 0, 2147483647)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return (((h ^ (h >>> 16)) >>> 0) / 4294967296); };
  O.hashStr = function (s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };

  /* ---------- piksel tamponu ---------- */
  class Px {
    constructor(w, h) {
      this.w = w; this.h = h;
      this.cv = document.createElement('canvas'); this.cv.width = w; this.cv.height = h;
      this.cx = this.cv.getContext('2d');
      this.im = this.cx.createImageData(w, h);
      this.d = new Uint32Array(this.im.data.buffer);
    }
    get(x, y) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= this.w || y >= this.h) return 0; return this.d[y * this.w + x]; }
    set(x, y, c) {
      x |= 0; y |= 0;
      if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
      c = C(c);
      const a = c >>> 24;
      if (a === 255) { this.d[y * this.w + x] = c; return; }
      if (a === 0) return;
      const i = y * this.w + x, d = this.d[i], da = d >>> 24;
      if (da === 0) { this.d[i] = c; return; }
      const t = a / 255;
      this.d[i] = pk(rr(d) + (rr(c) - rr(d)) * t, gg(d) + (gg(c) - gg(d)) * t, bb(d) + (bb(c) - bb(d)) * t, da + (255 - da) * t);
    }
    rect(x, y, w, h, c) { c = C(c); for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, c); }
    hline(x, y, w, c) { this.rect(x, y, w, 1, c); }
    vline(x, y, h, c) { this.rect(x, y, 1, h, c); }
    line(x0, y0, x1, y1, c) {
      c = C(c); x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
      const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
      let err = dx + dy;
      for (;;) {
        this.set(x0, y0, c);
        if (x0 === x1 && y0 === y1) break;
        const e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
      }
    }
    /* çokgen: piksel merkezi kuralı; komşu çokgenler arasında boşluk/çakışma olmaz */
    poly(pts, c) {
      c = C(c);
      let y0 = Infinity, y1 = -Infinity;
      for (const p of pts) { if (p[1] < y0) y0 = p[1]; if (p[1] > y1) y1 = p[1]; }
      const n = pts.length;
      for (let y = Math.floor(y0); y <= Math.ceil(y1); y++) {
        const yc = y + 0.5, xs = [];
        for (let i = 0; i < n; i++) {
          const p = pts[i], q = pts[(i + 1) % n];
          if ((p[1] <= yc && q[1] > yc) || (q[1] <= yc && p[1] > yc)) xs.push(p[0] + (yc - p[1]) * (q[0] - p[0]) / (q[1] - p[1]));
        }
        xs.sort((a, b) => a - b);
        for (let k = 0; k + 1 < xs.length; k += 2) {
          for (let x = Math.ceil(xs[k] - 0.5); x < Math.ceil(xs[k + 1] - 0.5); x++) this.set(x, y, c);
        }
      }
    }
    disc(cx, cy, rx, ry, c) {
      c = C(c);
      for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
        const dx = (x + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry;
        if (dx * dx + dy * dy <= 1) this.set(x, y, c);
      }
    }
    /* elmas (karo) üstündeki her piksel için fn(x, y, u, v): u,v karo içi 0..1 */
    diamond(sx, sy, fn) {
      for (let r = 0; r < HH * 2; r++) {
        const hw = (r < HH ? r + 0.5 : HH * 2 - r - 0.5) * 2;
        const x0 = Math.ceil(sx - hw - 0.5), x1 = Math.ceil(sx + hw - 0.5);
        for (let x = x0; x < x1; x++) {
          const dx = x + 0.5 - sx, dy = r + 0.5;
          const u = (dx / HW + dy / HH) / 2, v = (dy / HH - dx / HW) / 2;
          fn(x, sy + r, u, v);
        }
      }
    }
    outline(c) {
      c = C(c);
      const src = this.d.slice(), w = this.w, h = this.h;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        if ((src[y * w + x] >>> 24) > 40) continue;
        if ((x > 0 && (src[y * w + x - 1] >>> 24) > 120) || (x < w - 1 && (src[y * w + x + 1] >>> 24) > 120) ||
            (y > 0 && (src[(y - 1) * w + x] >>> 24) > 120) || (y < h - 1 && (src[(y + 1) * w + x] >>> 24) > 120)) this.d[y * w + x] = c;
      }
    }
    flush() { this.cx.putImageData(this.im, 0, 0); return this.cv; }
  }
  O.Px = Px;

  /* ---------- izometrik yardımcı: (u,v,z) → ekran ---------- */
  class Iso {
    constructor(P, ax, ay) { this.P = P; this.ax = ax; this.ay = ay; }
    p(u, v, z) { return [this.ax + Math.round((u - v) * HW), this.ay + Math.round((u + v) * HH - (z || 0))]; }
    /* kutu: üst + sol(+v) + sağ(+u) yüz; kenar çizgileri */
    box(u0, v0, u1, v1, z0, z1, m, o) {
      o = o || {};
      const P = this.P, p = this.p.bind(this);
      const top = [p(u0, v0, z1), p(u1, v0, z1), p(u1, v1, z1), p(u0, v1, z1)];
      const lf = [p(u0, v1, z0), p(u1, v1, z0), p(u1, v1, z1), p(u0, v1, z1)];
      const rt = [p(u1, v1, z0), p(u1, v0, z0), p(u1, v0, z1), p(u1, v1, z1)];
      P.poly(lf, m.l); P.poly(rt, m.r); P.poly(top, o.top !== undefined ? o.top : m.t);
      if (o.noedge) return;
      const e = m.e, h = m.h;
      // silüet
      P.line(lf[0][0], lf[0][1], lf[1][0], lf[1][1], e);
      P.line(rt[0][0], rt[0][1], rt[1][0], rt[1][1], e);
      P.line(lf[0][0], lf[0][1], lf[3][0], lf[3][1], e);
      P.line(rt[1][0], rt[1][1], rt[2][0], rt[2][1], e);
      P.line(top[0][0], top[0][1], top[1][0], top[1][1], e);
      P.line(top[0][0], top[0][1], top[3][0], top[3][1], e);
      P.line(lf[1][0], lf[1][1], lf[2][0], lf[2][1], e);
      // ışık: üstün ön kenarları
      P.line(top[3][0] + 1, top[3][1], top[2][0], top[2][1] - 1, h);
      P.line(top[2][0], top[2][1] - 1, top[1][0] - 1, top[1][1], h);
    }
    /* sol yüz (v sabit) düzleminde dikdörtgen; sağ yüz (u sabit) */
    fl(u0, u1, v, z0, z1, c) { this.P.poly([this.p(u0, v, z0), this.p(u1, v, z0), this.p(u1, v, z1), this.p(u0, v, z1)], c); }
    fr(u, v0, v1, z0, z1, c) { this.P.poly([this.p(u, v1, z0), this.p(u, v0, z0), this.p(u, v0, z1), this.p(u, v1, z1)], c); }
    top(u0, v0, u1, v1, z, c) { this.P.poly([this.p(u0, v0, z), this.p(u1, v0, z), this.p(u1, v1, z), this.p(u0, v1, z)], c); }
    ln(u0, v0, z0, u1, v1, z1, c) { const a = this.p(u0, v0, z0), b = this.p(u1, v1, z1); this.P.line(a[0], a[1], b[0], b[1], c); }
    dot(u, v, z, c) { const a = this.p(u, v, z); this.P.set(a[0], a[1], c); }
  }
  O.Iso = Iso;

  /* karo sprite: çıpa = karonun üst köşesi (ax, ay) */
  O.tspr = function (zmax, fn, o) {
    o = o || {};
    const w = o.w || 48, ax = o.ax || w / 2, ay = zmax + 4, h = ay + HH * 2 + 6;
    const P = new Px(w, h), I = new Iso(P, ax, ay);
    fn(I, P);
    return { c: P.flush(), ax: ax, ay: ay, w: w, h: h };
  };
  /* serbest sprite (çıpa = ayak noktası) */
  O.fspr = function (w, h, ax, ay, fn) {
    const P = new Px(w, h);
    fn(P);
    return { c: P.flush(), ax: ax, ay: ay, w: w, h: h, P: P };
  };
})();
