# Çapraz denetim: strateji-sg (KGT v3 + KMN) — model riski denetimi

Denetçi: day-trade-sg oturumu · 2026-10-12 · strateji-sg main `ffebf1b`, kagit-durum (son saat 2026-10-12 09:00 UTC).
Salt okunur: strateji-sg'ye commit/push yapılmadı. Ham 1S verisi (`data/kripto`) repoda yok ve bu konteynerden piyasa
verisi çekilemiyor. Bu yüzden nicel kanıtlar şu kaynaklardan:
- `ortak/backtest_gunluk_getiri.csv` ve `ortak/backtest_islemleri.csv` (strateji-sg),
- BTC günlük kapanışı (Binance),
- kod okuması.

Kullanılan betikler bu reponun dışında, oturum çalışma alanında.

## Özet tablo (günlük backtest getirileri, maliyet + fonlama dahil)
| | Yıllık | Maks. düşüş | Sharpe | IS 2020-23 Sh | OOS 2024+ Sh | 2022 | En kötü gün / hafta | CVaR95 (gün) | BTC kor./beta |
|---|---|---|---|---|---|---|---|---|---|
| KGT | %35,1 | −%29,5 | 1,30 | 1,31 | 1,32 | −%19,8 | −%8,7 / −%13,0 | −%2,8 | 0,48 / 0,21 |
| KMN | %58,7 | −%18,1 | 1,91 | 1,84 | 2,03 | +%18,1 | −%10,6 / −%13,2 | −%2,7 | −0,01 / −0,01 |
| %50/%50 | %48,2 | −%15,6 | 2,03 | 1,96 | 2,21 | −%2,2 | −%9,6 / −%6,7 | −%2,0 | 0,29 / 0,10 |

## Bulgular (15)
Önem: Y = yüksek, O = orta, D = düşük.

### 1) Model riski
1. **[Y] KGT'nin Sharpe'ı çoklu testten sonra istatistiksel olarak zayıf.**
   - Deflated Sharpe (Bailey–López de Prado; çarpıklık 1,55, basıklık +23,6) gözlenen SR 1,30:
     - N=20 bağımsız deneme → DSR 0,94,
     - N=100 → 0,83,
     - N=576 → **0,65** (0,95 eşiğinin altında).
   - Gerçek deneme sayısı yüksek: K5'te 576+1120 kombinasyon, ardından Faz 4–6 varyantları. Ayrıca `DURUM.md:126` "OOS birden çok kez incelendi" diyor.
   - KMN (N=576'da DSR 0,97) ve %50/%50 (0,99) sağlam.
2. **[O] KMN rejime bağımlı.**
   - 2021'de +%215 (getirinin büyük kısmı). 2021 hariç: Sharpe 1,70, yıllık %39,9.
   - 2023: +%1,8. 12 aylık kayan Sharpe dibi −0,37 (2023-07).
   - 2024+ OOS güçlü: Sh 2,03, yıllık %56, düşüş −%16,8.
   - Yürüyen pencere Sh 1,16–1,54 (`DENETIM.md`). Canlı beklenti için tam dönem Sharpe'ın ~%30 altı alınmalı.
3. **[O] KGT ayı piyasasında kırılgan.**
   - 2022: −%19,8. 12 aylık kayan Sharpe dibi −2,44 (2022-12).
   - BTC'nin −%5'ten kötü olduğu 88 günde KGT ortalaması −%1,28, KMN +%0,58.
4. **[D] Delist anında getiri 0 sayılıyor** (`backtest/momentum.py:104,136`).
   - Son fiyattan sonraki delist hareketi yok sayılıyor: long'da iyimser, short'ta kötümser.
   - Etkisi küçük (DENETIM: boşluk köprülenince %43,45 → %43,23). Point-in-time evren ve delist dahil veri doğru kurgulanmış.

### 2) Uygulama
5. **[Y] Backtest ile canlı aynı veri kaynağını kullanmıyor.**
   - Backtest: USDT-M vadeli fiyat ve evren. Canlı: spot fiyat (`canli/veri.py:1-3`).
   - Spot karşılığı olmayan vadeli-yalnız coinler canlı KMN ve KGT evreninden sessizce düşüyor (`canli/kagit.py:129, 206`).
   - Ekim evreninde aday örnekler: KORU, AKE, USELESS, HYPE (doğrulanmalı). Backtest bunları işliyor.
   - Ayrıca spot/vadeli baz farkı modellenmiyor.
6. **[Y] Canlı short fonlaması iyimser.**
   - OKX'te sembol yoksa sabit +%0,01 dönüyor (short **alır**); damga eşleşmezse en son oran kullanılıyor (`canli/veri.py:96-109`).
   - Sıkışan short'larda gerçek fonlama −%0,1 ile −%2/8s arası olabilir. Backtest gerçek Binance fonlamasını kullanıyor, canlı kullanmıyor.
7. **[O] Maliyet tüm coinlerde tek ve düz: %0,07/yön** (`momentum.py:22`, `kripto_final.py:39`).
   - Evrende sığ veya yeni coinler var: PUMP, LSK, QNT, WLD, USELESS, KORU.
   - Maliyet ×3'te Sh 1,63, yani 10 bin $ ölçeğinde sağlam. Sermaye büyürse piyasa etkisi (impact) modeli yok.
8. **[O] Canlıda 2 KMN defteri var, backtest ise 14 kaydırmanın ortalaması.**
   - DENETIM kendi verisi: 2 defterde Sh 1,41–1,90, düşüş %19–30 (medyan %22). −%18'lik backtest düşüşü canlı için iyimser.
   - B defteri ilk 7 gün boş: `durum.json` B={} 2.500 $, yani KMN sermayesinin yarısı şu an nakit.

### 3) Risk
9. **[Y] KMN short bacağında stop ve tek coin sınırı yok** (`momentum_sinyal.py:37-39`).
   - Ters oynaklık ağırlığı düşük oynaklıklı büyük coinleri büyütüyor. Canlı A defterinde (2026-10-10) XRP short %16,0, LTC short %14,6, WLD long %12,8.
   - Tarihsel kuyruk: en kötü gün −%10,6 (2021-02-20, bir önceki gün +%16,6), en kötü hafta −%13,2, aşırı basıklık 15,7.
   - %16'lık bir short'ta +%100'lük squeeze, defterde −%16 demek.
10. **[O] KGT topluluğu sahte çeşitlendirme.**
    - 6 alt portföy aynı sinyali farklı gün başlarıyla alıyor. 2021-02-20'de UNI, 6 alt portföyün 6'sında da açıktı (`ortak/backtest_islemleri.csv`).
    - `max_pay=0,25` alt portföy başına, yani KGT'nin %25'ine kadarı tek coin olabilir.
    - Sonuç: 2021-02-19'da +%18,7, ertesi gün −%8,7. %0,4 riskle bu, stopsuz piyasa değerlemesinden (MTM) gelen kuyruk.
11. **[O] Kriz gününde iki bacak birlikte kaybediyor.**
    - 2021-02-20'de KGT −%8,7, KMN −%10,6, birleşim −%9,6.
    - Ortalama korelasyon 0,29, ama kuyrukta "piyasa nötr" koruma vermiyor.

### 4) Kod / operasyon
12. **[O] Veri hataları sessiz geçiyor.**
    - `_get` 5 denemeden sonra `None` döndürüyor (`veri.py:17-28`). `mumlar` ilk boş sayfada kırılıyor, eksik geçmiş sessizce kabul ediliyor (`veri.py:63`).
    - Verisi gelmeyen coin o saatte işlenmiyor (`kagit.py:138`), yani KGT stop/çıkış kontrolü o saat atlanıyor.
    - `KMNDefter.fiyatla` eksik fiyatı atlıyor, değerleme bayat kalıyor (`motor.py:135`).
    - `dengele` fiyatı olmayan hedefi düşürüyor, brüt <1 oluyor (`motor.py:149`).
    - Bayat veri ya da eksik coin için alarm yok.
13. **[D] Telafi sınırı:** `TELAFI_MAKS_SAAT=168` (`kagit.py:29,112`). 7 günden uzun kesintide aradaki saatler sessizce atlanıyor ve stoplar işlenmiyor. Hata bildirimi yalnız GitHub e-postasına kalmış.
14. **[D] Tekrar üretilebilirlik zayıf.**
    - Ham veri (311 coin 1S, 1 dk BE çözümü) repoda yok; sonuçlar yalnız pickle'lardan yeniden üretilebiliyor.
    - `be_1dk.pkl` canlıda Binance 1 dk API'sine bağlı (`veri.py:74`).
    - Bağımlılıklar sabitlenmiş (iyi). Saat dilimi her yerde naive UTC ve tutarlı (sorun yok).
15. **[D] Rapor ile kod arasında sayı farkları var.**
    - KGT Sharpe: DENETIM 1,28; `ortak` CSV'den 1,30–1,31.
    - KMN Sharpe: DENETIM 1,86; CSV 1,91.
    - Panel ve rapor tek kaynaktan beslenmeli.

## Öneriler (Aralık v2 adayları — canlı bota dokunulmaz)
Seçim yalnız IS'e (2020-23) göre yapıldı. OOS = 2024+, stres = 2022. Hücreler: yıllık / maks. düşüş / Sharpe.

1. **Sermaye payı KGT %40 / KMN %60** (4 varyant denendi: 30/40/50/60).
   - IS-seçimi: 30/70 ve 40/60 eşit (Sh 2,01). Konsantrasyon riski (bulgu 9) yüzünden 40/60 seçildi.

   | | IS 2020-23 | OOS 2024+ | 2022 |
   |---|---|---|---|
   | 50/50 | %52 / −%15,6 / 1,96 | %43 / −%10,3 / 2,21 | −%2,2 |
   | **40/60** | %54 / −%14,5 / 2,01 | %46 / −%11,6 / 2,25 | +%1,6 |

   - Uyarı: KMN backtest'i canlıya göre iyimser (bulgu 5, 6, 8). Önce bulgu 5–6 düzeltilip kağıtta doğrulanmalı.
2. **KMN oynaklık hedefleme** (hedef yıllık %25, 30 günlük gerçekleşen oynaklık, ölçek ≤1; 6 varyant: hedef %15/20/25 × pencere 30/60).
   - IS-en iyi:

   | | IS 2020-23 | OOS 2024+ | 2022 |
   |---|---|---|---|
   | Taban | %61 / −%18,1 / 1,84 | Sh 2,03 | Sh 1,06 |
   | **%25 / 30g** | %44 / −%16,3 / 1,85 | %56 / −%16,8 / 2,16 | Sh 1,09 |

   - Alfa kazancı yok, bir risk düğmesi. %15 hedef düşüşü −%12'ye indiriyor, getiri %29'a düşüyor.
3. **KMN tek coin sınırı (≤%10 brüt) + short fonlama/squeeze freni.** Bulgu 9'a karşı önerildi.
   - Ham veri olmadığı için **burada test edilemedi**. strateji-sg sahibi kendi verisiyle IS/OOS/2022 olarak test etmeli.
   - Reddedilen alternatif: KGT'ye BTC SMA100/200 rejim filtresi (2 varyant). İşlem düzeyinde, 2021-06 → 2026-09:
     - 2022 zararını −%22 → −%2,5 / 0'a indiriyor,
     - ama elenen işlemler diğer yıllarda çok kârlı (PF 2,0–2,5): toplam katkı +%129 → +%57–60, IS PF 1,50 → 1,09.
     - **Önerilmez** (strateji-sg Faz 4 G3 bulgusuyla tutarlı).
