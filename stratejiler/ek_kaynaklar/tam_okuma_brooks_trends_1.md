# Tam okuma: Al Brooks, Price Action Trends, sayfa 1-220 (parca: brooks_trends_1)

Kaynak metin: `veri/pdf_metin_2/kitap_diger/Price_Action_Trends_-_Al_Brooks_439_sayfa.txt` (dosya sayfa numaralari). Sayfa 1-220 tamamı sırayla okundu.
Çıktı: `veri/kartlar_ham/daytrade/Price_Action_Trends_-_Al_Brooks_439_sayfa__tam_brooks_trends_1.json` (9 yeni kart, kart_id sonu `_t1`).

## Okuma kanıtı (blok / konu)
- 1-19: içindekiler ve terimler sözlüğü (sinyal çubuğu, H1/H2/L1/L2, ii/iii/ioi, MA boşluk çubuğu, mikro kanal, kama, dikenli tel vb. tanımları; kart yok, tanımlar kartlara işlendi).
- 20-40: giriş; kurumlar, göstergelere ve habere güvenmeme, martingale reddi, 50-50 belirsizlik ilkesi (kart yok, genel felsefe).
- 41-60: kumar/satranç benzetmesi, çöküşler, kitap haritası; güç işaretleri listesi (trend, kırılım ve ters çevirme güç ölçütleri, s46-53) ve çubuk sayımı (H1-H4, s53-54).
- 61-80: fiyat hareketi tanımı, kurumsal akış ve HFT, aşırılık, ABC iki bacak (PI.1), Bölüm 1 spektrum (kart yok).
- 81-100: Bölüm 2 trend çubukları/doji/climax (tükenme), Bölüm 3 kırılma-test-geri dönüş; Bölüm 4 sinyal çubuğu temelleri (s100-105) -> kart 1 için giriş/stop mantığı.
- 101-120: Bölüm 5 ters çubuklar -> kart 1; Bölüm 6 başlangıç (güçlü trend çubuğu, ters desenler).
- 121-140: iki/üç çubuklu ters dönüş, küçük çubuk, ii/iii/ioi, mikro çift dip/tepe, tıraşlı çubuk, tükenme çubuğu, MA ile sinyal -> kartlar 2,3,5,9.
- 141-160: Bölüm 6 örnek grafikleri 6.8-6.16 (ii, iki çubuk, 15 dk ters çubuk, dikenli tel, ölçülü hareketler).
- 161-180: Bölüm 6.17-6.19 (ters çubuk bayrağa dönüşür, tıraşlı çubuklar), Bölüm 7 dış çubuklar -> kart 4.
- 181-200: Bölüm 7 son grafikler; Bölüm 8 çubuk kapanışı; Bölüm 9 ETF/ters grafikler; Bölüm 10 ikinci girişler; Bölüm 11 geç girişler; Bölüm 12 desen evrimi (10-12 mevcut kartlarda, güncelleme önerisi).
- 201-220: Bölüm 12 sonu, Bölüm II başlangıcı (trend çizgileri/kanallar), Bölüm 13 trend çizgileri, Bölüm 14 başlangıcı (trend kanal çizgileri) -> kartlar 6,7,8.

## Yeni kartlar (9)
1. `daytrade__ters-cubuk-sinyali__brooks_t1` (s106-111,117): ters çubuk sinyal çubuğu girişi (puan 2).
2. `daytrade__iki-uc-cubuk-ters-donus__brooks_t1` (s119-121,130-137): iki/üç çubuklu ters dönüş (puan 1).
3. `daytrade__ic-cubuk-ii-ioi-kirilim-modu__brooks_t1` (s122,125-128,171-172,177): iç çubuk / ii / iii / ioi kırılım modu (puan 2).
4. `daytrade__dis-cubuk-giris-ve-ioi__brooks_t1` (s171-183): dış çubuk girişi, tuzak (puan 1).
5. `daytrade__mikro-cift-dip-tepe-tek-cubuk-bayrak__brooks_t1` (s123-127,143-145): (puan 1).
6. `daytrade__trend-cizgisi-kirilimi-ekstrem-testi__brooks_t1` (s29-30,102-108,206-209): (puan 1).
7. `daytrade__trend-cizgisi-testi-trend-girisi__brooks_t1` (s206-209,215,217): (puan 1).
8. `daytrade__trend-kanal-cizgisi-asimi-donus__brooks_t1` (s29-33,104,111,114,162,215,219-220): (puan 1).
9. `daytrade__climax-tukenme-sonrasi-duzeltme__brooks_t1` (s77-92,127,132-133,156-165): (puan 1).

Tümü ≥5m'ye uyarlanabilir; hacim gerekmez; kitap yorum ağırlıklı olduğundan çoğu puan 1. Öznel kısımlar için ölçülebilir öneriler `belirsizlikler` alanında ve kural olarak sunulmadı.

## Güncelleme önerileri (mevcut kartlara; yeni kart değil)
- `daytrade__ikinci-giris-ters-trend__brooks`: (s191-193) İkinci giriş birinciden daha iyi fiyatta doluyorsa tuzak şüphesi ("iyi dolum, kötü işlem"; iyi ikinci girişlerin çoğu aynı fiyat veya daha kötü). Momentum güçlüyse (yaklaşık 4 ardışık trend çubuğu veya 2-3 büyük trend çubuğu) ilk ters denemeyi atla, trendin 1-2 çubuk devam etmesini bekle ve ikinci denemeye gir. Örnek: 5 boğa trend çubuğu sonrası ilk düşüş girişi alınmaz, ikinci giriş alınır (s193).
- `daytrade__mikro-kanal-gec-giris__brooks`: (s195-197) Geç girişte pozisyon büyüklüğü = orijinal girişle şimdi tutulacak "swing" kısmı kadar; stop = orijinal stop mantığı (BE veya sinyal çubuğunun ~10 sent altı örneği); 4+ ardışık, çok büyük olmayan trend çubuğu varsa en az küçük pozisyon (zaten kartta).
- `daytrade__basarisiz-kurulum-ters-donusu__brooks`: (s198-200) güvenilir kalıplar yaklaşık %40 başarısız olur; başarısızlık birkaç çubuk yan giderse yeni kalıbı ilkinden bağımsız say.
- `daytrade__yuksek2-dusuk2-trend-geri-cekilmesi__brooks` (Ranges kartı): (s183) H2 tek başına kurulum değildir; öncesinde genelde trend çizgisini kıran bir H1 bacağı veya güçlü boğa trend çubuğu gerekir; önceki 6 çubuktan 5'i ayı çubuğu ise H2 "berbat" (kitap). Güçlü trendde H1/H2 sinyal çubukları çoğu zaman zayıf görünür, bu eleme nedeni değildir (s119).
- `daytrade__acilis-donusu__brooks` (En_Basarili kartı): (s199-201,119) İlk saatte çift tepe ayı bayrağı çift dip boğa bayrağına dönüşebilir (ve tersi): her iki girişi al ve bir kısmını salla; açılış aralığı ortalama günün ~1/3'ünden küçükse tüm açılış aralığının kırılmasını beklemek tercih edilir (s119).
- `daytrade__buyuk-trend-donusu__brooks` (En_Basarili): (s90-92,156-160) climax göstergeleri: 30+ çubuk süren ayı trendi, destek bölgesi, olağandışı büyük ayı trend çubuğu, ardından 2 bacak ve ~10+ çubuk MA üstü düzeltme; art arda ikinci ve üçüncü satış doruğu ayrıca vurgulanır; parabolik eğim artışı climax işareti.
- `daytrade__dar-aralik-kirilim-modu__brooks` (Ranges): (s126,180-181) dikenli tel (üst üste binen büyük, uzun kuyruklu çubuklar) kırılımlarının çoğu başarısız, fade kurulumu aranır; uzun trend sonrası dikenli tel genelde son bayrak.
- `daytrade__kama-uc-itme__brooks` (En_Basarili): (s220) trend kanal çizgisi aşımı ve kama aynı olgu; kama = trend çizgisi eğimi kanal çizgisinden büyük; kanal paralelken ikinci geri çekilme kamayı ayırır.
- `daytrade__olculu-hareket-hedefi__brooks`: (s152,159) trend sıçramasından ölçüm: ilk çubuğun açılışından son çubuğun kapanışına (ayı için son çubuğun kapanış/dibi) mesafe, ilk geri çekilmenin tepesinden aşağı yansıtılır.
- `daytrade__spike-ve-kanal-trendi__brooks`: (s77-78,148-149,159-160) spike sonrası kanal çoğunlukla üçüncü itişte biter; kanal başlangıcı genelde 1-2 gün içinde test edilir; spike sonrası ilk geri çekilmeden sonra kanal aşaması başlangıcı ticaret aralığı başlangıcıdır.

## Kart çıkmayan bölümler ve nedeni
- s1-19 (terimler), s20-54 (giriş ve güç işaretleri): kavram; kurulum yok. Güç işareti listeleri (kırılım güç ölçütleri) kartlara filtre olarak işlendi, tek başına kart değil.
- s55-76 (Bölüm I, 1): fiyat hareketi yelpazesi, kurumlar, HFT, aşırılık: kavram.
- s94-99 (Bölüm 3): kırılma/test/geri dönüş kavramları ve Şekil 3.1 yorumu; mevcut `kirilim-ve-kirilim-geri-cekilmesi` kartı kapsar.
- s100-105 (Bölüm 4): sinyal çubuğu temelleri, giriş mantığı ve sinyal listesi; ters çubuk (kart 1) ve diğer kartların alanlarına işlendi.
- s184-187 (Bölüm 8): çubuk kapanışı: kapanışı bekle, 3 dk yerine 5 dk; yönetim ilkesi, kural kartı değil.
- s188-190 (Bölüm 9): ETF/ters ETF (SPY/SDS) ile bakmak: araç tavsiyesi, kural yok.
- s191-201 (Bölüm 10-12): mevcut kartlarla kapsanmış (güncelleme önerileri yukarıda).
- s202-205 (Bölüm II girişi): çizgi tipleri sözlüğü, kart yok.
- s210, s213-214 (şekil 13.2, 13.4, 13.5): aylık trend çizgisi, kanal oluşturma, baş-omuz kanal çizgisi: görsel örnek, kural yok.
- s219-220 (Bölüm 14 başı): trend kanal çizgisi cizim yöntemleri: kart 8'e işlendi, devamı sayfa 221+ (başka parça).

## Dikkat
- Kitap Türkçe makine çevirisidir; kuyruk/tail, fitil, "kafa derisi" (scalp), "ara"(breakout) vb. çeviri gürültüsü var; kartlar orijinal anlama göre yazıldı.
- Sayısal hedef, stop mesafesi ve kazanma oranı çoğu kurulum için kitapta yok; uydurulmadı.
