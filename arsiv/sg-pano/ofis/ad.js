/* Ofis · adlar ve ayarlar. Oda, çalışan ve trader takma adları tarayıcıda saklanır (localStorage), JSON olarak dışa/içe aktarılır.
   Varsayılanlar kadro.json'dadır. Ad değişse de trader'ın gerçek adresi (kısaltılmış) bilgi kutusunda sabit kalır. */
(function () {
  'use strict';
  const O = window.OFIS;
  const N = (O.Names = {});
  const KEY = 'sgofis.adlar.v1', MAXLEN = 24;
  let kadro = { odalar: {}, calisanlar: {}, nesneler: {} };
  let user = { odalar: {}, calisanlar: {}, traderlar: {} };
  const subs = [];
  const clean = v => String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f<>]/g, '').replace(/\s+/g, ' ').trim().slice(0, MAXLEN);
  const store = {
    get() { try { return window.localStorage.getItem(KEY); } catch (e) { return null; } },
    set(v) { try { window.localStorage.setItem(KEY, v); return true; } catch (e) { return false; } }
  };
  function persist() { store.set(JSON.stringify(Object.assign({ surum: 1 }, user))); }
  function changed() { subs.forEach(f => f()); }
  N.onChange = f => subs.push(f);
  N.kadro = () => kadro;

  N.init = function (k) {
    kadro = k || kadro;
    const raw = store.get();
    if (raw) { try { N.apply(JSON.parse(raw), true); } catch (e) { /* bozuk kayıt: varsayılanlar */ } }
  };
  /* ad çözümleme: kullanıcı adı varsa o, yoksa varsayılan */
  N.roomDefault = (id, fb) => ((kadro.odalar[id] || {}).ad) || fb || id;
  N.room = (id, fb) => user.odalar[id] || N.roomDefault(id, fb);
  N.staffDefault = id => ((kadro.calisanlar[id] || {}).ad) || id;
  N.staff = id => user.calisanlar[id] || N.staffDefault(id);
  N.trader = id => user.traderlar[id] || '';
  N.isCustom = (kind, id) => !!((kind === 'oda' ? user.odalar : kind === 'calisan' ? user.calisanlar : user.traderlar)[id]);

  function put(map, id, v) { v = clean(v); if (v) map[id] = v; else delete map[id]; }
  N.set = function (kind, id, v) {
    put(kind === 'oda' ? user.odalar : kind === 'calisan' ? user.calisanlar : user.traderlar, id, v);
    persist(); changed();
  };
  N.reset = function () { user = { odalar: {}, calisanlar: {}, traderlar: {} }; persist(); changed(); };
  N.export = () => JSON.stringify({ surum: 1, odalar: user.odalar, calisanlar: user.calisanlar, traderlar: user.traderlar }, null, 1);
  /* içe aktar: yalnız bilinen kimlikler; uzunluk ve karakter temizlenir. Dönüş: {ok, n, atlanan} */
  N.apply = function (obj, silent) {
    if (!obj || typeof obj !== 'object' || obj.surum !== 1) return { ok: false, n: 0, atlanan: 0, hata: 'desteklenmeyen biçim (surum 1 bekleniyor)' };
    const next = { odalar: {}, calisanlar: {}, traderlar: {} }; let n = 0, skip = 0;
    const take = (src, dst, valid) => Object.keys(src || {}).forEach(k => { const v = clean(src[k]); if (v && valid(k)) { dst[k] = v; n++; } else skip++; });
    take(obj.odalar, next.odalar, k => !!kadro.odalar[k]);
    take(obj.calisanlar, next.calisanlar, k => !!kadro.calisanlar[k]);
    take(obj.traderlar, next.traderlar, k => /^T\d{3,4}$/.test(k));
    user = next; if (!silent) { persist(); changed(); } return { ok: true, n: n, atlanan: skip };
  };

  /* ---------- ayarlar penceresi ---------- */
  const $ = s => document.querySelector(s);
  function field(kind, id, label, ph) {
    const v = kind === 'oda' ? user.odalar[id] : user.calisanlar[id];
    return '<label class="af"><span>' + label + '</span><input type="text" maxlength="' + MAXLEN + '" data-kind="' + kind + '" data-id="' + id + '" value="' + (v || '').replace(/"/g, '&quot;') + '" placeholder="' + String(ph).replace(/"/g, '&quot;') + '"></label>';
  }
  function build() {
    const od = Object.keys(kadro.odalar).map(id => field('oda', id, kadro.odalar[id].ad, kadro.odalar[id].ad)).join('');
    const ca = Object.keys(kadro.calisanlar).map(id => field('calisan', id, 'Çalışan · ' + (kadro.odalar[kadro.calisanlar[id].oda] || {}).ad, kadro.calisanlar[id].ad)).join('');
    $('#ayarListe').innerHTML = '<h3>Oda adları</h3><div class="ag">' + od + '</div><h3>Çalışan adları</h3><div class="ag">' + ca + '</div>';
  }
  let lastFocus = null;
  N.open = function () {
    build(); const d = $('#ayarlar'); lastFocus = document.activeElement;
    if (d.showModal) { try { d.showModal(); } catch (e) { d.setAttribute('open', ''); } } else d.setAttribute('open', '');
    const f = d.querySelector('input'); if (f) f.focus();
  };
  N.close = function () { const d = $('#ayarlar'); if (d.close) d.close(); else d.removeAttribute('open'); if (lastFocus && lastFocus.focus) lastFocus.focus(); };
  function msg(t, bad) { const m = $('#ayarMesaj'); m.textContent = t; m.className = bad ? 'hata-satir' : ''; }
  N.bindUI = function () {
    const d = $('#ayarlar'); if (!d) return;
    $('#ayarBtn').addEventListener('click', N.open);
    $('#ayarKapat').addEventListener('click', N.close);
    d.addEventListener('click', e => { if (e.target === d) N.close(); });
    $('#ayarListe').addEventListener('change', e => { const i = e.target.closest('input[data-kind]'); if (!i) return; N.set(i.dataset.kind, i.dataset.id, i.value); i.value = (i.dataset.kind === 'oda' ? user.odalar : user.calisanlar)[i.dataset.id] || ''; msg('Kaydedildi (bu tarayıcıda).'); });
    $('#ayarSifirla').addEventListener('click', () => { N.reset(); build(); msg('Varsayılan adlara dönüldü.'); });
    $('#ayarDisa').addEventListener('click', () => {
      const blob = new Blob([N.export()], { type: 'application/json' }), a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = 'sg-ofis-adlar.json'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
      msg('Dışa aktarıldı: sg-ofis-adlar.json');
    });
    $('#ayarIce').addEventListener('change', e => {
      const f = e.target.files && e.target.files[0]; if (!f) return;
      if (f.size > 100000) { msg('Dosya çok büyük.', true); return; }
      const r = new FileReader();
      r.onload = () => { try { const res = N.apply(JSON.parse(r.result)); if (res.ok) { build(); msg('İçe aktarıldı: ' + res.n + ' ad' + (res.atlanan ? ', ' + res.atlanan + ' kayıt atlandı' : '') + '.'); } else msg('İçe aktarılamadı: ' + res.hata, true); } catch (err) { msg('İçe aktarılamadı: geçerli bir JSON değil.', true); } e.target.value = ''; };
      r.readAsText(f);
    });
  };
})();
