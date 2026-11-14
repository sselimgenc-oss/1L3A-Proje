"""K2 kaynak sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop var."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis.k2_kaynak import (
    VMA_KURALLARI, ArgusGizliBogaD3, DonchianEma2RS0083, FlipperS0879, IchimokuC4Arsiv, VmaBantKaynak)


def _mumlar(n=700, tohum=7) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    fiyat = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.02, n)) + 0.4 * np.sin(t / 40))
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"acilis": fiyat, "yuksek": fiyat * 1.01, "dusuk": fiyat * 0.99,
                         "kapanis": fiyat, "hacim": 100.0}, index=idx)


def _siniflar():
    yield DonchianEma2RS0083()
    yield FlipperS0879()
    for s, l, b in VMA_KURALLARI:
        yield VmaBantKaynak(s=s, l=l, b=b)
    yield IchimokuC4Arsiv()
    yield ArgusGizliBogaD3()


@pytest.mark.parametrize("st", list(_siniflar()), ids=lambda s: f"{s.ad}-{s.parametreler.get('s', '')}"
                         f"-{s.parametreler.get('l', '')}-{s.parametreler.get('b', '')}")
def test_sinyal_stop_gelecek(st):
    m = _mumlar()
    s = st.sinyaller(m)
    giris = s["yon"] == 1
    assert giris.any(), "sentetik veride sinyal üretmeli"
    assert (s["yon"] == -1).sum() == 0
    assert s.loc[giris, "stop"].notna().all()
    assert (s.loc[giris, "stop"] < m.loc[giris, "kapanis"]).all()
    assert st.cikis_var_mi()
    k = 600
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])


def test_s0083_hedef_2r_ve_ilk_kirilim():
    m = _mumlar()
    s = DonchianEma2RS0083().sinyaller(m)
    g = s["yon"] == 1
    risk = m.loc[g, "kapanis"] - s.loc[g, "stop"]
    assert np.allclose((s.loc[g, "hedef"] - m.loc[g, "kapanis"]) / risk, 2.0)
    assert not (g & g.shift(1, fill_value=False)).any()  # art arda iki giriş yok (olay, durum değil)


def test_flipper_zigzag_20_yuzde():
    kap = np.array([100, 95, 100, 115, 119, 130, 120, 110, 104.0, 90, 100, 112.0])
    yuk, dus = kap + 1, kap - 1
    giris, cikis, _ = FlipperS0879.zigzag(kap, yuk, dus, 0.20)
    # dip=94 -> 94*1.2=112.8: ilk kapanış >= bu 115 (t=3); tepe 131 -> 104.8: t=8 (104) çıkış
    assert list(np.flatnonzero(giris)) == [3, 11] or list(np.flatnonzero(giris))[0] == 3
    assert np.flatnonzero(cikis)[0] == 8


def test_vma_bant_kurali():
    m = _mumlar()
    a = VmaBantKaynak(s=1, l=50, b=0.01).sinyaller(m)
    sma = m["kapanis"].rolling(50).mean()
    assert ((a["yon"] == 1) == (m["kapanis"] > sma * 1.01).fillna(False) & a["stop"].notna()).all()
    assert (a["cikis_long"] == (m["kapanis"] < sma * 0.99).fillna(False)).all()
    assert len(VMA_KURALLARI) == 10 and len(set(VMA_KURALLARI)) == 10


def test_argus_hedef_15r_ve_sure():
    m = _mumlar()
    st = ArgusGizliBogaD3()
    s = st.sinyaller(m)
    g = s["yon"] == 1
    risk = m.loc[g, "kapanis"] - s.loc[g, "stop"]
    assert np.allclose((s.loc[g, "hedef"] - m.loc[g, "kapanis"]) / risk, 1.5)
    assert st.cikis_ayarlari.zaman_cikisi_mum == 10
    assert IchimokuC4Arsiv().cikis_ayarlari.zaman_cikisi_mum == 250
