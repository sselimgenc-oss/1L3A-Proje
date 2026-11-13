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
| G0_SONUC | 521 kodlu strateji × tüm sonuç dosyaları (k2/k3, v1 evren, kilit, final, v2, holdout keşif, paper_v2, v3) + ayar kümeleri | 521 | Sonnet | sürüyor (2026-11-13) | ara/G0_kod_akibet.csv, ara/G0_ayarlar.csv |
| G1_KITAP | veri/kartlar_ham (137 dosya, 810 kart) + aileler/elenenler/kitap_kartlari_eslesme/kodlama d10*-d12a | 810 | Sonnet | sürüyor (2026-11-13) | ara/G1_KITAP_ham.csv |
| G2_DIS_ESKI | dis_envanter (431), portfoy_adaylari (71), arsiv tv_eleme_dali meta (164+92) | 758 | Sonnet | sürüyor (2026-11-13) | ara/G2_DIS_ESKI_ham.csv |
| G3_REPO | repo_kodlari (398), repo_raporlari (331), ek_77_strateji.md (77), sg-arge xlsx/md | ~810 | Sonnet | sürüyor (2026-11-13) | ara/G3_REPO_ham.csv |
| G4_GITHUB | github_g1..g7 (1198) + kodlama_kuyrugu_github + d11f-j + ayarlar_d11j_ek | 1198 | Sonnet | sürüyor (2026-11-13) | ara/G4_GITHUB_ham.csv |
| G5_151_SON1AY | kakushadze_151 (173) + d12b + son1ay (16) | 189 | Sonnet | sürüyor (2026-11-13) | ara/G5_151_SON1AY_ham.csv |
| G6_V3 | v3 ham kataloglar (2592; on_eleme kapsar) + tur2/3/6 + adaylar/kartlar/kodlama_v3 | 2592 | Sonnet | sürüyor (2026-11-13) | ara/G6_V3_ham.csv |
| G8_DIS_ARASTIRMA | ajan1 906 (dal), ajan2 26 (md), karşılaştırma/derin_gecis/tur4 | ~932 | Sonnet | sürüyor (2026-11-13) | ara/G8_DIS_ARASTIRMA_ham.csv |
| G9_ROBOTIC | RoboticAutomations 909 dosya (dal) + kume_listesi | 909 | Sonnet | sürüyor (2026-11-13) | ara/G9_ROBOTIC_ham.csv |
| G10_ARSIV | arsiv/* eski projeler (algo-sg, strateji-sg, swing-sg, day-trade-sg, scalp-sg, codex-algo, sg-pano, strateji-test-pano, sg-algo-proje) + haiku dalları; repo_kodlari/raporlari'nın kapsamadıkları | ? | Sonnet | sürüyor (2026-11-13) | ara/G10_ARSIV_ham.csv |
| Birleştirme | ham → tekil, akıbet | — | lider | bekliyor | ham_satirlar.csv, tekil_stratejiler.csv |
| Öz denetim | 40 satır, tohum 20261113 | — | lider | bekliyor | ara/oz_denetim.csv |
| Rapor + PR | — | — | lider | bekliyor | RAPOR.md |

## Denetim günlüğü (lider: her ajan çıktısından ≥10 satır kaynağa izlenir)
_(boş)_

## Commit günlüğü
_(boş)_
