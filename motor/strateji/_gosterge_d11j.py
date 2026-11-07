"""d11j gösterge yardımcıları (saf pandas/numpy, NEDENSEL: t. değer yalnız <=t. mumlara bağlıdır).

Mevcut sınıflara EK SEÇENEK olarak bağlanan göstergeler; kaynak repolardaki kod kopyalanmadı, formüller kamuya açık
tanımlardan (Ehlers, Schaff, Klinger, Ultimate Oscillator, TSI, TRIX, MFI, Chandelier/NRTR) sıfırdan yazıldı.
Her gösterge ısınma döneminde NaN verir (özyinelemeli olanlar `isim_isinma` kadar sonra güvenilir sayılır).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b


# ---------------------------------------------------------------- momentum / hacim osilatörleri
def trix(kap: pd.Series, n: int = 14) -> pd.Series:
    """TRIX: üçlü EMA'nın yüzde değişimi (x100)."""
    e = kap.ewm(span=n, adjust=False, min_periods=n).mean()
    e = e.ewm(span=n, adjust=False, min_periods=n).mean()
    e = e.ewm(span=n, adjust=False, min_periods=n).mean()
    return 100.0 * e.pct_change(fill_method=None)


def tsi(kap: pd.Series, uzun: int = 25, kisa: int = 13) -> pd.Series:
    """True Strength Index (-100..100): çift EMA'lı momentum / çift EMA'lı mutlak momentum."""
    m = kap.diff()
    pay = m.ewm(span=uzun, adjust=False, min_periods=uzun).mean().ewm(span=kisa, adjust=False, min_periods=kisa).mean()
    payda = m.abs().ewm(span=uzun, adjust=False, min_periods=uzun).mean().ewm(span=kisa, adjust=False, min_periods=kisa).mean()
    return 100.0 * pay / payda.where(payda != 0)


def ultimate_osc(y: pd.Series, d: pd.Series, k: pd.Series, a: int = 7, b_: int = 14, c: int = 28) -> pd.Series:
    """Ultimate Oscillator (Williams), 0-100: üç periyodun alım baskısı / gerçek aralık oranı, ağırlık 4:2:1."""
    onc = k.shift(1)
    alt = pd.concat([d, onc], axis=1).min(axis=1)
    ust = pd.concat([y, onc], axis=1).max(axis=1)
    bp, tr = k - alt, ust - alt

    def oran(n):
        return bp.rolling(n, min_periods=n).sum() / tr.rolling(n, min_periods=n).sum().where(lambda x: x != 0)
    return 100.0 * (4.0 * oran(a) + 2.0 * oran(b_) + oran(c)) / 7.0


def stc(kap: pd.Series, hizli: int = 23, yavas: int = 50, dongu: int = 10, yumusat: float = 0.5) -> pd.Series:
    """Schaff Trend Cycle (0-100): MACD çizgisine iki kez ardışık yumuşatılmış stokastik uygulanır."""
    m = (kap.ewm(span=hizli, adjust=False, min_periods=hizli).mean()
         - kap.ewm(span=yavas, adjust=False, min_periods=yavas).mean())

    def stok(x):
        alt, ust = x.rolling(dongu, min_periods=dongu).min(), x.rolling(dongu, min_periods=dongu).max()
        return 100.0 * (x - alt) / (ust - alt).where(lambda v: v > 0)

    def yum(x):
        v = x.to_numpy(dtype=float)
        out = np.full(len(v), np.nan)
        onc = np.nan
        for i, xi in enumerate(v):
            if np.isnan(xi):
                continue
            onc = xi if np.isnan(onc) else onc + yumusat * (xi - onc)
            out[i] = onc
        return pd.Series(out, index=x.index)

    return yum(stok(yum(stok(m))))


def mfi(y: pd.Series, d: pd.Series, k: pd.Series, h: pd.Series, n: int = 14) -> pd.Series:
    """Money Flow Index (0-100): tipik fiyat x hacim akışının pozitif/negatif oranı."""
    tp = (y + d + k) / 3.0
    akis = tp * h
    art = akis.where(tp > tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    eks = akis.where(tp < tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    return 100.0 - 100.0 / (1.0 + art / eks.where(eks != 0))


def williams_r(y: pd.Series, d: pd.Series, k: pd.Series, n: int = 14) -> pd.Series:
    """Williams %R, 0 ile -100 arası."""
    ust, alt = y.rolling(n, min_periods=n).max(), d.rolling(n, min_periods=n).min()
    return -100.0 * (ust - k) / (ust - alt).where(lambda x: x > 0)


def obv(k: pd.Series, h: pd.Series) -> pd.Series:
    return (np.sign(k.diff()).fillna(0.0) * h).cumsum()


def birikim_dagitim(y: pd.Series, d: pd.Series, k: pd.Series, h: pd.Series) -> pd.Series:
    """Accumulation/Distribution çizgisi: kapanış konumu çarpanı x hacim birikimi."""
    aralik = (y - d).where(lambda x: x > 0)
    cl = ((k - d) - (y - k)) / aralik
    return (cl.fillna(0.0) * h).cumsum()


def pvt(k: pd.Series, h: pd.Series) -> pd.Series:
    """Price Volume Trend: yüzde getiri x hacim birikimi."""
    return (k.pct_change(fill_method=None).fillna(0.0) * h).cumsum()


def kvo(y: pd.Series, d: pd.Series, k: pd.Series, h: pd.Series, hizli: int = 34, yavas: int = 55) -> pd.Series:
    """Klinger Volume Oscillator: yön işaretli hacim gücünün iki EMA farkı."""
    hlc = (y + d + k).to_numpy(dtype=float)
    dm = (y - d).to_numpy(dtype=float)
    hv = h.to_numpy(dtype=float)
    n = len(hlc)
    vf = np.full(n, np.nan)
    cm = np.nan
    trend_onc = 0
    dm_onc = np.nan
    for i in range(1, n):
        t = 1 if hlc[i] > hlc[i - 1] else -1
        cm = (dm[i] if np.isnan(cm) else (cm + dm[i] if t == trend_onc else dm_onc + dm[i]))
        trend_onc, dm_onc = t, dm[i]
        if cm > 0:
            vf[i] = hv[i] * abs(2.0 * dm[i] / cm - 1.0) * t * 100.0
    vf = pd.Series(vf, index=k.index)
    return (vf.ewm(span=hizli, adjust=False, min_periods=hizli).mean()
            - vf.ewm(span=yavas, adjust=False, min_periods=yavas).mean())


def emv(y: pd.Series, d: pd.Series, h: pd.Series, n: int = 14) -> pd.Series:
    """Ease of Movement: orta fiyat değişimi / (hacim/aralık) kutu oranı, SMA(n). Ölçek göreli (yalnız kesişimde kullanılır)."""
    dm = (y + d) / 2.0 - (y.shift(1) + d.shift(1)) / 2.0
    kutu = (h / (y - d).where(lambda x: x > 0)).where(lambda x: x > 0)
    return (dm / kutu).rolling(n, min_periods=n).mean()


def _hp2(kap: np.ndarray, periyot: int) -> np.ndarray:
    """Ehlers 2 kutuplu yüksek geçiren süzgeç."""
    a = math.radians(0.707 * 360.0 / periyot)
    a1 = (math.cos(a) + math.sin(a) - 1.0) / math.cos(a)
    c0, c1, c2 = (1.0 - a1 / 2.0) ** 2, 2.0 * (1.0 - a1), -((1.0 - a1) ** 2)
    hp = np.zeros(len(kap))
    for i in range(2, len(kap)):
        hp[i] = c0 * (kap[i] - 2.0 * kap[i - 1] + kap[i - 2]) + c1 * hp[i - 1] + c2 * hp[i - 2]
    return hp


def decycler_osc(kap: pd.Series, kisa: int = 100, uzun: int = 125) -> pd.Series:
    """Ehlers Decycler Osilatörü (varsayım): 100*(HP(kisa) - HP(uzun)) / fiyat; ilk 2*uzun mum NaN."""
    v = kap.to_numpy(dtype=float)
    o = 100.0 * (_hp2(v, kisa) - _hp2(v, uzun)) / v
    o[: 2 * uzun] = np.nan
    return pd.Series(o, index=kap.index)


# ---------------------------------------------------------------- MA türleri
def wma(kap: pd.Series, n: int) -> pd.Series:
    w = np.arange(1, n + 1, dtype=float)
    return kap.rolling(n, min_periods=n).apply(lambda x: float(np.dot(x, w) / w.sum()), raw=True)


def hma(kap: pd.Series, n: int) -> pd.Series:
    yarim, kok = max(n // 2, 1), max(int(round(math.sqrt(n))), 1)
    return wma(2.0 * wma(kap, yarim) - wma(kap, n), kok)


def alma(kap: pd.Series, n: int = 9, ofset: float = 0.85, sigma: float = 6.0) -> pd.Series:
    """Arnaud Legoux MA: Gauss ağırlıklı, ağırlık tepesi pencerenin `ofset` noktasında."""
    m, s = ofset * (n - 1), n / sigma
    w = np.exp(-((np.arange(n) - m) ** 2) / (2.0 * s * s))
    w = w / w.sum()
    return kap.rolling(n, min_periods=n).apply(lambda x: float(np.dot(x, w)), raw=True)


def cma(kap: pd.Series, n: int = 35) -> pd.Series:
    """Düzeltilmiş (varyans ayarlı) MA: SMA'ya varyans oranı kadar hızla yaklaşır, aksi halde önceki değerde kalır."""
    sm = g.sma(kap, n).to_numpy(dtype=float)
    var1 = kap.rolling(n, min_periods=n).var(ddof=0).to_numpy(dtype=float)
    out = np.full(len(sm), np.nan)
    onc = np.nan
    for i in range(len(sm)):
        if np.isnan(sm[i]) or np.isnan(var1[i]):
            continue
        if np.isnan(onc):
            onc = sm[i]
        else:
            v2 = (onc - sm[i]) ** 2
            kat = 0.0 if (v2 < var1[i] or v2 == 0.0) else 1.0 - var1[i] / v2
            onc = onc + kat * (sm[i] - onc)
        out[i] = onc
    return pd.Series(out, index=kap.index)


def mama_fama(fiyat: pd.Series, hizli: float = 0.5, yavas: float = 0.05) -> tuple[pd.Series, pd.Series]:
    """Ehlers MAMA/FAMA: Hilbert dönüşümü ile ölçülen faz değişimine göre uyarlanan alfa. Ilk ~40 mum güvenilmez."""
    p = fiyat.to_numpy(dtype=float)
    n = len(p)
    sm, de, q1, i1 = (np.zeros(n) for _ in range(4))
    i2, q2, re, im, per, sper, faz = (np.zeros(n) for _ in range(7))
    mama, fama = np.full(n, np.nan), np.full(n, np.nan)

    def hil(x, i, per_onc):
        return (0.0962 * x[i] + 0.5769 * x[i - 2] - 0.5769 * x[i - 4] - 0.0962 * x[i - 6]) * (0.075 * per_onc + 0.54)

    for i in range(6, n):
        sm[i] = (4 * p[i] + 3 * p[i - 1] + 2 * p[i - 2] + p[i - 3]) / 10.0
        de[i] = hil(sm, i, per[i - 1])
        q1[i] = hil(de, i, per[i - 1])
        i1[i] = de[i - 3]
        ji, jq = hil(i1, i, per[i - 1]), hil(q1, i, per[i - 1])
        i2c, q2c = i1[i] - jq, q1[i] + ji
        i2[i] = 0.2 * i2c + 0.8 * i2[i - 1]
        q2[i] = 0.2 * q2c + 0.8 * q2[i - 1]
        rec = i2[i] * i2[i - 1] + q2[i] * q2[i - 1]
        imc = i2[i] * q2[i - 1] - q2[i] * i2[i - 1]
        re[i] = 0.2 * rec + 0.8 * re[i - 1]
        im[i] = 0.2 * imc + 0.8 * im[i - 1]
        pr = per[i - 1]
        if im[i] != 0.0 and re[i] != 0.0:
            pr = 360.0 / math.degrees(math.atan(im[i] / re[i]))
        pr = min(pr, 1.5 * per[i - 1]) if per[i - 1] > 0 else pr
        pr = max(pr, 0.67 * per[i - 1])
        pr = min(max(pr, 6.0), 50.0)
        per[i] = 0.2 * pr + 0.8 * per[i - 1]
        sper[i] = 0.33 * per[i] + 0.67 * sper[i - 1]
        faz[i] = math.degrees(math.atan(q1[i] / i1[i])) if i1[i] != 0.0 else faz[i - 1]
        dfaz = max(faz[i - 1] - faz[i], 1.0)
        alfa = min(max(hizli / dfaz, yavas), hizli)
        mama[i] = alfa * p[i] + (1 - alfa) * (p[i] if np.isnan(mama[i - 1]) else mama[i - 1])
        fama[i] = 0.5 * alfa * mama[i] + (1 - 0.5 * alfa) * (mama[i] if np.isnan(fama[i - 1]) else fama[i - 1])
    mama[:40], fama[:40] = np.nan, np.nan
    return pd.Series(mama, index=fiyat.index), pd.Series(fama, index=fiyat.index)


def itrend(fiyat: pd.Series, alfa: float = 0.07) -> tuple[pd.Series, pd.Series]:
    """Ehlers Anlık Trend çizgisi ve tetik çizgisi (2*trend - trend[2])."""
    p = fiyat.to_numpy(dtype=float)
    n = len(p)
    it = np.full(n, np.nan)
    for i in range(n):
        if i < 7:
            it[i] = (p[i] + 2 * p[i - 1] + p[i - 2]) / 4.0 if i >= 2 else p[i]
        else:
            it[i] = ((alfa - alfa ** 2 / 4) * p[i] + 0.5 * alfa ** 2 * p[i - 1] - (alfa - 0.75 * alfa ** 2) * p[i - 2]
                     + 2 * (1 - alfa) * it[i - 1] - (1 - alfa) ** 2 * it[i - 2])
    it[:12] = np.nan
    s = pd.Series(it, index=fiyat.index)
    return s, 2.0 * s - s.shift(2)


def ma_turu(kap: pd.Series, tip: str, n: int) -> pd.Series:
    """Tek periyotlu MA türleri (ema/sma haricindekiler)."""
    if tip == "wma":
        return wma(kap, n)
    if tip == "hma":
        return hma(kap, n)
    if tip == "alma":
        return alma(kap, n)
    if tip == "cma":
        return cma(kap, n)
    raise ValueError(f"Bilinmeyen ma_tipi: {tip}")


# ---------------------------------------------------------------- izleyen-çizgi dönüş sistemleri
def _donus_sonuc(idx, yon, cizgi_l, cizgi_s):
    return pd.DataFrame({"yon": yon, "cizgi_l": cizgi_l, "cizgi_s": cizgi_s}, index=idx)


def chandelier(y: pd.Series, d: pd.Series, k: pd.Series, n: int = 22, carpan: float = 3.0) -> pd.DataFrame:
    """Chandelier Exit: uzun çizgi = son n kapanışın zirvesi - carpan*ATR(n), yalnız yükselir; kısa çizgi = son n kapanışın
    dibi + carpan*ATR(n), yalnız alçalır. Kapanış kısa çizginin üstüne çıkarsa yön +1, uzun çizginin altına inerse -1."""
    atr = g.atr(y, d, k, n).to_numpy(dtype=float)
    kv = k.to_numpy(dtype=float)
    zi = k.rolling(n, min_periods=n).max().to_numpy(dtype=float)
    di = k.rolling(n, min_periods=n).min().to_numpy(dtype=float)
    m = len(kv)
    yon = np.zeros(m, dtype=int)
    ls, ss = np.full(m, np.nan), np.full(m, np.nan)
    for i in range(m):
        if np.isnan(atr[i]) or np.isnan(zi[i]):
            continue
        l0, s0 = zi[i] - carpan * atr[i], di[i] + carpan * atr[i]
        if i > 0 and not np.isnan(ls[i - 1]):
            if kv[i - 1] > ls[i - 1]:
                l0 = max(l0, ls[i - 1])
            if kv[i - 1] < ss[i - 1]:
                s0 = min(s0, ss[i - 1])
            yon[i] = yon[i - 1]
            if kv[i] > ss[i - 1]:
                yon[i] = 1
            elif kv[i] < ls[i - 1]:
                yon[i] = -1
        ls[i], ss[i] = l0, s0
    return _donus_sonuc(k.index, yon, pd.Series(ls, index=k.index), pd.Series(ss, index=k.index))


def nrtr(k: pd.Series, yuzde: float = 0.02) -> pd.DataFrame:
    """NRTR: yön yukarıyken çizgi = (yönün başından beri en yüksek kapanış)*(1-yuzde); kapanış çizginin altına inerse yön
    aşağı döner ve çizgi = (en düşük kapanış)*(1+yuzde). Yalnız yüzde, ATR yok."""
    kv = k.to_numpy(dtype=float)
    m = len(kv)
    yon = np.zeros(m, dtype=int)
    cz = np.full(m, np.nan)
    if m:
        yon[0], cz[0], uc = 1, kv[0] * (1 - yuzde), kv[0]
    for i in range(1, m):
        if np.isnan(kv[i]):
            yon[i], cz[i] = yon[i - 1], cz[i - 1]
            continue
        if yon[i - 1] == 1:
            uc = max(uc, kv[i])
            if kv[i] < cz[i - 1]:
                yon[i], uc, cz[i] = -1, kv[i], kv[i] * (1 + yuzde)
            else:
                yon[i], cz[i] = 1, max(cz[i - 1], uc * (1 - yuzde))
        else:
            uc = min(uc, kv[i])
            if kv[i] > cz[i - 1]:
                yon[i], uc, cz[i] = 1, kv[i], kv[i] * (1 - yuzde)
            else:
                yon[i], cz[i] = -1, min(cz[i - 1], uc * (1 + yuzde))
    cz = pd.Series(cz, index=k.index)
    yon = pd.Series(yon, index=k.index)
    yon.iloc[: min(m, 20)] = 0      # ilk 20 mum: başlangıç yönü keyfi, sinyal yok
    return _donus_sonuc(k.index, yon, cz, cz)


def ha_atr_donus(a: pd.Series, y: pd.Series, d: pd.Series, k: pd.Series, n: int = 22, ma_n: int = 22,
                 yarim: float = 0.5, ma_tip: str = "sma") -> pd.DataFrame:
    """Heikin-Ashi kapanışı üzerinde MA(ma_n) +/- yarim*ATR(n) bandı: HA kapanışı üst bandı yukarı geçerse yön +1, alt bandı
    aşağı geçerse -1, arada önceki yön (histerezis). Uzun çizgi = alt bant, kısa çizgi = üst bant."""
    ha = b.heikin_ashi(a, y, d, k)
    hk = ha["ha_kapanis"]
    ma = g.ema(hk, ma_n) if ma_tip == "ema" else g.sma(hk, ma_n)
    atr = g.atr(y, d, k, n)
    ust, alt = ma + yarim * atr, ma - yarim * atr
    hv, uv, av = hk.to_numpy(dtype=float), ust.to_numpy(dtype=float), alt.to_numpy(dtype=float)
    yon = np.zeros(len(hv), dtype=int)
    for i in range(len(hv)):
        if np.isnan(uv[i]):
            continue
        yon[i] = yon[i - 1] if i else 0
        if hv[i] > uv[i]:
            yon[i] = 1
        elif hv[i] < av[i]:
            yon[i] = -1
    return _donus_sonuc(k.index, yon, alt, ust)


# ---------------------------------------------------------------- seçici ve türev göstergeler
OZEL_OSILATORLER = ("trix", "tsi", "kvo", "obv", "ad", "pvt", "mfi", "uo", "emv", "decycler", "stc", "wpr")


def ozel_osc(ad: str, mumlar: pd.DataFrame, n: int = 0, kisa: int = 0, uzun: int = 0) -> pd.Series:
    """İsimle osilatör/çizgi seç. n/kisa/uzun 0 ise göstergenin kendi varsayılanı kullanılır."""
    y, d, k, h = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], mumlar["hacim"]
    if ad == "trix":
        return trix(k, n or 14)
    if ad == "tsi":
        return tsi(k, uzun or 25, kisa or 13)
    if ad == "kvo":
        return kvo(y, d, k, h, kisa or 34, uzun or 55)
    if ad == "obv":
        return obv(k, h)
    if ad == "ad":
        return birikim_dagitim(y, d, k, h)
    if ad == "pvt":
        return pvt(k, h)
    if ad == "mfi":
        return mfi(y, d, k, h, n or 14)
    if ad == "uo":
        return ultimate_osc(y, d, k, n or 7, kisa or 14, uzun or 28)
    if ad == "emv":
        return emv(y, d, h, n or 14)
    if ad == "decycler":
        return decycler_osc(k, kisa or 100, uzun or 125)
    if ad == "stc":
        return stc(k, kisa or 23, uzun or 50, n or 10)
    if ad == "wpr":
        return williams_r(y, d, k, n or 14)
    raise ValueError(f"Bilinmeyen gosterge: {ad}")


def stoch_rsi(kap: pd.Series, rsi_n: int = 14, stoch_n: int = 14, k_n: int = 3, d_n: int = 3) -> pd.DataFrame:
    """Stokastik RSI (0-100): RSI'ın stoch_n penceresindeki konumu; K = SMA(k_n), D = SMA(d_n)(K)."""
    r = g.rsi(kap, rsi_n)
    alt, ust = r.rolling(stoch_n, min_periods=stoch_n).min(), r.rolling(stoch_n, min_periods=stoch_n).max()
    ham = 100.0 * (r - alt) / (ust - alt).where(lambda x: x > 0)
    k = g.sma(ham, k_n)
    return pd.DataFrame({"k": k, "d": g.sma(k, d_n)})


def rsi_uyarlanir(kap: pd.Series, en_az: int = 8, en_cok: int = 28, vol_kisa: int = 10, vol_uzun: int = 50,
                  yumusat: int = 3) -> pd.Series:
    """Volatiliteye göre periyodu en_az..en_cok arasında kayan RSI (varsayım: kaynak formül belirsiz).
    Volatilite oranı vr = std(vol_kisa)/std(vol_uzun) (getiri üzerinden); vr yüksekse periyot kısalır:
    periyot = en_cok - (en_cok-en_az)*clip(vr-0.5, 0, 1), `yumusat` barlık EMA ile düzeltilir; Wilder özyinelemesi
    değişken alfa (1/periyot) ile yürütülür."""
    r = kap.pct_change(fill_method=None)
    vr = r.rolling(vol_kisa, min_periods=vol_kisa).std() / r.rolling(vol_uzun, min_periods=vol_uzun).std().where(lambda x: x > 0)
    per = (en_cok - (en_cok - en_az) * (vr - 0.5).clip(0.0, 1.0))
    per = per.ewm(span=yumusat, adjust=False, min_periods=1).mean().clip(en_az, en_cok)
    fark = kap.diff().to_numpy(dtype=float)
    pv = per.to_numpy(dtype=float)
    out = np.full(len(fark), np.nan)
    ort_k = ort_z = np.nan
    for i in range(1, len(fark)):
        if np.isnan(fark[i]) or np.isnan(pv[i]):
            continue
        kz, zy = max(fark[i], 0.0), max(-fark[i], 0.0)
        if np.isnan(ort_k):
            ort_k, ort_z = kz, zy
        else:
            a = 1.0 / pv[i]
            ort_k, ort_z = ort_k + a * (kz - ort_k), ort_z + a * (zy - ort_z)
        out[i] = 100.0 if ort_z == 0 else 100.0 - 100.0 / (1.0 + ort_k / ort_z)
    out[: vol_uzun + en_cok] = np.nan
    return pd.Series(out, index=kap.index)


def tepe_dip_medyani(osc: pd.Series, tepe_esik: float = 60.0, dip_esik: float = 30.0, n: int = 10) -> pd.DataFrame:
    """Osilatörün `tepe_esik` üstündeki bölge tepelerinin ve `dip_esik` altındaki bölge diplerinin son n tanesinin medyanı.
    Bir bölge ancak BİTTİĞİNDE (osilatör eşiğin öbür tarafına geçtiğinde) kayda girer (nedensel). İlk kayıt gelene dek NaN."""
    v = osc.to_numpy(dtype=float)
    tepeler, dipler = [], []
    in_t = in_d = False
    uc_t = uc_d = np.nan
    tm, dm = np.full(len(v), np.nan), np.full(len(v), np.nan)
    for i, x in enumerate(v):
        if not np.isnan(x):
            if x > tepe_esik:
                uc_t = x if not in_t else max(uc_t, x)
                in_t = True
            elif in_t:
                tepeler.append(uc_t)
                in_t = False
            if x < dip_esik:
                uc_d = x if not in_d else min(uc_d, x)
                in_d = True
            elif in_d:
                dipler.append(uc_d)
                in_d = False
        if tepeler:
            tm[i] = float(np.median(tepeler[-n:]))
        if dipler:
            dm[i] = float(np.median(dipler[-n:]))
    return pd.DataFrame({"tepe": tm, "dip": dm}, index=osc.index)


def ichimoku_skor(y: pd.Series, d: pd.Series, k: pd.Series, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52,
                  kaydirma: int = 26, zayif: float = 0.5, notr: float = 1.0, guclu: float = 2.0) -> pd.Series:
    """Ichimoku yedi sinyalinin bulut konumuna göre puanlanmış, -100..100 normalize edilmiş toplamı (NEDENSEL).
    Sinyaller: TK kesişimi, fiyat-Kijun kesişimi, bulut kırılımı, Senkou A/B kesişimi, Chikou kesişimi (fiyat k mum önceki
    fiyatı keser), Chikou yerleşimi (fiyatın k mum önceki bulutla konumu), fiyatın bulutla konumu. Kesişim sinyalleri bulutun
    üstünde/içinde/altında oluşmasına göre yükselişte zayıf/nötr/güçlü (düşüşte tersi) puan alır ve bir sonraki sinyale dek
    korunur. Kesişim noktası yerine kesişim mumundaki değer kullanılır (yaklaşım). Bulut b.ichimoku ile aynıdır (k mum
    gecikmeli, gelecek bulut kullanılmaz)."""
    ic = b.ichimoku(y, d, tenkan, kijun, senkou_b, kaydirma)
    t, kij, sa, sb = ic["tenkan"], ic["kijun"], ic["span_a"], ic["span_b"]

    def ust(v, a, c):
        return (v > a) & (v > c) & (v > a.shift(1)) & (v > c.shift(1))

    def alt(v, a, c):
        return (v < a) & (v < c) & (v < a.shift(1)) & (v < c.shift(1))

    def tablo(boga, ayi, deger):
        u, a_ = ust(deger, sa, sb), alt(deger, sa, sb)
        i_ = ~u & ~a_
        s = pd.Series(np.nan, index=k.index)
        s[boga & a_] = zayif
        s[boga & i_] = notr
        s[boga & u] = guclu
        s[ayi & a_] = -guclu
        s[ayi & i_] = -notr
        s[ayi & u] = -zayif
        return s.ffill().fillna(0.0)

    tk = tablo(b.yukari_kesis(t, kij), b.asagi_kesis(t, kij), (t + kij) / 2.0)
    pk = tablo(b.yukari_kesis(k, kij), b.asagi_kesis(k, kij), kij)
    bo = pd.Series(np.nan, index=k.index)
    boga = (b.yukari_kesis(k, sa) & (sa >= sb)) | (b.yukari_kesis(k, sb) & (sb >= sa))
    ayi = (b.asagi_kesis(k, sb) & (sa >= sb)) | (b.asagi_kesis(k, sa) & (sb >= sa))
    bo[boga], bo[ayi] = guclu, -guclu
    bo = bo.ffill().fillna(0.0)
    a0 = (t + kij) / 2.0
    b0 = (y.rolling(senkou_b, min_periods=senkou_b).max() + d.rolling(senkou_b, min_periods=senkou_b).min()) / 2.0
    fu, fa = ust(k, sa, sb), alt(k, sa, sb)
    fi = ~fu & ~fa

    def tablo_fiyat(boga_, ayi_):
        s = pd.Series(np.nan, index=k.index)
        s[boga_ & fa], s[boga_ & fi], s[boga_ & fu] = zayif, notr, guclu
        s[ayi_ & fa], s[ayi_ & fi], s[ayi_ & fu] = -guclu, -notr, -zayif
        return s.ffill().fillna(0.0)

    sc = tablo_fiyat(b.yukari_kesis(a0, b0), b.asagi_kesis(a0, b0))
    lead = k.shift(kaydirma)
    cc = tablo_fiyat(b.yukari_kesis(k, lead), b.asagi_kesis(k, lead))
    pp = pd.Series(np.where(fu, guclu, np.where(fa, -guclu, 0.0)), index=k.index)
    sa2, sb2 = sa.shift(kaydirma), sb.shift(kaydirma)
    cp = pd.Series(np.where(ust(k, sa2, sb2), guclu, np.where(alt(k, sa2, sb2), -guclu, 0.0)), index=k.index)
    toplam = tk + pk + bo + sc + cc + pp + cp
    skor = 100.0 * toplam / (7.0 * guclu)
    return skor.where(sa2.notna() & sb2.notna() & t.notna() & kij.notna())


# ---------------------------------------------------------------- portföy ağırlık ve rejim yardımcıları (saf numpy/pandas, scipy yok)
def _kume_varyansi(cov: np.ndarray, uyeler: list) -> float:
    alt = cov[np.ix_(uyeler, uyeler)]
    iv = 1.0 / np.clip(np.diag(alt), 1e-18, None)
    w = iv / iv.sum()
    return float(w @ alt @ w)


def hrp_agirlik(cov: np.ndarray) -> np.ndarray:
    """Hiyerarşik Risk Paritesi (López de Prado): korelasyon mesafesi sqrt((1-rho)/2), tek bağlantılı kümeleme (yaprak sırası),
    özyinelemeli ters-varyans ikiye bölme. Girdi: kovaryans (n,n). Çıktı: toplamı 1 olan ağırlıklar."""
    n = len(cov)
    if n == 1:
        return np.ones(1)
    sd = np.sqrt(np.clip(np.diag(cov), 1e-18, None))
    kor = np.clip(cov / np.outer(sd, sd), -1.0, 1.0)
    dist = np.sqrt((1.0 - kor) / 2.0)
    kume = {i: [i] for i in range(n)}
    sira = {i: [i] for i in range(n)}
    aktif = list(range(n))
    yeni = n
    while len(aktif) > 1:
        en = (np.inf, None, None)
        for ai in range(len(aktif)):
            for bi in range(ai + 1, len(aktif)):
                i, j = aktif[ai], aktif[bi]
                d = min(dist[a, b] for a in kume[i] for b in kume[j])
                if d < en[0]:
                    en = (d, i, j)
        _, i, j = en
        kume[yeni] = kume[i] + kume[j]
        sira[yeni] = sira[i] + sira[j]
        aktif = [a for a in aktif if a not in (i, j)] + [yeni]
        yeni += 1
    duzen = sira[aktif[0]]
    w = np.ones(n)
    parcalar = [duzen]
    while parcalar:
        sonraki = []
        for c in parcalar:
            if len(c) < 2:
                continue
            h = len(c) // 2
            c1, c2 = c[:h], c[h:]
            v1, v2 = _kume_varyansi(cov, c1), _kume_varyansi(cov, c2)
            alfa = 1.0 - v1 / (v1 + v2)
            w[c1] *= alfa
            w[c2] *= 1.0 - alfa
            sonraki += [c1, c2]
        parcalar = sonraki
    return w / w.sum()


def _aktif_kume_cozum(cov: np.ndarray, vektor: np.ndarray) -> np.ndarray:
    """Long-only: w ~ inv(cov_S) @ vektor_S, negatifler tek tek (en negatif önce) elenerek (aktif küme). Toplam 1; çözüm yoksa sıfırlar."""
    n = len(cov)
    idx = list(range(n))
    while idx:
        alt = cov[np.ix_(idx, idx)] + 1e-12 * np.eye(len(idx))
        try:
            w = np.linalg.solve(alt, vektor[idx])
        except np.linalg.LinAlgError:
            return np.zeros(n)
        if w.sum() <= 0:
            if len(idx) == 1:
                break
            idx.pop(int(np.argmin(vektor[idx])))
            continue
        w = w / w.sum()
        if (w >= -1e-12).all():
            out = np.zeros(n)
            out[idx] = np.clip(w, 0.0, None)
            return out / out.sum()
        idx.pop(int(np.argmin(w)))
    return np.zeros(n)


def min_varyans_agirlik(cov: np.ndarray) -> np.ndarray:
    """Long-only global minimum varyans (aktif küme yöntemi)."""
    return _aktif_kume_cozum(cov, np.ones(len(cov)))


def maks_sharpe_agirlik(cov: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Long-only teğet (maks. Sharpe) portföy: w ~ inv(cov) @ mu, beklenen getirisi <= 0 olanlar baştan elenir. Hepsi <= 0 ise sıfırlar (nakit).
    Girdi (mu) tahmini gürültülüdür; kısıtsız optimizasyon kodlanmadı (çözücü yok)."""
    n = len(cov)
    v = np.where(mu > 0, mu, 0.0)
    if not (v > 0).any():
        return np.zeros(n)
    out = np.zeros(n)
    pos = [i for i in range(n) if v[i] > 0]
    out[pos] = _aktif_kume_cozum(cov[np.ix_(pos, pos)], v[pos])
    return out


def triple_rsi_ok(kap: pd.DataFrame, kisa: int = 20, orta: int = 60, uzun: int = 120) -> pd.DataFrame:
    """Triple RSI giriş süzgeci (whchien/ai-trader tarifi, yorum bize ait): RSI(uzun) > 55, RSI(orta) < 75, RSI(kisa) son 3 barda > 55 ve
    2 barda göreli %2'den fazla yükselmiş. Sütun başına bool tablo (NaN -> False)."""
    out = {}
    for c in kap.columns:
        s = kap[c]
        ru, ro, rk = g.rsi(s, uzun), g.rsi(s, orta), g.rsi(s, kisa)
        out[c] = ((ru > 55) & (ro < 75) & (rk.rolling(3, min_periods=3).min() > 55) & (rk / rk.shift(2) - 1.0 > 0.02))
    return pd.DataFrame(out, index=kap.index).fillna(False)


def rejim_genislik(kap: pd.DataFrame, ref_getiri5: pd.Series, ref_hacim: pd.Series | None, sma_n: int = 50, delta_gun: int = 5,
                   esik: float = 0.08, hacim_tavan: float = 1.05) -> pd.Series:
    """Evren genişliği rejimi (Edge 'rejim kayması'): genişlik = SMA(sma_n) üstündeki sembol oranı. delta = genişlik[t]-genişlik[t-delta_gun].
    delta >= +esik ve ref 5g getirisi > 0 ve (ref_hacim verilmişse) hacim trendi <= hacim_tavan -> risk-on; delta <= -esik -> risk-off;
    arada önceki durum (başlangıç risk-off). True = risk-on."""
    ust = (kap > kap.rolling(sma_n, min_periods=sma_n).mean())
    gecerli = kap.rolling(sma_n, min_periods=sma_n).mean().notna()
    gen = ust.where(gecerli).mean(axis=1).where(gecerli.any(axis=1))
    delta = gen - gen.shift(delta_gun)
    hac_ok = pd.Series(True, index=kap.index)
    if ref_hacim is not None:
        hac_ok = (ref_hacim.rolling(5, min_periods=5).mean() / ref_hacim.rolling(20, min_periods=20).mean() <= hacim_tavan).fillna(False)
    on = (delta >= esik) & (ref_getiri5 > 0) & hac_ok
    off = delta <= -esik
    return _kalici_durum(on.to_numpy(dtype=bool), off.to_numpy(dtype=bool), kap.index)


def _kalici_durum(on: np.ndarray, off: np.ndarray, index) -> pd.Series:
    d = np.zeros(len(on), dtype=bool)
    cur = False
    for i in range(len(on)):
        if on[i]:
            cur = True
        elif off[i]:
            cur = False
        d[i] = cur
    return pd.Series(d, index=index)


def rejim_ftd(kap: pd.Series, hacim: pd.Series, dusus_esik: float = 0.03, min_dusus_gun: int = 3, ftd_getiri: float = 0.0125,
              gun_min: int = 4, gun_maks: int = 7, zirve_gun: int = 60) -> pd.Series:
    """O'Neil Follow-Through Day (rejim açma). Düzeltme: kapanış son zirve_gun günlük zirveden >= dusus_esik aşağıda ve zirveden beri en az
    min_dusus_gun düşüş günü var. Düzeltmenin dibinden sonra ilk yükseliş kapanışı rallinin 1. günüdür; rallinin gun_min..gun_maks. gününde
    getiri >= ftd_getiri ve hacim bir önceki günden fazlaysa FTD -> risk-on. Kapanış rally dibinin altına inerse ralli geçersiz; risk-on iken
    kapanış FTD'nin rally dibinin altına inerse risk-off (varsayım). Başlangıç risk-off. True = risk-on. Nedensel."""
    k = kap.to_numpy(dtype=float)
    h = hacim.to_numpy(dtype=float)
    zirve = kap.rolling(zirve_gun, min_periods=10).max().to_numpy(dtype=float)
    on = np.zeros(len(k), dtype=bool)
    cur = False
    dusus_say = 0
    dip = np.nan          # düzeltmenin en düşük kapanışı
    ralli_dip = np.nan
    ftd_dip = np.nan
    gun_say = 0
    ralli = False
    for i in range(1, len(k)):
        if np.isnan(k[i]) or np.isnan(k[i - 1]) or np.isnan(zirve[i]):
            on[i] = cur
            continue
        if k[i] >= zirve[i]:
            dusus_say, dip, ralli = 0, np.nan, False
        elif k[i] < k[i - 1]:
            dusus_say += 1
        duzeltme = (zirve[i] - k[i]) / zirve[i] >= dusus_esik
        if ralli:
            if k[i] < ralli_dip:
                ralli = False
                dip = k[i]
            else:
                gun_say += 1
                if gun_min <= gun_say <= gun_maks and k[i] / k[i - 1] - 1.0 >= ftd_getiri and h[i] > h[i - 1]:
                    cur, ralli, ftd_dip = True, False, ralli_dip
                elif gun_say >= gun_maks:
                    ralli = False
        elif duzeltme or not np.isnan(dip):
            if np.isnan(dip) or k[i] < dip:
                dip = k[i]
            elif k[i] > k[i - 1] and k[i - 1] <= dip and dusus_say >= min_dusus_gun:
                ralli, gun_say, ralli_dip = True, 1, dip
        if cur and k[i] < ftd_dip:
            cur = False
        on[i] = cur
    return pd.Series(on, index=kap.index)


def rejim_dagitim(kap: pd.Series, hacim: pd.Series, esik: int = 5, pencere: int = 25, dusus: float = 0.002) -> pd.Series:
    """IBD dağıtım günü sayacı: dağıtım günü = kapanış bir öncekine göre >= %dusus düşmüş ve hacim bir önceki günden fazla. Son `pencere` seansta
    >= `esik` dağıtım günü varsa risk-off (False), değilse risk-on (True). Pencere dolmadan sayaç eldeki günlerle. (+%6 yükselişle gün silme kodlanmadı.)"""
    d = ((kap / kap.shift(1) - 1.0) <= -dusus) & (hacim > hacim.shift(1))
    sayi = d.astype(float).rolling(pencere, min_periods=1).sum()
    return (sayi < esik) & kap.notna()
