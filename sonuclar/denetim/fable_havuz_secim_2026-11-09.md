# Strateji havuzu ve seçim mantığı — bağımsız değerlendirme ve "v2" önerisi

Tarih: 2026-11-09 · Hazırlayan: Fable (yöntem denetçisi) · Durum: **yalnız ÖNERİ** (karar kullanıcı + lider)

Kurallara uyum: repoda hiçbir dosya değişmedi. Holdout verisi (2025-11-08 sonrası) okunmadı, `kilit_ac=True` ile hiçbir
çağrı yapılmadı. Bütün sayılar geliştirme dönemi sonuç dosyalarından (`sonuclar/evren/2017_gelistirme/`) ve kilit öncesi
fiyat verisinden hesaplandı. Bu sayılar "görülmüş" veriye aittir: tasarım teşhisi içindir, kanıt değildir.

---

## 0. Bir sayfada sonuç

**Ne sağlam?** Altyapı disiplini iyi: ön kayıt, mühür, holdout'un kodla kesilmesi, tek kasada sert limitlerle yeniden
oynatma, maliyet tablosu, hataların sessiz geçilmemesi, "sonuç sonrası değişiklik" kayıtları. Rastgele giriş testi (K2)
doğru fikir ve hattın en değerli parçası. Bunlar korunmalı.

**Asıl sorunlar (önem sırasıyla):**

1. **Havuz geniş görünüyor ama tek bir şeye yaslanıyor: yükselen piyasada "long" olmak.** WF'yi geçen 38 stratejinin 32'si
   yalnız long, kalan 6'sında da kısa taraf zararda (kısa PF < 1). 38'in 27'si 2022'de (tek ayı yılı) zarar etti. Swing
   havuzunda long tarafı kârlı olan strateji oranı %85, kısa tarafı kârlı olan %3. Evrenin düz "al-tut" Sharpe'ı 1.69
   (bugünün kazananlarından seçildiği için şişkin) — yani PF ≥ 1.2 / Sharpe ≥ 0.5 eşikleri bu dönemde "ortalama strateji"
   seviyesi, ayırt edici değil (swing 1d'de sabit bir ayarın medyan PF'si zaten 1.23).
2. **Çoklu test düzeltmesi (K5/DSR) yanlış kurulmuş, ama doğru kurulunca da 24 çıkmıyor.** Doğru birim "ayar" değil
   "strateji"dir (ayar seçimi WF içinde zaten örneklem dışı). Aynı veride doğru kurulmuş bir aile testi (Romano-Wolf)
   **2**, daha yumuşak bir yanlış-keşif testi (BH %10) **yaklaşık 6**, rastgele girişe karşı aile düzeltmeli test
   **yaklaşık 12** strateji bırakıyor. Dürüst beklenti: "0 değil, 24 de değil; 2–12 arası".
3. **Parametre ızgarası + WF ayar seçimi neredeyse hiçbir şey katmıyor.** Swing 1d'de WF'nin seçtiği ayar, rastgele bir
   sabit ayardan ortalama yalnız 0.04 PF iyi (yüzdelik sırası 0.57; 0.50 = hiç fark yok); varsayılan ayardan farkı 0.02.
   Buna karşılık 32.200 görev, 35 saat hesap ve "deneme sayısı" şişmesi getiriyor.
4. **Kapıların çoğu ya etkisiz ya da yanlış şeyi ölçüyor.** WF'yi geçenlerde K1 (×2, ×3, gecikme) ve K4 hiç kimseyi
   elemiyor; PBO her grupta ~0 (bozuk); korelasyon süzgeci neredeyse hiç bağlamıyor. En çok eleyen kapı "en iyi %5
   işlem hariç PF ≥ 0.9" (40 stratejiyi tek başına eliyor) ve yapısı gereği trend takibini cezalandırıyor.
5. **Holdout kapısı zayıf:** "net > 0 ve PF ≥ 1.1" kuralını hiç avantajı olmayan bir strateji 12 ayda **~%39** ihtimalle
   geçer. 9 aday götürülürse en az birinin şansla geçme ihtimali ~%99. Üstelik evren listesi holdout'un SON günündeki
   piyasa değerine göre seçildi (ileriyi görme).

**Öneri (v2), tek cümle:** havuzu mekanizma bazında tekilleştir, **varsayılan ayarla** koş (ızgara yalnız sağlamlık
kontrolü), tek resmi istatistik testi **rastgele girişe karşı** yap ve yanlış-keşif oranını (%10) **strateji sayısı**
üzerinden kontrol et, sağ kalanları "en iyi 3" diye değil **küme başına bir temsilci, eşit risk** ile sete koy, holdout'u
**bir kez ve set düzeyinde** aç (yanlış geçme ≤ %5), asıl hüküm paper'da.

**Dürüstlük notu:** v2 de sonuçlar görüldükten sonra tasarlandı. Geliştirme dönemindeki v2 sayıları iyimser olacaktır;
ağırlık holdout + paper'a verilmeli. v2 "son tasarım" olarak dondurulmalı: sıfır çıkarsa cevap sıfırdır.

---

## 1. Strateji havuzu değerlendirmesi

### 1.1 Havuzda ne var?

460 tek-grafik strateji (swing 190, daytrade 168, scalp 102) + 19 portföy sınıfı. Kaynak: 355 dış (TradingView /
freqtrade / GitHub), 100 kitap kartı, 5 önceki proje. Kaba mekanizma dağılımı (isimden anahtar kelimeyle; yaklaşık):

| Mekanizma | daytrade | scalp | swing | toplam |
|---|---|---|---|---|
| trend / hareketli ortalama / momentum göstergesi | 52 | 34 | 68 | 154 |
| ortalamaya dönüş / osilatör / dip alımı | 34 | 31 | 39 | 104 |
| kırılım | 14 | 5 | 10 | 29 |
| formasyon / mum / seviye | 11 | 4 | 12 | 27 |
| takvim / mevsimsellik | 4 | 0 | 8 | 12 |
| hacim | 2 | 2 | 1 | 5 |
| funding / carry | 1 | 0 | 1 | 2 |
| sınıflanamayan / karma | 50 | 26 | 51 | 127 |

Sonuç tablosu (geliştirme dönemi, WF):

| Grup | satır | WF geçen | PF>1 oranı | medyan Sharpe | kill switch'e çarpan |
|---|---|---|---|---|---|
| swing 1d | 189 | 26 | %70 | 0.46 | swing toplam %64 |
| swing 4h | 189 | 6 | %62 | 0.20 | |
| daytrade 30m/1h | 336 | 1 | %14–30 | −0.4 | %96 |
| scalp 5m/15m | 204 | 5 | %10–16 | −0.5 / −0.8 | %94 |
| portföy 1d | 19 | 1 | %63 | 0.52 | 0 |

Kaynağa göre: dış stratejiler swing'de 282 satırdan 28 geçen; kitap stratejileri 90 satırdan 2; daytrade/scalp'ta kitap
stratejilerinden geçen yok. Yani "kitaplarda yaygın olan" ölçütü (karar 1) bu testte bir avantaj göstermedi.

### 1.2 Çeşitlilik: kâğıt üstünde var, sonuçta yok

- **Yön:** geçen 38'in 32'sinde hiç kısa işlem yok; kısa işlemi olan 6'sında kısa PF 0.04–0.98. Havuz genelinde kısa
  tarafı kârlı swing stratejisi %3 (≥ 30 kısa işlemi olanlarda). Set kurulursa her zaman "risk iştahı açık" yönünde
  net long olacak; ayı piyasasında koruyan parça yok.
- **Rejim:** geçen 38'in yıllık toplam R ortalaması: 2020 +25, 2021 +21, **2022 −4**, 2023 +17, 2024 +23, 2025 +9.
  Evrenin eşit ağırlıklı al-tut getirisi aynı yıllarda +%98, +%205, −%37, +%76, +%77, +%32. Swing geçenlerin kazancı
  evrenin yükseldiği aylarda yıllık ~%19 hızında, düştüğü aylarda ~%2 (medyan). 13/38 düşen aylarda ortalamada zararda.
- **Varlık sınıfı:** swing geçenlerde kârın medyan %55'i kriptodan. Scalp geçen 5'inde kârın %94–99'u kriptodan; "en az
  iki sınıfta net > 0" kuralını hissede kuruş kadar kârla geçiyorlar (kural büyüklüğe bakmıyor).
- **Birbirine benzerlik:** geçen 32 swing stratejisinin "yayılmış" günlük korelasyonu ortalama 0.17, aylıkta 0.30,
  çeyreklikte 0.41 (496 çiftin 201'i > 0.5). Kısa vadede farklı günlerde işlem yapıyorlar ama aynı büyük dalgaya
  biniyorlar. Günlük ≤ 0.5 süzgeci bunu göremiyor (496 çiftten yalnız 6'sını yakalıyor).
- **Olumlu taraf:** geçenler tek bir göstergenin kopyaları değil (haftalık getiride 0.5 eşiğiyle 24 strateji 21 kümeye
  ayrılıyor); mekanizma olarak trend 15, dönüş/dip 11, karma 8, takvim 2. Yani "aynı strateji 20 kez" durumu yok; sorun
  ortak piyasa yönü.

### 1.3 Gereksiz tekrar (deneme sayısını şişiren)

- **Stil klonları:** 33 kitap mekanizması 2–3 stilde birebir aynı kuralla duruyor (80 strateji). Aynı fikir üç ayrı
  "deneme" sayılıyor.
- **Zaman dilimi ikizleri:** her swing stratejisi hem 4h hem 1d koşuyor (1d–4h OOS Sharpe sıra korelasyonu 0.58).
  1d'de geçen 26'nın yalnız 3'ü 4h'te de geçiyor; ama 4h PF medyanı 1.42 — yani "ikinci deneme" çoğunlukla aynı
  bilginin gürültülü tekrarı.
- **Parametre ızgarası:** strateji başına ~24 ayar × 35 enstrüman. Yukarıdaki bulgu (madde 0.3) ızgaranın seçime değer
  katmadığını gösteriyor.
- **freqtrade "dip alımı" ailesi:** ewo-ema-ofset, bb-alt-bant-osilator, cluc, binhv45, cofibit, e0v1en,
  aroon-stochrsi-ema-dip aynı fikrin türevleri (scalp'ta geçen 5'in hepsi bu aileden; kendi aralarında iki kümeye
  düşüyorlar). Scalp 5m havuzunun tamamında etkin bağımsız seri sayısı ~4 (102 stratejiden).
- **Etkin bağımsız deneme sayısı (özdeğer yöntemi, haftalık getiri):** swing 1d 182 → ~65; swing 4h 189 → ~50;
  daytrade ~11–15; scalp 15m ~9, 5m ~4. Kabaca 900 satır ≈ 150 bağımsız deneme.

### 1.4 Maliyet duyarlılığı

- Scalp/daytrade'in sorunu seçim değil, aritmetik: gidiş-dönüş maliyet ~14–26 bps (komisyon 2×5 + kayma), 5m–30m'de
  tipik işlem getirisi bununla aynı büyüklükte. 540 satırdan 6 geçen; %94–96'sı %20 kill switch'e çarpıyor.
- Scalp'ta geçen 5 strateji "rastgele girişe" karşı çok güçlü görünüyor (z = 9–25) ve 1 mum gecikmeyle PF'leri
  **artıyor** (ör. ewo 5m: 1.63 → 1.82). Bu ya gerçek bir kısa vadeli dönüş etkisi ya da dolum varsayımı kaynaklı bir
  yapay sonuçtur; paper'a alınmadan önce **dolum gerçekçiliği denetimi** şart (giriş fiyatı, mum içi stop/hedef sırası).
- **TradFi funding sıfır varsayılıyor.** Hisse/emtia perp'lerinde 10–40 gün long tutan swing stratejileri için bu,
  getiriyi yukarı çeken bir eksik. Kriptoda funding gerçek seriden işleniyor (doğru).
- Swing'de maliyet ×2/×3 testlerini WF geçenlerin tamamı geçiyor: swing maliyete duyarlı değil; test burada bilgi
  üretmiyor.

### 1.5 Budanacaklar ve eklenecekler

**Buda (kod silinmez; resmi test ailesinden çıkar):**
1. Stil klonları: her mekanizma yalnız doğal stilinde (≈ −50 strateji).
2. Zaman dilimi ikizi: swing'de birincil tf **1d** (kaynak açıkça 4h diyorsa 4h); diğer tf deneme değil, sağlamlık
   kontrolü (≈ satır sayısı yarıya iner).
3. Parametre ızgarası: birincil test **varsayılan ayar**; ızgara yalnız "komşu ayar" kontrolünde.
4. Scalp ve daytrade "geniş havuz" olarak kapatılır. Kalan tek ciddi iz — kripto gün içi dip alımı — **tek bir önceden
   tanımlı hipotez** olarak, açıkça "yalnız kripto" evreninde ve dolum denetiminden sonra test edilir. (Şimdiki
   "üç sınıfta evren stratejisi" tanımını zaten sözde geçiyorlar.)
5. Yakın kopyalar: aynı mekanizma etiketi ya da haftalık getiri korelasyonu ≥ 0.7 olanlar tek küme; temsilci
   **performansa göre değil**, en az parametreli olan (eşitlikte alfabetik) seçilir.

Tahmini aile büyüklüğü: 939 satır → ~250–300 hipotez.

**Ekle (az ama farklı yönden):**
1. **Kısa/koruma tarafı.** Bugün yok. Adaylar: sınıf içi kesitsel long-short (momentum ve kısa vadeli dönüş), kısa
   açabilen yavaş zaman-serisi momentumu (1–12 ay), ve bir **rejim bindirmesi** (evren trendi bozulunca tüm setin
   riskini azaltan tek kural; strateji değil, set düzeyinde bir kez test edilir).
2. **Yavaş trend (aylık ölçek).** Havuzdaki trend stratejileri kısa periyotlu gösterge çeşitlemeleri. Portföy
   tarafındaki `pf__trend_sepet` (Sharpe 1.13, düşüş %22) ve 7 benzeri yalnız "%20 düşüş" eşiğinden kalıyor; bu bir
   boyutlama sorunu (bkz. 2.2).
3. **Funding sinyali (kripto).** Havuzda 2 strateji var. Aşırı funding'de karşı yön / funding süzgeci 3–5 varyant.
4. **Takvim (az sayıda).** Ay dönümü geçti; benzeri 2–3 iyi belgelenmiş etki. Gecelik hisse etkisi önerilmez: günlük
   gidiş-dönüş maliyet (~16 bps) etkiden büyük.

Eklemeler de aynı ön kayıtlı hatta, aynı aile sayımına dahil edilerek test edilir; "eklenen her fikir bir denemedir".

---

## 2. Seçim mantığı — aşama aşama

### 2.1 Walk-forward tasarımı

- **Sağlam:** eğitim/test ayrımı, işlemlerin pencereye göre ayrılması, pencere sınırı çakışma süzgeci, tek kasa
  oynatması. Kabul/ret sırasında sınıf yanlılığı yok (ret oranları kripto/hisse/emtia için %59–62, ölçüldü).
- **Zayıf:** ayar, eğitim penceresinde **en yüksek PF** ile seçiliyor (asgari 30/60 işlem, 35 enstrüman toplamında).
  PF küçük örnekte çok oynak; "en yüksek"i seçmek şanslı ayarı seçmektir. Kanıt: geçenlerde 11 pencerede medyan 5
  farklı ayar seçilmiş, en sık seçilen ayarın payı %36; ve seçim rastgele sabit ayardan anlamlı iyi değil (0.3).
- **Sonuç:** WF burada "ayar öğrenme" değil, yalnız "örneklem dışı görünüm" üretiyor. Varsayılan ayarla tüm dönem
  zaten örneklem dışıdır (uydurulan bir şey yok) ve 2017–2019 da kullanılabilir hale gelir (2018 kripto ayısı dahil →
  daha çok rejim).
- Uyarı: dış stratejilerin varsayılanları yazarlarınca 2020–2024 verisinde ayarlanmış olabilir; bu yanlılık her iki
  tasarımda da var, yalnız holdout/paper çözer.

### 2.2 Eşikler (ON_KAYIT ölçüt 1–2)

Her kapının tek başına etkisi (902 tek-grafik satır; "yalnız bu kapıdan kalan" = diğer hepsini geçip bundan kalan):

| Kapı | geçen | yalnız bundan kalan | Yorum |
|---|---|---|---|
| net > 0 | 341 | 0 | diğerleri kapsıyor |
| PF ≥ 1.2 | 220 | 2 | boğa döneminde swing için "medyan" seviye |
| ≥ 100 işlem | 758 | 0 | sorun değil |
| **en iyi %5 hariç PF ≥ 0.9** | 84 | **40** | hattın fiilî ana kapısı; trend takibini yapısal olarak cezalandırır |
| Sharpe ≥ 0.5 | 190 | 2 | PF ile büyük ölçüde aynı bilgi |
| düşüş ≤ %20 | 477 | 8 | boyutlamaya bağlı; kill switch (%20) ile aynı sayı |
| kârlı enstrüman ≥ %50 | 282 | 0 | etkisiz |
| tek enstrüman ≤ %40 | 134 | 9 | yararlı |
| kârlı sınıf ≥ 2 | 304 | 2 | büyüklüğe bakmadığı için kolay geçiliyor |

Değerlendirme:
- **"En iyi %5 hariç PF"** iyi niyetli (kâr birkaç işlemde yoğunlaşmasın) ama yanlış alet: az kazanıp büyük kazanan
  stratejiler (trend takibi) doğası gereği kalır, sık kazanıp az kazanan (dip alımı) geçer. Geçen listesinin long dip
  alımı / geri çekilme ağırlıklı olmasının bir nedeni bu. Yoğunlaşma riskini K3 (bootstrap) ve "en iyi enstrüman / en
  iyi yıl çıkarılınca hâlâ kârlı mı" sorusu çarpıklıktan bağımsız ölçer.
- **Düşüş ≤ %20** bir "avantaj" ölçüsü değil, **boyut** ölçüsü. Portföy stillerinde 17 stratejinin 8'i yalnız düşüş
  %22–40 olduğu için kalıyor (Sharpe'ları 0.5–1.1; 7'sinde düşüş %22–25). Risk bütçesi ~0.8 ile çarpılsa bu 7'si geçerdi. Ayrıca düşüş ve Sharpe
  **gerçekleşmiş** özsermayeden hesaplanıyor (açık pozisyonun dalgalanması yok) → gerçek düşüş daha büyük.
- **Kill switch olayı "bilgi" sayılıyor**; ama kasa %20'de durunca sonraki yıllar yok. Örnek: `dis__oncekigun-kirilim
  30m` 2022'de durmuş, 2023–2025'te hiç işlemi yok, yine de "WF geçti". Kill olayı olan satırın metrikleri yarım
  döneme aittir; kapı olmalı.
- **Genişlik:** "≥ 2 sınıfta net > 0" yerine büyüklük şartı gerekir (aşağıda).

### 2.3 PBO

Her grupta 0.00–0.03 (portföy 0.31). Bu "aşırı uyum yok" demek değil: matriste maliyetle batan binlerce ayar var;
eğitimde en iyi olan ayar testte "medyanın üstünde" olmayı neredeyse otomatik başarıyor. PBO bu havuzda ayırt edici
değil; kapı olarak hiçbir şey yapmıyor. Yalnız rapor kalsın ya da tamamen çıksın.

### 2.4 K1–K4

WF'yi geçen 38 tek-grafik stratejide: K1 ×2 → 38/38, K1b ×3 → 38/38, K1c gecikme → 38/38, K4 komşu → 37/38,
K3 → 35/38 (yalnız 1'i tek başına), **K2 → 25/38 (10'u yalnız K2'den kalıyor)**.

- **K2 (rastgele giriş) hattın tek gerçek ayırt edicisi** ve doğru soruyu soruyor: "aynı enstrümanda, aynı yönde, aynı
  çıkış kurallarıyla rastgele girseydim ne olurdu?" Swing adaylarında rastgele giriş, gerçek kazancın medyan **%46**'sını
  zaten veriyor (58 adayın 41'inde rastgele giriş kârlı). Yani swing "avantajının" yarısı yön + çıkış kuralı + piyasa.
  K2 aynı zamanda evren seçimi yanlılığına (bugünün kazananları) karşı bağışık: karşılaştırma aynı enstrümanlarda.
  Eksikleri: 500 tekrar → en küçük p = 0.002, çoklu test düzeltmesine çözünürlük yetmiyor; yalnız adaylara koşuluyor ve
  düzeltmesiz %5 eşiği kullanılıyor.
- **K1 ×2 ve ×3** aynı şeyi iki kez soruyor; swing'de bilgi üretmiyor. Biri yeter.
- **K4** fiilen ikili (58 adayın 52'sinde oran 1.00, 5'inde 0.00): "komşuların %60'ında PF > 1" eşiği çok gevşek.
- **K3** PF ile yüksek bağlantılı (0.66); sıfıra karşı test — yön yanlılığını ayıklamaz.

### 2.5 K5 (DSR) — neden bozuk, doğrusu ne

Bilinen üç kusura (V maliyetle batan ayarlarla şişiyor; V limitsiz matristen, sınanan seri limitli kasadan; N ayar
sayıyor) bir dördüncüsü eklenmeli: **DSR sıfır getiriye karşı test eder**; bu evrende sıfır yanlış kıyas (madde 1.2).

Aynı (görülmüş) veride, doğru birimle (strateji×tf, WF-OOS günlük serisi) yapılan gösterge hesaplar:

| Yöntem | Neye karşı | Kalan |
|---|---|---|
| ON_KAYIT K5 (DSR, grup N/V) | sıfır | 0 / 58 |
| Romano-Wolf adım-aşağı (aile hatası %10; blok bootstrap) | sıfır | 2 (one-mr1 4h, heracles 1d) |
| Benjamini-Hochberg (yanlış keşif %10; NW t) | sıfır | ~6 (508 canlı seri; 939 sayılırsa daha az) |
| aynı, %20 | sıfır | ~22 |
| K2 z-skoru + Bonferroni (939) | rastgele giriş | ~12 (normal yaklaşım; kesin değil) |

Okuma: (a) K5 gerçekten geçilemez kurulmuştu; (b) düzeltilince "hepsi geçer" olmuyor; (c) havuzda sıfırdan farklı bir
şey var (t > 2 olan 41 seri, şansla beklenen ~12), ama bunun ne kadarının yön etkisi olduğu ancak rastgele-giriş
kıyasıyla ayrılır.

### 2.6 Skor, korelasyon süzgeci, stil başına sınır

- **Skor = Sharpe × (1 − K2 p):** p zaten ≤ 0.05 olduğu için çarpan 0.95–1.00; skor fiilen Sharpe. 5.4 yıllık veride
  Sharpe'ın standart hatası ~0.45: listedeki 1. (1.8) ile 15. (1.0) arasındaki fark ~1.5 standart hata. "En iyi 3"ü
  Sharpe'a göre almak büyük ölçüde şans sıralamasıdır ("kazananın laneti"). Projenin kendi kanıtı da bunu söylüyor:
  Katman 4'te WF PF'si ile kilitli dönem PF'si arasındaki sıra korelasyonu −0.09 idi.
- **Korelasyon ≤ 0.5 (günlük, işlem süresine yayılmış R):** gerçek ortak hareketi ölçmüyor (1.2). Haftalık/aylık ve
  piyasa değeriyle işaretlenmiş seride ölçülmeli.
- **Stil başına ≤ 3:** makul ve kullanıcı kararı; "zorlama yok" kuralı doğru. Öneri: 3'ü Sharpe'a göre değil, **farklı
  kümelerden** seç.

### 2.7 Holdout tasarımı

- Mühür ve "bir kez" disiplini iyi. Sorun kapıda: **net > 0 ve PF ≥ 1.1**.
- Geliştirme işlemlerinden simülasyon (avantajı sıfırlanmış R dağılımı, yıllık işlem sayısı kadar çekim): bir strateji
  bu kapıyı **%39** ihtimalle şansla geçer; avantajı yarıya inmiş gerçek bir strateji %64, tam avantajlı %85 geçer.
  Yani geçmek, "gerçek" ile "şans" arasında yalnız ~1.6 kat ayırt ediyor. 3 / 6 / 9 aday götürülürse en az bir yanlış
  "doğrulandı" ihtimali %78 / %95 / %99. (İşlemler aynı piyasa dalgasına bağlı olduğu için gerçek oran daha da kötü.)
- **Evren ileriyi görüyor:** hisse/kripto listesi 2026-11-07 piyasa değerine göre sabit; bu holdout'un son günü.
  Holdout boyunca yükselip eşiği aşanlar listede. Long ağırlıklı her şey lehine çalışır. Kıyas "aynı enstrümanda
  rastgele giriş" olursa bu yanlılık büyük ölçüde düşer.
- **Kısmi görülmüşlük:** 2025-11-01 sonrası dönem Katman 4'te 7 strateji (+14'lük liste, +son 1 ay adayları) için bir
  kez açıldı. Evren hattı bu veriyi görmedi; ama o stratejiler holdout'ta "görülmüş" sayılıp işaretlenmeli.

### 2.8 Paper kapısı

≥ 8 hafta + set beklenti aralığında + ≥ 30 işlem. Bu, "backtest ile çelişmiyor" testidir, "avantaj var" testi değil:
8 haftada swing stratejisi başına ~8 işlem olur; aralık çok geniştir. Paper'ın asıl kanıtlayabileceği şey **uygulama
sadakati**dir (paper işlemleri = aynı dönemin backtest işlemleri mi; gerçekleşen kayma modele uyuyor mu). Öneri: paper'ı
iki amaçla tanımla — (1) sadakat (kısa sürede ölçülür), (2) performans (ancak uzun sürede; ≥ 12 hafta ve set toplamında
≥ 60 işlem, ardışık izleme).

### 2.9 Eksik olanlar

- **Rejim bağımlılığı** için kapı yok (yalnız bilgi sütunları). 
- **Yön/beta kıyası** yalnız K2'de ve yalnız adaylarda.
- **Kapasite/likidite:** 10.000 USD'lik kasa ve bu enstrümanlarla sorun değil; canlıda büyürse HYPE/ZEC/doğalgaz için
  yeniden bakılır. Öncelik düşük.
- **Devir/maliyet payı:** ayrı kapıya gerek yok; "maliyet ×2'de kârlı" bunu kapsar. Eksik olan TradFi funding.
- **Set düzeyi test:** her şey strateji bazında; oysa işleme girecek olan settir.

### 2.10 Çift sayımlar (özet)

PF ≥ 1.2 ↔ Sharpe ≥ 0.5 ↔ net > 0 ↔ K3; K1 ×2 ↔ K1b ×3; "en iyi %5 hariç" ↔ K3 ↔ tek enstrüman payı; düşüş ≤ %20 ↔
kill switch; PBO ↔ DSR (aynı matris). 16 kapının fiilen çalışanı 4: "%5 hariç PF", tek enstrüman payı, düşüş, K2.

---

## 3. Önerilen hat: v2

İlke: **az kapı, her kapı tek bir soruya cevap, tek bir resmi istatistik testi, her sayı koşudan önce yazılı.**

### 3.0 Koşudan önce ön kayda yazılacaklar (hepsi tek dosya + sha256 + commit)

1. Havuz dosyası: her satır = strateji, birincil tf, **varsayılan ayar**, mekanizma etiketi, küme no, beyan edilen evren
   (genel / yalnız kripto). Satır sayısı = **m** (aile büyüklüğü).
2. Geliştirme döneminde kullanılacak m: **max(v2 satır sayısı, 939)** — çünkü 939 satır bu veride zaten denendi;
   budama sonuç görüldükten sonra yapıldığı için indirim alınmaz. (Yeni eklenen her strateji m'yi artırır.)
3. Evren, maliyet tablosu (+ TradFi funding varsayımı), sert limitler (değişmez), tohumlar, tekrar sayıları.
4. Aşağıdaki bütün eşikler ve sıralama/eşitlik kuralları.
5. Holdout planı (3.6) ve paper planı (3.7), "ikinci deneme yok" hükmü.
6. Beyan: "v2 sonuç görüldükten sonra tasarlandı; geliştirme sonuçları kanıt değil eleme aracıdır."
7. v1 kurallarıyla sonuç (0 strateji) resmi kayıt olarak kalır; v2 raporu ikisini yan yana gösterir.

### 3.1 Aşama 0 — Havuzu dondur
Madde 1.5'teki budama + eklemeler. Kümeleme kuralı sabit: mekanizma etiketi aynı **veya** geliştirme dönemi haftalık
getiri korelasyonu ≥ 0.7 → aynı küme (ortalama bağlantı). Temsilci: en az serbest parametreli; eşitse alfabetik.
(Kümeleme performansa bakmaz; yalnız benzerliğe bakar.)

### 3.2 Aşama 1 — Ham koşu (varsayılan ayar)
Her satır, evrenin tüm enstrümanlarında, tüm geliştirme döneminde (2017 → 2025-11-07), maliyet ×1 ve ×2. Çıktıya her
işlemin **günlük piyasa-değeri yolu** eklenir (Sharpe, düşüş, korelasyon bunlardan). WF ayar seçimi yok.

### 3.3 Aşama 2 — Eleme (5 kapı; çıkarım değil, süzgeç)
Tek kasa, sert limitlerle oynatma üzerinden:

| # | Kapı | Tanım |
|---|---|---|
| E1 | Kârlılık | maliyet **×2**'de net > 0 **ve** maliyet ×1'de PF(R) ≥ 1.2 |
| E2 | Örnek | ≥ 200 kabul edilmiş işlem ve ≥ 10 enstrümanda işlem |
| E3 | Yoğunlaşma | en kârlı **enstrüman** çıkarılınca toplam R > 0 **ve** en kârlı **takvim yılı** çıkarılınca toplam R > 0 |
| E4 | Genişlik | "genel" beyanlı ise: en az 2 varlık sınıfının her biri toplam R'nin ≥ %15'i. "Yalnız kripto" beyanlı ise bu kapı yok, strateji yalnız kriptoda koşar |
| E5 | Hayatta kalma | oynatmada kill switch olayı **yok** |

Kaldırılanlar: Sharpe ≥ 0.5, düşüş ≤ %20 (set boyutlamasına taşındı), "en iyi %5 hariç PF", kârlı enstrüman oranı,
tek enstrüman ≤ %40 (E3 kapsıyor), K1b ×3, K3, PBO, DSR (son üçü yalnız rapor).

### 3.4 Aşama 3 — Resmi test (tek çoklu-test adımı)
- **İstatistik:** K2 rastgele giriş (mevcut `evren_k2` mantığı: aynı enstrüman, yön, tutma süresi, **stratejinin çıkış
  kuralları**, aynı takvim çeyreği içinden rastgele giriş). Sınama büyüklüğü: toplam R.
- **p-değeri:** p = (1 + #{sim ≥ gerçek}) / (B + 1). Uyarlamalı tekrar: önce B = 500; p ≤ 0.02 olanlara B = 10.000.
- **Aile:** m (3.0-2). Elemeyi (3.3) geçemeyen ya da K2 koşulmayan her satırın p'si **1** sayılır. (Bu, elemeden sonra
  test etmenin yarattığı seçilim yanlılığını kapatır; ispatı ekte.)
- **Karar:** Benjamini-Hochberg, **q = 0.10**. Geçenler "keşif".
- **Havuz geneli tek sayı (rapor):** Hansen SPA p-değeri (sıfıra karşı, m seri). p > 0.10 ise raporun başına yazılır:
  "havuzun bütününde sıfırdan farklılık kanıtı yok".

Neden bu seçim (kısaca; ayrıntı ekte):
- DSR, V ve N gibi iki elle belirlenen girdi ister ve sıfıra karşı test eder → burada yanlış kıyas, kırılgan.
- White/Hansen/Romano-Wolf "en iyisi gerçekten iyi mi?" sorusuna (aile hatası) cevap verir; 5–8 yıllık veride gücü
  düşük ve yine sıfıra karşı. Amaç tek şampiyon değil, küçük riskli birkaç stratejiden set kurmak; burada doğru hedef
  **yanlış keşif oranı**dır (10 keşiften ~1'i yanlış olabilir; holdout + eşit risk bunu seyreltir).
- Rastgele-giriş p-değeri dağılım varsayımı istemez, yön/evren yanlılığını kendiliğinden ayıklar, zaten kodlu.
- Korelasyon kümeleriyle "etkin N" hesaplamak mümkün ama eşik seçimi yeni bir çatallanma yaratır; BH bağımlılık altında
  da geçerliliğini büyük ölçüde korur (şüphede BY düzeltmesi rapor edilir) ve küme kuralı gerektirmez.

### 3.5 Aşama 4 — Sağlamlık (4 ikili kontrol; yalnız keşiflere)

| # | Kontrol | Geçme şartı |
|---|---|---|
| S1 | Gecikme | sinyal 1 mum gecikmeli, maliyet ×1: PF ≥ 1.0 |
| S2 | Komşu ayar | mevcut ızgaradaki komşuların **medyan** PF'si ≥ 1.1 **ve** en kötüsü ≥ 0.9 |
| S3 | Komşu zaman dilimi | swing: diğer tf'de (4h↔1d) PF ≥ 1.0; diğer stiller: yok |
| S4 | Ayı rejimi | "ayı günleri" (evren eşit ağırlıklı endeksi 200 günlük ortalamasının altında) toplam R ≥ −0.20 × tüm dönem toplam R |

Hepsini geçen = **"sağlam keşif"**. Birini kaçıran = "izleme listesi" (sete girmez).

### 3.6 Aşama 5 — Set kurma
1. Sağlam keşifler, haftalık piyasa-değeri getirisi korelasyonuyla kümelenir (ortalama bağlantı, eşik 0.5) + 3.1'deki
   mekanizma kümesi (ikisinden biri aynıysa aynı küme).
2. Stil başına ≤ 3; küme başına 1. Sıra: K2 p-değeri küçük olan; eşitlikte maliyet ×2 PF'si yüksek olan.
   (Sharpe'a göre sıralama yok.)
3. Ağırlık: **eşit risk** (her strateji işlem başı aynı risk payı; sert limitler aynen).
4. Boyut: setin geliştirme dönemi blok-bootstrap düşüşünün %95'liği ≤ %15 olacak şekilde **yalnız aşağı** ölçek
   (işlem başı risk ≤ %1; yukarı ölçek yok). Düşüş kapısının yerini bu alır.
5. Sağlam keşif yoksa o stil boş kalır; hiçbiri yoksa sonuç "0".

### 3.7 Aşama 6 — Holdout (bir kez, set düzeyinde)
Set, ayarlar ve boyut mühürlenir; sonra 2025-11-08 → veri sonu tek koşu.
- **Set kapısı:** set net > 0 **ve** havuzlanmış rastgele-giriş testi (setin tüm holdout işlemlerinin toplam R'si,
  B = 5.000) **p ≤ 0.05**.
- **Strateji notu (kapı değil, budama):** strateji net ≤ 0 **veya** kendi K2 p > 0.25 ise setten çıkar; yerine yenisi
  alınmaz.
- Set kapısı kalırsa: bu set paper'a gitmez; holdout'a bakarak değişiklik yapılmaz; kayıt düşülür.
- Yanlış geçme: genel "avantaj yok" durumunda ≤ %5 (bugünkü kapıda strateji başına ~%39). Güç: geliştirmedeki etkinin
  yarısı sürerse kabaca %60–65 (bugünkü kapıyla benzer güç, sekizde bir yanlış alarm).
- Katman 4'te kilitli dönemde görülmüş stratejiler raporda işaretlenir.

### 3.8 Aşama 7 — Paper (iki ayrı karar)
1. **Sadakat (ilk 4 hafta):** paper işlemleri ↔ aynı dönemin backtest işlemleri eşleşmesi ≥ %95; gerçekleşen
   kayma + komisyon ≤ modelin ×1.5'i; sert limit ihlali yok. Kalırsa durdur, düzelt, sıfırdan başlat.
2. **Performans:** ≥ 12 hafta **ve** set toplamında ≥ 60 kapanmış işlem; set özsermayesi başlangıçta sabitlenen koninin
   %5–%95 bandında; band altına iniş = duraklat + inceleme (önceden yazılı).
3. Canlıya geçiş: her zaman kullanıcı onayı; küçük bütçe; büyütme kuralı önceden yazılı.

### 3.9 Yeniden tasarımın dürüstçe doğrulanması
- Geliştirme verisi kirli (v1 sonuçları görüldü; v2 kuralları bu sonuçları bilerek yazıldı). v2'nin geliştirme
  çıktıları yalnız "kim holdout'a gider" kararıdır.
- **Temiz kalanlar:** (a) evren hattının hiç açmadığı holdout (12 ay) — tek atış; (b) **kardeş evren**: geliştirme
  döneminde, evrende olmayan enstrümanlar (kural önceden yazılır, ör. evrende olmayan S&P 100 hisselerinden alfabetik
  ilk 20 + piyasa değeri sırası 16–30 kripto + Dukascopy'de olan 4 endeks/6 döviz çifti). Zamanca bağımsız değil ama
  "yalnız bu 35 enstrümana uymuş" stratejiyi yakalar; rapor amaçlı, kapı değil; (c) ileri veri = paper.
- **D seçeneği ile ilişki:** holdout yalnız bir kez harcanabilir. Ya v1'in 24'üne (D) ya v2'nin setine. Öneri: v2'ye
  sakla. İkiye bölmek (6'şar ay) gücü ciddi düşürür; önerilmez.
- **Tek tur kuralı:** v2 dondurulduktan sonra üçüncü tasarım yok. Yeni fikirler ancak yeni veriyle (ileri dönem) ve
  yeni ön kayıtla.

---

## 4. Dürüst değerlendirme: ne mümkün, neye mal olur, ne kalır

**Ne beklenebilir?** Görülmüş veride göstergeler v2'nin 5–12 "keşif", sağlamlık ve küme süzgecinden sonra **3–8
stratejilik** bir set üreteceğini düşündürüyor (çoğu swing 1d, long, kripto ağırlıklı; belki 1–2 kripto gün içi dip
alımı). Bu bir tahmindir; 0 çıkması da olasıdır ve geçerli bir sonuçtur. Setin holdout'u geçme ihtimalini dürüstçe
%50 civarında görüyorum.

**"Teoride mükemmele yakın" ne demek, ne demek değil?** Hat, yanlış stratejiyi içeri alma ihtimalini kontrol edebilir;
havuzda olmayan avantajı yaratamaz. Havuz herkese açık gösterge stratejilerinden oluşuyor; bunların maliyet sonrası
gerçek avantaj oranı düşüktür. En iyi ihtimalle elde edilecek şey: riskli varlıklarda yön getirisini daha düşük
düşüşle toplayan, ayı piyasasında az kaybeden küçük bir set. Bu değerli olabilir, ama "piyasadan bağımsız kazanç" değil.

**Hesap süresi (bu konteyner, 4 süreç):**

| İş | Süre (duvar saati) |
|---|---|
| Ham koşu, varsayılan ayar, ~300 satır × 35 enstrüman × 2 maliyet | ~2–4 saat (bugünkü 35 saatin ~1/10'u) |
| Eleme + oynatma | dakikalar |
| K2: ~60 aday × 500 + ~30 × 10.000 (swing ~1 dk/500 tekrar) | ~3–4 saat |
| K2 kripto gün içi adayları (≈ 20 dk/500 tekrar; 5 aday × 5.000) | ~4–8 saat |
| Sağlamlık (komşu ayar/tf zaten ham dosyalarda) | < 1 saat |
| Kardeş evren verisi (saatlik Dukascopy dosyaları) + koşu | ~yarım gün |
| **Toplam** | **~1–1.5 gün** hesap; kodlama + test + denetim 4–6 iş günü |

**Kalan en büyük riskler:**
1. **Rejim:** set net long. 2022 benzeri bir yılda kaybeder; S4 ve rejim bindirmesi azaltır, yok etmez.
2. **Holdout tek yıl:** o yılın yönü sonucu etkiler; rastgele-giriş kıyası bunu azaltır ama örnek küçük.
3. **Evren yanlılığı:** bugünün kazananları. K2 kıyası çıkarımı korur, getiri beklentisini korumaz (beklenti aralıkları
   iyimser kalır). Paper'da günlük üyelik kuralı gerçek durumu gösterecek.
4. **Uygulama:** TradFi perp funding'i, 7/24 perp ↔ seanslı araştırma verisi farkı, gün içi dolum varsayımları.
5. **Kirlenme:** v2'nin kendisi görülmüş sonuçlardan esinli; tek panzehir holdout + paper ve "tek tur" kuralı.
6. **Düşük güç:** gerçek ama küçük avantajlı stratejiler de elenir. Bu bilinçli tercih: yanlış alarmı düşük tutmanın
   bedeli.

---

## 5. Öncelikli iş listesi

**P0 — karar ve dondurma (hesaptan önce)**

| # | İş | Efor |
|---|---|---|
| P0-1 | Karar: holdout v2 setine mi saklanacak (öneri), D ile mi harcanacak | kullanıcı + lider, 1 görüşme |
| P0-2 | v2 ön kayıt metni (3.0–3.9) — eşikler, m, tohumlar, "tek tur" hükmü | 0.5 gün |
| P0-3 | Havuz dondurma dosyası: klon/ikiz budama, mekanizma etiketi, küme, varsayılan ayar, evren beyanı | 1 gün (Haiku ayıklar, lider denetler) |
| P0-4 | Kill switch olayı = eleme (E5); "WF geçti ama kasa durmuş" satırların işaretlenmesi | 0.25 gün |
| P0-5 | Gün içi dolum denetimi (scalp geçen 5 strateji: giriş fiyatı, mum içi sıra, gecikmede PF artışı) | 0.5–1 gün |

**P1 — v2'nin çekirdeği**

| # | İş | Efor |
|---|---|---|
| P1-1 | Ham koşuya "varsayılan ayar" modu + işlem başına günlük piyasa-değeri yolu | 1 gün |
| P1-2 | Eleme kapıları E1–E5 (mevcut `olcutleri_degerlendir` yanına, eskisi korunarak) | 0.5 gün |
| P1-3 | K2: uyarlamalı tekrar (500 → 10.000), tüm aile için p = 1 kuralı, BH/BY, SPA raporu | 1 gün |
| P1-4 | Sağlamlık S1–S4 (S2/S3 mevcut ham dosyalardan; S4 için rejim serisi) | 0.5–1 gün |
| P1-5 | Set kurma: haftalık piyasa-değeri korelasyonu, küme başına 1, eşit risk, aşağı ölçek | 0.5 gün |
| P1-6 | Holdout modülü: set düzeyi havuzlanmış rastgele-giriş testi; mühür aynen | 0.5 gün |
| P1-7 | TradFi funding varsayımı maliyet tablosuna (tutucu sabit oran) | 0.25 gün + karar |

**P2 — genişletme ve izleme**

| # | İş | Efor |
|---|---|---|
| P2-1 | Yeni adaylar: kesitsel long-short, yavaş TSMOM (kısa açabilen), funding sinyali, rejim bindirmesi | 2–3 gün |
| P2-2 | Kardeş evren verisi + rapor | 1 gün |
| P2-3 | Paper kabulünün ikiye ayrılması (sadakat / performans) ve panoya yansıması | 1 gün |
| P2-4 | Portföy stillerinin düşüş eşiği yerine set boyutlamasıyla yeniden değerlendirilmesi (v2 kuralıyla) | 0.5 gün |
| P2-5 | Evren üyeliğinin tarihsel yaklaşık kuralı (ileriyi görmeyi azaltmak için) | 1–2 gün, veri bulunursa |

---

## Appendix (English, for the team lead)

### A. Evidence computed in this review (development period only; all contaminated, diagnostic use)

Sources: `wf_evren.parquet` (939 rows), `saglamlik.csv` (58), `pbo.csv`, `oos/*.parquet` (902), `ham/*.parquet`
(swing 1d only), pre-lock 1d candles via `tf_mumlari(..., kilit_ac=False)` (cut at 2025-11-01).

1. **Direction.** Of 38 WF passers: 32 have zero shorts; the other 6 have short PF 0.04–0.98. Pool-wide share with
   PF_short > 1 (n_short ≥ 30): swing 3%, daytrade 15%, scalp 9%; PF_long > 1: swing 85%.
2. **Regime.** Passers' yearly sum-R mean: 25.4 / 20.5 / −3.7 / 16.6 / 23.1 / 8.6 (2020–25); 27/38 negative in 2022.
   EW universe buy-and-hold (survivorship-biased membership): Sharpe 1.69; yearly +98/+205/−37/+76/+77/+32%.
   Monthly regression on EW universe: median corr 0.26, beta 0.09 (realised-PnL series, lumpy → understated);
   conditional means: swing median annualised +18.7% in up-months vs +2.0% in down-months; 13/38 ≤ 0 in down-months.
3. **Correlation.** Project's "yay" series among 32 swing passers: mean pairwise corr 0.17 daily / 0.23 weekly / 0.30
   monthly / 0.41 quarterly; pairs > 0.5: 6 / 20 / 71 / 201 of 496. Realised-at-exit series: 0.02 daily. The ≤ 0.5
   daily filter is nearly inert.
4. **Effective N** (participation ratio of correlation eigenvalues, weekly realised PnL): swing 1d 65 of 182; swing 4h
   50 of 189; daytrade 1h 15 / 30m 11; scalp 15m 9 / 5m 4. Among the 24 K5-only failures: 21 clusters at corr > 0.5.
5. **Grid value.** Swing 1d, 182 strategies, raw trades in OOS span: WF-stitched PF vs per-setting PF over the same
   span: mean percentile of WF 0.57; median(WF − median fixed) = +0.037 PF; median(WF − "varsayilan") = +0.022.
   Median fixed-setting PF ≥ 1.2 for 96/182 strategies. Passers: median 5 distinct settings over 11 windows, modal
   share 0.36.
6. **Gate marginals.** See table in 2.2. "PF ex top-5% ≥ 0.9" is the sole failure for 40 rows; K1/K1b/K1c/K4 have
   zero marginal rejections among WF passers; K2 has 10; K4 `par_oran` ∈ {0, 1} for 57/58.
7. **Kill switch.** Fires in 96% (daytrade), 94% (scalp), 64% (swing) of rows; 99% of rows with DD > 20% have a kill
   event, so the DD gate ≈ kill indicator. `dis__oncekigun-kirilim 30m` passes WF with `kill_olayi=1`,
   `red_kill=1641`, no trades after 2022.
8. **K2.** Random-entry mean R is positive for 41/58 candidates; median(random mean R / actual R) = 0.46. z =
   (actual − mean)/sd ranges −1.0 … 24.7; ~12 of the 24 have z ≥ 3.9 (Bonferroni-939 at 5% under a normal tail
   approximation — indicative only; needs B ≫ 500).
9. **Family tests on WF-OOS daily realised PnL** (2020-04-17 … 2025-09-12; 508 of 902 series have non-zero variance
   in span — the rest were killed earlier): studentised step-down max-T (stationary bootstrap, mean block 20, B=2000),
   zero benchmark: max t = 4.34; adjusted p ≤ 0.05: 1; ≤ 0.10: 2; ≤ 0.20: 3. BH on Newey-West(20) one-sided p:
   q=0.05 → 2, q=0.10 → 6, q=0.20 → 22; BY → 2. t > 2: 41 (null expectation 11.6); Storey π0 ≈ 0.85.
10. **Holdout gate operating characteristics** (block bootstrap of each of the 24 strategies' dev OOS R, block 10,
    n = trades/year, 4000 draws): P(net > 0 ∧ PF ≥ 1.1) = 0.39 under mean-zero R; 0.64 at half the dev mean; 0.85 at
    full. Independence across strategies assumed (optimistic).
11. **Acceptance ordering.** Replay tie-break is universe order (crypto first) but acceptance rates by class are
    0.61 / 0.59 / 0.62 for swing passers; PF of rejected trades (2.29) ≈ accepted (2.08). No bias found.

### B. Specific defects / mis-specifications

- `kasa_metrikleri`: Sharpe and max DD use realised equity (`gunluk_ozs = nakit`), while kill/daily-limit use a
  conservative MTM (losses only, linear path). DD is understated for long holds; Sharpe is not comparable across
  holding periods. v2 needs a true per-trade daily MTM path (from candles) for Sharpe, DD, correlation.
- `secim.gunluk_getiri('yay')` spreads R linearly over the holding period: removes market co-movement → correlation
  filter and `kumeler` understate dependence.
- `pbo_matrisi` / `grup_dsr_parametreleri`: full-period per-setting columns without account limits, including
  cost-dominated settings (scalp 15m median Sharpe −5.9) → V inflated, PBO ≈ 0 by construction. Unit of selection in
  the pipeline is the strategy line (one stitched OOS series), not the setting.
- DSR null is SR = 0; the realistic null here has positive drift for long-only rules on a survivorship-selected
  universe. Any zero-benchmark test (DSR, RC, SPA, RW) conflates edge with exposure.
- Universe membership frozen at 2026-11-07 caps: look-ahead for the whole dev period and, more importantly, for the
  holdout (membership determined at the holdout's end).
- TradFi funding = 0 (`funding: yok`) while live venue is perps; long multi-week holds are flattered.
- Score `Sharpe × (1 − p)` is monotone in Sharpe for all practical p; top-k by Sharpe with SE ≈ 0.45 is noise ranking.
- "Near" list thresholds (PF 1.1, Sharpe 0.4, DD 25%, p 0.10, DSR 0.5) double the forking paths; v2 has no "near" tier.
- Scalp universe was widened after seeing 0/204 (recorded); the five scalp passers are crypto-only in substance.

### C. v2 formal definitions

- **Family.** H_i, i = 1..m, one per (strategy, primary tf) line at default parameters. m_dev = max(|pool_v2|, 939).
- **Screen** E1–E5 as in 3.3, evaluated on the single-account replay with SERT_LIMITLER unchanged.
- **Randomisation p-value.** For line i passing the screen: T_i = Σ R over trades (post per-symbol overlap filter,
  pre-replay, as today). Null draws: for each trade keep (symbol, direction, stop/ATR multiple, strategy exit rules);
  draw entry bar uniformly within the same calendar quarter and symbol; B draws → p_i = (1 + #{T*_b ≥ T_i})/(B+1).
  Adaptive B: 500, then 10,000 if p ≤ 0.02 (fixed two-stage rule; report the final-stage p only, computed on the
  10,000 fresh draws to keep validity).
  Lines failing the screen or without a supported exit module: p_i := 1.
- **Validity of screen-then-test.** For a true null i, p'_i = p_i·1{pass} + 1·1{fail}; P(p'_i ≤ u) = P(p_i ≤ u, pass)
  ≤ P(p_i ≤ u) ≤ u, so p'_i is super-uniform regardless of dependence between screen and statistic. BH at level q over
  m hypotheses controls FDR under PRDS; report BY (q / Σ_{k≤m} 1/k) alongside as the arbitrary-dependence bound.
- **Why randomisation + BH rather than DSR / RC / SPA / RW / cluster-N_eff.**
  DSR: needs (N, V) — both arbitrary here — and a zero null. RC/SPA/RW: correct handling of dependence and of
  data-snooping over the family, no N/V knobs, but (i) zero or user-chosen benchmark, (ii) FWER target gives little
  power with ~5–8 years and ~300–900 lines (indicatively 2 survivors), (iii) answers "is the best one real", whereas
  the deliverable is a diversified small-risk set for which FDR is the appropriate error rate. Cluster-based N_eff:
  requires a linkage threshold and series definition (new forking paths; N_eff ranged 4–65 per group depending on
  horizon in A.4). The randomisation test is exact for its null, is conditional on realised exposure (hence immune to
  drift and to universe survivorship in the inference), and is already implemented (`evren_k2.py`).
  SPA on the m stitched series vs zero is kept as a single global diagnostic.
- **Limitations of the K2 null.** It tests entry timing given direction/instrument/exit rules; a strategy whose value
  is direction choice (long vs short) or instrument choice is not credited — acceptable for this pool (near-universal
  long-only, no instrument selection by design). It preserves the calendar quarter, so slow regime filters are
  credited as timing skill (intended). Statistic is pre-replay ΣR; profitability under limits is enforced by E1.
- **Robustness** S1–S4 as in 3.5. Bear regime: EW index of the frozen universe (daily, equal weight of available
  members), bear day ⇔ index < its own 200-day SMA at prior close (no lookahead).
- **Set construction.** Distance 1 − ρ on weekly MTM returns, average linkage, cut at 0.5, union with mechanism
  labels; per style ≤ 3, ≤ 1 per cluster; order by p_i then PF at ×2 cost; equal per-trade risk; global down-scale
  s ∈ (0, 1] chosen so that the 95th percentile of block-bootstrap (block 20 d, 2000 draws) max DD of the set ≤ 15%.
- **Holdout.** One run of the sealed set. Set statistic T_set = Σ_i Σ R (holdout entries only); null: joint random
  entry per strategy as above within holdout quarters, B = 5,000; gate: set net > 0 (single-account replay, costs ×1)
  and p_set ≤ 0.05. Per-strategy pruning: net ≤ 0 or p_i > 0.25 → dropped, no replacement. No second attempt.
  Size under the global null ≤ 0.05 (times P(net > 0)); rough power at half the dev effect ≈ 0.6 (pooled z ≈ 2).
- **Pre-registration checklist.** Pool file hash; m; universe and declared sub-universes; cost table hash incl. TradFi
  funding assumption; all thresholds in 3.3–3.8; seeds; B values; linkage rule; bear-regime definition; holdout and
  paper rules; list of strategies previously exposed to the 2025-11-01+ lock test; statement of contamination;
  commitment that the v1 official result (0) stands and that no v3 will be evaluated on these data.

### D. Things that are sound and should not be redesigned

Sealing/one-shot holdout mechanics (`liste_muhru.json`, v3 hash scope); period-bounded readers (`_veri` hard cut);
single-account replay with hard limits and explicit rejection counters; per-symbol cost table with hash pinning;
failure accounting (errors make a row "hata" instead of silently passing); trial registry; K2 with the strategy's own
exit rules; "no forcing" when a style has no survivor; explicit logging of post-result changes.
