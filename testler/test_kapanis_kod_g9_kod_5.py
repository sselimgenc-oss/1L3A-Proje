"""g9_kod_5 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import kod_g9_kod_5 as K

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
N = 6000
# Sentetik veri ayarı (tohum, volatilite, dalga) sınıf başına: kural sentetik seride en az bir kez tetiklenmeli.
OZEL = {"ObeliskImB0679": {"dalga": 200}, "Obelisk3EmaStochB0681": {"dalga": 200}}


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


def _veri(sinif, n: int = N) -> pd.DataFrame:
    return _mumlar(SINIF_TF[sinif.ad], n, **OZEL.get(sinif.__name__, {}))


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    m = _veri(sinif)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    assert not short.any()                       # Robotic satırlarının tamamı long
    assert st.cikis_var_mi()
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = sinif().sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = sinif().sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR}
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    s = st.sinyaller(_mumlar(kayit["tf"], 3000))
    assert len(s) == 3000
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_5.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler and not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    # TF, girdideki tf sütunuyla aynı
    tf_girdi = dict(zip(girdi["kaynak_id"], girdi["tf"]))
    assert all(tf_girdi[v["kimlik"].split("#")[0]] == v["tf"] for v in K.VARYANTLAR)


KANCALI = [K.NowoIchimoku1hV1B0634, K.NowoIchimokuV2B0635, K.NowoIchimoku5mV2B0636, K.ObeliskIchiZemaB0638,
           K.Ema20Ema200B0650, K.MultiMaTsl3B0663, K.MultiMaTsl3ModB0664, K.ObeliskRsiB0680, K.Obelisk3EmaStochB0681,
           K.SmaOffsetV2B0699]


@pytest.mark.parametrize("sinif", KANCALI, ids=lambda s: s.__name__)
def test_kanca_motorda_calisir(sinif):
    """Kancalı sınıflar motorda hatasız koşar; kanca callable."""
    m = _veri(sinif, 4000)
    st = sinif()
    assert callable(st.pozisyon_cikisi)
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) >= 0


def test_roi_trailing_esleme():
    assert K.NowoIchimokuV2B0635.cikis_ayarlari.azalan_roi == ((0, 42.7), (8, 20.2), (19, 8.9), (40, 0.0))
    assert K.ObeliskIchiSlowB0637.cikis_ayarlari.azalan_roi == ((0, 10.0), (1, 7.2), (2, 4.9), (4, 2.0), (6, 0.0))
    ca = K.ObeliskIchiSlowB0637.cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (0.5, 4.0)
    assert K.Ema50B0649.cikis_ayarlari.azalan_roi == ((0, 27.8), (8, 8.7), (25, 3.8), (27, 0.0))
    assert K.Ema50B0649.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 0.0
    assert K.EmaBreakoutB0651.cikis_ayarlari.yalniz_karda_cikis
    assert K.ChispeiB0645.cikis_ayarlari.azalan_roi[-3:] == ((8, 67.6), (11, 7.9), (22, 0.0))
    assert K.OmaGannB0707.cikis_ayarlari.azalan_roi == ((0, 11.3), (7, 7.6), (23, 4.1), (38, 0.0))
    assert K.RenkoB0685.cikis_ayarlari.yalniz_karda_min_kar_yuzde == 10.0


def test_zema_kurali_kaynak_dosyadan():
    p = K.ObeliskIchiZemaB0638.varsayilan_parametreler
    assert (p["zema_al"], p["alt_ofset"], p["zema_sat"], p["ust_ofset"]) == (51, 0.964, 72, 1.004)


def test_gostergeler():
    kap = pd.Series(np.arange(1.0, 41.0))
    assert np.isclose(K._trima(kap, 5).iloc[-1], 38.0)                # doğru üzerinde TRIMA = merkez değer
    e = K.g.ema(kap, 3)
    assert np.isclose(K._zema(kap, 3).iloc[-1], 2 * e.iloc[-1] - K.g.ema(e, 3).iloc[-1])
    assert np.isclose(K._kor(kap, 20).iloc[-1], 1.0)                  # artan doğru: korelasyon 1
    assert np.isclose(K._kor(-kap, 20).iloc[-1], -1.0)


def test_mum_desenleri_bilinen_ornek():
    # kırmızı + yutan boğa mumu
    m = pd.DataFrame({"acilis": [10.0, 10.0, 9.0], "yuksek": [10.5, 10.1, 10.6], "dusuk": [9.5, 9.2, 8.9],
                      "kapanis": [10.2, 9.5, 10.4], "hacim": 1.0},
                     index=pd.date_range("2020-01-01", periods=3, freq="1h", tz="UTC"))
    assert K.cdl_yutan(m).iloc[-1] > 0
    assert K.cdl_aksam_yildizi(m).max() <= 0                         # akşam yıldızı hiçbir zaman > 0 üretmez


def test_renko_trend_durumu():
    n = 400
    t = np.arange(n)
    kap = 100 + 0.5 * t + 3 * np.sin(t / 5)
    idx = pd.date_range("2020-01-01", periods=n, freq="15min", tz="UTC")
    m = pd.DataFrame({"acilis": kap, "yuksek": kap + 1.0, "dusuk": kap - 1.0, "kapanis": kap, "hacim": 10.0}, index=idx)
    s = K.RenkoB0685().sinyaller(m)
    assert (s["yon"] == 1).any() and not (s["yon"] == -1).any()
