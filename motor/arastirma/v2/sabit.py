"""v2 sabitleri — TEK KAYNAK (ON_KAYIT_V2 bölüm 1, 4). Başka v2 modülünde eşik/sayı sabiti YOKTUR (testler/test_v2_ham_eleme.py
kaynak taraması). Değerler koşudan önce yazılmış ön kayıttandır; sonuç görüldükten sonra değiştirilmez."""
from __future__ import annotations

import zlib
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[3]
CIKTI = KOK / "sonuclar" / "evren" / "v2"
HAVUZ_CSV = KOK / "stratejiler" / "havuz_v2.csv"
HAVUZ_MUHRU = CIKTI / "havuz_muhru.json"

# ---------------------------------------------------------------- 1. sabitler
HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")        # geliştirme: ... -> 2025-11-07 (dahil); bu tarih ve sonrası OKUNMAZ
DONEM = "2017_gelistirme"                                  # v1'in geliştirme dönemi etiketi (okuma `bit` = HOLDOUT_BAS ile kesilir)
TOHUM = 20261109
ASAMALAR = ("k2a", "k2b", "boot", "hk2", "hset")
K2_B1 = 500
K2_B2 = {"1d": 10000, "4h": 10000, "15m": 5000}
K2_GECIS_P = 0.02
BH_Q = 0.10
BOOT_BLOK_GUN = 20
BOOT_CEKIM = 2000
HOLDOUT_B_SET = 5000
HOLDOUT_B_STRATEJI = 2000
M_TABAN = 939
MALIYET_CARPANLARI = (1.0, 2.0)                           # ham koşu: ×1 ve ×2 (bölüm 3)

# 1.2 TradFi funding: DK_ sembollerinde LONG, tutulan her 8 saat (takvim süresi) için nominalin %0.01'i; SHORT'a gelir yazılmaz
FUNDING_LONG_8S_ORAN = 0.0001
FUNDING_PERIYOT_SAAT = 8.0
FUNDING_SUTUNU = "funding_long_8s_oran"
TABLO_V2_AD = "maliyet_tablosu_v2.csv"

# ---------------------------------------------------------------- 4. eleme kapıları
E1_PF_MIN = 1.2
E1_PORTFOY_SHARPE_MIN = 0.5
E2_MIN_ISLEM = 200
E2_MIN_ENSTRUMAN_GENEL = 10
E2_MIN_ENSTRUMAN_KRIPTO = 6
E2_PORTFOY_MIN_GUN = 1095
E2_PORTFOY_MIN_DENGELEME = 20
E4_SINIF_PAY_MIN = 0.15
E4_MIN_SINIF = 2
E5_MAKS_KILL = 0
GENEL_SINIFLAR = ("kripto", "hisse", "emtia")

# ---------------------------------------------------------------- teknik (v1 ile uyumlu; eşik değil)
GUN_SAAT = 24.0
SF_TABAN = 1e-4                  # v1 islem_ozet: stop oranı alt sınırı
SF_YEDEK = 0.05                  # v1 islem_ozet: R == 0 satırlarında hiç komşu yoksa
ONBELLEK_BOYUT = 4
SUREC_VARSAYILAN = 4


def satir_tohumu(strateji: str, tf: str, asama: str) -> int:
    """Satır tohumu = crc32(f"{strateji}|{tf}|{asama}") XOR TOHUM (bölüm 1)."""
    if asama not in ASAMALAR:
        raise ValueError(f"bilinmeyen aşama: {asama!r}")
    return zlib.crc32(f"{strateji}|{tf}|{asama}".encode()) ^ TOHUM


def evren_listesi(ad: str) -> tuple:
    """Beyan edilen evren: 'genel' = v1 EVREN_GENEL (35), 'kripto' = bunun 13 kripto üyesi (sıra korunur)."""
    from motor.arastirma import wf_evren as we
    if ad == "genel":
        return tuple(we.EVREN_GENEL)
    if ad == "kripto":
        return tuple(s for s in we.EVREN_GENEL if we.SINIF[s] == "kripto")
    raise ValueError(f"bilinmeyen evren: {ad!r}")


def sinif_of(sembol: str) -> str:
    from motor.arastirma import wf_evren as we
    return we.SINIF.get(sembol, "diger")
