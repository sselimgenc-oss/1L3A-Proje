"""D11-f (GitHub kaynaklı swing aileleri): sözleşme/ızgara, lookahead (prefix kesitleri), stop tarafı, sinyal üretimi, motor dumanı,
gösterge ve kurala özel testler."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d11f_github as mod
from motor.strateji.dis._gosterge_d11f import alma, ay_uygunluk, poli_tahmin, rsrs_egim, w_deseni
from motor.strateji.temel import Strateji
from testler.test_daytrade import rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]

# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__ma-kumelenme-kirilimi": dict(max_yayilim=0.2, choppiness_max=0.0, atr_yuzdelik_max=1.0, kume_pencere=5),
    "dis__stockbee-momentum-burst": dict(burst=0.01, taban_genislik=1.0, ort_aralik=1.0, taban_n=3),
    "dis__vcp-daralma-kirilimi": dict(daralma=1.5, trend_n=50, zirve_n=30),
    "dis__momentum-roc-filtreli": dict(mod="momentum"),
    "dis__haftalik-key-reversal": dict(pencere=3),
    "dis__ay-mevsimsellik": dict(min_ornek=2, min_ort=-1.0, min_kazanma=0.0),
    "dis__haftalik-macd-gunluk-ma": dict(giris_mod="gecerlilik"),
    "dis__uclu-rsi": dict(uzun_esik=40.0, orta_esik=90.0, kisa_esik=40.0, yukselis=0.0, min_bekleme=5),
    "dis__eski-tepe-asma": dict(geri_cekilme=0.01, yakin=0.1),
    "dis__polinom-regresyon-trend": dict(pencere=60, derece=3),
    "dis__cok-macd-geri-cekilme": dict(mod="2macdsto"),
}
EK_MOD = {"dis__cok-macd-geri-cekilme": dict(mod="3macd"), "dis__vcp-daralma-kirilimi": dict(mod="risk_averse"),
          "dis__momentum-roc-filtreli": dict(mod="roc_ma"), "dis__ama-egri-donus-filtresi": dict(mod="dip"),
          "dis__rsrs-egim-esigi": dict(mod="z"), "dis__stockbee-momentum-burst": dict(mod="atr")}


def veri(n=3000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="1D", baslangic="2014-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def ls_ek(sinif):
    return {"yonler": "ls"} if "yonler" in sinif.varsayilan_parametreler else {}


def test_ad_ve_sayi():
    assert len(SINIFLAR) == 19
    assert len(set(ADLAR)) == len(ADLAR) and all(a.startswith("dis__") for a in ADLAR)
    assert kayit.dogrula() == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara(sinif):
    s = sinif()
    assert s.cikis_var_mi() and s.stil == "swing"
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(1500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


def _varyantlar(sinif):
    yield olustur(sinif)
    yield olustur(sinif, **ls_ek(sinif))
    if sinif.ad in EK_MOD:
        yield olustur(sinif, **{**ls_ek(sinif), **EK_MOD[sinif.ad]})


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(2400)
    for s in _varyantlar(sinif):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_bari_degisince_gecmis_sinyal_ayni(sinif):
    df = veri(2400)
    s = olustur(sinif, **ls_ek(sinif))
    tam = s.sinyaller(df)
    df2 = df.copy()
    kes = 1800
    df2.iloc[kes:, :4] = df2.iloc[kes:, :4] * 1.37
    pdt.assert_frame_equal(s.sinyaller(df2).iloc[:kes - 10], tam.iloc[:kes - 10])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri()
    for s in _varyantlar(sinif):
        sig = s.sinyaller(df)
        giris = sig[sig.yon != 0]
        assert len(giris) > 0, f"{sinif.ad} {s.parametreler}: sinyal yok"
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
    df = veri(1800)
    sonuc = backtest(df, olustur(sinif, **ls_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ------------------------------------------------------------------ göstergeler / kurala özel
def test_alma_sabit_seride_sabit_ve_nedensel():
    x = pd.Series(np.full(50, 7.0))
    assert np.allclose(alma(x, 9).dropna(), 7.0) and alma(x, 9).iloc[:8].isna().all()
    r = pd.Series(np.random.default_rng(1).normal(100, 3, 300))
    pdt.assert_series_equal(alma(r.iloc[:200], 9), alma(r, 9).iloc[:200])


def test_poli_tahmin_kubik_seride_tam():
    t = np.arange(120, dtype=float)
    seri = pd.Series(0.001 * t ** 3 - 0.05 * t ** 2 + 2 * t + 50)
    tahmin = poli_tahmin(seri, 60, 3)
    gercek = seri.shift(-1)
    assert np.allclose(tahmin.dropna().iloc[:-1], gercek.loc[tahmin.dropna().index[:-1]], rtol=1e-6)
    r = pd.Series(np.random.default_rng(2).normal(100, 3, 300))
    pdt.assert_series_equal(poli_tahmin(r.iloc[:200], 60, 3), poli_tahmin(r, 60, 3).iloc[:200])


def test_rsrs_egim_dogrusal():
    d = pd.Series(np.linspace(10, 20, 60))
    y = 1.5 * d + 2.0
    assert np.allclose(rsrs_egim(y, d, 20).dropna(), 1.5)


def test_w_deseni_elle():
    # negatif dilimde iki dip: -10 ve -9 (daha sığ), aralarında -4'e sıçrama -> W; 2. dip sonrası ilk yükselişte onay
    h = pd.Series([-1, -5, -10, -6, -4, -7, -9, -8, -3, 2.0])
    w = w_deseni(h, tol=0.2, min_sicrama=0.25)
    assert w.iloc[7] and w.sum() == 1          # dip 6. mum (-9), onay 7. mumda (h[7] > h[6])
    # ikinci dip çok daha derin -> W değil
    h2 = pd.Series([-1, -5, -10, -6, -4, -7, -20, -8, -3, 2.0])
    assert w_deseni(h2, tol=0.2, min_sicrama=0.25).sum() == 0
    # sıfır geçişi arada olursa iki ayrı dilim -> W değil
    h3 = pd.Series([-1, -5, -10, -6, 3, 4, -7, -9, -8, -3.0])
    assert w_deseni(h3, tol=0.2, min_sicrama=0.25).sum() == 0


def test_ay_uygunluk_yalniz_gecmis_yillar():
    idx = pd.date_range("2015-01-01", "2023-12-31", freq="D", tz="UTC")
    kap = pd.Series(100.0, index=idx)
    # her Mart ayı +10% (ay sonu kapanış yükselir), diğer aylar sabit
    ay = idx.tz_localize(None).to_period("M")
    seviye = 100.0
    vals = []
    for p in pd.unique(ay):
        if p.month == 3:
            seviye *= 1.10
        vals.append(seviye)
    esl = dict(zip(pd.unique(ay), vals))
    kap = pd.Series([esl[p] for p in ay], index=idx)
    t = ay_uygunluk(kap, 6, 0.025, 0.6)
    mart = t[(t.index.month == 3) & t.yeni_ay]
    assert not mart["uygun"].loc[mart.index.year <= 2020].any()       # 6 önceki yıl yok
    assert mart["uygun"].loc[mart.index.year >= 2021].all()
    assert not t[(t.index.month == 5) & t.yeni_ay]["uygun"].any()
    # gelecek veri değişince geçmiş değişmez
    kap2 = kap.copy()
    kap2.loc["2023-03-01":] *= 0.5
    t2 = ay_uygunluk(kap2, 6, 0.025, 0.6)
    pdt.assert_frame_equal(t.loc[:"2023-02-28"], t2.loc[:"2023-02-28"])


def test_onceki_mum_ekstrem_kurali():
    kap = [100, 100, 98, 101, 102, 103, 104.0]
    ac = [100, 100, 100, 98, 101, 102, 103.0]
    df = pd.DataFrame({"acilis": ac, "yuksek": np.array(kap) + 0.5, "dusuk": np.array(kap) - 0.5, "kapanis": kap, "hacim": 1.0},
                      index=pd.date_range("2022-01-01", periods=7, freq="D", tz="UTC"))
    df.loc[df.index[2], "dusuk"] = 97.0        # 98 kapanışı, önceki dip 99.5'in altında
    s = mod.OncekiMumEkstremKapanis(stop_atr_k=0.5, tut_long=3, atr_periyot=2)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[2] == 1 and sig.zaman_cikisi_mum.iloc[2] == 3


def test_carstens_pazartesi_sinyal_gunu():
    df = veri(800)
    sig = olustur(mod.CarstensPazartesi, aralik_k=5.0).sinyaller(df)
    gunler = df.index[sig.yon != 0].dayofweek
    assert len(gunler) > 0 and (gunler == 4).all()
