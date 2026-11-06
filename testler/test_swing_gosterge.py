"""Swing gösterge stratejileri: lookahead, sentetik sinyal, stop tarafı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji.swing.bant_donus import BantDonus
from motor.strateji.swing.dar_aralik_kirilim import DarAralikKirilim
from motor.strateji.swing.ma_geri_cekilme import MaGeriCekilme
from motor.strateji.swing.macd_sinyal import MacdSinyal


def rastgele_mumlar(n=900, seed=11):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    acilis = np.r_[kap[0], kap[:-1]]
    yuksek = np.maximum(acilis, kap) * (1 + rng.uniform(0, 0.006, n))
    dusuk = np.minimum(acilis, kap) * (1 - rng.uniform(0, 0.006, n))
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": acilis, "yuksek": yuksek, "dusuk": dusuk, "kapanis": kap, "hacim": 1.0}, index=idx)


def ohlc(acilis, yuksek, dusuk, kapanis):
    idx = pd.date_range("2022-01-01", periods=len(kapanis), freq="1D", tz="UTC")
    return pd.DataFrame({"acilis": acilis, "yuksek": yuksek, "dusuk": dusuk, "kapanis": kapanis, "hacim": 1.0}, index=idx)


def kapanistan(kap, genlik=0.5):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    return ohlc(ac, np.maximum(ac, kap) + genlik, np.minimum(ac, kap) - genlik, kap)


STRATEJILER = [
    MacdSinyal(), MacdSinyal(mod="sifir"), MacdSinyal(sifir_filtre=True),
    MaGeriCekilme(), MaGeriCekilme(ma_periyot=10, hedef_r=2.0, adx_esik=20, trend_ma=100),
    BantDonus(), BantDonus(adx_esik=0, rsi_esik=30, bb_periyot=30, hedef_tipi="karsi"),
    DarAralikKirilim(), DarAralikKirilim(mod="ic_bar", hedef_r=2.0), DarAralikKirilim(trend_ma=50, kirilim_tampon_atr=0.25),
]


@pytest.mark.parametrize("s", STRATEJILER, ids=lambda s: f"{s.__class__.__name__}-{abs(hash(str(s.parametreler))) % 997}")
def test_lookahead_yok(s):
    df = rastgele_mumlar()
    tam = s.sinyaller(df)
    for n in (120, 301, 555, 777):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", STRATEJILER, ids=lambda s: f"{s.__class__.__name__}-{abs(hash(str(s.parametreler))) % 997}")
def test_stop_dogru_tarafta(s):
    df = rastgele_mumlar(1500, seed=3)
    sig = s.sinyaller(df)
    assert s.stil == "swing" and s.ad.startswith("swing__")
    assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    gir = sig[sig.yon != 0]
    assert len(gir) > 0 and gir.stop.notna().all()
    kap = df.kapanis[gir.index]
    assert (gir.stop[gir.yon == 1] < kap[gir.yon == 1]).all()
    assert (gir.stop[gir.yon == -1] > kap[gir.yon == -1]).all()
    h = gir.hedef.dropna()
    if len(h):
        assert (h[gir.yon[h.index] == 1] > kap[h.index][gir.yon[h.index] == 1]).all()
        assert (h[gir.yon[h.index] == -1] < kap[h.index][gir.yon[h.index] == -1]).all()


def test_short_kapatilabilir():
    df = rastgele_mumlar(1500, seed=3)
    for s in (MacdSinyal(short=False), MaGeriCekilme(short=False), BantDonus(short=False), DarAralikKirilim(short=False)):
        assert (s.sinyaller(df).yon >= 0).all()


def test_izgara_boyutu():
    for s in STRATEJILER[:1] + [STRATEJILER[3], STRATEJILER[5], STRATEJILER[7]]:
        assert int(np.prod([len(v) for v in s.parametre_izgarasi.values()])) <= 27 + 0
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)


def test_macd_sentetik():
    kap = np.r_[np.linspace(100, 70, 60), np.linspace(70, 110, 40), np.linspace(110, 60, 40)]
    df = kapanistan(kap)
    sig = MacdSinyal().sinyaller(df)
    assert sig.yon[sig.yon == 1].index[0] >= df.index[59]      # dip civarında long
    assert sig.yon[sig.yon == -1].index[-1] > df.index[100]    # tepeden sonra short
    sf = MacdSinyal(mod="sifir").sinyaller(df)
    assert (sf.yon == 1).any() and (sf.yon == -1).any()
    assert sig.cikis.any()


def test_ma_geri_cekilme_sentetik():
    kap = np.r_[np.linspace(100, 200, 120), np.linspace(200, 178, 8), [186.0, 192.0]]
    df = kapanistan(kap, 0.3)
    s = MaGeriCekilme(trend_ma=50, ma_periyot=20, geri_n=5)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[-2:].tolist().count(1) >= 1            # sıçrama mumunda long
    assert (sig.yon.iloc[:120] != 1).sum() >= 100               # düz trend ilerlerken geri çekilme yok
    assert not (sig.yon == -1).any()


def test_bant_donus_sentetik():
    rng = np.random.default_rng(1)
    kap = 100 + rng.normal(0, 0.3, 60)
    kap[50] = 94.0                 # alt bant dışı
    kap[51] = 99.6                 # bant içine dönüş
    df = kapanistan(kap, 0.2)
    sig = BantDonus(adx_esik=0).sinyaller(df)
    assert sig.yon.iloc[51] == 1
    assert sig.hedef.iloc[51] > df.kapanis.iloc[51]
    assert sig.stop.iloc[51] < 94.0
    kap2 = 100 + rng.normal(0, 0.3, 60)
    kap2[50], kap2[51] = 106.0, 100.4
    sg = BantDonus(adx_esik=0).sinyaller(kapanistan(kap2, 0.2))
    assert sg.yon.iloc[51] == -1


def test_dar_aralik_sentetik():
    n = 40
    ac = np.full(n, 100.0); yu = np.full(n, 102.0); du = np.full(n, 98.0); kp = np.full(n, 100.0)
    yu[30], du[30] = 100.5, 99.5          # NR7 mumu
    kp[31], yu[31] = 102.5, 103.0         # yukarı kırılım (kapanış > NR yüksek)
    df = ohlc(ac, yu, du, kp)
    sig = DarAralikKirilim(gecerlilik=3).sinyaller(df)
    assert sig.yon.iloc[31] == 1 and sig.stop.iloc[31] == pytest.approx(99.5)
    assert (sig.yon.iloc[:31] == 0).all()
    # aşağı kırılım
    kp2 = np.full(n, 100.0); yu2 = np.full(n, 102.0); du2 = np.full(n, 98.0)
    yu2[30], du2[30] = 100.5, 99.5
    kp2[31], du2[31] = 97.0, 96.5
    sg = DarAralikKirilim().sinyaller(ohlc(ac, yu2, du2, kp2))
    assert sg.yon.iloc[31] == -1 and sg.stop.iloc[31] == pytest.approx(100.5)


def test_ic_bar_sentetik():
    n = 30
    ac = np.full(n, 100.0); yu = np.full(n, 101.0); du = np.full(n, 99.0); kp = np.full(n, 100.0)
    yu[20], du[20] = 105.0, 95.0          # ana mum (geniş)
    yu[21], du[21] = 103.0, 97.0          # iç bar
    kp[22], yu[22] = 106.0, 106.5         # ana mum yükseğini kapanışla aşar
    sig = DarAralikKirilim(mod="ic_bar").sinyaller(ohlc(ac, yu, du, kp))
    assert sig.yon.iloc[22] == 1 and sig.stop.iloc[22] == pytest.approx(97.0)
