"""D8-A (atlanan satırlardan ayrı sınıflar): lookahead, stop tarafı, ızgara, birkaç elle kural, motor dumanı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d8_atlanan_a as m
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = [
    m.FlawlessBbRsi, m.FibstPullback, m.BbPowerSqz, m.Cci2Hma, m.OrbSweepDonus, m.EmaMtfStoch, m.FibKonfluans, m.HalfTrend,
    m.OncekiGunKirilim, m.LikiditeSupurmeGun, m.StochMacdCift, m.MumDizisi, m.MaKesisimDinamik, m.OttVar, m.OttVarHizli,
    m.PmaxRsiT3, m.RfHaScalper, m.MumDizisiRsi, m.Pivot30DeltaTers, m.SqzmomLbPine, m.StochRsiCift, m.SqzmomLbKlasik,
    m.HmaSupertrend, m.StDonchianHtf, m.PivotHacimEma150, m.TrendlineFibst, m.Cci3Mfi, m.Tott, m.PivotSdBolge,
]
# Çok seyrek sinyal veren sınıflar için testte sinyal üreten gevşek ayar
GEVSEK = {"PivotHacimEma150": {"sol": 3, "sag": 3, "hacim_esik": -1000.0, "ema_n": 20}}


def veri(n=4000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="15min", baslangic="2022-01-01")


def ornekle(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.__name__, {}), **ek})


def test_kayit_ve_dogrula():
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.endswith("d8_atlanan_a")}
    assert kayitli == {c.ad for c in SINIFLAR} and len(kayitli) == 29
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri()
    s = ornekle(sinif)
    tam = s.sinyaller(df)
    assert len(tam) == len(df) and {"yon", "stop", "hedef", "cikis"} <= set(tam.columns)
    for k in (len(df) // 4, len(df) // 2, int(len(df) * 0.8)):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_izgara(sinif):
    df = veri()
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27 and set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    sig = ornekle(sinif).sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 0 and giris.stop.notna().all()
    kap = df.kapanis
    l, s = giris[giris.yon == 1], giris[giris.yon == -1]
    assert (l.stop < kap[l.index]).all() and (s.stop > kap[s.index]).all()
    assert sinif().cikis_var_mi()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(2500)
    assert len(backtest(df, ornekle(sinif), MotorAyarlari()).ozsermaye) == len(df)


def test_mum_dizisi_kurali_elle():
    kap = np.r_[np.full(10, 100.0), [98.0], [99.0, 100.0, 101.0], np.full(5, 101.0)]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="15min")
    df.iloc[10, df.columns.get_loc("dusuk")] = 97.0           # ana mumun dibi
    sig = m.MumDizisi(n=3).sinyaller(df)
    assert sig.yon.iloc[13] == 1 and sig.yon.iloc[:13].eq(0).all()
    assert sig.stop.iloc[13] == pytest.approx(97.0)
    assert sig.hedef.iloc[13] == pytest.approx(101.0 + 1.5 * 4.0)
    assert (m.MumDizisi(n=3).sinyaller(df).yon == -1).sum() == 0        # short kapalı


def test_orb_supurme_donus_elle():
    kap = np.full(80, 100.0)
    df = mumlar_kapanistan(kap, genlik=1.0, baslangic="2022-01-04 14:30", freq="5min")   # 08:30 Chicago (kış)
    i = 14                                                                                 # 15:40 UTC = 09:40 Chicago
    df.iloc[i, df.columns.get_loc("yuksek")] = 103.0
    df.iloc[i, df.columns.get_loc("kapanis")] = 100.5
    sig = m.OrbSweepDonus().sinyaller(df)
    assert sig.yon.iloc[i] == -1 and (sig.yon.drop(df.index[i]) == 0).all()
    assert sig.stop.iloc[i] == pytest.approx(100.5 + 2.0) and sig.hedef.iloc[i] == pytest.approx(100.5 - 4.0)
    assert sig.cikis.any()                                                                 # pencere sonu çıkışı


def test_likidite_asya_supurmesi_elle():
    kap = np.full(80, 100.0)
    df = mumlar_kapanistan(kap, genlik=0.5, baslangic="2022-01-04 00:00", freq="1h")
    i = 33                                                                                 # 2022-01-05 09:00 UTC
    df.iloc[i, df.columns.get_loc("dusuk")] = 98.5
    s = m.LikiditeSupurmeGun(londra=False, onceki_gun=False, swing=False)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[i] == 1 and (sig.yon.drop(df.index[i]) == 0).all()
    assert sig.stop.iloc[i] < 98.5
    r = 100.0 - sig.stop.iloc[i]
    assert sig.hedef.iloc[i] == pytest.approx(100.0 + 3.0 * r)


def test_halftrend_yon_degisimi():
    rng = np.random.default_rng(3)
    kap = 100 * np.exp(np.cumsum(np.r_[np.full(300, 0.003), np.full(300, -0.003)] + rng.normal(0, 0.001, 600)))
    df = mumlar_kapanistan(kap, genlik=0.2, freq="15min")
    sig = m.HalfTrend().sinyaller(df)
    assert (sig.yon.iloc[:300] != 0).sum() == 0              # yükseliş boyunca ters sinyal yok
    assert (sig.yon.iloc[295:330] == -1).any()              # zirveden sonra short sinyali oluşur
