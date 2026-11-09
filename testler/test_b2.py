"""B2 grubu (gösterge/momentum/trend aileleri): lookahead, sentetik sinyal, stop tarafı, gün sonu, kart ayarları."""
import json
import pathlib

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import seans_son_mumu
from motor.strateji.daytrade.adx_trend_baslangici import AdxTrendBaslangici
from motor.strateji.daytrade.ichimoku import Ichimoku as DIchimoku
from motor.strateji.daytrade.rsi_asiri_donus import RsiAsiriDonus as DRsi
from motor.strateji.daytrade.trend_yapi_dow import TrendYapiDow as DDow
from motor.strateji.scalp.cci_esik import CciEsik as PCci
from motor.strateji.scalp.fisher import Fisher
from motor.strateji.scalp.heikin_ashi_donus import HeikinAshiDonus as PHa
from motor.strateji.scalp.rsi_asiri_donus import RsiAsiriDonus as PRsi
from motor.strateji.scalp.rsi_diverjans import RsiDiverjans as PDiv
from motor.strateji.scalp.rsi_momentum_esik import RsiMomentumEsik as PMom
from motor.strateji.scalp.trend_yapi_dow import TrendYapiDow as PDow
from motor.strateji.swing.bollinger_cift_bant_trend import BollingerCiftBantTrend
from motor.strateji.swing.cci_esik import CciEsik as SCci
from motor.strateji.swing.crane_reaksiyon_swing import CraneReaksiyonSwing
from motor.strateji.swing.goreceli_guc_momentum import GoreceliGucMomentum
from motor.strateji.swing.heikin_ashi_donus import HeikinAshiDonus as SHa
from motor.strateji.swing.ichimoku import Ichimoku as SIchimoku
from motor.strateji.swing.rsi_asiri_donus import RsiAsiriDonus as SRsi
from motor.strateji.swing.rsi_diverjans import RsiDiverjans as SDiv
from motor.strateji.swing.rsi_momentum_esik import RsiMomentumEsik as SMom
from motor.strateji.swing.uc_cubuklu_net_hat import UcCubukluNetHat

SINIFLAR = [
    AdxTrendBaslangici, BollingerCiftBantTrend, SCci, PCci, Fisher, SHa, PHa, SIchimoku, DIchimoku,
    SRsi, PRsi, DRsi, SDiv, PDiv, SMom, PMom, GoreceliGucMomentum, UcCubukluNetHat, CraneReaksiyonSwing,
    DDow, PDow,
]
FREKANS = {"swing": "1D", "scalp": "15min", "daytrade": "1h"}


def rastgele(stil, seed=5):
    n, vol = {"swing": (1400, 0.02), "scalp": (3500, 0.004), "daytrade": (2500, 0.008)}[stil]
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0002, vol, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range("2022-01-01", periods=n, freq=FREKANS[stil], tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": rng.uniform(1, 3, n)}, index=idx)


def kapanistan(kap, genlik=0.3, freq="1D"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range("2022-01-01", periods=len(kap), freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": 1.0}, index=idx)


def parca(*noktalar):
    """(deger, adim_sayisi) ... -> parçalı doğrusal kapanış dizisi; ilk eleman başlangıç değeri."""
    seri = [noktalar[0]]
    for hedef, n in zip(noktalar[1::2], noktalar[2::2]):
        seri += list(np.linspace(seri[-1], hedef, n + 1)[1:])
    return np.array(seri)


VARYANTLAR = [
    (AdxTrendBaslangici, {}), (AdxTrendBaslangici, {"yapi": False, "adx_esik": 20.0, "hedef_r": 2.0}),
    (BollingerCiftBantTrend, {}), (BollingerCiftBantTrend, {"dis_dahil": True, "periyot": 30}),
    (SCci, {}), (SCci, {"mod": "lambert"}), (SCci, {"mod": "esik30", "trend_ma": 100, "cci_periyot": 9}),
    (PCci, {}), (PCci, {"mod": "esik30", "trend_ma": 0}),
    (Fisher, {}), (Fisher, {"sinyal_tipi": "ma", "asiri_esik": 1.0, "trend_ma": 60}),
    (SHa, {}), (SHa, {"varyant": "graham", "golgesiz": True, "trend_ma": 50}),
    (PHa, {}), (PHa, {"golgesiz": False, "onceki_n": 1, "trend_ma": 0}),
    (SIchimoku, {}), (SIchimoku, {"mod": "tk_bulut", "tk_kesisim": True, "stop_tipi": "bulut"}),
    (DIchimoku, {}), (DIchimoku, {"tk_kesisim": True, "stop_tipi": "kijun", "hedef_r": 1.5}),
    (SRsi, {}), (SRsi, {"rsi_periyot": 2, "alt": 10.0, "mod": "bolgede", "cikis_rsi": 0.0}),
    (PRsi, {}), (PRsi, {"adx_max": 25.0, "vo_esik": 30.0, "trend_ma": 0}),
    (DRsi, {}), (DRsi, {"gosterge": "demarker", "trend_ma": 0}),
    (SDiv, {}), (SDiv, {"pivot_k": 5, "teyit": "mum", "hedef_tipi": "orta_bant", "bolge_rsi": 60.0}),
    (PDiv, {}), (PDiv, {"osilator": "cci", "bb_sart": False, "teyit": "ema", "hedef_tipi": "r"}),
    (SMom, {}), (SMom, {"esik": 60.0, "ust_tf": "1w", "hedef_r": 2.0}),
    (PMom, {}), (PMom, {"esik": 60.0, "ust_tf": "", "rsi_periyot": 9}),
    (GoreceliGucMomentum, {"short": True}), (GoreceliGucMomentum, {"mom_mod": "esik", "mom_n": 60, "mom_esik": 0.1, "yakinlik": 0.8, "zaman_mum": 10}),
    (UcCubukluNetHat, {}), (UcCubukluNetHat, {"pivot_k": 2, "cubuk_n": 4, "sma_filtre": 0, "hedef_r": 2.0}),
    (CraneReaksiyonSwing, {"pivot_k": 2, "min_gun": 3}), (CraneReaksiyonSwing, {"mod": "iki_gun", "pivot_k": 2, "iki_gun_onay": False}),
    (DDow, {}), (DDow, {"mod": "coklu_tf", "yapi_sart": False}), (DDow, {"ust_tf": "", "hedef_r": 0.0, "pivot_k": 2}),
    (PDow, {}), (PDow, {"mod": "yapi", "ust_tf": ""}),
]


def _id(v):
    s = v[0](**v[1])
    return f"{s.ad.split('__')[0]}-{s.ad.split('__')[1]}-{abs(hash(str(sorted(v[1].items())))) % 997}"


@pytest.mark.parametrize("v", VARYANTLAR, ids=_id)
def test_lookahead_yok(v):
    s = v[0](**v[1])
    df = rastgele(s.stil)
    tam = s.sinyaller(df)
    for n in (150, 477, 1001, len(df) - 3):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("v", VARYANTLAR, ids=_id)
def test_cerceve_ve_stop_tarafi(v):
    s = v[0](**v[1])
    df = rastgele(s.stil, seed=3)
    sig = s.sinyaller(df)
    assert sig.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    assert s.ad.startswith(s.stil + "__") and s.cikis_var_mi()
    gir = sig[sig.yon != 0]
    assert gir.stop.notna().all()
    kap = df.kapanis[gir.index]
    assert (gir.stop[gir.yon == 1] < kap[gir.yon == 1]).all()
    assert (gir.stop[gir.yon == -1] > kap[gir.yon == -1]).all()
    h = gir[gir.hedef.notna()]
    assert (h.hedef[h.yon == 1] > kap[h.index][h.yon == 1]).all()
    assert (h.hedef[h.yon == -1] < kap[h.index][h.yon == -1]).all()


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda c: c.ad)
def test_sinif_tanimi(sinif):
    s = sinif()
    assert s.ad.startswith(s.stil + "__") and s.stil in ("swing", "scalp", "daytrade")
    assert s.cikis_var_mi()
    assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)
    kombinasyon = int(np.prod([len(v) for v in s.parametre_izgarasi.values()]))
    assert 1 < kombinasyon <= 27, kombinasyon
    assert "short" in s.varsayilan_parametreler


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda c: c.ad)
def test_izgara_ve_short_kapali(sinif):
    s = sinif()
    df = rastgele(s.stil, seed=9)
    assert (sinif(short=False).sinyaller(df).yon >= 0).all()
    # izgaranın birkaç noktası hata vermeden çalışır ve her birinde sinyal çerçevesi geçerli
    import itertools
    anahtarlar = list(s.parametre_izgarasi)
    for i, kombo in enumerate(itertools.product(*s.parametre_izgarasi.values())):
        if i % 5:
            continue
        sig = s.yeni(**dict(zip(anahtarlar, kombo))).sinyaller(df)
        gir = sig[sig.yon != 0]
        assert gir.stop.notna().all()


@pytest.mark.parametrize("sinif", [AdxTrendBaslangici, DIchimoku, DRsi, DDow], ids=lambda c: c.ad)
def test_gun_sonu(sinif):
    s = sinif()
    df = rastgele("daytrade")
    sig = s.sinyaller(df)
    son = seans_son_mumu(df.index, 0.0)
    assert son.sum() > 50
    assert (sig.yon[son] == 0).all()
    assert sig.cikis[son].all()
    # kapsam: kısmi veri
    pdt.assert_frame_equal(s.sinyaller(df.iloc[:777]), sig.iloc[:777])


# ---------------------------------------------------------------- sentetik senaryolar

def test_rsi_asiri_donus_long_ve_short():
    kap = np.r_[np.full(40, 100.0), np.linspace(100, 70, 25), np.linspace(70, 90, 10),
                np.linspace(90, 130, 25), np.linspace(130, 95, 10)]
    df = kapanistan(kap)
    s = SRsi(trend_ma=0)
    sig = s.sinyaller(df)
    long_i = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(long_i) >= 1
    assert 65 <= long_i[0] <= 80      # düşüş sırasında/sonrasında RSI 30'u yukarı kesti
    short_i = np.flatnonzero(sig.yon.to_numpy() == -1)
    assert len(short_i) >= 1 and short_i[0] > long_i[0]
    assert SRsi(trend_ma=0, short=False).sinyaller(df).yon.min() == 0
    assert sig.cikis.any()


def test_bollinger_cift_bant_dogrusal_trend():
    rng = np.random.default_rng(1)
    kap = np.r_[np.full(40, 100.0), 100 + np.arange(1, 41) * 1.0 + rng.normal(0, 0.2, 40)]
    kap = np.r_[kap, kap[-1] - np.arange(1, 41) * 1.0 + rng.normal(0, 0.2, 40)]
    sig = BollingerCiftBantTrend().sinyaller(kapanistan(kap))
    assert (sig.yon.iloc[:40] == 0).all()
    assert (sig.yon.iloc[40:80] == 1).any()
    assert (sig.yon.iloc[80:] == -1).any()
    # stop = orta bant civarı (kapanışın altında)
    gir = sig[sig.yon == 1]
    assert (gir.stop < kapanistan(kap).kapanis[gir.index]).all()


def test_cci_lambert_sicrama():
    kap = np.r_[np.full(30, 100.0) + np.tile([0.0, 0.3], 15), np.linspace(100, 115, 8), np.full(10, 115.0)]
    sig = SCci(mod="lambert", trend_ma=0).sinyaller(kapanistan(kap))
    assert (sig.yon.iloc[:30] == 0).all()
    assert (sig.yon.iloc[30:40] == 1).any()
    assert sig.cikis.iloc[30:].any()


def test_heikin_ashi_v_donusu():
    kap = np.r_[np.linspace(120, 100, 15), np.linspace(100, 125, 15)]
    sig = SHa(onceki_n=2).sinyaller(kapanistan(kap))
    li = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(li) >= 1 and 14 <= li[0] <= 22
    assert (sig.yon.iloc[:12] == 1).sum() == 0
    kap2 = np.r_[np.linspace(100, 120, 15), np.linspace(120, 100, 15)]
    si = np.flatnonzero(SHa(onceki_n=2).sinyaller(kapanistan(kap2)).yon.to_numpy() == -1)
    assert len(si) >= 1 and si[0] >= 14


def test_ichimoku_bulut_ustune_cikis():
    kap = np.r_[np.full(120, 100.0), np.linspace(100, 125, 20), np.full(5, 125.0)]
    df = kapanistan(kap, genlik=0.2)
    sig = SIchimoku(mod="kijun_bulut").sinyaller(df)
    li = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(li) >= 1 and li[0] >= 120
    assert (sig.yon.iloc[:120] == 0).all()
    ic = b.ichimoku(df.yuksek, df.dusuk, 9, 26, 52, 26)
    assert ic["bulut_ust"].iloc[:77].isna().all()           # 52 + 26 - 1 mum sonra bulut hazır
    # bulut nedensel: t. bulut, kaydirma mum önceki Tenkan/Kijun ortalamasıdır
    pdt.assert_series_equal(ic["span_a"].iloc[60:], (((ic["tenkan"] + ic["kijun"]) / 2).shift(26)).iloc[60:], check_names=False)


def test_adx_trend_baslangici_yukari_trend():
    rng = np.random.default_rng(2)
    kap = np.r_[100 + rng.normal(0, 0.4, 80), 100 + np.cumsum(np.full(60, 0.8)) + rng.normal(0, 0.3, 60)]
    df = kapanistan(kap, genlik=0.4, freq="1h")
    sig = AdxTrendBaslangici(yapi=False).sinyaller(df)
    assert (sig.yon.iloc[80:] == 1).any()
    assert not ((sig.yon.iloc[80:] == -1).any())


def test_goreceli_guc_geri_cekilmede_long():
    a, son = [100.0], 100.0
    for _ in range(14):
        son *= 1.25
        a += [son, 8]
        son *= 0.94
        a += [son, 3]
    a += [son * 0.7, 6]
    kap = parca(*a)
    df = kapanistan(kap, genlik=0.1)
    s = GoreceliGucMomentum(mom_mod="esik", mom_n=30, mom_esik=0.2, zirve_n=60, ema_periyot=10, yakinlik=0.8)
    sig = s.sinyaller(df)
    assert (sig.yon == 1).sum() >= 2
    assert (sig.yon == -1).sum() == 0
    assert sig.cikis.any()


def test_uc_cubuklu_net_hat_v_donusu():
    kap = np.r_[np.linspace(100, 130, 15), np.linspace(130, 100, 15), np.linspace(100, 118, 9)]
    df = kapanistan(kap, genlik=0.4)
    sig = UcCubukluNetHat(pivot_k=2, sma_filtre=0).sinyaller(df)
    li = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(li) >= 1 and 31 <= li[0] <= 40
    assert sig.stop[sig.yon == 1].iloc[0] < 100.5            # pivot dibinin altı
    # yükseliş + tepe + düşüşle kırılım short
    kap2 = np.r_[np.linspace(100, 70, 15), np.linspace(70, 100, 15), np.linspace(100, 82, 9)]
    si = np.flatnonzero(UcCubukluNetHat(pivot_k=2, sma_filtre=0).sinyaller(kapanistan(kap2, genlik=0.4)).yon.to_numpy() == -1)
    assert len(si) >= 1 and si[0] >= 31


def test_crane_reaksiyon_swing_orta_nokta():
    kap = parca(100.0, 90, 8, 120, 8, 100, 8, 130, 8, 112, 8, 128, 8)
    df = kapanistan(kap, genlik=0.3)
    s = CraneReaksiyonSwing(pivot_k=2, min_gun=3)
    sig = s.sinyaller(df)
    li = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(li) == 1
    t = li[0]
    assert t > 40 and df.kapanis.iloc[t] >= 121             # tetik = 130 - 0.5*(130-112)
    assert abs(sig.hedef.iloc[t] - (112 + (130 - 100))) < 1e-6   # C + (B - A)
    assert sig.stop.iloc[t] < 112
    assert sig.zaman_cikisi_mum.iloc[t] == 20


def test_dow_yapi_kirilimi():
    kap = parca(100.0, 90, 6, 110, 6, 98, 6, 125, 6, 112, 6, 130, 6, 120, 4)
    df = kapanistan(kap, genlik=0.3, freq="1h")
    df.index = pd.date_range("2022-01-03 00:00", periods=len(df), freq="1h", tz="UTC")
    s = DDow(pivot_k=2, ust_tf="", hedef_r=2.0)
    sig = s.sinyaller(df)
    li = np.flatnonzero(sig.yon.to_numpy() == 1)
    assert len(li) >= 1
    assert sig.stop.iloc[li[0]] < df.kapanis.iloc[li[0]]
    assert sig.hedef.iloc[li[0]] > df.kapanis.iloc[li[0]]
    assert np.isnan(sig.hedef.iloc[:5]).all()


def test_dow_coklu_tf_uyum():
    n = 400
    kap = 100 + np.arange(n) * 0.5 + np.tile([0.0, 0.3, 0.1, 0.4], n // 4)
    df = kapanistan(kap, genlik=0.2, freq="15min")
    sig = PDow(mod="coklu_tf", tf_listesi=("30m", "1h"), ust_tf="").sinyaller(df)
    assert (sig.yon == 1).any() and not (sig.yon == -1).any()


def test_rsi_diverjans_boga():
    # keskin düşüş (RSI çok düşük dip), toparlanma, daha düşük fiyat ama daha yumuşak ikinci dip, sonra yükseliş
    kap = parca(100.0, 70, 10, 92, 8, 69, 22, 85, 8, 100, 6)
    df = kapanistan(kap, genlik=0.3)
    s = SDiv(pivot_k=3, rsi_periyot=5, bolge_rsi=100.0, teyit="ema", hedef_r=2.0, max_aralik=60)
    sig = s.sinyaller(df)
    assert (sig.yon == 1).any()
    gir = sig[sig.yon == 1].iloc[0]
    assert gir.stop < 69 and gir.hedef > df.kapanis.loc[gir.name]


def test_rsi_momentum_50_kesisim_ve_ust_tf():
    n = 700
    rng = np.random.default_rng(4)
    kap = 100 + np.cumsum(rng.normal(0, 0.5, n))
    df = kapanistan(kap, genlik=0.3, freq="15min")
    cekirdek = PMom(ust_tf="").sinyaller(df)
    filtreli = PMom(ust_tf="1h").sinyaller(df)
    assert (cekirdek.yon != 0).sum() > (filtreli.yon != 0).sum() > 0
    from motor.strateji import gostergeler as g
    r = g.rsi(df.kapanis, 14)
    li = filtreli.index[filtreli.yon == 1]
    assert (r[li] > 50).all() and (r.shift(1)[li] <= 50).all()


def test_fisher_kesisim_ozellikleri():
    df = rastgele("scalp", seed=2).iloc[:1500]
    f = b.fisher(df.yuksek, df.dusuk, 7)
    sig = Fisher().sinyaller(df)
    li = sig.index[sig.yon == 1]
    assert len(li) > 5
    assert (f["fisher"][li] > f["tetik"][li]).all() and (f["fisher"].shift(1)[li] <= f["tetik"].shift(1)[li]).all()
    assert f["fisher"].abs().max() < 8


def test_yuzdelik_sira_ve_cci_nedensel():
    s = pd.Series(np.arange(1, 11, dtype=float))
    sira = b.yuzdelik_sira(s, 5)
    assert sira.iloc[:4].isna().all() and (sira.iloc[4:] == 1.0).all()
    df = rastgele("swing")
    c1 = b.cci(df.yuksek, df.dusuk, df.kapanis, 14)
    c2 = b.cci(df.yuksek.iloc[:500], df.dusuk.iloc[:500], df.kapanis.iloc[:500], 14)
    pdt.assert_series_equal(c1.iloc[:500], c2)


def test_bilinmeyen_parametre_ve_mod():
    with pytest.raises(ValueError):
        SRsi(yok=1)
    with pytest.raises(ValueError):
        SRsi(mod="x").sinyaller(rastgele("swing"))


# ---------------------------------------------------------------- kart ayarları

KART_DIZIN = pathlib.Path(__file__).resolve().parent.parent / "stratejiler" / "kart_ayarlari"
SINIF_ESLEME = {c().ad: c for c in SINIFLAR}


@pytest.mark.parametrize("aile", sorted(SINIF_ESLEME))
def test_kart_ayarlari_gecerli(aile):
    yol = KART_DIZIN / f"{aile}.json"
    assert yol.exists(), yol
    liste = json.loads(yol.read_text(encoding="utf-8"))
    assert isinstance(liste, list)
    sinif = SINIF_ESLEME[aile]
    kartlar = {k["kart_id"] for a in json.loads((KART_DIZIN.parent / "aileler.json").read_text(encoding="utf-8"))
               if a["aile_id"] == aile for k in [{"kart_id": x} for x in a["kaynak_kartlar"]]}
    df = rastgele(sinif().stil, seed=7)
    for kayit in liste:
        assert set(kayit) >= {"kart_id", "parametreler", "cikis_ayarlari", "not"}
        assert kayit["kart_id"] in kartlar
        assert kayit["cikis_ayarlari"] is None
        s = sinif(**kayit["parametreler"])
        sig = s.sinyaller(df)
        assert sig.index.equals(df.index)
