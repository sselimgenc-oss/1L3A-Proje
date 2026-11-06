# GÜNCEL ÖNERİ (2026-10-09, Faz 9 denetiminden sonra): KGT v3 (%50) + KMN (%50)

Denetim raporu: `DENETIM.md`. Sonucu şişiren hata bulunmadı. Düzeltmelerden sonraki sayılar:

| | Kazanma | Yıllık | Maks. düşüş | Sharpe | 2022 | 2025 |
|---|---|---|---|---|---|---|
| KGT v3 | %45,5 (işlem) | %33,6 | %29,5 | 1,28 | −20 | +14 |
| KMN | %68 kârlı ay | %55,2 | %18,1 | 1,86 | +18 | +71 |
| **KGT %50 + KMN %50** | %60 kârlı ay | **%45,7** | **%15,6** | **1,99** | −2 | +41 |

- **KGT v3:** dar CPR + R1 kırılımı + günlük trend; stop fiilen 3×ATR(1S); 1R'de %15 kısmi kâr; 4S trend dönüşünde çıkış.
- **KMN:** 151 Strateji §3.1, piyasa nötr kesitsel momentum. 14 günde bir, hacme göre ilk 30 coin; son 14 günün ortalama getiri / σ değerine göre en iyi 5 long, en kötü 5 short; ağırlık ters oynaklıkla.
- **Gerçekçi beklenti:**
  - KGT: yıllık %25–33.
  - KMN: yıllık %25–40, düşüş %20–25.
  - Birleşim: yıllık %35–45, düşüş %15–20.
  - 2021'in olağanüstü yılı (+%215) ve genç coinler KMN'nin backtest sonucunu büyütüyor.
- **Sinyal:**
  - KGT: `python3 -m backtest.kripto_sinyal --sermaye <KGT payı>`, her saat.
  - KMN: `python3 -m backtest.momentum_sinyal --sermaye <KMN payı/2>`. 14 günde bir çalıştırılır; 2 alt portföy 7 gün arayla dengelenir, aradaki günlerde pozisyonlara dokunulmaz.

---|---|---|---|---|---|---|
| KGT v3 tek başına | %45 (işlem) | %33 | %31 | 1,26 | −20 | +14 |
| KMN tek başına | %51 (pozisyon), %65 kârlı ay | %43 | %16 | 1,69 | +18 | +57 |
| **KGT %50 + KMN %50** | %63 kârlı ay | **%40** | **%15** | **1,90** | −2 | +35 |

- **KMN (Kesitsel Momentum, Piyasa Nötr; 151 Trading Stratejisi §3.1):**
  - **Seçim:** her 14 günde bir, hacme göre ilk 30 coin arasında son 14 günün riske göre düzeltilmiş getirisi (ortalama / σ) en iyi 5 coin long, en kötü 5 coin short.
  - **Ağırlık:** ters oynaklık.
  - **Bağımsızlık:** KGT ile korelasyon 0,20.
- **Gerçekçi beklenti:** KMN için yürüyen pencere testi daha zayıf (Sharpe 0,6). Bu yüzden KMN'den Sharpe 1,0–1,3 beklenmeli. Birleşim yine de KGT'den belirgin şekilde daha iyi.
- **Ayrıntı:** `RAPOR_S2.md`. Ortalamaya dönüş (4S/1G, Bollinger/RSI/IBS) test edildi, başarısız.
- **Sinyal:**
  - KGT: `python3 -m backtest.kripto_sinyal --sermaye <KGT payı>`, her saat.
  - KMN: `python3 -m backtest.momentum_sinyal --sermaye <KMN payı/2>`, 14 günde bir, 2 alt portföy 7 gün arayla.

---

# Proje Sonucu — Kısa Özet (2026-10-09)

**Önerilen strateji: KGT v3 (Kripto Günlük Pivot Kırılımı + Trend Takibi)** — ayrıntı: `RAPOR_KRIPTO.md` (v3 bölümü)

**Kurallar:**
- **Evren:** Binance USDT-M vadeli, her ay hacme göre ilk 15 coin. Yalnız long.
- **Yön (1G):** günlük EMA10 > EMA20 **ve son günlük kapanış EMA20'nin üstünde** (v3, Brooks).
- **Giriş (1S):** günün CPR'si dar iken 1 saatlik kapanış önceki günün R1 seviyesini yukarı keserse. Stop S1.
- **Yönetim:** +1R'de pozisyonun %15'i satılır, stop başabaşa çekilir.
- **Çıkış:** 4 saatlik trend dönünce (EMA21 < EMA50).
- **Risk:** işlem başına %0,4, en fazla 5 pozisyon. Strateji 6 farklı gün başlangıcıyla, sermaye 6'ya bölünerek çalıştırılır.

**Sonuç (2020–2026/09, masraf ve fonlama dahil):**

| | Kazanma | PF | Yıllık | Maks. düşüş | Sharpe |
|---|---|---|---|---|---|
| **KGT v3 (%0,4 risk)** | **%45** | **2,00** | **%33** | **%31** | **1,26** |
| KGT v2 (%0,5 risk) | %44 | 1,95 | %40 | %38 | 1,27 |
| BTC al-tut | — | — | %44 | %77 | 0,91 |

- **Test dönemi (2024–2026/09):** kazanma %47, yıllık %28,5, düşüş %19.
- **2022 ayı yılı:** −%20 (v2'de −%25).
- **Risk ayarı:** sonuçlar riskle doğrusal ölçekleniyor. %0,25 risk ≈ yıllık %21, düşüş %19 (doğrusal tahmin). %0,5 risk: yıllık %39, düşüş %36 (test edildi).
- **3 pozisyon:** 5 pozisyondan kötü çıktı, kullanılmıyor.

**Faz 6'da Brooks metinlerinden denenip elenenler:**
- Salınım dibi iz süren stop
- Doruk filtresi
- Günde ikinci giriş
- Kârdaki pozisyona ekleme
- N günlük zirve kırılımı
- NR4/NR7/iç gün
- Haftalık trend filtresi
- Kırılım geri çekilmesi girişi

Yalnız "kapanış > EMA20" kuralı her testte (komşu EMA uzunlukları, maliyet ×2, evren 20) tutarlı iyileşme verdi. İyileşme küçük: bu yapının sınırına yakınız.

**Önceki fazlarda elenenler:**
- 5dk/1s seans stratejileri
- Galen Woods kurulumları
- SKA
- Brooks Yüksek 1/2
- Short ve BTC rejim filtreleri

**Kullanmadan önce:**
- 2–3 ay kâğıt üzerinde ileri test.
- Bir yılı zararla kapatma olasılığı ~%16 (Monte Carlo).

**Sinyal:** `python3 -m backtest.kripto_sinyal --sermaye <USDT>`, her saat başı birkaç dakika geçe çalıştırılır.

---

## Kullanıcının EMA 8/21/55 stratejisi (EPA) — test sonucu
Ayrıntı: `RAPOR_EPA.md`, analiz: `ANALIZ_EMA_STRATEJI.md`

- **Çalışan kısım (EPA-B):** günlük EMA 8/21/55 trendi + 4 saatlik sıkışma kırılımı + hacim teyidi (≥ 2 kat).
  - %0,5 riskte kazanma %49, PF 2,0, yıllık %17, düşüş %18, Sharpe 1,31.
  - 4 mum hizalamasının hepsinde ve 3 kat maliyette kârlı; rastgele girişlerin %100'ünü geçiyor.
  - 2024 sonrası zayıf: yıllık %11; 2025–2026 neredeyse yatay.
- **Çalışmayan kısım (EPA-A):**
  - Pullback + hammer/engulfing: en iyi OOS Sharpe 0,4.
  - Mum şartı katkı yapmıyor, trend çizgisi zarar veriyor, günlük yatay filtre zarar veriyor.
- **KGT ile korelasyon 0,77.**
  - %70 KGT + %30 EPA-B: yıllık %28, düşüş %26, Sharpe 1,32 (yalnız KGT: %33 / %31 / 1,26).
  - Ana öneri KGT v3 olarak kalıyor; EPA-B düşüşü azaltmak için ikinci strateji olabilir.
