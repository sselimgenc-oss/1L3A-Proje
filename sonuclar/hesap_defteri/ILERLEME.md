# Hesap defteri — İLERLEME (devam noktası)

_Başlangıç: 2026-11-13. Lider: ana oturum. Dal: `claude/funny-euler-ocflt3`._

**Oturum yeniden başlarsa:** bu dosyayı oku → "Durum" tablosunda `bitti`/`denetlendi` olan grupları tekrar yapma →
`bekliyor`/`sürüyor` olanlardan devam et. Ortak ajan kuralları: `AJAN_TALIMATI.md`.

## Amaç
Kullanıcının getirdiği her stratejinin akıbetini kanıtla tek tabloya dökmek (test koşmadan, yalnız okuyarak).
Çıktılar: `kaynaklar.csv`, `ham_satirlar.csv`, `tekil_stratejiler.csv`, `RAPOR.md`, `betikler/`.

## Plan
1. Kaynak envanteri (lider) → `kaynaklar.csv` (`betikler/kaynak_envanteri.py`). Kod kaydı → `ara/kod_kaydi.csv` (`betikler/kod_kaydi.py`).
2. Ham satırlar (alt ajanlar, grup başına bir ajan) → `ara/<GRUP>_ham.csv` + `ara/<GRUP>_NOTLAR.md`.
3. Kod akıbeti (alt ajan G0) → `ara/G0_kod_akibet.csv`, `ara/G0_ayarlar.csv` (521 kodlu strateji × tüm sonuç dosyaları).
4. Tekilleştirme + akıbet birleştirme (lider betiği) → `ham_satirlar.csv`, `tekil_stratejiler.csv`.
5. Adalet kontrolü (B grubunda `adil_test`), çapraz kontrol (belgelerdeki sayılar), öz denetim (40 satır, tohum 20261113).
6. RAPOR.md → commit → PR (main).

## Önemli kaynak notu
`sonuclar/dis_arastirma/` altındaki en güncel dosyalar (906 liste, derin_gecis, tur4_degerlendirme, RoboticAutomations 909)
main'de DEĞİL, birleşmemiş `origin/claude/adoring-maxwell-q7t60g` dalında (2026-11-13). Salt okunur kopya:
`git archive origin/claude/adoring-maxwell-q7t60g sonuclar/dis_arastirma | tar -x -C <scratchpad>/ref_adoring`.
Kanıt yollarında `dal:claude/adoring-maxwell-q7t60g:<yol>` yazılır.

## İlk lider bulguları (dosyadan doğrulandı)
- Kod kaydı: 521 strateji (492 tek-grafik + 29 portföy). v1 evren WF (`sonuclar/evren/2017_gelistirme/wf_evren.csv`) 479'unu,
  v2 eleme 222'sini, v3 eleme 9'unu içeriyor. **26 kodlu strateji hiçbir evren/v2/v3 sonuç dosyasında yok** (v3__* 23 + pf__v3-funding 3).
- v2 eleme: E1 ve E3'ü geçip elenen **73** satır (doğrulandı).
- `stratejiler/ayarlar_d11j_ek.json` ve `ayarlar_d12b_ek.json` yalnız `testler/` içinde okunuyor; araştırma hattının aday ayar
  kümesine (`motor/arastirma/tarama.py::_ayar_listesi`) girmiyor → bu ayarlar koşulmamış olabilir (G4/G5/G0 doğrulayacak).

## Kaynak grupları ve durum
| Grup | Kapsam (birincil kaynak) | ~satır | Ajan | Durum | Ara çıktı |
|---|---|---|---|---|---|
| G0_SONUC | 521 kodlu strateji × tüm sonuç dosyaları (k2/k3, v1 evren, kilit, final, v2, holdout keşif, paper_v2, v3) + ayar kümeleri | 521 | Sonnet | denetlendi | ara/G0_kod_akibet.csv, ara/G0_ayarlar.csv |
| G1_KITAP | veri/kartlar_ham (137 dosya, 810 kart) + aileler/elenenler/kitap_kartlari_eslesme/kodlama d10*-d12a | 810 | Sonnet | denetlendi | ara/G1_KITAP_ham.csv |
| G2_DIS_ESKI | dis_envanter (431), portfoy_adaylari (71), arsiv tv_eleme_dali meta (164+92) | 758 | Sonnet | denetlendi | ara/G2_DIS_ESKI_ham.csv |
| G3_REPO | repo_kodlari (398), repo_raporlari (331), ek_77_strateji.md (77), sg-arge xlsx/md | ~810 | Sonnet | denetlendi | ara/G3_REPO_ham.csv |
| G4_GITHUB | github_g1..g7 (1198) + kodlama_kuyrugu_github + d11f-j + ayarlar_d11j_ek | 1198 | Sonnet | denetlendi | ara/G4_GITHUB_ham.csv |
| G5_151_SON1AY | kakushadze_151 (173) + d12b + son1ay (16) | 189 | Sonnet | denetlendi | ara/G5_151_SON1AY_ham.csv |
| G6_V3 | v3 ham kataloglar (2592; on_eleme kapsar) + tur2/3/6 + adaylar/kartlar/kodlama_v3 | 2592 | Sonnet | denetlendi | ara/G6_V3_ham.csv |
| G8_DIS_ARASTIRMA | ajan1 906 (dal), ajan2 26 (md), karşılaştırma/derin_gecis/tur4 | ~932 | Sonnet | denetlendi | ara/G8_DIS_ARASTIRMA_ham.csv |
| G9_ROBOTIC | RoboticAutomations 909 dosya (dal) + kume_listesi | 909 | Sonnet | denetlendi | ara/G9_ROBOTIC_ham.csv |
| G10_ARSIV | arsiv/* eski projeler (algo-sg, strateji-sg, swing-sg, day-trade-sg, scalp-sg, codex-algo, sg-pano, strateji-test-pano, sg-algo-proje) + haiku dalları; repo_kodlari/raporlari'nın kapsamadıkları | ? | Sonnet | denetlendi | ara/G10_ARSIV_ham.csv |
| Birleştirme | ham → tekil, akıbet | — | lider | bitti | ham_satirlar.csv, tekil_stratejiler.csv |
| Öz denetim | 40 satır, tohum 20261113 | — | lider | bitti (3/40 = %7.5) | ara/oz_denetim.csv |
| Rapor + PR | — | — | lider | RAPOR.md bitti; PR sırada | RAPOR.md |

## Denetim günlüğü (lider: her ajan çıktısından ≥10 satır kaynağa izlenir)
- **G5** (189 satır: H 117, D 51, KOD 15, G 5, F 1): rastgele 12 satır kakushadze_151.csv'ye izlendi → 12/12 tutarlı.
  d12b iddiası lider tarafından doğrulandı: `ayarlar_d12b_ek.json` motor/ ve araclar/ içinde okunmuyor; 7 ayarın modları
  (kesit_ls skor ibs/dusuk_vol/r2_alfa, agirlik orantili; rotasyon agirlik getiri_vol) ne `baglama.BAGLAMA`'da ne ızgarada.
  Nüans: `dusuk_vol` yalnız long rotasyon olarak `pf__rotasyon` BAGLAMA satır 35/40'ta var (L/S hali koşulmadı).
- **G10** (105 satır): 12 örnek kaynağa izlendi → 12/12 tutarlı. Ichimoku iddiası kodla doğrulandı (ızgara kijun 26/52; eski proje 20/60/120 test edilmedi).
  Zayıflık: BENZER kararlarının bir kısmı yalnız docstring'e dayanıyor (ajan beyanı); tabloda işaretli.
- **G9** (909): 10 örnek dosya_listesi'ne izlendi → 10/10. 446 BENZER'in 323'ü "önceki ajan kararı, doğrulanmadı" → tabloda `benzer_dogrulanmadi`.
- **G4** (1198): 12 örnek github_g*.csv'ye izlendi → 12/12. d11j bulgusu bağımsız doğrulandı (ayarlar_d11j_ek.json yalnız testlerde).
  dis_ayarlari'daki d11j kayıtları (59) aday kümesinde → koşuldu; ek dosyadaki 11 koşulmadı.
- **G2** (758): 10 örnek → 10/10. Düzeltme: D002:18 KGT v3 kapsam_disi değil, `onceki__kgt` ile BENZER (portföy kısıtı farkı) — lider_duzeltmeleri.csv.
- **G3** (1446): 10 örnek → 9/10. HATA: P001:135 (gün içi pairs) hedefi daytrade__bant-donus yanlış → pf__pairs BENZER (lider_duzeltmeleri.csv).
  236 BENZER kaynak heuristik eşlemesi (doğrulanmadı). Kuyrukta C önceliğiyle kalıp hiçbir dosyada nedeni yazmayan 30 tv-* satırı
  ajan D yazmıştı → lider kararı: E_KODLANMADI_NEDENSIZ (öncelik notu akıbet değildir).
- **G1** (810): 10 örnek kart JSON'una izlendi → 10/10. 93 kart `ayar:X` önerilmiş ama kart_ayarlari'nda kaydı yok (BENZER).
- **G6** (2603 = 2592 + dal 11): 10 örnek on_eleme/katalogla → 10/10. 435 BENZER doğrulanmadı (docstring). 38 BELIRSIZ (tekrar hedefi çözülemedi).
- **G0** (521): 12 örnek (tohum 20261113) wf_evren/eleme/test'e izlendi → 12/12. A 10, B 485, C 26; yapisal_kapi=evet 73; C 26 (beklenenle aynı).
- **G8** (923 = 906 + ajan2 17): 10 örnek strateji_listesi'ne izlendi → 10/10. Önceki ajanın 'aynı' kararlarının kodla açılan 174'ünden 118'i BENZER çıktı.
  Kesitsel/pairs/seans satırları kullanıcı tanımı gereği H; raporda adalet notu (pf__pairs, pf__rotasyon, daytrade__orb kodda var).
  Eksik: v1_wf'de kalan B satırlarının çoğunda adil_test boş → birlestir.py wf_evren.csv'den (TF sayısı, n_aday) türetir.



## Limit kesintisi — 2026-11-13 ~01:00 UTC (devam için oku)
Tüm alt ajanlar 5 saatlik limite takılıp durdu (yenilenme 05:30 UTC). Ajan işleri kaydedildi; devamda **yeni ajan açma**,
aynı ajana SendMessage ile "kaldığın yerden devam et" gönder (oturum değiştiyse ajan erişilemez → o grubu yeniden başlat;
o zaman ajan mevcut ara dosyayı ve betiği okuyup üstüne devam etsin, baştan yazmasın).
| Grup | ajan kimliği | kesintide durum |
|---|---|---|
| G0_SONUC | a19776b566767384c | betik var (g0_kod_akibet.py), çıktı CSV yok |
| G1_KITAP | a404376c3683c1b48 | yalnız elle_kararlar (263 satır), ham CSV yok |
| G2_DIS_ESKI | a6099a7c8992bb752 | ham 758 satır var, NOTLAR yok (tamamlanmadı) |
| G3_REPO | a382858d1d4359fe4 | yalnız betik (g3_repo.py) |
| G4_GITHUB | ace3771aabc3c77ef | ham 1198 satır + ozet.json var, NOTLAR yok |
| G5_151_SON1AY | (bitti) | denetlendi |
| G6_V3 | a89f889e4a9084c6b | ham 2592 satır + ozet.json var, NOTLAR yok |
| G8_DIS_ARASTIRMA | abfef934e755e32c5 | çıktı yok |
| G9_ROBOTIC | ac679425a8291102b | ham 909 satır var, NOTLAR yok |
| G10_ARSIV | a6add8fc83e9791c8 | yalnız betik (g10_arsiv.py) |
Not: ara/ altındaki NOTLAR'ı olmayan dosyalar TASLAK'tır; lider denetiminden geçmedi.

## Son durum (2026-11-13)
Tüm gruplar denetlendi; birleştirme, öz denetim ve RAPOR.md tamam. Yeniden üretim sırası RAPOR.md §10'da.
Lider düzeltmeleri: `ara/lider_duzeltmeleri.csv`, `ara/lider_birlestir_ile.csv` (837 alt küme katalog satırı);
birlestir.py içinde: BAGLAMA ayarları → sınıf tekili; F yalnız martingale/DCA/ort.düşürme/stopsuz grid; adil_test türetmesi.

## Zamanlanmış kontrol
- 2026-11-13 08:35 TSİ (05:35 UTC): otomatik devam mesajı kurulu (kullanıcı isteği; limit yenilenince devam).
  Devam adımı: bitmiş ara çıktıları denetle → eksik/ölmüş grupları yeniden başlat → birleştir → denetim → RAPOR → PR.

## Commit günlüğü
_(boş)_
