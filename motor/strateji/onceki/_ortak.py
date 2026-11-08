"""onceki paketi için ortak yardımcılar (kendi kendine yeterli; gostergeler.py'ye ek yapılmaz)."""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import seans_son_mumu
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
    """UTC gününün son mumu ise True: kapanış anı bir sonraki UTC gününe taşıyor ya da (seanslı veride) o günün bilinen
    seans kapanışına ulaşıyor. Tanım daytrade/_ortak.seans_son_mumu (seans_saat=0) ile ortaktır; kripto davranışı aynı.
    Mum süresi yalnız geçmişten kestirilir (o ana kadarki en küçük aralık): lookahead yok."""
    return seans_son_mumu(index, 0.0)


def cerceve(index, long_ok, short_ok, stop_long, stop_short, cikis=None, zaman_cikisi_mum=None,
            cikis_long=None, cikis_short=None) -> pd.DataFrame:
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
    # Yönlü çıkış (motor: long cikis_long|cikis, short cikis_short|cikis ile kapanır).
    if cikis_long is not None:
        out["cikis_long"] = cikis_long.fillna(False).astype(bool)
    if cikis_short is not None:
        out["cikis_short"] = cikis_short.fillna(False).astype(bool)
    if zaman_cikisi_mum:
        out["zaman_cikisi_mum"] = float(zaman_cikisi_mum)
    return out
