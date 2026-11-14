"""Kapanış turu kodlama partisi g8_kod_7 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_7.csv, 40 kaynak satırı).

Hepsi HAM:X005:* (trend / ortalamaya dönüş listesi). Her kaynak satır için bir sınıf (35 sınıf); 5 satır KODLANAMADI.
Kurallar `kural_tam` metninden kendi kodumuzla yazıldı; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan (motor sonraki
açılışta doldurur); gelecek verisi yok (shift(-), center=True, tüm-seri istatistiği yok). Üst TF yalnız htf.ust_zaman ile.
Kaynak stopu yoksa ATR(14)x3 uyarlaması. Yönlü çıkış `cikis_long` / `cikis_short` sütunlarıyla verilir.

Biçim kararları (ILERLEME.md politikaları):
- Durum koşullu girişler ("RSI<30 iken al") her mumda yon != 0 üretir; motor pozisyon açıkken yeni girişi atlar.
- Stop-emir girişi seviye mum KAPANIŞIYLA aşılınca sonraki açılışta giriş (politika d): 695, 724.
- Kesişim: "x, y'yi yukarı keser" = x[t-1] <= y[t-1] ve x[t] > y[t]; seviye kesişimi: x[t-1] < seviye <= x[t] (yukarı),
  x[t-1] >= seviye > x[t] (aşağı).
- Girişe göre ölçülen seviyeler (kaynak stopu/hedefi) giriş fiyatı yerine sinyal mumunun kapanışından hesaplanır (giriş ertesi
  açılış; sinyal anında bilinen en yakın fiyat). Pozisyon durumu (giriş fiyatı, yaş, tepe) gerektiren çıkışlar (679 yüzde iz,
  699, 726, 736) `pozisyon_cikisi` kancasıyla / kod_g8_modul'de yazılmıştır.
- Zaman çıkışı, ROI tablosu ve başabaş stopu motorun CikisAyarlari modülleriyle ifade edilir; yüzde iz süren stop kancayla.

KODLANAMADI: 673 (TOTT/SOTT/HOTT/LOTT/ROTT formülleri kaynak metinde yok), 742 (bölge tanımı yok). 699, 726, 736 pozisyon bilinçli
modülle `kod_g8_modul.py`'ye taşındı.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import obv as _obv
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import ardisik_sayac
from motor.strateji.gostergeler_b2 import heikin_ashi
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, tepe_geri_cekilme
from motor.strateji.temel import Strateji


# ---------------------------------------------------------------- yardımcılar
def _seri(x, ref: pd.Series) -> pd.Series:
    return x if isinstance(x, pd.Series) else pd.Series(float(x), index=ref.index)


def _yukari(x: pd.Series, y) -> pd.Series:
    y = _seri(y, x)
    return ((x.shift(1) <= y.shift(1)) & (x > y)).fillna(False)


def _asagi(x: pd.Series, y) -> pd.Series:
    y = _seri(y, x)
    return ((x.shift(1) >= y.shift(1)) & (x < y)).fillna(False)


def _seviye_yukari(x: pd.Series, s: float) -> pd.Series:
    return ((x.shift(1) < s) & (x >= s)).fillna(False)


def _seviye_asagi(x: pd.Series, s: float) -> pd.Series:
    return ((x.shift(1) >= s) & (x < s)).fillna(False)


def _atr_riski(m: pd.DataFrame, p: dict) -> pd.Series:
    return float(p["atr_k"]) * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))


def _ekle(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _atr_stoplu(m: pd.DataFrame, p: dict, long_ok, short_ok, cikis_long=None, cikis_short=None, **kw) -> pd.DataFrame:
    """ATR(atr_n) x atr_k stoplu (uyarlama) iki yön çerçevesi + yönlü çıkışlar."""
    k = m["kapanis"]
    r = _atr_riski(m, p)
    return _ekle(cerceve(m, long_ok, short_ok, k - r, k + r, **kw), cikis_long, cikis_short)


def _lr(kap: pd.Series, n: int):
    """Son n kapanışa en küçük kareler doğrusu: (eğim [bar başına], doğrunun son bardaki değeri, Pearson(kapanış, bar sırası))."""
    n = int(n)
    a = kap.to_numpy(dtype=float)
    egim = np.full(len(a), np.nan)
    uc = np.full(len(a), np.nan)
    kor = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xm = (n - 1) / 2.0
        sxx = float(((x - xm) ** 2).sum())
        w = (x - xm) / sxx
        pen = sliding_window_view(a, n)
        ym = pen.mean(axis=1)
        e = pen @ w
        syy = ((pen - ym[:, None]) ** 2).sum(axis=1)
        egim[n - 1:] = e
        uc[n - 1:] = ym + e * (n - 1 - xm)
        with np.errstate(divide="ignore", invalid="ignore"):
            kor[n - 1:] = e * sxx / np.sqrt(sxx * syy)
    kor[~np.isfinite(kor)] = np.nan
    return (pd.Series(egim, index=kap.index), pd.Series(uc, index=kap.index), pd.Series(kor, index=kap.index))


def _rsi_z(kap: pd.Series, n: int) -> pd.Series:
    """z = (kapanış - SMA) / örneklem std (ddof=1)."""
    ort = kap.rolling(n, min_periods=n).mean()
    std = kap.rolling(n, min_periods=n).std(ddof=1).replace(0.0, np.nan)
    return (kap - ort) / std


def _mcginley(kap: pd.Series, n: int) -> pd.Series:
    """McGinley Dynamic: MD = MD[-1] + (C - MD[-1]) / (N * (C / MD[-1])^4); ilk değer ilk kapanış."""
    c = kap.to_numpy(dtype=float)
    md = np.full(len(c), np.nan)
    if len(c):
        md[0] = c[0]
    for i in range(1, len(c)):
        onc = md[i - 1]
        if np.isnan(onc) or np.isnan(c[i]) or onc <= 0 or c[i] <= 0:
            md[i] = c[i] if np.isnan(onc) else onc
            continue
        md[i] = onc + (c[i] - onc) / (n * (c[i] / onc) ** 4)
    return pd.Series(md, index=kap.index)


def _var_vidya(src: pd.Series, n: int, cmo_n: int) -> pd.Series:
    """VAR (Chande VIDYA): alfa = 2/(n+1); VAR = alfa*|CMO|*src + (1 - alfa*|CMO|)*VAR[-1]; ilk geçerli değer = src."""
    fark = src.diff()
    yuk = fark.clip(lower=0.0).rolling(cmo_n, min_periods=cmo_n).sum()
    asg = (-fark).clip(lower=0.0).rolling(cmo_n, min_periods=cmo_n).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        cmo = ((yuk - asg) / (yuk + asg)).abs().to_numpy()
    a = 2.0 / (n + 1)
    s = src.to_numpy(dtype=float)
    out = np.full(len(s), np.nan)
    onc = np.nan
    for i in range(len(s)):
        if np.isnan(cmo[i]):
            continue
        k = a * cmo[i]
        onc = s[i] if np.isnan(onc) else k * s[i] + (1.0 - k) * onc
        out[i] = onc
    return pd.Series(out, index=src.index)


def _pmax(ma: pd.Series, atr: pd.Series, carpan: float) -> pd.Series:
    """PMax: ma +/- carpan*ATR yapışkan (Supertrend benzeri) izleyen bant; yön +1 ise alt bant, -1 ise üst bant."""
    m, a = ma.to_numpy(dtype=float), atr.to_numpy(dtype=float)
    cikti = np.full(len(m), np.nan)
    ls_onc = ss_onc = np.nan
    yon = 1
    for i in range(len(m)):
        if np.isnan(m[i]) or np.isnan(a[i]):
            continue
        ls, ss = m[i] - carpan * a[i], m[i] + carpan * a[i]
        if not np.isnan(ls_onc):
            ls = max(ls, ls_onc) if m[i] > ls_onc else ls
            ss = min(ss, ss_onc) if m[i] < ss_onc else ss
            if yon == -1 and m[i] > ss_onc:
                yon = 1
            elif yon == 1 and m[i] < ls_onc:
                yon = -1
        cikti[i] = ls if yon == 1 else ss
        ls_onc, ss_onc = ls, ss
    return pd.Series(cikti, index=ma.index)


def _alphatrend(m: pd.DataFrame, atr_n: int, carpan: float, mfi_n: int, mfi_esik: float) -> pd.Series:
    """AT: ATR = SMA(TR); MFI >= esik ise AT = max(AT[-1], düşük - c*ATR), değilse AT = min(AT[-1], yüksek + c*ATR)."""
    h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
    atr = g.sma(g.gercek_aralik(h, d, k), atr_n).to_numpy()
    mf = _mfi(h, d, k, m["hacim"], mfi_n).to_numpy()
    yk = (d.to_numpy() - carpan * atr)
    ys = (h.to_numpy() + carpan * atr)
    at = np.full(len(k), np.nan)
    for i in range(len(k)):
        if np.isnan(atr[i]) or np.isnan(mf[i]):
            continue
        onc = at[i - 1] if i > 0 else np.nan
        if mf[i] >= mfi_esik:
            at[i] = yk[i] if np.isnan(onc) else max(onc, yk[i])
        else:
            at[i] = ys[i] if np.isnan(onc) else min(onc, ys[i])
    return pd.Series(at, index=k.index)


class _Taban(Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


_ATR = {"atr_n": 14, "atr_k": 3.0}


# ---------------------------------------------------------------- 659
class BbDonusAdxSma200(_Taban):
    """X005:659 (1d long): kapanış > SMA(200) VE ADX(14) < 20 VE kapanış alt Bollinger(20,2) altında -> long. Hedef orta bant
    (sinyal mumunun SMA20 değeri, sabit seviye); 5 seans içinde dönmezse zaman çıkışı (CikisAyarlari.zaman_cikisi_mum=5); stop =
    min(sinyal günü düşüğü, giriş - 1xATR(14)) (daha geniş olan; giriş = sinyal kapanışı). Dışarıda: isteğe bağlı RSI/çekiç teyidi.
    MA200 tipi SMA varsayımı."""
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "trend_sma": 200, "adx_n": 14, "adx_max": 20.0, "atr_n": 14, "atr_k": 1.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=5)

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        adx = g.adx(h, d, k, int(p["adx_n"]))["adx"]
        al = (k > g.sma(k, int(p["trend_sma"]))) & (adx < float(p["adx_max"])) & (k < bb["alt"])
        stop = np.minimum(d, k - _atr_riski(m, p))
        return cerceve(m, al, False, stop, k, hedef_l=bb["orta"])


# ---------------------------------------------------------------- 661
class McGinleyStopReverse(_Taban):
    """X005:661 (1d iki yön): kapanış McGinley Dynamic(25)'i yukarı keser VE kapanış son 3 barın en yükseği -> long; aşağı keser VE
    son 3 barın en düşüğü -> short. Çıkış: stop %10, hedef %40 ya da ters koşul (long, short koşuluyla; short, long koşuluyla kapanır
    = stop-and-reverse). Stop/hedef sinyal kapanışından. Kural fiyat yüzdelerinde (NSE lot/marj yok sayıldı)."""
    varsayilan_parametreler = {"mcginley_n": 25, "teyit_bar": 3, "sl_yuzde": 10.0, "tp_yuzde": 40.0}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        md = _mcginley(k, int(p["mcginley_n"]))
        nb = int(p["teyit_bar"])
        al = _yukari(k, md) & (k >= k.rolling(nb, min_periods=nb).max())
        sat = _asagi(k, md) & (k <= k.rolling(nb, min_periods=nb).min())
        sl, tp = float(p["sl_yuzde"]) / 100.0, float(p["tp_yuzde"]) / 100.0
        return _ekle(cerceve(m, al, sat, k * (1 - sl), k * (1 + sl), hedef_l=k * (1 + tp), hedef_s=k * (1 - tp)),
                     cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 664
class WaveTrendKesisim(_Taban):
    """X005:664 (1d long): esa = EMA(hlc3, 10); d = EMA(|hlc3 - esa|, 10); ci = (hlc3 - esa) / (0,015 d); wt1 = EMA(ci, 21);
    wt2 = SMA(wt1, 4). Önceki barda wt1 < wt2 iken bu barda wt1 > wt2 ise long; wt1 wt2'yi aşağı kesince kapat. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"n1": 10, "n2": 21, "sinyal_sma": 4, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        hlc3 = (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0
        esa = g.ema(hlc3, int(p["n1"]))
        d = g.ema((hlc3 - esa).abs(), int(p["n1"])).replace(0.0, np.nan)
        wt1 = g.ema((hlc3 - esa) / (0.015 * d), int(p["n2"]))
        wt2 = g.sma(wt1, int(p["sinyal_sma"]))
        al = ((wt1.shift(1) < wt2.shift(1)) & (wt1 > wt2)).fillna(False)
        return _atr_stoplu(m, p, al, False, cikis_long=_asagi(wt1, wt2))


# ---------------------------------------------------------------- 666
class ZirveYakinligiHacim(_Taban):
    """X005:666 (1d long): kapanış >= 0,98 x 252 günlük en yüksek HIGH (kaynakta high/kapanış ayrımı yazılı değil: "en yüksek seviye"
    = en yüksek yüksek, mevcut mum dahil) VE kapanış >= SMA(200) VE hacim >= 1,2 x SMA(hacim, 20) -> long (ertesi açılış). Stop =
    giriş - 2xATR(14) (giriş = sinyal kapanışı; bar içi stop). Çıkış: sinyal gününden 3 işlem günü sonra (zaman_cikisi_mum=3).
    ORB/VWAP teyidi ve günlük 30 hisse sıralaması uygulanmaz."""
    varsayilan_parametreler = {"zirve_n": 252, "yakinlik": 0.98, "trend_sma": 200, "hacim_n": 20, "hacim_k": 1.2,
                               "atr_n": 14, "atr_k": 2.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=3)

    def sinyaller(self, m):
        p = self.parametreler
        k, h = m["kapanis"], m["yuksek"]
        zn = int(p["zirve_n"])
        zirve = h.rolling(zn, min_periods=zn).max()
        al = ((k >= float(p["yakinlik"]) * zirve) & (k >= g.sma(k, int(p["trend_sma"])))
              & (m["hacim"] >= float(p["hacim_k"]) * g.sma(m["hacim"], int(p["hacim_n"]))))
        return cerceve(m, al, False, k - _atr_riski(m, p), k)


# ---------------------------------------------------------------- 671
class StokastikSlowKesisim(_Taban):
    """X005:671 (1d long): Stokastik (K=5, yavaşlatma=5, %D=3): ham %K(5) -> yavaş %K = SMA(5); %D = SMA(yavaş %K, 3). %K, %D'yi yukarı
    keserse long; %K, %D'yi aşağı keserse kapat. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"k": 5, "slow": 5, "d": 3, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        ham = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], int(p["k"]), 1)["k"]
        kk = g.sma(ham, int(p["slow"]))
        dd = g.sma(kk, int(p["d"]))
        return _atr_stoplu(m, p, _yukari(kk, dd), False, cikis_long=_asagi(kk, dd))


# ---------------------------------------------------------------- 672
class VarPmaxKesisim(_Taban):
    """X005:672 (5m iki yön): hl2 üzerinde VAR(10) (VIDYA: alfa = 2/(n+1) x |CMO(9)|); PMax = VAR +/- 3 x ATR(10) Supertrend mantığında
    izleyen bant. Kapanmış mumda VAR, PMax'i yukarı keserse long, aşağı keserse short (ters çevirme: karşı yön çıkışı). Stop yok
    (PMax çizgisi izleyici) -> ATR(14)x3 felaket stopu uyarlaması. VIDYA alfa standart varsayım."""
    varsayilan_parametreler = {"ma_n": 10, "cmo_n": 9, "atr_pmax_n": 10, "carpan": 3.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        hl2 = (m["yuksek"] + m["dusuk"]) / 2.0
        var = _var_vidya(hl2, int(p["ma_n"]), int(p["cmo_n"]))
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_pmax_n"]))
        pm = _pmax(var, atr, float(p["carpan"]))
        al, sat = _yukari(var, pm), _asagi(var, pm)
        return _atr_stoplu(m, p, al, sat, cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 674
class HaWmaPsarMacd(_Taban):
    """X005:674 (15m + 1h long): 1h Heikin-Ashi kapanışı = (O+H+L+C)/4. Yükselen trend (1h): WMA(14, gerçek kapanış) < HA kapanış VE
    PSAR(0,2/0,2; gerçek H/L) < HA kapanış. Giriş: yükselen trend VE 15m MACD histogramı (12,26,9) > 0 (pozisyon yokken). Çıkış: 15m
    MACD hist <= 0 VEYA 1h yükselen trend yok. 1h değerler htf.ust_zaman ile yalnız KAPANMIŞ 1h mumdan. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"htf": "1h", "wma": 14, "psar_adim": 0.2, "psar_maks": 0.2, "macd_hizli": 12, "macd_yavas": 26,
                               "macd_sinyal": 9, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler

        def ust(u):
            ha = heikin_ashi(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"])["ha_kapanis"]
            wma = _wma(u["kapanis"], int(p["wma"]))
            sar = g.psar(u["yuksek"], u["dusuk"], float(p["psar_adim"]), float(p["psar_maks"]))["sar"]
            return pd.DataFrame({"yuk": ((wma < ha) & (sar < ha)).astype(float)}, index=u.index)

        yuk = ust_zaman(m, str(p["htf"]), ust)["yuk"].fillna(0.0) == 1.0
        hist = g.macd(m["kapanis"], int(p["macd_hizli"]), int(p["macd_yavas"]), int(p["macd_sinyal"]))["histogram"]
        return _atr_stoplu(m, p, yuk & (hist > 0), False, cikis_long=(hist <= 0) | ~yuk)


# ---------------------------------------------------------------- 676
class AlphaTrendMfi(_Taban):
    """X005:676 (4h|1d long): ATR = SMA(TR,14); MFI(HLC3,14) >= 50 ise AT = max(AT[-1], düşük - c x ATR), değilse AT = min(AT[-1],
    yüksek + c x ATR) (c=1). AT kendi 2 bar gecikmeli değerini yukarı keser VE son satıştan sonra ilk alışsa (kapanmış bar) long; AT 2 bar
    gecikmeli değerini aşağı keserse (son alıştan sonra ilk) kapat. Alış/satış dönüşümü sinyal serisi durumudur (pozisyon değil). Stop yok
    -> ATR(14)x3."""
    varsayilan_parametreler = {"atr_n_at": 14, "carpan": 1.0, "mfi_n": 14, "mfi_esik": 50.0, "sinyal_gecikme": 2, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        at = _alphatrend(m, int(p["atr_n_at"]), float(p["carpan"]), int(p["mfi_n"]), float(p["mfi_esik"]))
        gec = at.shift(int(p["sinyal_gecikme"]))
        ham_al, ham_sat = _yukari(at, gec).to_numpy(), _asagi(at, gec).to_numpy()
        al = np.zeros(len(at), dtype=bool)
        sat = np.zeros(len(at), dtype=bool)
        son = 0                                    # 0 yok, 1 son sinyal alış, -1 son sinyal satış
        for i in range(len(at)):
            if ham_al[i] and son != 1:
                al[i], son = True, 1
            elif ham_sat[i] and son == 1:
                sat[i], son = True, -1
        return _atr_stoplu(m, p, pd.Series(al, index=m.index), False, cikis_long=pd.Series(sat, index=m.index))


# ---------------------------------------------------------------- 678
class BbKesisimRsiTp(_Taban):
    """X005:678 (15m iki yön): BB(20,2) kapanış. Long: kapanış alt bandı aşağıdan yukarı keser VE RSI(20) > 30; hedef = o barın üst bandı
    (sabit), stop = giriş x (1 - %2,5). Short: kapanış üst bandı yukarıdan aşağı keser VE RSI(20) < 70; hedef = o barın alt bandı, stop =
    giriş x (1 + %2,5). TP/SL temasında çıkış motorun bar içi stop/hedefidir (giriş = sinyal kapanışı)."""
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_n": 20, "rsi_alt": 30.0, "rsi_ust": 70.0, "sl_yuzde": 2.5}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        r = g.rsi(k, int(p["rsi_n"]))
        al = _yukari(k, bb["alt"]) & (r > float(p["rsi_alt"]))
        sat = _asagi(k, bb["ust"]) & (r < float(p["rsi_ust"]))
        sl = float(p["sl_yuzde"]) / 100.0
        return cerceve(m, al, sat, k * (1 - sl), k * (1 + sl), hedef_l=bb["ust"], hedef_s=bb["alt"])


# ---------------------------------------------------------------- 679
class BbHacimAdxRoi(KancaDestek, _Taban):
    """X005:679 (15m iki yön): long: kapanış BB(20,2) alt bandın altında VE önceki kapanış bandın içinde (ilk dokunuş) VE RSI(14) < 27 VE
    hacim > 1,061 x SMA(hacim,20) VE ADX(14) < 25; short: kapanış üst bandın üstünde (ilk dokunuş) VE RSI > 76 VE aynı hacim/ADX.
    Sinyal çıkışı yok. Kademeli ROI (dk -> 15m bar, yukarı yuvarlanır): %18,1 (0), %10,5 (59 dk -> 4 bar), %1,7 (232 dk -> 16 bar), %0
    (567 dk -> 38 bar) = CikisAyarlari.azalan_roi. İz süren stop: kâr %13,4 olunca zirveden %11,3 geriden (Freqtrade positive_offset/positive
    okuması; kanca: zirve kârı >= %13,4 iken kapanış zirve fiyatın (long: en yüksek HIGH, short: en düşük LOW) %11,3 gerisinde).
    Sabit stop -%30."""
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_long": 27.0, "rsi_short": 76.0, "hacim_k": 1.061,
                               "hacim_n": 20, "adx_n": 14, "adx_max": 25.0, "stop_yuzde": 30.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 18.1), (4, 10.5), (16, 1.7), (38, 0.0)))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, 11.3, 13.4)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        r = g.rsi(k, int(p["rsi_n"]))
        ortak = ((m["hacim"] > float(p["hacim_k"]) * g.sma(m["hacim"], int(p["hacim_n"])))
                 & (g.adx(m["yuksek"], m["dusuk"], k, int(p["adx_n"]))["adx"] < float(p["adx_max"])))
        ilk_alt = (k < bb["alt"]) & (k.shift(1) >= bb["alt"].shift(1))
        ilk_ust = (k > bb["ust"]) & (k.shift(1) <= bb["ust"].shift(1))
        al = ilk_alt & (r < float(p["rsi_long"])) & ortak
        sat = ilk_ust & (r > float(p["rsi_short"])) & ortak
        sl = float(p["stop_yuzde"]) / 100.0
        return cerceve(m, al, sat, k * (1 - sl), k * (1 + sl))


# ---------------------------------------------------------------- 680
class SmaRsiDurumIki(_Taban):
    """X005:680 (1h ve 1d iki yön; 1m veri dışı): long durumu: SMA(9) > SMA(21) VE RSI(14) < 50; short durumu: SMA(9) < SMA(21) VE
    RSI(14) > 50. Ters sinyale kadar tut (long, short durumuyla; short, long durumuyla kapanır). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"sma_hizli": 9, "sma_yavas": 21, "rsi_n": 14, "rsi_esik": 50.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        hizli, yavas = g.sma(k, int(p["sma_hizli"])), g.sma(k, int(p["sma_yavas"]))
        r = g.rsi(k, int(p["rsi_n"]))
        long_d = ((hizli > yavas) & (r < float(p["rsi_esik"]))).fillna(False)
        short_d = ((hizli < yavas) & (r > float(p["rsi_esik"]))).fillna(False)
        return _atr_stoplu(m, p, long_d, short_d, cikis_long=short_d, cikis_short=long_d)


# ---------------------------------------------------------------- 681
class BbOrtaKesisimDisBantCikis(_Taban):
    """X005:681 (1h iki yön): kapanış BB(27,2) orta bandı (SMA27) aşağıdan yukarı keserse long, yukarıdan aşağı keserse short. Pozisyon,
    son kapanmış mumun üst ya da alt Bollinger bandına (27,2) değince (yüksek >= üst bant ya da düşük <= alt bant) kapanır (kâr/zarar
    fark etmez). Sabit SL/TP yok -> ATR(14)x3 felaket stopu uyarlaması. Evren kripto13 (lider kararı)."""
    varsayilan_parametreler = {"bb_n": 27, "bb_k": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        dokunus = ((m["yuksek"] >= bb["ust"]) | (m["dusuk"] <= bb["alt"])).fillna(False)
        return _atr_stoplu(m, p, _yukari(k, bb["orta"]), _asagi(k, bb["orta"]), cikis_long=dokunus, cikis_short=dokunus)


# ---------------------------------------------------------------- 682
class TumZamanZirveWma(_Taban):
    """X005:682 (1d long): pozisyon yokken kapanış, önceki bara kadar oluşmuş tüm zamanların en yüksek HIGH değerini (kümülatif, mevcut mum
    hariç) aşarsa long (sonraki açılış); kapanış WMA(20) altına inince kapat. Kümülatif zirve için en az 20 bar geçmiş şartı (ısınma).
    Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"cikis_wma": 20, "isinma": 20, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        zirve = m["yuksek"].expanding(min_periods=int(p["isinma"])).max().shift(1)
        al = (k > zirve).fillna(False)
        return _atr_stoplu(m, p, al, False, cikis_long=k < _wma(k, int(p["cikis_wma"])))


# ---------------------------------------------------------------- 683
class Sma20EgimDonusRsi(_Taban):
    """X005:683 (1d long): SMA20[t] > SMA20[t-1] ve SMA20[t-1] <= SMA20[t-2] (eğim dönüşü) VE 30 <= RSI(10)[t] < 70 ise long (ertesi
    açılış); çıkış RSI(10) >= 70 ya da <= 30. RSI Wilder. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"sma_n": 20, "rsi_n": 10, "alt": 30.0, "ust": 70.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s = g.sma(k, int(p["sma_n"]))
        r = g.rsi(k, int(p["rsi_n"]))
        al = ((s > s.shift(1)) & (s.shift(1) <= s.shift(2)) & (r >= float(p["alt"])) & (r < float(p["ust"]))).fillna(False)
        return _atr_stoplu(m, p, al, False, cikis_long=(r >= float(p["ust"])) | (r <= float(p["alt"])))


# ---------------------------------------------------------------- 684
class Vwap3OranDurum(_Taban):
    """X005:684 (15m ve 30m iki yön): oran = kapanış / VWAP(3 mum; tipik fiyat (H+L+C)/3 x hacim, son 3 mum); oran < 0,998 ise long, oran >
    1,002 ise short; oran bantların içine dönünce pozisyon sıfırlanır (long oran >= 0,998 olunca, short oran <= 1,002 olunca kapanır).
    Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"vwap_n": 3, "alt": 0.998, "ust": 1.002, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        n = int(p["vwap_n"])
        tp = (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0
        vwap = ((tp * m["hacim"]).rolling(n, min_periods=n).sum() / m["hacim"].rolling(n, min_periods=n).sum().replace(0.0, np.nan))
        oran = m["kapanis"] / vwap
        alt, ust = float(p["alt"]), float(p["ust"])
        return _atr_stoplu(m, p, oran < alt, oran > ust, cikis_long=oran >= alt, cikis_short=oran <= ust)


# ---------------------------------------------------------------- 693
class BbUstAlAltSat(_Taban):
    """X005:693 (4h|1d long): pozisyon yokken kapanmış mum kapanışı >= BB(20, 2σ, kapanış) üst bant ise sonraki açılışta long; kapanış <=
    alt bant ise kapat ("alım gününden farklı gün" koşulu, giriş sinyal mumu üst bantta olduğundan alt bantla aynı anda olamayacağı için
    kendiliğinden sağlanır). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        return _atr_stoplu(m, p, (k >= bb["ust"]).fillna(False), False, cikis_long=(k <= bb["alt"]).fillna(False))


# ---------------------------------------------------------------- 695
class Sma20GeriCekilmeOnay(_Taban):
    """X005:695 (1d long): SMA(20) yükseliyor VE kapanış > SMA20 iken mumun düşüğü önceki iki mumun düşüğünün altına inerse kurulum (sinyal
    mumu S). Sonraki mumun kapanışı S.yüksek'i aşarsa (ve trend koşulu hâlâ sürüyorsa) o mumun kapanışında sinyal, ondan sonraki açılışta
    giriş (politika d; aşmazsa kurulum düşer). Hedef = giriş + 2 x S aralığı; stop = giriş - 1 x S aralığı (giriş = onay mumu kapanışı)."""
    varsayilan_parametreler = {"sma_n": 20, "geri_bar": 2, "hedef_aralik_k": 2.0, "stop_aralik_k": 1.0}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        s = g.sma(k, int(p["sma_n"]))
        trend = ((s > s.shift(1)) & (k > s)).fillna(False)
        geri = int(p["geri_bar"])
        onceki_dip = pd.concat([d.shift(i) for i in range(1, geri + 1)], axis=1).min(axis=1, skipna=False)
        kurulum = (trend & (d < onceki_dip)).fillna(False)
        aralik = h.shift(1) - d.shift(1)
        onay = kurulum.shift(1, fill_value=False) & (k > h.shift(1)) & trend & (aralik > 0)
        return cerceve(m, onay, False, k - float(p["stop_aralik_k"]) * aralik, k,
                       hedef_l=k + float(p["hedef_aralik_k"]) * aralik)


# ---------------------------------------------------------------- 697
class Sma20KanalDurTers(_Taban):
    """X005:697 (4h|1d iki yön, dur-ve-ters): yükselen SMA(20) (SMA20[t] > SMA20[t-1]) iken düşük < SMA(düşükler,3) -> long (buy-stop
    seviyesi sinyal mumunun kendi düşüğü, kapanışta zaten aşılmış sayılır: politika d; sonraki açılışta giriş). SMA(20) düşüşteyken yüksek >
    SMA(yükseksler,3) -> long kapanır ve aynı sinyalle short açılır; short -> long simetrik. Koruyucu stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"sma_n": 20, "kanal_n": 3, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s = g.sma(k, int(p["sma_n"]))
        kn = int(p["kanal_n"])
        al = ((s > s.shift(1)) & (m["dusuk"] < g.sma(m["dusuk"], kn))).fillna(False)
        sat = ((s < s.shift(1)) & (m["yuksek"] > g.sma(m["yuksek"], kn))).fillna(False)
        return _atr_stoplu(m, p, al, sat, cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 698
class YavasStokastikAsiri(_Taban):
    """X005:698 (4h|1d long): Yavaş Stokastik (14,3,3; yavaş %K = SMA(ham %K(14), 3), %D = SMA(yavaş %K, 3)); pozisyon yokken yavaş %K < 20
    ise long; yavaş %K > 80 olunca kapat (long yalnız %K < 20'de girildiği için ilk > 80 durumu üstüne çıkış anıdır). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"k_n": 14, "k_yum": 3, "d_yum": 3, "alt": 20.0, "ust": 80.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        ham = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], int(p["k_n"]), 1)["k"]
        kk = g.sma(ham, int(p["k_yum"]))
        return _atr_stoplu(m, p, (kk < float(p["alt"])).fillna(False), False, cikis_long=(kk > float(p["ust"])).fillna(False))


# ---------------------------------------------------------------- 706
class BbDisiKapanisIciKapanis(_Taban):
    """X005:706 (1d long): SMA(20) +/- sapma x std Bollinger (sapma 2 / 2,5 / 3: üç varyant). Bir mum alt bandın altında kapanır, sonraki mum
    bandın içinde (alt <= kapanış <= üst) kapanırsa long (sonraki açılış). Çıkış ayna: bir mum üst bandın üstünde kapanır, sonraki mum
    bandın içinde kapanırsa long kapanır; sat sinyalinde short AÇILMAZ (yorum). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"bb_periyot": 20, "bb_sapma": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_periyot"]), float(p["bb_sapma"]))
        ici = ((k >= bb["alt"]) & (k <= bb["ust"])).fillna(False)
        alt_disi = (k < bb["alt"]).fillna(False)
        ust_disi = (k > bb["ust"]).fillna(False)
        return _atr_stoplu(m, p, alt_disi.shift(1, fill_value=False) & ici, False,
                           cikis_long=ust_disi.shift(1, fill_value=False) & ici)


# ---------------------------------------------------------------- 710
class LrEgimDonusIki(_Taban):
    """X005:710 (4h|1d iki yön): 40 barlık doğrusal regresyon eğimi pozitife dönünce (önceki <= 0, şimdi > 0) long; negatife dönünce
    (önceki >= 0, şimdi < 0) short; ters eğim sinyalinde pozisyon ters çevrilir. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"lr_n": 40, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        egim = _lr(m["kapanis"], int(p["lr_n"]))[0]
        al = ((egim > 0) & (egim.shift(1) <= 0)).fillna(False)
        sat = ((egim < 0) & (egim.shift(1) >= 0)).fillna(False)
        return _atr_stoplu(m, p, al, sat, cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 711
class LrKanalDonus(_Taban):
    """X005:711 (4h|1d long): LR(20) çizgisi (son 20 kapanışa doğrunun son bardaki değeri) ve kanal +/- %5. Regresyon eğimi < 0 iken kapanış,
    bir önceki barın üst kanalını yukarı keserse long; kapanış bir önceki barın alt kanalını aşağı keserse kapat. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"lr_n": 20, "kanal_pct": 5.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        egim, cizgi, _ = _lr(k, int(p["lr_n"]))
        c = float(p["kanal_pct"]) / 100.0
        ust, alt = (cizgi * (1 + c)).shift(1), (cizgi * (1 - c)).shift(1)
        return _atr_stoplu(m, p, _yukari(k, ust) & (egim < 0), False, cikis_long=_asagi(k, alt))


# ---------------------------------------------------------------- 718
class KorelasyonTrend(_Taban):
    """X005:718 (1d long): CorrelationTrend = Pearson korelasyon(kapanış, bar sırası, 20); gösterge 0 çizgisini yukarı keserse long (sonraki
    bar); 0 çizgisini aşağı keserse kapat. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"kor_n": 20, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        kor = _lr(m["kapanis"], int(p["kor_n"]))[2]
        return _atr_stoplu(m, p, _seviye_yukari(kor, 0.0), False, cikis_long=_seviye_asagi(kor, 0.0))


# ---------------------------------------------------------------- 724
class SuperTrendYatayKurulum(_Taban):
    """X005:724 (1d iki yön): kapanış SuperTrend(10,3) üstünde VE çizgi yatay (ST[t] == ST[t-1]) VE en az 2 ardışık düşen yüksek -> kurulum;
    sonraki mum kapanışı bugünün yükseğini aşarsa o kapanışta sinyal, sonraki açılışta long (politika d; koşulsuz giriş yok). Short ayna
    (kapanış ST altında, çizgi yatay, 2 yükselen düşük; sonraki kapanış bugünün düşüğünün altına inince). Çıkış: kapanış SuperTrend
    altına inince (short: üstüne çıkınca) ya da giriş + 2 x ATR(10) hedef (short: -2 x ATR); stop: 2 günlük en düşük düşük (short: 2 günlük
    en yüksek yüksek; onay mumu dahil)."""
    varsayilan_parametreler = {"st_atr": 10, "st_carpan": 3.0, "ardisik": 2, "stop_n": 2, "hedef_atr_k": 2.0, "atr_n": 10}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        st = g.supertrend(h, d, k, int(p["st_atr"]), float(p["st_carpan"]))
        cz = st["cizgi"]
        yatay = (cz == cz.shift(1)) & cz.notna()
        ard = int(p["ardisik"])
        dusen_yuk = ardisik_sayac(h < h.shift(1)) >= ard
        yuken_dus = ardisik_sayac(d > d.shift(1)) >= ard
        kur_l = ((k > cz) & yatay & dusen_yuk).fillna(False)
        kur_s = ((k < cz) & yatay & yuken_dus).fillna(False)
        gir_l = kur_l.shift(1, fill_value=False) & (k > h.shift(1))
        gir_s = kur_s.shift(1, fill_value=False) & (k < d.shift(1))
        sn = int(p["stop_n"])
        atr = g.atr(h, d, k, int(p["atr_n"]))
        hk = float(p["hedef_atr_k"])
        return _ekle(cerceve(m, gir_l, gir_s, d.rolling(sn, min_periods=sn).min(), h.rolling(sn, min_periods=sn).max(),
                             hedef_l=k + hk * atr, hedef_s=k - hk * atr),
                     cikis_long=(k < cz).fillna(False), cikis_short=(k > cz).fillna(False))


# ---------------------------------------------------------------- 725
class SuperTrendIkiCarpan(_Taban):
    """X005:725 (1d iki yön): Supertrend ATR periyodu 10, çarpan 2 çizgisi çarpan 3 çizgisini yukarı keserse long, aşağı keserse short;
    ters sinyal pozisyonu çevirir. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"atr_n": 10, "carpan_hizli": 2.0, "carpan_yavas": 3.0, "stop_atr_n": 14, "stop_atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        hizli = g.supertrend(h, d, k, int(p["atr_n"]), float(p["carpan_hizli"]))["cizgi"]
        yavas = g.supertrend(h, d, k, int(p["atr_n"]), float(p["carpan_yavas"]))["cizgi"]
        al, sat = _yukari(hizli, yavas), _asagi(hizli, yavas)
        r = float(p["stop_atr_k"]) * g.atr(h, d, k, int(p["stop_atr_n"]))
        return _ekle(cerceve(m, al, sat, k - r, k + r), cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 727
class HaTipikEmaDurum(_Taban):
    """X005:727 (4h|1d iki yön): hızlı = EMA(tipik fiyat (H+L+C)/3, 5); yavaş = EMA(Heikin-Ashi kapanışı, 8). Hızlı, yavaşı yukarı keser VE
    bar yükseliş barı (kapanış > açılış) ise durum 1 -> long (sonraki bar); hızlı yavaşı aşağı keserek durum 0'a dönünce short (ters
    çevirme; durum 0'a dönüş yalnız durum 1 iken sayılır). Stop = giriş fiyatının %25 ötesi; fiyat girişin %15 lehine gidince stop başabaşa
    çekilir (CikisAyarlari.basabas_r_esigi = 15/25 = 0,6 R)."""
    varsayilan_parametreler = {"tip_ema": 5, "ha_ema": 8, "stop_pct": 25.0}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=0.6)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        tip = (m["yuksek"] + m["dusuk"] + k) / 3.0
        ha = heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], k)["ha_kapanis"]
        hizli, yavas = g.ema(tip, int(p["tip_ema"])), g.ema(ha, int(p["ha_ema"]))
        yk, as_ = _yukari(hizli, yavas).to_numpy(), _asagi(hizli, yavas).to_numpy()
        yukselis = (k > m["acilis"]).to_numpy()
        al = np.zeros(len(k), dtype=bool)
        sat = np.zeros(len(k), dtype=bool)
        durum = 0
        for i in range(len(k)):
            if yk[i] and yukselis[i]:
                al[i], durum = True, 1
            elif as_[i] and durum == 1:
                sat[i], durum = True, 0
        al, sat = pd.Series(al, index=m.index), pd.Series(sat, index=m.index)
        s = float(p["stop_pct"]) / 100.0
        return _ekle(cerceve(m, al, sat, k * (1 - s), k * (1 + s)), cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 730
class ObvmKesisim(_Taban):
    """X005:730 (4h|1d iki yön): OBVM = EMA(OBV, 7); sinyal çizgisi = SMA(OBVM, 10). OBVM sinyali yukarı keserse long (sonraki bar); aşağı
    keserse short (long kapanır, ters çevirme). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"obvm_n": 7, "sinyal_n": 10, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        obvm = g.ema(_obv(m["kapanis"], m["hacim"]), int(p["obvm_n"]))
        sg = g.sma(obvm, int(p["sinyal_n"]))
        al, sat = _yukari(obvm, sg), _asagi(obvm, sg)
        return _atr_stoplu(m, p, al, sat, cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 733
class AdxEsikSma50Iki(_Taban):
    """X005:733 (1d iki yön): long: [ADX(14) 30'u yukarı keser VE ADX < 42] VEYA [ADX 22'yi yukarı keser VE ADX > 1,8 x en düşük ADX (son 12
    bar, mevcut dahil)] VE kapanış > SMA(50) -> long; short: aynı ADX koşulu VE kapanış < SMA(50). Çıkış: long için kapanış SMA50 altına
    inince, short için üstüne çıkınca. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"adx_n": 14, "trend": 30.0, "axmax": 42.0, "lag": 12, "crit": 22.0, "mult": 1.8, "ma_n": 50, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        adx = g.adx(m["yuksek"], m["dusuk"], k, int(p["adx_n"]))["adx"]
        lag = int(p["lag"])
        a = _seviye_yukari(adx, float(p["trend"])) & (adx < float(p["axmax"]))
        b = _seviye_yukari(adx, float(p["crit"])) & (adx > float(p["mult"]) * adx.rolling(lag, min_periods=lag).min())
        guc = a | b
        sma = g.sma(k, int(p["ma_n"]))
        return _atr_stoplu(m, p, guc & (k > sma), guc & (k < sma), cikis_long=(k < sma).fillna(False),
                           cikis_short=(k > sma).fillna(False))


# ---------------------------------------------------------------- 737
class AylikSma8Ters(_Taban):
    """X005:737 (1M, 1d mumlardan; iki yön): sinyal ay SONU kapanışında (takvim: ertesi gün başka ay), dolum sonraki açılış. Aylık kapanışlar
    = ay sonu günlük kapanışları; aylık kapanış SMA(8)(son 8 aylık kapanış) üstündeyse long; altına inince long kapatılıp short açılır
    (ters çevirme). Ay sonu mumu dışında sinyal yok. Stop yok -> ATR(14)x3 (günlük ATR)."""
    varsayilan_parametreler = {"sma_n": 8, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ay_sonu = pd.Series((m.index + pd.Timedelta(days=1)).month != m.index.month, index=m.index)
        aylik = k[ay_sonu]
        sn = int(p["sma_n"])
        sma = pd.Series(np.nan, index=m.index)
        sma[ay_sonu] = aylik.rolling(sn, min_periods=sn).mean()
        al = ay_sonu & (k > sma)
        sat = ay_sonu & (k < sma)
        return _atr_stoplu(m, p, al, sat, cikis_long=sat, cikis_short=al)


# ---------------------------------------------------------------- 751
class RsiTrendYuzde20(_Taban):
    """X005:751 (1d long): trend durumu: son dipten kapanış %20 yükselirse yükseliş trendi başlar; yükseliş trendinde zirveden (kapanış)
    %20 geri çekilmede aşağı trend (ve tersi, dipten %20 yükselişle yeniden yukarı). Yükseliş trendindeyken RSI(14) 30'u aşağı keserse
    long (sonraki bar); çıkış: RSI 70'i yukarı keserse ya da trend %20 geri çekilmeyle aşağı dönerse. Başlangıçta trend yok (ilk %20'lik
    hareket belirler). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"rsi_n": 14, "os": 30.0, "ob": 70.0, "trend_yuzde": 0.20, **_ATR}

    @staticmethod
    def _trend(kap: pd.Series, oran: float) -> pd.Series:
        c = kap.to_numpy(dtype=float)
        durum = np.zeros(len(c), dtype="int64")
        d = 0
        alt = ust = np.nan
        for i in range(len(c)):
            x = c[i]
            if np.isnan(x):
                durum[i] = d
                continue
            alt = x if np.isnan(alt) else min(alt, x)
            ust = x if np.isnan(ust) else max(ust, x)
            if d != 1 and x >= alt * (1 + oran):
                d, ust = 1, x
            elif d != -1 and x <= ust * (1 - oran):
                d, alt = -1, x
            durum[i] = d
        return pd.Series(durum, index=kap.index)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        trend = self._trend(k, float(p["trend_yuzde"]))
        al = _seviye_asagi(r, float(p["os"])) & (trend == 1)
        cik = _seviye_yukari(r, float(p["ob"])) | (trend == -1)
        return _atr_stoplu(m, p, al, False, cikis_long=cik)


# ---------------------------------------------------------------- 756
class Bb12KesisimZaman4(_Taban):
    """X005:756 (1d iki yön): kapanış alt Bollinger bandını (12, 2sd) yukarı keserse long; üst bandı aşağı keserse short; girişten 4 bar
    sonra çık (CikisAyarlari.zaman_cikisi_mum=4). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"bb_n": 12, "bb_k": 2.0, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=4)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        return _atr_stoplu(m, p, _yukari(k, bb["alt"]), _asagi(k, bb["ust"]))


# ---------------------------------------------------------------- 758
class Rsi5DipTepeZaman4(_Taban):
    """X005:758 (1d iki yön): RSI(5) < 40 VE düşük > önceki düşük -> long; RSI(5) > 60 VE yüksek < önceki yüksek -> short; girişten 4 bar
    sonra çık (zaman_cikisi_mum=4). RSI Wilder. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"rsi_n": 5, "os": 40.0, "ob": 60.0, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=4)

    def sinyaller(self, m):
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi_n"]))
        al = ((r < float(p["os"])) & (m["dusuk"] > m["dusuk"].shift(1))).fillna(False)
        sat = ((r > float(p["ob"])) & (m["yuksek"] < m["yuksek"].shift(1))).fillna(False)
        return _atr_stoplu(m, p, al, sat)


# ---------------------------------------------------------------- 759
class ZSkorSmaFiltreIki(_Taban):
    """X005:759 (1d iki yön): z = (kapanış - SMA10) / std10 (örneklem std, ddof=1). Long: z -1'i aşağı keserken SMA(10) > SMA(100); short:
    z +1'i yukarı keserken SMA(10) < SMA(100). Long çıkış: z -0,5'i yukarı keserse ya da SMA10 SMA100'ü aşağı keserse; short çıkış: z
    +0,5'i aşağı keserse ya da SMA10 SMA100'ü yukarı keserse (kesişim yönü süzgeçle aynı yönde okundu). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"z_n": 10, "giris": 1.0, "cikis": 0.5, "sma_hizli": 10, "sma_yavas": 100, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        z = _rsi_z(k, int(p["z_n"]))
        hizli, yavas = g.sma(k, int(p["sma_hizli"])), g.sma(k, int(p["sma_yavas"]))
        gz, cz = float(p["giris"]), float(p["cikis"])
        al = _seviye_asagi(z, -gz) & (hizli > yavas)
        sat = _seviye_yukari(z, gz) & (hizli < yavas)
        cik_l = _seviye_yukari(z, -cz) | _asagi(hizli, yavas)
        cik_s = _seviye_asagi(z, cz) | _yukari(hizli, yavas)
        return _atr_stoplu(m, p, al, sat, cikis_long=cik_l, cikis_short=cik_s)


# ---------------------------------------------------------------- 760
class ZSkorAsiriSmaFiltre(_Taban):
    """X005:760 (1d long): z(10) < -2 VE SMA(10) > SMA(100) -> long; çıkış: z bir barda -0,5 altından +0,5 üstüne sıçrarsa ya da |z| < 0,5
    olursa; z = (kapanış - ort) / örneklem std (ddof=1). Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"z_n": 10, "giris": -2.0, "cikis": 0.5, "sma_hizli": 10, "sma_yavas": 100, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        z = _rsi_z(k, int(p["z_n"]))
        cz = float(p["cikis"])
        al = ((z < float(p["giris"])) & (g.sma(k, int(p["sma_hizli"])) > g.sma(k, int(p["sma_yavas"])))).fillna(False)
        cik = (z.abs() < cz) | ((z.shift(1) < -cz) & (z > cz))
        return _atr_stoplu(m, p, al, False, cikis_long=cik.fillna(False))


# ---------------------------------------------------------------- 762
class Sma200Rsi3Dip(_Taban):
    """X005:762 (1d long): kapanış > SMA(200) VE SMA(20) > SMA(20)[10 bar önce] VE RSI(3) < 10 -> long; kapanış SMA200 altına inerse ya da
    RSI(3) > 95 olursa kapat. RSI Wilder. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"sma_uzun": 200, "sma_kisa": 20, "egim_bar": 10, "rsi_n": 3, "giris": 10.0, "cikis_rsi": 95.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        uzun, kisa = g.sma(k, int(p["sma_uzun"])), g.sma(k, int(p["sma_kisa"]))
        r = g.rsi(k, int(p["rsi_n"]))
        al = ((k > uzun) & (kisa > kisa.shift(int(p["egim_bar"]))) & (r < float(p["giris"]))).fillna(False)
        return _atr_stoplu(m, p, al, False, cikis_long=((k < uzun) | (r > float(p["cikis_rsi"]))).fillna(False))


# ---------------------------------------------------------------- kayıt
SINIFLAR: dict = {}
VARYANTLAR: list = []
KODLANAMADI: list = []

_BOS = [{}]
_4H1D = ["4h", "1d"]


def _satir(kaynak_id, taban, ad, tflar, ozet, varyantlar=_BOS):
    """Kaynak satırı için alt sınıf (varsayılan = ilk varyant) üretir; VARYANTLAR'a her varyant x TF kaydı ekler (#v1.., varyant-ana)."""
    govde = {"__doc__": f"{kaynak_id}: {ozet}\n\n    Taban kural: {taban.__name__}.", "ad": ad,
             "varsayilan_parametreler": {**taban.varsayilan_parametreler, **varyantlar[0]}}
    sinif = type("S" + kaynak_id.split(":")[-1].replace("#", "_"), (taban,), govde)
    SINIFLAR[ad] = sinif
    no = 0
    for v in varyantlar:
        for tf in tflar:
            no += 1
            VARYANTLAR.append({"kimlik": f"{kaynak_id}#v{no}", "sinif": ad,
                               "parametreler": {**taban.varsayilan_parametreler, **v}, "tf": tf})
    return sinif


S0659 = _satir("HAM:X005:659", BbDonusAdxSma200, "kapanis__bb-adx-sma200-s0659", ["1d"],
               "SMA200 üstünde, ADX<20, alt BB altında kapanışta long; hedef orta bant, 5 mum, stop min(düşük, giriş-ATR).")
S0661 = _satir("HAM:X005:661", McGinleyStopReverse, "kapanis__mcginley-sar-s0661", ["1d"],
               "McGinley(25) kesişimi + 3 bar teyit, iki yön, stop %10, hedef %40, ters koşulda çevir.")
S0664 = _satir("HAM:X005:664", WaveTrendKesisim, "kapanis__wavetrend-s0664", ["1d"], "WaveTrend wt1/wt2 kesişimi long-only.")
S0666 = _satir("HAM:X005:666", ZirveYakinligiHacim, "kapanis__zirve-hacim-s0666", ["1d"],
               "252g zirvenin %2 yakınında + SMA200 + hacim; 3 gün tut, stop 2xATR.")
S0671 = _satir("HAM:X005:671", StokastikSlowKesisim, "kapanis__stok-5-5-3-s0671", ["1d"], "Stokastik(5,5,3) %K/%D kesişimi long-only.")
S0672 = _satir("HAM:X005:672", VarPmaxKesisim, "kapanis__var-pmax-s0672", ["5m"], "VAR(10) / PMax(ATR10 x3) kesişimi, iki yön.")
S0674 = _satir("HAM:X005:674", HaWmaPsarMacd, "kapanis__ha-wma-psar-macd-s0674", ["15m"],
               "1h HA/WMA/PSAR yükselen trend + 15m MACD histogram, long-only.")
S0676 = _satir("HAM:X005:676", AlphaTrendMfi, "kapanis__alphatrend-s0676", _4H1D, "MFI'lı AlphaTrend 2 bar gecikme kesişimi, long-only.")
S0678 = _satir("HAM:X005:678", BbKesisimRsiTp, "kapanis__bb-kesisim-rsi-s0678", ["15m"],
               "BB bandına geri dönüş + RSI(20), hedef karşı bant, stop %2,5.")
S0679 = _satir("HAM:X005:679", BbHacimAdxRoi, "kapanis__bb-hacim-roi-s0679", ["15m"],
               "BB dışı ilk kapanış + RSI/hacim/ADX, kademeli ROI, iz süren kâr, stop %30.")
S0680 = _satir("HAM:X005:680", SmaRsiDurumIki, "kapanis__sma-rsi-durum-s0680", ["1h", "1d"], "SMA9/21 + RSI14 durum kuralı, hep piyasada.")
S0681 = _satir("HAM:X005:681", BbOrtaKesisimDisBantCikis, "kapanis__bb27-orta-s0681", ["1h"],
               "BB(27,2) orta bant kesişimi giriş, dış banda dokunuşta çıkış.")
S0682 = _satir("HAM:X005:682", TumZamanZirveWma, "kapanis__tumzaman-zirve-s0682", ["1d"], "Tüm zamanların zirvesi kırılımı, WMA20 altı çıkış.")
S0683 = _satir("HAM:X005:683", Sma20EgimDonusRsi, "kapanis__sma20-donus-s0683", ["1d"], "SMA20 eğim dönüşü + RSI(10) bandı, long-only.")
S0684 = _satir("HAM:X005:684", Vwap3OranDurum, "kapanis__vwap3-oran-s0684", ["15m", "30m"], "Fiyat/VWAP(3) oranı eşik durumu, iki yön.")
S0693 = _satir("HAM:X005:693", BbUstAlAltSat, "kapanis__bb-ust-al-s0693", _4H1D, "BB üst bant kapanışı al, alt bant kapanışı sat.")
S0695 = _satir("HAM:X005:695", Sma20GeriCekilmeOnay, "kapanis__sma20-geri-onay-s0695", ["1d"],
               "SMA20 yükseliş + 3 mum düşük kurulum, ertesi kapanış onayı, hedef 2R, stop 1R.")
S0697 = _satir("HAM:X005:697", Sma20KanalDurTers, "kapanis__sma20-kanal-sar-s0697", _4H1D, "SMA20 yönünde 3 bar kanal dur-ve-ters, iki yön.")
S0698 = _satir("HAM:X005:698", YavasStokastikAsiri, "kapanis__yavas-stok-s0698", _4H1D, "Yavaş Stokastik(14,3,3) <20 al, >80 sat.")
S0706 = _satir("HAM:X005:706", BbDisiKapanisIciKapanis, "kapanis__bb-ici-donus-s0706", ["1d"],
               "BB dışı kapanış + sonraki mum içeride kapanış long, ayna çıkış; sapma 2 / 2,5 / 3.",
               [{"bb_sapma": 2.0}, {"bb_sapma": 2.5}, {"bb_sapma": 3.0}])
S0710 = _satir("HAM:X005:710", LrEgimDonusIki, "kapanis__lr40-egim-s0710", _4H1D, "LR(40) eğim işaret dönüşü, iki yön.")
S0711 = _satir("HAM:X005:711", LrKanalDonus, "kapanis__lr20-kanal-s0711", _4H1D, "LR(20) +/-%5 kanal kesişimi, eğim<0 iken long.")
S0718 = _satir("HAM:X005:718", KorelasyonTrend, "kapanis__korelasyon-trend-s0718", ["1d"], "Kapanış-zaman Pearson(20) sıfır çizgisi kesişimi.")
S0724 = _satir("HAM:X005:724", SuperTrendYatayKurulum, "kapanis__st-yatay-kurulum-s0724", ["1d"],
               "SuperTrend üstü yatay çizgi + düşen yüksekler kurulumu, ertesi kapanış onayı.")
S0725 = _satir("HAM:X005:725", SuperTrendIkiCarpan, "kapanis__st-2-3-s0725", ["1d"], "Supertrend çarpan 2 / çarpan 3 çizgi kesişimi.")
S0727 = _satir("HAM:X005:727", HaTipikEmaDurum, "kapanis__ha-tipik-ema-s0727", _4H1D,
               "Tipik fiyat EMA5 / HA kapanış EMA8 durumu, stop %25, %15'te başabaş.")
S0730 = _satir("HAM:X005:730", ObvmKesisim, "kapanis__obvm-s0730", _4H1D, "OBV EMA7 / SMA10 sinyal kesişimi, iki yön.")
S0733 = _satir("HAM:X005:733", AdxEsikSma50Iki, "kapanis__adx-sma50-s0733", ["1d"], "ADX 30/22 eşik kesişimi + SMA50 yönü, iki yön.")
S0737 = _satir("HAM:X005:737", AylikSma8Ters, "kapanis__aylik-sma8-s0737", ["1d"], "Aylık kapanış SMA(8) üstü long altı short (ay sonu).")
S0751 = _satir("HAM:X005:751", RsiTrendYuzde20, "kapanis__rsi-trend20-s0751", ["1d"], "%20 zigzag yükseliş trendinde RSI30 aşağı kesişimi al.")
S0756 = _satir("HAM:X005:756", Bb12KesisimZaman4, "kapanis__bb12-kesisim-s0756", ["1d"], "BB(12,2) band kesişimi, 4 bar sonra çık.")
S0758 = _satir("HAM:X005:758", Rsi5DipTepeZaman4, "kapanis__rsi5-donus-s0758", ["1d"], "RSI(5) 40/60 + düşük/yüksek filtresi, 4 bar sonra çık.")
S0759 = _satir("HAM:X005:759", ZSkorSmaFiltreIki, "kapanis__zskor-sma-s0759", ["1d"], "Z-skor +/-1 kesişimi + SMA10/100 süzgeci, iki yön.")
S0760 = _satir("HAM:X005:760", ZSkorAsiriSmaFiltre, "kapanis__zskor-asiri-s0760", ["1d"], "Z-skor < -2 + SMA10>SMA100 long, |z|<0,5 çıkış.")
S0762 = _satir("HAM:X005:762", Sma200Rsi3Dip, "kapanis__sma200-rsi3-s0762", ["1d"], "SMA200 üstünde RSI(3)<10 dip alımı, RSI>95 / SMA200 altı çıkış.")

KODLANAMADI = [
    {"kimlik": "HAM:X005:673",
     "neden": "kaynakta formülü olmayan gösterge: TOTT/SOTT (sott_period_k, sott_smooth_k), HOTT/LOTT kapısı, minör trend ve ROTT yaması "
              "kural metninde yalnız parametre adlarıyla geçiyor; tanımları yazılı değil, kaynak kodu kopyalanamaz -> uydurma çözüm yok."},
    # 699, 726, 736: kod_g8_modul.py (pozisyon bilinçli).
    {"kimlik": "HAM:X005:742",
     "neden": "kaynakta formülü olmayan gösterge: 'alt/üst bölge (Zone 0,20)' ve 'karşı bölge fiyat hedefi' kural metninde tanımlı değil "
              "(bölgenin neye göre ölçüldüğü yazılı değil) -> uydurma çözüm yok."},
]
