"""D11-G (GitHub kaynaklı yeni aileler) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi
kullanır. Paylaşılan dosyalara dokunulmaz. KOD KOPYALANMADI; formüller kendi yazımımızdır.

  ultimate_osc, trix, momentum, andean, yuzde_zigzag, lwma, d_u_orani, ilk_olay_gun
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g


def ultimate_osc(yuksek, dusuk, kapanis, k1: int = 7, k2: int = 14, k3: int = 28) -> pd.Series:
    """Ultimate Oscillator (Williams): alış baskısı / gerçek aralık toplamlarının 4:2:1 ağırlıklı ortalaması (0..100)."""
    onceki = kapanis.shift(1)
    alt = np.minimum(dusuk, onceki)
    ust = np.maximum(yuksek, onceki)
    bp, tr = kapanis - alt, ust - alt

    def ort(n):
        return bp.rolling(n, min_periods=n).sum() / tr.rolling(n, min_periods=n).sum().where(lambda x: x > 0)
    return 100.0 * (4.0 * ort(k1) + 2.0 * ort(k2) + ort(k3)) / 7.0


def trix(kapanis: pd.Series, n: int) -> pd.Series:
    """TRIX: üçlü EMA'nın 1 mumluk yüzde değişimi."""
    e = kapanis.ewm(span=n, adjust=False, min_periods=n).mean()
    e = e.ewm(span=n, adjust=False, min_periods=n).mean()
    e = e.ewm(span=n, adjust=False, min_periods=n).mean()
    return 100.0 * e.pct_change()


def momentum(kapanis: pd.Series, n: int) -> pd.Series:
    """MetaTrader Momentum: 100 x kapanış / n mum önceki kapanış (100 = değişim yok)."""
    return 100.0 * kapanis / kapanis.shift(n)


def lwma(seri: pd.Series, n: int) -> pd.Series:
    """Doğrusal ağırlıklı ortalama (en yeni değer en büyük ağırlık)."""
    n = int(n)
    w = np.arange(1, n + 1, dtype=float)
    return seri.rolling(n, min_periods=n).apply(lambda x: float(np.dot(x, w) / w.sum()), raw=True)


def andean(acilis: pd.Series, kapanis: pd.Series, uzunluk: int = 50, sinyal_n: int = 9) -> pd.DataFrame:
    """Andean Osilatör: kapanış/açılış zarflarının üstel güncellenen alt-üst anlarından boğa ve ayı bileşenleri.
    alfa = 2/(uzunluk+1); up1/up2 = zarfın 1. ve 2. anı (yüksek yönlü), dn1/dn2 = alçak yönlü.
    boga = sqrt(dn2 - dn1^2), ayi = sqrt(up2 - up1^2), sinyal = EMA(max(boga, ayi), sinyal_n). Özyinelemeli, nedensel."""
    c = kapanis.to_numpy(float)
    o = acilis.to_numpy(float)
    n = len(c)
    alfa = 2.0 / (uzunluk + 1.0)
    up1 = np.full(n, np.nan)
    up2 = np.full(n, np.nan)
    dn1 = np.full(n, np.nan)
    dn2 = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(c[i]) or np.isnan(o[i]):
            continue
        if i == 0 or np.isnan(up1[i - 1]):
            up1[i], up2[i], dn1[i], dn2[i] = c[i], c[i] * c[i], c[i], c[i] * c[i]
            continue
        up1[i] = max(c[i], o[i], up1[i - 1] - (up1[i - 1] - c[i]) * alfa)
        up2[i] = max(c[i] * c[i], o[i] * o[i], up2[i - 1] - (up2[i - 1] - c[i] * c[i]) * alfa)
        dn1[i] = min(c[i], o[i], dn1[i - 1] + (c[i] - dn1[i - 1]) * alfa)
        dn2[i] = min(c[i] * c[i], o[i] * o[i], dn2[i - 1] + (c[i] * c[i] - dn2[i - 1]) * alfa)
    boga = np.sqrt(np.clip(dn2 - dn1 * dn1, 0.0, None))
    ayi = np.sqrt(np.clip(up2 - up1 * up1, 0.0, None))
    boga_s = pd.Series(boga, index=kapanis.index)
    ayi_s = pd.Series(ayi, index=kapanis.index)
    sinyal = np.maximum(boga_s, ayi_s).ewm(span=sinyal_n, adjust=False, min_periods=sinyal_n).mean()
    return pd.DataFrame({"boga": boga_s, "ayi": ayi_s, "sinyal": sinyal})


def yuzde_zigzag(kapanis: pd.Series, yuzde: float) -> pd.DataFrame:
    """Kapanışa dayalı YÜZDE ZigZag, NEDENSEL ve ONAYLI: ilk durum long; long iken zirveden `yuzde` düşüş kapanışta
    görülünce short'a döner (dönüş o mumun kapanışında bilinir), short iken dipten `yuzde` yükseliş görülünce long'a döner.
    Dönüş mumları: `donus_long`, `donus_short` (bool); `durum` +1/-1 (o mumun kapanışı itibarıyla)."""
    c = kapanis.to_numpy(float)
    n = len(c)
    durum = np.zeros(n, dtype=int)
    dl = np.zeros(n, dtype=bool)
    ds = np.zeros(n, dtype=bool)
    d, uc = 1, np.nan
    for i in range(n):
        x = c[i]
        if np.isnan(x):
            durum[i] = d
            continue
        if np.isnan(uc):
            uc = x
        if d == 1:
            if x > uc:
                uc = x
            elif x <= uc * (1.0 - yuzde):
                d, uc = -1, x
                ds[i] = True
        else:
            if x < uc:
                uc = x
            elif x >= uc * (1.0 + yuzde):
                d, uc = 1, x
                dl[i] = True
        durum[i] = d
    idx = kapanis.index
    return pd.DataFrame({"durum": durum, "donus_long": dl, "donus_short": ds}, index=idx)


def d_u_orani(kapanis: pd.Series, n: int) -> pd.Series:
    """Son n mumda kapanış düşüşleri toplamı / yükselişleri toplamı (GU oranı, <1: yükseliş ağırlıklı)."""
    d = kapanis.diff()
    yuk = d.clip(lower=0.0).rolling(n, min_periods=n).sum()
    asg = (-d).clip(lower=0.0).rolling(n, min_periods=n).sum()
    return asg / yuk.where(yuk > 0)
