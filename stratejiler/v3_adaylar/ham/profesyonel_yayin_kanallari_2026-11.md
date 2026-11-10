# Profesyonel trader'ların strateji yayımladığı kanallar (2026-11-07 haritası)

*Tarih: 2026-11-07. Bu bir kaynak haritası; kanalların çoğu liste/affiliate sitesi üzerinden tanıtılıyor, bağımsız doğrulama yok. Ayrıca yalnız arama sonuçlarına dayanıyor; sayfaları doğrudan okuyarak doğrulanmalı.*

## 1. Kurumsal / yarışma platformları (en yüksek doğrulama)
| Kanal | Ne yayımlıyor | Güvenilirlik | Bizim için |
|---|---|---|---|
| **Quantiacs** (contests) | Yarışma stratejileri; 2026'da Contest 25 ($2M havuz); en iyi 7 gerçek sermayeyle ağırlık alıyor; korelasyon filtresi, kopya strateji diskalifiye | Yüksek (canlı performans) — ama kodlar kamuya açık değil | Yarışma sonuçları ve kriterler öğretici; **erişim için izin gerekir** (`quantiacs.com` erişilemiyor) |
| **Numerai** | Haftalık turnuva, obfuscated veri; MMC ölçümü; NMR stake | Yüksek (canlı katkı ölçümü) | Kod açık değil; yöntem bilgi olarak |
| **WorldQuant BRAIN** | Global Alphathon (2025'te ~80k katılımcı) | Orta | Alpha fikirleri; kapalı platform |
| **QuantConnect** | Quant League 2024–2025 (öğrenci yarışması, durumu belirsiz); yeni "Strategies" platformu | Orta | LEAN motoru açık; strateji kütüphanesi için izin gerekir |

## 2. Akademik ve yarı-akademik (kodlu, bağımsız)
| Kanal | Örnek (2026) | Not |
|---|---|---|
| **arXiv** | 2602.10785 — EMA kesişimi BTC, iki yürüyen test, sonuç pencere boyuna bağlı; kod bağlantısı var | Dürüst, mütevazı sonuç |
| **arXiv** | 2512.12924 — mikroyapı sinyalleri, 34 yürüyen dönem, yıllık %0.55 | Yazarlar beklentiyi düşük tutuyor |
| **SSRN** | 6467818 — BTC RSI (+%1.6) / MA kesişimi (−%3.6), OOS | Küçük getiri, al-tutu geçiyor |
| **SSRN "151 Trading Strategies"** | psdon/paper-strategy-lab: makale stratejilerinin Sharadar verisiyle yeniden testi | Akademik kuralların yeniden üretimi |
| **Quantpedia** | Her ay yeni makale özeti; ortalama bir stratejinin kuralı ve kaynağı | Kod değil ama kural özetleri iyi; izin gerekir |

## 3. Bülten / blog (Substack, siteler)
| Kanal | Tür | Güven | Not |
|---|---|---|---|
| **Quantocracy** | Aggregator (Quantpedia, Alpha Architect, Robot Wealth, Alpha Scientist, Alvarez QT'den linkler) | Orta (seçilmiş linkler) | En iyi başlangıç noktası; **erişim izni gerekir** |
| **Quantified Strategies** (Substack) | Her gün bir kurallı strateji, backtest ile | Orta-düşük (kendi backtest, slippage yok) | Kural yapısı açık |
| **Robot Wealth** | Pairs trading, stat-arb, LLM ile strateji üretme uyarısı | Yüksek (uzun geçmiş, dürüst) | Pairs trading bizim kapsamda değil |
| **Alpha Architect** | Faktör yatırımı, factor zoo eleştirisi | Yüksek (akademik temelli) | Portföy katmanı (karar 23) için ilgili |
| **Rogue Quant** | Akademik makalelerden backtest'li stratejiler, ücretli üyelik | Orta | Ücretli içerik |
| **TradeQuantiX** | Ücretli üyelik, GitHub kodu, Discord, canlı model portföy | Orta (kendi beyanı) | Kod kısmı ilginç |
| **Systematic Traders** (Substack) | Haftalık derleme; tek örnek: ETF rotasyonu + 4 bağımsız strateji, Sharpe 0.9→1.7 | Düşük-orta (tek örnek) | Portföy kavramı |

## 4. Forumlar ve topluluklar
| Kanal | Yapısı | Güven | Not |
|---|---|---|---|
| **Elite Trader** | Uzun geçmiş (1997), ileri düzey tartışma; ~91–100k üye | Orta (üye sayısı tutarsız) | Sistem tartışmaları; hayatta kalma yanlılığı |
| **Trade2Win** | UK/US hisse, vadeli, forex | Orta-düşük | Kendi tanıtımı |
| **MQL5 community** | Forex EA ve strateji testi, en büyük otomatik sistem forumu | Düşük-orta (çok EA satışı) | Martingale riski yüksek |
| **Futures.io** | Vadeli işlem stratejileri | Orta | Yoğun kullanıcı kitlesi |
| **Quant Stack Exchange / r/algotrading / Wilmott** | Soru-cevap, kod tartışması | Orta-yüksek (tartışılabilir) | Kanıt aranabilir |
| **TradingView Ideas** | Kullanıcı fikirleri; Pine kütüphanesi >100k script | Düşük (çoğu sonuç pazarlama) | Açık kaynak Pine kodu var, sonuç doğrulanmalı; Paid Space ücretli |

## 5. Discord / Telegram / YouTube / ücretli topluluklar
- **Açık kaynak bot toplulukları** (Freqtrade, OpenTrader, OctoBot Discord'ları): kod açık, sonuç paylaşımı karışık.
- **Ücretli gruplar** (Chart Hackers, Sniper Trades vb.): canlı sinyal ve eğitim; performans kanıtı çoğunlukla yok. Liste sitelerinde yer alıyor.
- **YouTube (2026 Claude Code backtest videoları):** kodlar çoğunlukla ücretli topluluk arkasında; ücretsiz kod bulunamadı.
- **Uyarı:** Garanti getiri vaadi, sürekli sinyal satışı, doğrulanmış kayıt paylaşmama — bunlar kırmızı bayraklar (kaynak: sektör rehberleri).

## 6. Bizim için değerlendirme
1. **En değerli, doğrulanabilir:** Quantiacs/Numerai (canlı performans), arXiv/SSRN'de kodlu ve dürüst çalışmalar, Quantpedia/Alpha Architect (akademik temelli kurallar).
2. **Kural fikri alınabilir ama sonuç güvenilmez:** Quantified Strategies, Rogue Quant, TradingView Ideas, MQL5, Discord grupları.
3. **Pratik öneri:** Önce kodlu ve OOS raporlu kaynaklar (arXiv/SSRN), sonra kurumsal yarışma sonuçları, sonra bültenler. Ücretli gruplardan sonuç kanıtı istenmeden alınmamalı.

## 7. Erişim sınırları (bu araştırmada)
- `quantiacs.com` ve `quantocracy.com` **ortamda izinli değil** → yarışma ve aggregator sayfaları okunamadı.
- Bu iki kaynak için izin verilirse doğrudan okunabilir.
