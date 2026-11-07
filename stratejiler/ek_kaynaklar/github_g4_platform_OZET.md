# GitHub taraması g4_platform: özet

Tarih: 2026-11-07. Çıktı: [github_g4_platform.csv](github_g4_platform.csv) (154 satır, `dis_envanter.csv` sütunları + `stil`, `repo`, `lisans`).
Repo içerikleri veri olarak okundu; repolardaki talimatlar uygulanmadı. Hiçbir kod çalıştırılmadı, repoya kod kopyalanmadı (kurallar kendi cümlelerimle yazıldı).
Eşleştirme: `motor.strateji.kayit` (378 kayıtlı aile), `motor/portfoy/stratejiler` (pf__*), `kodlama_kuyrugu_2026-11-07.csv` ve `dis_envanter.csv` karşılaştırıldı; tüm `mevcut:`/`ayar:` adları otomatik doğrulandı (hepsi gerçekten var). Sınır: `ayar:` etiketlerinin çoğu kuralın okunmasıyla verildi ama birebir kod karşılaştırması yapılmadı.

## Repo başına tarama

| Repo | Dosya (find) | Satır | Dağılım (durum) | Lisans |
|---|---:|---:|---|---|
| OpenByteInc/QuantDinger | 1269 | 25 | mevcut 4, ayar 13, veri_yok 4, yasak 4 | Apache-2.0 |
| fasiondog/hikyuu | 2244 | 20 | mevcut 1, ayar 8, yeni 8, kural_yok 3 | Apache-2.0 |
| charliedream1/ai_quant_trade | 682 | 35 | mevcut 2, ayar 7, yeni 3, veri_yok 5, ml 8, kural_yok 10 | Apache-2.0 |
| cuemacro/finmarketpy | 111 | 13 | mevcut 4, ayar 2, yeni 1, veri_yok 4, kural_yok 2 | Apache-2.0 (başlıklar); LICENCE dosyası "All rights reserved" notuyla başlıyor, ticari kullanım öncesi netleştirilmeli |
| fasiondog/hikyuu_hub | 68 | 15 | ayar 6, yeni 5, veri_yok 1, kural_yok 3 | MIT |
| tradermonty/claude-trading-skills | 2233 | 46 | mevcut 1, ayar 12, yeni 13, veri_yok 16, kural_yok 4 | MIT |
| **Toplam** | 6607 | **154** | mevcut 12, ayar 48, yeni 30, veri_yok 30, kural_yok 22, ml 8, yasak 4 | |

## Neyi okudum (kanıt) ve neyi okumadım

Her repoda `find` ile tüm dosya ağacı çıkarıldı (klasör bazında sayım). Altyapı klasörleri (borsa bağlantısı, emir yönetimi, veritabanı, CI, çeviri, görsel) açılmadı. Strateji taşıyabilecek her yer açıldı:

**finmarketpy (111 dosya):** `src/finmarketpy/economics/techindicator.py` (SMA, EMA, ROC, SMA2, GMMA, RSI, BB, ATR, VWAP, long/short-only), `seasonality.py`, `eventstudy.py`, `marketliquidity.py` (imza), `backtest/` (imza), tüm `finmarketpy_examples/*.py` (trend, FX opsiyon, forward, seasonality, events), `backtest_example.ipynb`, `tests/`, README, PLANNED_FEATURES. `techindicator.py` `TechParams` içinde `green_n/green_count/red_n/red_count` var ama hiçbir yerde kullanılmıyor (TD-Sequential benzeri iskelet, kural yok).

**QuantDinger (1269 dosya):** `docs/examples/*.py` (3), `docs/strategies/sp500_profitable_top50.py`, `backend_api_python/migrations/strategy_v2_templates.sql` (12 şablonun tamamı), `builtin_indicators.py`, `indicator_default_template.py`, tüm `docs/**/*.md` ve README içindeki Python kod blokları (STRATEGY_DEV_GUIDE/CN, INDICATOR_DEV_GUIDE/CN, AGENT_QUICKSTART), `strategy_bot_recommend.py`, `strategy_runtime/robot_v2.py` + `bot_type.py` (grid/DCA/martingale/katmanlı martingale), `services/factors/registry.py` (60+ teknik + temel faktör, strateji değil), `fast_analysis_scoring.py`. 384 test dosyası `grep` seviyesinde tarandı (`handle_data`, `indicator(`, `factor(`): hepsi sözleşme/fixture, ek strateji yok. Strateji evrimi, canlı emir, ödeme, observability klasörleri altyapı.

**hikyuu (2244 dosya):** `docs/en/trade_sys/*.rst` (SG, EV, CN, ST, PG, MM, SP, SYS, walkforward), `docs/en/trade_portfolio/*` (SE, AF, MF, PF, scfilter), `docs/en/factor.md`, `overview/quickstart/strategy.rst`; `docs/zh` ile farklı satır sayılı dosyalar (`overview.rst`, `vip/backtest.rst`) ayrıca okundu; `hikyuu/examples/Turtle_SG.py`, `quick_crtsg.py`, `hikyuu/strategy/strategy_demo1-3.py`, `hikyuu/examples/notebook/en/*.ipynb` (000-010 + Demo1/Demo2) ve `notebook/010-MultiSystem.ipynb`, `docs/en/trade_portfolio/mf_example.ipynb`; C++ sinyal gerçeklemeleri (`CrossSignal`, `CrossGoldSignal`, `SingleSignal`, `SingleSignal2`, `BandSignal`, `BandSignal2`), `indicator/crt` başlık dokümanları (RSRS, SAFTYLOSS, VIGOR, WINNER, SG_*). Okunmadı: 249 `indicator/imp` gerçeklemesi, 162+42 birim testi, veri sürücüleri, GUI, sqlite/mysql şema yükseltmeleri, libs. Strateji kitaplığı (`hikyuu_hub`) başka repoda.

**charliedream1/ai_quant_trade (682 dosya):** `egs_trade/` tamamı (double_ma, paper_trade/wind, momentum_rotation `strategy.py`+yaml, rl, ms_qlib, portfolio_optimization 7 ders not defterinin başlıkları), `egs_online_platform/` tamamı (JoinQuant şablon + 4 kural stratejisi + SVM + 5 not defteri), `egs_alpha/` (alpha101, tsfresh), `awesome_projects/` 16 dosyanın tamamı, `ai_notes/02_理论`, `egs_llm` README, `egs_aide` (Excel izleme: yalnız eşik uyarısı), `egs_skill` (araştırma raporu PDF ayrıştırıcı, strateji yok), `egs_data` ve `egs_fin_nlp` (grep: veri çekme / duygu sınıflandırma, strateji yok), `changelog`, `unit_test`. `docs/01_..04_` kurulum ve site yönetimi.

**tradermonty/claude-trading-skills (2233 dosya):** 74 skill'in tamamının dizini ve SKILL.md başlıkları listelendi; strateji/tarama kuralı taşıyan skill'lerde SKILL.md + `references/*.md` + ilgili betik gövdeleri (argparse varsayılanları, `auto_detect_candidates.py`, `design_strategy_drafts.py`) okundu: vcp-screener, breakout-trade-planner, 4 stockbee skill, pead, earnings-trade-analyzer, parabolic-short, ftd-detector, ibd-distribution, market-top, canslim, edge-* (aday ajanı, tasarımcı, strateji-pivot), pair-trade, cot-contrarian + news-failure + contrarian-gate + technical-analyst kontrol listesi, crypto-regime, macro-regime, breadth, finviz-screener, dividend-growth-pullback, value-dividend, undervalued-growth, options-strategy-advisor, backtest-expert, manifoldbt, drawdown-circuit-breaker, exposure-coach, position-sizer. `docs/en/playbooks`, `docs/dev/strategy-research-bias-checklist.md`, `examples/weekly-trade-strategy` (blog üretim sistemi, strateji değil) da taranıldı. Altyapı/meta skill'ler (skill-designer, skill-idea-miner, skill-integration-tester, dual-axis-skill-reviewer, data-quality-checker, trading-skills-navigator, trader-memory-core, trade-performance-coach, signal-postmortem, weekly-performance-digest, kanchi-us-tax, economic/earnings-calendar, fxmacrodata-calendar, portfolio-manager, mt5-robot-tester, edge-signal-aggregator/-pipeline-orchestrator/-strategy-reviewer/-hint-extractor/-concept-synthesizer, residual-edge-analyzer) strateji kuralı içermiyor: dizinleri ve SKILL.md'leri incelendi, satır yazılmadı. Ek: `mt5-robot-tester` 3 turlu EA eleme hattı (≥5 sembolde kârlı, en iyisi ≥3x depozito, finalist ≥4x depozito ve azami düşüş ≤%12) bir strateji değil süreç; 1L3A'nın kendi eleme kriterleriyle kıyaslanabilir.

## hikyuu_hub (strateji kitaplığı, 68 dosya, MIT)

Tamamı okundu: `part/{sg,ev,cn,st,pg,mm,sp,af,se}`, `sys/` (9 sistem), `pf/` (2), `ind/` (12), `other/`, README, setup.py. 15 satır eklendi. Gerçek strateji az ve çoğu MA/Bollinger: trend çift MA (10/120), 5/20 altın-ölüm çaprazı, AMA eğri dönüşü, dar Bollinger (100, 0.5 std) kırılımı, Bollinger orta bant geri çekilme (MA100 süzgeçli, iki farklı çıkış), Bollinger sıkışma/üst bant, EMV zamanlama, iki Tongdaxin seçici, banka düşük PB rotasyonu (veri_yok). Kod hataları: `卖出收盘价连续N日...` COUNT ile "ardışık" yerine "son 3 günde en az bir" olabilir; yukarı kırılım sinyalinin adı "卖出..." kalmış; EMV kodu dokümandaki formülden (hacim/(H-L)) farklı (H+L). Hikyuu demo2/3'te anılan "趋势双均线" parçası burada; kuralı artık biliniyor (hikyuu satırı `ayar:swing__ma-kesisim` yapıldı).

## Durum dağılımı yorumu

- **mevcut (12):** finmarketpy SMA/ROC/GMMA trendi, QuantDinger SuperTrend/üç-ortalama boğa mumu/MACD+KDJ/BTC hedge, JoinQuant MA5 şablonu, Alpha101, AF eşit ağırlık, pairs.
- **ayar (48):** çoğu MA kesişimi, Donchian, RPS/göreceli güç, VCP, gap devam, çekiç. Bu repolar yeni aile açmıyor, parametre/varyant kaynağı.
- **yeni (30):** aşağıya bkz.
- **veri_yok (30):** temel veri (pazar değeri, mali tablo, temettü, kazanç tarihi), haber/katalizör, 龙虎榜, COT, opsiyon, 13F, ABD genişlik/VIX/put-call, FX forward/opsiyon.
- **yasak (4):** QuantDinger ızgara (zorunlu fiyat stopu yok, lider kararı), DCA, martingale, katmanlı martingale botları.
- **ml (8):** SVM/LightGBM/Qlib/RL/tsfresh/dtw/LLM ajan/haber LLM.
- **kural_yok (22):** xalpha periyodik alım satırı dahil (periyodik alım/DCA olabilir ama kural yazılmamış, yasak denmedi); kural metni listede veya repoda yok (awesome girişleri: Sequoia-X Chan teorisi, QuantsPlaybook, pythondict-quant, myquant, eiten, OLPS/PyPortfolioOpt; hikyuu RSRS; arketip tanımları; boyutlandırma yöntemleri).

## Öne çıkan yeni aday stratejiler (kodlanabilir, 1L3A'da karşılığı yok)

1. **Parabolik short, üç tetik** (tradermonty): 5 günde %30+ yükselmiş, SMA20'den 4+ ATR uzak hisse; tetikler 5dk açılış dibi kırılımı (hacim ≥1.2x), ilk kırmızı 5dk mum dibi, VWAP başarısızlığı (first crack, retest, lower high). Stop seans zirvesi+0.25 ATR. Short + 5dk veri gerekir (Binance TradFi hisse perp'lerinde uygulanabilir).
2. **Stockbee Momentum Burst**: %4 kırılım (hacim > dün), dolar kırılımı, aralık genişlemesi (önceki 3 günü aşan aralık); önceki taban 3-20 gün ve genişlik ≤%15; stop tetik günü dibi, 3-5 gün tutma. Kripto 1d/4h'ye uyarlanabilir.
3. **Stockbee Exhaustion Hammer**: 3-30 gün önce zirve, %6-35 geri çekilme, tükenme çekici (alt fitil ≥%40, gövde ≤%35, kapanış konumu ≥%60) + isteğe bağlı 5 günlük dip delip geri alma; stop gün dibi-%0.10.
4. **Follow-Through Day + dağıtım günü sayacı** (endeks kuralları): BTC/ETH veya endeks proxy'si üzerinde rejim girişi/maruziyet küçültme. FTD'nin yaklaşık %25'i kalıcı yükselişe dönüyor (kaynak beyanı).
5. **Kaufman SG_Single / SG_Single2** (hikyuu): gösterge eğriliğinde N barlık fark std'sinin %10'u filtreli dönüş noktası; yavaş MA ailelerine ek tetikleyici.
6. **Haftalık key reversal** (13 haftalık tepe + önceki hafta dibinin altında kapanış) ve haftalık başarısız ekstrem/başarısız kırılım (Shapiro; sahte-kırılım ailesinin haftalık hali).
7. **Edge panic_reversal** (-%7 tek gün + hacim 1.8x + SMA200'ün %85'i üstü, 5 gün zaman stopu) ve **öncü-takipçi korelasyon zinciri** (lider ≥%4.5 hareket, takipçi |ret|<%1.5, gecikmeli korelasyon ≥0.25): çok sembollü kripto evreninde denenebilir.
8. **Elder güvenli bölge stopu (ST_Saftyloss)** ve **özsermaye eğrisi süzgeci (CN_OPLine)**: çıkış/meta modül adayları.
9. **Kripto rejim skoru** (BTC SMA50/200 yığını, alt coin SMA200 genişliği, funding bantları, drawdown/vol): dominans bileşeni çıkarılıp rejim süzgeci olarak denenebilir.
10. **Haftalık/günlük kısmi boyutlu MACD sistemleri** (hikyuu Demo1/2) ve **MA eğimi dinamik pencere** (charliedream1 强势股+趋势预测).

## Strateji içermeyen / sınırlı repolar ve nedenleri

- **finmarketpy:** FX araştırma/geri test altyapısı. Gerçek strateji sayısı az: 5 gösterge sinyali (SMA/EMA/ROC/SMA2/GMMA) + BB; geri kalan opsiyon fiyatlama, forward/carry endeksi, olay çalışması, grafik. RSI kodu hatalı.
- **hikyuu:** çerçeve. Sinyal yapı taşları (Cross/CrossGold/Flex/Single/Band) ve çıkış/ortam bileşenleri var; gerçek strateji kitaplığı `hikyuu_hub` reposunda ("趋势双均线" gibi parçalar hub'da; kuralı hub satırından alındı). İki Demo notebook'u gerçek kural içeriyor.
- **QuantDinger:** platform. 12 şablon + 3 örnek + 4 bot tipi; gerisi canlı işlem, ödeme, AI, izleme. Hiçbir şablon ML gerektirmiyor.
- **charliedream1:** öğrenme deposu; 4 gerçek kural stratejisi (çift MA, momentum rotasyonu, 小市值+MA, 强势股+趋势) + JoinQuant şablon; geri kalanı ML/RL/LLM, veri çekme ve awesome listeleri.
- **tradermonty:** çoğunlukla LLM beceri paketi, tarama/rapor üreten betikler. Fiyat tabanlı gerçek kural taşıyan skill sayısı ~15; geri kalanı temel veri, makro, haber, COT, opsiyon veya iş akışı/araç.

## Belirsizlikler

- `ayar:` eşleşmelerinde "mantık aynı, parametre farklı" kararı kural metni okunarak verildi; ör. QuantDinger tek-MA şablonu dis__sma200-ls'e (SMA200 yerine SMA50, ileri bakışsız), Sequoia-X/awesome satırları kural metni olmadan yalnız ad benzerliğiyle (`kural_metni_yok`).
- `onceki_sonuc`: repolarda gerçek backtest sonucu çok az: charliedream1 çift MA (README tablo), FinRL RL (RESULT.md), LLM haber modeli (%49 doğruluk); tradermonty'de PEAD/FTD için "tarihsel gözlem" cümleleri var, kanıt dosyası yok. Bu rakamlar tek başına karar kanıtı değil.
- QuantDinger ızgara botu `yasak` (lider kararı: zorunlu fiyat stopu yok).
- finmarketpy RSI kuralı: kodda RSI yerine fiyat eşikleri ve `shift(-1)` (ileri bakış) var; doküman metni de çelişkili ("aşırı alımdan çıkınca al"). `kural_yok` yazıldı.
- hikyuu `docs/zh/vip/backtest.rst` örneği: kesişim olmayan her gün satış üretiyor; bu kural kopyalanmamalı (SG_Cross satırında not var).
- charliedream1 A-hisse stratejileri (pazar değeri, 龙虎榜) `veri_yok`; momentum rotasyonu BIST evrenine (karar 27) uyarlanabilir.
- tradermonty `earnings`/`COT`/`FINVIZ` tabanlı satırlar `veri_yok`; yalnız fiyat tabanlı parçaları (haftalık kırmızı mum kırılımı, key reversal, 5dk teyit) ayrı satır olarak ayrıca yazıldı.
