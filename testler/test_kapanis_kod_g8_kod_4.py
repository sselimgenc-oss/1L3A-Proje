"""g8_kod_4: her sınıf sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import kod_g8_kod_4 as kod
from motor.strateji.kapanis.kod_g8_kod_4 import KODLANAMADI, SINIFLAR, VARYANTLAR


def _mumlar(n=900, tohum=11) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.normal(0.0006, 0.025, n)
    fiyat = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / 35))
    acilis = np.r_[fiyat[0], fiyat[:-1]] * (1 + rng.normal(0, 0.004, n))
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    hacim = rng.lognormal(4, 0.6, n)
    hacim[rng.random(n) < 0.1] *= 6          # hacim patlamaları (397, 408)
    return pd.DataFrame({"acilis": acilis, "yuksek": np.maximum(acilis, fiyat) * 1.01,
                         "dusuk": np.minimum(acilis, fiyat) * 0.99, "kapanis": fiyat, "hacim": hacim}, index=idx)


def _kayitlar():
    return VARYANTLAR


@pytest.mark.parametrize("kayit", _kayitlar(), ids=lambda k: k["kimlik"] + "-" + k["tf"])
def test_varyant_sinyal_stop_gelecek(kayit):
    st = SINIFLAR[kayit["sinif"]](**kayit["parametreler"])
    assert st.ad == kayit["sinif"] and st.parametre_izgarasi == {} and st.cikis_var_mi()
    for tohum in range(11, 41):      # nadir kurallar (ör. 408) için kurala uygun bir sentetik seri bul
        m = _mumlar(tohum=tohum)
        s = st.sinyaller(m)
        if (s["yon"] != 0).any():
            break
    assert (s["yon"] != 0).any(), "sentetik veride sinyal üretmeli"
    # (c) stop dolu ve doğru tarafta
    for yon in (1, -1):
        sec = s["yon"] == yon
        assert s.loc[sec, "stop"].notna().all()
        if yon == 1:
            assert (s.loc[sec, "stop"] < m.loc[sec, "kapanis"]).all()
        else:
            assert (s.loc[sec, "stop"] > m.loc[sec, "kapanis"]).all()
    # (b) lookahead: k'dan sonrasını değiştir, önceki satırlar aynı kalmalı
    k = 700
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2.iloc[k:, m2.columns.get_loc(c)] *= 2.5
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 3.0
    pd.testing.assert_frame_equal(s.iloc[:k], st.sinyaller(m2).iloc[:k])


def test_kayit_butunlugu():
    kimlikler = [k["kimlik"] for k in VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler))
    kaynaklar = {k["kimlik"].rsplit("#v", 1)[0] for k in VARYANTLAR} | {k["kimlik"] for k in KODLANAMADI}
    assert len(kaynaklar) == 36 and not KODLANAMADI       # 400, 401, 416, 419 kod_g8_modul'e taşındı
    assert len(SINIFLAR) == 36 and {k["sinif"] for k in VARYANTLAR} == set(SINIFLAR)
    assert {k["tf"] for k in VARYANTLAR} <= {"15m", "1h", "4h", "1d"}      # 1w yok: haftalık satırlar 1d + ust_zaman
    assert {k["tf"] for k in VARYANTLAR if k["kimlik"].startswith(("HAM:X005:367#", "HAM:X005:384#"))} == {"1d"}


def test_s0357_hedef_16r_iki_yon():
    m = _mumlar()
    s = kod.S0357().sinyaller(m)
    for yon in (1, -1):
        g = s["yon"] == yon
        assert g.any()
        risk = (m.loc[g, "kapanis"] - s.loc[g, "stop"]).abs()
        assert np.allclose(yon * (s.loc[g, "hedef"] - m.loc[g, "kapanis"]) / risk, 1.6)


def test_s0394_stop_hedef_yuzde():
    m = _mumlar()
    s = kod.S0394().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.97)
    assert np.allclose(s.loc[g, "hedef"], m.loc[g, "kapanis"] * 1.06)


def test_s0427_yalniz_ay_sonu():
    m = _mumlar()
    s = kod.S0427().sinyaller(m)
    ay_sonu = (m.index + pd.Timedelta(days=1)).month != m.index.month
    assert not (s["yon"] != 0)[~ay_sonu].any()
    assert not s["cikis_long"][~ay_sonu].any()


def test_s0362_stop_emir_kapanisla():
    m = _mumlar()
    s = kod.S0362().sinyaller(m)
    from motor.strateji import gostergeler as g
    ema = g.ema(m["kapanis"], 9)
    al = (m["acilis"] < ema) & (m["kapanis"] > ema)
    bek = al.shift(1, fill_value=False) & (m["kapanis"] > m["yuksek"].shift(1))
    assert ((s["yon"] == 1) == bek).all()


def test_s0373_zaman_cikisi_ve_varyantlar():
    assert kod.S0373.cikis_ayarlari.zaman_cikisi_mum == 5
    v = [k for k in VARYANTLAR if k["sinif"] == "kapanis__rsi2-kesisim-s0373"]
    assert [x["parametreler"]["rsi_esik"] for x in v] == [20, 25]
    assert kod.S0408.cikis_ayarlari.zaman_cikisi_mum == 20
    assert kod.S0397.cikis_ayarlari.atr_iz_suren_k is None
    m = _mumlar()
    st = kod.S0397()
    s = st.sinyaller(m)
    assert (s["yon"] == 1).any() and callable(st.pozisyon_cikisi) and "yaklasik" not in kod.VARYANTLAR[0]
    assert len([k for k in VARYANTLAR if k["kimlik"].startswith("HAM:X005:405")]) == 4


def _haftalik_rsi_kontrol(sinif, parametre=None):
    m = _mumlar(1500, tohum=5)
    st = sinif(**(parametre or {}))
    s = st.sinyaller(m)
    ilk_gun = (m.index.dayofweek == 0)
    # haftalık kurallar yalnız Pazartesi (yeni haftanın ilk günü) sinyal üretir
    assert (s["yon"] != 0).any()
    assert ((s["yon"] != 0) <= ilk_gun).all()
    assert (s.loc[s["cikis_long"], "cikis_long"].index.dayofweek == 0).all()


def test_s0367_s0384_haftalik_1d_ust_zaman():
    _haftalik_rsi_kontrol(kod.S0367)
    _haftalik_rsi_kontrol(kod.S0384)
    # hesaplanan haftalık SMA kapanmış haftadan gelir: son (kısmi) hafta değeri etkilemez
    m = _mumlar(1500, tohum=5)
    a = kod.S0367().sinyaller(m.iloc[:1000])
    b = kod.S0367().sinyaller(m)
    pd.testing.assert_frame_equal(a.iloc[:995], b.iloc[:995])


def test_s0397_kanca_chandelier_backtest():
    m = _mumlar(1500, tohum=17)
    st = kod.S0397(rvol_min=1.0)          # sentetik veride işlem çıksın diye hacim eşiği gevşek
    r = backtest(m, st, MotorAyarlari())
    kanca = r.islemler[r.islemler["cikis_nedeni"] == "kanca"]
    assert len(kanca) >= 1
    atr = kod.g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    for _, t in kanca.iterrows():
        i = m.index.get_loc(t.cikis_zamani) - 1        # karar mumu (kapanış)
        gi = m.index.get_loc(t.giris_zamani)
        tepe = m["yuksek"].iloc[gi:i + 1].max()
        assert m["kapanis"].iloc[i] <= tepe - 3.0 * atr.iloc[i] + 1e-9
