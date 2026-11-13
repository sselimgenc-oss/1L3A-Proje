# Bağımsız hakem raporu — ikinci tur (v2 düzeltmeleri + derin geçiş + K6)

Tarih: 2026-11-13. Hiçbir koşu sonucu okunmadı; yalnız karar tabloları, kaynak listesi, yerel klonlar ve açılabilen web sayfaları.
Satır satır gerekçeler: aynı klasörde `hakem_ikinci_ornek.csv` (138 satır: 97 uyumlu, 23 kısmi, 11 uyumsuz, 7 emin değilim).

## 1. Özet hüküm

| Dosya | Satır | Rastgele örnek (seed=11) | Hedefli bakışta bulunan | Hüküm |
|---|---|---|---|---|
| kul_k4_g9_a_v2 | 149 | 12 KOSULACAK: 0 hata. 5 COK_KOLLU sayımı: 4 tam, 1 bir fazla | 3 satırda `.json` katmanı atlanmış, 1 satırda stop cümlesi yanlış | **Kabul, 4 satır düzelt** (105, 156, 209, 440; 135 sayı) |
| kul_k4_g9_b_v2 | 149 | (yeniden örneklenmedi) | önceki istekler yapılmış (663, 571, 670, 593) | **Kabul** |
| kul_k4_g9_c_v2 | 148 | (yeniden örneklenmedi) | önceki istekler yapılmış (875, 876, 755, 78, kol sayıları) | **Kabul** |
| kul_k4_g8_a_v2 | 160 | — | 173 düzeltilmiş; 103 politika (d) ile çelişiyor | **Kabul, 1 satır düzelt** (103) |
| kul_k4_g8_b_v2 | 160 | — | 364, 553, 396, 568, 44, 381/382, 594 yapılmış; 517 mutlak birim politikasıyla çelişiyor | **Kabul, 1 satır düzelt** (517) |
| kul_k4_g8_c_v2 | 159 | K6 10 satır: 8 uyumlu, 2 kısmi | 695, 724, 721, traders.com gerekçeleri yapılmış; 816/818/798 ölçü sorusu | **Kabul, satır düzelt** (81, 728; 816/818 politika 4'e bağlı) |
| derin_bekleyen | 90 | 0/6 hata | 676, 84 K6 adayı | **Kabul** (K6 taşıması hariç) |
| derin_hkf_a | 101 | 0/6 hata, 1 kısmi (162) | 56, 260 K6 adayı; 51 aralık kuralı | **Kabul, satır düzelt** |
| derin_hkf_b | 101 | 0/6 hata | 393, 411 K6 adayı; FARK_YOK 286, 355 zayıf | **Kabul, satır düzelt** |
| derin_hkf_c | 102 | 0/6 hata, 1 emin değilim (802) | EVREN_DISI 10/10 kategori doğru; gerekçe metni şablon | **Kabul** |
| derin_kod_a | 64 | 1/6 hata (377) | 236 politika (d) ile çelişiyor; 9 satır "yalnız TF eksik" | **Satır düzelt** |
| derin_kod_b | 64 | 1/6 hata (742) | 584, 697, 699 "yalnız TF eksik"; 686 etiket | **Satır düzelt** |
| k6_kodsuz | 85 | 0/6 karar hatası, 2 kısmi | 18 K6 satırı: 11 uyumlu, 6 kısmi, 1 uyumsuz (508) | **Satır düzelt** |
| derin_ajan2 | 18 | 18'i de okundu: 0 hata | — | **Kabul** |
| derin_erisim | 126 | 1/6 hata (742), 1 kısmi (721) | EVREN_DISI satırlarında `neden` alanı karara uymuyor | **Satır düzelt** |

Örnekler küçük (dosya başına 6). 6'da 0 hata, gerçek hata oranının %40'a kadar olabileceğini dışlamaz; 6'da 1 hata kabaca %3–%60 aralığı demektir. Hiçbir dosya için "yeniden yap" demiyorum: bulunan hatalar sistematik ama dar (aşağıda dört küme).

Yapısal denetim temiz: her dosyada kimlikler tekil, v2 dosyalarının kimlik kümesi eskisiyle aynı, `ayar` alanlarının hepsi geçerli JSON, KOSULACAK/K6/FARK_YOK satırlarında `evren` dolu.

### Doğrulayabildiklerim ve doğrulayamadıklarım
- B001: yerel klon dosyaları (yalnız okundu). X005: `strateji_listesi.csv` satırı; ayrıca açabildiğim birincil kaynaklar: egx-desk (408, 397), prorealcode (327, 328), oanda.jp (234), mql5 (73), tradingqna (X008:L15#2), StockSharp yerel klonu (X008:L17#4).
- Açamadıklarım: traders.com, medium.com (Cloudflare), bitmex.com, TradingView pine-facade. Bu kaynaklara dayanan satırlarda "liste satırıyla aynı" diyebilirim, "birincil kaynakla aynı" diyemem (ör. 419, 508).
- EVREN_DISI satırlarının çoğunda birincil kaynağı açmadım; karar liste satırındaki kural metnine göre denetlendi.

## 2. A grubu — önceki düzeltme istekleri

Önceki raporun "karar değişmeli" ve "içerik düzeltilmeli" listesindeki satırların hepsi işlenmiş:
- g8_b: 364 → KURAL_YOK (erişilemedi), 553 → KOSULACAK (6 kol yazılmış), 396 `ayar` geçerli JSON listesi, 568 kanıt cümlesi düzeltilmiş, 44/568 `evren` dolu, 381/382 → EVREN_DISI, 594 → K6.
- g8_c: 695/724 "seviye mum kapanışıyla aşılınca sonraki açılış" biçimine çevrilmiş, 721 → EVREN_DISI, 73/98 yeniden değerlendirilmiş, traders.com KURAL_YOK gerekçeleri tek biçim (19 satır).
- g9_a: `kural_tam` baştan yazılmış; 190 → KOSULACAK; pHSL etkin değerleri önceki raporumdaki değerlerle aynı (395–399, 406, 433–439); ichiV1 ailesi düzeltilmiş (137: EMA 3/6/12/24/48/72/96, dosyayla aynı).
- g9_b: 663/571 → KOSULACAK, 670 EWO paydası `low` + `confirm_trade_exit`, 593 TF 15m.
- g9_c: 875/876 → KOSULACAK, 755 → KOSULACAK (g9_a 201 ile aynı yön), 78 stopsuz eşiğiyle tutarlı, kol sayıları dosyayla aynı (714: 34, 728: 21).

### g9_a_v2: 12 KOSULACAK satırı (seed=11)
454, 471, 456, 488, 465, 475, 227, 226, 480, 457, 476, 190. Betikle her dosyanın `buy_params`/`sell_params`, ROI, stoploss, trailing, TF değerleri çıkarılıp `ayar` JSON'uyla karşılaştırıldı: **12/12 satırda fark yok** (456'da 41/41, 457'de 41/41, 454'te 40/40 değer). 226 (mk4) satır satır elle okundu; kaynaktaki hata (ikinci kolun `enter_long`'a yazması) ve ölü çıkış sinyali doğru saptanmış.

### COK_KOLLU kol sayımı (5 satır)
| Satır | Ajan | Sayım | Not |
|---|---|---|---|
| 461 CombinedBinHClucAndMADV9 | 10 | 10 | eşik sınırında, doğru |
| 487 CBPete9 | 10 | 10 | eşik sınırında, doğru |
| 135 ckNSJT_morning | 11 | **10** | `buy_1` kolunun `append` satırı yorumda; karar değişmez |
| 407 BB_RPB_TSLmeneguzzo | 11 | 11 | |
| 410 BigPete | 12 | 12 | `cond0` toplamda yok |

Eşiğin öbür yanı: 8 kollu KOSULACAK satırlarından 399, 433, 437 sayıldı; üçü de 8.

### g9_a_v2'de kalan hatalar
1. **Hyperopt `.json` katmanı uygulanmamış (3 satır).** Freqtrade, strateji dosyasının yanındaki aynı adlı `.json`'u sınıf değerlerinin üstüne yükler. g9_b ve g9_c bunu uygulamış, g9_a uygulamamış:
   - 105 overwatch: etkin `base_nb_candles_buy` 19, `low_offset` 0,903, `ewo_high` 5,775, `ewo_low` −19,765, `rsi_buy` 44; ajan 46 / 0,938 / 2,239 / −8,029 / 64 yazmış.
   - 156 AWATRCT: etkin `base_nb_candles_buy` 51, `low_offset` 0,96, `ewo_lo_limit` −4,8, `rsi_buy_low` 32, `atr_buy` 2,1; ajan 20 / 0,95 / −2,5 / 35 / 1 yazmış.
   - 209 ImpulseMACD: etkin ROI {0: 0,244 …}, stop −0,35, trailing 0,011/0,014; ajan ROI 0,8, stop −0,5 → ATR uyarlaması, trailing 0,01/0,09 yazmış. JSON'a göre stop −0,35 korunur, ATR uyarlaması gerekmez.
   g9_a'da yanında `.json` olan başka satır yok (201'in kopyası AIRA dizininde, yanında json yok; 755'in kopyasının yanında var: iki satırın farklı parametre taşıması doğru).
2. **440 ClucHAnix_hhll:** "pHSL > −0,50 olduğundan ATR uyarlaması gerekmez" yazıyor. Dosyada pHSL yok; `custom_stoploss` taban değeri −0,99. Fiilen stopsuz, ATR(14)×3 uyarlaması yazılmalı. Aynı cümleyi taşıyan diğer 10 satırı kontrol ettim; onlarda HSL −0,10 ile −0,35 arası, doğru.
3. **`kural_tam` içinde kaynak kod parçaları var** (docstring'ler dahil; dosya 372 KB). Talimat "üçüncü taraf kodu kopyalama; kendi cümlen" diyor. İçerik doğru, ama bu dosya repoya girecekse lider karar vermeli (kaynaklar GPL-3).

## 3. FARK_YOK satırları (12)

Kod kaynağı kapsıyor mu: 12/12 evet (sınıf kodlarını açtım). "O ayar gerçekten koşulmuş mu" sorusunun cevabı ikiye ayrılıyor:

| Satır | Sınıf / ayar | Koşu kaydı | Görüş |
|---|---|---|---|
| hkf_a 40 | BtfdGunlukDip varsayılan | v2 1d varsayılan, 314 işlem, elendi | sağlam |
| hkf_a 53 | IbsDonus varsayılan 0,2/0,8 | v2 1d varsayılan, 1.524 işlem, elendi | sağlam |
| hkf_b 507 | D1H1Macd varsayılan | v1 30m/1h WF, 18 aday | sağlam |
| hkf_b 532 | v3 noise-alanı | v3 30m DK_SPX tek ayar, 121 işlem | sağlam (seans kuralı) |
| hkf_b 388, 286 | MaKesisim SMA50/200 long (dış ayar #30) | v1 WF, 6 pencerede seçilmiş | kabul; 286'da kaynak stop aralığı (%5–10) "stop yok" sayılmış |
| hkf_c 903 | MaKesisim SMA10/30 long (#24) | v1 WF, 1 kez seçilmiş | kabul |
| hkf_b 355 | MaKesisim SMA20/50 long (#28) | "WF aday kümesinde, hiç seçilmedi" | **zayıf**: bu ayarın örneklem dışı sonucu yok |
| bekleyen 624 | Donchian 20/20/stop 3 | ızgara noktası | **zayıf**: ayarın kendi sonucu yok |
| hkf_a 76 | Donchian 20/10/2 (varsayılan) | yalnız v1 WF ızgarası; v2 kart ayarıyla koştu | **zayıf** |
| hkf_a 116 | ConnorsEtf rsi4/200/stop 4 | ızgara noktası; v2 r3 ayarıydı | **zayıf**; stop ×4, ön kayıt uyarlaması ×3 |
| hkf_c 894 | IbsDonus 0,1/0,9/stop 3 | ızgara noktası; ajan "özgül kayıtla doğrulanmadı" diyor | **zayıf** |

Talimatın FARK_YOK tanımı "ızgara içi"ni yeterli sayıyor; bu ölçüyle 12'si de geçerli. Ama beş zayıf satırda (355, 624, 76, 116, 894) "test edildi ve elendi" demek, o ayar için bir sonuç olmadan söylenmiş oluyor. Sınıf ve ayar hazır olduğundan bunları KOSULACAK (sınıf + ayar) yapmak ucuz. Öneri; karar liderde. Önceki raporumdaki ortak çekince aynen geçerli: eski koşular kripto13 ve bu turun kapılarıyla yapılmadı.

## 4. K6_STANDART satırları (31 tekil: k6_kodsuz 18, derin_erisim 5 [3'ü aynı satır], g8_b_v2 1, g8_c_v2 10)

20 satır ek 3'e tam uyuyor (eksik yalnız sayısal parametre / MA tipi / TF; tablo değeri doğru). Uydurma tablo değeri görmedim. Sorunlu olanlar:

- **508 (uyumsuz):** Kaynakta eksik parametre yok. Sabit eşikler yazılı (−15,47 / +18,80 bp; ±2σ için −32,61 / +35,93 bp). Ajan bunları kayan 20 pencereli z-skoruyla değiştirmiş; bu kaynak kuralını değiştirir. 196'da (RSRS) örneklem içi seçilmiş sabit eşikler olduğu gibi alınıp KOSULACAK yapılmış; aynı ölçüyle 508 sabit eşikli KOSULACAK olmalı (ya da "eşik tüm örneklemden" diye LOOKAHEAD). bitmex sayfasını açamadım; liste satırına dayanıyorum.
- **496 (kısmi):** SAR değeri tabloya uygun, ama kaynağın öznel ilk stopu (destek / son dip) SAR'la değiştirilmiş ve "kâr al ya da stopu sıkılaştır" seçeneğinden biri seçilmiş. Ek 3 öznel kuralı K6 dışında tutuyor.
- **348, 346 (kısmi):** VisualChart kataloğu yalnız platformun izin verdiği girdi aralığını veriyor (BB katsayısı 0–2, periyot 2–25); kaynak notu "varsayılan yok, doğrudan uygulanamaz". 348'de beş parametrenin beşi tablo ya da orta noktadan. Ek 3'ün harfine uygun ("aralık → orta nokta"), ruhuna sınırda. Aynı kataloğun 347, 349, 350, 351, 352 satırları KURAL_YOK.
- **406 (kısmi):** "SMA veya EMA, 20 ya da 50" → 4 varyant × 2 TF = 8 hipotez. Kaynak bunları raporlamıyor, seçenek olarak sayıyor. Ek 3 "ızgara yok, tek değer" diyor.
- **421, 339 (kısmi):** `ayar` içinde varyant listesi var; hangi hipotezin koşulacağı belirsiz (421: EMA100 filtreli/filtresiz; 339: beş çıkış/stop varyantı).
- **728 (kısmi):** "Heikin-Ashi ortalaması = HA kapanış ortalaması" varsayımı tablo dışı; sayfa açılamadı.
- **81 (kısmi):** Kaynak örneği 4h; "kaynak kendi varsayılanını yazmışsa o kullanılır" → 4h tek hipotez.

### K6'ya alınmamış "yalnız TF / standart parametre eksik" satırları
ILERLEME "derin_kod_a/b sonrası parametre eksikliğiyle KURAL_YOK kalanlar K6'ya alınacak" diyor. g8_c için yapılmış (9 satır), diğerleri için yapılmamış. Birleşik tabloda KURAL_YOK kalan ve ajanın kendi gerekçesi "kural/kod tam, yalnız TF (ya da tablodaki bir periyot) yok" olan satırlar:

**1, 6, 56, 260, 296, 297, 356, 357, 362, 376, 377, 393, 411, 584, 676, 697, 699, 742** (18 satır).
Örnek: 260 (kripto, 1h, RSI 30/70, yalnız RSI periyodu yok), 393 ("SMA9/21 kuralı net ama TF uydurulmaz"), 742 (aynı sayfanın Rule 1'i 710 K6_STANDART).
Dikkat: 362 ve 697 stop-emirli (politika d uyarlaması da gerekir), 376 limit emirli (politika d'ye göre EVREN_DISI olabilir), 377'de "1 tick" tampon var, 411'de kaynak örneği 15m.
Emin olmadıklarım: 51 (aralık verilmiş: periyot 3–5, 30–40, 70–80; 346/348 ölçüsüyle orta nokta K6 olurdu), 84, 358 (ayrıca lookahead_on), 366, 802.

Ek 3 gereği bunlar K6'ya girmezse "hiçbir kod atlanmayacak" kararı eksik uygulanmış olur; girerse BH ailesi yaklaşık 18 × (1–2 TF) kadar büyür.

## 5. EVREN_DISI — kriptoda tek varlık kuralı olarak uygulanabilir olan var mı

30 satıra baktım (rastgele örneklerden 20 + hkf_c'den 10). 25'inde tek varlıkta işlem yolu yok (geniş hisse kesitseli, belirli çift, açılış boşluğu, pip). Tartışmalı olanlar:
- **hkf_a 162:** ana yöntem 15 ülke ETF'i kesitseli, ama kaynak tek-ETF varyantını da veriyor (IBS < 0,2 long, > 0,8 short, 1 gün tut). `dis__ibs-donus` sınıfı `short=True, maks_tutma=1` ile bunu karşılar. EVREN_DISI eksik; KOSULACAK ya da mevcut IBS satırına bağ gerekir.
- **g8_c 798:** SPY ayağı (RSI2 < 40 al, > 80 çık) tek varlık kuralı. 894 (QQQ) ve 40 (S&P) kriptoya taşınırken bu "eşik enstrümana özel" diye dışarıda. Emin değilim.
- **derin_erisim 105:** SPY için "S&P 500 50/200 filtresi" varlığın kendi endeksi; kendi SMA50/200 ile yazılabilir. Emin değilim.
- **kod_a 446:** tek sembol sinyali ve ATR çıkışları kodda tam; dışlama nedeni `top_n` sıralaması. g8_c 816/818'de aynı yapıdaki sıralama "yalnız tahsis önceliği" denip atılmış ve KOSULACAK yapılmış. İki parti iki ölçü.
- 280, 637, 675, 716, 444, 445 (dış endeks filtreli hisse kuralları): endeksi BTC ile değiştirmek kural değişikliği olur; EVREN_DISI savunulabilir.

Kripto kökenli EVREN_DISI yalnız 4 satır (123, 233, 506, 534). 233 ve 534 kripto kesitseli ama özü likiditesi düşük kuyruk / 100 coin'lik dilimler; 13 likit sembolde karşılığı yok.

hkf_c'de 80 EVREN_DISI satırının 75'inde gerekçe üç şablon cümleden biri ("… ve/veya …"); kategori doğru, ama satıra özgü kanıt değil.

## 6. Politikalar partiler arasında tutarlı mı

| Politika | Durum | Çelişen satırlar |
|---|---|---|
| Mutlak birim → EVREN_DISI | çoğunlukla tutarlı | **g8_b 517** (350 pip stop ATR×3'e çevrilip KOSULACAK). Ayrıca pip/puan nedeniyle dışlanıp KURAL_YOK etiketi taşıyanlar: 57, 58, 82, 323, 473, 885, X008:L23#2 (yalnız etiket) |
| Stop-emir → "kapanışla aşılınca sonraki açılış" | 695, 724, 73, 173, 327 tutarlı | **g8_a 103** KOSULACAK ↔ g8_c 98 EVREN_DISI (aynı tür: alış-stop + aynı gün kapanış). **kod_a 236** bar içi limit dolumuyla KOSULACAK ↔ 835 EVREN_DISI |
| Stopsuz eşiği (≤ −0,50) | g9 a/b/c tutarlı | g9_a 440 (yukarıda); 209 JSON'a göre −0,35 |
| COK_KOLLU (≥10 kol) | üç g9 partisinde tutarlı; 87 satır | 135 sayı; X005:686 (~60 girişli Pine) KURAL_YOK etiketiyle |
| Etkin parametre (`.json` katmanı) | g9_b, g9_c uygulamış | g9_a 105, 156, 209 |
| Kaynak varyant listesi | **biçim tutarsız** | 23 satır üç ayrı kodlama kullanıyor: `ayar` JSON listesi (9 satır), `ayar` içinde `*_varyant*` anahtarı (14 satır), `tf` alanında `4h|1d` (25 satır). Mühürden önce her hipoteze ayrı kimlik verilmeli; yoksa BH aile büyüklüğü belirsiz |
| Aralık → orta nokta (ek 3) | tutarsız | 346, 348 orta nokta ile K6; 51, 319, 372 aynı durumda KURAL_YOK |
| Kesitsel sıralamayı atma | tutarsız | 816, 818 atıp KOSULACAK; 446 EVREN_DISI |
| Geleceksiz uyarlama | 287, 310, 629 tutarlı; 157, 169, 678 tutarlı | 678 için emin değilim (canlıda nedensel) |
| Erişilemeyen kaynak | karar tutarlı | **derin_erisim** EVREN_DISI satırlarında (441, 712, 713, 720, 721) `neden` "kaynak erişilemedi" yazıyor; asıl gerekçe `not`ta. derin_erisim birleştirmede en yüksek öncelikli olduğu için nihai tabloya bu yanlış gerekçe geçer. 742'de derin_kod_b'nin "ayna açıldı, yalnız TF yok" bilgisi de böyle eziliyor |

Birleştirme: ILERLEME'deki öncelik kuralını uygulayıp 905 X005 kimliğini tek karara bağlayabildim (KOSULACAK 298, EVREN_DISI 269, KURAL_YOK 189, VERI_YOK 68, YASAK 32, K6 31, FARK_YOK 16, LOOKAHEAD 1, TEKRAR 1). Lider 906 diyor; bir kimlik bu dosyaların dışında (K1/K2) olmalı, doğrulamadım.

## 7. Politika 4 görüşü: kesitsel rotasyon ve pairs

Karar kullanıcıda; aşağıdaki hakem önerisidir.

**Mevcut ön kayıt metnine göre bu bir "uyarlama" değil, kaynak kuralını değiştirmektir.** Gerekçe:
1. Ön kaydın izin verdiği uyarlamalar sayılı ve yazılı: stop yoksa ATR(14)×3, sonraki açılış dolumu, K6 tablosu. Talimat EVREN_DISI'yi tam bu örneklerle tanımlıyor ("hisse kesitsel geniş evren, belirli hisse/ETF çifti").
2. Tek varlık kuralı kriptoya taşınınca yeni parametre gerekmez. Kesitsel kural taşınınca gerekir: 500 hissenin "en iyi ondalığı" 13 sembolde 1,3 varlıktır; "7 ETF'ten en iyi 1" (ikisi tahvil) 13 kriptoda neye karşılık gelir, kaynak söylemez. k, sepet ve güvenli liman bacağı bizim seçimimiz olur; ön kayıt "eksik parametreye keyfi değer verilmez" diyor.
3. Pairs'te çiftin kendisi kuralın özü (KO/PEP, GLD/USO, SPY/QQQ). BTC–ETH'yi biz seçersek bu yeni hipotezdir.
4. 13 sembol yüksek korelasyonlu dar bir kesit; yüzlerce hisseye göre ayarlanmış sıralama kuralları burada zayıf istatistik gücüyle sınanır ve her biri BH ailesini büyütüp diğer adayların eşiğini sıkılaştırır. Arşivde kripto kesitseli zaten var (`pf__kesit_ls`, aday listesinde ayarları duruyor; v3 Donchian ansamblı).

**Önerim:** Varsayılan olarak ~150 satır EVREN_DISI kalsın. Kullanıcı "bunlar da atlanmasın" derse, ek 3'teki gibi **sonuç görülmeden yeni bir ön kayıt eki** yazılarak dar bir katman açılabilir; ek olmadan uyarlama yapılmamalı. Ek için önerdiğim sınırlar:
- Yalnız kuralı **N'den bağımsız yazılabilen** kesitsel satırlar: sıralama ölçüsü yalnız OHLCV/funding'den; seçim oran ya da formülle verilmiş (ör. 160'taki ağırlık w = −(1/N)(R_i − R_m), "üst %30", "medyanın üstü"); kaynakta lookback ve yeniden dengeleme yazılı. Oran → adet çevirimi tek kural: k = max(1, yuvarla(oran × 13)).
- Dışarıda kalır: mutlak "en iyi k / belirli sepet" (558, 814), tahvil/altın/nakit-ETF bacağı kuralın parçası olanlar (505, 506, 422), sektör/büyüklük/temel veri isteyenler (169), likiditesi düşük kuyruğa dayananlar (233, 534).
- Pairs: yalnız **çift seçim yordamı kaynakta yazılı** olanlar (ör. 545 GGR: 12 ay oluşum, en küçük SSD, 2σ giriş) 13 sembolün 78 çiftine uygulanabilir; "en iyi 20 çift" gibi mutlak sayılar yine eşleme ister. Belirli çift kuralları (836, 837, 849, 850, 202) dışarıda kalır.
- Kapılar ek 2'deki portföy kapıları; BH ailesine dahil; ayrı etiket; aynı (lookback, tutma, yön) üçlüsü tek hipotez (TEKRAR).
Bu süzgeçten birkaç on satırın altında aday çıkmasını beklerim; kesin sayıyı çıkarmadım.

Bundan bağımsız olarak şimdi düzeltilmesi gereken: **sinyali tek varlıkta tanımlı olup sıralamayı yalnız kapasite sınırı için kullanan** kurallar (816, 818, 446) tek ölçüye çekilmeli. Bu satırlarda sıralamayı atmak yeni parametre gerektirmiyor; bence KOSULACAK + "uyarlama: kesitsel öncelik atıldı" notu savunulabilir, ama iki partinin iki farklı karar vermesi savunulamaz.

## 8. Düzeltilecek satırlar (toplu)

**Karar değişmeli**
- k6_kodsuz / derin_erisim X005:508 → sabit eşikli KOSULACAK (ya da LOOKAHEAD); K6 değil.
- g8_a_v2 X005:103 → EVREN_DISI (emir tipi/dolum modeli; 98 ile aynı).
- g8_b_v2 X005:517 → EVREN_DISI (mutlak birim) ya da politika "pip stop → ATR uyarlaması"na çevrilip 381/382/721/514 geri alınmalı; ikisi birden olmaz.
- derin_kod_a X005:236 → EVREN_DISI (bar içi limit dolumu) ya da politika (d)'ye yazılı istisna.
- derin_hkf_a X005:162 → tek-ETF varyantı için KOSULACAK / mevcut IBS satırına bağ.
- K6'ya taşınacaklar: 1, 6, 56, 260, 296, 297, 356, 357, 362, 376, 377, 393, 411, 584, 676, 697, 699, 742 (her biri taşınırken politika d ve mutlak birim süzgecinden geçmeli).

**Karar aynı, içerik düzeltilmeli**
- g9_a_v2 B001:105, 156, 209 (`.json` katmanı), 440 (stop → ATR uyarlaması), 135 (kol sayısı 10).
- g8_c_v2 X005:81 (TF 4h), 728 (HA varsayımı açıkça işaretlensin ya da KURAL_YOK).
- k6_kodsuz 406, 421, 339 (koşulacak varyantlar tek tek sayılsın), 496 (öznel stop ikamesi), 346/348 (lider kararı).
- derin_erisim 441, 712, 713, 720, 721 `neden` alanı karar gerekçesiyle değişsin; 742'de derin_kod_b bilgisi korunsun.
- Varyant taşıyan 23 satır + `4h|1d` taşıyan 25 satır: hipotez başına ayrı kimlik.

**Politika kararına bağlı**
- 816, 818, 446 (kesitsel önceliği atma).
- 798, 105, 422 (enstrümana özel eşik / endeks filtresi / tahvil bacağı).
- FARK_YOK zayıf beşli: 355, 624, 76, 116, 894 (KOSULACAK yapılsın mı).
- 51 ve benzeri aralık satırları (orta nokta kuralı herkese mi).
- g9_a_v2 `kural_tam` içindeki kaynak kod parçaları repoya girecek mi.

**Emin olmadıklarım**
- g9_b 678 (LOOKAHEAD mı, geleceksiz uyarlama mı), hkf_c 802 (TF dakika mı), derin_erisim 328 (1h varyantının kaynağı), kod_a 419 (Pine kodu açılamadı), FARK_YOK 286 (kaynak stop aralığı).
