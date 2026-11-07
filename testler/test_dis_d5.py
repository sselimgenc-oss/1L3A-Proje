"""D5 (ek_77 belgesi) stratejileri: lookahead (üç kesit), stop tarafı, ızgara uçları, motor dumanı, seans (UTC gün / ABD DST),
Dual Thrust'ta bugünün barının aralığa girmediği, R-Breaker seviyelerinin önceki güne dayandığı, TSMOM'un 12 ay öncesine baktığı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis._gosterge_d5 import cti, kama, ott, seans_bilgi
from motor.strateji.dis.d5_ek import (
    ConnorsEtf, DualThrust, E0v1en, Ema50200Geri, GunIciDonus, IbsDonus, Ifr2, Ifr2GunIci, OttBantlari, RBreaker,
    SpartaWhb, Tsmom, ay_sonu_mumu, gecmis_getiri)
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar
from testler.test_dis_d4 import NY, abd_mumlari, is_gunleri

SINIFLAR = [Ifr2, Ifr2GunIci, OttBantlari, SpartaWhb, ConnorsEtf, Tsmom, IbsDonus, DualThrust, RBreaker,
            GunIciDonus, E0v1en, Ema50200Geri]
TF = {Ifr2: "4h", Ifr2GunIci: "1h", OttBantlari: "15min", SpartaWhb: "1h", ConnorsEtf: "1D", Tsmom: "1D",
      IbsDonus: "1D", DualThrust: "1h", RBreaker: "1h", GunIciDonus: "1h", E0v1en: "15min", Ema50200Geri: "4h"}
# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    OttBantlari: dict(ott_pct_long=0.3, ott_pct_short=0.3, bant_long=0.0005, bant_short=0.0005, ott_len_long=10,
                      ott_len_short=10, sinyal_len_short=10, max_risk_long=50.0, max_risk_short=50.0),
    SpartaWhb: dict(alti_n=1, sapma_min=0.0, sapma_maks=1.0, mum_maks=1.0, pb_ort_esik=-1000.0),
    E0v1en: dict(cti_esik=2.0, rsi4_esik=80.0, rsi14_alt=0.0, sma_k=1.2, yeni_rsi4=80.0, yeni_rsi14=0.0, yeni_sma_k=1.2),
}


def veri(sinif, n=None, seed=11):
    tf = TF[sinif]
    n = n or {"1D": 2500, "4h": 4500, "1h": 4000, "15min": 5000}[tf]
    return rastgele_mumlar(n, seed=seed, freq=tf, baslangic="2018-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif, {}), **ek})


# ---------------------------------------------------------------- kayıt / sözleşme
def test_kayit_ve_dogrula():
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.endswith("d5_ek")}
    assert kayitli == {c.ad for c in SINIFLAR}
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.ad.startswith("dis__") and s.cikis_var_mi() and s.stil in ("scalp", "daytrade", "swing")
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(sinif, n=1800)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = sinif(**{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


# ---------------------------------------------------------------- lookahead / stop tarafı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif)
    kisa = {"short": True} if "short" in sinif.varsayilan_parametreler else {}
    for s in (olustur(sinif), olustur(sinif, **kisa)):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    ek = {"short": True} if "short" in sinif.varsayilan_parametreler else {}
    sig = olustur(sinif, **ek).sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 0, f"{sinif.ad}: sinyal yok"
    assert giris.stop.notna().all()
    kap = df.kapanis
    l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
    assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
    h = giris.hedef.dropna()
    if len(h):
        yl = giris.loc[h.index]
        assert ((yl.yon == 1) & (h > kap[h.index]) | (yl.yon == -1) & (h < kap[h.index])).all()


def test_sparta_yalniz_short_ve_ust_tf_atlama():
    df = veri(SpartaWhb)
    sig = olustur(SpartaWhb).sinyaller(df)
    assert not (sig.yon == 1).any() and (sig.yon == -1).any()
    # 4h tabanda 2h/1h üst TF geçersiz: atlanır, hata vermez
    df4 = rastgele_mumlar(2500, seed=5, freq="4h", baslangic="2018-01-01")
    assert len(olustur(SpartaWhb).sinyaller(df4)) == len(df4)


@pytest.mark.parametrize("sinif", [s for s in SINIFLAR if s not in (Ifr2GunIci, DualThrust, RBreaker, GunIciDonus)],
                         ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(sinif, n=1800)
    ek = {"short": True} if "short" in sinif.varsayilan_parametreler else {}
    sonuc = backtest(df, olustur(sinif, **ek), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- göstergeler
def test_kama_ott_nedensel_ve_sabit_seri():
    x = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, 0.01, 800))))
    for f in (lambda s: kama(s, 20), lambda s: ott(kama(s, 20), 1.5)):
        tam = f(x)
        pdt.assert_series_equal(f(x.iloc[:500]), tam.iloc[:500])
    sabit = pd.Series(np.full(100, 50.0))
    assert np.allclose(kama(sabit, 10).dropna(), 50.0)
    o = ott(kama(sabit, 10), 2.0).dropna()
    assert len(o) > 0 and np.isfinite(o).all()


def test_cti_dogrusal_seri():
    yuk = pd.Series(np.arange(1.0, 101.0))
    assert np.allclose(cti(yuk, 20).dropna(), 1.0)
    assert np.allclose(cti(-yuk, 20).dropna(), -1.0)


# ---------------------------------------------------------------- Ifr2
def test_ifr2_cikis_onceki_iki_mum_zirvesi_ve_gun_sonu():
    df = veri(Ifr2)
    s = Ifr2(esik=20.0)
    sig = s.sinyaller(df)
    onc = df.yuksek.shift(1).rolling(2).max()
    assert (sig.cikis_long == (df.kapanis > onc).fillna(False)).all()
    g = Ifr2GunIci(esik=20.0).sinyaller(veri(Ifr2GunIci))
    d = veri(Ifr2GunIci)
    son = pd.Series(d.index.floor("D"), index=d.index).shift(-1) != pd.Series(d.index.floor("D"), index=d.index)
    son.iloc[-1] = False
    assert g.loc[son, "cikis"].all() and (g.loc[son, "yon"] == 0).all()


def test_ifr2_bulut_ustu_sart():
    """Düşen seride (kapanış bulutun altında) long yok; yükselen seride RSI2 dipleri long verir."""
    dus = mumlar_kapanistan(200 * 0.995 ** np.arange(600), genlik=0.3, freq="4h")
    assert not (Ifr2(esik=50.0).sinyaller(dus).yon == 1).any()
    rng = np.random.default_rng(3)
    yuk = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.01, 1200)))
    assert (Ifr2(esik=30.0).sinyaller(mumlar_kapanistan(yuk, genlik=0.2, freq="4h")).yon == 1).any()


# ---------------------------------------------------------------- Connors
def test_connors_uc_gun_senaryosu():
    kap = np.r_[100 * 1.003 ** np.arange(260), [None]].astype(float)[:-1]
    # son 4 gün: üst üste düşen tepe ve dip (yükseliş trendinde, SMA200 üstünde)
    kap = np.r_[kap, kap[-1] * np.array([0.995, 0.99, 0.985])]
    df = mumlar_kapanistan(kap, genlik=0.0, freq="1D")
    df.loc[df.index[-3:], "yuksek"] = df.yuksek.iloc[-4] - np.array([0.5, 1.0, 1.5])
    df.loc[df.index[-3:], "dusuk"] = df.dusuk.iloc[-4] - np.array([0.5, 1.0, 1.5]) * 2
    sig = ConnorsEtf(kural="uc_gun").sinyaller(df)
    assert sig.yon.iloc[-1] == 1 and sig.stop.iloc[-1] < df.kapanis.iloc[-1]
    # SMA200 filtresi: trend_n büyükse (veri yetmez) NaN -> sinyal yok
    assert (ConnorsEtf(kural="uc_gun", trend_n=400).sinyaller(df).yon == 0).all()


def test_connors_r3_ve_rsi4_kurallari_uretir_ve_kural_gecersiz():
    df = veri(ConnorsEtf)
    for kural, ek in (("r3", dict(r3_giris=30.0, r3_onceki=90.0)), ("rsi4", dict(rsi_giris=35.0))):
        sig = ConnorsEtf(kural=kural, trend_n=0, **ek).sinyaller(df)
        assert (sig.yon == 1).any() and (sig.yon == -1).any()
    with pytest.raises(ValueError):
        ConnorsEtf(kural="x").sinyaller(df)


def test_connors_trend_filtresi_yonu():
    df = veri(ConnorsEtf)
    sig = ConnorsEtf(kural="rsi4", rsi_giris=40.0, trend_n=200).sinyaller(df)
    sma = df.kapanis.rolling(200).mean()
    assert (df.kapanis[sig.yon == 1] > sma[sig.yon == 1]).all()
    assert (df.kapanis[sig.yon == -1] < sma[sig.yon == -1]).all()


# ---------------------------------------------------------------- TSMOM
def test_tsmom_12_ay_oncesine_bakar():
    idx = pd.date_range("2019-01-01", "2021-06-30", freq="1D", tz="UTC", name="zaman")
    kap = pd.Series(100.0, index=idx)
    r = gecmis_getiri(kap, 12)
    t = pd.Timestamp("2021-03-15", tz="UTC")
    assert r[t] == 0.0
    # 12 ay önceki fiyatı düşür -> getiri pozitif; yüksek yap -> negatif; 13/11 ay önceki fiyatın etkisi yok
    k2 = kap.copy()
    k2[pd.Timestamp("2020-03-15", tz="UTC")] = 50.0
    assert gecmis_getiri(k2, 12)[t] == pytest.approx(1.0)
    k3 = kap.copy()
    k3[pd.Timestamp("2020-02-15", tz="UTC")] = 50.0
    k3[pd.Timestamp("2020-04-15", tz="UTC")] = 50.0
    assert gecmis_getiri(k3, 12)[t] == 0.0
    # veri 12 ay öncesine uzanmıyorsa NaN
    assert np.isnan(r[pd.Timestamp("2019-12-31", tz="UTC")]) and not np.isnan(r[pd.Timestamp("2020-01-02", tz="UTC")])


def test_tsmom_ay_sonu_degerlendirme_ve_isaret_donunce_cikis():
    idx = pd.date_range("2018-01-01", periods=1400, freq="1D", tz="UTC", name="zaman")
    assert ay_sonu_mumu(idx).sum() == len(set(zip(idx.year, idx.month))) - 1 + (1 if idx[-1].is_month_end else 0) - 0
    # yükselen, sonra düşen seri: önce long, işaret dönünce long çıkışı ve short
    kap = np.r_[100 * 1.002 ** np.arange(700), 100 * 1.002 ** 700 * 0.997 ** np.arange(700)]
    df = mumlar_kapanistan(kap, genlik=0.5, freq="1D", baslangic="2018-01-01")
    sig = Tsmom().sinyaller(df)
    assert (sig.yon == 1).any() and (sig.yon == -1).any()
    ilk_short = sig.index[sig.yon == -1][0]
    assert ilk_short > df.index[700]
    assert sig.cikis_long.loc[ilk_short]
    # girişler yalnız ay sonu mumlarında
    ay_sonu = pd.Series(ay_sonu_mumu(df.index), index=df.index)
    assert ay_sonu[sig.yon != 0].all()
    assert (Tsmom(short=False).sinyaller(df).yon != -1).all()


def test_ay_sonu_mumu_nedensel():
    idx = pd.date_range("2020-01-25", periods=60, freq="1D", tz="UTC")
    tam = ay_sonu_mumu(idx)
    assert (tam[:35] == ay_sonu_mumu(idx[:35])).all()
    assert idx[tam].tolist() == [pd.Timestamp("2020-01-31", tz="UTC"), pd.Timestamp("2020-02-29", tz="UTC")]


# ---------------------------------------------------------------- IBS
def test_ibs_esik_ve_cikis():
    df = mumlar_kapanistan(np.full(50, 100.0), genlik=1.0, freq="1D")
    df.loc[df.index[30], ["acilis", "yuksek", "dusuk", "kapanis"]] = [100.0, 101.0, 95.0, 95.5]   # IBS ~0.08
    df.loc[df.index[34], ["acilis", "yuksek", "dusuk", "kapanis"]] = [100.0, 105.0, 99.0, 104.5]  # IBS ~0.92
    sig = IbsDonus().sinyaller(df)
    assert sig.yon.iloc[30] == 1 and sig.stop.iloc[30] < 95.5
    assert sig.cikis_long.iloc[34] and not sig.cikis_long.iloc[33]
    assert IbsDonus(short=True).sinyaller(df).yon.iloc[34] == -1
    z = IbsDonus(maks_tutma=3).sinyaller(df)
    assert z.zaman_cikisi_mum.iloc[30] == 3


# ---------------------------------------------------------------- Dual Thrust
def _gunleri_degistir(df, gun, carpan_yuk=1.5, carpan_dus=0.5):
    d = df.copy()
    m = d.index.floor("D") == pd.Timestamp(gun, tz="UTC")
    d.loc[m, "yuksek"] = d.loc[m, "yuksek"] * carpan_yuk
    d.loc[m, "dusuk"] = d.loc[m, "dusuk"] * carpan_dus
    return d, m


def test_dual_thrust_bugunun_bari_araliga_girmez():
    df = rastgele_mumlar(24 * 40, seed=8, freq="1h", baslangic="2022-01-01")
    s = DualThrust(n=4)
    ust0, alt0, hazir0, _ = s.seviyeler(df)
    d2, m = _gunleri_degistir(df, "2022-01-20")
    ust1, alt1, hazir1, _ = s.seviyeler(d2)
    # aynı gün: tetikler değişmedi (bugünün tepe/dibi aralığa girmiyor)
    pdt.assert_series_equal(ust0[m], ust1[m])
    pdt.assert_series_equal(alt0[m], alt1[m])
    # sonraki gün: değişti (artık "önceki seans" içinde)
    sonraki = df.index.floor("D") == pd.Timestamp("2022-01-21", tz="UTC")
    assert not np.allclose(ust0[sonraki], ust1[sonraki])
    # n+1 gün sonra etkisi biter (pencere dışı)
    uzak = df.index.floor("D") == pd.Timestamp("2022-01-25", tz="UTC")
    pdt.assert_series_equal(ust0[uzak], ust1[uzak])


def test_dual_thrust_formul_elle_hesap():
    df = rastgele_mumlar(24 * 12, seed=9, freq="1h", baslangic="2022-01-01")
    s = DualThrust(n=3, k1=0.4, k2=0.6)
    ust, alt, hazir, _ = s.seviyeler(df)
    gun = pd.Timestamp("2022-01-06", tz="UTC")
    onc = df[(df.index.floor("D") >= gun - pd.Timedelta(days=3)) & (df.index.floor("D") < gun)]
    hh, ll, hc, lc = onc.yuksek.max(), onc.dusuk.min(), onc.kapanis.max(), onc.kapanis.min()
    ar = max(hh - lc, hc - ll)
    acilis = df.loc[gun, "acilis"]
    m = df.index.floor("D") == gun
    assert np.allclose(ust[m], acilis + 0.4 * ar) and np.allclose(alt[m], acilis - 0.6 * ar)
    assert hazir[m].all() and not hazir[df.index.floor("D") < pd.Timestamp("2022-01-04", tz="UTC")].any()


def test_dual_thrust_tetik_yonleri_ve_cevirme():
    df = rastgele_mumlar(24 * 60, seed=12, freq="1h", baslangic="2022-01-01")
    s = DualThrust(n=3, k1=0.2, k2=0.2)
    sig = s.sinyaller(df)
    ust, alt, hazir, _ = s.seviyeler(df)
    long_g = sig[sig.yon == 1].index
    short_g = sig[sig.yon == -1].index
    assert len(long_g) > 0 and len(short_g) > 0
    assert (df.kapanis[long_g] > ust[long_g]).all() and (df.kapanis[short_g] < alt[short_g]).all()
    assert sig.cikis_long[short_g].all()
    kisa_kapali = DualThrust(n=3, k1=0.2, k2=0.2, short=False).sinyaller(df)
    assert not (kisa_kapali.yon == -1).any()


def _abd(n_gun=80, dk=15, seed=6, vol=0.002):
    return abd_mumlari(is_gunleri("2023-01-02", "2023-06-30")[:n_gun], dk, seed=seed, vol=vol)


def test_dual_thrust_abd_dst_acilis_ve_gece_pozisyonu_yok():
    df = abd_mumlari(is_gunleri("2023-02-01", "2023-05-15"), 15, seed=6, vol=0.003)
    s = DualThrust(seans="abd_hisse", n=3, k1=0.15, k2=0.15)
    sig = s.sinyaller(df)
    assert (sig.yon != 0).any()
    b = seans_bilgi(df, "abd_hisse")
    # seans açılışı = o günün 09:30 NY mumunun açılışı (DST'de UTC saati kayar)
    yerel = df.index.tz_convert(NY)
    ilk = (yerel.hour == 9) & (yerel.minute == 30)
    assert np.allclose(b["acilis"][ilk], df.acilis[ilk])
    r = backtest(df, s, MotorAyarlari())
    t = r.islemler
    assert len(t) > 5
    g1 = t.giris_zamani.dt.tz_convert(NY).dt.date
    g2 = t.cikis_zamani.dt.tz_convert(NY).dt.date
    assert (g1[t.cikis_nedeni != "kill_switch"] == g2[t.cikis_nedeni != "kill_switch"]).all()
    # seans sonuna iki mum kala yeni giriş yok
    son2 = yerel.strftime("%H:%M").isin(["15:30", "15:45"])
    assert (sig.loc[son2, "yon"] == 0).all()


def test_dual_thrust_utc_gun_sonu_cikis():
    df = rastgele_mumlar(24 * 30, seed=3, freq="1h", baslangic="2022-01-01")
    sig = DualThrust(n=2, k1=0.2, k2=0.2).sinyaller(df)
    son = pd.Series(df.index.floor("D"), index=df.index).shift(-1) != pd.Series(df.index.floor("D"), index=df.index)
    son.iloc[-1] = False
    assert sig.loc[son, "cikis"].all() and (sig.loc[son, "yon"] == 0).all()
    with pytest.raises(ValueError):
        DualThrust(seans="x").sinyaller(df)


# ---------------------------------------------------------------- R-Breaker
def test_rbreaker_seviyeleri_onceki_gune_dayanir():
    df = rastgele_mumlar(24 * 15, seed=4, freq="1h", baslangic="2022-01-01")
    s = RBreaker()
    bilgi = seans_bilgi(df, "utc_gun")
    sv = s.seviyeler(df, bilgi)
    gun = pd.Timestamp("2022-01-08", tz="UTC")
    onc = df[df.index.floor("D") == gun - pd.Timedelta(days=1)]
    h, l, c = onc.yuksek.max(), onc.dusuk.min(), onc.kapanis.iloc[-1]
    pv = (h + l + c) / 3
    m = df.index.floor("D") == gun
    beklenen = {"pivot": pv, "r3": h + 2 * (pv - l), "r2": pv + (h - l), "r1": 2 * pv - l,
                "s1": 2 * pv - h, "s2": pv - (h - l), "s3": l - 2 * (h - pv)}
    for ad, v in beklenen.items():
        assert np.allclose(sv.loc[m, ad], v), ad
    assert sv.loc[df.index.floor("D") == df.index[0].floor("D"), "r3"].isna().all()
    # bugünü değiştirmek bugünün seviyelerini değiştirmez; yarınınkini değiştirir
    d2, mm = _gunleri_degistir(df, "2022-01-08")
    sv2 = s.seviyeler(d2, seans_bilgi(d2, "utc_gun"))
    pdt.assert_frame_equal(sv[mm], sv2[mm])
    yarin = df.index.floor("D") == pd.Timestamp("2022-01-09", tz="UTC")
    assert not np.allclose(sv.loc[yarin, "r3"], sv2.loc[yarin, "r3"])
    # R3 > R2 > R1 > pivot > S1 > S2 > S3
    d = sv.dropna()
    assert ((d.r3 > d.r2) & (d.r2 > d.r1) & (d.r1 > d["pivot"]) & (d["pivot"] > d.s1) & (d.s1 > d.s2) & (d.s2 > d.s3)).all()


def test_rbreaker_kollar_ve_yonler():
    df = rastgele_mumlar(24 * 80, seed=15, freq="1h", baslangic="2022-01-01")
    bilgi = seans_bilgi(df, "utc_gun")
    sv = RBreaker().seviyeler(df, bilgi)
    k = df.kapanis
    kir = RBreaker(kollar="kirilim").sinyaller(df)
    assert (kir.yon != 0).any()
    gl, gs = kir[kir.yon == 1].index, kir[kir.yon == -1].index
    assert (k[gl] > sv.r3[gl]).all() and (k[gs] < sv.s3[gs]).all()
    don = RBreaker(kollar="donus").sinyaller(df)
    assert (don.yon != 0).any()
    dl, ds = don[don.yon == 1].index, don[don.yon == -1].index
    assert (k[dl] > sv.s1[dl]).all() and (k[ds] < sv.r1[ds]).all()
    # bugünün önceki mumlarının tepesi R2'yi aşmış olmalı (short dönüş)
    yuk_onc = df.yuksek.groupby(df.index.floor("D")).cummax().groupby(df.index.floor("D")).shift(1)
    assert (yuk_onc[ds] >= sv.r2[ds]).all()
    with pytest.raises(ValueError):
        RBreaker(kollar="x").sinyaller(df)


def test_rbreaker_abd_seans_gece_yok():
    df = abd_mumlari(is_gunleri("2023-02-01", "2023-05-15"), 15, seed=7, vol=0.003)
    s = RBreaker(seans="abd_hisse", stop_atr_k=2.0)
    r = backtest(df, s, MotorAyarlari())
    t = r.islemler
    assert len(t) > 5
    g1 = t.giris_zamani.dt.tz_convert(NY).dt.date
    g2 = t.cikis_zamani.dt.tz_convert(NY).dt.date
    assert (g1[t.cikis_nedeni != "kill_switch"] == g2[t.cikis_nedeni != "kill_switch"]).all()


# ---------------------------------------------------------------- gün içi dönüş
def test_gun_ici_donus_pencere_new_york():
    df = abd_mumlari(is_gunleri("2023-02-01", "2023-05-15"), 30, seed=2, vol=0.004)
    s = GunIciDonus(esik=0.0005)
    sig = s.sinyaller(df)
    assert (sig.yon != 0).sum() > 10
    kapanis_yerel = (df.index + pd.Timedelta(minutes=30)).tz_convert(NY)
    hr = kapanis_yerel.hour + kapanis_yerel.minute / 60.0
    giris = sig.yon.to_numpy() != 0
    assert (hr[giris] >= 10.0).all() and (hr[giris] <= 14.5).all()       # sinyal mumu 10:00-14:30 arası kapanır (sonraki mum 15:00'te biter)
    # 15:00 ve sonrası kapanan mumlarda çıkış bayrağı (pozisyon 15:00 açılışında kapanır)
    assert sig.cikis_long[hr >= 15.0].all() and not sig.cikis_long[hr < 15.0].any()
    r = backtest(df, s, MotorAyarlari())
    t = r.islemler
    assert len(t) > 5
    c = t.cikis_zamani.dt.tz_convert(NY)
    assert ((c.dt.hour + c.dt.minute / 60.0)[t.cikis_nedeni == "sinyal"] <= 15.0).all()
    g1 = t.giris_zamani.dt.tz_convert(NY).dt.date
    assert (g1[t.cikis_nedeni != "kill_switch"] == c.dt.date[t.cikis_nedeni != "kill_switch"]).all()


def test_gun_ici_donus_yalniz_durum_degisince():
    df = abd_mumlari(is_gunleri("2023-02-01", "2023-03-31"), 30, seed=2, vol=0.004)
    sig = GunIciDonus(esik=0.0005).sinyaller(df)
    sma = df.kapanis.rolling(5).mean()
    uzun_durum = df.kapanis < sma * (1 - 0.0005)
    giris = sig.yon == 1
    assert (uzun_durum[giris]).all()
    assert not (uzun_durum.shift(1, fill_value=False)[giris]).any()      # önceki mumda durum yoktu


# ---------------------------------------------------------------- E0V1EN / EMA50-200 / OTT / Sparta
def test_e0v1en_cikis_ve_zaman_cikisi():
    df = veri(E0v1en)
    sig = olustur(E0v1en).sinyaller(df)
    g = sig[sig.yon == 1]
    assert (g.zaman_cikisi_mum == 28).all() and not (sig.yon == -1).any()
    assert (g.stop == df.kapanis[g.index] * 0.94).all()
    assert sig.cikis_long.any()


def test_ema50_200_tekrar_ve_ayna():
    df = veri(Ema50200Geri)
    sig = Ema50200Geri().sinyaller(df)
    giris = sig.yon != 0
    assert giris.sum() > 5
    # aynı yönde art arda 3 mumda tekrar sinyal yok
    for yon in (1, -1):
        idx = np.flatnonzero((sig.yon == yon).to_numpy())
        assert (np.diff(idx) > 3).all()
    g = sig[sig.yon == 1]
    assert np.allclose(g.stop, df.kapanis[g.index] * 0.9) and np.allclose(g.hedef, df.kapanis[g.index] * 1.1)
    assert (sig.zaman_cikisi_mum.dropna() == 100).all()
    assert not (Ema50200Geri(short=False).sinyaller(df).yon == -1).any()


def test_ott_long_stop_ott_cizgisi_ve_risk_siniri():
    df = veri(OttBantlari)
    s = olustur(OttBantlari, max_risk_long=0.5, max_risk_short=0.5)
    sig = s.sinyaller(df)
    giris = sig[sig.yon != 0]
    risk = (giris.stop - df.kapanis[giris.index]).abs() / df.kapanis[giris.index] * 100
    assert (risk <= 0.5 + 1e-9).all()
    assert len(giris) < (olustur(OttBantlari).sinyaller(df).yon != 0).sum()
    assert not (OttBantlari(long=False).sinyaller(df).yon == 1).any()


def test_seans_testleri_utc_ve_abd_bilgi():
    df = rastgele_mumlar(24 * 5, seed=1, freq="1h", baslangic="2022-01-01")
    b = seans_bilgi(df, "utc_gun")
    assert b["ici"][1:].all()
    assert not b["acilis_tamam"].iloc[:24].any() and b["acilis_tamam"].iloc[24:].all()   # ilk gün: mum süresi bilinmez, atlanır
    assert np.allclose(b["acilis"].iloc[24:48], df.acilis.iloc[24])
