"""v3 adayları üçüncü parti: kural, kayıt ve envanter testleri."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.strateji import gostergeler as g
from motor.strateji.dis.v3_adaylar_3 import (
    EmaRsiHacimKesisim, LondraVolatiliteKirilim, MomentumSifirKesisim,
    PazartesiDip, Rsi14Ema200Iz, Rsi2Sma200Hacim, Rsi30HacimEma200,
    Rsi32Yon, SmaTrendRsiAtr, YarimFitil, ZSkorKarsit,
)
from motor.strateji.kayit import tum_stratejiler


KOK = Path(__file__).resolve().parents[1]


def mum(kapanis, freq="1D", bas="2023-01-01", hacim=None, genlik=0.002):
    k = np.asarray(kapanis, dtype=float)
    idx = pd.date_range(bas, periods=len(k), freq=freq, tz="UTC", name="zaman")
    o = np.r_[k[0], k[:-1]]
    h = np.maximum(o, k) * (1 + genlik)
    d = np.minimum(o, k) * (1 - genlik)
    v = np.ones(len(k)) if hacim is None else np.asarray(hacim, dtype=float)
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": d, "kapanis": k, "hacim": v}, index=idx)


def test_ema_kesisimi_trend_rsi_hacim_stop_hedef_ve_ters_cikis():
    fiyat = np.r_[np.linspace(120, 80, 80), np.linspace(80, 140, 55), np.linspace(140, 50, 80)]
    sig = EmaRsiHacimKesisim(min_hacim=0, rsi_ust=101, rsi_alt=-1, ema_trend=5).sinyaller(
        mum(fiyat, "15min", hacim=np.linspace(1.0, 3.0, len(fiyat)))
    )
    giris = sig[sig.yon != 0]
    assert (giris.yon == 1).any() and (giris.yon == -1).any()
    assert giris.stop.notna().all() and giris.hedef.notna().all()
    assert sig.cikis_long.any() and sig.cikis_short.any()


@pytest.mark.parametrize("freq", ["5min", "15min", "1h"])
def test_londra_araligi_ve_saatli_cikis_mum_suresinden_hesaplanir(freq):
    sure = pd.Timedelta(freq)
    n = int(pd.Timedelta(days=4) / sure)
    df = mum(np.full(n, 100.0), freq, "2024-01-01")
    hedef = pd.Timestamp("2024-01-02 09:00", tz="UTC")
    i = df.index.get_loc(hedef)
    df.iloc[i, df.columns.get_loc("kapanis")] = 110.0
    df.iloc[i, df.columns.get_loc("yuksek")] = 110.1
    sig = LondraVolatiliteKirilim().sinyaller(df)
    assert sig.iloc[i].yon == 1 and sig.iloc[i].stop < df.iloc[i].kapanis
    cik = sig.index[sig.cikis]
    kapanis = (cik + sure).tz_convert("Europe/London")
    saat = kapanis.normalize() + pd.Timedelta(hours=16)
    assert len(cik) >= 3 and (kapanis <= saat).all() and (kapanis + sure > saat).all()


def test_rsi32_yon_stop_hedef_ve_rsi_cikislari():
    df = mum(np.r_[np.linspace(100, 160, 80), np.linspace(160, 70, 80)], "1h")
    sig = Rsi32Yon().sinyaller(df)
    assert (sig.yon == 1).any() and (sig.yon == -1).any()
    assert sig.loc[sig.yon != 0, ["stop", "hedef"]].notna().all().all()
    assert sig.cikis_long.any() and sig.cikis_short.any()


def test_ust_saat_sma_trendi_rsi_ivmesini_onaylar():
    fiyat = np.r_[np.linspace(80, 120, 320), np.full(20, 120.0), 130.0, 131.0]
    sig = SmaTrendRsiAtr(rsi_fark=-100).sinyaller(mum(fiyat, "15min"))
    giris = sig[sig.yon == 1]
    assert len(giris) > 0 and giris.stop.notna().all() and giris.hedef.notna().all()


@pytest.mark.parametrize("freq", ["5min", "15min", "1h"])
def test_yarim_fitil_gun_sonu_cikisi_mum_suresine_gore(freq):
    sure = pd.Timedelta(freq)
    n = int(pd.Timedelta(days=3) / sure)
    df = mum(np.full(n, 100.0), freq, "2024-01-01")
    sig = YarimFitil().sinyaller(df)
    cik = sig.index[sig.cikis]
    kapanis = (cik + sure).tz_convert("America/New_York")
    hedef = kapanis.normalize() + pd.Timedelta(hours=16)
    assert len(cik) >= 2 and (kapanis <= hedef).all() and (kapanis + sure > hedef).all()


def test_yarim_fitil_oranlari_mum_uclarini_stop_hedef_yapar():
    df = mum(np.full(60, 100.0), "30min", "2024-01-02 14:30")
    i = df.index.get_loc(pd.Timestamp("2024-01-02 15:00", tz="UTC"))
    df.iloc[i] = [100.0, 110.0, 98.0, 104.0, 1.0]
    sig = YarimFitil().sinyaller(df)
    assert sig.iloc[i].yon == 1 and sig.iloc[i].stop == 98.0 and sig.iloc[i].hedef == 110.0


def test_momentum_sifir_long_flat_ve_atr_stop():
    fiyat = np.r_[np.linspace(100, 150, 50), np.linspace(150, 80, 35)]
    sig = MomentumSifirKesisim().sinyaller(mum(fiyat))
    assert (sig.yon == 1).any() and sig.loc[sig.yon == 1, "stop"].notna().all()
    assert sig.cikis_long.iloc[-1]


def test_pazartesi_ibs_sma_filtresi_ve_carsamba_cikisi():
    df = mum(np.linspace(200, 100, 240))
    i = max(i for i, t in enumerate(df.index) if t.day_of_week == 0 and i > 200)
    df.iloc[i, df.columns.get_loc("acilis")] = 102.0
    df.iloc[i, df.columns.get_loc("yuksek")] = 103.0
    df.iloc[i, df.columns.get_loc("dusuk")] = 95.0
    df.iloc[i, df.columns.get_loc("kapanis")] = 96.0
    sig = PazartesiDip().sinyaller(df)
    assert sig.iloc[i].yon == 1 and sig.iloc[i].stop == pytest.approx(86.4)
    assert sig.loc[sig.index.day_of_week == 2, "cikis"].all()


def test_rsi_geri_cekilme_siniflari_kart_formullerini_uygular():
    fiyat = np.r_[np.linspace(100, 220, 230), np.linspace(220, 175, 10), np.linspace(175, 230, 15)]
    hacim = np.r_[np.ones(len(fiyat)-25), np.full(25, 3.0)]
    df = mum(fiyat, hacim=hacim)

    a = Rsi14Ema200Iz().sinyaller(df)
    r14 = g.rsi(df.kapanis, 14)
    assert (a.yon.eq(1) == ((df.kapanis > g.ema(df.kapanis, 200)) & (r14 < 40)).fillna(False)).all()
    assert Rsi14Ema200Iz.cikis_ayarlari.geri_cekilme_yuzde == 0.10

    b = Rsi2Sma200Hacim().sinyaller(df)
    assert b.loc[b.yon == 1, "stop"].notna().all()
    assert (b.cikis_long == ((g.rsi(df.kapanis, 2) > 65) | (df.kapanis < g.sma(df.kapanis, 200))).fillna(False)).all()

    c = Rsi30HacimEma200().sinyaller(df)
    assert c.loc[c.yon == 1, "stop"].notna().all()
    assert c.cikis_long.any()


def test_getiri_zskoru_asiri_harekette_karsit_sinyal_ve_sifir_cikisi():
    fiyat = np.r_[np.linspace(100, 105, 40), 80.0, np.linspace(80, 82, 25), 110.0]
    sig = ZSkorKarsit().sinyaller(mum(fiyat))
    assert sig.iloc[40].yon == 1 and pd.notna(sig.iloc[40].stop)
    assert sig.iloc[-1].yon == -1 and pd.notna(sig.iloc[-1].stop)
    assert sig.cikis_long.any() and sig.cikis_short.any()


def test_ucuncu_parti_kayitlari_ve_csv_tam():
    yeni = {k for k, s in tum_stratejiler().items() if s.__module__.endswith("v3_adaylar_3")}
    assert len(yeni) == 11 and all(k.startswith("v3__") for k in yeni)
    with (KOK / "stratejiler/v3_adaylar/adaylar.csv").open(encoding="utf-8-sig", newline="") as f:
        # Parti 3 = TUR 1 kartlarının öncelik-3'ü (tur 1 = adaylar.csv ilk 72 satır; tur 2-3 sona kendi öncelikleriyle eklendi).
        adaylar = [r for r in list(csv.DictReader(f))[:72] if r["oncelik"] == "3"]
    with (KOK / "stratejiler/v3_adaylar/kodlama_v3.csv").open(encoding="utf-8", newline="") as f:
        kodlama = {r["kart_id"]: r for r in csv.DictReader(f)}
    assert len(adaylar) == 46 and {r["kart_id"] for r in adaylar} <= set(kodlama)
    uygun = []
    for a in adaylar:
        d = json.loads((KOK / "stratejiler/v3_adaylar/kartlar" / f"{a['kart_id']}.json").read_text())
        if d["veri_uygun"][0]: uygun.append(a["kart_id"])
        else: assert kodlama[a["kart_id"]]["durum"] == "veri_yok"
    durumlar = [kodlama[k]["durum"] for k in uygun]
    assert len(uygun) == 23
    assert {x: durumlar.count(x) for x in set(durumlar)} == {
        "kodlandi": 11, "tekrar": 5, "belirsiz": 5, "veri_yok": 2,
    }
