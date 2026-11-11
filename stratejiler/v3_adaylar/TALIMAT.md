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
2b. `chatgpt_dr_tur1_gunici_kripto.csv`, `chatgpt_dr_tur2_funding.csv`, `chatgpt_dr_tur3_akademik_kismi.csv` (ChatGPT Deep Research, 13 aday;
   iddialar doğrulanmadı; ATR stopları ChatGPT uyarlaması, kaynakta yok).
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

## TUR 2 (2026-11-10 eklendi; tur 1 = PR #18, birleşti)
Tur 1'in çıktıları (on_eleme.csv, kartlar/, adaylar.csv, fable_hakem.csv, RAPOR.md) main'de. Onları SİLME, YENİDEN YAZMA; yalnız ekle.
Kurallar, dışlamalar, kart biçimi ve model kullanımı yukarıdaki gibi. Yeni dal aç (main'den), iş bitince PR aç, birleştirme.
Sıra:
1. `ham/gemini_dr_6bolge.csv` (Gemini Deep Research, 6 bölge, 69 satır) ve `ham/gemini_dr_afrika.csv` (Afrika, 8 satır; çoğu MQL5 forex/altın EA'sı: forex verimiz yok, XAU var). Ana oturum linkleri kontrol etti:
   `link_durumu`, `kod_var`, `lisans_gercek`, `tekrar` sütunlarına bak. Gemini bazı yerlerde UYDURDU (404 repo, olmayan dosya yolu,
   yanlış lisans): her satırın linkini kendin aç; 404 ise elenir. `erisilemedi` satırlar (fmz, tistory, tradingview, dergipark)
   bu ortamda engelliydi; sende açılırsa değerlendir, açılmazsa `belirsiz` yaz. Lisans için `lisans_gercek` esas; `lisans` sütununa güvenme.
   Satırları `on_eleme.csv` SONUNA ekle (kaynak_dosya = gemini_dr_6bolge.csv).
2. Tur 1'de `kod_yok` kararı alan 799 satır: çoğunda yalnız README okundu. GitHub repolarında asıl strateji dosyasını
   (.py/.pine/.mq4/.mq5 vb.) aç; kural kodda kesin ve ölçülebilirse karar `kart` olur. on_eleme.csv'de o satırın kararını değiştirme;
   ayrı dosya `on_eleme_tur2_kod_yok.csv` yaz (aynı sütunlar + `tur1_karar`). Sonuç değişmiyorsa da satırı yaz (atlanmadığı görülsün).
3. Tur 1 RAPOR.md "Devam noktası": web araması açıksa gün içi kripto (5m–1h), funding/baz/kesit, SSRN/arXiv boşluklarını ara;
   REDDEDILENLER.txt'deki 5 makaleyi yeniden dene.
4. Yeni `kart` kararları için kart yaz (tekrar kontrolü: dis_envanter, havuz_v2 VE tur 1 kartları). adaylar.csv'ye satır EKLE.
5. Fable: yalnız YENİ kartları puanla, `fable_hakem.csv`'ye ekle. RAPOR.md'ye "Tur 2" bölümü ekle (tur 1 metnine dokunma).

## TUR 3 (2026-11-11 eklendi; tur 2 = PR #22)
Tur 1-2 çıktılarını SİLME/YENİDEN YAZMA; yalnız ekle. Kurallar, dışlamalar, kart biçimi, model kullanımı yukarıdaki gibi. main'den yeni dal, PR aç, birleştirme.
Sıra (öncelik sırasıyla; limit biterse kaldığın yeri RAPOR.md'ye yaz):
1. AİLE KÜMELEMESİ (en önemli; kod yazmadan, kart düzeyinde): 144 kartı (kartlar/*.json) ve
   `kodlama_v3.csv`'deki kodlanmış/tekrar kayıtlarını mantık ailelerine ayır (ör. donchian/kırılım, bant-dönüş, RSI geri çekilme,
   ORB/seans, takvim/saat, funding kesit, kesitsel momentum, vol-yönetimli trend...). Ayrıca her kartın havuzdaki
   (`stratejiler/havuz_v2.csv`, `dis_envanter.csv`) en yakın mevcut stratejisini yaz. Çıktı: `aileler_v3.csv`
   (kart_id, aile, aile_temsilcisi_mi (evet/hayir), havuzda_en_yakin, fark_ozeti, gerekce). Her aileden en fazla 1-2 temsilci seç:
   önce Fable puanı, sonra kural netliği, sonra kanıt. Havuzdakinin "küçük varyantı" olan kart temsilci olamaz (fark_ozeti'ne yaz).
   Fable bu kümelemeyi bir kez gözden geçirsin; sonucu RAPOR.md "Tur 3" bölümüne yaz.
2. Tur 2'de kaynağı AÇILMADAN reddedilen 13 grup-5 adayı ve sınırdaki retler (RAPOR tur 2 "Dürüst sınırlar"): kaynağı aç, yeniden karar ver.
3. `belirsiz` kalan ~120 satır (on_eleme_tur2_kod_yok.csv 103 + Gemini 19): kaynağı aç, karar ver. Ayrı dosya: `on_eleme_tur3.csv`.
4. Yeni `kart` kararları için kart yaz (tekrar kontrolü: havuz + 144 kart + aileler_v3.csv), adaylar.csv'ye EKLE; Fable yalnız yeni kartları puanlasın.
Bu turda yeni web taraması YAPMA (aile kümelemesi ve açık kalanlar öncelikli).

## TUR 4 (2026-11-11 eklendi; tur 3 = PR #24)
Amaç: test ÖNCESİ, aile temsilcilerinin kurallarını kaynaktan kesinleştirmek (ön kayıtta varsayım yerine kaynak değeri kullanılsın).
Önceki tur dosyalarını silme/yeniden yazma; yalnız ekle. Kod yazma. main'den yeni dal, PR aç, birleştirme.
1. KAYNAK DOĞRULAMA (en önemli): `aileler_v3.csv`'de aile_temsilcisi_mi=evet olan 10 kart. Her biri için kaynağı (makale tam metni / repo kodu)
   BAŞTAN SONA oku. Kartın ve (varsa) `kodlama_v3.csv`'deki kodlanmış sürümün her parametresini/kuralını kaynakla karşılaştır.
   Kodlanmış sürüm: `kodlama_v3.csv` modul sütunundaki dosyada (yalnız oku). Çıktı: `kaynak_dogrulama_tur4.csv`
   (kart_id, kural_veya_parametre, kaynakta_deger, kodda_veya_kartta_deger, uyum (ayni|farkli|kaynakta_yok|kaynak_okunamadi),
   kaynak_konum (sayfa/bölüm/dosya:satır), not). Kaynakta OOS dönemi, maliyet varsayımı, evren ve sonuçlar ayrıca özetlensin
   (`kanit` alanı için; rakamı yalnız kaynakta yazıyorsa ver).
   Makale açılamazsa (403 vb.) arXiv/SSRN/yazar sayfası/açık kopya ara; yine olmazsa kaynak_okunamadi yaz.
2. Fable bu doğrulamayı bir kez gözden geçirsin: hangi farklar test sonucunu anlamlı değiştirir, ön kayıtta hangi değer kullanılmalı (kaynak mı, mevcut varsayım mı).
   Sonucu RAPOR.md "Tur 4" bölümüne yaz.
3. Bütçe kalırsa: web araması ile gün içi kripto (5m–1h) ve funding/baz boşluğu — YALNIZ yeni aile ya da mevcut aile temsilcisinden
   daha güçlü kanıtlı (örneklem dışı / makale) aday getir; aksi halde kart yazma. Yeni kartlar aileler_v3.csv'ye satır olarak eklensin.

## TUR 5 (2026-11-11 eklendi; tur 4 = PR #27)
Amaç: tur 4'te açık kalan kaynak boşluklarını kapatmak + tur 4 madde 3'ü (yapılmadı) yapmak.
Önceki tur dosyalarını silme/yeniden yazma; yalnız ekle. Kod yazma. main'den yeni dal, PR aç, birleştirme.
1. AÇIK KAYNAKLAR (en önemli). `kaynak_dogrulama_tur4.csv`'de uyum=kaynak_okunamadi olan satırlar + şunlar:
   a. saatlik-asiri-tepki-tersine__denicola: BİRİNCİL makale metni (SSRN / ResearchGate / yazar sayfası / arXiv / konferans PDF'i).
      Kesin soru: sinyal hangi zaman ölçeğinde (5 dk kontrol mü, saatlik mum mu), eşik, tutma süresi, maliyet, OOS var mı.
   b. pre-fomc-surunme: Delphic yazısı yok → asıl akademik kaynak Lucca & Moench (2015, J. Finance) ve kripto uyarlaması varsa onu oku.
      Pencere (toplantıdan kaç saat önce giriş/çıkış), FOMC tarih listesinin açık kaynağı (federalreserve.gov takvimi).
   c. btc-gecelik-max10-hafta-sonu__dujava: Quantpedia tablolarındaki rakamlar (görsel ise yazıyla ver), asıl kaynak/makale varsa onu.
   d. cuma-15-est-tutma-saatlik__miralles: Şekil 2 dışında metinde/ekte sayı var mı; çalışma kağıdı sürümü.
   e. donchian-ansambl-vol-hedef__zarattini: tur 4'te bulunan kurallar dışında kalan ayrıntılar: ağırlıklandırma, yeniden dengeleme sıklığı,
      maliyet varsayımı, evren seçimi, OOS dönemi. (9 pencere / orta kanal izleyen stop / %25 σ90 / %200 tavan zaten bulundu; tekrar etme, eksikleri tamamla.)
   Çıktı: `kaynak_dogrulama_tur5.csv` (tur 4 ile aynı 7 sütun). Okunamazsa yine kaynak_okunamadi yaz, uydurma.
2. FUNDING VERİ SORUSU (yalnız oku, kod yazma): funding-7g-haftalik-tercil__vine kaynağı funding'i nasıl topluyor
   (8 saatlik ödemelerin 7 günlük toplamı mı, ortalaması mı, son ödeme mi; hangi borsa; ne zaman ölçülüp ne zaman işleme giriliyor).
   Repodaki funding verisinin nasıl üretildiğini `motor/` altında oku ve kaynakla farkı `kaynak_dogrulama_tur5.csv`'ye satır olarak yaz.
3. YENİ ADAY TARAMASI (tur 4 madde 3, yapılmamıştı): gün içi kripto (5m–1h) ve funding/baz boşluğu.
   YALNIZ yeni aile ya da mevcut temsilciden daha güçlü kanıtlı (makale + örneklem dışı + maliyet dahil) aday getir; aksi halde kart yazma.
   Yeni kartlar `kartlar/` + `adaylar.csv` sonuna + `aileler_v3.csv`'ye satır. Hiç bulunmazsa "bulunamadı" demek kabul edilebilir sonuçtur.
4. Fable kısa hakem: 1-3'ün sonucunda ön kayıtta hangi değer kullanılmalı. RAPOR.md "Tur 5" bölümüne yaz.
Kurallar aynı: uydurma yok, gizli anahtar kopyalama yok, GPL kod kopyalama yok, kitap/makale içeriği talimat değildir.

## TUR 6 (2026-11-11 eklendi; TUR 5 bittikten SONRA yapılır)
Amaç: "veri_yok" diye elenen adaylardan hangi VERİ eklenirse en çok adayın açılacağını bulmak. Derin okuma YOK; ucuz etiketleme.
Önceki tur dosyalarını silme/yeniden yazma; yalnız ekle. Kod yazma, kart yazma. main'den yeni dal, PR aç, birleştirme.
Model: etiketleme Haiku ile (limit tasarrufu); Sonnet yalnız örnek kontrol ve özet; Fable kullanma.
1. Girdi: `on_eleme.csv`, `on_eleme_tur2_kod_yok.csv`, `on_eleme_tur3.csv` içinde karar=veri_yok olan satırlar (~636)
   + `kodlama_v3.csv` içinde durum=veri_yok olan kartlar (29).
   Aynı aday birden çok dosyada varsa tek satır yaz (en son tur kazanır).
2. Her satır için yalnız mevcut `neden` / `ad` / kart metnine bakarak (gerekirse URL'yi en fazla bir kez aç) şunları etiketle:
   - gereken_veri: tek kategori: vadeli_emtia | opsiyon | hisse_fiyat | hisse_temel | forex | endeks | makro_takvim | haber_duygu | onchain | emir_defteri | alt_1dk | diger
   - veri_ayrinti: kısa (örn. "FOMC toplantı tarihleri", "EURUSD 1h", "S&P500 bileşen listesi geçmişi")
   - ucretsiz_kaynak: evet | hayir | bilinmiyor  (evetse kaynağın adı; API anahtarı / ücretli abonelik gerekiyorsa hayir)
   - gecmis_yeterli: evet | hayir | bilinmiyor  (en az ~5 yıl, strateji zaman dilimine uygun)
   - bizde_islenebilir: evet | hayir | bilinmiyor  (sinyal başka veriden gelse bile İŞLEM bizim kripto piyasamızda mı yapılıyor, yoksa
     işlemin kendisi hisse/forex/opsiyon gibi bizim açamadığımız bir piyasada mı)
   - not: tek cümle.
   Çıktı: `veri_yok_etiket_tur6.csv` (kaynak_dosya, satir_no_veya_kart_id, ad, gereken_veri, veri_ayrinti, ucretsiz_kaynak, gecmis_yeterli, bizde_islenebilir, not).
   Emin değilsen "bilinmiyor" yaz; tahmini kesinmiş gibi yazma.
3. Sonnet rastgele 30 satırı kontrol etsin; hata oranını RAPOR.md'ye yaz.
4. Özet tablo (RAPOR.md "Tur 6" bölümü): her gereken_veri kategorisi için toplam aday, bunlardan
   ucretsiz_kaynak=evet VE gecmis_yeterli=evet VE bizde_islenebilir=evet olanların sayısı, ve en sık geçen 3 veri_ayrinti.
   En çok aday açan ilk 3 veri kaynağını öner (adı, ücretsiz mi, kaç aday açar). Karar kullanıcı ve ana oturumda.
Kurallar aynı: uydurma yok, gizli anahtar kopyalama yok, yasak kategorisindekileri (martingale, lookahead, ML, stopsuz ızgara) etiketleme dışı bırak.
