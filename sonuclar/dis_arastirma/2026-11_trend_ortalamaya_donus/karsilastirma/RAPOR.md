# Dış strateji listesi ↔ 1L3A arşivi karşılaştırması

_Hazırlayan: Claude (alt ajan), tarih 2026-11-12. Girdi: dış ajanın 3. tur listesi (707 satır, 119 fikir grubu, 81 bağımsız kanıt notu, özet raporu); ilk 547 satırın kararları değişmedi, 160 yeni satır (S0548+) ve 12 yeni grup aynı yöntemle eklendi. Repo okundu, hiçbir dosya değiştirilmedi._

## Kullanıcıya özet

1. Dış ajanın 707 stratejisini arşivimizle tek tek karşılaştırdım.
2. 115 tanesi arşivde aynı kuralla zaten var, 528 tanesi aynı fikir ailesinden ama farklı ayrıntıyla, yalnız 64 tanesi arşivimizde hiç yok.
3. Yani dış liste büyük ölçüde bizim zaten bildiğimiz fikirlerin tekrarı; yeni fikir azdır.
4. 118 satır dış ajanın kendi bayraklarıyla (şüpheli, geleceği görme, yasak tip) kullanılamaz; 216 satır da bizim evrenimize uymuyor (hisse sıralaması, pairs, seans saati, VIX/opsiyon, grid).
5. Geriye 420 kullanılabilir satır kalıyor; bunların çoğu zaten denenmiş ve elenmiş fikirler.
6. Arşivde olmayıp kullanılabilir olan 21 satır var (trend 9, ortalamaya dönüş 12); hepsinin kanıtı zayıf (çoğunda hiç yok).
7. Biz eledik ama dış kaynak güçlü kanıt gösteriyor: kripto Donchian ansamblı (bizde Sharpe 0,978, al-tut 0,995: ucu ucuna elendi) ve gürültü bölgesi gün içi momentum (dışta Sharpe 1,33, bizde net −%20).
8. Zaman serisi momentumu, Faber ortalaması ve kesitsel momentum da aynı durumda, ama dış kanıt hisse/vadeli evreninde; bizim ~35 sembollük evrenle birebir kıyaslanamaz.
9. Dış kaynağın da zayıf bulduğu aileler (Bollinger dönüşü, altın/ölüm kesişimi, Connors RSI(2)) bizim sonuçlarımızla uyumlu.
10. Hiçbir paper/canlı stratejimizin dış listede birebir karşılığı yok.
11. Güvenilirlik: eşleştirmeyi tek geçişte elle yaptım; belirsiz olanı "benzeri" saydım, o yüzden "yeni fikir" sayısı alt sınırdır.
12. Karar için dosyalar: karsilastirma.csv (satır satır), fikir_grubu_ozeti.csv, arsiv_envanteri.csv; ayrıntı aşağıda.

## 1. Kısaca

- 707 dış satırın **115** tanesi arşivde aynı kural (ZATEN_TEST), **528** tanesi aynı fikir ailesi ama giriş/çıkış/filtre farklı (BENZERI_TEST), **64** tanesi arşivde hiç yok (BIZDE_YOK).
- Yani dış listenin çok büyük kısmı bizim "bilinen fikir" havuzumuzun içinde; gerçekten yeni fikir az. **BIZDE_YOK ve kullanılabilir: 21 satır** (Trend 9, Ortalamaya dönüş 12). Bunların kanıtı da zayıf (çoğu "yok" ya da "yazarın kendi backtest iddiası").
- Fikir grubu düzeyinde: 119 grubun **51** tanesinde arşivde birebir aynı kural var, **46** tanesinde aynı aile var ama kural farklı, **22** grup arşivde hiç yok.
- Arşivde karşılığı bulunan fikirlerin neredeyse hepsi bizim kapılarımızda elendi. Geçen (paper/canlı) arşiv stratejileri bu eşleşmelerin içinde yok denecek kadar az; ayrıntı §6 ve `fikir_grubu_ozeti.csv`.
- Dış listedeki 118 satır bayraklı (YASAK_TİP / ŞÜPHELİ / LOOKAHEAD_RİSKİ): hepsi "kullanılamaz" işaretlendi. Ayrıca 216 satır projemizde yapılamayan türden (kapsam dışı). Toplam kullanılabilir: **420 / 707**.
- Dış raporun asıl "kanıt" mesajı (Donchian/zaman serisi momentumu sağlam, MA kesişimi/Bollinger/RSI(2) zayıf) arşivimizle büyük ölçüde uyumlu; çelişen noktalar §7'de.

## 2. Sayılar (hepsi betikle hesaplandı)

### Sınıf dağılımı

| Sınıf | Toplam | Trend | Ortalamaya dönüş | Kullanılabilir | Kullanılamaz |
|---|---|---|---|---|---|
| ZATEN_TEST | 115 | 66 | 49 | 98 | 17 |
| BENZERI_TEST | 528 | 297 | 231 | 301 | 227 |
| BIZDE_YOK | 64 | 18 | 46 | 21 | 43 |
| **Toplam** | 707 | 381 | 326 | 420 | 287 |

### Neden "kullanılamaz"

- Dış listede bayraklı: **118** satır. Bayrak dağılımı: ŞÜPHELİ: 45, LOOKAHEAD_RİSKİ: 42, YASAK_TİP: 17, YASAK_TİP ; ŞÜPHELİ: 5, ŞÜPHELİ ; LOOKAHEAD_RİSKİ: 4, LOOKAHEAD_RİSKİ ; ŞÜPHELİ: 3, ŞÜPHELİ ; YASAK_TİP: 1, YASAK_TİP ; LOOKAHEAD_RİSKİ: 1.
- Bayraksız ama kapsam dışı (benim işaretim): **169** satır. Nedenlere göre (her satır tek kategoriye, ilk eşleşen kurala göre):

| Kapsam dışı nedeni | Satır |
|---|---|
| Hisse kesitsel sıralama / çok varlıklı portföy / ETF rotasyonu | 76 |
| Borsa seansı / saat penceresi / açılış-kapanış / boşluk kuralı | 61 |
| Pairs / eşbütünleşme / spread / çapraz borsa arbitrajı | 29 |
| Veri yok (temel, olay, emir akışı, tick/1 dk, makro, açık pozisyon) | 15 |
| Grid / DCA / kademeli ekleme / katlama (proje yasağı veya motor desteği yok) | 13 |
| Opsiyon / VIX / volatilite endeksi / piyasa genişliği verisi | 12 |
| Diğer (enstrüman/borsa-özel yapı) | 10 |

Not: pairs/kesitsel gibi türler için arşivde yine de sınıf var (pf__pairs, pf__kesit_ls, pf__rotasyon…); bunlar kripto + DK_ evreninde (≈35 sembol) denendi ve elendi. Dış satırlar o sınıflara BENZERI olarak bağlandı, "kullanılabilir" ise bizim gerçek işlem evrenimize (Binance USDT perp + birkaç DK_) göre `hayir`.

### Arşiv envanteri (arsiv_envanteri.csv)

- Toplam 821 satır: 492 tek-grafik strateji sınıfı + 29 portföy sınıfı + 300 "kodlanmadı" kaydı (yasak/veri yok/kural çıkarılamadı/elenen kitap kartı).
- Durum dağılımı (strateji düzeyi, en ileri aşama esas alındı): kodlanmadi: 300, elendi_v1: 263, v2_elendi: 192, test_edilmedi: 26, v2_eleme_gecti_test_elendi: 11, elendi_v3: 9, paper: 8, v2_hata: 6, v2_kesif_set_disi: 3, canli_adayi: 2, v1_gecti_saglamlikta_elendi: 1.
- Tür (yalnız kodlu 521 sınıf; otomatik, v2 etiketi + anahtar kelime): trend: 277, diger: 128, mr: 116 ("diger" = formasyon/takvim/seviye/funding/portföy vb.). Bu sütun yaklaşıktır (bkz. §9).
- Canlı adayı: dis__ewo-ema-ofset, dis__e0v1en. Paper'da: gauss-stoch-eth, jt-awesome-osilator, uc-ortalama-boga-sma60, lube, hma-atr-rider, voltarget-trend, haftalik-macd-gunluk-ma, pf__sabit_sepet (DURUM.md v2 planı + paper_v2_seti.json).

## 3. Fikir grubu düzeyi (119 grup)

Tam tablo: `fikir_grubu_ozeti.csv`. Özet:

| Arşivde var mı | Grup sayısı | Satır sayısı |
|---|---|---|
| evet (birebir kural var) | 51 | 428 |
| hayır | 22 | 42 |
| kısmen (aynı aile, kural farklı) | 46 | 237 |

**Arşivde hiç karşılığı olmayan 22 grup** (idea düzeyinde BIZDE_YOK):

| Grup | Satır | Kullanılabilir satır | Not |
|---|---|---|---|
| M17 Emtia sanayi zinciri spread arbitrajı (跨品种) | 3 | 0 | Çin vadeli emtia zinciri; Binance'te yok |
| M18 Çapraz borsa fiyat farkı arbitrajı | 1 | 0 | İki yerel borsa arbitrajı; bizim evrende yok |
| M28 Haber / kazanç açıklaması sonrası ters dönüş | 2 | 0 | Kazanç/haber olay verisi gerekir |
| M29 Uzun vadeli kaybeden-kazanan dönüşü (DeBondt-Thaler) | 2 | 0 | 36 aylık ülke endeksi kesiti |
| M36 Trend göstergesinin tersine kullanımı (kontrarian EMA/PSAR/stokastik/DMI) | 4 | 4 | Trend göstergelerini tersine kullanmak: arşivde yok |
| M39 Volatilite endeksi / opsiyon sinyaliyle endeks alımı | 6 | 0 | VIX/SAVI/opsiyon verisi yok |
| M40 Piyasa genişliği aşırı satımında endeks alımı | 1 | 0 | Genişlik verisi yok |
| M42 Hurst üssü rejim filtresi + SMA'ya dönüş | 1 | 0 | Hurst göstergesi yok (v3 aday kartında Fable hakemi 1/10 verip kodlamadı) |
| M45 Kredili işlem aşırılığı ilanı sonrası açığa satış | 1 | 0 | JPX borsa bayrağı |
| M47 Yüksek/düşük ortalaması zarfından dip alımı (LW 3 ortalama, MMM) | 4 | 4 |  |
| M48 Çevrimiçi portföy ortalamaya dönüşü (OLMAR) | 1 | 0 |  |
| M50 Aşırılık sonrası aralık kırılımı (Momentum Pinball) | 1 | 0 |  |
| M52 Dolar bazlı/makro göreli seviyeye göre endeks ucuzluğunda alım (LatAm) | 2 | 0 |  |
| M53 Rejim anahtarlı dönüş/trend skor seçimi | 1 | 0 |  |
| T25 EMA9 yön dönüşü setup'ları (Larry Williams 9.1/9.2) | 3 | 3 | Larry Williams 9.1/9.2: arşivde yok |
| T37 CDC ActionZone (EMA12/26 + fiyat konumu renk bölgeleri) | 2 | 2 | CDC ActionZone: arşivde yok |
| T59 Hurst üssü rejim filtresi + MA trend | 1 | 1 | Hurst trend filtresi: arşivde yok |
| T62 Kârda kademeli ekleme (antimartingale) + iz stop | 1 | 0 | Kârda ikiye katlama (antimartingale): motor tek pozisyon, risk limitleriyle çelişir |
| T63 Öncü-izleyen (lead-lag) momentum | 1 | 0 |  |
| T64 VIX rejim/momentum filtresiyle zamanlama (trend) | 2 | 0 |  |
| T65 Fiyat-hacim momentum rezonansı | 1 | 1 |  |
| T66 HiLo Activator (yüksek/düşük ortalaması) yön dönüşü | 1 | 1 |  |

Gruplar arasında birebir kuralı bulunan (ZATEN_TEST içeren) en kalabalık gruplar: M05 (14/29), T17 (11/23), M09 (7/8), T46 (5/8), T27 (4/22), T05 (4/4), M13 (4/6), T30 (4/8).

## 4. BIZDE_YOK ve kullanılabilir

Toplam 21 satır. Hepsi tek grafik kuralı; bayraklı ya da kapsam dışı olanlar (pairs, VIX, grid, haber…) bu listede yok. **Kanıt çok zayıf**: 21 satırın 11'inde "kanıt yok", 7'inde yazar iddiası, yalnız 3 kontrarian satırı akademik (Nairobi Borsası endeksleri).

### Trend (arşivde yok, kullanılabilir)

| Dış id | Strateji | Mantık (tek cümle) | Dış kanıt | Piyasa / TF |
|---|---|---|---|---|
| S0362 | Backtest Larry Williams 9.1 (exemplo) - JB | EMA9 altında açılıp üstünde kapanan ilk mumun tepesi kırılınca al; EMA9 altında kapanan ilk mumun dibi kırılınca sat (Larry Williams 9.1, EMA9 yön dönüşü setup'ı). | kanıt yok (yazar sonuç vermiyor) | genel / bilinmiyor |
| S0363 | Advanced Larry Williams 9.2- By Edu | EMA9 yükselirken referans mumun dibi kırılınca "kurulum aktif", sonraki mumun tepesi tetik (Larry Williams 9.2, 9.1'in geri çekilmeli sürümü). | kanıt yok (yazar sonuç vermiyor) | hisse / bilinmiyor |
| S0418 | CDC ActionZone V3 2020 | Hızlı EMA > yavaş EMA ve fiyat hızlı EMA üstündeyken oluşan ilk "yeşil" bar kapanışında al, ilk "kırmızıda" sat (Tayland CDC ActionZone). | yazarın iddiası (%35-40 isabet, kâr faktörü 2-3) | genel / büyük zaman dili |
| S0419 | action zone - ATR stop reverse order strateg | ActionZone'un ATR stoplu, minimum tutma süreli ters çevirme (stop-and-reverse) türevi: EMA kesişiminde yön değiştir. | kanıt yok (yazar sonuç vermiyor) | kripto / 1 saat (önerilen |
| S0511 | Hurst Exponent Trend Strategy (0227) | Hurst üssü (100 bar R/S) > 0,55 ise trend rejimi: SMA(20) yönünde long/short, Hurst düşerse çık (rejim filtresi olarak Hurst). | yazarın backtest iddiası (yıllık ~%40, kripto 5dk, dönem belirsiz) | kripto ; genel / 5 dakika |
| S0515 | Traders' Tips – The Vortex Indicator (Botes  | Vortex VI+ VI-'yi yukarı keserse kesişim barının yükseğine buy-stop, aşağı keserse düşüğüne sell-stop, stop-and-reverse. | yazarın iddiası (2 yılda 24 işlem, maliyetsiz) | endeks ; hisse / günlük |
| S0626 | 成交量的奥秘：另类价量共振指标的择时 (华创证券 研报复现, VM_Strategy) | HMA(50) fiyat momentumu × HMA hacim momentumu çarpımı eşik üstünde long (fiyat-hacim rezonansı). | yazar backtest iddiası (araştırma raporu reprodüksiyonu) | endeks / günlük |
| S0683 | Un sistema con indicadores clásicos | SMA20 aşağı eğimden yukarı döndüğünde ertesi gün al, RSI(10) filtresiyle (MA eğim dönüşü). | kanıt yok | hisse / günlük |
| S0702 | _EXEC_VIRADA_HILOW (virada do HiLo Activator | Kapanış HiLo Activator(7) çizgisinin üstüne çıkınca al, altına inince çık (Brezilya Profit). | kanıt yok | endeks ; hisse / gün içi (grafik  |

### Ortalamaya dönüş (arşivde yok, kullanılabilir)

| Dış id | Strateji | Mantık (tek cümle) | Dış kanıt | Piyasa / TF |
|---|---|---|---|---|
| S0069 | DMI Swings (by Coinrule) | ADX>45 iken -DI>+DI ise ("güçlü düşüşte") ters yönde AL; +DI>-DI olunca çık (Coinrule DMI kontrarian). | yazarın iddiası (sayı yok) | kripto / 1 dakika gibi ço |
| S0112 | A different indicator (DV2) | DV2 göstergesi (kapanışın (H+L)/2'ye göre normalize edilmiş 2 günlük ortalaması) <10 + SMA200 üstü + 6 aylık getiri>0 iken sonraki açılışta al; önceki günün zirvesi aşılınca çık (Connors DV2). | yazarın backtest iddiası: yıllık %20,9, Sharpe 1,01, 2004+ S&P 500 hisseleri | hisse / günlük |
| S0236 | ATRくん | Her barda önceki kapanış ± c×ATR(14) seviyesine ters yönde limit emir koy, karşı limitte kâr al, 4 bar zaman stopu (limit emir tabanlı dönüş). | yazarın iddiası (sayı yok) | kripto / 15 dakika |
| S0377 | Reversal closing price (Preço de Fechamento  | Brezilya "kapanış dönüşü": mum dibi son 2 mumun dibinin altında ama kapanış önceki kapanışın üstünde ve kısa MA > uzun MA ise al (PFR benzeri). | kanıt yok (yazar sonuç vermiyor) | hisse ; endeks / günlük ; haftalı |
| S0378 | MY BOX by Gustavo (PFR com alvo Fibonacci 1, | PFR mumu (fiyat dönüş barı) oluşunca sonraki mum PFR kapanışını kırarsa al, hedef Fibonacci 1.618 uzantısı. | kanıt yok (yazar sonuç vermiyor) | genel / bilinmiyor |
| S0465 | Contrarian EMA50 & DMS rule (Contrarian Tech | Trend sinyalinin tersi: endeks EMA50 altında + Wilder +DM<-DM iken piyasada ol (kontrarian EMA50 & DMS, Nairobi borsası). | akademik makale (Nairobi Borsası, 2006-2013): kontrarian kurallar al-tut üstünde anlamlı fazla getiri iddiası | endeks / günlük |
| S0466 | Contrarian Parabolic SAR rule (Nairobi Stock | Fiyat Parabolic SAR'ın ALTINDAYKEN (normalde sat sinyali) long gir, SAR üstüne çıkınca çık (kontrarian PSAR). | akademik makale (aynı çalışma): on kontrarian kuralın hepsi anlamlı iddiası | endeks / günlük |
| S0467 | Contrarian Stochastic rule (Nairobi Stock In | %K<%D ve %D düşüyorken (normalde sat sinyali) long gir; koşul bozulunca çık (kontrarian stokastik). | akademik makale (aynı çalışma): al-sat günü farkı anlamlı; kural çok sık gir-çık ürettiği için strateji testinde sorunlu | endeks / günlük |
| S0578 | SlowPotato | Düşük, son 1440 mumun düşükler ortalamasına eşit/altına inince al, yüksekler ortalamasında çık (SlowPotato, 5dk kripto). | kanıt yok | kripto / 5m |
| S0583 | MMM (Média Móvel de Máximas e Mínimas) | Kapanış SMA30 üstünde ve son 3 düşüğün SMA(3)'ü altına inince al, 3 yüksek SMA'sı üstünde çık (MMM, Brezilya). | yazar backtest iddiası | kripto / 1h (sonuç dosyas |
| S0584 | MongeYokohama | Kapanış düşüklerin EMA(5)/1.02 altına inince al, yüksek EMA(7) üstünde çık (Monge Yokohama). | kanıt yok | kripto / bilinmiyor (kodd |
| S0697 | Setup Larry Williams Clássico (STP0003, médi | SMA20 yükselirken düşük son 3 düşüğün SMA(3)'ü altına inince düşüğe buy-stop (Larry Williams klasik setup). | kanıt yok | hisse ; endeks / bilinmiyor (graf |

Yorum: (1) Williams 9.1/9.2, CDC ActionZone, Vortex zaten bildiğimiz "EMA/yön göstergesi" ailelerinin kozmetik varyantı; yeni bilgi getirmez. (1b) 3. turdan gelen **yüksek/düşük ortalaması zarfı dip alımı** (M47: S0578, S0583, S0584, S0697) ve **HiLo Activator** (S0702) ucuz ve arşivde yok ama kanıtsız; fiyat-hacim rezonansı (S0626) ve MA eğim dönüşü (S0683) de öyle. (2) **Hurst rejim filtresi** (S0511 trend, S0512 ortalamaya dönüş) ve **kontrarian trend göstergeleri** (S0465-467, S0069) gerçekten arşivde olmayan iki fikir; ikisi de ucuz test edilir (Hurst bir filtre, kontrarian tersine çevirme). Ama kanıtları zayıf ve bu projede "yeni fikir" yerine "yeni ön kayıt + ileri veri" kuralı geçerli (DURUM.md). (3) S0112 (DV2) tek ciddi sayı veren satır, ama ABD hisse evreninde ve sıralamalı portföy; bizim evrende çalışacağı belirsiz.

### BIZDE_YOK ama kullanılamaz (43 satır)

Bayraklı olanlar ya da kapsam dışı. En çok neden: Hisse kesitsel sıralama / çok varlıklı portföy / ETF rotasyonu: 11, Opsiyon / VIX / volatilite endeksi / piyasa genişliği verisi: 9, Grid / DCA / kademeli ekleme / katlama: 8, Pairs / eşbütünleşme / spread / çapraz borsa arbitrajı: 5, Veri yok: 4, Diğer: 3, Bayraklı: 2, Borsa seansı / saat penceresi / açılış-kapanış / boşluk kuralı: 1. Liste `karsilastirma.csv` içinde (sinif=BIZDE_YOK, kullanilabilir=hayir).

Önemli not: dış listede **bayraksız** görünen 6 grid/DCA satırı (S0050, S0065, S0066, S0072, S0206, S0207) proje politikasına (martingale/grid/DCA yasak) göre "kullanılamaz" işaretlendi. Dış ajan bunları bayraklamamış.

## 5. BENZERI satırlarda "bizde olmayan bileşen" (kullanılabilir, kanıtı olanlar)

BENZERI satırların çoğu parametre/çift farkı. Aşağıdakilerde ise somut bir bileşen arşivde yok ve dış kaynak bir kanıt sunuyor (akademik ya da bağımsız not). Hepsi tek hat, arşivdeki en yakın sınıf yanında:

| Dış id | Strateji | Eksik bileşen | En yakın arşiv | Kanıt |
|---|---|---|---|---|
| S0047 | dual_moving_average | SMA 100/300 long-only; 100/300 çifti bizde yok (kartlarda 50/200, 20/50). | swing__ma-kesisim | yok; 2 bağımsız not (1 karışık; 1 çürütüyor): [karışık] [kapsam: genel, MA/ |
| S0060 | Keltner Channel Strategy | Keltner alt/üst bandı kesişimi dönüş modülü + EMA trend modülü; bizde Keltner kırılım (trend) var, Keltner MR bandı yok. | swing__bant-donus | yok; 1 bağımsız not (1 çürütüyor): [çürütüyor] [kapsam: Keltner ile ortalam |
| S0175 | TurtleSignalStrategy (海龟信号) | Turtle: 20 bar buy-stop, kârda her 0.5×ATR'de ekleme (en fazla 4 birim), 10 bar çıkış; piramit ekleme bizde yok. | swing__donchian-kirilim | yok; 2 bağımsız not (1 çürütüyor; 1 destekliyor): [çürütüyor] [kapsam: TURT |
| S0195 | turtle (rqalpha 海龟) | 55 gün zirve, kârda 0.5×ATR'de birim ekleme, 20 gün dip çıkış; piramit ekleme bizde yok (55/20 ızgarada). | swing__donchian-kirilim | yok; 1 bağımsız not (1 çürütüyor): [çürütüyor] [kapsam: TURTLE] Aylık/hafta |
| S0249 | 전략 12. 평균 노이즈 비율 + 마켓 타이밍 + 변동성 돌파 | k = 20 günlük ort. noise oranı ile uyarlamalı volatilite kırılımı; uyarlamalı k bizde yok. | v3__volatilite-kirilim-k05 | backtest iddiası; 1 bağımsız not (1 destekliyor): [destekliyor] Açılış bazlı oynaklık ba |
| S0253 | RSI(2) 전략 | RSI(2)<=5 + MA200 + MA5 altı koşulu + MA5 üstü çıkış; çıkış tipi bizde yok. | swing__rsi-asiri-donus | yok; 1 bağımsız not (1 karışık): [karışık] RSI(2)<5 + kapanış<MA5, MA5 üstü |
| S0297 | RISOTTO – RSI Optimized Trend Tracke | RISOTTO: VAR(RSI(100)) çizgisi kendi OTT'sini geçince; RSI üzerinde OTT bizde yok (PMax RSI-T3 benzer). | dis__ott-var | yok; 1 bağımsız not (1 karışık): [karışık] [kapsam: OTT ailesi birleşik sis |
| S0306 | MA kuralları (1,2,5 / 10–60, %1 bant | BLL: kısa MA (1,2,5) uzun MA (10-60) bant kadar aşınca; bant (%1) için dis__ema-esik-trend eşikli durum var, 1-2 günlük MA yok. | dis__ema-esik-trend | akademik makale |
| S0353 | T-26 (Backtest da Estratégia de Anál | EMA26 + HiLo Activator(4) + RSI>50; HiLo Activator bizde yok. | swing__ma-geri-cekilme | akademik makale |
| S0364 | Cruzamento de médias móveis 12/108 — | 12/108 ortalama kesişimi 5 dk; çift ve TF bizde yok. | swing__ma-kesisim | akademik makale |
| S0365 | Estrategia MACD (12,26,9) con filtro | MACD kesişimi + EMA eğim filtresi yönünde; eğim filtresi yok. | swing__macd-sinyal | akademik makale |
| S0373 | IFR2 sem filtro | IFR2 eşik 20, 5 mum zaman stopu + ATR iz stop; bizde çıkış farklı, filtre yok. | dis__ifr2 | akademik makale |
| S0381 | Estrategia Williams %R (WPR) con fil | WPR -80/-95 + EMA eğim filtresi; eşik -95 ve eğim filtresi bizde yok. | swing__rsi-asiri-donus | akademik makale |
| S0389 | 100/200 SMA death cross / golden cro | SMA 100/200 L/S; 100/200 çifti bizde yok. | swing__ma-kesisim | yok; 1 bağımsız not (1 karışık): [karışık] [kapsam: 50/200 kesişimi; ayrıca |
| S0395 | Variable Moving Average (VMA) rules  | VMA bantlı kural, 'double or out' kaldıraçla ikiye katlama; kaldıraç katlama bizde yok. | dis__ema-esik-trend | akademik makale; 7 bağımsız not (4 destekliyor; 2 çürütüyor; 1 karışık): [destekliyor]  |
| S0396 | Trading Range Breakout (TRB) rules – | TRB L=50/150/200 gün + %1 bant; kirilim_pct parametresi var ama periyotlar ızgara dışı (10/20/55). | swing__donchian-kirilim | akademik makale; 3 bağımsız not (2 karışık; 1 çürütüyor): [karışık] TRB(50–200, 10 gün  |
| S0430 | BB-BR (ดัชนีชี้วัดโบลิงเจอร์แบนด์ แบ | İki gün alt bant altında kaldıktan sonra yükselip hâlâ altta: iki gün şartı bizde yok. | swing__bant-donus | akademik makale |

## 6. Arşivde karşılığı olan fikirler bizde ne oldu?

Fikir grubu düzeyinde arşivdeki sonuç (birebir eşleşme varsa o, yoksa en yakın eşleşme): elendi: 92, arşivde yok: 22, elendi (bir kısmı test edilmedi): 2, test edilmedi: 2, kısmen geçti (set dışı): 1.

Hiçbir grupta "geçti" yok (yalnız T58 KAMA 'kısmen geçti, set dışı'): arşivde paper/canlıya giden 10 strateji (ewo-ema-ofset, e0v1en, gauss-stoch-eth, jt-awesome, uc-ortalama-boga-sma60, lube, hma-atr-rider, voltarget-trend, haftalik-macd-gunluk-ma, pf__sabit_sepet) dış listedeki hiçbir satırla birebir eşleşmedi. En yakınları: ewo-ema-ofset aynı NostalgiaForInfinity ailesinden (3. turdaki S0575 NFIX7 BENZERI; ewo/e0v1en adı dış listede yok), haftalik-macd-gunluk-ma ↔ S0084 / S0438 (haftalık MACD + günlük filtre; yakın ama farklı), gauss-stoch/lube/hma-atr-rider TradingView/Pine kaynaklı ve dış listede karşılığı yok.

Kısa not: bizim kapılarımız ağır (v1'de DSR kapısı 58 adayın 58'ini düşürdü; v2'de en az 200 işlem şartı yavaş stratejileri yapısal olarak eliyor; sepet sınıfları −%20 kill switch'e takılıyor). Yani "elendi", fikrin yanlış olduğunu değil, bu evrende bu kapılardan geçemediğini söyler.

## 7. Çelişki listesi: biz eledik, dış kaynak güçlü kanıt gösteriyor

Ölçüt: arşivde aynı/çok benzer kural kapılarda elendi VE dış kaynakta akademik ya da bağımsız "destekliyor" notu var. Sayılar `arsiv_envanteri.csv` durum_ayrintisi ve `sonuclar/` dosyalarından.

| # | Aile (grup) | Dış kanıt | Arşivde ne oldu | Not |
|---|---|---|---|---|
| 1 | Çoklu Donchian ansambli, kripto (T03: S0533; ayrıca T01 S0235, S0002) | Zarattini-Pagani-Barbon: kripto Donchian ansambli 2015-2025, %0,10 maliyetle net CAGR %18, BTC'ye karşı yıllık %11 alfa. S0002: BTC'de 10 günlük max alımı 2022-24 örneklem dışında çalışıyor. | pf__v3-donchian-ansambl (aynı kaynak) v3 elemesinde ELENDİ: P6 (strateji Sharpe 0,978 ≤ al-tut 0,995; net×2 +%67,7, 1942 işlem). swing__donchian-kirilim v2'de elendi (E4/E5), v1 WF 0/2. | En yakın kaçan arşiv ailesi. Fark: bizim kapı "al-tut Sharpe'ını geçme" şartı koyuyor; dış kaynak alfayı BTC'ye göre veriyor. Kapılar sonuç sonrası değiştirilmez (ön kayıt). |
| 2 | Gürültü bölgesi gün içi momentum (T08: S0199, S0532; S0249) | Beat the Market (Zarattini-Aziz-Barbon): SPY 2007-2024 net Sharpe 1,33; 33 vadelide ort. 0,60. | v3__gunici-momentum-noise-alani (DK_SPX 30m, 121 işlem): ELENDİ, net×2 −%20, PF 0,13, rastgele-giriş p=0,0005 (anlamlı ama net negatif). INCELEME_NOISE.md: motor hatası yok. | Dış sonuç ETF/vadeli ve dakikalık veriyle; bizim DK_SPX uyarlaması 30 dakikalık. Doğrudan çelişki: aynı fikir, ters sonuç. |
| 3 | Zaman serisi momentumu (T46: S0142, S0143, S0144…) | 7 satırın 7'si akademik (Moskowitz-Ooi-Pedersen, Hurst-Ooi-Pedersen 1/3/12 ay oy). Kripto için S0153: boğada yoğun, yalnız-kısa kaybettiriyor (karışık). | v2__tsmom-12-1 (E1 net<0), v2__tsmom-oy (E4), dis__tsmom (E2: 33 işlem < 200; E5 kill), v1 WF 0/2. | "En az 200 işlem" kapısı aylık işaret kuralını yapısal olarak eler. Dış kanıt çok-varlıklı portföyde (onlarca vadeli); bizim tek-grafik yorumumuz farklı. |
| 4 | Aylık MA filtresi / Faber (T28: S0141, S0157) | S0141: 28 emtiada 6-12 aylık MA filtresi Sharpe 0,66-0,76, MDD al-tut'un ~1/3'ü. | pf__trend_sepet v2'de E5 (kill_olayi 8), v1 sağlamlıkta K2/K5 kaldı; dis__sma200-ls v2 K2 p=0,004 ama BH/BY keşfi olmadı. | Sepet sınıfında −%20 kill switch tetiklendi; dış kanıt emtia için. |
| 5 | Kesitsel momentum, dual momentum, sektör rotasyonu (T47-T49: S0271, S0398, S0154…) | Akademik: JT momentumu yayın sonrası aylık %1,01 (t=4,10); vol ölçekli WML Sharpe 1,26; sektör momentumu 2000 sonrası zayıflıyor (çürütücü not). | pf__kesit_ls, pf__rotasyon, pf__gem, pf__sinif_kesit_mom v2'de E1/E5 ile elendi; pf__v3-fip-kesitsel-momentum (P1/P4/P5) ve kripto-max-piyango (P1/P4) v3'te elendi. | Dış kanıt yüzlerce hisse üzerinde; bizim evrenimiz ≈35 sembol (≈15 kripto). Karşılaştırılabilir değil, çelişki sayılmaz ama uyarı. |
| 6 | IBS dip alımı (M24: S0097, S0162) | Kanıt çoğunlukla yazar backtest'i; S0162 akademik (ülke ETF'leri). | pf__ibs_donus v1 WF geçti (1/1), v1 sağlamlıkta K2/K5 kaldı; v2'de E1: Sharpe 0,44 < 0,5 (net×2 +%8,9). dis__ibs-donus v1 0/2, v2 E1. | Arşivde "az farkla" kalan nadir aile. |
| 7 | Tüm zamanlar zirvesi / zirveye yakınlık (T44, T45: S0147, S0154) | S0147: Wilcox-Crittenden tipi 1991-2024 brüt CAGR %15,19, alfa %6,18, örneklem dışı 2005-2024. S0154: 52 hafta zirvesi, JT'den güçlü. | dis__yeni-zirve-trend-filtresi (200 gün yeni zirve) v1'de 1d geçti, sağlamlıkta K5 DSR'de kaldı; v2'de E1 net<0. swing__goreceli-guc-momentum elendi. | Dış kanıt hisse; kripto ATH davranışı farklı. |

**Dış kaynağın da çürüttüğü, bizim de elediğimiz aileler (uyumlu, sorun yok):** Bollinger bandı ortalamaya dönüşü (M10-M12: S0049, S0216, S0113 "al-tut altında"), altın/ölüm kesişimi ve BLL MA kuralları (T16, T21: STW/Reality Check çöküşü), Connors RSI(2) (M01: veri madenciliği eleştirisi), ilk-yarım-saat→son-yarım-saat momentumu BTC'de (S0149 maliyet sonrası kârsız), Turtle aylık kanal (S0011/S0076 EUR/USD PF 0,94).

## 8. En dikkat çekici 10 aday

Sıralama "arşivde yok ya da zayıf test + dış kanıt + bizim evrende uygulanabilir" mantığıyla; hiçbiri doğrudan teste alınmamalı, DURUM.md'ye göre önce karar + ön kayıt gerekir.

| # | Aday | Sınıf | Neden dikkat çekici |
|---|---|---|---|
| 1 | S0533 / S0235 Çoklu Donchian ansambli (kripto) | ZATEN (v3 elendi) | Dış kanıtı en güçlü ve kripto: CAGR %18, BTC'ye karşı %11 alfa. Arşivde near-miss (Sharpe 0,978 vs al-tut 0,995). |
| 2 | S0199 / S0532 Noise-area gün içi momentum | ZATEN (v3 elendi) | Akademik Sharpe 1,33 (SPY) ama bizde net −%20; çelişki, nedeni incelenmeye değer (veri çözünürlüğü, maliyet, DK_SPX kısa tarihçe). |
| 3 | S0153 Adaptif trend 6s (kripto, ATR iz stop) | ZATEN (v3 kodlandı, test edilmedi) | Kripto-özel, kod hazır, v3 elemesine hiç girmemiş; dış kanıt "karışık". |
| 4 | S0511 / S0512 Hurst rejim filtresi | BIZDE_YOK | Filtre olarak mevcut stratejilere bindirilebilir (rejim bindirmesi v2'de yoktu). Dış iddia: kripto 5dk yıllık %40 (zayıf kanıt, S0512 ŞÜPHELİ bayraklı). |
| 5 | S0465-S0467, S0069 Kontrarian trend göstergeleri | BIZDE_YOK | Üç satır akademik (anlamlı fazla getiri iddiası). Arşivdeki klasik trend aileleri (MA kesişimi, MACD, Supertrend vb.) kapılarda çoğunlukla elendi; tersine çevirme ucuz bir hipotez (ama aynı kapılar maliyet nedeniyle onu da eleyebilir). |
| 6 | S0508 Funding ortalamaya dönüşü (BitMEX XBTUSD) | ZATEN (v2 elendi) | Kripto-özel; v2__funding-asiri-kontra elendi (E1). Dış kanıt yok; yalnız mantık. |
| 7 | S0097 / pf__ibs_donus IBS dönüşü | ZATEN (v1 geçti, v2 elendi) | Arşivde "az farkla" kalan: v2 Sharpe 0,44 (eşik 0,5), net×2 +%8,9. |
| 8 | S0386 Hacim + mum boyu z-skoru düşüş dönüşü | BENZERI (onceki__kapitulasyon) | Arşivde kapitülasyon dönüşü v1 1d WF'i geçti (sağlamlıkta K2/K5'te kaldı), v2'de E2 (181 işlem < 200) ve E4 ile elendi; dış kural z-skor/yüzdelik tanımıyla daha ince, 1 dk veri. |
| 9 | S0175 / S0195 Turtle + kârda piramit ekleme | BENZERI (donchian) | Piramit bizde yok (motor tek pozisyon); dış kanıt karışık (Irwin-Brorsen destekliyor, EUR/USD aylık kanal PF 0,94 çürütüyor). |
| 10 | S0112 DV2 dip alımı | BIZDE_YOK | Dış listede en sayısal iddia (yıllık %20,9, Sharpe 1,01, 21 yılda 1 negatif yıl) ama hisse evreninde sıralamalı portföy; tek-grafik karşılığı belirsiz. |

### 3. turdan (S0548+) çıkan dikkat çekenler

160 yeni satır: ZATEN 22, BENZERI 118, BIZDE_YOK 20; kullanılabilir 80, bayraklı 36. Yeni satırların çoğu Freqtrade/QuantConnect/BIST/Nifty/B3 derlemesi; 22'si birebir arşivde (freqtrade stratejileri, TD Sequential, VWAP alt bant, PSAR, Donchian 20/çift kanal).
- **S0575 NostalgiaForInfinityX7**: canlı adayımız ewo-ema-ofset'in geldiği aile; arşivde üç çekirdek kolu kodlu, ama tam koruma kümesi yok (BENZERI).
- **M47 (LW yüksek/düşük ortalaması zarfı: S0578 SlowPotato 5dk kripto, S0583, S0584, S0697)**: arşivde hiç yok, tek mantık "düşük, son N düşüğün ortalamasının altına inince al", ucuz test; kanıt yok/zayıf.
- **T66 HiLo Activator (S0702), T65 fiyat-hacim rezonansı (S0626), S0683 MA eğim dönüşü**: yeni, kanıtsız.
- **S0630 hacim profili değer alanı**: arşivde dis__vp-deger-alani var (BENZERI).
- Yeni VIX/makro/kesitsel/pairs/grid satırları kapsam dışı (örn. S0628 "做T" bayraksız ama kademeli ekleme/grid).

## 9. Yöntem ve belirsizlikler

**Yöntem.** (1) Arşiv: `motor/strateji/` altındaki tüm sınıflar kayıt mekanizmasıyla içe aktarıldı (492 tek-grafik sınıf), `motor/portfoy/stratejiler/` taranarak 29 portföy sınıfı eklendi; kitap/dış kaynaklı sınıfların açıklaması sınıf docstring'inden, kitap aileleri için `aileler.json` mekanik özetinden alındı. Çalıştırılmış sonuçlar `sonuclar/evren/2017_gelistirme/wf_evren.csv` (v1 WF, 939 satır), `sonuclar/evren/v2/{eleme,test,saglamlik,holdout_kesif}`, `sonuclar/v3/eleme.csv` ve `stratejiler/paper_v2_seti.json` ile eşleştirildi. (2) Eşleştirme: 707 satırın hepsi tek tek, kural metni + parametre okunarak elle yapıldı (isimden değil); her ZATEN/BENZERI satırında somut arşiv id'si ve dosya yolu var; id'lerin hepsi envanterde otomatik doğrulandı. Ayar kapsamını anlamak için sınıf docstring'leri, `kart_ayarlari/` ve `dis_ayarlari/` JSON'ları ve parametre ızgaraları okundu. (3) Doğrulama: ZATEN satırlarının arşiv karşılığı sınıf docstring'leriyle tek tek karşılaştırıldı; bu turda 6 satır düzeltildi (S0016, S0078, S0244, S0321 ZATEN→BENZERI; S0245 BENZERI→ZATEN; S0350 ZATEN→BENZERI; S0386 BIZDE_YOK→BENZERI). (4) Sayılar betikle üretildi; betikler bu klasörde (`build_arsiv.py`, `build2.py`, `build3.py`, `build4.py`, `rapor.py`), karar girdileri `k/*.txt`.

**Belirsizlikler (dürüstçe):**
- **Eşleştirme tek kişilik, tek geçiş.** ZATEN/BENZERI sınırı bulanık: ben "aynı çekirdek kural + parametre kümemiz (varsayılan, ızgara, kart/dış ayar) içinde" ise ZATEN dedim; dis_ayarlari'ndaki ayarların çoğu "YAKLAŞIK" (filtresiz) olduğundan filtreli dış kural varsa BENZERI dedim. Emin olamadığım yerde BENZERI dedim; bu yüzden BENZERI şişkin, BIZDE_YOK ise "mutlak yeni fikir" için alt sınırdır. BENZERI içinde en yeni görünenler `fark_turu_otomatik = eksik bileşen/parametre` etiketli satırlardır (§5).
- ZATEN'lerin bir kısmı arşivde kodlanmış ama koşusu yok: v3__aralik-kirilim-bekleyen-emir, v3__volatilite-kirilim-k05, v3__adaptivetrend-6s-momentum gibi. `eslesen_arsiv_durum` sütunu bunu gösterir (test_edilmedi).
- Dış satırların bir kısmı (ör. BLL, Turtle, golden cross) arşivde ızgara/kart ayarı olarak vardır ama o ayar v1 WF'te seçilen adaylar arasındaydı; v2 yalnız varsayılan ayarı koşturdu. "Test edildi" demek her ayarın ayrı test edildiği anlamına gelmez.
- **Tür ve gösterge ailesi sütunları otomatik** (v2 etiketi varsa o, yoksa anahtar kelime): hata payı yüksek, özellikle "diğer" ve "mr/trend" sınırında. Karar vermek için kullanılmamalı.
- **Kullanılabilir = teknik/proje fizibilitesi**, kârlılık kanıtı değil. Pairs/kesitsel/portföy satırları için arşivde sınıf var ama "kullanılabilir" gerçek işlem evrenimize göre `hayir` yazıldı; isterseniz bu karar kullanıcıyla netleştirilmeli.
- Dış kanıt gücü (fikir_grubu_ozeti) kaba bir etiket: akademik satır sayısı + bağımsız not yönleri. {len(kan)} notun {sum(1 for k in kan if k["yon"]=="destekliyor")}'si destekliyor, {sum(1 for k in kan if k["yon"]=="çürütüyor")}'i çürütüyor, {sum(1 for k in kan if k["yon"]=="karışık")}'ı karışık; notların bir kısmı grup düzeyinde ("genel", "kapsam: TURTLE") ve ilgili satırlara elle dağıtıldı.
- Arşivdeki "elendi" bizim ön kayıtlı kapılarımıza göre; v1'de sonuç dosyaları (DSR dahil) sonradan değişen eşiklerle üretildi, v2/v3 ayrı ön kayıtlarla. Karşılaştırma yaparken kapıların farklı olduğu akılda tutulmalı.
- Veri: DK_ hisse/emtia tarihçesi kısa; scalp ve gün içi sonuçlar kripto ağırlıklı. Dış kanıtın çoğu hisse/endeks/vadeli.

## 10. Dosyalar

Hepsi `/tmp/claude-0/-home-user/d9801314-f689-5b3c-ae41-5973e32ea499/scratchpad/karsilastirma/` altında:
- `karsilastirma.csv` (707 satır): dis_id, aile, fikir_grubu, strateji_adi, sinif, eslesen_arsiv_id, eslesen_dosya, fark_aciklamasi, kullanilabilir, kapsam_disi_neden, kanit_turu, kanit_ekleri_ozeti (+ yardımcı: alt_tur, eslesen_arsiv_durum, bayrak_kullanilamaz, fark_turu_otomatik, piyasa, zaman_dilimi).
- `fikir_grubu_ozeti.csv` (119 satır).
- `arsiv_envanteri.csv` (821 satır).
- `RAPOR.md` (bu dosya).
