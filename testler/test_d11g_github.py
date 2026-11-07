"""D11-G (GitHub kaynaklı 19 aile) testleri: sözleşme/ızgara, lookahead (üç kesit), stop tarafı + sinyal var, motor dumanı,
kural özel testleri (zigzag, hafta sonu boşluğu, göstergeler)."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.dis import d11g_github as mod
from motor.strateji.dis._gosterge_d11g import andean, d_u_orani, momentum, trix, ultimate_osc, yuzde_zigzag
from motor.strateji.temel import Strateji
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__aroon-uc-deger": dict(uc=90.0, karsi_short=60.0, karsi_long=60.0, aroon_n=25),
    "dis__asiri-bolge-osilator-kesisimi": dict(alt_esik=45.0, ust_esik=55.0, pencere=20),
    "dis__cci-stochrsi-donus": dict(cci_alt=-20.0, cci_ust=20.0, k_alt=60.0, k_ust=40.0, egim_esik=5.0),
    "dis__hafta-sonu-bosluk": dict(min_gap=0.003, yonler="ls"),
    "dis__linreg-rsi-dip": dict(rsi_esik=48.0, atr_min=0.0),
    "dis__obv-onculu-fiyat": dict(pencere=24, chop_esik=70.0),
    "dis__pump-mumu-devam": dict(kisa_esik=0.012, uzun_esik=0.02, fitil_max=0.06),
    "dis__rsi-boga-ayi-rejim": dict(boga_long=50.0, ayi_long=45.0, ayi_short=55.0, boga_short=60.0,
                                    idle_long=45.0, idle_short=55.0, roc_idle=0.0, sma_y=100),
    "dis__sma400-tukenme": dict(sapma=0.01, chop_esik=100.0, rsi_esik=45.0, sma_n=100),
    "dis__tepeden-dusus-dip": dict(dusus=0.02, pencere=24),
    "dis__uo-obv-dip": dict(uo_alt=48.0),
    "dis__alligator-dizilim": dict(esik=0.0, gator=0),
    "dis__bb-stoch-gu-dip": dict(bb_oran=1.1, stoch_ust=60.0, gu60_max=9.0, gu12_max=9.0),
    "dis__adx-seviye-durumu": dict(ust=22.0, alt=17.0),
    "dis__andean-osilator": dict(uzunluk=20),
}


def veri(sinif, n=4000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="1h", baslangic="2022-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    p = sinif.varsayilan_parametreler
    return {"yonler": "short"} if "yonler" in p and p["yonler"] != "short" else {}


def test_ad_ve_sayi():
    assert len(SINIFLAR) == 19
    assert len(set(ADLAR)) == 19 and all(a.startswith("dis__") for a in ADLAR)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.cikis_var_mi() and s.stil == "daytrade"
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(sinif, n=1800)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif)
    for s in (olustur(sinif, yonler="ls") if "yonler" in sinif.varsayilan_parametreler else olustur(sinif),
              olustur(sinif, **kisa_ek(sinif))):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    ek = {"yonler": "ls"} if "yonler" in sinif.varsayilan_parametreler else {}
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


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(sinif, n=1800)
    sonuc = backtest(df, olustur(sinif, **kisa_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- göstergeler / kural özel
def test_gostergeler_nedensel_ve_sinirlar():
    r = np.random.default_rng(4)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 900))))
    h, l = x * (1 + r.uniform(0, 0.005, 900)), x * (1 - r.uniform(0, 0.005, 900))
    o = x.shift(1).fillna(x.iloc[0])
    uo = ultimate_osc(h, l, x)
    assert uo.dropna().between(0, 100).all() and uo.dropna().shape[0] > 800
    pdt.assert_series_equal(uo.iloc[:500], ultimate_osc(h.iloc[:500], l.iloc[:500], x.iloc[:500]))
    a = andean(o, x)
    pdt.assert_frame_equal(a.iloc[:500], andean(o.iloc[:500], x.iloc[:500]))
    assert (a.dropna() >= 0).all().all()
    pdt.assert_series_equal(trix(x, 9).iloc[:400], trix(x.iloc[:400], 9))
    assert abs(momentum(x, 10).iloc[-1] - 100 * x.iloc[-1] / x.iloc[-11]) < 1e-9
    assert (d_u_orani(x, 12).dropna() >= 0).all()


def test_zigzag_donus_ve_onay():
    kap = np.r_[np.full(5, 100.0), np.linspace(100, 110, 6), np.linspace(110, 100, 11), np.linspace(100, 108, 9)]
    z = yuzde_zigzag(pd.Series(kap), 0.03)
    assert z["durum"].iloc[0] == 1 and not z["donus_long"].iloc[:11].any()
    i_short = int(np.argmax(z["donus_short"].to_numpy()))
    assert kap[i_short] <= 110 * 0.97 and kap[i_short - 1] > 110 * 0.97     # %3 düşüş ilk gördüğü mumda
    i_long = int(np.argmax(z["donus_long"].to_numpy()))
    assert i_long > i_short and z["durum"].iloc[i_long] == 1


def test_hafta_sonu_bosluk_sentetik():
    idx = pd.date_range("2024-01-01", periods=24 * 21, freq="1h", tz="UTC", name="zaman")   # Pazartesi'den 3 hafta
    kap = np.full(len(idx), 100.0)
    # Cuma 20:00 sonrası fiyat 97'ye düşer, Pazar 22:00'da hâlâ 97 (Cuma kapanışı 100)
    cuma_20 = np.where((idx.dayofweek == 4) & (idx.hour == 20))[0][0]
    kap[cuma_20 + 1:cuma_20 + 61] = 97.0
    df = mumlar_kapanistan(kap, genlik=0.05, freq="1h", baslangic="2024-01-01")
    s = mod.HaftaSonuBosluk().sinyaller(df)
    giris = s[s.yon == 1]
    assert len(giris) == 1
    t = giris.index[0]
    assert t.dayofweek == 6 and t.hour == 22
    assert giris.zaman_cikisi_mum.iloc[0] == 72
    # boşluk yoksa sinyal yok
    duz = mumlar_kapanistan(np.full(len(idx), 100.0), genlik=0.05, freq="1h", baslangic="2024-01-01")
    assert (mod.HaftaSonuBosluk().sinyaller(duz).yon == 0).all()


def test_gecersiz_mod_hata():
    df = veri(None, n=300)
    with pytest.raises(ValueError):
        mod.IkiGostergeEgimi(mod="yok").sinyaller(df)
    with pytest.raises(ValueError):
        mod.AsiriBolgeOsilatorKesisimi(mod="yok").sinyaller(df)


def test_pump_mumu_tek_giris_ve_stop():
    kap = np.r_[np.full(30, 100.0), 103.0, np.full(10, 103.0)]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="1h")
    s = mod.PumpMumuDevam().sinyaller(df)
    assert s.yon.iloc[30] == 1 and (s.yon.iloc[:30] == 0).all()
    assert abs(s.stop.iloc[30] - 103.0 * 0.95) < 1e-9


def test_oy_toplami_cikis_ve_giris_esigi():
    df = veri(None, n=1500)
    s = mod.GostergeOyToplami(esik=3).sinyaller(df)
    s1 = mod.GostergeOyToplami(esik=1).sinyaller(df)
    assert (s.yon != 0).sum() <= (s1.yon != 0).sum()
