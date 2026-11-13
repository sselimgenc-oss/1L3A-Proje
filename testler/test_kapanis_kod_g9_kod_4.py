"""g9_kod_4 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g9_kod_4 as K
from motor.strateji.cikislar import PozisyonDurumu

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "3h": "3h", "4h": "4h", "6h": "6h", "1d": "1D"}
SINIF_TF = {v["sinif"]: v["tf"] for v in K.VARYANTLAR}
N = 6000
TOHUMLAR = (7, 11, 23, 42, 99, 5, 3)


def _mumlar(freq: str, n: int = N, tohum: int = 7, vol: float = 0.01, dalga: int = 60, cokus: bool = True) -> pd.DataFrame:
    """Sentetik OHLCV: t-dağılımlı getiri + yavaş dalga + (isteğe bağlı) ara sıra sert düşüş/toparlanma ve hacim patlamaları."""
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    hacim = rng.uniform(50, 150, n)
    if cokus:
        for b in range(300, n - 60, 400):
            u = int(rng.integers(8, 30))
            getiri[b:b + u] -= rng.uniform(0.01, 0.04)
            getiri[b + u:b + u + 15] += rng.uniform(0.005, 0.02)
            hacim[b:b + u] *= rng.uniform(3.0, 9.0)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": hacim}, index=idx)


def _sinyalli(sinif):
    """Long sinyal üreten ilk sentetik seri (kurallar nadir olabilir: birkaç tohum/oynaklık denenir)."""
    st = sinif()
    tf = SINIF_TF[st.ad]
    for vol in (0.01, 0.02, 0.005):
        for tohum in TOHUMLAR:
            m = _mumlar(tf, tohum=tohum, vol=vol)
            s = st.sinyaller(m)
            if (s["yon"] == 1).any():
                return st, m, s
    return st, m, s


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st, m, s = _sinyalli(sinif)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    assert not short.any()
    assert st.cikis_var_mi()
    assert s.loc[long, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = len(m) - 300
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
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_4.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler
    assert not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    assert all(a.rsplit("-b", 1)[-1].isdigit() for a in adlar)


def test_roi_ve_iz_esleme():
    # 15m: dakika -> mum (yukarı yuvarlama)
    assert K.FrostStokBb3B0504.cikis_ayarlari.azalan_roi == ((0.0, 18.418), (3.0, 10.736), (7.0, 2.998), (30.0, 0.0))
    assert K.FrostStokBb3B0505.cikis_ayarlari.azalan_roi[-1] == (38.0, 0.0)           # 2273 dk / 60 -> 38
    assert K.IchimokuSkorB0621.cikis_ayarlari.azalan_roi == ((0.0, 64.2), (7.0, 37.0), (18.0, 11.8), (39.0, 0.0))
    assert K.FisherRsiHacimB0549.cikis_ayarlari.yalniz_karda_cikis
    assert K.IchimokuV12IkiGirisB0626.cikis_ayarlari.yalniz_karda_cikis
    # trailing: offset sonrası (True) -> min kâr = offset; False -> 0
    ca = K.OnurBbOrtaB0515.cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (29.3, 36.2)
    ca = K.FisherCciSslB0542.cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (7.8, 0.0)
    ca = K.HaSslMomMacdB0614.cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (1.0, 7.0)


def test_atr_stopu_stopsuz_kaynaklarda():
    for sinif in (K.OnurBbOrtaB0515, K.KcBbHaB0544, K.IchimokuBulutUstuB0625, K.IchimokuV12IkiGirisB0626,
                  K.Ichimoku2MumB0627, K.IchimokuHaUstB0628, K.IchimokuHaUstB0631):
        st, m, s = _sinyalli(sinif)
        long = s["yon"] == 1
        atr = K.g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
        assert np.allclose((m.loc[long, "kapanis"] - s.loc[long, "stop"]), 3.0 * atr[long]), sinif.__name__


def test_yuzde_stop_sinyal_kapanisindan():
    st, m, s = _sinyalli(K.MontrealBbRsiB0514)
    long = s["yon"] == 1
    assert np.allclose(s.loc[long, "stop"], m.loc[long, "kapanis"] * (1 - 0.28646))
    st, m, s = _sinyalli(K.SmaBbrsiEwoB0518)
    long = s["yon"] == 1
    assert np.allclose(s.loc[long, "stop"], m.loc[long, "kapanis"] * (1 - 0.178))


def test_kademe_ihlali_ve_kanca():
    # kâr > %3 -> kapanıştan %1,5 geride iz; en yüksek kapanış 106,5 (kâr %6,5 > %6 -> %2): stop 104,37
    kv = np.array([100.0, 103.5, 106.5, 104.0, 104.0])
    kademe = ((0.03, 0.015), (0.06, 0.02), (0.10, 0.03), (0.20, 0.05))
    assert not K._kademe_ihlali(kv, 0, 2, 100.0, kademe)
    assert K._kademe_ihlali(kv, 0, 3, 100.0, kademe)          # 104 <= 106,5 x 0,98 = 104,37
    assert not K._kademe_ihlali(np.array([100.0, 99.0, 98.0]), 0, 2, 100.0, kademe)   # kâr yok: iz yok
    st, m, s = _sinyalli(K.KcBbHaB0544)
    i = int(np.flatnonzero(s["yon"].to_numpy() == 1)[0]) + 1
    d = PozisyonDurumu(yon=1, giris_fiyati=float(m["acilis"].iloc[i]), giris_mum_indeksi=i, mum_indeksi=i, tutulan_mum=0,
                       en_yuksek=float(m["yuksek"].iloc[i]), en_dusuk=float(m["dusuk"].iloc[i]),
                       kapanis=float(m["kapanis"].iloc[i]), kar_yuzde=0.0)
    assert st.pozisyon_cikisi(d) in (False, True)


def test_sma_bbrsi_kanca_basamaklari():
    st, m, s = _sinyalli(K.SmaBbrsiEwoB0518)
    i = int(np.flatnonzero(s["yon"].to_numpy() == 1)[0]) + 1
    giris = float(m["acilis"].iloc[i])
    # kaynak testinde zirve kâr: yapay kapanış dizisi (kanca yalnız kendi sakladığı kapanışları okur)
    st._sakla(kap=np.r_[np.zeros(i), giris, giris * 1.02, giris * 1.0])
    d = PozisyonDurumu(yon=1, giris_fiyati=giris, giris_mum_indeksi=i, mum_indeksi=i + 2, tutulan_mum=2, en_yuksek=giris * 1.02,
                       en_dusuk=giris * 0.99, kapanis=giris, kar_yuzde=0.0)
    # zirve kâr %2 (> PF1 %1): stop kârı 0,009 + (0,02-0,01) x (0,043-0,009)/(0,048-0,01) = %1,8946; kâr %0 altında -> çık
    assert st.pozisyon_cikisi(d)
    d2 = PozisyonDurumu(yon=1, giris_fiyati=giris, giris_mum_indeksi=i, mum_indeksi=i + 2, tutulan_mum=2, en_yuksek=giris * 1.02,
                        en_dusuk=giris * 0.99, kapanis=giris * 1.02, kar_yuzde=2.0)
    st._sakla(kap=np.r_[np.zeros(i), giris, giris * 1.02, giris * 1.02])
    assert not st.pozisyon_cikisi(d2)
    # zirve kâr <= PF1: kanca çıkmaz (başlangıç stopu korur)
    st._sakla(kap=np.r_[np.zeros(i), giris, giris * 1.005, giris * 0.9])
    d3 = PozisyonDurumu(yon=1, giris_fiyati=giris, giris_mum_indeksi=i, mum_indeksi=i + 2, tutulan_mum=2, en_yuksek=giris * 1.005,
                        en_dusuk=giris * 0.9, kapanis=giris * 0.9, kar_yuzde=-10.0)
    assert not st.pozisyon_cikisi(d3)


def test_aksam_dojisi_yildizi_deseni():
    # 10 mum arka plan (küçük gövde), uzun beyaz, yukarı boşluklu doji, 1. gövdenin %30'undan fazla aşağı kapanan siyah mum
    n = 14
    ac = np.r_[np.full(10, 100.0), 100.0, 106.5, 106.0]
    kap = np.r_[np.full(10, 100.5), 106.0, 106.6, 102.0]
    yuk = np.maximum(ac, kap) + 0.3
    dus = np.minimum(ac, kap) - 0.3
    m = pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap}, index=pd.date_range("2020-01-01", periods=13, freq="4h"))
    r = K._aksam_dojisi_yildizi(m)
    assert bool(r.iloc[-1]) and not r.iloc[:-1].any()
    assert n == 14


def test_kesisim_skoru():
    x, y = np.array([2.0]), np.array([1.0])
    # x yukarı kesti (önceki x <= y), kesişim bulutun üstünde -> 2
    assert K._kesisim_skoru(x, y, np.array([0.0]), np.array([1.0]), np.array([0.2]), np.array([0.3]))[0] == 2.0
    # kesişim bulutun altında -> 0,5; içinde -> 1
    assert K._kesisim_skoru(x, y, np.array([0.0]), np.array([1.0]), np.array([5.0]), np.array([6.0]))[0] == 0.5
    assert K._kesisim_skoru(x, y, np.array([0.0]), np.array([1.0]), np.array([0.5]), np.array([6.0]))[0] == 1.0
    # aşağı kesiş, kesişim bulutun üstünde -> -0,5
    assert K._kesisim_skoru(np.array([0.0]), np.array([1.0]), np.array([2.0]), np.array([1.0]), np.array([0.2]), np.array([0.3]))[0] == -0.5


def test_t3_ve_ssl_nedensel():
    m = _mumlar("1h", 800)
    t3 = K._t3(m["kapanis"], 5)
    t3b = K._t3(m["kapanis"].iloc[:500], 5)
    pd.testing.assert_series_equal(t3.iloc[:500], t3b)
    dn, up = K._ssl(m["yuksek"], m["dusuk"], m["kapanis"], 20)
    assert (up.dropna() >= dn.dropna()).mean() > 0.4
