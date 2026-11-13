# G6_V3 NOTLAR (hesap defteri, v3 aday araştırması)

Üretim: `python3 sonuclar/hesap_defteri/betikler/g6_v3.py` (elle: `ara/G6_V3_elle_kararlar.csv`). Çıktı: `ara/G6_V3_ham.csv` (2603 satır), `ara/G6_V3_ozet.json`.

## 1. Kaynak satırı ↔ ham satır
| kaynak_id | dosya | kaynak satır | ham satır |
|---|---|---|---|
| V001 | MASTER_katalog_2026-11.csv | 251 | 251 |
| V002 | asya-siteleri-katalog__b_duzeyi.csv | 50 | 50 |
| V003 | asya-siteleri-katalog__tumu.csv | 135 | 135 |
| V004 | bolgesel-katalog__b_duzeyi.csv | 9 | 9 |
| V005 | bolgesel-katalog__tumu.csv | 137 | 137 |
| V006 | chatgpt_dr_tur1_gunici_kripto.csv | 7 | 7 |
| V007 | chatgpt_dr_tur2_funding.csv | 4 | 4 |
| V008 | chatgpt_dr_tur3_akademik_kismi.csv | 2 | 2 |
| V009 | diger-siteler-derin-21.csv | 21 | 21 |
| V010 | gemini_dr_6bolge.csv | 69 | 69 |
| V011 | gemini_dr_afrika.csv | 8 | 8 |
| V012 | github-backtest-katalog-denetimli__dogrulanan_48.csv | 48 | 48 |
| V013 | github-backtest-katalog-denetimli__gercek_ek.csv | 586 | 586 |
| V014 | github-backtest-katalog-denetimli__tumu.csv | 999 | 999 |
| V015 | github-backtest-katalog-v4__diger_siteler.csv | 66 | 66 |
| V016 | github-backtest-katalog-v4__reddit.csv | 56 | 56 |
| V017 | github-backtest-katalog-v4__sayfa_dogrulamasi.csv | 144 | 144 |
| V901 | dal: bolgesel_son3yil_2026-11.csv | 15 | 4 |
| V902 | dal: cjk_son3yil_2026-11.csv | 17 | 4 |
| V903 | dal: uzakdogu_son3yil_2026-11.csv | 18 | 3 |

- 17 v3 ham katalog = 2592 satır = on_eleme.csv 2592 satır, hepsi bire bir (ham_id çakışması yok, 2592 benzersiz).
- Satır numarası: on_eleme `satir_no` başlık dahil kayıt sırasıdır; `kaynak_satir_no = satir_no - 1` (başlık hariç 1'den). İSTİSNA: gemini_dr_6bolge ve gemini_dr_afrika'da `satir_no` zaten başlıksız 1'den başlar (`kaynak_satir_no = satir_no`). 5+ satır ad/URL karşılaştırmasıyla doğrulandı; betik tüm 2592 satırda URL'yi katalogla karşılaştırır.
- HİZA KAYMASI: v4 `reddit.csv` satır 18-27 (10 satır): on_eleme satırının URL'si katalogdaki başka satıra ait (döngüsel kayma). Betik bu 10 satırı URL'ye göre katalog satırına yeniden hizaladı (not sütununda "hiza düzeltildi"). Ham satırlar yine 1:1.
- Ad farkı: on_eleme `ad` çoğu satırda ajanın kısaltma/çevirisi; `kaynaktaki_ad` katalog sütunundan alındı (repo katalogları: `repo`; `diger-siteler-derin-21`: ad sütunu yok, on_eleme adı kullanıldı). v4 `diger_siteler` 41-44'te on_eleme adları katalogdaki strateji adlarıyla uyuşmuyor (URL uyuşuyor); karar on_eleme'ye göre, not sütununda işaretli.
- `kisa_mantik` katalog satırındaki alanlardan kırpılmıştır (kitap/PDF değil; katalog bizim derlememiz); `aile` (trend/MR/diger) anahtar kelime sezgisidir, kart varsa kartın kategorisinden.

## 2. Dal ek katalogları (V901-V903)
Salt okunur kopya: `dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/`. MASTER_katalog_2026-11.csv dalda v3 ham ile bayt bayt aynı (cmp). 50 dal satırından 39'unun URL/reposu MASTER_katalog (V001) içinde bulundu: **kapsanıyor, ham satır yapılmadı** (bolgesel 11/15, cjk 13/17, uzakdogu 15/18 satır kapsanıyor). Kalan 11 satır strateji değil ("proje bulunamadı", araç, okunmadı, BigQuant negatif bulgu) ve MASTER'da yok: V901:11-14, V902:9,10,11,14, V903:13-15 ham satır yapıldı (D kapsam_disi; V902:10 ML için G). Not: V902:14'ün sütunları kaymış (kaynak dosyada başlık/değer hizası bozuk).
Bu 3 id `kaynaklar.csv`'de yok (lider ekleyecek). `ek_77_strateji.md`, `son1ay_*`, `profesyonel_*` dal dosyaları görev kapsamında değildi, bakılmadı.

## 3. Karar zinciri sayıları (satır bazında, sonraki tur öncekini geçersiz kılar)
- tur1 (on_eleme.csv): kod_yok 818, veri_yok 530, yasak 521, tekrar 388, arac 220, kart 96, belirsiz 19 (=2592).
- tur2 (on_eleme_tur2_kod_yok.csv, 799 satır; hepsi tur1 kod_yok): kod_yok 277, kart 162, belirsiz 103, yasak 95, veri_yok 94, tekrar 46, arac 22. (tur1'de kod_yok kalan 19 satır Gemini ekidir, tur2'ye girmedi.)
- tur3 (on_eleme_tur3.csv 122 = 103 tur2 belirsiz + 19 tur1 belirsiz): tekrar 34, yasak 26, kod_yok 24, kart 17, veri_yok 12, arac 8, belirsiz 1.
- tur3 görev2 (19 satır, hepsi tur2'den): tekrar 9, kart 6, yasak 2, kod_yok 1 (+1 satır listede iki kez geçiyor: tekilleştirildi). Tur2 `kart` → g2 ile tekrar/yasak/kod_yok'a dönenler zincirde görülür.
- SON KARAR dağılımı: yasak 643, veri_yok 635, tekrar 476, kod_yok 321, kart 266, arac 250, belirsiz 1.
- tur6 (veri_yok_etiket_tur6.csv 514): 485 satırı bu 2592 satıra ait (396 tur1-veri_yok + 87 tur2'de veri_yok'a dönen + 2 belirsiz); 29 satırı kart_id anahtarlı (kodlama_v3 veri_yok kartları, ham satır değil). Son kararı veri_yok olup tur6 etiketi olmayan 150 satır "veri_yok" D olarak bırakıldı (not: "tur6 etiketinde yok"). Tur6 etiketine göre `bizde_islenebilir=hayir` → H; evet/bilinmiyor → D veri_yok.
- 266 son-karar `kart` satırından yalnız ilk satırı kart başına bağlandı (ham satır→kart URL/repo/ad eşlemesi; MASTER 14 URL'siz satır elle ad eşlemesi). 154 kart json'u; 22'sinin katalog ham satırı yok (tur1/tur5/tur9 web araştırması kartları): bunlardan 9'u kodlandı (aşağıda) ve katalog satırları bu kodlara `tekrar`/benzer olarak bağlanmıştır.
- REDDEDILENLER{,_tur2,_tur3}.txt ile kart yazılmayan `kart` kararları: D (kart_reddedildi / kaynak_okunamadi / tekrar_kart_yok / ml). REDDEDILENLER_tur9.txt web araştırması içindir, ham katalog satırı yok.

## 4. on_durum dağılımı
| on_durum | n |
|---|---|
| D_KODLANMADI_NEDENLI | 1449 |
| G_ML | 540 |
| H_BIZIM_EVRENDE_UYGULANAMAZ | 392 |
| F_YASAK_TIP | 112 |
| TEKRAR | 49 |
| BELIRSIZ | 38 |
| KOD | 23 |

eslesme:
| eslesme | n |
|---|---|
| YOK | 2096 |
| BENZER | 435 |
| TEKRAR | 49 |
| KOD | 23 |

neden_kodu:
| neden_kodu | n |
|---|---|
| ml | 540 |
| benzer_var | 472 |
| kod_yok | 321 |
| veri_yok | 272 |
| arac_sablon | 250 |
| hisse_kesitsel | 176 |
| tekrar_kart_yok | 72 |
| oncelik_disi | 68 |
| opsiyon | 58 |
| kopya | 49 |
| forex_veri | 47 |
| veri_diger | 37 |
| lookahead | 32 |
| ortalama_dusurme | 26 |
| alt_1dk | 25 |
| (boş) | 23 |
| yasak_diger | 21 |
| orderbook | 17 |
| martingale | 14 |
| onchain | 11 |
| vadeli_emtia | 10 |
| dca | 10 |
| kapsam_disi | 10 |
| haber_duygu | 9 |
| stopsuz_grid | 9 |
| kart_reddedildi | 8 |
| kaynak_okunamadi | 8 |
| kural_belirsiz | 5 |
| makro_takvim | 2 |
| altyapi_yok | 1 |

## 5. Kodlanıp v3 elemesine alınmayan kartlar
- kodlama_v3.csv 76 satır: kodlandi 32, veri_yok 29, tekrar 9, belirsiz 5, altyapi_yok 1. (Liderin "76 kodlanan" ifadesi: 76 kart karara bağlandı, 32'si kodlandı.)
- `sonuclar/v3/eleme.csv` 9 koşu. Kodlanıp koşulmayan: **23** (G0'da C_KODLANDI_KOSULMADI). Nedeni: 22'si aile temsilcisi değil → test bütçesi yalnız 10 aile temsilcisi (DURUM.md:433; aileler_v3.csv); 1'i temsilci ama bekletildi: saatlik-asiri-tepki-tersine__denicola (birincil metin okunamadı, DURUM.md:433 "bekletilir").
- Kodlandı ama katalog ham satırında KOD'a bağlanamayanlar (kartın katalog satırı yok, web kaynaklı): saat-21-23-utc, saatlik-asiri-tepki, adaptivetrend-6s, donchian-ansambl, funding-z90-3gun, btc-gecelik-max10, vol-yonetimli-long, cuma-15, kripto-max (9 kart). Bunların G0 karşılığı kod kaydından gelir; ham satırda KOD yok.
- kodlama_v3 `tekrar` 9 kart: mevcut sınıf çekirdeği karşılıyor denmiş; ham satırda BENZER (fark yazılı, sınıf eşdeğerliği doğrulanmadı).

## 6. "Kod yok ama kural açık" (adalet bulgusu)
321 son-karar kod_yok satırının 10'u metin taramasıyla aday çıktı, elle incelendi; kural katalog/kaynak notunda açık yazılı ama kod yok diye elenenler (6): V014:440, V013:445, V005:4, V005:5, V005:25, V010:19. (V014:440/V013:445 aynı repo README'si ayrıntılı haftalık momentum kuralları; V005:4,5 ZSE/BSE kontrarian-momentum kuralı ama hisse evreni; V005:25 Rankia EMA30-170+PSAR kuralı yazıyla, forex; V010:19 GTAA-5 200g SMA ay sonu.) 4 aday elle çıkarıldı (kural eksik/kavramsal). Tarama başka satırları kaçırmış olabilir (yalnız `neden` metni üzerinden); MASTER'da kural_ozeti dolu kod_yok yalnız V001:89 (kuralı belirsiz).

## 7. Tutarsızlıklar / emin olunmayanlar
- ESDEGER üretilmedi: 435 BENZER satırında hedef sınıf kod_kaydi'ndaki dosya:satırdan bulundu ve docstring'i `fark` sütununa konuldu; kuralları tek tek karşılaştırmadım (otomatik), `fark` ağırlıkla on_eleme gerekçesidir. Liderin "fark test edilmedi" listesi bu 435 satır. Bir kısmı (aynı SMA/Strategy001-005 freqtrade vb.) gerçekte ESDEGER olabilir.
- 38 BELIRSIZ: `tekrar` denmiş ama hedef kod_kaydi'nde çözülemedi (dis_envanter satırı durum=kodlandi ama sınıf adı yok, ör. JT_Pair_trading, ICT 10AM FVG, VolatilitySystem; başka ham repo'ya referanslar; benzer_mevcut boş/yok) + 1 gerçek belirsiz (V011:3).
- KOD kodu: benzer_mevcut'ta kart_id geçen satırlar kodlama_v3 üzerinden sınıfa bağlandı; kart kodlanmamışsa BENZER hedefi kart_id'dir (kod değil) ve not'ta yazar.
- kod_kontrol_tur8.csv "kodda_yok" (11) dediği cuma-15, kripto-max sonradan kodlanmış (kod_kaydi'nde v3__cuma-15-est-tutma, pf__v3-kripto-max-piyango var): tur8 notu bayat.
- F/G ayrımı ve alt tür (martingale/dca/lookahead...) `neden` metninden anahtar kelimeyle; 21 satırda alt tür çıkarılamadı (`yasak_diger`). G_ML regex'i geniş: bazı "ML yasak" metinleri DCA vb. ile karışık olabilir (G öncelikli).
- H nedenleri tur6 gereken_veri'den (hisse_kesitsel = hisse fiyat/temel/endeks; forex_veri 47 satır: Dukascopy forex yok sayılmış, tur6 hükmü).
- AYAR üretilmedi: v3 sınıfları için kart_ayarlari/dis_ayarlari dosyası yok; ayarlar_d11j/d12b_ek ile bağlı v3 satırı yok.
- Envanter dışı: V901-V903 geçici kaynak_id.

## 8. Öz kontrol
Rastgele 10 satır (seed 11) ham_id → kaynak katalog satırı (kaynak_satir_no kaydı) → on_eleme/tur2/tur3/tur6 satırı kanıtına geri izlendi: kimlik sütunu ve karar eşleşti (10/10). DURUM.md:433-434 betik içinde metin doğrulamasıyla (assert) kontrol edilir.
