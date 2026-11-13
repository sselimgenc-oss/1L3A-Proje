"""Kaynak envanteri: sonuclar/hesap_defteri/kaynaklar.csv üretir (salt okur).
Kullanım: python sonuclar/hesap_defteri/betikler/kaynak_envanteri.py [--adoring DIZIN]
--adoring: origin/claude/adoring-maxwell-q7t60g dalının `git archive ... sonuclar/dis_arastirma` çıktısının açıldığı kök
(dal main'e birleşmedi; dosyalar o daldan okunur, yol önüne 'dal:adoring-maxwell:' yazılır).
"""
import csv, glob, json, os, subprocess, sys
from pathlib import Path
csv.field_size_limit(10**9)
KOK = Path(__file__).resolve().parents[3]
os.chdir(KOK)
ADOR = None
if "--adoring" in sys.argv:
    ADOR = Path(sys.argv[sys.argv.index("--adoring") + 1])

def git_tarih(yol):
    try:
        o = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", yol],
                           capture_output=True, text=True).stdout.split()
        return o[-1] if o else ""
    except Exception:
        return ""

def say(yol):
    p = Path(yol)
    if p.suffix == ".csv":
        with open(p, newline="", encoding="utf-8-sig") as f:
            return sum(1 for _ in csv.reader(f)) - 1
    if p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            for k in ("kartlar", "stratejiler"):
                if k in d:
                    return len(d[k])
        return len(d)
    if p.suffix == ".txt":
        return sum(1 for s in p.read_text(encoding="utf-8").splitlines() if s.strip())
    return ""

# (grup, desen, tur, not)
TANIM = [
 ("G1_KITAP", "veri/kartlar_ham/*/*.json", "birincil:kitap_kartlari", "PDF başına bir kart dosyası"),
 ("G1_KITAP", "veri/kart_dizini.csv", "esleme:kart_dizini", "Aşama 0 438 kartın dizini (810'un alt kümesi)"),
 ("G1_KITAP", "stratejiler/aileler.json", "esleme:aile_birlestirme", "kart -> aile"),
 ("G1_KITAP", "stratejiler/elenenler.json", "karar:elenen_kartlar", ""),
 ("G1_KITAP", "stratejiler/yazar_denetimi.csv", "karar:yazar_denetimi", ""),
 ("G1_KITAP", "stratejiler/ADAY_RAPORU.md", "karar:aday_raporu", ""),
 ("G1_KITAP", "stratejiler/ek_kaynaklar/kitap_kartlari_eslesme.csv", "esleme:yeni_kartlar", ""),
 ("G1_KITAP", "stratejiler/ek_kaynaklar/tam_okuma_*.md", "karar:tam_okuma_raporu", ""),
 ("G1_KITAP", "stratejiler/ek_kaynaklar/tam_okuma_guncelleme_ozet.csv", "esleme:tam_okuma_guncelleme", "mevcut kartlara öneri"),
 ("G1_KITAP", "stratejiler/ek_kaynaklar/kodlama_kuyrugu_tam_okuma.csv", "esleme:kodlama_kuyrugu", ""),
 ("G1_KITAP", "stratejiler/kodlama_2026-11-07_d1*.csv", "esleme:kodlama_kaydi", "yeni_aile -> kod adı"),
 ("G1_KITAP", "stratejiler/cikis_modulleri_ek.csv", "esleme:cikis_modulu", ""),
 ("G1_KITAP", "stratejiler/cikis_risk_modulleri.json", "esleme:cikis_modulu", ""),
 ("G2_DIS_ESKI", "stratejiler/dis_envanter.csv", "birincil:dis_envanter", "tv/freqtrade/kural/awesome/jesuistm"),
 ("G2_DIS_ESKI", "stratejiler/portfoy_adaylari.csv", "birincil:portfoy_adaylari", ""),
 ("G2_DIS_ESKI", "stratejiler/dis_kodlanacak.csv", "esleme:kodlama_kuyrugu", ""),
 ("G2_DIS_ESKI", "stratejiler/kodlama_2026-11-07_a.csv", "esleme:kodlama_kaydi", ""),
 ("G2_DIS_ESKI", "stratejiler/kodlama_2026-11-07_pf.csv", "esleme:kodlama_kaydi", ""),
 ("G2_DIS_ESKI", "stratejiler/dis_ayarlari/*.json", "esleme:dis_ayar", ""),
 ("G2_DIS_ESKI", "arsiv/strateji-sg/tv_eleme_dali/ham/meta.json", "birincil:tradingview_eski", "eski proje TV betikleri"),
 ("G2_DIS_ESKI", "arsiv/strateji-sg/tv_eleme_dali/ham/meta3.json", "birincil:tradingview_eski", ""),
 ("G2_DIS_ESKI", "arsiv/strateji-sg/tv_eleme_dali/RAPOR.md", "sonuc:eski_proje", ""),
 ("G3_REPO", "stratejiler/ek_kaynaklar/repo_kodlari.csv", "birincil:repo_kod_envanteri", ""),
 ("G3_REPO", "stratejiler/ek_kaynaklar/repo_raporlari.csv", "birincil:repo_rapor_envanteri", ""),
 ("G3_REPO", "stratejiler/ek_kaynaklar/ek_77_strateji.md", "birincil:ek77", "77 strateji (md)"),
 ("G3_REPO", "stratejiler/ek_kaynaklar/kodlama_kuyrugu_2026-11-07.csv", "esleme:kodlama_kuyrugu", ""),
 ("G3_REPO", "stratejiler/kodlama_2026-11-07_b.csv", "esleme:kodlama_kaydi", ""),
 ("G3_REPO", "arsiv/sg-arge-/strateji_listesi.xlsx", "birincil:excel_liste", ""),
 ("G3_REPO", "arsiv/sg-arge-/strateji_listesi (2).xlsx", "birincil:excel_liste", ""),
 ("G3_REPO", "arsiv/sg-arge-/day_trade_swing_trade_strateji_listesi.md", "birincil:md_liste", ""),
 ("G3_REPO", "arsiv/sg-arge-/dpay_trade_swing_trade_strateji_listesi.md", "birincil:md_liste", ""),
 ("G4_GITHUB", "stratejiler/ek_kaynaklar/github_g*.csv", "birincil:github_tarama", "50 repo"),
 ("G4_GITHUB", "stratejiler/ek_kaynaklar/kodlama_kuyrugu_github.csv", "esleme:kodlama_kuyrugu", ""),
 ("G4_GITHUB", "stratejiler/kodlama_github_d11*.csv", "esleme:kodlama_kaydi", ""),
 ("G4_GITHUB", "stratejiler/ayarlar_d11j_ek.json", "esleme:ek_ayar", "yalnız testlerde okunuyor (doğrulanacak)"),
 ("G5_151_SON1AY", "stratejiler/ek_kaynaklar/kakushadze_151.csv", "birincil:kakushadze_151", ""),
 ("G5_151_SON1AY", "stratejiler/kodlama_151_d12b.csv", "esleme:kodlama_kaydi", ""),
 ("G5_151_SON1AY", "stratejiler/ayarlar_d12b_ek.json", "esleme:ek_ayar", "yalnız testlerde okunuyor (doğrulanacak)"),
 ("G5_151_SON1AY", "stratejiler/ek_kaynaklar/son1ay_2026-11.csv", "birincil:son1ay", ""),
 ("G5_151_SON1AY", "stratejiler/ek_kaynaklar/son1ay_2026-11.md", "karar:son1ay", ""),
 ("G6_V3", "stratejiler/v3_adaylar/ham/*.csv", "birincil:v3_ham_katalog", "on_eleme.csv hepsini kapsar"),
 ("G6_V3", "stratejiler/v3_adaylar/ham/*.md", "karar:v3_ham_ozet", ""),
 ("G6_V3", "stratejiler/v3_adaylar/on_eleme*.csv", "karar:v3_on_eleme", ""),
 ("G6_V3", "stratejiler/v3_adaylar/veri_yok_etiket_tur6.csv", "karar:v3_veri_yok", ""),
 ("G6_V3", "stratejiler/v3_adaylar/REDDEDILENLER*.txt", "karar:v3_reddedilen", ""),
 ("G6_V3", "stratejiler/v3_adaylar/adaylar.csv", "karar:v3_adaylar", ""),
 ("G6_V3", "stratejiler/v3_adaylar/aileler_v3.csv", "karar:v3_aileler", ""),
 ("G6_V3", "stratejiler/v3_adaylar/kodlama_v3.csv", "esleme:kodlama_kaydi", ""),
 ("G6_V3", "stratejiler/v3_adaylar/fable_hakem.csv", "karar:v3_hakem", ""),
 ("G6_V3", "stratejiler/v3_adaylar/RAPOR.md", "karar:v3_rapor", ""),
 ("G6_V3", "stratejiler/v3_adaylar/kartlar/*.json", "esleme:v3_kart", ""),
 ("G0_SONUC", "sonuclar/v3/eleme.csv", "sonuc:v3_eleme", ""),
 ("G0_SONUC", "sonuclar/v3/ELEME_RAPORU.md", "sonuc:v3_eleme", ""),
 ("G0_SONUC", "sonuclar/evren/v2/eleme.csv", "sonuc:v2_eleme", ""),
 ("G0_SONUC", "sonuclar/evren/v2/test.csv", "sonuc:v2_test", ""),
 ("G0_SONUC", "sonuclar/evren/v2/saglamlik.csv", "sonuc:v2_saglamlik", ""),
 ("G0_SONUC", "sonuclar/evren/v2/set.csv", "sonuc:v2_set", ""),
 ("G0_SONUC", "stratejiler/havuz_v2.csv", "sonuc:v2_havuz", ""),
 ("G0_SONUC", "stratejiler/havuz_v2_etiketler.csv", "sonuc:v2_havuz", ""),
 ("G0_SONUC", "stratejiler/paper_v2_seti.json", "sonuc:paper_v2", ""),
 ("G0_SONUC", "stratejiler/final_set.json", "sonuc:final_v1", ""),
 ("G0_SONUC", "sonuclar/evren/2017_gelistirme/wf_evren.csv", "sonuc:v1_evren_wf", ""),
 ("G0_SONUC", "sonuclar/evren/2017_gelistirme/saglamlik.csv", "sonuc:v1_evren_saglamlik", ""),
 ("G0_SONUC", "sonuclar/evren/2017_gelistirme/pbo.csv", "sonuc:v1_evren_pbo", ""),
 ("G0_SONUC", "sonuclar/evren/2017_gelistirme/iyi_liste.csv", "sonuc:v1_evren_secim", ""),
 ("G0_SONUC", "sonuclar/evren/2017_gelistirme/iyiye_yakin_liste.csv", "sonuc:v1_evren_secim", ""),
 ("G0_SONUC", "sonuclar/tarama/k2_ana_ozet.csv", "sonuc:k2_tarama", ""),
 ("G0_SONUC", "sonuclar/wf/*.csv", "sonuc:k3_wf", ""),
 ("G0_SONUC", "sonuclar/saglamlik/*.csv", "sonuc:k3_saglamlik", ""),
 ("G0_SONUC", "sonuclar/wf_portfoy/*.csv", "sonuc:portfoy_wf", ""),
 ("G0_SONUC", "sonuclar/kilit/sonuc.csv", "sonuc:k4_kilit", ""),
 ("G0_SONUC", "sonuclar/final_aday_havuzu_tek_grafik.csv", "sonuc:final_aday_havuzu", ""),
 ("G0_SONUC", "sonuclar/secim/adaylar.csv", "sonuc:secim", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/karsilastirma/*.csv", "karar:dis_karsilastirma", "main'deki 707 karşılaştırması"),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/karsilastirma/RAPOR.md", "karar:dis_karsilastirma", ""),
]
ADOR_TANIM = [
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/strateji_listesi.csv", "birincil:dis_ajan1_tur4", "906 (tur1-3'ün üst kümesi)"),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/fikir_gruplari.csv", "esleme:fikir_grubu", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/test_oncelik_listesi.csv", "karar:oncelik", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan2/derin_arastirma_26_kayit_raporu.md", "birincil:dis_ajan2", "26 kayıt, CSV yok"),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/derin_gecis/*.csv", "karar:derin_gecis", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/derin_gecis/*.md", "karar:derin_gecis", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/tur4_degerlendirme/*.csv", "karar:tur4", ""),
 ("G8_DIS_ARASTIRMA", "sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/tur4_degerlendirme/RAPOR.md", "karar:tur4", ""),
 ("G9_ROBOTIC", "sonuclar/dis_arastirma/2026-11_freqtrade_robotic/dosya_listesi.csv", "birincil:robotic_909", ""),
 ("G9_ROBOTIC", "sonuclar/dis_arastirma/2026-11_freqtrade_robotic/kume_listesi.csv", "karar:robotic_kume", ""),
 ("G9_ROBOTIC", "sonuclar/dis_arastirma/2026-11_freqtrade_robotic/RAPOR.md", "karar:robotic_rapor", ""),
 ("G9_ROBOTIC", "sonuclar/dis_arastirma/2026-11_freqtrade_robotic/canli_akraba/*", "karar:robotic_canli_akraba", ""),
]

satirlar = []
def ekle(grup, yol, tur, notu, gosterim=None, tarih=None):
    satirlar.append({"grup": grup, "yol": gosterim or yol, "tur": tur,
                     "satir_veya_kayit": say(yol) if Path(yol).suffix in (".csv", ".json", ".txt") else "",
                     "git_ilk_ekleme": tarih if tarih is not None else git_tarih(yol), "not": notu})
for g, d, t, n in TANIM:
    for y in sorted(glob.glob(d)):
        ekle(g, y, t, n)
if ADOR:
    for g, d, t, n in ADOR_TANIM:
        for y in sorted(glob.glob(str(ADOR / d))):
            rel = str(Path(y).relative_to(ADOR))
            ekle(g, y, t, n, gosterim="dal:claude/adoring-maxwell-q7t60g:" + rel, tarih="2026-11-13 (dal)")
# kaynak_id
sayac = {}
for s in satirlar:
    on = {"G0_SONUC": "R", "G1_KITAP": "K", "G2_DIS_ESKI": "D", "G3_REPO": "P", "G4_GITHUB": "H",
          "G5_151_SON1AY": "Q", "G6_V3": "V", "G8_DIS_ARASTIRMA": "X", "G9_ROBOTIC": "B"}[s["grup"]]
    sayac[on] = sayac.get(on, 0) + 1
    s["kaynak_id"] = f"{on}{sayac[on]:03d}"
alan = ["kaynak_id", "grup", "yol", "tur", "satir_veya_kayit", "git_ilk_ekleme", "not"]
with open("sonuclar/hesap_defteri/kaynaklar.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=alan); w.writeheader(); w.writerows(satirlar)
print(len(satirlar), "kaynak yazıldı")
