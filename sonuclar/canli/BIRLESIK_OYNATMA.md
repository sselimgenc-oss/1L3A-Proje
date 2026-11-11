# Birleşik hesap yeniden oynatması (S1 / S2 / S3)

> **GEÇMİŞ SİMÜLASYON, GELECEK TAHMİNİ DEĞİL. ÜST SINIR UYARISI:** bu stratejiler tam da bu dönemde (v2 geliştirme, en geç 2025-11-07; holdout okunmadı) seçildi; sonuçlar bu yüzden iyimser bir üst sınırdır. Ön kayıt: `BIRLESIK_ON_KAYIT.md`; betik: `araclar/canli_birlesik_oynatma.py` (sha256 `9609f6bc367c7c45…`); ham sayılar: `birlesik_oynatma.json`.

## Ne yapıldı (sade)
- Her strateji kendi küçük hesabında, mevcut canlı kuralla (işlem başı %1,5, toplam açık stop riski %6, günlük -%6 yeni giriş yok, strateji -%30 kalıcı kill, asgari emir tutarı altı atlanır) ayrı ayrı oynatıldı; sonra günlük olarak toplandı.
- **Açık pozisyonlar dahil:** her gün sonu açık işlemler günlük MTM (piyasa değeri) ile değerlendi (v2 `mtm` dosyaları, `kum_r`); yalnız kapanan işlemler değil.
- İki birleşik seri: **K (kasa)** = Σ min(alt hesap özsermayesi, tahsis) (canlı hesap kill'in ölçtüğü seri; en çok tahsis toplamı kadar olabilir); **H (gerçek hesap)** = Σ özsermaye (kâr hesapta kalır). Net sonuç ve H düşüşü H'den; büyüme freni (-%10), -%15 aşma ve -%20 hesap kill K'dan.
- Hesap kill: K, tahsis toplamından -%20 olursa o gün sonu hepsi kapanır, sonrası donuk. Pencereler her seferinde sıfırdan başlar (başlangıç noktası etkisi).
- Ortak başlangıç 2018-01-01 (kripto 2017-08'de başlıyor; 2017 yarım yıl dışarıda), bitiş 2025-11-07. Yıl pencereleri 2018-2024 (7 tam yıl; 2025 yarım olduğu için yalnız ayrı satırda). 6 ay ve 12 ay pencereleri ayda bir kaydırıldı.
- Senaryolar: **S1** ewo 250 + e0v1en 60 USD; **S2** S1 + hma-atr-rider 250 + lube 250; **S3** eski plan: e0v1en, ewo, hma, lube 4 x 250 USD. Maliyet x2 ana, x1 ek. Boyutlandırmadaki kayma/komisyon da aynı çarpanla (x2'de x2).

## ANA: maliyet x2

### Tüm dönem (2018-01-01 .. 2025-11-07, tek başlangıç)

| Senaryo | Ad | Toplam USD | Net sonuç (H) | Maks düşüş H | Maks düşüş K | Hesap kill -%20 | Strateji kill (tüm dönem) |
|---|---|---|---|---|---|---|---|
| S1 | v2 plani | 310 | 150.9% | 10.3% | 1.5% | hayır | ewo-ema-ofset:ok, e0v1en:ok |
| S2 | v2 + trend | 810 | 106.6% | 7.7% | 5.2% | hayır | ewo-ema-ofset:ok, e0v1en:ok, hma-atr-rider:ok, lube:ok |
| S3 | eski plan | 1000 | 105.4% | 7.9% | 4.2% | hayır | e0v1en:ok, ewo-ema-ofset:ok, hma-atr-rider:ok, lube:ok |

### Pencere oranları (her pencere sıfırdan)

| Sen. | Pencere | n | -%10 değme (K) | -%15 aşma (K) | Hesap kill -%20 | -%10 değme (H) | -%15 aşma (H) | En kötü net | Medyan net | Strateji kill sayısı (pencere) |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 29% | 14% | 8.5% | 16.1% | ewo-em=0, e0v1en=0 |
| S1 | 6 ay kayan | 89 | 10% | 2% | 0% | 17% | 6% | -11.6% | 7.4% | ewo-em=0, e0v1en=2 |
| S1 | 12 ay kayan | 83 | 14% | 4% | 0% | 36% | 11% | -11.5% | 16.1% | ewo-em=0, e0v1en=2 |
| S2 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 0% | 0% | 1.0% | 7.9% | ewo-em=0, e0v1en=0, hma-at=0, lube=0 |
| S2 | 6 ay kayan | 89 | 0% | 0% | 0% | 0% | 0% | -5.4% | 3.6% | ewo-em=0, e0v1en=2, hma-at=0, lube=0 |
| S2 | 12 ay kayan | 83 | 0% | 0% | 0% | 1% | 0% | -5.0% | 7.4% | ewo-em=0, e0v1en=2, hma-at=0, lube=0 |
| S3 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 14% | 0% | -2.0% | 10.6% | e0v1en=0, ewo-em=0, hma-at=0, lube=0 |
| S3 | 6 ay kayan | 89 | 2% | 0% | 0% | 6% | 0% | -7.0% | 3.3% | e0v1en=2, ewo-em=0, hma-at=0, lube=0 |
| S3 | 12 ay kayan | 83 | 2% | 0% | 0% | 12% | 0% | -10.6% | 9.2% | e0v1en=2, ewo-em=0, hma-at=0, lube=0 |

### Yatay bandı (-%10 .. +%10, net sonuç H) ve en kötü dönemler

| Sen. | Pencere | n | Yatay bandında | Bandın üstünde | Bandın altında | En kötü net |
|---|---|---|---|---|---|---|
| S1 | 12 ay, yıl başı | 7 | 14% | 86% | 0% | 8.5% |
| S1 | 12 ay kayan | 83 | 34% | 64% | 2% | -11.5% |
| S1 | 6 ay kayan | 89 | 64% | 34% | 2% | -11.6% |
| S2 | 12 ay, yıl başı | 7 | 57% | 43% | 0% | 1.0% |
| S2 | 12 ay kayan | 83 | 57% | 43% | 0% | -5.0% |
| S2 | 6 ay kayan | 89 | 82% | 18% | 0% | -5.4% |
| S3 | 12 ay, yıl başı | 7 | 29% | 71% | 0% | -2.0% |
| S3 | 12 ay kayan | 83 | 52% | 47% | 1% | -10.6% |
| S3 | 6 ay kayan | 89 | 84% | 16% | 0% | -7.0% |

En kötü 6 ay = 6 ay kayan pencerelerin en düşük neti; en kötü 12 ay = 12 ay kayan pencerelerin en düşük neti (yukarıdaki 'En kötü net').

### Yıl yıl net sonuç (H) / maks düşüş K (12 ay yıl başı + 2025 kısmi)

| Yıl | S1 | S2 | S3 |
|---|---|---|---|
| Y2018 | 16.1% / 1.5% | 5.9% / 1.9% | 11.9% / 2.3% |
| Y2019 | 19.3% / 4.8% | 6.1% / 4.2% | 10.0% / 3.4% |
| Y2020 | 35.6% / 3.8% | 17.4% / 2.1% | 15.6% / 4.8% |
| Y2021 | 22.7% / 4.8% | 10.5% / 1.8% | 10.6% / 4.2% |
| Y2022 | 11.8% / 5.2% | 1.0% / 5.5% | -2.0% / 7.8% |
| Y2023 | 13.7% / 0.4% | 7.9% / 2.9% | 7.8% / 2.3% |
| Y2024 | 8.5% / 1.2% | 17.3% / 0.6% | 13.4% / 1.1% |
| Y2025K (yarım) | 4.1% / 1.5% | 27.5% / 3.7% | 25.7% / 3.0% |

### Stratejiler arası günlük getiri korelasyonu (tüm dönem; Δözsermaye / tahsis)

| Sen. | Çift | Tüm günler | İkisi de hareketli günler | Hareketli gün sayısı |
|---|---|---|---|---|
| S1 | e0v1en / ewo-ema-ofset | 0.16 | 0.24 | 244 |
| S2 | e0v1en / ewo-ema-ofset | 0.16 | 0.24 | 244 |
| S2 | e0v1en / hma-atr-rider | 0.06 | 0.11 | 645 |
| S2 | e0v1en / lube | 0.13 | 0.20 | 454 |
| S2 | ewo-ema-ofset / hma-atr-rider | -0.03 | -0.02 | 333 |
| S2 | ewo-ema-ofset / lube | 0.02 | 0.09 | 236 |
| S2 | hma-atr-rider / lube | 0.18 | 0.22 | 1868 |
| S3 | e0v1en / ewo-ema-ofset | 0.16 | 0.24 | 248 |
| S3 | e0v1en / hma-atr-rider | 0.06 | 0.11 | 653 |
| S3 | e0v1en / lube | 0.12 | 0.19 | 455 |
| S3 | ewo-ema-ofset / hma-atr-rider | -0.03 | -0.02 | 333 |
| S3 | ewo-ema-ofset / lube | 0.02 | 0.09 | 236 |
| S3 | hma-atr-rider / lube | 0.18 | 0.22 | 1868 |

## EK: maliyet x1

### Tüm dönem (2018-01-01 .. 2025-11-07, tek başlangıç)

| Senaryo | Ad | Toplam USD | Net sonuç (H) | Maks düşüş H | Maks düşüş K | Hesap kill -%20 | Strateji kill (tüm dönem) |
|---|---|---|---|---|---|---|---|
| S1 | v2 plani | 310 | 202.8% | 7.5% | 1.3% | hayır | ewo-ema-ofset:ok, e0v1en:ok |
| S2 | v2 + trend | 810 | 136.5% | 6.8% | 3.2% | hayır | ewo-ema-ofset:ok, e0v1en:ok, hma-atr-rider:ok, lube:ok |
| S3 | eski plan | 1000 | 148.2% | 5.0% | 2.6% | hayır | e0v1en:ok, ewo-ema-ofset:ok, hma-atr-rider:ok, lube:ok |

### Pencere oranları (her pencere sıfırdan)

| Sen. | Pencere | n | -%10 değme (K) | -%15 aşma (K) | Hesap kill -%20 | -%10 değme (H) | -%15 aşma (H) | En kötü net | Medyan net | Strateji kill sayısı (pencere) |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 14% | 0% | 12.0% | 22.2% | ewo-em=0, e0v1en=0 |
| S1 | 6 ay kayan | 89 | 6% | 0% | 0% | 13% | 3% | -6.2% | 9.4% | ewo-em=0, e0v1en=0 |
| S1 | 12 ay kayan | 83 | 7% | 0% | 0% | 19% | 4% | -2.0% | 18.7% | ewo-em=0, e0v1en=0 |
| S2 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 0% | 0% | 3.3% | 10.5% | ewo-em=0, e0v1en=0, hma-at=0, lube=0 |
| S2 | 6 ay kayan | 89 | 0% | 0% | 0% | 0% | 0% | -3.9% | 5.6% | ewo-em=0, e0v1en=0, hma-at=0, lube=0 |
| S2 | 12 ay kayan | 83 | 0% | 0% | 0% | 0% | 0% | -0.8% | 10.2% | ewo-em=0, e0v1en=0, hma-at=0, lube=0 |
| S3 | 12 ay, yıl başı | 7 | 0% | 0% | 0% | 0% | 0% | 1.1% | 16.9% | e0v1en=0, ewo-em=0, hma-at=0, lube=0 |
| S3 | 6 ay kayan | 89 | 0% | 0% | 0% | 3% | 0% | -2.8% | 5.7% | e0v1en=0, ewo-em=0, hma-at=0, lube=0 |
| S3 | 12 ay kayan | 83 | 0% | 0% | 0% | 4% | 0% | 0.3% | 13.0% | e0v1en=0, ewo-em=0, hma-at=0, lube=0 |

### Yatay bandı (-%10 .. +%10, net sonuç H) ve en kötü dönemler

| Sen. | Pencere | n | Yatay bandında | Bandın üstünde | Bandın altında | En kötü net |
|---|---|---|---|---|---|---|
| S1 | 12 ay, yıl başı | 7 | 0% | 100% | 0% | 12.0% |
| S1 | 12 ay kayan | 83 | 25% | 75% | 0% | -2.0% |
| S1 | 6 ay kayan | 89 | 57% | 43% | 0% | -6.2% |
| S2 | 12 ay, yıl başı | 7 | 43% | 57% | 0% | 3.3% |
| S2 | 12 ay kayan | 83 | 49% | 51% | 0% | -0.8% |
| S2 | 6 ay kayan | 89 | 78% | 22% | 0% | -3.9% |
| S3 | 12 ay, yıl başı | 7 | 14% | 86% | 0% | 1.1% |
| S3 | 12 ay kayan | 83 | 41% | 59% | 0% | 0.3% |
| S3 | 6 ay kayan | 89 | 73% | 27% | 0% | -2.8% |

En kötü 6 ay = 6 ay kayan pencerelerin en düşük neti; en kötü 12 ay = 12 ay kayan pencerelerin en düşük neti (yukarıdaki 'En kötü net').

### Yıl yıl net sonuç (H) / maks düşüş K (12 ay yıl başı + 2025 kısmi)

| Yıl | S1 | S2 | S3 |
|---|---|---|---|
| Y2018 | 22.2% / 1.3% | 10.0% / 1.5% | 17.1% / 2.0% |
| Y2019 | 24.6% / 4.1% | 8.2% / 4.6% | 13.0% / 3.7% |
| Y2020 | 53.6% / 1.0% | 25.7% / 1.6% | 25.2% / 4.0% |
| Y2021 | 37.1% / 4.6% | 17.1% / 1.8% | 23.0% / 4.0% |
| Y2022 | 16.3% / 4.6% | 3.3% / 4.7% | 1.1% / 6.2% |
| Y2023 | 16.0% / 0.3% | 10.5% / 2.3% | 10.5% / 1.9% |
| Y2024 | 12.0% / 0.1% | 19.9% / 0.6% | 16.9% / 0.5% |
| Y2025K (yarım) | 3.5% / 3.7% | 28.0% / 3.5% | 27.3% / 2.8% |

### Stratejiler arası günlük getiri korelasyonu (tüm dönem; Δözsermaye / tahsis)

| Sen. | Çift | Tüm günler | İkisi de hareketli günler | Hareketli gün sayısı |
|---|---|---|---|---|
| S1 | e0v1en / ewo-ema-ofset | 0.16 | 0.24 | 244 |
| S2 | e0v1en / ewo-ema-ofset | 0.16 | 0.24 | 244 |
| S2 | e0v1en / hma-atr-rider | 0.05 | 0.10 | 642 |
| S2 | e0v1en / lube | 0.13 | 0.21 | 454 |
| S2 | ewo-ema-ofset / hma-atr-rider | -0.03 | -0.02 | 332 |
| S2 | ewo-ema-ofset / lube | 0.01 | 0.09 | 236 |
| S2 | hma-atr-rider / lube | 0.18 | 0.22 | 1864 |
| S3 | e0v1en / ewo-ema-ofset | 0.16 | 0.25 | 248 |
| S3 | e0v1en / hma-atr-rider | 0.05 | 0.10 | 650 |
| S3 | e0v1en / lube | 0.13 | 0.21 | 455 |
| S3 | ewo-ema-ofset / hma-atr-rider | -0.03 | -0.02 | 332 |
| S3 | ewo-ema-ofset / lube | 0.01 | 0.09 | 236 |
| S3 | hma-atr-rider / lube | 0.18 | 0.22 | 1864 |

## Denetim (birleşik seriyi ayrı kısa kodla yeniden hesaplama)

Senaryo **S2**, pencere **Y2022**, maliyet **x2**. Ana yol (`birlestir`/`olcu`, numpy) ile saf Python döngüyle yazılmış ayrı kod (`denetim_yeniden`) karşılaştırıldı.

| Ölçü | Ana yol | Ayrı kod |
|---|---|---|
| net | 0.009780 | 0.009780 |
| dd_k | 0.055364 | 0.055364 |
| dd_h | 0.051149 | 0.051149 |
| son_k | 766.053147 | 766.053147 |
| son_h | 817.921845 | 817.921845 |
| hesap kill | False | False |

Sonuç: **UYUMLU** (en büyük mutlak fark 1.14e-13).

## Veri hattı doğrulaması (ham/x1 -> oyna, tüm dönem, tek başına) — ölçüm raporuyla uyum

Aynı 250 USD / %1,5 / x1 kurulumu, `OLCUM_250_15.md` (işlem listesi backtest'ten yeniden üretilmişti) ile karşılaştırıldı; giriş fiyatı ham dosyadan türetildiği için küçük fark olabilir.

| Strateji | Bu araç (son özsermaye USD) | OLCUM_250_15.csv | Fark |
|---|---|---|---|
| ewo-ema-ofset | 812.71 | 812.71 | -0.00 |
| e0v1en | 757.44 | 757.44 | +0.00 |
| hma-atr-rider | 264.58 | 264.57 | +0.01 |
| lube | 678.98 | 678.98 | +0.00 |

## Yorum (sade; yorum sonradan elle eklendi, sayılar betikten)
1. Hiçbir senaryoda, hiçbir pencerede (x1 ve x2) -%20 hesap kill'i tetiklenmedi; tüm dönemde de tetiklenmedi. Toplam düşüş küçük kaldı (tüm dönem H düşüşü S1 %10,3, S2 %7,7, S3 %7,9; x2).
2. Stratejiler birbirine az bağlı: günlük getiri korelasyonu 0,0-0,25 (en yüksek hma/lube 0,18-0,22, e0v1en/ewo 0,16-0,24). "Hepsi aynı anda kaybeder" bu dönemde görülmedi; en kötü yıl 2022'de bile S2 +%1,0, S3 -%2,0 (x2).
3. S1 (v2 planı) en yüksek getiriyi veriyor ama yalnız iki 15 dk kripto stratejisine dayanıyor: H düşüşü en büyük (%10,3), x2'de 12 ay kayan pencerelerin %36'sında H'de -%10 düşüşe değiyor. S2/S3'te swing eklemek düşüşü küçültüyor, getiriyi de düşürüyor (S2 %107, S3 %105 tüm dönem x2).
4. Yatay bant (-%10..+%10, 12 ay yıl başı, x2): S1 %14 bandın içinde, %86 üstünde; S2 %57 içinde; S3 %29 içinde, %71 üstünde. Yani S2 ve S3'te "yatay yıl" olasılığı S1'den belirgin yüksek. 7 pencere çok az; 12 ay kayan (n=83, üst üste binen pencereler) S2 %57 / S3 %52 / S1 %34 içeride.
5. Pencerelerin altına düşme nadir: 12 ay kayan x2'de bandın altı S1 %2, S2 %0, S3 %1; en kötü 12 ay S1 -%11,5, S2 -%5,0, S3 -%10,6; en kötü 6 ay S1 -%11,6, S2 -%5,4, S3 -%7,0.
6. K serisi (kill ölçüsü) kâr yazınca büyümez; bu yüzden -%10 değme (K) oranları H'den küçüktür (ör. S1 12 ay kayan x2: K %14, H %36). Canlıdaki hesap kill'i K'yı ölçtüğü için kill'e K üzerinden uzaklık geniş görünür; gerçek hesap düşüşü H'dir.
7. e0v1en 60 USD hesabı küçüklükten (BTC min 100 USD, atlama) en kırılgan parça: x2'de 6 ve 12 ay kayan pencerelerin 2'sinde -%30 strateji kill'ine çarptı (S1/S2, 60 USD), 250 USD'lik hesapta (S3) de 2 pencerede aynı sayı; hesap toplamına etkisi küçük.
8. Sınırlar: stratejiler bu dönemde seçildi -> ÜST SINIR; gün sonu MTM (gün içi dalgalanma yok); min tutar tablosu varsayım; kâr yeniden boyutlanmaz (kasa=min(özsermaye,tahsis)); 2018-2025 ağırlıklı kripto boğa dönemi.
