# EPA — Kullanıcı Stratejisinin Testi (EMA 8/21/55 + Hacim + Mum + Destek/Direnç + Trend Çizgisi + Pullback/Breakout)

**Tarih:** 2026-10-09
**Analiz ve kural kaynağı:** `ANALIZ_EMA_STRATEJI.md`
**Kod:** `backtest/epa.py`
**Ham sonuçlar:** `sonuclar/epa/`

## Test çerçevesi (KGT ile aynı)
- **Piyasa:** Binance USDT-M vadeli, her ay hacme göre ilk 15 coin (o ayın verisiyle), yalnız long. Dönem 2020-01 – 2026-09.
- **Masraf:** taraf başına %0,07 + gerçek fonlama.
- **Risk:** işlem başına %0,5, en fazla 5 pozisyon, kaldıraçsız.
- **Zaman dilimi:** 1G bağlam + 4S işlem.
- **Hizalama:** 4 saatlik mumların başlangıcı 0/1/2/3 saat kaydırılarak 4 kez test edildi ve ortalaması alındı (SKA'daki şans etkisine karşı).
- **Dönemler:** IS 2020–2023, OOS 2024–2026/09.
- **Taranan kombinasyon:** toplam 1.484. A için 540, B için 432 + 512 ince ızgara.

## Kural setleri
- **Kurulum A — Pullback:**
  - 4S EMA 8 > 21 > 55, son 10 mumun tepesi en az 2 mum önce.
  - Mum dibi EMA 8'e inmiş, kapanış EMA 21'in üstünde.
  - Sinyal mumunun tepesinde bekleyen alış emri; stop iki mumun dibi.
  - Ayrı ayrı açılıp kapatılan şartlar: mum (yok / hammer veya engulfing / Brooks kalite), konum (yok / EMA21 / destek / trend çizgisi), azalan hacim, günlük bağlam.
- **Kurulum B — Breakout:**
  - Son n mumun aralığı < k × ATR (sıkışma).
  - Kırılım mumu güçlü kapanıyor (gövde ≥ %50, kapanış üst 1/3'te) ve aralık tepesinin, EMA 55'in üstünde.
  - Hacim ≥ vk × 20 mum ortalaması.
  - Giriş sonraki açılışta, stop aralık ortası (1–4 ATR).
- **Bağlam (1G):**
  - EMA 8 > 21 > 55, kapanış > EMA 21, EMA 55'in 5 günlük eğimi > 0.
  - Ayrıca test edilen yatay filtre: EMA 21'in 10 günlük değişimi ≥ 0,5 ATR.
- **Yönetim:** 1R'de kısmi kâr (%15 veya %25) ve başabaş stop. Çıkış: 4S EMA 8 < 21 / EMA 21 altında 2 kapanış / 4S EMA 21–50.

## Sonuç 1 — Bileşenler tek tek ne katıyor? (medyan Sharpe, tüm ızgara)

| Bileşen | Etki | Karar |
|---|---|---|
| Hammer / engulfing şartı (A) | 0,66 (mum şartı olmadan 0,67) | ❌ katkı yok |
| Brooks kalite mumu (A) | 0,77 | ➖ biraz iyi, yine de yetersiz |
| Trend çizgisi konumu (A) | 0,33 | ❌ açıkça zararlı |
| EMA 21 / destek konumu (A) | 0,71–0,73 (konumsuz 0,78) | ➖ nötr |
| Azalan hacim (A) | 0,69 (yok 0,70); OOS 0,35 (yok 0,31) | ➖ nötr |
| Günlük EMA 8/21/55 bağlamı (B) | bağlamsız 0,83 → bağlamla 1,16 | ✅ **güçlü katkı** |
| Günlük yatay filtre | A: 0,83 → 0,50; B: 0,88 → 0,54 | ❌ zararlı (eşik işlemleri fazla eliyor) |
| Hacim teyidi (B, ortalamanın 2 katı) | Sharpe aynı (1,31), düşüş %26 → %18, Calmar 0,77 → 0,98 | ✅ düşüşü azaltıyor |
| EMA 8/21 iç içe şartı (B) | 0,79 → 0,58 | ❌ |
| Geniş sıkışma (7–10 ATR) / dar (3 ATR) (B) | 1,03 / 0,26 | ✅ geniş olan |

**Kurulum A (pullback + mum) başarısız.** En iyi ayar Sharpe 0,99 verdi, ama OOS Sharpe yalnızca 0,42 ve 2024 sonrası yıllık getiri %6. Kriterleri karşılayan ayar yok; KGT'deki Brooks H1/H2 ve pin bar testleriyle aynı sonuç.

## Sonuç 2 — EPA-B (seçilen ayar)
**Ayar:** günlük EMA 8/21/55 bağlamı, 18 mumluk sıkışma < 7 ATR, kırılım mumunda hacim ≥ 2 kat, 4S EMA 8 < 21 çıkışı, 1R'de %15 kısmi kâr. Komşu ayarlar da benzer sonuç verdi: n 18–24, k 5–10, hacim 1,5–2 kat.

| | Kazanma | PF | İşlem/yıl | Yıllık | Maks. düşüş | Sharpe | Calmar |
|---|---|---|---|---|---|---|---|
| **EPA-B, %0,5 risk** | **%48,9** | **2,03** | 82 | **%17,3** | **%17,7** | **1,31** | 0,98 |
| EPA-B, %1 risk | %48,9 | 2,03 | 81 | %30,1 | %32,0 | 1,32 | 0,94 |
| IS 2020–2023 (%0,5) | | | | | | 1,52 | |
| OOS 2024–2026/09 (%0,5) | | | | %10,6 | %10,5 | 0,96 | |
| KGT v3 (%0,4 risk), kıyas | %45,4 | 2,00 | 179 | %32,9 | %30,6 | 1,26 | 1,08 |

**Yıllık getiri, %0,5 risk (%):**

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| +37 | +35 | **−6** | +27 | +25 | +5 | +1 |

**Sağlamlık:**
- **Hizalama:** 4 hizalamanın 4'ünde kârlı, Sharpe 1,06 / 1,18 / 1,24 / 1,27.
- **Maliyet:** ×2'de Sharpe 1,24, ×3'te 1,17. Maliyete dayanıklı: işlem az, stop geniş.
- **Rastgele giriş kıyası:** aynı bağlam ve evrende, aynı sayıda rastgele giriş, 20 simülasyon. Rastgelelerin medyan Sharpe'ı 0,48, p95'i 0,72. Gerçek strateji rastgelelerin %100'ünden iyi.
- **Pozisyon sayısı:** 3'te Sharpe 1,39 (düşüş %15), 8'de 1,08.
- **Evren:** 10 coinde Sharpe 1,05; 20 coinde 1,37 (ama OOS 0,67).
- **Kısmi kâr yok:** Sharpe 1,38 ama kazanma %35. Kazanma ≥ %40 şartı için kısmi kâr kalıyor.

## Sonuç 3 — KGT ile birlikte
- **Günlük getiri korelasyonu 0,77.** İkisi de aynı coinlerde sıkışma sonrası long kırılım oynayıp trendi takip ediyor.
- **Birleşim** (sermaye bölünerek; KGT %0,4 risk, EPA-B %0,5 risk):

| Ağırlık (EPA-B) | Yıllık | Maks. düşüş | Sharpe | Calmar | OOS yıllık | OOS düşüş | OOS Sharpe |
|---|---|---|---|---|---|---|---|
| %0 (yalnız KGT v3) | %32,9 | %30,6 | 1,26 | 1,08 | %28,5 | %18,9 | 1,31 |
| %30 | %28,4 | %25,8 | 1,32 | 1,10 | %23,1 | %15,2 | 1,31 |
| %50 | %25,3 | %22,9 | 1,35 | 1,11 | %19,6 | %13,7 | 1,29 |
| %100 (yalnız EPA-B) | %17,3 | %17,7 | 1,31 | 0,98 | %10,6 | %10,5 | 0,96 |

- Çeşitlendirme faydası küçük ama gerçek: %30–50 EPA-B, Sharpe ve Calmar'ı biraz artırıp düşüşü 5–8 puan azaltıyor. Bedeli yıllık getiride 4–8 puanlık düşüş.

## Değerlendirme
1. **Stratejinin çalışan çekirdeği** günlük EMA 8/21/55 trend bağlamı + 4 saatlik sıkışma kırılımı + hacim teyidi. Nesnel kurallarla Sharpe 1,3, kazanma %49, düşüş düşük. Bu, kitapların "sıkışma → güçlü, yüksek hacimli kırılım" fikrinin doğrulaması.
2. **Çalışmayan kısımlar:**
   - Mum formasyonları (hammer/engulfing) ve EMA bölgesine pullback girişi kâr üretmedi.
   - Trend çizgisi zarar verdi.
   - Bunlar stratejiden çıkarılmalı ya da yalnız takdire bağlı ek teyit olarak kalmalı.
3. **KGT'ye kıyas:**
   - Tüm dönemde Sharpe benzer (1,31'e 1,26), düşüş çok daha düşük.
   - Ama 2024 sonrası KGT belirgin şekilde daha iyi: OOS Sharpe 1,31'e 0,96, getiri %28,5'e %10,6.
   - 2025–2026'da EPA-B neredeyse yatay.
4. **Öneri:**
   - Ana strateji KGT v3 kalıyor.
   - EPA-B, düşüşü azaltmak isteyen için ikinci strateji olarak sermayenin %30'uyla birlikte çalıştırılabilir: yıllık %28, düşüş %26, Sharpe 1,32.
   - Tek başına kullanılacaksa %0,75–1 risk gerekir (yıllık %24–30, düşüş %26–32).
