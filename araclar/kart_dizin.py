"""Ham kartlardan kompakt dizin (CSV) üretir — birleştirme ajanının girdisi.

Çıktı: veri/kart_dizini.csv  (bir satır = bir kart)
Kullanım:  python araclar/kart_dizin.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HAM = KOK / "veri" / "kartlar_ham"
CIKTI = KOK / "veri" / "kart_dizini.csv"


def yazar(dosya: str) -> str:
    """Dosya adından yazar/kitap kısa adı (eşleştirme için)."""
    ad = re.sub(r"_\d+_s(ayfa)?$|_\d+_say$|_\d+$", "", dosya)
    parca = ad.split("_-_")
    return (parca[1] if len(parca) > 1 else parca[0]).replace("_", " ")[:40]


def kisalt(v, n=160) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        v = " | ".join(str(x) for x in v)
    elif isinstance(v, dict):
        v = json.dumps(v, ensure_ascii=False)
    return str(v).replace("\n", " ")[:n]


def main() -> None:
    satirlar = []
    for stil_dir in sorted(p for p in HAM.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for f in sorted(stil_dir.glob("*.json")):
            for i, k in enumerate(json.loads(f.read_text(encoding="utf-8-sig"))):
                tf = k.get("zaman_dilimi") or {}
                satirlar.append({
                    "kart_id": k.get("kart_id"),
                    "klasor_stil": stil_dir.name,
                    "kart_stil": k.get("stil"),
                    "kaynak_dosya": f.stem,
                    "kaynak_yazar": yazar(f.stem),
                    "sira": i,
                    "ad": kisalt(k.get("ad"), 90),
                    "kategori": k.get("kategori"),
                    "rejim": k.get("piyasa_rejimi"),
                    "orijinal_piyasa": k.get("orijinal_piyasa"),
                    "tf_islem": tf.get("islem") if isinstance(tf, dict) else kisalt(tf, 30),
                    "tf_ust": tf.get("ust_filtre") if isinstance(tf, dict) else "",
                    "gostergeler": kisalt([g.get("ad") if isinstance(g, dict) else g for g in (k.get("gostergeler") or [])], 120),
                    "anahtar": kisalt(k.get("anahtar_kelimeler"), 120),
                    "long_giris": kisalt(k.get("long_giris"), 220),
                    "stop": kisalt(k.get("stop_loss"), 80),
                    "kar_al": kisalt(k.get("kar_al"), 80),
                    "puan": (k.get("kodlanabilirlik") or {}).get("puan"),
                    "iddia": kisalt(k.get("iddia_edilen_performans"), 100),
                })
    with CIKTI.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(satirlar[0].keys()))
        w.writeheader()
        w.writerows(satirlar)
    print(f"{len(satirlar)} kart -> {CIKTI.relative_to(KOK)} ({CIKTI.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
