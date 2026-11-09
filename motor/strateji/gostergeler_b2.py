"""B2 grubu (gösterge/momentum/trend aileleri) için ek göstergeler ve küçük yardımcılar.

Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır.
`gostergeler.py` değiştirilmedi; burada yalnız o dosyada olmayanlar var.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


def yukari_kesis(seri: pd.Series, seviye) -> pd.Series:
    """seri, seviye'yi (sayı veya Series) aşağıdan yukarı kesti (bu mumda)."""
    return (seri > seviye) & (seri.shift(1) <= (seviye.shift(1) if isinstance(seviye, pd.Series) else seviye))


def asagi_kesis(seri: pd.Series, seviye) -> pd.Series:
    return (seri < seviye) & (seri.shift(1) >= (seviye.shift(1) if isinstance(seviye, pd.Series) else seviye))


def gecis(durum: pd.Series) -> pd.Series:
    """Bool durumun False/NaN -> True geçişi (aynı durum sürerken tekrar sinyal vermez)."""
    d = durum.fillna(False).astype(bool)
    return d & ~d.shift(1, fill_value=False)


def cci(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, periyot: int = 14) -> pd.Series:
    """Commodity Channel Index (Lambert): (TP - SMA(TP)) / (0.015 * ortalama mutlak sapma)."""
    tp = ((yuksek + dusuk + kapanis) / 3.0).to_numpy(dtype=float)
    n = len(tp)
    out = np.full(n, np.nan)
    if n >= periyot:
        w = sliding_window_view(tp, periyot)
        ort = w.mean(axis=1)
        md = np.abs(w - ort[:, None]).mean(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[periyot - 1:] = (tp[periyot - 1:] - ort) / (0.015 * md)
    out[~np.isfinite(out)] = np.nan
    return pd.Series(out, index=kapanis.index)


def fisher(yuksek: pd.Series, dusuk: pd.Series, periyot: int = 9) -> pd.DataFrame:
    """Ehlers Fisher Transform. fisher ve tetik (= bir önceki mumun fisher değeri). Nedensel özyinelemeli."""
    hl2 = ((yuksek + dusuk) / 2.0).to_numpy(dtype=float)
    mx = pd.Series(hl2).rolling(periyot, min_periods=periyot).max().to_numpy()
    mn = pd.Series(hl2).rolling(periyot, min_periods=periyot).min().to_numpy()
    n = len(hl2)
    out = np.full(n, np.nan)
    v = f = 0.0
    for i in range(n):
        if np.isnan(mx[i]):
            continue
        aralik = mx[i] - mn[i]
        ham = (hl2[i] - mn[i]) / aralik if aralik > 0 else 0.5
        v = min(max(0.66 * (ham - 0.5) + 0.67 * v, -0.999), 0.999)
        f = 0.5 * np.log((1.0 + v) / (1.0 - v)) + 0.5 * f
        out[i] = f
    s = pd.Series(out, index=yuksek.index)
    return pd.DataFrame({"fisher": s, "tetik": s.shift(1)})


def heikin_ashi(acilis: pd.Series, yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series,
                varyant: str = "standart") -> pd.DataFrame:
    """Heikin Ashi. varyant "standart": hClose=(O+H+L+C)/4; "graham": hClose=(O+H+L+2C)/5 (Graham, değiştirilmiş).
    hOpen = (önceki hOpen + önceki hClose)/2. Nedensel (ileri-yürüyen)."""
    o, h, l, c = (x.to_numpy(dtype=float) for x in (acilis, yuksek, dusuk, kapanis))
    hc = (o + h + l + 2.0 * c) / 5.0 if varyant == "graham" else (o + h + l + c) / 4.0
    n = len(c)
    ho = np.empty(n)
    if n:
        ho[0] = (o[0] + c[0]) / 2.0
        for i in range(1, n):
            ho[i] = (ho[i - 1] + hc[i - 1]) / 2.0
    hh = np.maximum(h, np.maximum(ho, hc))
    hl = np.minimum(l, np.minimum(ho, hc))
    return pd.DataFrame({"ha_acilis": ho, "ha_yuksek": hh, "ha_dusuk": hl, "ha_kapanis": hc}, index=kapanis.index)


def ichimoku(yuksek: pd.Series, dusuk: pd.Series, tenkan: int = 9, kijun: int = 26,
             senkou_b: int = 52, kaydirma: int = 26) -> pd.DataFrame:
    """Ichimoku. Bulut (span_a/span_b) t. mumda `kaydirma` mum ÖNCE hesaplananın t'ye ileri taşınmış halidir
    (nedensel; gelecek bulut kullanılmaz). Chikou kullanılmaz."""
    def orta(n):
        return (yuksek.rolling(n, min_periods=n).max() + dusuk.rolling(n, min_periods=n).min()) / 2.0
    t, k = orta(tenkan), orta(kijun)
    a = ((t + k) / 2.0).shift(kaydirma)
    b = orta(senkou_b).shift(kaydirma)
    return pd.DataFrame({"tenkan": t, "kijun": k, "span_a": a, "span_b": b,
                         "bulut_ust": np.maximum(a, b), "bulut_alt": np.minimum(a, b)})


def demarker(yuksek: pd.Series, dusuk: pd.Series, periyot: int = 14) -> pd.Series:
    """DeMarker (0..1)."""
    demax = (yuksek - yuksek.shift(1)).clip(lower=0.0)
    demin = (dusuk.shift(1) - dusuk).clip(lower=0.0)
    a = demax.rolling(periyot, min_periods=periyot).mean()
    b = demin.rolling(periyot, min_periods=periyot).mean()
    return a / (a + b)


def hacim_osilatoru(hacim: pd.Series, hizli: int = 5, yavas: int = 20) -> pd.Series:
    """Hacim Osilatörü (%): 100 * (EMA(hacim, hızlı) - EMA(hacim, yavaş)) / EMA(hacim, yavaş)."""
    h = hacim.astype(float)
    f = h.ewm(span=hizli, adjust=False, min_periods=hizli).mean()
    s = h.ewm(span=yavas, adjust=False, min_periods=yavas).mean()
    return 100.0 * (f - s) / s


def yuzdelik_sira(seri: pd.Series, pencere: int) -> pd.Series:
    """Her mumda son `pencere` değer (kendisi dahil) içinde değerin yüzdelik sırası (0..1). Pencere
    tam dolu ve NaN'sız değilse NaN. Nedensel."""
    a = seri.to_numpy(dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    if n >= pencere:
        w = sliding_window_view(a, pencere)
        son = w[:, -1]
        gecerli = ~np.isnan(w).any(axis=1)
        sira = (w <= son[:, None]).mean(axis=1)
        out[pencere - 1:] = np.where(gecerli, sira, np.nan)
    return pd.Series(out, index=seri.index)


def swing_stop(yuksek, dusuk, kapanis, atr, n: int, tampon: float, maks: float):
    """Son n mumun dibi/zirvesi -/+ tampon*ATR; risk en çok `maks` ATR (stop_l, stop_s)."""
    alt = dusuk.rolling(n, min_periods=n).min() - tampon * atr
    ust = yuksek.rolling(n, min_periods=n).max() + tampon * atr
    return (np.maximum(alt, kapanis - maks * atr), np.minimum(ust, kapanis + maks * atr))


def hedef_r_ile(kapanis, stop_l, stop_s, r: float):
    """r > 0 ise (kapanış +/- r*risk) hedefleri, değilse (None, None)."""
    if not r or r <= 0:
        return None, None
    return kapanis + r * (kapanis - stop_l), kapanis - r * (stop_s - kapanis)
