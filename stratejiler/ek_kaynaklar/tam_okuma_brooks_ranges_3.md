# Tam okuma: Al Brooks, Price Action Trading Ranges (572 sayfa) — dosya sayfa 381-572

Kaynak metin: `veri/pdf_metin_2/kitap_diger/Price_Action_Trading_Ranges_-_Al_Brooks_572_sayfa.txt`.
Sayfa numaraları aşağıda ve kartlarda **metin dosyasındaki `=== SAYFA n ===` numarasıdır** (kitap içi numara 6 eksiktir).
Okunan aralık: 381-572 (192 sayfa), atlama yok. Aralıkta kitabın 22-32. bölümleri var (görev notundaki "24-32" yerine ilk sayfa 21. bölümün sonudur).

## Okuma kanıtı (20 sayfalık bloklar)
| Sayfalar | İşlenen konu |
|---|---|
| 381-400 | Bölüm 21 sonu (aralık örneği), 22 sıkı ticaret aralıkları: dikenli tel tanımı/MA kuralı, kırılışı değil başarısızlığı girme, martingale reddi, trend sonrası dar aralık |
| 401-420 | 22 sonu (10 ardışık kayıp, ioi dikenli tel, trend yeniden başlama), 23 üçgenler (3 itme, genişleyen üçgen, kırılış başarısızlığı) |
| 421-440 | Bölüm 24 scalp/swing/yatırım: scalp hedefi ≈ risk, %70 gerek; swing 2x; OCO, BE kuralları; 25 Tüccar matematiği başı (olasılık tablosu) |
| 441-460 | 25: tüccar denklemi, kurumların diğer taraf mantığı, yüksek/düşük olasılıklı sistem, break-even kazanma oranları |
| 461-480 | 25: hedefe yakın risk (%90), yön olasılığı, spike ölçülü hareket, kısa süreli yüksek olasılık anları |
| 481-500 | 25 sonu (scalper trend kaçırır), 26 "iki neden" kuralı, 27 stop girişleri, 28 limit giriş katalogu başı |
| 501-520 | 28 limit giriş (önceki çubuk ucu, %60-70, L1/L2 tuzağı, kanal fade, kırılış testi), 29 koruyucu/izleyen stop başı |
| 521-540 | 29 stop türleri (fiyat hareketi/para), sıkma kuralı, geniş stop gerektiren durumlar, izleyen stop; 30 kâr alma başı |
| 541-560 | 30 hedefler (2x stop yarım pozisyon, Euro FX/Tahvil örnekleri), 31 ölçeklendirme (karşı trend vs trend yönü) |
| 561-572 | 31 ölçeklendirme örnekleri (spike, kanal, zayıf elleri çıkaran yer), 32 stop/tuzağa düşme örneği |

## Yeni kartlar (10) — `veri/kartlar_ham/daytrade/Price_Action_Trading_Ranges_-_Al_Brooks_572_sayfa__tam_brooks_ranges_3.json`
1. `daytrade__dikenli-tel-basarisiz-kirilim__brooks_r3` — dikenli tel tanımı + başarısız kırılışa giriş (puan 2)
2. `daytrade__guclu-trendde-karsi-scalp-fade__brooks_r3` — güçlü trendde karşı scalp'ı limitle soldurma (puan 1)
3. `daytrade__onceki-cubuk-ucunda-limit-geri-cekilme__brooks_r3` — önceki çubuk ucunda limit giriş (puan 2)
4. `daytrade__yuzde60-70-geri-cekilme-limit__brooks_r3` — %60-70 geri çekilmeye limit (puan 2)
5. `daytrade__basarisiz-l1-l2-tuzagi-limit__brooks_r3` — güçlü trendde L1/L2 tuzağı, limitle ters giriş (puan 2)
6. `daytrade__zayif-kanalda-karsi-trend-olcekli-fade__brooks_r3` — karşı trend ölçekleme (puan 1; sert risk limitiyle çelişebilir, eleme adayı)
7. `daytrade__klimaks-cubugu-kapanis-fade__brooks_r3` — klimaks çubuğu kapanışında karşı giriş (puan 1)
8. `daytrade__kirilim-testi-limit-fade__brooks_r3` — zayıf kırılışı ölçülü hareket civarında limitle soldurma (puan 2)
9. `daytrade__islem-yonetimi-kismi-kar-izleyen-stop__brooks_r3` — çıkış/yönetim modülü: stop, BE, kısmi kâr, izleme (puan 2)
10. `daytrade__trend-yonunde-ekleme-ayri-islem__brooks_r3` — trend yönünde ekleme (puan 2)

## guncelleme_onerileri (mevcut kartlara; kart yazılmadı)
Sayfalar = dosya sayfa numarası.
1. `daytrade__yuksek2-dusuk2-trend-geri-cekilmesi__brooks` — stop_loss/kar_al/iz_suren_stop: ilk stop sinyal çubuğu 1 tik ötesi; giriş çubuğu güçlü trend çubuğuysa stop giriş çubuğu 1 tik ötesine sıkılır, dojiyse sıkılmaz; büyük sinyal çubuğunda para stopu (E-mini ~8 tik) veya çubuk yüksekliğinin %60-70'i; scalp hedefi ≥ risk (gereken olasılık ≥%60), swing hedefi ≥2x risk; MA'ya H2/L2 "olasılık ≥%60" (s442, 520-524, 528-529).
2. `daytrade__yuksek2-dusuk2-aralikta-ters__brooks` — filtre: aralık tepesinde H1/H2 zayıf sinyal çubuğunda short limit; güçlü boğa trendinde L1/L2 arama, tuzaktır (~%80 bayrak); aralık dibinde "ikinci giriş" ek olasılık (s442-443, 497-499, 505).
3. `daytrade__ucgenler-3-itme-kirilim__brooks` — belirsizlik/filtre: genişleyen üçgende kırılış başarısız olup ters tarafa kırar (ters tarafın da başarısız olduğu döngü); kırılış güçlüyse geri çekilmede gir (kırılışa değil); sıkı kanaldaki 3-itme "kama gibi tersine" işlemez, kanal gibi sürer; hedef = üçgen/kanal yüksekliği kadar ölçülü hareket (s416-418, 420, 487).
4. `daytrade__dar-aralik-kirilim-modu__brooks` — **önemli çelişki**: kitap dar aralıkta stop girişini (kırılışa giriş) kaybettiren olarak niteler; önerilen: başarısızlığa veya kırılış geri çekilmesine gir. Trend yönünde kırılış olasılığı yalnızca %51-55; dikenli tel olarak 20+ çubuk uzarsa bekle. Bu bilgi kartın `kar_al`/`stop_loss` alanlarının yanında "sert uyarı" olarak eklenmeli (s382-386, 389-391).
5. `daytrade__kirilim-geri-cekilmesi-ve-basarisiz-kirilim__brooks` — stop/hedef: kırılış testi limitle girişte 4-6 tik risk, 4+ puan hedef (olasılık >%50), zayıf elleri çıkaran (yuvarlak sayılı stop) yerde giriş; güçlü kırılışa girme, geri çekilme/kırılış testinde gir (s498, 508, 568-569).
6. `daytrade__olculu-hareket-bacak-esitligi__brooks` — kural: spike ölçümü ilk çubuğun AÇILIŞINDAN son çubuğun KAPANIŞINA (gövdeler, kuyruksuz); ölçülü hareket kurumların minimum hedefi, çoğu kez aşılır; spike büyüdükçe hedef büyür, stop sabit (s477-478).
7. `daytrade__trend-eden-ticaret-araligi-gunu__brooks` — filtre/hedef: açılış aralığı ortalama günlük aralığın ~yarısıysa kırılış ilk 1-2 saat sonra; kırılış testi için limit 4-6 puan (aralık ~10 puan); alt aralık dibinde limit alım, 3 tik risk, 4-12 puan hedef; geri çekilme çubuğunun dibinin altına izleyen stop koyma (s480, 501-502, 507-511, 521).
8. `daytrade__mikro-kanal-gec-giris__brooks` — giriş/stop: spike'a geç giriş teorik stopu çok uzak (spike dibi) → küçük boy veya geri çekilmede ölçekle; güçlü trend çubuğunun kapanışında giriş, duraklama çubuğunda (kuyruk, doji, ters renk) kapanış girişini durdur; hedef: stop mesafesinin 2x/4x (s497-498, 526, 555, 564).
9. `daytrade__basarisiz-kurulum-ters-donusu__brooks` — "iki neden" kuralı (ikinci giriş tek neden sayılır); başarısız L2 short → long; başarısız kırılış sonrası ters giriş (s484-485, 530).
10. `daytrade__kama-geri-cekilme-ve-donus__brooks` — hedef: kama tepesi sonrası genelde ≥2 bacak yan/aşağı düzeltme; kamanın yüksekliği düzeltme bitmeden aşılmaz; kama içi giriş limit short: sinyal çubuğunun üstünde 6 tik risk örneği (s491).
11. `daytrade__ikinci-giris-ters-trend__brooks` — kar_al/stop: ters trend girişinde yarım boy, aleyhe ikinci hamlede çık veya ters çevir; ilk stop sinyal çubuğu ötesi; kar_al "kitapta yok" → ters girişte genelde kısmi kâr/2 puan, kalanı yeni ekstrem (s426, 522, 550).
12. `daytrade__cift-dip-boga-bayragi__brooks` — giriş: çift dip boğa bayrağında alıcılar önceki dibin birkaç tik üstüne limit koyar (yeni trendi kaçırma korkusu); stop dibin ~1 puan altı, hedef 3-7 puan; kama tepesi sonrası çift tepe (s515-516, 508-511).
13. `daytrade__20-bosluk-cubugu__brooks` ve `daytrade__ilk-hareketli-ortalama-boslugu__brooks` — hedef/stop: MA'ya geri çekilme sinyal çubuğu 8 tik ise stop ~10 tik, 20 tik hedef (Euro FX örneği); ilk MA boşluk çubuğu + çift dip birleşimi; ölçeklemeli çıkışlar: yarım pozisyon 20 tikte, çeyrek 10-20 tik daha yukarı (s542-545).
14. `daytrade__ticaret-araligi-sinirda-dusuk-al-yuksek-sat__brooks` — filtre: aralık çok darsa (E-mini ~3 puan altı) işlem yok; dar aralığın dibinde alım yalnız swing hedefli (üst aralığı test, risk <1 puan, hedef 4+ puan, olasılık %50); limit emir hedefe 4 tik için sinyal çubuğunun 6 tik ötesi gerekir; scalp olasılığı %70 şartı (s382-386, 472-473, 495, 508-511).
15. `daytrade__gunun-onemli-saatleri-stop-run__brooks` — stop boyutu: günün ilk işleminin gerektirdiği maksimum stop (örnek 9 tik) gün boyu stop boyutunu belirler; yuvarlak sayı stop'lar vurulup dönülür (2/3/4/5 puan) → geniş stop + ölçek ya da zayıf elleri çıkaran yerde giriş (s532, 535, 568).
16. `daytrade__spike-ve-kanal-trendi__brooks` — hedef/yönetim: kanal 3 itişi sonrası ≥10 çubuk düzeltme; boğa kanalı tepesinde kısmi/tam kâr; kanal dibine düşük momentumlu geri çekilme alımı; kanal ters trend ölçeği yalnız güçlü trend günü değilse (s496, 531-532, 566).
17. `daytrade__cift-tepe-dip-ve-omuz-bas-omuz-donusu__brooks` — hedef ("kitapta yok" → doldurulabilir): ters kurulumlar %40 olasılık, ödül ≥2x risk; önce trend çizgisi güçlü kırılımı + uç testi + iyi ters sinyal çubuğu; yarım boy giriş ve ikinci giriş (s442-444, 426).
18. `daytrade__merdiven-genis-kanal-gunu__brooks` — hedef/stop: merdiven (sıralı kırılış) günlerinde önceki swing dibinin ~4 puan altına limit (E-mini ort. aralık 12 puan), her kırılış öncekinin ~aynı büyüklüğünde; geniş stop ve ölçek, sürekli daralan merdiven (s500, 568-569).
19. `daytrade__trend-yeniden-baslama-gunu__brooks` — filtre: ilk 1 saat güçlü trend + saatlerce dar aralık + aynı yönde kırılış, ikinci bacak ≈ ilk bacak; daha seyrek ters yönde kırılış (s385-386).
20. `daytrade__geri-donus-gunu__brooks` / `daytrade__acik-trend-kucuk-geri-cekilme__brooks` — bu aralıkta yeni kural yok (ek bilgi: açılıştan itibaren boğa trendi gününde L1/L2 yok, geri çekilme alımı).

## Kart çıkmayan bölümler ve nedeni
- Bölüm 21 sonu, 22 örnek grafikleri (s393-415): kuralları dikenli tel kartına işlendi, bağımsız kurulum yok.
- Bölüm 24 (s422-439) ve 25 (s440-483) büyük ölçüde kavram/matematik: olasılık-risk-ödül ilişkisi. Sayısal çıkarımlar (break-even kazanma oranları, E-mini 2 puan stop / 2-4 puan hedef, %60 eşit mesafe olasılığı) yönetim kartı, `belirsizlikler` ve güncelleme önerilerine işlendi. Tüccar denklemi tek başına "kart" değil (kod filtresi: beklenen değer > 0).
- Bölüm 26 "İki neden" kuralı: filtre kuralı, ayrı kart değil (güncelleme 9).
- Bölüm 27 (s494-495): stop girişi tanımı; mevcut H2/L2 kartlarına işlendi (güncelleme 1).
- Bölüm 29 grafik örnekleri, 30, 31, 32 (s527-572): çıkış/ölçekleme ve tuzak örnekleri; kartlar 9, 10, 6 ve güncelleme önerilerine işlendi.

## Notlar / riskler
- Kitap, E-mini (5 dk) tik/puan sayılarıyla yazılmıştır; kriptoda ATR veya günlük aralık oranına çevrilmeli. Kitap güvenilirlik iddiaları (%60, %70, %80) kanıtsızdır.
- Kitap martingale'i ve dikenli telde ardışık stop girişlerini açıkça reddeder; kart 6 (ölçekli karşı trend) 1L3A'nın %1 işlem riski ve "martingale yasak" kararıyla çelişebilir; kodlanacaksa toplam risk tek işlem limitinde tutulmalı.
- Brooks'un "tek puanlık scalp %80 doğru olmayı gerektirir" argümanı (s424, 459): 5 dk'da komisyon/kayma baskın olduğundan 1L3A DURUM.md'deki ilk deneme bulgusuyla uyumlu.
