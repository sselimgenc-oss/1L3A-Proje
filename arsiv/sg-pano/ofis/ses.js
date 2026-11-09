/* Ofis · ses: varsayılan KAPALI; Ayarlar'dan açılır (bu tarayıcıda saklanır). Olay başına tek kısa ton, WebAudio ile kodla üretilir (ses dosyası yok).
   Ton frekansı kadro.json olay_turleri[tur].ton alanındadır. Olay yağmurunda. */
(function () {
  'use strict';
  const O = window.OFIS, S = (O.Ses = {});
  const KEY = 'sgofis.ses.v1';
  let on = false, ctx = null, last = 0, Off = null, tones = {};
  const store = { get() { try { return window.localStorage.getItem(KEY); } catch (e) { return null; } }, set(v) { try { window.localStorage.setItem(KEY, v); } catch (e) { /* saklanamadı */ } } };
  S.isOn = () => on;
  function audio() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
    try { ctx = new AC(); } catch (e) { ctx = null; } return ctx;
  }
  S.set = function (v) {
    on = !!v; store.set(on ? '1' : '0');
    if (on) { const c = audio(); if (c && c.resume) c.resume(); }
    const cb = document.getElementById('sesAc'); if (cb) cb.checked = on;
  };
  function tone(f) {
    const c = audio(); if (!c) return;
    const t0 = c.currentTime, o = c.createOscillator(), g = c.createGain();
    o.type = 'sine'; o.frequency.value = f; g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.07, t0 + 0.012); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.14);
    o.connect(g); g.connect(c.destination); o.start(t0); o.stop(t0 + 0.16);
  }
  S.init = function (off, olayTurleri) {
    Off = off; tones = olayTurleri || {};
    on = store.get() === '1';
    const cb = document.getElementById('sesAc'); if (cb) { cb.checked = on; cb.addEventListener('change', () => S.set(cb.checked)); }
    Off.onEvent(e => {
      if (!on || e.tur === 'sistem') return;
      const st = Off.state(), t = performance.now(), f = (tones[e.tur] || {}).ton;
      if (!f || st.fastUntil > t || t - last < 120) return;     // olay yağmurunda tek ton bile çalınmaz
      last = t; tone(f);
    });
  };
})();
