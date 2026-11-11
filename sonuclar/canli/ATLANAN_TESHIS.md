# Atlanan sinyal teşhisi (CANLI_LIMITLER yeniden oynatma)

**Bu bir TEŞHİSTİR; öneri ya da limit değişikliği değildir.** Geçmiş (v2 geliştirme dönemi, holdout okunmadı) üzerinde, strateji başına 165 USD kasa, min tutar tablosu BTC 100 / ETH 20 / diğer 5 USDT. R = işlemin backtest R'si (net K/Z / stopa risk). Atlanan işlemin R'si 'alınsaydı olacak R'dir (boyuttan bağımsız).

Neden kodları: `min_tutar` (hesaplanan tutar min tutarın altı), `risk_butcesi_dolu` (toplam açık stop riski %6 bütçesi dolu), `brut_tavan` (brüt nominal 1.5x dolu), `stop_cok_uzak` (stop mesafesi > %25), `gunluk_blok` (günlük -%6 sonrası yeni giriş yok), `kill_sonrasi` (strateji kill sonrası), `diger` (geçersiz stop / kasa yok).

## 1. Alınan ve atlanan: genel

| strateji | sinyal | alinan | atlanan | alinan_ort_r | alinan_top_r | atlanan_ort_r | atlanan_top_r | r3_toplam | r3_atlanan | r3_atlanan_pay | poz_r_atlanan_pay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dis__gauss-stoch-eth | 1336 | 379 | 957 | 0.08 | 28.73 | 0.20 | 192.19 | 32 | 23 | 72% | 77% |
| dis__ewo-ema-ofset | 1287 | 730 | 557 | 0.15 | 111.84 | 0.17 | 94.89 | 1 | 0 | 0% | 44% |
| dis__jt-awesome-osilator | 1851 | 193 | 1658 | -0.08 | -14.58 | 0.44 | 721.56 | 102 | 97 | 95% | 95% |
| dis__uc-ortalama-boga-sma60 | 367 | 248 | 119 | 0.02 | 5.66 | 0.24 | 28.55 | 9 | 5 | 56% | 47% |
| dis__lube | 175 | 83 | 92 | 0.45 | 37.57 | 0.98 | 90.37 | 21 | 12 | 57% | 64% |
| dis__hma-atr-rider | 2124 | 682 | 1442 | 0.01 | 5.96 | 0.09 | 125.14 | 26 | 19 | 73% | 70% |
| dis__voltarget-trend | 1421 | 244 | 1177 | -0.10 | -25.09 | 0.25 | 298.28 | 73 | 67 | 92% | 92% |
| dis__haftalik-macd-gunluk-ma | 618 | 306 | 312 | 0.27 | 81.60 | 0.10 | 30.02 | 17 | 10 | 59% | 42% |
| dis__e0v1en | 2461 | 1935 | 526 | 0.07 | 128.59 | 0.09 | 48.30 | 1 | 0 | 0% | 23% |

`r3_*`: R>3 olan işlemler; `r3_atlanan_pay`: bunların atlanan payı. `poz_r_atlanan_pay`: stratejinin toplam POZİTİF R'sinin atlananlardan gelen payı.

## 2. Nedene göre kırılım

| strateji | neden | adet | ort_r | top_r | r3_atlanan | r3_pay | poz_r_pay |
|---|---|---|---|---|---|---|---|
| dis__gauss-stoch-eth | min_tutar | 737 | 0.14 | 106.17 | 14 | 44% | 51% |
| dis__gauss-stoch-eth | risk_butcesi_dolu | 10 | 0.08 | 0.75 | 0 | 0% | 1% |
| dis__gauss-stoch-eth | stop_cok_uzak | 210 | 0.41 | 85.27 | 9 | 28% | 26% |
| dis__ewo-ema-ofset | min_tutar | 527 | 0.19 | 100.61 | 0 | 0% | 42% |
| dis__ewo-ema-ofset | stop_cok_uzak | 5 | 0.17 | 0.84 | 0 | 0% | 0% |
| dis__ewo-ema-ofset | gunluk_blok | 25 | -0.26 | -6.56 | 0 | 0% | 1% |
| dis__jt-awesome-osilator | min_tutar | 126 | 0.09 | 11.96 | 4 | 4% | 5% |
| dis__jt-awesome-osilator | risk_butcesi_dolu | 23 | -0.06 | -1.34 | 1 | 1% | 1% |
| dis__jt-awesome-osilator | brut_tavan | 1 | 1.80 | 1.80 | 0 | 0% | 0% |
| dis__jt-awesome-osilator | stop_cok_uzak | 7 | 1.32 | 9.26 | 1 | 1% | 1% |
| dis__jt-awesome-osilator | kill_sonrasi | 1501 | 0.47 | 699.88 | 91 | 89% | 89% |
| dis__uc-ortalama-boga-sma60 | min_tutar | 83 | 0.23 | 19.25 | 2 | 22% | 32% |
| dis__uc-ortalama-boga-sma60 | risk_butcesi_dolu | 1 | -0.36 | -0.36 | 0 | 0% | 0% |
| dis__uc-ortalama-boga-sma60 | stop_cok_uzak | 35 | 0.28 | 9.66 | 3 | 33% | 15% |
| dis__lube | min_tutar | 78 | 1.12 | 87.52 | 10 | 48% | 60% |
| dis__lube | stop_cok_uzak | 14 | 0.20 | 2.84 | 2 | 10% | 4% |
| dis__hma-atr-rider | min_tutar | 1206 | 0.08 | 95.94 | 13 | 50% | 59% |
| dis__hma-atr-rider | risk_butcesi_dolu | 18 | 0.22 | 4.02 | 0 | 0% | 1% |
| dis__hma-atr-rider | brut_tavan | 1 | -0.15 | -0.15 | 0 | 0% | 0% |
| dis__hma-atr-rider | stop_cok_uzak | 217 | 0.12 | 25.34 | 6 | 23% | 11% |
| dis__voltarget-trend | min_tutar | 435 | 0.13 | 55.71 | 25 | 34% | 28% |
| dis__voltarget-trend | risk_butcesi_dolu | 52 | 0.42 | 22.05 | 4 | 5% | 5% |
| dis__voltarget-trend | brut_tavan | 49 | 0.28 | 13.89 | 5 | 7% | 4% |
| dis__voltarget-trend | stop_cok_uzak | 22 | 0.51 | 11.25 | 2 | 3% | 2% |
| dis__voltarget-trend | kill_sonrasi | 619 | 0.32 | 195.38 | 31 | 42% | 53% |
| dis__haftalik-macd-gunluk-ma | min_tutar | 291 | 0.12 | 35.28 | 10 | 59% | 41% |
| dis__haftalik-macd-gunluk-ma | risk_butcesi_dolu | 3 | -0.28 | -0.84 | 0 | 0% | 0% |
| dis__haftalik-macd-gunluk-ma | stop_cok_uzak | 18 | -0.25 | -4.42 | 0 | 0% | 0% |
| dis__e0v1en | min_tutar | 513 | 0.09 | 45.22 | 0 | 0% | 22% |
| dis__e0v1en | gunluk_blok | 13 | 0.24 | 3.08 | 0 | 0% | 1% |

`r3_pay`: stratejideki TÜM R>3 işlemlerin yüzde kaçı bu nedenle atlandı; `poz_r_pay`: toplam pozitif R'nin yüzde kaçı bu nedenle atlanan işlemlerden.

## 3. En büyük 10 R'li işlem (jt-awesome-osilator, voltarget-trend)

### jt-awesome-osilator

| sembol | giris | yon | R | durum | neden |
|---|---|---|---|---|---|
| BNBUSDT | 2020-12-18 | 1 | 86.05 | atlandi | kill_sonrasi |
| ZECUSDT | 2025-08-24 | 1 | 73.56 | atlandi | kill_sonrasi |
| DOGEUSDT | 2020-12-18 | 1 | 57.56 | atlandi | kill_sonrasi |
| SOLUSDT | 2021-01-04 | 1 | 36.00 | atlandi | kill_sonrasi |
| XLMUSDT | 2024-11-08 | 1 | 27.11 | atlandi | kill_sonrasi |
| SOLUSDT | 2023-10-01 | 1 | 26.16 | atlandi | kill_sonrasi |
| XRPUSDT | 2024-11-09 | 1 | 23.82 | atlandi | kill_sonrasi |
| BTCUSDT | 2020-10-06 | 1 | 19.26 | atlandi | kill_sonrasi |
| DOGEUSDT | 2021-04-02 | 1 | 18.51 | atlandi | kill_sonrasi |
| BTCUSDT | 2019-02-12 | 1 | 17.63 | atlandi | kill_sonrasi |

### voltarget-trend

| sembol | giris | yon | R | durum | neden |
|---|---|---|---|---|---|
| DK_LLY | 2023-03-27 | 1 | 30.29 | atlandi | kill_sonrasi |
| TRXUSDT | 2024-08-08 | 1 | 28.06 | atlandi | kill_sonrasi |
| DK_XAU | 2023-10-19 | 1 | 23.33 | atlandi | kill_sonrasi |
| DK_AVGO | 2022-12-12 | 1 | 17.36 | atlandi | kill_sonrasi |
| DK_TSLA | 2019-11-26 | 1 | 15.89 | atlandi | risk_butcesi_dolu |
| BTCUSDT | 2020-05-26 | 1 | 14.84 | atlandi | min_tutar |
| BNBUSDT | 2023-12-09 | 1 | 14.83 | atlandi | kill_sonrasi |
| BTCUSDT | 2023-10-17 | 1 | 13.92 | atlandi | kill_sonrasi |
| DK_MU | 2025-06-03 | 1 | 11.75 | atlandi | kill_sonrasi |
| DK_META | 2023-03-07 | 1 | 11.41 | atlandi | kill_sonrasi |

## 4. Varsayımsal senaryolar (YALNIZ TEŞHİS, öneri değil)

- `min_tutar_yok`: min tutar kontrolü kapalı (BTC/ETH küçük hesapta alınamayan işlemler alınmış olsaydı).
- `risk_butcesi_sinirsiz`: toplam açık stop riski (%6) ve brüt nominal (1.5x) bütçesi kapalı; yalnız işlem başı %3 kayıp + işlem başı nominal/marj tavanı kalır.

| strateji | senaryo | islem | alinan_top_r | son_ozsermaye | cagr | maks_dusus | kill | min_tutar | gunluk_blok |
|---|---|---|---|---|---|---|---|---|---|
| dis__gauss-stoch-eth | gercek | 379 | 28.73 | 274.28 | 3.1% | 31.1% |  | 737 | 0 |
| dis__gauss-stoch-eth | min_tutar_yok | 1021 | 110.50 | 294.41 | 3.5% | 31.5% |  | 51 | 0 |
| dis__gauss-stoch-eth | risk_butcesi_sinirsiz | 202 | -10.59 | 115.22 | -2.1% | 44.2% | 2019-02-06 | 0 | 0 |
| dis__ewo-ema-ofset | gercek | 730 | 111.84 | 681.61 | 18.9% | 19.2% |  | 527 | 25 |
| dis__ewo-ema-ofset | min_tutar_yok | 1234 | 197.91 | 721.68 | 19.7% | 14.7% |  | 47 | 0 |
| dis__ewo-ema-ofset | risk_butcesi_sinirsiz | 1187 | 179.14 | 1029.37 | 25.0% | 23.5% |  | 40 | 55 |
| dis__jt-awesome-osilator | gercek | 193 | -14.58 | 115.16 | -2.0% | 52.3% | 2018-05-03 | 126 | 0 |
| dis__jt-awesome-osilator | min_tutar_yok | 311 | -21.21 | 114.15 | -2.1% | 52.8% | 2018-08-17 | 3 | 0 |
| dis__jt-awesome-osilator | risk_butcesi_sinirsiz | 134 | -11.54 | 115.46 | -2.0% | 52.2% | 2015-08-13 | 0 | 0 |
| dis__uc-ortalama-boga-sma60 | gercek | 248 | 5.66 | 194.87 | 1.0% | 31.4% |  | 83 | 0 |
| dis__uc-ortalama-boga-sma60 | min_tutar_yok | 221 | 2.59 | 114.90 | -2.1% | 35.5% | 2023-05-01 | 0 | 0 |
| dis__uc-ortalama-boga-sma60 | risk_butcesi_sinirsiz | 315 | 26.20 | 280.52 | 3.2% | 38.2% |  | 17 | 0 |
| dis__lube | gercek | 83 | 37.57 | 323.71 | 4.4% | 20.9% |  | 78 | 0 |
| dis__lube | min_tutar_yok | 154 | 127.55 | 319.77 | 4.4% | 20.9% |  | 7 | 0 |
| dis__lube | risk_butcesi_sinirsiz | 156 | 127.90 | 786.10 | 10.6% | 47.4% |  | 5 | 0 |
| dis__hma-atr-rider | gercek | 682 | 5.96 | 236.69 | 2.1% | 42.9% |  | 1206 | 0 |
| dis__hma-atr-rider | min_tutar_yok | 1616 | 52.31 | 215.96 | 1.5% | 43.3% |  | 197 | 0 |
| dis__hma-atr-rider | risk_butcesi_sinirsiz | 170 | -12.76 | 115.49 | -2.0% | 49.4% | 2015-07-17 | 0 | 0 |
| dis__voltarget-trend | gercek | 244 | -25.09 | 114.94 | -2.1% | 55.3% | 2022-04-22 | 435 | 0 |
| dis__voltarget-trend | min_tutar_yok | 628 | -33.84 | 114.62 | -2.1% | 55.4% | 2022-12-13 | 34 | 0 |
| dis__voltarget-trend | risk_butcesi_sinirsiz | 85 | -11.92 | 115.30 | -2.1% | 55.2% | 2015-10-08 | 0 | 0 |
| dis__haftalik-macd-gunluk-ma | gercek | 306 | 81.60 | 535.91 | 7.2% | 39.1% |  | 291 | 0 |
| dis__haftalik-macd-gunluk-ma | min_tutar_yok | 561 | 112.11 | 548.02 | 7.4% | 40.0% |  | 27 | 0 |
| dis__haftalik-macd-gunluk-ma | risk_butcesi_sinirsiz | 135 | -11.57 | 115.29 | -2.1% | 45.6% | 2018-10-31 | 2 | 0 |
| dis__e0v1en | gercek | 1935 | 128.59 | 750.32 | 20.2% | 28.2% |  | 513 | 13 |
| dis__e0v1en | min_tutar_yok | 2422 | 173.39 | 808.70 | 21.3% | 24.0% |  | 19 | 20 |
| dis__e0v1en | risk_butcesi_sinirsiz | 2328 | 144.54 | 856.04 | 22.2% | 28.2% |  | 90 | 43 |
