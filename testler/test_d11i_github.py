"""D11-i (GitHub kaynaklı yeni aileler, i grubu): sözleşme/ızgara, lookahead (üç kesit), stop tarafı, sinyal üretimi, motor dumanı,
kol varyantları, gösterge doğrulukları."""
import inspect

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.dis import d11i_github as mod
from motor.strateji.dis._gosterge_d11i import aroon_asagi, aroon_yukari, ewo_yuzde, obv, vwap_bant, williams_r
from motor.strateji.temel import Strateji
from testler.test_daytrade import rastgele_mumlar

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
# rastgele yürüyüşte sinyal üretmesi için gevşek parametreler (kural aynı, eşikler gevşek)
GEVSEK = {
    "dis__bb-alt-bant-osilator": dict(gen_min=0.0, dusus_min=0.0, bant_pay=1.0),
    "dis__cci-aroon-dogus": dict(geri_pay=0.0, sk_alt=100.0, rsi_ust=100.0, cci_alt=-1000.0, cci_ust=1000.0, aroon_min=0.0,
                                 cmf_min=-1.0, mfi_min=0.0, rsi_alt=0.0),
    "dis__cok-osilator-ekstrem": dict(rsi3_ust=60.0, rsi14_ust=55.0),
    "dis__ema-hizali-olgun-yukselis": dict(),
    "dis__ewo-ema-ofset": dict(ofset=1.0, ewo_alt=-0.5, rsi_alt=60.0, cti_alt=-0.2),
    "dis__dortlu-stokastik-rotasyon": dict(alt=40.0, ust_rejim=60.0),
    "dis__cok-tf-stokastik-dip": dict(esik=40.0),
    "dis__nfi-short-cokus": dict(),
}
# kol / varyant -> ek parametreler (tüm kollar lookahead + sinyal testinden geçer)
KOLLAR = {
    "dis__aroon-stochrsi-ema-dip": [dict(kol="ema_ofset"), dict(kol="rsi_aroon"), dict(kol="wr_bb"), dict(ema_fark=0.0)],
    "dis__bb-alt-bant-osilator": [dict(kol="bb3"), dict(kol="ema_acik", acik=0.001, acik_onceki=0.0005), dict(kol="mfi_cmf")],
    "dis__cok-osilator-ekstrem": [dict(short_kol="tukenme"), dict(short_kol="dagitim", rsi14_ust=0.0)],
    "dis__dortlu-stokastik-rotasyon": [dict(kol="kirik"), dict(kol="diverjans"), dict(kol="ikisi")],
    "dis__ewo-ema-ofset": [dict(kol="ewo"), dict(kol="derin_dip", wr_alt=-70.0)],
    "dis__ha-bb40-cluc": [dict(kol="bant"), dict(kol="ema50")],
    "dis__nfi-short-cokus": [dict(kol="rollover"), dict(kol="cokus"), dict(kol="olu_kedi")],
    "dis__vwap-alt-bant-dip": [dict(kol="rsi14"), dict(kol="rsi_uzun")],
    "dis__smc-htf-supurme-choch": [dict(ust_tf="1h"), dict(ust_tf="4h", htf_n=3)],
}
SINYAL_BEKLENMEZ = {  # rastgele yürüyüşte eşikleri çok sıkı: yalnız çalışır + lookahead + yönsüz boş sinyal
    "dis__cci-aroon-dogus", "dis__ema-hizali-olgun-yukselis", "dis__ewo-ema-ofset"}


def veri(n=6000, seed=11):
    return rastgele_mumlar(n, seed=seed, freq="15min", baslangic="2018-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def varyantlar(sinif):
    return [olustur(sinif, **kw) for kw in KOLLAR.get(sinif.ad, [{}])]


def kisa_ek(sinif):
    p = sinif.varsayilan_parametreler
    return {"yonler": "ls"} if "yonler" in p and p["yonler"] == "long" else {}


# ---------------------------------------------------------------- kayıt / sözleşme
def test_ad_ve_sayi():
    assert len(SINIFLAR) == 14
    assert len(set(ADLAR)) == len(ADLAR)
    assert all(a.startswith("dis__") for a in ADLAR)
    assert all(c.stil == "scalp" for c in SINIFLAR)


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_ve_izgara_uclari(sinif):
    s = sinif()
    assert s.cikis_var_mi()
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    df = veri(n=2500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = olustur(sinif, **{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)


def test_bilinmeyen_parametre_ve_kol_hata_verir():
    with pytest.raises(ValueError):
        mod.UstTfMaRsiMomentum(yok=1)
    with pytest.raises(ValueError):
        mod.BbAltBantOsilator(kol="yok").sinyaller(veri(n=500))


# ---------------------------------------------------------------- lookahead / stop tarafı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri()
    for s in varyantlar(sinif) + [olustur(sinif, **kisa_ek(sinif))]:
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_gelecek_bari_degisince_gecmis_sinyal_ayni(sinif):
    df = veri()
    k = len(df) // 2
    oynak = df.copy()
    oynak.iloc[k + 1:, oynak.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 1.37
    oynak.iloc[k + 1:, oynak.columns.get_loc("hacim")] *= 3.0
    for s in varyantlar(sinif):
        pdt.assert_frame_equal(s.sinyaller(df).iloc[:k + 1], s.sinyaller(oynak).iloc[:k + 1])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri()
    toplam = 0
    for s in varyantlar(sinif):
        sig = s.sinyaller(df)
        giris = sig[sig.yon != 0]
        toplam += len(giris)
        assert giris.stop.notna().all()
        kap = df.kapanis
        l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
        h = giris.hedef.dropna()
        if len(h):
            yl = giris.loc[h.index]
            assert ((yl.yon == 1) & (h > kap[h.index]) | (yl.yon == -1) & (h < kap[h.index])).all()
    if sinif.ad not in SINYAL_BEKLENMEZ:
        assert toplam > 0, f"{sinif.ad}: sinyal yok"


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(n=2500)
    sonuc = backtest(df, olustur(sinif, **kisa_ek(sinif)), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


@pytest.mark.parametrize("ad", ["dis__ewo-ema-ofset", "dis__cci-aroon-dogus", "dis__ema-hizali-olgun-yukselis"])
def test_sikilastirilmis_ayar_gevsek_ayardan_az_sinyal_verir(ad):
    """Sıkı eşikli aileler rastgele yürüyüşte seyrek; gevşek ayar en az varsayılan kadar sinyal vermeli."""
    sinif = next(c for c in SINIFLAR if c.ad == ad)
    df = veri()
    sik = (sinif().sinyaller(df).yon != 0).sum()
    gevsek = (olustur(sinif).sinyaller(df).yon != 0).sum()
    assert gevsek >= sik


# ---------------------------------------------------------------- kural özel testleri
def test_uzun_yon_kisitlari():
    df = veri()
    for c in (mod.AroonStochRsiEmaDip, mod.BbAltBantOsilator, mod.CciAroonDogus, mod.CokTfStokastikDip,
              mod.EmaHizaliOlgunYukselis, mod.EwoEmaOfset, mod.HaBb40Cluc, mod.VwapAltBantDip):
        assert (olustur(c).sinyaller(df).yon >= 0).all(), c.ad
    assert (olustur(mod.NfiShortCokus).sinyaller(df).yon <= 0).all()


def test_smc_sweep_sonrasi_choch_ob_girisi():
    """Sentetik: aşağı süpürme (4h) -> LTF CHoCH -> OB'ye geri dokunma -> long; sinyal süpürmeden ÖNCE olamaz."""
    df = veri(n=9000, seed=3)
    s = mod.SmcHtfSupurmeChoch(ust_tf="1h", htf_n=3, bias_mum=96, ob_geri=20)
    sig = s.sinyaller(df)
    assert (sig.yon != 0).sum() > 0
    assert sig[sig.yon != 0].index.min() > df.index[3 * 4]   # htf_n x HTF mumu öncesi sinyal yok
    sol = mod.SmcHtfSupurmeChoch(ust_tf="1h", htf_n=3, yonler="long").sinyaller(df)
    assert (sol.yon >= 0).all()


def test_getiri_oynaklik_sentetik_sicrama():
    kap = np.full(600, 100.0)
    kap += np.random.default_rng(1).normal(0, 0.05, 600)
    kap[400:] += 3.0                                  # ani yukarı sıçrama
    df = pd.DataFrame({"acilis": np.r_[kap[0], kap[:-1]], "yuksek": kap + 0.1, "dusuk": kap - 0.1, "kapanis": kap,
                       "hacim": 1.0}, index=pd.date_range("2022-01-01", periods=600, freq="15min", tz="UTC"))
    sig = mod.GetiriOynaklikMomentum(vol_n=96).sinyaller(df)
    assert sig.yon.iloc[400] == 1 and (sig.yon.iloc[:400] == 1).sum() < 40


def test_cok_tf_stokastik_tum_tf_sart():
    df = veri(n=6000)
    gevsek = mod.CokTfStokastikDip(esik=45.0, tf_listesi="1h,4h").sinyaller(df)
    sadece_taban = mod.CokTfStokastikDip(esik=45.0, tf_listesi="").sinyaller(df)
    assert (gevsek.yon != 0).sum() <= (sadece_taban.yon != 0).sum()


# ---------------------------------------------------------------- göstergeler
def test_aroon_bilinen_deger():
    y = pd.Series([1, 2, 3, 4, 5, 4, 3, 2, 1, 0.5], dtype=float)
    a = aroon_yukari(y, 4)
    assert a.iloc[4] == 100.0                     # zirve şimdi
    assert a.iloc[6] == 50.0                      # zirve 2 mum önce (n=4)
    assert a.iloc[:4].isna().all()
    d = pd.Series([5, 4, 3, 2, 1, 2, 3, 4, 5, 6], dtype=float)
    assert aroon_asagi(d, 4).iloc[4] == 100.0
    assert aroon_asagi(d, 4).iloc[6] == 50.0


def test_gostergeler_nedensel_ve_sinirlar():
    r = np.random.default_rng(4)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 900))))
    h, l = x * (1 + r.uniform(0, 0.005, 900)), x * (1 - r.uniform(0, 0.005, 900))
    v = pd.Series(r.uniform(1, 3, 900))
    wr = williams_r(h, l, x, 14).dropna()
    assert wr.max() <= 0.0 and wr.min() >= -100.0
    pdt.assert_series_equal(williams_r(h, l, x, 14).iloc[:500], williams_r(h.iloc[:500], l.iloc[:500], x.iloc[:500], 14))
    pdt.assert_series_equal(aroon_yukari(h, 14).iloc[:500], aroon_yukari(h.iloc[:500], 14))
    pdt.assert_series_equal(obv(x, v).iloc[:500], obv(x.iloc[:500], v.iloc[:500]))
    pdt.assert_series_equal(ewo_yuzde(h, l, x).iloc[:500], ewo_yuzde(h.iloc[:500], l.iloc[:500], x.iloc[:500]))
    vb = vwap_bant(h, l, x, v, 20, 1.0)
    pdt.assert_frame_equal(vb.iloc[:500], vwap_bant(h.iloc[:500], l.iloc[:500], x.iloc[:500], v.iloc[:500], 20, 1.0))
    ok = vb.dropna()
    assert (ok["alt"] <= ok["orta"]).all() and (ok["orta"] <= ok["ust"]).all()
