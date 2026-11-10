"""Portföy stratejileri (motor/portfoy/stratejiler/): kayıt, ızgara, lookahead, stop, motor dumanı, pairs ve rotasyon özel testleri."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import EK_SINIFLAR, SINIFLAR, V2_SINIFLAR, V3_SINIFLAR, tum_portfoy_stratejileri
from motor.portfoy.stratejiler.baglama import BAGLAMA, BAGLANAMAYAN
from motor.portfoy.stratejiler.ortak import HEPSI, Takvim, donem_kimligi, tetik_satirlari
from motor.portfoy.stratejiler.pairs import Pairs, adf_t, johansen_iki, kalman_hata, ols_cizgi
from motor.portfoy.stratejiler.rotasyon import Gem, Rotasyon, SabitSepet
from motor.portfoy.stratejiler.sinyal import BtcHedge, IbsDonus, ReferansFiltreliLong, RsiCift, RsiTarama
from motor.portfoy.stratejiler.kesit import GoreceliGuc, KesitLS, WqAlfa
from motor.portfoy.stratejiler.cta import Cta
from motor.portfoy.stratejiler.ek2 import HISSE18
from motor.portfoy.stratejiler.rotasyon import Kanarya, TrendSepet

KRIPTO3 = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
SEMB = KRIPTO3 + ("DK_AAPL", "DK_MSFT", "DK_XAU")
CSV = Path(__file__).resolve().parents[1] / "stratejiler" / "portfoy_adaylari.csv"


def sentetik(n=620, semb=SEMB, seed=3, bas="2021-01-01"):
    """Ortak faktörlü rastgele yürüyüş; DK_ sembolleri hafta sonu işlem görmez."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC", name="zaman")
    ortak = np.cumsum(rng.normal(0.0002, 0.012, n))
    v = {}
    for s in semb:
        r = 0.7 * ortak + np.cumsum(rng.normal(0.0004, 0.018, n))
        k = 100 * np.exp(r)
        o = np.r_[k[0], k[:-1]] * (1 + rng.normal(0, 0.003, n))
        h = np.maximum(o, k) * (1 + abs(rng.normal(0, 0.006, n)))
        l = np.minimum(o, k) * (1 - abs(rng.normal(0, 0.006, n)))
        df = pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": k, "hacim": rng.uniform(1, 2, n) * 1000},
                          index=idx)
        v[s] = df[df.index.dayofweek < 5] if s.startswith("DK_") else df
    return v


def kes(v, bitis):
    return {s: d[d.index < bitis] for s, d in v.items()}


# (sınıf, kwargs): her skor/mod/yöntem bir kez
VAKALAR = [
    (Rotasyon, {}),
    (Rotasyon, dict(skor="agirlikli", lookback_gun=30, lookback2_gun=90, takvim="W", k=2)),
    (Rotasyon, dict(skor="w13612", takvim="14", k=3, agirlik="ters_vol")),
    (Rotasyon, dict(skor="regresyon", lookback_gun=60, trend_sma=50, gap_filtre=0.15, k=2, takvim="W")),
    (Rotasyon, dict(skor="risk_ayarli", lookback_gun=30, k=2, cikis_rank=4, takvim="W")),
    (Rotasyon, dict(skor="dusuk_vol", lookback_gun=40, k=2, mutlak=False, takvim="W")),
    (Rotasyon, dict(skor="kompozit", trend_sma=40, rejim_sembol="BTCUSDT", rejim_sma=40, iz_stop_yuzde=0.15, k=2)),
    (Gem, dict(lookback_gun=90, takvim="M")),
    (Gem, dict(skor="agirlikli", lookback_gun=30, lookback2_gun=90, takvim="30", savunma=())),
    (SabitSepet, dict(semboller=KRIPTO3, takvim="M")),
    (SabitSepet, dict(semboller=KRIPTO3, takvim="yok", sapma=0.05)),
    (SabitSepet, dict(semboller=KRIPTO3, agirlik="sabit", agirliklar=(0.5, 0.3, 0.2), takvim="yok", sapma=0.05)),
    (SabitSepet, dict(semboller=SEMB, agirlik="ters_vol", takvim="M")),
    (TrendSepet, dict(sma_gun=100)),
    (TrendSepet, dict(sma_gun=100, nakitli=False, takvim="W")),
    (Kanarya, dict(mod="daa", kanarya=("BTCUSDT", "DK_XAU"))),
    (Kanarya, dict(mod="vaa", ust_k=2)),
    (KesitLS, dict(lookback_gun=14, k=2)),
    (KesitLS, dict(skor="getiri", lookback_gun=90, atla_gun=20, k=1, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="artik", lookback_gun=60, k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="beta", lookback_gun=120, k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="zirve", lookback_gun=100, k=2, takvim="W", agirlik="esit", mod="long")),
    (KesitLS, dict(skor="carpiklik", lookback_gun=100, k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="asimetri", lookback_gun=100, k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="hacim", k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="donus", lookback_gun=7, lookback2_gun=30, k=2, takvim="W", agirlik="esit")),
    (KesitLS, dict(skor="tutarli", lookback_gun=100, atla_gun=20, lookback2_gun=60, takvim="30", agirlik="esit")),
    (KesitLS, dict(skor="getiri", lookback_gun=60, vol_filtre="yuksek", k=1, takvim="W", agirlik="esit", mod="ters")),
    (GoreceliGuc, dict(mod="geri_cekilme", rs_gun=30)),
    (GoreceliGuc, dict(mod="donus_kirilim", rs_gun=30, rs_sma=20, kirilim_gun=10, ref_sembol="BTCUSDT")),
    (WqAlfa, dict(alfa=101)),
    (WqAlfa, dict(alfa=12)),
    (WqAlfa, dict(alfa=33, takvim="3")),
    (WqAlfa, dict(alfa=6)),
    (WqAlfa, dict(alfa=41, takvim="W")),
    (Cta, dict(sinyal="ewmac")),
    (Cta, dict(sinyal="ewmac", birlesim="kovaryans")),
    (Cta, dict(sinyal="tsmom", tsmom_gun=100, takvim="M", yon="long")),
    (Cta, dict(sinyal="sma", yavas=50)),
    (Pairs, dict(ciftler=(("BTCUSDT", "ETHUSDT"), ("DK_AAPL", "DK_MSFT")), yontem="eg", pencere=120, giris_z=1.0)),
    (Pairs, dict(ciftler="otomatik", yontem="johansen", pencere=120, giris_z=1.0)),
    (Pairs, dict(ciftler=(("BTCUSDT", "ETHUSDT"), ("ETHUSDT", "SOLUSDT")), yontem="kalman", pencere=40, giris_z=0.5,
                 cikis_z=0.0)),
    (Pairs, dict(ciftler="otomatik", yontem="mesafe", pencere=60, giris_z=0.5, cikis_z=0.0, max_cift=3, max_tutma=20)),
    (Pairs, dict(ciftler=(("ETHUSDT", "BTCUSDT"),), yontem="oran_sma", pencere=20, giris_z=0.0, cikis_z=0.0,
                 semboller=("ETHUSDT", "BTCUSDT"))),
    (ReferansFiltreliLong, dict(semboller=("ETHUSDT", "SOLUSDT"), giris="sikisma")),
    (ReferansFiltreliLong, dict(semboller=("DK_AAPL", "DK_MSFT"), ref_sembol="", giris="ema", ema_hizli=10, ema_gun=21,
                                ref_ema=21, iz_stop_yuzde=0.035)),
    (BtcHedge, dict()),
    (BtcHedge, dict(hedge_sembol="ETHUSDT", hedge_orani=0.5)),
    (RsiCift, dict(esik_hedef=45.0, esik_ref=50.0)),
    (RsiTarama, dict(asiri_satim=40.0, onay=50.0)),
    (IbsDonus, dict(carpan=1.0, ibs_max=0.4)),
]
VAKA_ID = [f"{c.__name__}-{i}" for i, (c, _) in enumerate(VAKALAR)]


@pytest.fixture(scope="module")
def veri():
    return sentetik()


# ------------------------------------------------------------------ kayıt / ızgara / csv
def test_kayit_15_sinif_ve_adlar():
    t = tum_portfoy_stratejileri()
    assert len(SINIFLAR) == 15 and len(t) == len(SINIFLAR) + len(EK_SINIFLAR) + len(V2_SINIFLAR) + len(V3_SINIFLAR) == 25
    assert all(ad.startswith(("pf__", "v3__")) and c.ad == ad for ad, c in t.items())


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda c: c.ad)
def test_izgara_en_cok_27_ve_gecerli(sinif):
    izg = sinif.parametre_izgarasi
    n = int(np.prod([len(x) for x in izg.values()]))
    assert 1 <= n <= 27
    assert set(izg) <= set(sinif.varsayilan_parametreler)
    assert "semboller" in sinif.varsayilan_parametreler and "atr_k" in sinif.varsayilan_parametreler


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda c: c.ad)
def test_izgara_uclari_kurulur_ve_calisir(sinif, veri):
    izg = sinif.parametre_izgarasi
    kw = {}
    if sinif is Pairs:
        kw = dict(ciftler=(("BTCUSDT", "ETHUSDT"), ("DK_AAPL", "DK_MSFT")))
    if sinif is ReferansFiltreliLong:
        kw = dict(semboller=("ETHUSDT", "SOLUSDT"))
    anahtar = list(izg)
    uclar = [dict(zip(anahtar, [izg[k][0] for k in anahtar])), dict(zip(anahtar, [izg[k][-1] for k in anahtar]))]
    for u in uclar:
        st = sinif(**{**kw, **u})
        h, s = st.sinyaller(veri)
        assert h.shape[0] == s.shape[0] > 0


def test_csv_baglantilari_tam():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    assert {"pf_sinif", "pf_ayar"} <= set(df.columns)
    kayitli = tum_portfoy_stratejileri()
    hedef = df[df["evrene_uyarlanabilir_mi"].isin(["evet", "kısmen"])]
    assert len(hedef) == 56
    for i, r in hedef.iterrows():
        if i in BAGLANAMAYAN:
            assert r["pf_sinif"] == "" and r["pf_ayar"].startswith("BAĞLANAMADI:") and len(r["pf_ayar"]) > 30
            continue
        adlar = [a.strip() for a in r["pf_sinif"].split("|")]
        assert adlar and all(a in kayitli for a in adlar), (i, r["ad"])
        ayarlar = json.loads(r["pf_ayar"])
        ayarlar = ayarlar if isinstance(ayarlar, list) else [ayarlar]
        assert len(ayarlar) == len(adlar)
    # hayır satırları boş
    assert (df.loc[df["evrene_uyarlanabilir_mi"] == "hayır", ["pf_sinif", "pf_ayar"]] == "").all().all()


def test_baglama_ayarlari_gecerli_parametre():
    kayitli = tum_portfoy_stratejileri()
    for b in BAGLAMA:
        st = kayitli[b["sinif"]](**b["ayar"])         # bilinmeyen parametre ValueError verir
        assert set(st.parametreler["semboller"]) <= set(HEPSI) | set(HISSE18) | {"DK_XAG"}   # ek2: karar 27 evreni


# ------------------------------------------------------------------ takvim
def test_donem_kimligi_ve_tetik_baslangictan_bagimsiz():
    eksen = pd.date_range("2024-01-29", periods=70, freq="D", tz="UTC")
    for t in ("D", "W", "M", "Q", "14"):
        kimlik = donem_kimligi(eksen, t)
        kimlik2 = donem_kimligi(eksen[10:], t)
        assert (kimlik[10:] == kimlik2).all()                       # veri başlangıcına bağlı değil
    gecerli = np.ones(len(eksen), dtype=bool)
    hafta = tetik_satirlari(eksen, "W", gecerli)
    assert hafta[0] and eksen[hafta][1].dayofweek == 0               # ilk geçerli satır + Pazartesi
    ay = tetik_satirlari(eksen, "M", gecerli)
    assert [t.day for t in eksen[ay][1:]] == [1, 1, 1]
    assert (tetik_satirlari(eksen, "14", gecerli).sum()) in (5, 6)


# ------------------------------------------------------------------ her strateji: lookahead / stop / motor
@pytest.mark.parametrize("sinif,kw", VAKALAR, ids=VAKA_ID)
def test_lookahead_yok_oneki_ayni(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    for gun in (350, 480):
        bitis = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=gun)
        h2, s2 = st.sinyaller(kes(veri, bitis))
        pd.testing.assert_frame_equal(h.loc[h2.index], h2, check_freq=False)
        pd.testing.assert_frame_equal(s.loc[s2.index], s2, check_freq=False)
    assert (h.notna() & (h != 0)).any(axis=1).sum() >= 0


@pytest.mark.parametrize("sinif,kw", VAKALAR, ids=VAKA_ID)
def test_gelecek_verisini_bozmak_gecmis_hedefi_degistirmez(sinif, kw, veri):
    """t'den sonraki fiyatları çarpıtmak (kesmekten güçlü) t'ye kadarki hedef ve stopları değiştirmez."""
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    t = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=400)
    boz = {}
    for k, d in veri.items():
        d2 = d.copy()
        son = d2.index > t
        d2.loc[son, ["acilis", "yuksek", "dusuk", "kapanis"]] *= np.linspace(1.0, 3.0, int(son.sum()))[:, None]
        d2.loc[son, "hacim"] *= 7.0
        boz[k] = d2
    h2, s2 = st.sinyaller(boz)
    pd.testing.assert_frame_equal(h.loc[:t], h2.loc[:t], check_freq=False)
    pd.testing.assert_frame_equal(s.loc[:t], s2.loc[:t], check_freq=False)


@pytest.mark.parametrize("sinif,kw", VAKALAR, ids=VAKA_ID)
def test_stop_zorunlu_dogru_tarafta_ve_motor_dumani(sinif, kw, veri):
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    ev = st.evren(veri)
    kap = pd.DataFrame({k: d["kapanis"] for k, d in ev.items()}).reindex(h.index).ffill()
    acik = h.notna() & (h != 0)
    if acik.to_numpy().any():
        sp = s.reindex(columns=h.columns)
        assert sp[acik].notna().to_numpy()[acik.to_numpy()].all(), "hedefi sıfırdan farklı satırda stop yok"
        yon = np.sign(h.ffill().fillna(0.0))
        ust = (yon > 0) & sp.notna()
        alt = (yon < 0) & sp.notna()
        assert (sp[ust] < kap[ust]).to_numpy()[ust.to_numpy()].all()
        assert (sp[alt] > kap[alt]).to_numpy()[alt.to_numpy()].all()
    r = portfoy_backtest(veri, st, PortfoyAyarlari())                   # sert limitler uygulanır
    assert np.isfinite(r.ozsermaye.to_numpy()).all() and r.ozsermaye.iloc[-1] > 0
    assert float(r.maruziyet["brut"].max()) <= 3.0 + 1e-6 or float(r.maruziyet_dolum.max()) <= 3.0 + 1e-6
    assert float(r.maruziyet_dolum.max()) <= 3.0 + 1e-6
    if len(r.islemler):
        assert r.islemler["cikis_zamani"].notna().all()


def test_atr_hazir_degilse_stopsuz_pozisyon_yok(veri):
    st = Rotasyon(lookback_gun=3, k=2, takvim="D", mutlak=False, atr_periyot=30)
    h, s = st.sinyaller(veri)
    acik = h.notna() & (h != 0)
    assert s[acik].notna().to_numpy()[acik.to_numpy()].all()


def test_alt_evren_ve_min_sembol(veri):
    st = Rotasyon(semboller=("BTCUSDT",))
    with pytest.raises(ValueError, match="en az 2 sembol"):
        st.hedefler(veri)
    st2 = Rotasyon(semboller=("BTCUSDT", "YOK1"))
    assert not st2.uygun_mu(veri)
    assert Rotasyon(semboller=KRIPTO3).uygun_mu(veri)
    assert not Rotasyon(rejim_sembol="YOK2").uygun_mu(veri)


# ------------------------------------------------------------------ rotasyon özel
def _dogrusal(egimler, n=200, bas="2023-01-02"):
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC", name="zaman")
    v = {}
    for s, e in egimler.items():
        k = 100 * np.exp(e * np.arange(n))
        v[s] = pd.DataFrame({"acilis": k, "yuksek": k * 1.01, "dusuk": k * 0.99, "kapanis": k, "hacim": 1.0}, index=idx)
    return v


def test_rotasyon_en_guclu_k_secilir_elle():
    v = _dogrusal({"A": 0.001, "B": 0.004, "C": 0.002, "D": -0.001})
    h, _ = Rotasyon(semboller=tuple(v), lookback_gun=30, k=2, takvim="M", mutlak=True).sinyaller(v)
    ilk = h.dropna(how="all")
    assert ilk.iloc[0].to_dict() == {"A": 0.0, "B": 0.5, "C": 0.5, "D": 0.0}
    h1, _ = Rotasyon(semboller=tuple(v), lookback_gun=30, k=1, takvim="M").sinyaller(v)
    assert h1.dropna(how="all").iloc[0].to_dict() == {"A": 0.0, "B": 1.0, "C": 0.0, "D": 0.0}


def test_rotasyon_mutlak_momentum_negatifse_nakit():
    v = _dogrusal({"A": -0.001, "B": -0.004})
    h, _ = Rotasyon(semboller=("A", "B"), lookback_gun=30, k=1, takvim="M", mutlak=True).sinyaller(v)
    assert (h.dropna(how="all").fillna(0) == 0).all().all()
    h2, _ = Rotasyon(semboller=("A", "B"), lookback_gun=30, k=1, takvim="M", mutlak=False).sinyaller(v)
    assert h2.dropna(how="all").iloc[0].to_dict() == {"A": 1.0, "B": 0.0}              # en az kötü


def test_rotasyon_siralama_kapanmis_barlardan_yapilir():
    """Yeniden dengeleme satırı t'de sıralama t'nin kapanışına KADAR olan veriyle yapılır: t+1'deki sıçrama etkisiz,
    t'deki sıçrama (kapanmış bar) etkili."""
    v = _dogrusal({"A": 0.001, "B": 0.0015, "C": 0.0005})
    st = Rotasyon(semboller=("A", "B", "C"), lookback_gun=30, k=1, takvim="M", mutlak=False)
    h0, _ = st.sinyaller(v)
    t = h0.dropna(how="all").index[1]                                # ikinci aylık yeniden dengeleme satırı
    assert h0.loc[t].idxmax() == "B"

    def sicrat(gun, sembol, oran):
        d = {k: x.copy() for k, x in v.items()}
        d[sembol].loc[d[sembol].index >= gun, ["acilis", "yuksek", "dusuk", "kapanis"]] *= oran
        return d

    h_sonra, _ = st.sinyaller(sicrat(t + pd.Timedelta(days=1), "C", 5.0))      # t+1'de sıçrama: t'de etkisiz
    assert h_sonra.loc[t].idxmax() == "B"
    h_ayni, _ = st.sinyaller(sicrat(t, "C", 5.0))                              # t'de (kapanmış bar) sıçrama: seçim değişir
    assert h_ayni.loc[t].idxmax() == "C"


def test_gem_riskli_negatifse_savunma_veya_nakit():
    v = _dogrusal({"R1": -0.002, "R2": -0.001, "S": 0.0005})
    h, _ = Gem(semboller=("R1", "R2", "S"), savunma=("S",), lookback_gun=30, takvim="M").sinyaller(v)
    assert h.dropna(how="all").iloc[0].to_dict() == {"R1": 0.0, "R2": 0.0, "S": 1.0}
    h2, _ = Gem(semboller=("R1", "R2"), savunma=(), lookback_gun=30, takvim="M").sinyaller(v)
    assert (h2.dropna(how="all").fillna(0) == 0).all().all()                       # nakit


# ------------------------------------------------------------------ pairs
def koentegre(n=700, beta=1.5, seed=5, bas="2022-01-03", sapma=0.0):
    """ln A rastgele yürüyüş, ln B = (ln A - ar1_spread)/beta -> spread (ln A - beta ln B) durağan AR(1)."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC", name="zaman")
    la = np.cumsum(rng.normal(0, 0.012, n)) + 4.0
    sp = np.zeros(n)
    for t in range(1, n):
        sp[t] = 0.85 * sp[t - 1] + rng.normal(0, 0.03)
    if sapma:
        sp[500:] += np.linspace(0, sapma, n - 500)             # kopma: spread sürekli açılır
    lb = (la - sp) / beta
    v = {}
    for ad, l in (("A", la), ("B", lb)):
        k = np.exp(l)
        v[ad] = pd.DataFrame({"acilis": k, "yuksek": k * 1.004, "dusuk": k * 0.996, "kapanis": k, "hacim": 1.0}, index=idx)
    return v


def test_adf_johansen_kalman_istatistikleri():
    rng = np.random.default_rng(1)
    dur = np.zeros(400)
    for t in range(1, 400):
        dur[t] = 0.5 * dur[t - 1] + rng.normal()
    yur = np.cumsum(rng.normal(size=400))
    assert adf_t(dur, 1) < -3.34
    assert adf_t(yur, 1) > -3.34
    v = koentegre(3000)
    la, lb = np.log(v["A"]["kapanis"].to_numpy()), np.log(v["B"]["kapanis"].to_numpy())
    iz, beta = johansen_iki(np.column_stack([la, lb]))
    assert iz > 15.4943 and beta == pytest.approx(1.5, abs=0.15)
    iz2, _ = johansen_iki(np.column_stack([np.cumsum(rng.normal(size=400)), np.cumsum(rng.normal(size=400))]))
    assert iz2 < 15.4943
    a, b, res = ols_cizgi(lb, la)
    assert b == pytest.approx(1.5, abs=0.15) and abs(res.mean()) < 1e-9
    # Kalman: spread beyaz gürültüyse beta gerçek değere yakınsar; hata yalnız önceki bilgiyle hesaplanır
    n = 3000
    lb2 = np.cumsum(rng.normal(0, 0.012, n)) + 4
    la2 = 1.5 * lb2 + 0.7 + rng.normal(0, 0.02, n)
    e, sq, bt = kalman_hata(la2, lb2, 1e-5, 4e-4, 40)
    assert bt[-1] == pytest.approx(1.5, abs=0.15) and np.isfinite(e).all()
    e2, _, bt2 = kalman_hata(la2[:1500], lb2[:1500], 1e-5, 4e-4, 40)
    assert np.allclose(e[:1500], e2) and np.allclose(bt[:1500], bt2)                    # nedensel


@pytest.mark.parametrize("yontem", ["eg", "johansen", "kalman", "mesafe"])
def test_pairs_hedge_orani_yalniz_gecmisten(yontem):
    v = koentegre()
    kw = dict(semboller=("A", "B"), ciftler=(("A", "B"),), yontem=yontem, pencere=120, giris_z=1.5, cikis_z=0.3,
              stop_z=6.0, max_tutma=60, brut_cift=0.6, beta_max=10.0)
    if yontem == "kalman":
        kw.update(pencere=40, giris_z=0.6, cikis_z=0.0)
    st = Pairs(**kw)
    h, s = st.sinyaller(v)
    girisler = h[(h["A"].notna()) & (h["A"] != 0)]
    assert len(girisler) >= 1, "koentegre sentetik çiftte hiç giriş yok"
    # her girişte |wA| + |wB| = brut_cift ve bacaklar zıt işaretli (beta > 0)
    t0 = girisler.index[0]
    toplam = h.loc[t0, "A"].__abs__() + h.loc[t0, "B"].__abs__()
    assert toplam == pytest.approx(0.6, abs=1e-9)
    assert np.sign(h.loc[t0, "A"]) == -np.sign(h.loc[t0, "B"])
    # gelecek verisi bozulunca t0'a kadarki hedefler değişmez (hedge oranı geçmişten)
    bozuk = {k: d.copy() for k, d in v.items()}
    for d in bozuk.values():
        d.loc[d.index > t0, ["acilis", "yuksek", "dusuk", "kapanis"]] *= 2.5
    h2, _ = st.sinyaller(bozuk)
    pd.testing.assert_frame_equal(h.loc[:t0], h2.loc[:t0], check_freq=False)
    # eg: giriş ağırlığı, t0'da biten pencereden OLS beta'sıyla elle hesaplanan orana uyar
    if yontem == "eg":
        w = 120
        gun_no = (v["A"].index - pd.Timestamp("1970-01-01", tz="UTC")).days.to_numpy()
        poz0 = v["A"].index.get_loc(t0)
        test_gunu = max(i for i in range(w - 1, poz0 + 1) if i == w - 1 or gun_no[i] % 5 == 0)
        ila = np.log(v["A"]["kapanis"].to_numpy()[test_gunu - w + 1:test_gunu + 1])
        ilb = np.log(v["B"]["kapanis"].to_numpy()[test_gunu - w + 1:test_gunu + 1])
        oran = abs(h.loc[t0, "B"]) / abs(h.loc[t0, "A"])
        assert oran == pytest.approx(ols_cizgi(ilb, ila)[1], rel=1e-9)         # beta = son test gününde biten pencerenin OLS'i
    # motor: her bacağa stop
    ust = h.ffill().fillna(0.0)
    assert s[(ust != 0) & h.notna()].notna().to_numpy()[((ust != 0) & h.notna()).to_numpy()].all()


def test_pairs_z_stop_iki_bacagi_da_kapatir_ve_kointegrasyon_kaybi():
    v = koentegre(sapma=1.2)
    st = Pairs(semboller=("A", "B"), ciftler=(("A", "B"),), yontem="eg", pencere=120, giris_z=1.5, cikis_z=0.3,
               stop_z=3.0, max_tutma=400, brut_cift=0.6, test_aralik=5, beta_max=10.0)
    h, _ = st.sinyaller(v)
    poz = h.ffill().fillna(0.0)
    # kopma sonrası (satır 500+): pozisyon açıksa kapanır; son satırlarda bacaklar sıfır olur ya da pozisyon yok
    assert (poz.iloc[-1] == 0).all()
    assert np.allclose(poz["A"] * poz["B"] <= 0, True)                 # bacaklar zıt yönlü (ya da sıfır)


def test_pairs_olmayan_cift_hata_ve_uygun_degil(veri):
    st = Pairs(ciftler=(("YOK", "BTCUSDT"),))
    assert not st.uygun_mu(veri)
    with pytest.raises(ValueError):
        st.sinyaller(veri)


# ------------------------------------------------------------------ diğer sınıflara özel
def test_sabit_sepet_sapma_yeniden_dengeler_ve_sabit_agirlik():
    v = _dogrusal({"A": 0.003, "B": 0.0, "C": 0.0})
    h, _ = SabitSepet(semboller=("A", "B", "C"), agirlik="esit", takvim="yok", sapma=0.05).sinyaller(v)
    em = h.dropna(how="all")
    assert em.iloc[0].tolist() == pytest.approx([1 / 3] * 3)
    assert len(em) > 2                                                  # A uçunca sapma tetiklenir
    h2, _ = SabitSepet(semboller=("A", "B", "C"), agirlik="sabit", agirliklar=(0.5, 0.3, 0.2), takvim="yok",
                       sapma=0.0).sinyaller(v)
    em2 = h2.dropna(how="all")
    assert len(em2) == 1 and em2.iloc[0].tolist() == pytest.approx([0.5, 0.3, 0.2])


def test_btc_hedge_sma_alti_net_duz_ve_hedge_short():
    n = 150
    idx = pd.date_range("2023-01-02", periods=n, freq="D", tz="UTC", name="zaman")
    kb = np.r_[np.linspace(100, 160, 100), np.linspace(160, 100, 50)]
    v = {}
    for s, k in (("BTCUSDT", kb), ("ETHUSDT", kb * 0.5)):
        v[s] = pd.DataFrame({"acilis": k, "yuksek": k * 1.01, "dusuk": k * 0.99, "kapanis": k, "hacim": 1.0}, index=idx)
    h, _ = BtcHedge(semboller=("BTCUSDT", "ETHUSDT"), sma_gun=20).sinyaller(v)
    son = h.ffill().iloc[-1]
    assert son["BTCUSDT"] == 0.0                                       # SMA altı: net düz
    h2, _ = BtcHedge(semboller=("BTCUSDT", "ETHUSDT"), sma_gun=20, hedge_sembol="ETHUSDT", hedge_orani=0.5).sinyaller(v)
    son2 = h2.ffill().iloc[-1]
    assert son2["BTCUSDT"] == 1.0 and son2["ETHUSDT"] == -0.5


def test_wq_alfa_kesitsel_rank_zaman_boyunca_degil():
    """rank kesitte: tek bir günün alfa sıralaması başka günlerin verisine bağlı değildir (kaynak hatasının düzeltmesi)."""
    v = sentetik(200, semb=("BTCUSDT", "ETHUSDT", "SOLUSDT"))
    st = WqAlfa(alfa=101, semboller=KRIPTO3)
    h, _ = st.sinyaller(v)
    t = h.dropna(how="all").index[50]
    v2 = {k: d.copy() for k, d in v.items()}
    for d in v2.values():
        d.loc[d.index < t, ["acilis", "yuksek", "dusuk", "kapanis"]] *= 3.0           # geçmiş fiyat düzeyini değiştir
    # alfa 101 tek günlük (kapanış-açılış)/(yüksek-düşük) oranı olduğundan ölçek değişimi sıralamayı değiştirmez
    h2, _ = st.sinyaller(v2)
    assert np.allclose(h.loc[t].to_numpy(), h2.loc[t].to_numpy(), atol=1e-3)
    assert abs(h.loc[t].abs().sum() - 1.0) < 1e-9 and abs(h.loc[t].sum()) < 1e-9       # rank-nötr, brüt 1


def test_kesit_ls_k_evrene_kisilir_ve_bacaklar_ayri():
    v = _dogrusal({"A": 0.003, "B": 0.001, "C": -0.001, "D": -0.003})
    h, _ = KesitLS(semboller=tuple(v), skor="getiri", lookback_gun=30, k=5, takvim="M", agirlik="esit").sinyaller(v)
    ilk = h.dropna(how="all").iloc[0]
    assert ilk["A"] == pytest.approx(0.25) and ilk["B"] == pytest.approx(0.25)
    assert ilk["C"] == pytest.approx(-0.25) and ilk["D"] == pytest.approx(-0.25)    # k=5 -> n//2=2
    h2, _ = KesitLS(semboller=tuple(v), skor="getiri", lookback_gun=30, k=1, takvim="M", agirlik="esit").sinyaller(v)
    ilk2 = h2.dropna(how="all").iloc[0]
    assert ilk2.to_dict() == {"A": 0.5, "B": 0.0, "C": 0.0, "D": -0.5}
