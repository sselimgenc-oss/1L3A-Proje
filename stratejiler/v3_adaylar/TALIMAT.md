# v3 aday araştırma oturumu: talimat

Bu oturumun TEK işi: 1L3A projesi için açık kaynak strateji ADAYI bulmak ve kart olarak yazmak.
Kod yazmaz, test koşmaz, başka dosyaya dokunmaz. Bunun dışında bir şey istenirse reddet ve kullanıcıya söyle.

## Yazma izni (kesin)
- Yalnız `stratejiler/v3_adaylar/` altına dosya EKLE. Repo'nun başka hiçbir dosyasını değiştirme, silme.
- Bu TALIMAT.md'yi değiştirme.
- Kendi dalında commit + push, sonra main'e PR AÇ. PR'ı BİRLEŞTİRME (birleştirmeyi ana oturum, denetimden sonra yapar).
- Gizli anahtar, token, PDF metni, üçüncü taraf kod dosyası ASLA commit edilmez. GPL/AGPL kod kopyalanmaz; yalnız kural mantığı kendi cümlelerinle yazılır.

## Önce oku
- `CLAUDE.md`, `DURUM.md` (yalnız bağlam için; oradaki "sıradaki işler" senin işin DEĞİL).
- `stratejiler/KART_SEMASI.md` (kart formatı).
- `stratejiler/dis_envanter.csv` ve `stratejiler/havuz_v2.csv`: zaten elimizde olanlar. Aynısını ya da küçük varyantını getirme.

## Ne arıyoruz (öncelik sırasıyla)
1. Gün içi kripto (5m–1h): elimizde az ve zayıf.
2. Piyasa yönünden bağımsız kripto: funding, baz (perp–spot), coinler arası göreli güç / kesit sıralama.
3. Yayımlanmış kanıtı olan stratejiler: SSRN/arXiv makaleleri, yazarı örneklem dışı ya da farklı piyasada da sonuç göstermiş olanlar.
   Rastgele TradingView scripti en düşük öncelik.

## Kesin dışlama
- Martingale, DCA, ortalama düşürme, stopsuz ızgara.
- Geleceği gören (lookahead) ya da yeniden çizen (repaint) gösterge; makine öğrenmesi modeli.
- Verimizde olmayan veri: yalnız Binance USDT-M perp kripto (OHLCV + funding) ve Dukascopy hisse/emtia OHLCV var
  (sembol listesi `veri/sembol_envanteri.csv`). Order book, haber, on-chain, opsiyon verisi YOK.
- 5m altı zaman dilimi.

## Çıktı
1. `stratejiler/v3_adaylar/kartlar/<kart_id>.json`: aday başına bir kart, KART_SEMASI alanlarıyla. Farklar:
   `kaynak` = {"url": "...", "lisans": "MIT / GPL-3.0 / makale / bilinmiyor", "tur": "makale|github|tv|blog"};
   ek alan `kanit` = yayımlanmış sonuç / örneklem dışı kanıt özeti (yoksa null; uydurma rakam YOK);
   ek alan `veri_uygun` = true/false + neden. Kurallar kesin ve ölçülebilir olmalı (giriş, stop, çıkış).
2. `stratejiler/v3_adaylar/adaylar.csv`: kart başına bir satır. Sütunlar:
   kart_id, ad, kaynak_url, lisans, tur, stil, zaman_dilimi, kategori, piyasa, kanit_var, benzer_mevcut (dis_envanter/havuz'daki en yakın ad ya da yok), oncelik (1-3), not
3. `stratejiler/v3_adaylar/RAPOR.md`: kısa Türkçe özet; kaç kaynak tarandı, kaç aday, kaç elendi ve neden, Fable hakem sonucu.

## Hedef sayı
En çok 40 aday kart. Az ve kaliteli, çok ve zayıftan iyidir. Kart yazmadan önce tekrar kontrolü yap.

## Model kullanımı (limit tasarrufu)
- Ana oturum (Sonnet 5.5): arama, okuma, kart yazma.
- Haiku ajanı: tekrar kontrolü (adayı dis_envanter.csv / havuz_v2.csv ile karşılaştırma), CSV/JSON biçim kontrolü, link kontrolü.
- Opus: kullanılmaz (gerekmez).
- Fable: EN SONDA, bir kez. Tüm kartları hakem olarak değerlendirir: kurallar kodlanabilir mi, lookahead var mı, kanıt sağlam mı,
  aşırı uydurma (çok parametre) riski. Her karta 0-10 puan + kısa gerekçe; en iyi 15-20'yi işaretler. Sonucu RAPOR.md'ye yaz,
  `oncelik` sütununu buna göre güncelle.

## Bitiş
PR açıldığında dur. PR açıklamasına aday sayısını ve Fable'ın ilk 15-20 listesini yaz.
