# Scalp Dokümanları — Ortak Payda Analizi

Kaynak: `metinler/*.md` (30 doküman). Amaç: **1 saat (H1) yön + 5 dakika (M5) giriş** yapısına uyan,
dokümanların büyük kısmının ortaklaştığı, kural tabanlı (backtest edilebilir) 2–3 strateji belirlemek.

## 1. Dokümanların özeti (strateji içeren kısımlar)

| Doküman | Zaman dilimi | Yön/Trend filtresi | Giriş | Çıkış / Risk |
|---|---|---|---|---|
| 5 Dakikalık Scalp Stratejisi | M5 | EMA50 eğimi + yükselen tepe/dip | Fiyat EMA10–EMA21 arasına geri çekilince | SL 5 pip, TP 10 pip (1:2); +10 pip'te BE; EMA50 yataylaşınca dur |
| Ellis – *Short Momentum Scalper* | **H1 yön + M5 giriş** | H1: EMA8 > EMA34 ve fiyat ikisinin üstünde | M5: fiyat EMA8'i yukarı kesince al | SL önceki dip, TP **1:2** |
| Ellis – *One-Minute* | M1 | EMA50 > EMA100 | Fiyat EMA'lara yakın + Stokastik(5,3,3) 20'yi yukarı keser | — |
| Ellis – *MACD* | M5/M15 | MACD histogram yönü | Stokastik aşırı bölgeden dönüş + histogram dönüşü | %80 pozisyon 1:1, %20 BE sonrası 2R |
| Ellis – *Meta Scalper* / Connell geri çekilme | M1/M5 | yatay piyasa | Fiyat alt BB'ye iner, ilk bar orta banda dönerken al | Küçük sabit hedef |
| M1-M5 Forex Scalping | M1/M5 | MACD > 0 | Stokastik(8,3,3) 20'yi yukarı keser | SL son destek, TP ≥ 3R (örnekte 1:3) |
| Trevor Candle (1 dk) | M30 trend, M1 giriş | EMA200 eğimi ve fiyat üstünde | Fiyat EMA20 (BB orta) altına çekilir, sonra yeşil mum EMA20 üstünde kapanır + MACD kesişimi + PSAR dönüşü; BB genişliyor olmalı | SL son dip; TP sabit |
| Zackary Carson | **H1 trend + M5 geri çekilme** (açıkça yazıyor) | SMA500 / EMA500 / SMA200 | StochRSI 50 altında yukarı keser + fiyat HMA30 üstüne çıkar; BB+RSI(5) aşırılıktan çıkış | SL giriş mumu altı / son salınım; çıkış HMA altı / karşı bant |
| Max Stevenson (ortalamaya dönüş) | M5 | EMA200 + **ADX<25** | BB(40,2) dışına taşma + RSI(5) <30'dan çıkış; RSI+Keltner(1.5) | SL son salınım; TP karşı bant / ortalama |
| Ferrazzi | M5 | VWAP / EMA500 / SMA200 | BB(1.5σ) dışında kapanış + Stokastik(7,4,3) <20, bant içine dönüşte gir; BB+RSI(5)+ADX<25 | SL giriş mumu; TP karşı bant / Stoch>80 |
| LBR (Kevin Ho) | M5 | 10MA eğimi | **Std sapma geri çekilmesi** (10MA ±1σ banda geri çekilme, eğim yönünde); *ANTI* (Stoch 7 kendi 10MA'sını eğim yönünde keser); açılış aralığı kırılması | Sabit SL/TP, zaman stopu |
| Price Action Scalper | **H1 + M30 + M15 + M5** | 4 zaman diliminin son mumu aynı renk | Kapanışın 3 pip ötesine kırılım | SL önceki H1 mum dibi; TP = SL'nin 2–3 katı |
| Bob Volman | 70-tick (≈M1–M5) | EMA20 yönü | EMA20 yakınında **sıkışma bloğunun (BB) kırılımı**, trend yönünde | 10 pip hedef / 10 pip stop |
| Waqar EMA14/50 | M15/H1 | EMA14–50 kesişimi | Geniş aralıklı yaklaşan kesişim | TP 10–20 pip, SL 10–20 pip |
| Payapa | M5/M15/H1 | 3 zaman dilimi uyumu, EMA 5/8/13/21 + 100/200 | Stokastik(5,3,3) uçlarda kesişim | Karşı uç bölge |
| RSI Pro | M5 (+M15) | SMA24 (2 saat) | RSI(8) "vadisi" trend yönünde | ATR(3) + spread tabanlı stop |
| Kesin Kılavuz / Uko / Busiere | M5 + H1/H4 | Üst zaman dilimi trendi, SMA200 | Geri çekilmede osilatör dönüşü; kırılım onayı | %1 risk, ≥1:2 R/R |
| Christopher | H1 bölge + M5 giriş | H1 arz/talep bölgesi | M5'te bölge içinde tuzak mumu | — |
| GBPJPY M1 / Teva Lama / Heikin Ashi | M1–M5 | — | Aşırı bant (3σ) dönüşü, yuvarlak seviyeler, HA renk değişimi | Zaman stopu |
| Norden, Schroder, Super Scalper, Ultimate Scalper | — | Emir akışı, tape okuma, VSA, MACD/stoch | Büyük ölçüde takdire dayalı | — |

## 2. Ortak paydalar (≥ 5 dokümanda tekrar eden fikirler)

1. **Üst zaman diliminde yön, alt zaman diliminde giriş.** (Ellis, Carson, Price Action Scalper, Payapa, Trevor, Busiere, Uko, Christopher, Kesin Kılavuz, Teva Lama.) H1 trendi EMA ile tanımlamak en yaygın yöntem (EMA8/34, EMA50, EMA200/SMA200/500).
2. **Trend yönünde geri çekilmeden giriş** — fiyat hızlı EMA bölgesine (EMA8–21) geri çekilir, osilatör (Stokastik 5,3,3 / StochRSI) aşırı bölgeden döner, mum tekrar EMA'nın üzerinde kapanınca girilir. (5 Dakikalık, Ellis ×2, M1-M5, Trevor, Carson, LBR, RSI Pro, Kesin Kılavuz, Volman.)
3. **Ortalamaya dönüş (BB + RSI/Stokastik)** — fiyat Bollinger bandı dışına taşar, RSI(5)/Stokastik aşırı bölgeden çıkar, hedef orta bant/karşı bant. Yüksek kazanma oranı için önerilen yöntem; **trend filtresi (MA200/500) + ADX<25** ile. (Stevenson, Carson, Ferrazzi, Ellis Meta Scalper, Connell, GBPJPY, LBR.)
4. **Sıkışma sonrası kırılım (momentum)** — dar konsolidasyonun trend yönünde kırılması, çok zaman dilimli mum uyumu, açılış aralığı. (Volman, Price Action Scalper, LBR 15ORS, Trevor "BB genişliyor olmalı", Uko, Kesin Kılavuz.)
5. **Risk:** sabit/yapısal stop (son salınım / giriş mumu / ATR), **R/R ≥ 1:1.5–1:2**, +1R'de başabaşa çekme, zaman stopu, işlem başına %1–2 risk, haber ve düşük likidite saatlerinden kaçınma, spread maliyetine dikkat.

## 3. Seçilen 3 strateji (H1 yön + M5 işlem)

### S1 — Trend Geri Çekilme (EMA + Stokastik)
*Kaynaklar: Ellis Short Momentum Scalper + One-Minute, 5 Dakikalık Scalp, Trevor Candle, M1-M5, Carson, LBR.*
- **H1 yön:** EMA(8) > EMA(34) ve H1 kapanış > EMA(34) → yalnız AL; tersi → yalnız SAT.
- **M5 kurulum:** son *k* bar içinde fiyat EMA(21) bölgesine geri çekilmiş (low ≤ EMA21) ve Stokastik(5,3,3) %K < 30 olmuş.
- **M5 tetik:** mum EMA(8) üzerinde kapanır ve %K, %D'yi yukarı keser (satışta simetrik).
- **Stop:** son *n* barın en düşüğü − 0.1·ATR (min 0.5·ATR, max 2.5·ATR). **Hedef:** 1.5R (parametre). +1R'de başabaş (opsiyon). Zaman stopu: 36 bar (3 saat).

### S2 — Trend Yönünde Ortalamaya Dönüş (BB + RSI)
*Kaynaklar: Stevenson #3/#4, Carson #3, Ferrazzi #1/#5, Ellis Meta Scalper, Connell, GBPJPY.*
- **H1 yön:** H1 kapanış > EMA(50) ve EMA(50) yükseliyor → yalnız AL (tersi SAT).
- **M5 kurulum:** kapanış alt Bollinger(20, 2) bandının altında **ve** RSI(5) < 30 (son birkaç bar içinde).
- **M5 tetik:** RSI(5) 30'un üstüne geri çıkar ve mum bandın içinde kapanır. Opsiyonel: M5 ADX(14) < 25.
- **Stop:** kurulumdaki en düşük dip − 0.2·ATR (min 0.5·ATR). **Hedef:** orta bant (BB orta) veya sabit R; hangisi önce. Zaman stopu: 24 bar.

### S3 — Sıkışma Kırılımı (Volman Block Break + Çok Zaman Dilimi Uyumu)
*Kaynaklar: Volman, Price Action Scalper, LBR 15ORS, Trevor, Uko, Kesin Kılavuz.*
- **H1 yön:** EMA(8) > EMA(34) ve son kapanmış H1 mumu yeşil → AL yönü (tersi SAT).
- **M5 kurulum:** son *N* (=6) barın aralığı ≤ 1.2·ATR(14) (sıkışma) ve kutu EMA(20)'ye yakın/üstünde.
- **M5 tetik:** kapanış kutu tepesinin üzerinde (alış) — kırılım mumu.
- **Stop:** kutu dibi − 0.1·ATR. **Hedef:** 1.5R–2R. Zaman stopu: 24 bar.

## 4. Değerlendirme kriterleri
- Kazanma oranı ≥ %45, Profit Factor ≥ 1.3, pozitif beklenti (R cinsinden), makul maksimum düşüş.
- Maliyetler dahil (komisyon + kayma, varlık sınıfına göre).
- **Örneklem dışı doğrulama:** parametreler verinin ilk %70'inde seçilir, son %30'da test edilir; yalnız dokümanlarda geçen parametre aralıkları denenir (aşırı uyumu sınırlamak için).

## 5. Veri kaynakları
| Varlık | Kaynak | Not |
|---|---|---|
| İlk 20 kripto | Binance public API (`data-api.binance.vision/api/v3/klines`) ve toplu arşiv `data.binance.vision` | Anahtarsız, 5m/1h, yıllarca geçmiş |
| Magnificent 7 | Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart`) / yfinance | 5m son 60 gün, 1h son 730 gün |
| BIST30 ilk 10 | Yahoo Finance (`.IS` uzantısı) | Aynı limitler |
| Altın, Petrol | Yahoo Finance `GC=F`, `CL=F` (WTI), `BZ=F` (Brent) | Vadeli sürekli kontrat |
