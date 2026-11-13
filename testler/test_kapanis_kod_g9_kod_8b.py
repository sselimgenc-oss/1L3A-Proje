"""g9_kod_8b sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür,
ROI/iz/stop eşlemeleri kaynak değerlerle uyumlu, kancalar beklenen durumlarda çıkış verir."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.kapanis import kod_g9_kod_8b as K

FREQ = {"1h": "1h", "4h": "4h", "6h": "6h", "1d": "1D"}
CSV = "sonuclar/kapanis/kod_girdi/g9_kod_8b.csv"
SINIF_TF = {v["sinif"]: v["tf"] for v in K.VARYANTLAR}
KISA_VAR = {K.GfiB0147, K.GfiHacimB0148, K.IrmB0210}      # long + short kuralı olanlar
N = 6000


def _mumlar(freq: str, n: int = N, tohum: int = 7, vol: float = 0.01, dalga: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(50, 150, n)}, index=idx)


def _girdi() -> pd.DataFrame:
    return pd.read_csv(CSV)


def _durum(giris_i, i, tutulan, kar, giris=100.0):
    kap = giris * (1 + kar / 100.0)
    return PozisyonDurumu(1, giris, giris_i, i, tutulan, max(kap, giris), min(kap, giris), kap, kar)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    tf = SINIF_TF[st.ad]
    m = _mumlar(tf)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    if sinif in KISA_VAR:
        assert short.any()
    else:
        assert not short.any(), "kaynak kural yalnız long"
    assert st.cikis_var_mi()
    assert s.loc[long, "stop"].notna().all() and s.loc[short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    assert (s.loc[short, "stop"] > m.loc[short, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    pd.testing.assert_frame_equal(s.iloc[:k], sinif().sinyaller(m2).iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    pd.testing.assert_frame_equal(s.iloc[:k + 1], sinif().sinyaller(m.iloc[:k + 1]))


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_hacim_degisimi_gecmisi_bozmaz(sinif):
    m = _mumlar(SINIF_TF[sinif.ad])
    s = sinif().sinyaller(m)
    k = N - 300
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 7.0
    pd.testing.assert_frame_equal(s.iloc[:k], sinif().sinyaller(m2).iloc[:k])


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR}
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    assert len(st.sinyaller(m)) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = _girdi()
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler and not kayitli & kod_yok
    assert kod_yok == {"HAM:B001:661"} and all(x["neden"] for x in K.KODLANAMADI)
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    for v in K.VARYANTLAR:
        assert v["sinif"].endswith("-b%04d" % int(v["kimlik"].split("#")[0].split(":")[-1]))
    tf_girdi = dict(zip(girdi["kaynak_id"], girdi["tf"]))
    assert all(v["tf"] == tf_girdi[v["kimlik"].split("#")[0]] for v in K.VARYANTLAR)


def test_roi_iz_stop_kaynak_degerleri():
    ca = K.IrmB0210.cikis_ayarlari
    assert ca.azalan_roi[0] == (0, 50.0) and ca.azalan_roi[-1] == (120, 2.0) and len(ca.azalan_roi) == 10
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (1.5, 3.0)
    for sinif in (K.GkdHurstB0607, K.GkdPfeB0608):
        ca = sinif.cikis_ayarlari
        assert ca.azalan_roi == ((0, 5.0), (1, 3.0), (2, 1.0))
        assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (2.0, 3.0)
    assert K.GovdeKirmiziB0686.cikis_ayarlari.azalan_roi == ((0, 90.0),)
    assert K.Pcb20B0905.cikis_ayarlari.azalan_roi == ((0, 30.9),)
    assert K.TacosB0906.cikis_ayarlari.azalan_roi == ((0, 36.1), (3, 10.4), (5, 5.8), (22, 0.0))
    n = K.NormalizerB0889.cikis_ayarlari
    assert n.yalniz_karda_cikis and (n.geri_cekilme_yuzde, n.geri_cekilme_min_kar_yuzde) == (1.0, 1.5)
    # yüzde stoplar kaynak stopuyla; ATR uyarlamalı satırlar kapanıştan uzak
    for sinif, sl in ((K.MinmaxB0377, 0.05), (K.GkdHurstB0607, 0.10), (K.GkdPfeB0608, 0.10), (K.ApolloB0842, 0.16),
                      (K.Pcb20B0905, 0.015), (K.TacosB0906, 0.255)):
        m = _mumlar(SINIF_TF[sinif.ad], 3000)
        s = sinif().sinyaller(m)
        g = s["yon"] == 1
        assert g.any(), sinif.__name__
        assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - sl))
    # GKD kaynakta can_short tanımsız: varsayılan long-only; kisa=1 ile short kolu
    m = _mumlar("1h")
    assert not (K.GkdHurstB0607().sinyaller(m)["yon"] == -1).any()
    assert (K.GkdPfeB0608(kisa=1).sinyaller(m)["yon"] == -1).any()
    assert K.TacosB0906().varsayilan_parametreler["sell_rsiu"] < K.TacosB0906().varsayilan_parametreler["sell_rsil"]


def test_tacos_cikis_imkansiz_pcb20_cikis_var():
    m = _mumlar("1d")
    assert not K.TacosB0906().sinyaller(m)["cikis_long"].any()
    assert K.Pcb20B0905().sinyaller(_mumlar("6h"))["cikis_long"].any()


def test_minmax_yerel_dip_ve_tepe():
    n = 700
    kap = np.r_[np.linspace(200, 150, 550), 149.0, 160.0, np.linspace(161, 170, n - 552)]
    idx = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC")
    m = pd.DataFrame({"acilis": kap, "yuksek": kap + 0.1, "dusuk": kap - 0.1, "kapanis": kap, "hacim": 1.0}, index=idx)
    s = K.MinmaxB0377().sinyaller(m)
    assert list(np.flatnonzero(s["yon"] == 1)) == [552]
    assert not s["cikis_long"].any()
    # ayna: yerel tepe -> çıkış
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2[c] = 400 - m[c]
    s2 = K.MinmaxB0377().sinyaller(m2)
    assert list(np.flatnonzero(s2["cikis_long"])) == [552]


def test_zerolag_ratchet_kancasi():
    st = K.ZeroLagB0155()
    kap = np.array([100.0, 110.0, 110.0, 110.0])
    st._sakla(kapanis=kap, vol=np.full(4, 4.0))          # stop = kapanış - 2
    assert st.pozisyon_cikisi(_durum(0, 2, 2, 7.9))      # seviye 108 (j=1) >= 107,9
    assert not st.pozisyon_cikisi(_durum(0, 2, 2, 8.5))
    assert st.pozisyon_cikisi(_durum(0, 1, 1, -10.5))    # sabit -%10 tabanı


def test_apollo_basamaklar_ve_kanca():
    d = K.ApolloB0842._mesafe(np.array([0.25, 0.15, 0.08, 0.04, -0.12, -0.09, -0.12, 0.0]),
                              np.array([0, 0, 0, 0, 61, 121, 30, 0.0]))
    assert d[:4].tolist() == [0.04, 0.03, 0.02, 0.01]
    assert d[4] == pytest.approx(0.12 / 1.75) and d[5] == pytest.approx(0.09 / 1.70)
    assert np.isnan(d[6]) and np.isnan(d[7])
    st = K.ApolloB0842()
    st._sakla(kapanis=np.array([100.0, 108.0, 105.0]))   # j=1: kâr %8 -> stop 108 x 0,98 = 105,84
    assert st.pozisyon_cikisi(_durum(0, 2, 2, 5.0))
    assert not st.pozisyon_cikisi(_durum(0, 2, 2, 6.5))


def test_normalizer_roi_giris_sinyalinde_askida_ve_zarar_stopu():
    st = K.NormalizerB0889()
    st._sakla(kapanis=np.full(10, 120.0), al=np.array([False] * 5 + [True] + [False] * 4))
    assert st.pozisyon_cikisi(_durum(0, 4, 4, 20.0))      # kâr >= %18, o mumda giriş sinyali yok
    assert not st.pozisyon_cikisi(_durum(0, 5, 5, 20.0))  # giriş sinyali aktif: ROI yok sayılır
    zarar = np.array([100.0, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0, 93.9, 93.0])
    st._sakla(kapanis=zarar, al=np.zeros(10, bool))
    # j=6: kâr < 0 ve tutulan 6 mum -> stop 95 x 0,99 = 94,05
    assert st.pozisyon_cikisi(_durum(0, 8, 8, -6.1))
    assert not st.pozisyon_cikisi(_durum(0, 8, 8, -5.5))
    assert not st.pozisyon_cikisi(_durum(0, 5, 5, -6.1))  # 6 mumluk koşul henüz yok


def test_pcb20_negatif_roi_kancasi():
    st = K.Pcb20B0905()
    assert not st.pozisyon_cikisi(_durum(0, 0, 0, 0.5))
    assert st.pozisyon_cikisi(_durum(0, 1, 1, -0.9)) and not st.pozisyon_cikisi(_durum(0, 1, 1, -1.2))


def test_gfi_ve_pfe_hurst_temel_ozellikler():
    x = pd.Series(np.arange(1.0, 60.0))
    mm = K._minmax(x, 20).dropna()
    assert np.allclose(mm, 1.0, atol=1e-6)
    assert (K._pfe(pd.Series(np.arange(100.0, 160.0)), 10).iloc[10:] > 99).all()
    assert (K._pfe(pd.Series(np.arange(160.0, 100.0, -1.0)), 10).iloc[10:] < -99).all()
    assert (K._pfe(pd.Series(np.arange(5.0)), 10) == 0).all()
    h = K._hurst(pd.Series(np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, 400)))), 64)
    assert h.iloc[:64].isna().all() and h.iloc[64:].between(0, 1).all()


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_backtest_calisir(sinif):
    tf = SINIF_TF[sinif.ad]
    m = _mumlar(tf, N)
    r = backtest(m, sinif(), MotorAyarlari())
    assert len(r.islemler) > 0
    assert not math.isnan(float(r.ozsermaye.iloc[-1]))
