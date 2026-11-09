/* Pages önbelleği yüzünden yeni sürüm geç göründüğü için yerel CSS/JS çağrılarına ?v=<sürüm> ekler.
   Kullanım:  node tools/surum.js [sürüm]   (sürüm verilmezse: git kısa sha'sı, olmazsa tarih)
   Dokunduğu dosyalar: index.html, ofis/index.html. Dış (http…) adresler ve vendor/ dosyaları sabit sürümlüdür, atlanır. */
'use strict';
const fs = require('fs'), path = require('path'), cp = require('child_process');
const root = path.join(__dirname, '..'), DOSYALAR = ['index.html', 'ofis/index.html'];
const RE = /(<(?:script|link)\b[^>]*?\b(?:src|href)=")([^"?#]+\.(?:js|css))(?:\?v=[^"]*)?(")/g;
function varsayilan() {
  try { return cp.execSync('git rev-parse --short HEAD', { cwd: root, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch (e) { return new Date().toISOString().slice(0, 16).replace(/\D/g, ''); }
}
function damga(html, v) { return html.replace(RE, (m, a, f, z) => (/^(https?:)?\/\//.test(f) || /^vendor\//.test(f) ? m : `${a}${f}?v=${v}${z}`)); }
module.exports = { damga, RE, DOSYALAR };
if (require.main === module) {
  const v = process.argv[2] || varsayilan();
  if (!/^[A-Za-z0-9._-]+$/.test(v)) { console.error('geçersiz sürüm: ' + v); process.exit(1); }
  DOSYALAR.forEach(f => { const p = path.join(root, f), s = fs.readFileSync(p, 'utf8'), n = damga(s, v); if (n !== s) fs.writeFileSync(p, n); console.log(f + ' → ?v=' + v); });
}
