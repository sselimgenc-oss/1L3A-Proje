"""g9_kod_6 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import kod_g9_kod_6 as K

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "3h": "3h", "4h": "4h", "1d": "1D"}
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
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


def _dusus_serisi(freq: str, n: int = N) -> pd.DataFrame:
    """B0810 için: yükseliş + aniden %20 çöküş tekrarı (MAMA-FAMA farkı, 48/288 mum düşüşü, CTI < -0,7)."""
    rng = np.random.default_rng(3)
    getiri = rng.normal(0, 0.002, n)
    for k in range(400, n - 60, 450):
        getiri[k - 250:k] += 0.0012          # yükseliş
        getiri[k:k + 40] -= 0.012            # sert çöküş
    kap = 100 * np.exp(np.cumsum(getiri))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, 0.001, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, 0.001, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(50, 150, n)}, index=idx)


def _veri(sinif, tf):
    return _dusus_serisi(tf) if sinif in (K.MamaKamaDususB0810, K.EmaObvRsiB0801) else _mumlar(tf)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    tf = SINIF_TF[st.ad]
    m = _veri(sinif, tf)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    assert not short.any(), "tüm B001 satırları yalnız long"
    assert st.cikis_var_mi()
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = st.sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR}
    sinif = sozluk[kayit["sinif"]]
    st = sinif(**kayit["parametreler"])
    m = _veri(sinif, kayit["tf"])
    s = st.sinyaller(m.iloc[:3000])
    assert len(s) == 3000
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_6.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler
    assert not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    assert all(a.rsplit("-b", 1)[1].isdigit() for a in adlar)
    # girdi TF'leri ile VARYANT TF'leri uyuşuyor
    tf_girdi = dict(zip(girdi["kaynak_id"], girdi["tf"]))
    assert all(tf_girdi[v["kimlik"].split("#")[0]] == v["tf"] for v in K.VARYANTLAR)


def test_roi_tablosu_ve_cikis_ayarlari():
    assert K.AdxDiKesisimB0758.cikis_ayarlari.azalan_roi == ((0, 26.552), (2, 10.255), (14, 3.545), (36, 0.0))
    assert K.MacdTemaB0784.cikis_ayarlari.azalan_roi == ((2, 15.0), (3, 6.0), (6, 4.0), (24, 0.0))
    assert K.EmaYiginUst1hB0772.cikis_ayarlari.azalan_roi == ((0, 4.0), (6, 3.0), (12, 1.0))
    # 5m'de 3 ve 5 dakika anahtarları aynı muma düşer: büyük dakikalı (%3,351) geçerli
    assert K.RsiDiverjansB0770.cikis_ayarlari.azalan_roi[:2] == ((0, 10.347602), (1, 3.350898))
    ca = K.KamaCciB0775.cikis_ayarlari
    assert ca.yalniz_karda_cikis and ca.yalniz_karda_min_kar_yuzde == 1.0
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (28.596, 29.771)
    assert K.StochRsiTemaB0797.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 0.0   # only_offset=False
    assert K.MacdCciB0798.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 10.0       # only_offset=True
    assert K.TrixV15B0804.cikis_ayarlari.yalniz_karda_cikis
    assert K.MacdCciB0777.cikis_ayarlari.azalan_roi == ()                          # ROI {0:100} etkisiz


def test_stop_uyarlamalari():
    for sinif, tf, oran in ((K.RsiDiverjansB0770, "5m", 0.85), (K.MacdCciB0777, "30m", 0.70),
                            (K.AwesomeMacdB0762, "1h", 0.984)):
        m = _veri(sinif, tf)
        s = sinif().sinyaller(m)
        g = s["yon"] == 1
        assert g.any()
        assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * oran)
    # kaynak stopu -%99 olanlar ATR(14)x3
    from motor.strateji import gostergeler as gg
    for sinif in (K.CrossEmaStochRsiB0768, K.TrixHistStochRsiB0803, K.UcSupertrendStochRsiB0754):
        m = _mumlar("1h")
        s = sinif().sinyaller(m)
        g = s["yon"] == 1
        assert g.any()
        mes = 3.0 * gg.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
        assert np.allclose(s.loc[g, "stop"], (m["kapanis"] - mes)[g])


def test_b0744_filtre_cikista_etkin_girisde_etkisiz():
    m = _mumlar("5m", 3000)
    s = K.HacimSma9YonB0744().sinyaller(m)
    kap = m["kapanis"]
    sma = m["hacim"].rolling(9).mean()
    beklenen_al = (m["hacim"] > sma) & (kap.shift(1) < kap)
    assert (s["yon"] == 1).equals(beklenen_al)
    # çıkış: önceki mumda giriş sinyali varsa çıkış yok
    onceki_al = beklenen_al.shift(1, fill_value=False)
    assert not (s["cikis_long"] & (beklenen_al | onceki_al)).any()
    assert s["cikis_long"].any()


def test_diverjans_bilinen_desen():
    # fiyat ikinci dipte daha düşük, osilatör ikinci dipte daha yüksek -> boğa diverjansı
    kap = pd.Series([10, 9, 8, 9, 10, 9, 7, 8, 9.0])
    osc = pd.Series([50, 40, 30, 40, 50, 45, 35, 45, 50.0])
    d = K._boga_diverjans(kap, osc)
    assert d.iloc[7]            # 7. barda ikinci dip (7) görünür hale gelir
    assert not d.iloc[:6].any()
    # fiyat daha YÜKSEK dip yaparsa diverjans yok
    kap2 = pd.Series([10, 9, 8, 9, 10, 9, 8.5, 9, 9.5])
    assert not K._boga_diverjans(kap2, osc).any()


def test_yardimci_gostergeler():
    x = pd.Series(np.arange(40, dtype=float))
    assert np.allclose(K._cti(x, 20).dropna(), 1.0)
    assert np.allclose(K._cti(-x, 20).dropna(), -1.0)
    s = pd.Series(np.linspace(1, 2, 80))
    t = K._tema(s, 5).dropna()
    assert (t - s.loc[t.index]).iloc[-30:].abs().max() < 1e-6      # doğrusal seride (ısınma sonrası) TEMA gecikmesiz
    sr = K._stoch_rsi_ham(_mumlar("1h", 500)["kapanis"], 14).dropna()
    assert ((sr >= 0) & (sr <= 1)).all()


def _kancali(sinif, tf, n=4000):
    m = _mumlar(tf, n, tohum=3, vol=0.02)
    st = sinif()
    return st, backtest(m, st, MotorAyarlari())


@pytest.mark.parametrize("sinif,tf", [(K.MacdEma80AtrIzB0788, "4h"), (K.TrixV21B0805, "1h")])
def test_atr_iz_kancasi_backtestte_tetiklenir(sinif, tf):
    st, r = _kancali(sinif, tf)
    assert callable(st.pozisyon_cikisi)
    assert len(r.islemler) > 3
    assert "kanca" in set(r.islemler["cikis_nedeni"]), "kapanış bazlı iz kancayla tetiklenmeli"


def test_kanca_seviye_yalniz_yukari():
    from motor.strateji.cikislar import PozisyonDurumu
    st = K.TrixV21B0805()
    m = _mumlar("1h", 1500, tohum=5)
    st.sinyaller(m)
    kap, sv = st._kd["kap"], st._kd["seviye"]
    i = 800
    d = PozisyonDurumu(yon=1, giris_fiyati=kap[i], giris_mum_indeksi=i, mum_indeksi=i + 50, tutulan_mum=50,
                       en_yuksek=kap[i:i + 51].max(), en_dusuk=kap[i:i + 51].min(), kapanis=kap[i + 50], kar_yuzde=0.0)
    beklenen = kap[i + 50] <= np.nanmax(sv[i - 1:i + 51])
    assert st.pozisyon_cikisi(d) == beklenen
    # sinyal mumundan ÖNCEKİ seviyeler dikkate alınmaz
    assert not st.pozisyon_cikisi(PozisyonDurumu(1, kap[5], 5, 5, 0, kap[5], kap[5], kap[5], 0.0)) or np.isfinite(sv[4:6]).any()
