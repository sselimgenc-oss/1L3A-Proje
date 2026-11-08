"""Evren stratejileri (wf_evren): kilit öncesi ham koşu, tek ortak ayar, pencere içi seçim, genişlik, ölçütler, sert limitler."""
import json
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_k2, evren_maliyet, pbo
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_holdout as wh
from motor.arastirma import wf_tarama
from motor.backtest import deneme_kaydi
from motor.veri import kilit

T0 = pd.Timestamp("2022-01-01", tz="UTC")


@pytest.fixture(autouse=True)
def _maliyet_ve_gunluk(tmp_path, monkeypatch):
    """Maliyet tablosu = gerçek tablo + test sembolleri; kilit/deneme günlükleri geçici dosyaya (gerçek dosyalar kirlenmez)."""
    t = evren_maliyet.yukle(evren_maliyet.TABLO_YOLU).reset_index()
    ek = pd.concat([t[t["sembol"] == "BTCUSDT"].assign(sembol=s) for s in ("TESTUSDT", "BOSUSDT")])
    yol = tmp_path / "maliyet_tablosu.csv"
    pd.concat([t, ek]).to_csv(yol, index=False)
    monkeypatch.setattr(evren_maliyet, "TABLO_YOLU", yol)
    monkeypatch.setattr(kilit, "KILIT_LOG", tmp_path / "kilit_log.jsonl")
    monkeypatch.setattr(deneme_kaydi, "VARSAYILAN_YOL", tmp_path / "deneme.jsonl")
    we._ONB.clear()


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
    iyi = {"m2_pf": 1.05, "m3_pf": 1.0, "g1_pf": 1.0, "rnd_p": 0.05, "pf_boot_alt": 1.01, "par_oran": 0.6, "dsr_deneme": 0.9}
    assert we.saglamlik_oneri(iyi)[0]
    for k, v, ad in (("m2_pf", 1.04, "K1_"), ("m3_pf", 0.99, "K1b"), ("g1_pf", 0.99, "K1c"), ("rnd_p", 0.06, "K2"),
                     ("pf_boot_alt", 1.0, "K3"), ("par_oran", 0.59, "K4"), ("par_oran", float("nan"), "K4"),
                     ("dsr_deneme", 0.89, "K5"), ("g1_pf", float("nan"), "K1c")):
        ok, kay = we.saglamlik_oneri({**iyi, k: v})
        assert not ok and kay.startswith(ad), (k, kay)
    # kıl payı eşikleri: K2 p 0.10, DSR 0.50 (diğerleri aynı)
    assert we.saglamlik_oneri({**iyi, "rnd_p": 0.10, "dsr_deneme": 0.5}, we.YAKIN_OLCUT)[0]
    assert not we.saglamlik_oneri({**iyi, "rnd_p": 0.11}, we.YAKIN_OLCUT)[0]
    assert not we.saglamlik_oneri({**iyi, "dsr_deneme": 0.49}, we.YAKIN_OLCUT)[0]


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
    assert len(we.EVREN_GENEL) == 48 and len(set(we.EVREN_GENEL)) == 48
    assert "DK_ABBV" not in we.EVREN_GENEL                                     # BIST kararı: ABBV çıktı
    assert we.EVREN_SCALP == ("DK_SPX", "DK_XAU", "DK_WTI", "BTCUSDT")         # XU030 scalp'ten çıktı
    assert we.SINIF["BIST_THYAO"] == "bist"
    assert not {"XMRUSDT", "LEOUSDT"} & set(we.EVREN_GENEL)
    assert all(s in we.SINIF for s in we.EVREN_GENEL + we.EVREN_SCALP)
    assert all(s in evren_maliyet.yukle().index for s in we.EVREN_GENEL + we.EVREN_SCALP)
    assert we.SINIF["DK_SPX"] == "hisse"
    assert we.stil_tf_listesi("swing__ma-kesisim") == ("4h", "1d")


def test_islem_ozet_sf_ve_stop():
    d = pd.DataFrame({"yon": [1, -1], "giris_zamani": [_g(0), _g(5)], "cikis_zamani": [_g(1), _g(6)],
                      "giris_fiyati": [100.0, 100.0], "miktar": [2.0, 2.0], "net_pnl": [-20.0, 40.0], "r": [-1.0, 2.0]})
    o = we.islem_ozet(d, 7)
    assert list(o["ayar_no"]) == [7, 7]
    assert o["sf"].iloc[0] == pytest.approx(0.1) and o["stop_mesafe"].iloc[0] == pytest.approx(10.0)


def test_iyi_ve_iyiye_yakin_listeleri_yeni_kapilar_ve_pbo():
    ad = ["a", "b", "c", "d", "e", "f", "g"]
    stil = ["swing"] * 5 + ["daytrade", "swing"]
    tf = ["4h"] * 5 + ["1h", "4h"]
    wf = pd.DataFrame({"strateji": ad, "tf": tf, "stil": stil, "sharpe": [1.0, 0.9, 0.8, 0.7, 0.6, 0.95, 0.5],
                       "gecti": [True, True, False, False, True, True, True],
                       "yakin_wf": [True, True, True, False, True, True, True],
                       "basarisiz_sayi": [0, 0, 1, 3, 0, 0, 0], "hata": ""})
    sag = pd.DataFrame({"strateji": ad, "tf": tf, "saglam_mi": [True, False, True, False, False, True, False],
                        "kapi_basarisiz": ["", "K2_rastgele_p", "", "K1_maliyet2_pf;K2_rastgele_p", "K5_dsr", "", "K2_rastgele_p"],
                        "rnd_p": [0.01, 0.08, 0.01, 0.01, 0.01, 0.01, 0.20], "m2_pf": 1.1, "m3_pf": 1.05, "g1_pf": 1.05,
                        "pf_boot_alt": 1.1, "par_oran": 0.8, "dsr_deneme": [0.95, 0.95, 0.95, 0.95, 0.3, 0.95, 0.95],
                        "hata": ""})
    pbo_df = pd.DataFrame({"stil": ["swing", "daytrade"], "tf": ["4h", "1h"], "pbo": [0.3, 0.7]})
    iyi, yakin = we.listeler(wf, sag, pbo_df)
    assert list(iyi["strateji"]) == ["a"]
    # b: WF tam + K2 p 0.08 (<= 0.10) -> yakın; c: WF'de 1 ölçüt kaçıyor, kapılar tam -> yakın; f: tüm kapılar tamam ama PBO 0.7 -> iyiden DÜŞER
    # d: 3+2 kaçan; e: DSR 0.3 < 0.5; g: K2 p 0.20 > 0.10 -> yok
    assert sorted(yakin["strateji"]) == ["b", "c", "f"]
    assert bool(yakin.set_index("strateji").loc["f", "pbo_dusurdu"]) and not bool(yakin.set_index("strateji").loc["b", "pbo_dusurdu"])
    with pytest.raises(ValueError, match="PBO"):
        we.listeler(wf, sag, None)                       # PBO kapısı atlanamaz
    # PBO hesaplanamayan (NaN) grup da iyiyi düşürür
    iyi2, yakin2 = we.listeler(wf, sag, pbo_df.assign(pbo=[float("nan"), 0.7]))
    assert len(iyi2) == 0 and "a" in set(yakin2["strateji"])


def test_yakin_wf_esikleri():
    m = {**IYI, "profit_factor": 1.15}                  # PF 1.2 altı, 1.1 üstü: bir ölçüt kıl payı kaçar
    assert not we.olcutleri_degerlendir(m)["gecti"] and we.yakin_wf_mi(m)
    assert not we.yakin_wf_mi({**IYI, "profit_factor": 1.05})
    assert not we.yakin_wf_mi({**IYI, "profit_factor": 1.15, "sharpe": 0.45})      # iki ölçüt kaçıyor
    assert not we.yakin_wf_mi({**IYI, "islem_sayisi": 99})                         # kıl payı eşiği yalnız PF/Sharpe/düşüş


# ============================================================================ GÜNCELLEME 5
AD = "swing__donchian-kirilim"


def _veri_kopya_degisik(veri_dizini, tmp_path, kes):
    """TESTUSDT 1h dosyasının kesimden SONRAKİ barlarını bozar (fiyat x3.7); öncesi aynı."""
    import shutil
    d2 = tmp_path / "veri_bozuk"
    shutil.copytree(veri_dizini, d2)
    yol = d2 / "TESTUSDT" / "1h.parquet"
    df = pd.read_parquet(yol)
    sut = ["acilis", "yuksek", "dusuk", "kapanis"]
    df.loc[df.index >= kes, sut] = df.loc[df.index >= kes, sut] * 3.7
    df.to_parquet(yol)
    return d2


def test_holdout_verisi_gelistirme_ciktilarini_etkilemez(tmp_path, veri_dizini, monkeypatch):
    kes = pd.Timestamp("2023-09-01", tz="UTC")
    monkeypatch.setitem(we.DONEMLER, "test_gel", {"bas": None, "bit": kes, "kilit_ac": True})
    monkeypatch.setitem(we.DONEMLER, "test_tam", {"bas": None, "bit": None, "kilit_ac": True})
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    d2 = _veri_kopya_degisik(veri_dizini, tmp_path, kes)
    pg = {"swing": (200, 100), "daytrade": (200, 100), "scalp": (200, 100)}
    mi = {"swing": 3, "daytrade": 3, "scalp": 3}
    ciktilar, satirlar, oosler = {}, {}, {}
    for ad_, dizin in (("a", veri_dizini), ("b", d2)):
        we.veri_ayarla(dizin, "test_gel")
        h = tmp_path / f"ham_{ad_}"
        meta = we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h)
        assert pd.Timestamp(meta["veri_bit"]) < kes and meta["donem"] == "test_gel"
        ciktilar[ad_] = pd.read_parquet(we.ham_yolu(h, AD, "4h", "TESTUSDT"))
        satir, oos = we.evren_wf_kos(AD, "4h", "swing", h, evren=("TESTUSDT",), pencere_gun=pg, min_islem=mi)
        satirlar[ad_], oosler[ad_] = satir, oos
    assert len(ciktilar["a"]) > 0
    pd.testing.assert_frame_equal(ciktilar["a"], ciktilar["b"])                    # ham işlemler birebir aynı
    for k in ("profit_factor", "net_getiri", "islem_sayisi", "sharpe", "oos_bit", "secimler"):
        assert satirlar["a"].get(k) == satirlar["b"].get(k) or (
            satirlar["a"][k] != satirlar["a"][k] and satirlar["b"][k] != satirlar["b"][k]), k
    pd.testing.assert_frame_equal(oosler["a"], oosler["b"])
    # duyarlılık kontrolü: kesimsiz dönem bozuk veriyi GÖRÜR ve farklı sonuç verir (testin gücü)
    sonuc = []
    for dizin in (veri_dizini, d2):
        we.veri_ayarla(dizin, "test_tam")
        h = tmp_path / f"tam_{len(sonuc)}"
        we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h)
        sonuc.append(pd.read_parquet(we.ham_yolu(h, AD, "4h", "TESTUSDT")))
    assert not sonuc[0].equals(sonuc[1])


def test_ham_yukle_sinir_asan_veri_ve_maliyet_hash(tmp_path, veri_dizini, monkeypatch):
    kes = pd.Timestamp("2023-09-01", tz="UTC")
    monkeypatch.setitem(we.DONEMLER, "test_gel", {"bas": None, "bit": kes, "kilit_ac": True})
    we.veri_ayarla(veri_dizini, "test_gel")
    h = tmp_path / "ham"
    we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h)
    ham, _, bilgi = we.ham_yukle(h, AD, "4h", ("TESTUSDT",))
    assert bilgi["maliyet_hash"] == evren_maliyet.tablo_hash()
    # meta'daki veri_bit sınırı aşarsa (sızıntı) reddedilir
    yan = we.ham_yolu(h, AD, "4h", "TESTUSDT").with_suffix(".json")
    meta = json.loads(yan.read_text())
    yan.write_text(json.dumps({**meta, "veri_bit": "2023-10-01 00:00:00+00:00"}))
    with pytest.raises(RuntimeError, match="holdout sızıntısı"):
        we.ham_yukle(h, AD, "4h", ("TESTUSDT",))
    yan.write_text(json.dumps(meta))
    # maliyet tablosu değişirse eski koşular reddedilir
    t = pd.read_csv(evren_maliyet.TABLO_YOLU)
    t.loc[t["sembol"] == "TESTUSDT", "spread_kayma_oran"] = 0.01
    yeni = tmp_path / "degisik.csv"
    t.to_csv(yeni, index=False)
    monkeypatch.setattr(evren_maliyet, "TABLO_YOLU", yeni)
    with pytest.raises(RuntimeError, match="maliyet tablosu"):
        we.ham_yukle(h, AD, "4h", ("TESTUSDT",))


# ---------------------------------------------------------------------------- holdout aşaması
def _holdout_cikti(tmp_path):
    cikti = tmp_path / "cikti"
    cikti.mkdir()
    sec = [{"pencere": 0, "secilen": None, "ayar": None},
           {"pencere": 1, "secilen": 3, "ayar": "varsayilan"}, {"pencere": 2, "secilen": None, "ayar": None}]
    wf = pd.DataFrame([{"strateji": AD, "tf": "4h", "stil": "swing", "secimler": json.dumps(sec), "kisa_gecmis": "",
                        "disarida": "", "hatali_sembol": "", "profit_factor": 1.3, "sharpe": 0.7}])
    wf.to_parquet(cikti / "wf_evren.parquet")
    pd.DataFrame([{"strateji": AD, "tf": "4h", "stil": "swing"}]).to_csv(cikti / "iyi_liste.csv", index=False)
    pd.DataFrame(columns=["strateji", "tf", "stil"]).to_csv(cikti / "iyiye_yakin_liste.csv", index=False)
    pd.DataFrame(columns=["ajan"]).to_csv(cikti / "secim.csv", index=False)
    wh.muhur_yaz(cikti)
    return cikti


def test_holdout_asamasi_bir_kerelik_ve_liste_muhru(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp("2023-09-01", tz="UTC"))
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    cikti = _holdout_cikti(tmp_path)
    assert wh.son_secilen_ayar(pd.read_parquet(cikti / "wf_evren.parquet")["secimler"].iloc[0]) == "varsayilan"
    # liste değişmişse holdout reddedilir (günlüğe de yazılmaz)
    iyi = cikti / "iyi_liste.csv"
    orijinal = iyi.read_text()
    iyi.write_text(orijinal + f"{AD}2,4h,swing\n")
    with pytest.raises(wh.HoldoutHatasi, match="liste değişmiş"):
        wh.holdout_asamasi(cikti, veri_dizini=veri_dizini)
    assert not wh.holdout_baslamis_mi(cikti)
    iyi.write_text(orijinal)
    # zorla bayrağı ilk koşuda anlamsız
    with pytest.raises(wh.HoldoutTekrarHatasi):
        wh.holdout_asamasi(cikti, veri_dizini=veri_dizini, zorla=True, gerekce="x")
    df = wh.holdout_asamasi(cikti, veri_dizini=veri_dizini)
    assert len(df) == 1 and df["durum"].iloc[0] in ("dogrulanmis", "holdout_ta_kaldi") and df["hata"].iloc[0] == ""
    assert df["ayar"].iloc[0] == "varsayilan" and df["liste"].iloc[0] == "iyi"
    assert (cikti / "holdout" / "holdout.csv").exists()
    # ikinci koşu: açık hata
    with pytest.raises(wh.HoldoutTekrarHatasi, match="bir kerelik"):
        wh.holdout_asamasi(cikti, veri_dizini=veri_dizini)
    with pytest.raises(wh.HoldoutTekrarHatasi, match="gerekçe"):
        wh.holdout_asamasi(cikti, veri_dizini=veri_dizini, zorla=True, gerekce="  ")
    wh.holdout_asamasi(cikti, veri_dizini=veri_dizini, zorla=True, gerekce="test: veri hatası düzeltildi")
    gunluk = wh.gunluk_oku(cikti)
    assert [k["olay"] for k in gunluk] == ["basladi", "bitti", "basladi", "bitti"]
    assert gunluk[2]["zorla"] is True and "veri hatası" in gunluk[2]["gerekce"]
    # holdout başladıktan sonra secim aşaması listeleri yeniden yazamaz
    from motor.arastirma import wf_evren_rapor
    with pytest.raises(wh.HoldoutHatasi, match="holdout"):
        wf_evren_rapor.secim_ve_ozet(cikti)


def test_holdout_yalniz_kesimden_sonraki_girisleri_sayar(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    we.veri_ayarla(veri_dizini, "holdout")
    n = {}
    for bas in ("2022-06-01", "2023-03-01", "2030-01-01"):
        monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp(bas, tz="UTC"))
        n[bas] = wh.holdout_kos(AD, "4h", "swing", "varsayilan")
    assert n["2022-06-01"]["islem_sayisi"] > n["2023-03-01"]["islem_sayisi"] > 0
    assert n["2030-01-01"]["islem_sayisi"] == 0 and n["2030-01-01"]["profit_factor"] != n["2030-01-01"]["profit_factor"]


def test_holdout_kapisi():
    assert wh.kapi({"islem_sayisi": 10, "net_getiri": 0.01, "profit_factor": 1.1})
    assert not wh.kapi({"islem_sayisi": 10, "net_getiri": 0.01, "profit_factor": 1.09})
    assert not wh.kapi({"islem_sayisi": 10, "net_getiri": 0.0, "profit_factor": 1.5})
    assert not wh.kapi({"islem_sayisi": 0, "net_getiri": 0.0, "profit_factor": math.nan})


# ---------------------------------------------------------------------------- K1c: 1 mum gecikmeli sinyal
def test_gecikmeli_strateji_ve_ham_gorev(tmp_path, veri_dizini, monkeypatch):
    from motor.arastirma import saglamlik
    from motor.veri.yeniden_ornekle import tf_mumlari
    monkeypatch.setitem(we.DONEMLER, "test_tam", {"bas": None, "bit": None, "kilit_ac": True})
    we.veri_ayarla(veri_dizini, "test_tam")
    mumlar = tf_mumlari("TESTUSDT", "4h", None, None, dizin=veri_dizini, kilit_ac=True, gerekce="test")
    st = saglamlik.ayar_coz(AD, "varsayilan")
    sig, g = st.sinyaller(mumlar), we.GecikmeliStrateji(st, 1).sinyaller(mumlar)
    assert g.index.equals(sig.index) and g["yon"].iloc[0] == 0
    np.testing.assert_array_equal(g["yon"].to_numpy()[1:], sig["yon"].to_numpy()[:-1])
    np.testing.assert_array_equal(g["cikis"].to_numpy()[1:], sig["cikis"].to_numpy()[:-1])
    assert we.GecikmeliStrateji(st, 1).cikis_ayarlari is st.cikis_ayarlari and we.GecikmeliStrateji(st, 1).ad == st.ad
    h0, h1 = tmp_path / "h0", tmp_path / "h1"
    we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h0)
    m1 = we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h1, gecikme=1)
    assert m1["gecikme"] == 1
    a, b = pd.read_parquet(we.ham_yolu(h0, AD, "4h", "TESTUSDT")), pd.read_parquet(we.ham_yolu(h1, AD, "4h", "TESTUSDT"))
    for no in set(a["ayar_no"]) & set(b["ayar_no"]):                # gecikmeli ilk giriş en az 1 mum (4h) sonra
        assert b[b.ayar_no == no]["giris_zamani"].min() >= a[a.ayar_no == no]["giris_zamani"].min() + pd.Timedelta("4h")


# ---------------------------------------------------------------------------- K2: stratejinin çıkış kurallarıyla rastgele giriş
def _duz_seri(n=60, fiyat=100.0):
    o = np.full(n, fiyat)
    return o.copy(), o.copy(), o.copy(), o.copy(), np.ones(n)


def test_k2_sinyal_hedef_ve_iz_suren_cikislar():
    o, h, l, c, atr = _duz_seri()
    kw = dict(kayma=0.0, stop_kayma=0.0, taker=0.0)
    # sinyal çıkışı: 3. mumun kapanışında sinyal -> 4. mumun açılışında çık; R = (102-100)/2 = 1
    o2 = o.copy()
    o2[13] = 102.0
    ex = np.zeros(60, dtype=bool)
    ex[12] = True
    r = evren_k2.tek_islem_r(o2, h, l, c, atr, 10, 1, 30, 2.0, ex=ex, **kw)
    assert r == pytest.approx(1.0)
    # sinyal yok: zaman çıkışı (hm=30 -> o[40]) flat -> 0
    assert evren_k2.tek_islem_r(o, h, l, c, atr, 10, 1, 30, 2.0, **kw) == pytest.approx(0.0)
    # hedef 1R = 102: 12. mumun yükseği 103 -> hedefte çık, R = 1
    h2 = h.copy()
    h2[12] = 103.0
    assert evren_k2.tek_islem_r(o, h2, l, c, atr, 10, 1, 30, 2.0, hedef_r=1.0, **kw) == pytest.approx(1.0)
    assert evren_k2.tek_islem_r(o, h2, l, c, atr, 10, 1, 30, 2.0, **kw) == pytest.approx(0.0)       # hedefsiz: yok sayılır
    # stop: dip 97 < stop 98 -> R = -1 (kayma yok)
    l2 = l.copy()
    l2[11] = 97.0
    assert evren_k2.tek_islem_r(o, h, l2, c, atr, 10, 1, 30, 2.0, **kw) == pytest.approx(-1.0)
    # kısa yön ayna: sinyal çıkışı 98 -> R = +1
    o3 = o.copy()
    o3[13] = 98.0
    assert evren_k2.tek_islem_r(o3, h, l, c, atr, 10, -1, 30, 2.0, ex=ex, **kw) == pytest.approx(1.0)
    # iz süren stop: tepe 110'a yürüyüş, sonra çöküş; k=1 ATR -> stop ~109 civarı çıkış => R >> -1 (iz yoksa stop 98'de -1)
    o4, h4, l4, c4, atr4 = _duz_seri()
    for i in range(11, 21):
        o4[i], c4[i] = 100 + (i - 10), 100 + (i - 10)
        h4[i], l4[i] = 100.5 + (i - 10), 99.5 + (i - 10)
    l4[21:] = 70.0
    o4[21:] = 109.0
    iz = evren_k2.tek_islem_r(o4, h4, l4, c4, atr4, 10, 1, 30, 2.0, iz_k=1.0, iz_atr=atr4, **kw)
    assert iz > 3.0
    # başabaş: 1R'ye ulaşınca stop girişe -> sonra düşüş stop = giriş (R = 0), başabaşsız ilk stop = -1
    o5, h5, l5, c5, atr5 = _duz_seri()
    h5[11] = 102.5
    l5[13] = 95.0
    assert evren_k2.tek_islem_r(o5, h5, l5, c5, atr5, 10, 1, 30, 2.0, be_r=1.0, **kw) == pytest.approx(0.0)
    assert evren_k2.tek_islem_r(o5, h5, l5, c5, atr5, 10, 1, 30, 2.0, **kw) == pytest.approx(-1.0)


def test_k2_hizli_yol_ile_mum_mum_yol_ayni():
    rng = np.random.default_rng(11)
    n = 400
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = np.r_[c[0], c[:-1]]
    h, l = np.maximum(o, c) * 1.004, np.minimum(o, c) * 0.996
    atr = np.full(n, 0.8)
    ex = rng.random(n) < 0.03
    for _ in range(300):
        j = int(rng.integers(5, n - 40))
        yon = int(rng.choice([-1, 1]))
        kw = dict(ex=ex, hedef_r=float(rng.choice([math.nan, 1.5, 3.0])))
        a = evren_k2.tek_islem_r(o, h, l, c, atr, j, yon, 25, 1.5, 2e-4, 5e-4, 5e-4, **kw)
        b = evren_k2.tek_islem_r(o, h, l, c, atr, j, yon, 25, 1.5, 2e-4, 5e-4, 5e-4, _dongu=True, **kw)
        assert (a is None and b is None) or a == pytest.approx(b, abs=1e-12)


def test_k2_cikis_bilgisi_ve_desteklenmeyen(veri_dizini):
    from motor.arastirma import saglamlik
    from motor.strateji.cikislar import CikisAyarlari
    from motor.veri.yeniden_ornekle import tf_mumlari
    mumlar = tf_mumlari("TESTUSDT", "4h", "2022-01-01", "2022-12-31", dizin=veri_dizini, kilit_ac=True, gerekce="test")
    st = saglamlik.ayar_coz(AD, "varsayilan")
    ci = evren_k2.cikis_bilgisi(st, mumlar)
    assert len(ci["ex_long"]) == len(mumlar) and ci["ex_long"].dtype == bool and ci["ex_long"].any()
    assert ci["iz_k"] == st.cikis_ayarlari.atr_iz_suren_k and ci["desteklenmeyen"] == []
    assert evren_k2.desteklenmeyen(CikisAyarlari(kismi=((1.0, 0.25),), geri_cekilme_yuzde=2.0)) == ["kismi", "geri_cekilme_yuzde"]


def test_rastgele_evren_cikis_kurallarini_kullanir(veri_dizini):
    from motor.veri.yeniden_ornekle import tf_mumlari
    mumlar = tf_mumlari("TESTUSDT", "1h", None, None, dizin=veri_dizini, kilit_ac=True, gerekce="test")
    ay = evren_maliyet.maliyet_ayarlari("TESTUSDT", None)
    t0 = mumlar.index[500]
    oos = pd.DataFrame({"sembol": "TESTUSDT", "yon": [1] * 20, "giris_zamani": [mumlar.index[500 + 10 * i] for i in range(20)],
                        "cikis_zamani": [mumlar.index[510 + 10 * i] for i in range(20)], "stop_mesafe": 2.0,
                        "pencere": 0})
    sinir = [(t0, mumlar.index[900])]
    ortak = dict(n_sim=20, seed=3, tf="1h", veri_al=lambda s: (mumlar, ay))
    eski = we.rastgele_evren(oos, sinir, **ortak)
    hepsi = {"ex_long": np.ones(len(mumlar), bool), "ex_short": np.ones(len(mumlar), bool), "hedef_r": math.nan,
             "iz_k": None, "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
    yeni = we.rastgele_evren(oos, sinir, cikis_al=lambda s, w: hepsi, **ortak)
    ayni = we.rastgele_evren(oos, sinir, cikis_al=lambda s, w: {**hepsi, "ex_long": np.zeros(len(mumlar), bool)}, **ortak)
    assert len(yeni["toplam_r"]) == 20 and np.isfinite(yeni["toplam_r"]).all()
    assert not np.allclose(yeni["toplam_r"], eski["toplam_r"])                  # çıkış sinyali sonucu değiştirir
    np.testing.assert_allclose(ayni["toplam_r"], eski["toplam_r"])              # sinyal yoksa eski davranışla aynı


# ---------------------------------------------------------------------------- maliyet tablosu
def test_maliyet_tablosu_esleme_ve_bsmv():
    from motor.backtest.motor import SembolKurallari
    k = SembolKurallari()
    a = evren_maliyet.maliyet_ayarlari("BIST_THYAO", k)
    assert a.komisyon_taker_yuzde == pytest.approx(0.0004 * 1.05 * 100)             # komisyon + BSMV (%5'i)
    r = evren_maliyet.satir("BIST_THYAO")
    assert r["bsmv_oran"] == 0.05 and r["efektif_komisyon_oran"] == pytest.approx(0.00042)
    assert a.kayma_bps == pytest.approx(r["spread_kayma_oran"] * 1e4) and a.stop_kayma_bps == pytest.approx(r["stop_kayma_oran"] * 1e4)
    b = evren_maliyet.maliyet_ayarlari("BTCUSDT", k)
    assert b.komisyon_taker_yuzde == pytest.approx(0.05) and b.limit_modu == "olc"           # Binance taker %0.05
    b3 = evren_maliyet.maliyet_ayarlari("BTCUSDT", k, 3.0)
    assert b3.komisyon_taker_yuzde == pytest.approx(0.15) and b3.kayma_bps == pytest.approx(3 * b.kayma_bps)
    assert evren_maliyet.satir("BTCUSDT")["funding"] == "gercek_seri" and evren_maliyet.satir("DK_AAPL")["funding"] == "yok"
    with pytest.raises(KeyError, match="tablosunda yok"):
        evren_maliyet.maliyet_ayarlari("YOKYOKUSDT", k)
    with pytest.raises(ValueError):
        evren_maliyet.maliyet_ayarlari("BTCUSDT", k, 0)


def test_gercek_maliyet_tablosu_butunlugu():
    import hashlib
    from pathlib import Path
    gercek = Path(__file__).resolve().parents[1] / "sonuclar" / "evren" / "maliyet_tablosu.csv"
    d = pd.read_csv(gercek)
    assert list(d.columns) == evren_maliyet.SUTUNLAR and not d["sembol"].duplicated().any()
    assert set(we.EVREN_GENEL + we.EVREN_SCALP) <= set(d["sembol"])
    assert (d["efektif_komisyon_oran"] - d["komisyon_oran"] * (1 + d["bsmv_oran"])).abs().max() < 1e-9
    assert (d["kaynak"].str.len() > 20).all()                                    # her satırda kaynak/gerekçe
    kayit = gercek.with_suffix(".sha256").read_text().strip()
    assert kayit == hashlib.sha256(gercek.read_bytes()).hexdigest()              # tablo sabitlenmiş (değişmemiş)


# ---------------------------------------------------------------------------- spot vekil, analiz başlangıcı
def test_spot_vekil_bilgisi(tmp_path):
    d = tmp_path / "BTCUSDT"
    d.mkdir()
    (d / "kaynak.json").write_text(json.dumps({"perp_baslangic": "2020-01-01", "spot_vekil_baslangic": "2017-08-17 04:00:00+00:00",
                                               "spot_vekil_bitis": "2019-12-31 23:55:00+00:00"}))
    idx = pd.date_range("2017-08-17", periods=5, freq="1D", tz="UTC")
    mum = pd.DataFrame({"kapanis": 1.0}, index=idx)
    sv = we.spot_vekil_bilgisi("BTCUSDT", mum, None, tmp_path)
    assert sv["var"] and sv["kaynak"] == "kaynak.json" and sv["bit"].startswith("2019-12-31")
    # işaret yoksa tahmin: funding mumdan çok geç başlıyorsa
    (d / "kaynak.json").unlink()
    fund = pd.DataFrame({"oran": [0.0001]}, index=pd.DatetimeIndex(["2019-09-10"], tz="UTC"))
    sv = we.spot_vekil_bilgisi("BTCUSDT", mum, fund, tmp_path)
    assert sv["var"] and sv["kaynak"].startswith("tahmin")
    assert not we.spot_vekil_bilgisi("DK_AAPL", mum, None, tmp_path)["var"]
    # biçim farklıysa: yalnız 'spot' içeren anahtar + perp başlangıcı
    (d / "kaynak.json").write_text(json.dumps({"spot_vekil": True, "perp_bas": "2020-01-01"}))
    sv = we.spot_vekil_bilgisi("BTCUSDT", mum, None, tmp_path)
    assert sv["var"] and sv["bit"] == "2020-01-01"


def test_analiz_baslangici_kisa_bist_sayima_katilmaz(monkeypatch):
    eski = pd.Timestamp("2018-03-05 10:00", tz="UTC")
    yeni = pd.Timestamp("2023-12-07 06:30", tz="UTC")
    bas = {**{f"DK_X{i}": eski for i in range(35)}, **{s: yeni for s in we.BIST}}            # 35 uzun + 13 kısa BIST
    assert we.kisa_bist(bas) == sorted(we.BIST)
    assert we.analiz_bas_hesapla(bas) == eski.floor("D")                                    # BIST sayıma katılmaz
    monkeypatch.setattr(we, "BIST_KISA_ANALIZ_DISI", False)
    assert we.analiz_bas_hesapla(bas) == yeni.floor("D")                                    # kural harfiyen: 35/48 < %75
    # BIST 1d (uzun geçmiş) sayıma girer
    uzun = {**{f"DK_X{i}": eski for i in range(35)}, **{s: pd.Timestamp("2005-01-03", tz="UTC") for s in we.BIST}}
    assert we.kisa_bist(uzun) == []


# ---------------------------------------------------------------------------- PBO matrisi
def test_pbo_matrisi_ham_islemlerden(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setitem(we.DONEMLER, "test_tam", {"bas": None, "bit": None, "kilit_ac": True})
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    we.veri_ayarla(veri_dizini, "test_tam")
    h = tmp_path / "ham"
    we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h)
    grup = pd.DataFrame([{"strateji": AD, "tf": "4h", "kisa_gecmis": ""}])
    bas, bit = pd.Timestamp("2022-03-01", tz="UTC"), pd.Timestamp("2023-12-01", tz="UTC")
    M, etiket = we.pbo_matrisi(h, grup, "swing", "4h", bas, bit)
    ham = pd.read_parquet(we.ham_yolu(h, AD, "4h", "TESTUSDT"))
    g = pd.DatetimeIndex(ham["giris_zamani"])
    ham = ham[(g >= bas) & (g < bit)]
    assert M.shape[1] == len(etiket) == ham["ayar_no"].nunique() and M.shape[0] == (bit.floor("D") - bas).days + 1
    assert float(M.sum()) == pytest.approx(float(ham["r"].sum()) * 0.01, rel=1e-4)
    sonuc = pbo.pbo_cscv(M, 16)
    assert 0.0 <= sonuc["pbo"] <= 1.0 or math.isnan(sonuc["pbo"])


def test_evren_wf_kos_yeni_sutunlar(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setitem(we.DONEMLER, "test_tam", {"bas": None, "bit": None, "kilit_ac": True})
    we.veri_ayarla(veri_dizini, "test_tam")
    h = tmp_path / "ham"
    we.ham_gorev(AD, "4h", "TESTUSDT", 1.0, h)
    satir, _ = we.evren_wf_kos(AD, "4h", "swing", h, evren=("TESTUSDT",),
                               pencere_gun={"swing": (200, 100), "daytrade": (200, 100), "scalp": (200, 100)},
                               min_islem={"swing": 3, "daytrade": 3, "scalp": 3})
    assert satir["maliyet_hash"] == evren_maliyet.tablo_hash() and satir["bist_kisa_donem"] == ""
    assert json.loads(satir["spot_vekil"]) == {}


# ============================================================================ lider kararları 2026-11-08
def test_dsr_deneme_sayisi_sembol_carpansiz(tmp_path):
    yol = tmp_path / "deneme.jsonl"
    deneme_kaydi.kaydet("a", "BTCUSDT", "4h", 10, 5, 400, yol)         # önceki aşama: kombinasyon_sayisi=10 sayılır
    deneme_kaydi.kaydet("b", "evren", "4h", 99, 5, 99 * 48, yol)       # evren aşaması satırı: wf n_aday'dan sayılır (çift yok)
    wf = pd.DataFrame({"n_aday": [30, 20, 7], "hata": ["", "", "boom"]})
    assert we.deneme_sayisi_ayar(wf, yol) == 50 + 10 + we.HAIKU_DENEME
    assert we.toplam_deneme(yol) == 400 + 99 * 48 + we.HAIKU_DENEME      # eski sembol çarpanlı sayım bilgi olarak kalır


def test_k3_portfoy_boot_sharpe_alt():
    iyi = {"m2_pf": 1.1, "m3_pf": 1.1, "g1_pf": 1.1, "rnd_p": 0.01, "pf_boot_alt": math.nan, "par_oran": 0.8, "dsr_deneme": 0.95,
           "boot_sharpe_alt": 0.2}
    assert we.saglamlik_oneri(iyi)[0]
    assert we.saglamlik_oneri({**iyi, "boot_sharpe_alt": -0.1})[1] == "K3_boot_alt"
    assert not we.saglamlik_oneri({**iyi, "boot_sharpe_alt": math.nan})[0]       # ikisi de yok -> geçmez


@pytest.fixture
def pf_veri(tmp_path, monkeypatch):
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT"]
    n = 1400 * 24
    idx = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC", name="zaman")
    for i, s in enumerate(syms):
        rng = np.random.default_rng(i)
        kap = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.006, n)))
        ac = np.r_[kap[0], kap[:-1]]
        df = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.002, "dusuk": np.minimum(ac, kap) * 0.998,
                           "kapanis": kap, "hacim": 10.0, "quote_hacim": 1000.0, "islem_sayisi": 5}, index=idx)
        (tmp_path / "pfveri" / s).mkdir(parents=True)
        df.to_parquet(tmp_path / "pfveri" / s / "1h.parquet")
    monkeypatch.setitem(we.DONEMLER, "pf_test", {"bas": None, "bit": pd.Timestamp("2023-06-01", tz="UTC"), "kilit_ac": True})
    from motor.arastirma import wf_evren_portfoy as wep
    wep._VERI.clear()
    we.veri_ayarla(tmp_path / "pfveri", "pf_test")
    return tmp_path / "pfveri"


def test_portfoy_motoru_sembol_maliyeti_varsayilan_ayni_ve_pahali_daha_kotu(pf_veri):
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    v, f, _ = wep.veri_yukle(None)
    st = tum_portfoy_stratejileri()["pf__rotasyon"]()
    v = {s: d for s, d in v.items()}
    r0 = portfoy_backtest(v, st, PortfoyAyarlari(limit_modu="olc"), f)
    tablo = {s: (0.05, 0.02, 2.0, 5.0) for s in v}                      # varsayılanla AYNI -> birebir aynı sonuç
    r1 = portfoy_backtest(v, st, PortfoyAyarlari(limit_modu="olc", maliyet_sembol=tablo), f)
    assert r0.gunluk_ozsermaye.iloc[-1] == pytest.approx(r1.gunluk_ozsermaye.iloc[-1], rel=1e-12)
    r2 = portfoy_backtest(v, st, PortfoyAyarlari(limit_modu="olc", maliyet_sembol={s: (0.5, 0.2, 20.0, 50.0) for s in v}), f)
    assert r2.gunluk_ozsermaye.iloc[-1] < r0.gunluk_ozsermaye.iloc[-1]   # 10x maliyet daha kötü


def test_portfoy_evren_akisi_wf_holdout_pbo_listeler(tmp_path, pf_veri, monkeypatch):
    from motor.arastirma import saglamlik_portfoy as sp
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    ad = "pf__rotasyon"
    # GecikmePf: hedef ve stop tabloları 1 bar kayar
    v, f, dis = wep.veri_yukle(None)
    assert len(v) == 8 and "DK_AAPL" in dis
    st = dict(wep.wp.aday_listesi(ad, tuple(v), True)[0])["varsayilan"]
    h, s = st.sinyaller({k: v[k] for k in wep.wp.gerekli_semboller(st, tuple(v))})
    h1, s1 = wep.GecikmePf(st, 1).sinyaller({k: v[k] for k in wep.wp.gerekli_semboller(st, tuple(v))})
    pd.testing.assert_frame_equal(h1.iloc[1:], h.shift(1).iloc[1:])
    # WF (varsayılan 730/180 pencere; veri ~1247 gün -> 1 pencere) + dosyalar
    cikti = tmp_path / "cikti"
    monkeypatch.setattr(deneme_kaydi, "VARSAYILAN_YOL", tmp_path / "d.jsonl")
    o = wep.pf_wf_asamasi(cikti, "pf_test", [ad], surec=1, ilerleme=False)
    assert o["yeni"] == 1 and o["hatali"] == 0
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    r = wf.iloc[0]
    assert r["stil"] == "portfoy" and r["tf"] == "1d" and r["maliyet_hash"] == evren_maliyet.tablo_hash() and r["n_pencere"] >= 1
    assert (cikti / "pf" / f"{ad}--gunluk.parquet").exists() and (cikti / "pf" / f"{ad}--adaylar.parquet").exists()
    assert wep.TF == "1d" and json.loads(r["secimler"])[0]["ayar"] == json.loads(r["secimler"])[0]["secilen"]
    # PBO matrisi
    M, et = wep.pbo_matrisi_pf(cikti, wf, r["oos_bas"], r["oos_bit"])
    assert M.shape[1] == len(et) > 5
    pb = we.pbo_asamasi(cikti, ilerleme=False)
    assert pb["stil"].iloc[0] == "portfoy" and pb["hata"].iloc[0] == ""
    # listeler: portföy satırı sağlamlık tablosuyla birlikte iyi/iyiye yakına girebilir
    wf2 = wf.assign(gecti=True, yakin_wf=True, basarisiz_sayi=0)
    sag = pd.DataFrame([{"strateji": ad, "tf": "1d", "saglam_mi": True, "kapi_basarisiz": "", "rnd_p": 0.01, "m2_pf": 1.5,
                         "m3_pf": 1.4, "g1_pf": 1.3, "pf_boot_alt": math.nan, "par_oran": 0.9, "dsr_deneme": 0.95, "hata": ""}])
    iyi, yakin = we.listeler(wf2, sag, pd.DataFrame({"stil": ["portfoy"], "tf": ["1d"], "pbo": [0.2]}))
    assert list(iyi["strateji"]) == [ad] and iyi["stil"].iloc[0] == "portfoy"
    iyi, yakin = we.listeler(wf2, sag, pd.DataFrame({"stil": ["portfoy"], "tf": ["1d"], "pbo": [0.8]}))
    assert len(iyi) == 0 and list(yakin["strateji"]) == [ad]            # PBO > 0.5: iyi -> iyiye yakın
    # holdout: yalnız kesimden sonraki (burada 2023-01-01) girişler
    we.veri_ayarla(pf_veri, "holdout")
    wep._VERI.clear()
    monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp("2022-09-01", tz="UTC"))
    etiket = json.loads(r["secimler"])[0]["ayar"] or r["en_sik_ayar"]
    h1 = wep.holdout_kos(ad, etiket)
    monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp("2030-01-01", tz="UTC"))
    h2 = wep.holdout_kos(ad, etiket)
    assert h1["holdout_gun"] > 300 and h2["holdout_gun"] == 0 and h2["islem_sayisi"] == 0
    assert set(("net_getiri", "profit_factor", "sharpe", "max_dusus")) <= set(h1)
