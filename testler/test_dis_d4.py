"""D4 sistematik stratejiler (EWMAC Carver, gün içi trend-day): lookahead, stop tarafı, ızgara, DST, gün sonu, motor dumanı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis._gosterge_d4 import (
    OLCEK, TAHMIN_SINIRI, birlesik_tahmin, ewmac_tahmin, mum_gun_tahmin, seans_cerceve, varyantlari_coz)
from motor.strateji.dis.d4_sistematik import EwmacCarver, TrendGunIci
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

NY = "America/New_York"


def abd_mumlari(gunler, dk=15, seed=3, atla=None, kisa_gunler=(), vol=0.0015):
    """Yalnız RTH (09:30-16:00 NY) mumları, UTC indeksli; DST'yi zoneinfo ile uygular."""
    rng = np.random.default_rng(seed)
    atla = set(atla or [])
    satirlar = []
    for gun in gunler:
        bas = pd.Timestamp(f"{gun} 09:30").tz_localize(NY)
        bitis = pd.Timestamp(f"{gun} {'13:00' if gun in kisa_gunler else '16:00'}").tz_localize(NY)
        t = bas
        while t < bitis:
            if (gun, t.strftime("%H:%M")) not in atla:
                satirlar.append(t.tz_convert("UTC"))
            t += pd.Timedelta(minutes=dk)
    idx = pd.DatetimeIndex(satirlar, name="zaman")
    kap = 100 * np.exp(np.cumsum(rng.normal(0, vol, len(idx))))
    ac = np.r_[kap[0], kap[:-1]]
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.0005, "dusuk": np.minimum(ac, kap) * 0.9995,
                         "kapanis": kap, "hacim": 1.0}, index=idx)


def is_gunleri(bas, bitis):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(bas, bitis)]


def veri(sinif, n=None, seed=11):
    if sinif is EwmacCarver:
        return rastgele_mumlar(n or 4500, seed=seed, freq="4h")
    return rastgele_mumlar(n or 4000, seed=seed, freq="1h")


# ---------------------------------------------------------------- kayıt / sözleşme
def test_kayit_ve_dogrula():
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.endswith("d4_sistematik")}
    assert kayitli == {"dis__ewmac-carver", "dis__trend-gun-ici"}
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []


@pytest.mark.parametrize("sinif", [EwmacCarver, TrendGunIci], ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.ad.startswith("dis__") and s.cikis_var_mi()
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(sinif, n=2500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = sinif(**{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index)


# ---------------------------------------------------------------- EWMAC
def test_olcek_sabitleri_ve_varyant_ayristirma():
    assert varyantlari_coz("16/64+32/128") == [(16, 64), (32, 128)]
    assert OLCEK[(2, 8)] == 10.6 and OLCEK[(64, 256)] == 1.87
    with pytest.raises(ValueError):
        varyantlari_coz("3/9")
    with pytest.raises(ValueError):
        EwmacCarver(varyantlar="5/20").sinyaller(veri(EwmacCarver, n=500))


def test_ewmac_surekli_yukselis_long_dusus_short():
    kap = 100 * 1.006 ** np.arange(700)
    yuk = mumlar_kapanistan(kap, genlik=0.01, freq="1D")
    dus = mumlar_kapanistan(kap[::-1].copy(), genlik=0.01, freq="1D")
    sy, sd = EwmacCarver().sinyaller(yuk), EwmacCarver().sinyaller(dus)
    assert (sy.yon == 1).any() and not (sy.yon == -1).any()
    assert (sd.yon == -1).any() and not (sd.yon == 1).any()
    assert EwmacCarver().tahmin(yuk).dropna().iloc[-1] > 5 > -5 > EwmacCarver().tahmin(dus).dropna().iloc[-1]
    # short kapalıysa düşen seride giriş yok
    assert (EwmacCarver(short=False).sinyaller(dus).yon == 0).all()


def test_ewmac_tahmin_kirpilir():
    # çok düzgün, düşük oynaklıklı üstel trend: ham değer 20'yi aşar -> tam 20'de kırpılır
    kap = pd.Series(100 * 1.01 ** np.arange(600), index=pd.date_range("2020-01-01", periods=600, freq="1D", tz="UTC"))
    kap = kap * (1 + 1e-4 * np.sin(np.arange(600)))
    f = birlesik_tahmin(kap, [(2, 8), (4, 16)], 1)
    assert f.dropna().max() == pytest.approx(TAHMIN_SINIRI) and f.dropna().min() >= -TAHMIN_SINIRI
    tek = ewmac_tahmin(kap, 2, 8, 1).dropna()
    assert tek.abs().max() <= TAHMIN_SINIRI
    rng = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, 0.02, 3000))))
    rng.index = pd.date_range("2010-01-01", periods=3000, freq="1D", tz="UTC")
    assert birlesik_tahmin(rng, varyantlari_coz("2/8+4/16+8/32"), 1).dropna().abs().max() <= TAHMIN_SINIRI


def test_ewmac_olcek_ortalama_mutlak_tahmin_makul():
    kap = rastgele_mumlar(4000, seed=7, freq="1D", baslangic="2005-01-01").kapanis
    for h, y in OLCEK:
        ort = ewmac_tahmin(kap, h, y, 1).abs().mean()
        assert 4 < ort < 16, (h, y, ort)   # rastgele yürüyüşte yayımlanan ölçekle ~10 civarı


def test_gun_mum_tahmin():
    assert mum_gun_tahmin(pd.date_range("2022-01-01", periods=300, freq="4h", tz="UTC")) == 6
    assert mum_gun_tahmin(pd.date_range("2022-01-01", periods=300, freq="1D", tz="UTC")) == 1
    assert mum_gun_tahmin(pd.date_range("2022-01-01", periods=300, freq="1D", tz="UTC"), 6) == 6


@pytest.mark.parametrize("tf,n", [("4h", 4500), ("1D", 1800)])
def test_ewmac_lookahead_ve_stop_tarafi(tf, n):
    df = rastgele_mumlar(n, seed=11, freq=tf, baslangic="2018-01-01")
    for s in (EwmacCarver(), EwmacCarver(varyantlar="2/8+4/16+8/32", esik=3.0)):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])
        giris = tam[tam.yon != 0]
        assert len(giris) > 0 and giris.stop.notna().all()
        kap = df.kapanis
        l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
        assert {"cikis_long", "cikis_short"} <= set(tam.columns)


def test_ewmac_cikis_isaret_donunce():
    df = rastgele_mumlar(2500, seed=4, freq="1D", baslangic="2015-01-01")
    s = EwmacCarver(varyantlar="2/8+4/16+8/32", esik=3.0)
    f, sig = s.tahmin(df), s.sinyaller(df)
    assert (sig.cikis_long == (f < 0).fillna(False)).all()
    assert (sig.cikis_short == (f > 0).fillna(False)).all()


@pytest.mark.parametrize("tf,n", [("4h", 4500), ("1D", 1800)])
def test_ewmac_motor_calisir(tf, n):
    df = rastgele_mumlar(n, seed=5, freq=tf, baslangic="2018-01-01")
    sonuc = backtest(df, EwmacCarver(varyantlar="2/8+4/16+8/32", esik=3.0), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- trend-day: seans çerçevesi / DST
def test_abd_dst_karar_ve_cikis_mumu():
    """Mart (Cuma EST -> Pazartesi EDT) ve Kasım (Cuma EDT -> Pazartesi EST): karar mumu hep 14:45 NY, UTC karşılığı kayar."""
    gunler = ["2023-03-10", "2023-03-13", "2023-11-03", "2023-11-06"]
    df = abd_mumlari(gunler, 15)
    c = seans_cerceve(df.index, "abd_hisse", 60)
    karar = df.index[c.karar.to_numpy()]
    assert len(karar) == 4
    yerel = karar.tz_convert(NY)
    assert set(yerel.strftime("%H:%M")) == {"14:45"}      # kapanışı 15:00 olan mum
    utc_saat = {str(k.date()): k.strftime("%H:%M") for k in karar}
    assert utc_saat["2023-03-10"] == "19:45" and utc_saat["2023-03-13"] == "18:45"
    assert utc_saat["2023-11-03"] == "18:45" and utc_saat["2023-11-06"] == "19:45"
    assert c.seans_ici.iloc[1:].all() and not c.seans_ici.iloc[0]     # ilk mumun süresi bilinmez


def test_abd_sinyal_ve_seans_sonu_cikisi_dst_gunlerinde():
    # 2023-03-09 ısınma günü: serinin ilk mumunun süresi bilinmediğinden ilk gün her zaman atlanır
    gunler = ["2023-03-09", "2023-03-10", "2023-03-13", "2023-11-03", "2023-11-06"]
    df = abd_mumlari(gunler, 15, vol=0.0)
    gun = pd.Series(df.index.tz_convert(NY).strftime("%Y-%m-%d"), index=df.index)
    ilk_ac = df.acilis.groupby(gun).transform("first")
    # her gün açılıştan %3 yukarıda kapan (sabit eşik %1)
    df["kapanis"] = ilk_ac * 1.03
    df["yuksek"] = df.kapanis * 1.0005
    df["dusuk"] = np.minimum(df.acilis, df.kapanis) * 0.9995
    s = TrendGunIci(seans="abd_hisse", giris_dk=60, esik_modu="sabit", esik_sabit=0.01)
    sig = s.sinyaller(df)
    yerel = df.index.tz_convert(NY)
    giris = df.index[sig.yon.to_numpy() == 1]
    assert len(giris) == 4 and "2023-03-09" not in set(giris.tz_convert(NY).strftime("%Y-%m-%d")) and set(giris.tz_convert(NY).strftime("%H:%M")) == {"14:45"}
    cik = df.index[sig.cikis.to_numpy()]
    assert set(cik.tz_convert(NY).strftime("%H:%M")) == {"15:30", "15:45"}      # son mumdan bir önceki ve son
    assert (sig.loc[sig.cikis, "yon"] == 0).all()
    # motor: işlem aynı gün 15:00 NY'de açılır, aynı gün 15:45 NY (son mumun açılışı)'nda kapanır
    r = backtest(df, s, MotorAyarlari())
    t = r.islemler
    assert len(t) == 4
    assert set(t.giris_zamani.dt.tz_convert(NY).dt.strftime("%H:%M")) == {"15:00"}
    assert set(t.cikis_zamani.dt.tz_convert(NY).dt.strftime("%H:%M")) == {"15:45"}
    assert (t.giris_zamani.dt.tz_convert(NY).dt.date == t.cikis_zamani.dt.tz_convert(NY).dt.date).all()


def test_abd_short_ve_short_kapali():
    df = abd_mumlari(["2023-04-28", "2023-05-01", "2023-05-02"], 15, vol=0.0)
    gun = pd.Series(df.index.tz_convert(NY).strftime("%Y-%m-%d"), index=df.index)
    df["kapanis"] = df.acilis.groupby(gun).transform("first") * 0.97
    df["yuksek"] = df.kapanis * 1.0005
    df["dusuk"] = np.minimum(df.acilis, df.kapanis) * 0.9995
    kw = dict(seans="abd_hisse", giris_dk=60, esik_modu="sabit", esik_sabit=0.01)
    sig = TrendGunIci(**kw).sinyaller(df)
    assert (sig.yon == -1).sum() == 2 and (sig.yon == 1).sum() == 0
    assert (sig.loc[sig.yon == -1, "stop"] > df.kapanis[sig.yon == -1]).all()
    assert (TrendGunIci(short=False, **kw).sinyaller(df).yon == 0).all()


def test_abd_esik_alti_getiri_sinyal_yok():
    df = abd_mumlari(["2023-04-28", "2023-05-01"], 15, vol=0.0)
    df["kapanis"] = df.acilis.iloc[0] * 1.004
    sig = TrendGunIci(seans="abd_hisse", esik_modu="sabit", esik_sabit=0.01).sinyaller(df)
    assert (sig.yon == 0).all()


def test_abd_eksik_acilis_ve_kisa_gun_atlanir():
    gunler = ["2023-04-28", "2023-05-01", "2023-05-02", "2023-05-03"]
    # 2 Mayıs: 09:30 ve 09:45 mumları yok (geç/eksik açılış); 3 Mayıs: erken kapanış 13:00 (karar mumu yok)
    df = abd_mumlari(gunler, 15, vol=0.0, atla=[("2023-05-02", "09:30"), ("2023-05-02", "09:45")],
                     kisa_gunler=["2023-05-03"])
    gun = pd.Series(df.index.tz_convert(NY).strftime("%Y-%m-%d"), index=df.index)
    df["kapanis"] = df.acilis.groupby(gun).transform("first") * 1.03
    s = TrendGunIci(seans="abd_hisse", giris_dk=60, esik_modu="sabit", esik_sabit=0.01)
    sig = s.sinyaller(df)
    giris_gunleri = set(df.index[sig.yon.to_numpy() == 1].tz_convert(NY).strftime("%Y-%m-%d"))
    assert giris_gunleri == {"2023-05-01"}


def test_abd_karar_mumu_cikis_penceresindeyse_giris_yok():
    """30m mumda giris_dk=30: karar mumu çıkış penceresine denk gelir -> gece taşınmaması için giriş yok."""
    df = abd_mumlari(["2023-04-28", "2023-05-01", "2023-05-02"], 30, vol=0.0)
    gun = pd.Series(df.index.tz_convert(NY).strftime("%Y-%m-%d"), index=df.index)
    df["kapanis"] = df.acilis.groupby(gun).transform("first") * 1.03
    s = TrendGunIci(seans="abd_hisse", giris_dk=30, esik_modu="sabit", esik_sabit=0.01)
    assert (s.sinyaller(df).yon == 0).all()
    assert (TrendGunIci(seans="abd_hisse", giris_dk=60, esik_modu="sabit", esik_sabit=0.01).sinyaller(df).yon != 0).any()


def test_abd_sigma_modu_gecmis_gun_olmadan_sinyal_yok():
    gunler = is_gunleri("2023-04-03", "2023-06-30")
    df = abd_mumlari(gunler, 15, seed=8, vol=0.002)
    s = TrendGunIci(seans="abd_hisse", giris_dk=60, esik_modu="sigma", esik_k=0.2, gecmis_gun=20)
    sig = s.sinyaller(df)
    gun = pd.Series(df.index.tz_convert(NY).strftime("%Y-%m-%d"), index=df.index)
    ilk = sorted(set(gun[sig.yon != 0]))[0]
    assert gunler.index(ilk) >= 20
    assert (sig.yon != 0).sum() > 5


# ---------------------------------------------------------------- trend-day: UTC günü (24 saat)
def test_utc_gun_giris_saati_ve_gun_sonu_cikisi():
    n = 24 * 13     # ilk gün ısınma (ilk mumun süresi bilinmez -> ilk gün atlanır): 12 giriş
    kap = np.full(n, 103.0)          # her gün açılışın %3 üstünde
    df = mumlar_kapanistan(kap, genlik=0.05, freq="1h", baslangic="2023-04-30")
    df["acilis"] = np.where(np.arange(n) % 24 == 0, 100.0, 103.0)
    s = TrendGunIci(seans="utc_gun", giris_dk=60, esik_modu="sabit", esik_sabit=0.01)
    sig = s.sinyaller(df)
    assert set(df.index[sig.yon == 1].hour) == {22} and (sig.yon == 1).sum() == 12
    assert set(df.index[sig.cikis].hour) == {23}
    s30 = TrendGunIci(seans="utc_gun", giris_dk=30, esik_modu="sabit", esik_sabit=0.01).sinyaller(df)
    assert set(df.index[s30.yon == 1].hour) == {22}
    r = backtest(df, s, MotorAyarlari())
    t = r.islemler
    assert len(t) > 0
    assert set(t.giris_zamani.dt.hour) == {23} and set(t.cikis_zamani.dt.hour) == {0}
    assert (t.cikis_zamani.dt.normalize() - t.giris_zamani.dt.normalize() == pd.Timedelta(days=1)).all()


def test_utc_gun_acilis_eksikse_atlanir():
    n = 24 * 5
    df = mumlar_kapanistan(np.full(n, 103.0), genlik=0.05, freq="1h", baslangic="2023-04-30")
    df["acilis"] = np.where(np.arange(n) % 24 == 0, 100.0, 103.0)
    df = df.drop(df.index[24:27])          # 1 Mayıs: 00:00-02:00 mumları yok (30 Nisan ısınma günü)
    sig = TrendGunIci(seans="utc_gun", esik_modu="sabit", esik_sabit=0.01).sinyaller(df)
    assert set(df.index[sig.yon == 1].strftime("%m-%d")) == {"05-02", "05-03", "05-04"}


def test_seans_gecersiz():
    with pytest.raises(ValueError):
        TrendGunIci(seans="x").sinyaller(veri(TrendGunIci, n=300))
    with pytest.raises(ValueError):
        TrendGunIci(esik_modu="x").sinyaller(veri(TrendGunIci, n=300))


# ---------------------------------------------------------------- trend-day: lookahead / stop / motor
def _td_veriler():
    return {
        "utc_1h": (veri(TrendGunIci), dict(seans="utc_gun")),
        "utc_15m": (rastgele_mumlar(5000, seed=2, freq="15min"), dict(seans="utc_gun", giris_dk=30)),
        "abd_15m": (abd_mumlari(is_gunleri("2023-01-02", "2023-06-30"), 15, seed=6, vol=0.002),
                    dict(seans="abd_hisse", giris_dk=60)),
        "abd_30m": (abd_mumlari(is_gunleri("2023-01-02", "2023-06-30"), 30, seed=6, vol=0.003),
                    dict(seans="abd_hisse", giris_dk=60)),
    }


@pytest.mark.parametrize("ad", ["utc_1h", "utc_15m", "abd_15m", "abd_30m"])
def test_trend_gun_ici_lookahead_stop_motor(ad):
    df, kw = _td_veriler()[ad]
    for ek in ({}, {"esik_modu": "sabit", "esik_sabit": 0.003, "esik_k": 0.3}):
        s = TrendGunIci(**kw, **ek)
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])
        giris = tam[tam.yon != 0]
        assert len(giris) > 0 and giris.stop.notna().all()
        kap = df.kapanis
        l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
        assert tam.cikis.any()
    sonuc = backtest(df, TrendGunIci(**kw, esik_modu="sabit", esik_sabit=0.003), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


def test_trend_gun_ici_gece_pozisyonu_yok_abd():
    df, kw = _td_veriler()["abd_15m"]
    r = backtest(df, TrendGunIci(**kw, esik_modu="sabit", esik_sabit=0.003), MotorAyarlari())
    t = r.islemler
    assert len(t) > 5
    g1 = t.giris_zamani.dt.tz_convert(NY).dt.date
    g2 = t.cikis_zamani.dt.tz_convert(NY).dt.date
    stopsuz = t.cikis_nedeni != "kill_switch"
    assert (g1[stopsuz] == g2[stopsuz]).all()
