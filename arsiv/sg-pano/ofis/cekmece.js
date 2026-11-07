/* Ofis · olay çekmecesi: Gözcü kaydının tam hali. Oda, trader ve olay türü filtresi; olaya tıklayınca kamera o odaya gider ve ilgili figür vurgulanır.
   Kaynak: bu oturumun olay günlüğü + veri dosyasındaki geçmiş günlük (gecmis_olaylar). Masaüstünde soldan panel, telefonda alttan çekmece. */
(function () {
  'use strict';
  const O = window.OFIS, W = O.World, Names = O.Names;
  const C = (O.Cekmece = {});
  let Off, api, box, open = false, raf = 0;
  const F = { oda: '', trader: '', tur: '' };
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pad = n => (n < 10 ? '0' : '') + n;
  const turAd = t => (((Names.kadro().olay_turleri || {})[t]) || {}).ad || t;
  const odaAd = id => { const r = W.roomById[id]; return r ? Names.room(id, r.ad) : (id || '—'); };
  /* Taban kolundaki traderlar ofiste Lab/havuz katında oturur (ayrı oda çizilmiyor), ama "taban" kontrol kümesi
     Lab'daki gölge izleme akışından kavramsal olarak ayrıdır — olay etiketi karıştırmasın diye "Taban" yazılır. */
  const odaAdOlay = e => { const t = e.trader && Off.state().traders[e.trader]; return t && t.kol === 'taban' ? 'Taban' : odaAd(e.oda); };
  const traderAd = id => { const t = Off.state().traders[id] || {}; return Names.trader(id) || t.adres || id; };
  function entries() {
    const st = Off.state(), list = st.log.map(l => ({ iso: l.iso, ts: l.ts, oda: l.oda, tur: l.tur, trader: l.trader, metin: l.metin, id: l.olay_id, gecmis: false }));
    st.gecmis.forEach(g => { const p = Off.trParts(g.zaman); list.push({ iso: g.zaman, ts: pad(p.day) + '.' + pad(p.mo + 1) + ' ' + pad(p.h) + ':' + pad(p.m), oda: g.oda || '', tur: g.tur, trader: g.trader || null, metin: g.metin || g.tur, id: g.id, gecmis: true }); });
    return list.filter(e => e.tur !== 'sistem').sort((a, b) => (a.iso < b.iso ? 1 : a.iso > b.iso ? -1 : 0));
  }
  C.entries = entries;
  C.filtered = () => entries().filter(e => (!F.oda || e.oda === F.oda) && (!F.trader || e.trader === F.trader) && (!F.tur || e.tur === F.tur));
  function options(all) {
    const rooms = W.ROOMS.filter(r => !r.out), traders = [...new Set(all.map(e => e.trader).filter(Boolean))].sort(), turs = Object.keys(Names.kadro().olay_turleri || {});
    const opt = (v, t, sel) => '<option value="' + esc(v) + '"' + (sel === v ? ' selected' : '') + '>' + esc(t) + '</option>';
    $('#fOda').innerHTML = opt('', 'Tüm odalar', F.oda) + rooms.map(r => opt(r.id, odaAd(r.id), F.oda)).join('');
    $('#fTrader').innerHTML = opt('', 'Tüm trader\'lar', F.trader) + traders.map(t => opt(t, traderAd(t), F.trader)).join('');
    $('#fTur').innerHTML = opt('', 'Tüm olaylar', F.tur) + turs.map(t => opt(t, turAd(t), F.tur)).join('');
  }
  function render() {
    raf = 0; if (!open || !box) return;
    const all = entries(), list = all.filter(e => (!F.oda || e.oda === F.oda) && (!F.trader || e.trader === F.trader) && (!F.tur || e.tur === F.tur));
    options(all);
    $('#cSay').textContent = 'n=' + list.length + (list.length !== all.length ? ' / ' + all.length : '');
    $('#cListe').innerHTML = list.slice(0, 250).map((e, i) => '<li><button type="button" data-i="' + i + '"' + (e.gecmis ? ' class="gecmis"' : '') + '><time>' + esc(e.ts) + '</time><i class="oc">' + esc(odaAdOlay(e)) + '</i><b class="tur">' + esc(turAd(e.tur)) + (e.trader ? ' · ' + esc(traderAd(e.trader)) : '') + '</b><span>' + esc(e.metin) + '</span><code>' + esc(e.id || '') + '</code></button></li>').join('') || '<li class="bos">Bu filtreyle olay yok.</li>';
    C._list = list.slice(0, 250);
    const orn = $('#cekmeceOrnek'); if (orn) orn.hidden = !(O.Panel && O.Panel.ornekMi());
  }
  const schedule = () => { if (!raf && open) raf = requestAnimationFrame(render); };
  C.isOpen = () => open;
  C.open = function () { open = true; box.hidden = false; document.body.classList.add('cekmece-acik'); if (api.beforeOpen) api.beforeOpen(); render(); if (api.invalidate) api.invalidate(); };
  C.close = function () { if (!open) return; open = false; box.hidden = true; document.body.classList.remove('cekmece-acik'); };
  C.setFilter = function (k, v) { F[k] = v; render(); };
  C.clear = function () { F.oda = F.trader = F.tur = ''; render(); };
  C.filters = () => Object.assign({}, F);
  C.init = function (off, a) {
    Off = off; api = a; box = $('#olayCekmece');
    Off.on(schedule); Names.onChange(schedule);
    $('#cKapat').addEventListener('click', C.close);
    $('#fTemizle').addEventListener('click', C.clear);
    ['Oda', 'Trader', 'Tur'].forEach(k => $('#f' + k).addEventListener('change', e => C.setFilter(k.toLowerCase(), e.target.value)));
    $('#cListe').addEventListener('click', e => { const b = e.target.closest('button[data-i]'); if (!b) return; const en = C._list[+b.dataset.i]; if (en && api.focusEvent) api.focusEvent(en); });
    document.addEventListener('click', e => { if (e.target.closest('[data-olay-ac]')) { open ? C.close() : C.open(); } });
  };
})();
