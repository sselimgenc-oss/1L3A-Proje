"""Hesap defteri birleştirme (lider betiği, salt okur + yalnız sonuclar/hesap_defteri/ altına yazar).

Girdi : ara/kod_kaydi.csv, ara/G0_kod_akibet.csv, ara/G0_ayarlar.csv, ara/G*_ham.csv (G1..G10), kaynaklar.csv (+ ara/G10_ARSIV_kaynaklar.csv)
Çıktı : ham_satirlar.csv, tekil_stratejiler.csv, ara/birlestirme_sorunlari.csv, ara/sayilar.json

Tekilleştirme kuralları (isim değil kanıtlı eşleme; emin değilsek birleştirmeyiz):
- eslesme KOD / ESDEGER            -> tekil `KOD:<hedef>` (hedef kod kaydında olmalı)
- eslesme AYAR, ayar araştırma hattının aday kümesinde (G0_ayarlar.v1_aday_havuzunda=evet) -> `KOD:<hedef>` (parametre çeşidi)
- eslesme AYAR, ayar aday kümesinde değil (ör. ayarlar_d11j_ek / d12b_ek) -> ayrı tekil `AYAR:<hedef>:<ayar_id>` (C: kodlandı, koşulmadı)
- eslesme TEKRAR                   -> zinciri izle, hedef ham satırın tekiline bağlan
- eslesme BENZER / YOK             -> kendi tekili `HAM:<ham_id>` (BENZER: fark test edilmedi işareti)
Akıbet: KOD tekilleri G0'dan; diğerleri ham satırların on_durum'undan (öncelik F > G > H > D > BELIRSIZ > E).
"""
import csv, glob, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10**9)
KOK = Path(__file__).resolve().parents[3]
HD = KOK / "sonuclar" / "hesap_defteri"
ARA = HD / "ara"

def oku(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

kod = {r["ad"]: r for r in oku(ARA / "kod_kaydi.csv")}
g0 = {r["kod_id"]: r for r in oku(ARA / "G0_kod_akibet.csv")}
ayarlar = oku(ARA / "G0_ayarlar.csv")
ayar_havuz = {}
for a in ayarlar:
    ayar_havuz[(a["hedef_kod_id"], a["ayar_id"])] = a
kaynaklar = {r["kaynak_id"]: r for r in oku(HD / "kaynaklar.csv")}
for ek in ("G10_ARSIV_kaynaklar.csv", "lider_ek_kaynaklar.csv"):
    if (ARA / ek).exists():
        for r in oku(ARA / ek):
            kaynaklar.setdefault(r["kaynak_id"], r)
# v1 evren WF: strateji -> (tf sayısı, en büyük n_aday) — boş adil_test için
v1 = defaultdict(lambda: {"tf": set(), "n_aday": 0})
for r in oku(KOK / "sonuclar" / "evren" / "2017_gelistirme" / "wf_evren.csv"):
    v1[r["strateji"]]["tf"].add(r["tf"])
    try:
        v1[r["strateji"]]["n_aday"] = max(v1[r["strateji"]]["n_aday"], int(float(r["n_aday"] or 0)))
    except ValueError:
        pass

HAM_DOSYALAR = sorted(glob.glob(str(ARA / "G*_ham.csv")))
ALAN_HAM = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef",
            "ayar_id", "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]
ham = []
sorunlar = []
for p in HAM_DOSYALAR:
    grup = Path(p).name.replace("_ham.csv", "")
    for r in oku(p):
        r = {k: (r.get(k) or "").strip() for k in ALAN_HAM}
        r["grup"] = grup
        ham.append(r)
# lider düzeltmeleri (ajan dosyaları değişmez; düzeltme burada uygulanır)
duz = oku(ARA / "lider_duzeltmeleri.csv") if (ARA / "lider_duzeltmeleri.csv").exists() else []
_idx = {r["ham_id"]: r for r in ham}
for d in duz:
    r = _idx.get(d["ham_id"])
    if r is None:
        sorunlar.append({"tur": "duzeltme_ham_yok", "ham_id": d["ham_id"], "aciklama": d["alan"]})
        continue
    r[d["alan"]] = d["yeni"]
    r["not"] = (r["not"] + " | " if r["not"] else "") + "lider düzeltmesi: " + d["alan"]
for r in ham:
    if r["eslesme"].upper() == "AYAR" and ";" in r["ayar_id"]:
        r["ayar_id"] = r["ayar_id"].split(";")[0].strip()
    r["benzer_dogrulanmadi"] = "evet" if (r["eslesme"].upper() == "BENZER" and re.search(
        r"doğrulanmadı|dogrulanmadi|doğrulanmamış|dogrulanmamis|heuristik|anahtar kelime|önceki ajan kararı|kural farkı açılmadı",
        r["fark"] + " " + r["not"], re.I)) else ""
ham_by = {}
for r in ham:
    if r["ham_id"] in ham_by:
        sorunlar.append({"tur": "ham_id_tekrar", "ham_id": r["ham_id"], "aciklama": r["grup"]})
        continue
    ham_by[r["ham_id"]] = r

# portföy WF aday kümesi = baglama.BAGLAMA (csv:<satir>) + varsayılan + ızgara (motor/arastirma/wf_portfoy.py::aday_listesi)
sys.path.insert(0, str(KOK))
from motor.portfoy.stratejiler.baglama import BAGLAMA  # noqa: E402
BAGLAMA_SET = {(b["sinif"], int(b["satir"])) for b in BAGLAMA}

def baglama_mi(hedef, ayar_id):
    m = re.search(r"(?:baglama|csv)\w*[:=]\s*satir\s*=?\s*(\d+)|csv:(\d+)", ayar_id)
    if not m:
        return False
    n = int(m.group(1) or m.group(2))
    return (hedef, n) in BAGLAMA_SET

def ayar_havuzda(hedef, ayar_id):
    a = ayar_havuz.get((hedef, ayar_id))
    if a is None:
        # bazı gruplar ayar_id'yi önek olmadan yazmış olabilir: sonek eşleşmesi
        aday = [v for (h, i), v in ayar_havuz.items() if h == hedef and (i.endswith(ayar_id) or ayar_id.endswith(i))]
        a = aday[0] if len(aday) == 1 else None
    return a

# --- 1. aşama: doğrudan tekil ---
dogrudan = {}
for r in ham:
    e = r["eslesme"].upper()
    h = r["hedef"]
    if e in ("KOD", "ESDEGER"):
        if h in kod:
            dogrudan[r["ham_id"]] = f"KOD:{h}"
        else:
            sorunlar.append({"tur": "hedef_kodda_yok", "ham_id": r["ham_id"], "aciklama": f"{e} -> {h}"})
            dogrudan[r["ham_id"]] = f"HAM:{r['ham_id']}"
    elif e == "AYAR":
        a = ayar_havuzda(h, r["ayar_id"])
        if h in kod and a is None and baglama_mi(h, r["ayar_id"]):
            dogrudan[r["ham_id"]] = f"KOD:{h}"
            r["not"] = (r["not"] + " | " if r["not"] else "") + "portföy BAGLAMA ayarı (WF aday kümesinde)"
            continue
        if h not in kod:
            sorunlar.append({"tur": "ayar_hedefi_kodda_yok", "ham_id": r["ham_id"], "aciklama": f"{h} {r['ayar_id']}"})
            dogrudan[r["ham_id"]] = f"HAM:{r['ham_id']}"
        elif a is None:
            sorunlar.append({"tur": "ayar_G0_listesinde_yok", "ham_id": r["ham_id"], "aciklama": f"{h} {r['ayar_id']}"})
            dogrudan[r["ham_id"]] = f"AYAR:{h}:{r['ayar_id']}"
        elif a.get("v1_aday_havuzunda", "").lower().startswith("evet"):
            dogrudan[r["ham_id"]] = f"KOD:{h}"
        else:
            dogrudan[r["ham_id"]] = f"AYAR:{h}:{a['ayar_id']}"
    elif e == "TEKRAR":
        pass
    else:
        dogrudan[r["ham_id"]] = f"HAM:{r['ham_id']}"

def coz(hid, yol=()):
    if hid in dogrudan:
        return dogrudan[hid]
    r = ham_by.get(hid)
    if r is None:
        return None
    if hid in yol:
        sorunlar.append({"tur": "tekrar_dongusu", "ham_id": hid, "aciklama": "->".join(yol)})
        return f"HAM:{hid}"
    hedef = r["hedef"]
    if hedef not in ham_by:
        sorunlar.append({"tur": "tekrar_hedefi_yok", "ham_id": hid, "aciklama": hedef})
        dogrudan[hid] = f"HAM:{hid}"
        return dogrudan[hid]
    t = coz(hedef, yol + (hid,))
    dogrudan[hid] = t
    return t

for r in ham:
    r["tekil_id"] = coz(r["ham_id"]) or f"HAM:{r['ham_id']}"

# --- 2. tekil tablo ---
uyeler = defaultdict(list)
for r in ham:
    uyeler[r["tekil_id"]].append(r)
for k in kod:
    uyeler.setdefault(f"KOD:{k}", [])

ONCELIK = ["F_YASAK_TIP", "G_ML", "H_BIZIM_EVRENDE_UYGULANAMAZ", "D_KODLANMADI_NEDENLI", "BELIRSIZ", "E_KODLANMADI_NEDENSIZ"]

def aile_sec(rs):
    c = Counter(x["aile"] for x in rs if x["aile"])
    return c.most_common(1)[0][0] if c else ""

def kisalt(s, n=300):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"

def adil_normal(etiket):
    p = [x for x in etiket.split(";") if x]
    if len(p) > 1 and "evet" in p:
        p.remove("evet")
    return ";".join(p)

def adil_turet(k, g):
    """B için adil_test: G0 önerisi varsa o; yoksa v1 evren WF'den (TF sayısı, ayar adayı sayısı) türetilir."""
    if not (g.get("durum_onerisi") or "").startswith("B_"):
        return ""
    if g.get("adil_test_onerisi"):
        return (adil_normal(g["adil_test_onerisi"]) + (" — " + g["adil_test_gerekce"] if g.get("adil_test_gerekce") else "")).strip()
    v = v1.get(k)
    if not v or not v["tf"]:
        if g.get("v2_tf"):
            et = ["yalniz_tek_TF"] + (["yalniz_varsayilan_ayar"] if g.get("v2_ayar_kaynagi") != "izgara" else [])
            return ";".join(et) + f" — lider türetmesi: yalnız v2 elemesinde tek TF ({g['v2_tf']}), sabit ayar ({g.get('v2_ayar_kaynagi') or '?'}); v1 WF yok"
        if g.get("v3_eleme"):
            return f"yalniz_tek_TF;yalniz_varsayilan_ayar — lider türetmesi: yalnız v3 elemesi (ön kayıtlı tek ayar, tek TF: {g.get('tf_evren', '')[:60]})"
        return "BELIRSIZ — adil test bilgisi türetilemedi"
    et = []
    if len(v["tf"]) == 1:
        et.append("yalniz_tek_TF")
    if v["n_aday"] <= 1:
        et.append("yalniz_varsayilan_ayar")
    gerekce = (f"lider türetmesi: v1 evren WF (35 enstrüman, 2017→2025, walk-forward) {len(v['tf'])} TF "
               f"({','.join(sorted(v['tf']))}), {v['n_aday']} ayar adayı (varsayılan+kart/dış+ızgara)")
    return (";".join(et) if et else "evet") + " — " + gerekce

tekil = []
for tid, rs in sorted(uyeler.items()):
    kaynak_set = sorted({x["kaynak_id"] for x in rs})
    satir = {"tekil_id": tid, "ham_sayisi": len(rs), "kaynak_sayisi": len(kaynak_set),
             "kaynaklar": ";".join(kaynak_set[:20]) + (";…" if len(kaynak_set) > 20 else ""),
             "aile": aile_sec(rs), "kisa_mantik": kisalt(next((x["kisa_mantik"] for x in rs if x["kisa_mantik"]), ""), 200)}
    if tid.startswith("KOD:"):
        k = tid[4:]
        g = g0.get(k, {})
        satir.update({
            "ad": k, "durum": g.get("durum_onerisi", "BELIRSIZ") or "BELIRSIZ", "asama": g.get("asama", ""),
            "tf_evren": g.get("tf_evren", ""), "kapi_ve_deger": g.get("kapi_ve_deger", ""),
            "yapisal_kapi": g.get("yapisal_kapi", ""),
            "adil_test": adil_turet(k, g),
            "islem_sayisi": g.get("islem_sayisi", ""),
            "kod_dosyasi": g.get("kod_dosyasi") or f"{kod[k]['dosya']}:{kod[k]['sinif']}:{kod[k]['satir']}",
            "kanit_dosyasi": g.get("kanit", ""), "neden_kodu": "",
        })
        if not g:
            sorunlar.append({"tur": "G0_satiri_yok", "ham_id": "", "aciklama": k})
        notlar = []
        if not rs:
            notlar.append("kaynak ham satırı bağlanmadı (kod var, getirilen kaynaklarda eşleşen satır bulunamadı)")
        esd = sum(1 for x in rs if x["eslesme"].upper() == "ESDEGER")
        if esd:
            notlar.append(f"{esd} ham satır ESDEGER (koddan doğrulanmış aynı mantık) olarak bağlı")
        satir["not"] = "; ".join(notlar)
    elif tid.startswith("AYAR:"):
        _, h, aid = tid.split(":", 2)
        a = ayar_havuzda(h, aid) or {}
        satir.update({
            "ad": f"{h} [ayar {aid}]", "durum": "C_KODLANDI_KOSULMADI" if not a.get("kosuldu_mu", "").lower().startswith("evet") else "BELIRSIZ",
            "asama": "", "tf_evren": "", "kapi_ve_deger": "", "yapisal_kapi": "", "adil_test": "", "islem_sayisi": "",
            "kod_dosyasi": f"{a.get('ayar_dosyasi', '')} -> {kod[h]['dosya']}:{kod[h]['sinif']}" if h in kod else a.get("ayar_dosyasi", ""),
            "kanit_dosyasi": a.get("ayar_dosyasi", "") + (" ; " + a.get("not", "") if a.get("not") else ""),
            "neden_kodu": "ayar_aday_kumesinde_degil",
            "not": "ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi)",
        })
    else:
        durumlar = [x["on_durum"] for x in rs if x["on_durum"] and x["on_durum"] not in ("KOD", "TEKRAR")]
        durum = next((d for d in ONCELIK if d in durumlar), "BELIRSIZ")
        temsil = next((x for x in rs if x["on_durum"] == durum), rs[0])
        benzer = [x for x in rs if x["eslesme"].upper() == "BENZER"]
        notlar = []
        if any(x["benzer_dogrulanmadi"] for x in benzer):
            notlar.append("benzer_dogrulanmadi (eşleme kaynak/önceki ajan kararı; kodla karşılaştırılmadı)")
        if benzer:
            notlar.append("fark_test_edilmedi: " + kisalt("; ".join(sorted({f"{x['hedef']} ({x['fark']})" for x in benzer})), 300))
        if temsil["not"]:
            notlar.append(kisalt(temsil["not"], 200))
        satir.update({
            "ad": kisalt(temsil["kaynaktaki_ad"], 120), "durum": durum, "asama": "", "tf_evren": "",
            "kapi_ve_deger": "", "yapisal_kapi": "", "adil_test": "", "islem_sayisi": "", "kod_dosyasi": "",
            "kanit_dosyasi": kisalt(" ; ".join(sorted({x["kanit"] for x in rs if x["kanit"]})), 400),
            "neden_kodu": temsil["neden_kodu"] + (f" ({kisalt(temsil['neden_metni'], 160)})" if temsil["neden_metni"] else ""),
            "not": " | ".join(notlar),
        })
        satir["benzer_hedef"] = ";".join(sorted({x["hedef"] for x in benzer}))
    satir.setdefault("benzer_hedef", "")
    tekil.append(satir)

ALAN_TEKIL = ["tekil_id", "ad", "aile", "kisa_mantik", "kaynak_sayisi", "ham_sayisi", "durum", "asama", "tf_evren",
              "kapi_ve_deger", "yapisal_kapi", "adil_test", "islem_sayisi", "kod_dosyasi", "kanit_dosyasi", "neden_kodu",
              "benzer_hedef", "kaynaklar", "not"]
with open(HD / "tekil_stratejiler.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=ALAN_TEKIL, extrasaction="ignore"); w.writeheader(); w.writerows(tekil)
ALAN_CIKTI_HAM = ["ham_id", "kaynak_id", "kaynaktaki_ad", "kaynak_satir_no", "tekil_id", "grup", "eslesme", "hedef",
                  "on_durum", "neden_kodu", "benzer_dogrulanmadi", "kanit"]
with open(HD / "ham_satirlar.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=ALAN_CIKTI_HAM, extrasaction="ignore"); w.writeheader(); w.writerows(ham)
with open(ARA / "birlestirme_sorunlari.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["tur", "ham_id", "aciklama"]); w.writeheader(); w.writerows(sorunlar)

# --- 3. sayılar ---
s = {
    "kaynak_dosya": len(kaynaklar),
    "kaynak_dosya_birincil": sum(1 for v in kaynaklar.values() if v.get("tur", "").startswith("birincil")),
    "ham_satir": len(ham), "ham_grup": dict(Counter(r["grup"] for r in ham)),
    "ham_eslesme": dict(Counter(r["eslesme"].upper() for r in ham)),
    "tekil": len(tekil), "tekil_tur": dict(Counter(t["tekil_id"].split(":")[0] for t in tekil)),
    "tekil_durum": dict(Counter(t["durum"] for t in tekil)),
    "kod_durum": dict(Counter(t["durum"] for t in tekil if t["tekil_id"].startswith("KOD:"))),
    "yapisal_kapi_evet": sum(1 for t in tekil if t["yapisal_kapi"] == "evet"),
    "fark_test_edilmedi": sum(1 for t in tekil if t.get("benzer_hedef")),
    "fark_test_edilmedi_dogrulanmamis": sum(1 for t in tekil if "benzer_dogrulanmadi" in t.get("not", "")),
    "B_adil": dict(Counter(t["adil_test"].split(" — ")[0] for t in tekil if t["durum"].startswith("B_"))),
    "kod_kaynaksiz": sum(1 for t in tekil if t["tekil_id"].startswith("KOD:") and t["ham_sayisi"] == 0),
    "sorun": dict(Counter(x["tur"] for x in sorunlar)),
}
(ARA / "sayilar.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(s, ensure_ascii=False, indent=1))
