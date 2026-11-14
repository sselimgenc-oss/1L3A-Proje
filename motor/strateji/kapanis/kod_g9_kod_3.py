"""Kapanış turu, kodlama partisi g9_kod_3 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_3.csv, 30 kaynak satırı, HAM:B001 Robotic/Freqtrade).

Her sınıf, satırın `kanit` sütunundaki Freqtrade kaynak dosyası OKUNARAK (çalıştırılmadan) kendi cümlelerimizle yazılmış bir
uyarlamadır; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel; üst zaman
dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış -/+ 3 x ATR(14) (ön kayıt); aksi halde kaynak yüzde stopu sinyal kapanışından.
- Freqtrade `minimal_roi` ({dakika: oran}) -> `CikisAyarlari.azalan_roi` (mum = yukarı yuvarlanmış dakika / TF dakikası; aynı muma düşen
  basamaklarda büyük dakikalı olan geçerli; "0" oranı = kâr >= 0). Kâr kapanışta sınanır, çıkış sonraki açılışta (kaynakta mum içi).
- `trailing_stop_positive` / offset -> `geri_cekilme_yuzde` (iz) / `geri_cekilme_min_kar_yuzde` (offset; yalnız-offset=False ise 0),
  kâr% farkı, kapanış bazlı. `exit_profit_only` / `sell_profit_only` -> `yalniz_karda_cikis`.
- qtpylib Bollinger bantları ORNEK standart sapma (ddof=1) kullanır; burada da öyle (`_bbq`). talib STDDEV/BBANDS (ddof=0) kullanan
  satırlarda (208, 474 RSI sapması) `g.bollinger`/ddof=0.
- Kaldıraç (kaynakta 3-10x) motorda yok: 1x, boyut motor riski. Hacim eşiği içeren satırlarda eşik kaynaktaki mutlak değerdir.
- `ignore_roi_if_entry_signal=True` olan satırlarda (150, 203) ROI tablosu motor ROI'si yerine kancada (`pozisyon_cikisi`) uygulanır:
  aynı yönde giriş koşulu hâlâ doğruysa ROI çıkışı atlanır (Freqtrade semantiği).

KODLANAMADI: yok (30 satırın hepsi kodlandı).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import mfi as _mfi  # noqa: F401  (diverjans göstergeleri)
from motor.strateji._gosterge_d11j import obv as _obv
from motor.strateji._gosterge_d11j import ultimate_osc as _uo
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu, azalan_roi_doldu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek
from motor.strateji.seans_takvimi import mum_suresi
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _roi(tablo: dict, tf_dk: float) -> tuple:
    """{dakika: oran} -> ((mum, kâr%), ...). Aynı muma düşen basamaklarda büyük dakikalı olan geçerli (Freqtrade)."""
    d = {}
    for dk in sorted(tablo):
        d[int(math.ceil(dk / tf_dk))] = round(float(tablo[dk]) * 100.0, 6)
    return tuple(sorted(d.items()))


def _ayar(roi: dict | None, tf_dk: float, iz: tuple | None = None, yalniz_offset: bool = True,
          karda: bool = False) -> CikisAyarlari:
    """Freqtrade çıkış ayarı -> CikisAyarlari. iz = (trailing_stop_positive, offset) oran olarak."""
    kw = {}
    if roi:
        kw["azalan_roi"] = _roi(roi, tf_dk)
    if iz is not None:
        kw["geri_cekilme_yuzde"] = round(iz[0] * 100.0, 6)
        kw["geri_cekilme_min_kar_yuzde"] = round(iz[1] * 100.0, 6) if yalniz_offset else 0.0
    if karda:
        kw["yalniz_karda_cikis"] = True
    return CikisAyarlari(**kw)


def _stoplar(m: pd.DataFrame, sl: float | None, atr_n: int = 14, atr_k: float = 3.0):
    """(stop_long, stop_short). sl = kaynak stop oranı (örn. 0.2); None ya da >= 0.5 -> ATR(atr_n) x atr_k."""
    kap = m["kapanis"]
    if sl is None or float(sl) >= 0.5:
        mes = atr_k * g.atr(m["yuksek"], m["dusuk"], kap, atr_n)
        return kap - mes, kap + mes
    return kap * (1.0 - float(sl)), kap * (1.0 + float(sl))


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _ft(m: pd.DataFrame, al, sat, sl, cik_l=None, cik_s=None, **ata) -> pd.DataFrame:
    """Ortak çerçeve: giriş maskeleri + kaynak/ATR stopu + yönlü sinyal çıkışları."""
    stop_l, stop_s = _stoplar(m, sl, **ata)
    return _bitir(cerceve(m, al, sat, stop_l, stop_s), cik_l, cik_s)


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _bbq(seri: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """qtpylib tarzı Bollinger: SMA +/- k x ORNEK std (ddof=1)."""
    orta = seri.rolling(n).mean()
    sd = seri.rolling(n).std()
    return pd.DataFrame({"orta": orta, "ust": orta + k * sd, "alt": orta - k * sd})


def _tema(kap: pd.Series, n: int) -> pd.Series:
    e1 = g.ema(kap, n)
    e2 = g.ema(e1, n)
    e3 = g.ema(e2, n)
    return 3.0 * e1 - 3.0 * e2 + e3


def _linreg_uc(seri: pd.Series, n: int) -> pd.Series:
    """Son n değere en küçük kareler doğrusu; değer = doğrunun son mumdaki uç noktası (talib LINEARREG)."""
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xm = x.mean()
        w = 1.0 / n + (x - xm) * ((n - 1) / 2.0) / np.sum((x - xm) ** 2)
        out[n - 1:] = sliding_window_view(a, n) @ w
    return pd.Series(out, index=seri.index)


def _ust_rsi(m: pd.DataFrame, ust_dk: int, n: int) -> pd.Series:
    """Üst TF (ust_dk dakikalık) KAPANMIŞ mumlardan RSI(n)."""
    return ust_zaman(m, f"{int(ust_dk)}m", lambda u: g.rsi(u["kapanis"], n))


def _filtre_a(src: np.ndarray, sm: np.ndarray) -> np.ndarray:
    """Range Filter (150): kapanış önceki filtrenin üstündeyse kapanış; kapanış+aralık hâlâ üstündeyse önceki; yoksa kapanış+aralık.
    NaN aralıkta sonuç NaN, önceki NaN ise kapanış+aralık (Python karşılaştırma semantiği; kaynakla aynı)."""
    s, r = src.tolist(), sm.tolist()
    f = list(s)
    for i in range(1, len(s)):
        prev = f[i - 1]
        if s[i] > prev:
            f[i] = s[i]
        elif s[i] + r[i] > prev:
            f[i] = prev
        else:
            f[i] = s[i] + r[i]
    return np.asarray(f, dtype=float)


def _filtre_b(src: np.ndarray, sm: np.ndarray) -> np.ndarray:
    """Range Filter (235): kapanış önceki filtrenin üstündeyse max(kapanış-aralık, önceki); değilse min(kapanış+aralık, önceki)."""
    s, r = src.tolist(), sm.tolist()
    f = list(s)
    for i in range(1, len(s)):
        prev = f[i - 1]
        f[i] = max(s[i] - r[i], prev) if s[i] > prev else min(s[i] + r[i], prev)
    return np.asarray(f, dtype=float)


def _wt(esa_kaynak: pd.Series, n1: int, n2: int):
    """WaveTrend: ci=(x-esa)/(0.015 d); wt1=EMA(ci,n2). esa=EMA(x,n1), d=EMA(|x-esa|,n1)."""
    esa = g.ema(esa_kaynak, n1)
    d = g.ema((esa_kaynak - esa).abs(), n1)
    return g.ema((esa_kaynak - esa) / (0.015 * d), n2)


class _RoiKancaDestek(KancaDestek):
    """ignore_roi_if_entry_signal=True: ROI tablosu kancada; aynı yönde giriş koşulu sürüyorsa ROI çıkışı yok."""

    _roi_tablo: tuple = ()

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        if self._dz("al" if d.yon == 1 else "sat", d.mum_indeksi) > 0:
            return False
        return azalan_roi_doldu(d.tutulan_mum, d.kar_yuzde, self._roi_tablo)


# ================================================================ B001:150
class RangeFiltreB0150(_RoiKancaDestek, Strateji):
    """HAM:B001:150 (LongStrat2h_Long_Short.py, 15m, iki yön). Range Filter: smooth = EMA(EMA(|dKapanış|, t), 2t-1) x m; özyinelemeli filtre.
    Long filtresi t=189 m=2,161; short t=150 m=3,0. Long: kapanış > filtre_long x 0,99 VE filtre_long yükseliyor VE kapanış < 20 mumluk en
    yüksek kapanış; short: kapanış < filtre_short x 1,01 VE filtre_short düşüyor VE kapanış > 10 mumluk en düşük kapanış. Sinyal çıkışı
    kapalı (use_exit_signal=False). ROI {0:%64,8; 560dk:%24,7; 1400:%8,4; 3409:0} (ignore_roi_if_entry_signal: kancada), stop -%34,2,
    iz %2,7 (offset %4,7, yalnız offset).
    Uyarlama: kaynaktaki roll() sınır artefaktı yok (ilk fark NaN); EMA tohumu pandas (ewm adjust=False)."""

    ad, stil = "kapanis__range-filtre-b0150", "daytrade"
    varsayilan_parametreler = {"long_per": 189, "long_mult": 2.161, "short_per": 150, "short_mult": 3.0,
                               "visited_long": 10, "visited_short": 20, "long_oran": 0.99, "short_oran": 1.01,
                               "sl": 0.342}
    parametre_izgarasi = {}
    _roi_tablo = _roi({0: 0.648, 560: 0.247, 1400: 0.084, 3409: 0.0}, 15)
    cikis_ayarlari = _ayar(None, 15, iz=(0.027, 0.047))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        fark = kap.diff().abs()

        def filtre(per, mult):
            sm = g.ema(g.ema(fark, int(per)), 2 * int(per) - 1) * float(mult)
            return pd.Series(_filtre_a(kap.to_numpy(float), sm.to_numpy(float)), index=mumlar.index)

        fl, fs = filtre(p["long_per"], p["long_mult"]), filtre(p["short_per"], p["short_mult"])
        vis_l = kap > kap.rolling(int(p["visited_long"])).min()
        vis_s = kap < kap.rolling(int(p["visited_short"])).max()
        al = (kap > fl * float(p["long_oran"])) & (fl > fl.shift(1)) & vis_s
        sat = (kap < fs * float(p["short_oran"])) & (fs < fs.shift(1)) & vis_l
        self._sakla(al=al, sat=sat & ~al)
        return _ft(mumlar, al, sat, p["sl"])


# ================================================================ B001:168
class SupurmePocB0168(Strateji):
    """HAM:B001:168 (QMR.py, 15m, iki yön). range_hi/lo = 50 mumluk en yüksek yüksek / en düşük düşük (mevcut mum dahil); POC = SMA50(tipik).
    Long: düşük <= range_lo VE RSI14 < 30 VE kapanış > düşük VE hacim > 0; short: yüksek >= range_hi VE RSI14 > 70 VE kapanış < yüksek.
    Çıkış: long kapanış >= POC, short kapanış <= POC; yalnız kârda. ROI yok; stop -%99 -> ATR(14)x3.
    Uyarlama: Kelly boyutlama uygulanmaz (motor riski)."""

    ad, stil = "kapanis__supurme-poc-b0168", "daytrade"
    varsayilan_parametreler = {"pencere": 50, "rsi": 14, "rsi_long": 30.0, "rsi_short": 70.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar(None, 15, karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        n = int(p["pencere"])
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        hi, lo = yuk.rolling(n).max(), dus.rolling(n).min()
        poc = g.sma(_tipik(mumlar), n)
        r = g.rsi(kap, int(p["rsi"]))
        hv = mumlar["hacim"] > 0
        al = (dus <= lo) & (r < float(p["rsi_long"])) & (kap > dus) & hv
        sat = (yuk >= hi) & (r > float(p["rsi_short"])) & (kap < yuk) & hv
        return _ft(mumlar, al, sat, None, kap >= poc, kap <= poc)


# ================================================================ B001:190
def _pivotlar(kap: np.ndarray, w: int = 2):
    """Kapanış üzerinde pivot (w mum her iki yan): dip = komşulardan hiçbirinden büyük değil, tepe = hiçbirinden küçük değil.
    Pivot i satırına yazılır; ancak i+w mumu kapandığında bilinir (kullanan taraf w gecikmeli okur)."""
    n = len(kap)
    dip, tepe = np.zeros(n, bool), np.zeros(n, bool)
    if n >= 2 * w + 1:
        c = kap[w:n - w]
        lo, hi = np.ones(len(c), bool), np.ones(len(c), bool)
        for s in range(1, w + 1):
            for yon in (-s, s):
                komsu = kap[w + yon:n - w + yon]
                lo &= c <= komsu
                hi &= c >= komsu
        dip[w:n - w], tepe[w:n - w] = lo, hi
    return dip, tepe


def _diverjans(kap: np.ndarray, ind: np.ndarray, piv: list, yon: int, onceki: int = 5) -> np.ndarray:
    """Klasik diverjans (yon=1 boğa: fiyat daha düşük dip + gösterge daha yüksek; yon=-1 ayı). Her pivot için önceki `onceki` pivot
    en yakından başlayarak denenir; ilk fiyat+gösterge eşleşmesinde durulur ve iki pivotu birleştiren doğru (fiyat ve gösterge için)
    aradaki değerlerin boğada altında / ayıda üstünde kalmıyorsa (eşitlik ihlal) diverjans yok sayılır. Sonuç pivot satırına yazılır."""
    out = np.zeros(len(kap), bool)
    for k in range(1, len(piv)):
        i = piv[k]
        for j in piv[max(0, k - onceki):k][::-1]:
            if yon == 1:
                esles = kap[i] < kap[j] and ind[i] > ind[j]
            else:
                esles = kap[i] > kap[j] and ind[i] < ind[j]
            if not esles:
                continue
            ihlal = False
            if i - j > 1:
                t = np.arange(1, i - j) / (i - j)
                fp = kap[j] + (kap[i] - kap[j]) * t
                ip = ind[j] + (ind[i] - ind[j]) * t
                if yon == 1:
                    ihlal = bool(np.any(fp >= kap[j + 1:i]) or np.any(ip >= ind[j + 1:i]))
                else:
                    ihlal = bool(np.any(fp <= kap[j + 1:i]) or np.any(ip <= ind[j + 1:i]))
            out[i] = not ihlal
            break
    return out


def _gec(x: np.ndarray, k: int) -> np.ndarray:
    """x'i k mum geciktir (nedensel kaydırma)."""
    out = np.zeros(len(x), bool)
    if k < len(x):
        out[k:] = x[:len(x) - k]
    return out


class DiverjansPivotB0190(KancaDestek, Strateji):
    """HAM:B001:190 (AlexDivergenceV6__2.py, 15m, iki yön). 11 gösterge (RSI14, Stoch slowk 5/3/3, ROC10, ULTOSC, AO 5/34, MACD, CCI14, CMF20, OBV,
    MFI14, ADX14); kapanış pivotu (pencere 2). Boğa diverjansı: güncel pivot-dip, önceki 5 pivot-dipten birine göre fiyat DAHA DÜŞÜK + gösterge
    DAHA YÜKSEK ve birleştiren doğru fiyat/gösterge için ara değerlerin altında; ayı simetrik. Herhangi bir gösterge diverjans verirse pivot
    satırı işaretlenir; giriş 2 mum sonra (pivot onayı): long = boğa[t-2] VE hacim>0, short = ayı[t-2]. (hq kolu düz kolun alt kümesi.)
    Sinyal çıkışı: long ayı[t-2], short boğa[t-2]. Kanca (custom_exit): son 6 mumda ters diverjans (uyarlama: yalnız onaylı t-5..t-2) VEYA
    kapanış >= sinyal mumu yüksek + ATR(14, SMA) (kaynakta short'a da aynı koşul uygulanır, short stopu ile çakışır).
    Stop: sinyal mumu düşük(short: yüksek) -/+ ATR(14) (short simetrik uygulanır), en geniş sınır kaynak -%25. ROI {0:%5; 30dk %3; 60 %2;
    300 %1}; iz %2 (offset %3, yalnız offset).
    Uyarlama: kaynağın başlangıçtaki negatif indeks sarması (ilk 5 pivot) yok; yalnız gerçek önceki pivotlar kullanılır."""

    ad, stil = "kapanis__diverjans-pivot-b0190", "daytrade"
    varsayilan_parametreler = {"pivot_pencere": 2, "onceki_pivot": 5, "gecikme": 2, "ters_pencere": 6,
                               "kc_n": 20, "kc_atr_n": 10, "atr_n": 14, "sl": 0.25}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.05, 30: 0.03, 60: 0.02, 300: 0.01}, 15, iz=(0.02, 0.03))

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _gostergeler(m: pd.DataFrame) -> dict:
        y, d, k, h = m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        aralik = (y - d).where(lambda x: x > 0)
        mfv = ((((k - d) - (y - k)) / aralik).fillna(0.0)) * h
        cmf = mfv.rolling(20, min_periods=1).sum() / h.rolling(20, min_periods=1).sum()
        med = (y + d) / 2.0
        return {
            "rsi": g.rsi(k, 14),
            "stoch": g.stokastik(y, d, k, 5, 3)["d"],
            "roc": (k / k.shift(10) - 1.0) * 100.0,
            "uo": _uo(y, d, k, 7, 14, 28),
            "ao": g.sma(med, 5) - g.sma(med, 34),
            "macd": g.macd(k, 12, 26, 9)["macd"],
            "cci": b2.cci(y, d, k, 14),
            "cmf": cmf.replace([np.inf, -np.inf], np.nan),
            "obv": _obv(k, h),
            "mfi": _mfi(y, d, k, h, 14),
            "adx": g.adx(y, d, k, 14)["adx"],
        }

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        kv = kap.to_numpy(float)
        dip, tepe = _pivotlar(kv, int(p["pivot_pencere"]))
        pd_, pt_ = [int(i) for i in np.flatnonzero(dip)], [int(i) for i in np.flatnonzero(tepe)]
        boga, ayi = np.zeros(len(kv), bool), np.zeros(len(kv), bool)
        for x in self._gostergeler(mumlar).values():
            xv = x.to_numpy(float)
            boga |= _diverjans(kv, xv, pd_, 1, int(p["onceki_pivot"]))
            ayi |= _diverjans(kv, xv, pt_, -1, int(p["onceki_pivot"]))
        gec = int(p["gecikme"])
        boga_g, ayi_g = _gec(boga, gec), _gec(ayi, gec)
        hv = (mumlar["hacim"] > 0).to_numpy(bool)
        al, sat = pd.Series(boga_g & hv, index=mumlar.index), pd.Series(ayi_g & hv, index=mumlar.index)
        # kanca dizileri: son `ters_pencere` mumun onaylı kısmı (t-gecikme .. t-(ters_pencere-1))
        ters_ayi, ters_boga = np.zeros(len(kv), bool), np.zeros(len(kv), bool)
        for s in range(gec, int(p["ters_pencere"])):
            ters_ayi |= _gec(ayi, s)
            ters_boga |= _gec(boga, s)
        atr = (g.gercek_aralik(yuk, dus, kap)).rolling(int(p["atr_n"])).mean()
        self._sakla(ters_ayi=ters_ayi, ters_boga=ters_boga, tp=yuk + atr)
        sl = float(p["sl"])
        stop_l = np.maximum(dus - atr, kap * (1.0 - sl))
        stop_s = np.minimum(yuk + atr, kap * (1.0 + sl))
        return _bitir(cerceve(mumlar, al, sat, stop_l, stop_s), pd.Series(ayi_g & hv, index=mumlar.index),
                      pd.Series(boga_g & hv, index=mumlar.index))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        if self._dz("ters_ayi" if d.yon == 1 else "ters_boga", i) > 0:
            return True
        tp = self._dz("tp", d.giris_mum_indeksi - 1)
        return bool(tp == tp and d.kapanis >= tp)


# ================================================================ B001:202
class SmaRsiB0202(Strateji):
    """HAM:B001:202 (Best5m.py, 5m, iki yön). Long: SMA10 > SMA30 VE RSI14 < 30; short: SMA10 < SMA30 VE RSI14 > 70. Çıkış: long SMA10 < SMA30
    VE RSI14 > 70; short SMA10 > SMA30 VE RSI14 < 30; yalnız kârda. ROI {0: %1}; stop -%99 -> ATR(14)x3; trailing kapalı (varsayılan
    trailing_stop_opt=False, custom_stoploss durumu değiştirmez)."""

    ad, stil = "kapanis__sma-rsi-b0202", "daytrade"
    varsayilan_parametreler = {"sma_hizli": 10, "sma_yavas": 30, "rsi": 14, "rsi_long": 30.0, "rsi_short": 70.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.01}, 5, karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hz, yv = g.sma(kap, int(p["sma_hizli"])), g.sma(kap, int(p["sma_yavas"]))
        r = g.rsi(kap, int(p["rsi"]))
        lo, hi = float(p["rsi_long"]), float(p["rsi_short"])
        return _ft(mumlar, (hz > yv) & (r < lo), (hz < yv) & (r > hi), None,
                   (hz < yv) & (r > hi), (hz > yv) & (r < lo))


# ================================================================ B001:203
class RsiDolarHacimB0203(_RoiKancaDestek, Strateji):
    """HAM:B001:203 (DC_UT.py, 1h, long). RSI14 > 49 VE dolar hacim (hacim x kapanış, bir önceki mum) > 2.000.000 -> long (ma50 şartı kaynakta
    uygulanmıyor: sütun yok). Çıkış: RSI14 > 68 VE dolar hacim > 2.000.000; yalnız kârda. ROI {0:%12; 10dk %10; 25 %8; 60 %5}
    (ignore_roi_if_entry_signal: kancada); stop -%20."""

    ad, stil = "kapanis__rsi-dolar-hacim-b0203", "swing"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 49.0, "rsi_cikis": 68.0, "dolar_hacim_min": 2000000.0, "sl": 0.20}
    parametre_izgarasi = {}
    _roi_tablo = _roi({0: 0.12, 10: 0.10, 25: 0.08, 60: 0.05}, 60)
    cikis_ayarlari = _ayar(None, 60, karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        dv = (mumlar["hacim"] * kap).shift(1) > float(p["dolar_hacim_min"])
        al = (r > float(p["rsi_giris"])) & dv
        self._sakla(al=al, sat=pd.Series(False, index=mumlar.index))
        return _ft(mumlar, al, False, p["sl"], (r > float(p["rsi_cikis"])) & dv)


# ================================================================ B001:208
class SqueezeMomentumB0208(Strateji):
    """HAM:B001:208 (ImprovedClaudioStrategy036.py, 1h, long; TTM Squeeze). BB(20, 2; kapanış, ddof=0); KC = SMA20(kapanış) +/- 1,5 x SMA20(TR);
    sqz_off = BB alt < KC alt VE BB üst > KC üst. Momentum = LINEARREG(kapanış - ((en yüksek20 + en düşük20)/2 + SMA20)/2, 20).
    Giriş: mom > 0 VE mom > mom[-1] VE sqz_off. Çıkış: mom < 0 VE mom < mom[-1]. ROI {0: %5}; stop -%20; iz %0,05 (offset %1,5, yalnız offset).
    Uyarlama: confirm_trade_exit zarar vetosu yalnız sinyal/ROI çıkışlarına (yalniz_karda_cikis), stop -%20 korunur; pasif DCA kodu yok sayıldı."""

    ad, stil = "kapanis__squeeze-momentum-b0208", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "kc_n": 20, "kc_k": 1.5, "mom_n": 20, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.05}, 60, iz=(0.0005, 0.015), karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n = int(p["kc_n"])
        bb = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        ma = g.sma(kap, n)
        rng = g.sma(g.gercek_aralik(mumlar["yuksek"], mumlar["dusuk"], kap), n)
        kc_a, kc_u = ma - float(p["kc_k"]) * rng, ma + float(p["kc_k"]) * rng
        sqz_off = (bb["alt"] < kc_a) & (bb["ust"] > kc_u)
        ortalama = ((mumlar["yuksek"].rolling(n).max() + mumlar["dusuk"].rolling(n).min()) / 2.0 + ma) / 2.0
        mom = _linreg_uc(kap - ortalama, int(p["mom_n"]))
        return _ft(mumlar, (mom > 0) & (mom > mom.shift(1)) & sqz_off, False, p["sl"], (mom < 0) & (mom < mom.shift(1)))


# ================================================================ B001:209
class ImpulseMacdB0209(Strateji):
    """HAM:B001:209 (ImpulseMACD.py + ImpulseMACD.json hyperopt, 1h, iki yön). Impulse MACD: ort = (H+L+C)/3; SMMA(yüksek,20), SMMA(düşük,20);
    ZLEMA = 2 EMA20(ort) - EMA20(EMA20(ort)); imp = ZLEMA - SMMA_yüksek (ZLEMA > SMMA_yüksek), ZLEMA - SMMA_düşük (ZLEMA < SMMA_düşük), yoksa 0;
    sinyal = SMA14(imp). Long: imp sinyali yukarı keser VE hacim > 0; short aşağı keser. Çıkış dur-ve-ters (long: aşağı kesiş, short: yukarı).
    check_macd_position=False. json ROI {0:%24,4; 245dk %17,4; 935 %3,4; 2251 0}; stop -%35; iz %1,1 (offset %1,4, yalnız offset).
    Not: ısınma satırlarında imp (NaN karşılaştırması) 0 sayılır (kaynak np.where davranışı)."""

    ad, stil = "kapanis__impulse-macd-b0209", "swing"
    varsayilan_parametreler = {"ma_period": 20, "signal_period": 14, "sl": 0.35}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.244, 245: 0.174, 935: 0.034, 2251: 0.0}, 60, iz=(0.011, 0.014))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        n = int(p["ma_period"])
        yuk, dus = mumlar["yuksek"], mumlar["dusuk"]
        ort = (yuk + dus + mumlar["kapanis"]) / 3.0
        smma_h = yuk.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
        smma_l = dus.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
        e1 = g.ema(ort, n)
        zl = 2.0 * e1 - g.ema(e1, n)
        imp = pd.Series(np.where(zl > smma_h, zl - smma_h, np.where(zl < smma_l, zl - smma_l, 0.0)), index=mumlar.index)
        sig = g.sma(imp, int(p["signal_period"]))
        hv = mumlar["hacim"] > 0
        yk, ak = yukari(imp, sig) & hv, asagi(imp, sig) & hv
        return _ft(mumlar, yk, ak, p["sl"], ak, yk)


# ================================================================ B001:214
class BbGenislemeHacimB0214(Strateji):
    """HAM:B001:214 (RSIBB_V4.py, 15m, iki yön). RSI6, RSI12; BB(20, 2; tipik fiyat); bbw = (üst-alt)/orta; squeeze = bbw < 0,05; expansion = bbw >
    5 mumluk en düşük bbw x 1,2; hacim bandı = SMA20(hacim) + 2 x std20(hacim). Long: kapanış > BB üst VE expansion VE squeeze[-1] VE hacim >
    hacim üst bandı VE RSI6 > 50 VE RSI12 > 50; short: kapanış < BB alt ... RSI6 < 50 VE RSI12 < 50. Çıkış: long kapanış < BB orta VEYA hacim <
    SMA20(hacim); short kapanış > BB orta VEYA hacim < SMA20(hacim). ROI yok; stop -%20; iz %1,2 (offset %1,5, yalnız offset)."""

    ad, stil = "kapanis__bb-genisleme-hacim-b0214", "daytrade"
    varsayilan_parametreler = {"rsi_hizli": 6, "rsi_yavas": 12, "rsi_esik": 50.0, "bb_n": 20, "bb_k": 2.0,
                               "squeeze_esik": 0.05, "expansion": 1.2, "expansion_pencere": 5, "hacim_n": 20,
                               "hacim_k": 2.0, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar(None, 15, iz=(0.012, 0.015))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        rh, ry = g.rsi(kap, int(p["rsi_hizli"])), g.rsi(kap, int(p["rsi_yavas"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        bbw = (bb["ust"] - bb["alt"]) / bb["orta"]
        sq = (bbw < float(p["squeeze_esik"])).shift(1, fill_value=False)
        gen = bbw > bbw.rolling(int(p["expansion_pencere"])).min() * float(p["expansion"])
        hn = int(p["hacim_n"])
        hort = hac.rolling(hn).mean()
        vust = hort + float(p["hacim_k"]) * hac.rolling(hn).std()
        e = float(p["rsi_esik"])
        al = (kap > bb["ust"]) & gen & sq & (hac > vust) & (rh > e) & (ry > e)
        sat = (kap < bb["alt"]) & gen & sq & (hac > vust) & (rh < e) & (ry < e)
        return _ft(mumlar, al, sat, p["sl"], (kap < bb["orta"]) | (hac < hort), (kap > bb["orta"]) | (hac < hort))


# ================================================================ B001:231
class RsiMacdBbTemaB0231(Strateji):
    """HAM:B001:231 (sample_strategy__2.py, 1h, long). Giriş: RSI14 30'u yukarı keser VE TEMA9 <= BB(20, 2; tipik) orta VE hacim > 0 VE MACD(12,26,9) >
    sinyal VE kapanış < BB alt. Çıkış (OR; VE önceliği yazıldığı gibi): RSI14 70'i yukarı keser VEYA (TEMA9 > BB orta VE TEMA9 düşüyor) VEYA
    MACD < sinyal VEYA (kapanış > BB üst VE hacim > 0). ROI {0:%2; 20dk %0,5; 40 %0,6; 60 %1,5; 120 0}; stop -%10; iz %1 (offset %2, yalnız
    offset DEĞİL: iz offsetten önce de çalışır)."""

    ad, stil = "kapanis__rsi-macd-bb-tema-b0231", "swing"
    varsayilan_parametreler = {"rsi": 14, "buy_rsi": 30.0, "sell_rsi": 70.0, "tema": 9, "bb_n": 20, "bb_k": 2.0, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.02, 20: 0.005, 40: 0.006, 60: 0.015, 120: 0.0}, 60, iz=(0.01, 0.02), yalniz_offset=False)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        tema = _tema(kap, int(p["tema"]))
        mc = g.macd(kap, 12, 26, 9)
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        hv = mumlar["hacim"] > 0
        al = yukari(r, float(p["buy_rsi"])) & (tema <= bb["orta"]) & hv & (mc["macd"] > mc["sinyal"]) & (kap < bb["alt"])
        dusen = (tema > bb["orta"]) & (tema < tema.shift(1))
        cik = yukari(r, float(p["sell_rsi"])) | dusen | (mc["macd"] < mc["sinyal"]) | ((kap > bb["ust"]) & hv)
        return _ft(mumlar, al, False, p["sl"], cik)


# ================================================================ B001:235
class WavetrendRangeB0235(Strateji):
    """HAM:B001:235 (scalpv3.py, 5m, iki yön). WaveTrend (hlc3; esa=EMA10, d=EMA10, wt1=EMA21(ci), wt2=SMA4(wt1)); para akışı hızlı = 2 SMA9(hlc3 -
    SMA9(hlc3)) / SMA9(H-L) x 5, yavaş aynı (10); Range Filter (smooth = EMA199(EMA100(|dKapanış|)) x 3; özyinelemeli rngfilt; hband/lband = rngfilt +/-
    smooth); RSI14; MACD(14,26,9). Long: wt1 wt2'yi yukarı keser VE hızlı > yavaş akış VE kapanış < hband VE RSI < 70 VE MACD > sinyal; short ayna
    (lband, RSI > 30). Çıkış: long wt aşağı kesiş VE kapanış > hband VE RSI > 70 VE MACD < sinyal; short ayna. ROI {0:%6; 5dk %5,5; 10 %4; 15 %3; 20
    %2; 25 %1}; stop -%70 -> ATR(14)x3; iz %1 (offset %4,5, yalnız offset)."""

    ad, stil = "kapanis__wavetrend-range-b0235", "daytrade"
    varsayilan_parametreler = {"n1": 10, "n2": 21, "wt_sma": 4, "akis_hizli": 9, "akis_yavas": 10, "akis_carpan": 5.0,
                               "filtre_per": 100, "filtre_mult": 3.0, "rsi": 14, "macd": (14, 26, 9)}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.06, 5: 0.055, 10: 0.04, 15: 0.03, 20: 0.02, 25: 0.01}, 5, iz=(0.01, 0.045))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        hlc3 = (yuk + dus + kap) / 3.0
        wt1 = _wt(hlc3, int(p["n1"]), int(p["n2"]))
        wt2 = g.sma(wt1, int(p["wt_sma"]))

        def akis(n):
            return 2.0 * g.sma(hlc3 - g.sma(hlc3, n), n) / g.sma(yuk - dus, n) * float(p["akis_carpan"])

        hizli, yavas = akis(int(p["akis_hizli"])), akis(int(p["akis_yavas"]))
        per = int(p["filtre_per"])
        sm = g.ema(g.ema(kap.diff().abs(), per), 2 * per - 1) * float(p["filtre_mult"])
        rf = pd.Series(_filtre_b(kap.to_numpy(float), sm.to_numpy(float)), index=mumlar.index)
        hband, lband = rf + sm, rf - sm
        r = g.rsi(kap, int(p["rsi"]))
        mc = g.macd(kap, *[int(x) for x in p["macd"]])
        yk, ak = yukari(wt1, wt2), asagi(wt1, wt2)
        al = yk & (hizli > yavas) & (kap < hband) & (r < 70) & (mc["macd"] > mc["sinyal"])
        sat = ak & (hizli < yavas) & (kap > lband) & (r > 30) & (mc["macd"] < mc["sinyal"])
        cik_l = ak & (kap > hband) & (r > 70) & (mc["macd"] < mc["sinyal"])
        cik_s = yk & (kap < lband) & (r < 30) & (mc["macd"] > mc["sinyal"])
        return _ft(mumlar, al, sat, None, cik_l, cik_s)


# ================================================================ B001:252
class WtSeviyeB0252(Strateji):
    """HAM:B001:252 (SuperTrade.py, 5m, iki yön). WaveTrend (kapanış; esa=EMA9, d=EMA9, wt1=EMA21(ci)). Giriş seviye tetikli: long wt1 < -60 (boğa
    diverjansı VEYA wt1 < -60 = wt1 < -60); short wt1 > 60. Çıkış: long wt1 > 0, short wt1 < 0; yalnız kârda. ROI yok; stop -%29,6; iz %1
    (offset %10, yalnız offset)."""

    ad, stil = "kapanis__wt-seviye-b0252", "daytrade"
    varsayilan_parametreler = {"n1": 9, "n2": 21, "ob": 60.0, "os": -60.0, "sl": 0.296}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar(None, 5, iz=(0.01, 0.10), karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        wt1 = _wt(mumlar["kapanis"], int(p["n1"]), int(p["n2"]))
        return _ft(mumlar, wt1 < float(p["os"]), wt1 > float(p["ob"]), p["sl"], wt1 > 0, wt1 < 0)


# ================================================================ B001:380
class SmaMacdKesisimB0380(Strateji):
    """HAM:B001:380 (AlligatorStrat.py, 4h, long). Giriş: (SMA5 SMA8'i yukarı keser VE MACD(12,26,9) > -0,00001 VE MACD > sinyal) VEYA MACD sinyali
    yukarı keser. Çıkış: (kapanış < SMA8 VE MACD < sinyal) VEYA MACD sinyali aşağı keser. ROI {0: %10}; stop -%20. (SMA13 hesaplanır, kullanılmaz.)"""

    ad, stil = "kapanis__sma-macd-kesisim-b0380", "swing"
    varsayilan_parametreler = {"sma_kisa": 5, "sma_orta": 8, "macd_esik": -1e-05, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.10}, 240)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        sk, so = g.sma(kap, int(p["sma_kisa"])), g.sma(kap, int(p["sma_orta"]))
        mc = g.macd(kap, 12, 26, 9)
        m_, s_ = mc["macd"], mc["sinyal"]
        al = (yukari(sk, so) & (m_ > float(p["macd_esik"])) & (m_ > s_)) | yukari(m_, s_)
        cik = ((kap < so) & (m_ < s_)) | asagi(m_, s_)
        return _ft(mumlar, al, False, p["sl"], cik)


# ================================================================ B001:381
class EmaDizilimStochRsiB0381(Strateji):
    """HAM:B001:381 (AlligatorStrategy.py, 1h, long). EMA7/30/50/100/121/200; StochRSI = ham (0-1) RSI14 stokastiği (ta.stochrsi yumuşatılmamış değer;
    kaynak yorumu 'Non moyenné'). Giriş: EMA7 > EMA30 > EMA50 > EMA100 > EMA121 > EMA200 VE stochrsi < 0,82 VE hacim > 0. Çıkış: EMA121 > EMA7 VE
    stochrsi > 0,2 VE hacim > 0. ROI {0: 100} = devre dışı (tanımlanmadı); stop -%99 -> ATR(14)x3."""

    ad, stil = "kapanis__ema-dizilim-stochrsi-b0381", "swing"
    varsayilan_parametreler = {"ema": (7, 30, 50, 100, 121, 200), "rsi": 14, "stoch_n": 14, "buy_stoch": 0.82, "sell_stoch": 0.2}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        e = [g.ema(kap, int(n)) for n in p["ema"]]
        r = g.rsi(kap, int(p["rsi"]))
        n = int(p["stoch_n"])
        alt, ust = r.rolling(n).min(), r.rolling(n).max()
        sr = (r - alt) / (ust - alt).where(lambda x: x > 0)
        hv = mumlar["hacim"] > 0
        dizi = pd.Series(True, index=mumlar.index)
        for a, b in zip(e[:-1], e[1:]):
            dizi &= a > b
        al = dizi & (sr < float(p["buy_stoch"])) & hv
        cik = (e[4] > e[0]) & (sr > float(p["sell_stoch"])) & hv
        return _ft(mumlar, al, False, None, cik)


# ================================================================ B001:463 / 473
class BbRsi1sdB0463(Strateji):
    """HAM:B001:463 (BBRSI.py, 4h, long). BB(20, 1; tipik) alt/üst; RSI14. Giriş: RSI > 25 VE kapanış < BB alt. Çıkış: RSI > 95 VE kapanış > BB üst.
    ROI {0:%21,5; 21dk %5,49; 48 %1,30; 125 0}; stop -%36,04; trailing kapalı."""

    ad, stil = "kapanis__bbrsi-1sd-b0463", "swing"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 25.0, "rsi_cikis": 95.0, "bb_n": 20, "bb_k": 1.0, "sl": 0.3603667187598833}
    parametre_izgarasi = {}
    ROI = {0: 0.21547444718127343, 21: 0.054918778723794665, 48: 0.013037720775643222, 125: 0.0}
    cikis_ayarlari = _ayar(ROI, 240)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        return _ft(mumlar, (r > float(p["rsi_giris"])) & (kap < bb["alt"]), False, p["sl"],
                   (r > float(p["rsi_cikis"])) & (kap > bb["ust"]))


class BbRsi1sdB0473(BbRsi1sdB0463):
    """HAM:B001:473 (BBRSIStrategy.py, 15m, long): 463 ile aynı kural ve aynı ROI/stop; yalnız TF 15m (ROI mum sayısı 15m'e çevrilir)."""

    ad, stil = "kapanis__bbrsi-1sd-b0473", "daytrade"
    cikis_ayarlari = _ayar(BbRsi1sdB0463.ROI, 15)


# ================================================================ B001:466
class RsiBbUstB0466(Strateji):
    """HAM:B001:466 (BBRSI3366.py, 5m, long). Giriş: RSI14 < 33. Çıkış: kapanış > BB(20, 1; tipik) üst VE RSI14 > 66. ROI {0:%9,52; 13dk %7,34; 30
    %1,47; 85 0}; stop -%33,23; iz %5,07 (offset %6,19, yalnız offset DEĞİL: iz offsetten önce de çalışır)."""

    ad, stil = "kapanis__rsi-bb-ust-b0466", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 33.0, "rsi_cikis": 66.0, "bb_n": 20, "bb_k": 1.0, "sl": 0.33233}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.09521, 13: 0.07341, 30: 0.01468, 85: 0.0}, 5, iz=(0.05069, 0.06189), yalniz_offset=False)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        return _ft(mumlar, r < float(p["rsi_giris"]), False, p["sl"], (kap > bb["ust"]) & (r > float(p["rsi_cikis"])))


# ================================================================ B001:468
class BbRsiNaifB0468(Strateji):
    """HAM:B001:468 (BBRSINaiveStrategy.py, 15m, long). Giriş: RSI14 > 25 VE kapanış < BB(20, 2; tipik) alt. Çıkış: RSI14 > 70 VE kapanış > BB orta.
    ROI {0:%4; 30dk %2; 60 %1}; stop -%10."""

    ad, stil = "kapanis__bbrsi-naif-b0468", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 25.0, "rsi_cikis": 70.0, "bb_n": 20, "bb_k": 2.0, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({60: 0.01, 30: 0.02, 0: 0.04}, 15)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        return _ft(mumlar, (r > float(p["rsi_giris"])) & (kap < bb["alt"]), False, p["sl"],
                   (r > float(p["rsi_cikis"])) & (kap > bb["orta"]))


# ================================================================ B001:472
class BbRsiCokluTfB0472(Strateji):
    """HAM:B001:472 (BBRSIS.py, 5m, long). SMA5/75/200; RSI20 (5m) ve 15/30/50 dakikalık KAPANMIŞ üst mumlardan RSI20 (htf.ust_zaman); BB(20, 3; tipik).
    Giriş: kapanış < BB alt VE SMA5 >= SMA75 VE SMA75 >= SMA200 VE RSI < RSI_15m - 5 VE hacim > 0. Çıkış: kapanış > BB orta VE RSI > RSI_15m + 5
    VE RSI > RSI_30m VE RSI > RSI_50m VE hacim > 0. ROI {0: %30}; stop -%99 -> ATR(14)x3."""

    ad, stil = "kapanis__bbrsi-coklu-tf-b0472", "daytrade"
    varsayilan_parametreler = {"rsi": 20, "bb_n": 20, "bb_k": 3.0, "carpan": (3, 6, 10), "fark": 5.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.30}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        dk = mum_suresi(mumlar.index) / pd.Timedelta(minutes=1)
        n = int(p["rsi"])
        r = g.rsi(kap, n)
        r1, r2, r3 = (_ust_rsi(mumlar, int(round(dk * int(c))), n) for c in p["carpan"])
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        s5, s75, s200 = g.sma(kap, 5), g.sma(kap, 75), g.sma(kap, 200)
        hv = mumlar["hacim"] > 0
        f = float(p["fark"])
        al = (kap < bb["alt"]) & (s5 >= s75) & (s75 >= s200) & (r < r1 - f) & hv
        cik = (kap > bb["orta"]) & (r > r1 + f) & (r > r2) & (r > r3) & hv
        return _ft(mumlar, al, False, None, cik)


# ================================================================ B001:474
class RsiBbTvB0474(Strateji):
    """HAM:B001:474 (BBRSITV.py, 5m, long). RSI14; basis_n = EMA(RSI, n), dev_n = std(RSI, n; ddof=0); EWO = (EMA50 - EMA200) / kapanış x 100. Giriş: RSI <
    basis_22 - 1,74 x dev_22 VE EWO > 4,86 VE hacim > 0. Çıkış: (RSI > 72 VEYA RSI > basis_65 + 1,895 x dev_65) VE hacim > 0. ROI {0: %10};
    stop -%25; trailing kapalı."""

    ad, stil = "kapanis__rsi-bb-tv-b0474", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "ewo_hizli": 50, "ewo_yavas": 200, "ewo_yuksek": 4.86, "for_sigma": 1.74,
                               "for_sigma_sell": 1.895, "rsi_yuksek": 72.0, "for_ma_length": 22,
                               "for_ma_length_sell": 65, "sl": 0.25}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.10}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        ewo = (g.ema(kap, int(p["ewo_hizli"])) - g.ema(kap, int(p["ewo_yavas"]))) / kap * 100.0
        na, ns = int(p["for_ma_length"]), int(p["for_ma_length_sell"])
        b_a, d_a = g.ema(r, na), r.rolling(na).std(ddof=0)
        b_s, d_s = g.ema(r, ns), r.rolling(ns).std(ddof=0)
        hv = mumlar["hacim"] > 0
        al = (r < b_a - d_a * float(p["for_sigma"])) & (ewo > float(p["ewo_yuksek"])) & hv
        cik = ((r > float(p["rsi_yuksek"])) | (r > b_s + d_s * float(p["for_sigma_sell"]))) & hv
        return _ft(mumlar, al, False, p["sl"], cik)


# ================================================================ B001:475
class Bb3SigmaAltB0475(Strateji):
    """HAM:B001:475 (BBRSIoriginal.py, 1h, long). Giriş: kapanış < BB(20, 3; tipik) alt. Çıkış: RSI14 > 75 VE kapanış > BB orta. ROI {0:%9,64; 19dk %3,64;
    69 %1,92; 120 0}; stop -%36,83."""

    ad, stil = "kapanis__bb3sigma-alt-b0475", "swing"
    varsayilan_parametreler = {"rsi": 14, "rsi_cikis": 75.0, "bb_n": 20, "bb_k": 3.0, "sl": 0.36828}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.09638, 19: 0.03643, 69: 0.01923, 120: 0.0}, 60)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        r = g.rsi(kap, int(p["rsi"]))
        return _ft(mumlar, kap < bb["alt"], False, p["sl"], (r > float(p["rsi_cikis"])) & (kap > bb["orta"]))


# ================================================================ B001:476
class BbRsiTemaIzB0476(KancaDestek, Strateji):
    """HAM:B001:476 (BBRSIv2.py, 15m, long). RSI14; BB(20, 2; tipik); TEMA9(kapanış); close_max = 60 mumluk en yüksek kapanış. RB1: RSI 35'i yukarı keser
    VE kapanış < BB alt. RB2: RSI < 23 VE TEMA < BB alt VE TEMA yükseliyor VE hacim > 0. Giriş = RB1 VEYA RB2. Çıkış: RSI > 70 VEYA yüksek > close_max;
    yalnız kârda. ROI {0: %30}; stop -%99 -> ATR(14)x3 (zararda stopsuz kaynak). custom_stoploss kâr basamaklı iz stop: kâr > %3 iken stop güncel fiyatın
    %1 altı, > %6 %2, > %10 %3, > %20 %5 (yalnız yukarı taşınır; backtest kolu sl_new=1). Kancada kapanış bazlı: girişten önceki mumun kapanışına
    göre hesaplanan en yüksek seviyenin altına/eşitine inen kapanış çıkar (uyarlama)."""

    ad, stil = "kapanis__bbrsi-tema-iz-b0476", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "bb_n": 20, "bb_k": 2.0, "tema": 9, "close_max_n": 60, "rsi_rb1": 35.0,
                               "rsi_rb2": 23.0, "rsi_cikis": 70.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.30}, 15, karda=True)
    BASAMAK = ((0.20, 0.05), (0.10, 0.03), (0.06, 0.02), (0.03, 0.01))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        tema = _tema(kap, int(p["tema"]))
        hv = mumlar["hacim"] > 0
        rb1 = yukari(r, float(p["rsi_rb1"])) & (kap < bb["alt"])
        rb2 = (r < float(p["rsi_rb2"])) & (tema < bb["alt"]) & (tema > tema.shift(1)) & hv
        cmax = kap.rolling(int(p["close_max_n"])).max()
        cik = (r > float(p["rsi_cikis"])) | (mumlar["yuksek"] > cmax)
        self._sakla(kap=kap)
        return _ft(mumlar, rb1 | rb2, False, None, cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i, g0 = d.mum_indeksi, d.giris_mum_indeksi
        if not self._var(i) or i <= g0 or d.giris_fiyati <= 0:
            return False
        kv = self._kd["kap"]
        c = kv[g0:i]                       # önceki kapanışlar (stop bir sonraki mumdan geçerli)
        kar = c / d.giris_fiyati - 1.0
        oran = np.full(len(c), np.nan)
        for esik, sl in self.BASAMAK[::-1]:   # küçükten büyüğe; büyük eşik en son yazılır
            oran[kar > esik] = sl
        seviye = c * (1.0 - oran)
        seviye = seviye[np.isfinite(seviye)]
        return bool(len(seviye) and kv[i] <= seviye.max())


# ================================================================ B001:477
class BbRsi1sdAltB0477(Strateji):
    """HAM:B001:477 (BB_RSI.py, 1h, long). Giriş: kapanış < BB(20, 1; tipik) alt VE RSI14 > 7. Çıkış: kapanış > BB üst VE RSI14 > 74; yalnız kârda.
    ROI {0:%40; 335dk %18,83; 564 %7,35; 1097 0}; stop -%6,49; iz %1,04 (offset %2,41, yalnız offset DEĞİL)."""

    ad, stil = "kapanis__bbrsi-1sd-alt-b0477", "swing"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 7.0, "rsi_cikis": 74.0, "bb_n": 20, "bb_k": 1.0, "sl": 0.06491}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.4, 335: 0.18834, 564: 0.07349, 1097: 0.0}, 60, iz=(0.01036, 0.02409), yalniz_offset=False,
                           karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi"]))
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        return _ft(mumlar, (kap < bb["alt"]) & (r > float(p["rsi_giris"])), False, p["sl"],
                   (kap > bb["ust"]) & (r > float(p["rsi_cikis"])))


# ================================================================ B001:478
class Bb72Sigma2B0478(Strateji):
    """HAM:B001:478 (BB_Strategy04.py, 1h, long). BB(kapanış, 72, 2) alt/üst (kapanış tabanlı, tipik değil). Giriş: kapanış < BB alt VE kapanış > BB alt
    x (1 - 0,3253). Çıkış: kapanış > BB üst. ROI {0:%22,6; 180dk %6,27; 613 %3,77; 2004 0}; stop -%32,53; trailing kapalı."""

    ad, stil = "kapanis__bb72-sigma2-b0478", "swing"
    varsayilan_parametreler = {"bb_n": 72, "bb_k": 2.0, "alt_sinir": 0.32530922906811843, "sl": 0.32530922906811843}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.22597784040439192, 180: 0.06269048445164815, 613: 0.037662786960331776, 2004: 0.0}, 60)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = _bbq(kap, int(p["bb_n"]), float(p["bb_k"]))
        al = (kap < bb["alt"]) & (kap > bb["alt"] * (1.0 - float(p["alt_sinir"])))
        return _ft(mumlar, al, False, p["sl"], kap > bb["ust"])


# ================================================================ B001:482
class Ema5BbOrtaB0482(Strateji):
    """HAM:B001:482 (Babico_SMA5xBBmid.py, 1d, long). Giriş: EMA5 BB(20, 2; tipik) orta bandını yukarı keser. Çıkış: BB orta EMA5'i yukarı keser; yalnız
    kârda. ROI 99999999 (fiilen yok, tanımlanmadı); stop -%99 -> ATR(14)x3; trailing kapalı."""

    ad, stil = "kapanis__ema5-bb-orta-b0482", "swing"
    varsayilan_parametreler = {"ema": 5, "bb_n": 20, "bb_k": 2.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar(None, 1440, karda=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        orta = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["orta"]
        e = g.ema(kap, int(p["ema"]))
        return _ft(mumlar, yukari(e, orta), False, None, yukari(orta, e))


# ================================================================ B001:484
class BbOrtaUstTrendB0484(Strateji):
    """HAM:B001:484 (BbRoi.py, 15m, long). EMA9/20/200; BB(20, 2; tipik). Giriş: kapanış > BB orta VE kapanış < BB üst VE kapanış > EMA9 VE kapanış > EMA200
    VE EMA20 > EMA200. Çıkış: RSI14 > 75 VEYA (kapanış < BB orta x 0,97 VE açılış > kapanış). ROI {0:%17,55; 53dk %11,47; 226 %6,13; 400 0}; stop
    -%23,7; iz %1,01 (offset %1,82, yalnız offset)."""

    ad, stil = "kapanis__bb-orta-ust-trend-b0484", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "rsi_cikis": 75.0, "bb_n": 20, "bb_k": 2.0, "dusus": 0.97, "sl": 0.23701}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.17552, 53: 0.11466, 226: 0.06134, 400: 0.0}, 15, iz=(0.01007, 0.01821))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        e9, e20, e200 = g.ema(kap, 9), g.ema(kap, 20), g.ema(kap, 200)
        r = g.rsi(kap, int(p["rsi"]))
        al = (kap > bb["orta"]) & (kap < bb["ust"]) & (kap > e9) & (kap > e200) & (e20 > e200)
        cik = (r > float(p["rsi_cikis"])) | ((kap < bb["orta"] * float(p["dusus"])) & (mumlar["acilis"] > kap))
        return _ft(mumlar, al, False, p["sl"], cik)


# ================================================================ B001:488
class CmoBbUstB0488(Strateji):
    """HAM:B001:488 (Chandem.py, 5m, long). CMO(50) (talib Wilder tanımı = 2 RSI50 - 100); BB(25, 3,5; tipik) üst. Giriş: CMO[-1] sıfırı yukarı keser VE CMO >= 0
    (yani CMO[t-1] > 0 VE CMO[t-2] <= 0). Çıkış: kapanış BB üstünü yukarı keser. ROI {0:%28,4; 974dk %9,27; 1740 %6,55; 3087 0}; stop -%28,03; iz %1,01
    (offset %10,86, yalnız offset)."""

    ad, stil = "kapanis__cmo-bb-ust-b0488", "daytrade"
    varsayilan_parametreler = {"cmo": 50, "bb_n": 25, "bb_k": 3.5, "sl": 0.28031}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.28396, 974: 0.09268, 1740: 0.06554, 3087: 0.0}, 5, iz=(0.01013, 0.10858))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        cmo = 2.0 * g.rsi(kap, int(p["cmo"])) - 100.0
        ust = _bbq(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["ust"]
        return _ft(mumlar, yukari(cmo.shift(1), 0.0) & (cmo >= 0), False, p["sl"], yukari(kap, ust))


# ================================================================ B001:499
class EmaBbRsiUcKolB0499(Strateji):
    """HAM:B001:499 (EMABBRSI.py, 1h, long). EMA50/200; RSI14; BB(20, 3; tipik) ve BB(20, 2; tipik). Giriş (OR): (RSI > 33 VE kapanış BB3 altını yukarı keser) VEYA
    (önceki kapanış > EMA200 VE düşük < EMA200 VE kapanış > EMA200) VEYA EMA50 EMA200'ü yukarı keser. Çıkış: (kapanış > BB2 alt VE RSI > 91) VEYA EMA50
    EMA200'ün altına keser. ROI {0:%14,14; 25dk %4,59; 41 %2,07; 67 0}; stop -%20."""

    ad, stil = "kapanis__ema-bb-rsi-uc-kol-b0499", "swing"
    varsayilan_parametreler = {"rsi": 14, "rsi_giris": 33.0, "rsi_cikis": 91.0, "bb3_k": 3.0, "bb2_k": 2.0, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.14142349227153977, 25: 0.04585271106137356, 41: 0.020732379189664467, 67: 0.0}, 60)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, dus = mumlar["kapanis"], mumlar["dusuk"]
        tp = _tipik(mumlar)
        e50, e200 = g.ema(kap, 50), g.ema(kap, 200)
        r = g.rsi(kap, int(p["rsi"]))
        alt3 = _bbq(tp, 20, float(p["bb3_k"]))["alt"]
        alt2 = _bbq(tp, 20, float(p["bb2_k"]))["alt"]
        al = ((r > float(p["rsi_giris"])) & yukari(kap, alt3)) | ((kap.shift(1) > e200) & (dus < e200) & (kap > e200)) | yukari(e50, e200)
        cik = ((kap > alt2) & (r > float(p["rsi_cikis"]))) | asagi(e50, e200)
        return _ft(mumlar, al, False, p["sl"], cik)


# ================================================================ B001:501
class Rsi8KesisimB0501(Strateji):
    """HAM:B001:501 (FiveMinCrossAbove.py, 5m, long). Giriş: RSI8 30'u yukarı keser VE RSI8 < 41. Sinyal çıkışı yok (kaynakta ölü koşul). ROI {0:%1,5; 25dk
    %1; 100 %0,5}; stop -%99 -> ATR(14)x3 (felaket stopu)."""

    ad, stil = "kapanis__rsi8-kesisim-b0501", "daytrade"
    varsayilan_parametreler = {"rsi": 8, "seviye": 30.0, "ust_sinir": 41.0}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.015, 25: 0.01, 100: 0.005}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        r = g.rsi(mumlar["kapanis"], int(p["rsi"]))
        return _ft(mumlar, yukari(r, float(p["seviye"])) & (r < float(p["ust_sinir"])), False, None)


# ================================================================ B001:502 / 503
class BbAltCikisB0502(Strateji):
    """HAM:B001:502 (FrostAuraM115mStrategy.py, 15m, long). Giriş: kapanış < BB(20, 2; tipik) alt (kapanış > 1,5e-6). Çıkış: RSI14 > 53 VE kapanış > BB(20, 1)
    alt. ROI {0:%25,02; 89dk %9,50; 248 %2,60; 350 0}; stop -%34,32; trailing kapalı."""

    ad, stil = "kapanis__bb-alt-cikis-b0502", "daytrade"
    varsayilan_parametreler = {"rsi": 14, "rsi_cikis": 53.0, "bb_n": 20, "giris_k": 2.0, "cikis_k": 1.0, "asgari_fiyat": 1.5e-06,
                               "cikis_bant": "alt", "sl": 0.34316}
    parametre_izgarasi = {}
    cikis_ayarlari = _ayar({0: 0.25023, 89: 0.09497, 248: 0.02596, 350: 0.0}, 15)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        giris = _bbq(tp, int(p["bb_n"]), float(p["giris_k"]))["alt"]
        cik_bb = _bbq(tp, int(p["bb_n"]), float(p["cikis_k"]))[str(p["cikis_bant"])]
        r = g.rsi(kap, int(p["rsi"]))
        return _ft(mumlar, (kap < giris) & (kap > float(p["asgari_fiyat"])), False, p["sl"], (r > float(p["rsi_cikis"])) & (kap > cik_bb))


class BbAltCikisB0503(BbAltCikisB0502):
    """HAM:B001:503 (FrostAuraM11hStrategy.py, 1h, long). Giriş: kapanış < BB(20, 2; tipik) alt (kapanış > 1,5e-6). Çıkış: RSI14 > 97 VE kapanış > BB(20, 1)
    ÜST. ROI {0:%31,64; 467dk %10,19; 1143 %2,53; 2368 0}; stop -%40,62; trailing kapalı."""

    ad, stil = "kapanis__bb-alt-cikis-b0503", "swing"
    varsayilan_parametreler = {**BbAltCikisB0502.varsayilan_parametreler, "rsi_cikis": 97.0, "cikis_bant": "ust", "sl": 0.40618}
    cikis_ayarlari = _ayar({0: 0.31637, 467: 0.10191, 1143: 0.0253, 2368: 0.0}, 60)


# ================================================================ koşu listesi
def _v(kaynak: str, sinif, tf: str, no: int = 1) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad, "parametreler": dict(sinif.varsayilan_parametreler), "tf": tf}


SINIFLAR = [RangeFiltreB0150, SupurmePocB0168, DiverjansPivotB0190, SmaRsiB0202, RsiDolarHacimB0203, SqueezeMomentumB0208,
            ImpulseMacdB0209, BbGenislemeHacimB0214, RsiMacdBbTemaB0231, WavetrendRangeB0235, WtSeviyeB0252, SmaMacdKesisimB0380,
            EmaDizilimStochRsiB0381, BbRsi1sdB0463, BbRsi1sdB0473, RsiBbUstB0466, BbRsiNaifB0468, BbRsiCokluTfB0472, RsiBbTvB0474,
            Bb3SigmaAltB0475, BbRsiTemaIzB0476, BbRsi1sdAltB0477, Bb72Sigma2B0478, Ema5BbOrtaB0482, BbOrtaUstTrendB0484,
            CmoBbUstB0488, EmaBbRsiUcKolB0499, Rsi8KesisimB0501, BbAltCikisB0502, BbAltCikisB0503]

VARYANTLAR = [
    _v("HAM:B001:150", RangeFiltreB0150, "15m"),
    _v("HAM:B001:168", SupurmePocB0168, "15m"),
    _v("HAM:B001:190", DiverjansPivotB0190, "15m"),
    _v("HAM:B001:202", SmaRsiB0202, "5m"),
    _v("HAM:B001:203", RsiDolarHacimB0203, "1h"),
    _v("HAM:B001:208", SqueezeMomentumB0208, "1h"),
    _v("HAM:B001:209", ImpulseMacdB0209, "1h"),
    _v("HAM:B001:214", BbGenislemeHacimB0214, "15m"),
    _v("HAM:B001:231", RsiMacdBbTemaB0231, "1h"),
    _v("HAM:B001:235", WavetrendRangeB0235, "5m"),
    _v("HAM:B001:252", WtSeviyeB0252, "5m"),
    _v("HAM:B001:380", SmaMacdKesisimB0380, "4h"),
    _v("HAM:B001:381", EmaDizilimStochRsiB0381, "1h"),
    _v("HAM:B001:463", BbRsi1sdB0463, "4h"),
    _v("HAM:B001:466", RsiBbUstB0466, "5m"),
    _v("HAM:B001:468", BbRsiNaifB0468, "15m"),
    _v("HAM:B001:472", BbRsiCokluTfB0472, "5m"),
    _v("HAM:B001:473", BbRsi1sdB0473, "15m"),
    _v("HAM:B001:474", RsiBbTvB0474, "5m"),
    _v("HAM:B001:475", Bb3SigmaAltB0475, "1h"),
    _v("HAM:B001:476", BbRsiTemaIzB0476, "15m"),
    _v("HAM:B001:477", BbRsi1sdAltB0477, "1h"),
    _v("HAM:B001:478", Bb72Sigma2B0478, "1h"),
    _v("HAM:B001:482", Ema5BbOrtaB0482, "1d"),
    _v("HAM:B001:484", BbOrtaUstTrendB0484, "15m"),
    _v("HAM:B001:488", CmoBbUstB0488, "5m"),
    _v("HAM:B001:499", EmaBbRsiUcKolB0499, "1h"),
    _v("HAM:B001:501", Rsi8KesisimB0501, "5m"),
    _v("HAM:B001:502", BbAltCikisB0502, "15m"),
    _v("HAM:B001:503", BbAltCikisB0503, "1h"),
]

KODLANAMADI: list = []
