# GitHub taraması, grup g1_freqtrade (özet)

Çıktı: `stratejiler/ek_kaynaklar/github_g1_freqtrade.csv` (153 satır). Repolar `/home/user/gh/` altında salt okunur okundu; kod kopyalanmadı, kurallar kendi cümlelerimle yazıldı.

## Repo bazında

| Repo | Lisans | Dosya (find) | Satır | Durum dağılımı |
|---|---|---|---|---|
| freqtrade/freqtrade-strategies | GPL-3.0 | 78 | 74 | mevcut 42, ayar 19, yeni 4, kural_yok 7, ml 2 |
| ssssi/freqtrade_strs | lisans dosyası yok | 34 | 23 | mevcut 1, ayar 7, yeni 13, yasak 1, kural_yok 1 |
| Rikj000/MoniGoMani | GPL-3.0 | 530 | 8 | ml 1, yeni 3, ayar 3, kural_yok 1 |
| iterativv/NostalgiaForInfinity | GPL-3.0 | 346 | 48 | yeni 26, ayar 19, yasak 2, kural_yok 1 |

## Okunan klasörler / kanıt

- **freqtrade-strategies:** `user_data/strategies/` (kök 25 dosya), `berlinguyinca/` (29), `futures/` (8 + Readme), `lookahead_bias/` (4 + readme), `user_data/hyperopts/GodStraHo.py`, README, `.github`. Eski `dis_envanter.csv` satırları (68) mevcut satır olarak kullanıldı; eksik olan GodStraHo eklendi. Eski taramada "kural belirsiz/eşik yok" denen **FReinforcedStrategy, mabStra, UniversalMACD, multi_tf, InformativeSample** kod okunarak kuralları çıkarıldı (satırlarda yazılı). **TrendRiderStrategy** tek satırdı, kodda 6 ayrı giriş etiketi var (trend_pullback, ema50_bounce, rsi_bounce, ema_crossover, bb_bounce, macd_reversal): 6 satıra bölündü. Kodda "fng_value" (korku-açgözlülük) sabit 50, funding/OI sıfır: dış veri fiilen kullanılmıyor.
- **ssssi/freqtrade_strs:** `ClucHAnix/` (2 strateji + `dry_run_history/kucoin.txt`), `binance/Archive/` (8 strateji + json), `binance/dry_run/` (E0V1EN, buy1_and_buynew/E0V1E, cooldown_period, 3 dry-run Telegram ekran görüntüsü: en yenisi okundu), `binance/hyperopts_loss_function/` (9 hedef fonksiyonu: strateji değil), `binance/dry&live_config/` (config), `binance/some_feature/max_min.patch` (yalnız Telegram bildirimi), `aws_run_bot/README.md`, README.
- **MoniGoMani:** `user_data/strategies/` (2 dosya: çerçeve + sinyal tanımı), `mgm-config.example.json` (ağırlık/stop/ROI/unclogger/koruma uzayları), `user_data/hyperopts`, `mgm_tools`, `mgm-hurry`, Documentation (4 md), README, `Some Test Results/` (v0.4.1..v0.13.0, 425 log, örnekleri okundu).
- **NostalgiaForInfinity:** kök `NostalgiaForInfinityX.py..X8.py` (X8 65k satır; `user_data/strategies/*` bunların kopyası/symlink'i), `legacy/Next` ve `NextGen`, `docs/` (backtest-results özetleri, trading-modes, position-management), `configs/`, `tools/`, `tests/unit` (adları), `.github`. X8'in 89 giriş koşulunun (57 long + 32 short) **her birinin** tetikleyici çekirdeği betikle ayıklanıp tek tek okundu; X5/X6/X7 ile aynı numaralı koşullar karşılaştırıldı (X5-X7'de aynı aileler, yalnız eşik ve süzgeç sayısı farklı; X7de bulunan #592 (kısa quad-stokastik pullback) X8de yok). X, X2, X3/X4 (birbirinin aynısı), Next, NextGen eski kuşak ayrıca okundu.

## NFI için önemli bulgular

1. **Yapı:** her koşul = (a) yüzlerce yan cümlelik "KORUMA" bloğu (5m + 15m/1h/4h/1d RSI3, StochRSI, Aroon, ROC, CMF eşiklerinin VEYA'lı kombinasyonları: düşen bıçağa girme) + (b) 3-10 satırlık gerçek tetikleyici. Satırlar yalnız tetikleyiciyi özetler. Koruma blokları fiilen tek tek "veriyle uydurulmuş" izlenimi veriyor (yorumlarda "4 kayıp, 3 kayıp" gibi notlar): aşırı uyum riski yüksek.
2. **Aileler:** 89 koşul ~30 mantık ailesine indirgendi (EMA12-EMA26 açıklığı + alt BB; SMA16 ofset + RSI20; EMA ofset + Aroon/StochRSI; BinHV45; derin düşüş sonrası aşırı satım; ADX doğumu; Donchian 7 gün; engulfing/SFP/inside-bar/marubozu/pin-bar/NR4/Fib/squeeze; quad-stokastik; kısa yönde tükeniş/dağıtım/çöküş aileleri; eski kuşakta EWO ofset, Williams derin dip, KAMA/MAMA, VWAP bandı, PMAX, Ichimoku, Moderi).
3. **Yasak kısımlar (ayrı satırlarla işaretli):** Grind (v1-v4, buyback) ve Rebuy: zarardaki pozisyona -%3..-%27 eşiklerinde 3-9 kademeli ekleme = ortalama düşürme. Giriş tetikleyicileri (özellikle #61-63, #120) kendi başlarına kullanılabilir, ek alım kısımları alınmaz.
4. **Çıkış/stop:** çıkış yalnız kârdayken (kâra göre yükselen RSI eşiği); zarardaki pozisyon sinyalle çıkmaz; `stoploss=-0.99`, doom stop varsayılan sistemde kapalı (`system_v3_2_stops_enable=False`), derisk kısmi satış. Yani fiilen stopsuz. Repodaki 2024 backtest özetleri %97-99 kazanma, %0.7-3 düşüş gösteriyor: bu, kayıpların tutulup grind ile taşınmasının yapay sonucu, kanıt sayılmaz.
5. **Veri:** tümü OHLCV ile üretilebilir. "Piyasa emri balonu / CVD" (#48/#548) OHLCV içi aralık oranıyla yaklaşıktır, gerçek emir akışı değildir. #164/#662 UTC günü ilk 4 saat aralığını kullanır (kripto 24/7 varsayımı). BTC ROC/RSI süzgeçleri (#106, #146) yalnız kriptoda anlamlı.
6. **Futures:** varsayılan kaldıraç 3x (`futures_mode_leverage`), kısa yön var.

## MoniGoMani

Strateji değil çerçeve: 8 sinyalin ağırlıkları, eşikler, stop, ROI, koruma uzayları HYPEROPT ile bulunuyor (`ml`). Çıkarılabilir kural parçaları: çekirdek trend rejimi (HT_TRENDMODE + SAR, `yeni`), Open Trade Unclogger (zararı erken kesen çıkış modülü, ortalama düşürme değil), koruma seti. Repodaki 425 backtest logu hyperopt edilen aynı kısa dönemde (örn. 2021-05..06) alınmış, örneklem-içi: kanıt değeri düşük.

## ssssi/freqtrade_strs

Küçük repo. Gerçek strateji: E0V1E/E0V1EN (zaten `dis__e0v1en`), ClucHAnix, BBMod (12 giriş ailesi), BinHV27 türevleri (kısa + kaldıraçlı), ConsensusShort. Dry-run ekran görüntüsü (E0V1E, 2025-02-09..03-16): 197 işlem, %73.6 kazanma, PF 1.48, maks düşüş %18.1, kısa dönem. `ClucHAnix` dosyalarındaki `Cluc5mDCA`/DCA alt sınıfı **yasak** satırı olarak işaretli. README'de kopya-ticaret bağlantısı ve bağış adresleri var (strateji bilgisi yok).

## Öne çıkan yeni adaylar (1L3A'da karşılığı yok)

- NFI: ADX trend doğumu (4h ADX 20 geçişi) + Donchian 7 gün (zaten ayar), derin düşüş sonrası aşırı satım (tepeden %10 + 1h BB genişliği), EMA12-EMA26 açıklığı + alt BB ailesi, Aroon/StochRSI aşırı satım, NR4 saat kırılımı, dörtlü stokastik rotasyon diverjansı, çöküş sıçraması, kısa yön tükeniş/dağıtım/ölü kedi aileleri.
- freqtrade-strategies: UniversalMACD (EMA12/EMA26 oran bandı ortalamaya dönüş), mabStra (fiilen hep piyasada, ilginç değil).
- Çıkış/risk modülleri: kâr-adımlı izleyen stop (HSL/PF/SL), werkkrew ROI-azalan + trend sonu çıkışı, stop_loss sonrası çift bazlı bekleme, MGM Unclogger.

## Belirsizlikler

- NFI eski kuşak (X v11, X3/X4, Next) koşullarının numaraları satırlarda aile bazında listelendi; her koşulun kendi eşikleri tek tek tabloya dökülmedi (aynı aile, farklı eşik olarak birleştirildi).
- NFI X5-X7 ile X8 arasında "aynı numara = aynı aile" kontrolü tetikleyici çekirdeklerin yapısına bakılarak yapıldı; X5/X6 koruma blokları ayrıca incelenmedi.
- Eski 1L3A satırlarındaki `onceki_sonuc` (PF IS/OOS) repo değil, önceki 1L3A testidir; satırlarda öyle etiketlendi.
- GodStra/Diamond/Heracles gibi hyperopt ürünleri için kural var ama anlamsız (mutlak fiyat eşiği, fiyat-hacim kesişimi); `ml`/`kural_yok` işaretlendi.
- Zaman dilimine göre `stil`: NFI 5m girişleri `scalp` yazıldı, ancak pozisyonlar saatler-günler tutuluyor.
