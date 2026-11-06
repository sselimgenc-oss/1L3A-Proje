"""B4 aileleri: lookahead, çerçeve geçerliliği, gün sonu, elle kurgulanmış senaryolar, long/short simetrisi."""
import importlib
import time

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

KAYITLAR = [
    ("swing", "sahte_kirilim", "SahteKirilim"), ("daytrade", "sahte_kirilim", "SahteKirilim"),
    ("scalp", "sahte_kirilim", "SahteKirilim"),
    ("swing", "seviye_tepki", "SeviyeTepki"), ("daytrade", "seviye_tepki", "SeviyeTepki"),
    ("scalp", "seviye_tepki", "SeviyeTepki"),
    ("swing", "talep_arz_bolgesi", "TalepArzBolgesi"), ("scalp", "talep_arz_bolgesi", "TalepArzBolgesi"),
    ("swing", "trend_cizgisi_kanal", "TrendCizgisiKanal"), ("daytrade", "trend_cizgisi_kanal", "TrendCizgisiKanal"),
    ("swing", "ucgen_dikdortgen_kirilim", "UcgenDikdortgenKirilim"),
    ("daytrade", "ucgen_dikdortgen_kirilim", "UcgenDikdortgenKirilim"),
    ("scalp", "ucgen_dikdortgen_kirilim", "UcgenDikdortgenKirilim"),
    ("swing", "witch_hat", "WitchHat"),
    ("swing", "geri_cekilme_fiyat_eylemi", "GeriCekilmeFiyatEylemi"),
    ("daytrade", "geri_cekilme_fiyat_eylemi", "GeriCekilmeFiyatEylemi"),
    ("scalp", "geri_cekilme_fiyat_eylemi", "GeriCekilmeFiyatEylemi"),
    ("swing", "yeni_dip_sonrasi_donus", "YeniDipSonrasiDonus"), ("swing", "yuvarlak_dip_fincan", "YuvarlakDipFincan"),
]


def sinif(st, mod, cls):
    return getattr(importlib.import_module(f"motor.strateji.{st}.{mod}"), cls)


TUMU = [sinif(*k) for k in KAYITLAR]
FREQ = {"swing": "1h", "daytrade": "1h", "scalp": "15min"}


def rastgele(n=3000, seed=7, freq="1h", vol=0.006):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.003, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.003, n))
    idx = pd.date_range("2022-01-03", periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def ohlc(satirlar, freq="1h", hacim=1.0, baslangic="2022-01-03"):
    a = np.asarray(satirlar, float)
    idx = pd.date_range(baslangic, periods=len(a), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": a[:, 0], "yuksek": a[:, 1], "dusuk": a[:, 2], "kapanis": a[:, 3],
                         "hacim": hacim}, index=idx)


def yoldan(kapanislar, w=0.1, freq="1h"):
    k = np.asarray(kapanislar, float)
    ac = np.r_[k[0], k[:-1]]
    return ohlc(np.c_[ac, np.maximum(ac, k) + w, np.minimum(ac, k) - w, k], freq)


def ek(df, *satirlar):
    yeni = ohlc(satirlar, baslangic=df.index[-1] + (df.index[1] - df.index[0]), freq=pd.infer_freq(df.index) or "1h")
    return pd.concat([df, yeni])


def _esit(a, b):
    pdt.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True), check_dtype=False)


# ---------------------------------------------------------------- lookahead / çerçeve
VARYANTLAR = {
    "SahteKirilim": [{}, {"kapanis_disi": False, "min_dokunus": 0, "hedef_modu": "r", "adx_esik": 25.0}],
    "SeviyeTepki": [{}, {"seviye_tipi": "onceki_seans"}, {"seviye_tipi": "yuvarlak", "tepki_modu": "ha"},
                    {"seviye_tipi": "pivot", "pivot_yontemi": "zigzag"}],
    "TalepArzBolgesi": [{}, {"giris_modu": "tepki", "hacim_onay": False, "itki_atr": 1.0},
                        {"giris_modu": "tuzak", "itki_atr": 1.0, "ust_tf": "4h"}],
    "TrendCizgisiKanal": [{}, {"mod": "kirilim"}, {"egim_sart": False, "kanal_sd": 1.0}],
    "UcgenDikdortgenKirilim": [{}, {"stop_modu": "karsi_uc", "min_rr": 0.0, "pivot_yontemi": "zigzag"}],
    "WitchHat": [{}, {"hareket_atr": 2.0, "yakin_atr": 1.0}],
    "GeriCekilmeFiyatEylemi": [{}, {"hedef_modu": "tepe", "zayif": False, "adx_esik": 0.0, "ust_tf": "4h"}],
    "YeniDipSonrasiDonus": [{}, {"dip_pencere": 40, "itki_atr": 1.0}],
    "YuvarlakDipFincan": [{}, {"yuvarlaklik": 0.0, "zigzag_esik_k": 1.5, "min_derinlik_atr": 1.0}],
}


def _id(s):
    return s.ad


@pytest.mark.parametrize("S", TUMU, ids=lambda c: c.ad)
def test_meta_ve_izgara(S):
    s = S()
    stil, aile = S.ad.split("__")
    assert S.stil == stil and S.ad == f"{stil}__{aile}"
    kombinasyon = 1
    for k, v in S.parametre_izgarasi.items():
        assert k in S.varsayilan_parametreler
        kombinasyon *= len(v)
    assert kombinasyon <= 27
    assert s.cikis_var_mi() is True
    with pytest.raises(ValueError):
        S(olmayan_parametre=1)


@pytest.mark.parametrize("S", TUMU, ids=lambda c: c.ad)
def test_lookahead_ve_gecerlilik(S):
    df = rastgele(3000, freq=FREQ[S.stil])
    for var in VARYANTLAR[S.__name__]:
        s = S(**var)
        tam = s.sinyaller(df)
        assert list(tam.columns) == ["yon", "stop", "hedef", "cikis"] and tam.index.equals(df.index)
        for n in (900, 1700, 2600):
            _esit(s.sinyaller(df.iloc[:n]), tam.iloc[:n])
        g = tam[tam.yon != 0]
        assert g.stop.notna().all()
        kap = df.kapanis[g.index]
        uzun, kisa = g[g.yon == 1], g[g.yon == -1]
        assert (uzun.stop < kap[uzun.index]).all() and (kisa.stop > kap[kisa.index]).all()
        h = g.dropna(subset=["hedef"])
        assert (h[h.yon == 1].hedef > kap[h[h.yon == 1].index]).all()
        assert (h[h.yon == -1].hedef < kap[h[h.yon == -1].index]).all()


@pytest.mark.parametrize("S", TUMU, ids=lambda c: c.ad)
def test_long_short_kapatma(S):
    df = rastgele(2500, seed=11, freq=FREQ[S.stil])
    toplam = S().sinyaller(df)
    assert not (S(long=False).sinyaller(df).yon == 1).any()
    assert not (S(short=False).sinyaller(df).yon == -1).any()
    # long-only çıktı, tam çıktının long alt kümesidir
    pd.testing.assert_series_equal((S(short=False).sinyaller(df).yon == 1), (toplam.yon == 1), check_names=False)


@pytest.mark.parametrize("S", [c for c in TUMU if c.stil == "daytrade"], ids=lambda c: c.ad)
def test_daytrade_gun_sonu(S):
    from motor.strateji.daytrade._ortak import seans_son_mumu
    df = rastgele(2400, freq="1h")
    sig = S().sinyaller(df)
    son = seans_son_mumu(df.index, 0.0)
    assert son.sum() > 50
    assert (sig.loc[son, "yon"] == 0).all()
    assert sig.loc[son, "cikis"].all()
    assert (sig.loc[~son, "cikis"] == False).all()   # noqa: E712
    assert (sig.yon != 0).sum() > 0


def test_sure_60k():
    df = rastgele(60000, freq="15min", vol=0.004)
    for S in TUMU:
        t = time.time()
        S().sinyaller(df)
        assert time.time() - t < 10, S.ad


# ---------------------------------------------------------------- elle kurgulanmış senaryolar
def _ilk(sig):
    return sig[sig.yon != 0]


def test_sahte_kirilim_long_ve_ayna_short():
    from motor.strateji.swing.sahte_kirilim import SahteKirilim
    # 100-110 üçgen dalga aralık, sonra alt sınır altına delme (kapanış dışarıda) ve içeri dönüş
    dalga = [100 + (i % 20 if i % 20 <= 10 else 20 - i % 20) for i in range(120)]
    df = yoldan(dalga, w=0.2)
    df = ek(df, (101.0, 101.2, 97.5, 99.0), (99.0, 101.5, 98.9, 101.2))
    s = SahteKirilim()
    sig = s.sinyaller(df)
    g = _ilk(sig)
    assert list(g.index) == [df.index[-1]] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < 97.5 and g.hedef.iloc[0] > 109          # karşı uç
    gs = _ilk(s.sinyaller(_ayna200(df)))
    assert list(gs.index) == [df.index[-1]] and gs.yon.iloc[0] == -1
    assert gs.stop.iloc[0] > 200 - 97.5 and gs.hedef.iloc[0] < 200 - 109


def _ayna200(df):
    return pd.DataFrame({"acilis": 200 - df.acilis, "yuksek": 200 - df.dusuk, "dusuk": 200 - df.yuksek,
                         "kapanis": 200 - df.kapanis, "hacim": df.hacim}, index=df.index)


def test_sahte_kirilim_kapanis_icerde_degilse_sinyal_yok():
    from motor.strateji.swing.sahte_kirilim import SahteKirilim
    dalga = [100 + (i % 20 if i % 20 <= 10 else 20 - i % 20) for i in range(120)]
    df = ek(yoldan(dalga, w=0.2), (101.0, 101.2, 97.5, 99.0), (99.0, 99.2, 96.0, 97.0))   # devam eden gerçek kırılım
    assert _ilk(SahteKirilim().sinyaller(df)).empty


def test_seviye_tepki_yuvarlak_100():
    from motor.strateji.scalp.seviye_tepki import SeviyeTepki
    yol = list(np.linspace(130, 101.5, 40)) + [101.0]
    df = yoldan(yol, w=0.1, freq="15min")
    df = ek(df, (101.5, 102.1, 100.0, 102.0))          # 100'e iğne atıp yeşil kapanan red mumu
    s = SeviyeTepki(tepki_modu="red", seviye_tipi="yuvarlak")
    g = _ilk(s.sinyaller(df))
    assert g.index[-1] == df.index[-1] and g.yon.iloc[-1] == 1
    assert g.stop.iloc[-1] < 100.0 and g.hedef.iloc[-1] > 102.0
    gs = _ilk(s.sinyaller(_ayna200(df)))
    assert gs.index[-1] == df.index[-1] and gs.yon.iloc[-1] == -1 and gs.stop.iloc[-1] > 100.0
    # tolerans dışı (seviyeden uzak) -> sinyal yok
    df2 = ek(yoldan(yol, w=0.1, freq="15min"), (105.0, 105.6, 104.2, 105.5))
    assert (_ilk(s.sinyaller(df2)).index != df2.index[-1]).all()


def test_seviye_tepki_onceki_seans_dibi():
    from motor.strateji.daytrade.seviye_tepki import SeviyeTepki
    # gün 1: dip 100; gün 2: fiyat 100'e iner, iğne + yeşil kapanış
    g1 = [(105, 106, 100, 104)] + [(104, 105, 103, 104)] * 22 + [(104, 105, 103, 104)]
    g2 = [(104, 105, 103.5, 104)] * 10 + [(104, 104.2, 101.5, 102), (102, 102.2, 101, 101.4),
                                             (101.4, 101.5, 100.1, 100.3), (100.9, 101.5, 99.9, 101.4)]
    df = ohlc(g1 + g2, freq="1h", baslangic="2022-01-03")
    s = SeviyeTepki(seviye_tipi="onceki_seans")
    g = _ilk(s.sinyaller(df))
    assert len(g) >= 1 and g.index[-1] == df.index[-1] and g.yon.iloc[-1] == 1
    assert g.stop.iloc[-1] < 100.0


def test_talep_bolgesi_dbr_tepki_ve_tek_islem():
    from motor.strateji.swing.talep_arz_bolgesi import TalepArzBolgesi
    sakin = [(100.0, 100.2, 99.9, 100.05)] * 60
    leg_in = [(100.0, 100.05, 97.45, 97.5)]
    baz = [(97.6, 98.1, 97.3, 97.7)]
    leg_out = [(97.7, 100.55, 97.65, 100.5)]
    rali = [(100.5, 101.6, 100.4, 101.5), (101.5, 102.6, 101.4, 102.5), (102.5, 103.6, 102.4, 103.5),
            (103.5, 104.1, 103.4, 104.0)]
    dusus = [(104.0, 104.05, 102.0, 102.1), (102.1, 102.15, 100.0, 100.1), (100.1, 100.15, 98.4, 98.5)]
    tepki = [(98.5, 98.9, 97.6, 98.8)]
    df = ohlc(sakin + leg_in + baz + leg_out + rali + dusus + tepki)
    s = TalepArzBolgesi(giris_modu="tepki", hacim_onay=False, short=False)
    g = _ilk(s.sinyaller(df))
    assert list(g.index) == [df.index[-1]] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < 97.3 and g.hedef.iloc[0] > 98.8
    gs = _ilk(TalepArzBolgesi(giris_modu="tepki", hacim_onay=False).sinyaller(_ayna200(df)))
    assert list(gs.index) == [df.index[-1]] and gs.yon.iloc[0] == -1          # arz bölgesi aynası
    # bölge bozulursa (distal altı kapanış) sinyal yok
    df_k = ohlc(sakin + leg_in + baz + leg_out + rali + dusus + [(98.5, 98.6, 96.0, 96.2)] + tepki)
    assert _ilk(s.sinyaller(df_k)).empty or _ilk(s.sinyaller(df_k)).index[-1] != df_k.index[-1]


def test_talep_bolgesi_tuzak_mumu():
    from motor.strateji.scalp.talep_arz_bolgesi import TalepArzBolgesi
    sakin = [(100.0, 100.2, 99.9, 100.05)] * 60
    bolge = [(100.0, 100.05, 97.45, 97.5), (97.6, 98.1, 97.3, 97.7), (97.7, 100.55, 97.65, 100.5)]
    rali = [(100.5, 101.6, 100.4, 101.5), (101.5, 102.6, 101.4, 102.5), (102.5, 103.6, 102.4, 103.5)]
    dusus = [(103.5, 103.55, 101.0, 101.1), (101.1, 101.15, 98.6, 98.7)]
    tuzak = [(98.7, 98.8, 97.6, 97.9), (97.9, 99.5, 97.8, 99.2)]     # kırmızı tuzak mumu, sonra yükseğini aşan kapanış
    df = ohlc(sakin + bolge + rali + dusus + tuzak, freq="15min")
    df.loc[df.index[-2], "hacim"] = 3.0
    s = TalepArzBolgesi(ust_tf="", short=False, hacim_onay=True, baz_maks=1)
    g = _ilk(s.sinyaller(df))
    assert list(g.index) == [df.index[-1]] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < 97.6                                          # tuzak mumu dibi altı
    df.loc[df.index[-2], "hacim"] = 0.5                                   # hacim onayı yok
    assert _ilk(s.sinyaller(df)).empty


def test_trend_kanali_yukselen_alt_cizgi():
    from motor.strateji.swing.trend_cizgisi_kanal import TrendCizgisiKanal
    i = np.arange(260)
    kap = 100 + 0.5 * i + 1.0 * np.sin(i * 0.9)
    df = yoldan(kap, w=0.15)
    s = TrendCizgisiKanal(kanal_sd=1.0, r2_esik=0.5, min_kanal_atr=1.0)
    sig = s.sinyaller(df)
    assert (sig.yon == 1).sum() > 3 and (sig.yon == -1).sum() == 0          # yükselen kanal: yalnız long
    g = _ilk(sig)
    assert (g.hedef > df.kapanis[g.index]).all() and (g.stop < df.kapanis[g.index]).all()
    gs = _ilk(s.sinyaller(_ayna200(df)))
    assert (gs.yon == -1).all() and len(gs) == (sig.yon == 1).sum()          # düşen kanal aynası


def test_trend_cizgisi_kirilimi():
    from motor.strateji.daytrade.trend_cizgisi_kanal import TrendCizgisiKanal
    i = np.arange(200)
    kap = list(300 - 0.5 * i + 1.0 * np.sin(i * 0.9))
    df = yoldan(kap, w=0.1)
    # son mumlarda düşen kanalın üstüne sert çıkış
    df = ek(df, (kap[-1], kap[-1] + 6.5, kap[-1] - 0.2, kap[-1] + 6.0))
    s = TrendCizgisiKanal(mod="kirilim", kanal_sd=1.0, short=False, regresyon=48, min_kanal_atr=1.0)
    g = _ilk(s.sinyaller(df))
    assert len(g) >= 1 and g.index[-1] == df.index[-1] and g.yon.iloc[-1] == 1


def test_dikdortgen_kirilimi_long_short():
    from motor.strateji.swing.ucgen_dikdortgen_kirilim import UcgenDikdortgenKirilim
    dalga = [100 + (i % 20 if i % 20 <= 10 else 20 - i % 20) for i in range(100)]
    df = yoldan(dalga, w=0.1)
    df = ek(df, (dalga[-1], 111.6, dalga[-1] - 0.1, 111.5))
    s = UcgenDikdortgenKirilim(ucgen=False, simetrik=False)
    g = _ilk(s.sinyaller(df))
    assert list(g.index) == [df.index[-1]] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < 105.1 and g.hedef.iloc[0] > 111.5
    gs = _ilk(s.sinyaller(_ayna200(df)))
    assert list(gs.index) == [df.index[-1]] and gs.yon.iloc[0] == -1
    # tip kapalıysa sinyal yok
    assert _ilk(UcgenDikdortgenKirilim(ucgen=False, simetrik=False, dikdortgen=False).sinyaller(df)).empty


def test_yukselen_ucgen():
    from motor.strateji.daytrade.ucgen_dikdortgen_kirilim import UcgenDikdortgenKirilim
    # yatay direnç 110, yükselen dipler 100, 103, 106
    yol = [100, 105, 110, 105, 100.5, 104, 110, 106, 103, 106.5, 110, 108, 106]
    yol = list(np.interp(np.arange(0, 12.01, 1 / 3), np.arange(len(yol)), yol))
    df = yoldan(yol, w=0.1)
    df = ek(df, (yol[-1], 111.3, yol[-1] - 0.1, 111.0))
    s = UcgenDikdortgenKirilim(pivot_k=2, pencere=60, stop_modu="orta", short=False, min_rr=0.0)
    g = _ilk(s.sinyaller(df))
    assert len(g) >= 1 and g.index[-1] == df.index[-1] and g.yon.iloc[-1] == 1


def _witch_df():
    dus = list(np.linspace(300, 125, 160))                # güçlü düşüş
    tepe = [125.0, 127.0, 130.0, 127.0]                    # pivot tepe 130
    dusus = list(np.linspace(126, 110, 8))
    don = [117.0, 123.0, 129.5]                           # sert dönüş (brim ~130)
    df = yoldan(dus + tepe + dusus + don, w=0.3)
    return ek(df, (129.5, 129.6, 121.5, 122.0))           # dünkü dibin altında kapanış


def test_witch_hat_short_ve_ayna_long():
    from motor.strateji.swing.witch_hat import WitchHat
    df = _witch_df()
    s = WitchHat()
    g = _ilk(s.sinyaller(df))
    assert len(g) >= 1 and g.index[-1] == df.index[-1] and g.yon.iloc[-1] == -1
    assert g.stop.iloc[-1] > 130.0 and g.hedef.iloc[-1] < 115.0          # şapka ucu (eski dipler)
    gl = _ilk(s.sinyaller(_ayna200(df)))
    assert gl.index[-1] == df.index[-1] and gl.yon.iloc[-1] == 1


def _gc_df(govde=0.1):
    yukari = [100 + 0.5 * i for i in range(120)]
    df = yoldan(yukari, w=0.1)
    son = yukari[-1]
    k1, k2 = son - govde, son - 2 * govde
    df = ek(df, (son, son + 0.05, k1 - 0.05, k1), (k1, k1 + 0.05, k2 - 0.05, k2))
    return ek(df, (k2, k2 + 0.9, k2 - 0.05, k2 + 0.8))


def test_geri_cekilme_long_short_ve_zayif_filtre():
    from motor.strateji.swing.geri_cekilme_fiyat_eylemi import GeriCekilmeFiyatEylemi
    df = _gc_df()
    s = GeriCekilmeFiyatEylemi()
    g = _ilk(s.sinyaller(df))
    assert list(g.index[-1:]) == [df.index[-1]] and g.yon.iloc[-1] == 1
    assert g.stop.iloc[-1] < df.dusuk.iloc[-3:].min() and g.hedef.iloc[-1] > df.kapanis.iloc[-1]
    gs = _ilk(s.sinyaller(_ayna200(df)))
    assert gs.index[-1] == df.index[-1] and gs.yon.iloc[-1] == -1
    # güçlü (iki ardışık geniş gövdeli karşı mum) geri çekilme 'zayıf' filtresine takılır
    df2 = _gc_df(govde=0.4)
    assert df2.index[-1] not in _ilk(s.sinyaller(df2)).index
    assert df2.index[-1] in _ilk(GeriCekilmeFiyatEylemi(zayif=False).sinyaller(df2)).index
    # trend zayıfsa (ADX eşiği çok yüksek) sinyal yok
    assert df.index[-1] not in _ilk(GeriCekilmeFiyatEylemi(adx_esik=101.0).sinyaller(df)).index


def test_yeni_dip_sonrasi_donus():
    from motor.strateji.swing.yeni_dip_sonrasi_donus import YeniDipSonrasiDonus
    dus = list(np.linspace(200, 100, 150))
    yuksel = [102.0, 104.0, 106.0, 108.5]
    df = yoldan(dus + yuksel, w=0.2)
    df = ek(df, (108.0, 108.3, 105.7, 106.0), (106.0, 109.7, 105.9, 109.2))
    s = YeniDipSonrasiDonus(dip_pencere=100, short=False)
    g = _ilk(s.sinyaller(df))
    assert list(g.index) == [df.index[-1]] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < df.dusuk.iloc[-2]
    gs = _ilk(YeniDipSonrasiDonus(dip_pencere=100).sinyaller(_ayna200(df)))
    assert gs.index[-1] == df.index[-1] and gs.yon.iloc[-1] == -1
    # yeni dip yoksa (dip_pencere çok büyük -> pencere dolmaz) sinyal yok
    assert _ilk(YeniDipSonrasiDonus(dip_pencere=400).sinyaller(df)).empty


def _fincan_df():
    x = np.linspace(-1, 1, 60)
    onc = list(np.linspace(100, 120, 20))
    fincan = list(100 + 20 * x ** 2)[1:]
    kenar = [119.0]
    sap = list(np.linspace(119, 113.5, 10))[1:] + list(np.linspace(113.5, 117.5, 6))[1:]
    df = yoldan(onc + fincan + kenar + sap, w=0.2)
    return df


def test_fincan_sap_kirilimi_ve_ayna():
    from motor.strateji.swing.yuvarlak_dip_fincan import YuvarlakDipFincan
    df = _fincan_df()
    kirilim = ek(df, (117.5, 121.4, 117.4, 121.2))
    s = YuvarlakDipFincan(zigzag_esik_k=2.0, min_derinlik_atr=2.0, short=False)
    g = _ilk(s.sinyaller(kirilim))
    assert len(g) >= 1 and g.index[-1] == kirilim.index[-1] and g.yon.iloc[-1] == 1
    assert g.stop.iloc[-1] < 113.5 and g.hedef.iloc[-1] > 125
    # V şekilli taban parabol R2 eşiğini geçemez
    v = list(np.linspace(100, 120, 20)) + list(np.linspace(120, 100, 30)) + list(np.linspace(100, 119, 30)) + \
        list(np.linspace(119, 113.5, 9)) + list(np.linspace(113.5, 117.5, 5))
    dv = ek(yoldan(v, w=0.2), (117.5, 121.4, 117.4, 121.2))
    assert dv.index[-1] not in _ilk(YuvarlakDipFincan(zigzag_esik_k=2.0, min_derinlik_atr=2.0, yuvarlaklik=0.97,
                                                      short=False).sinyaller(dv)).index
    gs = _ilk(YuvarlakDipFincan(zigzag_esik_k=2.0, min_derinlik_atr=2.0).sinyaller(_ayna200(kirilim)))
    assert len(gs) >= 1 and gs.index[-1] == kirilim.index[-1] and gs.yon.iloc[-1] == -1


def test_kart_ayarlari_gecerli():
    import json
    import pathlib
    kok = pathlib.Path(__file__).resolve().parents[1] / "stratejiler" / "kart_ayarlari"
    aileler = {a["aile_id"]: a for a in json.load(open(kok.parent / "aileler.json", encoding="utf-8"))}
    for st, mod, cls in KAYITLAR:
        S = sinif(st, mod, cls)
        dosya = kok / f"{S.ad}.json"
        assert dosya.exists(), dosya
        kayit = json.load(open(dosya, encoding="utf-8"))
        assert kayit or S.ad == 'daytrade__trend-cizgisi-kanal', S.ad   # tek kartı (Boxer 1m kanal) ifade edilemedi
        kartlar = set(aileler[S.ad]["kaynak_kartlar"])
        for k in kayit:
            assert k["kart_id"] in kartlar
            assert k["cikis_ayarlari"] is None
            S(**k["parametreler"])          # bilinmeyen parametre -> ValueError
