"""D11-H (GitHub kaynaklı daytrade aileleri) testleri: sözleşme/ızgara, lookahead, stop tarafı, sinyal üretimi, motor dumanı,
kural özel testleri."""
import importlib
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.temel import Strateji
from testler.test_daytrade import rastgele_mumlar
from testler.test_dis_d4 import abd_mumlari, is_gunleri

_DIS = Path(__file__).resolve().parents[1] / "motor" / "strateji" / "dis"
if not (_DIS / "d11h_github.py").exists():       # taşınmadan önce hazırlık klasöründen yükle
    import motor.strateji.dis as _pk
    _pk.__path__.append(str(_DIS / "_hazirlik_d11h"))
mod = importlib.import_module("motor.strateji.dis.d11h_github")
gos = importlib.import_module("motor.strateji.dis._gosterge_d11h")

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
SEANSLI = {"dis__parabolik-ilk-kirmizi-short", "dis__vwap-basarisizlik-short"}
# rastgele veride sinyal üretmesi için gevşek parametreler (varsayılanlar korunur; yalnız test verisi)
GEVSEK = {
    "dis__parabolik-ilk-kirmizi-short": dict(getiri_esik=-1.0, yuzde_sma=-1.0, atr_sma=-100.0, yesil_gun=1, hacim_k=0.0),
    "dis__vwap-basarisizlik-short": dict(min_ust=1, min_mum=3, lh_tolerans=0.0),
    "dis__osilator-esik-and": dict(stok_esik=45.0, rsi_esik=55.0, srsi_esik=45.0),
    "dis__hacim-govde-patlamasi": dict(hacim_k=1.5, govde_k=0.5, hacim_n=50),
    "dis__jake-ppo-vosc": dict(ppo_oran=0.1),
    "dis__ppo-tsi-uo-esik": dict(tsi_esik=5.0, hist_esik=0.0),
    "dis__spinning-top-rsi": dict(rsi_esik=45.0, min_aralik_atr=0.0),
    "dis__nw-zarf-rsi": dict(carpan=1.0, rsi_alt=45.0),
    "dis__macd-seviye-mtf": dict(yonler="ls", seviye_atr=0.2),
    "dis__x2-rsi-mtf": dict(ust_esik=60.0),
    "dis__klinger-skoru": dict(esik=0.1),
    "dis__macd-hist-esik-onay": dict(hist_esik=0.02, rsi_alt=50.0),
    "dis__cok-gosterge-teyit": dict(rsi_esik=50.0),
    "dis__gosterge-egim-esik": dict(yuzde_esik=0.2),
    "dis__ma-gunluk-pivot": dict(gun_sonu=0),
}
TF = {"dis__macd-seviye-mtf": "15min", "dis__ust-tf-ma-yon-kesisim": "15min"}


def veri(sinif, n=5000, seed=11):
    if sinif.ad in SEANSLI:
        return abd_mumlari(is_gunleri("2024-01-02", "2024-06-28"), dk=5, seed=seed, vol=0.003)
    return rastgele_mumlar(n, seed=seed, freq=TF.get(sinif.ad, "1h"), baslangic="2024-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def test_ad_ve_sayi():
    assert len(SINIFLAR) == 19
    assert len(set(ADLAR)) == len(ADLAR) and all(a.startswith("dis__") for a in ADLAR)
    assert all(c.stil == "daytrade" for c in SINIFLAR)


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
    s = olustur(sinif)
    tam = s.sinyaller(df)
    for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])
    df2 = df.copy()
    j = int(len(df) * 0.8)
    df2.iloc[j:, df2.columns.get_loc("kapanis")] *= 1.07
    df2.iloc[j:, df2.columns.get_loc("yuksek")] *= 1.07
    pdt.assert_frame_equal(s.sinyaller(df2).iloc[:j], tam.iloc[:j])


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    sig = olustur(sinif).sinyaller(df)
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
    df = veri(sinif, n=2000)
    sonuc = backtest(df, olustur(sinif), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- varyantlar / hata yolları
@pytest.mark.parametrize("sinif,anahtar,degerler", [
    (mod.GostergeEgimEsik, "gosterge", list(gos.GOSTERGELER)),
    (mod.MacdHistEsikOnay, "onay", ["rsi", "mfi", "cci_trend", "cci_ters"]),
    (mod.PpoTsiUoEsik, "varyant", ["tsi", "tsi_rsi", "uo"]),
    (mod.LinregMumTeyit, "teyit", ["macd", "utbot"]),
    (mod.FraktalOkGirisi, "stop_modu", ["pivot", "atr"]),
    (mod.MaGunlukPivot, "seviye_grubu", ["pivot", "destek_direnc", "hepsi"])])
def test_varyantlar_calisir_ve_hata_verir(sinif, anahtar, degerler):
    df = rastgele_mumlar(6000, seed=4, freq="1h", baslangic="2024-01-01")
    for v in degerler:
        ek = dict(GEVSEK.get(sinif.ad, {}))
        if sinif is mod.PpoTsiUoEsik:
            ek.update(rsi_alt=60.0, uo_alt=45.0)
        sig = sinif(**{**ek, anahtar: v}).sinyaller(df)
        assert sig.index.equals(df.index), (sinif.ad, v)
    with pytest.raises(ValueError):
        sinif(**{anahtar: "yok"}).sinyaller(df)


def test_gosterge_egim_sinyal_ureten_gostergeler():
    df = rastgele_mumlar(6000, seed=4, freq="1h", baslangic="2024-01-01")
    uretmeyen = [g_ for g_ in gos.GOSTERGELER
                 if (mod.GostergeEgimEsik(gosterge=g_, yuzde_esik=0.2).sinyaller(df).yon != 0).sum() == 0]
    assert len(uretmeyen) <= 2, uretmeyen


def test_gosterge_egim_bolge_ve_yonsuz():
    df = rastgele_mumlar(6000, seed=4, freq="1h", baslangic="2024-01-01")
    s = mod.GostergeEgimEsik(gosterge="ao", yuzde_esik=0.2, bolge="orta")
    sig = s.sinyaller(df)
    assert (sig.yon != 0).sum() > 0
    with pytest.raises(ValueError):
        mod.GostergeEgimEsik(bolge="x").sinyaller(df)


def test_fraktal_onay_gecikmeli():
    """Fraktal sinyali pivot mumunun k mum SONRASINDA gelir (nedensel)."""
    df = rastgele_mumlar(3000, seed=2, freq="1h", baslangic="2024-01-01")
    s = mod.FraktalOkGirisi(fraktal_k=2, stop_modu="atr")
    k = s.kosullar(df)
    i = np.flatnonzero(k["long"].to_numpy())[5]
    assert df.dusuk.iloc[i - 2] <= df.dusuk.iloc[i - 4:i + 1].min() + 1e-12      # pivot mumu 2 mum önce


def test_nw_zarf_nedensel_ve_zarf_sirasi():
    r = np.random.default_rng(3)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 800))))
    z = gos.nw_zarf(x, 8.0, 60, 3.0)
    pdt.assert_frame_equal(gos.nw_zarf(x.iloc[:500], 8.0, 60, 3.0), z.iloc[:500])
    v = z.dropna()
    assert (v["alt"] <= v["orta"]).all() and (v["orta"] <= v["ust"]).all()


def test_klinger_nedensel_ve_ust_tf():
    df = rastgele_mumlar(2500, seed=6, freq="1h", baslangic="2024-01-01")
    kvo = gos.klinger(df.yuksek, df.dusuk, df.kapanis, df.hacim)
    pdt.assert_series_equal(gos.klinger(df.yuksek[:1200], df.dusuk[:1200], df.kapanis[:1200], df.hacim[:1200]), kvo.iloc[:1200])
    s1 = mod.KlingerSkoru(ust_tf="", esik=0.1).sinyaller(df)
    s2 = mod.KlingerSkoru(ust_tf="4h", esik=0.1).sinyaller(df)
    assert (s1.yon != 0).sum() > 0 and (s2.yon != 0).sum() > 0


def test_tsi_ultimate_aralik():
    df = rastgele_mumlar(1500, seed=8, freq="1h", baslangic="2024-01-01")
    t = gos.tsi(df.kapanis).dropna()
    u = gos.ultimate(df.yuksek, df.dusuk, df.kapanis).dropna()
    assert t.abs().max() <= 100 + 1e-9 and (u >= -1e-9).all() and (u <= 100 + 1e-9).all()


def test_ma_gunluk_pivot_sadece_onceki_gun():
    """Seviyeler bir önceki tamamlanmış günden gelir: ilk günün ilk mumlarında sinyal yok."""
    df = rastgele_mumlar(1500, seed=2, freq="1h", baslangic="2024-01-01")
    sig = mod.MaGunlukPivot(gun_sonu=0, ma_n=5).sinyaller(df)
    assert (sig.yon.iloc[:24] == 0).all()
    with pytest.raises(ValueError):
        mod.MaGunlukPivot(ma_tipi="x").sinyaller(df)


def test_macd_seviye_mtf_ust_tf_kapanmis():
    df = rastgele_mumlar(3000, seed=5, freq="15min", baslangic="2024-01-01")
    s = mod.MacdSeviyeMtf(seviye_atr=0.2)
    sig = s.sinyaller(df)
    assert (sig.yon != 0).sum() > 0
    with pytest.raises(ValueError):
        mod.MacdSeviyeMtf(ust_tf="15min").sinyaller(df)


def _parabolik_veri():
    """Önceki günler üst üste güçlü yeşil; sonra bir gün: yeşil açılış, ilk kırmızı mum, dibinin altında kapanış."""
    gunler = is_gunleri("2024-01-02", "2024-02-29")
    df = abd_mumlari(gunler, dk=5, seed=3, vol=0.0005)
    seans = df.index.floor("D")
    gun_no = pd.Series(seans).factorize()[0]
    carpan = np.where(gun_no < 40, 1.0 + 0.02 * gun_no, 1.0 + 0.02 * 40)         # günlük sıçrayan trend
    ac = df.acilis.to_numpy() * carpan
    kap = df.kapanis.to_numpy() * carpan
    df = df.assign(acilis=ac, kapanis=kap, yuksek=np.maximum(ac, kap) * 1.001, dusuk=np.minimum(ac, kap) * 0.999)
    return df


def test_parabolik_filtre_ve_tetik_sirasi():
    df = rastgele_mumlar(10, freq="5min")                       # yalnız hata yolu için küçük veri
    with pytest.raises(ValueError):
        mod.ParabolikIlkKirmiziShort(tetik="yok").sinyaller(df)
    abd = abd_mumlari(is_gunleri("2024-01-02", "2024-03-29"), dk=5, seed=3, vol=0.003)
    s_siki = mod.ParabolikIlkKirmiziShort()
    assert (s_siki.sinyaller(abd).yon != 0).sum() == 0          # varsayılan süzgeç rastgele veride tetiklenmez (kaynak uyarısı)
    for tetik in ("ilk_kirmizi", "orl"):
        s = mod.ParabolikIlkKirmiziShort(tetik=tetik, **GEVSEK["dis__parabolik-ilk-kirmizi-short"])
        sig = s.sinyaller(abd)
        giris = sig[sig.yon != 0]
        assert len(giris) > 0 and (giris.yon == -1).all()
        gun = giris.index.tz_convert("UTC").floor("D")
        assert not pd.Series(gun).duplicated().any()           # günde en çok bir short


def test_vwap_basarisizlik_gunde_bir_ve_sira():
    df = abd_mumlari(is_gunleri("2024-01-02", "2024-06-28"), dk=5, seed=11, vol=0.003)
    sig = mod.VwapBasarisizlikShort(**GEVSEK["dis__vwap-basarisizlik-short"]).sinyaller(df)
    giris = sig[sig.yon != 0]
    assert len(giris) > 0 and (giris.yon == -1).all()
    assert not pd.Series(giris.index.floor("D")).duplicated().any()


def test_x2_rsi_yapiskan_yon_ve_hata():
    df = rastgele_mumlar(6000, seed=4, freq="1h", baslangic="2024-01-01")
    sig = mod.X2RsiMtf(ust_esik=60.0).sinyaller(df)
    assert (sig.yon == 1).sum() > 0 and (sig.yon == -1).sum() > 0


def test_zigzag_bacak_giris_pivot_onayindan_sonra():
    df = rastgele_mumlar(4000, seed=9, freq="1h", baslangic="2024-01-01")
    s = mod.ZigzagBacak()
    sig = s.sinyaller(df)
    assert (sig.yon != 0).sum() > 0
    k = s.kosullar(df)
    assert not (k["long"] & k["short"]).any()


def test_spinning_top_tanimi():
    o = pd.Series([100.0, 100.0]); y = pd.Series([102.0, 102.0]); d = pd.Series([98.0, 98.0]); k = pd.Series([100.2, 101.9])
    df = pd.DataFrame({"acilis": o, "yuksek": y, "dusuk": d, "kapanis": k, "hacim": 1.0})
    f = (df.kapanis - df.acilis).abs() <= 0.3 * (df.yuksek - df.dusuk)
    assert f.tolist() == [True, False]
