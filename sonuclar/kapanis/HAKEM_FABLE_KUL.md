# Bağımsız hakem raporu — 970 satırlık kapanış karar partileri

Tarih: 2026-11-13. Kapsam: `kul_k3_g8`, `kul_k4_g8_a/b/c`, `kul_k4_g9_a/b/c` (toplam 970 satır).
Satır satır gerekçeler: aynı klasörde `hakem_kul_ornek.csv` (107 satır).

## 1. Özet hüküm

| Parti | Satır | Rastgele 8'de karar hatası | Rastgele 8'de kısmi kusur | Hüküm |
|---|---|---|---|---|
| kul_k3_g8 | 45 | 0/8 | 1/8 (yalnız politika c) | **Kabul** |
| kul_k4_g8_a | 160 | 0/8 | 1/8 (X005:173) | **Kabul**, 1 satıra yeniden bak |
| kul_k4_g8_b | 160 | 0/8 | 1/8 (X005:396) | **Kabul, şu satırları düzelt** (364, 553, 396, 568) |
| kul_k4_g8_c | 159 | 0/8 | 1/8 (X005:734) | **Kabul, şu satırları düzelt** (695, 724 ve traders.com gerekçeleri) |
| kul_k4_g9_a | 149 | 2/8 (B001:190, 438) | 3/8 (416, 140, 427) | **KOSULACAK satırlarının `kural_tam` alanı yeniden yapılmalı**; kararların çoğu kalabilir |
| kul_k4_g9_b | 149 | 0/8 | 1/8 gerçek (670) + 2 politika | **Kabul, şu satırları düzelt** (663, 571, 670) |
| kul_k4_g9_c | 148 | 1/8 (B001:875) | 2 politika + sayım | **Kabul, şu satırları düzelt** (875, 755, 78) |

Örneklem partide 8 satır; oranlar kaba tahmindir (8'de 0 hata, gerçek hata oranının %30'a kadar olabileceğini dışlamaz). Hedefli bakışlarda bulunan hatalar tabloda ayrıca sayılmadı, aşağıda listeli.

Yapısal denetim (hepsi temiz): her partide girdi satır sayısı = çıktı satır sayısı, kimlik kümeleri aynı, `INCELEME_BEKLIYOR` kalmamış.

### Neyi doğruladım, neyi doğrulayamadım
- B001 (Freqtrade) satırları: yerel klondaki dosyalar açıldı (yalnız okundu, çalıştırılmadı). TF, ROI, stop, giriş/çıkış koşulları dosyadan karşılaştırıldı.
- X005 satırları: `strateji_listesi.csv` satırına kadar izlendi. Birincil kaynağa yalnız yerelde klonu olanlarda gidebildim (freqtrade-strategies: X005:12, 27, 568, 553). Diğer web/GitHub kaynaklarını açamadım; o satırlarda "kural_tam liste satırıyla aynı" diyebilirim, "birincil kaynakla aynı" diyemem.
- **traders.com bu oturumdan da kapalı** (ağ izni yok). Politika c satırlarının içeriğini doğrulayamadım.

## 2. Parti parti bulgular

### kul_k3_g8 — kabul
Sekiz örneğin hepsi yerinde. TF'si "bilinmiyor" olan kaynaklar tutarlı biçimde KURAL_YOK. Tek KOSULACAK örneği (X005:639, haftalık SMA40) kaynakla aynı.

### kul_k4_g8_a — kabul
- X005:27 ve X005:12 birincil dosyadan doğrulandı; parametre, TF, ROI, stop birebir.
- **X005:173 (Dual Thrust) tartışmalı:** gerekçe "dört kaynakta parametre çelişkili". Ama satırın `kaynak_link`'i tek dosya ve o dosyanın seti tam (N=5, K1=K2=0,2, dur-ve-çevir). Çelişki liste satırının birleştirme notundan geliyor. Birincil dosyayı açamadım; emin değilim.
- X005:142 (1/3/12 ay işaret ortalaması) KURAL_YOK sınırda: eksik denen şey pozisyon boyutu, sinyal tam.

### kul_k4_g8_b — kabul, düzeltmelerle
- **X005:553 (TrendRiderStrategy) yanlış:** "alternatif giriş eşikleri kaynakta sayısal yazılı değil" denmiş. Birincil dosya yerelde duruyor (`/tmp/kapanis-src-freqtrade-strategies/user_data/strategies/TrendRiderStrategy.py`, 633 satır, 6 giriş etiketi, koruma sayıları yazılı). Talimat "kural metni eksikse birincil kaynağa bak" diyor; bakılmamış. Doğrusu KOSULACAK ya da çok-kollu politikasına göre.
- **X005:364 yanlış:** tezin yalnız ilk ~100 bin karakteri okunmuş, MA tipi ve stop görülmemiş; buna rağmen KOSULACAK. Doğrusu KURAL_YOK (ya da tez tam okunsun).
- **X005:396:** tek kimlikte 6 varyant = 6 hipotez; ayrıca `ayar` alanı geçerli JSON değil (tek tırnak, `False`).
- X005:44 ve X005:568'de `evren` sütunu boş.

### kul_k4_g8_c — kabul, düzeltmelerle
- X005:695 ve 724: stop-emirli giriş "sonraki açılışta koşulsuz giriş"e çevrilmiş. Bu, kırılım şartını düşürür; kural_tam kaynakla aynı değil. Aynı partide aynı tür emirler (73, 98) EVREN_DISI.
- traders.com satırlarında neden "formül kaynak metninde yok" yazıyor; doğrusu "liste özetinde yok, sayfa açılamadı". Bu partide traders.com kaynaklı 28 KURAL_YOK var.
- TF sütununda motorun desteklediği kesin olmayan değerler: `3h`, `1w`, `1M`, `15m,30m`, `1h,1d`.

### kul_k4_g9_a — `kural_tam` güvenilmez
Kararların yönü çoğunlukla savunulabilir, ama `kural_tam` alanı kodlamaya temel alınamaz. Üç ayrı sistematik hata:

1. **Hyperopt varsayılanı, etkin değer yerine yazılmış.** Freqtrade'de `load=True` parametreler sınıftaki `buy_params`/`sell_params` sözlüğünden yüklenir. Ajan `DecimalParameter(default=-0.08)` değerini yazmış. Dosyadaki etkin `pHSL` değerleri:
   135 → −0,397; 395/396/397/398/406 → −0,178; 399 → −0,25; 433 → −0,23; 434 → −0,35; 435 → −0,10; 437/438 → −0,32; 439 → −0,134; **462 → −0,99** (fiilen stopsuz; ATR uyarlaması gerekir, ajan "stopsuz değil" demiş).
   Aynı hatanın stop dışındaki eşiklerde de olup olmadığını taramadım; olması muhtemel.
2. **Şablon kopyası.** ichiV1 ailesinde (137–140) EMA periyotları 136'dan kopyalanmış: yazılan EMA(2,3,5,8,13,21,34) ve fan EMA5/EMA34; dosyalarda 3/6/12/24/48/72/96 ve EMA12/EMA96. BigZ/BinCluc ailesinde (408–428, 487) aynı "kollar ör.: c12, c11, c0…" metni her satıra yapıştırılmış; 427'de bu yüzden stop cümlesi kendi içinde çelişiyor (hem "SL −0,228 gerçek" hem "SL −0,99 nominal → ATR uyarlaması"; dosyada `use_custom_stoploss=False`).
3. **Çok kollu 46 satır KOSULACAK ama kural yazılmamış.** `kural_tam` "kollar ör." diye birkaç örnek veriyor; KOSULACAK'ın kanıt şartı (kuralın tamamı) karşılanmıyor. 46 satırın 46'sı `emin_degil=evet`.

Karar hatası:
- **B001:190 LOOKAHEAD yanlış** (büyük olasılıkla). Dosyada `pivot_points(informative, window=2)` çağrılıyor (ajan "window=5" yazmış) ve bütün giriş/çıkış koşulları `shift(2)`. Pivot t−2 barı t barıyla teyitleniyor, t anında okunuyor: gelecek veri yok. Geçici pivot bloğu da kaldırılmış. Diverjans bulucunun her dalını koşturmadım; %100 emin değilim. 189'da düz koşul `shift(1)` olduğu için orada LOOKAHEAD doğru. 188, 193–195'i ayrıca doğrulamadım (193–195 varsayılan pencere 5 + `shift(1)`: LOOKAHEAD makul).

### kul_k4_g9_b — kabul, düzeltmelerle
Okunan 6 KOSULACAK dosyasında `buy_params`/`sell_params` doğru alınmış (ör. Inverse: CCI31, StarRise pHSL −0,467). Tek parametre kusuru 670'te (EWO paydası kodda `low`, ajan "kapanış" yazmış; `confirm_trade_exit` süzgeci yazılmamış).
- Parti içi tutarsızlık: 3 kollu NASOS (670) KOSULACAK, 3 kollu MultiMA_TSL3 (663) ve 4 kollu NASOSRv6_private (571) "tek kural değil" KURAL_YOK.
- 593: `tf` 5m yazılmış, dosya 15m (karar YASAK, etkisiz).

### kul_k4_g9_c — kabul, düzeltmelerle
Okunan 5 KOSULACAK dosyası birebir.
- **B001:875 (2Candle) yanlış:** 272 satır, 5 giriş etiketi, bütün eşikler yazılı. "Tek satıra sığmaz" bir KURAL_YOK gerekçesi değil. Doğrusu KOSULACAK. 876 (TwoCandle) büyük olasılıkla aynı; açmadım.
- Kol sayıları şişirilmiş: 728'de "63 buy koşulu" yazıyor, dosyada 21 kol bayrağı var; 714'te "173", dosyada 34. Karar yönünü değiştirmez, kanıt değerini düşürür.
- 78: stop −0,85 "fiilen stopsuz" sayılıp ATR uyarlaması yazılmış; aynı partide −0,5 ile −0,9 arası 10 satırda kaynak stopu korunmuş.

## 3. Beş FARK_YOK satırı

| Satır | Kod kaynağı kapsıyor mu | Koşu gerçek mi | Görüş |
|---|---|---|---|
| g8_a X005:143 (12 ay TSMOM) | Evet (`motor/strateji/dis/d5_ek.py:369-393`) | Evet: v2 1d varsayılan ayar, `sonuclar/evren/v2/eleme.csv:126`, elendi, 33 işlem | **Kabul.** Çekince: v2 evreni "genel" (35 enstrüman), stop ATR×5, oynaklık-ters boyutlama yok |
| g8_b X005:44 (MTF RSI) | Evet (`d9_atlanan_b.py:1079-1100`) | Evet: v2 1d varsayılan, `eleme.csv:87`, elendi, 106 işlem | **Kabul.** Evren yine "genel" |
| g8_b X005:533 (Donchian ansambl) | Evet (`motor/portfoy/stratejiler/v3.py:260-341`) | Evet: `sonuclar/v3/eleme.csv:2`, 13 kripto, 1.942 işlem, elendi | **Kabul.** Kural CXO özetinden; PDF okunmamış |
| g8_b X005:568 (EMASkipPump) | Evet; kaynak dosyayla karşılaştırdım | Kısmen: v1 5m sonucu 12 adaylı walk-forward zinciri; varsayılan ayar tek başına 5m'de raporlanmamış | **Kabul, kanıt cümlesi düzeltilsin.** Talimat "ızgara içi"ni yeterli sayıyor |
| g8_c X005:721 (SMA50/200) | Giriş/çıkış evet (`dis_ayarlari#30`, short=False) | Kısmen: v1 WF aday havuzunda 4h/1d, 6 pencerede seçilmiş; sabit ayarın tek başına sonucu yok | **Sınırda.** Kaynağın stopu var (kapanış−2 puan), test edilen ATR×2. Aşağıdaki tutarsızlık 4'e bağlı |

Ortak not: FARK_YOK'ların dayandığı eski koşular kripto13 + bu turun kapılarıyla yapılmadı (evren, stop çarpanı, WF/tek ayar farkı). Talimatın FARK_YOK tanımını karşılıyorlar; "bu kural bu turun koşullarında test edildi" anlamına gelmiyorlar.

## 4. KURAL_YOK ek bakışı

Rastgele örneğin dışında 17 KURAL_YOK satırına (X005) ve 10 traders.com satırına ayrıca baktım; g9 partilerindeki KURAL_YOK gerekçelerinin tamamını da okudum. 17 satırın 15'inde eksik gerçek (TF yok, eşik aralık halinde, öznel tanım, çift/evren yok). Kolaya kaçma sayılacaklar:
- **g8_b X005:553** — birincil dosya yerelde, bakılmamış.
- **g9_c B001:875** — kural tam, "kompozit" denmiş.
- **g9_b B001:663, 571** — 3–4 kollu, kural tam.
- **traders.com grubu** (g8_c 734, 735, 740, 750, 752; K3 745–747) — eksik denen şey gösterge formülü; sayfada olması muhtemel, sayfa açılmamış.
- g8_a X005:142 ve 173 sınırda.

## 5. Politika görüşleri

Bu beşi kullanıcı/lider kararıdır; aşağıdakiler hakem önerisidir.

**a) Çok kollu Freqtrade sistemleri.** Üç parti aynı tür dosyaya üç farklı şey yapmış; ikisi de tam uymuyor. KURAL_YOK'un tanımı "eksik ya da öznel"; bu dosyalarda eksik yok. KOSULACAK'ın şartı kuralın `kural_tam`'da yazılması ve birebir uygulanması; g9_a 46 satırda bunu yapmamış, 1.000–4.000 satırlık dosyaları kendi kodumuzla birebir yeniden yazmak da doğrulanamaz bir iş. Ön kayıt düzeltmesi "kodlanamayan" kayıtları zaten ayrı sayıyor.
*Öneri:* Üç partide de aynı ayrı kod (`COK_KOLLU`: kural belirli, bu turda kodlanmadı, BH ailesi dışı) kullanılsın; eşik koşudan önce sayıyla yazılsın (önerim: 10+ bağımsız giriş kolu ya da onlarca dallı `custom_exit`), altındaki dosyalar (2Candle, MultiMA_TSL3, NASOS, TrendRider) bütün kolları yazılarak KOSULACAK olsun.

**b) MA tipi yazmayan satırlar.** 364 politika sorusu değil, eksik okuma: KURAL_YOK. 594 gerçek politika sorusu.
*Öneri:* Yalın "MA" ifadesi, kaynak tam okunmuşsa ve başka okuma işareti yoksa, "uyarlama: MA=SMA" notuyla KOSULACAK sayılsın ve bu kural üç X005 partisine aynı uygulansın; ön kaydı harfiyen okumak isterseniz hepsi KURAL_YOK olur, ikisinin ortası olmaz.

**c) traders.com satırları.** Talimat açık: erişilemezse KURAL_YOK, neden "kaynak erişilemedi". Karar kabul edilebilir. Kusur gerekçede: g8_c satırları "kaynakta yok" diyor, bu yanlış bir iddia.
*Öneri:* Karar KURAL_YOK kalsın ama `neden` "kaynak erişilemedi (liste özeti formülü içermiyor)" olarak tekleştirilsin; mühürden önce traders.com ağ iznine eklenip bu ~35 satır bir kez yeniden bakılırsa daha iyi, mühürden sonra eklenemezler.

**d) Bekleyen emir / seans saati.** Tutarsız. 695 ve 724'teki "koşulsuz sonraki açılış" uyarlaması kuralı değiştiriyor; 73 ve 98'deki EVREN_DISI ise yanlış gerekçe kodu (engel evren değil, motorun dolum modeli).
*Öneri:* Stop-emirli girişler tek biçimde "seviye bir mum kapanışıyla aşılınca sonraki açılışta giriş (uyarlama)" olarak KOSULACAK yapılsın (695, 724 bu biçime çevrilsin; 73, 98 aynı ölçüyle yeniden değerlendirilsin); bar içi limit dolumuna ya da seans saatine özünde bağlı olanlar (835, 892, 893, 800, 834) dışarıda kalsın ve nedenleri "emir tipi/dolum modeli" diye yazılsın.

**e) B001:776.** Arşivde EMA50/200 yalnız iki yönlü ve ATR×2 stopla koşmuş. Kaynak long-only ve −%15 sabit stop. Talimat "kodda olmayan yön/çıkış/parametre → FARK_VAR" diyor.
*Öneri:* KOSULACAK kalsın. Yalnız X005:721 ile aynı ölçü uygulanmalı (orada stop farkı görmezden gelinip FARK_YOK denmiş; fark, 721'in stopunun kriptoya taşınamaması).

## 6. Partiler arası tutarsızlıklar

1. **Çok kollu sistemler:** g9_a 46 satır KOSULACAK; g9_b ~27 ve g9_c ~33 satır KURAL_YOK. Aynı aile iki tarafa düşmüş: NASOSRv6 (g9_a 101 KOSULACAK / g9_b 571 KURAL_YOK).
2. **Aynı dosya, iki karar:** `eltoro1_4_simple.py` — g9_a 201 KOSULACAK, g9_c 755 KURAL_YOK (iki kopya birkaç karakter farklı). g9_b 593 `eltoro.py` YASAK.
3. **Etkin parametre okuma:** g9_b ve g9_c `buy_params`/`sell_params` sözlüğünü kullanmış; g9_a parametre varsayılanını.
4. **Mutlak birimli stop (pip/puan/tik):** g8_a 134 EVREN_DISI; g8_b 381, 382 ve g8_c 712, 713 KURAL_YOK; g8_c 721 stop atılıp FARK_YOK.
5. **Emir tipi:** g8_c içinde 73/98/835 EVREN_DISI, 695/724 KOSULACAK (politika d).
6. **"Stopsuz" eşiği:** −0,99/−1 her partide ATR uyarlaması; arası belirsiz: g9_c 78 (−0,85) uyarlama, g9_b 675 (−0,90) ve g9_c'de 10 satır kaynak stopu.
7. **LOOKAHEAD:** g9_a 11, g9_b 2, g9_c 1. g9_a pivot/diverjans ailesini toptan işaretlemiş; en az biri (190) yanlış görünüyor. g9_c 748 aynı aile, açmadım.
8. **Haftalık/aylık TF:** g8 partilerinin hepsi `1w`/`1M`'i 1d'den türetip KOSULACAK yapmış (tutarlı); motor desteği doğrulanmamış. g9 partilerinde `ayar` alanı neredeyse hep boş (120/73/87 KOSULACAK satırında), g8 partilerinde dolu.
9. **FARK_YOK ölçüsü:** 721 (stop farkı var, FARK_YOK) ile 776 (stop farkı var, KOSULACAK).

Tutarlı bulduklarım: TF'si bilinmeyen X005 kaynaklarının hiçbiri KOSULACAK yapılmamış (60 KURAL_YOK, 1 VERI_YOK, 1 YASAK); 1m dosyalar üç g9 partisinde de VERI_YOK (30 satır); DCA açık dosyalar YASAK ya da gerekçeli istisna.

## 7. Düzeltilecek satırlar (toplu)

- **Karar değişmeli:** g8_b X005:364 (→KURAL_YOK), X005:553 (→KOSULACAK/çok-kollu); g9_a B001:190 (→KOSULACAK, teyit edilerek); g9_b B001:663, 571; g9_c B001:875 (ve 876'ya bakılmalı).
- **Karar aynı, içerik düzeltilmeli:** g9_a 135, 137–140, 395–399, 406, 427, 433–435, 437–439, 462; g9_b 670, 593; g8_b 396, 568, 44; g8_c 695, 724 ve traders.com gerekçeleri; g9_c 728/714 türü kol sayıları, 78.
- **Karar politika a–e'ye bağlı:** g9_a'daki 46 çok kollu satır, g9_b/g9_c'deki ~60 "tek kural değil/kompozit" satır, g9_a 201 / g9_c 755, g8_b 594, g8_c 73/98/721.
- **Yeniden bakılmalı (emin değilim):** g8_a X005:173, 142; g9_a 188, 193–195; g9_c 748.
