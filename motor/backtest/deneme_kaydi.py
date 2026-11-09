"""Deneme kaydı: her walk-forward çağrısı bir satır JSONL ekler (çoklu test / veri kazıma takibi).

Satır: zaman, strateji, sembol, aralik, kombinasyon_sayisi, pencere_sayisi, toplam_kosu.
`toplam_kosu` = o çağrıdaki backtest koşusu sayısı (eğitim kombinasyonları + test koşuları).
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VARSAYILAN_YOL = Path(__file__).resolve().parents[2] / "sonuclar" / "deneme_kaydi.jsonl"


def kaydet(strateji: str, sembol: Optional[str], aralik: Optional[str], kombinasyon_sayisi: int,
           pencere_sayisi: int, toplam_kosu: int, yol: Optional[Path] = None, ek: Optional[dict] = None) -> dict:
    """ek: isteğe bağlı ek alanlar (ör. evren aşamasında donem / evren_imza); temel alanların üzerine yazamaz."""
    yol = Path(yol) if yol is not None else VARSAYILAN_YOL
    satir = {"zaman": datetime.now(timezone.utc).isoformat(), "strateji": strateji, "sembol": sembol,
             "aralik": aralik, "kombinasyon_sayisi": int(kombinasyon_sayisi),
             "pencere_sayisi": int(pencere_sayisi), "toplam_kosu": int(toplam_kosu)}
    if ek:
        cakisan = set(ek) & set(satir)
        if cakisan:
            raise ValueError(f"ek alanlar temel alanlarla çakışıyor: {sorted(cakisan)}")
        satir.update(ek)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    return satir


def oku(yol: Optional[Path] = None) -> list:
    yol = Path(yol) if yol is not None else VARSAYILAN_YOL
    if not yol.exists():
        return []
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def toplam_deneme(strateji_ad: Optional[str] = None, yol: Optional[Path] = None) -> int:
    """Kayıtlı toplam backtest koşusu sayısı (strateji_ad verilirse yalnız o strateji)."""
    return sum(k["toplam_kosu"] for k in oku(yol) if strateji_ad is None or k["strateji"] == strateji_ad)
