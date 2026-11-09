"""D10-A (kuyruktaki yeni_aile satırları, a grubu, 22 strateji): sözleşme/ızgara, lookahead (üç kesit), stop/hedef tarafı, sinyal üretimi,
motor dumanı ve kural özel testleri (P&F üçlü tepe, ayın ilk günü, cuma-pazartesi, SMA200 bandı, MACD pivot gecikmesi, mükemmel sıralama)."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.dis import d10a_kitap as mod
from motor.strateji.dis._gosterge_d10a import connors_rsi, nokta_sekil_sinyalleri, yuzde_b
from motor.strateji.temel import Strateji
from testler.test_daytrade import rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
DORTSAAT = {"dis__ma20-rsi-cmf"}
# rastgele veride sinyal üretmesi için gevşek parametreler
GEVSEK = {
    "dis__ivanov-swing-kurulumlari": dict(tetik=0.004, kons_atr=12.0, hacim_alt=10.0, hacim_k=0.0, zirve_n=3),
    "dis__nokta-sekil": dict(kutu=0.01, tol=2, mod="hepsi"),
    "dis__ma20-rsi-cmf": dict(pencere=8),
    "dis__ema-kesisim-123-kurulumu": dict(ust_tf="", yakin_atr=3.0, govde_oran=0.1, kes_pencere=80),
    "dis__ochoa-genisleme-gunu": dict(adr_k=1.3, ust_yuzde=0.4, zirve_n=3),
    "dis__ma-mukemmel-siralama": dict(adx_min=0.0),
    "dis__lien-20-gun-sahte-kirilim": dict(pencere=10, geri_gun=5),
}


def tf_of(sinif):
    return "4h" if sinif.ad in DORTSAAT else "1D"


def veri(sinif, n=None, seed=11):
    n = n or (4500 if tf_of(sinif) == "4h" else 2500)
    return rastgele_mumlar(n, seed=seed, freq=tf_of(sinif), baslangic="2012-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def kisa_ek(sinif):
    p = sinif.varsayilan_parametreler
    return {"short": True} if "short" in p else {}


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) == 22
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
    for s in (olustur(sinif), olustur(sinif, **kisa_ek(sinif)), sinif(**kisa_ek(sinif))):
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


def test_mod_degerleri_calisir():
    """Izgarada olmayan veya uçta kalmayan modlar da hata vermeden çalışır."""
    df = veri(mod.OrtalamayaDonusGerilme)
    for mo in mod.OrtalamayaDonusGerilme.parametre_izgarasi["mod"]:
        mod.OrtalamayaDonusGerilme(mod=mo).sinyaller(df)
    for fl in ("bant", "iki_kapanis", "sma"):
        mod.Sma200BandTrend(filtre=fl).sinyaller(df)
    for k in ("12345678", "1234", "5678", "48"):
        mod.GranvilleMaKurallari(kurallar=k).sinyaller(df)
    mod.UcMumSwingNoktasi(agresif=True, kapanis_teyit=True).sinyaller(df)
    mod.HaStokastikGeriCekilme(ust_tf="1w").sinyaller(df)
    with pytest.raises(ValueError):
        mod.OrtalamayaDonusGerilme(mod="yok").sinyaller(df)
    with pytest.raises(ValueError):
        mod.NoktaSekil(mod="yok").sinyaller(df)
    with pytest.raises(ValueError):
        mod.OchoaGenislemeGunu(mod="yok").sinyaller(df)
    with pytest.raises(ValueError):
        mod.HaftaIciTakvim(mod="yok").sinyaller(df)


def test_ust_tf_lookahead_ema123_ha():
    df = rastgele_mumlar(2500, seed=3, freq="1D", baslangic="2012-01-01")
    for s in (mod.EmaKesisim123Kurulumu(yakin_atr=3.0, govde_oran=0.1, kes_pencere=80), mod.HaStokastikGeriCekilme(ust_tf="1w")):
        tam = s.sinyaller(df)
        for k in (900, 1500, 2100):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


# ---------------------------------------------------------------- kural özel testleri
def test_pf_ucle_tepe_kirilimi():
    kutu = 0.1
    # X 0-8, O ->3, X ->8, O ->5 (yükselen dip), X ->8 (üçlü tepe), 9: kırılım
    yol = [0, 1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 5, 4, 3, 4, 5, 6, 7, 8, 7, 6, 5, 6, 7, 8, 9]
    fiyat = pd.Series(100.0 * (1 + kutu) ** np.array(yol, dtype=float) * 1.002)
    r = nokta_sekil_sinyalleri(fiyat, fiyat, kutu, ters=3, tol=0, ucle=True, sarsinti=False)
    assert r["long"].sum() == 1 and bool(r["long"].iloc[-1])
    assert r["stop_l"].iloc[-1] < fiyat.iloc[-1]
    assert not r["short"].any()


def test_pf_nedensel_ve_yalniz_yukselis_sinyal_vermez():
    kutu = 0.05
    fiyat = pd.Series(100.0 * np.exp(0.01 * np.arange(300)))
    r = nokta_sekil_sinyalleri(fiyat, fiyat, kutu)
    assert not r["long"].any() and not r["short"].any() and not r["cikis_l"].any()
    rng = np.random.default_rng(2)
    x = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.012, 1200))))
    tam = nokta_sekil_sinyalleri(x * 1.002, x * 0.998, 0.01, tol=2)
    pdt.assert_frame_equal(nokta_sekil_sinyalleri(x.iloc[:700] * 1.002, x.iloc[:700] * 0.998, 0.01, tol=2), tam.iloc[:700])


def test_ayin_ilk_gunu_yalniz_ay_basi():
    df = rastgele_mumlar(2500, seed=8, freq="1D", baslangic="2012-01-01")
    s = mod.AyinIlkGunuDeseni(esik=0.0)
    sig = s.sinyaller(df)
    giris = sig[sig.yon != 0].index
    assert len(giris) > 20
    ay = pd.Series(df.index.month, index=df.index)
    assert ay[giris].ne(ay.shift(1)[giris]).all()
    # yön kuralı: düşüşten sonra + kapanış < açılış => long
    for t in giris:
        i = df.index.get_loc(t)
        chg = df.kapanis.iloc[i - 1] - df.kapanis.iloc[i - 2]
        if sig.yon[t] == 1:
            assert chg < 0 and df.kapanis.iloc[i] < df.acilis.iloc[i]
        else:
            assert chg > 0 and df.kapanis.iloc[i] > df.acilis.iloc[i]


def test_cuma_pazartesi_yalniz_cuma():
    df = rastgele_mumlar(1500, seed=4, freq="1D", baslangic="2012-01-02")
    sig = mod.HaftaIciTakvim(mod="cuma_pzt", short=True).sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 50 and (giris.index.dayofweek == 4).all()
    up = df.kapanis[giris.index] > df.acilis[giris.index]
    assert ((giris.yon == 1) == up).all()
    assert (sig["zaman_cikisi_mum"].dropna() == 1.0).all()


def test_sma200_bant_kosulu():
    df = rastgele_mumlar(2500, seed=6, freq="1D", baslangic="2012-01-01")
    sig = mod.Sma200BandTrend(k=0.5).sinyaller(df)
    k = df.kapanis
    sma = k.rolling(200).mean()
    sd = k.rolling(200).std(ddof=0)
    giris = sig[sig.yon == 1].index
    assert len(giris) > 20 and (k[giris] > (sma + 0.5 * sd)[giris]).all()
    assert (sig.yon[:199] == 0).all()
    assert set(sig["zaman_cikisi_mum"].dropna().unique()) == {20.0}


def test_macd_pivot_gecikmeli_onay():
    df = rastgele_mumlar(2500, seed=9, freq="1D", baslangic="2012-01-01")
    sig = mod.MacdHistogramPivot().sinyaller(df)
    from motor.strateji import gostergeler as g
    hist = g.macd(df.kapanis)["histogram"].to_numpy()
    for t in np.flatnonzero(sig.yon.to_numpy() == 1):
        mer = hist[t - 2]
        assert all(mer < hist[t - 4 + j] for j in range(5) if j != 2)
        assert hist[t - 4] < 0 and hist[t] < 0
    a = g.atr(df.yuksek, df.dusuk, df.kapanis, 10)
    t0 = sig.index[sig.yon == 1][0]
    assert sig.stop[t0] == pytest.approx(df.kapanis[t0] - a[t0]) and sig.hedef[t0] == pytest.approx(df.kapanis[t0] + 3 * a[t0])


def test_mukemmel_siralama_bekleme():
    rng = np.random.default_rng(1)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.006, 700)))
    idx = pd.date_range("2012-01-01", periods=700, freq="1D", tz="UTC", name="zaman")
    df = pd.DataFrame({"acilis": np.r_[kap[0], kap[:-1]], "yuksek": kap * 1.003, "dusuk": kap * 0.997, "kapanis": kap,
                       "hacim": 1.0}, index=idx)
    from motor.strateji import gostergeler as g
    s = [g.sma(df.kapanis, n) for n in (10, 20, 50, 100, 200)]
    sira = (df.kapanis > s[0]) & (s[0] > s[1]) & (s[1] > s[2]) & (s[2] > s[3]) & (s[3] > s[4])
    ilk = sira.idxmax()
    assert sira.any()
    sig = mod.MaMukemmelSiralama(adx_min=0.0, bekle=5).sinyaller(df)
    giris = sig.index[sig.yon == 1]
    assert len(giris) > 0
    assert df.index.get_loc(giris[0]) >= df.index.get_loc(ilk) + 5


def test_gostergeler_sinirlar():
    r = np.random.default_rng(4)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 900))))
    c = connors_rsi(x).dropna()
    assert len(c) > 700 and c.min() >= 0 and c.max() <= 100
    b = yuzde_b(x, 20, 2.0).dropna()
    assert len(b) > 800
    pdt.assert_series_equal(connors_rsi(x.iloc[:500]), connors_rsi(x).iloc[:500])
