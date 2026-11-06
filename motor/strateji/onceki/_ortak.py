"""onceki paketi için ortak yardımcılar (kendi kendine yeterli; gostergeler.py'ye ek yapılmaz)."""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.htf import ust_zaman


def hacim_serisi(mumlar: pd.DataFrame) -> pd.Series:
    """Hacim: varsa quote_hacim (orijinal algo-sg quote_volume kullanır), yoksa hacim."""
    return mumlar["quote_hacim"] if "quote_hacim" in mumlar.columns else mumlar["hacim"]


def kaynak_suresi(index: pd.DatetimeIndex) -> pd.Timedelta:
    return pd.Series(index).diff().median()


def ust_atr(mumlar: pd.DataFrame, aralik: str, periyot: int = 14) -> pd.Series:
    """Üst TF (kapanmış mumlardan) ATR'si, mumlarla aynı indekse hizalı. Mum TF'si zaten >= aralik ise
    doğrudan kendi ATR'si kullanılır."""
    from motor.veri.depo import aralik_suresi
    if len(mumlar) >= 2 and aralik_suresi(aralik) <= kaynak_suresi(mumlar.index):
        return g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], periyot)
    return ust_zaman(mumlar, aralik,
                     lambda u: g.atr(u["yuksek"], u["dusuk"], u["kapanis"], periyot))


def heikin_ashi(acilis: pd.Series, yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series):
    """(ha_acilis, ha_kapanis). ha_acilis özyinelemelidir: serinin başından itibaren hesaplanır (nedensel)."""
    hc = (acilis + yuksek + dusuk + kapanis) / 4.0
    o, c, n = acilis.to_numpy(float), hc.to_numpy(float), len(acilis)
    ho = np.empty(n)
    if n:
        ho[0] = (o[0] + kapanis.to_numpy(float)[0]) / 2.0
        for i in range(1, n):
            ho[i] = (ho[i - 1] + c[i - 1]) / 2.0
    return pd.Series(ho, index=acilis.index), hc


def olay(kosul: pd.Series) -> pd.Series:
    """Koşulun ilk doğru olduğu mum (önceki mumda yanlıştı)."""
    kosul = kosul.fillna(False).astype(bool)
    return kosul & ~kosul.shift(1, fill_value=False)


def gun_sonu_maskesi(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun KAPANIŞ anı bir sonraki UTC gününe denk geliyorsa True (= UTC gününün son mumu).
    Mum süresi yalnız geçmişten kestirilir (o ana kadarki en küçük aralık): lookahead yok."""
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kapanis = index + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    return (kapanis.floor("D") != index.floor("D")) & gecerli


def yone_gore_cikis(yon: pd.Series, cikis_long: pd.Series, cikis_short: pd.Series) -> pd.Series:
    """`cikis` yönsüz bir bool olduğundan: pozisyon yönü = son giriş sinyalinin yönü kabul edilir.
    (Pozisyon açıkken gelen ters yönlü sinyal motorca yok sayılır ama burada yönü değiştirir; nadir bir
    yaklaşıklık. Yalnız-long kullanımda hiçbir etkisi yoktur.)"""
    son = yon.where(yon != 0).ffill()
    cl = cikis_long.fillna(False).astype(bool)
    cs = cikis_short.fillna(False).astype(bool)
    return (((son == 1) & cl) | ((son == -1) & cs)).astype(bool)


def cerceve(index, long_ok, short_ok, stop_long, stop_short, cikis=None, zaman_cikisi_mum=None) -> pd.DataFrame:
    """yon/stop/hedef/cikis çerçevesi. Stop NaN veya yanlış tarafta ise sinyal düşer (kapanışa göre
    kontrol çağıran tarafta yapılır: stop_long < kapanış varsayılır; burada yalnız NaN elenir)."""
    long_ok = long_ok.fillna(False).astype(bool) & stop_long.notna()
    short_ok = short_ok.fillna(False).astype(bool) & stop_short.notna() & ~long_ok
    yon = pd.Series(0, index=index, dtype="int64")
    yon[long_ok] = 1
    yon[short_ok] = -1
    stop = pd.Series(np.nan, index=index)
    stop[long_ok] = stop_long[long_ok]
    stop[short_ok] = stop_short[short_ok]
    cik = pd.Series(False, index=index) if cikis is None else cikis.fillna(False).astype(bool)
    out = pd.DataFrame({"yon": yon, "stop": stop, "hedef": np.nan, "cikis": cik})
    if zaman_cikisi_mum:
        out["zaman_cikisi_mum"] = float(zaman_cikisi_mum)
    return out
