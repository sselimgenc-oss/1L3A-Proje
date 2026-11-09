"""D10-B (kuyruk yeni_aile, b payı) stratejileri: sözleşme/ızgara, lookahead (üç kesit), stop tarafı, sinyal üretimi, motor dumanı,
kural özel testleri (haftalık hizalama, Paskalya, swing aşımı, trend çizgisi retest, R1 sanal mod, ADX/DI takvimi)."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d10b_kitap as mod
from motor.strateji.dis._gosterge_d10b import (
    adl, gun_ust, haftalik_ust, ibs, obv, paskalya_kalan_gun, pivot_noktalari, verimlilik_orani)
from motor.strateji.temel import Strateji
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
SAATLIK = {"dis__lrc-wma-kesisim", "dis__swing-asim-mesafesi", "dis__trend-cizgisi-kirilim-retest",
           "dis__ust-tf-trend-60dk-donus"}
OTUZ_DK = {"dis__adx-di-esik-kesisimi"}
# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__lrc-wma-kesisim": dict(adx_esik=5.0, bbw_esik=0.12, rsi_alt=65.0),
    "dis__ust-tf-trend-60dk-donus": dict(faktor_min=2, destek_atr=10.0, hacim_k=0.0, bb_gerisi=1, pivot_n=3),
    "dis__trend-cizgisi-kirilim-retest": dict(pivot_n=3, guclu_oran=0.3, tol_atr=1.0, bekle=40),
    "dis__swing-asim-mesafesi": dict(esik_atr=6.0),
    "dis__adx-di-esik-kesisimi": dict(adx_esik=10.0, di_esik=20.0),
    "dis__codex-wd-hacim-akisi": dict(cmf_n=10, adl_n=5),
    "dis__codex-wd-kama-verimlilik": dict(er_giris=0.1),
}


def tf_of(sinif):
    return "1h" if sinif.ad in SAATLIK else ("30min" if sinif.ad in OTUZ_DK else "1D")


def veri(sinif, n=None, seed=11):
    n = n or {"1D": 3000, "1h": 6000, "30min": 6000}[tf_of(sinif)]
    return rastgele_mumlar(n, seed=seed, freq=tf_of(sinif), baslangic="2018-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    p = sinif.varsayilan_parametreler
    if "short" in p:
        return {"short": True}
    if "yonler" in p and p["yonler"] != "short":
        return {"yonler": "ls"}
    return {}


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) == 17
    assert len(set(ADLAR)) == len(ADLAR)
    assert all(a.startswith("dis__") for a in ADLAR)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    ca = s.cikis_ayarlari
    assert (s.cikis_var_mi() or ca.atr_iz_suren_k or ca.zaman_cikisi_mum or ca.sabit_r_hedefi) and s.stil in ("scalp", "daytrade", "swing")
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(sinif, n=1800)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


# ---------------------------------------------------------------- lookahead / stop tarafı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif, n=2500 if tf_of(sinif) != "1D" else 2000)
    for s in (olustur(sinif), olustur(sinif, **kisa_ek(sinif))):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_bari_degistirmek_gecmisi_degistirmez(sinif):
    df = veri(sinif, n=2500 if tf_of(sinif) != "1D" else 2000)
    s = olustur(sinif, **kisa_ek(sinif))
    tam = s.sinyaller(df)
    k = len(df) // 2
    df2 = df.copy()
    for kol in ("acilis", "yuksek", "dusuk", "kapanis"):
        df2.iloc[k:, df2.columns.get_loc(kol)] = df2[kol].iloc[k:] * 1.37
    df2.iloc[k:, df2.columns.get_loc("hacim")] = df2["hacim"].iloc[k:] * 3.0
    pdt.assert_frame_equal(s.sinyaller(df2).iloc[:k], tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    sig = olustur(sinif, **kisa_ek(sinif)).sinyaller(df)
    giris = sig[sig.yon != 0]
    if sinif.ad == "dis__paskalya-takvim":
        assert len(giris) >= 3                       # 3000 günde ~8 Paskalya
    else:
        assert len(giris) > 0, f"{sinif.ad}: sinyal yok"
    assert giris.stop.notna().all()
    kap = df.kapanis
    l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
    assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
    h = giris.hedef.dropna()
    if len(h):
        yl = giris.loc[h.index]
        assert ((yl.yon == 1) & (h > kap[h.index]) | (yl.yon == -1) & (h < kap[h.index])).all()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(sinif, n=1800)
    sonuc = backtest(df, olustur(sinif, **kisa_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


def test_kayit_dogrula_kendi_siniflarimiz():
    sorun = [s for s in kayit.dogrula() if any(a in s for a in ADLAR)]
    assert sorun == []


# ---------------------------------------------------------------- göstergeler
def test_gostergeler_nedensel():
    r = np.random.default_rng(4)
    df = rastgele_mumlar(900, seed=4, freq="1D")
    for f in (lambda d: adl(d), lambda d: obv(d), lambda d: ibs(d), lambda d: verimlilik_orani(d["kapanis"], 10)):
        tam = f(df).iloc[:500]
        kisa = f(df.iloc[:500])
        # ADL / OBV kümülatif: düzey aynı (aynı başlangıç) -> eşit
        pdt.assert_series_equal(kisa, tam, check_names=False)
    assert 0.0 <= verimlilik_orani(df["kapanis"], 10).dropna().min() and verimlilik_orani(df["kapanis"], 10).dropna().max() <= 1.0 + 1e-9
    x = ibs(df).dropna()
    assert (x >= 0).all() and (x <= 1).all()
    del r


def test_pivot_onay_gecikmesi():
    y = pd.Series([1, 2, 3, 9, 4, 3, 2, 1, 1, 1], dtype=float)
    s = pivot_noktalari(y, 2, True)
    assert s.iloc[:5].isna().all() and s.iloc[5] == 9.0       # indeks 3 pivotu ancak indeks 5'te görünür


def test_haftalik_ust_5_gunluk_veride_calisir_ve_hizalanir():
    # yalnız iş günleri (hisse): htf.ust_zaman bunları "eksik" atardı
    idx = pd.bdate_range("2023-01-02", periods=60, tz="UTC")
    df = pd.DataFrame({"acilis": 1.0, "yuksek": 2.0, "dusuk": 0.5, "kapanis": np.arange(60) + 1.0, "hacim": 1.0}, index=idx)
    h = haftalik_ust(df, lambda w: pd.DataFrame({"k": w["kapanis"]}))["k"]
    # 1. hafta (Pzt 2 Oca - Cum 6 Oca), son kapanış = 5.0; değer 9 Oca (Pzt) 00:00'dan itibaren
    assert h.loc["2023-01-06"] != h.loc["2023-01-06"]                      # henüz yok (NaN)
    assert h.loc["2023-01-09"] == 5.0 and h.loc["2023-01-13"] == 5.0       # tüm 2. hafta boyunca 1. hafta
    assert h.loc["2023-01-16"] == 10.0
    g = gun_ust(df, lambda u: pd.DataFrame({"k": u["kapanis"]}))["k"]
    assert g.loc["2023-01-03"] == 1.0


# ---------------------------------------------------------------- kural özel testleri
def test_paskalya_gunleri_ve_sinyal():
    gunler = pd.DatetimeIndex(["2024-03-27", "2024-03-28", "2024-03-31", "2024-03-22"], tz="UTC")   # Paskalya 2024-03-31
    assert paskalya_kalan_gun(gunler).tolist() == [4, 3, 0, 9]
    df = rastgele_mumlar(1500, seed=2, freq="1D", baslangic="2022-01-01")
    for mod_, kalan in (("sprint", 4), ("hafta", 9)):
        sig = mod.PaskalyaTakvim(mod=mod_).sinyaller(df)
        g = sig.index[sig.yon == 1]
        assert len(g) >= 3
        assert (paskalya_kalan_gun(g) == kalan).all()
    c = mod.PaskalyaTakvim().kosullar(df)["cikis_long"]
    assert (c.index[c] >= pd.Timestamp("2022-01-01", tz="UTC")).all() and (paskalya_kalan_gun(c.index[c]) <= 3).all()


def test_adx_di_yalniz_pzt_car_ve_persembe_cikis():
    df = rastgele_mumlar(6000, seed=11, freq="30min", baslangic="2018-01-01")
    s = mod.AdxDiEsikKesisimi(adx_esik=10.0, di_esik=20.0)
    sig = s.sinyaller(df)
    g = sig.index[sig.yon == 1]
    assert len(g) > 0 and (g.dayofweek <= 2).all()
    k = s.kosullar(df)["cikis_long"]
    assert (k[(df.index.dayofweek == 3) & (df.index.hour >= 16)]).all() and not k[df.index.dayofweek == 1].any()
    # yüzde stop / hedef: stop %4,5 altı, hedef %1,5 üstü
    r = sig[sig.yon == 1]
    assert np.allclose(r.stop, df.kapanis[r.index] * 0.955) and np.allclose(r.hedef, df.kapanis[r.index] * 1.015)


def _asim_veri(ters=False):
    kap = np.r_[100 + np.arange(30) * 0.001, np.linspace(100, 90, 15), np.linspace(90, 96, 8), np.linspace(96, 89.7, 8),
                np.linspace(89.7, 91, 4), np.linspace(91, 98, 8), 98 + np.arange(10) * 0.001]
    if ters:
        kap = 200.0 - kap
    return mumlar_kapanistan(kap, genlik=0.05, freq="1h")


def test_swing_asim_kucuk_asim_dipten_long_ve_buyuk_asim_kurulum_yok():
    df = _asim_veri()
    sig = mod.SwingAsimMesafesi(pivot_n=3, esik_atr=1.0, bolge_atr=3.0, onay="tepe", bekle=40, short=False).sinyaller(df)
    g = sig[sig.yon == 1]
    assert len(g) == 1 and g.stop.iloc[0] < 89.7 and g.hedef.iloc[0] > df.kapanis[g.index[0]]
    # aşım eşiğin (0.1 ATR) üstünde -> trend devamı sayılır, dönüş kurulumu açılmaz
    assert (mod.SwingAsimMesafesi(pivot_n=3, esik_atr=0.1, bolge_atr=3.0, onay="tepe", short=False).sinyaller(df).yon == 1).sum() == 0
    # ayna: short
    ters = mod.SwingAsimMesafesi(pivot_n=3, esik_atr=1.0, bolge_atr=3.0, onay="tepe", bekle=40).sinyaller(_asim_veri(True))
    assert (ters.yon == -1).sum() == 1 and (ters.yon == 1).sum() == 0


def _trend_veri(ters=False):
    kap = np.r_[np.full(3, 80.0), np.linspace(80, 100, 8), np.linspace(100, 90, 8), np.linspace(90, 95, 8), np.linspace(95, 88, 8),
                np.linspace(88, 90, 8), np.linspace(90, 84, 8), [93.0, 88.0, 93.5, 94.5, 95.5, 96.5]]
    if ters:
        kap = 200.0 - kap
    return mumlar_kapanistan(kap, genlik=0.1, freq="4h")


def test_trend_cizgisi_kirilim_retest_sentetik_ve_ayna():
    s = mod.TrendCizgisiKirilimRetest(pivot_n=2, tol_atr=1.5, guclu_oran=0.6)
    sig = s.sinyaller(_trend_veri())
    g = sig[sig.yon == 1]
    assert len(g) == 1 and (g.stop < 88.5).all()           # stop yutan mumun dibinin altında
    assert (sig.yon == -1).sum() == 0
    ters = s.sinyaller(_trend_veri(True))
    assert (ters.yon == -1).sum() == 1 and (ters.yon == 1).sum() == 0
    # retest şartı: yutan mum yoksa (kırılımdan sonra düz yükseliş) sinyal yok
    kap = np.r_[np.full(3, 80.0), np.linspace(80, 100, 8), np.linspace(100, 90, 8), np.linspace(90, 95, 8), np.linspace(95, 88, 8),
                np.linspace(88, 90, 8), np.linspace(90, 84, 8), [93.0, 94, 95, 96, 97, 98, 99]]
    assert (s.sinyaller(mumlar_kapanistan(kap, genlik=0.1, freq="4h")).yon != 0).sum() == 0
    # güçlü mum tanımı: gövde iki fitilden de küçükse hiç kırılım sinyali yok
    d = _trend_veri().copy()
    d["acilis"] = d["kapanis"] - 0.001
    d["yuksek"] = d["kapanis"] + 3.0
    d["dusuk"] = d["kapanis"] - 3.0
    assert (s.sinyaller(d).yon != 0).sum() == 0


def test_r1_sanal_mod_a_ve_b_cikislari_ayri():
    s = mod.VoltranR1()
    n = 12
    m = pd.DataFrame({"yuksek": np.full(n, 11.0), "dusuk": np.full(n, 9.0)}, index=pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC"))
    a = np.zeros(n, bool)
    b = np.zeros(n, bool)
    ca = np.zeros(n, bool)
    cb = np.zeros(n, bool)
    a[1] = True
    b[6] = True
    ca[3] = True       # A çıkışı: A pozisyonunu kapatır
    ca[8] = True       # A çıkışı: B pozisyonunu KAPATMAZ
    cb[10] = True      # B çıkışı
    stop = np.full(n, 5.0)
    mod_once = s._sanal_mod(m, a, b, ca, cb, stop, np.full(n, 1.0))
    assert mod_once.tolist() == [0, 0, 1, 1, 0, 0, 0, 2, 2, 2, 2, 0]


def test_codex_haftalik_rejim_yoksa_giris_yok():
    # sürekli düşen fiyat: haftalık rejim hiç oluşmaz -> giriş yok
    kap = np.linspace(200, 50, 600)
    df = mumlar_kapanistan(kap, genlik=0.2, freq="1D", baslangic="2020-01-01")
    for s in (mod.CodexWdCiftMomentum(), mod.CodexWdGunlukMomentum(), mod.CodexWdKamaVerimlilik()):
        assert (s.sinyaller(df).yon != 0).sum() == 0
    # sürekli yükselen fiyat: rejim açık, momentum girişi var
    up = mumlar_kapanistan(np.linspace(50, 400, 600), genlik=0.2, freq="1D", baslangic="2020-01-01")
    assert (mod.CodexWdGunlukMomentum().sinyaller(up).yon == 1).sum() > 0


def test_codex_gunluk_donus_zaman_cikisi():
    df = rastgele_mumlar(3000, seed=11, freq="1D", baslangic="2018-01-01")
    sig = mod.CodexWdGunlukDonus(bb_k=1.0, rsi_alt=40.0).sinyaller(df)
    g = sig[sig.yon == 1]
    assert len(g) > 0 and (sig.loc[g.index, "zaman_cikisi_mum"] == 10).all()


def test_voltran_1a_stop_3atr():
    df = rastgele_mumlar(3000, seed=11, freq="1D", baslangic="2018-01-01")
    from motor.strateji import gostergeler as g_
    sig = mod.Voltran1a(adx_esik=5.0, hacim_k=0.0).sinyaller(df)
    r = sig[sig.yon == 1]
    atr = g_.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    assert len(r) > 0 and np.allclose(df.kapanis[r.index] - r.stop, 3.0 * atr[r.index])
