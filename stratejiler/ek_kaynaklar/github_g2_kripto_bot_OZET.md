# GitHub taraması — grup g2_kripto_bot (2026-11-07)

CSV: `stratejiler/ek_kaynaklar/github_g2_kripto_bot.csv` (203 satır). Klonlar `/home/user/gh/` altında, salt okunur. Hiçbir kod kopyalanmadı;
`mekanik_ozet` sütunları kendi cümlelerimizle yazıldı. Karar 27 (evren stratejisi, tek sembol–strateji ikilisi yok) göz önünde tutuldu:
buradaki satırların hepsi "tek parametre seti, çok enstrüman" mantığına uyan kural ailesi olarak kaydedildi.

## Repo bazında kapsam

| Repo | Dosya (git hariç) | Okunan / taranan | Strateji satırı | Lisans |
|---|---|---|---|---|
| xFFFFF/Gekko-Strategies | 1095 (615 js, 386 toml, 56 log, 10 ods) | 615 js dosyası içerik-özetiyle gruplandı (351 tekil içerik, 204 isim ailesi; `!WORKSOP` 566 js, 48 üst-klasör js); strateji ailelerinin `check()` gövdeleri, tüm toml ayarları, `backtest_database.csv` (2118 satır), `source.txt`, README'ler okundu | 112 | LICENSE yok |
| DeviaVir/zenbot | 308 | `extensions/strategies/*` 42 klasörün tamamı (strategy.js + README), `docs/strategies/*`, `conf-sample.js`, `crossover_vwap/example_sims` (8 sim HTML sonucu çıkarıldı) | 33 | MIT |
| bitcoinvsalts/node-binance-trader | 72 | `src/server/backtest.js`, `server.js`, `trader.ts`, README/docs | 1 | MIT |
| saniales/golang-crypto-trading-bot | 39 | `strategies/*.go`, `examples/*.go`, README | 1 (strateji kuralı yok) | GPL-3.0 |
| chrisleekr/binance-trading-bot | 3123 (1894 ts, 432 tsx, scripts/ci 682) | `docs/concepts/strategies/{index,momentum,trailing-trade,rebalance}.md`, `docs/concepts/{technicals,discovery}.md`, `docs/_generated/config/*`, `packages/strategy/{trailing-trade,momentum,rebalance}/src` dosya listesi + `mean-reversion-gate.ts`, `indicator-gate.ts`; `apps/*`, `packages/db|contracts|notify|...`, `scripts/ci`, e2e = altyapı, atlandı | 16 | Apache-2.0 |
| 51bitquant/binance_grid_trader | 54 | `gridtrader/trader/strategies/*.py` (3 grid), README | 3 (hepsi yasak) | MIT |
| 51bitquant/howtrader | 205 | `examples/strategies/*` (11), `app/cta_strategy/strategies/*` (11), `app/portfolio_strategy/strategies` (3), `app/spread_trading/strategies` (2), `app/tradingview/strategies` (6), `examples/data_analysis`, docs başlıkları | 20 | MIT |
| Superior-Trade/trading-terminal | 231 | `README.md`, `docs/strategy-pipeline.md`, `lib/tier-rubric.ts`, `app/api/{detect,compile,chat}/route.ts` prompt'ları, `evals/*.json`; geri kalan UI/altyapı | 5 | Apache-2.0 |
| ccxt/ccxt (yalnız `examples/`, bu oturumda seyrek klonlandı: `/home/user/gh/ccxt_ccxt`) | 900 (py 290, ts 185, js 192, php 85, cs 39, rust 29, go 16) | py örneklerinin tamamı listelendi; indikatör/arbitraj/bot/prediction/order-router/rust-watch_and_buy/notebook dosyaları açıldı; js/ts/php/cs/go sürümleri aynı örneklerin çevirisi | 12 | MIT |

## Durum dağılımı (toplam 203)

yeni 84 · ayar 60 · kural_yok 31 · veri_yok 9 · mevcut 7 · yasak 7 · ml 5.
Repo kırılımı: Gekko — yeni 52, ayar 37, kural_yok 15, mevcut 4, ml 4; zenbot — ayar 15, yeni 14, kural_yok 2, veri_yok 1, ml 1; chrisleekr — yeni 10, mevcut 3, ayar 2, yasak 1; howtrader — yeni 8, ayar 5, yasak 3, kural_yok 3, veri_yok 1; 51bitquant grid — yasak 3.

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

## Belirsizlikler ve dikkat

- **Gekko `onceki_sonuc`**: `backtest_database.csv` testleri 10 dk mum, ~61 gun, Subat 2018 altcoin dususu (medyan piyasa %-22.3), Binance/Bitfinex/Poloniex/Kraken; kar yuzdeleri motor 1L3A'nin walk-forward standardiyla karsilastirilamaz, yalniz "piyasayi gecti" bilgisi kaba ipucudur. Zaman dilimi satirlarinda "mum boyutu kullanici ayari" yazdim; 10 dk daytrade sayildi.
- **Gekko bos alt modulleri** (18 klasor: Gab0, AdoptedStrategies, CloggyStrats, Kane2, TommieHansenStrategies, SuperTrend, BuyAtSellAt, NeuralNet, Neapticator, gekko-strat-hl, gekko, GekkoStrategies, ManuNet, tether, Luke_NN, NNv2, neuralnet_zschro, RSI-WR) git submodule ve klonda bos; icerigi okunamadi. Bunlardan DB'de sonucu olan RSI_WR, tether, HL, neataptic, Luke_NN_Sample, neuralnet_zschro `kural_yok`/`ml` olarak kod_yok notuyla yazildi.
- **Gekko obfuske / paketli dosyalar**: `2xTheMarket-min.js`, `bear-market.js` (base64 diziler; yalniz kullanilan gostergeler okunabildi), `BitBankStrategy*.js` (370 KB bundle), `NEO-1525230452.js` (GitHub HTML sayfasi) → `kural_yok`.
- **Gekko `jake`, `jazzbre`, `RSI_BB_ADX_Peak` BB teyidi, `Combination-*`, `tulip-multi-custom`, `stopTrailing`, `trend-based`, `loosai/oosai`, `bryanbeck`, `chang`, `signals`, `STI-DEMA`**: `check()` parcali okundu, tum esikler cikarilamadi; satirlarda "okunmadi" notu var. Kodlamadan once tam okunmali.
- **Gekko zaman damgali kopyalar** (`-1525...`): ayni mantik ya da eski/yeni arayuz farki; yalnizca icerik-farki buyuk olanlar (ATR_ADX_v2, RSI_BULL_BEAR varyantlari) ayri anildi. Tam 351 tekil icerik grubu aile bazinda birlestirildi; `exponential-moving-averages-*`, `*-candle-fetcher`, `talib.js`, `functions.js`, `indicators/*`, `debug-advice`, `noop`, `CSV_Export`, `forex.*` altyapi sayildi, satir yazilmadi.
- **Eslestirme**: `mevcut:` yalniz `dis__ema50-sapma` (EMADIV), `yeni__ma-tipli-kesisim` (DEMA/TEMA/Crossover aileleri; kuyruk adi), `pf__goreceli_guc`, `pf__sabit_sepet`, `pf__rotasyon` icin soyledim. `ayar:` olanlarin kurali mevcut ailenin ana fikrine uyuyor ama parametre/ek filtre farki var; `ayar:dis__dual-thrust` (howtrader) gunluk aralik tanimi 1L3A'dakinden farkli olabilir, kodlayan kontrol etmeli. `DI` icin `ayar:yeni__adx-di-esik-kesisimi` yalnizca DI (ADX yok) oldugu icin yakin bir tahmin.
- **Martingale giris satirlari** (`yeni`): giris kurali ekleme olmadan baska bir cikis (izleyen/+%1-2) ile calisir; ancak bu orijinal stratejinin riski/getirisi katlamaya bagli olabilir. Kullanici karari gerekebilir.
- **chrisleekr**: belge-odakli okuma; `.ts` kaynak dosyalari yalniz iki kapi (indicator/mean-reversion) acildi, digerleri belge ve config sablonlariyla dogrulandi. Sayisal sonuclar yalnizca belgedeki "research" notlari (sayi tablosu yok).
- **zenbot `trendline`** satiri kismi (satis kosulu yorum satirinda), `ta_srsi_bollinger`/`ta_stoch_bollinger` varsayilan zaman dilimi belirtilmemis.
- ccxt klonu `git sparse-checkout` ile `examples/` icin alindi (kok dosyalari da geldi); repo icinde baska yerde strateji aranmadi (talimat gereği yalniz examples/).
