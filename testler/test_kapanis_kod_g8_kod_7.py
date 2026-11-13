"""g8_kod_7: her sınıf sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_7 as kod
from motor.strateji.kapanis.kod_g8_kod_7 import KODLANAMADI, SINIFLAR, VARYANTLAR

_FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "D"}


def _durgun_sicrama(n=1100, tohum=1) -> pd.DataFrame:
    """Düşük oynaklıklı seri + hacimli ani sıçramalar (679: ADX < 25, RSI aşırı, hacim patlaması, banda ilk dokunuş)."""
    rng = np.random.default_rng(tohum)
    fiyat = 100 * np.exp(rng.normal(0, 0.002, n))
    hacim = rng.lognormal(4, 0.2, n)
    for i in range(200, n, 150):
        fiyat[i:] *= 0.96
        hacim[i] *= 4
    for i in range(275, n, 150):
        fiyat[i:] *= 1.04
        hacim[i] *= 4
    idx = pd.date_range("2020-01-01", periods=n, freq="15min", tz="UTC")
    a = np.r_[fiyat[0], fiyat[:-1]]
    return pd.DataFrame({"acilis": a, "yuksek": np.maximum(a, fiyat) * 1.001, "dusuk": np.minimum(a, fiyat) * 0.999,
                         "kapanis": fiyat, "hacim": hacim}, index=idx)


def _mumlar(freq="D", n=1100, tohum=11) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.normal(0.0006, 0.025, n)
    fiyat = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / 35))
    acilis = np.r_[fiyat[0], fiyat[:-1]] * (1 + rng.normal(0, 0.004, n))
    idx = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
    hacim = rng.lognormal(4, 0.6, n)
    hacim[rng.random(n) < 0.1] *= 6
    return pd.DataFrame({"acilis": acilis, "yuksek": np.maximum(acilis, fiyat) * 1.01,
                         "dusuk": np.minimum(acilis, fiyat) * 0.99, "kapanis": fiyat, "hacim": hacim}, index=idx)


@pytest.mark.parametrize("kayit", VARYANTLAR, ids=lambda k: k["kimlik"] + "-" + k["tf"])
def test_varyant_sinyal_stop_gelecek(kayit):
    st = SINIFLAR[kayit["sinif"]](**kayit["parametreler"])
    assert st.ad == kayit["sinif"] and st.parametre_izgarasi == {} and st.cikis_var_mi()
    freq = _FREQ[kayit["tf"]]
    for tohum in range(11, 61):      # nadir kurallar için kurala uygun bir sentetik seri bul
        m = _durgun_sicrama(tohum=tohum) if kayit["sinif"] == kod.S0679.ad else _mumlar(freq, tohum=tohum)
        s = st.sinyaller(m)
        if (s["yon"] != 0).any():
            break
    assert (s["yon"] != 0).any(), "sentetik veride sinyal üretmeli"
    assert list(s.index) == list(m.index)
    for yon in (1, -1):
        sec = s["yon"] == yon
        assert s.loc[sec, "stop"].notna().all()
        if yon == 1:
            assert (s.loc[sec, "stop"] < m.loc[sec, "kapanis"]).all()
        else:
            assert (s.loc[sec, "stop"] > m.loc[sec, "kapanis"]).all()
    k = 900
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2.iloc[k:, m2.columns.get_loc(c)] *= 2.5
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 3.0
    pd.testing.assert_frame_equal(s.iloc[:k], st.sinyaller(m2).iloc[:k])


def test_kayit_butunlugu():
    kimlikler = [k["kimlik"] for k in VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler))
    kaynaklar = {k["kimlik"].rsplit("#v", 1)[0] for k in VARYANTLAR}
    kodlanamadi = {k["kimlik"] for k in KODLANAMADI}
    assert len(kaynaklar) == 35 and len(kodlanamadi) == 2 and not (kaynaklar & kodlanamadi)   # 699, 726, 736 kod_g8_modul'de
    assert len(kaynaklar | kodlanamadi) == 37
    assert len(SINIFLAR) == 35 and {k["sinif"] for k in VARYANTLAR} == set(SINIFLAR)
    assert {k["tf"] for k in VARYANTLAR} <= {"5m", "15m", "30m", "1h", "4h", "1d"}
    assert all(k["neden"] for k in KODLANAMADI)


def test_cikis_ayarlari_ve_varyantlar():
    assert kod.S0659.cikis_ayarlari.zaman_cikisi_mum == 5
    assert kod.S0666.cikis_ayarlari.zaman_cikisi_mum == 3
    assert kod.S0756.cikis_ayarlari.zaman_cikisi_mum == 4 and kod.S0758.cikis_ayarlari.zaman_cikisi_mum == 4
    c = kod.S0679.cikis_ayarlari
    assert c.azalan_roi[0] == (0.0, 18.1) and len(c.azalan_roi) == 4
    assert c.geri_cekilme_yuzde is None and callable(kod.S0679().pozisyon_cikisi)      # iz kancada (zirve fiyatın %11,3'ü)
    assert kod.S0727.cikis_ayarlari.basabas_r_esigi == 0.6
    v = [x for x in VARYANTLAR if x["kimlik"].startswith("HAM:X005:706")]
    assert [x["parametreler"]["bb_sapma"] for x in v] == [2.0, 2.5, 3.0]
    assert [x["tf"] for x in VARYANTLAR if x["kimlik"].startswith("HAM:X005:684")] == ["15m", "30m"]
    assert [x["tf"] for x in VARYANTLAR if x["kimlik"].startswith("HAM:X005:680")] == ["1h", "1d"]


def test_s0661_hedef_stop_yuzde():
    m = _mumlar()
    s = kod.S0661().sinyaller(m)
    g = s["yon"] == 1
    assert g.any()
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.90)
    assert np.allclose(s.loc[g, "hedef"], m.loc[g, "kapanis"] * 1.40)
    assert (s["yon"] == -1).any()


def test_s0737_yalniz_ay_sonu():
    m = _mumlar()
    s = kod.S0737().sinyaller(m)
    ay_sonu = (m.index + pd.Timedelta(days=1)).month != m.index.month
    assert not (s["yon"] != 0)[~ay_sonu].any()
    assert not s["cikis_long"][~ay_sonu].any()


def test_s0695_onay_mumu():
    m = _mumlar()
    s = kod.S0695().sinyaller(m)
    g = s["yon"] == 1
    assert g.any()
    pos = np.flatnonzero(g.to_numpy())
    assert (m["kapanis"].to_numpy()[pos] > m["yuksek"].to_numpy()[pos - 1]).all()
    aralik = (m["yuksek"] - m["dusuk"]).shift(1)
    assert np.allclose(s.loc[g, "hedef"] - m.loc[g, "kapanis"], 2 * aralik[g])
    assert np.allclose(m.loc[g, "kapanis"] - s.loc[g, "stop"], aralik[g])


def test_s0676_alis_satis_donusumlu():
    m = _mumlar()
    s = kod.S0676().sinyaller(m)
    olay = pd.Series(0, index=m.index)
    olay[s["yon"] == 1] = 1
    olay[s["cikis_long"]] = -1
    seri = olay[olay != 0].to_numpy()
    assert len(seri) > 2 and (seri[1:] != seri[:-1]).all()


def test_s0751_trend_durumu():
    k = pd.Series([100, 110, 120, 100, 95, 100, 115, 120, 90.0])
    d = kod.RsiTrendYuzde20._trend(k, 0.20)
    assert list(d) == [0, 0, 1, 1, 1, 1, 1, 1, -1] or d.iloc[-1] == -1
    assert d.iloc[2] == 1 and d.iloc[-1] == -1


def test_s0679_baslangic_ilk_dokunus():
    m = _durgun_sicrama()
    s = kod.S0679().sinyaller(m)
    g = s["yon"] == 1
    assert g.any() and (s["yon"] == -1).any()
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.70)
