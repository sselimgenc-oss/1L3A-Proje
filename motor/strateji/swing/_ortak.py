"""Swing gösterge stratejileri için küçük ortak yardımcılar."""
import numpy as np
import pandas as pd


def sinyal_cercevesi(index, long_ok, short_ok, long_stop, short_stop,
                     hedef_long=None, hedef_short=None, cikis=None) -> pd.DataFrame:
    """yon/stop/hedef/cikis çerçevesini kurar. Girdiler boolean/float Series (aynı indeks)."""
    long_ok = long_ok.fillna(False).astype(bool) & long_stop.notna()
    short_ok = short_ok.fillna(False).astype(bool) & short_stop.notna() & ~long_ok
    yon = pd.Series(0, index=index, dtype="int64")
    yon[long_ok] = 1
    yon[short_ok] = -1
    stop = pd.Series(np.nan, index=index)
    stop[long_ok] = long_stop[long_ok]
    stop[short_ok] = short_stop[short_ok]
    hedef = pd.Series(np.nan, index=index)
    if hedef_long is not None:
        hedef[long_ok] = hedef_long[long_ok]
    if hedef_short is not None:
        hedef[short_ok] = hedef_short[short_ok]
    if cikis is None:
        cikis = pd.Series(False, index=index)
    return pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef,
                         "cikis": cikis.fillna(False).astype(bool)})
