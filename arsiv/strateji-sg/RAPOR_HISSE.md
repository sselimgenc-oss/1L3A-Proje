# KGT v3 ve KMN — Hisse / Emtia Testi (Magnificent 7, BIST, Altın, Brent)

**Tarih:** 2026-10-09
**Kod:** `backtest/hisse.py`
**Veri:**
- `veri_dis/`: Yahoo Finance, GitHub sunucusunda indirildi (`araclar/veri_hisse.py`).
- `data/XAUUSD_H1`, `data/UKOIL_H1`: ilk aşama, 2020–2023.
- `sonuclar/hisse/ozet.csv`: test sonuçları.

**Dönemler:**
- **Saatlik (KGT):** hisselerde 2023-11 → 2026-10 (yaklaşık 3 yıl), altın ve Brent'te 2024-05 → 2026-10. Altın ve Brent için ayrıca 2020–2023.
- **Günlük (KMN):** 2020-01 → 2026-10.

**Uyarlama:**
- **KGT:** seans mumları, pivot/CPR bir önceki işlem gününden; kurallar kripto ile aynı.
- **KMN:** her grup kendi içinde sıralanır. Mag7'de en güçlü 2 long, en zayıf 2 short; BIST'te 3 long, 3 short.
- **Masraf (taraf başına):** ABD %0,03, BIST %0,10, emtia %0,03.
- **BIST:** TL bazlı. USD karşılığı USDTRY ile hesaplandı. Boştaki TL nakdin faizi hesaba katılmadı.

## Sonuçlar

| Grup | Strateji | Yıllık | Maks. düşüş | Sharpe | Kazanma | PF | Kıyas: al-tut (aynı dönem) |
|---|---|---|---|---|---|---|---|
| **Mag7** | KGT, %0,4 risk | %11,2 | %11,8 | 1,16 | %48 | 1,92 | %34,0 / düşüş %29,8 / Sharpe 1,22 |
| **Mag7** | KGT, %1 risk | **%20,0** | **%15,7** | **1,43** | %50 | 1,85 | ″ |
| Mag7 | KMN (long/short) | %−0,4 | %25,5 | 0,03 | — | — | |
| Mag7 | Momentum long-only | %34,8 | %53,4 | 1,27 | — | — | Eşit ağırlık al-tut %37,1 / %49,4 / 1,39 |
| BIST | KGT, %0,4 risk (TL) | %7,3 | %14,3 | 0,79 | %47 | 1,45 | Al-tut %34,1 TL / %20,2 / 1,22 |
| BIST | KGT, %1 risk (TL) | %14,8 | %15,9 | 1,03 | %49 | 1,50 | ″ |
| BIST | KGT, %0,4 risk (USD) | %−11,0 | %35,6 | −1,06 | | | |
| BIST | KMN (TL) | %−2,0 | %31,0 | −0,15 | — | — | |
| BIST | Momentum long-only (TL / USD) | %60,3 / %17,3 | %31,5 / %40,1 | 1,95 / 0,76 | — | — | Eşit ağırlık al-tut %58,9 / %16,3 USD |
| Emtia (altın + Brent), 2024–26 | KGT | %6,1 | %8,7 | 0,94 | %63 | 3,49 | Al-tut %18,3 / %25,7 / 0,87 |
| Emtia, 2020–23 | KGT | %4,0 | %11,0 | 0,38 | %50 | 1,68 | |

**Yıllık getiri, Mag7 KGT (%1 risk):** 2024 +45, 2025 +26, 2026 (9 ay) −2,5.

**Mag7'de kârın kaynağı (toplam R):**
- Yüksek: NVDA +30,5, META +20,8, GOOGL +18,9.
- Düşük: TSLA +4,6, AAPL +3,9, AMZN +2,1.
- Zararda: MSFT −4,7.

## Değerlendirme
1. **KGT Mag7'de çalışıyor.**
   - %1 riskte Sharpe 1,43, kazanma %50, PF 1,85. Kriptodaki KGT'ye yakın: Sharpe 1,28, kazanma %45.
   - Al-tutun getirisini (%34) geçmiyor, ama düşüşü yarı yarıya (%16'ya karşı %30).
   - Örneklem kısa (yaklaşık 3 yıl, 173 işlem), kâr 3 hisseden geliyor. Güven düzeyi kriptodakinden düşük.
2. **KGT BIST'te zayıf.**
   - TL bazında %7–15. Aynı dönemde TL faizi ve enflasyon bundan yüksek, USD bazında zarar.
   - Al-tut ve endeks çok daha iyi. Önerilmez.
3. **KGT altın ve Brent'te düşük getirili ama istikrarlı.**
   - Kazanma %50–63, PF 1,5–3,9, ama yıllık %3–6.
   - Tek pozisyon %25 sınırı nedeniyle risk artırılınca getiri artmıyor.
   - Bu varlıklar CPR kırılımına uygun trend günleri üretiyor ama hareketler küçük.
4. **KMN hisse ve emtiada çalışmıyor.**
   - Mag7'de 7, BIST'te 11 hisse ile kesitsel momentumun kazancı yok (Sharpe ≈ 0).
   - Kriptoda 30 coin ve çok büyük getiri farkları vardı. Az sayıda, birbirine çok bağlı hissede bu fark oluşmuyor.
   - Long-only momentum, eşit ağırlıklı al-tutla aynı sonucu veriyor; ek değer yok.
   - BIST'te açığa satış kısıtlı olduğu için KMN zaten pratik değil.
5. **Sonuç.** İki strateji en iyi kriptoda çalışıyor. Hisse tarafında yalnız **KGT + Mag7** umut verici. İleride kullanmak için iki adım gerekir:
   - daha uzun saatlik veriyle (2020'den) doğrulamak,
   - hisse sayısını genişletmek, örneğin Nasdaq-100.
