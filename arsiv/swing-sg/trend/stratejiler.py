"""brainbrick-trades long-only stratejileri (düzeltilmiş) + bizim yaklaşımla geliştirilmiş sürümler.

Orijinal (kod sahibi tarafından verilen varsayılanlar):
  037  günlük kapanış > SMA50 VE son tamamlanmış haftalık kapanış > haftalık SMA50
  007  günlük n-bar getirisi > 0 VE haftalık 52-hafta getirisi > 0 (orijinalde günlük n=52 gün: HATA → 252/365)
  050  maruziyet = min(1, hedef / 60 günlük yıllık volatilite), haftalık güncelleme
  001  12-1 momentum, en iyi %10 (en az 3), aylık, eşit ağırlık
  020  artık (beta-arındırılmış) 12-1 momentum, en iyi %10
  007P 12 aylık getirisi pozitif olan tümü, eşit ağırlık
  012  252 günlük volatilitesi en düşük %10
  089  emtia değer: 5 yıl önceki fiyat / bugünkü fiyat, en yüksek üçte bir

Bizim yaklaşım (swing sisteminden): haftalık yön (EMA10/EMA30), piyasa rejimi (sınıf endeksi trendi),
volatiliteye göre pozisyon büyüklüğü, parametre seçimi yalnızca 2015-2022 verisinde.
"""
import numpy as np
import pandas as pd

from swing import gostergeler as g


# ------------------------------------------------------------------ yardımcılar
def haftalik_kapanis(c):
    return c.resample("W-SUN").last().dropna()


def haftadan_gune(ws, gunluk_index):
    """Tamamlanmış haftanın değeri ertesi Pazartesi'den itibaren geçerli (ileriye bakma yok)."""
    s = ws.copy()
    s.index = s.index + pd.Timedelta(days=1)
    return s.reindex(gunluk_index, method="ffill")


def vol_hedef(c, hedef, ann, pencere=60):
    vol = c.pct_change().rolling(pencere).std() * np.sqrt(ann)
    w = (hedef / vol).clip(upper=1.0)
    return w.resample("W-SUN").last().pipe(lambda x: haftadan_gune(x, c.index)).fillna(0.0)


def yon_ema(c):
    """Bizim haftalık yön: haftalık EMA10 > EMA30 ve kapanış > EMA30 (swing S2/S3 ile aynı)."""
    w = haftalik_kapanis(c)
    e1, e2 = g.ema(w, 10), g.ema(w, 30)
    return haftadan_gune(((e1 > e2) & (w > e2)).astype(float), c.index).fillna(0.0)


# ------------------------------------------------------------------ tek enstrüman
def s037(df, n=50, **_):
    c = df["Close"]
    w = haftalik_kapanis(c)
    hf = haftadan_gune((w > w.rolling(n).mean()).astype(float), c.index).fillna(0.0)
    return ((c > c.rolling(n).mean()).astype(float) * hf).fillna(0.0)


def s007(df, n_gun=252, n_hafta=52, **_):
    c = df["Close"]
    w = haftalik_kapanis(c)
    hf = haftadan_gune((w / w.shift(n_hafta) > 1).astype(float), c.index).fillna(0.0)
    return ((c / c.shift(n_gun) > 1).astype(float) * hf).fillna(0.0)


def t1(df, n=50, **_):
    """Bizim sürüm: haftalık EMA10/30 yönü + günlük kapanış > SMA n."""
    c = df["Close"]
    return ((c > c.rolling(n).mean()).astype(float) * yon_ema(c)).fillna(0.0)


TEKLER = {"037 SMA50": s037, "007 12ay (düzeltilmiş)": s007,
          "007 orijinal (52 gün)": lambda df, **k: s007(df, n_gun=52), "T1 bizim (EMA10/30 + SMA50)": t1}


# ------------------------------------------------------------------ portföy skorları (ay sonu)
def skor_001(m, px):
    return m.shift(1) / m.shift(12) - 1


def skor_020(m, px, T=12, S=1, beta_win=36):
    r = m.pct_change()
    mkt = r.mean(axis=1)
    skor = pd.DataFrame(np.nan, index=m.index, columns=m.columns)
    for i in range(beta_win + T, len(r)):
        est = r.iloc[i - beta_win - T:i - T]
        x = mkt.iloc[i - beta_win - T:i - T]
        beta = est.apply(lambda y: np.polyfit(x[y.notna()], y.dropna(), 1)[0] if y.notna().sum() > 24 else np.nan)
        form = r.iloc[i - T - S + 1:i - S + 1]
        eps = form.sub(mkt.iloc[i - T - S + 1:i - S + 1].values[:, None] * beta.values, axis=0)
        skor.iloc[i] = eps.mean() / eps.std()
    return skor


def skor_007p(m, px):
    return m / m.shift(12) - 1


def skor_012(m, px):
    return -(px.pct_change().rolling(252).std().resample("ME").last())  # düşük vol = yüksek skor


def skor_089(m, px):
    return m.shift(60) / m


PORTFOY = {"001 momentum": (skor_001, "top", 0.1), "020 artık momentum": (skor_020, "top", 0.1),
           "007P trend portföyü": (skor_007p, "pozitif", None), "012 düşük volatilite": (skor_012, "top", 0.1),
           "089 değer (emtia)": (skor_089, "top", 1 / 3)}


def agirliklar(px, skor_fn, secim, q, min_ad=3):
    """Ay sonu kapanışında karar verilen hedef ağırlıklar (günlük indekste, bir sonraki ay sonuna kadar sabit)."""
    m = px.resample("ME").last()
    skor = skor_fn(m, px)
    W = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    for d in m.index:
        if d > px.index[-1]:
            continue  # ay henüz bitmedi: yeniden dengeleme ay tamamlanınca yapılır
        s = skor.loc[d].dropna() if d in skor.index else pd.Series(dtype=float)
        gun = px.index[px.index <= d]
        if not len(gun):
            continue
        w = pd.Series(0.0, index=px.columns)
        if len(s):
            if secim == "pozitif":
                adlar = s[s > 0].index
            else:
                k = max(min_ad, int(round(len(s) * q)))
                adlar = s.nlargest(k).index
            if len(adlar):
                w[adlar] = 1.0 / len(adlar)
        W.loc[gun[-1]] = w.values
    return W.ffill().fillna(0.0)
