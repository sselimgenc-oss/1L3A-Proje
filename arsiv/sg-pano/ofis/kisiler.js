/* Ofis · kişi figürleri, sandalye ve balon simgeleri (kodla çizilir). */
(function () {
  'use strict';
  const O = window.OFIS, C = O.C, shade = O.shade, fspr = O.fspr;
  const INK = '#2a2230';
  const SKIN = ['#f3cfa8', '#e5b88e', '#c98f62', '#a46b45', '#7b4a2e', '#f6d9bd'];
  const HAIR = ['#2b2118', '#4a3322', '#7a4a26', '#c4893a', '#d9d4c8', '#1c2438', '#8a2f2f', '#5b3b6e'];
  O.SKIN = SKIN; O.HAIR = HAIR;
  const cache = {};

  function legs(P, ax, ay, o, pose) {
    const pc = o.pants, sc = '#262a33';
    const a = pose === 'w0' ? 1 : 0, b = pose === 'w1' ? 1 : 0;
    P.rect(ax - 4, ay - 6 + a, 4, 6 - a, pc); P.rect(ax, ay - 6 + b, 4, 6 - b, pc);
    P.rect(ax - 4, ay - 6 + a, 1, 6 - a, shade(pc, 0.8)); P.rect(ax + 3, ay - 6 + b, 1, 6 - b, shade(pc, 0.8));
    P.rect(ax - 4, ay - 1 + a, 4, 1, sc); P.rect(ax, ay - 1 + b, 4, 1, sc);
    if (pose === 'w0' || pose === 'w1') { P.set(ax - 5 + (pose === 'w0' ? 0 : 0), ay - 1, sc); }
  }
  function torso(P, ax, ty, o, pose, front) {
    const sh = o.shirt;
    P.rect(ax - 5, ty, 10, 8, sh);
    P.rect(ax - 5, ty, 10, 1, shade(sh, 1.18));
    P.rect(ax + 3, ty + 1, 2, 7, shade(sh, 0.82));
    const sw = pose === 'w0' ? 1 : pose === 'w1' ? -1 : 0;
    // kollar
    P.rect(ax - 7, ty + 1 + (sw > 0 ? 1 : 0), 2, 6, sh); P.rect(ax + 5, ty + 1 + (sw < 0 ? 1 : 0), 2, 6, shade(sh, 0.85));
    P.rect(ax - 7, ty + 7 + (sw > 0 ? 1 : 0), 2, 1, o.skin); P.rect(ax + 5, ty + 7 + (sw < 0 ? 1 : 0), 2, 1, o.skin);
    if (front) {
      if (o.acc === 'tie') { P.rect(ax - 1, ty, 2, 6, '#b0302c'); P.rect(ax - 1, ty, 2, 1, '#fff'); }
      if (o.acc === 'apron') { P.rect(ax - 4, ty + 3, 8, 5, '#f4f1ea'); P.rect(ax - 4, ty + 3, 8, 1, '#d8d2c4'); }
      if (o.acc === 'vest') { P.rect(ax - 5, ty, 3, 8, '#f28c28'); P.rect(ax + 2, ty, 3, 8, '#f28c28'); P.rect(ax - 5, ty + 5, 10, 1, '#fff1a8'); }
      if (o.acc === 'coat') { P.rect(ax - 5, ty, 10, 8, '#f1f3f6'); P.rect(ax - 1, ty, 2, 8, shade(o.shirt, 1)); }
    } else {
      if (o.acc === 'vest') { P.rect(ax - 5, ty, 10, 8, '#f28c28'); P.rect(ax - 5, ty + 5, 10, 1, '#fff1a8'); }
      if (o.acc === 'coat') P.rect(ax - 5, ty, 10, 8, '#f1f3f6');
      if (o.acc === 'apron') P.rect(ax - 2, ty + 4, 4, 1, '#f4f1ea');
    }
  }
  function head(P, ax, hy, o, front) {
    // 8x8 kafa; hy = üst satır
    P.rect(ax - 4, hy + 1, 8, 7, o.skin);
    P.rect(ax - 3, hy, 6, 1, o.skin);
    P.rect(ax + 2, hy + 3, 2, 5, shade(o.skin, 0.9));
    const hc = o.hair, hd = shade(hc, 0.75);
    if (front) {
      P.rect(ax - 4, hy - 1, 8, 3, hc); P.rect(ax - 3, hy - 2, 6, 1, hc); P.rect(ax - 4, hy + 2, 1, 2, hc); P.rect(ax + 3, hy + 2, 1, 2, hc);
      P.rect(ax - 2, hy + 2, 4, 1, hc);
      if (o.hs === 'long') { P.rect(ax - 5, hy + 1, 2, 9, hc); P.rect(ax + 3, hy + 1, 2, 9, hd); }
      if (o.hs === 'bun') P.rect(ax - 1, hy - 4, 3, 2, hc);
      if (o.hs === 'bald') { P.rect(ax - 4, hy - 1, 8, 3, o.skin); P.rect(ax - 3, hy - 2, 6, 1, o.skin); P.rect(ax - 4, hy + 2, 1, 2, hd); P.rect(ax + 3, hy + 2, 1, 2, hd); }
      P.set(ax - 2, hy + 4, INK); P.set(ax + 1, hy + 4, INK);
      P.set(ax - 2, hy + 6, shade(o.skin, 0.78)); P.set(ax - 1, hy + 6, shade(o.skin, 0.78));
      if (o.acc === 'glasses') { P.rect(ax - 3, hy + 3, 3, 3, '#00000000'); P.hline(ax - 3, hy + 3, 3, '#1d2430'); P.hline(ax, hy + 3, 3, '#1d2430'); P.set(ax - 3, hy + 4, '#1d2430'); P.set(ax + 2, hy + 4, '#1d2430'); P.set(ax - 2, hy + 5, '#aee0ff'); P.set(ax + 1, hy + 5, '#aee0ff'); }
      if (o.acc === 'beard') { P.rect(ax - 3, hy + 6, 6, 2, hd); P.rect(ax - 1, hy + 6, 2, 1, o.skin); }
    } else {
      P.rect(ax - 4, hy - 1, 8, 8, hc); P.rect(ax - 3, hy - 2, 6, 1, hc);
      P.rect(ax + 2, hy + 1, 2, 6, hd);
      P.rect(ax - 4, hy + 6, 8, 1, hd);
      if (o.hs === 'long') { P.rect(ax - 5, hy + 1, 2, 10, hc); P.rect(ax + 3, hy + 1, 2, 10, hd); P.rect(ax - 4, hy + 7, 8, 3, hc); }
      if (o.hs === 'bun') P.rect(ax - 1, hy - 4, 3, 2, hc);
      if (o.hs === 'bald') { P.rect(ax - 4, hy - 1, 8, 7, o.skin); P.rect(ax - 3, hy - 2, 6, 1, o.skin); P.rect(ax - 4, hy + 5, 8, 1, hd); }
    }
    if (o.acc === 'cap') { P.rect(ax - 5, hy - 2, 10, 3, '#1f3a6e'); P.rect(ax - 3, hy - 3, 6, 1, '#1f3a6e'); if (front) P.rect(ax - 5, hy + 1, 10, 1, '#16294f'); P.set(ax, hy - 2, '#f5cb5c'); }
    if (o.acc === 'visor') { P.rect(ax - 5, hy, 10, 2, '#2c8c4a'); P.rect(ax - 5, hy + 2, 10, 1, shade('#2c8c4a', 0.7)); }
    if (o.acc === 'headset') { P.rect(ax - 5, hy + 2, 1, 4, '#222a38'); P.rect(ax + 4, hy + 2, 1, 4, '#222a38'); P.hline(ax - 4, hy - 2, 8, '#222a38'); if (front) { P.rect(ax - 5, hy + 5, 3, 1, '#222a38'); P.set(ax - 3, hy + 6, '#f5cb5c'); } }
  }

  /* kişi: view 'b'|'f', pose 'stand'|'w0'|'w1'|'sit' */
  function person(o, view, pose) {
    const front = view === 'f';
    return fspr(28, 40, 14, 34, P => {
      const ax = 14, ay = 34;
      P.disc(ax, ay, 7, 2.6, O.pk(0, 0, 0, 48));
      if (pose === 'sit') {
        // oturan: sandalye arkası ön planda (arkadan görünüm)
        chairBase(P, ax, ay, o.chair);
        torso(P, ax, ay - 17, o, 'stand', false); head(P, ax, ay - 26, o, false);
        chairBack(P, ax, ay, o.chair);
      } else if (pose === 'sitF') {
        chairBackBehind(P, ax, ay, o.chair);
        torso(P, ax, ay - 17, o, 'stand', true); head(P, ax, ay - 26, o, true);
      } else {
        legs(P, ax, ay, o, pose); torso(P, ax, ay - 14, o, pose, front); head(P, ax, ay - 23, o, front);
      }
      P.outline(INK);
    });
  }
  function chairBase(P, ax, ay, c) {
    P.rect(ax, ay - 5, 1, 4, '#3a4150'); P.rect(ax - 4, ay - 2, 9, 1, '#3a4150'); P.set(ax - 5, ay - 1, '#1c2130'); P.set(ax + 5, ay - 1, '#1c2130'); P.set(ax - 1, ay - 1, '#1c2130'); P.set(ax + 1, ay - 1, '#1c2130');
    P.rect(ax - 6, ay - 8, 12, 3, c); P.rect(ax - 6, ay - 8, 12, 1, shade(c, 1.25));
  }
  function chairBack(P, ax, ay, c) {
    P.rect(ax - 6, ay - 16, 12, 9, c); P.rect(ax - 6, ay - 16, 12, 1, shade(c, 1.3)); P.rect(ax + 4, ay - 15, 2, 8, shade(c, 0.78));
    P.rect(ax - 5, ay - 14, 1, 5, shade(c, 1.15));
  }
  function chairBackBehind(P, ax, ay, c) {
    chairBase(P, ax, ay, c);
    P.rect(ax - 7, ay - 27, 14, 18, c); P.rect(ax - 7, ay - 27, 14, 1, shade(c, 1.3)); P.rect(ax + 5, ay - 26, 2, 17, shade(c, 0.78));
  }
  function emptyChair(c, face) {
    return fspr(28, 40, 14, 34, P => {
      const ax = 14, ay = 34;
      P.disc(ax, ay, 7, 2.6, O.pk(0, 0, 0, 40));
      chairBase(P, ax, ay, c);
      if (face === 'f') P.rect(ax - 6, ay - 22, 12, 14, c);
      chairBack(P, ax, ay, c); P.outline(INK);
    });
  }
  function flip(s) {
    const c = document.createElement('canvas'); c.width = s.w; c.height = s.h;
    const x = c.getContext('2d'); x.translate(s.w, 0); x.scale(-1, 1); x.drawImage(s.c, 0, 0);
    return { c: c, w: s.w, h: s.h, ax: s.w - s.ax, ay: s.ay };
  }
  O.flip = flip;
  O.look = function (seed, role, extra) {
    const r = O.rng(seed * 2654435761 + 11);
    const shirts = ['#d4553b', '#3b82c4', '#e0a93a', '#3aa17a', '#8a63c9', '#2f9aa8', '#d86b8f', '#6b7a8f', '#7aa83a', '#c0683a'];
    const pants = ['#2c3342', '#3b4256', '#4a3a34', '#2f4a62', '#55525c'];
    const o = { skin: SKIN[Math.floor(r() * SKIN.length)], hair: HAIR[Math.floor(r() * HAIR.length)], shirt: shirts[Math.floor(r() * shirts.length)], pants: pants[Math.floor(r() * pants.length)], hs: ['short', 'short', 'long', 'bun', 'short', 'bald'][Math.floor(r() * 6)], acc: r() < 0.18 ? 'glasses' : r() < 0.12 ? 'beard' : '', chair: ['#3a4254', '#4a5568', '#2f3b52', '#5a3f6e', '#3d5a52', '#6a4a3a'][Math.floor(r() * 6)] };
    if (o.hs === 'long' || o.hs === 'bun') { if (o.acc === 'beard') o.acc = ''; }
    return Object.assign(o, extra || {});
  };
  /* sprite al: pose 'stand'|'w0'|'w1'|'sit'|'sitF'; yön: dx,dy karo hareket yönü */
  O.person = function (o, pose, dir) {
    const key = JSON.stringify(o) + pose + dir;
    if (cache[key]) return cache[key];
    const front = pose === 'sitF' || dir === 'd' || dir === 'r';
    const mirror = (dir === 'l' || dir === 'r') && pose !== 'sit' && pose !== 'sitF';
    let s = person(o, front ? 'f' : 'b', pose);
    if (mirror) s = flip(s);
    return (cache[key] = s);
  };
  O.chairSpr = function (c, face) { const k = 'ch' + c + face; return cache[k] || (cache[k] = emptyChair(c, face)); };

  /* ---------- balon simgeleri ---------- */
  const GLY = {
    uyari: ['..#..', '..#..', '..#..', '..#..', '.....', '..#..'],
    zarf: ['#########', '##.....##', '#.#...#.#', '#..#.#..#', '#...#...#', '#########'],
    tik: ['.......#', '......##', '#....##.', '##..##..', '.####...', '..##....'],
    para: ['..###..', '.#.#.#.', '.#.#...', '..###..', '...#.#.', '.#.#.#.', '..###..'],
    belge: ['.#####.', '.#...#.', '.#.#.#.', '.#...#.', '.#.#.#.', '.#####.'],
    goz: ['..###..', '.#...#.', '#..#..#', '.#...#.', '..###..'],
    yukari: ['...#...', '..###..', '.#.#.#.', '...#...', '...#...', '...#...'],
    asagi: ['...#...', '...#...', '...#...', '.#.#.#.', '..###..', '...#...'],
    arama: ['.###...', '#...#..', '#...#..', '#...#..', '.###.#.', '.....##'],
    kapi: ['.#####.', '.#...#.', '.#..##.', '.#...#.', '.#...#.', '.#####.'],
    saat: ['..###..', '.#.#.#.', '#..#..#', '#..##.#', '.#...#.', '..###..'],
    kilit: ['..###..', '.#...#.', '.#...#.', '#######', '###.###', '#######'],
    gulumse: ['.#...#.', '.#...#.', '.......', '#.....#', '.#...#.', '..###..'],
    bayrak: ['#####..', '######.', '#####..', '#......', '#......', '#......']
  };
  O.bubble = function (name, color) {
    const k = 'bub' + name + color;
    if (cache[k]) return cache[k];
    const g = GLY[name] || GLY.uyari, gw = g[0].length, w = gw + 8, h = g.length + 12;
    return (cache[k] = fspr(w, h, Math.floor(w / 2), h - 1, P => {
      P.rect(1, 1, w - 2, g.length + 6, '#ffffff'); P.rect(0, 2, 1, g.length + 4, '#ffffff'); P.rect(w - 1, 2, 1, g.length + 4, '#ffffff');
      P.poly([[Math.floor(w / 2) - 2, g.length + 7], [Math.floor(w / 2) + 3, g.length + 7], [Math.floor(w / 2), g.length + 10]], '#ffffff');
      g.forEach((row, y) => { for (let x = 0; x < gw; x++) if (row[x] === '#') P.set(4 + x, 4 + y, color); });
      P.outline('#1b2236');
    }));
  };
  O.icons = {
    envelope: () => cache.env || (cache.env = fspr(16, 12, 8, 6, P => {
      P.rect(1, 1, 14, 10, '#fbf7ea'); P.line(1, 1, 8, 7, '#c9bfa6'); P.line(14, 1, 8, 7, '#c9bfa6'); P.line(1, 10, 6, 6, '#e3dac2'); P.line(14, 10, 10, 6, '#e3dac2');
      P.rect(7, 6, 2, 2, '#d4553b'); P.outline('#2a2230');
    })),
    coin: () => cache.coin || (cache.coin = fspr(10, 10, 5, 5, P => { P.disc(5, 5, 4, 4, '#f5cb5c'); P.disc(4, 4, 2, 2, '#fff0a8'); P.rect(4, 3, 2, 4, '#b98a1e'); P.outline('#5a3f0a'); })),
    not: () => cache.not || (cache.not = fspr(12, 13, 6, 12, P => { P.rect(1, 1, 10, 11, '#fff3b0'); P.rect(1, 1, 10, 2, '#f0d760'); P.rect(3, 5, 6, 1, '#8a7a2a'); P.rect(3, 7, 5, 1, '#8a7a2a'); P.rect(3, 9, 4, 1, '#8a7a2a'); P.outline('#4a3f12'); })),
    bayrakNot: () => cache.bayrakNot || (cache.bayrakNot = fspr(14, 18, 7, 17, P => { P.rect(2, 1, 1, 16, '#5a3a2a'); P.rect(3, 1, 9, 6, '#e23a2e'); P.rect(3, 1, 9, 1, '#ff7a6a'); P.rect(4, 7, 1, 1, '#a82020'); P.outline('#2a1210'); })),
    kutu: () => cache.kutu || (cache.kutu = fspr(14, 14, 7, 13, P => { P.rect(1, 3, 12, 10, '#c9a46a'); P.rect(1, 3, 12, 3, '#dcb97f'); P.rect(5, 3, 4, 3, '#f1e6c8'); P.rect(1, 12, 12, 1, '#8e6e3e'); P.outline('#4a3418'); }))
  };
})();
