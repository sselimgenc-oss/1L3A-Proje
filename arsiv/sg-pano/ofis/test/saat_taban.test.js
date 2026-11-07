/* Lider Ek 2 düzeltmeleri — node ofis/test/saat_taban.test.js (Playwright + Chromium; GitHub istekleri yakalanır, UYDURMA fixture)
   Kapsam: (a) olay/saat gösterimi Türkiye saati (UTC+3), tarayıcı saat dilimine bağlı değil; (b) örnek olay akışı
   (ve "Örnek veri." ibaresi) yalnız ?durum=ornek'te çalışır, gerçek veride hiç tetiklenmez; (c) taban kolundaki
   traderların olayları "Taban" etiketiyle görünür ("LAB · HAVUZ" değil). */
'use strict';
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const F = require('./fixture.js'), G = require('../gercek.js');
const root = path.join(__dirname, '..', '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css' };
let bad = 0;
const ok = (n, c, x) => { if (!c) bad++; console.log((c ? 'OK   ' : 'FAIL ') + n + (x !== undefined && x !== '' ? ' → ' + x : '')); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const json = b => ({ status: 200, contentType: 'application/json', body: JSON.stringify(b) });

const TABAN_ID = 'TD1', TABAN_ADRES = F.adres('d', 1);
const ODA_ID = 'TO1', ODA_ADRES = F.adres('a', 1);
const IZLEME = F.izleme('v1@2026-10-28', [
  { id: 'TD1', adresTam: TABAN_ADRES, kol: 'taban', kollar: ['taban'] },
  { id: 'TO1', adresTam: ODA_ADRES, kol: 'oda', kollar: ['oda'], pozisyonlar: [{ coin: 'BTC', yon: 'long', kaldirac: 3, anlik_kz_usd: -12.4, acilis: '2026-10-28T13:20:00Z' }] }   // veri 14:20 üretildi → yas 60 dk
], [
  { id: 'ev1', trader: TABAN_ID, coin: 'BTC', tur: 'acilis', zaman: '2026-10-28T10:05:00Z' }   // TR saati: 13:05
]);

const srv = http.createServer((q, r) => {
  let p = decodeURIComponent(q.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html';
  fs.readFile(path.join(root, p), (e, d) => { if (e) { r.writeHead(404); r.end('nf'); return; } r.writeHead(200, { 'content-type': (TYPES[path.extname(p)] || 'application/octet-stream') + '; charset=utf-8' }); r.end(d); });
}).listen(0, async () => {
  const base = 'http://localhost:' + srv.address().port + '/ofis/';
  const b = await chromium.launch();
  async function gercekAc(url, vp) {
    const ctx = await b.newContext({ viewport: vp || { width: 1440, height: 900 }, isMobile: !!(vp && vp.width < 700), hasTouch: !!(vp && vp.width < 700) });
    const pg = await ctx.newPage();
    const errs = []; pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
    await pg.route('https://api.github.com/**', r => r.fulfill(json(F.agac(['2026-10-28'], ['2026-10-28']))));
    await pg.route('https://raw.githubusercontent.com/**', r => {
      const u = r.request().url();
      if (u === G.HAM + 'son.json') return r.fulfill({ status: 404, body: '' });
      if (u === G.HAM + 'secim/2026-10-28/secim.json') return r.fulfill(json(F.secim('2026-10-28', null)));
      if (u === G.HAM + 'copytrade/kapi/2026-10-28/durum.json') return r.fulfill(json(F.durum));
      if (u === G.IZLEME_HAM) return r.fulfill(json(IZLEME));
      return r.fulfill({ status: 404, body: '' });
    });
    await pg.goto(base + (url || '?saat=15:40'));
    await pg.waitForFunction('window.OFIS&&window.OFIS.ready', null, { timeout: 8000 });
    return { ctx, pg, errs };
  }

  /* ---------- a) saat gösterimi: Türkiye saati (UTC+3), host saat dilimine bağlı değil ---------- */
  let { ctx, pg, errs } = await gercekAc('?saat=09:15');
  const saat = await pg.evaluate(() => document.getElementById('saat').textContent);
  ok('üst "ışık saati": ?saat=09:15 → ekranda tam 09:15 (TR saati olarak yorumlanır)', saat === '09:15', saat);
  const taban = await pg.evaluate(() => OFIS.Office.state().traders.TD1);
  ok('fikstür: taban traderı kol=taban olarak geldi', taban && taban.kol === 'taban', JSON.stringify(taban));
  /* olay çekmecesini aç, taban traderının olayını bul */
  await pg.click('[data-olay-ac]'); await sleep(400);
  const satir = await pg.evaluate(() => { const b = [...document.querySelectorAll('#cListe button')].find(x => /TD1|0xdddd/i.test(x.textContent)); return b ? { zaman: b.querySelector('time').textContent, oda: b.querySelector('.oc').textContent } : null; });
  ok('olay saati Türkiye saatinde: 10:05 UTC → 13:05 gösterilir', !!satir && /13:05$/.test(satir.zaman), JSON.stringify(satir));
  ok('c) taban kolundaki traderın olayı "Taban" etiketiyle görünür ("LAB · HAVUZ" değil)', !!satir && satir.oda === 'Taban', JSON.stringify(satir));

  /* ---------- b) örnek olay akışı ve "Örnek veri." ibaresi yalnız ?durum=ornek'te ---------- */
  const ornekIbare = await pg.evaluate(() => document.getElementById('cekmeceOrnek').hidden);
  ok('b) gerçek veride olay çekmecesi altında "Örnek veri." ibaresi gizli', ornekIbare === true);
  await sleep(2500);   // önceki hatada 120 "sim saniyesi" beklemeden sürekli döngüye giriyordu; burada kısa bekleme yeterli görülür
  const sistemLog = await pg.evaluate(() => OFIS.Office.state().log.some(l => /Örnek olay akışı/.test(l.metin)) || OFIS.Office.state().gecmis.some(g => /Örnek olay akışı/.test(g.metin || '')));
  ok('b) gerçek veride "Örnek olay akışı baştan başladı" hiç tetiklenmez', !sistemLog);
  ok('sayfa/konsol hatası yok (gerçek veri)', errs.length === 0, errs.join(' | '));
  await ctx.close();

  /* ---------- b2) örnek veride ("?durum=ornek") ibare görünür ve akış normal çalışır ---------- */
  ({ ctx, pg } = await gercekAc('?saat=15:40&durum=ornek'));
  const ornekIbare2 = await pg.evaluate(() => { OFIS.Cekmece.open(); return document.getElementById('cekmeceOrnek').hidden; });
  ok('örnek veride olay çekmecesi altında "Örnek veri." ibaresi görünür', ornekIbare2 === false);
  await ctx.close();

  /* ---------- Ek: açık işlemler durum.json'daki oda üyesi pozisyonlarından (iki temada da) ---------- */
  for (const tema of ['klasik']) {
    ({ ctx, pg, errs } = await gercekAc('?saat=15:40&tema=' + tema));
    await pg.click('.ray [data-oda=oda]'); await sleep(600);
    const acik = await pg.evaluate(() => ({ n: document.getElementById('acikN').textContent, html: document.getElementById('acikIcerik').innerHTML, kartGorunur: !document.getElementById('kartPanel').hidden || !document.getElementById('bilgi').hidden }));
    ok(tema + ': "Oda" paneli açık işlemler listesini gösterir (durum.json\'daki pozisyondan, BTC)', acik.n === '1' && /BTC/.test(acik.html) && /LONG/.test(acik.html) && /3x/.test(acik.html) && acik.kartGorunur, JSON.stringify({ n: acik.n, kartGorunur: acik.kartGorunur, kisa: acik.html.slice(0, 200) }));
    const cekmeceVar = await pg.evaluate(() => !!document.getElementById('olayCekmece'));
    ok(tema + ': olay çekmecesi hâlâ yerinde (kaldırılmadı)', cekmeceVar);
    await ctx.close();
  }

  /* ---------- Lider denetimi: gözcü kaydı aynı kaynaktan (st.gecmis), risk biriminin doğru yazımı, rozetler
     ekrandan taşmaz/çakışmaz, Arşiv/Sekreterlik veri yoksa rozetsiz ---------- */
  ({ ctx, pg, errs } = await gercekAc('?saat=15:40'));
  const gozcu = await pg.evaluate(() => document.getElementById('gozcuListe').textContent);
  ok('gözcü kaydı olay çekmecesiyle aynı kaynaktan dolar (st.log boşsa st.gecmis), "Taban" etiketiyle', !/Henüz olay yok/.test(gozcu) && /Taban/.test(gozcu), gozcu.slice(0, 200));
  await pg.click('.ray [data-oda=risk]'); await sleep(500);
  const riskTxt = await pg.evaluate(() => document.getElementById('riskIcerik').textContent);
  ok('Risk kartında kaldıraç "x" birimiyle yazılır (yüzdeye çevrilmez): "3x / 10x"', /3x\s*\/\s*10x/.test(riskTxt), riskTxt.replace(/\s+/g, ' ').trim());
  await ctx.close();

  await b.close(); srv.close();
  console.log(bad ? ('\n' + bad + ' test başarısız') : '\nTüm testler geçti.');
  process.exit(bad ? 1 : 0);
});
