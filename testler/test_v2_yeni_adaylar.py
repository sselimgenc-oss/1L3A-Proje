"""v2 yeni adayları (ON_KAYIT_V2 2.8): sınıf içi kesitsel L/S (pf__sinif_kesit_mom/donus), yavaş TSMOM (v2__tsmom-*),
funding sinyalleri (v2__funding-*, v2__trend-funding-suzgec). YALNIZ sentetik veri; gerçek veri/sonuç açılmaz."""
import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import V2_SINIFLAR, tum_portfoy_stratejileri
from motor.portfoy.stratejiler.sinif_ici import SinifIciKesitDonus, SinifIciKesitMom
from motor.strateji import kayit
from motor.strateji.dis.v2_ek import (FundingAsiriKontra, FundingEsikKarsit, Tsmom121, TsmomOy, TrendFundingSuzgec,
                                      gecmis_kapanis)
from motor.strateji.funding import SUTUN, FundingYokHatasi, funding_sutunu_ekle, stratejiye_hazirla
from testler.test_daytrade import mumlar_kapanistan
from testler.test_portfoy_stratejiler import kes, sentetik

TEK_GRAFIK = (Tsmom121, TsmomOy, FundingAsiriKontra, FundingEsikKarsit, TrendFundingSuzgec)


# ================================================================== kayıt / kalite kapısı
def test_kayit_ve_dogrula():
    assert kayit.dogrula() == []
    reg = kayit.tum_stratejiler()
    for s in TEK_GRAFIK:
        assert reg[s.ad] is s and s.stil == "swing" and s().cikis_var_mi()
        n = int(np.prod([len(x) for x in s.parametre_izgarasi.values()]))
        assert 1 <= n <= 27
    pf = tum_portfoy_stratejileri()
    assert all(pf[c.ad] is c for c in V2_SINIFLAR) and len(V2_SINIFLAR) == 2


def test_funding_bayragi():
    assert [s.funding_gerekli for s in TEK_GRAFIK] == [False, False, True, True, True]


# ================================================================== kesitsel L/S (portföy)
def _dogrusal(egimler, n=200, bas="2023-01-02"):
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC", name="zaman")
    v = {}
    for s, e in egimler.items():
        k = 100 * np.exp(e * np.arange(n))
        v[s] = pd.DataFrame({"acilis": k, "yuksek": k * 1.01, "dusuk": k * 0.99, "kapanis": k, "hacim": 1.0}, index=idx)
    return v


EGIM = {"BTCUSDT": 0.001, "ETHUSDT": 0.004, "SOLUSDT": -0.002, "DK_XAU": 0.0005, "DK_WTI": -0.003, "DK_COPPER": 0.002}


def test_mom_siniflar_ayri_siralanir_elle():
    v = _dogrusal(EGIM)
    h, _ = SinifIciKesitMom(lookback_gun=30, atla_gun=0, takvim="M").sinyaller(v)
    w = h.dropna(how="all").iloc[0].to_dict()
    # iki geçerli sınıf (kripto, emtia): bacak başı 1/2 x 1/2 = 0.25; her sınıfta en iyi long, en kötü short, orta 0
    assert w == pytest.approx({"BTCUSDT": 0.0, "ETHUSDT": 0.25, "SOLUSDT": -0.25,
                               "DK_XAU": 0.0, "DK_COPPER": 0.25, "DK_WTI": -0.25})
    assert sum(w.values()) == pytest.approx(0.0)                       # dolar-nötr
    assert sum(abs(x) for x in w.values()) == pytest.approx(1.0)       # brüt = brut


def test_donus_kaybeden_long_kazanan_short():
    v = _dogrusal(EGIM)
    h, _ = SinifIciKesitDonus(lookback_gun=7, takvim="W").sinyaller(v)
    w = h.dropna(how="all").iloc[0].to_dict()
    assert w["SOLUSDT"] > 0 and w["ETHUSDT"] < 0 and w["DK_WTI"] > 0 and w["DK_COPPER"] < 0
    assert w["BTCUSDT"] == 0 and w["DK_XAU"] == 0


def test_tek_gecerli_sinif_brut_tam_kullanir_ve_tek_semboll_sinif_atlanir():
    v = {k: x for k, x in _dogrusal(EGIM).items() if k != "DK_WTI" and k != "DK_COPPER"}   # emtia: 1 sembol -> atlanır
    h, _ = SinifIciKesitMom(lookback_gun=30, atla_gun=0, takvim="M").sinyaller(v)
    w = h.dropna(how="all").iloc[0].to_dict()
    assert w == pytest.approx({"BTCUSDT": 0.0, "ETHUSDT": 0.5, "SOLUSDT": -0.5, "DK_XAU": 0.0})


def test_yedi_sembollu_sinifta_k_iki():
    egim = {f"DK_{x}": e for x, e in zip(["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
                                          [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007])}
    h, _ = SinifIciKesitMom(lookback_gun=30, atla_gun=0, takvim="M").sinyaller(_dogrusal(egim))
    w = h.dropna(how="all").iloc[0]
    assert (w > 0).sum() == 2 and (w < 0).sum() == 2
    assert set(w[w > 0].index) == {"DK_TSLA", "DK_META"} and set(w[w < 0].index) == {"DK_AAPL", "DK_MSFT"}


@pytest.mark.parametrize("sinif", V2_SINIFLAR, ids=lambda c: c.ad)
def test_pf_ongoru_varsayilan_aciklamali_ve_short_acar(sinif):
    st = sinif()
    p = st.parametreler
    assert p["takvim"] in ("M", "W") and "semboller" in p and p["atr_k"] > 0
    veri = sentetik(n=620)
    h, s = st.sinyaller(veri)
    acik = h.fillna(0.0)
    assert (acik > 0).to_numpy().any() and (acik < 0).to_numpy().any()          # long VE short taraf


@pytest.mark.parametrize("sinif,kw", [(SinifIciKesitMom, {}), (SinifIciKesitMom, dict(lookback_gun=90, atla_gun=0)),
                                      (SinifIciKesitDonus, {}), (SinifIciKesitDonus, dict(lookback_gun=3, takvim="D"))],
                         ids=lambda x: getattr(x, "__name__", ""))
def test_pf_lookahead_stop_motor(sinif, kw):
    veri = sentetik(n=620)
    st = sinif(**kw)
    h, s = st.sinyaller(veri)
    for gun in (350, 480):                                                      # (a) kesme
        bitis = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=gun)
        h2, s2 = st.sinyaller(kes(veri, bitis))
        pd.testing.assert_frame_equal(h.loc[h2.index], h2, check_freq=False)
        pd.testing.assert_frame_equal(s.loc[s2.index], s2, check_freq=False)
    t = pd.Timestamp("2021-01-01", tz="UTC") + pd.Timedelta(days=400)           # (b) geleceği çarpıtma
    boz = {}
    for k, d in veri.items():
        d2 = d.copy()
        son = d2.index > t
        d2.loc[son, ["acilis", "yuksek", "dusuk", "kapanis"]] *= np.linspace(1.0, 3.0, int(son.sum()))[:, None]
        boz[k] = d2
    h3, s3 = st.sinyaller(boz)
    pd.testing.assert_frame_equal(h.loc[:t], h3.loc[:t], check_freq=False)
    pd.testing.assert_frame_equal(s.loc[:t], s3.loc[:t], check_freq=False)
    # stop zorunlu ve doğru tarafta (long: altında, short: üstünde)
    ev = st.evren(veri)
    kap = pd.DataFrame({k: d["kapanis"] for k, d in ev.items()}).reindex(h.index).ffill()
    acik = h.notna() & (h != 0)
    assert s[acik].notna().to_numpy()[acik.to_numpy()].all()
    yon = np.sign(h.ffill().fillna(0.0))
    ust, alt = (yon > 0) & s.notna(), (yon < 0) & s.notna()
    assert (s[ust] < kap[ust]).to_numpy()[ust.to_numpy()].all() and (s[alt] > kap[alt]).to_numpy()[alt.to_numpy()].all()
    r = portfoy_backtest(veri, st, PortfoyAyarlari())                           # sert limitler uygulanır
    assert np.isfinite(r.ozsermaye.to_numpy()).all() and float(r.maruziyet_dolum.max()) <= 3.0 + 1e-6


@pytest.mark.parametrize("sinif", V2_SINIFLAR, ids=lambda c: c.ad)
def test_pf_izgara_uclari_calisir(sinif):
    veri = sentetik(n=500)
    izg = sinif.parametre_izgarasi
    anahtar = list(izg)
    for i in (0, -1):
        h, s = sinif(**{k: izg[k][i] for k in anahtar}).sinyaller(veri)
        assert h.shape == s.shape and h.shape[0] > 0


# ================================================================== TSMOM (tek grafik, long + short)
def _fiyat(egim, n=700, seed=1, gurultu=0.004):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(egim * np.arange(n) + np.cumsum(rng.normal(0, gurultu, n)))


def _gun_mum(kap, **kw):
    return mumlar_kapanistan(kap, genlik=0.3, baslangic="2020-01-01", freq="1D", **kw)


def test_gecmis_kapanis_nedensel_ve_bosluk():
    idx = pd.DatetimeIndex(["2022-01-03", "2022-01-04", "2022-01-07", "2022-01-10"], tz="UTC")
    k = pd.Series([1.0, 2.0, 3.0, 4.0], index=idx)
    g = gecmis_kapanis(k, 3)
    assert np.isnan(g.iloc[0]) and np.isnan(g.iloc[1])
    assert g.iloc[2] == 2.0            # 01-04 (t-3g) mevcut
    assert g.iloc[3] == 3.0            # 01-07 (t-3g) mevcut
    assert gecmis_kapanis(k, 4).iloc[2] == 1.0 and (gecmis_kapanis(k, 0) == k).all()
    assert gecmis_kapanis(k, 2).iloc[3] == 3.0                    # 01-08 yok -> en son bilinen (01-07)


@pytest.mark.parametrize("sinif", (Tsmom121, TsmomOy), ids=lambda c: c.ad)
def test_tsmom_long_ve_short_ve_stop(sinif):
    st = sinif()
    yuk, dus = _gun_mum(_fiyat(0.004)), _gun_mum(_fiyat(-0.004))
    sy, sd = st.sinyaller(yuk), st.sinyaller(dus)
    assert (sy["yon"].iloc[:300] == 0).all() and (sd["yon"].iloc[:300] == 0).all()           # 365g hazır olmadan sinyal yok
    assert sy["yon"].iloc[-1] == 1 and sd["yon"].iloc[-1] == -1                                # long ve SHORT
    assert not (sy["yon"] == -1).any() or (sy["yon"] == 1).sum() > (sy["yon"] == -1).sum()
    for m, s in ((yuk, sy), (dus, sd)):
        acik = s["yon"] != 0
        assert s.loc[acik, "stop"].notna().all()
        assert (s.loc[s["yon"] == 1, "stop"] < m.loc[s["yon"] == 1, "kapanis"]).all()
        assert (s.loc[s["yon"] == -1, "stop"] > m.loc[s["yon"] == -1, "kapanis"]).all()
    assert sy["cikis_short"].iloc[-1] and not sy["cikis_long"].iloc[-1]
    assert sd["cikis_long"].iloc[-1] and not sd["cikis_short"].iloc[-1]
    uzun_yalniz = sinif(short=False).sinyaller(dus)
    assert (uzun_yalniz["yon"] >= 0).all()


def test_tsmom121_elle_skor_12_1():
    m = _gun_mum(_fiyat(0.002, n=500))
    s = Tsmom121().skor(m)
    t = m.index[450]
    beklenen = m["kapanis"].loc[t - pd.Timedelta(days=30)] / m["kapanis"].loc[t - pd.Timedelta(days=365)] - 1
    assert s.loc[t] == pytest.approx(beklenen)


def test_tsmom_oy_cogunluk():
    # uzun vade (365g) yukarı, son 30g ve 90g aşağı -> 2 aşağı oyu 1 yukarı oyu yener -> short
    n = 700
    kap = np.r_[np.linspace(100, 300, n - 120), np.linspace(300, 250, 120)]
    m = _gun_mum(kap)
    o = TsmomOy().oy(m)
    assert o.iloc[-1] == pytest.approx(-1 / 3)
    assert TsmomOy().sinyaller(m)["yon"].iloc[-1] == -1


@pytest.mark.parametrize("sinif", (Tsmom121, TsmomOy), ids=lambda c: c.ad)
def test_tsmom_lookahead_yok(sinif):
    st = sinif()
    m = _gun_mum(_fiyat(0.0005, n=900, seed=7, gurultu=0.02))
    tam = st.sinyaller(m)
    assert tam["yon"].abs().sum() > 0
    for n in (500, 700):
        pd.testing.assert_frame_equal(tam.iloc[:n], st.sinyaller(m.iloc[:n]), check_freq=False)
    boz = m.copy()
    boz.iloc[600:, boz.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    pd.testing.assert_frame_equal(tam.iloc[:600], st.sinyaller(boz).iloc[:600], check_freq=False)


@pytest.mark.parametrize("sinif", (Tsmom121, TsmomOy), ids=lambda c: c.ad)
def test_tsmom_motor_dumani_iki_yon(sinif):
    n = 1500
    kap = np.r_[_fiyat(0.003, n=700), _fiyat(-0.003, n=800, seed=2) * (_fiyat(0.003, n=700)[-1] / 100)]
    r = backtest(_gun_mum(kap), sinif(), MotorAyarlari(limit_modu="olc"))
    yonler = set(r.islemler["yon"]) if "yon" in r.islemler.columns else None
    assert len(r.islemler) > 0
    if yonler is not None:
        assert yonler == {1, -1} or yonler == {"long", "short"} or len(yonler) == 2


# ================================================================== funding sinyalleri
def _fund(n_gun, ofset=None, spike=(), baz=0.0001, gurultu=0.00002, seed=3):
    """8 saatlik funding; spike = [(gun_bas, gun_son, oran), ...]."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n_gun * 3, freq="8h", tz="UTC", name="zaman")
    oran = baz + gurultu * rng.standard_normal(len(idx))
    for b, s, o in spike:
        oran[b * 3:s * 3] = o
    return pd.DataFrame({"oran": oran}, index=idx)


def _girdi(egim=0.0, n=600, seed=1, spike=()):
    m = _gun_mum(_fiyat(egim, n=n, seed=seed))
    f = _fund(n + 5, spike=spike)
    return funding_sutunu_ekle(m, f, "1d"), f


SPIKE = [(300, 306, 0.002), (450, 456, -0.001)]


def test_funding_asiri_kontra_short_ve_long():
    m, _ = _girdi(spike=SPIKE)
    s = FundingAsiriKontra().sinyaller(m)
    ust = s.loc["2020-10-27":"2020-11-02"]           # gün 300-306
    alt = s.loc["2021-03-27":"2021-04-02"]           # gün 450-456
    assert (ust["yon"] == -1).any() and not (ust["yon"] == 1).any()          # yüksek funding -> SHORT
    assert (alt["yon"] == 1).any() and not (alt["yon"] == -1).any()          # negatif funding -> LONG
    acik = s["yon"] != 0
    assert s.loc[acik, "stop"].notna().all()
    assert (s.loc[s["yon"] == 1, "stop"] < m.loc[s["yon"] == 1, "kapanis"]).all()
    assert (s.loc[s["yon"] == -1, "stop"] > m.loc[s["yon"] == -1, "kapanis"]).all()
    assert s.loc[acik, "zaman_cikisi_mum"].eq(20.0).all()                    # 20 gün zaman çıkışı (1d mum)
    assert (FundingAsiriKontra(short=False).sinyaller(m)["yon"] >= 0).all()


def test_funding_esik_karsit_short_ve_long():
    m, _ = _girdi(spike=SPIKE)
    s = FundingEsikKarsit().sinyaller(m)
    assert (s.loc["2020-10-27":"2020-11-05", "yon"] == -1).any()
    assert (s.loc["2021-03-27":"2021-04-05", "yon"] == 1).any()
    # taban funding (~%11 yıllık) eşiklerin içinde: spike'tan uzakta sinyal yok
    assert (s.loc["2020-04-01":"2020-09-30", "yon"] == 0).all()
    acik = s["yon"] != 0
    assert s.loc[acik, "stop"].notna().all()
    assert (s.loc[s["yon"] == -1, "stop"] > m.loc[s["yon"] == -1, "kapanis"]).all()


def test_trend_funding_suzgec_degismezleri():
    m, _ = _girdi(egim=0.0004, seed=4, spike=[(250, 300, 0.002)])
    st = TrendFundingSuzgec()
    s = st.sinyaller(m)
    from motor.strateji.dis.v2_ek import _funding_z
    z = _funding_z(m, st.ad, 90, 0)
    sma = m["kapanis"].rolling(100, min_periods=100).mean()
    uzun, kisa = s["yon"] == 1, s["yon"] == -1
    assert uzun.any()
    assert (m.loc[uzun, "kapanis"] > sma[uzun]).all() and (z[uzun] < 1.0).all()           # trend + kalabalık değil
    assert (m.loc[kisa, "kapanis"] < sma[kisa]).all() and (z[kisa] > -1.0).all()
    # funding kalabalıkken (z >= 1) uzun açılmaz: kontrolün anlamlı olması için en az bir z >= 1 ve kapanış > SMA barı olmalı
    assert ((z >= 1.0) & (m["kapanis"] > sma)).any()
    # short tarafı: düşen fiyat -> short
    md, _ = _girdi(egim=-0.0015, seed=5)
    sd = st.sinyaller(md)
    assert (sd["yon"] == -1).any()
    acik = sd["yon"] != 0
    assert sd.loc[acik, "stop"].notna().all() and (sd.loc[sd["yon"] == -1, "stop"] > md.loc[sd["yon"] == -1, "kapanis"]).all()
    assert (st.yeni(short=False).sinyaller(md)["yon"] >= 0).all()


@pytest.mark.parametrize("sinif", (FundingAsiriKontra, FundingEsikKarsit, TrendFundingSuzgec), ids=lambda c: c.ad)
def test_funding_lookahead_yok(sinif):
    m_ham = _gun_mum(_fiyat(0.0005, n=700, seed=9, gurultu=0.02))
    f = _fund(705, spike=[(300, 306, 0.002), (450, 456, -0.001), (600, 606, 0.002)])
    st = sinif()
    m = funding_sutunu_ekle(m_ham, f, "1d")
    tam = st.sinyaller(m)
    assert (tam["yon"] != 0).any()
    t = m.index[500]
    # (a) gelecekteki funding'i boz -> t'ye kadar aynı
    f2 = f.copy()
    f2.loc[f2.index > t + pd.Timedelta(days=1), "oran"] = 0.01      # t barı t+1g kapanır: o ana dek funding meşru
    pd.testing.assert_frame_equal(tam.loc[:t], st.sinyaller(funding_sutunu_ekle(m_ham, f2, "1d")).loc[:t], check_freq=False)
    # (b) fiyat kesilince aynı
    pd.testing.assert_frame_equal(tam.iloc[:500], st.sinyaller(funding_sutunu_ekle(m_ham.iloc[:500], f, "1d")), check_freq=False)
    # (c) gelecek fiyatı boz
    boz = m_ham.copy()
    boz.iloc[500:, boz.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 3.0
    pd.testing.assert_frame_equal(tam.iloc[:500], st.sinyaller(funding_sutunu_ekle(boz, f, "1d")).iloc[:500], check_freq=False)


@pytest.mark.parametrize("sinif", (FundingAsiriKontra, FundingEsikKarsit, TrendFundingSuzgec), ids=lambda c: c.ad)
def test_funding_yoksa_acik_hata_sifir_varsayilmaz(sinif):
    m = _gun_mum(_fiyat(0.0, n=300))
    with pytest.raises(ValueError, match=SUTUN):
        sinif().sinyaller(m)                                    # sütun yok
    with pytest.raises(FundingYokHatasi):
        stratejiye_hazirla(sinif(), m, None, "DK_XAU", "1d")    # DK_ sembol: funding dosyası yok


@pytest.mark.parametrize("sinif", (FundingAsiriKontra, FundingEsikKarsit, TrendFundingSuzgec), ids=lambda c: c.ad)
def test_funding_motor_dumani(sinif):
    m, f = _girdi(egim=0.0006, n=900, seed=6, spike=[(300, 306, 0.002), (450, 456, -0.001), (600, 606, 0.002)])
    r = backtest(m, sinif(), MotorAyarlari(limit_modu="olc"), f)
    assert len(r.islemler) > 0


@pytest.mark.parametrize("sinif", TEK_GRAFIK, ids=lambda c: c.ad)
def test_izgara_uclari_calisir(sinif):
    m, _ = _girdi(spike=SPIKE) if sinif.funding_gerekli else (_gun_mum(_fiyat(0.002)), None)
    izg = sinif.parametre_izgarasi
    for i in (0, -1):
        out = sinif(**{k: izg[k][i] for k in izg}).sinyaller(m)
        assert len(out) == len(m)
