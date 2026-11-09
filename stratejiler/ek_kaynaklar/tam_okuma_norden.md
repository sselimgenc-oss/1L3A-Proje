# Tam okuma: Scalping Kılavuzu (Gary Norden) — parça "norden"

Kitap Türkçe (s.1-57) + aynı metnin İngilizcesi (s.58-114, 57 sayfa ofset). Türkçe kısım sayfa sayfa okundu. İngilizce kısım için her sayfa çiftinde uzunluk ve sayı karşılaştırması yapıldı (54 çiftten 51'i sayıca birebir; 3 fark çeviri/biçim artefaktı: s.18/75, 21/78, 24/81), ayrıca s.58-70 ve s.75 doğrudan okundu. İçerik farkı yok. Kitap grafik/gösterge kullanmaz; tüm yöntem DOM, Time&Sales ve korelasyon izlemeye dayanır.

## Okuma kanıtı (20 sayfalık bloklar)
- s.1-20: tanıtım, zihniyet/disiplin, araçlar (DOM, T+S, izleme listesi, haber), hedef kazanma oranı (~%80 + ~%10 scratch), spread'e katılmanın matematiği (bid'e alış: 6 sonuçtan 1 kayıp; offer'a alış: 6'da 1 kâr), limit emirle giriş-çıkış ilkesi.
- s.21-40: kuyruk pozisyonu, likidite, hızlı dolum, hızlı/ince piyasada sıçrama sonrası emir yerleşimi, "değer" (ağır hacim, korelasyon), kâr-veya-sıfır kurulumu ve scratch, chop-hareket ayrımı, iki yönlü akış.
- s.41-57: dolum kontrol listesi ve ayarlar, pozisyon büyütme, aşırı volatilitede zorluklar (boşluk, uzak savunma emri, teklif vurma), istatistik hedefleri, özet ve piyasa öncesi hazırlık.
- s.58-114: s.1-57'nin İngilizce aynası (yukarıdaki doğrulama).

## Yeni kartlar (4) — dosya: veri/kartlar_ham/scalp/Scalping_Kılavuzu_-_Gary_Norden_-_Türkçe_ve_İngilizce_114_sayfa__tam_norden.json
1. scalp__kuyruk-pozisyonu-hizli-dolum__norden (s.21-27) — kodlanabilirlik 0
2. scalp__sicrama-sonrasi-geri-donus-teklifi__norden (s.28-31, 34) — 0
3. scalp__dolum-kontrol-listesi-scratch__norden (s.36-37, 42-44, 54) — 0
4. scalp__volatil-gun-teklif-vurma__norden (s.51-53) — 0

Hepsi emir defteri/tick verisi ister; 1L3A'da (≥5m OHLC) uygulanamaz. OHLCV ile yaklaşılabilen, kitabın gerçekten kural olarak verdiği bir kurulum yok; kartlardaki OHLCV önerileri yalnız `belirsizlikler`'de "kural değil" notuyla.

## guncelleme_onerileri (mevcut 3 kart için)
- scalp__spread-uzerinde-pasif-scalp__norden (kaynak sayfalarına 17-20, 31-35, 40-41 eklenmeli):
  - s.17-20: piyasa emri kullanma; giriş ve çıkış limit emirle. İstisnalar: (a) hareketin normalden büyük beklendiği an (haber sonrası gibi), (b) işlem hızla aleyhe gidiyorsa piyasa emriyle çıkış, (c) hızlı piyasada 2-4 tik kâr çabuk gelirse teklifi vurarak kâr al. Spread'in doğru tarafı ile yanlış tarafı arasındaki fark (6 eşit olasılıklı sonuçta 1 kâr/3 zarar ve 5 zararsız/1 zarar) kitabın temel gerekçesi.
  - s.33: "değer" tanımı = en ağır hacmin işlem gördüğü fiyat (örnek: 16'da 50 ve 30 lotluk işlemler, 15'te 5 ve 2 lotluk -> değer 16). 1 lotluk işlemler değer söylemez. Hızlı piyasada değer = son işlem fiyatı (s.34).
  - s.33-34: korelasyon yalnız o gün güçlü olduğu açıkça belliyse kullanılır; zayıfsa işlem yapma. Çelişen kanıtta işlem yok; yalnız bazı kanıtla girilirse "agresif işlem", başarısızsa gün boyu bırak. Korelasyon yardımcı girdidir, tek başına işlem sebebi değil.
  - s.40-41: iki yönlü akış (örn. 15,16,15,16 basması) şart; tek yönlü akışta (16,16,16...) 15'ten dolmak mümkün değil veya istenmez; emri kısa deneyip çek. Piyasa hızı (dakikadaki işlem sayısı) belli eşiğin altındaysa işlem yok.
  - s.14, 16, 57: haber/veri çıkışında işlem yok, veri çıktıktan ve piyasa oturduktan sonra gir; vade yenilemesi (roll) sırasında işlemi durdur; resmi tatiller; aynı piyasada günün aynı saatinde işlem yap.
  - s.45: pozisyon büyütme yalnız ≈%70+ kazanma oranında; ince sözleşmede (bid/offer <20-30 lot) en fazla 2 lot, >100 lotta 5-10 lot; kısmi dolumda kalan emir iptal; çıkış emri dolan miktar kadar otomatik (+1 tik).
  - s.54-55: izlenecek ölçütler: scratch sayısı > kayıp sayısı, kazanma ≥%70, kâr+scratch ≈%90, 3+ tik kayıp seyrek, ortalama işlem süresi düşük, kayıp günü yaklaşık ≤10 tik, kayıp gününde kaybı iyi günün %50'sinin çok altında tut.
- scalp__chop-vs-hareket-islemi__norden (s.38-39): etkin spread örneği (gerçek 16b/17o iken piyasa 15 ve 18'de işlem görüyor -> etkin 15b/18o); chop içinde de hızlı dolmayan emir çekilir; chop kaldırılamayacak kadar riskli olabilir (kayıp ≥5 tik); düşük volatilitede chop, yüksek volatilitede yalnız hareket sonrası işlem. Mevcut kart bunları büyük ölçüde içeriyor, sadece "dolmayan emri çek" ve "tek yönlü hareket başlarsa kötü dolum" ayrıntısı eklenebilir.
- scalp__bosluklu-defterde-savunma-emri__norden (s.49-53): orta büyüklük örneği 10 lot (11 lotluk tek teklifin iki yanına emir verme); boşluk varken spread çevresinde (1-2 tik için) hiç işlem yapma; örnek: 25 son fiyat, 45'te satış, kâr potansiyeli 16-20 tik, stop 49/50; şüphede emri uzağa koy veya işlem yapma; önceki fiyattan 30 tik ötede bile doldurulmuş; dolumdan sonra değer sıçradıysa hemen en iyi fiyattan çık; defter dengesizliğine güvenme (petrol çöküşü örneği); işlem sayısını azalt, işlem başına kârı normalden yüksek bekle.

## Kart çıkmayan bölümler
- s.2-10, 15, 55-57 (ve aynaları): zihniyet, disiplin, günlük/istatistik tutma, ekran sayısı, özet; kurulum değil.
- s.3, 11 (aynı metin tekrar): araçlar; kurulum yok.
- s.12-14: neden grafik değil işlem-bazlı izleme; bağlam/korelasyon açıklaması; haber akışı; kayıt tutma. Kavramsal.
- s.16: durum tespiti (sözleşmeyi tanı, vade yenileme, tatil); filtre olarak yukarıda önerildi.
- s.17-20: spread matematiği; ayrı kart yerine mevcut spread kartına öneri.
- s.31-35: "değer" kavramı; mevcut kart güncelleme önerisinde.
- s.40-41: iki yönlü akış; filtre olarak güncelleme önerisinde.
- s.45: ölçekleme; risk kuralı, güncelleme önerisinde.
- s.46-48: aşırı volatilitede değer/korelasyon/likidite zorlukları; kavramsal (yazar çoğu kişiye işlem yapmamayı öneriyor).
- s.54-55: istatistik hedefleri; güncelleme önerisinde.
