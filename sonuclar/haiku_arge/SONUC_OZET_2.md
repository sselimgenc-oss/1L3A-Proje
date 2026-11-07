# Elenen havuz — daytrade, scalp ve sağlamlık sonuçları (Ar-Ge kolu, ara özet)

## Walk-forward (karar 13), 5 enstrüman
- **Swing** (42 strateji × 5 enstrüman × 4s/1d): 420 görev, 1 geçen → `swing__rsi-momentum-esik` DK_XAU 1d.
- **Daytrade** (38 × 5 × 1h/30m): 380 görev, 2 geçen → XU30 1h: `daytrade__donchian-kirilim` (PF 1.68, 50 işlem)
  ve `dis__atr-rsi-liwei` (PF 1.77, 51 işlem). **Her ikisinin OOS'u yalnız 2025-01 → 2025-09 (3 pencere, ~9 ay).**
- **Scalp** (40 × BTCUSDT × 15m/30m): 80 görev, 0 geçen. Diğer dört enstrümanda dakikalık veri yok.
- Hatalar: 30m / 15m için dakikalık veri olmayan enstrümanlarda (158 satır, kayıtlı); funding verisi olmayan carry stratejileri.

## Sağlamlık (sağlamlik.py kapıları), WF'de geçen 3 aday
| Aday | Kapı başarısız | Not |
|---|---|---|
| swing__rsi-momentum-esik, DK_XAU 1d | K2 rastgele giriş, K3 bootstrap alt sınır | Al-tut dönemde %83.5 vs strateji %6.8 |
| daytrade__donchian-kirilim, XU30 1h | K2 rastgele giriş (p = 0.053 > 0.05) | Sınırda |
| dis__atr-rsi-liwei, XU30 1h | K2 rastgele giriş (p = 0.058), K3 bootstrap alt sınır | |

**Sonuç: sağlamlık paketinden geçen aday yok.** Kazanan yok. Scalp'te de WF'de geçen yok.

## Deneme sayısı
- `deneme_kaydi.jsonl` (bu Ar-Ge kolu): tüm koşular toplamı, deflated Sharpe için alt sınır olarak kullanılmalı.
