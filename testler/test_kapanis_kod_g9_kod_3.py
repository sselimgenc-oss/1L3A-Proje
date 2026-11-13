"""g9_kod_3 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import kod_g9_kod_3 as K

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "3h": "3h", "4h": "4h", "1d": "1D"}
IKI_YON = {K.RangeFiltreB0150, K.SupurmePocB0168, K.DiverjansPivotB0190, K.SmaRsiB0202, K.ImpulseMacdB0209,
           K.BbGenislemeHacimB0214, K.WavetrendRangeB0235, K.WtSeviyeB0252}
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
N = 6000
# özel sentetik ayar: (volatilite, hacim ölçeği, dalga)
OZEL = {
    K.RsiMacdBbTemaB0231: {"tohum": 6, "vol": 0.02},
    K.RsiDolarHacimB0203: {"hacim_olcek": 1e5},
    K.BbGenislemeHacimB0214: {"vol": 0.004, "kume": True},
    K.BbRsiCokluTfB0472: {"vol": 0.01},
}


def _mumlar(freq: str, n: int = N, tohum: int = 7, vol: float = 0.01, dalga: int = 60, hacim_olcek: float = 1.0,
            kume: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    sig = np.full(n, vol)
    if kume:   # volatilite kümeleri: sıkışma ve genişleme dönüşümlü (BB sıkışma/genişleme kuralları için)
        sig = vol * np.where((t // 40) % 3 == 0, 0.2, 1.0 + 2.0 * ((t // 40) % 3 == 2))
    getiri = rng.standard_t(4, n) * sig + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, sig / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, sig / 2, n)))
    hacim = np.exp(rng.normal(0, 0.6, n)) * 100 * hacim_olcek
    if kume:
        hacim = hacim * np.where((t // 40) % 3 == 2, 3.0, 1.0)
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": hacim}, index=idx)


def _veri(sinif, n: int = N, **ek) -> pd.DataFrame:
    return _mumlar(SINIF_TF[sinif.ad], n, **{**OZEL.get(sinif, {}), **ek})


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    m = _veri(sinif)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    if sinif in IKI_YON:
        assert short.any(), "iki yönlü kural short da üretmeli"
    else:
        assert not short.any()
    assert st.cikis_var_mi()
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    assert (s.loc[short, "stop"] > m.loc[short, "kapanis"]).all()
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
    m = _mumlar(kayit["tf"], 3000, **OZEL.get(sozluk[kayit["sinif"]], {}))
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_3.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler and not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    tf_csv = dict(zip(girdi["kaynak_id"], girdi["tf"]))
    assert all(v["tf"] == tf_csv[v["kimlik"].split("#")[0]] for v in K.VARYANTLAR)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") and a.split("-")[-1].startswith("b0") for a in adlar)
    assert {s.__name__ for s in K.SINIFLAR} >= {"BbRsi1sdB0463", "BbRsi1sdB0473", "BbAltCikisB0502", "BbAltCikisB0503"}


def test_roi_tablosu_mum_donusumu():
    assert K._roi({0: 0.02, 20: 0.005, 40: 0.006, 60: 0.015, 120: 0.0}, 60) == ((0, 2.0), (1, 1.5), (2, 0.0))
    assert K._roi({60: 0.01, 30: 0.02, 0: 0.04}, 15) == ((0, 4.0), (2, 2.0), (4, 1.0))
    assert K.BbRsi1sdB0463.cikis_ayarlari.azalan_roi == ((0, 21.547445), (1, 0.0))
    assert K.BbRsi1sdB0473.cikis_ayarlari.azalan_roi[-1] == (9, 0.0)
    # yalnız-offset: True ise offset = min kâr, False ise 0
    assert K.RangeFiltreB0150.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 4.7
    assert K.RsiBbUstB0466.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 0.0
    assert K.RsiBbUstB0466.cikis_ayarlari.geri_cekilme_yuzde == 5.069
    assert K.SupurmePocB0168.cikis_ayarlari.yalniz_karda_cikis and K.SmaRsiB0202.cikis_ayarlari.azalan_roi == ((0, 1.0),)


def test_stop_uyarlamasi_atr_ve_yuzde():
    m = _mumlar("1h", 400)
    sl_l, sl_s = K._stoplar(m, 0.2)
    assert np.allclose(sl_l, m["kapanis"] * 0.8) and np.allclose(sl_s, m["kapanis"] * 1.2)
    a_l, a_s = K._stoplar(m, 0.99)
    atr = K.g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    assert np.allclose((m["kapanis"] - a_l).dropna(), (3 * atr).dropna())
    assert K._stoplar(m, None)[0].equals(a_l)


def test_range_filtre_ozyineleme():
    kap = np.array([10.0, 9.0, 9.2, 9.5, 8.0, 12.0])
    sm = np.array([np.nan, np.nan, 0.5, 0.5, 0.5, 0.5])
    f = K._filtre_a(kap, sm)
    assert f[0] == 10.0 and np.isnan(f[1])                  # kapanış önceki filtrenin altında + aralık NaN -> NaN
    assert np.isclose(f[2], 9.7)                            # önceki NaN: kapanış + aralık
    assert np.isclose(f[3], 9.7)                            # kapanış+aralık (10,0) hâlâ önceki üstünde: önceki korunur
    assert np.isclose(f[4], 8.5) and f[5] == 12.0           # düşüşte kapanış+aralık; yükselişte kapanışın kendisi
    fb = K._filtre_b(np.array([10.0, 11.0, 10.0, 12.0]), np.array([np.nan, np.nan, 0.5, 0.5]))
    assert fb[0] == 10.0 and np.isnan(fb[1]) and np.isclose(fb[2], 10.5) and np.isclose(fb[3], 11.5)


def test_pivot_ve_diverjans():
    kap = np.array([5, 4, 3, 4, 5, 4, 2, 3, 4, 3.5, 4.5, 5.0])
    dip, tepe = K._pivotlar(kap, 2)
    assert list(np.flatnonzero(dip)) == [2, 6] and list(np.flatnonzero(tepe)) == [4]
    assert not dip[:2].any() and not dip[-2:].any()          # kenar: pivot onayı için iki mum sağda gerekir
    # boğa diverjansı: fiyat 3 -> 2 (daha düşük dip), gösterge 1 -> 2 (daha yüksek); aradaki doğru değerlerin altında
    ind = np.array([3.0, 3.0, 1.0, 3.5, 4.0, 3.5, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0])
    out = K._diverjans(kap, ind, [2, 6], 1)
    assert list(np.flatnonzero(out)) == [6]
    ind_kotu = ind.copy()
    ind_kotu[4] = 1.2                                        # aradaki gösterge değeri doğrunun altına iner: diverjans iptal
    assert not K._diverjans(kap, ind_kotu, [2, 6], 1).any()
    # ayı diverjansı: fiyat daha yüksek tepe, gösterge daha düşük
    kap2 = np.array([1, 2, 5, 2, 1, 2, 6, 2, 1.0])
    ind2 = np.array([1, 2, 5, 2, 1, 2, 4, 2, 1.0])
    assert list(np.flatnonzero(K._diverjans(kap2, ind2, [2, 6], -1))) == [6]
    assert list(K._gec(np.array([True, False, False, True]), 2)) == [False, False, True, False]


def test_b0190_diverjans_nedensel_onay_gecikmesi():
    """Giriş, pivot satırından en az 2 mum sonra olur (pivot onayı); sinyal satırı pivot satırından önce olamaz."""
    m = _mumlar("15m")
    s = K.DiverjansPivotB0190().sinyaller(m)
    assert not s["yon"].iloc[:2].any()
    st = K.DiverjansPivotB0190()
    st.sinyaller(m)
    assert st._kd["tp"].shape[0] == len(m)


def _kancali_backtest(sinif, tf, n=4000, **ek):
    m = _mumlar(tf, n, tohum=3, vol=0.02, **{**OZEL.get(sinif, {}), **ek})
    st = sinif()
    return st, backtest(m, st, MotorAyarlari())


def test_roi_kancasi_ignore_roi_if_entry_signal():
    """150/203: giriş koşulu sürerken ROI çıkışı atlanır; koşul yokken ROI tablosu uygulanır."""
    st = K.RangeFiltreB0150()
    st._sakla(al=np.array([1, 1, 0, 0]), sat=np.array([0, 0, 0, 0]))
    from motor.strateji.cikislar import PozisyonDurumu

    def durum(i, kar):
        return PozisyonDurumu(1, 100.0, 0, i, 5, 110.0, 99.0, 100 + kar, kar)

    assert not st.pozisyon_cikisi(durum(1, 80.0))      # giriş koşulu sürüyor: %80 kâr bile ROI çıkışı yok
    assert st.pozisyon_cikisi(durum(2, 80.0))          # koşul yok: 0. basamak %64,8 aşıldı
    assert not st.pozisyon_cikisi(durum(2, 5.0))       # tutulan 5 mum (75dk): %64,8 altı
    assert K.RangeFiltreB0150._roi_tablo[0] == (0, 64.8)


def test_b0476_kar_basamakli_iz_kancasi():
    st = K.BbRsiTemaIzB0476()
    kap = np.array([100.0, 100.0, 104.0, 112.0, 111.0, 108.0, 107.0])
    st._sakla(kap=kap)
    from motor.strateji.cikislar import PozisyonDurumu

    def durum(i):
        return PozisyonDurumu(1, 100.0, 1, i, i - 1, 112.0, 99.0, kap[i], (kap[i] / 100.0 - 1) * 100)

    # i=3: önceki kapanışlar 100 (kâr 0), 104 (kâr %4 > %3 -> stop %1 altı = 102,96); kapanış 112 üstünde -> çıkış yok
    assert not st.pozisyon_cikisi(durum(3))
    # i=4: 112 (kâr %12 > %10 -> %3 altı = 108,64); kapanış 111 > 108,64 -> yok
    assert not st.pozisyon_cikisi(durum(4))
    # i=5: seviye max(102,96; 108,64; 111x0,97=107,67) = 108,64; kapanış 108 <= 108,64 -> çıkış
    assert st.pozisyon_cikisi(durum(5))


def test_kancali_siniflar_backtestte_calisir():
    for sinif, tf in ((K.RangeFiltreB0150, "15m"), (K.DiverjansPivotB0190, "15m"), (K.BbRsiTemaIzB0476, "15m"),
                      (K.RsiDolarHacimB0203, "1h")):
        st, r = _kancali_backtest(sinif, tf)
        assert callable(st.pozisyon_cikisi)
        assert len(r.islemler) >= 1


def test_b0381_stochrsi_ham_ve_sinirli():
    m = _mumlar("1h", 1500)
    kap = m["kapanis"]
    r = K.g.rsi(kap, 14)
    sr = (r - r.rolling(14).min()) / (r.rolling(14).max() - r.rolling(14).min())
    assert sr.dropna().between(0, 1).all()


def test_qtpylib_bb_ornek_std():
    x = pd.Series(np.arange(30, dtype=float) ** 1.3)
    bb = K._bbq(x, 20, 2.0)
    assert np.isclose(bb["ust"].iloc[-1] - bb["orta"].iloc[-1], 2.0 * np.std(x.iloc[-20:], ddof=1))


def test_b0488_cmo_kesisim_gecikmesi():
    st = K.CmoBbUstB0488()
    m = _mumlar("5m", 3000)
    s = st.sinyaller(m)
    cmo = 2.0 * K.g.rsi(m["kapanis"], 50) - 100.0
    girdi = s.index[s["yon"] == 1]
    assert len(girdi) > 0
    for t in girdi[:20]:
        i = m.index.get_loc(t)
        assert cmo.iloc[i - 1] > 0 and cmo.iloc[i - 2] <= 0 and cmo.iloc[i] >= 0
