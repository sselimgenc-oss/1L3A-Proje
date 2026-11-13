"""g8_kod_8: her sınıf sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_8 as kod
from motor.strateji.kapanis.kod_g8_kod_8 import KODLANAMADI, SINIFLAR, VARYANTLAR

_FREQ = {"5m": "5min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "D"}
_VOL = {"5m": 0.0025, "30m": 0.005, "1h": 0.007, "4h": 0.014, "1d": 0.025}
_N = {"5m": 3000, "30m": 2000, "1h": 1500, "4h": 1200, "1d": 900}


def _mumlar(tf="1d", tohum=11, carpan=1.0) -> pd.DataFrame:
    n = _N[tf]
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.normal(0.0006, _VOL[tf] * carpan, n)
    fiyat = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / 35) * (_VOL[tf] / 0.025) ** 0.5)
    acilis = np.r_[fiyat[0], fiyat[:-1]] * (1 + rng.normal(0, _VOL[tf] / 6, n))
    idx = pd.date_range("2020-01-01", periods=n, freq=_FREQ[tf], tz="UTC")
    hacim = rng.lognormal(4, 0.6, n)
    return pd.DataFrame({"acilis": acilis, "yuksek": np.maximum(acilis, fiyat) * (1 + _VOL[tf] / 2.5),
                         "dusuk": np.minimum(acilis, fiyat) * (1 - _VOL[tf] / 2.5), "kapanis": fiyat, "hacim": hacim},
                        index=idx)


def _sinyalli(st, tf):
    for carpan in (1.0, 1.6, 2.5):
        for tohum in range(11, 61):
            m = _mumlar(tf, tohum, carpan)
            s = st.sinyaller(m)
            if (s["yon"] != 0).any():
                return m, s
    return m, s


@pytest.mark.parametrize("kayit", VARYANTLAR, ids=lambda k: k["kimlik"] + "-" + k["tf"])
def test_varyant_sinyal_stop_gelecek(kayit):
    st = SINIFLAR[kayit["sinif"]](**kayit["parametreler"])
    assert st.ad == kayit["sinif"] and st.parametre_izgarasi == {} and st.cikis_var_mi()
    m, s = _sinyalli(st, kayit["tf"])
    assert (s["yon"] != 0).any(), "sentetik veride sinyal üretmeli"
    for yon in (1, -1):
        sec = s["yon"] == yon
        assert s.loc[sec, "stop"].notna().all()
        if yon == 1:
            assert (s.loc[sec, "stop"] < m.loc[sec, "kapanis"]).all()
        else:
            assert (s.loc[sec, "stop"] > m.loc[sec, "kapanis"]).all()
    # lookahead: k'dan sonrasını değiştir, önceki satırlar aynı kalmalı
    k = int(len(m) * 0.78)
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2.iloc[k:, m2.columns.get_loc(c)] *= 2.5
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 3.0
    pd.testing.assert_frame_equal(s.iloc[:k], st.sinyaller(m2).iloc[:k])


def test_kayit_butunlugu():
    kimlikler = [k["kimlik"] for k in VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler))
    kaynaklar = {k["kimlik"].rsplit("#v", 1)[0] for k in VARYANTLAR} | {k["kimlik"] for k in KODLANAMADI}
    assert len(kaynaklar) == 39 and [k["kimlik"] for k in KODLANAMADI] == ["HAM:X005:863"]    # 879 kod_g8_modul'de
    assert len(SINIFLAR) == 38 and {k["sinif"] for k in VARYANTLAR} == set(SINIFLAR)
    assert len([k for k in VARYANTLAR if k["kimlik"].startswith("HAM:X008:L15#2")]) == 6
    assert len([k for k in VARYANTLAR if k["kimlik"].startswith("HAM:X005:802#")]) == 2
    assert {k["tf"] for k in VARYANTLAR} <= {"5m", "30m", "1h", "4h", "1d"}


def test_cikis_modulleri_yuzde_ve_sure():
    c = kod.S0816().cikis_ayarlari
    assert c.azalan_roi == ((0.0, 3.0),) and c.zaman_cikisi_mum == 4
    c = kod.S0817().cikis_ayarlari
    assert c.azalan_roi == ((0.0, 4.0),) and c.zaman_cikisi_mum == 2
    assert kod.S0819().cikis_ayarlari.azalan_roi == ((0.0, 30.0),)
    assert kod.S0764().cikis_ayarlari.zaman_cikisi_mum == 5
    assert kod.S0790().cikis_ayarlari.zaman_cikisi_mum == 14
    assert kod.S0793().cikis_ayarlari.zaman_cikisi_mum == 12
    assert kod.S0828().cikis_ayarlari.zaman_cikisi_mum == 365
    assert kod.S0830().cikis_ayarlari.zaman_cikisi_mum is None
    assert kod.S0840().cikis_ayarlari.atr_iz_suren_k == 3.5
    assert kod.S0812().cikis_ayarlari.azalan_roi == ()


def test_s0812_hedef_stop_yuzde():
    st = kod.S0812()
    m, s = _sinyalli(st, "30m")
    for yon in (1, -1):
        g = s["yon"] == yon
        assert g.any()
        assert np.allclose(s.loc[g, "hedef"], m.loc[g, "kapanis"] * (1 + 0.25 * yon))
        assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - 0.05 * yon))


def test_s0828_s0830_ayni_sinyal_farkli_sure():
    m = _mumlar("1d", 11)
    pd.testing.assert_frame_equal(kod.S0828().sinyaller(m), kod.S0830().sinyaller(m))


def test_s0790_histerezis():
    m = _mumlar("1d", 11)
    s = kod.S0790().sinyaller(m)
    idx = np.flatnonzero((s["yon"] != 0).to_numpy())
    assert len(idx) >= 2
    # aynı yönde iki sinyal arasında RSI nötr bölgeye (reset) dönmüş olmalı
    from motor.strateji import gostergeler as g
    r = g.rsi(m["kapanis"], 14).to_numpy()
    for a, b in zip(idx[:-1], idx[1:]):
        if s["yon"].iloc[a] == s["yon"].iloc[b] == 1:
            assert (r[a + 1:b + 1] > 35).any()
        if s["yon"].iloc[a] == s["yon"].iloc[b] == -1:
            assert (r[a + 1:b + 1] < 65).any()


def test_s0780_gun_ici_aralik_gelecek_yok():
    m = _mumlar("1h", 11)
    s = kod.S0780().sinyaller(m)
    assert (s["yon"] != 0).sum() > 10
    # ilk 4 günde (HH/LL için geçmiş yok) sinyal olmamalı
    assert (s["yon"].iloc[:4 * 24] == 0).all()
