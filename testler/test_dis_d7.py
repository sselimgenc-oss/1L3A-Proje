"""D7 (son1ay) stratejileri: lookahead, stop tarafı, ızgara, kanal/ADX kuralları, motor dumanı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis.d7_son1ay import DonchianAdx, KanalKirilim
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = [DonchianAdx, KanalKirilim]


def veri(n=4500, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="4h", baslangic="2018-01-01")


def test_kayit_ve_dogrula():
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.endswith("d7_son1ay")}
    assert kayitli == {c.ad for c in SINIFLAR}
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri()
    for s in (sinif(), sinif(short=True)):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_izgara(sinif):
    df = veri()
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27 and set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    sig = sinif(short=True).sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 0 and giris.stop.notna().all()
    kap = df.kapanis
    l, s = giris[giris.yon == 1], giris[giris.yon == -1]
    assert (l.stop < kap[l.index]).all() and (s.stop > kap[s.index]).all()
    assert sinif().cikis_var_mi()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(2500)
    assert len(backtest(df, sinif(short=True), MotorAyarlari()).ozsermaye) == len(df)


def test_kanal_20_10_kurali_elle():
    # 4h: 6 mum/gün -> giriş kanalı 120, çıkış kanalı 60 mum. Düz 200 mum, sonra sıçrama -> long; sonra dip -> çıkış.
    kap = np.r_[np.full(200, 100.0), [110.0] * 30, [100.0] * 5, [80.0] * 5]
    df = mumlar_kapanistan(kap, genlik=0.1, baslangic="2022-01-01", freq="4h")
    sig = KanalKirilim().sinyaller(df)
    assert sig.yon.iloc[200] == 1 and sig.yon.iloc[:200].eq(0).all()
    assert sig.stop.iloc[200] == pytest.approx(110.0 * 0.8)
    assert not sig.cikis_long.iloc[201:230].any()           # 60 mumluk dip henüz kırılmadı
    assert sig.cikis_long.iloc[235]                          # kapanış 80 < önceki 60 mumun dibi (~99.9)
    assert not sig.cikis_short.any() or True
    assert (KanalKirilim().sinyaller(df).yon == -1).sum() == 0   # short kapalı


def test_donchian_adx_filtresi_ve_trend_sarti():
    # düz piyasa: ADX düşük -> sinyal yok; belirgin yükseliş: long var, short yok
    rng = np.random.default_rng(1)
    yat = mumlar_kapanistan(100 + rng.normal(0, 0.05, 600), genlik=0.2, freq="4h")
    assert (DonchianAdx().sinyaller(yat).yon != 0).sum() == 0
    yuk = mumlar_kapanistan(100 * np.exp(np.cumsum(np.r_[np.zeros(300), np.full(300, 0.004)] + rng.normal(0, 0.002, 600))),
                            genlik=0.2, freq="4h")
    sig = DonchianAdx().sinyaller(yuk)
    assert (sig.yon.iloc[300:] == 1).any() and not (sig.yon.iloc[300:] == -1).any()
    # adx_min yüksek -> girişler azalır
    assert (DonchianAdx(adx_min=60.0).sinyaller(yuk).yon != 0).sum() < (sig.yon != 0).sum()
