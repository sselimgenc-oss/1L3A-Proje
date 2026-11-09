# TradingView stratejileri: eleme raporu

- Kaynak: 164 benzersiz betik (2 PDF). Kaynağı açık: 160, kapalı: 4.
- Aşama 1 ön eleme: **41 aday** seçildi, 123 elendi (gerekçeler `tv/aday.csv`).
- Aşama 2: 36 aday Python'a çevrildi ve backtest edildi (5 çevrilemedi, nedenleri `aday.csv`).
- Aşama 3: **3 strateji** tüm zorunlu kuralları geçti.

## Kural bazında kaybedenler

| Kural | Kalan strateji |
|---|---|
| 1_islem_sayisi | 0 |
| 2_maks_dusus<=20 | 27 |
| 3_beklenti>=0.15R | 20 |
| 4a_kf>=1.3 | 20 |
| 4b_sharpe>=1 | 32 |
| 5_oos | 18 |
| 6_maliyet2x_kf>=1.1 | 18 |
| 7_komsu>=70 | 14 |
| 8_enstr>=60 | 16 |

## Geçenler

| Strateji | İşlem | KF | Sharpe | Maks. düşüş | Beklenti R | OOS/Eğitim Sharpe | Sıralama puanı (5 üzerinden) |
|---|---|---|---|---|---|---|---|
| hybrid_brk (hezSShJr) | 570 | 1.89 | 1.36 | %11 | 0.52 | 1.61/1.34 | 4 |
| sqzmom (G40dtEbK) | 1477 | 1.81 | 1.06 | %5 | 0.45 | 0.74/1.18 | 4 |
| macd_reloaded (VO6DY8s1) | 4113 | 1.52 | 1.03 | %20 | 0.33 | 0.87/1.12 | 3 |

## Kalanlar (en yakın 10: sağlanan zorunlu kural sayısına göre)

| Strateji | Geçilen kural | Başarısız kurallar |
|---|---|---|
| gvto | 8/9 | 4b_sharpe>=1 |
| ichimoku | 8/9 | 4b_sharpe>=1 |
| kripto_mom | 8/9 | 5_oos |
| st_kivanc | 8/9 | 4b_sharpe>=1 |
| alphatrend | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |
| gaussian | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |
| grover | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |
| macd_sma200 | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |
| pivot_st | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |
| pmax | 7/9 | 2_maks_dusus<=20, 4b_sharpe>=1 |

## Yöntem ve varsayımlar

- Motor: sinyal bar kapanışında, giriş sonraki barın açılışında (`process_orders_on_close=true` olan betiklerde sinyal mumunun kapanışında); stop/hedef mum içinde, aynı mumda ikisi de olursa önce stop.
- Pozisyon boyu: stop varsa işlem başı %1 risk (10.000 $ sabit sermaye, bileşiksiz; pozisyon değeri en çok sermayenin %25'i), stop yoksa %10 (enstrüman sayısı N>10 ise %100/N: brüt pozisyon ≤ %100).
- Masraf taraf başına: kripto %0,07, ABD %0,02, BIST %0,10, emtia %0,03 + kayma %0,02. Parametreler Pine varsayılanı, optimizasyon yok.
- Veri: kripto Binance spot (2019→), hisse/emtia Yahoo (günlük 2015→, saatlik son ~730 gün). Dört saatlik = saatlikten türetildi.
- Eğitim/OOS: portföy veri aralığının ilk %70'i eğitim, son %30'u OOS (parametre değişmez).
- ±%20 sağlamlık: her sayısal parametre ×0,8/×1,2 ayrı ayrı + rastgele birlikte kombinasyonlar (en çok 24 komşu); komşuda portföy net kârı > 0 ise "kârda".
- Beklenti R: stop olan stratejilerde kâr/başlangıç riski, stop olmayanlarda kâr/ortalama kayıp.
- Sharpe: günlük portföy getirisi (sabit 10.000 $ tabanlı), yıllık √365 (yalnız kripto) veya √252.
- İşlem türü: ortanca tutma süresi < 1 gün ise gün içi (≥300 işlem), değilse swing (≥100 işlem).
- Bilinen sınırlar: (1) hayatta kalma yanlılığı — enstrüman listesi bugünün büyük/likit varlıkları; (2) Pine'daki kısmi çıkışlar, pyramiding ve seans/gün sonu kuralları motorda yok, ilgili betiklerin modül başlığında not edildi; (3) mevcut stratejilerle korelasyon `ortak/backtest_gunluk_getiri.csv` içindeki 4 seriyle (KGT, KMN ve karışımları) hesaplandı; (4) CRYPTOCAP:TOTAL verisi yok, BTC vekil kullanıldı.
