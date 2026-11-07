"""D11-i grubu için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır.

  aroon_yukari, aroon_asagi, williams_r, obv, ewo_yuzde, vwap_bant, ust_tf (HTF yardımcısı)
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji.htf import ust_zaman


def _aroon(seri: pd.Series, n: int, tepe: bool) -> pd.Series:
    """Aroon: son n+1 mum penceresinde en yüksek (en düşük) değerin kaç mum önce olduğu -> 100 x (n - mum) / n."""
    n = int(n)
    x = seri.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n + 1:
        w = sliding_window_view(x, n + 1)[:, ::-1]   # ters: indeks 0 = en yeni mum
        gecerli = ~np.isnan(w).any(axis=1)
        w = np.where(np.isnan(w), 0.0, w)
        mum = (w.argmax(axis=1) if tepe else w.argmin(axis=1))   # ilk eşleşme = en yeni
        out[n:] = np.where(gecerli, 100.0 * (n - mum) / n, np.nan)
    return pd.Series(out, index=seri.index)


def aroon_yukari(yuksek: pd.Series, n: int = 14) -> pd.Series:
    return _aroon(yuksek, n, True)


def aroon_asagi(dusuk: pd.Series, n: int = 14) -> pd.Series:
    return _aroon(dusuk, n, False)


def williams_r(yuksek, dusuk, kapanis, n: int = 14) -> pd.Series:
    """Williams %R (-100..0)."""
    hh = yuksek.rolling(n, min_periods=n).max()
    ll = dusuk.rolling(n, min_periods=n).min()
    return -100.0 * (hh - kapanis) / (hh - ll).where(hh != ll)


def obv(kapanis: pd.Series, hacim: pd.Series) -> pd.Series:
    """On-Balance Volume (kümülatif; mutlak değeri değil değişimi kullanılır)."""
    yon = np.sign(kapanis.diff()).fillna(0.0)
    return (yon * hacim).cumsum()


def ewo_yuzde(yuksek, dusuk, kapanis, hizli: int = 5, yavas: int = 35) -> pd.Series:
    """Elliott Wave Oscillator YÜZDE biçiminde: (EMA(hizli) - EMA(yavas)) / kapanış x 100 (mutlak fiyat birimi yerine)."""
    e1 = kapanis.ewm(span=hizli, adjust=False, min_periods=hizli).mean()
    e2 = kapanis.ewm(span=yavas, adjust=False, min_periods=yavas).mean()
    return (e1 - e2) / kapanis * 100.0


def vwap_bant(yuksek, dusuk, kapanis, hacim, n: int = 20, sapma: float = 1.0) -> pd.DataFrame:
    """Yuvarlanan (seanssız) VWAP(n) ve hacim ağırlıklı standart sapma bantları: orta = Σ(tp x hacim)/Σhacim."""
    tp = (yuksek + dusuk + kapanis) / 3.0
    hv = hacim.rolling(n, min_periods=n).sum().where(lambda s: s > 0)
    vw = (tp * hacim).rolling(n, min_periods=n).sum() / hv
    var = ((tp * tp * hacim).rolling(n, min_periods=n).sum() / hv - vw * vw).clip(lower=0.0)
    sd = np.sqrt(var)
    return pd.DataFrame({"orta": vw, "alt": vw - sapma * sd, "ust": vw + sapma * sd})


def ust_tf(mumlar: pd.DataFrame, aralik: str, fonk) -> pd.DataFrame:
    """Üst zaman dilimi özeti (yalnız kapanmış HTF mumlarından; kapanış anından itibaren kullanılabilir)."""
    return ust_zaman(mumlar, aralik, fonk)
