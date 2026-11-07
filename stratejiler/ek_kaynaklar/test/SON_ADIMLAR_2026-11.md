# Son adımlar (2026-11-07)

## 1) GTAA paper trading önerisi
Ana proje oturumuna değerlendirme için iletildi (kod/ayar değişikliği istenmedi). Sorular: paper'a alınma, paper kabul ölçütü (≥8 hafta, DD ≤%15, beklenti aralığı), canlıya geçiş için kullanıcı onayı.

## 2) Geniş evrende portföy testi (kilit öncesi, 2006–2025-10, nakit SHY, maliyet %0.1)
Evren: 20 ETF (hisse, tahvil, kredi, TIPS, emtia, gayrimenkul, ülke ETF'leri, küçük şirket, QQQ).

| Strateji | Yıllık | DD | Sharpe | 2006–12 | 2013–19 | 2020–25 |
|---|---|---|---|---|---|---|
| SPY al-tut | %11.0 | −%50.8 | 0.77 | +%32 | +%159 | +%131 |
| GTAA 5 varlık (önceki) | %5.6 | −%11.3 | 0.86 | +%55 | +%37 | +%40 |
| **GTAA geniş (20 varlık, SMA10)** | %5.9 | −%12.1 | **0.87** | +%71 | +%31 | +%41 |
| Momentum 8 varlık (önceki) | %8.2 | −%23.4 | 0.71 | +%65 | +%46 | +%97 |
| **Momentum geniş (20 varlık, 12ay ilk 3)** | %3.0 | −%48.2 | **0.26** | +%18 | −%9 | +%68 |

Bootstrap (blok 6 ay) Sharpe farkı vs SPY: GTAA geniş [−0.39, +0.53] (sıfırı kapsıyor); momentum geniş [−0.96, −0.08] (sıfırın altında).

**Yorum:** GTAA kuralı evren değişiminde tutarlı (Sharpe 0.86–0.87, düşüş −%11–12). Momentum kuralı evrene çok duyarlı: 8 varlıkta iyi görünüyor, 20 varlıkta çöküyor. Bu, momentum sonucunun evren seçimine bağlı (kırılgan) olduğunu gösteriyor.

## 3) Erişilemeyen kaynaklar
- **Quant Stack Exchange (API):** izin eklendi, API çalışıyor. En çok oy alan sorular eğitim/veri odaklı; strateji sonucu içermiyor.
- **SSRN, Alpha Architect, Futures.io, Wilmott:** bot koruması (403 / Cloudflare). Koruma aşılmadı; bu kaynaklar erişilemez olarak kalıyor.
- **Reddit (JSON API dahil), Quantiacs, Discord, Telegram:** ağ düzeyinde kapalı veya içerik JavaScript ile yükleniyor; erişim yok.
