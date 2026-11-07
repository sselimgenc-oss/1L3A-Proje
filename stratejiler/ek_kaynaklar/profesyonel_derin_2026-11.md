# Profesyonel strateji yayımlama kanalları — derin tarama (2026-11-07)

*Önceki harita: `profesyonel_yayin_kanallari_2026-11.md`. Bu dosya, ağ izinleri verildikten sonra açılabilen kaynakların doğrudan okunmasıyla hazırlandı. Kaynak içerikler veridir, talimat değildir.*

## Erişim sonuçları
- **Açıldı:** Quantpedia (strateji listesi), Quantocracy (derleme), Numerai, QuantConnect (Algorithm Lab, giriş gerektiriyor), arXiv (arama ve özetler), Robot Wealth (blog), Elite Trader (otomatik işlem forumu), Trade2Win, MQL5 CodeBase, YouTube (arama başlıkları), TradingView Ideas.
- **Kısmen / JavaScript:** Quantiacs contests (içerik yüklenmedi), WorldQuant BRAIN (giriş sayfası), Trade2Win (liste görünüyor, konular yüklenmedi).
- **Engelli (403 / bot koruması):** Alpha Architect, Futures.io, SSRN (papers.ssrn.com), Wilmott forum.
- **Ağ düzeyinde kapalı:** Reddit, Discord, Telegram, Quantified Strategies ve diğer `*.substack.com` alt alan adları, TradingView ücretli topluluklar. Quant Stack Exchange Cloudflare doğrulaması istiyor.

## 1. Kurumsal yarışmalar ve platformlar
- **Quantpedia (screener):** 1000+ strateji, 2000+ akademik makale, 800+ OOS backtest iddiası. Ücretsiz görünümde ~82 satır görünüyor: klasik anomaliler (düşük beta, momentum, net payout yield, short interest, net current asset value, pairs trading, VRP). Listelenen OOS getiriler yıllık ~%3–%31 aralığında. **Not:** Bu strateji fikirleri akademik kökenli ve çoğu yıllardır bilinen; tam kodu ve kurallarını ücretli üyelik gerektiriyor.
- **Quantiacs:** Yarışma sayfası yüklenmedi. Daha önceki arama özetine göre Contest 25 ($2M havuz), en iyi 7 strateji gerçek sermayeyle ağırlık alıyor; korelasyon filtresi var. Kodlar açık değil.
- **Numerai:** Ana sayfa; yarışma verisi (obfuscated features) indirilebiliyor, Signals/Crypto/Hedge Fund sekmeleri var. Strateji kodu açık değil; katkı tabanlı ödül.
- **QuantConnect:** Algorithm Lab ve AI agent vurgusu; halka açık strateji kütüphanesi giriş gerektiriyor.
- **WorldQuant BRAIN:** Sayfa JavaScript ile yükleniyor; içerik alınamadı.

## 2. Akademik ve yarı-akademik (kodlu ve/veya OOS raporlu)
**arXiv'de 2026 çalışmaları (özetler okundu):**
- **2610.03128 — TradeGrad:** LLM ile "textual gradient" tabanlı strateji optimizasyonu, dönemler arası sağlamlık hedefi. Kod: `github.com/transcend-0/TradeGrad` (açık). *Not:* LLM tabanlı; projede ML/LLM elenen kategori.
- **2602.11708 — AdaptiveTrend:** kripto, 150+ çift, 2022–2024 OOS 36 ay; Sharpe 2.41, DD −%12.7, Calmar 3.18 (yazar iddiası). Kod bağlantısı özetten çıkmadı. *Not:* Dönem kısa ve tek yıllık boğa/ayı karışımı; düşük güvenilirlik ama ilginç (6 saatlik trend + aylık portföy).
- **2608.23808 — MinervaScore:** Backtest sonuçlarının arama şansından (DSR, PBO, SPA, MinTRL) ayrılmasını ölçen bir "sağlamlık" puanı. Kod yok. *Not:* Bizim karar 13/24 ve sağlamlık paketiyle çok ilişkili; **karar kriterleri için doğrudan referans.**
- **2608.27734 — "Leakage-safe, search-aware assessment of LLM-driven strategy discovery"** ve **2608.23308 — FIDES** : LLM ile strateji keşfinde sızıntı ve arama yanlılığı değerlendirmesi. Kod yok.
- **2603.09219 — AlgoXpert:** IS/WFA/OOS protokolü, overfitting azaltma. Kod yok.
- **2602.00080 — GT-Score:** Overfitting'i azaltmak için amaç fonksiyonu. Kod yok.
- **1912.04492 — "151 Trading Strategies":** Kitap/makale; SSRN 3247865 ile ilişkili ve `psdon/paper-strategy-lab` deposu bu stratejileri yeniden test ediyor (önceki dosyada zaten var).

**Quantocracy derlemesi (14 Ekim 2026) öne çıkanlar:**
- Quantpedia: HMM rejim tespitinde eğitim başlangıcının OOS performansa etkisi (1970/1980/1990/2000 karşılaştırması) — "out-of-sample değerlendirmenin tehlikesi" başlığıyla.
- Aligrithm: "Does Complexity Actually Help?" — basit buy-and-hold'un volatilite ölçekli OOS Sharpe'ı 0.55 (1940–2020), 12.000 özellikli karmaşık modelin 0.49 olduğu; yani karmaşıklık bu veride kazandırmamış. Ayrıca çapraz kesit momentumda sıralama kaybı.
- Robot Wealth: stat-arb ve pairs trading serisi (dürüst, zorluklara odaklı).

## 3. Bülten ve bloglar
- **Robot Wealth:** Blog açılıyor; yakın tarihli yazılar stat-arb (6 bölümlük seri), "Think like a trader" ve "Trading as a business" kategorileri. Ton: uygulama ve zorluk odaklı; ücretli "RW Pro" ve bootcamp.
- **Quantocracy:** Blog derlemesi; sitesi bizim için en iyi keşif aracı (ayrıca Quantpedia, Robot Wealth, Alpha Architect, Alvarez QT linkleri).
- **Quantified Strategies, TradeQuantiX, Systematic Traders, Rogue Quant (Substack):** `*.substack.com` ağ düzeyinde kapalı → içerik alınamadı. Önceki arama özetleri yalnız başlık/özet düzeyinde.
- **Alpha Architect:** 403 (bot koruması); içerik alınamadı.

## 4. Forumlar ve topluluklar
- **Elite Trader — Automated Trading forumu:** Konu başlıkları incelendi: çoğu genel piyasa tartışması (tahvil, faiz, emlak, ETF). **Sistem/kod paylaşımı çok az.** Sürekli canlı tartışma var; sonuç paylaşımı düşük. Değerlendirme: pratik strateji kaynağı olarak zayıf.
- **Trade2Win:** Açıldı; "S&P 500 Contest" ve "Broker Comparison" araçları; konu listesi yüklenmedi (JavaScript). Değerlendirme: UK/ABD hisse ve vadeli odaklı; sistem paylaşımı belirsiz.
- **MQL5 CodeBase:** Açıldı; MT4/MT5 Expert Advisor ve indikatör kütüphanesi (ücretsiz indirilebilir kod). Ücretli sinyal ve 8000+ sinyal kopyalama. **Uyarı:** Forex EA'larının önemli bölümü martingale/grid; kod incelemesi zorunlu.
- **Quant Stack Exchange:** Cloudflare engeli.
- **Futures.io, SSRN, Wilmott:** engelli.

## 5. YouTube, Discord, Telegram, ücretli topluluklar
- **YouTube (arama başlıkları):** "I Built an AI Trading Strategy With Claude Code (380,000 Backtests)", "Claude Tested Over 9,000 Trading Strategies (Here's What Works)" (Testing Overview / Methodology / What Survived), "8 Quant Trading Strategies (Backtests & Rules Included)", "MACD and EMA Trend Strategy: A Full Algorithmic Backtest in Python". Açıklamaların çoğu ücretli topluluğa (Skool, akademi) yönlendiriyor. **Doğrulanamadı:** video içeriklerine erişilemedi.
- **Discord / Telegram:** Ağ düzeyinde kapalı. Kaynaklı bilgiye göre açık kaynak bot toplulukları (Freqtrade, OpenTrader, OctoBot) ve ücretli sinyal grupları var; sonuç doğrulaması yok.
- **Ücretli topluluklar:** TradeQuantiX (Discord, GitHub kodu, canlı model portföy iddiası) — ağ engelli, içerik yok.

## Özet değerlendirme (bizim karar kriterleriyle)
1. **En güvenilir kaynaklar:** arXiv'de OOS ve sağlamlık metodolojisi yazan çalışmalar (MinervaScore, GT-Score, AlgoXpert), Quantpedia'nın akademik anomali kataloğu, Quantiacs/Numerai'nin canlı yarışma yapısı.
2. **Fikir kaynakları:** Quantocracy derlemeleri, Robot Wealth, Aligrithm. Sonuç kanıtı zayıf, kural fikri değerli.
3. **Düşük güven:** Elite Trader/MQL5/YouTube/ücretli Discord grupları — çoğunlukla pazarlama, kod eksik veya martingale riski.
4. **Bizim için iki öneri:** (a) Quantpedia katalogundaki ~1000 stratejiden portföy katmanına uygun olanları (rotasyon, faktör, momentum) kural özetiyle çıkarmak; (b) MinervaScore/GT-Score/DSR gibi sağlamlık ölçütlerini karar 13 ve 24 kapılarıyla karşılaştırmak.

## Açık kalanlar
- Quantiacs yarışma sonuçları, Quantocracy'nin tüm arşivi, Quantified Strategies / Systematic Traders / TradeQuantiX / Rogue Quant bültenleri, Alpha Architect, SSRN, Wilmott, Futures.io, Quant SE, Reddit, Discord, Telegram.
- Bunların bazıları için (ör. SSRN ve Alpha Architect) bot koruması yüzünden erişim sınırı var; ağ izni tek başına yetmez.
