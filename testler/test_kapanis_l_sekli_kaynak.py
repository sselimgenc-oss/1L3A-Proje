"""L biçimi kaynak profilinin sinyal, stop ve gelecekten bağımsızlık denetimi."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji.kapanis.l_sekli_kaynak import LSekliKaynak


def _mumlar() -> pd.DataFrame:
    n = 140
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    close = np.full(n, 100.0)
    opening = close.copy()
    high = close + 0.5
    low = close - 0.5
    high[120] = 110.0
    low[132] = 95.0
    close[136:139] = opening[136:139] = 99.0
    high[136:139], low[136:139] = 99.5, 98.5
    opening[139], close[139], high[139], low[139] = 99.0, 102.0, 103.0, 98.5
    return pd.DataFrame(
        {"acilis": opening, "yuksek": high, "dusuk": low,
         "kapanis": close, "hacim": np.full(n, 1000.0)},
        index=idx,
    )


def test_l_sekli_sinyal_stop_ve_kaynak_yarim_cikis() -> None:
    m = _mumlar()
    strateji = LSekliKaynak()
    sinyal = strateji.sinyaller(m)
    assert sinyal["yon"].iloc[-1] == 1
    assert sinyal["stop"].iloc[-1] == 102.0 * 0.95
    assert sinyal["hedef"].iloc[-1] == 102.0 * 1.10
    assert strateji.cikis_ayarlari.kismi == ((0.6, 0.5),)
    assert strateji.cikis_ayarlari.basabas_r_esigi == 0.6


def test_l_sekli_gelecek_mumlerinden_etkilenmez() -> None:
    m = _mumlar()
    ilk = LSekliKaynak().sinyaller(m)
    gelecek = m.iloc[-1:].copy()
    gelecek.index = gelecek.index + pd.Timedelta(hours=1)
    gelecek[["acilis", "yuksek", "dusuk", "kapanis"]] = [200.0, 250.0, 190.0, 220.0]
    sonra = LSekliKaynak().sinyaller(pd.concat([m, gelecek]))
    pd.testing.assert_frame_equal(ilk, sonra.iloc[:-1])
