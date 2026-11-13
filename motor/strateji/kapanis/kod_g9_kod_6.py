"""Kapanış turu, kodlama partisi g9_kod_6 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_6.csv, 30 Robotic (HAM:B001) kaynak satırı).

Her sınıf, satırın `kanit` sütunundaki kaynak dosyadan (yalnız OKUNDU, çalıştırılmadı) kendi cümleleriyle yazılmış bir
uyarlamadır; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel
(gelecek verisi yok); üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise (754, 768, 795, 803) stop = kapanış - 3 x ATR(14) (ön kayıt uyarlaması). Aksi halde kaynak
  yüzde stopu sinyal kapanışından hesaplanır (dolum sonraki açılıştan olduğu için gerçek mesafe biraz farklıdır).
- Freqtrade `minimal_roi` (dakika anahtarlı) `CikisAyarlari.azalan_roi` ile (mum = yukarı yuvarlanmış dakika / TF dakikası; aynı muma
  düşen basamakta büyük dakikalı olan geçerli); "0": 100 (etkisiz) tablolar yazılmadı. Hedef kapanışta sınanır, çıkış sonraki açılışta.
- `trailing_stop_positive/offset` -> `geri_cekilme_yuzde` / `geri_cekilme_min_kar_yuzde` (only_offset=True ise offset = min kâr,
  False ise min kâr 0). Kapanış bazlıdır (kaynakta fiyat ve mum içi).
- `sell_profit_only` (+offset) -> `yalniz_karda_cikis` (+`yalniz_karda_min_kar_yuzde`).
- `custom_stoploss` (ATR izi: 788, 805) -> strateji kancası `pozisyon_cikisi` (kapanış bazlı, yalnız lehine taşınan seviye).
- Freqtrade durum koşulları (her mumda doğru olan) durum olarak yazıldı: açık pozisyon varken yeni giriş motorda zaten yok.
- `ta.momentum.stochrsi` (0-1) kaynakta yumuşatmasız ham StochRSI'dir (smooth1/smooth2 yalnız %K/%D içindir): ham alındı.
- Kaynaktaki TA-Lib/pandas_ta göstergeleri motorun göstergeleriyle yazıldı (Wilder RSI/ATR/ADX, SMA tohumlu EMA farkları ihmal edilir).

KODLANAMADI satırları dosya sonundaki listededir (neden satır başına yazılı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import mama_fama as _mama_fama
from motor.strateji._gosterge_d11j import obv as _obv
from motor.strateji._gosterge_d11j import trix as _trix
from motor.strateji._gosterge_d11j import williams_r as _williams_r
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d5 import kama as _kama
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, kapanis_iz_ihlali
from motor.strateji.kapanis.kod_g8_modul import roi_tablosu as _roi
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _bitir(sonuc: pd.DataFrame, cikis_long=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _long(m: pd.DataFrame, al, stop) -> pd.DataFrame:
    """Yalnız long çerçevesi; `stop` long stop fiyatı (Series)."""
    kap = m["kapanis"]
    return cerceve(m, al, False, stop, kap * 2.0 - stop)


def _yuzde_stop(m: pd.DataFrame, sl: float) -> pd.Series:
    """Kaynak yüzde stopu (sl pozitif oran, örn. 0.2) sinyal kapanışından."""
    return m["kapanis"] * (1.0 - float(sl))


def _stoch_rsi_ham(kap: pd.Series, n: int = 14) -> pd.Series:
    """Ham StochRSI (0-1): RSI(n)'in son n RSI değerindeki konumu."""
    r = g.rsi(kap, n)
    alt, ust = r.rolling(n, min_periods=n).min(), r.rolling(n, min_periods=n).max()
    return (r - alt) / (ust - alt).where(lambda x: x > 0)


def _stoch_yavas(m: pd.DataFrame, fastk: int, slowk: int, slowd: int):
    """TA-Lib STOCH: slowk = SMA(fastk, slowk), slowd = SMA(slowk, slowd). Döner (fastk, slowk, slowd)."""
    st = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], fastk, slowk)
    return st["k"], st["d"], g.sma(st["d"], slowd)


def _tema(seri: pd.Series, n: int) -> pd.Series:
    e1 = g.ema(seri, n)
    e2 = g.ema(e1, n)
    e3 = g.ema(e2, n)
    return 3.0 * e1 - 3.0 * e2 + e3


def _cti(seri: pd.Series, n: int) -> pd.Series:
    """Korelasyon Trend Göstergesi: son n kapanışın zaman sırasıyla Pearson korelasyonu (-1..1)."""
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xm = x - x.mean()
        w = sliding_window_view(a, n)
        wm = w - w.mean(axis=1, keepdims=True)
        payda = np.sqrt((wm ** 2).sum(axis=1)) * np.sqrt((xm ** 2).sum())
        with np.errstate(invalid="ignore", divide="ignore"):
            out[n - 1:] = np.where(payda > 0, (wm @ xm) / payda, np.nan)
    return pd.Series(out, index=seri.index)


def _dip_serisi(x: pd.Series) -> pd.Series:
    """x[t-1] yerel dipse (x[t-1] <= x[t-2] ve x[t] >= x[t-1]) o t'de dip değeri = x[t-1]; sonra ileri doldurulur."""
    onceki = x.shift(1)
    return onceki.where((onceki <= x.shift(2)) & (x >= onceki)).ffill()


def _boga_diverjans(kap: pd.Series, osc: pd.Series, en_fazla: int = 14) -> pd.Series:
    """Geriye bakan boğa diverjansı: i = 2..en_fazla için fiyat dibi i dip önceki değerden düşük, osc dibi daha yüksek,
    fiyat dibi bir önceki dipten büyük değil ve arada kalan dipler i dip önceki değere eşit/üstünde."""
    ob, rb = _dip_serisi(kap), _dip_serisi(osc)
    sonuc = pd.Series(False, index=kap.index)
    for i in range(2, en_fazla + 1):
        arada = pd.Series(True, index=kap.index)
        for ii in range(1, i):
            arada &= ob.shift(i).le(ob.shift(ii))
        sonuc |= ob.lt(ob.shift(i)) & rb.gt(rb.shift(i)) & ob.le(ob.shift(1)) & arada
    return sonuc


# ================================================================ B001:744
class HacimSma9YonB0744(Strateji):
    """HAM:B001:744 (5m, long; kaynak pivot-supertrend/A9AV.py): hacim > SMA9(hacim) VE önceki kapanış < kapanış -> long.
    Çıkış: hacim > SMA9(hacim) VE önceki kapanış > kapanış VE son 2 mumda (bu mum dahil) giriş sinyali yok. Stop -%20.
    Uyarlama: kaynakta alış sinyali önce hesaplandığı için 'son 2 barda sat sinyali yok' girişte HER ZAMAN doğrudur (filtre
    etkisiz): girişe filtre konmadı; çıkıştaki 'son 2 barda alış sinyali yok' filtresi etkindir ve uygulandı."""

    ad, stil = "kapanis__hacim-sma9-yon-b0744", "daytrade"
    varsayilan_parametreler = {"length": 9, "opposing_signal_filter": 2, "sl": 0.20}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hacim = mumlar["hacim"]
        patlama = hacim > hacim.rolling(int(p["length"]), min_periods=int(p["length"])).mean()
        al = patlama & (kap.shift(1) < kap)
        karsi = al.astype(float).rolling(int(p["opposing_signal_filter"]), min_periods=1).max() > 0
        cik = patlama & (kap.shift(1) > kap) & ~karsi
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:754
class UcSupertrendStochRsiB0754(Strateji):
    """HAM:B001:754 (1h, long; kaynak pivot-supertrend/SupertrendStrategy.py): üç Supertrend (ATR periyodu/çarpan 20/3, 20/4,
    40/8) yön toplamı >= 1 VE ham StochRSI(14) < 0,8 VE kapanış > EMA(90) VE hacim > 0 -> long. Çıkış: yön toplamı < 1 VE StochRSI > 0,2.
    ROI {0:100} etkisiz (yazılmadı); kaynak stopu -%99 -> ATR(14)x3 felaket stopu uyarlaması."""

    ad, stil = "kapanis__3st-stochrsi-ema90-b0754", "swing"
    varsayilan_parametreler = {"st": ((20, 3.0), (20, 4.0), (40, 8.0)), "ema_n": 90, "stoch_n": 14,
                               "buy_stoch_rsi": 0.8, "sell_stoch_rsi": 0.2, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        toplam = sum(g.supertrend(mumlar["yuksek"], mumlar["dusuk"], kap, int(per), float(car))["yon"]
                     for per, car in p["st"])
        sr = _stoch_rsi_ham(kap, int(p["stoch_n"]))
        al = (toplam >= 1) & (sr < float(p["buy_stoch_rsi"])) & (kap > g.ema(kap, int(p["ema_n"]))) & (mumlar["hacim"] > 0)
        cik = (toplam < 1) & (sr > float(p["sell_stoch_rsi"])) & (mumlar["hacim"] > 0)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(_long(mumlar, al, kap - mes), cik)


# ================================================================ B001:758
class AdxDiKesisimB0758(Strateji):
    """HAM:B001:758 (15m, long; kaynak rsi-momentum/ADX_15M_USDT.py): ADX(14) > 16 VE -DI(25) > 4 VE +DI(25) > 20 VE +DI, -DI'yı
    yukarı keser -> long. Çıkış: ADX(14) > 43 VE -DI > 22 VE +DI > 20 VE -DI, +DI'yı yukarı keser. ROI {0dk %26,552; 30 %10,255;
    210 %3,545; 540 0}; stop -%12,55."""

    ad, stil = "kapanis__adx-di-kesisim-b0758", "daytrade"
    varsayilan_parametreler = {"adx_n": 14, "di_n": 25, "adx_al": 16.0, "eksi_di_al": 4.0, "arti_di_al": 20.0,
                               "adx_sat": 43.0, "eksi_di_sat": 22.0, "arti_di_sat": 20.0, "sl": 0.1255}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.26552, 30: 0.10255, 210: 0.03545, 540: 0.0}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, l, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        adx = g.adx(h, l, kap, int(p["adx_n"]))["adx"]
        di = g.adx(h, l, kap, int(p["di_n"]))
        arti, eksi = di["arti_di"], di["eksi_di"]
        al = ((adx > float(p["adx_al"])) & (eksi > float(p["eksi_di_al"])) & (arti > float(p["arti_di_al"]))
              & yukari(arti, eksi))
        cik = ((adx > float(p["adx_sat"])) & (eksi > float(p["eksi_di_sat"])) & (arti > float(p["arti_di_sat"]))
               & yukari(eksi, arti))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:759
class EksiDiKesisimB0759(Strateji):
    """HAM:B001:759 (15m, long; kaynak rsi-momentum/ADX_15M_USDT2.py): -DI(25), +DI(25)'i yukarı keser -> long (ters yön, kaynakta
    böyle). Çıkış: ADX(14) > 91 VE -DI > 91 VE +DI, -DI'yı yukarı keser (pratikte nadir). ROI {0dk %10,313; 102 %7,627; 275 %4,228;
    588 0}; stop -%31,941."""

    ad, stil = "kapanis__eksi-di-kesisim-b0759", "daytrade"
    varsayilan_parametreler = {"adx_n": 14, "di_n": 25, "adx_sat": 91.0, "eksi_di_sat": 91.0, "sl": 0.31941}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.10313, 102: 0.07627, 275: 0.04228, 588: 0.0}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, l, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        adx = g.adx(h, l, kap, int(p["adx_n"]))["adx"]
        di = g.adx(h, l, kap, int(p["di_n"]))
        arti, eksi = di["arti_di"], di["eksi_di"]
        cik = (adx > float(p["adx_sat"])) & (eksi > float(p["eksi_di_sat"])) & yukari(arti, eksi)
        return _bitir(_long(mumlar, yukari(eksi, arti), _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:762
class AwesomeMacdB0762(Strateji):
    """HAM:B001:762 (1h, long; kaynak rsi-momentum/AwesomeMacd.py): MACD(12,26,5) çizgisi > sinyal VE Awesome Oscillator (HL2,
    SMA5-SMA34) önceki muma göre yükseliyor -> long (durum). Çıkış: MACD < sinyal VE AO düşüyor. ROI {0:%80}; stop -%1,6."""

    ad, stil = "kapanis__awesome-macd-b0762", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 5, "ao_hizli": 5, "ao_yavas": 34, "sl": 0.016}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.8}, 60))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        mc = g.macd(mumlar["kapanis"], int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        med = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        ao = g.sma(med, int(p["ao_hizli"])) - g.sma(med, int(p["ao_yavas"]))
        al = (mc["macd"] > mc["sinyal"]) & (ao > ao.shift(1))
        cik = (mc["macd"] < mc["sinyal"]) & (ao < ao.shift(1))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:768
class CrossEmaStochRsiB0768(Strateji):
    """HAM:B001:768 (1h, long; kaynak rsi-momentum/CrossEMAStrategy.py): EMA(28) > EMA(48) VE ham StochRSI(14) < 0,8 VE hacim > 0 ->
    long (durum). Çıkış: EMA(28) < EMA(48) VE StochRSI > 0,2. ROI {0:100} etkisiz; kaynak stopu -%99 -> ATR(14)x3 felaket stopu."""

    ad, stil = "kapanis__ema2848-stochrsi-b0768", "swing"
    varsayilan_parametreler = {"ema_a": 28, "ema_b": 48, "stoch_n": 14, "buy_stoch_rsi": 0.8, "sell_stoch_rsi": 0.2,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ea, eb = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        sr = _stoch_rsi_ham(kap, int(p["stoch_n"]))
        al = (ea > eb) & (sr < float(p["buy_stoch_rsi"])) & (mumlar["hacim"] > 0)
        cik = (ea < eb) & (sr > float(p["sell_stoch_rsi"])) & (mumlar["hacim"] > 0)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(_long(mumlar, al, kap - mes), cik)


# ================================================================ B001:770
class RsiDiverjansB0770(Strateji):
    """HAM:B001:770 (5m, long; kaynak rsi-momentum/DIV_v1.py): boğa RSI diverjansı (dosyadaki divergence() mantığı: kapanış ve
    RSI(14) için yerel dip = [t-1] <= [t-2] VE [t] >= [t-1], dip değerleri ileri doldurulur; i = 2..14 için fiyat dibi i önceki
    dipten düşük, RSI dibi daha yüksek, fiyat dibi bir önceki dipten büyük değil ve arada kalan dipler >= i önceki) VE RSI14 < 30
    -> long. Çıkış sinyali yok. ROI {0dk %10,348; 3 %5,05; 5 %3,351; 61 %2,752; 292 %0,519; 399 0}; stop -%15; iz süren %0,1
    (offset %2, only_offset=True -> min kâr %2). Tüm kaynak koşulları yalnız geçmişe bakar (shift(i))."""

    ad, stil = "kapanis__rsi-diverjans-b0770", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_esik": 30.0, "en_fazla": 14, "sl": 0.15}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.10347601757573865, 3: 0.050495605759981035, 5: 0.03350898081823659,
                         61: 0.0275218557571848, 292: 0.005185372158403069, 399: 0.0}, 5),
        geri_cekilme_yuzde=0.1, geri_cekilme_min_kar_yuzde=2.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        al = _boga_diverjans(kap, r, int(p["en_fazla"])) & (r < float(p["rsi_esik"])) & (mumlar["hacim"] > 0)
        return _long(mumlar, al, _yuzde_stop(mumlar, p["sl"]))


# ================================================================ B001:772
class EmaYiginUst1hB0772(Strateji):
    """HAM:B001:772 (5m, long; kaynak rsi-momentum/ForexSignal.py): 1h EMA8 > 1h EMA21 (kapanmış 1h mumlardan, htf.ust_zaman) VE
    EMA8 > EMA13 > EMA21 (5m) VE düşük < EMA8 -> long (durum). Çıkış: EMA8 < önceki EMA8 (eğim aşağı) VEYA ROI {0dk %4; 30 %3; 60 %1};
    stop -%3."""

    ad, stil = "kapanis__ema-yigin-ust1h-b0772", "daytrade"
    varsayilan_parametreler = {"ema_a": 8, "ema_b": 13, "ema_c": 21, "ust_tf": "1h", "sl": 0.03}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.03, 60: 0.01}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        a, b, c = int(p["ema_a"]), int(p["ema_b"]), int(p["ema_c"])
        ust = ust_zaman(mumlar, str(p["ust_tf"]), lambda u: pd.DataFrame({"a": g.ema(u["kapanis"], a),
                                                                          "c": g.ema(u["kapanis"], c)}))
        ea, eb, ec = g.ema(kap, a), g.ema(kap, b), g.ema(kap, c)
        al = (ust["a"] > ust["c"]) & (ea > eb) & (eb > ec) & (mumlar["dusuk"] < ea)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), ea < ea.shift(1))


# ================================================================ B001:773
class RsiStochUstBolgeB0773(Strateji):
    """HAM:B001:773 (15m, long; kaynak rsi-momentum/FrostAuraM21hStrategy.py): RSI(14) > 48 VE Stoch(5,3,3) slowd > 79 VE slowk > 77 VE
    kapanış > 1,5e-6 -> long (durum). Çıkış: RSI < 48 VE slowd < 79 VE slowk < 77. ROI {0dk %32,365; 359 %12,673; 934 %8,834;
    2090 0}; stop -%44,897."""

    ad, stil = "kapanis__rsi-stoch-ust-b0773", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_esik": 48.0, "stok_k": 5, "stok_yk": 3, "stok_yd": 3,
                               "slowd_esik": 79.0, "slowk_esik": 77.0, "min_fiyat": 1.5e-6, "sl": 0.44897}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.32365, 359: 0.12673, 934: 0.08834, 2090: 0.0}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        _, slowk, slowd = _stoch_yavas(mumlar, int(p["stok_k"]), int(p["stok_yk"]), int(p["stok_yd"]))
        al = ((r > float(p["rsi_esik"])) & (slowd > float(p["slowd_esik"])) & (slowk > float(p["slowk_esik"]))
              & (kap > float(p["min_fiyat"])))
        cik = (r < float(p["rsi_esik"])) & (slowd < float(p["slowd_esik"])) & (slowk < float(p["slowk_esik"]))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:775
class KamaCciB0775(Strateji):
    """HAM:B001:775 (5m, long; kaynak rsi-momentum/KAMACCIRSI.py, buy_params/sell_params sabit): CCI(18) > 198 VE KAMA(11) > KAMA(46) VE
    hacim > 0 -> long (RSI koşulu kapalı). Çıkış: KAMA(5) < KAMA(41) VE hacim > 0 (CCI/RSI çıkışı kapalı), yalnız kârda (sell_profit_only,
    offset %1). ROI {0dk %11,599; 18 %3,112; 34 %1,895; 131 0}; stop -%32,982; iz süren %28,596 (offset %29,771, only_offset=True)."""

    ad, stil = "kapanis__kama-cci-b0775", "daytrade"
    varsayilan_parametreler = {"cci_n": 18, "cci_esik": 198.0, "kama_kisa": 11, "kama_uzun": 46,
                               "sat_kama_kisa": 5, "sat_kama_uzun": 41, "sl": 0.32982}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.11599, 18: 0.03112, 34: 0.01895, 131: 0.0}, 5),
        geri_cekilme_yuzde=28.596, geri_cekilme_min_kar_yuzde=29.771,
        yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=1.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        cci = b2.cci(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["cci_n"]))
        al = ((cci > float(p["cci_esik"])) & (_kama(kap, int(p["kama_kisa"])) > _kama(kap, int(p["kama_uzun"])))
              & (mumlar["hacim"] > 0))
        cik = (_kama(kap, int(p["sat_kama_kisa"])) < _kama(kap, int(p["sat_kama_uzun"]))) & (mumlar["hacim"] > 0)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:777
class MacdCciB0777(Strateji):
    """HAM:B001:777 (30m, long; kaynak rsi-momentum/MACDCCI.py): MACD(12,26,9) çizgisi > sinyal VE CCI(35) <= -100 -> long (durum).
    Çıkış: MACD < sinyal VE CCI(62) >= 200. ROI {0:100} etkisiz, trailing kapalı; stop -%30."""

    ad, stil = "kapanis__macd-cci-3562-b0777", "daytrade"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "cci_al_n": 35, "cci_al": -100.0,
                               "cci_sat_n": 62, "cci_sat": 200.0, "sl": 0.30}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, l, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        al = (mc["macd"] > mc["sinyal"]) & (b2.cci(h, l, kap, int(p["cci_al_n"])) <= float(p["cci_al"])) & (mumlar["hacim"] > 0)
        cik = (mc["macd"] < mc["sinyal"]) & (b2.cci(h, l, kap, int(p["cci_sat_n"])) >= float(p["cci_sat"])) & (mumlar["hacim"] > 0)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:798
class MacdCciB0798(MacdCciB0777):
    """HAM:B001:798 (30m, long; kaynak rsi-momentum/SwingHigh.py): 777 ile aynı yapı, derin eşikler: MACD(12,26,9) > sinyal VE CCI(13) <=
    -188 -> long; çıkış MACD < sinyal VE CCI(76) >= 231. ROI {0dk %16,035; 23 %3,218; 54 %1,182; 173 0}; stop -%22,274; iz süren %8
    (offset %10, only_offset=True -> min kâr %10)."""

    ad = "kapanis__macd-cci-1376-b0798"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "cci_al_n": 13, "cci_al": -188.0,
                               "cci_sat_n": 76, "cci_sat": 231.0, "sl": 0.22274}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.16035, 23: 0.03218, 54: 0.01182, 173: 0.0}, 30),
        geri_cekilme_yuzde=8.0, geri_cekilme_min_kar_yuzde=10.0)


# ================================================================ B001:778
class MacdSifirAltiEma100B0778(Strateji):
    """HAM:B001:778 (1h, long; kaynak rsi-momentum/MACDCrossoverWithTrend.py): MACD(12,26,9) < 0 VE MACD sinyali yukarı keser VE düşük >
    EMA(100) VE hacim > 0 -> long. Çıkış: MACD sıfırı aşağı keser VEYA düşük < EMA(100). Stop -%20; ROI yok; trailing kapalı."""

    ad, stil = "kapanis__macd-sifir-alti-ema100-b0778", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "ema_n": 100, "sl": 0.20}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        mc = g.macd(mumlar["kapanis"], int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        ema = g.ema(mumlar["kapanis"], int(p["ema_n"]))
        al = (mc["macd"] < 0) & yukari(mc["macd"], mc["sinyal"]) & (mumlar["dusuk"] > ema) & (mumlar["hacim"] > 0)
        cik = asagi(mc["macd"], 0.0) | (mumlar["dusuk"] < ema)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:782
class MacdEma200B0782(Strateji):
    """HAM:B001:782 (5m, long; kaynak rsi-momentum/MACD_EMA.py): MACD(12,26,9) sinyali yukarı keser VE kapanış > EMA(200) -> long.
    Çıkış: MACD sinyali aşağı keser VE kapanış < EMA(200) VEYA ROI {0dk %5; 20 %4; 30 %3; 60 %1}; stop -%25."""

    ad, stil = "kapanis__macd-ema200-b0782", "daytrade"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "ema_n": 200, "sl": 0.25}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 20: 0.04, 30: 0.03, 60: 0.01}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        ema = g.ema(kap, int(p["ema_n"]))
        al = yukari(mc["macd"], mc["sinyal"]) & (kap > ema)
        cik = asagi(mc["macd"], mc["sinyal"]) & (kap < ema)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:783
class MacdUcSmaB0783(Strateji):
    """HAM:B001:783 (5m, long; kaynak rsi-momentum/MACD_TRIPLE_MA.py): MACD sinyali yukarı keser VE SMA6, SMA14'ü yukarı keser VE SMA26 >
    SMA6 -> long (aynı mumda). Çıkış: MACD sinyali aşağı keser VE SMA6, SMA14'ü aşağı keser VE SMA26 < SMA6 VE SMA26 < SMA14 VEYA ROI
    {0dk %15,825; 28 %8,491; 45 %4; 88 %1,94; 120 0}; stop -%3; iz süren %14,55 (offset %15,434, only_offset=True)."""

    ad, stil = "kapanis__macd-uc-sma-b0783", "daytrade"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "sma_a": 6, "sma_b": 14, "sma_c": 26, "sl": 0.03}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.15825, 28: 0.08491, 45: 0.04, 88: 0.0194, 120: 0.0}, 5),
        geri_cekilme_yuzde=14.55, geri_cekilme_min_kar_yuzde=15.434)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        sa, sb, sc = (g.sma(kap, int(p[k])) for k in ("sma_a", "sma_b", "sma_c"))
        al = yukari(mc["macd"], mc["sinyal"]) & yukari(sa, sb) & (sc > sa)
        cik = asagi(mc["macd"], mc["sinyal"]) & asagi(sa, sb) & (sc < sa) & (sc < sb)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:784
class MacdTemaB0784(Strateji):
    """HAM:B001:784 (5m, long; kaynak rsi-momentum/MACD_TRI_EMA.py): MACD sinyali yukarı keser VE önceki kapanış > önceki TEMA(13) -> long.
    Çıkış: MACD sinyal çizgisi MACD'yi yukarı keser (yani MACD sinyalin altına kesişir) VEYA ROI {10dk %15; 15 %6; 30 %4; 120 %0}
    (ROI tablosunda '0' anahtarı yok: ilk 2 mumda ROI yok); stop -%3."""

    ad, stil = "kapanis__macd-tema13-b0784", "daytrade"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "tema_n": 13, "sl": 0.03}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({10: 0.15, 15: 0.06, 30: 0.04, 120: 0.0}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        tema = _tema(kap, int(p["tema_n"]))
        al = yukari(mc["macd"], mc["sinyal"]) & (kap.shift(1) > tema.shift(1))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), yukari(mc["sinyal"], mc["macd"]))


# ================================================================ B001:786
class GunlukMacdHistB0786(Strateji):
    """HAM:B001:786 (1h, long; kaynak rsi-momentum/Macd.py): günlük MACD(12,26,9) histogramı > 0 (son KAPANMIŞ günlük mum, htf.ust_zaman) ->
    long (durum); histogram < 0 olunca çık. Stop -%10; ROI yok. custom_stoploss: kâr > %30 ise stop = kâr - %1 (iz süren): zirve kâr >=
    %30 iken zirveden kâr farkı >= 1 puan olunca çıkış (geri_cekilme_yuzde=1, min kâr 30). Not: Freqtrade gerçeğinde dönüş değeri
    abs() ile uygulandığından kaynak kod daha gevşek davranır; kuralın yazılı niyeti (kâr - %1 izi) uygulandı."""

    ad, stil = "kapanis__gunluk-macd-hist-b0786", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "ust_tf": "1d", "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=30.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, y, sg = int(p["hizli"]), int(p["yavas"]), int(p["sinyal"])
        hist = ust_zaman(mumlar, str(p["ust_tf"]), lambda u: g.macd(u["kapanis"], h, y, sg)["histogram"])
        return _bitir(_long(mumlar, hist > 0, _yuzde_stop(mumlar, p["sl"])), hist < 0)


# ================================================================ B001:787
class MacdHistDipSdB0787(Strateji):
    """HAM:B001:787 (5m, long; kaynak rsi-momentum/Maro4hMacdSd.py): hist% = 100 x MACD histogramı(12,26,9) / kapanış < 0 VE hist%[t-2] >
    hist%[t-1] VE hist% > hist%[t-2] (dip dönüşü) VE STDDEV(kapanış,28) > SMA28(STDDEV) -> long. Çıkış: hist% > 0 VE hist%[t-2] <
    hist%[t-1] VE hist% < hist%[t-2] VE STDDEV(28) < SMA28(STDDEV). ROI {0dk %24,627; 24 %6,484; 38 %2,921; 145 0}; stop -%21,611.
    STDDEV popülasyon sapması (TA-Lib)."""

    ad, stil = "kapanis__macd-hist-dip-sd-b0787", "daytrade"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "sd_n": 28, "sd_ort_n": 28, "sl": 0.21611}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.24627, 24: 0.06484, 38: 0.02921, 145: 0.0}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hp = 100.0 * g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))["histogram"] / kap
        sd = kap.rolling(int(p["sd_n"]), min_periods=int(p["sd_n"])).std(ddof=0)
        sd_ort = g.sma(sd, int(p["sd_ort_n"]))
        al = (hp < 0) & (hp.shift(2) > hp.shift(1)) & (hp > hp.shift(2)) & (sd > sd_ort)
        cik = (hp > 0) & (hp.shift(2) < hp.shift(1)) & (hp < hp.shift(2)) & (sd < sd_ort)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:788
class MacdEma80AtrIzB0788(KancaDestek, Strateji):
    """HAM:B001:788 (4h, long; kaynak rsi-momentum/Momentumv2.py, buy_params/sell_params sabit): MACD(12,26,9) sinyali yukarı keser VE kapanış >
    EMA(80) VE hacim > 0 -> long. Çıkış: (MACD sinyali aşağı keser VEYA RSI(14) 90'ı aşağı keser) VE hacim > 0. custom_stoploss: her mumda
    kapanış - 2,6 x ATR(12) (iz süren, yalnız yukarı taşınır, fiyatın altındaysa) = KAPANIŞ BAZLI kanca (kapanis_iz_ihlali; sinyal mumundan
    beri en büyük seviye). Stop -%8 (motor); ROI {0dk %22; 1260 %17; 1944 %9; 7200 0}. CooldownPeriod korumasu (6 mum) motorda yok, yazılmadı."""

    ad, stil = "kapanis__macd-ema80-atr-iz-b0788", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "buy_ema": 80, "rsi_n": 14, "sell_rsi": 90.0,
                               "atr_timeperiod": 12, "atr_multiplier": 2.6, "sl": 0.08}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.22, 1260: 0.17, 1944: 0.09, 7200: 0.0}, 240))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        r = g.rsi(kap, int(p["rsi_n"]))
        al = yukari(mc["macd"], mc["sinyal"]) & (kap > g.ema(kap, int(p["buy_ema"]))) & (mumlar["hacim"] > 0)
        cik = (asagi(mc["macd"], mc["sinyal"]) | asagi(r, float(p["sell_rsi"]))) & (mumlar["hacim"] > 0)
        self._sakla(kap=kap, atr=g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_timeperiod"])))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, d.mum_indeksi,
                                 float(self.parametreler["atr_multiplier"]), 1, False)


# ================================================================ B001:794
class Rsi10Ema600B0794(Strateji):
    """HAM:B001:794 (1h, long; kaynak rsi-momentum/RSIDirectionalWithTrendSlow.py): RSI(10) 25'i yukarı keser VE düşük > EMA(600) VE hacim > 0 ->
    long. Çıkış: RSI(10) 20'yi aşağı keser VEYA düşük < EMA(600). Stop -%20; trailing_stop açık (pozitif/offset yok: zirveden %20 iz) ->
    geri_cekilme_yuzde=20 (kâr puanı farkı, min kâr 0)."""

    ad, stil = "kapanis__rsi10-ema600-b0794", "swing"
    varsayilan_parametreler = {"rsi_n": 10, "rsi_al": 25.0, "rsi_sat": 20.0, "ema_n": 600, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=20.0, geri_cekilme_min_kar_yuzde=0.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        r = g.rsi(mumlar["kapanis"], int(p["rsi_n"]))
        ema = g.ema(mumlar["kapanis"], int(p["ema_n"]))
        al = yukari(r, float(p["rsi_al"])) & (mumlar["dusuk"] > ema) & (mumlar["hacim"] > 0)
        cik = asagi(r, float(p["rsi_sat"])) | (mumlar["dusuk"] < ema)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:795
class RsiWillrCiftTeyitB0795(Strateji):
    """HAM:B001:795 (15m, long; kaynak rsi-momentum/RSIv2.py): RSI(14) < 30 VE Williams %R(14) < -80, hem bu mumda hem önceki mumda -> long.
    Çıkış: 30m bilgi TF (htf.ust_zaman; kapanmış 30m mum) RSI(14) > 70 VE %R(14) > -20, bu 15m satırında ve bir önceki 15m satırında (kaynakta
    shift(1) birleştirilmiş 15m çerçevesinde). ROI {0:%1}; kaynak stopu -%99 -> ATR(14)x3 felaket stopu uyarlaması (kaynaktaki kullanılmayan
    custom_stop özniteliği yok sayıldı)."""

    ad, stil = "kapanis__rsi-willr-cift-b0795", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "willr_n": 14, "rsi_al": 30.0, "willr_al": -80.0, "rsi_sat": 70.0,
                               "willr_sat": -20.0, "ust_tf": "30m", "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.01}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, l, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        rn, wn = int(p["rsi_n"]), int(p["willr_n"])
        kosul = (g.rsi(kap, rn) < float(p["rsi_al"])) & (_williams_r(h, l, kap, wn) < float(p["willr_al"]))
        al = kosul & kosul.shift(1, fill_value=False)
        ust = ust_zaman(mumlar, str(p["ust_tf"]), lambda u: pd.DataFrame({
            "rsi": g.rsi(u["kapanis"], rn), "wr": _williams_r(u["yuksek"], u["dusuk"], u["kapanis"], wn)}))
        k2 = (ust["rsi"] > float(p["rsi_sat"])) & (ust["wr"] > float(p["willr_sat"]))
        cik = k2 & k2.shift(1, fill_value=False)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(_long(mumlar, al, kap - mes), cik)


# ================================================================ B001:797
class StochRsiTemaB0797(Strateji):
    """HAM:B001:797 (5m, long; kaynak rsi-momentum/StochRSITEMA.py, buy_params/sell_params sabit): RSI(15) > 36 VE Stoch slowd 48'i yukarı keser VE
    slowk 48'i yukarı keser VE slowk, slowd'yi yukarı keser (STOCH fastk 14, slowk 3, slowd 3) VE hacim > 0 -> long. Çıkış: kapanış < TEMA(5)
    VE hacim > 0, yalnız kârda (sell_profit_only, offset %1) VEYA ROI {0dk %19,503; 13 %9,149; 36 %2,891; 64 0}; stop -%2,205; iz süren
    %17,251 (offset %25,16, only_offset=False -> min kâr 0)."""

    ad, stil = "kapanis__stochrsi-tema-b0797", "daytrade"
    varsayilan_parametreler = {"rsi_n": 15, "rsi_alt": 36.0, "stok_alt": 48.0, "fastk": 14, "slowk": 3, "slowd": 3,
                               "tema_n": 5, "sl": 0.02205}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.19503, 13: 0.09149, 36: 0.02891, 64: 0.0}, 5),
        geri_cekilme_yuzde=17.251, geri_cekilme_min_kar_yuzde=0.0,
        yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=1.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        _, slowk, slowd = _stoch_yavas(mumlar, int(p["fastk"]), int(p["slowk"]), int(p["slowd"]))
        esik = float(p["stok_alt"])
        al = ((g.rsi(kap, int(p["rsi_n"])) > float(p["rsi_alt"])) & yukari(slowd, esik) & yukari(slowk, esik)
              & yukari(slowk, slowd) & (mumlar["hacim"] > 0))
        cik = (kap < _tema(kap, int(p["tema_n"]))) & (mumlar["hacim"] > 0)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:800
class TheForceB0800(Strateji):
    """HAM:B001:800 (15m, long; kaynak rsi-momentum/TheForce.py): hızlı Stoch(5,3,3) fastk ve fastd 20-80 aralığında VE MACD(12,26,1) çizgisi ve
    sinyali bir önceki mumdan yüksek VE kapanış > önceki kapanış VE EMA5(kapanış) >= EMA5(açılış) -> long (durum). Çıkış: fastk <= 80 VE
    fastd <= 80 VE MACD ve sinyal bir önceki mumdan düşük VE EMA5(kapanış) < EMA5(açılış) VEYA ROI {0dk %1,2; 15 %1; 30 %0,5}; stop -%1,5."""

    ad, stil = "kapanis__theforce-b0800", "daytrade"
    varsayilan_parametreler = {"stok_k": 5, "stok_d": 3, "alt": 20.0, "ust": 80.0, "hizli": 12, "yavas": 26, "sinyal": 1,
                               "ema_n": 5, "sl": 0.015}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.012, 15: 0.01, 30: 0.005}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        st = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["stok_k"]), int(p["stok_d"]))
        fk, fd = st["k"], st["d"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        ec, eo = g.ema(kap, int(p["ema_n"])), g.ema(mumlar["acilis"], int(p["ema_n"]))
        alt, ust = float(p["alt"]), float(p["ust"])
        al = ((fk >= alt) & (fk <= ust) & (fd >= alt) & (fd <= ust)
              & (mc["macd"] > mc["macd"].shift(1)) & (mc["sinyal"] > mc["sinyal"].shift(1))
              & (kap > kap.shift(1)) & (ec >= eo))
        cik = ((fk <= ust) & (fd <= ust) & (mc["macd"] < mc["macd"].shift(1)) & (mc["sinyal"] < mc["sinyal"].shift(1))
               & (ec < eo))
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:801
class EmaObvRsiB0801(Strateji):
    """HAM:B001:801 (5m, long; kaynak rsi-momentum/TrendFollowingStrategy_4.py): kapanış EMA(20)'yi (ewm span 20) yukarı keser VE OBV > önceki OBV VE
    RSI(14) < 30 -> long. Çıkış: kapanış EMA(20)'yi aşağı keser VE OBV > önceki OBV VEYA ROI {0dk %15; 30 %10; 60 %5}; stop -%20; iz
    süren %5 (offset %10, only_offset=False -> min kâr 0). Kaynakta enter_short = -1 yazılıyor (can_short=True) ama Freqtrade yalnız 1'i
    kabul ettiğinden short fiilen hiç açılmaz: yalnız long kodlandı."""

    ad, stil = "kapanis__ema-obv-rsi-b0801", "daytrade"
    varsayilan_parametreler = {"ema_n": 20, "rsi_n": 14, "rsi_esik": 30.0, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.15, 30: 0.10, 60: 0.05}, 5),
                                   geri_cekilme_yuzde=5.0, geri_cekilme_min_kar_yuzde=0.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ema = g.ema(kap, int(p["ema_n"]))
        obv = _obv(kap, mumlar["hacim"])
        artiyor = obv > obv.shift(1)
        al = yukari(kap, ema) & artiyor & (g.rsi(kap, int(p["rsi_n"])) < float(p["rsi_esik"]))
        cik = asagi(kap, ema) & artiyor
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:803
class TrixHistStochRsiB0803(Strateji):
    """HAM:B001:803 (1h, long; kaynak rsi-momentum/TrixStrategy.py): TRIX histogramı > 0 (TRIX = üçlü EMA(9) kapanışın yüzde değişimi, sinyal =
    SMA21, histogram = TRIX - sinyal) VE ham StochRSI(14) < 0,8 VE hacim > 0 -> long (durum). Çıkış: histogram < 0 VE StochRSI > 0,2.
    ROI {0:100} etkisiz; kaynak stopu -%99 -> ATR(14)x3 felaket stopu uyarlaması."""

    ad, stil = "kapanis__trix-hist-stochrsi-b0803", "swing"
    varsayilan_parametreler = {"trix_n": 9, "trix_sinyal": 21, "stoch_n": 14, "buy_stoch_rsi": 0.8, "sell_stoch_rsi": 0.2,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tx = _trix(kap, int(p["trix_n"]))
        histo = tx - g.sma(tx, int(p["trix_sinyal"]))
        sr = _stoch_rsi_ham(kap, int(p["stoch_n"]))
        al = (histo > 0) & (sr < float(p["buy_stoch_rsi"])) & (mumlar["hacim"] > 0)
        cik = (histo < 0) & (sr > float(p["sell_stoch_rsi"])) & (mumlar["hacim"] > 0)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(_long(mumlar, al, kap - mes), cik)


# ================================================================ B001:804
class TrixV15B0804(Strateji):
    """HAM:B001:804 (1h, long; kaynak rsi-momentum/TrixV15Strategy.py, buy_params/sell_params sabit): hacim > 0 VE TRIX(yüksek, 10) yüzde değişimi >
    SMA19'u (satış tarafı süzgeci, kaynakta girişe de konmuş) VE ham StochRSI(14) < 0,901 VE kapanış > EMA10(açılış) x 0,85 VE TRIX(düşük, 8) yüzde
    değişimi SMA19'unu yukarı keser (trigger) -> long. Çıkış: StochRSI > 0,183 VE TRIX(yüksek,10) < SMA19'u (trailing), yalnız kârda
    (sell_profit_only). ROI {0dk %55,3; 423 %14,4; 751 %5,9; 1342 0}; stop -%31."""

    ad, stil = "kapanis__trix-v15-b0804", "swing"
    varsayilan_parametreler = {"al_trix_n": 8, "al_sinyal_n": 19, "sat_trix_n": 10, "sat_sinyal_n": 19, "stoch_n": 14,
                               "buy_stoch_rsi": 0.901, "sell_stoch_rsi": 0.183, "ema_n": 10, "ema_carpan": 0.85, "sl": 0.31}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.553, 423: 0.144, 751: 0.059, 1342: 0.0}, 60),
                                   yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def _hesapla(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tb = _trix(mumlar["dusuk"], int(p["al_trix_n"]))
        sb = g.sma(tb, int(p["al_sinyal_n"]))
        ts = _trix(mumlar["yuksek"], int(p["sat_trix_n"]))
        ss = g.sma(ts, int(p["sat_sinyal_n"]))
        sr = _stoch_rsi_ham(kap, int(p["stoch_n"]))
        ema_s = g.ema(mumlar["acilis"], int(p["ema_n"])) * float(p["ema_carpan"])
        return kap, tb, sb, ts, ss, sr, ema_s

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, tb, sb, ts, ss, sr, ema_s = self._hesapla(mumlar)
        al = ((mumlar["hacim"] > 0) & (ts > ss) & (sr < float(p["buy_stoch_rsi"])) & (kap > ema_s) & yukari(tb, sb))
        cik = (mumlar["hacim"] > 0) & (sr > float(p["sell_stoch_rsi"])) & (ts < ss)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)


# ================================================================ B001:805
class TrixV21B0805(KancaDestek, TrixV15B0804):
    """HAM:B001:805 (1h, long; kaynak rsi-momentum/TrixV21Strategy.py, buy_params/sell_params sabit): 804 (TrixV15) girişi VE kapanış > EMA(238) x 0,994
    (koruma) -> long (StochRSI = RSI(14)'ün ham 14 pencere min/max konumu, 804 ile aynı). Çıkış: StochRSI > 0,183 VE TRIX(yüksek,10) < SMA19, yalnız
    kârda. custom_stoploss: her mumda düşük - 4,99 x ATR(30), yalnız yukarı taşınır = KAPANIŞ BAZLI kanca (giriş sinyali mumundan beri en büyük
    seviye; kapanış ona eşit/altındaysa çık). ROI {0dk %55,3; 423 %14,4; 751 %5,9; 1342 %2}; stop -%31."""

    ad, stil = "kapanis__trix-v21-b0805", "swing"
    varsayilan_parametreler = {**TrixV15B0804.varsayilan_parametreler, "koruma_n": 238, "koruma_carpan": 0.994,
                               "atr_n": 30, "atr_k": 4.99}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.553, 423: 0.144, 751: 0.059, 1342: 0.02}, 60),
                                   yalniz_karda_cikis=True)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, tb, sb, ts, ss, sr, ema_s = self._hesapla(mumlar)
        koruma = g.ema(kap, int(p["koruma_n"])) * float(p["koruma_carpan"])
        al = ((mumlar["hacim"] > 0) & (kap > koruma) & (ts > ss) & (sr < float(p["buy_stoch_rsi"])) & (kap > ema_s)
              & yukari(tb, sb))
        cik = (mumlar["hacim"] > 0) & (sr > float(p["sell_stoch_rsi"])) & (ts < ss)
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        self._sakla(kap=kap, seviye=mumlar["dusuk"] - float(p["atr_k"]) * atr)
        return _bitir(_long(mumlar, al, _yuzde_stop(mumlar, p["sl"])), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        sv = self._kd["seviye"][max(d.giris_mum_indeksi - 1, 0):d.mum_indeksi + 1]
        sv = sv[np.isfinite(sv)]
        return bool(len(sv)) and bool(self._kd["kap"][d.mum_indeksi] <= sv.max())


# ================================================================ B001:810
class MamaKamaDususB0810(Strateji):
    """HAM:B001:810 (5m, long; kaynak rsi-momentum/adaptive.py): KAMA(84; kapanış) > FAMA VE FAMA > MAMA x 0,981 VE Williams %R(14) < -61,3 VE (MAMA -
    FAMA)/HL2 < -0,025 VE CTI(20) < -0,715 VE son 48 kapanışın en yükseği >= 1,05 x kapanış VE son 288 kapanışın en yükseği >= 1,125 x kapanış VE
    RSI(84) < 60 VE RSI(112) < 60 -> long; MAMA/FAMA = Ehlers MAMA(HL2, 0,25, 0,025). Çıkış sinyali yok. ROI {0:%2}; stop -%10,9."""

    ad, stil = "kapanis__mama-kama-dusus-b0810", "daytrade"
    varsayilan_parametreler = {"mama_hizli": 0.25, "mama_yavas": 0.025, "kama_n": 84, "mama_carpan": 0.981, "willr_n": 14,
                               "willr_esik": -61.3, "mama_fark": -0.025, "cti_n": 20, "cti_esik": -0.715,
                               "dusus_kisa_n": 48, "dusus_kisa": 1.05, "dusus_uzun_n": 288, "dusus_uzun": 1.125,
                               "rsi_a_n": 84, "rsi_b_n": 112, "rsi_esik": 60.0, "sl": 0.109}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.02}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hl2 = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        mama, fama = _mama_fama(hl2, float(p["mama_hizli"]), float(p["mama_yavas"]))
        kn, un = int(p["dusus_kisa_n"]), int(p["dusus_uzun_n"])
        al = ((_kama(kap, int(p["kama_n"])) > fama) & (fama > mama * float(p["mama_carpan"]))
              & (_williams_r(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["willr_n"])) < float(p["willr_esik"]))
              & (((mama - fama) / hl2) < float(p["mama_fark"]))
              & (_cti(kap, int(p["cti_n"])) < float(p["cti_esik"]))
              & (kap.rolling(kn, min_periods=kn).max() >= kap * float(p["dusus_kisa"]))
              & (kap.rolling(un, min_periods=un).max() >= kap * float(p["dusus_uzun"]))
              & (g.rsi(kap, int(p["rsi_a_n"])) < float(p["rsi_esik"]))
              & (g.rsi(kap, int(p["rsi_b_n"])) < float(p["rsi_esik"])))
        return _long(mumlar, al, _yuzde_stop(mumlar, p["sl"]))


# ================================================================ B001:812
class Ema1350KesisimB0812(Strateji):
    """HAM:B001:812 (30m, long; kaynak rsi-momentum/botbaby.py): EMA(13), EMA(50)'yi yukarı keser -> long. Çıkış: EMA(13) < EMA(50) (durum) VEYA
    ROI {0:%1}; stop -%0,7."""

    ad, stil = "kapanis__ema1350-kesisim-b0812", "daytrade"
    varsayilan_parametreler = {"ema_a": 13, "ema_b": 50, "sl": 0.007}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.01}, 30))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ea, eb = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        return _bitir(_long(mumlar, yukari(ea, eb), _yuzde_stop(mumlar, p["sl"])), ea < eb)


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad, "parametreler": _p(sinif), "tf": tf}


SINIFLAR = [HacimSma9YonB0744, UcSupertrendStochRsiB0754, AdxDiKesisimB0758, EksiDiKesisimB0759, AwesomeMacdB0762,
            CrossEmaStochRsiB0768, RsiDiverjansB0770, EmaYiginUst1hB0772, RsiStochUstBolgeB0773, KamaCciB0775,
            MacdCciB0777, MacdCciB0798, MacdSifirAltiEma100B0778, MacdEma200B0782, MacdUcSmaB0783, MacdTemaB0784,
            GunlukMacdHistB0786, MacdHistDipSdB0787, MacdEma80AtrIzB0788, Rsi10Ema600B0794, RsiWillrCiftTeyitB0795,
            StochRsiTemaB0797, TheForceB0800, EmaObvRsiB0801, TrixHistStochRsiB0803, TrixV15B0804, TrixV21B0805,
            MamaKamaDususB0810, Ema1350KesisimB0812]

VARYANTLAR = [
    _v("HAM:B001:744", 1, HacimSma9YonB0744, "5m"),
    _v("HAM:B001:754", 1, UcSupertrendStochRsiB0754, "1h"),
    _v("HAM:B001:758", 1, AdxDiKesisimB0758, "15m"),
    _v("HAM:B001:759", 1, EksiDiKesisimB0759, "15m"),
    _v("HAM:B001:762", 1, AwesomeMacdB0762, "1h"),
    _v("HAM:B001:768", 1, CrossEmaStochRsiB0768, "1h"),
    _v("HAM:B001:770", 1, RsiDiverjansB0770, "5m"),
    _v("HAM:B001:772", 1, EmaYiginUst1hB0772, "5m"),
    _v("HAM:B001:773", 1, RsiStochUstBolgeB0773, "15m"),
    _v("HAM:B001:775", 1, KamaCciB0775, "5m"),
    _v("HAM:B001:777", 1, MacdCciB0777, "30m"),
    _v("HAM:B001:778", 1, MacdSifirAltiEma100B0778, "1h"),
    _v("HAM:B001:782", 1, MacdEma200B0782, "5m"),
    _v("HAM:B001:783", 1, MacdUcSmaB0783, "5m"),
    _v("HAM:B001:784", 1, MacdTemaB0784, "5m"),
    _v("HAM:B001:786", 1, GunlukMacdHistB0786, "1h"),
    _v("HAM:B001:787", 1, MacdHistDipSdB0787, "5m"),
    _v("HAM:B001:788", 1, MacdEma80AtrIzB0788, "4h"),
    _v("HAM:B001:794", 1, Rsi10Ema600B0794, "1h"),
    _v("HAM:B001:795", 1, RsiWillrCiftTeyitB0795, "15m"),
    _v("HAM:B001:797", 1, StochRsiTemaB0797, "5m"),
    _v("HAM:B001:798", 1, MacdCciB0798, "30m"),
    _v("HAM:B001:800", 1, TheForceB0800, "15m"),
    _v("HAM:B001:801", 1, EmaObvRsiB0801, "5m"),
    _v("HAM:B001:803", 1, TrixHistStochRsiB0803, "1h"),
    _v("HAM:B001:804", 1, TrixV15B0804, "1h"),
    _v("HAM:B001:805", 1, TrixV21B0805, "1h"),
    _v("HAM:B001:810", 1, MamaKamaDususB0810, "5m"),
    _v("HAM:B001:812", 1, Ema1350KesisimB0812, "30m"),
]

KODLANAMADI = [
    {"kimlik": "HAM:B001:806",
     "neden": "Giriş koşulu BTC/USDT 1h kapanışı > EMA(184; BTC 1h) x 0,996 (@informative BTC bilgi paritesi): strateji arayüzü yalnız "
              "işlem gören sembolün mumlarını alır, motorda çapraz-sembol (BTC) referans serisi yok; BTC süzgeci olmadan kodlamak "
              "farklı bir strateji olurdu (uydurma çözüm yok)"},
]
