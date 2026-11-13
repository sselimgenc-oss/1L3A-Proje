"""Öz denetim örneği: tekil_stratejiler.csv'den tohum 20261113 ile 40 satır; her biri için kaynak satır metnini basar."""
import csv, random, sys
from pathlib import Path
csv.field_size_limit(10**9)
HD = Path(__file__).resolve().parents[1]; KOK = HD.parents[1]
ADOR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
kay = {}
for p in [HD / "kaynaklar.csv", HD / "ara/G10_ARSIV_kaynaklar.csv", HD / "ara/lider_ek_kaynaklar.csv"]:
    for r in csv.DictReader(open(p)): kay.setdefault(r["kaynak_id"], r["yol"])
t = list(csv.DictReader(open(HD / "tekil_stratejiler.csv")))
ham = {}
for r in csv.DictReader(open(HD / "ham_satirlar.csv")): ham.setdefault(r["tekil_id"], []).append(r)
random.seed(20261113)
orn = random.sample(t, 40)
cache = {}
def src(r):
    y = kay.get(r["kaynak_id"], "")
    p = (ADOR / y.split(":", 2)[2]) if y.startswith("dal:claude/adoring") and ADOR else KOK / y
    if p.suffix != ".csv" or not p.exists() or not r["kaynak_satir_no"].isdigit(): return f"[{y}]"
    if p not in cache: cache[p] = list(csv.reader(open(p, encoding="utf-8-sig")))
    try: return " | ".join(c[:60] for c in cache[p][int(r["kaynak_satir_no"])][:7])
    except Exception as e: return f"HATA {e}"
with open(HD / "ara/oz_denetim_ornek.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["sira", "tekil_id", "durum"])
    for i, x in enumerate(orn, 1): w.writerow([i, x["tekil_id"], x["durum"]])
for i, x in enumerate(orn, 1):
    print(f"#{i} {x['tekil_id']} | {x['durum']} {x['asama']} | {x['neden_kodu'][:80]} | ham={x['ham_sayisi']}")
    print(f"    ad={x['ad'][:70]} | kapi={x['kapi_ve_deger'][:70]} | adil={x['adil_test'][:50]}")
    print(f"    kanit={x['kanit_dosyasi'][:130]}")
    for r in ham.get(x["tekil_id"], [])[:2]:
        print(f"    HAM {r['ham_id']} {r['eslesme']} {r['hedef']} -> SRC: {src(r)[:230]}")
