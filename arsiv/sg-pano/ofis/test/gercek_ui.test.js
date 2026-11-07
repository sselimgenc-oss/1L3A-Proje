/* Ofis gerçek veri arayüz testi:  node ofis/test/gercek_ui.test.js   (Playwright + Chromium; GitHub istekleri yakalanır, UYDURMA fixture)
   Kapsam: varsayılan kaynak gerçek veri, ön izleme şeridi, örnek yalnız ?durum=ornek, gri odalar, gizli kontrol odası, körlük, hata yolu. */
'use strict';
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const F = require('./fixture.js'), G = require('../gercek.js');
const root = path.join(__dirname, '..', '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.md': 'text/plain' };
let bad = 0;
const ok = (n, c, x) => { if (!c) bad++; console.log((c ? 'OK   ' : 'FAIL ') + n + (x !== undefined && x !== '' ? ' → ' + x : '')); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const json = b => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) });

const srv = http.createServer((q, r) => {
  let p = decodeURIComponent(q.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html';
  fs.readFile(path.join(root, p), (e, d) => { if (e) { r.writeHead(404); r.end('nf'); return; } r.writeHead(200, { 'content-type': (TYPES[path.extname(p)] || 'application/octet-stream') + '; charset=utf-8' }); r.end(d); });
}).listen(0, async () => {
  const base = 'http://localhost:' + srv.address().port + '/ofis/';
  const b = await chromium.launch(), errs = [], istek = [];
  async function open(url, opt) {
    opt = opt || {};
    const ctx = await b.newContext({ viewport: opt.vp || { width: 1440, height: 900 } });
    const pg = await ctx.newPage();
    pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
    pg.on('request', q => { if (/api\.github\.com|raw\.githubusercontent\.com/.test(q.url())) istek.push(q.url()); });
    await pg.route('https://api.github.com/**', r => (opt.agacHata ? r.fulfill({ status: 403, body: '{}' }) : r.fulfill(json(F.agac(['2026-10-28'], ['2026-10-28'])))));
    await pg.route('https://raw.githubusercontent.com/**', r => {
      const u = r.request().url();
      if (opt.son && u === G.HAM + 'son.json') return r.fulfill(json({ kapi: '2026-10-28', secim: '2026-10-28' }));
      if (u === G.HAM + 'secim/2026-10-28/secim.json') return r.fulfill(json(F.secim('2026-10-28', null)));
      if (u === G.HAM + 'copytrade/kapi/2026-10-28/durum.json') return r.fulfill(json(F.durum));
      return r.fulfill({ status: 404, body: '' });
    });
    await pg.goto(base + (url || '?saat=15:40'));
    if (!opt.hataBekle) await pg.waitForFunction('window.OFIS&&window.OFIS.ready', null, { timeout: 8000 });
    else await sleep(800);
    return { ctx, pg };
  }
  const govde = pg => pg.evaluate(() => document.querySelector('aside').textContent);

  /* ---------- A. varsayılan: gerçek veri ---------- */
  let { ctx, pg } = await open();
  ok('varsayılan açılış ağ yolundan veri alır (son.json 404 → API, kapı ve canlı izleme; örnek yok)', istek.length === 5 && istek[0] === G.HAM + 'son.json' && istek[1] === G.AGAC && istek[4] === G.IZLEME_HAM, istek.join(' | '));
  const sera = await pg.evaluate(() => ({ on: !document.getElementById('onizlemeFlt').hidden, t: document.getElementById('onizlemeMetin').textContent, o: !document.getElementById('ornekFlt').hidden, r: document.getElementById('onizlemeFlt').getBoundingClientRect() }));
  ok('canlı etiket eşleşmezse üst şerit veri yok der', sera.on && sera.t === 'Seçim v1 — veri yok (2026-10-28)', sera.t);
  ok('şerit ekranın içinde ve görünür', sera.r.width > 100 && sera.r.top >= 0 && sera.r.top < 120);
  ok('örnek veri şeridi yok', !sera.o);
  const durum = await pg.evaluate(() => { const s = OFIS.Office.state(), n = k => s.actors.filter(a => a.kind === 'trader' && a.kat === k).length; return { oda: n('oda'), aday: n('aday'), lab: n('lab'), kontrol: n('kontrol'), gri: ['lab', 'finans', 'risk', 'oda', 'aday'].map(r => OFIS.Office.gri(r)), gizli: !!OFIS.World.roomById.kontrol.gizli, out: !!OFIS.World.roomById.kontrol.out, kaynak: OFIS.data.kaynak }; });
  ok('figürler: oda 6, aday 3, lab 0, kontrol 0', durum.oda === 6 && durum.aday === 3 && durum.lab === 0 && durum.kontrol === 0, JSON.stringify(durum));
  ok('gri odalar: lab, finans, risk; oda ve aday gri değil', durum.gri.join('|') === 'sanal izleme başlamadı|sanal izleme başlamadı|sanal izleme başlamadı||' || (durum.gri[0] && durum.gri[1] && durum.gri[2] && !durum.gri[3] && !durum.gri[4]), JSON.stringify(durum.gri));
  ok('kontrol odası gizli (etkileşim dışı)', durum.gizli && durum.out);
  const t = await govde(pg);
  ok('sol panel: kasa/risk "sanal izleme başlamadı"', (t.match(/sanal izleme başlamadı/g) || []).length >= 7, String((t.match(/sanal izleme başlamadı/g) || []).length));
  ok('"örnek" rozeti ve "örnek veri" yazısı yok', !/örnek/i.test(t.replace(/Örnek veri yalnız[^\n]*/i, '')), (t.match(/.{20}örnek.{20}/i) || [''])[0]);
  ok('körlük: para birimi ($), K/Z, "puan" yok', !/\$\d/.test(t) && !/K\/Z/.test(t) && !/puan/i.test(t), (t.match(/.{15}(\$\d|K\/Z|puan).{15}/i) || [''])[0]);
  ok('etiket eşleşmezse kontrol veri yoktur; örnek kontrol figürü yok', /Kontrol \(sabit\)\s*N=5/i.test(t) && (t.match(/KONTROL GRUBU/gi) || []).length === 0, (t.match(/.{10}ontrol.{20}/g) || []).join(' | '));
  ok('sol panelde Oda/Aday/Havuz sayıları gerçek: 6, 9, 30', /Oda\s*6/i.test(t) && /Aday\s*9/i.test(t) && /Havuz\s*30/i.test(t));
  /* oda bilgileri */
  const bilgi = await pg.evaluate(() => ['tarama', 'kapi', 'lab', 'finans', 'risk', 'oda'].map(r => OFIS.Office.roomInfo(r).lines.join(' ')));
  ok('Tarama odası: evren 13.710 · işlenen 13.767', /Evren: 13\.710/.test(bilgi[0]) && /İşlenen: 13\.767/.test(bilgi[0]), bilgi[0]);
  ok('Kapı odası: havuz 30 · aday 9 · oda 6', /Havuz: 30 · Aday: 9 · Oda: 6/.test(bilgi[1]), bilgi[1]);
  ok('Lab, Finans, Risk odası bilgisi: sanal izleme başlamadı', bilgi.slice(2, 5).every(x => /^sanal izleme başlamadı\.$/.test(x)), bilgi.slice(2, 5).join('|'));
  ok('Oda bilgisi kontrol/para içermez', !/kontrol|\$/i.test(bilgi[5]), bilgi[5]);
  /* trader bilgi kutusu */
  await pg.evaluate(() => { const a = OFIS.Office.state().actorById.O01; OFIS.Info.show ? OFIS.Info.show({ type: 'person', a: a }) : null; });
  await sleep(300);
  const kutu = await pg.evaluate(() => (document.getElementById('bilgi') || {}).innerText || '');
  ok('trader bilgisi: aday sırası, tarz, kaldıraç; puan/K-Z yok', /Aday sırası\s*#1/.test(kutu) && /intraday/.test(kutu) && /En yüksek kaldıraç\s*3x/.test(kutu) && !/puan|K\/Z|\$/i.test(kutu), kutu.slice(0, 260).replace(/\n/g, ' | '));
  /* kontrol odasına gidiş engellenir */
  await pg.goto(base + '?saat=15:40#oda/kontrol'); await pg.waitForFunction('window.OFIS&&window.OFIS.ready'); await sleep(500);
  ok('#oda/kontrol açılmaz', await pg.evaluate(() => !OFIS.debug.mode.active || OFIS.debug.mode.room !== 'kontrol'));
  await pg.screenshot({ path: path.join(__dirname, '..', '..', 'docs', 'ofis_gercek_veri_bina.png') });
  await ctx.close();

  /* ---------- A2. son.json varsa API çağrılmaz ---------- */
  istek.length = 0;
  ({ ctx, pg } = await open('?saat=15:40', { son: true }));
  ok('son.json işaretçisi: GitHub API hiç çağrılmaz (4 ham istek)', istek.length === 4 && !istek.some(u => /api\.github\.com/.test(u)), istek.join(' | '));
  await ctx.close();

  /* ---------- A3. telefon: rozet, yakın açılış, gece konturu ---------- */
  ({ ctx, pg } = await open('?saat=12:00', { vp: { width: 390, height: 844 } }));
  const tz = await pg.evaluate(() => ({ z: OFIS.debug.cam.z, kont: OFIS.Office.konturN || 0 }));
  const yak = await pg.evaluate(() => { const r = OFIS.debug.interest(), v = OFIS.debug.view, z0 = Math.min(v.w / (r.x1 - r.x0 + 28), v.h / (r.y1 - r.y0 + 40)); return { oran: OFIS.debug.cam.z / z0 }; });
  ok('telefon: açılışta kamera sığdırmadan %12 yakın', Math.abs(yak.oran - 1.12) < 0.01, JSON.stringify(yak));
  const rozet = await pg.evaluate(() => { const s = OFIS.Office.state(); return ['oda', 'aday'].map(id => s.actors.some(a => a.kind === 'trader' && a.kat === id) + ':' + s.katlar[id].n); });
  ok('telefon: dolu masalı odalarda rozet verisi (Oda 6, Aday 9)', rozet.join() === 'true:6,true:9', rozet.join());
  await pg.screenshot({ path: path.join(__dirname, '..', '..', 'docs', 'ofis_gercek_veri_telefon.png') });
  ok('gündüz: figür konturu çizilmez', (await pg.evaluate(() => OFIS.Office.konturN || 0)) === 0);
  await ctx.close();
  ({ ctx, pg } = await open('?saat=23:30', { vp: { width: 390, height: 844 } }));
  await sleep(300);
  ok('gece: figürlere kontur çizilir', (await pg.evaluate(() => OFIS.Office.konturN || 0)) > 0 && (await pg.evaluate(() => OFIS.Office.gece)) > 0.35);
  await ctx.close();

  /* ---------- B. örnek yalnız ?durum=ornek ---------- */
  istek.length = 0;
  ({ ctx, pg } = await open('?saat=15:40&durum=ornek'));
  const o = await pg.evaluate(() => ({ o: !document.getElementById('ornekFlt').hidden, on: !document.getElementById('onizlemeFlt').hidden, ort: document.getElementById('ornekFlt').textContent, n: OFIS.data.traderlar.length }));
  ok('?durum=ornek: örnek veri şeridi görünür, ön izleme şeridi yok, GitHub isteği yok', o.o && !o.on && /Örnek veri — gerçek veriye bağlı değil/.test(o.ort) && istek.length === 0 && o.n === 44, JSON.stringify(o));
  await ctx.close();

  /* ---------- C. veri okunamazsa sahte veri yok ---------- */
  ({ ctx, pg } = await open('?saat=15:40', { agacHata: true, hataBekle: true }));
  const h = await pg.evaluate(() => ({ t: document.getElementById('hata').textContent, v: !document.getElementById('hata').hidden, ready: !!(window.OFIS && window.OFIS.ready) }));
  ok('API sınırı/erişim hatası: "Sahte veri gösterilmiyor", örneğe düşülmez', h.v && /Sahte veri gösterilmiyor/.test(h.t) && /403/.test(h.t) && !h.ready, h.t);
  await ctx.close();

  /* ---------- D. telefon ---------- */
  ({ ctx, pg } = await open('?saat=15:40', { vp: { width: 390, height: 844 } }));
  const tel = await pg.evaluate(() => { const r = document.getElementById('onizlemeFlt').getBoundingClientRect(); return { h: !document.getElementById('onizlemeFlt').hidden, l: r.left, rt: r.right, w: innerWidth }; });
  ok('telefon: ön izleme şeridi görünür ve ekran dışına taşmaz', tel.h && tel.l >= 0 && tel.rt <= tel.w, JSON.stringify(tel));
  await ctx.close();

  ok('sayfa/konsol hatası yok', errs.length === 0, errs.join(' | ').slice(0, 300));
  await b.close(); srv.close();
  console.log(bad ? '\n' + bad + ' test başarısız' : '\nhepsi geçti');
  process.exit(bad ? 1 : 0);
});
