"""Teknik göstergeler — saf pandas/numpy. Hepsi nedensel (sadece geçmişe bakar)."""
import numpy as np
import pandas as pd


def sma(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.rolling(periyot, min_periods=periyot).mean()


def ema(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.ewm(span=periyot, adjust=False, min_periods=periyot).mean()


def _wilder(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.ewm(alpha=1.0 / periyot, adjust=False, min_periods=periyot).mean()


def rsi(kapanis: pd.Series, periyot: int = 14) -> pd.Series:
    fark = kapanis.diff()
    kazanc = fark.clip(lower=0.0)
    kayip = (-fark).clip(lower=0.0)
    rs = _wilder(kazanc, periyot) / _wilder(kayip, periyot)
    return 100.0 - 100.0 / (1.0 + rs)


def gercek_aralik(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series) -> pd.Series:
    onceki = kapanis.shift(1)
    parcalar = pd.concat([yuksek - dusuk, (yuksek - onceki).abs(), (dusuk - onceki).abs()], axis=1)
    return parcalar.max(axis=1)


def atr(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, periyot: int = 14) -> pd.Series:
    return _wilder(gercek_aralik(yuksek, dusuk, kapanis), periyot)


def bollinger(kapanis: pd.Series, periyot: int = 20, sapma: float = 2.0) -> pd.DataFrame:
    orta = sma(kapanis, periyot)
    std = kapanis.rolling(periyot, min_periods=periyot).std(ddof=0)
    return pd.DataFrame({"orta": orta, "ust": orta + sapma * std, "alt": orta - sapma * std})


def macd(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, sinyal: int = 9) -> pd.DataFrame:
    m = ema(kapanis, hizli) - ema(kapanis, yavas)
    s = m.ewm(span=sinyal, adjust=False, min_periods=sinyal).mean()
    return pd.DataFrame({"macd": m, "sinyal": s, "histogram": m - s})


def adx(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, periyot: int = 14) -> pd.DataFrame:
    yukari = yuksek.diff()
    asagi = -dusuk.diff()
    arti_dm = pd.Series(np.where((yukari > asagi) & (yukari > 0), yukari, 0.0), index=kapanis.index)
    eksi_dm = pd.Series(np.where((asagi > yukari) & (asagi > 0), asagi, 0.0), index=kapanis.index)
    a = atr(yuksek, dusuk, kapanis, periyot)
    arti_di = 100.0 * _wilder(arti_dm, periyot) / a
    eksi_di = 100.0 * _wilder(eksi_dm, periyot) / a
    dx = 100.0 * (arti_di - eksi_di).abs() / (arti_di + eksi_di)
    return pd.DataFrame({"adx": _wilder(dx, periyot), "arti_di": arti_di, "eksi_di": eksi_di})


def stokastik(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series,
              k_periyot: int = 14, d_periyot: int = 3) -> pd.DataFrame:
    en_yuksek = yuksek.rolling(k_periyot, min_periods=k_periyot).max()
    en_dusuk = dusuk.rolling(k_periyot, min_periods=k_periyot).min()
    k = 100.0 * (kapanis - en_dusuk) / (en_yuksek - en_dusuk)
    return pd.DataFrame({"k": k, "d": sma(k, d_periyot)})


def vwap_seans(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, hacim: pd.Series,
               seans) -> pd.DataFrame:
    """Seans (ör. UTC gün) içinde kümülatif VWAP ve hacim ağırlıklı standart sapma.

    seans: mumlarla aynı uzunlukta seans kimliği dizisi (aynı değer = aynı seans). Her seansta sıfırlanır.
    t. satır yalnız seans başından t. mum kapanışına kadarki mumları kullanır (nedensel).
    Fiyat = tipik fiyat (H+L+C)/3. Dönen: vwap, sd, mum_no (seansın kaçıncı mumu, 1'den).
    """
    tp = (yuksek + dusuk + kapanis) / 3.0
    anahtar = np.asarray(seans)
    v = hacim.groupby(anahtar).cumsum().replace(0.0, np.nan)
    pv = (tp * hacim).groupby(anahtar).cumsum()
    p2 = (tp * tp * hacim).groupby(anahtar).cumsum()
    vwap = pv / v
    sd = np.sqrt((p2 / v - vwap ** 2).clip(lower=0.0))
    mum_no = kapanis.groupby(anahtar).cumcount() + 1
    return pd.DataFrame({"vwap": vwap, "sd": sd, "mum_no": mum_no})


def supertrend(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series,
               atr_periyot: int = 10, carpan: float = 3.0) -> pd.DataFrame:
    """Supertrend. yon: +1 çizgi fiyatın altında (yükseliş), -1 üstünde, 0 ATR hazır değil.
    cizgi: o mumun kapanışında geçerli çizgi (stop olarak kullanılır). Nedensel (ileri-yürüyen döngü)."""
    a = atr(yuksek, dusuk, kapanis, atr_periyot).to_numpy()
    h, l, c = yuksek.to_numpy(), dusuk.to_numpy(), kapanis.to_numpy()
    n = len(c)
    yon = np.zeros(n, dtype="int64")
    cizgi = np.full(n, np.nan)
    ub = lb = np.nan
    d = 0
    for i in range(n):
        if np.isnan(a[i]):
            continue
        hl2 = (h[i] + l[i]) / 2.0
        bu, bl = hl2 + carpan * a[i], hl2 - carpan * a[i]
        if d == 0:
            ub, lb, d = bu, bl, (1 if c[i] >= hl2 else -1)
        else:
            ub = bu if (bu < ub or c[i - 1] > ub) else ub
            lb = bl if (bl > lb or c[i - 1] < lb) else lb
            if d == 1 and c[i] < lb:
                d = -1
            elif d == -1 and c[i] > ub:
                d = 1
        yon[i] = d
        cizgi[i] = lb if d == 1 else ub
    return pd.DataFrame({"cizgi": cizgi, "yon": yon}, index=kapanis.index)


def psar(yuksek: pd.Series, dusuk: pd.Series, adim: float = 0.02, maks: float = 0.2) -> pd.DataFrame:
    """Parabolik SAR. yon: o mum kapanışındaki trend (+1/-1; ilk mum 0).
    sar: BİR SONRAKİ mum için SAR değeri (mum kapanışında bilinir; stop olarak kullanılır). Nedensel."""
    h, l = yuksek.to_numpy(), dusuk.to_numpy()
    n = len(h)
    yon = np.zeros(n, dtype="int64")
    sar_out = np.full(n, np.nan)
    if n < 2:
        return pd.DataFrame({"sar": sar_out, "yon": yon}, index=yuksek.index)
    trend = 1
    sar, ep, af = l[0], h[0], adim
    for i in range(1, n):
        if trend == 1:
            if l[i] < sar:
                trend, sar, ep, af = -1, ep, l[i], adim
            else:
                if h[i] > ep:
                    ep, af = h[i], min(af + adim, maks)
                sar = min(sar + af * (ep - sar), l[i], l[i - 1])
        else:
            if h[i] > sar:
                trend, sar, ep, af = 1, ep, h[i], adim
            else:
                if l[i] < ep:
                    ep, af = l[i], min(af + adim, maks)
                sar = max(sar + af * (ep - sar), h[i], h[i - 1])
        yon[i] = trend
        sar_out[i] = sar
    return pd.DataFrame({"sar": sar_out, "yon": yon}, index=yuksek.index)
