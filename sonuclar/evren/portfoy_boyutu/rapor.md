# Test A — Kaç strateji ideal? (keşif)

Her kesimde kapıyı (G1–G3) geçenlerden N tanesi alınıp 6 ay boyunca para hesabıyla yürütüldü. "üst-N" = puana göre ilk N; "rastgele-N" = kapı geçenlerden 2000 rastgele N'li çekiliş (kesim içi ortalaması). Her strateji 250 USD ayrı kasa, işlem başı %1,5 risk, kasa zirveden −%30'a inerse o strateji durur, toplam kasa zirveden −%20'ye inerse hepsi durur.

Doyma noktası (ön kayıtlı yorum; ort. max düşüşte sonraki adımda < 1 puan iyileşme): üst-N: **2**, rastgele-N: **1** (None = 10'a kadar doymadı). Tek başına karar değildir.

## üst-N (puana göre ilk N)

| N | kesim | ort getiri % | medyan % | sd (kesimler) | ort maks düşüş % | en kötü maks düşüş % | hesap kill | en az 1 strateji kill | ort korelasyon |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 11/11 | 14.58 | -13.68 | 72.98 | 26.43 | 57.61 | 0.818 | 0.182 | — |
| 2 | 11/11 | 15.78 | -2.19 | 45.56 | 22.00 | 36.54 | 0.727 | 0.455 | 0.474 |
| 3 | 11/11 | 16.75 | -4.31 | 52.53 | 23.25 | 31.82 | 0.818 | 0.818 | 0.523 |
| 4 | 11/11 | 24.33 | -5.29 | 80.32 | 20.98 | 29.58 | 0.545 | 0.818 | 0.546 |
| 6 | 11/11 | 20.99 | -4.67 | 70.98 | 21.27 | 26.80 | 0.818 | 1.000 | 0.612 |
| 8 | 11/11 | 26.84 | -0.15 | 67.90 | 20.86 | 24.60 | 0.636 | 1.000 | 0.637 |
| 10 | 11/11 | 18.22 | 11.08 | 56.33 | 20.91 | 24.85 | 0.818 | 1.000 | 0.654 |

## rastgele-N (kesim içi ortalama)

| N | kesim | ort getiri % | medyan % | sd (kesimler) | ort maks düşüş % | en kötü maks düşüş % | hesap kill | en az 1 strateji kill | ort korelasyon |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 11/11 | 9.46 | 4.56 | 31.62 | 21.15 | 27.13 | 0.790 | 0.073 | — |
| 2 | 11/11 | 13.14 | 4.12 | 41.34 | 21.46 | 25.58 | 0.769 | 0.453 | 0.486 |
| 3 | 11/11 | 13.48 | 4.85 | 40.71 | 21.18 | 27.36 | 0.753 | 0.693 | 0.484 |
| 4 | 11/11 | 13.45 | 4.90 | 40.74 | 20.88 | 27.66 | 0.732 | 0.821 | 0.483 |
| 6 | 11/11 | 13.11 | 4.90 | 39.40 | 20.61 | 27.65 | 0.698 | 0.941 | 0.482 |
| 8 | 11/11 | 13.23 | 4.76 | 39.87 | 20.53 | 27.49 | 0.680 | 0.977 | 0.483 |
| 10 | 11/11 | 13.07 | 5.43 | 39.43 | 20.34 | 26.66 | 0.666 | 0.989 | 0.484 |

## Rastgele-N: kesim içi dağılım (kesimler üzerinden ortalaması alınmış yüzdelikler)

| N | getiri % p5 | p50 | p95 | maks düşüş % p5 | p50 | p95 | tek çekilişte en kötü düşüş % |
|---|---|---|---|---|---|---|---|
| 1 | -22.96 | 1.85 | 69.26 | 7.24 | 21.15 | 32.19 | 120.58 |
| 2 | -15.65 | 6.83 | 64.74 | 13.68 | 21.08 | 29.14 | 97.19 |
| 3 | -13.04 | 8.73 | 54.41 | 14.96 | 21.11 | 27.57 | 65.89 |
| 4 | -10.66 | 9.94 | 48.74 | 15.40 | 20.91 | 27.72 | 54.49 |
| 6 | -7.71 | 11.17 | 41.30 | 16.01 | 20.51 | 25.85 | 44.87 |
| 8 | -5.91 | 11.70 | 37.95 | 16.51 | 20.39 | 24.97 | 44.64 |
| 10 | -4.80 | 11.78 | 35.02 | 16.77 | 20.16 | 24.32 | 44.32 |

## Kesim başına kapıyı geçen sayısı

| kesim | kapı geçen |
|---|---|
| 2020-05-08 | 16 |
| 2020-11-08 | 37 |
| 2021-05-08 | 57 |
| 2021-11-08 | 72 |
| 2022-05-08 | 50 |
| 2022-11-08 | 47 |
| 2023-05-08 | 37 |
| 2023-11-08 | 36 |
| 2024-05-08 | 57 |
| 2024-11-08 | 49 |
| 2025-05-08 | 59 |

## Uyarılar ve sınırlar

- Keşif testidir; sonuç sonrası tasarlandı (meta-testin ardından). Sonuç kilitli canlı planı değiştirmez.
- Yalnız 11 pencere: güç düşük, kesimler arası sd büyük; N'ler arası küçük farklar gürültüdür.
- Kaldıraç ve marj sınırı MODELLENMEDİ: gerçekte çok sayıda eşzamanlı pozisyon marj/kaldıraç tavanına çarpabilir.
- Günlük R toplamı kasa oranıyla çarpıldı (bileşik); gün içi tepe/dip görülmez, kill kontrolü gün sonunda.
- Kapı geçen sayısı N'den az olan kesimler o N için atlandı (tablodaki 'kesim' sütunu); farklı N'lerin kesim kümesi farklı olabilir, N'ler arası karşılaştırmayı bozar.
- Rastgele-N, kapı geçenlerin tamamı yerine rastgele alt kümedir; üst-N puan sırasına güvenir (meta-test: sıralama sınırlı bilgi taşıyor, p 0,046).
- Kullanılan en büyük tarih: 2025-11-07 22:00:00+00:00 (< 2025-11-08 doğrulandı). Betik sha256: 2de0fdf92f291ac150fd6e0504c043c11881073867348759a633228ffe49e43e; commit: 8b1925de6e751caae276309a1c5609a87798c337.

## Koşu sonrası okuma notları ve denetim (betik çıktısına sonradan eklendi; sayıları değiştirmez)

- **Düşüş ölçüsü doyuyor (tavan etkisi):** toplam kasa −%20'de durdurulduğu için ort. max düşüş her N'de ~%20–26'da sıkışıyor; bu yüzden ön kayıtlı "doyma noktası" (üst-N: 2, rastgele-N: 1)
  zayıf bilgi taşır — N büyüdükçe düşüş değil, KILL SIKLIĞI ve kesimler arası dağılım değişiyor. Tek başına karar değildir (ön kayıtta da yazılı).
- **Hesap kill olasılığı yüksek her N'de:** üst-N'de 0,55–0,82; rastgele-N'de 0,67–0,79 (N=10'da 0,67). Bu para kuralıyla (işlem başı %1,5 risk, aynı anda çok pozitif günlük R toplamı) 6 ayda −%20'ye inmek sık.
  Marj/kaldıraç sınırı modellenmedi; gerçekte durum daha kötü olabilir.
- **Çeşitlendirme etkisi net görünen yerler:** rastgele-N'de getirinin kesim içi p5–p95 aralığı N=1'de [−23 ; +69] iken N=10'da [−4,8 ; +35]: dağılım daralıyor (belirsizlik azalıyor); ortalama getiri 13 civarında düz kalıyor (N=1'de 9,5).
  Strateji-arası korelasyon rastgele-N'de ~0,48; üst-N'de N ile 0,47'den 0,65'e yükseliyor (puana göre seçilenler birbirine daha benzer: daha az gerçek çeşitlendirme).
  "En az bir strateji kill" olasılığı N ile hızla 1'e yaklaşıyor (N=10'da 0,99): çok sayıda strateji = en az birinin −%30 görmesi neredeyse kesin; bu tek başına kötü değil (diğerleri sürüyor).
- Üst-N ort. getirisi (14,6–26,8) rastgeleden (9,5–13,5) yüksek ama kesimler arası sd 45–80 puan ve medyan eksi (−14…+11): ortalama birkaç iyi pencereye (2023–2025) bağlı. 11 pencerede N'ler arası fark gürültüdür.
- Denetim (ayrı düz-döngü koduyla, gerçek veriden): kesim 2022-11-08, üst-3 (47 kapı geçen): getiri −20,4776 %, max düşüş 20,4776 %, hesap kill 1, strateji kill 1, korelasyon 0,87591 — betikle birebir.
  Kesim 2020-05-08, rastgele-2 (G=16, aynı tohum akışı, 2000 çekilişin düz döngüyle yeniden hesabı): getiri 4,11789, max düşüş 23,66544, hesap kill 0,9585, strateji kill 0,5375 — betikle birebir.
- Kapı geçen sayısı hiçbir kesimde 10'dan az olmadı (atlanan kesim yok; bkz. kesim_gecen.csv).
