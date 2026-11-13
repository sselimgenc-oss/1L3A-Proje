"""Kapanış turu, kodlama partisi g8_kod_3 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_3.csv, 39 kaynak satırı).

Her sınıf kendi cümlelerimizle yazılmış bir uyarlamadır; üçüncü taraf kodu kopyalanmadı. Mevcut dosyalara dokunulmaz.
Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Gelecek verisi yok; üst TF yalnız kapanmış mumdan (htf.ust_zaman).
Kaynak stopu yoksa ya da ≤ -%50 ise ATR(14)x3 felaket stopu = "uyarlama" (ön kayıt). Izgara yoktur (parametre_izgarasi = {}).

Ortak uyarlamalar:
- Giriş koşulları "pozisyon yokken" okunur; motor zaten açık pozisyonda yeni girişi işlemez.
- Durumsal çıkışlar her mumda yazılır (cikis_long / cikis_short), pozisyon durumu motora bırakılır.
- Yüzde/ATR iz süren stop içeren satırlar (294, 310, 325) strateji kancasıyla (`pozisyon_cikisi`, kod_g8_modul) GERÇEK pozisyondan
  çıkış verir (sanal pozisyon yok): iz kapanışta sınanır, çıkış sonraki açılışta.

Satırlar: X005:247 253 257 259 260 264 268 278 283 287 288 289 290 291 292 294 295 296 297 301 304 306 310 313 314 317
320 325 327 328 332 335 338 339 341 346 348 353 (356 kodlanamadı: KODLANAMADI).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import donchian_kanal
from motor.strateji.gostergeler_b2 import asagi_kesis, gecis, ichimoku, yukari_kesis
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, kapanis_iz_ihlali, tepe_geri_cekilme
from motor.strateji.temel import Strateji


# --------------------------------------------------------------------------------------------- yardımcılar

def _b(x, idx) -> pd.Series:
    if x is None:
        return pd.Series(False, index=idx)
    return pd.Series(x, index=idx).fillna(False).astype(bool)


def _atr_stop(m: pd.DataFrame, p: dict):
    """ATR(14)x3 felaket stopu (uyarlama): (long stop, short stop)."""
    atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
    k = float(p["atr_k"])
    return m["kapanis"] - k * atr, m["kapanis"] + k * atr


def _kaynak_stop(stop: pd.Series, kap: pd.Series, atr_stop: pd.Series, yon: int) -> pd.Series:
    """Kaynak stopu; kayıp <= %50 ise (fiilen stopsuz) ATR uyarlamasına düşer. NaN kalır NaN."""
    kotu = (stop <= kap * 0.5) if yon == 1 else (stop >= kap * 1.5)
    return stop.where(stop.isna() | ~kotu, atr_stop)


def _cikti(m, long_ok, short_ok, stop_l, stop_s, cikis_long=None, cikis_short=None,
           hedef_l=None, hedef_s=None) -> pd.DataFrame:
    s = cerceve(m, long_ok, short_ok, stop_l, stop_s, hedef_l=hedef_l, hedef_s=hedef_s)
    s["cikis_long"] = _b(cikis_long, m.index)
    s["cikis_short"] = _b(cikis_short, m.index)
    return s


def _uzun(m, p, al, sat, stop_l=None, hedef_l=None) -> pd.DataFrame:
    sl, ss = _atr_stop(m, p)
    return _cikti(m, al, False, sl if stop_l is None else stop_l, ss, cikis_long=sat, hedef_l=hedef_l)


def _iki(m, p, al, sat_l, short, sat_s) -> pd.DataFrame:
    sl, ss = _atr_stop(m, p)
    return _cikti(m, al, short, sl, ss, cikis_long=sat_l, cikis_short=sat_s)


def _rsi_sma(kap: pd.Series, n: int) -> pd.Series:
    """Basit ortalamalı RSI (Wilder yumuşatması yok)."""
    d = kap.diff()
    kazanc = d.clip(lower=0.0).rolling(n, min_periods=n).mean()
    kayip = (-d).clip(lower=0.0).rolling(n, min_periods=n).mean()
    return 100.0 - 100.0 / (1.0 + kazanc / kayip)


def _wpr(yuk, dus, kap, n: int) -> pd.Series:
    hh = yuk.rolling(n, min_periods=n).max()
    ll = dus.rolling(n, min_periods=n).min()
    return -100.0 * (hh - kap) / (hh - ll)


def _var(src: np.ndarray, uzunluk: int, cmo_n: int = 9) -> np.ndarray:
    """Değişken endeksli dinamik ortalama: alfa = 2/(uzunluk+1) x |CMO(cmo_n)|. İlk geçerli değerden başlar
    (kaynaktaki 0'dan başlangıç yerine; uyarlama)."""
    n = len(src)
    out = np.full(n, np.nan)
    d = np.diff(src, prepend=np.nan)
    yukari = pd.Series(np.where(d > 0, d, 0.0)).rolling(cmo_n, min_periods=cmo_n).sum().to_numpy()
    asagi = pd.Series(np.where(d < 0, -d, 0.0)).rolling(cmo_n, min_periods=cmo_n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        cmo = np.nan_to_num((yukari - asagi) / (yukari + asagi))
    alfa = 2.0 / (uzunluk + 1.0)
    onceki = np.nan
    for i in range(n):
        if np.isnan(src[i]):
            continue
        if np.isnan(onceki):
            out[i] = src[i]
        else:
            a = alfa * abs(cmo[i])
            out[i] = a * src[i] + (1.0 - a) * onceki
        onceki = out[i]
    return out


def _ott(src: np.ndarray, periyot: int, yuzde: float) -> np.ndarray:
    """Optimize edilmiş trend takipçisi: src'nin VAR(periyot) ortalaması etrafında yüzde bandıyla yürüyen stop."""
    mav = _var(src, periyot)
    n = len(src)
    ott = np.full(n, np.nan)
    uz_onc = ks_onc = np.nan
    yon = 1
    for i in range(n):
        if np.isnan(mav[i]):
            continue
        fark = mav[i] * yuzde * 0.01
        uz, ks = mav[i] - fark, mav[i] + fark
        if np.isnan(uz_onc):
            uz_onc, ks_onc = uz, ks
        if mav[i] > uz_onc:
            uz = max(uz, uz_onc)
        if mav[i] < ks_onc:
            ks = min(ks, ks_onc)
        if yon == -1 and mav[i] > ks_onc:
            yon = 1
        elif yon == 1 and mav[i] < uz_onc:
            yon = -1
        mt = uz if yon == 1 else ks
        ott[i] = mt * (200.0 + yuzde) / 200.0 if mav[i] > mt else mt * (200.0 - yuzde) / 200.0
        uz_onc, ks_onc = uz, ks
    return ott


def _egim(kap: pd.Series, n: int) -> pd.Series:
    """Son n kapanışın en küçük kareler eğimi (bar başına)."""
    y = kap.to_numpy(float)
    out = np.full(len(y), np.nan)
    if len(y) >= n:
        x = np.arange(n) - (n - 1) / 2.0
        out[n - 1:] = sliding_window_view(y, n) @ x / (x @ x)
    return pd.Series(out, index=kap.index)


def _pma(kap: pd.Series, n: int) -> pd.Series:
    return g.sma(kap, n) + _egim(kap, n) * n / 2.0


def _hilo(yuk: pd.Series, dus: pd.Series, kap: pd.Series, n: int):
    """Gann HiLo etkinleştirici: kapanış önceki n mumun yüksek ortalamasını aşarsa yukarı, düşük ortalamasının altına
    inerse aşağı; arada durum korunur. Döner: (yon, çizgi)."""
    ust = yuk.rolling(n, min_periods=n).mean().shift(1).to_numpy()
    alt = dus.rolling(n, min_periods=n).mean().shift(1).to_numpy()
    c = kap.to_numpy(float)
    yon = np.zeros(len(c), dtype="int64")
    cizgi = np.full(len(c), np.nan)
    d = 0
    for i in range(len(c)):
        if np.isnan(ust[i]) or np.isnan(alt[i]):
            continue
        if c[i] > ust[i]:
            d = 1
        elif c[i] < alt[i]:
            d = -1
        yon[i] = d
        cizgi[i] = alt[i] if d == 1 else (ust[i] if d == -1 else np.nan)
    return pd.Series(yon, index=kap.index), pd.Series(cizgi, index=kap.index)


def _gelisen_gunluk(m: pd.DataFrame, n: int = 20) -> dict:
    """Gün içi mumlarda, o ana kadar GERÇEKLEŞEN (gelişen) UTC günlük mumuyla günlük CCI(n) ve günlük bağlam.
    Önceki n-1 günün tipik fiyatı tamamlanmış günlerden, cari gün yalnız bu mumun kapanışına kadarki veriden gelir."""
    idx = m.index
    kod, _ = pd.factorize(idx.floor("D"))
    o = m["acilis"].to_numpy(float)
    h = m["yuksek"].to_numpy(float)
    l = m["dusuk"].to_numpy(float)
    c = m["kapanis"].to_numpy(float)
    df = pd.DataFrame({"k": kod, "o": o, "h": h, "l": l, "c": c})
    grp = df.groupby("k")
    gh, gl, gc = grp["h"].max().to_numpy(), grp["l"].min().to_numpy(), grp["c"].last().to_numpy()
    gtp = (gh + gl + gc) / 3.0
    gun_sayisi, w = len(gtp), n - 1
    onceki = np.full((gun_sayisi, w), np.nan)
    if gun_sayisi > w:
        onceki[w:] = sliding_window_view(gtp, w)[: gun_sayisi - w]
    tp = (grp["h"].cummax().to_numpy() + grp["l"].cummin().to_numpy() + c) / 3.0
    mat = np.column_stack([onceki[kod], tp])
    ort = mat.mean(axis=1)
    md = np.abs(mat - ort[:, None]).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        cci = (tp - ort) / (0.015 * md)
    cci[~np.isfinite(cci)] = np.nan
    dun_yuksek = np.r_[np.nan, gh[:-1]][kod]
    gun = idx.floor("D")
    hafta = gun - pd.to_timedelta(gun.dayofweek, unit="D")
    hkod, _ = pd.factorize(hafta)
    hafta_acilis = pd.Series(o).groupby(hkod).transform("first").to_numpy()
    return {"cci": pd.Series(cci, index=idx),
            "gun_acilis": pd.Series(grp["o"].transform("first").to_numpy(), index=idx),
            "dun_yuksek": pd.Series(dun_yuksek, index=idx),
            "hafta_acilis": pd.Series(hafta_acilis, index=idx)}


_ATR = {"atr_n": 14, "atr_k": 3.0}


# --------------------------------------------------------------------------------------------- X005 satırları

class BbRsiAltS0247(Strateji):
    """X005:247 (5m, long): kapanış < BB(20, 2σ) alt bant VE RSI(14) < 30 -> long; kapanış > SMA20 -> kapat.
    Kaynakta stop yok: ATR(14)x3 (uyarlama). Kaynak BTC/USDT, kripto13'e genelleştirildi."""

    ad, stil = "kapanis__bb-rsi-alt-s0247", "scalp"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_alt": 30.0, "cikis_n": 20, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        al = (kap < b["alt"]) & (g.rsi(kap, int(p["rsi_n"])) < float(p["rsi_alt"]))
        return _uzun(mumlar, p, al, kap > g.sma(kap, int(p["cikis_n"])))


class Rsi2Sma5S0253(Strateji):
    """X005:253 (1d, long): kapanış > SMA200 VE kapanış < SMA5 VE RSI(2) <= 5 -> long; kapanış > SMA5 olunca çık.
    RSI Wilder (standart tablo). Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi2-sma5-s0253", "swing"
    varsayilan_parametreler = {"rsi_n": 2, "rsi_ust": 5.0, "trend_n": 200, "kisa_n": 5, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        sma5 = g.sma(kap, int(p["kisa_n"]))
        al = ((kap > g.sma(kap, int(p["trend_n"]))) & (kap < sma5)
              & (g.rsi(kap, int(p["rsi_n"])) <= float(p["rsi_ust"])))
        return _uzun(mumlar, p, al, kap > sma5)


class IkeyorisiS0257(Strateji):
    """X005:257 (1d, long): Fiyat/SMA60 x 100 (이격도). Alt çizgi 95'i yukarı keserse long; üst çizgi 105'i aşağı
    keserse long'u kapat. MA tipi yazılmamış: SMA (standart). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__ikyori-sma60-s0257", "swing"
    varsayilan_parametreler = {"ma_n": 60, "alt": 95.0, "ust": 105.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        oran = kap / g.sma(kap, int(p["ma_n"])) * 100.0
        return _uzun(mumlar, p, yukari_kesis(oran, float(p["alt"])), asagi_kesis(oran, float(p["ust"])))


class Bb1SigmaS0259(Strateji):
    """X005:259 (1d, long): kapanış BB(20, 1σ) üst bandını yukarı keserse VE RSI(14) <= 70 -> long. Çıkış (herhangi
    biri): kapanış >= BB(20, 3,4σ) üst bant; RSI(14) >= 71; kapanış BB(20, 1σ) alt bandın altında.
    Stop yok: ATR(14)x3 (uyarlama). Kaynak ETHBTC, kripto13 USDT perp'lerine genellendi."""

    ad, stil = "kapanis__bb1sigma-rsi-s0259", "swing"
    varsayilan_parametreler = {"bb_n": 20, "giris_k": 1.0, "hedef_k": 3.4, "rsi_n": 14, "rsi_giris_ust": 70.0,
                               "rsi_cikis": 71.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        n = int(p["bb_n"])
        b1 = g.bollinger(kap, n, float(p["giris_k"]))
        b34 = g.bollinger(kap, n, float(p["hedef_k"]))
        rsi = g.rsi(kap, int(p["rsi_n"]))
        al = yukari_kesis(kap, b1["ust"]) & (rsi <= float(p["rsi_giris_ust"]))
        sat = (kap >= b34["ust"]) | (rsi >= float(p["rsi_cikis"])) | (kap < b1["alt"])
        return _uzun(mumlar, p, al, sat)


class RsiEsikS0260(Strateji):
    """X005:260 (1h, long): RSI(14) <= 30 iken (pozisyonsuzsa) kapanışta sinyal, sonraki açılışta long; RSI >= 70 -> çık.
    Stop kaynakta yok: ATR(14)x3 (uyarlama). %100 kazanma iddiası kural değil."""

    ad, stil = "kapanis__rsi-30-70-s0260", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30.0, "rsi_cik": 70.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        rsi = g.rsi(mumlar["kapanis"], int(p["rsi_n"]))
        return _uzun(mumlar, p, rsi <= float(p["rsi_al"]), rsi >= float(p["rsi_cik"]))


class BbSarkmaS0264(Strateji):
    """X005:264 (4h|1d, long): BB(20, 2σ, kapanış). Önceki mum kapanışı alt bandın altındaydı ve bu mum yükseliş mumu
    (kapanış > açılış) olup kapanışı bant İÇİNDE ise long (üst bant kırılımında alma yok). Çıkış: önceki kapanış üst
    bandın üstündeydi ve bu mum düşüş mumuyla bant içine döndüyse. `cikis_modu="orta_hat"`: ek olarak kapanış SMA20'yi
    yukarı keserse kâr al (kaynaktaki trend varyantı; VARYANTLAR'a girmez). "Sarkma" = bant dışı KAPANIŞ okundu
    (Bollinger tablosu kapanış tabanlı). Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__bb-sarkma-donus-s0264", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "cikis_modu": "ust_bant", **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap, ac = self.parametreler, mumlar["kapanis"], mumlar["acilis"]
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        al = ((kap.shift(1) < b["alt"].shift(1)) & (kap > ac) & (kap >= b["alt"]) & (kap <= b["ust"]))
        sat = (kap.shift(1) > b["ust"].shift(1)) & (kap < ac) & (kap <= b["ust"])
        if p["cikis_modu"] == "orta_hat":
            sat = sat | yukari_kesis(kap, b["orta"])
        return _uzun(mumlar, p, al, sat)


class BbCiftYonS0268(Strateji):
    """X005:268 (1d, iki yön): BB(20 SMA, 2σ). Kapanış <= alt bant -> long, kapanış >= üst bant -> short; çıkış orta
    bant (kapanış SMA20'ye ulaşınca; kapanmış mum kuralı). Stop kaynakta yok: ATR(14)x3 (uyarlama; yorum stopları
    kaynak ana metninde yok)."""

    ad, stil = "kapanis__bb-cift-yon-s0268", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        return _iki(mumlar, p, kap <= b["alt"], kap >= b["orta"], kap >= b["ust"], kap <= b["orta"])


class UcSupertrendS0278(Strateji):
    """X005:278 (1d, long): Supertrend(12,3), (10,1), (11,2) (periyot, çarpan) üçü de yukarı (yeşil) -> long;
    Supertrend(11,2) aşağıya dönünce çık. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__uc-supertrend-s0278", "swing"
    varsayilan_parametreler = {"st_al": ((12, 3.0), (10, 1.0), (11, 2.0)), "st_cikis": (11, 2.0), **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, l, c = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        al = pd.Series(True, index=mumlar.index)
        for per, carpan in p["st_al"]:
            al &= g.supertrend(h, l, c, int(per), float(carpan))["yon"] == 1
        per, carpan = p["st_cikis"]
        return _uzun(mumlar, p, al, g.supertrend(h, l, c, int(per), float(carpan))["yon"] == -1)


class BbAltGeriS0283(Strateji):
    """X005:283 (1d, long): SMA20 ve popülasyon sd20 (÷20). Önceki kapanış < önceki günün alt 2σ ve bugünkü kapanış >=
    bugünkü alt 2σ -> long. Hedef = sinyal günü SMA20 (hedef giriş fiyatının üstünde değilse sinyal düşer);
    stop = sinyal günü SMA20 - 3·sd20 (sabit; kayıp > %50 ise ATR(14)x3 uyarlaması). Zaman çıkışı yok.
    Kaynak anlık kotasyon kullanan tarama aracı: kapanmış mum + sonraki açılış dolumu (uyarlama)."""

    ad, stil = "kapanis__bb-alt-geri-hedef-s0283", "swing"
    varsayilan_parametreler = {"pencere": 20, "giris_k": 2.0, "stop_k": 3.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        n = int(p["pencere"])
        b2 = g.bollinger(kap, n, float(p["giris_k"]))
        b3 = g.bollinger(kap, n, float(p["stop_k"]))
        hedef = b2["orta"]
        al = (kap.shift(1) < b2["alt"].shift(1)) & (kap >= b2["alt"]) & (hedef > kap)
        sl, ss = _atr_stop(mumlar, p)
        stop = _kaynak_stop(b3["alt"], kap, sl, 1)
        return _cikti(mumlar, al, False, stop, ss, hedef_l=hedef)


class CciGunlukS0287(Strateji):
    """X005:287 (1h|2h|4h, long): GÜNLÜK CCI(20) (cari, gelişen gün mumuyla), günün açılışı, dünün yükseği, haftalık
    açılış. AL: kapanış > dünün yükseği VE > günlük açılış VE CCI_D > 0 VE > haftalık açılış VE CCI_D > 95 (yükselen
    kenar = koşul bir önceki mumda sağlanmıyordu). SAT: CCI_D 85'i VEYA 0'ı aşağı keser. Kaynak Pine'daki
    request.security(lookahead_on) sızıntısı uygulanmadı: yalnız o ana kadar gerçekleşen veri (uyarlama: geleceksiz
    biçim). Stop kaynakta yok: ATR(14)x3 (uyarlama). Gün = UTC günü, hafta Pazartesi 00:00 UTC."""

    ad, stil = "kapanis__cci-gunluk-s0287", "daytrade"
    varsayilan_parametreler = {"cci_n": 20, "al_esik": 95.0, "sat_esik": 85.0, "sat_esik2": 0.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        d = _gelisen_gunluk(mumlar, int(p["cci_n"]))
        cci = d["cci"]
        kos = ((kap > d["dun_yuksek"]) & (kap > d["gun_acilis"]) & (cci > 0) & (kap > d["hafta_acilis"])
               & (cci > float(p["al_esik"])))
        sat = asagi_kesis(cci, float(p["sat_esik"])) | asagi_kesis(cci, float(p["sat_esik2"]))
        return _uzun(mumlar, p, gecis(kos), sat)


class BbGeriDonusS0288(Strateji):
    """X005:288 (1d, long): önceki kapanış < BB(20, 2σ) alt ve şimdi kapanış >= alt -> long; önceki kapanış > üst ve
    şimdi kapanış <= üst -> çık (sinyal çıkışı). ADX filtresi yok. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__bb-geri-donus-s0288", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        al = (kap.shift(1) < b["alt"].shift(1)) & (kap >= b["alt"])
        sat = (kap.shift(1) > b["ust"].shift(1)) & (kap <= b["ust"])
        return _uzun(mumlar, p, al, sat)


class StokKesisimS0289(Strateji):
    """X005:289 (1d, long): hızlı stokastik %K(14), %D(3, SMA). %K %D'yi yukarı keserken %K < 20 -> long; %K %D'yi
    aşağı keserken %K > 80 -> çık. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__stokastik-kesisim-s0289", "swing"
    varsayilan_parametreler = {"k_n": 14, "d_n": 3, "alt": 20.0, "ust": 80.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        s = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], int(p["k_n"]), int(p["d_n"]))
        al = yukari_kesis(s["k"], s["d"]) & (s["k"] < float(p["alt"]))
        sat = asagi_kesis(s["k"], s["d"]) & (s["k"] > float(p["ust"]))
        return _uzun(mumlar, p, al, sat)


class WprKesisimS0290(Strateji):
    """X005:290 (1d, long): Williams %R(14) -80'in altından yukarı keserse long; -20'nin üstünden aşağı keserse çık.
    Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__williams-r-kesisim-s0290", "swing"
    varsayilan_parametreler = {"wpr_n": 14, "al": -80.0, "cik": -20.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        w = _wpr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], int(p["wpr_n"]))
        return _uzun(mumlar, p, yukari_kesis(w, float(p["al"])), asagi_kesis(w, float(p["cik"])))


class RsiSmaKesisimS0291(Strateji):
    """X005:291 (1d, long): basit ortalamalı RSI(14) (kaynak kodu Wilder değil, ortalama kazanç/kayıp SMA) 30'un altından
    yukarı keserse al; 70'in üstünden aşağı keserse sat. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi-sma-kesisim-s0291", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30.0, "ust": 70.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        r = _rsi_sma(mumlar["kapanis"], int(p["rsi_n"]))
        return _uzun(mumlar, p, yukari_kesis(r, float(p["alt"])), asagi_kesis(r, float(p["ust"])))


class IchimokuAyniBarS0292(Strateji):
    """X005:292 (1d, long): Tenkan(9) Kijun(26)'yı yukarı keser VE kapanış max(SenkouA, SenkouB(52)) üstünde (bulut
    ileri kaydırılmadan, aynı bar) -> al; Tenkan Kijun'u aşağı keser VE kapanış min(SenkouA, SenkouB) altında -> sat.
    Stop: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__ichimoku-ayni-bar-s0292", "swing"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        ic = ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), 0)
        al = yukari_kesis(ic["tenkan"], ic["kijun"]) & (kap > ic["bulut_ust"])
        sat = asagi_kesis(ic["tenkan"], ic["kijun"]) & (kap < ic["bulut_alt"])
        return _uzun(mumlar, p, al, sat)


class BbIzStopS0294(KancaDestek, Strateji):
    """X005:294 (15m, long): BB(20,2), Stokastik(14,1,3). AL: kapanış <= alt bant (stokastik kolu bunun alt kümesi:
    %K/%D <= 20 kesişimi de kapanış <= alt bant gerektirir, ayrıca yazılmadı). SAT: kapanış >= üst bant. İz süren stop:
    giriş sonrası en yüksekten %pct (kaynak iki değer verir: 7 ve 3, ikisi de varyant). Uyarlama: iz süren stop kancadadır
    (gerçek pozisyonun giriş sonrası en yüksek HIGH'ı; kapanış <= zirve x (1-pct) ise sonraki açılışta çık); giriş stopu
    kapanış x (1-pct) sabit sert stoptur."""

    ad, stil = "kapanis__bb-iz-stop-s0294", "scalp"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "iz_yuzde": 7.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        yz = float(p["iz_yuzde"]) / 100.0
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        stop_l = kap * (1.0 - yz)
        stop_s = kap * (1.0 + yz)
        al = (kap <= b["alt"]) & b["alt"].notna()
        sat = (kap >= b["ust"]) & b["ust"].notna()
        return _cikti(mumlar, al, False, stop_l, stop_s, cikis_long=sat)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, float(self.parametreler["iz_yuzde"]))


class RsiMacdS0295(Strateji):
    """X005:295 (1h, long): RSI(14, Wilder) < 30 VE MACD(12,26,9) çizgisi > sinyal -> AL; RSI > 70 VE MACD < sinyal ->
    SAT (çıkış). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi-macd-s0295", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30.0, "ust": 70.0, "macd": (12, 26, 9), **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        mc = g.macd(kap, *[int(x) for x in p["macd"]])
        return _uzun(mumlar, p, (r < float(p["alt"])) & (mc["macd"] > mc["sinyal"]),
                     (r > float(p["ust"])) & (mc["macd"] < mc["sinyal"]))


class RottVarS0296(Strateji):
    """X005:296 (4h|1d, long): destek = 2 x VAR(kapanış, 1000) (VAR: CMO(9) ağırlıklı değişken ortalama); ROTT = destek
    serisi üzerinde OTT(periyot 30, yüzde 7); destek > ROTT'u yukarı keserse AL, destek < ROTT SAT (long kapat).
    Uyarlamalar: VAR ilk geçerli değerden başlar (kaynakta 0'dan) ve ilk (VAR uzunluğu + OTT periyodu) mumda sinyal
    verilmez (ısınma). Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__rott-var-s0296", "swing"
    varsayilan_parametreler = {"var_n": 1000, "var_cmo_n": 9, "carpan": 2.0, "ott_periyot": 30, "ott_yuzde": 7.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        destek = float(p["carpan"]) * _var(kap.to_numpy(float), int(p["var_n"]), int(p["var_cmo_n"]))
        rott = _ott(destek, int(p["ott_periyot"]), float(p["ott_yuzde"]))
        d, r = pd.Series(destek, index=kap.index), pd.Series(rott, index=kap.index)
        isinma = np.arange(len(kap)) >= int(p["var_n"]) + int(p["ott_periyot"])
        al = yukari_kesis(d, r) & isinma
        return _uzun(mumlar, p, al, (d < r) & isinma)


class RisottoS0297(Strateji):
    """X005:297 (4h|1d, long): plot1 = VAR(RSI(kapanış,100), VAR uzunluğu 50) + 1000; plot2 = OTT(plot1, 30, %0,2);
    plot1 > plot2'yi yukarı keserse AL, plot1 < plot2 SAT (long kapat). Uyarlamalar: VAR ilk geçerli değerden
    başlar; ilk (RSI + VAR + OTT periyodu) mumda sinyal yok (ısınma). Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__risotto-s0297", "swing"
    varsayilan_parametreler = {"rsi_n": 100, "var_n": 50, "var_cmo_n": 9, "ofset": 1000.0, "ott_periyot": 30,
                               "ott_yuzde": 0.2, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        rsi = g.rsi(kap, int(p["rsi_n"])).to_numpy(float)
        plot1 = _var(rsi, int(p["var_n"]), int(p["var_cmo_n"])) + float(p["ofset"])
        plot2 = _ott(plot1, int(p["ott_periyot"]), float(p["ott_yuzde"]))
        a, b = pd.Series(plot1, index=kap.index), pd.Series(plot2, index=kap.index)
        isinma = np.arange(len(kap)) >= int(p["rsi_n"]) + int(p["var_n"]) + int(p["ott_periyot"])
        return _uzun(mumlar, p, yukari_kesis(a, b) & isinma, (a < b) & isinma)


class RsiEma5020S0301(Strateji):
    """X005:301 (4h|1d, iki yön): long: RSI(14) > 50 VE kapanış > EMA50 VE kapanış > EMA200; short: RSI < 50 VE kapanış <
    EMA50 VE < EMA200. Çıkış yalnız ters sinyal (long için short koşulu, short için long koşulu). Stop yok: ATR(14)x3."""

    ad, stil = "kapanis__rsi-ema-50-200-s0301", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_esik": 50.0, "ema_hizli": 50, "ema_yavas": 200, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        e1, e2 = g.ema(kap, int(p["ema_hizli"])), g.ema(kap, int(p["ema_yavas"]))
        esik = float(p["rsi_esik"])
        uzun = (r > esik) & (kap > e1) & (kap > e2)
        kisa = (r < esik) & (kap < e1) & (kap < e2)
        return _iki(mumlar, p, uzun, kisa, kisa, uzun)


class CardwellRsiS0304(Strateji):
    """X005:304 (1d, long): Cardwell: RSI(14) 40'ı yukarı keserse long; RSI 60'ın altına inerse (aşağı kesiş) long'u
    kapat. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__cardwell-rsi-s0304", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "giris": 40.0, "cikis": 60.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        r = g.rsi(mumlar["kapanis"], int(p["rsi_n"]))
        return _uzun(mumlar, p, yukari_kesis(r, float(p["giris"])), asagi_kesis(r, float(p["cikis"])))


class SmaBantS0306(Strateji):
    """X005:306 (1d, long): kısa SMA (s; s=1 kapanış) uzun SMA'yı (l) b bandı kadar yukarı keserse (kısa > uzun x (1+b)
    koşulu yeni sağlanınca) long; kısa SMA uzun SMA'nın b bandı kadar altına inerse long'u kapat. 36 varyant:
    s in {1,2,5} x l in {10,20,30,40,50,60} x b in {0, 0,01}. Short yazılı değil. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__sma-bant-s0306", "swing"
    varsayilan_parametreler = {"s": 1, "l": 10, "b": 0.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        s, l, b = int(p["s"]), int(p["l"]), float(p["b"])
        kisa = kap if s == 1 else g.sma(kap, s)
        uzun = g.sma(kap, l)
        return _uzun(mumlar, p, gecis(kisa > uzun * (1 + b)), kisa < uzun * (1 - b))


class PmaHaftalikS0310(KancaDestek, Strateji):
    """X005:310 (1d + 1w filtre, long): PMA(n) = SMA(kapanış, n) + OLS eğimi(son n kapanış, bar başına) x n/2.
    Giriş (pozisyon yokken): son TAMAMLANMIŞ haftalık kapanış > haftalık PMA(50) VE günlük kapanış > PMA(50) VE
    PMA(10) > PMA(50). Başlangıç stop = giriş x 0,90. İz süren stop: tepe = giriş sonrası en yüksek kapanış; stop =
    max(önceki stop, tepe - 2xATR(14)); kapanış <= stop -> çıkış (kanca: gerçek pozisyon). Kaynak gelişen haftayı
    kullanıyordu; yalnız tamamlanmış haftalar (geleceksiz biçim, uyarlama)."""

    ad, stil = "kapanis__pma-haftalik-s0310", "swing"
    varsayilan_parametreler = {"pma_kisa": 10, "pma_uzun": 50, "pma_hafta": 50, "sl_yuzde": 10.0, "atr_n": 14, "atr_x": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        hn = int(p["pma_hafta"])
        hafta = ust_zaman(mumlar, "1w", lambda u: pd.DataFrame({"kap": u["kapanis"], "pma": _pma(u["kapanis"], hn)}))
        pk, pu = _pma(kap, int(p["pma_kisa"])), _pma(kap, int(p["pma_uzun"]))
        kos = ((hafta["kap"] > hafta["pma"]) & (kap > pu) & (pk > pu))
        stop_l = kap * (1.0 - float(p["sl_yuzde"]) / 100.0)
        stop_s = kap * (1.0 + float(p["sl_yuzde"]) / 100.0)
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        self._sakla(kap=kap, atr=atr)
        return _cikti(mumlar, kos.fillna(False), False, stop_l, stop_s)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, d.mum_indeksi,
                                 float(self.parametreler["atr_x"]), 1, True)


class RsiBantS0313(Strateji):
    """X005:313 (5m, iki yön): RSI(14); bant = SMA(RSI,20) ± 2 x std(RSI,20) (popülasyon std). RSI < alt bant -> long;
    RSI > üst bant -> short; long çıkış RSI > SMA(RSI,20), short çıkış RSI < SMA(RSI,20); ters sinyal pozisyonu
    çevirir; sabit stop -%2 (kaynakta var)."""

    ad, stil = "kapanis__rsi-bant-s0313", "scalp"
    varsayilan_parametreler = {"rsi_n": 14, "ort_n": 20, "carpan": 2.0, "sl": 0.02}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        n = int(p["ort_n"])
        ort = g.sma(r, n)
        sd = r.rolling(n, min_periods=n).std(ddof=0)
        k, sl = float(p["carpan"]), float(p["sl"])
        al, kisa = r < ort - k * sd, r > ort + k * sd
        return _cikti(mumlar, al, kisa, kap * (1 - sl), kap * (1 + sl), cikis_long=(r > ort) | kisa,
                      cikis_short=(r < ort) | al)


class DonchianOrtaS0314(Strateji):
    """X005:314 (15m, iki yön): Donchian(200) bandı önceki 200 bar (sinyal mumu hariç). Mumun dibi <= alt band -> long;
    tepesi >= üst band -> short (pozisyon yokken). Hedef kanal orta çizgisi; stop = 2 x giriş - orta çizgi (giriş =
    sinyal kapanışı; kayıp > %50 ise ATR(14)x3 uyarlaması). Hedef girişin doğru tarafında değilse sinyal düşer."""

    ad, stil = "kapanis__donchian200-orta-s0314", "scalp"
    varsayilan_parametreler = {"donchian_n": 200, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        d = donchian_kanal(mumlar["yuksek"], mumlar["dusuk"], int(p["donchian_n"]))
        orta = (d["ust"] + d["alt"]) / 2.0
        al = (mumlar["dusuk"] <= d["alt"]) & (orta > kap)
        kisa = (mumlar["yuksek"] >= d["ust"]) & (orta < kap)
        sl, ss = _atr_stop(mumlar, p)
        stop_l = _kaynak_stop(2 * kap - orta, kap, sl, 1)
        stop_s = _kaynak_stop(2 * kap - orta, kap, ss, -1)
        return _cikti(mumlar, al, kisa, stop_l, stop_s, hedef_l=orta, hedef_s=orta)


class AtrDaralmaS0317(Strateji):
    """X005:317 (5m, iki yön): pozisyon yokken ATR(14) < 0,75 x SMA(ATR(14), 20) ise: kapanış < SMA20 -> long; kapanış >
    SMA20 -> short; long kapanış >= SMA20, short kapanış <= SMA20 olunca çık. Stop girişte sabitlenen 2,0 x ATR(14)."""

    ad, stil = "kapanis__atr-daralma-sma20-s0317", "scalp"
    varsayilan_parametreler = {"ma_n": 20, "atr_n": 14, "atr_ort_n": 20, "atr_esik": 0.75, "stop_atr": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        sma = g.sma(kap, int(p["ma_n"]))
        dar = atr < float(p["atr_esik"]) * g.sma(atr, int(p["atr_ort_n"]))
        k = float(p["stop_atr"])
        return _cikti(mumlar, dar & (kap < sma), dar & (kap > sma), kap - k * atr, kap + k * atr,
                      cikis_long=kap >= sma, cikis_short=kap <= sma)


class ArdisikKapanisS0320(Strateji):
    """X005:320 (1d, iki yön): N ardışık düşüş kapanışından sonra ertesi açılışta long, aynı işlem gününün kapanışında
    çık (Williams); ayna: N ardışık yükseliş kapanışından sonra short. N in {1,2,3}. Stop yok: ATR(14)x3 (uyarlama).
    Çıkış: 7/24 kripto günlük mumunda gün kapanışı = sonraki açılış, bu yüzden zaman_cikisi_mum=1 (giriş mumu kapanınca
    sonraki açılışta çıkış)."""

    ad, stil = "kapanis__ardisik-kapanis-s0320", "swing"
    varsayilan_parametreler = {"n": 1, **_ATR}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        n = int(p["n"])
        dus = (kap < kap.shift(1)).astype(float).rolling(n, min_periods=n).sum() == n
        yuk = (kap > kap.shift(1)).astype(float).rolling(n, min_periods=n).sum() == n
        return _iki(mumlar, p, dus, None, yuk, None)


class CokluTfSmaS0325(KancaDestek, Strateji):
    """X005:325 (5m, long): pozisyon yokken 5m kapanış > 5m SMA(30) VE son KAPANMIŞ 1h mumun kapanışı > 1h SMA(45) ->
    long; çıkış: kapanış, girişten beri en yüksek kapanışın %3 altına inerse (iz süren stop, kanca: gerçek pozisyon).
    Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__coklu-tf-sma-iz-s0325", "scalp"
    varsayilan_parametreler = {"sma_alt": 30, "sma_ust": 45, "iz_yuzde": 0.03, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        sn = int(p["sma_ust"])
        saat = ust_zaman(mumlar, "1h", lambda u: pd.DataFrame({"kap": u["kapanis"], "sma": g.sma(u["kapanis"], sn)}))
        kos = (kap > g.sma(kap, int(p["sma_alt"]))) & (saat["kap"] > saat["sma"])
        sl, ss = _atr_stop(mumlar, p)
        self._sakla(kap=kap)
        return _cikti(mumlar, kos.fillna(False), False, sl, ss)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        tepe = float(np.nanmax(self._kd["kap"][max(d.giris_mum_indeksi - 1, 0):i + 1]))
        return tepe_geri_cekilme(d, float(self.parametreler["iz_yuzde"]) * 100.0, 0.0, tepe)


class TrendTakipS0327(Strateji):
    """X005:327 (4h|1d, iki yön): Long: EMA50 > EMA100 VE kapanış, önceki 50 mumun en yüksek KAPANIŞINI (Highest[50]
    (close[1])) yukarı keserse; kaynak 'BUY AT high STOP' -> uyarlama: bir sonraki mumun kapanışı sinyal mumunun
    high'ının üstündeyse ondan sonraki açılışta giriş (sinyal bu sonraki mumun kapanışında). Short: EMA50 < EMA100
    VE kapanış, önceki 50 mumun en düşük DİBİNİ (Lowest[50](low[1])) aşağı keserse piyasadan short (kaynak asimetrisi
    aynen). Çıkış: long kapanış < SuperTrend(ATR10, x3), short kapanış > SuperTrend. Stop = SuperTrend çizgisi (long
    için çizgi kapanışın altında değilse sinyal düşer; kayıp > %50 ise ATR(14)x3). Piramit ekleme uygulanmaz."""

    ad, stil = "kapanis__trend-takip-supertrend-s0327", "swing"
    varsayilan_parametreler = {"ema_hizli": 50, "ema_yavas": 100, "donchian_n": 50, "st_atr": 10, "st_carpan": 3.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        h, l = mumlar["yuksek"], mumlar["dusuk"]
        n = int(p["donchian_n"])
        e1, e2 = g.ema(kap, int(p["ema_hizli"])), g.ema(kap, int(p["ema_yavas"]))
        zirve = kap.shift(1).rolling(n, min_periods=n).max()
        dip = l.shift(1).rolling(n, min_periods=n).min()
        sinyal_l = ((e1 > e2) & yukari_kesis(kap, zirve)).fillna(False)
        al = sinyal_l.shift(1, fill_value=False) & (kap > h.shift(1))
        kisa = (e1 < e2) & asagi_kesis(kap, dip)
        st = g.supertrend(h, l, kap, int(p["st_atr"]), float(p["st_carpan"]))
        sl, ss = _atr_stop(mumlar, p)
        cizgi = st["cizgi"]
        stop_l = _kaynak_stop(cizgi, kap, sl, 1)
        stop_s = _kaynak_stop(cizgi, kap, ss, -1)
        return _cikti(mumlar, al, kisa, stop_l, stop_s, cikis_long=st["yon"] == -1, cikis_short=st["yon"] == 1)


class Rsi2Sma200IkiS0328(Strateji):
    """X005:328 (30m|1h, iki yön): Long: kapanış > SMA200 VE RSI(2) < 5 -> sonraki mum açılışında al; çıkış kapanış >
    SMA5. Short: kapanış < SMA200 VE RSI(2) > 95 -> sonraki açılışta sat; çıkış kapanış < SMA5. RSI Wilder. Connors stop
    kullanmaz: ATR(14)x3 felaket stopu (uyarlama)."""

    ad, stil = "kapanis__rsi2-sma200-iki-s0328", "daytrade"
    varsayilan_parametreler = {"sma_trend": 200, "rsi_n": 2, "rsi_long": 5.0, "rsi_short": 95.0, "cikis_sma": 5, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        tr, cs = g.sma(kap, int(p["sma_trend"])), g.sma(kap, int(p["cikis_sma"]))
        return _iki(mumlar, p, (kap > tr) & (r < float(p["rsi_long"])), kap > cs,
                    (kap < tr) & (r > float(p["rsi_short"])), kap < cs)


class BbFitilS0332(Strateji):
    """X005:332 (15m, iki yön): BB(10, 2σ); kapanış > alt bant VE dip < alt bant -> long; kapanış < üst bant VE tepe >
    üst bant -> short. Çıkış SMA14(kapanış) seviyesinde limit: hedef = sinyal mumunun SMA14 değeri (sabit; giriş
    fiyatının doğru tarafında değilse sinyal düşer). Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__bb-fitil-sma14-s0332", "scalp"
    varsayilan_parametreler = {"bb_n": 10, "bb_k": 2.0, "hedef_n": 14, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        hedef = g.sma(kap, int(p["hedef_n"]))
        al = (kap > b["alt"]) & (mumlar["dusuk"] < b["alt"]) & (hedef > kap)
        kisa = (kap < b["ust"]) & (mumlar["yuksek"] > b["ust"]) & (hedef < kap)
        sl, ss = _atr_stop(mumlar, p)
        return _cikti(mumlar, al, kisa, sl, ss, hedef_l=hedef, hedef_s=hedef)


class Rsi2Rsi22S0335(Strateji):
    """X005:335 (1d, long): RSI(2) < 15 VE RSI(22) > 50 VE SMA(22) eğimi > 0 (SMA[0] > SMA[1]) -> long (tek pozisyon);
    RSI(2) > 60 olunca çık. MA tipi yazılmamış: SMA. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi2-rsi22-s0335", "swing"
    varsayilan_parametreler = {"rsi_kisa": 2, "rsi_kisa_alt": 15.0, "rsi_uzun": 22, "rsi_uzun_ust": 50.0, "ma_n": 22,
                               "cikis": 60.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        rk = g.rsi(kap, int(p["rsi_kisa"]))
        ma = g.sma(kap, int(p["ma_n"]))
        al = ((rk < float(p["rsi_kisa_alt"])) & (g.rsi(kap, int(p["rsi_uzun"])) > float(p["rsi_uzun_ust"]))
              & (ma > ma.shift(1)))
        return _uzun(mumlar, p, al, rk > float(p["cikis"]))


class Rsi2IkiS0338(Strateji):
    """X005:338 (1d, iki yön): long: kapanış > SMA200 VE kapanış < SMA5 VE RSI(2) < 13; short: kapanış < SMA200 VE kapanış >
    SMA5 VE RSI(2) > 83. Long çıkış: kapanış SMA(9)'u yukarı keser; short çıkış: kapanış SMA(5)'i aşağı keser.
    Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi2-iki-yon-s0338", "swing"
    varsayilan_parametreler = {"rsi_n": 2, "rsi_long": 13.0, "rsi_short": 83.0, "sma_trend": 200, "sma_giris": 5,
                               "sma_cikis_long": 9, "sma_cikis_short": 5, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        tr, gs = g.sma(kap, int(p["sma_trend"])), g.sma(kap, int(p["sma_giris"]))
        al = (kap > tr) & (kap < gs) & (r < float(p["rsi_long"]))
        kisa = (kap < tr) & (kap > gs) & (r > float(p["rsi_short"]))
        return _iki(mumlar, p, al, yukari_kesis(kap, g.sma(kap, int(p["sma_cikis_long"]))),
                    kisa, asagi_kesis(kap, g.sma(kap, int(p["sma_cikis_short"]))))


class RsiBantiTrendS0339(Strateji):
    """X005:339 (4h|1d, long): RSI(14) kendi SMA(100)+ust_std x std(100) bandının üstüne çıkınca (yukarı kesiş) long;
    çıkış RSI < ort - alt_std x std (v1: 1σ, v2: 2σ). v3/v4: v2 + sabit kâr al (+%2 / +%3; hedef = kapanış x (1+pct)).
    v5: v2 + sabit stop %5 (ATR stopu yerine). Diğerlerinde stop yok: ATR(14)x3 (uyarlama). std pencere = ortalama
    penceresi (100), popülasyon std."""

    ad, stil = "kapanis__rsi-bant-trend-s0339", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "ort_n": 100, "std_n": 100, "ust_std": 1.0, "alt_std": 1.0,
                               "kar_al_pct": 0.0, "stop_pct": 0.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        ort = g.sma(r, int(p["ort_n"]))
        sd = r.rolling(int(p["std_n"]), min_periods=int(p["std_n"])).std(ddof=0)
        al = yukari_kesis(r, ort + float(p["ust_std"]) * sd)
        sat = r < ort - float(p["alt_std"]) * sd
        sl, ss = _atr_stop(mumlar, p)
        if float(p["stop_pct"]) > 0:
            y = float(p["stop_pct"]) / 100.0
            sl, ss = kap * (1 - y), kap * (1 + y)
        hedef = kap * (1 + float(p["kar_al_pct"]) / 100.0) if float(p["kar_al_pct"]) > 0 else None
        return _cikti(mumlar, al, False, sl, ss, cikis_long=sat, hedef_l=hedef)


class Rsi5Sma50S0341(Strateji):
    """X005:341 (1d, long): kapanış > SMA(50) VE RSI(5) < 30 -> long; kapanış SMA(50)'yi yukarıdan aşağı keserse çık.
    Stop kaynakta belirsiz: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi5-sma50-s0341", "swing"
    varsayilan_parametreler = {"rsi_n": 5, "alt": 30.0, "trend_n": 50, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        sma = g.sma(kap, int(p["trend_n"]))
        al = (kap > sma) & (g.rsi(kap, int(p["rsi_n"])) < float(p["alt"]))
        return _uzun(mumlar, p, al, asagi_kesis(kap, sma))


class BandKirilimS0346(Strateji):
    """X005:346 (4h|1d, iki yön): Bands Breakthrough, dur-ve-dön: kapanış önceki 13 barın en yüksek YÜKSEĞİNİ aşarsa
    long'a geç, önceki 13 barın en düşük DİBİNİN altına inerse short'a geç (kaynak 'yüksek/kapanış' demiş; en yüksek
    yüksek okundu). Ters kırılım karşı pozisyonu kapatır. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__band-kirilim-13-s0346", "swing"
    varsayilan_parametreler = {"donchian_n": 13, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        d = donchian_kanal(mumlar["yuksek"], mumlar["dusuk"], int(p["donchian_n"]))
        uzun, kisa = kap > d["ust"], kap < d["alt"]
        return _iki(mumlar, p, uzun, kisa, kisa, uzun)


class RsiBb1IkiS0348(Strateji):
    """X005:348 (4h|1d, iki yön): Long: RSI(14) < 30 VE kapanış <= alt Bollinger bandı (BB 20, 1σ); short: RSI(14) > 70
    VE kapanış >= üst bant. Çıkış ters sinyal. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi-bb1-iki-s0348", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 30.0, "rsi_ust": 70.0, "bb_n": 20, "bb_k": 1.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        b = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        uzun = (r < float(p["rsi_alt"])) & (kap <= b["alt"])
        kisa = (r > float(p["rsi_ust"])) & (kap >= b["ust"])
        return _iki(mumlar, p, uzun, kisa, kisa, uzun)


class EmaHiloS0353(Strateji):
    """X005:353 (1d, long): kapanış > EMA(26) VE kapanış > HiLo Activator(4) VE RSI(14) > 50 -> kapanışta long; HiLo
    Activator(4) aşağı (negatif) döndüğü mumun kapanışında çık. HiLo formülü kaynakta yok: Gann HiLo (önceki 4 mumun
    SMA(yüksek)/SMA(düşük) değeri; kapanış üstünü aşarsa yukarı, altına inerse aşağı, arada durum korunur) kabul
    edildi. Stop yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__ema-hilo-rsi-s0353", "swing"
    varsayilan_parametreler = {"ema_n": 26, "hilo_n": 4, "rsi_n": 14, "rsi_esik": 50.0, **_ATR}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p, kap = self.parametreler, mumlar["kapanis"]
        yon, cizgi = _hilo(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["hilo_n"]))
        al = ((kap > g.ema(kap, int(p["ema_n"]))) & (yon == 1) & (kap > cizgi)
              & (g.rsi(kap, int(p["rsi_n"])) > float(p["rsi_esik"])))
        return _uzun(mumlar, p, al, yon == -1)


# --------------------------------------------------------------------------------------------- koşu listesi

VARYANTLAR: list = []


def _ekle(kaynak: str, sinif, tfler, parametre_listesi=({},)) -> None:
    """Her (parametre seti, TF) bir kayıt; kimlik <kaynak_id>#v<sıra> (ayar-major, sonra TF)."""
    sira = 0
    for par in parametre_listesi:
        for tf in tfler:
            sira += 1
            kayit = {"kimlik": f"{kaynak}#v{sira}", "sinif": sinif.ad, "parametreler": dict(par), "tf": tf}
            VARYANTLAR.append(kayit)


_ekle("HAM:X005:247", BbRsiAltS0247, ["5m"])
_ekle("HAM:X005:253", Rsi2Sma5S0253, ["1d"])
_ekle("HAM:X005:257", IkeyorisiS0257, ["1d"])
_ekle("HAM:X005:259", Bb1SigmaS0259, ["1d"])
_ekle("HAM:X005:260", RsiEsikS0260, ["1h"])
_ekle("HAM:X005:264", BbSarkmaS0264, ["4h", "1d"])
_ekle("HAM:X005:268", BbCiftYonS0268, ["1d"])
_ekle("HAM:X005:278", UcSupertrendS0278, ["1d"])
_ekle("HAM:X005:283", BbAltGeriS0283, ["1d"])
_ekle("HAM:X005:287", CciGunlukS0287, ["1h", "2h", "4h"])
_ekle("HAM:X005:288", BbGeriDonusS0288, ["1d"])
_ekle("HAM:X005:289", StokKesisimS0289, ["1d"])
_ekle("HAM:X005:290", WprKesisimS0290, ["1d"])
_ekle("HAM:X005:291", RsiSmaKesisimS0291, ["1d"])
_ekle("HAM:X005:292", IchimokuAyniBarS0292, ["1d"])
_ekle("HAM:X005:294", BbIzStopS0294, ["15m"], [{"iz_yuzde": 7.0}, {"iz_yuzde": 3.0}])
_ekle("HAM:X005:295", RsiMacdS0295, ["1h"])
_ekle("HAM:X005:296", RottVarS0296, ["4h", "1d"])
_ekle("HAM:X005:297", RisottoS0297, ["4h", "1d"])
_ekle("HAM:X005:301", RsiEma5020S0301, ["4h", "1d"])
_ekle("HAM:X005:304", CardwellRsiS0304, ["1d"])
_ekle("HAM:X005:306", SmaBantS0306, ["1d"],
      [{"s": s, "l": l, "b": b} for s in (1, 2, 5) for l in (10, 20, 30, 40, 50, 60) for b in (0.0, 0.01)])
_ekle("HAM:X005:310", PmaHaftalikS0310, ["1d"])
_ekle("HAM:X005:313", RsiBantS0313, ["5m"])
_ekle("HAM:X005:314", DonchianOrtaS0314, ["15m"])
_ekle("HAM:X005:317", AtrDaralmaS0317, ["5m"])
_ekle("HAM:X005:320", ArdisikKapanisS0320, ["1d"], [{"n": 1}, {"n": 2}, {"n": 3}])
_ekle("HAM:X005:325", CokluTfSmaS0325, ["5m"])
_ekle("HAM:X005:327", TrendTakipS0327, ["4h", "1d"])
_ekle("HAM:X005:328", Rsi2Sma200IkiS0328, ["30m", "1h"])
_ekle("HAM:X005:332", BbFitilS0332, ["15m"])
_ekle("HAM:X005:335", Rsi2Rsi22S0335, ["1d"])
_ekle("HAM:X005:338", Rsi2IkiS0338, ["1d"])
_ekle("HAM:X005:339", RsiBantiTrendS0339, ["4h", "1d"],
      [{"alt_std": 1.0},
       {"alt_std": 2.0},
       {"alt_std": 2.0, "kar_al_pct": 2.0},
       {"alt_std": 2.0, "kar_al_pct": 3.0},
       {"alt_std": 2.0, "stop_pct": 5.0}])
_ekle("HAM:X005:341", Rsi5Sma50S0341, ["1d"])
_ekle("HAM:X005:346", BandKirilimS0346, ["4h", "1d"])
_ekle("HAM:X005:348", RsiBb1IkiS0348, ["4h", "1d"])

KODLANAMADI = [
    {"kimlik": "HAM:X005:353",
     "neden": "HiLo formülü kaynakta yok (Gann HiLo varsayımı uydurma sayıldı); EmaHiloS0353 sınıfı kodda kalır, koşulmaz."},
    {"kimlik": "HAM:X005:356",
     "neden": "kural_tam belirsiz: 'orta bölüm MA'lar artan dizili', 'daha önce dip bir MA'ya temas' (hangi MA, kaç mum "
              "geriye) ve 'cari tepe önceki tepeyi aşıyor' kesin tanımlanmamış; kaynak Pine kodu repoda yok. "
              "Uydurma çözüm yazılmadı."},
]
