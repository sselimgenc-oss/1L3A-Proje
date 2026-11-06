"""Ham strateji kartlarını doğrular (Aşama 0).

veri/kartlar_ham/<stil>/*.json dosyalarını okur; JSON geçerliliğini, zorunlu alanları
ve kodlanabilirlik puanını kontrol eder; özet istatistik basar.

Kullanım:  python araclar/kart_dogrula.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HAM = KOK / "veri" / "kartlar_ham"
ZORUNLU = ["kart_id", "ad", "stil", "kaynak", "long_giris", "kodlanabilirlik"]


def main() -> int:
    hatali_dosya, toplam, puanlar, eksik = [], 0, Counter(), Counter()
    stil_say = Counter()
    for stil_dir in sorted(p for p in HAM.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for f in sorted(stil_dir.glob("*.json")):
            try:
                kartlar = json.loads(f.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as e:
                hatali_dosya.append((f.relative_to(KOK), f"satır {e.lineno} sütun {e.colno}: {e.msg}"))
                continue
            if not isinstance(kartlar, list):
                hatali_dosya.append((f.relative_to(KOK), "kök bir dizi değil"))
                continue
            for k in kartlar:
                toplam += 1
                stil_say[stil_dir.name] += 1
                for alan in ZORUNLU:
                    if alan not in k:
                        eksik[alan] += 1
                p = (k.get("kodlanabilirlik") or {}).get("puan")
                puanlar[p if p in (0, 1, 2, 3) else "geçersiz"] += 1
            print(f"OK  {len(kartlar):3} kart  {f.relative_to(KOK)}")
    print("\n=== ÖZET ===")
    print(f"Toplam kart: {toplam}   stil: {dict(stil_say)}")
    print(f"Puan dağılımı: {dict(sorted(puanlar.items(), key=str))}")
    print(f"Eksik zorunlu alanlar: {dict(eksik) or 'yok'}")
    if hatali_dosya:
        print(f"\nGEÇERSİZ JSON ({len(hatali_dosya)}):")
        for f, m in hatali_dosya:
            print(f"  {f}: {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
