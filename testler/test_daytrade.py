"""Day trade stratejileri: lookahead, gün sonu çıkışı, sentetik senaryo, stop tarafı, seviyelerin kaynağı."""
import itertools

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import onceki_seans_hlc, seans_kimligi, seans_son_mumu
from motor.strateji.daytrade.bb_sikisma_kirilim import BbSikismaKirilim
from motor.strateji.daytrade.konsolidasyon_kirilim import KonsolidasyonKirilim
from motor.strateji.daytrade.kirilim_geri_test import KirilimGeriTest
from motor.strateji.daytrade.orb import Orb
from motor.strateji.daytrade.pivot_seviye import PivotSeviye
from motor.strateji.daytrade.vwap_donus import VwapDonus


def rastgele_mumlar(n=1500, seed=5, freq="1h", baslangic="2022-01-01"):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range(baslangic, periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def mumlar_kapanistan(kap, genlik=0.5, hacim=1.0, baslangic="2022-01-01", freq="1h"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range(baslangic, periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hacim}, index=idx)


STRATEJILER = [
    PivotSeviye(), PivotSeviye(mod="kirilim"), PivotSeviye(seviyeler="p_s1_s2", cpr_filtre="uygun", hedef_modu="r"),
    KonsolidasyonKirilim(), KonsolidasyonKirilim(uzunluk=8, hacim_k=0.0, tampon_atr=0.0, trend_ema=0),
    KirilimGeriTest(), KirilimGeriTest(uzunluk=12, pencere=4, hedef_r=3.0),
    BbSikismaKirilim(), BbSikismaKirilim(stop_modu="kutu", sikisma_yuzdelik=20.0, hedef_r=0.0, hacim_k=1.0),
    VwapDonus(), VwapDonus(bant_k=1.5, hedef_tipi="karsi_bant", rsi_esik=35.0),
    Orb(), Orb(aralik_dk=120, stop_modu="atr", hedef_r=1.0), Orb(stop_modu="orta", ust_yari_filtre=False, gunde_tek=False),
    Orb(seans_saat=13.5, aralik_dk=60),
]


def _id(s):
    return f"{s.ad.split('__')[1]}-{abs(hash(str(s.parametreler))) % 997}"


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_lookahead_yok(s):
    df = rastgele_mumlar()
    tam = s.sinyaller(df)
    for n in (150, 301, 555, 777, 1001, 1233):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_lookahead_30dk(s):
    df = rastgele_mumlar(n=1800, seed=8, freq="30min")
    tam = s.sinyaller(df)
    for n in (211, 640, 1111):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_stop_dogru_tarafta_ve_cikis(s):
    df = rastgele_mumlar(3000, seed=3)
    sig = s.sinyaller(df)
    assert s.stil == "daytrade" and s.ad.startswith("daytrade__") and s.cikis_var_mi() is True
    assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    gir = sig[sig.yon != 0]
    assert len(gir) > 0 and gir.stop.notna().all()
    kap = df.kapanis[gir.index]
    assert (gir.stop[gir.yon == 1] < kap[gir.yon == 1]).all()
    assert (gir.stop[gir.yon == -1] > kap[gir.yon == -1]).all()
    h = gir.hedef.dropna()
    assert (h[gir.yon[h.index] == 1] > kap[h.index][gir.yon[h.index] == 1]).all()
    assert (h[gir.yon[h.index] == -1] < kap[h.index][gir.yon[h.index] == -1]).all()
    assert (gir.yon == 1).any() or (gir.yon == -1).any()


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_gun_sonu_cikisi(s):
    df = rastgele_mumlar(1500, seed=9)
    sig = s.sinyaller(df)
    saat = s.parametreler["seans_saat"]
    seans = pd.Series(seans_kimligi(df.index, saat), index=df.index)
    # her tam seansın SON mumunda cikis=True ve yeni giriş yok
    son = seans.ne(seans.shift(-1)) & (seans.shift(-1).notna())
    assert son.sum() > 30
    assert sig.cikis[son].all()
    assert (sig.yon[son] == 0).all()
    # ilk mum dışında son-mum olmayan satırların çoğunda gün sonu cikis'ı yok (cikis yalnız gün sonu değil)
    assert not sig.cikis.iloc[1:][~son.iloc[1:]].all()


def test_gun_sonu_ozel_seans_saati():
    idx = pd.date_range("2022-03-01 00:00", periods=60, freq="1h", tz="UTC")
    son = seans_son_mumu(idx, 13.5)
    # 13:30 seansı: 12:00 mumu (12-13) bitişi 13:00 -> hâlâ önceki seans; 13:00 mumu (13-14) 13:30'u kapsar
    # (kapanış 14:00 > 13:30) yani son mum 13:00 mumudur.
    assert [t.hour for t in idx[son]] == [13, 13]
    son0 = seans_son_mumu(idx, 0.0)
    assert [t.hour for t in idx[son0]] == [23, 23]


def test_parametre_izgarasi_sinirli():
    for s in STRATEJILER:
        assert 1 <= np.prod([len(v) for v in s.parametre_izgarasi.values()]) <= 27
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)
        for kombinasyon in itertools.islice(itertools.product(*s.parametre_izgarasi.values()), 3):
            s.yeni(**dict(zip(s.parametre_izgarasi, kombinasyon)))


def test_short_kapatilabilir():
    df = rastgele_mumlar(3000, seed=3)
    for s in (PivotSeviye(short=False), KirilimGeriTest(short=False), BbSikismaKirilim(short=False),
              VwapDonus(short=False), Orb(short=False), KonsolidasyonKirilim(short=False, hacim_k=0.0)):
        assert (s.sinyaller(df).yon >= 0).all()


# ---------------------------------------------------------------- pivot / VWAP kaynağı

def test_pivot_yalniz_onceki_seanstan():
    df = rastgele_mumlar(24 * 6, seed=2)
    seans = seans_kimligi(df.index)
    h1 = onceki_seans_hlc(df, seans)
    # 2. günün satırları 1. günün H/L/C'sine eşit
    gun1 = df.iloc[:24]
    gun2 = h1.iloc[24:48]
    assert (gun2["h"] == gun1.yuksek.max()).all() and (gun2["l"] == gun1.dusuk.min()).all()
    assert (gun2["c"] == gun1.kapanis.iloc[-1]).all()
    assert h1.iloc[:24].isna().all().all()
    # bugünün verisini değiştirmek bugünün seviyelerini değiştirmez
    df2 = df.copy()
    df2.iloc[48:60, df2.columns.get_loc("yuksek")] *= 3
    h2 = onceki_seans_hlc(df2, seans_kimligi(df2.index))
    pdt.assert_frame_equal(h1.iloc[48:60], h2.iloc[48:60])


def test_vwap_seans_sifirlanir_ve_nedensel():
    df = rastgele_mumlar(24 * 4, seed=4)
    seans = seans_kimligi(df.index)
    v = g.vwap_seans(df.yuksek, df.dusuk, df.kapanis, df.hacim, seans)
    tp = (df.yuksek + df.dusuk + df.kapanis) / 3
    for gun in range(4):
        sl = slice(gun * 24, (gun + 1) * 24)
        beklenen = (tp.iloc[sl] * df.hacim.iloc[sl]).cumsum() / df.hacim.iloc[sl].cumsum()
        np.testing.assert_allclose(v["vwap"].iloc[sl], beklenen)
    assert v["vwap"].iloc[24] == pytest.approx(tp.iloc[24])      # yeni seansın ilk mumu: yalnız kendisi
    kesik = g.vwap_seans(df.yuksek.iloc[:50], df.dusuk.iloc[:50], df.kapanis.iloc[:50], df.hacim.iloc[:50], seans[:50])
    pdt.assert_frame_equal(kesik, v.iloc[:50])


# ---------------------------------------------------------------- sentetik senaryolar

def test_pivot_tepki_s1_long():
    # 1. gün: H=110 L=90 C=100 -> P=100, S1=90, R1=110. 2. gün: fiyat 95 civarı, S1'e iner, yükseliş mumuyla döner.
    g1 = [100.0] * 24
    df = mumlar_kapanistan(g1 + [100.0] * 24, genlik=0.4)
    df.iloc[5, df.columns.get_loc("yuksek")] = 110.0
    df.iloc[7, df.columns.get_loc("dusuk")] = 90.0
    k = df.kapanis.to_numpy().copy()
    k[24:34] = np.linspace(99, 92, 10)
    k[34] = 90.3     # düşüş
    k[35] = 91.5     # yükseliş mumu, S1 (90) üstünde kapanır
    k[36:48] = 92.0
    df = mumlar_kapanistan(k, genlik=0.4)
    df.iloc[5, df.columns.get_loc("yuksek")] = 110.0
    df.iloc[7, df.columns.get_loc("dusuk")] = 90.0
    df.iloc[35, df.columns.get_loc("dusuk")] = 89.9
    s = PivotSeviye(seviyeler="s1", temas_atr=0.5)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[35] == 1
    assert sig.stop.iloc[35] < 89.9 and sig.stop.iloc[35] < df.kapanis.iloc[35]
    assert sig.hedef.iloc[35] > df.kapanis.iloc[35]
    assert (sig.yon.iloc[:24] == 0).all()                       # önceki seans yokken sinyal yok


def test_pivot_kirilim_r1_long_dar_cpr():
    # 1. gün H=110 L=90 C=100 (CPR dar: |2C-H-L|=0). R1=110: ikinci günde kapanış 111'e çıkar.
    k = np.r_[np.full(24, 100.0), np.linspace(100, 109, 10), [111.5], np.full(13, 111.0)]
    df = mumlar_kapanistan(k, genlik=0.3)
    df.iloc[5, df.columns.get_loc("yuksek")] = 110.0
    df.iloc[7, df.columns.get_loc("dusuk")] = 90.0
    sig = PivotSeviye(mod="kirilim", cpr_filtre="uygun").sinyaller(df)
    assert sig.yon.iloc[34] == 1
    assert sig.stop.iloc[34] < 110.0
    assert (sig.yon.iloc[35:] == 0).all()


def test_vwap_alt_bant_donus_long():
    rng = np.random.default_rng(1)
    # 36: aşırı düşüş (92), 37: yükseliş mumu (93.5), 38: önceki mumun zirvesini kıran kapanış (95)
    k = np.r_[np.full(24, 100.0), 100 + rng.normal(0, 0.4, 12), [92.0], [93.5], [95.0], np.full(9, 96.0)]
    df = mumlar_kapanistan(k, genlik=0.2)
    sig = VwapDonus(min_mum=4).sinyaller(df)
    i = 38
    assert sig.yon.iloc[i] == 1
    v = g.vwap_seans(df.yuksek, df.dusuk, df.kapanis, df.hacim, seans_kimligi(df.index))
    assert sig.hedef.iloc[i] == pytest.approx(v["vwap"].iloc[i])
    assert sig.stop.iloc[i] < df.dusuk.iloc[i - 1]


def test_orb_yukari_kirilim_tek_giris():
    k = np.r_[np.full(30, 100.0), [100.0, 100.4, 101.0, 103.0, 103.5, 103.8, 104.0], np.full(11, 104.0)]
    df = mumlar_kapanistan(k, genlik=0.2)
    # 2. gün 00:00 mumu aralık: yüksek 101, düşük 99
    df.iloc[24, df.columns.get_loc("yuksek")] = 101.0
    df.iloc[24, df.columns.get_loc("dusuk")] = 99.0
    sig = Orb(aralik_dk=60, atr_periyot=5).sinyaller(df)
    gun2 = sig.iloc[24:48]
    assert (gun2.yon == 1).sum() == 1
    i = 24 + int(np.argmax(gun2.yon.to_numpy() == 1))
    assert df.kapanis.iloc[i] > 101.0 and sig.stop.iloc[i] == pytest.approx(99.0)
    assert sig.yon.iloc[24] == 0                              # aralık içinde sinyal yok


def test_orb_asagi_kirilim_short_ve_orta_stop():
    k = np.r_[np.full(30, 100.0), [100.0, 99.6, 99.0, 97.0, 96.5, 96.0, 95.5], np.full(11, 95.0)]
    df = mumlar_kapanistan(k, genlik=0.2)
    df.iloc[24, df.columns.get_loc("yuksek")] = 101.0
    df.iloc[24, df.columns.get_loc("dusuk")] = 99.0
    sig = Orb(aralik_dk=60, stop_modu="orta", atr_periyot=5).sinyaller(df)
    i = 24 + int(np.argmax(sig.yon.iloc[24:48].to_numpy() == -1))
    assert sig.yon.iloc[i] == -1 and sig.stop.iloc[i] == pytest.approx(100.0)


def test_kirilim_geri_test_long():
    k = np.r_[np.tile([100.0, 100.4, 99.6, 100.2], 15), [103.0, 104.0, 102.4, 103.2], np.full(8, 103.0)]
    # kutu: 100 civarı (yüksek ~101); kırılım 103; geri test 101.3'e iner, yükselişle kapanır
    df = mumlar_kapanistan(k, genlik=0.5)
    n0 = 60
    df.iloc[n0 + 2, df.columns.get_loc("dusuk")] = 101.3
    df.iloc[n0 + 2, df.columns.get_loc("acilis")] = 102.0
    df.iloc[n0 + 2, df.columns.get_loc("kapanis")] = 102.8
    df.iloc[n0 + 2, df.columns.get_loc("yuksek")] = 103.0
    # n0 mumunu gün ortasına denk getir (60 saat = 2.5 gün: saat 12) -> 62. mum saat 14
    sig = KirilimGeriTest(uzunluk=12, atr_periyot=10).sinyaller(df)
    assert sig.yon.iloc[n0 + 2] == 1
    assert sig.stop.iloc[n0 + 2] < 101.3
    assert (sig.yon.iloc[n0: n0 + 2] == 0).all()               # kırılım mumunda giriş yok


def test_bb_sikisma_kirilim_long():
    rng = np.random.default_rng(3)
    oynak = 100 + np.cumsum(rng.normal(0, 1.5, 100))
    sakin = oynak[-1] + rng.normal(0, 0.05, 30)
    k = np.r_[oynak, sakin, [sakin[-1] + 4.0], np.full(5, sakin[-1] + 4.5)]
    df = mumlar_kapanistan(k, genlik=0.05)
    s = BbSikismaKirilim(sikisma_pencere=60, sikisma_yuzdelik=20.0)
    sig = s.sinyaller(df)
    i = 130
    assert sig.yon.iloc[i] == 1
    assert sig.stop.iloc[i] < df.kapanis.iloc[i] and sig.hedef.iloc[i] > df.kapanis.iloc[i]


def test_konsolidasyon_kirilim_long_ve_hacim_filtresi():
    yukari = np.linspace(80, 100, 70)
    kutu = 100 + np.tile([0.3, -0.3, 0.2, -0.2], 5)
    k = np.r_[yukari, kutu, [102.5], np.full(6, 102.5)]
    hacim = np.ones(len(k))
    df = mumlar_kapanistan(k, genlik=0.3, hacim=hacim)
    df.loc[df.index[90], "hacim"] = 5.0
    s = KonsolidasyonKirilim(uzunluk=12, atr_periyot=10, trend_ema=30)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[90] == 1 and sig.stop.iloc[90] < df.kapanis.iloc[90]
    df2 = df.copy()
    df2.loc[df2.index[90], "hacim"] = 1.0
    assert KonsolidasyonKirilim(uzunluk=12, atr_periyot=10, trend_ema=30).sinyaller(df2).yon.iloc[90] == 0
