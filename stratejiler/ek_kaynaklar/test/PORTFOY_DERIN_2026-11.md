# Portföy stratejileri — derin sağlamlık testi (2026-11-07)

**Ön kayıt (sonuçlar görülmeden yazıldı):** Kıyas karar 24 (OOS net>0, Sharpe≥0.5, DD≤%20, ≥20 yeniden dengeleme). Nakit: SHY. Komşu parametreler raporlanır, seçilmez. Dönem 2006-01 — 2025-10-31 (kilit sonrası yok). Maliyet %0.1 (×2, ×3 testleri).

## Ana sonuçlar (nakit SHY ile)
| Strateji | Yıllık | DD | Sharpe |
|---|---|---|---|
| SPY al-tut | %11.0 | −%50.8 | 0.77 |
| GTAA 10 aylık SMA (5 varlık) | %5.6 | −%11.3 | **0.86** |
| Momentum 12 ay, ilk 3/8 | %8.7 | −%23.4 | 0.74 |

## Sağlamlık
- **GTAA komşuluğu:** SMA 6/8/10/12 — dördü de Sharpe'ta SPY'ı geçiyor (0.85–0.90), DD −%9 ile −%11.
- **Momentum komşuluğu:** 9 kombinasyon (lookback 6/9/12 × ilk 2/3/4). Sharpe>SPY oranı %67; ama DD≤%20 oranı yalnız %44. Ana kural (12/3) DD kapısında başarısız.
- **Blok bootstrap (blok 6 ay), Sharpe farkı vs SPY, %95 aralık:** GTAA [−0.33, +0.47] — **sıfırı kapsıyor, anlamlı değil**. Momentum [−0.54, +0.38] — anlamlı değil.
- **Rastgele seçim kıyası (1000 simülasyon, 3/8 rastgele):** medyan Sharpe 0.44, %95 0.63. Momentum 0.74 → sıralama rastgele seçimden **üstün** (tek başına anlamlı bir bilgi, ama bootstrap belirsizliği var).
- **Maliyet:** ×3'te de sıralama korunuyor (GTAA 0.80, momentum 0.68).

## Karar 24 kapıları
- **GTAA:** net>0 ✓, Sharpe 0.86 ≥0.5 ✓, DD −%11 ≤%20 ✓, ≥20 yeniden dengeleme ✓ → **kapıları geçiyor**, ama Sharpe farkı istatistiksel olarak sıfırdan ayırt edilemiyor.
- **Momentum:** DD −%23 > %20 → **geçmiyor**.

## Yorum ve sınırlar
- GTAA'nın avantajı ağırlıklı olarak düşüş kontrolünde; getiri al-tuttan düşük. Sharpe farkı belirsiz.
- Tek dönem, tek evren (5–8 ETF), nakit ve sektör ETF evreni bugünkü ETF'ler; hayatta kalma yanlılığı riski var.
- Kilit dönem zaten kullanılmış; bu sonuçlar paper trading (yeni veri) ile sınanmadan canlıya taşınmamalı.
- **Sonuç:** GTAA tipi düşük-risk portföy adayı (karar 24 kapılarını geçiyor, istatistik zayıf). Momentum DD kapısında düşüyor.
