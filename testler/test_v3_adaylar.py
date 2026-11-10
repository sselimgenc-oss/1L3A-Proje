"""v3 adayları ilk parti: yalnız sentetik kural ve kayıt testleri."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.v3 import FipKesitsel, Funding1sDevam, Funding7gTercil, FundingKesitCarry
from motor.strateji.dis.v3_adaylar import (
    AdaptiveTrend6s, AsyaKutuKirilimMa50, DonchianAnsambl, HaftalikSmaTrixKirilim,
    KirmiziMumHacim, Saat2123Utc, SaatlikAsiriTepki, VolatiliteKirilimK05,
)
from motor.strateji.kayit import tum_stratejiler


KOK = Path(__file__).resolve().parents[1]


def mum(kapanis, freq="1h", bas="2024-01-01", hacim=None, genlik=0.01):
    k = np.asarray(kapanis, dtype=float)
    idx = pd.date_range(bas, periods=len(k), freq=freq, tz="UTC", name="zaman")
    o = np.r_[k[0], k[:-1]]
    h = np.maximum(o, k) * (1 + genlik)
    d = np.minimum(o, k) * (1 - genlik)
    v = np.ones(len(k)) if hacim is None else np.asarray(hacim, dtype=float)
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": d, "kapanis": k, "hacim": v}, index=idx)


def girisleri(sig):
    return sig.loc[sig["yon"] != 0]


def test_asya_kutusu_ma_yonunde_kirilir_stop_ve_13_cikisi_var():
    df = mum(np.r_[np.linspace(90, 100, 96), np.full(16, 100.0), np.linspace(100, 110, 32)], "15min")
    sig = AsyaKutuKirilimMa50(tampon_atr=0.0).sinyaller(df)
    g = girisleri(sig)
    assert (g.yon == 1).any() and (g.stop < df.loc[g.index, "kapanis"]).all()
    assert (g.hedef > df.loc[g.index, "kapanis"]).all()
    assert sig.loc[sig.index.hour == 13, "cikis"].any()


def test_21_utc_girisi_iki_mum_tutulur():
    df = mum(np.linspace(100, 110, 80), "1h")
    sig = Saat2123Utc().sinyaller(df)
    g = girisleri(sig)
    assert len(g) >= 2 and set(g.index.hour) == {20}  # 20:00 kapanışı -> 21:00 açılış dolumu
    assert g.zaman_cikisi_mum.eq(2).all() and g.stop.notna().all()


def test_saatlik_asiri_hareketin_tersine_girer():
    k = np.full(90, 100.0)
    k[70:] = 101.0
    k[80:] = 120.0
    sig = SaatlikAsiriTepki(k=1.0).sinyaller(mum(k))
    assert sig.iloc[80].yon == -1 and sig.iloc[80].stop > k[80]


@pytest.mark.parametrize("sinif,n", [(AdaptiveTrend6s, 80), (DonchianAnsambl, 180), (HaftalikSmaTrixKirilim, 180)])
def test_trend_adaylari_yukseliste_long_ve_stop_uretir(sinif, n):
    x = np.linspace(0, 1.0, n)
    fiyat = 50 * np.exp(2 * x * x) if sinif is HaftalikSmaTrixKirilim else np.linspace(50, 200, n)
    df = mum(fiyat, "7D" if sinif is HaftalikSmaTrixKirilim else "6h")
    g = girisleri(sinif().sinyaller(df))
    assert len(g) > 0 and (g.yon == 1).all() and g.stop.notna().all()


def test_trend_adaylarinin_kendi_cikis_kurallari_tetiklenir():
    adaptif = AdaptiveTrend6s().sinyaller(mum(np.r_[np.linspace(50, 100, 60), np.linspace(100, 60, 40)], "6h"))
    assert adaptif["cikis_long"].any()

    donchian = DonchianAnsambl().sinyaller(mum(np.r_[np.linspace(50, 150, 130), np.linspace(150, 40, 50)], "1D"))
    assert donchian["cikis"].any()

    x = np.linspace(0, 1, 150)
    haftalik_fiyat = np.r_[50 * np.exp(2 * x * x), np.linspace(50 * np.e ** 2, 40, 30)]
    haftalik = HaftalikSmaTrixKirilim().sinyaller(mum(haftalik_fiyat, "7D"))
    assert haftalik["cikis"].any()


def test_kirmizi_yuksek_hacim_ertesi_gun_sinyali():
    df = mum(np.linspace(100, 90, 70), "1D", hacim=np.r_[np.ones(69), 3.0])
    df.iloc[-1, df.columns.get_loc("acilis")] = 95.0
    sig = KirmiziMumHacim().sinyaller(df)
    assert sig.iloc[-1].yon == 1 and sig.iloc[-1].zaman_cikisi_mum == 1 and pd.notna(sig.iloc[-1].stop)


def test_volatilite_kirilimi_onceki_aralik_ve_trend_filtresi():
    df = mum(np.linspace(100, 106, 5 * 24), "1h", genlik=0.001)
    son_gun = df.index.floor("D") == df.index[-1].floor("D")
    df.loc[son_gun, "kapanis"] += np.linspace(0, 8, son_gun.sum())
    df.loc[son_gun, "yuksek"] = df.loc[son_gun, ["acilis", "kapanis"]].max(axis=1) * 1.001
    sig = VolatiliteKirilimK05().sinyaller(df)
    g = girisleri(sig)
    assert len(g) > 0 and (g.yon == 1).all() and g.stop.notna().all()
    assert sig["cikis"].any()


def pf_veri(freq="1D", n=140):
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC", name="zaman")
    sonuc = {}
    for i, s in enumerate(("BTCUSDT", "ETHUSDT", "SOLUSDT")):
        yon = (1, -1, 0.25)[i]
        k = 100 * np.exp(yon * np.linspace(0, 0.5, n))
        df = mum(k, freq=freq)
        df.index = idx
        df["funding_orani"] = (-0.001, 0.0, 0.001)[i]
        sonuc[s] = df
    return sonuc


@pytest.mark.parametrize("sinif", [Funding1sDevam, FundingKesitCarry, Funding7gTercil])
def test_funding_kesitleri_dolar_notr_stoplu(sinif):
    veri = pf_veri("1h", 24 * 20) if sinif is Funding1sDevam else pf_veri("1D", 140)
    h, s = sinif().sinyaller(veri)
    dolu = h.dropna(how="all")
    acik = dolu[dolu.abs().sum(axis=1) > 0]
    assert len(acik) > 0
    assert np.allclose(acik.sum(axis=1), 0.0)
    assert s.loc[acik.index].notna().any(axis=1).all()
    if sinif is Funding1sDevam:
        ilk = h.index.get_loc(acik.index[0])
        assert h.iloc[ilk + 1].eq(0.0).all()


def test_funding_eksigi_sessizce_sifir_sayilmaz():
    veri = pf_veri()
    del veri["BTCUSDT"]["funding_orani"]
    with pytest.raises(ValueError, match="funding_orani eksik"):
        FundingKesitCarry().sinyaller(veri)


def test_fip_ust_long_alt_short_ve_stoplu():
    h, s = FipKesitsel().sinyaller(pf_veri())
    acik = h.dropna(how="all")
    assert len(acik) > 0 and np.allclose(acik.sum(axis=1), 0.0)
    son = acik.iloc[-1]
    assert (son > 0).sum() == 1 and (son < 0).sum() == 1
    assert s.loc[acik.index].notna().any(axis=1).all()


def test_kayit_ve_kodlama_csv_ilk_parti_tam():
    tek = tum_stratejiler()
    pf = tum_portfoy_stratejileri()
    assert sum(a.startswith("v3__") for a in tek) == 8
    assert sum(a.startswith("v3__") for a in pf) == 4
    yol = KOK / "stratejiler/v3_adaylar/kodlama_v3.csv"
    with yol.open(encoding="utf-8", newline="") as f:
        satirlar = list(csv.DictReader(f))
    assert len(satirlar) == 14
    assert {r["durum"] for r in satirlar} == {"kodlandi", "tekrar"}
    assert sum(r["durum"] == "kodlandi" for r in satirlar) == 12
