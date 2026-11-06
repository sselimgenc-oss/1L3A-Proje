"""Scalp stratejileri (15m): lookahead, sentetik senaryo, stop tarafı, göstergeler (Supertrend/PSAR)."""
import itertools

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import gostergeler as g
from motor.strateji.scalp.konsolidasyon_kirilim import KonsolidasyonKirilim
from motor.strateji.scalp.ma_geri_cekilme import MaGeriCekilme
from motor.strateji.scalp.ma_kesisim import MaKesisim
from motor.strateji.scalp.stokastik_donus import StokastikDonus
from motor.strateji.scalp.supertrend_psar import SupertrendPsar


def rastgele_mumlar(n=2500, seed=7, freq="15min"):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.006, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.003, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.003, n))
    idx = pd.date_range("2022-01-01", periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def mumlar_kapanistan(kap, genlik=0.3, hacim=1.0, freq="15min"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range("2022-01-01", periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hacim}, index=idx)


STRATEJILER = [
    StokastikDonus(), StokastikDonus(trend_ema=20, k_periyot=8, hedef_r=1.0),
    MaKesisim(), MaKesisim(hizli=5, yavas=34, adx_esik=0.0, hedef_r=2.0), MaKesisim(adx_esik=25.0, trend_ma=100),
    MaGeriCekilme(), MaGeriCekilme(ma_periyot=10, hedef_r=3.0, stop_tampon_atr=1.0),
    SupertrendPsar(), SupertrendPsar(gosterge="psar"), SupertrendPsar(gosterge="ikisi", rsi_esik=55.0, hedef_r=2.0),
    SupertrendPsar(atr_periyot=7, carpan=2.0),
    KonsolidasyonKirilim(), KonsolidasyonKirilim(uzunluk=8, hacim_k=0.0, stop_modu="uc", trend_ema=0),
]


def _id(s):
    return f"{s.ad.split('__')[1]}-{abs(hash(str(s.parametreler))) % 997}"


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_lookahead_yok(s):
    df = rastgele_mumlar()
    tam = s.sinyaller(df)
    for n in (130, 301, 555, 1001, 1777, 2222):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_stop_dogru_tarafta(s):
    df = rastgele_mumlar(4000, seed=2)
    sig = s.sinyaller(df)
    assert s.stil == "scalp" and s.ad.startswith("scalp__") and s.cikis_var_mi() is True
    assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    gir = sig[sig.yon != 0]
    assert len(gir) > 0 and gir.stop.notna().all()
    kap = df.kapanis[gir.index]
    assert (gir.stop[gir.yon == 1] < kap[gir.yon == 1]).all()
    assert (gir.stop[gir.yon == -1] > kap[gir.yon == -1]).all()
    h = gir.hedef.dropna()
    yh = gir.yon[h.index]
    assert (h[yh == 1] > kap[h.index][yh == 1]).all() and (h[yh == -1] < kap[h.index][yh == -1]).all()
    assert sig.cikis.any() or gir.hedef.notna().any()          # stop dışında en az bir çıkış yolu var


def test_parametre_izgarasi_sinirli_ve_short():
    for s in STRATEJILER:
        assert 1 <= np.prod([len(v) for v in s.parametre_izgarasi.values()]) <= 27
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)
        for komb in itertools.islice(itertools.product(*s.parametre_izgarasi.values()), 3):
            s.yeni(**dict(zip(s.parametre_izgarasi, komb)))
    df = rastgele_mumlar(4000, seed=2)
    for cls in (StokastikDonus, MaKesisim, MaGeriCekilme, SupertrendPsar, KonsolidasyonKirilim):
        kapali = cls(short=False) if cls is not KonsolidasyonKirilim else cls(short=False, hacim_k=0.0)
        assert (kapali.sinyaller(df).yon >= 0).all()


# ---------------------------------------------------------------- göstergeler

def test_supertrend_psar_yon_ve_nedensellik():
    kap = np.r_[np.linspace(100, 80, 60), np.linspace(80, 110, 80)]
    df = mumlar_kapanistan(kap, genlik=0.4)
    st = g.supertrend(df.yuksek, df.dusuk, df.kapanis, 7, 3.0)
    ps = g.psar(df.yuksek, df.dusuk)
    assert st.yon.iloc[55] == -1 and st.yon.iloc[-1] == 1
    assert ps.yon.iloc[55] == -1 and ps.yon.iloc[-1] == 1
    assert (st.cizgi[st.yon == 1] < df.kapanis[st.yon == 1]).all()
    assert (st.cizgi[st.yon == -1] > df.kapanis[st.yon == -1]).all()
    assert (ps.sar[ps.yon == 1] < df.kapanis[ps.yon == 1]).all()
    assert (ps.sar[ps.yon == -1] > df.kapanis[ps.yon == -1]).all()
    pdt.assert_frame_equal(g.supertrend(df.yuksek[:90], df.dusuk[:90], df.kapanis[:90], 7, 3.0), st.iloc[:90])
    pdt.assert_frame_equal(g.psar(df.yuksek[:90], df.dusuk[:90]), ps.iloc[:90])


# ---------------------------------------------------------------- sentetik senaryolar

def test_supertrend_dipten_donuste_long_ve_ters_cikis():
    kap = np.r_[np.linspace(100, 80, 60), np.linspace(80, 110, 50), np.linspace(110, 85, 40)]
    df = mumlar_kapanistan(kap, genlik=0.4)
    sig = SupertrendPsar(atr_periyot=7, carpan=2.0).sinyaller(df)
    longlar = sig.index[sig.yon == 1]
    assert len(longlar) >= 1
    ilk = df.index.get_loc(longlar[0])
    assert 60 <= ilk < 80 and sig.stop.iloc[ilk] < df.kapanis.iloc[ilk]
    sonraki_cikis = sig.cikis.iloc[ilk + 1:]
    assert sonraki_cikis.any() and df.index.get_loc(sonraki_cikis.idxmax()) > 110     # tepeden dönüşte çıkış


def test_ma_kesisim_yukari_kesisimde_long():
    kap = np.r_[np.linspace(100, 90, 50), np.linspace(90, 110, 50)]
    df = mumlar_kapanistan(kap)
    sig = MaKesisim(adx_esik=0.0).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(longlar) == 1 and 55 <= longlar[0] <= 80
    i = longlar[0]
    assert sig.stop.iloc[i] < df.kapanis.iloc[i] and sig.cikis.iloc[i]      # kesişim mumu: cikis ters yönü kapatır
    # ADX filtresi giriş sayısını artırmaz
    f = MaKesisim(adx_esik=60.0).sinyaller(df)
    assert (f.yon != 0).sum() <= (sig.yon != 0).sum()
    # hedef_r
    h = MaKesisim(adx_esik=0.0, hedef_r=2.0).sinyaller(df)
    assert h.hedef.iloc[i] == pytest.approx(df.kapanis.iloc[i] + 2.0 * (df.kapanis.iloc[i] - h.stop.iloc[i]))


def test_ma_geri_cekilme_trend_geri_cekilme_sicrama():
    kap = np.r_[np.linspace(100, 140, 130), np.linspace(140, 134, 5), [138.0], np.linspace(138, 150, 20)]
    df = mumlar_kapanistan(kap, genlik=0.3)
    s = MaGeriCekilme(ma_periyot=10, trend_ma=50, geri_n=6, temas_atr=1.0)
    sig = s.sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(longlar) >= 1 and any(130 <= i <= 140 for i in longlar)
    i = [i for i in longlar if i >= 130][0]
    assert sig.stop.iloc[i] < df.dusuk.iloc[130:i + 1].min() and sig.hedef.iloc[i] > df.kapanis.iloc[i]


def test_stokastik_trendde_asiri_satim_donusu():
    t = np.arange(600)
    kap = 100 + 0.05 * t + 2.0 * np.sin(t / 3.0)
    df = mumlar_kapanistan(kap, genlik=0.2)
    s = StokastikDonus(trend_ema=50)
    sig = s.sinyaller(df)
    ema = g.ema(df.kapanis, 50)
    gir = sig.yon != 0
    assert (sig.yon == 1).sum() >= 5
    assert (df.kapanis[sig.yon == 1] > ema[sig.yon == 1]).all()
    assert (df.kapanis[sig.yon == -1] < ema[sig.yon == -1]).all()
    ham = g.stokastik(df.yuksek, df.dusuk, df.kapanis, 14, 1)["k"]
    kk = g.sma(ham, 3)
    # her long'dan önceki 3 mumda %K <= 20 görülmüş olmalı
    for i in np.flatnonzero(sig.yon.to_numpy() == 1):
        assert kk.iloc[i - 2:i + 1].min() <= 20.0
    assert gir.any()


def test_konsolidasyon_kirilim_scalp_long():
    yukari = np.linspace(90, 100, 60)
    kutu = 100 + np.tile([0.3, -0.3, 0.2, -0.2], 3)
    k = np.r_[yukari, kutu, [102.5], np.full(5, 102.5)]
    df = mumlar_kapanistan(k, genlik=0.3)
    df.loc[df.index[72], "hacim"] = 5.0
    sig = KonsolidasyonKirilim(uzunluk=10, atr_periyot=10, trend_ema=30).sinyaller(df)
    assert sig.yon.iloc[72] == 1
    assert sig.stop.iloc[72] == pytest.approx(100.0, abs=0.5) and sig.hedef.iloc[72] > 102.5
    assert (sig.yon.iloc[:72] == 0).all()
