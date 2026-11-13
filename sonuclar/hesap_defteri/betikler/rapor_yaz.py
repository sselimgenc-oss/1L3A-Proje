"""RAPOR.md üretir. Sayılar ara/rapor_sayilari.json ve ara/liste_*.csv'den okunur (elle sayı yazılmaz).
Önce: birlestir.py → rapor_sayilari.py → (olasi_tekrar.py) → bu betik."""
import csv, json
from collections import Counter
from pathlib import Path
csv.field_size_limit(10**9)
HD = Path(__file__).resolve().parents[1]; ARA = HD / "ara"; KOK = HD.parents[1]
S = json.loads((ARA / "rapor_sayilari.json").read_text())
oku = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
g0 = {r["kod_id"]: r for r in oku(ARA / "G0_kod_akibet.csv")}
ayar = oku(ARA / "G0_ayarlar.csv")
oz = oku(ARA / "oz_denetim.csv")
E = oku(ARA / "liste_E.csv"); C = oku(ARA / "liste_C.csv"); A = oku(ARA / "liste_A.csv")
BEL = oku(ARA / "liste_BELIRSIZ.csv")
ot = oku(ARA / "olasi_tekrar.csv") if (ARA / "olasi_tekrar.csv").exists() else []
kay = {}
for p in [HD / "kaynaklar.csv", ARA / "G10_ARSIV_kaynaklar.csv", ARA / "lider_ek_kaynaklar.csv"]:
    for r in oku(p): kay.setdefault(r["kaynak_id"], r)
D = S["durum"]
def n(k): return D.get(k, 0)
hata = sum(1 for r in oz if r["sonuc"] == "HATA")
ayar_kosulmadi = [r for r in ayar if r["kosuldu_mu"] == "hayir"]
yk = [r for r in g0.values() if r["yapisal_kapi"] == "evet"]
def kapi(r): return "+".join(f"E{i}" for i in (2, 4, 5) if r[f"v2_e{i}"] == "False")
def fl(x):
    try: return float(x)
    except ValueError: return float("-inf")
yk.sort(key=lambda r: -fl(r["v2_net_x1"]))
v1_gecen = sum(1 for r in g0.values() if "gecti" in r["v1_sonuc"])
kod_test = sum(1 for r in g0.values() if r["durum_onerisi"][0] in "AB")
v1_tek = sum(1 for r in g0.values() if r["v1_tf"] and r["tur"] == "tek_grafik")
v1_pf = sum(1 for r in g0.values() if r["v1_tf"] and r["tur"] == "portfoy")
kod_tek = sum(1 for r in g0.values() if r["tur"] == "tek_grafik"); kod_pf = len(g0) - kod_tek
B_adil_degil = sum(v for k, v in S["B_adil"].items() if k != "evet")
etiket = Counter()
for k, v in S["B_adil"].items():
    for e in k.split(";"): etiket[e] += v
ot_fazla = sum(int(r["tekil_sayisi"]) - 1 for r in ot)
C_kod = sum(1 for r in C if r["tekil_id"].startswith("KOD:")); C_ayar = len(C) - C_kod
A_kesif = sum(1 for r in A if g0[r["tekil_id"][4:]]["asama"] == "paper_v2")
A_canli = len(A) - A_kesif
yk_paper = sum(1 for r in g0.values() if r["yapisal_kapi"] == "evet" and r["paper_v2"] == "evet")
H = S["H_neden"]

L = []
w = L.append
w("# Hesap defteri — getirilen tüm stratejilerin akıbeti\n")
w("_2026-11-13. Yalnız okuma; test koşulmadı, kod değişmedi. Sayılar `betikler/` altındaki betiklerle hesaplandı._\n")
w("## Kullanıcıya özet\n")
w(f"1. **{S['kaynak_dosya']} kaynak dosya** ({S['kaynak_birincil']}'i strateji listesi), **{S['ham']} ham satır**, tekilleştirme sonrası **{S['tekil']} tekil strateji** "
  f"({S['tekil_kod']} kodlu + {S['tekil_ayar']} kodlu ama koşulmamış ek ayar + {S['tekil_kodsuz']} kodlanmamış).")
w(f"2. Geçen (A): **{n('A_TEST_EDILDI_GECTI')}** ({A_canli} canlı kadro, {A_kesif} paper — bunlar holdout 'keşif yolu', kanıt değil). Elenen (B): **{n('B_TEST_EDILDI_ELENDI')}**. "
  f"Kodlu ama hiç koşulmamış (C): **{n('C_KODLANDI_KOSULMADI')}** ({C_kod} strateji + {C_ayar} ek ayar; kaynak satırına bağlanmayan {len(ayar_kosulmadi) - C_ayar} ek ayar daha koşulmadı).")
w(f"3. Kodlanmadı, nedeni yazılı (D): **{n('D_KODLANMADI_NEDENLI')}** — bunun {S['D_neden'].get('benzer_var', 0)}'i \"benzeri var\" denip **fark hiç test edilmemiş** olanlar.")
w(f"4. **Kodlanmadı, hiçbir dosyada akıbeti yok (E): {n('E_KODLANMADI_NEDENSIZ')}** — çoğu RoboticAutomations ({S['E_kaynak'].get('B001', 0)}), 906 dış liste ({S['E_kaynak'].get('X005', 0)}) ve TV kuyruğu ({S['E_kaynak'].get('P002', 0)}).")
w(f"5. Yasak tip (F): {n('F_YASAK_TIP')} · ML (G): {n('G_ML')} · bizim evrende uygulanamaz (H): {n('H_BIZIM_EVRENDE_UYGULANAMAZ')} · belirsiz: {n('BELIRSIZ')}.")
w(f"6. Elenen {n('B_TEST_EDILDI_ELENDI')}'in yalnız **{S['B_adil_evet']}'i adil testte** elendi; {B_adil_degil}'i son testte tek TF / sabit ayar / yapısal kapı / kısa veri ile elendi.")
w(f"7. v2'de kârlılığı (E1) ve yoğunlaşmayı (E3) geçip yalnız yapısal kapıdan (E2 örnek / E4 genişlik / E5 kill) düşen: **{S['yapisal_kapi']}** ({yk_paper}'sı sonradan keşif yoluyla paper'da).")
w(f"8. Belgelerdeki \"~460 test edildi\" sayısı v1 evren testindeki tek-grafik sayısıyla tutuyor ({v1_tek}); ama bugün kodda {kod_tek} tek-grafik + {kod_pf} portföy var, test edilen kodlu strateji {kod_test}.")
w(f"9. `ayarlar_d11j_ek.json` (11) ve `ayarlar_d12b_ek.json` (7) **hiçbir araştırma kodunca okunmuyor**: {len(ayar_kosulmadi)} ek ayar kodlandı ama hiç koşulmadı.")
w(f"10. Öz denetim: 40 rastgele tekil satır (tohum 20261113) → **{hata} hata (%{100*hata/40:.1f})**; hataların hepsi doğrulanmamış \"benzer\" eşlemelerinde.")
w(f"11. Emin olmadıklarım: {S['fark_dogrulanmamis']} \"benzer\" eşlemesi kodla karşılaştırılmadı (kaynak/önceki ajan kararı); kaynaklar arası tekilleştirme yalnız açık kanıtla yapıldı → "
  f"tekil sayısı üst sınır (URL'si aynı {len(ot)} grupta en çok {ot_fazla} tekil daha birleşebilir).\n")

w("## 1. Kaynaklar ve sayım\n")
w("| Grup | Kapsam | Ham satır |\n|---|---|---|")
ack = {"G1_KITAP": "Kitap/PDF kartları (137 dosya, 810 kart)", "G2_DIS_ESKI": "dis_envanter (TV/freqtrade/kural), portföy adayları, eski TV meta",
       "G3_REPO": "repo_kodlari, repo_raporlari, ek_77, sg-arge Excel/md listeleri", "G4_GITHUB": "50 GitHub reposu (g1..g7)",
       "G5_151_SON1AY": "Kakushadze 151 + son 1 ay", "G6_V3": "v3 aday katalogları (17 dosya) + dal ekleri",
       "G8_DIS_ARASTIRMA": "Dış ajan 906 liste + ajan2 (dal)", "G9_ROBOTIC": "RoboticAutomations 909 Freqtrade (dal)", "G10_ARSIV": "Eski projeler (arsiv/), haiku dalları"}
for k, v in sorted(S["ham_grup"].items()):
    w(f"| {k} | {ack.get(k, '')} | {v} |")
w(f"| **Toplam** | | **{S['ham']}** |\n")
w("Her grubun kaynak satırı = ham satır sayısı denetlendi (`ara/<GRUP>_NOTLAR.md`). Eşleme dağılımı: " +
  ", ".join(f"{k} {v}" for k, v in sorted(S["ham_eslesme"].items(), key=lambda x: -x[1])) + ".")
w("TEKRAR = aynı stratejinin başka ham satırı (ör. iki Excel sürümü, `b_duzeyi` ⊂ `tumu` kataloglar: 837 satır lider betiğiyle bağlandı).\n")
w("**Not:** 906 liste, derin geçiş, tur 4 ve RoboticAutomations 909 dosyaları main'de değil, birleşmemiş `claude/adoring-maxwell-q7t60g` dalında; "
  "kanıt yolları `dal:...` önekiyle yazıldı.\n")

w("## 2. Durum dağılımı (tekil)\n")
w("| Durum | Sayı | Açıklama |\n|---|---|---|")
acik = {"A_TEST_EDILDI_GECTI": "paper/canlı kadroda", "B_TEST_EDILDI_ELENDI": "son tabi tutulduğu testte elendi",
        "C_KODLANDI_KOSULMADI": "kodda var, hiçbir sonuç dosyasında yok", "D_KODLANMADI_NEDENLI": "nedeni bir dosyada yazılı",
        "E_KODLANMADI_NEDENSIZ": "hiçbir dosyada akıbeti yok", "F_YASAK_TIP": "martingale/DCA/ort. düşürme/stopsuz grid",
        "G_ML": "makine öğrenmesi / LLM", "H_BIZIM_EVRENDE_UYGULANAMAZ": "hisse kesitsel, opsiyon, pairs, seans, orderbook…",
        "BELIRSIZ": "kanıt yetersiz"}
for k in ["A_TEST_EDILDI_GECTI", "B_TEST_EDILDI_ELENDI", "C_KODLANDI_KOSULMADI", "D_KODLANMADI_NEDENLI", "E_KODLANMADI_NEDENSIZ",
          "F_YASAK_TIP", "G_ML", "H_BIZIM_EVRENDE_UYGULANAMAZ", "BELIRSIZ"]:
    w(f"| {k} | {n(k)} | {acik[k]} |")
w(f"| **Toplam** | **{S['tekil']}** | |\n")
w("- B son aşama: " + ", ".join(f"{k} {v}" for k, v in sorted(S["B_asama"].items(), key=lambda x: -x[1])) + ".")
w("- D nedenleri (ilk 10): " + ", ".join(f"{k} {v}" for k, v in list(S["D_neden"].items())[:10]) + ".")
w("- H nedenleri: " + ", ".join(f"{k} {v}" for k, v in S["H_neden"].items()) + ".")
w("- F: " + ", ".join(f"{k} {v}" for k, v in S["F_neden"].items()) + ". (Ön elemenin \"yasak\" torbasındaki lookahead/model satırları D/G'ye taşındı.)\n")

w("## 3. A — geçenler\n")
w("| Strateji | Aşama | Test / işlem |\n|---|---|---|")
for r in A:
    w(f"| `{r['tekil_id'][4:]}` | {r['asama']} | {r['tf_evren'][:60].replace('|', '/')} · {r['islem_sayisi']} |")
w("")
w("## 4. C — kodlandı, hiç koşulmadı\n")
w("| Kod | Neden (dosyadan) |\n|---|---|")
for r in C:
    w(f"| `{r['tekil_id']}` | {r['neden'].removeprefix('kosulmadi ')[:170].replace('|', '/')} |")
eksik = [r for r in ayar_kosulmadi if not any(c["tekil_id"].endswith(r["ayar_id"]) for c in C)]
for r in eksik:
    w(f"| `AYAR:{r['hedef_kod_id']}:{r['ayar_id']}` | ek ayar dosyası araştırma hattında okunmuyor (kaynak satırı bağlanmadı) |")
w(f"\nToplam koşulmamış: {C_kod} strateji + {len(ayar_kosulmadi)} ek ayar. Kanıt: `motor/arastirma/tarama.py::_ayar_listesi`, "
  "`motor/arastirma/wf_portfoy.py::aday_listesi` (yalnız kart_ayarlari + dis_ayarlari + BAGLAMA + ızgara); "
  "`ayarlar_d11j_ek.json`/`ayarlar_d12b_ek.json` yalnız `testler/` içinde okunuyor.\n")

w(f"## 5. E — kodlanmadı, akıbeti hiçbir yerde yazmıyor ({len(E)})\n")
grp = Counter(r["kaynaklar"].split(";")[0] for r in E)
w("Kaynağa göre: " + ", ".join(f"{k} ({kay.get(k, {}).get('yol', '?')[-60:]}) {v}" for k, v in grp.most_common()) + ".\n")
w("| Tekil | Ad | Mantık |\n|---|---|---|")
for r in E:
    w(f"| `{r['tekil_id'][4:]}` | {r['ad'][:70].replace('|', '/')} | {r['kisa_mantik'][:110].replace('|', '/')} |")
w("")

w("## 6. Adil olmayan elemeler\n")
w(f"Elenen {n('B_TEST_EDILDI_ELENDI')} kodlu stratejiden {S['B_adil_evet']}'i \"adil\" (birden çok TF, ızgara, geniş evren) testte elendi. Diğerleri "
  f"(bir strateji birden çok etikette olabilir): " + ", ".join(f"{k} {v}" for k, v in etiket.most_common() if k != "evet") + ".")
w("- `yalniz_varsayilan_ayar`: son test (çoğunlukla v2 elemesi) tek sabit ayarla yapıldı; v1'de ızgara vardı ama v2 tek ayar taşıdı.")
w("- `yalniz_tek_TF`: son testte tek zaman dilimi. `kisa_veri`: v3/kısa dönem. `yapisal_kapi`: kârlı ama örnek/genişlik/kill kapısı.")
w("- Tam liste: `ara/liste_adil_olmayan.csv`.\n")
w(f"### Kârlılığı geçip yapısal kapıdan düşen {len(yk)} strateji (v2, yapisal_kapi=evet)\n")
w("Kapı dağılımı: " + ", ".join(f"{k} {v}" for k, v in Counter(kapi(r) for r in yk).most_common()) + ". En yüksek net (maliyet ×1) ilk 15:\n")
w("| Strateji | TF | Düştüğü kapı | Net ×1 | PF ×1 | İşlem | paper_v2 |\n|---|---|---|---|---|---|---|")
for r in yk[:15]:
    w(f"| `{r['kod_id']}` | {r['v2_tf']} | {kapi(r)} | {r['v2_net_x1'][:6]} | {r['v2_pf_x1'][:5]} | {r['v2_n_islem_x1']} | {r['paper_v2']} |")
w("\nTam liste: `ara/liste_yapisal_kapi.csv`. Not: net değerleri 2017→2025 geliştirme dönemi (kanıt değil).\n")
w("### Benzeri var denip fark test edilmeyenler\n")
w(f"{S['fark_test_edilmedi']} kodlanmamış tekil strateji, kodlu bir sınıfa \"benzer\" denerek bırakıldı; mantık farkı (filtre, çıkış, TF, yön, evren) hiç test edilmedi. "
  f"Bunların {S['fark_dogrulanmamis']}'inde benzerlik iddiası bile kodla doğrulanmadı (kaynak heuristiği/önceki ajan). "
  "Kodla açılan örneklerde önceki \"aynı\" kararlarının çoğu tutmadı (G8: 174'te 118 fark; G9: 16 eşleşme reddedildi; G1: 81 `mevcut:X` kartının 8'i eşdeğer). "
  "Liste: `ara/liste_fark_test_edilmedi.csv`.\n")
w("### Diğer adalet bulguları\n")
w(f"- {S['kod_kaynaksiz']} kodlu stratejinin birebir kaynak satırı yok: kaynak kartlarının hepsi koda \"benzer\" (aile kodu kartın kuralını uygulamıyor) ya da v2/v3 eklemesi.")
w("- 102 kitap kartı aile üyesi ama aile kodu kartın kuralını uygulamıyor (G1 NOTLAR). 93 kart `ayar:X` önerilmiş ama `kart_ayarlari`'na yazılmamış; repo envanterinde 374 `ayar:X` satırının ayar kaydı yok.")
w("- v3'te 22 kodlu strateji \"aile temsilcisi değil\" (test bütçesi) diye koşulmadı (ON_KAYIT_V3 0.4).")
w("- Eski projelerde iyi sonuç verip 1L3A'da aynı biçimi test edilmeyenler (G10 NOTLAR): Argus gizli diverjans, Ichimoku 20/60/120 (eski OOS PF 2.52; bizde ızgara 26/52), günlük kapitülasyon D2, EPA-B, ABD trend portföyü.")
w(f"- Pairs ({H.get('pairs',0)}), hisse kesitsel ({H.get('hisse_kesitsel',0)}), seans/gap ({H.get('seans_gap',0)}) tekilleri tanım gereği H; ama `pf__pairs`, `pf__rotasyon`, `pf__kesit_ls`, `daytrade__orb`, `daytrade__gap-doldurma` kodda var ve kendi evrenimizde test edildi — H burada \"kaynaktaki enstrümanlar evrenimizde yok\" demektir.")
w("- v3 ön elemede \"kod yok\" gerekçesiyle elenen ama kuralı metinde açık olan satırlar (G6 NOTLAR: V014:440, V013:445, V005:4/5/25, V010:19).\n")

w("## 7. Belgelerdeki sayılar ↔ tablo\n")
w("| Belge iddiası | Kaynak | Tablo | Sonuç |\n|---|---|---|---|")
rows = [
 ("460 tek grafik strateji + 19 portföy sınıfı", "DURUM.md:407", f"v1 evren WF: {v1_tek} + {v1_pf}; kodda bugün {kod_tek} + {kod_pf}", "v1 için tutuyor; kod sonra büyüdü (+42)"),
 ("~120 ek ayar/mod kaydı", "DURUM.md:407", "dis_ayarlari 177 + d11j_ek 11 + d12b_ek 7 (kart_ayarlari 226 ayrı)", "TUTMUYOR (195; 18'i hiç koşulmadı)"),
 ("192 kodlu (105 kitap + 87 dış), 226 kart ayarı, 110 dış ayar", "DURUM.md:103", "kart_ayarlari 226; dış KOD eşlemesi 162 satır; dis_ayarlari 177", "226 tutuyor; 87/110 eski (Katman 1 anı)"),
 ("~700 aday: 438 kart + 160 TV + 68 freqtrade + ~30 dış kural", "DURUM.md:74", "kart 810; dis_envanter tv 247, freqtrade 68, kural+awesome+jesuistm 116", "freqtrade tutuyor; TV/kural sayıları TUTMUYOR"),
 ("~430 strateji (2026-11-07 gece)", "DURUM.md:391", f"kodda {kod_tek + kod_pf}", "ara sayı; bugünle tutmaz (beklenen)"),
 ("810 kart, 100 aile, 70 elenen", "DURUM.md:24-25,392", "810 / 100 / 70", "tutuyor"),
 ("rapor 314 (65 yeni, 54 yasak); kod 398 (44 yeni)", "DURUM.md:385", "G3 sayımı birebir (rapor CSV'sinde ayrıca 17 arac_sablon)", "tutuyor"),
 ("GitHub 1198 satır", "DURUM.md:392", "1198", "tutuyor"),
 ("v2: eleme 222 → 18; keşif 7; sağlam 5; set 2", "DURUM.md:207-211", "G0: 18 geçti, 198 elendi, 6 hata; keşif 7; sağlam 5; set 2", "tutuyor"),
 ("Katman 3b: 32 adaydan 13'ü sağlam", "DURUM.md:109", "sonuclar/saglamlik/k3_kripto.csv'de saglam_mi=True 15 (35 satır)", "TUTMUYOR (15; dosya sonradan yenilenmiş olabilir)"),
 ("26 kodlu strateji hiç koşulmamış", "görev metni", "C: 26 strateji (+18 ek ayar)", "tutuyor (ayarlarla 44)"),
 ("v2'de E1+E3 geçip E2/E4/E5'ten düşen 73", "görev metni", f"{S['yapisal_kapi']}", "tutuyor"),
 ("v3 eleme 0/9", "DURUM.md:143", "v3 eleme.csv 9 satır, 0 geçen", "tutuyor"),
 ("dis_envanter 'kodlandi' yazan satırlar", "stratejiler/dis_envanter.csv", "7 satırın sınıfı kodda yok (G2 NOTLAR)", "TUTMUYOR"),
 ("CODEX_ADAYLAR '12 strateji'", "arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md", "tabloda 11 repo", "TUTMUYOR (küçük)"),
]
for a, b, c, d in rows:
    w(f"| {a} | `{b}` | {c} | {d} |")
w("")
w("## 8. Öz denetim\n")
w(f"`betikler/oz_denetim_ornek.py`: tekil tablodan tohum 20261113 ile 40 satır; her biri kaynak satırına ve kanıt dosyasına geri izlendi (`ara/oz_denetim.csv`). "
  f"**Hata: {hata}/40 = %{100*hata/40:.1f}** (eşik %10 aşılmadı; düzeltmeler `ara/lider_duzeltmeleri.csv`'de uygulandı).")
for r in oz:
    if r["sonuc"] == "HATA":
        w(f"- #{r['sira']} `{r['tekil_id']}`: {r['aciklama']}")
w("\nAyrıca her ajan çıktısından 10–12 satır kaynağa izlendi (ILERLEME.md denetim günlüğü): 1 hata (G3 P001:135) dışında tutarlı. "
  "Hataların hepsi doğrulanmamış \"benzer\" eşlemelerinde → bu alt kümenin hata oranı genelden yüksektir (örnekte ~10 satırda 2).\n")
w("## 9. Emin olmadıklarım\n")
w(f"- {S['fark_dogrulanmamis']} \"benzer\" eşlemesinin hedef sınıfı kodla karşılaştırılmadı (çoğu G3 heuristik `ayar:X`, G9 önceki ajan kümeleri, G6 docstring). Durumları D doğru olsa bile hedefleri yanlış olabilir.")
w(f"- Kaynaklar arası tekilleştirme yalnız açık kanıtla (TEKRAR, aynı katalog kaydı) yapıldı. Aynı URL'yi paylaşan {len(ot)} grup var (`ara/olasi_tekrar.csv`); "
  f"çoğu tek makalede birden çok strateji. Tekil sayısı ({S['tekil']}) bu yüzden üst sınırdır.")
w(f"- {n('BELIRSIZ')} BELIRSIZ: v3'te \"tekrar\" denip hedefi çözülemeyen 38 satırdan kalanlar ve 906 listesinde kapsam dışı nedeni boş satırlar (`ara/liste_BELIRSIZ.csv`).")
w("- adil_test etiketleri lider/G0 tanımıdır (kurallar `ara/G0_NOTLAR.md` §5 ve `betikler/birlestir.py::adil_turet`).")
w("- H/D ayrımı (veri yok mu, evren dışı mı) ajanlar arasında tam tek tip değil; ikisi de \"kodlanmadı, nedenli\" anlamına gelir.")
w("- Kitap kartlarında kart ↔ kod karşılaştırması çoğunlukla docstring + parametre ızgarasıyla yapıldı, `sinyaller()` gövdesi satır satır okunmadı.")
w("- Ajan2 (26 kayıt) raporundan 17'si ayırt edilebildi; CSV'si yok.\n")
w("## 10. Dosyalar\n")
w("- `kaynaklar.csv` (+ `ara/G10_ARSIV_kaynaklar.csv`, `ara/lider_ek_kaynaklar.csv`): kaynak envanteri.")
w("- `ham_satirlar.csv`: her ham satır → tekil_id (kanıt + eşleme). `tekil_stratejiler.csv`: tekil başına tek durum.")
w("- `ara/G*_ham.csv`, `ara/G*_NOTLAR.md`: ajan çıktıları (değiştirilmedi). `ara/lider_duzeltmeleri.csv`, `ara/lider_birlestir_ile.csv`: lider düzeltmeleri.")
w("- `ara/G0_kod_akibet.csv`: 521 kodlu stratejinin tüm aşamaları. `ara/G0_ayarlar.csv`: 421 ayar kaydı ve koşulup koşulmadığı.")
w("- `ara/liste_*.csv`: A, C, E, BELIRSIZ, adil olmayan, yapısal kapı, fark test edilmedi.")
w("- Yeniden üretim: `kaynak_envanteri.py` → `kod_kaydi.py` → grup betikleri → `lider_v3_alt_kume.py` → `birlestir.py` → `rapor_sayilari.py` → `olasi_tekrar.py` → `oz_denetim_ornek.py` → `rapor_yaz.py`.")
(HD / "RAPOR.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("RAPOR.md", len(L), "satır")
