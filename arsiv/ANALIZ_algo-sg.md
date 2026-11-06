# algo-sg incelemesi (1L3A için) — Rapor

Kapsam: /home/user/algo-sg (HEAD dfe7973, tek commit görünüyor, sığ klon). Salt okunur. Tek `git fetch` (kagit-durum). Not: bir de GitHub MCP ile `actions_list` denendi (salt okunur), sonuç boş döndü (0 çalıştırma; erişim/izin belirsiz), bu yüzden bot durma nedeni doğrulanamadı.
Kısaltmalar: IS = optimizasyon dönemi, OOS = optimizasyona katılmayan dönem, PF = kâr faktörü, WR = kazanma oranı, R = riske edilen birim, DD = en büyük düşüş.

## 1. Amaç, kapsam, zaman çizelgesi, durum
- Amaç: Binance USDT-M perpetual, 25 coin; 1D/4H yön + 1H işlem; 2-3 strateji, her biri WR >= %45 ve PF > 1.3, OOS pozitif (PROGRESS.md "Bağlam").
- Kitaplar: 19-20 algo-trading kitabı `metinler/*.md` (Davey, Pruitt, Halsey, Ratford, Kılınçarslan tezi, D'errico, Jansen vb.; metinler/README.md). Kurallar bu kitaplardan alınıp veriyle "yeniden seçildi" (STRATEJILER.md §1).
- Aşamalar (PROGRESS.md): 1) veri+motor+araştırma (s1-s5) -> A, B, C; 2) denetim (DENETIM.md): C, A'nın modülü yapıldı (A2); 3) kağıt bot (paper/); 4) haftalık yön + günlük işlem (D1, D2; STRATEJILER_GUNLUK.md); 5) dış depo analizi (DIS_STRATEJILER.md); ayrıca A v2/kaldıraç (docs/A_V2_VE_KALDIRAC.md) ve başka bir deponun (day-trade-sg) çapraz denetimi (DENETIM_CAPRAZ_DAYTRADE.md).
- Veri 2026-10-08 civarına kadar; son birleştirme PR #7 (2026-10-13). Dış metin: "DURUM: TAMAMLANDI" (PROGRESS.md:3) ama kağıt bot maddesi "DEVAM EDİYOR".
- Şu an: araştırma tamam; kağıt bot 2026-10-10 başladı, 60 gün planlı (paper/config.json), ama **kagit-durum dalının son güncellemesi 2026-10-16 00:23 UTC** (FETCH_HEAD f02b4bb). Bugün 2026-11-06: ~3 hafta bayat. Gerçek para yok.

## 2. Veri
- Kaynak: data.binance.vision (aylık+günlük zip) 1h kline + funding (scripts/fetch_data.py:1-8,40-60). Binance API sandbox'tan engelli, bu yüzden arşiv.
- Evren (scripts/fetch_data.py:12-15): BTC ETH BNB SOL XRP ADA DOGE AVAX LINK DOT LTC TRX BCH ATOM NEAR UNI ETC FIL XLM APT ARB OP INJ SUI AAVE = "hacme göre ilk 25" ama liste sabit, bugünün listesi. APT/ARB/OP/INJ/SUI 2022-23'te listelenmiş (öncesi veri yok).
- Stres evreni (.github/workflows/fetch-data.yml): LUNA FTT SRM MATIC EOS WAVES XMR ALGO ICP SAND MANA AXS CRV EGLD THETA VET XTZ ZEC DASH COMP (data_extra/). Hepsi delist değil (MATIC, XMR vb. sonradan kalktı/azaldı; LUNA/FTT/SRM gerçek çöküş).
- Zaman dilimi: yalnız 1h saklanır; 4h ve 1D, 1h'den `resample` (algo/data.py:71-73). Hafta: Pazartesi 00:00 UTC (algo/daily.py).
- İndirme: GitHub Actions `fetch-data` (push ile data/REFRESH veya script değişince; yml). Sonuç repoya commit (data/ 44 MB). Geleneksel: `fetch-geleneksel` + yfinance (Mag7, BIST10, altın, petrol; data_gel/1d). Dakikalık freqtrade: `dis-dakika` (5 paralel runner, ~150 dk).
- Bölme: IS 2020-01..2023-12, OOS 2024-01.. (algo/run.py:12 `IS_END="2024-01-01"`). Eksik saatler önceki kapanışla "düz mum" doldurulur (algo/data.py:47-53), funding saatlik toplanır (data.py:67-68).
- 1L3A ile fark: 1L3A veri sözleşmesi 5m + parquet + sha256; burada 1h gz-csv. Burada 5m/15m yok (dakikalık yalnız dış freqtrade testinde, dis_kaynak/ft/).

## 3. Backtest motoru (algo/backtest.py)
Doğrulanan (kodda gördüm, 8 birim test: tests/test_backtest.py):
- Giriş: sinyal i. mum kapanışı, giriş i+1 açılışı (backtest.py:36-37). Üst ZD verisi mum kapanınca aktarılır (data.py:76-87: `known_at = index+1h`); Donchian seviyeleri `.shift(1)` (features.py:124-126). Lookahead göstergelerde yok (kendi taramamda bulgu yok).
- Mum içi: aynı mumda stop ve hedef -> önce stop (backtest.py:55-66). Gap: stop ötesinde açılışta çıkış (`min(stop,o[j])`). Stop/BE/iz süren stop mum KAPANIŞINDA güncellenir, sonraki mumdan geçerli (satır 99-110). Muhafazakâr.
- Maliyet: COST=0.0007 taraf (komisyon 0.05 + kayma 0.02; backtest.py:14), giriş ve çıkış aynı sabit oran; R'ye çevrim `2*cost/sl_pct` (satır 115). Funding: gerçek Binance oranı, her saat `funding*yön*kalan` (satır 52), kısmi kârdan sonra kalan pozisyona göre (denetimde düzeltildi).
- Boyut: portföy.py: lev=risk/sl_pct, toplam nominal tavanı 5x, eşzamanlı pozisyon sınırı, coin başına tek pozisyon (portfolio.py:226-253). Kasa girişteki özsermayeye göre (bileşikli); raporlanan "bileşiksiz MTM" ayrıca.
Benim bulduğum iyimser/riskli noktalar:
1. Kayma 0.02% sabit; stop çıkışları ve kriz girişlerinde (B: -%15 sonrası saatlik açılış) gerçekçi değil. B'nin en büyük kâr günleri 2024-08-05 (25 işlem, +25R), 2025-10-10 (19 işlem, +15R), 2025-04-07 (+14R) çöküş günleri; o saatlerde defter boş, fiyat dolum gerçekçi değil. Day-trade çapraz denetimi maliyet 0.12-0.16%'de kenarın kaybolduğunu gösterdi (DENETIM_CAPRAZ_DAYTRADE.md #8) - burada A/B için benzer duyarlılık testi yok (yalnız 1-2 saat gecikme).
2. Evren seçim yanlılığı: hayatta kalan/bugünün büyükleri (bkz. §9). Day-trade denetimi aynı sorunda OOS PF 1.74 -> 1.27 düşürdü (bulgu #3); algo-sg için PIT-evren testi yapılmamış.
3. Kayıp işlemlerde ortalama R -1.02..-1.07 (kayıp 1R'yi aşıyor, gap/maliyet); kabul edilebilir, tutarlı.
4. BE stop = giriş + 2*cost (satır 106) iyi. Ama TP1 + aynı mumda stop sırası: stop önce -> muhafazakâr.
5. Funding girişin açıldığı mumda da ödenir (satır 52, j=e_i): küçük.
6. Kağıt botta spot mum + OKX funding kullanılıyor, backtest vadeli + Binance funding (paper/README.md "Veri"). Hacim katsayısıyla ölçekleniyor (volume_scale.json). A1'in hacim filtresi (>=1.5x) bu yüzden canlıda yaklaşık.
7. Mum `open` ile giriş: 1H açılış anındaki fiyat; bot günde 24 saat çalışsa bile gerçek emir gecikmesi yok sayılıyor.
8. Rapor yöntemi: "A+B eşit ağırlık Sharpe 1.45" günlük yüzde ortalaması; docs/A_V2_VE_KALDIRAC.md basit 50/50 ile 1.25 buluyor (kendileri belirtmiş). İki sayı karışabilir.

## 4. Stratejiler
Sonuçlar: STRATEJILER.md §3, results/final_summary.json (kontrol ettim, tutuyor: A 3147 işlem, B 996).

### A (A1+A2) — Trend kırılımı (long+short)
- A1 (algo/final.py:200-203): 4H kapanış önceki 20 mumun zirvesini/dibini kırar, 4H hacim >= 1.5x ortalama, kapanış 4H EMA100'ün doğru tarafında; long için BTC günlük > EMA200 (short'ta BTC filtresi yok). Giriş sinyalden sonraki 1H açılış. Stop 2x ATR(4H). %25'i 1R'de kapat + BE, kalan için 10x ATR(4H) iz stop, 4H kapanış EMA100'ü ters keserse çık, max 720 saat.
- A2: günlük Donchian(20) kırılımı, 4H EMA200 tarafı, BTC filtresi (long), stop 4x ATR(4H), iz 15x ATR, çıkış EMA200, max 720 saat.
- Risk %0.5/işlem, en çok 10 pozisyon, toplam 5x nominal.
- Sonuçlar (final_summary.json): ALL 3147 işlem, WR 50.1, PF 1.61, ort R +0.254; IS 1713 işlem WR 51.4 PF 1.66; OOS 1434 işlem WR 48.5 PF 1.545. Bileşiksiz MTM: yıllık %26.9, DD -%34.2, Sharpe 0.99. Bileşikli gerçekleşen: DD -%29.6. Stres: 2781 işlem WR 48.6 PF 1.40 (IS 1.24 / OOS 1.62). Yıllık PF: 2020 1.17, 2021 2.04, 2022 1.91, 2023 1.58, 2024 2.21, 2025 1.17, 2026* 1.14 (WR %39.6).
- Kendi hesabım (results/final_trades_A.csv): ilk %5 işlem pozitif R'nin %64'ünü veriyor; bu %5'i çıkarınca toplam R +800 -> -551. Yani klasik "az sayıda dev trend". Medyan kazanç +0.25R, medyan kayıp -1.02R; WR %50 ama kâr kuyruktan.
- Parametre seçimi: grid_s5_*.csv (s5 ızgaraları) IS skoru `avg_R*sqrt(n)` ile sıralanır (run.py grid), ama aynı satırda OOS sütunları da yazılır; ayrıca "teşhis" OOS'a bakılarak yapıldı (PROGRESS.md: "2024-26 OOS'ta EMA filtresinin gücü yok"). Denetimde kabul kuralı "ana (IS+OOS) VE stres evreninde iyileşme" (DENETIM.md baş). Yani OOS ve stres birden çok kez seçim döngüsüne girdi.
- Parametre platosu: 144 komşu A ayarında getiri/DD medyanı 1.15, hiçbiri zararda değil (STRATEJILER.md §4; results/pgrid_A3.csv).
- Short bacağı: OOS'ta BTC<EMA200 rejiminde short PF 0.90 (n=324), BTC>EMA200'de 1.12 (docs/A_V2_VE_KALDIRAC.md); A "yalnız long" 2022'de zarar. A v2 (rejime bağlı short) reddedildi.
- Kaldıraç: izole teminat A için <=5x güvenli; riski büyütmek önerilmedi (1.5-2x'in üstünde DD katlanıyor).

### B — Kapitülasyon dönüşü (yalnız long)
- Kural (final.py:210; strategies.py s4): coin 24 saatlik basit getirisi <= -%15 ise sinyal mumu kapanışı, giriş sonraki açılış. Stop 4x ATR(4H) (medyan stop mesafesi %22!), 1R'de BE, 96 saat zaman çıkışı. Risk %0.75, max 25 pozisyon.
- Sonuç: 996 işlem WR 64.0 PF 1.78; IS 645 işlem WR 60.8 PF 1.41; OOS 351 işlem WR 69.8 PF 2.67. Stres 1007 işlem WR 60.2 PF 1.65 (IS 1.45/OOS 2.40). Bileşiksiz MTM yıllık %12.1, DD -%18.5, Sharpe 0.86. Yıllar: 2022 PF 0.95 (n=168), 2023 PF 16.7 (n=35), 2024 2.85, 2025 2.55.
- Kendi hesabım: 996 işlem ~234 ayrı günde; >=5 işlemli 53 günün R'si 87 / toplam 156 (%56). Yani bağımsız "olay" sayısı ~50-60; örneklem işlem sayısı gibi görünmüyor. En kötü ay 2020-03: -16.5R.
- B'nin R'si büyük stop mesafesine bölündüğünden medyan kazanç +0.45R ve kayıp -0.45R; WR yüksek olması stopun çok uzak olmasıyla ilgili (kayıpların çoğu zaman çıkışı, stop vuran sadece 157/996).
- Belge-kod: eşik logaritmikken "%15" yazılması düzeltildi; BTC filtresi aşırı uyum bulunup kaldırıldı (DENETIM.md #3,#4 - doğru tespit; tablo §3 gerçekten komşuları zayıf).
- Davey çelişkisi dürüstçe not edilmiş: B fiilen Davey'in en kötü bulduğu "Percent Decrease" yöntemi (DENETIM.md §2).

### D1 / D2 (günlük işlem + haftalık yön) — algo/final_daily.py, STRATEJILER_GUNLUK.md
- D1: Elder Impulse haftalık (EMA13 eğimi + MACD hist eğimi) yönü; günlük: 20 günlük bacakta yeni zirve, fiyat bacağın %50'sine iner ve üstünde kapatır; stop 3 ATR20, %33'ü 0.6R'de kapat+BE, çıkış 10 gün Turtle kanalı, max 90 gün; risk %1. Ana 810 işlem WR 49.1 PF 1.58 (IS 1.64/OOS 1.51); stres 618 işlem PF 1.33 (IS **1.08**). Yıllık %16.1, DD -%22.8. 2020 stres PF 0.08.
- D2: Elder "kırmızı değil" + 2 günde >= %20 düşüş (long) ; stop 3 ATR20, SMA5 üstü kapanışta çıkış, max 15 gün; ana 143 işlem WR 76.9 PF 4.14 (IS 5.12/OOS 2.68); stres 156 işlem PF 2.33. Yıllık %2.9. Yılda ~21 işlem: B ile aynı fikir. Kağıt bota eklenmedi.
- Kombine D1+D2: yıllık %8.3, DD -%11.3, her yıl pozitif.
- Seçim: daily_grid1..7 (~512 satır). Haftalık yön filtresi "teşhis" tablosu (§2) hem IS hem OOS'a bakarak seçildi.

### Elenen stratejiler (neden)
| Strateji | Aile (1L3A) | Sonuç | Neden elendi |
|---|---|---|---|
| s1: 1H RSI/BB trend geri çekilme (Ratford, Davey MR#1/#3) | swing/daytrade__ma-geri-cekilme, bant-donus, rsi-asiri-donus | PF < 1 (grid_s1_a.csv) | maliyet sonrası kenar yok |
| s2: 1H Donchian kırılımı | daytrade__donchian-kirilim | zarar | 1H kırılımlar sahte (Davey bar boyutu) |
| s3: Fibonacci %50-61.8 ölçülü hareket (Halsey, Altın Oran, Price Action Algo) | fib-geri-cekilme (3 stil) | IS zayıf+, OOS PF ~0.85 | OOS çöktü |
| 4H kırılım + 1H geri test girişi | kirilim-geri-test | anında girişten kötü | |
| 24 saatlik momentum patlaması | momentum | WR<%45, OOS zayıf | |
| B + BTC "çökmüyor" filtresi | - | PF 1.96 -> 1.35 doğru hesapla | aşırı uyumlu tepe (DENETIM §3) |
| Davey #4 MA stretch (d1_ema20 -%15..25) | ma-geri-cekilme/bant-donus | PF 1.12-1.25 | zayıf |
| Davey #2&#3&#4 VE kombinasyonu | - | IS PF 2.7, OOS < 1 | az işlem, aşırı uyum |
| Turtle LTLF, kayıp sonrası bekleme, yüksek vol anahtarı | cikis/risk | karışık/kötü | denetim §2 |
| C (günlük Turtle ayrı kol) | donchian-kirilim | A ile %95 çakışma | mükerrer -> A2 |
| Elder üçlü ekran (RSI2), Turtle+haftalık Donchian, Elder Impulse ilk gün, Halsey kitap seviyeleri | rsi-asiri-donus, donchian, fib | PF 1.0-1.3 veya IS iyi/OOS 1.0 | STRATEJILER_GUNLUK §3 |
| A v2 (short yalnız BTC<EMA200) | - | Sharpe düştü | 2022'ye uyumlu, OOS'ta bozdu |

## 5. Kağıt bot
- Mimari: GitHub Actions `kagit-al-sat` (.github/workflows/kagit.yml): cron "13 * * * *" ve "43 * * * *" (saatte 2 kez); `paper/fetch_live.py` Binance spot (data-api.binance.vision) + OKX funding çeker; `paper/engine.py` her çalıştırmada kağıt dönemini BAŞTAN backtest koduyla yeniden oynatır (engine.py:3-8). Durum `kagit-durum` dalına (durum.json, islemler.csv, pozisyonlar.csv, ozsermaye.csv, live/), günlük rapor GitHub issue'ya. Bitince `BITTI` dosyası.
- Başlangıç 2026-10-10 00:00Z, 60 gün (bitiş 2026-12-09), 10.000 $ (A 5.000 / B 5.000) (paper/config.json).
- Son durum (durum.json): son mum 2026-10-15 23:00; toplam 9.587,86 $ (-%4.12), DD -%4.23. A: 19 kapalı işlem, WR %15.8, PF 0.05, ort R -0.77, 7 açık; B: 0 kapalı, 2 açık (+14.7 $). Beklenti: A WR %50 PF 1.6, ~39 işlem/ay; B WR %64 PF 1.78, ~12/ay. A'nın ilk 6 gününde 15 stop (10 Ekim sonrası kısa süreli whipsaw; çoğu long ve short stop yedi). 19 işlemlik örneklem istatistiksel olarak anlamsız (binom: WR 0.5 iken 3/19 yaklaşık %0.2 olasılık, yani gerçekten kötü başlangıç ama tek bir rejim kırılımı olayı), A'nın 39 işlem/ay beklentisi 6 günde 28 işlem ile uyumlu.
- Neden durdu (doğrulanamadı; olası nedenler):
  1. **Actions kotası**: README "2 saatte bir (~360 dk/ay)" diyor ama yml saatte 2 çalıştırma (48/gün). Her çalıştırma ~1-2 dk (pip cache + 25 sembol özellik hesabı) => ~1.400-2.900 dk/ay; PROGRESS.md iki gizli repo 2.000 dk/ay paylaşıyor diyor. Kota bitmesi çok olası. Ay sonu sıfırlanınca devam etmesi beklenirdi; devam etmediyse (kagit-durum son commit 10-16) başka neden.
  2. Zamanlanmış workflow'lar 60 gün etkinlik yoksa devre dışı kalır (burada tetikleyici değil, repoda 13 Ekim'de PR vardı).
  3. Çökme: 11 Ekim'de tz-naive/aware hatası görülmüş ve düzeltilmişti (PROGRESS.md); benzer bir hata sonrası çalıştırmaları durdurmuş olabilir. Veri kesintisi (data-api.binance.vision) da mümkün.
  4. Kullanıcı/oturum durdurmuş (PROGRESS: haftalık değerlendirme rutini kapalı).
  Kesin neden için Actions günlükleri gerek (ben görmedim).
- Backtest vs gerçekleşen: kağıt bot "yeniden oynatma" olduğundan **gerçek icra testi değildir** (day-trade denetimi aynı mimariyi bu yüzden eleştirdi, DENETIM_CAPRAZ #5). Kayma, gecikme, spread ölçülmüyor. Spot mum + OKX funding de farklı kaynak.
- Belge-kod çelişkisi: paper/README.md ":43, 2 saatte bir" vs yml iki cron saatlik; workflow yorumu "saatte iki kez". Ayrıca README "60 gün" vs PROGRESS "2 ay".

## 6. Pano / raporlama / bildirim
- Web pano yok. Raporlama: `paper/engine.py` `_report` ile ozet.md + günlük rapor GitHub issue'ya (issue yorumu -> GitHub bildirimi e-posta/telefon). Telegram yok. results/*.png (final_equity.png, stress_equity.png) matplotlib grafikleri. 1L3A'nın "dashboard + Telegram" hedefi için alınacak hazır pano yok; rapor şablonu (açık pozisyon/son 15 işlem/beklenti-gerçekleşen karşılaştırma tablosu) fikir olarak kullanılabilir.

## 7. dis_kaynak/
- 10 depo (freqtrade-strategies, je-suis-tm/quant-trading, awesome-systematic-trading, binance-trading-bot, OctoBot, QuantDinger, ai_quant_trade, finmarketpy, backtesting.py, backtrader) taranmış: ~334 kayıt; 142 kural >=1h + 40 dakikalık freqtrade stratejisi test edildi (DIS_STRATEJILER.md §1,3). Kod: dis_kaynak/kurallar.py, awesome.py, jesuistm.py, calistir.py; freqtrade stratejileri dis_kaynak/ft/strategies/ (~68 dosya, kendi kodlarıyla freqtrade 2026.9, futures, ücret %0.07, 990 $ sabit pay).
- Sonuç: **hiçbiri bota eklenecek düzeyde değil.** Ön eleme (iki dönemde PF>1.2, Sharpe>0.5, stres PF>1.1) 7 aday geçti; sağlamlık (komşu parametre, 1 gün gecikme, al-tut, 2022) testlerini geçen yok. Dakikalık 40 freqtrade stratejisi: hiçbiri geçmedi (en iyi CombinedBinHAndCluc 5m PF 1.16/1.18, 2022 PF 0.90). Yüksek WR (%70-95) ama PF<1.
- Geleceği gören stratejiler: GodStraNew, Zeus, DevilStra (orijinal PF 2.8/2.4/1.3 -> düzeltilince 1.16/1.08/1.25 ve OOS<1).
- Geleneksel evren (Mag7, BIST10, altın, petrol; 88 kural): eşit ağırlıklı al-tut'u iki dönemde de geçen yok.
- Araştırma fikirleri: N-gün zirve kırılımı ertesi gün devam (1 gün gecikmede çöküyor), QuantDinger "üç ortalamayı kesen boğa mumu + SMA60" (OOS Sharpe 0.46-0.64).
- Doğrulamam: sonuç CSV'leri (dis_kaynak/sonuc_*.csv) var; tabloyu DIS_STRATEJILER.md'den okudum, kodu tek tek yeniden koşmadım (ortamda numba/freqtrade yok). "Elenme" kararı muhafazakâr ve makul.

## 8. 1L3A'ya aktarım önerisi
(a) Kod modülleri (algo-sg -> 1L3A motor/)
- `algo/backtest.py` `_simulate`: 1H için yazılmış, numba; 1L3A motoru Decimal tabanlı. Doğrudan almak yerine **kuralları referans/çapraz kontrol** olarak al: sinyal kapanış/giriş açılış, stop-önce, gap açılıştan, stop kapanışta güncellenir, kısmi kâr + BE, funding kalan pozisyona göre. tests/test_backtest.py'deki 8 test senaryosu 1L3A testlerine aynen taşınabilir (iyi değer).
- `algo/data.py` `to_1h` üst-ZD hizalama mantığı (kapanış zamanına göre `known_at`): 5m için genelleştirilerek alınabilir (lookahead güvenliği). `resample(label=left, closed=left)`.
- `algo/portfolio.py`: olay tabanlı portföy simülasyonu (slot, coin başına tek pozisyon, toplam nominal tavan, açık pozisyon MTM DD) - 1L3A sert limitleriyle uyumlu fikir; Decimal'e uyarlanmalı.
- `algo/indicators.py` (Wilder RSI/ATR/ADX, Donchian): küçük, 1L3A göstergeleriyle karşılaştırma için.
- `scripts/fetch_data.py`: data.binance.vision aylık/günlük zip + funding; 1L3A zaten benzerini yapıyor (sha256, parquet). Funding'de ts // 1000 normalizasyonu (mikrosaniye) detayı faydalı.
- `scripts/denetim_daytrade.py` (DSR, PIT evren, gecikme/maliyet duyarlılığı) ve DENETIM_CAPRAZ_DAYTRADE.md: 1L3A Aşama 2 eleme eşikleri (kullanıcı kararı bekleyen #3) için hazır kontrol listesi: deflated Sharpe, maliyet x2, 1 mum gecikme, PIT evren, kâr yoğunlaşması.
- `paper/`: GitHub Actions "yeniden oynatma" mimarisi 1L3A'ya UYMAZ (DigitalOcean, canlı WS, gerçek emir simülasyonu). Sadece rapor formatı ve "beklenen vs gerçekleşen" tablosu alınabilir.
- Funding/kayma modeli: 1L3A zaten daha ayrıntılı (kayma ayrı); burada kayma sabit 2 bp - 1L3A daha iyi.
(b) Aday strateji olarak
- A1/A2 (Donchian kırılımı + hacim + EMA/BTC rejim filtresi, 4H/1D): 1L3A'da `daytrade__donchian-kirilim`, `swing__donchian-kirilim`; 1L3A ADAY_RAPORU swing havuzu güçlü. 1L3A'nın 5m min. TF'sinde 4H/1D sinyal 5m'den resample edilerek çalışır, A1 zaten 1H'de giriş. En güçlü aday, çünkü kripto + binance perp + 6.8 yıl + stres evreni. Yeniden test: PIT evren, 5m giriş, kayma modeli.
- B (24s -%15 kapitülasyon dönüşü, long): aile `swing__yeni-dip-sonrasi-donus` / `swing__bant-donus` / `swing__rsi-asiri-donus`. Kitap yaygınlığı düşük ama kripto-spesifik; olay sayısı az (~50-60 bağımsız gün), kriz fiyatı doldurma riski yüksek. Aday ama kayma stresiyle (örn. 0.3%) ve "ertesi saat açılışı" yerine gecikmeli giriş ile.
- D1 (Elder haftalık Impulse + Halsey %50): `swing__fib-geri-cekilme` + `swing__macd-sinyal`; stres IS zayıf; düşük öncelik. D2 B ile aynı fikir.
(c) Negatif bilgi ("denendi-başarısız", kriptoda 2020-2026, maliyet+funding dahil)
- `daytrade/swing__ma-geri-cekilme`, `bant-donus`, `rsi-asiri-donus` (1H trend yönünde RSI/BB geri çekilme): PF<1.
- `daytrade__donchian-kirilim` 1H: zarar; 4H/1D'de çalışır. `swing__donchian-kirilim`: A olarak pozitif.
- `fib-geri-cekilme` (3 stil; Halsey/Altın Oran/Price Action Algo): OOS PF ~0.85; D1 kitap seviyeleriyle PF 1.15.
- `kirilim-geri-test`: 4H kırılım sonrası 1H geri test girişi, anında girişten kötü.
- `swing__heikin-ashi-donus`: je-suis-tm HA günlük long PF 2.8/3.0 ama piramitleme ile; 4H'de OOS Sharpe -0.43, DD -%68; elendi.
- `swing__ma-kesisim` (SMA 10/20, 13/50, 15/50 long, günlük, Mag7/BIST/kripto): IS PF 2-3.5, OOS 1.2-2.1, 2022 PF 0.3-0.5, OOS Sharpe 0.05-0.4 -> elendi (kripto beta).
- `macd-sinyal`, Awesome osc., `supertrend-psar`, Parabolic SAR günlük: OOS Sharpe ~0; 2022 PF<0.6. Freqtrade FSupertrend 1h PF 1.11/1.07, 2022 0.94: elendi.
- `rsi-asiri-donus` günlük RSI 30/70: PF 0.87/0.90. `bas-omuz` (RSI omuz-baş-omuz): PF 1.02/1.19 sınırda. `pin-bar` (Shooting Star): kod hatalıydı, 0 işlem.
- `scalp__bant-donus` / `scalp__rsi-asiri-donus` / scalp grubu: 40 freqtrade 1m/5m/15m/30m stratejisi (BinHV/Cluc = Bollinger+hacim, MultiRSI, Strategy001-005 = EMA/Heikin/Stokastik): hiçbiri PF>1.2; yüksek WR kandırıcı (%70-95 WR, PF 0.6-0.8). 1L3A scalp/5m için kritik uyarı: sabit küçük ROI hedefleri %0.14 gidiş-dönüş maliyetini karşılamıyor.
- `daytrade__orb`-benzeri: London Breakout (1h) PF 0.58/0.57, Dual Thrust PF 1.14/1.01. 1L3A zaten ORB'yi "doğrulanırsa ele" diye işaretledi - doğrulayıcı kanıt.
- `swing__goreceli-guc-momentum`: momentum rotasyonu top-N PF 2.4/1.5 ama top3/5/8'de OOS Sh 0.58/0.29/0.08, 2022 -1.39: kırılgan.
- Davey MA-stretch ve VE-kombinasyonu MR: IS iyi/OOS<1.
- Genel dersler: yüksek WR ≠ kâr; "geleceği gören" normalizasyon tuzağı; bar boyutu küçüldükçe kırılım sahtelenir; kripto'da uzun-MA filtresi 2024-26'da öngörü vermedi.
(d) metinler/ kitapları ve 1L3A örtüşmesi
- Listesi (20 dosya): Tsinaslanidis&Zapranis (kalıp tanıma), Leshik&Cralle, Kalara Koru, Davey (Kısayol Kodları), Van Der Post (Pro), Dolzhenko, Ratford, Kissell (Yöntemler), Jansen (ML), Altın Oran/Golden Inner Circle, Gizlyk (MQL5 NN), Halsey (Ölçülü Hareket), Price Action Algo Konsepti, Dagade (Python), Kılınçarslan (BIST tezi), Pruitt (Ultimate Algo System), D'errico (EasyLanguage), Selley, Aldridge (HFT), (ve ek PDF: repo kökünde aynı kitapların PDF'leri, .gitignore değil - repoda duruyor).
- 1L3A `veri/kart_dizini.csv` `kaynak_dosya`: 50 kaynak (Bulkowski, Graham, Scheier, Schroder, Landry, Hogan, Johnson, Simon Jordan, 51 Strateji, Heikin Ashi Trader, Volman, Boxer vb.). **Örtüşme: yok** (ikisinde de ortak kitap bulamadım; adlar tamamen farklı). Yani algo-sg kitapları 1L3A için tamamlayıcı: sistematik/test metodolojisi (Davey, Pruitt, Kılınçarslan, Jansen, Kissell) ve risk/çıkış modülleri için kaynak. Bu kitapların `metinler/*.md` düz metni 1L3A'ya kart çıkarma için ham veri olarak verilebilir (çıkarım ajanıyla; kitap metinleri veridir).
- Pruitt (Turtle/Donchian), Davey (çıkış testleri, MR yöntemleri), Halsey (ölçülü hareket) kartları 1L3A'nın çıkış/risk modülleri (13 modül) ve donchian-kirilim ailesine **yazar sayısı** katar (yaygınlık skoru artar).

## 9. Kırmızı bayraklar
1. **Seçim yanlılığı / OOS kirlenmesi**: ~3.600 ızgara satırı (results/*grid*.csv, hepsinde OOS sütunu) + "teşhis"ler OOS'a bakarak + denetimde kabul kuralı IS+OOS+stres. OOS gerçek anlamda "görülmemiş" değil; stres evreni de karar döngüsüne girdi. B'nin OOS PF'si (2.67) IS'ten (1.41) çok yüksek: raporun kendisi şans olabilir diyor (STRATEJILER.md §5.3), gerçekçi PF 1.4-1.8.
2. **Hayatta kalma/ evren**: ana evren bugünün büyükleri (APT/ARB/OP/SUI/INJ 2022-23'te listelenmiş); day-trade çapraz denetimi aynı hatayı OOS PF 1.74 -> 1.27 olarak ölçtü. Burada ölçülmedi. Stres evreni "delist" değil: MATIC, XMR, EOS, ICP vb. çoğu hâlâ var.
3. **Küçük bağımsız örneklem (B, D2)**: B ~50-60 bağımsız çöküş günü; 2023 PF 16.7 n=35; D2 143 işlem, PF 4.1 (kendileri "iyimser olabilir" diyor); ana evrende 21/24 coin kârlı ama aynı günlerde.
4. **Kuyruk bağımlılığı (A)**: ilk %5 işlem tüm kârın üstünde; 2026'da WR %39.6, 2025'te PF 1.17; trend yoksa yatay. Short bacağı OOS'ta rejime göre PF 0.90-1.12; A DD -%34 MTM (rapor "-%15" sayısı yalnız A+B kombinasyonu için).
5. **Rejim bağımlılığı**: B 2022 PF 0.95, D1 stres 2020 PF 0.08; boğa/2021 ve 2024 ağırlıklı kâr; day-trade benzeri sistemde 2022 PF 0.66.
6. **Kriz doldurma gerçekçiliği (B)**: -%15 sonrası saatlik açılıştan giriş; kayma sabit 2 bp. 2024-08-05, 2025-10-10 gibi günler kâr merkezi.
7. **Kağıt bot gerçek icra testi değil** + bot durmuş (son güncelleme 2026-10-16) + 19 işlemde PF 0.05 (A) küçük örneklem ama beklentiden çok kötü; dönem tamamlanmadığı için sonuç yok.
8. **Belge-kod / belge-belge çelişkileri**: (a) PROGRESS.md "Strateji A: SL=1x4H ATR, 480 bar, IS PF 1.39-1.48" vs final.py `sl_h4atr=2.0, max_bars=720` ve STRATEJILER.md (PROGRESS bayat, ara sürüm). (b) STRATEJILER.md ana evren A MTM DD -%34.2 ve kombinasyon -%15.2; A v2 belgesinde -%31.2/-%14.7 (hesap yöntemi farkı). (c) paper/README "2 saatte bir :43, ~360 dk/ay" vs kagit.yml saatte iki cron. (d) backtest.py:14 yorum "0.05% taker + 0.02% kayma" ama STRATEJILER.md "komisyon+kayma %0.07" - tutarlı; Binance VIP0 taker 0.05% olduğundan makul, ama maker/BNB indirimi hesaba katılmamış. (e) PROGRESS.md sonu "DURUM: TAMAMLANDI" fakat kağıt bot bitmedi.
9. **Rapor Sharpe yöntemi**: "rapor yöntemi" (yüzde ortalaması) 1.45 vs basit 50/50 1.25; kaldıraçta yanıltıcı (docs/A_V2_VE_KALDIRAC.md giriş).
10. **Çoklu zaman dilimi modülü kısmi çakışma**: A ve B aynı anda sistemik çöküşte (B long alırken A short) -0.27 korelasyon iyi görünüyor; ancak Mart 2020 tipi olaylarda B'nin 25 eş zamanlı long'u (her biri %0.75) yüksek risk.

## Lider için özet
1. algo-sg: Binance USDT-M 25 coin, 1h veri (2020-2026), IS 2020-23 / OOS 2024+, stres evreni 20 coin; maliyet %0.07/taraf + gerçek funding.
2. Motor temiz: sinyal kapanış-giriş açılış, stop-önce, gap, 8 birim test; göstergelerde lookahead bulmadım. Kayma sabit 2 bp (kriz girişlerinde iyimser).
3. Tek canlı aday: A (4H/1D Donchian kırılımı + hacim + EMA/BTC filtresi, long+short) ALL PF 1.61, OOS 1.545, WR %50, MTM DD -%34; kâr ilk %5 işlemde yoğun.
4. B (24s -%15 kapitülasyon long) PF 1.78 / OOS 2.67 ama ~50-60 bağımsız olay, kriz doldurma varsayımı iyimser; D1/D2 daha zayıf.
5. OOS kirli: ~3.600 ızgara satırında OOS görünür, denetim kabulü IS+OOS+stres; evren bugünün büyükleri (PIT testi yok).
6. Kağıt bot (10 Ekim başlangıç): son güncelleme 16 Ekim, A 19 işlemde PF 0.05, toplam -%4.1; durma nedeni doğrulanamadı (en olası: Actions kotası, yml saatte 2 çalıştırma, README yanlış).
7. dis_kaynak: ~180 dış kural/freqtrade stratejisi test edildi, hiçbiri geçmedi (yüksek WR scalper'lar PF<1; lookahead'li olanlar düzeltilince çöktü) -> 1L3A scalp için güçlü negatif bilgi.
8. Almaya değer: test senaryoları, üst-ZD hizalama mantığı, portföy simülatörü, DSR/PIT/gecikme denetim listesi; A ve B'yi 1L3A donchian-kirilim ve dip-sonrası-donus ailelerinde aday olarak yeniden test et.
9. Kitaplar: 20 sistematik kitap, 1L3A'nın 50 kaynağıyla örtüşme yok -> tamamlayıcı (Davey/Pruitt/Halsey çıkış-risk modülleri için).
10. Belge çelişkileri: PROGRESS.md bayat (SL 1x/480 bar vs kod 2x/720), paper/README vs workflow cron.
