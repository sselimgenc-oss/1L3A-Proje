"""Seanslı veride mum süresi (medyan yerine mod) ve yıllık periyot (gözlenen mum sıklığı). Kripto değişmez."""
import numpy as np
import pandas as pd
import pytest

from motor.backtest.metrikler import YIL_SANIYE, yillik_periyot
from motor.strateji.htf import ust_zaman
from motor.strateji.seans_takvimi import mum_suresi

NY = "America/New_York"


def _hisse_4h(bas="2023-01-02", bit="2023-12-29"):
    """NY 09:00'a hizalı hisse 4h: 09:00 ve 13:00 NY mumları (farklar 4s / 20s / 68s)."""
    z = []
    for g in pd.bdate_range(bas, bit):
        for saat in ("09:00", "13:00"):
            z.append(pd.Timestamp(f"{g.date()} {saat}", tz=NY).tz_convert("UTC"))
    return pd.DatetimeIndex(z)


def _mumlar(idx):
    k = 100 + np.cumsum(np.random.default_rng(0).normal(0, 1, len(idx)))
    return pd.DataFrame({"acilis": k, "yuksek": k + 1, "dusuk": k - 1, "kapanis": k, "hacim": 1.0}, index=idx)


def test_mum_suresi_hisse_4h_mod():
    idx = _hisse_4h()
    assert mum_suresi(idx) == pd.Timedelta(hours=4)


@pytest.mark.parametrize("adim", ["5min", "1h", "4h", "1D"])
def test_mum_suresi_kripto_medyanla_ayni(adim):
    idx = pd.date_range("2024-01-01", "2024-06-01", freq=adim, tz="UTC")
    idx = idx.delete(np.arange(10, len(idx), 37))                      # delikli veri
    assert mum_suresi(idx) == pd.Series(idx).diff().median()
    assert pd.isna(mum_suresi(idx[:1]))


def test_hisse_4h_gunluk_ust_tf_calisir():
    m = _mumlar(_hisse_4h())
    u = ust_zaman(m, "1d", lambda u: u[["kapanis"]])
    assert u["kapanis"].notna().mean() > 0.99
    # nedensel: gün d'nin kapanışı en erken ertesi günün mumunda görünür
    assert (u["kapanis"].iloc[2:].to_numpy() != m["kapanis"].iloc[2:].to_numpy()).any()


def test_motor_cikis_zamani_hisse_4h():
    from motor.backtest.motor import backtest
    from motor.strateji.temel import Strateji

    class Ac(Strateji):
        ad = "test_ac"
        stil = "swing"

        def cikis_var_mi(self):
            return True

        def sinyaller(self, mumlar):
            n = len(mumlar)
            yon = np.zeros(n, dtype=int)
            yon[::6] = 1
            return pd.DataFrame({"yon": yon, "stop": mumlar["kapanis"] - 1e-6, "hedef": np.nan,
                                 "cikis": False}, index=mumlar.index)

    m = _mumlar(_hisse_4h())
    isl = backtest(m, Ac()).islemler
    stop = isl[isl["cikis_nedeni"] == "stop"]
    assert len(stop) > 0
    # stop mum içinde: çıkış zamanı = o mumun açılışı + 4 saat (eskiden +20 saat)
    acilis = pd.DatetimeIndex(stop["cikis_zamani"]) - pd.Timedelta(hours=4)
    assert acilis.isin(m.index).all()


def test_yillik_periyot_gozlenen():
    kripto = pd.date_range("2024-01-01", "2025-01-01", freq="1h", tz="UTC")
    assert yillik_periyot(kripto) == pytest.approx(YIL_SANIYE / 3600, rel=1e-12)
    hisse = pd.DatetimeIndex([t for g in pd.bdate_range("2023-01-02", "2024-12-31")
                              for t in pd.date_range(pd.Timestamp(f"{g.date()} 09:00", tz=NY), periods=7, freq="1h")])
    assert 1700 < yillik_periyot(hisse) < 1850                                # ~261 gün x 7 mum
    assert yillik_periyot(kripto[:1]) != yillik_periyot(kripto[:1])         # NaN
