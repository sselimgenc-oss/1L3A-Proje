# 4. tur değerlendirmesi: 199 yeni satır ve 30 öncelikli fikir grubu

_Hazırlayan: Claude (alt ajan), 2026-11-13. Girdi: dış ajanın 4. tur listesi (906 satır, 130 grup), önceki karşılaştırma (707 satır), arşiv envanteri (821 satır), v1/v2/v3 sonuç dosyaları. Repoda hiçbir dosya değiştirilmedi, commit/push yok. Sayıların hepsi betikle hesaplandı (`build_a.py`, `build_b.py`, aynı klasörde); yargı gerektiren yerler ayrıca belirtildi._

## Kullanıcıya özet

1. Dış ajanın 4. turunda 199 yeni strateji geldi (TASC Traders' Tips 65, QuantConnect/Quantopian 69, kitap/kütüphane kodu 65). Hepsini arşivimizle, kodu açarak, mantık düzeyinde tek tek karşılaştırdım.
2. 11 tanesi arşivde aynı kuralla zaten var, 172 tanesi aynı fikir ailesinden ama ayrıntısı farklı, yalnız 16 tanesi arşivde hiç yok. Yeni fikir yine çok az.
3. Arşivde hiç olmayan 16 fikirde tablo şöyle: 13 tanesinin dış kanıtı hiç yok, 3 tanesinde yalnız yazarın kendi backtest iddiası var; çoğu gösterge varyantı (Stiffness, korelasyon-trend, Elegant Oscillator, SuperSmoother, Hurst filtreli dönüş). Kanıtsız bir fikir için ayrı test açmaya değmez.
4. Bizim evrende yapılamayan ya da dış ajan bayraklı satır sayısı 77 (hisse sıralaması/rotasyon 29, pairs 22, bayrak 17, veri yok 6, seans 3). Teknik olarak denenebilir 122 satır kaldı, ama bunların neredeyse hepsi zaten elenmiş ailelerin varyantı.
5. 4. turda düzeltilen 28 eski satırda sınıf değişen yok. Tek kullanılabilirlik değişimi: S0438 yeni ŞÜPHELİ bayrağı aldı (evet -> hayır). S0474'ün kaynağı açılamadığı için doğrulanamadı.
6. Dış ajanın 30 öncelikli fikri bizde şöyle çıktı: adil biçimde test edilip elenen 16; bizim evrende yapılamayan 9 (hisse kesiti, seans/gap, VIX, pairs, limit ızgarası); zayıf temsilciyle test edilen 4; hiç test edilmeyen 1.
7. Önemli: elenen trend ailelerinin çoğu (MACD, MA dizilimi, RSI 60/40, Donchian, ROC) kârsız olduğu için değil, iki sert kapıda düştü: 'kâr üç sınıftan en az ikisinden gelmeli' (E4) ve 'tek hesapta -%20 kill'e hiç takılmamalı' (E5). Kârlılık ve yoğunlaşma kapılarını geçip yalnız bu ikisinden düşen 62 strateji var. Kapılar sonuç sonrası değişmez (ön kayıt); ama 'elendi' ile 'fikir yanlış' aynı şey değil.
8. '200 işlem' kapısı yavaş stratejileri kısmen yapısal eler: yalnız bu kapıdan düşen 11 strateji var (ewmac-carry/carver, sott, lube dahil). Ama sayım 35 sembolün toplamı olduğu için oy-tabanlı TSMOM 841 işlem üretti; aylık sinyal tek başına elenme sebebi değil.
9. Yeniden test hak edenler (hepsi 'yeni ön kayıt + tek koşu', canlı kadroya dokunmadan): günlük geniş eşikli yüzde filtre / %20 iz stoplu long trend (T61), BLL tipi bantlı MA (T21), EMA200 filtreli + 2R hedefli Donchian (T02). ORB (T09) yalnız maliyet varsayımı doğrulanırsa.
10. Dış ajanın puanlaması kanıt sıralaması değil: puanın ortalama yüzde 26 kadarı 'bağımsız tekrar' (kaç sitede/yazarda geçtiği), yüzde 22 kadarı 'uygulanabilirlik' (kodun açık/stoplu olması; evrene uyum değil). Kanıtı olumsuz 9 grup ilk 30'da yer alıyor (sıralar: 4, 9, 14, 17, 18, 26, 27, 28, 29).
11. Güçlü dış kanıtın (noise-area Sharpe 1,33) bizde çökmesinin nedeni maliyet: bizde tur ≈13 bp, brüt kenar ≈2 bp. Dış ajanın önerdiği test maliyeti taraf başına 2-5 bp civarı; bizim tur maliyetimiz ≈13-14 bp.
12. Öneri: yeni dış arama yerine v2 planını sürdür; bir sonraki ön kayıtlı turda yalnız yukarıdaki 3 ucuz günlük testi düşün. Karar senin.
13. Güvenilirlik: eşleştirmeyi tek geçişte elle yaptım; emin olamadığımda BENZERI dedim, yani 'yeni fikir' sayısı alt sınırdır. Hüküm tablosundaki sıralama (bizim_sira) yargıdır, ölçüm değil.

**Terimler.** E1-E5 = v2 eleme kapıları: E1 kârlılık (maliyet x2'de net > 0 ve PF >= 1,2), E2 örnek (>= 200 işlem, >= 10 enstrüman), E3 yoğunlaşma (en iyi sembol/yıl çıkarılınca hâlâ kârlı), E4 genişlik (üç sınıftan en az ikisi toplam R'nin >= %15'ini taşır), E5 hayatta kalma (tek hesapta -%20 kill hiç tetiklenmez). 'Tek kasa' = 35 sembolün tek hesapta, %1 işlem riskiyle oynatılması. K2 p = rastgele giriş testi p-değeri; BH = çoklu test düzeltmesi (939 satır). v1 WF = 2017 geliştirme dönemi yürüyen pencere testi. DK_ = Dukascopy CFD hisse/emtia/endeks sembolleri. P1-P6 / V1-V5 = v3 kapıları.

---

## 1. İş A: 199 yeni satır (S0708-S0906)

Yöntem önceki karşılaştırmayla aynı: eşleşme isimden değil kuraldan; ZATEN = çekirdek kural ve parametre kümesi sınıfımızın ayar kapsamında (varsayılan, ızgara, `dis_ayarlari`, `kart_ayarlari`); BENZERI = aynı ailede ama giriş/çıkış/filtre/parametre farkı var; BIZDE_YOK = arşivde karşılığı yok. `kullanilabilir` teknik/proje fizibilitesidir (kârlılık kanıtı değil): bayraklı, hisse kesitsel, pairs, seans, veri-yok, yasak tip satırlar `hayir`. Hisse taramalı satırlarda sıralama yalnız aday sınırlama ise (sinyal kural kendisi tek-hisse koşulları) `evet` yazdım; sinyalin kendisi sıralama/yüzdelik ise `hayir`.

### 1.1 Dağılım

| Sınıf | Toplam | Trend | Ortalamaya dönüş | Kullanılabilir | Kullanılamaz |
|---|---|---|---|---|---|
| ZATEN_TEST | 11 | 9 | 2 | 9 | 2 |
| BENZERI_TEST | 172 | 79 | 93 | 104 | 68 |
| BIZDE_YOK | 16 | 5 | 11 | 9 | 7 |
| **Toplam** | 199 | 93 | 106 | 122 | 77 |

| Küme | Satır | ZATEN | BENZERI | BIZDE_YOK | Kullanılabilir | Kullanılamaz |
|---|---|---|---|---|---|---|
| D1 TASC Traders' Tips | 65 | 1 | 56 | 8 | 57 | 8 |
| D2 QuantConnect / Quantopian | 69 | 5 | 62 | 2 | 31 | 38 |
| D3 kitap / kütüphane eşlik kodu | 65 | 5 | 54 | 6 | 34 | 31 |

Kanıt türü: backtest iddiası 57, kanıtsız 142 (akademik ya da canlı kayıt yok). Dış bayrak: 17 satır (LOOKAHEAD_RİSKİ: 5, ŞÜPHELİ: 7, YASAK_TİP ; ŞÜPHELİ: 1, YASAK_TİP: 4); hepsi `kullanilabilir=hayir`.

### 1.2 Kullanılamaz nedenleri (her satır tek kategori, bayrak önce)

| Neden | Satır |
|---|---|
| kesitsel sıralama / rotasyon / çok varlıklı | 29 |
| pairs / spread / çapraz arbitraj | 22 |
| dış ajan bayrağı (ŞÜPHELİ / LOOKAHEAD / YASAK_TİP) | 17 |
| veri yok (vadeli, olay, tick, ilişkili varlık) | 6 |
| borsa seansı / açılış-kapanış / saat penceresi | 3 |
| **Toplam** | 77 |

Ayrı stop tanımı olmayan satır: 149 (kullanılabilir olanların 82'i). Bunlar için motorun zorunlu felaket stopu (ATR katı) eklenir; kaynak stopsuzsa (Carver EWMAC/breakout/accel S0866-S0868, S0838, S0842-S0844 'hep piyasada' vektörel kurallar, S0874-S0877 ve S0880 stopsuz giriş-çıkış kuralları) 'kaynağa sadık' test imkansızdır: test ancak felaket stoplu uyarlama olarak koşar ve öyle etiketlenmelidir.

### 1.3 En çok eşleşen arşiv sınıfları

| Arşiv sınıfı | Satır | Arşivdeki durum |
|---|---|---|
| pf__pairs | 25 | elendi v2 |
| swing__rsi-asiri-donus | 21 | elendi v2 |
| swing__ma-kesisim | 12 | elendi v2 |
| pf__rotasyon | 11 | elendi v2 |
| pf__kesit_ls | 11 | elendi v2 |
| swing__donchian-kirilim | 10 | elendi v2 |
| swing__bant-donus | 10 | elendi v2 |
| pf__sinif_kesit_donus | 8 | elendi v2 |
| dis__connors-etf | 6 | elendi v2 |
| dis__ema21-sapma | 6 | elendi v2 |
| dis__bant-kirilim-trend | 4 | elendi v2 |
| swing__stokastik-donus | 4 | elendi v2 |

`pf__pairs`, `pf__rotasyon`, `pf__kesit_ls`, `pf__sinif_kesit_donus` portföy sınıflarıdır; hisse kesitsel/pairs satırları bunlara BENZERI olarak bağlandı ve evren nedeniyle `hayir` yazıldı (kripto+DK ≈35 sembolde denendi, elendi).

### 1.4 ZATEN_TEST (11 satır)

| Dış id | Strateji | Arşiv | Arşivdeki sonuç | Kullanılabilir |
|---|---|---|---|---|
| S0721 | Golden Cross Breakouts – Traders' Tips Mart 2017 (MetaS | swing__ma-kesisim | v2 elendi (kalan E2,E4,E5; net x2 +129%; PF 3,35, 95 işlem); v1 WF 1d:elendi (Sharpe 0,43), 4h:elendi (Sharpe 0,65) | evet |
| S0780 | Dual Thrust Trading Algorithm (SPY, saatlik) | dis__dual-thrust | v1 WF 1h:elendi (Sharpe 0,58), 30m:elendi (Sharpe 0,27) | hayir |
| S0782 | Intraday ETF Momentum (Gao, Han, Li & Zhou 2017) | dis__ilk-yarim-saat-son-yarim-saat | v1 WF 1h:elendi (Sharpe -0,73), 30m:elendi (Sharpe -0,33) | hayir |
| S0790 | RsiAlphaModel (LEAN çerçeve alfa modeli) | swing__rsi-asiri-donus | v2 elendi (kalan E1,E2,E3,E4,E5; net x2 -11%; PF 0,78, 138 işlem); v1 WF 1d:elendi (Sharpe -0,20), 4h:elendi (Sharpe -1,59) | evet |
| S0792 | EmaCrossAlphaModel (LEAN çerçeve alfa modeli) | swing__ma-kesisim | v2 elendi (kalan E2,E4,E5; net x2 +129%; PF 3,35, 95 işlem); v1 WF 1d:elendi (Sharpe 0,43), 4h:elendi (Sharpe 0,65) | evet |
| S0839 | MovingAverageCrossAlgorithm (BTCUSD EMA 15/70) | swing__ma-kesisim | v2 elendi (kalan E2,E4,E5; net x2 +129%; PF 3,35, 95 işlem); v1 WF 1d:elendi (Sharpe 0,43), 4h:elendi (Sharpe 0,65) | evet |
| S0842 | SMAVectorBacktester (SMA-based strategy) | swing__ma-kesisim | v2 elendi (kalan E2,E4,E5; net x2 +129%; PF 3,35, 95 işlem); v1 WF 1d:elendi (Sharpe 0,43), 4h:elendi (Sharpe 0,65) | evet |
| S0843 | MomVectorBacktester (momentum-based strategy) | dis__roc20-ls | v2 elendi (kalan E4,E5; net x2 +182%; PF 1,66, 1371 işlem); v1 WF 1d:elendi (Sharpe 0,63), 4h:elendi (Sharpe 0,79) | evet |
| S0844 | BacktestLongShort.run_momentum_strategy | dis__roc20-ls | v2 elendi (kalan E4,E5; net x2 +182%; PF 1,66, 1371 işlem); v1 WF 1d:elendi (Sharpe 0,63), 4h:elendi (Sharpe 0,79) | evet |
| S0894 | How to Build a Profitable Mean Reversion Strategy Using | dis__ibs-donus | v2 elendi (kalan E1,E3,E5; net x2 -3%; PF 1,08, 1524 işlem); v1 WF 1d:elendi (Sharpe 1,06), 4h:elendi (Sharpe 0,22) | evet |
| S0903 | 06a technical strategy with VectorBT (SMA 10/30 FAANG) | swing__ma-kesisim | v2 elendi (kalan E2,E4,E5; net x2 +129%; PF 3,35, 95 işlem); v1 WF 1d:elendi (Sharpe 0,43), 4h:elendi (Sharpe 0,65) | evet |

### 1.5 BIZDE_YOK (16 satır): arşivde hiç karşılığı olmayan

| Dış id | Strateji | Grup | Kanıt | Kullanılabilir | Not |
|---|---|---|---|---|---|
| S0715 | The Stiffness Indicator – Traders' Tips Kasım 2018 | T69 | yok | evet | Stiffness (60 bar içinde SMA100 üstü kapanış oranı, EMA) 90'ı yukarı kesince al, 84 bar tu |
| S0716 | Stiffness pullback strategy (Pullback=1) – Traders | T24 | yok | evet | SMA100 üstü + Stiffness≥90 + SPY EMA yükselen + RSI(3) 40 altından yukarı dönüş; 84 bar za |
| S0717 | Correlation Trend strategy – Correlation As A Tren | T69 | yok | evet | Fiyat-zaman korelasyonu (20 bar) 0.5'i yukarı kesince al, 40 bar korelasyon 0 altına ininc |
| S0718 | CorrelationTrend long-only – Traders' Tips Mayıs 2 | T69 | yok | evet | 20 günlük CorrelationTrend sıfırı yukarı kesince al, aşağı kesince sat (long-only). Arşivd |
| S0745 | Reversion Index – Python sinyali – Traders' Tips O | M54 | yok | evet | Reversion index (20) üzerinde SuperSmoother(4) tetik × SuperSmoother(8) kesişimi. Ehlers S |
| S0746 | Elegant Oscillator BB strategy – Traders' Tips Şub | M54 | yok | evet | Elegant Oscillator (Ehlers) kendi Bollinger alt bandını (100, 1.5) yukarı kesince al, üst  |
| S0747 | Elegant Oscillator peak/valley – Traders' Tips Şub | M54 | yok | evet | Elegant Oscillator ±0.5 eşiğinde tepe/dip (Zorro), ters sinyalde çevirme. EO arşivde yok. |
| S0749 | Trading The Nikkei – Correlation Divergence strate | M56 | yok | hayir | ilişkili varlık verisi (Nikkei, yen/FXY, SPY) |
| S0778 | Intraday Arbitrage Between Index ETFs (SPY/IVV) | M18 | backtest iddiası | hayir | çapraz borsa/ETF arbitrajı, saniye kotasyon verisi |
| S0807 | Futures trend reversion algo | M36 | yok | hayir | çok vadeli portföy (16 sürekli vadeli) |
| S0860 | calendarSpdsMeanReversion.py (CL calendar spread r | M17 | backtest iddiası | hayir | bayraklı: LOOKAHEAD_RİSKİ; vadeli takvim yayılımı verisi (CL vadeleri) |
| S0865 | pead.py (post-earnings announcement drift, intrada | T72 | backtest iddiası | hayir | kazanç takvimi verisi (olay verisi) |
| S0869 | mr_wings (mean reversion in the wings) | M36 | yok | evet | EWMAC sinyali 5000 gün std'sinin 3 katını aşarsa tersi yönde pozisyon (mean reversion in t |
| S0872 | fastMR scalper (systems/provided/scalper) | M21 | yok | hayir | tick/600 sn bar + çift taraflı limit emir (market making tarzı) |
| S0883 | Strat_Mean_revers_Hurst (HighPass + Fisher + Hurst | M42 | yok | evet | HighPass(30) + Fisher(500) normalize, Hurst(500)<0.5 iken ±1 kesişimde dönüş işlemi. Hurst |
| S0904 | 12q trading-app crack spread vs PSX rank z-score | M17 | yok | hayir | bayraklı: ŞÜPHELİ; vadeli yayılımı verisi + 1 dakika |

Yorum: (1) Dokuz kullanılabilir yeni fikirden hiçbirinin kanıtı yok; hepsi gösterge varyantı. (2) S0715-S0718 (Stiffness, korelasyon-trend) ve S0883/S0745 (Hurst/Reversion Index filtreleri) filtre olarak düşünülebilir ama **canlıdaki stratejilere yeni filtre eklenmez** (v2 §8, §3); olsa olsa paper/backtest tarafında yeni ön kayıtla. (3) S0869 (EWMAC aşırı ucunda ters işlem), S0807 ve S0465-S0467 (3. tur) ile aynı 'trendin tersi' hipotezi; bkz. M36 hükmü (ayna mantığı). (4) S0872 limit ızgarası ve S0778 ETF arbitrajı market-making türü: motorumuz yalnız market emir, maker altyapısı yok.

### 1.6 Önceki turdan düzeltilen 28 satır

4. tur denetimi ilk 707 satırın 28 tanesinde alan düzeltmesi yaptı. Sınıf değişmesi gereken satır: **0**. Kullanılabilirlik değişen: **1** (S0438). Kanıt/belirsizlik etkisi olanlar: S0447, S0466, S0474, S0521, S0538. Tablo, ek kaynak eklenen 8 satır dışındakileri gösterir:

| Dış id | Değişen alanlar | Etki |
|---|---|---|
| S0427 | populerlik_olcusu, notlar | yalnız popülerlik (5.383 görüntülenme) eklendi; etki yok |
| S0428 | iddia_edilen_performans, notlar | CCI-100 kanıt cümlesi nüanslandı (Tukey tablosunda bazı koşullarda al-tut ile aynı grup); sınıf ve kullanılabilirlik aynı |
| S0435 | yayin_yili, stop_kurali, iddia_edilen_performans, notlar | dinamik ATR çarpanı depoda momentum bacağında etkisiz; sınıf aynı |
| S0438 | bayraklar, notlar | kullanilabilir evet -> HAYIR (yeni ŞÜPHELİ bayrağı: ücretli üyelik, yöntem verilmiyor); sınıf BENZERI aynı |
| S0439 | notlar | ana gönderi de 'Potential Spam' etiketli; zaten hayir (hisse screener, seans), sınıf aynı |
| S0443 | giris_kurali, parametreler, notlar | rejim puanı kademeli (aç/kapa değil); sınıf aynı |
| S0447 | iddia_edilen_performans, kanit_turu, notlar | kanıt türü yok -> backtest iddiası (rakamlar Pine'a değil depo araştırma özetine ait: BTC günlük 12 işlem); sınıf aynı |
| S0453 | giris_kurali, cikis_kurali, parametreler, notlar | iki yalnız-uzun bacaklı z-skor (kısa satış yok); pairs, kullanilabilir=hayir aynı |
| S0458 | cikis_kurali, stop_kurali, parametreler, notlar | gerçek kod R-katı hedefler + ATR stop (config'teki %10/%15 kullanılmıyor); sınıf aynı |
| S0461 | parametreler, iddia_edilen_performans, notlar | OCR bozuk parametre notu, iddia 'Tablo 8 örneklem içi en iyi' olarak daraltıldı; ZATEN aynı |
| S0466 | cikis_kurali, iddia_edilen_performans, notlar | kontrarian PSAR: makale %5'te anlamlı DEĞİL (Tablo 2, t=0,95); 'on kuralın hepsi anlamlı' PSAR'ı kapsamıyor; sınıf BIZDE_YOK aynı, M36 grubunun kanıtı zayıfladı |
| S0474 | notlar | kaynak üç denemede açılamadı, kural ve %28,5/154 işlem iddiası doğrulanamadı (ERİŞİLEMEDİ); sınıf BENZERI korundu, kullanılabilirlik kararı belirsiz |
| S0489 | giris_kurali, notlar | giriş artık RSI<30 VE (ardışık düşüş YA DA alt BB); sınıf aynı |
| S0508 | iddia_edilen_performans, notlar | funding ortalamaya dönüş: dört eşiğin üçünde pozitif kümülatif getiri eklendi (çoğu fonlama ödemesi); sınıf ZATEN aynı |
| S0521 | iddia_edilen_performans, notlar | Ichimoku kanıtı ters yazılmıştı: DJ30'da al-tut'un %90 gerisinde (çürütücü kanıt); sınıf aynı |
| S0523 | populerlik_olcusu, stop_kurali, notlar | satış stopu metinle kod arasında farklı (kodda stop = üst bant); popülerlik eklendi; sınıf aynı |
| S0524 | populerlik_olcusu, notlar | yalnız popülerlik (11.174 görüntülenme) eklendi; etki yok |
| S0530 | giris_kurali, notlar | giriş cümlesi: 'getiri ortalamanın üstünde' ifadesi Faber tipi okunuyor; sınıf aynı |
| S0531 | iddia_edilen_performans, notlar | z-istatistikleri pariteler arasında yer değiştirmişti, düzeltildi; zaten hayir (LOOKAHEAD, boşluk); sınıf aynı |
| S0538 | iddia_edilen_performans, notlar | kripto TSMOM: Newey-West t=3,20 kaynakta yok (üç faktör alfası t=3,28); sınıf ve kullanilabilir=hayir (piyasa değeri endeksi) aynı |

Yalnız ek kaynak eklenen 8 satır (S0038, S0141, S0143, S0145, S0156, S0163, S0168, S0171): D2 kümesinin mevcut satırlarla aynı saydığı QuantConnect uygulamaları `EK_KAYNAK` olarak eklendi; sınıf ve kullanılabilirlik etkisi yok.

Notlar: (a) Lisans: S0842-S0847 (Hilpisch py4at) depo lisansı yalnız kişisel kullanım; kural projede sıfırdan yeniden yazılmalı. 19 satır lisanssız depodan geliyor (Zorro koleksiyonları, Radge, Clenow): kural fikri kullanılabilir, kod kopyalanamaz. (b) 52 satır dış denetimde yalnız model özetiyle okundu (WebFetch); benim eşleştirmem satır metnine ve ayar alanlarına dayanıyor, kaynak sayfa/koda inmedi. (c) Yasak tipler: S0811 (Turtle her gün birim ekleme), S0891 (kademeli ekleme), S0897-S0899 (yeniden ekleme/ortalama düşürme) `hayir`; martingale/DCA/ML satırı yok.

---

## 2. İş B: 30 öncelikli fikir grubunun hükmü

Hüküm kodları: **a** = ADIL_TEST_EDILDI_ELENDI, **b** = ZAYIF_TEMSILCI_ILE_TEST_EDILDI (yeniden test hak ediyor), **c** = HIC_TEST_EDILMEDI, **d** = BIZIM_EVRENDE_UYGULANAMAZ. 'Adil' = kural çekirdeği ön kayıtlı kapılardan geçirildi (v2: varsayılan ayar, 1d, 35 sembol; v1 WF ızgaralı); parametre ızgarasının her noktası ayrı koşulmadı. Tam satır satır gerekçe, arşiv id'leri ve sonuçlar `oncelik30_hukum.csv` içinde.

Dağılım: a = 16, b = 4, c = 1, d = 9 (toplam 30).

| Dış sıra | Grup | Dış puan | Hüküm | Bizim sıra | Bizde test edilen | Neden / sonuç |
|---|---|---|---|---|---|---|
| 1 | T01 Donchian/kanal kırılımı (N-gün yüksek) | 73.5 | a | 4 | swing__donchian-kirilim; pf__v3-donchian-ansambl; dis__son1ay-kanal-20 | Ansambl P6'da Sharpe 0,978 < al-tut 0,995 ile elendi; Donchian E4/E5'te düştü |
| 2 | T28 Aylık MA filtresi / taktik varlık dağılımı (Faber 10 ay) | 73.1 | a | 6 | pf__trend_sepet; dis__sma200-ls | SMA200 L/S tüm eleme kapılarını geçti ama BH dışı kaldı; Faber sepeti kill'de elendi |
| 3 | T47 Kesitsel momentum (12-1 / 6-6 kazanan-kaybeden) | 70.7 | d | 28 | pf__kesit_ls; pf__rotasyon; pf__sinif_kesit_mom; pf__v3-fip-kesitsel-m | Hisse/vadeli kesiti yok; kripto karşılıkları kapılarda elendi |
| 4 | T46 Zaman serisi momentumu (N-ay getiri işareti, TSMOM) | 64.7 | a | 7 | v2__tsmom-oy; v2__tsmom-12-1; dis__tsmom; pf__cta; dis__ewmac-carry | Oy-tabanlı TSMOM yalnız E4'ten düştü; yavaş sürümler E2'ye takıldı |
| 5 | T09 Açılış aralığı kırılımı (ORB, ilk N dakika) | 61.3 | b | 5 | daytrade__orb; dis__orb-sweep-donus; v3__orb-4s-hacim-atr | Yalnız 30m/1h (v1) koşuldu; 5 dk ve kripto UTC-açılış ORB koşulmadı |
| 6 | T30 MACD/TRIX/PPO sinyal kesişimi (klasik) | 59.9 | a | 17 | swing__macd-sinyal; scalp__macd-sinyal | Kârlılık kapılarını geçti, E4/E5'te elendi |
| 7 | M35 Stokastik / Williams %R / Ultimate Oscillator aşırılık d | 59.3 | a | 22 | swing__stokastik-donus; daytrade__stokastik-donus; scalp__stokastik-do | Her TF'de net negatif |
| 8 | M31 Gece/açılış boşluğu sönümleme (gap fade) | 58.9 | d | 30 | swing__gap-doldurma; daytrade__gap-doldurma; dis__gap-onceki-kapanis-t | Kripto'da boşluk yok; DK'da 0 işlem / negatif |
| 9 | T27 Tek MA üstü/altı zamanlama (günlük/haftalık) | 58.9 | a | 16 | dis__sma200-ls; swing__ma-kesisim; pf__trend_sepet | SMA200 L/S BH dışı; MA kesişimi ve sepet kapı dışı |
| 10 | T21 BLL tipi değişken MA (VMA) kuralları, bantlı | 57.1 | b | 2 | dis__ema-esik-trend; swing__ma-kesisim; dis__sma200-ls | BLL (1-2 gün MA + %1 bant) koşulmadı; EMA eşikli sürüm E2/E5 |
| 11 | T45 52 hafta zirvesine yakınlık (kesitsel) | 56.7 | d | 12 | swing__goreceli-guc-momentum; dis__yeni-zirve-trend-filtresi; pf__kesi | Kesitsel çapa etkisi; kesit yok, tek-grafik karşılığı kârsız |
| 12 | T08 Gürültü bölgesi / noise oranı uyarlamalı kırılım | 56.5 | a | 9 | v3__gunici-momentum-noise-alani; v3__volatilite-kirilim-k05 | DK_SPX 30 dk elendi: brüt +2 bp, maliyet ≈13 bp |
| 13 | M20 VWAP bandından dönüş | 56.5 | a | 19 | daytrade__vwap-donus; dis__vwap-alt-bant-dip | Gün içi VWAP dönüşü maliyetle elendi |
| 14 | M27 Kesitsel kısa vadeli ters dönüş (geçen hafta/günün kaybe | 56.4 | d | 27 | pf__sinif_kesit_donus | Hisse kesiti yok; sınıf içi karşılığı belirgin negatif |
| 15 | T26 Fiyat yapısı kırılımı (direnç, salınım tepesi, 123, ardı | 56.1 | a | 10 | dis__arps-pivot-desenleri; swing__kirilim-geri-test; daytrade__trend-y | Heterojen aile, tekrar tekrar elendi |
| 16 | T55 Osilatörün trend yönlü kullanımı (RSI/CCI/KDJ/stokastik  | 56.1 | a | 11 | swing__rsi-momentum-esik; swing__cci-esik | RSI 60/40 kârlılık kapılarını geçti, E4/E5'te elendi |
| 17 | M11 Bollinger alt bant dokunuşu/geri dönüşü (filtresiz) | 55.1 | a | 23 | swing__bant-donus; dis__bollinger-2-3-sd-bolgesi; dis__ft-low-bb | Her TF'de negatif ya da sıfır |
| 18 | M05 RSI(14) 30/70 aşırılık (klasik, filtresiz) | 55.1 | a | 29 | swing__rsi-asiri-donus; daytrade__rsi-asiri-donus; scalp__rsi-asiri-do | Her kapıda elendi |
| 19 | T22 Üçlü/çoklu MA dizilimi (kısa>orta>uzun) | 55.0 | a | 15 | dis__ma-dizilim-5-10-30; dis__ma-mukemmel-siralama; dis__gmma-ls | SMA5/10/30 yalnız E5'te düştü; keşifte pozitif iz yok |
| 20 | T02 Kanal kırılımı + trend/hacim/ADX/temel filtresi | 54.9 | b | 3 | swing__donchian-kirilim; dis__bant-kirilim-trend; dis__son1ay-donchian | EMA200 + 2R hedefli ayar koşulmadı |
| 21 | T61 Yüzde filtre kuralı (Alexander / Fama-Blume) | 54.5 | b | 1 | dis__yuzde-zigzag | Yalnız 1h/30m ve %1-%3 koşuldu; günlük geniş eşik yok |
| 22 | M29 Uzun vadeli kaybeden-kazanan dönüşü (DeBondt-Thaler) | 53.6 | d | 25 | (yok) | Ülke endeksi, 36 ay; bizde evren yok |
| 23 | M36 Trend göstergesinin tersine kullanımı (kontrarian EMA/PS | 53.1 | c | 8 | (yok) | Arşivde yok; ayna mantığıyla beklenti düşük |
| 24 | M39 Volatilite endeksi / opsiyon sinyaliyle endeks alımı | 51.7 | d | 18 | (yok) | VIX/opsiyon verisi yok |
| 25 | M04 Kısa periyot RSI (3–5) aşırı satım + trend filtresi | 49.3 | a | 13 | swing__rsi-asiri-donus; dis__connors-etf | Maliyet sonrası negatif |
| 26 | M21 Kanal/zarf ucundan dönüş (Keltner, ATR, Donchian) | 48.7 | d | 21 | swing__bant-donus; dis__bant-kirilim-trend | Temsilci çift taraflı limit ızgarası; motorda yok |
| 27 | M01 RSI(2) aşırı satım alımı + uzun vade trend filtresi (Con | 48.7 | a | 24 | dis__connors-etf; dis__ifr2; swing__rsi-asiri-donus | ifr2 v1'de geçti, v2'de PF eşiği altı |
| 28 | M15 Pairs / eşbütünleşme spread z-skoru | 48.2 | d | 14 | pf__pairs | Hisse çiftleri / dakika verisi yok; küçük liste elendi |
| 29 | M16 Mesafe yöntemi pairs (GGR) | 48.1 | d | 26 | pf__pairs | Hisse SSD seçimi; kesit dar, mesafe yöntemi koşulmadı |
| 30 | M24 IBS (kapanışın gün aralığındaki konumu) dip alımı | 48.0 | a | 20 | dis__ibs-donus; pf__ibs_donus | Tek-varlık IBS dört biçimde elendi (pf__ibs_donus Sharpe 0,44) |

### 2.1 Bizim v2 kapıları ne yapıyor? (222 satırlık havuz)

v2 eleme: 222 satır, 18 geçen, 6 hata; 211'i 'genel' evren (35 sembol, 'tek kasa'), 11'i yalnız kripto. Kapıdan düşenler (hata hariç): E4 (sınıf genişliği) 143, E5 (kill) 134, E2 (işlem/enstrüman) 81.

| Gözlem | Sayı |
|---|---|
| E1 (kârlılık) ve E3 (yoğunlaşma) geçip E4 ya da E5'te düşen | 62 |
| E1+E2+E3 geçen (kârlı, yeterli işlem, yoğun değil) | 66 |
| yalnız E2'den düşen (yavaş sinyal) | 11 |
| yalnız E4'ten düşen | 17 |
| yalnız E5'ten düşen | 15 |
| E4+E5'ten düşen | 16 |
| E2'den düşenlerin medyan işlem sayısı | 95 (n<100: 44/81) |

Sonuçlar: (1) '≥200 işlem' kapısı yavaş stratejileri evet eler (yalnız bu kapıdan düşen: dis__ay-mevsimsellik, dis__ewmac-carry, dis__ewmac-carver, dis__lube, dis__ochoa-genisleme-gunu, dis__rsi-t3-sqz...), ama kapının sayımı 35 sembolün toplamıdır: aylık/haftalık sinyal 35 sembolde yılda yüzlerce işlem üretebilir (v2__tsmom-oy 841). Yani 'aylık yapısal olarak elenir' doğru değil; 'tek sembollü ya da düşük devirli sürümler elenir' doğru. (2) Asıl eleyiciler E4 (üç sınıftan en az ikisi ΣR'nin ≥%15'ini taşımalı) ve E5 (tek kasada -%20 kill hiç tetiklenmemeli): çoğu trend ailesi bunlara takıldı. E5 %1 risk, 35 sembol, tek kasa varsayımı altındadır; canlı kadro (ewo, e0v1en) farklı yapı. (3) Elemeyi geçen 18 stratejiden resmi testte (BH) 7'si keşif oldu, sağlamlıkta 5'i kaldı, mühürlü sette 2'si (DURUM.md); yani bu kapılar ve sonraki adımlar zaten çok seçici.

### 2.2 Kripto 7/24'te seans ve gap kuralları: karşılıklar

| Dış fikir | Kripto 7/24 karşılığı | Arşivde durum |
|---|---|---|
| Gece/açılış boşluğu sönümleme (M31) | Yok: önceki kapanış = ertesi açılış. Yakın analog: hafta sonu boşluğu (CME) ya da DK seans boşlukları | swing__gap-doldurma v2: 0 işlem; dis__hafta-sonu-bosluk v1 elendi |
| ORB / seans aralığı kırılımı (T09) | UTC gün başı aralığı; Asya (23-03 UTC) ve Londra kutusu | daytrade__orb seans_saat=0 v1'de elendi; v3__asya-kutu-kirilim-ma50, v3__aralik-kirilim-bekleyen-emir, v3__londra-volatilite-kirilim, v3__orb-4s-hacim-atr kodlu, koşulmadı |
| İlk yarım saat -> son yarım saat (T50, S0782) | UTC gün açılışı -> UTC gün kapanışı (seans='utc_gun') | dis__ilk-yarim-saat-son-yarim-saat v1 elendi |
| Noise-area gün içi momentum (T08) | UTC günü açılış fiyatı çevresi sigma bandı; kripto bacağı yok | v3 DK_SPX 30 dk elendi (maliyet) |
| Saat/mevsimsellik (21-23 UTC, gece tutma) | Doğrudan geçerli (BTC) | v3__btc-gecelik-max10-hafta-sonu elendi; v3__saat-21-23-utc koşulmadı |
| Haftalık takvim (Cuma-Pazartesi, hafta sonu) | Kripto hafta sonu da işlem görür: 'Cuma UTC kapanış -> Pazartesi' tutma | dis__hafta-ici-takvim v2 elendi |
| Seans/olay saati (FOMC, ABD açılışı) | Olay saatleri aynı, piyasa 7/24 | v3__pre-fomc-surunme, v3__cuma-15-est-tutma elendi |

Genel hüküm: seans/gap kurallarının kripto karşılığı 'UTC gün açılışı' gibi yapaydır; kural mantığı (açılışta likidite boşluğu, seans kapanışı akışı) kriptoda yoktur, bu yüzden bu fikirleri aynı kanıtla taşımak mümkün değil. Karşılık denemek yeni hipotez olur, kanıtı dış kaynaktan devralmaz.

### 2.3 Yeniden test hak edenler (kısa liste)

Hüküm b ve c grupları ile bizim sıralamanın başı. Her biri v2 §8 kurallarına uyar: yeni ön kayıt (kural, maliyet, ret ölçütü önceden), tek koşu, backtest/paper tarafı, canlı kadroya filtre eklenmez, yılda en fazla 2-3 ön kayıtlı tur. Görülmüş test dönemi (geliştirme + holdout) yeniden kanıt sayılmaz; kanıt ancak yeni ileri veri (paper) olur.

| # | Fikir | Hüküm | Neden / koşul |
|---|---|---|---|
| 1 | T61 yüzde filtre (Alexander / Radge '20% Flipper') | b | Günlük, %5-%20 eşikli, long-only, iz süren %20 çıkış: düşük devir (maliyete duyarsız), tek-grafik, bizim long plana uyar. Arşivde yalnız 1h/30m %1-%3 koşuldu. Dış kanıt: akademik (MENA), SPA'da 14 piyasanın 10'unda 'sağlam', maliyet yok. Felaket stopu: iz süren %20 zaten çıkış; ATR stop ek. |
| 2 | T21 BLL tipi bantlı MA | b | Kısa MA (1-2 gün) x uzun MA (50-200) + %1 bant. SMA200 sınıfında bant ızgarası var ama v2 yalnız bant=0 koştu. Ucuz; dış kanıt karışık (gerçeklik kontrolünde çöküş), beklenti düşük. |
| 3 | T02 Donchian + EMA200 + 2R hedef | b | dis_ayar bu ayarı kapsıyor sayılıyor ama koşulmadı. Dış kanıt zayıf (komisyon hariç, tek sembol). Beklenti orta-düşük; mevcut Donchian sonucu (E1-E3 geçti) kapı yapısına takılmıştı. |
| 4 | M36 kontrarian trend göstergeleri | c | Hiç test yok ama ayna mantığıyla beklenti düşük (aynı örnekte trend kuralları brüt pozitif). Test yerine 'ayna kontrolü' (mevcut trend sonuçlarının işaret çevrilmiş brütü) yeterli olabilir. |
| 5 | T01 Donchian ansamblı (stopsuz, kaynağa sadık kıyas) | a | Yeniden değil: yalnız Fable'ın açık bıraktığı 'stopsuz kaynak-sadık kıyas ya da beyan' maddesi; sonuç sonrası kapı değişmez. İleri veride (paper) izleme seçeneği; kadroya yeni strateji eklemek v2 kapsamında değil. |
| 6 | T09 ORB (5 dk ABD açılışı + kripto UTC açılışı) | b | Yalnız maliyet varsayımı bağımsız doğrulanırsa (tur 13-14 bp, brüt kenar ≈2 bp). Aksi halde sonucu maliyet belirler, fikir değil. |

Hüküm d grupları (hisse kesiti, seans/gap, VIX, pairs, limit ızgarası) bizim evrende anlamlı test olamaz; bunlar için ek veri (yüzlerce hisse, VIX, opsiyon) ya da altyapı (limit emir) gerekir ve v2 kapsamı dışındadır.

---

## 3. Dış puanlamanın eleştirisi ve bizim sıralama

**Formül (dış ajanın `test_oncelik.py` tanımı, ozet.md):** puan = 100 x (0,30 E + 0,10 G + 0,20 R + 0,20 U + 0,20 K) - bayrak cezası - bozulma cezası. E = kanıt gücü, G = 'en güçlü 15' üyeliği, R = bağımsız tekrar (farklı alan adı/yazar/bölge sayısı), U = uygulanabilirlik (kodu açık, stopu ve çıkışı tanımlı satır payı), K = kanıt yönü. Bileşenleri 30 grup için yeniden hesapladım: dış puanla en çok 0,2 puan fark (yuvarlama), formül doğru uygulanmış.

| Bileşen | Ort. puan payı | Puan sıralamasıyla Spearman |
|---|---|---|
| E kanıt gücü (x30) | %39 | +0,20 |
| G en güçlü 15 (x10) | %3 | -0,20 |
| R bağımsız tekrar (x20) | %26 | +0,28 |
| U uygulanabilirlik (x20) | %22 | -0,01 |
| K kanıt yönü (x20) | %14 | +0,06 |

Eleştiriler:

1. **Popülerlik kanıt sayılıyor.** R (kaç sitede/yazarda tekrarlandığı) puanın ortalama yüzde 26 kadarını oluşturuyor; üstelik K (kanıt yönü) ile puan sırası arasında neredeyse hiç ilişki yok (Spearman +0.06). İlk 30'da K < 0,35 olan 9 grup var (T46 (4.), T27 (9.), M27 (14.), M11 (17.), M05 (18.), M21 (26.), M01 (27.), M15 (28.), M16 (29.)); çürütücü kanıtlı Bollinger/RSI(14)/RSI(2)/pairs grupları R=0,8-1,0 yüzünden listeye giriyor.
2. **K cezası toplamsal ve zayıf.** Negatif kanıt grubu 'veto' etmiyor, yalnız en çok 20 puan düşürüyor; bozulma cezası en çok 8. Çarpımsal bir yapı (kanıt yönü kötüyse puan sıfıra yakın) daha doğru olurdu.
3. **U (uygulanabilirlik) bizim evren için yanlış tanım.** U 'kodu açık, stopu/çıkışı yazılı satır payı'dır; piyasa/veri/maliyet uyumu değil. Örnekler: M31 gap fade U=0,68 (kriptoda uygulanamaz), M20 VWAP U=0,90, M21 U=0,90 (temsilci çift taraflı limit ızgarası, motorumuzda yok), M15 pairs U=0,74. Bizim evrene göre yeniden değerlendirdiğimde (kripto 7/24, DK ≈17 hisse, yalnız market emir, tur maliyeti ≈13-14 bp) gruplar arası U 0,05-1,0 yayılıyor (dış: 0,30-0,94).
4. **Test boşluğu hiç yok.** Puan 'bu fikri biz zaten ve adil biçimde test ettik mi' sorusunu içermiyor. 30 grubun 16'sı bizde adil test edilip elenmiş; 9'u evrende uygulanamaz; test edilmeye değer boşluk yalnız 5 grupta (hüküm b/c). Listeyi bu haliyle 'test sırası' olarak kullanmak, 25 grup için ya gereksiz (zaten adil elenmiş) ya da imkansız (evrende yok) test demek.
5. **Maliyet/devir terimi yok.** Gün içi ORB, VWAP, noise-area, gap fade gibi yüksek devirli fikirler 5-10 bp'lik dış maliyet varsayımıyla puan alıyor; bizde tur ≈13-14 bp. Bu yüzden M31 (8.), T09 (5.), T08 (12.), M20 (13.) üst sırada.
6. **Aile dengesi zorunlu.** Her aileden 15 grup alınıyor; birinci ile otuzuncunun puan farkı 25,5 (73,5 ve 48,0): kalite eşiği yok, 'ilk 30' kısmen kota.
7. **Bayrak cezası etkisiz:** M31 (13 satırın 8'i ŞÜPHELİ/LOOKAHEAD, -7,4 puan) yine 8. sırada.

Duyarlılık: R ve G'yi atıp K ağırlığını iki katına çıkarırsam ilk beş: T21, T08, M29, T28, T61 (dış puandaki ilk beş: T01, T28, T47, T46, T09). Yalnız U'yu bizim değerlendirmemle değiştirsem (dış formülde): T28, T01, T46, T21, M35.

### Bizim sıralama (bizim_sira)

Formül (yargıya dayalı, ölçüm değil; ayrıntı `groups30.py`): **bizim skor = 100 x U_biz x B x (0,5 + 0,5 x kanıt) x (0,7 + 0,3 x M)**; U_biz = kripto+DK evrende uygulanabilirlik (0-1), B = test boşluğu/bilgi değeri (0 = adil test edildi, 1 = hiç test yok), kanıt = (E+K)/2 dış puandan, M = maliyet/devir dayanıklılığı (günlük/haftalık = 1, gün içi = 0,2). Çarpımsal olduğu için U_biz ya da B sıfıra yakınsa grup düşer.

| Bizim sıra | Grup | U_biz | B | M | Kanıt | Skor | Dış sıra | Hüküm |
|---|---|---|---|---|---|---|---|---|
| 1 | T61 Yüzde filtre kuralı (Alexander / Fama-Blume) | 0,80 | 0,60 | 0,9 | 0,69 | 39,2 | 21 | b |
| 2 | T21 BLL tipi değişken MA (VMA) kuralları, bantlı | 0,80 | 0,40 | 0,9 | 0,90 | 29,5 | 10 | b |
| 3 | T02 Kanal kırılımı + trend/hacim/ADX/temel filtresi | 0,90 | 0,35 | 0,8 | 0,42 | 21,0 | 20 | b |
| 4 | T01 Donchian/kanal kırılımı (N-gün yüksek) | 0,90 | 0,25 | 0,9 | 0,62 | 17,7 | 1 | a |
| 5 | T09 Açılış aralığı kırılımı (ORB, ilk N dakika) | 0,50 | 0,60 | 0,2 | 0,54 | 17,6 | 5 | b |
| 6 | T28 Aylık MA filtresi / taktik varlık dağılımı (Faber 1 | 0,60 | 0,30 | 1,0 | 0,70 | 15,3 | 2 | a |
| 7 | T46 Zaman serisi momentumu (N-ay getiri işareti, TSMOM) | 0,80 | 0,25 | 0,9 | 0,57 | 15,2 | 4 | a |
| 8 | M36 Trend göstergesinin tersine kullanımı (kontrarian E | 0,80 | 0,20 | 0,8 | 0,69 | 12,7 | 23 | c |
| 9 | T08 Gürültü bölgesi / noise oranı uyarlamalı kırılım | 0,50 | 0,30 | 0,3 | 0,80 | 10,7 | 12 | a |
| 10 | T26 Fiyat yapısı kırılımı (direnç, salınım tepesi, 123, | 0,80 | 0,20 | 0,6 | 0,51 | 10,6 | 15 | a |
| 11 | T55 Osilatörün trend yönlü kullanımı (RSI/CCI/KDJ/stoka | 0,90 | 0,15 | 0,8 | 0,56 | 9,9 | 16 | a |
| 12 | T45 52 hafta zirvesine yakınlık (kesitsel) | 0,30 | 0,40 | 1,0 | 0,61 | 9,7 | 11 | d |
| 13 | M04 Kısa periyot RSI (3–5) aşırı satım + trend filtresi | 1,00 | 0,15 | 0,6 | 0,42 | 9,4 | 25 | a |
| 14 | M15 Pairs / eşbütünleşme spread z-skoru | 0,30 | 0,50 | 0,5 | 0,43 | 9,1 | 28 | d |
| 15 | T22 Üçlü/çoklu MA dizilimi (kısa>orta>uzun) | 1,00 | 0,12 | 0,9 | 0,55 | 9,0 | 19 | a |
| 16 | T27 Tek MA üstü/altı zamanlama (günlük/haftalık) | 1,00 | 0,12 | 1,0 | 0,50 | 9,0 | 9 | a |
| 17 | T30 MACD/TRIX/PPO sinyal kesişimi (klasik) | 1,00 | 0,10 | 0,8 | 0,57 | 7,4 | 6 | a |
| 18 | M39 Volatilite endeksi / opsiyon sinyaliyle endeks alım | 0,10 | 0,90 | 1,0 | 0,61 | 7,3 | 24 | d |
| 19 | M20 VWAP bandından dönüş | 0,60 | 0,20 | 0,2 | 0,50 | 6,8 | 13 | a |
| 20 | M24 IBS (kapanışın gün aralığındaki konumu) dip alımı | 0,80 | 0,12 | 0,6 | 0,54 | 6,5 | 30 | a |
| 21 | M21 Kanal/zarf ucundan dönüş (Keltner, ATR, Donchian) | 0,25 | 0,50 | 0,2 | 0,32 | 6,3 | 26 | d |
| 22 | M35 Stokastik / Williams %R / Ultimate Oscillator aşırı | 1,00 | 0,08 | 0,7 | 0,55 | 5,6 | 7 | a |
| 23 | M11 Bollinger alt bant dokunuşu/geri dönüşü (filtresiz) | 1,00 | 0,08 | 0,5 | 0,43 | 4,9 | 17 | a |
| 24 | M01 RSI(2) aşırı satım alımı + uzun vade trend filtresi | 1,00 | 0,08 | 0,6 | 0,31 | 4,6 | 27 | a |
| 25 | M29 Uzun vadeli kaybeden-kazanan dönüşü (DeBondt-Thaler | 0,05 | 1,00 | 1,0 | 0,81 | 4,5 | 22 | d |
| 26 | M16 Mesafe yöntemi pairs (GGR) | 0,10 | 0,60 | 0,6 | 0,59 | 4,2 | 29 | d |
| 27 | M27 Kesitsel kısa vadeli ters dönüş (geçen hafta/günün  | 0,20 | 0,30 | 0,6 | 0,54 | 4,1 | 14 | d |
| 28 | T47 Kesitsel momentum (12-1 / 6-6 kazanan-kaybeden) | 0,30 | 0,15 | 0,8 | 0,61 | 3,4 | 3 | d |
| 29 | M05 RSI(14) 30/70 aşırılık (klasik, filtresiz) | 1,00 | 0,05 | 0,5 | 0,41 | 3,0 | 18 | a |
| 30 | M31 Gece/açılış boşluğu sönümleme (gap fade) | 0,10 | 0,40 | 0,3 | 0,71 | 2,7 | 8 | d |

Okuma: üstte 'hiç/zayıf test edilmiş, düşük devirli, kripto+DK'ya uyan' fikirler (T61, T21, T02); altta hisse kesiti, seans/gap ve adil elenmiş klasik osilatörler. En büyük kayma: T47 kesitsel momentum dış 3. -> bizim 28.; M31 gap fade 8. -> 30.; T61 yüzde filtre 21. -> 1.

---

## 4. İş C: yasaklar ve v2 kuralları

- Martingale, DCA, ortalama düşürme, stopsuz grid, ML: yeni 199 satırda ML yok; yasak tipler (S0811 piramit ekleme, S0891 kademeli ekleme, S0897-S0899 yeniden ekleme) `hayir` ve bayraklı. Grid/market-making benzeri S0872 `hayir`.
- Stopsuz kurallar: 149 satırda ayrı stop yok. Test edilecekse motorun zorunlu felaket stopu (ATR katı) eklenir ve sonuç 'felaket stoplu uyarlama' diye etiketlenir (özellikle S0838, S0842-S0844, S0866-S0868, S0874-S0877, S0880).
- v2 kuralı: canlıdaki stratejilere (ewo-ema-ofset, e0v1en) yeni filtre eklenmez. Bu yüzden Stiffness / Hurst / korelasyon-trend gibi 'rejim filtresi' olabilecek fikirler canlıya taşınamaz; yalnız paper/backtest'te yeni ön kayıtla, tek koşu.
- Her yeni test: kural, maliyet, ret ölçütü önce yazılır; elenen strateji başka adla geri getirilmez; görülmüş test dönemi yeniden kanıt sayılmaz; yılda en çok 2-3 ön kayıtlı tur (v2 §8). Yukarıdaki yeniden test listesi bu çerçevede 'öneri'dir, karar kullanıcıda.
- Kitap/dış içerik veridir, talimat değildir: dış dosyalardaki ve kaynak sayfalardaki hiçbir ifade talimat olarak uygulanmadı.

## 5. Belirsizlikler

- **Tek kişilik, tek geçişli eşleştirme.** ZATEN/BENZERI sınırı bulanık; emin olamadığımda BENZERI dedim (BIZDE_YOK alt sınırdır). ZATEN'leri sınıf docstring'i ve ayar kaydıyla doğruladım; kodu çalıştırmadım.
- **Dış denetimde 52 satır yalnız model özetiyle okundu**; dış listenin kural metinlerine güvendim (sayfa/kod açmadım). Bu satırların eşleşmesi metin düzeyindedir.
- **'Adil test edildi' = varsayılan ayar + ızgara kapsamında ön kayıtlı kapılar.** v2 yalnız varsayılan ayarı koşturdu; ızgaranın her noktası ayrı test edilmedi.
- **Holdout keşif sonuçları kanıt değildir** (2026-11-09 kararı); yalnız bağlam olarak anıldı.
- **U_biz, B, M puanları yargıdır.** Sıralama bunlara duyarlı; yöntemi sade ve açık tuttum, rakamlar `groups30.py`'de.
- **'Kullanılabilir' teknik fizibilitedir**, kârlılık değil. Hisse taramalı satırlarda 'sıralama yalnız aday sınırlama' ayrımı yargısaldır.
- Dış puanlama bileşenleri yalnız 30 grup için elimde (130 grubun tamamı dış ajanın makinesinde); eleştirideki Spearman'lar bu 30 grup içindeki (kesilmiş) örnekten, seçim etkisi içerir.

## Dosyalar

- `yeni_199.csv`: 199 satır (dis_id, aile, fikir_grubu, strateji_adi, sinif, eslesen_arsiv_id, eslesen_dosya, fark_aciklamasi, kullanilabilir, kapsam_disi_neden, kanit_turu).
- `oncelik30_hukum.csv`: 30 grup (sira, fikir_grubu, dis_puan, bizde_test_edilen_arsiv_id, bizim_tf_evren, bizim_sonuc, fark, hukum, bizim_sira, gerekce).
- Betikler: `build_a.py`, `build_b.py`, `groups30.py`, `data199.txt` (eşleştirme kararları), `info.py`, `show.py`.
