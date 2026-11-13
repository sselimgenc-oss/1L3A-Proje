# G3_REPO notları

Betik: `sonuclar/hesap_defteri/betikler/g3_repo.py` (yeniden üretir). Elle kararlar: `ara/G3_REPO_elle_kararlar.csv`.

## Kaynak satır sayısı ↔ ham satır

| kaynak_id | dosya | kaynak satırı | ham satır | not |
|---|---|---:|---:|---|
| P001 | stratejiler/ek_kaynaklar/repo_kodlari.csv | 398 | 398 | tam |
| P002 | stratejiler/ek_kaynaklar/repo_raporlari.csv | 331 | 331 | tam |
| P003 | stratejiler/ek_kaynaklar/ek_77_strateji.md | 77 | 77 | #1..#77 tam |
| P006 | arsiv/sg-arge-/strateji_listesi.xlsx | 243 | 243 | ID dolu satırlar (sayfa 244 satır - başlık); hepsi TEKRAR -> P001 |
| P007 | arsiv/sg-arge-/strateji_listesi (2).xlsx | 281 | 281 | 282 satır - başlık = 281; hepsi TEKRAR -> P001 |
| P008 | arsiv/sg-arge-/day_trade_swing_trade_strateji_listesi.md | 65 | 65 | tablo satırları (Denetim/Kaynak grubu tabloları strateji değil, alınmadı) |
| P009 | arsiv/sg-arge-/dpay_trade_swing_trade_strateji_listesi.md | 51 | 51 | tablo satırları |

Toplam ham satır: 1446. P004 (kuyruk 133 satır), P005 (b.csv 88 satır) ve kodlama d10a-e/d12a/pf dosyaları eşleme kaynağıdır, ham satır üretmez; kuyruk'un repo atıflı 109 referansının 109'u eşleşti.

## xlsx ↔ repo_kodlari sayı farkı

- strateji_listesi.xlsx 243 kayıt, strateji_listesi (2).xlsx 281 kayıt; (1)'deki tüm ID'ler (2)'de var, (2) fazladan 38 kayıt içerir (3. tur: A6-016/017, O2-013..016, P3-001.. vb.).
- repo_kodlari liste_xlsx = 281 satır = (2)'nin tamamı (ID ile birebir). Yani repo_kodlari yalnız (2)'yi esas almış; (1) alt kümedir. 281 satırda 280 tekil ad var (AlphaTrend Strategy iki platformda: O1-001 Matriks, B1-002 TradingView).
- liste_md 51 satır, day_trade md 65 tablo satırı: 14 md satırı repo_kodlari'da ayrı satır değil (aynı URL'li satıra katılmış; 4'ü ayrı kural olduğu için BENZER ayrıca değerlendirildi: L82, L103, L104, L105; kalan 10 TEKRAR URL eşlemesiyle).
- dpay md 51 satır = day_trade md'nin 2. ve 3. tablolarıyla aynı strateji/URL (hepsi TEKRAR -> P008). Repo_kodlari yalnız day_trade md'yi kaynak göstermiş; dpay dosyası envanterde ama hiçbir satırı doğrudan kullanılmamış.

## on_durum dağılımı (kaynak başına)

- P001: D_KODLANMADI_NEDENLI=342, F_YASAK_TIP=3, G_ML=8, H_BIZIM_EVRENDE_UYGULANAMAZ=7, KOD=5, TEKRAR=33
- P002: D_KODLANMADI_NEDENLI=109, F_YASAK_TIP=20, G_ML=2, H_BIZIM_EVRENDE_UYGULANAMAZ=5, KOD=31, TEKRAR=164
- P003: D_KODLANMADI_NEDENLI=7, F_YASAK_TIP=4, G_ML=14, H_BIZIM_EVRENDE_UYGULANAMAZ=11, KOD=41
- P006: TEKRAR=243
- P007: TEKRAR=281
- P008: D_KODLANMADI_NEDENLI=4, TEKRAR=61
- P009: TEKRAR=51

## eslesme dağılımı (kaynak başına)

- P001: BENZER=277, KOD=5, TEKRAR=33, YOK=83
- P002: BENZER=62, KOD=31, TEKRAR=164, YOK=74
- P003: AYAR=14, BENZER=3, ESDEGER=2, KOD=25, YOK=33
- P006: TEKRAR=243
- P007: TEKRAR=281
- P008: BENZER=4, TEKRAR=61
- P009: TEKRAR=51

Genel on_durum: D_KODLANMADI_NEDENLI=462, F_YASAK_TIP=27, G_ML=24, H_BIZIM_EVRENDE_UYGULANAMAZ=23, KOD=77, TEKRAR=833
Genel eslesme: AYAR=14, BENZER=346, ESDEGER=2, KOD=61, TEKRAR=833, YOK=190

## DURUM.md sayılarıyla karşılaştırma

- DURUM: rapor 314 strateji / 65 yeni / 54 yasak. Benim sayım (repo_raporlari.csv durum sütunu): 331 satır = 314 + 17 arac_sablon; durumlar: arac_sablon=17, ayar=89, kurala_dokulemez=11, mevcut=80, ml_elendi=3, veri_yok=12, yasak=54, yeni=65 -> yeni=65 ve yasak=54 TUTUYOR.
- DURUM: kod 398 / 44 yeni. Benim sayım: 398 satır; ayar=285, kural_yok=28, mevcut=18, ml=8, veri_yok=9, yasak=6, yeni=44 -> yeni=44 TUTUYOR (liste_xlsx 37, liste_md 6, daytrade_py 1).
- ham `on_durum` sayıları kaynak durumdan farklı çıkar çünkü: tv_listesi 255 satırın 162'i dis_envanter'deki aynı betik olarak TEKRAR (D001:n) yazıldı (G2 karar verir); her satırın kaynak durumu `not` sütununda `kaynak_durum=` ile durur. yasak: 54 rapor satırının 34'ü TEKRAR (dis_envanter yasak_dca/izgara/katlama betikleriyle aynı), 20'si F; kod tarafında 6 yasak: 3 F, 3 TEKRAR.

## Bulgular / tutarsızlıklar

1. **ayar:X (285 kod + 89 rapor) satırlarının çoğunun ayar kaydı yok.** `stratejiler/dis_ayarlari` yalnız tv:/d11j:/kural:/freqtrade:/ek77:/son1ay:/awesome:/jesuistm: kimlikleri, `kart_ayarlari` yalnız kitap kartı kimlikleri taşıyor; repo_kodlari liste_xlsx/liste_md/codex/day-trade/scalp ya da repo_raporlari rapor satırlarına ait HİÇ ayar kaydı yok (ayarlar_d11j_ek / d12b_ek da bu kaynaklara bağlı değil: kaynak_dosya alanları github_g3/kakushadze). Bunların 234'ü kaynakta "heuristik_esleme (anahtar kelime, dogrulanmadi)". Hepsi BENZER + D_KODLANMADI_NEDENLI/benzer_var yazıldı; `fark` sütununda kaynak özeti ile hedef sınıf docstring'i yan yana duruyor. Lider "fark test edilmedi" listesine bunları koymalı.
2. repo_kodlari `kapali-kaynak-sistemler` ailesi ("kural metni yok") altına `Quantified Strategies beşli swing portföyü` (P001:359) konmuş; oysa day_trade md satır 103/104/105 aynı makalenin 3 stratejisinin kurallarını açıkça veriyor (IBS bandı, Turnaround Tuesday, 5-gün düşük). Bu md satırları ayrı BENZER değerlendirildi; P001:359 hâlâ D/kural_belirsiz — yanlış olabilir.
3. ek77 #17 ve #69 için d5_ek.py docstring'i "mevcut ayarlarla aynı" diyor; sınıflar açılınca fark çıktı (EMA200 mum dibi/çıkış/stop; Supertrend EMA20 ek giriş kolu) -> BENZER. ek77 #57 (Carver) için b.csv "carry zaten kodlu" diyor; ama dis__ewmac-carry funding vekili kullanıyor, kaynağın vade-farkı carry'si değil -> BENZER. ek77 #29 ve #68 sınıf kodu açılarak ESDEGER doğrulandı.
4. ek77 #54 (ML4T CME vadeli) hiçbir kodlama/eşleme dosyasında yok; ML olduğu için G_ML yazdım (lider teyit etsin).
5. portfoy_adaylari.csv'de ek77 #25 Clenow satırının `pf_sinif` sütunu boş; ama ek2.BAGLAMA_EK2 (satır 3) + kodlama_pf.csv "kodlandi" var -> AYAR (pf__rotasyon). pf.csv `satir_indeksi` 0 tabanlı csv satırı.
6. pdf_adaylari_csv/codex_py `mevcut:dis__...` satırlarından TradingView id'si taşıyanlar sınıf docstring'indeki pine id'si ile dis_envanter satırına bağlandı (TEKRAR D001:n); codex_py yazılımları (ao_ac_zones, kst_momentum, cci3/cci2, wd_pullback) Python uyarlaması olduğu için BENZER bırakıldı.
7. onceki__ sınıfları (s1, 4s-kirilim, kgt, kapitulasyon) modül docstring'inde swing-sg S1/S2, algo-sg A1/B, KGT v3 kaynağını yazıyor -> ilgili rapor satırları KOD. P002 A2 (ayar:onceki__4s-kirilim) ayar kaydı yok -> BENZER. KMN -> pf__kesit_ls (KOD, baglama satir16).
8. kuyrukta olup kodlanmayan C-öncelikli aileler (özellikle 31 `tv-*` satırı): kodlama dosyasında kaydı yok, kuyrukta da neden yazmıyor; D/kural_belirsiz yazdım, gerekçe: rapor durumu `kural_metni_yok` + kapalı kaynak. Kesin "neden" belgesi yok; E sayılabilir.
9. E_KODLANMADI_NEDENSIZ: bu grupta 0 satır (tüm yeni satırların kuyruk atfı var).
10. portfoy_adaylari.csv `liste8` kaynağı ("8-strateji.md"): `find -maxdepth 4 -name "*8-strateji*"` (repo kökü, sonuclar hariç) sonuç vermedi -> kaynak dosya repoda yok (ek_77_strateji.md de ona link veriyor). liste8-pairs ve liste8-tinycta satırları G2'nin (D002) satırlarıdır; benim ham satırım değil. `arsiv` kaynaklı KMN/KGT satırları repo_raporlari P002:70/P002:69 ile karşılandı.
11. `ayarlar_d11j_ek.json` / `ayarlar_d12b_ek.json`: G3 satırlarının hiçbiri bu dosyalara bağlı değil (kaynakları github_g3_cerceve/kakushadze_151).

## Envanter dışı kaynaklar

- `arsiv/sg-arge-/beniokuortak.md` (44 satır) envanterde yok; strateji tablosu içermiyor, atlandı. Geçici Y-id kullanılmadı.

## Öz kontrol

- Otomatik: P001/P002 729 satırda kaynaktaki_ad kaynak CSV'deki satırla karşılaştırıldı, uyumsuz: 0.
- Rastgele 10 satır (tohum 7) seçildi; ad doğrulaması yalnız P001/P002 için otomatik yapıldı, xlsx/md/ek77 satırları liste_id/URL eşleşmesi ve hedef/kanıt alanı varlığıyla denetlendi, kaynakla tek tek elle karşılaştırılmadı:
- P002:266 "[3Commas] EURUSD Grid Bot - Long Strategy" -> TEKRAR D001:10 (TEKRAR) 
- P001:309 "Trendline Breaks with Multi Fibonacci Supertrend S" -> TEKRAR D001:214 (TEKRAR) 
- P006:Strateji Listesi!4 "Bollinger Prism – NQ reversal (PF 2.78)" -> TEKRAR P001:69 (TEKRAR) 
- P008:L19 "SPY Noise Area + VWAP" -> TEKRAR P001:351 (TEKRAR) 
- P001:99 "Grover Llorens Activator Strategy Analysis" -> TEKRAR D001:93 (TEKRAR) 
- P001:149 "Market Sentiment and an Overnight Anomaly" -> YOK  (H_BIZIM_EVRENDE_UYGULANAMAZ) 
- P007:Strateji Listesi!50 "SPX Trading Strategy for ThinkorSwim" -> TEKRAR P001:115 (TEKRAR) 
- P001:193 "MACD + EMA" -> BENZER swing__macd-sinyal (D_KODLANMADI_NEDENLI) 
- P003:20 "OB5F_LSv2 (OTT bantları, ysdede)" -> KOD dis__ott-bantlari (KOD) 
- P007:Strateji Listesi!146 "RSI Mean Reversion Trading Strategy in Nasdaq100 (" -> TEKRAR P001:211 (TEKRAR) 
- TEKRAR hedefleri (D001:n) dis_envanter'de gerçekten var: True. Sınıf hedefleri kod_kaydi.csv'de: True.
