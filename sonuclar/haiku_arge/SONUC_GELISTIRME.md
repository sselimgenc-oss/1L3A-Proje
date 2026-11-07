# Aşama 4 sonucu — sınırdaki adayların geliştirilmesi (ön kayıta göre)

Ön kayıt: `GELISTIRME_ON_KAYIT.md`. 3 aday × 4 varyant = 12 varyant, 5 enstrüman.

## Walk-forward (karar 13)
- 120 sonuç, **5 geçti**: 4'ü XU30 1h (`don-notrend`, `liwei-ema200`, `liwei-noband`, `liwei-vol`), 1'i SPX 1d (`rsi-ema-vol`).
- XU30 1h OOS yalnız 2025-01 → 2025-09 (3 pencere, 50–60 işlem); dört varyant aynı işlemleri paylaşıyor, bağımsız kanıt değil.

## Sağlamlık (K2 rastgele giriş, K3 bootstrap alt sınır)
| Varyant | Enstrüman | Kapı başarısız |
|---|---|---|
| don-notrend | XU30 1h | K2 (p = 0.104) |
| liwei-ema200 | XU30 1h | K2 (p = 0.184) |
| liwei-noband | XU30 1h | K2 (p = 0.214), K3 |
| liwei-vol | XU30 1h | K2 (p = 0.224), K3 |
| rsi-ema-vol | SPX 1d | K2 (p = 0.054, eşik 0.05 — sınırda), bootstrap oranı 0.93 |

**Sonuç: hiçbir varyant sağlamlıktan geçmedi.** Ön kayıt kuralına göre bu adaylar "geliştirilemedi" olarak raporlanır.

## Not
- Üç adayın orijinali de (donchian XU30, liwei XU30, rsi-momentum DK_XAU) sağlamlıktan kalmıştı; varyantlar bu durumu düzeltmedi.
- Deneme sayısı arttı (`deneme_kaydi.jsonl`); deflated Sharpe'ta bu koşular dahil edilmeli.
