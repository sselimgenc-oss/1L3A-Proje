"""V2'de 1d üst-TF hatası alan dört kodun geçerli TF ile sinyal sözleşmesi."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji import kayit


@pytest.mark.parametrize(
    ("ad", "tf"),
    [
        ("dis__norn-weave-thurisaz", "4h"),
        ("dis__shm-wma", "4h"),
        ("onceki__4s-kirilim", "4h"),
        ("onceki__kgt", "1h"),
    ],
)
def test_v2_ust_tf_hatasi_gecerli_tf_ile_olmaz(ad: str, tf: str) -> None:
    n = 1100
    idx = pd.date_range("2022-01-01", periods=n, freq=tf, tz="UTC")
    rastgele = np.random.default_rng(23)
    fiyat = 100 + np.cumsum(rastgele.normal(0, 1, n))
    mumlar = pd.DataFrame(
        {
            "acilis": fiyat,
            "yuksek": fiyat + 1.2,
            "dusuk": fiyat - 1.2,
            "kapanis": fiyat + rastgele.normal(0, 0.1, n),
            "hacim": np.full(n, 1000.0),
            "quote_hacim": np.full(n, 100000.0),
        },
        index=idx,
    )
    sinyaller = kayit.al(ad)().sinyaller(mumlar)
    assert len(sinyaller) == n
    giris = sinyaller["yon"] != 0
    assert sinyaller.loc[giris, "stop"].notna().all()
