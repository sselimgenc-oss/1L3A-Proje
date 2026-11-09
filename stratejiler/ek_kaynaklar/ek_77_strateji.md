# Ek Açık Kaynak Trade Stratejileri (77 adet)

*7 Kasım 2026. [8-strateji.md](8-strateji.md) dosyasındaki 8 stratejinin devamıdır ve onlarla tekrar etmez. Yıldız sayıları ve tarihler GitHub API verisidir. Her stratejinin kodu okunarak giriş, çıkış ve risk parametreleri dosyalardan çıkarıldı; hiçbir kod çalıştırılmadı. Aktarılan performans rakamları yazarların kendi beyanıdır, bağımsız doğrulama yoktur. Güvenilirlik: ★★★ güçlü, ★★ orta, ★ zayıf.*

## Önce bunu okuyun

- **77 stratejiden yalnızca birkaçı ★★★ aldı.** Bunlar akademik kökenli ve walk-forward/holdout yöntemi temiz olanlar (Momentum Transformer, DLSA, Antonacci GEM, Carver EWMAC/Carry). Gerçekçi maliyet modeli ile örneklem dışı kanıtı birlikte sunan hiçbir kripto stratejisi bulunamadı.
- **Kodda gerçek hatalar bulundu:** Lean Greenblatt Magic Formula sıralaması ters, WorldQuant 101 alfa kodunda look-ahead var, Dual Thrust sürümlerinde o günün barı tetiğe dahil, TqSdk Turtle'da giriş koşulu hiç sağlanmıyor, FinRL EIIE demosunda ölçekleme tüm veriye uygulanmış (veri sızıntısı). Ayrıntılar ilgili başlıklarda.
- **Birçok resmi örnekte komisyon sıfır** (QuantConnect Lean Alphas `ConstantFeeModel(0)`). Bu sonuçları maliyet eklemeden ciddiye almayın.
- **Pazarlama iddiaları elendi veya işaretlendi** (ör. FinRL-Trading'in 5 aylık paper işlemden "yıllık %62" iddiası, ssssi'nin doğrulanamayan copy-trade linki).

## Özet tablo

| # | Strateji | Piyasa / zaman dilimi | Not |
|---|---|---|---|
| 1 | MomentumRegimeBasket15mFast (nateemma) | Binance.US spot, yalnızca long; 15m veri, saatlik yeniden dengeleme | ★★ |
| 2 | FundingCarry (nateemma) | Spot long, fonlama verisi Binance Data Vision ve OKX'ten; 1h | ★ |
| 3 | GLFT market making (hftbacktest) | Binance USDⓈ-M vadeli ETHUSDT; tick seviyesinde L2 emir defteri | ★★ |
| 4 | Order book imbalance alfalı market making (hftbacktest) | Binance vadeli; tick seviyesinde L2 | ★★ |
| 5 | Passivbot trailing_martingale | Perpetual vadeli (Bybit, OKX, Bitget, Binance, Hyperliquid vb.); 1m mumlar ve emir defteri | ★★ |
| 6 | Passivbot ema_anchor | Perpetual vadeli; 1m | ★★ |
| 7 | OctoBot Grid Trading Mode | Spot (Binance, Hyperliquid ve 15'ten fazla borsa); olay tabanlı, zaman diliminden bağımsız | ★★ |
| 8 | OctoBot DCA Trading Mode | Spot; varsayılan olarak haftalık | ★★ |
| 9 | Uniswap v3 Bollinger bandı LP (demeter) | Polygon Uniswap v3 USDC/ETH %0,05 havuzu; dakikalık havuz verisi, 4 saatte bir yeniden ayar | ★★ |
| 10 | Delta-hedge'li Uniswap v3 LP + Aave (demeter) | Polygon Uniswap v3 USDC/ETH + Aave v3; dakikalık | ★ |
| 11 | DEX-DEX fonlama oranı arbitrajı (50shadesofgwei) | Synthetix v3 (Base), GMX (Arbitrum), ayrıca Binance, Bybit, OKX, HMX, Perennial; sürekli izleme | ★ |
| 12 | Fonlama oranı farkı tarayıcısı (aoki-h-jp) | Binance, Bybit, OKX, Gate.io, CoinEx, Bitget perpetual ve spot; anlık | ★ |
| 13 | Avellaneda-Stoikov simülasyonu (fedecaccia) | Sentetik Brownian fiyat (kripto verisi yok); T=1, 200 adım | ★ |
| 14 | CryptoFrog | Spot altcoin/USDT; 5m, 1h bilgilendirici zaman dilimi | ★ |
| 15 | Solipsis v5 (werkkrew) | Spot altcoin/USD veya /BTC; 5m, 1h bilgilendirici | ★ |
| 16 | E0V1EN (ssssi) | Binance spot USDT; 5m | ★ |
| 17 | DoubleEMACrossoverWithTrend (paulcpk) | Spot BTC, ETH, LTC, XRP, ADA, XLM, XMR, DASH /USDT; 1h | ★★ |
| 18 | IFR2 (RSI2 + Ichimoku, gabrielweich) | Binance spot ADA, BAT, NEO, REEF, UNI /USDT; 1h (Jesse) | ★★ |
| 19 | Donchian kırılımı (gabrielweich) | Binance spot BTC, ETH, ADA, BAT, NEO /USDT; 6h (Jesse) | ★★ |
| 20 | OB5F_LSv2 (OTT bantları, ysdede) | Binance Futures BTC-USDT, long ve short; 5m (Jesse) | ★ |
| 21 | Sparta Weak Hands Buster (Superalgos) | BTC/USDT spot short; 1h, 2h, 3h, 4h, 6h, 8h, 24h çoklu zaman dilimi | ★ |
| 22 | Antonacci Global Equities Momentum (GEM, dual momentum) | ABD listeli ETF'ler (SPY, ACWX, BIL, AGG) / günlük veri, aylık işlem | ★★★ |
| 23 | Keller Defensive Asset Allocation (DAA, kanarya evreni) | ABD ETF'leri (G12: SPY, IWM, QQQ, VGK, EWJ, VWO, VNQ, GSG, GLD, TLT, HYG, LQD; korunma: SHY, IEF, LQD; kanarya: VWO, BND) / aylık | ★★ |
| 24 | Connors kısa vadeli ETF ortalamaya dönüş setleri (RSI2/R3, RSI 25/75, 3 gün düşük-yüksek) | SPY (varsayılan, başka ETF verilebilir) / günlük | ★★ |
| 25 | Clenow "Stocks on the Move" (volatiliteye göre ayarlanmış hisse momentumu) | S&P 500 bileşenleri (nokta zamanlı, point-in-time) / günlük veri, haftalık işlem (çarşamba) | ★★ |
| 26 | Varlık dağılımı paketi: Faber GTAA, Ivy, Keller VAA/DAA/PAA, Kipnis KDA (pyTAA) | ABD ETF'leri / aylık (BME, iş günü ay sonu) | ★★ |
| 27 | Varlık sınıfı momentum rotasyonu (Faber tipi 5 ETF) | SPY, EFA, IEF, VNQ, GSG / aylık | ★★ |
| 28 | Zaman serisi momentumu (TSMOM, Moskowitz-Ooi-Pedersen) | Yaklaşık 60 vadeli işlem sözleşmesi (emtia, döviz, hisse endeksi, tahvil), sürekli geri ayarlı seri / aylık | ★★ |
| 29 | Ay dönümü etkisi (turn-of-the-month, SPY) | SPY / günlük | ★★ |
| 30 | Volatilite risk primi: korumalı kısa straddle (SPY opsiyonları) | SPY ve SPY opsiyonları / dakikalık veri, aylık döngü | ★ |
| 31 | Kısa put ve 16 delta iron condor (optopsy) | Hisse ve endeks opsiyonları (SPX, SPY vb.) / günlük opsiyon zinciri | ★★ |
| 32 | SteadyOptions "Anchor Trade" (LEAP call, uzun put koruması ve aylık put satışı) | SPX, XSP ya da SPY opsiyonları / günlük | ★ |
| 33 | Küresel ülke ETF'lerinde IBS ortalamaya dönüşü | 32 ülke ve bölge ETF'i (EWJ, EWZ, FXI, SPY, QQQ vb.) / günlük | ★ |
| 34 | Greenblatt "Magic Formula" (QuantConnect uygulaması) | ABD hisseleri (dolar hacmine göre ilk 500) / aylık evren, günlük veri | ★ |
| 35 | 3x kaldıraçlı ETF çifti volatilite aşınması (UGLD/DGLD) | UGLD ve DGLD (3x long ve 3x short altın ETN'leri) / günlük | ★ |
| 36 | Dual Thrust (açılış etrafında aralık kırılımı) | SPX endeksi (vadeli işlem stratejisi olarak tasarlanmış) / günlük | ★ |
| 37 | R-Breaker (pivot destek ve direnç, tersine dönüş ve kırılım) | SPX endeksi (aslen emtia vadelileri için gün içi strateji) / günlük | ★ |
| 38 | Heikin-Ashi mum momentum ve dönüş sinyali | NVDA (tek hisse, yfinance) / günlük | ★ |
| 39 | Kointegrasyon tabanlı çift işlemi (Engle-Granger) | NVDA ve AMD (2013-2014) / günlük | ★ |
| 40 | Deep Learning Statistical Arbitrage (CNN+Transformer, PCA/IPCA artıkları) | ABD hisseleri (CRSP evreni, piyasa değeri filtresi), günlük | ★★★ |
| 41 | Qlib LightGBM + Alpha158 + TopkDropout | Çin A hisseleri (CSI300, CSI500 varyantı da var), günlük | ★★ |
| 42 | Qlib DoubleEnsemble (LightGBM topluluğu) | Çin A hisseleri (CSI300), günlük | ★★ |
| 43 | Qlib TRA (Temporal Routing Adaptor, rejim yönlendirmeli LSTM) | Çin A hisseleri (CSI300), günlük | ★★ |
| 44 | Momentum Transformer (Oxford-Man, vadeli işlemlerde derin momentum) | 100 sürekli vadeli kontrat (emtia, endeks, tahvil, döviz), günlük | ★★★ |
| 45 | Slow Momentum with Fast Reversion (LSTM Deep Momentum Network + değişim noktası tespiti) | 100 sürekli vadeli kontrat, günlük | ★★ |
| 46 | FinRL Ensemble Stock Trading (A2C/PPO/DDPG) | Dow 30 hisseleri, günlük | ★ |
| 47 | FinRL EIIE Portföy Optimizasyonu (Jiang ve ark. policy gradient) | Brezilya hisseleri (örnek defterde `TOP_BRL`), günlük | ★ |
| 48 | FinRL-Trading ML Hisse Seçimi (sektör kovası bazlı Random Forest/LightGBM/XGBoost) | S&P 500 hisseleri, çeyreklik yeniden dengeleme | ★★ |
| 49 | FreqaiExampleStrategy (LightGBM regresyonu, kripto) | Binance kripto (spot ya da vadeli), 3 dakikalık mumlar (5m/15m/4h ek zaman dilimleri) | ★ |
| 50 | Litmus MLDP: FreqAI üzerinde meta-labeling ve triple-barrier | Kripto vadeli (Binance), 5 dakikalık mumlar | ★ |
| 51 | NautilusTrader Hurst/VPIN Directional (dolar barları, mikroyapı) | Kraken Futures `PF_XBTUSD`, dolar barları (2.000.000 USD notional) ve tick verisi | ★ |
| 52 | PyBroker Walk-Forward ML Örneği (CMMA + doğrusal regresyon) | ABD hisseleri (örnekte NVDA, AMD), günlük, Yahoo Finance | ★ |
| 53 | ML4T 3. Baskı: ETF Vaka Çalışması (LightGBM/LSTM kesitsel sıralama) | 100 çok varlıklı ABD ETF'i, günlük veri, aylık yeniden dengeleme | ★★ |
| 54 | ML4T 3. Baskı: CME Vadeli Vaka Çalışması (taşıma/momentum sıralamalı long-short) | 30 CME vadeli kontratı (endeks, tahvil, enerji, metal, döviz, tarım, hayvancılık), günlük veri, haftalık karar | ★★ |
| 55 | ArbitrageLab PCA Stat-Arb (Avellaneda-Lee eigenportfolio s-skoru) | ABD hisseleri (S&P 500'den yaklaşık 170 hisse), günlük, yfinance | ★★ |
| 56 | ArbitrageLab Kalman Filtreli Pairs Trading (EWA/EWC) | EWA ve EWC ülke ETF'leri, günlük, 2006-2012 | ★ |
| 57 | Carver EWMAC ve Carry kuralları (systematictradingexamples) | Vadeli işlemler (ham petrol, US10, Bund, döviz, endeks vb. yaklaşık 40 kontrat, CSV olarak repoda) / günlük | ★★★ |
| 58 | EA31337 (MT4/MT5 çok stratejili Forex EA) | Forex, varsayılan olarak EURUSD / M1'den H12'ye kadar zaman dilimi başına ayrı strateji | ★★ |
| 59 | Geraked BBRSI ve diğer MT5 EA'ları (grid ile) | XAUUSD 5 dakika (BBRSI); diğer EA'lar AUDUSD 5M, NZDUSD 3H, USDCAD 15M gibi farklı semboller | ★ |
| 60 | JamesORB: Frankfurt/Londra açılış aralığı kırılımı (MQL4) | Forex (sembol sabit değil) / saatlik | ★ |
| 61 | QuantConnect Lean: Intraday FX Reversal (EURUSD) | Forex, EURUSD (OANDA) / saatlik | ★★ |
| 62 | QuantConnect Lean: VIX Dual Thrust (aslında SPY) | ABD hisse (SPY) / 30 dakikalık konsolide barlar | ★ |
| 63 | QuantConnect Lean: Futures Momentum (E-mini S&P EMA cross) | CME E-mini S&P 500 vadeli / günlük sinyal | ★ |
| 64 | QuantConnect Lean: ETF Global Rotation | ABD ETF'leri (MDY, IEV, EEM, ILF, EPP; güvenli liman EDV, SHY) / aylık rotasyon | ★ |
| 65 | WorldQuant 101 Formulaic Alphas (Python uygulaması) | Hisse senedi kesiti (orijinalde ABD) / günlük | ★ |
| 66 | Clenow "Stocks on the Move" momentum tarayıcısı | ABD hisseleri (S&P 500 ve Nasdaq 100, isteğe bağlı S&P 400/600) / günlük, haftalık yeniden dengeleme (kitaba göre) | ★★ |
| 67 | TqSdk Dual Thrust (Çin vadeli) | Çin vadeli işlemleri (varsayılan SHFE bakır `SHFE.cu2501`) / gün içi, tick bazlı tetik | ★ |
| 68 | TqSdk Turtle (Çin vadeli) | Çin vadeli (varsayılan INE ham petrol `INE.sc2501`) / günlük | ★ |
| 69 | Pine Script: Alorse strateji koleksiyonu (CI ile backtest edilmiş) | Kripto ağırlıklı (testler BTCUSDT günlük) | ★ |
| 70 | Pine Script: Acrypto Weighted Strategy | Kripto (örnek BTC/USDT Binance 4 saat) | ★ |
| 71 | Pine Script: krosenfeld7 EMA/osilatör stratejileri | Belirtilmemiş, yorumda "saatlik grafikte en iyi" | ★ |
| 72 | backtesting.py örnekleri: SmaCross + ATR trailing ve çok zaman dilimli RSI | ABD hisse (paketle gelen GOOG 2004-2013 verisi) / günlük | ★ |
| 73 | vectorbt: BTC çift MA çaprazı için walk-forward optimizasyon | BTC-USD (Yahoo) / günlük | ★★ |
| 74 | NautilusTrader: AUD/USD tick verisiyle EMA cross | Forex AUD/USD (TrueFX tick verisi) / 100 tick'lik mid barlar | ★ |
| 75 | Alpaca resmi örneği: Scalping (20 dakikalık SMA) | ABD hisseleri (kullanıcının verdiği semboller) / 1 dakika | ★ |
| 76 | Alpaca resmi örneği: Momentum day trading | ABD düşük fiyatlı hisseler (2 ile 13 USD) / 1 saniye ve 1 dakika | ★ |
| 77 | Alpaca resmi örneği: Options Wheel | ABD hisse opsiyonları (varsayılan AAPL, QQQ, INTC, CAT, DLR, MP, NVDA, PLTR, AAL, V) / günde birkaç kez cron ile | ★★ |

## Kripto (bot, market making, grid/DCA, funding, DEX)

### 1. MomentumRegimeBasket15mFast (nateemma) ★★

| | |
|---|---|
| Repo | https://github.com/nateemma/strategies (`Basket/MomentumRegimeBasket15mFast.py`, ana sınıf `Basket/MomentumRegimeBasket15m.py`) |
| Yıldız / son güncelleme | 442 / 2026-10-27 |
| Lisans | GPL-3.0 |
| Piyasa / zaman dilimi | Binance.US spot, yalnızca long; 15m veri, saatlik yeniden dengeleme |
| Yazar | "Phil" (GitHub: nateemma); profesyonel geçmişi doğrulanamadı |

**Mantık:** Kesitsel momentum sepetidir. Rejim filtresi olarak BTC günlük kapanışı SMA100'ün üzerinde olmalıdır; ayrıca her coin için SMA50 trend filtresi uygulanır. Coinler 14 günlük getiriye göre sıralanır (`MOM_LOOKBACK_DAYS = 14`; temel sınıfta 90 gün) ve ilk 3 coin (`TOP_N=3`) eşit ağırlıkla tutulur. Pozisyon tek seferde açılmaz: `adjust_trade_position` ile her mumda, o mumun kote hacminin en fazla %10'u kadar eklenerek hedef ağırlığa doğru biriktirilir. Çıkış, coin sıralamada `EXIT_RANK_N=9`'un dışına düştüğünde ya da rejim risk-off'a döndüğünde tam satıştır. Aşırı büyüyen pozisyon `MAX_POSITION_WEIGHT` ile kırpılır. ROI tablosu ve stop yerine rejim ve sıralama tabanlı çıkış kullanılır.

**Güvenilirlik:** Kanıt, yazarın freqtrade backtest'idir (2024-08-31 ile 2026-08-20 arası, 596 işlem, +%444, maksimum düşüş %61,7) ve gerçekçi dolum için hacim sınırı ile bir sonraki mumda dolum içerir. Yazar olağandışı derecede dürüst: ilk 5 işlemin net kârın %107'sini oluşturduğunu, medyan kazancın medyan kayıptan küçük olduğunu ve 14 günlük pencerenin 2021-2022 rejiminde altı aday arasında beşinci sırada kaldığını, yani rejimler arası doğrulanmadığını dosyanın başında yazıyor. Overfit işaretleri şunlardır: lookback ve `EXIT_RANK_N` taraması aynı veri üzerinde yapılmış, kâr birkaç coine (ZEC/PENGU/TROLL) dayanıyor ve %60 civarında düşüş var. Look-ahead için ayrı bir test dosyası (`test_momentum_regime_bias.py`) bulunuyor.

**Çalıştırma:**
```
freqtrade download-data -c user_data/strategies/config/config_mom_15m.json -t 15m 1d --days 720
freqtrade backtesting -c user_data/strategies/config/config_mom_15m.json -s MomentumRegimeBasket15mFast
```

---

### 2. FundingCarry (nateemma) ★

| | |
|---|---|
| Repo | https://github.com/nateemma/strategies (`Funding/FundingCarry.py`) |
| Yıldız / son güncelleme | 442 / 2026-10-27 |
| Lisans | GPL-3.0 |
| Piyasa / zaman dilimi | Spot long, fonlama verisi Binance Data Vision ve OKX'ten; 1h |
| Yazar | "Phil" (nateemma); doğrulanamadı |

**Mantık:** Fonlama oranı tersine dönüşüne dayanır. Son 90 fonlama ödemesi (yaklaşık 30 gün) üzerinden hesaplanan z-skoru `ENTRY_Z = -1.5`'in altına indiğinde, yani short pozisyonlar kalabalıklaştığında, spot long açılır. Çıkış yalnızca zamana bağlıdır: `MAX_HOLD_H = 16` saat. ROI (`{"0": 10.0}`) ve stop (`-0.99`) bilinçli olarak kapatılmıştır. Devre kesici olarak yalnızca BTC, SMA(500, yaklaşık 21 gün) üzerindeyken giriş yapılır. Emir büyüklüğü mum kote hacminin %10'u ile sınırlanır.

**Güvenilirlik:** Yazar sinyalin gerçek ancak yakalanmasının marjinal olduğunu kendisi söylüyor: backtest işlemlerinin yaklaşık %73'ü Binance.US'te doldurulamaz, hacim sınırı açıldığında sonuç +%23,7'den +%6,6'ya (Sharpe 0,89) düşüyor ve 2025 sonrası dönem düz ile negatif arasında. Hedge'siz spot long olduğu için piyasa betası taşır; bu nedenle gerçek bir cash-and-carry değildir. Stop olmaması ve -0.99 stoploss bilinçli bir tasarım tercihi olarak belgelenmiştir.

**Çalıştırma:**
```
python user_data/strategies/scripts/refresh_funding.py
freqtrade backtesting -c <config> -s FundingCarry -t 1h
```

---

### 3. GLFT market making (hftbacktest) ★★

| | |
|---|---|
| Repo | https://github.com/nkaz001/hftbacktest (`examples/GLFT Market Making Model and Grid Trading.ipynb`) |
| Yıldız / son güncelleme | 5055 / 2025-12-23 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Binance USDⓈ-M vadeli ETHUSDT; tick seviyesinde L2 emir defteri |
| Yazar | nkaz001; gerçek adı ve profesyonel geçmişi doğrulanamadı |

**Mantık:** Guéant-Lehalle-Fernandez-Tapia (Avellaneda-Stoikov'un sonsuz ufuklu hali) kotasyonudur. Piyasa emri varış derinliğinden A ve k kalibre edilir, `compute_coeff(xi=gamma, gamma=0.05, delta=1, A, k)` ile c1 ve c2 elde edilir. Yarı spread `c1 + delta/2 * c2 * volatilite`, eğim (skew) `c2 * volatilite` ve rezervasyon fiyatı `mid - skew * pozisyon` olarak hesaplanır. Teklifler en iyi bid/ask'tan içeri girmeyecek şekilde GTX (post-only) limit emirleriyle verilir. Pozisyon büyüklüğü `order_qty = 1`, envanter sınırı `max_position = 20` ile yönetilir.

**Güvenilirlik:** Bu listedeki en gerçekçi backtest altyapısıdır: kuyruk pozisyonu modeli (`power_prob_queue_model(2.0)`), ölçülmüş emir gecikmesi ve maker -%0,005 / taker %0,07 ücret içerir. Yazar sonuçları abartmıyor: notebook'ta "rebate dahil bile en iyi ihtimalle başa baş" ve "kâr rebate'ten geliyor" deniyor. Sınırlar şunlardır: veri tek gün ile beş günle sınırlı (2022-10), varsayılan rebate Binance'in en yüksek likidite sağlayıcı kademesi ve sıradan bir hesap buna erişemez. Kod bir eğitim örneğidir, hazır bir canlı bot değildir.

**Çalıştırma:**
```
pip install hftbacktest
# Binance ham verisini collector ile toplayıp npz'ye çevirin, ardından notebook'u çalıştırın
jupyter lab "examples/GLFT Market Making Model and Grid Trading.ipynb"
```

---

### 4. Order book imbalance alfalı market making (hftbacktest) ★★

| | |
|---|---|
| Repo | https://github.com/nkaz001/hftbacktest (`examples/Market Making with Alpha - Order Book Imbalance.ipynb`) |
| Yıldız / son güncelleme | 5055 / 2025-12-23 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Binance vadeli; tick seviyesinde L2 |
| Yazar | nkaz001; doğrulanamadı |

**Mantık:** Orta fiyatın belirli bir derinliği (`looking_depth`) içindeki bid ve ask miktarlarının farkı alınır, son bir saatlik pencerede standartlaştırılarak alfa elde edilir (`(x - ortalama) / std`). Adil fiyat `mid + c1 * alfa`, rezervasyon fiyatı `adil fiyat - skew * normalize pozisyon` olarak hesaplanır. Örnek parametre setleri `half_spread=80, skew=3.5, c1=160` ve `half_spread=5, skew=0.2, c1=10` (tick cinsinden) şeklindedir. Envanter sınırı `max_position_dollar = order_qty_dollar * 50` olarak belirlenir.

**Güvenilirlik:** Ücret, gecikme ve kuyruk modeli GLFT örneğiyle aynıdır. Parametreler elle seçilmiş ve az sayıdadır; kapsamlı bir optimizasyon görünmüyor, ancak örneklem dışı test de yok. Alfanın kalıcılığı tek varlık ve kısa bir dönem üzerinde gösteriliyor. Sonuçların büyük kısmı rebate varsayımına duyarlıdır.

**Çalıştırma:**
```
jupyter lab "examples/Market Making with Alpha - Order Book Imbalance.ipynb"
```

---

### 5. Passivbot trailing_martingale ★★

| | |
|---|---|
| Repo | https://github.com/enarjord/passivbot (`configs/examples/default_trailing_martingale_long.json`, Rust çekirdeği `passivbot-rust/src/`) |
| Yıldız / son güncelleme | 2158 / 2026-11-06 |
| Lisans | Unlicense |
| Piyasa / zaman dilimi | Perpetual vadeli (Bybit, OKX, Bitget, Binance, Hyperliquid vb.); 1m mumlar ve emir defteri |
| Yazar | enarjord; doğrulanamadı |

**Mantık:** Kontrarian grid/DCA ve martingale yaklaşımını birleştirir. Başlangıç girişi EMA bandının `initial_ema_dist=0.0028` altında, sermayenin `initial_qty_pct=0.0081` oranında verilir. Fiyat aleyhe gittikçe `double_down_factor=0.94` ile ek alım yapılır. Yeniden giriş ve kapanışlar volatiliteye göre ölçeklenen eşik ve geri çekilme ("trailing") koşullarına bağlıdır. Kapanışta pozisyonun `qty_pct=0.84` kadarı kapatılır. Risk tarafında `n_positions=7` ve `total_wallet_exposure_limit=1.5` (1,5x kaldıraç eşdeğeri) kullanılır. Zararda kalan pozisyonlar "unstuck" mekanizmasıyla küçük parçalar halinde zararına kapatılır (`loss_allowance_pct=0.0052`). Hacim ve volatiliteye göre coin seçen "Forager" modülü de vardır.

**Güvenilirlik:** Uzun süredir aktif ve canlıda yaygın kullanılan bir projedir. Backtest ile canlı aynı Rust orkestratörünü kullanır. Overfit riski yüksektir: örnek config'teki ondalıklı ağırlıklar (`retracement_volatility_1m_weight=52.34` gibi) evrimsel optimizasyon çıktısıdır. Martingale yapısı nedeniyle dağılımın sol kuyruğu kalındır: trend piyasada pozisyon büyür ve sistem kademeli zarar realizasyonuna dayanır. Equity hard stop (`hsl`) örnek config'te kapalı (`enabled: false`).

**Çalıştırma:**
```
pip install -e .
passivbot backtest configs/examples/default_trailing_martingale_long.json
passivbot live configs/examples/default_trailing_martingale_long.json
```

---

### 6. Passivbot ema_anchor ★★

| | |
|---|---|
| Repo | https://github.com/enarjord/passivbot (`passivbot-rust/src/strategies/ema_anchor.rs`, `configs/examples/ema_anchor.json`) |
| Yıldız / son güncelleme | 2158 / 2026-11-06 |
| Lisans | Unlicense |
| Piyasa / zaman dilimi | Perpetual vadeli; 1m |
| Yazar | enarjord; doğrulanamadı |

**Mantık:** Market maker benzeri iki taraflı kotasyon kullanır. Bid fiyatı `min(en iyi bid, alt EMA bandı * (1 - offset - envanter kayması))`, ask fiyatı simetrik olarak hesaplanır. Örnek config'te `offset=0.0193` (%1,93) ve EMA aralığı 415/793 dakikadır. Offset, 1m ve 1h volatilite ağırlıklarıyla (`0.4` ve `13.0`) genişletilir. Envanter kayması `offset_psize_weight=0.3576` ile pozisyon büyüdükçe kotasyonu kaydırır. Ek alımlar `entry_double_down_factor=1.96` ile büyür; bu, trailing_martingale'den daha agresiftir.

**Güvenilirlik:** Mantık sade ve okunaklıdır, Avellaneda-Stoikov'daki envanter eğimine benzer. Parametreler yine optimizasyon çıktısıdır ve bağımsız bir performans kanıtı yoktur. Bu örnekte unstuck kapalıdır (`enabled: false`), bu da trend piyasada sınırsız envanter riskine yol açar.

**Çalıştırma:**
```
passivbot backtest configs/examples/ema_anchor.json
```

---

### 7. OctoBot Grid Trading Mode ★★

| | |
|---|---|
| Repo | https://github.com/Drakkar-Software/OctoBot-Tentacles (`Trading/Mode/grid_trading_mode/grid_trading.py`); ana uygulama https://github.com/Drakkar-Software/OctoBot |
| Yıldız / son güncelleme | 176 / 2026-02-03 (ana repo 6904 / 2026-11-02) |
| Lisans | LGPL-3.0 (ana repo GPL-3.0) |
| Piyasa / zaman dilimi | Spot (Binance, Hyperliquid ve 15'ten fazla borsa); olay tabanlı, zaman diliminden bağımsız |
| Yazar | Drakkar-Software (OctoBot'u geliştiren Fransız şirket); bireysel geçmiş doğrulanamadı |

**Mantık:** Sabit aralıklı klasik grid kurar. Varsayılan BTC/USDT ayarında `flat_spread=2000` (orta fiyat çevresindeki boşluk), `flat_increment=1000` (emirler arası USDT farkı), 25 alış ve 25 satış emri bulunur. Bir emir dolduğunda karşı yönde "mirror" emri bir artım ötesine yerleştirilir. Opsiyonel olarak `enable_trailing_up/down` ile grid fiyatı takip eder ve `reinvest_profits` ile kâr yeniden yatırılır. Stop yoktur; risk, grid aralığının dışına çıkıldığında tek yönlü envanter birikmesidir.

**Güvenilirlik:** Mekanik bir kural setidir ve sinyal optimizasyonu içermez; bu yüzden overfit riski düşüktür. Buna karşılık grid'in kârlılığı tamamen yatay piyasa varsayımına dayanır ve repo herhangi bir performans iddiasında bulunmaz. Ücretler `ignore_exchange_fees=false` iken mirror emir fiyatına dahil edilir.

**Çalıştırma:**
```
pip install OctoBot
OctoBot   # web arayüzünden Trading mode: GridTradingMode seçilir, backtest ya da paper trading ile denenir
```

---

### 8. OctoBot DCA Trading Mode ★★

| | |
|---|---|
| Repo | https://github.com/Drakkar-Software/OctoBot-Tentacles (`Trading/Mode/dca_trading_mode/dca_trading.py`) |
| Yıldız / son güncelleme | 176 / 2026-02-03 |
| Lisans | LGPL-3.0 |
| Piyasa / zaman dilimi | Spot; varsayılan olarak haftalık |
| Yazar | Drakkar-Software; doğrulanamadı |

**Mantık:** Varsayılan config (`DCATradingMode.json`) zaman tabanlıdır: her `minutes_before_next_buy=10080` dakikada (bir hafta) piyasa emriyle `buy_order_amount="50q"` (50 birim kote para) alım yapılır. Çıkış emirleri, take-profit ve stop varsayılan olarak kapalıdır (`use_take_profit_exit_orders=false`, `use_stop_losses=false`). İsteğe bağlı olarak `exit_limit_orders_price_percent=5` ile çıkış ve ikincil kademeli giriş emirleri açılabilir. Ikinci tetik modu ("Maximum evaluators signals based") girişleri değerlendirici sinyallerine bağlar.

**Güvenilirlik:** Bir alfa stratejisi değil, düzenli birikim aracıdır; overfit edilecek parametresi yok gibidir. Kodda zaman tabanlı modun backtest'i desteklemediği açıkça yazıyor ("trigger is not supporting backtesting for now"), dolayısıyla backtest kanıtı yalnızca sinyal tabanlı modla üretilebilir.

**Çalıştırma:**
```
OctoBot   # arayüzden DCATradingMode, gerekirse trigger_mode "Maximum evaluators signals based" ile backtest
```

---

### 9. Uniswap v3 Bollinger bandı LP (demeter) ★★

| | |
|---|---|
| Repo | https://github.com/zelos-alpha/demeter (`samples/strategy-example/13_bollinger_bands.py`) |
| Yıldız / son güncelleme | 91 / 2026-10-24 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Polygon Uniswap v3 USDC/ETH %0,05 havuzu; dakikalık havuz verisi, 4 saatte bir yeniden ayar |
| Yazar | Zelos (zelos-alpha) DeFi araştırma ekibi; bireysel geçmiş doğrulanamadı |

**Mantık:** Yoğunlaştırılmış likidite aralığı Bollinger bandına göre seçilir. 1 günlük SMA (`pa`) ve 1 günlük gerçekleşmiş volatilite (`v`) hesaplanır ve likidite `[pa - c*v*fiyat, pa + c*v*fiyat]` aralığına (`c = 2`) yatırılır. Her 4 saatte bir tüm likidite çekilir, sermaye iki varlığa eşit bölünür (`even_rebalance`) ve yeni aralıkla tekrar eklenir. Stop yoktur; risk geçici kayıp (impermanent loss) ve aralık dışına düşmedir. Kaynak olarak ETH Zürih lisans tezi ("Providing Liquidity in Uniswap V3") ve GammaStrategies'in active-strategy-framework'ü gösteriliyor.

**Güvenilirlik:** Parametre azdır (c=2, 1 gün, 4 saat) ve akademik bir kaynağa dayanır. Örnek yalnızca 5 günlük veriyle (2023-08-13 ile 2023-08-17) gelir ve bir performans iddiası yoktur. Her 4 saatte bir yapılan swap ve gas maliyetleri ayrı bir örnekte (`07_estimate_gas_used.py`) tahmin edilir; varsayılan backtest'te gas hesaba katılmadığı için sonuç iyimser olabilir.

**Çalıştırma:**
```
pip install zelos-demeter
cd samples/strategy-example && python 13_bollinger_bands.py
```

---

### 10. Delta-hedge'li Uniswap v3 LP + Aave (demeter) ★

| | |
|---|---|
| Repo | https://github.com/zelos-alpha/demeter (`samples/strategy-example/23_delta_hedging.py`) |
| Yıldız / son güncelleme | 91 / 2026-10-24 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Polygon Uniswap v3 USDC/ETH + Aave v3; dakikalık |
| Yazar | Zelos; doğrulanamadı |

**Mantık:** LP pozisyonunun ETH deltası, Aave'den ödünç alınan ETH ile nötrlenir. Aralık fiyatın `L=0.8` ile `H=1.2` katı arasıdır. SLSQP optimizasyonu, Aave'ye USDC teminat, ETH borçlanma ve LP miktarlarını delta-nötr kısıtı ve `AAVE_POLYGON_USDC_ALPHA=0.7` borçlanma oranı sınırı altında LP büyüklüğünü maksimize edecek şekilde belirler. Pozisyon değiştiğinde önce tüm LP ve borçlar kapatılır, sonra yeniden kurulur.

**Güvenilirlik:** Teorik olarak sağlam bir fikirdir (LP ücretini yönsüz toplamak), ancak örnek kodda yeniden ayar yalnızca başlangıçta tek bir `AtTimeTrigger` ile yapılıyor; fiyat aralıktan çıktığında hedge bozulur. Borç faizi, likidasyon ve gas ayrıntılı modellenmiyor. Bu haliyle canlı bir stratejiden çok bir şablondur.

**Çalıştırma:**
```
cd samples/strategy-example && python 23_delta_hedging.py
```

---

### 11. DEX-DEX fonlama oranı arbitrajı (50shadesofgwei) ★

| | |
|---|---|
| Repo | https://github.com/50shadesofgwei/funding-rate-arbitrage (`MatchingEngine/MatchingEngine.py`, `PositionMonitor/Master/MasterPositionMonitor.py`) |
| Yıldız / son güncelleme | 186 / 2025-07-29 |
| Lisans | yok (README MIT diyor, ancak repoda lisans dosyası algılanmıyor) |
| Piyasa / zaman dilimi | Synthetix v3 (Base), GMX (Arbitrum), ayrıca Binance, Bybit, OKX, HMX, Perennial; sürekli izleme |
| Yazar | 50shadesofgwei (takma ad); doğrulanamadı |

**Mantık:** Aynı token için iki platform arasındaki fonlama oranı farkını delta-nötr biçimde toplar: fonlaması yüksek tarafta short, düşük tarafta long açılır. Eşleştirme motoru, oranların işaret kombinasyonlarına göre hangi tarafın long olacağını seçer. Önerilen ayarlar `TRADE_LEVERAGE=5`, `DELTA_BOUND=0.03`, `PERCENTAGE_CAPITAL_PER_TRADE=50` şeklindedir. Pozisyon monitörü dört durumda kapatır: likidasyon riski, kârlılığın bitmesi, deltanın sınırı aşması ve Synthetix fonlama hızının 15 dakika içinde aleyhe dönmesi.

**Güvenilirlik:** Gerçek emir gönderen bir bottur, bu da onu tarayıcılardan ayırır. Buna karşın README "henüz üretimde kapsamlı çalıştırılmadı" diyor ve geliştirmeye devam edilmesi önerilmiyor (son güncelleme 2025-07). Backtest modülü mevcut, ancak işlem maliyeti, kayma ve iki zincir arasındaki teminat transfer maliyetinin ne ölçüde dahil edildiği belirsiz. 5x kaldıraçlı iki bacaklı pozisyonda bacaklardan birinin likide olma riski var.

**Çalıştırma:**
```
pip install -r requirements.txt && pip install -e .
# .env içine Alchemy anahtarı, cüzdan, TRADE_LEVERAGE vb. girilir; önce testnet
project-run-demo   # gerçek işlem için: project-run
```

---

### 12. Fonlama oranı farkı tarayıcısı (aoki-h-jp) ★

| | |
|---|---|
| Repo | https://github.com/aoki-h-jp/funding-rate-arbitrage (`funding_rate_arbitrage/frarb.py`) |
| Yıldız / son güncelleme | 314 / 2023-11-05 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Binance, Bybit, OKX, Gate.io, CoinEx, Bitget perpetual ve spot; anlık |
| Yazar | aoki-h-jp; doğrulanamadı |

**Mantık:** ccxt ile tüm perpetual fonlama oranlarını çeker ve iki tür fırsat listeler. Tek borsada spot long ile perp short (cash-and-carry), çok borsada ise iki perp arasındaki fonlama farkı. Fırsatlar, borsa başına sabit kodlanmış maker/taker komisyonları (`get_commission`, ör. Binance spot taker %0,075) iki giriş ve iki çıkış için düşülerek "net getiri"ye göre sıralanır.

**Güvenilirlik:** README'nin kendisi "otomatik arbitraj içermez" diyor; bu bir strateji değil, sinyal tarayıcısıdır. Komisyon tabloları 2023'ten kalma ve sabit kodlu, fonlama oranının sonraki dönemlerde süreceği varsayılıyor, backtest yok. Cash-and-carry fikrinin şeffaf bir başlangıç noktası olarak değerlidir.

**Çalıştırma:**
```
pip install git+https://github.com/aoki-h-jp/funding-rate-arbitrage
python examples/get_large_divergence_multi_exchange.py
```

---

### 13. Avellaneda-Stoikov simülasyonu (fedecaccia) ★

| | |
|---|---|
| Repo | https://github.com/fedecaccia/avellaneda-stoikov (`src/main.py`) |
| Yıldız / son güncelleme | 737 / 2023-07-06 |
| Lisans | yok |
| Piyasa / zaman dilimi | Sentetik Brownian fiyat (kripto verisi yok); T=1, 200 adım |
| Yazar | fedecaccia; doğrulanamadı |

**Mantık:** Orijinal makalenin doğrudan uygulamasıdır. Rezervasyon fiyatı `s - q*gamma*sigma^2*(T-t)`, kotasyonlar bunun etrafına `2/gamma * ln(1 + gamma/k)` toplam spread ile yerleştirilir (`gamma=0.1, sigma=2, k=1.5`). Dolum olasılığı `A*exp(-k*delta)` ile simüle edilir. Sonsuz ufuk seçeneğinde envanter sınırı `q_max=10` kullanılır. 100 simülasyonun PnL dağılımı çizdirilir.

**Güvenilirlik:** Eğitim amaçlı bir Monte Carlo'dur. Gerçek veri, ücret ya da gecikme yoktur. Kodda iki önemli sapma var: fiyata her adımda yapay bir yukarı trend ekleniyor (`s[n] = s[n] + 0.1 * n`) ve spread formülünden makaledeki `gamma*sigma^2*(T-t)` terimi eksik. Yıldız sayısı yüksek, ancak bu bir borsada çalışan strateji değil. Gerçek veriyle AS/GLFT için hftbacktest örnekleri tercih edilmeli.

**Çalıştırma:**
```
cd src && pip install -r requirements.txt && python main.py
```

---

### 14. CryptoFrog ★

| | |
|---|---|
| Repo | https://github.com/froggleston/cryptofrog-strategies (`CryptoFrog.py`) |
| Yıldız / son güncelleme | 185 / 2022-03-02 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | Spot altcoin/USDT; 5m, 1h bilgilendirici zaman dilimi |
| Yazar | froggleston; finans geçmişi doğrulanamadı |

**Mantık:** Long-only "dip alma" stratejisidir. Ön koşul olarak kapanış, 5m düzleştirilmiş Heikin-Ashi dibinin altında ve 1h HA EMA'sı düşüşte olmalıdır. Ardından dört alternatif tetikten biri gerekir: Bollinger genişlemesi + squeeze yok + (MFI<20 veya DMI- >30); SAR altında + StochRSI ve Stoch fast aşırı satım + MFI<30; DMI- kesişimi + alt Bollinger altında; squeeze + fastd<20. Bunlara VFI<0 hacim filtresi eklenir. Çıkış, simetrik aşırı alım koşulları, ROI tablosu (`0: %21,3, 39dk: %10,3, 96dk: %3,7, 166dk: 0`), trailing stop (`+%4,7` sonrası %1) ve werkkrew'den alınan, -%8,5'ten başlayıp sönümlenen özel stop ile olur.

**Güvenilirlik:** README'nin ilk satırı "DO NOT USE THIS FOR LIVE TRADING" diyor. Kodun içinde "this strat REALLY benefits from roi and trailing hyperopt" yorumu ve "just throw in any old SQZMI shit based fastd, this needs work!" notu var. Onlarca koşul ve hyperopt edilmiş ROI tablosu güçlü overfit işaretidir. Yayınlanmış bir backtest sonucu yok ve repo 2022'den beri güncellenmiyor; yeni freqtrade sürümlerinde `populate_buy_trend` arayüzü uyarı verir.

**Çalıştırma:**
```
cp CryptoFrog.py custom_indicators.py user_data/strategies/
freqtrade backtesting -c cryptofrog.config.json -s CryptoFrog -t 5m
```

---

### 15. Solipsis v5 (werkkrew) ★

| | |
|---|---|
| Repo | https://github.com/werkkrew/freqtrade-strategies (`strategies/solipsis/Solipsis_v5.py`) |
| Yıldız / son güncelleme | 324 / 2021-06-04 |
| Lisans | yok |
| Piyasa / zaman dilimi | Spot altcoin/USD veya /BTC; 5m, 1h bilgilendirici |
| Yazar | werkkrew (JimmyNixx ile birlikte, freqtrade Discord); doğrulanamadı |

**Mantık:** Düşüş trendinde dönüş arar. Giriş koşulları: RMI düşüş serisi `>= 3`, MA streak `>= 1`, RMI 20 ile 50 arası, Momentum Pinball `<= 30`, RMI yukarı dönüş tetiği ve fiyatın günlük dibe ADR'nin %80'inden yakın olması. BTC bilgilendirici filtresi ("lazy": coin KAMA üzerinde ya da BTC RMI > 40 ve BTC KAMA üzerinde) eklenir. Statik ROI kapalıdır (`"0": 100`), stoploss `-0.99`'dur. Çıkışlar tamamen `custom_sell` ve `custom_stoploss` içinde yapılır: trend sürerken kârda kalınır, %1 geri çekilmede satılır, ROI 720 dakika sonra %1'den 0'a basamaklanır.

**Güvenilirlik:** README'de "VARSAYILAN PARAMETRELER KASITLI OLARAK KÖTÜ, HYPEROPT ZORUNLU" ve "artık kullanmıyorum" yazıyor. 25'ten fazla hyperopt parametresi, -0.99 stoploss ve kullanıcının kendi verisine hyperopt yapmasının beklenmesi, yüksek overfit riski demektir. Topluluğun pek çok stratejisini (CryptoFrog dahil) etkileyen tarihsel bir referans olarak değerlidir.

**Çalıştırma:**
```
cp strategies/solipsis/*.py user_data/strategies/
freqtrade hyperopt -s Solipsis_v5 --hyperopt-loss SharpeHyperOptLoss --spaces buy sell -e 500
```

---

### 16. E0V1EN (ssssi) ★

| | |
|---|---|
| Repo | https://github.com/ssssi/freqtrade_strs (`binance/dry_run/E0V1EN.py`) |
| Yıldız / son güncelleme | 651 / 2026-07-24 |
| Lisans | yok |
| Piyasa / zaman dilimi | Binance spot USDT; 5m |
| Yazar | ssssi (Çince freqtrade Discord topluluğu); doğrulanamadı |

**Mantık:** Kısa vadeli aşırı satım alımıdır. `buy_1`: RSI(20) düşüyor, RSI(4) < 40, RSI(14) > 42, kapanış SMA15'in 0,973 katının altında, CTI < 0,69 ve 24 saatlik değişim -%15 ile +%50 arasında. `buy_new` benzer şekilde sabit değerlerle (RSI4<34, RSI>28, SMA15*0,96) çalışır. Çıkışlar `custom_exit` içindedir: `buy_new` kârdayken fastk > 84 ise satış, kâr > -%3 iken CCI > 80 ise satış, 7 saat sonra kâr >= -%5 ise ve 10 saat sonra kâr >= -%10 ise zaman tabanlı çıkış. Ek olarak stoploss -%25, trailing (%3 sonrası %0,2) ve 96 mumluk cooldown koruması vardır.

**Güvenilirlik:** Kanıt olarak dry-run ekran görüntüleri ve README'deki bir Binance copy-trading bağlantısı (2026-07 başlangıçlı) sunuluyor; bunlar bağımsız olarak doğrulanamaz ve bağışçı/takipçi çekmeye yönelik bir pazarlama unsuru da taşır. 0,973 ve 0,69 gibi ondalık eşikler hyperopt çıktısıdır. -%25 stop ile çoğu çıkışın zaman tabanlı "kayıpla çık" kuralları olması, kazanç oranını yüksek, ortalama kaybı büyük gösterebilir.

**Çalıştırma:**
```
cp binance/dry_run/E0V1EN.py user_data/strategies/
freqtrade backtesting -c "binance/dry&live_config/config_usdt_spot.json" -s E0V1EN -t 5m --timerange 20240101-
```

---

### 17. DoubleEMACrossoverWithTrend (paulcpk) ★★

| | |
|---|---|
| Repo | https://github.com/paulcpk/freqtrade-strategies-that-work (`DoubleEMACrossoverWithTrend.py`) |
| Yıldız / son güncelleme | 330 / 2021-06-14 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Spot BTC, ETH, LTC, XRP, ADA, XLM, XMR, DASH /USDT; 1h |
| Yazar | Paul Csapak; profesyonel geçmişi doğrulanamadı |

**Mantık:** EMA9, EMA21'i yukarı kestiğinde ve mumun dibi EMA200'ün üzerindeyken long açılır. EMA9, EMA21'i aşağı kestiğinde veya mum dibi EMA200'ün altına düştüğünde çıkılır. Stoploss -%20'dir; trailing tanımlı ama kapalıdır (`trailing_stop = False`). ROI tablosu stratejide tanımlı değildir, config'ten gelir. Pozisyon büyüklüğü freqtrade config'indeki stake ayarına bırakılır.

**Güvenilirlik:** Yalnızca üç sabit, yaygın parametre içerir ve hyperopt yoktur; overfit riski düşüktür. Buna karşılık repo adı ("Strategies That Work") pazarlama tonundadır. Kanıt, 2018-03 ile 2020-03 arası tek bir in-sample backtest tablosudur (655 işlem, +%122,5); ücret varsayımı ve buy-and-hold karşılaştırması verilmiyor. Repo 2021'den beri güncellenmiyor ve eski `populate_buy_trend` arayüzünü kullanıyor.

**Çalıştırma:**
```
freqtrade download-data --timeframes 1h --timerange=20180301-20200301
freqtrade backtesting -s DoubleEMACrossoverWithTrend --timeframe 1h --timerange=20180301-20200301
```

---

### 18. IFR2 (RSI2 + Ichimoku, gabrielweich) ★★

| | |
|---|---|
| Repo | https://github.com/gabrielweich/jesse-strategies (`IFR2/__init__.py`) |
| Yıldız / son güncelleme | 28 / 2021-04-26 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Binance spot ADA, BAT, NEO, REEF, UNI /USDT; 1h (Jesse) |
| Yazar | Gabriel Weich; doğrulanamadı |

**Mantık:** Larry Connors'ın RSI2 ortalamaya dönüş kuralının uyarlamasıdır. RSI(2) < 10 olduğunda long açılır. Filtreler: kapanış kripto için uyarlanmış Ichimoku bulutunun (20/30/120/60) üzerinde olmalı ve Hilbert Transform trend modu 1 olmalıdır. Çıkış, kapanışın önceki iki mumun en yükseğinin üzerine çıkmasıdır. Tüm bakiye ile girilir ve stop yoktur.

**Güvenilirlik:** Kural seti az parametreli ve literatüre dayalıdır. Repodaki Jesse çıktıları ücretleri içeriyor (ör. ADA: 260 işlem, +%141, ödenen ücret 6.313 USDT, maksimum düşüş -%26,6). Zayıf yanlar: test dönemleri 2019 ile 2021-04 arası boğa piyasasıdır ve buy-and-hold ile karşılaştırılmıyor, REEF ve UNI sonuçları 2,7 ile 6 aylık çok kısa dönemlere dayanıyor, varlıklar sonuç görülerek seçilmiş olabilir ve stop olmaması tüm bakiyeyle girişte kuyruk riski yaratır.

**Çalıştırma:**
```
jesse import-candles 'Binance' 'ADA-USDT' '2019-01-01'
# routes.py: ('Binance', 'ADA-USDT', '1h', 'IFR2')
jesse backtest '2019-01-10' '2021-04-01'
```

---

### 19. Donchian kırılımı (gabrielweich) ★★

| | |
|---|---|
| Repo | https://github.com/gabrielweich/jesse-strategies (`Donchian/__init__.py`) |
| Yıldız / son güncelleme | 28 / 2021-04-26 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Binance spot BTC, ETH, ADA, BAT, NEO /USDT; 6h (Jesse) |
| Yazar | Gabriel Weich; doğrulanamadı |

**Mantık:** Kapanış önceki mumlardan hesaplanan Donchian üst bandının üzerine çıktığında long açılır (`self.candles[:-1]` ile mevcut mum hariç tutularak look-ahead önlenir). Filtre olarak kapanış SMA200 üzerinde olmalıdır. Çıkış, kapanışın Donchian alt bandının altına düşmesidir. Tüm bakiye ile girilir ve ayrı bir stop yoktur; alt bant fiilen trailing stop görevi görür.

**Güvenilirlik:** Klasik trend takip kuralıdır (Turtle'ın sadeleştirilmiş hali) ve neredeyse hiç ayarlanmış parametresi yoktur. Sonuç dosyaları ücret dahil Jesse çıktılarıdır (BTC: 2 yılda 18 işlem, +%452, maksimum düşüş -%46,9). Ancak her varlıkta 17 ile 24 işlem istatistiksel olarak çok azdır ve dönem 2021-04'te biten boğa piyasasıdır. Raporda zaten bulunan jesse-ai TurtleRules'tan farkı daha basit olması ve ek varlık sonuçları sunmasıdır.

**Çalıştırma:**
```
# routes.py: ('Binance', 'BTC-USDT', '6h', 'Donchian')
jesse backtest '2019-04-01' '2021-04-01'
```

---

### 20. OB5F_LSv2 (OTT bantları, ysdede) ★

| | |
|---|---|
| Repo | https://github.com/ysdede/jesse_strategies (`OB5F_LSv2/strategies/OB5F_LSv2/__init__.py`) |
| Yıldız / son güncelleme | 72 / 2022-06-06 |
| Lisans | CC0-1.0 |
| Piyasa / zaman dilimi | Binance Futures BTC-USDT, long ve short; 5m (Jesse) |
| Yazar | ysdede; doğrulanamadı |

**Mantık:** Anıl Özekşi'nin Optimized Trend Tracker (OTT) göstergesinin KAMA tabanlı sürümünü kullanır. Long: OTT ortalaması OTT'nin %1,35 üzerindeki üst bandı yukarı kestiğinde (`ott_len=70, ott_percent=1.70`). Short: KAMA(59) sinyal ortalaması alt bandı (%1,84 aşağısı) aşağı kestiğinde (`ott_len=31, ott_percent=3.33`). Stop, OTT çizgisinin kendisidir. Kâr al, %1, %2, %3, %5 ve %8 Fibonacci benzeri seviyelerde, hyperopt ile seçilmiş bir dağılım indeksine (`tps_qty_index`) göre kademeli yapılır. Pozisyon büyüklüğü sermayenin 1/10'udur; girişe ancak stop mesafesindeki risk `max_risk_long=5.2` / `max_risk_short=4.6` yüzdesinin altındaysa izin verilir. Ters OTT kesişiminde pozisyon tasfiye edilir.

**Güvenilirlik:** On bir hiperparametre Optuna NSGA-II ile tek bir varlık (BTC-USDT) üzerinde optimize edilmiştir ve README'ye göre optimizasyon sonuçları repodan çıkarılmıştır. Kanıt harici bir benchmark sayfasına bağlanıyor ve repo içinde örneklem dışı test yok. Borsa hassasiyet kuralları ve minimum miktar dikkate alınmış, bu da canlıya geçiş için olumlu bir mühendislik detayıdır.

**Çalıştırma:**
```
cd OB5F_LSv2
jesse import-candles 'Binance Futures' 'BTC-USDT' '2021-01-01'
jesse backtest '2021-01-01' '2022-05-01'
```

---

### 21. Sparta Weak Hands Buster (Superalgos) ★

| | |
|---|---|
| Repo | https://github.com/Superalgos/Algorithmic-Trading-Plugins (`Trading-Systems/Sparta-WHB-BTC-USDT.json`) |
| Yıldız / son güncelleme | 32 / 2024-04-23 (platform: Superalgos/Superalgos 5772 / 2026-11-03, Apache-2.0) |
| Lisans | yok (plugin reposu) |
| Piyasa / zaman dilimi | BTC/USDT spot short; 1h, 2h, 3h, 4h, 6h, 8h, 24h çoklu zaman dilimi |
| Yazar | Superalgos topluluğu; doğrulanamadı |

**Mantık:** Düşüş piyasası için short sistemidir. "Steep" stratejisinde giriş: 1h'de art arda üç kapanış Bollinger ortalamasının altında, kapanış alt bandın altında, 2h Bollinger kanalı aşağı yönlü, 1h sapma 200 ile 1000 USD arasında, mum boyu 750 USD'den küçük, birden çok zaman diliminde %B ortalaması 30'un üzerinde (tam aşırı satım değil). Stop, BB ortalamasının %4 veya %5,25 üzerinde takip eden bir seviyedir. Kâr hedefi, ortalamanın %85'i eksi 4 sapmadan alt banda kadar kademeli fazlarla (P1 ile P6) sıkılaştırılır. Kapanış ortalamanın üzerine çıkınca çıkılır.

**Güvenilirlik:** Mantık görsel JSON düğümleri içindeki JavaScript parçacıklarındadır (dosya yaklaşık 585 KB), denetlenmesi zordur. Eşikler mutlak dolar cinsindendir (sapma > 200, mum < 750, 8h sapma < 1575); bu, BTC'nin belirli bir fiyat düzeyine (2019-2020) göre ayarlandığını ve fiyat değiştikçe davranışın bozulacağını gösterir. Bu güçlü bir overfit/rejim bağımlılığı işaretidir. Yayınlanmış bağımsız bir sonuç yok.

**Çalıştırma:**
```
git clone https://github.com/Superalgos/Superalgos && cd Superalgos && node setup && node platform
# arayüzde Plugins > Algorithmic-Trading > Sparta-WHB-BTC-USDT yüklenip backtest oturumu başlatılır
```

---


## Hisse, ETF, varlık dağılımı ve opsiyon

### 22. Antonacci Global Equities Momentum (GEM, dual momentum) ★★★

| | |
|---|---|
| Repo | https://github.com/fbertram/TuringTrader (BooksAndPubs/Antonacci_DualMomentumInvesting.cs) |
| Yıldız / son güncelleme | 538 / 2026-05-19 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | ABD listeli ETF'ler (SPY, ACWX, BIL, AGG) / günlük veri, aylık işlem |
| Yazar | Kod: Felix Bertram, dosya başlığında "Bertram Enterprises LLC dba TuringTrader" olarak geçiyor; profesyonel geçmişi doğrulanamadı. Strateji: Gary Antonacci, "Dual Momentum Investing" kitabının yazarı. |

**Mantık:** Momentum `Close[0] / Close[252] - 1` olarak tanımlanmış, yani 12 aylık getiri. Her ayın son işlem gününde SPY, ACWX ve BIL arasından momentumu en yüksek olan seçiliyor (göreli momentum). Kazanan BIL çıkarsa, yani hisse momentumu T-bill'in altındaysa, bu pay güvenli varlık olan AGG'ye aktarılıyor (mutlak momentum). Portföy her zaman tek bir varlıkta yüzde 100 tutuluyor. Stop yok; risk kontrolünü yalnızca aylık rejim geçişi sağlıyor. Aynı dosyada Global Balanced, Parity Portfolio, Sektör Rotasyonu, 4 Pairs ve "Accelerating Dual Momentum" varyantları da var.

**Güvenilirlik:** Kitabın kuralları sadeliğini koruyarak uygulanmış. Hisse başına 0,015 USD komisyon (`Globals.COMMISSION`) her zaman düşülüyor. Optimize edilmiş bir sabit yok; tek parametre 12 aylık geri bakış ve o da kitaptan geliyor. Zayıf yanları: ACWX 2008'den önce yok ve simülasyon 2007'de başladığı için gerçek örneklem kısa. Antonacci'nin kitaptaki 1974'e uzanan sonuçları endeks verisiyle elde edildi. 12 aylık momentumun yayından (2014) sonraki performansı belirgin şekilde zayıfladı: 2018 ve 2020'deki V tipi dönüşlerde sinyal geç kaldı. Yalnızca 3 varlık ve tek pozisyon taşıdığı için sonuç birkaç geçiş kararına çok bağlı.

**Çalıştırma:** Yalnızca Windows'ta çalışır. https://www.turingtrader.org/download/ adresinden kurulum yapılır, `BooksAndPubs/BooksAndPubs.sln` Visual Studio ile derlenir ve TuringTrader arayüzünde `Antonacci_GlobalEquitiesMomentum` seçilir. Veri kaynağı olarak Norgate ya da Tiingo yapılandırılmalıdır.

---

### 23. Keller Defensive Asset Allocation (DAA, kanarya evreni) ★★

| | |
|---|---|
| Repo | https://github.com/fbertram/TuringTrader (BooksAndPubs/Keller_DAA.cs) |
| Yıldız / son güncelleme | 538 / 2026-05-19 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | ABD ETF'leri (G12: SPY, IWM, QQQ, VGK, EWJ, VWO, VNQ, GSG, GLD, TLT, HYG, LQD; korunma: SHY, IEF, LQD; kanarya: VWO, BND) / aylık |
| Yazar | Kod: Felix Bertram (doğrulanamadı). Strateji: Wouter J. Keller ve Jan Willem Keuning, SSRN 3212862 (2018). Keller'in Flex Capital ile bağı yaygın olarak biliniyor, ancak burada ayrıca doğrulanmadı. |

**Mantık:** Her varlık için 13612W momentumu hesaplanıyor: `12*(p0/p1-1) + 4*(p0/p3-1) + 2*(p0/p6-1) + (p0/p12-1)`, aylık barlarla. Kanarya evrenindeki (VWO, BND) negatif momentumlu varlık sayısı `b`'den nakit oranı türetiliyor: `CF = min(1, floor(b*T/B)/T)`. Bu, makaledeki "Easy Trading" sürümü. G12 için T=6 ve B=2. Riskli kısım momentumu en yüksek `t = round((1-CF)*T)` varlığa eşit ağırlıkla dağıtılıyor. Nakit kısmı ise korunma evreninde momentumu en yüksek tek varlığa gidiyor. Aylık yeniden dengeleme yapılıyor. G4, G6, DAA1 ve kaldıraçlı (L2X, L3X, E2X) varyantlar da dosyada mevcut.

**Güvenilirlik:** Makaleye sadık bir uygulama ve komisyon dahil. Ancak T, B ve kanarya seçimi Keller'in kendi örneklem içi (in-sample) optimizasyonunun ürünü. Makalede birçok evren ve parametre denendiği açıkça yazıyor, dolayısıyla veri madenciliği (data mining) riski yüksek. 13612W ağırlıkları kısa vadeye çok ağırlık verdiği için portföy devri (turnover) yüksek. Kaldıraçlı "on steroids" varyantları kaldıraçlı ETF'lerin gerçek geçmişinden daha uzun bir dönem için sentetik seri gerektiriyor. Yayından sonraki gerçek performans, özellikle 2022'de tahvil korumasının da düştüğü dönemde, makaledeki geriye dönük testten daha zayıf kaldı.

**Çalıştırma:** Antonacci girişindeki adımlarla aynı. Arayüzde `Keller_DAA_G12` ya da `Keller_DAA_G4` seçilir.

---

### 24. Connors kısa vadeli ETF ortalamaya dönüş setleri (RSI2/R3, RSI 25/75, 3 gün düşük-yüksek) ★★

| | |
|---|---|
| Repo | https://github.com/fbertram/TuringTrader (BooksAndPubs/Connors_HighProbEtfTrading.cs; ayrıca Connors_ShortTermTrading.cs) |
| Yıldız / son güncelleme | 538 / 2026-05-19 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | SPY (varsayılan, başka ETF verilebilir) / günlük |
| Yazar | Kod: Felix Bertram (doğrulanamadı). Strateji: Larry Connors ve Cesar Alvarez, "High Probability ETF Trading" (2009). |

**Mantık:** Her setin ortak bir trend filtresi var: Close > SMA200 iken yalnızca long, altında iken yalnızca short. *R3:* RSI(2) üç gün üst üste düşmüş olmalı, üç gün önceki RSI(2) < 60 ve bugünkü RSI(2) < 10 olmalı. Bu durumda long açılıyor ve RSI(2) > 70 olunca çıkılıyor. Short tarafı simetrik (100 eksi eşik). *RSI 25/75:* RSI(4) < 25 iken long, RSI(4) > 55 olunca çıkış. *3 gün düşük-yüksek:* üç gün üst üste düşen tepe ve dip görülürse long, Close > SMA5 olunca çıkış. `AGGRESSIVE_ON=1` ayarı fiyat girişin altına inerse ikinci bir yarım pozisyon ekliyor (ortalama düşürme). Stop-loss yok, bu Connors'un kitabındaki tercih. Pozisyon büyüklüğü sermayenin yüzde 100'ü, agresif modda iki kez yüzde 50.

**Güvenilirlik:** Eşikler `[OptimizerParam]` ile işaretli ve optimize edilebilir aralıklar tanımlı (örneğin `ENTRY_MAX_RSI_0_LONG` için 5-30). Varsayılan değerler kitaptan alınmış olsa da kitabın kendisi 1993-2008 verisi üzerinde parametre taraması yapıyordu. Emirler `OrderType.closeThisBar` ile veriliyor: sinyal aynı barın kapanışıyla hesaplanıp aynı kapanıştan işleniyor. Bu, kapanışa yakın tahmin edip MOC emri verilebileceği varsayımına dayanıyor ve hafif iyimser. Komisyon dahil, kayma (slippage) yok. Stop olmaması nedeniyle 2008 ya da 2020 gibi sert düşüşlerde ortalama düşürme modu büyük kayıplar verir. SPY'da RSI2 tipi kısa vadeli dönüş etkisi 2010 sonrasında da büyük ölçüde sürdü, ancak getirinin önemli kısmı tek tük büyük günlerden geliyor.

**Çalıştırma:** TuringTrader kurulumu ve `BooksAndPubs.sln` derlemesi gerekir; arayüzde `Connors_HighProbEtfTrading_R3` seçilir.

---

### 25. Clenow "Stocks on the Move" (volatiliteye göre ayarlanmış hisse momentumu) ★★

| | |
|---|---|
| Repo | https://github.com/fbertram/TuringTrader (BooksAndPubs/Clenow_StocksOnTheMove.cs, v2 sürümü BooksAndPubsV2 altında) |
| Yıldız / son güncelleme | 538 / 2026-05-19 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | S&P 500 bileşenleri (nokta zamanlı, point-in-time) / günlük veri, haftalık işlem (çarşamba) |
| Yazar | Kod: Felix Bertram (doğrulanamadı). Strateji: Andreas F. Clenow, "Stocks on the Move" (2015). Clenow fon yöneticisi olarak tanınan bir yazar, bu çalışmada bağımsız olarak doğrulanmadı. |

**Mantık:** Sıralama ölçütü, 90 günlük log-fiyat regresyonunun yıllıklaştırılmış eğimi ile R²'nin çarpımı. Bileşenlerin ilk yüzde 20'si alınıyor. Fiyatı SMA100'ün altında olan ya da 90 gün içinde yüzde 15'ten büyük tek günlük hareket yapmış hisseler eleniyor. Pozisyon büyüklüğü ATR ile belirleniyor: `ağırlık = 0,001 / ATR20 * Close`, yani hisse başına 10 baz puan günlük risk. Para bitene kadar sıralamaya göre dolduruluyor. Endeks filtresi olarak S&P 500'ün SMA10 > SMA200 olması gerekiyor; filtre negatifse yeni giriş yapılmıyor, mevcut pozisyonlar küçültülerek tutuluyor. Emirler `openNextBar`, yani ertesi açılışta işleniyor.

**Güvenilirlik:** `GlueLogic.cs` içinde `USE_NORGATE_UNIVERSE` varsayılan olarak tanımlı, yani hayatta kalma yanlılığı (survivorship bias) olmayan nokta zamanlı S&P 500 üyeliği kullanılıyor. Yorumda bu bayrak kapatılırsa "ağır survivorship bias" oluşacağı açıkça yazıyor. Look-ahead yok ve komisyon dahil. Yazar koda iki "FIXME" bırakmış (eğim çarpı R² hesabının kitapla birebir uyumu ve maxMove birimi), yani uygulamanın kitaba tam uyduğundan kendisi de emin değil. Endeks SMA10 filtresi kitapta yok ve sonradan eklenmiş. Hisse momentumu 2009 ve 2020 gibi sert toparlanmalarda büyük düşüş (momentum crash) yaşar.

**Çalıştırma:** TuringTrader kurulumu gerekir. Nokta zamanlı evren için ücretli Norgate Data aboneliği şarttır. Arayüzde `Clenow_StocksOnTheMove` seçilir.

---

### 26. Varlık dağılımı paketi: Faber GTAA, Ivy, Keller VAA/DAA/PAA, Kipnis KDA (pyTAA) ★★

| | |
|---|---|
| Repo | https://github.com/oronimbus/tactical-asset-allocation (src/pytaa/strategy, src/pytaa/backtest/positions.py) |
| Yıldız / son güncelleme | 55 / 2024-12-23 |
| Lisans | MIT |
| Piyasa / zaman dilimi | ABD ETF'leri / aylık (BME, iş günü ay sonu) |
| Yazar | GitHub kullanıcısı oronimbus; gerçek kimliği ve geçmişi doğrulanamadı. |

**Mantık:** Kural seti `strategy/README.md` dosyasında tek tek yazılı ve `signals.py` ile `positions.py` dosyalarında kodlanmış. *GTAA (Faber):* 13 ETF sabit ağırlıklı; ay sonunda fiyat 10 aylık SMA'nın üstündeyse varlık tutuluyor, değilse o pay nakde geçiyor. *Ivy:* VTI, VEU, VNQ, AGG ve DBC eşit ağırlıklı, aynı 10 aylık SMA kuralıyla. *VAA G12:* 13612W skoru negatif olan varlık sayısı `n` ise güvenli paya `min(1, 0,25*n)` ayrılıyor, kalanı en iyi 5 riskli varlığa eşit dağıtılıyor (`vigilant_allocation`, top_k=5, step=0,25). *Kipnis KDA:* kanarya varlıklar (EEM, AGG) üzerinden minimum varyans ağırlıklandırma yapılıyor. Stop yok; risk kontrolü trend ve kanarya kurallarıyla sağlanıyor.

**Güvenilirlik:** README'deki Sharpe ve maksimum düşüş rakamları (örneğin VAA için SR 1, MDD yüzde 10) bu kodun çıktısı değil, orijinal makalelerden ya da bir Twitter derlemesinden (WifeyAlpha) alınmış. Paket README'de "WIP" olarak işaretli. Backtest modülünde komisyon ya da kayma modeli bulunamadı, yani maliyetsiz. Aylık sinyal `resample("BME").last()` ile ay sonu kapanışından alınıyor; işlemin aynı kapanıştan mı ertesi günden mi yapıldığı ağırlık kaydırma koduna bağlı ve açıkça belgelenmemiş. Keller stratejilerindeki örneklem içi parametre seçimi riski burada da geçerli. Avantajı, onlarca TAA kuralını tek ve okunabilir Python kod tabanında karşılaştırabilmesi.

**Çalıştırma:** `pip install pytaa` ya da repo içinde `pip install -e .`, ardından `notebooks/Main.ipynb`. Veri yfinance ile çekiliyor.

---

### 27. Varlık sınıfı momentum rotasyonu (Faber tipi 5 ETF) ★★

| | |
|---|---|
| Repo | https://github.com/paperswithbacktest/awesome-systematic-trading (static/strategies/asset-class-momentum-rotational-system.py) |
| Yıldız / son güncelleme | 15200 / 2026-09-28 |
| Lisans | yok |
| Piyasa / zaman dilimi | SPY, EFA, IEF, VNQ, GSG / aylık |
| Yazar | Kod Quantpedia'nın QuantConnect uygulaması; dosyada quantpedia.com bağlantısı var. Kodun tek tek yazarları belirtilmemiş, doğrulanamadı. |

**Mantık:** 252 günlük ROC hesaplanıyor. Her ayın ilk işlem gününde momentumu en yüksek 3 ETF seçiliyor ve her birine 1/3 ağırlık veriliyor. Listeden düşen varlık tamamen satılıyor. Mutlak momentum ya da nakit filtresi yok; 5 varlığın hepsi düşüşteyse de en az kötü 3'ü tutuluyor. Stop yok.

**Güvenilirlik:** Fikir Faber'ın 2010 tarihli "Relative Strength Strategies for Investing" çalışmasından geliyor. Kod kısa ve okunaklı, look-ahead görülmedi (ROC ay başında önceki kapanışa göre hesaplanıyor). Komisyon modeli olarak QuantConnect'in varsayılan IB modeli geçerli, kayma ise yok. Mutlak momentum filtresinin olmaması 2008 ve 2022 gibi her şeyin birlikte düştüğü yıllarda koruma sağlamıyor. Repo README'si, Sharpe değerlerinin "maliyetler düşülmeden" ve "her stratejinin kendi penceresinde" ölçüldüğünü, ayrıca kataloğun yarısının t > 1,96 eşiğini geçemediğini kendisi belirtiyor. Bu dürüst bir uyarı.

**Çalıştırma:** QuantConnect bulutunda yeni bir Python projesi oluşturup dosyayı `main.py` olarak yapıştırmak ya da yerelde `pip install lean`, `lean init`, `lean project-create` ve `lean backtest <proje>` adımlarını izlemek yeterli.

---

### 28. Zaman serisi momentumu (TSMOM, Moskowitz-Ooi-Pedersen) ★★

| | |
|---|---|
| Repo | https://github.com/paperswithbacktest/awesome-systematic-trading (static/strategies/time-series-momentum-effect.py) |
| Yıldız / son güncelleme | 15200 / 2026-09-28 |
| Lisans | yok |
| Piyasa / zaman dilimi | Yaklaşık 60 vadeli işlem sözleşmesi (emtia, döviz, hisse endeksi, tahvil), sürekli geri ayarlı seri / aylık |
| Yazar | Quantpedia uygulaması (doğrulanamadı). Strateji: Moskowitz, Ooi ve Pedersen, Journal of Financial Economics (2012). |

**Mantık:** Ayda bir kez her sözleşmenin 12 aylık (252 gün) getirisine bakılıyor; pozitifse long, negatifse short. Long ve short bacaklar ayrı ayrı 60 günlük tarihsel volatilitenin tersiyle ağırlıklandırılıyor. Ardından her bacak yüzde 10 yıllık volatilite hedefine ölçekleniyor ve kaldıraç en fazla 4 ile sınırlanıyor. Son verisi 5 günden eski olan sözleşmeler dışarıda bırakılıyor. Stop yok.

**Güvenilirlik:** Makaledeki GARCH yerine basit tarihsel volatilite kullanılıyor ve bu değişiklik dosyada açıkça not edilmiş. Makale risksiz faizin üstündeki getiriyi kullanırken kod ham getiriyi kullanıyor. Kodda bir hata var: `"LIFFE_R1"` satırından sonra virgül unutulmuş, bu yüzden Python bu dizgeyi bir sonraki `"MX_CGB1"` ile birleştiriyor. Sonuçta Long Gilt ve Kanada 10 yıllık tahvili evrenden sessizce düşüyor. Veri `data.quantpedia.com` adresinden özel bir sınıfla çekiliyor; erişim garantisi yok. Komisyon notional'ın 0,5 baz puanı, roll maliyeti ve kayma yok. TSMOM'un 2012 sonrasındaki performansı yayın dönemine göre belirgin şekilde zayıfladı (2012-2019 düz bir dönem), 2022'de ise güçlü döndü.

**Çalıştırma:** QuantConnect bulutunda Python projesi; Quantpedia veri adresine erişim gerekir. Yerelde `lean backtest` çalışır, ancak özel veri indirmesi engellenebilir.

---

### 29. Ay dönümü etkisi (turn-of-the-month, SPY) ★★

| | |
|---|---|
| Repo | https://github.com/paperswithbacktest/awesome-systematic-trading (static/strategies/turn-of-the-month-in-equity-indexes.py) |
| Yıldız / son güncelleme | 15200 / 2026-09-28 |
| Lisans | yok |
| Piyasa / zaman dilimi | SPY / günlük |
| Yazar | Quantpedia uygulaması (doğrulanamadı). Etki: Ariel (1987), Lakonishok ve Smidt (1988). |

**Mantık:** Ayın son işlem gününde piyasa açılışından hemen sonra sermayenin yüzde 100'üyle SPY alınıyor. Yeni ayın ilk işlem gününde bir bayrak kalkıyor ve sayaç başlıyor; üçüncü `OnData` çağrısında, yani yaklaşık 3. işlem gününde pozisyon kapatılıyor. Ayda yaklaşık 4 gün piyasada kalınıyor, kalan sürede nakitte bekleniyor. Stop yok.

**Güvenilirlik:** Kural son derece basit ve optimize edilecek parametre neredeyse yok. Ancak dosyanın kendi yorumu "bazı makaleler 4 gün diyor" diye yazıyor, yani giriş ve çıkış günü tercihi esnek ve seçim yanlılığına açık. Giriş ay sonu kapanışından değil açılışından yapılıyor. Bu, makalelerdeki "son günün getirisini de dahil et" tanımıyla uyumlu ama zamanlama farkı sonucu etkileyebilir. Komisyon QuantConnect varsayılanı. Etki literatürde ABD'de onlarca yıl gözlendi; ancak 2000 sonrası çalışmalarda genliğinin azaldığı ve kısmen emeklilik fonu akışlarına bağlı olduğu ileri sürülüyor. Nakitte geçen günlerde faiz getirisi modellenmiyor.

**Çalıştırma:** QuantConnect bulutu ya da `lean backtest`. Veri QuantConnect'in kendi SPY verisi olduğu için ek gereksinim yok.

---

### 30. Volatilite risk primi: korumalı kısa straddle (SPY opsiyonları) ★

| | |
|---|---|
| Repo | https://github.com/paperswithbacktest/awesome-systematic-trading (static/strategies/volatility-risk-premium-effect.py) |
| Yıldız / son güncelleme | 15200 / 2026-09-28 |
| Lisans | yok |
| Piyasa / zaman dilimi | SPY ve SPY opsiyonları / dakikalık veri, aylık döngü |
| Yazar | Quantpedia uygulaması (doğrulanamadı). |

**Mantık:** Portföy boşken vadesi 30 güne en yakın seri seçiliyor. Bu seride ATM call ve ATM put satılıyor, aynı adette yaklaşık yüzde 15 OTM put alınıyor (kuyruk koruması). Ayrıca sermayenin yüzde 100'üyle SPY alınıyor. Adet `MarginRemaining / (fiyat * 100)` ile belirleniyor ve opsiyon marj modeli 5x kaldıraca ayarlanıyor. Vade sonunda opsiyonlar düşüp yalnızca SPY kaldığında SPY satılıyor ve döngü yeniden başlıyor. Erken kapanış, kâr al ya da stop kuralı yok; pozisyon vadeye kadar tutuluyor.

**Güvenilirlik:** Zayıf. Uygulama dosya başındaki tanımdan sapıyor: tanımda "kalan nakit endekse yatırılır" denirken kod ayrıca yüzde 100 SPY alıyor ve buna 5x kaldıraçlı kısa straddle ekliyor. Böylece fiili risk iki kattan fazla. ATM straddle'ın vadede fiziki teslimle (assignment) sonuçlanması büyük hisse pozisyonları doğurur ve kod bunu ayrıca yönetmiyor. Dakikalık opsiyon verisi 2010'dan başladığı için örneklem kısa. Kısa volatilite stratejilerinin getirisi 2018 Şubat ve 2020 Mart gibi olaylarda birkaç günde silinebilir; yüzde 15 OTM put yalnızca kısmi koruma sağlar. Volatilite primi etkisinin kendisi akademik olarak sağlam, ancak bu kod onun iyi bir uygulaması değil.

**Çalıştırma:** QuantConnect bulutu tavsiye edilir, çünkü dakikalık opsiyon verisi yerelde ücretli. Komut: `lean cloud backtest <proje>`.

---

### 31. Kısa put ve 16 delta iron condor (optopsy) ★★

| | |
|---|---|
| Repo | https://github.com/goldspanlabs/optopsy (eski adres michaelchu/optopsy; docs/examples.md ve optopsy/exits.py) |
| Yıldız / son güncelleme | 1512 / 2026-11-04 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | Hisse ve endeks opsiyonları (SPX, SPY vb.) / günlük opsiyon zinciri |
| Yazar | Michael Chu; şu an goldspanlabs organizasyonu altında. Profesyonel geçmişi doğrulanamadı. |

**Mantık:** optopsy bir kütüphane, ancak hazır strateji fonksiyonları ve belgelenmiş parametre setleri içeriyor. *Kısa put (cash-secured put):* `op.short_puts(data, max_entry_dte=45, exit_dte=0, stop_loss=-1.0, take_profit=0.50)`. 45 gün veya daha az vadeli put satılıyor; prim yüzde 50 kazanılınca kapatılıyor, kayıp primin yüzde 100'üne ulaşınca stop çalışıyor, aksi halde vadeye kadar tutuluyor. *Iron condor:* `op.iron_condor(data, max_entry_dte=45, exit_dte=21, leg2_delta=0,16, leg3_delta=0,16)`. Kısa bacaklar 16 delta civarında (0,15-0,20 aralığı) seçiliyor ve vadeye 21 gün kala çıkılıyor. `exits.py` dosyasında stop, kâr al ve azami tutma süresi önceliği stop > kâr al > süre şeklinde kodlanmış. Covered call, collar, takvim ve kelebek gibi yapılar da mevcut.

**Güvenilirlik:** Kayma modelleri (`mid`, `spread`, `liquidity`, `per_leg`) ve komisyon (`Commission(per_contract=0.65, base_fee=4.95)`) desteği var. `core.py` içinde varsayılan kayma `slippage="spread"`, yani alış-satış farkından işlem; bu olumlu bir varsayılan. Komisyonun varsayılanı ise `None`, yani kullanıcı belirtmezse komisyon düşülmüyor. Çıktı ilk olarak DTE ve delta aralıklarına göre gruplanmış ortalama getiri tablosu veriyor. Örnek kod `results[results['mean'] > 0.20]` diye "en iyi DTE aralığını" seçiyor; bu doğrudan örneklem içi seçim ve overfit'e davet. Veri kullanıcıdan geliyor (CSV ya da ücretli EODHD), dolayısıyla veri kalitesi ve hayatta kalma yanlılığı kullanıcının sorumluluğunda. Kısa opsiyon getirilerinin sol kuyruk riski (2020 Mart) ortalama tablolarında gizlenebilir.

**Çalıştırma:** `pip install optopsy`, ardından Python içinde `import optopsy as op; data = op.csv_data("SPX_2023.csv"); op.short_puts(data, max_entry_dte=45, take_profit=0.5, stop_loss=-1.0, commission=0.65, slippage="spread", raw=True)`.

---

### 32. SteadyOptions "Anchor Trade" (LEAP call, uzun put koruması ve aylık put satışı) ★

| | |
|---|---|
| Repo | https://github.com/fbertram/TuringTrader (BooksAndPubs/SteadyOptions_AnchorTrade.cs) |
| Yıldız / son güncelleme | 538 / 2026-05-19 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | SPX, XSP ya da SPY opsiyonları / günlük |
| Yazar | Kod: Felix Bertram (doğrulanamadı). Strateji: dosyaya göre Chris Welsh, steadyoptions.com üzerinde yayımlanmış; doğrulanamadı. |

**Mantık:** 1) Yaklaşık 396 gün (365+31) vadeli, 0,90 deltalı derin ITM call alınıyor (ana pozisyon; `MAIN_W = 170`, yani net varlık değerinin yüzde 170'i kadar dayanak tutarına denk gelen lot). 2) Yaklaşık 1 yıl vadeli, kullanım fiyatı spotun yüzde 92'si civarında put alınıyor ve ana pozisyonu tam korumaya yetecek adette tutuluyor. Spot yükseldikçe, put kullanım fiyatı spotun yüzde 86'sının altına düşerse koruma yukarı kaydırılıyor (roll). 3) Gelir bacağı olarak yaklaşık 14 gün vadeli put satılıyor ve kâr hedefi `INCOME_POS_PT = 65` (yüzde 65) dolunca roll ediliyor. 4) Kalan nakit BIL'e yatırılıyor. Hedeflenen toplam kaldıraç yaklaşık yüzde 150.

**Güvenilirlik:** Varsayılan derleme bayrağı `#define FAKE_OPTIONS`. Bu durumda opsiyon fiyatları gerçek kotasyonlar değil, `$SPX.fake.options` adlı sentetik bir veri setinden geliyor; bu nedenle varsayılan backtest gerçek alış-satış farklarını ve volatilite yüzeyini yansıtmıyor. Gerçek veri (SPX haftalık, XSP, SPY) seçenekleri yorum satırında kapalı. Parametreler (92, 86, 120, 65) kodda yorum satırına alınmış eski değerlerle birlikte duruyor (`//95`, `//90`), yani elle ayarlanmışlar. Strateji bir forum gönderisinden kodlanmış ve yayımlanmış bağımsız bir performans kaydı bulunamadı. Uzun delta ile kısa put, düşüşte aynı yöne kaybeder; korumanın etkinliği roll zamanlamasına çok bağlı.

**Çalıştırma:** TuringTrader kurulumu gerekir; gerçek opsiyon verisi için `FAKE_OPTIONS` kapatılıp `SPX_OPTIONS` açılmalı ve ücretli bir tarihsel opsiyon verisi sağlanmalıdır.

---

### 33. Küresel ülke ETF'lerinde IBS ortalamaya dönüşü ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (Algorithm.Python/Alphas/GlobalEquityMeanReversionIBSAlpha.py) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | 32 ülke ve bölge ETF'i (EWJ, EWZ, FXI, SPY, QQQ vb.) / günlük |
| Yazar | QuantConnect ekibi, "Benchmark Alpha" serisi. Kurumsal kaynak; tek tek yazarlar belirtilmemiş. |

**Mantık:** Her gün her ETF için Internal Bar Strength hesaplanıyor: `IBS = (Close - Low) / (High - Low)`. IBS'si en yüksek 2 ETF için "aşağı" (short), en düşük 2 ETF için "yukarı" (long) içgörüsü üretiliyor ve süre 1 gün. Portföy eşit ağırlıklı ve stop yok (`NullRiskManagementModel`).

**Güvenilirlik:** Zayıf. `ConstantFeeModel(0)` ile işlem ücreti sıfıra ayarlanmış. Her gün 4 pozisyon değiştiren bir strateji için bu ciddi bir iyimserlik ve ülke ETF'lerinde spread de yüksek. Ticker listesinde EWM üç kez geçiyor; RSX ise 2022'de işlemden kaldırıldı. Başlangıç 2018. Sinyal günün kapanışında hesaplanıyor ve işlem ancak ertesi gün yapılabiliyor; IBS etkisinin büyük kısmı ise kapanıştan ertesi açılışa kadar olan aralıkta yoğunlaşıyor. Kod bir çerçeve (framework) örneği olarak yazılmış, performans iddiası yok.

**Çalıştırma:** `pip install lean`, `lean init`, ardından dosya bir projeye `main.py` olarak kopyalanıp `lean backtest <proje>` çalıştırılır. Gerçekçi bir test için `set_fee_model` satırı kaldırılmalıdır.

---

### 34. Greenblatt "Magic Formula" (QuantConnect uygulaması) ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (Algorithm.Python/Alphas/GreenblattMagicFormulaAlpha.py) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | ABD hisseleri (dolar hacmine göre ilk 500) / aylık evren, günlük veri |
| Yazar | QuantConnect ekibi. Strateji: Joel Greenblatt, "The Little Book That Beats the Market". |

**Mantık:** Ayda bir dolar hacmine göre ilk 500 hisse alınıyor. NYSE ya da NASDAQ'ta işlem gören, en az 180 günlük ve piyasa değeri 500 milyon USD'den büyük ABD şirketleri sektör şablonuna göre orantılı örnekleniyor. Sonra EV/EBITDA ve forward ROA'ya göre sıralanıp 10 hisse seçiliyor, eşit ağırlıklı long. Stop yok ve ücret sıfır.

**Güvenilirlik:** Kodda sıralama hatası var: `sorted(..., key=ev_to_ebitda, reverse=True)` en yüksek EV/EBITDA'yı, yani en pahalı hisseleri öne alıyor. Ardından `forward_roa` için `reverse=False` en düşük karlılığı seçiyor. Bu, Greenblatt'ın "ucuz ve kaliteli" kuralının tam tersi. Ayrıca formüldeki sermaye getirisi (ROC) yerine forward ROA ve kazanç getirisi yerine EV/EBITDA kullanılmış. Ücret sıfır. Bu dosya Magic Formula'nın sınanması için kullanılmamalı; yalnızca bir başlangıç iskeleti olarak, sıralama yönleri düzeltilerek kullanılabilir.

**Çalıştırma:** `lean backtest`. Temel (fundamental) veri QuantConnect bulutunda ücretsiz, yerelde ise ücretli. Önce iki `sorted` çağrısındaki yönler düzeltilmelidir.

---

### 35. 3x kaldıraçlı ETF çifti volatilite aşınması (UGLD/DGLD) ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (Algorithm.Python/Alphas/TripleLeverageETFPairVolatilityDecayAlpha.py) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | UGLD ve DGLD (3x long ve 3x short altın ETN'leri) / günlük |
| Yazar | QuantConnect ekibi. |

**Mantık:** Her gün iki kaldıraçlı ürünün ikisi için de "aşağı" içgörüsü üretiliyor ve eşit ağırlıkla ikisi birden açığa satılıyor. Fikir, günlük yeniden dengelenen kaldıraçlı ürünlerin yatay ve oynak piyasada değer kaybetmesi (volatility decay). Gün sonunda yeniden dengeleniyor ve stop yok.

**Güvenilirlik:** Zayıf. Ücret sıfır ve açığa satış ödünç maliyeti (borrow fee) modellenmiyor; kaldıraçlı ürünlerde bu maliyet yıllık yüzde 5-20'ye çıkabiliyor ve stratejinin teorik kârının büyük kısmını yer. UGLD ve DGLD, Credit Suisse'in VelocityShares ETN'leri olarak 2020'de işlemden kaldırıldı (delisting), bu yüzden strateji bugün bu enstrümanlarla çalıştırılamaz. Güçlü tek yönlü trendlerde kısa bacaklardan biri sınırsız kayıp üretebilir. Başlangıç 2018, örneklem çok kısa.

**Çalıştırma:** `lean backtest`. Güncel kullanım için UGL/GLL ya da TQQQ/SQQQ gibi yaşayan çiftlerle ve borrow maliyeti eklenerek yeniden yazılmalıdır.

---

### 36. Dual Thrust (açılış etrafında aralık kırılımı) ★

| | |
|---|---|
| Repo | https://github.com/letianzj/QuantResearch (backtest/dual_thrust.py; benzeri https://github.com/je-suis-tm/quant-trading içinde "Dual Thrust backtest.py") |
| Yıldız / son güncelleme | 3059 / 2023-08-26 |
| Lisans | MIT |
| Piyasa / zaman dilimi | SPX endeksi (vadeli işlem stratejisi olarak tasarlanmış) / günlük |
| Yazar | Letian Wang (GitHub letianzj); profesyonel geçmişi doğrulanamadı. Strateji Michael Chalek'e atfediliyor. |

**Mantık:** Son n=4 günün HH, HC, LC ve LL değerlerinden `range = max(HH-LC, HC-LL)` hesaplanıyor. Üst tetik `Open + k1*range`, alt tetik `Open - k2*range` (k1=k2=0,5). Kapanış üst tetiğin üstündeyse sermayenin tamamıyla long, alt tetiğin altındaysa tamamıyla short açılıyor ve ters sinyalde pozisyon çevriliyor (always-in-the-market). Stop yok.

**Güvenilirlik:** Look-ahead var: `df_hist.High.iloc[-self.n:]` aralığına bugünün barı da dahil, yani tetik seviyesi bugünün tepe ve dibi bilinerek hesaplanıyor. je-suis-tm sürümünde de aynı sorun var: `intraday['range'][date]` o günün 3:00-12:00 tepe-dibini içeren rolling değerden geliyor. Dosyada n, k1 ve k2 için paralel parametre taraması kodu hazır. Buna rağmen README'de yazarın kendi raporladığı Sharpe -0,10 ve bu dürüst bir sonuç. Endeks (SPX) doğrudan işlem görmüyor. Look-ahead'e rağmen negatif sonuç, kuralın günlük barda değersiz olduğuna işaret ediyor; strateji aslında gün içi Çin vadelilerinde popüler.

**Çalıştırma:** `pip install quanttrader pyfolio empyrical`, önce `python backtest/hist_downloader.py --sym SPX` ile veri indirilir, sonra `cd backtest && python dual_thrust.py` çalıştırılır.

---

### 37. R-Breaker (pivot destek ve direnç, tersine dönüş ve kırılım) ★

| | |
|---|---|
| Repo | https://github.com/letianzj/QuantResearch (backtest/r_breaker.py) |
| Yıldız / son güncelleme | 3059 / 2023-08-26 |
| Lisans | MIT |
| Piyasa / zaman dilimi | SPX endeksi (aslen emtia vadelileri için gün içi strateji) / günlük |
| Yazar | Letian Wang (doğrulanamadı). Strateji Richard Saidenberg'e (1994) atfediliyor. |

**Mantık:** Dünün H, L ve C değerlerinden pivot `P = (H+L+C)/3` ve altı seviye hesaplanıyor (R1-R3, S1-S3). Pozisyon yokken kapanış R3'ün üstündeyse long, S3'ün altındaysa short açılıyor (kırılım). Long iken bugünün tepesi R2'yi aştıysa ve kapanış R1'in altındaysa ya da kapanış S3'ün altındaysa pozisyon short'a çevriliyor (tersine dönüş). Short taraf simetrik. Sermayenin tamamı kullanılıyor. `stop_loss_price = 10` tanımlı ama kodda hiç kullanılmıyor.

**Güvenilirlik:** Dosya başlığında stratejinin "Futures Truth dergisinde 15 yıl üst üste en kârlı 10 strateji arasında" olduğu iddiası var. Bu bir pazarlama iddiası ve doğrulanamadı. Yazar, gün içi strateji günlük kapanışla test edildiği için "performansın kötüleşmesi beklenir" diye kendisi not düşmüş. Bugünün tepesi ve kapanışı aynı barda karşılaştırılıyor, sıralama belirsiz. README'de raporlanan Sharpe 0,15. Maliyet modeli belirtilmemiş.

**Çalıştırma:** `pip install quanttrader pyfolio empyrical ta-lib`, veri `hist_downloader.py` ile indirilir, sonra `cd backtest && python r_breaker.py` çalıştırılır.

---

### 38. Heikin-Ashi mum momentum ve dönüş sinyali ★

| | |
|---|---|
| Repo | https://github.com/je-suis-tm/quant-trading ("Heikin-Ashi backtest.py") |
| Yıldız / son güncelleme | 11206 / 2026-06-20 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | NVDA (tek hisse, yfinance) / günlük |
| Yazar | GitHub kullanıcısı je-suis-tm; README'de Londra'da yaşadığını belirtiyor, profesyonel geçmişi doğrulanamadı. |

**Mantık:** HA kapanış `(O+H+L+C)/4`, HA açılış önceki HA açılış ve HA kapanışın ortalaması. Al sinyali: HA açılış > HA kapanış (düşüş mumu), HA açılış = HA tepe (üst fitil yok), gövde bir önceki günden büyük ve önceki mum da düşüş mumu. Yani kod pratikte güçlenen bir düşüşte alıyor. Sat sinyali: iki ardışık yükseliş mumu ve HA açılış = HA dip; bu durumda tüm pozisyon kapatılıyor. Pozisyon ekleme `stls=3` ile en fazla 3 lot (her biri 100 hisse) ile sınırlı; açığa satış yok.

**Güvenilirlik:** Zayıf. Test tek bir hissede ve tek bir dönemde yapılmış (NVDA, 2015-04 ile 2018-02, NVDA'nın yaklaşık 10 kat yükseldiği dönem); bu açık bir seçim yanlılığı. Komisyon ve kayma yok. Sinyal kapanışta üretilip aynı kapanıştan işleniyor. Sharpe hesabında risksiz faiz yerine S&P 500 getirisi kullanılıyor, bu standart bir tanım değil. Kod eğitim amaçlı ve README'de de böyle sunuluyor.

**Çalıştırma:** `pip install yfinance pandas scipy matplotlib`, ardından `python "Heikin-Ashi backtest.py"`.

---

### 39. Kointegrasyon tabanlı çift işlemi (Engle-Granger) ★

| | |
|---|---|
| Repo | https://github.com/je-suis-tm/quant-trading ("Pair trading backtest.py") |
| Yıldız / son güncelleme | 11206 / 2026-06-20 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | NVDA ve AMD (2013-2014) / günlük |
| Yazar | je-suis-tm (doğrulanamadı). |

**Mantık:** 250 günlük kayan pencerede Engle-Granger iki adım testi uygulanıyor: OLS artığına ADF testi (p < 0,05) ve hata düzeltme katsayısının negatif olması. Kointegrasyon başladığı anda artık standartlaştırılıyor ve o günkü z değeri ± artık standart sapması bant olarak sabitleniyor. z üst bandın üstündeyse varlık 1 long, varlık 2 short; alt bandın altındaysa tersi. Kointegrasyon kaybolursa pozisyon kapatılıyor. Stop yok.

**Güvenilirlik:** Zayıf. `portfolio()` fonksiyonunda pozisyon büyüklüğü `capital0 // max(data['asset1'])` ile hesaplanıyor; tüm dönemin en yüksek fiyatı kullanıldığı için bu bir look-ahead. Bant tanımı da tutarsız: z değerine artığın ham standart sapması ekleniyor, birimler karışık. Tek çift ve iki yıllık veri var. Maliyet ve ödünç alma ücreti yok. Kavramı öğretmek için iyi, işlem için uygun değil.

**Çalıştırma:** `pip install yfinance statsmodels pandas matplotlib`, ardından `python "Pair trading backtest.py"`.

---


## İstatistiksel arbitraj ve ML/RL

### 40. Deep Learning Statistical Arbitrage (CNN+Transformer, PCA/IPCA artıkları) ★★★

| | |
|---|---|
| Repo | https://github.com/gregzanotti/dlsa-public (`run_train_test.py`, `train_test.py`, `factor_models/pca.py`, `models/CNNTransformer.py`) |
| Yıldız / son güncelleme | 281 / 2022-10-05 |
| Lisans | Özel lisans (GitHub "NOASSERTION"); BSD benzeri metin, ancak ticari kullanım açıkça yasak |
| Piyasa / zaman dilimi | ABD hisseleri (CRSP evreni, piyasa değeri filtresi), günlük |
| Yazar | Jorge Guijarro-Ordonez (Stanford, Matematik), Markus Pelger ve Greg Zanotti (Stanford, Management Science & Engineering); kurumlar arXiv 2106.04028 makalesinin ilk sayfasından doğrulandı |

**Mantık:** Önce her hisse için faktör artıkları üretilir: Avellaneda-Lee tarzı yerel PCA (252 günlük korelasyon penceresi, 60 günlük regresyon penceresi), Fama-French ya da IPCA. Bu adım `OOSRollingWindowPermnos` ile her gün yalnızca geçmiş veriyle yapılır. Son 30 günlük kümülatif artık serisi bir CNN+Transformer ağına verilir; ağ her artık portföy için bir ağırlık üretir. Ağırlıklar mutlak toplamı 1 olacak şekilde normalize edilir (L1), yani pozisyon büyüklüğü dolar-nötr ve kaldıraç 1'dir. Ayrı bir giriş/çıkış eşiği yoktur; her gün yeniden ağırlıklandırılır. Amaç fonksiyonu doğrudan Sharpe oranıdır. Karşılaştırma için klasik OU s-skoru modeli (`OUFFN`) de repoda bulunur.

**Güvenilirlik:** Hakemli akademik çalışmanın resmi kodu. Model 1000 günlük kayan pencerede eğitilip her 125 günde bir yeniden eğitiliyor (`rolling_retrain: True`), yani yapı walk-forward. Zayıf yanlar: makaledeki manşet sonuç (IPCA ile örneklem dışı Sharpe yaklaşık 4,2) işlem maliyetsiz; makale maliyetli sonucu ayrı bir sağlamlık bölümünde veriyor. Varsayılan konfigürasyonda da `market_frictions: False`, `trans_cost: 0`. Sabit tek seed (`random_seed=0`) kullanılıyor. Ham CRSP verisi lisans nedeniyle paylaşılmıyor; repoda hazır artık dosyaları var, ancak makaleyi birebir üretmek için gereken `use_residual_weights: True` ayarı artık kompozisyon matrislerini (`OOSMatrixresiduals`) istiyor ve bu dosyalar repoda yok. Sharpe'ı 4'ün üzerinde olan bir stratejiye maliyet eklenmeden güvenilmemeli.

**Çalıştırma:**
```bash
git clone https://github.com/gregzanotti/dlsa-public && cd dlsa-public
pip install -r requirements.txt
# Paylaşılan artıklarla çalıştırmak için configs/*.yaml içinde use_residual_weights: False yapın
# ve maliyet için market_frictions: True, trans_cost: 0.0005 girin
python3 run_train_test.py -c configs/cnntransformer-full.yaml
```

---

### 41. Qlib LightGBM + Alpha158 + TopkDropout ★★

| | |
|---|---|
| Repo | https://github.com/microsoft/qlib (`examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`, `qlib/contrib/strategy/signal_strategy.py`) |
| Yıldız / son güncelleme | 50076 / 2026-11-04 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Çin A hisseleri (CSI300, CSI500 varyantı da var), günlük |
| Yazar | Microsoft (Qlib ekibi) |

**Mantık:** Alpha158 el yapımı 158 teknik özelliği hesaplar; etiket iki günlük ileri getiridir. LightGBM (MSE kaybı) her hisse için getiri tahmini üretir. `TopkDropoutStrategy` tahmine göre ilk 50 hisseyi tutar ve her gün en kötü sıradaki 5 tanesini değiştirir (`topk: 50`, `n_drop: 5`), bu da devir hızını sınırlar. Pozisyonlar eşit ağırlıklıdır, sermayenin yüzde 95'i yatırılır (`risk_degree`). Yalnızca long tarafı vardır; sonuç CSI300'e karşı fazla getiri olarak raporlanır. Yüzde 9,5 tavan/taban limitine takılan hisselerde işlem yapılmaz.

**Güvenilirlik:** Kronolojik ayrım net: eğitim 2008-2014, doğrulama 2015-2016, test 2017-2020/08. Maliyet modeli var (alış yüzde 0,05, satış yüzde 0,15, minimum 5 CNY). README'deki CSI300 sonuçları: IC 0,0448, yıllık fazla getiri yüzde 9,0, bilgi oranı 1,02. Zayıf yanlar: tek bir sabit test penceresi (yeniden eğitim yok, walk-forward için `examples/rolling_process_data` ve `benchmarks_dynamic` ayrıca kurulmalı); hiperparametreler (`lambda_l1: 205.6999` gibi) ayarlanmış görünüyor ve hangi veriyle ayarlandığı belgelenmemiş; test dönemi 2020'de bitiyor ve README yeni sonuç vermiyor. Qlib README'sine göre resmi veri seti şu an kapalı, topluluk veri seti (chenditc/investment_data) öneriliyor; bu veri setinin kalitesi ayrıca doğrulanmalı.

**Çalıştırma:**
```bash
pip install pyqlib
wget https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
mkdir -p ~/.qlib/qlib_data/cn_data && tar -zxvf qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
cd qlib/examples/benchmarks/LightGBM && pip install -r requirements.txt
qrun workflow_config_lightgbm_Alpha158.yaml
```

---

### 42. Qlib DoubleEnsemble (LightGBM topluluğu) ★★

| | |
|---|---|
| Repo | https://github.com/microsoft/qlib (`examples/benchmarks/DoubleEnsemble/workflow_config_doubleensemble_Alpha158.yaml`) |
| Yıldız / son güncelleme | 50076 / 2026-11-04 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Çin A hisseleri (CSI300), günlük |
| Yazar | Qlib README'si yöntemi Chuheng Zhang ve arkadaşlarına atfediyor; yazarların kurumu doğrulanamadı |

**Mantık:** Taban model LightGBM'dir. DoubleEnsemble ardışık 3 alt model eğitir (`num_models: 3`); her turda eğitim kaybı eğrisine göre örnekleri yeniden ağırlıklandırır (`enable_sr`, `bins_sr: 10`) ve özellik karıştırma ile önemsiz özellikleri eler (`enable_fs`, `bins_fs: 5`). Tahminlerin ortalaması alınır. Portföy kuralı LightGBM girişiyle aynıdır: TopkDropout (50 hisse, günde 5 değişim), aynı maliyetler.

**Güvenilirlik:** Aynı kronolojik eğitim/doğrulama/test ayrımı ve maliyet modeli. README'de CSI300 Alpha158 için yıllık fazla getiri yüzde 11,6, bilgi oranı 1,34 (birden fazla tekrarın ortalaması ve sapması verilmiş, bu artı). Dikkat çekici bir uyarı işareti: aynı README'de CSI500 sonucu yıllık yüzde 3,8 getiri, bilgi oranı 0,17 ve yüzde 48,8 maksimum düşüş gösteriyor. Yani CSI300'deki üstünlük evrene genellenmiyor ve CSI300 sonucu muhtemelen o evrene uyumlu. Tek test penceresi ve yeniden eğitim yokluğu burada da geçerli.

**Çalıştırma:**
```bash
cd qlib/examples/benchmarks/DoubleEnsemble && pip install -r requirements.txt
qrun workflow_config_doubleensemble_Alpha158.yaml
# Birden fazla tekrar için: cd ../../ && python run_all_model.py run 5 doubleensemble Alpha158 csi300
```

---

### 43. Qlib TRA (Temporal Routing Adaptor, rejim yönlendirmeli LSTM) ★★

| | |
|---|---|
| Repo | https://github.com/microsoft/qlib (`examples/benchmarks/TRA/workflow_config_tra_Alpha158.yaml`, `qlib/contrib/model/pytorch_tra.py`) |
| Yıldız / son güncelleme | 50076 / 2026-11-04 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Çin A hisseleri (CSI300), günlük |
| Yazar | Qlib README'si yöntemi Hengxu Lin ve arkadaşlarına atfediyor; yazarların kurumu doğrulanamadı |

**Mantık:** LSTM tabanlı bir gövde üzerinde 3 ayrı tahmin başlığı vardır (`num_states: 3`); bir yönlendirici her örneği gizli piyasa "rejimlerinden" birine atar ve atama optimal transport ile dengelenir. Etiket iki günlük ileri getirinin kesitsel sıralamasıdır (`CSRankNorm`). Portföy kuralı yine TopkDropout (50 hisse, günde 5 değişim), aynı maliyetlerle.

**Güvenilirlik:** Kronolojik test ve maliyet var; README sonuçları beş tekrardan ortalama ve sapmayla verilmiş (Alpha158 için yıllık fazla getiri yüzde 7,2 artı eksi 2, bilgi oranı 1,08 artı eksi 0,35). Sapmanın büyük olması seed'e duyarlılığı gösteriyor. Sızıntı riski: varsayılan konfigürasyon 20 özellikle çalışıyor ve README bu özelliklerin "LightGBM tabanlı bir modelin özellik önemine göre" seçildiğini söylüyor; seçimin hangi dönemde yapıldığı belirtilmemiş. Test dönemini de içeren veriyle seçildiyse bu bir ileri bakış sızıntısıdır. Konfigürasyonda `eval_test: True` var; bu eğitim sırasında test metriklerini de hesaplatıyor, erken durdurma doğrulama setine bağlı olsa da sonuçları izlerken test setine bakma eğilimini kolaylaştırıyor.

**Çalıştırma:**
```bash
cd qlib/examples/benchmarks/TRA && pip install -r requirements.txt
qrun workflow_config_tra_Alpha158.yaml
```

---

### 44. Momentum Transformer (Oxford-Man, vadeli işlemlerde derin momentum) ★★★

| | |
|---|---|
| Repo | https://github.com/kieranjwood/trading-momentum-transformer (`examples/run_dmn_experiment.py`, `mom_trans/momentum_transformer.py`, `mom_trans/backtest.py`) |
| Yıldız / son güncelleme | 644 / 2026-03-19 |
| Lisans | MIT |
| Piyasa / zaman dilimi | 100 sürekli vadeli kontrat (emtia, endeks, tahvil, döviz), günlük |
| Yazar | Kieran Wood, Stephen Roberts, Stefan Zohren (Oxford-Man Institute of Quantitative Finance, University of Oxford) ve Sven Giegerich (Oxford Internet Institute); kurumlar arXiv 2112.08534 makalesinin ilk sayfasından doğrulandı |

**Mantık:** Temporal Fusion Transformer bileşenlerinden kurulu bir dikkat (attention) ağı, normalize getiriler, MACD göstergeleri ve isteğe bağlı değişim noktası (CPD) özelliklerinden her varlık için -1 ile +1 arasında bir pozisyon üretir. Kayıp fonksiyonu doğrudan Sharpe oranıdır. Pozisyonlar volatilite hedefiyle ölçeklenir (`VOL_TARGET`), yani her varlık benzer riske sahip olur. Ayrı bir eşik ya da stop yoktur; pozisyon her gün güncellenir. `TFT`, `TFT-CPD-126-21`, `TFT-SHORT` gibi deney adlarıyla farklı varyantlar seçilir.

**Güvenilirlik:** Akademik ve hakemli çizgide bir çalışma. Genişleyen pencereli walk-forward var: her test yılı için model yalnızca o yıldan önceki veriyle yeniden eğitiliyor; eğitim/doğrulama ayrımı kronolojik (yüzde 90/10, ticker bazında zaman sırasına göre). Deney birden fazla tekrarla (`num_repeats`) çalıştırılıyor ve hiperparametreler rastgele arama ile yalnızca doğrulama setinde seçiliyor. Zayıf yanlar: maliyet eğitim kaybına dahil değil, yalnızca sonradan 0,5 ile 3 baz puan arası uygulanıyor (makale de bunu açıkça yazıyor); README'deki "Sample results" bölümü hâlâ "yakında" diyor, yani repoda hazır sonuç yok. Kullanılan ücretsiz Quandl/Nasdaq Data Link CHRIS sürekli vadeli veri setine bugün erişilip erişilemediği doğrulanamadı.

**Çalıştırma:**
```bash
git clone https://github.com/kieranjwood/trading-momentum-transformer && cd trading-momentum-transformer
pip install -r requirements.txt
python -m data.download_quandl_data <API_KEY>
python -m examples.concurent_cpd_quandl 21 && python -m examples.concurent_cpd_quandl 126
python -m examples.create_features_quandl 126 21
python -m examples.run_dmn_experiment TFT-CPD-126-21
```

---

### 45. Slow Momentum with Fast Reversion (LSTM Deep Momentum Network + değişim noktası tespiti) ★★

| | |
|---|---|
| Repo | https://github.com/kieranjwood/trading-momentum-transformer (`LSTM`, `LSTM-CPD-21`, `LSTM-CPD-63` deneyleri, `mom_trans/changepoint_detection.py`); yalnızca CPD modülünü içeren eski repo: https://github.com/kieranjwood/slow-momentum-fast-reversion |
| Yıldız / son güncelleme | 644 / 2026-03-19 (eski repo: 278 / 2026-03-19) |
| Lisans | MIT |
| Piyasa / zaman dilimi | 100 sürekli vadeli kontrat, günlük |
| Yazar | Kieran Wood, Stephen Roberts, Stefan Zohren; Journal of Financial Data Science 4(1), 2022. Aynı ekibin Oxford-Man bağlantısı Momentum Transformer makalesinden doğrulandı; bu makalenin kendi künyesi ayrıca kontrol edilmedi |

**Mantık:** Lim, Zohren ve Roberts'ın Deep Momentum Network fikri: 63 günlük girdiyle çalışan bir LSTM, getiri ve MACD özelliklerinden doğrudan pozisyon üretir ve Sharpe oranını maksimize eder. Bu varyant, Gauss süreci tabanlı bir değişim noktası tespit modülünün çıktısını (değişim noktası şiddeti ve konumu) ek özellik olarak ekler. Böylece ağ, rejim kırılmalarında yavaş momentumdan hızlı ters dönüşe geçmeyi öğrenir. Pozisyon büyüklüğü volatilite hedefiyle ölçeklenir.

**Güvenilirlik:** Momentum Transformer ile aynı walk-forward, tekrar ve maliyet altyapısını kullanır. CPD her pencere için yalnızca geçmiş gözlemlerle hesaplanıyor, bu doğru. Zayıf yanlar aynı: maliyet sonradan ekleniyor, eğitimde yok; repoda hazır sonuç yok. Eski `slow-momentum-fast-reversion` reposu tek başına çalıştırılabilir bir strateji değil, yalnızca CPD modülünü içeriyor; tam strateji Momentum Transformer reposunda. CPD hesaplaması 100 varlıkta oldukça yavaş.

**Çalıştırma:**
```bash
cd trading-momentum-transformer
python -m examples.concurent_cpd_quandl 21
python -m examples.create_features_quandl 21
python -m examples.run_dmn_experiment LSTM-CPD-21
```

---

### 46. FinRL Ensemble Stock Trading (A2C/PPO/DDPG) ★

| | |
|---|---|
| Repo | https://github.com/AI4Finance-Foundation/FinRL (`finrl/applications/stock_trading/ensemble_stock_trading.py`, `finrl/agents/stablebaselines3/models.py`, `examples/FinRL_Ensemble_StockTrading_ICAIF_2020.ipynb`) |
| Yıldız / son güncelleme | 17006 / 2026-11-03 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Dow 30 hisseleri, günlük |
| Yazar | AI4Finance Foundation; ICAIF 2020 makalesine dayanıyor, yazarların kurumu bu çalışmada doğrulanmadı |

**Mantık:** Teknik göstergeler ve türbülans endeksinden oluşan durum vektörüyle üç ayrı ajan (A2C, PPO, DDPG) eğitilir. Her 63 günde bir tüm ajanlar yeniden eğitilir, son 63 günlük doğrulama penceresinde Sharpe oranı en yüksek olan ajan sonraki 63 gün işlem yapar. Aksiyon hisse başına en fazla 100 adetlik alım/satımdır (`hmax: 100`). Türbülans örneklem içi 90. yüzdelik dilimi aşınca tüm pozisyonlar satılır. Maliyet her yön için yüzde 0,1.

**Güvenilirlik:** Olumlu yanlar: 63 günlük yeniden eğitimle kayan walk-forward ve maliyet modeli var. Overfit ve sızıntı işaretleri belirgin: her ajan yalnızca 10.000 adım eğitiliyor (`timesteps_dict`), bu RL için çok az ve sonuçlar seed'e aşırı duyarlı; seed sabitlenmiyor (`seed=None`) ve birden fazla seed raporlanmıyor. Ajan seçimi doğrulama Sharpe'ına göre yapılıyor, bu da 3 aday arasından seçim sapması ekliyor. Ortam, durumu ve işlemi aynı günün kapanış fiyatıyla kuruyor; yani sinyal gördüğün kapanıştan işlem yapıldığı varsayılıyor, bu iyimser bir dolum varsayımı. Evren bugünkü Dow 30 olduğu için hayatta kalma sapması var. Projenin tanıtım dili iddialı; yayınlanmış sonuçlar tek koşu ve bağımsız tekrarlanmamış.

**Çalıştırma:**
```bash
git clone https://github.com/AI4Finance-Foundation/FinRL && cd FinRL
pip install -e .
python -m finrl.applications.stock_trading.ensemble_stock_trading
```

---

### 47. FinRL EIIE Portföy Optimizasyonu (Jiang ve ark. policy gradient) ★

| | |
|---|---|
| Repo | https://github.com/AI4Finance-Foundation/FinRL (`examples/FinRL_PortfolioOptimizationEnv_Demo.ipynb`, `finrl/agents/portfolio_optimization/`, `finrl/meta/env_portfolio_optimization/`) |
| Yıldız / son güncelleme | 17006 / 2026-11-03 |
| Lisans | MIT |
| Piyasa / zaman dilimi | Brezilya hisseleri (örnek defterde `TOP_BRL`), günlük |
| Yazar | AI4Finance Foundation katkıcıları; mimari Jiang ve arkadaşlarının EIIE makalesinden |

**Mantık:** EIIE (Ensemble of Identical Independent Evaluators) her varlığa aynı küçük CNN'i uygulayıp 50 günlük fiyat penceresinden portföy ağırlıkları üretir (nakit dahil, toplam 1, yalnızca long). Policy gradient doğrudan portföy değerini maksimize eder; replay buffer'dan ardışık batch'ler örneklenir. Her adımda ağırlıklar yeniden dengelenir ve işlem maliyeti yüzde 0,25'tir (`comission_fee_pct=0.0025`). Eğitim 2011-2019, test 2020, 2021 ve 2022 yıllarında ayrı ayrı yapılır ve al-tut ile kıyaslanır.

**Güvenilirlik:** Maliyet var ve test yılları ayrı tutulmuş, bu iyi. Ancak açık bir veri sızıntısı var: `GroupByScaler(by="tic", scaler=MaxAbsScaler)` eğitim/test ayrımından önce 2011-2022 verisinin tamamına uygulanıyor; yani her hissenin ölçeklemesi gelecekteki maksimum fiyatı biliyor. Bu, girdilerde ileri bakışa yol açar ve düzeltilmeden sonuçlar güvenilmez. Tek seed, 40 episode ve tek koşu raporlanıyor. Evren bugünkü büyük Brezilya hisseleri olduğundan hayatta kalma sapması var.

**Çalıştırma:**
```bash
pip install git+https://github.com/AI4Finance-Foundation/FinRL.git
jupyter notebook examples/FinRL_PortfolioOptimizationEnv_Demo.ipynb
# Önce ölçekleyiciyi yalnızca eğitim dönemine fit edecek şekilde düzeltin
```

---

### 48. FinRL-Trading ML Hisse Seçimi (sektör kovası bazlı Random Forest/LightGBM/XGBoost) ★★

| | |
|---|---|
| Repo | https://github.com/AI4Finance-Foundation/FinRL-Trading (`src/strategies/ml_strategy.py`, `src/strategies/ml_bucket_selection.py`, `ML_STOCK_SELECTION.md`) |
| Yıldız / son güncelleme | 3911 / 2026-09-18 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | S&P 500 hisseleri, çeyreklik yeniden dengeleme |
| Yazar | AI4Finance Foundation |

**Mantık:** 52 temel (bilanço/gelir tablosu/oran) faktörden, her sektör kovası (growth_tech, cyclical, real_assets, defensive) için ayrı modellerle bir sonraki çeyreğin log getirisi tahmin edilir. Aday modeller (RF, GBM, isteğe bağlı LightGBM ve XGBoost) son 4 çeyreklik doğrulama penceresinde karşılaştırılır ve en iyisi seçilir. En yüksek tahminli hisseler eşit ağırlık ya da minimum varyans ağırlıklarıyla alınır, hisse başına risk limitleri uygulanır. Yalnızca long.

**Güvenilirlik:** Belgeler sızıntıya karşı bilinçli: etiket, raporun kamuya açık olduğu varsayılan işlem tarihinden (çeyrek sonu artı 2 ay) bir sonraki işlem tarihine kadar ölçülüyor ve endeks üyeliği o tarihteki tarihsel S&P 500 listesine göre kuruluyor (point-in-time, hayatta kalma sapmasını azaltır). Eğitim kayan ya da genişleyen çeyreklik pencereyle yapılıyor. Backtest motoru varsayılan olarak işlem başına yüzde 0,1 maliyet uyguluyor. Zayıf yanlar: README'deki rakamlar pazarlama tonunda; özellikle 5 aylık kâğıt işlem dönemi için "yıllık yüzde 62, Sharpe 1,96" iddiası istatistiksel olarak anlamsız uzunlukta. 2018-2025 backtest'inde Sharpe 0,93 ile QQQ'nun 0,81'ine yakın ve volatilite daha yüksek; getirinin büyük kısmı teknoloji betası olabilir. "2 ay sonra rapor açıktır" varsayımı kaba bir kural (gerçek açıklama tarihi kullanılmıyor). Her çeyrek birden fazla model arasından seçim yapılması ek seçim sapması getirir. Veri için ücretli FMP API anahtarı gerekiyor.

**Çalıştırma:**
```bash
git clone https://github.com/AI4Finance-Foundation/FinRL-Trading && cd FinRL-Trading
pip install -r requirements.txt
echo "FMP_API_KEY=..." > .env
python3 src/data/fetch_and_store_fundamentals.py
python3 src/data/backfill_historical_sp500.py
python3 src/strategies/ml_bucket_selection.py   # tarih argümanları için ML_STOCK_SELECTION.md'ye bakın
```

---

### 49. FreqaiExampleStrategy (LightGBM regresyonu, kripto) ★

| | |
|---|---|
| Repo | https://github.com/freqtrade/freqtrade (`freqtrade/templates/FreqaiExampleStrategy.py`, `config_examples/config_freqai.example.json`) |
| Yıldız / son güncelleme | 56562 / 2026-11-05 |
| Lisans | GPL-3.0 |
| Piyasa / zaman dilimi | Binance kripto (spot ya da vadeli), 3 dakikalık mumlar (5m/15m/4h ek zaman dilimleri) |
| Yazar | Freqtrade/FreqAI geliştiricileri |

**Mantık:** RSI, MFI, ADX, SMA, Bollinger gibi göstergeler birden fazla periyot, zaman dilimi ve korele parite için çoğaltılarak yüzlerce özellik üretilir. Hedef, sonraki 20 mumun ortalama kapanışının bugünkü kapanışa oranıdır (`label_period_candles: 20`). Model (varsayılan LightGBMRegressor) son 15 günle eğitilir ve her 7 günde yeniden eğitilir. Tahmin yüzde 1'in üzerindeyse long, yüzde -1'in altındaysa short açılır; tahmin işaret değiştirince çıkılır. Dissimilarity Index ve SVM ile "tanıdık olmayan" veri noktalarında işlem yapılmaz (`do_predict`). Stop yüzde 5, ROI yüzde 10 ve 240 dakika sonra zorunlu çıkış. Pozisyon başına sabit 200 USDT.

**Güvenilirlik:** FreqAI'nin altyapısı kayan pencereyle yeniden eğitim yaptığı için yapı walk-forward; backtest'te borsa ücreti uygulanır. Ancak bu bir şablon, kârlı strateji iddiası yok ve hiçbir performans kanıtı sunulmuyor. Hedef `shift(-20)` ile geleceğe bakıyor; bu tasarım gereği doğru, fakat özellik mühendisliğinde kullanıcı hatası kolay, bu yüzden `freqtrade lookahead-analysis` komutuyla kontrol edilmeli. 15 günlük eğitim penceresi ve 3 dakikalık mumlarla aşırı uyum riski yüksek.

**Çalıştırma:**
```bash
pip install -e ".[freqai]"
freqtrade create-userdir --userdir user_data
freqtrade download-data -c config_examples/config_freqai.example.json --timerange 20240101-20240601 -t 3m 5m 15m 4h
freqtrade backtesting -c config_examples/config_freqai.example.json --strategy FreqaiExampleStrategy \
  --strategy-path freqtrade/templates --freqaimodel LightGBMRegressor --timerange 20240301-20240601
```

---

### 50. Litmus MLDP: FreqAI üzerinde meta-labeling ve triple-barrier ★

| | |
|---|---|
| Repo | https://github.com/markdregan/FreqAI-Marcos-Lopez-De-Prado (dal `litmus-ai`; `user_data/strategies/LitmusMLDPStrategy.py`, `user_data/freqaimodels/LitmusMLDPClassifier.py`, `freqtrade/litmus/`) |
| Yıldız / son güncelleme | 88 / 2024-04-15 |
| Lisans | GPL-3.0 (freqtrade çatalı) |
| Piyasa / zaman dilimi | Kripto vadeli (Binance), 5 dakikalık mumlar |
| Yazar | GitHub kullanıcısı markdregan; kimliği ve kurumu doğrulanamadı |

**Mantık:** Lopez de Prado'nun "Advances in Financial Machine Learning" kitabındaki fikirleri FreqAI'ye taşır. Birincil sinyal (ör. kapanışın Bollinger alt bandının altına inmesi) ve ZigZag tabanlı birincil hedefler üretilir. İkincil (meta) model, birincil sinyalin triple-barrier yöntemine göre üst bariyere mi alt bariyere mi önce değeceğini sınıflandırır; birincil modelin geçmiş başarısı da meta modele özellik olarak verilir. İşleme yalnızca meta modelin olasılığı eşiği aşınca girilir. Long ve short açılabilir, özel stoploss ve ROI tablosu var. Özellik seçimi için SHAP-RFECV, zaman serisi çapraz doğrulaması için `tscv` kullanılıyor.

**Güvenilirlik:** Teknik olarak meta-labeling'in az sayıdaki çalıştırılabilir açık uygulamalarından biri ve sınıflandırıcıda zaman sırasına duyarlı CV var. Ancak repo sahibi README'de projenin artık geliştirilmediğini söylüyor; hiçbir backtest sonucu ya da kanıt yok. Repoda onlarca "Untitled" defter ve `deprecated` klasörü var, yani deneysel bir çalışma alanı. ZigZag hedefleri tanımı gereği geleceğe bakıyor; bunlar yalnızca hedef olarak kullanılmalı ve özelliklere sızmadığı tek tek kontrol edilmeli. Repoda `config.exchange_secret.json` ve `tokens.txt` dosyaları commit edilmiş (içerikleri açılmadı); bu da özensiz bir depo düzenine işaret ediyor. Eski bir freqtrade çatalı olduğu için güncel freqtrade ile uyumlu değil.

**Çalıştırma:**
```bash
git clone -b litmus-ai https://github.com/markdregan/FreqAI-Marcos-Lopez-De-Prado && cd FreqAI-Marcos-Lopez-De-Prado
pip install -e . && pip install -r requirements-freqai.txt -r requirements-litmus.txt
freqtrade backtesting -c user_data/strategies/config.LitmusMLDP.json --strategy LitmusMLDPStrategy \
  --freqaimodel LitmusMLDPClassifier --timerange 20230101-20230301
```

---

### 51. NautilusTrader Hurst/VPIN Directional (dolar barları, mikroyapı) ★

| | |
|---|---|
| Repo | https://github.com/nautechsystems/nautilus_trader (`crates/trading/src/examples/strategies/hurst_vpin_directional/`, `crates/adapters/kraken/examples/engine_hurst_vpin_backtest.rs`) |
| Yıldız / son güncelleme | 31311 / 2026-11-06 |
| Lisans | LGPL-3.0 |
| Piyasa / zaman dilimi | Kraken Futures `PF_XBTUSD`, dolar barları (2.000.000 USD notional) ve tick verisi |
| Yazar | Nautech Systems |

**Mantık:** Lopez de Prado'nun dolar barları üzerinde iki istatistik hesaplanır. Hurst üssü, son 128 dolar barının log getirilerinden rescaled-range yöntemiyle tahmin edilir; 0,55'in üzeri "trend rejimi" sayılır. VPIN, son 50 kovadaki alış/satış agresör hacim dengesizliğinin mutlak ortalamasıdır; 0,30'un üzeri "bilgili akış" sayılır. Pozisyon yokken Hurst trend gösteriyor ve VPIN eşiği aşıyorsa, imzalı dengesizlik yönünde IOC piyasa emri gönderilir. Hurst 0,50'nin altına inince ya da 3600 saniyelik azami tutma süresi dolunca çıkılır. Pozisyon büyüklüğü sabit (`trade_size`).

**Güvenilirlik:** Olay güdümlü, tick seviyesinde gerçekçi bir motor; backtest örneği maker yüzde 0,02, taker yüzde 0,05 ücret modeli içeriyor ve strateji için birim testler var. Ancak bu bir motor örneği: parametreler gerekçelendirilmemiş, örnek veri tek gün (Tardis'in her ayın ilk günü ücretsiz verisi), performans iddiası ya da örneklem dışı çalışma yok. IOC piyasa emirleri sürekli taker ücreti ve spread ödediği için kârlılığı belirsiz. İstatistiksel bir rejim filtresi olarak öğretici, alfa kanıtı olarak değil. ML modeli yok, istatistiksel sinyal tabanlı.

**Çalıştırma:**
```bash
git clone https://github.com/nautechsystems/nautilus_trader && cd nautilus_trader
# Tardis'ten PF_XBTUSD trade ve quote CSV'lerini /tmp/tardis_kraken/ altına indirin (dosya başındaki yorumlara bakın)
cargo run -p nautilus-kraken --features examples --example kraken-hurst-vpin-backtest --release
```

---

### 52. PyBroker Walk-Forward ML Örneği (CMMA + doğrusal regresyon) ★

| | |
|---|---|
| Repo | https://github.com/edtechre/pybroker (`docs/source/notebooks/6. Training a Model.ipynb`, ayrıca `16. Time Series Models` ve `17. Multi-Symbol Models`) |
| Yıldız / son güncelleme | 3674 / 2026-11-02 |
| Lisans | Apache-2.0 artı Commons Clause (GitHub "NOASSERTION"; ticari satış kısıtlı) |
| Piyasa / zaman dilimi | ABD hisseleri (örnekte NVDA, AMD), günlük, Yahoo Finance |
| Yazar | edtechre (PyBroker geliştiricisi); kimliği doğrulanamadı |

**Mantık:** Özellik, kapanışın son 20 günlük ortalamadan farkıdır (CMMA). Doğrusal regresyon bu özellikten ertesi günün getirisini tahmin eder. Tahmin pozitifse 100 adet alınır, pozisyondayken tahmin negatife dönerse satılır. Yalnızca long, sabit adet.

**Güvenilirlik:** Değerli tarafı altyapı: `strategy.walkforward(windows=3, train_size=0.5, lookahead=1)` ile eğitim ve test pencereleri arasında boşluk bırakan walk-forward yapılıyor ve bootstrap ile Sharpe/profit factor güven aralıkları ile drawdown güven aralıkları hesaplanıyor. Strateji ise öğretici bir oyuncak: iki hisse ve sonradan seçilmiş (NVDA, AMD) bir dönem, varsayılan ayarlarda komisyon yok, tek özellik. Seçilen hisseler örneklem döneminde güçlü yükselmiş olduğundan long-only sonuç büyük ölçüde betadır. Kendi stratejinizi walk-forward ve bootstrap ile sınamak için iyi bir iskelet.

**Çalıştırma:**
```bash
pip install lib-pybroker scikit-learn
jupyter notebook "docs/source/notebooks/6. Training a Model.ipynb"
# Maliyet için StrategyConfig(fee_mode=FeeMode.ORDER_PERCENT, fee_amount=0.1) ekleyin
```

---

### 53. ML4T 3. Baskı: ETF Vaka Çalışması (LightGBM/LSTM kesitsel sıralama) ★★

| | |
|---|---|
| Repo | https://github.com/stefan-jansen/machine-learning-for-trading (`case_studies/etfs/`, özellikle `07_gbm.py`, `14_backtest.py`, `17_costs.py`, `18_holdout_predictions.py`, `19_holdout_backtest.py`, `config/setup.yaml`) |
| Yıldız / son güncelleme | 21737 / 2026-11-06 |
| Lisans | MIT |
| Piyasa / zaman dilimi | 100 çok varlıklı ABD ETF'i, günlük veri, aylık yeniden dengeleme |
| Yazar | Stefan Jansen ("Machine Learning for Trading", 3. baskı) |

**Mantık:** Teknik, makro ve model tabanlı özelliklerden 21 günlük ileri getiri tahmin edilir (5 günlük varyant da var). Doğrusal modeller, LightGBM, LSTM, TSMixer, PCA/IPCA ve otomatik kodlayıcı gibi birçok model aynı hattan geçer. Ay sonunda tahmine göre ilk k ETF (5, 10 ya da 20) eşit ağırlıkla alınır, emir ertesi barın açılışında gerçekleşir. Sonraki defterler tahsis yöntemlerini (minimum varyans vb.), trailing stop ve zaman bazlı çıkış gibi risk katmanlarını ekler. Yalnızca long.

**Güvenilirlik:** Bu listedeki metodolojik olarak en disiplinli hatlardan biri: 10 yıllık eğitim ve 1 yıllık doğrulamayla 8 katlı walk-forward, etiket ufku kadar boşluk (`buffer: 21D`), 2024-2025 için dokunulmamış bir holdout dönemi, hisse başına 0,0035 USD komisyon artı ETF'e özgü yarım spread, ve maliyet duyarlılık defteri ("kenar hangi maliyette yok oluyor?"). Kendi kendini eleştiren notlar da var: yapılandırma dosyası 100 ETF'in geriye dönük seçildiğini ve bu yüzden hayatta kalma sapması taşıdığını açıkça yazıyor. Zayıf yanlar: çok sayıda model ve konfigürasyon taranıp en iyisinin seçilmesi çoklu test sapması yaratır; holdout bunu kısmen dengeliyor ama yalnızca 2 yıl. Spread varsayımları gözlemlenmiş değil, "sektör bilgisine dayalı kademeler". Repo hızla değişiyor ve büyük bir kurulum gerektiriyor.

**Çalıştırma:**
```bash
git clone https://github.com/stefan-jansen/machine-learning-for-trading && cd machine-learning-for-trading
uv sync
uv run python data/download_all.py --free-only --skip-firm-characteristics
uv run python scripts/verify_installation.py
# case_studies/etfs/ altındaki defterleri numara sırasıyla 01'den 19'a kadar çalıştırın
```

---

### 54. ML4T 3. Baskı: CME Vadeli Vaka Çalışması (taşıma/momentum sıralamalı long-short) ★★

| | |
|---|---|
| Repo | https://github.com/stefan-jansen/machine-learning-for-trading (`case_studies/cme_futures/`, `config/setup.yaml`, `13_backtest.py`, `16_costs.py`, `18_holdout_backtest.py`) |
| Yıldız / son güncelleme | 21737 / 2026-11-06 |
| Lisans | MIT |
| Piyasa / zaman dilimi | 30 CME vadeli kontratı (endeks, tahvil, enerji, metal, döviz, tarım, hayvancılık), günlük veri, haftalık karar |
| Yazar | Stefan Jansen |

**Mantık:** Vade yapısı, roll getirisi ve momentum özelliklerinden ML modelleri (doğrusal, GBM, tablo DL, LSTM, PCA, DML) ürün getirilerini tahmin eder. Her cuma uzlaşma fiyatıyla karar verilir, emir pazartesi açılışında uygulanır. Ürünler tahmine göre sıralanır, en iyi k long, en kötü k short ve her bacak eşit büyüklüktedir; sonraki aşamalar eşit risk ya da notional tabanlı tahsis ve risk katmanı ekler. Bu yapı vadeli işlemlerde kesitsel bir istatistiksel arbitraj, yani piyasa-nötre yakın bir taşıma/momentum stratejisidir.

**Güvenilirlik:** ETF vaka çalışmasıyla aynı disiplin: 5 katlı walk-forward, etiket ufku kadar boşluk, 2024-2025 holdout'u ve holdout'a dokunmadan seçilmiş tek konfigürasyon. Maliyet modeli malzemesel: kontrat başına 2 USD komisyon, likit ürünlerde 1, az likitlerde 2 tick spread ve roll kayması. Defterler kendi sınırlamalarını açıkça yazıyor (ör. temel backtest'te "kovaryans, risk hedefi ve maliyet modeli yok" ve bunun yalnızca karşılaştırma tabanı olduğu). Zayıf yanlar: veri Databento'dan ve ücretli (README önce maliyet tahmini almayı öneriyor); çok sayıda konfigürasyon taraması; evren 30 ürünle küçük olduğundan kesitsel sıralama gürültülü.

**Çalıştırma:**
```bash
cd machine-learning-for-trading && uv sync
uv run python data/futures/market/download.py --estimate-only   # Databento maliyet tahmini
uv run python data/futures/market/download.py
# case_studies/cme_futures/ defterlerini 01'den 19'a kadar sırayla çalıştırın
# Yeniden eğitmeden incelemek için: uv run python scripts/download_artifacts.py
```

---

### 55. ArbitrageLab PCA Stat-Arb (Avellaneda-Lee eigenportfolio s-skoru) ★★

| | |
|---|---|
| Repo | Defter: https://github.com/hudson-and-thames/arbitrage_research (`Other Approaches/pca_approach.ipynb`); kütüphane: https://github.com/hudson-and-thames/arbitragelab (`arbitragelab/other_approaches/pca_approach.py`) |
| Yıldız / son güncelleme | 164 / 2024-05-02 (kütüphane: 705 / 2024-05-19) |
| Lisans | BSD-3-Clause |
| Piyasa / zaman dilimi | ABD hisseleri (S&P 500'den yaklaşık 170 hisse), günlük, yfinance |
| Yazar | Hudson & Thames (yöntem: Avellaneda ve Lee, 2010) |

**Mantık:** 252 günlük korelasyon matrisinden 15 temel bileşen (eigenportfolio) çıkarılır. Her hissenin son 60 günlük getirisi bu faktör getirilerine regrese edilir; artığın kümülatif toplamı OU süreci olarak modellenir ve s-skoru hesaplanır (yalnızca ortalamaya dönüş hızı `k > 8.4` olanlar alınır). Makaledeki eşikler kullanılır: s < -1,25 ise long, s > 1,25 ise short açılır; long pozisyon s > -0,5'te, short pozisyon s < 0,75'te kapatılır. Her hisse pozisyonu faktör yüklerine göre hedge edilir. Ağırlıklar mutlak toplamı 1 olacak şekilde normalize edilir, sinyaller bir gün kaydırılarak getiriye uygulanır.

**Güvenilirlik:** Avellaneda-Lee yönteminin sadık ve okunaklı bir uygulaması; parametreler makaleden alınmış, yani bu veride optimize edilmemiş. Pencereler kayan olduğu için yapıda doğrudan ileri bakış yok. Zayıf yanlar: maliyet hiç yok, oysa günlük yeniden dengelenen yüzlerce hisseli bir portföyde maliyet sonucu belirler. Hisse listesi bugün yfinance'ta bulunan isimlerle sınırlı olduğundan, kaybolan hisseler (ör. ALXN, BBBY) indirilemez ve hayatta kalma sapması oluşur. Eşitlik eğrisi tek bir dönem için çiziliyor, istatistiksel sağlamlık testi yok. Defterdeki getiri ve sinyal indekslerinin hizalaması elle yapılıyor, çalıştırmadan önce kontrol edilmeli. Kütüphane 2024'ten beri güncellenmiyor.

**Çalıştırma:**
```bash
pip install arbitragelab yfinance jupyter
git clone https://github.com/hudson-and-thames/arbitrage_research
jupyter notebook "arbitrage_research/Other Approaches/pca_approach.ipynb"
```

---

### 56. ArbitrageLab Kalman Filtreli Pairs Trading (EWA/EWC) ★

| | |
|---|---|
| Repo | Defter: https://github.com/hudson-and-thames/arbitrage_research (`Other Approaches/kalman_filter.ipynb`); kütüphane: https://github.com/hudson-and-thames/arbitragelab (`arbitragelab/other_approaches/kalman_filter.py`) |
| Yıldız / son güncelleme | 164 / 2024-05-02 (kütüphane: 705 / 2024-05-19) |
| Lisans | BSD-3-Clause |
| Piyasa / zaman dilimi | EWA ve EWC ülke ETF'leri, günlük, 2006-2012 |
| Yazar | Hudson & Thames (yöntem: Ernest Chan, "Algorithmic Trading" kitabındaki örnek) |

**Mantık:** Kalman filtresi, EWC = beta x EWA + alfa ilişkisindeki beta ve alfayı her gün günceller (`observation_covariance=0.001`, `delta=0.0001`). Tahmin hatası e(t) ve onun standart sapması sqrt(Q(t)) hesaplanır. e(t) < -1 x sqrt(Q) ise spread long, e(t) > 1 x sqrt(Q) ise spread short açılır; hata işaret değiştirip eşiğin öbür tarafına geçince kapanır. Bacak ağırlıkları dinamik hedge oranından türetilir (`w_x = beta / (beta + 1)`).

**Güvenilirlik:** Filtre her adımda yalnızca geçmiş veriyle güncellendiği için hedge oranında ileri bakış yok ve sonuçlar Chan'in kitabıyla karşılaştırılarak doğrulanıyor (kod referans grafiklerle aynı çıktıyı hedefliyor). Ancak bu bir kitap örneğinin tekrarı: parite ve dönem sonradan seçilmiş (EWA/EWC 2006-2012 en bilinen başarılı örnek), maliyet yok, örneklem dışı test yok, tek parite. Kovaryans parametreleri gerekçesiz sabitler. Kalman tabanlı pairs için temiz bir referans kod, strateji kanıtı değil. (letianzj'nin Kalman defterinden farklı bir uygulamadır.)

**Çalıştırma:**
```bash
pip install arbitragelab yfinance jupyter
jupyter notebook "arbitrage_research/Other Approaches/kalman_filter.ipynb"
```

---


## Forex, vadeli/CTA, Pine Script ve kurum örnekleri

### 57. Carver EWMAC ve Carry kuralları (systematictradingexamples) ★★★

| | |
|---|---|
| Repo | https://github.com/robcarver17/systematictradingexamples (`ewmac.py`, `carry.py`, `tradingrules.py`, `common.py`) |
| Yıldız / son güncelleme | 494 / 2020-07-22 |
| Lisans | GPL-2.0 |
| Piyasa / zaman dilimi | Vadeli işlemler (ham petrol, US10, Bund, döviz, endeks vb. yaklaşık 40 kontrat, CSV olarak repoda) / günlük |
| Yazar | Robert Carver. Man AHL'de eski portföy yöneticisi, "Systematic Trading" ve "Leveraged Trading" kitaplarının yazarı; geçmişi kamuya açık kaynaklarla doğrulanabiliyor. |

**Mantık:** EWMAC kuralı hızlı ve yavaş üssel hareketli ortalama farkını alır (`Lfast=16`, `Lslow=4*Lfast=64`), bunu 25 günlük EWM fiyat değişimi standart sapmasına böler, kitaptaki tablo 49'dan gelen sabit bir ölçekleyiciyle çarpar (16/64 için 3.75) ve sonucu -20 ile +20 arasında keser. Carry kuralı, işlem gören ve yakın kontrat arasındaki fiyat farkını vade farkına bölerek "nerpu" (fiyat biriminde net beklenen getiri) hesaplar, yıllık oynaklığa böler, 30 ile ölçekler ve yine ±20'de keser. Çıktı bir "forecast"tır; pozisyon büyüklüğü kitaptaki oynaklık hedeflemesiyle (forecast/10 × hedef risk / enstrüman riski) belirlenir, bu repoda pozisyon motoru yoktur. Stop yoktur; çıkış, forecast'ın işaret değiştirmesi ya da küçülmesiyle sürekli pozisyon ayarıdır.

**Güvenilirlik:** Kanıt türü kitap ve blog düzeyinde akademik/pratisyen literatürdür; trend ve carry, onlarca yıllık çok piyasalı verilerde belgelenmiş risk primleridir. Parametreler serbestçe optimize edilmemiş, sabit bir hız ailesinden (2/8 ile 64/256) seçilmiştir ve forecast ölçekleyiciler tablodan gelir; bu, overfit riskini düşürür. Kod eğitim amaçlıdır: Python 2 (`print "..."`), kaldırılmış `pd.ewma` ve `pd.ewmstd` çağrıları içerir, hata ve NaN işlemesi yoktur. Maliyet modeli bu dosyalarda yoktur. Repo 2020'den beri güncellenmiyor; üretim kodu Carver'ın ayrı bir projesindedir (bu raporun kapsamı dışında).

**Çalıştırma:** `git clone https://github.com/robcarver17/systematictradingexamples && cd systematictradingexamples`; modern pandas için `pd.ewma(x, span=n)` yerine `x.ewm(span=n).mean()`, `pd.ewmstd` yerine `x.ewm(span=n).std()` yazılmalı ve `print` ifadeleri Python 3'e çevrilmeli; ardından `python ewmac.py` ve `python carry.py`.

---

### 58. EA31337 (MT4/MT5 çok stratejili Forex EA) ★★

| | |
|---|---|
| Repo | https://github.com/EA31337/EA31337 (strateji kodları `src/strategies` alt modülünde, https://github.com/EA31337/EA31337-strategies) |
| Yıldız / son güncelleme | 1354 / 2026-04-07 |
| Lisans | GPL-3.0 |
| Piyasa / zaman dilimi | Forex, varsayılan olarak EURUSD / M1'den H12'ye kadar zaman dilimi başına ayrı strateji |
| Yazar | EA31337 topluluğu (ana geliştirici GitHub'da kenorb). Profesyonel trading geçmişi doğrulanamadı. |

**Mantık:** Her zaman dilimine bir strateji atanır (rapordaki parametrelerde örneğin `Strategy_M5=15`, `Strategy_H1=34`); stratejiler RSI, Bollinger, MA gibi göstergelerin sinyal yöntemleri ve bit maskeli filtrelerden oluşur. Çıkış ve risk, EA düzeyinde parametrelerle yönetilir: `EA_OrderCloseLoss=300`, `EA_OrderCloseProfit=120`, `EA_OrderCloseTime=-90`, zaman dilimine göre stop stratejileri (`EA_Stops_H1=22` vb.) ve `EA_Risk_MarginMax=1.8`. Lot boyutu `EA_LotSize=0` ile otomatik risk hesabına bırakılmıştır.

**Güvenilirlik:** Repoda Docker ile üretilmiş, MT4 Strategy Tester raporları yıl yıl ve iki spread seviyesiyle (1 ve 10 puan) commit edilmiş durumda; bu nadir görülen bir şeffaflık. Ancak sonuçlar zayıf: Advanced sürüm 10.000 USD ile 2017'de -910 (PF 0.57), 2018'de -403 (PF 0.83), 2019'da -137 (PF 0.90), 2020'de +94 (PF 1.01), 2021'de +1252 (PF 1.84) yaptı (spread 10). Lite sürüm yıllar boyunca PF 0.98 ile 1.21 arasında kaldı. Rider sürümü 2017'de hesabın %92'sini kaybetti. Raporlardaki modelleme kalitesi %24.99'dur, yani tick verisi sentetiktir. README, SET dosyalarının "sürüm öncesi optimizasyonda en iyi performans gösteren değerler" olduğunu açıkça söylüyor ve her sürümde yeniden optimize ediliyor; bu, son yılın iyi sonucunun büyük ölçüde örneklem içi olduğunu düşündürür. Çerçeve olarak değerli, hazır strateji olarak kenarı kanıtlanmamış.

**Çalıştırma:** `git clone --recursive https://github.com/EA31337/EA31337`; MetaEditor'da `src/EA31337.mq5` (ya da `.mq4`) derlenir, Strategy Tester'da EURUSD ile sürüm paketindeki SET dosyası yüklenir. Docker tabanlı test için repodaki `docker/backtest/...` altındaki `docker-compose.yml` dosyaları kullanılır.

---

### 59. Geraked BBRSI ve diğer MT5 EA'ları (grid ile) ★

| | |
|---|---|
| Repo | https://github.com/geraked/metatrader5 (`Experts/BBRSI.mq5`, test sonuçları `Test/BBRSI/`) |
| Yıldız / son güncelleme | 686 / 2025-11-15 |
| Lisans | MIT |
| Piyasa / zaman dilimi | XAUUSD 5 dakika (BBRSI); diğer EA'lar AUDUSD 5M, NZDUSD 3H, USDCAD 15M gibi farklı semboller |
| Yazar | "Rabist" (README'de LinkedIn bağlantısı var). Profesyonel trading geçmişi doğrulanamadı. README'de USDT bağış adresi bulunuyor. |

**Mantık:** BBRSI'da long girişi: iki bar önce RSI(7) < 30 ve kapanış alt Bollinger(500, 2) bandının altında, bir önceki barda RSI 30'un üstüne dönmüş, kapanış alt bandın üstüne dönmüş ve orta bandın altında. Short simetriktir (70 ve üst bant). SL alt banttan `SLCoef=0.9` × (orta - alt) kadar aşağıda, TP giriş ile SL arasındaki mesafenin `TPCoef=1` katı. Ancak commit edilmiş test SET dosyasında `IgnoreSL=true`, `IgnoreTP=true`, `Grid=true`, `GridVolMult=1.1`, `GridMaxLvl=20`, `MarginLimit=0` ayarlı; yani zarardaki pozisyona 1.1 katı lotla 20 kademeye kadar ekleme yapılır ve gerçek stop yoktur, yalnızca %50 trailing ve orta banda geri dönüşte (sadece kârdayken) kapanış vardır.

**Güvenilirlik:** Yazarın kendi test README'si açıkça şunu söylüyor: "Stratejinin saf uygulaması uzun vadede kârlı değildi; mevcut uygulama Grid tekniğiyle birleştirildi ve bu onu kârlı yaptı." Ana README de bazı EA'ların "kârlılığı zorla artırmak için" grid ile birleştirildiğini ve bunun ciddi risk getirdiğini kabul ediyor. Bu, kenarın göstergeden değil martingale benzeri pozisyon büyütmeden geldiği ve 2.5 yıllık tek bir örneklemle (2021-02 ile 2023-09, tek broker) gösterildiği anlamına gelir. Her EA farklı sembol ve zaman diliminde test edilmiş; bu da sembol/zaman dilimi seçiminin optimize edildiğini düşündürür. Kod okunaklı ve derlenmiş `.ex5` dosyaları var, ama canlı kullanım için önerilmez.

**Çalıştırma:** Repo klonlanır, `Experts/`, `Include/` ve `Indicators/` klasörleri MT5 `MQL5` veri klasörüne kopyalanır, MetaEditor'da `BBRSI.mq5` derlenir; Strategy Tester'da `Test/BBRSI/BBRSI-XAUUSD-5M-Inputs.set` yüklenir. Değerlendirme için `Grid=false`, `IgnoreSL=false` ile de test edilmesi gerekir.

---

### 60. JamesORB: Frankfurt/Londra açılış aralığı kırılımı (MQL4) ★

| | |
|---|---|
| Repo | https://github.com/omnisis/mt4-ea-obr (`JamesORB.mq4`) |
| Yıldız / son güncelleme | 10 / 2012-12-16 |
| Lisans | yok |
| Piyasa / zaman dilimi | Forex (sembol sabit değil) / saatlik |
| Yazar | Dosya başlığında "Clifford H. James"; profesyonel geçmişi doğrulanamadı. |

**Mantık:** Saat 11:00 barında (EET 10:00 barının kapanışı) aralık değeri olarak ATR(72) + 0.0002 hesaplanır. Önceki barın yükseğinin bu değer kadar üstüne BUY STOP, düşüğünün bu değer kadar altına SELL STOP konur. TP girişten 1 × ORB, SL 1.65 × ORB uzaklıktadır. Lot sabit 1'dir (dosyada risk yüzdesine göre lot hesaplayan `calcTradeVolume` fonksiyonu var ama kullanılmıyor). Saat 17:30'da tüm açık ve bekleyen emirler kapatılır.

**Güvenilirlik:** Hiçbir backtest sonucu yok. TP/SL oranı 1:1.65 olduğundan stratejinin başa baş için maliyet öncesi yaklaşık %62 isabet oranına ihtiyacı var. İki bekleyen emir OCO değil; fiyat önce bir yöne sonra diğer yöne giderse her ikisi de dolabilir. `calcSLDist` fonksiyonu -1 döndüren bir taslak; kod yarım bırakılmış görünüyor. Tarihsel bir Londra kırılımı örneği olarak okunabilir, hazır bir sistem değildir.

**Çalıştırma:** `JamesORB.mq4` ve `include/user/*.mq4` dosyaları MT4 `MQL4/Experts` ve `MQL4/Include/user` altına kopyalanır, MetaEditor'da derlenir ve H1 grafikte Strategy Tester ile çalıştırılır. Broker saatinin EET olduğu varsayılır.

---

### 61. QuantConnect Lean: Intraday FX Reversal (EURUSD) ★★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (`Algorithm.Python/Alphas/IntradayReversalCurrencyMarketsAlpha.py`) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | Forex, EURUSD (OANDA) / saatlik |
| Yazar | QuantConnect ekibi, "Benchmark Alpha Series" kapsamında. Dayandığı makale: LeBaron ve Zhao, "Intraday Foreign Exchange Reversals" (Blake LeBaron, Brandeis Üniversitesi'nde finans profesörü; doğrulanabilir). |

**Mantık:** Yalnızca New York saatiyle 10:00 ile 15:00 arasında sinyal üretilir. Fiyat 5 saatlik SMA × 1.001'in altındaysa "UP" (long), üstündeyse "DOWN" (short) insight verilir; yalnızca yön değiştiğinde yeni sinyal üretilir. Tüm insight'ların süresi aynı gün 15:01'de biter, yani pozisyon gün sonunda kapanır. Portföy eşit ağırlıklıdır, risk yönetimi `NullRiskManagementModel` (stop yok).

**Güvenilirlik:** Kanıt türü akademik makaledir (New York saatlerinde dolar karşısında gün içi geri dönüş). Parametre sayısı az (SMA 5, eşik %0.1, saat penceresi makaleden). Kodda komisyon açıkça sıfıra ayarlanmış (`ConstantFeeModel(0)`); Lean'de forex işlemleri bid/ask quote verisiyle dolduğu için spread kısmen modellenir, ama saatlik ve sık işlem yapan bir strateji için bu varsayım iyimserdir. Repoda sonuç raporu yok; sonucu kullanıcı kendisi üretmelidir. Makalenin örneklemi 2000'lerin başı olduğundan kenarın zamanla aşınmış olma ihtimali yüksektir.

**Çalıştırma:** `pip install lean && lean init` ile proje oluşturulur, dosya bir proje klasörüne `main.py` olarak kopyalanır, `lean backtest "<proje>"` (QuantConnect veri aboneliği veya yerel OANDA saatlik verisi gerekir). Alternatif olarak QuantConnect web IDE'sine yapıştırılabilir.

---

### 62. QuantConnect Lean: VIX Dual Thrust (aslında SPY) ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (`Algorithm.Python/Alphas/VIXDualThrustAlpha.py`) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | ABD hisse (SPY) / 30 dakikalık konsolide barlar |
| Yazar | QuantConnect topluluğu/ekibi; yazar adı belirtilmemiş, doğrulanamadı. |

**Mantık:** Klasik Dual Thrust: son 20 barın HH, LL, HC, LC değerlerinden Range = max(HH - LC, HC - LL); üst çizgi = açılış + 0.63 × Range, alt çizgi = açılış - 0.63 × Range. Fiyat üst çizgiyi geçince ve long değilken UP, alt çizginin altına inince ve short değilken DOWN insight verilir; insight 5 gün geçerlidir. Risk yönetimi: menkul kıymet başına %3 maksimum düşüş (`MaximumDrawdownPercentPerSecurity(0.03)`).

**Güvenilirlik:** Dosya yorumu parametrelerin "Ekim 2016 ile Şubat 2019 arasında bir dizi rastgele backtest'te kabul edilebilir sonuç veren" değerler olduğunu söylüyor; bu, kısa bir dönemde yapılmış açık bir parametre taramasıdır. Başlık ve yorum UVXY işlem yaptığını söylerken kod SPY işliyor; dokümantasyon ile kod tutarsız. Komisyon sıfır. Örnek olarak faydalı, kanıt olarak zayıf.

**Çalıştırma:** `lean init`, dosyayı `main.py` olarak kopyalama, `lean backtest "<proje>"` (dakikalık SPY verisi gerekir).

---

### 63. QuantConnect Lean: Futures Momentum (E-mini S&P EMA cross) ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (`Algorithm.Python/FuturesMomentumAlgorithm.py`) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | CME E-mini S&P 500 vadeli / günlük sinyal |
| Yazar | QuantConnect ekibi (şirket örneği). |

**Mantık:** SPY üzerinde EMA(20) ve EMA(60) hesaplanır. EMA20 > EMA60 × 1.001 ise ve pozisyon yoksa, vadesi 90 günden uzak kontratlardan biri 1 adet alınır. EMA20 < EMA60 × 1.001 olduğunda tüm pozisyon kapanır. Short yok, stop yok, sabit 1 kontrat.

**Güvenilirlik:** Test aralığı yalnızca 2016-01-01 ile 2016-08-18 (yaklaşık 8 ay); bir API gösterimi olarak tasarlanmış. Yorum "ön kontratı işle" derken kod `sorted(..., reverse=True)[0]` ile vadesi en uzak kontratı seçiyor; bu, likiditesi düşük kontratla işlem demektir. Roll mantığı yok. Klasik CTA trend fikrinin en basit hali; kanıt değeri yok.

**Çalıştırma:** `lean init`, dosyayı `main.py` olarak kopyalama, `lean backtest "<proje>"` (vadeli işlem verisi gerekir).

---

### 64. QuantConnect Lean: ETF Global Rotation ★

| | |
|---|---|
| Repo | https://github.com/QuantConnect/Lean (`Algorithm.Python/ETFGlobalRotationAlgorithm.py`) |
| Yıldız / son güncelleme | 22422 / 2026-11-06 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | ABD ETF'leri (MDY, IEV, EEM, ILF, EPP; güvenli liman EDV, SHY) / aylık rotasyon |
| Yazar | QuantConnect ekibi (şirket örneği). |

**Mantık:** 30 günde bir, her ETF için skor = (100 × 30 günlük MOM + 75 × 90 günlük MOM) / 175 hesaplanır. En yüksek skorlu ETF pozitif skorluysa tüm marjla ona geçilir, değilse nakde geçilir. Stop yok, tek varlıkta yüzde 100 pozisyon.

**Güvenilirlik:** Lean'deki `MOM` göstergesi yüzde değil mutlak fiyat farkı döndürür (yüzdelik versiyon `MOMP`'dir). Dolayısıyla fiyat düzeyleri çok farklı ETF'ler dolar bazında karşılaştırılıyor; fiyatı yüksek ETF'ler sistematik olarak avantajlı. Bu, sıralamanın kendisini bozan bir hatadır. Ayrıca güvenli liman ETF'leri de aynı listede sıralandığı için "growth" ve "safety" ayrımı kodda fiilen uygulanmıyor. Fikir (göreceli momentum rotasyonu) literatürde sağlam ama bu uygulama hatalı.

**Çalıştırma:** `lean init`, dosyayı `main.py` olarak kopyalama; düzeltme için `self.mom(...)` yerine `self.momp(...)` yazılması önerilir; sonra `lean backtest "<proje>"`.

---

### 65. WorldQuant 101 Formulaic Alphas (Python uygulaması) ★

| | |
|---|---|
| Repo | https://github.com/yli188/WorldQuant_alpha101_code (`101Alpha_code_1.py`) |
| Yıldız / son güncelleme | 882 / 2019-03-07 |
| Lisans | yok |
| Piyasa / zaman dilimi | Hisse senedi kesiti (orijinalde ABD) / günlük |
| Yazar | Formüller: Zura Kakushadze, "101 Formulaic Alphas" (Wilmott, 2016; arXiv:1601.00991); makale WorldQuant'ta üretimde kullanılmış alfaları anlattığını belirtiyor ve yazarın WorldQuant geçmişi doğrulanabiliyor. Python kodunun yazarı yli188: profesyonel geçmişi doğrulanamadı, WorldQuant ile resmi bağı yok. |

**Mantık:** 101 alfa, `rank`, `ts_rank`, `correlation`, `decay_linear`, `delta` gibi yardımcı fonksiyonlarla tek tek yazılmış; örneğin `alpha101 = (close - open) / ((high - low) + 0.001)`, `alpha001 = rank(ts_argmax(SignedPower(...), 5))`. Bunlar sinyal üretir, giriş/çıkış ve pozisyon büyüklüğü yoktur; makalede alfalar kesitsel olarak nötrlenip birleştirilmek üzere tasarlanmıştır, ortalama tutma süresi 0.6 ile 6.4 gün arasıdır.

**Güvenilirlik:** Makale, alfaların gerçek bir fonun üretim sinyalleri olduğunu ve birbirleriyle düşük korelasyonlu olduğunu raporluyor; ancak tek tek alfaların maliyet sonrası kârlılığı makalede iddia edilmiyor ve 2016 sonrası yayın etkisiyle aşınmış olmaları beklenir. Kodda ciddi bir hata var: `rank(df)` fonksiyonu `df.rank(pct=True)` ile zaman ekseninde sıralama yapıyor (doğru olan kesitsel `axis=1` satırı yorum satırı olarak bırakılmış). Bu haliyle tek hisse üzerinde çalışırken tüm geçmiş ve gelecek veri üzerinden yüzdelik sıra hesaplanıyor, yani ileriye bakma (look-ahead) yanlılığı oluşuyor. Ayrıca `alpha001` içinde `inner = self.close` kopya almadan değiştirildiği için kapanış serisi bozuluyor. Formül kaynağı olarak değerli, kod olduğu gibi kullanılmamalı.

**Çalıştırma:** `pip install pandas numpy scipy`; `from 101Alpha_code_1 import get_alpha` yerine dosya `alpha101.py` adıyla kopyalanıp `get_alpha(df)` çağrılır (df: open, high, low, close, volume, vwap sütunlu). Önce `rank` fonksiyonu kesitsel panel veriye göre düzeltilmelidir.

---

### 66. Clenow "Stocks on the Move" momentum tarayıcısı ★★

| | |
|---|---|
| Repo | https://github.com/skyte/momentum (`momentum_posis.py`, `momentum_data.py`, `config.yaml`) |
| Yıldız / son güncelleme | 42 / 2023-06-03 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | ABD hisseleri (S&P 500 ve Nasdaq 100, isteğe bağlı S&P 400/600) / günlük, haftalık yeniden dengeleme (kitaba göre) |
| Yazar | Strateji: Andreas Clenow (Acies Asset Management CIO'su, "Stocks on the Move" ve "Trading Evolved" yazarı; doğrulanabilir). Kod: GitHub kullanıcısı skyte, bir Discord üyesinin ilk sürümünden uyarlamış; profesyonel geçmişi doğrulanamadı. |

**Mantık:** Her hisse için son 125 günün log fiyatına doğrusal regresyon yapılır; skor = (exp(eğim)^252 - 1) × 100 × R². Fiyatı 100 günlük ortalamanın altında olan ve son dönemde %15'ten büyük gap içeren hisseler elenir. Skora göre sıralanıp ilk 50 listelenir. Pozisyon büyüklüğü = hesap × risk faktörü (varsayılan 0.002) / ATR(20); hedef pozisyon sayısına (25) ulaşacak şekilde risk faktörü bir kez yeniden ölçeklenir. Çıktı CSV ve TradingView izleme listesidir.

**Güvenilirlik:** Clenow'un kitabındaki kurallar yayımlanmış ve kitapta uzun dönemli backtest ile desteklenmiştir; parametreler (90/125 gün, MA100, %15 gap, ATR20) kitaptan gelir, yeniden optimize edilmemiştir. Ancak bu repo bir backtest değil, yalnızca bugünkü pozisyon listesini üreten bir tarayıcıdır. Kitaptaki piyasa rejimi filtresi (S&P 500 200 günlük ortalamanın altındaysa yeni alım yapma) uygulanmamış. Gap filtresi `pct_change().diff()` ile ikinci fark üzerinden hesaplanıyor, yani gerçek gap'i değil getirideki değişimi ölçüyor. Endeks üyeliği güncel listeden alındığı için geriye dönük kullanımda hayatta kalma yanlılığı olur.

**Çalıştırma:** `pip install -r requirements.txt`, `config.yaml` içinde `CASH` ve evren seçilir, `python momentum.py` (ya da adım adım `python momentum_data.py` ve `python momentum_posis.py`). Veri kaynağı varsayılan olarak Yahoo; TD Ameritrade API'si artık kapalı.

---

### 67. TqSdk Dual Thrust (Çin vadeli) ★

| | |
|---|---|
| Repo | https://github.com/ringoshinnytech/tqsdk-strategies (`strategies/04_dual_thrust.py`) |
| Yıldız / son güncelleme | 207 / 2026-08-06 |
| Lisans | yok |
| Piyasa / zaman dilimi | Çin vadeli işlemleri (varsayılan SHFE bakır `SHFE.cu2501`) / gün içi, tick bazlı tetik |
| Yazar | Hesap adı TqSdk sağlayıcısı Shinny Tech (信易科技) ile ilişkili izlenimi veriyor; bağlantı ve kişisel geçmiş doğrulanamadı. |

**Mantık:** Her yeni gün için son 4 günün HH, LL, HC, LC değerlerinden Range = max(HH - LC, HC - LL); üst çizgi = bugünkü açılış + 0.5 × Range, alt çizgi = açılış - 0.5 × Range. Son fiyat üst çizginin üstündeyse hedef pozisyon +1 lot, altındaysa -1 lot (`TargetPosTask` ile ters dönüş dahil). 14:50'de pozisyon sıfırlanır. Stop yok, sabit 1 lot.

**Güvenilirlik:** Dual Thrust, Michael Chalek'e atfedilen ve Çin vadeli piyasasında çok bilinen bir şablondur; kod formülü doğru uyguluyor. Ancak hiçbir backtest sonucu yok, maliyet ve kayma modeli yok, gece seansı hesaba katılmamış. Repo 90'dan fazla strateji içeriyor ve `scripts/daily_state.json` dosyası stratejilerin günlük otomatik bir takvimle yüklendiğini gösteriyor; bu, repo'nun bir içerik/pazarlama akışı olduğunu düşündürür. Kütüphane tanıtımı olarak okunmalı.

**Çalıştırma:** `pip install tqsdk -U`; dosyadaki `YOUR_ACCOUNT` / `YOUR_PASSWORD` kendi Shinny hesabınızla değiştirilir, süresi dolmuş kontrat kodu güncellenir, `python strategies/04_dual_thrust.py` (TqSim sanal hesapta çalışır; backtest için `TqBacktest` eklenmelidir).

---

### 68. TqSdk Turtle (Çin vadeli) ★

| | |
|---|---|
| Repo | https://github.com/ringoshinnytech/tqsdk-strategies (`strategies/05_turtle_trading.py`) |
| Yıldız / son güncelleme | 207 / 2026-08-06 |
| Lisans | yok |
| Piyasa / zaman dilimi | Çin vadeli (varsayılan INE ham petrol `INE.sc2501`) / günlük |
| Yazar | Yukarıdakiyle aynı; doğrulanamadı. |

**Mantık:** Kurgulanan kural: kapanış 20 günlük yüksek üstüne çıkarsa long, 20 günlük düşük altına inerse short; 10 günlük kanal ters yönde kırılınca çıkış. Lot = bakiye × %1 / (ATR(20) × 1000 çarpan), en fazla 10 lot.

**Güvenilirlik:** Kodda stratejiyi işlevsiz bırakan bir hata var. Kanal `klines.high.iloc[-(N1+1):-1]` ile hesaplanıyor; bu pencere son tamamlanmış barı (`iloc[-2]`) içeriyor ve karşılaştırılan kapanış da `klines.close.iloc[-2]`. Bir barın kapanışı kendi yükseğinden büyük olamayacağı için `last_close > high_n1` koşulu hiçbir zaman sağlanmaz; giriş sinyali fiilen hiç oluşmaz (short için de aynısı geçerli). Ayrıca çıkış koşulları pozisyon yönünü kontrol etmiyor: long pozisyondayken fiyat 10 günlük yeni yükseğe çıkarsa `last_close > high_n2` dalı pozisyonu kapatıyor. Turtle'ın orijinal kurallarındaki pyramiding ve 2N stop da yok. Kullanılmadan önce düzeltilmesi gerekir.

**Çalıştırma:** `pip install tqsdk -U`, hesap bilgileri ve kontrat kodu güncellenir, kanal pencereleri `iloc[-(N1+2):-2]` olarak düzeltilir, `python strategies/05_turtle_trading.py`.

---

### 69. Pine Script: Alorse strateji koleksiyonu (CI ile backtest edilmiş) ★

| | |
|---|---|
| Repo | https://github.com/Alorse/pinescript-strategies (örnek: `strategies/trend/Supertrend + EMA rebound [Alorse].pine`, sonuçlar `BACKTEST.md`) |
| Yıldız / son güncelleme | 342 / 2026-08-25 |
| Lisans | yok (dosya başlıklarında MPL-2.0 ibaresi var) |
| Piyasa / zaman dilimi | Kripto ağırlıklı (testler BTCUSDT günlük) |
| Yazar | Alorse; profesyonel geçmişi doğrulanamadı. |

**Mantık:** Örnek strateji: Supertrend(10, 3) yön değiştirince giriş, ters değişimde çıkış; ayrıca trend yönündeyken fiyat EMA(20)'yi geri kazanırsa ve son girişten daha iyi bir fiyattaysa ek giriş. İsteğe bağlı %1.5 kâr al. Pozisyon özsermayenin %10'u, komisyon %0.1. `request.security` kullanılmadığı için çok zaman dilimli repaint riski bu dosyada yok.

**Güvenilirlik:** Repo, PineTS ile tüm v5 stratejilerini commit edilmiş BTCUSDT günlük verisi üzerinde iki dönemde (2022-2024 ve 2025-2026) otomatik backtest eden bir CI içeriyor; bu dürüst bir yaklaşım. Sonuçlar da dürüstçe zayıf: listedeki stratejilerin neredeyse hepsinin Sharpe oranı negatif ya da sıfıra yakın (en iyisi "Full Candle", 2022-2024'te 0.175, 2025-2026'da -0.248), işlem sayıları çok düşük. Bir dosya adında "[FAKE]" etiketi var ("Heikin Ashi Strategy V2 [FAKE]"), yazarın bu stratejinin sonuçlarını kendisi güvenilmez saydığını gösteriyor (Heikin Ashi grafiklerinde sentetik fiyatlarla dolum, TradingView'de bilinen bir yanıltıcı backtest kaynağıdır; dosya ayrıca incelenmedi). 31 dosya Pine v4 olduğu için test edilmemiş. Koleksiyon, popüler TradingView fikirlerinin maliyet sonrası kenar göstermediğine dair yararlı bir negatif kanıt.

**Çalıştırma:** `.pine` dosyası TradingView Pine Editor'a yapıştırılıp "Add to chart" ile Strategy Tester'da çalıştırılır. Yerel CI için `npm install` ve `node scripts/backtest.mjs` (repodaki `package.json`'a göre).

---

### 70. Pine Script: Acrypto Weighted Strategy ★

| | |
|---|---|
| Repo | https://github.com/AlbertoCuadra/algo_trading_weighted_strategy (`weighted_strategy.pine`) |
| Yıldız / son güncelleme | 321 / 2022-11-04 |
| Lisans | CC BY-NC-SA 4.0 (GitHub'da NOASSERTION görünüyor; ticari kullanım yasak) |
| Piyasa / zaman dilimi | Kripto (örnek BTC/USDT Binance 4 saat) |
| Yazar | Alberto Cuadra; README'ye göre doktora öğrencisi. Finans alanında profesyonel geçmişi doğrulanamadı. |

**Mantık:** Beş alt sinyal (MACD, Stoch RSI, RSI, Supertrend, MA crossover) 0 ile 5 arası ağırlıklarla toplanır; toplam `weight_trigger=2`'ye ulaşınca long veya short açılır. Pozisyon özsermayenin %100'ü. Stop %6 (kaynak `hl2`, yalnızca mum kapanışında kontrol edilir), kâr al long için her %6.8'de pozisyonun %15'i, short için her %13'te %10'u, en fazla 6 kademe; her kâr alımında stop TP-2 seviyesine taşınır. Ayrıca "tepe/dip tespiti" ile kısmi kapanış. Komisyon %0.075 ve 1 tick kayma tanımlı; `request.security` yok.

**Güvenilirlik:** 40'tan fazla girdi parametresi ve long ile short için birbirinden çok farklı kâr al seviyeleri (6.8 ve 13) var; README açıkça "algoritmanın istenen varlık için optimize edilmesi gerektiğini" söylüyor. Bu, eğri uydurmanın klasik işaretidir. Kanıt yalnızca tek bir BTC 4 saatlik ekran görüntüsü. README, Telegram sinyal kanalı ve 3Commas otomasyonu içeren ücretli "Pro" ve "Premium" sürümleri tanıtıyor ve TradingView referans bağlantısı içeriyor; repo kısmen pazarlama amaçlı. Proje 2022'den beri askıda.

**Çalıştırma:** `weighted_strategy.pine` TradingView Pine Editor'a yapıştırılıp BTCUSDT 4H grafikte Strategy Tester ile çalıştırılır.

---

### 71. Pine Script: krosenfeld7 EMA/osilatör stratejileri ★

| | |
|---|---|
| Repo | https://github.com/krosenfeld7/pine_script_strategies (örnek: `50_EMA+200_EMA/50_EMA+200_EMA_Long_Strategy.txt`) |
| Yıldız / son güncelleme | 5 / 2023-05-13 |
| Lisans | Apache-2.0 (dosya başlıklarında MPL-2.0) |
| Piyasa / zaman dilimi | Belirtilmemiş, yorumda "saatlik grafikte en iyi" |
| Yazar | krosenfeld7; profesyonel geçmişi doğrulanamadı. |

**Mantık:** Long: son 3 bar içinde fiyat EMA50'yi yukarı kesmiş, mevcut bar yeşil ve EMA50'nin üstünde, EMA50 > EMA200; önceki 3 barda aynı sinyal yoksa giriş. Çıkış: varsayılan %10 kâr al ve %10 zarar durdur (isteğe bağlı ATR × 1), ayrıca 100 bar sonra zaman çıkışı. Pozisyon özsermayenin %20'si. Short dosyaları simetrik. YouTube'da popüler 15 civarı indikatör kombinasyonu aynı şablona dökülmüş.

**Güvenilirlik:** `strategy()` çağrısında komisyon ve kayma tanımlı değil, yani TradingView varsayılanıyla maliyetsiz test edilir. `process_orders_on_close=true` olduğu için emir sinyal barının kapanışında dolar; bu, gerçekte uygulanabilir ama hafif iyimserdir. `request.security` kullanılmadığından bu dosyada repaint yok. Repoda hiçbir backtest sonucu yok, README tek cümle. Kodda short koşulunun önceki sinyal kontrolünde yanlışlıkla `longCondition` kullanılıyor (`search_preceding_candles(longCondition, lookback)`). Eğitim amaçlı şablon.

**Çalıştırma:** `.txt` dosyasının içeriği TradingView Pine Editor'a yapıştırılır (Pine v4), `strategy()` satırına `commission_type=strategy.commission.percent, commission_value=0.05, slippage=2` eklenerek test edilmesi önerilir.

---

### 72. backtesting.py örnekleri: SmaCross + ATR trailing ve çok zaman dilimli RSI ★

| | |
|---|---|
| Repo | https://github.com/kernc/backtesting.py (`doc/examples/Strategies Library.py`, `doc/examples/Multiple Time Frames.py`) |
| Yıldız / son güncelleme | 9206 / 2026-08-05 |
| Lisans | AGPL-3.0 |
| Piyasa / zaman dilimi | ABD hisse (paketle gelen GOOG 2004-2013 verisi) / günlük |
| Yazar | Kütüphane yazarı kernc; profesyonel geçmişi doğrulanamadı. |

**Mantık:** SmaCross: SMA(10) SMA(25)'i yukarı kesince özsermayenin %95'iyle long, `set_trailing_sl(2)` ile 2 × ATR iz süren stop; yalnızca long. MTF System: günlük RSI(30) > 70, haftalık RSI(30) > 70, haftalık RSI > günlük RSI, SMA10 > SMA20 > SMA50 > SMA100 ve fiyat SMA10'un üstündeyse long, %8 sabit stop; fiyat SMA10'un %2 altına kapanırsa çıkış. Her iki örnekte komisyon %0.2.

**Güvenilirlik:** Bunlar kütüphanenin dokümantasyon örnekleridir ve tek bir hisse üzerinde, tek bir dönemde çalışır. MTF örneği aynı veri üzerinde `backtest.optimize(d_rsi=range(10,35,5), w_rsi=range(10,35,5), level=range(30,80,10))` ile 125 kombinasyon tarayıp sonucu aynı veride raporluyor; örneklem dışı test yok. Bu, kütüphanenin kullanımını gösterir, kenar iddiası taşımaz. Kütüphanenin kendisi bar sonu sinyali bir sonraki açılışta doldurduğu için ileriye bakma riski düşüktür.

**Çalıştırma:** `pip install backtesting`; `python "doc/examples/Strategies Library.py"` ya da notebook sürümü Jupyter'de açılır.

---

### 73. vectorbt: BTC çift MA çaprazı için walk-forward optimizasyon ★★

| | |
|---|---|
| Repo | https://github.com/polakowo/vectorbt (`examples/WalkForwardOptimization.ipynb`) |
| Yıldız / son güncelleme | 9717 / 2026-11-03 |
| Lisans | Apache-2.0 + Commons Clause (GitHub'da NOASSERTION; ticari satış kısıtlı) |
| Piyasa / zaman dilimi | BTC-USD (Yahoo) / günlük |
| Yazar | Oleg Polakow (vectorbt ve vectorbt PRO geliştiricisi); finans alanında profesyonel geçmişi doğrulanamadı. |

**Mantık:** Fiyat serisi 30 kayan pencereye bölünür (her biri 730 gün, son 180 günü test). Her eğitim penceresinde 10 ile 49 arasındaki tüm hızlı/yavaş MA çiftleri (780 kombinasyon) long/short olarak simüle edilir, Sharpe'ı en yüksek çift seçilir ve bir sonraki 180 günlük test diliminde uygulanır. Giriş: hızlı MA yavaşı yukarı keser; çıkış/ters dönüş: aşağı keser. Pozisyon tam sermaye; stop yok.

**Güvenilirlik:** Bu örnek, overfit'i ölçmek için doğru bir metodolojidir: örnek içi en iyi, örnek içi medyan, örnek dışı test ve al-tut Sharpe değerleri yan yana karşılaştırılır. Yani strateji değil, bir doğrulama şablonudur ve bu açıdan değerlidir. Zayıf yanları: `pf_kwargs` içinde komisyon ve kayma yok, test pencereleri `rolling_split` ile örtüşüyor (30 pencere bağımsız değil), yalnızca tek bir varlık. Notebook'un kendi çıktısı örnek dışı performansın örnek içi en iyiden belirgin biçimde düştüğünü göstermek için tasarlanmış.

**Çalıştırma:** `pip install vectorbt yfinance`; `jupyter notebook examples/WalkForwardOptimization.ipynb`. Gerçekçi sonuç için `pf_kwargs`'a `fees=0.001, slippage=0.0005` eklenmeli.

---

### 74. NautilusTrader: AUD/USD tick verisiyle EMA cross ★

| | |
|---|---|
| Repo | https://github.com/nautechsystems/nautilus_trader (`examples/backtest/fx_ema_cross_audusd_ticks.py`, strateji `docs/tutorials/ema_cross.py`; test sürümü `python/tests/strategies/ema_cross.py`) |
| Yıldız / son güncelleme | 31311 / 2026-11-06 |
| Lisans | LGPL-3.0 |
| Piyasa / zaman dilimi | Forex AUD/USD (TrueFX tick verisi) / 100 tick'lik mid barlar |
| Yazar | Nautech Systems (Chris Sellers'ın kurduğu şirket); kurumsal proje. |

**Mantık:** EMA(10) EMA(20)'yi yukarı kesince 1.000.000 birim long, aşağı kesince mevcut pozisyon kapatılıp short; her zaman piyasada. Stop yok. Simülasyon ayarları gerçekçi: `MakerTakerFeeModel` ile %0.002 ücret, `ProbabilisticFillModel` ile limit emirlerde %20 dolum ve %50 kayma olasılığı, hedging hesap, tick seviyesinde quote verisi.

**Güvenilirlik:** Motorun yürütme gerçekçiliği (bid/ask, kayma, ücret) bu listedeki en iyilerden biridir, ama strateji tamamen pedagojiktir: parametreler keyfi, veri kısa bir TrueFX örneği, sonuç raporu repoda yok. 100 tick'lik barlarda EMA çaprazının maliyet sonrası kenarı olması beklenmez. Değeri, stratejiyi gerçekçi maliyetlerle test etmek için hazır bir altyapı sunmasıdır.

**Çalıştırma:** `pip install -U nautilus_trader` ardından repo kökünden `python examples/backtest/fx_ema_cross_audusd_ticks.py`; örnek, `TestDataProvider` ile repodaki `truefx/audusd-ticks.csv` test verisini kullanır (repo klonlanmış olmalıdır).

---

### 75. Alpaca resmi örneği: Scalping (20 dakikalık SMA) ★

| | |
|---|---|
| Repo | https://github.com/alpacahq/example-scalping (`main.py`) |
| Yıldız / son güncelleme | 853 / 2023-10-02 |
| Lisans | yok |
| Piyasa / zaman dilimi | ABD hisseleri (kullanıcının verdiği semboller) / 1 dakika |
| Yazar | Alpaca Markets (aracı kurum, resmi örnek). |

**Mantık:** Her sembol için durum makinesi. Kapanış önceki dakikada 20 dakikalık SMA'nın altında, bu dakikada üstündeyse son işlem fiyatından limit alış (tutar `--lot` dolar). Alış dolunca hemen max(maliyet + 0.01, güncel fiyat) seviyesinden limit satış konur. 2 dakikada dolmayan alış iptal edilir. 15:55'ten sonra pozisyon piyasa emriyle kapatılır.

**Güvenilirlik:** Zarar durdurma yok: satış limiti her zaman maliyetin en az bir sent üstünde olduğundan zarardaki pozisyon gün sonuna kadar taşınır ve 15:55'te piyasa emriyle zararla kapanır. Bu, küçük kazançlar ve seyrek büyük kayıplar üreten negatif çarpıklıklı bir yapı. Hiçbir backtest veya sonuç yok; amaç API ve websocket kullanımını göstermek. Kod `DataFrame.append` kullanıyor, pandas 2.x'te çalışmaz; `alpaca_trade_api` paketi de artık `alpaca-py` ile değiştirildi.

**Çalıştırma:** `pipenv install` (ya da `pip install alpaca-trade-api pandas<2`), `main.py` içindeki API anahtarları doldurulur, `python main.py --lot=2000 SPY QQQ` (paper hesapta, piyasa açıkken).

---

### 76. Alpaca resmi örneği: Momentum day trading ★

| | |
|---|---|
| Repo | https://github.com/alpacahq/Momentum-Trading-Example (`algo.py`) |
| Yıldız / son güncelleme | 730 / 2023-10-02 |
| Lisans | yok |
| Piyasa / zaman dilimi | ABD düşük fiyatlı hisseler (2 ile 13 USD) / 1 saniye ve 1 dakika |
| Yazar | Alpaca Markets (resmi örnek). |

**Mantık:** Evren: fiyatı 2 ile 13 USD arası, önceki gün dolar hacmi 500.000 üstü ve gün içi en az %3.5 yükselmiş hisseler. Açılıştan 15 ile 60 dakika sonrası arasında: önceki kapanışa göre %4'ten fazla yükselmiş, ilk 15 dakikanın tepesinin üstünde, hacmi 30.000'den büyük ve MACD(12,26) histogramı pozitif ve son üç barda artan, MACD(40,60) pozitif ve artan hisselerde limit alış. Stop: son 5 dakikalık yerel dip - 0.01 (yoksa %5 altı), hedef: giriş + 3 × risk. Lot = portföy × 0.001 / (giriş - stop). Gün sonundan 15 dakika önce pozisyonlar kapatılır.

**Güvenilirlik:** Mantık açık ve risk bazlı pozisyonlama makul, ancak repoda hiç backtest yok ve parametre seçiminin (%4, 15 dakika, MACD 40/60) gerekçesi verilmemiş. Kod Alpaca üzerinden Polygon veri akışına (`api.polygon`) bağımlı; bu entegrasyon kapatıldığı için kod olduğu gibi çalışmaz. README Python 3.6 gerektiğini söylüyor. Küçük fiyatlı, hızlı yükselen hisselerde kayma ve spread maliyeti yüksektir.

**Çalıştırma:** `pip install -r requirements.txt`; veri katmanının `alpaca-py` ile yeniden yazılması gerekir; ardından API bilgileri girilip `python algo.py`.

---

### 77. Alpaca resmi örneği: Options Wheel ★★

| | |
|---|---|
| Repo | https://github.com/alpacahq/options-wheel (`core/strategy.py`, `core/execution.py`, `config/params.py`) |
| Yıldız / son güncelleme | 138 / 2025-06-05 |
| Lisans | Apache-2.0 |
| Piyasa / zaman dilimi | ABD hisse opsiyonları (varsayılan AAPL, QQQ, INTC, CAT, DLR, MP, NVDA, PLTR, AAL, V) / günde birkaç kez cron ile |
| Yazar | Alpaca Markets "Data Science" ekibi (resmi örnek). |

**Mantık:** Hisse yoksa nakit teminatlı put satılır, atanırsa (assignment) maliyet bazının üstünde covered call satılır. Kontrat filtresi: mutlak delta 0.15 ile 0.30 arası, yıllıklandırılmış prim getirisi (bid/strike × 365/(DTE+1)) %4 ile %100 arası, vade 0 ile 21 gün, açık pozisyon en az 100. Skor = (1 - |delta|) × (250 / (DTE + 5)) × (bid / strike); skoru 0.05'in üstünde olan ve sembol başına en yüksek skorlu kontrat seçilir. Sembol başına 1 kontrat, toplam risk tavanı `MAX_RISK=80.000` USD. Stop, roll veya erken kapanış kuralı yok.

**Güvenilirlik:** Wheel, prim toplama (kısa volatilite) stratejisidir; uzun dönemde kısa put getirisinin volatilite risk primi taşıdığı literatürde belgelenmiştir, ancak kuyruk riski yüksektir. Repodaki tek kanıt `reports/options-wheel-strategy-test.pdf`: 14-28 Mayıs 2025 arasındaki iki haftalık paper trading raporu; bu istatistiksel olarak anlamsız bir süre. Sembol listesi AAL, INTC, MP, PLTR gibi yüksek oynaklıklı hisseler içeriyor; çöküşte atanan hisse için koruma yok. Kod temiz ve modüler, kurulum belgelenmiş.

**Çalıştırma:** `uv venv && source .venv/bin/activate && uv pip install -e .`; `.env` dosyasına Alpaca anahtarları (paper) yazılır, `config/symbol_list.txt` ve `config/params.py` düzenlenir, ilk çalıştırma `run-strategy --fresh-start --strat-log`, sonra cron ile günde birkaç kez `run-strategy`.

---

## Elenenler

### Kripto (bot, market making, grid/DCA, funding, DEX)
- **Rikj000/MoniGoMani** (1027 yıldız): "Isn't that what we all want? Our money to go many?" pazarlama tonu, sinyal ağırlıklarını hyperopt ile bulmaya dayalı ve aşırı uydurmaya açık çerçeve yapısı ve 2023'ten beri güncellenmemesi nedeniyle elendi.
- **financial-astrology-research/jesse-astrology-trading-strategy** (112 yıldız): Gezegen döngülerine dayalı sinyaller bilimsel bir temele sahip değil.
- **IrakliXYZ/ARBOT** (38 yıldız): Spot-vadeli fonlama arbitraj botu, ancak kapanmış FTX borsasına bağımlı ve lisanssız.
- **godzilla-foundation/godzilla-community** (385 yıldız): Fonlama arbitrajı için C++/Python altyapısı; somut bir strateji kodundan çok bir motor.
- **counterfactual5/funding-arb** (11 yıldız): Çok yeni (2026-11-07 güncellenmiş) ve 11 yıldızlı; kullanım ve canlı geçmişi değerlendirilemediği için elendi.
- **coindataschool/univ3lp** (15 yıldız): Uniswap v3 LP analiz notebook'ları ve ARIMA tahminleri; çalıştırılabilir bir LP yönetim stratejisi değil.
- **yogi-bo/uniswap-v3-online-framework** (11 yıldız): Go simülatör çerçevesi, yalnızca statik ve iskelet strateji örnekleri içeriyor.
- **juanfp02/Avellaneda-Stoikov-Crypto-MarketMaking**, **FrancescoMangia/avellaneda-stoikov-crypto** (9 ve 6 yıldız): Ders projesi düzeyinde notebook'lar; hftbacktest örnekleri aynı konuyu çok daha gerçekçi işliyor.
- **tfrmma/game-theory-trading-strats** (14 yıldız): SAC/PPO ajanıyla AS parametresi optimizasyonu iddiası; az yıldızlı ve doğrulanabilir sonuç yok.
- **PeetCrypto/freqtrade-stuff** (338 yıldız): Başka yazarların stratejilerinin derlemesi, büyük kısmı NostalgiaForInfinity ve Cluc türevi; 2022'den beri güncellenmiyor.
- **ssssi/freqtrade_strs ClucHAnix ve Archive klasörü**: Cluc/BinHV ailesinin hyperopt edilmiş kopyaları; E0V1EN zaten temsil ediyor.
- **werkkrew/freqtrade-strategies archived klasörü** (Schism, Hacklemore vb.): Yazar tarafından terk edilmiş ve Solipsis ile yerini bulmuş sürümler.
- **nateemma NNPredict ve TSPredict ailesi**: Yazarın kendi notuna göre "her model tek başına zarar ediyor" ve "maliyet sonrası hiçbir tahmin yaklaşımı çalışmıyor".
- **Vukkk/Strategy-BTC-WeakHandsBuster**, **mqhub/Strategy-USDT-BullRunRider**: Superalgos'un 2019-2020 eski format stratejileri; güncel sürümü Sparta-WHB olarak incelendi.
- **Superior-Trade/trading-terminal** (1071 yıldız): "AI trading terminal" ürünü, somut strateji kodu değil.
- **jesse-ai/awesome-jesse** (86 yıldız): Liste reposu; içindeki stratejiler (ysdede, gabrielweich) ayrı olarak incelendi.
- **aoki-h-jp/funding-rate-arbitrage dışındaki fonlama tarayıcıları** (vvonha/crypto-trading-tools, Flotapponnier/funding-radar): Yalnızca uyarı ve tarama yapıyor, test ve maliyet modeli yok.

### Hisse, ETF, varlık dağılımı ve opsiyon
- QuantConnect/Lean IndexOptionIronCondorAlgorithm.py: yalnızca 2 aylık (2019-09 ile 2019-11) bir SPXW combo emir demosu; strateji kanıtı yok.
- QuantConnect/Lean VIXDualThrustAlpha.py: adına rağmen VIX değil SPY işliyor, k1=k2=0,63 optimize edilmiş görünüyor ve ücret sıfır; Dual Thrust zaten listede.
- QuantConnect/Lean RebalancingLeveragedETFAlpha.py: kaldıraçlı ETF aşınma fikrinin tekrarı, UGLD/DGLD girişiyle aynı zayıflıklar.
- je-suis-tm/quant-trading London Breakout: yalnızca GBPUSD spot döviz (kapsam dışı), tek günlük grafik ve backtest istatistiği yok.
- je-suis-tm/quant-trading Options Straddle: tek bir STOXX50 vadesi için tek işlem ve sabit `threshold=2`; backtest değil, örnek hesap.
- letianzj/QuantResearch mebane_faber_taa.py: Faber'ın 10 aylık SMA kuralı yerine 20/200 günlük SMA kesişimi kullanıyor, kaynağa sadık değil; pyTAA girişi daha doğru.
- letianzj/QuantResearch comdty_roll.py: alfa stratejisi değil, CL vadelilerinde roll zamanlaması araştırması.
- jesse-ai/example-strategies IFR2: RSI2'nin kripto için Ichimoku parametreleriyle değiştirilmiş hali; hisse ve ETF kapsamı dışında.
- dacre/AutomaticDualMomentum ve benzeri 0-5 yıldızlı dual momentum repoları: yazar doğrulanamıyor, TuringTrader uygulaması daha eksiksiz.
- leo-aa88/larry_connors_rsi2_bot, ExitAnt-dev connors-rsi2-* repoları: kripto botu ya da yalnızca dağıtım şablonu, çok düşük yıldız.
- mirkovicdev/TSMOM ve diğer küçük TSMOM repoları: rehber ya da öğrenci projesi, Quantpedia uygulaması daha eksiksiz.
- sbauwow/schwagent: yapay zeka destekli bir ajan; strateji kuralları sabit değil ve kanıt yok.
- yudonglu1136/Covered_Call_Backtest, jgQuantScripts/CoveredCallBT: düşük yıldız, yazar doğrulanamıyor; optopsy covered call bu ihtiyacı karşılıyor.
- KalpaTrader/Turn-of-the-Month: Nifty üzerine 2 yıldızlı keşif not defteri, işlem kodu yok.
- mementum/backtrader samples: motor örnekleri, somut strateji değil.

### İstatistiksel arbitraj ve ML/RL
- bradleyboyuyang/Statistical-Arbitrage (289 yıldız): Ders projesi düzeyinde OU tabanlı intraday pairs defteri; eşik analizi örneklem içinde yapılıyor, eğitim/test ayrımı ve maliyet kodu yok, ticker'lar anonim.
- hudson-and-thames/meta-labeling (105 yıldız, lisans yok): Sentetik veriyle meta-labeling araştırma kodu; gerçek piyasa verisinde çalışan bir strateji değil.
- hudson-and-thames/arbitragelab (doğrudan): Strateji değil kütüphane; çalıştırılabilir örnekler arbitrage_research reposundan alındı.
- financialnoob/pairs_trading (350 yıldız): Blog eşliğinde 23 araştırma defteri (kopula, OU, Markov rejim); lisans yok ve çoğu defter örneklem içi parametre seçimiyle tekil analiz, paketlenmiş strateji değil.
- nautilus_trader `architect_ax_mean_reversion` (Bollinger + RSI): Tek varlıklı teknik ortalamaya dönüş; istatistiksel arbitraj ya da ML içermiyor.
- nautilus_trader diğer örnekleri (ema_cross, grid_mm, orderbook_imbalance, delta_neutral_vol): Piyasa yapıcılık ya da basit teknik örnekler, bu raporun kapsamı dışında.
- FreqAI RL ajanları (`ReinforcementLearner`, `freqai_rl_test_strat.py`): Repoda yalnızca test stratejisi olarak var, belgelenmiş bir örnek strateji yok; FreqaiExampleStrategy girişi altyapıyı zaten kapsıyor.
- notadamking/RLTrader (1866 yıldız): Son güncelleme 2022-01-22; bakımsız ve örneklem dışı kanıt sunmuyor.
- Personae, deep_trader, deep-trading-agent, crypto-rl gibi eski RL repoları: 2018-2022 arasında terk edilmiş, bağımlılıkları kırık, örneklem dışı kanıt yok.
- benstaf/FinRL_DeepSeek (331 yıldız): FinRL ensemble girişiyle aynı altyapının bir varyantı; son güncelleme 2025-04-08 ve kod ayrıntılı incelenmedi.
- Avellaneda-Lee aramalarında çıkan küçük PCA stat-arb repoları (valentin-mnd-77/statarb-avellaneda-lee, lucaspaulien/pca-stat-arb vb.): 0 yıldızlı, tek kişilik öğrenci çalışmaları; doğrulanabilir kalite yok.
- lukstei/trading-backtest (352 yıldız): Java tabanlı Kalman pairs örneği; 2021'den beri güncellenmiyor ve arbitragelab girişi aynı mantığı daha okunaklı veriyor.
- maxlamberti/time-series-momentum (137 yıldız): Son güncelleme 2020-04-26, lisans yok; derin momentum için Oxford-Man ekibinin kendi kodu daha güçlü bir kaynak.
- markdregan dışındaki Lopez de Prado repoları (BlackArbsCEO/Adv_Fin_ML_Exercises, emoen/Machine-Learning-for-Asset-Managers vb.): Kitap alıştırmaları, uçtan uca çalıştırılabilir strateji değil.

### Forex, vadeli/CTA, Pine Script ve kurum örnekleri
- ErikHendriks/londonBreakoutStrategy (5 yıldız): Londra kırılımı için QuantConnect kodu, ancak giriş için stop emri yerine limit emir kullanıyor (fiyatın üstündeki alış limiti hemen dolar), SL ve TP girişten bağımsız ve OCO olmadan konuyor, backtest yalnızca 2 hafta.
- MHZardary/london-strategy-backtest, Naoghuman/MQL5_Strategy_Session_BreakOut_London, 964quanyuan/fx-strategy: 1 ile 6 yıldız, belgelenmemiş kişisel denemeler, öncelik verilmedi.
- man-group (dtale, arctic, ArcticDB, notebooker, mdf): Man Group'un açık kaynak repoları altyapı ve veri araçlarıdır, strateji içermiyor.
- AQR: GitHub'da AQR'ye ait strateji kodu yayımlayan bir organizasyon bulunamadı; AQR'nin veri kütüphanesi web sitesinde Excel/CSV olarak sunuluyor, çalıştırılabilir strateji değil.
- Two Sigma (twosigma organizasyonu): Repolar mühendislik araçları (ör. Flint, BeakerX), strateji yok.
- RussellDash332/WQ-Brain, YHYYDS666/WorldQuant-Brain-Alpha: WorldQuant BRAIN platformuna alfa gönderen otomasyon araçları, strateji mantığı veya bağımsız backtest yok.
- alexisdpc/WorldQuant-alpha-trading: Yalnızca iki markdown dosyası, çalıştırılabilir kod yok.
- Miasyster/QuantGPT, QuantML-Research/wq-alpha-research, lavender1203/worldquant-alpha-aiac, singlebridge/WorldQuant-miner: LLM ile alfa üretimi; ML/LLM kapsamı başka ajanda.
- cs224/andreas_clenow_trading_evolved: Clenow kitabı için ortam ve veri yükleme kurulumu, strateji kodu içermiyor.
- QuantConnect/Lean içindeki Framework alfaları (EmaCrossAlphaModel, MacdAlphaModel, RsiAlphaModel, ConstantAlphaModel): Çerçeve yapı taşları, kendi başına strateji değil.
- alpacahq/gamma-scalping (165 yıldız): Opsiyon delta hedge şablonu, bu bölümün klasik forex/vadeli odağı dışında kaldı ve okunmadı.
- everget/tradingview-pinescript-indicators (955 yıldız): Yalnızca gösterge, strateji (`strategy()`) içermiyor.
- just-nilux/awesome-tradingview, pinecoders/pine-utils: Liste ve kod parçacıkları, strateji değil.
- geraked/tradingview (104 yıldız): Aynı yazarın Pine sürümleri; MT5 tarafındaki grid bağımlılığı nedeniyle ayrıca incelenmedi.
- DaviddTech/ai-trading-agent, TreborNamor/TradingView-Machine-Learning-GUI: AI/ML kapsamında ve pazarlama ağırlıklı.
- foeed/FvgGold-EA, MrOwl1011/Smc_ZOB_CISD, BAKOME-Hub/BakomeTrinityEA, ibadnarpatih-create/XAUUSD-Auto-Trader-MQL5: "Smart money", "professional" gibi pazarlama dili, bağımsız doğrulanabilir test yok, düşük yıldız.
- abiodunaremu/openea: Harici bir AI sinyal servisine (FxChartAI) bağlı EA, strateji mantığı repoda değil.
- zhenghaobaby/UBS-A-Composite-FX-Strategy-of-Pairs-and-Carry-Trading ve diğer FX carry repoları (spantaleoni, lanteignel93, JackMansfield2019): 1 ile 6 yıldız, öğrenci ödevi düzeyinde, carry için güvenilir ve bakımı yapılan bir açık kaynak örnek bulunamadı.
- Kevin Davey: GitHub'da kendisine ait doğrulanabilir bir strateji reposu bulunamadı (arama yalnızca isim benzerliği olan alakasız hesaplar döndürdü).
- mementum/backtrader: Kütüphane; içindeki örnekler basit SMA gösterimleri, ayrıca incelenmedi.
