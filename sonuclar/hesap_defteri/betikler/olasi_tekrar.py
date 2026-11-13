"""Kaynaklar arası OLASI tekrar tahmini (birleştirme YAPMAZ; yalnız rapor).
Kodlanmamış tekillerin (HAM:*) kaynak satırlarından dosya düzeyinde URL çıkarır (github blob/tree yolu, tradingview script id,
diğer sitelerde tam yol); aynı URL'yi paylaşan, FARKLI kaynak dosyadan gelen tekilleri listeler.
Kullanım: python betikler/olasi_tekrar.py [--adoring DIZIN] [--haiku DIZIN]"""
import csv, re, sys
from collections import defaultdict
from pathlib import Path
csv.field_size_limit(10**9)
HD = Path(__file__).resolve().parents[1]; KOK = HD.parents[1]
def arg(a):
    return Path(sys.argv[sys.argv.index(a) + 1]) if a in sys.argv else None
ADOR, HAIKU = arg("--adoring"), arg("--haiku")
kay = {}
for p in [HD / "kaynaklar.csv", HD / "ara" / "G10_ARSIV_kaynaklar.csv", HD / "ara" / "lider_ek_kaynaklar.csv"]:
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8")):
            kay.setdefault(r["kaynak_id"], r["yol"])
def yol_coz(y):
    if y.startswith("dal:claude/adoring-maxwell-q7t60g:") and ADOR:
        return ADOR / y.split(":", 2)[2]
    if y.startswith("dal:claude/haiku-strateji-arastirma:") and HAIKU:
        return HAIKU / y.split(":", 2)[2]
    return KOK / y
cache = {}
def satir(kid, no):
    p = yol_coz(kay.get(kid, ""))
    if p.suffix != ".csv" or not p.exists():
        return ""
    if p not in cache:
        cache[p] = list(csv.reader(open(p, encoding="utf-8-sig")))
    try:
        return " ".join(cache[p][int(no)])
    except Exception:
        return ""
URL = re.compile(r"https?://[^\s,;|\"'<>)\]]+")
def normal(u):
    u = u.lower().rstrip("/.").split("?")[0].split("#")[0]
    u = re.sub(r"^https?://(www\.|[a-z]{2}\.)?", "", u)
    if u.startswith("github.com/"):
        parca = u.split("/")
        if len(parca) < 5:      # repo kökü: dosya düzeyi değil
            return None
        u = "/".join(parca[:3] + parca[5:]) if parca[3] in ("blob", "tree") else u
    if "tradingview.com/script/" in u:
        m = re.search(r"script/([a-z0-9]+)", u)
        return "tv:" + m.group(1) if m else None
    if u.count("/") < 1 or len(u) < 15:
        return None
    return u
tekil = {r["tekil_id"]: r for r in csv.DictReader(open(HD / "tekil_stratejiler.csv", encoding="utf-8"))}
ham = list(csv.DictReader(open(HD / "ham_satirlar.csv", encoding="utf-8")))
url_tekil = defaultdict(set)
for h in ham:
    if not h["tekil_id"].startswith("HAM:"):
        continue
    metin = satir(h["kaynak_id"], h["kaynak_satir_no"]) if h["kaynak_satir_no"].isdigit() else ""
    for u in {normal(x) for x in URL.findall(metin)} - {None}:
        url_tekil[u].add((h["tekil_id"], h["kaynak_id"]))
gruplar = []
for u, s in url_tekil.items():
    tekiller = {t for t, _ in s}
    kaynaklar = {k for _, k in s}
    if len(tekiller) > 1 and len(kaynaklar) > 1:
        gruplar.append((u, sorted(tekiller), sorted(kaynaklar)))
# birleşik bileşenler (aynı tekil birden çok URL grubunda olabilir)
ebeveyn = {}
def bul(x):
    while ebeveyn.setdefault(x, x) != x:
        x = ebeveyn[x]
    return x
for _, ts, _ in gruplar:
    for t in ts[1:]:
        ebeveyn[bul(t)] = bul(ts[0])
bilesen = defaultdict(set)
for _, ts, _ in gruplar:
    for t in ts:
        bilesen[bul(t)].add(t)
with open(HD / "ara" / "olasi_tekrar.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["url", "tekil_sayisi", "tekiller", "kaynaklar", "adlar"])
    for u, ts, ks in sorted(gruplar, key=lambda g: -len(g[1])):
        w.writerow([u, len(ts), ";".join(ts), ";".join(ks), " || ".join(tekil[t]["ad"][:60] for t in ts[:6])])
fazla = sum(len(b) - 1 for b in bilesen.values())
print(f"URL grubu: {len(gruplar)}; birleşik bileşen: {len(bilesen)}; birleşirse azalacak tekil (üst sınır): {fazla}")
