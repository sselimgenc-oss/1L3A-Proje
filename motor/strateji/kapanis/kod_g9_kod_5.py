"""Kapanış turu, kodlama partisi g9_kod_5 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_5.csv, 30 Robotic (HAM:B001) kaynak satırı).

Her sınıf, satırın `kanit` sütunundaki Freqtrade strateji dosyasının KURALINI kendi cümlelerimizle yazar (dosya yalnız okundu, çalıştırılmadı,
üçüncü taraf kod kopyalanmadı). Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel; üst zaman dilimi yalnız
`motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan. Sınıf adı `kapanis__<kisa>-b<NNNN>`.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış -/+ 3 x ATR(14) (ön kayıt). Aksi halde kaynak yüzde stopu sinyal kapanışından.
- minimal_roi (dakika anahtarlı) -> `CikisAyarlari.azalan_roi` (mum = yukarı yuvarlanmış dakika / TF dakikası; aynı muma düşende büyük dakika
  geçerli). Fiilen yok sayılabilecek tablolar ({0: 5..999} gibi >= %500) yazılmadı. Hedef kapanışta sınanır, çıkış sonraki açılışta.
- trailing_stop -> `geri_cekilme_yuzde` / `geri_cekilme_min_kar_yuzde` (kâr% farkı, kapanış bazlı). `trailing_only_offset_is_reached=False` ise
  min kâr 0; True ise offset. trailing_stop_positive yoksa mesafe = stoploss yüzdesi.
- custom_sell / custom_exit / custom_stoploss -> `pozisyon_cikisi` kancası (yalnız kapanmış mum ve `sinyaller()`in nedensel dizileri).
  Freqtrade'in mum içi (high/low) stop mantığı kapanış bazlı kancaya çevrildi; kâra bağlı basamaklı iz/stoplar giriş sonrası ZİRVE
  (en_yuksek) kârından hesaplanır (yakınsama).
- Gösterge karşılıkları: TA-Lib EMA/SMA/RSI/ATR -> `g.ema/sma/rsi/atr` (başlangıç tohumlaması farkı yalnız ilk mumlarda); TA-Lib TRIMA,
  `technical.zema` (2*EMA - EMA(EMA)), qtpylib HMA/rolling_vwap, pandas_ta ssf/cti ve TA-Lib SAR / mum desenleri bu dosyada yeniden yazıldı.
- Ichimoku `chikou_span` (shift(-n)) kaynakta `shift(n)` ile geri çekilip kullanılır; net etkisi kapanış[t] > bulut[t-n] (nedensel) olduğundan
  doğrudan bu biçimde yazıldı (gelecek verisi yok).
- Protections (CooldownPeriod, LowProfitPairs, stoploss_guard), emir tipi/limit emir, canlı-only dalları (dry_run/live) motorda yok, yazılmadı.

Satır uyarlamaları:
- 634/635/636 (Nowo Ichimoku): buy_allowed durum makinesi (bir yeşil bulut döneminde bir giriş) kaynak niyetine göre yazıldı (kaynak V1 bozuk);
  634 custom_sell'deki `srsi>80 & kâr>1.1` (öncelik hatası) sayısal olarak %110 / %101 eşikleriyle korundu (fiilen tetiklenmez); 635/636
  custom_stoploss(-0.0001) = anında çıkış olarak kancada; 636'da 1h bilgi TF `ust_zaman`, kaydırmalar x12; yeşil bulut = kaydırılmış (cloud_green).
- 638: giriş/çıkış ZEMA uzunluk-ofset eşleşmesi KAYNAK DOSYADAN: giriş ZEMA(51)x0.964 altı, çıkış ZEMA(72)x1.004 üstü (kural_tam özeti tersti).
  `confirm_trade_exit` ROI çıkışını 1h `trending>0` iken engeller: ROI tablosu kancada, trending>0 iken çıkış yok.
- 663/664: custom_sell iz-EMA (alpha 2/33, girişte EMA ile tohumlu) backtest dalı; stoploss etkin başlangıç -%15 (Freqtrade stopu gevşetmez,
  custom_stoploss pHSL -%32 devreye girmez; satırdaki -%32 yerine sınıf stopu). Basamaklı kâr stopu zirve kârıyla kancada.
- 681: sinyal 1h bilgi TF (`ust_zaman`), yürütme 5m; TP = 1h kapanış + 2xATR(1h) kancada, stop = %3xATR(1h)/kapanış.
- 685 (Renko): ilk tuğla boyunda kaynak tüm-seri ATR ortalaması kullanıyor (lookahead); ATR(5) hazır olana kadar tuğla üretilmez (nedensel
  ısınma), sonrası kaynak gibi. Satır başına renko olayı (tuğla oluşan mum) ve önceki OLAY satırının trendi kullanılır.
- 701: pandas_ta ssf (poles=2) başlangıcı kaynakta serinin SONUNA sarıyor; nedensel başlangıç (ilk iki değer = kapanış) kullanıldı.
- 704: TA-Lib CDL3LINESTRIKE/CDLEVENINGSTAR/CDLHARAMI/CDLENGULFING tanımları yeniden yazıldı; kaynaktaki ABANDONEDBABY = EVENINGSTAR hatası ve
  `EVENINGSTAR > 0` (desen yalnız -100 üretir) olduğu gibi: iki sütun hiç tetiklenmez.
- 741: `&`/`|` öncelik sırası (A&B) | C | (D&E&F); OBV tüm kümülatif (ilk değer = ilk hacim).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import birikim_dagitim as _ad
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu
from motor.strateji.seans_takvimi import mum_suresi
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- ortak yardımcılar
def _bitir(sonuc: pd.DataFrame, cikis_long=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _dk(m: pd.DataFrame) -> float:
    return float(mum_suresi(m.index) / pd.Timedelta(minutes=1))


def _yuzde_stop(m: pd.DataFrame, sl: float):
    kap = m["kapanis"]
    return kap * (1.0 - sl), kap * (1.0 + sl)


def _ichi(h: pd.Series, l: pd.Series, t: int, k: int, sb: int, kay: int) -> dict:
    """Ichimoku: tenkan/kijun, öndeki (kaydırılmamış) span A/B ve `kay` mum kaydırılmış (şimdiki bulut) sen_a/sen_b."""
    def orta(n):
        return (h.rolling(n).max() + l.rolling(n).min()) / 2.0
    tenkan, kijun = orta(t), orta(k)
    lead_a, lead_b = (tenkan + kijun) / 2.0, orta(sb)
    return {"tenkan": tenkan, "kijun": kijun, "lead_a": lead_a, "lead_b": lead_b,
            "sen_a": lead_a.shift(kay), "sen_b": lead_b.shift(kay)}


def _srsi_k(kap: pd.Series, rsi_n: int = 14, stok_n: int = 14, k_n: int = 3) -> pd.Series:
    r = g.rsi(kap, rsi_n)
    mn, mx = r.rolling(stok_n).min(), r.rolling(stok_n).max()
    return ((r - mn) / (mx - mn)).rolling(k_n).mean() * 100.0


def _ssl_kanal(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 10):
    """SSL kanalı (ATR(14) bantlı): hlv = kapanış üst banttan büyükse 1, alt banttan küçükse -1, aksi önceki; (ssl_down, ssl_up)."""
    atr = g.atr(h, l, c, 14)
    ust = h.rolling(n).mean() + atr
    alt = l.rolling(n).mean() - atr
    hlv = pd.Series(np.where(c > ust, 1.0, np.where(c < alt, -1.0, np.nan)), index=c.index).ffill()
    asagi_ = np.where(hlv < 0, ust, alt)
    yukari_ = np.where(hlv < 0, alt, ust)
    return pd.Series(asagi_, index=c.index), pd.Series(yukari_, index=c.index)


def _trima(s: pd.Series, n: int) -> pd.Series:
    if n % 2:
        a = b = (n + 1) // 2
    else:
        a, b = n // 2, n // 2 + 1
    return g.sma(g.sma(s, a), b)


def _zema(s: pd.Series, n: int) -> pd.Series:
    e1 = g.ema(s, n)
    return 2.0 * e1 - g.ema(e1, n)


def _hma_q(s: pd.Series, n: int) -> pd.Series:
    return _wma(2.0 * _wma(s, n // 2) - _wma(s, n), int(math.sqrt(n)))


def _ewo(kap: pd.Series, hizli: int, yavas: int) -> pd.Series:
    return (g.ema(kap, hizli) - g.ema(kap, yavas)) / kap * 100.0


def _ohlc4(m: pd.DataFrame) -> pd.Series:
    return (m["acilis"] + m["yuksek"] + m["dusuk"] + m["kapanis"]) / 4.0


def _pmax(ha: pd.DataFrame, period: int = 10, carpan: int = 27, uzun: int = 9) -> pd.Series:
    """PMAX (MA = EMA, kaynak = HA OHLC4): izleyen üst/alt bant özyinelemesi; çıktı `pm` çizgisi (nedensel)."""
    src = (ha["ha_yuksek"] + ha["ha_dusuk"] + ha["ha_kapanis"] + ha["ha_acilis"]) / 4.0
    ma = g.ema(src, uzun).to_numpy(dtype=float)
    atr = g.atr(ha["ha_yuksek"], ha["ha_dusuk"], ha["ha_kapanis"], period).to_numpy(dtype=float)
    ub, lb = (ma + (carpan / 10.0) * atr).tolist(), (ma - (carpan / 10.0) * atr).tolist()
    mav = ma.tolist()
    n = len(mav)
    fub, flb, pm = [0.0] * n, [0.0] * n, [0.0] * n
    for i in range(period, n):
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or mav[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or mav[i - 1] < flb[i - 1]) else flb[i - 1]
    for i in range(period, n):
        pu, pl, m_ = pm[i - 1] == fub[i - 1], pm[i - 1] == flb[i - 1], mav[i]
        if pu and m_ <= fub[i]:
            pm[i] = fub[i]
        elif pu and m_ > fub[i]:
            pm[i] = flb[i]
        elif pl and m_ >= flb[i]:
            pm[i] = flb[i]
        elif pl and m_ < flb[i]:
            pm[i] = fub[i]
        else:
            pm[i] = 0.0
    return pd.Series(pm, index=ha.index)


def _sar(h: pd.Series, l: pd.Series, adim: float = 0.02, maks: float = 0.2) -> pd.Series:
    """Parabolik SAR (TA-Lib SAR mantığı): çıktı[t] = t. muma uygulanan SAR değeri (nedensel)."""
    hv, lv = h.to_numpy(dtype=float), l.to_numpy(dtype=float)
    n = len(hv)
    out = np.full(n, np.nan)
    if n < 2:
        return pd.Series(out, index=h.index)
    yukari_f, asagi_f = hv[1] - hv[0], lv[0] - lv[1]
    minus_dm = asagi_f if (asagi_f > 0 and asagi_f > yukari_f) else 0.0
    uzun = not (minus_dm > 0)
    ep, sar = (hv[1], lv[0]) if uzun else (lv[1], hv[0])
    yeni_h, yeni_l, af = hv[0], lv[0], adim
    for t in range(1, n):
        onc_h, onc_l = yeni_h, yeni_l
        yeni_l, yeni_h = lv[t], hv[t]
        if uzun:
            if yeni_l <= sar:
                uzun, sar = False, ep
                sar = max(sar, onc_h, yeni_h)
                out[t] = sar
                af, ep = adim, yeni_l
                sar = max(sar + af * (ep - sar), onc_h, yeni_h)
            else:
                out[t] = sar
                if yeni_h > ep:
                    ep, af = yeni_h, min(af + adim, maks)
                sar = min(sar + af * (ep - sar), onc_l, yeni_l)
        else:
            if yeni_h >= sar:
                uzun, sar = True, ep
                sar = min(sar, onc_l, yeni_l)
                out[t] = sar
                af, ep = adim, yeni_h
                sar = min(sar + af * (ep - sar), onc_l, yeni_l)
            else:
                out[t] = sar
                if yeni_l < ep:
                    ep, af = yeni_l, min(af + adim, maks)
                sar = max(sar + af * (ep - sar), onc_h, yeni_h)
    return pd.Series(out, index=h.index)


def _rmi(kap: pd.Series, uzun: int = 9, mom: int = 3) -> pd.Series:
    """Göreli Momentum Endeksi: RSI'nın `mom` mumluk farklı biçimi (EMA yumuşatmalı)."""
    fark = kap - kap.shift(mom)
    art = fark.clip(lower=0.0).fillna(0.0)
    eks = (-fark).clip(lower=0.0).fillna(0.0)
    ea, eb = g.ema(art, uzun), g.ema(eks, uzun)
    return pd.Series(np.where(eb == 0, 0.0, 100.0 - 100.0 / (1.0 + ea / eb)), index=kap.index)


def _kor(seri: pd.Series, n: int) -> pd.Series:
    """Son n mumda fiyat ile zaman indeksi arasındaki Pearson korelasyonu (CTI)."""
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        w = sliding_window_view(a, n)
        x = np.arange(n, dtype=float) - (n - 1) / 2.0
        wm = w - w.mean(axis=1, keepdims=True)
        pay = wm @ x
        payda = np.sqrt((wm ** 2).sum(axis=1) * (x ** 2).sum())
        with np.errstate(divide="ignore", invalid="ignore"):
            out[n - 1:] = np.where(payda > 0, pay / payda, np.nan)
    return pd.Series(out, index=seri.index)


class _Taban(KancaDestek, Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


# ================================================================ B001:634 / 635 / 636 (Nowo Ichimoku)
def _wma_k(s: pd.Series, n: int) -> pd.Series:
    """Kaynaktaki özel ağırlıklı ortalama: shift(1..n-2), ağırlık (n-i)*n (bu mumun kendisi ve n-1. geçmiş hariç)."""
    toplam, norm = 0.0, 0.0
    for i in range(1, n - 1):
        w = float((n - i) * n)
        norm += w
        toplam = toplam + s.shift(i) * w
    return toplam / norm


def _bb_hma_ust(k: pd.Series, n: int = 20, carpan: float = 2.5) -> pd.Series:
    """Bollinger üst bandı, orta çizgi = HMA (kaynaktaki özel WMA ile), sapma = popülasyon std (TA-Lib STDDEV)."""
    hma = _wma_k(2.0 * _wma_k(k, n // 2) - _wma_k(k, n), int(math.floor(math.sqrt(n))))
    return hma + carpan * k.rolling(n).std(ddof=0)


def _nowo_ham(u: pd.DataFrame) -> pd.DataFrame:
    h, l, k = u["yuksek"], u["dusuk"], u["kapanis"]
    ich = _ichi(h, l, 9, 26, 52, 26)
    l1, l2 = ich["lead_a"], ich["lead_b"]
    ust, alt = l1.where(l1 > l2, l2), l1.where(l1 < l2, l2)
    return pd.DataFrame({
        "upper": _bb_hma_ust(k), "tenkan": ich["tenkan"], "kijun": ich["kijun"], "lead1": l1, "lead2": l2,
        "yesil_disp": (ich["sen_a"] > ich["sen_b"]).astype(float), "ust": ust, "alt": alt,
        "kay_ust": ust.shift(25), "kay_alt": alt.shift(25), "srsi": _srsi_k(k)}, index=u.index)


def _bir_donem(yesil: np.ndarray, olur: np.ndarray, baslangic: int, v1: bool) -> np.ndarray:
    """buy_allowed durumu: yeşil bulut döneminde bir giriş; bulut yeşil olmayınca yeniden izin. i <= baslangic ısınma (giriş yok)."""
    n = len(olur)
    al = np.zeros(n, dtype=bool)
    izin = (not yesil[0]) if v1 and n else True
    for i in range(1, n):
        if i <= baslangic:
            izin = (not yesil[i]) if v1 else True
            continue
        if al[i - 1]:
            izin = False
            if not v1 and not yesil[i]:
                izin = True
        elif not yesil[i]:
            izin = True
        al[i] = izin and bool(olur[i])
    return al


class _NowoTaban(_Taban):
    def _hazirla(self, m: pd.DataFrame, v1: bool) -> pd.DataFrame:
        p = self.parametreler
        k = int(p["kat"])
        kap, ac = m["kapanis"], m["acilis"]
        ham = _nowo_ham(m) if k == 1 else ust_zaman(m, "1h", _nowo_ham)
        yesil = (ham["lead1"] > ham["lead2"]) if k == 1 else (ham["yesil_disp"] > 0.5)
        olur = ((kap > ac) & (kap > ham["kay_ust"] * float(p["bulut_carpan"])) & (kap > ham["kay_alt"]) & yesil
                & (ham["tenkan"] > ham["kijun"]) & (kap > ham["tenkan"].shift(25 * k)) & (kap > ham["ust"].shift(50 * k)))
        al = _bir_donem(yesil.to_numpy(dtype=bool), olur.to_numpy(dtype=bool), int(p["baslangic"]), v1)
        self._sakla(kap=kap, srsi=ham["srsi"], upper=ham["upper"], kay_alt=ham["kay_alt"])
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return cerceve(m, pd.Series(al, index=m.index), False, sl, ss)

    def sinyaller(self, mumlar):
        return self._hazirla(mumlar, self._v1)


class NowoIchimoku1hV1B0634(_NowoTaban):
    """HAM:B001:634 (1h, long; NowoIchimoku1hV1): giriş = yeşil mum (kapanış > açılış) VE kapanış > 25 mum kaydırılmış üst bulut x1,04 VE >
    kaydırılmış alt bulut VE bulut yeşil (öndeki span A > span B) VE tenkan > kijun VE kapanış > 25 mum önceki tenkan VE kapanış > 50 mum
    kaydırılmış üst bulut; yeşil bulut dönemi başına tek giriş. Çıkış (kanca): srsi_k > 80 ve kâr > %110, ya da kapanış > HMA-Bollinger üst bandı
    (2,5s) ve kâr > %101 (kaynak öncelik hatası, fiilen tetiklenmez); kapanış > giriş mumunun kapanışı + 2 x (kapanış - kaydırılmış alt bulut);
    kapanış < giriş mumunun kaydırılmış alt bulutu. Stop -%8; ROI {0: 999} yok."""

    ad = "kapanis__nowo-ichimoku-1h-v1-b0634"
    _v1 = True
    varsayilan_parametreler = {"kat": 1, "sl": 0.08, "bulut_carpan": 1.04, "baslangic": 100, "srsi_esik": 80.0,
                               "srsi_kar": 110.0, "ust_kar": 101.0, "limit_carpan": 2.0}

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        e = d.giris_mum_indeksi
        kap_e, alt_e = self._dz("kap", e), self._dz("kay_alt", e)
        if self._dz("srsi", i) > float(p["srsi_esik"]) and d.kar_yuzde > float(p["srsi_kar"]):
            return True
        if d.kapanis > self._dz("upper", i) and d.kar_yuzde > float(p["ust_kar"]):
            return True
        if d.kapanis > kap_e + (kap_e - alt_e) * float(p["limit_carpan"]):
            return True
        return bool(d.kapanis < alt_e)


class NowoIchimokuV2B0635(_NowoTaban):
    """HAM:B001:635 (1h, long; NowoIchimoku1hV2, hyperopt varsayılanları): 634 girişi, kaydırılmış üst bulut katsayısı 0,603; buy_allowed
    durumu bağımsız iki koşullu. Çıkış (custom_stoploss=-0,0001, kancada): srsi_k(son) > 80 ve kâr > %3,6; ya da önceki kapanış < önceki üst
    bant VE kapanış > üst bant VE kâr > %1,1; ya da kapanış > giriş fiyatı + (giriş - giriş mumunun kaydırılmış alt bulutu) x 1,918; ya da kapanış
    < giriş mumunun kaydırılmış alt bulutu x 0,971. ROI {0 .427, 448 .202, 1123 .089, 2355 0}; stop -%34,5; trailing (mesafe = stop)."""

    ad = "kapanis__nowo-ichimoku-1h-v2-b0635"
    _v1 = False
    varsayilan_parametreler = {"kat": 1, "geri": 1, "sl": 0.345, "bulut_carpan": 0.603, "baslangic": 100,
                               "srsi_esik": 80.0, "srsi_kar": 3.6, "ust_kar": 1.1, "limit_carpan": 1.918,
                               "alt_carpan": 0.971}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.427, 448: 0.202, 1123: 0.089, 2355: 0}, 60),
                                   geri_cekilme_yuzde=34.5, geri_cekilme_min_kar_yuzde=0.0)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        geri = int(p["geri"])
        son, onc = i - (geri - 1), i - 2 * geri + 1
        e = d.giris_mum_indeksi
        alt_e = self._dz("kay_alt", e)
        if self._dz("srsi", son) > float(p["srsi_esik"]) and d.kar_yuzde > float(p["srsi_kar"]):
            return True
        if (self._dz("kap", onc) < self._dz("upper", onc) and d.kapanis > self._dz("upper", son)
                and d.kar_yuzde > float(p["ust_kar"])):
            return True
        if d.kapanis > d.giris_fiyati + (d.giris_fiyati - alt_e) * float(p["limit_carpan"]):
            return True
        return bool(d.kapanis < alt_e * float(p["alt_carpan"]))


class NowoIchimoku5mV2B0636(NowoIchimokuV2B0635):
    """HAM:B001:636 (5m, long; NowoIchimoku5mV2): 635 mantığı, 1h bilgi TF'den (kapanmış 1h; ust_zaman) Ichimoku/üst bant/srsi, bulut kaydırmaları
    x12 (time_factor); yeşil bulut = kaydırılmış cloud_green; kanca 12/24 mum geriden. ROI {0: 999} yok; stop -%29,3; trailing (mesafe = stop)."""

    ad = "kapanis__nowo-ichimoku-5m-v2-b0636"
    varsayilan_parametreler = {**NowoIchimokuV2B0635.varsayilan_parametreler, "kat": 12, "geri": 12, "sl": 0.293,
                               "baslangic": 0}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=29.3, geri_cekilme_min_kar_yuzde=0.0)


# ================================================================ B001:637 / 638 (Obelisk Ichimoku Slow / ZEMA)
def _obelisk_ham(u: pd.DataFrame, zema_surum: bool) -> pd.DataFrame:
    """Obelisk yavaş Ichimoku (20/60/120, kaydırma 30) trend durumu. zema_surum=False: v1.3 (EMA/EFI/SSL korumalı); True: ZEMA sürümü
    (boğa+ayı trend, geçerlilik)."""
    h, l, c, o = u["yuksek"], u["dusuk"], u["kapanis"], u["acilis"]
    ich = _ichi(h, l, 20, 60, 120, 30)
    tenkan, kijun, sen_a, sen_b = ich["tenkan"], ich["kijun"], ich["sen_a"], ich["sen_b"]
    ikili = pd.concat([sen_a, sen_b], axis=1)
    tepe, taban = ikili.max(axis=1), ikili.min(axis=1)           # kaynakta NaN atlanır (skipna)
    gelecek_yesil = ich["lead_a"] > ich["lead_b"]
    ssl_asagi, ssl_yukari = _ssl_kanal(h, l, c, 10)
    ssl_ok = ssl_yukari > ssl_asagi
    if zema_surum:
        chikou_yuksek = c > tepe.shift(30)
    else:
        chikou_yuksek = (c > sen_a.shift(30)) & (c > sen_b.shift(30))
    ichimoku_ok = (tenkan > kijun) & (c > tepe) & gelecek_yesil & chikou_yuksek

    def yonlu(nabiz, bitis):
        t = pd.Series(np.nan, index=u.index)
        t[nabiz.to_numpy(dtype=bool)] = 3.0
        t[bitis.to_numpy(dtype=bool)] = 0.0
        return t.ffill()

    if not zema_surum:
        ema_ok = (c > g.ema(c, 50)) & (g.ema(c, 50) > g.ema(c, 200))
        efi_ok = g.ema((c - c.shift(1)) * u["hacim"], 13) > 0
        entry_ok = efi_ok & (o < ssl_yukari) & (c < ssl_yukari)
        trending = yonlu(ichimoku_ok & ssl_ok & ema_ok, ~ssl_ok)
        return pd.DataFrame({"trending": trending, "entry_ok": entry_ok.astype(float)}, index=u.index)
    gelecek_kirmizi = ich["lead_a"] < ich["lead_b"]
    chikou_dusuk = c < taban.shift(30)
    ssl_ayi = ssl_yukari < ssl_asagi
    ichimoku_ayi = (tenkan < kijun) & (c < taban) & gelecek_kirmizi & chikou_dusuk
    trending = yonlu(ichimoku_ok & ssl_ok, ~ssl_ok | (c < tepe))
    ayi = yonlu(ichimoku_ayi & ssl_ayi, ~ssl_ayi | (c > taban))
    return pd.DataFrame({"trending": trending, "bear_trending": ayi,
                         "gecerli": ich["lead_b"].notna().astype(float)}, index=u.index)


class ObeliskIchiSlowB0637(_Taban):
    """HAM:B001:637 (1h, long; Obelisk_Ichimoku_Slow_v1_3): trending > 0 (Ichimoku 20/60/120 disp 30: tenkan > kijun, kapanış > bulut tepesi, öndeki
    bulut yeşil, kapanış > 30 mum önceki bulut; SSL(10) yukarı; EMA50 > EMA200 ve kapanış > EMA50 -> nabız, SSL aşağıya dönünce biter) VE entry_ok
    (EFI(13) > 0, açılış ve kapanış SSL üstünün altında) -> long; çıkış trending == 0. ROI {0 .10, 60 .072, 120 .049, 240 .02, 360 0}; trailing +%0,5,
    offset %4 (yalnız offset sonrası); stoploss -0,99 -> ATR(14)x3."""

    ad = "kapanis__obelisk-ichi-slow-b0637"
    varsayilan_parametreler = {"atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.10, 60: 0.072, 120: 0.049, 240: 0.02, 360: 0}, 60),
                                   geri_cekilme_yuzde=0.5, geri_cekilme_min_kar_yuzde=4.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ham = _obelisk_ham(mumlar, False)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (ham["trending"] > 0) & (ham["entry_ok"] > 0.5), False, kap - mes, kap + mes)
        return _bitir(s, ham["trending"] == 0)


class ObeliskIchiZemaB0638(_Taban):
    """HAM:B001:638 (5m, long; Obelisk_Ichimoku_ZEMA_v1, hyperopt parametreleri): 1h bilgi TF'de (kapanmış; ust_zaman) Ichimoku geçerli VE ayı trendi yok
    (bear_trending == 0) VE 5m kapanış < ZEMA(51) x 0,964 -> long; çıkış: kapanış > ZEMA(72) x 1,004. ROI {0 .078, 40 .062, 99 .039, 218 0} kancada:
    1h trending > 0 iken ROI çıkışı yapılmaz (confirm_trade_exit). Stop -%29,4."""

    ad = "kapanis__obelisk-ichi-zema-b0638"
    varsayilan_parametreler = {"zema_al": 51, "zema_sat": 72, "alt_ofset": 0.964, "ust_ofset": 1.004, "sl": 0.294,
                               "roi": roi_tablosu({0: 0.078, 40: 0.062, 99: 0.039, 218: 0}, 5)}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ham = ust_zaman(mumlar, "1h", lambda u: _obelisk_ham(u, True))
        al = ((ham["gecerli"] > 0.5) & (ham["bear_trending"] == 0)
              & (kap < _zema(kap, int(p["zema_al"])) * float(p["alt_ofset"])))
        cik = kap > _zema(kap, int(p["zema_sat"])) * float(p["ust_ofset"])
        self._sakla(trending=ham["trending"])
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi) or self._dz("trending", d.mum_indeksi) > 0:
            return False
        hedef = None
        for mum, yuzde in self.parametreler["roi"]:
            if d.tutulan_mum >= mum:
                hedef = yuzde
        return hedef is not None and d.kar_yuzde >= hedef


# ================================================================ B001:642 (ichiV1)
class IchiV1B0642(_Taban):
    """HAM:B001:642 (5m, long; ichiV1, ichiV1.json etkin katman): Heikin-Ashi açılış/yüksek/düşük ile Ichimoku(20/60/120, kaydırma 30); giriş: kapanış
    >  bulut (senkou A ve B), ilk 6 EMA ölçeğinde (1,3,6,12,24,48 mum) EMA(kapanış) > EMA(HA açılış), fan_magnitude = EMA12/EMA96 > 1, kazancı
    >= 1,002 ve son 3 mumdan her birinden büyük. Çıkış: kapanış EMA(24)'ü aşağı keser. ROI {0 .098, 225 .079, 399 .047, 938 0}; stop -%19,8;
    trailing kapalı."""

    ad = "kapanis__ichiv1-b0642"
    varsayilan_parametreler = {"bulut_seviye": 1, "boga_seviye": 6, "fan_kayma": 3, "fan_kazanc": 1.002,
                               "cikis_ema": 24, "sl": 0.198}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.098, 225: 0.079, 399: 0.047, 938: 0}, 5))
    _OLCEK = (1, 3, 6, 12, 24, 48, 72, 96)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ha = b2.heikin_ashi(mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], kap)
        tc = {n: (kap if n == 1 else g.ema(kap, n)) for n in self._OLCEK}
        to = {n: (ha["ha_acilis"] if n == 1 else g.ema(ha["ha_acilis"], n)) for n in self._OLCEK}
        ich = _ichi(ha["ha_yuksek"], ha["ha_dusuk"], 20, 60, 120, 30)
        al = pd.Series(True, index=mumlar.index)
        for n in self._OLCEK[:int(p["bulut_seviye"])]:
            al &= (tc[n] > ich["sen_a"]) & (tc[n] > ich["sen_b"])
        for n in self._OLCEK[:int(p["boga_seviye"])]:
            al &= tc[n] > to[n]
        fan = tc[12] / tc[96]
        al &= (fan / fan.shift(1) >= float(p["fan_kazanc"])) & (fan > 1.0)
        for x in range(int(p["fan_kayma"])):
            al &= fan.shift(x + 1) < fan
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), asagi(kap, g.ema(kap, int(p["cikis_ema"]))))


# ================================================================ B001:645 (Chispei)
class ChispeiB0645(_Taban):
    """HAM:B001:645 (4h, long; Chispei): MOM(21) (kapanış farkı, fiyat birimi) < 15 VE SMA13 > SMA25 -> long; çıkış MOM(21) < 80 VE SMA13 < SMA25.
    ROI {0 .04, 20 .05, 30 .05, 60 .10, 120 .10, 1836 .676, 2599 .079, 5127 0} (dk); stop -%32,336."""

    ad = "kapanis__chispei-mom-b0645"
    varsayilan_parametreler = {"mom_n": 21, "mom_al": 15.0, "mom_sat": 80.0, "hizli": 13, "yavas": 25, "sl": 0.32336}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu(
        {0: 0.04, 20: 0.05, 30: 0.05, 60: 0.10, 120: 0.10, 1836: 0.676, 2599: 0.079, 5127: 0}, 240))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mom = kap - kap.shift(int(p["mom_n"]))
        hz, yv = g.sma(kap, int(p["hizli"])), g.sma(kap, int(p["yavas"]))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        s = cerceve(mumlar, (mom < float(p["mom_al"])) & (hz > yv), False, sl, ss)
        return _bitir(s, (mom < float(p["mom_sat"])) & (hz < yv))


# ================================================================ B001:648 (DoubleEMACrossoverWithTrend)
class DoubleEmaTrendB0648(_Taban):
    """HAM:B001:648 (1h, long; DoubleEMACrossoverWithTrend): EMA9 EMA21'i yukarı keser VE düşük > EMA200 VE hacim > 0 -> long; çıkış EMA9 EMA21'i aşağı
    keser VEYA düşük < EMA200. ROI yok; stop -%20; trailing kapalı."""

    ad = "kapanis__double-ema-trend-b0648"
    varsayilan_parametreler = {"hizli": 9, "yavas": 21, "trend": 200, "sl": 0.20}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, dus = mumlar["kapanis"], mumlar["dusuk"]
        ea, eb, et = (g.ema(kap, int(p[k])) for k in ("hizli", "yavas", "trend"))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        s = cerceve(mumlar, yukari(ea, eb) & (dus > et) & (mumlar["hacim"] > 0), False, sl, ss)
        return _bitir(s, asagi(ea, eb) | (dus < et))


# ================================================================ B001:649 (EMA50)
class Ema50B0649(_Taban):
    """HAM:B001:649 (5m, long; EMA50, varsayılan parametreler): hacim > 0 VE kapanış EMA(50)'yi yukarı keser -> long. Sinyal çıkışı yok (sell_hold=True).
    ROI {0 .278, 39 .087, 124 .038, 135 0}; trailing +%17,2 / offset %21,2 (offset öncesi de çalışır); stop -%33,3."""

    ad = "kapanis__ema50-b0649"
    varsayilan_parametreler = {"ema_n": 50, "sl": 0.333}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.278, 39: 0.087, 124: 0.038, 135: 0}, 5),
                                   geri_cekilme_yuzde=17.2, geri_cekilme_min_kar_yuzde=0.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return cerceve(mumlar, (mumlar["hacim"] > 0) & yukari(kap, g.ema(kap, int(p["ema_n"]))), False, sl, ss)


# ================================================================ B001:650 (EMA520015_V17)
class Ema20Ema200B0650(_Taban):
    """HAM:B001:650 (4h, long; EMA520015_V17): kapanış EMA(20)'yi yukarı keser -> long; çıkış kapanış EMA(20)'yi aşağı keser. custom_exit (kanca): kâr > %2 VE
    EMA20 < EMA200. ROI {0 .15}; stop -%10; trailing +%1, offset %8 (yalnız offset sonrası)."""

    ad = "kapanis__ema20-ema200-b0650"
    varsayilan_parametreler = {"ema_n": 20, "ema_uzun": 200, "kar_esik": 2.0, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.15}, 240),
                                   geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=8.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        e20 = g.ema(kap, int(p["ema_n"]))
        al = (kap.shift(1) < e20) & (kap > e20)
        cik = (kap.shift(1) > e20) & (kap < e20)
        self._sakla(zayif=(e20 < g.ema(kap, int(p["ema_uzun"]))))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return (self._var(d.mum_indeksi) and d.kar_yuzde > float(self.parametreler["kar_esik"])
                and self._dz("zayif", d.mum_indeksi) > 0.5)


# ================================================================ B001:651 (EMABreakout)
class EmaBreakoutB0651(_Taban):
    """HAM:B001:651 (5m, long; EMABreakout, buy_macd_enabled=True, period 90): MACD histogramı >= 0 VE kapanış EMA(90)'ı yukarı keser VE hacim > 0 -> long;
    çıkış kapanış EMA(90)'ı aşağı keser (yalnız kârda: exit_profit_only). ROI {0 .278, 39 .087, 124 .038, 135 0}; trailing +%17,2 / offset %21,2 (offset
    öncesi de); stop -%33,3."""

    ad = "kapanis__ema-breakout-b0651"
    varsayilan_parametreler = {"ema_n": 90, "sl": 0.333}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.278, 39: 0.087, 124: 0.038, 135: 0}, 5),
                                   geri_cekilme_yuzde=17.2, geri_cekilme_min_kar_yuzde=0.0, yalniz_karda_cikis=True)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ema = g.ema(kap, int(p["ema_n"]))
        hist = g.macd(kap)["histogram"]
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        s = cerceve(mumlar, (mumlar["hacim"] > 0) & (hist >= 0) & yukari(kap, ema), False, sl, ss)
        return _bitir(s, asagi(kap, ema))


# ================================================================ B001:655 (EMA_CROSSOVER_STRATEGY)
class EmaCrossB0655(_Taban):
    """HAM:B001:655 (5m, long; EMA_CROSSOVER_STRATEGY): EMA10 EMA100'ü yukarı keser -> long; çıkış EMA100 EMA10'u yukarı keser (EMA10 aşağı). ROI {0 .04,
    30 .02, 60 .01}; stop -%10."""

    ad = "kapanis__ema-cross-b0655"
    varsayilan_parametreler = {"hizli": 10, "yavas": 100, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({60: 0.01, 30: 0.02, 0: 0.04}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ea, eb = g.ema(kap, int(p["hizli"])), g.ema(kap, int(p["yavas"]))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, yukari(ea, eb), False, sl, ss), yukari(eb, ea))


# ================================================================ B001:656 (HansenSmaOffsetV1)
class HansenSmaOffsetB0656(_Taban):
    """HAM:B001:656 (15m, long; HansenSmaOffsetV1): yüksek < SMA(20) x 0,95 VE hopen < hclose (hopen = iki mum önceki (açılış+kapanış)/2, hclose = OHLC/4) ->
    long; çıkış: düşük > SMA(20) x 1,05 VE hopen > hclose. ROI {0: 10} yok; stoploss -99 (stopsuz) -> ATR(14)x3."""

    ad = "kapanis__hansen-sma-ofset-b0656"
    varsayilan_parametreler = {"sma_n": 20, "alt": 0.95, "ust": 1.05, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        sma = g.sma(kap, int(p["sma_n"]))
        hopen = (mumlar["acilis"].shift(2) + kap.shift(2)) / 2.0
        hclose = _ohlc4(mumlar)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (mumlar["yuksek"] < sma * float(p["alt"])) & (hopen < hclose), False, kap - mes, kap + mes)
        return _bitir(s, (mumlar["dusuk"] > sma * float(p["ust"])) & (hopen > hclose))


# ================================================================ B001:662 (MultiMA_TSL)
class MultiMaTslB0662(_Taban):
    """HAM:B001:662 (5m, long; MultiMA_TSL, buy_params/sell_params dosyadaki etkin): giriş = ortak filtre [RSI(4) < 35 VE kapanış < EMA(50) x 1,061 VE hacim > 0]
    VE (TRIMA kolu: kapanış < TRIMA(14) x 0,963 VE (EWO(50,200) < -20 VEYA (EWO > 6 VE RSI(14) < 50)) VEYA ZEMA kolu: kapanış < ZEMA(30) x 0,963 VE aynı EWO/RSI
    koşulu). Çıkış: hacim > 0 VE (kapanış > EMA(32) x 1,002 VEYA kapanış > TRIMA(48) x 1,085). ROI {0: 100} yok; stop -%15."""

    ad = "kapanis__multima-tsl-b0662"
    varsayilan_parametreler = {"ema_al": 50, "ema_ofset": 1.061, "zema_n": 30, "zema_ofset": 0.963, "zema_rsi": 50,
                               "trima_n": 14, "trima_ofset": 0.963, "trima_rsi": 50, "ewo_hizli": 50, "ewo_yavas": 200,
                               "ewo_alt": -20.0, "ewo_ust": 6.0, "rsi_hizli": 35, "ema_sat": 32, "ema_sat_ofset": 1.002,
                               "trima_sat": 48, "trima_sat_ofset": 1.085, "sl": 0.15}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        ewo = _ewo(kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]))
        rsi = g.rsi(kap, 14)

        def kol(ma, rsi_esik):
            return (kap < ma) & ((ewo < float(p["ewo_alt"])) | ((ewo > float(p["ewo_ust"])) & (rsi < rsi_esik)))

        k_trima = kol(_trima(kap, int(p["trima_n"])) * float(p["trima_ofset"]), float(p["trima_rsi"]))
        k_zema = kol(_zema(kap, int(p["zema_n"])) * float(p["zema_ofset"]), float(p["zema_rsi"]))
        ortak = ((g.rsi(kap, 4) < float(p["rsi_hizli"])) & (kap < g.ema(kap, int(p["ema_al"])) * float(p["ema_ofset"]))
                 & (hac > 0))
        cik = (hac > 0) & ((kap > g.ema(kap, int(p["ema_sat"])) * float(p["ema_sat_ofset"]))
                           | (kap > _trima(kap, int(p["trima_sat"])) * float(p["trima_sat_ofset"])))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, ortak & (k_trima | k_zema), False, sl, ss), cik)


# ================================================================ B001:663 / 664 (MultiMA_TSL3 / Mod)
class _IzEmaKanca(_Taban):
    """Ortak: giriş sinyali mumunun EMA'sıyla tohumlanan iz-EMA (alpha = 2/(1+uzunluk)); kapanış > iz-EMA x ofset VE o mumda giriş sinyali yok -> çıkış
    ('New Sell Signal', yalnız backtest dalı). Artımlı hesaplanır (aynı giriş için bir önceki mum değeri önbellekte)."""

    def _iz_ema(self, e: int, i: int) -> float:
        kap = self._kd["kap"]
        alfa = 2.0 / (1.0 + float(self.parametreler["iz_uzunluk"]))
        c = getattr(self, "_izc", None)
        if c is not None and c[0] == e and c[1] == i - 1:
            s, bas = c[2], i
        else:
            s, bas = (float(self._kd["ema_sat"][e - 1]) if e >= 1 else math.nan), e
        for j in range(bas, i + 1):
            s = alfa * kap[j] + (1.0 - alfa) * s
        self._izc = (e, i, s)
        return s

    def _iz_cikis(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        s = self._iz_ema(d.giris_mum_indeksi, i)
        return bool(d.kapanis > s * float(self.parametreler["sat_ofset"]) and self._dz("al", i) == 0.0)


class MultiMaTsl3B0663(_IzEmaKanca):
    """HAM:B001:663 (5m, long; MultiMA_TSL3, etkin değerler): ortak filtre (hacim > 0 VE kapanış < yumuşak HA düşüğü (EMA4) VE kapanış < EMA(5) x 0,994 VE son 288
    mumun en yüksek kapanışı >= kapanış x 1,10 VE önceki yumuşak HA açılış < önceki yumuşak HA yükseği VE RSI(4) < 35, RSI(84) < 60, RSI(112) < 60 VE ((kapanış <
    EMA9 x 1,067 VE pm <= pmax_thresh VE (EWO < -19,632 VEYA (EWO > 2,615 VE RSI < 60))) VEYA (kapanış < EMA75 x 0,973 VE pm > pmax_thresh VE (EWO < -19,955 VEYA (EWO >
    2,188 VE RSI < 45))))) VE (TRIMA kolu VEYA ZEMA kolu VEYA HMA kolu). pm: HA üzerinde PMAX (EMA9, çarpan 2,7, ATR10); pmax_thresh: EMA9(OHLC4). Çıkış (kanca): iz-EMA
    (alpha 2/33; girişte EMA5 ile tohumlu) x 0,994 altında değilse ve o mumda giriş sinyali yoksa; kâra bağlı stop: zirve kâr > %4,7 ise stop = giriş x (1 + %4,6 +
    (kâr - %4,7)), %2-%4,7 arası %2 -> %4,6 doğrusal. ROI {0: 100} yok; stop -%15 (etkin)."""

    ad = "kapanis__multima-tsl3-b0663"
    varsayilan_parametreler = {
        "ewo_hizli": 50, "ewo_yavas": 200, "rsi_hizli": 35, "ema_sat_n": 5, "sat_ofset": 0.994, "iz_uzunluk": 32,
        "ema_a": 9, "ema_a_ofset": 1.067, "ema_b": 75, "ema_b_ofset": 0.973,
        "ewo_alt": -19.632, "ewo_ust": 2.615, "rsi_a": 60, "ewo_alt2": -19.955, "ewo_ust2": 2.188, "rsi_b": 45,
        "trima_a": 15, "trima_a_ofset": 0.959, "trima_b": 38, "trima_b_ofset": 0.949,
        "zema_a": 25, "zema_a_ofset": 0.958, "zema_b": 53, "zema_b_ofset": 0.961,
        "hma_a": 70, "hma_a_ofset": 0.948, "hma_b": 12, "hma_b_ofset": 0.941,
        "pf1": 0.02, "sl1": 0.02, "pf2": 0.047, "sl2": 0.046, "sl": 0.15}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        ewo = _ewo(kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]))
        rsi = g.rsi(kap, 14)
        ha = b2.heikin_ashi(mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], kap)
        pm = _pmax(ha)
        esik = g.ema(_ohlc4(mumlar), 9)
        alt_rejim, ust_rejim = pm <= esik, pm > esik
        ho, hh, hl = g.ema(ha["ha_acilis"], 4), g.ema(ha["ha_yuksek"], 4), g.ema(ha["ha_dusuk"], 4)
        ema_sat = g.ema(kap, int(p["ema_sat_n"]))

        def iki_kol(f, a, b):
            return (((kap < f(kap, int(p[a])) * float(p[a + "_ofset"])) & alt_rejim)
                    | ((kap < f(kap, int(p[b])) * float(p[b + "_ofset"])) & ust_rejim))

        k_trima = iki_kol(_trima, "trima_a", "trima_b")
        k_zema = iki_kol(_zema, "zema_a", "zema_b")
        hma1 = _hma_q(kap, int(p["hma_a"])) * float(p["hma_a_ofset"])
        hma2 = _hma_q(kap, int(p["hma_b"])) * float(p["hma_b_ofset"])
        k_hma = ((((kap < hma1) & alt_rejim & (rsi < 35)) | ((kap < hma2) & ust_rejim & (rsi < 30)))
                 & (g.rsi(kap, 4) < 30))
        ema_kol = (((kap < g.ema(kap, int(p["ema_a"])) * float(p["ema_a_ofset"])) & alt_rejim
                    & ((ewo < float(p["ewo_alt"])) | ((ewo > float(p["ewo_ust"])) & (rsi < float(p["rsi_a"])))))
                   | ((kap < g.ema(kap, int(p["ema_b"])) * float(p["ema_b_ofset"])) & ust_rejim
                      & ((ewo < float(p["ewo_alt2"])) | ((ewo > float(p["ewo_ust2"])) & (rsi < float(p["rsi_b"]))))))
        ortak = ((kap < hl) & (kap < ema_sat * float(p["sat_ofset"]))
                 & (kap.rolling(288).max() >= kap * 1.10) & (ho.shift(1) < hh.shift(1))
                 & (g.rsi(kap, 4) < float(p["rsi_hizli"])) & (g.rsi(kap, 84) < 60) & (g.rsi(kap, 112) < 60)
                 & ema_kol & (hac > 0))
        al = ortak & (k_trima | k_zema | k_hma)
        self._izc = None
        self._sakla(kap=kap, ema_sat=ema_sat, al=al)
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return cerceve(mumlar, al, False, sl, ss)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        if self._iz_cikis(d):
            return True
        p = self.parametreler
        kp = d.en_yuksek / d.giris_fiyati - 1.0
        pf1, sl1, pf2, sl2 = (float(p[k]) for k in ("pf1", "sl1", "pf2", "sl2"))
        if kp > pf2:
            sl_kar = sl2 + (kp - pf2)
        elif kp > pf1:
            sl_kar = sl1 + (kp - pf1) * (sl2 - sl1) / (pf2 - pf1)
        else:
            return False
        return bool(d.kapanis <= d.giris_fiyati * (1.0 + sl_kar))


class MultiMaTsl3ModB0664(_IzEmaKanca):
    """HAM:B001:664 (5m, long; MultiMA_TSL3_Mod): giriş = SAR, pmax_thresh'i (EMA9 OHLC4) aşağı keser VE pmax_thresh > pm VE pmax_thresh > SAR VE: pmax_pct (EMA9(OHLC4)'in
    288 mumluk aralıktaki yeri, %) 20,09-83,754 arası VE hacim değişimi 0,247-8,721 arası VE kapanış değişimi 0,01121-0,06785 arası VE RSI(14) 24-79 arası VE RSI(4) 36-98
    arası VE EWO(12,150) > 0,546 VE hacim > 0. Çıkış (kanca): iz-EMA (alpha 2/33; girişte EMA(65) ile tohumlu) x 1,074 üstünde VE o mumda giriş yok; kâra bağlı iz: zirve kâr
    > %20 ise zirveden %5, > %10 ise %3, > %6 ise %2, > %3 ise %1 geri çekilmede çık. ROI {0: 100} yok; stop -%15."""

    ad = "kapanis__multima-tsl3-mod-b0664"
    varsayilan_parametreler = {
        "ewo_hizli": 12, "ewo_yavas": 150, "ewo_alt": 0.546, "pmax_min": 20.09, "pmax_max": 83.754, "hacim_min": 0.247,
        "hacim_max": 8.721, "kapanis_min": 0.01121, "kapanis_max": 0.06785, "rsi_min": 24, "rsi_max": 79,
        "rsi_hizli_min": 36, "rsi_hizli_max": 98, "ema_sat_n": 65, "sat_ofset": 1.074, "iz_uzunluk": 32, "sl": 0.15,
        "iz_basamak": ((20.0, 0.05), (10.0, 0.03), (6.0, 0.02), (3.0, 0.01))}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        ha = b2.heikin_ashi(mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], kap)
        pm = _pmax(ha)
        esik = g.ema(_ohlc4(mumlar), 9)
        sar = _sar(mumlar["yuksek"], mumlar["dusuk"])
        y24 = mumlar["yuksek"].rolling(288, min_periods=288).max()
        d24 = mumlar["dusuk"].rolling(288, min_periods=288).min()
        pmax_pct = (esik - d24) / (y24 - d24) * 100.0
        hac_pct = hac.pct_change(fill_method=None)
        kap_pct = kap.pct_change(fill_method=None)
        rsi, rsi4 = g.rsi(kap, 14), g.rsi(kap, 4)
        ewo = _ewo(kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]))
        tetik = asagi(sar, esik) & (esik > pm) & (esik > sar)
        filtre = ((pmax_pct > float(p["pmax_min"])) & (hac_pct > float(p["hacim_min"])) & (kap_pct > float(p["kapanis_min"]))
                  & (rsi > float(p["rsi_min"])) & (rsi4 > float(p["rsi_hizli_min"])) & (pmax_pct < float(p["pmax_max"]))
                  & (hac_pct < float(p["hacim_max"])) & (kap_pct < float(p["kapanis_max"])) & (rsi < float(p["rsi_max"]))
                  & (rsi4 < float(p["rsi_hizli_max"])) & (ewo > float(p["ewo_alt"])) & (hac > 0))
        al = tetik & filtre
        self._izc = None
        self._sakla(kap=kap, ema_sat=g.ema(kap, int(p["ema_sat_n"])), al=al)
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return cerceve(mumlar, al, False, sl, ss)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        if self._iz_cikis(d):
            return True
        kp = (d.en_yuksek / d.giris_fiyati - 1.0) * 100.0
        for esik, mesafe in self.parametreler["iz_basamak"]:
            if kp > esik:
                return bool(d.kapanis <= d.en_yuksek * (1.0 - mesafe))
        return False


# ================================================================ B001:679 (ObeliskIM_v1_1)
class ObeliskImB0679(_Taban):
    """HAM:B001:679 (5m, long; ObeliskIM_v1_1): Ichimoku(20/60/120, kaydırma 30): güçlü yeşil bulut (senkou A > B, tenkan > kijun, kijun > senkou A) VE son 3 mumda
    tenkan kijun'u yukarı kesmiş VE EMA3 > EMA5 > EMA10 VE kapanış > önceki kapanış VE kapanış > önceki mumun 12 mumluk en yükseği VE spike yok (kapanış <= 3 mum
    önceki kapanış x 1,036) -> long. Çıkış: tenkan kijun'u aşağı keser VEYA kapanış kijun'u aşağı keser. ROI {0: 5} yok; stop -%4."""

    ad = "kapanis__obelisk-im-b0679"
    varsayilan_parametreler = {"spike": 1.036, "yuksek_n": 12, "kes_pencere": 3, "sl": 0.04}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ich = _ichi(mumlar["yuksek"], mumlar["dusuk"], 20, 60, 120, 30)
        tenkan, kijun, sen_a, sen_b = ich["tenkan"], ich["kijun"], ich["sen_a"], ich["sen_b"]
        guclu = (sen_a > sen_b) & (tenkan > kijun) & (kijun > sen_a)
        kes = yukari(tenkan, kijun).astype(int).rolling(int(p["kes_pencere"]), min_periods=1).max() > 0
        e3, e5, e10 = g.ema(kap, 3), g.ema(kap, 5), g.ema(kap, 10)
        spike = kap > kap.shift(3) * float(p["spike"])
        yuksek12 = mumlar["yuksek"].rolling(int(p["yuksek_n"])).max()
        al = guclu & kes & (e3 > e5) & (e5 > e10) & (kap > kap.shift(1)) & (kap > yuksek12.shift(1)) & ~spike
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), asagi(tenkan, kijun) | asagi(kap, kijun))


# ================================================================ B001:680 (ObeliskRSI_v6_1)
class ObeliskRsiB0680(_Taban):
    """HAM:B001:680 (5m, long; ObeliskRSI_v6_1): boğa = 1h (kapanmış) RSI(14) > 60. Giriş: hacim > 0 VE (boğa VE RSI(14) 35'i aşağı keser) VEYA (boğa değil VE RSI 21'i
    aşağı keser); çıkış: hacim > 0 VE (boğa VE RSI > 69) VEYA (boğa değil VE RSI > 55). ROI {0 .15, 35 .04, 65 .01, 115 0}; stop -%30; custom_stoploss (kanca): kapanıştan
    %(30 x (1 - rampa^3) + 0,1) aşağıda taşınan, yalnız yukarı giden stop; rampa = girişten geçen süre / 110 dk (0-1)."""

    ad = "kapanis__obelisk-rsi-b0680"
    varsayilan_parametreler = {"rsi_n": 14, "boga_esik": 60.0, "boga_al": 35.0, "ayi_al": 21.0, "boga_sat": 69.0,
                               "ayi_sat": 55.0, "rampa_dk": 110.0, "sl": 0.30}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.15, 35: 0.04, 65: 0.01, 115: 0}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        rsi = g.rsi(kap, int(p["rsi_n"]))
        r1h = ust_zaman(mumlar, "1h", lambda u: g.rsi(u["kapanis"], int(p["rsi_n"])))
        boga = (r1h > float(p["boga_esik"])).fillna(False).astype(bool)
        al = (hac > 0) & ((boga & asagi(rsi, float(p["boga_al"]))) | (~boga & asagi(rsi, float(p["ayi_al"]))))
        cik = (hac > 0) & ((boga & (rsi > float(p["boga_sat"]))) | (~boga & (rsi > float(p["ayi_sat"]))))
        self._sakla(kap=kap, dk=np.full(len(kap), _dk(mumlar)))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        e = d.giris_mum_indeksi
        if i <= e:
            return False
        j = np.arange(e, i)                                  # önceki mumlarda kurulan stoplar (bu mumun stopu kapanışa bağlı)
        rampa = np.clip((j - e) * self._dz("dk", i) / float(p["rampa_dk"]), 0.0, 1.0)
        stop = (self._kd["kap"][j] * (1.0 - (float(p["sl"]) * (1.0 - rampa ** 3) + 0.001))).max()
        return bool(d.kapanis <= stop)


# ================================================================ B001:681 (Obelisk_3EMA_StochRSI_ATR)
def _uc_ema_ham(u: pd.DataFrame) -> pd.DataFrame:
    k = u["kapanis"]
    e8, e14, e50 = g.ema(k, 8), g.ema(k, 14), g.ema(k, 50)
    atr = g.atr(u["yuksek"], u["dusuk"], k, 14)
    r = g.rsi(k, 14)
    mn, mx = r.rolling(14).min(), r.rolling(14).max()
    sk = ((r - mn) / (mx - mn)).rolling(3).mean() * 100.0
    sd = sk.rolling(3).mean()
    git = ((e8 > e14) & (e14 > e50) & yukari(sk, sd)).astype(float)
    yeni = (git > 0) & ~(git.shift(1) > 0)
    tp = (k + 2.0 * atr).where(yeni).ffill()
    sp = (3.0 * atr / k).where(yeni).ffill()
    return pd.DataFrame({"git": git, "tp": tp, "sp": sp}, index=u.index)


class Obelisk3EmaStochB0681(_Taban):
    """HAM:B001:681 (5m yürütme, 1h sinyal; Obelisk_3EMA_StochRSI_ATR): 1h (kapanmış mum) EMA8 > EMA14 > EMA50 VE StochRSI(14,14,K=SMA3,D=SMA3) %K %D'yi yukarı keser ->
    go_long (0 -> 1 ilk 5m mumda giriş). Çıkış (kanca): kapanış > 1h sinyal kapanışı + 2xATR(14, 1h). Stop = giriş x (1 - 3xATR(1h)/1h kapanış) (stoploss -0,99 ->
    ATR3 ile aynı büyüklük). ROI {0: 1} yok."""

    ad = "kapanis__obelisk-3ema-stoch-b0681"
    varsayilan_parametreler = {}

    def sinyaller(self, mumlar):
        kap = mumlar["kapanis"]
        ham = ust_zaman(mumlar, "1h", _uc_ema_ham)
        al = yukari(ham["git"], 0)
        self._sakla(tp=ham["tp"])
        return cerceve(mumlar, al, False, kap * (1.0 - ham["sp"]), kap * (1.0 + ham["sp"]))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return bool(d.kapanis > self._dz("tp", d.giris_mum_indeksi))


# ================================================================ B001:682 / 683 (Obelisk TradePro Ichi)
class TradeProIchiV1B0682(_Taban):
    """HAM:B001:682 (1h, long; Obelisk_TradePro_Ichi_v1_1): Ichimoku(20/60/120, kaydırma 30): tenkan > kijun VE kapanış > senkou A ve B VE öndeki bulut yeşil VE kapanış >
    30 mum önceki bulut (chikou_high) durumunun 0 -> 1 geçişi -> long. Çıkış: tenkan kijun'u aşağı keser VEYA kapanış kijun'u aşağı keser. ROI {0: 10} yok; stop -%1,5."""

    ad = "kapanis__tradepro-ichi-v1-b0682"
    varsayilan_parametreler = {"sl": 0.015}

    def _durum(self, m):
        kap = m["kapanis"]
        ich = _ichi(m["yuksek"], m["dusuk"], 20, 60, 120, 30)
        chikou = (kap > ich["sen_a"].shift(30)) & (kap > ich["sen_b"].shift(30))
        go = ((ich["tenkan"] > ich["kijun"]) & (kap > ich["sen_a"]) & (kap > ich["sen_b"])
              & (ich["lead_a"] > ich["lead_b"]) & chikou)
        return ich, go

    def sinyaller(self, mumlar):
        kap = mumlar["kapanis"]
        ich, go = self._durum(mumlar)
        al = go & ~go.shift(1, fill_value=False)
        sl, ss = _yuzde_stop(mumlar, float(self.parametreler["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), asagi(ich["tenkan"], ich["kijun"]) | asagi(kap, ich["kijun"]))


class TradeProIchiV2B0683(TradeProIchiV1B0682):
    """HAM:B001:683 (1h, long; Obelisk_TradePro_Ichi_v2_1): 682 koşuluna ek: SSL(10) yukarı (up > down) VE ROCR(28) bir öncekinden büyük VE RMI(9, mom 3) iki mum önceki
    değerinden büyük; durumun 0 -> 1 geçişi -> long. Çıkış: SSL aşağı (ssl_high == 0) VE (tenkan < kijun VEYA kapanış < kijun). Stop -%7,5; trailing +%0,5 / offset %3
    (yalnız offset sonrası)."""

    ad = "kapanis__tradepro-ichi-v2-b0683"
    varsayilan_parametreler = {"sl": 0.075}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=0.5, geri_cekilme_min_kar_yuzde=3.0)

    def sinyaller(self, mumlar):
        kap = mumlar["kapanis"]
        ich, go = self._durum(mumlar)
        asagi_, yukari_ = _ssl_kanal(mumlar["yuksek"], mumlar["dusuk"], kap, 10)
        ssl_yuksek = yukari_ > asagi_
        rocr = kap / kap.shift(28)
        rmi = _rmi(kap, 9, 3)
        go = go & ssl_yuksek & (rocr > rocr.shift(1)) & (rmi > rmi.shift(2))
        al = go & ~go.shift(1, fill_value=False)
        cik = ~ssl_yuksek & ((ich["tenkan"] < ich["kijun"]) | (kap < ich["kijun"]))
        sl, ss = _yuzde_stop(mumlar, float(self.parametreler["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)


# ================================================================ B001:685 (Renko)
class RenkoB0685(_Taban):
    """HAM:B001:685 (15m, long; Renko): tuğla boyu = ATR(5) (her mumda güncel); trend yukarıyken 1 tuğla yukarı devam, 2 tuğla ters dönüş = trend dönüşü; giriş: tuğla oluşan mumda
    trend yukarı; çıkış: tuğla oluşan mumda (önceki olay trendi yukarı ve şimdiki yukarı) DEĞİLSE, yalnız kâr > %10 iken (sell_profit_offset 0,1). ROI {0: 100} yok;
    stoploss -100 (stopsuz) -> ATR(14)x3. Uyarlama: ATR(5) hazır olana kadar tuğla yok (kaynakta ilk tuğla boyu tüm-seri ATR ortalaması)."""

    ad = "kapanis__renko-b0685"
    varsayilan_parametreler = {"renko_atr": 5, "atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=10.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["renko_atr"])).to_numpy(dtype=float).tolist()
        c = kap.to_numpy(dtype=float).tolist()
        n = len(c)
        giris, cikis = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
        cp, trend, onceki_olay_trend = c[0] if n else 0.0, True, True
        for i in range(1, n):
            bs = atr[i]
            if not (bs == bs) or bs <= 0:
                continue
            tuglalar = int((c[i] - cp) / bs)
            if (trend and tuglalar >= 1) or (not trend and tuglalar <= -1):
                pass
            elif trend and tuglalar <= -2:
                trend = False
            elif not trend and tuglalar >= 2:
                trend = True
            else:
                continue
            cp += tuglalar * bs
            giris[i] = trend
            cikis[i] = not (onceki_olay_trend and trend)
            onceki_olay_trend = trend
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, pd.Series(giris, index=mumlar.index), False, kap - mes, kap + mes)
        return _bitir(s, pd.Series(cikis, index=mumlar.index))


# ================================================================ B001:699 (SMAOffsetV2)
class SmaOffsetV2B0699(_Taban):
    """HAM:B001:699 (5m, long; SMAOffsetV2): 1h (kapanmış) EMA(20) > EMA(25) (go_long) VE kapanış < SMA(20) x 0,96 VE hacim > 0 -> long; çıkış: (go_long == 0 VEYA kapanış >
    SMA(20) x 1,012) VE hacim > 0. ROI {0: 1}; stoploss -%20; custom_stoploss (kanca): 40 dk'dan uzun tutulup kâr < -%10 ise çık."""

    ad = "kapanis__sma-ofset-v2-b0699"
    varsayilan_parametreler = {"sma_n": 20, "alt": 0.96, "ust": 1.012, "ema_hizli": 20, "ema_yavas": 25, "bekle_dk": 40.0,
                               "zarar_esik": -10.0, "sl": 0.20}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 1}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        ust = ust_zaman(mumlar, "1h", lambda u: (g.ema(u["kapanis"], int(p["ema_hizli"]))
                                                 > g.ema(u["kapanis"], int(p["ema_yavas"]))).astype(float))
        sma = g.sma(kap, int(p["sma_n"]))
        al = (ust > 0.5) & (kap < sma * float(p["alt"])) & (hac > 0)
        cik = ((ust == 0) | (kap > sma * float(p["ust"]))) & (hac > 0)
        self._sakla(dk=np.full(len(kap), _dk(mumlar)))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        return bool(self._var(d.mum_indeksi) and d.tutulan_mum * self._dz("dk", d.mum_indeksi) > float(p["bekle_dk"])
                    and d.kar_yuzde < float(p["zarar_esik"]))


# ================================================================ B001:701 (UziChan)
def _ssf(kap: pd.Series, uzun: int = 5) -> pd.Series:
    """Ehlers Super Smoother Filter, 2 kutuplu (pandas_ta ssf varsayılanı); ilk iki değer kapanış (nedensel başlangıç)."""
    x = math.pi * math.sqrt(2.0) / uzun
    a0 = math.exp(-x)
    c2, c3 = 2.0 * a0 * math.cos(x), -a0 * a0
    c1 = 1.0 - c2 - c3
    v = kap.to_numpy(dtype=float)
    out = v.copy()
    for i in range(2, len(v)):
        out[i] = c1 * v[i] + c2 * out[i - 1] + c3 * out[i - 2]
    return pd.Series(out, index=kap.index)


class UziChanB0701(_Taban):
    """HAM:B001:701 (5m, long; UziChan): uc_mid = SSF(kapanış, 5); uc_stdv = STDDEV(uc_mid, 15) (5 hane yuvarlı); uc_low = EMA(uc_mid - uc_stdv, 3), uc_up = EMA(uc_mid + uc_stdv, 3)
    (5 hane yuvarlı); co = ADOSC(30, 100) (3 hane yuvarlı). Giriş: (kapanış < uc_low VEYA açılış < uc_low) VE co > önceki co. Çıkış: yüksek > uc_up VE co > önceki co.
    ROI {0 .10}; stop -%10."""

    ad = "kapanis__uzichan-b0701"
    varsayilan_parametreler = {"ssf_n": 5, "std_n": 15, "ema_n": 3, "ad_hizli": 30, "ad_yavas": 100, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.1}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mid = _ssf(kap, int(p["ssf_n"]))
        std = mid.rolling(int(p["std_n"])).std(ddof=0).round(5)
        alt = g.ema(mid - std, int(p["ema_n"])).round(5)
        ust = g.ema(mid + std, int(p["ema_n"])).round(5)
        ad = _ad(mumlar["yuksek"], mumlar["dusuk"], kap, mumlar["hacim"])
        co = (g.ema(ad, int(p["ad_hizli"])) - g.ema(ad, int(p["ad_yavas"]))).round(3)
        artiyor = co > co.shift(1)
        al = ((kap < alt) | (mumlar["acilis"] < alt)) & artiyor
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), (mumlar["yuksek"] > ust) & artiyor)


# ================================================================ B001:703 (ema.py)
class EmaOsilatorB0703(_Taban):
    """HAM:B001:703 (5m, long; ema.py): osc = 0,6 x (EMA9 - EMA18) + 0,5 x (EMA32 - EMA64); sinyal = SMA(osc, 29); osc sinyali yukarı keser -> long, aşağı keser -> çıkış. ROI {0: 10}
    yok; stoploss -1 (stopsuz) -> ATR(14)x3."""

    ad = "kapanis__ema-osilator-b0703"
    varsayilan_parametreler = {"e1": 9, "e2": 18, "e3": 32, "e4": 64, "k1": 0.6, "k2": 0.5, "sinyal_n": 29,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        osc = (float(p["k1"]) * (g.ema(kap, int(p["e1"])) - g.ema(kap, int(p["e2"])))
               + float(p["k2"]) * (g.ema(kap, int(p["e3"])) - g.ema(kap, int(p["e4"]))))
        sg = g.sma(osc, int(p["sinyal_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(mumlar, yukari(osc, sg), False, kap - mes, kap + mes), asagi(osc, sg))


# ================================================================ B001:704 (hansencandlepatternV1)
def _ort_aralik(x: pd.Series, n: int, kat: int) -> pd.Series:
    """TA-Lib ortalama: `kat` mum önceki mumun öncesindeki n mumun ortalaması (kat=0: bu mumun öncesi)."""
    return x.shift(1 + kat).rolling(n, min_periods=n).mean()


def _cdl_ortak(m: pd.DataFrame):
    o, h, l, c = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    govde = (c - o).abs()
    return o, h, l, c, govde, (c >= o)


def cdl_uc_cizgi_vurus(m: pd.DataFrame) -> pd.Series:
    """TA-Lib CDL3LINESTRIKE: ilk üç mum aynı renk, her biri öncekinin gövdesine yakın açılıp ilerleyen kapanışla; 4. mum zıt renk, ilk mumun açılışının ötesinde kapanır.
    Değer = üçlünün rengi x 100 (kırmızı üçlü + boğa 4. mum = -100)."""
    o, h, l, c, _, beyaz = _cdl_ortak(m)
    yakin = 0.2 * _ort_aralik(h - l, 5, 0)
    y3, y2 = yakin.shift(3), yakin.shift(2)
    o1, o2, o3 = o.shift(3), o.shift(2), o.shift(1)
    c1, c2, c3 = c.shift(3), c.shift(2), c.shift(1)
    renk = lambda b: b.map({True: 1, False: -1})   # noqa: E731
    r1, r2, r3, r4 = renk(beyaz.shift(3)), renk(beyaz.shift(2)), renk(beyaz.shift(1)), renk(beyaz)
    govde_ok = ((o2 >= pd.concat([o1, c1], axis=1).min(axis=1) - y3) & (o2 <= pd.concat([o1, c1], axis=1).max(axis=1) + y3)
                & (o3 >= pd.concat([o2, c2], axis=1).min(axis=1) - y2) & (o3 <= pd.concat([o2, c2], axis=1).max(axis=1) + y2))
    ayni = (r1 == r2) & (r2 == r3) & (r4 == -r3)
    beyaz_ucu = (r3 == 1) & (c3 > c2) & (c2 > c1) & (c < o1)
    kara_ucu = (r3 == -1) & (c3 < c2) & (c2 < c1) & (c > o1)
    ok = ayni & govde_ok & (beyaz_ucu | kara_ucu)
    return pd.Series(np.where(ok, r3 * 100.0, 0.0), index=m.index)


def cdl_aksam_yildizi(m: pd.DataFrame, nufuz: float = 0.3) -> pd.Series:
    """TA-Lib CDLEVENINGSTAR: uzun beyaz, yukarı boşluklu kısa gövde, kısa olmayan kırmızı mum ilk gövdenin %30'undan fazlasına iner. Değer yalnız -100 ya da 0."""
    o, h, l, c, govde, beyaz = _cdl_ortak(m)
    uzun = _ort_aralik(govde, 10, 2)          # i-2 mumu için
    kisa1 = _ort_aralik(govde, 10, 1)         # i-1 mumu için
    kisa0 = _ort_aralik(govde, 10, 0)
    ust1 = pd.concat([o.shift(1), c.shift(1)], axis=1).min(axis=1)
    ust2 = pd.concat([o.shift(2), c.shift(2)], axis=1).max(axis=1)
    ok = ((govde.shift(2) > uzun) & beyaz.shift(2, fill_value=False) & (govde.shift(1) <= kisa1) & (ust1 > ust2)
          & (govde > kisa0) & ~beyaz & (c < c.shift(2) - govde.shift(2) * nufuz))
    return pd.Series(np.where(ok, -100.0, 0.0), index=m.index)


def cdl_harami(m: pd.DataFrame) -> pd.Series:
    """TA-Lib CDLHARAMI: uzun gövdeli ilk mum, gövdesi içine (<=, >=) oturan kısa ikinci mum. Değer = -(ilk mumun rengi) x 100 (kırmızı ilk mum -> boğa, > 0)."""
    o, h, l, c, govde, beyaz = _cdl_ortak(m)
    uzun = _ort_aralik(govde, 10, 1)
    kisa = _ort_aralik(govde, 10, 0)
    ust, alt = pd.concat([o, c], axis=1).max(axis=1), pd.concat([o, c], axis=1).min(axis=1)
    ok = ((govde.shift(1) > uzun) & (govde <= kisa) & (ust <= ust.shift(1)) & (alt >= alt.shift(1)))
    renk1 = beyaz.shift(1).map({True: 1, False: -1})
    return pd.Series(np.where(ok, -renk1 * 100.0, 0.0), index=m.index)


def cdl_yutan(m: pd.DataFrame) -> pd.Series:
    """TA-Lib CDLENGULFING: ikinci mumun gövdesi ilkini yutar. Değer = ikinci mumun rengi x 100/200 (beyaz yutan > 0)."""
    o, h, l, c, govde, beyaz = _cdl_ortak(m)
    o1, c1, b1 = o.shift(1), c.shift(1), beyaz.shift(1).fillna(True).astype(bool)
    boga = beyaz & ~b1 & (((c >= o1) & (o < c1)) | ((c > o1) & (o <= c1)))
    ayi = ~beyaz & b1 & (((o >= c1) & (c < o1)) | ((o > c1) & (c <= o1)))
    return pd.Series(np.where(boga, 100.0, np.where(ayi, -100.0, 0.0)), index=m.index)


class HansenMumB0704(_Taban):
    """HAM:B001:704 (1h, long; hansencandlepatternV1): (CDL3LINESTRIKE < 0 VEYA CDLEVENINGSTAR > 0 VEYA 'ABANDONEDBABY' (kaynakta aynı EVENINGSTAR sütunu) > 0 VEYA CDLHARAMI > 0 VEYA
    CDLENGULFING > 0) VE SMA6(hopen) < SMA6(hclose) (hopen = iki mum önceki (açılış+kapanış)/2, hclose = OHLC/4) -> long; çıkış SMA6(hopen) > SMA6(hclose). ROI {0: 10} yok; stop -%10."""

    ad = "kapanis__hansen-mum-b0704"
    varsayilan_parametreler = {"sma_n": 6, "sl": 0.10}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        aksam = cdl_aksam_yildizi(mumlar)
        desen = ((cdl_uc_cizgi_vurus(mumlar) < 0) | (aksam > 0) | (aksam > 0) | (cdl_harami(mumlar) > 0)
                 | (cdl_yutan(mumlar) > 0))
        emao = g.sma((mumlar["acilis"].shift(2) + kap.shift(2)) / 2.0, int(p["sma_n"]))
        emac = g.sma(_ohlc4(mumlar), int(p["sma_n"]))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, desen & (emao < emac), False, sl, ss), emao > emac)


# ================================================================ B001:707 / 708 (OmaGann)
def _oma(s: pd.Series, uzun: int, ayar: bool) -> pd.Series:
    """T3 benzeri üç kat çift EMA (alpha = 1/uzun): 1,5 x e - 0,5 x e(e), üç tur."""
    a = 1.0 / uzun

    def e(x):
        return x.ewm(alpha=a, adjust=ayar).mean()
    e1 = e(s)
    v1 = 1.5 * e1 - 0.5 * e(e1)
    e3 = e(v1)
    v2 = 1.5 * e3 - 0.5 * e(e3)
    e5 = e(v2)
    return 1.5 * e5 - 0.5 * e(e5)


class OmaGannB0707(_Taban):
    """HAM:B001:707 (1h, long; OmaGann, OmaGann.json etkin): OMA(yüksek, 13), OMA(düşük, 13), OMA(kapanış, 3) (ewm adjust=False). jfghla: close_ma > önceki high_ma ise low_ma[t];
    close_ma < önceki low_ma ise high_ma[t]; aksi önceki. trend = işaret(close_ma - jfghla). trend 1'e dönünce (önceki <= 0) long; -1'e dönünce (önceki >= 0) çıkış. ROI {0 .113,
    418 .076, 1323 .041, 2236 0}; stop -%13; trailing +%13,6 / offset %17,7 (offset öncesi de)."""

    ad = "kapanis__oma-gann-b0707"
    varsayilan_parametreler = {"uzun": 13, "kapanis_uzun": 3, "ayar": False, "sl": 0.13}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.113, 418: 0.076, 1323: 0.041, 2236: 0}, 60),
                                   geri_cekilme_yuzde=13.6, geri_cekilme_min_kar_yuzde=0.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        ayar = bool(p["ayar"])
        hm = _oma(mumlar["yuksek"], int(p["uzun"]), ayar).to_numpy(dtype=float)
        lm = _oma(mumlar["dusuk"], int(p["uzun"]), ayar).to_numpy(dtype=float)
        cm = _oma(mumlar["kapanis"], int(p["kapanis_uzun"]), ayar).to_numpy(dtype=float)
        n = len(cm)
        jf = np.full(n, np.nan)
        for i in range(1, n):
            if cm[i] > hm[i - 1]:
                jf[i] = lm[i]
            elif cm[i] < lm[i - 1]:
                jf[i] = hm[i]
            else:
                jf[i] = jf[i - 1]
        with np.errstate(invalid="ignore"):
            trend = pd.Series(np.where(cm > jf, 1, np.where(cm < jf, -1, 0)), index=mumlar.index)
        onceki = trend.shift(1)
        al = (trend == 1) & (onceki <= 0)
        cik = (trend == -1) & (onceki >= 0)
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl, ss), cik)


class OmaGann30mB0708(OmaGannB0707):
    """HAM:B001:708 (30m, long; OmaGann__2): 707 ile aynı kural; yalnız TF 30m, ewm adjust=True ve varsayılanlar (OMA uzunluk 10, kapanış uzunluğu 1). ROI {0 .1}; stop -%10;
    trailing yok."""

    ad = "kapanis__oma-gann-30m-b0708"
    varsayilan_parametreler = {"uzun": 10, "kapanis_uzun": 1, "ayar": True, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.1}, 30))


# ================================================================ B001:741 (PrawnstarOBV)
class PrawnstarObvB0741(_Taban):
    """HAM:B001:741 (1h, long; PrawnstarOBV): (OBV, SMA7(OBV)'yi yukarı keser VE RSI(14) < 50) VEYA ((SMA7(OBV) - kapanış)/SMA7(OBV) > 0,1) VEYA (OBV > önceki OBV VE SMA7(OBV) > 5 mum önceki
    SMA7(OBV) VE RSI < 50) -> long. Sinyal çıkışı yok. ROI {0 .296, 179 .137, 810 .025, 1024 0}; stop -%15; trailing +%0,1 / offset %4 (yalnız offset sonrası)."""

    ad = "kapanis__prawnstar-obv-b0741"
    varsayilan_parametreler = {"sma_n": 7, "rsi_esik": 50.0, "fark": 0.1, "sl": 0.15}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.296, 179: 0.137, 810: 0.025, 1024: 0}, 60),
                                   geri_cekilme_yuzde=0.1, geri_cekilme_min_kar_yuzde=4.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        yon = np.sign(kap.diff()).fillna(1.0)                 # TA-Lib OBV: ilk değer = ilk hacim
        obv = (yon * mumlar["hacim"]).cumsum()
        sma = g.sma(obv, int(p["sma_n"]))
        rsi = g.rsi(kap, 14)
        al = ((yukari(obv, sma) & (rsi < float(p["rsi_esik"]))) | (((sma - kap) / sma) > float(p["fark"]))
              | ((obv > obv.shift(1)) & (sma > sma.shift(5)) & (rsi < float(p["rsi_esik"]))))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return cerceve(mumlar, al, False, sl, ss)


# ================================================================ B001:742 (VWAP)
class VwapDipB0742(_Taban):
    """HAM:B001:742 (5m, long; VWAP): kapanış < VWAP bandı alt çizgisi (20 mumluk kayan VWAP - 20 mumluk std(VWAP)) VE (son 4 açılışın en yükseği - kapanış)/kapanış > 0,04 VE
    CTI(20) < -0,8 VE RSI(14) < 35 VE RSI(84) < 60 VE RSI(112) < 60 VE hacim > 0 -> long. Sinyal çıkışı yok. ROI {0 .02}; stop -%15."""

    ad = "kapanis__vwap-dip-b0742"
    varsayilan_parametreler = {"vwap_n": 20, "tcp_n": 4, "tcp_esik": 0.04, "cti_n": 20, "cti_esik": -0.8, "sl": 0.15}
    cikis_ayarlari = CikisAyarlari(azalan_roi=roi_tablosu({0: 0.02}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        n = int(p["vwap_n"])
        vwap = (hac * _tipik(mumlar)).rolling(n).sum() / hac.rolling(n).sum()
        alt = vwap - vwap.rolling(n).std()
        tcp = (mumlar["acilis"].rolling(int(p["tcp_n"])).max() - kap) / kap
        al = ((kap < alt) & (tcp > float(p["tcp_esik"])) & (_kor(kap, int(p["cti_n"])) < float(p["cti_esik"]))
              & (g.rsi(kap, 14) < 35) & (g.rsi(kap, 84) < 60) & (g.rsi(kap, 112) < 60) & (hac > 0))
        sl, ss = _yuzde_stop(mumlar, float(p["sl"]))
        return cerceve(mumlar, al, False, sl, ss)


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


# ================================================================ koşu listesi
SINIFLAR = [NowoIchimoku1hV1B0634, NowoIchimokuV2B0635, NowoIchimoku5mV2B0636, ObeliskIchiSlowB0637, ObeliskIchiZemaB0638,
            IchiV1B0642, ChispeiB0645, DoubleEmaTrendB0648, Ema50B0649, Ema20Ema200B0650, EmaBreakoutB0651, EmaCrossB0655,
            HansenSmaOffsetB0656, MultiMaTslB0662, MultiMaTsl3B0663, MultiMaTsl3ModB0664, ObeliskImB0679, ObeliskRsiB0680,
            Obelisk3EmaStochB0681, TradeProIchiV1B0682, TradeProIchiV2B0683, RenkoB0685, SmaOffsetV2B0699, UziChanB0701,
            EmaOsilatorB0703, HansenMumB0704, OmaGannB0707, OmaGann30mB0708, PrawnstarObvB0741, VwapDipB0742]

_TF = {634: "1h", 635: "1h", 636: "5m", 637: "1h", 638: "5m", 642: "5m", 645: "4h", 648: "1h", 649: "5m", 650: "4h", 651: "5m",
       655: "5m", 656: "15m", 662: "5m", 663: "5m", 664: "5m", 679: "5m", 680: "5m", 681: "5m", 682: "1h", 683: "1h",
       685: "15m", 699: "5m", 701: "5m", 703: "5m", 704: "1h", 707: "1h", 708: "30m", 741: "1h", 742: "5m"}


def _v(sinif) -> dict:
    no = int(sinif.ad.rsplit("-b", 1)[1])
    return {"kimlik": f"HAM:B001:{no}#v1", "sinif": sinif.ad, "parametreler": dict(sinif.varsayilan_parametreler),
            "tf": _TF[no]}


VARYANTLAR = [_v(s) for s in SINIFLAR]

KODLANAMADI = []
