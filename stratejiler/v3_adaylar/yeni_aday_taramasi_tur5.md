# Tur 5 madde 3: yeni aday taraması (gün içi kripto 5m-1h, funding/baz)
**Sonuç: BULUNAMADI.** Yeni aile getiren ya da mevcut temsilciden daha güçlü kanıtlı (makale + OOS + maliyet dahil + verimize uygun) aday çıkmadı. Kart yazılmadı; `adaylar.csv` ve `aileler_v3.csv`'ye satır eklenmedi. 17 arama + 8 sayfa açma.

## Tam metni açılıp okunanlar (hiçbiri aday değil)
- Bianchi-Babiak-Dickerson, Riksbank WP 413 (2022): günlük hacim şoku kesit ters dönüşü; maliyet long 20-30 bp / short 30-40 bp; değer ağırlıklıda net getiri anlamsız; ayrı OOS yok; küçük/illikit coinler. Günlük, kesit-ters-donus ailesi.
- Caporale-Plastun (FMPM 2020): maliyet YOK, parametreler örnek içinde seçilmiş, OOS yok.
- Kim-Hansen quarter-hour (2026): 10 sn ufku, order flow + ML, "kâr edilebilir değil".
- Kasinski funding risk faktörü (Mendeley veri seti): sabit funding hasadı, OOS yok; he-manela'dan zayıf.
- Concretum "Seasonality in Bitcoin intraday trend trading": blog, kural yok, maliyet yok, OOS yok.

## Yalnız özetten okunanlar (aday SAYILMADI)
Guo-Sang-Tu-Wang (JEDC 2024, dakikalık + LASSO, dışlama kapsamı); Kurihara-Matsumoto 2026 (ML); Han-Kang-Ryu (gerçekçi maliyetle Binance futures TSM/kesit momentum çoğunlukla anlamsız; tam metin açılmadı); MDPI/AFA funding-saati likidite makaleleri (getiri kuralı yok).

## Elenenler
He-Manela (zaten kart), Quantpedia saat anomalisi (zaten kart; maliyet raporlanmamış), Baur vd. 2019 (kalıcı değil), DTW lead-lag (ML), walk-forward MA (MA ailesi), Hu-Härdle-Kuo (tahmin), Alexander-Imeraj VRP (opsiyon verisi), Zhang tezi (kural okunamadı), Lima-Sebastião Amihud (kural yok), BAB/low-beta (anomali yok), Presto/Vine/levolytics (zaten kart), MEXC blog (brüt→net Sharpe 2,89 → -0,09).

## Boşluk değerlendirmesi
Gün içi 5m-1h: yayınlanmış kanıt ya maliyetsiz ya OOS'suz ya da dakika altı/order flow/ML. Funding/baz: kaliteli makaleler (He-Manela, Chi) zaten kartlı. BTC→alt lead-lag: OOS+maliyetli kanıt yalnız dakikalık/ML. Likidite kesiti: tradeable kural yok. Opsiyonsuz VRP: yok. Seans etkileri: kalıcı değil.

## Yan bulgu (ön kayıt maliyet ihtiyatı)
Han-Kang-Ryu (özetten) ve Bianchi vd. (tam metin): kesit momentum / ters dönüşün kazancı maliyet sonrası küçülüyor ya da illikit coinlerde toplanıyor; kesitsel temsilcilerin ön kaydında gerçekçi maliyet zorunlu.
