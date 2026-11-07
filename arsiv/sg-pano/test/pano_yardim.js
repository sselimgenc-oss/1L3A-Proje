/* Ana pano testleri için ortak yardımcılar: statik sunucu + ağ yakalama (canlı adresler yerel örnek veriye bağlanır, Hyperliquid taklit edilir). */
'use strict';
const http = require('http'), fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.md': 'text/plain', '.png': 'image/png' };

function sunucu() {
  return new Promise((ok) => {
    const s = http.createServer((q, r) => {
      let p = decodeURIComponent(q.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html';
      fs.readFile(path.join(root, p), (e, d) => { if (e) { r.writeHead(404); r.end('nf'); return; } r.writeHead(200, { 'content-type': (TYPES[path.extname(p)] || 'application/octet-stream') + '; charset=utf-8' }); r.end(d); });
    }).listen(0, () => ok({ s, base: 'http://localhost:' + s.address().port + '/' }));
  });
}

const ADRES = (n) => '0x' + String(n).padStart(40, '0');
const HL_POZ = (coin, szi, giris) => ({ position: { coin, szi: String(szi), entryPx: String(giris), unrealizedPnl: '120.5', leverage: { value: 3 } } });
/* opt: durum (özel durum.json nesnesi), kesif (özel kesif.json nesnesi | 'hata'), canliKesif (veri dalındaki kesif/kesif.json içeriği; yoksa 404), hl: false → Hyperliquid erişilemez.
   page.istekler: raw/API istek adresleri (sözleşme testi için). */
async function yakala(page, opt = {}) {
  const oku = (f) => JSON.parse(fs.readFileSync(path.join(root, f), 'utf8'));
  const json = (b) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) });
  page.istekler = [];
  page.on('request', (q) => { if (/raw\.githubusercontent\.com|api\.github\.com/.test(q.url())) page.istekler.push(q.url().replace(/[?&]t=\d+$/, '')); });
  await page.route('**/raw.githubusercontent.com/**', (r) => {
    const u = r.request().url();
    if (u.includes('/copytrade-kapi/kesif/kesif.json')) return opt.canliKesif ? r.fulfill(json(opt.canliKesif)) : r.fulfill({ status: 404, body: '' });
    if (u.includes('durum.json')) return r.fulfill(json(opt.durum || oku('izleme/ornek_durum.json')));
    if (u.includes('kararlar.jsonl')) return r.fulfill({ status: 404, body: '' });
    return r.fulfill({ status: 404, body: '' });
  });
  await page.route('**/api.github.com/**', (r) => r.fulfill({ status: 500, body: '{}' }));   // canlı keşif yok → yerel örneğe düşer
  if (opt.kesif) {
    await page.route('**/kesif/ornek_kesif.json*', (r) => opt.kesif === 'hata' ? r.fulfill({ status: 404, body: '' }) : r.fulfill(json(opt.kesif)));
  }
  await page.route('https://api.hyperliquid.xyz/info', (r) => {
    if (opt.hl === false) return r.abort();
    const b = JSON.parse(r.request().postData() || '{}');
    if (b.type === 'perpDexs') return r.fulfill(json([null]));
    if (b.type === 'allMids') return r.fulfill(json({ BTC: '70000', ETH: '3600', SOL: '170' }));
    if (b.type === 'clearinghouseState') return r.fulfill(json({ marginSummary: { accountValue: '150000' }, assetPositions: [HL_POZ('BTC', 0.16, 68400)] }));
    if (b.type === 'userFillsByTime') {
      const t = Date.now() - 3600e3;
      return r.fulfill(json([{ coin: 'BTC', oid: 1, tid: 1, side: 'B', sz: '0.16', px: '68400', time: t - 7200e3, startPosition: '0', closedPnl: '0', fee: '1' },
        { coin: 'ETH', oid: 2, tid: 2, side: 'A', sz: '2', px: '3500', time: t - 9000e3, startPosition: '0', closedPnl: '0', fee: '1' },
        { coin: 'ETH', oid: 3, tid: 3, side: 'B', sz: '2', px: '3450', time: t - 3600e3, startPosition: '-2', closedPnl: '100', fee: '1' }]));
    }
    return r.fulfill(json({}));
  });
}
module.exports = { sunucu, yakala, root, ADRES };
