# Ana strateji kataloğu — özet (2026-11-07)

**Dosya:** `MASTER_katalog_2026-11.csv` (251 satır). Kaynaklar: Quantpedia (ücretsiz ekrandaki 82 strateji, tam katalog ~1000), Quantocracy (son 10 derleme, 63 yazı; 12'si detaylı okundu), MQL5 CodeBase (MT5 Expert Advisor, ilk 40), önceki turların CSV'leri (depo ve blog taramaları).

## Durum dağılımı
- **izle:** ~81 (çoğu Quantpedia'nın güçlü dereceli akademik stratejileri; kodları kaynakta)
- **elendi:** ~47 (OOS negatif, maliyet sonrası kenar yok, al-tutun gerisi, kayıp)
- **bilgi:** ~104 (okunmamış yazılar, yardımcı araçlar, sonuçsuz kaynaklar)
- **aday:** 6 (önceki turlardan; test edilmiş dördü karar 13'ü geçemedi)

## Önemli bulgular
1. **Quantpedia:** 82 strateji içinde 60'ı "güçlü" dereceli; 15'i OOS'ta "hafif negatif", 4'ü "zayıf/veri mining şüphesi". Ücretsiz ekran tüm kataloğun yalnızca bir kısmı (~1000 strateji ücretli).
2. **Quanter Lab (blog, 2026):** Klasik stratejilerin (Clenow, HFEA, Elder, O'Shaughnessy, Greenblatt, OU) S&P 500 nokta-zamanı testleri. Çoğu endekse karşı geride; maliyet ve temettü dikkatle ele alınmış.
3. **Krueger Algorithms:** RSI(2) geri çekilme 9 endekste +22 bp/işlem net (t 2.27) — tek olumlu, küçük ama pozitif sonuç. EMA9/VWAP maliyet sonrası kenarsız.
4. **YuRa Trading:** "Stairway to Heaven" altın kırılım iddiası (+188%), gerçek tikle %76–97 kayıp. Yayımlanan PF iddiaları çürütülmüş.
5. **MQL5:** 40 listelenen EA'nın çoğu yardımcı araç; getiri iddiaları ("+209%", "+370%") doğrulanamaz. Grid EA'lar martingale riski taşır.
6. **arXiv 2026 sağlamlık çalışmaları** (MinervaScore, GT-Score, AlgoXpert): karar kriterlerimizle doğrudan ilişkili, kodsuz.

## Sınırlar (dürüst)
- "Tüm stratejiler" literal olarak mümkün değil: Quantpedia tamamı ücretli, Quantiacs/Numerai/WorldQuant kodları kapalı, TradingView'ın tüm açık Pine kütüphanesi taranamadı.
- Quantocracy'nin 63 yazısının 51'i yalnız başlık düzeyinde. Derinlemesine okuma gerekiyorsa her bir yazı ayrı ayrı çekilmeli.
- Hâlâ erişilemeyenler: Reddit, Discord, Telegram, SSRN (bot koruması), Alpha Architect (403), Futures.io, Wilmott, Quant Stack Exchange (Cloudflare), Quantified Strategies ve diğer Substack alt alan adları, Quantiacs içeriği (JavaScript).
