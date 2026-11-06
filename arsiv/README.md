# Arşiv — kapatılan önceki projeler

Kullanıcı 2026-11-06'da `algo-sg`, `strateji-sg`, `swing-sg` repolarını kapattı; işe yarayan kısımlar buraya alındı.
Bu klasör **yalnızca başvuru içindir**: 1L3A kodu buradan import etmez. Bir şey kullanılacaksa önce 1L3A
standartlarına (Decimal, borsa filtreleri, lookahead testi) göre yeniden yazılır ve denetlenir.

| Klasör | Önceki proje | Kaynak commit |
|---|---|---|
| `algo-sg/` | Kripto 25 coin, 1S/4S/1G; Strateji A (4S Donchian+hacim), B (kapitülasyon) + kağıt bot | `algo-sg/.kaynak_commit` |
| `strateji-sg/` | KGT (CPR+R1), KMN (kesitsel momentum), EPA, HGT, PA/Brooks, TradingView elemesi + kağıt botlar | `strateji-sg/.kaynak_commit` |
| `swing-sg/` | Günlük swing S1/S2/S3 + trend kolları (kripto, Mag7, BIST, emtia) + kağıt botlar | `swing-sg/.kaynak_commit` |

Alınanlar: kod, raporlar/denetimler, backtest sonuç CSV'leri, GitHub Actions iş akışları, kağıt bot son durumları.
**Alınmayanlar:** PDF'ler ve `metinler/` (telif + 1L3A kuralı: kaynak kitaplar repoya girmez), piyasa verisi
(`data*/`, `veri_dis/` — data.binance.vision / Yahoo'dan yeniden üretilebilir).

Lisans: `algo-sg/dis_kaynak/ft/` freqtrade topluluk stratejileri (GPLv3), `strateji-sg/tv/pine/` TradingView
Pine betikleri (her betiğin kendi lisansı). Sadece başvuru; 1L3A'ya kopyalanmaz.
