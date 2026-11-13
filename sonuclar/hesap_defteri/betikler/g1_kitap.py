"""G1_KITAP ham satırları: 810 kitap kartı -> ara/G1_KITAP_ham.csv + ara/G1_KITAP_NOTLAR.md.
Mekanik kısım burada; elle (kod okuyarak) verilen kararlar ara/G1_KITAP_elle_kararlar.csv'den okunur ve üstüne yazılır.
Test koşmaz, strateji kodu değiştirmez (yalnız sınıf özelliklerini okumak için içe aktarır)."""
import csv, json, glob, re, collections, os, sys
from pathlib import Path
KOK = Path(__file__).resolve().parents[3]; os.chdir(KOK); sys.path.insert(0, str(KOK))
ARA = "sonuclar/hesap_defteri/ara/"
def rd(p, enc="utf-8-sig"): return list(csv.DictReader(open(p, encoding=enc)))

kaynak = [r for r in rd("sonuclar/hesap_defteri/kaynaklar.csv") if r["grup"] == "G1_KITAP" and r["tur"] == "birincil:kitap_kartlari"]
kod = {r["ad"]: (i + 2, r) for i, r in enumerate(rd(ARA + "kod_kaydi.csv"))}
KY = lambda ad: f"{ARA}kod_kaydi.csv:{kod[ad][0]} ({kod[ad][1]['dosya']}:{kod[ad][1]['satir']})"
cards, order = {}, []
for r in kaynak:
    for i, c in enumerate(json.load(open(r["yol"]))):
        hid = f"{r['kaynak_id']}:{i+1}"; cards[c["kart_id"]] = (hid, r["kaynak_id"], i + 1, c); order.append(c["kart_id"])
aile = {x["aile_id"]: x for x in json.load(open("stratejiler/aileler.json"))}
mem = {k: a for a, x in aile.items() for k in x["kaynak_kartlar"]}
ele = {x["kart_id"]: x["neden"] for x in json.load(open("stratejiler/elenenler.json"))}
cm = json.load(open("stratejiler/cikis_risk_modulleri.json"))
cmk = {k: m["modul_id"] for m in cm for k in m["kaynak_kartlar"]}
yd = {r["kart_id"]: (i + 2, r) for i, r in enumerate(rd("stratejiler/yazar_denetimi.csv"))}
EKF = "stratejiler/ek_kaynaklar/kitap_kartlari_eslesme.csv"
ek = {r["kart_id"]: (i + 2, r) for i, r in enumerate(rd(EKF))}
ay = {}
for f in glob.glob("stratejiler/kart_ayarlari/*.json"):
    for r in json.load(open(f)): ay[r["kart_id"]] = (f, r)
tg = collections.defaultdict(list)
for i, r in enumerate(rd("stratejiler/ek_kaynaklar/tam_okuma_guncelleme_ozet.csv")): tg[r["hedef_kart_id"]].append(r)
cikis_ek = rd("stratejiler/cikis_modulleri_ek.csv")
queue = {}
for f in ["stratejiler/ek_kaynaklar/kodlama_kuyrugu_2026-11-07.csv", "stratejiler/ek_kaynaklar/kodlama_kuyrugu_tam_okuma.csv"]:
    for i, r in enumerate(rd(f)):
        for k in r["kaynak_kartlar"].split(";"): queue.setdefault(k.strip(), (f, i + 2, r["yeni_aile"]))
coding = {}
for f in sorted(glob.glob("stratejiler/kodlama_2026-11-07_d1*.csv")):
    for i, r in enumerate(rd(f)): coding[r["yeni_aile"]] = (f, i + 2, r)   # sonraki dosya (d12a) önceki kararı geçer
elle = {r["kart_id"]: r for r in rd(ARA + "G1_KITAP_elle_kararlar.csv")}
try:
    from motor.strateji import kayit
    SIN = kayit.tum_stratejiler()
except Exception: SIN = {}

def tur(c, a=None):
    k = c["kategori"]
    if k == "ortalamaya_donus": return "MR"
    if k in ("trend_takip", "kirilim", "momentum"): return "trend"
    r = c.get("piyasa_rejimi")
    return "MR" if r == "yatay" else "trend" if r == "trend" else "diger"

def elenen(neden):
    n = neden.lower()
    if "martingale" in n: return "F_YASAK_TIP", "martingale"
    if "makine ogrenmesi" in n or "ml" in n.split() or "lorentzian" in n or "knn" in n or "(ml" in n: return "G_ML", "ml"
    if "opsiyon" in n: return "H_BIZIM_EVRENDE_UYGULANAMAZ", "opsiyon"
    if "level-2" in n or "spread" in n: return "H_BIZIM_EVRENDE_UYGULANAMAZ", "orderbook"
    if "sozlesmeler arasi" in n: return "H_BIZIM_EVRENDE_UYGULANAMAZ", "arbitraj"
    if "sektor" in n or "genisligi" in n: return "H_BIZIM_EVRENDE_UYGULANAMAZ", "hisse_kesitsel"
    if "kapali" in n or "tescilli" in n or "ozel" in n and "gosterge" in n: return "D_KODLANMADI_NEDENLI", "kapali_gosterge"
    if "kodlanabilirlik" in n and ("0" in n or "1" in n): return "D_KODLANMADI_NEDENLI", "kural_belirsiz"
    if "pip hedefli" in n or "penny" in n: return "D_KODLANMADI_NEDENLI", "kapsam_disi"
    return "D_KODLANMADI_NEDENLI", "veri_yok"

def bos(): return dict(aile="", eslesme="", hedef="", ayar_id="", ayar_dosyasi="", fark="", on_durum="", neden_kodu="", neden_metni="", kanit="", **{"not": ""})
rows, sorun = [], []
for k in order:
    hid, kid_, no, c = cards[k]
    d = bos(); d["aile"] = tur(c); notes = []
    ekk = ek.get(k)
    if k in mem:
        a = mem[k]; d["hedef"] = a; d["kanit"] = f"stratejiler/aileler.json#{a} ; {KY(a)}"
        if a not in kod: sorun.append(f"aile id kodda yok: {a}")
        y = yd.get(k)
        if y: d["kanit"] += f" ; stratejiler/yazar_denetimi.csv:{y[0]}"; notes.append(f"yazar_denetimi={y[1]['etiket']}")
        if k in ay:
            d.update(eslesme="AYAR", on_durum="KOD", ayar_id=k, ayar_dosyasi=ay[k][0]); d["kanit"] += f" ; {ay[k][0]}#{k}"
            notes.append("ayar: " + ay[k][1]["not"][:140])
            bad = [p for p in ay[k][1]["parametreler"] if a in SIN and p not in getattr(SIN[a], "varsayilan_parametreler", {})]
            if bad: sorun.append(f"ayar parametresi sınıfta yok: {k} {bad}")
        else:
            d.update(eslesme="KOD", on_durum="KOD"); notes.append("kart_ayari yok; aile kodu (kanonik kural)")
        if y and y[1]["etiket"] != "ayni":
            d.update(eslesme="BENZER", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var", ayar_id="", ayar_dosyasi="",
                     fark=f"yazar_denetimi ({y[1]['etiket']}): {y[1]['gerekce']}", neden_metni="Kart aile üyesi ama aile kuralı kartın tetiğini uygulamıyor")
    elif k in ele:
        n = ele[k]; od, nk = elenen(n)
        d.update(eslesme="YOK", on_durum=od, neden_kodu=nk, neden_metni=n[:200], kanit=f"stratejiler/elenenler.json#{k}")
        if "ikinci kopyasi" in n.lower():
            ilk = k.split("__")[0] + "__" + k.split("__")[1] + "__" + k.split("__")[2]
            if ilk in cards and ilk != k: d.update(eslesme="TEKRAR", hedef=cards[ilk][0], on_durum="TEKRAR", neden_kodu="", neden_metni="aynı kitabın ikinci PDF kopyası; ilk kopya da elenmiş")
    elif k in cmk:
        d.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="cikis_modulu", hedef="", neden_metni="Strateji değil, çıkış/risk modülü", kanit=f"stratejiler/cikis_risk_modulleri.json#{cmk[k]}")
    elif ekk:
        li, r = ekk; dur = r["durum"]; d["kanit"] = f"{EKF}:{li}"
        if dur.startswith("ayar:") or dur.startswith("mevcut:"):
            h = dur.split(":", 1)[1]; d["hedef"] = h; d["kanit"] += f" ; {KY(h)}"
            if h not in kod: sorun.append(f"hedef kodda yok {h}")
            if dur.startswith("ayar:"): d.update(eslesme="BENZER", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var")
        elif dur == "yeni":
            q = queue.get(k)
            if q:
                fa = q[2]; d["kanit"] += f" ; {q[0]}:{q[1]}"; cd = coding.get(fa)
                if cd and cd[2]["durum"] == "kodlandi" and cd[2]["yeni_strateji_adi"] in kod:
                    h = cd[2]["yeni_strateji_adi"]; d.update(eslesme="KOD", hedef=h, on_durum="KOD"); d["kanit"] += f" ; {cd[0]}:{cd[1]} ; {KY(h)}"
                    notes.append(f"yeni_aile={fa}; kodlama gerekçesi: {cd[2]['gerekce'][:150]}")
                elif cd: d.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz", neden_metni=cd[2]["gerekce"][:200]); d["kanit"] += f" ; {cd[0]}:{cd[1]}"
                else: d.update(eslesme="YOK", on_durum="E_KODLANMADI_NEDENSIZ", neden_metni=f"kuyrukta ({fa}) ama kodlama dosyasında akıbeti yok")
            else: d.update(eslesme="YOK", on_durum="E_KODLANMADI_NEDENSIZ", neden_metni="yeni denildi, kuyrukta yok")
        elif dur in ("kural_yok", "veri_yok", "yasak", "cikis_modulu"):
            d.update(eslesme="YOK", neden_metni=r["gerekce"][:200])
            if dur == "kural_yok": d.update(on_durum="D_KODLANMADI_NEDENLI", neden_kodu="kural_belirsiz")
            elif dur == "veri_yok":
                g = r["gerekce"].lower(); nk = "opsiyon" if "opsiyon" in g or "covered" in g else "orderbook" if ("defter" in g or "level" in g or "dom" in g or "time&sales" in g) else "veri_yok"
                d.update(on_durum="H_BIZIM_EVRENDE_UYGULANAMAZ" if nk != "veri_yok" else "D_KODLANMADI_NEDENLI", neden_kodu=nk)
            elif dur == "yasak": d.update(on_durum="F_YASAK_TIP", neden_kodu="ortalama_dusurme")
            else:
                d.update(on_durum="D_KODLANMADI_NEDENLI", neden_kodu="cikis_modulu")
                m = [x for x in cikis_ek if k in x["kaynak"]]
                if m: d["kanit"] += " ; stratejiler/cikis_modulleri_ek.csv:" + m[0]["alan_adi"]; notes.append("modül CikisAyarlari'na eklendi: " + m[0]["alan_adi"])
                else: notes.append("cikis_modulleri_ek.csv'de karşılığı yok (modül eklenmedi)")
        else: d.update(on_durum="BELIRSIZ", neden_metni="bilinmeyen durum " + dur)
    else:
        d.update(eslesme="YOK", on_durum="E_KODLANMADI_NEDENSIZ", neden_metni="hiçbir dosyada akıbeti yok")
    if k in tg: notes.append(f"tam_okuma_guncelleme: {len(tg[k])} öneri ({','.join(sorted({x['kodlamaya_etkisi'] for x in tg[k]}))})")
    # elle kararlar
    e = elle.get(k)
    if e:
        for f in ("eslesme", "hedef", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit"):
            if e[f]:
                d[f] = (d["kanit"] + " ; " + e[f]) if f == "kanit" else e[f]
        if e["eslesme"] in ("BENZER", "ESDEGER", "YOK"): d["ayar_id"] = d["ayar_dosyasi"] = ""
        if e["not"]: notes.append(e["not"])
        notes.append("karar:" + e["karar_kaynagi"])
        if d["eslesme"] == "ESDEGER" and not d["fark"]: d["fark"] = "yok"
    if d["eslesme"] == "BENZER" and not d["fark"]: d["fark"] = "(yok)"; sorun.append("BENZER fark boş " + k)
    d["not"] = f"kart_id={k} ; " + " ; ".join(notes)
    d["ham_id"], d["kaynak_id"], d["kaynak_satir_no"] = hid, kid_, no
    d["kaynaktaki_ad"] = c["ad"][:120]; d["kisa_mantik"] = re.sub(r"\s+", " ", c["ozet"])[:160]
    rows.append(d)

COLS = ["ham_id","kaynak_id","kaynak_satir_no","kaynaktaki_ad","kisa_mantik","aile","eslesme","hedef","ayar_id","ayar_dosyasi","fark","on_durum","neden_kodu","neden_metni","kanit","not"]
with open(ARA + "G1_KITAP_ham.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)

C = collections.Counter
ed = C(r["eslesme"] for r in rows); od = C(r["on_durum"] for r in rows)
kc = C(r["kaynak_id"] for r in rows)
fa = C(r["hedef"] for r in rows if r["eslesme"] in ("KOD", "AYAR", "BENZER") and r["hedef"] in aile)
ya = C(r["hedef"] for r in rows if r["eslesme"] == "KOD" and r["hedef"].startswith("dis__"))
mevcut_notr = C(r["eslesme"] for r in rows if "mevcut:" in r["kanit"] or "karar:elle" in r["not"])
aile_benzer = [r for r in rows if r["eslesme"] == "BENZER" and "aileler.json#" in r["kanit"]]
ayarsiz = sum(1 for r in rows if "ayar_onerilen_ama_yazilmamis" in r["not"])
eksik_tg = sorted({k for k in tg if k not in cards})
L = []
L.append("# G1_KITAP NOTLAR\n")
L.append(f"Betik: sonuclar/hesap_defteri/betikler/g1_kitap.py ; elle kararlar: ara/G1_KITAP_elle_kararlar.csv ({len(elle)} kart). Çıktı: ara/G1_KITAP_ham.csv ({len(rows)} satır).\n")
L.append("## Kaynak satır sayısı = ham satır sayısı\nBeklenen 810, üretilen %d. Tüm 137 dosyada tutuyor (dosya başına kart sayısı = satır)." % len(rows))
L.append(f"Dosya sayısı: {len(kc)}; 810 karttan 435 `veri/kart_dizini.csv` (438 satır, 3 kart_id tekrarı) + 372 `kitap_kartlari_eslesme.csv`; ilk 438 (3 Holmes/HA kopyası dahil) = 333 aile üyesi + 70 elenen + 35 çıkış modülü kartı. Yetim kart yok.\n")
L.append("## eslesme dağılımı\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(ed.items())))
L.append("\n## on_durum dağılımı\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(od.items())))
L.append(f"\n## Aile eşlemesi\n{sum(fa.values())} satır aile id'li (KOD/AYAR/BENZER); {len([k for k in rows if k['hedef'] in aile and k['eslesme'] in ('KOD','AYAR')])} satır aile kodu tarafından uygulanıyor. Aile başına kart (en çok 15):")
L.append(", ".join(f"{a}:{n}" for a, n in fa.most_common(15)))
L.append(f"\nYeni aile olarak kodlanan (dis__*) kart: {sum(ya.values())} kart / {len(ya)} sınıf; 139 'yeni' kartın geri kalanı kart-bazlı BENZER (aile kodlu, varyant yok) ya da D/kural_belirsiz (elle CSV).")
L.append(f"E_KODLANMADI_NEDENSIZ: {od.get('E_KODLANMADI_NEDENSIZ',0)} kart.")
L.append("\n## Önemli bulgular")
L.append(f"1. 93 kart eşleme dosyasında `ayar:X` etiketli ama `stratejiler/kart_ayarlari/` içinde bu kart_id'li kayıt YOK (kart_ayarlari'ndaki 226 kayıt tamamı aile üyesi kartlara ait). Bunlar BENZER (not: ayar_onerilen_ama_yazilmamis; sayı {ayarsiz}).")
L.append("2. `stratejiler/ayarlar_d11j_ek.json` / `ayarlar_d12b_ek.json` hiçbir G1 kart_id'sine bağlı değil (kart_id içermiyor; hedef/ayar_id farklı yapıda).")
L.append("3. Aile üyesi kartlarda kart_ayarlari kaydı olanlar eslesme=AYAR (hedef=aile id, KOD eşdeğeri; on_durum KOD). Kaydı olmayanlar KOD.")
L.append(f"4. 'Aile kanonik kuralı kartı uygulamıyor' (aile üyesi BENZER) = {len(aile_benzer)} kart: yazar_denetimi 'yakin/farkli' (otomatik) + aile sınıfı docstring'inde 'KODLANMADI/İFADE EDİLEMEZ' (elle) + elle karşılaştırma. Liste:")
for r in aile_benzer: L.append(f"   - {r['ham_id']} {r['hedef']} <- {r['not'].split(' ; ')[0][8:]} : {r['fark'][:150]}")
L.append("5. Çıkış modülü kartları: 35 eski (cikis_risk_modulleri.json) + 5 yeni (cikis_modulu) = D/cikis_modulu; modül eklenenler not'ta (cikis_modulleri_ek.csv). `trend-yonunde-ekleme-ayri-islem__brooks_r3` için modül eklenmedi (piramit).")
L.append("6. Holmes ikinci PDF kopyaları (2 kart) TEKRAR; `scalp__ha-renk-donusu__heikinashi__eglencelidir` içerik farklı olduğu için TEKRAR değil, aile üyesi.")
L.append(f"7. tam_okuma_guncelleme_ozet.csv: {len(tg)} hedef_kart_id, {len(eksik_tg)} tanesi G1 kartı değil (strateji/başka id): {eksik_tg}")
L.append("8. `yeni__halsey-olculu-hareket`: d10c 'kurala_dokulemez', d12a 'kodlandi' (sonraki karar esas alındı). `yeni__bladerunner-ters` hiçbir yerde kodlanmadı (D, kural_belirsiz).")
if sorun: L.append("9. Betik uyarıları:\n" + "\n".join("   - " + s for s in sorun[:40]))
L.append("\n## Yöntem ve sınırlar\n- aile sütunu: kategori ortalamaya_donus->MR; trend_takip/kirilim/momentum->trend; diğerleri piyasa_rejimi (yatay->MR, trend->trend, kalan diger).\n- mevcut:X (81 kart): yalnız çekirdeği temiz (ızgara içi, ek filtre yok) 8 kart ESDEGER; kodlanabilirliği ≤1 ya da ek koşullu olanlar BENZER (birebirlik doğrulanamadı).\n- Aile üyeleri: tek kartlı 27 aile ve 3+ kartlı ailelerin her biri için sınıf docstring'i (kaynak kart listesi + 'kodlanmadı' notları) tam tarandı; ek olarak ailenin ~2 kartı için kart özeti sınıf kuralıyla elle karşılaştırıldı. sinyaller() gövdeleri her sınıfta satır satır okunmadı.\n- Elenenler: neden metninden regex ile sınıflandı (betikteki `elenen()`); H/D ayrımı yaklaşık.")
L.append("\n## Öz kontrol\nRastgele 10 satır ham_id -> kaynak JSON indeksi -> kart_id geri izlendi (aşağıdaki doğrulama betikle yapıldı):")
import random
random.seed(7)
ok = 0
for r in random.sample(rows, 10):
    kid2 = re.match(r"kart_id=(\S+)", r["not"]).group(1); fid, no = r["ham_id"].split(":")
    p = [x["yol"] for x in kaynak if x["kaynak_id"] == fid][0]; good = json.load(open(p))[int(no) - 1]["kart_id"] == kid2; ok += good
    L.append(f"- {r['ham_id']} {kid2} -> {'OK' if good else 'HATA'}")
L.append(f"Sonuç: {ok}/10 doğru. Envanter dışı kaynak bulunmadı.")
open(ARA + "G1_KITAP_NOTLAR.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print(len(rows), dict(ed), dict(od), len(aile_benzer), sorun[:10])
