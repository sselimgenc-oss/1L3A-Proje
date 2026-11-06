# Dış Depo Strateji Analizi

Kullanıcının bulduğu 10 GitHub deposundaki **bütün stratejiler** çıkarıldı ve bizim ölçütlerimizle test edildi. Altyapı depolarında örnek ya da hazır gelen stratejiler de dahil.

Depolar:
- freqtrade-strategies
- je-suis-tm/quant-trading
- paperswithbacktest/awesome-systematic-trading
- chrisleekr/binance-trading-bot
- Drakkar-Software/OctoBot
- OpenByteInc/QuantDinger
- charliedream1/ai_quant_trade
- cuemacro/finmarketpy
- kernc/backtesting.py
- mementum/backtrader

Kod `dis_kaynak/`, ham sonuçlar `dis_kaynak/sonuc_*.csv`, sağlamlık testleri `dis_kaynak/sonuc_aday_saglamlik.csv` dosyalarında.

## 1. Kısa sonuç

**Hiçbir dış strateji elimizdeki sistemlerin yerini alacak ya da kağıt bota eklenecek düzeyde değil.**

- Ön eleme ölçütleri: iki dönemde de kâr faktörü (PF) > 1.2 ve Sharpe > 0.5, stres evreninde PF > 1.1.
- Saat ve üstü zaman dilimlerinde **142 farklı kural** test edildi (+3 düzeltilmiş sürüm); bunlardan **7'si** ön elemeyi geçti. Biri (GodStraNew) geleceği gördüğü için geçersiz.
- Bu 7 aday, bizim denetimde kullandığımız ek testlerden geçirildi: komşu parametreler, girişi 1 gün geciktirme, al-tut karşılaştırması, 2022 ayı yılı. **Bu testlerin hepsini geçen aday kalmadı.**
- Kıyas için aynı ölçüyle bizim sistemlerimiz:
  - A+B: Sharpe IS 1.80, OOS 1.30.
  - Diğer oturumun KGT+KMN sistemi: Sharpe 1.99.
- En iyi dış aday tek başına OOS Sharpe 0.9 civarında. Bunlar da ya 1 günlük gecikmede çöküyor ya da 2022'de büyük kayıp veren long-only beta.
- Geleneksel piyasa evreninde (Magnificent 7 + BIST 30'un ilk 10'u + altın/petrol) 88 günlük kural denendi. **Hiçbiri eşit ağırlıklı al-tut'u iki dönemde de geçmedi.** Long-only kuralların oradaki iyi görünen sonuçları, bugünün kazanan hisselerinin geriye dönük seçilmesinden (seçim yanlılığı) geliyor.
- En yüksek görünen freqtrade sonuçları (GodStraNew, Zeus, DevilStra) depo tarafından "**geleceği görüyor**" diye işaretlenmiş stratejiler. Normalizasyon tüm verinin min/max değerini kullanıyor; düzeltilmiş sürüm sonuçları §4'te.
- Dakikalık (1m/5m/15m/30m) 40 freqtrade stratejisi, tek bir GitHub Actions çalıştırmasında kendi zaman dilimlerinde test edildi. **Hiçbiri ön elemeyi geçmedi** (§5).

**Not edilmeye değer iki fikir** (bota değil, ileride araştırmaya):
1. **N günlük zirve kırılımında ertesi gün devam etkisi** (backtrader "pinkfish", Padysak-Vojtko MAX). n = 20…55 aralığında tutarlı, ama etki yalnızca ilk günde: 1 gün gecikince OOS Sharpe 0.9 → 0.0. Bu, A stratejimizin 4H kırılım + 1H giriş mantığıyla zaten örtüşüyor; ayrı bir strateji olarak değer katmıyor.
2. **"Üç ortalamayı kesen boğa mumu + SMA60 trend filtresi"** (QuantDinger şablonu). Parametre ve gecikmeye karşı sağlam, düşüşü küçük (−%11), ama OOS Sharpe yalnızca 0.46–0.64 ve 2022'de zararda. A'nın 4H/1H yapısında yeniden ele alınabilir.

## 2. Yöntem — bizim kurallarımız

Hepsi aynı kurallarla test edildi:

| Kural | Uygulama |
|---|---|
| Maliyet | Taraf başına %0.07 (komisyon + kayma); vadeli işlemde funding pozisyon yönüne göre |
| İleriye bakma yok | Karar mum kapanışında; pozisyon bir sonraki mumdan; aynı mumda önce stop |
| Dönemler | IS 2020–2023, OOS 2024–2026, **2022 ayı yılı ayrıca** (ekip standardı) |
| Evrenler | Ana: 25 coin (Binance USDT-M). Stres: 20 eski/delist edilmiş coin (LUNA, FTT dahil). Geleneksel: Mag7 + BIST 10 (USDTRY ile dolara çevrildi) + altın, WTI, Brent (günlük, 2010–2026) |
| Sermaye | Bileşiksiz. Coin başına eşit dilim (strateji tek varlık içinse); kesitsel stratejilerde brüt ağırlık ≤ 1 |
| Muhafazakâr botlar | Grid/DCA/martingale: dolum mumunda kâr alma yok (mum içi sıra bilinmiyor). İlk sürümde bu yoktu ve %99.9 WR gibi sahte sonuçlar çıktı, düzeltildi |
| freqtrade stratejileri | **Kendi kodlarıyla**, freqtrade 2026.9 backtest motorunda. Futures modu, sabit 990$ pay, en çok 10 açık işlem, ücret %0.07, funding dahil. Uyumluluk için yalnız `numpy.lib.math` importu düzeltildi |
| Diğer depolar | Kurallar koddan birebir çıkarıldı (`dis_kaynak/kurallar.py`, `awesome.py`, `jesuistm.py`). Mutlak fiyat eşikleri orana çevrildi. Hisse günü pencereleri takvim gününe çevrildi (21→30, 252→365) |

Kısaltmalar: PF = kâr faktörü (işlem başına brüt kâr / brüt zarar), Sh = yıllık Sharpe (günlük getiriden), DD = en büyük düşüş (bileşiksiz, sermaye oranı).

**DD hakkında:** stratejiler kaldıraçsız ve tam nominal olduğu için long-only stratejilerde DD −%60…−%130 görünüyor. Bu ölçek, risk bazlı boyutlandırma yapan sistemimizle doğrudan kıyaslanamaz. Bu yüzden eleme Sharpe ve PF ile yapıldı, DD yalnız gösterildi.

## 3. Envanter — hangi depoda ne var

| Depo | Bulunan | Test edilen satır | Test edilemeyen (neden) |
|---|---|---|---|
| freqtrade-strategies | 68 strateji | 26 (≥1h) + 40 (dakikalık, Actions) + 3 düzeltilmiş sürüm | DoesNothingStrategy işlem yapmaz; `lookahead_bias/` klasöründeki 4 strateji kasıtlı hatalı (düzeltilmiş sürümleri de test edildi) |
| je-suis-tm/quant-trading | 17 | 11 | Options Straddle, VIX Calculator (opsiyon), Monte Carlo (tahmin), Oil/Ore Money, Smart Farmers (makro/emtia-FX), Portfolio Optimization, Wisdom of Crowds (analist tahmini) |
| awesome-systematic-trading | 61 kod + 8 kripto makale | 29 dosya + 3 makale = 32 satır | 28 dosya: bilanço/kazanç verisi, opsiyon, makro faiz/PPP/CAPE, ESG, metin, açığa satış verisi, vadeli eğri. 5 makale: kural metni erişilemedi (site sandbox'tan çözülemedi) |
| backtrader | 40 örnek | 18 (kopyalar gruplandı) | 7 rastgele/altyapı demosu (yazı-tura alım, emir türü testleri), 1 test fikstürü |
| backtesting.py | 8 | 5 | P7 ile P8 aynı model; P2 kopya |
| finmarketpy | 9 | 7 | Opsiyon/forward roll endeksleri (F7–F9) |
| QuantDinger | 31 | 18 | Piyasa değeri/ROE/büyüme filtreleri (Q9, Q12), 1m+1h BTC (Q17, dakika verisi), LLM karar filtreleri (Q26–27), yalnız grafik göstergeleri (Q28–31; SuperTrend Q8 ile test edildi) |
| ai_quant_trade | 18 | 9 | A-share'e özgü veri (Dragon-Tiger listesi A6, küçük ölçek A17), temel/faktör ML (A8, A10, A11), RL (A12, A13), LLM/NLP (A15, A16) |
| OctoBot | 71 bileşen | 12 | Sosyal/haber/Google Trends/Fear&Greed değerlendiricileri (10), LLM (O14, O32, O33, O45), anlık 1m değerlendiriciler (O15–O17), piyasa yapıcılık/arbitraj (çoklu borsa, emir defteri), kopya/TradingView/Polymarket/DSL/boş modlar. İşlem modları (O35–O37) değerlendirici notlarını uygular; bileşen değerlendiriciler ayrı test edildi |
| binance-trading-bot | 3 | 3 | — |

Toplam: **~334 kayıt → 142 farklı kural saat ve üstünde + 40 dakikalık freqtrade stratejisi** test edildi (186 sonuç satırı; 6'sı stratejinin kendi hatası ya da süre aşımı nedeniyle sonuçsuz). Kalanlar kopya, demo ya da kripto fiyat verisiyle tanımsız (yukarıdaki nedenler).

## 4. Ön elemeyi geçen 7 aday ve sağlamlık testleri

Ölçüt: iki dönemde de PF > 1.2 ve Sharpe > 0.5, stres evreninde PF > 1.1. Kıyas ölçütleri:
- Ana evrende eşit ağırlıklı al-tut: Sharpe IS 1.13, OOS 0.18.
- BTC al-tut: Sharpe IS 1.00, OOS 0.74, 2022'de −1.28.

| Aday | Kaynak | PF IS / OOS | Sh IS / OOS | 2022 Sh | Sağlamlık | Karar |
|---|---|---|---|---|---|---|
| 20 mum zirvesine dokununca al, 2 gün tut | backtrader (pinkfish) | 1.43 / 1.30 | 1.43 / 0.92 | <0 | n=30/55'te sürüyor; **1 gün gecikmede OOS Sh 0.02** | Ele (fikir A'da zaten var) |
| 10 günün en yüksek kapanışında long (MAX) | awesome (Padysak-Vojtko) | 1.29 / 1.30 | 0.92 / 0.87 | <0 | n=20/30'da sürüyor; **1 gün gecikmede OOS Sh −0.14** | Ele (aynı etki) |
| Üç ortalamayı kesen boğa mumu + SMA60 trend | QuantDinger Q4 | 1.82 / 1.88 | 0.88 / 0.58 | −0.26 | Gövde %1–3 sağlam; gecikme OOS 0.46; trend 40'ta OOS −0.06 | Araştırma fikri |
| Düşük volatilite top 4, haftalık | QuantDinger Q11 | 2.30 / 2.24 | 0.91 / 0.78 | −0.77 | Parametrelerde sağlam, ama tam yatırımlı long-only; OOS başarısı BTC'nin altcoinleri geçmesinden | Ele (beta, kenar değil) |
| Momentum rotasyonu (skor + BTC filtresi + %15 iz) | ai_quant_trade A3 | 2.44 / 1.48 | 1.39 / 0.67 | −1.39 | top 3/5/8'de OOS Sh 0.58/0.29/0.08 | Ele (kırılgan) |
| Heikin-Ashi ters mum birikimi | je-suis-tm | 2.83 / 3.02 | 0.60 / 0.78 | −0.70 | Yüksek PF piramitlemeden; 4h'de OOS Sh −0.43; DD −%68 | Ele |
| GodStraNew | freqtrade `lookahead_bias/` | 2.81 / 2.08 | 2.07 / 0.92 | — | **Geleceği görüyor** (tüm veri min/max normalizasyonu); düzeltilince PF 1.16 / 0.76 | Geçersiz |

A+B ile birleşim testinde günlük korelasyon −0.01…+0.05. Adaylar eşit volatiliteyle %25–50 eklendiğinde OOS Sharpe 1.30'dan 1.37–1.56'ya çıkıyor. Ama bu artışın büyük kısmı, ilişkisiz herhangi bir pozitif serinin mekanik çeşitlendirme etkisi. Adayların kendi kenarları kırılgan olduğu için çeşitlendirme gerekçesiyle eklemek önerilmez.

### İleriye bakan freqtrade stratejileri: orijinal ve düzeltilmiş

Düzeltme: normalizasyondaki `min()/max()` yerine yalnız geçmişe bakan `expanding().min()/max()`. Kodun geri kalanı aynı.

| Strateji | PF IS / OOS | Sh IS / OOS | Stres PF | DD % |
|---|---|---|---|---|
| GodStraNew (orijinal) | 2.81 / 2.08 | 2.07 / 0.92 | 1.74 | −6 |
| GodStraNew (düzeltilmiş) | 1.16 / 0.76 | 0.36 / −0.73 | 0.85 | −49 |
| Zeus (orijinal) | 2.40 / 1.19 | 1.93 / 0.35 | 1.71 | −17 |
| Zeus (düzeltilmiş) | 1.08 / 0.97 | 0.17 / −0.09 | 0.65 | −46 |
| DevilStra (orijinal) | 1.34 / 0.98 | 1.11 / −0.07 | 1.03 | −116 |
| DevilStra (düzeltilmiş) | 1.25 / 0.98 | 0.82 / −0.09 | 0.90 | −110 |

İleriye bakma kaldırılınca avantaj tamamen kayboluyor. GitHub'da "çok kârlı" görünen stratejilerin tipik tuzağı bu.


## 5. Dakikalık freqtrade stratejileri (1m/5m/15m/30m, kendi zaman diliminde)

Tek GitHub Actions çalıştırmasında test edildi: run 38175168797, 5 paralel parça, toplam ~150 dk.
- Veri: data.binance.vision USDT-M, 10 coin (BTC ETH SOL XRP BNB DOGE ADA AVAX LINK LTC).
- 5m/15m/30m: 2022-01 → 2026-09. IS = 2022–2023, OOS = 2024+.
- 1m: yalnız 2025-10 → 2026-09 (OOS).
- Ayarlar: freqtrade futures modu, ücret %0.07, funding dahil, sabit 990$ pay, en çok 10 açık işlem.

**Sonuç: 40 stratejiden hiçbiri ön elemeyi geçmedi.**
- En iyisi CombinedBinHAndCluc (5m): PF 1.16 / 1.18, Sharpe 0.74 / 0.67, 2022 PF 0.90. Eşik 1.2 altında.
- Bu 2018 dönemi scalper'ların çoğu yüksek kazanma oranına (%70–95) rağmen PF < 1. Küçük ROI hedefleri, %0.07'lik taraf maliyetini karşılamıyor.
- Bazı stratejilerde OOS boş: 2024 sonrası işlem yok. Stopsuz kaybeden işlemler 10 slotun hepsini doldurup açık kalmış; bu, orijinal kuralın sonucu.
- AlmgrenChrissStrategy 15 dakikalık süre sınırında bitmedi.

| Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | Not |
|---|---|---|---|---|---|---|---|---|---|---|
| CombinedBinHAndCluc | 5m | 1670 | 75 | 1.16 | 1.18 | 0.90 | 0.74 | 0.67 | -22 |  |
| UniversalMACD | 5m | 1105 | 73 | 0.72 | 1.53 | 0.53 | -0.68 | 0.66 | -37 |  |
| BinHV45 | 1m | 21 | 86 | – | 1.46 | – | – | 0.57 | -1 |  |
| TrendFollowingStrategy | 5m | 1166 | 82 | 0.85 | 0.96 | 0.61 | -0.56 | -0.14 | -81 |  |
| PowerTower | 5m | 2437 | 68 | 0.91 | 0.93 | 0.71 | -0.29 | -0.24 | -28 |  |
| wtc | 30m | 1252 | 60 | 0.78 | 0.94 | 0.63 | -1.06 | -0.29 | -78 |  |
| Simple | 5m | 7715 | 87 | 0.88 | 0.93 | 0.75 | -0.79 | -0.52 | -81 |  |
| Diamond | 5m | 1484 | 70 | 0.67 | 0.67 | 0.51 | -0.70 | -0.66 | -23 |  |
| ClucMay72018 | 5m | 1196 | 77 | 1.04 | 0.72 | 0.91 | 0.16 | -0.66 | -21 |  |
| SwingHighToSky | 15m | 2345 | 70 | 0.59 | 0.62 | 0.53 | -1.12 | -0.78 | -87 |  |
| Quickie | 5m | 1895 | 93 | 0.71 | 0.72 | 0.56 | -1.12 | -0.84 | -86 |  |
| SmoothOperator | 5m | 2364 | 58 | 0.72 | 0.56 | 0.71 | -2.33 | -0.86 | -91 |  |
| MACDStrategy | 5m | 1571 | 95 | 0.63 | 0.69 | 0.53 | -1.08 | -0.88 | -91 |  |
| Low_BB | 1m | 56 | 14 | – | 0.49 | – | – | -0.93 | -5 |  |
| Strategy001 | 5m | 2593 | 87 | 0.72 | 0.79 | 0.68 | -1.74 | -1.04 | -93 |  |
| MACDStrategy_crossed | 5m | 2380 | 88 | 0.74 | 0.71 | 0.61 | -1.22 | -1.12 | -87 |  |
| Strategy001_custom_exit | 5m | 3549 | 91 | 0.71 | 0.69 | 0.66 | -1.91 | -1.14 | -91 |  |
| Strategy002 | 5m | 1021 | 91 | 0.78 | 0.68 | 0.75 | -0.67 | -1.14 | -32 |  |
| MultiRSI | 5m | 7499 | 57 | 0.76 | 0.68 | 0.74 | -3.54 | -1.24 | -90 |  |
| CCIStrategy | 1m | 439 | 26 | – | 0.77 | – | – | -1.24 | -21 |  |
| Strategy004 | 5m | 4116 | 92 | 0.88 | 0.73 | 0.77 | -0.66 | -1.27 | -73 |  |
| Strategy005 | 5m | 2338 | 83 | 0.82 | 0.75 | 0.74 | -1.14 | -1.31 | -90 |  |
| Strategy003 | 5m | 2710 | 91 | 0.73 | 0.71 | 0.60 | -1.25 | -1.36 | -73 |  |
| ReinforcedQuickie | 5m | 5739 | 70 | 0.80 | 0.69 | 0.86 | -2.17 | -1.43 | -92 |  |
| BinHV27 | 5m | 7786 | 58 | 0.93 | 0.80 | 0.84 | -0.50 | -1.54 | -77 |  |
| CMCWinner | 15m | 4849 | 67 | 0.63 | 0.39 | 0.61 | -2.79 | -1.69 | -92 |  |
| SmoothScalp | 1m | 1558 | 60 | – | 0.63 | – | – | -1.73 | -34 |  |
| ReinforcedSmoothScalp | 1m | 400 | 52 | – | 0.57 | – | – | -2.93 | -13 |  |
| Scalp | 1m | 5676 | 43 | – | 0.40 | – | – | -9.43 | -85 |  |
| ASDTSRockwellTrading | 5m | 7848 | 26 | 0.67 | – | 0.67 | -4.85 | – | -88 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| BreakEven | 5m | – | – | – | – | – | – | – | – | işlem yok (bilgi çifti / yardımcı sınıf) |
| InformativeSample | 5m | – | – | – | – | – | – | – | – | işlem yok (bilgi çifti / yardımcı sınıf) |
| TWAPStrategy | 15m | 5888 | 60 | 0.79 | – | 0.79 | -3.34 | – | -91 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| AlmgrenChrissStrategy | 15m | – | – | – | – | – | – | – | – | zaman aşımı (900s) |
| TechnicalExampleStrategy | 5m | 7640 | 46 | 0.62 | – | 0.62 | -3.62 | – | -90 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| Bandtastic | 15m | 5089 | 62 | 0.70 | – | 0.70 | -2.83 | – | -93 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| DoesNothingStrategy | 5m | – | – | – | – | – | – | – | – | işlem yapmaz (örnek) |
| EMASkipPump | 5m | 4274 | 61 | 0.70 | – | 0.70 | -2.61 | – | -92 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| CofiBitStrategy | 5m | 6353 | 52 | 0.57 | – | 0.57 | -5.31 | – | -90 | 2024 sonrası işlem yok: slotlar stopsuz açık işlemlerle dolu kaldı |
| FReinforcedStrategy | 5m | – | – | – | – | – | – | – | – |                                                                            2/4  50% • 0:00:43 • -:--:--
analyze ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0/0   0% • 0:00:43 • 0:0 |


## 6. Kaynak depolarda bulunan hatalar ve tuzaklar

Yayınlanan sonuçların bizim testten farklı çıkmasının nedenleri:
- **İleriye bakma (geleceği görme):**
  - freqtrade `lookahead_bias/` klasörü: GodStraNew, Zeus, DevilStra, wtc (depo kasıtlı örnek olarak koymuş).
  - je-suis-tm Shooting Star: ertesi mumun yüksek/kapanışını kullanıyor.
  - finmarketpy TechIndicator "RSI" kuralı: `shift(-1)` kullanıyor.
  - backtesting.py ML örneği: ileri yürüyen eğitimde son 48 mumun gelecek etiketi eğitime giriyor. Bizim testimizde düzeltildi.
- **awesome-systematic-trading kod hataları:**
  - 12 aylık döngüde iki bacak da long.
  - Kazanç duyurusu stratejisi tek pozisyon açıyor.
  - Vadeli kısa dönem dönüşte iki bacak net short; hacim filtresi etkisiz.
  - Ülke değer faktörü CAPE yerine fiyata göre sıralıyor.
  - Momentum faktöründe "1 ay atlama" yok.
  - Bu hatalar düzeltilip amaçlanan kural test edildi.
- **Diğer:**
  - QuantDinger "Dual EMA" örneği aslında SMA kullanıyor.
  - backtrader signals-strategy'de `shortexit` yanlış eşlenmiş.
  - OctoBot GPT profilindeki `max_confidence_threshold` anahtarı kod tarafından okunmuyor.
  - GodStra çalışırken freqtrade "uzunluk uyuşmazlığı" hatası veriyor (strateji hatalı).
- **Mutlak eşikler:** je-suis-tm Bollinger W ve RSI omuz-baş-omuz kalıpları FX/hisse fiyat ölçeğine göre mutlak eşik kullanıyor. Oranlı hale getirildi. Bollinger W kriptoda hiç tetiklenmedi.

## 7. Tüm sonuçlar

Tablolar kaynak depoya göre gruplandı, her grup OOS Sharpe'a göre sıralandı. "PF gel" sütunları geleneksel evreni gösterir (yalnız günlük kurallar).

### freqtrade-strategies (30 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FT_GodStraNew | GodStraNew | 4h | 249 | 71 | 2.81 | 2.08 | 1.74 | 2.07 | 0.92 | -6 | 1.74 | – | – | geçersiz (ileriye bakma) |
| FT_FSupertrendStrategy | FSupertrendStrategy | 1h | 18699 | 64 | 1.11 | 1.07 | 0.94 | 1.07 | 0.69 | -61 | 1.01 | – | – | ele |
| FT_ADXMomentum | ADXMomentum | 1h | 32259 | 89 | 1.10 | 1.09 | 1.02 | 0.77 | 0.63 | -65 | 1.00 | – | – | ele |
| FT_CustomStoplossWithPSAR | CustomStoplossWithPSAR | 1h | 139 | 5 | 0.76 | 36.16 | 0.03 | -0.21 | 0.59 | -137 | 0.82 | – | – | ele |
| FT_FSampleStrategy | FSampleStrategy | 1h | 1931 | 14 | 1.60 | 1.14 | 0.52 | 1.67 | 0.38 | -115 | 1.17 | – | – | ele |
| FT_Zeus | Zeus | 4h | 430 | 69 | 2.40 | 1.19 | 3.43 | 1.93 | 0.35 | -17 | 1.71 | – | – | geçersiz (ileriye bakma) |
| FT_MultiMa | MultiMa | 4h | 2605 | 41 | 1.39 | 1.04 | 1.11 | 1.63 | 0.18 | -44 | 1.16 | – | – | ele |
| FT_Supertrend | Supertrend | 1h | 12102 | 63 | 1.09 | 1.02 | 0.88 | 0.62 | 0.11 | -108 | 1.03 | – | – | ele |
| FT_DevilStra | DevilStra | 4h | 2563 | 66 | 1.34 | 0.98 | 0.64 | 1.11 | -0.07 | -116 | 1.03 | – | – | geçersiz (ileriye bakma) |
| FT_DevilStraDuz | DevilStraDuz | 4h | 2460 | 67 | 1.25 | 0.98 | 0.66 | 0.82 | -0.09 | -110 | 0.90 | – | – | ele |
| FT_ZeusDuz | ZeusDuz | 4h | 534 | 66 | 1.08 | 0.97 | 0.97 | 0.17 | -0.09 | -46 | 0.65 | – | – | ele |
| FT_PatternRecognition | PatternRecognition | 1d | 2262 | 78 | 1.07 | 0.91 | 0.61 | 0.24 | -0.32 | -170 | 0.89 | – | – | ele |
| FT_VolatilitySystem | VolatilitySystem | 1h | 1569 | 34 | 1.26 | 0.66 | 0.85 | 1.32 | -0.36 | -82 | 0.93 | – | – | ele |
| FT_ReinforcedAverageStrategy | ReinforcedAverageStrategy | 4h | 10637 | 27 | 1.28 | 0.95 | 0.90 | 1.79 | -0.38 | -79 | 1.11 | – | – | ele |
| FT_Freqtrade_backtest_validation_freqtrade1 | Freqtrade_backtest_validation_freqtrade1 | 1h | 19934 | 36 | 1.18 | 0.94 | 0.89 | 1.31 | -0.53 | -165 | 0.99 | – | – | ele |
| FT_AverageStrategy | AverageStrategy | 4h | 18010 | 27 | 1.13 | 0.93 | 0.75 | 1.04 | -0.58 | -190 | 0.98 | – | – | ele |
| FT_GodStraNewDuz | GodStraNewDuz | 4h | 514 | 58 | 1.16 | 0.76 | 0.45 | 0.36 | -0.73 | -49 | 0.85 | – | – | ele |
| FT_AwesomeMacd | AwesomeMacd | 1h | 7730 | 33 | 1.18 | 0.90 | 0.94 | 1.30 | -0.79 | -154 | 1.02 | – | – | ele |
| FT_FAdxSmaStrategy | FAdxSmaStrategy | 1h | 2308 | 35 | 0.92 | 0.81 | 0.96 | -0.42 | -0.98 | -45 | 0.87 | – | – | ele |
| FT_AdxSmas | AdxSmas | 1h | 4770 | 46 | 0.93 | 0.65 | 0.75 | -0.43 | -1.19 | -136 | 0.91 | – | – | ele |
| FT_BbandRsi | BbandRsi | 1h | 760 | 63 | 0.78 | – | 0.50 | -0.50 | – | -117 | 0.88 | – | – | ele |
| FT_HourBasedStrategy | HourBasedStrategy | 1h | 1448 | 57 | 0.80 | – | – | -0.74 | – | -128 | 0.80 | – | – | ele |
| FT_TDSequentialStrategy | TDSequentialStrategy | 1h | 1610 | 40 | 0.81 | – | – | -0.79 | – | -96 | 0.89 | – | – | ele |
| FT_TrendRiderStrategy | TrendRiderStrategy | 1h | 3219 | 26 | 0.72 | – | – | -2.53 | – | -96 | 0.67 | – | – | ele |
| FT_hlhb | hlhb | 4h | 2061 | 73 | 0.70 | – | 0.64 | -1.24 | – | -95 | 0.71 | – | – | ele |
| FT_mabStra | mabStra | 4h | 660 | 48 | 0.77 | – | – | -0.63 | – | -129 | 0.85 | – | – | ele |
| FT_FOttStrategy | FOttStrategy | 1h | – | – | – | – | – | – | – | – | – | – | – | hata |
| FT_Heracles | Heracles | 4h | – | – | – | – | – | – | – | – | – | – | – | hata |
| FT_GodStra | GodStra | 12h | – | – | – | – | – | – | – | – | – | – | – | hata |
| FT_wtc | wtc (30m) | 30m | – | – | – | – | – | – | – | – | – | – | – | hata |

### freqtrade-strategies (dakikalık) (40 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FTD_CombinedBinHAndCluc | CombinedBinHAndCluc | 5m | 1670 | 75 | 1.16 | 1.18 | 0.90 | 0.74 | 0.67 | -22 | – | – | – | ele |
| FTD_UniversalMACD | UniversalMACD | 5m | 1105 | 73 | 0.72 | 1.53 | 0.53 | -0.68 | 0.66 | -37 | – | – | – | ele |
| FTD_BinHV45 | BinHV45 | 1m | 21 | 86 | – | 1.46 | – | – | 0.57 | -1 | – | – | – | ele |
| FTD_TrendFollowingStrategy | TrendFollowingStrategy | 5m | 1166 | 82 | 0.85 | 0.96 | 0.61 | -0.56 | -0.14 | -81 | – | – | – | ele |
| FTD_PowerTower | PowerTower | 5m | 2437 | 68 | 0.91 | 0.93 | 0.71 | -0.29 | -0.24 | -28 | – | – | – | ele |
| FTD_wtc | wtc | 30m | 1252 | 60 | 0.78 | 0.94 | 0.63 | -1.06 | -0.29 | -78 | – | – | – | ele |
| FTD_Simple | Simple | 5m | 7715 | 87 | 0.88 | 0.93 | 0.75 | -0.79 | -0.52 | -81 | – | – | – | ele |
| FTD_Diamond | Diamond | 5m | 1484 | 70 | 0.67 | 0.67 | 0.51 | -0.70 | -0.66 | -23 | – | – | – | ele |
| FTD_ClucMay72018 | ClucMay72018 | 5m | 1196 | 77 | 1.04 | 0.72 | 0.91 | 0.16 | -0.66 | -21 | – | – | – | ele |
| FTD_SwingHighToSky | SwingHighToSky | 15m | 2345 | 70 | 0.59 | 0.62 | 0.53 | -1.12 | -0.78 | -87 | – | – | – | ele |
| FTD_Quickie | Quickie | 5m | 1895 | 93 | 0.71 | 0.72 | 0.56 | -1.12 | -0.84 | -86 | – | – | – | ele |
| FTD_SmoothOperator | SmoothOperator | 5m | 2364 | 58 | 0.72 | 0.56 | 0.71 | -2.33 | -0.86 | -91 | – | – | – | ele |
| FTD_MACDStrategy | MACDStrategy | 5m | 1571 | 95 | 0.63 | 0.69 | 0.53 | -1.08 | -0.88 | -91 | – | – | – | ele |
| FTD_Low_BB | Low_BB | 1m | 56 | 14 | – | 0.49 | – | – | -0.93 | -5 | – | – | – | ele |
| FTD_Strategy001 | Strategy001 | 5m | 2593 | 87 | 0.72 | 0.79 | 0.68 | -1.74 | -1.04 | -93 | – | – | – | ele |
| FTD_MACDStrategy_crossed | MACDStrategy_crossed | 5m | 2380 | 88 | 0.74 | 0.71 | 0.61 | -1.22 | -1.12 | -87 | – | – | – | ele |
| FTD_Strategy001_custom_exit | Strategy001_custom_exit | 5m | 3549 | 91 | 0.71 | 0.69 | 0.66 | -1.91 | -1.14 | -91 | – | – | – | ele |
| FTD_Strategy002 | Strategy002 | 5m | 1021 | 91 | 0.78 | 0.68 | 0.75 | -0.67 | -1.14 | -32 | – | – | – | ele |
| FTD_MultiRSI | MultiRSI | 5m | 7499 | 57 | 0.76 | 0.68 | 0.74 | -3.54 | -1.24 | -90 | – | – | – | ele |
| FTD_CCIStrategy | CCIStrategy | 1m | 439 | 26 | – | 0.77 | – | – | -1.24 | -21 | – | – | – | ele |
| FTD_Strategy004 | Strategy004 | 5m | 4116 | 92 | 0.88 | 0.73 | 0.77 | -0.66 | -1.27 | -73 | – | – | – | ele |
| FTD_Strategy005 | Strategy005 | 5m | 2338 | 83 | 0.82 | 0.75 | 0.74 | -1.14 | -1.31 | -90 | – | – | – | ele |
| FTD_Strategy003 | Strategy003 | 5m | 2710 | 91 | 0.73 | 0.71 | 0.60 | -1.25 | -1.36 | -73 | – | – | – | ele |
| FTD_ReinforcedQuickie | ReinforcedQuickie | 5m | 5739 | 70 | 0.80 | 0.69 | 0.86 | -2.17 | -1.43 | -92 | – | – | – | ele |
| FTD_BinHV27 | BinHV27 | 5m | 7786 | 58 | 0.93 | 0.80 | 0.84 | -0.50 | -1.54 | -77 | – | – | – | ele |
| FTD_CMCWinner | CMCWinner | 15m | 4849 | 67 | 0.63 | 0.39 | 0.61 | -2.79 | -1.69 | -92 | – | – | – | ele |
| FTD_SmoothScalp | SmoothScalp | 1m | 1558 | 60 | – | 0.63 | – | – | -1.73 | -34 | – | – | – | ele |
| FTD_ReinforcedSmoothScalp | ReinforcedSmoothScalp | 1m | 400 | 52 | – | 0.57 | – | – | -2.93 | -13 | – | – | – | ele |
| FTD_Scalp | Scalp | 1m | 5676 | 43 | – | 0.40 | – | – | -9.43 | -85 | – | – | – | ele |
| FTD_ASDTSRockwellTrading | ASDTSRockwellTrading | 5m | 7848 | 26 | 0.67 | – | 0.67 | -4.85 | – | -88 | – | – | – | ele |
| FTD_BreakEven | BreakEven | 5m | – | – | – | – | – | – | – | – | – | – | – | ele |
| FTD_InformativeSample | InformativeSample | 5m | – | – | – | – | – | – | – | – | – | – | – | ele |
| FTD_TWAPStrategy | TWAPStrategy | 15m | 5888 | 60 | 0.79 | – | 0.79 | -3.34 | – | -91 | – | – | – | ele |
| FTD_AlmgrenChrissStrategy | AlmgrenChrissStrategy | 15m | – | – | – | – | – | – | – | – | – | – | – | hata |
| FTD_TechnicalExampleStrategy | TechnicalExampleStrategy | 5m | 7640 | 46 | 0.62 | – | 0.62 | -3.62 | – | -90 | – | – | – | ele |
| FTD_Bandtastic | Bandtastic | 15m | 5089 | 62 | 0.70 | – | 0.70 | -2.83 | – | -93 | – | – | – | ele |
| FTD_DoesNothingStrategy | DoesNothingStrategy | 5m | – | – | – | – | – | – | – | – | – | – | – | ele |
| FTD_EMASkipPump | EMASkipPump | 5m | 4274 | 61 | 0.70 | – | 0.70 | -2.61 | – | -92 | – | – | – | ele |
| FTD_CofiBitStrategy | CofiBitStrategy | 5m | 6353 | 52 | 0.57 | – | 0.57 | -5.31 | – | -90 | – | – | – | ele |
| FTD_FReinforcedStrategy | FReinforcedStrategy | 5m | – | – | – | – | – | – | – | – | – | – | – | hata |

### je-suis-tm/quant-trading (11 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JT02 | JT_Heikin_Ashi | 1D | 2635 | 78 | 2.83 | 3.02 | 1.25 | 0.60 | 0.78 | -68 | 2.05 | 2.39 | 3.21 | **aday** |
| JT06 | JT_RSI_omuz_bas_omuz | 1D | 648 | 42 | 1.02 | 1.19 | 2.11 | 0.02 | 0.42 | -14 | 1.15 | 0.94 | 0.96 | ele |
| JT01 | JT_MACD_osilator | 1D | 1129 | 41 | 2.24 | 1.41 | 0.48 | 1.38 | 0.21 | -61 | 1.84 | 1.79 | 1.56 | ele |
| JT03 | JT_Awesome_osilator | 1D | 1122 | 36 | 2.56 | 1.46 | 0.44 | 1.50 | 0.16 | -69 | 2.03 | 1.78 | 1.50 | ele |
| JT10 | JT_Dual_Thrust | 1h | 11760 | 46 | 1.14 | 1.01 | 1.02 | 0.90 | 0.06 | -51 | 1.06 | – | – | ele |
| JT04 | JT_Parabolic_SAR | 1D | 2090 | 40 | 1.69 | 0.98 | 0.61 | 1.40 | -0.09 | -87 | 1.36 | 1.28 | 1.33 | ele |
| JT05 | JT_RSI_30_70 | 1D | 1607 | 71 | 0.87 | 0.90 | 2.55 | -0.21 | -0.18 | -79 | 0.80 | 0.82 | 0.96 | ele |
| JT11 | JT_Pair_trading | 1D | 1002 | 51 | 0.70 | 0.81 | 0.67 | -1.09 | -1.22 | -12 | 0.87 | – | – | ele |
| JT09 | JT_London_Breakout | 1h | 18409 | 39 | 0.58 | 0.57 | 0.59 | -4.10 | -4.82 | -136 | 0.61 | – | – | ele |
| JT07 | JT_Shooting_Star | 1D | 0 | – | – | – | – | – | – | 0 | – | – | – | ele |
| JT08 | JT_Bollinger_W | 1h | 0 | – | – | – | – | – | – | 0 | – | – | – | ele |

### backtrader (18 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BT16 | 20 mum zirvesine dokununca al, 2 gün tut | 1D | 3062 | 49 | 1.43 | 1.30 | 0.87 | 1.43 | 0.92 | -23 | 1.28 | 0.95 | 1.12 | **aday** |
| BT03 | SMA 15/50 kesişim long | 1D | 609 | 43 | 3.34 | 2.13 | 0.31 | 1.47 | 0.42 | -53 | 2.14 | 2.14 | 2.14 | ele |
| BT04 | SMA 13/50 kesişim long | 1D | 640 | 43 | 3.52 | 2.08 | 0.34 | 1.52 | 0.40 | -51 | 2.27 | 2.13 | 1.96 | ele |
| BT09 | Kapanış SMA30 long | 1D | 2496 | 23 | 1.89 | 1.38 | 0.64 | 1.47 | 0.26 | -77 | 1.73 | 1.66 | 1.43 | ele |
| BT08 | Kapanış SMA30 long-short | 1D | 4995 | 23 | 1.25 | 1.16 | 1.10 | 0.74 | 0.12 | -73 | 1.37 | 1.18 | 0.94 | ele |
| BT01 | SMA 10/30 kesişim long | 1D | 1035 | 38 | 2.40 | 1.35 | 0.50 | 1.40 | 0.09 | -67 | 2.02 | 1.90 | 1.44 | ele |
| BT02 | SMA 10/20 kesişim long | 1D | 1510 | 37 | 2.19 | 1.16 | 0.54 | 1.50 | 0.05 | -85 | 1.73 | 1.56 | 1.37 | ele |
| BT07 | Kapanış SMA15 long | 1D | 3700 | 26 | 1.78 | 1.07 | 0.83 | 1.48 | 0.05 | -96 | 1.42 | 1.42 | 1.40 | ele |
| BT18 | MACD+SMA çift sinyal (SMA10/30 & MACD 12/26/9) | 1D | 1521 | 29 | 1.54 | 0.86 | 0.39 | 1.52 | 0.03 | -86 | 1.16 | 1.14 | 1.17 | ele |
| BT12 | EMA10/20 kesişim + %2 stop | 1D | 731 | 8 | 0.19 | 5.56 | 0.40 | 0.93 | 0.03 | -57 | 0.94 | 0.30 | 338.02 | ele |
| BT10 | Kapanış SMA10 long | 1D | 4730 | 28 | 1.65 | 1.02 | 0.79 | 1.52 | -0.01 | -98 | 1.36 | 1.40 | 1.40 | ele |
| BT05 | SMA 10/30 long-short (dön) | 1D | 2056 | 36 | 1.39 | 1.08 | 1.06 | 0.83 | -0.11 | -81 | 1.50 | 1.20 | 0.86 | ele |
| BT15 | BTFD: low/high-1 <= -%1, 2 gün tut | 1D | 18075 | 49 | 1.19 | 0.98 | 0.87 | 1.01 | -0.14 | -95 | 1.05 | 1.01 | 1.07 | ele |
| BT13 | RSI 35/65 kesişim, 50'de çık (L/S) | 1D | 1254 | 66 | 0.55 | 0.77 | 0.89 | -1.00 | -0.15 | -217 | 0.59 | 0.74 | 1.16 | ele |
| BT06 | Kapanış SMA15 long-short | 1D | 7410 | 27 | 1.22 | 0.98 | 1.23 | 0.66 | -0.17 | -98 | 1.18 | 1.09 | 1.00 | ele |
| BT14 | MACD kesişim + düşen SMA30, 3xATR stop (Tharp) | 1D | 1104 | 40 | 1.74 | 0.69 | 0.67 | 0.95 | -0.69 | -93 | 1.03 | 1.33 | 1.80 | ele |
| BT17 | Hafta günü braket (Sa/Pe/Cu, ±%3, 7 gün) | 1D | 20664 | 43 | 0.64 | 0.70 | 0.63 | -3.59 | -2.87 | -580 | 0.63 | 0.96 | 0.97 | ele |
| BT11 | SMA5/15 kesişim + %2 stop/%2 hedef | 1D | 2095 | 36 | 0.47 | 0.48 | 0.51 | -3.58 | -3.49 | -69 | 0.44 | 0.96 | 0.87 | ele |

### backtesting.py (5 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BP03 | Sma4Cross 50/100 rejim, 20 giriş 10 çıkış | 1D | 2468 | 35 | 1.25 | 0.97 | 1.05 | 0.58 | -0.13 | -52 | 1.04 | 1.05 | 0.93 | ele |
| BP01 | SMA 10/20 dur-ve-dön | 1D | 3022 | 37 | 1.33 | 1.00 | 1.00 | 0.88 | -0.16 | -91 | 1.35 | 1.08 | 0.86 | ele |
| BP04 | Çoklu zaman dilimi RSI(30) günlük+haftalık >70, %8 stop | 1D | 30 | 23 | 1.62 | 0.18 | – | 0.39 | -0.34 | -5 | 2.38 | 0.51 | 0.99 | ele |
| BP02 | SMA 10/25 + 2xATR(100) iz süren stop | 1D | 1017 | 37 | 1.20 | 0.68 | 0.52 | 0.35 | -0.65 | -78 | 0.99 | 1.35 | 1.33 | ele |
| BP05 | Makine öğrenmesi kNN ileri yürüyen (1h, ±%0.4) | 1h | 1080982 | 36 | 0.25 | 0.29 | 0.26 | -43.81 | -52.88 | -12609 | 0.24 | – | – | ele |

### finmarketpy (7 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FM04 | TechIndicator ROC20 L/S | 1D | 5373 | 33 | 1.28 | 1.22 | 1.00 | 0.84 | 0.33 | -68 | 1.32 | 1.20 | 0.96 | ele |
| FM05 | TechIndicator SMA2 (20/50) L/S | 1D | 1143 | 40 | 1.64 | 1.50 | 1.10 | 0.97 | 0.26 | -67 | 1.46 | 1.14 | 1.11 | ele |
| FM06 | TechIndicator GMMA L/S | 1D | 1743 | 29 | 1.56 | 1.44 | 1.07 | 0.95 | 0.23 | -81 | 1.70 | 1.12 | 0.84 | ele |
| FM01 | SMA200 üstü long altı short, %10 vol hedefi | 1D | 1549 | 16 | 0.73 | 1.10 | 0.95 | 0.47 | 0.23 | -13 | 0.87 | 0.81 | 1.18 | ele |
| FM07 | TechIndicator Bollinger(20,2) kırılım L/S | 1D | 1093 | 42 | 1.36 | 1.46 | 1.02 | 0.79 | 0.21 | -74 | 1.56 | 1.10 | 0.85 | ele |
| FM03 | TechIndicator EMA20 L/S | 1D | 6680 | 25 | 1.23 | 1.13 | 1.13 | 0.73 | 0.15 | -83 | 1.30 | 1.14 | 0.92 | ele |
| FM02 | TechIndicator SMA20 L/S | 1D | 6110 | 26 | 1.28 | 1.06 | 1.20 | 0.77 | 0.05 | -101 | 1.23 | 1.13 | 0.96 | ele |

### QuantDinger (18 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QD16 | Düşük volatilite top 4 (60g), haftalık | 1D | 182 | 56 | 2.30 | 2.24 | 0.95 | 0.91 | 0.78 | -133 | 1.43 | 1.06 | 2.54 | **aday** |
| QD04 | Üç ortalama boğa mumu + SMA60 trend | 1D | 274 | 32 | 1.82 | 1.88 | 0.58 | 0.88 | 0.58 | -11 | 1.95 | 1.12 | 3.10 | **aday** |
| QD10 | EMA20/50 long | 1D | 502 | 36 | 2.72 | 2.54 | 0.33 | 1.32 | 0.47 | -64 | 2.71 | 1.89 | 2.24 | ele |
| QD15 | Momentum top 4 (60g), haftalık | 1D | 305 | 45 | 1.68 | 1.69 | 0.25 | 0.88 | 0.39 | -141 | 1.98 | 1.49 | 1.19 | ele |
| QD01 | Tek SMA50 long | 1D | 1751 | 22 | 2.34 | 1.74 | 0.39 | 1.53 | 0.37 | -66 | 1.98 | 1.72 | 1.63 | ele |
| QD09 | SMA20/50 long | 1D | 577 | 42 | 3.30 | 2.03 | 0.30 | 1.42 | 0.34 | -54 | 2.20 | 2.10 | 2.25 | ele |
| QD03 | Üç ortalamayı kesen boğa mumu | 1D | 741 | 27 | 1.66 | 1.28 | 0.57 | 0.95 | 0.29 | -31 | 1.84 | 1.31 | 2.40 | ele |
| QD08 | SuperTrend(10,3) long | 1D | 600 | 43 | 2.65 | 1.81 | 0.40 | 1.54 | 0.25 | -62 | 2.18 | 1.83 | 1.85 | ele |
| QD11 | Kapanış SMA20 long | 1D | 3048 | 25 | 1.93 | 1.18 | 0.77 | 1.57 | 0.20 | -95 | 1.51 | 1.52 | 1.40 | ele |
| QD17 | Momentum_20 top 5, haftalık | 1D | 722 | 48 | 2.13 | 1.09 | 0.67 | 1.40 | 0.13 | -135 | 1.50 | 1.25 | 1.24 | ele |
| QD05 | Turtle 20/10 + 2xATR stop | 1D | 809 | 34 | 2.19 | 1.45 | 0.50 | 1.35 | 0.11 | -50 | 2.02 | 1.71 | 1.51 | ele |
| QD06 | Gösterge rezonansı MACD>0, 50<RSI<75, ADX>20 | 1D | 2110 | 36 | 1.54 | 1.00 | 0.59 | 1.19 | 0.03 | -49 | 1.47 | 1.26 | 1.10 | ele |
| QD18 | Grid botu (1h, OctoBot ızgarasıyla aynı test) | 1h | 82912 | 100 | – | – | – | 0.21 | -0.12 | -39 | – | – | – | ele |
| QD02 | SMA20/60 L/S (4h, BTC şablonu) | 4h | 6327 | 36 | 1.28 | 0.93 | 1.19 | 0.79 | -0.26 | -78 | 1.24 | – | – | ele |
| QD12 | BTC long çekirdek + SMA50 altı hedge (1h) | 1h | 49065 | 18 | 1.01 | 0.87 | 0.74 | 0.16 | -0.95 | -224 | 0.91 | – | – | ele |
| QD07 | MACD+KDJ (4h), %2 stop, +%5 sonra %1 iz | 4h | 24009 | 33 | 0.88 | 0.90 | 0.82 | -1.20 | -0.97 | -148 | 0.84 | – | – | ele |
| QD14 | DCA botu (1h) | 1h | 125145 | 71 | 0.85 | 0.74 | 0.66 | -1.14 | -1.67 | -252 | 0.81 | – | – | ele |
| QD13 | Martingale (1h) | 1h | 242394 | 99 | 0.83 | 0.66 | 0.58 | -0.90 | -1.68 | -245 | 0.74 | – | – | ele |

### ai_quant_trade (9 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AQ03 | Momentum rotasyonu (skor, BTC filtresi, %15 iz) | 1D | 269 | 41 | 2.44 | 1.48 | 0.57 | 1.39 | 0.67 | -54 | 1.48 | – | – | **aday** |
| AQ08 | Ters volatilite ağırlık (aylık) | 1D | 25 | 88 | – | 67.27 | – | 1.12 | 0.28 | -128 | 12.61 | – | – | ele |
| AQ04 | MA5>10>30 dizilimi | 1D | 622 | 44 | 2.77 | 1.77 | 0.41 | 1.46 | 0.25 | -61 | 2.40 | 2.16 | 1.76 | ele |
| AQ07 | Eşit ağırlık (aylık) | 1D | 25 | 88 | – | 52.51 | – | 1.15 | 0.18 | -132 | 21.97 | 5.96 | 11.85 | ele |
| AQ06 | Kapanış > 1.01 x MA5 | 1D | 5801 | 34 | 1.47 | 1.04 | 0.70 | 1.49 | 0.13 | -95 | 1.24 | 1.33 | 1.36 | ele |
| AQ02 | MA5/20 long | 1D | 1632 | 35 | 2.24 | 1.16 | 0.58 | 1.58 | 0.06 | -80 | 1.68 | 1.43 | 1.29 | ele |
| AQ01 | MA10/20 long | 1D | 1510 | 37 | 2.19 | 1.16 | 0.54 | 1.50 | 0.05 | -85 | 1.73 | 1.56 | 1.37 | ele |
| AQ05 | Trend yargısı + %5 stop | 1D | 2659 | 31 | 1.37 | 1.23 | 0.50 | 0.86 | 0.03 | -60 | 1.10 | 1.50 | 1.94 | ele |
| AQ09 | Minervini trend şablonu + %10 stop | 1D | 141 | 19 | 0.48 | 3.51 | 9.87 | 0.46 | 0.03 | -59 | 0.84 | 0.09 | 556.57 | ele |

### OctoBot (12 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OB12 | Endeks: BTC/ETH/SOL eşit, ±%5 sapma | 1D | 3 | 100 | – | – | – | 1.20 | 0.42 | -154 | – | – | – | ele |
| OB08 | RSI-MA uç seviyeler 39.57/67.45 | 1D | 131 | 73 | 5.65 | 2.38 | 2.87 | 0.91 | 0.34 | -115 | 2.36 | 4.60 | 14.19 | ele |
| OB07 | EMA9/21 kesişim (4h; doküman 5m) | 4h | 7156 | 29 | 1.56 | 1.10 | 0.83 | 1.66 | 0.25 | -90 | 1.30 | – | – | ele |
| OB10 | Smart DCA (4h) | 4h | 3579 | 100 | – | – | – | 0.83 | 0.17 | -42 | – | – | – | ele |
| OB06 | RSI(10)<28 al, %15 stop %25 hedef | 1D | 896 | 43 | 1.44 | 1.03 | 0.82 | 0.58 | 0.04 | -45 | 1.17 | 1.49 | 2.17 | ele |
| OB09 | RSI-MA normal seviyeler 48.62/53.63 | 1D | 451 | 51 | 3.99 | 1.41 | 0.56 | 1.45 | 0.02 | -73 | 2.40 | 2.92 | 1.82 | ele |
| OB11 | Simple DCA haftalık, satış yok | 1h | 0 | – | – | – | – | 0.25 | -0.01 | -236 | – | – | – | ele |
| OB02 | EMA21 ±%2 (4h) | 4h | 5792 | 66 | 1.08 | 0.97 | 0.65 | 0.13 | -0.07 | -94 | 0.98 | – | – | ele |
| OB05 | SMA50/200 altın kesişim | 1D | 175 | 42 | 2.64 | 1.59 | 1.32 | 0.78 | -0.07 | -74 | 1.18 | 2.27 | 5.61 | ele |
| OB01 | Bollinger momentum (ortalamaya dönüş, 4h) | 4h | 7181 | 64 | 1.05 | 0.90 | 0.63 | 0.07 | -0.28 | -104 | 0.94 | – | – | ele |
| OB03 | EMA50 sapma (4h) | 4h | 11201 | 81 | 1.09 | 0.85 | 0.59 | 0.21 | -0.36 | -150 | 0.94 | – | – | ele |
| OB04 | StochRSI uçları (4h) | 4h | 9984 | 59 | 1.20 | 0.86 | 0.72 | 0.61 | -0.57 | -121 | 1.06 | – | – | ele |

### binance-trading-bot (4 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BB03 | Rebalance sabit BTC.5/ETH.3/SOL.2 (4h) | 4h | 3 | 100 | – | – | – | 1.06 | 0.43 | -146 | – | – | – | ele |
| BB01 | Trailing Trade (1h, örnek ayar) | 1h | 49244 | 53 | 0.99 | 0.92 | 0.84 | -0.10 | -0.79 | -196 | 0.94 | – | – | ele |
| BB04 | Rebalance momentum top 3 (1h, 30 mum) | 1h | 28679 | 37 | 1.06 | 0.86 | 0.83 | 0.59 | -1.73 | -714 | 0.87 | – | – | ele |
| BB02 | Momentum EMA9/21 + SMA200 + %5 iz (1h) | 1h | 237 | 34 | 1.06 | 0.32 | 0.69 | 0.10 | -1.87 | -6 | 0.84 | – | – | ele |

### awesome-systematic-trading (32 test)

| ID | Strateji | TF | İşlem | WR % | PF IS | PF OOS | PF 2022 | Sh IS | Sh OOS | DD % | PF stres | PF gel IS | PF gel OOS | Karar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AS12 | Momentum + yüksek volatilite (6 dilim) | 1D | 104 | 50 | 0.80 | 1.29 | 1.06 | -0.01 | 1.14 | -42 | 2.01 | 1.49 | – | ele |
| AS30 | MAX: 10 gün zirvesinde long (Padysak-Vojtko) | 1D | 4736 | 33 | 1.29 | 1.30 | 0.83 | 0.92 | 0.87 | -27 | 1.25 | 1.15 | 1.02 | **aday** |
| AS11 | Düşük volatilite top 6 | 1D | 87 | 63 | 2.20 | 3.60 | 1.00 | 0.42 | 0.86 | -129 | 1.14 | 1.77 | – | ele |
| AS05 | Düşük beta (BAB) BTC'ye göre | 1D | 128 | 52 | 1.82 | 0.86 | 1.15 | 0.91 | 0.81 | -40 | 0.74 | 1.13 | 0.84 | ele |
| AS09 | Momentum 1/1 (stil rotasyonu) | 1D | 53 | 49 | 0.66 | 3.27 | 0.76 | -0.09 | 0.80 | -115 | 0.92 | 1.41 | 2.94 | ele |
| AS02 | 52 hafta zirvesi (L/S, 3 dilim) | 1D | 107 | 47 | 0.68 | 1.87 | 0.81 | -0.07 | 0.74 | -38 | 1.26 | 1.55 | – | ele |
| AS16 | Yeniden dengeleme primi | 1D | 427 | 90 | – | 1.25 | – | 0.34 | 0.67 | -21 | 0.44 | 0.88 | 0.73 | ele |
| AS15 | Çift işlemi mesafe (365g, 20 çift, 2sd) | 1D | 378 | 50 | 0.79 | 1.18 | 0.18 | 0.02 | 0.61 | -38 | 1.14 | 1.05 | 0.83 | ele |
| AS17 | Getiri asimetrisi (5/5) | 1D | 191 | 52 | 1.43 | 1.03 | 1.45 | 0.33 | 0.57 | -41 | 1.01 | 0.82 | – | ele |
| AS18 | Kısa vadeli dönüş (haftalık) | 1D | 2153 | 52 | 0.79 | 1.08 | 0.86 | -1.61 | 0.57 | -213 | 0.94 | 0.96 | 1.25 | ele |
| AS13 | Eşli geçiş BTC/ETH (90g, çeyreklik) | 1D | 12 | 58 | 2.74 | 2.73 | 1.14 | 0.82 | 0.24 | -138 | – | – | – | ele |
| AS07 | Momentum 3/3 (365g) | 1D | 111 | 50 | 0.68 | 1.31 | 0.57 | -0.46 | 0.22 | -93 | 0.90 | 1.15 | 3.28 | ele |
| AS10 | 6 ay momentum top 3, çeyreklik | 1D | 45 | 62 | 1.94 | 2.74 | 0.62 | 0.73 | 0.18 | -162 | 2.19 | 2.75 | 19.56 | ele |
| AS03 | Momentum rotasyonu top 5 (365g) | 1D | 72 | 50 | 1.15 | 1.80 | 0.28 | 0.22 | 0.14 | -143 | 1.26 | 2.63 | 5.59 | ele |
| AS04 | Trend takibi (kapanış > 300g SMA) | 1D | 140 | 43 | 3.58 | 1.48 | 4.05 | 0.50 | 0.10 | -206 | 0.82 | 0.95 | – | ele |
| AS29 | Tüm zamanların zirvesi + 1xATR(10) iz | 1D | 502 | 37 | 1.38 | 1.08 | 0.27 | 0.74 | 0.08 | -17 | 1.42 | 1.00 | 1.26 | ele |
| AS32 | Aşırı tepki ertesi gün (Caporale-Plastun) | 1D | 3467 | 43 | 0.81 | 1.02 | 0.71 | -0.62 | 0.07 | -77 | 0.82 | 1.13 | 1.26 | ele |
| AS08 | Momentum faktörü 5/5 (365g) | 1D | 149 | 50 | 0.69 | 1.11 | 0.98 | -0.56 | 0.06 | -98 | 0.97 | 1.13 | 1.53 | ele |
| AS31 | MIN: 10 gün dibinde long (Padysak-Vojtko) | 1D | 4893 | 66 | 1.51 | 1.00 | 0.81 | 0.74 | 0.01 | -45 | 1.04 | 0.91 | 1.02 | ele |
| AS01 | 12 aylık döngü (L/S) | 1D | 516 | 51 | 0.84 | 0.99 | 1.17 | -0.70 | -0.08 | -121 | 0.88 | 0.97 | 1.39 | ele |
| AS06 | Tutarlı momentum (6 ay tut) | 1D | 86 | 49 | 0.66 | 1.46 | 1.50 | -0.11 | -0.08 | -73 | 1.28 | 0.86 | 1.02 | ele |
| AS25 | Maaş günü (15->16) | 1D | 1776 | 43 | 0.73 | 0.92 | 0.47 | -0.48 | -0.13 | -62 | 0.70 | 0.96 | 0.62 | ele |
| AS21 | Küçük ölçek (dolar hacmi vekil) | 1D | 160 | 57 | 3.43 | 0.63 | 1.88 | 2.02 | -0.15 | -50 | 1.37 | 1.11 | 0.82 | ele |
| AS23 | Kalıntı momentum (BTC faktörü) | 1D | 122 | 49 | 0.51 | 1.07 | – | -0.29 | -0.17 | -34 | 1.53 | 1.14 | 1.21 | ele |
| AS19 | Çarpıklık (5/5) | 1D | 128 | 47 | 1.14 | 0.85 | 1.44 | 0.22 | -0.24 | -45 | 0.82 | 0.95 | 0.64 | ele |
| AS26 | Ocak barometresi | 1D | 82 | 61 | – | 4.55 | – | 1.48 | -0.25 | -74 | 6.63 | 5.33 | 17.79 | ele |
| AS24 | Ay dönümü | 1D | 1792 | 51 | 2.34 | 0.79 | 1.08 | 1.34 | -0.36 | -56 | 1.40 | 1.24 | 0.94 | ele |
| AS22 | ETH/BTC yayılımı 20g SMA | 1D | 536 | 50 | 0.83 | 0.94 | 0.91 | -0.99 | -0.36 | -132 | – | – | – | ele |
| AS14 | Çift işlemi mesafe (120g, 5 çift, 0.5sd) | 1D | 1433 | 52 | 0.85 | 0.96 | 0.88 | -1.30 | -0.37 | -131 | 1.04 | 1.11 | 0.84 | ele |
| AS27 | Vade haftası (son Cuma) | 1D | 1787 | 45 | 1.29 | 0.65 | 1.75 | 0.37 | -0.67 | -54 | 0.90 | 0.98 | 1.03 | ele |
| AS20 | Zaman serisi momentumu (vol hedefli) | 1D | 190 | 41 | 1.10 | 1.21 | 1.84 | 0.09 | -1.06 | -34 | 0.84 | 0.38 | – | ele |
| AS28 | Bitcoin gün içi mevsimsellik 22-00 UTC | 1h | 54308 | 44 | 0.86 | 0.72 | 0.71 | -1.29 | -2.61 | -282 | 0.85 | – | – | ele |

