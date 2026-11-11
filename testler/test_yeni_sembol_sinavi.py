"""Yeni sembol sınavı betiği testleri: YALNIZ küçük sentetik girdi (ağ/gerçek veri yok)."""
import numpy as np
import pandas as pd
import pytest

from araclar import yeni_sembol_sinavi as y

S = y.SECIM_TARIHI


def bilgi(satirlar):
    """(sembol, ilk_mum, son_mum, hacim) -> DataFrame"""
    return pd.DataFrame([{"sembol": a, "ilk_mum": pd.Timestamp(b, tz="UTC"), "son_mum": pd.Timestamp(c, tz="UTC"), "hacim_30g": h}
                         for a, b, c, h in satirlar])


UZUN = "2020-01-01"
SON = "2026-11-10"


def test_secim_kurallari_ve_hariclar():
    d = bilgi([
        ("AAAUSDT", UZUN, SON, 100.0),
        ("BBBUSDT", UZUN, "2024-05-01", 90.0),            # sonradan delist: DAHİL
        ("CCCUSDT", "2022-06-01", SON, 500.0),            # < 730 gün geçmiş: elenir
        ("DDDUSDT", UZUN, "2023-10-30", 400.0),           # S'de işlem yok
        ("BTCUSDT", UZUN, SON, 1e6),                      # hariç liste
        ("USDCUSDT", UZUN, SON, 1e5),                     # stablecoin
        ("DEFIUSDT", UZUN, SON, 1e5),                     # endeks
        ("EEEUSDT_240329", UZUN, "2024-03-29", 50.0),     # teslimli
        ("EEEUSDC", UZUN, SON, 50.0),                     # quote USDT değil
        ("FFFUSDTSETTLED", UZUN, SON, 50.0),
        ("1000SHIBUSDT", UZUN, SON, 80.0),                # ikinci kontrat çifti
        ("SHIBUSDT", UZUN, SON, 70.0),
        ("GGGUSDT", "2021-11-01", SON, 60.0),             # tam 730 gün: kalır
        ("HHHUSDT", "2021-11-02", SON, 65.0),             # 729 gün: elenir
        ("NOVOLUSDT", UZUN, SON, float("nan")),           # S öncesi 30g mum yok
    ])
    r = y.aday_sec(d).set_index("sembol")
    assert r.loc["AAAUSDT", "neden"] == "" and r.loc["BBBUSDT", "neden"] == ""
    assert r.loc["CCCUSDT", "neden"] == "gecmis_730g_yok"
    assert r.loc["DDDUSDT", "neden"] == "S_de_islem_yok"
    assert r.loc["BTCUSDT", "neden"] == "haric_liste"
    assert r.loc["USDCUSDT", "neden"] == "stablecoin"
    assert r.loc["DEFIUSDT", "neden"] == "endeks_kontrat"
    assert r.loc["EEEUSDT_240329", "neden"] == "usdt_surekli_degil"
    assert r.loc["EEEUSDC", "neden"] == "usdt_surekli_degil"
    assert r.loc["FFFUSDTSETTLED", "neden"] == "usdt_surekli_degil"
    assert r.loc["1000SHIBUSDT", "neden"] == "" and r.loc["SHIBUSDT", "neden"] == "ikinci_kontrat"
    assert r.loc["GGGUSDT", "neden"] == "" and r.loc["HHHUSDT", "neden"] == "gecmis_730g_yok"
    assert r.loc["NOVOLUSDT", "neden"] == "S_de_islem_yok"
    sec = r[r["sira"] > 0].sort_values("sira").index.tolist()
    assert sec == ["AAAUSDT", "BBBUSDT", "1000SHIBUSDT", "GGGUSDT"]  # hacme göre azalan: 100, 90, 80, 60


def test_ikinci_kontrat_s_de_islem_goreni_kalir():
    d = bilgi([("1000XECUSDT", UZUN, SON, 10.0), ("XECUSDT", UZUN, "2023-06-01", 99.0)])   # XEC S'de işlem görmüyor
    r = y.aday_sec(d).set_index("sembol")
    assert r.loc["1000XECUSDT", "sira"] == 1
    assert r.loc["XECUSDT", "neden"] == "S_de_islem_yok"


def test_ilk_n_siniri():
    d = bilgi([(f"S{i:02d}USDT", UZUN, SON, float(100 - i)) for i in range(10)])
    r = y.aday_sec(d, ilk_n=4)
    assert (r["sira"] > 0).sum() == 4
    assert set(r.loc[r["neden"] == "ilk_n_disi", "sembol"]) == {f"S{i:02d}USDT" for i in range(4, 10)}


def test_taban_ad():
    assert y.taban_ad("1000SHIBUSDT") == "SHIB" and y.taban_ad("1000000MOGUSDT") == "MOG" and y.taban_ad("BTCUSDT") == "BTC"


def test_tarih_siniri_sert():
    ok = pd.DatetimeIndex(["2026-10-31 23:55"], tz="UTC")
    assert y.tarih_siniri_dogrula(ok, "x") == pd.Timestamp("2026-10-31 23:55", tz="UTC")
    with pytest.raises(y.TarihSiniriIhlali):
        y.tarih_siniri_dogrula(pd.DatetimeIndex(["2026-11-01 00:00"], tz="UTC"), "x")
    assert y.tarih_siniri_dogrula(pd.DatetimeIndex([], tz="UTC"), "x") is None


def test_bootstrap_tekrarlanabilir_ve_tohum_duyarli():
    g = np.random.default_rng(1)
    s = g.normal(1.0, 5.0, 30)
    n = g.integers(3, 20, 30)
    a = y.bootstrap_ga(s, n, n_boot=2000, tohum=7)
    b = y.bootstrap_ga(s, n, n_boot=2000, tohum=7)
    c = y.bootstrap_ga(s, n, n_boot=2000, tohum=8)
    assert a == b
    assert a["alt"] != c["alt"] or a["ust"] != c["ust"]
    assert a["alt"] < a["ust"] and a["n_gecerli"] == 2000


def test_bootstrap_hepsi_pozitif_alt_sinir_pozitif():
    a = y.bootstrap_ga([5.0, 4.0, 6.0, 5.5], [10, 10, 10, 10], n_boot=1000)
    assert a["alt"] > 0


def test_r_olculeri():
    o = y.r_olculeri([2.0, -1.0, 1.0, -1.0, 0.0])
    assert o["n"] == 5 and o["sum_r"] == pytest.approx(1.0) and o["ort_r"] == pytest.approx(0.2)
    assert o["pf"] == pytest.approx(3.0 / 2.0) and o["kazanma"] == pytest.approx(0.4)
    assert o["ort_kazanc"] == pytest.approx(1.5) and o["ort_kayip"] == pytest.approx(1.0) and o["kazanc_kayip"] == pytest.approx(1.5)
    assert np.isnan(y.r_olculeri([])["ort_r"])
    assert y.r_olculeri([1.0, 2.0])["pf"] == float("inf")


def test_en_iyi3_cikar():
    kalan, cikan = y.en_iyi_k_cikar({"A": 10.0, "B": 8.0, "C": 6.0, "D": 1.0, "E": -3.0})
    assert kalan == pytest.approx(-2.0) and cikan == ["A", "B", "C"]


def test_evren_olculeri_ve_yorum():
    x2 = {"A": [1.0, 1.0, -0.5], "B": [2.0], "C": [-1.0], "D": [], "E": [1.5, 1.5]}
    x1 = {k: [r + 0.1 for r in v] for k, v in x2.items()}
    o = y.evren_olculeri(x1, x2, ["A", "B", "C", "D", "E"])
    assert o["n_x2"] == 7 and o["sum_r_x2"] == pytest.approx(5.5) and o["n_sembol_islemli_x2"] == 4
    assert o["pozitif_sembol_pct_x2"] == pytest.approx(60.0)             # paydada işlemsiz D de var
    assert o["sembol_medyan_sumr_x2"] == pytest.approx(1.5) and o["sum_r_x1"] > o["sum_r_x2"]
    assert o["en_iyi3_cikinca_sumr_x2"] == pytest.approx(-1.0) and o["en_iyi3_semboller"] == "E,B,A"
    assert y.yorum_etiketi(o) == "ZAYIF / BELİRSİZ"                      # ortalama > 0 ama en iyi 3 çıkınca ΣR <= 0
    assert y.yorum_etiketi({**o, "ort_r_x2": -0.1}) == "GENELLEŞMİYOR"
    iyi = {**o, "boot_ga_alt_x2": 0.1, "en_iyi3_cikinca_sumr_x2": 1.0, "pozitif_sembol_pct_x2": 50.0}
    assert y.yorum_etiketi(iyi) == "GENELLEŞİYOR"
    assert y.yorum_etiketi({**iyi, "pozitif_sembol_pct_x2": 49.9}) == "ZAYIF / BELİRSİZ"
    assert y.yorum_etiketi({**iyi, "boot_ga_alt_x2": 0.0}) == "ZAYIF / BELİRSİZ"
    assert y.yorum_etiketi({**o, "ort_r_x2": float("nan")}) == "GENELLEŞMİYOR"


def test_maliyet_en_pahali_kripto():
    t = pd.DataFrame({"sembol": ["BTCUSDT", "XLMUSDT", "ABCUSDT", "DK_X"], "sinif": ["kripto", "kripto", "kripto", "hisse"],
                      "efektif_komisyon_oran": [0.0005, 0.0005, 0.0005, 0.01], "spread_kayma_oran": [0.0002, 0.0005, 0.0005, 0.01],
                      "stop_kayma_oran": [0.0005, 0.0012, 0.0012, 0.01], "kaynak": ["a", "b", "c", "d"]})
    assert y.en_pahali_kripto_satiri(t)["sembol"] == "ABCUSDT"           # eşitlikte alfabetik ilk; hisse sayılmaz
    u = y.maliyet_tablosu_uret(t, ["NEWUSDT"])
    yeni = u[u["sembol"] == "NEWUSDT"].iloc[0]
    assert yeni["stop_kayma_oran"] == 0.0012 and len(u) == 5
    with pytest.raises(ValueError):
        y.maliyet_tablosu_uret(t, ["BTCUSDT"])


def test_kural_turet():
    assert y.kural_turet(30.0) == (0.001, 0.01)
    assert y.kural_turet(0.5) == (1e-05, 1.0)
    assert y.kural_turet(60000.0) == (1.0, 1e-05)
    with pytest.raises(ValueError):
        y.kural_turet(0.0)


def test_son_islem_kes_duz_mumlari_atar():
    idx = pd.date_range("2024-01-01", periods=6, freq="5min", tz="UTC")
    df = pd.DataFrame({"kapanis": [1, 2, 3, 3, 3, 3.0]}, index=idx)
    out = y.son_islem_kes(df, idx[2])
    assert len(out) == 3 and out.index.max() == idx[2]
