# Tam okuma: Al Brooks, Price Action Trading Ranges, sayfa 1-190 (parça brooks_ranges_1)

Metin sayfa numaraları (`=== SAYFA n ===`) kullanılmıştır; kart içindeki "p" göndermeleri de bu numaradır (kitabın basılı numarası yaklaşık 8 küçük).
Sayfa 1-190 sırayla okundu (1-4 ve 20 kapak/ara başlık, 5-19 terimler sözlüğü). Kitap her sayfada çeviri filigranı içerir; şekil sayfaları kısa.

## Okunan aralık ve konu (20 sayfalık bloklar)
- 1-20: içindekiler, terimler sözlüğü (sinyal çubuğu, ters çubuk, iç/dış çubuk, H/L sayımı, kama, mikro kanal, ölçüm boşluğu tanımları).
- 21-40: giriş; kurumlar/algoritmalar, haberi yoksay, göstergesiz tek grafik (20 EMA), kumar/martingale yorumu (martingale kitapta da reddedilir), %50-50 yön olasılığı.
- 41-60: giriş devam, "kitaplar nasıl okunur", güç işaretleri (trend, kırılım, ters çubuk, dönüş), çubuk sayımı H1-H4/L1-L4; Bölüm "Kırılımlar" başlangıcı (kırılım/başarısız kırılım, kurumların davranışı).
- 61-80: kırılımlarda kurum davranışı, trend olgunlaşması (Şekil PI.1-PI.2); Bölüm 1 kırılım işleminin örneği (spike dibi stop, küçük pozisyon, ölçülü hareket, ilk geri çekilme).
- 81-100: Bölüm 2 kırılımda güç/zayıflık işaretleri listeleri, Şekil 2.1-2.3 örnekleri; Bölüm 3 ilk patlama başlangıcı.
- 101-120: Bölüm 3 şekilleri (3.1-3.3), Bölüm 4 mevcut güçlü trendde kırılım girişleri, Bölüm 5 başarısız kırılım/kırılım geri çekilmesi/testi.
- 121-140: Bölüm 5 şekilleri (5.1-5.10, son bayrak), Bölüm 6 boşluklar (kırılma/ölçüm/tükenme, MA boşluğu, mikro boşluk).
- 141-160: Bölüm 6 şekilleri (6.1-6.5), Bölüm II mıknatıslar giriş (destek/direnç listesi, kurum davranışı).
- 161-190: mıknatıs devam, Şekil PII.1-PII.2; Bölüm 7 ilk bacağa göre ölçülü hareket (7.1-7.5), Bölüm 8 boşluk/aralığa göre ölçülü hareket (8.1-8.5), Bölüm 9 başlangıcı (başarısız dönüşlerin giriş fiyatı mıknatıs; bölüm 190'da kesiliyor, devamı sonraki parçada).

## Yeni kartlar (3), dosya: `veri/kartlar_ham/daytrade/Price_Action_Trading_Ranges_-_Al_Brooks_572_sayfa__tam_brooks_ranges_1.json`
1. `daytrade__guclu-kirilim-yonunde-giris__brooks` (puan 1) kırılım yönünde giriş; güç işaretleri, spike dibi stop, küçük pozisyon, ölçülü hareket/boşluk ortası hedef.
2. `daytrade__zayif-kirilimi-fade-et__brooks` (puan 1) zayıflık işaretleriyle kırılım fade; stop kitapta yok (belirsizlik).
3. `daytrade__miknatiste-ikinci-ters-donus__brooks` (puan 1) mıknatısta ikinci deneme ters dönüş; stop/hedef kitapta yok.

## guncelleme_onerileri (var olan kartlara)
- `daytrade__kirilim-geri-cekilmesi-ve-basarisiz-kirilim__brooks` (+ En Başarılı 10 kitabındaki `kirilim-ve-kirilim-geri-cekilmesi`):
  - Kırılma testinde başabaş stop giriş fiyatında olmak zorunda değil; hissenin davranışına göre tolerans (kitap örneği 10-30 sent, 750 dolarlık hissede) veya başabaştan çıkıp test çubuğunun 1 tik ötesinde yeniden giriş (sayfa 120, 125-126).
  - Giriş: test/sinyal çubuğunun 1 tik ötesine stop; test tamamlanınca stop test çubuğu ucunun 1 tik ötesine taşınır (sayfa 119, 125).
  - Kırılma sonrası geri çekilmenin sık bittiği alanlar listesi (kırılma noktası, spike tepesi, son bayrak öncesi salınım, merdivenin son salınımı, giriş çubuğu dibi, sinyal çubuğu yüksekliği, hareketli ortalama vb.) (sayfa 118).
  - Filtre: gün erken saatte güçlü hareket yaptıysa trend yönlü kırılım başarılı olur; gün trendsizse başarısızlık tersine döner (sayfa 120). Kırılma geri çekilmesi "bardak ve sap" olarak anılır, en güvenilir kurulumlardan biridir (sayfa 120).
  - Kırılma çubuğu çevresinde derin geri çekilme (~10 çubuk) varsa H1 yerine H2 beklenir (sayfa 89).
- `daytrade__olculu-hareket-bacak-esitligi__brooks` ve `daytrade__olculu-hareket-hedefi__brooks`:
  - Ölçüm boşluğu kuralı: kırılma noktası ile kırılma testi (ilk geri çekilme dibi) arası; bacak dibinden boşluk ortasına tik sayısı, ortanın üstüne projekte edilir. Boşluk negatifse (geri çekilme kırılma noktasının altına inerse) aynı yöntem daha az güvenilir (sayfa 139-141, 179-180, 182).
  - Kırılma noktası-test mesafesi çok yakınsa (örnek: günlük ortalama aralığın üçte biri altında) kâr hedefi olarak kullanma, yalnızca güç işareti say; mesafe ortalama günlük aralığın 1/3-1/2'siyse orta nokta projeksiyonunda kâr al/ters çevir (sayfa 140).
  - Spike bazlı: ilk spike çubuğunun açılışından (veya düşüğünden) son spike çubuğunun kapanışına (veya yüksek) olan mesafe, son çubuğun kapanışından projekte edilir; ilk hedef için küçük olan seçilir; daha sonra diğer olasılıklar (sayfa 168-171, 177-178).
  - İki ayaklı geri çekilmenin sonu: geri çekilme tepesinden birinci ayağın yüksekliği çıkarılır veya gelişen aralığın ortası izlenir (sayfa 168-169).
  - Açılış aralığı ortalama günlük aralığın yaklaşık yarısıysa hedef aralığın iki katıdır (sayfa 147; örnek, kural değil).
  - Olasılık iddiası: ölçülü hareket vurma ihtimali en az %60 (çok güçlü spike'ta >%70) (sayfa 167, 102) — kanıtsız.
- `daytrade__yuksek2-dusuk2-trend-geri-cekilmesi__brooks`:
  - Çubuk sayımı sıfırlanır: piyasayı yeni trende sokan güçlü dış çubuğun dibi trendin başlangıcıdır (sayfa 108). H4 başarısız olursa boğalar kontrolü kaybetmiştir (sayfa 54, mevcut kartta var).
  - Güçlü trendde ilk geri çekilmede H1 için önceki çubuk dibinde limit (agresif) veya H1 buy-stop; her ikisi kaçırılırsa spike tepesinin 1 tik üstüne son çare buy-stop (sayfa 58, 109-110).
  - Sinyal çubuğu kalitesi: boğa dönüş çubuğu minimum şartı kapanış açılışın veya orta noktanın üstü; iyi dönüş çubuğu: alt kuyruk bar yüksekliğinin ~1/3-1/2'si, küçük üst kuyruk, önceki çubuklarla az örtüşme, sonraki çubuk doji iç çubuk değil (sayfa 50-51). Ayna ayı için (sayfa 51).
- `daytrade__ilk-hareketli-ortalama-boslugu__brooks` (mevcut içerik kontrol edilmeli): ilk MA boşluk çubuğunun dibinin 1 tik altına sell-stop; dolmazsa stop yeni kapanan çubuk dibine kadar aşağı çekilir; stopla çıkılırsa önceki çubuğun dibinin altında yeniden girilir (sayfa 139).

## Kart çıkmayan bölümler
- Giriş, kurum/algoritma anlatısı, haber/uzman eleştirisi, kumar/martingale yorumu, terimler: kavramsal (sayfa 1-45). Martingale kitapta da matematiksel olarak reddedilir.
- Kırılımlar: Şekil PI.1-PI.2, 2.1-2.3, 3.1-3.3, 5.1-5.10, 6.1-6.5, 7.1-7.5, 8.1-8.5 örnek yorumları: yeni kural yok, yukarıdaki kartlara/önerilere işlendi.
- Boşluklar bölümü (kırılma/ölçüm/tükenme sınıflaması): sınıflandırma sonradan yapılır; kurulum olarak değil hedef hesabı olarak güncelleme önerisinde.
- Mıknatıslar (destek/direnç felsefesi, kurum davranışı, haber eleştirisi): kavramsal; yalnızca ikinci deneme ters dönüş cümlesi kart oldu.
- Son bayrak (Şekil 5.7-5.10): kitap 3'e (ters dönüşler) ait konu, bu kitapta kural yok; bu parçada kart yok.
- Bölüm 9 (başarısız dönüş giriş fiyatı mıknatıs): sayfa 189-190'da başlıyor; tamamı sonraki parçada işlenmeli.
