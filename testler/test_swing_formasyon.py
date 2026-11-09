"""Swing formasyon aileleri: lookahead, sentetik formasyon, stop yönü."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji.swing.aralik_ticareti import AralikTicareti
from motor.strateji.swing.cift_dip_tepe import CiftDipTepe
from motor.strateji.swing.fib_geri_cekilme import FibGeriCekilme
from motor.strateji.swing.konsolidasyon_kirilim import KonsolidasyonKirilim
from motor.strateji.swing.mum_yutan_donus import MumYutanDonus


def rastgele(n=900, seed=11):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap,
                         "hacim": rng.uniform(0.5, 3.0, n)}, index=idx)


def yoldan(kapanislar, w=0.1, hacim=None):
    """Kapanış yolundan OHLC: açılış = önceki kapanış, fitil = w."""
    k = np.asarray(kapanislar, float)
    ac = np.r_[k[0], k[:-1]]
    idx = pd.date_range("2024-01-01", periods=len(k), freq="1h", tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, k) + w, "dusuk": np.minimum(ac, k) - w,
                         "kapanis": k, "hacim": 1.0 if hacim is None else hacim}, index=idx)


def ayna(df, eksen=200.0):
    return pd.DataFrame({"acilis": eksen - df.acilis, "yuksek": eksen - df.dusuk, "dusuk": eksen - df.yuksek,
                         "kapanis": eksen - df.kapanis, "hacim": df.hacim}, index=df.index)


def yol(*parcalar):
    """(hedef, adim_sayisi) parçalarını doğrusal birleştirir."""
    cikti = [parcalar[0]]
    for hedef, adim in parcalar[1:]:
        cikti += list(np.linspace(cikti[-1], hedef, adim + 1)[1:])
    return cikti


def kontrol_stop_tarafi(sig, df):
    g = sig[sig.yon != 0]
    assert g.stop.notna().all()
    kap = df.kapanis[g.index]
    uzun, kisa = g[g.yon == 1], g[g.yon == -1]
    assert (uzun.stop < kap[uzun.index]).all()
    assert (kisa.stop > kap[kisa.index]).all()
    h = g.dropna(subset=["hedef"])
    assert (h[h.yon == 1].hedef > kap[h[h.yon == 1].index]).all()
    assert (h[h.yon == -1].hedef < kap[h[h.yon == -1].index]).all()


# ---------------------------------------------------------------- lookahead

STRATEJILER = [
    (KonsolidasyonKirilim, [{}, {"uzunluk": 10, "hacim_k": 0.0, "tampon_atr": 0.0, "maks_genislik_atr": 20.0}]),
    (CiftDipTepe, [{}, {"tolerans_yuzde": 3.0, "min_arasi": 3, "min_derinlik_atr": 0.5},
                   {"pivot_yontemi": "zigzag", "tolerans_yuzde": 3.0, "min_derinlik_atr": 0.5, "rsi_esik": 40.0}]),
    (FibGeriCekilme, [{}, {"giris_alt": 0.3, "giris_ust": 0.786}, {"pivot_yontemi": "zigzag", "trend_ema": 50}]),
    (AralikTicareti, [{}, {"pencere": 20, "adx_esik": 0.0, "min_genislik_atr": 1.0}]),
    (MumYutanDonus, [{}, {"trend_mum": 3, "trend_min_atr": 0.2, "hacim_k": 1.0}]),
]


@pytest.mark.parametrize("sinif,paramlar", STRATEJILER, ids=[s.__name__ for s, _ in STRATEJILER])
def test_lookahead_yok_ve_sozlesme(sinif, paramlar):
    df = rastgele()
    toplam = 0
    for p in paramlar:
        s = sinif(**p)
        tam = s.sinyaller(df)
        assert tam.index.equals(df.index)
        assert {"yon", "stop", "hedef", "cikis"} <= set(tam.columns)
        kontrol_stop_tarafi(tam, df)
        toplam += int((tam.yon != 0).sum())
        for n in (150, 333, 517, 700):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])
    assert toplam > 0, "rastgele veride hiç sinyal yok: lookahead testi anlamsız kalır"


@pytest.mark.parametrize("sinif", [s for s, _ in STRATEJILER])
def test_aile_kimligi_ve_izgara(sinif):
    s = sinif()
    assert s.ad.startswith("swing__") and s.stil == "swing"
    kombin = int(np.prod([len(v) for v in s.parametre_izgarasi.values()]))
    assert 1 <= kombin <= 27
    assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)


# ---------------------------------------------------------------- sentetik formasyonlar

def cift_dip_yolu():
    return yol(120, (100, 20), (110, 10), (100.3, 10), (112, 8), (116, 4))


def test_cift_dip_boyun_kirilimi_long():
    df = yoldan(cift_dip_yolu())
    s = CiftDipTepe(tolerans_yuzde=1.0, min_arasi=5)
    sig = s.sinyaller(df)
    girisler = sig[sig.yon != 0]
    assert len(girisler) == 1 and girisler.yon.iloc[0] == 1
    t = df.index.get_loc(girisler.index[0])
    boyun = df.yuksek.iloc[20:41].max()
    assert df.kapanis.iloc[t] > boyun
    assert df.kapanis.iloc[t - 1] <= boyun            # ilk kapanış üstü mumda girer
    assert t >= 40 + 3                                # ikinci dip onaylanmadan sinyal yok
    assert girisler.stop.iloc[0] < df.dusuk.iloc[20:41].min()
    assert girisler.hedef.iloc[0] > df.kapanis.iloc[t]
    kontrol_stop_tarafi(sig, df)


def test_cift_tepe_boyun_kirilimi_short():
    df = ayna(yoldan(cift_dip_yolu()))
    sig = CiftDipTepe(tolerans_yuzde=1.0, min_arasi=5).sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.yon.iloc[0] == -1
    assert g.stop.iloc[0] > df.yuksek.iloc[20:41].max()
    assert g.hedef.iloc[0] < df.kapanis[g.index[0]]
    # short kapalıyken sinyal yok
    assert (CiftDipTepe(short=False).sinyaller(df).yon == 0).all()


def test_cift_dip_tolerans_asilirsa_sinyal_yok():
    k = yol(120, (100, 20), (110, 10), (103, 10), (112, 8), (116, 4))   # ikinci dip %3 yüksek
    sig = CiftDipTepe(tolerans_yuzde=1.0).sinyaller(yoldan(k))
    assert (sig.yon == 0).all()
    sig2 = CiftDipTepe(tolerans_yuzde=4.0).sinyaller(yoldan(k))
    assert (sig2.yon == 1).sum() == 1


def fib_yolu():
    # 100->105 (önceki tepe), 102'ye düş (D), 120'ye çık (T), 110.5'e geri çekil, toparlan
    return yol(100, (105, 5), (102, 4), (120, 18), (110.5, 9), (113, 1), (116, 3))


def test_fib_geri_cekilme_long():
    df = yoldan(fib_yolu(), w=0.1)
    sig = FibGeriCekilme().sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.yon.iloc[0] == 1
    t = df.index.get_loc(g.index[0])
    assert df.kapanis.iloc[t] > df.acilis.iloc[t]                    # tepki mumu
    T, D = df.yuksek.iloc[:33].max(), df.dusuk.iloc[5:28].min()
    assert abs(g.hedef.iloc[0] - T) < 1e-9                           # hedef önceki tepe
    assert g.stop.iloc[0] < D                                        # stop bacak başlangıcının ötesi
    assert T - 0.618 * (T - D) <= df.dusuk.iloc[t] <= T - 0.382 * (T - D)
    kontrol_stop_tarafi(sig, df)


def test_fib_geri_cekilme_short_ayna():
    df = ayna(yoldan(fib_yolu(), w=0.1))
    sig = FibGeriCekilme().sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.yon.iloc[0] == -1
    kontrol_stop_tarafi(sig, df)
    assert (FibGeriCekilme(short=False).sinyaller(df).yon == 0).all()


def test_fib_stop_asilmis_bacakta_sinyal_yok():
    k = yol(100, (105, 5), (102, 4), (120, 18), (101, 12), (104, 1), (106, 3))  # D'nin altına indi
    sig = FibGeriCekilme().sinyaller(yoldan(k, w=0.1))
    assert (sig.yon == 0).all()


def konsolidasyon_yolu(kirilim_hacim=3.0):
    k = list(np.linspace(90, 100, 15)) + [99.6, 100.4] * 12 + [102.0]
    hacim = np.ones(len(k)); hacim[-1] = kirilim_hacim
    return yoldan(k, w=0.1, hacim=hacim)


def test_konsolidasyon_kirilim_long_hacimli():
    df = konsolidasyon_yolu()
    sig = KonsolidasyonKirilim(uzunluk=15, hacim_k=1.5).sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.index[0] == df.index[-1] and g.yon.iloc[0] == 1
    ust, alt = df.yuksek.iloc[-16:-1].max(), df.dusuk.iloc[-16:-1].min()
    assert abs(g.stop.iloc[0] - alt) < 1e-9
    assert abs(g.hedef.iloc[0] - (102.0 + (ust - alt))) < 1e-9
    kontrol_stop_tarafi(sig, df)


def test_konsolidasyon_dusuk_hacim_filtrelenir():
    df = konsolidasyon_yolu(kirilim_hacim=1.0)
    assert (KonsolidasyonKirilim(uzunluk=15, hacim_k=1.5).sinyaller(df).yon == 0).all()
    assert (KonsolidasyonKirilim(uzunluk=15, hacim_k=0.0).sinyaller(df).yon == 1).sum() == 1


def test_konsolidasyon_short_ayna():
    df = ayna(konsolidasyon_yolu())
    sig = KonsolidasyonKirilim(uzunluk=15, hacim_k=1.5).sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.yon.iloc[0] == -1
    kontrol_stop_tarafi(sig, df)
    assert (KonsolidasyonKirilim(uzunluk=15, short=False).sinyaller(df).yon == 0).all()


def test_aralik_ticareti_alt_uste_long_ust_alta_short():
    # 100-110 arası üçgen dalga, periyot 20
    dalga = yol(105, (110, 5), (100, 10), (110, 10), (100, 10), (110, 10), (100, 10), (110, 10), (100, 10), (105, 5))
    df = yoldan(dalga, w=0.1)
    s = AralikTicareti(pencere=20, adx_esik=0.0)
    sig = s.sinyaller(df)
    uzun, kisa = sig[sig.yon == 1], sig[sig.yon == -1]
    assert len(uzun) > 0 and len(kisa) > 0
    assert (df.kapanis[uzun.index] < 105).all()                      # alt yarıdan al
    assert (df.kapanis[kisa.index] > 105).all()                      # üst yarıdan sat
    assert (uzun.hedef > 105).all() and (kisa.hedef < 105).all()    # hedef karşı sınır
    kontrol_stop_tarafi(sig, df)
    assert (AralikTicareti(pencere=20, adx_esik=0.0, short=False).sinyaller(df).yon != -1).all()


def test_aralik_ticareti_trendde_adx_filtresi():
    df = yoldan(np.linspace(100, 200, 400) + np.tile([0, 1, 0, -1], 100))
    assert (AralikTicareti(pencere=20, adx_esik=20.0).sinyaller(df).yon == 0).all()


def yutan_yolu():
    # düşüş trendi, küçük kırmızı mum, onu yutan yeşil mum
    k = list(np.linspace(112, 100, 16)) + [99.5]
    df = yoldan(k, w=0.1)
    son = pd.DataFrame({"acilis": [99.4], "yuksek": [101.2], "dusuk": [99.3], "kapanis": [101.0], "hacim": [2.0]},
                       index=[df.index[-1] + pd.Timedelta(hours=1)])
    return pd.concat([df, son])


def test_boga_yutan_mum_long():
    df = yutan_yolu()
    sig = MumYutanDonus(trend_mum=6).sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.index[0] == df.index[-1] and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < df.dusuk.iloc[-2:].min()
    risk = 101.0 - g.stop.iloc[0]
    assert abs(g.hedef.iloc[0] - (101.0 + 2.0 * risk)) < 1e-9
    kontrol_stop_tarafi(sig, df)


def test_ayi_yutan_mum_short_ve_hacim_filtresi():
    df = ayna(yutan_yolu())
    sig = MumYutanDonus(trend_mum=6).sinyaller(df)
    g = sig[sig.yon != 0]
    assert len(g) == 1 and g.yon.iloc[0] == -1
    kontrol_stop_tarafi(sig, df)
    assert (MumYutanDonus(trend_mum=6, short=False).sinyaller(df).yon == 0).all()
    # hacim filtresi: son mum hacmi ortalamanın altına inerse sinyal yok
    d2 = yutan_yolu(); d2.iloc[-1, d2.columns.get_loc("hacim")] = 0.5
    assert (MumYutanDonus(trend_mum=6, hacim_k=1.5).sinyaller(d2).yon == 0).all()


def test_yutan_mum_trend_yoksa_sinyal_yok():
    df = yutan_yolu()
    # trend şartını bozan düz önceki seyir
    df.iloc[:-2, df.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] = 100.0
    assert (MumYutanDonus(trend_mum=6).sinyaller(df).yon == 0).all()
