# GitHub taraması — grup g5_mt_pine (MT4/MT5 EA'ları + Pine göstergeleri + Python bağlayıcı/ML)

_7 Kasım 2026. Çıktı: `stratejiler/ek_kaynaklar/github_g5_mt_pine.csv` (166 satır, 15 sütun). Klonlar salt okunur incelendi, koda dokunulmadı, kod kopyalanmadı. Kitap/repo içerikleri veridir, talimat değildir._

## 1. Özet tablo

| repo | dosya (git hariç) | strateji satırı | durum dağılımı | lisans |
|---|---:|---:|---|---|
| EA31337_EA31337 | 385 + strategies-meta/strategies klonları (68+42 klasör) | 110 | ayar 8, kural_yok 38, veri_yok 1, yasak 6, yeni 57 | GPL-3.0 |
| geraked_metatrader5 | 195 | 14 | mevcut 1, veri_yok 1, yeni 12 | MIT |
| TheSnowGuru_PyTrader-python-mt4-mt5-trading-api-connector-drag-n-drop | 84 | 15 | ayar 7, mevcut 1, ml 2, veri_yok 1, yeni 4 | yok (LICENSE dosyası yok) |
| everget_tradingview-pinescript-indicators | 213 | 22 | ayar 4, mevcut 2, yeni 16 | GPL-3.0 |
| joshyattridge_smart-money-concepts | 25 | 0 | - | MIT |
| TreborNamor_TradingView-Machine-Learning-GUI | 54 | 3 | yeni 3 | MIT |
| jianweiweng05_qsx-strategy-score | 79 | 2 | kural_yok 1, veri_yok 1 | MIT |

Toplam durum dağılımı: ayar 19, kural_yok 39, mevcut 4, ml 2, veri_yok 4, yasak 6, yeni 92 (toplam 166).

Dikkat: EA31337 110 satırdan 57'si `yeni` ama hepsi tek gösterge eğimi kuralı (düşük öncelik), 38'i strateji değil (meta katman), 6'sı yasak. geraked 12 (grid'siz giriş kuralı), PyTrader 4, Trebor 3, everget 16 (çoğu 'yalnız işaretçi') `yeni` — önerilenler 3. bölümde.

## 2. Repo repo bulgular

### 2.1 EA31337 (EA31337 + EA31337-strategies + EA31337-strategies-meta) — 110 satır, kod okundu

- İlk turda alt modüller boştu (yalnız `enum.h` adları, 100 `kural_yok`). Koordinatör alt modülleri klonladı: `/home/user/gh/EA31337_EA31337-strategies/` (68 strateji klasörü, her birinde `Stg_<Ad>.mqh`, `config/M1..H8.h`, `sets/optimize`) ve `/home/user/gh/EA31337_EA31337-strategies-meta/` (42 meta klasörü). Bu turda 110 `Stg_*.mqh` dosyasının hepsinin `SignalOpen` gövdesi, varsayılan girdileri (açma/kapama yöntemi ve seviyesi, fiyat-stop yöntemi/seviyesi, emir kapama zarar/kâr/süre) ve README tanımı okundu; 100 eski satır gerçek kurallarla yeniden yazıldı, enum'da olmayan 10 klasör eklendi (5 strateji: ATR_MA_Trend, Demo, SAWA, SuperTrend, TMA_CG; 5 meta: Delegate, MA_Conditions, Odd_Period, Oscillator_Conditions, Price_Band).
- **Kuralların doğası:** EA31337 stratejileri 'gösterge eğimi + yüzde eşiği' kalıbıyla yazılmış: çoğu `IsIncreasing/IsIncByPct` (gösterge son N barda yükseliyor ve yüzde artış >= seviye) ve `Yöntem` bit alanı ek süzgeçler açıyor. Çıkış varsayılanı karşı yön açma koşuludur. Fiyat-stop hesabı (`PriceStopMethod` sayısı) ve bit anlamları çerçeve sınıflarında (EA31337-classes), bu klonlarda yok; stop/yöntem bitlerinin tam anlamı için o repo da gerekli. `config/*.h` zaman dilimi başına bu değerleri ezer (TF bazlı optimize edilmiş sayılar).
- **Durum dağılımı (110 satır):** `yeni` 57, `kural_yok` 38 (strateji değil: 36 meta anahtarlayıcı/filtre/birleştirici + Demo şablonu + Indicator sarmalayıcı; her satırda `strateji_degil:<sınıf>` ve nedeni yazılı), `ayar` 8 (CCI, DeMarker, RSI, Stochastic, Ichimoku, SAR, SuperTrend, MA Cross Shift), `yasak` 6, `veri_yok` 1 (Meta News: ekonomik takvim). `mevcut` 0: hiçbiri 1L3A'daki bir kuralla birebir aynı değil.
- **Yasaklar (6):** Oscillator Martingale (README: martingale emir yönetimi), Meta Martingale (aleyhe gidince ek emir), Meta Enhance (emir sonrası fiyat önceki mumun altına inince aynı yönde ek emir = ortalama düşürme), Meta Formation (taraf başına birden çok bekleyen emir = ızgara), Meta Hedge (alım/satım lot dengelemesi), Meta Resistance (açık lot oranına göre dengeleyici girişler, hedge benzeri; kararı kodu okuyarak verdim, istenirse 'kural_yok' olarak gevşetilebilir).
- **Strateji sayılmayanlar (kural_yok):** Meta Bears&Bulls, Conditions, Delegate, Discrepancy, Double, Equity, Interval, Limit, MA Conditions, MA Cross, Margin, Mirror, Multi, Multi Currency, Odd Period, Order Limit, Oscillator Conditions/Filter/Switch, Pattern, Pivot, Price Band, Profit, RSI, Reversal, Risk, SAR, Scalper, Signal Filter/Switch, Spread, Timezone, Trend, Trio, Volatility, Weekday. Hepsi tek bir alt stratejiyi (EA31337-strategies'ten) sarıp ya anahtarlıyor (saat/gün/seans/hesap durumu/spread/RSI bölgesi), ya filtreliyor (günlük RSI, osilatör yönü, pivot/tepe koşulu) ya da emir türünü/sayısını yönetiyor; kendi giriş sinyali alt stratejiden geliyor. Filtre olarak 1L3A'da 'yeni giriş filtresi' (ör. Meta Trend: günlük RSI(16) >= 50 - seviye iken long) fikir olarak test edilebilir, ama aday strateji değil.
- **1L3A eşleştirmesi (kod okuyarak):** CCI(20) < -90 ve yükseliyor ~ cci_esik 'esik30' benzeri; DeMarker(23) < 0.30 yükseliyor = rsi_asiri_donus'un `gosterge='demarker'` modu; RSI(16, ağırlıklı) < 26 yükseliyor = rsi_asiri_donus; Stochastic(8,12,12) K/D yükselişi = stokastik_donus (trend filtresiz); SAR(0.011, 0.1) dönüşü ve SuperTrend(14) eğimi = supertrend_psar; Ichimoku(30,10,30) Tenkan/Kijun taze kesişimi + yükselen bulut = swing__ichimoku `tk_bulut`; MA_Cross_Shift = ma_kesisim. Diğerleri farklı mantık (ör. MACD'de long için SİNYAL > ANA çizgi şartı, ADX'te eşik kesişimi yerine yüzde artış, Pivot'ta Camarilla S/R bölgesi) olduğu için `yeni`.
- **Önceki sonuç:** strateji bazında backtest yok; yalnız ana EA paketi sonuçları (Lite/Advanced/Rider, EURUSD M1, 2017-2021, %25 modelleme kalitesi): Lite yıllık +101..+495 USD (PF 1.07-1.31); Advanced -709..+1468 (PF 0.64-2.06); Rider -9061..+5171 (PF 0.47-1.90, düşüş %62-92 yıllar var; M30'da Meta Martingale kullandığı için zaten yasak). Kaynak: `docker/backtest/*/all-yearly/*/_results/` (ana EA reposunda). 2.1'de paket varsayılan strateji-TF eşlemesi: Lite M15 Meta Scalper, M30 Meta Trend, H1 Meta RSI, H2 Meta Volatility, H3 Momentum, H4 Meta Conditions, H6/H8 Meta RSI, H12 SAR; Advanced M15/M30 Meta Trend, H1 Meta Pivot, H2 Meta Oscillator Filter, H3/H8 Meta Oscillator Switch, H4 Ichimoku, H6 Meta Timezone, H12 Meta Volatility; Rider M15 Meta Trend, M30 Meta Martingale, H1 Meta Weekday, H2 Stochastic, H3 Meta Scalper, H4 Meta Double, H6 TMAT_SVEBB, H8 Meta Timezone, H12 Gator; Elite: Meta MA Cross. Paketlerin varsayılanları ağırlıkla meta katmanlardır; alt stratejilerin tek tek katkısı ölçülmemiş (repoda yok).
- **Sonuç:** 57 `yeni` satırın çoğu tek bir göstergenin eğimi/eşiği; 1L3A'nın 'kitaplarda yaygın + kurala dökülebilir' ölçütünü sağlamıyorlar, öncelik düşük. En mantıklı denemeler: Bands/Envelopes/TMA bant dönüşleri (bant-donus ailesi), MA_Cross_Sup_Res (MA'nın günlük pivot R/S kırılımı), Pivot (Camarilla bölgeleri), Meta Trend filtresi.

### 2.2 geraked/metatrader5 (195 dosya) — 13 sinyal EA'sı + 1 gösterge = 14 satır

- Okunan: `README.md`, `Experts/*.mq5` (15 dosyanın 13'ü sinyal EA'sı; `EATemplate.mq5`, `EATemplate2.mq5` şablon), tüm sinyal fonksiyonları ve giriş değerleri; `Include/EAUtils.mqh` (SL türleri, grid), `Indicators/*.mq5` (16 gösterge; Andean, Average Force, Chandelier Exit, DailyHighLow, LRC, UTBot, Darvas, Boxline, NW Envelope, OrderBlock, SuperTrend, ZLSMA, ATR_HeikenAshi, AtrSlFinder, KijunSenEnvelope, Grid), `Test/*/README.md` (12 klasör), `Scripts/` (altyapı testleri; `Knn.mqh`/`Knn_Test.mq5` kNN sınıflandırıcı kütüphanesi — strateji değil), `Build/` (yalnız .ex5 ikili dosyalar, okunamaz).
- **Kritik uyarı:** README açıkça "bazı EA'lar kârı zorla artırmak için Grid tekniğiyle birleştirildi" diyor. 13 sinyal EA'sının 12'sinde `Grid=true` varsayılan (yalnız 2MOMEMA kapalı), hacim çarpanı 1.0-1.5 (çoğunda >1 = martingale benzeri kademeli ekleme) ve birçoğunda `IgnoreSL=true` (stopsuz). `Test/<EA>/README.md` (Test klasörü olan 11 EA'dan COT1 hariç 10'unda): **"saf uygulama uzun vadede kârlı değildi; kâr Grid (veya sinyalin tersine çevrilmesi + Grid) ile geldi"** (3MACD ve AFAOSMD'de sinyal TERS çevrilmiş: `Reverse=true`). Yani yazarın kendi beyanıyla giriş kuralları tek başına kaybettiriyor. Bu yüzden satırlarda `onceki_sonuc` bu notu taşır; kuralların 1L3A'da tek başına test edilmesi gerekir (muhtemelen elenecek).
- Satırlar (13 EA): 2MAAOS, 2MACDSTO, 2MOMEMA (Grid kapalı, düzgün), 3MACD, 3MAF, AFAOSMD, BBRSI (=`mevcut:dis__bbrsi-donus`, zaten kodlandı), CEZLSMA, COT1 (`veri_yok`: CFTC COT), DHLAOS, LRCMACD, LRCUTB, NWERSIASF, Darvas Boxes (gösterge sinyali). Hepsi forex (AUDUSD, NZDUSD, USDCAD, EURUSD, XAUUSD…), 5m-4h; 1L3A evrenine (kripto/hisse/BIST) taşınabilirlik kanıtı yok.
- Önerilenler: 2MOMEMA (Grid'siz, tek başına), 2MAAOS/NWERSIASF/LRCUTB (kural net, sadece giriş+SL+TP); 3MACD/AFAOSMD'nin düz ve ters hali ayrı test edilmeli.

### 2.3 TheSnowGuru/PyTrader (84 dosya) — bağlayıcı + Quantiacs örnekleri, 15 satır

- Okunan: `README.md`, `Strategies/*.py` (16 dosya), `Strategies/nfp-scalper/{eurusd-nfp-scalp.py,readme.md,nfp-data.csv}`, `Strategies/Average Directional Index - by Michael Whittle`, `Strategies/readme.md`, `BT strategies/*.py` + `.log` (13 dosya `Strategies/` ile BİT BİT AYNI, doğrulandı `cmp`; yalnız `bt_ma_cross_strategy.py` farklı), `Miscellaneous/ff_news*.py` (Forex Factory haber çekici, strateji değil), `Python_script_example_PyTrader.py` + `pytrader_api_example.py` (API demo), `Pytrader_API_V3_02c.py`/`V4_01.py` + `Older versions/` (bağlantı kodu), `Instrument.conf`, `tick_data/*.zip` (GBPUSD tick verisi Mayıs-Haziran 2021, 2 zip, açılmadı; strateji değil), PDF/ikili dosyalar.
- Bulgu: Gerçek strateji sayısı az ve çoğu 'örnek': SMA9/16 kesişimi (TP 10 pip < SL 20 pip), MACD kesişimi (TP 5 < SL 10), Quantiacs örnekleri (Carstens 3 ve 7 — piyasalar arası/ATR kurallı, trend takip SMA40/200, kesitsel SMA oranı, Bollinger, Heikin Ashi, polinom regresyon), 2 SVM (`ml`), NFP haber scalp'i (`veri_yok`; kod yer tutucu). `rsiExample.py` BOŞ (0 satır). ADX makale dosyası çalışmaz durumda.
- Tek başına özgün ve kitap kaynaklı olanlar: Carstens Illustration 3 (Pazartesi + dar aralık) ve 7 (9 gün dip + ATR genişlemesi + ikinci piyasa teyidi, 4 gün tut) — 1L3A'da yok. Backtest sonucu yazılı değil (yalnız `bt_ma_cross_strategy.log` işlem günlüğü).

### 2.4 everget/tradingview-pinescript-indicators (213 dosya = 210 `.pine` + README/LICENSE/.gitignore)

- Okunan: 210 `.pine` dosyasının tamamı tarandı (`grep` ile `strategy(`, `alertcondition`, `alert(`, `plotshape/plotarrow/plotchar`, `crossover/crossunder` kalıpları + tek tek açılan sinyal dosyaları: 5 trailing stop, 10 osilatör, 8 hacim, 8 hareketli ortalama dosyası). **`strategy()` çağrısı içeren dosya yok** (hepsi `indicator`/`study`). 22 dosyada `alertcondition`, 32 dosyada `plotshape` var.
- Strateji satırı yazılan 22 satır (alert/sinyal tanımlı): açık Al/Sat etiketi+alert olanlar (5 trailing stop, STC, Corrected MA, PVT), eşik uyarıları (CCI, SARSI), çizgi-kesişimi işaretçisi olanlar (Stokastik K/D, MFI, TRIX, TSI, Didi, VW-MACD, Decycler, TDLD, KVO, OBV, A/D) ve MA eğim rengi uyarısı (7 MA dosyası tek satır). İşaretçiler `yalniz_isaretci` diye etiketli (al/sat etiketi yok, işlem yönü kullanıcıya bırakılmış).
- Sinyal tanımı olmayan, trade kuralı çıkmayan göstergeler (ör. `volume_accumulation` 'daha yüksek birikim' uyarısı, `ytd`/`roi` yüzde seviyesi uyarıları, `bitcoin_ath_hash_rate_level`, `fancy_shapes`, takvim vurgulayıcılar) strateji satırı almadı; aşağıdaki gösterge listesinde yer alır. Önceki sonuç: repoda hiç backtest yok.

**Gösterge envanteri** (210 dosya; `(…)` = 1L3A'daki karşılığı `motor/strateji/gostergeler*.py` ve `dis/_gosterge_*.py` içinde yaklaşık eşleşme; **yok** = 1L3A'da karşılığı bulunamadı):

Toplam 1L3A'da var (yaklaşık): 38; yok: 172. (Eşleştirme dosya adına göre kaba; tam doğruluk için kod karşılaştırması gerekir.)

**bands_and_channels/** (7 dosya)
- 1L3A'da gösterge var (1): moving_average_channel (keltner/bollinger (yaklaşık))
- **1L3A'da YOK** (6): acceleration_bands, interquartile_range_bands, kirshenbaum_bands, mean_absolute_deviation_bands, stoller_average_range_channels, vortex_bands

**highlighters/** (5 dosya)
- **1L3A'da YOK** (5): bitmex_withdrawals_cutoff_time, leap_years, quarters, range_candles, weekdays_gaps

**movings/** (70 dosya)
- CSV'de strateji satırı olanlar (8): adaptive_laguerre_filter, corrected_moving_average, fibonacci_weighted_moving_average, henderson_weighted_moving_average, inverse_distance_weighted_moving_average, quick_moving_average, sharp_modified_moving_average, sine_weighted_moving_average
- 1L3A'da gösterge var (15): arnaud_legoux_moving_average (alma), exponential_moving_average (ema), gaussian_filter (gauss_filtre), hull_moving_average (hma), kaufman_adaptive_moving_average (kama), laguerre_filter (laguerre), least_squares_moving_average (linreg), linear_weighted_moving_average (wma), parabolic_sar (psar), simple_moving_average (sma), t3_moving_average (t3), vidya_variable_index_dynamic_average (var_ma), weighted_moving_average (wma), wilder_modified_moving_average (smma/rma), zero_lag_exponential_moving_average (zlema)
- **1L3A'da YOK** (47): adaptive_rsi_moving_average, ahrens_moving_average, alpha_decreasing_exponential_moving_average, apirine_adaptive_exponential_moving_average, apirine_adaptive_moving_average, bryant_adaptive_moving_average, butterworth_filter, distance_coefficient_filter, distance_weighted_moving_average, double_exponential_moving_average, double_weighted_moving_average, ehlers_deviation_scaled_moving_average, ehlers_distance_coefficient_filter, ehlers_leading_indicator, ehlers_mesa_adaptive_moving_averages, ehlers_modified_optimum_elliptic_filter, ehlers_optimum_elliptic_filter, ehlers_super_smoother_filter, elastic_volume_weighted_moving_average, farey_sequence_weighted_moving_average, finite_impulse_response_filter, fractal_adaptive_moving_average, hampel_filter, holt_exponential_moving_average, infinite_impulse_response_filter, jurik_moving_average, leo_moving_average, mcginley_dynamic, mcnicholl_moving_average, middle_high_low_moving_average, moving_geometric_mean, moving_harmonic_mean, moving_median, moving_quadratic_mean, multiple_hull_moving_average, parabolic_weighted_moving_average, pentuple_exponential_moving_average, quadruple_exponential_moving_average, recursive_median_filter, recursive_median_oscillator, recursive_moving_trend_average, regularized_exponential_moving_average, self_weighted_moving_average, spencer_15_point_moving_average, spencer_21_point_moving_average, triangular_moving_average, trimean

**oscillators/** (73 dosya)
- CSV'de strateji satırı olanlar (11): cci_commodity_channel_index, didi_index, ehlers_decycler_oscillator, ehlers_triple_delay_line_detrender, mfi_money_flow_index, self_adjusting_rsi, stc_schaff_trend_cycle, stochastic, trix, tsi_true_strength_index, vw_macd
- 1L3A'da gösterge var (9): accelerator_oscillator (ao_ac), awesome_oscillator (ao_ac), chande_momentum_oscillator (cmo), demarker (demarker), ehlers_fisherized_deviation_scaled_oscillator (fisher (yaklaşık)), laguerre_rsi (laguerre), relative_momentum_index (rmi), rsi_relative_strength_index (rsi), stochastic_connors_rsi (stoch_rsi (yaklaşık))
- **1L3A'da YOK** (53): accumulative_swing_index, asymmetrical_rsi, center_of_gravity_oscillator, coppock_curve, derivative_oscillator, disparity_index, dorsey_inertia, dynamic_momentum_index, ehlers_cyber_cycle, ehlers_roofing_filter, ehlers_smoothed_adaptive_momentum, ehlers_stochastic, ehlers_stochastic_cyber_cycle, ehlers_super_passband_filter, ergodic_oscillator, forecast_oscillator, gator_oscillator, intraday_momentum_index, jurik_rsx, kairi_relative_index, laguerre_rsi_self_adjusting_alpha_with_fractals_energy, mass_index, normalized_relative_vigor_index, percentage_price_oscillator, percentage_volume_oscillator, phase_change_index, pretty_good_oscillator, price_momentum_oscillator, pring_special_k, rainbow_oscillator, random_walk_index, range_action_verification_index, rapid_rsi, recursive_median_oscillator, regression_oscillator, relative_spread_strength, relative_volatility_index, repulse, rocket_rsi, rsx, smoothed_rate_of_change, stiffness_indicator, stochastic_momentum_index, tick_line_momentum_oscillator, total_power_indicator, trend_continuation_factor, trend_detection_index, trend_intensity_index, trend_trigger_factor, trendscore, true_range_double, v_macd, vertical_horizontal_filter

**research/** (16 dosya)
- 1L3A'da gösterge var (3): heikin_ashi_chart_identifier (heikin_ashi (grafik tipi tanıyıcı, gösterge değil)), momentum (momentum), rate_of_change (roc)
- **1L3A'da YOK** (13): chart_type_identifier, custom_median_vs_built_in_median, dashed_line_style, fancy_shapes, kagi_chart_identifier, litecoin_halving_utc_countdown, mean_absolute_deviation, percentrank_bug, point_and_figure_pnf_chart_identifier, renko_chart_identifier, script_with_expiration_time, symbol_info_helper, utc_clock

**statistics/** (17 dosya)
- 1L3A'da gösterge var (1): z_score (zscore)
- **1L3A'da YOK** (16): all_time_high_days, all_time_high_percent_drop, bitcoin_ath_hash_rate_level, bullish_bearish_candle_series_distribution, candles_history, close_to_close_percent_change_distribution, dividends_per_share_dps_yearly, earnings_per_share_eps_yearly, gaps_percent_size_distribution, kendall_rank_correlation_coefficient, kurtosis_indicator, linear_regression_all_data, roi_return_on_investment, ticker_performance_by_us_president, us_treasury_yields, ytd_year_to_date_percent_return

**trailing_stops/** (5 dosya)
- CSV'de strateji satırı olanlar (5): chandelier_exit, halftrend, nrtr_nick_rypock_trailing_reverse, parabolic_sar, supertrend

**utils/** (2 dosya)
- **1L3A'da YOK** (2): session_input_parser, unit_testing_framework

**volatility/** (6 dosya)
- 1L3A'da gösterge var (1): normalized_average_true_range (atr (yaklaşık))
- **1L3A'da YOK** (5): damping_index, gopalakrishnan_range_index, mayer_multiple, ulcer_index, volatility_ratio

**volume/** (9 dosya)
- CSV'de strateji satırı olanlar (4): accumulation_distribution_line, klinger_volume_oscillator, on_balance_volume, price_volume_trend
- **1L3A'da YOK** (5): negative_volume_index, net_volume, percent_volume, positive_volume_index, volume_accumulation

Not: 'CSV'de strateji satırı olanlar' içindeki bazı göstergeler (ör. STC, TRIX, TSI, Didi, Klinger, NRTR, Corrected MA, PVT, A/D, Decycler, TDLD, VW-MACD) de 1L3A'da gösterge olarak **yok** (satır `yeni` ve gösterge de kodlanmalı).

### 2.5 joshyattridge/smart-money-concepts (25 dosya) — kütüphane, strateji YOK

- Okunan: `README.md`, `smartmoneyconcepts/smc.py` (987 satır; fonksiyonlar: `fvg`, `swing_highs_lows`, `bos_choch`, `ob`, `liquidity`, `previous_high_low`, `sessions`, `retracements`), `tests/unit_tests.py` (yalnız doğruluk testleri), `tests/generate_gif.py`, `tests/test_data/EURUSD/*.csv` (15m EURUSD verisi + beklenen çıktılar), `setup.py`, CODE_OF_CONDUCT/CONTRIBUTING.
- Giriş/çıkış/stop/hedef kuralı, alert ya da backtest YOK; yalnız 8 SMC göstergesi (FVG, swing H/L, BOS/CHoCH, order block, likidite, önceki yüksek/düşük, seans, geri çekilme). Strateji satırı yazılmadı. Gösterge listesi: yukarıdaki 8; 1L3A'da SMC kodları `dis/d1_smc.py`, `dis/d2_smc.py` içinde var.

### 2.6 TreborNamor/TradingView-Machine-Learning-GUI (54 dosya, 'HyperView') — 3 strateji

- Okunan: `strategy/{macd_rsi,adx_stochastic,smc_swing,smc_core,base,indicators,__init__}.py`, `config.json`, `config.schema.json`, `hyperview/` (backtest motoru, hyperopt, presets, pine dışa aktarma — altyapı), `README.md` (+vi), `tests/` (pine ayrıştırma testleri), `scripts/`. Çıkış SL/TP yüzdesi Optuna ile aranıyor (config: 150 deneme, SL/TP 1-15%).
- Üç Python stratejisi satıra döküldü: MACD+RSI, ADX+Stokastik, SMC Swing (HTF süpürme → LTF CHoCH → OB). Repoda sonuç yok (`results/`, `data/` klasörleri gitignore). Repoda ML eğitimi YOK (adına rağmen yalnız parametre optimizasyonu; 'Machine Learning' pazarlama adı). Pine dosyaları (`strategies/raw`) repoda bulunmuyor.

### 2.7 jianweiweng05/qsx-strategy-score (79 dosya) — strateji değerlendirme aracı, strateji YOK

- Okunan: `README.md`, `docs/*.md` (overlay, scoring, methodology, calibration, case-studies, privacy…), `qsx_strategy_score/*.py` (skorlama/metrikler/rapor), `examples/` (3 sentetik getiri CSV'si + `make_samples.py`: rastgele üretilmiş, strateji değil), `chrome-extension/`, `app/streamlit_app.py`, `tests/`, `scripts/`.
- İki satır (kuralsız): TradingView 'Crypto Bottom & Top Risk Radar' (BTC uzun/kısa hesap oranı yüzdelikleri → `veri_yok`; kodu repoda yok) ve 'Overlay Preview' (dinamik risk katsayısı, motoru kapalı → `kural_yok`). Faydalı yan ürün: skor/benzerlik testleri (rastgele zamanlama, Monte Carlo) 1L3A'nın sağlamlık testleriyle karşılaştırılabilir — ayrı iş.

## 3. Öne çıkan (denemeye değer) yeni adaylar

1. **geraked 2MOMEMA** — Momentum(10) 100 çizgisi kesişimi + Momentum(34)>100 + EMA10>EMA34 (son 9 mum), Grid'siz EA; tek başına kural (kategori trend_takip).
2. **geraked 2MAAOS / NWERSIASF / LRCUTB** — giriş+SL+TP net; **ancak yazar 'saf hali kârsız' diyor**; Andean Osc / Nadaraya-Watson / LRC+UT Bot ayrıca kodlanmalı (düşük öncelik).
3. **Carstens Illustration 3 ve 7** (PyTrader) — kitap kaynaklı, piyasalar-arası teyitli 4 günlük tutma; yeni aile.
4. **everget STC (Schaff) 25/75 kesişimi, NRTR %2, Chandelier Exit (22,3)** — kural net, 1L3A'da yok; NRTR/Chandelier mevcut supertrend ailesine yakın (ayrı satır, bağımsız test).
5. **Trebor SMC Swing** — 3 aşamalı (süpürme+CHoCH+OB) kural net, seans filtreli, RR 2; mevcut `dis__smc-*` satırlarıyla örtüşebilir.
6. İşaretçi kesişimleri (TRIX, TSI, KVO, Didi, Decycler, VW-MACD…) tek başına zayıf beklenir: osilatör-sinyal çizgisi kesişimi zaten swing__macd-sinyal ailesi mantığında; öncelik düşük.

## 4. Strateji içermeyen / sınırlı repolar

- **joshyattridge/smart-money-concepts**: yalnız gösterge kütüphanesi (0 satır).
- **qsx-strategy-score**: yalnız puanlama aracı (2 'kuralsız' satır).
- **EA31337**: strateji kodu artık okundu (2.1); ama 42 meta klasörünün 38'i strateji değil, filtre/anahtarlayıcı/risk katmanı.
- **PyTrader**: bağlantı altyapısı, `Strategies/` bir avuç örnek; 15 satırın yalnız 5'i özgün kural.

## 5. Belirsizlikler

- EA31337: `PriceStopMethod`/`SignalOpenMethod` bit anlamları ve Indi_* göstergelerin iç hesabı EA31337-classes ve EA31337-indicators repolarında; klonlanmadı. Satırlardaki kural, `Stg_*.mqh` içindeki `SignalOpen` gövdesine dayanır; `config/*.h` ile zaman dilimi başına ezilen sayılar tek tek okunmadı. Meta Resistance'ın yasak sayılması yorumdur.
- geraked: README 'Test' notu COT1 için yok; Andean/ZLSMA/LRC/NW Envelope/UT Bot göstergeleri 1L3A'da yok (bazıları `.mq5` kaynağından formülü okunabilir ama kodlanmadı). `Reverse=true` olan EA'larda (3MACD, AFAOSMD) hangi yönün 'asıl' olduğu yazarın seçimi.
- everget: gösterge eşleştirmesi (1L3A'da var/yok) dosya adına göre yaklaşık; Ehlers filtreleri vb. 1L3A'da başka adla bulunabilir.
- PyTrader `Strategies/Average Directional Index…` kural metni ile kodu çelişiyor; ADX satırında metin kuralı baz alındı.
- PyTrader'da LICENSE dosyası yok: lisans 'yok' (varsayılan tüm hakları saklı kabul edilir); yalnız kural fikri alınır, kod alınmaz.
- `repo` sütunu klon klasör adıdır; `kaynak` sütunu `github:sahip/repo` biçimindedir (everget için `github:everget/tradingview-pinescript-indicators`).
