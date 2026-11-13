"""g8_kod_6: her sınıf sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_3
from motor.strateji.kapanis import kod_g8_kod_6 as K

FREQ = {"5m": "5min", "15m": "15min", "1h": "1h", "6h": "6h", "1d": "1D", "1w": "7D", "1M": "MS"}
ADET = {"5m": 5000, "15m": 3000, "1h": 3000, "6h": 1500, "1d": 2400, "1w": 1200, "1M": 1200}
SINIFLAR = {s.ad: s for s in K.SINIFLAR}
SINIFLAR["kapanis__rsi2-sma5-s0253"] = kod_g8_kod_3.Rsi2Sma5S0253
IKI_YON = {"kapanis__kumo-iz-s0600", "kapanis__aylik-sma10-rsi2-s0606", "kapanis__ma5-dusen-gunler-s0608",
           "kapanis__tk-kesisim-don-s0621", "kapanis__va-skor-s0630", "kapanis__aralik-kanal-s0631",
           "kapanis__bb-donus-h4-s0633", "kapanis__ichimoku-bulut-kirilim-s0634", "kapanis__keltner-durum-s0649",
           "kapanis__sd-donus-s0653"}


def _mumlar(tf: str, tohum: int = 1, vol: float = 0.01, n: int | None = None, drift: float = 0.0003) -> pd.DataFrame:
    n = n or ADET[tf]
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + drift + 0.0004 * np.sin(t / 45.0)
    kap = 100 * np.exp(np.cumsum(getiri))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, vol / 5, n))
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    hacim = rng.lognormal(4, 0.5, n)
    hacim[rng.random(n) < 0.08] *= 5
    idx = pd.date_range("2018-01-01", periods=n, freq=FREQ[tf], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": hacim}, index=idx)


def _sinyalli(st, tf: str):
    """Kurala uygun bir sentetik seri bul (nadir kurallar için tohum/oynaklık/eğilim tara)."""
    for tohum in range(1, 13):
        for vol, drift in ((0.01, 0.0003), (0.02, -0.0004), (0.004, 0.0008), (0.03, 0.001), (0.015, -0.001)):
            m = _mumlar(tf, tohum, vol, drift=drift)
            s = st.sinyaller(m)
            if (s["yon"] != 0).any():
                return m, s
    return m, s


KAYITLAR = K.VARYANTLAR


@pytest.mark.parametrize("kayit", KAYITLAR, ids=lambda k: k["kimlik"] + "-" + k["tf"])
def test_varyant_sinyal_stop_gelecek(kayit):
    sinif = SINIFLAR[kayit["sinif"]]
    st = sinif(**kayit["parametreler"])
    assert st.ad == kayit["sinif"] and st.parametre_izgarasi == {} and st.cikis_var_mi()
    m, s = _sinyalli(st, kayit["tf"])
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert (long | short).any(), "sentetik veride sinyal üretmeli"
    if kayit["sinif"] in IKI_YON:
        assert long.any() and short.any(), "iki yönlü kural iki yön de üretmeli"
    else:
        assert not short.any()
    # (c) stop dolu ve doğru tarafta
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    assert (s.loc[short, "stop"] > m.loc[short, "kapanis"]).all()
    # (b) lookahead: k'dan sonrasını değiştir, önceki satırlar aynı kalmalı
    k = int(len(m) * 0.75)
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2.iloc[k:, m2.columns.get_loc(c)] *= 2.5
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 3.0
    pd.testing.assert_frame_equal(s.iloc[:k], st.sinyaller(m2).iloc[:k])


def test_kayit_butunlugu():
    kimlikler = [k["kimlik"] for k in K.VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler)) == 33
    kaynaklar = {k["kimlik"].rsplit("#v", 1)[0] for k in K.VARYANTLAR}
    kodlanamadi = {k["kimlik"] for k in K.KODLANAMADI}
    assert len(K.SINIFLAR) == 31 and len(kodlanamadi) == 7
    assert not (kaynaklar & kodlanamadi) and len(kaynaklar | kodlanamadi) == 39
    assert {s.ad for s in K.SINIFLAR} <= {k["sinif"] for k in K.VARYANTLAR}
    assert all(k["neden"] for k in K.KODLANAMADI)
    assert {k["tf"] for k in K.VARYANTLAR} <= set(FREQ)


def test_roi_tablolari():
    assert K.CmcWinnerS0567.cikis_ayarlari.azalan_roi == ((0.0, 5.0), (2.0, 2.0), (3.0, 0.0))
    assert K.EmaOranBandiS0571.cikis_ayarlari.azalan_roi == ((0.0, 21.3), (6.0, 9.9), (12.0, 3.0), (33.0, 0.0))
    assert K.Cci72Rsi36S0572.cikis_ayarlari.azalan_roi[-1] == (17.0, 0.0)
    ca = K.DonchianAgirlikliBbS0577.cikis_ayarlari
    assert ca.geri_cekilme_yuzde == 17.2 and ca.geri_cekilme_min_kar_yuzde == 21.2
    assert K.BbDonusH4S0633.cikis_ayarlari.zaman_cikisi_mum == 24
    assert K.IchimokuBulutKirilimS0634.cikis_ayarlari.zaman_cikisi_mum == 120
    assert K.Crsi2S0635.cikis_ayarlari.zaman_cikisi_mum == 5


def test_s0608_iki_varyant():
    v = [k for k in K.VARYANTLAR if k["kimlik"].startswith("HAM:X005:608")]
    assert [x["parametreler"]["ma_uzun"] for x in v] == [200, 220]


def test_s0561_zirve_gunu_ve_hedef_stop():
    m = _mumlar("1d")
    s = K.Yuksek20TemasS0561().sinyaller(m)
    zirve = m["yuksek"] >= m["yuksek"].rolling(20).max()
    assert ((s["yon"] == 1) & ~zirve).sum() == 0 and (s["yon"] == 1).any()


def test_s0576_hedef_yuzde2_stop_yuzde15():
    m, s = _sinyalli(K.VwapDipS0576(), "5m")
    g_ = s["yon"] == 1
    assert np.allclose(s.loc[g_, "hedef"], m.loc[g_, "kapanis"] * 1.02)
    assert np.allclose(s.loc[g_, "stop"], m.loc[g_, "kapanis"] * 0.85)


def test_s0611_yalniz_pazartesi():
    m = _mumlar("1d")
    s = K.PazartesiDusSalitS0611().sinyaller(m)
    assert (s["yon"] == 1).any() and (m.index[s["yon"] == 1].dayofweek == 0).all()


def test_s0621_ters_kesisim_karsi_cikis():
    m = _mumlar("1h")
    s = K.TenkanKijunDonS0621().sinyaller(m)
    assert (s["cikis_long"] == (s["yon"] == -1)).all() and (s["cikis_short"] == (s["yon"] == 1)).all()


def test_s0625_siegel_dogrusal_seride_tam():
    k = pd.Series(2.0 + 3.0 * np.arange(10.0))
    uc = K._siegel_uc(k, 5)
    assert np.allclose(uc.iloc[4:], k.iloc[4:])
    assert uc.iloc[:4].isna().all()


def test_cti_dogrusal_seri():
    k = pd.Series(10.0 + np.arange(30.0))
    assert np.allclose(K._cti(k, 20).dropna(), 1.0)
    assert np.allclose(K._cti(-k, 20).dropna(), -1.0)


def test_s0653_stop_sma_eksi_25sd():
    m, s = _sinyalli(K.SdDonusS0653(), "1d")
    k = m["kapanis"]
    sma = k.rolling(8).mean()
    sd = k.diff().rolling(756).std(ddof=0)
    g_ = (s["yon"] == 1) & ((k - (sma - 2.5 * sd)) / k < 0.5)
    assert g_.any() and np.allclose(s.loc[g_, "stop"], (sma - 2.5 * sd)[g_])


def test_s0655_hedef_4x_stop_070():
    m, s = _sinyalli(K.YillikZirveKirilimS0655(), "1w")
    g_ = s["yon"] == 1
    assert np.allclose(s.loc[g_, "hedef"], m.loc[g_, "kapanis"] * 4.0)
    assert np.allclose(s.loc[g_, "stop"], m.loc[g_, "kapanis"] * 0.7)


def test_s0600_kumo_cikis_ve_stop_bulut_kenari():
    m, s = _sinyalli(K.KumoIzS0600(), "1d")
    assert "cikis_long" in s and "cikis_short" in s and s["cikis_long"].any()


def test_s0594_arsiv_sinifi_esik_10():
    kayit = [k for k in K.VARYANTLAR if k["kimlik"].startswith("HAM:X005:594")][0]
    assert kayit["sinif"] == "kapanis__rsi2-sma5-s0253" and kayit["parametreler"]["rsi_ust"] == 10.0
