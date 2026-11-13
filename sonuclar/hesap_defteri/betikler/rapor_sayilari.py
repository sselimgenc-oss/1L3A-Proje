"""RAPOR.md sayıları ve listeleri (salt okur): ara/rapor_sayilari.json + ara/liste_*.csv"""
import csv, json, re
from collections import Counter
from pathlib import Path
csv.field_size_limit(10**9)
HD = Path(__file__).resolve().parents[1]; ARA = HD / "ara"
t = list(csv.DictReader(open(HD / "tekil_stratejiler.csv")))
h = list(csv.DictReader(open(HD / "ham_satirlar.csv")))
g0 = {r["kod_id"]: r for r in csv.DictReader(open(ARA / "G0_kod_akibet.csv"))}
kay = {}
for p in [HD / "kaynaklar.csv", ARA / "G10_ARSIV_kaynaklar.csv", ARA / "lider_ek_kaynaklar.csv"]:
    for r in csv.DictReader(open(p)): kay.setdefault(r["kaynak_id"], r)
def yaz(ad, rows, alan):
    with open(ARA / ad, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=alan, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
A = [x for x in t if x["durum"].startswith("A_")]
B = [x for x in t if x["durum"].startswith("B_")]
C = [x for x in t if x["durum"].startswith("C_")]
E = [x for x in t if x["durum"].startswith("E_")]
BEL = [x for x in t if x["durum"] == "BELIRSIZ"]
adil_degil = [x for x in B if x["adil_test"].split(" — ")[0] != "evet"]
yk = [x for x in t if x["yapisal_kapi"] == "evet"]
fark = [x for x in t if x["benzer_hedef"]]
for x in A + B + C:
    g = g0.get(x["tekil_id"][4:], {})
    x["v2_kapi"] = g.get("v2_nedenler", "")[:200]; x["stil"] = g.get("stil", "")
    x["neden"] = g.get("not", "")[:200] if x in C else ""
for x in C:
    if x["tekil_id"].startswith("KOD:"):
        g = g0[x["tekil_id"][4:]]; x["neden"] = (g.get("asama", "") + " " + g.get("kapi_ve_deger", "") + " " + g.get("not", ""))[:220]
    else:
        x["neden"] = x["not"]
yaz("liste_A.csv", A, ["tekil_id", "asama", "tf_evren", "islem_sayisi", "kanit_dosyasi", "not"])
yaz("liste_C.csv", C, ["tekil_id", "ad", "neden", "kod_dosyasi", "kanit_dosyasi"])
yaz("liste_E.csv", E, ["tekil_id", "ad", "aile", "kisa_mantik", "kaynaklar", "kanit_dosyasi", "not"])
yaz("liste_BELIRSIZ.csv", BEL, ["tekil_id", "ad", "neden_kodu", "kanit_dosyasi"])
yaz("liste_adil_olmayan.csv", adil_degil, ["tekil_id", "stil", "asama", "kapi_ve_deger", "yapisal_kapi", "adil_test", "tf_evren", "islem_sayisi"])
yaz("liste_yapisal_kapi.csv", yk, ["tekil_id", "stil", "kapi_ve_deger", "adil_test", "tf_evren", "islem_sayisi"])
yaz("liste_fark_test_edilmedi.csv", fark, ["tekil_id", "ad", "benzer_hedef", "kaynaklar", "not"])
s = {
 "kaynak_dosya": len(kay), "kaynak_birincil": sum(1 for v in kay.values() if v["tur"].startswith("birincil")),
 "kaynak_grup": dict(Counter(v["grup"] for v in kay.values())),
 "ham": len(h), "ham_grup": dict(Counter(r["grup"] for r in h)), "ham_eslesme": dict(Counter(r["eslesme"] for r in h)),
 "tekil": len(t), "tekil_kod": sum(1 for x in t if x["tekil_id"].startswith("KOD:")),
 "tekil_ayar": sum(1 for x in t if x["tekil_id"].startswith("AYAR:")),
 "tekil_kodsuz": sum(1 for x in t if x["tekil_id"].startswith("HAM:")),
 "durum": dict(Counter(x["durum"] for x in t)),
 "A_asama": dict(Counter(x["asama"] for x in A)), "B_asama": dict(Counter(x["asama"] for x in B)),
 "B_adil": dict(Counter(x["adil_test"].split(" — ")[0] for x in B)),
 "B_adil_evet": len(B) - len(adil_degil), "yapisal_kapi": len(yk),
 "fark_test_edilmedi": len(fark), "fark_dogrulanmamis": sum(1 for x in fark if "benzer_dogrulanmadi" in x["not"]),
 "E_kaynak": dict(Counter(x["kaynaklar"].split(";")[0] for x in E)),
 "D_neden": dict(Counter(re.split(r"[ (]", x["neden_kodu"])[0] for x in t if x["durum"].startswith("D_")).most_common(15)),
 "H_neden": dict(Counter(re.split(r"[ (]", x["neden_kodu"])[0] for x in t if x["durum"].startswith("H_")).most_common(12)),
 "F_neden": dict(Counter(re.split(r"[ (]", x["neden_kodu"])[0] for x in t if x["durum"].startswith("F_"))),
 "kod_kaynaksiz": sum(1 for x in t if x["tekil_id"].startswith("KOD:") and x["ham_sayisi"] == "0"),
}
(ARA / "rapor_sayilari.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
print(json.dumps(s, ensure_ascii=False, indent=1))
