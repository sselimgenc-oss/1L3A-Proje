"""Meta-test betiği testleri: YALNIZ sentetik veri (gerçek veri okunmaz)."""
import itertools
import math

import numpy as np
import pandas as pd
import pytest

from araclar import meta_test_secim as m

UTC = "UTC"


def ts(s):
    return pd.Timestamp(s, tz=UTC)


def yap(ad, bas="2018-01-01", gun_r=None, islemler=None, etiket="trend", tf="1d", pf_islem=None):
    """gun_r: {tarih: R}; islemler: [(sembol, giris, cikis, r)]."""
    g = pd.Series({ts(k): v for k, v in (gun_r or {}).items()}, dtype=float)
    g.index = pd.DatetimeIndex(g.index)
    tr = pd.DataFrame([(s, ts(a), ts(b), r) for s, a, b, r in (islemler or [])], columns=["sembol", "giris", "cikis", "r"])
    if len(tr) == 0:
        tr = pd.DataFrame({"sembol": [], "giris": pd.DatetimeIndex([], tz=UTC), "cikis": pd.DatetimeIndex([], tz=UTC), "r": []})
    return m.sdata_olustur(ad, tf, etiket, ts(bas), g, tr, tr[["giris", "cikis", "r"]])


def uretken(ad, T, n_gun=1000, ort=0.05, tohum=1, etiket="trend", n_islem=400):
    """T'den önceki n_gun için günlük seri + n_islem işlem; ΣR>0, PF yüksek."""
    rng = np.random.default_rng(tohum)
    gunler = pd.date_range(T - pd.Timedelta(days=n_gun), T - pd.Timedelta(days=1), freq="D", tz=UTC)
    v = rng.normal(ort, 0.3, len(gunler))
    g = pd.Series(v, index=gunler)
    isl = []
    for i in range(n_islem):
        a = gunler[i * 2 % (len(gunler) - 5)]
        r = 1.0 if i % 3 else -0.5
        isl.append((f"S{i % 7}", a, a + pd.Timedelta(days=2), r))
    tr = pd.DataFrame(isl, columns=["sembol", "giris", "cikis", "r"])
    return m.sdata_olustur(ad, "1d", etiket, gunler[0], g, tr, tr[["giris", "cikis", "r"]])


# ---------------------------------------------------------------- kesimler / pencereler
def test_kesimler_sinirlari():
    k = m.kesimleri_uret()
    assert len(k) == 11
    assert k[0] == ts("2020-05-08") and k[1] == ts("2020-11-08") and k[-1] == ts("2025-05-08")
    assert all(b > a for a, b in zip(k, k[1:]))
    assert m.pencere_sonu(k[0]) == ts("2020-11-08")
    assert m.pencere_sonu(k[-1]) == m.HOLDOUT_BAS          # 2025-11-07 dahil biter


def test_pencere_holdouta_tasamaz():
    with pytest.raises(AssertionError):
        m.pencere_sonu(ts("2025-08-08"))
    with pytest.raises(AssertionError):
        m.pencere_sonu(ts("2025-05-08"), 12)


def test_kayma_ve_12ay_kesimleri():
    assert m.kesimleri_uret(adet=10, kayma_ay=3)[0] == ts("2020-08-08")
    assert [str(t.date()) for t in m.kesimleri_uret(adet=5, adim_ay=12)] == \
        ["2020-05-08", "2021-05-08", "2022-05-08", "2023-05-08", "2024-05-08"]


# ---------------------------------------------------------------- holdout verisi
def test_holdout_verisi_reddedilir():
    with pytest.raises(AssertionError):
        yap("a", gun_r={"2025-11-08": 1.0})
    with pytest.raises(AssertionError):
        yap("a", islemler=[("X", "2025-11-01", "2025-11-08", 1.0)])


def test_maks_tarih_dogrulamasi():
    m._MAKS_TARIH[0] = None
    yap("a", gun_r={"2025-11-07": 1.0})
    assert m.maks_tarih_dogrula() == ts("2025-11-07")
    m._MAKS_TARIH[0] = ts("2025-11-08")
    with pytest.raises(AssertionError):
        m.maks_tarih_dogrula()
    m._MAKS_TARIH[0] = None


def test_pencere_ve_geriye_bakis_ayrimi():
    # T'den sonraki veri geriye bakışa, T'den önceki veri ölçüme girmez
    T = ts("2021-05-08")
    gun = {"2020-05-01": 1.0, "2020-06-01": -1.0, "2021-05-07": 0.5, "2021-05-08": 100.0}
    sd = yap("a", gun_r=gun)
    g = m.geriye_bakis(sd, T)
    n = (T - ts("2018-01-01")).days
    a = np.zeros(n)
    a[(ts("2020-05-01") - ts("2018-01-01")).days] = 1.0
    a[(ts("2020-06-01") - ts("2018-01-01")).days] = -1.0
    a[(ts("2021-05-07") - ts("2018-01-01")).days] = 0.5
    assert g["uygun"] and g["sd"] == pytest.approx(a.std(ddof=1))
    assert g["puan"] == pytest.approx(a.mean() / a.std(ddof=1) * math.sqrt(n))     # 100.0 (T günü) dahil değil
    s, sc = m.olcum(sd, T, ts("2021-11-08"), g["sd"])
    assert s == pytest.approx(100.0)
    assert sc == pytest.approx(100.0 / (g["sd"] * math.sqrt((ts("2021-11-08") - T).days)))


def test_uygunluk_730_gun():
    gun = {"2018-03-01": 1.0, "2019-01-01": -1.0}
    sd = yap("a", bas="2018-01-01", gun_r=gun)
    assert not m.geriye_bakis(sd, ts("2019-12-31"))["uygun"]       # 729 gün
    assert m.geriye_bakis(sd, ts("2020-01-01"))["uygun"]            # 730 gün
    assert (ts("2020-01-01") - ts("2018-01-01")).days == 730


def test_sd_sifir_uygun_degil():
    assert not m.geriye_bakis(yap("a"), ts("2021-05-08"))["uygun"]


# ---------------------------------------------------------------- kapılar
def test_kapilar_gecer():
    T = ts("2021-05-08")
    sd = uretken("a", T)
    g = m.geriye_bakis(sd, T)
    assert g["g1"] and g["g2"] and g["g3"] and g["gecti"]
    assert g["pf"] >= 1.2


def test_g1_pf_esigi_ve_toplam():
    T = ts("2021-05-08")
    # ΣR > 0 ama PF < 1.2: 11 × (+1) ve 10 × (-1) -> PF 1.1
    isl = [("A", f"2020-0{1 + i % 9}-01", f"2020-0{1 + i % 9}-02", 1.0) for i in range(11)]
    isl += [("B", "2019-03-01", "2019-03-02", -1.0)] * 10
    sd = yap("a", gun_r={"2020-01-01": 1.0, "2020-02-01": -1.0}, islemler=isl)
    g = m.geriye_bakis(sd, T)
    assert g["sum_r"] == pytest.approx(1.0) and g["pf"] == pytest.approx(1.1) and not g["g1"]
    # PF tam 1.2: 12 / 10
    isl2 = isl + [("A", "2020-09-01", "2020-09-02", 1.0)]
    g2 = m.geriye_bakis(yap("a", gun_r={"2020-01-01": 1.0, "2020-02-01": -1.0}, islemler=isl2), T)
    assert g2["pf"] == pytest.approx(1.2) and g2["g1"]


def test_g2_islem_sayisi_siniri():
    # 2018-01-01 .. 2020-01-01 = 730 gün -> yıl 1.99863; eşik = 27 × 1.99863 = 53.96 -> 54 geçer, 53 geçmez
    T = ts("2020-01-01")

    def kur(n):
        isl = [("A" if i % 2 else "B", "2019-01-01", "2019-01-02", 1.0) for i in range(n)]
        isl += [("C", "2019-01-01", "2019-01-02", -0.1)]
        return yap("a", gun_r={"2019-01-01": 1.0, "2019-02-01": -1.0}, islemler=isl)
    assert not m.geriye_bakis(kur(52), T)["g2"]     # 53 işlem
    assert m.geriye_bakis(kur(53), T)["g2"]         # 54 işlem


def test_g3_en_iyi_enstruman_ve_yil():
    T = ts("2021-05-08")
    gun = {"2019-01-01": 1.0, "2019-02-01": -1.0}
    # tek enstrüman: çıkarınca 0 -> geçmez
    tek = [("A", "2019-05-01", "2019-05-02", 1.0)] * 5
    assert not m.geriye_bakis(yap("a", gun_r=gun, islemler=tek), T)["g3"]
    # iki enstrüman, biri hepsini taşıyor, diğeri negatif
    iki = [("A", "2019-05-01", "2019-05-02", 1.0)] * 5 + [("B", "2020-05-01", "2020-05-02", -0.1)]
    assert not m.geriye_bakis(yap("a", gun_r=gun, islemler=iki), T)["g3"]
    # iki enstrüman ve iki yıl, ikisi de pozitif
    ok = [("A", "2019-05-01", "2019-05-02", 1.0)] * 5 + [("B", "2020-05-01", "2020-05-02", 0.5)]
    assert m.geriye_bakis(yap("a", gun_r=gun, islemler=ok), T)["g3"]
    # iki enstrüman pozitif ama aynı yıl -> yıl çıkarınca 0 (boş) -> geçmez
    ayni = [("A", "2019-05-01", "2019-05-02", 1.0)] * 5 + [("B", "2019-06-01", "2019-06-02", 0.5)]
    assert not m.geriye_bakis(yap("a", gun_r=gun, islemler=ayni), T)["g3"]


def test_acik_islem_T_sonrasi_kapanan_sayilmaz():
    T = ts("2021-05-08")
    gun = {"2019-01-01": 1.0, "2019-02-01": -1.0}
    isl = [("A", "2021-05-01", "2021-05-08", 5.0)]      # çıkış = T -> kapanmış sayılmaz (çıkış < T şartı)
    g = m.geriye_bakis(yap("a", gun_r=gun, islemler=isl), T)
    assert g["n_islem"] == 0 and g["sum_r"] == 0.0


# ---------------------------------------------------------------- puan, yüzdelik, D_k
def test_t_istatistigi_puani():
    T = ts("2021-05-08")
    rng = np.random.default_rng(5)
    gun = {}
    d0 = ts("2019-01-01")
    vals = rng.normal(0.1, 1.0, 400)
    for i, v in enumerate(vals):
        gun[str((d0 + pd.Timedelta(days=i)).date())] = v
    sd = yap("a", gun_r=gun)
    g = m.geriye_bakis(sd, T)
    n = (T - ts("2018-01-01")).days
    a = np.zeros(n)
    a[(d0 - ts("2018-01-01")).days:(d0 - ts("2018-01-01")).days + 400] = vals
    assert g["puan"] == pytest.approx(a.mean() / a.std(ddof=1) * math.sqrt(n))


def test_yuzdelik_sira_eslik():
    p = m.yuzdelik_sira([5, 1, 3, 3, 9])
    # sıralar: 1->1, 3->2.5, 3->2.5, 5->4, 9->5 ; (r-1)/4*100
    assert list(p) == pytest.approx([75.0, 0.0, 37.5, 37.5, 100.0])
    assert m.yuzdelik_sira([2, 2, 2]).tolist() == [50.0, 50.0, 50.0]
    assert m.yuzdelik_sira([7]).tolist() == [50.0]
    assert m.yuzdelik_sira([1, 2]).tolist() == [0.0, 100.0]


def test_s_sec_kurallari():
    kim = [f"s{i}" for i in range(15)]
    puan = {k: float(i) for i, k in enumerate(kim)}
    # 12 geçen -> ilk 10 puana göre
    gec = set(kim[:12])
    S = m.s_sec(kim, puan, gec, set(kim))
    assert S == [f"s{i}" for i in range(11, 1, -1)]
    # 5 geçen -> hepsi
    assert len(m.s_sec(kim, puan, set(kim[:5]), set(kim))) == 5
    # 1 geçen -> N1'den puan sırasıyla 3'e tamamla
    S3 = m.s_sec(kim, puan, {"s0"}, set(kim[:8]))
    assert S3 == ["s0", "s7", "s6"]
    # 0 geçen
    assert m.s_sec(kim, puan, set(), set(kim[:8])) == ["s7", "s6", "s5"]
    # ilk_n=5
    assert len(m.s_sec(kim, puan, set(kim), set(kim), ilk_n=5)) == 5


def test_D_k_sema_kosusu_el_hesabi():
    """3 güçlü + 3 zayıf strateji, tek kesim; D_k el hesabı."""
    T = ts("2021-05-08")
    rng = np.random.default_rng(0)
    havuz = []
    for i in range(4):
        havuz.append(uretken(f"iyi{i}", T, tohum=i, ort=0.05 + 0.01 * i))
    # zayıf: ΣR>0 değil -> N1 dışı (negatif işlem)
    for i in range(3):
        g = pd.Series(rng.normal(-0.05, 0.3, 900), index=pd.date_range("2018-06-01", periods=900, freq="D", tz=UTC))
        tr = pd.DataFrame([("A", ts("2019-01-01"), ts("2019-01-02"), -1.0)], columns=["sembol", "giris", "cikis", "r"])
        havuz.append(m.sdata_olustur(f"kotu{i}", "1d", "donus", ts("2018-06-01"), g, tr, tr[["giris", "cikis", "r"]]))
    # ölçüm penceresine veri: iyiler pozitif, kötüler negatif
    for sd in havuz:
        o = m._gun_ofset(T)
        sd.gunluk[o:o + 180] = 0.2 if sd.ad.startswith("iyi") else -0.2
    res = m.sema_kos(havuz, [T], ilk_n=2)
    w = res["pencereler"][0]
    assert w["n_uygun"] == 7 and w["n_kapi_gecen"] == 4 and w["n_N1"] == 4 and w["n_S"] == 3   # ilk_n=2 < MIN_S=3 -> 3'e tamamlanır
    # iyiler: score eşit işaretli pozitif, sd'ye göre ölçeklenir -> iyiler en üst 4 sıra; kötüler alt 3 (eşit değil)
    P = {r["strateji"]: r["P"] for r in res["satirlar"]}
    assert min(P[f"iyi{i}"] for i in range(4)) > max(P[f"kotu{i}"] for i in range(3))
    s_adlari = [x.split("|")[0] for x in w["S"].split(";")]
    assert w["P_S"] == pytest.approx(np.mean([P[a] for a in s_adlari]))
    assert w["P_N1"] == pytest.approx(np.mean([P[f"iyi{i}"] for i in range(4)]))
    assert w["D_N1"] == pytest.approx(w["P_S"] - w["P_N1"])
    assert w["D_N2"] == pytest.approx(w["P_S"] - 50.0)
    assert w["D_N3"] == pytest.approx(w["D_N1"])      # S ve N1 aynı etiket (trend)


# ---------------------------------------------------------------- işaret çevirme
def test_isaret_cevirme_kaba_kuvvet():
    d = [3.0, -1.0, 2.5, 0.5, 4.0, -2.0, 1.0, 1.5, 0.2, -0.3, 2.0]
    r = m.isaret_cevirme(d)
    ort = [np.mean(np.array(d) * np.array(s)) for s in itertools.product([1, -1], repeat=11)]
    obs = np.mean(d)
    assert len(ort) == 2048 == r["desen"]
    assert r["p_yukari"] == pytest.approx(np.mean([x >= obs - 1e-12 for x in ort]))
    assert r["p_asagi"] == pytest.approx(np.mean([x <= obs + 1e-12 for x in ort]))
    assert r["dbar"] == pytest.approx(obs)


def test_isaret_cevirme_uc_durumlar():
    r = m.isaret_cevirme([1.0] * 11)       # tümü pozitif: yalnız bir desen >= gözlenen
    assert r["p_yukari"] == pytest.approx(1 / 2048) and r["p_asagi"] == 1.0
    r0 = m.isaret_cevirme([0.0] * 11)
    assert r0["p_yukari"] == 1.0 and r0["p_asagi"] == 1.0
    r5 = m.isaret_cevirme([2.0] * 5)
    assert r5["p_yukari"] == pytest.approx(1 / 32)


def test_guven_araligi():
    d = np.arange(11, dtype=float)
    lo, hi = m.guven_araligi_90(d)
    h = 1.812461 * d.std(ddof=1) / math.sqrt(11)
    assert lo == pytest.approx(5 - h) and hi == pytest.approx(5 + h)


# ---------------------------------------------------------------- karar kuralı
@pytest.mark.parametrize("dbar,py,pa,beklenen", [
    (5.0, 0.10, 0.95, "SEÇİM ÇALIŞIYOR"),
    (5.0, 0.1001, 0.95, "RASTGELEDEN AYIRT EDİLEMİYOR"),
    (4.99, 0.01, 0.99, "RASTGELEDEN AYIRT EDİLEMİYOR"),
    (-5.0, 0.95, 0.10, "SEÇİM ZARARLI"),
    (-5.0, 0.95, 0.11, "RASTGELEDEN AYIRT EDİLEMİYOR"),
    (-4.9, 0.95, 0.01, "RASTGELEDEN AYIRT EDİLEMİYOR"),
    (12.0, 0.5, 0.5, "RASTGELEDEN AYIRT EDİLEMİYOR"),
])
def test_karar_kurali(dbar, py, pa, beklenen):
    assert m.karar_etiketi(dbar, py, pa) == beklenen


def test_spearman_ve_rng_deterministik():
    assert m.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert m.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert math.isnan(m.spearman([1, 1, 1], [1, 2, 3]))
    T = ts("2021-05-08")
    havuz = [uretken(f"s{i}", T, tohum=i) for i in range(6)]
    a = m.sema_kos(havuz, [T], rng=np.random.default_rng(m.TOHUM))["pencereler"][0]["rastgele_p_yukari"]
    b = m.sema_kos(havuz, [T], rng=np.random.default_rng(m.TOHUM))["pencereler"][0]["rastgele_p_yukari"]
    assert a == b and 0 < a <= 1
