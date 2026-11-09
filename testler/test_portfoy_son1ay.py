"""Son 1 ay portföy adayları (pf__son1ay_*): lookahead, stop, motor dumanı, kural testleri."""
import numpy as np
import pandas as pd
import pytest

from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.son1ay import KADEMELI, MAKRO, SonBirAyE014, SonBirAyTrendRider
from testler.test_portfoy_stratejiler import KRIPTO3, kes, sentetik

MAKRO_VERI = sentetik(semb=MAKRO)
VAKALAR = [
    (SonBirAyTrendRider, dict(), sentetik(semb=KRIPTO3)),
    (SonBirAyTrendRider, dict(sma_gun=20, agirlik="esit", iz_stop_yuzde=0.25), sentetik(semb=KRIPTO3)),
    (SonBirAyE014, dict(), MAKRO_VERI),
    (SonBirAyE014, dict(mutlak=True, lookback_gun=126, k=2), MAKRO_VERI),
]
ID = [f"{c.__name__}-{i}" for i, (c, _, _) in enumerate(VAKALAR)]


def test_kayit_ve_izgara():
    t = tum_portfoy_stratejileri()
    for c in (SonBirAyTrendRider, SonBirAyE014):
        assert t[c.ad] is c and c.ad.startswith("pf__son1ay_")
        n = int(np.prod([len(v) for v in c.parametre_izgarasi.values()]))
        assert 1 < n <= 27 and set(c.parametre_izgarasi) <= set(c.varsayilan_parametreler)


@pytest.mark.parametrize("sinif,kw,veri", VAKALAR, ids=ID)
def test_lookahead_ve_bozma(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    for gun in (350, 480):
        bitis = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=gun)
        h2, s2 = st.sinyaller(kes(veri, bitis))
        pd.testing.assert_frame_equal(h.loc[h2.index], h2, check_freq=False)
        pd.testing.assert_frame_equal(s.loc[s2.index], s2, check_freq=False)
    t = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=400)
    boz = {}
    for k, d in veri.items():
        d2 = d.copy()
        son = d2.index > t
        d2.loc[son, ["acilis", "yuksek", "dusuk", "kapanis"]] *= np.linspace(1.0, 3.0, int(son.sum()))[:, None]
        boz[k] = d2
    h3, s3 = st.sinyaller(boz)
    pd.testing.assert_frame_equal(h.loc[:t], h3.loc[:t], check_freq=False)
    pd.testing.assert_frame_equal(s.loc[:t], s3.loc[:t], check_freq=False)


@pytest.mark.parametrize("sinif,kw,veri", VAKALAR, ids=ID)
def test_stop_ve_motor(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    acik = h.notna() & (h != 0)
    assert acik.to_numpy().any() and s[acik].notna().to_numpy()[acik.to_numpy()].all()
    assert (h.fillna(0) >= 0).all().all()                              # long-only
    r = portfoy_backtest(veri, st, PortfoyAyarlari())
    assert np.isfinite(r.ozsermaye.to_numpy()).all() and float(r.maruziyet_dolum.max()) <= 3.0 + 1e-6


def test_trendrider_sma_ustu_dilim_altinda_nakit():
    v = sentetik(semb=KRIPTO3, n=400)
    st = SonBirAyTrendRider(sma_gun=50)
    h, _ = st.sinyaller(v)
    ff = h.ffill()
    kap = pd.DataFrame({k: d["kapanis"] for k, d in v.items()})
    ust = kap > kap.rolling(50).mean()
    # t kapanışı SMA üstündeyse hedef = dilim; değilse 0 (ATR hazır olduktan sonra, SMA hazırken)
    t = kap.index[200:]
    for c in KRIPTO3:
        beklenen = np.where(ust.loc[t, c], KADEMELI[c], 0.0)
        np.testing.assert_allclose(ff.loc[t, c].to_numpy(), beklenen)
    eş = SonBirAyTrendRider(sma_gun=50, agirlik="esit").sinyaller(v)[0].ffill()
    assert set(np.round(eş.loc[t].to_numpy().ravel(), 6)) <= {0.0, round(1 / 3, 6)}


def test_e014_haftalik_25hafta_en_iyi_tek_varlik():
    v = sentetik(semb=MAKRO, n=500)
    h, _ = SonBirAyE014().sinyaller(v)
    satir = h.dropna(how="all")
    assert (satir.index.dayofweek[1:] == 0).all()                     # haftalık: Pazartesi
    kap = pd.DataFrame({k: d["kapanis"] for k, d in v.items()}).asfreq("D").ffill()
    mom = kap / kap.shift(175) - 1.0
    for t, w in satir.iloc[3:].iterrows():
        assert w.sum() == pytest.approx(1.0) and (w > 0).sum() == 1
        assert w.idxmax() == mom.loc[t].idxmax()
