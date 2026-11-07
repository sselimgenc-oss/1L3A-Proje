# Arşiv ön eleme sonuçları

Tarih: 14 Ekim 2026

Bu test, canlı Yahoo/Binance erişimi proxy tarafından engellendiği için Plotly'nin MIT
lisanslı `all_stocks_5yr.csv` veri kümesiyle yapılmıştır. Dönem 2013–2018'dir. Sonuçlar
güncel doğrulama değildir, paper-test başlatmaz ve veri kümesi hayatta kalma/seçim yanlılığı
taşıyabilir.

## Üç seçili hisse testi

AAPL, MSFT ve NVDA üzerinde ilk sonuçlar:

- Fraktal Kırılım: üç hissede pozitif; medyan getiri %53,9, OOS %32,9, PF 3,68. Üç
  hissenin ikisi kârlılık kapısını geçti. İlk bakışta ilerletildi.
- Kanal Ortalamaya Dönüş: üç hissede pozitif; medyan PF 2,55 ve düşüş %11,7 altında,
  fakat medyan yalnız 12 işlem ve AAPL OOS negatif. Düşük güvenle izlendi.
- Sıkışma Kırılımı: üç hissede pozitif; medyan PF 2,14, fakat medyan 11 işlem ve MSFT
  OOS negatif. Düşük güvenle izlendi.
- AO/AC: üç hissede pozitif ve medyan 62 işlem; NVDA düşüşü %35,24 ile sınırı az farkla
  aştı.
- MACD+SMA200: AAPL/NVDA pozitif, MSFT -%20,5; MSFT PF 0,65 ve stres sonucu negatif.
- SuperTrend: üç hissede pozitif; NVDA düşüşü %41,9 olduğu için ilerletilmedi.

## 483 hisselik genişlik testi

En az 1.000 barı olan 483 ABD hissesi, aynı parametrelerle ve hisse başına 6 baz puan
tek-yön maliyetle test edildi.

| Strateji | Pozitif pay | Stres pozitif | Medyan PF | Medyan OOS | Medyan işlem | Karar |
|---|---:|---:|---:|---:|---:|---|
| Kanal Ortalamaya Dönüş | %62,3 | %57,8 | 1,32 | %0,83 | 9 | Düşük örnekle öncelikli izle |
| SuperTrend Rejim | %56,3 | %53,0 | 1,20 | %3,45 | 12 | Zayıf genişlikle izle |
| AO/AC Bölgeleri | %56,5 | %43,3 | 1,12 | %3,82 | 57 | Maliyet dayanıklılığı yetersiz |
| Fraktal Kırılım | %50,3 | %47,4 | 1,06 | %0,82 | 14 | Seçili-hisse başarısı genellenmedi |
| MACD+SMA200 | %50,1 | %44,7 | 1,08 | %1,47 | 29 | Genişlik ve stres yetersiz |
| Sıkışma Kırılımı | %43,5 | %40,0 | 0,89 | %0,00 | 9 | Mevcut kural elendi |

İkinci dalgada aynı genişlik testine üç model daha, parametre optimizasyonu yapılmadan eklendi:

| Strateji | Pozitif pay | Stres pozitif | Medyan PF | Medyan OOS | Medyan işlem | Karar |
|---|---:|---:|---:|---:|---:|---|
| Double CCI + HMA | %57,6 | %47,8 | 1,15 | %3,31 | 53 | Üç-hisse başarısı genellenmedi |
| Triple CCI + MFI | %54,7 | %50,3 | 1,15 | %3,37 | 29 | Genişlik yetersiz |
| KST Momentum | %45,8 | %42,2 | 0,95 | %0,02 | 10 | Mevcut uyarlama elendi |

## Al-tut karşılaştırması

Her strateji satırı aynı sembol/dönemde, aynı sonraki-bar yürütme ve maliyet modeliyle
hesaplanan al-tut benchmarkına bağlandı. Dokuz modelin de 483 hisselik medyan toplam ve OOS
fazla getirisi negatiftir. Bu dönem güçlü bir hisse boğa piyasası olduğu için nakitte kalan
stratejilerin al-tutun gerisinde kalması beklenebilir; sonuç yine de mutlak kâr ile piyasa
üstünlüğünün aynı şey olmadığını gösterir. Fazla getiri paper için katı veto değildir fakat
panoda ayrı raporlanır.

## Karar

Arşiv tek başına hiçbir modeli paper'a geçirmez. Canlı çoklu-piyasa testinde öncelik:

1. Kanal Ortalamaya Dönüş — en iyi genişlik, ancak düşük işlem sayısı nedeniyle daha uzun
   veri şart.
2. SuperTrend Rejim — ikinci doğrulama adayı; düşüş kontrolü gerekiyor.
3. Double CCI+HMA — seçili üç hissede güçlü, fakat geniş evrende stres payı yetersiz; yalnız
   canlı çoklu-piyasa doğrulamasında izlenecek.
4. Triple CCI+MFI ve AO/AC — maliyet dayanıklılığı sınırlı; doğrudan paper'a geçmez.
5. Fraktal — üç seçili hissedeki güçlü sonuç geniş evrende kaybolduğu için geri düşürüldü.
6. MACD+SMA200 — ilk dalgada ilerletilmeyecek.
7. KST ve Sıkışma Kırılımı uyarlamaları — mevcut biçimleriyle elendi; PDF beyanları
   doğrulanmış sayılmaz.

Canlı veri açıldığında dokuz model tam kripto/ABD/BIST/emtia matrisinde yeniden koşacak;
arşiv sonuçları paper uygunluğu üretmeyecektir.
