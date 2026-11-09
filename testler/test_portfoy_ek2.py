"""portfoy_ek2: pf__pca_statarb, pf__gumus_makro ve Clenow(18 hisse) bağlaması — lookahead, limitler, kural testleri."""
import numpy as np
import pandas as pd
import pytest

from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.ek2 import BAGLAMA_EK2, HISSE18, GumusMakro, PcaStatArb
from motor.portfoy.stratejiler.rotasyon import Rotasyon
from testler.test_portfoy_stratejiler import kes, sentetik

BAS = pd.Timestamp("2021-01-01", tz="UTC")
HISSE8 = HISSE18[:8]
VERI_H = sentetik(n=700, semb=HISSE8 + ("DK_SPX",), seed=5)
VERI_G = sentetik(n=620, semb=("DK_XAG", "DK_UST"), seed=11)

VAKALAR = [
    (PcaStatArb, dict(semboller=HISSE8, n_faktor=2, korel_gun=120, regres_gun=40, giris_long=0.8, giris_short=0.8,
                      kappa_min=0.0), VERI_H),
    (PcaStatArb, dict(semboller=HISSE8, n_faktor=3, korel_gun=200, regres_gun=60, max_poz=2, takvim="D", kappa_min=0.0), VERI_H),
    (GumusMakro, dict(), VERI_G),
    (GumusMakro, dict(ema_yavas=50, makro_ust_yuzde=0.3, flush_1g=2.0, makro_sembol=""), VERI_G),
    (Rotasyon, dict(semboller=HISSE8, skor="regresyon", lookback_gun=90, trend_sma=100, gap_filtre=0.15, k=2, takvim="W",
                    agirlik="ters_vol", mutlak=False, rejim_sembol="DK_SPX", rejim_sma=200), VERI_H),
]
ID = [f"{c.__name__}-{i}" for i, (c, _, _) in enumerate(VAKALAR)]


def test_kayit_ve_izgara():
    t = tum_portfoy_stratejileri()
    for c in (PcaStatArb, GumusMakro):
        assert t[c.ad] is c and c.ad.startswith("pf__")
        n = int(np.prod([len(v) for v in c.parametre_izgarasi.values()]))
        assert 1 < n <= 27 and set(c.parametre_izgarasi) <= set(c.varsayilan_parametreler)
        assert "semboller" in c.varsayilan_parametreler and "atr_k" in c.varsayilan_parametreler


def test_baglama_ek2_gecerli():
    kayitli = tum_portfoy_stratejileri()
    for b in BAGLAMA_EK2:
        st = kayitli[b["sinif"]](**b["ayar"])
        assert st.parametreler["semboller"]
        assert {"satir", "ad_basi", "sinif", "ayar", "not_"} == set(b)


@pytest.mark.parametrize("sinif,kw,veri", VAKALAR, ids=ID)
def test_lookahead_ve_bozma(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    n = len(next(iter(veri.values())))
    for gun in (n - 150, n - 60):
        bitis = BAS + pd.Timedelta(days=gun)
        h2, s2 = st.sinyaller(kes(veri, bitis))
        pd.testing.assert_frame_equal(h.loc[h2.index], h2, check_freq=False)
        pd.testing.assert_frame_equal(s.loc[s2.index], s2, check_freq=False)
    t = BAS + pd.Timedelta(days=n - 200)
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
def test_agirlik_toplami_stop_ve_kaldirac(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    durum = h.ffill().fillna(0.0)
    assert (durum.abs().sum(axis=1) <= 1.0 + 1e-9).all() or sinif is Rotasyon      # long-only rotasyon: toplam <= 1
    assert (durum.abs().sum(axis=1) <= 1.0 + 1e-9).all()
    acik = h.notna() & (h != 0)
    assert s[acik].notna().to_numpy()[acik.to_numpy()].all(), "hedefi sıfırdan farklı satırda stop yok"
    ev = st.evren(veri)
    kap = pd.DataFrame({k: d["kapanis"] for k, d in ev.items()}).reindex(h.index).ffill()
    yon = np.sign(durum)
    ust, alt = (yon > 0) & s.notna(), (yon < 0) & s.notna()
    assert (s[ust] < kap[ust]).to_numpy()[ust.to_numpy()].all()
    assert (s[alt] > kap[alt]).to_numpy()[alt.to_numpy()].all()
    r = portfoy_backtest(veri, st, PortfoyAyarlari())
    assert np.isfinite(r.ozsermaye.to_numpy()).all() and r.ozsermaye.iloc[-1] > 0
    assert float(r.maruziyet_dolum.max()) <= 3.0 + 1e-6


def test_pca_statarb_islem_uretir_ve_faktor_notr():
    st = PcaStatArb(semboller=HISSE8, n_faktor=2, korel_gun=120, regres_gun=40, giris_long=0.8, giris_short=0.8, kappa_min=0.0)
    h, _ = st.sinyaller(VERI_H)
    acik = h.notna() & (h != 0)
    assert acik.any(axis=1).sum() >= 1, "sentetik veride hiç pozisyon açılmadı"
    satir = h[acik.any(axis=1)].iloc[0]
    assert (satir > 0).any() and (satir < 0).any()                     # hisse + özportföy hedge'i = iki yönlü
    with pytest.raises(ValueError):
        PcaStatArb(semboller=HISSE8, n_faktor=7).hedefler(VERI_H)


def _gumus_veri(n=500, dusus_gunu=300):
    idx = pd.date_range("2021-01-01", periods=n, freq="B", tz="UTC", name="zaman")
    r = np.full(n, 0.002)
    r[dusus_gunu] = -0.09                                              # tek günde %9 çöküş (flush)
    k = 30 * np.exp(np.cumsum(r))
    o = np.r_[k[0], k[:-1]]
    df = lambda kk, oo: pd.DataFrame({"acilis": oo, "yuksek": np.maximum(kk, oo) * 1.002, "dusuk": np.minimum(kk, oo) * 0.998,
                                      "kapanis": kk, "hacim": np.full(n, 1000.0)}, index=idx)
    ust = 100 * np.exp(np.cumsum(np.full(n, 0.0002)))
    return {"DK_XAG": df(k, o), "DK_UST": df(ust, np.r_[ust[0], ust[:-1]])}, idx


def test_gumus_makro_flush_cikis_ve_gec_giris():
    veri, idx = _gumus_veri()
    h, _ = GumusMakro().sinyaller(veri)
    durum = h["DK_XAG"].ffill()
    assert durum.iloc[260] == 1.0                                      # düzgün yükselen trendde long
    assert durum.iloc[300] == 0.0                                      # flush gününde kapanışta çıkış kararı
    assert durum.iloc[301] == 0.0                                      # flush sonrası cooldown içinde flat
    assert durum.iloc[-1] == 1.0                                       # toparlanınca (EMA150 üstü) yeniden long
    assert set(h["DK_XAG"].dropna().unique()) <= {0.0, 1.0}            # yalnız long ya da nakit (short/ekleme yok)


def test_gumus_makro_ust_stresi_cikis_getirir():
    veri, idx = _gumus_veri(dusus_gunu=480)
    ust = veri["DK_UST"].copy()
    carp = np.ones(len(ust))
    carp[400:] = np.linspace(1.0, 0.6, len(ust) - 400)                 # tahvil fiyatı düşüyor = getiri yükseliyor
    for a in ("acilis", "yuksek", "dusuk", "kapanis"):
        ust[a] = ust[a] * carp
    veri["DK_UST"] = ust
    h, _ = GumusMakro().sinyaller(veri)
    durum = h["DK_XAG"].ffill()
    assert durum.iloc[390] == 1.0
    assert (durum.iloc[420:470] == 0.0).any(), "makro stres çıkışı yok"
    h0, _ = GumusMakro(makro_sembol="").sinyaller({"DK_XAG": veri["DK_XAG"]})
    assert h0["DK_XAG"].ffill().iloc[420] == 1.0                       # makro kapalıyken çıkış yok


def test_ek_sembol_yoksa_uygun_degil():
    assert not GumusMakro().uygun_mu(["DK_XAG"])
    assert GumusMakro().uygun_mu(["DK_XAG", "DK_UST"])
