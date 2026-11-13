"""k3_kod_1 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür (mevcut sınıflı H007:48
dahil), ROI/iz/stop eşlemeleri ve satıra özgü zaman/seans kuralları beklenen biçimde."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.kapanis import kod_k3_kod_1 as K

FREQ = {"5m": "5min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
CSV = "sonuclar/kapanis/kod_girdi/k3_kod_1.csv"
KAYIT_TF = {v["sinif"]: v["tf"] for v in K.VARYANTLAR}
KISA_VAR = {K.ElderImpulseK3A002_6, K.EmaKesisSma1hK3D001_272, K.ScalpRsiBbK3V001_226, K.GeceGunduzTersK3V006_1,
            K.HacimSeansiMomentumK3V006_3, K.UcSigmaTersK3V006_4, K.FundingSonrasiKirilimK3V006_6, K.VolatiliteSistemiK3V010_7,
            K.RsiTemaBbK3V010_8}
# sınıf -> (mum sayısı, volatilite, drift/mum, dalga)
KONF = {
    K.ElderImpulseK3A002_6: (3000, 0.02, 0.0, 80),
    K.EmaKesisSma1hK3D001_272: (6000, 0.003, 0.0, 400),
    K.HaftalikKirilimRejimK3V001_225: (9000, 0.004, 0.0004, 1500),
    K.ScalpRsiBbK3V001_226: (6000, 0.003, 0.0, 400),
    K.GeceGunduzTersK3V006_1: (3000, 0.01, 0.0, 60),
    K.HacimSeansiMomentumK3V006_3: (4000, 0.004, 0.0, 200),
    K.UcSigmaTersK3V006_4: (6000, 0.01, 0.0, 60),
    K.FundingSonrasiKirilimK3V006_6: (14000, 0.003, 0.0, 400),
    K.KamaFamaK3V010_22: (20000, 0.004, 0.0, 700),
    K.VolatiliteSistemiK3V010_7: (6000, 0.01, 0.0, 60),
    K.RsiTemaBbK3V010_8: (6000, 0.01, 0.0, 60),
    K.Rsi5K3V014_255: (3000, 0.02, 0.0, 80),
}
SINIF_TF = {s: KAYIT_TF[s.ad] for s in K.SINIFLAR}


def _mumlar(freq: str, n: int, vol: float = 0.01, drift: float = 0.0, dalga: int = 60, tohum: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + drift + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(50, 150, n)}, index=idx)


def _veri(sinif) -> pd.DataFrame:
    n, vol, drift, dalga = KONF[sinif]
    return _mumlar(SINIF_TF[sinif], n, vol, drift, dalga)


def _durum(giris_i, i, tutulan, kar, giris=100.0):
    kap = giris * (1 + kar / 100.0)
    return PozisyonDurumu(1, giris, giris_i, i, tutulan, max(kap, giris), min(kap, giris), kap, kar)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    m = _veri(sinif)
    n = len(m)
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
    k = n - 300
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    pd.testing.assert_frame_equal(s.iloc[:k], sinif().sinyaller(m2).iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez (ortadaki bir noktada)
    for kes in (k + 1, n - 37):
        pd.testing.assert_frame_equal(s.iloc[:kes], sinif().sinyaller(m.iloc[:kes]))
    # hacim değişimi geçmişi bozmaz
    m3 = m.copy()
    m3.iloc[k:, m3.columns.get_loc("hacim")] *= 7.0
    pd.testing.assert_frame_equal(s.iloc[:k], sinif().sinyaller(m3).iloc[:k])


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR + K.MEVCUT_SINIFLAR}
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    assert len(st.sinyaller(m)) == len(m)
    assert st.parametre_izgarasi in ({}, st.parametre_izgarasi)


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv(CSV)
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == set(girdi["kaynak_id"]) and not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR) == 13
    tf_girdi = dict(zip(girdi["kaynak_id"], girdi["tf"]))
    assert all(v["tf"] == tf_girdi[v["kimlik"].split("#")[0]] for v in K.VARYANTLAR)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    for v in K.VARYANTLAR:
        kaynak = v["kimlik"].split("#")[0]
        if kaynak == "HAM:H007:48":
            assert v["sinif"] == "dis__rsrs-egim-esigi" and v["kimlik"] == "HAM:H007:48#v1"
            continue
        assert v["sinif"].endswith("-k3" + kaynak.split(":", 1)[1].lower().replace(":", "-")), v["sinif"]
    # satır ayarları girdideki gibi
    ayar = __import__("json").loads(girdi.loc[girdi["kaynak_id"] == "HAM:H007:48", "ayar"].iloc[0])
    kayit = next(v for v in K.VARYANTLAR if v["kimlik"].startswith("HAM:H007:48"))
    assert {k: kayit["parametreler"][k] for k in ("mod", "n", "esik_al", "esik_cik", "stop_atr_k")} == ayar


def test_h007_mevcut_sinif_ayarla_sinyal_verir():
    kayit = next(v for v in K.VARYANTLAR if v["kimlik"].startswith("HAM:H007:48"))
    st = K.RsrsEgimEsigi(**kayit["parametreler"])
    assert st.ad == kayit["sinif"]
    m = _mumlar("1d", 3000, 0.02, 0.0, 80)
    s = st.sinyaller(m)
    long = s["yon"] == 1
    assert long.any() and (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    k = 2700
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    pd.testing.assert_frame_equal(s.iloc[:k], K.RsrsEgimEsigi(**kayit["parametreler"]).sinyaller(m2).iloc[:k])


def test_roi_iz_stop_kaynak_degerleri():
    assert K.EmaKesisSma1hK3D001_272.cikis_ayarlari.azalan_roi == ((0, 5.0), (6, 10.0), (12, 7.5))
    ca = K.ScalpRsiBbK3V001_226.cikis_ayarlari
    assert ca.azalan_roi == ((0, 1.2), (2, 0.8), (4, 0.4), (6, 0.0))
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (0.4, 0.8)
    assert K.RsiTemaBbK3V010_8.cikis_ayarlari.azalan_roi == ((0, 100.0),)
    assert K.HaftalikKirilimRejimK3V001_225.cikis_ayarlari.stop_sonrasi_bekleme_mum == 24
    assert K.KamaFamaK3V010_22.cikis_ayarlari.yalniz_karda_cikis
    for sinif, sl in ((K.EmaKesisSma1hK3D001_272, 0.05), (K.HaftalikKirilimRejimK3V001_225, 0.06),
                      (K.ScalpRsiBbK3V001_226, 0.012), (K.KamaFamaK3V010_22, 0.25), (K.RsiTemaBbK3V010_8, 0.05)):
        m = _veri(sinif)
        s = sinif().sinyaller(m)
        g = s["yon"] == 1
        assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - sl)), sinif.__name__
        k = s["yon"] == -1
        if k.any():
            assert np.allclose(s.loc[k, "stop"], m.loc[k, "kapanis"] * (1 + sl))


def test_d001_272_cikis_iki_yon_adx():
    m = _veri(K.EmaKesisSma1hK3D001_272)
    s = K.EmaKesisSma1hK3D001_272().sinyaller(m)
    assert s["cikis_long"].any() and (s["cikis_long"] == s["cikis_short"]).all()


def test_v001_226_giris_iki_yon_ve_cikis():
    m = _veri(K.ScalpRsiBbK3V001_226)
    s = K.ScalpRsiBbK3V001_226().sinyaller(m)
    assert s["cikis_long"].any() and s["cikis_short"].any()


def test_a002_6_haftalik_yon_ilk_gun():
    m = _veri(K.ElderImpulseK3A002_6)
    s = K.ElderImpulseK3A002_6().sinyaller(m)
    # yön yalnız yeni oluştuğu günde: ardışık iki gün aynı yönde giriş olmaz
    y = s["yon"]
    assert not ((y != 0) & (y == y.shift(1))).any()
    assert (y.iloc[:7 * 30] == 0).all()   # haftalık MACD histogram eğimi ~35 haftadan önce yok


def test_v006_1_seans_saatleri_ve_yon():
    n = 24 * 60
    idx = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC")
    kap = 100.0 + 0.05 * np.arange(n) + np.sin(np.arange(n))
    m = pd.DataFrame({"acilis": np.r_[kap[0], kap[:-1]], "yuksek": kap + 0.3, "dusuk": kap - 0.3, "kapanis": kap, "hacim": 1.0},
                     index=idx)
    # yükselen piyasa: gündüz getirisi > 0 -> short; gece her gün long
    s = K.GeceGunduzTersK3V006_1().sinyaller(m)
    saat = pd.Series(idx.hour, index=idx)
    ok = s.index[20:]
    assert (s.loc[(saat == 16) & s.index.isin(ok), "yon"] == 1).all()
    assert (s.loc[(saat == 4) & (np.arange(n) > 40), "yon"] == -1).all()
    assert (s.loc[~saat.isin([4, 16]), "yon"] == 0).all()
    assert (s.loc[saat.isin([4, 16]), "cikis"]).all() and not s.loc[~saat.isin([4, 16]), "cikis"].any()
    # düşen piyasa: gündüz getirisi < 0 -> long
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2[c] = 400 - m[c]
    s2 = K.GeceGunduzTersK3V006_1().sinyaller(m2)
    assert (s2.loc[(saat == 4) & (np.arange(n) > 40), "yon"] == 1).all()


def test_v006_3_hacim_dilimi_ve_son_30dk():
    gun = 45
    n = gun * 48
    idx = pd.date_range("2020-01-01", periods=n, freq="30min", tz="UTC")
    rng = np.random.default_rng(3)
    dilim = np.arange(n) % 48
    hacim = rng.uniform(10, 20, n)
    hacim[dilim == 20] += 500                         # en yüksek hacimli dilim 10:00
    kap = 100 + np.cumsum(rng.normal(0, 0.1, n))
    ac = kap - np.where(dilim == 20, 0.5, 0.0)        # seans ilk mumu hep yeşil: kapanış > açılış
    m = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + 0.2, "dusuk": np.minimum(ac, kap) - 0.2, "kapanis": kap,
                      "hacim": hacim}, index=idx)
    s = K.HacimSeansiMomentumK3V006_3().sinyaller(m)
    long_pos = np.flatnonzero(s["yon"] == 1)
    assert len(long_pos) > 5 and ((long_pos % 48) == (20 + 46) % 48).all()      # 09:00 mumu = seans başlangıcı + 46 mum
    assert not (s["yon"] == -1).any()
    cik = np.flatnonzero(s["cikis"])
    assert ((cik % 48) == (20 + 47) % 48).all()
    assert long_pos.min() >= 30 * 48                    # 30 günlük hacim geçmişi dolmadan sinyal yok


def test_v006_4_uc_sigma_ve_bir_mum_sonra_cikis():
    n = 800
    rng = np.random.default_rng(5)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    kap[500:] *= 0.95                                  # 500. mumda -%5 sıçrama
    idx = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC")
    m = pd.DataFrame({"acilis": np.r_[kap[0], kap[:-1]], "yuksek": kap * 1.001, "dusuk": kap * 0.999, "kapanis": kap, "hacim": 1.0},
                     index=idx)
    s = K.UcSigmaTersK3V006_4().sinyaller(m)
    assert s["yon"].iloc[500] == 1 and s["cikis_long"].iloc[501]
    kap2 = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    kap2[500:] *= 1.05
    m2 = m.assign(kapanis=kap2, acilis=np.r_[kap2[0], kap2[:-1]], yuksek=kap2 * 1.001, dusuk=kap2 * 0.999)
    s2 = K.UcSigmaTersK3V006_4().sinyaller(m2)
    assert s2["yon"].iloc[500] == -1 and s2["cikis_short"].iloc[501]


def test_v006_6_yalniz_funding_ilk_mumu():
    m = _veri(K.FundingSonrasiKirilimK3V006_6)
    s = K.FundingSonrasiKirilimK3V006_6().sinyaller(m)
    giris = s["yon"] != 0
    assert giris.any()
    assert (m.index[giris].hour.isin([0, 8, 16]).all()) and (m.index[giris].minute == 0).all()
    zaman = s["cikis_long"] & (m.index.minute == 25) & m.index.hour.isin([0, 8, 16])
    assert zaman.any()


def test_kamafama_kilit_stop_kancasi():
    st = K.KamaFamaK3V010_22()
    st._sakla(kapanis=np.array([100.0, 106.0, 104.0, 104.0]))
    assert st.pozisyon_cikisi(_durum(0, 3, 3, 4.0)) is True or st.pozisyon_cikisi(_durum(0, 3, 3, 4.0))
    # kilit seviyesi 106 x 0,998 = 105,788
    assert st.pozisyon_cikisi(_durum(0, 3, 3, 5.5))
    assert not st.pozisyon_cikisi(_durum(0, 3, 3, 5.9))
    st._sakla(kapanis=np.array([100.0, 104.0, 104.0]))   # kâr %5'e hiç ulaşmadı: kilit yok
    assert not st.pozisyon_cikisi(_durum(0, 2, 2, -3.0))


def test_v014_255_rsi_esigi():
    from motor.strateji import gostergeler as g
    m = _veri(K.Rsi5K3V014_255)
    s = K.Rsi5K3V014_255().sinyaller(m)
    r = g.rsi(m["kapanis"], 5)
    assert (s["cikis_long"] == (r < 70)).all()
    assert set(s.index[s["yon"] == 1]) <= set(r.index[r > 70])


def test_v010_7_3h_kapanmis_mumdan():
    m = _veri(K.VolatiliteSistemiK3V010_7)
    s = K.VolatiliteSistemiK3V010_7().sinyaller(m)
    assert s["cikis_long"].any() and s["cikis_short"].any()
    # 3h mumun içindeki 1h mumları bozmak aynı 3h mumun (açık kalan) sinyalini değiştirmez
    j = 3000
    son = m.index[j].floor("3h") + pd.Timedelta(hours=2)
    m2 = m.copy()
    m2.loc[son, ["yuksek", "kapanis"]] = m2.loc[son, "yuksek"] * 1.5
    s2 = K.VolatiliteSistemiK3V010_7().sinyaller(m2)
    once = m2.index < son
    pd.testing.assert_frame_equal(s.loc[once], s2.loc[once])


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_backtest_calisir(sinif):
    m = _veri(sinif)
    r = backtest(m, sinif(), MotorAyarlari())
    assert len(r.islemler) > 0
    assert not math.isnan(float(r.ozsermaye.iloc[-1]))
