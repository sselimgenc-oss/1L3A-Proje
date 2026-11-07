"""D9-B (dis_envanter atlananlar B yarısı + ek_77 tek-grafik maddeler) stratejileri: sözleşme/ızgara, lookahead (üç kesit),
stop/hedef tarafı, sinyal üretimi, motor dumanı, kural özel testleri (BBRSI, baş-omuz, shooting star, BTFD, W dibi, seans)."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d9_atlanan_b as mod
from motor.strateji.dis._gosterge_d9 import (
    ardisik_say, cmo, fisher_rsi, kdj, pinball, pivot_seviye, rmi, vfi)
from motor.strateji.temel import Strateji
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar
from testler.test_dis_d4 import abd_mumlari, is_gunleri

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
GUNLUK = {"dis__btfd-gunluk-dip", "dis__gosterge-rezonansi", "dis__ma-dizilim-5-10-30", "dis__macd-sma-cift",
          "dis__rsi-ma-normal", "dis__rsi-ma-uc", "dis__gmma-ls", "dis__bas-omuz-rsi-short", "dis__shooting-star-onay",
          "dis__ha-guclu-dusus-al", "dis__ema-esik-trend", "dis__mtf-rsi-trend", "dis__ft-highwave"}
SEANSLI = {"dis__sma20-scalp", "dis__alpaca-momentum"}
TF_STIL = {"scalp": "15min", "daytrade": "1h", "swing": "4h"}
# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__ft-low-bb": dict(alt_pay=0.0),
    "dis__ft-strategy002": dict(rsi_alt=90.0, stoch_alt=100.0, cekic_alt_k=0.3, cekic_ust=1.0),
    "dis__solipsis-rmi": dict(dus_seri=1, pinball_maks=100.0, adr_k=10.0, rmi_alt=0.0, rmi_ust=100.0, ma_seri=0),
    "dis__pivot-kirilim-hacim": dict(hacim_k=0.0, pivot_n=2),
    "dis__alpaca-momentum": dict(min_yuk=-1.0, hacim_k=0.0),
    "dis__sma20-scalp": dict(),
    "dis__shooting-star-onay": dict(ust_k=0.5, yukselis_n=1),
    "dis__macd-sma-cift": dict(pencere=6),
    "dis__mtf-rsi-trend": dict(seviye=45.0, rsi_n=14),
    "dis__bas-omuz-rsi-short": dict(omuz_tol=0.3, pivot_n=2),
}
ADLAR = [c.ad for c in SINIFLAR]


def tf_of(sinif):
    if sinif.ad in GUNLUK:
        return "1D"
    return TF_STIL[sinif.stil]


def veri(sinif, n=None, seed=11):
    if sinif.ad in SEANSLI:
        return abd_mumlari(is_gunleri("2024-01-02", "2024-03-29"), dk=5, seed=seed)
    n = n or {"1D": 2500, "4h": 4500, "1h": 4000, "15min": 5000}[tf_of(sinif)]
    return rastgele_mumlar(n, seed=seed, freq=tf_of(sinif), baslangic="2018-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    p = sinif.varsayilan_parametreler
    if "short" in p:
        return {"short": True}
    if "yonler" in p and p["yonler"] != "short":
        return {"yonler": "ls"}
    return {}


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) >= 50
    assert len(set(ADLAR)) == len(ADLAR)
    assert all(a.startswith("dis__") for a in ADLAR)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.cikis_var_mi() and s.stil in ("scalp", "daytrade", "swing")
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


# ---------------------------------------------------------------- lookahead / stop tarafı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif)
    for s in (olustur(sinif), olustur(sinif, **kisa_ek(sinif))):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    sig = olustur(sinif, **kisa_ek(sinif)).sinyaller(df)
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


# ---------------------------------------------------------------- göstergeler
def test_gostergeler_nedensel_ve_sinirlar():
    r = np.random.default_rng(4)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 900))))
    h = x * (1 + r.uniform(0, 0.005, 900))
    l = x * (1 - r.uniform(0, 0.005, 900))
    v = pd.Series(r.uniform(1, 3, 900))
    for f in (lambda: cmo(x, 14), lambda: fisher_rsi(x), lambda: rmi(x, 14, 3), lambda: pinball(x, 3),
              lambda: vfi(h, l, x, v, 50, std_n=20), lambda: kdj(h, l, x, 9)["j"]):
        tam = f()
        assert tam.dropna().shape[0] > 100
    assert cmo(x).dropna().abs().max() <= 100.0 + 1e-9
    assert fisher_rsi(x).dropna().abs().max() <= 1.0
    assert 0.0 <= rmi(x).dropna().min() and rmi(x).dropna().max() <= 100.0
    # kısaltılmış seride aynı değerler
    pdt.assert_series_equal(cmo(x.iloc[:500], 14), cmo(x, 14).iloc[:500])
    pdt.assert_series_equal(rmi(x.iloc[:500]), rmi(x).iloc[:500])
    pdt.assert_series_equal(vfi(h.iloc[:500], l.iloc[:500], x.iloc[:500], v.iloc[:500], 50, std_n=20),
                            vfi(h, l, x, v, 50, std_n=20).iloc[:500])


def test_pivot_seviye_onay_gecikmesi():
    y = pd.Series([1, 2, 3, 9, 4, 3, 2, 1, 1, 1], dtype=float)
    s = pivot_seviye(y, 2, 2, True)
    assert s.iloc[:5].isna().all()          # pivot (indeks 3) ancak indeks 5'te onaylanır
    assert s.iloc[5] == 9.0 and s.iloc[-1] == 9.0
    assert ardisik_say(pd.Series([True, True, False, True])).tolist() == [1, 2, 0, 1]


# ---------------------------------------------------------------- kural özel testleri
def test_btfd_dip_ve_zaman_cikisi():
    df = rastgele_mumlar(300, seed=3, freq="1D", baslangic="2020-01-01")
    df.loc[df.index[100], "dusuk"] = df["yuksek"].iloc[100] * 0.97   # %3 aralık
    sig = mod.BtfdGunlukDip(dusus=0.02).sinyaller(df)
    assert sig["yon"].iloc[100] == 1
    assert sig["zaman_cikisi_mum"].iloc[100] == 2


def test_bbrsi_saf_kural_stop_ve_hedef():
    kap = np.r_[np.full(300, 100.0) + np.sin(np.arange(300) / 3.0) * 0.3, np.linspace(100, 92, 5),
                np.linspace(92, 99, 30), np.full(30, 99.0)]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="15min")
    sig = mod.BbrsiDonus(bb_n=50, short=True).sinyaller(df)
    g = sig[sig.yon == 1]
    assert len(g) > 0
    assert (g.stop < df.kapanis[g.index]).all() and (g.hedef > df.kapanis[g.index]).all()
    # hedef = giriş + tp_k x (giriş - stop)
    r = (df.kapanis[g.index] - g.stop)
    assert np.allclose(g.hedef - df.kapanis[g.index], r)


def test_bas_omuz_sentetik_formasyon():
    # sol omuz, baş, sağ omuz, boyun çizgisi altına kırılım
    parca = [100] * 40 + list(np.linspace(100, 110, 8)) + list(np.linspace(110, 102, 8)) + list(np.linspace(102, 118, 8)) \
        + list(np.linspace(118, 102, 8)) + list(np.linspace(102, 109, 8)) + list(np.linspace(109, 95, 12)) + [95] * 20
    df = mumlar_kapanistan(parca, genlik=0.3, freq="1D")
    sig = mod.BasOmuzRsiShort(pivot_n=3, omuz_tol=0.1, bekle=15).sinyaller(df)
    g = sig[sig.yon == -1]
    assert len(g) >= 1
    assert (g.stop > df.kapanis[g.index]).all()


def test_shooting_star_onay_gerekli():
    kap = np.r_[np.linspace(100, 110, 30), [110.0, 109.0], np.full(20, 105.0)]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="1D")
    i = 30
    df.iloc[i, df.columns.get_loc("acilis")] = 110.0
    df.iloc[i, df.columns.get_loc("kapanis")] = 109.8
    df.iloc[i, df.columns.get_loc("yuksek")] = 113.0      # uzun üst fitil
    df.iloc[i, df.columns.get_loc("dusuk")] = 109.75
    sig = mod.ShootingStarOnay().sinyaller(df)
    assert (sig["yon"].iloc[:i + 1] == 0).all()            # yıldız mumunun kendisinde sinyal yok (onay gerekir)
    assert sig["yon"].iloc[i + 1] == -1                    # ertesi mum yıldızın düşüğünün altında kapandı
    assert sig["zaman_cikisi_mum"].iloc[i + 1] == 7


def test_rsi_ma_gecersiz_mod_hata():
    with pytest.raises(ValueError):
        mod.RsiMaNormal(mod="x").sinyaller(rastgele_mumlar(300, freq="1D"))


def test_ma_cift_gecersiz_tip_hata():
    with pytest.raises(ValueError):
        mod.MaCiftCross(ma_tipi="wma").sinyaller(rastgele_mumlar(300, freq="4h"))


def test_williams_supertrend_yalniz_filtreli_giris():
    df = veri(mod.WilliamsRSupertrend)
    sig = mod.WilliamsRSupertrend().sinyaller(df)
    assert (sig.yon == 1).any() and (sig.yon == -1).any()


def test_alpaca_yalniz_pencere_ve_seans_sonu():
    df = veri(mod.AlpacaMomentum)
    s = olustur(mod.AlpacaMomentum, son_dk=60.0).sinyaller(df)
    giris = s[s.yon == 1]
    assert len(giris) > 0
    yerel = giris.index.tz_convert("America/New_York")
    dk = (yerel.hour * 60 + yerel.minute) - (9 * 60 + 30) + 5      # bar kapanışı, açılıştan geçen dk
    assert ((dk > 15) & (dk <= 60)).all()
    assert s["cikis"].any()                                        # seans sonu çıkışı


def test_sma20_scalp_seans_sonunda_giris_yok():
    df = veri(mod.Sma20Scalp)
    s = mod.Sma20Scalp().sinyaller(df)
    yerel = s.index[s.yon == 1].tz_convert("America/New_York")
    assert len(yerel) > 0 and (yerel.hour * 60 + yerel.minute < 15 * 60 + 55).all()


def test_mtf_haftalik_rsi_gecmise_bakar():
    df = rastgele_mumlar(1500, seed=9, freq="1D", baslangic="2016-01-01")
    s = olustur(mod.MtfRsiTrend)
    a = s.sinyaller(df)
    b = s.sinyaller(df.iloc[:900])
    pdt.assert_frame_equal(a.iloc[:900], b)


def test_kayit_ve_dogrula():
    """Modül dis paketinde taranıyorsa: kayıtlı küme sınıf kümesine eşit, dogrula() sorunsuz, ad çakışması yok."""
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.endswith("d9_atlanan_b")}
    assert kayitli == set(ADLAR)
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []
