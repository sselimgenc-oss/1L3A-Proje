"""Tarama altyapısı: sentetik veriyle küçük tarama, devam etme, hata satırı, umutsuz_mu, kilit."""
import numpy as np
import pandas as pd
import pytest

from motor.arastirma import tarama
from motor.backtest import deneme_kaydi
from motor.backtest import metrikler as mtr
from motor.strateji import kayit
from motor.strateji.temel import Strateji
from motor.veri import kilit

SW = "swing__donchian-kirilim"
DT = "daytrade__donchian-kirilim"
CIKISSIZ = "test__cikissiz"
SEMBOL = "TESTUSDT"


class Cikissiz(Strateji):
    ad = CIKISSIZ
    stil = "swing"
    varsayilan_parametreler = {}

    def sinyaller(self, mumlar):
        return pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=mumlar.index)


@pytest.fixture
def kayitli(monkeypatch):
    gercek = kayit.al
    monkeypatch.setattr(kayit, "al", lambda ad: Cikissiz if ad == CIKISSIZ else gercek(ad))


@pytest.fixture
def veri_dizini(tmp_path):
    rng = np.random.default_rng(7)
    n = 150 * 288
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC", name="zaman")
    kap = 100 * np.exp(np.cumsum(rng.normal(0.00002, 0.002, n)))
    ac = np.r_[kap[0], kap[:-1]]
    df = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.001, "dusuk": np.minimum(ac, kap) * 0.999,
                       "kapanis": kap, "hacim": 10.0, "quote_hacim": 1000.0, "islem_sayisi": 5}, index=idx)
    d = tmp_path / "veri" / SEMBOL
    d.mkdir(parents=True)
    df.to_parquet(d / "5m.parquet")
    fi = pd.date_range("2024-01-01", periods=150 * 3, freq="8h", tz="UTC", name="zaman")
    pd.DataFrame({"oran": 0.0001}, index=fi).to_parquet(d / "funding.parquet")
    return tmp_path / "veri"


def _tara(tmp_path, veri_dizini, etiket="t1", stratejiler=(SW,), **kw):
    kw.setdefault("surec", 1)
    return tarama.tara(etiket, list(stratejiler), [SEMBOL], {"swing": ("4h",), "daytrade": ("1h",)},
                       cikti_dizini=tmp_path / "cikti", veri_dizini=veri_dizini, ilerleme=False, **kw)


def test_metrik_alanlari_hesapla_ile_uyumlu():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    islemler = pd.DataFrame({"net_pnl": [1.0, -1.0], "r": [1.0, -1.0], "komisyon": [0.1, 0.1], "funding": [0.0, 0.0],
                             "giris_zamani": idx[:2], "cikis_zamani": idx[1:]})
    m = mtr.hesapla(islemler, pd.Series([1.0, 2.0, 1.5], index=idx), 1.0)
    assert set(m) == set(tarama.METRIK_ALANLARI)


def test_kucuk_tarama_cikti_ve_kolonlar(tmp_path, veri_dizini):
    df = _tara(tmp_path, veri_dizini, stratejiler=(SW, DT), izgara=True)
    assert list(df.columns) == tarama.SUTUNLAR
    assert set(df.strateji) == {SW, DT}
    assert set(df.ayar_kaynagi) >= {"varsayilan", "izgara"}
    assert (df.hata == "").all()
    assert (df.sure_sn > 0).all() and (df.islem_sayisi > 0).any()
    # izgara satırları: swing 3*3*2 = 18 + varsayılan 1 (kart ayarı varsa ek)
    assert (df[(df.strateji == SW) & (df.ayar_kaynagi == "izgara")].shape[0]) == 18
    assert all(isinstance(p, str) and p.startswith("{") for p in df.parametreler)
    cd = tmp_path / "cikti"
    assert (cd / "t1.parquet").exists() and (cd / "t1.csv").exists() and (cd / "t1_ozet.csv").exists()
    assert len(pd.read_parquet(cd / "t1.parquet")) == len(df)
    # deneme kaydı: strateji başına bir satır, toplam_kosu = hatasız koşu sayısı
    kayitlar = deneme_kaydi.oku()
    assert {k["strateji"] for k in kayitlar} == {SW, DT}
    assert deneme_kaydi.toplam_deneme(SW) == (df.strateji == SW).sum()


def test_devam_etme_biten_gorevleri_atlar(tmp_path, veri_dizini, monkeypatch):
    ilk = _tara(tmp_path, veri_dizini, stratejiler=(SW,))
    cagrilar = []
    gercek = tarama._calistir
    monkeypatch.setattr(tarama, "_calistir", lambda g: cagrilar.append(g["strateji"]) or gercek(g))
    ikinci = _tara(tmp_path, veri_dizini, stratejiler=(SW, DT))
    assert set(cagrilar) == {DT}                                  # SW tekrar koşulmadı
    assert len(ikinci) == len(ilk) + len(cagrilar)
    cagrilar.clear()
    _tara(tmp_path, veri_dizini, stratejiler=(SW, DT))
    assert cagrilar == []                                         # her şey bitmişti


def test_hata_satira_yazilir_tarama_durmaz(tmp_path, veri_dizini, kayitli):
    df = _tara(tmp_path, veri_dizini, stratejiler=(CIKISSIZ, SW))
    h = df[df.strateji == CIKISSIZ]
    assert len(h) == 1 and "CikisYokHatasi" in h.hata.iloc[0] and h.islem_sayisi.isna().all()
    assert (df[df.strateji == SW].hata == "").all()
    # hatalı satır deneme kaydına koşu olarak yazılmaz
    assert deneme_kaydi.toplam_deneme(CIKISSIZ) == 0
    # varsayılan: hata satırı da "bitmiş" sayılır; --hatalari-yeniden ile tekrar denenir
    cagrilar = []
    gercek = tarama._calistir
    import motor.arastirma.tarama as t
    t._calistir = lambda g: cagrilar.append(g["strateji"]) or gercek(g)
    try:
        _tara(tmp_path, veri_dizini, stratejiler=(CIKISSIZ, SW))
        assert cagrilar == []
        _tara(tmp_path, veri_dizini, stratejiler=(CIKISSIZ, SW), hatalari_yeniden=True)
        assert cagrilar == [CIKISSIZ]
    finally:
        t._calistir = gercek


def test_coklu_surec_ayni_sonuc(tmp_path, veri_dizini):
    a = _tara(tmp_path, veri_dizini, etiket="tek", stratejiler=(SW, DT), surec=1)
    b = _tara(tmp_path, veri_dizini, etiket="cok", stratejiler=(SW, DT), surec=2)
    kol = ["strateji", "sembol", "tf", "ayar_kaynagi", "parametreler"]
    a, b = a.sort_values(kol).reset_index(drop=True), b.sort_values(kol).reset_index(drop=True)
    pd.testing.assert_frame_equal(a.drop(columns="sure_sn"), b.drop(columns="sure_sn"))


def test_kilitli_donem_taramaya_girmez(tmp_path, veri_dizini, monkeypatch):
    sinir = pd.Timestamp("2024-04-01", tz="UTC")
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", sinir)
    df = _tara(tmp_path, veri_dizini, stratejiler=(SW,))
    mumlar, fund = tarama._veri(SEMBOL, "4h")
    assert mumlar.index.max() < sinir and fund.index.max() < sinir
    assert not kilit.KILIT_LOG.exists()                           # kilit_ac hiç kullanılmadı
    assert (df.hata == "").all()
    # kaynak kodda kilit_ac yok
    import inspect
    assert "kilit_ac=True" not in inspect.getsource(tarama)


def _satir(strateji, pf, islem=20, hata=""):
    return {"strateji": strateji, "stil": "swing", "sembol": "BTCUSDT", "tf": "1d", "ayar_kaynagi": "varsayilan",
            "parametreler": "{}", "cikis_ayarlari": "{}", "profit_factor": pf, "islem_sayisi": islem,
            "net_getiri": 0.1, "max_dusus": 0.2, "hata": hata}


def test_umutsuz_mu_ve_ozet():
    df = pd.DataFrame([
        _satir("a", 0.5), _satir("a", 0.79), _satir("a", np.nan, islem=0),          # hepsi kötü -> umutsuz
        _satir("b", 0.5), _satir("b", 1.3),                                          # biri iyi -> değil
        _satir("c", 0.5, hata=""), _satir("c", np.nan, islem=np.nan, hata="Hata: x"),  # hatalı satır kanıt değil
        _satir("d", np.nan, islem=np.nan, hata="Hata: x"),                           # yalnız hata -> işaretlenmez
        _satir("e", 0.8),                                                            # eşit -> umutsuz değil
    ])
    u = tarama.umutsuz_mu(df)
    assert u.to_dict() == {"a": True, "b": False, "c": True, "d": False, "e": False}
    assert tarama.umutsuz_mu(df, pf_esik=1.5)["b"]                                  # eşik yükselince b de umutsuz
    o = tarama.ozet(df).set_index("strateji")
    assert o.loc["b", "en_iyi_pf"] == 1.3 and o.loc["b", "medyan_pf"] == pytest.approx(0.9)
    assert bool(o.loc["a", "umutsuz"]) and not bool(o.loc["b", "umutsuz"])
    assert o.loc["d", "hata_sayisi"] == 1
    assert len(df) == 9                                                              # hiçbir şey silinmedi
