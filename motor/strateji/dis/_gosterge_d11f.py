"""D11-f (GitHub kaynaklı swing aileleri) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan
veriyi kullanır. Paylaşılan dosyalara dokunulmaz. Kural anlaşılıp kendi kodumuzla yazıldı (kaynak kodu kopyalanmadı).

  alma, poli_tahmin, rsrs_egim, choppiness, yavas_stokastik, ay_uygunluk, ay_gunu, w_deseni, uc_macd_al
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g


def alma(seri: pd.Series, n: int = 9, ofset: float = 0.85, sigma: float = 6.0) -> pd.Series:
    """Arnaud Legoux hareketli ortalaması: Gauss ağırlıklı MA; ağırlık tepesi pencerenin `ofset` oranında."""
    n = int(n)
    m = ofset * (n - 1)
    s = n / sigma
    w = np.exp(-((np.arange(n) - m) ** 2) / (2.0 * s * s))
    w = w / w.sum()
    out = np.full(len(seri), np.nan)
    a = seri.to_numpy(dtype=float)
    if len(a) >= n:
        out[n - 1:] = sliding_window_view(a, n) @ w
    return pd.Series(out, index=seri.index)


def poli_tahmin(kapanis: pd.Series, pencere: int = 252, derece: int = 3) -> pd.Series:
    """Her mumda son `pencere` kapanışa `derece`. dereceden polinom uydurur, bir adım ilerisini tahmin eder.
    Pencere içi x ekseni [-1, 1]'e normalleştirilir; tahmin = pencere . w (w sabit, pinv ile bir kez hesaplanır).
    Yalnız o mumun penceresi kullanılır (kayan pencere, nedensel)."""
    n, d = int(pencere), int(derece)
    x = np.linspace(-1.0, 1.0, n)
    w = np.vander([1.0 + 2.0 / (n - 1)], d + 1)[0] @ np.linalg.pinv(np.vander(x, d + 1))
    a = kapanis.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        out[n - 1:] = sliding_window_view(a, n) @ w
    return pd.Series(out, index=kapanis.index)


def rsrs_egim(yuksek: pd.Series, dusuk: pd.Series, n: int = 20) -> pd.Series:
    """RSRS: son n barda yüksek = a + b x düşük OLS eğimi b (cov(düşük, yüksek) / var(düşük))."""
    n = int(n)
    return dusuk.rolling(n, min_periods=n).cov(yuksek) / dusuk.rolling(n, min_periods=n).var().where(lambda v: v > 0)


def choppiness(yuksek, dusuk, kapanis, n: int = 14) -> pd.Series:
    """Choppiness Index (0..100): 100 x log10(toplam TR / (en yüksek - en düşük)) / log10(n)."""
    tr = g.gercek_aralik(yuksek, dusuk, kapanis)
    aralik = (yuksek.rolling(n, min_periods=n).max() - dusuk.rolling(n, min_periods=n).min()).where(lambda v: v > 0)
    return 100.0 * np.log10(tr.rolling(n, min_periods=n).sum() / aralik) / np.log10(n)


def yavas_stokastik(yuksek, dusuk, kapanis, k_n: int = 7, yavas: int = 3, d_n: int = 3) -> pd.DataFrame:
    """Yavaş stokastik: ham %K'nın `yavas` SMA'sı = %K, onun `d_n` SMA'sı = %D (MT5 STO_LOWHIGH / SMA)."""
    hh = yuksek.rolling(k_n, min_periods=k_n).max()
    ll = dusuk.rolling(k_n, min_periods=k_n).min()
    ham = 100.0 * (kapanis - ll) / (hh - ll).where(hh != ll)
    k = g.sma(ham, yavas)
    return pd.DataFrame({"k": k, "d": g.sma(k, d_n)})


def _naive_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_localize(None) if index.tz is not None else index


def ay_gunu(index: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(index.day, index=index)


def ay_uygunluk(kapanis: pd.Series, min_ornek: int, min_ort: float, min_kazanma: float) -> pd.DataFrame:
    """Veri güdümlü ay mevsimselliği, yalnız GEÇMİŞ yıllardan. Her takvim ayı (yıl, ay) için, AYNI ayın önceki
    yıllardaki aylık getirileri (ay sonu kapanış / önceki ay sonu kapanış - 1) alınır; örnek sayısı >= min_ornek,
    ortalama >= min_ort ve kazanma oranı >= min_kazanma ise o ay "uygun". Dönüş (mumlarla aynı indeks):
    uygun (bool), yeni_ay (bool: bu mum ayın ilk mumu). Cari ayın kendi getirisi hiç kullanılmaz."""
    per = _naive_index(kapanis.index).to_period("M")
    ay_kap = kapanis.groupby(per).last()
    getiri = ay_kap.pct_change()
    uygun_per = {}
    for p in ay_kap.index:
        gecmis = getiri[(getiri.index.month == p.month) & (getiri.index.year < p.year)].dropna()
        uygun_per[p] = bool(len(gecmis) >= min_ornek and gecmis.mean() >= min_ort and (gecmis > 0).mean() >= min_kazanma)
    uygun = pd.Series([uygun_per[p] for p in per], index=kapanis.index)
    p_ser = pd.Series(per.astype(str), index=kapanis.index)
    yeni = (p_ser != p_ser.shift(1))
    yeni.iloc[0] = False
    return pd.DataFrame({"uygun": uygun, "yeni_ay": yeni})


def w_deseni(h: pd.Series, tol: float, min_sicrama: float) -> pd.Series:
    """MACD histogramında W (alım) deseni, negatif dilim içinde. Dilim = histogramın sıfırı geçmediği ardışık negatif mumlar.
    Dip = h[t-1] < h[t-2] ve h[t-1] < h[t] (t mumunda onaylanır, 1 mum gecikme). Aynı dilimde önceki dipten sonra histogram
    en az min_sicrama x |önceki dip| yükselmiş ve yeni dip, önceki dipten tol oranından fazla derin değilse (yeni >= eski x (1+tol))
    t mumunda W sinyali. M deseni için -h verilir. Nedensel."""
    a = h.to_numpy(dtype=float)
    n = len(a)
    out = np.zeros(n, dtype=bool)
    dip = np.nan
    ara_max = np.nan
    for t in range(2, n):
        if not a[t] < 0:                       # NaN ya da >= 0: dilim bitti
            dip = np.nan
            continue
        if a[t - 1] < a[t - 2] and a[t - 1] < a[t]:
            v = a[t - 1]
            if not np.isnan(dip) and ara_max - dip >= min_sicrama * abs(dip) and v >= dip * (1.0 + tol):
                out[t] = True
            dip = v
            ara_max = a[t]
        elif not np.isnan(dip):
            ara_max = max(ara_max, a[t])
    return pd.Series(out, index=h.index)


def _poz(x) -> bool:
    return x > 0          # NaN -> False


def uc_macd_al(m1: np.ndarray, m2: np.ndarray, m3: np.ndarray, pencere: int = 32) -> np.ndarray:
    """3MACD alım koşulu (A veya B), her mum t için; MQL dizin i = t - i + 1 (1 = son kapanmış mum). Satım için negatif
    seriler verilir. Kuralı kaynak EA'nın mantığından yeniden yazdık (kopya değil)."""
    n = len(m1)
    W = int(pencere)
    out = np.zeros(n, dtype=bool)
    with np.errstate(invalid="ignore"):
        on_a = (m3 > 0) & (m2 > 0) & (np.roll(m2, 1) > 0) & (np.roll(m2, 2) > 0) & \
               (m2 > np.roll(m2, 1)) & (np.roll(m2, 1) < np.roll(m2, 2))
        on_b = (m3 > 0) & (np.roll(m3, 1) > 0) & (np.roll(m3, 2) > 0) & (m3 > np.roll(m3, 1)) & (np.roll(m3, 1) < np.roll(m3, 2))
    for t in range(W, n):
        def A(arr, i):
            return arr[t - i + 1]

        if on_a[t]:
            j = 0
            for i in range(2, W - 1):
                if not (_poz(A(m3, i)) and _poz(A(m3, i + 1)) and _poz(A(m2, i)) and _poz(A(m2, i + 1))):
                    break
                if A(m1, i) < 0 and A(m1, i + 1) > 0:
                    j = i + 1
                    break
            if j == 0:
                continue
            for i in range(j, W - 2):
                if not all(_poz(A(x, i + d)) for x in (m3, m2) for d in range(3)):
                    break
                if A(m2, i) < A(m2, i + 1) and A(m2, i + 1) > A(m2, i + 2):
                    out[t] = True
                    break
        elif on_b[t]:
            j = k = 0
            for i in range(2, W - 1):
                if not (_poz(A(m3, i)) and _poz(A(m3, i + 1))):
                    break
                if A(m2, i) < 0 and A(m2, i + 1) > 0:
                    j = i + 1
                    break
            if j == 0:
                continue
            for i in range(j, W - 1):
                if not all(_poz(x) for x in (A(m3, i), A(m3, i + 1), A(m2, i), A(m2, i + 1))):
                    break
                if A(m1, i) < 0 and A(m1, i + 1) > 0:
                    k = i + 1
                    break
            if k == 0:
                continue
            for i in range(k, W - 2):
                if not all(_poz(A(x, i + d)) for x in (m3, m2) for d in range(3)):
                    break
                if A(m2, i) < A(m2, i + 1) and A(m2, i + 1) > A(m2, i + 2):
                    out[t] = True
                    break
    return out
