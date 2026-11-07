/* Ofis · ortak bilgi kutusu. Masaüstünde sağda panel, telefonda alttan çekmece. Üç bölüm:
   Kimlik · Gerçek veri (zaman, n, "X dk önce"; "Neden burada?": olay_id, kural, tarih) · Replik (olay repliği + "ofis esprisi").
   Süs replikleri veri gibi görünmez: ayrı kutu, etiketli, rakam/adres/oran içermez (test: test/replik.test.js). */
(function () {
  'use strict';
  const O = window.OFIS, W = O.World, Names = O.Names;
  const I = (O.Info = {});
  let Off, api, R = { veri: [], suz: [] }, box, cur = null, editing = false, raf = 0;
  const rec = {}, clicks = {};
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const UNK = '<span class="bil">bilinmiyor</span>';
  const pad = n => (n < 10 ? '0' : '') + n;
  const KATAD = { lab: 'Lab (havuz)', aday: 'Aday', oda: 'Oda (kopya)', kontrol: 'Kontrol grubu', referans: 'Referans', diger: 'Diğer', disari: 'Kapıda' };
  const ROL = { yeni_adres: ['tarama', 'kapici'], kapi_gecti: ['kapici'], kapi_elendi: ['kapici'], havuzdan_cikar: ['kapici'], islem_acildi: ['finans'], islem_kapandi: ['finans'], bildirim: ['haber'], risk_tavan: ['risk'], risk_normal: ['risk'], veri_bayat: ['denetim'], veri_taze: ['denetim'], denetim: ['denetim'], arsiv_yazildi: ['arsivci'], kasa_guncelle: ['finans'], kural_kitabi: ['sekreter'], kullanici_karari: ['makam'], veri_yenile: ['finans'], kirmizi_bayrak: ['denetim'], bayrak_kalkti: ['denetim'] };
  const usd = v => (v == null ? null : (v < 0 ? '−' : v > 0 ? '+' : '') + '$' + Math.abs(v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  const pct = v => (v == null ? null : (v < 0 ? '−' : v > 0 ? '+' : '') + '%' + Math.abs(v).toLocaleString('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
  const fmtDate = d => Off.trDDMMYYYYHM(d);   // Türkiye saati (UTC+3); tarayıcının yerel saat dilimine bağlı değil
  function ago(iso) {
    const st = Off.state(); if (!iso || !st.data.uretildi) return 'bilinmiyor';
    const m = Math.round(Off.ageMin(iso));
    if (isNaN(m)) return 'bilinmiyor';
    if (m < 1) return 'şimdi'; if (m < 60) return m + ' dk önce';
    const h = Math.floor(m / 60); return h < 24 ? h + ' sa ' + (m % 60) + ' dk önce' : Math.floor(h / 24) + ' g önce';
  }
  const roleOf = id => id.replace(/\d$/, '').replace(/^haberlesme$/, 'haber');

  /* ---------- olay kaydı ("Neden burada?") ---------- */
  function record(e) {
    const r = { e: e, at: Off.clock() };
    if (e.trader) rec[e.trader] = r;
    if (e.oda) rec['oda:' + e.oda] = r;
    (ROL[e.tur] || []).forEach(x => (rec['rol:' + x] = r));
  }
  function why(r) {
    return '<div class="neden"><b>Neden burada?</b><div class="nd"><span>olay_id</span><code>' + esc(r.id || '—') + '</code></div><div class="nd"><span>kural</span><span>' + esc(r.kural || 'bilinmiyor') + '</span></div><div class="nd"><span>tarih</span><span>' + esc(r.tarih || 'bilinmiyor') + '</span></div></div>';
  }
  const whyFromEv = r => why({ id: r.e.id, kural: r.e.kural || r.e.neden, tarih: fmtDate(r.at) });
  const whyStatic = txt => '<div class="neden"><b>Neden burada?</b><div class="nd"><span>olay_id</span><code>—</code></div><div class="nd"><span>kural</span><span>' + esc(txt) + '</span></div><div class="nd"><span>tarih</span><span>sabit yerleşim</span></div></div>';

  /* ---------- replikler ---------- */
  function fields(e, st) {
    const nm = id => Names.trader(id) || ((st.traders[id] || {}).adres) || id, oad = id => Names.room(id, (W.roomById[id] || {}).ad);
    const t = e.trader ? st.traders[e.trader] : null, ris = (st.risk.tavanlar.find(x => x.anahtar === e.kalem) || {});
    const f = {
      adres: (t && t.adres) || e.adres, trader: e.trader ? nm(e.trader) : null, coin: e.coin, yon: e.yon ? String(e.yon).toUpperCase() : null, kaldirac: e.kaldirac,
      teminat: e.teminat_usd != null ? e.teminat_usd.toLocaleString('tr-TR', { minimumFractionDigits: 2 }) : null, kimden_ad: e.kimden ? oad(e.kimden) : null, kime_ad: e.kime ? oad(e.kime) : null,
      neden: e.neden, kural: e.kural, oda_ad: e.oda ? oad(e.oda) : null, kalem: ris.ad || e.kalem, yuzde: e.deger != null ? Math.round(e.deger * 100) : null, yas_dk: e.yas_dk,
      satir: e.satir != null ? e.satir.toLocaleString('tr-TR') : null, sonuc: e.sonuc, metin: e.metin, id: e.id, kz_usd: e.kz_usd != null ? usd(e.kz_usd).replace('$', '') : null, kz_yuzde: e.kz_yuzde != null ? pct(e.kz_yuzde).replace('%', '') : null,
      n_guncelleme: e.guncellemeler ? e.guncellemeler.length : null
    };
    return f;
  }
  I.fill = function (tpl, f) { return String(tpl).replace(/\{(\w+)\}/g, (m, k) => (f[k] == null || f[k] === '' ? 'bilinmiyor' : f[k])); };
  function veriReplik(rol, r, st) {
    if (!r) return null;
    const t = R.veri.find(x => x.olay_turu === r.e.tur && x.rol === rol); if (!t) return null;
    return { text: I.fill(t.sablon, fields(r.e, st)), r: r };
  }
  function susReplik(rol, key) {
    const list = R.suz.filter(x => x.rol === rol); if (!list.length) return null;
    const n = clicks[key] = (clicks[key] || 0) + 1;
    return list[(n - 1 + (O.hashStr ? O.hashStr(key) : 0)) % list.length].metin;
  }
  function replikHTML(vr, suz) {
    let h = '<section class="b-replik" aria-label="Replik"><h3>Replik</h3>';
    if (vr) h += '<blockquote class="r-veri"><p>' + esc(vr.text) + '</p><small>olay repliği · ' + esc(vr.r.e.id || '') + ' · ' + esc(fmtDate(vr.r.at)) + '</small></blockquote>';
    if (suz) h += '<blockquote class="r-suz"><span class="etiket">ofis esprisi</span><p>“' + esc(suz) + '”</p><small>veri değildir; yalnız eğlence</small></blockquote>';
    if (!vr && !suz) h += '<p class="bos">Replik yok.</p>';
    return h + '</section>';
  }

  /* ---------- satır yardımcıları ---------- */
  const row = (l, v, meta) => '<div class="vr2"><dt>' + esc(l) + '</dt><dd>' + (v == null ? UNK : v) + (meta ? '<small>' + esc(meta) + '</small>' : '') + '</dd></div>';
  const rows = list => '<dl class="b-rows">' + list.join('') + '</dl>';
  const sec = (title, body, cls) => '<section class="' + (cls || '') + '" aria-label="' + esc(title) + '"><h3>' + esc(title) + '</h3>' + body + '</section>';

  function staffRows(rol, st) {
    const k = st.katlar, d = st.data;
    switch (rol) {
      case 'finans': { const tem = st.acik.reduce((s, x) => s + (x.teminat_usd || 0), 0); return [row('Açık gölge işlem', 'n=' + st.acik.length, 'teminat ' + usd(tem).replace('+', '') + ' · ' + ago(st.ozet.zaman)), row('Bugün kapanan', 'n=' + st.ozet.bugun_kapanan_n, ago(st.ozet.zaman)), row('Kasa değeri', 'kilitli', 'ön kayıt: hafta ' + st.kk.hafta + '/' + st.kk.hafta_toplam)]; }
      case 'haber': return [row('Bugün bildirim', st.tg.bugun_n == null ? null : 'n=' + st.tg.bugun_n, ago(st.tg.zaman)), row('Son bildirim', esc((st.tg.son || [])[0] || 'bilinmiyor'))];
      case 'risk': return st.risk.tavanlar.map(t => row(t.ad, '%' + Math.round(t.kullanim / t.tavan * 100) + ' dolu', 'tavan payı · ' + ago(st.risk.zaman)));
      case 'denetim': { const v = st.vk.find(x => x.anahtar === 'denetim') || {}; return [row('Son sağlama', esc(v.deger || 'bilinmiyor'), ago(v.zaman)), row('Durum', st.denetim === 'tamam' ? 'tamam' : 'uyarı'), row('Açık kırmızı bayrak', 'n=' + Object.keys(st.traders).filter(x => st.traders[x].bayrak).length)]; }
      case 'arsivci': { const a = st.arsiv, tot = (a.turler || []).reduce((s, x) => s + x.satir, 0); return [row('Toplam satır', a.turler && a.turler.length ? tot.toLocaleString('tr-TR') : null, 'n=' + (a.turler || []).length + ' tür · ' + ago(a.zaman))]; }
      case 'tarama': { const v = st.vk.find(x => x.anahtar === 'tarama') || {}; return [row('Son tarama', esc(v.deger || 'bilinmiyor'), ago(v.zaman))]; }
      case 'kapici': return [row('Bugün geçen', st.kapi.bugun_gecen_n == null ? null : 'n=' + st.kapi.bugun_gecen_n, ago(st.kapi.zaman)), row('Bugün elenen', st.kapi.bugun_elenen_n == null ? null : 'n=' + st.kapi.bugun_elenen_n, ago(st.kapi.zaman))];
      case 'sekreter': return [row('Ön kayıt', esc(st.kk.onkayit || 'bilinmiyor'), ago(st.kk.zaman)), row('Kural kitabı', 'kurallar.yaml')];
      case 'makam': return [row('Ön kayıt haftası', st.kk.hafta + '/' + st.kk.hafta_toplam, ago(st.kk.zaman)), row('Karar', 'kullanıcıda')];
      default: return [];
    }
  }
  function traderRows(t, st) {
    const u = ago(st.data.uretildi), tr = st.acik.filter(x => x.trader === t.id), list = [];
    list.push(row('Kat', t.kol === 'taban' ? 'Taban' : esc(KATAD[(st.actorById[t.id] || {}).kat] || KATAD[t.kat] || '—'), 'veri ' + u));
    list.push(row('Kol', esc(t.kol || 'bilinmiyor')), row('Tarz', esc(t.tarz || 'bilinmiyor')));
    if (O.Panel.ornekMi()) list.push(row('Gün', t.gun == null ? null : 'n=' + t.gun), row('İşlem', t.islem_n == null ? null : 'n=' + t.islem_n), row('Gölge puanı (bilgi)', t.puan == null ? null : String(t.puan).replace('.', ',')));
    else {                                                  // gerçek veri: körlük — puan, kâr/zarar yok; yalnız kat, sıra, tarz, kaldıraç
      list.push(row('Aday sırası', t.sira == null ? null : '#' + t.sira + ' (tarz içinde)'), row('Geçmiş', t.gun == null ? null : 'n=' + t.gun + ' gün'));
      list.push(row('Medyan kaldıraç', t.medyan_kaldirac == null ? null : String(Math.round(t.medyan_kaldirac * 10) / 10).replace('.', ',') + 'x'), row('En yüksek kaldıraç', t.en_yuksek_kaldirac == null ? null : String(Math.round(t.en_yuksek_kaldirac * 10) / 10).replace('.', ',') + 'x'));
      if (t.genc_aday) list.push(row('Not', 'genç aday (geçmişi kısa)'));
    }
    if (t.bayrak) list.push(row('Kırmızı bayrak', esc(t.bayrak.neden), 'Denetim notu'));
    if (tr.length) tr.forEach(x => list.push(row(x.coin + ' ' + (x.yon === 'long' ? 'LONG' : 'SHORT') + ' ' + x.kaldirac + 'x', usd(x.kz_usd) + ' (' + pct(x.kz_yuzde) + ')', 'lik. uzaklık %' + String(x.lik_uzaklik).replace('.', ',') + ' · açık işlem')));
    else list.push(row('Açık gölge işlem', O.Panel.ornekMi() ? 'yok' : 'sanal izleme başlamadı'));
    return list;
  }
  function objRows(id, st) {
    const k = st.katlar, a = st.arsiv, v = key => st.vk.find(x => x.anahtar === key) || {};
    const arsiv = () => (a.turler || []).map(x => row(x.tur, x.satir.toLocaleString('tr-TR') + ' satır', 'son kayıt ' + ago(x.son_kayit)));
    switch (id) {
      case 'lab.pano': return [row('Havuz', k.havuz.n == null ? null : 'n=' + k.havuz.n + ' adres', ago(k.havuz.zaman)), row('Görünen masa', 'n=' + k.havuz.masa)];
      case 'lab.kayit_dolabi': return [row('Gölge defteri', esc(v('lab').deger || 'bilinmiyor'), ago(v('lab').zaman))];
      case 'kapi.turnike1': case 'kapi.turnike2': return [row('Bugün geçen', st.kapi.bugun_gecen_n == null ? null : 'n=' + st.kapi.bugun_gecen_n, ago(st.kapi.zaman)), row('Bugün elenen', st.kapi.bugun_elenen_n == null ? null : 'n=' + st.kapi.bugun_elenen_n, ago(st.kapi.zaman))];
      case 'arsiv.raf1': case 'arsiv.raf2': case 'arsiv.raf3': case 'arsiv.dolap': case 'arsiv.kutu': return arsiv().length ? arsiv() : [row('Arşiv', null)];
      case 'finans.kasa': case 'finans.tv': return [row('Kasa değeri ve eğrisi', 'kilitli', 'ön kayıt: hafta ' + st.kk.hafta + '/' + st.kk.hafta_toplam)];
      case 'haberlesme.posta': case 'haberlesme.tv': return [row('Bugün bildirim', st.tg.bugun_n == null ? null : 'n=' + st.tg.bugun_n, ago(st.tg.zaman)), row('Son bildirim', esc((st.tg.son || [])[0] || 'bilinmiyor'))];
      case 'oda.masa': return [row('Oda', 'n=' + k.oda.n + '/' + k.oda.kapasite + ' trader', ago(k.oda.zaman)), row('Boş masa', 'n=' + Math.max(0, k.oda.kapasite - k.oda.n)), row('Açık gölge işlem', 'n=' + st.acik.length, ago(st.ozet.zaman))];
      case 'sekreterlik.onkayit_kasasi': { const o = st.onkayit; return [row('Ön kayıt sürümü', esc(o.surum || 'bilinmiyor'), ago(o.zaman)), row('Commit', o.commit ? '<code>' + esc(o.commit) + '</code>' : null), row('Dondurma tarihi', esc(o.dondurma_tarihi || 'bilinmiyor'))]; }
      case 'haberlesme.zarf_rafi': return [row('Bugün gönderilen bildirim', st.tg.bugun_n == null ? null : 'n=' + st.tg.bugun_n, ago(st.tg.zaman)), row('Rafta görünen zarf', 'n=' + Math.min(12, st.tg.bugun_n || 0) + ' (en çok 12)'), row('Son bildirim', esc((st.tg.son || [])[0] || 'bilinmiyor'))];
      case 'risk.alarm': case 'risk.fener': case 'risk.tv': return st.risk.tavanlar.map(t => row(t.ad, '%' + Math.round(t.kullanim / t.tavan * 100) + ' dolu', ago(st.risk.zaman))).concat([row('Alarm', st.alarm ? 'açık' : 'yok')]);
      case 'denetim.sunucu1': case 'denetim.sunucu2': case 'denetim.sunucu3': return [row('Son denetim', st.denetim === 'tamam' ? 'tamam (yeşil ışık)' : 'uyarı (sarı ışık)', ago(v('denetim').zaman))];
      case 'tarama.tv': return [row('Son tarama', esc(v('tarama').deger || 'bilinmiyor'), ago(v('tarama').zaman)), row('En yüksek puanlar', (st.tarama.puanlar || []).slice(0, 3).map(p => String(p).replace('.', ',')).join(' · ') || null, ago(st.tarama.zaman))];
      case 'aday.tv': return [row('Aday katı', k.aday.n == null ? null : 'n=' + k.aday.n, ago(k.aday.zaman)), row('Görünen masa', 'n=' + k.aday.masa)];
      case 'sekreterlik.kural_rafi': return [row('Ön kayıt', esc(st.kk.onkayit || 'bilinmiyor'), ago(st.kk.zaman))];
      case 'aday.masa': return [row('Aday katı', st.katlar.aday.n == null ? null : 'n=' + st.katlar.aday.n, ago(st.katlar.aday.zaman)), row('Görünen masa', 'n=' + st.katlar.aday.masa)];
      case 'kontrol.masa': return [row('Kontrol grubu', 'n=' + st.katlar.kontrol.n + ' adres', ago(st.katlar.kontrol.zaman)), row('Görünen masa', 'n=' + st.katlar.kontrol.masa)];
      case 'kontrol.zar': return [row('Kontrol grubu', 'n=' + ((st.kk.kollar.find(c => /Kontrol/.test(c.ad)) || {}).n || '?') + ' adres', 'rastgele, sabit tohum · ' + ago(st.kk.zaman))];
      case 'makam.masa': return [row('Ön kayıt haftası', st.kk.hafta + '/' + st.kk.hafta_toplam, ago(st.kk.zaman))];
      default: return [];
    }
  }

  const eskiRow = room => { if (room && Off.gri(room)) return row('Durum', Off.gri(room)); const i = room ? Off.ageInfo(room) : null; if (!i) return ''; return row('Veri yaşı', (i.stale ? '<span class="eski-etiket">VERİ ESKİ</span> ' : '') + O.Panel.ageTxt(i), i.esik != null ? 'eşik ' + O.Panel.dkTxt(i.esik) + ' (veri kaynağına göre)' : ''); };
  /* ---------- seçime göre içerik ---------- */
  function build(sel, st) {
    const kad = Names.kadro();
    let title = '', sub = '', kimlik = '', veri = '', replik = '', edit = null;
    if (sel.type === 'person') {
      const a = sel.a;
      if (a.kind === 'staff') {
        const id = a.staffId, rol = roleOf(id), k = (kad.calisanlar[id] || {}), oad = Names.room(k.oda, (W.roomById[k.oda] || {}).ad);
        title = Names.staff(id); sub = 'çalışan · ' + oad; edit = { kind: 'calisan', id: id, cur: Names.isCustom('calisan', id) ? Names.staff(id) : '', ph: Names.staffDefault(id) };
        kimlik = rows([row('Ad', esc(title) + (Names.isCustom('calisan', id) ? '<small>varsayılan: ' + esc(Names.staffDefault(id)) + '</small>' : '')), row('Oda', esc(oad)), row('Görevi', esc(k.yapar || 'bilinmiyor'))]);
        const r = rec['rol:' + rol];
        veri = rows([eskiRow(k.oda)].concat(staffRows(rol, st))) + (r ? whyFromEv(r) : whyStatic('sabit kadro (kadro.json); bu oturumda henüz olay yok'));
        replik = replikHTML(veriReplik(rol, r, st), susReplik(rol, 'p:' + id));
      } else {
        const t = st.traders[a.id] || {}, al = Names.trader(a.id);
        title = al || t.adres || a.id; sub = 'trader · ' + (t.kol === 'taban' ? 'Taban' : (KATAD[a.kat] || '—')); edit = { kind: 'trader', id: a.id, cur: al, ph: t.adres || a.id };
        kimlik = rows([row('Ad', esc(title)), row('Gerçek adres', '<code>' + esc(t.adres || a.id) + '</code>' + (O.Panel.ornekMi() ? ' <span class="ornek">örnek</span>' : ''), 'kısaltılmış; takma ad değişse de sabit')]);
        const r = rec[a.id];
        veri = rows(traderRows(Object.assign({ id: a.id }, t), st)) + (r ? whyFromEv(r) : t.kat_olay ? why({ id: t.kat_olay.id, kural: t.kat_olay.kural, tarih: fmtDate(new Date(t.kat_olay.zaman)) }) : whyStatic(O.Panel.ornekMi() ? 'başlangıç durumu (örnek veri)' : 'başlangıç durumu (veri dalındaki seçim)'));
        replik = replikHTML(veriReplik('trader', r, st), susReplik('trader', 'p:' + a.id));
      }
    } else if (sel.type === 'obje') {
      const o = sel.o, d = kad.nesneler[o.id] || { ad: o.id, ne: '', suz: true }, rd = (st.roomById || {}), oad = Names.room(o.room, (W.roomById[o.room] || {}).ad);
      title = d.ad; sub = 'nesne · ' + oad;
      kimlik = rows([row('Nesne', esc(d.ad)), row('Oda', esc(oad)), row('İşlevi', esc(d.ne))]);
      const data = objRows(o.id, st), r = rec['oda:' + o.room];
      veri = (data.length ? rows([eskiRow(o.room)].concat(data)) : '<p class="bos">Bu nesne süstür; veri taşımaz.</p>') + (!d.suz && r ? whyFromEv(r) : whyStatic('sabit oda donanımı (kadro.json)'));
      replik = replikHTML(null, susReplik('obje', 'o:' + o.id));
    } else if (sel.type === 'oda') {
      const id = sel.id, r0 = W.roomById[id] || {}, d = kad.odalar[id] || {}, info = Off.roomInfo(id) || { lines: [] };
      title = Names.room(id, r0.ad); sub = 'oda'; edit = { kind: 'oda', id: id, cur: Names.isCustom('oda', id) ? title : '', ph: Names.roomDefault(id, r0.ad) };
      kimlik = rows([row('Ad', esc(title) + (Names.isCustom('oda', id) ? '<small>varsayılan: ' + esc(Names.roomDefault(id, r0.ad)) + '</small>' : ''))]) + '<div class="birim-kart" aria-label="Bu birim ne yapar, ne yapmaz"><div><b>Bu birim ne yapar</b>' + esc(d.yapar || 'bilinmiyor') + '</div><div class="yapmaz"><b>Ne yapmaz</b>' + esc(d.yapmaz || 'bilinmiyor') + '</div></div>';
      const r = rec['oda:' + id];
      veri = '<ul class="b-lines">' + info.lines.map(l => '<li>' + esc(l) + '</li>').join('') + '</ul>' + '<dl class="b-rows">' + eskiRow(id) + '</dl>' + (r ? whyFromEv(r) : whyStatic('sabit oda (kadro.json)'));
      replik = '';
    } else if (sel.type === 'isaret') {
      const m = sel.mark, n = sel.note, e = (m ? m.e : n.e) || {}, kind = m ? ({ zarf: 'Zarf', not: 'Not kâğıdı', ok: 'Ok' }[m.kind]) : 'Kırmızı bayrak notu';
      title = kind; sub = 'iletişim işareti';
      kimlik = rows([row('İşaret', esc(kind)), row('Olay', esc(e.metin || e.tur || 'bilinmiyor'))]);
      veri = rows([row('olay_id', '<code>' + esc(e.id || '—') + '</code>'), row('Zaman', esc(m ? fmtDate(m.zaman) : e.id && rec[sel.trader] ? fmtDate(rec[sel.trader].at) : 'bilinmiyor')), row('Kural', esc(e.kural || e.neden || 'bilinmiyor'))]);
      replik = '';
    }
    return { title: title, sub: sub, kimlik: kimlik, veri: veri, replik: replik, edit: edit };
  }
  const row2 = (l, v) => '<div class="vr2"><dt>' + esc(l) + '</dt><dd>' + v + '</dd></div>';

  function html(b) {
    let h = '<header class="b-ust"><div><h2 id="bAd">' + esc(b.title) + '</h2><p class="b-alt">' + esc(b.sub) + '</p></div><button type="button" class="b-kapat" id="bKapat" aria-label="Bilgi kutusunu kapat">×</button></header>';
    h += sec('Kimlik', b.kimlik, 'b-kimlik');
    if (b.edit) {
      h += editing ? '<form class="b-ad" id="bAdForm"><label>Yeni ad<input type="text" id="bAdInput" maxlength="24" value="' + esc(b.edit.cur) + '" placeholder="' + esc(b.edit.ph) + '"></label><div class="b-btnler"><button type="submit">Kaydet</button><button type="button" id="bAdIptal">Vazgeç</button></div><p class="ks">Boş bırakırsan varsayılan ad döner. Yalnız etiket değişir; veri ve gerçek adres sabit kalır.</p></form>'
        : '<button type="button" class="b-ad-btn" id="bAdBtn">Adı değiştir</button>';
    }
    h += sec('Gerçek veri', b.veri, 'b-veri') + b.replik;
    h += '<p class="yasal">Araştırma / sanal gösterim; yatırım tavsiyesi değildir. Örnek veri, adresler uydurma.</p>';
    return h;
  }

  function render() {
    raf = 0; if (!cur || !box) return;
    const st = Off.state(); if (!st) return;
    const b = build(cur, st);
    box.innerHTML = html(b); box.hidden = false;
    document.body.classList.add('bilgi-acik');
    const inp = $('#bAdInput'); if (inp) inp.focus();
  }
  const schedule = () => { if (!raf && cur) raf = requestAnimationFrame(render); };

  I.show = function (sel) {
    cur = sel; editing = false;
    if (sel.type === 'person') Off.react(sel.a);
    render(); if (api && api.onShow) api.onShow(sel); if (api && api.invalidate) api.invalidate();
  };
  I.close = function () { cur = null; editing = false; if (box) { box.hidden = true; box.innerHTML = ''; } document.body.classList.remove('bilgi-acik'); if (api && api.onClose) api.onClose(); if (api && api.invalidate) api.invalidate(); };
  I.isOpen = () => !!cur;
  I.current = () => cur;
  /* hover/aria için kısa başlık */
  I.title = function (sel) {
    const st = Off.state(), kad = Names.kadro();
    if (sel.type === 'person') { const a = sel.a; return a.kind === 'staff' ? Names.staff(a.staffId) + ' · ' + Names.room((kad.calisanlar[a.staffId] || {}).oda, '') : (Names.trader(a.id) || (st.traders[a.id] || {}).adres || a.id) + ' · trader'; }
    if (sel.type === 'obje') return (kad.nesneler[sel.o.id] || {}).ad || sel.o.id;
    if (sel.type === 'isaret') return 'İletişim işareti';
    return '';
  };

  I.init = function (off, a, replikler) {
    Off = off; api = a; R = replikler || R; box = $('#bilgi');
    Off.onEvent(record);
    Off.on(schedule);
    Names.onChange(schedule);
    box.addEventListener('click', e => {
      if (e.target.closest('#bKapat')) { I.close(); return; }
      if (e.target.closest('#bAdBtn')) { editing = true; render(); return; }
      if (e.target.closest('#bAdIptal')) { editing = false; render(); return; }
    });
    box.addEventListener('submit', e => {
      e.preventDefault(); const f = e.target.closest('#bAdForm'); if (!f || !cur) return;
      const v = $('#bAdInput').value, b = build(cur, Off.state()); if (!b.edit) return;
      Names.set(b.edit.kind, b.edit.id, v); editing = false; render();
    });
  };
})();
