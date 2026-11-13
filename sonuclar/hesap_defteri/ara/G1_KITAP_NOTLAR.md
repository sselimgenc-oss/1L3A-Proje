# G1_KITAP NOTLAR

Betik: sonuclar/hesap_defteri/betikler/g1_kitap.py ; elle kararlar: ara/G1_KITAP_elle_kararlar.csv (263 kart). Çıktı: ara/G1_KITAP_ham.csv (810 satır).

## Kaynak satır sayısı = ham satır sayısı
Beklenen 810, üretilen 810. Tüm 137 dosyada tutuyor (dosya başına kart sayısı = satır).
Dosya sayısı: 135; 810 karttan 435 `veri/kart_dizini.csv` (438 satır, 3 kart_id tekrarı) + 372 `kitap_kartlari_eslesme.csv`; ilk 438 (3 Holmes/HA kopyası dahil) = 333 aile üyesi + 70 elenen + 35 çıkış modülü kartı. Yetim kart yok.

## eslesme dağılımı
- AYAR: 212
- BENZER: 275
- ESDEGER: 8
- KOD: 143
- TEKRAR: 2
- YOK: 170

## on_durum dağılımı
- D_KODLANMADI_NEDENLI: 402
- F_YASAK_TIP: 6
- G_ML: 4
- H_BIZIM_EVRENDE_UYGULANAMAZ: 33
- KOD: 363
- TEKRAR: 2

## Aile eşlemesi
484 satır aile id'li (KOD/AYAR/BENZER); 231 satır aile kodu tarafından uygulanıyor. Aile başına kart (en çok 15):
swing__ma-kesisim:24, scalp__ma-kesisim:19, daytrade__orb:17, scalp__bant-donus:15, swing__mum-yutan-donus:14, swing__konsolidasyon-kirilim:11, swing__trend-cizgisi-kanal:11, swing__ma-geri-cekilme:10, swing__cift-dip-tepe:9, scalp__ma-geri-cekilme:9, swing__fib-geri-cekilme:9, daytrade__donchian-kirilim:8, swing__rsi-diverjans:8, scalp__cift-dip-tepe:8, swing__ardisik-bar-tukenme:8

Yeni aile olarak kodlanan (dis__*) kart: 124 kart / 78 sınıf; 139 'yeni' kartın geri kalanı kart-bazlı BENZER (aile kodlu, varyant yok) ya da D/kural_belirsiz (elle CSV).
E_KODLANMADI_NEDENSIZ: 0 kart.

## Önemli bulgular
1. 93 kart eşleme dosyasında `ayar:X` etiketli ama `stratejiler/kart_ayarlari/` içinde bu kart_id'li kayıt YOK (kart_ayarlari'ndaki 226 kayıt tamamı aile üyesi kartlara ait). Bunlar BENZER (not: ayar_onerilen_ama_yazilmamis; sayı 93).
2. `stratejiler/ayarlar_d11j_ek.json` / `ayarlar_d12b_ek.json` hiçbir G1 kart_id'sine bağlı değil (kart_id içermiyor; hedef/ayar_id farklı yapıda).
3. Aile üyesi kartlarda kart_ayarlari kaydı olanlar eslesme=AYAR (hedef=aile id, KOD eşdeğeri; on_durum KOD). Kaydı olmayanlar KOD.
4. 'Aile kanonik kuralı kartı uygulamıyor' (aile üyesi BENZER) = 102 kart: yazar_denetimi 'yakin/farkli' (otomatik) + aile sınıfı docstring'inde 'KODLANMADI/İFADE EDİLEMEZ' (elle) + elle karşılaştırma. Liste:
   - K003:2 daytrade__stokastik-donus <- daytrade__williams-r-sma14__singhal : daytrade/stokastik_donus.py docstring: kartın "-50'ye geri dönüş" tetiği sınıfın "%K, %D'yi kesti" tetiğinden FARKLI, sınıfla ifade edilemez; kart aya
   - K003:5 swing__talep-arz-bolgesi <- daytrade__bosluk-ilk-geri-cekilme__singhal : swing/talep_arz_bolgesi.py docstring: boşluk, kodlanmadı
   - K003:9 scalp__supertrend-psar <- daytrade__supertrend-pivot-r1s1__singhal : yazar_denetimi (yakin): Supertrend ustunde ve pivot R1 kirilimi; trend donusu degil.
   - K003:13 scalp__rsi-momentum-esik <- daytrade__cift-rsi-5dk-1sa__singhal : yazar_denetimi (yakin): RSI 30 alti ve mum; 50 esigi yerine farkli tetik.
   - K003:16 scalp__talep-arz-bolgesi <- daytrade__smc-emir-blogu-adil-deger__singhal : scalp/talep_arz_bolgesi.py docstring: kodlanmadı
   - K003:18 daytrade__donchian-kirilim <- daytrade__fraktal-williams-sma50__singhal : yazar_denetimi (yakin): Williams fraktal kirilimi; Donchian kanali degil.
   - K003:20 daytrade__donchian-kirilim <- daytrade__donchian-geri-cekilme-kirilim__singhal : daytrade/donchian_kirilim.py docstring: Donchian üst banda iki temas + geri çekilme kırılımı İFADE EDİLEMEZ, kart ayarı verilmedi
   - K003:25 swing__rsi-diverjans <- daytrade__rsi-mw-pozisyonel__singhal : yazar_denetimi (yakin): RSI M ve W yapisi; uyumsuzluk degil, RSI formasyonu.
   - K003:26 scalp__supertrend-psar <- daytrade__sar-rsi-heikin-ashi-3dk__singhal : yazar_denetimi (yakin): PSAR yalniz filtre; tetik heikin ashi ve RSI.
   - K003:28 daytrade__vwap-donus <- daytrade__rsi-vwap-scalp-1dk__singhal : yazar_denetimi (yakin): VWAP destegi ve RSI; bant disi uc yok.
   - K003:30 scalp__ma-kesisim <- daytrade__ema5-7-ilk-saat-scalp__singhal : yazar_denetimi (yakin): EMA 5/7 uzun kurali acik degil; kesisim varsayimi belirsiz.
   - K003:45 scalp__ma-kesisim <- daytrade__ema9-21-kesisim-kirilim__singhal : yazar_denetimi (yakin): EMA kesisimi kirilim mumuna bagli; tetik kirilim.
   - K003:50 swing__dar-aralik-kirilim <- daytrade__vcp-minervini-daralma__singhal : swing/dar_aralik_kirilim.py docstring: Singhal VCP kartı kodlanmadı (daralma sayısı/oranı belirsiz)
   - K003:51 scalp__geri-cekilme-fiyat-eylemi <- daytrade__iki-bacakli-geri-cekilme__singhal : scalp/geri_cekilme_fiyat_eylemi.py docstring: iki bacaklı: kodlanmadı
   - K008:1 scalp__cift-dip-tepe <- daytrade__yanal-momentum-cift-dip-tepe__maza : scalp/cift_dip_tepe.py docstring: 1dk eşit tepe/dip + gün tipi/ana trend filtreleri: farklı mekanik, KODLANMAYAN
   - K008:2 scalp__cift-dip-tepe <- daytrade__geri-cekilme-cift-dip-tepe__maza : scalp/cift_dip_tepe.py docstring: 1dk eşit tepe/dip + seviye + gün tipi filtreleri: farklı mekanik, KODLANMAYAN
   - K026:1 swing__mum-yutan-donus <- daytrade__bar-inversiyon-tersine-donus__derr : swing/mum_yutan_donus.py docstring: Derr dış-bar (high/low yutma) varyantı kodlanmadı
   - K026:4 daytrade__orb <- daytrade__ilk-saat-yon-takibi__derr : yazar_denetimi (farkli): Ilk saat yonu; acilis araligi kirilimi kullanilmiyor.
   - K026:5 daytrade__trend-yapi-dow <- daytrade__trend-takibi-yukselen-dusen__derr : yazar_denetimi (yakin): Yukselen trend tanimi belirsiz; trend takibi tetigi.
   - K035:2 daytrade__kirilim-geri-test <- daytrade__sikisiklik-bolgesi__woods : yazar_denetimi (yakin): Uc mumluk sikisma bolgesi; yeniden test degil, kirilim kurulumu.
   - K035:6 daytrade__konsolidasyon-kirilim <- daytrade__basinc-bolgesi__woods : yazar_denetimi (farkli): Alt golge basinc bolgesi; konsolidasyon kirilimi degil.
   - K035:7 daytrade__sahte-kirilim <- daytrade__kaygi-bolgesi__woods : daytrade/sahte_kirilim.py docstring: öznel, kodlanmadı
   - K040:4 swing__uc-cubuklu-net-hat <- daytrade__guppy-cbl-kademeli-giris__bulkowski : swing/uc_cubuklu_net_hat.py docstring: CBL geri sayım + kademeli giriş KODLANMADI (ayrı mekanik)
   - K040:10 swing__sahte-kirilim <- daytrade__bozulmus-alcalan-ucgen__bulkowski : swing/sahte_kirilim.py docstring: üçgen sahte kırılımı kodlanmadı
   - K040:11 swing__sahte-kirilim <- daytrade__bozulmus-simetrik-ucgen__bulkowski : swing/sahte_kirilim.py docstring: üçgen sahte kırılımı kodlanmadı
   - K040:21 swing__cift-dip-tepe <- daytrade__iki-b-zirve-satis__bulkowski : elle: kart 2B tepe + önceki zirvenin altına satış limiti; swing/cift_dip_tepe.py boyun çizgisi kırılımı bekler (teyitsiz erken giriş yok)
   - K040:25 swing__konsolidasyon-kirilim <- daytrade__destek-kirilim-satis__bulkowski : elle: kart tek başına destek kapanış kırılımı satışı; swing/konsolidasyon_kirilim.py dar kutu (maks_genislik_atr) + opsiyonel hacim şartı arar
   - K040:27 swing__ma-kesisim <- daytrade__weinstein-30hma-asama-cikis__bulkowski : yazar_denetimi (yakin): Haftalik 30 MA yonu ve fiyat ustu; kesisim degil, durum filtresi.
   - K040:38 swing__goreceli-guc-momentum <- daytrade__goreceli-guc-donus-kirilim__bulkowski : swing/goreceli_guc_momentum.py docstring: RS=hisse/S&P oranı dönüşü KODLANMADI
   - K040:46 scalp__cift-dip-tepe <- daytrade__gun-ici-ucl-tepe-kisa__bulkowski : scalp/cift_dip_tepe.py docstring: üçlü formasyon KODLANMAYAN (sınıf iki pivotla çalışır)
   - K040:51 scalp__cift-dip-tepe <- daytrade__gun-ici-ucl-dip-uzun__bulkowski : scalp/cift_dip_tepe.py docstring: üçlü formasyon KODLANMAYAN (sınıf iki pivotla çalışır)
   - K047:1 scalp__stokastik-donus <- daytrade__stokastik-rsi-ema20-2dk__backus : yazar_denetimi (yakin): Stokastik kesisimi var ama asiri bolge sarti yok; RSI ek filtre.
   - K047:3 scalp__fib-geri-cekilme <- daytrade__pivot-fibonacci-cift-destek-direnc__backus : scalp/fib_geri_cekilme.py docstring: pivot+Fib çakışması + stokastik KODLANMADI
   - K047:4 scalp__bant-donus <- daytrade__keltner-dis-stokastik-asiri-satim__backus : scalp/bant_donus.py docstring: hipotez, Keltner KODLANMADI
   - K055:1 scalp__ardisik-bar-tukenme <- scalp__iki-mum-kurulumu__grail : scalp/ardisik_bar_tukenme.py docstring: iki mumlu boyut/kapanış-mesafesi koşulu ve sabit pip hedefi sınıfla İFADE EDİLEMEZ, kart ayarı verilmedi
   - K060:1 scalp__ma-kesisim <- scalp__ma3-ma7-bollinger-trend-kirilim__simvour : yazar_denetimi (yakin): MA3/MA7 kesisimi var ama tetik Bollinger sapma mumu.
   - K064:1 scalp__ma-kesisim <- scalp__linreg-5-34-cizgileri-hizala__schroder : yazar_denetimi (yakin): Regresyon cizgisi kirilimi; MA kesisimi degil.
   - K064:3 scalp__rsi-asiri-donus <- scalp__rsi-aralik-ticareti-1dk__schroder : yazar_denetimi (yakin): RSI asiri satim ve aralik alt siniri; tetik aralik.
   - K064:4 daytrade__trend-yapi-dow <- scalp__trendi-yakala-1-2-3-vwap__schroder : yazar_denetimi (yakin): Yuksek dip yapisi ve VWAP; kirilim tetigi yok.
   - K064:6 scalp__seviye-tepki <- scalp__petrol-yuvarlak-seviye-araligi__schroder : yazar_denetimi (yakin): Yuvarlak seviye aralik ticareti; tepki tetigi yok.
   - K064:7 scalp__geri-cekilme-fiyat-eylemi <- scalp__dusuk-hacimli-geri-cekilme__schroder : scalp/geri_cekilme_fiyat_eylemi.py docstring: kodlanmadı
   - K064:8 daytrade__vwap-donus <- scalp__vwap-geri-cekilme-plani__schroder : yazar_denetimi (yakin): VWAP geri cekilmesinde dip alimi; bant donusu degil.
   - K064:9 swing__ma-kesisim <- scalp__altin-hac-olum-hac-rejim__schroder : yazar_denetimi (yakin): 50/200 EMA ust uste durumu rejim filtresi; kesisim tetigi yok.
   - K070:2 scalp__konsolidasyon-kirilim <- scalp__yuvarlak-sayi-aralik-kirilimi__volman : scalp/konsolidasyon_kirilim.py docstring: yuvarlak sayı varyantı kodlanmadı
   - K070:4 scalp__konsolidasyon-kirilim <- scalp__devrilme-noktasi-arb__volman : scalp/konsolidasyon_kirilim.py docstring: iç-aralık/ARB varyantları kodlanmadı
   - K071:2 scalp__talep-arz-bolgesi <- scalp__5sma-bosluk-hacim-tuzak__christopher : scalp/talep_arz_bolgesi.py docstring: ayrı 5-SMA boşluk mantığı (NSE opsiyon hacmi), kodlanmadı
   - K076:1 scalp__ma-kesisim <- scalp__basit-trend-ma-egim__connell : yazar_denetimi (yakin): MA egimi ve fiyat-MA konumu; kesisim tetigi yok.
   - K078:3 scalp__macd-sinyal <- scalp__macd-histogram-stokastik__ellis : yazar_denetimi (yakin): Histogram ve yavas stokastik; sinyal kesisimi tetik degil.
   - K078:4 scalp__ma-kesisim <- scalp__kisa-momentum-ema8-34__ellis : yazar_denetimi (yakin): EMA8 fiyat kesisimi ve EMA konumu; MA kesisimi degil.
   - K079:4 scalp__cci-esik <- scalp__cci-zirve__busiere : yazar_denetimi (yakin): CCI dip ve donus; esik kirilimi degil, dip yapisi.
   - K083:1 scalp__stokastik-donus <- scalp__sma500-hma30-stokastik-rsi__carson : yazar_denetimi (yakin): Stokastik RSI ve HMA gecisi; tetik fiyatin HMA'yi gecmesi.
   - K083:4 scalp__rsi-momentum-esik <- scalp__triple-rsi-heikin-ashi__carson : scalp/rsi_momentum_esik.py docstring: tescilli gösterge, KODLANMADI
   - K083:5 scalp__macd-sinyal <- scalp__tsi-bjorgum__carson : yazar_denetimi (yakin): TSI cizgi caprazi; farkli gosterge, benzer caprazlama mekanigi.
   - K083:13 scalp__supertrend-psar <- scalp__halftrend-fisher-plus__carson : scalp/supertrend_psar.py docstring: HalfTrend/Fisher kodlanmadı
   - K083:15 scalp__ma-kesisim <- scalp__rsi-wma-hma__carson : yazar_denetimi (yakin): RSI ile WMA kesisimi; fiyatin HMA ustune cikmasi tetik.
   - K083:16 scalp__ma-kesisim <- scalp__mfi-hma65-sma200__carson : yazar_denetimi (yakin): Fiyatin HMA65'i mum kapanisiyla gecmesi; MFI ayri tetik.
   - K084:4 scalp__bant-donus <- scalp__rsi5-keltner-ema200__stevenson : scalp/bant_donus.py docstring: Keltner 1.5 ATR + EMA200 KODLANMADI (Keltner kanalı yok)
   - K085:10 swing__ardisik-bar-tukenme <- swing__ortalamaya-donus__ladha : swing/ardisik_bar_tukenme.py docstring: aylık dip + yeşil kapanış: ayrı mekanik, KODLANMADI
   - K087:2 swing__sahte-kirilim <- swing__trend-kanali-sahte-kirilim__heikinashi : swing/sahte_kirilim.py docstring: kanal sahte kırılımı ayrı kodlanmadı
   - K087:4 swing__cift-dip-tepe <- swing__cift-dip-tepe__heikinashi : yazar_denetimi (yakin): Cift dip ters donus mumuyla; boyun kirilimi tetik degil.
   - K095:2 swing__geri-cekilme-fiyat-eylemi <- swing__trend-knockout__landry : swing/geri_cekilme_fiyat_eylemi.py docstring: silkelenme (önceki dip altına iğne) varyantı KODLANMADI
   - K095:4 swing__geri-cekilme-fiyat-eylemi <- swing__trend-pivot-pullback__landry : swing/geri_cekilme_fiyat_eylemi.py docstring: kodlanmadı
   - K095:5 swing__geri-cekilme-fiyat-eylemi <- swing__accelerating-momentum__landry : swing/geri_cekilme_fiyat_eylemi.py docstring: kodlanmadı
   - K095:6 swing__gap-devam <- swing__explosion-gap-pivots__landry : swing/gap_devam.py docstring: 20g zirve gap + pivot-test deseni KODLANMADI
   - K095:8 swing__ma-kesisim <- swing__bow-ties__landry : yazar_denetimi (yakin): MA dizilimi ve sikisma; kesisim degil, siralama tetigi.
   - K095:9 swing__gap-doldurma <- swing__reversal-gap__landry : swing/gap_doldurma.py docstring: gap yönünde devam (doldurma değil) KODLANMADI
   - K100:3 swing__crane-reaksiyon-swing <- swing__reversal-date-stop__crane : swing/crane_reaksiyon_swing.py docstring: ters/ileri gün sayımı belirsiz ve takvim bağımlı; KODLANMADI
   - K100:4 swing__yeni-dip-sonrasi-donus <- swing__peg-leg__crane : swing/yeni_dip_sonrasi_donus.py docstring: Peg Leg (20g tepe, 3 gün kuralı) aynı çekirdeğe oturmadığı için KODLANMADI
   - K100:5 swing__gap-doldurma <- swing__gap-and-go__crane : swing/gap_doldurma.py docstring: gün1/gün2 boşluk-devam KODLANMADI
   - K100:7 swing__yeni-dip-sonrasi-donus <- swing__major-reversal__crane : swing/yeni_dip_sonrasi_donus.py docstring: Major Reversal KODLANMADI
   - K100:13 swing__rsi-diverjans <- swing__ssto-uyumsuzluk__crane : aile sınıfı docstring: SSTO uyumsuzluğu KODLANMADI (swing/rsi_diverjans.py)
   - K104:2 daytrade__trend-cizgisi-kanal <- daytrade__gun-ici-yukselen-kanal__boxer : daytrade/trend_cizgisi_kanal.py docstring: kanal çizimi içgüdüsel, kodlanamadı; yerine regresyon kanalı
   - K104:3 swing__ma-kesisim <- swing__ma-10-21-50-gecis-geri-cekilme__boxer : yazar_denetimi (yakin): MA gecisinden sonra geri cekilme tetigi; kesisim ana giris degil.
   - K104:11 swing__bant-donus <- swing__bollinger-w-m-formasyon__boxer : yazar_denetimi (yakin): W dip/M tepe formasyonu bant uzerinde; bant dokunusu tetik degil.
   - K104:12 swing__rsi-diverjans <- swing__obv-fiyat-farkliligi__boxer : aile sınıfı docstring: OBV farklılığı KODLANMADI (swing/rsi_diverjans.py)
   - K105:3 daytrade__orb <- swing__orb-eslesen-yuksek-dusuk__scheier : yazar_denetimi (yakin): ORB sinirinin basarisiz kirilimi; ters yon tetik.
   - K105:5 daytrade__gap-doldurma <- swing__bosluk-kapanisi-y-kapanis__scheier : daytrade/gap_doldurma.py docstring: boşluk yönünde giriş (dolumun tersi) ÇELİŞKİ, kodlanmadı
   - K105:6 daytrade__orb <- swing__test-reddet-2-trend__scheier : yazar_denetimi (yakin): ORB'nin tekrar test ve red sonrasi kirilim.
   - K105:7 daytrade__orb <- swing__kalici-trend-orb-geri-cekilme__scheier : yazar_denetimi (yakin): ORB'ye geri cekilme girisi; kirilim yerine pullback.
   - K105:8 scalp__stokastik-donus <- swing__stochsplit__scheier : yazar_denetimi (yakin): Stokastik ayrismasi iki zaman diliminde; bolge cikisi farkli tetik.
   - K105:10 scalp__ma-geri-cekilme <- swing__ema-cup__scheier : yazar_denetimi (yakin): 200 EMA'ya ikinci kirilim ve tutunma; geri cekilme farkli tetik.
   - K105:19 daytrade__orb <- swing__maymun-barlari-orb-geri-donus__scheier : yazar_denetimi (yakin): ORB'ye tekrarli geri donus; sayim tetigi.
   - K110:5 swing__stokastik-donus <- swing__stokastik-kesisim-80-20__jordan : swing/stokastik_donus.py docstring: trend filtresiz 80/20 kesişimi sınıfla İFADE EDİLEMEZ -> kodlanmadı
   - K110:12 swing__ma-kesisim <- swing__fiyat-hareketli-ortalama-konumu__jordan : yazar_denetimi (yakin): Fiyatin MA ustunde kalmasi; kesisim degil, konum tetigi.
   - K120:3 swing__mum-yutan-donus <- swing__karsit-desen-kisa__penn : yazar_denetimi (yakin): Karsit desen; giris tetigi ve mum tanimi belirsiz.
   - K120:4 swing__rsi-diverjans <- swing__macd-uyumsuzluk__penn : aile sınıfı docstring: MACD histogram uyumsuzluğu (yalnız short) KODLANMADI (swing/rsi_diverjans.py)
   - K120:8 swing__cift-dip-tepe <- swing__cift-dip-tepe-donus__penn : yazar_denetimi (yakin): Cift dip donusu; kirilim tetigi kitapta belirsiz.
   - K121:10 swing__ma-geri-cekilme <- swing__sma200-destek-uzun__make : yazar_denetimi (yakin): Dusus trendinde 200 SMA desteginden alim; trend ters.
   - K122:1 swing__donchian-kirilim <- swing__gann-cift-tepe-kirilim__razaq : swing/donchian_kirilim.py docstring: çift tepe formasyonu KODLANMADI
   - K122:2 swing__mum-yutan-donus <- swing__gann-dis-gun-trend__razaq : swing/mum_yutan_donus.py docstring: dış-bar (high/low yutma) varyantı kodlanmadı; sınıf gövde yutması
   - K125:2 scalp__ma-geri-cekilme <- swing__mukemmel-firtina__yu : elle: kart 60/15/5 dk üç TF mini-pup + MA yönü + 1dk stokastik; scalp/ma_geri_cekilme.py yalnız MA bölgesine geri çekilme + sıçrama mumu (çok TF/stoka
   - K126:5 swing__ma-kesisim <- swing__elder-uclu-ortalama__hogan : yazar_denetimi (yakin): MA'larin yonu (ucu de yukseliyor); kesisim tetigi yok.
   - K126:10 swing__pin-bar <- swing__cimbiz-dip-tepe__hogan : swing/pin_bar.py docstring: çımbız (iki mumlu) ayrı kodlanmadı (sınıf tek mumlu pin bar)
   - K128:2 swing__rsi-diverjans <- swing__rsi-basarisizlik-salinimi__johnson : yazar_denetimi (yakin): RSI basarisizlik salinimi; uyumsuzluk degil, RSI yapisi.
   - K128:9 swing__stokastik-donus <- swing__macd-stokastik-onay__johnson : swing/stokastik_donus.py docstring: MACD>0 + stokastik İFADE EDİLEMEZ -> kodlanmadı
   - K128:10 swing__stokastik-donus <- swing__stokastik-20-gecis__johnson : swing/stokastik_donus.py docstring: %K 20 geçişi (%D kesişimi değil) İFADE EDİLEMEZ -> kodlanmadı
   - K128:13 swing__konsolidasyon-kirilim <- swing__kirilim-hacim-onayli__johnson : yazar_denetimi (yakin): Hacim patlamasi ve fiyat artisi; konsolidasyon kirilimi sart degil.
   - K128:16 daytrade__vwap-trend <- swing__vwap-konum__johnson : yazar_denetimi (yakin): VWAP alti konum; kesisim tetigi tanimsiz.
   - K131:11 swing__macd-sinyal <- swing__macd-sifir-gecisi__graham : yazar_denetimi (yakin): Sinyal cizgisinin sifir cizgisini gecmesi; farkli cizgi kesisimi.
   - K131:19 swing__rsi-momentum-esik <- swing__rsi-70-30-secim__graham : swing/rsi_momentum_esik.py docstring: varlık seçimi 70/30, tek varlık için anlamsız, KODLANMADI
   - K135:1 daytrade__ma-geri-cekilme <- swing__sloth-psar-ema-roc__kratter : daytrade/ma_geri_cekilme.py docstring: PSAR+stokastik+ROC bileşik kurulum KODLANMADI; sınıf yalnız MA geri çekilme + sıçrama çekirdeği
   - K135:7 swing__macd-sinyal <- swing__impuls-sistemi-ema13-macd__kratter : yazar_denetimi (yakin): EMA13 yonu ve histogram rengi; MACD kesisimi tetik degil.
5. Çıkış modülü kartları: 35 eski (cikis_risk_modulleri.json) + 5 yeni (cikis_modulu) = D/cikis_modulu; modül eklenenler not'ta (cikis_modulleri_ek.csv). `trend-yonunde-ekleme-ayri-islem__brooks_r3` için modül eklenmedi (piramit).
6. Holmes ikinci PDF kopyaları (2 kart) TEKRAR; `scalp__ha-renk-donusu__heikinashi__eglencelidir` içerik farklı olduğu için TEKRAR değil, aile üyesi.
7. tam_okuma_guncelleme_ozet.csv: 43 hedef_kart_id, 4 tanesi G1 kartı değil (strateji/başka id): ['daytrade__20-bosluk-cubugu__brooks;daytrade__ilk-hareketli-ortalama-boslugu__brooks', 'daytrade__acik-trend-kucuk-geri-cekilme__brooks;daytrade__mikro-kanal-gec-giris__brooks', 'daytrade__geri-donus-gunu__brooks;daytrade__acik-trend-kucuk-geri-cekilme__brooks', 'daytrade__olculu-hareket-bacak-esitligi__brooks;daytrade__olculu-hareket-hedefi__brooks']
8. `yeni__halsey-olculu-hareket`: d10c 'kurala_dokulemez', d12a 'kodlandi' (sonraki karar esas alındı). `yeni__bladerunner-ters` hiçbir yerde kodlanmadı (D, kural_belirsiz).

## Yöntem ve sınırlar
- aile sütunu: kategori ortalamaya_donus->MR; trend_takip/kirilim/momentum->trend; diğerleri piyasa_rejimi (yatay->MR, trend->trend, kalan diger).
- mevcut:X (81 kart): yalnız çekirdeği temiz (ızgara içi, ek filtre yok) 8 kart ESDEGER; kodlanabilirliği ≤1 ya da ek koşullu olanlar BENZER (birebirlik doğrulanamadı).
- Aile üyeleri: tek kartlı 27 aile ve 3+ kartlı ailelerin her biri için sınıf docstring'i (kaynak kart listesi + 'kodlanmadı' notları) tam tarandı; ek olarak ailenin ~2 kartı için kart özeti sınıf kuralıyla elle karşılaştırıldı. sinyaller() gövdeleri her sınıfta satır satır okunmadı.
- Elenenler: neden metninden regex ile sınıflandı (betikteki `elenen()`); H/D ayrımı yaklaşık.

## Öz kontrol
Rastgele 10 satır ham_id -> kaynak JSON indeksi -> kart_id geri izlendi (aşağıdaki doğrulama betikle yapıldı):
- K050:19 scalp__5dk-sistem-20-ema3-bb-orta-macd__carter -> OK
- K026:7 daytrade__aralik-ticareti-yatay__derr -> OK
- K068:1 scalp__payapa-ema-stokastik-mtf__blanco -> OK
- K119:1 swing__stop-iz-suren-kombinasyon__mcarthur -> OK
- K003:48 daytrade__geri-cekilme-yeniden-test__singhal -> OK
- K010:4 daytrade__acilis-araligi-kirilimi__christensen -> OK
- K098:1 swing__destek-direnc-sicrama__abraham -> OK
- K015:1 daytrade__kirilim-sistemi-52h-zirve__kuepper -> OK
- K063:6 scalp__wtmo-halftrend__ferrazzi -> OK
- K105:5 swing__bosluk-kapanisi-y-kapanis__scheier -> OK
Sonuç: 10/10 doğru. Envanter dışı kaynak bulunmadı.
