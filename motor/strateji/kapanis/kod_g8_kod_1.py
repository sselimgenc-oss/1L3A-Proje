"""Kapanış turu, kodlama partisi g8_kod_1 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_1.csv, 39 kaynak satırı).

Her sınıf kaynak satırın `kural_tam` metninden kendi cümleleriyle yazılmış bir uyarlamadır; üçüncü taraf kodu
kopyalanmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel (gelecek verisi yok);
üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa (ya da <= -%50 ise) stop = kapanış -/+ 3 x ATR(14) (ön kayıt uyarlaması).
- Kaynak yüzde stopu (örn. -%5) sinyal kapanışından hesaplanır; dolum sonraki açılıştan olduğu için gerçek mesafe
  biraz farklı olabilir.
- Freqtrade `minimal_roi` tablosu (dakika anahtarlı) `CikisAyarlari.azalan_roi` ile: mum sayısı = yukarı yuvarlanmış
  dakika / TF dakikası; hedef kâr kapanışta sınanır, çıkış sonraki açılışta (kaynakta mum içi). Tek basamaklı ROI
  (zaman yok) de aynı biçimde `azalan_roi = ((0, yüzde),)` ile (`RoiTek` karışımı; eskiden sinyaldeki limit `hedef`).
- Pozisyon bilinçli çıkışlar (41, 43: kapanış bazlı ATR izi) `kod_g8_modul` kancasıyla (pozisyon_cikisi).
- Freqtrade iz süren stop (`trailing_stop_positive` + offset) `geri_cekilme_yuzde` (iz) +
  `geri_cekilme_min_kar_yuzde` (offset) ile: kâr% farkı, kapanış bazlı (kaynakta fiyat ve mum içi).

KODLANAMADI satırları dosya sonundaki listededir (neden satır başına yazılı).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import obv as _obv
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, RoiTek, kapanis_iz_ihlali
from motor.strateji.seans_takvimi import mum_suresi
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _roi(tablo: dict, tf_dk: float) -> tuple:
    """{dakika: oran} -> ((mum, kâr%), ...). Aynı muma düşen basamaklarda büyük dakikalı olan geçerli (Freqtrade:
    süresi dolmuş en büyük anahtar)."""
    d = {}
    for dk in sorted(tablo):
        d[int(math.ceil(dk / tf_dk))] = round(float(tablo[dk]) * 100.0, 6)
    return tuple(sorted(d.items()))


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _ibs(m: pd.DataFrame) -> pd.Series:
    aralik = (m["yuksek"] - m["dusuk"]).where(lambda x: x > 0)
    return (m["kapanis"] - m["dusuk"]) / aralik


def _linreg_uc(seri: pd.Series, n: int) -> pd.Series:
    """Son n kapanışa en küçük kareler doğrusu; değer = doğrunun son mumdaki uç noktası (nedensel)."""
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xm = x.mean()
        w = 1.0 / n + (x - xm) * ((n - 1) / 2.0) / np.sum((x - xm) ** 2)
        out[n - 1:] = sliding_window_view(a, n) @ w
    return pd.Series(out, index=seri.index)


def _ust_rsi(m: pd.DataFrame, carpan: int, n: int) -> pd.Series:
    """Alt TF'nin `carpan` katı mumlardan RSI(n); yalnız kapanmış üst mumlar."""
    dk = mum_suresi(m.index) / pd.Timedelta(minutes=1)
    return ust_zaman(m, f"{int(round(dk * carpan))}m", lambda u: g.rsi(u["kapanis"], n))


# ================================================================ X005:6
class LinregAdxS0006(Strateji):
    """HAM:X005:6 (4h|1d, iki yön; Jesse benzeri): hızlı MA(5) yavaş MA(20)'yi yukarı keser VE ADX(8) > 13 -> long;
    aşağı keser VE ADX(8) > 13 -> short. MA = doğrusal regresyon uç noktası (linearreg). Çıkış: long iken hızlı <
    yavaş VE ADX(8) < 15; short iken hızlı > yavaş VE ADX(8) < 15. Stop 2xATR(32), hedef 5xATR(32).
    Uyarlama: stop/hedef sinyal kapanışından; kaynak riski %3 yerine motor riski."""

    ad, stil = "kapanis__linreg-adx-s0006", "swing"
    varsayilan_parametreler = {"ma_hizli": 5, "ma_yavas": 20, "adx_n": 8, "adx_giris": 13.0, "adx_cikis": 15.0,
                               "atr_n": 32, "stop_atr": 2.0, "hedef_atr": 5.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hz, yv = _linreg_uc(kap, int(p["ma_hizli"])), _linreg_uc(kap, int(p["ma_yavas"]))
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        ra, rh = float(p["stop_atr"]) * atr, float(p["hedef_atr"]) * atr
        al = yukari(hz, yv) & (adx > float(p["adx_giris"]))
        sat = asagi(hz, yv) & (adx > float(p["adx_giris"]))
        s = cerceve(mumlar, al, sat, kap - ra, kap + ra, hedef_l=kap + rh, hedef_s=kap - rh)
        low_adx = adx < float(p["adx_cikis"])
        return _bitir(s, (hz < yv) & low_adx, (hz > yv) & low_adx)


# ================================================================ X005:7
class Rsi2Sma200S0007(Strateji):
    """HAM:X005:7 (3h, iki yön): long: kapanış > SMA(200) VE RSI(2) <= 10; short: kapanış < SMA(200) VE RSI(2) >= 90.
    Long çıkış: kapanış SMA(5) üstüne çıkınca; short çıkış: kapanış SMA(5) altına inince. Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__rsi2-sma200-s0007", "swing"
    varsayilan_parametreler = {"rsi_n": 2, "os": 10.0, "ob": 90.0, "sma_kisa": 5, "sma_uzun": 200,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        uzun, kisa = g.sma(kap, int(p["sma_uzun"])), g.sma(kap, int(p["sma_kisa"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (kap > uzun) & (r <= float(p["os"])), (kap < uzun) & (r >= float(p["ob"])),
                    kap - mes, kap + mes)
        return _bitir(s, kap > kisa, kap < kisa)


# ================================================================ X005:9
class BbHl2IchimokuS0009(Strateji):
    """HAM:X005:9 (1h, long): Bollinger(20, 2) HL2 serisi üzerinde; kapanış üst bandın üstünde VE kapanış Ichimoku
    (9/26/52/26) bulutunun üstünde -> long (durum); kapanış orta bandın altına inince kapat. Stop yok: ATR(14)x3.
    Uyarlama: 'kapanış (hl2 kaynaklı)' = bantlar HL2'den, karşılaştırma kapanışla (lider notu)."""

    ad, stil = "kapanis__bb-hl2-ichimoku-s0009", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydir": 26,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hl2 = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        bb = g.bollinger(hl2, int(p["bb_n"]), float(p["bb_k"]))
        ich = b2.ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]),
                          int(p["senkou_b"]), int(p["kaydir"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (kap > bb["ust"]) & (kap > ich["bulut_ust"]), False, kap - mes, kap + mes)
        return _bitir(s, kap < bb["orta"])


# ================================================================ X005:10
class RsiTradingViewS0010(RoiTek, Strateji):
    """HAM:X005:10 (1h, long): RSI(5) 35'i yukarı keser -> long. Çıkış: RSI(5) 75'i aşağı keser VEYA 10'u aşağı keser
    (acil) VEYA +%10 kâr (ROI, azalan_roi ((0, 10),)); sabit stop -%5."""

    roi_anahtar = "tp"
    ad, stil = "kapanis__rsi5-tv-s0010", "swing"
    varsayilan_parametreler = {"rsi_n": 5, "giris": 35.0, "cikis_ust": 75.0, "cikis_acil": 10.0,
                               "tp": 0.10, "sl": 0.05}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        s = cerceve(mumlar, yukari(r, float(p["giris"])), False, kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, asagi(r, float(p["cikis_ust"])) | asagi(r, float(p["cikis_acil"])))


# ================================================================ X005:12
class RsiBbTipikS0012(RoiTek, Strateji):
    """HAM:X005:12 (1h, long): RSI(14) < 30 VE kapanış < Bollinger(20, 2s; TİPİK fiyat) alt bandı (aynı mumda) -> long;
    çıkış RSI > 70 ya da ROI %10 (azalan_roi); sabit stop -%25."""

    ad, stil = "kapanis__rsi-bb-tipik-s0012", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 30.0, "rsi_cik": 70.0, "bb_n": 20, "bb_k": 2.0,
                               "roi": 0.10, "sl": 0.25}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        s = cerceve(mumlar, (r < float(p["rsi_alt"])) & (kap < bb["alt"]), False,
                    kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, r > float(p["rsi_cik"]))


# ================================================================ X005:15
class ClucMayS0015(RoiTek, Strateji):
    """HAM:X005:15 (5m, long): kapanış < EMA(50) VE kapanış < 0,985 x Bollinger(20, 2s; tipik fiyat) alt bandı VE
    hacim < 20 x önceki 30 mumun ortalama hacmi -> long. Çıkış: kapanış > BB orta bandı ya da kâr >= %1 (ROI, azalan_roi);
    sabit stop -%5."""

    roi_anahtar = "tp"
    ad, stil = "kapanis__cluc-may-s0015", "daytrade"
    varsayilan_parametreler = {"ema_n": 50, "bb_n": 20, "bb_k": 2.0, "bb_carpan": 0.985, "hacim_n": 30,
                               "hacim_k": 20.0, "tp": 0.01, "sl": 0.05}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        hort = mumlar["hacim"].rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean().shift(1)
        al = ((kap < g.ema(kap, int(p["ema_n"]))) & (kap < float(p["bb_carpan"]) * bb["alt"])
              & (mumlar["hacim"] < float(p["hacim_k"]) * hort))
        s = cerceve(mumlar, al, False, kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, kap > bb["orta"])


# ================================================================ X005:16
class MultiRsiS0016(RoiTek, Strateji):
    """HAM:X005:16 (5m, long): SMA(5) >= SMA(200) VE RSI(14) < RSI_8x(14) - 20 (RSI_8x: 8 kat (40m) süreli KAPANMIŞ üst
    mumların RSI(14)'ü) -> long. Çıkış: RSI(14) hem 2x (10m) hem 8x (40m) RSI'ların üstüne çıkınca. ROI +%1 (azalan_roi),
    sabit stop -%5. Üst TF yalnız htf.ust_zaman ile (nedensel)."""

    ad, stil = "kapanis__multi-rsi-s0016", "daytrade"
    varsayilan_parametreler = {"sma_kisa": 5, "sma_uzun": 200, "rsi_n": 14, "fark": 20.0, "carpan_a": 2,
                               "carpan_b": 8, "roi": 0.01, "sl": 0.05}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        ra = _ust_rsi(mumlar, int(p["carpan_a"]), int(p["rsi_n"]))
        rb = _ust_rsi(mumlar, int(p["carpan_b"]), int(p["rsi_n"]))
        al = (g.sma(kap, int(p["sma_kisa"])) >= g.sma(kap, int(p["sma_uzun"]))) & (r < rb - float(p["fark"]))
        s = cerceve(mumlar, al, False, kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, (r > ra) & (r > rb))


# ================================================================ X005:18
class BandtasticS0018(Strateji):
    """HAM:X005:18 (15m, long): kapanış < Bollinger(20, 1s; tipik fiyat) alt bandı VE hacim > 0 -> long (diğer filtreler
    kapalı). Çıkış: MFI(14) > 46 VE kapanış > Bollinger(20, 2s; tipik fiyat) üst bandı. ROI {0dk %16,2; 69 %9,7;
    229 %6,1; 566 0}; sabit stop -%34,5; iz süren %1 (offset %5,8).
    Uyarlama: 2s üst bant da tipik fiyattan (kaynakta tek bant gösterge ailesi)."""

    ad, stil = "kapanis__bandtastic-s0018", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_giris_k": 1.0, "bb_cikis_k": 2.0, "mfi_n": 14, "mfi_esik": 46.0,
                               "sl": 0.345}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.162, 69: 0.097, 229: 0.061, 566: 0.0}, 15),
        geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=5.8)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        alt = g.bollinger(tp, int(p["bb_n"]), float(p["bb_giris_k"]))["alt"]
        ust = g.bollinger(tp, int(p["bb_n"]), float(p["bb_cikis_k"]))["ust"]
        mf = _mfi(mumlar["yuksek"], mumlar["dusuk"], kap, mumlar["hacim"], int(p["mfi_n"]))
        s = cerceve(mumlar, (kap < alt) & (mumlar["hacim"] > 0), False,
                    kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, (mf > float(p["mfi_esik"])) & (kap > ust))


# ================================================================ X005:19
class HaEmaS0019(Strateji):
    """HAM:X005:19 (5m, long): EMA(20) EMA(50)'yi yukarı keser VE Heikin-Ashi kapanış > EMA(20) VE HA mumu yeşil -> long.
    Çıkış: EMA(50) EMA(100)'ü yukarı keserken HA kapanış < EMA(20) VE HA mumu kırmızı. ROI {0dk %5; 20 %4; 30 %3;
    60 %1}; sabit stop -%10."""

    ad, stil = "kapanis__ha-ema-s0019", "daytrade"
    varsayilan_parametreler = {"ema_a": 20, "ema_b": 50, "ema_c": 100, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 20: 0.04, 30: 0.03, 60: 0.01}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ha = b2.heikin_ashi(mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], kap)
        ea, eb, ec = (g.ema(kap, int(p[k])) for k in ("ema_a", "ema_b", "ema_c"))
        yesil = ha["ha_kapanis"] > ha["ha_acilis"]
        al = yukari(ea, eb) & (ha["ha_kapanis"] > ea) & yesil
        cik = yukari(eb, ec) & (ha["ha_kapanis"] < ea) & (ha["ha_kapanis"] < ha["ha_acilis"])
        s = cerceve(mumlar, al, False, kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, cik)


# ================================================================ X005:23
class HlhbS0023(Strateji):
    """HAM:X005:23 (4h, long): AYNI mumda RSI(10; fiyat=(açılış+kapanış)/2) 50'yi yukarı keser VE EMA(5) EMA(10)'u
    yukarı keser VE ADX(14) > 25 -> long. Çıkış: RSI 50'yi aşağı keser VE EMA5 EMA10'u aşağı keser VE ADX > 25.
    ROI {0dk %62,25; 703 %21,87; 2849 %3,63; 5520 0}; sabit stop -%32,11; iz süren %1,17 (offset %1,86)."""

    ad, stil = "kapanis__hlhb-s0023", "swing"
    varsayilan_parametreler = {"rsi_n": 10, "rsi_esik": 50.0, "ema_a": 5, "ema_b": 10, "adx_n": 14,
                               "adx_esik": 25.0, "sl": 0.3211}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.6225, 703: 0.2187, 2849: 0.0363, 5520: 0.0}, 240),
        geri_cekilme_yuzde=1.17, geri_cekilme_min_kar_yuzde=1.86)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi((mumlar["acilis"] + kap) / 2.0, int(p["rsi_n"]))
        ea, eb = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"] > float(p["adx_esik"])
        al = yukari(r, float(p["rsi_esik"])) & yukari(ea, eb) & adx
        cik = asagi(r, float(p["rsi_esik"])) & asagi(ea, eb) & adx
        s = cerceve(mumlar, al, False, kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, cik)


# ================================================================ X005:24
class AdxSmasS0024(RoiTek, Strateji):
    """HAM:X005:24 (1h, long): ADX(14) > 25 VE SMA(3) SMA(6)'yı yukarı keser -> long. Çıkış: ADX(14) < 25 VE SMA(6)
    SMA(3)'ü yukarı keser (ters kesişim). ROI %10 (azalan_roi); sabit stop -%25."""

    ad, stil = "kapanis__adx-smas-s0024", "swing"
    varsayilan_parametreler = {"adx_n": 14, "adx_esik": 25.0, "sma_a": 3, "sma_b": 6, "roi": 0.10, "sl": 0.25}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        sa, sb = g.sma(kap, int(p["sma_a"])), g.sma(kap, int(p["sma_b"]))
        s = cerceve(mumlar, (adx > float(p["adx_esik"])) & yukari(sa, sb), False,
                    kap * (1 - float(p["sl"])), kap * (1 + float(p["sl"])))
        return _bitir(s, (adx < float(p["adx_esik"])) & yukari(sb, sa))


# ================================================================ X005:25
class EmaObvS0025(Strateji):
    """HAM:X005:25 (5m, iki yön): long: kapanış EMA(20)'yi yukarı keser VE OBV artıyor (OBV[t] > OBV[t-1]); short: aşağı
    keser VE OBV azalıyor. Çıkış long: kapanış EMA(20)'nin altına iner VE OBV artıyor (kaynaktaki garip koşul korunur);
    short ayna (yukarı keser VE OBV azalıyor). ROI {0dk %15; 30 %10; 60 %5}; sabit stop -%26,5; iz süren %5 (offset %10).
    Uyarlama: 'altına iner / üstüne çıkar' kesişim olayı olarak okundu."""

    ad, stil = "kapanis__ema-obv-s0025", "daytrade"
    varsayilan_parametreler = {"ema_n": 20, "sl": 0.265}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.15, 30: 0.10, 60: 0.05}, 5),
        geri_cekilme_yuzde=5.0, geri_cekilme_min_kar_yuzde=10.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ema = g.ema(kap, int(p["ema_n"]))
        obv = _obv(kap, mumlar["hacim"])
        artiyor, azaliyor = obv > obv.shift(1), obv < obv.shift(1)
        yk, ak = yukari(kap, ema), asagi(kap, ema)
        sl = float(p["sl"])
        s = cerceve(mumlar, yk & artiyor, ak & azaliyor, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, ak & artiyor, yk & azaliyor)


# ================================================================ X005:27
class AdxSma1248S0027(Strateji):
    """HAM:X005:27 (1h, iki yön): ADX(14) > 30 VE SMA(12) SMA(48)'i yukarı keser -> long; aşağı keser -> short. Çıkış:
    ADX(14) < 30 olunca (her iki yön). ROI {0dk %5; 30 %10; 60 %7,5}; sabit stop -%5.
    Uyarlama: 1h mumda 30. dk basamağı ile 60. dk aynı muma düşer; Freqtrade gibi büyük anahtar (%7,5) geçerli."""

    ad, stil = "kapanis__adx-sma1248-s0027", "swing"
    varsayilan_parametreler = {"adx_n": 14, "adx_esik": 30.0, "sma_a": 12, "sma_b": 48, "sl": 0.05}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 30: 0.10, 60: 0.075}, 60))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        sa, sb = g.sma(kap, int(p["sma_a"])), g.sma(kap, int(p["sma_b"]))
        guclu = adx > float(p["adx_esik"])
        sl = float(p["sl"])
        s = cerceve(mumlar, guclu & yukari(sa, sb), guclu & asagi(sa, sb), kap * (1 - sl), kap * (1 + sl),
                    cikis=adx < float(p["adx_esik"]))
        return s


# ================================================================ X005:28
class UcSupertrendS0028(Strateji):
    """HAM:X005:28 (1h, long): üç al-Supertrend (çarpan/periyot 4/8, 7/9, 1/8) aynı anda yükselişte VE hacim > 0 -> long;
    üç sat-Supertrend (1/16, 3/18, 6/18) hepsi düşüşte -> çıkış. ROI {0dk %8,7; 372 %5,8; 861 %2,9; 2221 0};
    sabit stop -%26,5; iz süren %5 (offset %14,4). Durum tabanlı (kaynak sütunları 'up/down' durumu)."""

    ad, stil = "kapanis__uc-supertrend-s0028", "swing"
    varsayilan_parametreler = {"al_st": ((8, 4.0), (9, 7.0), (8, 1.0)), "sat_st": ((16, 1.0), (18, 3.0), (18, 6.0)),
                               "sl": 0.265}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(
        azalan_roi=_roi({0: 0.087, 372: 0.058, 861: 0.029, 2221: 0.0}, 60),
        geri_cekilme_yuzde=5.0, geri_cekilme_min_kar_yuzde=14.4)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        h, l = mumlar["yuksek"], mumlar["dusuk"]

        def hepsi(liste, yon):
            durum = pd.Series(True, index=mumlar.index)
            for per, car in liste:
                durum &= g.supertrend(h, l, kap, int(per), float(car))["yon"] == yon
            return durum

        sl = float(p["sl"])
        s = cerceve(mumlar, hepsi(p["al_st"], 1) & (mumlar["hacim"] > 0), False,
                    kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, hepsi(p["sat_st"], -1))


# ================================================================ X005:29
class CofibitS0029(Strateji):
    """HAM:X005:29 (5m, long): açılış < EMA(5; düşük) VE hızlı Stokastik(5,3) fastk fastd'yi yukarı keser VE fastk < 25 VE
    fastd < 25 VE ADX(14) > 25 -> long. Çıkış: açılış >= EMA(5; yüksek) VEYA fastk ya da fastd 75'i yukarı keser.
    ROI {0dk %10; 20 %7; 30 %6; 40 %5}; sabit stop -%25."""

    ad, stil = "kapanis__cofibit-s0029", "daytrade"
    varsayilan_parametreler = {"ema_n": 5, "stok_k": 5, "stok_d": 3, "stok_alt": 25.0, "stok_ust": 75.0,
                               "adx_n": 14, "adx_esik": 25.0, "sl": 0.25}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.10, 20: 0.07, 30: 0.06, 40: 0.05}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        st = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["stok_k"]), int(p["stok_d"]))
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        ema_l, ema_h = g.ema(mumlar["dusuk"], int(p["ema_n"])), g.ema(mumlar["yuksek"], int(p["ema_n"]))
        al = ((ac < ema_l) & yukari(st["k"], st["d"]) & (st["k"] < float(p["stok_alt"]))
              & (st["d"] < float(p["stok_alt"])) & (adx > float(p["adx_esik"])))
        ust = float(p["stok_ust"])
        cik = (ac >= ema_h) | yukari(st["k"], ust) | yukari(st["d"], ust)
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


# ================================================================ X005:30
class Ema821Ust48S0030(RoiTek, Strateji):
    """HAM:X005:30 (4h, long): EMA(8) EMA(21)'i yukarı keser VE kapanış > SMA(50) (48 saatlik = 12 adet 4h mumdan oluşan
    üst TF serisinin kapanışlarından) -> long. Çıkış: EMA(8) EMA(21)'in altına keserek iner VEYA ROI %50 (azalan_roi); sabit stop
    -%20. Uyarlama: 48h mumlar UTC epoch'a hizalı (htf.ust_zaman), yalnız kapanmış 48h mumlar kullanılır; kapanış
    karşılaştırması 4h kapanışla."""

    ad, stil = "kapanis__ema821-ust48-s0030", "swing"
    varsayilan_parametreler = {"ema_a": 8, "ema_b": 21, "ust_tf": "48h", "ust_sma": 50, "roi": 0.50, "sl": 0.20}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ea, eb = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        ust_sma = ust_zaman(mumlar, str(p["ust_tf"]), lambda u: g.sma(u["kapanis"], int(p["ust_sma"])))
        sl = float(p["sl"])
        s = cerceve(mumlar, yukari(ea, eb) & (kap > ust_sma), False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, asagi(ea, eb))


# ================================================================ X005:36
class AralikKirilimS0036(Strateji):
    """HAM:X005:36 (30m, iki yön; QuantConnect SPY kaynağı): aralık = max(HH-LC, HC-LL) son 20 mum (HH en yüksek yüksek,
    LC en düşük kapanış, HC en yüksek kapanış, LL en düşük düşük; geçmiş 20 mum, bu mum hariç); üst = önceki mum
    kapanışı + 0,63 x aralık; alt = önceki mum kapanışı - 0,63 x aralık. Kapanış üstü aşarsa long, altı aşarsa short;
    zıt koşulda pozisyon çevrilir; pozisyon 5 gün sonra sona erer (zaman çıkışı); stop giriş -/+ %3.
    'Long değilse' koşulu motorda doğal (açık pozisyonda yeni giriş yok)."""

    ad, stil = "kapanis__aralik-kirilim-s0036", "daytrade"
    varsayilan_parametreler = {"aralik_bar": 20, "k1": 0.63, "k2": 0.63, "sure_gun": 5.0, "sl": 0.03}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        n = int(p["aralik_bar"])
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        hh = yuk.rolling(n, min_periods=n).max()
        ll = dus.rolling(n, min_periods=n).min()
        hc = kap.rolling(n, min_periods=n).max()
        lc = kap.rolling(n, min_periods=n).min()
        aralik = pd.concat([hh - lc, hc - ll], axis=1).max(axis=1).shift(1)
        cap = kap.shift(1)
        ust, alt = cap + float(p["k1"]) * aralik, cap - float(p["k2"]) * aralik
        al, sat = kap > ust, kap < alt
        sl = float(p["sl"])
        s = cerceve(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))
        s = _bitir(s, sat, al)   # zıt koşul: pozisyon çevrilir
        bar_sn = mum_suresi(mumlar.index).total_seconds()
        s["zaman_cikisi_mum"] = float(round(float(p["sure_gun"]) * 86400.0 / bar_sn))
        return s


# ================================================================ X005:37
class MacdTolS0037(Strateji):
    """HAM:X005:37 (1d, long): (MACD - sinyal) / EMA(12) > +0,0025 ise long; < -0,0025 ise düz; eşikler arasında pozisyon
    korunur. Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__macd-tolerans-s0037", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "tolerans": 0.0025, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        oran = (mc["macd"] - mc["sinyal"]) / g.ema(kap, int(p["hizli"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, oran > float(p["tolerans"]), False, kap - mes, kap + mes)
        return _bitir(s, oran < -float(p["tolerans"]))


# ================================================================ X005:38
class EmaBantS0038(Strateji):
    """HAM:X005:38 (1d, long): pozisyon yokken EMA(15) > EMA(30) x 1,00015 ise long (durum; yalnız kesişimde değil);
    EMA(15) < EMA(30) olunca çık. Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__ema-bant-s0038", "swing"
    varsayilan_parametreler = {"ema_a": 15, "ema_b": 30, "bant": 1.00015, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ea, eb = g.ema(kap, int(p["ema_a"])), g.ema(kap, int(p["ema_b"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, ea > eb * float(p["bant"]), False, kap - mes, kap + mes)
        return _bitir(s, ea < eb)


# ================================================================ X005:41
class MacdSmaIzS0041(KancaDestek, Strateji):
    """HAM:X005:41 (1d, long): MACD(12,26,9) sinyali yukarı keser VE SMA(30) - SMA(30)[10] < 0 (düşen SMA30) -> long.
    Çıkış: kapanış, kapanış - 3xATR(14) iz süren stopunun (yalnız yukarı taşınır) altına inerse: KAPANIŞ BAZLI iz, kancada
    (kapanis_iz_ihlali: giriş sinyali mumundan beri en büyük (kapanış_j - 3xATR_j); kapanış ona eşit/altındaysa çık).
    Kaynakta stop yalnız bu iz; zorunlu felaket stopu ATR(14)x3 sinyal kapanışından (uyarlama)."""

    ad, stil = "kapanis__macd-sma-iz-s0041", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "sma": 30, "dir": 10, "atr_n": 14, "iz_k": 3.0,
                               "felaket_n": 14, "felaket_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        sma = g.sma(kap, int(p["sma"]))
        mes = _atr_mesafe(mumlar, int(p["felaket_n"]), float(p["felaket_k"]))
        al = yukari(mc["macd"], mc["sinyal"]) & ((sma - sma.shift(int(p["dir"]))) < 0)
        self._sakla(kap=kap, atr=g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"])))
        return cerceve(mumlar, al, False, kap - mes, kap + mes)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, d.mum_indeksi,
                                 float(self.parametreler["iz_k"]), 1, False)


# ================================================================ X005:43
class SmaKesIzS0043(KancaDestek, Strateji):
    """HAM:X005:43 (1d, long): SMA(10) SMA(25)'i yukarı keser -> long. Çıkış YALNIZ 2xATR(100) iz süren stop (ters
    kesişimde çıkış yok); stop tetiklenince sonraki yukarı kesişimde yeniden giriş. İz KAPANIŞ BAZLI, kancada
    (giriş sinyali mumundan beri en büyük (kapanış_j - 2xATR(100)_j); kapanış ona eşit/altındaysa çık). Zorunlu felaket stopu
    ATR(14)x3 sinyal kapanışından (uyarlama)."""

    ad, stil = "kapanis__sma-kesis-iz-s0043", "swing"
    varsayilan_parametreler = {"hizli": 10, "yavas": 25, "atr_n": 100, "iz_k": 2.0, "felaket_n": 14, "felaket_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        mes = _atr_mesafe(mumlar, int(p["felaket_n"]), float(p["felaket_k"]))
        al = yukari(g.sma(kap, int(p["hizli"])), g.sma(kap, int(p["yavas"])))
        self._sakla(kap=kap, atr=g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"])))
        return cerceve(mumlar, al, False, kap - mes, kap + mes)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, d.mum_indeksi,
                                 float(self.parametreler["iz_k"]), 1, False)


# ================================================================ X005:51
class Rsi4DonusS0051(Strateji):
    """HAM:X005:51 (4h, iki yön, dur-ve-ters; K6 standart): RSI(4) 35'in altından yukarı keserse long; 75'in üstünden
    aşağı keserse short; ters sinyal mevcut pozisyonu kapatıp ters açar. Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__rsi4-donus-s0051", "swing"
    varsayilan_parametreler = {"rsi_n": 4, "asiri_satim": 35.0, "asiri_alim": 75.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        al, sat = yukari(r, float(p["asiri_satim"])), asagi(r, float(p["asiri_alim"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, sat, al)


# ================================================================ X005:54
class IbsEma252S0054(Strateji):
    """HAM:X005:54 (1d, long): IBS = (kapanış - düşük)/(yüksek - düşük) < 0,2 VE kapanış > EMA(252) ise long; IBS > 0,9
    olunca kapat. Stop yok: ATR(14)x3. (Asgari mesafe / azami süre seçenekleri kullanılmaz.)"""

    ad, stil = "kapanis__ibs-ema252-s0054", "swing"
    varsayilan_parametreler = {"ibs_alt": 0.2, "ibs_ust": 0.9, "ema": 252, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ibs = _ibs(mumlar)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (ibs < float(p["ibs_alt"])) & (kap > g.ema(kap, int(p["ema"]))), False,
                    kap - mes, kap + mes)
        return _bitir(s, ibs > float(p["ibs_ust"]))


# ================================================================ X005:56
class Rsi14SeviyeS0056(Strateji):
    """HAM:X005:56 (4h|1d, long; K6 standart RSI 14): RSI(14) <= 30 iken (pozisyonsuzsa) long; RSI >= 70 olunca çık.
    Kaynağın opsiyonel %2 stopu yerine zorunlu ATR(14)x3."""

    ad, stil = "kapanis__rsi14-seviye-s0056", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30.0, "rsi_cik": 70.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, r <= float(p["rsi_al"]), False, kap - mes, kap + mes)
        return _bitir(s, r >= float(p["rsi_cik"]))


# ================================================================ X005:67
class RsiH1D1S0067(Strateji):
    """HAM:X005:67 (1h + 1d teyit, iki yön, durum tabanlı çevirme): RSI_H1 = RSI(12) (kapanmış 1h), RSI_D1 = RSI(18) (son
    KAPANMIŞ günlük mum; htf.ust_zaman). Long: RSI_H1 >= 20 ve bir öncekinden büyük VE RSI_D1 >= 20 ve bir önceki
    günlükten büyük -> long aç (short varsa kapat). Short: RSI_H1 <= 80 ve düşüyor VE RSI_D1 <= 80 ve düşüyor -> short
    aç (long kapat). Kaynakta stop/TP yok: ATR(14)x3."""

    ad, stil = "kapanis__rsi-h1-d1-s0067", "swing"
    varsayilan_parametreler = {"rsi_h1": 12, "rsi_d1": 18, "lvl_up": 80.0, "lvl_dw": 20.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r1 = g.rsi(kap, int(p["rsi_h1"]))

        def gunluk(u):
            r = g.rsi(u["kapanis"], int(p["rsi_d1"]))
            return pd.DataFrame({"r": r, "onceki": r.shift(1)})

        d = ust_zaman(mumlar, "1d", gunluk)
        al = ((r1 >= float(p["lvl_dw"])) & (r1 > r1.shift(1)) & (d["r"] >= float(p["lvl_dw"])) & (d["r"] > d["onceki"]))
        sat = ((r1 <= float(p["lvl_up"])) & (r1 < r1.shift(1)) & (d["r"] <= float(p["lvl_up"])) & (d["r"] < d["onceki"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, sat, al)


# ================================================================ X005:70
class MaIbsS0070(Strateji):
    """HAM:X005:70 (1d, iki yön): IBS = (C-L)/(H-L); maIBS = SMA(IBS, 3); maIBS 0,3'ün altına keserse long; 0,75'in üstüne
    keserse short (kaynak metin 'buy' yazıyor, yazım hatası: short alındı). 1 gün tutma (zaman çıkışı, 1 gün =
    günlük mumda 1 mum; kripto 7/24'te giriş gününün kapanışına denk). Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__ma-ibs-s0070", "swing"
    varsayilan_parametreler = {"ibs_ort_n": 3, "long_esik": 0.3, "short_esik": 0.75, "tutma_gun": 1.0,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ma = g.sma(_ibs(mumlar), int(p["ibs_ort_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, asagi(ma, float(p["long_esik"])), yukari(ma, float(p["short_esik"])),
                    kap - mes, kap + mes)
        bar_sn = mum_suresi(mumlar.index).total_seconds()
        s["zaman_cikisi_mum"] = float(max(1, round(float(p["tutma_gun"]) * 86400.0 / bar_sn)))
        return s


# ================================================================ X005:73
class AoWmaDunS0073(Strateji):
    """HAM:X005:73 (1h, iki yön; MetaTrader EURUSD kaynağı, WMA kapanış / AO 5-34 standart = K6): LONG kurulumu: iki mum
    önceki açılış < WMA(14) VE Awesome Oscillator düşüyor VE 3 gün önceki GÜNLÜK mumun düşüğü L kapanışın üstünde ->
    seviye = L; emir 12 mum canlı; 12 mum içinde bir 1h kapanışı L'nin üstünde ise sonraki açılışta long (uyarlama d:
    seviye kapanışla aşılınca). SHORT ayna (açılış > WMA14, AO yükseliyor, 3 gün önceki günlük YÜKSEK kapanışın
    altında, kapanış seviyenin altına inince). TP = giriş x %0,7; stop = 1,5 x ATR(24). Başabaş/iz yok.
    Uyarlama: WMA değeri kurulum mumundaki (güncel) WMA; günlük mumlar htf.ust_zaman ile (kapanmış, takvim günü
    kaydırmalı: 3 gün önceki takvim günü)."""

    ad, stil = "kapanis__ao-wma-dun-s0073", "daytrade"
    varsayilan_parametreler = {"wma_n": 14, "ao_hizli": 5, "ao_yavas": 34, "gun_geri": 3, "emir_omru_bar": 12,
                               "tp_pct": 0.7, "sl_atr_n": 24, "sl_atr_k": 1.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _tetik(kurulum: np.ndarray, seviye: np.ndarray, kap: np.ndarray, omur: int, yon: int) -> np.ndarray:
        """Canlı emir: kurulum mumundan sonraki `omur` mum içinde kapanış seviyeyi (yon=1: üstüne, -1: altına) aşarsa
        tetik. Yeni kurulum eski emrin yerini alır."""
        n = len(kap)
        out = np.zeros(n, bool)
        seviye_s, yas = np.nan, 0
        for t in range(n):
            if not np.isnan(seviye_s):
                yas += 1
                if yas > omur:
                    seviye_s = np.nan
                elif (kap[t] - seviye_s) * yon > 0:
                    out[t] = True
                    seviye_s = np.nan
            if kurulum[t] and not np.isnan(seviye[t]):
                seviye_s, yas = seviye[t], 0
        return out

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        gun = int(p["gun_geri"])

        def gunluk(u):
            d = pd.DataFrame({"l": u["dusuk"], "h": u["yuksek"]}).asfreq("1D")
            return d.shift(gun - 1)

        dg = ust_zaman(mumlar, "1d", gunluk)
        wma = _wma(kap, int(p["wma_n"]))
        med = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        ao = g.sma(med, int(p["ao_hizli"])) - g.sma(med, int(p["ao_yavas"]))
        k_long = ((ac.shift(2) < wma) & (ao < ao.shift(1)) & (dg["l"] > kap)).fillna(False).to_numpy(bool)
        k_short = ((ac.shift(2) > wma) & (ao > ao.shift(1)) & (dg["h"] < kap)).fillna(False).to_numpy(bool)
        omur = int(p["emir_omru_bar"])
        kv = kap.to_numpy(float)
        al = pd.Series(self._tetik(k_long, dg["l"].to_numpy(float), kv, omur, 1), index=mumlar.index)
        sat = pd.Series(self._tetik(k_short, dg["h"].to_numpy(float), kv, omur, -1), index=mumlar.index)
        mes = float(p["sl_atr_k"]) * g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["sl_atr_n"]))
        tp = float(p["tp_pct"]) / 100.0
        return cerceve(mumlar, al, sat, kap - mes, kap + mes, hedef_l=kap * (1 + tp), hedef_s=kap * (1 - tp))


# ================================================================ X005:74
class IbsPazartesiS0074(Strateji):
    """HAM:X005:74 (1d, long): Pazartesi (UTC gün) kapanışı önceki gün (Pazar) kapanışından düşük VE IBS <= 0,25 VE kapanış
    < SMA(180) ise Pazartesi kapanışında al; Çarşamba günlük kapanışında kapat; giriş fiyatının %10 altında stop; TP yok.
    Uyarlama: kriptoda 'önceki işlem günü' = Pazar (7/24); sinyal Pazartesi mumunda, dolum ertesi açılıştan."""

    ad, stil = "kapanis__ibs-pazartesi-s0074", "swing"
    varsayilan_parametreler = {"gun": 0, "ibs_max": 0.25, "sma_n": 180, "cikis_gun": 2, "stop_yuzde": 0.10}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        gun = pd.Series(mumlar.index.dayofweek, index=mumlar.index)
        al = ((gun == int(p["gun"])) & (kap < kap.shift(1)) & (_ibs(mumlar) <= float(p["ibs_max"]))
              & (kap < g.sma(kap, int(p["sma_n"]))))
        sl = float(p["stop_yuzde"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, gun == int(p["cikis_gun"]))


# ================================================================ X005:81
class SmaKesisDonS0081(Strateji):
    """HAM:X005:81 (4h, iki yön, dur-ve-ters; K6 SMA): SMA(5) SMA(10)'u yukarı keserse long, aşağı keserse short; ters
    sinyal pozisyonu kapatıp ters açar. Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__sma-kesis-don-s0081", "swing"
    varsayilan_parametreler = {"hizli": 5, "yavas": 10, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        a, b = g.sma(kap, int(p["hizli"])), g.sma(kap, int(p["yavas"]))
        al, sat = yukari(a, b), asagi(a, b)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, sat, al)


# ================================================================ X005:84
class MacdHaftalikS0084(Strateji):
    """HAM:X005:84 (1d, long; K6 MACD 12/26/9): son KAPANMIŞ haftalık MACD(12,26,9) > sinyal iken pencere açık; pencerede
    günlük MACD sinyali yukarı kesip o gün sinyalin üstünde kapanırsa sonraki açılışta long; stop = sinyal mumunun
    düşüğü; çıkış: günlük MACD sinyali aşağı kesip altında kapanınca; kâr al yok. Haftalık seri htf.ust_zaman('1w')
    ile (Pazartesi hizalı, kapanmış hafta)."""

    ad, stil = "kapanis__macd-haftalik-s0084", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        h, y, sg = int(p["hizli"]), int(p["yavas"]), int(p["sinyal"])
        mc = g.macd(kap, h, y, sg)
        haftalik = ust_zaman(mumlar, "1w", lambda u: g.macd(u["kapanis"], h, y, sg)["histogram"])
        al = yukari(mc["macd"], mc["sinyal"]) & (haftalik > 0)
        return _bitir(cerceve(mumlar, al, False, mumlar["dusuk"], mumlar["dusuk"]),
                      asagi(mc["macd"], mc["sinyal"]))


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [LinregAdxS0006, Rsi2Sma200S0007, BbHl2IchimokuS0009, RsiTradingViewS0010,
            RsiBbTipikS0012, ClucMayS0015, MultiRsiS0016, BandtasticS0018, HaEmaS0019, HlhbS0023, AdxSmasS0024,
            EmaObvS0025, AdxSma1248S0027, UcSupertrendS0028, CofibitS0029, Ema821Ust48S0030, AralikKirilimS0036,
            MacdTolS0037, EmaBantS0038, MacdSmaIzS0041, SmaKesIzS0043, Rsi4DonusS0051, IbsEma252S0054,
            Rsi14SeviyeS0056, RsiH1D1S0067, MaIbsS0070, AoWmaDunS0073, IbsPazartesiS0074, SmaKesisDonS0081,
            MacdHaftalikS0084]

VARYANTLAR = [
    # X005:5 = jesse_kaynak.MacdEmaS0005 ile aynı hipotez (MACD > sinyal VE kapanış > EMA100, 1h long): yeni sınıf yazılmadı,
    # mevcut sınıfa bağlı tek kayıt (modul alanı sınıfın bulunduğu modülü gösterir).
    {"kimlik": "HAM:X005:5#v1", "sinif": "kapanis__macd-ema-s0005",
     "parametreler": {"ema_n": 100, "macd_hizli": 12, "macd_yavas": 26, "macd_sinyal": 9, "atr_n": 14, "atr_k": 3.0},
     "tf": "1h", "modul": "motor.strateji.kapanis.jesse_kaynak"},
    _v("HAM:X005:6", 1, LinregAdxS0006, "4h"),
    _v("HAM:X005:6", 2, LinregAdxS0006, "1d"),
    _v("HAM:X005:7", 1, Rsi2Sma200S0007, "3h"),
    _v("HAM:X005:9", 1, BbHl2IchimokuS0009, "1h"),
    _v("HAM:X005:10", 1, RsiTradingViewS0010, "1h"),
    _v("HAM:X005:12", 1, RsiBbTipikS0012, "1h"),
    _v("HAM:X005:15", 1, ClucMayS0015, "5m"),
    _v("HAM:X005:16", 1, MultiRsiS0016, "5m"),
    _v("HAM:X005:18", 1, BandtasticS0018, "15m"),
    _v("HAM:X005:19", 1, HaEmaS0019, "5m"),
    _v("HAM:X005:23", 1, HlhbS0023, "4h"),
    _v("HAM:X005:24", 1, AdxSmasS0024, "1h"),
    _v("HAM:X005:25", 1, EmaObvS0025, "5m"),
    _v("HAM:X005:27", 1, AdxSma1248S0027, "1h"),
    _v("HAM:X005:28", 1, UcSupertrendS0028, "1h"),
    _v("HAM:X005:29", 1, CofibitS0029, "5m"),
    _v("HAM:X005:30", 1, Ema821Ust48S0030, "4h"),
    _v("HAM:X005:36", 1, AralikKirilimS0036, "30m"),
    _v("HAM:X005:37", 1, MacdTolS0037, "1d"),
    _v("HAM:X005:38", 1, EmaBantS0038, "1d"),
    _v("HAM:X005:41", 1, MacdSmaIzS0041, "1d"),
    _v("HAM:X005:43", 1, SmaKesIzS0043, "1d"),
    _v("HAM:X005:51", 1, Rsi4DonusS0051, "4h"),
    _v("HAM:X005:54", 1, IbsEma252S0054, "1d"),
    _v("HAM:X005:56", 1, Rsi14SeviyeS0056, "4h"),
    _v("HAM:X005:56", 2, Rsi14SeviyeS0056, "1d"),
    _v("HAM:X005:67", 1, RsiH1D1S0067, "1h"),
    _v("HAM:X005:70", 1, MaIbsS0070, "1d"),
    _v("HAM:X005:73", 1, AoWmaDunS0073, "1h"),
    _v("HAM:X005:74", 1, IbsPazartesiS0074, "1d"),
    _v("HAM:X005:81", 1, SmaKesisDonS0081, "4h"),
    # X005:83 = K2'deki DonchianEma2RS0083 ile aynı hipotez (girdi notu: "koşuda tek kayıt"); yeni sınıf yazılmadı,
    # mevcut sınıfa bağlı kayıt (motor/strateji/kapanis/k2_kaynak.py).
    {"kimlik": "HAM:X005:83#v1", "sinif": "kapanis__donchian-ema-2r-s0083",
     "parametreler": {"kanal_n": 20, "ema_n": 200, "atr_n": 20, "atr_k": 2.0, "hedef_r": 2.0}, "tf": "4h"},
    _v("HAM:X005:84", 1, MacdHaftalikS0084, "1d"),
]

KODLANAMADI = [
    {"kimlik": "HAM:X005:3",
     "neden": "TA-Lib HT_TRENDMODE (Ehlers Hilbert) göstergesi motorda yok, TA-Lib kurulu değil; formül kaynak dosyada "
              "olmadan birebir yazılamaz (uydurma çözüm yok)"},
    # 4, 20, 21, 22, 60, 79: pozisyon bilinçli çıkış modülüyle kod_g8_modul.py'de kodlandı (VARYANTLAR orada).
]
