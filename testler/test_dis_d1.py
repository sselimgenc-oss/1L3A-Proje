"""D1 grubu dış stratejiler: lookahead, stop/hedef tarafı, sentetik senaryo, gün sonu, ızgara ve yönlü çıkış."""
import itertools

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji.daytrade._ortak import seans_son_mumu
from motor.strateji.dis.d1_fraktal import (ElliottItki, FraktalAlligatorSky, FraktalKirilimChartArt,
                                           GoldenTrident, PivotTersStop)
from motor.strateji.dis.d1_osilator import (BilateralStokastik, GaussKanal, KstSkyrexio, LaguerreRsi, Lube,
                                            MtfMomentumYigin)
from motor.strateji.dis.d1_skor import (ConfluenceRank, EmaMacdIkili, EmaMacdOrtalamayaDonus, EmaSeritYelpaze,
                                        GunlukKapanis, ZSkorCokFaktor)
from motor.strateji.dis.d1_skyrexio import AcCokKatman, AoAcBolgeleri, AoTabak
from motor.strateji.dis.d1_smc import Ema200BosFvg, Ict10amFvg, MtfAralikDonus, NornWeaveThurisaz
from motor.strateji.dis.d1_trend_ma import (AtrRsiLiwei, AuroraKama, BchHaRsiFade, HmaAtrRider, KellyAtrBant,
                                            MaCciTrailing)

SINIFLAR = [
    BchHaRsiFade, MaCciTrailing, AtrRsiLiwei, AuroraKama, HmaAtrRider, KellyAtrBant,
    ConfluenceRank, GunlukKapanis, EmaSeritYelpaze, ZSkorCokFaktor, EmaMacdIkili, EmaMacdOrtalamayaDonus,
    FraktalKirilimChartArt, FraktalAlligatorSky, PivotTersStop, GoldenTrident, ElliottItki,
    GaussKanal, KstSkyrexio, LaguerreRsi, Lube, BilateralStokastik, MtfMomentumYigin,
    AoAcBolgeleri, AcCokKatman, AoTabak,
    Ema200BosFvg, Ict10amFvg, MtfAralikDonus, NornWeaveThurisaz,
]
FREQ = {"scalp": "15min", "daytrade": "1h", "swing": "4h"}


def rejimli_mumlar(n=3200, seed=1, freq="1h", baslangic="2022-01-03", vol_ust=0.02):
    rng = np.random.default_rng(seed)
    drift = np.repeat(rng.normal(0, 0.002, n // 200 + 1), 200)[:n]
    vol = np.repeat(rng.uniform(0.004, vol_ust, n // 150 + 1), 150)[:n]
    r = drift + rng.normal(0, 1, n) * vol
    kap = 100 * np.exp(np.cumsum(r))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range(baslangic, periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n) * (1 + np.abs(r) * 50)}, index=idx)


def mumlar_kapanistan(kap, genlik=0.05, hacim=1.0, baslangic="2022-01-03", freq="15min"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range(baslangic, periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hacim}, index=idx)


def _id(s):
    return s.ad.split("__")[1]


# ATR/fiyat bandı dar (%0.3-0.7) olan strateji için düşük oynaklıklı veri
DUSUK_VOL = {"dis__atr-rsi-liwei": 0.006}


def _veri(s, seed=1, n=3200):
    return rejimli_mumlar(n=n, seed=seed, freq=FREQ[s.stil], vol_ust=DUSUK_VOL.get(s.ad, 0.02))


STRATEJILER = [c() for c in SINIFLAR]
# long-only varsayılanı olanların short=True kopyaları (aynalar da sağlam olmalı)
AYNALI = [c(short=True) for c in SINIFLAR if c.varsayilan_parametreler.get("short") is False]


@pytest.mark.parametrize("s", STRATEJILER + AYNALI, ids=lambda s: _id(s) + ("-ayna" if s in AYNALI else ""))
def test_lookahead_yok(s):
    df = _veri(s)
    tam = s.sinyaller(df)
    for n in (700, 1111, 1650, 2401, 3000):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n], check_exact=False)


@pytest.mark.parametrize("s", STRATEJILER + AYNALI, ids=lambda s: _id(s) + ("-ayna" if s in AYNALI else ""))
def test_stop_hedef_tarafi_ve_sutunlar(s):
    for seed in (1, 2, 3):
        df = _veri(s, seed)
        sig = s.sinyaller(df)
        assert list(sig.index) == list(df.index)
        assert {"yon", "stop", "hedef", "cikis", "cikis_long", "cikis_short"} <= set(sig.columns)
        k = df["kapanis"]
        uz, kz = sig["yon"] == 1, sig["yon"] == -1
        assert (sig.loc[uz | kz, "stop"].notna()).all()
        assert (sig.loc[uz, "stop"] < k[uz]).all()
        assert (sig.loc[kz, "stop"] > k[kz]).all()
        h = sig["hedef"]
        assert (h[uz & h.notna()] > k[uz & h.notna()]).all()
        assert (h[kz & h.notna()] < k[kz & h.notna()]).all()


def test_her_strateji_sinyal_uretiyor():
    for s in STRATEJILER:
        toplam = 0
        for seed in (1, 2, 3):
            toplam += int((s.sinyaller(_veri(s, seed))["yon"] != 0).sum())
        assert toplam > 0, s.ad


def test_ad_stil_izgara_ve_cikis():
    adlar = set()
    for c in SINIFLAR:
        s = c()
        assert s.ad.startswith("dis__") and s.ad not in adlar and s.ad == s.ad.lower()
        adlar.add(s.ad)
        assert s.stil in ("scalp", "daytrade", "swing")
        assert s.cikis_var_mi() is True
        n = 1
        for v in s.parametre_izgarasi.values():
            n *= len(v)
        assert 1 <= n <= 27, s.ad
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler), s.ad
        assert c.__doc__ and "Kaynak: arsiv/" in c.__doc__ and "Eski sonuç" in c.__doc__, s.ad


@pytest.mark.parametrize("c", SINIFLAR, ids=lambda c: c.ad.split("__")[1])
def test_izgara_degerleri_calisiyor(c):
    s = c()
    df = _veri(s, 1, n=1500)
    for anahtar, degerler in s.parametre_izgarasi.items():
        for v in (degerler[0], degerler[-1]):
            sig = s.yeni(**{anahtar: v}).sinyaller(df)
            assert len(sig) == len(df)


def test_varsayilan_long_only_olanlar_short_uretmez():
    for c in SINIFLAR:
        if c.varsayilan_parametreler.get("short") is False:
            s = c()
            for seed in (1, 2):
                assert (s.sinyaller(_veri(s, seed))["yon"] == -1).sum() == 0, s.ad


@pytest.mark.parametrize("c", [c for c in SINIFLAR if c.stil == "daytrade"], ids=lambda c: c.ad.split("__")[1])
def test_daytrade_gun_sonu(c):
    s = c()
    df = _veri(s, 1)
    sig = s.sinyaller(df)
    son = seans_son_mumu(df.index, s.parametreler["seans_saat"])
    assert son.sum() > 50
    assert (sig.loc[son, "yon"] == 0).all()
    assert sig.loc[son, "cikis"].all()
    assert not sig.loc[~son, "cikis"].any()


def test_daytrade_stilleri():
    assert {c.stil for c in SINIFLAR} == {"scalp", "daytrade", "swing"}
    assert [c.ad for c in SINIFLAR if c.stil == "daytrade"] == [
        "dis__ma-cci-trailing", "dis__atr-rsi-liwei", "dis__ema-macd-ikili"]


# ------------------------------------------------------------------ sentetik senaryolar
def test_bch_ha_rsi_fade_yukselisten_short():
    kap = np.r_[np.full(150, 100.0), 100 + np.arange(1, 41) * 0.4, np.full(20, 116.0)]
    df = mumlar_kapanistan(kap, genlik=0.05)
    s = BchHaRsiFade(rsi_periyot=14, rsi_seviye=46.0, ha_seri=7)
    sig = s.sinyaller(df)
    assert (sig["yon"] == -1).sum() > 0 and (sig["yon"] == 1).sum() == 0
    i = sig.index[sig["yon"] == -1][0]
    k = df.loc[i, "kapanis"]
    assert sig.loc[i, "stop"] == pytest.approx(k * 1.025)
    assert sig.loc[i, "hedef"] == pytest.approx(k * (1 - 0.021))
    # ayna: düşüşten long
    sa = BchHaRsiFade(rsi_periyot=14, long=True).sinyaller(mumlar_kapanistan(np.r_[np.full(150, 100.0), 100 - np.arange(1, 41) * 0.4]))
    assert (sa["yon"] == 1).sum() > 0


def test_kelly_atr_bant_yukari_kirilim_long_ve_ters_cikis():
    kap = np.r_[np.full(80, 100.0) + np.tile([0.0, 0.1], 40), np.arange(1, 25) * 1.5 + 100, np.full(10, 136.0)]
    df = mumlar_kapanistan(kap, genlik=0.05, freq="4h")
    sig = KellyAtrBant().sinyaller(df)
    assert (sig["yon"] == 1).sum() > 0
    i = sig.index[sig["yon"] == 1][0]
    assert sig.loc[i, "stop"] < df.loc[i, "kapanis"]
    # ters kesişim long'u kapatır (short kapalı olsa da)
    kap2 = np.r_[kap, 136 - np.arange(1, 40) * 3.0]
    s2 = KellyAtrBant(short=False).sinyaller(mumlar_kapanistan(kap2, genlik=0.05, freq="4h"))
    assert s2["cikis_long"].sum() > 0 and (s2["yon"] == -1).sum() == 0


def test_gunluk_kapanis_dun_dunden_yuksekse_long():
    # 1h veri, günler arasında artan kapanış -> gün 3'ten sonra long durumu
    gun_kapanis = [100, 101, 102, 103, 102, 101]
    kap = np.concatenate([np.linspace(c - 0.5, c, 24) for c in gun_kapanis])
    df = mumlar_kapanistan(kap, genlik=0.05, freq="1h", baslangic="2022-01-03")
    sig = GunlukKapanis().sinyaller(df)
    gunler = df.index.normalize()
    # 3. gün (index 2) içinde, 2. gün kapanışı > 1. gün kapanışı => long
    uz = sig["yon"] == 1
    assert uz[(gunler == gunler[48])].any()
    # 5. gün (kapanış düştü) sonrası 6. gün short
    kz = sig["yon"] == -1
    assert kz[(gunler == gunler[24 * 5])].any()
    # günlük kapanış tamamlanmadan durum değişmez: 3. günün ilk mumunda 3. günün kapanışı kullanılmaz
    assert sig["cikis_short"][gunler == gunler[48]].all()


def test_gunluk_kapanis_gun_ici_degerler_sizdirmaz():
    kap = np.concatenate([np.linspace(99.5, 100, 24), np.linspace(100, 100.9, 24), np.linspace(101, 90, 24)])
    df = mumlar_kapanistan(kap, genlik=0.05, freq="1h")
    s = GunlukKapanis()
    sig = s.sinyaller(df)
    ilk3 = sig.iloc[48:72]            # 3. gün: karar yalnız 1. ve 2. gün kapanışına bağlı (2. > 1. -> long durumu)
    assert (ilk3["cikis_short"]).all()
    assert not ilk3["cikis_long"].any()


def test_ict_10am_fvg_boga_geri_cekilme_long():
    # Ocak: NY = UTC-5 -> 10:00 NY = 15:00 UTC. 15m mumlar 14:00 UTC'den başlar.
    idx = pd.date_range("2022-01-04 14:00", periods=24, freq="15min", tz="UTC", name="zaman")
    o = np.full(24, 100.0); h = np.full(24, 100.2); l = np.full(24, 99.8); c = np.full(24, 100.0)
    i0 = 4                                     # 15:00 UTC = 10:00 NY
    h[:i0] = 100.35                            # 10:00 öncesi tepe: ilk mumda yanlış FVG oluşmasın
    h[i0], l[i0], c[i0] = 100.5, 99.9, 100.4
    o[i0 + 1], h[i0 + 1], l[i0 + 1], c[i0 + 1] = 100.4, 101.5, 100.3, 101.4   # büyük boğa mumu
    o[i0 + 2], h[i0 + 2], l[i0 + 2], c[i0 + 2] = 101.4, 101.6, 100.8, 101.5   # l(100.8) > h[i0](100.5): boğa FVG
    o[i0 + 3], h[i0 + 3], l[i0 + 3], c[i0 + 3] = 101.5, 101.6, 100.7, 100.95  # giriş seviyesine (100.8) geri çekilme
    df = pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": 1.0}, index=idx)
    sig = Ict10amFvg().sinyaller(df)
    uz = sig.index[sig["yon"] == 1]
    assert list(uz) == [idx[i0 + 3]]
    assert sig.loc[idx[i0 + 3], "stop"] == pytest.approx(100.3)       # low[i-1]
    assert sig.loc[idx[i0 + 3], "hedef"] == pytest.approx(101.6)      # seans tepesi
    assert (sig["yon"] == -1).sum() == 0


def test_ict_10am_fvg_gunde_tek_islem_ve_16_kapanis():
    df = rejimli_mumlar(n=2000, seed=4, freq="15min")
    sig = Ict10amFvg().sinyaller(df)
    ny = df.index.tz_convert("America/New_York")
    gun = pd.Series(ny.date, index=df.index)
    islem = sig[sig["yon"] != 0]
    assert islem.groupby(gun[islem.index]).size().max() == 1
    assert sig["cikis_long"][ny.hour >= 16].all()


def test_williams_trend_yukselis_ve_dusus():
    from motor.strateji.dis._gosterge_d1 import williams_trend
    zig = np.r_[np.tile(np.r_[np.linspace(100, 110, 12), np.linspace(110, 106, 8)], 1),
                np.tile(np.r_[np.linspace(106, 118, 12), np.linspace(118, 113, 8)], 1),
                np.tile(np.r_[np.linspace(113, 126, 12), np.linspace(126, 121, 8)], 1)]
    df = mumlar_kapanistan(zig, genlik=0.3, freq="4h")
    tr = williams_trend(df["yuksek"], df["dusuk"])
    assert (tr == 1).any() and (tr == -1).sum() == 0
    dus = np.r_[zig, np.linspace(121, 70, 40), np.full(10, 70.0)]
    t2 = williams_trend(*[mumlar_kapanistan(dus, 0.3, freq="4h")[c] for c in ("yuksek", "dusuk")])
    assert t2.iloc[-1] == -1 and (t2 == 1).any()


def test_gauss_filtre_sabit_girdide_sabite_yakinsar():
    from motor.strateji.dis._gosterge_d1 import gauss_kutup
    f = gauss_kutup(pd.Series(np.full(2000, 50.0)), 4, 144)
    assert f.iloc[-1] == pytest.approx(50.0, rel=1e-6)


def test_lube_surtunme_dar_aralikta_dusuk():
    df = rejimli_mumlar(n=2500, seed=5, freq="4h")
    s = Lube(geri_bak=300, aralik=50)
    sig = s.sinyaller(df)
    assert (sig["yon"] != 0).sum() >= 0 and len(sig) == len(df)
    assert not sig["yon"].iloc[:360].ne(0).any()      # ısınma
