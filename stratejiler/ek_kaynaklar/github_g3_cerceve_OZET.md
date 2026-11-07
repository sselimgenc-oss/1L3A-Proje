# GitHub taraması: g3_cerceve (bot/çerçeve repoları)

Çıktı: `stratejiler/ek_kaynaklar/github_g3_cerceve.csv` (74 satır). Kod kopyalanmadı; kurallar kendi cümlelerimle yazıldı.
Sekiz repo da klonlardan (`/home/user/gh/`) salt okunur okundu. Eşleştirme için `tum_stratejiler()` kayıt listesi (289 kayıt), `motor/portfoy/stratejiler/`
(pf__*), `dis_envanter.csv` ve `kodlama_kuyrugu_2026-11-07.csv` kullanıldı; "mevcut/ayar" dediğim her ad kayıtta gerçekten var (betikle doğrulandı).

**Önemli bağlam:** OctoBot daha önce taranmıştı (`arsiv/algo-sg/DIS_STRATEJILER.md` ve `arsiv/algo-sg/dis_kaynak/envanter_altyapi_en.txt`, O1-O71 numaralı 71 bileşen,
12 test: OB01-OB12, hepsi "ele" kararı). Bu tarama o envanteri bağımsız olarak yeniden doğruladı (kod okunarak); `onceki_sonuc` sütununa o arşivdeki sayılar kaynakla birlikte
taşındı. Diğer yedi repo için önceki bir tarama bulunamadı (1L3A deposunda adlarına rastlanmadı).

## Repo bazında kanıt

| Repo | Toplam dosya | Strateji açısından açılıp okunan | CSV satırı | Durum dağılımı | Lisans |
|---|---|---|---|---|---|
| Drakkar-Software/OctoBot | 6086 | ~700 (aşağıya bak) | 36 | ayar 6, yeni 12, mevcut 6, veri_yok 5, ml 1, yasak 3, kural_yok 3 | GPL-3.0 |
| banbox/banbot | 1537 | ~330 | 20 | ayar 3, yeni 9, mevcut 1, ml 3, kural_yok 1, veri_yok 3 | AGPL-3.0 (+ticari) |
| Open-Trader/opentrader | 682 | ~200 | 4 | ayar 1, yasak 2, veri_yok 1 | Apache-2.0 |
| idanya/algo-trader | 202 | 112 (`src/`) + testler | 4 | ayar 2, ml 2 | MIT |
| garethdmm/gryphon | 584 | ~300 | 4 | veri_yok 4 | Apache-2.0 + Commons Clause |
| ent0n29/polybot | 238 | ~55 (docs, research, strategy-service) | 2 | veri_yok 1, kural_yok 1 | MIT |
| cassandre-tech/cassandre-trading-bot | 566 | ~60 | 2 | ayar 1, kural_yok 1 | GPL-3.0 |
| s-brez/trading-server | 34 | 34 (tamamı) | 2 | ayar 1, kural_yok 1 | GPL-3.0 |

Toplam durum dağılımı (74 satır): yeni 21, ayar 14, veri_yok 14, mevcut 7, kural_yok 7, ml 6, yasak 5.

## Hangi klasörleri okudum (kanıt)

- **OctoBot** (6086 dosyanın çoğu arayüz, borsa bağlayıcıları, protokol, düğüm/istemci altyapısı):
  `packages/tentacles/Evaluator/` (159 dosya: TA 3 modül + AI, RealTime 2, Social 5, Strategies 5, Util 6; hepsinin .py, config/*.json, resources/*.md ve ilgili testleri),
  `packages/tentacles/Trading/Mode/` (169 dosya: 14 işlem modu; kod + resources + config), `packages/tentacles/profiles/` (70 dosya: 18 profilin profile.json, tentacles_config.json ve specific_config/*.json),
  `packages/tentacles/Agent/` (60: ajan takımları ve becerileri, özellikle `resources/skills/*/SKILL.md`), `packages/tentacles/Automation/` (40: tetikleyiciler; strateji değil, altyapı),
  `packages/tentacles/Meta/` (156: DSL operatörleri ve scripting kütüphanesi; altyapı, ancak TA operatörleri ve DSL örnekleri kontrol edildi), `tests/static/` (36: test yapılandırmaları),
  `docs/content/` (134: octobot-script, investing/tradingview-strategies-tutorials, guides/octobot-trading-modes, client-sdk/strategies), `docs/blog/` (59: anahtar sözcük taramasıyla, strateji içerenler tamamen okundu),
  `README.md`, `CHANGELOG.md`. `packages/` altındaki diğer paketlerde (trading, protocol, node, flow, copy, agents, commons vb.; ~4000 dosya) `RSI|EMA|strategy|TradingMode|dsl_script` taraması yapıldı; strateji kuralı bulunmadı (yalnız altyapı + testler).
  Atlananlar: `Trading/Exchange/*` (70 borsa bağlayıcısı klasörü), `Services/*` (arayüz/bildirim), `node_web_interface`, `packages/protocol*`.
- **banbot**: `doc/*.md` (yalnızca `banbot.md`, `banbot_cn.md`, `statarb_guide.md`, `factor_*.md`, `factors.md` ayrıntılı; diğerleri başlık düzeyinde), `bandoc/en-US/guide/*.md` (strat_custom.md satır satır), `bandoc/en-US/api/*.md`,
  `strat/` (39 dosya), `factor/` (334 dosya; `factor/statistics` 193 dosya başlık yorumlarıyla taranıp ilgili 30 kadarı okundu, `factor/research/combine.go`, `factor/runner/definition.go`, `example.json`), `web/dev/strat.go` (şablon), `config`, `doc/config.yml`.
  Strateji kodu depoda yok (stratejiler ayrı depoda); depoda yalnız dokümandaki örnekler, birim test iskeleti ve istatistik/faktör araç seti var.
- **opentrader**: `packages/bot-templates/src/templates/` (rsi, dca, grid, grid-bot + 16 test şablonu), `packages/bot-processor/src/effects/`, `packages/indicators` (yalnız sma/ema/rsi), `packages/tools/src/{dca,grid,candlesticks}`, `packages/backtesting`, `README.md`, `config.sample.json5`, `.changeset/*`. `pro/` klasörü boş.
- **idanya/algo-trader**: `src/algotrader/pipeline/strategies/*` (4 strateji), `src/algotrader/examples/pipeline-templates/*.json` (13 şablon), `calc/technicals.py`, `README.md`, `tests/unit/strategies/*`. Geri kalanı yükleyici/depolama/IB bağlayıcısı (`libs/ib_client` vendor kodu).
- **gryphon**: `gryphon/execution/strategies/builtin/*.pyx` (8 dosya) + `fundamental_value/*`, `gryphon/lib/{arbitrage,market_making}.py`, `gryphon/lib/analysis/legacy/*` (göstergeler), `docs/source/{writing_strategies,reading_list}.rst`, `README.md`, `tests/logic/strategies`.
- **polybot**: `docs/EXAMPLE_STRATEGY_SPEC.md`, `docs/STRATEGY_RESEARCH_GUIDE.md`, `strategy-service/**` (GabagoolDirectionalEngine dahil), `research/backtest/*`, `research/final_strategy_findings.py`, `README.md`.
- **cassandre**: `docs/docs/tutorial/write-strategy.md`, `trading-bot-archetypes/**/SimpleStrategy.java`, test stratejileri (`OnlyPositionsStrategy` vb.), `docs/docs/cassandre_basics/*`.
- **trading-server**: 34 dosyanın tamamı (`model.py`, `strategy.py`, `features.py`, `portfolio.py`, `misc testing/*`).

## Öne çıkan (1L3A'da karşılığı olmayan ama kuralı net) — hepsi düşük/orta öncelik

1. **OctoBot Dip Analyser**: 4h'te RSI(14) yerel minimumu + yavaş/hızlı RSI ortalama katmanları + Klinger osilatörü dönüş teyidi, limit alış (x0.995), alım fiyatından +%4/+%7/+%10'a 3 kademeli satış. Varsayılan stopsuz (ATR stop gerekir). Martingale/DCA değil.
2. **OctoBot SimpleStrategy + DailyTradingMode**: DoubleMA(5,10) skoru + RSI(14) skoru, 1h/4h/1d ortalaması, eşik durumları (-0.85/-0.25/+0.25/+0.85, risk ile kaydırma). 1L3A'da "çok göstergeli oylama" benzeri tek `dis__confluence-rank` var.
3. **OctoBot MoveSignals/SignalTradingMode**: Klinger sinyali x Bollinger ağırlığı, 30m/1h/4h ağırlıkları 4/3/3, eşik 0.15. Klinger osilatörü göstergeleri 1L3A'da yok.
4. **OctoBot Ajan becerisi (SKILL.md)**: RSI<30 + MACD yukarı kesişim + kapanış>MA50 üç koşullu birleşim; kodlanabilir ama çıkış/stop yok.
5. **banbot kesitsel faktörler**: momentum−volatilite (top/bottom-K), risk ayarlı momentum + 3 bar dönüş, momentum + funding carry. `pf__kesit_ls` tek skor seçer; bu üçü skor birleşimi (z-skor) kullanıyor.
6. **banbot portföy tahsisleri**: HRP, long-only min-varyans, faktör nötr ağırlıklar (Pole), Chan etkin sınır/Kelly. Bunlar sinyal değil tahsis yöntemi; Kelly risk kuralı alanına girdiği için önermiyorum.

Gerçekçi değerlendirme: bu sekiz repo "bot çerçevesi" olduğu için mekanik kural zenginliği düşük; satırların çoğu daha önce kodlanmış ailelerin (MA kesişim, RSI aşırı bölge, SuperTrend, EMA sapma, RSI-MA, bant dönüşü) yeniden ifadesi. Önceki OctoBot taramasında bu ailelerin hepsi elendi (PF/Sharpe örneklem-dışında zayıf); yeni bir "kaldı" sinyali yok.

## Strateji içermeyen / strateji sayılamayan kısımlar

- **cassandre**: yalnız çerçeve; tek kural öğreticidedeki "3 ardışık düşen dakikalık fiyat → long (SG %4, SL %8)". Arketip ve test stratejileri boş/sabit.
- **trading-server**: yalnız test amaçlı EMA10/20 modeli; `features.py`'deki yeni-trend, J-eğrisi, küçük-bar, dönüş-bar, yakınsama fonksiyonlarının gövdesi boş (`return` tanımsız değişken). README: "strateji uygulamaları dahil değil".
- **gryphon**: tüm yerleşik stratejiler emir defteri tabanlı (arbitraj, piyasa yapıcılık); `lib/analysis/legacy` yalnız gösterge hesapları (aroon, ADX, ATR, Bollinger, CMF, CCI, MACD, RSI...) ve strateji değil.
- **polybot**: tek strateji Polymarket "tam set" arbitrajı (emir defteri + tahmin piyasası); analiz kodları (ClickHouse + Python) altyapı/araştırma.
- **opentrader**: üç yerleşik strateji (RSI, DCA, Grid), ikisi yasak.
- **OctoBot altyapı kısımları (CSV'ye girmedi)**: Automation tetikleyicileri (fiyat/volatilite/profitability eşikleri), DSL operatörleri, scripting kütüphanesi, borsa bağlayıcıları, `strategy_optimizer`.
- **banbot dokümanındaki `CustomExitDemo`/`DrawDown` örnekleri**: giriş kuralı rastgele; yalnız çıkış mekaniği gösterimi (izleyen %50 geri çekilme çıkışı); satır açılmadı. `ta.Cross`/`RouteData` gibi API ayrıntıları da strateji sayılmadı.

## Belirsizlikler

- **OctoBot işaret kuralı** tersine: değerlendirici notu -1 = AL, +1 = SAT. Satır özetlerinde bu ifade edildi. Pek çok değerlendirici sürekli skor üretiyor; işleme çevirme eşiği DailyTradingMode'da (±0.25 + 0.2xrisk kayması). Tek başına eşik kuralı gerekiyorsa o eşik "yeni" satırlarda not edildi ama kodlamadan önce kullanıcı kararı gerekir.
- **EMADivergenceTrendEvaluator** varsayılan değerlerle (long 2, short -2) iki koşul örtüşüyor; kod fark <= %2 iken hep AL, üstünde SAT diyor (adlandırma ters). 1L3A `dis__ema50-sapma` bu davranışı zaten uyarlamış.
- **InstantMAEvaluator** eşiği: yapılandırma %0.5, kod varsayılanı %5 (satırda %0.5 yazıldı).
- **banbot SmaOf2**: kesişim koşulu ile "kapanış SMA20'nin 3 ATR altında" koşulu birlikte nadiren sağlanır; belgedeki hâliyle kayıt, düşük öncelik. `ta.Cross` dönüş değeri semantiği banta kütüphanesinde (bu depoda yok); Demo2'de "1sa kısa MA uzunun üstünde" olarak yorumlandı.
- **banbot istatistik araçları**: pairs/Kalman/Vidyamurthy kuralları yalnız yorum satırlarında (±sqrt(S), 0.75σ eşiği); giriş-çıkış politikası yok. Bu yüzden `mevcut:pf__pairs` (zaten 5 yöntemi var) olarak eşlendi.
- **polybot** sonuçları yazarın izlediği trader'ın kâr/zararı; kendi botunun test sonucu yok. Veri (Polymarket CLOB) Binance/OHLCV evreninde olmadığı için veri_yok.
- **idanya ConnorsRSI2**: kodda çıkış sinyali yön olarak "ters pozisyon" biçiminde üretiliyor ancak durum bayrağını sıfırladığı için ters pozisyon açılmıyor; özetlendiği gibi "çıkış" olarak yorumlandı.
- **OctoBot TA değerlendiricilerinin çoğu `swing`/`daytrade` zaman dilimi seçimini kullanıcıya bırakıyor**; `stil` sütunu varsayılan profillerdeki zaman dilimlerine (1h/4h/1d) göre seçildi.
- **Önceki sonuç sütunları**: OctoBot satırlarındaki PF/Sharpe sayıları 1L3A'nın eski arşivinden (OctoBot'un eski bir sürümü üzerindeki 71 bileşenlik envanter) alındı; bu klondaki kod aynı kuralları içeriyor ama sayılar yeniden üretilmedi.
