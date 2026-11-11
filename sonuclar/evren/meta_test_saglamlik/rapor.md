# Test B — Meta-test sağlamlık (keşif)

Ana ölçü ve test meta-testle aynı: D̄ = 11 pencerede (S_k − N1) yüzdelik puan farkının ortalaması, işaret çevirme (2048), tek yönlü p. Üç ayrı koşu; eşik/p kararı yok.

Kontrol: tam veriyle D̄ yeniden hesaplandı = 7.92 (meta-test: 7.92).

| koşul | pencere | D̄ | p_yukarı | p_aşağı | %90 GA | D_k > 0 |
|---|---|---|---|---|---|---|
| B1 bilinen büyükler | 11 | **3.49** | 0.1577 | 0.8428 | [-2.63 ; 9.61] | 8/11 |
| B2 kazananları çıkar | 11 | **2.44** | 0.2715 | 0.7290 | [-4.82 ; 9.71] | 6/11 |
| B3 yalnız short | 11 | **4.83** | 0.0625 | 1.0000 | [0.01 ; 9.65] | 4/11 |

**Önceden yazılan yorum uygulaması:** Üçünde de D̄ > 0: evren/long şüphesi büyük ölçüde zayıflar.

## Pencere başına D_k

| kesim | tam veri | B1 | B2 | B3 |
|---|---|---|---|---|
| 2020-05-08 | -5.91 | -2.70 | -7.77 | 16.71 |
| 2020-11-08 | 9.55 | 2.47 | 10.09 | 7.76 |
| 2021-05-08 | -7.83 | 1.02 | -12.30 | 26.27 |
| 2021-11-08 | -7.22 | 11.40 | -13.01 | 0.00 |
| 2022-05-08 | -14.30 | -14.93 | -15.63 | 0.00 |
| 2022-11-08 | 11.78 | 12.48 | -2.84 | 2.38 |
| 2023-05-08 | 22.59 | 7.24 | 14.36 | 0.00 |
| 2023-11-08 | 22.32 | 14.23 | 21.75 | 0.00 |
| 2024-05-08 | 13.77 | -17.38 | 3.91 | 0.00 |
| 2024-11-08 | 24.45 | 14.22 | 15.40 | 0.00 |
| 2025-05-08 | 17.91 | 10.31 | 12.92 | 0.00 |

## Kesim başına kapı geçen / uygun sayıları

| kesim | B1 geçen/uygun | B2 geçen/uygun | B3 geçen/uygun |
|---|---|---|---|
| 2020-05-08 | 6/179 | 16/180 | 0/102 |
| 2020-11-08 | 14/180 | 37/180 | 0/102 |
| 2021-05-08 | 17/180 | 57/180 | 0/102 |
| 2021-11-08 | 16/191 | 72/191 | 0/106 |
| 2022-05-08 | 9/192 | 50/192 | 0/106 |
| 2022-11-08 | 5/192 | 47/192 | 0/106 |
| 2023-05-08 | 4/192 | 37/192 | 0/106 |
| 2023-11-08 | 3/192 | 36/193 | 0/106 |
| 2024-05-08 | 6/192 | 57/193 | 0/106 |
| 2024-11-08 | 4/192 | 49/193 | 0/106 |
| 2025-05-08 | 4/192 | 59/193 | 0/106 |

## B2: her pencerenin al-tut kazananları (ölçüm penceresinden çıkarılanlar)

| kesim | kazananlar (getiri %) |
|---|---|
| 2020-05-08 | LINKUSDT (213), DK_TSLA (176), ETHUSDT (105), ADAUSDT (98), DK_NVDA (91) |
| 2020-11-08 | DOGEUSDT (25839), BNBUSDT (2148), SOLUSDT (2032), ADAUSDT (1531), ETHUSDT (699) |
| 2021-05-08 | SOLUSDT (478), DK_NVDA (101), DK_NATGAS (86), DK_TSLA (82), DK_AMD (73) |
| 2021-11-08 | DK_NATGAS (44), DK_XOM (41), DK_WTI (36), DK_LLY (12), DK_JNJ (8) |
| 2022-05-08 | DK_XOM (24), DK_LLY (23), DK_JPM (6), DK_V (-2), DK_JNJ (-2) |
| 2022-11-08 | DK_META (141), DK_NVDA (100), DK_AMD (42), BTCUSDT (38), DK_MSFT (36) |
| 2023-05-08 | BCHUSDT (110), SOLUSDT (98), LINKUSDT (89), DK_NVDA (60), XRPUSDT (53) |
| 2023-11-08 | SOLUSDT (244), BNBUSDT (134), DOGEUSDT (104), DK_NVDA (97), BCHUSDT (93) |
| 2024-05-08 | ZECUSDT (96), DK_TSLA (67), DK_NVDA (65), DK_AVGO (41), DK_WMT (38) |
| 2024-11-08 | XRPUSDT (282), XLMUSDT (155), ADAUSDT (65), TRXUSDT (55), DK_NATGAS (35) |
| 2025-05-08 | ZECUSDT (1496), DK_MU (188), DK_AMD (133), ETHUSDT (90), DK_GOOGL (84) |

## B3: long işlem payı (S_k vs N1; tam veri, havuzlanmış işlem sayısıyla)

| kesim | S_k long payı (geriye bakış) | N1 (geriye bakış) | S_k (ölçüm) | N1 (ölçüm) |
|---|---|---|---|---|
| 2020-05-08 | 0.660 | 0.663 | 0.704 | 0.713 |
| 2020-11-08 | 0.867 | 0.764 | 0.900 | 0.824 |
| 2021-05-08 | 0.883 | 0.792 | 0.873 | 0.793 |
| 2021-11-08 | 1.000 | 0.777 | 1.000 | 0.694 |
| 2022-05-08 | 1.000 | 0.758 | 1.000 | 0.677 |
| 2022-11-08 | 1.000 | 0.723 | 1.000 | 0.702 |
| 2023-05-08 | 1.000 | 0.729 | 1.000 | 0.720 |
| 2023-11-08 | 1.000 | 0.744 | 1.000 | 0.776 |
| 2024-05-08 | 1.000 | 0.742 | 1.000 | 0.732 |
| 2024-11-08 | 1.000 | 0.752 | 1.000 | 0.733 |
| 2025-05-08 | 1.000 | 0.744 | 1.000 | 0.770 |

Ortalama long payı — S_k: 0.946 (geriye bakış), 0.953 (ölçüm); N1: 0.744 (geriye bakış), 0.739 (ölçüm).

## B1 enstrüman eşleşmesi

Listedeki 17 enstrümandan mtm dosyalarında bulunan: 17. Bulunmayan: yok (liste değiştirilmedi).

## Uyarılar ve sınırlar

- Keşif testi; sonuç sonrası tasarlandı (meta-testin ardından). Sonuç kilitli canlı planı değiştirmez.
- Yalnız 11 pencere: güç düşük. Süzülmüş verilerde (B1, B3) kapıyı geçen sayısı küçülür; S_k çoğu kesimde N1'den tamamlanabilir (bkz. kapı geçen sayıları) — bu D̄'yi gürültülü yapar.
- Evren 2026'da seçildi; kapılar geliştirme verisi görüldükten sonra tasarlandı (meta-testteki yanlılıklar geçerli).
- B2: çıkarma yalnız ölçüm penceresinde ve günlük R serisinde yapıldı; geriye bakış ve seçim aynı. Pencere başı = T'den önceki son günlük kapanış, sonu = pencere sonundan önceki son günlük kapanış.
- Kullanılan en büyük tarih: 2025-11-07 23:55:00+00:00 (< 2025-11-08 doğrulandı). Betik sha256: 1e0932e317ecb37354968c651e3b4d4f9e2e1df72f532d3048441494fd0d162e; commit: 253eb221a2771c4d16c4abc250452daaec7ea83c.

## Koşu sonrası ek bilgi ve okuma notları (betik çıktısına sonradan eklendi; sayıları değiştirmez)

- **B3 neredeyse bilgisiz:** yalnız short işlemlerle hiçbir kesimde hiçbir strateji kapıyı geçemedi (kapı geçen 0/102–106). S_k bu yüzden N1'in
  puana göre ilk 3'ünden (N1 ≤ 3 ise N1'in tamamından) kuruldu. N1 boyutu kesim sırasıyla 14, 6, 5, 3, 3, 4, 3, 2, 2, 2, 2; S_k boyutu 3,3,3,3,3,3,3,2,2,2,2.
  Yani 2021-11'den itibaren S_k = N1 ve D_k tam 0 (7 pencere; 2023-11'den sonra N1 yalnız 2 strateji). D̄ +4,83 yalnız ilk iki-üç pencereden (+16,7; +7,8; +26,3)
  geliyor; "yalnız short'ta seçim işe yarıyor" diye okunamaz. Kuralın mekanik sonucu "D̄ > 0" ama bilgi içeriği düşük.
- **B1 kapı geçen** 3–17, S_k boyutu: 6, 10, 10, 10, 9, 5, 4, 3, 6, 4, 4 (kapı geçen < 10 olunca S_k yalnız kapı geçenlerden; 3'ün altına inilmedi). Küçük S_k = gürültülü D_k.
- **Long payı bulgusu (B3 ek tablosu):** tam veride S_k'nin işlemleri 2021-11'den itibaren (8 pencere) %100 long (ort. %94,6 geriye bakış / %95,3 ölçüm);
  N1 ortalaması ~%74. Yani seçim vekili son yıllarda yalnız long-yönlü stratejileri öne çıkarıyor. Bu, "üstünlük long/yükselen piyasa yanlılığıdır" şüphesini
  destekleyen bir göstergedir (B3'ün kendisi bunu sınayamıyor, yukarıya bakın). Kanıt değil, ipucu.
- **Önceden yazılan kural sonucu:** üçünde de D̄ > 0 → "evren/long şüphesi büyük ölçüde zayıflar". Dikkatli okuma: B1 (D̄ 3,5, p 0,16) ve B2 (D̄ 2,4, p 0,27) ana sonuca (7,9) göre
  belirgin küçüldü ve tek başına rastgeleden ayırt edilemez; B3 bilgisiz. Pozitif işaret korunuyor, ama "zayıflar" ifadesi B1/B2'de kısmen, B3'te hiç desteklenmiyor.
  B2'de D_k pozitif pencere 6/11 (tam veride 7/11); 2022-11 penceresi kazananlar çıkınca +11,8 → −2,8.
- **Ek duyarlılık yok:** B1/B2/B3 için ek denemeler yapılmadı; parametreler ön kayıttaki gibi. Betik hatası: ilk koşu `yon_tablosu`'nda (B3 ek tablosu) çöktü, hiçbir sonuç görülmeden
  yalnız havuz kuralı süzgeci düzeltildi (ON_KAYIT.md notu); SONUÇ SONRASI DEĞİŞİKLİK yok.

## Denetim (ayrı kodla, gerçek veriden)

- B3 short süzgeci: `dis__acrypto-agirlikli|1d` (hem long hem short işlemli): ham dosyalardan bağımsız sayım short işlem 1782, ΣR(short) −419,2129; betik SData: 1782 işlem,
  ΣR −419,2129, günlük seri toplamı −419,2129 (eşit). Long-only bir strateji (`dis__ac-cok-katman|1d`, 873 long) short havuzunda 0 işlem veriyor (doğru).
- B2 çıkarma: `dis__ac-cok-katman|1d`, pencere 2023-11-08, 5 kazanan (SOL, BNB, DOGE, NVDA, BCH) çıkarılınca pencere ΣR bağımsız hesap 31,43062 = betik 31,43062 (tam veri 54,47491);
  geriye bakış günlük serisi tam veriyle aynı (allclose).
- B1: bu strateji için işlem sayısı 445 (tam 873): yalnız 17 enstrümandaki işlemler.
- Tam veriyle yeniden hesaplanan D̄ = meta-test D̄ (7,92; tolerans 1e-6 doğrulandı).
- Yükleme: kum_r = r doğrulaması ve holdout süzgeci meta-testle aynı kodla (`_strateji_yukle`); en büyük kullanılan tarih 2025-11-07 < 2025-11-08.
