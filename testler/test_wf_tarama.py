"""Hızlı walk-forward (wf_tarama): seçim yalnız eğitim verisiyle, pencere örtüşmesi yok, tek aday, kilit, devam etme."""
import inspect
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_tarama as wf
from motor.backtest import deneme_kaydi
from motor.backtest.walk_forward import pencereler_uret
from motor.veri import kilit

SW = "swing__donchian-kirilim"
SEMBOL = "TESTUSDT"
T0 = pd.Timestamp("2022-01-01", tz="UTC")


def _g(gun):
    return T0 + pd.Timedelta(days=gun)


def _islemler(satirlar):
    """satirlar: [(giris_gun, cikis_gun, r, yon)] -> motor işlem tablosu biçiminde."""
    return pd.DataFrame({"giris_zamani": [_g(a) for a, _, _, _ in satirlar], "cikis_zamani": [_g(b) for _, b, _, _ in satirlar],
                         "r": [float(r) for _, _, r, _ in satirlar], "yon": [y for _, _, _, y in satirlar],
                         "net_pnl": [float(r) * 100 for _, _, r, _ in satirlar]})


def _seri(gunler, r_ornek):
    """Her gün için 1 günlük işlem; r değerleri döngüyle."""
    return [(g, g + 0.5, r_ornek[i % len(r_ornek)], 1) for i, g in enumerate(gunler)]


PENCERELER = pencereler_uret(T0, _g(400), 100, 50)      # eğitim 100g, test 50g


def test_pencereler_ortusmez_uc_uca():
    assert len(PENCERELER) >= 5
    for (e0, e1, t0, t1), (_, _, n0, _) in zip(PENCERELER, PENCERELER[1:]):
        assert e1 == t0 and t1 == n0                    # eğitim testten hemen önce; test pencereleri uç uca
        assert t0 < t1


def test_secim_yalniz_egitim_islemlerini_gorur():
    """'gecmis_iyi' eğitimde iyi, testte kötü; 'gelecek_iyi' eğitimde kötü, testte dev kâr: seçilen gecmis_iyi olmalı."""
    gunler_hepsi = list(range(0, 400, 2))
    iyi, gelecek = [], []
    for g in gunler_hepsi:
        e0_i = None
        # hangi pencerenin testi mi eğitimi mi olduğunu göz ardı et: pencere 1 (idx 0) test aralığı [100,150)
        test_mi = 100 <= g < 150
        iyi.append((g, g + 0.5, -1.0 if test_mi else (2.0 if g % 4 == 0 else -0.5), 1))
        gelecek.append((g, g + 0.5, 50.0 if test_mi else (-1.0 if g % 4 == 0 else 0.4), 1))
    adaylar = {"gelecek_iyi": _islemler(gelecek), "gecmis_iyi": _islemler(iyi)}
    oos, sec = wf.secim_ve_oos(adaylar, PENCERELER[:1], min_islem=10)
    assert sec[0]["secilen"] == "gecmis_iyi"
    assert (oos["r"] <= 0).all()                        # testteki dev kâr (50R) OOS'a hiç sızmadı, seçim ona bakmadı
    assert set(oos["ayar"]) == {"gecmis_iyi"}


def test_egitim_sonunda_acik_islem_skora_girmez():
    """Eğitim bitişinden sonra kapanan işlemin sonucu seçimde bilinemez: işlem sayısına/PF'ye katılmaz."""
    e0, e1, t0, t1 = PENCERELER[0]
    gun_e1 = (e1 - T0).days
    satir = [(g, g + 0.5, 1.0 if g % 2 else -0.5, 1) for g in range(1, 10)]
    satir.append((gun_e1 - 1, gun_e1 + 3, 100.0, 1))    # eğitimde girilir, testte kapanır
    a = wf.AdayIslemleri(_islemler(satir))
    n, pf = a.skor(e0, e1)
    assert n == 9 and pf < 10                           # 100R'lik işlem sayılmadı
    oos, sec = wf.secim_ve_oos({"x": _islemler(satir)}, PENCERELER[:1], min_islem=10)
    assert sec[0]["secilen"] is None and oos.empty      # 9 işlem < 10 -> aday yok -> işlem yok


def test_kimse_kosulu_saglamazsa_o_pencerede_islem_yok():
    adaylar = {"az": _islemler(_seri(range(0, 400, 40), [1.0, -0.5]))}
    oos, sec = wf.secim_ve_oos(adaylar, PENCERELER, min_islem=50)
    assert oos.empty and all(s["secilen"] is None for s in sec)


def test_tek_aday_oos_test_pencerelerindeki_islemler():
    r = _islemler(_seri(range(0, 400), [1.0, -0.5, 0.7]))
    oos, sec = wf.secim_ve_oos({"tek": r}, PENCERELER, min_islem=5)
    bek = pd.concat([r[(r.giris_zamani >= t0) & (r.giris_zamani < t1)] for _, _, t0, t1 in PENCERELER])
    assert all(s["secilen"] == "tek" for s in sec)
    assert len(oos) == len(bek)
    pd.testing.assert_series_equal(oos["giris_zamani"].reset_index(drop=True), bek["giris_zamani"].reset_index(drop=True))
    assert oos["giris_zamani"].is_unique                # hiçbir işlem iki pencerede değil
    for w, (_, _, t0, t1) in enumerate(PENCERELER):     # her işlem kendi test penceresinde
        d = oos[oos["pencere"] == w]
        assert ((d.giris_zamani >= t0) & (d.giris_zamani < t1)).all()


def test_oos_metrikleri_elle_dogrulama():
    r = _islemler([(1, 2, 1.0, 1), (3, 4, -0.5, -1), (5, 6, 2.0, 1), (7, 8, -1.0, -1)])
    r["giris_zamani"] = [pd.Timestamp("2022-03-01", tz="UTC") + pd.Timedelta(days=g) for g in (1, 3, 5, 7)]
    r["cikis_zamani"] = r["giris_zamani"] + pd.Timedelta(hours=12)
    m = wf.oos_metrikleri(r, pd.Timestamp("2022-03-01", tz="UTC"), pd.Timestamp("2022-03-20", tz="UTC"))
    assert m["islem_sayisi"] == 4 and m["profit_factor"] == pytest.approx(3.0 / 1.5)
    assert m["pf_long"] == math.inf and m["pf_short"] == 0.0 and m["n_long"] == 2
    assert m["net_getiri"] == pytest.approx(1.01 * 0.995 * 1.02 * 0.99 - 1)
    assert m["pf_2022"] == pytest.approx(2.0) and np.isnan(m["pf_2023"])
    assert m["en_iyi_yuzde5_haric_pf"] == pytest.approx(1.0 / 1.5)      # 1 işlem (2R) çıkar


# ---------------------------------------------------------------------------- uçtan uca (sentetik veri)
@pytest.fixture
def veri_dizini(tmp_path):
    rng = np.random.default_rng(7)
    n = 500 * 288
    idx = pd.date_range("2022-01-01", periods=n, freq="5min", tz="UTC", name="zaman")
    kap = 100 * np.exp(np.cumsum(rng.normal(0.00002, 0.002, n)))
    ac = np.r_[kap[0], kap[:-1]]
    df = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.001, "dusuk": np.minimum(ac, kap) * 0.999,
                       "kapanis": kap, "hacim": 10.0, "quote_hacim": 1000.0, "islem_sayisi": 5}, index=idx)
    d = tmp_path / "veri" / SEMBOL
    d.mkdir(parents=True)
    df.to_parquet(d / "5m.parquet")                      # funding dosyası YOK -> funding=None
    return tmp_path / "veri"


KISA = {"pencere_gun": {"swing": (120, 60), "daytrade": (120, 60), "scalp": (120, 60)},
        "min_islem": {"swing": 3, "daytrade": 3, "scalp": 3}}


def _wf(tmp_path, veri_dizini, etiket="w1", **kw):
    kw.setdefault("surec", 1)
    kw = {**KISA, **kw}
    return wf.wf_tara(etiket, [SW], [SEMBOL], cikti_dizini=tmp_path / "wf", veri_dizini=veri_dizini, ilerleme=False, **kw)


def test_uctan_uca_ciktilar_ve_deneme_kaydi(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(wf.tarama, "STIL_TF", {"swing": ("4h",), "daytrade": ("1h",), "scalp": ("1h",)})
    df = _wf(tmp_path, veri_dizini)
    assert len(df) == 1 and df.hata.iloc[0] == "" and df.n_kosu.iloc[0] > 1
    s = df.iloc[0]
    assert s.n_pencere >= 3 and s.n_aday >= s.n_kosu
    for kol in ("gecti", "nedenler", "profit_factor", "sharpe", "bh_getiri", "bh_sharpe", "pf_2022", "n_farkli_ayar",
                "en_sik_pay", "pf_long", "pf_short"):
        assert kol in df.columns
    assert (tmp_path / "wf" / "w1.parquet").exists() and (tmp_path / "wf" / "w1.csv").exists()
    if s.islem_sayisi > 0:
        yol = wf.islem_yolu(tmp_path / "wf", "w1", SW, SEMBOL, "4h")
        t = pd.read_parquet(yol)
        assert len(t) == s.islem_sayisi and {"giris_zamani", "r", "ayar", "pencere"} <= set(t.columns)
    k = deneme_kaydi.oku()
    assert len(k) == 1 and k[0]["toplam_kosu"] == s.n_kosu and k[0]["kombinasyon_sayisi"] == s.n_aday
    assert k[0]["pencere_sayisi"] == s.n_pencere


def test_devam_etme_cift_sayma_yok(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(wf.tarama, "STIL_TF", {"swing": ("4h",), "daytrade": ("1h",), "scalp": ("1h",)})
    _wf(tmp_path, veri_dizini)
    cagrilar = []
    gercek = wf.gorev_calistir
    monkeypatch.setattr(wf, "gorev_calistir", lambda g: cagrilar.append(g["strateji"]) or gercek(g))
    ikinci = _wf(tmp_path, veri_dizini)
    assert cagrilar == [] and len(ikinci) == 1                       # biten görev tekrar koşulmadı
    assert len(deneme_kaydi.oku()) == 1                              # deneme kaydı çiftlenmedi
    # yeni görev eklenince yalnız o koşulur ve yalnız o yazılır
    ucuncu = wf.wf_tara("w1", [SW, "daytrade__donchian-kirilim"], [SEMBOL], surec=1, cikti_dizini=tmp_path / "wf",
                        veri_dizini=veri_dizini, ilerleme=False, **KISA)
    assert cagrilar == ["daytrade__donchian-kirilim"] and len(ucuncu) == 2
    assert [k["strateji"] for k in deneme_kaydi.oku()] == [SW, "daytrade__donchian-kirilim"]


def test_kilitli_donem_girmez(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(wf.tarama, "STIL_TF", {"swing": ("4h",), "daytrade": ("1h",), "scalp": ("1h",)})
    sinir = pd.Timestamp("2023-02-01", tz="UTC")
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", sinir)
    df = _wf(tmp_path, veri_dizini)
    assert df.hata.iloc[0] == ""
    mumlar, fund = wf._veri(SEMBOL, "4h")
    assert mumlar.index.max() < sinir and fund is None
    assert pd.Timestamp(df.oos_bit.iloc[0]) <= sinir
    assert not kilit.KILIT_LOG.exists()
    assert "kilit_ac=True" not in inspect.getsource(wf)


def test_hata_satira_yazilir(tmp_path, veri_dizini, monkeypatch):
    monkeypatch.setattr(wf.tarama, "STIL_TF", {"swing": ("4h",), "daytrade": ("1h",), "scalp": ("1h",)})
    df = wf.wf_tara("h", [SW], ["YOKUSDT"], surec=1, cikti_dizini=tmp_path / "wf", veri_dizini=veri_dizini,
                    ilerleme=False, **KISA)
    assert "FileNotFoundError" in df.hata.iloc[0] and not df.gecti.iloc[0]
    assert deneme_kaydi.oku() == []                                  # hatalı görev deneme sayılmaz
