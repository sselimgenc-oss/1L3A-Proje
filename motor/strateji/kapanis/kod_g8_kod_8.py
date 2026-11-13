"""Kapanış turu kodlama partisi g8_kod_8 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_8.csv, 40 kaynak satırı).

HAM:X005:* (trend / ortalamaya dönüş listesi) ve HAM:X008:* (ajan2 kaynak raporu) satırları. Her satır için bir sınıf vardır
(38 sınıf); kurallar `kural_tam` metninden kendi kodumuzla yazıldı, üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan
(motor sonraki açılışta doldurur); gelecek verisi yok. Kaynak stopu yoksa ATR(14)x3 uyarlaması; kaynakta yüzde stop varsa
sinyal kapanışından hesaplanır (dolum sonraki açılış olduğundan gerçek mesafe biraz farklı olabilir).

Genel biçim kararları:
- Durum koşullu girişler her mumda `yon != 0` üretir; motor pozisyon açıkken yeni girişi atlar. "Keser / aşınca" diyen
  kurallar kesişim olayıdır: x[t-1] <= y[t-1] ve x[t] > y[t]; seviye kesişimi x[t-1] < s <= x[t].
- Yönlü çıkış `cikis_long` / `cikis_short` sütunlarıyla verilir (sınıfın kendi çıkış sinyali; pozisyon durumu kestirilmez).
- Kapanış bazlı kâr hedefi ve süre çıkışı motorun KAPANIŞTA çalışan modülleriyle (`CikisAyarlari.azalan_roi` = kapanıştaki
  kâr% >= hedef, `zaman_cikisi_mum`; kod_g8_kod_1 emsali). Sınıflar bunları `varsayilan_parametreler`den kurar.
- Arşiv taraması (kural d): hiçbir arşiv sınıfı bu satırların kuralını birebir uygulamıyor (ör. Roc20Ls eşiksiz işaret kuralı,
  Sma200Ls bant/5 gün teyitsiz, Ifr2 Ichimoku süzgeçli, SupertrendPsar çizgi stoplu/dönüş girişli, MaKesisim toleranssız,
  BantDonus RSI/ADX süzgeçli), bu yüzden yeni sınıf yazıldı.

KODLANAMADI (VARYANTLAR dışında, bkz. `KODLANAMADI`): X005:863 (örtüşen dilimli net pozisyon), X005:879 (giriş sonrası zirveden
%20 geri çekilme: pozisyon bilinçli çıkış gerekli).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.dis._gosterge_d2 import sikisma_momentum
from motor.strateji.temel import Strateji


# ---------------------------------------------------------------- yardımcılar
def _seri(y, ref: pd.Series) -> pd.Series:
    return y if isinstance(y, pd.Series) else pd.Series(float(y), index=ref.index)


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


def _hepsi(kosul: pd.Series, n: int) -> pd.Series:
    """Son n mumun (bu mum dahil) hepsinde koşul doğru."""
    return (kosul.fillna(False).astype(float).rolling(int(n), min_periods=int(n)).min() == 1.0)


def _atr_stop(m: pd.DataFrame, p: dict):
    a = float(p["atr_k"]) * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
    return m["kapanis"] - a, m["kapanis"] + a


def _ekle(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _rsi_basit(kap: pd.Series, n: int) -> pd.Series:
    """Basit ortalamalı RSI: yukarı/aşağı hareketlerin n'lik SMA'sı (Wilder yumuşatması yok)."""
    fark = kap.diff()
    yukari = fark.clip(lower=0.0).rolling(n, min_periods=n).mean()
    asagi = (-fark).clip(lower=0.0).rolling(n, min_periods=n).mean()
    return 100.0 - 100.0 / (1.0 + yukari / asagi)


def _roc_bant(m: pd.DataFrame, roc_n: int, ema_n: int, rms_n: int):
    """ROC(roc_n) yüzde, EMA(ema_n) ile yumuşatılmış; RMS = karekök(SMA(ham ROC^2, rms_n)) (ham ROC varsayımı)."""
    k = m["kapanis"]
    roc = (k / k.shift(int(roc_n)) - 1.0) * 100.0
    sm = g.ema(roc, int(ema_n))
    rms = np.sqrt(g.sma(roc ** 2, int(rms_n)))
    return sm, rms


class _Taban(Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            kw = self._cikis_kw(self.parametreler)
            if kw:
                self.cikis_ayarlari = CikisAyarlari(**kw)

    @staticmethod
    def _cikis_kw(p: dict) -> dict:
        """Parametrelerden kapanışta çalışan motor çıkışları: kâr hedefi (yüzde) ve süre (mum)."""
        kw = {}
        if p.get("hedef_yuzde"):
            kw["azalan_roi"] = ((0, float(p["hedef_yuzde"]) * 100.0),)
        if p.get("tutma_bar"):
            kw["zaman_cikisi_mum"] = int(p["tutma_bar"])
        return kw

    def cikis_var_mi(self) -> bool:
        return True


SINIFLAR: dict = {}


def _kaydet(sinif):
    SINIFLAR[sinif.ad] = sinif
    return sinif


_ATR = {"atr_n": 14, "atr_k": 3.0}


# ================================================================ X005:763
@_kaydet
class S0763(_Taban):
    """HAM:X005:763 (1d, long): kapanış > SMA(200) VE SMA(20) 10 bar öncesinden yüksek (yükselen) VE RSI(3) < 10 -> long (durum).
    Çıkış: kapanış < SMA(200) ya da SMA(20) < SMA(20)[10]. Stop yok -> ATR(14)x3 (uyarlama). "SMA20 yükselen" = SMA20 >
    SMA20[egim_bar] okuması (çıkıştaki karşıt koşulla simetrik)."""
    ad = "kapanis__rsi3-sma200-egim-s0763"
    varsayilan_parametreler = {"sma_uzun": 200, "sma_kisa": 20, "egim_bar": 10, "rsi_n": 3, "giris": 10.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s200, s20 = g.sma(k, int(p["sma_uzun"])), g.sma(k, int(p["sma_kisa"]))
        e = int(p["egim_bar"])
        gir = (k > s200) & (s20 > s20.shift(e)) & (g.rsi(k, int(p["rsi_n"])) < float(p["giris"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss), cikis_long=(k < s200) | (s20 < s20.shift(e)))


# ================================================================ X005:764
@_kaydet
class S0764(_Taban):
    """HAM:X005:764 (1d, iki yön): DMI osilatörü = +DI(10) - -DI(10); DMI stokastiği = osilatör üzerinde Stokastik(10), 3 SMA
    yumuşatma (0-100). Osilatör > 0 iken stokastik 10'u yukarı keserse long; osilatör < 0 iken 90'ı aşağı keserse short.
    Çıkış: 5 bar tutma (zaman_cikisi_mum=5). Stop yok -> ATR(14)x3 (uyarlama). Stokastik ölçeği 0-100."""
    ad = "kapanis__dmi-stokastik-s0764"
    varsayilan_parametreler = {"dmi_n": 10, "stoch_n": 10, "stoch_smooth": 3, "long_esik": 10.0, "short_esik": 90.0,
                               "tutma_bar": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        a = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], int(p["dmi_n"]))
        osc = a["arti_di"] - a["eksi_di"]
        n = int(p["stoch_n"])
        hh, ll = osc.rolling(n, min_periods=n).max(), osc.rolling(n, min_periods=n).min()
        st = g.sma(100.0 * (osc - ll) / (hh - ll).where(lambda x: x > 0), int(p["stoch_smooth"]))
        al = (osc > 0) & _seviye_yukari(st, float(p["long_esik"]))
        sat = (osc < 0) & _seviye_asagi(st, float(p["short_esik"]))
        sl, ss = _atr_stop(m, p)
        return cerceve(m, al, sat, sl, ss)


# ================================================================ X005:768
@_kaydet
class S0768(_Taban):
    """HAM:X005:768 (1d, iki yön): ROC(12) yüzde, EMA(3) yumuşatılmış; bant = +/- 1 x RMS (karekök(SMA(ham ROC^2, 12))).
    Long: kapanış > EMA(200) iken yumuşak ROC alt bandı (-1 RMS) yukarı keserse; short: kapanış <= EMA(200) iken üst bandı
    aşağı keserse. Long çıkış: ROC üst bandı aşağı keserse; short çıkış: alt bandı yukarı keserse. Stop yok -> ATR(14)x3.
    Not: RMS ham ROC'tan (kaynak özeti belirsiz)."""
    ad = "kapanis__roc-bant-iki-yon-s0768"
    varsayilan_parametreler = {"roc_n": 12, "ema_n": 3, "rms_n": 12, "carpan_ust": 1.0, "carpan_alt": -1.0, "trend_ema": 200,
                               **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sm, rms = _roc_bant(m, p["roc_n"], p["ema_n"], p["rms_n"])
        ust, alt = float(p["carpan_ust"]) * rms, float(p["carpan_alt"]) * rms
        tr = g.ema(k, int(p["trend_ema"]))
        al = (k > tr) & _yukari(sm, alt)
        sat = (k <= tr) & _asagi(sm, ust)
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=_asagi(sm, ust), cikis_short=_yukari(sm, alt))


# ================================================================ X005:769
@_kaydet
class S0769(_Taban):
    """HAM:X005:769 (1d, long): kapanış > EMA(200) VE yumuşak ROC (ROCWB 12,3,12) yukarı dönüyor (ROC[t] > ROC[t-1]) VE önceki
    bar ROC alt bandın (-1 RMS) altında -> long. Çıkış: ROC aşağı dönüp üst bandı (+1 RMS) aşağı keserse. Stop yok -> ATR(14)x3.
    Not: "ROC" = ROCWB göstergesinin yumuşatılmış (EMA 3) çizgisi (kaynak metni ham/yumuşak ayrımını yazmıyor)."""
    ad = "kapanis__roc-bant-donus-s0769"
    varsayilan_parametreler = {"roc_n": 12, "ema_n": 3, "rms_n": 12, "trend_ema": 200, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sm, rms = _roc_bant(m, p["roc_n"], p["ema_n"], p["rms_n"])
        gir = (k > g.ema(k, int(p["trend_ema"]))) & (sm > sm.shift(1)) & (sm.shift(1) < (-rms).shift(1))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss), cikis_long=_asagi(sm, rms) & (sm < sm.shift(1)))


# ================================================================ X005:771
@_kaydet
class S0771(_Taban):
    """HAM:X005:771 (1d, iki yön): kapanış tabanlı stokastik = (C-LLV(C,7))/(HHV(C,7)-LLV(C,7)), 3 SMA yumuşatma. Long: stok < 0,30
    VE kapanış > EMA(271) (bu mum kapanışında); short: stok > 0,70 VE kapanış < EMA(271). Long çıkış: stok > 0,70 ya da kapanış <
    EMA(271); short çıkış: stok < 0,30 ya da kapanış > EMA(271). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__stokastik-colby-s0771"
    varsayilan_parametreler = {"stok_n": 7, "stok_smooth": 3, "alt": 0.30, "ust": 0.70, "ema_n": 271, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["stok_n"])
        hh, ll = k.rolling(n, min_periods=n).max(), k.rolling(n, min_periods=n).min()
        st = g.sma((k - ll) / (hh - ll).where(lambda x: x > 0), int(p["stok_smooth"]))
        ema = g.ema(k, int(p["ema_n"]))
        alt, ust = float(p["alt"]), float(p["ust"])
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, (st < alt) & (k > ema), (st > ust) & (k < ema), sl, ss),
                     cikis_long=(st > ust) | (k < ema), cikis_short=(st < alt) | (k > ema))


# ================================================================ X005:772
@_kaydet
class S0772(_Taban):
    """HAM:X005:772 (1d, iki yön, dur-ve-çevir): yumuşatılmış StochK(7,3) < 30 VE kapanış > EMA(271) -> long; StochK > 70 VE kapanış <
    EMA(271) -> short; ayrı çıkış yok, karşı koşulda ters çevir (long, short koşulunda kapanır ve tersi). Stop yok -> ATR(14)x3.
    StochK = yüksek/düşük tabanlı hızlı %K'nın 3 SMA'sı (g.stokastik d)."""
    ad = "kapanis__stokastik-ema271-s0772"
    varsayilan_parametreler = {"stok_n": 7, "stok_smooth": 3, "alt": 30.0, "ust": 70.0, "ema_n": 271, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        st = g.stokastik(m["yuksek"], m["dusuk"], k, int(p["stok_n"]), int(p["stok_smooth"]))["d"]
        ema = g.ema(k, int(p["ema_n"]))
        al, sat = (st < float(p["alt"])) & (k > ema), (st > float(p["ust"])) & (k < ema)
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X005:779
def _dinamik_n(k: pd.Series, n0: int, n_min: int, n_max: int, sigma_n: int) -> np.ndarray:
    """N her gün N*(1 + dsigma/sigma) ile güncellenir (sigma = son sigma_n kapanışın std'si, dsigma = sigma'nın günlük farkı),
    [n_min, n_max] arasına sınırlanır. İleri yürüyen (nedensel)."""
    sig = k.rolling(sigma_n, min_periods=sigma_n).std(ddof=0).to_numpy()
    n = np.full(len(k), np.nan)
    cur = float(n0)
    for i in range(len(k)):
        if np.isnan(sig[i]):
            continue
        if i > 0 and not np.isnan(sig[i - 1]) and sig[i] > 0:
            cur = float(np.floor(cur * (1.0 + (sig[i] - sig[i - 1]) / sig[i]) + 0.5))
            cur = min(max(cur, float(n_min)), float(n_max))
        n[i] = cur
    return n


@_kaydet
class S0779(_Taban):
    """HAM:X005:779 (1d, iki yön; Dynamic Breakout II): N adaptif (başlangıç 20, [20,60], sigma = son 30 kapanışın std'si).
    Long: kapanış üst Bollinger (N gün, k=2, EMA ortalama) üstünde VE kapanış önceki N günün en yükseğinin üstünde; short ayna.
    Long çıkış: kapanış son N kapanışın ortalamasının altına inince; short çıkış: üstüne çıkınca. Ayrı stop yok -> ATR(14)x3
    felaket stopu. Uyarlamalar: "önceki kapanış/fiyat" = sinyal mumunun kapanışı; her mumda EMA, o günkü N'lik pencerede
    (pencere başlangıcından başlayan EMA) hesaplanır; std ddof=0."""
    ad = "kapanis__dinamik-kirilim-s0779"
    varsayilan_parametreler = {"n0": 20, "n_min": 20, "n_max": 60, "sigma_n": 30, "bb_k": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        nn = _dinamik_n(k, int(p["n0"]), int(p["n_min"]), int(p["n_max"]), int(p["sigma_n"]))
        kv, hv, dv = k.to_numpy(float), h.to_numpy(float), d.to_numpy(float)
        sz = len(kv)
        al, sat = np.zeros(sz, bool), np.zeros(sz, bool)
        cl, cs = np.zeros(sz, bool), np.zeros(sz, bool)
        bk = float(p["bb_k"])
        for i in range(sz):
            if np.isnan(nn[i]):
                continue
            n = int(nn[i])
            if i < n:
                continue
            w = kv[i - n + 1:i + 1]
            alfa = 2.0 / (n + 1.0)
            ema = w[0]
            for x in w[1:]:
                ema = alfa * x + (1.0 - alfa) * ema
            std = w.std()
            ort = w.mean()
            al[i] = kv[i] > ema + bk * std and kv[i] > hv[i - n:i].max()
            sat[i] = kv[i] < ema - bk * std and kv[i] < dv[i - n:i].min()
            cl[i] = kv[i] < ort
            cs[i] = kv[i] > ort
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, pd.Series(al, index=m.index), pd.Series(sat, index=m.index), sl, ss),
                     cikis_long=pd.Series(cl, index=m.index), cikis_short=pd.Series(cs, index=m.index))


# ================================================================ X005:780
@_kaydet
class S0780(_Taban):
    """HAM:X005:780 (1h, iki yön, her zaman piyasada; Dual Thrust): her UTC günü açılışında son n=4 tamamlanmış günün HH, HC, LC,
    LL değerleriyle Range = max(HH-LC, HC-LL). Fiyat gün açılışı + 0,5 x Range üstüne çıkınca long, açılış - 0,5 x Range altına
    inince short; ters kırılım pozisyonu çevirir (gece taşır). Fiyat = 1h mum kapanışı (kapanışta sinyal). Stop yok -> ATR(14)x3."""
    ad = "kapanis__dual-thrust-utc-s0780"
    stil = "daytrade"
    varsayilan_parametreler = {"n": 4, "k1": 0.5, "k2": 0.5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        gun = m.index.normalize()
        gr = m.groupby(gun)
        dh, dl, dc, do = gr["yuksek"].max(), gr["dusuk"].min(), gr["kapanis"].last(), gr["acilis"].first()
        n = int(p["n"])
        hh = dh.rolling(n, min_periods=n).max().shift(1)
        ll = dl.rolling(n, min_periods=n).min().shift(1)
        hc = dc.rolling(n, min_periods=n).max().shift(1)
        lc = dc.rolling(n, min_periods=n).min().shift(1)
        aralik = pd.concat([hh - lc, hc - ll], axis=1).max(axis=1)
        esle = lambda s: pd.Series(s.reindex(gun).to_numpy(), index=m.index)  # noqa: E731
        ac, rg = esle(do), esle(aralik)
        al = k > ac + float(p["k1"]) * rg
        sat = k < ac - float(p["k2"]) * rg
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X005:790
@_kaydet
class S0790(_Taban):
    """HAM:X005:790 (1d, iki yön; LEAN RSI alfa modeli): RSI(14, Wilder) 30'un altına inince TRIPPED_LOW durumu ve long; 70'in
    üstüne çıkınca TRIPPED_HIGH ve short; her sinyal 14 bar (zaman_cikisi_mum=14). Yeni sinyal için RSI düşük durumdan 35 üstüne,
    yüksek durumdan 65 altına dönmeli (histerezis; durum sürerken tekrar sinyal yok). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__rsi-alfa-histerezis-s0790"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30.0, "ust": 70.0, "reset_alt": 35.0, "reset_ust": 65.0, "tutma_bar": 14,
                               **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi_n"])).to_numpy()
        al, sat = np.zeros(len(r), bool), np.zeros(len(r), bool)
        durum = 0                                   # 0 nötr, 1 düşük, -1 yüksek
        for i in range(len(r)):
            if np.isnan(r[i]):
                continue
            if durum != -1 and r[i] > float(p["ust"]):
                durum, sat[i] = -1, True
            elif durum != 1 and r[i] < float(p["alt"]):
                durum, al[i] = 1, True
            elif durum == 1 and r[i] > float(p["reset_alt"]):
                durum = 0
            elif durum == -1 and r[i] < float(p["reset_ust"]):
                durum = 0
        sl, ss = _atr_stop(m, p)
        return cerceve(m, pd.Series(al, index=m.index), pd.Series(sat, index=m.index), sl, ss)


# ================================================================ X005:793
@_kaydet
class S0793(_Taban):
    """HAM:X005:793 (1d, iki yön; LEAN MACD alfa modeli): oran = MACD(12,26,9) sinyal çizgisi / kapanış. Oran +%1'i aşınca long,
    -%1'in altına inince short; oran +-%1 bandının içine dönünce pozisyon kapanır (long: oran <= +%1; short: oran >= -%1);
    pozisyon süresi 12 bar (zaman_cikisi_mum=12). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__macd-sinyal-oran-s0793"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "esik": 0.01, "tutma_bar": 12, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        oran = g.macd(k, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))["sinyal"] / k
        e = float(p["esik"])
        al, sat = _seviye_yukari(oran, e), _seviye_asagi(oran, -e)
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=oran <= e, cikis_short=oran >= -e)


# ================================================================ X005:802
@_kaydet
class S0802(_Taban):
    """HAM:X005:802 (4h|1d, long-only): RSI(14) < 30 VE 100-|W%R(14)| < 10 (W%R kapanış serisinin 14 bar en yüksek/en düşüğüyle;
    100-|W%R| = 100 x (C-LLV)/(HHV-LLV)) -> long (durum). Çıkış: RSI(14) > 90 ya da 100-|W%R| > 95. Stop yok -> ATR(14)x3
    (uyarlama). Standart (K6): TF yazılı değil, 4h ve 1d iki hipotez (VARYANTLAR)."""
    ad = "kapanis__rsi-williams-kapanis-s0802"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30.0, "wr_n": 14, "wr_donusum_al": 10.0, "rsi_cik": 90.0,
                               "wr_donusum_cik": 95.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["wr_n"])
        hh, ll = k.rolling(n, min_periods=n).max(), k.rolling(n, min_periods=n).min()
        wr = 100.0 * (k - ll) / (hh - ll).where(lambda x: x > 0)
        r = g.rsi(k, int(p["rsi_n"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, (r < float(p["rsi_al"])) & (wr < float(p["wr_donusum_al"])), False, sl, ss),
                     cikis_long=(r > float(p["rsi_cik"])) | (wr > float(p["wr_donusum_cik"])))


# ================================================================ X005:809
@_kaydet
class S0809(_Taban):
    """HAM:X005:809 (1d, iki yön, dur-ve-çevir): ADX(14) > 20 VE +DI > -DI -> long; ADX(14) > 20 VE -DI > +DI -> short;
    ADX <= 20 iken mevcut pozisyon korunur (çıkış yalnız ters koşulda). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__adx-di-cevir-s0809"
    varsayilan_parametreler = {"adx_n": 14, "adx_esik": 20.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        a = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], int(p["adx_n"]))
        guclu = a["adx"] > float(p["adx_esik"])
        al, sat = guclu & (a["arti_di"] > a["eksi_di"]), guclu & (a["eksi_di"] > a["arti_di"])
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X005:812
@_kaydet
class S0812(_Taban):
    """HAM:X005:812 (30m, iki yön): MACD(12,26,9) çizgisi sinyali yukarı keserse long, aşağı keserse short (açık long varsa kapanıp
    short). Kâr hedefi giriş +%25, sabit zarar kes giriş %5 (long ve short). Hedef ve stop sinyal kapanışından hesaplanır."""
    ad = "kapanis__macd-hedef25-stop5-s0812"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "hedef_yuzde": 0.25, "stop_yuzde": 0.05}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        mc = g.macd(k, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        al, sat = _yukari(mc["macd"], mc["sinyal"]), _asagi(mc["macd"], mc["sinyal"])
        sy, hy = float(p["stop_yuzde"]), float(p["hedef_yuzde"])
        s = cerceve(m, al, sat, k * (1 - sy), k * (1 + sy), hedef_l=k * (1 + hy), hedef_s=k * (1 - hy))
        return _ekle(s, cikis_long=sat, cikis_short=al)

    @staticmethod
    def _cikis_kw(p):
        return {}


# ================================================================ X005:816
@_kaydet
class S0816(_Taban):
    """HAM:X005:816 (1d, long): kapanış > SMA(50) > SMA(150) > SMA(200) VE ROC(7) >= 0 VE RSI(2) <= 30 -> piyasa emriyle (sonraki
    açılış) long. Çıkış: gerçekleşmemiş kâr >= %3 (kapanışta sınanır, motor azalan_roi) ya da 4 günlük pozisyon (zaman_cikisi_mum=4);
    gerçekleşmemiş zarar <= -%8 (stop = sinyal kapanışı x 0,92). Kesitsel ROC sıralaması atıldı; hisse hacim/fiyat filtreleri yok."""
    ad = "kapanis__trend-rsi2-dip-s0816"
    varsayilan_parametreler = {"sma_a": 50, "sma_b": 150, "sma_c": 200, "roc_n": 7, "rsi_n": 2, "rsi_max": 30.0,
                               "hedef_yuzde": 0.03, "tutma_bar": 4, "stop_yuzde": 0.08}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a, b, c = g.sma(k, int(p["sma_a"])), g.sma(k, int(p["sma_b"])), g.sma(k, int(p["sma_c"]))
        gir = ((k > a) & (a > b) & (b > c) & (k >= k.shift(int(p["roc_n"])))
               & (g.rsi(k, int(p["rsi_n"])) <= float(p["rsi_max"])))
        sy = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sy), k * (1 + sy))


# ================================================================ X005:817
@_kaydet
class S0817(_Taban):
    """HAM:X005:817 (1d, short): RSI(3) >= 85 VE son 3 kapanış art arda yükselen (3 ardışık yükseliş: C>C1>C2>C3) VE ADX(7) > 50 VE
    ATR(10)/fiyat > %5 -> short. Çıkış: gerçekleşmemiş kâr >= %4 (azalan_roi) ya da 2 günlük pozisyon (zaman_cikisi_mum=2);
    zarar <= -%20 (stop = sinyal kapanışı x 1,20). Piyasa değeri sıralaması (veri dışı) uygulanmadı."""
    ad = "kapanis__rsi3-asiri-short-s0817"
    varsayilan_parametreler = {"rsi_n": 3, "rsi_min": 85.0, "yukselen_kapanis": 3, "adx_n": 7, "adx_min": 50.0, "atr_n": 10,
                               "natr_min": 0.05, "hedef_yuzde": 0.04, "tutma_bar": 2, "stop_yuzde": 0.20}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        yuk = _hepsi(k.diff() > 0, int(p["yukselen_kapanis"]))
        natr = g.atr(h, d, k, int(p["atr_n"])) / k
        sat = ((g.rsi(k, int(p["rsi_n"])) >= float(p["rsi_min"])) & yuk
               & (g.adx(h, d, k, int(p["adx_n"]))["adx"] > float(p["adx_min"])) & (natr > float(p["natr_min"])))
        sy = float(p["stop_yuzde"])
        return cerceve(m, False, sat, k * (1 - sy), k * (1 + sy))


# ================================================================ X005:818
@_kaydet
class S0818(_Taban):
    """HAM:X005:818 (1d, long): RSI(3) < 30 VE kapanış > SMA(50) > SMA(150) VE kapanış <= Bollinger(21, 2sd) alt bandı -> long.
    Çıkış: gerçekleşmemiş kâr >= %3 (azalan_roi) ya da 4 günlük pozisyon; zarar <= -%20 (stop = kapanış x 0,80).
    Kesitsel RSI sıralaması atıldı; hisse filtreleri uygulanmadı."""
    ad = "kapanis__bb-rsi3-dip-s0818"
    varsayilan_parametreler = {"rsi_n": 3, "rsi_max": 30.0, "sma_a": 50, "sma_b": 150, "bb_n": 21, "bb_k": 2.0,
                               "hedef_yuzde": 0.03, "tutma_bar": 4, "stop_yuzde": 0.20}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a, b = g.sma(k, int(p["sma_a"])), g.sma(k, int(p["sma_b"]))
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        gir = (g.rsi(k, int(p["rsi_n"])) < float(p["rsi_max"])) & (k > a) & (a > b) & (k <= bb["alt"])
        sy = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sy), k * (1 + sy))


# ================================================================ X005:819
@_kaydet
class S0819(_Taban):
    """HAM:X005:819 (1d, long): kapanış > SMA(50) > SMA(150) > SMA(200) VE EMA(21) > SMA(50) VE EMA(7) > EMA(7)[2 gün önce] VE
    EMA21 x 0,98 <= kapanış <= EMA21 -> long. Çıkış: gerçekleşmemiş kâr >= %30 (azalan_roi) ya da 4 günlük pozisyon; zarar <=
    -%5 (stop = kapanış x 0,95)."""
    ad = "kapanis__ema21-geri-cekilme-s0819"
    varsayilan_parametreler = {"sma_a": 50, "sma_b": 150, "sma_c": 200, "ema_kisa": 7, "ema_orta": 21, "bant": 0.02,
                               "hedef_yuzde": 0.30, "tutma_bar": 4, "stop_yuzde": 0.05}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a, b, c = g.sma(k, int(p["sma_a"])), g.sma(k, int(p["sma_b"])), g.sma(k, int(p["sma_c"]))
        e7, e21 = g.ema(k, int(p["ema_kisa"])), g.ema(k, int(p["ema_orta"]))
        gir = ((k > a) & (a > b) & (b > c) & (e21 > a) & (e7 > e7.shift(2))
               & (k >= e21 * (1 - float(p["bant"]))) & (k <= e21))
        sy = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sy), k * (1 + sy))


# ================================================================ X005:820
@_kaydet
class S0820(_Taban):
    """HAM:X005:820 (1d, long): RSI(3) < 30 VE kapanış > SMA(50) VE ADX(7) > 45 VE ATR(10)/fiyat >= %4 -> long. Çıkış: gerçekleşmemiş
    kâr >= %3 (azalan_roi) ya da 4 günlük pozisyon; zarar <= -%20 (stop = kapanış x 0,80). ETF evreni kripto13'e uyarlandı;
    RSI sıralaması atlandı."""
    ad = "kapanis__rsi3-adx7-dip-s0820"
    varsayilan_parametreler = {"rsi_n": 3, "rsi_max": 30.0, "sma_n": 50, "adx_n": 7, "adx_min": 45.0, "atr_n": 10,
                               "natr_min": 0.04, "hedef_yuzde": 0.03, "tutma_bar": 4, "stop_yuzde": 0.20}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        natr = g.atr(h, d, k, int(p["atr_n"])) / k
        gir = ((g.rsi(k, int(p["rsi_n"])) < float(p["rsi_max"])) & (k > g.sma(k, int(p["sma_n"])))
               & (g.adx(h, d, k, int(p["adx_n"]))["adx"] > float(p["adx_min"])) & (natr >= float(p["natr_min"])))
        sy = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sy), k * (1 + sy))


# ================================================================ X005:822
@_kaydet
class S0822(_Taban):
    """HAM:X005:822 (1d, long): SMA(50) > SMA(200) iken önceki kapanış SMA50 altında VE bugünkü kapanış SMA50 üstünde -> long.
    Çıkış: art arda iki kapanış SMA50 altında, SMA(200) > SMA(50) olması ya da kapanış SMA200 altına inmesi. Stop yok ->
    ATR(14)x3 (uyarlama). SMA farkı sıralaması tahsis önceliği (atlandı)."""
    ad = "kapanis__sma50-geri-alim-s0822"
    varsayilan_parametreler = {"sma_hizli": 50, "sma_yavas": 200, "alt_kapanis_cikis": 2, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s50, s200 = g.sma(k, int(p["sma_hizli"])), g.sma(k, int(p["sma_yavas"]))
        gir = (s50 > s200) & (k.shift(1) < s50.shift(1)) & (k > s50)
        cik = _hepsi(k < s50, int(p["alt_kapanis_cikis"])) | (s200 > s50) | (k < s200)
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss), cikis_long=cik)


# ================================================================ X005:824
@_kaydet
class S0824(_Taban):
    """HAM:X005:824 (1d, long; Powertrend): son 10 günün hepsinde düşük > EMA(21) VE son 5 günün hepsinde EMA(21) > SMA(50) VE
    SMA(50) > önceki gün SMA(50) VE kapanış > açılış -> long. Çıkış: EMA(21) SMA(50)'nin altına inince. Stop yok -> ATR(14)x3."""
    ad = "kapanis__powertrend-s0824"
    varsayilan_parametreler = {"ema_n": 21, "sma_n": 50, "dusuk_gun": 10, "dizilim_gun": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        e, s = g.ema(k, int(p["ema_n"])), g.sma(k, int(p["sma_n"]))
        gir = (_hepsi(m["dusuk"] > e, int(p["dusuk_gun"])) & _hepsi(e > s, int(p["dizilim_gun"]))
               & (s > s.shift(1)) & (k > m["acilis"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss), cikis_long=e < s)


# ================================================================ X005:827
@_kaydet
class S0827(_Taban):
    """HAM:X005:827 (1d, long): alt bant = HH(yüksek,10) - 2,5 x SMA(yüksek-düşük, 25); kapanış < alt bant VE IBS=(C-L)/(H-L) < 0,3
    -> long. Çıkış: kapanış önceki günün yükseğinin üstüne çıkınca ya da kapanış SMA(200) altına inince (kaynak notunda 300
    yazıyor; metin değeri 200 alındı). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ibs-alt-bant-s0827"
    varsayilan_parametreler = {"tepe_gun": 10, "aralik_gun": 25, "carpan": 2.5, "ibs_max": 0.3, "sma_cikis": 200, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        nt, na = int(p["tepe_gun"]), int(p["aralik_gun"])
        alt = h.rolling(nt, min_periods=nt).max() - float(p["carpan"]) * g.sma(h - d, na)
        ibs = (k - d) / (h - d).where(lambda x: x > 0)
        gir = (k < alt) & (ibs < float(p["ibs_max"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss),
                     cikis_long=(k > h.shift(1)) | (k < g.sma(k, int(p["sma_cikis"]))))


# ================================================================ X005:830 / 828 / 829
@_kaydet
class S0830(_Taban):
    """HAM:X005:830 (1d, long): kapanış Bollinger(20, 2sd) alt bandının altındaysa (pozisyon yoksa) long; kapanış üst bandın üstüne
    çıkınca kapat. Stop yok -> ATR(14)x3 (uyarlama). `tutma_bar` verilirse (828) o kadar bar sonra zaman çıkışı."""
    ad = "kapanis__bb-alt-al-ust-sat-s0830"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "tutma_bar": None, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, k < bb["alt"], False, sl, ss), cikis_long=k > bb["ust"])


@_kaydet
class S0828(S0830):
    """HAM:X005:828 (1d, long, tek varlık): BB(20,2) günlük (popülasyon std). Pozisyon yokken kapanış < alt bant -> long; kapanış >
    üst bant -> çık; ayrıca 365 gün (Insight süresi) dolunca çık (zaman_cikisi_mum=365). Stop kaynakta yok -> ATR(14)x3 felaket
    stopu. 830 ile fark yalnız 365 günlük zaman çıkışıdır (sinyal mantığı aynı sınıftan türer)."""
    ad = "kapanis__bb-alt-al-365g-s0828"
    varsayilan_parametreler = {**S0830.varsayilan_parametreler, "tutma_bar": 365}


@_kaydet
class S0829(_Taban):
    """HAM:X005:829 (1d, iki yön, dur-ve-çevir, her zaman pozisyonda): pozisyon <= 0 iken kapanış Bollinger(20, 2sd, SMA) alt bandının
    altındaysa long; pozisyon >= 0 iken kapanış üst bandın üstündeyse short. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__bb-cevir-s0829"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        al, sat = k < bb["alt"], k > bb["ust"]
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X005:831
@_kaydet
class S0831(_Taban):
    """HAM:X005:831 (1d, long): RSI(2, basit hareketli ortalama türü) < 15 -> long; pozisyondayken kapanış önceki günün yükseğinin
    üstüne çıkınca kapat. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__rsi2-basit-s0831"
    varsayilan_parametreler = {"rsi_n": 2, "esik": 15.0, "cikis_n": 1, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["cikis_n"])
        onc = m["yuksek"].shift(1).rolling(n, min_periods=n).max()
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, _rsi_basit(k, int(p["rsi_n"])) < float(p["esik"]), False, sl, ss), cikis_long=k > onc)


# ================================================================ X005:832
@_kaydet
class S0832(_Taban):
    """HAM:X005:832 (1d, iki yön, dur-ve-çevir): günlük RSI(14, Wilder): önceki <= 25 iken güncel > 25 -> varsa short kapat, long aç;
    önceki >= 80 iken güncel < 80 -> long kapat, short aç. Stop giriş fiyatının %2 altı (short için %2 üstü; sinyal kapanışından)."""
    ad = "kapanis__rsi-esik-cevir-s0832"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 25.0, "ust": 80.0, "stop_yuzde": 0.02}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        al = ((r.shift(1) <= float(p["alt"])) & (r > float(p["alt"]))).fillna(False)
        sat = ((r.shift(1) >= float(p["ust"])) & (r < float(p["ust"]))).fillna(False)
        sy = float(p["stop_yuzde"])
        return _ekle(cerceve(m, al, sat, k * (1 - sy), k * (1 + sy)), cikis_long=sat, cikis_short=al)


# ================================================================ X005:839
@_kaydet
class S0839(_Taban):
    """HAM:X005:839 (1d, long-only): EMA(15) > EMA(70) x 1,00015 ve long değilse long; EMA(15) < EMA(70) olunca kapat; açığa satış yok.
    Stop yok -> ATR(14)x3 (uyarlama). Kaynak veri saatlik, karar günlük EMA: TF 1d."""
    ad = "kapanis__ema15-70-tolerans-s0839"
    varsayilan_parametreler = {"ema_hizli": 15, "ema_yavas": 70, "tolerans": 0.00015, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        eh, ey = g.ema(k, int(p["ema_hizli"])), g.ema(k, int(p["ema_yavas"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, eh > ey * (1.0 + float(p["tolerans"])), False, sl, ss), cikis_long=eh < ey)


# ================================================================ X005:840
@_kaydet
class S0840(_Taban):
    """HAM:X005:840 (1h, iki yön; TTM squeeze çıkışı): Bollinger(20, 2sd) bantları Keltner(20, 1,5; SMA merkez, TR-SMA aralık: motorun
    sikisma_momentum göstergesi) içindeyken (sıkışma) bir sonraki barda sıkışma biterse: momentum = linreg(fiyat - ((HH20+LL20)/2 +
    SMA20)/2, 20). Long: momentum > 0 VE yükseliyor VE fiyat > SMA(200); short: momentum < 0 VE düşüyor VE fiyat < SMA(200).
    Hedef: giriş +/- 8 x ATR(14); çıkış: momentum işareti dönerse ya da önceki değerin %50'sinin altına düşerse. Stop: giriş
    -/+ 3,5 x ATR(14), lehte kaydırılır (motor atr_iz_suren_k=3,5; bar içi ekstrem tabanlı)."""
    ad = "kapanis__sikisma-cikisi-s0840"
    stil = "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "kc_n": 20, "kc_k": 1.5, "sma_n": 200, "atr_n": 14,
                               "hedef_atr": 8.0, "stop_atr": 3.5}

    @staticmethod
    def _cikis_kw(p):
        return {"atr_iz_suren_k": float(p["stop_atr"]), "atr_periyot": int(p["atr_n"])}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        sq = sikisma_momentum(h, d, k, int(p["bb_n"]), float(p["bb_k"]), int(p["kc_n"]), float(p["kc_k"]))
        val = sq["val"]
        biter = sq["sqz_on"].shift(1, fill_value=False) & ~sq["sqz_on"]
        s200 = g.sma(k, int(p["sma_n"]))
        al = biter & (val > 0) & (val > val.shift(1)) & (k > s200)
        sat = biter & (val < 0) & (val < val.shift(1)) & (k < s200)
        a = g.atr(h, d, k, int(p["atr_n"]))
        st, hd = float(p["stop_atr"]) * a, float(p["hedef_atr"]) * a
        yarim = 0.5 * val.shift(1)
        return _ekle(cerceve(m, al, sat, k - st, k + st, hedef_l=k + hd, hedef_s=k - hd),
                     cikis_long=(val <= 0) | (val < yarim), cikis_short=(val >= 0) | (val > yarim))


# ================================================================ X005:853
@_kaydet
class S0853(_Taban):
    """HAM:X005:853 (1d, iki yön): z = (kapanış - SMA20) / STD20 (std ddof=0); pozisyon = -işaret(z): kapanış SMA20 üstündeyse short,
    altındaysa long; fiyat MA20'yi kesince pozisyon ters döner (bir gün gecikme = motorun sonraki açılış dolumu). Stop yok ->
    ATR(14)x3 (uyarlama). Faiz rollover PnL kalemi atlandı (işlem kuralı değil)."""
    ad = "kapanis__z-ters-pozisyon-s0853"
    varsayilan_parametreler = {"ma_n": 20, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["ma_n"])
        z = (k - g.sma(k, n)) / k.rolling(n, min_periods=n).std(ddof=0).where(lambda x: x > 0)
        al, sat = z < 0, z > 0
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X005:876
@_kaydet
class S0876(_Taban):
    """HAM:X005:876 (1d, long; TrendPilot): kapanış 5 gün üst üste SMA(200) üstünde kapanınca long (sonraki açılış); 5 gün üst üste
    SMA(200) altında kapanınca sat. Stop yok -> ATR(14)x3 (uyarlama). Endeks filtreli sürüm uygulanmadı."""
    ad = "kapanis__sma200-teyit-s0876"
    varsayilan_parametreler = {"sma_n": 200, "teyit_gun": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s = g.sma(k, int(p["sma_n"]))
        n = int(p["teyit_gun"])
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, _hepsi(k > s, n), False, sl, ss), cikis_long=_hepsi(k < s, n))


# ================================================================ X005:877
@_kaydet
class S0877(_Taban):
    """HAM:X005:877 (1d, long; Moving Avg Channel): 5 ardışık barın tamamı (dip) SMA(High,10)'un üstündeyse long; 5 ardışık barın
    tamamı (tepe) SMA(Low,8)'in altındaysa sat (her bar kendi günündeki ortalamayla karşılaştırılır). Stop yok -> ATR(14)x3."""
    ad = "kapanis__ma-kanali-s0877"
    varsayilan_parametreler = {"ust_n": 10, "alt_n": 8, "teyit_bar": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        h, d = m["yuksek"], m["dusuk"]
        n = int(p["teyit_bar"])
        gir = _hepsi(d > g.sma(h, int(p["ust_n"])), n)
        cik = _hepsi(h < g.sma(d, int(p["alt_n"])), n)
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, gir, False, sl, ss), cikis_long=cik)


# ================================================================ X005:878
@_kaydet
class S0878(_Taban):
    """HAM:X005:878 (1d, long; TechTrader): kapanış > SMA(40) VE kapanış > açılış VE kapanış önceki 70 günün ve önceki 10 günün en
    yükseğinin (yüksek) üstünde -> long. Çıkış yalnız kapanış 180 günlük EMA(Low) altına inince; başlangıç stopu giriş fiyatının
    %10 altı (sinyal kapanışından). 21 günlük ciro tabanı ve endeks filtresi uygulanmadı."""
    ad = "kapanis__techtrader-s0878"
    varsayilan_parametreler = {"sma_n": 40, "zirve_uzun": 70, "zirve_kisa": 10, "ema_low_cikis": 180, "stop_yuzde": 0.10}

    def sinyaller(self, m):
        p = self.parametreler
        k, h = m["kapanis"], m["yuksek"]
        nu, nk = int(p["zirve_uzun"]), int(p["zirve_kisa"])
        gir = ((k > g.sma(k, int(p["sma_n"]))) & (k > m["acilis"])
               & (k > h.shift(1).rolling(nu, min_periods=nu).max()) & (k > h.shift(1).rolling(nk, min_periods=nk).max()))
        sy = float(p["stop_yuzde"])
        return _ekle(cerceve(m, gir, False, k * (1 - sy), k * (1 + sy)),
                     cikis_long=k < g.ema(m["dusuk"], int(p["ema_low_cikis"])))


# ================================================================ X005:880
@_kaydet
class S0880(_Taban):
    """HAM:X005:880 (1d, long; Bollinger Breakout): kapanış SMA(100) + 3 std (ddof 0) üst bandını aşınca (yukarı kesişim) long;
    kapanış SMA(100) - 1 std alt bandının altına inince sat. Stop yok -> ATR(14)x3 (uyarlama). Endeks filtresi uygulanmadı."""
    ad = "kapanis__bb-kirilim-3sd-s0880"
    varsayilan_parametreler = {"sma_n": 100, "ust_k": 3.0, "alt_k": 1.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["sma_n"])
        orta = g.sma(k, n)
        std = k.rolling(n, min_periods=n).std(ddof=0)
        ust, alt = orta + float(p["ust_k"]) * std, orta - float(p["alt_k"]) * std
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, _yukari(k, ust), False, sl, ss), cikis_long=k < alt)


# ================================================================ X005:896
@_kaydet
class S0896(_Taban):
    """HAM:X005:896 (1d, long): sinyal = kapanış/kapanış[20] - 1; pozisyon yokken sinyal > %2 ise long; pozisyondayken sinyal < -%1
    olunca kapat. Stop yok -> ATR(14)x3 (uyarlama). Kelly büyüklüğü uygulanmaz (risk motoru)."""
    ad = "kapanis__momentum20-esik-s0896"
    varsayilan_parametreler = {"lookback": 20, "giris": 0.02, "cikis": -0.01, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sinyal = k / k.shift(int(p["lookback"])) - 1.0
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, sinyal > float(p["giris"]), False, sl, ss), cikis_long=sinyal < float(p["cikis"]))


# ================================================================ X008:EK#5
@_kaydet
class X8Ek5(_Taban):
    """HAM:X008:EK#5 (5m, iki yön; VWAP sapma + RSI ortalamaya dönüş): günlük UTC'de sıfırlanan VWAP (motorun vwap_seans göstergesi,
    tipik fiyat); sapma% = 100 x (kapanış - VWAP) / VWAP. Pozisyon yokken sapma < -2 VE RSI(14) < 30 -> long; sapma > +2 VE
    RSI(14) > 70 -> short. Long iken kapanış >= VWAP, short iken kapanış <= VWAP kapat. Stop: girişten %2 sabit yüzde (sinyal
    kapanışından)."""
    ad = "kapanis__vwap-sapma-rsi-x8ek-5"
    stil = "scalp"
    varsayilan_parametreler = {"sapma_pct": 2.0, "rsi_n": 14, "rsi_alt": 30.0, "rsi_ust": 70.0, "stop_pct": 2.0}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        v = g.vwap_seans(m["yuksek"], m["dusuk"], k, m["hacim"], seans_kimligi(m.index))["vwap"]
        sapma = 100.0 * (k - v) / v
        r = g.rsi(k, int(p["rsi_n"]))
        e = float(p["sapma_pct"])
        al = (sapma < -e) & (r < float(p["rsi_alt"]))
        sat = (sapma > e) & (r > float(p["rsi_ust"]))
        sy = float(p["stop_pct"]) / 100.0
        return _ekle(cerceve(m, al, sat, k * (1 - sy), k * (1 + sy)), cikis_long=k >= v, cikis_short=k <= v)


# ================================================================ X008:L15#2
@_kaydet
class X8L152(_Taban):
    """HAM:X008:L15#2 (1d|4h|1h, iki yön, SAR: daima piyasada, ters sinyal çıkış+giriş): `gosterge`="ema": kapanış EMA üstündeyse long,
    altındaysa short (EMA periyodu 1d=8, 4h=21, 1h=50). `gosterge`="supertrend": ATR(10) x 3 Supertrend, kapanış üst bandın
    üstüne çıkınca long, alt bandın altına inince short (motor supertrend yönü). 6 raporlu varyant (3 TF x EMA/Supertrend),
    hepsi VARYANTLAR'da. Stop kaynakta yok -> ATR(14)x3 felaket stopu (uyarlama)."""
    ad = "kapanis__sar-ema-supertrend-x8l15-2"
    varsayilan_parametreler = {"gosterge": "ema", "n": 8, "st_atr": 10, "st_carpan": 3.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        if p["gosterge"] == "ema":
            e = g.ema(k, int(p["n"]))
            al, sat = k > e, k < e
        elif p["gosterge"] == "supertrend":
            yon = g.supertrend(m["yuksek"], m["dusuk"], k, int(p["st_atr"]), float(p["st_carpan"]))["yon"]
            al, sat = yon == 1, yon == -1
        else:
            raise ValueError(f"Bilinmeyen gosterge: {p['gosterge']!r}")
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, al, sat, sl, ss), cikis_long=sat, cikis_short=al)


# ================================================================ X008:L17#3
@_kaydet
class X8L173(_Taban):
    """HAM:X008:L17#3 (5m, iki yön; Bollinger dönüşü): pozisyon yokken kapanış < BB(20, 2sd) alt bandı -> long, kapanış > üst bant ->
    short; long iken kapanış >= alt bant olunca (banda geri dönüş), short iken kapanış <= üst bant olunca kapat; ters çevirme
    yok. Stop: sinyal mumunun ATR(14) x 2 sabit mesafesi. Std ddof=0 (kaynakta belirsiz; lider onayı bekliyor)."""
    ad = "kapanis__bb-donus-x8l17-3"
    stil = "scalp"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "atr_n": 14, "atr_k": 2.0}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        sl, ss = _atr_stop(m, p)
        return _ekle(cerceve(m, k < bb["alt"], k > bb["ust"], sl, ss),
                     cikis_long=k >= bb["alt"], cikis_short=k <= bb["ust"])


# ================================================================ X008:L17#4
@_kaydet
class X8L174(_Taban):
    """HAM:X008:L17#4 (5m, iki yön; z-skoru): z = (kapanış - SMA(20)) / StdDev(20, kapanış) (ddof=0); pozisyon yokken z < -2 -> long,
    z > +2 -> short; long iken z >= 0, short iken z <= 0 kapat. Stop: giriş fiyatından %2 sabit yüzde (sinyal kapanışından)."""
    ad = "kapanis__z-skor-donus-x8l17-4"
    stil = "scalp"
    varsayilan_parametreler = {"ma_n": 20, "std_n": 20, "giris_z": 2.0, "cikis_z": 0.0, "stop_pct": 2.0}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sn = int(p["std_n"])
        z = (k - g.sma(k, int(p["ma_n"]))) / k.rolling(sn, min_periods=sn).std(ddof=0).where(lambda x: x > 0)
        e, c = float(p["giris_z"]), float(p["cikis_z"])
        sy = float(p["stop_pct"]) / 100.0
        return _ekle(cerceve(m, z < -e, z > e, k * (1 - sy), k * (1 + sy)), cikis_long=z >= c, cikis_short=z <= -c)


# ---------------------------------------------------------------- koşu listesi
VARYANTLAR: list = []


def _kayit(kaynak_id: str, sinif, tflar, varyantlar=None):
    """Her varyant x TF için bir kayıt (#v1.. varyant-ana, TF-ikincil sırayla)."""
    varyantlar = varyantlar or [{}]
    no = 0
    for v in varyantlar:
        for tf in tflar:
            no += 1
            VARYANTLAR.append({"kimlik": f"{kaynak_id}#v{no}", "sinif": sinif.ad,
                               "parametreler": {**sinif.varsayilan_parametreler, **v}, "tf": tf})


for _kid, _sinif, _tf in [
    ("763", S0763, "1d"), ("764", S0764, "1d"), ("768", S0768, "1d"), ("769", S0769, "1d"), ("771", S0771, "1d"),
    ("772", S0772, "1d"), ("779", S0779, "1d"), ("780", S0780, "1h"), ("790", S0790, "1d"), ("793", S0793, "1d"),
    ("809", S0809, "1d"), ("812", S0812, "30m"), ("816", S0816, "1d"), ("817", S0817, "1d"), ("818", S0818, "1d"),
    ("819", S0819, "1d"), ("820", S0820, "1d"), ("822", S0822, "1d"), ("824", S0824, "1d"), ("827", S0827, "1d"),
    ("828", S0828, "1d"), ("829", S0829, "1d"), ("830", S0830, "1d"), ("831", S0831, "1d"), ("832", S0832, "1d"),
    ("839", S0839, "1d"), ("840", S0840, "1h"), ("853", S0853, "1d"), ("876", S0876, "1d"), ("877", S0877, "1d"),
    ("878", S0878, "1d"), ("880", S0880, "1d"), ("896", S0896, "1d"),
]:
    _kayit(f"HAM:X005:{_kid}", _sinif, [_tf])

_kayit("HAM:X005:802", S0802, ["4h", "1d"])                       # K6: TF yazılı değil, iki hipotez
_kayit("HAM:X008:EK#5", X8Ek5, ["5m"])
_kayit("HAM:X008:L17#3", X8L173, ["5m"])
_kayit("HAM:X008:L17#4", X8L174, ["5m"])
# L15#2: 6 raporlu varyant (3 TF x EMA/Supertrend); EMA periyodu TF'ye bağlı
for _no, (_tf, _gos, _par) in enumerate(
        [("1d", "ema", {"n": 8}), ("4h", "ema", {"n": 21}), ("1h", "ema", {"n": 50}),
         ("1d", "supertrend", {"st_atr": 10, "st_carpan": 3.0}), ("4h", "supertrend", {"st_atr": 10, "st_carpan": 3.0}),
         ("1h", "supertrend", {"st_atr": 10, "st_carpan": 3.0})], start=1):
    VARYANTLAR.append({"kimlik": f"HAM:X008:L15#2#v{_no}", "sinif": X8L152.ad,
                       "parametreler": {**X8L152.varsayilan_parametreler, "gosterge": _gos, **_par}, "tf": _tf})

KODLANAMADI = [
    {"kimlik": "HAM:X005:863",
     "neden": "örtüşen dilimli net pozisyon: her gün bir birim long/short dilimi açılır, her dilim 25 gün tutulur, net pozisyon "
              "-25..+25 dilim toplamıdır; motorun tek giriş + tek stop modeline sığmaz (kaynak notu: lider uygulanabilirliği "
              "onaylamalı); tek pozisyonlu yaklaşım farklı bir strateji olurdu (uydurma çözüm yok)."},
    {"kimlik": "HAM:X005:879",
     "neden": "pozisyon bilinçli çıkış gerekli: giriş sonrası izlenen en yüksek tepeden kapanış %20 düşünce sat (kapanış bazlı, "
              "fiyat zirvesinin yüzdesi; motorun geri_cekilme modülü kâr-puanı cinsindendir, aynı değil). Giriş (son salınım "
              "dibinden %20 yükseliş) tek başına kodlanabilir ama çıkışı sanal pozisyonla kestirmek yasak."},
]
