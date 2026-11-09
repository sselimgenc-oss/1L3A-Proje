# GitHub taraması — grup g2_kripto_bot (2026-11-07)

CSV: `stratejiler/ek_kaynaklar/github_g2_kripto_bot.csv` (207 satır). Klonlar `/home/user/gh/` altında, salt okunur. Hiçbir kod kopyalanmadı;
`mekanik_ozet` sütunları kendi cümlelerimizle yazıldı. Karar 27 (evren stratejisi, tek sembol–strateji ikilisi yok) göz önünde tutuldu:
buradaki satırların hepsi "tek parametre seti, çok enstrüman" mantığına uyan kural ailesi olarak kaydedildi.

## Repo bazında kapsam

| Repo | Dosya (git hariç) | Okunan / taranan | Strateji satırı | Lisans |
|---|---|---|---|---|
| xFFFFF/Gekko-Strategies | 1095 (615 js, 386 toml, 56 log, 10 ods) | 615 js dosyası içerik-özetiyle gruplandı (351 tekil içerik, 204 isim ailesi; `!WORKSOP` 566 js, 48 üst-klasör js); strateji ailelerinin `check()` gövdeleri, tüm toml ayarları, `backtest_database.csv` (2118 satır), `source.txt`, README'ler okundu | 116 | ana repoda LICENSE yok; alt modüller: BuyAtSellAt/NeuralNet/NNv2/neuralnet_zschro MIT, SuperTrend izin metni (MIT benzeri) |
| DeviaVir/zenbot | 308 | `extensions/strategies/*` 42 klasörün tamamı (strategy.js + README), `docs/strategies/*`, `conf-sample.js`, `crossover_vwap/example_sims` (8 sim HTML sonucu çıkarıldı) | 33 | MIT |
| bitcoinvsalts/node-binance-trader | 72 | `src/server/backtest.js`, `server.js`, `trader.ts`, README/docs | 1 | MIT |
| saniales/golang-crypto-trading-bot | 39 | `strategies/*.go`, `examples/*.go`, README | 1 (strateji kuralı yok) | GPL-3.0 |
| chrisleekr/binance-trading-bot | 3123 (1894 ts, 432 tsx, scripts/ci 682) | `docs/concepts/strategies/{index,momentum,trailing-trade,rebalance}.md`, `docs/concepts/{technicals,discovery}.md`, `docs/_generated/config/*`, `packages/strategy/{trailing-trade,momentum,rebalance}/src` dosya listesi + `mean-reversion-gate.ts`, `indicator-gate.ts`; `apps/*`, `packages/db|contracts|notify|...`, `scripts/ci`, e2e = altyapı, atlandı | 16 | Apache-2.0 |
| 51bitquant/binance_grid_trader | 54 | `gridtrader/trader/strategies/*.py` (3 grid), README | 3 (hepsi yasak) | MIT |
| 51bitquant/howtrader | 205 | `examples/strategies/*` (11), `app/cta_strategy/strategies/*` (11), `app/portfolio_strategy/strategies` (3), `app/spread_trading/strategies` (2), `app/tradingview/strategies` (6), `examples/data_analysis`, docs başlıkları | 20 | MIT |
| Superior-Trade/trading-terminal | 231 | `README.md`, `docs/strategy-pipeline.md`, `lib/tier-rubric.ts`, `app/api/{detect,compile,chat}/route.ts` prompt'ları, `evals/*.json`; geri kalan UI/altyapı | 5 | Apache-2.0 |
| ccxt/ccxt (yalnız `examples/`, bu oturumda seyrek klonlandı: `/home/user/gh/ccxt_ccxt`) | 900 (py 290, ts 185, js 192, php 85, cs 39, rust 29, go 16) | py örneklerinin tamamı listelendi; indikatör/arbitraj/bot/prediction/order-router/rust-watch_and_buy/notebook dosyaları açıldı; js/ts/php/cs/go sürümleri aynı örneklerin çevirisi | 12 | MIT |

## Durum dağılımı (toplam 207)

yeni 87 · ayar 63 · kural_yok 27 · veri_yok 10 · mevcut 7 · yasak 7 · ml 6.
Repo kırılımı: Gekko-Strategies — yeni 55, ayar 40, kural_yok 11, ml 5, mevcut 4, veri_yok 1; zenbot — ayar 15, yeni 14, kural_yok 2, veri_yok 1, ml 1; node-binance-trader — veri_yok 1; golang-crypto-trading-bot — kural_yok 1; binance-trading-bot — yeni 10, mevcut 3, ayar 2, yasak 1; binance_grid_trader — yasak 3; howtrader — yeni 8, ayar 5, kural_yok 3, yasak 3, veri_yok 1; trading-terminal — kural_yok 3, ayar 1, veri_yok 1; ccxt — kural_yok 7, veri_yok 5

## Öne çıkan yeni / ilginç stratejiler (kodlama adayı)

1. **chrisleekr momentum tetikleyicileri** (en iyi belgelenmiş, 1h kripto arastirma notlariyla): `maCluster` (4 SMA sikismasi + kirilim, choppiness/ATR-yuzdelik filtreli), `exhaustion` (400-SMA'nin %5 altinda + Choppiness<30 + RSI<25 dip), `obvLead` (OBV yeni zirve, fiyat degil), `impulse` (hacim 3x + 2 ATR govde), `weekendGap` (Pazar 22 UTC acilisi Cuma kapanisinin >%1 altinda → Cuma kapanisina donus; 3 gun zaman stopu), `breakout` (400 mum Donchian) + trend filtresi + ATR izleyen stop. Hepsi evrende tek parametre setiyle calisabilir; weekendGap yalniz 7/24 piyasalarda (kripto) anlamli.
2. **Gekko RSI_BULL_BEAR_ADX / NEO** ailesi: rejim (SMA50/SMA500) bazli RSI esikleri; ADX ile esik kaydirma; NEO'da ucuncu "idle" rejim (ROC). Repodaki backtestte en iyiler (NEO medyan +%34, 27/40 sette piyasayi gecti; RSI_BULL_BEAR_ADX +%22.9, 27/40) ama test = 61 gunluk 2018 dususu, 10dk mum.
3. **zenbot**: `ichimoku_score` (7 Ichimoku sinyalinin agirlikli puani, 50/49 esikleri), `cci_srsi` (CCI+StochRSI birlikte donus, EMA egim filtresi), `ehlers_mama`/`ehlers_trend` (Ehlers adaptif MA), `ta_srsi_bollinger`/`ta_stoch_bollinger` (stokastik donusu + bant temasi), `wavetrend`, `trust_distrust` (yuzde zigzag).
4. **howtrader**: `AtrRsi` (ATR>ATR ortalamasi + RSI(5) 66/34 + %0.8 izleyen stop), `BollChannel` (BB 18/3.4 kirilim + CCI yonu + 5.2xATR izleyen), `MultiTimeframe` (15dk SMA trend + 5dk RSI), `KingKeltner`, `DualThrust` (mevcut dis__dual-thrust ile ayni aile), `Turtle` (piramitli).
5. Martingale ailesinden **ekleme (DCA) haric tutulmus giris kurallari** (V3 pump devami: 1s mum >%2.6 / 4s mum >%4.6; V2: 2 gunluk zirveden %4 dusus; V1: Bollinger(30,2.2) ust kirilimi) ayri `yeni` satir olarak yazildi; ekleme/katlama kismi `yasak` satirinda.
6. **Gekko DI esigi, Aroon uc-deger (zit yon), saat-disi sade kurallar** (Bro-RSI egim, StratLV SMA bandi) kucuk ve test edilebilir ama beklenti dusuk.

## Strateji icermeyen / sinirli repolar

- **saniales/golang-crypto-trading-bot**: bot cercevesi; `examples/` yalniz "Watch5Sec", Telegram ve websocket ornegi; al-sat kurali yok (1 kural_yok satiri).
- **bitcoinvsalts/node-binance-trader**: tek strateji var ve emir defteri derinligi/maker sayisi/saniyelik veri istiyor → `veri_yok`.
- **Superior-Trade/trading-terminal**: LLM'in Freqtrade kodu urettigi terminal; stratejiler kullanici istegiyle uretiliyor. Kural olarak yalniz README'deki ornek (BB alt + RSI<40 + EMA50 uzerinde) ve prompt arketipleri var; funding/OI/likidasyon kapilari `veri_yok`.
- **ccxt/ccxt**: kutuphane; `examples/` gosterge hesabi, uyari, arbitraj taramasi ve altyapi ornekleri; islenebilir kural yok (arbitraj/orderbook → veri_yok).
- **51bitquant/binance_grid_trader**: yalniz stopsuz izgara (3 satir, hepsi yasak).
- **chrisleekr**: `trailing-trade` izgara/ortalama dusurme (yasak satiri), ama tek-giris/ATR-izleyen preset ve RSI/z-skor kapilari ayri `yeni` satir.

## Güncelleme (ikinci tur): alt modüller ve eksik okumalar

- **Alt modüller:** 18 Gekko submodule klasörü çalışma ağacında hâlâ boştu (yalnız `.git` işaretçisi); `git reset --hard` izni reddedildiği için klonu değiştirmeden `git archive HEAD` ile `.git/modules/*` nesnelerinden scratchpad'e açıp okudum. 16 modül dolu (toplam ~140 dosya): AdoptedStrategies/Gab0 (Gab0'nun GA uyarlamaları: NEO, RSI_BULL_BEAR, _ADX, _ADXold, Supertrend, DUAL_RSI_BULL_BEAR), BuyAtSellAt, CloggyStrats (n8, mounirs-ga v1/v2, helper.js izleyen stop), GekkoStrategies/ManuNet, Kane2 (Kane2.js + gannswing), NNv2 = neuralnet_zschro, NeuralNet, RSI-WR = gekko, SuperTrend, TommieHansenStrategies (orijinal RSI_BULL_BEAR, _ADX, TEMA; geri kalanı shell/php araçları), gekko-strat-hl (HL.js), tether (tether, tether-simple). `Luke_NN` ve `Neapticator` modül nesnesi de yok → tek `ml`/kod_yok satırı.
- **Yeni gerçek kurallar:** RSI_WR (RSI 30/70 + Williams %R; R eşiği -10 pratikte hep doğru), tether (SMA100 ±%0.35, `dis__ema50-sapma` ailesi), tether-simple (mutlak 0.995/1.005 → kural_yok), HL (25 mumluk en düşük kapanış altında al, en yüksek kapanışta çık), Kane2 (RSI 9, 36/69; ADX toml'da var kodda yok), DUAL_RSI_BULL_BEAR (SMA14>700 mutlak seçici → kural_yok), NNv2 (ml). Diğer dosyaların hepsi ana klondaki mevcut aile satırlarıyla içerik olarak aynı çıktı (dosya sütununa eklendi).
- **Tamamlanan "okunmadı" satırları (baştan sona okundu):** jake, jazzbre (efektif kural yalnız EMA 8/13 kesişimi), Combination-1/2/3 + Entry_Plus (RSI bull/bear sinyali EMA onayıyla geçitlenir; Entry_Plus ATR hedef/stop), tulip-multi-custom (açık filtrelerin hepsi aynı anda), stopTrailing (1/5/15/60 dk stokastik %K<3 hepsinde; stop %5, başa baş +%1.2, %20 izleyen), trend-based (yalnız Telegram bildirimi → kural_yok), loosai/oosai (hacim patlaması, kademeli kâr geri verme), bryanbeck (3 ardışık düşen mum al, 2 ardışık yükselen sat; mutlak eşik), chang (MACD + zaman aşımı çıkışı), signals (yalnız pump bildirimi → kural_yok), STI-DEMA, RSI_BB_ADX_Peak/BB_Adx/ReEntry, PINGPONG/_T/Stop varyantları, ZERO/nikiehihsa (geometrik OHLC EMA MACD), FIBO (gösterge dosyası), HL_Scalp, zenbot `trendline` (yalnız alım, satış yorumda).
- **Obfüske dosyalar çözüldü (statik base64 + dizi dönüşü, kod çalıştırmadan):** `2xTheMarket-min.js` ve `bear-market.js`: BB(19,2)+Stoch(14,1,3)+EMA20+MACD+60/12 mumluk düşüş/yükseliş toplam oranı ile long-only dip alımı, kademeli hedef ve çok parçalı stoplar; mutlak EMA-fiyat mesafesi (-25/-16) sembole özgü. `BitBankStrategy*.js` (370 KB bundle): kural okundu = BitBank emir defteri özellik seti (power_imbalance, tahmini gelecek ortalama) → `veri_yok`. `NEO-1525230452.js` GitHub HTML sayfası → kural_yok.

## Belirsizlikler ve dikkat

- **Gekko `onceki_sonuc`**: `backtest_database.csv` testleri 10 dk mum, ~61 gün, Şubat 2018 altcoin düşüşü (medyan piyasa %-22.3), Binance/Bitfinex/Poloniex/Kraken; kar yüzdeleri 1L3A'nın walk-forward standardıyla karşılaştırılamaz, yalnız "piyasayı geçti" bilgisi kaba ipucudur. Zaman dilimi "mum boyutu kullanıcı ayarı"; 10 dk daytrade sayıldı.
- **Mutlak eşikli kurallar** (bryanbeck 0.00001, 2xTheMarket EMA-fiyat -25, tether-simple 0.995/1.005, DUAL_RSI 700): sembole özgü, evren stratejisine (karar 27) yüzdeye çevrilmeden uygun değil; satırlarda belirtildi.
- **Gekko zaman damgalı kopyalar** (`-1525...`): aynı mantık veya eski/yeni arayüz farkı; aile bazında birleştirildi (351 tekil içerik). `exponential-moving-averages-*`, `*-candle-fetcher`, `talib.js`, `functions.js`, `indicators/*`, `debug-advice`, `noop`, `CSV_Export`, `forex.*` altyapı sayıldı.
- **Eşleştirme:** `mevcut:` yalnız `dis__ema50-sapma` (EMADIV), `yeni__ma-tipli-kesisim` (DEMA/TEMA/Crossover), `pf__goreceli_guc`, `pf__sabit_sepet`, `pf__rotasyon`. `ayar:dis__dual-thrust` (howtrader günlük aralık tanımı farklı olabilir) ve `ayar:yeni__adx-di-esik-kesisimi` (yalnız DI) yakın tahmin; kodlayan kontrol etmeli.
- **Martingale giriş satırları** (`yeni`): koordinatör ayrıştırmayı kabul etti; yalnız ekleme/katlama dışarıda, giriş + stoplu çıkış kuralı alınır. Orijinalin getirisi katlamaya bağlıydı.
- **chrisleekr**: belge-odaklı okuma; `.ts` kaynağından yalnız iki kapı dosyası açıldı. Sayısal sonuç yok, yalnız belgedeki "research" notları.
- **zenbot** `ta_srsi_bollinger`/`ta_stoch_bollinger` varsayılan zaman dilimi belirtilmemiş.
- ccxt klonu `git sparse-checkout` ile yalnız `examples/` için alındı.
