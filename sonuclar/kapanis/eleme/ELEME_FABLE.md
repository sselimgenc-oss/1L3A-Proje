# G8 koşu listesi elemesi — bağımsız hakem (sonuç görülmeden)

Tarih: 2026-11-13. Gerçek mum verisi açılmadı, hiçbir koşu yapılmadı; kararlar yalnız kural metni, TF, parametre ve kaynak notlarından verildi. Kapsam: `kod_g8_*.py` içindeki VARYANTLAR (anlık görüntü: 433 kayıt) + `g8_mevcut_sinif.csv` (49 satır; çoklu ayarlar açılınca 61 hipotez). Satır satır kararlar: `eleme.csv` (kimlik, sinif, karar, gerekce_turu, gerekce, tf, katman).

## Özet

| | Önce | ÇIKAR | KOŞ |
|---|---:|---:|---:|
| VARYANTLAR (yeni sınıflar) | 433 | 125 | 308 |
| Mevcut sınıf + ayar | 61 | 24 | 37 |
| **Toplam (G8 BH ailesi payı)** | **494** | **149** | **345** |

### Gerekçe türüne göre ÇIKAR dağılımı

| Tür | Kayıt | Tahmini CPU dk |
|---|---:|---:|
| a) Yapısal: kapı 2 (≥200 işlem) geçilemez | 49 | 98 |
| c) Kaynağın büyük varyant listesi → temsilci | 69 | 160 |
| b) Yakın/birebir kopya | 26 | 54 |
| d) Gereksiz ikinci TF | 2 | 8 |
| g) emin_degil + düşük kaynak kalitesi | 2 | 15 |
| e) Kaynağa sadık değil | 1 | 2 |
| Toplam | 149 | 337 |

f) "kriptoda anlamsız" tek başına hiçbir kaydı çıkarmadı (495 sezonsal kuralında a ile birlikte ek gerekçe). Takvim kuralları (74, 611, 519, 501) lider daha önce KOSULACAK kabul ettiği ve işlem sayıları yeterli olduğu için kaldı.

### Süre ve BH etkisi

- Süre modeli (kayıt başına kapı 6, B=100.000; verilen 2–10 dk aralığı TF'ye yayıldı): 1d/1w 2 dk, 6h–8h 2,5, 4h 3, 2h–3h 3,5, 1h 5, 30m 6, 15m 8, 5m 10 dk.
- Önce: 1525 CPU dk ≈ 6.4 saat (4 çekirdek). Sonra: 1188 CPU dk ≈ 5.0 saat. Kazanç: 337 CPU dk ≈ 1.4 saat duvar süresi (≈ %22).
- Dürüst not: çıkarılanların 132/149'i günlük/haftalık (en ucuz) kayıt; süre kazancı sınırlı. Sürenin asıl yükü kalan 44 adet 5m/15m kaydında (410 CPU dk, kalanın %35'i); bunlar ayrı fikirler olduğu için sonuçtan bağımsız gerekçeyle çıkarılamadı.
- Asıl kazanç BH ailesinde: G8 payı 494 → 345 hipotez (−%30). Yalnız G8 ailesi olsaydı en küçük p için BH eşiği q/m = 0,10/494 = 0.000202 → 0,10/345 = 0.000290 (≈ 1.43 kat gevşer). Gerçek aile K1–K5 ve G9'u da içerir; oran o toplamda daha küçük olur ama yön aynıdır.
- Çıkarılan 49 "a" kaydı zaten kapı 2'den geçemeyecekti; bunları koşmak yalnız aileyi büyütüp gerçek adayların BH eşiğini sıkılaştırırdı.

## Ölçütler (nasıl karar verildi)

**a) İşlem sayısı kaba hesabı.** Evren 13 USDT perp, geliştirme dönemi ~2019/20 → 2025-11-07; listelenme tarihleri yüzünden ortalama ~5,5 yıl/sembol ≈ 70 sembol-yıl (≈ 26.000 günlük mum, ≈ 3.700 haftalık, ≈ 860 aylık mum). 200 işlem = sembol başına yılda ≥ 2,9 işlem. Merkez tahmin ≤ ~100 işlem ise ya da yapısal üst sınır varsa (haftalık/aylık bar, 250+ gün ısınma, çelişen koşul birleşimi) ÇIKAR; 100–200 arası "sınırda" sayıldı ve başka gerekçe yoksa KOŞ bırakıldı (belirsizse KOŞ kuralı).

**b) Kopya.** Yalnız giriş + çıkış + yön + TF aynı olup fark ≤/<, MA tipi, RSI ortalama tipi, tek basamak parametre ya da fiilen bağlamayan ek koşul olduğunda. Arşivde (G0) elenmiş sınıfa "parametre yakınlığı" tek başına gerekçe yapılmadı: liderin önceki kararı ("FARK_YOK ayarının kendi sonucu yok") korunup yalnız bu turun kendi içindeki kopyalar birleştirildi.

**c) Varyant listeleri.** Kaynağın kendi önerdiği/ana varyantı varsa o; yoksa bir hızlı + bir yavaş temsilci. Seçim sonuçtan bağımsız (ızgara ortası/uçları, kaynağın "en iyi" beyanı, kod varsayılanı).

**d) İkinci TF.** K6 "4h|1d" çiftleri ön kayıt ek 3 gereği iki hipotez; yalnız 1d kaydı kopya (b) ya da kapı 2 engelli (a) olduğunda ya da kaynak başka TF'yi işaret ettiğinde tekine indirildi. Kaynağın TF ipucu vermediği ve iki TF'de de yeterli işlem beklenen ~22 çift iki TF ile kaldı (aşağıda "isteğe bağlı ikinci dalga").

**e/g)** "Yaklaşık" işaretliler (60, 629) sapma küçük olduğu için kaldı (60'ta yalnız TF sayısı azaltıldı); 655 a ile çıktı. emin_degil tek başına gerekçe yapılmadı; yalnız kaynak kuralı bozuk/uydurma olduğunda (571, 630, 391).

## ÇIKAR listesi (türe göre)

### a) Yapısal: kapı 2 (≥200 işlem) geçilemez — 49 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:136#v1 | 1d | Haftalık 20 hafta kapanış kanalı: yılda ~0,5-1 kırılım/sembol → ~35-70 işlem. |
| X005:141#v1 | 1d | Aylık kapanış x 10 aylık SMA: yılda ~0,7-1 giriş/sembol → ~50-70 işlem. |
| X005:147#v1 | 1d | Tüm zaman zirvesi + 10xATR iz stopu: pozisyon aylarca/yıllarca taşınır, yeniden giriş yeni zirve ister → sembol başına toplam 3-6 işlem (~40-80). |
| X005:296#v2 | 1d | ROTT: VAR uzunluğu 1000 bar → 1d'de 1000 gün (~2,7 yıl) ısınma verinin yarısını yer; %7 OTT bandı çok yavaş → çok az işlem. 4h kaydı (#v1) kalır. |
| X005:367#v1 | 1d | Haftalık SMA5/SMA50 (%1 bant): 50 hafta ısınma + yılda <0,5 geçiş → ~20-30 işlem. |
| X005:375#v1 | 1d | RSI14(basit)<25 → >75: yılda ~1,5 olay/sembol → ~100-130; ayrıca (b) X005:215/213'ün eşik kopyası ve (g) kaynak açılamadı + emin_degil. |
| X005:384#v1 | 1d | Haftalık %K(50) 20 seviyesini yukarı kesiş: 50 hafta ısınma, olay ayı piyasası dibinde bir kez → ~20-40 işlem. |
| X005:427#v1 | 1d | Pozisyon yalnız ay sonunda güncellenir (kapanış>EMA150): yılda ~1 giriş/sembol → ~70-90 işlem. |
| X005:438#v1 | 1d | Haftalık SMA20 + haftalık MACD: yılda ~1,3 giriş/sembol → ~80-100 işlem. |
| X005:448#v1 | 1d | Çelişen birleşim: kapanış>SMA216 iken RSI(18)<31 VE kapanış<BB(37,2) alt bandı; günlükte yılda <0,5 olay/sembol → ~20-35 işlem. |
| X005:454#v1 | 1d | SMA9/SMA21 kesişimi VE son 5 barda RSI14≤30 (ayna ≥70): kesişim dipten 8-15 gün sonra gelir, 5 bar penceresine nadiren düşer → yılda <0,5/sembol/yön (~≤70). |
| X005:495#v1 | 1d | Yılda tek giriş (16 Ekim–20 Nisan sezonu) → en çok ~70-85 işlem; ayrıca (f) hisse senedi "Sell in May" takvim anomalisi. |
| X005:508#v2 | 8h | Fonlama ±2σ eşiği (−32,61 / +35,93 bp, BitMEX XBTUSD dağılımından): Binance fonlamasında bu uç değerler çok nadir (tavan civarı) → <100 işlem; (c) kaynağın ikinci varyantı. #v1 (±1σ) kalır. |
| X005:544#v3 | 1d | BB(50) alt bandı yukarı kesiş → üst bandı aşağı kesişte çıkış döngüsü: yılda ~1,3/sembol → ~90. (c) Kaynağın 4 N varyantından temsilci #v1 (N=10) kalır. |
| X005:544#v4 | 1d | BB(250): 250 gün ısınma + yılda <0,5 döngü → ~30 işlem. |
| X005:606#v1 | 1d | Aylık bar (SMA 10 ay + RSI2): toplam ~860 aylık mum; yılda ~1 işlem/sembol → ~70. |
| X005:639#v1 | 1d | Weinstein 40 haftalık SMA yukarı kesişi: yılda ~0,7/sembol, 40 hafta ısınma → ~40-50 işlem. |
| X005:655#v1 | 1d | Haftalık 52 hafta zirve kırılımı, +%300 hedef / 24 hafta dip çıkışı: yılda ~0,5/sembol → ~35 işlem (ayrıca "yaklaşık" işaretli). |
| X005:659#v1 | 1d | kapanış>SMA200 VE ADX<20 VE kapanış<BB alt bandı: yılda ~0,9 olay/sembol → ~60-100 işlem. |
| X005:706#v2 | 1d | 2,5σ dışı kapanış → içeri dönüş; çıkış üst 2,5σ aynası: yılda ≤1,5 döngü → ~100. (c) Temsilci #v1 (2σ) kalır. |
| X005:706#v3 | 1d | 3σ dışı günlük kapanış çok nadir: yılda ~0,3/sembol → ~20-30 işlem. |
| X005:737#v1 | 1d | Aylık kapanış x SMA(8 ay) dur-ve-çevir: yılda ~1 çevirme/sembol → ~70 işlem. |
| X005:751#v1 | 1d | "Yükseliş trendi" (zirveden %20 geri çekilmeyle biter) içinde günlük RSI14 30'u aşağı kesmeli: kriptoda RSI<30, %20 düşüşten önce nadiren gelir → yılda ≤0,5-1/sembol (~35-70). |
| X005:818#v1 | 1d | kapanış>SMA50>SMA150 iken kapanış ≤ BB(21,2) alt bandı VE RSI3<30: alt bandın SMA50 üstünde olması gerekir → yılda ~0,5/sembol (~35). |
| X005:876#v1 | 1d | 5 gün üst üste SMA200 üstü teyitli giriş: yılda ~1,2/sembol → ~85; ayrıca X005:395#7 (kapanış x SMA200) kuralının teyitli yakın kopyası. |
| X005:880#v1 | 1d | Kapanış > SMA100 + 3σ kırılımı: yılda ≤1/sembol → ~50-70 işlem. |
| X005:416#v1 | 1d | Günlük RSI(60) < 5 koşulu pratikte hiç oluşmaz (60 periyotluk RSI 20'nin altına bile nadiren iner) → ~0 işlem; kapı 2 imkânsız. |
| X005:643#v1 | 1d | z20≤-2 VE RSI<40 VE ADX<20 VE 52 hafta zirvesine ≤%30 uzaklık VE 52 hafta dibine >%5: yılda ~0,7/sembol → ~50 (iyimser 100). Ayrıca hisse tarama filtreleri (52 hafta, PER) kalıntısı. |
| X005:726#v1 | 1d | Haftalık iki bacaklı RSI (17/5) + SMA40/10 hafta: 40 hafta ısınma, yılda ≤1,5-2 giriş/sembol → ~90-120 işlem; haftalık yapı. |
| X005:47 | 1d | SMA100/300 durum kuralı: 300 gün ısınma, yılda ~0,5 geçiş → ~25-40 işlem. |
| X005:119 | 1d | SMA100/400: 400 gün ısınma, yılda <0,5 kesişim → ~15-30 işlem. |
| X005:128 | 1w | Haftalık EMA10/40 kesişimi: yılda <0,5/sembol → ~20-30 işlem. |
| X005:193 | 1d | SMA20/120 long kesişimi (yalnız kesişim olayında giriş): yılda ~1,3/sembol → ~90. |
| X005:270#a3 | 1d | EMA50/100 long kesişimi: yılda ~1-1,5/sembol → ~70-100 (ayrıca X005:307 ile aynı ayar). |
| X005:270#a4 | 1d | EMA100/200 long kesişimi: yılda ~0,6/sembol → ~40. |
| X005:307#a1 | 1d | EMA50/100 long: ~70-100 işlem. |
| X005:307#a2 | 1d | EMA50/200 long (altın haç): yılda ~1,1/sembol → ~70. |
| X005:307#a3 | 1d | EMA100/200 long: ~40 işlem. |
| X005:383 | 1w | Haftalık RSI(15)<30: yılda ~0,3/sembol → ~20 işlem. |
| X005:389 | 1d | SMA100/200 iki yön: yılda ~0,8-1,2 çevirme/sembol → ~55-85. |
| X005:396#a1 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:396#a2 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:396#a3 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:396#a4 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:396#a5 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:396#a6 | 1d | Donchian L=50/150/200 günlük kırılım, çıkış aynı L günlük dip (long): L=50 için yılda ~1,3/sembol (~90; arşivde koşulan 55 ayarının da yakın kopyası), 150/200 için <0,5 → kapı 2 geçilemez. |
| X005:838 | 1d | Donchian 100 iki yön dur-ve-çevir: yılda ~1,2 çevirme/sembol → ~85. |
| X005:874 | 1d | Donchian 250 long: 250 gün ısınma, yılda <0,5 kırılım → ~20-30. |
| X005:875 | 1d | Donchian 100 long: yılda ~0,8/sembol → ~55. |

### c) Kaynağın büyük varyant listesi → temsilci — 69 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:138 (6 varyant: #v1, #v2, #v4, #v5, #v7, #v8) | 1d | Kaynağın 8 tutma süresinden (olay çalışması; kaynak sonucu kendi beyanıyla olumsuz, önerilen varyant yok) 2 temsilci kalır: 5 gün (#v3) ve 30 gün (#v6). Giriş hepsinde aynı (SMA10/50 yukarı kesiş). |
| X005:222#v2 | 4h | Stop varyantı B (iki önceki mum dibi) A'nın küçük parametre türevi; A (#v1) kalır. |
| X005:287#v2 | 2h | Sayfa TF listesi 1h/2h/4h; 2h ara değer. 1h (#v1) ve 4h (#v3) kalır. |
| X005:294#v2 | 15m | İz stop %3 yalnız başlık yorumunda; kodun varsayılanı %7 (#v1) kalır. |
| X005:306 (32 varyant: #v1, #v2, #v3, #v4, #v5, #v6, #v7, #v8, #v10, #v11, #v12, #v13, #v14, #v15, #v16, #v18, #v19, #v20, #v21, #v22, #v23, #v24, #v25, #v26, #v28, #v29, #v30, #v31, #v32, #v33, #v34, #v36) | 1d | Kaynağın 36 kuralından (kısa 1/2/5 x uzun 10..60 x bant 0/%1) temsilci 2 kayıt kalır: #v17 (2/30, bant 0; ızgara ortası) ve #v35 (5/60, bant 0; yavaş uç). Bant ve fiyat-x-MA biçimleri X005:395#1/#2/#7, 481, 265 ile zaten temsil ediliyor. BH ailesi şişmesi. |
| X005:339 (8 varyant: #v1, #v2, #v5, #v6, #v7, #v8, #v9, #v10) | 4h+1d | Kaynağın 5 çıkış varyantından kaynağın kendi "en iyi" dediği v2 (çıkış ort−2σ) kalır: #v3 (4h), #v4 (1d). Diğerleri aynı girişin çıkış/kâr-al/stop türevi. |
| X005:373#v2 | 1d | Eşik 25 Pine varsayılanı; tezde test edilen ana değer 20 (#v1) kalır. |
| X005:395 (7 kural: #3, #4, #5, #6, #8, #9, #10) | 1d | JSE VMA bant ailesinin 10 kuralından 3 temsilci kalır: #1 (1/50, bant 0), #2 (1/50, bant %1; bant fikrinin temsilcisi), #7 (1/200, bant 0). 150/200 uzun MA'lı diğerleri birbirinin parametre kopyası ve yılda ~1-2,5 giriş/sembol ile kapı 2 sınırının altında/üstünde (a). |
| X005:405#v3, X005:405#v4 | 4h+1d | Kaynağın "agresif" 5/95 yan varyantı; ana varyant 10/90 1d (#v2) kalır. |
| X005:406 (4 varyant: #v5, #v6, #v7, #v8) | 4h+1d | MA±1σ dönüş: EMA varyantları SMA varyantlarının (#v1-#v4) MA tipi kopyası; 4 kayıt (SMA20/SMA50 x 4h/1d) kalır. |
| X005:540 (4 varyant: #v1, #v3, #v5, #v7) | 1d | Kaynağın 8 varyantından (TSMOM/SMA x N 10/50/100/200) temsilci: TSMOM N=50 (#v2) ve N=200 (#v4). SMA kolu X005:395/306/481 ile aynı kural (b). |
| X005:60#v1, X005:60#v4 | 15m+1d | Kaynak 4 TF öneriyor (15m/1h/4h/1d), ana TF yok; kayıt ayrıca "yaklaşık". İki orta TF (1h #v2, 4h #v3) temsilci kalır. |

### b) Yakın/birebir kopya — 26 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:56#v2 | 1d | 1d RSI14 30/70 long: X005:215 ile aynı giriş/çıkış (yalnız stop %8 ↔ ATRx3). K6 4h kaydı (#v1) kalır (d). |
| X005:219#v1 | 1d | X005:829 (BB20 alt/üst bant dur-ve-çevir) ile yalnız periyot 25↔20 farkı; aynı karşı-bant mantığı. |
| X005:234#v2 | 1d | 1d SMA20/60 long kesişimi: mevcut X005:355 (SMA20/50 long, ATRx3) ile yalnız 50→60 farkı; ayrıca ~2/yıl/sembol ile kapı 2 sınırında. 4h kaydı (#v1) kalır. |
| X005:253#v1 | 1d | X005:108 ile aynı işlem yolu: RSI(2)≤5 iken kapanış<SMA5 koşulu zaten sağlanır; tek fark ≤/< . Sınıf X005:594 (eşik 10, kripto kaynağı) ile koşmaya devam eder. |
| X005:288#v1 | 1d | X005:706#v1 (günlük BTC tezi, kripto kaynağı) ile birebir: alt bandın altından içeri dönüşte al, üst bandın üstünden içeri dönüşte çık. Temsilci 706#v1. |
| X005:291#v1 | 1d | X005:484 ile aynı kural (RSI14 30 yukarı kesiş al / 70 aşağı kesiş sat, ATRx3); tek fark RSI ortalama tipi (basit ↔ Wilder). |
| X005:306#v9 | 1d | (S=1,L=50,bant 0) = X005:395#1 ile birebir (kapanış x SMA50 long/flat). |
| X005:306#v27 | 1d | (S=5,L=20,bant 0) = mevcut X005:265 (SMA5/20 long, ATRx3) ile birebir. |
| X005:366#v2 | 1d | X005:194 (mevcut sınıf swing__macd-sinyal, long, ATRx3) ile birebir 1d MACD kesişimi; tek temsilci 194. 4h kaydı (#v1) kalır. |
| X005:393#v2 | 1d | 1d SMA9/21 long kesişimi: mevcut X005:270 (EMA 9/21 long, 1d, ATRx3) ile yalnız MA tipi farkı. K6 4h kaydı (#v1) kalır (d). |
| X005:405#v1 | 4h | 4h RSI2 10/90 + MA200 + SMA5 çıkışı: X005:7 (3h, aynı eşikler) ile neredeyse aynı; kaynakta 1d ana, 4h alternatif (d). Ana varyant #v2 kalır. |
| X005:407#v1 | 1d | X005:216 ile aynı kural: BB(20,2) alt bandı altı al, orta banda dönüşte çık (üst bant çıkışı fiilen hiç devreye girmez), aynı ATRx3 stop. |
| X005:417#v2 | 1d | X005:268 ile birebir (1d, BB20/2σ iki yön, orta bant çıkışı, ATRx3). 4h kaydı (#v1) kalır. |
| X005:421#v1 | 4h | X005:366#v1 ile birebir (4h MACD 12/26/9 kesişimi, long, ATRx3; ema_filtre yok). EMA100 filtreli #v3/#v4 kalır. |
| X005:421#v2 | 1d | X005:194 (mevcut sınıf) = X005:366#v2 = X005:483 ile birebir (1d MACD kesişimi long, ATRx3). |
| X005:540#v6 | 1d | SMA kuralı N=50 = X005:395#1 ile birebir (kapanış>SMA50 long/flat). |
| X005:540#v8 | 1d | SMA kuralı N=200 = X005:395#7 ile birebir (kapanış>SMA200 long/flat). |
| X005:544#v2 | 1d | X005:706#v1 / 288 ile birebir (BB20/2σ alt bandı yukarı kesiş al, üst bandı aşağı kesiş çık). |
| X005:608#v2 | 1d | #v1 ile yalnız SMA 200↔220 farkı; aynı işlem yolu. |
| X005:638#v1 | 1d | X005:108'in parametre kopyası (RSI2≤5 + SMA200; yalnız çıkış SMA10/20 gün ve stop 2,5 ATR farkı). |
| X005:828#v1 | 1d | X005:217 ile aynı; tek fark 365 günlük azami tutma (fiilen bağlamaz). |
| X005:830#v1 | 1d | X005:217 ile birebir (kapanış<alt bant al, kapanış>üst bant çık, ATRx3). |
| X005:269 | 1d | Kapanış x EMA50 long/flat: X005:395#1 (kapanış x SMA50) ile yalnız MA tipi farkı. |
| X005:392 | 1d | X005:395#7 (kapanış x SMA200 long/flat, bant 0) ile birebir; tek kimlik 395#7. |
| X005:483 | 1d | X005:194 ile birebir aynı sınıf+ayar (swing__macd-sinyal 12/26/9, long, ATRx3). |
| X005:624 | 1d | X005:607 (Donchian 20/20 iki yön) ile yalnız stop modu farkı (ATR3 ↔ kanal); zaten bagli_kimlik ile aynı sınıf ayarına bağlı. |

### d) Gereksiz ikinci TF — 2 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:684#v2 | 30m | Kaynak 15m ve 30m veriyor; kanıt zayıf (1 aylık, maliyetsiz test; emin_degil) → tek TF (15m, #v1) yeter (g). |
| X005:802#v2 | 1d | Kaynak "büyük olasılıkla dakika" grafiği; 1d kaynağın TF'sinden en uzak ve RSI14<30 girişleriyle ~2/yıl/sembol (kapı 2 sınırı). 4h (#v1) kalır. |

### g) emin_degil + düşük kaynak kalitesi — 2 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:571#v1 | 5m | Kaynak kuralı kendi içinde bozuk: çıkış bandı çelişkili (hiç tetiklenmez), giriş EMA12/EMA26 oranının dar bir hyperopt aralığı ([-1,416%, -1,176%]); emin_degil. Fikir değil, optimizasyon kalıntısı. |
| X005:630#v1 | 1h | Şablon-üretimli (LLM) kod havuzundan çok faktörlü skor (ağırlıklar 1,1/0,4/0,4 gerekçesiz), backtest kanıtı yok, emin_degil. |

### e) Kaynağa sadık değil — 1 kayıt

| Kimlik | TF | Gerekçe |
|---|---|---|
| X005:391#v1 | 1d | Kaynak yalnız "güven 0,8/0,6" skor ağırlıkları veriyor; "EMA kesişimi VEYA RSI<30" ikili kuralı bizim varsayımımız (emin_degil) → kaynağa sadık değil; parçaları (EMA20/50, RSI 30/70) başka kayıtlarda ayrı ayrı koşuluyor. |

## KOŞ kalıp dikkat isteyenler

| Kimlik | Not |
|---|---|
| X005:5#v1 | K1 (MacdEmaS0005) ile aynı hipotez: koşu listesinde tek kimlik (çift kayıt varsa G8 kaydı düşer). |
| X005:74#v1 | Takvim kuralı (hisse kökenli) ama lider takvim kurallarını KOSULACAK kabul etmişti; işlem sayısı yeterli → KOŞ. |
| X005:83#v1 | K2 sınıfıyla aynı hipotez: koşu listesinde tek kimlik (çift kayıt varsa G8 kaydı düşer). |
| X005:108#v1 | 253 / 638 ile aynı kuralın tek temsilcisi. |
| X005:138#v3 | 138 tutma süresi temsilcisi. |
| X005:138#v6 | 138 tutma süresi temsilcisi. |
| X005:144#v3 | Sınırda (a): EWMA 32/128 ~2 çevirme/yıl/sembol ≈ 140 işlem tahmini; akademik ana kaynak, belirsiz → KOŞ. |
| X005:213#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:217#v1 | 830 / 828 ile aynı kuralın tek temsilcisi. |
| X005:257#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:306#v17 | 306 ailesinin temsilcisi. |
| X005:306#v35 | 306 ailesinin temsilcisi. |
| X005:339#v3 | Kaynağın "en iyi" varyantı (çıkış −2σ). |
| X005:339#v4 | Kaynağın "en iyi" varyantı (çıkış −2σ). |
| X005:395#1#v1 | JSE VMA bant ailesinin temsilcisi (K2 kimliği; koşu listesinde tek kayıt). |
| X005:395#2#v1 | JSE VMA bant ailesinin temsilcisi (K2 kimliği; koşu listesinde tek kayıt). |
| X005:395#7#v1 | JSE VMA bant ailesinin temsilcisi (K2 kimliği; koşu listesinde tek kayıt). |
| X005:503#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:519#v1 | Takvim kuralı (hisse kökenli) ama lider takvim kurallarını KOSULACAK kabul etmişti; işlem sayısı yeterli → KOŞ. |
| X005:540#v2 | 540 TSMOM temsilcisi. |
| X005:540#v4 | 540 TSMOM temsilcisi. |
| X005:611#v1 | Takvim kuralı (hisse kökenli) ama lider takvim kurallarını KOSULACAK kabul etmişti; işlem sayısı yeterli → KOŞ. |
| X005:640#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:682#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:706#v1 | 288 / 544#v2 ile aynı kuralın tek temsilcisi (kripto kaynağı). |
| X005:824#v1 | Sınırda (a): tahmini 110-170 işlem; belirsiz → KOŞ. |
| X005:60#v2 | "Yaklaşık" ama sapma küçük (bar içi seviye yerine kapanışta sınama); koşu bilgi verir. |
| X005:60#v3 | "Yaklaşık" ama sapma küçük (bar içi seviye yerine kapanışta sınama); koşu bilgi verir. |
| X005:629#v1 | "Yaklaşık" ama sapma küçük (bar içi seviye yerine kapanışta sınama); koşu bilgi verir. |
| X005:879#v1 | K2 sınıfıyla aynı hipotez: koşu listesinde tek kimlik (çift kayıt varsa G8 kaydı düşer). |
| X005:2 | K2 (DonchianS0002) kimliği: koşu listesinde tek kayıt. |
| X005:76 | Arşiv sınıfıyla FARK_YOK ama lider "kendi sonucu yok" diyerek KOSULACAK yaptı → KOŞ. |
| X005:270#a2 | Sınırda (a): EMA25/50 long ~2/yıl/sembol ≈ 140; belirsiz → KOŞ. |
| X005:355 | Sınırda (a): SMA20/50 long ~2/yıl/sembol ≈ 110-150; lider kararıyla eklendi, belirsiz → KOŞ. |
| X005:501 | Arşivde dis__ay-donumu (giris_kalan 1) kendi sonucuyla elendi; bu ayar tutmayı 4 gün uzatıyor (küçük değil) → KOŞ. |
| X005:842 | Sınırda (a): SMA42/252 iki yön ~2 çevirme/yıl ≈ 120-140; belirsiz → KOŞ. |

## En tartışmalı 10 ÇIKAR kararı

1. **X005:395#3–#6, #8–#10 (c)** — hakem kısa listesindeki JSE VMA bant ailesi 10 → 3 kayda indi (#1, #2, #7). Kaynak "her kural ayrı raporlu" diyor; gerekçe aile şişmesi + 150/200 uzunluklarının kapı 2 sınırında oluşu. Lider isterse #5 (5/150) dördüncü temsilci olarak geri alınabilir.
2. **X005:306 (36 → 2) ve X005:540 (8 → 2), X005:138 (8 → 2) (c)** — temsilci seçimi (2/30 ve 5/60; TSMOM 50 ve 200; 5 ve 30 gün) zorunlu olarak keyfî; sonuçtan bağımsız ama başka temsilci de savunulabilir.
3. **X005:339 (10 → 2) (c)** — yalnız kaynağın "en iyi" dediği çıkış (−2σ) kaldı; kaynağın temel modeli v1 (−1σ) çıktı.
4. **Mevcut X005:396 (6 ayar) ve 838/874/875 (a)** — Donchian 50–250 günlük kırılımlar; (50,0) için tahmin ~90 işlem, stop sonrası yeniden kırılımlarla 150'ye çıkabilir.
5. **Mevcut X005:193, 270#a3, 307 (3 ayar), 389 (a)** — yavaş MA kesişimleri (20/120, 50/100, 50/200, 100/200); 50/100 long için tahmin 70–100, sınırın hemen altı.
6. **X005:726, 438 (a)** — haftalık kurallar içinde en sık işlem üretenler (tahmin 80–120); diğer haftalık/aylıklar kadar kesin değil.
7. **X005:659, 643, 751, 818, 454 (a)** — günlük "nadir birleşim" kuralları; tahminler koşul sıklıklarının çarpımına dayanıyor (2 kat hata payıyla bile <200).
8. **X005:375 (a+b+g)** — basit-RSI 25/75; tek başına hiçbir gerekçe kesin değil, üçü birlikte (≈120 işlem, 215/213'ün eşik kopyası, kaynak açılamadı).
9. **X005:391 (e), 630 (g), 571 (g)** — "kaynak kuralı uydurma/bozuk" gerekçesi; kurallar yine de kodlanmış ve koşulabilir durumda. Kullanıcı kaynakları önemsiyorsa geri alınabilir (3 kayıt, 1d + 1h + 5m ≈ 17 CPU dk).
10. **Mevcut X005:269 (b) ve X005:638, 219, 876** — "yalnız MA tipi / tek parametre farkı" kopyaları (EMA50↔SMA50; çıkış SMA10↔SMA5; BB25↔BB20; SMA200 5 gün teyitli). Farklı kaynaklardan geliyorlar; işlem yolları çok benzer ama birebir değil.

## İsteğe bağlı ikinci dalga (bu raporda ÇIKARILMADI)

- K6 "4h|1d" olup iki TF ile kalan çiftler: 6, 264, 297, 301, 327, 346, 348, 357, 362, 584, 676, 693, 697, 698, 699, 710, 711, 727, 730, 736 (+ 339 v2, 406 SMA20/50). Kullanıcı daha sert budama isterse "kaynak TF vermediyse yalnız 4h" kuralı ~22 kayıt daha düşürür (≈44 CPU dk, BH −22). Ön kayıt ek 3 bunları açıkça iki hipotez saydığı için hakem olarak ben dokunmadım; karar kullanıcı/lider.
- 5m/15m kayıtları süreyi belirliyor. Sonuçtan bağımsız bir gerekçe bulamadım; maliyet ×2 altında 5m kurallarının zorlanacağı bir beklentidir, gerekçe değildir.

## Uygulama notları

- Eleme koşu listesi dondurulmadan uygulanmalı; ön kayıt düzeltmesi (BH ailesi = dondurulan koşu listesi) buna izin veriyor. Çıkarılanlar karar tablosunda gerekçeleriyle kalmalı (p=1 ile aileye katılmaz).
- K1/K2 ile aynı hipotez olanlar (X005:2, 5, 83, 879, 395#x) KOŞ işaretli ama koşu listesinde tek kimlik olmalı.
- Kopya (b) kararlarında "temsilci" kimlik eleme.csv gerekçesinde yazılı; temsilci başka nedenle düşerse kopyası geri alınmalı.
- Düzeltme ajanı VARYANTLAR'ı değiştiriyorsa (yeni kimlik, TF değişimi) eleme.csv kimlik bazında yeniden eşlenmeli; bu rapor 433 kayıtlık anlık görüntüye göredir (haftalık/aylık kurallar 1d mumla koşsa da işlem sayısı gerekçesi değişmez).
- KODLANAMADI kalanlar (3, 114, 353, 356, 419, 553, 580, 585, 673, 742, 863) VARYANTLAR'da olmadığı için kapsam dışı.
