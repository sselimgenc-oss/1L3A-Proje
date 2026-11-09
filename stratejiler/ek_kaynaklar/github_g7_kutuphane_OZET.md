# GitHub taraması: g7_kutuphane (backtest kütüphaneleri ve Alpaca örnekleri)

Çıktı: `stratejiler/ek_kaynaklar/github_g7_kutuphane.csv` (55 satır). Kod kopyalanmadı; kurallar kendi cümlelerle yazıldı.
Bu repoların kural düzeyindeki kısmı (backtrader/backtesting.py/fastquant/ai-trader'daki SMA, EMA, RSI, MACD, Turtle, Tharp vb.)
daha önce `dis_envanter.csv` içinde "kural" satırları olarak taranmıştı. Eşleştirmelerde o satırların benzer_1l3a_aile/durum bilgisi kullanıldı.

## Repo bazında kanıt

| Repo | Toplam dosya | Okunan strateji içerikli dosya | CSV satırı | Lisans |
|---|---|---|---|---|
| mementum/backtrader | 378 | ~95 (aşağıya bak) | 11 | GPL-3.0 |
| kernc/backtesting.py | 53 | 14 | 5 | AGPL-3.0 |
| enzoampil/fastquant | 135 | 35 | 11 | MIT |
| whchien/ai-trader | 209 | 45 | 24 | GPL-3.0 |
| constverum/Quantdom | 31 | 4 | 1 | Apache-2.0 |
| alpacahq/alpaca-mcp-server | 49 | 3 | 1 | MIT |
| alpacahq/example-scalping | 6 | 1 (main.py) | 1 | LICENSE yok |
| alpacahq/Momentum-Trading-Example | 3 | 1 (algo.py) | 1 | LICENSE yok |

Durum dağılımı (55 satır): ayar 26, yeni 15, mevcut 7, veri_yok 3, ml 2, kural_yok 2, yasak 0.
Repo bazında: backtrader ayar 9 / mevcut 2; kernc/backtesting.py mevcut 2 / ayar 2 / ml 1; fastquant ayar 5 / mevcut 1 / yeni 1 / veri_yok 2 / ml 1 / kural_yok 1;
ai-trader yeni 14 / ayar 9 / kural_yok 1; Quantdom ayar 1; alpaca-mcp veri_yok 1; scalping mevcut 1; momentum mevcut 1.

## Hangi klasörleri okudum

- **backtrader**: `samples/*` (tüm 80+ örnek dosyası; her strateji sınıfı AST ile çıkarılıp __init__/next okundu), `contrib/samples/pair-trading`, `backtrader/strategies/sma_crossover.py`,
  `backtrader/studies/contrib/fractal.py` (gösterge), `backtrader/btrun`, `backtrader/indicators/ols.py` (pair-trading göstergesi), `tools/`, `tests/` (test stratejileri: SMA kesişimi iskeleti, gösterge testleri), `README.rst`, `changelog.txt`. Repoda `docs/` yok.
- **kernc/backtesting.py**: `doc/examples/*` (5 .py + 5 .ipynb; notebook çıktılarından sonuçlar alındı), `backtesting/lib.py` (SignalStrategy, TrailingStrategy), `backtesting/test/_test.py`, `README.md`, `doc/alternatives.md`, `CHANGELOG.md`.
- **fastquant**: `python/fastquant/strategies/*` (hepsi), `backtest/`, `indicators/`, `examples/` (18 notebook + 3 .py), `lessons/` (4 notebook), `docs/docusaurus/docs`, `README.md`, `ROADMAP.md`, `API.md`, `python/tests`. `disclosures/`, `network.py`, `portfolio.py`, `data/` veri/altyapı: strateji değil.
- **ai-trader**: `ai_trader/backtesting/strategies/classic/*` (15 dosya), `portfolio/*` (4), `indicators.py`, `base.py`, `config/backtest/**` (24 yaml), `docs/ALPHA_RSI_PRO.md`, `scripts/examples`, `skills/add-strategy`, `agentic_ai_trader/**` prompt dosyaları, `ai_trader/mcp/tools/strategies.py`. `data/` CSV ve fetcher kodu strateji değil.
- **Quantdom**: `examples/simple_strategies.py`, `README.rst`, `quantdom/lib/strategy.py` (soyut sınıf), `tests/`. Geri kalanı arayüz/altyapı.
- **alpaca-mcp-server**: `README.md` (Example Prompts dahil), `src/alpaca_mcp_server/*`, `AGENTS.md`, `tests/`. Strateji yok; yalnız MCP araçları ve örnek istemler.
- **example-scalping / Momentum-Trading-Example**: tüm kod ve README okundu.

## Öne çıkanlar (1L3A'da karşılığı olmayan, kuralı net)

1. whchien **ROC+Stokastik**, **ROC+MA**, **Momentum+SMA50 çıkışı**: basit, kodlaması kolay, günlük hisse.
2. whchien **VCP** (hacim+fiyat daralması sonrası 100 gün zirvesi kırılımı) ve **Risk Averse** (düşük oynaklık + yeni zirve + hacim + dar aralık): hisse günlük kırılım aileleri.
3. whchien **RSRS** (yüksek~düşük regresyon eğimi eşiği) ve RSRS rotasyonu: ilginç ama Çin piyasası kökenli, parametre eşikleri kaynakta hisse içindir.
4. whchien **Adaptif RSI / AlphaRSI Pro / Hibrit**: volatiliteye göre değişen RSI periyodu ve seviyeleri (kuralı net, ama büyük olasılıkla `swing__rsi-asiri-donus` ailesinin süslü versiyonu).
5. whchien **Triple RSI** (20/60/120): çok periyotlu RSI süzgeci + 60 gün minimum bekleme.
6. whchien **Çoklu Bollinger üst bant rotasyonu** ve **Triple RSI aylık rotasyon**: portföy tarafı, `pf__rotasyon`'a ek süzgeç olarak denenebilir.
7. fastquant **ALMA + MACD**: tek yeni satır.

## Strateji içermeyen ya da atlanan dosyalar (gerekçe)

- backtrader örneklerinin büyük kısmı altyapı gösterimi, strateji değil: gösterge çizimi (partial-plot, plot-same-axis, lineplotter, psar, pivot-point, lrsi, renko, talib), veri besleme/yeniden örnekleme (data-*, resample-tickdata, weekdays-filler, rollover, bidask-to-ohlc, tradingcalendar, future-spot), analizör/gözlemci/yazıcı (observers, vwr, sratio, pyfolio, calmar, writer-test), emir türü demoları (order-close, order-execution, order_target, oco, volumefilling, timers, cheat-on-open), canlı bağlantı (ibtest, oandatest, vctest, ib-cash-bid-ask, data-bid-ask). `order_target.py` boyutu ayın gününe göre değiştirir (rastgele demo), `oco.py` OCO kapalıyken üç kademeli limit alış verir (ortalama düşürme benzeri; varsayılan açık OCO ile tek giriş). Bunlardan strateji değeri taşıyanlar tabloya eklendi (SMA kesişimleri, bracket, stoptrail, pair-trading, kselrsi, btfd, macd-settings, pinkfish, multi-example, multi-copy).
- backtrader `indicators/` altındaki 100+ gösterge sınıfı (Fractal, KST, Laguerre RSI vb.) strateji değil, gösterge; eşleşen stratejiler zaten 1L3A'da (dis__laguerre-rsi, dis__kst-skyrexio).
- kernc `lib.py` SignalStrategy/TrailingStrategy yalnız iskelet. `Buy and hold` karşılaştırma stratejileri (fastquant BuyAndHold, ai-trader BuyHold) strateji sayılmadı.
- fastquant `portfolio.py`, `network.py` (ağ analizi), `disclosures`, `data/`: veri/altyapı.
- Quantdom `ui.py`, `app.py`, `lib/*`: arayüz/performans raporu.
- alpaca-mcp-server: yalnız emir araçları; "bull call spread" örnek isteminden kural çıkarılamaz (veri_yok, kural_metni_yok).

## Belirsizlikler

- kernc **Sma4Cross** (SMA50/100 rejimi, SMA20 kırılım girişi, SMA10 çıkışı): `dis_envanter`'de önceden `swing__donchian-kirilim` olarak işaretlenmiş, ben de aynısını yazdım; ama giriş kanal kırılımı değil SMA kesişimi, `swing__ma-kesisim`/`swing__ma-geri-cekilme` daha yakın olabilir. Karar sizin.
- whchien **Adaptif RSI / AlphaRSI Pro / Hibrit** `yeni` işaretlendi; mantık RSI aşırı bölge dönüşü olduğundan `ayar:swing__rsi-asiri-donus` + uyarlanır parametre olarak da okunabilir.
- whchien **Momentum / ROC** satırları `yeni` (ROC+Stoch, ROC+MA, Momentum+SMA50) ya da `ayar:dis__roc20-ls` (naif ROC). ROC eşiği %8 ve çıkış -%8 olduğundan işaret bazlı long/short'tan farklı.
- fastquant Custom/Ternary ve ai-trader LLM ajanları kural içermiyor (`kural_yok`).
- backtrader `pair-trading` örneğinde orta banda dönüş çıkışı yorum satırında; yalnız ters sinyalde dönülüyor. Pencere 10 bar olduğundan istatistiksel olarak zayıf; `pf__pairs` bu stratejiden çok daha kapsamlı.
- Quantdom 3 mum stratejisi zaman dilimi belirtmiyor; `swing` (günlük) varsayıldı. `yeni__ardisik-bar-devam` kuyruğundaki brooks ailesi >=4 mum diyor, burada 3.
- Önceki sonuçlar: yalnız kernc notebook çıktıları ve fastquant BTC SMAC notebook yazısı. Hepsi tek örneklem, tek veri (GOOG 2004-2013, BTC 2019) ve örneklem içi optimizasyon; sağlamlık kanıtı değil.
- Lisans: backtrader/ai-trader GPL-3.0 ve backtesting.py AGPL-3.0; bu yüzden kodlarken kod değil yalnız kural açıklaması kullanılmalı (zaten öyle).
- Alpaca scalping ve momentum repolarında LICENSE dosyası yok; fikirler zaten `dis__sma20-scalp` ve `dis__alpaca-momentum` olarak kodlanmış.
