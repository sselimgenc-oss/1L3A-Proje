"""Çıkış modülleri. Motor bunları her mumun KAPANIŞINDA uygular; etki sonraki mumda başlar.

Saf fonksiyonlar (float); strateji hangisini istediğini CikisAyarlari ile seçer.
"""
from dataclasses import dataclass
from typing import Optional

import math


@dataclass(frozen=True)
class CikisAyarlari:
    atr_iz_suren_k: Optional[float] = None      # None: kapalı. Aksi halde stop = ekstrem -/+ k*ATR
    atr_periyot: int = 14
    zaman_cikisi_mum: Optional[int] = None      # N mum tutulduysa çık
    sabit_r_hedefi: Optional[float] = None      # hedef = giriş +/- R*risk (sinyalde hedef yoksa)
    basabas_r_esigi: Optional[float] = None     # örn. 1.0: kâr 1R'ye ulaşınca stop girişe çekilir


def r_hedef_fiyati(yon: int, giris: float, risk_birim: float, r: float) -> float:
    return giris + yon * r * risk_birim


def iz_suren_stop(yon: int, stop: float, ekstrem: float, atr: float, k: float) -> float:
    """ekstrem: girişten beri en yüksek (long) / en düşük (short) fiyat. Stop asla gevşemez."""
    if math.isnan(atr):
        return stop
    yeni = ekstrem - yon * k * atr
    return max(stop, yeni) if yon == 1 else min(stop, yeni)


def basabasa_cek(yon: int, stop: float, giris: float, ekstrem: float,
                 risk_birim: float, r_esik: float) -> float:
    if yon * (ekstrem - giris) >= r_esik * risk_birim:
        return max(stop, giris) if yon == 1 else min(stop, giris)
    return stop


def zaman_doldu(tutulan_mum: int, limit: Optional[int]) -> bool:
    return limit is not None and tutulan_mum >= limit
