# Tam okuma: Alan Farley, Swing Trader (306 sayfa) — sayfa 154-306 (parça: farley_2)

Kaynak metin: `veri/pdf_metin_2/swing/Swing_Trader_-_Alan_S_Farley_306_sayfa.txt` (metindeki `=== SAYFA n ===` numaraları kullanıldı).
Çıktı: `veri/kartlar_ham/swing/Swing_Trader_-_Alan_S_Farley_306_sayfa__tam_farley_2.json` (9 kart) ve
`veri/kartlar_ham/daytrade/Swing_Trader_-_Alan_S_Farley_306_sayfa__tam_farley_2.json` (2 kart). Doğrulama temiz.

Not: Görev notunda anılan "bölüm 11 mum/tersine dönüş formasyonları" bu sayfa aralığında yok. Bölüm 11 (s.263-277) "Kaybetmenin Doğası" adlı psikoloji
bölümü; kitap boyunca mum/tersine dönüş formasyonları ayrıntıları "Master Swing Trader" kitabına gönderme olarak geçer, burada tanımlanmaz.
Aralığın büyük kısmı risk/psikoloji/piyasa seçimi/gün içi okuma anlatısıdır; kurulum sayısı az, kodlanabilirlik düşüktür.

## Okunan aralık (20 sayfalık bloklar, tek satır konu)
- 154-173: ikili giriş (çift yönlü dikdörtgen kurulumu), Mosaic "kaya ve sert yer" örneği, piyasaya giriş psikolojisi, marj, beklenti-tepki (NR7 stop fikri).
- 174-193: piyasa/hisse evreni seçimi, ETF'ler, sabah "maverick" taraması, pozisyon boyutu, Fibonacci kademeli alım (Nordstrom), sepet ticareti.
- 194-213: elde tutma süreleri, haftalık uzaktan ticaret, "ticaret katilleri" örnekleri, durak yerleşimi, Apple kısa vadeli stoplar, üç aşamalı iz süren stop.
- 214-233: durulama/stop mıknatısı, gece tutma, gün sonu 10 soru, gün içi bant okuma, trend günü uçları, piyasa öncesi/sonrası.
- 234-253: piyasa öncesi kontrol listesi, haber ticareti, gün içi salınım, boşluk türleri (kopuş/devam/tükenme), durulama (shakeout) türleri.
- 254-273: olay riski, "kesme bloğu" (dalgalı piyasa), boşluk günü ilk saat aralığı (Dow Chemical), kaybetmenin doğası, aşırı ticaret, ticaret hataları.
- 274-306: düşüşler/bırakma işaretleri, sermaye korunumu, ödül:risk planı, "yaka" (agresif-savunma) ayarı, kademeli girişler (Apple), çıkış stratejileri, yeniden giriş (Schlumberger), usta ticaret örnek gün.

## Yeni kartlar (11)
Swing (9):
- swing__ikili-giris-dikdortgen__farley (s.154-157)
- swing__fibonacci-kademeli-alim__farley (s.187-191, 290-291)
- swing__haftalik-uzaktan-kademeli-giris__farley (s.197-200)
- swing__devam-boslugu-geri-test__farley (s.247-249)
- swing__kopus-boslugu-bayrak-geri-cekilme__farley (s.246-247)
- swing__tukenme-boslugu-tersleme__farley (s.246, 249-250)
- swing__durulama-stop-avi-donusu__farley (s.212, 215, 253-254)
- swing__stop-sonrasi-yeniden-giris__farley (s.167, 209-210, 293-295)
- swing__uc-asamali-iz-suren-stop-cikis__farley (s.211-213, 215, 296-299) — giriş yok, yönetim/çıkış modülü
Daytrade (2):
- daytrade__bosluk-gunu-ilk-saat-araligi__farley (s.159-161, 244-245, 258-262)
- daytrade__aralik-durulama-gun-ici-tersine__farley (s.250-253)

Kodlanabilirlik: 2 puan: ikili giriş, Fibonacci kademeli alım, üç aşamalı iz. 1 puan: kalan 8. Hiç 3 yok. Hiçbirinde stop+hedef birlikte tam sayısal verilmemiştir.

## Güncelleme önerileri (mevcut kartlar için; kart eklenmedi)
1. `daytrade__ilk-saat-araligi-kirilim-ve-basarisizlik__farley`
   - Aralık oluşturma (s.153-154): ilk 30 dk bekle, 5dk grafikte bu dönemin yüksek/düşüğüne yatay çizgi çiz, sonraki 30 dk içinde çizgileri ayarla; salınım seviyesi 5dk karşı salınım (yüksek/düşük) oluşana kadar ölçülmez.
   - Filtre: ilk saatin sonunda zaten trende girmiş (ileri geri salınmamış) enstrümanlarda strateji kullanılmaz (s.154).
   - Min ödül:risk: beklenen kazanç riskin en az 3 katı olmayan işlemden kaçın (s.153-154; örnek giriş 30, hedef 30,70, stop 29,80).
   - Beklenti kuralı: aralık ucunu ilk denemede geri dönmesi, sonraki denemede başarılı olması beklenir; gün içinde küçük kupa-kulp / ters kupa-kulp (s.259).
   - Varyantlar: agresif = 3-4 adet 5dk çubukla aralık; savunmacı = boşluk sonrası 2-4 günlük aralık; kesin giriş fiyatı 1-2 tik gürültü içinde karar işi (s.260).
   - Yönetim: 15dk grafikte 8 barlık SMA ihlalinde çık (s.215).
   - Rejim: trend günü uçları (NYSE TICK ±1000, ilerleme/düşüş ±1500-2000, yukarı/aşağı hacim 4:1, endeks vadeli ±%2) varsa ters (fade) kurulumlarından kaçın (s.227-228) — bu veriler kriptoda yok.
2. `swing__50ema-geri-cekilme__farley`
   - Stop sonrası yeniden giriş (s.293-294): 50 EMA'dan alım stop olduktan sonra fiyat 50 EMA'yı yeniden aşarsa yeniden gir, stop kurtarma çubuğunun dibinin altı (bkz. yeni kart `swing__stop-sonrasi-yeniden-giris__farley`).
   - Stop seviyesi: stop'u 50 EMA gibi yaygın seviyenin hemen arkasına koyma riski (stop mıknatısı); durulama aşırı seviyesinin bir tik ötesi alternatifi (s.210, 214-215).
   - ETF'lerde 50 ve 200 günlük EMA'larda geri dönüşler iyi çalışır (s.181).
3. `swing__fibonacci-62-78-kamci__farley`
   - %78 geri çekilme çıkış sınırı ve kademeli limit alım ızgarası (%38/%50/%62, oran 25/25/50) için yeni kart `swing__fibonacci-kademeli-alim__farley`; aynı oranlarda sinyal tabanlı (kamçı) giriş ile limit tabanlı giriş aynı backtestte karıştırılmamalı.
   - Fibonacci çıkışı: son bacağın %62'si, kırık zirve/dolu boşluk/ihlal edilmiş MA ile çapraz doğrulama (s.297-298).

## Kart çıkmayan bölümler ve nedeni
- s.158-161 (Mosaic uygulaması): ikili giriş + boşluk günü; yeni kart `daytrade__bosluk-gunu-ilk-saat-araligi__farley` içine işlendi.
- s.162-173, 263-277: psikoloji, marj, hata listeleri, bırakma ölçütleri: kurulum yok.
- s.174-186: piyasa/sektör evreni, ETF'ler, sabah "maverick" taraması (aşağı açılışta yeşil hisse vb.): öznel liste, kural/eşik yok; likidite ipucu (60g ortalama hacim >200.000 hisse) evren filtresi notu olarak kalır.
- s.191-193 sepet ticareti: portföy kurma yöntemi (200 EMA'nın %10 üstü filtre, eşit ağırlık); giriş tetiği günlük endeks grafiğinin kırılım/geri çekilme sinyali, ayrı kural yok.
- s.194-196, 215-221: gece tutma, gün sonu 10 soru, Salı dönüşü/hafta içi eğilimler: karar yardımcı soruları ve kanıtsız takvim iddiası; kural ve stop/hedef yok. (Haftanın günü eğilimi: Cuma kapanışı yönünde Pazartesi ön piyasa → trendi izle, Salı geri dönüş, Çarşamba-Perşembe devam; test edilebilir hipotez ama kitapta kanıt ve eşik yok.)
- s.222-231 bant okuma, açılış fiyatı ilkesi (Pesavento), gizli kırılımlar: Level-2/TICK/bant verisine bağlı veya tanımı belirsiz (açılış fiyatı pivot çizgisi ilkesi için tetik/stop yok).
- s.232-243 piyasa öncesi/haber ticareti: haber verisi gerektirir (karar: olay verisi elenenler arasında); haber sonrası 60dk 50 EMA'ya kademeli limit alım fikri sayısal kural içermez.
- s.243-246 gün içi salınım, 15dk stokastik: yorum rehberi (aşırı alım/satımda dönüş varsayma, 1-2-3 / 1-2-3-4-5 bekle), giriş kuralı yok.
- s.254-262 olay riski, kesme bloğu: rejim ve savunma notu; kesme bloğunda boşlukların çoğu dolar iddiası boşluk günü kartının filtresine işlendi.
- s.278-306 sermaye korunumu, "yaka" (agresif-savunma): risk toplamı hesap büyüklüğünün 1/3'ü (savunma) - %90'ı (destekleyici) gibi kitap rakamları bizim sert limitlerimizle (işlem başı %1, günlük %3, 3x, %20) uyuşmaz, uygulanmaz; VIX 25 ve 35 eşikleri rejim notu olarak belirsizlikte kalır. Haftalık işlem sayısını yarıya indirme, 250$ günlük kayıp limiti gibi öneriler kodda zaten sert limit olarak var.
