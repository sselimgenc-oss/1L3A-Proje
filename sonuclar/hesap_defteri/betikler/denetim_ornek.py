"""Lider denetimi: bir grubun ham CSV'sinden tohumlu örnek çekip kaynak satırıyla yan yana basar (salt okur).
Kullanım: python betikler/denetim_ornek.py GRUP N TOHUM [--adoring DIZIN]"""
import csv, random, sys
from pathlib import Path
csv.field_size_limit(10**9)
HD = Path(__file__).resolve().parents[1]; KOK = HD.parents[1]
g, n, t = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ador = Path(sys.argv[sys.argv.index("--adoring") + 1]) if "--adoring" in sys.argv else None
kay = {r["kaynak_id"]: r["yol"] for r in csv.DictReader(open(HD / "kaynaklar.csv"))}
rows = list(csv.DictReader(open(HD / "ara" / f"{g}_ham.csv")))
random.seed(t)
cache = {}
for x in random.sample(rows, n):
    yol = kay.get(x["kaynak_id"], "?")
    p = (ador / yol.split(":", 1)[1].split(":", 1)[1]) if yol.startswith("dal:") and ador else KOK / yol
    src = ""
    if p.suffix == ".csv" and p.exists():
        if p not in cache:
            cache[p] = list(csv.reader(open(p, encoding="utf-8-sig")))
        try:
            src = " | ".join(c[:70] for c in cache[p][int(x["kaynak_satir_no"])][:8])
        except Exception as e:
            src = f"OKUNAMADI {e}"
    print(f"== {x['ham_id']}  {x['eslesme']} {x['hedef']}  {x['on_durum']} {x['neden_kodu']}")
    print(f"   AD : {x['kaynaktaki_ad'][:90]}")
    print(f"   SRC: {src[:400]}")
    print(f"   FARK/NEDEN: {(x['fark'] or x['neden_metni'])[:200]}")
    print(f"   KANIT: {x['kanit'][:150]}")
