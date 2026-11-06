# A v2 (rejime bağlı short) ve kaldıraç testi

Görev: ekip lideri (swing-sg). Yalnız backtest yapıldı, kağıt bota ve main'e dokunulmadı.
- Kod: `scripts/a_v2_kaldirac.py`.
- Ham sonuçlar: `results/a_v2_kaldirac_{ana,stres}.json`.

Ortak kurallar: nihai parametreler (`algo/final.py`), maliyet %0.07/taraf ve Binance funding (işlem R'sine dahil), portföy motoru.
- A: risk %0.5, en çok 10 pozisyon.
- B: risk %0.75, en çok 25 pozisyon.
- Toplam nominal sınırı 5x, coin başına tek pozisyon.
- Öz sermaye açık pozisyonlar dahil (MTM) ve bileşiksiz.
- Dönemler: IS 2020–2023, OOS 2024–2026, 2022 ayrı.

Birleşimler iki yöntemle verildi:
- **rapor yöntemi** = kolların günlük yüzde getirilerinin ortalaması (önceki raporlardaki 21%/−15%/1.45 bununla);
- **basit 50/50** = sermaye ikiye bölünür, kâr/zararlar toplanır. Kaldıraçta yalnız bu yöntem doğru sonuç verir; yüzde ortalaması bir kol çok düşünce yanıltıyor.

## Görev 1 — A v2: short yalnız BTC günlük kapanış < EMA200

**Sonuç: A v2 mevcut A'dan kötü, önerilmez.** Kural IS'te (özellikle 2022'de) iyileştiriyor, OOS'ta bozuyor.

Neden (mevcut A'nın portföyde alınmış short işlemleri, BTC rejimine göre):

| Dönem | BTC > EMA200 short: n / ort R / PF | BTC < EMA200 short: n / ort R / PF |
|---|---|---|
| IS | 581 / +0.06 / 1.15 | 310 / +0.24 / 1.67 |
| OOS | 497 / +0.05 / 1.12 | **324 / −0.06 / 0.90** |
| 2022 | 10 / +1.47 / 31 | 240 / +0.32 / 1.89 |

2024–26'da ayı rejimindeki shortlar zarar etti, boğa rejimindekiler (BTC yükselirken düşen altcoinler) hafif kârlı. Filtre 2022'ye uyuyor ama ileriye taşınmıyor. Ham R toplamıyla yapılan kaba hesap da (pozisyon sınırı yok) 2023–26 shortlarını ~0 göstermişti. Bu sonuç onunla uyumlu, ama portföy etkisi negatif: OOS'ta kârlı boğa-rejimi shortları kaybolurken ayı-rejimi shortlarının zararı kalıyor.


### Ana evren (25 coin)

| Varyant | İşlem (short) | PF TÜM | Yıllık % | MTM DD % | Sharpe | IS Sh | OOS Sh | OOS yıllık % | 2022 Sh | 2022 yıllık % |
|---|---|---|---|---|---|---|---|---|---|---|
| A mevcut | 3147 (1712) | 1.61 | 26.9 | -31.2 | 0.99 | 1.06 | 1.04 | 14.8 | 1.40 | 27.6 |
| A yalnız long | 1564 (0) | 1.95 | 23.6 | -24.5 | 1.02 | 1.08 | 1.01 | 14.0 | -0.67 | -2.1 |
| A v2 (rejim short) | 2323 (778) | 1.61 | 23.0 | -24.0 | 1.01 | 1.22 | 0.56 | 6.1 | 1.19 | 20.6 |
| B (referans) | 996 (0) | 1.78 | 12.1 | -15.7 | 0.86 | 0.66 | 1.26 | 16.0 | -0.03 | -2.1 |

| A+B birleşimi | Yöntem | Yıllık % | MTM DD % | Sharpe | IS Sh | OOS Sh | 2022 Sh |
|---|---|---|---|---|---|---|---|
| A mevcut + B | rapor | 21.1 | -14.7 | 1.45 | 1.41 | 1.76 | 1.52 |
| A mevcut + B | basit 50/50 | 20.8 | -17.8 | 1.25 | 1.25 | 1.42 | 1.55 |
| A yalnız long + B | rapor | 18.8 | -12.9 | 1.30 | 1.24 | 1.59 | -0.13 |
| A yalnız long + B | basit 50/50 | 18.6 | -16.2 | 1.17 | 1.14 | 1.37 | -0.26 |
| A v2 + B | rapor | 18.7 | -12.6 | 1.36 | 1.43 | 1.36 | 1.22 |
| A v2 + B | basit 50/50 | 18.3 | -16.3 | 1.18 | 1.30 | 1.05 | 1.30 |

### Stres evreni (20 eski/delist coin)

| Varyant | İşlem (short) | PF TÜM | Yıllık % | MTM DD % | Sharpe | IS Sh | OOS Sh | OOS yıllık % | 2022 Sh | 2022 yıllık % |
|---|---|---|---|---|---|---|---|---|---|---|
| A mevcut | 2781 (1459) | 1.40 | 19.9 | -23.0 | 0.83 | 0.70 | 1.08 | 23.1 | 1.83 | 46.8 |
| A yalnız long | 1414 (0) | 1.52 | 15.5 | -41.9 | 0.70 | 0.39 | 1.10 | 28.2 | -1.09 | -2.9 |
| A v2 (rejim short) | 2021 (626) | 1.44 | 17.6 | -32.2 | 0.77 | 0.63 | 0.97 | 22.3 | 1.50 | 33.8 |
| B (referans) | 1007 (0) | 1.65 | 11.4 | -13.0 | 0.92 | 0.87 | 1.07 | 10.5 | -0.20 | -4.1 |

| A+B birleşimi | Yöntem | Yıllık % | MTM DD % | Sharpe | IS Sh | OOS Sh | 2022 Sh |
|---|---|---|---|---|---|---|---|
| A mevcut + B | rapor | 17.2 | -11.7 | 1.30 | 1.18 | 1.52 | 2.19 |
| A mevcut + B | basit 50/50 | 16.1 | -13.1 | 1.13 | 1.01 | 1.32 | 2.07 |
| A yalnız long + B | rapor | 14.7 | -24.1 | 1.02 | 0.76 | 1.41 | -0.38 |
| A yalnız long + B | basit 50/50 | 13.5 | -23.8 | 0.94 | 0.68 | 1.31 | -0.43 |
| A v2 + B | rapor | 15.8 | -16.1 | 1.14 | 1.01 | 1.32 | 1.73 |
| A v2 + B | basit 50/50 | 14.7 | -17.6 | 1.01 | 0.89 | 1.19 | 1.64 |

Özet: A+B'nin Sharpe'ı (rapor yöntemi) iki evrende de düşüyor.

| Evren | A mevcut + B | A v2 + B | A yalnız long + B |
|---|---|---|---|
| Ana | 1.45 | 1.36 | 1.30 |
| Stres | 1.30 | 1.14 | 1.02 |

Notlar:
- A v2 ana evrende düşüşü azaltıyor (−%14.7 → −%12.6), stres evreninde ise artırıyor (−%11.7 → −%16.1).
- Yalnız long sürüm 2022'de zarar ediyor. Short bacak A'nın ayı piyasası sigortası; kaldırılmamalı.

## Görev 2 — Kaldıraç

### Stop mesafesi dağılımı (portföyde alınan işlemler)

| | Medyan | %75 | %95 | Güvenli en yüksek L (stopların %95'i tasfiye mesafesinin içinde) |
|---|---|---|---|---|
| A (ana) | %5.32 | %7.29 | %13.47 | **7.16x** |
| B (ana) | %22.48 | %31.06 | %51.87 | **1.91x** |
| A (stres) | %6.04 | %8.38 | %14.76 | **6.55x** |
| B (stres) | %24.61 | %33.0 | %53.19 | **1.86x** |

Tasfiye mesafesi = 1/L − %0.5:
- 1.5x → %66.2
- 2x → %49.5
- 3x → %32.8
- 5x → %19.5

A'nın stopları dar (medyan %5–6), B'ninki geniş (medyan %22–25; 4×4H ATR ve kapitülasyon sonrası oynaklık).

### (a) Aynı risk, kaldıraç yalnız teminatı azaltır

Kural: stop mesafesi tasfiye mesafesinden büyükse ve işlem içindeki en kötü 1H fiyatı o seviyeye ulaştıysa işlem tasfiye olur. Kayıp nominalin 1/L'si, işlem sonradan kârlı kapanacak olsa bile.

Muhafazakâr varsayım: işlem boyunca ilk stop kullanıldı. İz süren stop yukarı taşınmış olsa bile tasfiye sayıldı, yani tasfiye sayısı abartılı olabilir.


**ana evren**

| L | A yıllık % / DD % / Sh | A tasfiye % | B yıllık % / DD % / Sh | B tasfiye % (tasfiye olmasa kârlı) | A+B basit: yıllık / DD / Sh |
|---|---|---|---|---|---|
| 1.0x | 26.9 / -31.2 / 0.99 | 0.0 | 12.1 / -15.7 / 0.86 | 0.0 (0) | 20.8 / -17.8 / 1.25 |
| 1.5x | 26.9 / -31.2 / 0.99 | 0.0 | 12.1 / -15.7 / 0.86 | 0.0 (0) | 20.8 / -17.8 / 1.25 |
| 2.0x | 26.9 / -31.2 / 0.99 | 0.0 | 12.1 / -15.7 / 0.86 | 0.0 (0) | 20.8 / -17.8 / 1.25 |
| 3.0x | 26.9 / -31.2 / 0.99 | 0.1 | 12.0 / -15.7 / 0.85 | 2.9 (0) | 20.7 / -17.9 / 1.25 |
| 5.0x | 26.8 / -31.2 / 0.98 | 0.7 | 11.2 / -15.5 / 0.79 | 14.7 (26) | 20.4 / -19.1 / 1.22 |

**stres evren**

| L | A yıllık % / DD % / Sh | A tasfiye % | B yıllık % / DD % / Sh | B tasfiye % (tasfiye olmasa kârlı) | A+B basit: yıllık / DD / Sh |
|---|---|---|---|---|---|
| 1.0x | 19.9 / -23.0 / 0.83 | 0.0 | 11.4 / -13.0 / 0.92 | 0.0 (0) | 16.1 / -13.1 / 1.13 |
| 1.5x | 19.9 / -23.0 / 0.83 | 0.0 | 11.4 / -12.9 / 0.92 | 0.4 (0) | 16.1 / -13.1 / 1.13 |
| 2.0x | 19.9 / -23.0 / 0.83 | 0.0 | 11.4 / -12.8 / 0.92 | 0.8 (1) | 16.1 / -13.1 / 1.13 |
| 3.0x | 19.9 / -23.0 / 0.82 | 0.1 | 11.1 / -13.1 / 0.90 | 3.7 (6) | 16.0 / -13.2 / 1.12 |
| 5.0x | 19.9 / -23.0 / 0.82 | 1.1 | 10.1 / -13.1 / 0.81 | 18.0 (32) | 15.6 / -13.5 / 1.08 |

Sonuç:
- **A** 3x teminat kaldıracına kadar etkilenmiyor. 5x'te işlemlerin %0.7–1.1'i tasfiye oluyor.
- **B** 3x'te %3–4, 5x'te %15–18 tasfiye ediliyor; bunların 26–32'si aslında kârlı kapanacaktı.
- Pratik sınır: A için en çok ~5x, B için en çok ~2x teminat kaldıracı.

### (b) Büyütme: işlem riski × L, toplam maruziyet sınırı × L (tasfiye kuralı aynı L ile)


**ana evren**

| L | A yıllık % / DD % / Sh | B yıllık % / DD % / Sh | A+B basit 50/50: yıllık % / DD % / Sh | (rapor yöntemi: yıllık / DD / Sh) |
|---|---|---|---|---|
| 1.0x | 26.9 / -31.2 / 0.99 | 12.1 / -15.7 / 0.86 | **20.8 / -17.8 / 1.25** | 21.1 / -14.7 / 1.45 |
| 1.5x | 33.3 / -40.9 / 0.97 | 16.2 / -23.4 / 0.86 | **26.4 / -23.1 / 1.22** | 27.6 / -17.6 / 1.46 |
| 2.0x | 38.4 / -48.6 / 0.97 | 19.5 / -31.1 / 0.86 | **30.9 / -29.3 / 1.19** | 33.4 / -19.5 / 1.47 |
| 3.0x | 46.1 / -59.7 / 0.96 | 24.7 / -46.2 / 0.84 | **37.7 / -39.8 / 1.15** | 43.6 / -22.2 / 1.49 |
| 5.0x | 56.7 / -73.0 / 0.96 | 31.2 / -72.1 / 0.78 | **47.1 / -56.9 / 1.07** | 65.8 / -31.2 / 1.46 |

**stres evren**

| L | A yıllık % / DD % / Sh | B yıllık % / DD % / Sh | A+B basit 50/50: yıllık % / DD % / Sh | (rapor yöntemi: yıllık / DD / Sh) |
|---|---|---|---|---|
| 1.0x | 19.9 / -23.0 / 0.83 | 11.4 / -13.0 / 0.92 | **16.1 / -13.1 / 1.13** | 17.2 / -11.7 / 1.30 |
| 1.5x | 25.5 / -27.2 / 0.84 | 15.2 / -16.9 / 0.94 | **21.0 / -16.0 / 1.13** | 23.1 / -14.0 / 1.34 |
| 2.0x | 29.8 / -30.5 / 0.86 | 18.4 / -19.7 / 0.95 | **24.9 / -18.1 / 1.13** | 28.1 / -15.4 / 1.37 |
| 3.0x | 36.7 / -37.6 / 0.88 | 23.3 / -27.0 / 0.93 | **31.0 / -23.2 / 1.11** | 36.7 / -19.2 / 1.42 |
| 5.0x | 46.3 / -49.8 / 0.91 | 28.9 / -39.7 / 0.85 | **39.1 / -31.6 / 1.06** | 50.3 / -24.3 / 1.45 |

Sonuç (ana evren, basit 50/50):

| L | Yıllık | Düşüş |
|---|---|---|
| 1x | %21 | −%18 |
| 2x | %31 | −%29 |
| 3x | %38 | −%40 |
| 5x | %47 | −%57 |

- Getiri kaldıraçla doğrusal artmıyor, düşüş ise kabaca doğrusal artıyor. Sharpe 1.25'ten 1.07'ye geriliyor: tasfiyeler ve 25 slot sınırı.
- Swing referansıyla benzer tablo (1x %29/−%13, 2x %54/−%30, 3x %79/−%44): 2x'in üstünde düşüş katlanıyor.

## Aralık değerlendirmesine aday notlar (şimdi uygulanmadı)

1. **A v2 uygulanmamalı.** Mevcut short kuralı korunmalı; regime filtresi 2022'ye aşırı uyumlu.
2. **Kaldıraç:** gerçek hesapta risk %0.5/%0.75 korunursa A için ≤5x, B için ≤2x izole teminat kaldıracı güvenli. Riski büyütmek (b) istenirse en çok 1.5–2x (ana: yıllık ~%26–31, düşüş −%23…−%29).
