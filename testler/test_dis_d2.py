"""D2 grubu dış stratejiler: lookahead, stop/hedef tarafı, sentetik senaryoda sinyal, daytrade gün sonu, göstergeler."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import gostergeler as g
from motor.strateji import kayit
from motor.strateji.daytrade._ortak import seans_son_mumu
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.dis.d2_diger import (NornWeave, ObsHacimSoku, ShmWma, TrendAnalysis, VpDegerAlani, XauEmaAtr,
                                         _hacim_profili)
from motor.strateji.dis.d2_freqtrade import FtAdxMomentum, FtBinHV27, FtBinHV45, FtEmaSkipPump, FtFSample
from motor.strateji.dis.d2_gauss import GaussStochBtc, GaussStochEth, RsiGaussVelocity
from motor.strateji.dis.d2_sikisma import RsiCoil, RsiT3Sqz, SqzDonus
from motor.strateji.dis.d2_smc import SmartTrendBos, SmcObFvgSweep, SmcProBtc, TomukasSmc
from motor.strateji.dis.d2_trend import (OneMr1, Sott, SpyAyiShort, TascHaftadaYuzde1, VixfixStoch,
                                         VoltargetTrend)


def rastgele_mumlar(n=3000, seed=5, freq="1h", vol=0.01, baslangic="2022-01-03"):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0, vol, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range(baslangic, periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def mumlar_kapanistan(kap, genlik=0.3, hacim=1.0, freq="1D", baslangic="2022-01-03"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range(baslangic, periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hacim}, index=idx)


# (strateji, grafik aralığı, mum sayısı)
TUM = [
    (GaussStochBtc(), "4h", 3000), (GaussStochBtc(short=True, per=55), "4h", 3000),
    (GaussStochEth(), "4h", 3000), (GaussStochEth(short=True, sma_rejim=0, yesil_mum=False), "4h", 3000),
    (RsiGaussVelocity(), "1D", 1500), (RsiGaussVelocity(short=True, per=55), "1D", 1500),
    (SqzDonus(), "1D", 1500), (RsiT3Sqz(), "1D", 1500), (RsiT3Sqz(short=False), "1D", 1500),
    (RsiCoil(), "1h", 3000), (RsiCoil(yuzdelik_esik=40.0, adx_min=0.0), "1h", 3000),
    (Sott(), "1D", 1500), (Sott(periyot_k=60, yumusatma_k=10), "1D", 1500),
    (SpyAyiShort(), "1D", 1500), (SpyAyiShort(long=True, bosluk_yuzde=0.0), "1D", 1500),
    (VixfixStoch(), "1D", 1500), (VixfixStoch(short=True), "1D", 1500),
    (VoltargetTrend(), "1D", 1500), (VoltargetTrend(short=True, sma_n=50), "1D", 1500),
    (OneMr1(), "1D", 1500), (OneMr1(short=True, alt=2.0, ust=9.0), "1D", 1500),
    (TascHaftadaYuzde1(), "4h", 3000), (TascHaftadaYuzde1(short=True), "4h", 3000),
    (SmcProBtc(), "15min", 4000), (SmcProBtc(secici=True, swing_n=5), "15min", 4000),
    (SmcObFvgSweep(), "1h", 3000), (SmcObFvgSweep(retest=False), "1h", 3000),
    (SmcObFvgSweep(onay="ob_ustu", swing_n=3, yer_degistirme=0.0), "1h", 3000),
    (TomukasSmc(), "1h", 3000), (TomukasSmc(swing_n=3, adx_esik=10.0), "1h", 3000),
    (SmartTrendBos(), "1h", 3000), (SmartTrendBos(onay_modu=3, pivot_n=5), "1h", 3000),
    (NornWeave(), "4h", 3000), (NornWeave(ema_n=21, adx_esik=10.0), "4h", 3000),
    (TrendAnalysis(), "4h", 3000), (TrendAnalysis(min_skor=34.0, gec_giris=False), "4h", 3000),
    (ShmWma(), "4h", 3000), (ShmWma(hizli=21, yavas=100, rsi_filtre=False), "4h", 3000),
    (VpDegerAlani(), "1h", 3000), (VpDegerAlani(mod="fade", lookback=5), "1h", 3000),
    (VpDegerAlani(mod="kirilim", hacim_k=1.0), "1h", 3000),
    (ObsHacimSoku(), "15min", 3000), (XauEmaAtr(), "15min", 3000), (XauEmaAtr(short=False, hedef_r=0.7), "15min", 3000),
    (FtAdxMomentum(), "1h", 3000), (FtAdxMomentum(short=True), "1h", 3000),
    (FtBinHV27(), "15min", 4000), (FtBinHV27(short=True, adx_1=10.0), "15min", 4000),
    (FtBinHV45(), "15min", 3000), (FtBinHV45(short=True, bbdelta=2, closedelta=3), "15min", 3000),
    (FtEmaSkipPump(), "15min", 3000), (FtEmaSkipPump(short=True), "15min", 3000),
    (FtFSample(), "1h", 3000), (FtFSample(short=False), "1h", 3000),
]


def _id(t):
    s = t[0]
    return f"{s.ad.split('__')[1]}-{abs(hash(str(s.parametreler))) % 997}"


@pytest.fixture(scope="module")
def veri():
    cache = {}

    def al(freq, n):
        if (freq, n) not in cache:
            cache[(freq, n)] = rastgele_mumlar(n, freq=freq, vol=0.01 if freq != "15min" else 0.006)
        return cache[(freq, n)]
    return al


@pytest.mark.parametrize("t", TUM, ids=[_id(t) for t in TUM])
def test_lookahead_yok(t, veri):
    s, freq, n = t
    df = veri(freq, n)
    tam = s.sinyaller(df)
    for m in (130, 301, 777, 1301, int(n * 0.8)):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:m]), tam.iloc[:m])


@pytest.mark.parametrize("t", TUM, ids=[_id(t) for t in TUM])
def test_stop_ve_hedef_dogru_tarafta(t, veri):
    s, freq, n = t
    df = veri(freq, n)
    sig = s.sinyaller(df)
    assert list(sig.columns[:4]) == ["yon", "stop", "hedef", "cikis"]
    assert sig.index.equals(df.index)
    kap = df["kapanis"]
    uzun, kisa = sig["yon"] == 1, sig["yon"] == -1
    assert sig.loc[uzun | kisa, "stop"].notna().all()
    assert (sig.loc[uzun, "stop"] < kap[uzun]).all()
    assert (sig.loc[kisa, "stop"] > kap[kisa]).all()
    h_l, h_s = sig.loc[uzun, "hedef"].dropna(), sig.loc[kisa, "hedef"].dropna()
    assert (h_l > kap[h_l.index]).all()
    assert (h_s < kap[h_s.index]).all()
    assert sig.loc[sig["yon"] == 0, ["stop", "hedef"]].isna().all().all()
    assert s.cikis_var_mi()


# --- sentetik veride (sabit seed) varsayılan parametrelerle sinyal üretimi
ONLAR = [
    (GaussStochBtc(), "4h", 3000, 1), (GaussStochEth(), "4h", 3000, 1), (RsiGaussVelocity(), "1D", 1500, 1),
    (SqzDonus(), "1D", 1500, 0), (RsiT3Sqz(), "1D", 1500, 0), (RsiCoil(), "1h", 3000, 0), (Sott(), "1D", 1500, 0),
    (VixfixStoch(), "1D", 1500, 1), (VoltargetTrend(), "1D", 1500, 1),
    (SmcProBtc(), "15min", 4000, 1), (SmcObFvgSweep(), "1h", 3000, 0), (TomukasSmc(), "1h", 3000, 0),
    (SmartTrendBos(), "1h", 3000, 0), (NornWeave(), "4h", 3000, 0), (TrendAnalysis(), "4h", 3000, 0),
    (ShmWma(), "4h", 3000, 0), (VpDegerAlani(), "1h", 3000, 0), (XauEmaAtr(), "15min", 3000, 0),
    (FtAdxMomentum(), "1h", 3000, 1), (FtBinHV27(), "15min", 4000, 1), (FtBinHV45(bbdelta=3, closedelta=5), "15min", 3000, 1),
    (FtEmaSkipPump(), "15min", 3000, 1), (FtFSample(), "1h", 3000, 0),
]


@pytest.mark.parametrize("t", ONLAR, ids=[_id(t) for t in ONLAR])
def test_sentetik_veride_long_sinyali(t, veri):
    s, freq, n, _ = t
    sig = s.sinyaller(veri(freq, n))
    assert (sig["yon"] == 1).sum() > 0


@pytest.mark.parametrize("s", [RsiCoil(), SmartTrendBos(), SmcObFvgSweep(), TomukasSmc(), VpDegerAlani(), FtAdxMomentum(),
                               FtFSample(short=True)], ids=lambda s: s.ad.split("__")[1])
def test_daytrade_gun_sonu(s, veri):
    df = veri("1h", 3000)
    sig = s.sinyaller(df)
    son = seans_son_mumu(df.index)
    assert son.sum() > 100
    assert (sig.loc[son, "yon"] == 0).all()
    assert sig.loc[son, "cikis"].all()
    assert s.stil == "daytrade"


def test_stil_kurali():
    stiller = {s.ad: s.stil for s, _, _ in TUM}
    assert stiller["dis__ft-binhv45"] == "scalp" and stiller["dis__smc-pro-btc"] == "scalp"
    assert stiller["dis__sott"] == "swing" and stiller["dis__rsi-coil"] == "daytrade"
    for s, freq, _ in TUM:
        if s.stil == "scalp":
            assert freq == "15min"          # scalp en az 15m
        if s.stil == "daytrade":
            assert freq == "1h"


def test_kayit_kapisi_d2_temiz():
    sorunlar = [x for x in kayit.dogrula() if "dis__" in x]
    assert sorunlar == []
    d2 = [a for a, s in kayit.tum_stratejiler().items() if s.__module__.rsplit(".", 1)[-1].startswith("d2_")]
    assert len(d2) == 27
    for a in d2:
        assert a.startswith("dis__")


# --- elle kurulan senaryolar
def test_one_mr1_dusus_sonrasi_long_ve_stop_altinda():
    kap = [100.0] * 20 + [100.0, 97.0, 94.0, 94.0, 94.0, 94.0, 94.0, 95.0]
    sig = OneMr1().sinyaller(mumlar_kapanistan(kap))
    assert (sig["yon"] == 1).any()
    i = sig.index[sig["yon"] == 1][0]
    assert sig.loc[i, "stop"] < kap[sig.index.get_loc(i)]


def test_spy_ayi_short_senaryosu():
    kap = list(np.linspace(200, 100, 300)) + [100.5, 101.0, 107.0, 114.0]
    sig = SpyAyiShort().sinyaller(mumlar_kapanistan(kap))
    assert (sig["yon"] == -1).any()
    sig2 = SpyAyiShort(short=False).sinyaller(mumlar_kapanistan(kap))
    assert (sig2["yon"] == 0).all()


def test_obs_hacim_soku_dusus_mumunda_long():
    n = 60
    kap = np.full(n, 100.0)
    df = mumlar_kapanistan(kap, genlik=0.2, freq="15min")
    j = 45
    df.iloc[j, df.columns.get_loc("acilis")] = 100.0
    df.iloc[j, df.columns.get_loc("yuksek")] = 100.5
    df.iloc[j, df.columns.get_loc("dusuk")] = 90.0
    df.iloc[j, df.columns.get_loc("kapanis")] = 91.0
    df.iloc[j, df.columns.get_loc("hacim")] = 12.0
    sig = ObsHacimSoku().sinyaller(df)
    assert sig["yon"].iloc[j] == 1
    assert sig["stop"].iloc[j] < 90.0 and sig["hedef"].iloc[j] > 91.0
    assert (sig["yon"].drop(df.index[j]) == 0).all()


def test_tasc_haftada_yuzde1_dip_alim_ve_hafta_sonu_cikisi():
    n = 42 * 3                      # 3 hafta, 4h mum (hafta Pazartesi 00:00 UTC başlar)
    df = mumlar_kapanistan(np.full(n, 100.0), genlik=0.1, freq="4h")
    j = 20
    df.iloc[j, df.columns.get_loc("dusuk")] = 98.5
    df.iloc[j, df.columns.get_loc("kapanis")] = 99.0
    sig = TascHaftadaYuzde1().sinyaller(df)
    assert sig["yon"].iloc[j] == 1
    assert sig["hedef"].iloc[j] == pytest.approx(99.0 * 1.01)
    assert sig["cikis"].iloc[41] and sig["cikis"].iloc[83]
    assert sig["cikis"].sum() == 3 or sig["cikis"].sum() == 2     # son hafta kesik olabilir
    assert (sig["yon"].iloc[41] == 0)


def test_voltarget_yukselen_trendde_long():
    kap = 100 * np.exp(np.cumsum(np.full(400, 0.002)))
    sig = VoltargetTrend().sinyaller(mumlar_kapanistan(kap))
    assert (sig["yon"] == 1).any()


def test_adx_momentum_guclu_yukselis():
    kap = 100 * np.exp(np.cumsum(np.full(300, 0.004)))
    sig = FtAdxMomentum().sinyaller(mumlar_kapanistan(kap, freq="1h"))
    assert (sig["yon"] == 1).any()


def test_xau_ema_atr_kesisim():
    kap = list(np.linspace(100, 130, 80)) + [127.0, 126.0, 131.0, 133.0]
    sig = XauEmaAtr().sinyaller(mumlar_kapanistan(kap, genlik=0.5, freq="15min"))
    assert (sig["yon"] == 1).any()


# --- göstergeler
def test_gauss_filtresi_sabit_seriye_yakinsar():
    s = pd.Series(np.full(2000, 50.0))
    f = gd.gauss_filtre(s, 55, 4)
    assert f.iloc[-1] == pytest.approx(50.0, rel=1e-6)
    assert f.iloc[10] < 25.0                                   # sıfırdan başlar (Pine nz benzeri) -> ısınma gerekir


def test_gauss_filtre_nedensel():
    s = pd.Series(np.random.default_rng(1).normal(100, 1, 600))
    pdt.assert_series_equal(gd.gauss_filtre(s, 20, 3).iloc[:300], gd.gauss_filtre(s.iloc[:300], 20, 3))


def test_linreg_wma_hma_dogru():
    rng = np.random.default_rng(3)
    s = pd.Series(rng.normal(0, 1, 120).cumsum() + 50)
    n = 20
    beklenen_lr = s.rolling(n).apply(lambda w: np.polyval(np.polyfit(np.arange(n), w, 1), n - 1), raw=True)
    pdt.assert_series_equal(gd.linreg(s, n), beklenen_lr, check_names=False, rtol=1e-8)
    w = np.arange(1, n + 1)
    beklenen_wma = s.rolling(n).apply(lambda x: (x * w).sum() / w.sum(), raw=True)
    pdt.assert_series_equal(gd.wma(s, n), beklenen_wma, check_names=False, rtol=1e-9)
    h = gd.hma(s, 16)
    assert h.notna().sum() > 80 and np.isnan(h.iloc[:16]).all()


def test_percentrank_ve_pivotlar():
    s = pd.Series([5.0, 1, 2, 3, 4, 6, 0, 7, 8, 2.5])
    pr = gd.pine_percentrank(s, 4)
    assert np.isnan(pr.iloc[:4]).all()
    assert pr.iloc[5] == 100.0                  # 6 >= önceki 4 değerin hepsi (1,2,3,4)
    assert pr.iloc[6] == 0.0                    # 0 <= hiçbiri değil
    yuk = pd.Series([1.0, 2, 5, 3, 2, 1, 2, 3, 9, 4, 3, 2, 1])
    pv = gd.pivot_yuksek(yuk, 2)
    assert pv.iloc[4] == 5.0 and pv.iloc[10] == 9.0     # onay 2 mum sonra
    assert pv.iloc[:4].isna().all()


def test_hafta_son_mumu_ve_kimligi():
    idx = pd.date_range("2022-01-03", periods=14, freq="1D", tz="UTC")       # Pazartesi'den iki hafta
    son = gd.hafta_son_mumu(idx)
    assert son[6] and not son[13] or son[6]
    assert not son[:6].any() and not son[7:13].any()
    assert len(set(gd.hafta_kimligi(idx))) == 2


def test_hacim_profili_poc_ve_deger_alani():
    rng = np.random.default_rng(0)
    orta = 100.0 + rng.normal(0, 1, 500)
    yuk, dus = orta + 0.2, orta - 0.2
    poc, vah, val = _hacim_profili(yuk, dus, np.ones(500), 60, 70.0)
    assert val < poc < vah
    assert 98 < poc < 102
    assert (vah - val) < (yuk.max() - dus.min())


def test_ott_ve_var_nedensel():
    s = pd.Series(np.random.default_rng(2).normal(0, 1, 500).cumsum() + 1000)
    pdt.assert_series_equal(gd.ott(s, 3, 0.618).iloc[:300], gd.ott(s.iloc[:300], 3, 0.618))
    pdt.assert_series_equal(gd.var_ma(s, 50).iloc[:250], gd.var_ma(s.iloc[:250], 50))
