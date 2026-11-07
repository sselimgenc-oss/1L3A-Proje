"""D10-d (kodlama kuyruğu, harf d) stratejileri: sözleşme/ızgara, lookahead (üç kesit), stop/hedef tarafı, sinyal üretimi, motor dumanı,
yardımcı göstergeler ve kural özel testleri."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d10d_kitap as mod
from motor.strateji.dis._gosterge_d10d import abcd_c_durumu, diverjans_durumu, kama_durumu, tuzak_durumu
from motor.strateji.temel import Strateji
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar
from testler.test_dis_d4 import abd_mumlari, is_gunleri

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
TF = {"dis__d1h1-macd": "1h", "dis__voltran-2a": "1h", "dis__voltran-2b": "1h", "dis__seans-yeniden-acilis-long": "1h",
      "dis__aksam-momentumu": "15min", "dis__tuzak-kirilim": "15min", "dis__ilk-yarim-saat-son-yarim-saat": "15min"}
# rastgele veride yeterli sinyal için gevşek parametreler
GEVSEK = {
    "dis__gun-zirvesi-sikisma-kirilimi": dict(dar_k=3.0, yapisma_atr=1.0),
    "dis__aksam-momentumu": dict(esik_k=0.3, bas_saat=12, bit_saat=22),
    "dis__tuzak-kirilim": dict(mtf_filtre=False, n_tepe=40, n_dip=6),
    "dis__abcd-c-girisi": dict(ab_atr=1.5, yakin_atr=3.0, min_rr=0.2),
    "dis__voltran-2a": dict(skor_esik=50, htf_mod=2),
    "dis__voltran-2b": dict(htf_mod=2),
}


def veri(sinif, n=6000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq=TF.get(sinif.ad, "5min"), baslangic="2022-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    return {"short": True} if "short" in sinif.varsayilan_parametreler else {}


def test_ad_ve_sayi():
    assert len(SINIFLAR) == 17
    assert len(set(ADLAR)) == len(ADLAR)
    assert all(a.startswith("dis__") for a in ADLAR)


def test_kayit_dogrula_temiz():
    assert kayit.dogrula() == []
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__ == mod.__name__}
    assert kayitli == set(ADLAR)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara(sinif):
    s = sinif()
    assert s.cikis_var_mi() and s.stil in ("scalp", "daytrade", "swing")
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(sinif, n=1500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif)
    for s in (olustur(sinif), olustur(sinif, **kisa_ek(sinif))):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_bari_degisince_gecmis_ayni(sinif):
    df = veri(sinif)
    s = olustur(sinif, **kisa_ek(sinif))
    tam = s.sinyaller(df)
    k = len(df) // 2
    df2 = df.copy()
    df2.iloc[k:, df2.columns.get_indexer(["yuksek", "dusuk", "kapanis", "acilis"])] *= 1.7
    pdt.assert_frame_equal(s.sinyaller(df2).iloc[:k], tam.iloc[:k])


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
    df = veri(sinif, n=2500)
    sonuc = backtest(df, olustur(sinif, **kisa_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- yardımcı göstergeler
def test_yardimcilar_nedensel():
    df = rastgele_mumlar(3000, seed=2, freq="5min")
    y, d, k = df.yuksek.to_numpy(), df.dusuk.to_numpy(), df.kapanis.to_numpy()
    mom = k - np.r_[np.full(10, np.nan), k[:-10]]
    a = pd.Series(df.yuksek - df.dusuk).rolling(14).mean().to_numpy()
    n = 1700
    for tm in (False, True):
        pdt.assert_frame_equal(diverjans_durumu(y, d, mom, tepe_modu=tm).iloc[:n],
                               diverjans_durumu(y[:n], d[:n], mom[:n], tepe_modu=tm))
        pdt.assert_frame_equal(kama_durumu(y, d, tepe_modu=tm).iloc[:n], kama_durumu(y[:n], d[:n], tepe_modu=tm))
        pdt.assert_frame_equal(abcd_c_durumu(y, d, a, ab_atr=1.0, tepe_modu=tm).iloc[:n],
                               abcd_c_durumu(y[:n], d[:n], a[:n], ab_atr=1.0, tepe_modu=tm))
    assert (tuzak_durumu(y, d, k, 40, 6)[:n] == tuzak_durumu(y[:n], d[:n], k[:n], 40, 6)).all()


def test_tuzak_durumu_senaryo():
    # 50 mum yatay, tepe (110), geri çekilme (dip altı), sonra tepe üstü kapanış
    kap = [100.0] * 50 + [105, 110, 108, 104, 98, 99, 101, 104, 109, 111, 112]
    df = mumlar_kapanistan(kap, genlik=0.3)
    s = tuzak_durumu(df.yuksek.to_numpy(), df.dusuk.to_numpy(), df.kapanis.to_numpy(), n_tepe=30, n_dip=3, geri_max=12, donus_max=8)
    assert s[:59].sum() == 0 and s[59]           # 111 kapanışı 110.3 tepesinin üstünde


def test_diverjans_boga_senaryo():
    # fiyat: dip C (95), tepe, daha düşük dip A (93); momentum ikinci dipte daha yüksek
    kap = np.r_[np.linspace(100, 95, 8), np.linspace(95.7, 103, 7), np.linspace(102.3, 93, 10), np.linspace(93.8, 99, 7)]
    mom = np.r_[np.linspace(-1, -5, 8), np.linspace(-4, 3, 7), np.linspace(2.5, -2, 10), np.linspace(-1.5, 2, 7)]
    d = diverjans_durumu(kap + 0.2, kap - 0.2, mom, k=2, min_aralik=6, max_aralik=60, gecerlilik=30)
    assert d["aktif"].any()
    assert (d.loc[d["aktif"], "a_fiyat"] < d.loc[d["aktif"], "c_fiyat"]).all()
    assert (d.loc[d["aktif"], "e_seviye"] > 0).all()


def test_stokastik_pop_senaryo():
    kap = np.r_[np.full(30, 100.0), np.linspace(100, 110, 15), np.linspace(110, 100, 15)]
    df = mumlar_kapanistan(kap, genlik=0.4, freq="5min")
    sig = mod.StokastikPop(stop_atr_k=3.0).sinyaller(df)
    assert (sig.yon == 1).any() and sig.cikis_long.any()
    ilk = sig.index[sig.yon == 1][0]
    assert df.index.get_loc(ilk) >= 30


def test_ilk_yarim_saat_abd_hisse():
    df = abd_mumlari(is_gunleri("2024-01-02", "2024-03-29"), dk=5, seed=3)
    s = mod.IlkYarimSaatSonYarimSaat(seans="abd_hisse", ilk_dk=30, son_dk=30)
    sig = s.sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 20
    # her seans başına en çok bir giriş ve giriş son yarım saatte (NY 15:25 civarı)
    ny = giris.index.tz_convert("America/New_York")
    assert (ny.hour * 60 + ny.minute >= 15 * 60).all()
    assert pd.Series(ny.date).duplicated().sum() == 0
    tam = s.sinyaller(df)
    pdt.assert_frame_equal(s.sinyaller(df.iloc[:6000]), tam.iloc[:6000])


def test_seans_yeniden_acilis_saat_ve_pazartesi():
    df = rastgele_mumlar(24 * 30, seed=1, freq="1h", baslangic="2022-01-03")      # 03.01.2022 Pazartesi
    sig = mod.SeansYenidenAcilisLong(giris_saat=23).sinyaller(df)
    gir = sig.index[sig.yon == 1]
    assert len(gir) > 0 and (gir.hour == 22).all()                                # sinyal mumu 22:00-23:00; dolum 23:00 açılışı
    assert ((gir + pd.Timedelta(hours=1)).dayofweek != 0).all()
    assert (sig.loc[gir, "zaman_cikisi_mum"] == 2).all()
