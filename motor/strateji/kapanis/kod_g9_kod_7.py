"""Kapanış turu, kodlama partisi g9_kod_7 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_7.csv, 13 kaynak satırı, HAM:B001).

Her sınıf, kaynak Freqtrade dosyasının (RoboticAutomations/freqtradestrategies) okunmasından kendi cümleleriyle yazılmış bir
uyarlamadır; üçüncü taraf kodu kopyalanmadı, kaynak dosyalar çalıştırılmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan
(motor). Hepsi nedensel (gelecek verisi yok); üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış - 3 x ATR(14) (ön kayıt uyarlaması): 813, 865, 870, 894.
  Diğerlerinde kaynak yüzde stopu sinyal kapanışından hesaplanır (dolum sonraki açılıştan olduğu için gerçek mesafe biraz farklı).
- `minimal_roi` (dakika anahtarlı) -> `CikisAyarlari.azalan_roi`: mum sayısı = yukarı yuvarlanmış dakika / TF dakikası; aynı muma
  düşen basamaklarda büyük dakikalı olan geçerli (Freqtrade: süresi dolmuş en büyük anahtar). Kâr kapanışta sınanır, çıkış
  sonraki açılışta (kaynakta mum içi).
- `trailing_stop` + `trailing_only_offset_is_reached=True` -> `geri_cekilme_yuzde` (iz) + `geri_cekilme_min_kar_yuzde` (offset):
  zirve kâr% >= offset iken zirveden kâr% farkı >= iz (kapanış bazlı).
- `sell_profit_only=True` -> `yalniz_karda_cikis=True` (865, 894; 843'te sinyal çıkışı olmadığından etkisiz ama kaynağa uygun).
- Kaynakta gösterge değerleri TA-Lib ile ısınır; burada motorun EMA/RSI/ATR tanımları kullanıldığından ilk ~100 mumda küçük fark olur.

Kaynak ile `kural_tam` özeti arasındaki farklarda KAYNAK dosya esas alındı (satır notlarına bakın): 854 (BB penceresi 16 / 1 sapma,
TEMA periyodu 7).

KODLANAMADI satırı yok (dosya sonundaki liste boş).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import hma as _hma
from motor.strateji._gosterge_d11j import williams_r as _willr
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu as _roi
from motor.strateji.seans_takvimi import mum_suresi
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


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _ema_zinciri(seri: pd.Series, n: int, adet: int) -> list:
    cikti, x = [], seri
    for _ in range(adet):
        x = x.ewm(span=n, adjust=False, min_periods=n).mean()
        cikti.append(x)
    return cikti


def _tema(seri: pd.Series, n: int) -> pd.Series:
    e1, e2, e3 = _ema_zinciri(seri, n, 3)
    return 3.0 * e1 - 3.0 * e2 + e3


def _dema(seri: pd.Series, n: int) -> pd.Series:
    e1, e2 = _ema_zinciri(seri, n, 2)
    return 2.0 * e1 - e2


def _fisher_rsi(kap: pd.Series, n: int) -> pd.Series:
    """Ters Fisher dönüşümlü RSI: x = 0,1 x (RSI - 50); (e^2x - 1) / (e^2x + 1) = tanh(x)."""
    return np.tanh(0.1 * (g.rsi(kap, n) - 50.0))


def _desen(m: pd.DataFrame) -> pd.Series:
    """İki mum teorisi 9'lu desen (0..8): kapanışın mum içi üçte biri (+1 üst, -1 alt) x 3 + önceki mum aralığına göre kapanış
    (+1 önceki yükseğin üstünde, -1 önceki düşüğün altında) + 4."""
    aralik3 = (m["yuksek"] - m["dusuk"]) / 3.0
    konum = (m["kapanis"] > m["yuksek"] - aralik3).astype(int) - (m["kapanis"] < m["dusuk"] + aralik3).astype(int)
    kars = (m["kapanis"] > m["yuksek"].shift(1)).astype(int) - (m["kapanis"] < m["dusuk"].shift(1)).astype(int)
    return konum * 3 + kars + 4


# ================================================================ B001:813
class HmaWillrB0813(Strateji):
    """HAM:B001:813 (15m, long; kaynak strategies/rsi-momentum/e6v34.py, .json yok -> sınıf varsayılanları): HMA(15) - HMA(35)
    farkı iki ardışık mumda artıyor VE Williams %R(12) -20'yi yukarı keser (şimdiki > -20, önceki < -20) VE hacim > EMA(100, hacim)
    -> long. Çıkış: Williams %R -50'yi aşağı keser VEYA ROI {0dk %55,5; 300 %35; 500 %24,7; 1200 %9,36; 2100 %4; 4000 0} VEYA iz
    süren %18 (offset %20, yalnız offset sonrası). Kaynak stopu -%54 (<= -%50) -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__hma-willr-b0813", "daytrade"
    varsayilan_parametreler = {"hma_kisa": 15, "hma_uzun": 35, "willr_n": 12, "bwill": -20.0, "swill": -50.0,
                               "hacim_ema": 100, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.555, 300: 0.35, 500: 0.247, 1200: 0.0936, 2100: 0.04, 4000: 0.0}, 15),
        geri_cekilme_yuzde=18.0, geri_cekilme_min_kar_yuzde=20.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        fark = _hma(kap, int(p["hma_kisa"])) - _hma(kap, int(p["hma_uzun"]))
        wr = _willr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["willr_n"]))
        b, sw = float(p["bwill"]), float(p["swill"])
        al = ((fark.shift(1) < fark) & (fark.shift(2) < fark.shift(1)) & (wr > b) & (wr.shift(1) < b)
              & (mumlar["hacim"] > g.ema(mumlar["hacim"], int(p["hacim_ema"]))))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, False, kap - mes, kap + mes)
        return _bitir(s, (wr < sw) & (wr.shift(1) > sw))


# ================================================================ B001:816
class RsiSmaDurumB0816(Strateji):
    """HAM:B001:816 (15m, long; kaynak strategies/rsi-momentum/qrsi.py): durum girişi, her mumda: RSI(14) < 60 VE kapanış > SMA(20).
    Kaynağın sinyal çıkışı ölü koşul (giriş sinyali ile RSI > 70 aynı anda imkânsız): çıkış yalnız ROI %10 (azalan_roi ((0, 10),)),
    iz süren %3 (offset %4, yalnız offset sonrası), stop -%5. Dosyadaki 1h/4h/1d resample sütunları girişte kullanılmıyor (teyit
    edildi); debug print/CSV yazımı kural dışı."""

    ad, stil = "kapanis__rsi-sma-durum-b0816", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_ust": 60.0, "sma_n": 20, "sl": 0.05}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.10}, 15),
                                   geri_cekilme_yuzde=3.0, geri_cekilme_min_kar_yuzde=4.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        al = (g.rsi(kap, int(p["rsi_n"])) < float(p["rsi_ust"])) & (kap > g.sma(kap, int(p["sma_n"])))
        sl = float(p["sl"])
        return cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))


# ================================================================ B001:817
class Rsi30DemaB0817(Strateji):
    """HAM:B001:817 (1h, long; kaynak strategies/rsi-momentum/stratfib.py): RSI(14) 30'u yukarı keser VE DEMA(8) > DEMA(21) VE
    DEMA(8) > DEMA(89) VE hacim > 0 -> long. Çıkış: RSI(14) 70'i yukarı keser VE DEMA(8) < DEMA(21) VE DEMA(8) < DEMA(89) VEYA
    ROI {0dk %4; 30 %2; 60 %1} (1h mumda 30 ve 60. dk aynı muma düşer: %1 geçerli); stop -%10."""

    ad, stil = "kapanis__rsi30-dema-b0817", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "buy_rsi": 30.0, "sell_rsi": 70.0, "dema_a": 8, "dema_b": 21, "dema_c": 89,
                               "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 60))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        da, db, dc = (_dema(kap, int(p[k])) for k in ("dema_a", "dema_b", "dema_c"))
        var = mumlar["hacim"] > 0
        al = yukari(r, float(p["buy_rsi"])) & (da > db) & (da > dc) & var
        cik = yukari(r, float(p["sell_rsi"])) & (da < db) & (da < dc) & var
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ B001:843
class Rsi30BbTemaB0843(Strateji):
    """HAM:B001:843 (15m, long; kaynak strategies/smart-money-concepts/BuyOnly.py): RSI(14) 30'u yukarı keser VE açılış <=
    Bollinger(tipik fiyat, 20, 2s) alt bandı VE TEMA(9) önceki mumdan büyük VE hacim > 0 -> long (TEMA/BB periyotları dosyadan
    teyit edildi). Çıkış sinyali yok (HODL); ROI {0dk %4; 30 %2; 60 %1} (azalan_roi), yalnız kârda; stop -%10."""

    ad, stil = "kapanis__rsi30-bb-tema-b0843", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30.0, "bb_n": 20, "bb_k": 2.0, "tema_n": 9, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 15), yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        alt = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["alt"]
        tema = _tema(kap, int(p["tema_n"]))
        al = (yukari(g.rsi(kap, int(p["rsi_n"])), float(p["rsi_al"])) & (mumlar["acilis"] <= alt)
              & (tema > tema.shift(1)) & (mumlar["hacim"] > 0))
        sl = float(p["sl"])
        return cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))


# ================================================================ B001:845
class ClucFiatSlowB0845(Strateji):
    """HAM:B001:845 (5m, long; kaynak strategies/smart-money-concepts/ClucFiatSlow.py, buy/sell_params sabit): Fisher-RSI(RSI 9) <
    -0,97101 VE [ kol 1: |orta40 - alt40| > kapanış x 0,00642 VE |kapanış - önceki kapanış| > kapanış x 0,00883 VE (kapanış - düşük)
    < bb1delta x 0,75559 VE kapanış < alt40[t-1] VE kapanış <= önceki kapanış (BB40: kapanış, 2s) VEYA kol 2: kapanış < EMA(48) VE
    kapanış < 0,01415 x alt20(tipik fiyat BB 20, 2s; kaynakta aynen böyle, fiilen nadir) VE hacim < SMA(24, hacim)[t-1] x 18 ].
    Çıkış (VE): 0,95153 x kapanış > orta20 VE EMA(6) > kapanış VE Fisher-RSI > 0,60924 VE hacim > 0; ayrıca ROI {0dk %4,354; 5 %3,734;
    8 %2,569; 10 %1,9; 76 %1,283; 235 %0,7; 415 0} ve iz süren %1,057 (offset %3,668); stop -%34,299."""

    ad, stil = "kapanis__cluc-fiat-slow-b0845", "daytrade"
    varsayilan_parametreler = {"fisher": -0.97101, "bbdelta_close": 0.00642, "bbdelta_tail": 0.75559,
                               "closedelta_close": 0.00883, "close_bblower": 0.01415, "volume": 18.0,
                               "sell_bbmiddle_close": 0.95153, "sell_fisher": 0.60924, "rsi_n": 9, "bb1_n": 40,
                               "bb2_n": 20, "ema_yavas": 48, "ema_hizli": 6, "hacim_n": 24, "sl": 0.34299}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.04354, 5: 0.03734, 8: 0.02569, 10: 0.019, 76: 0.01283, 235: 0.007, 415: 0.0}, 5),
        geri_cekilme_yuzde=1.057, geri_cekilme_min_kar_yuzde=3.668)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, dus = mumlar["kapanis"], mumlar["dusuk"]
        fr = _fisher_rsi(kap, int(p["rsi_n"]))
        bb1 = g.bollinger(kap, int(p["bb1_n"]), 2.0)
        bb2 = g.bollinger(_tipik(mumlar), int(p["bb2_n"]), 2.0)
        bb1delta = (bb1["orta"] - bb1["alt"]).abs()
        kol1 = ((bb1delta > kap * float(p["bbdelta_close"]))
                & ((kap - kap.shift(1)).abs() > kap * float(p["closedelta_close"]))
                & ((kap - dus).abs() < bb1delta * float(p["bbdelta_tail"]))
                & (kap < bb1["alt"].shift(1)) & (kap <= kap.shift(1)))
        hort = mumlar["hacim"].rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        kol2 = ((kap < g.ema(kap, int(p["ema_yavas"]))) & (kap < float(p["close_bblower"]) * bb2["alt"])
                & (mumlar["hacim"] < hort.shift(1) * float(p["volume"])))
        al = (fr < float(p["fisher"])) & (kol1 | kol2)
        cik = ((kap * float(p["sell_bbmiddle_close"]) > bb2["orta"]) & (g.ema(kap, int(p["ema_hizli"])) > kap)
               & (fr > float(p["sell_fisher"])) & (mumlar["hacim"] > 0))
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ B001:854
class FrayCokluB0854(Strateji):
    """HAM:B001:854 (15m, long; kaynak strategies/smart-money-concepts/FRAYSTRAT.py): 3 kollu giriş (VEYA, hepsi hacim > 0):
    (1) RSI(14) 46'yı yukarı keser VE TEMA < BB orta VE TEMA önceki mumdan büyük VE TEMA < EMA(7); (2) EMA(7) < EMA(12) VE RSI > 40 VE
    RSI > önceki RSI VE MACD sinyali > MACD; (3) MACD > sinyal VE EMA(12) < EMA(7) VE TEMA önceki mumdan büyük. 3 kollu çıkış (VEYA):
    (1) RSI 70'i yukarı keser VE TEMA > BB orta VE TEMA düşüyor; (2) EMA(7) > EMA(12) VE TEMA > EMA(7) VE RSI düşüyor VE sinyal > MACD;
    (3) sinyal > MACD VE MACD > sinyal[t-1] VE TEMA > EMA(7) VE TEMA düşüyor. ROI artan tablo {0dk %6; 30 %8; 60 %12} (kaynakta öyle;
    ilk 30 dk %6, sonra %8, 60 dk sonrası %12); iz süren %2 (offset %3); stop -%10.
    DÜZELTME (kaynak esas): kural_tam 'TEMA9' ve 'BB(20)' diyordu; kaynakta TEMA periyodu 7, BB penceresi 16 (1 sapma; yalnız orta
    bant kullanılır = tipik fiyatın SMA(16)'sı)."""

    ad, stil = "kapanis__fray-coklu-b0854", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "buy_rsi": 46.0, "sell_rsi": 70.0, "tema_n": 7, "bb_n": 16, "ema_a": 7,
                               "ema_b": 12, "rsi_dip": 40.0, "macd_hizli": 12, "macd_yavas": 26, "macd_sinyal": 9,
                               "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.06, 30: 0.08, 60: 0.12}, 15),
                                   geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        tema = _tema(kap, int(p["tema_n"]))
        orta = g.sma(_tipik(mumlar), int(p["bb_n"]))
        e7, e12 = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        mc = g.macd(kap, int(p["macd_hizli"]), int(p["macd_yavas"]), int(p["macd_sinyal"]))
        m, sg = mc["macd"], mc["sinyal"]
        var = mumlar["hacim"] > 0
        tema_yuk, tema_dus = tema > tema.shift(1), tema < tema.shift(1)
        al = ((yukari(r, float(p["buy_rsi"])) & (tema < orta) & tema_yuk & (tema < e7) & var)
              | ((e7 < e12) & (r > float(p["rsi_dip"])) & (r > r.shift(1)) & (sg > m) & var)
              | ((sg < m) & (e12 < e7) & tema_yuk & var))
        cik = ((yukari(r, float(p["sell_rsi"])) & (tema > orta) & tema_dus & var)
               | ((e7 > e12) & (tema > e7) & (r < r.shift(1)) & (sg > m) & var)
               | ((sg > m) & (m > sg.shift(1)) & (tema > e7) & tema_dus & var))
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ B001:865
class FisherTemaBbB0865(Strateji):
    """HAM:B001:865 (15m, long; kaynak strategies/smart-money-concepts/PRICEFOLLOWINGX.py, rsi_enabled/sell_rsi_enabled = True):
    Fisher-RSI(RSI 14) -0,40'ı aşağı keser VE TEMA(7) < Bollinger(tipik fiyat, 19, 2,2s) alt bant VE TEMA(7) EMA(12, düşük)'ü aşağı
    keser -> long. Çıkış: Fisher-RSI 0,2'yi aşağı keser VE TEMA(7) < BB orta VE TEMA(7) SMA(14)'ü aşağı keser, yalnız kârda (sell_profit_only);
    ROI {0dk %1,5; 30 %3; 60 %2,5; 120 %1,5}; iz süren %2 (offset %3); kaynak stopu -%50 (<= -%50) -> ATR(14)x3 (uyarlama).
    Not: ema_pct/frsi_pct parametreleri tanımlı ama girişte kullanılmıyor; Heikin-Ashi sütunları kullanılmıyor."""

    ad, stil = "kapanis__fisher-tema-bb-b0865", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "buy_frsi": -0.40, "sell_frsi": 0.20, "tema_n": 7, "bb_n": 19, "bb_k": 2.2,
                               "ema_dusuk_n": 12, "sma_n": 14, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.015, 30: 0.03, 60: 0.025, 120: 0.015}, 15),
        geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0, yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        fr = _fisher_rsi(kap, int(p["rsi_n"]))
        tema = _tema(kap, int(p["tema_n"]))
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        ema_dusuk = g.ema(mumlar["dusuk"], int(p["ema_dusuk_n"]))
        sma = g.sma(kap, int(p["sma_n"]))
        al = asagi(fr, float(p["buy_frsi"])) & (tema < bb["alt"]) & asagi(tema, ema_dusuk)
        cik = asagi(fr, float(p["sell_frsi"])) & (tema < bb["orta"]) & asagi(tema, sma)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, False, kap - mes, kap + mes)
        return _bitir(s, cik)


# ================================================================ B001:870
# flawless_lambo minimal_roi: 120 dk'dan sonra her 5 dk'da bir basamak (tek tek yazılmak yerine 15 dk katlarındaki değerler; 15m
# mumda tutulan süre hep 15'in katıdır ve o anahtar daima vardır, sonuç tam tablo ile aynı: testte CSV'deki tam tabloyla sınanır).
# Değerler 120, 135, ..., 3750. dk için oran; 3755. dk anahtarı 0.
_LAMBO_ROI_DEGERLERI = (
    0.30135315985130107, 0.29452230483271374, 0.28769144981412637, 0.28086059479553904, 0.27402973977695166,
    0.2671988847583643, 0.2603680297397769, 0.2535371747211896, 0.2467063197026022, 0.23987546468401488,
    0.2330446096654275, 0.22621375464684013, 0.2193828996282528, 0.2125520446096654, 0.20572118959107805,
    0.1988903345724907, 0.19205947955390332, 0.18522862453531597, 0.17839776951672862, 0.17156691449814124,
    0.1647360594795539, 0.15790520446096654, 0.15107434944237916, 0.1442434944237918, 0.13741263940520443,
    0.13058178438661708, 0.12375092936802971, 0.11692007434944236, 0.11079597315436242, 0.10926577181208054,
    0.10773557046979866, 0.10620536912751678, 0.1046751677852349, 0.10314496644295304, 0.10161476510067116,
    0.10008456375838928, 0.09855436241610738, 0.0970241610738255, 0.09549395973154362, 0.09396375838926174,
    0.09243355704697986, 0.090903355704698, 0.08937315436241611, 0.08784295302013423, 0.08631275167785235,
    0.08478255033557047, 0.0832523489932886, 0.08172214765100672, 0.08019194630872484, 0.07866174496644296,
    0.07713154362416108, 0.0756013422818792, 0.07407114093959732, 0.07254093959731545, 0.07101073825503357,
    0.06948053691275169, 0.06795033557046981, 0.06642013422818793, 0.06488993288590604, 0.06335973154362416,
    0.06182953020134229, 0.060299328859060405, 0.05876912751677853, 0.05723892617449665, 0.05570872483221477,
    0.05417852348993289, 0.052648322147651014, 0.05111812080536913, 0.04958791946308725, 0.04805771812080538,
    0.0465275167785235, 0.04499731543624161, 0.04346711409395973, 0.04193691275167785, 0.04040671140939597,
    0.038876510067114095, 0.03734630872483222, 0.03581610738255034, 0.03490072933549433, 0.034688006482982175,
    0.03447528363047002, 0.03426256077795786, 0.034049837925445706, 0.033837115072933556, 0.0336243922204214,
    0.03341166936790924, 0.033198946515397086, 0.03298622366288493, 0.03277350081037277, 0.032560777957860616,
    0.03234805510534847, 0.03213533225283631, 0.03192260940032415, 0.031709886547812, 0.03149716369529984,
    0.031284440842787684, 0.03107171799027553, 0.030858995137763377, 0.03064627228525122, 0.030433549432739064,
    0.030220826580226907, 0.03000810372771475, 0.02979538087520259, 0.02958265802269044, 0.029369935170178284,
    0.02915721231766613, 0.028944489465153975, 0.028731766612641815, 0.02851904376012966, 0.028306320907617505,
    0.02809359805510535, 0.027880875202593195, 0.02766815235008104, 0.027455429497568885, 0.02724270664505673,
    0.027029983792544572, 0.026817260940032416, 0.026604538087520262, 0.026391815235008102, 0.026179092382495953,
    0.025966369529983796, 0.02575364667747164, 0.025540923824959483, 0.02532820097244733, 0.025115478119935173,
    0.024902755267423016, 0.024690032414910863, 0.024477309562398707, 0.02426458670988655, 0.024051863857374393,
    0.023839141004862237, 0.023626418152350084, 0.023413695299837927, 0.023200972447325777, 0.022988249594813617,
    0.02277552674230146, 0.022562803889789304, 0.022350081037277147, 0.02213735818476499, 0.02192463533225284,
    0.021711912479740685, 0.021499189627228528, 0.02128646677471637, 0.021073743922204215, 0.020861021069692055,
    0.020648298217179905, 0.020435575364667752, 0.020222852512155595, 0.02001012965964344, 0.01979740680713128,
    0.019584683954619125, 0.019371961102106972, 0.019159238249594816, 0.01894651539708266, 0.018733792544570502,
    0.01852106969205835, 0.018308346839546193, 0.018095623987034036, 0.017882901134521883, 0.017670178282009726,
    0.01745745542949757, 0.017244732576985417, 0.01703200972447326, 0.016819286871961103, 0.016606564019448947,
    0.016393841166936794, 0.016181118314424637, 0.01596839546191248, 0.015755672609400327, 0.01554294975688817,
    0.015330226904376014, 0.015117504051863856, 0.014904781199351704, 0.014692058346839548, 0.014479335494327393,
    0.014266612641815238, 0.01405388978930308, 0.013841166936790925, 0.013628444084278771, 0.013415721231766617,
    0.013202998379254458, 0.012990275526742302, 0.012777552674230148, 0.012564829821717992, 0.012352106969205835,
    0.012139384116693682, 0.011926661264181524, 0.011713938411669369, 0.011501215559157212, 0.01128849270664506,
    0.011075769854132902, 0.010863047001620746, 0.010650324149108593, 0.010437601296596436, 0.01022487844408428,
    0.010012155591572125, 0.00979943273905997, 0.009586709886547811, 0.009373987034035657, 0.009161264181523503,
    0.008948541329011347, 0.00873581847649919, 0.008523095623987034, 0.00831037277147488, 0.008097649918962724,
    0.007884927066450567, 0.007672204213938414, 0.007459481361426257, 0.007246758508914101, 0.007034035656401944,
    0.006821312803889791, 0.0066085899513776344, 0.006395867098865478, 0.006183144246353325, 0.005970421393841168,
    0.0057576985413290115, 0.005544975688816855, 0.005332252836304702, 0.005119529983792545, 0.0049068071312803885,
    0.004694084278768235, 0.004481361426256079, 0.004268638573743922, 0.004055915721231769, 0.003843192868719613,
    0.003630470016207456, 0.003417747163695299, 0.0032050243111831425, 0.002992301458670986, 0.002779578606158836,
    0.0025668557536466796, 0.002354132901134523, 0.0021414100486223664, 0.0019286871961102096, 0.0017159643435980532,
    0.0015032414910858966, 0.0012905186385737469, 0.0010777957860615905, 0.0008650729335494337, 0.000652350081037277,
    0.0004396272285251204, 0.00022690437601296384, 1.4181523500814142e-05,
)
_LAMBO_ROI = {**{dk: v for dk, v in zip(range(120, 3751, 15), _LAMBO_ROI_DEGERLERI)}, 3755: 0.0}
# 3900/3960/4020. dk anahtarları -%1/-%2/-%3 (negatif ROI): azalan_roi ifade edemez, kancada.
_LAMBO_NEGATIF_ROI = ((3900, 1.0), (3960, 2.0), (4020, 3.0))


class LamboObvWillrB0870(Strateji):
    """HAM:B001:870 (15m, long; kaynak strategies/smart-money-concepts/flawless_lambo.py): hacim > 0 VE OBV eğimi > 0 (OBV[t] > OBV[t-1],
    slope(length=1)) VE +DI(14) eğimi > 0 (+DI[t] > +DI[t-1]) VE Williams %R(14) < -66 VE kapanış Bollinger(tipik fiyat, 20, 2s) alt
    bandını yukarı keser -> long. Çıkış: hacim > 0 VE kapanış > BB üst VE +DI eğimi < 0 VE Williams %R >= -10 VE RSI(14) >= 70; ayrıca
    ROI tablosu (dosyadaki minimal_roi: 120. dk %30,135 ... 3755. dk 0, 5 dk adımlı azalan; 120 dk öncesi ROI yok) ve 3900/3960/4020. dk
    anahtarları -%1/-%2/-%3 (negatif ROI, `azalan_roi` kabul etmez: kancada, tutulan süre >= anahtar ise kâr% >= -zarar ise çık).
    Kaynak stopu -1 (stopsuz) -> ATR(14)x3 (uyarlama). trailing_stop kapalı (trailing_stop_positive değerleri etkisiz);
    canlı trailing-sell blokları yalnız live/dry_run, kural dışı."""

    ad, stil = "kapanis__lambo-obv-willr-b0870", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "willr_n": 14, "willr_al": -66.0, "willr_cik": -10.0, "rsi_n": 14,
                               "rsi_cik": 70.0, "di_n": 14, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi(_LAMBO_ROI, 15))
    _negatif_roi = tuple((int(math.ceil(dk / 15.0)), z) for dk, z in _LAMBO_NEGATIF_ROI)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        obv_egim = (np.sign(kap.diff()).fillna(0.0) * mumlar["hacim"]).cumsum().diff()
        di = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["di_n"]))["arti_di"]
        di_egim = di.diff()
        wr = _willr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["willr_n"]))
        var = mumlar["hacim"] > 0
        al = var & (obv_egim > 0) & (di_egim > 0) & (wr < float(p["willr_al"])) & yukari(kap, bb["alt"])
        cik = (var & (kap > bb["ust"]) & (di_egim < 0) & (wr >= float(p["willr_cik"]))
               & (g.rsi(kap, int(p["rsi_n"])) >= float(p["rsi_cik"])))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, False, kap - mes, kap + mes)
        return _bitir(s, cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        gecerli = None
        for mum, zarar in self._negatif_roi:
            if d.tutulan_mum >= mum:
                gecerli = zarar
        return gecerli is not None and d.kar_yuzde >= -gecerli


# ================================================================ B001:875
class IkiMum4hB0875(Strateji):
    """HAM:B001:875 (1h + 4h bilgi, long; kaynak strategies/two-candle/2Candle.py, etkin değerler = sınıf varsayılanı: buy_params ve
    .json yok). 4h (yalnız KAPANMIŞ mumlar, htf.ust_zaman): desen_4h (9'lu), CO2_4h = (kapanış - açılış)/2 + açılış, RSI(6)_4h, düşük_4h,
    yüksek_4h. 1h: desen = konum x 3 + kapanış karşılaştırması + 4; pattern_avg = SMA2((desen + desen_4h)/2); destek = düşük_4h'nin
    (1h satırlarına taşınmış) son 24 satır en küçüğü, 24 satır kaydırılmış; direnç aynı biçimde yüksek_4h en büyüğü; rsi = RSI(12, 1h).
    Giriş (VEYA, 5 kol): (1) pattern_avg >= 4 VE pattern_avg[t-1] < 8 VE rsi_4h < 65 VE rsi > rsi_4h; (2) pattern_avg >= 4 VE pattern_avg[t-1]
    < 8 VE CO2_4h > direnç VE CO2_4h[t-1] < direnç[t-1] VE rsi_4h < 65 VE rsi > rsi_4h; (3) pattern_avg >= 4 VE CO2_4h > destek VE
    CO2_4h[t-1] < destek[t-1]; (4) pattern_avg >= 4 VE CO2_4h < destek VE CO2_4h[t-4] < CO2_4h VE rsi > rsi_4h; (5) CO2_4h < destek VE
    rsi_4h < 10 VE rsi > rsi_4h. Çıkış: CO2_4h > direnç VE kapanış > direnç VE kapanış < CO2_4h VE rsi_4h > 85. ROI yok ({});
    iz süren %2,5 (offset %10, yalnız offset sonrası); stop -%4. (sell_threshold parametresi dosyada çıkışta kullanılmıyor, yok sayıldı.)"""

    ad, stil = "kapanis__iki-mum-4h-b0875", "swing"
    varsayilan_parametreler = {"buy_threshold": 4.0, "rsi_threshold": 65.0, "sr_length": 24, "sr_shift": 24,
                               "fast_rsi": 12, "rsi4_n": 6, "rsi4_asiri": 10.0, "rsi4_cikis": 85.0, "sl": 0.04}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=2.5, geri_cekilme_min_kar_yuzde=10.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n4 = int(p["rsi4_n"])

        def dortsaat(u):
            return pd.DataFrame({"desen": _desen(u), "co2": (u["kapanis"] - u["acilis"]) / 2.0 + u["acilis"],
                                 "rsi": g.rsi(u["kapanis"], n4), "dusuk": u["dusuk"], "yuksek": u["yuksek"]})

        h4 = ust_zaman(mumlar, "4h", dortsaat)
        co2, rsi4 = h4["co2"], h4["rsi"]
        desen_ort = ((_desen(mumlar) + h4["desen"]) / 2.0).rolling(2).mean()
        uz, kay = int(p["sr_length"]), int(p["sr_shift"])
        destek = h4["dusuk"].rolling(uz).min().shift(kay)
        direnc = h4["yuksek"].rolling(uz).max().shift(kay)
        r = g.rsi(kap, int(p["fast_rsi"]))
        esik, rsi_esik = float(p["buy_threshold"]), float(p["rsi_threshold"])
        guclu = desen_ort >= esik
        onceki_ok = desen_ort.shift(1) < 8
        kol1 = guclu & onceki_ok & (rsi4 < rsi_esik) & (r > rsi4)
        kol2 = (guclu & onceki_ok & (co2 > direnc) & (co2.shift(1) < direnc.shift(1)) & (rsi4 < rsi_esik) & (r > rsi4))
        kol3 = guclu & (co2 > destek) & (co2.shift(1) < destek.shift(1))
        kol4 = guclu & (co2 < destek) & (co2.shift(4) < co2) & (r > rsi4)
        kol5 = (co2 < destek) & (rsi4 < float(p["rsi4_asiri"])) & (r > rsi4)
        cik = (co2 > direnc) & (kap > direnc) & (kap < co2) & (rsi4 > float(p["rsi4_cikis"]))
        sl = float(p["sl"])
        s = cerceve(mumlar, kol1 | kol2 | kol3 | kol4 | kol5, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ B001:876
class IkiMumB0876(Strateji):
    """HAM:B001:876 (1h, long; kaynak strategies/two-candle/TwoCandle.py; tek aktif giriş kolu, diğerleri yorum satırında): desen = konum x
    3 + kapanış karşılaştırması + 4 (0..8); pattern_mean = SMA2(desen). Giriş: pattern_mean[t-1] < 4 VE pattern_mean > 4. Çıkış (VEYA):
    pattern_mean < 3,5 VE desen[t-1] == 8; ... == 7; ... == 6 (desen >= 0 koşulu her zaman doğru); pattern_mean[t-1] > 4 VE pattern_mean
    < 4. ROI {0dk %1,5; 15 %1,2; 30 %5; 60 %2,5} (1h mumda 15/30/60 dk aynı muma düşer: %2,5 geçerli); iz süren %1,3 (offset %3,5);
    stop -%3."""

    ad, stil = "kapanis__iki-mum-b0876", "swing"
    varsayilan_parametreler = {"giris_esik": 4.0, "cikis_esik": 3.5, "sl": 0.03}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.015, 15: 0.012, 30: 0.05, 60: 0.025}, 60),
                                   geri_cekilme_yuzde=1.3, geri_cekilme_min_kar_yuzde=3.5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        desen = _desen(mumlar)
        ort = desen.rolling(2).mean()
        e, c = float(p["giris_esik"]), float(p["cikis_esik"])
        al = (ort.shift(1) < e) & (ort > e)
        zayif = ort < c
        onceki = desen.shift(1)
        cik = (zayif & ((onceki == 8) | (onceki == 7) | (onceki == 6))) | ((ort.shift(1) > e) & (ort < e))
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ B001:894
class OtuzGunDipB0894(Strateji):
    """HAM:B001:894 (1h, long; kaynak strategies/uncategorized/Slowbro.py): 1d bilgi (yalnız KAPANMIŞ günlük mumlar, htf.ust_zaman):
    30 günlük kapanış en düşüğü ve en yükseği (rolling(30) üzerinden günlük kapanışlar). Giriş: kapanış, 30g dibi yukarı keser.
    Çıkış: kapanış 30g tepeyi yukarı keser, yalnız kârda (sell_profit_only); ROI {0dk %10; 1440 %20; 2880 %30; 10080 %100} (azalan_roi).
    Kaynak stopu -%99 (stopsuz) -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__otuz-gun-dip-b0894", "swing"
    varsayilan_parametreler = {"gun_n": 30, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.10, 1440: 0.20, 2880: 0.30, 10080: 1.0}, 60),
                                   yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n = int(p["gun_n"])
        gun = ust_zaman(mumlar, "1d", lambda u: pd.DataFrame({"dip": u["kapanis"].rolling(n).min(),
                                                              "tepe": u["kapanis"].rolling(n).max()}))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, yukari(kap, gun["dip"]), False, kap - mes, kap + mes)
        return _bitir(s, yukari(kap, gun["tepe"]))


# ================================================================ B001:899
class DynaBinB0899(KancaDestek, Strateji):
    """HAM:B001:899 (5m + 1h bilgi, long; kaynak strategies/wavetrend/Dyna_opti.py, buy/sell_params sabit). Giriş (VE): Bollinger(tipik fiyat,
    12, 2s) alt[t-1] > 0 VE |orta - alt| > kapanış x 0,025 VE |kapanış - önceki kapanış| > kapanış x 0,018 VE (kapanış - düşük) < bbdelta x
    0,945 VE kapanış < alt[t-1] VE kapanış <= önceki kapanış VE hacim > 0 VE 1h süzgeç (inf_guard='lower'; yalnız KAPANMIŞ 1h, htf.ust_zaman):
    kapanış >= 3g düşük (72 x 1h kapanış en küçüğü) + 0,172 x ADR (24 x 1h kapanış max - min). Sinyal çıkışı yok. Stop -%28,819.
    Çıkışlar kancada (kapanış bazlı): (a) DİNAMİK ROI: tablo {0dk %18,724; 20 %4,751; 30 %2,393; 72 0}, tutulan süreye göre; trend içindeyse
    (droi_trend_type 'any': RMI(24,5) son 5 mumun >= 3'ünde artıyor VEYA SSL kanalı(21, ATR) yukarı VEYA son 5 mumun >= 3'ü yükselen
    kapanış) ROI askıda (min_roi = 100), değilse kâr > tablo ROI ise çık (droi_pullback kapalı; açılırsa kaynak gibi); (b) ÖZEL STOP: kâr <
    -%5 iken tutulan süre > 961 dk ise çık (cstp_bail_how 'time'; 'roc'/'any' için SROC(21,13,21)/100 <= bail_roc koşulu da kodlandı).
    Uyarlama: kaynaktaki bar içi/zaman damgalı kontrol yerine kapanışta kontrol, çıkış sonraki açılışta."""

    ad, stil = "kapanis__dyna-bin-b0899", "daytrade"
    ROI_DK = {0: 0.18724, 20: 0.04751, 30: 0.02393, 72: 0.0}
    varsayilan_parametreler = {"bbdelta_close": 0.025, "closedelta_close": 0.018, "tail_bbdelta": 0.945,
                               "inf_guard": "lower", "inf_pct_adr_top": 0.792, "inf_pct_adr_bot": 0.172,
                               "droi_trend_type": "any", "droi_pullback": False, "droi_pullback_amount": 0.015,
                               "droi_pullback_respect_table": True, "cstp_threshold": -0.05, "cstp_bail_how": "time",
                               "cstp_bail_roc": -0.018, "cstp_bail_time": 961, "bb_n": 12, "sl": 0.28819}
    parametre_izgarasi = {}
    _tf_dk = 5.0

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _rmi(kap: pd.Series, n: int, mom: int) -> pd.Series:
        art = (kap - kap.shift(mom)).clip(lower=0).fillna(0.0)
        eks = (kap.shift(mom) - kap).clip(lower=0).fillna(0.0)
        a, e = g.ema(art, n), g.ema(eks, n)
        return pd.Series(np.where(e == 0, 0.0, 100.0 - 100.0 / (1.0 + a / e)), index=kap.index)

    @staticmethod
    def _ssl_yukari(m: pd.DataFrame, n: int) -> pd.Series:
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
        ust = m["yuksek"].rolling(n).mean() + atr
        alt = m["dusuk"].rolling(n).mean() - atr
        yon = pd.Series(np.where(m["kapanis"] > ust, 1.0, np.where(m["kapanis"] < alt, -1.0, np.nan)), index=m.index).ffill()
        ssl_asagi = pd.Series(np.where(yon < 0, ust, alt), index=m.index)
        ssl_yukari = pd.Series(np.where(yon < 0, alt, ust), index=m.index)
        return ssl_yukari > ssl_asagi

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), 2.0)
        bbdelta = (bb["orta"] - bb["alt"]).abs()
        inf = ust_zaman(mumlar, "1h", lambda u: pd.DataFrame({
            "dip3g": u["kapanis"].rolling(72).min(),
            "adr": u["kapanis"].rolling(24).max() - u["kapanis"].rolling(24).min()}))
        guard = pd.Series(True, index=mumlar.index)
        if p["inf_guard"] in ("upper", "both"):
            guard &= kap <= inf["dip3g"] + float(p["inf_pct_adr_top"]) * inf["adr"]
        if p["inf_guard"] in ("lower", "both"):
            guard &= kap >= inf["dip3g"] + float(p["inf_pct_adr_bot"]) * inf["adr"]
        al = (guard & (bb["alt"].shift(1) > 0) & (bbdelta > kap * float(p["bbdelta_close"]))
              & ((kap - kap.shift(1)).abs() > kap * float(p["closedelta_close"]))
              & ((kap - mumlar["dusuk"]).abs() < bbdelta * float(p["tail_bbdelta"]))
              & (kap < bb["alt"].shift(1)) & (kap <= kap.shift(1)) & (mumlar["hacim"] > 0))
        # kanca dizileri (nedensel)
        rmi = self._rmi(kap, 24, 5)
        rmi_trend = ((rmi >= rmi.shift(1)).astype(int).rolling(5).sum() >= 3)
        mum_trend = ((kap >= kap.shift(1)).astype(int).rolling(5).sum() >= 3)
        ssl = self._ssl_yukari(mumlar, 21)
        tip = str(p["droi_trend_type"])
        trend = pd.Series(False, index=mumlar.index)
        if tip in ("rmi", "any"):
            trend |= rmi_trend
        if tip in ("ssl", "any"):
            trend |= ssl
        if tip in ("candle", "any"):
            trend |= mum_trend
        self._sakla(trend=trend.astype(float), sroc=self._sroc(kap))
        self._tf_dk = float(mum_suresi(mumlar.index) / pd.Timedelta(minutes=1))
        sl = float(p["sl"])
        return cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))

    @staticmethod
    def _sroc(kap: pd.Series) -> pd.Series:
        """SROC(21, 13, 21): EMA(13)'ün 21 mumluk değişim yüzdesi (kaynakta bu seri ROC(EMA, 21))."""
        e = g.ema(kap, 13)
        return 100.0 * (e / e.shift(21) - 1.0)

    def _tablo_roi(self, dk: float):
        gecerli = None
        for anahtar in sorted(self.ROI_DK):
            if dk >= anahtar:
                gecerli = self.ROI_DK[anahtar]
        return gecerli

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if d.yon != 1 or not self._var(i):
            return False
        p = self.parametreler
        dk = d.tutulan_mum * self._tf_dk
        kar = d.kar_yuzde / 100.0
        tablo = self._tablo_roi(dk)
        if tablo is not None:
            min_roi = tablo
            if self._dz("trend", i) >= 0.5:
                min_roi = 100.0
                en_iyi = d.en_yuksek / d.giris_fiyati - 1.0
                if bool(p["droi_pullback"]) and kar < en_iyi - float(p["droi_pullback_amount"]):
                    min_roi = tablo if bool(p["droi_pullback_respect_table"]) else kar / 2.0
            if kar > min_roi:
                return True
        if kar < float(p["cstp_threshold"]):
            how = str(p["cstp_bail_how"])
            if how in ("roc", "any"):
                sroc = self._dz("sroc", i)
                if not math.isnan(sroc) and sroc / 100.0 <= float(p["cstp_bail_roc"]):
                    return True
            if how in ("time", "any") and dk > float(p["cstp_bail_time"]):
                return True
        return False


# ================================================================ B001:903
class WaveTrendB0903(Strateji):
    """HAM:B001:903 (4h, long; kaynak strategies/wavetrend/WaveTrendStra.py): ap = (yüksek + düşük + kapanış)/3; esa = EMA(10, ap); d = EMA(10,
    |ap - esa|); ci = (ap - esa)/(0,015 x d); wt1 = EMA(21, ci); wt2 = SMA(4, wt1). wt1 wt2'yi yukarı keser -> long; aşağı keser -> çıkış.
    ROI {0: 100} (kaynakta 'ROI kapalı': %10000, uygulanmaz); stop -%25."""

    ad, stil = "kapanis__wavetrend-b0903", "swing"
    varsayilan_parametreler = {"esa_n": 10, "d_n": 10, "ci_n": 21, "sinyal_n": 4, "sl": 0.25}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ap = _tipik(mumlar)
        esa = g.ema(ap, int(p["esa_n"]))
        d = g.ema((ap - esa).abs(), int(p["d_n"]))
        wt1 = g.ema((ap - esa) / (0.015 * d), int(p["ci_n"]))
        wt2 = g.sma(wt1, int(p["sinyal_n"]))
        sl = float(p["sl"])
        s = cerceve(mumlar, yukari(wt1, wt2), False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, asagi(wt1, wt2))


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [HmaWillrB0813, RsiSmaDurumB0816, Rsi30DemaB0817, Rsi30BbTemaB0843, ClucFiatSlowB0845, FrayCokluB0854,
            FisherTemaBbB0865, LamboObvWillrB0870, IkiMum4hB0875, IkiMumB0876, OtuzGunDipB0894, DynaBinB0899,
            WaveTrendB0903]

VARYANTLAR = [
    _v("HAM:B001:813", 1, HmaWillrB0813, "15m"),
    _v("HAM:B001:816", 1, RsiSmaDurumB0816, "15m"),
    _v("HAM:B001:817", 1, Rsi30DemaB0817, "1h"),
    _v("HAM:B001:843", 1, Rsi30BbTemaB0843, "15m"),
    _v("HAM:B001:845", 1, ClucFiatSlowB0845, "5m"),
    _v("HAM:B001:854", 1, FrayCokluB0854, "15m"),
    _v("HAM:B001:865", 1, FisherTemaBbB0865, "15m"),
    _v("HAM:B001:870", 1, LamboObvWillrB0870, "15m"),
    _v("HAM:B001:875", 1, IkiMum4hB0875, "1h"),
    _v("HAM:B001:876", 1, IkiMumB0876, "1h"),
    _v("HAM:B001:894", 1, OtuzGunDipB0894, "1h"),
    _v("HAM:B001:899", 1, DynaBinB0899, "5m"),
    _v("HAM:B001:903", 1, WaveTrendB0903, "4h"),
]

KODLANAMADI: list = []
