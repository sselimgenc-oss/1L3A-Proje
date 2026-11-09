# Tam okuma: Ultimate Scalper (Gün İçi İşlem Metodolojisi), sayfa 1-496

Sonuç: **yeni kart yok** (çıktı dosyası boş dizi). Kitabın tüm kurulumları (çift tepe/dip + üçlü varyant, aşırı alım/satım, histogram, sapan, trend çizgisi kırılımı + kahve molası, hacim olasılık testi/son itme) ilk turda zaten kartlanmış. Bu turda yalnızca eksik ayrıntılar bulundu.

Not: Dosyada sayfa 249-496 sayfa 1-248'in İngilizce aslıdır (aynı içerik, sayfa kayması 248). Türkçe kısım tam, İngilizce kısım kontrol amaçlı tarandı; farklı bilgi çıkmadı. Sayfaların çoğu grafik görüntüsüdür, metni yok.

## Okuma kanıtı (20 sayfalık bloklar)
- 1-20: telif, yasal uyarı, içindekiler, ES vadeli tanıtımı, emir türleri (piyasa/limit/stop), platform-komisyon (~2,5$/yön/sözleşme), mum ve OHLC anatomisi. Kart yok (bilgilendirme).
- 21-40: grafik zaman dilimleri (tik/dakika), trend sınıfları, trend çizgisi çizimi (3 nokta kuralı), kanallar, destek/direnç çizme yöntemi başlangıcı. Kavram; trend çizgisi kuralı mevcut karta işlendi.
- 41-60: önceki gün tepe/dip hizalı yatay çizgiler (S/R), floor trader pivot, 50 EMA "tornado", hacim göstergesi ve hacim olasılık testi (VPT). Mevcut hacim kartı kapsıyor.
- 61-80: son yukarı/aşağı itme çubukları, çok sinyalli örnek grafik analizi, yazarın örnek işlem yönetimi (son itmede kâr kilitle). Güncelleme önerisi.
- 81-100: 7 sistemin listesi, trend takip/dönüş sınıflaması, 987-tik ekran düzeni, MACD(5,26,9), yakınsama/ıraksama, stokastik, çift tepe/dip tanımları. Kavram.
- 101-120: çift tepe/dip sistemi tanımı, 3 koşul + "go sinyali", adım adım örnekler, stop yeri. Mevcut karta ayrıntı eklendi.
- 121-140: çift tepe/dip grafik örnekleri (görsel, metin yok).
- 141-160: aynı, yalnız görsel.
- 161-180: aynı, yalnız görsel.
- 181-200: grafik örneklerinin sonu, üçlü tepe/dip kuralları, aşırı alım/satım sistemi tanımı. Güncelleme önerisi.
- 201-220: aşırı alım/satım örnekleri ve özel hususlar (keskin MACD dönüşü, düzgün stokastik, 50 EMA yönü), histogram sistemi, sapan sistemi tanımı. Güncelleme önerisi.
- 221-240: sapan örnekleri, trend çizgisi kırılım sistemi (çapa, 45 derece, 3 nokta, sahte kırılım), kahve molası. Güncelleme önerisi.
- 241-248: kahve molası örnekleri, başarı ipuçları (seans saatleri, 2000 tik, öğrenci anketi sırası), sonuç (günlük hedef/zarar limiti), videolar.
- 249-496: yukarıdakinin İngilizce aslı (sayfa n+248 = sayfa n); farklı içerik yok.

## Yeni kart listesi
Yok.

## guncelleme_onerileri
Kart kimlikleri: `scalp__<ad>__ultimate-scalper`.

1. **cift-tepe-dip-macd-stokastik** (s.102-125, 188-190)
   - Sıra: tepe oluşur, geri çekilme (birkaç mumdan büyük U/V'ye kadar olabilir), fiyat ilk tepeyi test edip en az eşitler (aşması normal, geçerli). Sonra MACD ve stokastik ilk tepedekinden düşük olmalı ve girişte düşük kalmalı.
   - "Go sinyali": MACD ucu kapanışta herhangi bir açıyla aşağı bakmalı; yatay MACD geçerli değil (s.106-108). Hafif yukarı bakan ucun long için yeterli sayıldığı örnek var (s.120).
   - Stokastik ikinci tepede ilk tepeye "hemen hemen eşit" ise işlem yazarın takdirine kalmış; başarı için kesin DÜŞÜK (dipte kesin YÜKSEK) olması öneriliyor (s.125). Kodda sıkı `<` / `>` kullanılabilir.
   - Stop: ikinci tepenin en yükseği + 1 tik; gerekçe: ikinci tepe çoğu zaman ilkinden yüksek (s.114).
   - Girişe piyasa emriyle, sinyal mumunun kapanışında girilir; stop emri aynı anda konabilir.
   - Üçlü tepe/dip (s.188-190): 3. tepede MACD ve stokastik, 1. veya 2. tepeden (veya ikisinden) düşük; 3. tepenin fiyatı öncekilerden yüksek, düşük ya da eşit olabilir; giriş MACD'yi aşağı bükten ilk mumun kapanışı. Tepeler bir sonraki üçlüyle paylaşılabilir. Stop kuralı üçlü için ayrıca yazılmamış (çift tepedeki gibi varsayılabilir, belirsiz).
   - Tik grafik ayarı: 987 tik (Fibonacci), 2000 tik daha az yanlış sinyal verir (yeni başlayanlara öneri), 233 tik daha hızlı (s.87, 245).
2. **asiri-alim-satim-macd-donusu** (s.198-206, 215)
   - "İlk dönüş" stokastik 80 üstüne (20 altına) girdikten SONRAKİ ilk MACD dönüşü. Yazar zayıf, hemen kaybeden ilk dönüşü değil, keskin/sivri (yaklaşık 90 derece) dönüşü tercih ediyor (s.203). Ölçülebilir öneri (kitapta sayı yok): MACD'nin bir önceki çubuğa göre eğim değişimi eşiği, yalnız `belirsizlikler`'e.
   - Filtre: MACD ve stokastik dalgalı/zikzaklı iken işlem yok; stokastik düzgün akıyorsa tercih (s.204-205). Kodlanabilir yaklaşık: son N çubukta stokastik yön değişimi sayısı üst sınırı (sayı kitapta yok).
   - 50 EMA yönünde işlemler daha yüksek başarılı; yazar ters yöne de işlem yapıyor, çünkü sistem yeni trend başlangıcını 50 EMA'dan erken yakalar (s.206). Zaman: ilk ve son seans saatleri daha iyi (s.245).
   - Örnek: floor pivot direncinden dönüş + sinyal birlikte (s.215), onay olarak.
3. **histogram-sistemi** (s.216-219)
   - Giriş: bir taraftaki çubuk serisi bitip ilk karşı taraf çubuğunun mumunun kapanışı; histogram "dalga gibi düzgün" olmalı, kırık/eksik dişli görünüyorsa kullanılmaz (s.218). Yedek giriştir: çift tepe/dip ve OBOS koşulu yokken, başka onaylarla yön fikri varsa (s.216).
   - Stop ve hedef bu bölümde de yok.
4. **sapan-macd-ave-geri-cekilme** (s.220-225)
   - Geri çekilme mumu KAPANDIKTAN sonra stop emri konur; geri çekilme tek veya birkaç mum olabilir; her yeni ardışık düşük (yüksek) geri çekilme mumunun kapanışından sonra emir o mumun yükseği (düşüğü) + (-) 1 tik'e taşınır; emir dolana veya MACDAve dönmeye başlayana kadar (s.220, 225).
   - Stop: geri çekilmedeki en düşük (yüksek) -/+ 1 tik.
   - "MACDAve" = MACD(5,26,9)'un sinyal çizgisi (yavaş mavi çizgi, s.220).
   - Dolum sonrası momentumun hemen kâr getirdiği belirtiliyor, yazarın en sevdiği giriş (s.225). Öğrenci anketi sırası: 1 sapan, 2 histogram, 3 çift tepe/dip, 4 üçlü, 5 trend çizgisi, 6 OBOS (s.245).
5. **trend-cizgisi-kirilimi-kahve-molasi** (s.233-240)
   - Çapa: son trend tepesi/dibi; iki mum aynı yükseklikteyse düşüş trendinde en sağdakini seç (s.237). Sonraki en az 2 noktada çizgi mükemmele yakın hizalanmalı (toplam 3 dahil çapa); çizgi uydurulmaz.
   - Eğim: en fazla yaklaşık 45 derece; sığ çizgide kırılım daha güvenilir (s.239).
   - Sahte kırılımda çizgi yeniden çizilir (s.234). Aynı dipten/tepeden iki farklı çapa (hafif farklı mum) ile iki çizgi çizilip ikisi de işlem verebilir (s.238).
   - Stop: önceki önemli tepe/dip -/+ 1 tik veya "rahat" seviye (s.234).
   - Kahve molası: çizgi seans öncesi (5:30 PT) kurulur, normal seans 6:30 PT'de açılır (s.236, 240); yazar seans 6:30-13:00 PT (= 9:30-16:00 ET) alır (s.234).
   - Çizim kolaylığı için ölçülebilir öneri: zikzak pivotları + doğrusal regresyon/RANSAC (yalnız `belirsizlikler`).
6. **hacim-olasilik-testi-son-itme** (s.57-81)
   - Hacim göstergesi: son 5 çubuk ortalama hacim çizgisiyle; mum önceki kapanıştan yüksek kapandıysa "yukarı" renk, düşükse "aşağı" renk (s.59). 1 veya 3 dk grafikte, tik grafikte değil (s.57).
   - Yönetim kuralı (kartta yoktu): açık pozisyon lehine ve karşı renk "son itme" çubuğu görülürse çıkış ya da stopu kâr kilitleyecek yere çek (s.77). Hedef/çıkış olarak kullanılabilir.
   - Başarısız test sonrası stop: test edilen ucun 1 tik ötesi (s.81).
   - Yazar bunları tek başına işlem kuralı yapmıyor; trend çizgisi kırılımı, 50 EMA uzaklığı gibi onaylarla birleştiriyor (s.71).
7. **Tüm kartlara filtre notu (50 EMA "tornado" ve S/R)** (s.52-56, 39-51)
   - Fiyat 50 EMA'nın çok uzağındayken EMA'ya doğru yönde sinyal güven artırır; EMA'nın hemen (yaklaşık bir puandan az) karşı tarafındayken yazar temkinli, çoğu zaman girmez (s.55-56). Ölçülebilir öneri: |kapanış - EMA50| / ATR eşiği (kitapta sayı yok; yalnız `belirsizlikler`).
   - Yatay S/R: önceki 1-2 seansın hizalanan tepe/diplerinden çizgi, fiyat ±birkaç tik tolerans; destek kırılınca direnç olur (s.39-46). Floor pivot ile üst üste gelen S/R daha güçlü (s.51, 245). Yalnız onay; giriş kuralı yok.
   - Seans: günün ilk ve son birkaç saati daha iyi, öğle saati yan kanal ve yanlış sinyal (s.245).
   - Risk çerçevesi (kitapta, 1L3A limitleriyle çelişir mi diye lider baksın): günlük kâr hedefi 50-200$ ve zarar limiti 200-250$ sonrası gün biter, ilk işlemler 1 sözleşme (s.246). Yazar 1-10 sözleşme ve günde 1,5-2,5 puan hedefler (s.84).

## Kart çıkmayan bölümler
- Giriş, emir türleri, platform/komisyon, mum ve zaman dilimi anlatımı (s.1-22): bilgilendirme.
- Trend çizgisi/kanal çizimi genel anlatım (s.26-38): trend kanalı sıçraması "dönüş hedefi" olarak anılıyor ama giriş/stop/hedef kuralı yok.
- Destek/direnç ve floor pivot (s.39-51): yalnız çizim ve yorum; pivot formülü yok, giriş kuralı yok.
- 50 EMA "tornado" (s.52-56): filtre/bağlam, tek başına kural yok.
- Çok sinyalli örnek grafik analizi (s.71-81): mevcut kartların birleşik uygulaması.
- Grafik örnekleri (s.121-187, 193-197, 207-214, 222-232, 241-244): görsel, metin yok.
- Başarı ipuçları ve sonuç (s.245-247): genel tavsiye (risk ve duygu), yalnız yukarıdaki filtre/risk notları alındı.
- İngilizce aslı (s.249-496): Türkçe kısmın birebir tekrarı.
