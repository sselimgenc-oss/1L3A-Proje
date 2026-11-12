# 417 açık kural, az sayıda sağlam kanıt

Altı bölge kümesi ve dört platform/kaynak kümesi olmak üzere on kümeden gelen 419 ham satır, iki birleştirmeden sonra **417 benzersiz stratejiye** indi: **217 TREND** ve **200 ORTALAMAYA_DONUS**. Böylece "her aile için en az 100, toplamda 200+" hedefi karşılandı. Ancak listenin ağırlığı kanıtta değil kural açıklığında. 236 satırda (%56,6) hiçbir performans kanıtı yok, 118 satır yalnız yazarın kendi backtest iddiasına dayanıyor ve 61 satır akademik çalışmadan geliyor. Canlı kayıt iddiası yalnız 2 satırda var ve ikisi de zayıf. En sağlam kanıt, çok varlıklı vadelilerde zaman serisi momentumu ve hareketli ortalama filtrelerinde, pairs trading'de ve kısa vadeli ters dönüşte bulunuyor. Bunların hepsinde yayın sonrası zayıflama ya da maliyete duyarlılık da raporlanmış. Popülerlik 288 satırda (%69,1) ölçülemedi. Bu yüzden "en popüler" yargıları etkileşim sayısına değil, aynı kuralın kaç bağımsız kaynakta tekrarlandığına dayanıyor. 65 satır en az bir bayrak taşıyor. Bunlar listede yalnız kayıt amacıyla tutuluyor, uygulanması önerilmiyor.

## Toplam, aile, bölge ve platform dağılımı

Bölge, kaynağın dil ya da bölge kümesine göre atandı. A5, A6 ve A7 Asya'ya, A8 Avrupa'ya, A9 Amerika'ya, A10 Afrika+Orta Doğu'ya yazıldı. A1–A4 (kod depoları, grafik platformları, İngilizce forum ve bloglar, akademik kaynaklar) "Küresel/İngilizce" kabul edildi. Tek istisna, Hindistan merkezli marketcalls.in'deki 2 satır; bunlar Asya'ya yazıldı. ABD'ye bağlı İngilizce satırlar (22 adet, hepsi akademik kümeden) Amerika'ya sayılsaydı Amerika toplamı 57 olurdu.

| Bölge | Satır | TREND | ORT. DÖNÜŞ | Farklı alan adı (ana link) | Alan adı (ek kaynaklar dahil) | Farklı yazar/yayıncı |
|---|---|---|---|---|---|---|
| Asya | 139 | 80 | 59 | 31 | 34 | 64 |
| Avrupa | 44 | 19 | 25 | 12 | 14 | 31 |
| Amerika | 35 | 18 | 17 | 16 | 19 | 25 |
| Afrika+Orta Doğu | 30 | 17 | 13 | 12 | 13 | 19 |
| Küresel/İngilizce | 169 | 83 | 86 | 30 | 42 | 107 |
| **Toplam** | **417** | **217** | **200** | 95 | — | 246 |

"Her kıtadan en az 15 kaynak" hedefi yazar/yayıncı sayısında her bölgede karşılanıyor. Alan adı sayısında ise karşılanmıyor: **Avrupa 12** ve **Afrika+Orta Doğu 12** farklı alan adında kalıyor, ek kaynaklar dahil edilse bile sırasıyla 14 ve 13. Amerika 16 alan adıyla sınırı ancak geçiyor ve bu bölgenin 26 satırı Brezilya'dan geliyor. GitHub (alan adı olarak tek sayılır) ve tek bir yayıncıdan çok satır (ör. OANDA証券'ten 13, VisualChart kataloğundan 7) bölgesel çeşitliliği alan adı ölçüsünde düşük gösteriyor.

Ülke/dil kırılımı: **Asya:** Çin 47, Japonya 25, Kore 22, Hindistan 21, Türkiye 13, Vietnam 5, Malezya 3, Tayland 2, Endonezya 1 · **Avrupa:** Rusça 18, İngilizce yayın (ProRealCode toplulukları) 12, İspanyolca 9, Fransızca 3, Almanca 2 · **Amerika:** Brezilya 26, Kolombiya 5, Ekvador 3, Meksika 1 · **Afrika+Orta Doğu:** Güney Afrika 10, İran 8, Mısır 6, Arapça (küresel aracı kurum sayfaları) 2, Nijerya 1, Suudi Arabistan 1, Körfez 1, BAE 1.

| Platform türü | Satır | TREND | ORT. DÖNÜŞ |
|---|---|---|---|
| GitHub (kod deposu) | 127 | 69 | 58 |
| Blog / makale sitesi | 73 | 41 | 32 |
| Akademik / akademik özet | 64 | 37 | 27 |
| Aracı kurum / fintech eğitim | 45 | 21 | 24 |
| TradingView | 41 | 21 | 20 |
| MQL5 | 21 | 9 | 12 |
| ProRealCode | 12 | 4 | 8 |
| Reddit (ayna) | 9 | 2 | 7 |
| Forum / topluluk | 8 | 6 | 2 |
| VisualChart | 7 | 3 | 4 |
| StockSharp dokümantasyonu | 6 | 1 | 5 |
| AmiBroker (marketcalls.in) | 2 | 1 | 1 |
| cTrader | 2 | 2 | 0 |

Kod 254 satırda açık (%60,9). Lisans dağılımı şöyle: lisanssız ya da lisans görülmeyen 269, Apache-2.0 44, MIT 30, GPL/AGPL/LGPL 26, MPL 2, TradingView açık kaynak (başlık doğrulanamadı) 38 ve diğer (FxCraft örnek EA lisansı, UNLICENSED, BSD tarzı, kodu kapalı davetli script) 8. Piyasa etiketleri (bir satır birden çok etiket taşıyabilir): hisse 147, endeks 120, kripto 69, genel 58, emtia 53, forex 50.

## En sık tekrar eden 10 kanonik aile

Sayımda DIGER_TREND (38) ve DIGER_MR (24) dışarıda bırakıldı, çünkü bunlar tek bir aile değil. "Kaynak" üç biçimde sayıldı: ana linklerdeki farklı alan adları, ek_kaynaklar alanındaki linkler eklendiğinde farklı alan adları ve farklı yazar/yayıncılar.

| # | Aile (alt_tur) | Ana aile | Satır | Alan adı (ana) | Alan adı (ek dahil) | Farklı yazar | Bölgeler |
|---|---|---|---|---|---|---|---|
| 1 | MA_CROSS | TREND | 44 | 27 | 28 | 39 | Küresel/İngilizce 15, Asya 14, Amerika 6, Afrika+Orta Doğu 6, Avrupa 3 |
| 2 | RSI_OB_OS | ORT. DÖNÜŞ | 40 | 21 | 21 | 34 | Küresel/İngilizce 14, Asya 12, Afrika+Orta Doğu 6, Avrupa 4, Amerika 4 |
| 3 | BB_REVERSION | ORT. DÖNÜŞ | 34 | 21 | 21 | 29 | Asya 14, Küresel/İngilizce 11, Avrupa 4, Afrika+Orta Doğu 3, Amerika 2 |
| 4 | SHORT_TERM_REVERSAL | ORT. DÖNÜŞ | 20 | 10 | 15 | 16 | Küresel/İngilizce 13, Amerika 3, Asya 2, Avrupa 2 |
| 5 | RSI2_MR | ORT. DÖNÜŞ | 19 | 12 | 14 | 19 | Küresel/İngilizce 7, Avrupa 5, Amerika 4, Afrika+Orta Doğu 2, Asya 1 |
| 6 | PAIRS_COINT | ORT. DÖNÜŞ | 19 | 10 | 13 | 16 | Asya 11, Küresel/İngilizce 6, Avrupa 2 |
| 7 | VOL_BREAKOUT | TREND | 19 | 6 | 8 | 12 | Asya 12, Küresel/İngilizce 6, Avrupa 1 |
| 8 | FIYAT_MA_FILTRE | TREND | 18 | 15 | 21 | 16 | Küresel/İngilizce 8, Avrupa 4, Asya 3, Afrika+Orta Doğu 2, Amerika 1 |
| 9 | MACD_TREND | TREND | 14 | 9 | 9 | 14 | Küresel/İngilizce 7, Amerika 4, Asya 2, Afrika+Orta Doğu 1 |
| 10 | ORB | TREND | 14 | 7 | 8 | 13 | Küresel/İngilizce 7, Asya 7 |

Bu sıralamayı okurken üç uyarı var. Birincisi, kümelerin çalışma kuralı her kümede aynı kanonik aileden en fazla 6 satır alınmasını öngörüyordu. Bu yüzden MA_CROSS, RSI_OB_OS ve BB_REVERSION'ın gerçek yaygınlığı muhtemelen daha yüksek; frekanslar kısmen bu tavanın ürünü. İkincisi, ilk üç aile çoğunlukla ders kitabı kuralı: 20/2 Bollinger, RSI(14) 30/70 ve klasik MA kesişimi farklı ülkelerin eğitim sayfalarında neredeyse aynı biçimde tekrar ediyor. Bunlar farklı piyasa, çıkış ya da stop kurallarıyla geldiği için ayrı satır olarak kaldı. Üçüncüsü, 11. sıradaki DONCHIAN_BREAKOUT (11 satır) ilk 10'a çok yakın. VOL_BREAKOUT'un 12 satırı Asya'dan geliyor (Çin'de Dual Thrust/R-Breaker, Kore'de 변동성 돌파).

## Bölgesel farklar

**Çin (vadeli CTA'nın baskın olduğu yer).** Açık kaynak Çince stratejiler büyük ölçüde üç kurumsal örnek kütüphanesinden geliyor: vn.py, TqSdk ve 掘金 myquant. Ağırlık emtia ve endeks vadelilerinde. "Seviye kırılımı" ailesi bölgenin imzası: Dual Thrust dört ayrı Çince kaynakta ([vn.py](https://github.com/vnpy/vnpy_ctastrategy/blob/main/vnpy_ctastrategy/strategies/dual_thrust_strategy.py), [wtpy](https://github.com/wondertrader/wtpy/blob/master/demos/Strategies/DualThrust.py)), R-Breaker üç kaynakta ([BigQuant](https://bigquant.com/wiki/doc/W7L8gBllSH)) var. Yanlarında Hans123, 空中花园 ve 菲阿里四价 gibi seans sonu zorunlu kapanışlı ORB'ler bulunuyor. Ortalamaya dönüş tarafında sanayi zinciri spread arbitrajı (跨品种套利: rb/hc, cu/al, j/jm) Çin'e özgü. A-hisse örnekleri ise T+1 kısıtı nedeniyle yalnız long ve günlük çalışıyor ([qteasy](https://github.com/shepherdpp/qteasy/blob/master/docs/source/examples/Example_09_%E6%97%A5%E5%86%85%E5%9B%9E%E8%BD%AC%E4%BA%A4%E6%98%93.md)).

**Japonya ve Kore (iki ayrı imza).** Japonya'da en zengin ücretsiz kaynak aracı kurum eğitimi, yani OANDA証券「30の戦略」 ([örnek](https://www.oanda.jp/lab-education/blog_30strategy/jp225_bollinger_bands/)). Burada 順張り ve 逆張り (BB −2σ, RSI, 乖離率) yan yana duruyor. Japonya'da MR payı %44,0 (25 satırın 11'i); dolayısıyla "Japonya = 逆張り" hipotezi bu örneklemde sayıca doğrulanmıyor. Kore'de tek bir aile açıkça baskın: Upbit kriptoda Larry Williams volatilite kırılımı (변동성 돌파). Bu ailenin 5 Korece satırının 5'i kripto ve 09:00 KST'de sıfırlanan günlük döngüyle çalışıyor ([Tistory](https://poalim.tistory.com/30)). Japonya'da bu aile hiç çıkmadı. Kore ŞÜPHELİ bayraklarında da öne çıkıyor; Kore 6, Japonya 1 bayrak alıyor ve bunların çoğu uygulama ya da hizmet tanıtımından kaynaklanıyor.

**Hindistan, Türkiye ve Güneydoğu Asya.** Hindistan'da içerik Nifty/BankNifty endeks türevlerinde gün içi ORB ve Supertrend üzerinde toplanıyor. Zaman filtreleri (09:15 açılış, 14:30–15:15 kesim) ve STT gibi maliyetlerin açıkça modellenmesi bölgenin özelliği ([mistrymah](https://github.com/mistrymah/nifty-pairs-trading-futures/blob/main/README.md)). Zerodha Varsity'nin Trading Systems modülünün 16 bölümünden 13'ü pairs trading'e ayrılmış ([Varsity](https://zerodha.com/varsity/module/trading-systems/)). Türkiye'de Anıl Özekşi'nin OTT/MOST ailesi ([ROTT](https://github.com/zentoliyan/Pinescript-Indicator-ROTT-RelativeOTT/blob/main/Source-Code)) ve BIST/VİOP backtest araçları öne çıkıyor. Güneydoğu Asya'da kural içeriği aracı kurum blogları ve üniversite dergilerindeki MA/RSI testleriyle sınırlı; açık kod çok az. Asya'nın tamamında en sık alt türler DIGER_TREND 15, MA_CROSS 14, BB_REVERSION 14, VOL_BREAKOUT 12; piyasalar hisse 62, endeks 41, emtia 25, kripto 18.

**Rusya ve Kıta Avrupası.** Rusça kaynaklarda (smart-lab, habr, StockSharp RU) MOEX hisse ve vadelileri, Python testleri, Larry Williams kökenli kısa vade testleri ve pairs/stat-arb öne çıkıyor. En çok ilgiyi olumsuz sonucu da raporlayan veri odaklı test yazıları görüyor ([smart-lab](https://smart-lab.ru/blog/603603.php)). Fransız ve İtalyan topluluğu ProRealCode'da ProBuilder ile DAX/CAC üzerinde RSI(2) ve Bollinger dönüşü paylaşıyor ([RSI 2P](https://www.prorealcode.com/prorealtime-trading-strategies/rsi-2p-larry-connors/?pnum=2)). İspanyolca katkı ağırlıkla dur-ve-dön mantıklı VisualChart kataloğundan geliyor. Avrupa, MR payı en yüksek bölge: 44 satırın 25'i. En sık alt türler DIGER_TREND 6, DIGER_MR 5, RSI2_MR 5, FIYAT_MA_FILTRE 4.

**Latin Amerika.** Brezilya'nın kendine özgü bir "setup kültürü" var: IFR2, 9.1–9.4, PFR, 123 ve 2HL. Bunların çoğu Stormer (Alexandre Wolwacz) adıyla anılıyor ([TradingView stormer](https://www.tradingview.com:443/scripts/stormer/)) ve B3/WIN/WDO'ya uyarlanıyor. Üniversite tezleri bu kuralları açık parametreyle test ediyor ve sonuçlar çoğu zaman al-tut'un gerisinde kalıyor: IFR2 33 Ibovespa hissesinde CAGR %12,59 iddiası ile al-tut'un hafif altında ([UNIPAMPA](https://repositorio.unipampa.edu.br/server/api/core/bitstreams/40d98aa1-eb87-4de2-80a9-1a3c334342f0/content)). İspanyolca LatAm'da isimli bir yerel setup kültürü bulunamadı; içerik akademik ya da broker eğitimi.

**Afrika ve Orta Doğu.** Güney Afrika'da JSE üzerinde akademik testler var. Bunlar maliyet sonrası zayıf sonuç veriyor: VMA kuralları maliyet öncesi %6,7, sonrası %2,0 fazla getiri iddia ediyor ve sonuç anlamsız ([WCE 2011](https://www.iaeng.org/publication/WCE2011/WCE2011_pp384-390.pdf)). Mısır'dan EGX için Python araç takımları ([egx-desk](https://github.com/CodeNKoffee/egx-desk/blob/main/README.md)), İran'dan Nobitex/Wallex kripto botları ([Pouryazv](https://github.com/Pouryazv/nobitex-moving-average-trader)) geliyor. Körfez kaynakları stopsuz, öznel Arapça TradingView fikirleri; Nijerya'dan yalnız bir golden cross blogu var. Bölgede en sık alt türler MA_CROSS 6, RSI_OB_OS 6, BB_REVERSION 3, FIYAT_MA_FILTRE 2.

**Küresel/İngilizce.** Bu grupta üç ayrı ekosistem var. Birincisi ABD ETF/endekslerinde günlük kısa vadeli dip alımı (RSI(2–5), IBS, N-gün dip, Turnaround Tuesday). İkincisi forex forumlarında (BabyPips, FF ağı) sabit pip SL/TP'li EMA kesişimleri. Üçüncüsü Freqtrade'in kripto MR scalp'leri: 1–5 dakikalık, dar ROI hedefli ve geniş sabit stoplu. En sık alt türler MA_CROSS 15, RSI_OB_OS 14, DIGER_MR 13, SHORT_TERM_REVERSAL 13.

## En güçlü kanıtı olan 15 strateji

Seçim ölçütleri uzun örneklem, çoklu piyasa, açık kural ve mümkünse yayın sonrası OOS ya da bağımsız replikasyon. Uzun canlı kayıtlı satır bulunamadı. Listedeki iki canlı kayıt iddiası ([S0332](https://prorealcode.com/prorealtime-trading-strategies/code-mark-larsen-bollinger-strategy/?pnum=5), [S0338](https://www.prorealcode.com/prorealtime-trading-strategies/larry-connors-style-slightly-adjusted-dax-daily-time-frame-)) anekdot ya da kısa demo hesap düzeyinde kaldığı için alınmadı. Tablodaki bütün rakamlar kaynakta yazan **iddialardır**; bu çalışmada doğrulanmadı.

| # | Satır | Strateji | Neden güçlü | Replikasyon / bozulma uyarısı |
|---|---|---|---|---|
| 1 | [S0142](https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf) | A Century of Evidence on Trend-Following Investing (TSMOM) | 1880–2013, çok varlıklı vadeliler; 1-3-12 ay TSMOM; 2/20 ücret sonrası net Sharpe 0,77 iddiası | Hipotetik; 1880'lerde uygulanamaz; erken dönem maliyetleri varsayımsal |
| 2 | [S0143](https://quantpedia.com/strategies/time-series-momentum-effect) | Time Series Momentum (Time Series Momentum Effect) (TSMOM) | 58 vadeli enstrüman, 1965–2009; 12 ay işaret kuralı; Sharpe 1,31 iddiası; SSRN özeti 21.670 indirme gösteriyor | Kim-Tse-Wald: 2009–2013'te üstünlük kayboluyor, alfa büyük ölçüde oynaklık ölçeklemesinden |
| 3 | [S0144](https://research-api.cbs.dk/ws/files/60084063/lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf) | Which Trend Is Your Friend? (MACROSS) (MA_CROSS) | 1985–2015; EMA kesişimi ile TSMOM'un matematiksel eşdeğerliğini kanıtlıyor; Sharpe 1,0–1,45 (maliyet öncesi) | Kesişim sinyalleri TSMOM'a ek alfa katmıyor; parametre seçiminden çok ufuk önemli |
| 4 | [S0145](https://arxiv.org/pdf/1404.3274) | Two centuries of trend following (FIYAT_MA_FILTRE) | ~1800–2013 iki yüzyıl; 5 aylık EMA sinyali; t=10,5 iddiası | Maliyetsiz kurgusal P&L; resmi OOS yok; kısa vadeli trendlerin ~1990'dan beri zayıfladığı not ediliyor |
| 5 | [S0141](https://quantpedia.com/strategies/asset-class-trend-following) | A Quantitative Approach to Tactical Asset Allocation (Asset Class Tren (FIYAT_MA_FILTRE) | Faber 10 aylık SMA, 5 varlık sınıfı; ayrıca Alpha Architect replikasyonu (birleştirilen satır) ve Hernæs (2014) OOS testi | Hernæs: 1935 ve 1975 sonrası alt dönemlerde iyileşme anlamsız; optimal MA uzunluğu zamanla değişiyor |
| 6 | [S0146](https://gnanaganga.inflibnet.ac.in:8443/jspui/bitstream/123456789/14295/1/Risk%20Premia%20Harvesting%20through%20Dual%20Momentum.pdf) | Risk Premia Harvesting Through Dual Momentum (DUAL_MOMENTUM) | 1974–2011, 4 modül; göreli + mutlak momentum; kompozit Sharpe 1,07, MDD −%10,9 iddiası | Maliyet yok; tamamen örneklem içi |
| 7 | [S0147](https://www.cis.upenn.edu/~mkearns/finread/trend.pdf) | Does Trend Following Work on Stocks? (DIGER_TREND) | 1983–2004, geniş ABD hisse evreni; tüm zamanların zirvesi + 10 ATR iz süren stop; 2025 güncellemesi 1950–2024'e uzatıyor | Hakemsiz şirket beyaz kitabı; kârın çoğu işlemlerin <%7'sinden; küçük hesaplarda maliyet sorunu |
| 8 | [S0157](https://c.mql5.com/forextsd/forum/214/Market%20Timing%20with%20Moving%20Averages%20-%20Anatomy%20and%20Performance%20of%20Trading%20Rules.pdf) | Market Timing with Moving Averages: Anatomy and Performance of Trading (FIYAT_MA_FILTRE) | 155 yıllık veride genişleyen pencereli gerçek OOS; MA zamanlamasının en dürüst testi | Sonuç zayıf: OOS'ta S&P için +0,12–0,15 SR, DJIA'da anlamsız; yazar kârlılığın 'fazlasıyla abartıldığını' söylüyor |
| 9 | [S0149](https://academicweb.nd.edu/~zda/intramom.pdf) | Hedging demand and market intraday momentum (DIGER_TREND) | 1974–2020 hisse vadelileri; gün içi momentum; Sharpe 1,73, OOS R² %2,88 iddiası | Ana sonuçlar maliyetsiz; rONFH varyantında OOS R² negatif |
| 10 | [S0158](https://quantpedia.com/strategies/pairs-trading-with-stocks) | Pairs Trading: Performance of a Relative-Value Arbitrage Rule (Pairs T (PAIRS_COINT) | GGR mesafe yöntemi; 1962–2002 ve yayın sonrası 1999–2002 OOS'ta yıllık %10,4 iddiası | Do & Faff: kârlılık düşüş eğiliminde, yalnız türbülans dönemlerinde güçlü |
| 11 | [S0161](https://math.nyu.edu/~avellane/AvellanedaLeeStatArb071008.pdf) | Statistical Arbitrage in the U.S. Equities Market (ZSCORE_MR) | Avellaneda-Lee s-skor stat-arb; 1997–2007; PCA Sharpe ~1,44 iddiası | Makale içinde bozulma: 2003–2007'de Sharpe ~0,9; gerçek ETF stratejisi ~0,6 |
| 12 | [S0159](https://www.nber.org/papers/w2533.pdf) | Fads, Martingales, and Market Efficiency (SHORT_TERM_REVERSAL) | Lehmann haftalık ters dönüş; 1962–1986; haftaların ~%90'ında pozitif | Maliyete çok duyarlı: tek yön ~%0,40 maliyette kâr sıfıra iniyor |
| 13 | [S0160](https://www.nber.org/system/files/working_papers/w2977/w2977.pdf) | When Are Contrarian Profits Due to Stock Market Overreaction? (SHORT_TERM_REVERSAL) | Lo-MacKinlay; 1.330 hafta; kârın kaynağını (aşırı tepki ve öncü-gecikmeli ilişki) ayrıştırıyor | Kârın yalnız bir kısmı aşırı tepkiden; maliyet yok |
| 14 | [S0156](https://quantpedia.com/strategies/momentum-effect-in-commodities) | Momentum in Commodity Futures Markets (Momentum Effect in Commodities) (XS_MOMENTUM) | Emtia vadelilerinde 12 ay kesitsel momentum; 1979–2004; Sharpe 0,57 | MDD −%79,75; Quantpedia sayfasında enstrüman sayısı tutarsız |
| 15 | [S0154](https://quantpedia.com/Screener/Details/88) | Industry Information and the 52-Week High Effect (52-Weeks High Effect (52W_HIGH) | Sektör düzeyinde 52 hafta zirvesi; 1963–2009; yıllık ~%11,75 iddiası | Maliyet yok; Quantpedia OOS testi hafif negatif; MDD 'not stated' |

Akademik kümenin dışında, dürüst ve sistematik test içeren satırlar şunlar: [S0278](https://github.com/abhinavgudipati/nifty-supertrend-research/blob/main/supertrend-backtest/backtest.py) (survivorship'siz Nifty 50 testi, al-tut'u geçemiyor), [S0140](https://articles.stockcharts.com/article/articles-arthurhill-2018-02-in-sample-and-out-of-sample-results-for-two-momentum-systems---measuring-performance-and-drawdowns/) (OOS'ta yıllık %9,76'ya karşı backtest %16,72) ve [S0151](https://papers.ssrn.com/abstract=4416622) (ORB; bağımsız MQL5 replikasyonunda maliyet sonrası ~0R). Ortak örüntü açık: OOS ya da replikasyon yapılan her yerde rakamlar küçülüyor. Kripto pairs makaleleri çok yüksek Sharpe bildiriyor ([S0166](https://ar5iv.labs.arxiv.org/html/2109.10662)'da 6,96–20,38) ama kısa örneklem ve maker komisyon iadesine bağımlılık nedeniyle listeye alınmadı.

## Bayrak istatistikleri

417 satırın 65'i en az bir bayrak taşıyor: **YASAK_TİP 13**, **ŞÜPHELİ 32**, **LOOKAHEAD_RİSKİ 26**. Bir satır birden çok bayrak taşıyabilir. Bölgelere göre: YASAK_TİP: Küresel/İngilizce 5, Asya 5, Avrupa 2, Amerika 1; ŞÜPHELİ: Asya 13, Küresel/İngilizce 7, Avrupa 6, Amerika 4, Afrika+Orta Doğu 2; LOOKAHEAD_RİSKİ: Asya 15, Küresel/İngilizce 7, Afrika+Orta Doğu 2, Avrupa 1, Amerika 1. Nedenler aşağıda satırların notlarından elle sınıflandırıldı; bir satır birden çok nedene girebilir.

**YASAK_TİP:** stopsuz ya da lot çarpanlı ızgara (MQL5 ızgara EA'ları, TqSdk/qteasy 网格, nautilus grid_mm) — 6 satır (S0050, S0065, S0066, S0072, S0206, S0207); DCA, ortalama düşürme ya da zararda pozisyon büyütme — 6 satır (S0214, S0279, S0282, S0318, S0329, S0372); koşulsuz ek giriş ve fiilen stopsuz — 1 satır (S0026).

**ŞÜPHELİ:** kural ile kod (ya da metin ile sürüm notu) uyuşmazlığı — 17 satır (S0004, S0063, S0086, S0118, S0185, S0203, …); ücretli kurs, bot, abonelik, affiliate ya da sinyal uygulaması tanıtımı — 12 satır (S0082, S0089, S0113, S0117, S0118, S0256, …); metodolojisiz, olağandışı ya da "%100" başarı iddiası — 7 satır (S0089, S0260, S0261, S0286, S0309, S0368, …).

**LOOKAHEAD_RİSKİ:** kapanmamış mum, anlık fiyat ya da aynı kapanışta sinyal ve işlem (TqSdk yarım bar, cheat-on-close dahil) — 16 satır (S0046, S0101, S0110, S0162, S0181, S0182, …); teyitsiz pivot, fraktal, uyumsuzluk ya da öznel formasyon — 5 satır (S0058, S0324, S0368, S0402, S0403); örneklem içi eşik, tüm örneklemle tahmin ya da merkezlenmiş MA — 3 satır (S0102, S0196, S0220); üst zaman dilimi verisi (lookahead ayarı doğrulanamadı) — 1 satır (S0084); geleceği bilmeyi gerektiren çıkış kuralı — 1 satır (S0307).

Bayrak "yok" bir güvence değil. TradingView satırlarının çoğunda Pine kodu okunamadığı için bayrak yalnız açıklama metnine dayanıyor; bu durumda "yok", "risk tespit edilmedi" anlamına geliyor. Ayrıca 206 satırda (%49,4) kaynakta hiç stop kuralı yok: 108'i MR, 98'i TREND. Stopsuz MR kuralları YASAK_TİP sayılmadı (ızgara ya da ekleme olmadığı sürece), ama projede kullanılacaksa zaman stopu ya da felaket stopu eklenmesi gerekir.

## Taramada eksik kalan bölge, dil ve platform

Eksiklerin başlıca nedeni ortak arama bütçesi oldu. Tüm ajanların paylaştığı 200 WebSearch çağrısı iş ortasında tükendi ve A2–A10 kümelerinin hepsi planlanan aramaların bir kısmını yapamadığını bildirdi. İkinci neden teknik engeller. Bash/curl ile tüm dış alan adlarına proxy CONNECT 403 döndü. github.com HTML/API sayfaları 403 verdi ya da WebFetch izin listesinde değildi; bu yüzden yıldız sayıları alınamadı, A6 (Kore pyupbit) ve A9 (Brezilya NTSL/IFR2) depoları hiç okunamadı. reddit.com izin listesinde değildi ve redlib aynaları kullanıldı. ForexFactory client_error verdi, yerine metalsmine aynası kullanıldı. quantifiedstrategies bot doğrulamasına takıldı ve substack kopyaları ücretliydi. Çin'de zhihu, xueqiu (雪球), joinquant (聚宽), myquant.cn ve gitee'ye curl reddedildi ve aramada bu sitelerin strateji sayfası çıkmadı; juejin JS sınamasına, 51cto bot kontrolüne takıldı. Kore'de Naver Cafe giriş istediği için denenmedi, wikidocs client_error verdi ve brunch sayfası kısıtlıydı. İran eğitim siteleri (Mofid, Charisma, Tabdeal, maktabkhooneh, khanesarmaye) robots.txt ile WebFetch'e kapalıydı, mql5.com/ar izin listesinde değildi. Şili tezleri Anubis JS doğrulamasına takıldı. TradingView'in kaynak kodu sekmesi de WebFetch çıktısına gelmedi.

Bu nedenlerle satır üretilemeyen yerler şunlar. Bölge olarak **Kanada, Arjantin, Şili, Peru, Filipinler, Kenya, Gana** ve İsrail'den (tek aday sayfa açılmadı) hiç satır yok. **İtalya, Polonya, Hollanda ve İskandinavya** için yerel dilde satır yok; İtalyan katkısı yalnız ProRealCode'daki İngilizce bir satırla sınırlı. Endonezya 1, Tayland 2, Mısır'ın Arapça kaynakları 0. Platform olarak **NinjaTrader, MetaStock, forum.amibroker, futures.io**, GitLab/Codeberg/Gitee, topluluk Freqtrade depoları (NFI vb.), Quant Stack Exchange, X, YouTube, Telegram/Discord arşivleri, Wilmott, Quantocracy, 5ch, note.com (kurallı ücretsiz bot yazısı bulunamadı), Streak/Sensibull/Tradetron ve hisse.net/borsagundem forumları taranamadı. Bölgesel olarak çok popüler ama parametreleri doğrulanamayan kurallar da var: Tayland'ın CDC Action Zone'u, Türkiye'nin özgün Matriks MOST/OTT formülleri ve Hindistan'ın Streak şablonları. Bir sonraki turda bunlar öncelikli olmalı.

## Yöntem ve dürüstlük notları

**Birleştirme:** Yalnız aynı kural, aynı çekirdek parametre, aynı piyasa sınıfı ve aynı zaman dilimi taşıyan satırlar birleştirildi. Bu ölçütle **2 birleştirme** yapıldı. Faber 10 aylık SMA/Ivy 5 satırında A3-041, [S0141](https://quantpedia.com/strategies/asset-class-trend-following)'e eklendi; Turtle Sistem 1 (20/10, 2N) satırında A6-034, [S0076](https://www.tradingview.com/script/gbxblhGl/?amp)'ya eklendi. Diğer bariz adaylar farklı parametre, piyasa ya da çıkış kuralı taşıdığı için ayrı tutuldu: Connors RSI(2) varyantları (S&P günlük, DAX, Kore hisse, kripto), Dual Thrust (Jesse kripto 0,71/0,67, TqSdk emtia 0,2/0,2, Lean SPY 0,63), Jesse "IFR2" (Ichimoku filtreli kripto) ile Brezilya IFR2'leri (eşik 20/25, farklı çıkışlar) ve Turtle'ın 55/20 ve 1 dakikalık varyantları. Kaynaklar aynı stratejinin başka uygulamalarını zaten ek_kaynaklar alanına yazmıştı (ör. Dual Thrust için vn.py ve wtpy, R-Breaker için BigQuant ve myquant).

**Link benzersizliği:** Satırlar 386 farklı link kullanıyor. Aynı sayfa ya da PDF'te birden çok farklı stratejinin bulunduğu 19 grupta (ör. VisualChart kataloğunda 7 sistem, Icesi tezinde 4 kural) link ortak kaldı. Link uydurmamak için bu satırların notlarına "aynı kaynakta birden fazla farklı strateji" işareti kondu.

**Okuma yöntemindeki sapmalar:** A1, A5, A7 ve A10'daki GitHub satırları (126 satır) WebFetch yerine `git clone --depth 1` ile indirilip yerelde okundu. Kurallar README'den değil koddan çıkarıldı ve bu durum her satırın notlarına yazıldı. 41 TradingView satırında Pine sürümü, varsayılan girdiler ve MPL-2.0 başlığı doğrulanamadı; kurallar sayfa açıklamasından alındı (A2 bunu açıkça bildirdi, A7/A9/A10'da da aynı durum var). VisualChart satırlarında (A8-038…044) varsayılan parametre değeri yok; bu satırlar kayıt amaçlı tutuldu ve notlarda işaretlendi. A2 ve A8 alıntıları WebFetch'in model özetinden geldiği için noktalama farkı olabilir. Piyasa alanı enum'a indirildi ve ayrıntı (ör. "endeks (SPY)") 21 satırda notlara taşındı.

**Popülerlik ve performans:** Popülerlik 288 satırda bilinmiyor. TradingView sayaçları etiketsiz geldi ve "muhtemel beğeni/boost" olarak kaydedildi. Reddit sayıları aynalardan okundu. Performans alanındaki her değer kaynağın kendi iddiası; 220 satırda performans hiç verilmemiş. Akademik iddiaların çoğu maliyetsiz ya da yalnız komisyonlu, ve bazı Quantpedia MDD değerleri kaynakta "not stated" olarak işaretli. Hiçbir rakam bu çalışmada yeniden üretilmedi. Kümeler içi denetim düzensizdi: A5 10 satırı kaynak koduyla yeniden karşılaştırdı ve parametre farklarını düzeltti; A7 rastgele denetim yapmadığını açıkça bildirdi.

## Bağımsız denetim

Denetim 2026-11-12'de, listeyi üreten kümelerden bağımsız olarak yapıldı. Sonuç: örneklemdeki 38 satırın 38'inin kaynağı açıldı, **uydurma link ya da uydurma kural bulunmadı**, 36 satır değişmeden geçti, 2 satırda küçük düzeltme yapıldı, silinen satır yok.

**Örneklem.** Python `random.Random(20261112)` (tohum **20261112**; betik: `/home/claude/audit/sample.py`). Tekrarsız katmanlı çekim, sırasıyla: 10 tamamen rastgele satır + her kümeden (A1…A10) 2'şer satır (20) + kanit_turu "akademik makale" ya da "canlı kayıt iddiası" olanlardan 5 + bayraklı satırlardan 3 = **38 satır** (417 satırın %9,1'i). Kümelere düşen satır: A1 2, A2 3, A3 5, A4 4, A5 4, A6 3, A7 3, A8 4, A9 4, A10 6.

**Yöntem.** GitHub dışındaki 32 link WebFetch ile açıldı. GitHub'daki 6 satır için 6 depo `git clone --depth 1` ile ayrı boş klasörlere indirildi ve ilgili dosya yerelde okundu (kod çalıştırılmadı). S0196'nın bayrak gerekçesi için ek kaynaktaki QuantsPlaybook RSRS klasörü de seyrek klonla okundu.

**Ölçütler.** (a) link açılıyor, (b) strateji o sayfada, (c) giriş/çıkış/stop kaynağa uyuyor, (d) parametreler doğru, (e) performans "iddia" olarak ve doğru rakamla aktarılmış, (f) lisans/popülerlik doğru, (g) bayrak eksik ya da fazla değil.

| id | orijinal_id | Katman | Sonuç | Gerekçe |
|---|---|---|---|---|
| S0108 | A3-012 | rastgele | GEÇTİ | RSI(2)<5, 200 MA filtresi, 5 MA çıkışı, 1990–2024, kısa-only %0,67 sayfada. Yazar adı aynada görünmüyor; satır zaten "muhtemel" diyor. |
| S0405 | A10-018 | rastgele | DÜZELTİLDİ | Kurallar (EMA200, RSI(2) 10/5 ve 90/95, SMA5 çıkışı, sinyal mumu stopu) doğru. Not "kopya işlem ve bot ürünlerine yönlendiriyor" diyordu; bunlar yalnız site menüsünde, yazı gövdesinde hesap açma/bonus çağrısı var. Not daraltıldı, ŞÜPHELİ bayrağı (sınırda) korundu. |
| S0259 | A6-042 | rastgele | GEÇTİ | 1σ üst bant kırılımı + RSI≤70, 3,4σ kâr al, RSI≥71 / 1σ alt bant çıkışı, ~%800 iddiası ve yazarın çekinceleri sayfada. |
| S0106 | A3-010 | rastgele | GEÇTİ | 50/200 SMA filtresi, RSI 30 yukarı kesişi, Chandelier (22,1), min. 5 gün; 463 işlem, %8,68, PF 5,04 birebir. RSI periyodunun yazıda olmadığı doğru not edilmiş. |
| S0196 | A5-025 | rastgele | GEÇTİ | N=18 (2022'de 15), M=600, 1,0/0,8 ve ±0,7; net değer 11,21 (44 işlem) ve 9,79 sayfada. Eşiklerin tüm örneklem ortalama±std'sinden seçildiği ana sayfada değil ek kaynakta (QuantsPlaybook) yazıyor; orada doğrulandı, bayrak yerinde. |
| S0376 | A9-024 | rastgele | GEÇTİ | Son 2 mumun dibinden al, tepesinden sat, ~7 bar zaman çıkışı, stop yok. 146 sayacı etiketsiz. |
| S0128 | A3-032 | rastgele | GEÇTİ | 10/40 hafta EMA, yalnız long, $SPXTR, 25 yılda 9 sinyal, ~%10/yıl, maruziyet %77–80. |
| S0310 | A8-002 | rastgele | GEÇTİ | PMA 50 hafta / 50 gün / 10 gün, %10 başlangıç stopu, ATR iz süren; SPBE +%249,14 ve NVTK −%5,56, tarih tutarsızlığı notu doğru. |
| S0060 | A2-010 | rastgele | GEÇTİ | İki modül, EMA 9/21/50, SL 1,5×ATR, TP 2×ATR; Keltner ayarlarının belirtilmediği doğru. Pine kodu görülemedi. |
| S0390 | A10-003 | rastgele | GEÇTİ | main.py: EMA20/50 + RSI(14) 50, exclusive_orders, komisyon 0,0002, EURUSD 2020–2024; LICENSE yok. Yıldız sayısı doğrulanamadı. |
| S0016 | A1-016 | küme A1 | GEÇTİ | SMA5≥SMA200, RSI < (8× örneklenmiş RSI − 20); çıkış, ROI %1, SL −%5, 5m, GPL-3.0 koda uyuyor. |
| S0028 | A1-028 | küme A1 | GEÇTİ | Alım 4/8, 7/9, 1/8; satış 1/16, 3/18, 6/18; ROI tablosu, SL −%26,5, trailing %5 / %14,4; 1h. |
| S0074 | A2-024 | küme A2 | GEÇTİ | Pazartesi düşük kapanış, IBS≤0,25, kapanış<SMA180, Çarşamba kapanış çıkışı, %10 stop, 0,10 lot, 1.390 görüntülenme. |
| S0063 | A2-013 | küme A2 | GEÇTİ | %4–20 boşluk, ilk 12 bar, Stokastik 5,3,3, 3 bar tetik, 0,5×ATR(14) stop, filtreler; "fade" / "continuation" etiket çelişkisi sayfada var, ŞÜPHELİ gerekçesi doğru. |
| S0130 | A3-034 | küme A3 | GEÇTİ | 26 hafta ROC, ilk 5 al / ilk 7 dışı sat, PPO(10,40,1) filtresi; DD %19,42'ye karşı %47,41, isabet %61, 125 sinyal; PPO sistemi %6,97 / %14,01. |
| S0134 | A3-038 | küme A3 | GEÇTİ | Kijun 52, RSI 26/50, 4s+1s, SL 40, TP 120, iz süren 60, 40 pipte başabaş; EUR/USD. |
| S0147 | A4-007 | küme A4 | GEÇTİ | Tüm zamanların en yüksek kapanışı, 10 ATR iz süren stop, 15$ ve hacim filtreleri; %15,2, %49,3, 2,56, 305 gün, %19,3'e karşı %12,0. Hakemsiz olduğu doğru işaretlenmiş. |
| S0171 | A4-031 | küme A4 | GEÇTİ | 22 ETF, 120/20 gün, 0,5σ, 5 çift; ~%20,6, Sharpe 1,66; güven "Weak", OOS negatif. |
| S0186 | A5-015 | küme A5 | DÜZELTİLDİ | Giriş/çıkış koda uyuyor. Hata: satır %6,8 sabit zarar stopunu etkin gösteriyordu; yapılandırmada `is_fixation_stop=0`, yani varsayılanda yalnız iz süren kâr al açık. Ayrıca "2000 adet" havuz büyüklüğü değil emir büyüklüğü. stop_kurali, parametreler ve giriş açıklaması düzeltildi. |
| S0204 | A5-033 | küme A5 | GEÇTİ | 30 gün, z ±2 giriş, \|z\|<0,5 çıkış, ±3 stop, 10:22 oranı, 50 lot; Apache-2.0. |
| S0246 | A6-028 | küme A6 | GEÇTİ | SPY/EFA 12 ay, 8 güvenli varlık 6 ay, ilk 3, BIL; metin "≤0" / kod "BIL getirisi" uyuşmazlığı gerçek, ŞÜPHELİ gerekçesi doğru. |
| S0220 | A6-002 | küme A6 | GEÇTİ | seasonal_decompose freq=25 toplamsal, ~%2–3 sapma, backtest yok; uçlardan 12 nokta kesiliyor, merkezlenmiş filtre → LOOKAHEAD_RİSKİ yerinde. |
| S0299 | A7-034 | küme A7 | GEÇTİ | Yatay bantta alt banttan al, hedef üst bant, BB(20,2), VCB örneği, stop yok. |
| S0285 | A7-020 | küme A7 | GEÇTİ | EMA 25/68, 4 bar teyit, EMA160 filtresi, 17:45 kapanışı, %0,021 efektif maliyet, XU030D1! 15 dk. |
| S0315 | A8-007 | küme A8 | GEÇTİ | Period 20, giriş 2, çıkış 0,5, Beta 1, stop %2, 5 dk; ~%103 yıllık iddiası; metin/parametre çıkış farkı doğru not edilmiş. |
| S0343 | A8-035 | küme A8 | GEÇTİ | SMA200 filtresi, SMA50 geri çekilme ya da tepe kırılımı, son yükselen dibin altı stop, %1 kuralı, isabet %35–45 genel ifadesi. |
| S0368 | A9-016 | küme A9 | GEÇTİ | Tepe kırılımı, 3× hedef, dip altı çıkış; 95.008,84 R$ / 111.238,18 R$ / %50; iç tutarsızlık gerçek, iki bayrak da savunulabilir. |
| S0360 | A9-008 | küme A9 | GEÇTİ | EMA 10/30 + EMA200, 400/800 puan, seans sonu; −%1,9…−%3,5, Sharpe −0,7…−2,5, PF 0,67–0,74, isabet %33–38. Tezde test penceresi tutarsız; satır 2024–2025 yazıyor. |
| S0399 | A10-012 | küme A10 | GEÇTİ | 11 ay (son ay hariç), 4 sektör, en iyi 1, aylık; %15,78'e karşı %11,93, Sharpe 0,63'e karşı 0,72. Yıldız sayısı doğrulanamadı. |
| S0413 | A10-026 | küme A10 | GEÇTİ | RSI(14)<30 ve SMA9>SMA21 al; RSI>70 ve SMA9<SMA21 sat; açıklama Malayca. |
| S0396 | A10-009 | akademik/canlı | GEÇTİ | TRB (1,50/150/200; bant 0/0,01), maliyet %0,956, 1988-04–2007-04 ALSI; TRB sonuçlarının Part 3'e bırakıldığı doğru. |
| S0415 | A10-028 | akademik/canlı | GEÇTİ | SAVI RSI(2)>90 al, Top 40 RSI(2)>65 sat; %116'ya karşı %104, maliyet sonrası geride. PDF'in ilk 100.000 / 166.596 karakteri okundu. |
| S0332 | A8-024 | akademik/canlı | GEÇTİ | Bollinger(10), 14 periyot ortalamada limit çıkış, stop yok, EUR/USD M15, 156 indirme, 5 yorum; yazarın gerçek parayla kaybı ve yorumcu %90 anekdotu. |
| S0142 | A4-002 | akademik/canlı | GEÇTİ | 1-3-12 ay, %10 oynaklık hedefi, 67 piyasa; %14,9 / %11,2 / %9,7 / 0,77 / −%26,3 / 8'de 10; 12'ye karşı 10 döviz tutarsızlığı doğru. |
| S0148 | A4-008 | akademik/canlı | GEÇTİ | 10 gün SMA, oynaklık ondalıkları, ertesi gün açılış, T-bill, 25 bp, 7,4–10,5 gün, 1963–2009. Yayın yılı (JFQA 2013) ana sayfada yok, ek kaynaktan. |
| S0279 | A7-014 | bayraklı | GEÇTİ | Supertrend (10,3) endekste, ₹10.000 dilim, ≥%1 kârda çıkış yoksa taşı; README "süresiz ortalama" diyor → YASAK_TİP yerinde. Yıldız sayısı doğrulanamadı. |
| S0182 | A5-011 | bayraklı | GEÇTİ | Aroon 10, 75/25, %1,2 stop, 30 lot, au2306; sinyal yeni açılan barla hesaplanıyor → LOOKAHEAD_RİSKİ yerinde. |
| S0372 | A9-020 | bayraklı | GEÇTİ | IFR2 5/25 giriş, 70/75 çıkış, IFR2 daha düşerse ekleme, Ouro/Prata planları; iki bayrak da yerinde. |

**Hata oranı.** GEÇTİ 36, DÜZELTİLDİ 2, SİLİNDİ 0, ERİŞİLEMEDİ 0. Düzeltme gerektiren satır oranı 2/38 = **%5,3**; kuralı ya da parametreyi etkileyen hata 1/38 = %2,6 (S0186), uydurma link/kural 0/38. Oran %10 eşiğinin altında kaldığı ve hiçbir kümede uydurma çıkmadığı için örneklem genişletilmedi. 38 satırlık örneklemde sıfır uydurma, listenin tamamında uydurma olmadığını göstermez; yaklaşık %95 güvenle uydurma oranının %8'in altında olduğunu söyler. Düzeltmeler `/home/claude/work/audit_fixes.py` ile uygulandı (build.py yeniden çalıştırılırsa bu betik de çalıştırılmalı). Düzeltmelerden sonra `validate.py` yeniden çalıştırıldı: 417 satır, 23 alan, 0 hata. Düzeltmeler sayılan hiçbir alanı değiştirmediği için bu rapordaki istatistikler aynı kaldı (`stats.py` ile yeniden hesaplanıp karşılaştırıldı).

**Küme bazında güvenilirlik.** Örneklem küme başına 2–6 satır olduğu için aşağıdakiler kesin hüküm değil, gösterge.
- **A1 (kod depoları), A5 (Çin):** kurallar doğrudan koddan çıkarılmış ve parametreler birebir tutuyor. Tek hata A5'te, kod yerine yapılandırma dosyasındaki varsayılan anahtarın kaçırılmasından (S0186). Benzer "çerçeve stopu" içeren diğer myquant satırlarında aynı hata olabilir.
- **A3 (İngilizce forum/blog), A4 (akademik):** 9 satırın 9'u geçti; rakamlar kaynakla birebir, iç tutarsızlıklar ve hakemsizlik notlara doğru yazılmış. En güvenilir iki küme.
- **A2, A7, A9, A10'daki TradingView satırları:** açıklama metniyle birebir uyumlu, ancak Pine kodu ve lisans başlığı bu denetimde de görülemedi; kural-kod uyumu doğrulanmış sayılmaz.
- **A6 (Japonya/Kore), A8 (Rusya/Avrupa):** 7 satırın 7'si geçti; bayrak gerekçeleri kaynakta doğrulandı.
- **A7 (Hindistan/GD Asya/Türkiye):** kendi iç denetimini yapmadığını bildiren küme; örneklemdeki 3 satırı da geçti, ancak örneklem küçük.
- **A10 (Afrika/Orta Doğu):** 6 satırın 5'i geçti; tek düzeltme bayrak gerekçesinin abartılı yazılmasıydı.

**Kalan riskler.**
1. **Denetlenmeyen 379 satır.** Örneklem %9,1; S0186 türü "varsayılan ayarı yanlış okuma" hataları ve küçük parametre farkları başka satırlarda da bulunabilir. Bir kuralı uygulamadan önce o satırın kaynağı yeniden okunmalı.
2. **TradingView (41 satır) kural-kod uyumu doğrulanmadı.** Kaynak kod sekmesi WebFetch'e gelmiyor; bu satırlarda "bayrak yok", repaint/lookahead olmadığı anlamına gelmiyor.
3. **Popülerlik ve lisansın bir bölümü doğrulanamadı.** GitHub API bu oturumda kapalıydı, yıldız sayıları (örneklemde 3 satır) teyit edilemedi; TradingView sayaçları etiketsiz. LICENSE dosyaları klonlanan depolarda doğrulandı.
4. **Doğrulama, sayfanın model özetine dayanıyor.** WebFetch ham metni değil özet döndürüyor; uzun PDF'lerde (S0415) yalnız ilk bölüm okundu. ek_kaynaklar linkleri (S0196 dışında) açılmadı.
5. **Bayrak tutarlılığı.** Hesap açma çağrısı içeren aracı kurum sayfalarının bir kısmı ŞÜPHELİ (ör. S0405), bir kısmı değil (ör. OANDA satırları); ölçüt kümeler arasında aynı sıkılıkta uygulanmamış. Ayrıca S0089 davetli (kodu kapalı) bir script; ŞÜPHELİ işaretli ama "kodu açık" şartını zorluyor.
6. **Performans rakamlarının hiçbiri yeniden üretilmedi**; denetim yalnız rakamın kaynakta yazdığını doğruladı.

**Raporun genel tutarlılığı.** Rapordaki sayılar `stats.py` çıktısıyla tek tek karşılaştırıldı: toplam, aile, bölge, platform, kanıt türü, bayrak, stop, popülerlik ve ilk 10 aile tablosu CSV ile uyuşuyor; rapordaki tüm S-kimlikleri CSV'de var ve bağlantıların hepsi ilgili satırın kaynak_link'iyle aynı. Tek tutarsızlık lisans dökümündeydi: sayılan kalemler 409 ediyordu, çünkü 8 satır (FxCraft örnek EA lisansı 3, pyproject'te UNLICENSED 3, BSD tarzı 1, kodu kapalı davetli script 1) dökümde yoktu; cümleye eklendi. "En güçlü 15" seçimi makul: 15 satırın 14'ü akademik makale, seçim uzun örneklem ve çoklu piyasa ölçütüne uyuyor ve her satırın bozulma uyarısı yanında veriliyor. Üç çekince var. S0147 hakemsiz bir şirket beyaz kitabı ve kanit_turu "backtest iddiası"; listede yer alması başlıktaki "akademik ya da uzun canlı kayıt" ölçütünü esnetiyor (rapor bunu belirtiyor). S0141'in rakamları Quantpedia'nın ücretsiz kısmında yok; gücü replikasyonlardan geliyor. S0143, S0154, S0156 ve S0158 makalenin kendisine değil Quantpedia özetine bağlı. Bu 15 satırdan yalnız ikisi (S0142, S0147) denetim örneklemine düştü ve ikisi de geçti; diğer 13'ü bu denetimde açılmadı.
