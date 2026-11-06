# Derin Denetim Raporu — KGT v3 ve KMN (Faz 9, 2026-10-09)

**Kapsam:**
- **KGT v3:** `strateji.py`, `kripto_strateji.py`, `gostergeler.py`, `kripto_motor.py`, `kripto_final.py`, `kripto_sinyal.py`, `kripto_evren.py`
- **KMN:** `momentum.py`, `momentum_sinyal.py`
- **PDF uygunluğu:** 51 Strateji, 151 Strateji, Brooks

**Yöntem:**
- Üç bağımsız denetim (KGT kodu, KMN kodu, PDF uygunluğu).
- Her bulgu sentetik testlerle ya da tam veriyle doğrulandı.
- Düzeltmelerden sonra tüm sonuçlar yeniden üretildi.

## 1. Özet
- **Sonucu şişiren bir hata bulunmadı.** Kontrol edilenler: geleceğe bakma (look-ahead), hayatta kalma yanlılığı (borsadan çıkan coinler dahil), ay başı evren seçimi, fonlama işareti, masraf, özsermaye muhasebesi, topluluk ortalaması.
  - KMN için ayrıca bir "1 gün erken bakma" testi yapıldı. Ağırlıklar bir gün önce kullanılınca Sharpe 2,92'ye fırlıyor. Asıl hesap bu kadar yüksek çıkmadığı için tarihlerin doğru hizalandığı kanıtlanıyor.
- **Düzeltilenler:** 11 hata/tutarsızlık, 5 belge çelişkisi. Ayrıntılar aşağıda.
- **En büyük belirsizlik ölçülerek kapatıldı:** KGT'de aynı saatlik mumda "1R kısmi kâr → başabaş stop" sırası. 501 belirsiz mum Binance 1 dakikalık verisiyle tek tek çözüldü; yalnız 51'inde başabaş gerçekten vurulmuştu. Kötümser varsayımın verdiği Sharpe 0,94 gerçek dışı çıktı, gerçek Sharpe 1,28.
- **KMN backtest'i stratejiyi olduğundan kötü gösteriyordu.** Ağırlıklar dengelemeler arasında sabit tutuluyordu; canlıda ise adetler sabit kalır. Gerçekçi hesapla Sharpe 1,69'dan 1,86'ya çıktı.

## 2. Bulgular ve düzeltmeler

### KGT v3
| # | Bulgu | Önem | Etki | Düzeltme |
|---|---|---|---|---|
| 1 | Aynı mumda 1R kısmi kârdan sonra çekilen başabaş stopu o mumda kontrol edilmiyordu (`kripto_motor.py`) | Büyük (belirsizlik) | Kötümser varsayımda Sharpe 1,28 → 0,94; 1 dk veriyle gerçek etki ≈ 0 | `ici_sira` seçeneği: 1 = OHLC yolu (varsayılan), 2 = kötümser, 3 = 1 dakikalık veriyle çözülmüş (`be_1dk.pkl`, nihai sonuçlar) |
| 2 | Üst zaman dilimi (4S/1G) değerleri 1 mum geç kullanılıyordu; canlı betik zamanında kullanıyordu → backtest ile canlı arasında 1 saat fark (`gostergeler.htf_hizala`) | Orta | Çıkışlar 1 saat erkene geldi; sonuç biraz iyileşti | HTF mumu, kapanışı alt mumun kapanışına denk geldiği mumda kullanılıyor; hâlâ geleceğe bakmıyor (birim testli) |
| 3 | Geçici veri boşluğunda (2022-02-26/28, 2022-04-01/02, ~30 coin) pozisyon "veri sonu" diye bayat fiyattan kapatılıyordu | Orta | Alt portföy başına +0,6…+5,3R yapay sonuç | Motor, coinin son geçerli verisinden önceki boşlukta pozisyonu korur, veri gelince yönetir; yalnız gerçek delistte kapatır |
| 4 | Boşluktan sonraki gün pivot/CPR bayat fiyattan hesaplanıp yapay sinyal üretiyordu (CPR genişliği 0, stop çok dar) | Küçük | Alt portföy başına 3–4 işlem, yaklaşık −2R | Önceki günü boşluklu (≥2 boş/düz mum) olan günde ve boş mumlarda sinyal yok |
| 5 | Rastgele giriş kıyası v3'ün "kapanış > EMA20" filtresini içermiyordu; "rastgeleden iyi" iddiası şişkin | Orta | Kıyas, filtreyi de rastgeleye verince %97 (PF ve CAGR), %90 (OOS PF) | Kıyas v3 filtresiyle yeniden yapıldı |
| 6 | Short sinyalleri "günün ilk sinyali" sayımında long'u engelleyebiliyordu | Küçük | Ölçülen işlem değişimi 0 | Kripto girişi yalnız long üretiyor (`yon=1`) |
| 7 | Dönem sonunda açık kalan işlemler kayda geçmiyordu | Küçük | İstatistiklerde eksik | "açık (dönem sonu)" olarak kaydediliyor |
| 8 | İşlem kaydı tamponu (200.000 satır) taşma kontrolü yoktu | Gizli | — | Taşmada açık hata |
| 9 | `np.roll` dizi başında son değeri başa taşıyordu (Donchian, KGT'de kullanılmıyor) | Gizli | — | İlk değer NaN |

**Belge çelişkileri:**
- **Stop "S1'de" yazıyordu.** R1−S1 bir önceki günün aralığına eşit olduğundan mesafe sinyallerin %95–98'inde 3×ATR(1S) üst sınırına takılıyor. Fiilen stop = 3×ATR14(1S). Bu, çeşitli stop seçenekleri arasında en iyi Calmar'ı veren seçenek (tablo aşağıda).
- **Çıkış zamanlaması** ("bir sonraki 1S açılışında"), "00:00–20:00 UTC" penceresi (yalnız gün başı 0 için geçerli), "ilk 10 coin", "KGT v2" ve topluluğun "sermaye/6" açıklaması düzeltildi.

**Stop seçenekleri** (düzeltilmiş kodla, 6'lı topluluk, %0,4 risk):

| Stop | Kazanma | Yıllık | Düşüş | Sharpe | Calmar |
|---|---|---|---|---|---|
| **3×ATR (mevcut)** | %45,5 | %33,7 | %29,4 | **1,29** | **1,15** |
| 2×ATR | %44,2 | %37,7 | %39,3 | 1,24 | 0,96 |
| 4×ATR | %45,8 | %25,6 | %24,6 | 1,23 | 1,04 |
| 5×ATR | %45,1 | %22,9 | %23,0 | 1,19 | 1,00 |
| S1 (kırpılmamış) | %44,9 | %21,8 | %22,0 | 1,17 | 0,99 |
| Kırılım mumu dibi (51S) | %40,8 | %39,3 | %39,3 | 1,24 | 1,00 |

### KMN
| # | Bulgu | Önem | Etki | Düzeltme |
|---|---|---|---|---|
| 10 | Ağırlıklar dengelemeler arasında sabit tutuluyordu: masrafsız günlük dengeleme varsayımı. Canlıda adetler sabit kalır | Orta (kötümser yönde) | Gerçekçi hesap: yıllık %43 → %55, Sharpe 1,69 → 1,86 | `getiri_kayma` (varsayılan): ağırlık fiyatla kayar, dengelemede gerçek devir masrafı |
| 11 | Canlı betiğin evreni günlük değişen 30 günlük hacim sırası, backtest ay başında sabit sıra | Orta | Canlı tipi evrenle düşüş %16 → %26 | Canlı betik backtest ile aynı: önceki ay sonu 30 günlük hacim, ay başında ≥ 90 gün geçmiş |
| 12 | Ters oynaklık ağırlığında 1e-4 taban: bayat/düz fiyatlı coin bir tarafın çoğunu alabiliyordu (gözlenen en büyük tek ağırlık %37) | Küçük | Sonuç değişmedi | Günlük oynaklık tabanı %1 (backtest ve canlı) |
| 13 | RAPOR_S2'deki "180/365 gün geçmiş" satırları seçilen risk skoruyla değil, birikimli getiri skoruyla hesaplanmıştı | Belge | — | Doğru sayılar aşağıda |
| 14 | Docstring: "o ayın hacim sıralaması" → aslında önceki ay sonu sıralaması | Belge | — | Düzeltildi |

**Doğrulanan, sorun olmayanlar:**
- Gün kapanışı ve getiri hizalaması: karar d kapanışında, getiri d→d+1.
- Fonlama işareti: long öder, short alır.
- Delist ve boşluk etkisi: boşluk köprülenirse yıllık getiri %43,45'ten %43,23'e iniyor, etkisi yok denecek kadar küçük.
- Kötü veri (bad tick): uç getirili günlerin 1 saatlik yolları pürüzsüz, gerçek hareket.
- Canlı ağırlıklar, backtest ağırlıklarıyla 167 dengeleme gününde birebir aynı.

## 3. PDF uygunluğu

| Kural | Kitap | Kod | Durum |
|---|---|---|---|
| Pivot P, R1=2P−L, S1=2P−H, R2, S2 | 51S s.134 | `strateji.py:338` | ✅ Aynı |
| CPR: BC=(H+L)/2, TC=2P−BC | 51S s.135 (formül yok, standart tanım) | `strateji.py:339` | ✅ |
| "Dar CPR → trend günü" | 51S s.135 (sayı yok) | ≤ 0,25×günlük ATR | Sapma, gerekçeli (sayısallaştırma) |
| Yön filtresi | 51S s.136: "CPR yön göstermez" | Günlük EMA10>20 + kapanış>EMA20 (Brooks) | Sapma, gerekçeli |
| Giriş: seviye kırılımı (R1 örneği) | 51S s.142 (5 dk, mumun tepesinden) | 1S kapanışı R1 üstü, sonraki açılış | Sapma, gerekçeli (kripto 1S) |
| Stop: alış mumu / salınım dibi altı | 51S s.142 | 3×ATR(1S) | Sapma; kitaptaki mum dibi stopu test edildi, daha kötü (Calmar 1,00'e karşı 1,15) |
| Hedef: 1:2, sonraki pivot ya da "piyasa dönene kadar takip" | 51S s.142 | Trend dönene kadar (4S EMA21/50), 1R'de %15 kısmi | Kısmen uygun ("takip et" kolu); gün içi değil çok günlük |
| Short (destek kırılımı) | 51S s.146 | Yok | Sapma, test edildi: kriptoda short zarar |
| Fiyat momentumu: 12 ay formasyon, 1 ay atlama, en iyi/en kötü dilim, nötr | 151S §3.1 s.81–84 | 14 gün formasyon, atlama yok, 5/30 | **Gerçek sapma.** Kitap 1 ayı kısa vadeli dönüş için atlar. Kriptoda kısa vadede dönüş değil devam var: kısa vadeli dönüş stratejisi test edildi, Sharpe −0,99. S=1 atlaması ve L=21–30 da kârlı (sağlamlık). Ampirik gerekçeli |
| Riske göre düzeltilmiş skor (ort/σ) | 151S §3.1 | `momentum.py` skor="risk" | ✅ |
| Ağırlık (eşit / oynaklıkla sönümlü) | 151S §3.1 | 1/σ | ✅ |
| Örtüşen portföyler (Jegadeesh-Titman) | 151S §3.1 | 14 dengeleme günü ortalaması / canlıda 2 alt portföy | ✅ |

## 4. Düzeltilmiş nihai sonuçlar (2020-01 – 2026-09, masraf ve fonlama dahil)

| | Kazanma | PF | Yıllık | Maks. düşüş | Sharpe | Calmar | OOS yıllık / düşüş / Sharpe |
|---|---|---|---|---|---|---|---|
| **KGT v3** (%0,4 risk, 1 dk çözümlü) | %45,5 | 2,05 | %33,6 | %29,5 | 1,28 | 1,14 | %28,7 / %19,2 / 1,31 |
| **KMN** (kaymalı, 14 kaydırma ort.) | %51 pozisyon, %68 kârlı ay | — | %55,2 | %18,1 | 1,86 | 3,04 | %56,1 / %16,8 / 2,03 |
| KMN, 2 alt portföy (canlı düzen, 7 çift) | | | %42–64 | %19–30 (medyan 22) | 1,41–1,90 | | |
| KMN, 180 gün geçmiş (muhafazakâr) | | | %36,8 | %20,4 | 1,51 | 1,80 | |
| **KGT %50 + KMN %50** | %60 kârlı ay | | **%45,7** | **%15,6** | **1,99** | **2,94** | %43,1 / %10,3 / 2,20 |

**Yıllık getiri (%):**

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|---|
| KGT v3 | +56 | +75 | −20 | +60 | +40 | +14 | +26 |
| KMN | +51 | +215 | +18 | +2 | +52 | +71 | +30 |
| %50 + %50 | +55 | +141 | −2 | +29 | +48 | +41 | +30 |

**KMN sağlamlığı:**
- **Maliyet:** ×2'de Sharpe 1,75, ×3'te 1,63.
- **Gecikmeli işlem:** 1 gün gecikmede 1,79.
- **Uç günler:** en iyi 10 gün sıfırlanırsa 1,53; coin günlük getirisi ±%40 ile sınırlanırsa 1,81.
- **Rastgele kıyas:** gerçek strateji rastgele seçimlerin %100'ünü geçiyor (rastgele medyan Sharpe −0,30).
- **Yürüyen pencere:** her yıl yalnız geçmiş veriyle ayar seçilirse Sharpe 1,16–1,54 (eski hesapla 0,60).

**KGT sağlamlığı:**
- **Rastgele kıyas:** v3 filtresiyle rastgele girişlerin %97'sini geçiyor.
- **Monte Carlo:** 1 yılda zarar olasılığı %16, maks. düşüş medyanı %16.

## 5. Gerçekçi beklentiler ve kalan riskler
- **KGT:** yıllık %25–33, düşüş %30'a kadar. 2022 gibi ayı yıllarında −%20.
- **KMN:** yıllık %25–40, düşüş %20–25, Sharpe 1,2–1,5.
  - Backtest'in %55'lik getirisini 2021 (+%215) büyütüyor.
  - Kârın bir kısmı 90–365 gün önce listelenmiş coinlerden geliyor. Bu coinlerde gerçek kayma %0,07'den yüksek olabilir.
- **Birleşim (%50/%50):** yıllık %35–45, düşüş %15–20 beklenir.
- **Kalan riskler:**
  - Short tarafında ani yükselişler (squeeze).
  - Momentum çöküşü (piyasa dibinden sert dönüş).
  - Borsa ve likidite riskleri.
  - 2–3 ay kâğıt üzerinde ileri test önerilir.

## 6. Dosyalar
- **Kod:** `backtest/kripto_motor.py` (`ici_sira`, `SON`, `BEZ`), `gostergeler.py`, `kripto_final.py`, `kripto_strateji.py`, `momentum.py`, `momentum_sinyal.py`
- **1 dakikalık çözüm:** `sonuclar/kripto/be_1dk.pkl` (veri: `data/kripto/1m/`, 256 coin-gün)
- **Sonuçlar:** `sonuclar/kripto/ozet_v3_topluluk.csv`, `yillik_v3_topluluk.csv`, `montecarlo.csv`, `rastgele_kiyas.csv`, `sonuclar/s2/getiri_KMN.pkl`
