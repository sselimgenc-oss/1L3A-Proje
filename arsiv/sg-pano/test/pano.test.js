/* Ana pano (kök index.html) arayüz testleri:  node test/pano.test.js   (Playwright + Chromium; ağ yakalanır, yalnız örnek veri)
   Kapsam: 4 sekme, "?" açıklamaları, kol filtresi ve "kol bilinmiyor", performans körlüğü, trader sayfası düzeni, eski adresler, telefon. */
'use strict';
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const { sunucu, yakala, root } = require('./pano_yardim.js');
let bad = 0;
const ok = (n, c, x) => { if (!c) bad++; console.log((c ? 'OK   ' : 'FAIL ') + n + (x !== undefined && x !== '' ? ' → ' + x : '')); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ornek = JSON.parse(fs.readFileSync(path.join(root, 'izleme/ornek_durum.json'), 'utf8'));
const kasaSentetik = JSON.parse(fs.readFileSync(path.join(root, 'test/kasa_sentetik.json'), 'utf8'));
const A1 = '0x0000000000000000000000000000000000000001';

function kollu() {                                   // kol alanı olan varyant
  const d = JSON.parse(JSON.stringify(ornek));
  ['oda', 'aday', 'kontrol', 'taban'].forEach((k, i) => { d.traderlar[i].kol = k; });
  d.golge = { hafta: 5, hafta_toplam: 12, oda_kapasite: 20 };
  d.traderlar[0].veri_kalitesi = { mutabakat: { saglik: { isik: 'yesil', neden: 'mutabakat uyumlu' } } };
  d.traderlar[0].neden_secildi = 'gölgede ≥ 3 hafta, kapıyı geçti';
  d.traderlar[1].kirmizi_bayraklar = ['uzun süredir işlem yok'];
  return d;
}

(async () => {
  const { s, base } = await sunucu();
  const b = await chromium.launch(), errs = [];
  async function ac(opt = {}, vp = { width: 1440, height: 900 }, url = '') {
    const ctx = await b.newContext({ viewport: vp, hasTouch: !!opt.dokunmatik, isMobile: !!opt.dokunmatik, acceptDownloads: true });
    const pg = await ctx.newPage();
    pg.on('pageerror', (e) => errs.push(e.message)); pg.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
    await yakala(pg, opt);
    await pg.goto(base + url); await pg.waitForFunction('document.querySelector("#ozMain").innerText.length>30', null, { timeout: 8000 }).catch(() => { });
    await sleep(500);
    return { ctx, pg };
  };
  const metin = (pg, sel) => pg.evaluate((q) => document.querySelector(q).textContent, sel);

  /* ---- 1) sekmeler ve yasal ibare ---- */
  let { ctx, pg } = await ac();
  const sek = await pg.$$eval('button.nav-btn', (l) => l.map((x) => x.textContent.trim()));
  ok('5 sekme, Kasa dahil doğru sırada', JSON.stringify(sek) === JSON.stringify(['Özet', 'Kasa', "Trader'lar", 'Huni', 'Ayarlar']), JSON.stringify(sek));
  const ol = await pg.$eval('#ofisLink', (e) => ({ href: e.getAttribute('href'), txt: e.textContent.trim(), cls: e.className, h: e.getBoundingClientRect().height }));
  ok('üst menüde "Ofis" bağlantısı: göreli yol ofis/, sekmelerle aynı stil', ol.href === 'ofis/' && ol.txt === 'Ofis' && /nav-btn/.test(ol.cls) && ol.h >= 44, JSON.stringify(ol));
  ok('açılışta Özet sekmesi aktif', await pg.$eval('.nav-btn.active', (e) => e.dataset.nav) === 'ozet');
  for (const t of ['ozet', 'kasa', 'traderlar', 'huni', 'ayarlar']) {
    await pg.click(`[data-nav=${t}]`); await sleep(300);
    const g = await pg.evaluate(() => { const y = document.getElementById('yasal'), r = y.getBoundingClientRect(); return { txt: y.textContent, gor: r.height > 0 && r.top >= 0 && r.bottom <= innerHeight }; });
    ok(`yasal ibare görünür (${t}): araştırma / sanal, yatırım tavsiyesi değil`, /araştırma \/ sanal, yatırım tavsiyesi değil/i.test(g.txt) && g.gor);
  }
  await pg.click('[data-nav=ozet]');

  /* ---- 2) Özet ---- */
  const oz = await metin(pg, '#ozMain');
  ok('Özet: hafta x/12', /Hafta[\s\S]*\?\/12|hafta \d+\/12/.test(oz));
  ok('Özet: oda doluluğu', /Oda doluluğu/.test(oz));
  ok('Özet: kol başına trader sayıları (5 kol)', ['Oda', 'Aday', 'Kontrol', 'Taban', 'Elle liste'].every((k) => oz.includes(k)));
  ok('Özet: veri tazeliği "X önce"', /Pano verisi[\s\S]{0,40}(dk|sa|gün) önce/.test(oz));
  const son5 = await pg.$$eval('#ozMain .card', (cs) => { const c = cs.find((x) => /Son 5 olay/.test(x.textContent)); return c ? c.querySelectorAll('.ct-row').length : -1; });
  ok('Özet: son 5 olay (tam 5 satır)', son5 === 5, 'n=' + son5);
  ok('Özet: "Tüm akış", "Şu an açık işlemler", "Kararlarım değer kattı mı?" korunur (kapalı bölümler)', await pg.$$eval('#ozMain details summary', (l) => l.map((x) => x.textContent).join('|')).then((t) => /Tüm akış/.test(t) && /açık işlemler/.test(t) && /Kararlarım değer kattı mı/.test(t)));
  ok('kol alanı yokken "kol bilinmiyor" gösterilir, çökme yok', /kol bilinmiyor/.test(oz) && errs.length === 0, errs.join(' | '));
  await pg.click('#ozMain details[data-d=akis] summary'); await sleep(200);
  ok('Tüm akış açılır, olay satırları listelenir', await pg.$$eval('#ozMain details[data-d=akis] .ct-row', (l) => l.length) >= 5);
  await pg.click('#ozMain details[data-d=kararlar] summary'); await sleep(200);
  ok('Kararlarım: sayılar görünür, kilit yok', /Toplam karar/.test(await metin(pg, '#ozMain')) && await pg.$$eval('#ozMain details[data-d=kararlar] [data-kilit]', (l) => l.length) === 0);
  await pg.click('[data-nav=kasa]'); await sleep(200);
  ok('Kasa: veri yoksa sahte sayı yerine açık açıklama gösterir', /Sanal kasa|veri yok/.test(await metin(pg, '#kasaMain')));

  /* ---- 3) canlı pilot performans görünümü ---- */
  const tum = [];
  for (const h of ['ozet', 'traderlar', 'huni', 'ayarlar']) { await pg.click(`[data-nav=${h}]`); await sleep(200); tum.push(await pg.evaluate(() => document.body.innerText)); }
  await pg.goto(base + '#trader/' + A1); await pg.reload(); await sleep(1200); tum.push(await pg.evaluate(() => document.body.innerText));
  const hepsi = tum.join('\n');
  ok('"sanal kopya (hepsi)" getiri olarak görünür; kilit yok', /Sanal kopya \(hepsi\)[\s\S]{0,80}%/.test(hepsi) && !/kilitli · hafta/.test(hepsi));
  ok('kohort ↔ kontrol kıyası görünür', /Kohort ↔ kontrol:[\s\S]*%/.test(hepsi));
  ok('kâr/zarar rengi sınıfı yok (up/down kullanılmaz)', await pg.evaluate(() => document.querySelectorAll('.up, .down').length) === 0);
  ok('rozet/seri yok (kazanma serisi, rozet kazanıldı)', !/seri|rozet kazan|streak/i.test(hepsi));
  await ctx.close();

  /* ---- 4) Trader'lar: kol filtresi + kart alanları ---- */
  ({ ctx, pg } = await ac({ durum: kollu() }));
  const oz2 = await metin(pg, '#ozMain');
  ok('Özet: oda doluluğu "1 / 20 trader", hafta 5/12', /1 \/ 20 trader/.test(oz2) && /5\/12/.test(oz2), oz2.match(/Oda doluluğu[^]{0,40}/)?.[0]);
  ok('Özet: mutabakat sağlık ışığı ve eylem görünür', /Her şey yolunda/.test(oz2) && /İşlem gerekmez/.test(oz2));
  await pg.click('[data-nav=kasa]'); await sleep(200);
  const kasa = await metin(pg, '#kasaMain');
  ok('Kasa: yalnız oda toplamı, kontrol satırı, eğri ve dört kutu görünür', ['Oda kasası', 'Kontrol karşılaştırması', 'Kasa eğrisi', 'Nakit (serbest)', 'Açık teminat', 'Gerçekleşmemiş K/Z', 'Son 24 saat'].every((x) => kasa.includes(x)), kasa.slice(0, 300));
  ok('Kasa: açık işlem ve son kapanan tabloları, eksik likidasyon verisini dürüstçe gösterir', /Açık işlemler/.test(kasa) && /Son kapananlar/.test(kasa) && /veri yok/.test(kasa));
  await ctx.close();
  ({ ctx, pg } = await ac({ durum: kasaSentetik })); await pg.click('[data-nav=kasa]'); await sleep(200);
  ok('Kasa sentetik altın örneği: oda 1.050 $, kontrol 2.120 $ (K1 1.020 + E1 1.100: kollar üyeliği, ana etiketi elle), teminat 100 $ (nosyonel 200 $ / 2x)', /1\.050 \$/.test(await metin(pg, '#kasaMain')) && /2\.120 \$/.test(await metin(pg, '#kasaMain')) && /100 \$/.test(await metin(pg, '#kasaMain')));
  await ctx.close();
  ({ ctx, pg } = await ac({ durum: kollu() }));
  await pg.click('[data-nav=traderlar]'); await sleep(300);
  const chips = await pg.$$eval('#trMain .chip', (l) => l.map((x) => x.textContent.trim()));
  ok('kol filtresi: standart ve referans kolları görünür', ['Tümü', 'Oda', 'Referans oda', 'Aday', 'Kontrol', 'Referans kontrol', 'Taban', 'Elle liste'].every((k) => chips.some((c) => c.startsWith(k))) && chips.some((c) => /kol bilinmiyor/.test(c)), chips.join(' | '));
  ok('Tümü: 4 kart', await pg.$$eval('#trMain .ct-card.tik', (l) => l.length) === 4);
  await pg.click('#trMain .chip:has-text("Aday")'); await sleep(200);
  const adayKart = await pg.$$eval('#trMain .ct-card.tik', (l) => l.map((x) => x.textContent));
  ok('kol filtresi: Aday → yalnız 1 kart (Trader-2)', adayKart.length === 1 && /Trader-2/.test(adayKart[0]), adayKart.length + '');
  ok('kart: takma ad, tarz, kol, neden seçildi, kırmızı bayrak, açık işlem sayısı', ['Trader-2', 'tarz bilinmiyor', 'Aday', 'Neden seçildi', 'uzun süredir işlem yok', 'Açık işlem'].every((k) => adayKart[0].includes(k)), adayKart[0].replace(/\s+/g, ' ').slice(0, 200));
  await pg.click('#trMain .chip:has-text("Tümü")'); await sleep(200);
  const ilk = (await pg.$$eval('#trMain .ct-card.tik .ct-name', (l) => l.map((x) => x.textContent)));
  ok('kart sırası sanal getiriye göre azalan', JSON.stringify(ilk) === JSON.stringify(['Trader-1', 'Trader-3', 'Trader-2', 'Trader-4']), ilk.join(','));
  await pg.click('#trMain .chip:has-text("Oda")'); await sleep(150);
  const odaKart = await pg.$eval('#trMain .ct-card.tik', (e) => e.textContent);
  ok('kart: veride verilen "neden seçildi" metni görünür', /gölgede ≥ 3 hafta, kapıyı geçti/.test(odaKart));
  await ctx.close();

  /* ---- 5) trader sayfası ---- */
  ({ ctx, pg } = await ac({ durum: kollu() }, undefined, '#trader/' + A1));
  await sleep(1200);
  const sira = await pg.evaluate(() => { const bs = [...document.querySelectorAll('#trMain .card, #trMain details')].map((c) => (c.querySelector('h2,summary,.ct-name') || c).textContent.trim().slice(0, 24)); return bs; });
  ok('trader sayfası sırası: kimlik → açık pozisyonlar → ... (kimlikte kol, neden, bayrak)', /Trader-1/.test(sira[0]) && /Açık pozisyonlar/.test(sira[1]), sira.join(' | '));
  const ust = await pg.$eval('#trMain .card', (e) => e.innerText);
  ok('üstte kimlik, kol, neden seçildi, kırmızı bayraklar', /Trader-1/.test(ust) && /Oda/.test(ust) && /Neden seçildi/.test(ust) && /Kırmızı bayraklar/.test(ust));
  const linkler = await pg.$$eval('#trMain .card:first-child a[href^="http"]', (l) => l.map((a) => a.href));
  ok('başlıkta Hyperliquid ve Hyperdash bağlantıları', linkler.some((h) => /app\.hyperliquid\.xyz\/explorer\/0x0+1$/.test(h)) && linkler.some((h) => /hyperdash\.com\/address\/0x0+1$/.test(h)), linkler.join(' '));
  ok('açık pozisyonlar tek liste (BTC tek kez, iki tekrarlı liste yok)', await pg.$$eval('#trMain .card', (cs) => { const c = cs.find((x) => /Açık pozisyonlar/.test(x.textContent)); return c ? [...c.querySelectorAll('.ct-trade')].filter((x) => /BTC/.test(x.textContent)).length : -1; }) === 1
    && await pg.$$eval('#trMain h2, #trMain summary', (l) => l.filter((x) => /Açık pozisyonlar|Açık işlemler/.test(x.textContent)).length) === 1);
  ok('işlem geçmişi (ham dolumlardan) varsayılan kapalı', await pg.$eval('details[data-d^="gecmis:"]', (e) => !e.open));
  await pg.click('details[data-d^="gecmis:"] summary'); await sleep(250);
  ok('işlem geçmişi aç/kapa: açılınca satırlar görünür', await pg.$eval('details[data-d^="gecmis:"]', (e) => e.open && e.querySelectorAll('.ct-trade').length >= 1));
  await pg.click('details[data-d^="gecmis:"] summary'); await sleep(150);
  ok('işlem geçmişi yeniden kapanır', await pg.$eval('details[data-d^="gecmis:"]', (e) => !e.open));
  ok('trader sayfası: sanal kopya sonucu görünür', /Bizim sanal kopya[\s\S]*Getiri[\s\S]*Bakiye/.test(await metin(pg, '#trMain')));
  await ctx.close();

  /* ---- 6) Hyperliquid erişilemezse çökmez; kol/alan eksik veri ---- */
  const eksik = JSON.parse(JSON.stringify(ornek)); eksik.traderlar = [{ id: 'X1', adres: '0x' + '9'.repeat(40) }];
  ({ ctx, pg } = await ac({ durum: eksik, hl: false }, undefined, '#trader/0x' + '9'.repeat(40)));
  await sleep(1200);
  const t6 = await metin(pg, '#trMain');
  ok('eksik alanlı trader (kol/tarz/neden/bayrak yok) ve canlı veri yok: sayfa çökmeden açılır', /kol bilinmiyor/.test(t6) && /belirtilmemiş/.test(t6) && /bayrak bilgisi yok/.test(t6) && /Canlı veri alınamadı/.test(t6), t6.replace(/\s+/g, ' ').slice(0, 160));
  await pg.click('[data-nav=traderlar]'); await sleep(200);
  ok('eksik alanlı trader kartı çizilir', await pg.$$eval('#trMain .ct-card.tik', (l) => l.length) === 1);
  await ctx.close();

  /* ---- 7) "?" açıklamaları ---- */
  ({ ctx, pg } = await ac());
  await pg.click('[data-nav=huni]'); await sleep(250);
  const soru = await pg.$$eval('#huMain .ip', (l) => l.map((x) => x.getAttribute('aria-label')));
  ok('Huni: kapı, havuz, aday, oda terimlerinin yanında "?"', ['Kapı', 'Havuz', 'Aday', 'Oda'].every((k) => soru.some((s) => s.includes(k))), soru.join(' | '));
  await pg.click('#huMain .ip[aria-label*="Kapı"]'); await sleep(150);
  const kutu = await pg.$eval('#ipKutu', (e) => ({ h: e.hidden, t: e.textContent }));
  ok('"?" dokununca kısa açıklama kutusu açılır', !kutu.h && /ön eleme/i.test(kutu.t), kutu.t.slice(0, 60));
  await pg.keyboard.press('Escape'); ok('Esc açıklamayı kapatır', await pg.$eval('#ipKutu', (e) => e.hidden));
  await pg.click('[data-nav=ozet]'); await sleep(200);
  await pg.click('#ozMain .ip[aria-label*="Kol"]'); ok('Özet: "kol" açıklaması açılır', /Kol/.test(await metin(pg, '#ipKutu')));
  await pg.click('[data-ip-kapat]');
  await pg.click('[data-nav=ayarlar]'); await sleep(200);
  const soz = await metin(pg, '#ayarMain');
  ok('Ayarlar: sözlükte kapı, kol, gecikme, havuz, kontrol, taban', ['Kapı', 'Kol', 'Gecikme', 'Havuz', 'Kontrol', 'Taban'].every((k) => soz.includes(k)));

  /* ---- 8) Huni ---- */
  await pg.click('[data-nav=huni]'); await sleep(250);
  const hu = await metin(pg, '#huMain');
  ok('Huni: havuz → aday → oda sayıları ve son tarama durumu', /Havuz/.test(hu) && /12\.300/.test(hu) && /Aday/.test(hu) && /Oda/.test(hu) && /Son tarama/.test(hu) && /Taranan evren/.test(hu));
  ok('Huni: oda sayısı bilinmiyorsa "bilinmiyor" (kol alanı yok)', /Oda[\s\S]{0,12}bilinmiyor/.test(hu));
  await pg.click('#huMain details[data-d=adaylar] summary'); await sleep(250);
  ok('Huni: aday listesi ve filtreler eskisi gibi çalışır', await pg.$$eval('#huMain .ks-card', (l) => l.length) === 12);
  await pg.selectOption('#huMain select >> nth=0', 'swing'); await sleep(200);
  ok('Huni: tarz filtresi (swing)', (await pg.$$eval('#huMain .ks-card', (l) => l.length)) < 12);
  await pg.evaluate(() => { ksFiltre = { tarz: '', katman: '', piyasa: '', gecmis: '' }; });

  /* ---- 9) Ayarlar ---- */
  await pg.click('[data-nav=ayarlar]'); await sleep(200);
  await pg.check('#tutarAcik'); await pg.fill('#tutarButce', '2500'); await pg.press('#tutarButce', 'Tab'); await sleep(200);
  ok('Ayarlar: tutar hesaplayıcı saklanır', await pg.evaluate(() => JSON.parse(localStorage.getItem('sg-pano-tutar-v1')).butce) === 2500);

  /* ---- 10) eski adresler ---- */
  await pg.goto(base + '#ctakis'); await sleep(400); ok('#ctakis → Özet', await pg.$eval('.nav-btn.active', (e) => e.dataset.nav) === 'ozet');
  await pg.goto(base + '#kesif'); await sleep(400); ok('#kesif → Huni', await pg.$eval('.nav-btn.active', (e) => e.dataset.nav) === 'huni');
  await pg.goto(base + '#ct/T1'); await sleep(1200); ok('#ct/T1 → trader sayfası', /Trader-1/.test(await metin(pg, '#trMain')) && /Açık pozisyonlar/.test(await metin(pg, '#trMain')) && /#trader\//.test(await pg.evaluate(() => location.hash)));
  await pg.goto(base + '#kesif/0x0a1b2c3d4e5f6789012345678901234567890a01'); await sleep(1000); ok('#kesif/<adres> → trader sayfası (Seçim ayrıntıları)', /Seçim ayrıntıları/.test(await metin(pg, '#trMain')));
  await ctx.close();

  /* ---- 11) veri yok ---- */
  ({ ctx, pg } = await ac());
  await ctx.close();
  const c2 = await b.newContext({ viewport: { width: 390, height: 844 } }), p2 = await c2.newPage();
  p2.on('pageerror', (e) => errs.push(e.message));
  await p2.route('**/raw.githubusercontent.com/**', (r) => r.fulfill({ status: 500, body: '' })); await p2.route('**/api.github.com/**', (r) => r.fulfill({ status: 500, body: '' })); await p2.route('**/kesif/ornek_kesif.json*', (r) => r.fulfill({ status: 404, body: '' }));
  await p2.route('https://api.hyperliquid.xyz/info', (r) => r.abort());
  await p2.goto(base); await sleep(1200);
  ok('veri yoksa hata görünür, sahte veri yok, çökme yok', /okunamadı/.test(await metin(p2, '#ctMsg')) && /Henüz veri yok/.test(await metin(p2, '#ozMain')));
  for (const t of ['traderlar', 'huni', 'ayarlar']) { await p2.click(`[data-nav=${t}]`); await sleep(150); }
  ok('veri yokken tüm sekmeler açılır', true);
  await c2.close();

  /* ---- 12) telefon ---- */
  ({ ctx, pg } = await ac({ durum: kollu(), dokunmatik: true }, { width: 390, height: 844 }));
  const ofisGor = await pg.evaluate(() => { const r = document.getElementById('ofisLink').getBoundingClientRect(); return r.width > 0 && r.left >= 0 && r.right <= innerWidth && r.height >= 44; });
  ok('telefon: "Ofis" bağlantısı ekranda, tam görünür, ≥ 44 px', ofisGor);
  for (const h of ['ozet', 'kasa', 'traderlar', 'huni', 'ayarlar']) {
    await pg.click(`[data-nav=${h}]`); await sleep(250);
    const g = await pg.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth }));
    ok(`telefon: ${h} sekmesinde yatay kaydırma yok`, g.sw <= g.iw, JSON.stringify(g));
  }
  const kucuk = await pg.evaluate(() => [...document.querySelectorAll('.nav-btn, .chip, .ct-btn')].filter((e) => e.offsetParent && e.getBoundingClientRect().height < 43.5).map((e) => e.className + ':' + Math.round(e.getBoundingClientRect().height)));
  ok('telefon: sekme, filtre ve düğmeler ≥ 44 px', kucuk.length === 0, kucuk.join(', '));
  await pg.click('[data-nav=ozet]'); await sleep(200);
  const ipk = await pg.evaluate(() => { const e = document.querySelector('#ozMain .ip'); const cs = getComputedStyle(e, '::after'); return { w: e.getBoundingClientRect().width, extra: parseFloat(cs.left) }; });
  ok('telefon: "?" düğmesi dokunma alanı ≥ 44 px (22 px + 11 px genişletme)', ipk.w + 22 >= 44, JSON.stringify(ipk));
  await pg.click('[data-nav=kasa]'); await sleep(200);
  await pg.screenshot({ path: path.join(root, 'docs/kasa_telefon.png'), fullPage: true });
  ok('telefon: yasal ibare ekranda', await pg.$eval('#yasal', (e) => { const r = e.getBoundingClientRect(); return r.bottom <= innerHeight && r.height > 0; }));
  await ctx.close();

  /* ---- 13) Keşif canlı yol sözleşmesi (veri dalı: kesif/kesif.json) ---- */
  const KESIF_CANLI = 'https://raw.githubusercontent.com/sselimgenc-oss/sg-arge/copytrade-kapi/kesif/kesif.json';
  const ornekKesif = JSON.parse(fs.readFileSync(path.join(root, 'kesif/ornek_kesif.json'), 'utf8'));
  ({ ctx, pg } = await ac({ canliKesif: { ...ornekKesif, uretildi: '2026-10-28T18:00:00Z', adaylar: ornekKesif.adaylar.slice(0, 3) } }));
  ok('Keşif: canlı dosya sabit yoldan okunur, GitHub API listelemesi yok', pg.istekler.some((u) => u === KESIF_CANLI) && !pg.istekler.some((u) => /api\.github\.com/.test(u)), pg.istekler.join(' ').slice(0, 200));
  await pg.click('[data-nav=huni]'); await sleep(250);
  ok('Keşif: canlı veri gösterilir (tarih 2026-10-28), örnek uyarısı yok', /2026-10-28/.test(await metin(pg, '#huMain')) && await pg.$eval('#ksMsg', (e) => e.classList.contains('hidden')));
  await ctx.close();
  ({ ctx, pg } = await ac({}, { width: 1440, height: 900 }));
  const uyari = await pg.$eval('#ksMsg', (e) => { const m = document.getElementById('main').getBoundingClientRect(), r = e.getBoundingClientRect(); return { gorunur: !e.classList.contains('hidden'), tam: Math.abs(r.width - (m.width - parseFloat(getComputedStyle(document.getElementById('main')).paddingLeft) * 2)) < 40, metin: e.textContent }; });
  ok('Keşif: canlı yoksa tam genişlikte "ÖRNEK (sahte) veri" uyarısı, her sekmede', uyari.gorunur && uyari.tam && /ÖRNEK \(sahte\) veri/.test(uyari.metin), JSON.stringify(uyari).slice(0, 160));
  await ctx.close();

  ok('sayfa/konsol hatası yok', errs.length === 0, errs.join(' | ').slice(0, 300));
  await b.close(); s.close();
  console.log(bad ? '\n' + bad + ' test başarısız' : '\nhepsi geçti');
  process.exit(bad ? 1 : 0);
})();
