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

## Önce elindeki ham listeyi işle (limit tasarrufu)
`stratejiler/v3_adaylar/ham/MASTER_katalog_2026-11.csv` (251 satır, 2026-11-07 taraması: Quantpedia, Quantocracy, MQL5) ve yanındaki
.md özetleri daha önce bulundu, işlenmedi. Yeni aramadan ÖNCE: `durum` = izle veya aday olan satırları tekrar kontrolünden geçir,
verimize ve kurallara uyanları kart yap. `elendi` ve `bilgi` satırları da ön elemeden geçer (eski karar yeniden kontrol edilir). Sonra kalan limitle aşağıdaki boşlukları ara.
Bu ham dosyaları değiştirme.
Ayrıca kullanıcının başka oturumda derlediği kataloglar (aynı klasör, 2026-11-10 eklendi). İşleme sırası:
1. `github-backtest-katalog-denetimli__dogrulanan_48.csv` (doğrulanmış 48), sonra `__tumu.csv` içinde `nihai` = GERÇEK-TEMİZ olanlar
   ve diğer TÜM satırlar (ŞÜPHELİ, BELİRSİZ, ÖRNEK, ARAÇ, KOPYA dahil; sıra yalnız önceliktir, hiçbir satır atlanmaz).
2. `github-backtest-katalog-v4__sayfa_dogrulamasi.csv`, `diger-siteler-derin-21.csv`, `*__b_duzeyi.csv` (asya, bölgesel).
3. `github-backtest-katalog-v4__reddit.csv`, `__diger_siteler.csv`, `*__tumu.csv` (asya, bölgesel): en düşük öncelik.
Repo listelerinde lisansı GPL/AGPL olanlardan yalnız kural mantığı alınır. Yayımlanmış Sharpe/getiri iddiaları kanıt değildir;
`kanit` alanına "iddia (doğrulanmadı)" diye yazılır.

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
0. `stratejiler/v3_adaylar/on_eleme.csv` (yukarıda).
1. `stratejiler/v3_adaylar/kartlar/<kart_id>.json`: aday başına bir kart, KART_SEMASI alanlarıyla. Farklar:
   `kaynak` = {"url": "...", "lisans": "MIT / GPL-3.0 / makale / bilinmiyor", "tur": "makale|github|tv|blog"};
   ek alan `kanit` = yayımlanmış sonuç / örneklem dışı kanıt özeti (yoksa null; uydurma rakam YOK);
   ek alan `veri_uygun` = true/false + neden. Kurallar kesin ve ölçülebilir olmalı (giriş, stop, çıkış).
2. `stratejiler/v3_adaylar/adaylar.csv`: kart başına bir satır. Sütunlar:
   kart_id, ad, kaynak_url, lisans, tur, stil, zaman_dilimi, kategori, piyasa, kanit_var, benzer_mevcut (dis_envanter/havuz'daki en yakın ad ya da yok), oncelik (1-3), not
3. `stratejiler/v3_adaylar/RAPOR.md`: kısa Türkçe özet; kaç kaynak tarandı, kaç aday, kaç elendi ve neden, Fable hakem sonucu.

## Hedef: açık kaynak kodlu HER stratejiyi kaçırmadan eleme (kullanıcı isteği 2026-11-10)
İki aşama; sayı sınırı yok:
KULLANICI KURALI: SINIR YOK. Ham klasördeki ~1300 satırın HEPSİ titizlikle incelenir; nereden ne çıkacağı belli olmaz.
1. ÖN ELEME (Haiku ajanları, ucuz): ham listelerdeki HER satır için (kaynak linki/kodu açılıp bakılarak) `stratejiler/v3_adaylar/on_eleme.csv`'ye
   bir satır: kaynak_dosya, satir_no, ad, url, lisans, karar (kart|tekrar|veri_yok|yasak|arac|kod_yok|belirsiz), neden, benzer_mevcut.
   ARAÇ/ÖRNEK/KOPYA satırları da açılıp bakılır (içinde strateji olabilir); hiçbir satır sessizce atlanmaz.
   `belirsiz` çıkanlara Sonnet ikinci kez bakar.
2. KART (Sonnet): `karar = kart` olan HER satır için kart yazılır (sayı sınırı yok). Limit biterse kaldığın yer
   RAPOR.md'ye yazılır; bir sonraki oturum oradan devam eder. Ara ara commit + push yap ki iş kaybolmasın.
Kart yazmadan önce tekrar kontrolü yap.

## Model kullanımı (limit tasarrufu)
- Ana oturum (Sonnet 5.5): arama, okuma, kart yazma.
- Haiku ajanı: tekrar kontrolü (adayı dis_envanter.csv / havuz_v2.csv ile karşılaştırma), CSV/JSON biçim kontrolü, link kontrolü.
- Opus: kullanılmaz (gerekmez).
- Fable: EN SONDA, bir kez. Tüm kartları hakem olarak değerlendirir: kurallar kodlanabilir mi, lookahead var mı, kanıt sağlam mı,
  aşırı uydurma (çok parametre) riski. Her karta 0-10 puan + kısa gerekçe; en iyi 15-20'yi işaretler (test hepsine yapılır; puan yalnız sıra içindir). Sonucu RAPOR.md'ye yaz,
  `oncelik` sütununu buna göre güncelle.

## Bitiş
PR açıldığında dur. PR açıklamasına aday sayısını ve Fable'ın ilk 15-20 listesini yaz.
