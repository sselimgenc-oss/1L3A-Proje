# Haftalık Yön + Günlük İşlem (1W / 1D) — Strateji Çalışması

**Kapsam:** önceki 1D/4H yön + 1H işlem çalışmasından bağımsız, ikinci bir zaman dilimi çalışması.
- **Veri:** Binance USDT-M, 25 coin (ana evren) ve 20 eski/delist edilmiş coin (stres evreni), 2020-01 → 2026-10.
- **Mumlar:** günlük mumlar 1h veriden (UTC gün) üretilir; haftalık mumlar Pazartesi açılışlıdır.
- **İleriye bakma yok:** haftalık değer, günlük muma ancak o hafta kapandıktan sonra aktarılır.
- **Maliyet:** taraf başına %0.07 ve gerçek funding.
- **Test bölümleri:** IS (in-sample, optimizasyon dönemi) 2020–2023, OOS (out-of-sample, optimizasyonda kullanılmayan dönem) 2024–2026.
- **Kod:**
  - `algo/daily.py`: veri ve özellikler
  - `algo/strategies_daily.py`: stratejiler
  - `algo/run_daily.py`: koşturma ve değerlendirme
  - `algo/final_daily.py`: nihai parametreler

Kısaltmalar: WR = kazanma oranı, PF = kâr faktörü (toplam kâr / toplam zarar), R = işlem başına riske edilen tutar, MAR = yıllık getiri / en büyük düşüş.

## 1. Dokümanlardan dayanak

| İlke | Kaynak (`metinler/`) |
|---|---|
| "Haftalık grafik en güçlü trenddir… Günlük ölçülü hareketler bize haftalık hedefe bir giriş sağlar"; "Haftalık trendlere en çok saygı gösterin" | Halsey, Bölüm 7 (PDF s.93–96) |
| Elder: tüm zaman dilimleri aynı yönü gösteriyorsa "en az dirençli yol" bulunmuştur | Halsey, Elder alıntısı (PDF s.92–93) |
| %50 geri çekilme (HWB) girişi; %61.8 başarısızlık seviyesi; −%23.6 hedef | Halsey, Bölüm 2 |
| Turtle: 20 günlük kırılım, 10 günlük ters kanal çıkışı, stop 2N | Pruitt, Box 3.1 |
| Ortalamaya dönüş testleri günlük mumlarla; en iyi aday zaman dilimi günlük | Davey, Bölüm 4–5 |
| Percent Decrease (#5) ve Connors RSI(2) ailesi; kısa vadeli ortalamaya dönüş | Davey, Bölüm 5 |
| Hızlı (6–11 gün) ve yavaş (220–300 gün) ortalama ile uzun trend yakalama | D'errico, s.~3530 |

## 2. Teşhis: hangi haftalık yön filtresi gerçekten öngörüyor?

Filtre "yukarı" iken ile "aşağı" iken sonraki 20 günlük getiri farkı (baz puan, ana evren):

| Haftalık yön filtresi | IS farkı | OOS farkı |
|---|---|---|
| **Elder Impulse** (haftalık EMA13 eğimi ve MACD histogram eğimi aynı yönde) | **+625** | **+335** |
| Haftalık Donchian(10) kırılım durumu | +231 | +240 |
| BTC haftalık > EMA20 | +752 | +210 |
| Haftalık kapanış > EMA10 | +452 | +168 |
| Haftalık kapanış > EMA40 | +567 | **−251** (OOS'ta ters) |

**Sonuç:** basit uzun EMA filtresi 2024–26'da işe yaramıyor; önceki çalışmadaki bulguyla tutarlı. Elder Impulse ise iki dönemde de iki yönlü olarak anlamlı. Seçilen haftalık yön filtresi bu.

## 3. Test edilen ve elenen girişler

Sonuçlar `results/daily_grid*.csv` dosyalarında.

| Giriş | Sonuç | Neden |
|---|---|---|
| Elder Üçlü Ekran (haftalık yukarı + günlük RSI2 aşırı satım) | ❌ | PF 1.2–1.3; OOS ya da IS zayıf |
| Turtle 20 gün kırılım + haftalık Donchian yönü | ❌ | IS'te PF 2.4–3.2, OOS'ta yaklaşık 1.0 (aşırı uyum) |
| Turtle 20 gün kırılım + Elder yönü | ❌ | Kısmi kârla PF 1.2–1.3 |
| Elder Impulse ilk gün girişi | ❌ | OOS'ta PF yaklaşık 1.0–1.2; stres sonuçlarını birkaç uç işlem şişiriyor |
| Halsey ölçülü hareket, kitaptaki seviyelerle (%61.8 / %78.6 stop, tepe ve −%23.6 hedef) | ❌ | WR %52–54 ama PF yaklaşık 1.15 |
| **Halsey %50 geri çekilme, ATR stoplu + Turtle çıkışı** | ✅ **D1** | |
| **Kapitülasyon dönüşü + Elder "kırmızı değil"** | ✅ **D2** | |

## 4. Nihai stratejiler

### D1 — Elder haftalık yön + Halsey %50 geri çekilme (long ve short)
- **Yön (1W):** Elder Impulse yeşilse (haftalık EMA13 yükseliyor ve MACD histogramı yükseliyor) yalnızca long, kırmızıysa yalnızca short.
- **Kurulum (1D):** son 20 günün yükselişinde yeni bir tepe yapılmış olmalı. Fiyat 20 günlük aralığın orta noktasına (%50) iner ve günü bu seviyenin üstünde kapatır. Short tarafı simetrik.
- **Giriş:** ertesi günün açılışında.
- **Stop:** 3 × ATR20 (günlük).
- **Çıkış:**
  1. Pozisyonun %33'ü 0.6R kârda kapatılır ve stop başabaşa çekilir.
  2. Kalan pozisyon Turtle çıkışıyla, yani ters yöndeki 10 günlük kanal kırılınca kapanır.
  3. En fazla 90 gün tutulur.
- **Risk:** işlem başına %1, aynı anda en fazla 10 pozisyon.

### D2 — Elder "kırmızı değil" + günlük kapitülasyon dönüşü (yalnızca long)
- **Yön (1W):** Elder Impulse kırmızı değilse. Bu, Elder'in "impulse kırmızıyken long açma" kuralı.
- **Kurulum (1D):** coin 2 günde en az %20 düşmüş olmalı.
- **Giriş:** ertesi günün açılışında.
- **Stop:** 3 × ATR20.
- **Çıkış:** kapanış 5 günlük ortalamanın (SMA5) üstüne çıkınca (Connors çıkışı) ya da en fazla 15 gün sonra.
- **Risk:** işlem başına %1, aynı anda en fazla 10 pozisyon.

## 5. Sonuçlar (maliyet ve funding dahil)

### İşlem bazında

| | Evren | İşlem sayısı | WR | PF | PF IS / OOS | WR IS / OOS | Kârlı coin |
|---|---|---|---|---|---|---|---|
| **D1** | Ana | 810 | **%49.1** | **1.58** | 1.64 / 1.51 | %49.5 / %48.7 | 18/25 |
| D1 | Stres | 618 | %48.9 | 1.33 | **1.08** / 1.67 | %48.3 / %49.6 | 11/20 |
| **D2** | Ana | 143 | **%76.9** | **4.14** | 5.12 / 2.68 | %76.2 / %79.0 | 21/24 |
| D2 | Stres | 156 | %68.0 | 2.33 | 2.33 / 2.31 | %66.7 / %71.4 | 15/19 |

### D1 yıllara göre (ana evren, işlem sayısı / WR / PF)

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|
| 63 / %36.5 / 3.66 | 113 / %54.0 / 1.43 | 84 / %46.4 / 1.26 | 158 / %53.2 / 1.11 | 170 / %45.3 / 1.65 | 151 / %55.6 / 1.54 | 71 / %42.3 / 1.18 |

\* 2026 yılı 8 Ekim'e kadar.

### Portföy (açık pozisyonlar dahil, sabit risk, bileşiksiz)

| | Yıllık getiri | En büyük düşüş (açık pozisyonlar dahil) |
|---|---|---|
| D1 (ana) | %16.1 | −%22.8 |
| D2 (ana) | %2.9 | −%5.2 |
| **D1+D2 eşit ağırlık (ana)** | **%8.3** | **−%11.3** |
| D1+D2 eşit ağırlık (stres) | %4.9 | −%16.3 |

- **D1–D2 günlük korelasyonu:** 0.07.
- **Kombine yıllık getiri (ana evren):** 2020 +%5, 2021 +%31, 2022 +%3, 2023 +%7, 2024 +%7, 2025 +%5, 2026 (9 ay) +%1. Her yıl pozitif.

## 6. Sağlamlık

- **D2 parametre platosu:** düşüş eşiği (%15 / %20 / %25), gün sayısı (2 / 3 / 4) ve stop (2.5 / 3 / 4 ATR) değiştikçe sonuçlar düzgün ve tek yönlü değişiyor. 54 komşu ayarın %75'inde üç testin (IS, OOS, stres) en kötüsünde bile PF > 1.3 (`results/daily_grid7_capit.csv`).
- **D1 parametre platosu:** geri çekilme penceresi 15–20 gün ve stop 3 ATR bölgesinde üç testte de WR ≥ %45 ve PF ≥ 1.30 (`results/daily_grid4_half.csv`).
- **D1 varyantları:** sadece long sürümde PF daha yüksek (1.77; stres evreninde 1.58), ama portföyde getiri/düşüş oranı düşük (0.63). Short'ları BTC filtresine bağlamak iyileştirmedi. Sade sürüm korundu.

## 7. Riskler ve sınırlamalar

1. **D1 stres evreninin IS döneminde zayıf** (PF 1.08). Özellikle 2020 (PF 0.08) ve 2023'te zarar etti; stres evreninde 20 coinden yalnızca 11'i kârlı. D1, yalnızca 2024–26 ve ana evrende güçlü. Bu yüzden ana sistemden daha düşük güvenle değerlendirilmeli.
2. **D2 az işlem yapıyor:** ana evrende yılda yaklaşık 21 işlem. %1 riskle getiri düşük (yıllık %3). Düşüşü çok küçük olduğu için risk %2'ye çıkarılabilir, ama küçük örneklemde PF 4–5 gibi değerler fazla iyimser olabilir.
3. **D2, kağıt botundaki B (1H kapitülasyon) ile aynı fikre dayanıyor.** Farklı zaman dilimi ve eşikte çalışıyor, ama birlikte kullanılırsa riskler kısmen çakışır.
4. **Günlük mumda aynı gün hem stop hem hedef görülürse önce stop varsayılıyor.** Bu muhafazakâr bir varsayım; gerçek sonuçlar biraz daha iyi olabilir.
5. **1H sistemine göre:** bu çalışma daha az işlem, daha düşük getiri ve daha kolay uygulanabilirlik sunuyor (günde bir kontrol yeterli).
