"""D2 grubu (dış kaynaklı TradingView / freqtrade) stratejileri için ek göstergeler.

Hepsi NEDENSELDİR: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır. Pine'daki `request.security`,
`[1]` ve tüm-veri normalizasyonu gibi gelecek sızdırabilecek yapılar burada kullanılmaz; üst zaman dilimi gerektiğinde
`motor.strateji.htf.ust_zaman` kullanılır. Paylaşılan dosyalara dokunulmaz.
"""
import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g


# ------------------------------------------------------------------ küçük yardımcılar
def hlc3(y: pd.Series, d: pd.Series, k: pd.Series) -> pd.Series:
    return (y + d + k) / 3.0


def kesis_yukari(a: pd.Series, b) -> pd.Series:
    """Pine ta.crossover(a, b): bu mumda a > b ve önceki mumda a <= b."""
    bs = b.shift(1) if isinstance(b, pd.Series) else b
    return (a > b) & (a.shift(1) <= bs)


def kesis_asagi(a: pd.Series, b) -> pd.Series:
    bs = b.shift(1) if isinstance(b, pd.Series) else b
    return (a < b) & (a.shift(1) >= bs)


def mum_sayaci(kosul: pd.Series) -> pd.Series:
    """Pine ta.barssince: koşulun en son True olduğu mumdan beri geçen mum (o mumda 0); hiç olmadıysa NaN."""
    k = kosul.fillna(False).to_numpy(dtype=bool)
    out = np.full(len(k), np.nan)
    son = -1
    for i in range(len(k)):
        if k[i]:
            son = i
        if son >= 0:
            out[i] = i - son
    return pd.Series(out, index=kosul.index)


def pine_stdev(seri: pd.Series, n: int) -> pd.Series:
    """Pine ta.stdev: popülasyon standart sapması (ddof=0)."""
    return seri.rolling(n, min_periods=n).std(ddof=0)


def pine_stoch(kaynak: pd.Series, yuksek: pd.Series, dusuk: pd.Series, n: int) -> pd.Series:
    """Pine ta.stoch: 100*(kaynak - en düşük)/(en yüksek - en düşük)."""
    hh = yuksek.rolling(n, min_periods=n).max()
    ll = dusuk.rolling(n, min_periods=n).min()
    return 100.0 * (kaynak - ll) / (hh - ll).replace(0.0, np.nan)


def stoch_rsi(kapanis: pd.Series, rsi_n: int = 14, stoch_n: int = 14, k_n: int = 3, d_n: int = 3) -> pd.DataFrame:
    r = g.rsi(kapanis, rsi_n)
    k = g.sma(pine_stoch(r, r, r, stoch_n), k_n)
    return pd.DataFrame({"k": k, "d": g.sma(k, d_n)})


def pine_percentrank(seri: pd.Series, n: int) -> pd.Series:
    """Pine ta.percentrank: ÖNCEKİ n değerden (şimdiki hariç) şimdikine eşit/küçük olanların yüzdesi."""
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) > n:
        w = sliding_window_view(a, n + 1)          # son eleman = şimdiki
        gecmis, simdi = w[:, :-1], w[:, -1]
        gecerli = ~np.isnan(w).any(axis=1)
        sira = 100.0 * (gecmis <= simdi[:, None]).sum(axis=1) / n
        out[n:] = np.where(gecerli, sira, np.nan)
    return pd.Series(out, index=seri.index)


def _evrisim(seri: pd.Series, agirlik: np.ndarray) -> pd.Series:
    """Pencere sonlu ağırlıklı toplam (NaN içeren pencere -> NaN). agirlik[k] = pencerenin k. (eski->yeni) elemanı."""
    n = len(agirlik)
    a = seri.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        nan = np.isnan(a)
        z = np.where(nan, 0.0, a)
        yaz = np.convolve(z, agirlik[::-1], mode="valid")
        bozuk = np.convolve(nan.astype(float), np.ones(n), mode="valid") > 0
        out[n - 1:] = np.where(bozuk, np.nan, yaz)
    return pd.Series(out, index=seri.index)


def wma(seri: pd.Series, n: int) -> pd.Series:
    w = np.arange(1, n + 1, dtype=float)
    return _evrisim(seri, w) / w.sum()


def hma(seri: pd.Series, n: int) -> pd.Series:
    yari = max(int(n / 2), 1)
    kok = max(int(round(math.sqrt(n))), 1)
    return wma(2.0 * wma(seri, yari) - wma(seri, n), kok)


def linreg(seri: pd.Series, n: int) -> pd.Series:
    """Pine ta.linreg(seri, n, 0): son n değere en küçük kareler doğrusu, doğrunun SON noktadaki değeri."""
    x = np.arange(n, dtype=float)
    xo = x.mean()
    sxx = ((x - xo) ** 2).sum()
    toplam = _evrisim(seri, np.ones(n))
    yo = toplam / n
    sxy = _evrisim(seri, x)
    egim = (sxy - xo * toplam) / sxx
    return yo + egim * (n - 1 - xo)


def tema(seri: pd.Series, n: int) -> pd.Series:
    e1 = g.ema(seri, n)
    e2 = e1.ewm(span=n, adjust=False, min_periods=n).mean()
    e3 = e2.ewm(span=n, adjust=False, min_periods=n).mean()
    return 3.0 * e1 - 3.0 * e2 + e3


def pine_rma(seri: pd.Series, n: int) -> pd.Series:
    return seri.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


# ------------------------------------------------------------------ pivotlar
def pivot_yuksek(yuksek: pd.Series, n: int) -> pd.Series:
    """Pine ta.pivothigh(high, n, n): t. mumda (n mum gecikmeyle) t-n. mum, solundaki ve sağındaki n mumdan
    yüksek/eşitse onun değeri; değilse NaN. Nedensel (onay gecikmeli)."""
    orta = yuksek.shift(n)
    tepe = yuksek.rolling(2 * n + 1, min_periods=2 * n + 1).max()
    return orta.where(orta == tepe)


def pivot_dusuk(dusuk: pd.Series, n: int) -> pd.Series:
    orta = dusuk.shift(n)
    dip = dusuk.rolling(2 * n + 1, min_periods=2 * n + 1).min()
    return orta.where(orta == dip)


def yapi_trendi(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, n: int) -> pd.Series:
    """Yapı trendi: kapanış son onaylı pivot tepeyi aşarsa +1, son onaylı pivot dibin altına inerse -1 (aksi halde
    önceki). Pine `f_structureTrend`."""
    ph, pl = pivot_yuksek(yuksek, n).to_numpy(), pivot_dusuk(dusuk, n).to_numpy()
    c = kapanis.to_numpy()
    out = np.zeros(len(c), dtype="int64")
    sh = sl = np.nan
    d = 0
    for i in range(len(c)):
        if not np.isnan(ph[i]):
            sh = ph[i]
        if not np.isnan(pl[i]):
            sl = pl[i]
        if not np.isnan(sh) and c[i] > sh:
            d = 1
        if not np.isnan(sl) and c[i] < sl:
            d = -1
        out[i] = d
    return pd.Series(out, index=kapanis.index)


# ------------------------------------------------------------------ Gauss filtresi (Ehlers / DonovanWall)
def gauss_filtre(seri: pd.Series, per: int, kutup: int) -> pd.Series:
    """`kutup` kutuplu Gauss alçak geçiren filtre (TradingView "Gaussian Channel", f_filt9x). Özyinelemeli;
    Pine nz() gibi geçmişi 0 ile başlatır, bu yüzden ilk ~3*per mum ısınmadır (kullanılmamalı)."""
    N = int(kutup)
    beta = (1 - math.cos(2 * math.pi / per)) / (1.414 ** (2.0 / N) - 1)
    alfa = -beta + math.sqrt(beta * beta + 2 * beta)
    x = 1 - alfa
    kat = [math.comb(N, k) * (-1) ** (k + 1) * x ** k for k in range(1, N + 1)]
    a = np.nan_to_num(seri.to_numpy(dtype=float))
    out = np.zeros(len(a))
    c0 = alfa ** N
    for i in range(len(a)):
        f = c0 * a[i]
        for k in range(1, N + 1):
            if i - k >= 0:
                f += kat[k - 1] * out[i - k]
        out[i] = f
    return pd.Series(out, index=seri.index)


def gauss_kanal(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, per: int = 144, kutup: int = 4,
                carpan: float = 1.414) -> pd.DataFrame:
    """filt (hlc3 üzerinde), ust/alt bant = filt -/+ süzülmüş gerçek aralık*carpan."""
    f = gauss_filtre(hlc3(yuksek, dusuk, kapanis), per, kutup)
    ftr = gauss_filtre(g.gercek_aralik(yuksek, dusuk, kapanis), per, kutup)
    return pd.DataFrame({"filt": f, "ust": f + ftr * carpan, "alt": f - ftr * carpan})


# ------------------------------------------------------------------ sıkışma momentumu / T3
def sikisma_momentum(yuksek, dusuk, kapanis, bb_n=20, bb_carpan=1.5, kc_n=20, kc_carpan=1.5) -> pd.DataFrame:
    """LazyBear Squeeze Momentum. Bollinger sapması burada da `bb_carpan` ile çarpılır. sqz_on: BB, KC içinde;
    sqz_off: BB, KC'yi aşıyor. val: linreg(kapanış - (orta(HH,LL) + SMA)/2)."""
    taban = g.sma(kapanis, bb_n)
    sap = bb_carpan * pine_stdev(kapanis, bb_n)
    ub, lb = taban + sap, taban - sap
    ma = g.sma(kapanis, kc_n)
    aralik = g.sma(g.gercek_aralik(yuksek, dusuk, kapanis), kc_n)
    uk, lk = ma + aralik * kc_carpan, ma - aralik * kc_carpan
    hh = yuksek.rolling(kc_n, min_periods=kc_n).max()
    ll = dusuk.rolling(kc_n, min_periods=kc_n).min()
    val = linreg(kapanis - ((hh + ll) / 2.0 + ma) / 2.0, kc_n)
    return pd.DataFrame({"sqz_on": (lb > lk) & (ub < uk), "sqz_off": (lb < lk) & (ub > uk), "val": val})


def t3_rsi_uyarlamali(kapanis: pd.Series, rsi_n=14, min_len=5, max_len=50, v=0.7) -> pd.Series:
    """RSI'ye göre uzunluğu değişen T3 (altı ardışık EMA, her mumda alfa=2/(uzunluk+1))."""
    r = g.rsi(kapanis, rsi_n).to_numpy()
    c = kapanis.to_numpy(dtype=float)
    ln = np.round(min_len + (max_len - min_len) * (1 - r / 100.0))
    c1, c2 = -v ** 3, 3 * v ** 2 + 3 * v ** 3
    c3, c4 = -6 * v ** 2 - 3 * v - 3 * v ** 3, 1 + 3 * v + v ** 3 + 3 * v ** 2
    n = len(c)
    out = np.full(n, np.nan)
    e = [None] * 6
    for i in range(n):
        if np.isnan(ln[i]):
            continue
        al = 2.0 / (ln[i] + 1.0)
        s = c[i]
        for j in range(6):
            e[j] = s if e[j] is None else al * s + (1 - al) * e[j]
            s = e[j]
        out[i] = c1 * e[5] + c2 * e[4] + c3 * e[3] + c4 * e[2]
    return pd.Series(out, index=kapanis.index)


# ------------------------------------------------------------------ VAR / OTT
def var_ma(src: pd.Series, uzunluk: int, cmo_n: int = 9) -> pd.Series:
    """Chande değişken endeksli dinamik ortalama (VIDYA, 'VAR'). Pine nz() gibi 0 ile başlar (ısınma gerekir)."""
    s = src.to_numpy(dtype=float)
    fark = np.r_[np.nan, np.diff(s)]
    yuk = pd.Series(np.where(fark > 0, fark, 0.0)).rolling(cmo_n, min_periods=1).sum().to_numpy()
    asg = pd.Series(np.where(fark < 0, -fark, 0.0)).rolling(cmo_n, min_periods=1).sum().to_numpy()
    toplam = yuk + asg
    cmo = np.where(toplam == 0, 0.0, (yuk - asg) / np.where(toplam == 0, 1.0, toplam))
    al = 2.0 / (uzunluk + 1.0)
    out = np.zeros(len(s))
    onceki = 0.0
    for i in range(len(s)):
        a = al * abs(cmo[i])
        val = np.nan_to_num(a * s[i]) + (1 - a) * onceki
        out[i] = val
        onceki = val
    return pd.Series(out, index=src.index)


def ott(src: pd.Series, uzunluk: int = 3, yuzde: float = 0.618) -> pd.Series:
    """Optimized Trend Tracker çizgisi (OTT), `src` üzerinde. Pine: OTT, MAvg ve MT'den hesaplanır."""
    mav = var_ma(src, uzunluk).to_numpy()
    fark = mav * yuzde * 0.01
    n = len(mav)
    ls = np.zeros(n)
    ss = np.zeros(n)
    d = np.ones(n, dtype=int)
    mt = np.zeros(n)
    out = np.zeros(n)
    for i in range(n):
        l0, s0 = mav[i] - fark[i], mav[i] + fark[i]
        lp = ls[i - 1] if i else l0
        sp = ss[i - 1] if i else s0
        ls[i] = max(l0, lp) if mav[i] > lp else l0
        ss[i] = min(s0, sp) if mav[i] < sp else s0
        dp = d[i - 1] if i else 1
        d[i] = 1 if (dp == -1 and mav[i] > sp) else (-1 if (dp == 1 and mav[i] < lp) else dp)
        mt[i] = ls[i] if d[i] == 1 else ss[i]
        out[i] = mt[i] * (200 + yuzde) / 200 if mav[i] > mt[i] else mt[i] * (200 - yuzde) / 200
    return pd.Series(out, index=src.index)


# ------------------------------------------------------------------ hafta / seans yardımcıları
def hafta_kimligi(index: pd.DatetimeIndex) -> np.ndarray:
    """Pazartesi 00:00 UTC'de başlayan haftanın kimliği (tam sayı)."""
    gun = index.floor("D")
    if gun.tz is not None:
        gun = gun.tz_localize(None)
    pzt = gun - pd.to_timedelta(index.dayofweek, unit="D")
    return pzt.values.astype("datetime64[D]").astype("int64")


def hafta_son_mumu(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun kapanışı bir sonraki haftaya denk geliyorsa True. Mum süresi yalnız GEÇMİŞTEN kestirilir (lookahead yok)."""
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kapanis = index + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    return (hafta_kimligi(kapanis) != hafta_kimligi(index)) & gecerli


def yonlu_cerceve(sig: pd.DataFrame, cikis_long, cikis_short) -> pd.DataFrame:
    """Sinyal çerçevesine yönlü çıkış sütunları ekler (long yalnız cikis_long ile, short yalnız cikis_short ile)."""
    s = sig.copy()
    s["cikis_long"] = pd.Series(cikis_long, index=s.index).fillna(False).astype(bool)
    s["cikis_short"] = pd.Series(cikis_short, index=s.index).fillna(False).astype(bool)
    return s


def atr_stoplari(mumlar: pd.DataFrame, periyot: int, carpan: float):
    """(atr, stop_long, stop_short): kapanış -/+ carpan*ATR."""
    a = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], periyot)
    k = mumlar["kapanis"]
    return a, k - carpan * a, k + carpan * a
