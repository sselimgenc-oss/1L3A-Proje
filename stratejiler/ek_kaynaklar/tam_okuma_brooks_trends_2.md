# Tam okuma: Al Brooks, Price Action Trends — sayfa 221-439 (parça: brooks_trends_2)

Kaynak metin: `veri/pdf_metin_2/kitap_diger/Price_Action_Trends_-_Al_Brooks_439_sayfa.txt` (`=== SAYFA n ===` numaraları kullanıldı).
Çıktı kartları: `veri/kartlar_ham/daytrade/Price_Action_Trends_-_Al_Brooks_439_sayfa__tam_brooks_trends_2.json` (10 yeni kart).
Önceden kartlı (tekrar yazılmadı): Trends dosyası (10 kart) + Trading Ranges dosyası (13 kart, aynı yazar).

## Okunan aralık ve kanıt (her ~20 sayfalık blokta işlenen konu)
- 221-240: Trend çizgisi/kanal çizgisi bölümü sonu (kanal çizgisi aşımı neden başarısız olur, son bayrağın eğimi) + Kanallar bölümü (vakum etkisi, kanal ters bayrak, ölçülü hareket = kanal yüksekliği, boğa kanalında yalnız trend yönü).
- 241-260: Kanal örnek grafikleri (kanal kırılımı, ölçülü hareket, limit emirle giriş) + Mikro kanallar (tanım, ilk kırılım kâr alımı, H1/L1, trend yönü).
- 261-280: Mikro trend çizgileri (başarısız kırılım, 1dk/5dk), Yatay çizgiler/salınım noktaları (aralık günü başarısız kırılım, ikinci giriş), Trendler bölümü girişi (bacak/salınım/geri çekilme tanımları).
- 281-300: Güçlü trendi fade etme, trend olgunlaşması ve kâr alma psikolojisi, "Nasıl trend ticareti yapılır" giriş listesi (stop ve limit girişleri), 20 boşluk çubuğu MA limiti.
- 301-320: Trend işlem yönetimi (2R yarım kâr, stop trail, boyut), GS trend günü örneği, Güç İşaretleri bölümü (özellikler listesi), Şekil 19.1-19.3.
- 321-340: Güç işaretleri (örnekler), İki bacak bölümü, Ortak trend kalıpları girişi, Spike ve kanal (özellikler, olasılıklar, ölçülü hareket, 3 itme).
- 341-360: Spike-kanal örnekleri (ardışık doruklar, gap spike, dik kanallar, kama), boşluk + çift dip örneği.
- 361-380: Spike ve doruk, Trend eden ticaret aralığı günleri (özellikler, ilk aralık = ort. günlük aralığın 1/3-1/2'si, olasılıklar, geç kırılım, örnek şekiller 22.1-22.7).
- 381-400: Şekil 22.8-22.10, Açık günden trend ve küçük geri çekilme trendleri (özellikler, yüzdeler, giriş türleri, yönetim, rapor saatleri).
- 401-420: Şekil 23.1-23.11 (gap ilk bar, küçük geri çekilme, ters yakalama), Geri dönüş günü bölümü giriş + örnek.
- 421-439: Geri dönüş (Şekil 24.1-24.3), Trend yeniden başlama günü (25.1-25.4), Merdivenler (26.1-26.3), yazar notu.

## Yeni kartlar (10) — hepsi `daytrade`
1. `daytrade__kanal-basarisiz-kirilim-olculu-hareket__brooks` (sayfa 222,230,231,236,239,242,245)
2. `daytrade__trend-geri-cekilme-limit-emir__brooks` (232,247,253,297,298,302,392)
3. `daytrade__mikro-trend-cizgisi-basarisiz-kirilim__brooks` (259-270,274)
4. `daytrade__salinim-noktasi-basarisiz-kirilim-ikinci-giris__brooks` (278-282)
5. `daytrade__trend-gunu-yonetim-2r-yari-swing-iz__brooks` (299-313)
6. `daytrade__guc-isaretleri-trend-gunu-filtresi__brooks` (314-329)
7. `daytrade__trend-araligi-olculu-hareket-bari-fade__brooks` (365-377)
8. `daytrade__ardisik-doruk-iki-bacakli-duzeltme__brooks` (291,307,333,338,352,357,358,422)
9. `daytrade__merdiven-kirilim-testi-limit-daralan-donus__brooks` (433-438)
10. `daytrade__gap-ilk-bar-trend-kirilimi__brooks` (390-393,401-405,420-422)

Not: 2 ve 5 giriş/yönetim bileşenleri, 6 filtre türüdür (tek başına işlem kuralı değil; Aşama 1'de ayrı modül olarak ele alınabilir). Hepsi kitabın "öznel okuma" doğası nedeniyle kodlanabilirlik 1-2; 3 yok.

## guncelleme_onerileri (mevcut kartlara eklenecek bilgi)
- `daytrade__spike-ve-kanal-trendi__brooks` — (s331) spike sonrası geri çekilme trend yönünde ≥%25; (s335) kanal hedefi: spike ilk barın open/low'undan son barın close/high'ına mesafe aynı yöne yansıtılır veya bacak1(spike)=bacak2(kanal); (s333) spike ardından aralık oluşursa ~1/3 vakada aralık ters yöne kırılır; (s330) kanalın trend yönünde kırılımı nadir, 5 çubuk içinde başarısız olur; (s334,344) kanal tabanı testi = çift dipli boğa bayrağı; (s352,357) 2 ardışık doruk sonrası ≥2 bacak, 3 sonrası daha büyük; (s349) kanal başlangıcı 1-2 günde test edilir; (s337) günün ikinci yarısında kanalda karşı trend riskli.
- `daytrade__trend-eden-ticaret-araligi-gunu__brooks` — (s364-365) ilk aralık = son günlerin ortalama aralığının ~1/3-1/2'si → kırılım, gün aralığı yaklaşık 2 katına; (s365) spike: 1-3 küçük çubuk, kuyruklu; (s366) kırılıma girmek düşük olasılık, kırılım geri çekilmesi/karşı taraf tercih; stop swing dibine trail edilmez; (s368) ~1/3 vakada sakin aralık günü; son saate kadar 5 puan aralık kalırsa ~%90 kapanıştan önce genişler; (s366-367) ölçülü hareket bölgesinde büyük trend barı fade (yeni kart 7).
- `daytrade__acik-trend-kucuk-geri-cekilme__brooks` — (s388-389) küçük geri çekilme günü: tüm geri çekilmeler ort. günlük aralığın %10-30'u (Emini 10-12 tik); gün içinde 11:00 PST sonrası önceki geri çekilmenin %150-200'ü (≈2 katı) büyüklüğünde geri çekilme; açıktan trend günlerin ~%20'sinde, küçük geri çekilme günü ayda 1-2; (s392) giriş: önceki çubuk dibi ± 1-2 tik limit veya H1/H2 +1 tik stop; en büyük geri çekilme 8 tik ise zirvenin 5-7 tik altına limit; (s393) başabaş stopuna acele edilmez, trail swing dibi altı; (s390) rapor çubuğu kapanmadan giriş yok, ilk bar sonrası 3.-4. barda duraklama yoksa %40 başarısız; (s400) ilk trend çizgisi kırılımı başarısız olur → ilk önemli geri çekilme alım.
- `daytrade__geri-donus-gunu__brooks` — (s419-421) geri dönüş günlerinin çoğu trend eden aralık günü olarak başlar; geri çekilmede güçlü karşı spike varsa dönüş olasılığı; ardışık 3 doruk sonrası büyük dönüş; (s422-423) büyük kama tabanı sonrası ≥2 bacaklı ralli ve kama çubuk sayısının ≥1/3'ü kadar düzeltme.
- `daytrade__trend-yeniden-baslama-gunu__brooks` — (s426) öğle ters yönlü kırılım 11:00-12:00 PST'de 1-2 çubukta başarısız; (s426-427) 3 tembel karşı trend itme = kama bayrağı, baş-omuz bayrağı; (s427) 2-3 gün sürebilir (5m'de aralık, 60m'de ABC); (s429-430) dar aralıktan çıkışta en iyi ölçülü hareket; ~%40 beklenenin tersi.
- `daytrade__merdiven-genis-kanal-gunu__brooks` — (s434) hızlanan merdiven kanaldan çıkarsa 2 bacak veya kanal yüksekliği; (s435-438) kırılım testi limit emirleri ve daralan merdiven dönüşü yeni kart 9 olarak çıkarıldı.
- `daytrade__mikro-kanal-gec-giris__brooks` — (s259-262) mikro kanal 2-10 çubuk; ilk kırılım kâr alımı; 10+ çubuk sürdürülemez; kırılımın çevrilmesi H1/L1 olarak yeni kart 3'te.
- `daytrade__iki-bacak-trend__brooks` — (s325-326) 3 itme modelinde bacaklar iki küçük bacaktan oluşabilir; (s325) trend çizgisi kırılımı yeni bacak başlangıcı.
- `daytrade__20-bosluk-cubugu__brooks` (Ranges kitabı) — (s282,297-298) 20 boşluk çubuğunda MA'nın 1 tik üstüne limit AL, 1-3 puan aşağıda ölçekle, çıkış ilk giriş fiyatı; (s282,319,397) MA'ya ilk dokunuş H2 ile birleşir; 11:30 PST sonrası sık.
- `daytrade__kama-geri-cekilme-ve-donus__brooks` (Ranges) — (s334,338) kama kanalında 3. itme + trend kanal çizgisi aşımı + ikinci giriş güçlü ters çubuk; (s341) kama tepesi yukarı kırılırsa spike olur, ölçülü hareket = kama yüksekliği; 5-10 çubuk sonra 2 bacaklı geri dönüş.
- `daytrade__ilk-hareketli-ortalama-boslugu__brooks` (Ranges) — (s248,319) güçlü trendde ilk MA boşluk çubuğu kurulumu genellikle trendin son bacağını başlatır, ardından zirve testi.
- `daytrade__olculu-hareket-bacak-esitligi__brooks` (Ranges) — (s335,345) spike(bacak1)=kanal(bacak2); (s349) 60dk spike kanal günü sonrası 2 haftada ölçülü ralli tamamlandı (tek örnek).
- `daytrade__yuksek2-dusuk2-trend-geri-cekilmesi__brooks` (Ranges) — (s270,302) güçlü trendde H1 da geçerli (aciliyet); H2 sinyal çubuğu altına düşerse H3/kama alımına dönüşebilir; şüpheli sinyalde yarım boy (s302); güçlü boğa trendinde L1/L2 sinyal çubuğu üstü kısa açılmaz, tuzak (s277,281).

## Kart çıkmayan bölümler ve nedeni
- Trend çizgisi/kanal bölümü (221-228) ve Kanallar teorik anlatımı (229-240): kurumların psikolojisi ve program ticareti açıklamaları kavramsal; ölçülebilir kısımlar kart 1-2'ye ve güncellemelere alındı.
- Trendler giriş (283-295): bacak/salınım/geri çekilme tanımları, hedge fon/emeklilik anlatıları — kavramsal.
- İki bacak (325-327): kavramsal, mevcut `iki-bacak-trend` kartı yeterli.
- Ortak trend kalıpları giriş (328-329): özet tavsiye; açılış aralığı yüzdeleri güncelleme önerilerine ve kart 6'ya işlendi.
- Spike-kanal şekilleri (341-360) ve Geri dönüş/Trend yeniden başlama/Merdiven örnek grafikleri: mevcut kartların örnek açıklamaları; yeni giriş-çıkış kuralı eklemedi (güncelleme önerileri yapıldı).
- Şekil 23.1-23.11: gün içi gerçek zamanlı okuma örnekleri; kural olarak kart 10, 2, 5'e işlendi.
- Yazar notu (439): kart yok.

## Notlar
- Kitaptaki sayısal değerlerin (puan, tik) çoğu E-mini (ort. günlük aralık 10-15 puan) ve ABD hisseleri (GS, AAPL, GOOG vb.) örneğindedir; 1L3A'ya taşırken günlük ortalama aralık veya ATR oranı olarak yeniden tanımlanması gerekir (kart `belirsizlikler` alanlarında önerildi, kural değil).
- Çoğu yüzde iddiası (%80 başarısız, %60 kazanma varsayımı, %40 başarısız) kitap sezgisidir, kanıtsızdır; backtestte doğrulanmadıkça kullanılmamalı.
- Limit emir girişleri (kart 2) ve ölçülü hareket/2R yarım kâr (kart 5) 5m mum verisiyle ancak yaklaşık simüle edilir; dolum varsayımı tutucu olmalı.
