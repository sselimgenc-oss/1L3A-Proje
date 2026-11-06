"""PDF -> metin dönüştürücü (Aşama 0).

scalp/, day trade/, swing/ klasörlerindeki PDF'leri sayfa işaretleriyle
veri/pdf_metin/<stil>/<ad>.txt dosyalarına yazar ve bir envanter (envanter.json) üretir.
Metni çok az olan sayfalar "taranmış (OCR gerekli)" olarak işaretlenir.

Kullanım:  python araclar/pdf_metne.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

KOK = Path(__file__).resolve().parent.parent
STILLER = {"scalp": "scalp", "day trade": "daytrade", "swing": "swing"}
CIKTI = KOK / "veri" / "pdf_metin"
AZ_METIN = 40  # bir sayfada bundan az karakter varsa "boş/taranmış" say


def kisa_ad(ad: str) -> str:
    ad = re.sub(r"\s*-\s*@eseckal", "", ad)
    ad = re.sub(r"[^\w\s\-]", "", ad, flags=re.UNICODE)
    return re.sub(r"\s+", "_", ad.strip())[:90]


def main() -> int:
    envanter = []
    for klasor, stil in STILLER.items():
        hedef = CIKTI / stil
        hedef.mkdir(parents=True, exist_ok=True)
        for pdf in sorted((KOK / klasor).glob("*.pdf")):
            try:
                doc = pymupdf.open(pdf)
            except Exception as e:  # bozuk PDF
                envanter.append({"stil": stil, "pdf": pdf.name, "hata": str(e)})
                continue
            parcalar, bos = [], 0
            for i, sayfa in enumerate(doc, start=1):
                t = sayfa.get_text("text").strip()
                if len(t) < AZ_METIN:
                    bos += 1
                parcalar.append(f"\n\n=== SAYFA {i} ===\n{t}")
            metin = "".join(parcalar)
            txt = hedef / f"{kisa_ad(pdf.stem)}.txt"
            txt.write_text(metin, encoding="utf-8")
            envanter.append({
                "stil": stil,
                "pdf": pdf.name,
                "txt": str(txt.relative_to(KOK)).replace("\\", "/"),
                "sayfa": doc.page_count,
                "karakter": len(metin),
                "bos_sayfa": bos,
                "ocr_gerekli": bos > doc.page_count * 0.5,
            })
            doc.close()
    (CIKTI / "envanter.json").write_text(
        json.dumps(envanter, ensure_ascii=False, indent=2), encoding="utf-8")
    for e in envanter:
        if "hata" in e:
            print(f"HATA  {e['stil']:8} {e['pdf']}: {e['hata']}")
        else:
            bayrak = " OCR!" if e["ocr_gerekli"] else ""
            print(f"{e['stil']:8} {e['sayfa']:4}s {e['karakter']:8}k bos={e['bos_sayfa']:3}{bayrak}  {e['txt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
