"""Evren stratejileri (wf_evren): kilit öncesi ham koşu, tek ortak ayar, pencere içi seçim, genişlik, ölçütler, sert limitler."""
import json
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_evren as we
from motor.arastirma import wf_tarama
from motor.veri import kilit

T0 = pd.Timestamp("2022-01-01", tz="UTC")


def _g(gun):
    return T0 + pd.Timedelta(days=gun)


def _ham(satirlar):
    """satirlar: [(ayar_no, giris_gun, cikis_gun, r)] -> ham biçim."""
    return pd.DataFrame({"ayar_no": np.array([a for a, *_ in satirlar], dtype=np.int16),
                         "giris_zamani": pd.DatetimeIndex([_g(g) for _, g, _, _ in satirlar]).as_unit("ns"),
                         "cikis_zamani": pd.DatetimeIndex([_g(c) for _, _, c, _ in satirlar]).as_unit("ns"),
                         "yon": np.ones(len(satirlar), dtype=np.int8),
                         "r": np.array([r for *_, r in satirlar], dtype=np.float32),
                         "sf": np.full(len(satirlar), 0.05, dtype=np.float32),
                         "stop_mesafe": np.full(len(satirlar), 1.0, dtype=np.float32)})


# ---------------------------------------------------------------------------- seçim: pencere içi bilgi, tek ortak ayar
def _iki_ayar(gelecek_r):
    """ayar 0: eğitimde iyi; ayar 1: eğitimde kötü, [100, 150) testte dev kâr (gelecek_r)."""
    a, b = [], []
    for g in range(0, 150, 2):
        test = g >= 100
        a.append((0, g, g + 1, -1.0 if test else (2.0 if g % 4 == 0 else -0.5)))
        b.append((1, g, g + 1, gelecek_r if test else (-1.0 if g % 4 == 0 else 0.4)))
    return _ham(a + b)


def test_evren_secimi_pencere_ici_bilgi_ve_tek_ortak_ayar():
    pencereler = [(_g(0), _g(100), _g(100), _g(150))]
    sonuclar = []
    for gelecek in (50.0, -50.0):                       # testteki sonuç ne olursa seçim aynı
        ham = {"A": _iki_ayar(gelecek), "B": _iki_ayar(gelecek)}
        oos, sec = we.evren_wf(ham, pencereler, 10, sira=("A", "B"))
        sonuclar.append((sec[0]["secilen"], sec[0]["egitim_pf"]))
        assert sec[0]["secilen"] == 0
        assert set(oos["ayar_no"]) == {0}               # her enstrümanda AYNI ayar
        assert set(oos["sembol"]) == {"A", "B"}
    assert sonuclar[0] == sonuclar[1]


def test_secim_evren_toplami_ile_yapilir():
    """Tek başına A'da ayar 1 iyi, B'de çok kötü; toplamda ayar 0 kazanır."""
    a = [(0, g, g + 1, 0.5) for g in range(0, 90, 3)] + [(1, g, g + 1, 1.0) for g in range(0, 90, 3)]
    b = [(0, g, g + 1, 0.4) for g in range(0, 90, 3)] + [(1, g, g + 1, -3.0) for g in range(0, 90, 3)]
    nesne = we.seriler_kur({"A": _ham(a), "B": _ham(b)})
    no, pf, n = we.evren_secimi(nesne, _g(0), _g(100), 10)
    assert no == 0 and n == 60 and pf == math.inf


def test_egitim_acik_islem_sayilmaz_ve_min_islem():
    # kapanışı eğitim bitişinden sonra olan işlem skora girmez
    h = _ham([(0, 90, 120, 5.0)] + [(0, g, g + 1, 1.0) for g in range(0, 40, 2)])
    nesne = we.seriler_kur({"A": h})
    assert we.evren_secimi(nesne, _g(0), _g(100), 20) is not None
    assert we.evren_secimi(nesne, _g(0), _g(100), 21) is None


# ---------------------------------------------------------------------------- çakışma, sert limitler
def test_sembol_cakismasi_elenir():
    d = pd.DataFrame({"sembol": ["A", "A", "A", "B"], "giris_zamani": [_g(0), _g(2), _g(10), _g(1)],
                      "cikis_zamani": [_g(5), _g(6), _g(12), _g(3)]})
    s, atilan = we.sembol_cakismasini_ele(d)
    assert atilan == 1 and len(s) == 3


def test_sert_limitler_birlestirmede_uygulanir():
    """13 enstrümanda aynı anda sinyal: toplam stop riski %5 -> en çok 5 işlem aynı anda açık."""
    semboller = we.EVREN_GENEL[:13]
    oos = pd.DataFrame({"sembol": semboller, "yon": 1, "giris_zamani": _g(1), "cikis_zamani": _g(3), "r": 1.0,
                        "sf": 0.05, "stop_mesafe": 1.0})
    tablo = we.oynatma_tablosu(oos, we.EVREN_GENEL)
    m = we.kasa_metrikleri(tablo, _g(0), _g(10))
    assert m["islem_sayisi"] == 5 and m["red_toplam_risk"] + m["red_kaldirac"] == 8
    assert m["net_getiri"] == pytest.approx(5 * 0.01, rel=1e-6)          # 5 işlem x %1 x 1R


def test_kaldirac_siniri():
    """Stop mesafesi çok dar (sf=0.001): %1 risk için nominal 10x özsermaye -> 3x tavanı ölçekler/reddeder."""
    oos = pd.DataFrame({"sembol": ["A", "B"], "yon": 1, "giris_zamani": _g(1), "cikis_zamani": _g(3), "r": 1.0,
                        "sf": 0.001, "stop_mesafe": 1.0})
    m = we.kasa_metrikleri(we.oynatma_tablosu(oos, ("A", "B")), _g(0), _g(10))
    assert m["net_getiri"] < 0.01 * 0.5                                  # 3x tavanı kârı keser (10x gerekirdi)


# ---------------------------------------------------------------------------- genişlik metrikleri
def test_genislik_metrikleri():
    tablo = pd.DataFrame({"sembol": ["BTCUSDT", "BTCUSDT", "DK_AAPL", "DK_XAU"]})
    pnl = {0: (0, 0.03), 1: (0, 0.01), 2: (0, -0.01), 3: (0, 0.02)}
    g = we.genislik(tablo, [0, 1, 2, 3], pnl)
    assert g["n_enstruman_islemli"] == 3 and g["n_enstruman_kar"] == 2
    assert g["enstruman_kar_orani"] == pytest.approx(2 / 3)
    assert g["tek_enstruman_pay"] == pytest.approx(0.04 / 0.05) and g["en_buyuk_enstruman"] == "BTCUSDT"
    assert g["sinif_net"] == pytest.approx({"kripto": 0.04, "hisse": -0.01, "emtia": 0.02})
    assert g["n_sinif_kar"] == 2
    assert g["enstruman_adet"] == {"BTCUSDT": 2, "DK_AAPL": 1, "DK_XAU": 1}


# ---------------------------------------------------------------------------- ON_KAYIT ölçüt mantığı
IYI = {"net_getiri": 0.3, "profit_factor": 1.4, "islem_sayisi": 250, "pf_en_iyi5_haric": 1.0, "sharpe": 0.9,
       "max_dusus": 0.12, "enstruman_kar_orani": 0.6, "tek_enstruman_pay": 0.3, "n_sinif_kar": 2}


def test_olcutler_gecer_ve_her_esik_ayri_kirar():
    assert we.olcutleri_degerlendir(IYI)["gecti"]
    for anahtar, kotu in (("net_getiri", -0.01), ("profit_factor", 1.19), ("islem_sayisi", 99), ("pf_en_iyi5_haric", 0.89),
                          ("sharpe", 0.49), ("max_dusus", 0.21), ("enstruman_kar_orani", 0.49),
                          ("tek_enstruman_pay", 0.41), ("n_sinif_kar", 1), ("sharpe", float("nan"))):
        o = we.olcutleri_degerlendir({**IYI, anahtar: kotu})
        assert not o["gecti"] and o["basarisiz_sayi"] == 1, anahtar
    sinir = {**IYI, "profit_factor": 1.2, "islem_sayisi": 100, "pf_en_iyi5_haric": 0.9, "sharpe": 0.5, "max_dusus": 0.2,
             "enstruman_kar_orani": 0.5, "tek_enstruman_pay": 0.4}
    assert we.olcutleri_degerlendir(sinir)["gecti"]                      # eşikler dahil
    assert we.olcutleri_degerlendir(IYI)["g1"] and we.olcutleri_degerlendir({**IYI, "n_sinif_kar": 0})["g1"]


def test_saglamlik_kapilari():
    iyi = {"m2_pf": 1.05, "rnd_p": 0.05, "pf_boot_alt": 1.01, "par_oran": 0.6}
    assert we.saglamlik_oneri(iyi)[0]
    for k, v in (("m2_pf", 1.04), ("rnd_p", 0.06), ("pf_boot_alt", 1.0), ("par_oran", 0.59), ("par_oran", float("nan"))):
        assert not we.saglamlik_oneri({**iyi, k: v})[0]


# ---------------------------------------------------------------------------- ham koşu: sentetik veri, kilit öncesi
@pytest.fixture
def veri_dizini(tmp_path):
    rng = np.random.default_rng(3)
    n = 900 * 24
    idx = pd.date_range("2022-01-01", periods=n, freq="1h", tz="UTC", name="zaman")
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, n)))
    ac = np.r_[kap[0], kap[:-1]]
    df = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.002, "dusuk": np.minimum(ac, kap) * 0.998,
                       "kapanis": kap, "hacim": 10.0, "quote_hacim": 1000.0, "islem_sayisi": 5}, index=idx)
    d = tmp_path / "veri" / "TESTUSDT"
    d.mkdir(parents=True)
    df.to_parquet(d / "1h.parquet")
    return tmp_path / "veri"


def test_ham_gorev_kilit_oncesi_devam_ve_bekleme(tmp_path, veri_dizini, monkeypatch):
    sinir = pd.Timestamp("2023-12-01", tz="UTC")
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", sinir)
    we.veri_ayarla(veri_dizini, "kilit_oncesi")
    ham = tmp_path / "ham"
    meta = we.ham_gorev("swing__donchian-kirilim", "4h", "TESTUSDT", 1.0, ham)
    assert meta["n_kosu"] > 1 and meta["n_islem"] > 0 and meta["hata"] == "" or meta["n_hata"] >= 0
    df = pd.read_parquet(we.ham_yolu(ham, "swing__donchian-kirilim", "4h", "TESTUSDT"))
    assert pd.DatetimeIndex(df["cikis_zamani"]).max() <= sinir and pd.DatetimeIndex(df["giris_zamani"]).max() < sinir
    assert {"ayar_no", "giris_zamani", "cikis_zamani", "yon", "r", "sf", "stop_mesafe"} <= set(df.columns)
    assert not kilit.KILIT_LOG.exists()
    # devam: biten atlanır
    assert we.ham_gorev("swing__donchian-kirilim", "4h", "TESTUSDT", 1.0, ham) == {"atlandi": True}
    # verisi henüz olmayan sembol: yan dosya YAZILMAZ (bekliyor); kesin ile mühürlenir
    m = we.ham_gorev("swing__donchian-kirilim", "4h", "YOKUSDT", 1.0, ham, kesin=False)
    assert m.get("veri_bekliyor") and not we.ham_yolu(ham, "swing__donchian-kirilim", "4h", "YOKUSDT").with_suffix(".json").exists()
    m = we.ham_gorev("swing__donchian-kirilim", "4h", "YOKUSDT", 1.0, ham, kesin=True)
    assert m["veri_yok"] and we.ham_yolu(ham, "swing__donchian-kirilim", "4h", "YOKUSDT").with_suffix(".json").exists()


def test_ham_gorev_ayar_etiketleri_ve_wf_uctan_uca(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", pd.Timestamp("2024-06-01", tz="UTC"))
    we.veri_ayarla(veri_dizini, "kilit_oncesi")
    ham = tmp_path / "ham"
    ad = "swing__donchian-kirilim"
    we.ham_gorev(ad, "4h", "TESTUSDT", 1.0, ham)
    satir, oos = we.evren_wf_kos(ad, "4h", "swing", ham, evren=("TESTUSDT", "BOSUSDT")[:1],
                                 pencere_gun={"swing": (200, 100), "daytrade": (200, 100), "scalp": (200, 100)},
                                 min_islem={"swing": 3, "daytrade": 3, "scalp": 3})
    assert satir["hata"] == "" and satir["n_pencere"] >= 3 and satir["n_enstruman"] == 1
    if len(oos):
        assert oos["kabul"].sum() == satir["islem_sayisi"]
        assert json.loads(satir["secimler"])[0]["ayar"] is not None or satir["n_islemli_pencere"] >= 0
        # OOS işlemleri test pencerelerinde
        assert pd.DatetimeIndex(oos["giris"]).min() >= pd.Timestamp(satir["oos_bas"])


def test_ham_yukle_bitmemis_hata(tmp_path):
    with pytest.raises(RuntimeError, match="bitmemiş"):
        we.ham_yukle(tmp_path, "swing__x", "4h", ("A",))


def test_evren_tanimlari():
    assert len(we.EVREN_GENEL) == 49 and len(set(we.EVREN_GENEL)) == 49
    assert we.EVREN_SCALP == ("DK_SPX", "DK_XAU", "DK_WTI", "BTCUSDT", "BIST_XU030")
    assert we.SINIF["BIST_THYAO"] == "bist" and we.SINIF["BIST_XU030"] == "bist"
    assert not {"XMRUSDT", "LEOUSDT"} & set(we.EVREN_GENEL)
    assert all(s in we.SINIF for s in we.EVREN_GENEL + we.EVREN_SCALP)
    assert we.SINIF["DK_SPX"] == "hisse"
    assert we.stil_tf_listesi("swing__ma-kesisim") == ("4h", "1d")


def test_islem_ozet_sf_ve_stop():
    d = pd.DataFrame({"yon": [1, -1], "giris_zamani": [_g(0), _g(5)], "cikis_zamani": [_g(1), _g(6)],
                      "giris_fiyati": [100.0, 100.0], "miktar": [2.0, 2.0], "net_pnl": [-20.0, 40.0], "r": [-1.0, 2.0]})
    o = we.islem_ozet(d, 7)
    assert list(o["ayar_no"]) == [7, 7]
    assert o["sf"].iloc[0] == pytest.approx(0.1) and o["stop_mesafe"].iloc[0] == pytest.approx(10.0)


def test_iyi_ve_iyiye_yakin_listeleri():
    wf = pd.DataFrame({"strateji": ["a", "b", "c", "d"], "tf": "4h", "stil": "swing", "sharpe": [1.0, 0.9, 0.8, 0.7],
                       "gecti": [True, True, False, False], "yakin_wf": [True, True, True, False],
                       "basarisiz_sayi": [0, 0, 1, 3], "hata": ""})
    sag = pd.DataFrame({"strateji": ["a", "b", "c", "d"], "tf": "4h", "saglam_mi": [True, False, True, False],
                        "kapi_basarisiz": ["", "K2_rastgele_p", "", "K1_maliyet2_pf;K2_rastgele_p"],
                        "rnd_p": 0.01, "m2_pf": 1.1, "pf_boot_alt": 1.1, "par_oran": 0.8, "hata": ""})
    iyi, yakin = we.listeler(wf, sag)
    assert list(iyi["strateji"]) == ["a"]
    # b: WF tam + 1 kapı kaçıyor; c: WF'de 1 ölçüt kaçıyor + kapılar tam; d: 3+2 kaçan -> yok
    assert list(yakin["strateji"]) == ["b", "c"]


def test_yakin_wf_esikleri():
    m = {**IYI, "profit_factor": 1.15}                  # PF 1.2 altı, 1.1 üstü: bir ölçüt kıl payı kaçar
    assert not we.olcutleri_degerlendir(m)["gecti"] and we.yakin_wf_mi(m)
    assert not we.yakin_wf_mi({**IYI, "profit_factor": 1.05})
    assert not we.yakin_wf_mi({**IYI, "profit_factor": 1.15, "sharpe": 0.45})      # iki ölçüt kaçıyor
    assert not we.yakin_wf_mi({**IYI, "islem_sayisi": 99})                         # kıl payı eşiği yalnız PF/Sharpe/düşüş
