"""v3 veri okuma: v1 yükleyicisi (`wf_evren._veri`, `wf_evren_portfoy.veri_yukle`) çalışma zamanında eklenen v3 dönemiyle
çağrılır (dosyalar DEĞİŞTİRİLMEZ; v2 yeniden üretilebilir kalır). Dönem: en eski veri -> VERI_SONU (hariç); kilit gerekçeyle açılır,
açılış kaydı v2 günlüğüne değil `sonuclar/v3/kilit_acilis.jsonl`'a yazılır."""
from __future__ import annotations

import os

import pandas as pd

from motor.arastirma import wf_evren as we
from motor.arastirma.v3 import sabit
from motor.veri import kilit

_ORJ_GEREKCE = we.donem_gerekce


def _gerekce(donem: str):
    return sabit.KILIT_GEREKCE if donem == sabit.DONEM else _ORJ_GEREKCE(donem)


def hazirla(veri_dizini=None) -> None:
    """v3 dönemini kaydeder ve etkinleştirir (süreç başına; fork edilen işçilere miras kalır)."""
    we.DONEMLER[sabit.DONEM] = {"bas": None, "bit": sabit.VERI_SONU, "kilit_ac": True}
    we.donem_gerekce = _gerekce
    os.environ.setdefault(kilit.KILIT_LOG_ORTAM, str(sabit.KILIT_GUNLUGU))
    we.veri_ayarla(veri_dizini, sabit.DONEM)


def oku(sembol: str, tf: str) -> tuple:
    """(mumlar, funding) — dönem sınırı okumada uygulanır; VERI_SONU ve sonrası hiçbir satır çıkmaz (kesin hata)."""
    mumlar, fund = we._veri(sembol, tf)
    sinir_kontrol(sembol, tf, mumlar, fund)
    return mumlar, fund


def sinir_kontrol(sembol: str, tf: str, mumlar, fund) -> None:
    for ad, df in (("mum", mumlar), ("funding", fund)):
        if df is not None and len(df) and pd.Timestamp(df.index.max()) >= sabit.VERI_SONU:
            raise RuntimeError(f"{sembol} {tf}: {ad} verisi VERI_SONU ({sabit.VERI_SONU}) ve sonrasına uzanıyor")


def pf_oku(evren: tuple) -> tuple:
    """(veriler, fundingler, dışarıda) — portföy yükleyicisi (1d)."""
    from motor.arastirma import wf_evren_portfoy as wep
    v, f, dis = wep.veri_yukle(tuple(evren), "1d")
    for s, df in v.items():
        sinir_kontrol(s, "1d", df, f.get(s))
    return v, f, dis
