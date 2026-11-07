/* Sürüm sorgusu denetimi:  node test/surum.test.js
   Her yerel CSS/JS çağrısı (kök index.html, ofis/index.html) ?v=<sürüm> taşır, tek sürüm kullanılır, dosya vardır; vendor/ ve dış adresler atlanır. */
'use strict';
const fs = require('fs'), path = require('path');
const { damga, DOSYALAR } = require('../tools/surum.js');
const root = path.join(__dirname, '..');
let bad = 0;
const ok = (n, c, x) => { if (!c) bad++; console.log((c ? 'OK   ' : 'FAIL ') + n + (x ? ' → ' + x : '')); };
const sur = new Set();
for (const f of DOSYALAR) {
  const html = fs.readFileSync(path.join(root, f), 'utf8'), dir = path.dirname(path.join(root, f));
  const refs = [...html.matchAll(/<(?:script|link)\b[^>]*?\b(?:src|href)="([^"#]+\.(?:js|css)[^"#]*)"/g)].map(m => m[1]);
  const yerel = refs.filter(r => !/^(https?:)?\/\//.test(r) && !/^vendor\//.test(r));
  const eksik = yerel.filter(r => !/\?v=[A-Za-z0-9._-]+$/.test(r));
  ok(`${f}: ${yerel.length} yerel CSS/JS çağrısının hepsi ?v= taşır`, eksik.length === 0, eksik.join(', '));
  yerel.forEach(r => sur.add(r.split('?v=')[1]));
  if (!yerel.length) console.log(`NOT ${f}: yerel CSS/JS çağrısı yok (yalnız sürümü dosya adında sabit vendor/ dosyaları; kod sayfanın içinde)`);
  ok(`${f}: çağrılan dosyalar mevcut`, yerel.every(r => fs.existsSync(path.join(dir, r.split('?')[0]))));
  ok(`${f}: vendor/ ve dış adresler dokunulmamış`, refs.filter(r => /^vendor\//.test(r) || /^(https?:)?\/\//.test(r)).every(r => !/\?v=/.test(r)));
  ok(`${f}: damga() tekrar çalıştırılınca değişmez (idempotent)`, damga(html, [...sur][0]) === html);
}
ok('ofis/index.html en az bir yerel çağrı taşır', sur.size >= 1);
ok('tek sürüm değeri kullanılır', sur.size === 1, [...sur].join(','));
ok('damga(): eski ?v= değişir, vendor ve http atlanır', damga('<script src="a.js?v=1"></script><link href="vendor/x.css"><script src="https://x/y.js"></script>', '2') === '<script src="a.js?v=2"></script><link href="vendor/x.css"><script src="https://x/y.js"></script>');
console.log(bad ? '\n' + bad + ' test başarısız' : '\nhepsi geçti'); process.exit(bad ? 1 : 0);
