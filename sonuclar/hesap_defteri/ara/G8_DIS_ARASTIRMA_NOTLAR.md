# G8_DIS_ARASTIRMA notlar

Üretici: `sonuclar/hesap_defteri/betikler/g8_dis_arastirma.py`; elle verilen kararlar: `ara/G8_DIS_ARASTIRMA_elle_kararlar.csv`.

## Kaynak sayıları
- X005 `ajan1/strateji_listesi.csv` (dal): 906 veri satırı -> 906 ham satır (hiçbiri atlanmadı).
- X008 `ajan2/derin_arastirma_26_kayit_raporu.md`: 26 kayıt iddia ediliyor, CSV yok; metinden AYIRT EDİLEBİLEN 17 strateji çıkarıldı (kalan ~9 kayıt anlatımda adlandırılmamış, sayı olarak da yok). Linkleri anlatımda yok (citeturn etiketleri), bu yüzden 906 listesiyle eşleme yalnız isimden/mantıktan: 3 TEKRAR (Strategy001->S0019, Strategy002->S0020, Triple Supertrend->S0278; isim eşliği, emin değilim), 1 ESDEGER (Donchian 20/10 2xATR = sınıf varsayılanı), diğerleri BENZER/YOK doğrulanamadı. Aynı satır numaralı paragraftan birden çok strateji: ham_id `X008:L13#1` biçiminde.
- Toplam ham satır: 923.

## Dağılımlar
eslesme: BENZER=480, ESDEGER=57, TEKRAR=3, YOK=383
on_durum: BELIRSIZ=16, D_KODLANMADI_NEDENLI=570, E_KODLANMADI_NEDENSIZ=29, F_YASAK_TIP=28, H_BIZIM_EVRENDE_UYGULANAMAZ=220, KOD=57, TEKRAR=3

## Karşılaştırma dosyaları tutarlılığı
main `sonuclar/dis_arastirma/.../karsilastirma/` {karsilastirma.csv, arsiv_envanteri.csv, fikir_grubu_ozeti.csv, RAPOR.md} dal kopyasıyla bayt bayt AYNI (cmp). Karşılaştırma yalnız ilk 707 satırı kapsar; S0708-S0906 yalnız dalda (`tur4_degerlendirme/yeni_199.csv`).

## Önceki ajan kararlarının doğrulaması
Hiçbir S0xxx id'si kodlama_* dosyalarında / motor docstring'lerinde geçmiyor (kontrol edildi); dolayısıyla KOD/AYAR yok. Not: 38 satırın linki repoda başka kaynaklarda (v3_adaylar, on_eleme, repo_kodlari...) geçiyor; ilgili satırların `not` sütununda yazıldı (bu satırların başka gruplarda kodlanmış olma ihtimali o grupların işi).
- Kodla açıp ESDEGER/BENZER doğruladığım satır: 174 (ZATEN_TEST + FARK_ONEMSIZ adayları: 196 kullanılabilir adaydan 162 doğrulandı).
- Önceki ajan "ZATEN_TEST/FARK_ONEMSIZ" (=aynı) demişti; benim sonucum: ESDEGER_SAYILIR->BENZER: 118, ESDEGER_SAYILIR->ESDEGER: 56.
- Doğrulanıp ONAYLANAN (ESDEGER): 56; FARKLI karar verdiğim (önceki "aynı" -> ben BENZER): 118.
  Ölçüt: parametre çifti ızgara/ayar kümesi ya da ızgara aralığı (±%15) içinde değilse; kaynakta sınıfta olmayan filtre/TP/zaman-iz çıkışı/bant/MTF/TF varsa; sınıf kural tetiği farklıysa (örn. bant dışı kapanış vs bant içine dönüş) BENZER.
  Farklı karar liste: S0001, S0010, S0011, S0017, S0018, S0024, S0027, S0030, S0036, S0037, S0043, S0047, S0049, S0052, S0054, S0055, S0071, S0081, S0083, S0093, S0105, S0107, S0114, S0115, S0119, S0128, S0144, S0145, S0157, S0173, S0184, S0188, S0193, S0199, S0213, S0216, S0219, S0234, S0237, S0242, S0247, S0251, S0254, S0257, S0264, S0268, S0269, S0288, S0290, S0299, S0304, S0306, S0313, S0316, S0332, S0342, S0346, S0347, S0348, S0350, S0354, S0358, S0364, S0367, S0369, S0371, S0379, S0383, S0387, S0389, S0391, S0394, S0395, S0397, S0406, S0407, S0410, S0417, S0427, S0430, S0441, S0448, S0461, S0468, S0469, S0481, S0484, S0501, S0513, S0517, S0521, S0525, S0543, S0544, S0549, S0554, S0572, S0574, S0586, S0600, S0603, S0622, S0634, S0650, S0659, S0660, S0684, S0687, S0693, S0705, S0721, S0780, S0790, S0792, S0839, S0842, S0843, S0844
- Doğrulanmayan (önceki ajan kararı, lider doğrulamadı) kullanılabilir=evet ZATEN/FARK_ONEMSIZ adayı: 34 satır; BENZER yazıldı (not sütununda işaretli): S0003, S0013, S0016, S0020, S0022, S0025, S0028, S0044, S0097, S0142, S0143, S0153, S0178, S0179, S0211, S0245, S0255, S0296, S0300, S0308, S0333, S0438, S0492, S0493, S0508, S0509, S0533, S0550, S0552, S0568, S0569, S0570, S0576, S0651
- FARK_TEST_EDILMEDI (208) ve yeni_199 BENZERI_TEST (172) satırları: kural satır satır açılmadı; BENZER kabul edildi, `not`: "önceki ajan kararı, lider doğrulamadı". Önceki ajanın "denenmemiş bileşen" iddiaları kodla sınıf bazında örneklendi ve doğru çıktı: macd-sinyal'de fiyat>EMA trend filtresi yok (yalnız sifir_filtre); ma-kesisim'de zaman çıkışı yok; rsi-asiri-donus'ta SMA5 geri kazanım çıkışı yok; bant-donus giriş = banda dönüş mumu; donchian scalp klonu/TRB 50-200 yok. Yani BENZERI sınıfı doğrulanan 5 büyük aile için tutarlı; kalan ~170 sınıfın tamamında yapılmadı (sınıf başına en az 1 satır koşulu SAĞLANMADI).
- Önceki ajanın ZATEN_TEST sınıfı güvenilir değil: doğruladığım ZATEN satırlarının çoğu BENZER çıktı (kendi denetimi de %35 sorun demişti). Örnekler: S0001/S0780 dual-thrust (n=21; kaynak her zaman piyasada, sınıf seans sonu çıkış), S0018 bandtastic (sınıfta RSI/MFI/EMA filtreleri açık, kaynak varsayılanında kapalı), S0549 AwesomeMacd (AO sıfır kesişimi vs AO dönüşü).

- TEKRAR (906 liste içi): aynı link + aynı giriş kuralı olan çift bulunmadı (828 benzersiz link; ortak linkler farklı stratejiler: aynı repo/sayfada birden çok kural). Emin olmadığım için isimden TEKRAR demedim.
- BELIRSIZ (16): kullanilabilir=hayir ama karşılaştırma dosyasında kapsam_disi_neden boş ve bayrak da yok; nedeni dosyada yazmıyor (1 satırı ajan2 AAPL/STLD/IBM).
## Tutarsızlıklar
- `swing__ma-kesisim` ayar kümesinde 15/70 EMA (S0839 "aynı" denmişti) yok; S0347 (DI/ADX kesişimi) yanlışlıkla `swing__macd-sinyal`e bağlanmıştı.
- `dis__ft-bandtastic` sınıf kodu kaynağın varsayılan tetikleyicisini (yalnız BB 1σ alt) yansıtmıyor.
- Derin geçiş: hiç koşulmamış sınıflara bağlı 21 satır (v3__volatilite-kirilim-k05, v3__adaptivetrend-6s, v3__z-skor-karsit...) "test edildi" sayılamaz (önceki rapor kendi söylemiş); burada o satırlar BENZER.

## E_KODLANMADI_NEDENSIZ yargısı
BIZDE_YOK + kullanilabilir=evet satırların akıbeti yalnızca "kanıtsız, ayrı test açmaya değmez / canlıya filtre eklenmez" önerisi (tur4 RAPOR §1.5) ya da test önceliği; bu bir karar değil -> E yazıldı. Hakem elemesi/kodlanmadı gerekçesi yazılanlar D.

## oncelik30 (30 fikir grubu) akıbeti
Kaynak: dal `tur4_degerlendirme/oncelik30_hukum.csv` (önceki ajan hükmü; kodla yeniden doğrulamadım, ancak Donchian/RSI/MA/MACD/bant sınıfları yukarıdaki doğrulamaya uyuyor).

| sıra | fikir grubu | hüküm | bizde test edilen |
|---|---|---|---|
| 1 | T01 Donchian/kanal kırılımı (N-gün yüksek) | ADIL_TEST_EDILDI_ELENDI | swing__donchian-kirilim; pf__v3-donchian-ansambl; dis__son1ay-kanal-20 |
| 2 | T28 Aylık MA filtresi / taktik varlık dağılımı (Faber 10 ay) | ADIL_TEST_EDILDI_ELENDI | pf__trend_sepet; dis__sma200-ls |
| 3 | T47 Kesitsel momentum (12-1 / 6-6 kazanan-kaybeden) | BIZIM_EVRENDE_UYGULANAMAZ | pf__kesit_ls; pf__rotasyon; pf__sinif_kesit_mom; pf__v3-fip-kesitsel-m |
| 4 | T46 Zaman serisi momentumu (N-ay getiri işareti, TSMOM) | ADIL_TEST_EDILDI_ELENDI | v2__tsmom-oy; v2__tsmom-12-1; dis__tsmom; pf__cta; dis__ewmac-carry |
| 5 | T09 Açılış aralığı kırılımı (ORB, ilk N dakika) | ZAYIF_TEMSILCI_ILE_TEST_EDILDI | daytrade__orb; dis__orb-sweep-donus; v3__orb-4s-hacim-atr |
| 6 | T30 MACD/TRIX/PPO sinyal kesişimi (klasik) | ADIL_TEST_EDILDI_ELENDI | swing__macd-sinyal; scalp__macd-sinyal |
| 7 | M35 Stokastik / Williams %R / Ultimate Oscillator aşırılık dönüşü | ADIL_TEST_EDILDI_ELENDI | swing__stokastik-donus; daytrade__stokastik-donus; scalp__stokastik-do |
| 8 | M31 Gece/açılış boşluğu sönümleme (gap fade) | BIZIM_EVRENDE_UYGULANAMAZ | swing__gap-doldurma; daytrade__gap-doldurma; dis__gap-onceki-kapanis-t |
| 9 | T27 Tek MA üstü/altı zamanlama (günlük/haftalık) | ADIL_TEST_EDILDI_ELENDI | dis__sma200-ls; swing__ma-kesisim; pf__trend_sepet |
| 10 | T21 BLL tipi değişken MA (VMA) kuralları, bantlı | ZAYIF_TEMSILCI_ILE_TEST_EDILDI | dis__ema-esik-trend; swing__ma-kesisim; dis__sma200-ls |
| 11 | T45 52 hafta zirvesine yakınlık (kesitsel) | BIZIM_EVRENDE_UYGULANAMAZ | swing__goreceli-guc-momentum; dis__yeni-zirve-trend-filtresi; pf__kesi |
| 12 | T08 Gürültü bölgesi / noise oranı uyarlamalı kırılım | ADIL_TEST_EDILDI_ELENDI | v3__gunici-momentum-noise-alani; v3__volatilite-kirilim-k05 |
| 13 | M20 VWAP bandından dönüş | ADIL_TEST_EDILDI_ELENDI | daytrade__vwap-donus; dis__vwap-alt-bant-dip |
| 14 | M27 Kesitsel kısa vadeli ters dönüş (geçen hafta/günün kaybedenini al) | BIZIM_EVRENDE_UYGULANAMAZ | pf__sinif_kesit_donus |
| 15 | T26 Fiyat yapısı kırılımı (direnç, salınım tepesi, 123, ardışık yüksel | ADIL_TEST_EDILDI_ELENDI | dis__arps-pivot-desenleri; swing__kirilim-geri-test; daytrade__trend-y |
| 16 | T55 Osilatörün trend yönlü kullanımı (RSI/CCI/KDJ/stokastik momentum b | ADIL_TEST_EDILDI_ELENDI | swing__rsi-momentum-esik; swing__cci-esik |
| 17 | M11 Bollinger alt bant dokunuşu/geri dönüşü (filtresiz) | ADIL_TEST_EDILDI_ELENDI | swing__bant-donus; dis__bollinger-2-3-sd-bolgesi; dis__ft-low-bb |
| 18 | M05 RSI(14) 30/70 aşırılık (klasik, filtresiz) | ADIL_TEST_EDILDI_ELENDI | swing__rsi-asiri-donus; daytrade__rsi-asiri-donus; scalp__rsi-asiri-do |
| 19 | T22 Üçlü/çoklu MA dizilimi (kısa>orta>uzun) | ADIL_TEST_EDILDI_ELENDI | dis__ma-dizilim-5-10-30; dis__ma-mukemmel-siralama; dis__gmma-ls |
| 20 | T02 Kanal kırılımı + trend/hacim/ADX/temel filtresi | ZAYIF_TEMSILCI_ILE_TEST_EDILDI | swing__donchian-kirilim; dis__bant-kirilim-trend; dis__son1ay-donchian |
| 21 | T61 Yüzde filtre kuralı (Alexander / Fama-Blume) | ZAYIF_TEMSILCI_ILE_TEST_EDILDI | dis__yuzde-zigzag |
| 22 | M29 Uzun vadeli kaybeden-kazanan dönüşü (DeBondt-Thaler) | BIZIM_EVRENDE_UYGULANAMAZ | (yok) |
| 23 | M36 Trend göstergesinin tersine kullanımı (kontrarian EMA/PSAR/stokast | HIC_TEST_EDILMEDI | (yok) |
| 24 | M39 Volatilite endeksi / opsiyon sinyaliyle endeks alımı | BIZIM_EVRENDE_UYGULANAMAZ | (yok) |
| 25 | M04 Kısa periyot RSI (3–5) aşırı satım + trend filtresi | ADIL_TEST_EDILDI_ELENDI | swing__rsi-asiri-donus; dis__connors-etf |
| 26 | M21 Kanal/zarf ucundan dönüş (Keltner, ATR, Donchian) | BIZIM_EVRENDE_UYGULANAMAZ | swing__bant-donus; dis__bant-kirilim-trend |
| 27 | M01 RSI(2) aşırı satım alımı + uzun vade trend filtresi (Connors) | ADIL_TEST_EDILDI_ELENDI | dis__connors-etf; dis__ifr2; swing__rsi-asiri-donus |
| 28 | M15 Pairs / eşbütünleşme spread z-skoru | BIZIM_EVRENDE_UYGULANAMAZ | pf__pairs |
| 29 | M16 Mesafe yöntemi pairs (GGR) | BIZIM_EVRENDE_UYGULANAMAZ | pf__pairs |
| 30 | M24 IBS (kapanışın gün aralığındaki konumu) dip alımı | ADIL_TEST_EDILDI_ELENDI | dis__ibs-donus; pf__ibs_donus |

Özet: ADIL_TEST_EDILDI_ELENDI=16, BIZIM_EVRENDE_UYGULANAMAZ=9, ZAYIF_TEMSILCI_ILE_TEST_EDILDI=4, HIC_TEST_EDILMEDI=1. "HIC_TEST_EDILMEDI" = M36 (kontrarian trend göstergesi): kodlanmamış, test bekliyor (akıbet değil).

## Öz kontrol
Betikle: ham_id sırası = strateji_listesi veri sırası, id S0xxx numarası = satır no (906/906 tutuyor). Elle 6 rastgele/özel satır (X005:277,422,458,138,583,868) kaynağa geri izlendi; ESDEGER/BENZER kodla açılan 174 satırın hedef sınıfı kod_kaydi.csv'de var.
