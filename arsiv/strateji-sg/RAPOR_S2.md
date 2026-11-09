# Strateji 2 — KGT'yi Tamamlayan İkinci Strateji: KMN (Kesitsel Momentum, Piyasa Nötr)

> **Faz 9 denetim notu:** Bu rapordaki sayılar dengelemeler arasında sabit ağırlık varsayımıyla hesaplandı. Gerçekçi
> hesap, yani adetlerin sabit kalıp ağırlıkların kaydığı canlı uygulama, daha iyi sonuç veriyor: yıllık %55,2, düşüş %18,1,
> Sharpe 1,86. KGT ile %50/%50 birleşimde yıllık %45,7, düşüş %15,6, Sharpe 1,99. "180/365 gün geçmiş" satırları
> seçilen risk skoruyla değil, birikimli getiri skoruyla hesaplanmıştı. Doğru sayılar (kaymalı, risk skoru): 180 gün →
> Sharpe 1,51, 365 gün → 1,15. Yürüyen pencere testi kaymalı ızgarayla Sharpe 1,16–1,54 veriyor (eski 0,60).
> Ayrıntı: `DENETIM.md`.

**Tarih:** 2026-10-09

**Kod:**
- `backtest/momentum.py`, `backtest/ortdon.py`
- Canlı: `backtest/momentum_sinyal.py`

**Sonuç dosyaları:** `sonuclar/s2/`

**Hedef:** KGT v3 kesin ana strateji. İkinci strateji KGT'nin zayıf olduğu dönemlerde (2022 düşüşü, 2025–2026 yatay piyasa) kazanmalı.

**Ölçütler:**
- KGT ile korelasyon < 0,3
- OOS PF ≥ 1,3
- KGT ile birleşimde düşüş azalırken getiri korunmalı

**Adaylar:**
- Ortalamaya dönüş
- Piyasa nötr kesitsel momentum

Long ve short birlikte test edildi.

**Kaynaklar:**
- *151 Trading Stratejisi* §3.1 (fiyat momentumu), §3.7 (artık momentum), §3.9 / §10.3 (aykırı / kesitsel dönüş), §4.4 (IBS)
- Brooks *Trading Ranges* (aralık kuralları)
- *20 Strateji* / *51 Strateji* Bollinger-RSI sistemleri

## 1. Ortalamaya dönüş — BAŞARISIZ

| Test | Kombinasyon | Medyan Sharpe | Sharpe > 0,5 | Not |
|---|---|---|---|---|
| 4S Bollinger / RSI(2), ADX aralık filtresi, günlük trend içi, onay mumu, ortalamaya çıkış | 256 | −1,10 | 0 | Kazanma %50–55, PF 0,75–0,8 |
| Aynısı günlük mumlarda | 256 | −0,31 | 0 | PF 0,73–0,88 |
| Kesitsel kısa vadeli dönüş (geçen haftanın kaybedenini al) | 16 | −0,99 | 0 | |
| IBS dönüşü (151 §4.4), günlük | 1 | −2,07 | — | Yıllık −%49 |

**Neden başarısız:**
- Kriptoda tek coin üzerinde "aşırı düşeni al" yaklaşımı masraf ve stoplardan sonra zarar ediyor.
- Brooks'un uyarısı doğrulanıyor: yatay aralıklar kısa, kırılımlar sert. Kripto ortalamaya dönen değil, trend yapan bir piyasa.

## 2. Kesitsel momentum

**Kural:**
- Her H günde bir, o ayın hacim sıralamasında ilk N coin (en az 90 günlük geçmiş) bir skora göre sıralanır.
- En yüksek K coin long, en düşük K coin short.
- Her taraf sermayenin %50'si: brüt 1,0, net ≈ 0, kaldıraçsız.
- Masraf taraf başına %0,07, fonlama dahil (long öder, short alır).
- Sonuç, H farklı dengeleme gününün ortalamasıdır; şans etkisini azaltmak için.

| Varyant | Medyan Sharpe | KGT ile korelasyon |
|---|---|---|
| Long-only (en güçlü K) | 0,68 | 0,53, KGT'ye benziyor ❌ |
| Piyasa nötr, birikimli getiri skoru | 0,77 | 0,16 |
| **Piyasa nötr, riske göre düzeltilmiş skor (ort / σ, 151 §3.1)** | **1,26** (432 ayarın %78'i > 1) | **0,17** |
| Piyasa nötr, BTC'ye göre artık skor (151 §3.7) | 1,09 | 0,21 |

**Parametre bölgesi (risk skoru):**
- **Dönem L:** 10–14 gün en iyi (Sharpe 1,43–1,53). 7 ve 21 gün de iyi (1,24–1,30). 45 gün zayıf (0,88).
- **Dengeleme:** 14 günde bir, 7 günden iyi.
- **Ağırlık:** ters oynaklık, eşit ağırlıktan daha düşük düşüş veriyor.
- **Evren ve pozisyon sayısı:** 30 coin en iyisi, K 4–5.

### Seçilen ayar: KMN
- **Evren ve skor:** ilk 30 coin, son 14 günlük günlük getirilerin ortalaması / σ.
- **Pozisyonlar:** en iyi 5 long, en kötü 5 short.
- **Ağırlık ve dengeleme:** 30 günlük oynaklığın tersiyle ağırlık, 14 günde bir dengeleme.

| | Yıllık | Maks. düşüş | Sharpe | Calmar | Kârlı ay | Pozisyon kazanma |
|---|---|---|---|---|---|---|
| **KMN, 2020–2026/09** | **%43,5** | **%16,3** | **1,69** | 2,67 | %65 | %51 (long %45, short %57) |
| IS 2020–2023 | | | 1,56 | | | |
| OOS 2024–2026/09 | %49,0 | | 1,88 | | | |

**Yıllık getiri (%):**

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (9 ay) |
|---|---|---|---|---|---|---|
| +48 | +113 | **+18** | +2 | +39 | **+57** | +37 |

KMN, KGT'nin zayıf olduğu yıllarda kazanıyor: 2022'de +%18 (KGT −%20), 2025'te +%57 (KGT +%14).

### Sağlamlık

| Test | Sonuç |
|---|---|
| Maliyet ×2 / ×3 | Sharpe 1,57 / 1,44 (yıllık %39 / %35) |
| İşlem 1 gün / 2 gün geç yapılırsa | Sharpe 1,61 / 1,54 |
| 14 farklı dengeleme gününün her biri ayrı | Sharpe min 0,88, medyan 1,27, maks 1,77 |
| Rastgele long/short seçimi (aynı evren ve ağırlık, 30 simülasyon) | Rastgele medyan Sharpe −0,43, p95 0,43; gerçek %100 daha iyi |
| Yeni coinler hariç (≥ 180 / 365 gün geçmiş, birikimli skor) | Sharpe 1,17 / 0,74; kârın bir kısmı genç coinlerin short tarafından |
| Yalnız long / yalnız short bacak | 0,94 / 0,02. Kâr iki bacağın farkından geliyor; tek bacak işe yaramaz |
| Yıllık devir | Özsermayenin ~42 katı, yıllık masraf ~%2,9 (sonuçlara dahil) |
| **Yürüyen pencere** (her yıl, yalnız geçmiş veriyle 864 ayardan en iyisi seçildi) | **Yıllık %13,6, Sharpe 0,60.** İlk yıllarda yanlış ayarlar seçildi (2021: L=45). 2024'ten sonra +%20, +%23, +%44 |

**Dürüst değerlendirme:**
- Seçilen ayarın Sharpe'ı (1,69), ızgaranın medyanının (1,26) üstünde. Bir kısmı seçim şansı olabilir.
- Yürüyen pencere sonucu gerçek parayla beklentinin daha düşük olması gerektiğini söylüyor. **Gerçekçi beklenti: Sharpe 1,0–1,3, yıllık %20–35.**
- Tek dengeleme günüyle çalışmak sonucu şansa bağlar (Sharpe 0,88–1,77). Bu yüzden canlıda **sermaye ikiye bölünüp iki alt portföy 7 gün arayla dengelenmeli.**

## 3. KGT v3 + KMN birleşimi
Sermaye bölünüyor. KGT kendi payında işlem başına %0,4 riskle, KMN kendi payında brüt 1,0 ile çalışıyor.

| Ağırlık | Yıllık | Maks. düşüş | Sharpe | Calmar | OOS Sharpe | 2022 | 2025 |
|---|---|---|---|---|---|---|---|
| KGT %100 | %32,9 | %30,6 | 1,26 | 1,08 | 1,31 | −20 | +14 |
| KGT %70 + KMN %30 | %37,3 | %18,2 | 1,69 | 2,05 | 1,89 | −9 | +26 |
| **KGT %50 + KMN %50** | **%39,7** | **%15,0** | **1,90** | **2,64** | **2,14** | **−2** | **+35** |
| KGT %40 + KMN %60 | %40,7 | %13,8 | 1,94 | 2,94 | 2,16 | +2 | +40 |
| KMN %100 | %43,5 | %16,3 | 1,69 | 2,67 | 1,88 | +18 | +57 |

**Öneri: KGT %50 + KMN %50.**
- Yıllık getiri KGT'den yüksek: %40'a karşı %33.
- Düşüş yarıdan az: %15'e karşı %31.
- Her yıl kârlı ya da başa baş.
- KMN'nin gerçekte daha zayıf çıkma ihtimaline karşı ağırlığı %50'de tutmak, %60'tan daha güvenli.

## 4. Kullanım
```bash
python3 -m backtest.momentum_sinyal --sermaye 5000     # KMN hedef portföyü (sermayenin KMN payı / 2 alt portföy)
python3 -m backtest.kripto_sinyal --sermaye 5000       # KGT (her saat)
```

**KMN uygulaması:**
- KMN payı ikiye bölünür. Birinci yarı her 14 günde bir dengelenir, ikinci yarı ondan 7 gün sonra.
- Dengeleme günü 00:00 UTC'den hemen sonra betik çalıştırılır. Hedef tutarlarla mevcut pozisyonlar arasındaki fark Binance USDT-M vadelide alınır/satılır.
- Short pozisyonlar vadeli işlemde açılır; kaldıraç kullanılmaz, toplam brüt pozisyon kendi sermayesine eşit.
- Canlı betik, backtest ağırlıklarıyla 25/25 dengeleme gününde birebir aynı.

**Riskler:**
- Short tarafında ani yükselen (squeeze) coinler.
- Momentum çöküşleri (151 kitabı Daniel ve Moskowitz 2016'yı anar). Örneğin piyasa dibinden sert dönüşte zayıf coinlerin hızla toparlanması.
- Genç coinlerde likidite.
- 2–3 ay kâğıt üzerinde ileri test önerilir.
