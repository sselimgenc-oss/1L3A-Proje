"""Portföy walk-forward (wf_portfoy): seçim yalnız eğitimi görür, pencereler örtüşmez, kilit, devam etme, deneme kaydı."""
import inspect
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_portfoy as wp
from motor.backtest import deneme_kaydi
from motor.backtest.walk_forward import pencereler_uret
from motor.portfoy.stratejiler.ortak import KRIPTO
from motor.veri import kilit

T0 = pd.Timestamp("2022-01-01", tz="UTC")


def _g(gun):
    return T0 + pd.Timedelta(days=gun)


def _aday(getiri_fn, islem_gunleri, n=500):
    """getiri_fn(gun) -> günlük getiri; işlemler verilen günlerde girilir (r = +-1)."""
    gunler = pd.date_range(T0, periods=n, freq="D", tz="UTC")
    g = pd.Series([getiri_fn(i) for i in range(n)], index=gunler)
    isl = pd.DataFrame({"giris_zamani": [_g(d) for d in islem_gunleri], "cikis_zamani": [_g(d + 1) for d in islem_gunleri],
                        "r": [1.0 if d % 2 else -0.5 for d in islem_gunleri], "yon": 1, "net_pnl": 1.0})
    return wp.AdayHesap(g, isl, 0.1, [])


PENCERELER = pencereler_uret(T0, _g(500), 100, 50)


def test_pencereler_ortusmez_uc_uca_ve_varsayilan_730_180():
    assert len(PENCERELER) >= 5
    for (e0, e1, t0, t1), (_, _, n0, _) in zip(PENCERELER, PENCERELER[1:]):
        assert e1 == t0 and t1 == n0 and t0 < t1
    p = pencereler_uret(T0, _g(2100), wp.EGITIM_GUN, wp.TEST_GUN)
    assert (wp.EGITIM_GUN, wp.TEST_GUN) == (730, 180) and len(p) >= 7
    assert all(a[3] <= b[2] for a, b in zip(p, p[1:]))


def test_secim_yalniz_egitim_gunlerini_gorur():
    """'gecmis_iyi' eğitimde iyi, testte kötü; 'gelecek_iyi' eğitimde kötü, testte çok iyi -> gecmis_iyi seçilir."""
    e0, e1, t0, t1 = PENCERELER[0]
    gt0, gt1 = (t0 - T0).days, (t1 - T0).days

    def test_mi(i):
        return gt0 <= i < gt1

    rng = np.random.default_rng(0)
    gurultu = rng.normal(0, 0.002, 500)
    gecmis = _aday(lambda i: (-0.01 if test_mi(i) else 0.003) + gurultu[i], range(0, 500, 3))
    gelecek = _aday(lambda i: (0.05 if test_mi(i) else -0.002) + gurultu[i], range(0, 500, 3))
    getiri, oos, sec = wp.secim_ve_oos({"gelecek_iyi": gelecek, "gecmis_iyi": gecmis}, PENCERELER[:1], min_islem=10, min_gun=30)
    assert sec[0]["secilen"] == "gecmis_iyi"
    assert getiri.sum() < 0                          # testteki dev kazanç (gelecek_iyi) OOS'a hiç girmedi
    assert set(oos["ayar"]) == {"gecmis_iyi"}
    # test penceresini değiştirmek eğitim seçimini değiştirmez
    bozuk = _aday(lambda i: (123.0 if test_mi(i) else 0.003) + gurultu[i], range(0, 500, 3))
    _, _, sec2 = wp.secim_ve_oos({"gelecek_iyi": gelecek, "gecmis_iyi": bozuk}, PENCERELER[:1], min_islem=10, min_gun=30)
    assert sec2[0]["secilen"] == "gecmis_iyi" and sec2[0]["egitim_sharpe"] == sec[0]["egitim_sharpe"]


def test_egitim_kriterleri_az_islem_ve_az_gun_ve_sifir_oynaklik():
    rng = np.random.default_rng(1)
    g = rng.normal(0.002, 0.005, 500)
    az_islem = _aday(lambda i: g[i], range(0, 500, 40))                    # eğitimde < 10 işlem
    oos_getiri, oos, sec = wp.secim_ve_oos({"az": az_islem}, PENCERELER, min_islem=10, min_gun=30)
    assert all(s["secilen"] is None for s in sec) and oos.empty and (oos_getiri == 0).all()
    sabit = _aday(lambda i: 0.0, range(0, 500, 2))                         # std = 0 -> skor tanımsız
    _, _, sec2 = wp.secim_ve_oos({"sabit": sabit}, PENCERELER, min_islem=10, min_gun=30)
    assert all(s["secilen"] is None for s in sec2)
    tam = _aday(lambda i: g[i], range(0, 500, 2))
    _, _, sec3 = wp.secim_ve_oos({"tam": tam}, PENCERELER, min_islem=10, min_gun=30)
    assert all(s["secilen"] == "tam" for s in sec3)
    _, _, sec4 = wp.secim_ve_oos({"tam": tam}, PENCERELER, min_islem=10, min_gun=10_000)
    assert all(s["secilen"] is None for s in sec4)


def test_oos_yalniz_test_pencerelerinin_gunleri_islemler_cakismaz():
    rng = np.random.default_rng(2)
    g = rng.normal(0.001, 0.004, 500)
    a = _aday(lambda i: g[i], range(0, 500, 2))
    getiri, oos, sec = wp.secim_ve_oos({"a": a}, PENCERELER, min_islem=5, min_gun=30)
    oos_bas, oos_bit = PENCERELER[0][2], PENCERELER[-1][3]
    assert getiri.index[0] == oos_bas.floor("D") and getiri.index[-1] == (oos_bit - pd.Timedelta(days=1))
    assert len(getiri) == (oos_bit - oos_bas).days
    ref = a.gunluk.reindex(getiri.index)
    assert np.allclose(getiri.to_numpy(), ref.to_numpy())                   # tek aday: OOS = adayın kendi günleri
    assert oos["giris_zamani"].is_unique
    for w, (_, _, t0, t1) in enumerate(PENCERELER):
        d = oos[oos["pencere"] == w]
        assert ((d.giris_zamani >= t0) & (d.giris_zamani < t1)).all()


def test_oos_metrikleri_elle():
    gun = pd.date_range("2022-01-01", periods=10, freq="D", tz="UTC")
    g = pd.Series([0.01, -0.02, 0.03, 0.0, 0.01, -0.01, 0.02, 0.0, 0.0, 0.01], index=gun)
    oos = pd.DataFrame({"giris_zamani": [gun[0], gun[2], gun[4], gun[6]], "r": [1.0, -0.5, 2.0, -1.0], "yon": [1, -1, 1, -1]})
    m = wp.oos_metrikleri(g, oos)
    assert m["islem_sayisi"] == 4 and m["profit_factor"] == pytest.approx(3.0 / 1.5)
    assert m["net_getiri"] == pytest.approx(np.prod(1 + g.to_numpy()) - 1)
    assert m["sharpe"] == pytest.approx(g.mean() / g.std(ddof=1) * math.sqrt(365))
    ozs = np.r_[1.0, np.cumprod(1 + g.to_numpy())]
    assert m["max_dusus"] == pytest.approx(((np.maximum.accumulate(ozs) - ozs) / np.maximum.accumulate(ozs)).max())
    assert m["pf_long"] == math.inf and m["pf_short"] == 0.0 and m["n_2022"] == 4 and np.isnan(m["net_2023"])
    assert m["en_iyi_yuzde5_haric_pf"] == pytest.approx(1.0 / 1.5)
    assert m["net_2022"] == pytest.approx(m["net_getiri"])


def test_karar24_metrikleri_ve_portfoy_degerlendir():
    from motor.backtest import eleme
    g = pd.Series([0.10, 0.01, -0.01, 0.02] + [0.001] * 16, index=pd.date_range("2022-01-01", periods=20, freq="D", tz="UTC"))
    m = wp.oos_metrikleri(g, pd.DataFrame(), yeniden_dengeleme=25)
    assert m["oos_gun"] == 20 and m["yeniden_dengeleme"] == 25
    kalan = np.sort(g.to_numpy())[::-1][1:]                      # 5% x 20 = 1 gün çıkar
    assert m["net_en_iyi5_gun_haric"] == pytest.approx(np.prod(1 + kalan) - 1)
    iyi = {"oos_gun": 1200, "yeniden_dengeleme": 30, "net_getiri": 0.4, "sharpe": 0.8, "max_dusus": 0.15,
           "net_en_iyi5_gun_haric": 0.1}
    assert eleme.portfoy_degerlendir({"metrikler": iyi}) == {"gecti": True, "nedenler": []}
    for anahtar, kotu, parca in [("oos_gun", 1000, "süresi"), ("yeniden_dengeleme", 19, "dengeleme"),
                                 ("net_getiri", 0.0, "net getiri"), ("sharpe", 0.49, "Sharpe"),
                                 ("max_dusus", 0.21, "düşüş"), ("net_en_iyi5_gun_haric", -0.01, "%5 gün")]:
        k = eleme.portfoy_degerlendir({"metrikler": {**iyi, anahtar: kotu}})
        assert not k["gecti"] and len(k["nedenler"]) == 1 and parca in k["nedenler"][0]
    sinir = {**iyi, "oos_gun": 1095, "yeniden_dengeleme": 20, "sharpe": 0.5, "max_dusus": 0.20}
    assert eleme.portfoy_degerlendir({"metrikler": sinir})["gecti"]          # sınır değerler geçer
    assert not eleme.portfoy_degerlendir({})["gecti"]
    assert not eleme.portfoy_degerlendir({"metrikler": {**iyi, "sharpe": float("nan")}})["gecti"]


def test_dengeleme_gunleri_secilen_pencerede_sayilir():
    gun = pd.date_range("2022-01-01", periods=10, freq="D", tz="UTC")
    a = wp.AdayHesap(pd.Series(0.01, index=gun), pd.DataFrame(), dengeleme_gunleri=[gun[1], gun[1] + pd.Timedelta(hours=5), gun[6]])
    assert a.dengeleme_sayisi(gun[0], gun[5]) == 1 and a.dengeleme_sayisi(gun[0], gun[9]) == 2


def test_al_tut_esit_agirlik_kaymali_elle():
    gun = pd.date_range("2022-01-01", periods=6, freq="D", tz="UTC", name="zaman")
    a = pd.DataFrame({"kapanis": [100, 100, 110, 121, 121, 121.0]}, index=gun)
    b = pd.DataFrame({"kapanis": [50, 50, 50, 50, 25, 25.0]}, index=gun)
    bh = wp.al_tut_getirisi({"A": a, "B": b}, ["A", "B"], gun[1], gun[5] + pd.Timedelta(days=1))
    assert bh.index[0] == gun[1] and bh.index[-1] == gun[5]
    # taban: gun[0] kapanışı; değer = ort(A/100, B/50)
    deger = np.array([1.0, 1.0, 1.1 / 2 + 0.5, 1.21 / 2 + 0.5, 1.21 / 2 + 0.25, 1.21 / 2 + 0.25])
    assert np.allclose((1 + bh).cumprod().to_numpy(), deger[1:] / deger[0])
    m = wp.al_tut_metrikleri(bh)
    assert m["bh_getiri"] == pytest.approx(deger[-1] - 1)


# ---------------------------------------------------------------------------- uçtan uca (sentetik 5m veri)
@pytest.fixture
def veri_dizini(tmp_path):
    n = 420 * 288
    idx = pd.date_range("2022-01-01", periods=n, freq="5min", tz="UTC", name="zaman")
    kok = tmp_path / "veri"
    for k, s in enumerate(KRIPTO):
        rng = np.random.default_rng(10 + k)
        kap = 100 * np.exp(np.cumsum(rng.normal(0.00001 * (k + 1), 0.0015, n)))
        ac = np.r_[kap[0], kap[:-1]]
        df = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.001, "dusuk": np.minimum(ac, kap) * 0.999,
                           "kapanis": kap, "hacim": 10.0, "quote_hacim": 1000.0, "islem_sayisi": 5}, index=idx)
        (kok / s).mkdir(parents=True)
        df.to_parquet(kok / s / "5m.parquet")
    return kok


KISA = dict(egitim_gun=150, test_gun=60, min_islem=3, min_gun=30)


def _wf(tmp_path, veri_dizini, etiket="p1", stratejiler=("pf__rotasyon",), **kw):
    kw.setdefault("surec", 1)
    kw.setdefault("izgara", False)
    return wp.wf_portfoy(etiket, list(stratejiler), "kripto", cikti_dizini=tmp_path / "wfp", veri_dizini=veri_dizini,
                         ilerleme=False, **{**KISA, **kw})


def test_uctan_uca_ciktilar_ve_deneme_kaydi(tmp_path, veri_dizini):
    df = _wf(tmp_path, veri_dizini)
    assert len(df) == 1 and df.hata.iloc[0] == "" and not df.atlandi.iloc[0]
    s = df.iloc[0]
    assert s.n_pencere >= 3 and s.n_aday >= s.n_kosu >= 1
    for kol in ("gecti", "nedenler", "profit_factor", "sharpe", "net_getiri", "max_dusus", "bh_getiri", "bh_sharpe",
                "net_2022", "bh_net_2022", "gecti_k13", "nedenler_k13", "oos_gun", "yeniden_dengeleme",
                "net_en_iyi5_gun_haric", "n_farkli_ayar", "en_sik_pay", "ort_brut", "sharpe_ustu", "limit_olay_oos"):
        assert kol in df.columns
    assert (tmp_path / "wfp" / "p1.parquet").exists() and (tmp_path / "wfp" / "p1.csv").exists()
    gun = pd.read_parquet(wp.islem_yolu(tmp_path / "wfp", "p1", "pf__rotasyon", "kripto", "1d", "gunluk"))
    assert {"oos_getiri", "bh_getiri"} <= set(gun.columns) and len(gun) == (
        pd.Timestamp(s.oos_bit) - pd.Timestamp(s.oos_bas)).days
    k = deneme_kaydi.oku()
    assert len(k) == 1 and k[0]["toplam_kosu"] == s.n_kosu and k[0]["kombinasyon_sayisi"] == s.n_aday
    assert k[0]["pencere_sayisi"] == s.n_pencere and k[0]["sembol"] == "kripto" and k[0]["aralik"] == "1d"


def test_devam_etme_cift_sayma_yok(tmp_path, veri_dizini, monkeypatch):
    _wf(tmp_path, veri_dizini)
    cagrilar = []
    gercek = wp.gorev_calistir
    monkeypatch.setattr(wp, "gorev_calistir", lambda g: cagrilar.append(g["strateji"]) or gercek(g))
    ikinci = _wf(tmp_path, veri_dizini)
    assert cagrilar == [] and len(ikinci) == 1
    assert len(deneme_kaydi.oku()) == 1
    ucuncu = _wf(tmp_path, veri_dizini, stratejiler=("pf__rotasyon", "pf__trend_sepet"))
    assert cagrilar == ["pf__trend_sepet"] and len(ucuncu) == 2
    assert [k["strateji"] for k in deneme_kaydi.oku()] == ["pf__rotasyon", "pf__trend_sepet"]


def test_kilitli_donem_girmez(tmp_path, veri_dizini, monkeypatch):
    sinir = pd.Timestamp("2022-12-01", tz="UTC")
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", sinir)
    df = _wf(tmp_path, veri_dizini)
    assert df.hata.iloc[0] == ""
    veriler, _ = wp._veri(tuple(KRIPTO), "1d")
    assert all(d.index.max() < sinir for d in veriler.values())
    assert pd.Timestamp(df.oos_bit.iloc[0]) <= sinir
    assert not kilit.KILIT_LOG.exists()
    assert "kilit_ac(" not in inspect.getsource(wp)


def test_hata_satira_yazilir_atlanan_deneme_sayilmaz(tmp_path, veri_dizini):
    df = wp.wf_portfoy("h", ["pf__rotasyon"], "kripto", semboller=["BTCUSDT", "DK_AAPL"], cikti_dizini=tmp_path / "wfp",
                       veri_dizini=veri_dizini, ilerleme=False, surec=1, izgara=False, **KISA)
    assert "FileNotFoundError" in df.hata.iloc[0] and not df.gecti.iloc[0]
    assert deneme_kaydi.oku() == []
    # tek sembollü evrende rotasyon/pairs uygun aday bulamaz -> atlandi, deneme yok
    df2 = wp.wf_portfoy("a", ["pf__pairs"], "kripto", semboller=["BTCUSDT"], cikti_dizini=tmp_path / "wfp",
                        veri_dizini=veri_dizini, ilerleme=False, surec=1, izgara=False, **KISA)
    assert bool(df2.atlandi.iloc[0]) and df2.hata.iloc[0] == "" and deneme_kaydi.oku() == []


def test_aday_listesi_evrenle_kesisir_ve_tekrarsiz():
    adaylar, atlanan = wp.aday_listesi("pf__rotasyon", KRIPTO, izgara=True)
    etiketler = [e for e, _ in adaylar]
    assert "varsayilan" in etiketler and any(e.startswith("izgara:") for e in etiketler)
    assert all(set(st.parametreler["semboller"]) <= set(KRIPTO) for _, st in adaylar)
    kimlikler = [wp._json(st.parametreler) for _, st in adaylar]
    assert len(set(kimlikler)) == len(kimlikler)
    # hisse/emtia ağırlıklı csv ayarları kripto evreninde atlanır, nedenleri yazılır
    assert atlanan and all("yok" in n or "Error" in n for _, n in atlanan)
    adaylar2, _ = wp.aday_listesi("pf__rotasyon", KRIPTO, izgara=False)
    assert len(adaylar2) < len(adaylar)
