# 1L3A Aday Strateji Raporu (Strateji Birlestirme)

Bu rapor, 438 kitap kartini ailelere topluyor, her aileye puan veriyor ve her ajan (scalp / daytrade / swing) icin 10 aday + 5 yedek oneriyor. Kartlar kitaplardan cikarilmis VERIDIR; rapor bunlari kodlamaya hazir "aday liste"ye cevirir. Henuz backtest yapilmadi: skorlar kitaplardaki yayginlik ve kodlama kolayligina dayanir, karlilik kaniti degildir.

## 1. Ozet sayilar

| Kalem | Sayi |
|---|---|
| Toplam kart satiri (kart_dizini.csv) | 438 (benzersiz kart_id: 435; 3 mukerrer satir) |
| Aileye giren kart satiri | 333 |
| Cikis/risk modulune giren kart satiri | 35 |
| Elenen kart satiri | 70 |
| Cekirdek aile (stilden bagimsiz mekanik) | 53 |
| Aile kaydi (stil basina ayri; scalp/daytrade/swing) | 100 (scalp 26, daytrade 29, swing 45) |
| Cikis/risk modulu (aile mantigiyla) | 13 |
| elenenler.json kaydi (kart_id basina) | 68 |

Stil yeniden atamasi (kural 1) uygulandi: klasor etiketine bakilmadi; zaman dilimi ve tutma suresine gore atandi. Ornekler: Bulkowski'nin 1G kartlari swing, 5m gun ici desenleri scalp, ORB daytrade; Scheier kartlari daytrade (seans modelleri) veya scalp (1m EMA/Stokastik kartlari, 5m'ye uyarlanir); Graham'in gun ici kopus/VWAP/bosluk kartlari daytrade, gunluk kartlari swing; Boxer'in 1m bosluk/kanal kartlari daytrade.

## 2. Skor formulu

```
toplam = 0.40*yayginlik + 0.25*kodlanabilirlik + 0.25*uyum + 0.10*kanit     (hepsi 0-10)
```

- **yayginlik** = min(10, 2 x farkli YAZAR sayisi). 1 yazar=2, 2=4, 3=6, 4=8, 5 ve ustu=10 (kart sayisi sayilmaz; Heikin Ashi Trader'in 3 kitabi, Gavin Holmes'in 2 PDF'i, Christopher'in scalp+swing kitaplari tek yazar; Stevenson-Carson'daki ayni Bollinger(40,2)+RSI(5)+ADX kurali 1 kaynak; "eseckal" yazar sayilmadi, kitap adi kullanildi).
- **kodlanabilirlik** = 10 x (0.7 x (ailedeki en iyi kart puani / 3) + 0.3 x (puani 2 veya 3 olan kartlarin orani)).
- **uyum** (elle, gerekceli): kripto/hisse/emtia perpetual'da >=5m ve sadece OHLCV ile calisir mi; seans bagimliligi, ozel veri ihtiyaci, tespit zorlugu dusurur.
- **kanit**: baslangic 1; kitapta sayisal iddia/test varsa +2; Bulkowski gibi buyuk istatistik varsa +3; geri test tablosu varsa +1; negatif kanit -2; kanitsiz/supheli iddia -1 (sinir 0-10). ORB elle 3'e sabitlendi.

## 3. Stil bazinda tablolar

### Scalp (5m-15m, dakikalar-saatler)

Bu stilde 26 aile var. En iyi 15:

| Sira | Aile | Kategori | Yazar | Kodlanabilirlik | Uyum | Toplam | Not |
|---|---|---|---|---|---|---|---|
| 1 | scalp__stokastik-donus **[ONERILEN 2]** | momentum | 5 | 7.7 | 9 | 8.28 | Trend yonunde Stokastik 20/80 donusu; trend filtreli osilator girisi. |
| 2 | scalp__ma-kesisim **[ONERILEN 3]** | trend_takip | 7 | 7.7 | 8 | 8.22 | En yaygin trend takip kurali; yatay piyasada sahte sinyal uretir, ADX/egim filtresi gerekir. |
| 3 | scalp__bant-donus **[ONERILEN 1]** | ortalamaya_donus | 4 | 7.2 | 9 | 7.65 | Bollinger/Keltner bandi disindan ortalamaya donus (RSI/ADX onayli); trend gununde zarar eder. |
| 4 | scalp__ma-geri-cekilme **[ONERILEN 4]** | trend_takip | 4 | 7.2 | 8 | 7.00 | Trendde MA'ya geri cekilmeyi alir; trend piyasada guclu, yatayda zayif. |
| 5 | scalp__supertrend-psar **[ONERILEN 5]** | trend_takip | 2 | 10.0 | 9 | 6.65 | ATR/ivme tabanli iz suren cizgi donusu; tam mekanik, yatayda sahte sinyal. |
| 6 | scalp__macd-sinyal **[ONERILEN 6]** | momentum | 3 | 7.7 | 9 | 6.58 | MACD sinyal/sifir cizgisi kesisimi; cok yazar tarafindan anlatilir, tam mekanik. |
| 7 | scalp__rsi-asiri-donus **[ONERILEN 7]** | ortalamaya_donus | 3 | 6.7 | 9 | 6.42 | RSI asiri alim/satimdan ters donus; guclu trendde erken ters sinyal. |
| 8 | scalp__rsi-momentum-esik [yedek 1] | momentum | 2 | 7.7 | 9 | 6.08 | RSI 50/60/40 esigi ile momentum yonu; basit filtre niteliginde. |
| 9 | scalp__heikin-ashi-donus **[ONERILEN 9]** | trend_takip | 2 | 7.7 | 9 | 6.08 | Heikin Ashi renk donusu; deterministik ama yazarlar kayiplarini gostermez. |
| 10 | scalp__rsi-diverjans [yedek 4] | momentum | 3 | 5.7 | 7 | 5.88 | Fiyat-osilator uyumsuzlugu; pivot tespiti yoruma acik ve sinyal gec. |
| 11 | scalp__geri-cekilme-fiyat-eylemi [yedek 2] | trend_takip | 3 | 6.7 | 6 | 5.88 | Fiyat eylemiyle trend ici geri cekilme girisi; kurallar mum bazli. |
| 12 | scalp__cci-esik [yedek 5] | momentum | 1 | 9.0 | 9 | 5.60 | CCI +-100/30 esik kirilimi; yazar cok sayida yanlis sinyal uyarisi yapar. |
| 13 | scalp__konsolidasyon-kirilim **[ONERILEN 8]** | kirilim | 2 | 7.1 | 8 | 5.47 | Dar blok/aralik kirilimi (hacimli); yanlis kirilim cok, filtre gerekir. |
| 14 | scalp__seviye-tepki [yedek 3] | destek_direnc | 3 | 5.9 | 6 | 5.47 | Yuvarlak sayi / onceki gun seviyesinde tepki; seviye secimi sezgisel. |
| 15 | scalp__cift-dip-tepe **[ONERILEN 10]** | formasyon | 2 | 6.7 | 6 | 5.18 | Cift dip/tepe boyun kirilimi; Bulkowski istatistigi var (gunluk), tespit toleransa duyarli. |

**ONERILEN 10 (scalp):**

1. `scalp__bant-donus` (skor sirasi 3, toplam 7.65) - Ortalamaya donus; 4 yazar; ADX<25 filtreli yatay rejim.
2. `scalp__stokastik-donus` (skor sirasi 1, toplam 8.28) - Trend filtreli osilator giris; 5 yazar.
3. `scalp__ma-kesisim` (skor sirasi 2, toplam 8.22) - Trend takip; 7 yazar, en yaygin.
4. `scalp__ma-geri-cekilme` (skor sirasi 4, toplam 7.00) - Trend icinde geri cekilme (trend takip ama farkli giris zamani).
5. `scalp__supertrend-psar` (skor sirasi 5, toplam 6.65) - Iz suren trend cizgisi; tam mekanik (kod 10/10).
6. `scalp__macd-sinyal` (skor sirasi 6, toplam 6.58) - Momentum kesisimi; MA ailelerinden farkli sinyal turu.
7. `scalp__rsi-asiri-donus` (skor sirasi 7, toplam 6.42) - Osilator ortalamaya donus (bant-donus ile farkli sinyal kaynagi).
8. `scalp__konsolidasyon-kirilim` (skor sirasi 13, toplam 5.47) - SIRA DISI (13.): kirilim kategorisi eksik kalmasin diye eklendi (Volman blok/aralik kirilimi).
9. `scalp__heikin-ashi-donus` (skor sirasi 9, toplam 6.08) - Fiyat donusumu ile trend sinyali; 2 yazar, tam mekanik.
10. `scalp__cift-dip-tepe` (skor sirasi 15, toplam 5.18) - SIRA DISI (15.): formasyon/donus kategorisi + Bulkowski istatistigi.

**5 YEDEK:**

1. `scalp__rsi-momentum-esik` (skor sirasi 8, toplam 6.08) - RSI 50 esigi; sade yon filtresi.
2. `scalp__geri-cekilme-fiyat-eylemi` (skor sirasi 11, toplam 5.88) - Fiyat eylemi giris.
3. `scalp__seviye-tepki` (skor sirasi 14, toplam 5.47) - Destek-direnc tepkisi.
4. `scalp__rsi-diverjans` (skor sirasi 10, toplam 5.88) - Diverjans; pivot tespiti gerekli.
5. `scalp__cci-esik` (skor sirasi 12, toplam 5.60) - CCI esigi; tek yazar ama tam mekanik.

Cesitlilik: ortalamaya_donus=2, momentum=2, trend_takip=4, kirilim=1, formasyon=1.

### Daytrade (15m-1h, gun ici kapanir)

Bu stilde 29 aile var. En iyi 15:

| Sira | Aile | Kategori | Yazar | Kodlanabilirlik | Uyum | Toplam | Not |
|---|---|---|---|---|---|---|---|
| 1 | daytrade__orb **[ONERILEN 1]** | kirilim | 4 | 8.7 | 5 | 6.92 | Acilis araligi kirilimi; Bulkowski'ye gore mekanik cikislarla komisyon sonrasi zararli (NEGATIF KANIT), seans uyarlamasi sart. |
| 2 | daytrade__trend-yapi-dow **[ONERILEN 2]** | trend_takip | 3 | 6.7 | 7 | 6.12 | Dow yapisi / cok zaman dilimi hizalama; salinim tespiti ile kodlanir. |
| 3 | daytrade__konsolidasyon-kirilim **[ONERILEN 3]** | kirilim | 3 | 6.2 | 8 | 5.95 | Dar blok/aralik kirilimi (hacimli); yanlis kirilim cok, filtre gerekir. |
| 4 | daytrade__kirilim-geri-test **[ONERILEN 4]** | destek_direnc | 3 | 6.7 | 7 | 5.92 | Kirilan seviyeye geri test (rol degisimi); Bulkowski geri donus orani %54-58. |
| 5 | daytrade__bant-donus **[ONERILEN 5]** | ortalamaya_donus | 2 | 7.7 | 9 | 5.88 | Bollinger/Keltner bandi disindan ortalamaya donus (RSI/ADX onayli); trend gununde zarar eder. |
| 6 | daytrade__aralik-ticareti **[ONERILEN 6]** | ortalamaya_donus | 3 | 5.7 | 7 | 5.88 | Yatay aralikta al-sat; aralik kirilinca buyuk zarar riski. |
| 7 | daytrade__pivot-seviye **[ONERILEN 7]** | destek_direnc | 2 | 7.7 | 8 | 5.83 | Onceki gunden hesaplanan pivot/CPR seviyelerinde tepki veya kirilim; tamamen mekanik. |
| 8 | daytrade__vwap-donus **[ONERILEN 8]** | ortalamaya_donus | 2 | 6.7 | 8 | 5.58 | VWAP bandina asiri uzaklasinca ortalamaya donus; UTC gun VWAP'i gerekir. |
| 9 | daytrade__gap-doldurma [yedek 5] | ortalamaya_donus | 2 | 8.5 | 5 | 5.57 | Boslugun kapanmasina oynar; sadece seans bosluklu varliklarda anlamli. |
| 10 | daytrade__bb-sikisma-kirilim **[ONERILEN 9]** | kirilim | 1 | 7.7 | 9 | 5.27 | Bant daralmasi sonrasi kirilim; volatilite rejimi gecisini yakalar. |
| 11 | daytrade__donchian-kirilim [yedek 2] | kirilim | 1 | 7.7 | 9 | 5.27 | N-bar zirve/dip kirilimi; basit ve guclu trend yakalama, sahte kirilim riski. |
| 12 | daytrade__stokastik-donus **[ONERILEN 10]** | momentum | 1 | 7.7 | 9 | 5.27 | Trend yonunde Stokastik 20/80 donusu; trend filtreli osilator girisi. |
| 13 | daytrade__vwap-trend [yedek 1] | trend_takip | 2 | 6.2 | 8 | 5.25 | VWAP ustu/alti konumla yon; kurallar kisa, cikis tanimi zayif. |
| 14 | daytrade__pin-bar [yedek 3] | formasyon | 2 | 6.2 | 7 | 5.00 | Seviyede uzun fitilli mumla ters giris; seviye tanimi sart. |
| 15 | daytrade__rsi-asiri-donus | ortalamaya_donus | 1 | 7.7 | 9 | 4.97 | RSI asiri alim/satimdan ters donus; guclu trendde erken ters sinyal. |
| 16 | daytrade__ma-geri-cekilme [yedek 4] | trend_takip | 1 | 7.7 | 8 | 4.82 | Trendde MA'ya geri cekilmeyi alir; trend piyasada guclu, yatayda zayif. |

**ONERILEN 10 (daytrade):**

1. `daytrade__orb` (skor sirasi 1, toplam 6.92) - Seans kirilimi; NEGATIF KANIT var, filtreli (trend+hacim) ve 5m uyarlamali test edilecek.
2. `daytrade__trend-yapi-dow` (skor sirasi 2, toplam 6.12) - Gun ici trend yapisi (HH/HL kirilimi, cok zaman dilimi).
3. `daytrade__konsolidasyon-kirilim` (skor sirasi 3, toplam 5.95) - Gun ici blok/aralik kirilimi (Woods basinc bolgesi, Graham kopus, Scheier ogle kanali).
4. `daytrade__kirilim-geri-test` (skor sirasi 4, toplam 5.92) - Kirilim sonrasi geri test; kirilim ailelerinin daha guvenli girisi.
5. `daytrade__bant-donus` (skor sirasi 5, toplam 5.88) - Bollinger ortalamaya donus (30dk-1sa).
6. `daytrade__aralik-ticareti` (skor sirasi 6, toplam 5.88) - Yatay gun rejimi.
7. `daytrade__pivot-seviye` (skor sirasi 7, toplam 5.83) - Gun ici seviye tepkisi (pivot/CPR); tam mekanik.
8. `daytrade__vwap-donus` (skor sirasi 8, toplam 5.58) - VWAP bandindan ortalamaya donus.
9. `daytrade__bb-sikisma-kirilim` (skor sirasi 10, toplam 5.27) - SIRA DISI (9.-10.): volatilite genislemesi rejimini kapsar.
10. `daytrade__stokastik-donus` (skor sirasi 12, toplam 5.27) - SIRA DISI (11.): momentum/osilator temsili (Williams %R); 1 yazar, zayif dayanak.

**5 YEDEK:**

1. `daytrade__vwap-trend` (skor sirasi 13, toplam 5.25) - VWAP trend; kurallar kisa.
2. `daytrade__donchian-kirilim` (skor sirasi 11, toplam 5.27) - N-bar kirilimi.
3. `daytrade__pin-bar` (skor sirasi 14, toplam 5.00) - Fitil reddi.
4. `daytrade__ma-geri-cekilme` (skor sirasi 16, toplam 4.82) - Sloth (PSAR+EMA+Stokastik); tek yazar.
5. `daytrade__gap-doldurma` (skor sirasi 9, toplam 5.57) - Sadece hisse/emtia perpetual icin.

Cesitlilik: kirilim=3, trend_takip=1, destek_direnc=2, ortalamaya_donus=3, momentum=1.

### Swing (4h-1G, gunler-haftalar)

Bu stilde 45 aile var. En iyi 15:

| Sira | Aile | Kategori | Yazar | Kodlanabilirlik | Uyum | Toplam | Not |
|---|---|---|---|---|---|---|---|
| 1 | swing__ma-kesisim **[ONERILEN 1]** | trend_takip | 12 | 10.0 | 9 | 9.05 | En yaygin trend takip kurali; yatay piyasada sahte sinyal uretir, ADX/egim filtresi gerekir. |
| 2 | swing__macd-sinyal **[ONERILEN 2]** | momentum | 7 | 10.0 | 9 | 9.05 | MACD sinyal/sifir cizgisi kesisimi; cok yazar tarafindan anlatilir, tam mekanik. |
| 3 | swing__ma-geri-cekilme **[ONERILEN 3]** | trend_takip | 7 | 6.5 | 9 | 8.18 | Trendde MA'ya geri cekilmeyi alir; trend piyasada guclu, yatayda zayif. |
| 4 | swing__cift-dip-tepe **[ONERILEN 6]** | formasyon | 6 | 8.1 | 6 | 7.93 | Cift dip/tepe boyun kirilimi; Bulkowski istatistigi var (gunluk), tespit toleransa duyarli. |
| 5 | swing__konsolidasyon-kirilim **[ONERILEN 4]** | kirilim | 6 | 7.2 | 8 | 7.90 | Dar blok/aralik kirilimi (hacimli); yanlis kirilim cok, filtre gerekir. |
| 6 | swing__dar-aralik-kirilim **[ONERILEN 5]** | kirilim | 4 | 10.0 | 8 | 7.80 | NR7/ic bar/VCP gibi daralma sonrasi kirilim; gunluk mumlarda net kodlanir. |
| 7 | swing__trend-cizgisi-kanal [yedek 5] | destek_direnc | 6 | 6.4 | 5 | 7.55 | Trend cizgisi/kanal tepkisi veya kirilimi; cizgi secimi oznel. |
| 8 | swing__rsi-diverjans [yedek 2] | momentum | 7 | 6.2 | 7 | 7.40 | Fiyat-osilator uyumsuzlugu; pivot tespiti yoruma acik ve sinyal gec. |
| 9 | swing__mum-yutan-donus **[ONERILEN 10]** | formasyon | 7 | 6.2 | 7 | 7.40 | Yutan mum / dis bar donusu; net mum olcusu, tek basina zayif. |
| 10 | swing__fib-geri-cekilme **[ONERILEN 7]** | destek_direnc | 7 | 6.0 | 7 | 7.35 | Fibonacci seviyesinde trend yonunde giris; swing tespiti parametreye duyarli. |
| 11 | swing__bant-donus **[ONERILEN 8]** | ortalamaya_donus | 4 | 7.1 | 9 | 7.32 | Bollinger/Keltner bandi disindan ortalamaya donus (RSI/ADX onayli); trend gununde zarar eder. |
| 12 | swing__aralik-ticareti **[ONERILEN 9]** | ortalamaya_donus | 5 | 5.9 | 7 | 7.32 | Yatay aralikta al-sat; aralik kirilinca buyuk zarar riski. |
| 13 | swing__seviye-tepki | destek_direnc | 5 | 5.9 | 6 | 7.27 | Yuvarlak sayi / onceki gun seviyesinde tepki; seviye secimi sezgisel. |
| 14 | swing__bayrak-flama [yedek 3] | formasyon | 4 | 8.5 | 6 | 7.23 | Direk+bayrak devam kirilimi; Bulkowski istatistigi mevcut. |
| 15 | swing__goreceli-guc-momentum [yedek 4] | momentum | 3 | 10.0 | 6 | 7.10 | Gucli varliklarda momentum/geri cekilme; kucuk evrende (<=25 varlik) zayif. |
| 17 | swing__rsi-asiri-donus [yedek 1] | ortalamaya_donus | 3 | 7.7 | 9 | 6.67 | RSI asiri alim/satimdan ters donus; guclu trendde erken ters sinyal. |

**ONERILEN 10 (swing):**

1. `swing__ma-kesisim` (skor sirasi 1, toplam 9.05) - 12 yazar; trend takibin temeli.
2. `swing__macd-sinyal` (skor sirasi 2, toplam 9.05) - 7 yazar; momentum.
3. `swing__ma-geri-cekilme` (skor sirasi 3, toplam 8.18) - 7 yazar; trend ici geri cekilme.
4. `swing__konsolidasyon-kirilim` (skor sirasi 5, toplam 7.90) - 6 yazar; hacimli kirilim.
5. `swing__dar-aralik-kirilim` (skor sirasi 6, toplam 7.80) - SIRA 5: volatilite daralmasi kirilimi (NR7/ic bar/VCP), tam kodlanabilir.
6. `swing__cift-dip-tepe` (skor sirasi 4, toplam 7.93) - Formasyon/donus; 6 yazar, Bulkowski istatistikli.
7. `swing__fib-geri-cekilme` (skor sirasi 10, toplam 7.35) - 7 yazar; geri cekilme seviyesi.
8. `swing__bant-donus` (skor sirasi 11, toplam 7.32) - Ortalamaya donus (Bollinger); yatay rejim.
9. `swing__aralik-ticareti` (skor sirasi 12, toplam 7.32) - Yatay aralik rejimi; 5 yazar.
10. `swing__mum-yutan-donus` (skor sirasi 9, toplam 7.40) - 7 yazar; net mum olcusu; trend sonu donus. (rsi-diverjans ve trend-cizgisi-kanal yerine: daha mekanik)

**5 YEDEK:**

1. `swing__rsi-asiri-donus` (skor sirasi 17, toplam 6.67) - Osilator ortalamaya donus.
2. `swing__rsi-diverjans` (skor sirasi 8, toplam 7.40) - 7 yazar ama pivot tespiti yorumlu.
3. `swing__bayrak-flama` (skor sirasi 14, toplam 7.23) - Trend devami formasyonu; Bulkowski istatistikli.
4. `swing__goreceli-guc-momentum` (skor sirasi 15, toplam 7.10) - Momentum siralamasi; evren kucuk.
5. `swing__trend-cizgisi-kanal` (skor sirasi 7, toplam 7.55) - SIRA 6 ama cizgi secimi oznel (uyum 5).

Cesitlilik: trend_takip=2, momentum=1, kirilim=2, formasyon=2, destek_direnc=1, ortalamaya_donus=2.

Cesitlilik notu: Her stilde trend takip, ortalamaya donus, kirilim, momentum/osilator ve (mumkunse) formasyon karisimi korundu; skor sirasindan sapmalar yukaridaki satirlarda "SIRA DISI" ile isaretli. Daytrade havuzu zayiftir: gun ici kartlarin cogu tek yazarli veya Bulkowski/Woods gibi Forex/vadeli/hisse kaynaklidir, bu yuzden daytrade skorlari swing'e gore dusuktur.

## 4. Dikkat edilecekler

### 4.1 Negatif kanitlar

- **swing__cift-dip-tepe**: Uyari: Bulkowski'nin gun ici (5m) cift dip/tepe kartlarindaki istatistikler gunluk olcege aittir, gun ici dogrulama yok.
- **swing__konsolidasyon-kirilim**: Scheier: kirilimlarin cogu basarisiz olur; duraklama/retest filtresi gerekir.
- **swing__konsolidasyon-kirilim**: Bulkowski kisisel: destekten olumsuz kopmalarda (destek kirilimi satisi) satislarinin %70'i kayipla sonuclanmis.
- **swing__bayrak-flama**: Bulkowski: yuksek ve siki bayrak boga piyasasinda ortalama +%31 (2897 desen); basarisizlik orani yuksek: bayrak dibi stoplu basarisizlik %33 (ort. %27 kayip).
- **daytrade__orb**: Bulkowski (60.801 gun, 555 hisse testi): ORB mekanik cikislarla komisyon sonrasi zararli; kar yalnizca yazarin mekanik olmayan cikis yorumlariyla olusuyor. Sabit stoplar kayiplari kisiyor ama kazananlari da kesiyor.
- **swing__rsi-asiri-donus**: Schroder s.224: RSI(2) 90/10 sisteminde Sharpe zayif, dusus buyuk.
- **scalp__cci-esik**: Busiere: CCI +-100 sinyali cok sayida yanlis sinyal uretir (yazarin kendi uyarisi).
- **swing__uc-cubuklu-net-hat**: Bulkowski testi (554 hisse + 88 ETF, 2001-2010, komisyon 10$): SMA filtresiz ETF sistemi islem basina yaklasik -%0,2 kaybettirdi; 50 gunluk SMA filtresiyle karli hale geldi.

### 4.2 Supheli / kanitsiz iddialar

Asagidaki iddialar kitabin kendi sozudur, dogrulanmamistir ve skorda kanit puanini dusurmustur:

- **scalp__ma-kesisim**: [Waqar] Yazar: 'Şahsen pratiğimi geliştirdiğimden beri henüz bir işlem kaybetmedim'; her girişte 10-20 pip; en iyi kaydı bir swing'e dönüşüp 150 pip. İstatistik veya kanıt sunulmuyor.
- **scalp__ma-kesisim**: [Simvour] Yazar: ana trend cizgisine karsi girilmezse 'kararlarinizin %80'inin garanti altina alinmasi' (kisisel iddia, istatistik verilmemis).
- **scalp__ma-geri-cekilme**: [Trevor Candle] %83 kazanan işlem, kar faktörü 2,01, matematiksel beklenti 2,81; 1 Haziran - 14 Eylül 2021 demo verisi. Kitap örneklemin küçük olduğunu ve en az 2000 işlem gerektiğini belirtir (s.92-93).
- **scalp__ma-geri-cekilme**: [Jea Yu] Kitap: kazanma tutarlılığı %75 eşiğinin aşılması hedeflenir; 'aylık yüzde iki ila beş kazanç, kayıpları yüzde birin altında' ifadesi (sistem geneli). Örnek işlemler: VHC mini-pup uzun 5,52$'dan 7,55$'a (%36, 3 gün); SPY …
- **scalp__macd-sinyal**: [Ellis (Para Kazanma Yontemleri kitabi)] Yazar: MACD stratejisi 'doğru kullanıldığında %80'in üzerinde kazançlı işlem üretme yeteneğine sahip'. Kanıt, örneklem veya test sonucu sunulmuyor.
- **scalp__trend-yapi-dow**: [kitap: Price Action Scalper] Kitap: islemlerin %75-80+'inin karli olmasi beklenebilir (genel beklenti, istatistik verilmemis).
- **scalp__ardisik-bar-tukenme**: [Currency Grail kitabi] Yazar: 'kayıpsız' sistem, 'hiçbir kayıplı işlem yaşamayacaksınız'; sermayeyi bırakırsanız 'bir ay içinde hesabı ikiye katlayabilir' (kitapta yazıyor). Kanıt veya istatistik sunulmuyor. Kitap ayrıca stop ku…
- Elenen: Singhal martingale karti "zarar etmezsiniz" iddiasi (martingale zaten kesin ret).

### 4.3 Seans uyarlamasi gereken aileler

Kripto 7/24 oldugu icin "gun baslangici" UTC 00:00 alinmali (alternatif: 8 saatlik fonlama donemi); hisse/emtia perpetual'larda dayanak piyasanin acilis saati referans olmali:

- `orb` (daytrade)
- `gap-devam` (daytrade, swing) - kriptoda bosluk yok, yalnizca hisse/emtia perpetual'da anlamli
- `gap-doldurma` (daytrade, swing) - kriptoda bosluk yok, yalnizca hisse/emtia perpetual'da anlamli
- `vwap-donus` (daytrade)
- `vwap-trend` (daytrade)
- `pivot-seviye` (daytrade, swing)
- `dar-aralik-kirilim` (swing)
- Ayrica 1m-3m kaynakli kartlar (Scheier, Singhal 1dk scalp, Maza, Heikin Ashi Trader, Lama) 5m'ye uyarlanir; sabit pip/puan hedefleri ATR katsayisina cevrilmeli.

### 4.4 Ayni ailenin birden cok stilde cikmasi

- `ma-kesisim`: scalp, swing
- `ma-geri-cekilme`: scalp, daytrade, swing
- `fib-geri-cekilme`: scalp, daytrade, swing
- `gap-devam`: daytrade, swing
- `gap-doldurma`: daytrade, swing
- `pivot-seviye`: daytrade, swing
- `supertrend-psar`: scalp, swing
- `bant-donus`: scalp, daytrade, swing
- `bb-sikisma-kirilim`: scalp, daytrade, swing
- `konsolidasyon-kirilim`: scalp, daytrade, swing
- `donchian-kirilim`: daytrade, swing
- `rsi-asiri-donus`: scalp, daytrade, swing
- `rsi-momentum-esik`: scalp, swing
- `rsi-diverjans`: scalp, swing
- `stokastik-donus`: scalp, daytrade, swing
- `macd-sinyal`: scalp, swing
- `cci-esik`: scalp, swing
- `pin-bar`: daytrade, swing
- `cift-dip-tepe`: scalp, swing
- `bas-omuz`: scalp, swing
- `ucgen-dikdortgen-kirilim`: scalp, daytrade, swing
- `bayrak-flama`: daytrade, swing
- `sahte-kirilim`: scalp, daytrade, swing
- `trend-cizgisi-kanal`: daytrade, swing
- `kirilim-geri-test`: scalp, daytrade, swing
- `seviye-tepki`: scalp, daytrade, swing
- `aralik-ticareti`: scalp, daytrade, swing
- `talep-arz-bolgesi`: scalp, swing
- `trend-yapi-dow`: scalp, daytrade
- `geri-cekilme-fiyat-eylemi`: scalp, daytrade, swing
- `heikin-ashi-donus`: scalp, swing
- `ichimoku`: daytrade, swing
- `ardisik-bar-tukenme`: scalp, daytrade, swing

Bu ailelerde stil basina ayri kayit vardir; ayni mekanik farkli zaman dilimlerinde ayri strateji olarak test edilir, ama final secimde ayni ailenin 3 stilde birden "yaygin" gorunmesi bagimsiz kanit sayilmamalidir.

### 4.5 Diger notlar

- Dolayli kaynak: Graham'in mum formasyonu yuzdeleri (%68-84) Bulkowski'den aktarmadir; ayri yazar sayilmadi.
- Elenen kapali gostergelerin acik muadili varsa ilgili ailenin `elenen_kapali_muadiller` alanina not olarak baglandi (ornek: LuxAlgo -> bant-donus, YinYang/AlgoAlpha -> rsi-asiri-donus, Fibonacci Bolgesi -> fib-geri-cekilme).
- Cikis/risk modulleri (13 adet) ayri havuzdadir: iz suren stop, kademeli kar alma, min R:R, sabit R boyutu, zaman stopu vb. Her giris stratejisine takilabilir.

### 4.6 Elenen kartlar (ozet)

- Temel/olay/sektor/haber verisi: 23 kart_id
- Opsiyon: 15 kart_id
- Kapali/tescilli gosterge: 14 kart_id
- Kodlanabilirlik 0: 9 kart_id
- Genellenemeyen / forex / penny: 4 kart_id
- Level-2 / TICK / spread / sozlesmeler arasi: 2 kart_id
- Martingale: 1 kart_id

Tum liste nedenleriyle `stratejiler\elenenler.json` icindedir.

## 5. Kapsama kontrolu

**438 kartin 333'i aileye, 35'i module, 70'i elendi (toplam 438).**

(Benzersiz kart_id bazinda: 332 aile + 35 modul + 68 elenen = 435; 3 kart_id csv'de iki kez gecer: scalp__ha-renk-donusu__heikinashi (aileye), scalp__superscalp-vsa__holmes ve scalp__ultra-hacim-seviye__holmes (elenen).)