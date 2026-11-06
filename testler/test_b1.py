"""B1 aileleri: lookahead, arayüz, stop/hedef tarafı, gün sonu, türetme eşdeğerliği, sentetik senaryolar, kart ayarları."""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import gun_sonu_uygula, seans_son_mumu
from motor.strateji.gostergeler_b1 import ardisik_sayac, donchian_kanal, gunluk_sma, seans_gap
from motor.strateji.scalp.aralik_ticareti import AralikTicareti as ScAralik
from motor.strateji.scalp.ardisik_bar_tukenme import ArdisikBarTukenme as ScArdisik
from motor.strateji.scalp.bant_donus import BantDonus as ScBant
from motor.strateji.scalp.bb_sikisma_kirilim import BbSikismaKirilim as ScBb
from motor.strateji.scalp.cift_dip_tepe import CiftDipTepe as ScCift
from motor.strateji.scalp.fib_geri_cekilme import FibGeriCekilme as ScFib
from motor.strateji.scalp.kirilim_geri_test import KirilimGeriTest as ScKgt
from motor.strateji.scalp.macd_sinyal import MacdSinyal as ScMacd
from motor.strateji.scalp.stokastik_donus import StokastikDonus as ScStok
from motor.strateji.scalp.supertrend_psar import SupertrendPsar as ScSuper
from motor.strateji.daytrade.aralik_ticareti import AralikTicareti as DtAralik
from motor.strateji.daytrade.ardisik_bar_tukenme import ArdisikBarTukenme as DtArdisik
from motor.strateji.daytrade.bant_donus import BantDonus as DtBant
from motor.strateji.daytrade.donchian_kirilim import DonchianKirilim as DtDonchian
from motor.strateji.daytrade.fib_geri_cekilme import FibGeriCekilme as DtFib
from motor.strateji.daytrade.gap_devam import GapDevam as DtGapDevam
from motor.strateji.daytrade.gap_doldurma import GapDoldurma as DtGapDoldurma
from motor.strateji.daytrade.ma_geri_cekilme import MaGeriCekilme as DtMa
from motor.strateji.daytrade.stokastik_donus import StokastikDonus as DtStok
from motor.strateji.daytrade.vwap_trend import VwapTrend as DtVwap
from motor.strateji.swing.aralik_ticareti import AralikTicareti as SwAralik
from motor.strateji.swing.ardisik_bar_tukenme import ArdisikBarTukenme as SwArdisik
from motor.strateji.swing.bant_donus import BantDonus as SwBant
from motor.strateji.swing.bb_sikisma_kirilim import BbSikismaKirilim as SwBb
from motor.strateji.swing.cift_dip_tepe import CiftDipTepe as SwCift
from motor.strateji.swing.donchian_kirilim import DonchianKirilim as SwDonchian
from motor.strateji.swing.fib_geri_cekilme import FibGeriCekilme as SwFib
from motor.strateji.swing.gap_devam import GapDevam as SwGapDevam
from motor.strateji.swing.gap_doldurma import GapDoldurma as SwGapDoldurma
from motor.strateji.swing.kirilim_geri_test import KirilimGeriTest as SwKgt
from motor.strateji.swing.ma_geri_cekilme import MaGeriCekilme as SwMa
from motor.strateji.swing.macd_sinyal import MacdSinyal as SwMacd
from motor.strateji.swing.pivot_seviye import PivotSeviye as SwPivot
from motor.strateji.swing.stokastik_donus import StokastikDonus as SwStok
from motor.strateji.swing.supertrend_psar import SupertrendPsar as SwSuper

KART_DIZINI = Path(__file__).resolve().parent.parent / "stratejiler" / "kart_ayarlari"


def rastgele(n, seed=2, freq="1h"):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range("2022-01-01", periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def kapanistan(kap, genlik=0.5, hacim=1.0, freq="1h", baslangic="2022-01-01"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range(baslangic, periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hacim}, index=idx)


FREQ = {"scalp": "15min", "daytrade": "1h", "swing": "4h"}

# (strateji, veri freq'i, "az sinyal" olduğundan gevşetilmiş yapısal-test parametreleri)
KAYITLAR = [
    DtAralik(), ScAralik(), DtBant(), ScBant(), ScBb(hacim_k=0.0), SwBb(), ScCift(), DtFib(), ScFib(),
    ScKgt(), SwKgt(), DtMa(), ScMacd(), ScMacd(mod="hist_donus"), ScMacd(mod="sifir"), SwPivot(),
    SwPivot(mod="kirilim", pivot_periyodu="gun"), DtStok(), SwStok(), SwSuper(), SwSuper(gosterge="psar"),
    SwSuper(gosterge="ikisi", rsi_esik=55.0),
    DtDonchian(), SwDonchian(), SwDonchian(stop_modu="kanal", cikis_n=5), SwDonchian(stop_modu="bar", kirilim_pct=0.5, hacim_k=1.0, trend_ma=50),
    DtVwap(), DtVwap(tampon_atr=0.25, hedef_r=1.5),
    DtGapDevam(min_gap_atr=0.7),
    SwGapDevam(min_gap_atr=0.5), SwGapDevam(min_gap_atr=0.5, stop_modu="gap", gap_korunur=False),
    DtGapDoldurma(min_gap_atr=0.7, sma_gun=0), DtGapDoldurma(min_gap_atr=0.7, sma_gun=20),
    SwGapDoldurma(), SwGapDoldurma(referans="aralik", min_gap_atr=0.5, kapanis_yuzde=0.0),
    DtArdisik(), DtArdisik(desen="yavaslama"), DtArdisik(desen="doruk", seri_n=4), ScArdisik(), SwArdisik(),
    SwArdisik(tetik="seri_sonu", zincir=True, zaman_cikisi_mum=5, trend_ma=50),
]
HEPSI = [DtAralik(), ScAralik(), DtBant(), ScBant(), ScBb(), SwBb(), ScCift(), DtFib(), ScFib(), ScKgt(), SwKgt(), DtMa(),
         ScMacd(), SwPivot(), DtStok(), SwStok(), SwSuper(), DtDonchian(), SwDonchian(), DtVwap(), DtGapDevam(),
         SwGapDevam(), DtGapDoldurma(), SwGapDoldurma(), DtArdisik(), ScArdisik(), SwArdisik()]
_VERI = {}


def veri(stil, n=6000, seed=2):
    anahtar = (stil, n, seed)
    if anahtar not in _VERI:
        _VERI[anahtar] = rastgele(n, seed, FREQ[stil])
    return _VERI[anahtar]


def _id(s):
    return f"{s.ad.split('__')[1]}-{abs(hash(str(sorted(s.parametreler.items())))) % 997}"


# ------------------------------------------------------------------ arayüz / kapsam

def test_yirmiyedi_aile_ve_adlandirma():
    adlar = {s.ad for s in HEPSI}
    assert len(HEPSI) == 27 and len(adlar) == 27
    for s in HEPSI:
        stil, aile = s.ad.split("__")
        assert s.stil == stil and stil in FREQ and aile
        assert s.cikis_var_mi() is True


def test_parametre_izgarasi_sinirli():
    for s in HEPSI:
        assert 1 <= np.prod([len(v) for v in s.parametre_izgarasi.values()]) <= 27, s.ad
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler), s.ad
        for komb in itertools.islice(itertools.product(*s.parametre_izgarasi.values()), 4):
            s.yeni(**dict(zip(s.parametre_izgarasi, komb)))
        with pytest.raises(ValueError):
            type(s)(bilinmeyen_parametre=1)


@pytest.mark.parametrize("s", KAYITLAR, ids=_id)
def test_lookahead_yok(s):
    df = veri(s.stil)
    tam = s.sinyaller(df)
    for n in (350, 901, 1777, 2501, 3333):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", KAYITLAR, ids=_id)
def test_cerceve_stop_hedef_tarafi_ve_cikis(s):
    df = veri(s.stil)
    sig = s.sinyaller(df)
    assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    assert sig["yon"].dtype == "int64" and sig["cikis"].dtype == bool
    gir = sig[sig.yon != 0]
    assert len(gir) > 0, f"{s.ad} sinyal üretmedi"
    assert gir.stop.notna().all()
    kap = df.kapanis[gir.index]
    l, sh = gir.yon == 1, gir.yon == -1
    assert (gir.stop[l] < kap[l]).all() and (gir.stop[sh] > kap[sh]).all()
    h = gir.hedef.dropna()
    yh = gir.yon[h.index]
    assert (h[yh == 1] > kap[h.index][yh == 1]).all() and (h[yh == -1] < kap[h.index][yh == -1]).all()
    yonlu = any(c in sig.columns and sig[c].any() for c in ("cikis_long", "cikis_short"))
    assert sig.cikis.any() or yonlu or gir.hedef.notna().any() or "zaman_cikisi_mum" in sig.columns
    assert (sig.loc[sig.yon == 0, "stop"].isna()).all()


@pytest.mark.parametrize("s", [s for s in KAYITLAR if not isinstance(s, (ScCift,))], ids=_id)
def test_short_kapatilabilir(s):
    kapali = s.yeni(short=False)
    sig = kapali.sinyaller(veri(s.stil, 3000))
    assert (sig.yon >= 0).all()


@pytest.mark.parametrize("s", [s for s in KAYITLAR if s.stil == "daytrade"], ids=_id)
def test_gun_sonu_zorunlu_cikis(s):
    df = veri("daytrade")
    sig = s.sinyaller(df)
    son = seans_son_mumu(df.index, s.parametreler["seans_saat"])
    assert son.sum() > 100
    assert sig.cikis[son].all()
    assert (sig.yon[son] == 0).all() and sig.stop[son].isna().all()
    # farklı seans saatinde de geçerli
    s2 = s.yeni(seans_saat=13.5)
    sig2 = s2.sinyaller(df)
    son2 = seans_son_mumu(df.index, 13.5)
    assert sig2.cikis[son2].all() and (sig2.yon[son2] == 0).all()


# ------------------------------------------------------------------ türetme eşdeğerliği

def _ayni(cls_a, cls_b, df, **kw):
    """İki sınıfı AYNI (tam) parametre kümesiyle çalıştırıp çıktıların eşit olduğunu doğrular."""
    p = cls_a(**kw).parametreler
    pdt.assert_frame_equal(cls_a(**p).sinyaller(df), cls_b(**{k: v for k, v in p.items()}).sinyaller(df))


def test_turetilen_siniflar_ebeveynle_ayni_mekanik():
    dg = veri("swing", 3000)
    _ayni(SwSuper, ScSuper, dg, carpan=2.0, atr_periyot=7, rsi_esik=55.0, gosterge="ikisi")
    _ayni(SwStok, ScStok, dg, trend_ema=50, k_periyot=8, hedef_r=1.5)
    d15 = veri("scalp", 3000)
    _ayni(ScAralik, SwAralik, d15, pencere=30, bant=0.2, adx_esik=0.0)
    _ayni(ScBant, SwBant, d15, bb_periyot=30, rsi_esik=0.0, adx_esik=0.0)
    _ayni(ScFib, SwFib, d15, pivot_k=3, giris_alt=0.382, trend_ema=0)
    _ayni(ScKgt, SwKgt, d15, uzunluk=20, pencere=8)
    _ayni(ScBb, SwBb, d15, sikisma_pencere=100, hacim_k=0.0)
    _ayni(ScCift, SwCift, d15, tolerans_yuzde=1.0)
    _ayni(ScMacd, SwMacd, d15, mod="sinyal", atr_k=1.5)
    _ayni(ScArdisik, SwArdisik, d15, seri_n=4)


def test_day_trade_siniflari_swing_cekirdek_arti_gun_sonu():
    d1 = veri("daytrade", 3000)
    kw = dict(pencere=24, bant=0.2, adx_esik=0.0)
    pdt.assert_frame_equal(DtAralik(**kw).sinyaller(d1), gun_sonu_uygula(SwAralik(**kw).sinyaller(d1), 0.0))
    kw = dict(ma_periyot=20, trend_ma=100, geri_n=4, hedef_r=2.0)
    pdt.assert_frame_equal(DtMa(**kw).sinyaller(d1), gun_sonu_uygula(SwMa(**kw).sinyaller(d1), 0.0))
    kw = dict(pivot_k=4, giris_alt=0.382, trend_ema=0)
    pdt.assert_frame_equal(DtFib(**kw).sinyaller(d1), gun_sonu_uygula(SwFib(**kw).sinyaller(d1), 0.0))
    kw = dict(bb_periyot=20, adx_esik=0.0)
    pdt.assert_frame_equal(DtBant(**kw).sinyaller(d1), gun_sonu_uygula(SwBant(**kw).sinyaller(d1), 0.0))


# ------------------------------------------------------------------ yardımcı göstergeler

def test_donchian_kanal_mevcut_mumu_icermez():
    df = kapanistan([100, 101, 102, 150, 103])
    k = donchian_kanal(df.yuksek, df.dusuk, 3)
    assert k.ust.iloc[3] == pytest.approx(df.yuksek.iloc[:3].max())     # 150'lik mum t=3'te görülmez
    assert k.ust.iloc[4] == pytest.approx(df.yuksek.iloc[1:4].max())
    assert np.isnan(k.ust.iloc[2])


def test_ardisik_sayac():
    s = pd.Series([True, True, False, True, True, True, False])
    assert ardisik_sayac(s).tolist() == [1, 2, 0, 1, 2, 3, 0]


def test_seans_gap_degerleri_ve_nedensellik():
    # gün 1: 24 mum kapanış 100; gün 2: ilk mum açılış 102 (boşluk), kapanış 103
    kap = np.r_[np.full(24, 100.0), 103.0, np.full(23, 104.0)]
    df = kapanistan(kap)
    df.iloc[24, df.columns.get_loc("acilis")] = 102.0
    atr = g.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    ac = seans_gap(df, atr, 0.0, "acilis")
    il = seans_gap(df, atr, 0.0, "ilk_bar")
    assert ac.gap.iloc[:24].isna().all()
    assert np.allclose(ac.gap.iloc[24:], 2.0) and np.allclose(il.gap.iloc[24:], 3.0)
    assert (ac.onc_kap.iloc[24:] == 100.0).all() and ac.mum_no.iloc[24] == 1 and ac.mum_no.iloc[47] == 24
    assert il.dusuk_kor.iloc[24] == np.inf and il.dusuk_kor.iloc[25] == pytest.approx(df.dusuk.iloc[25])
    pdt.assert_frame_equal(seans_gap(df.iloc[:30], atr.iloc[:30], 0.0, "ilk_bar"), il.iloc[:30])


def test_gunluk_sma_ertesi_gunden_itibaren():
    df = rastgele(24 * 80, 5)
    s = gunluk_sma(df, 10)
    gunluk_kap = df.kapanis.groupby(df.index.floor("D")).last()
    beklenen = gunluk_kap.rolling(10).mean()
    # 11. günün ilk mumunda, ilk 10 günün SMA'sı kullanılabilir
    t = gunluk_kap.index[10]
    assert s.loc[t] == pytest.approx(beklenen.iloc[9])
    assert s.loc[:gunluk_kap.index[9] + pd.Timedelta(hours=23)].isna().all()


# ------------------------------------------------------------------ sentetik senaryolar

def test_donchian_kirilim_giris_ve_kanal_cikisi():
    kap = np.r_[np.full(40, 100.0), np.linspace(100, 130, 30), np.linspace(130, 100, 40)]
    df = kapanistan(kap, genlik=0.3, freq="1D")
    sig = SwDonchian(giris_n=20, cikis_n=10, short=False).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(longlar) == 1 and 40 <= longlar[0] <= 43
    i = longlar[0]
    assert sig.stop.iloc[i] == pytest.approx(df.kapanis.iloc[i] - 2.0 * g.atr(df.yuksek, df.dusuk, df.kapanis, 14).iloc[i])
    cks = np.flatnonzero(sig.cikis_long.to_numpy())
    cks = cks[cks > i]
    assert len(cks) >= 1 and cks[0] > 70            # çıkış yalnız düşüş fazında (yükselişte değil)
    # kanal modu: stop = önceki cikis_n mumun dibi
    sk = SwDonchian(giris_n=20, cikis_n=10, stop_modu="kanal", short=False).sinyaller(df)
    assert sk.stop.iloc[i] == pytest.approx(df.dusuk.iloc[i - 10:i].min())
    # short: düşüş
    kap2 = np.r_[np.full(40, 100.0), np.linspace(100, 70, 30)]
    sh = SwDonchian(giris_n=20).sinyaller(kapanistan(kap2, genlik=0.3, freq="1D"))
    assert (sh.yon == -1).sum() == 1 and (sh.stop[sh.yon == -1] > 99).all()


def test_donchian_cikis_yonlu_long_yukselisinde_cikis_yok():
    kap = np.r_[np.full(40, 100.0), np.linspace(100, 140, 60)]
    sig = SwDonchian(giris_n=20, cikis_n=5, short=False).sinyaller(kapanistan(kap, genlik=0.3, freq="1D"))
    assert sig.cikis_long.sum() == 0     # sürekli yeni zirve: karşı kanal yüksekliği long'u kapatmaz


def test_ardisik_bar_tukenme_uc_dusus_sonra_kirilim():
    kap = np.r_[np.full(20, 100.0), [99.0, 98.0, 97.0], [99.5], np.full(5, 100.0)]
    df = kapanistan(kap, genlik=0.4, freq="1D")
    sig = SwArdisik(short=False).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert list(longlar) == [23]      # 99.5 > önceki mumun zirvesi (98.4)
    assert sig.stop.iloc[23] == pytest.approx(df.dusuk.iloc[20:24].min() - 0.25 * g.atr(df.yuksek, df.dusuk, df.kapanis, 14).iloc[23])
    # seri_sonu: seri tamamlanınca (3. düşüş mumunda) giriş
    s2 = SwArdisik(short=False, tetik="seri_sonu").sinyaller(df)
    assert list(np.flatnonzero(s2.yon.to_numpy() == 1)) == [22]
    # zincir: dip ve zirveler de düşmeli -> aynı seri geçerli; 2 mum yetmez
    assert (SwArdisik(short=False, seri_n=4, tetik="seri_sonu").sinyaller(df).yon == 0).all()
    # yükseliş serisi -> short
    kap_s = np.r_[np.full(20, 100.0), [101.0, 102.0, 103.0], [100.5], np.full(5, 100.0)]
    ss = SwArdisik().sinyaller(kapanistan(kap_s, genlik=0.4, freq="1D"))
    assert list(np.flatnonzero(ss.yon.to_numpy() == -1)) == [23] and ss.stop.iloc[23] > 103.4


def test_woods_yavaslama_ve_doruk_desen_ayrimi():
    # dipler: 100 -> 98 (adım 2) -> 97 (adım 1): yavaşlama; sonra yükseliş kırılımı
    kap_y = np.r_[np.full(30, 105.0), [100.0, 98.0, 97.0], [100.0], np.full(3, 100.0)]
    # dipler: 100 -> 99 (adım 1) -> 96.5 (adım 2.5): doruk
    kap_d = np.r_[np.full(30, 105.0), [100.0, 99.0, 96.0], [99.5], np.full(3, 99.5)]
    dfy, dfd = kapanistan(kap_y, genlik=0.0, freq="1h"), kapanistan(kap_d, genlik=0.0, freq="1h")
    ya = DtArdisik(desen="yavaslama", short=False)
    do = DtArdisik(desen="doruk", short=False)
    assert (ya.sinyaller(dfy).yon == 1).sum() == 1 and (do.sinyaller(dfy).yon == 1).sum() == 0
    assert (do.sinyaller(dfd).yon == 1).sum() == 1 and (ya.sinyaller(dfd).yon == 1).sum() == 0


def test_vwap_trend_kesisim_ve_gun_sonu():
    # gün 1: fiyat düşer sonra VWAP'ı yukarı keser; gün 2 aynı
    gun = np.r_[np.linspace(100, 94, 10), np.linspace(94, 108, 14)]
    df = kapanistan(np.r_[gun, gun], genlik=0.3, hacim=1.0)
    sig = DtVwap(min_mum=3, short=False).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(longlar) >= 2
    assert all(i < 23 or 24 <= i < 47 for i in longlar)
    assert sig.yon.iloc[23] == 0 and sig.cikis.iloc[23] and sig.cikis.iloc[47]
    i = longlar[0]
    v = g.vwap_seans(df.yuksek, df.dusuk, df.kapanis, df.hacim, df.index.floor("D").to_numpy())["vwap"]
    atr = g.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    assert sig.stop.iloc[i] == pytest.approx(v.iloc[i] - 0.5 * atr.iloc[i])
    assert df.kapanis.iloc[i] > v.iloc[i] and df.kapanis.iloc[i - 1] <= v.iloc[i - 1]


def _gun1_duz(n=24, fiyat=100.0):
    return np.full(n, fiyat)


def test_gap_devam_gunici_kirilim_ve_stop():
    kap = np.r_[_gun1_duz(), [104.0, 103.6, 104.2, 105.8], np.full(20, 105.0)]
    df = kapanistan(kap, genlik=0.5)
    s = DtGapDevam(min_gap_atr=1.5, konsol_n=1, short=False)
    sig = s.sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert list(longlar) == [27]               # kutu = ilk mum (zirve 104.5); 105.8 kırılım
    assert sig.stop.iloc[27] < 100.0 and sig.stop.iloc[27] == pytest.approx(
        df.dusuk.iloc[24] - 0.25 * g.atr(df.yuksek, df.dusuk, df.kapanis, 14).iloc[27])
    assert sig.hedef.iloc[27] == pytest.approx(105.8 + 2.0 * (105.8 - sig.stop.iloc[27]))
    # boşluk dolarsa (düşük önceki kapanışın altına iner) giriş yok
    kap2 = kap.copy()
    kap2[25] = 99.0
    assert (s.sinyaller(kapanistan(kap2, genlik=0.5)).yon == 0).all()
    # küçük boşluk: eşik altında
    kap3 = kap.copy()
    kap3[24:] = kap3[24:] - 3.9
    assert (DtGapDevam(min_gap_atr=1.5, konsol_n=1).sinyaller(kapanistan(kap3, genlik=0.5)).yon == 0).all()


def test_gap_devam_aşağı_boşluk_short_ve_seans_acilis_olcumu():
    kap = np.r_[_gun1_duz(), [96.0, 96.4, 95.8, 94.2], np.full(20, 95.0)]
    sig = DtGapDevam(min_gap_atr=1.5, konsol_n=1).sinyaller(kapanistan(kap, genlik=0.5))
    assert list(np.flatnonzero(sig.yon.to_numpy() == -1)) == [27] and sig.stop.iloc[27] > 96.0
    # "acilis" ölçümü: açılış=önceki kapanış olduğundan hiç boşluk yok
    assert (DtGapDevam(gap_olcum="acilis", min_gap_atr=1.5, konsol_n=1).sinyaller(kapanistan(kap, genlik=0.5)).yon == 0).all()


def test_gap_doldurma_gunici_donus_hedef_onceki_kapanis():
    kap = np.r_[_gun1_duz(), [96.0, 95.5, 97.0], np.full(21, 97.0)]
    df = kapanistan(kap, genlik=0.5)
    s = DtGapDoldurma(min_gap_atr=1.5, sma_gun=0, short=False, bekle_n=1)
    sig = s.sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert list(longlar) == [26]
    assert sig.hedef.iloc[26] == pytest.approx(100.0)       # hedef_oran=1: önceki kapanış
    assert sig.stop.iloc[26] < 95.0
    # günlük SMA filtresi (veri yok -> NaN): sinyal yok
    assert (DtGapDoldurma(min_gap_atr=1.5, sma_gun=50, short=False).sinyaller(df).yon == 0).all()
    # hedef_oran=0.5
    h = DtGapDoldurma(min_gap_atr=1.5, sma_gun=0, short=False, hedef_oran=0.5, min_rr=0.5).sinyaller(df)
    assert h.hedef.iloc[26] == pytest.approx(97.0 + 0.5 * 3.0)


def test_gap_devam_swing_gunluk_zirveye_yakin_kapanis():
    kap = np.r_[np.full(30, 100.0), [106.0], np.full(5, 106.0)]
    df = kapanistan(kap, genlik=0.4, freq="1D")
    sig = SwGapDevam(gap_olcum="ilk_bar", min_gap_atr=1.5, short=False).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert list(longlar) == [30]
    assert sig.stop.iloc[30] < 100.5 and sig.hedef.iloc[30] > 106.0
    # gün zirvesinden uzak kapanış (üst %67'de değil) -> yok
    df2 = df.copy()
    df2.iloc[30, df2.columns.get_loc("yuksek")] = 112.0
    assert (SwGapDevam(gap_olcum="ilk_bar", min_gap_atr=1.5, short=False).sinyaller(df2).yon == 0).all()


def test_gap_doldurma_swing_4h_ters_donus():
    # 4 gün düz; gün 5'in ilk 4h mumu -5 düşer (gap proxy), kalan mumlar toparlanır ama önceki kapanışın altında kalır
    kap = np.r_[np.full(24, 100.0), [95.0, 95.5, 96.5, 97.0, 97.5, 98.0], np.full(6, 98.0)]
    df = kapanistan(kap, genlik=0.3, freq="4h")
    sig = SwGapDoldurma(min_gap_atr=1.0, short=False, kapanis_yuzde=0.5, min_rr=0.5).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert list(longlar) == [29]                     # gün 5'in son mumu
    assert sig.hedef.iloc[29] == pytest.approx(100.0) and sig.stop.iloc[29] < 95.0
    # boşluk dolmuşsa (kapanış önceki kapanışın üstünde) giriş yok
    kap2 = kap.copy()
    kap2[29] = 100.5
    assert (SwGapDoldurma(min_gap_atr=1.0, short=False, min_rr=0.5).sinyaller(kapanistan(kap2, genlik=0.3, freq="4h")).yon == 0).all()


def test_kirilim_geri_test_swing_ve_scalp():
    kap = np.r_[np.full(30, 100.0), [105.0, 103.5, 102.0, 100.8, 102.0], np.full(10, 102.0)]
    df = kapanistan(kap, genlik=0.5, freq="1D")
    for s in (SwKgt(uzunluk=20, short=False), ScKgt(uzunluk=20, short=False)):
        sig = s.sinyaller(df)
        longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
        assert list(longlar) == [34], s.ad
        assert sig.stop.iloc[34] < 100.5 and sig.hedef.iloc[34] > 102.0
    # sinyal iptal: seviyenin altında kapanış
    kap2 = kap.copy()
    kap2[33] = 99.0
    assert (SwKgt(uzunluk=20, short=False).sinyaller(kapanistan(kap2, genlik=0.5, freq="1D")).yon == 0).all()


def test_bb_sikisma_kirilim_dar_bant_sonrasi_yukari_kirilim():
    rng = np.random.default_rng(1)
    kap = np.r_[100 + rng.normal(0, 1.5, 120), 100 + rng.normal(0, 0.05, 40), [100.8, 101.6, 102.5], np.full(5, 102.5)]
    df = kapanistan(kap, genlik=0.05, freq="4h")
    sig = SwBb(sikisma_pencere=100, short=False).sinyaller(df)
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert any(160 <= i <= 163 for i in longlar)
    assert all(sig.stop.iloc[i] < df.kapanis.iloc[i] for i in longlar)


def test_macd_hist_donus_ve_mod_ayrimi():
    i = np.arange(240)
    df = kapanistan(100 + 10 * np.sin(2 * np.pi * i / 60), genlik=0.3, freq="15min")
    p = ScMacd(mod="hist_donus")
    sig = p.sinyaller(df)
    h = g.macd(df.kapanis, 12, 26, 9)["histogram"]
    longlar = np.flatnonzero(sig.yon.to_numpy() == 1)
    shortlar = np.flatnonzero(sig.yon.to_numpy() == -1)
    assert len(longlar) >= 3 and len(shortlar) >= 3
    assert all(h.iloc[j] < 0 and h.iloc[j] > h.iloc[j - 1] and h.iloc[j - 1] <= h.iloc[j - 2] for j in longlar)
    assert all(h.iloc[j] > 0 and h.iloc[j] < h.iloc[j - 1] and h.iloc[j - 1] >= h.iloc[j - 2] for j in shortlar)
    atr = g.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    assert sig.stop.iloc[longlar[0]] == pytest.approx(df.kapanis.iloc[longlar[0]] - 1.5 * atr.iloc[longlar[0]])
    # çıkış = histogram sıfır işaret değişimi
    isaret = ((h > 0) & (h.shift(1) <= 0)) | ((h < 0) & (h.shift(1) >= 0))
    assert sig.cikis.sum() >= 3 and (sig.cikis <= isaret).all()
    # sinyal modu: histogram sıfır geçişinde (sonra) tetiklenir; hist_donus daha erken
    sm = ScMacd(mod="sinyal").sinyaller(df)
    ls = np.flatnonzero(sm.yon.to_numpy() == 1)
    assert len(ls) >= 3 and longlar[0] <= ls[0]


def test_pivot_seviye_swing_haftalik_onceki_hafta_ve_hedef():
    df = rastgele(6 * 7 * 12, 4, "4h")
    s = SwPivot(trend_ema=0)
    sig = s.sinyaller(df)
    gir = sig[sig.yon != 0]
    assert len(gir) > 20
    # ilk hafta (önceki hafta yok) sinyal üretemez
    assert (sig.yon.loc[:"2022-01-02 23:59"] == 0).all()
    # haftalık seviye: değişen gelecek veri (son hafta) önceki sinyalleri bozmaz
    df2 = df.copy()
    df2.iloc[-30:, df2.columns.get_loc("kapanis")] *= 1.5
    pdt.assert_frame_equal(s.sinyaller(df2).iloc[:-60], sig.iloc[:-60])
    assert not SwPivot(pivot_periyodu="gun", trend_ema=0).sinyaller(df).equals(sig)


# ------------------------------------------------------------------ kart ayarları

def _kart_ayarlari(aile):
    return json.loads((KART_DIZINI / f"{aile}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("s", HEPSI, ids=lambda s: s.ad)
def test_kart_ayarlari_gecerli(s):
    aileler = {a["aile_id"]: a for a in json.loads((KART_DIZINI.parent / "aileler.json").read_text(encoding="utf-8"))}
    kayitlar = _kart_ayarlari(s.ad)
    assert isinstance(kayitlar, list)
    gorulen = set()
    for r in kayitlar:
        assert set(r) == {"kart_id", "parametreler", "cikis_ayarlari", "not"}
        assert r["kart_id"] in aileler[s.ad]["kaynak_kartlar"] and r["kart_id"] not in gorulen
        gorulen.add(r["kart_id"])
        assert r["cikis_ayarlari"] is None and r["not"]
        yeni = type(s)(**r["parametreler"])          # bilinmeyen parametre ValueError verir
        yeni.sinyaller(veri(s.stil, 1200))           # çalışır


def test_donchian_yonlu_cikis_sanal_pozisyonsuz():
    """Çıkış her mumda yönlü koşuldur: giriş sırası/yönü sinyallere bağlı değildir."""
    kap = np.r_[np.full(40, 100.0), np.linspace(100, 130, 30), np.linspace(130, 100, 40)]
    df = kapanistan(kap, genlik=0.3, freq="1D")
    s = SwDonchian(giris_n=20, cikis_n=10)
    a = s.sinyaller(df)
    b = s.yeni(short=False).sinyaller(df)
    pdt.assert_series_equal(a.cikis_long, b.cikis_long)      # short girişleri long çıkışını değiştirmez
    pdt.assert_series_equal(a.cikis_short, b.cikis_short)
    assert not a.cikis.any()
    assert (a.cikis_long & a.cikis_short).sum() == 0
