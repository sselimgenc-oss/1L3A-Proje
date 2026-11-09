"""D12-A (Brooks/Farley tam okuma + Halsey, 9 strateji): sözleşme/ızgara, lookahead (üç kesit), stop/hedef tarafı, sinyal üretimi, motor dumanı,
long/short simetrisi (ayna), tutucu limit yaklaşığı ve kural özel testleri (dikenli tel tanımı, ölçülü hareket seviyesi, boşluk türleri)."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.dis import d12a_kitap as mod
from motor.strateji.dis._gosterge_d12a import ayna, dikenli_tel_barlari, kirilim_olcu_durumu, trend_gunu_skoru
from motor.strateji.temel import Strateji

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
# seyrek sinyal veren kurallar için gevşek parametreler (sentetik veride sinyal çıksın diye)
GEVSEK = {
    "dis__brooks-dikenli-tel": dict(doji_oran=0.5, ort_oran=0.3, bekle=8, ma_filtre=False),
    "dis__brooks-doruk-tukenme": dict(buyuk_k=1.2, destek_n=10, trend_oran=0.5),
    "dis__farley-bosluk-turleri": dict(gap_atr=0.1),
}
MOD_GEVSEK = {
    ("dis__brooks-doruk-tukenme", "ardisik"): dict(ard_say=1),
    ("dis__farley-bosluk-turleri", "tukenme"): dict(run_atr=2.0, run_n=8),
}


def uretec(n, seed=3, freq="5min", baslangic="2022-01-01"):
    """Rejim değişimli (trend/yatay), ara sıra boşluklu sentetik mum verisi."""
    rng = np.random.default_rng(seed)
    kap, ac, yk, ds = (np.empty(n) for _ in range(4))
    fiyat, i = 100.0, 0
    while i < n:
        uz = int(rng.integers(60, 300))
        drift = rng.choice([-0.0025, 0.0, 0.0, 0.0025])
        vol = rng.uniform(0.003, 0.009)
        for _ in range(min(uz, n - i)):
            gap = rng.normal(0, 0.012) if rng.random() < 0.08 else rng.normal(0, 0.0008)
            o = fiyat * (1 + gap)
            c = o * (1 + rng.normal(drift, vol))
            ac[i], kap[i] = o, c
            yk[i] = max(o, c) * (1 + rng.uniform(0, 0.004))
            ds[i] = min(o, c) * (1 - rng.uniform(0, 0.004))
            fiyat, i = c, i + 1
    idx = pd.date_range(baslangic, periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yk, "dusuk": ds, "kapanis": kap, "hacim": rng.uniform(1, 3, n)}, index=idx)


def tf_of(sinif):
    return "1D" if sinif.stil == "swing" else "5min"


def veri(sinif, n=5000, seed=3):
    return uretec(n, seed=seed, freq=tf_of(sinif))


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def modlar(sinif):
    return sinif.parametre_izgarasi.get("mod", [None])


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) == 9
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
    df = veri(sinif, n=1500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


# ---------------------------------------------------------------- lookahead / stop tarafı
def _ornekler(sinif):
    return [olustur(sinif, mod=mo) if mo else olustur(sinif) for mo in modlar(sinif)]


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif, n=3500)
    for s in _ornekler(sinif):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_degisince_gecmis_sabit(sinif):
    """Gelecek barları bozmak geçmiş sinyalleri değiştirmez."""
    df = veri(sinif, n=3000)
    k = 2000
    bozuk = df.copy()
    bozuk.iloc[k:, bozuk.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 1.7
    for s in _ornekler(sinif):
        pdt.assert_frame_equal(s.sinyaller(df).iloc[:k], s.sinyaller(bozuk).iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    kap = df.kapanis
    for mo in modlar(sinif):
        ek = MOD_GEVSEK.get((sinif.ad, mo), {})
        sig = olustur(sinif, **({"mod": mo} if mo else {}), **ek).sinyaller(df)
        giris = sig[sig.yon != 0]
        assert len(giris) > 0, f"{sinif.ad}/{mo}: sinyal yok"
        assert giris.stop.notna().all()
        l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
        h = giris.hedef.dropna()
        if len(h):
            yl = giris.loc[h.index]
            assert ((yl.yon == 1) & (h > kap[h.index]) | (yl.yon == -1) & (h < kap[h.index])).all()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(sinif, n=1800)
    sonuc = backtest(df, olustur(sinif), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_ayna_simetrisi(sinif):
    """Fiyatı çevrilmiş (ayna) veride long/short yer değiştirir: long kodu short'un aynasıdır."""
    df = veri(sinif, n=3000)
    s = olustur(sinif)
    a = s.sinyaller(df)
    b = s.sinyaller(ayna(df))
    assert (a.yon.values == -b.yon.values).all()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_short_kapali(sinif):
    sig = olustur(sinif, short=False).sinyaller(veri(sinif, n=3000))
    assert (sig.yon >= 0).all()


def test_bilinmeyen_mod():
    df = veri(mod.BrooksLimitFade, n=500)
    for sinif in (mod.BrooksLimitFade, mod.BrooksLimitGeriCekilme, mod.BrooksOlculuHareketLimit, mod.BrooksDorukTukenme,
                  mod.FarleyBasarisizliginBasarisizligi, mod.FarleyBoslukTurleri, mod.HalseyOlculuHareket):
        with pytest.raises(ValueError):
            sinif(mod="yok").sinyaller(df)


# ---------------------------------------------------------------- tutucu limit yaklaşığı
def test_limit_tutucu_kapanis_seviyeyi_gecmis():
    """Limit girişlerde sinyal barının KAPANIŞI limit seviyesinin (önceki barın dibi) altında/eşit — dokunuşla dolum varsayılmaz."""
    df = veri(mod.BrooksLimitGeriCekilme)
    s = mod.BrooksLimitGeriCekilme(mod="onceki_cubuk", tik_atr=0.1, short=False)
    sig = s.sinyaller(df)
    idx = np.flatnonzero(sig.yon.values == 1)
    assert len(idx) > 0
    for i in idx:
        assert df.kapanis.iloc[i] <= df.dusuk.iloc[i - 1]


def test_olculu_hareket_seviye_kapanisla():
    """Ölçülü hareket seviyesi kapanışla ulaşılınca sinyal; dokunuş (fitil) tek başına yetmez."""
    n = 40
    k = np.full(n, 100.0)
    h = k + 1.0
    l = k - 1.0                       # 12 bar aralık: dip 99, zirve 101 -> H = 2
    k[20] = 98.0                      # aşağı kırılım (dip altı)
    h[20], l[20] = 99.5, 97.5
    k[21] = 98.5
    h[21], l[21] = 99.0, 96.0         # fitil seviyeye (99 - 2 = 97) değiyor ama kapanış 98.5 -> sinyal yok
    k[22] = 97.0                      # kapanış seviyeye ulaştı
    h[22], l[22] = 98.5, 96.5
    atr = np.full(n, 1.5)
    guclu = np.zeros(n, dtype=bool)
    sig, ll, hh, ns = kirilim_olcu_durumu(h, l, k, guclu, atr, n=12, rng_atr=5.0, min_atr=0.5, bekle=10, olcu=1.0)
    assert np.flatnonzero(sig).tolist() == [22]
    assert ll[22] == 99.0 and hh[22] == 2.0


# ---------------------------------------------------------------- kural özel testleri
def test_dikenli_tel_tanimi():
    idx = pd.date_range("2024-01-01", periods=6, freq="5min", tz="UTC")
    # üst üste binen, ortası doji bar -> tel
    m = pd.DataFrame({"acilis": [10.0, 10.2, 10.5, 10.4, 20.0, 30.0], "yuksek": [11.0, 11.0, 11.0, 11.0, 21.0, 31.0],
                      "dusuk": [9.5, 9.6, 10.0, 9.8, 19.0, 29.0], "kapanis": [10.6, 10.2, 10.5, 10.0, 20.5, 30.5],
                      "hacim": 1.0}, index=idx)
    tel = dikenli_tel_barlari(m, doji_oran=0.25, ort_oran=0.5)
    assert bool(tel.iloc[2]) and bool(tel.iloc[3])
    assert not bool(tel.iloc[5])   # bitişik olmayan barlar tel değil


def test_dikenli_tel_basarisiz_kirilim_sinyali():
    """Elle kurulmuş seri: tel bölgesi -> aşağı çıkış trend barı -> zirvesi geri alınır -> long sinyali (sonraki barda değil, o barın kapanışında)."""
    n = 60
    o = np.full(n, 100.0)
    c = np.full(n, 100.0)
    h = np.full(n, 101.0)
    l = np.full(n, 99.0)
    # tel: küçük gövdeli, örtüşen barlar (0-29), EMA'nın üstünde kalsın diye hafif yukarı
    for i in range(30):
        o[i], c[i] = 100.0 + 0.02 * i, 100.0 + 0.02 * i + 0.05
        h[i], l[i] = o[i] + 1.0, o[i] - 1.0
    # çıkış barı: güçlü ayı barı bölge dibinin altında
    o[30], c[30], h[30], l[30] = 100.8, 96.0, 101.0, 95.8
    # geri alma: kapanış çıkış barı zirvesini aşar
    o[31], c[31], h[31], l[31] = 96.5, 101.5, 101.8, 96.3
    for i in range(32, n):
        o[i], c[i], h[i], l[i] = 101.5, 101.6, 102.2, 101.0
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC")
    m = pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": 1.0}, index=idx)
    s = mod.BrooksDikenliTel(ma_filtre=False, doji_oran=0.5, short=False, atr_periyot=5)
    sig = s.sinyaller(m)
    assert sig.yon.iloc[31] == 1 and sig.stop.iloc[31] < c[31]


def _bosluk_serisi(pullback_kapanis):
    """Yükselen trend, j=80'de yukarı boşluk (120.2 - 125.6), sonra geri çekilme ve boğa barı."""
    n = 120
    k = np.linspace(100, 130, n)
    o = np.r_[k[0], k[:-1]]
    h = np.maximum(o, k) + 0.3
    l = np.minimum(o, k) - 0.3
    j = 80
    o[j:], k[j:], h[j:], l[j:] = o[j:] + 6, k[j:] + 6, h[j:] + 6, l[j:] + 6
    for i, (oo, kk) in zip((j + 1, j + 2, j + 3), ((126.5, 125.0), (125.0, pullback_kapanis), (pullback_kapanis - 0.3, pullback_kapanis + 1.0))):
        o[i], k[i] = oo, kk
        h[i], l[i] = max(oo, kk) + 0.2, min(oo, kk) - 0.2
    for i in range(j + 4, n):
        o[i], k[i], h[i], l[i] = k[i - 1], k[i - 1] + 0.1, k[i - 1] + 0.4, k[i - 1] - 0.2
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC")
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": k, "hacim": 1.0}, index=idx), j


def test_bosluk_devam_dolmadan_donus_long():
    m, j = _bosluk_serisi(pullback_kapanis=124.0)         # boşluk altı 120.2'nin çok üstünde: dolmadı
    sig = mod.FarleyBoslukTurleri(mod="devam", gap_atr=0.5, short=False, tol_atr=3.0, atr_periyot=5).sinyaller(m)
    assert sig.yon.iloc[j + 3] == 1
    assert sig.stop.iloc[j + 3] < 120.2                    # stop boşluk altının altında


def test_bosluk_devam_dolunca_giris_yok():
    m, j = _bosluk_serisi(pullback_kapanis=119.0)         # kapanış boşluk altına indi -> kurulum geçersiz
    sig = mod.FarleyBoslukTurleri(mod="devam", gap_atr=0.5, short=False, tol_atr=3.0, atr_periyot=5).sinyaller(m)
    assert (sig.yon.iloc[j:j + 15] == 0).all()


def test_trend_gunu_skoru_guclu_trend_yuksek():
    df = uretec(3000, seed=9)
    a = pd.Series(1.0, index=df.index)
    sk = trend_gunu_skoru(df, a)
    assert sk["skor"].between(0, 6).all()
    # sürekli yükselen mükemmel trendde skor tavana yakın
    n = 200
    k = pd.Series(np.linspace(100, 200, n)).to_numpy()
    o = np.r_[100.0, k[:-1]] - 0.05
    m = pd.DataFrame({"acilis": o, "yuksek": k + 0.05, "dusuk": o - 0.02, "kapanis": k, "hacim": 1.0},
                     index=pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"))
    sk2 = trend_gunu_skoru(m, pd.Series(1.0, index=m.index))
    assert sk2["skor"].iloc[-1] >= 5


def test_halsey_seviyeler():
    """Halsey: giriş seviyesi %50, stop %61.8 altı, hedef %123 (P1 + 1.23 x bacak) ve ayrık bacak başına tek giriş."""
    df = uretec(8000, seed=21, freq="15min")
    sig = mod.HalseyOlculuHareket(short=False).sinyaller(df)
    giris = sig[sig.yon == 1]
    assert len(giris) > 0
    assert (giris.hedef.dropna() > df.kapanis[giris.hedef.dropna().index]).all()


def test_tum_modlar_calisir():
    for sinif in SINIFLAR:
        df = veri(sinif, n=1500)
        for mo in modlar(sinif):
            sinif(**({"mod": mo} if mo else {})).sinyaller(df)
