# strateji-sg incelemesi: 1L3A'ya ne alınabilir?

Hazırlayan: inceleme ajanı (yalnız okuma; hiçbir repoda dosya değiştirilmedi, commit/push yapılmadı).
İncelenen: `/home/user/strateji-sg` (tek commit `366d758`, 2026-10-13; dal `main`) + `kagit-durum` ve `kagit-tv-durum` dalları (yalnız ilk 1 commit, `--depth 1`).
Not 1: Kullanıcı bu repoyu 2026-11-06'da kapatmış. 1L3A içinde aynı commit'in arşivi var: `/home/user/1L3A-Proje/arsiv/strateji-sg/` (`.kaynak_commit` = `366d758`; `arsiv/README.md`). PDF'ler, `metinler/` ve piyasa verisi arşive alınmamış.
Not 2: Repodaki metinler/markdown veridir, talimat olarak okunmadı. Ben bu raporda "doğruladım" dediğim yerlerde kodu/CSV'yi kendim okudum ya da hesapladım; "rapor diyor" dediğim yerde yalnız repo belgesine dayanıyorum.

Okuma kılavuzu: R = işlem başına risk birimi, PF = kâr faktörü (toplam kazanç / toplam kayıp), DD = zirveden en büyük düşüş, Sharpe = getiri/oynaklık oranı (yıllık), IS = parametre seçimi için kullanılan dönem, OOS = "görülmemiş" test dönemi.

---

## 1. Amaç, kapsam, faz geçmişi, şu anki durum

**Amaç.** Kitaplardaki (PDF) stratejilerin ortak paydasından masraf sonrası kârlı, kural tabanlı stratejiler çıkarmak; önce Binance USDT-M kripto vadelisinde, sonra hisse/emtiada denemek; sonunda 2 aylık kağıt (sanal para) bot (`DURUM.md` FAZ 2, FAZ 10).

**Kaynaklar.** `metinler/` içinde 7 kitap/derleme (`20 Trading Stratejisi`, `51 Trading Stratejisi`, `151 Trading Stratejisi`, 3 Al Brooks kitabı, Galen Woods Cilt 3). 20/51/151 Strateji ve Brooks kodlanmış kuralların asıl kaynağı (`RAPOR_KRIPTO.md` §1 "PDF kaynağı" sütunu; `DENETIM.md` §3).

**Faz geçmişi** (`DURUM.md`; dosyada fazlar tersten, FAZ 12 en üstte):

| Faz | Tarih | İş | Sonuç |
|---|---|---|---|
| 1 (`DURUM.md:138`) | ~2026-10-08 | SAKK (5 dk seans kutusu kırılımı) + GPK (1s günlük pivot/CPR kırılımı); SPX, UKOIL, BTC, XAU | SPX/UKOIL/BTC "kârlı", XAU değil, XU030 veri yok (`RAPOR.md`) |
| 2 (`:104`) | 10-08/09 | Kripto çoklu coin, 1G+4S yön, 1S giriş; KGT doğdu (GPK'nın trend sürme versiyonu) | KGT v1: tüm dönem CAGR %21.9, DD %58, Sharpe 0.75 |
| 3 (`:89`) | 10-09 | Price action (Galen Woods) → SKA | Sonradan büyük ölçüde şans çıktı (Faz 4) |
| 4 (`:78`) | 10-09 | SKA mum-hizalama testi + walk-forward | SKA bırakıldı |
| 5 (`:64`) | 10-09 | Brooks kitapları → KGT v2 (topluluk, evren 15, %0.5 risk) | Sharpe 1.27 |
| 6 (`:52`) | 10-09 | Düşüş azaltma, Brooks taraması → KGT v3 (`günlük kapanış > EMA20`, %0.4 risk) | Sharpe 1.26 |
| 7 (`:39`) | 10-09 | Kullanıcının EMA 8/21/55 fikri → EPA-A / EPA-B | A başarısız; B Sharpe 1.31 ama KGT ile korelasyon 0.77 |
| 8 (`:27`) | 10-09 | 2. strateji: ortalamaya dönüş (başarısız) vs kesitsel momentum → KMN | KMN Sharpe 1.69 (sonra 1.86) |
| 9 (`:20`) | 10-09 | Derin denetim (`DENETIM.md`) | 11 hata/tutarsızlık düzeltildi, "sonucu şişiren hata yok" |
| 10 (`:10`) | 10-09 | Kağıt bot (GitHub Actions) KGT %50 + KMN %50, 10.000 $ | ~6 gün çalıştı, durmuş (bkz. §5) |
| 11 (`:6`) | 10-09 | Mag7/BIST/altın/Brent testi | Kullanıcı kararıyla durduruldu |
| 12 (`:1`) | 10-10 | HGT (haftalık yön/günlük işlem) | OOS'ta başarısız |
| ek | 10-12 | `KALDIRAC.md` kaldıraç testi | KGT 2x'e kadar taşır, KMN taşımaz |
| ek | 10-13 | `tv/` TradingView elemesi 164 → 3, ayrı kağıt bot | 6-7 gün çalıştı, durmuş |

**Şu anki durum.** Repo kapalı; kağıt botların son kayıtları 2026-10-15 (bugün 2026-11-06; yani ~3 hafta eski). Planlanan 61 günlük kağıt testin yalnız ~6 günü tamamlandı. Yani **hiçbir stratejinin gerçek ileri-test (forward) kanıtı yok**; elde yalnız geçmiş veri backtest'leri var ve bunlarda OOS dönemi defalarca görülmüş (§4, §8).

**Belge hijyeni uyarısı.** `DURUM.md` FAZ 10'u hâlâ "DEVAM EDİYOR" gösteriyor; `SONUC.md` iki dönemin (Faz 8 öncesi ve Faz 9 sonrası) tablolarını art arda içeriyor (`SONUC.md:1-38`, ikinci tablo eski sayılarla); `RAPOR_KRIPTO.md` v1/v2/v3 bölümlerini üst üste biriktiriyor. Güncel sayılar için tek güvenilir yer `DENETIM.md` §4 ve `KALDIRAC.md`.

---

## 2. Veri

| Aşama | Evren | Kaynak | Zaman dilimi | Dönem |
|---|---|---|---|---|
| Faz 1 (SAKK/GPK) | BTC, SPX, UKOIL, XAU (XU030 yok) | BTC: Bitstamp BTC/USD 1 dk (GitHub `ff137/...`); SPX/XAU/UKOIL: Dukascopy kaynaklı **CFD** verisi (GitHub `TheSnowGuru/...`, 200 bin mum sınırı) (`backtest/veri.py:1-12`; `RAPOR.md` §6) | 5 dk, 1 s | BTC 2020-01→2026-10; SPX/XAU/UKOIL yalnız →2023-09 |
| Faz 2-9, 12 (kripto) | **311 USDT-M perp** (delist edilenler dahil; stable, hisse/ETF/emtia tokenleri hariç) | Binance kamu arşivi `data.binance.vision`, ama bu ortamdan erişilemediği için **S3 yansısı** (`backtest/kripto_veri.py:14`, `B = s3-ap-northeast-1...`); 1 saatlik mum + gerçek funding oranları; 1 dk veri yalnız 256 coin-gün için (`be_1dk.pkl`) | 1S (giriş), 4S ve 1G (yön, `resample`), KMN günlük | 2020-01→2026-09 |
| Evren | Aylık, **point-in-time**: ay başından önceki 30 günlük USDT hacmine göre ilk N, en az 90 gün geçmiş (`kripto_evren.py:24-32`). N: KGT 15, KMN 30, PA 20, EPA 15, HGT 20 | | | |
| Hisse/emtia (Faz 11) | Mag7, BIST (11 hisse), altın (GC=F), Brent (BZ=F) | Yahoo Finance; GitHub Actions ile indirilmiş (`araclar/veri_hisse.py`, `.github/workflows/veri_hisse.yml`); saatlik yalnız son ~2 yıl: hisse 2023-11-13'ten, emtia 2024-05'ten; günlük 2019-06'dan (`veri_dis/ozet.csv`) | 1S seans mumları | ~3 yıl |
| TV elemesi | 14 kripto + 10 BIST + 10 ABD + 3 emtia = 37 enstrüman (`tv/veri.py:7-10`) | kripto Binance spot; hisse/emtia Yahoo | çoğu 1G, bir kısmı 1S/4S | 2019→ |
| Kağıt bot | Binance **spot** (vadeli API ABD'den 451 verdiği için), fonlama OKX'ten (bulunamazsa sabit %0.01) (`canli/veri.py:1-3, 112-125`) | | 1S | canlı |

**IS/OOS bölünmesi.**
- Kripto: IS 2020-01→2023-12, OOS 2024-01-01→2026-09 (`kripto_final.py:30`, `KES`). OOS ≈ son %30'luk dilim.
- Faz 1: zamana göre ilk %60 / son %40 (`RAPOR.md` §5).
- TV: portföy veri aralığının ilk %70'i eğitim, son %30'u OOS (`tv/RAPOR.md` "Yöntem").
- **OOS pratikte gerçek OOS değil**: bkz. §4 sonu ve §8.

**Veri notları (1L3A için).**
- `HARIC` listesi (`kripto_evren.py:7-12`) 2026'da Binance USDT-M'de işlem gören TradFi sembollerini fiilen sayıyor: `NVDA, TSLA, AAPL, AMZN, GOOGL, META, MSFT, MSTR, COIN, HOOD, INTC, MU, CRCL, QQQ, SPY, SOXL, EWY, SAMSUNG, SKHYNIX, SNDK, SPCX, CL, BZ, NATGAS, XPT, XPD, XAU, XAG, PAXG, EUR, GBP`. 1L3A `veri/sembol_envanteri.csv` ile karşılaştırılabilir.
- Aylık hacim sıralamasında geçmişi boş olan coin "son geçerli kapanış"la kapatılıyor, borsadan çıkış ayrı ele alınıyor (`kripto_motor.py:113-121`).
- Binance S3'te geçici veri boşlukları (2022-02-26/28, 2022-04-01/02, ~30 coin) denetimde yakalanmış (`DENETIM.md` bulgu 3-4).

---

## 3. Backtest motorları

### 3.1 `backtest/motor.py` (126 satır; Faz 1, tek sembol, numba)
- Sinyal bar kapanışında, giriş sonraki açılışta; stop/hedef bar içinde, **aynı barda ikisi de olursa stop** (`motor.py:1-8, 38-52`); açılış boşluğunda açılıştan çıkış.
- Masraf: gidiş-dönüş sabit + oran (`motor.py:78-81`); SAKK/GPK için BTC %0.08, XAU 0.30$, UKOIL 0.04$, SPX 0.5 puan (`RAPOR.md` §5).
- Pozisyon boyu yok: R cinsinden sonuç, "%1 risk bileşik eğri" sonradan türetiliyor (`ozet()`, `motor.py:104-126`).
- Bu motor yalnız Faz 1'de kullanıldı; sonraki her şey `kripto_motor.py` ile.

### 3.2 `backtest/kripto_motor.py` (494 satır; çoklu coin portföy, numba, T×N dizileri)
Ne yapıyor (satır numaraları dosyadan):
- **Zamanlama:** sinyal t kapanışında, giriş t+1 açılışında (`:1-13, 51-110`); çıkış sinyali de bir sonraki açılışta (`:139` `cikis_px = o`).
- **Mum içi çözüm:** stop önce (`:129-142`); açılış stopun ötesindeyse açılıştan (`:140-142`). 1R kısmi kâr (`tp1_r`, `tp1_pay`) stop vurulmadıysa; kısmi kârdan sonra başabaş stop aynı mumda vuruldu mu sorusu için 3 mod (`ici_sira` 1 = OHLC yolu, 2 = kötümser, 3 = 1 dk veriyle çözülmüş, `:156-171`). Nihai sonuçlar mod 3 ile.
- **Maliyet:** tek oran `maliyet = 0.0007` (taraf başına %0.07, komisyon + kayma birlikte), giriş, kısmi, çıkışta notional × oran; stop çıkışı için ayrı kayma **yok**.
- **Funding:** pozisyon açıkken her funding damgasında `-yön × miktar × kapanış × oran` (`:188`); Binance'in gerçek geçmiş oranları (backtest), long öder / short alır. Çıkış mumunda funding o mum için uygulanmıyor (küçük).
- **Boyutlandırma:** `notional = risk_oran × ozs / (stop_mesafesi / fiyat)` (`:86`), sonra `min(…, max_pay×ozs, max_brut×ozs − mevcut brüt)`. `ozs` **gerçekleşmiş** özsermaye (açık kâr/zarar dahil değil). Kaldıraçsız: toplam brüt ≤ özsermaye, tek pozisyon ≤ %25, en çok 5 pozisyon.
- **Kaldıraç/tasfiye:** `KALDIRAC.md` için izole teminat tasfiyesi eklenmiş (`tasfiye_d`, `:21-23, 94, 146-158`), varsayılan kapalı; yalnız tek-slot motorda (`_portfoy`), piramit motorunda (`_portfoy_s`) yok.
- **Evren:** `UYE` maskesi ile yeni giriş yalnız o ay evrendeki coinlerde; açık pozisyon evrenden çıksa da yönetilir.
- Koddaki yapı: `_portfoy` ve `_portfoy_s` ~250 satır kopya; her ikisinde 200.000 satırlık işlem tamponu.

**Sonuç topluluğu (ensemble):** KGT v3'ün nihai getirisi 6 ayrı "gün başlangıcı" (0/4/8/12/16/20 UTC) koşusunun **günlük getirilerinin ortalaması**dır (`kripto_final.py:46, topluluk()`): yani 6 alt portföy her gün maliyetsiz biçimde eşitleniyor. Bunun kâğıt botta karşılığı 6 ayrı hesap (833 $) ve eşitleme yok.

**Lookahead denetimim (kendim okudum):**
- `gostergeler.htf_hizala` (`:99-114`): üst zaman dilimi mumu, kapanışı alt mumun kapanışına denk gelen mumda kullanılıyor → ileri bakma yok. Bu fonksiyonda Faz 9'da bir mumluk gecikme hatası bulunup düzeltilmiş (`DENETIM.md` bulgu 2).
- Pivot/CPR seviyeleri `lv.shift(1)` ile yalnız önceki günden (`strateji.py:346`). Günlük EMA'lar `htf_hizala` ile.
- Evren: ay başından önceki veri (`kripto_evren.py:26`).
- KMN: karar d kapanışında, getiri d→d+1; "1 gün erken bakınca Sharpe 2.92'ye fırlıyor" kontrolü yapılmış (`DENETIM.md` §1).
- **Gerçek bir lookahead bulamadım.**

**Benim bulduğum iyimser varsayımlar / zayıflıklar** (hepsi küçük-orta; sonucu tek başına çökertmez ama gerçek parada sonucu aşağı çeker):
1. **Sabit %0.07/taraf maliyet tüm coin ve tüm dönemler için aynı; stop çıkışı tam stop fiyatından.** Sadece açılış boşluğunda kötüleşme var. Gerçekte stop-market emri hareketli saatlerde (Mart 2020, Mayıs/Kasım 2022) ve orta boy altcoinlerde (ZEC, BCH, XLM, NEAR) fiyatın ötesinde dolar; ortalama kayıp "−0.35%" iken en kötü tek işlem −2.25R olmuş (`RAPOR_KRIPTO.md` v3 bölümü). Maliyet ×2 ve ×3 testleri var (PF 2.0 → 1.83 / 1.68, kazanma oranı %38'e düşüyor) ama kriz günü kayması ölçülmemiş.
2. **Delist günü getirisi KMN'de 0** (`momentum.py:104` `fillna(0.0)`; "delist: fiyat yoksa getiri 0"). Çökerek delist olan bir long ya da yükselerek delist olan bir short'un gerçek etkisi ölçülmüyor. Boşluk köprüleme testi etkiyi çok küçük buluyor (`DENETIM.md`: %43.45 → %43.23).
3. **Alt portföyler aynı işlemi tekrarlıyor (sahte çeşitlendirme).** `ortak/backtest_islemleri.csv`'de XRP 2024-11-10 işlemi (R = 112.3) iki alt portföyde aynı anda; BNB Şubat 2021'in R = 80.2 işlemi üç alt portföyde birebir aynı. Kağıt botta SUI 2026-10-11 16:00 girişi üç alt portföyde birebir aynı (`kagit-durum:islemler.csv`). 6 alt portföy "zamanlama şansını" azaltıyor ama aynı 15 coinde risk yoğunluğunu bir miktar katlıyor. Topluluk tablosunda DD %56 → %38 → %30 iyileşmesinin bir kısmı bu eşitlemeden geliyor.
4. **KGT/KMN'nin %50/%50 birleşimi de günlük maliyetsiz eşitleniyor** (`ortak/backtest_gunluk_getiri.csv` sütunu `KGT_KMN_50_50`). Gerçekte iki strateji ayrı hesaplarda sapar.
5. **Sharpe hesabı `√365`** ve günlük özsermaye getirisinden (`kripto_motor.py:488`). Kripto için doğru; ama `backtest/hisse.py` aynı `metrik`'i seans piyasalarına (hafta sonu sıfır getirili günler) uyguluyor; hisse Sharpe'ları buna duyarlı olabilir. (Doğrulamadım; yön belirsiz.)
6. **Sizing gerçekleşmiş sermayeye göre;** canlı hesapta kullanılabilir marjin/mark-to-market ile farkı küçük.
7. **KGT "S1 stopu" iddiası belgede yanlıştı:** gerçekte stop neredeyse hep üst sınır = 3×ATR(1S) (`strateji.py:405` kırpma; `kripto_final.py` docstring; `DENETIM.md` §2). Yani strateji adındaki pivot/CPR yalnız **giriş zamanlama filtresi**; çıkış/risk yapısı ATR tabanlı trend takibi.

**Repo kendi denetimini yaptı; ben ne dedim?** `DENETIM.md` makul ve ayrıntılı: 1 dk veriyle aynı-mum belirsizliğini çözmek (kötümser Sharpe 0.94 gerçek 1.28), motor sentetik testleri, boşluk düzeltmeleri. Ancak şu noktalarda "sonuçlar şişmedi" sonucu yeterince sorgulanmamış:
- Denetim **kaynak olarak aynı ajan zincirine** dayanıyor (üç "bağımsız denetim" ajanı + liderin kendi kontrolleri); dış karşılaştırma (başka motorla çapraz doğrulama) yok.
- **KMN'nin Sharpe'ını 1.69'dan 1.86'ya çıkaran "kaymalı ağırlık" düzeltmesi mantıklı ama yalnız sonucu iyileştirdi.** Düzeltmenin yönü doğru olabilir (adetler sabit kalır); fakat hem ana sonucu hem de yürüyen pencere testini (0.60 → 1.16-1.54) **sonuçları gördükten sonra** değiştirilen hesapla yenilemek "forking paths" (çatallanan yollar) örneği. Eski ve yeni hesap yan yana verilmemiş.
- Rastgele giriş kıyası (v3 filtresiyle yeniden yapıldı) yalnız "giriş zamanlaması"nı ölçüyor: aynı trend filtresi, aynı çıkış, aynı evren. Daha anlamlı kıyas "yalnız trend filtresi + çıkış, giriş serbest" ve "BTC'yi sadece trend filtresiyle tut" olurdu; yapılmamış. KGT'nin BTC ile korelasyonu rapor edilmemiş.

---

## 4. Stratejiler

### 4.1 Özet tablo (tek bakış)

| Strateji | Durum | Tam dönem (2020→2026/09) | OOS (2024→2026/09) | Seçim yöntemi | Not |
|---|---|---|---|---|---|
| SAKK 5 dk (Faz 1) | Terk | BTC %57 kazanma, PF 1.44, 61 işlem/6.7 yıl | BTC PF 1.75 (az örnek) | IS'te seçilip tüm enstrümanlarda aynı parametre | CFD verisi, XAU OOS'ta kaybetti, UKOIL OOS PF 1.01 |
| GPK 1 s (Faz 1) | KGT'nin atası | BTC 644 işlem, %45.5, PF 1.19 | PF 1.28 | `konfig.py` | 2R hedef + gün sonu çıkış |
| **KGT v3** | "Önerilen" | CAGR %33.6, DD %29.5, Sharpe 1.28, PF 2.05 | CAGR %28.7, DD %19.2, Sharpe 1.31 | ~1.750+ kombinasyon + ~20 Brooks varyantı; OOS her adımda görüldü | 6 alt portföy topluluğu |
| **KMN** | "Önerilen" | CAGR %55.2, DD %18.1, Sharpe 1.86 (düzeltmeden sonra) | CAGR %56.1, DD %16.8, Sharpe 2.03 | 432 (kodda 576) ayar + OOS PF ≥ 1.3 seçim ölçütü | 2021 payı büyük, genç coin etkisi |
| EPA-B | Yedek | CAGR %17.3, DD %17.7, Sharpe 1.31 (%0.5 risk) | CAGR %10.6, Sharpe 0.96 | 1.484 kombinasyon | KGT ile korelasyon 0.77 |
| SKA (PA) | Terk (Faz 4) | Hizalama ortalaması CAGR %12.9 | %7.4 | ~2.900 kombinasyon | Tek hizalamada güçlü, kaydırınca bozuldu |
| HGT | Terk (Faz 12) | IS Sharpe 1.39 | OOS Sharpe ≤ 0.25 | 52 varyant | IS kârı 2020-21 boğası |
| Ortalamaya dönüş | Terk (Faz 8) | Medyan Sharpe −1.10 (4S), −0.31 (1G) | – | 256+256+16+1 | |
| TV elemesi | 3 geçti | CAGR %5-12, Sharpe 1.03-1.36 | Sharpe 0.74-1.61 | Pine varsayılanı, optimizasyon yok | Günlük/swing, hayatta kalma yanlılığı |
| KGT Mag7 | Durduruldu | CAGR %11.2 (%0.4 risk), Sharpe 1.16 | – | – | Al-tut Sharpe 1.22; %1 risk satırı CSV'de yok |

### 4.2 KGT (Kripto Günlük Pivot Kırılımı + Trend Takibi), v1 → v3

**Kurallar (v3; `kripto_final.py:1-46`, `konfig.py`, `RAPOR_KRIPTO.md` §1 ve v3 bölümü, `strateji.py:351-410`):**
- **Evren:** her ay hacme göre ilk 15 coin (v1: 10). Yalnız long (short zarar etti).
- **Yön (1G):** günlük EMA(10) > EMA(20) **ve** son günlük kapanış > EMA(20) (v3 eki; Brooks). Ayrıca o günün CPR'si "dar": |TC−BC| ≤ 0.25 × günlük ATR(14). Pivotlar önceki UTC gününden: P=(H+L+C)/3, BC=(H+L)/2, TC=2P−BC, R1=2P−L, S1=2P−H.
- **Giriş (1S):** gün başından ilk 20 saat içinde 1S kapanışı R1'i yukarı keserse (önceki kapanış R1'in altında), bir sonraki saat açılışında long; coin başına günde 1 giriş.
- **Stop:** (R1 kırılım kapanışı − S1) mesafesi, 0.75–3 × ATR14(1S)'e kırpılır → fiilen **3×ATR14(1S)** (sinyallerin ~%95-98'inde).
- **Yönetim:** +1R'de pozisyonun %15'i kapatılır (v1: %25 → v2: %15), stop girişe çekilir.
- **Çıkış:** 4S EMA21 < EMA50 ve kapanış < EMA21 olunca bir sonraki saat açılışında kalanı kapat.
- **Risk:** işlem başına %0.4 (v1 %1, v2 %0.5), en çok 5 eşzamanlı pozisyon, tek pozisyon ≤ %25, kaldıraçsız.
- **Topluluk:** 6 gün-başlangıcı (0/4/8/12/16/20 UTC), sermaye/6.

**Sonuçlar (düzeltilmiş, `DENETIM.md` §4; `sonuclar/kripto/ozet_v3_topluluk.csv`):**

| | İşlem/alt portföy | Kazanma | PF | CAGR | DD | Sharpe |
|---|---|---|---|---|---|---|
| Tüm dönem | 1.225 | %45.5 | 2.05 | %33.6 | %29.5 | 1.28 |
| IS 2020-23 | 741 | %44.5 | 2.10 | %36.9 | %29.5 | 1.28 |
| OOS 2024-26/09 | 483 | %47.1 | 1.96 | %28.7 | %19.2 | 1.31 |
| BTC al-tut | – | – | – | %43.8 | %76.7 | 0.91 |

Yıllık (%): 2020 +56, 2021 +75, 2022 −20, 2023 +60, 2024 +40, 2025 +14, 2026(9 ay) +26 (`yillik_v3_topluluk.csv`).

**Evrim:** v1 → v3'te Sharpe 0.75 → 1.26 (`RAPOR_KRIPTO.md`). Bunun büyük kısmı yapısal seçimlerden: evren 10→15, topluluk (6 gün başı), kısmi kâr %25→%15, EMA20 filtresi. Her biri OOS görülürken seçildi.

**Parametre seçimi / OOS kaç kez görüldü:**
- Faz 2 K5: 576 + 1.120 kombinasyon (OOS izleniyor; `DURUM.md:126` kendisi "OOS birden çok kez incelendi" diyor).
- `RAPOR_KRIPTO.md` §4: "1.750'den fazla kombinasyon".
- Faz 5-6: ~20 Brooks varyantı (iz süren stop, doruk filtresi, günde 2 giriş, piramit, N gün zirvesi, NR4/NR7, haftalık trend, kırılım geri çekilmesi…), her biri IS+OOS ile değerlendirildi; yalnız `kapanış > EMA20` kabul edildi. İyileşme "küçük": Calmar 1.04→1.08, OOS Sharpe 1.26→1.34.
- Sonuç: OOS dönemi **seçim kümesi** gibi davranmış (aşağıda toplam sayım).

**Walk-forward (WF):**
- `RAPOR_PA.md` §9: 2021'den itibaren her yıl yalnız geçmişle seçim (CPR 0.18/0.25/0.35 × kısmi kâr yok/var × evren 5/10/15). KGT: CAGR %38.4, DD %63.7, Sharpe 0.99, her yıl benzer ayar seçilmiş. **Bu WF v1-dönemi motoruyla, %1 riskle, Faz 9 düzeltmelerinden önce** yapıldı.
- `RAPOR_KRIPTO.md` v2 bölümü: WF (kazanma ≥ %40 aday kümesi): CAGR %28.9, DD %63, Sharpe 0.88 (%1 risk). Sabit v2 ayarı aynı dönemde %42.3.
- v3 + Faz 9 sonrası motor için ayrı bir WF görmedim. Önemli: WF yalnız **parametrelere** bakıyor; yapısal seçimler (CPR+R1, EMA10/20, kapanış>EMA20, 4S çıkışı) tüm veriyle bulunduğu için WF onları test etmiyor.

**Dayanıklılık testleri (rapor):** rastgele giriş (aynı filtre ve çıkışla) gerçek PF'de %97'yi geçiyor, OOS PF'de %85-90; komşu parametreler OOS PF 1.34-1.58; maliyet ×2'de PF 1.83; 6 gün-başının 6'sı da kârlı; Monte Carlo (20 günlük blok bootstrap) 1 yılda zarar olasılığı %16; kaldıraç: 2x'e kadar kabul edilebilir (`KALDIRAC.md`).

**Benim bulgularım (`ortak/backtest_islemleri.csv`, `backtest_gunluk_getiri.csv` üzerinden hesapladım):**
- **Kâr aşırı yoğun:** 7.349 işlem satırından en iyi 100'ü (satırların %1.4'ü; aynı işlem birkaç alt portföyde tekrarlanıyor) toplam basit katkının **%95'ini** veriyor; en iyi 10 satır %24. Geri kalan ~7.050 satır toplamda net negatif. R ≥ 20 olan 100 satır var; en büyükler XRP 2024-11 (R=112), BNB 2021-01/02. Tipik trend takibi şekli; yani strateji "ayda bir iki büyük trendi yakalama" stratejisi, kazanma oranı %45 yanıltıcı (rapor da kendi içinde kabul ediyor: kazançların %73'ü < 0.3R, işlemlerin %9'u ≥ 1R).
- **Uzun düşüş süresi:** KGT eğrisinde zirveden en uzun dönüş süresi **990 gün (~2.7 yıl)**; KMN 314 gün; KGT+KMN 50/50 272 gün. Maks. DD %29.5 küçük görünüyor ama yeni zirve görmeden 2.7 yıl.
- **2021 payı:** log getiriye payı KGT'de %29, KMN'de %39; 2021 çıkarılırsa yıllık getiri KGT ≈ %27, KMN ≈ %37 (yıllık tablodan kendi hesabım, yaklaşık).
- **KGT–KMN korelasyonu** `ortak/backtest_gunluk_getiri.csv`'de 0.25, belgede 0.20 (Faz 8 tablosu 0.17-0.20).
- **BTC+ETH payı:** R toplamının ~%31'i BTC+ETH'den (679+499 / 3.750); 15 coinlik genişlik gerçek anlamda önemli (SOL, BNB, ZEC, LINK, DOGE katkıları). Tek-sembol (1L3A) uyarlamasında sonuç bundan zayıf çıkabilir.

### 4.3 KMN (Kesitsel Momentum, Piyasa Nötr) — portföy stratejisi

**Kaynak:** 151 Trading Stratejisi §3.1 (fiyat momentumu).
**Kurallar (`RAPOR_S2.md` §2, `momentum.py`, `momentum_sinyal.py:1-40`):**
- Evren: önceki ay sonu 30 günlük hacme göre ilk **30** coin, en az 90 gün kesintisiz geçmiş.
- Skor: son 14 günlük günlük getirilerin **ortalaması / standart sapması** (riske göre düzeltilmiş), son gün atlanmıyor (S=0).
- En yüksek 5 coin long, en düşük 5 coin short; her taraf sermayenin %50'si (brüt 1.0, net ≈ 0).
- Ağırlık: 30 günlük günlük oynaklığın tersi (alt sınır %1, `VOL_TABAN=0.01`).
- Dengeleme: 14 günde bir, günlük kapanışta (00:00 UTC); aradaki günlerde **adetler sabit** (ağırlıklar fiyatla kayar). Canlıda 2 alt portföy 7 gün arayla.
- Masraf %0.07 × devir; funding (long öder, short alır).

**Sonuçlar (düzeltilmiş):** tam dönem CAGR %55.2, DD %18.1, Sharpe 1.86; OOS CAGR %56.1, DD %16.8, Sharpe 2.03. Yıllık %: 2020 +51, 2021 **+215**, 2022 +18, 2023 +2, 2024 +52, 2025 +71, 2026(9 ay) +30. 2 alt portföy canlı düzende: %42-64, DD %19-30, Sharpe 1.41-1.90 (`DENETIM.md` §4).

**Parametre seçimi:** ızgara `momentum.py:~165` kodda 3 mod × 2 N × 6 L × 2 S × 2 K × 2 H × 2 ağırlık = **576** kombinasyon (belge "432" diyor, küçük çelişki; skor türü ek 3 koşu). Medyan Sharpe 1.26; seçilen ayar 1.69'du. Yani seçim primi ≈ +0.4 Sharpe. Seçim ölçütleri `DURUM.md:27-29`'a göre OOS PF ≥ 1.3 ve KGT ile korelasyon < 0.3'ü **içeriyor**: OOS'ın kendisi seçimin parçası.

**Walk-forward:** "her yıl yalnız geçmişle 864 ayardan en iyisi": ilk hesapta CAGR %13.6, Sharpe **0.60** (`RAPOR_S2.md:101`); Faz 9'da hesap kaymalı ağırlıkla yenilenince Sharpe **1.16-1.54** (`DENETIM.md:106`). Belge kendi içinde "gerçekçi beklenti Sharpe 1.0-1.3" diyor.

**Sağlamlık (rapor):** maliyet ×3'te Sharpe 1.63; 1 gün gecikmede 1.79; en iyi 10 gün sıfırlanınca 1.53; rastgele long/short %100'den iyi (medyan −0.30); **yalnız long bacak 0.94, yalnız short bacak 0.02** (kâr iki bacağın farkından); "≥180 gün geçmişli coinler" Sharpe 1.51, "≥365 gün" 1.15 (`DENETIM.md`); kısa vadeli dönüş (ters momentum) Sharpe −0.99.

**Benim notlarım:**
- Kâr bir kısmı genç coinlerin (90-365 gün listelenmiş) short bacağından geliyor; bu coinlerde gerçek kayma %0.07'den büyük olabilir (belge bunu kabul ediyor, `DENETIM.md` §5).
- Short bacak gerçek dünyada squeeze'e açık; en kötü 14 günlük ters hareketin %95'i %48.6 (`KALDIRAC.md`). 1.5x'te bile getiri yarıya iniyor.
- Maliyet gerçekçi mi? 30 coinin 5+5'i, 14 günde bir devir ≈ yıllık 42× sermaye devri, masraf ~%2.9. Küçük/yeni coinlerde spread bu varsayımdan geniş olabilir.
- **Genişlik bağımlılığı:** KMN yalnız N=30'da çalıştı. Mag7 (N=7, K=2): Sharpe 0.03; BIST: −0.15 (`RAPOR_HISSE.md`). Izgarada N=15 de denendi (30 daha iyi). Bu, 1L3A'nın "kripto ≤10 sembol" sınırıyla doğrudan çelişiyor (§7b).

### 4.4 EPA (kullanıcının EMA 8/21/55 + hacim + mum + S/D + trend çizgisi fikri; Faz 7)
`RAPOR_EPA.md`, `ANALIZ_EMA_STRATEJI.md`, `backtest/epa.py`. 1.484 kombinasyon, 4 mum hizalamasının ortalaması.
- **EPA-A (pullback + mum formasyonu):** başarısız. En iyi ayar Sharpe 0.99 ama OOS Sharpe 0.42, 2024 sonrası yıllık %6. Bileşen etkisi: hammer/engulfing şartı katkısız (0.66 vs 0.67), trend çizgisi zararlı (0.33), azalan hacim nötr, günlük yatay filtre zararlı.
- **EPA-B (breakout):** günlük EMA 8/21/55 bağlamı + 4S 18 mumluk sıkışma (< 7 ATR) + kırılım mumunda hacim ≥ 2× ortalama + 4S EMA8<21 çıkışı + 1R'de %15 kısmi. %0.5 riskte kazanma %48.9, PF 2.03, CAGR %17.3, DD %17.7, Sharpe 1.31, OOS Sharpe 0.96 (OOS CAGR %10.6); 4 hizalamanın 4'ünde kârlı; maliyet ×3'te 1.17; rastgele girişlerin %100'ünden iyi. **KGT ile korelasyon 0.77**; 2025-26 neredeyse yatay.

### 4.5 PA / Brooks / Galen Woods (Faz 3-5)
- **SKA** (Galen "Tıkanıklık Kırılım Arızası", 4S, ilk 20 coin): ilk rapor Tüm dönem PF 3.18, CAGR %25 (`RAPOR_PA.md` §3). **Mum hizalamasını 1-3 saat kaydırınca** PF 1.12-2.74, OOS PF 0.78'e düşüyor (`RAPOR_PA.md` §8); 4 hizalama ortalaması CAGR %12.9, Sharpe 0.89; WF Sharpe 0.36, ayarlar her yıl değişti. Sonuç: bırakıldı. Kâr yoğunlaşması aşırı: en iyi 5 işlem toplam R'nin %73'ü; tek XRP işlemi özsermayenin %59'u.
- **Elenen PA kurulumları** (1S ve 4S; TBF, DEC, ANT, PZ, WPB, PIN): test PF 0.75-0.88; 1S'de masraf stopun ~%13'ü (`RAPOR_PA.md` §5). ~2.900 kombinasyon.
- **Brooks Yüksek 1/2 (H1/H2) boğa bayrağı:** 4S'de 4 hizalamada OOS PF ~0.5; 1S'de de başarısız.
- **Brooks'tan KGT'ye eklenenler** (iz süren stop, doruk filtresi, günde 2 giriş, piramit, N günlük zirve, NR4/NR7/iç gün, haftalık trend, kırılım geri çekilmesi): hepsi iyileştirmedi; yalnız `kapanış > EMA20` kabul edildi (`SONUC.md`, `RAPOR_KRIPTO.md` v3 tablosu).

### 4.6 HGT (haftalık yön / günlük işlem; Faz 12)
Kaynak 20 Strateji Sistem #5. 52 varyant. IS 2020-23 en iyi Sharpe 1.39 (CAGR %43.4), OOS tüm varyantlarda Sharpe ≤ 0.25 (çoğu negatif); IS kârı 2020 (+85) ve 2021 (+133) boğasından; 2024'te BTC +%121 yaparken strateji −%10 (`RAPOR_HGT.md`). Kitabın kendi 1:1 hedefi CAGR %2-5. Karar: kağıt bota eklenmedi.

### 4.7 Ortalamaya dönüş (Faz 8)
4S Bollinger/RSI(2) + ADX filtresi + onay mumu: 256 kombinasyon, medyan Sharpe −1.10, hiçbiri > 0.5; günlük: −0.31; kesitsel kısa vadeli dönüş: −0.99; IBS günlük: −2.07 (yıllık −%49) (`RAPOR_S2.md` §1). Gerekçe: kripto trend yapan piyasa.

### 4.8 Faz 1: SAKK / GPK ve 5 dk bulguları
`RAPOR.md`. Üç ortak payda test edildi; A (trend + EMA bölgesine geri çekilme) ve B (üst TF trend + BB/RSI/VWAP dönüşü) "avantaj yok"; **5 dakikada koşullu ileri getiri avantajı en fazla ~0.15 ATR, gerçekçi masraf 0.18-0.46 ATR** (§2). C (kutu/seviye kırılımı + daralma filtresi) IS ve OOS'ta avantajlı → SAKK/GPK. Bu, 1L3A'nın "min 5 dk" kararı ve DURUM.md'deki "5 dk'da maliyet baskın" gözlemiyle uyumlu.
- SAKK sonuçları: SPX %60.5/PF 1.62 (76 işlem), UKOIL %54/PF 1.32, BTC %57.4/PF 1.44 (61 işlem), XAU OOS'ta PF 0.87. GPK: SPX PF 1.38, UKOIL 1.21 (komşu parametrelerin yalnız ~%48'i kârlı), BTC PF 1.19, XAU 0.99. Örneklem küçük (61-644 işlem), SPX/UKOIL/XAU CFD verisi yalnız →2023-09.

### 4.9 Kaldıraç (`KALDIRAC.md`)
Tasfiye hesaplı: KGT 5x'e kadar neredeyse tasfiyesiz (stop medyan %3.9, %95'i %9.4); (b) senaryosunda (riski de büyüt) Sharpe ~1.34 sabit, DD 2x'te %51. KMN 1.5x'te CAGR %55→%29, 3x'te iflas. Öneri: kaldıraç yalnız KGT'ye (≤2x), KMN 1x. Kağıt bot değiştirilmedi. Tasfiye modeli son işlem fiyatına göre; Binance işaret fiyatı kullanır (belge bunu not ediyor).

### 4.10 Hisse/emtia (`RAPOR_HISSE.md`, `sonuclar/hisse/ozet.csv`)
- **KGT Mag7:** %0.4 riskte CAGR %11.2, DD %11.8, Sharpe 1.16, 168 işlem, PF 1.92; **al-tut CAGR %34, DD %29.8, Sharpe 1.22** (aynı dönem). Rapordaki "KGT Mag7'de çalışıyor" cümlesi **%1 risk satırına** (CAGR %20, Sharpe 1.43) dayanıyor; bu satır `sonuclar/hisse/ozet.csv`'de **yok** (CSV'de yalnız %0.4 risk var), yani rakam kayıtlı çıktıdan doğrulanamıyor. Kâr 3 hisseden: NVDA +30.5R, META +20.8R, GOOGL +18.9R; MSFT −4.7R. Örneklem ~3 yıl, 2023-11 → 2026-10, boğa piyasası.
- **BIST:** TL'de %7-15 (al-tut %34), USD'de −%11; KMN BIST TL −%2, USD −%28. TL enflasyonu trend stratejilerini TL bazında şişirir.
- **Emtia (altın+Brent):** KGT CAGR %6, Sharpe 0.94, kazanma %63, PF 3.5; 2024-26; yalnız 64 işlem. Tek pozisyon %25 sınırı nedeniyle risk artınca getiri artmıyor.
- **KMN hisse/emtia:** Mag7 Sharpe 0.03, BIST −0.15 (küçük evren).

### 4.11 TradingView elemesi (`tv/`)
**Süreç:** 2 PDF'ten 164 benzersiz Pine betiği (160 kaynağı açık, 4 kapalı) → Aşama 1 ön eleme **41 aday** (123 elendi: gösterge/şablon, `lookahead_on`, repaint, kapalı kaynak, tick verisi, kopya; `tv/aday.csv`) → 36'sı Python'a çevrildi (5 çevrilemedi) → Aşama 3 sert kurallar → **3 geçti** (`tv/RAPOR.md`, `tv/GOREV.md` Aşama 3).

**9 zorunlu kural (kullanıcı onaylı 13 Eki; `tv/GOREV.md`):** (1) işlem sayısı swing ≥ 100 / gün içi ≥ 300; (2) maks. DD ≤ %20; (3) beklenti ≥ +0.15R; (4) PF ≥ 1.3 ve Sharpe ≥ 1.0; (5) OOS Sharpe ≥ 0.5 × eğitim Sharpe ve OOS kârda; (6) maliyet ×2'de PF ≥ 1.1; (7) her sayısal parametre ±%20 → komşuların ≥ %70'i kârda; (8) enstrümanların ≥ %60'ı kârda. Sıralama: Calmar ≥ 1, DD süresi < 6 ay, PSR ≥ %90, işlem başı kâr ≥ 3× maliyet, mevcut stratejilerle korelasyon ≤ 0.6.

**Kural bazında elenenler** (kümülatif değil, her kuralı ayrı ayrı kaçıran strateji sayısı; `tv/RAPOR.md` tablosu ve `tv/sonuclar/ozet.csv`): işlem sayısı 0, maks. DD ≤ %20 kuralını 27, beklenti 20, PF 20, Sharpe ≥ 1 kuralını 32, OOS 18, maliyet ×2 18, komşu ≥ %70 kuralını 14, enstrüman ≥ %60 kuralını 16 strateji kaçırdı. En çok eleyen kural: Sharpe ≥ 1 ve DD ≤ %20.

**Geçenler (hepsi günlük/swing, long ağırlıklı, 37 enstrümanda):**

| Strateji | İşlem | PF | Sharpe | DD | CAGR (sabit 10.000$) | Sharpe IS / OOS | Ortalama tutma |
|---|---|---|---|---|---|---|---|
| hybrid_brk (Minervini tarzı 50>150>200 SMA + sıkışma + hacim kırılımı, %8 stop, %20 hedef) | 570 | 1.89 | 1.36 | %10.9 | %12.4 | 1.34 / 1.61 | 29 gün |
| sqzmom (LazyBear Squeeze Momentum, 1G, EMA100) | 1.477 | 1.81 | 1.06 | %4.9 | %5.0 | 1.18 / 0.74 | 8 gün |
| macd_reloaded (VAR ortalamalı MACD sıfır kesişimi) | 4.113 | 1.52 | 1.03 | %19.8 | %12.2 | 1.12 / 0.87 | 25 gün |

(`tv/sonuclar/*.json` `olcut` alanı.) Kazanma %35-44.

**Benim notlarım (TV):**
- Pine **varsayılan parametreleri** kullanıldı (optimizasyon yok, iyi), ama bu varsayılanları yazarlar kendi geçmiş grafiklerinde güzel görünmesi için seçmiştir; üstelik giriş havuzu "en beğenilen 100" ve "performans araştırması" PDF'leri (`tv/kaynak/pdf1_...`, `pdf2_...`): popülerlik seçimi.
- Enstrüman listesi **bugünün kazananları**: NVDA, META, AVGO, LLY, TSLA, MSFT… ve BIST'te TL bazlı fiyatlar. Rapor kendi "bilinen sınırlar" bölümünde hayatta kalma yanlılığını kabul ediyor. TL fiyatları enflasyonla yükseldiği için trend takipçileri BIST'te yapay iyi çıkar.
- Pozisyon boyu "10.000 $ sabit, bileşiksiz"; CAGR %5-12: mutlak getiri düşük. Çevirmede Pine'daki kısmi çıkışlar, pyramiding ve seans/gün sonu kuralları motorda **yok** (`tv/RAPOR.md` sınırlar (2)).
- 36 test, 3 geçen: 9 kural eşiği tek tek makul ama bir arada çoklu-test düzeltmesi yok. `kripto_mom` OOS kuralında kalan tek "yakın" aday (8/9).
- `tv/` stratejilerinin hiçbiri 1L3A'nın Binance-only evrenine (BIST yok, hisse perp geçmişi 1-10 ay) doğrudan taşınamaz; yalnız kripto alt kümesi.

### 4.12 Elenenler ve nedenleri

| Ne | Neden (kaynak) |
|---|---|
| 5 dk trend + EMA bölgesi geri çekilme (A) ve BB/RSI/VWAP dönüşü (B) | Avantaj ≤ 0.15 ATR < masraf 0.18-0.46 ATR (`RAPOR.md` §2) |
| SAKK/GPK XAU | OOS PF 0.87 / 0.99 |
| SAKK/GPK XU030 | Veri yok (hiç test edilmedi) |
| Kripto saf 1S geri çekilme (RSI) ve Donchian kırılımı girişi | OOS PF ~0.95-1.0, kâr birkaç dev trendden (`RAPOR_KRIPTO.md` §4) |
| Short (KGT) | Her ayarda long-only'den kötü; OOS PF 1.09 |
| BTC rejim filtresi, göreli güç filtresi | Testte bozuyor / katkısız |
| İlk 20-40 coin (KGT) | Altcoinler birlikte düşüyor; OOS zayıf |
| SKA ve tüm PA kurulumları | Hizalama testi / OOS PF < 1 |
| Brooks H1/H2 | OOS PF ~0.5 |
| Ortalamaya dönüş (4S, 1G, IBS, kesitsel) | Medyan Sharpe −0.3…−2.1 |
| HGT (haftalık yön) | OOS Sharpe ≤ 0.25, kâr 2020-21'de |
| EPA-A (pullback + mum, trend çizgisi) | OOS Sharpe 0.42; trend çizgisi zararlı |
| 33 TV stratejisi (36 çevrilenden 3 geçti) | Çoğu Sharpe < 1 veya DD > %20; 10'u 7-8/9 kuralı geçip 1-2 kuralda kaldı (gvto, ichimoku, kripto_mom, st_kivanc…) |
| KMN hisse/emtia | Küçük evren, Sharpe ≈ 0 |
| KGT BIST | USD'de zarar |
| Kaldıraç (KMN) | 1.5x'te getiri yarıya, 3x iflas |

---

## 5. Kağıt botlar

### 5.1 `kagit` (KGT v3 + KMN, 10.000 $)
- **Mimari** (`canli/README.md`, `canli/kagit.py`, `canli/motor.py`, `.github/workflows/kagit.yml`): GitHub Actions saat :07 ve :37'de çalışır; durum klasörünü `kagit-durum` dalından yükler, son işlenen saatten itibaren **kapanmış tüm saatlik mumları sırayla işler** (kaçırılan çalıştırmaları telafi, en çok 7 gün); durum ve CSV'leri geri `kagit-durum`'a push eder; her UTC günü bitince günlük rapor GitHub issue'ya yorum olarak yazılır. KGT: `KGTAltPortfoy` × 6 (833 $); KMN: `KMNDefter` × 2 (A, B; her biri 2.500 $, 7 gün arayla 14 günde bir dengeleme). Backtest ile **aynı fonksiyonları** kullanıyor (`backtest/strateji.py`, `kripto_final.py`, `momentum_sinyal.py`); doğrulama: 2024'te 221/221 işlem aynı, 2 aylık oynatmada 90/90 işlem, toplam fark %0.3 (`DURUM.md` K4).
- **Veri:** Binance **spot** (vadeli değil); `1000XUSDT`→`XUSDT` eşleme; fonlama OKX'ten, bulunamazsa sabit %0.0001; aylık evren Binance vadeli arşivinden "önceki takvim ayı hacmi" (backtest "önceki 30 gün" kullanıyor; küçük sapma). `canli/README.md` evreni "ilk 40" diyor, KGT `KGT_P["evren_n"]=15` kullanıyor (`canli/kagit.py:129,141`).
- **Başlangıç:** 2026-10-09 19:07 UTC; planlanan bitiş 2026-12-09 19:07 (`kagit-durum:ozet.md`, `durum.json`).
- **Son güncelleme:** 2026-10-15 22:00 UTC saat verisi, son commit 2026-10-15 23:13 UTC (`kagit-durum` HEAD `0f2e4c4`).
- **Son durum** (`ozet.md`): KGT 4.988,03 $ (−%0.24), KMN 5.013,59 $ (+%0.27), toplam **10.001,62 $ (+%0.02)**. Açık: 3× NEAR (KGT G00/G08/G20), KMN-A 10 pozisyon (+342 $ FIL, +317 $ WLD, … −385 $ XRP), KMN-B henüz pozisyonsuz (ilk dengeleme 7 gün sonra). `islemler.csv` ~11 kayıt, `ozsermaye.csv` 148 saatlik satır.
- **Gerçekleşen vs beklenti:** 6 günlük +%0.02. KGT için %33 yıllık ≈ haftada %0.6 ve haftalık oynaklık yaklaşık %3-4; yani sonuç gürültü içinde; **istatistiksel hiçbir anlamı yok**. Not: aynı SUI girişi üç alt portföyde (G04/G08/G12) aynı anda tekrarlandı (islemler.csv), alt portföy korelasyonuna işaret.
- **Neden durmuş olabilir** (kesin bilgi yok; kanıtlar):
  1. İki bot (`kagit` 10-15 23:13 UTC, `kagit-tv` 10-15 00:06 UTC) neredeyse aynı günde durdu: ortak neden olası.
  2. `canli/README.md` "Maliyet" bölümü kendi tahminini 720-1.440 dk/ay veriyor, ücretsiz planda özel repo için 2.000 dk. İkinci bot (`tv`) ve aynı hesaptaki diğer projelerin (`algo-sg`, `swing-sg`; arşivde `kagit.yml` var) botları aynı kotadan yer. **En olası neden: Actions dakika kotası.** (Doğrulayamam; kullanıcı Actions sekmesine bakmalı.)
  3. `main`'deki `.github/workflows/` içinde yalnız `kagit.yml`, `kagit_deneme.yml`, `veri_hisse.yml` var; **`kagit-tv` için workflow yok**. Zamanlanmış workflow'lar yalnız varsayılan daldan çalışır; `tv` botu muhtemelen başka bir daldan/elle tetiklendi ve main'e hiç alınmadı.
  4. Kullanıcı repoları 2026-11-06'da kapattı (`arsiv/README.md`); ama bu, 10-15'te durmayı açıklamaz.
  5. GitHub'ın 60 günlük hareketsizlik kuralı henüz geçerli olamaz.
- **Kağıt botun kanıt değeri sınırlı:** dolumları kendi simülasyonu yapıyor (gerçek emir defteri/kayma yok), fiyatlar spot, fonlama OKX/varsayım. Yani iki aylık test tamamlansa bile yürütme varsayımlarını doğrulamazdı; yalnız sinyal akışını ve ileri dönem davranışını gösterirdi.

### 5.2 `kagit-tv` (TV'den geçen 3 strateji, 10.000 $)
- **Mimari** (`tv/kagit.py`, `tv/GOREV.md` Aşama 4): her çalıştırmada başlangıç tarihinden bugüne tüm geçmişi **yeniden oynatır**; durum `kagit_tv_durum`/`kagit-tv-durum` dalı: `durum.json, islemler.csv, ozsermaye.csv, pozisyonlar.csv, ozet.md`. Bütçe 3 × 3.333,33 $ sabit; veri: kripto Binance spot, hisse/emtia Yahoo.
- **Başlangıç:** 2026-10-14 00:00 UTC, planlanan bitiş 2026-12-10 (57 gün). **Son güncelleme:** 2026-10-15 00:04 UTC (`kagit-tv-durum` HEAD `f4e6f69`).
- **Durum:** toplam 10.001,71 $ (+%0.02), kapanan işlem **0**, macd_reloaded'de bir açık AVAX short (+1,71 $); diğer ikisi pozisyonsuz. 25 saatlik veri. **Hiçbir şey öğretmiyor.**
- Durma nedenleri için bkz. 5.1.

---

## 6. Pano, raporlama, bildirim

- **Pano (dashboard) bu repoda yok.** `tv/GOREV.md` "swing-sg `karsilastirma/panel_veri.py` (panel bunu okuyor)" diyerek paneli diğer repoya (swing-sg) bağlıyor; strateji-sg'de web/panel kodu yok. Telegram da yok.
- **Günlük rapor:** `kagit.yml` her UTC günü bitince `kagit_durum/gunluk_rapor.md`'yi açık bir GitHub issue'ya (başlık: "Kağıt al-sat raporu (KGT + KMN, 10.000 USD)") yorum olarak ekliyor (`gh issue create/comment`), ardından dosyayı siliyor. GitHub bildirimi e-posta/telefona düşüyor (`canli/README.md`). İssue içeriğini göremedim (yalnız `--depth 1` dal çekildi; issue API'si çağrılmadı). Rapor metnine "Backtest beklentisi (yıllık): toplam %35-45, maks. düşüş %15-20" sabit olarak yazılıyor (`canli/kagit.py:316`).
- **Haftalık Claude rutini:** `DURUM.md` FAZ 10 K5'e göre Pazartesi 08:52 İstanbul'da zamanlanmış bir Claude görevi (`trig_01NYzWBMPH4uVrSGGHq9mJQd`) kağıt botu değerlendirecekti. İlk kurulan rutin repo erişimi olmadığı için hata verip silinmiş, bir oturuma bağlı yenisi kurulmuş (`DURUM.md:1-5`). Bu rutinin çalışıp çalışmadığı repodan görünmüyor.
- **PR / dal düzeni:** Bot PR #1 ile main'e alınacaktı; `kagit-durum` ve `kagit-tv-durum` ayrı "veri dalı" olarak durumu tutuyor (main'i kirletmiyor). `kagit_deneme.yml` ve `veri_hisse.yml` yalnız `claude/dreamy-cannon-lsimjy` dalı için.

---

## 7. 1L3A'ya aktarım önerisi

### 7a. Alınabilecek kod modülleri ve 1L3A motoruyla uyum

1L3A motoru (`motor/backtest/motor.py`): tek sembol, aynı anda 1 pozisyon, Decimal, tick/step/min_notional, ayrı stop kayması, sert limitler, funding; `Strateji.sinyaller(mumlar)` → `yon/stop/hedef/cikis`. `cikislar.py`: ATR iz süren, zaman çıkışı, sabit R hedefi, **başabaşa çekme**. **Eksik:** kısmi kâr (tp1_pay), çok pozisyon/portföy, günlük pivot, kesitsel sıralama.

| Modül (strateji-sg) | Ne işe yarar | 1L3A'ya uyum | Öneri |
|---|---|---|---|
| `gostergeler.htf_hizala` (`:99-114`) + birim testi fikri | Kapanmış üst-TF mumunu alt-TF'ye ileri bakmadan hizalar (1G/4S → 1S/5 dk) | 1L3A'da `yeniden_ornekle` var, hizalama yok. Taşıması kolay (pandas `merge_asof`) | **Al** (yeniden yaz, kendi testiyle). Faz 9'da burada bir mum gecikme hatası bulunmuş |
| `strateji.gunluk_seviyeler` / `gunluk_kirilim` (`:300-410`) | Günlük pivot/CPR, dar CPR, R1 kırılımı, günde tek sinyal | 1L3A'da yalnız salınım pivotu (`pivotlar.py`) var; `daytrade__pivot-seviye` ailesi (Singhal, 2 yazar, CPR kartıyla) bu işin ailesi | **Al, aile kodu olarak** (`motor/strateji/` altında). `tz`/`gun_bas` parametreleri TradFi perp (24/7) için yeniden düşünülmeli |
| `kripto_motor.py` | Çoklu coin portföy, kısmi kâr, aynı mumda belirsizlik çözümü, tasfiye modeli | float, tick/step yok, sert limit yok, 494 satır + kopya kod; **import etme** | **Referans motor olarak kullan:** aynı veride aynı KGT'yi iki motorda koş, işlem listelerini karşılaştır (çapraz doğrulama). Alınacak kavramlar: kısmi kâr + başabaş, `ici_sira` (ince veriyle belirsizliği çözme: 1L3A'da 5 dk içinde 1 dk) |
| `kripto_final.rastgele / montecarlo` ve `hizalama` testleri | Rastgele giriş kıyası, blok bootstrap, **mum hizalama / gün başı kaydırma testi** | 1L3A `metrikler.py` 52 satır, bunlar yok | **Al:** her aday için standart sağlamlık paketi. Hizalama testi SKA'yı çökerten testti; 4S/1G dayanan adaylara şart |
| `tv/GOREV.md` Aşama 3 kuralları | 9 net sayısal eleme eşiği | `DURUM.md` "Aşama 2 eleme eşikleri" kararı bekliyor | **Şablon olarak kullan** (özellikle: OOS ≥ 0.5×IS, maliyet ×2'de PF ≥ 1.1, ±%20 komşular ≥ %70, enstrümanların ≥ %60'ı) |
| `momentum.py`, `momentum_sinyal.py` (190 + 93 satır) | Kesitsel momentum ağırlıkları, kaymalı ağırlıkla getiri, canlı hedef portföy | Strateji arayüzüne uymuyor (çok sembol, günlük panel, getiri serisi döndürüyor) | **Ayrı "portföy modülü"** olarak yeniden yaz (Decimal, adım yuvarlama, funding dosyaları); §7b sorusuna bağlı |
| `kripto_veri.py` / `kripto_evren.py` | S3 indirme; aylık point-in-time evren | 1L3A `motor/veri/indir.py` zaten S3+sha256+parquet yapıyor. Evren seçimi (ay başında önceki 30 gün hacmi, ≥ 90 gün, delist dahil, hisse/emtia hariç) 1L3A'da yok | **Evren fikrini al**; kodu değil |
| `canli/motor.py`, `canli/kagit.py` | Saat saat artımlı motor, "kaçırılan saatleri yeniden oynat" deseni | 1L3A Aşama 3'te kendi paper motorunu yazacak; DigitalOcean'da sürekli çalışacak, GitHub Actions deseni gerekmez | Yalnız **"başlangıçtan yeniden oynat → durum"** idempotent deseni ve "paper = backtest motoru" eşdeğerlik testi (221/221) fikri al |
| `tv/stratejiler/*.py`, `tv/pine/*.pine` | 36 Pine → Python çeviri | Pine betiklerinin kendi lisansları var (`arsiv/README.md`); 1L3A bunları kopyalamıyor | Yalnız başvuru; kopyalama |
| `araclar/veri_hisse.py`, `veri_dis/` | Yahoo hisse/emtia verisi | 1L3A BIST yok, Binance TradFi perp verisini data.binance.vision'dan alıyor | **Alma** |

**Uyum sorunları:**
- **Kısmi kâr (1R'de %15)** KGT'nin karakter belirleyici parçası (kazançların %73'ü < 0.3R); 1L3A motoru bunu yapmıyor. Eklenecek.
- **Portföy kısıtı** (max 5 eş zamanlı, brüt ≤ özsermaye, hacim sırası önceliği) tek-sembol motorda yok. Seçenek: her sembolü bağımsız koş + paper katmanında koordinatör; ya da portföy motoru.
- **6 gün-başı topluluğu** 6 ayrı koşu + günlük ortalama; 1L3A'da "tek strateji = tek sembol" ile uyumsuz. Aday olarak "tek gün başı" ile test edip topluluğu ayrı bir katman olarak düşünmek gerek.
- Sert limit uyumu: KGT %0.4 risk, kaldıraçsız → 1L3A'nın %1/3x limitlerine rahat sığar. KMN brüt 1.0 (5L+5S) ve short bacak squeeze'i: günlük kayıp %3 / kill switch %20 ile test edilmeli.

### 7b. Aday strateji olarak değerlendirilecekler

**KGT (en olgun aday, ama dikkatle):**
- 1L3A'da en yakın aile: `daytrade__pivot-seviye` (CPR kartı `daytrade__cpr-genis-dar-kirilim__singhal`, 51 Strateji kaynaklı) + `swing__ma-kesisim` (yön filtresi) + çıkış modülü (4S trend dönüşü) + kısmi kâr/başabaş. Yani tek bir aileye değil **bileşik** bir stratejiye karşılık geliyor.
- Önerilen yol: (1) BTC/ETH üzerinde (1L3A'da zaten 5 dk verisi var: `veri/mumlar/BTCUSDT, ETHUSDT, XAUUSDT`) 1S'e resample ile yeniden kodla; (2) strateji-sg motoruyla çapraz doğrula; (3) 1L3A'nın maliyet modeli (komisyon + 2/5 bps kayma + funding) ile koş; (4) IS/OOS'u **yeniden** böl (2020-2023 / 2024-2026 artık "görülmüş"), asıl OOS = yeni veri; (5) rastgele giriş + hizalama + komşu parametre + eleme eşikleri.
- **Genişlik uyarısı:** sonuç 15 coin + 5 pozisyon ile çıktı. BTC+ETH payı R toplamının ~%31'i; tek sembolde çok daha zayıf, daha yüksek DD ve uzun düşüş süresi beklenmeli.
- **Beklenti için gerçekçi aralık** (repo kendisi): yıllık %25-33, DD %30'a kadar, 2.7 yıl zirvesiz dönem mümkün.

**KMN (kesitsel/portföy; 1L3A'nın tek-sembol mimarisiyle çelişiyor):**
- 1L3A `Strateji.sinyaller(mumlar)` **tek sembolün mumunu** alır. KMN aynı anda 30 coini **birbirine göre** sıralar; arayüze sığmaz. Ayrı bir "portföy stratejisi" tipi gerekir (günlük panel girdi, hedef ağırlık çıktı) ve DURUM.md karar #3 (LLM ajanları ≥ 15 dk aralıkla üst seviye karar) ile uyumlu bir "dengeleme ajanı" olarak düşünülebilir.
- **Çelişki:** 1L3A kararı "kripto ≤ 10 sembol" (`README.md`). KMN'nin sonucu N=30'a bağlı (N=15 daha zayıf; küçük evrende Sharpe ≈ 0). N=10, K=2-3 ile test edilmeden aday sayılamaz. **Karar kullanıcıda:** evren sınırını KMN için gevşetmek, ya da KMN'yi 1L3A kapsamından çıkarmak.
- Ek riskler: short bacak squeeze/tasfiye (kaldıraçsız bile), genç coin kayması, 2021 etkisi, WF belirsizliği. Beklenti: Sharpe 1.0-1.3 (belgeye göre), 1.86 değil.
- 1L3A aile listesinde karşılığı yok; `swing__goreceli-guc-momentum` (3 yazar, YEDEK) yalnız "en güçlüyü al" tek-yönlü; KMN market-nötr long/short.

**Diğer adaylar:**
- EPA-B (günlük EMA 8/21/55 bağlamı + 4S sıkışma + hacim ≥ 2× kırılım) → `swing__konsolidasyon-kirilim` / `swing__dar-aralik-kirilim` / `swing__bb-sikisma-kirilim` ailelerine **kanıt** olarak yazılabilir: "hacim teyidi DD'yi düşürür, bağlam filtresi şart". KGT ile korelasyon 0.77 olduğundan ikinci bağımsız kaynak değil.
- TV'den `sqzmom` (BB/Keltner sıkışma kırılımı) → `swing__bb-sikisma-kirilim` (1 yazar) için ek kanıt; `macd_reloaded` → `swing__macd-sinyal`; `hybrid_brk` → `swing__konsolidasyon-kirilim`/VCP kartı (Singhal). Hepsi günlük, hayatta kalma yanlılığı var, CAGR %5-12 → ancak **zayıf ek kanıt**.

### 7c. "Denendi-başarısız" negatif bilgi → 1L3A `aile_id` eşlemesi
(1L3A `stratejiler/aileler.json`; kapsam: kripto 1S-1G, 2020-2026, masraf %0.07/taraf, repo bulgularına göre.)

| Bulgu | 1L3A aile_id | Not |
|---|---|---|
| 5 dk/1 s trend + EMA bölgesine geri çekilme avantaj yok (avantaj ≤ 0.15 ATR < masraf) | `scalp__ma-geri-cekilme`, `daytrade__ma-geri-cekilme`, `scalp__geri-cekilme-fiyat-eylemi`, `daytrade__geri-cekilme-fiyat-eylemi` | 5 dk'da maliyet duvarı; 1L3A'nın DURUM.md gözlemiyle (BTC 5m EMA 9/21, komisyon sermayenin %9'u) aynı sonuç |
| BB/RSI/VWAP dönüşü (5 dk, 1 s, 4S, 1G) medyan Sharpe < 0 | `scalp__bant-donus`, `daytrade__bant-donus`, `swing__bant-donus`, `scalp__rsi-asiri-donus`, `daytrade__rsi-asiri-donus`, `swing__rsi-asiri-donus`, `daytrade__vwap-donus`, `daytrade__aralik-ticareti`, `swing__aralik-ticareti` | Kripto trend piyasası; test ETH/BTC değil 15-20 coin portföyü |
| IBS dönüşü günlük Sharpe −2.07, kesitsel kısa vadeli dönüş −0.99 | `swing__ardisik-bar-tukenme`, `daytrade__ardisik-bar-tukenme` (IBS benzeri) | |
| Çift RSI geri çekilme (1G+4S yön, 1S RSI dip) OOS PF ~0.95 | `scalp/daytrade/swing__rsi-*` | |
| 1S Donchian kırılımı OOS PF ~1.0, DD %60-90 geniş evrende | `swing__donchian-kirilim`, `daytrade__donchian-kirilim` | |
| Kırılım geri çekilmesi (R1'e dönüp yeni zirve) tek başına Sharpe 0.76-0.82; tabana ek faydasız | `swing__kirilim-geri-test`, `daytrade__kirilim-geri-test` | |
| Brooks H1/H2 boğa bayrağı (4S/1S) OOS PF ~0.5 | `swing__geri-cekilme-fiyat-eylemi`, `swing__ma-geri-cekilme` | |
| Pin bar 4S/1S, Yavaşlama, Doruğa karşı, Basınç Bölgesi, Zayıf Geri Çekilme, Trend Çubuğu Arızası | `swing__pin-bar`, `daytrade__pin-bar`, `swing__sahte-kirilim`, `scalp/daytrade__sahte-kirilim` | PA kurulumları test PF 0.75-0.88 |
| SKA / Congestion Breakout Failure: tek mum hizalamasında iyi | `swing__sahte-kirilim`, `scalp__sahte-kirilim` | Mum hizalaması testini geçemedi |
| Mum formasyonları (hammer, engulfing) pullback'e katkısız | `swing__mum-yutan-donus`, `swing__mum-coklu-formasyon` | EPA-A: 0.66 vs 0.67 |
| Trend çizgisi konumu şartı zararlı | `swing__trend-cizgisi-kanal`, `daytrade__trend-cizgisi-kanal`, `swing__talep-arz-bolgesi` | EPA-A: Sharpe 0.33 |
| Günlük yatay-piyasa filtresi zararlı | (ADX/yatay filtre) | EPA: 0.83 → 0.50 |
| Haftalık yön + günlük tetik EMA dizilimi OOS ≤ 0.25 | `swing__ma-kesisim` (çoklu EMA dizilim), `daytrade__trend-yapi-dow` | HGT: IS kâr 2020-21 |
| Short tarafı (KGT) zarar | tüm trend ailelerinin short kolları | Kripto, 2020-26 |
| BTC rejim filtresi (BTC trendi yukarıyken alt long) ve göreli güç filtresi | `swing__goreceli-guc-momentum` | IS iyi, OOS kötü / katkısız |
| Kısmi kâr yok, yalnız 1:1 hedef | – | HGT: CAGR %2-5 |
| Stok: ORB-benzeri seans kutusu (SAKK) | `daytrade__orb` | SPX/BTC kâr, XAU OOS'ta kayıp, örneklem küçük, CFD verisi; BTC 61 işlem/6.7 yıl |
| TV: gunluk_kapanis, halftrend, mom_exhaust, sikisma_bb, stoch_rsi, bb_rsi, macd_stoch, utbot, st_rejim, ribbon_fan… | `swing__bant-donus`, `swing__stokastik-donus`, `scalp__supertrend-psar`, `swing__supertrend-psar`, `swing__heikin-ashi-donus` benzerleri | Sharpe < 0.5 veya PF < 1; supertrend türevlerinden yalnız `st_kivanc` 8/9 kuralı geçti (Sharpe 0.97) |

(`pivot-seviye` ve `dar-aralik-kirilim` ailelerinde KGT/EPA-B bulguları **olumlu** kanıt sayılmalı.)

### 7d. `metinler/` kitapları ve 1L3A kaynaklarıyla örtüşme

| strateji-sg `metinler/` | 1L3A `veri/kart_dizini.csv` `kaynak_dosya` | Durum |
|---|---|---|
| 51 Trading Stratejisi (433 s.) | `51_Trading_Stratejisi_433_sayfa` (51 kart) | **Örtüşüyor** (KGT'nin CPR/pivot kuralı 51S §2.7 / §2.3, s.134-146; 1L3A'da `daytrade__cpr-genis-dar-kirilim__singhal` kartı var) |
| Galen Woods Cilt 3 | `Price_Action_ile_Günlük_Trading_Teknikleri_-_Galen_Woods_-_Volume_3_227_sayfa` (9 kart) | **Örtüşüyor** (SKA kaynağı) |
| 20 Trading Stratejisi (28 s.) | yok | **Yeni kaynak** (kart_dizini.csv'de yok) |
| 151 Trading Stratejisi (Kakushadze & Serur, 800 s.) | yok | **Yeni kaynak:** KMN'nin (kesitsel momentum §3.1), IBS §4.4, artık momentum §3.7, ortalamaya dönüş §10.3 kaynağı. Kripto için nicel stratejilerin en zengin kaynağı |
| Al Brooks: Trends (439), Trading Ranges (572), En Başarılı 10 PA Modeli (24 s.) | yok | **Yeni kaynak** (3 dosya). Sonuç: kuralları çıkarılıp test edildi, ana katkı yalnız `kapanış > EMA20` |

Notlar: 1L3A'da 50 PDF'den 438 kart var; strateji-sg 7 kaynağın 2'si orada, 5 yeni (20S, 151S, 3 Brooks). `metinler/` dosyaları (4,6 MB .md) arşive alınmamış, 1L3A kuralı gereği zaten repoya girmez. İsterse kullanıcı bu 5 PDF'yi 1L3A'nın kart çıkarma hattına (Aşama 0 süreci) sokabilir; özellikle 151S ve 20S. (Yazar sayısı kuralı açısından 151 Strateji bir derleme: "farklı yazar" sayısını nasıl sayacağı ayrı karar.)

### 7e. Mag7/hisse testinin TradFi perpetual'lar için anlamı
- Hisse/emtia testi **Yahoo seans (RTH) mumları** ile yapıldı (hisse 09:30-16:00 NY, gece boşluğu doldurulmadı, `backtest/hisse.py:1-12`); Binance TradFi perp'leri **24/7** işlem görür, gün sınırı, açılış boşluğu, spread, funding ve gece likiditesi farklıdır. Pivot "önceki gün" tanımı, gün başı (UTC mi, NY mi) KGT'nin çekirdeği; TradFi perp'te yeniden tanımlanmalı.
- Sonuç zaten zayıf: %0.4 riskte KGT Mag7 Sharpe 1.16 vs al-tut 1.22; yani **al-tutu aşan kanıt yok**, yalnız DD düşük (%12 vs %30). Kâr 3 hisseden (NVDA, META, GOOGL), 3 yıllık boğa dönemi, 168 işlem. %1 riskli "Sharpe 1.43" satırı kayıtlı çıktıda yok.
- Binance TradFi perp geçmişi 1-10 ay (`DURUM.md`, `veri/sembol_envanteri.csv`): KGT'nin 1S/1G EMA'larını ısıtmak bile zor (EMA20 günlük + 90 gün).
- **KMN hisse/emtiada çalışmadı** (Sharpe 0.03): kesitsel mantık küçük ve yüksek korelasyonlu evrende kaybolur.
- Yorum: strateji-sg'nin sonucu TradFi perp için **ne olumlu ne olumsuz kanıt** sayılmalı; en çok, "trend takibi hisselerde de kâğıt üzerinde çalışabilir ama al-tutu aşmaz" ipucu verir. Seçimi kriptoda yapıp TradFi'yi yalnız doğrulama için kullanma yönündeki 1L3A önerisi (DURUM.md "Kullanıcı kararı bekleyenler" #6) bu sonuçla tutarlı.

---

## 8. Kırmızı bayraklar

**Aşırı uyum / seçim yanlılığı**
- OOS (2024-01 → 2026-09) seçimin parçası olarak defalarca görüldü. Belgelenen deneme sayıları: KGT 1.750+ (Faz 2 K5: 576 + 1.120) + ~20 Brooks varyantı; SKA ~2.900; EPA 1.484; KMN 432-576 (+864 WF); HGT 52; ortalamaya dönüş ~530; TV 36 test (+164 tarama). Toplam **~7.000+ yapılandırma**, çoğunda OOS metrikleri raporlandı ya da seçim ölçütüydü (KMN: "OOS PF ≥ 1.3"; `DURUM.md:27-29`). Bu nedenle "OOS" sonuçları bağımsız doğrulama değil. Belgeler de bunu itiraf ediyor (`RAPOR_KRIPTO.md:97`, `RAPOR_PA.md:98`, `DURUM.md:126`).
- **Tek gerçek ileri-test kanıtı:** kağıt botlarda ~6 gün, +%0.02; anlamsız.
- Yapısal seçimler (CPR+R1, EMA10/20, `kapanış>EMA20`, evren 15, %15 kısmi kâr) WF'nin dışında kaldı; WF yalnız aday kümesindeki parametrelere bakıyor ve v3/Faz 9 sonrası yenilenmedi.
- Çoklu test düzeltmesi (Deflated Sharpe, White Reality Check vb.) hiç yok.
- KMN: seçilen Sharpe 1.69/1.86, ızgara medyanı 1.26; "kayma" düzeltmesi sonuçları gördükten sonra yapılıp hem ana sonucu hem WF'yi iyileştirdi.

**Rejim / dönem etkileri**
- **2021 boğa:** log getirinin KGT'de %29'u, KMN'de %39'u tek yıldan (benim hesabım). KMN 2021 ilk raporda +%113, düzeltmeden sonra +%215. 2021 hariç yaklaşık yıllık KGT %27, KMN %37.
- 2020-2021 + 2023-2024 trend yılları; 2022 ve 2025 zayıf. Veri yalnız tek tam kripto döngüsü (2020-2026); 2018-2019 yok.
- **Genç coin etkisi (KMN):** ≥180 gün geçmiş filtresiyle Sharpe 1.51, ≥365 gün 1.15; kâr kısmen yeni listelenen coinlerin short bacağından. Bu coinlerde kayma %0.07'den yüksek olabilir.
- **Kâr yoğunlaşması:** KGT'de en iyi 100 işlem satırı toplam katkının ~%95'i; SKA'da XRP Kasım 2024 tek başına özsermayenin %59'u; BNB 2021 işlemleri.
- **Uzun düşüş süresi:** KGT 990 gün (~2.7 yıl) zirvesiz; kazanma oranı %45 yanıltıcı (kazançların %73'ü < 0.3R).
- **Beta/yön:** yalnız long KGT; ayı yılı 2022'de −%20 (BTC −%64). KGT–BTC korelasyonu raporlanmamış.

**Belge-kod çelişkileri** (bir kısmı repo tarafından düzeltilmiş, bir kısmı hâlâ duruyor)
- Stop "S1'de" yazıyordu; fiilen 3×ATR(1S) (düzeltildi, `DENETIM.md`).
- "İlk 10 coin" (v1) / "ilk 15" (v2-v3) / `canli/README.md` "ilk 40" (evren listesi; KGT yine 15 kullanıyor).
- KMN ızgarası belgede 432, kodda 576 kombinasyon (`momentum.py:~165`).
- KGT–KMN korelasyonu belgede 0.17-0.20, `ortak/backtest_gunluk_getiri.csv`'den 0.25.
- `RAPOR_HISSE.md` "%1 risk Sharpe 1.43" satırı `sonuclar/hisse/ozet.csv`'de yok.
- `SONUC.md` aynı dosyada iki farklı dönemin KMN rakamlarını (%43 ve %55) art arda veriyor; `DURUM.md` FAZ 10 hâlâ "DEVAM EDİYOR".
- `SONUC.md` "Kullanmadan önce: 2-3 ay kağıt üzerinde ileri test" der; kağıt bot ~6 gün çalıştı.
- Kağıt bot backtest'ten farklı: spot fiyat, OKX fonlama/sabit %0.01, evren "önceki takvim ayı", 6 ayrı hesap (eşitleme yok).
- `kagit-tv` botu için workflow `main`'de yok (§5).
- `be_1dk.pkl` .gitignore'a rağmen repoda (tek `*.pkl`); `data/` yok → KGT nihai sayıları repodan **tek başına yeniden üretilemez** (veri indirilmesi gerek).

**Dış doğrulama yok:** tüm sayıları aynı ekibin kodu üretti; başka motorla/çapraz kaynakla doğrulama yapılmadı.

---

## Lider için özet

1. strateji-sg: 12 fazlı kripto-ağırlıklı araştırma (Binance USDT-M, 311 perp, 1S/4S/1G, 2020–2026/09). Ana ürünleri KGT v3 (günlük CPR/R1 kırılımı + trend takibi, long-only) ve KMN (30 coinlik kesitsel momentum, long/short); sonuç: KGT Sharpe 1.28 / CAGR %34 / DD %29, KMN Sharpe 1.86 / CAGR %55 / DD %18 (düzeltilmiş backtest).
2. Motor ve denetim genelde sağlam, gerçek lookahead bulamadım. İyimserlikler: sabit %0.07 maliyet ve stop kayması yok, 6 alt portföyün sahte çeşitlendirmesi, delist günü KMN'de 0 getiri, günlük maliyetsiz eşitleme.
3. "OOS" fiilen kullanıldı: toplam ~7.000 yapılandırma OOS görülerek seçildi; çoklu test düzeltmesi yok. Tek gerçek ileri test (kağıt bot) ~6 gün, +%0.02, 10-15'te durdu (en olası neden Actions dakika kotası, kanıt yok).
4. Kâr yoğunlaşması: KGT'de en iyi 100 işlem satırı katkının ~%95'i; en uzun düşüş 990 gün; 2021 log getirinin KGT'de %29'u, KMN'de %39'u. KMN'de genç coin etkisi, WF belirsizliği (0.6 → 1.2-1.5, sonradan hesapla yenilendi).
5. Kesin negatifler (1L3A ailelerine eşlenmiş, §7c): 5 dk geri çekilme/dönüş (maliyet duvarı), BB/RSI/IBS ortalamaya dönüş, Brooks H1/H2, SKA (mum hizalamasına duyarlı), HGT, short, EPA-A mum/trend çizgisi.
6. Alınacaklar: `htf_hizala`, günlük pivot/CPR modülü, sağlamlık paketi (rastgele giriş, mum-hizalama, blok bootstrap), TV eleme eşikleri (Aşama 2 şablonu), evren yöntemi; `kripto_motor.py` import edilmez, çapraz doğrulama referansı olur.
7. KGT aday (daytrade__pivot-seviye + trend + kısmi kâr); 1L3A motoruna kısmi kâr ve portföy kısıtı eklenmeli; BTC+ETH ile sonuç zayıflar (R'nin ~%31'i). KMN tek-sembol mimarisine ve "kripto ≤10" sınırına uymuyor; N=30'a bağımlı → kullanıcı kararı gerek.
8. Yeni kaynaklar: 20 Strateji, 151 Strateji (KMN kaynağı), 3 Brooks kitabı `kart_dizini.csv`'de yok; 51 Strateji ve Galen Woods zaten var.
9. Mag7/hisse testi TradFi perp için kanıt değil: RTH mumları, 3 yıl boğa, KGT Sharpe 1.16 vs al-tut 1.22, %1 risk satırı CSV'de yok; KMN hisse/emtiada çalışmadı.
10. Arşiv zaten `/home/user/1L3A-Proje/arsiv/strateji-sg/` altında (commit 366d758); yalnız başvuru, import yasak.
