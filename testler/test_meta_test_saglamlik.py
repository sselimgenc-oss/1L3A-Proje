"""meta_test_saglamlik.py testleri: YALNIZ sentetik veri (gerçek veri okunmaz)."""
import math

import numpy as np
import pandas as pd
import pytest

from araclar import meta_test_saglamlik as sg
from araclar import meta_test_secim as mts

UTC = "UTC"


def ts(s):
    return pd.Timestamp(s, tz=UTC)


def yaz(kok, ad, tf, sembol, islemler):
    """islemler: [(yon, giris, cikis, r)]; ham x1/x2 + mtm x2 parquet yazar (kum_r doğrusal -> son değer = r)."""
    for alt in ("ham/x1", "ham/x2", "mtm/x2"):
        (kok / alt).mkdir(parents=True, exist_ok=True)
    ham = pd.DataFrame({"giris_zamani": [ts(a) for _, a, _, _ in islemler], "cikis_zamani": [ts(b) for _, _, b, _ in islemler],
                        "yon": np.array([y for y, _, _, _ in islemler], dtype=np.int8),
                        "r": np.array([r for _, _, _, r in islemler], dtype=np.float32),
                        "fonlama_r": np.zeros(len(islemler), dtype=np.float32)})
    satir = []
    for no, (_, a, b, r) in enumerate(islemler):
        gunler = pd.date_range(ts(a), ts(b), freq="D")
        for i, g in enumerate(gunler):
            satir.append((no, g, r * (i + 1) / len(gunler)))
    mtm = pd.DataFrame(satir, columns=["islem_no", "gun", "kum_r"])
    mtm["islem_no"] = mtm["islem_no"].astype("int32")
    mtm["kum_r"] = mtm["kum_r"].astype("float32")
    ad_tf = f"{ad}--{tf}--{sembol}.parquet"
    ham.to_parquet(kok / "ham/x1" / ad_tf)
    ham.to_parquet(kok / "ham/x2" / ad_tf)
    mtm.to_parquet(kok / "mtm/x2" / ad_tf)


@pytest.fixture
def kok(tmp_path):
    isl_a = [(1, "2019-03-01", "2019-03-05", 2.0), (-1, "2019-04-01", "2019-04-03", -1.0), (-1, "2019-05-01", "2019-05-04", 3.0),
             (1, "2025-11-01", "2025-11-20", 5.0)]                         # sonuncusu holdout'a taşar -> süzülür
    isl_b = [(1, "2019-03-10", "2019-03-12", 1.0), (-1, "2019-06-01", "2019-06-02", 0.5)]
    yaz(tmp_path, "st", "1d", "AAA", isl_a)
    yaz(tmp_path, "st", "1d", "BBB", isl_b)
    eleme = pd.DataFrame({"strateji": ["st"], "tf": ["1d"], "etiket": ["trend"], "analiz_bas": ["2018-01-01 00:00:00+00:00"],
                          "durum": ["elendi"]})
    return tmp_path, eleme


def toplam(sd):
    return float(sd.gunluk.sum())


def test_yukle_tam_ve_holdout_suzgeci(kok):
    k, el = kok
    (sd,), _ = sg.havuz_yukle(k, el)
    assert toplam(sd) == pytest.approx(2.0 - 1.0 + 3.0 + 1.0 + 0.5)       # holdout işlemi (5.0) yok
    assert len(sd.r2) == 5


def test_enstruman_filtresi(kok):
    k, el = kok
    (sd,), _ = sg.havuz_yukle(k, el, sembol_filtre={"BBB"})
    assert toplam(sd) == pytest.approx(1.5) and len(sd.r2) == 2
    hv, b = sg.havuz_yukle(k, el, sembol_filtre={"ZZZ"})
    assert hv == [] and b["dosyasiz_satir_n"] == 1


def test_short_filtresi_ve_geri_yukleme(kok):
    k, el = kok
    orijinal = mts._ham_suz
    (sd,), _ = sg.havuz_yukle(k, el, yon=sg.SHORT)
    assert mts._ham_suz is orijinal                                        # süzgeç geri alındı
    assert toplam(sd) == pytest.approx(-1.0 + 3.0 + 0.5) and len(sd.r2) == 3
    (sl,), _ = sg.havuz_yukle(k, el, yon=sg.LONG)
    assert toplam(sl) == pytest.approx(2.0 + 1.0)                          # holdout long'u yok
    assert toplam(sd) + toplam(sl) == pytest.approx(toplam(sg.havuz_yukle(k, el)[0][0]))


def test_bilinmeyen_yon_hatasi(kok):
    k, el = kok
    yaz(k, "st", "1d", "CCC", [(0, "2019-03-01", "2019-03-02", 1.0)])
    with pytest.raises(AssertionError):
        sg.havuz_yukle(k, el, yon=sg.SHORT)
    assert mts._ham_suz.__name__ == "_ham_suz"


def test_enstruman_toplami_tam_veriye_esit(kok):
    k, el = kok
    tam = sg.havuz_yukle(k, el)[0][0]
    parca = sum(sg.havuz_yukle(k, el, sembol_filtre={s})[0][0].gunluk for s in ("AAA", "BBB"))
    assert np.allclose(parca, tam.gunluk)


def test_pencereden_cikar_yalniz_pencerede(kok):
    k, el = kok
    tam = sg.havuz_yukle(k, el)[0]
    ins = {s: {sd.kimlik: sd.gunluk for sd in sg.havuz_yukle(k, el, sembol_filtre={s})[0]} for s in ("AAA", "BBB")}
    T, son = ts("2019-04-01"), ts("2019-07-01")                           # pencere: AAA'nın 2 short'u + BBB'nin short'u
    (m,) = sg.pencereden_cikar(tam, ins, T, son, ["AAA"])
    o1, o2 = mts._gun_ofset(T), mts._gun_ofset(son)
    assert m.gunluk[o1:o2].sum() == pytest.approx(0.5)                     # yalnız BBB kaldı
    assert np.allclose(m.gunluk[:o1], tam[0].gunluk[:o1])                  # geriye bakış aynı
    assert np.allclose(m.gunluk[o2:], tam[0].gunluk[o2:])
    assert m.g2 is tam[0].g2 or np.array_equal(m.g2, tam[0].g2)            # işlem listesi (kapılar) değişmez
    (m2,) = sg.pencereden_cikar(tam, ins, T, son, ["AAA", "BBB"])
    assert (m2.gunluk[o1:o2] == 0).all()                                   # kayan nokta artığı yok


def test_yon_tablosu_ve_long_payi(kok):
    k, el = kok
    tab = sg.yon_tablosu(k, el)
    g, c, y = tab["st|1d"]
    assert len(y) == 5 and (y == sg.LONG).sum() == 2
    lp = sg.long_payi(tab, ["st|1d"], ts("2019-04-15"), ts("2019-12-31"))
    assert lp["lb_n"] == 3 and lp["lb_long_payi"] == pytest.approx(2 / 3)  # çıkış < T: 2 long (AAA, BBB) + 1 short (AAA 04-01)
    assert lp["ol_n"] == 2 and lp["ol_long_payi"] == 0.0


# ---------------------------------------------------------------- B2 kazananlar
def seri(baslangic, fiyatlar):
    return pd.Series(fiyatlar, index=pd.date_range(baslangic, periods=len(fiyatlar), freq="D", tz=UTC), dtype=float)


def test_al_tut_ve_kazananlar():
    T, son = ts("2020-05-08"), ts("2020-11-08")
    gun = (son - ts("2020-04-01")).days
    s = {"A": seri("2020-04-01", np.linspace(100, 200, gun)), "B": seri("2020-04-01", np.linspace(100, 110, gun)),
         "C": seri("2020-04-01", np.linspace(100, 300, gun)), "D": seri("2020-08-01", np.linspace(10, 500, 100))}   # D: T'de veri yok
    k = sg.kazananlar(s, T, son, adet=2)
    assert [x for x, _ in k] == ["C", "A"]
    assert sg.al_tut(s["D"], T, son) is None
    r = sg.al_tut(s["B"], T, son)
    a = s["B"][s["B"].index < T].iloc[-1]
    b = s["B"][s["B"].index < son].iloc[-1]
    assert r == pytest.approx(b / a - 1)


def test_gunluk_kapanis_holdout_sizdirmaz(monkeypatch):
    monkeypatch.setattr(mts, "_MAKS_TARIH", [None])
    idx = pd.date_range("2025-11-06 00:00", periods=96, freq="h", tz=UTC)
    df = pd.DataFrame({"kapanis": np.arange(96, dtype=float)}, index=idx)
    s = sg.gunluk_kapanis(df)
    assert s.index.max() == ts("2025-11-07") and s.iloc[-1] == 47.0       # 2025-11-07 son saat 23:00 -> 47
    assert mts.maks_tarih_dogrula() < mts.HOLDOUT_BAS


# ---------------------------------------------------------------- istatistik ve yorum
def test_d_istatistik_ve_yorum():
    r = sg.d_istatistik([5.0, 3.0, -1.0, 4.0])
    assert r["dbar"] == pytest.approx(2.75) and r["pozitif_pencere"] == 3 and r["n"] == 4
    assert 0 < r["p_yukari"] < 1 and r["p_asagi"] <= 1
    oz = {"B1": {"dbar": 1.0}, "B2": {"dbar": 2.0}, "B3": {"dbar": 3.0}}
    assert "zayıflar" in sg.yorum_metni(oz)
    oz["B3"]["dbar"] = -0.5
    t = sg.yorum_metni(oz)
    assert "B3" in t and "B1" not in t
