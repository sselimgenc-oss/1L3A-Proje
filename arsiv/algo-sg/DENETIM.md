# Denetim Raporu — Bug, Mükerrerlik, Çelişki ve PDF Uygunluğu

Bu rapor ilk sürüm stratejileri (A, B, C) inceler: kod satır satır okundu, şüpheli her nokta veriyle ölçüldü, her kural PDF'lerdeki kaynağıyla karşılaştırıldı.

**Kabul kuralı:** bir değişiklik iki durumdan birinde kabul edildi:
- mantıksal bir hatayı düzeltiyorsa, ya da
- PDF'lere dayanıyorsa **ve** ana evren (IS + OOS) ile hiç görülmemiş stres evreninin (20 eski/delist edilmiş coin) ikisinde de iyileştiriyorsa.

Sonuç tablolarındaki kısaltmalar: WR = kazanma oranı, PF = kâr faktörü (toplam kâr / toplam zarar), MAR = yıllık getiri / en büyük düşüş, R = işlem başına riske edilen tutar.

## 1. Bulunan sorunlar ve yapılanlar

| # | Tür | Sorun | Kanıt | Karar |
|---|---|---|---|---|
| 1 | **Bug / çelişki** | A'da fiyat 4H EMA100'ün yanlış tarafındayken de kırılım girişi açılabiliyordu. Bu durumda çıkış kuralı girişte zaten doğru olduğu için işlem bir sonraki mumda kapanıyor, sadece komisyon ödeniyordu. | 458 işlem (%7.9): ortalama −0.03R, WR %41 | **Düzeltildi** (`entry_ema_side`). IS PF 1.39→1.41, OOS 1.48→1.49 |
| 2 | **Bug (maliyet)** | Kısmi kâr alındıktan sonra da funding tam pozisyon üzerinden hesaplanıyordu. | Kod incelemesi + birim testi | **Düzeltildi** (`backtest.py`: funding × kalan pozisyon) |
| 3 | **Belge–kod çelişkisi** | B'nin eşiği `ret24=0.15` logaritmik getiriydi; gerçek düşüş %13.9 olmasına rağmen raporda "%15" yazıyordu. | log(1−0.139) = −0.15 | **Düzeltildi**: basit yüzde `drop24=0.15` |
| 4 | **Tutarsızlık + aşırı uyum** | B'nin "BTC çökmüyorsa" filtresi BTC'yi gecikmeli 4H kapanışla, coin'i ise 1H kapanışla ölçüyordu. Doğru hesapla (1H) PF 1.96'dan 1.35'e düştü; komşu ayarlar da (%3/4H, %5/1H) zayıftı. Yani filtre şanslı bir parametre tepesiydi. | `results` + DENETIM §3 tablosu | **Filtre kaldırıldı.** Filtresiz B iki evrende de daha sağlam |
| 5 | **Gereksiz parametre** | B'nin 6 saatlik sinyal penceresi aynı çöküşe yeniden girişe izin veriyordu (32 işlem). Sonuç olarak pencere 1 saat ile 6 saat neredeyse aynı çıktı. | PF 1.780 / 1.786 | **Kaldırıldı** (`bias_win=1`) |
| 6 | **Anlaşılmaz kod** | B'deki `trigger="level", rsi_lo=101` "her zaman doğru" anlamına gelen bir hileydi. | Kod incelemesi | `trigger="none"` olarak açık hale getirildi |
| 7 | **MÜKERRERLİK** | C (günlük Turtle) işlemlerinin **%95'inde** (1656/1738) aynı coin'de, aynı yönde açık bir A pozisyonu zaten vardı. Açık pozisyonlar dahil günlük getiri korelasyonu 0.77'ydi. C, A'nın riskini ikiye katlıyordu. | Ayrı C kolu eklenince Sharpe 1.46→1.37 düştü; C'yi A ile birleştirince 1.49'a çıktı | **C ayrı strateji olmaktan çıkarıldı.** A'nın ikinci giriş modülü (A2) yapıldı: ortak risk bütçesi, coin başına tek pozisyon |
| 8 | **Raporlama yanılgısı** | İlk raporda düşüşler yalnızca kapanmış işlemlerden hesaplanmıştı (A için −%27). | Açık pozisyonlar dahil hesapla A −%34 | Rapor artık açık pozisyonlar dahil (MTM) düşüşü esas alıyor |
| 9 | **Ölü kod** | s1, s2, s3 ve `htf_direction` nihai sistemde kullanılmıyor. | — | Araştırmanın yeniden üretilebilmesi için tutuldu, kodda "ELENDİ" diye işaretlendi |

**Kontrol edilip sorun bulunmayanlar:**
- **Geç giriş:** sinyallerin %100'ü taze üst zaman dilimi kapanışında oluşuyor.
- **İleriye bakma (look-ahead):** 4H/1D değerleri yalnızca o mum kapandıktan sonra kullanılıyor; birim testleri bunu doğruluyor.
- **Gecikme sağlamlığı:** girişler 1–2 saat geciktirilince PF sadece hafif düşüyor (A1 1.45→1.39–1.41, A2 1.47→1.46–1.48, B 1.78→1.65–1.70).
- **Simülatör:** 8 birim testi eklendi (`tests/test_backtest.py`). Doğrulanan kurallar: girişin sonraki açılıştan yapılması, aynı mumda önce stop varsayılması, gap'te açılıştan çıkış, kısmi kâr + başabaş, short simetrisi, maliyet + funding, funding'in kalan pozisyona göre hesaplanması, çıkış sinyali, kayıp sonrası bekleme.

## 2. PDF uygunluk denetimi

| Kural | Kaynak (metinler/) | Uygunluk | Not |
|---|---|---|---|
| Bir gösterge trendi/yönü doğrular, diğeri girişi verir | Ratford s.6–7; Kılınçarslan tez PDF s.141 ("önce geniş, sonra orta vadede ve son olarak kısa") | ✅ | 1D/4H yön + 1H giriş |
| Donchian kırılımı ile girmek | Pruitt Box 3.1–3.3 (Turtle 20/55 gün, Donchian) | ✅ | A1: 4H 20 mum, A2: 1D 20 gün |
| Stop = 2N (N = ATR) | Pruitt / Turtle | ✅ | A1: 2 × ATR(4H) |
| Kırılımlar büyük mumlarda kârlı, küçük mumlarda sahte | Davey Bölüm 4 | ✅ | 1H kırılım (s2) test edildi ve elendi; A 4H/1D'de |
| Hacim trendi onaylamalı | Kılınçarslan tez PDF s.23 (Dow ilkesi: "Hacim, piyasa eğilimini onaylamalıdır"); Tsinaslanidis (hacim onayının eksikliği bir sınırlama) | ✅ | A1: 4H hacim ≥ 1.5 × ortalama |
| Rejim filtresi kârı artırır, düşüşü azaltır | Davey Bölüm 7 | ✅ | A'da long için BTC günlük > EMA200 |
| Başabaş stop neredeyse stop & reverse kadar iyi | Davey Bölüm 8 | ✅ | A ve B'de 1R'de başabaş |
| Turtle çıkışı: ters yöndeki N/2 kanal | Pruitt Box 3.1 | ⚠️ **Bilinçli sapma** | Test edildi: 4H 10 mum çıkışında PF 1.45→1.29; 20 mum çıkışı ana evrende karışık, stres evreninde PF 1.35→1.27. EMA100 + geniş iz süren stop korundu |
| Turtle LTLF (son işlem kazandıysa sonraki sinyali atla) | Pruitt s.79 | ❌ Reddedildi | OOS'ta iyileştirdi, IS'te kötüleştirdi, düşüşü −%28'den −%35'e çıkardı |
| Kayıp sonrası bekleme (Risk Koruma #2) | Davey Bölüm 6 | ❌ Reddedildi | A'da nötr; B'de iki evrende de kötüleştirdi (çöküşte stop sonrası yeniden giriş çoğu zaman dibi yakalıyor) |
| Yüksek volatilite anahtarı (Risk Koruma #4) | Davey Bölüm 6 | ❌ Reddedildi | Ana evrende karışık, stres evreninde PF 1.35→1.31 |
| Ortalamaya dönüş: Percent Decrease (#5) | Davey Bölüm 5 | ⚠️ **Çelişki, açıkça belirtiliyor** | B fiilen Davey'in #5 yöntemi. Davey bunu vadeli işlemlerde, günlük mumlarda, long+short **en kötü** yöntemlerden biri buldu. Bizim testimizde (kripto, sadece long, 24 saat, %15 eşik) iki evrende de en sağlam MR girişi bu çıktı. Davey'in "her şeyi kendin test et" ilkesine uyuldu |
| MA Stretch (#4, Davey'in en iyisi) | Davey Bölüm 5 | ❌ Test edildi, zayıf | d1_ema20'nin %15/20/25 altı: PF 1.12–1.25, düşüş daha büyük |
| VE (AND) kombinasyonu (#2 & #3 & #4) | Davey Bölüm 5 | ❌ Test edildi, zayıf | IS'te güçlü (PF 2.7), OOS'ta PF < 1. Az işlemli ve aşırı uyumlu |
| Zaman çıkışları MR'de kötü; MA'ya dönünce çık | Davey Bölüm 5 | ⚠️ **Bilinçli sapma** | "d1_ema20'ye dönünce çık" PF 1.19, "h4_ema20" PF 1.28; 96 saatlik zaman çıkışı PF 1.78 ile açık ara en iyi |
| Fibonacci %50–61.8 ölçülü hareket, prim/indirim | Halsey; Altın Oran; Price Action Algo | ❌ Elendi | OOS PF yaklaşık 0.85 (s3) |
| Maliyet dahil test, OOS, aşırı optimizasyondan kaçınma | Davey, Pruitt, Jansen | ✅ Güçlendirildi | Stres evreni eklendi; kırılgan filtre kaldırıldı; parametre platosu kontrol edildi |

## 3. B — BTC filtresi duyarlılığı (kaldırılma gerekçesi)

24 saatte %13.9 düşüş eşiğinde kâr faktörü (PF):

| BTC filtresi | Ana evren | Stres evreni |
|---|---|---|
| Yok | **1.68** | **1.54** |
| BTC 24 saatte %3'ten az düştüyse (1H) | 1.45 | 1.25 |
| %3'ten az (4H) | 1.42 | 1.30 |
| %5'ten az (1H) — doğru hesap | 1.35 | 1.24 |
| %5'ten az (4H) — eski sürüm | 1.94 | 1.52 |
| %8'den az (1H) | 1.63 | 1.53 |

Yalnızca eski sürümün kombinasyonu (%5/4H) parlıyor, komşularının hepsi zayıf. Bu, aşırı uyumun tipik bir belirtisi.

## 4. Önce / sonra

| | Eski | Yeni |
|---|---|---|
| Strateji sayısı | 3 (C, A'nın kopyasıydı) | **2 bağımsız strateji** (A: A1+A2 kırılım, B: kapitülasyon) |
| A işlem bazında, ana evren (WR / PF) | %50.4 / 1.43 | %50.1 / **1.61** |
| A, stres evreni (WR / PF) | %49.0 / 1.35 | %48.6 / **1.40** |
| B işlem bazında, ana evren (WR / PF) | %63.1 / 1.94 (kırılgan) | %64.0 / 1.78 (sağlam) |
| B, stres evreni (WR / PF) | %55.9 / 1.56 | %60.2 / **1.65** |
| Kombine, açık pozisyonlar dahil düşüş (ana / stres) | −%14.9 / — | −%15.2 / −%12.7 |
| A–B günlük korelasyonu | −0.12 | **−0.27** |
