#!/usr/bin/env python3
"""G2_DIS_ESKI hesap defteri betiği.

Kaynaklar (kaynaklar.csv, grup G2_DIS_ESKI):
  D001 stratejiler/dis_envanter.csv (431)      D002 stratejiler/portfoy_adaylari.csv (71)
  D050 arsiv/strateji-sg/tv_eleme_dali/ham/meta.json (164)   D051 .../meta3.json (92)
Eşleme/karar dosyaları (satır üretmez, kanıt olarak okunur): dis_kodlanacak.csv (D003), kodlama_2026-11-07_a/b/pf.csv
(D004/D005), dis_ayarlari/*.json (D006-D049), kod_kaydi.csv, motor/strateji/dis/*.py sınıf docstring'leri,
motor/portfoy/stratejiler/baglama.py + ek2.py (BAGLAMA), github_g1_freqtrade.csv (ek kanıt).

Çıktı: sonuclar/hesap_defteri/ara/G2_DIS_ESKI_ham.csv (+ elle kararlar: ara/G2_DIS_ESKI_elle_kararlar.csv, burada
okunur ve üstüne yazılır). Test KOŞMAZ, strateji kodu yazmaz/değiştirmez; yalnız okur.
Çalıştırma: python3 -I sonuclar/hesap_defteri/betikler/g2_dis_eski.py
"""
import ast
import csv
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARA = ROOT / "sonuclar/hesap_defteri/ara"
CIKTI = ARA / "G2_DIS_ESKI_ham.csv"
ELLE = ARA / "G2_DIS_ESKI_elle_kararlar.csv"

SUTUNLAR = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef", "ayar_id",
            "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]
ELLE_SUTUN = ["ham_id", "eslesme", "hedef", "ayar_id", "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit",
              "not", "gerekce"]

ENV_DOSYA = "stratejiler/dis_envanter.csv"
PF_DOSYA = "stratejiler/portfoy_adaylari.csv"
G1_DOSYA = "stratejiler/ek_kaynaklar/github_g1_freqtrade.csv"
UYARILAR = []


def uyar(m):
    UYARILAR.append(m)


def kes(s, n):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def oku_csv(yol):
    """[(satir_dict, baslangic_satiri)] — satır numarası dosyadaki fiziksel satır (başlık = 1)."""
    out = []
    with open(yol, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        baslik = next(rd)
        onceki = rd.line_num
        for row in rd:
            out.append((dict(zip(baslik, row)), onceki + 1))
            onceki = rd.line_num
    return out


def nz(s):
    return re.sub(r"[^0-9a-zçğıöşü]+", "", s.lower())


# ------------------------------------------------------------------ yükleme
env = oku_csv(ROOT / ENV_DOSYA)
pf = oku_csv(ROOT / PF_DOSYA)
kodlanacak = {x["ad"]: (ln, x) for x, ln in oku_csv(ROOT / "stratejiler/dis_kodlanacak.csv")}
kodlanacak_dosya = {x["dosya"]: (ln, x) for x, ln in oku_csv(ROOT / "stratejiler/dis_kodlanacak.csv")}
kod_a = {int(x["satir_indeksi"]): (x, ln) for x, ln in oku_csv(ROOT / "stratejiler/kodlama_2026-11-07_a.csv")}
kod_b = {int(x["satir_indeksi_veya_madde_no"]): (x, ln) for x, ln in oku_csv(ROOT / "stratejiler/kodlama_2026-11-07_b.csv")
         if x["kaynak_dosya"] == "dis_envanter"}
kod_pf = {int(x["satir_indeksi"]): (x, ln) for x, ln in oku_csv(ROOT / "stratejiler/kodlama_2026-11-07_pf.csv")}
kod_kaydi = {x["ad"]: x for x, _ in oku_csv(ARA / "kod_kaydi.csv")}
g1 = defaultdict(list)
for x, ln in oku_csv(ROOT / G1_DOSYA):
    g1[x["ad"]].append((x, ln))

# kod sınıfı docstring'leri
sinif_doc = {}
_dosya_ast = {}
for ad, k in kod_kaydi.items():
    f = k["dosya"]
    if f not in _dosya_ast:
        _dosya_ast[f] = ast.parse((ROOT / f).read_text(encoding="utf-8"))
    for n in _dosya_ast[f].body:
        if isinstance(n, ast.ClassDef) and n.name == k["sinif"]:
            sinif_doc[ad] = ast.get_docstring(n) or ""


def sinif_kanit(ad):
    k = kod_kaydi[ad]
    return f"{k['dosya']}:{k['satir']}"


# dis_ayarlari
ay_dosya = defaultdict(list)   # dis_id -> [(dosya_adi, kayit)]
ay_kayit = []
for f in sorted(glob.glob(str(ROOT / "stratejiler/dis_ayarlari/*.json"))):
    ad = os.path.basename(f)[:-5]
    for e in json.load(open(f, encoding="utf-8")):
        ay_dosya[e["dis_id"]].append((ad, e))
        ay_kayit.append((ad, e))


def env_anahtar(x):
    if x["kaynak"] in ("tv", "freqtrade"):
        return x["kaynak"] + ":" + os.path.basename(x["dosya"]).rsplit(".", 1)[0]
    if x["kaynak"] == "kural":
        return "kural:kurallar:" + x["ad"]
    return x["kaynak"] + ":" + x["kaynak"] + ":" + x["ad"]


def ay_bul(x, sinif):
    """Satırın ayar kaydı: önce doğrudan dis_id, sonra 'Birleşik ayar' notunda geçen dis_id. -> (dosya_adi, kayit, birlesik)"""
    k = env_anahtar(x)
    for ad, e in ay_dosya.get(k, []):
        if ad == sinif:
            return ad, e, False
    for ad, e in ay_kayit:
        if ad == sinif and e["not"].startswith("Birleşik ayar") and k in e["not"]:
            return ad, e, True
    return None


def ay_not_parca(e, k):
    n = e["not"]
    m = re.search(r"\[" + re.escape(k) + r"\]\s*(.*?)(?:\s\|\s\[|$)", n)
    return (m.group(1) if m else n)


AILE = {"trend_takip": "trend", "momentum": "trend", "kirilim": "trend", "ortalamaya_donus": "MR", "formasyon": "diger",
        "destek_direnc": "diger", "diger": "diger"}

# ------------------------------------------------------------------ elle kararlar
elle = {}
if ELLE.exists():
    for x, _ in oku_csv(ELLE):
        elle[x["ham_id"]] = x


def satir(hid, kid, no, ad, mantik, aile):
    return {"ham_id": hid, "kaynak_id": kid, "kaynak_satir_no": no, "kaynaktaki_ad": kes(ad, 120), "kisa_mantik": kes(mantik, 160),
            "aile": aile, "eslesme": "", "hedef": "", "ayar_id": "", "ayar_dosyasi": "", "fark": "", "on_durum": "",
            "neden_kodu": "", "neden_metni": "", "kanit": "", "not": ""}


def ekle_not(h, t):
    h["not"] = (h["not"] + " | " + t).strip(" |") if h["not"] else t


# ------------------------------------------------------------------ pf bağlama (BAGLAMA) kaydı
sys.path.insert(0, str(ROOT))
from motor.portfoy.stratejiler.baglama import BAGLAMA, BAGLANAMAYAN  # noqa: E402  (salt okuma: sabit tabloları)
import motor.portfoy.stratejiler.ek2 as _ek2  # noqa: E402

BAG = defaultdict(list)
for b in BAGLAMA:
    BAG[b["satir"]].append(b)
EK2_SATIR = {b["satir"] for b in _ek2.BAGLAMA_EK2}
pf_sinif_ilk = {}
for b in sorted(BAGLAMA, key=lambda b: (b["satir"] in EK2_SATIR, b["satir"])):
    pf_sinif_ilk.setdefault(b["sinif"], b["satir"])

# pf satırı <-> envanter satırı eşi (ad: kaynak 'dis_envanter_veri_yok')
env_ad = {}
for i, (x, ln) in enumerate(env):
    env_ad.setdefault((x["kaynak"], nz(x["ad"])), []).append(i)
PF_ENV_EL = {18: 2, 19: 59, 22: 168, 23: 196, 25: 285, 32: 351, 45: 400, 52: 411, 70: 53}   # pf 0-tabanlı -> env 0-tabanlı
pf_env = {}
for j, (x, ln) in enumerate(pf):
    if x["kaynak"] != "dis_envanter_veri_yok":
        continue
    if j in PF_ENV_EL:
        pf_env[j] = PF_ENV_EL[j]
        continue
    k, rest = x["ad"].split(": ", 1)
    m = env_ad.get((k, nz(rest)))
    if m and len(m) == 1:
        pf_env[j] = m[0]
    else:
        uyar(f"pf satır {j}: envanter eşi bulunamadı ({x['ad']})")
env_pf = {v: k for k, v in pf_env.items()}
if len(env_pf) != len(pf_env):
    uyar("pf->env eşi birebir değil")


def pf_aile(sinif, ayar_text):
    if sinif in ("pf__pairs", "pf__ibs_donus", "pf__rsi_cift", "pf__rsi_tarama", "pf__pca_statarb"):
        return "MR"
    if sinif == "pf__kesit_ls" and ('"donus"' in ayar_text or "'donus'" in ayar_text):
        return "MR"
    if sinif in ("pf__sabit_sepet", "pf__wq_alfa"):
        return "diger"
    return "trend"


def pf_kod_yaz(h, j, x, ln):
    """Portföy satırı j için KOD/AYAR bilgisi (BAGLAMA kaydından). True: bağlıydı."""
    kay = BAG.get(j)
    if not kay:
        return False
    ilk = kay[0]
    sinif = ilk["sinif"]
    ek2 = ilk["satir"] in EK2_SATIR
    dosya = "motor/portfoy/stratejiler/ek2.py" if ek2 else "motor/portfoy/stratejiler/baglama.py"
    if sinif not in kod_kaydi:
        uyar(f"pf satır {j}: sınıf kod_kaydi'nda yok: {sinif}")
        return False
    kp = kod_pf.get(j)
    yeni_sinif = (kp and "Yeni sınıf" in kp[0]["gerekce"]) or pf_sinif_ilk[sinif] == j
    h["eslesme"] = "KOD" if yeni_sinif else "AYAR"
    h["hedef"] = sinif
    h["on_durum"] = "KOD"
    if h["eslesme"] == "AYAR":
        h["ayar_id"] = f"baglama:satir={j}"
        h["ayar_dosyasi"] = dosya
    kan = [f"{PF_DOSYA}:{ln}", f"{dosya}#satir={j}", sinif_kanit(sinif)]
    if kp:
        kan.append(f"stratejiler/kodlama_2026-11-07_pf.csv:{kp[1]}")
    h["kanit"] = " ; ".join(kan)
    notlar = []
    if len(kay) > 1:
        notlar.append("ayrıca " + ", ".join(b["sinif"] for b in kay[1:]) + " (aynı satır birden çok sınıfa bağlı)")
    if h["eslesme"] == "KOD":
        notlar.append("sınıf bu satırdan ya da bu satırın ilk bağlandığı kayıttan (BAGLAMA sırası) doğdu; sonraki satırlar AYAR")
    n = kay[0].get("not_", "")
    if n:
        notlar.append("bağlama notu: " + kes(n, 140))
    if notlar:
        ekle_not(h, "; ".join(notlar))
    h["aile"] = pf_aile(sinif, str(ilk["ayar"]))
    return True


# ------------------------------------------------------------------ yardımcılar: neden eşlemeleri
YASAK_NEDEN = {"yasak_dca": ("dca", "DCA / ortalama düşürme (kademeli alım, ortalama maliyete göre çıkış): yasak tip"),
               "yasak_izgara_stopsuz": ("stopsuz_grid", "stopsuz ızgara: yasak tip"),
               "yasak_katlama": ("martingale", "katlamalı/piramitleme büyüklük (martingale benzeri): yasak tip")}


def g1_kanit(ad):
    return [f"{G1_DOSYA}:{ln}" for x, ln in g1.get(ad, [])[:1]]


def build_env():
    out = []
    for i, (x, ln) in enumerate(env):
        hid = f"D001:{i + 1}"
        h = satir(hid, "D001", i + 1, x["ad"], x["mekanik_ozet"], AILE.get(x["kategori"], "diger"))
        kb = f"{ENV_DOSYA}:{ln}"
        durum, ayd = x["durum"], x["ayar_durumu"]
        h["kanit"] = kb
        if x["onceki_sonuc"]:
            ekle_not(h, "eski sonuç (envanterde): " + kes(x["onceki_sonuc"], 110))
        ab = kod_a.get(i) or kod_b.get(i)

        def tamamla(on, eslesme="YOK", neden="", metin="", ekk=None):
            h["eslesme"] = eslesme
            h["on_durum"] = on
            h["neden_kodu"] = neden
            h["neden_metni"] = metin
            if ekk:
                h["kanit"] = " ; ".join([kb] + ekk)

        if durum in YASAK_NEDEN:
            nk, nm = YASAK_NEDEN[durum]
            tamamla("F_YASAK_TIP", "YOK", nk, nm)
        elif durum == "ml":
            tamamla("G_ML", "YOK", "ml", "makine öğrenmesi modeli (sınıflandırıcı/kNN/XGBoost) tahmini")
        elif durum == "gecersiz_lookahead":
            tamamla("D_KODLANMADI_NEDENLI", "YOK", "lookahead", "normalizasyon tüm veriyi kullanıyor (geleceği görüyor): geçersiz",
                    g1_kanit(x["ad"]))
        elif durum == "arac_sablon":
            tamamla("D_KODLANMADI_NEDENLI", "YOK", "arac_sablon", "strateji değil: şablon/araç/iskelet (kendi giriş mantığı yok)",
                    g1_kanit(x["ad"]))
        elif durum == "veri_yok":
            j = env_pf.get(i)
            if j is not None and pf_kod_yaz(h, j, *pf[j]):
                h["kanit"] = kb + " ; " + h["kanit"]
                ekle_not(h, f"envanter durumu 'veri_yok' idi; sonradan portföy katmanında kodlandı (portfoy_adaylari satır {j + 1}); "
                            f"kopya satır: D002:{j + 1}")
            else:
                tamamla("D_KODLANMADI_NEDENLI", "YOK", "veri_yok",
                        "gerekli dış veri/evren yok: " + kes(x["veri_ihtiyaci"], 60) + " (envanter durumu veri_yok)")
                if j is not None:
                    kp = kod_pf.get(j)
                    ekle_not(h, f"portföy satırı D002:{j + 1} kopyası; portföyde de bağlanamadı"
                                + (f" (kodlama_2026-11-07_pf.csv:{kp[1]}: {kp[0]['durum']})" if kp else ""))
                    if kp:
                        h["kanit"] += f" ; stratejiler/kodlama_2026-11-07_pf.csv:{kp[1]}"
        elif ayd.startswith("ayar:"):
            sinif = ayd.split(":", 1)[1].strip()
            bul = ay_bul(x, sinif)
            if bul is None or sinif not in kod_kaydi:
                tamamla("BELIRSIZ", "YOK", "", f"ayar:{sinif} yazıyor ama dis_ayarlari/{sinif}.json'da kayıt yok / sınıf yok")
                uyar(f"{hid}: ayar kaydı bulunamadı ({ayd})")
            else:
                ad, e, birl = bul
                h["eslesme"], h["hedef"], h["on_durum"] = "AYAR", sinif, "KOD"
                h["ayar_id"] = e["dis_id"]
                h["ayar_dosyasi"] = f"stratejiler/dis_ayarlari/{ad}.json"
                h["kanit"] = f"{kb} ; stratejiler/dis_ayarlari/{ad}.json#{e['dis_id']} ; {sinif_kanit(sinif)}"
                nt = ay_not_parca(e, env_anahtar(x))
                if birl:
                    ekle_not(h, "birleşik ayar (kayıt başka satırla paylaşılıyor; dis_id=" + e["dis_id"] + ")")
                if nt.startswith("YAKLAŞIK") or "YAKLAŞIK" in nt:
                    ekle_not(h, "ayar YAKLAŞIK uyarlama: " + kes(nt, 170))
        elif ayd.startswith("atlandi") and ab is not None:
            rec, aln = ab
            d = rec["durum"]
            kf = "stratejiler/kodlama_2026-11-07_a.csv" if i in kod_a else "stratejiler/kodlama_2026-11-07_b.csv"
            ekk = [f"{kf}:{aln}"]
            if d == "kodlandi":
                sinif = rec["yeni_strateji_adi"]
                if sinif in kod_kaydi:
                    h["eslesme"], h["hedef"], h["on_durum"] = "KOD", sinif, "KOD"
                    h["kanit"] = " ; ".join([kb] + ekk + [sinif_kanit(sinif)])
                else:
                    tamamla("BELIRSIZ", "YOK", "", f"{kf} kodlandi diyor ({sinif}) ama kod_kaydi.csv'de sınıf yok", ekk)
                    uyar(f"{hid}: kodlandi ama sınıf yok: {sinif}")
            elif d == "kurala_dokulemez":
                tamamla("D_KODLANMADI_NEDENLI", "YOK", "kural_belirsiz", kes(rec["gerekce"], 170), ekk)
            elif d == "veri_yok":
                tamamla("D_KODLANMADI_NEDENLI", "YOK", "veri_yok", kes(rec["gerekce"], 170), ekk)
            elif d == "yasak":
                tamamla("F_YASAK_TIP", "YOK", "stopsuz_grid", kes(rec["gerekce"], 170), ekk)
            else:
                tamamla("BELIRSIZ", "YOK", "", f"kodlama kaydı durumu: {d} — {kes(rec['gerekce'], 120)}", ekk)
        elif ayd == "kodlandi":
            # sınıf docstring'inde kaynak izi aranır (D1-D3 dalgaları)
            ana = os.path.basename(x["dosya"]).rsplit(".", 1)[0] if x["kaynak"] in ("tv", "freqtrade") else None
            hit = []
            if ana:
                pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(ana) + r"(?![A-Za-z0-9_])")
                hit = [a for a, d in sinif_doc.items() if pat.search(d)]
            kl = kodlanacak_dosya.get(x["dosya"]) if x["kaynak"] in ("tv", "freqtrade") else kodlanacak.get(x["ad"])
            ekk = [f"stratejiler/dis_kodlanacak.csv:{kl[0]}"] if kl else []
            if len(hit) == 1:
                s = hit[0]
                h["eslesme"], h["hedef"], h["on_durum"] = "KOD", s, "KOD"
                h["kanit"] = " ; ".join([kb] + ekk + [sinif_kanit(s) + f" (docstring kaynak izi: {ana})"])
            elif len(hit) > 1:
                h["eslesme"], h["hedef"], h["on_durum"] = "KOD", hit[0], "KOD"
                h["kanit"] = " ; ".join([kb] + ekk + [sinif_kanit(s) for s in hit])
                ekle_not(h, "aynı kaynaktan birden çok sınıf: " + ", ".join(hit))
            else:
                tamamla("E_KODLANMADI_NEDENSIZ", "YOK", "kod_yok",
                        "envanter ayar_durumu=kodlandi ve dis_kodlanacak.csv'de kuyrukta; ama sınıf/kayıt bulunamadı", ekk)
        else:
            tamamla("BELIRSIZ", "YOK", "", f"beklenmeyen durum/ayar_durumu: {durum} / {ayd[:40]}")
        out.append(h)
    return out


def build_pf():
    out = []
    for j, (x, ln) in enumerate(pf):
        hid = f"D002:{j + 1}"
        h = satir(hid, "D002", j + 1, x["ad"], x["kural_ozu"], "diger")
        kb = f"{PF_DOSYA}:{ln}"
        h["kanit"] = kb
        kp = kod_pf.get(j)
        ekle_not(h, f"kaynak={x['kaynak']} kimlik={x['kimlik']}; evrene_uyarlanabilir_mi={x['evrene_uyarlanabilir_mi']}")
        if j in pf_env:
            e = pf_env[j]
            h["eslesme"], h["hedef"], h["on_durum"] = "TEKRAR", f"D001:{e + 1}", "TEKRAR"
            h["aile"] = AILE.get(env[e][0]["kategori"], "diger")
            h["kanit"] = f"{kb} ; {ENV_DOSYA}:{env[e][1]}"
            ekle_not(h, "aynı strateji dis_envanter'de (durum veri_yok); karar/eşleme o satırda")
        elif pf_kod_yaz(h, j, x, ln):
            h["kanit"] = h["kanit"]
        elif j in BAGLANAMAYAN:
            h["eslesme"], h["on_durum"] = "YOK", "D_KODLANMADI_NEDENLI"
            h["neden_kodu"], h["neden_metni"] = "kapsam_disi", kes(BAGLANAMAYAN[j][1], 170)
            h["kanit"] = f"{kb} ; motor/portfoy/stratejiler/baglama.py#BAGLANAMAYAN[{j}]" + (
                f" ; stratejiler/kodlama_2026-11-07_pf.csv:{kp[1]}" if kp else "")
        elif kp:
            h["eslesme"] = "YOK"
            h["on_durum"] = "D_KODLANMADI_NEDENLI"
            h["neden_kodu"] = {"veri_yok": "veri_yok", "uyarlanamaz": "kapsam_disi"}.get(kp[0]["durum"], kp[0]["durum"])
            h["neden_metni"] = kes(kp[0]["gerekce"], 170)
            h["kanit"] = f"{kb} ; stratejiler/kodlama_2026-11-07_pf.csv:{kp[1]}"
        else:
            h["eslesme"], h["on_durum"], h["neden_kodu"] = "YOK", "BELIRSIZ", ""
            h["neden_metni"] = "pf_sinif boş, kodlama/BAGLANAMAYAN kaydı yok"
            uyar(f"{hid}: akıbet kaydı yok")
        out.append(h)
    return out


# ------------------------------------------------------------------ eski TV (meta / meta3)
EV = {}
for i, (x, ln) in enumerate(env):
    if x["kaynak"] == "tv":
        EV[os.path.basename(x["dosya"]).rsplit(".", 1)[0]] = (i, x, ln)

TV_ESKI = ROOT / "arsiv/strateji-sg/tv_eleme_dali"
aday = {x["id"]: (x, ln) for x, ln in oku_csv(TV_ESKI / "aday.csv")}
kararlar = json.load(open(TV_ESKI / "analiz/_kararlar.json", encoding="utf-8"))
GECEN = {"hezSShJr": "hybrid_brk", "G40dtEbK": "sqzmom", "VO6DY8s1": "macd_reloaded"}


def eski_not(tid):
    p = []
    if tid in aday:
        a, ln = aday[tid]
        p.append(f"eski proje aday.csv:{ln} karar={a['karar']}: {kes(a['neden'], 90)}")
    elif tid in kararlar:
        k = kararlar[tid]
        p.append(f"eski proje analiz/_kararlar.json#{tid} karar={k['karar']}: {kes(k['gerekce'], 90)}")
    else:
        p.append("eski projede karar kaydı yok")
    if tid in GECEN:
        p.append(f"eski RAPOR.md: 3 geçenden biri ({GECEN[tid]}) — 1L3A testi DEĞİL")
    return "; ".join(p)


def build_meta():
    out = []
    for kid, dosya, ad_no in (("D050", "arsiv/strateji-sg/tv_eleme_dali/ham/meta.json", "meta"),
                              ("D051", "arsiv/strateji-sg/tv_eleme_dali/ham/meta3.json", "meta3")):
        liste = json.load(open(ROOT / dosya, encoding="utf-8"))
        for n, m in enumerate(liste, 1):
            hid = f"{kid}:{n}"
            tid = m["id"]
            kb = f"{dosya}#{tid}"
            if tid in EV:
                i, x, ln = EV[tid]
                h = satir(hid, kid, n, m["ad"], x["mekanik_ozet"], AILE.get(x["kategori"], "diger"))
                h["eslesme"], h["hedef"], h["on_durum"] = "TEKRAR", f"D001:{i + 1}", "TEKRAR"
                h["kanit"] = f"{kb} ; {ENV_DOSYA}:{ln} (aynı betik kimliği {tid})"
                if nz(m["ad"]) != nz(x["ad"]):
                    ekle_not(h, f"ad farkı: envanterde '{kes(x['ad'], 60)}'")
                    uyar(f"{hid}: meta adı ≠ envanter adı ({tid}): {m['ad'][:50]} / {x['ad'][:50]}")
            else:
                h = satir(hid, kid, n, m["ad"], "kaynak okunamadı (kapalı/bulunamadı); mantık bilinmiyor", "diger")
                ak = aday.get(tid)
                if m["tur"] != "strategy":
                    h["eslesme"], h["on_durum"] = "YOK", "D_KODLANMADI_NEDENLI"
                    h["neden_kodu"] = "kaynak_kapali"
                    h["neden_metni"] = "TradingView kaynak kodu kapalı/bulunamadı (erişim='?'), eski projede de elendi; dis_envanter'da satırı yok"
                    h["kanit"] = kb + (f" ; arsiv/strateji-sg/tv_eleme_dali/aday.csv:{aday[tid][1]}" if tid in aday else
                                       f" ; arsiv/strateji-sg/tv_eleme_dali/analiz/_kararlar.json#{tid}")
                else:
                    h["eslesme"], h["on_durum"] = "YOK", "BELIRSIZ"
                    h["neden_metni"] = "envanterde yok ve neden bilinmiyor"
                    h["kanit"] = kb
                    uyar(f"{hid}: envanterde yok ve kapalı değil ({tid})")
            ekle_not(h, eski_not(tid))
            out.append(h)
    return out


# ------------------------------------------------------------------ elle kararları uygula
def elle_uygula(satirlar):
    idx = {h["ham_id"]: h for h in satirlar}
    for hid, e in elle.items():
        h = idx.get(hid)
        if h is None:
            uyar(f"elle karar: ham_id yok {hid}")
            continue
        for a in ("eslesme", "hedef", "ayar_id", "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni"):
            if e.get(a, "") != "":
                h[a] = e[a]
        if e.get("kanit"):
            h["kanit"] = h["kanit"] + " ; " + e["kanit"] if h["kanit"] else e["kanit"]
        if e.get("not"):
            ekle_not(h, e["not"])
        # tutarlılık: KOD/ESDEGER/BENZER hedefi kayıtta mı
        if h["eslesme"] in ("KOD", "AYAR", "ESDEGER", "BENZER"):
            for t in h["hedef"].split(";"):
                if t.strip() not in kod_kaydi:
                    uyar(f"elle karar {hid}: hedef kayıtta yok: {t}")
            if h["eslesme"] in ("ESDEGER", "BENZER") and not h["fark"]:
                uyar(f"elle karar {hid}: fark boş")
            if h["eslesme"] == "BENZER" and h["on_durum"] != "D_KODLANMADI_NEDENLI":
                h["on_durum"] = "D_KODLANMADI_NEDENLI"
                h["neden_kodu"] = h["neden_kodu"] or "benzer_var"
            if h["eslesme"] in ("KOD", "AYAR", "ESDEGER"):
                h["on_durum"] = "KOD"
        if h["eslesme"] == "TEKRAR":
            h["on_durum"] = "TEKRAR"
    return satirlar


def main():
    satirlar = build_env() + build_pf() + build_meta()
    satirlar = elle_uygula(satirlar)
    with open(CIKTI, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUTUNLAR)
        w.writeheader()
        for h in satirlar:
            w.writerow({k: h[k] for k in SUTUNLAR})
    print("yazıldı:", CIKTI, len(satirlar))
    for kid in ("D001", "D002", "D050", "D051"):
        s = [h for h in satirlar if h["kaynak_id"] == kid]
        print(kid, len(s), dict(Counter(h["on_durum"] for h in s)))
    print("eslesme:", dict(Counter(h["eslesme"] for h in satirlar)))
    print("on_durum:", dict(Counter(h["on_durum"] for h in satirlar)))
    ids = [h["ham_id"] for h in satirlar]
    assert len(ids) == len(set(ids)), "ham_id tekrarı"
    for u in UYARILAR:
        print("UYARI:", u)


if __name__ == "__main__":
    main()
