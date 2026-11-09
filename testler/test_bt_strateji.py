"""MA kesişim stratejisi ve göstergeler."""
import numpy as np
import pandas as pd
import pandas.testing as pdt

from motor.strateji import gostergeler as g
from motor.strateji.ma_kesisim import MaKesisim


def rastgele_mumlar(n=800, seed=7):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    acilis = np.r_[kap[0], kap[:-1]]
    yuksek = np.maximum(acilis, kap) * (1 + rng.uniform(0, 0.005, n))
    dusuk = np.minimum(acilis, kap) * (1 - rng.uniform(0, 0.005, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": acilis, "yuksek": yuksek, "dusuk": dusuk, "kapanis": kap,
                         "hacim": 1.0}, index=idx)


def test_lookahead_yok():
    df = rastgele_mumlar()
    for p in [{}, {"trend_ma": 100}, {"ma_tipi": "sma", "hizli": 5, "yavas": 30}]:
        s = MaKesisim(**p)
        tam = s.sinyaller(df)
        for n in (150, 333, 600):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


def test_sinyal_sozlesmesi():
    df = rastgele_mumlar()
    s = MaKesisim().sinyaller(df)
    assert s.index.equals(df.index)
    assert {"yon", "stop", "hedef", "cikis"} <= set(s.columns)
    girisler = s[s.yon != 0]
    assert len(girisler) > 0 and girisler.stop.notna().all()
    long = girisler[girisler.yon == 1]
    assert (long.stop < df.kapanis[long.index]).all()
    short = girisler[girisler.yon == -1]
    assert (short.stop > df.kapanis[short.index]).all()


def test_kesisim_yonu():
    kap = np.r_[np.linspace(100, 80, 40), np.linspace(80, 120, 40)]
    idx = pd.date_range("2024-01-01", periods=80, freq="1h", tz="UTC")
    df = pd.DataFrame({"acilis": kap, "yuksek": kap + 1, "dusuk": kap - 1, "kapanis": kap, "hacim": 1.0}, index=idx)
    s = MaKesisim(hizli=5, yavas=20).sinyaller(df)
    assert (s.yon == 1).any()
    assert s.index[s.yon == 1][0] > idx[40]       # yükseliş başladıktan sonra


def test_gostergeler_temel():
    kap = pd.Series(np.arange(1.0, 101.0))
    assert g.sma(kap, 5).iloc[4] == 3.0
    assert g.rsi(kap, 14).iloc[-1] == 100.0        # hep yükseliş
    assert g.ema(kap, 10).isna().sum() == 9
    b = g.bollinger(kap, 20)
    assert (b.ust >= b.orta).all() or b.ust.isna().any()
    a = g.atr(kap + 1, kap - 1, kap, 14)
    assert abs(a.iloc[-1] - 2.0) < 1e-9
    assert g.macd(kap).shape[1] == 3 and g.adx(kap + 1, kap - 1, kap).shape[1] == 3
    st = g.stokastik(kap + 1, kap - 1, kap)
    assert st.k.iloc[-1] > 90
