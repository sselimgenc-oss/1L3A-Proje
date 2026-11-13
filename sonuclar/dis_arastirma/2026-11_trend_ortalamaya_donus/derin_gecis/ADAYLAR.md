# Aday listesi (12 aday, en fazla 15 sınırı içinde)

> Bu liste **araştırma önerisidir, kanıt değildir**. Dış rakamlar kaynakların iddiasıdır; biz doğrulamadık.
> Hiçbirinin canlıya etkisi yok. Plan kuralları (CANLI_PLAN_V2 §8): kota doldurulmaz, yılda en fazla 2–3 ön kayıtlı tur,
> görülmüş test dönemi yeniden kanıt sayılmaz, canlı sürerken stratejiye yeni filtre eklenmez. Yani 12 adayın hepsi
> koşulamaz: **önerim bir turda en fazla 3 aday** (A2, A3 ve A1'in ileri-veri izlemesi; gerekçe en altta).
> Yasaklar (martingale, DCA, ortalama düşürme, stopsuz grid, ML) hiçbir adayda yok. Kaynağında stopu olmayan kurallarda
> "felaket stopu eklenmeli" notu ayrıca yazıldı.
> Sayılar `veri/mumlar` 5 dakikalık dosyalarından betikle sayıldı (geliştirme dönemi ≤ 2025-11-07, dosyası olan 22 sembol:
> 12 kripto + 7 DK_ hisse + DK_XAU + DK_WTI). Sayılar **sinyal/olay sayısıdır**, işlem sayısı değil; stopla/çıkışla azalır.

Sıra: önce çelişki listesi (biz eledik, dış kanıt var), sonra "kodlu ama hiç koşulmamış", sonra BIZDE_YOK / FARK_TEST_EDILMEDI.

---

## A1. Kripto Donchian ansamblı — çelişki #1 (dış satırlar: S0533, S0235, S0002)
- **Kural (tek cümle):** Her coin için dokuz bakış süresinin her birinde günlük kapanış o sürenin en yüksek kapanışını aşarsa long, kanal orta noktası iz stopuyla çık; dokuz modeli eşit ağırlıkla birleştir, 90 günlük volatiliteyle boyutlandır (kod: `motor/portfoy/stratejiler/v3.py` `DonchianAnsambl`).
- **Neden aday:** v3'te bu kaynak birebir koşuldu ve **tek kapıda (P6) kıl payı kaldı**: strateji Sharpe 0,978, al-tut 0,995 (fark −0,017, pratikte sıfır). Dış kuralda yalnız kanal-orta-nokta iz stopu var; bizim koşuda ek olarak motorun zorunlu ATR(14)x3 stopu çalıştı ve evren 2019+ idi (dış çalışma 2015+). Yani "test ettik" doğru, "dış kuralın tam stop yapısını test ettik" yanlış.
- **Dış kanıt (iddia):** Zarattini ve ark. kripto uygulaması, 2015–2025, %0,10 maliyetle net CAGR ≈ %18, BTC'ye karşı yıllık net alfa ≈ %11 (CXO özeti); aynı ailede BTC'de 10 günlük maksimumda alım örneklem dışında çalışmaya devam ediyor (Quantpedia notu). S0235 (15 dk Donchian, kaynağın kendi notu: maks. DD hedefi aşıyor) bu adaya bağlı alt varyant.
- **Bizim evrende uygulanabilirlik:** Tam (13 USDT perp, günlük OHLCV; HYPE vb. kısa tarihçeli coinlerde evren 2019+).
- **Gereken veri:** Günlük OHLCV (var). Funding zaten kripto maliyetinde.
- **Tahmini işlem:** 1942 (ölçüldü: v3 eleme koşusu, 13 sembol, 2019-07 → 2026-10).
- **Risk:** (1) Aynı veriyle ikinci bakış: P6 sonucu sonradan değiştirilemez (ON_KAYIT_V3); yalnız **yeni ön kayıt + ileri (paper) veri** ile. (2) Parametre sayısı küçük (9 bakış süresi sabit), aşırı uyum riski düşük. (3) Lookahead: kanal "önceki muma kadar" hesaplanmalı (kodda öyle). (4) Tek hedef long-only kripto beta; hedefi Sharpe değil **düşüş (MDD/Calmar)** olarak yazmak plan hedefiyle (düşüş ≤ %15) uyumlu olurdu — ama bu da kapıyı sonuçtan sonra değiştirmek olur, ön kayıtla yapılmalı.
- **Felaket stopu:** Kaynakta orta-nokta iz stopu var; motorun zorunlu stopu ATR×3'ten geniş (5–6 ATR) olarak ön kayıtla belirlenmeli.

## A2. Adaptif trend, 6 saatlik kripto momentum + ATR iz stop — çelişki/ZATEN ama koşulmamış (S0153)
- **Kural:** 6 saatlik mumda MOM = (P_t − P_{t−L}) / P_{t−L} eşiği (θ) aşarsa long, ATR iz stopla çık; uzun aday yalnız piyasa değeri ilk 15 coin ve önceki ay Sharpe ≥ 1,3 olanlar.
- **Neden aday:** İlk geçişte ZATEN sayılmıştı ama `v3__adaptivetrend-6s-momentum` **kodlanmış, hiçbir sonuç dosyasında yok**. Test edilmiş sayılamaz. Üstelik kaynağın L / θ / ATR değerleri eksik; arşivdeki sınıf bunları uydurma sabitlerle (20 / 0 / ATR×3) doldurmuş.
- **Dış kanıt (iddia):** arXiv 2602.11708: örneklem dışı Ocak 2022 – Aralık 2024, 4 bp taker + kayma + funding sonrası Sharpe 2,41, CAGR %40,5, MDD −%12,7. Bağımsız not "karışık": kripto TSMOM boğada yoğun, yalnız-kısa portföyler kaybettiriyor.
- **Uygulanabilirlik:** Long kolu tam uygulanabilir (6h = 5 dk veriden birleştirme). Short kolu ve "ilk 15 piyasa değeri" filtresi için tarihsel piyasa değeri verimiz yok (dolar hacmi sırası vekil olabilir).
- **Gereken veri:** 5 dk → 6 saatlik OHLCV (var); aylık evren sıralaması için dolar hacmi (OHLCV'den türetilir).
- **Tahmini olay:** 6360 giriş olayı (13 kripto, 6h, MOM(20)>0 ilk gün, filtresiz; stop ve Sharpe süzgeciyle azalır; ≈ 74/sembol-yıl).
- **Risk:** Ön ay Sharpe ≥ 1,3 süzgeci yeni coinler için hayatta kalma yanlılığı taşır; θ ve L için "plato" iddiası kaynakta ayar verisiyle (aşırı uyum). Kaynak çok yeni, bağımsız tekrar yok.
- **Felaket stopu:** İz stop kaynakta var (α ≈ 2,5 ATR); kısa kolun çıkışı kaynakta belirsiz → eklenmeli.

## A3. Larry Williams / Koreli volatilite kırılımı (açılış + k × önceki gün aralığı) — kodlu ama hiç koşulmamış (S0078, S0244, S0248, S0249, S0250, S0321)
- **Kural:** Gün içinde fiyat "bugünkü açılış + k × (dünkü yüksek − düşük)" seviyesini aşarsa long, gün sonunda (ya da ertesi açılışta) çık; uyarlamalı sürümde k = 20 günlük ortalama "noise oranı".
- **Neden aday:** Altı dış satırın hepsi "benzeri test edildi" sayılmıştı; oysa karşılık gelen `v3__volatilite-kirilim-k05` **hiç koşulmadı** (k = 0,5 tek ayar, ızgarası yok). Uyarlamalı k, 12 saatlik seans ayrımı, MA-skor boyutlandırma ve hedef volatilite arşivde yok.
- **Dış kanıt (iddia):** Karışık. S0249 (blog): 2014–2018 kripto, hedef volatilite %3'te bileşik +%143,6 / MDD −%3,8 (backtest, örneklem içi). S0245: aynı fikrin dürüst negatif sonucu −%3,3 (39/59 işlem, S&P örneklemi). Akademik kanıt yok.
- **Uygulanabilirlik:** Tam (kripto günlük; gün sınırı UTC; KST 09:00 değil). DK_ hisse/emtia için seans başlangıcı tanımı gerekir.
- **Gereken veri:** Günlük OHLCV (var), gün içi doğrulama için 5 dk (var).
- **Tahmini olay:** 6512 tetik günü (12 kripto, k = 0,5, açılış > son 3 kapanış ort.), ≈ 76/sembol-yıl; DK_ 7 hisse 3753, DK_XAU+DK_WTI dahil toplam 11 968 (22 sembol).
- **Risk:** Maliyet: günde bir tur işlem, tur başı ≈ %0,1–0,2 (tahmin; taker %0,05 x2 + kayma varsayımıyla) → brüt avantaj bundan büyük olmalı (INCELEME_NOISE'ta aynı sorun). Lookahead: seviye "dünkü aralık + bugünkü açılış"; tetik anında henüz bilinmeyen bugünkü yüksek kullanılmamalı (kapanmış 5 dk mumla doğrula, giriş sonraki mum açılışı). Aşırı parametre: k ve trend filtresi seçimi.
- **Felaket stopu:** Kaynak (S0244) stopsuz; arşiv sınıfı 2 ATR stop eklemiş.

## A4. Gürültü bölgesi gün içi momentum — çelişki #2 (S0199, S0532)
- **Kural:** Son 14 günün aynı saatteki ortalama mutlak hareketinden bant kur; yarım saatlik kontrolde fiyat üst bandın üstündeyse long, altındaysa short; iz stop = max(bant, VWAP), gün sonunda kapat.
- **Neden aday (ve neden temkinli):** v3'te `v3__gunici-momentum-noise-alani` (DK_SPX 30 dk) koşuldu, net×2 −%20, PF 0,13. `sonuclar/v3/INCELEME_NOISE.md`: motor hatası yok; **brüt avantaj ≈ +2,3 bps, maliyet ≈ 13 bps/işlem** (komisyon 5 bps varsayımı "tutucu, doğrulanmadı"), günde ~1,7 işlem; kill kuralı 121. işlemde (2017 H1) koşuyu kesti (tüm 2645 işlemde PF 0,43). Rastgele girişten +0,07 R/işlem iyi, yani brüt sinyal var ama maliyeti taşımıyor. Dış çalışma 1 dakika veri + ETF/vadeli maliyetiyle.
- **Dış kanıt (iddia):** Zarattini–Aziz–Barbon: SPY 2007–2024 net Sharpe 1,33, yıllık %19,6; 33 vadelide ortalama 0,60. Bağımsız not: BTC'de ilk-yarım-saat sinyali ~3 bp başabaş maliyetle kârsız (çürütüyor).
- **Uygulanabilirlik:** Sınırlı: DK_SPX var (2017+); kripto 24/7 seans tanımı yok. Asıl soru kural değil **maliyet**: gerçek Binance TradFi taker maliyeti doğrulanmadan teste değmez.
- **Gereken veri:** DK_SPX 5 dk (var), gerçek komisyon/kayma tablosu (YOK, kullanıcıdan alınmalı).
- **Tahmini işlem:** 2645 (ölçüldü, kill'siz); seyrek sürümde (günde ≤ 1 kontrol) tavan ≈ 2400 (9 yıl × ~250 gün) — tahmin.
- **Risk:** Aşırı parametre düşük (14 gün); asıl risk maliyet. Düşük öncelik.
- **Felaket stopu:** Kaynakta bant/VWAP iz stopu ve gün sonu kapanışı var; ek gerekmez.

## A5. Tüm zamanların zirvesinde alım + çok geniş (10×ATR) iz stop (S0147, S0503, S0655, S0682)
- **Kural:** Kapanış tüm zamanların en yüksek kapanışına eşit/üstündeyse ertesi açılışta long; 10×ATR iz süren stopla çık.
- **Neden aday:** Dış kural ATH (n sınırsız) + 10×ATR iz stop; arşiv `dis__yeni-zirve-trend-filtresi` yalnız n = 50/100/200 gün ve ATR stop 2–4. v1'de 1d geçti, sağlamlıkta K5 (DSR) takıldı; v2 E1 net<0. Farklı yön: çok geniş iz stop ve sınırsız pencere.
- **Dış kanıt (iddia):** S0147: işlem başına ortalama net %15,2, kazanma %49,3, kazanç/kayıp 2,56, ortalama tutma 305 gün (backtest özeti; "destekliyor" notu). Yazarlar ABD hisse, 1991–2024.
- **Uygulanabilirlik:** Evren: 13 kripto + DK_ hisseler + DK_XAU; ATH çok seyrek olay. Kriptoda 10×ATR ≈ %30 üstü stop → işlem başı %1,5 risk ile pozisyon çok küçük kalır.
- **Gereken veri:** Günlük OHLCV (var).
- **Tahmini olay:** ≤ 774 ATH günü (22 sembol, 170 sembol-yıl; ≈ 4,5/sembol-yıl); stop sonrası yeniden giriş kuralına göre gerçek işlem sayısı bunun altında. E2 kapısı (≥ 200 işlem) sınırda; ATH sonrası kısa seri çok bağımlı.
- **Risk:** Az işlem + yüksek yoğunlaşma (birkaç büyük trend belirler); 2021 ve 2024 kripto ATH dönemlerine bağımlı. Lookahead: ATH "bugünü hariç önceki max" olmalı.
- **Felaket stopu:** 10×ATR iz stop zaten geniş felaket stopu işlevi görür.

## A6. IBS (kapanışın günlük aralıktaki konumu) 3 günlük ortalama + 1 gün tutma (S0070; yakın: S0053)
- **Kural:** IBS'nin 3 günlük ortalaması 0,3'ün altına inince ertesi açılışta long, aynı günün kapanışında çık.
- **Neden aday:** Arşivin "az farkla kalan" ailesi: `pf__ibs_donus` v1 WF 1d geçti (Sharpe 0,97), sağlamlıkta K2/K5; v2 E1: Sharpe 0,44 < 0,5, net×2 +%8,9; holdout keşfi net −%0,1 (kanıt değil). Dış kuralda IBS ortalaması ve sabit 1 gün tutma var, arşivde yok.
- **Dış kanıt (iddia):** Zayıf: Nifty 2007–2014 sonuçları yalnız görselde (metinde sayı yok).
- **Uygulanabilirlik:** Tam (günlük, DK_ hisse + kripto).
- **Gereken veri:** Günlük OHLC (var).
- **Tahmini olay:** 2633 (22 sembol, ortalama-IBS aşağı kesişim günü).
- **Risk:** Kısa vadeli dönüş ailesi (RSI2, N-gün dip) bizde sürekli elendi; maliyet ×2'de hayatta kalma zor. Aşırı parametre: eşik 0,3, ortalama 3, tutma 1.
- **Felaket stopu:** Kaynakta stop yok → 3×ATR(14) felaket stopu eklenmeli.

## A7. DV2 göstergesi dip alımı, tek-grafik uyarlama (S0112) — BIZDE_YOK
- **Kural:** Önceki günün DV2 değeri (Kapanış/((Y+D)/2) − 1 değerinin 2 günlük ortalaması; kaynakta yüzdelik penceresi yazılı değil, sayımda 126 gün varsayıldı) < 10, kapanış > SMA200 ve 6 aylık getiri > 0 ise açılışta long; önceki günün yükseğini aşınca çık.
- **Neden aday:** Arşivde DV2 yok (kod ve envanterde arandı). Dış listedeki en sayısal iddia.
- **Dış kanıt (iddia):** Yıllık %20,9, Sharpe 1,01, maks. DD ≈ %34, 21 yılda 1 negatif yıl; S&P 500 tarihsel bileşenleri 2004+ (blog backtest, hayatta kalma yanlılığı kontrolü belirtilmiş değil).
- **Uygulanabilirlik:** Dış kural sıralamalı portföy ("normalize ATR'si en yüksek olanlar"); bizde 17 DK_ hisse ile **tek-grafik** uyarlama gerekir (sıralama yok). Dış sayıların bizde tekrarlanması beklenmemeli.
- **Gereken veri:** Günlük OHLC (var).
- **Tahmini olay:** ≤ 2876 sinyal günü (22 sembol; durum günü sayısı, fiili işlem daha az).
- **Risk:** Kısa vadeli dönüş ailesi, IBS ile aynı sorun; blog iddiası. Lookahead: yüzdelik sırası yalnız geçmiş 126 gün olmalı.
- **Felaket stopu:** Kaynakta stop yok → eklenmeli.

## A8. Hurst üssü rejim filtresi (S0511 trend, S0512 dönüş — S0512 dış listede ŞÜPHELİ bayraklı) — BIZDE_YOK
- **Kural:** 100 barlık R/S Hurst üssü > 0,55 ise trend kolunda (kapanış SMA20 üstü long), < eşik ise dönüş kolunda (kapanış SMA20 altı long); %2 sabit stop.
- **Neden aday:** Arşivde Hurst yok. Mevcut ailelere **rejim filtresi olarak** bindirilebilir (rejim bindirmesi v2'de yoktu; CANLI_PLAN_V2 §3: sonuca bakılmış fikir olarak ancak yeni ön kayıtla).
- **Dış kanıt (iddia):** Zayıf: "ortalama yıllık ~%40, en iyi kripto" (5 dk, kaynak yok, bayrak ŞÜPHELİ).
- **Uygulanabilirlik:** Kripto 5 dk; filtre olarak 1d/4h ailelere de bindirilebilir.
- **Gereken veri:** OHLCV (var).
- **Tahmini işlem:** Filtre ek işlem üretmez; mevcut ailelerin işlem sayısını azaltır. Hesaplanmadı.
- **Risk:** R/S tahmincisi kısa pencerede çok gürültülü ve yanlı; eşik (0,55) ve pencere (100) yeni serbest parametre; en zayıf kanıtlı aday. Düşük öncelik.
- **Felaket stopu:** Kaynakta %2 stop var.

## A9. Kontrarian trend göstergeleri (PSAR altında al, %K<%D iken al, -DI>+DI & ADX>45 iken al) (S0466, S0467, S0069; S0465 EMA50 kısmen test edilmiş)
- **Kural:** Klasik trend sinyalinin tersi: fiyat Parabolic SAR altındayken long, %K < %D ve %D düşüyorken long, vb.; koşul bozulunca çık.
- **Neden aday:** Arşivde ters-yön kurallar yok (ilk geçiş de bunu "BIZDE_YOK" saymıştı; denetimde doğrulandı). Not: kontrarian EMA50 ≈ `dis__ema50-sapma` (sapma ≤ 0 %) ile büyük ölçüde örtüşür, o ayrıca düşük öncelik.
- **Dış kanıt (iddia):** Akademik (Nairobi borsa endeksi 2006–2013): on kontrarian kuralın hepsinde al-günü/sat-günü farkı anlamlı; ancak yazarlar çok sık gir-çık nedeniyle al-tutla maliyet-sonrası kıyası net yapmıyor.
- **Uygulanabilirlik:** Tam ama kanıt tek küçük sığ borsa endeksinde; kripto/DK_ için aktarım belirsiz.
- **Gereken veri:** Günlük OHLC (var).
- **Tahmini işlem:** Durum kuralı, sayılmadı (günlük sinyal sık değişir; yüzlerce–binlerce).
- **Risk:** Maliyet: sık gir-çık. Aşırı parametre düşük. Düşük öncelik.
- **Felaket stopu:** Kaynakta stop yok → eklenmeli.

## A10. Yüksek/düşük ortalaması zarfından dip alımı (MMM, SlowPotato, Monge Yokohama, LW STP0003) (S0583, S0578, S0584, S0697) — BIZDE_YOK
- **Kural:** Kapanış SMA(30) üstünde ve kapanış son 3 düşüğün SMA'sı altına inince long; son 3 yüksek ortalamasını aşınca çık.
- **Neden aday:** Arşivde bu aile yok; ucuz (sıfır yeni altyapı).
- **Dış kanıt (iddia):** S0583: BTC-USDT 1 saat 2019–2021, 393 işlem, net %58,64, maks. DD −%21,12, Sharpe 1,24, isabet %61 (aynı dönemde piyasa +%681; yani al-tutun çok altında). Diğer üçünde kanıt yok.
- **Uygulanabilirlik:** Tam (kripto 1h).
- **Gereken veri:** 1h OHLCV (var, 5 dk'dan türetilir).
- **Tahmini olay:** 25 862 (13 kripto, 1h, 85,7 sembol-yıl ≈ 300/sembol-yıl). Maliyet baskısı çok yüksek.
- **Risk:** Kısa vadeli dip alımı ailesi (RSI/IBS gibi) sürekli elendi; 300 işlem/yıl/sembol maliyeti öldürür. Kanıt Jesse örneği (yazar backtesti).
- **Felaket stopu:** Kaynakta stop yok (S0578 pratik stop −%99) → eklenmeli.

## A11. EMA eğim filtreli osilatör dönüşü (MACD / Bollinger / Williams %R / CCI + EMA eğimi) (S0365, S0380, S0381, S0382)
- **Kural:** Osilatör (WPR −95/−5, CCI ±110, BB(15) 1σ içeri / 3σ çıkış, MACD) sinyali yalnız EMA(55) eğimi yönündeyse alınır; ters seviyede çık.
- **Neden aday:** Dört bağımsız satır aynı yeni bileşeni (EMA **eğim** filtresi) kullanıyor; arşivde fiyat>EMA filtresi var ama eğim filtresi yok. Ucuz tek bileşen testi.
- **Dış kanıt (iddia):** Aynı yazar serisi, EURUSD M15, 2006-10 → 2011-09, optimize edilmiş ayarlarla: WPR net +%313 PF 1,42; CCI +%266 PF 1,26; BB +%230 PF 1,33 (örneklem içi optimizasyon; "akademik" etiketli ama tez/rapor).
- **Uygulanabilirlik:** Forex dışı evrende (kripto 15m, DK_XAU) denenebilir; kaynak forex EURUSD.
- **Gereken veri:** 15m OHLCV (var).
- **Tahmini işlem:** Hesaplanmadı (15m'de çok yüksek).
- **Risk:** Örneklem içi optimize (EMA 55, eğim 4, seviyeler −95/−110 …); 2006–2011 forex; aşırı uyum riski yüksek. Düşük-orta öncelik.
- **Felaket stopu:** Kaynakta 50–80 pip stop var.

## A12. Faber / TSMOM tipi yavaş MA filtresi, sepet düzeyinde risk azaltıcı (S0141, S0157, S0145)
- **Kural:** Ay sonunda her varlık (13 kripto + DK_SPX + DK_XAU + DK_WTI) kapanışı 10 aylık (≈ 200 günlük) MA üstündeyse eşit ağırlıkla tut, değilse nakit; hedef getiri değil **düşüş azaltma**.
- **Neden aday:** Çelişki #3/#4. `v2__tsmom-oy` (E4), `v2__tsmom-12-1` (E1), `dis__tsmom` (E2: 33 işlem < 200; E5 kill) tek-grafik kapılarıyla yapısal olarak elendi; `pf__trend_sepet` E5 (kill 8); `dis__sma200-ls` v2 K2 p=0,004 ama BH keşfi çıkmadı. Yani sinyalde bir şey var ama kapı tasarımı (≥200 işlem, −%20 kill) yavaş sinyali eliyor.
- **Dış kanıt (iddia):** Akademik: 28 emtiada 6–12 aylık MA filtresi Sharpe 0,66–0,76, MDD al-tutun ~1/3'ü (1992–2011); ~235 endeks ve ~120 hissede üstün performans (ama en büyük 100 S&P hissesinde başarısız).
- **Uygulanabilirlik:** Tam (günlük); ama sepet ≈ 16 sembol, dış kanıt onlarca vadeli/ETF.
- **Gereken veri:** Günlük kapanış (var).
- **Tahmini işlem:** Aylık karar × 16 sembol; geçiş sayısı ≈ 100–200 (tahmin, hesaplanmadı). Çok az işlem: E2 benzeri kapı tasarlanmalı (portföy kapısı).
- **Risk:** Kripto boğa/ayı ayrışması 2018, 2022 gibi az örneklem; test dönemi görülmüş (ön kayıt + ileri veri gerek).
- **Felaket stopu:** Aylık MA filtresi kendisi stop işlevi görür; ek gün içi stop gerekmez, ama kasa seviyesinde düşüş freni zaten var.

---

## Öneri (tek paragraf)
Plan bir turda 2–3 test izin veriyor. Önceliğim: **A3** (altı dış satır, arşivde kodlu ama hiç koşulmamış; yeni kod/veri gerekmiyor; tek turda tek koşuyla ön kayıt yazılabilir; ama maliyet baskısı yüksek), **A2** (kodlu, hiç koşulmamış; dış iddia güçlü ama çok yeni ve süzgeci hayatta kalma yanlılığı taşıyor) ve **A1'i test değil ileri-veri izleme** olarak (P6 sonucu değişmez; paper'a bir "geniş stoplu varyant" olarak eklemek ancak kullanıcı kararıyla). A4 için önce gerçek maliyet verisi gerekir. A8–A11'i şu an önermem (kanıt zayıf/aşırı uyum riski), A5–A7'yi "kısa vadeli dönüş / az işlem" sorunları nedeniyle düşük öncelik sayarım.
Karar kullanıcıya aittir; bu liste test emri değildir.
