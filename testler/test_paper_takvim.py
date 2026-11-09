"""Seans takvimi: hisse hafta sonu/tatil yanlış bayat uyarısı vermesin; kripto 7/24."""
from datetime import date

import pandas as pd

from motor.canli import paper_takvim as tk

U = lambda s: pd.Timestamp(s, tz="UTC")     # noqa: E731


def test_nyse_tatilleri_2026():
    t = tk.nyse_tatilleri(2026)
    assert date(2026, 11, 26) in t and date(2026, 4, 3) in t and date(2026, 7, 3) in t and date(2026, 12, 25) in t
    assert date(2026, 11, 27) not in t and tk.erken_kapanis(date(2026, 11, 27))


def test_hisse_hafta_sonu_bayat_degil_ama_hafta_ici_bayat():
    esik = 2 * 240 + 10
    # Cuma son 4h mum (kapanış Cuma 17:00 NY) -> Pazar öğlen: seans dakikası 0
    dk, bayat = tk.bayatlik("DK_NVDA", "4h", U("2026-11-06 18:00"), U("2026-11-08 12:00"), esik)
    assert dk == 0 and not bayat
    # Salı seans içinde hâlâ yeni mum yok (Pazartesi + Salı seansı = 630 dk > eşik) -> bayat
    dk, bayat = tk.bayatlik("DK_NVDA", "4h", U("2026-11-06 18:00"), U("2026-11-10 18:30"), esik)
    assert bayat and dk > esik


def test_tatilde_bayat_degil():
    # Şükran Günü (26 Kasım 2026) kapalı: Çarşamba kapanıştan Cuma açılışına kadar seans dakikası ~ 0
    dk = tk.acik_dakika("DK_AAPL", U("2026-11-25 21:00"), U("2026-11-27 14:00"))
    assert dk == 0


def test_kripto_duvar_saati_ve_negatif_olmaz():
    dk, bayat = tk.bayatlik("ETHUSDT", "30m", U("2026-11-06 18:00"), U("2026-11-06 20:00"), 70)
    assert dk == 90 and bayat
    dk, bayat = tk.bayatlik("ETHUSDT", "30m", U("2026-11-06 18:00"), U("2026-11-06 18:10"), 70)    # kapanmamış mum
    assert dk == 0 and not bayat


def test_seans_maskesi_hisse_ve_emtia():
    idx = pd.date_range("2026-11-06 12:00", "2026-11-09 22:00", freq="30min", tz="UTC")
    m = tk.seans_maskesi("DK_NVDA", idx)
    saat = idx[m]
    assert saat.min().strftime("%H:%M") == "14:30" and saat.dayofweek.max() <= 4        # kış saati: 09:30 NY = 14:30 UTC
    assert not m[(idx.dayofweek >= 5)].any()
    e = tk.seans_maskesi("DK_XAU", idx)
    assert not e[(idx.dayofweek == 5)].any() and e[(idx.dayofweek == 0) & (idx.hour == 12)].all()
    assert tk.seans_maskesi("BTCUSDT", idx).all()


def test_tur():
    assert tk.tur("ETHUSDT") == "kripto" and tk.tur("DK_TSLA") == "hisse" and tk.tur("DK_WTI") == "emtia"
