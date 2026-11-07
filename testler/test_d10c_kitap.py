"""D10-C kitap stratejileri (19 aile): sözleşme/ızgara, lookahead (üç kesit), stop/hedef tarafı, sinyal üretimi, motor dumanı,
gösterge ve kural özel testleri."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis import d10c_kitap as mod
from motor.strateji.dis._gosterge_d10c import aroon, h_say, pmax, qqe, vwma
from motor.strateji.temel import Strateji
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
# rastgele (kısa hafızalı, düz hacimli) veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__cpr-camarilla-kirilim": dict(dar_oran=0.34, dunden_dar=0, hacim_sart=0, bekle_n=3),
    "dis__hacim-patlama-kirilimi": dict(hacim_k=1.4),
    "dis__brooks-ma-bosluk": dict(bosluk_n=5),
    "dis__rudd-gunluk-kurulum-5dk-kirilim": dict(alt_oran=0.9, yakin_oran=0.9, ust_kapanis=0.9, alan_atr=0.0,
                                                 acilis_tol=2.0, pencere_n=2),
    "dis__dar-gun-acilis-kirilimi": dict(k=0.02),
    "dis__3gun-momentum-acilis-hacmi": dict(gun_n=1, hacim_k=0.0),
}


def veri(n=6000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="5min", baslangic="2024-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    return {"yonler": "ls"} if sinif.varsayilan_parametreler.get("yonler") != "short" else {}


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) == 19
    assert len(set(ADLAR)) == 19 and all(a.startswith("dis__") for a in ADLAR)


def test_kayit_dogrula_kendi_adlari():
    sorunlar = kayit.dogrula()
    assert [s for s in sorunlar if any(a in s for a in ADLAR)] == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.cikis_var_mi() and s.stil in ("scalp", "daytrade", "swing")
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(2500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


# ---------------------------------------------------------------- lookahead / stop tarafı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri()
    for s in (olustur(sinif), olustur(sinif, **kisa_ek(sinif))):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_degisimi_gecmisi_degistirmez(sinif):
    df = veri()
    k = len(df) // 2
    df2 = df.copy()
    gel = df2.iloc[k:].copy()
    df2.iloc[k:, df2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] = gel[["acilis", "yuksek", "dusuk", "kapanis"]].to_numpy() * 1.37
    df2.iloc[k:, df2.columns.get_loc("hacim")] = gel["hacim"].to_numpy() * 5.0
    s = olustur(sinif, **kisa_ek(sinif))
    pdt.assert_frame_equal(s.sinyaller(df).iloc[:k], s.sinyaller(df2).iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri()
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
    df = veri(2500)
    sonuc = backtest(df, olustur(sinif, **kisa_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- göstergeler
def test_aroon_sinirlari_ve_kural():
    x = pd.Series(np.arange(60, dtype=float))
    a = aroon(x + 1, x, 10)
    assert a["up"].iloc[-1] == 100.0 and a["down"].iloc[-1] == 0.0       # sürekli yükseliş
    assert a["up"].iloc[:10].isna().all()
    r = np.random.default_rng(1)
    h = pd.Series(100 + np.cumsum(r.normal(0, 1, 200)))
    a2 = aroon(h + 0.5, h - 0.5, 14)
    assert a2.dropna().min().min() >= 0 and a2.dropna().max().max() <= 100


def test_vwma_esit_hacimde_sma():
    k = pd.Series(np.arange(1.0, 40.0))
    pdt.assert_series_equal(vwma(k, pd.Series(1.0, index=k.index), 5), k.rolling(5).mean())


def test_pmax_yon_ve_cizgi_tarafi():
    k = pd.Series(100 + np.r_[np.arange(60), np.arange(60)[::-1]].astype(float))
    pm = pmax(k + 0.5, k - 0.5, k, 5, 5, 2.0)
    yesil = pm["yon"] == 1
    kirmizi = pm["yon"] == -1
    assert yesil.any() and kirmizi.any()
    assert (pm["cizgi"][yesil] <= pm["ma"][yesil] + 1e-9).all()      # yeşil: çizgi MA altında
    assert (pm["cizgi"][kirmizi] >= pm["ma"][kirmizi] - 1e-9).all()  # kırmızı: çizgi MA üstünde


def test_qqe_yon_degerleri():
    r = np.random.default_rng(2)
    k = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 800))))
    q = qqe(k)
    assert set(q["yon"].unique()) <= {-1.0, 0.0, 1.0} and (q["yon"] != 0).any()
    assert q["yon"].iloc[:20].eq(0).all()


def test_h_say_h2_kurali():
    #            0     1     2     3     4     5     6     7
    y = np.array([10.0, 11.0, 12.0, 11.5, 11.8, 11.2, 11.6, 11.9])
    d = np.array([9.0, 10.0, 11.0, 10.8, 11.0, 10.7, 10.9, 11.0])
    tr = np.ones(8, bool)
    sig2, stop2 = h_say(y, d, tr, 2)
    sig1, stop1 = h_say(y, d, tr, 1)
    assert list(np.flatnonzero(sig1)) == [4]             # geri çekilmeden (mum 3) sonraki ilk deneme (H1)
    assert list(np.flatnonzero(sig2)) == [6]             # mum 5 geri düştü, mum 6 = ikinci deneme (H2)
    assert stop2[6] == pytest.approx(10.7)


# ---------------------------------------------------------------- kural özel testleri
def _seans_verisi(gunler, ilk_ac=None, **kw):
    """Gün başına 48 mum (30 dk), UTC gün = seans; düz zaman serisi ince ayar için mumlar_kapanistan."""
    n = gunler * 48
    kap = 100 + np.zeros(n)
    return mumlar_kapanistan(kap, genlik=0.2, baslangic="2024-03-04", freq="30min", **kw)


def test_zaman_kirilimi_kutu_ve_giris():
    # 08:00 UTC'de önceki 4 mumun kutusu (99.8-100.2); 08:00 mumu kutu üstünde kapanır
    n = 48 * 3
    kap = np.full(n, 100.0)
    kap[48 + 17] = 101.0           # 2. gün 08:30 kapanışı: kutu yüksekliği 0.4, tepe 100.2 + 0.2*0.4 -> kırılım
    df = mumlar_kapanistan(kap, genlik=0.2, baslangic="2024-03-04", freq="30min")
    s = mod.ZamanKirilimi(saat=8.0, geri_n=4, pencere_mum=4, giris_pay=0.2, yonler="long").sinyaller(df)
    gir = s[s.yon == 1]
    assert len(gir) == 1 and gir.index[0] == df.index[48 + 17]
    assert gir.stop.iloc[0] == pytest.approx(df["dusuk"].iloc[48 + 12:48 + 16].min(), abs=1.0)   # kutu dibi civarı
    assert gir.stop.iloc[0] < 100.0


def test_acilis_yanlilik_ilk_kirilim():
    # gün 1: ATR ısınması için sakin gün. gün 2: ilk mum yükseliş; zirve; 2 mum zirveyi geçemez; kapanışla kırılım -> long
    g1 = 100 + 0.05 * np.sin(np.arange(48))
    g2 = np.array([100.5, 102.0, 101.5, 101.4, 103.0, 103.5] + [103.0] * 42, dtype=float)
    df = mumlar_kapanistan(np.r_[g1, g2], genlik=0.1, baslangic="2024-03-04", freq="30min")
    s = mod.AcilisYanlilikGeriCekilme(geri_n=2, yonler="ls").sinyaller(df)
    assert list(s.index[s.yon == 1]) == [df.index[48 + 4]] and (s.yon == -1).sum() == 0
    assert s.stop[df.index[48 + 4]] < 101.5


def test_gap_onceki_kapanis_long_ve_tek_giris():
    # gün 1 kapanış 100; gün 2: 99'da açılır, 100.5'e geçer ve tutunur -> long (tut_n=2)
    g1 = np.full(48, 100.0)
    g2 = np.r_[np.full(10, 99.0), np.full(38, 100.6)]
    df = mumlar_kapanistan(np.r_[g1, g2], genlik=0.05, baslangic="2024-03-04", freq="30min")
    s = mod.GapOncekiKapanisTepki(tut_n=2, yonler="long").sinyaller(df)
    gir = s[s.yon == 1]
    assert len(gir) == 1 and gir.index[0] == df.index[48 + 11]       # geçiş 10. mumda, 2. tutunan mum = 11
    assert gir.stop.iloc[0] < 100.0


def test_bist_uclu_oy_yalniz_uzlasmada():
    df = veri(6000)
    s = mod.BistUcluSistemOyu(yonler="ls").sinyaller(df)
    assert (s.yon != 0).sum() > 0
    # uzlaşma yoksa giriş yok: tek alt sistem değişse giriş sayısı değişir ama hiçbir giriş aynı anda iki yönde olamaz
    assert not ((s.yon == 1) & (s.yon == -1)).any()


def test_3gun_momentum_yalniz_long_ve_seans_ilk_mumu():
    df = veri(6000)
    s = olustur(mod.UcGunMomentumAcilisHacmi).sinyaller(df)
    assert (s.yon == -1).sum() == 0
    gir = s[s.yon == 1].index
    assert len(gir) > 0 and all((t.hour == 0 and t.minute == 0) for t in gir)


def test_hacim_patlama_stop_patlama_dibi():
    n = 80
    kap = np.full(n, 100.0)
    kap[40] = 100.5
    kap[42] = 101.5          # patlama mumunun (40) yükseğinin üstünde kapanış
    df = mumlar_kapanistan(kap, genlik=0.1, hacim=1.0, baslangic="2024-03-04", freq="5min")
    df.iloc[40, df.columns.get_loc("hacim")] = 10.0
    s = mod.HacimPatlamaKirilimi(hacim_k=3.0, gecerlilik=5, yonler="long", hedef_r=2.0).sinyaller(df)
    gir = s[s.yon == 1]
    assert len(gir) == 1 and gir.index[0] == df.index[42]
    assert gir.stop.iloc[0] < df["dusuk"].iloc[40]


def test_dar_gun_sadece_dar_gunde():
    # 12 geniş gün + 1 dar gün + 1 işlem günü
    gun_say = 14
    kap = []
    for g in range(gun_say):
        if g == 12:
            kap += list(np.full(48, 100.0) + np.linspace(0, 0.1, 48))          # dar gün (yukarı kapanış)
        elif g == 13:
            kap += [100.1] * 4 + [104.0] * 44
        else:
            kap += list(100 + 5 * np.sin(np.linspace(0, 6, 48)))
    df = mumlar_kapanistan(np.array(kap), genlik=0.2, baslangic="2024-03-04", freq="30min")
    s = mod.DarGunAcilisKirilimi(k=0.2, yonler="ls").sinyaller(df)
    gir = s[s.yon != 0]
    assert len(gir) == 1 and gir.index[0].date() == df.index[13 * 48].date() and gir.yon.iloc[0] == 1
