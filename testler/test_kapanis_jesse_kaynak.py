"""Kapanış turu Jesse kuralları: sentetik mumlarla kaynak mantığı ve nedensellik."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis.jesse_kaynak import DonchianS0002, MacdEmaS0005


def mumlar() -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=400, freq="h", tz="UTC")
    fiyat = np.r_[np.linspace(100, 120, 210), np.linspace(120, 145, 100),
                  np.linspace(145, 110, 90)]
    fiyat[220] += 4.0
    fiyat[330] -= 4.0
    return pd.DataFrame({"acilis": fiyat, "yuksek": fiyat + 0.5,
                         "dusuk": fiyat - 0.5, "kapanis": fiyat,
                         "hacim": 100.0}, index=idx)


@pytest.mark.parametrize("sinif", [DonchianS0002, MacdEmaS0005])
def test_sinyal_stop_ve_gelecek_bagimsizligi(sinif):
    m = mumlar()
    st = sinif()
    s = st.sinyaller(m)
    assert (s["yon"] == 1).any()
    assert (s["yon"] == -1).sum() == 0
    giris = s["yon"] == 1
    assert s.loc[giris, "stop"].notna().all()
    assert (s.loc[giris, "stop"] < m.loc[giris, "kapanis"]).all()
    assert st.parametre_izgarasi == {}
    m2 = m.copy()
    m2.loc[m2.index[350]:, ["acilis", "yuksek", "dusuk", "kapanis"]] *= 3.0
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:349], s2.iloc[:349])


def test_donchian_mevcut_mum_haric_ve_alt_kanal_cikisi():
    m = mumlar()
    s = DonchianS0002().sinyaller(m)
    assert s.loc[m.index[220], "yon"] == 1
    assert s.loc[m.index[330], "cikis_long"]


def test_macd_durum_tetikler_kesisim_olayina_indirgenmez():
    s = MacdEmaS0005().sinyaller(mumlar())
    assert (s["yon"] == 1).sum() > 1
    assert s["cikis_long"].any()
