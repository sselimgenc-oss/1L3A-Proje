# İnceleme: gün içi noise-alanı stratejisi neden PF 0.13 çıktı?

> **Teşhis, kanıt değil. v3 sonucu değişmez** (dondurma.json, ON_KAYIT_V3.md, eleme.csv, ELEME_RAPORU.md ve `motor/` dokunulmadı).
> Tüm sayılar `python` ile gerçek veri (`veri/mumlar/DK_SPX`, 5m → 30m) üzerinde yeniden üretildi; betikler `/tmp/claude-0/noise_inceleme/` altında.

## 1. Kısa cevap

**Motorda ya da veri hazırlığında PF 0.13'ü açıklayan bir hata bulunmadı.** Aynı sinyalleri bağımsız bir döngüyle (maliyetsiz) yeniden koştum: işlem başına **+2.3 baz puan (bps) brüt kâr** çıktı (kâğıttaki "kâr var" ile uyumlu). Ama motorun maliyeti işlem başına **yaklaşık 13 bps** (komisyon 2×5 bps + kayma 2×1.5 bps). Strateji günde ~1.7 işlem açtığı için maliyet brüt kârın 5-6 katı. PF 0.13 üç şeyin birleşimi:

1. **Maliyet** brüt avantajdan çok büyük (asıl neden).
2. **Kill (−%20) hesabı 121. işlemde keser.** PF, net ve Sharpe yalnız ilk 121 işlemden hesaplandı (2017-01-23 → 2017-06-13). Sonraki 2524 işlem "reddedildi". 2017 stratejinin en kötü yılı. Tüm işlemlerle PF 0.43, ΣR −278.
3. **p = 0.0005 ile PF 0.13 çelişmez**: rastgele giriş testi tüm 2645 işlemi kill olmadan koşar ve rastgele girişler daha da kötü çıkar (ΣR −457, std 16). Yani "giriş zamanlaması rastgele değil" ama "maliyeti çıkarmaya yetmiyor".

## 2. İşlem anatomisi (ilk 121 işlem, maliyet ×1)

| Ölçü | İlk 121 | Tüm 2645 |
|---|---|---|
| Çıkış nedeni | sinyal 93, gün sonu 28 | sinyal 1847, gün sonu 790, stop 8 |
| 1 mum tutulan | %49 (59 işlem) | %43 |
| Ort. tutma (30 dk mum) | 2.8 | 3.6 |
| Brüt R / işlem | −0.067 | −0.007 |
| Maliyet R / işlem | 0.157 | 0.096 |
| Funding R / işlem | ~0 | 0.001 |
| Net R / işlem | −0.224 | −0.105 |
| Kazanma oranı | %11 | %23 |
| Long ΣR / Short ΣR | −11.2 / −15.9 | −132.7 / −142.4 |
| Brüt R long / short | −1.9 / −6.2 | −4.3 / −15.6 |

- **Maliyet / stop**: stop = 1 günlük ATR ≈ %0.65 (2017, düşük oynaklık). Komisyon 10 bps (nominalin) ⇒ 0.157 R. Yani her işlem daha açılırken stop mesafesinin ~%16'sını kaybediyor; kazanç için işlemin brüt >0.16 R yapması gerek. Bu yüzden 2017'de kazanma oranı %11.
- **Pozisyon boyutu makul**: nominal ≈ 11.9 bin $ / özsermaye ≈ 8-10 bin $ (≈1.2x kaldıraç), risk ≈ 75 $ (%0.75-1).
- **Funding**: yalnız long'a işleniyor (0.01%/8 s), toplam 3.2 R / 2645 işlem; short'ta tam 0 (kural 1.2 doğru uygulanmış).
- **Short taraf ana kaybeden mi?** Evet, ama brüt olarak (S&P yükseliş eğilimi): brüt R short −15.6, long −4.3. Net ΣR'de ikisi de ~eşit zarar, çünkü maliyet iki tarafta aynı.
- Örnek zincir (2017-01-30, short, ET): 10:00→12:00 (−0.08R), 12:00→12:30 (−0.15R), 12:30→14:30 (−0.33R), 14:30→15:00 (−0.23R), 15:00→15:30 (−0.09R), 15:30→16:00 gün sonu (−0.54R). Aynı gün 6 işlem, her biri ~0.15 R maliyet. Bant çizgisi etrafında gidip gelme ("testere"): giriş `kapanış > UB`, çıkış `kapanış < max(UB, VWAP)`; fiyat çizgiyi biraz aşıp geri dönünce 1 mumda çıkıyor, hemen tekrar giriyor (işlemlerin %13'ü bir önceki çıkışla aynı mumda giriyor). Bu kaynak makalenin kendi kuralı; hata değil, ama maliyetli.

## 3. Çıkış zamanlaması ve fiyatlar (soru 2 ve 5) — doğrulandı

- `cikis_long` giriş mumunda hemen tetiklenmiyor; en erken giriş mumunun kapanışında, sonraki açılışta çıkış (1 mum tutma). VWAP üretimi doğru: ET 09:30'dan başlıyor (gece mumları `hacim=0`), tipik fiyat ağırlıklı, her ET günü sıfırlanıyor. 2017-02-15 ve 2017-01-30 günlerinde ac, önceki kapanış, sigma, UB/LB, VWAP elle kontrol edildi, tutarlı (sigma 8-27 bps).
- **Gün sonu**: 790/790 işlem 16:00 ET'de, fiyat = 15:30 mumunun kapanışı × (1 ∓ 1.5 bps) (en büyük fark 0.005 puan). 18:00 yeniden açılışında kapanan gün-sonu işlemi yok.
- **Motor dolumları**: giriş = sonraki mum açılışı × (1 ± 1.5 bps), sinyal çıkışı = sonraki açılış ∓ 1.5 bps, stop = stop fiyatı ∓ 4 bps (8 stopun hepsi R −1.07…−1.24; gap dolumu doğru). Olumsuz-dolum ayarı 0. Sistematik "en kötü fiyattan dolum" yok.
- Kâğıttan fark: kâğıt sinyal mumunun kapanışında işlem yapar, biz bir sonraki açılışta. Fark: +2.45 bps → +2.33 bps (önemsiz).

## 4. Veri (soru 3) — temiz

- 5m → 30m kovalama UTC tabanlı; ET ile :00/:30 hizalı (UTC−4/−5 tam saat). Kış ve yaz aylarında 09:30 ET mumu hem aralık hem hacim olarak zirve yapıyor (DST kayması yok).
- 2531 seans gününün hepsinde ilk RTH mumu 09:30; 2447 günde tam 13 mum (60 günde 13:00 erken kapanış, ~20 gün diğer eksikler).
- Gece/24-5 mumları `aktif` maskesiyle `ac`, sigma, VWAP, ATR ve önceki kapanıştan dışlanıyor. Önceki kapanış = önceki günün son RTH mumunun kapanışı (doğru).
- **Küçük sorunlar (strateji kodunda)**: (a) CFD tatil günlerinde de işlem görüyor: 78 tatil günü RTH sayılıyor, sigma'nın 14 günlük penceresine giriyor, 11 işlem tatilde açılmış. (b) Erken kapanış (13:00) günlerinde gün sonu bayrağı hiç gelmiyor (bayrak yalnız 15:30 mumunda): 13 işlem 16:00'dan sonra / ertesi güne taşınmış (ΣR −2.5; biri 137 mum tutulup stop yemiş). Önem: **düşük** (işlemlerin %0.5'i; ilk 121 işlemde yok).

## 5. Rastgele-giriş testi (soru 6)

- `gercek_t` = **−278 R** (tüm 2645 işlem, kill yok), `sim_ort` = **−457 R**, `sim_std` = 16 R. p = (1+0)/(2000+1): gerçek değer bütün simülasyonlardan iyi. (CSV'de sütun sırası yanıltıcı; `satir_6.json`'da açık.)
- Rastgele işlemler: aynı yön, aynı tutma süresi (mum), aynı maliyet, aynı stop katı; giriş aynı UTC çeyreği içinde rastgele. Girişlerin yalnız %28'i 10:00-15:30 ET'e düşüyor, ama RTH'de ortalama −0.158 R, diğer saatlerde −0.179 R: saat karışımı sonucu belirlemiyor. Rastgele işlemler gerçekler gibi 16:00'da zorla kapanmıyor (gece taşıyor) ve funding yok; ikisi de farkı açıklayacak kadar büyük değil.
- Yorum: strateji rastgeleden ≈ +0.07 R/işlem iyi (~+180 R toplam, 11 sigma) — yani brüt bir sinyal var — ama ortalama net R yine negatif. V4 geçer, V1 kalır; çelişki yok. Not: p, kill sonrası kesilmiş 121 işlemi değil tüm örneği ölçüyor; iki sayı farklı işlem kümelerinden.

## 6. Bulgu listesi

| # | Konu | Nerede | Önem | Not |
|---|---|---|---|---|
| 1 | Maliyet ≈13 bps tur, brüt avantaj ≈2.3 bps. Komisyon 5 bps "tutucu, doğrulanmadı" (maliyet tablosu: Binance TradFi taker varsayımı) | Maliyet tablosu (paylaşılan) | **Yüksek** (asıl neden) | Hata değil, varsayım. Başabaş tur maliyet ≈ 2.6 bps. |
| 2 | Kill, 121. işlemde tüm örneği keser; PF/net/Sharpe 2017 H1 ile sınırlı, p tüm örnek | Eleme hattı (v3/kos.py + v2 kasa_oynat) | Orta (yorum riski) | ON_KAYIT'a uygun, ama ELEME_RAPORU'nda iki küme ayrı belirtilmemiş. Karar (elendi) değişmez: ×0.2 maliyetle bile ΣR < 0. |
| 3 | Testere/yeniden giriş: 1 mumluk işlemler %43, günde ~1.7 işlem | Strateji (kaynağın kuralı) | Orta | Hata değil, doğası. Maliyeti şişiriyor. |
| 4 | Tatil günleri sigma penceresinde; erken kapanışta gün sonu bayrağı yok | Strateji kodu | Düşük | 13 işlem, ΣR −2.5. |
| 5 | Rastgele test girişleri 24/5 saatlerine dağılıyor, funding yok | Eleme hattı (rastgele.py) | Düşük | Sonuçta fark yaratmıyor (RTH −0.158 vs −0.179 R). |
| – | Motor dolum modeli, kayma, stop-gap, gün sonu fiyatı, funding (short = 0), VWAP, saat dilimi/DST, mum hizası | – | Hata yok | Yukarıda sayılarla doğrulandı. |

## 7. Teşhis koşuları — *teşhis, kanıt değil, v3 sonucu değişmez*

Aynı dönem (2017-01-03 → 2026-10-30), aynı strateji, yalnız maliyet çarpanı değişiyor (tur maliyet ≈ 13 bps × çarpan). "Kill açık" = hattın gerçek davranışı (−%20'de durur); "kill kapalı" = tüm örnek.

| Maliyet çarpanı | Tur maliyet | Kill açık: işlem / net / PF | Kill kapalı: net / PF / Sharpe | ΣR (tüm işlem) |
|---|---|---|---|---|
| ×1.0 (hat) | 13 bps | 121 / −20.1% / 0.13 | −91% / 0.43 / −4.5 | −278 |
| ×0.5 | 6.5 bps | 214 / −20.1% / 0.37 | −65% / 0.69 / −2.0 | −113 |
| ×0.3 | 3.9 bps | 1264 / −20.0% / 0.86 | −37% / 0.86 / −0.8 | −47 |
| ×0.2 | 2.6 bps | 2645 / −12.9% / 0.96 | −12.9% / 0.96 / −0.24 | −13 |
| ×0.1 | 1.3 bps | 2645 / +20.9% / 1.08 | +20.9% / 1.08 / 0.39 | +21 |
| ×0.05 | 0.7 bps | 2645 / +43.1% / 1.14 | +43.1% / 1.14 / 0.70 | +38 |

- İşlem sayısı ×0.2'de hâlâ 2645 (kill hiç tetiklenmiyor). Başabaş ≈ 2.6 bps tur maliyet.
- Düzeltilmiş kopya (`/tmp/claude-0/noise_inceleme/duzeltilmis.py`: tatil günleri dışarıda, erken kapanışta 12:30 gün-sonu): ham işlem 2133 (2645 değil: tatil günlerinin 14 günlük pencereden çıkması bant seviyelerini kaydırıyor, işlem kümesi değişiyor). Sonuç: ×1.0 → net −20.1% (kill, 129 işlem), PF 0.15; ×0.2 → +1.8% / PF 1.01 / Sharpe 0.06; ×0.1 → +31.9% / PF 1.14 / Sharpe 0.62. Yani küçük kod düzeltmesi hikâyeyi değiştirmiyor; ayrıca sonucun işlem kümesine duyarlı, yani brüt avantajın gürültü düzeyinde olduğunu gösteriyor.
- Kıyas: makale SPY'de, işlem başı maliyet ≈ 0.1 bps, 4x'e varan kaldıraç ve oynaklık hedefli boyutlandırma ile Sharpe ≈1.3. Burada brüt avantaj makaleyle uyumlu (kaldıraçlı yıllık ~%19 brüt), ama maliyet 100 kat fazla.

## 8. v2 kâğıt stratejilerine ve canlıya etkisi (c)

- **Paylaşılan motor / dolum modeli**: DK_ semboller için hata bulunmadı (dolum, gün sonu, stop-gap, kayma, funding). v2 sonuçlarını ya da canlı motoru bozan bir motor hatası çıkmadı.
- **Maliyet tablosu (DK_*)**: komisyon 5 bps/taraf "doğrulanmadı" varsayımı. Sık işlem yapan (5m-30m, günde >1 işlem) DK_ stratejileri için karar verici. Canlı yer Binance TradFi ise gerçek komisyon/spread doğrulanmalı; çok yüksek maliyet varsayımı bu tür stratejileri sistematik eler, çok düşük olması da yanlış kabul üretir. Tutma süresi günlük+ olan v2 stratejileri bundan çok az etkilenir.
- **Kill ile kesilen satır**: aynı davranış (PF/net kill öncesi işlemlerden) başka tek-grafik satırlarda da olur; v3te kill alan satırlar: satır 3 (portföy) ve bu satır (tek grafik); satır 8 ve 9 kill almadı.
- **Tatil / erken kapanış**: tatil günlerindeki CFD mumlarının "seans" sayılması bu stratejiye özgü kodda; v2 gün içi stratejilerinin aynı kalıbı kullanıp kullanmadığı bu incelemede **kontrol edilmedi**.
