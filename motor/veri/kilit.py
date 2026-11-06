"""Kilitli dönem (DURUM.md karar 20): bu tarih ve sonrası veri kasada; yalnız final seçimde BİR kez açılır."""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
KILIT_BASLANGIC = pd.Timestamp("2025-11-01", tz="UTC")
KILIT_LOG = KOK / "sonuclar" / "kilit_acilis.jsonl"


def kilit_siniri(bitis, kilit_ac: bool, gerekce: str | None = None, sembol: str = "", ne: str = ""):
    """Okuma için etkin `bitis` (hariç). Kilit açıksa bitis aynen döner ve açılış kayda geçer."""
    if kilit_ac:
        if not isinstance(gerekce, str) or not gerekce.strip():
            raise ValueError("kilit_ac=True için boş olmayan `gerekce` zorunlu")
        kilit_acilisi_yaz(sembol, ne, gerekce)
        return bitis
    if bitis is None:
        return KILIT_BASLANGIC
    b = pd.Timestamp(bitis)
    b = b.tz_localize("UTC") if b.tzinfo is None else b.tz_convert("UTC")
    return min(b, KILIT_BASLANGIC)


def kilit_acilisi_yaz(sembol: str, ne: str, gerekce: str) -> None:
    yigin = [f"{Path(f.filename).name}:{f.lineno}:{f.name}"
             for f in traceback.extract_stack()[:-2]
             if "pytest" not in f.filename and "pluggy" not in f.filename][-4:]
    kayit = {"zaman": datetime.now(timezone.utc).isoformat(), "sembol": sembol, "veri": ne,
             "gerekce": gerekce, "yigin": yigin}
    KILIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(KILIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
