"""v3 eleme sabitleri — TEK KAYNAK (ON_KAYIT_V3 bölüm 1, 1.2, 2, 3). Başka v3 modülünde eşik/sayı sabiti YOKTUR
(testler/test_v3_eleme.py kaynak taraması). Değerler koşudan önce yazılmış ön kayıttandır; sonuç görüldükten sonra değiştirilmez."""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

KOK = Path(__file__).resolve().parents[3]
CIKTI = KOK / "sonuclar" / "v3"
ON_KAYIT = CIKTI / "ON_KAYIT_V3.md"
DONDURMA = CIKTI / "dondurma.json"
SATIR_DIZINI = CIKTI / "satir"
ELEME_CSV = CIKTI / "eleme.csv"
RAPOR_MD = CIKTI / "ELEME_RAPORU.md"
KILIT_GUNLUGU = CIKTI / "kilit_acilis.jsonl"           # v3 okumaları v2'nin kilit günlüğüne yazmaz
MALIYET_V1 = KOK / "sonuclar" / "evren" / "maliyet_tablosu.csv"
MALIYET_V2 = KOK / "sonuclar" / "evren" / "v2" / "maliyet_tablosu_v2.csv"   # v1 + DK_ long funding (ON_KAYIT_V2 1.2)
KODLAMA_CSV = KOK / "stratejiler" / "v3_adaylar" / "kodlama_v3.csv"
FOMC_CSV = KOK / "veri" / "takvim" / "fomc.csv"

# ---------------------------------------------------------------- 2. sabitler
VERI_SONU = pd.Timestamp("2026-10-31 00:00", tz="UTC")     # okuma `bit` (hariç)
DONEM = "v3_eleme"                                          # wf_evren.DONEMLER'e çalışma zamanında eklenen dönem etiketi
KILIT_GEREKCE = "ON_KAYIT_V3: geçmiş veri yalnız eleme (v2 holdout dönemi dahil okunur; kanıt değildir)"
TOHUM = 20261111
ASAMALAR = ("k2", "rw")                                     # k2 = rastgele giriş, rw = rastgele ağırlık
B = 2000
CARPAN_ANA = 1.0
CARPAN_KAPI = 2.0
CARPAN_RAPOR = 3.0

# ---------------------------------------------------------------- 3. kapı eşikleri
V1_PF_MIN = 1.2
V2_MIN_ISLEM = 60
V2_MIN_ISLEM_KISA = 40                 # satır 7 ve 9
V4_P_MAX = 0.10
V5_MAKS_KILL = 0
P1_SHARPE_MIN = 0.5
P2_MIN_GUN = 1095
P2_MIN_DENGELEME = 20
P4_P_MAX = 0.10
P5_MAKS_KILL = 0

# ---------------------------------------------------------------- 1.2 geniş stop duyarlılığı (yalnız rapor)
GENIS_STOP_ATR = 20.0
STOP_PARAMETRESI = "atr_k"             # her satırın stop çarpanı parametresi (varsayilan_parametreler anahtarı)

# ---------------------------------------------------------------- teknik (eşik değil)
YILLIK_GUN = 365
EPS = 1e-12
K2_YENIDEN_CEKIM = 10                  # geçersiz stopta en çok 10 yeniden çekim (v2 ile aynı)
RW_BLOK = 50                           # rastgele-ağırlık: işçi başına simülasyon parçası (sonucu etkilemez)
SURUM = 1                              # satır sonucu şema sürümü


def satir_tohumu(strateji: str, asama: str) -> int:
    """Satır tohumu = crc32(f"{strateji}|{asama}") XOR TOHUM (bölüm 2)."""
    if asama not in ASAMALAR:
        raise ValueError(f"bilinmeyen aşama: {asama!r}")
    return zlib.crc32(f"{strateji}|{asama}".encode()) ^ TOHUM


# ---------------------------------------------------------------- bölüm 1: satırlar
@dataclass(frozen=True)
class Satir:
    no: int
    kart: str
    strateji: str
    tur: str                           # "portfoy" | "tek"
    tf: str
    evren: tuple
    bas: Optional[pd.Timestamp]        # eleme dönemi başlangıcı (None = tüm veri)
    min_islem: Optional[int]           # V2 eşiği (tek grafik)
    rastgele: Optional[str]            # "giris" | "agirlik" | None
    al_tut: bool                       # P6
    rapor_evren: tuple = ()            # yalnız rapor (satır 9: BTCUSDT)
    tam_donem_rapor: bool = False      # satır 7-8: tüm dönem yalnız rapor


def _kodlama_evreni(strateji: str, tf: str) -> tuple:
    """Satır 8: evren `kodlama_v3.csv` 'varsayimlar' sütununun başındaki 'BTC 1h' kalıbından (dondurmada csv sha256'sı kayıtlı)."""
    d = pd.read_csv(KODLAMA_CSV)
    s = d[d["strateji_ad"] == strateji]
    if len(s) != 1:
        raise ValueError(f"{KODLAMA_CSV.name}: {strateji} için tam 1 satır olmalı ({len(s)})")
    m = re.match(r"^\s*([A-Z0-9]+)\s+(\d+[mhd])\b", str(s.iloc[0]["varsayimlar"]))
    if not m:
        raise ValueError(f"{KODLAMA_CSV.name}: {strateji} evreni 'SEMBOL tf' kalıbıyla okunamadı")
    sembol, kaynak_tf = m.group(1), m.group(2)
    if kaynak_tf != tf:
        raise ValueError(f"{strateji}: kodlama tf {kaynak_tf} != satır tf {tf}")
    return (sembol if sembol.endswith("USDT") or sembol.startswith("DK_") else sembol + "USDT",)


@lru_cache(maxsize=1)
def satirlar() -> tuple:
    from motor.portfoy.stratejiler.ortak import HEPSI
    from motor.portfoy.stratejiler.v3 import V3_KRIPTO
    utc = lambda t: pd.Timestamp(t, tz="UTC")
    return (
        Satir(1, "donchian-ansambl-vol-hedef__zarattini", "pf__v3-donchian-ansambl", "portfoy", "1d", tuple(V3_KRIPTO),
              None, None, None, True),
        Satir(2, "funding-7g-haftalik-tercil__vine", "pf__v3-funding-7g-haftalik-tercil", "portfoy", "1d", tuple(V3_KRIPTO),
              None, None, "agirlik", False),
        Satir(3, "fip-kesitsel-momentum__baptoudur", "pf__v3-fip-kesitsel-momentum", "portfoy", "1d", tuple(V3_KRIPTO),
              None, None, "agirlik", False),
        Satir(4, "kripto-max-piyango-kesit__ozdamar", "pf__v3-kripto-max-piyango", "portfoy", "1d", tuple(V3_KRIPTO),
              None, None, "agirlik", False),
        Satir(5, "vol-yonetimli-long__moreira", "pf__v3-vol-yonetimli-long", "portfoy", "1d", tuple(HEPSI),
              None, None, None, True),
        Satir(6, "gunici-momentum-noise-alani__zarattini", "v3__gunici-momentum-noise-alani", "tek", "30m", ("DK_SPX",),
              None, V2_MIN_ISLEM, "giris", False),
        Satir(7, "btc-gecelik-max10-hafta-sonu__dujava", "v3__btc-gecelik-max10-hafta-sonu", "tek", "1h", ("BTCUSDT",),
              utc("2024-10-15"), V2_MIN_ISLEM_KISA, "giris", False, tam_donem_rapor=True),
        Satir(8, "cuma-15-est-tutma-saatlik__miralles", "v3__cuma-15-est-tutma", "tek", "1h",
              _kodlama_evreni("v3__cuma-15-est-tutma", "1h"), utc("2022-01-01"), V2_MIN_ISLEM, "giris", False,
              tam_donem_rapor=True),
        Satir(9, "pre-fomc-surunme__delphic", "v3__pre-fomc-surunme", "tek", "15m", ("DK_SPX",),
              None, V2_MIN_ISLEM_KISA, "giris", False, rapor_evren=("BTCUSDT",)),
    )


def satir_al(no: int) -> Satir:
    for s in satirlar():
        if s.no == no:
            return s
    raise KeyError(f"satır yok: {no}")
