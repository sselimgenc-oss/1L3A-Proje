"""portfoy_boyutu.py testleri: YALNIZ sentetik veri (gerçek veri okunmaz)."""
import math

import numpy as np
import pandas as pd
import pytest

from araclar import meta_test_secim as mts
from araclar import portfoy_boyutu as pb

UTC = "UTC"


def ts(s):
    return pd.Timestamp(s, tz=UTC)


def uretken(ad, T, n_gun=1000, ort=0.05, tohum=1, n_islem=400, isaret=1.0):
    rng = np.random.default_rng(tohum)
    gunler = pd.date_range(T - pd.Timedelta(days=n_gun), T - pd.Timedelta(days=1), freq="D", tz=UTC)
    g = pd.Series(rng.normal(ort * isaret, 0.3, len(gunler)), index=gunler)
    isl = []
    for i in range(n_islem):
        a = gunler[i * 2 % (len(gunler) - 5)]
        r = (1.0 if i % 3 else -0.5) * isaret
        isl.append((f"S{i % 7}", a, a + pd.Timedelta(days=2), r))
    tr = pd.DataFrame(isl, columns=["sembol", "giris", "cikis", "r"])
    return mts.sdata_olustur(ad, "1d", "trend", gunler[0], g, tr, tr[["giris", "cikis", "r"]])


# ---------------------------------------------------------------- para hesabı
def test_strateji_kill_ve_dondurma():
    R = np.full((1, 8), -10.0)                       # her gün x0.85
    V, kd = pb.strateji_kasa_yollari(R)
    assert kd[0] == 3                                # 250·0.85³ = 153.5 <= 175
    assert V[0, 3] == pytest.approx(250 * 0.85 ** 3)
    assert np.allclose(V[0, 3:], V[0, 3])            # kalan günlerde durur


def test_kill_olmayan_strateji():
    V, kd = pb.strateji_kasa_yollari(np.full((1, 5), 1.0))
    assert kd[0] == pb.BUYUK and V[0, -1] == pytest.approx(250 * 1.015 ** 5)


def test_strateji_zirveden_olcer():
    R = np.array([[20.0, 0.0, -10.0, -10.0, -10.0, 0.0]])   # x1.3 sonra zirve 325; 0.85'lerle 325·0.85² = 234.8 > 227.5 ; ³ = 199.6 <= 227.5
    V, kd = pb.strateji_kasa_yollari(R)
    assert V[0, 1] == pytest.approx(325.0)
    assert kd[0] == 5


def test_hesap_kill_ve_dondurma():
    R = np.full((1, 10), -4.0)                       # her gün x0.94
    V, kd = pb.strateji_kasa_yollari(R)
    o = pb.portfoy_olc(V, kd, np.array([[1.0]]), np.array([[0]]))
    # 0.94⁴ = 0.7807 <= 0.8 -> hesap 4. gün durur; strateji kill (0.94⁶ = 0.69) hesap durduktan sonra -> sayılmaz
    assert o["hesap_kill"][0] == 1.0 and o["strateji_kill"][0] == 0.0
    assert o["dd"][0] == pytest.approx(100 * (1 - 0.94 ** 4))
    assert o["getiri"][0] == pytest.approx(100 * (0.94 ** 4 - 1))


def test_strateji_kill_hesap_kill_olmadan():
    R = np.vstack([np.full(6, -10.0), np.zeros(6)])  # biri 153.5'e iner, toplam 403.5 / 500 = 0.807 > 0.8
    V, kd = pb.strateji_kasa_yollari(R)
    o = pb.portfoy_olc(V, kd, np.array([[1.0, np.nan], [np.nan, 1.0]]), np.array([[0, 1]]))
    assert o["strateji_kill"][0] == 1.0 and o["hesap_kill"][0] == 0.0
    assert o["getiri"][0] == pytest.approx(100 * ((250 * 0.85 ** 3 + 250) / 500 - 1))


def test_hesap_kill_uygula_zirve_baslangic_dahil():
    don, ka = pb.hesap_kill_uygula(np.array([[100.0, 90.0, 80.0, 120.0]]))
    assert ka[0] == 2 and np.allclose(don, [[100.0, 90.0, 80.0, 80.0]])


def test_max_dusus():
    assert pb.max_dusus_yuzde(np.array([[100.0, 120.0, 90.0, 130.0]]))[0] == pytest.approx(25.0)


def test_korelasyon_matrisi_ve_ortalama():
    R = np.array([[1.0, -1.0, 2.0, 0.0], [2.0, -2.0, 4.0, 0.0], [-1.0, 1.0, -2.0, 0.0], [0.0, 0.0, 0.0, 0.0]])
    C = pb.korelasyon_matrisi(R)
    assert C[0, 1] == pytest.approx(1.0) and C[0, 2] == pytest.approx(-1.0) and math.isnan(C[0, 3])
    m = pb.ort_korelasyon(C, np.array([[0, 1, 2], [0, 1, 3], [0, 0 + 1, 1]]))
    assert m[0] == pytest.approx((1 - 1 - 1) / 3)    # (0,1)=1, (0,2)=-1, (1,2)=-1
    assert m[1] == pytest.approx(1.0)                # NaN çiftler atlanır
    assert math.isnan(pb.ort_korelasyon(C, np.array([[0]]))[0])


# ---------------------------------------------------------------- kesim: filtreler, atlama, tekrarlanabilirlik
def test_kesim_gecenler_filtre_ve_siralama():
    T = ts("2021-05-08")
    iyi1, iyi2 = uretken("a", T, ort=0.05, tohum=1), uretken("b", T, ort=0.15, tohum=2)
    kotu = uretken("c", T, ort=0.05, tohum=3, isaret=-1.0)                 # ΣR < 0 -> G1 kalır
    kisa = uretken("d", T, n_gun=300, tohum=4)                              # < 730 gün -> uygun değil
    g = pb.kesim_gecenler([kotu, iyi1, kisa, iyi2], T)
    assert [sd.ad for sd, _ in g] == ["b", "a"]
    assert g[0][1] >= g[1][1]


def test_kesim_kos_atlama_ve_tohum():
    T = ts("2021-05-08")
    son = mts.pencere_sonu(T)
    havuz = [uretken(f"s{i}", T, ort=0.05 + 0.01 * i, tohum=10 + i) for i in range(4)]
    # pencereye günlük R yaz
    for i, sd in enumerate(havuz):
        o1, o2 = mts._gun_ofset(T), mts._gun_ofset(son)
        sd.gunluk[o1:o2] = np.random.default_rng(100 + i).normal(0.1, 0.5, o2 - o1)
    gecen = pb.kesim_gecenler(havuz, T)
    assert len(gecen) == 4
    s1 = pb.kesim_kos(gecen, T, son, np.random.default_rng(5), cekilis=50)
    s2 = pb.kesim_kos(gecen, T, son, np.random.default_rng(5), cekilis=50)
    pd.testing.assert_frame_equal(pd.DataFrame(s1), pd.DataFrame(s2))       # tohumla tekrarlanabilir
    Nler = sorted({r["N"] for r in s1})
    assert Nler == [1, 2, 3, 4]                                             # 6, 8, 10 atlandı (kapı geçen 4)
    ust4 = [r for r in s1 if r["tur"] == "ust" and r["N"] == 4][0]
    ras4 = [r for r in s1 if r["tur"] == "rastgele" and r["N"] == 4][0]
    assert ust4["getiri"] == pytest.approx(ras4["getiri"])                  # N = G: her çekiliş aynı küme
    assert ras4["getiri_p5"] == pytest.approx(ras4["getiri_p95"])
    ust1 = [r for r in s1 if r["tur"] == "ust" and r["N"] == 1][0]
    en_iyi = gecen[0][0]
    R = pb.pencere_R(en_iyi, T, son)
    V, _ = pb.strateji_kasa_yollari(R[None, :])
    assert ust1["getiri"] == pytest.approx(100 * (V[0, -1] / 250 - 1))      # üst-1 = puanı en yüksek stratejinin kendi kasası
    assert math.isnan(ust1["korelasyon"])


def test_toplulastir_ve_doyma():
    satir = []
    dd = {1: 30.0, 2: 20.0, 3: 15.0, 4: 14.5, 6: 14.0, 8: 13.9, 10: 13.8}
    for N, d in dd.items():
        for k in ("a", "b"):
            satir.append({"tur": "ust", "N": N, "kesim": k, "n_gecen": 10, "n_cekilis": 1, "getiri": 5.0, "dd": d,
                          "hesap_kill": 0.0, "strateji_kill": 0.0, "korelasyon": 0.1,
                          **{f"getiri_p{q}": 5.0 for q in pb.YUZDELIKLER}, **{f"dd_p{q}": d for q in pb.YUZDELIKLER},
                          "dd_maks_cekilis": d})
    tab = pb.toplulastir(pd.DataFrame(satir), 3)
    assert (tab["n_kesim_atlanan"] == 1).all()
    assert pb.doyma_noktasi(tab, "ust") == 3          # 15 -> 14.5: iyileşme 0.5 < 1
    assert pb.doyma_noktasi(tab, "rastgele") is None


# ---------------------------------------------------------------- tarih sert doğrulama
def test_holdout_tarihi_kabul_edilmez(monkeypatch):
    with pytest.raises(AssertionError):
        mts.pencere_sonu(ts("2025-08-08"))
    monkeypatch.setattr(mts, "_MAKS_TARIH", [None])
    mts._gor(ts("2025-11-07"))
    assert mts.maks_tarih_dogrula() == ts("2025-11-07")
    mts._gor(ts("2025-11-08"))
    with pytest.raises(AssertionError):
        mts.maks_tarih_dogrula()
    g = pd.Series([1.0], index=pd.DatetimeIndex([ts("2025-11-08")]))
    bos = pd.DataFrame({"sembol": [], "giris": pd.DatetimeIndex([], tz=UTC), "cikis": pd.DatetimeIndex([], tz=UTC), "r": []})
    with pytest.raises(AssertionError):
        mts.sdata_olustur("x", "1d", "t", ts("2018-01-01"), g, bos, bos[["giris", "cikis", "r"]])
