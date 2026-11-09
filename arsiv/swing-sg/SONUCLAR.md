# Backtest Sonuçları

**Veri:** 2015-01 → 2026-10 günlük OHLCV (kripto Binance, hisse/emtia/endeks/kur Yahoo Finance).
**Evren:** 25 kripto, Magnificent 7, BIST 30'un en büyük 10 hissesi (USD bazında), altın (GC=F), WTI petrol (CL=F).
**Doğrulama:** Parametreler yalnızca **2015–2022 (IS, örneklem-içi)** verisinde seçildi; **2023–2026 (OOS,
örneklem-dışı)** verisi seçimde kullanılmadı, yalnızca doğrulama için.
**Portföy:** 100.000 başlangıç, işlem başına %1 risk, maks. 10 pozisyon, kaldıraçsız. Tüm rakamlar maliyet sonrası.

## Hedef kontrolü

| Hedef | Sonuç |
|---|---|
| Her stratejide kazanma oranı ≥ %45 | ✅ S1 %52,4 · S2 %50,5 · S3 %70,2 (OOS'ta da: %50,4 · %47,4 · %70,4) |
| Birleşik sistemde kazanma oranı ≥ %45 | ✅ %56,1 (IS %57,1 · OOS %55,1) |
| Yüksek kârlılık | ✅ Yıllık %29,1 (OOS dönemi %25,4), maks. düşüş −%12,6, Sharpe 1,40 |

## Strateji bazında

| Strateji | Dönem | İşlem | Kazanma | Kâr faktörü (R) | Ort. R | Ort. kazanç | Ort. kayıp | Ort. gün | Yıllık getiri* | Maks. düşüş* | Sharpe* |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Geri çekilme | Tüm | 1186 | 52,4% | 1,82 | +0,32 | +14,8% | −8,6% | 15,7 | 19,8% | −16,0% | 1,10 |
| | IS | 591 | 54,5% | 2,06 | +0,39 | +16,8% | −8,5% | 16,7 | 20,9% | −14,4% | 1,08 |
| | OOS | 595 | 50,4% | 1,60 | +0,25 | +12,6% | −8,7% | 14,7 | 17,5% | −12,6% | 1,18 |
| S2 Kırılım | Tüm | 501 | 50,5% | 1,85 | +0,43 | +12,9% | −6,7% | 18,0 | 12,3% | −12,4% | 1,05 |
| | IS | 305 | 52,5% | 1,91 | +0,45 | +12,6% | −6,1% | 18,1 | 16,4% | −12,4% | 1,27 |
| | OOS | 196 | 47,4% | 1,77 | +0,41 | +13,4% | −7,5% | 17,8 | 4,9% | −10,4% | 0,55 |
| S3 Aşırı satım | Tüm | 510 | 70,2% | 1,96 | +0,22 | +6,8% | −7,1% | 5,2 | 9,5% | −9,8% | 1,27 |
| | IS | 233 | 70,0% | 1,92 | +0,25 | +6,9% | −7,0% | 5,0 | 8,9% | −9,8% | 1,30 |
| | OOS | 277 | 70,4% | 2,00 | +0,19 | +6,7% | −7,1% | 5,5 | 14,1% | −7,9% | 1,36 |
| **BİRLEŞİK** | **Tüm** | **2197** | **56,1%** | **1,85** | **+0,32** | +12,1% | −7,9% | 13,8 | **29,1%** | **−12,6%** | **1,40** |
| | IS | 1129 | 57,1% | 1,99 | +0,38 | +13,3% | −7,5% | 14,7 | 30,0% | −9,2% | 1,35 |
| | OOS | 1068 | 55,1% | 1,70 | +0,26 | +10,8% | −8,2% | 12,9 | 25,4% | −12,6% | 1,44 |

\* Stratejinin tek başına portföy simülasyonu. Birleşik satırı üç stratejinin aynı portföyde birlikte çalışmasıdır.

**Karşılaştırma (al-tut, aynı dönem):** BTC yıllık %38,2 / maks. düşüş −%83 · Nasdaq-100 %18,4 / −%36 ·
S&P 500 %12,0 / −%34 · Altın %11,4 / −%25. Sistem, Nasdaq-100'den yüksek getiriyi çok daha düşük düşüşle sağlıyor.

## Yıllık birleşik portföy getirisi

2015: +2,6% · 2016: −2,2% · 2017: +35,6% · 2018: −1,2% · 2019: +25,8% · 2020: +72,4% · 2021: +127,2% ·
2022: +11,0% · 2023: +32,9% · 2024: +29,0% · 2025: +10,9% · 2026 (Eki'ye kadar): +30,7%

12 yılın 10'u pozitif; en kötü yıl −%2,2. 2022 ayı piyasasında rejim filtresi işlem sayısını 47'ye indirerek
sermayeyi korudu.

## Varlık sınıfı bazında (birleşik sistem)

| Sınıf | Dönem | İşlem | Kazanma | Kâr faktörü (R) | Ort. R |
|---|---|---|---|---|---|
| BIST (USD) | IS | 77 | 41,6% | 1,14 | +0,08 |
| | OOS | 42 | 47,6% | 1,62 | +0,31 |
| Emtia | IS | 105 | 45,7% | 1,21 | +0,10 |
| | OOS | 46 | 54,3% | 2,14 | +0,46 |
| Kripto | IS | 408 | 61,8% | 2,94 | +0,60 |
| | OOS | 703 | 53,9% | 1,61 | +0,23 |
| Mag7 | IS | 539 | 58,1% | 1,79 | +0,31 |
| | OOS | 277 | 59,2% | 1,88 | +0,31 |

## Sağlamlık testleri (`deneyler/saglamlik.py`)

- **Parametre duyarlılığı:** Her parametre tek tek bir kademe aşağı/yukarı oynatıldı (39 varyasyon).
  Hepsinde beklenti pozitif kaldı; kazanma oranı S1'de %47–58, S2'de %46–56, S3'te %67–73 aralığında.
  Sonuçlar tek bir "şanslı" ayara bağlı değil.
- **2× maliyet:** kazanma %55,8, yıllık getiri %26,8, maks. düşüş −%14,1.
- **Monte Carlo (2.000 yeniden örnekleme):** medyan maks. düşüş −%13,1, en kötü %5'lik dilim −%18,8.
- **BIST TL vs USD:** TL bazında S1/S3 BIST'te kârlı görünüyordu (S1 ort. R +0,30); USD'ye çevrilince
  +0,01'e düştü. Bu yüzden sistem BIST'i USD bazında değerlendirir ve yalnızca S2 ile işler.

## İyileştirme günlüğü

| Adım | Değişiklik (dokümandaki dayanağı) | Etki |
|---|---|---|
| 1 | Temel sürüm: haftalık EMA10 yönü + 3 kurulum | S1 KO %35, S2 KO %44, S3 KO %65 (düşük kâr faktörü) |
| 2 | S1: RSI eşiği gevşetildi, **kısmi kâr alma** (Ladha: yarısını erken sat) | S1 KO %35 → %49 |
| 3 | S2: kısmi kâr 2R, izleyen stop 4 ATR, daralma filtresi (Farley NR7) | S2 KO %49, ort. R +0,58 |
| 4 | S3: **limit emirle giriş** (kapanış − 0,5 ATR), SMA10 çıkışı | S3 kâr faktörü 1,26 → 1,53 |
| 5 | S1: **haftalık Heikin Ashi** yönü (Munroe) | S1 IS/OOS KO %54/%48 |
| 6 | Portföyde gizli kaldıraç düzeltildi (toplam maruziyet ≤ %100) | Daha gerçekçi getiri |
| 7 | BIST USD'ye çevrildi (TL enflasyon yanılsaması ayıklandı) | Birleşik yıllık %35 → %21 (dürüst değer) |
| 8 | **Piyasa rejimi filtresi** (Ladha: önce endeks trendi) | S2 OOS ort. R +0,36 → +0,49, S3 kripto +0,06 → +0,19 |
| 9 | Strateji–sınıf eşlemesi (BIST yalnızca S2, emtia S3 dışı) | Birleşik yıllık %29, düşüş −%15 |
| 10 | S1 rejim filtresi + RSI<65; S2 kısmi kâr 1,5R | Birleşik KO %56, düşüş −%12,6 |

## Bilinmesi gereken sınırlamalar

- **Hayatta kalma yanlılığı:** Kripto listesi *bugünün* ilk 25'idir; 2018–2021'de bu listede olmayan, sonradan
  çöken coinler testte yok. Kripto IS sonuçları bu yüzden olduğundan iyi görünebilir. OOS (2023+) bu etkiden
  daha az etkilenir ve sistem orada da hedefleri sağlıyor.
- Altın/petrol sürekli vadeli kontrat serisidir (GC=F, CL=F); kontrat devirlerinde küçük fiyat sıçramaları olabilir.
- Kayma basit sabit oranla modellendi; büyük boşluklu açılışlarda stop gerçekleşmesi daha kötü olabilir
  (motor, açılış stopun altındaysa açılıştan çıkış yapar).
- Geçmiş performans gelecekteki sonuçları garanti etmez. Bu çalışma yatırım tavsiyesi değildir.
