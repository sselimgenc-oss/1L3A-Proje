"""D10-E (kuyruk yeni_aile 14'ten 14 strateji) testleri: sözleşme/ızgara, lookahead, stop tarafı, sinyal üretimi, motor dumanı,
kural özel testleri (UT Bot, saat dönüşü, NSM, Trend Magic, OB bölgesi, varyant hataları)."""
import importlib
import inspect
import sys
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
if not (_DIS / "d10e_kitap.py").exists():       # taşınmadan önce hazırlık klasöründen yükle
    import motor.strateji.dis as _pk
    _pk.__path__.append(str(_DIS / "_hazirlik_d10e"))
mod = importlib.import_module("motor.strateji.dis.d10e_kitap")
gos = importlib.import_module("motor.strateji.dis._gosterge_d10e")

SINIFLAR = sorted((c for _, c in inspect.getmembers(mod, inspect.isclass)
                   if c.__module__ == mod.__name__ and issubclass(c, Strateji) and c.ad), key=lambda c: c.ad)
ADLAR = [c.ad for c in SINIFLAR]
SEANSLI = {"dis__saat-donus-scalp"}
# rastgele veride sinyal üretmesi için gevşek parametreler (varsayılanlar korunur; yalnız test verisi)
GEVSEK = {
    "dis__carter-bb-disi-sinyal-mumu": dict(bb_k=1.0, trend_yavas=100),
    "dis__saat-donus-scalp": dict(yakin=0.5, min_hareket_atr=0.0),
    "dis__tv-cleantradequantum": dict(sniper_min=34.0, ut_key=0.5),
    "dis__sapan-geri-cekilme": dict(geri_min=1),
    "dis__rsi-ma-kesisim": dict(sma_yavas=50),
    "dis__utbot-kdj": dict(sma_n=50, ut_key=1.0, ut_atr=10),
    "dis__wavetrend-halftrend": dict(wt_seviye=20.0),
}


def veri(sinif, n=5000, seed=11):
    if sinif.ad in SEANSLI:
        return abd_mumlari(is_gunleri("2024-01-02", "2024-06-28"), dk=15, seed=seed, vol=0.004)
    return rastgele_mumlar(n, seed=seed, freq="5min", baslangic="2024-01-01")


def olustur(sinif, **ek):
    return sinif(**{**GEVSEK.get(sinif.ad, {}), **ek})


def test_ad_ve_sayi():
    assert len(SINIFLAR) == 14
    assert len(set(ADLAR)) == len(ADLAR) and all(a.startswith("dis__") for a in ADLAR)


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
    # gelecek barını değiştirmek geçmiş sinyali değiştirmez
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


# ---------------------------------------------------------------- varyantlar
@pytest.mark.parametrize("v", mod.CarterOnayliTrend.VARYANTLAR)
def test_carter_varyantlari_sinyal_uretir(v):
    df = rastgele_mumlar(8000, seed=2, freq="5min", baslangic="2024-01-01")
    sig = mod.CarterOnayliTrend(varyant=v).sinyaller(df)
    assert (sig.yon != 0).sum() > 0, v
    with pytest.raises(ValueError):
        mod.CarterOnayliTrend(varyant="yok").sinyaller(df)


@pytest.mark.parametrize("sinif,anahtar,degerler", [
    (mod.HmaOsilator, "osilator", ["rsi_bb", "stok", "mfi"]),
    (mod.MaKirilimMacdYeniPozitif, "varyant", ["lien", "ema20", "ema50_100"]),
    (mod.CarterCciMacd, "varyant", ["ema_cci0", "cci100_macd"])])
def test_diger_varyantlar_sinyal_uretir(sinif, anahtar, degerler):
    df = rastgele_mumlar(12000, seed=4, freq="5min", baslangic="2024-01-01")
    for v in degerler:
        ek = {"sma_yavas": 50} if False else {}
        sig = sinif(**{anahtar: v}).sinyaller(df)
        assert (sig.yon != 0).sum() > 0, (sinif.ad, v)
    with pytest.raises(ValueError):
        sinif(**{anahtar: "yok"}).sinyaller(df)


# ---------------------------------------------------------------- göstergeler / kural özel
def test_ut_bot_formul_ve_nedensellik():
    r = np.random.default_rng(3)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 800))))
    a = pd.Series(np.abs(r.normal(0.5, 0.1, 800)))
    ut = gos.ut_bot(x, a, 2.0)
    assert (ut["al"] & ut["sat"]).sum() == 0 and ut["al"].sum() > 3 and ut["sat"].sum() > 3
    # al olayında kaynak stopun üstünde, durum +1
    assert (ut.loc[ut["al"], "durum"] == 1).all() and (ut.loc[ut["sat"], "durum"] == -1).all()
    # stop long durumunda gevşemez (durum +1 art arda iken azalmaz)
    sey = ut["stop"].where((ut["durum"] == 1) & (ut["durum"].shift(1) == 1))
    assert (sey.diff().dropna() >= -1e-12).all()
    pdt.assert_frame_equal(gos.ut_bot(x.iloc[:500], a.iloc[:500], 2.0), ut.iloc[:500])


def test_trend_magic_yalniz_iz_surer():
    r = np.random.default_rng(5)
    x = pd.Series(100 * np.exp(np.cumsum(r.normal(0, 0.01, 800))))
    y, d = x * 1.004, x * 0.996
    tm = gos.trend_magic(y, d, x)
    ayni = tm["mavi"] & tm["mavi"].shift(1, fill_value=False)
    assert (tm["cizgi"].diff()[ayni].dropna() >= -1e-12).all()      # mavi iken çizgi düşmez
    pdt.assert_frame_equal(gos.trend_magic(y.iloc[:400], d.iloc[:400], x.iloc[:400]), tm.iloc[:400])


def test_nsm_yesil_don_egim_degisimi():
    x = pd.Series(np.r_[np.linspace(100, 90, 150), np.linspace(90, 110, 150), np.linspace(110, 95, 150)])
    n = gos.nsm_macd(x, norm_n=50)
    assert n["yesil_don"].sum() >= 1 and n["kirmizi_don"].sum() >= 1
    assert not (n["yesil_don"] & n["kirmizi_don"]).any()
    assert n["nsm"].dropna().abs().max() <= 100.0 + 1e-9


def test_ob_bolgesi_pivot_gecikmeli():
    taban = np.arange(12, dtype=float) * 0.01 + 20.0
    d = pd.Series(taban.copy())
    y = pd.Series(taban + 1.0)
    d.iloc[5] = 10.0                          # tek belirgin dip (pivot dibi)
    y.iloc[5] = 21.0                          # bölge [10, 21]
    a = pd.Series(np.full(12, 5.0))
    boga, _ = gos.ob_bolgeleri(y, d, a, 2, 3.0, 2)
    assert not boga.iloc[:7].any()          # pivot (indeks 5) ancak indeks 7'de onaylanır
    assert boga.iloc[7:10].all()             # onaydan sonra ömür boyunca (2 mum) dokunuş
    assert not boga.iloc[10:].any()          # ömür dolduktan sonra yok


def test_saat_donus_pencere_ve_gunde_bir():
    df = abd_mumlari(is_gunleri("2024-01-02", "2024-03-29"), dk=15, seed=7, vol=0.004)
    s = mod.SaatDonusScalp(saat=10, yakin=0.5, min_hareket_atr=0.0)
    sig = s.sinyaller(df)
    g_ = sig[sig.yon != 0]
    assert len(g_) > 0
    ny = g_.index.tz_convert("America/New_York")
    kapanis_dk = ny.hour * 60 + ny.minute + 15
    assert ((kapanis_dk > 600) & (kapanis_dk <= 630)).all()      # 10:00-10:30 penceresi (kapanış anı)
    assert not pd.Series(ny.date).duplicated().any() or pd.Series(list(zip(ny.date, g_.yon.to_numpy()))).duplicated().sum() == 0
    s15 = mod.SaatDonusScalp(saat=15, min_hareket_atr=0.0).sinyaller(df)
    g15 = s15[s15.yon != 0]
    assert len(g15) > 0
    ny = g15.index.tz_convert("America/New_York")
    kd = ny.hour * 60 + ny.minute + 15
    assert ((kd > 900) & (kd <= 930)).all()
    with pytest.raises(ValueError):
        mod.SaatDonusScalp(saat=11).sinyaller(df)


def test_anti_stokastik_zaman_cikisi_sutunu():
    df = rastgele_mumlar(3000, seed=9, freq="5min", baslangic="2024-01-01")
    sig = mod.AntiStokastik().sinyaller(df)
    z = sig.loc[sig.yon != 0, "zaman_cikisi_mum"]
    assert len(z) > 0 and (z == 3).all()


def test_ma_kirilim_kismi_cikis_ayari():
    s = mod.MaKirilimMacdYeniPozitif()
    assert s.cikis_ayarlari.kismi == ((1.0, 0.5),) and s.cikis_ayarlari.basabas_r_esigi == 1.0
