# Kullanıcı Stratejisi Analizi — EMA 8/21/55 + Hacim + Mum Formasyonları + Destek/Direnç + Trend Çizgisi + Pullback/Breakout

**Tarih:** 2026-10-09
**Kaynaklar:** `metinler/` klasöründeki 7 kitap.
**Kısaltmalar:** Trends / TR / 10P = Al Brooks'un üç kitabı. Woods = Galen Woods Cilt 3. 51S / 20S / 151S = strateji derlemeleri. "S." = metindeki "## Sayfa N" başlığı.

**Strateji (kullanıcının anlatımıyla):** EMA 8, 21, 55 · hacim · engulfing ve hammer mumları · destek/direnç · trend çizgileri · pullback ve breakout.

---

## 1. Genel teşhis

Bileşenlerin hepsi kitaplarda geçiyor ve doğru araçlar. Ama liste bir **araç kutusu**, henüz bir **strateji** değil. Kitapların ortak uyarısı tam bu boşluğu gösteriyor. Bir işlemin tanımlı olması için beş şey gerekir:

1. **Bağlam:** piyasa trendde mi, yatay aralıkta mı? Hangi kurulum nerede kullanılır?
2. **Kurulum:** hangi koşul, nesnel olarak nasıl ölçülür?
3. **Tetik:** giriş tam olarak nerede?
4. **Stop:** nerede?
5. **Hedef ve yönetim:** kâr nerede alınır, pozisyon nasıl taşınır?

Listede yalnızca 2. madde var; o da nesnel değil. "Destek/direnç", "trend çizgisi" ve "güçlü mum" göze göre değişir. Böyle olunca hem backtest yapılamaz hem de canlıda disiplin bozulur.

Brooks'un "iki nedene ihtiyacınız var" ilkesi (TR S.484) çoklu teyit fikrini destekliyor. Bu stratejinin ruhu da bu. Ancak her teyidin ölçülebilir olması gerekir.

---

## 2. Bileşen bazında: kitaplar ne diyor, ne eksik, nasıl geliştirilir

### 2.1 EMA 8 / 21 / 55
**Destekleyen:**
- 20S Strateji 3: 10/21/50 EMA. 10 ile 21 EMA arası "BÖLGE"dir. Trend yönünde bu bölgeye geri çekilmede işleme girilir. 50 EMA "yataydan yaklaşık 30 derece" eğimli olmalıdır (S.3).
- 20S S.9–10: 14/21/50 EMA hem 5 dakikalıkta hem 1 saatlikte sıralı olmalıdır.
- 51S S.385: yükselen ortalamalar dinamik destek görevi görür.

Senin 8/21/55 yapın bunlara çok yakın.

**Uyarılar:**
- Ortalamalar yataylaşınca piyasa sıkışmadadır ve kesişimler testere üretir (51S S.385, TR S.335, TR S.389 "barbwire").
- 20S S.13: "Fiyat sadece 50 ila 100 EMA arasında işlem görüyorsa, işlemi yapmayın."
- 151S S.116: kesişimin tek başına öngörü gücü yoktur.
- Brooks yalnız 20 EMA kullanır, o da bağlam içindir. Ona göre düz trend çizgileri ortalamadan daha güvenilirdir (Trends S.31, S.230).

**Eksik:**
- Yatay piyasa filtresi
- Eğim şartı
- Üst zaman dilimi uyumu
- EMA'nın görevinin tanımı: yön mü, giriş bölgesi mi, çıkış mı?

**Öneri:**
- **55 EMA:** yalnız yön filtresi. Fiyat üstünde olmalı ve EMA yükselmeli.
- **8 > 21 > 55 sıralaması:** trend var demek.
- **8–21 arası:** pullback giriş bölgesi.
- **21 EMA'nın altında kapanış:** çıkış veya stop sıkılaştırma.
- **Yatay filtre:** 55 EMA'nın eğimi ATR'ye göre çok küçükse işlem yok.
- **Brooks'tan ek:** trendde iki ardışık kapanışın EMA'nın karşı tarafında olması trendin zayıfladığını gösterir (Trends S.47).

### 2.2 Hacim
**Destekleyen:**
- 51S S.46–48 (üçgen) ve S.416–418 (VCP): geri çekilmede hacim azalır, kırılım mumu "yüksek hacimli" olmalıdır.
- Brooks da güçlü kırılımlarda hacmin ortalamanın 10–20 katına çıkabildiğini yazar (TR S.80, S.88).

**Karşı görüş (Brooks):** "Hacim… güvenilir değil." Büyük trend çubuğu bilgiyi zaten veriyor; hacme odaklanmak "dikkatinizi dağıtacak" (TR S.88, Trends S.32).

**Öneri:**
- Hacmi **yalnız kırılım kurulumunda** teyit olarak kullan: kırılım mumunun hacmi son 20 mumun ortalamasının en az 1,5–2 katı olsun.
- Pullback kurulumunda geri çekilme sırasında azalan hacim istenebilir. Zorunlu şart yapma.
- Kriptoda hacim borsa ve vadeli işlem nedeniyle gürültülüdür. Gerçekten katkı sağlayıp sağlamadığını test etmek gerekir.

### 2.3 Engulfing ve hammer mumları
**Kitaplar ne diyor:**
- Kitaplarda "engulfing" yalnız 51S'de bir kez geçiyor. Brooks ve Woods bunu **dış çubuk** olarak ele alıyor ve şüpheci: dış çubuk tek mumluk bir yatay aralıktır, stop uzaktır.
  - "Neredeyse her zaman akıllıca değildir" (Trends S.171–172).
  - "Genellikle güvenilir değildir… ikinci bir kurulum çubuğunu bekleyin" (Woods S.60, S.173–176).
- **Hammer / pin bar:** Brooks'ta "ters çubuk". İyi bir dönüş çubuğunun ölçütleri (Trends S.106–107):
  - kapanış açılışın ve orta noktanın üstünde
  - alt fitil boyun 1/3 ile 1/2'si kadar, üst fitil küçük
  - önceki mumlarla fazla örtüşmüyor
  - ardından güçlü bir giriş çubuğu geliyor
- Woods S.104–110 ve 166: tek fitil "yeterince güvenilir olmayabilir". Önem sırası şöyle; mumun şekli **en az önemli** etkendir:
  1. piyasa eğilimi
  2. destek/direnç
  3. birden fazla kurulumun aynı yeri göstermesi
  4. mumun şekli
- 51S S.398–403: "İlk Pin Bar'da işlem yapamayız". İlk pin bar seviyeyi işaretler, işlem aynı seviyedeki ikinci pin bara açılır. Rastgele mum alınmaz; mum ancak aralığın kenarında anlamlıdır.
- **En sık hata:**
  - Güçlü trende tek dönüş mumuyla karşı gelmek. Trendi dönüştürme girişimlerinin yaklaşık %80'i başarısız olur (Trends S.80, S.285).
  - Aralığın ortasında, önceki mumlarla örtüşen büyük mumlarla işlem açmak. Bunlar genelde tuzaktır (Trends S.108–109, TR S.348).

**Eksik:**
- Mum kalitesinin ölçüsü
- Zorunlu konum (destek veya EMA)
- Yalnız trend yönünde işlem şartı
- Tetik: kapanışta değil, mumun tepesinin üstüne konan alış stop emri (Trends S.72)
- Stop: mumun dibinin altı
- İkinci giriş kuralı

**Öneri:**
- Mumu tek başına sinyal sayma; yalnız **pullback'in bittiğini gösteren tetik** olarak kullan.
- Yalnız trend yönünde ve destek bölgesinde (8–21 EMA bölgesi veya kırılan direnç) olanı al.
- Engulfing yerine Brooks'un "güçlü boğa dönüş çubuğu" tanımını kullan. Dış çubukta işlem açacaksan bir mum daha bekle.

### 2.4 Destek / direnç
**Kitaplar ne diyor:**
- Brooks'un nesnel seviye listesi ("mıknatıslar", TR S.155–156):
  - önceki salınım tepe ve dipleri
  - dünün tepe, dip ve kapanışı
  - büyük trend çubuklarının uçları
  - ölçülü hareket hedefleri
  - günlük pivotlar
  - hareketli ortalamalar
  - trend ve kanal çizgileri
- Gerçek bir seviye en az yaklaşık %60 yön avantajı sağlamalıdır.
- Woods'a göre destek ve direnç **bir çizgi değil, bir bölgedir** (S.6, S.33).
- Trend içinde çoğu destek/direnç kırılır. Dönüş başarısı "çoğu zaman yalnızca %40" (TR S.154–155).

**Eksik:** seviyenin nasıl çizildiği tanımlı değil. Hangi salınım? Kaç mum geriye bakılıyor?

**Öneri:**
- Seviyeleri **pivot tepe/dip** olarak tanımla: iki yanında N mum daha düşük olan tepe.
- Kırılan direnci, yeniden test edildiğinde destek say (kırılım geri çekilmesi).
- Önceki günün tepe ve dibini ekle.
- Seviyeye ±0,25–0,5 ATR'lik bir bölge olarak bak.

### 2.5 Trend çizgileri
**Kitaplar ne diyor:**
- Çizgi salınım diplerinden çizilir. Ana trend çizgisinin noktaları genelde en az 10 mum aralıklıdır (Trends S.10, S.203–206).
- **Kırılım tek başına dönüş değildir;** yalnız "ilk işaret"tir. Ardından eski uç test edilir. Dönüş işlemi için kırılım, ardından uç noktanın testi ve güçlü bir dönüş çubuğu gerekir (Trends S.10, S.30, S.108).
- "Çoğu çıkış başarısız olur!" Deneyimli trader boğa trend çizgisinde alır (Trends S.209).
- Boğa kanalı %75 olasılıkla alttan kırılır. Kanalın üstüne yapılan kırılımın tutma oranı yalnız %25'tir (10P S.11, S.14).

**Eksik:** çizgiyi nesnel çizme kuralı ve çizginin hangi işe yaradığı.

**Öneri:**
- Elle çizim backtest edilemez. Son iki yükselen pivot dibi birleştiren otomatik bir çizgi kullan.
- Çizgiyi **giriş için değil, yönetim için** kullan. Fiyat çizgiye dokunup döndüyse alım bölgesidir. Çizgi kırıldıysa yeni alım yapılmaz, stop sıkılaştırılır.

### 2.6 Pullback ve breakout
**Pullback:**
- İki bacaklı geri çekilmeler (H2) yüksek olasılıklıdır, ama yalnız boğa trendinde veya aralığın dibinde (10P S.8–9, TR S.484).
- Güçlü trendde ilk pullback neredeyse her zaman tepenin yeniden test edilmesiyle sonuçlanır (Trends S.165).
- Woods'a göre (S.147–150) ardışık en az 3 ayı mumu yoksa geri çekilme "zayıftır". Zayıf geri çekilme trendin devam edeceğine işaret eder.

**Breakout:**
- Aralık kırılım girişimlerinin yaklaşık **%80'i başarısız olur** (TR S.169, S.328, S.335). En güçlü kırılımlar bile %30 oranında başarısız olur (TR S.87).
- Güçlü kırılımın göstergeleri (TR S.80–81):
  - büyük gövde, küçük fitil
  - birkaç seviyenin üstünde kapanış
  - takip mumları
  - ilk geri çekilmenin kırılım noktasına inmemesi
- Kırılımdan hemen almak mı, geri çekilmeyi beklemek mi? Güçlü trendde hemen almak daha iyidir; aralıkta beklemek gerekir (TR S.100, S.209).
- 51S S.386–392: önce konsolidasyon, sonra 9/21 kesişimi, sonra direnç kırılımı; giriş kırılım mumunun üstünden.

**Eksik:**
- **Trend ile aralığı ayırt eden kural.** En kritik eksik bu. Aynı breakout trendde işe yarar, aralıkta %80 başarısız olur.
- Pullback'in nesnel tanımı (derinlik, bacak sayısı)
- Kırılımın nesnel tanımı (hangi seviye, kaç mumluk sıkışma)

---

## 3. Bizim testlerimizde bu bileşenler ne yaptı?
Kripto verisi, 2020–2026, masraf dahil; ayrıntılar `RAPOR_PA.md` ve `RAPOR_KRIPTO.md`.

| Bileşen | Bizim test | Sonuç |
|---|---|---|
| Pin bar / hammer (51S kuralları) | 4 saatlik, trend yönünde | ❌ test dönemi PF 0,82 |
| Mum kurulumları (Woods'un 7 kurulumu) | 1 saatlik | ❌ PF 0,75–0,88 (masraf, stopun ~%13'ü) |
| Pullback (Brooks H1/H2) | 1 ve 4 saatlik | ❌ başarısız |
| Kırılım geri çekilmesi | KGT'ye ek | ❌ |
| Sıkışma kırılımı (CPR dar + R1 kırılımı) | KGT | ✅ çalışıyor |
| EMA trend takibi (4 saatlik EMA 21/50 çıkışı) | KGT çıkışı | ✅ kârın ana kaynağı |
| Günlük kapanış > EMA20 | KGT v3 | ✅ küçük iyileşme |

**Çıkarım:** Bu stratejinin bizde **çalışmış parçaları** şunlar:
- EMA trend filtresi
- Sıkışma sonrası kırılım
- Trendi EMA ile takip edip uzun süre taşımak

**Tek başına çalışmayan parçalar:** mum formasyonları ve pullback girişleri. Bunlar ancak güçlü bağlam ve iyi yönetimle birlikte değer kazanabilir.

Bu, Woods'un "mum şekli en az önemli etkendir" sözüyle de uyumlu.

---

## 4. Somut kural önerisi (test edilebilir sürüm, "EPA")
**Kurgu:** zaman dilimi önerisi 1 günlük bağlam + 4 saatlik işlem. 1 saatlikte masraf ve gürültü bu tip kurulumları öldürüyor. Yalnız long; short ayrı test edilir.

**Bağlam (1 günlük):**
- EMA 8 > 21 > 55
- Kapanış > EMA 21
- EMA 55'in son 5 gündeki eğimi > 0
- *Yatay filtre:* EMA 21'in 10 günlük değişimi < 0,5 ATR ise işlem yok.

**Kurulum A — Pullback (4 saatlik):**
1. Fiyat 8 ile 21 EMA arasındaki bölgeye geri çekilir. Bunun ölçüsü: mumun dibi EMA 8'in altında, kapanışı EMA 55'in üstünde.
2. Geri çekilme en az 2 mum sürer. H2 tercih edilir.
3. **Sinyal mumu:** boğa dönüş çubuğu. Kapanış mum boyunun üst 1/3'ünde, alt fitil ≥ boyun 1/3'ü, kapanış > açılış, mum önceki mumla %50'den az örtüşüyor. Hammer ya da gövdesi büyük boğa mumu olabilir. Engulfing de bu tanıma girer.
4. **Konum:** sinyal mumunun dibi EMA 21'e veya bir önceki kırılmış dirence ±0,5 ATR yakın.
5. **Tetik:** sinyal mumunun tepesi + 1 tik alış stop emri, 2 mum geçerli.
6. **Stop:** sinyal mumu ya da geri çekilme dibi − 0,2 ATR (en az 1 ATR).

**Kurulum B — Breakout (4 saatlik):**
1. Son 10–20 mumun aralığı < 3 ATR (sıkışma) ve bu sırada EMA 8 ile 21 iç içe.
2. **Kırılım mumu:** kapanış aralığın tepesinin üstünde, gövde boyun en az %60'ı, hacim 20 mum ortalamasının ≥ 1,5 katı.
3. **Giriş:** kırılım mumunun kapanışında, ya da kırılım seviyesine geri dönüş testinde. İkisi de test edilecek.
4. **Stop:** aralığın orta noktası veya kırılım mumunun dibi.

**Yönetim (iki kurulumda aynı):**
- 1R'de pozisyonun bir kısmı kapatılır, stop başabaşa çekilir.
- Kalan kısım 4 saatlik EMA 21 altında 2 kapanışta ya da EMA 8 < 21'de çıkar.
- Alternatif hedef: ölçülü hareket veya bir sonraki direnç.

**Test planı:** KGT ile aynı çerçeve.
- ilk 15 coin, masraf + fonlama dahil
- IS 2020–2023 / OOS 2024–2026
- komşu parametreler, maliyet ×2, rastgele giriş kıyası, mum hizalama kaydırması
- **Bileşen katkı testi:** hacim, mum kalitesi, trend çizgisi ve konum şartlarının her biri tek tek açılıp kapatılır. Hangisinin gerçekten değer kattığı ölçülür.
- **KGT ile korelasyon.** Düşükse iki strateji birlikte çalıştırılabilir.

---

## 5. Kısa özet
- **Güçlü yanlar:** trend yönünde çalışma, EMA bölgesine pullback, sıkışma kırılımı, çoklu teyit. Bunlar kitapların ana fikirleriyle uyumlu.
- **En kritik eksik:** trend ile yatay aralık ayrımı, tetik, stop ve hedef kurallarının tanımlı olmaması.
- **Yanlış yerde güç:** mum formasyonları stratejinin merkezinde duruyor. Kitaplar ve bizim testlerimiz mumun en zayıf halka olduğunu gösteriyor.
- **Yeniden düşünülmesi gereken:** hacim (Brooks'a göre güvenilir değil, yalnız kırılım teyidi) ve elle çizilen trend çizgisi (nesnel değil, yönetim aracı olarak kullanılmalı).
