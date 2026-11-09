# Doküman Analizi ve Strateji Seçimi

Kaynak: `metinler/` altındaki 28 kitabın metinleri (PDF'lerden çıkarıldı).
Amaç: kitapların **ortak paydada buluştuğu**, kuralları net ve koda dökülebilen
2-3 day trade stratejisi. Yapı: **4s/1s yön (trend filtresi) + 15dk/5dk giriş**.

## 1. Kavramların kitaplar arası yaygınlığı

`metinler/*.md` üzerinde sayım (kaç kitapta geçiyor / toplam geçiş):

| Kavram | Kitap | Geçiş | Not |
|---|---|---|---|
| Destek / direnç | 28 | 1091 | Hepsinde temel |
| Çoklu zaman dilimi | 27 | 413 | "Büyük resimde yön, küçükte giriş" |
| Hacim | 26 | 635 | Kırılma teyidi |
| Hareketli ortalama / EMA | 26 | ~1100 | 20 EMA en çok anılan |
| Zarar durdur (stop-loss) | 25 | 475 | Her işlemde zorunlu |
| Geri çekilme (pullback) | 23 | 266 | Trend yönünde girişin yolu |
| Kırılma (breakout) | 22 | 699 | Aralık / açılış aralığı / kanal |
| Boşluk (gap) | 22 | 304 | Hisseler için |
| Momentum | 21 | 498 | MACD, MOM, RSI |
| Pivot | 19 | 402 | Klasik pivot, CPR, Camarilla |
| Fibonacci | 19 | 196 | %38,2–%61,8 geri çekilme |
| Risk/ödül | 19 | 123 | En az 1:2 önerilir |
| MACD | 17 | 189 | 12-26-9 |
| RSI | 17 | 171 | 14 (Backus 9) |
| Bollinger | 14 | 182 | 20,2 |
| Stokastik | 14 | 125 | Aşırı satımdan dönüş tetiği |
| ATR | 6 | 13 | Stop/aralık ölçüsü |
| VWAP | 4 | 167 | Christensen, Don Charles |

## 2. Kitaplarda geçen somut, kuralı olan kurulumlar

| Kurulum | Kaynak | Özet kural |
|---|---|---|
| Çoklu zaman dilimi trend | Kathy Lien (Böl. 9) | Üst TF'de trendi belirle, alt TF'de trend yönünde geri çekilmede (Fibonacci %38–%76) gir; tepe/dip seçme |
| Mükemmel düzen (Perfect Order) | Kathy Lien | SMA10>20>50>100>200 ve ADX>20 yükselen → trend; düzen bozulunca çık |
| 20-100 momentum | Kathy Lien | 5dk: fiyat 20 EMA ve 100 SMA'yı kırar, MACD son ≤5 mumda sıfırı geçmiş; stop kırılım mumunun dibi; 1R'de yarı kapat + başabaş, kalan 20 EMA ile iz sür |
| 20 EMA + Stokastik + RSI | Manny Backus | Fiyat 20 EMA üstünde, Stokastik 20'den yukarı kesişim, RSI(9) kendi 4'lü MA'sını yukarı keser; stop EMA'yı geçmeden önceki son dip (≈1:3 R/Ö) |
| Hareketli ortalama + saatlik yön | Odin Velez | Saatlik MA çifti ile yön; 5dk 8 EMA tetikleyici; stop son tepe/dibin ötesi |
| 5/8 + 34/55 + 200 EMA | Gavin Wallace | 200 EMA yön filtresi (birden çok TF), 34/55 trend, 5/8 kesişimi giriş; 15dk grafik |
| MA kanalı (MAC) | Jacob Bernstein | SMA10(yüksek)/SMA8(düşük) kanalı; kanal dışında 2 tam mum + Momentum(28) kendi SMA'sını geçerse giriş; 30dk |
| 20 MA kesişimi | Rajiv LB Roy | 15dk: fiyat 20 MA üstünde kapanır, son mumun tepesi aşılınca al; stop salınım dibi; MA altında kapanışta çık |
| Açılış aralığı kırılması (ORB) | Christensen, Rajiv Roy, Kathy Lien, Odin Velez | İlk 5/15/30 dk aralığı; aralık ATR'ye göre dar olmalı; kırılım yönünde gir, stop aralığın karşı ucu / VWAP; hedef 1R–2R |
| Seans aralığı kırılması | Kathy Lien ("Gerçek anlaşmayı beklemek"), Velez ("New York kırılması") | Seans öncesi aralık; kırılım +tampon ile giriş; 1R'de yarısını al |
| CPR + Camarilla | Tranquil Trader | Dar ve yükselen CPR = trend günü; H4/L4 üstü/altı kapanış + kırılım mumu; 1R'de %70 kapat, kalan 2R |
| VWAP | Christensen | VWAP üstü alıcı kontrolü; ORB stopu VWAP altı kapanış |
| İç gün kırılması | Kathy Lien | ≥2 iç gün sonrası önceki gün tepesi/dibi kırılımı, 2R hedef |
| Yanlış kırılma / Fader | Kathy Lien | ADX<35 iken önceki gün aralığının dışına sahte taşma → içeri dönüşte ters işlem |

## 3. Ortak payda: üç ilke

Kitapların neredeyse tamamı aynı üç ilkeyi tekrarlıyor:

1. **Trendle işlem yap**: üst zaman diliminde yönü belirle (MA dizilimi, fiyatın
   200/50 EMA'ya göre konumu, CPR yönü) ve yalnızca o yönde işlem aç.
2. **Girişi alt zaman diliminde, net bir tetikle yap**: 20 EMA'ya geri çekilme
   ve dönüş, momentum teyidi (MACD/RSI/Stokastik) ya da aralık kırılması.
3. **Riski önceden tanımla**: stop yapısal noktaya (salınım dibi/tepesi, aralığın
   karşı ucu) konur, hedef ≥1:2 R/Ö; 1R'de kısmi kâr + stopu başabaşa çekme
   (Lien, Tranquil Trader, Rajiv Roy) kazanma oranını yükseltir.

## 4. Seçilen stratejiler

Her stratejide **yön** 4s ve 1s grafikten, **giriş** 15dk veya 5dk grafikten.
Day trade kuralı: hisse/BIST/emtiada seans sonunda, kriptoda en geç gün sonunda
(UTC 00:00) tüm pozisyonlar kapatılır.

### S1 — Trend Geri Çekilme (EMA Pullback)
Kaynak: Kathy Lien (çoklu TF + Fibonacci geri çekilme), Manny Backus (20 EMA +
Stokastik/RSI), Gavin Wallace (200/55 EMA), Odin Velez (saatlik yön + kısa EMA tetik),
Rajiv Roy (20 MA).

- **Yön (4s + 1s):** Long için 4s kapanış > EMA200(4s) *veya* EMA50>EMA200 (4s),
  ve 1s'te EMA20 > EMA50 ve kapanış > EMA50. Short tersi.
- **Kurulum (15dk/5dk):** Fiyat trend yönünde ilerledikten sonra 20 EMA'ya geri çekilir
  (mum dibi EMA20'ye ≤ 0,25·ATR yaklaşır/dokunur) ama EMA50'nin altına kapanmaz.
- **Tetik:** Dönüş mumu: kapanış EMA20 üstünde ve önceki mumun tepesi üstünde, ayrıca
  Stokastik(14,3) %K, %D'yi yukarı keser (son 3 mum içinde, <50 bölgesinden) *veya*
  RSI(9) kendi 4'lü ortalamasını yukarı keser (Backus).
- **Stop:** Son geri çekilme dibi − 0,1·ATR (en az 0,5·ATR, en çok 2·ATR).
- **Çıkış:** 1R'de %50 kapat + stop başabaş; kalan 2R hedefi veya 20 EMA altı kapanış
  (Lien'in 20 EMA iz süren stopu) ya da gün sonu.

### S2 — Momentum Kırılması (20-100 / MAC)
Kaynak: Kathy Lien (20-100 momentum, MACD), Jacob Bernstein (MA kanalı + Momentum
teyidi), Gavin Wallace (EMA kesişimleri), Mükemmel düzen (Lien).

- **Yön (4s + 1s):** 4s'te EMA20 > EMA50 (long) ve 1s'te MACD histogramı > 0 ve
  kapanış > SMA100(1s). Short tersi.
- **Kurulum (15dk/5dk):** Fiyat önce hem EMA20 hem SMA100'ün karşı tarafındadır
  (veya aralarında sıkışmıştır).
- **Tetik:** Mum, ikisinin de üzerinde (tampon: 0,1·ATR) kapanır **ve** MACD(12,26,9)
  son ≤5 mum içinde sıfırın üzerine geçmiştir (Lien'in "momentum olgunlaşmadan" kuralı).
  Alternatif teyit: Bernstein MOM(28) > SMA(MOM,28).
- **Stop:** Kırılım mumunun dibi (en az 0,5·ATR).
- **Çıkış:** 1R'de %50 + başabaş; kalan EMA20 − 0,25·ATR ile iz süren stop
  (Lien'in "20 EMA eksi 15 pip" kuralının ATR'ye uyarlanmışı); gün sonu.

### S3 — Açılış/Seans Aralığı Kırılması + Pivot (ORB + CPR)
Kaynak: Christensen (ORB, VWAP), Rajiv Roy (ORB, 1:1 ve 1:2 hedef), Kathy Lien
(seans aralığı kırılması), Odin Velez (New York kırılması), Tranquil Trader (CPR/Camarilla).

- **Yön (4s + 1s + günlük pivot):** Long için 1s kapanış > EMA50(1s), 4s EMA20 > EMA50,
  ve kapanış > günlük pivot (P). Dar CPR (genişlik < son 20 günün medyanı) tercih
  (Tranquil Trader: dar CPR = trend günü).
- **Aralık:** Hisse/BIST/emtia: seansın ilk 30 dk'sı (15dk'da 2 mum, 5dk'da 6 mum).
  Kripto (7/24): UTC 00:00–03:00 Asya aralığı, Londra/AB açılışında kırılım (Lien).
  Aralık genişliği ≤ 1,2·ATR(günlük ölçeğe göre) olmalı (Christensen: "aralık normal
  gerçek aralığa göre dar olmalı").
- **Tetik:** Mum aralık tepesinin üzerinde kapanır (short: dibinin altında) ve
  kapanış VWAP'ın doğru tarafındadır; hacim > son 20 mum ortalaması (kırılım teyidi).
- **Stop:** Aralığın orta noktası veya karşı ucu (hangisi ≤ 1,5·ATR ise).
- **Çıkış:** 1R'de %50 (Tranquil: %70) + başabaş; kalan 2R veya R1/S1 pivotu; gün sonu.
  Günde sembol başına en fazla 1 ORB işlemi.

## 5. Risk ve pozisyon yönetimi (tüm stratejiler)
- İşlem başına risk: sermayenin %0,5–%1'i (birçok kitapta %1–%2 üst sınır).
- Günlük zarar limiti: −%3 → o gün işlem durur.
- Aynı anda en fazla 5 açık pozisyon; korelasyonlu (aynı sınıf) en fazla 3.
- Maliyetler backtest'e dahil: kripto %0,10 + kayma, ABD hisse %0,02, BIST %0,05,
  emtia %0,03 (her yön).

## 6. Değerlendirme ölçütleri ve hedef
- Kazanma oranı (net kârlı işlem / toplam) **≥ %45**.
- Profit factor ≥ 1,3, beklenti > 0,15R, max drawdown makul.
- Aşırı uydurmayı (overfitting) önlemek için: parametreler yalnızca kitaplarda
  geçen değer kümelerinden seçilir; veri **eğitim (%70) / test (%30)** olarak ayrılır,
  karar test dönemine göre verilir; sonuçlar varlık sınıfı bazında raporlanır.
