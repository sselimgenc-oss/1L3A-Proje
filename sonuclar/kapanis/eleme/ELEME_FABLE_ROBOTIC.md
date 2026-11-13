# Aşama 2 (Robotic, HAM:B001) koşu listesi elemesi — bağımsız hakem (sonuç görülmeden)

Tarih: 2026-11-13. Gerçek mum verisi açılmadı, hiçbir koşu yapılmadı, `veri/` okunmadı. Kararlar yalnız `kul_k4_g9_{a,b,c}_v2.csv` içindeki kural metni (kural_tam), TF, fark/not sütunları ve aşama 1 koşu listesi (`kosu_listesi_asama1.csv` + ilgili sınıfların belge satırı) üzerinden verildi. Kapsam: karar=KOSULACAK olan 277 satır (hepsi henüz kodlanmamış). Satır satır kararlar: `eleme_asama2_robotic.csv` (kimlik, karar, gerekce_turu, gerekce, tf, aile, temsilci_mi). Ölçütler aşama 1 elemesiyle (`ELEME_FABLE.md`) aynıdır; iki yeni tür eklendi: **m** (maliyet) ve **s** (aşama 1 eşi).

## Özet

| | Önce | ÇIKAR | KOŞ |
|---|---:|---:|---:|
| Robotic KOSULACAK | 277 | 85 | 192 |

### TF'ye göre

| TF | Önce | ÇIKAR | KOŞ |
|---|---:|---:|---:|
| 5m | 165 | 68 | 97 |
| 15m | 37 | 6 | 31 |
| 30m | 9 | 3 | 6 |
| 1h | 49 | 6 | 43 |
| 4h | 13 | 1 | 12 |
| 6h | 1 | 0 | 1 |
| 1d | 3 | 1 | 2 |

### Gerekçe türüne göre ÇIKAR dağılımı

| Tür | Kayıt | 5m olan | Tahmini koşu dk |
|---|---:|---:|---:|
| c) Aynı ailenin ayar/hyperopt varyantı → temsilci | 62 | 57 | 2334 |
| s) Aşama 1'de koşulan hipotezin aynısı | 8 | 4 | 178 |
| b) Birebir/klasör kopyası (aşama 2 içinde) | 7 | 5 | 220 |
| m) Yapısal: maliyet ×2'de kazanamaz (kâr hedefi maliyet düzeyinde) | 4 | 1 | 85 |
| a) Yapısal: kapı 2 (≥200 işlem) geçilemez | 3 | 0 | 12 |
| g) Kaynak fikir değil (API gösterim dosyası) | 1 | 1 | 40 |
| Toplam | 85 | 68 | 2869 |

### Tahmini süre kazancı

- Süre modeli (kayıt başına koşu; lider beyanı "5m: 20–60 dk"): 5m 40 dk (aralık 20–60), 15m 15, 30m 8, 1h 5, 4h/6h 3, 1d 2 dk. Bu bir varsayımdır; gerçek süre ölçülmedi.
- Önce: 7520 dk ≈ 125 saat (tek çekirdek). Çıkarılan: 2869 dk ≈ 48 saat. Sonra: 4651 dk ≈ 78 saat. Kazanç ≈ %38.
- Yalnız 5m: 68 kayıt × 20–60 dk = 23–68 saat koşu süresi (tek çekirdek); 4 çekirdekte ≈ 6–17 saat duvar süresi.
- Kodlama kazancı ayrıca: 85 strateji hiç kodlanmayacak. Çıkarılanların çoğu çok kollu/uzun dosyalar (CombinedBinHCluc, CryptoFrog, NASOS, ElliotV8) olduğu için ajan kodlama + denetim yükü de yaklaşık üçte bir azalır.
- BH ailesi (aşama 2, ön kayıt ek 4): Robotic payı 277 → 192 hipotez (−%31); yalnız bu pay için en küçük p eşiği 0,10/277 = 0.000361 → 0,10/192 = 0.000521 (1.44 kat gevşer). Aynı girişin 10 hyperopt kopyasını koşmak yeni bilgi vermeden aileyi şişirirdi.

## Ölçütler (nasıl karar verildi)

**c) Aile varyantı.** Aynı yazar soyundan gelen, giriş mantığı (kollar ve koşul iskeleti) aynı olup yalnız hyperopt eşikleri / ROI tablosu / stop-trailing ayarı farklı dosyalar tek ailedir. Aile başına 1–2 temsilci; ailenin içinde gerçekten ek giriş kolu ya da ek süzgeç taşıyan alt sürümler ayrı temsilci olarak bırakıldı (bu yüzden büyük ailelerde temsilci sayısı 2'yi aşar). Temsilci seçimi sonuçtan bağımsız: (1) ailenin özgün/kanonik dosyası, (2) en kapsamlı (üst küme) sürüm, (3) farklı uç (ör. kısa ROI'li ↔ uzun çıkışlı). "HO/Hyper/Mod/tarihli kullanıcı kopyası" adlı dosyalar temsilci yapılmadı.

**b) Kopya.** Kural metni birebir aynı ya da aynı dosyanın `AIRA - open code v2/` klasöründeki kopyası.

**s) Aşama 1 eşi.** Aşama 1 koşu listesindeki sınıfın belge satırı ile giriş + çıkış + ROI + stop + TF birebir eşleşenler (Robotic deposu freqtrade-strategies dosyalarını da içeriyor; 906 listesi aynı dosyaları ayrıca vermişti). Eş kimlik gerekçede yazılı.

**m) Maliyet.** Maliyet ×2 gidiş-dönüş = 2 × [2 × komisyon %0,05 + 2 × kayma %0,02–0,05] ≈ %0,28 (BTC/ETH) – %0,40 (ince semboller) (`maliyet_tablosu.csv`). Yalnız kural metni kâr hedefini bu düzeye sabitliyorsa (ROI {0: 0} ya da {0: 0,003} gibi) ÇIKAR. "5m'de maliyet zorlar" beklentisi tek başına gerekçe yapılmadı.

**a) İşlem sayısı.** Aşama 1'deki kaba hesap (≈70 sembol-yıl; 200 işlem = yılda ≥2,9/sembol). Yalnız 3 kayıt: 1d altın çapraz ve 1h Bollinger 4σ (cebirsel sınır).

**Dokunulmayanlar.** Farklı giriş mantığı olan her dosya KOŞ (5m dahil). emin_degil tek başına gerekçe yapılmadı. Aynı kuralın farklı TF'leri (ör. BBRSI 4h ↔ 15m, FrostAura 15m ↔ 1h, OmaGann 1h ↔ 30m) ön kayıt gereği ayrı hipotez sayılıp bırakıldı.

## Aile listesi ve temsilci seçimi

| Aile | Üye | KOŞ (temsilci) | ÇIKAR | Seçim ölçütü |
|---|---:|---|---|---|
| EWO-ofset A (Elliot) | 20 | 105, 221, 558, 561, 666, 673, 694 | 67, 559, 560, 562, 563, 592, 690, 692, 693, 695, 696, 697, 698 | Şablon: kapanış<EMA×ofset + (EWO>eşik ve RSI<x | EWO<eşik); çıkış kapanış>EMA×ofset. 561 kanonik (ElliotV5HO), 558 yavaş çıkış ucu, 694 SMAOffsetProtectOpt kolunun kanonik V1'i (kısa ROI ucu). 673 (RSI'siz Lite), 666 (çoklu MA), 221 (long+short), 105 (1h) ek mantık/TF taşıdığı için kaldı. |
| CombinedBinHCluc | 16 | 442, 446, 449, 451, 454, 459 | 443, 447, 448, 450, 453, 455, 456, 457, 458, 460 | Her alt sürüm grubundan bir dosya: 442 (2021, sabit stop), 446 (1h go_long süzgeci), 449 (V3–V5 grubu), 451 (V6: 3 kol), 454 (V8: 5 kol), 459 (MAD kollu). Ara sürümler ve Hyper/XH/XHO çıktı. |
| EWO-ofset C (NASOS) | 13 | 571, 573, 574, 590, 670 | 572, 575, 576, 591, 669, 671, 672, 740 | 3 kollu (ewo1/ewo2/ewolow). 670 özgün dosya; 573 pump süzgeci + basamaklı stop; 574 farklı EWO tanımı (5/35); 571 (5 kol: +clucHA, +zema) ve 590 (trend değiştiren kollar) ek kol taşıdığı için kaldı. |
| EWO-ofset B (ElliotV8) | 11 | 564, 570 | 103, 565, 566, 567, 568, 674, 675, 676, 677 | Şablon A + RSI4<35 + yüksek-ofset süzgeci, HMA50'li iki dallı çıkış. 570 kanonik Elliotv8; 564 ek 1h trend süzgeci. |
| BbandRsi-5m | 9 | 469, 470, 506, 533 | 465, 471, 480, 486, 496 | 5m "kapanış < BB alt (+RSI eşiği)". 533 kanonik (RSI<30), 470 RSI'siz 2σ, 469 3σ, 506 farklı çıkış fikri. 480 maliyet (m) ile çıktı. |
| CryptoFrog | 8 | 846, 847 | 848, 849, 850, 851, 852, 853 | 8 dosyada giriş/çıkış sinyali aynı; yalnız ROI/stop/trailing. 846 özgün, 847 ilk hyperopt. |
| ichiV1-30m | 5 | 136, 138 | 137, 139, 140 | 138 varsayılan, 136 farklı EMA yelpazesi + zaman çıkışı. (5m sürümü 642 ayrı TF, kaldı.) |
| BB_RPB_TSL | 5 | 395, 399, 406 | 396, 398 | 395 taban, 406 eski sürüm (farklı süzgeç/çıkış), 399 ek vwap kolu. |
| ClucHAnix | 4 | 434, 440, 547 | 435 | 434 taban, 440 hhll sürümü, 547 ek lambo kolu. |
| StarRise | 3 | 52, 54 | 53 | 52 (V3 + JSON) ve 54 (sabit sınıf parametreleri); 53 aynı sınıfın ikinci JSON seti. |
| AngleWave | 3 | 69, 156 | 68 | 69 (CT, üst küme) 5m; 156 15m sürümü. |
| E0V1E | 3 | 205, 206 | 204 | 206 tam sürüm, 205 farklı eşik seti; 204'te koşullar yorum satırı. |
| sample_strategy | 3 | 230, 820 | 861 | İki kopyadan biri (gerekçe CSV'de). |
| lw_tdw_tdm | 3 | 250 | 248, 249 | 250 (geniş tablo). 249 maliyet/al-tut (m) ile çıktı. |
| Tema-BB | 3 | 527, 528 | 524 | 527 (sinyal çıkışlı) ve 528 (1σ + CMO50). |
| eltoro | 2 | 755 | 201 | İki kopyadan biri (gerekçe CSV'de). |
| mk4 | 2 | 227 | 226 | İki kopyadan biri (gerekçe CSV'de). |
| ForexRobootSuperScalper | 2 | 828 | 233 | İki kopyadan biri (gerekçe CSV'de). |
| MarketCypher | 2 | 251 | 900 | İki kopyadan biri (gerekçe CSV'de). |
| BB4σ-1h | 2 | — | 532, 792 | İki kopyadan biri (gerekçe CSV'de). |
| Strategy001 | 2 | — | 545, 613 | İki kopyadan biri (gerekçe CSV'de). |
| NFI V1/V2 | 2 | 723 | 722 | İki kopyadan biri (gerekçe CSV'de). |
| MACD-RSI200 | 2 | 814 | 779 | İki kopyadan biri (gerekçe CSV'de). |
| flawless_lambo-5m | 2 | 871 | 872 | İki kopyadan biri (gerekçe CSV'de). |

## ÇIKAR listesi (türe göre)

### s) Aşama 1'de koşulan hipotezin aynısı — 8 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:545 | 5m | Seb.py | Aşama 1'de koşulan HAM:X005:19#v1 (kapanis__ha-ema-s0019, 5m) ile birebir: EMA20×EMA50 + HA, aynı çıkış, aynı ROI {5/4/3/1}, stop −%10. |
| B001:613 | 5m | Strategy001_custom_sell.py | HAM:X005:19#v1 ile aynı giriş/çıkış/ROI/stop; tek fark ek custom_exit (RSI>70 ve kârda) — yakın kopya. |
| B001:624 | 4h | Ichimoku_SenkouSpanCross.py | Aşama 1'de koşulan HAM:X005:556#v1 (kapanis__ichimoku-senkou-s0556, 4h) ile birebir: Ichimoku 20/60/120/30 Senkou A×B kesişimi, %45/%50 iz stop. |
| B001:763 | 1h | AwesomeMacd__2.py | Aşama 1'de koşulan HAM:X005:549#v1 (kapanis__macd-ao-roi-s0549, 1h) ile birebir: MACD>0 + AO sıfır kesişimi, ROI %10, stop %25. |
| B001:793 | 1h | RSIDirectionalWithTrend.py | Aşama 1'de koşulan HAM:X005:574#v1 (kapanis__rsi4-ema100-s0574, 1h) ile birebir: RSI4 15/85 kesişimi + EMA100, stop %10 iz süren. |
| B001:823 | 5m | Strategy003.py | Aşama 1'de koşulan HAM:X005:21#v1 (kapanis__ft-strategy003-s0021, 5m) ile birebir (aynı eşikler, ROI, stop). |
| B001:824 | 5m | Strategy004.py | Aşama 1'de koşulan HAM:X005:573#v1 (kapanis__ft-strategy004-s0573, 5m) ile birebir (aynı eşikler, ROI, stop). |
| B001:826 | 1h | FastSupertrend.py | Aşama 1'de koşulan HAM:X005:28#v1 (kapanis__uc-supertrend-s0028, 1h) ile birebir: aynı 3+3 Supertrend parametreleri, ROI, stop −%26,5, trailing. |

### m) Yapısal: maliyet ×2'de kazanamaz (kâr hedefi maliyet düzeyinde) — 4 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:249 | 15m | lw_tdw_tdm_btc_v1.py | Her gün 00:00'da al, 23:00'te sat (süzgeç yok) = al-tut eksi günde 1 saat eksi her gün gidiş-dönüş maliyet ×2 (≈%0,28–0,40/gün ≈ yılda %100+). Kapı 5 (al-tut Sharpe'ını aşmak) yapısal olarak olanaksız. |
| B001:467 | 15m | BBRSI4cust.py | ROI {0:0.003}: kâr hedefi %0,3 = maliyet ×2 gidiş-dönüş (%0,28–0,40) düzeyinde; kazananların neti ≤ ~0, zarar tarafı −%10 stop → net>0 yapısal olarak olanaksız. |
| B001:480 | 5m | BBandsRSI.py | ROI {0:0.0}: her kârlı işlem brüt ~%0'da kapanır, maliyet ×2 (gidiş-dönüş ≈ %0,28–0,40) altında net kazanç yapısal olarak olanaksız; zarar tarafı −%15 stop / RSI>70. |
| B001:622 | 15m | Ichi.py | ROI tablosu ilk 15 dk sonrası ≤%0,25, 60 dk sonra %0 (herhangi bir kârda çık); sinyal çıkışı yok, stop −%20. Kazananlar yapısal olarak maliyet ×2 (≈%0,28–0,40) düzeyinde/altında, kayıplar −%20 → net>0 ve PF≥1,2 olanaksız. |

### a) Yapısal: kapı 2 (≥200 işlem) geçilemez — 3 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:532 | 1h | bb_rsi_opt.py | 1h kapanış < BB(20, 4σ) alt bandı: n=20 pencerede en büyük olası z = √19 ≈ 4,36; z ≤ −4 için son kapanışın önceki 19 barın ortalamasından ≥ 10,3 standart sapma aşağıda olması gerekir (cebirsel). Yılda ~1 olay/sembol → ~70 işlem; kapı 2 geçilemez. |
| B001:776 | 1d | MAC.py | 1d EMA50/200 altın çapraz: yılda ~1/sembol → ~70 işlem (kapı 2 geçilemez); aşama 1 elemesinde X005:307#a2 aynı kural aynı gerekçeyle çıkarıldı. |
| B001:792 | 1h | RSIBB02.py | 532 ile aynı giriş (1h kapanış < BB(20,4σ) alt; yalnız RSI>19 ↔ >28): aynı cebirsel sınır (≥10,3σ sapma) → ~70 işlem; kapı 2 geçilemez. |

### g) Kaynak fikir değil (API gösterim dosyası) — 1 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:537 | 5m | custom_sell.py | Kaynak "custom_sell" API gösterim dosyası: giriş "kapanış>Keltner orta" (barların ~yarısı), çıkış koşulsuz sonraki mum → 1 mumluk 5m tutma; fikir değil, ayrıca tek 5m mumun tipik hareketi maliyet ×2'nin altında. |

### b) Birebir/klasör kopyası (aşama 2 içinde) — 7 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:67 | 5m | el.py | 221 (rsi-momentum/el.py) ile aynı strateji: aynı eşikler (EMA12×0,915; 4,428/−12,383; RSI<44; short EMA72×1,008); temsilci 221. |
| B001:103 | 5m | V8ichi.py | 567 ile birebir aynı kural (giriş, çıkış, ROI, stop, trailing); o da 570 ile temsil ediliyor. |
| B001:201 | 15m | eltoro1_4_simple.py | 755 ile aynı dosyanın (eltoro1_4_simple.py) AIRA klasöründeki kopyası; temsilci 755. Not: kodlayıcı iki dosyayı/JSON'u karşılaştırsın, fark çıkarsa geri alınır. |
| B001:233 | 5m | ForexRobootSuperScalper.py | 828 ile aynı dosyanın AIRA klasöründeki kopyası (aynı giriş/çıkış/TP); temsilci 828. |
| B001:698 | 5m | SMAOffsetProtectOptV1_kkeue_20210619.py | 697 ile birebir aynı kural metni (giriş, çıkış, ROI, stop); o da 694 ile temsil ediliyor. |
| B001:861 | 5m | Martin.py | 230 (sample_strategy) ile birebir aynı kural (RSI 30 kesişimi + TEMA9 ≤ BB orta + TEMA yükseliyor; aynı çıkış, ROI, stop). |
| B001:900 | 1h | MarketChyperHyperStrategy.py | 251 ile aynı strateji (aynı rejim eşikleri −37/−28/−43 ve ağırlıklar 96/5/91); klasör kopyası; temsilci 251. |

### c) Aynı ailenin ayar/hyperopt varyantı → temsilci — 62 kayıt

| Kimlik | TF | Dosya | Gerekçe |
|---|---|---|---|
| B001:53 | 5m | StarRise_V3__2.py | 52 ile aynı sınıf/yapı, yalnız JSON hyperopt seti farklı; temsilci 52 (V3) ve 54 (sabit sınıf parametreleri). |
| B001:68 | 5m | AngleWave.py | 69 (AngleWaveCT) aynı etkin değerler + ATR-uyarlamalı bant ve 2 ek kol (üst küme); temsilci 69 (5m) ve 156 (15m). |
| B001:137 | 30m | ichiV1__2.py | 138 ile aynı giriş (yalnız kaydırma 3↔1 ve yalnız-kârda bayrağı); temsilci 138. |
| B001:139 | 30m | ichiV1__4.py | 138 ile aynı giriş, çıkış göstergesi EMA24→EMA3; temsilci 138. |
| B001:140 | 30m | ichiV1__5.py | 138 ile aynı giriş ve çıkış (yalnız ROI/stop ayarı); temsilci 138. |
| B001:204 | 5m | E0V1E.py | Giriş koşullarının çoğu kaynakta yorum satırı (fiilen yalnız RSI4<40): ailenin bozuk/eksik kopyası; temsilci 206 (tam sürüm) ve 205. |
| B001:226 | 15m | mk4.py | 227 ile aynı kod; farkı kaynak hatası (short kolu enter_long sütununa yazılmış); temsilci 227 (doğru sürüm). |
| B001:248 | 15m | lw_tdw_tdm_btc_eth_v1.py | 250 ile aynı kural; (hafta günü:ay günü) tablosu 250'nin alt kümesi (32 ↔ 38 çift); temsilci 250. |
| B001:396 | 5m | BB_RPB_TSL_RNG_2.py | 395 ile giriş birebir aynı, yalnız çıkış parametreleri farklı; temsilci 395. |
| B001:398 | 5m | BB_RPB_TSL_RNG_TBS_G.py | 395'ten tek fark stoploss −0,049; temsilci 395. |
| B001:435 | 5m | ClucHAnix_5m1.py | 434 ile yalnız pHSL (−0,10 ↔ −0,35) farkı; temsilci 434. |
| B001:443 | 5m | CombinedBinHAndCluc2021Bull.py | 442 ile yalnız ROI farkı (tek kademe %1); temsilci 442. |
| B001:447 | 5m | CombinedBinHAndClucV3.py | V3: 449 (V5) ile aynı iki kol; yalnız ROI/trailing/zaman-stop ayarı; temsilci 449. |
| B001:448 | 5m | CombinedBinHAndClucV4.py | V4: 449 (V5) ile aynı iki kol; yalnız ROI ayarı; temsilci 449. |
| B001:450 | 5m | CombinedBinHAndClucV5Hyperoptable.py | V5Hyperoptable: 449 ile aynı, bir eşik (bbdelta 0,0175) farklı; temsilci 449. |
| B001:453 | 5m | CombinedBinHAndClucV7.py | V7: V6 (451) ile V8 (454) arası ara sürüm (4 kol, V8'in alt kümesi); temsilci 451/454. |
| B001:455 | 5m | CombinedBinHAndClucV8Hyper.py | V8Hyper: 454 ile aynı 5 kol, hyperopt eşik/ROI/stop farkı; temsilci 454. |
| B001:456 | 5m | CombinedBinHAndClucV8XH.py | V8XH: 454 ile aynı 5 kol, eşik farkı; temsilci 454. |
| B001:457 | 5m | CombinedBinHAndClucV8XHO.py | V8XHO: 456 ile aynı, birkaç eşik farkı; temsilci 454. |
| B001:458 | 5m | CombinedBinHClucAndMADV3.py | MADV3: kolları 451 (BinH kolu birebir) ve 459 (MAD kolu) içinde zaten var; ara sürüm; temsilci 459. |
| B001:460 | 5m | CombinedBinHClucAndMADV6.py | MADV6: 459 ile aynı 5 kol, küçük eşik/süzgeç farkı; temsilci 459. |
| B001:465 | 5m | BBRSI21.py | Aynı şablon, RSI<21 eşik varyantı (çıkış RSI>99 fiilen yok → ROI); temsilci 533. |
| B001:471 | 5m | BBRSIOptimizedStrategy.py | 469 ile aynı giriş (kapanış<BB 3σ alt), çıkışta yalnız RSI>64 eki ve ROI farkı; temsilci 469. |
| B001:486 | 5m | BbandRsiRolling.py | Aynı şablon; min(RSI,8)<37 koşulu alt bant altında fiilen bağlamaz → 470 ile aynı giriş, yalnız ROI tablosu farklı; temsilci 470. |
| B001:496 | 5m | DD.py | 5m "kapanış<BB(20,2) alt + RSI eşiği" şablonunun hyperopt varyantı (RSI<40, çıkış üst bant); temsilci 533. |
| B001:524 | 5m | TemaMaster.py | 527 ile neredeyse aynı giriş (TEMA18 x BB alt; 26/1,4σ ↔ 25/1,5σ; aynı CMO14>−5, aynı ROI); temsilci 527 (sinyal çıkışı olan). |
| B001:559 | 5m | ElliotV4.py | Şablon A varyantı (EMA14×0,983, sinyal çıkışı kapalı); temsilci 561. |
| B001:560 | 5m | ElliotV531.py | 561 ile giriş birebir aynı (EMA11×0,979; EWO 2,337/−15,87); yalnız çıkış/ROI ayarı farklı; temsilci 561. |
| B001:562 | 5m | ElliotV5HOMod2.py | Şablon A varyantı (EMA17×0,978); temsilci 561. |
| B001:563 | 5m | ElliotV5HOMod3.py | 562 ile aynı giriş, çıkış ayarı farklı; temsilci 561. |
| B001:565 | 5m | ElliotV8HO.py | V8 şablonunun hyperopt varyantı (EMA19×0,983); temsilci 570. |
| B001:566 | 5m | ElliotV8_original.py | 570 ile giriş/çıkış birebir; yalnız ROI ilk kademe ve yalnız-kârda bayrağı; temsilci 570. |
| B001:567 | 5m | ElliotV8_original_ichiv2.py | V8 şablonunun eşik varyantı (EMA12×0,987); temsilci 570. |
| B001:568 | 5m | ElliotV8_original_ichiv3.py | 567 ile aynı, yalnız ROI'ye 200 dk zaman çıkışı eki; temsilci 570. |
| B001:572 | 5m | NASOSv4.py | NASOSv5'in önceki sürümü, eşik/pencere farkı; temsilci 573. |
| B001:575 | 5m | NASOSv5_mod2.py | 574 ile aynı giriş/çıkış, EWO katsayısı ve küçük ek süzgeç farkı; temsilci 574. |
| B001:576 | 5m | NASOSv5_mod3.py | 575 ile aynı metin; temsilci 574. |
| B001:591 | 5m | RalliV1_disable56.py | 590'ın bazı kolları kapalı alt kümesi; temsilci 590. |
| B001:592 | 5m | bestV2.py | Şablon A'nın hyperopt varyantı (EMA31×0,978; 558 ile aynı giriş iskeleti, eşik farkı); temsilci 558/561. |
| B001:669 | 5m | NotAnotherSMAOffSetStrategy_V2.py | 670 + hacim süzgeci ve ofset 0,991→0,998; temsilci 670. |
| B001:671 | 5m | NotAnotherSMAOffsetStrategyHO.py | 670 ile aynı 3 kollu yapı, yalnız hyperopt değerleri farklı (kaynak notu da böyle); temsilci 670. |
| B001:672 | 5m | NotAnotherSMAOffsetStrategyHOv3.py | 670 ile aynı 3 kollu yapı, yalnız hyperopt değerleri farklı; temsilci 670. |
| B001:674 | 5m | NotAnotherSMAOffsetStrategyModHO.py | V8 şablonunun hyperopt varyantı (EMA10×0,984 / EMA6×1,002); temsilci 570. |
| B001:675 | 5m | NotAnotherSMAOffsetStrategyModHO_LamineDz_20210901.py | 674 ile giriş/çıkış birebir, yalnız stop ayarı; temsilci 570. |
| B001:676 | 5m | NotAnotherSMAOffsetStrategyX1.py | 570 ile giriş ve çıkış sinyali birebir aynı (yalnız EWO paydası low ve kâr basamaklı stop); temsilci 570. |
| B001:677 | 5m | NotAnotherSMAOffsetStrategy_uzi.py | V8 girişinin yüksek-ofset süzgeçsiz hali, çıkış/stop ayarı farklı; temsilci 570. |
| B001:690 | 5m | SMAOPv1_TTF.py | 694 ile giriş birebir aynı; yalnız ek TTF çıkışı ve ROI yok; temsilci 694. |
| B001:692 | 5m | SMAOffsetProtectOpt.py | Şablon A'nın SMAOffsetProtectOpt varyantı (EMA20×0,975); temsilci 694. |
| B001:693 | 5m | SMAOffsetProtectOptV0.py | 692 ile aynı giriş, çıkış/ROI ayarı farklı; temsilci 694. |
| B001:695 | 5m | SMAOffsetProtectOptV1HO1.py | Şablon A hyperopt varyantı (EMA17×0,98); temsilci 694. |
| B001:696 | 5m | SMAOffsetProtectOptV1Mod.py | 697/698 ile aynı giriş, ROI tablosu farklı; temsilci 694. |
| B001:697 | 5m | SMAOffsetProtectOptV1Mod2.py | Şablon A hyperopt varyantı (EMA16×0,973); temsilci 694. |
| B001:722 | 5m | NostalgiaForInfinityV1.py | 723 ile aynı 3 giriş kolu, yalnız eşikler farklı; ayrıca V1 göstergeleri doğrulanmamış (emin_degil); temsilci 723. |
| B001:740 | 5m | NASOSv5_mod1_DanMod.py | 574 (NASOSv5_mod1) ile aynı eşikler; yalnız ewo1 koluna VWAP/düşüş süzgeci ve RSI periyodu farkı; temsilci 574. |
| B001:779 | 5m | MACDRSI200.py | 814 ile birebir aynı kural, yalnız MACD periyotları (24,56,6 ↔ 12,26,9); ROI/stop aynı; temsilci 814 (standart MACD). |
| B001:848 | 5m | CryptoFrogHO2.py | 847 ile birebir aynı metin (giriş, çıkış, ROI, stop); temsilci 847. |
| B001:849 | 5m | CryptoFrogHO2A.py | Giriş/çıkış sinyali 846 ile aynı; yalnız trailing ayarı; temsilci 847. |
| B001:850 | 5m | CryptoFrogHO3A1.py | Giriş/çıkış sinyali 846 ile aynı; yalnız ROI/stop/trailing hyperopt değerleri; temsilci 846/847. |
| B001:851 | 5m | CryptoFrogHO3A2.py | Giriş/çıkış sinyali 846 ile aynı; yalnız ROI/stop/trailing hyperopt değerleri; temsilci 846/847. |
| B001:852 | 5m | CryptoFrogHO3A3.py | Giriş/çıkış sinyali 846 ile aynı; yalnız ROI/stop/trailing hyperopt değerleri; temsilci 846/847. |
| B001:853 | 5m | CryptoFrogHO3A4.py | Giriş/çıkış sinyali 846 ile aynı; yalnız ROI/stop/trailing hyperopt değerleri; temsilci 846/847. |
| B001:872 | 5m | lambo_testing.py | 871 ile aynı giriş, ROI ve stop; yalnız çıkış ifadesinde parantez/öncelik farkı; temsilci 871. |

## Keyfî kalan yerler (dürüst not)

1. **Aile sınırı.** "EWO-ofset" soyunu üç alt şablona (A/B/C) böldüm ve toplam 44 dosyadan 14'ünü bıraktım. Tek aile sayıp 2–3 temsilciyle yetinmek de savunulabilirdi (≈11 kayıt daha kazanırdı); kol/süzgeç farkı olanları "emin değilsen KOŞ" kuralıyla tuttum.
2. **Temsilci seçimi.** 561/558/694, 570/564, 670/573/574, 449/451/454/459, 846/847 seçimleri sonuçtan bağımsız ama zorunlu olarak keyfî (kanonik dosya adı, üst küme sürüm, farklı uç). Başka temsilci de savunulabilir.
3. **BbandRsi-5m.** 496 (RSI<40, çıkış üst bant) ve 465 (RSI<21) "eşik varyantı" sayıldı; RSI eşiği işlem kümesini belirgin değiştirir, yani bunlar birebir kopya değil, aynı şablonun hyperopt çıktılarıdır.
4. **m türü.** 622 (Ichi 15m) için ilk 15 dakikada %0,5–1 ROI kademesi var; çıkarma gerekçesi "kazançların büyük kısmı ≤%0,25, kayıp −%20" asimetrisidir, katı bir imkânsızlık değil. 249'da gerekçe kapı 5'tir (al-tut eksi maliyet).
5. **a türü (532, 792).** Cebirsel sınır kesin (≥10,3σ sapma şart); "yılda ~1/sembol" sıklığı ise tahmindir. 1h olduğu için süre etkisi küçük (10 dk); istenirse geri alınabilir.
6. **s türü.** 613, aşama 1 eşinden (X005:19) tek bir ek çıkışla ayrılıyor; 545 birebir.
7. **Klasör kopyaları (201, 233, 900, 67).** Kural metinleri iki ayrı çıkarıcıdan geldiği için küçük anlatım farkları var (ör. 67'de EWO EMA50/200, 221'de SMA5/35 yazıyor). Eşikler üç ondalığa kadar aynı olduğundan kopya saydım; kodlayıcı temsilci dosyayı açarken diğer kopyayla diff alıp fark varsa geri eklemeli.

## En tartışmalı kararlar

1. **CombinedBinHCluc 16 → 6 ve EWO-ofset 44 → 14 (c).** En büyük süre kazancı burada (40 × 5m); ara sürümlerin (V7, MADV3, NASOSv4, ModHO) temsilcilerle "aynı fikir" olduğu yargısına dayanıyor.
2. **CryptoFrog 8 → 2 (c).** Sinyaller birebir aynı; fark yalnız ROI/stop/trailing. Ancak bu ailede çıkış (dinamik ROI, özel stop) getiriyi sinyal kadar belirler; 6 kayıt × 5m.
3. **249 ve 622 (m), 532/792 (a).** Kural metninden çıkarım güçlü ama "kesin imkânsız" değil; toplam 4 kayıt, süre etkisi ~40 dk. Kullanıcı "kanıtsız hiçbir şey çıkmasın" derse ilk geri alınacaklar.

## KOŞ kalıp dikkat isteyenler

| Kimlik | Not |
|---|---|
| B001:828 | Kâr hedefi 1×ATR(10) (5m): tipik 5m ATR maliyet ×2 düzeyinde; metinden kesin çıkmadığı için kaldı. |
| B001:136 | ROI {0: %1, 30 dk: %0,2, 60 dk: zorunlu çıkış}: 30 dk sonrası kademe maliyetin altında; ilk kademe %1 olduğu için kaldı. |
| B001:800, 812, 762 | Çok sıkı stop/ROI (stop %0,7–1,6): maliyete duyarlı ama yapısal imkânsızlık yok. |
| B001:744, 816, 515 | Durum koşulu neredeyse her mumda doğru (sürekli pozisyon); işlem sayısı sorun değil, maliyet yükü yüksek. |
| B001:801, 656, 810, 529 | Nadir birleşim; 200 işlem sınırda olabilir, hesaplanamadığı için kaldı. |
| B001:482 | Aşama 1 X005:265 (SMA5/20, 1d) ile yakın (EMA5 × BB orta); çıkış "yalnız kârda" olduğu için ayrı sayıldı. |
| B001:380 | Aşama 1 X005:366#v1 (4h MACD kesişimi) ile yakın; ek SMA5/8 kolu ve farklı çıkış nedeniyle kaldı. |
| B001:463 / 473, 502 / 503, 504 / 505, 707 / 708 | Aynı kuralın iki TF'si; ön kayıt gereği iki hipotez. Daha sert budama istenirse ikinci dalga adayı. |
| B001:634, 635, 636; 804, 805, 806; 542, 543 | Aynı yazarın ardışık sürümleri ama her biri ek süzgeç/TF taşıyor; 1h olanlar ucuz. |

## Uygulama notları

- Eleme, aşama 2 koşu listesi dondurulmadan uygulanmalı; ÇIKAR kayıtlar koşulmaz ve BH ailesine girmez (ön kayıt ek 4'teki aşama 1 kuralının aynısı; aşama 2 için ön kayda bir satırla işlenmesi gerekir — karar kullanıcı/lider).
- Temsilci başka nedenle düşerse (kodlanamadı, lookahead çıktı vb.) ailesinden bir ÇIKAR kaydı geri alınmalı; temsilci kimlikleri CSV gerekçesinde yazılı.
- "s" türünde eş kimlik aşama 1'de zaten koşulduğu için sonuç oradan okunur; aşama 2'de ikinci kez hipotez sayılmaz.
- COK_KOLLU (87), VERI_YOK, LOOKAHEAD vb. satırlar kapsam dışıdır; bu rapor yalnız 277 KOSULACAK satırını kapsar.
