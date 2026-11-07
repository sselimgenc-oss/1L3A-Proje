/* Gerçek veri yolunun test verisi: veri dalındaki secim.json / durum.json ile aynı biçim, UYDURMA adresler (0x + 40 onaltılık hane). */
'use strict';
const adres = (k, i) => '0x' + (k + String(i).padStart(2, '0')).repeat(20).slice(0, 40);
function secim(tarih, surum) {
  const adresler = {}, ekle = (a, o) => { adresler[a] = Object.assign({ kol: 'havuz', kollar: ['havuz'], tarz: 'intraday', puan: 0.123456, sira: null, genc_aday: false, medyan_kaldirac: 1.5, en_yuksek_kaldirac: 4.0, gecmis_gun: 400.0, hesap_degeri: 1000, iliskili_not: '', hesap_surumu: 'v1.1-test' }, o); };
  for (let i = 1; i <= 6; i++) ekle(adres('a', i), { kol: 'oda', kollar: ['oda', 'aday', 'havuz'], tarz: i % 2 ? 'intraday' : 'swing', sira: Math.ceil(i / 2), puan: 0.9 - i / 100, en_yuksek_kaldirac: 2 + i, medyan_kaldirac: 1 + i / 10, genc_aday: i === 6, gecmis_gun: i === 6 ? 200 : 400 });
  for (let i = 1; i <= 3; i++) ekle(adres('b', i), { kol: 'aday', kollar: ['aday', 'havuz'], tarz: 'swing', sira: 3 + i, puan: 0.5 - i / 100 });
  for (let i = 1; i <= 5; i++) ekle(adres('c', i), { kol: 'kontrol', kollar: ['kontrol', 'havuz'], tarz: 'swing', puan: 0.7 });       // kontrol: ofiste hiçbir yerde olmamalı
  for (let i = 1; i <= 4; i++) ekle(adres('d', i), { kol: 'taban', kollar: ['taban'], tarz: null, puan: null });
  const s = { surum: 1, tarih, tohum: 1, tohum_dizgesi: 'secim-v1-' + tarih, sayilar: { kapi_satiri: 100, havuz: 30, aday: 9, oda: 6, kontrol: 5, taban: 4, elle: 2, tarz: {} }, oda_kisa: true, oda_kota: {}, kontrol: [], adresler };
  if (surum) { s.secim_surumu = surum; s.kapi_tarihi = tarih; }
  return s;
}
const durum = { durum: 'tamam', parca_beklenen: 32, parca_biten: 32, islenen: 13767, evren: 13710, kapsam: 1.0042, neden: '', hesap: 'v1.1-2026-10-27d' };
/* copytrade-izleme/izleme/durum.json biçiminde "onaylı" (secim etiketiyle eşleşen) canlı veri — UYDURMA.
   traders: [{id, adresIndex(kol harfi+sayı), kol, kollar, saglik, sanal_kopya_v3, pozisyonlar}]; her biri secim.json'daki
   aynı adres(a1..a6=oda, b1..b3=aday, d1..d4=taban)'a eşlenir ki gercek.js onu secim satırıyla birleştirsin.
   sanal_kopya_v3: gercek.js'in güncel motor olarak okuduğu alan (v1 sanal_kopya artık okunmuyor, kullanıcı kararı 2026-10-30). */
function izleme(etiket, traders, olaylar) {
  return {
    surum: 1, uretildi: '2026-10-28T14:20:00Z', kaynak: 'hyperliquid-izleme (test)',
    traderlar: traders.map(t => Object.assign({
      id: t.id, adres: t.adresTam, takma_ad: t.adresTam.slice(2, 6), durum: 'izlemede', t0: '2026-10-28',
      kol: t.kol, kollar: t.kollar, tarz: t.tarz || 'intraday', veri_zamani: '2026-10-28T14:18:00Z', gecerli: true,
      secim: etiket, saglik: t.saglik || null, sanal_kopya_v3: t.sanal_kopya_v3 || null, pozisyonlar: t.pozisyonlar || []
    })),
    kasa_egri: [], olaylar: olaylar || [], kalabalik: { n_oda: traders.filter(t => t.kollar.includes('oda')).length, uyari: false, uyari_metni: null }
  };
}
const agac = (secimler, kapilar) => ({ sha: 'x', truncated: false, tree: [].concat(
  secimler.map(d => ({ path: 'secim/' + d + '/secim.json', type: 'blob' })), secimler.map(d => ({ path: 'secim/' + d + '/RAPOR.md', type: 'blob' })),
  kapilar.map(d => ({ path: 'copytrade/kapi/' + d + '/durum.json', type: 'blob' })), [{ path: 'secim', type: 'tree' }, { path: 'kesif/kesif.json', type: 'blob' }]) });
module.exports = { adres, secim, durum, agac, izleme };
