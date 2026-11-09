# Evren stratejileri seçimi — ÖN KAYIT v2

Tarih: 2026-11-09. Hazırlayan: Fable (yöntem denetçisi). Onay: kullanıcı (v2 önerisi olduğu gibi onaylandı; holdout v2'ye
saklandı; "D" seçeneği uygulanmadı). Dayanak rapor: `fable_havuz_secim_raporu.md` bölüm 3.0–3.9.

Bu dosya v2 koşularından ÖNCE yazıldı. İçindeki hiçbir sayı, eşik, sıra kuralı ya da tohum sonuç görüldükten sonra
değiştirilmez. `[v2 kararı]` işareti: raporda açık bırakılmış, burada tek bir somut seçimle kapatılmış nokta.

---

## 0. Beyanlar (değişmez)

**0.1 Sonuç-sonrası tasarım beyanı.** v2, v1 hattının geliştirme dönemi sonuçları (WF 920 → 38 geçen; sağlamlık 58 aday;
K5'ten 58/58 kalan; K5 hariç her şeyi geçen 24) GÖRÜLDÜKTEN SONRA tasarlandı. Bu yüzden v2'nin geliştirme dönemi
(… → 2025-11-07) çıktıları **kanıt değildir**; yalnız "holdout'a hangi set gider" kararını verir. Kanıt: holdout (bölüm 7)
ve paper (bölüm 8).

**0.2 v1 resmi sonucu.** v1 (ON_KAYIT.md, Güncelleme 1–8) sonucu **"iyi 0, iyiye yakın 0"** olarak resmi kayıtta kalır,
silinmez, değiştirilmez. v2 raporu v1 ve v2 sonucunu yan yana gösterir.

**0.3 Tek tur.** v2 son tasarımdır. Bu veriler (geliştirme + holdout) üzerinde üçüncü bir tasarım (v3) değerlendirilmez.
v2 sıfır strateji verirse sonuç sıfırdır. Yeni fikir ancak yeni (ileri) veriyle ve yeni ön kayıtla denenir.

**0.4 Holdout.** 2025-11-08 00:00 UTC → veri sonu. v2 seti mühürlenene kadar hiçbir aşama bu veriyi okumaz
(`kilit_ac`/`donem="holdout"` yalnız bölüm 7'de). Holdout BİR KEZ açılır; ikinci deneme yoktur.

**0.5 Değişmez proje kuralları.** SERT_LIMITLER (işlem başı %1 maliyet dahil, toplam açık stop riski %5, brüt 3x,
günlük %3, kill %20) aynen. Martingale / DCA / ortalama düşürme / stopsuz grid yok. Lookahead yok. Sessiz try/except
yok (hata = satır "hata", sayılır). Canlı para her zaman kullanıcı onayı.

**0.6 "İyiye yakın" kademesi yok.** v2'de tek liste vardır: sağlam keşif. Kıl payı eşikleri yoktur.

**0.7 Yalnız rapor (kapı değil):** DSR, PBO, K3 bootstrap PF alt sınırı, Sharpe, max düşüş, maliyet ×3 PF, Hansen SPA,
BY düzeltmesi, kardeş evren (bölüm 9).

---

## 1. Sabitler

| Ad | Değer |
|---|---|
| Geliştirme dönemi | en eski veri → 2025-11-07 (dahil) |
| Analiz başlangıcı | evrenin (o tf'de verisi olan enstrümanların) ≥ %75'inin verisinin başladığı gün (v1 ile aynı) |
| Evren (genel) | v1 `EVREN_GENEL` (35: 13 kripto + 17 ABD hisse + 5 emtia), 2026-11-07 listesi, sabit |
| Evren (yalnız kripto) | `EVREN_GENEL` içindeki 13 kripto |
| Maliyet | `sonuclar/evren/maliyet_tablosu.csv` (hash'i aynı) + TradFi funding (1.2) |
| Ana tohum `TOHUM` | **20261109** `[v2 kararı]` |
| Satır tohumu | `zlib.crc32(f"{strateji}|{tf}|{asama}".encode()) ^ TOHUM` `[v2 kararı]`; `asama` ∈ {k2a, k2b, boot, hk2, hset} |
| K2 tekrar (1. aşama) | B = 500 |
| K2 tekrar (2. aşama) | 1d ve 4h: B = 10.000; 15m: B = 5.000 `[v2 kararı]` |
| K2 2. aşamaya geçiş | 1. aşama p ≤ 0.02 |
| Yanlış keşif oranı (BH) | q = 0.10 |
| Bootstrap | durağan blok, ortalama blok 20 gün, 2.000 çekim |
| SPA (rapor) | durağan bootstrap, ortalama blok 20 gün, B = 2.000, kıyas = sıfır |
| Holdout K2 | set: B = 5.000; strateji: B = 2.000 `[v2 kararı]` |
| Çıktı dizini | `sonuclar/evren/v2/` `[v2 kararı]` |
| Havuz dosyası | `stratejiler/havuz_v2.csv` `[v2 kararı]` |

**1.1 Varsayılan ayar.** Her strateji tek ayarla koşar: kayıttaki `varsayilan` adayı (ham yan dosyasında `adaylar[0]`).
Kart ayarı varsa (stratejiler/kart_ayarlari) o dosyanın İLK kaydı varsayılandır `[v2 kararı]`. Izgara yalnız S2'de
kullanılır. Walk-forward ayar seçimi yoktur.

**1.2 TradFi funding `[v2 kararı]`.** `DK_` sembollerinde LONG pozisyon, tutulan her 8 saat (takvim süresi; hafta sonu
ve seans dışı dahil) için nominalin **%0.01**'ini öder (≈ yıllık %10.95). SHORT pozisyona funding geliri **yazılmaz**
(0). Maliyet çarpanı (×2) funding'i çarpmaz. Kriptoda gerçek funding serisi aynen. Bu varsayım maliyet tablosuna
`funding_long_8s_oran` sütunu olarak eklenir; tablonun yeni sha256'sı v2 çıktılarına yazılır.

**1.3 p-değeri tanımı.** Her rastgele-giriş testinde p = (1 + #{sim ≥ gerçek}) / (B + 1).

---

## 2. Aşama 0 — Havuzun dondurulması

Çıktı: `stratejiler/havuz_v2.csv` + sha256 (`sonuclar/evren/v2/havuz_muhru.json`) + commit. Sütunlar: `strateji, stil_v2,
tf, evren (genel|kripto), etiket, alt_etiket, kume_no, kaynak_strateji (klon ise), kilit_gorulmus (evet|hayir), not`.
Koşu başladıktan sonra havuz dosyası değişmez.

**2.1 Birim.** Bir satır = (strateji, birincil tf), varsayılan ayar.

**2.2 Stiller `[v2 kararı]`.** `swing` (tek-grafik, 1d/4h), `gunici_kripto` (2.5), `portfoy` (19 `pf__` sınıfı, 1d).
Daytrade ve scalp geniş havuzları v2 resmi ailesine girmez (kod silinmez).

**2.3 Stil klonları.** Aynı gövde adı birden çok stilde bulunan kitap stratejilerinde yalnız `swing__` olanı havuza
girer; swing karşılığı yoksa strateji havuza girmez `[v2 kararı]`.

**2.4 Birincil zaman dilimi (swing) `[v2 kararı]`.** Birincil tf = **1d**. İstisna: stratejinin kaynak kaydındaki
`zaman_dilimi` alanı (kart ya da `dis_envanter.csv`) `4h`, `4s`, `H4` ya da `240` içeriyor VE `1d`, `1g`, `D`, `günlük`,
`daily` içermiyorsa birincil tf = 4h. Alan boşsa 1d. Diğer tf deneme sayılmaz; yalnız S3'te kullanılır.

**2.5 Gün içi kripto hipotezi `[v2 kararı]`.** Tek aile, 7 satır, tf = **15m**, evren = yalnız kripto:
`dis__ewo-ema-ofset`, `dis__bb-alt-bant-osilator`, `dis__ft-cluc-may2018`, `dis__ft-binhv45`, `dis__ft-cofibit`,
`dis__e0v1en`, `dis__aroon-stochrsi-ema-dip`. Ön şart: dolum gerçekçiliği denetimi (P0-5) tamamlanmış ve raporu
`sonuclar/evren/v2/dolum_denetimi.md` olarak yazılmış olmalı. Denetim motor hatası bulursa motor düzeltilir, SONRA
v2 koşulur; denetim bir stratejide lookahead/gerçek dışı dolum bulursa o satır `hata` olur (m'den düşmez).

**2.6 Etiketler `[v2 kararı]`.** Her satıra giriş tetikleyicisine göre TEK ana etiket:

| etiket | tanım |
|---|---|
| `trend` | fiyat/ortalama kesişimi, ortalama dizilimi, trend çizgisi göstergeleri (MA, MACD, Supertrend, PSAR, Ichimoku, ADX yönü) |
| `geri_cekilme` | trend yönünde geri çekilmede giriş (trend filtresi + dip) |
| `donus` | trend filtresi olmadan aşırı alım/satımdan dönüş (RSI, stokastik, bant, z-skor) |
| `kirilim` | aralık / kanal / zirve / sıkışma kırılımı |
| `formasyon` | mum ve grafik formasyonları, harmonik, fraktal |
| `seviye` | destek-direnç, pivot, yuvarlak sayı, önceki gün seviyesi |
| `takvim` | ay/gün/saat/mevsim kuralı |
| `hacim` | tetikleyici hacim göstergesi |
| `funding` | funding/baz sinyali |
| `kesitsel` | enstrümanlar arası sıralama / çift / sepet (portföy sınıfları) |
| `karma` | yukarıdakilerden ikisi eşit ağırlıkta; başka etikete indirgenemiyor |

`alt_etiket` = ana gösterge adı (ör. `ema_kesisim`, `macd`, `rsi`, `bollinger`, `donchian`). Etiketleme performansa
bakmadan, yalnız kural metninden yapılır; etiketleyen ajan sonuç dosyalarını açmaz.

**2.7 Tekilleştirme (küme) kuralı `[v2 kararı]`.** İki satır aynı kümededir, eğer:
(a) aynı sınıf/kuralın klonu ise (2.3), **veya**
(b) aynı `etiket` + aynı `alt_etiket` **ve** v1 geliştirme WF-OOS haftalık getiri korelasyonu ≥ 0.7 ise.
Haftalık seri: `sonuclar/evren/2017_gelistirme/oos/<strateji>--<tf>.parquet`, kabul edilen işlemlerin `pnl`'i çıkış gününe,
haftalık (Pazar kapanışlı, UTC) toplam; ortak hafta < 100 ise korelasyon "ölçülemedi" = ayrı küme. Bağlantı: ortalama
bağlantı. v1'de serisi olmayan (yeni) strateji yalnız (a) ile kümelenir.
Kümenin temsilcisi havuza girer: en az sayısal parametreli olan; eşitlikte alfabetik ilk. Diğerleri havuz dışı.

**2.8 Yeni adaylar.** v2 havuzuna, koşudan önce kodlanıp `dogrula`'dan geçmiş şu sınıflardan stratejiler eklenebilir:
kesitsel long-short, kısa açabilen yavaş zaman-serisi momentumu, funding sinyali, takvim. Her eklenen satır aileye
dahildir ve m'yi artırır. Havuz mühürlendikten sonra ekleme yok. (Rejim bindirmesi strateji değildir; v2'de yoktur.)

**2.9 Kilitli dönemde görülmüşler.** `stratejiler/final_set.json`'daki 7 strateji, `sonuclar/kilit/` set dosyalarında adı
geçenler ve "son 1 ay" adayları havuz dosyasında `kilit_gorulmus=evet` işaretlenir (yalnız adlar okunur, sonuçlar
okunmaz). Bunlar havuzda kalır; holdout raporunda ayrı işaretlenir.

**2.10 Aile büyüklüğü m.** `m = max(havuz_v2 satır sayısı, 939)`. Gerekçe: 939 satır bu veride zaten denendi; budama
sonuç görüldükten sonra yapıldığı için indirim alınmaz. Havuz 939'u aşarsa m = havuz satır sayısı. m, havuz mührüne
yazılır.

---

## 3. Aşama 1 — Ham koşu

Her satır, beyan ettiği evrenin tüm enstrümanlarında, geliştirme döneminin tamamında, varsayılan ayarla, maliyet ×1 ve
×2 ile koşulur. Çıktıya her işlem için **günlük piyasa-değeri (MTM) yolu** yazılır: işlemin açık olduğu her UTC gün sonu
için birikimli R (o günün kapanış fiyatıyla; maliyetler girişte ve çıkışta). Sharpe, düşüş ve korelasyon bu yoldan
hesaplanır. Verisi olmayan (sembol, tf) dışarıda kalır ve raporlanır. Tek kasa oynatma: `secim.yeniden_oyna`, sıra =
giriş zamanı, eşitlikte evren sırası (v1 ile aynı).

---

## 4. Aşama 2 — Eleme (5 kapı)

Tek kasa oynatmasında KABUL edilen işlemler üzerinden. Hepsi şart. NaN = geçmez.

| # | Kapı | Tam tanım |
|---|---|---|
| E1 | Kârlılık | maliyet ×2 oynatmasında net getiri > 0 **ve** maliyet ×1'de PF(R) ≥ 1.2 |
| E2 | Örnek | kabul edilen işlem ≥ 200 **ve** işlem yapılan enstrüman ≥ 10 (evren = kripto ise ≥ 6 `[v2 kararı]`) |
| E3 | Yoğunlaşma | toplam R'si en yüksek enstrüman çıkarılınca Σ R > 0 **ve** toplam R'si en yüksek takvim yılı (giriş tarihi, UTC) çıkarılınca Σ R > 0 |
| E4 | Genişlik | evren = genel ise: üç sınıftan (kripto/hisse/emtia) en az ikisinin her biri Σ R'nin ≥ %15'i. Evren = kripto ise kapı yok |
| E5 | Hayatta kalma | maliyet ×1 oynatmasında `kill_olayi == 0` `[v2 kararı: ×1]` |

**Portföy satırları `[v2 kararı]`:** E1 = maliyet ×2'de net > 0 ve maliyet ×1'de günlük Sharpe ≥ 0.5; E2 = dönem ≥ 1095
gün ve ≥ 20 yeniden dengeleme (karar 24); E3 = yalnız "en iyi takvim yılı çıkarılınca net > 0"; E4 yok; E5 aynı.

Elemeyi geçemeyen satırın resmi test p-değeri 1'dir (5.3).

---

## 5. Aşama 3 — Resmi test (tek çoklu-test adımı)

**5.1 İstatistik (tek-grafik).** `evren_k2` mantığı: her gerçek işlem için enstrüman, yön, stop/ATR14 katı ve
stratejinin kendi çıkış kuralları korunur; giriş mumu, gerçek girişin bulunduğu **takvim çeyreği (UTC)** içinden, o
enstrümanın mumlarından tekdüze rastgele çekilir. Sınama büyüklüğü T = Σ R (enstrüman başı çakışma süzgecinden sonra,
tek kasa oynatmasından önce; v1 ile aynı). Maliyet ×1. Desteklenmeyen çıkış modülü olan satır: p = 1, `rnd_desteklenmeyen`
yazılır.

**5.2 Portföy.** v1'deki rastgele-ağırlık testi (aynı takvim, aynı ağırlık kümesi, rastgele semboller); büyüklük =
günlük Sharpe.

**5.3 Tekrar ve p.** 1. aşama B = 500 (tohum `k2a`). p ≤ 0.02 ise 2. aşama: **yeni** tohumla (`k2b`) B = 10.000
(15m: 5.000); nihai p YALNIZ 2. aşama çekimlerinden hesaplanır. p > 0.02 ise nihai p = 1. aşama p'si.
Elemeyi geçemeyen, hata veren ya da test koşulmayan her satır: p = 1.

**5.4 Karar.** Benjamini-Hochberg: m (2.10) hipotez; p'ler küçükten büyüğe sıralanır (eşitlikte alfabetik);
k* = max{k : p_(k) ≤ 0.10 · k / m}; ilk k* satır **"keşif"**. k* yoksa keşif yok.

**5.5 Rapor.** BY sonucu (eşik 0.10·k / (m·Σ_{j≤m} 1/j)); Hansen SPA p-değeri (havuzun tüm satırlarının günlük MTM
getirisi, sıfıra karşı). SPA p > 0.10 ise v2 raporunun ilk satırına yazılır: "havuzun bütününde sıfırdan farklılık
kanıtı yok". SPA kapı değildir.

---

## 6. Aşama 4 ve 5 — Sağlamlık ve set

### 6.1 Sağlamlık (yalnız keşiflere; dördü de şart)

| # | Kontrol | Tam tanım |
|---|---|---|
| S1 | Gecikme | sinyal 1 mum gecikmeli (`GecikmeliStrateji`), maliyet ×1, tek kasa: PF(R) ≥ 1.0 |
| S2 | Komşu ayar | `saglamlik.komsu_parametreler(varsayılan)` komşuları, geliştirme döneminin tamamı, aynı evren, maliyet ×1, PF(R) = evren toplamı (oynatma öncesi): **medyan ≥ 1.1 ve en düşük ≥ 0.9**. Geçerli komşu < 2 ise kalır |
| S3 | Komşu tf | swing: diğer tf'de (1d↔4h) varsayılan ayarla PF(R) (oynatma öncesi) ≥ 1.0. `gunici_kripto` ve `portfoy`: yok |
| S4 | Ayı rejimi | ayı günlerinde girilen işlemlerin Σ R ≥ −0.20 × (tüm dönem Σ R) |

**S4 tanımı `[v2 kararı]`.** Endeks: stratejinin beyan ettiği evrenin (genel 35 / kripto 13) 1d kapanışlarından günlük
basit getiri; o gün verisi olan üyelerin eşit ağırlıklı ortalaması (seans boşluğu için en çok 5 gün ileri doldurma);
endeks = birikimli çarpım, başlangıç 1. Gün d **ayı günüdür** ⇔ endeks(d−1) < endeksin d−1'de biten 200 günlük basit
ortalaması. İlk 200 gün tanımsız = ayı değil. İşlem, GİRİŞ gününe göre atanır. Ayı günlerinde kabul edilen işlem < 20
ise S4 "ölçülemedi = geçti" sayılır ve `s4_az_ornek=evet` yazılır. Portföy satırlarında R yerine günlük getiri toplamı.

Dördünü geçen = **sağlam keşif**. Birini kaçıran = izleme listesi (sete girmez, holdout'a gitmez).

### 6.2 Set kurma

1. **Korelasyon kümesi:** sağlam keşiflerin haftalık MTM getirisi (Pazar kapanışlı, UTC; tek kasa, maliyet ×1);
   uzaklık 1 − ρ, ortalama bağlantı, kesim 0.5 (ρ > 0.5 aynı küme). Ortak hafta < 100 ise ayrı küme.
2. **Sıra:** nihai K2 p küçük olan önce; eşitlikte maliyet ×2 PF(R) yüksek olan; hâlâ eşitse alfabetik.
3. **Açgözlü seçim, stil başına:** sırayla; aday alınır, eğer (a) stilde henüz < 3 seçilmişse, (b) aynı korelasyon
   kümesinden seçilmiş yoksa, (c) aynı stilde aynı ana `etiket`ten seçilmiş yoksa `[v2 kararı]`. Sharpe'a göre sıralama yok.
4. **Ağırlık:** eşit risk — her stratejide işlem başı risk = s × %1; hepsi TEK kasada, sert limitler aynen.
   Portföy satırı sete girerse karar 25 bütçesi (toplam stop riski ≤ s × %5) uygulanır.
5. **Boyut s `[v2 kararı]`:** s ∈ {1.0, 0.9, …, 0.1}. Setin s = 1 tek kasa oynatmasının günlük MTM getirisi alınır;
   s ile çarpılır; durağan blok bootstrap (blok 20, 2.000 çekim, tohum `boot`) ile max düşüş dağılımı; **%95'lik
   ≤ %15** şartını sağlayan EN BÜYÜK s seçilir. s = 0.1 de sağlamıyorsa set kurulmaz (sonuç 0). Yukarı ölçek yok.
6. Sağlam keşfi olmayan stil boş kalır (zorlama yok). Hiç yoksa v2 sonucu "0 strateji"dir ve holdout AÇILMAZ.

### 6.3 Mühür
`sonuclar/evren/v2/set_muhru.json`: set listesi, ayarlar, s, havuz/eleme/test/sağlamlık dosyalarının sha256'ları,
maliyet tablosu hash'i, bu dosyanın sha256'sı, git commit, strateji kaynak + ortak motor modülü hash'leri (v1 mühür
sürüm 3 kapsamı). Mühürden sonra geliştirme aşamaları yazamaz.

---

## 7. Aşama 6 — Holdout (bir kez, set düzeyinde)

1. Mühür doğrulanır (uyuşmazlık = DUR). Günlüğe "başladı" yazılır; kayıt varsa ikinci koşu açık hata.
2. Mühürlü set, mühürlü ayarlar ve s ile, aynı sabit evrende, 2025-11-08 → o gün mevcut veri sonu (tarih kayda yazılır)
   tek kasada koşulur. Yalnız girişi ≥ 2025-11-08 olan işlemler sayılır (ısınma için eski veri okunur).
3. **Set kapısı (ikisi de şart):**
   - set net getirisi > 0 (tek kasa, maliyet ×1, TradFi funding dahil);
   - havuzlanmış rastgele-giriş testi p_set ≤ **0.05**. T_set = setteki tüm stratejilerin holdout işlemlerinin Σ R'si.
     Sıfır dağılımı: her strateji için 5.1 kuralıyla (çeyrekler holdout içinde; holdout sınırını aşan çeyrek kesilir)
     B = 5.000 çekim, tohum `hset`; b'inci set çekimi = stratejilerin b'inci çekimlerinin toplamı. Portföy satırı sette
     ise onun katkısı kendi testindeki standartlaştırılmış fark olarak DEĞİL, ayrı raporlanır ve set p'sine girmez
     `[v2 kararı]`; set kapısının net > 0 şartına girer.
4. **Strateji budaması (kapı değil):** set kapısı GEÇTİYSE; holdout neti ≤ 0 **veya** kendi K2 p'si (B = 2.000, tohum
   `hk2`) > 0.25 olan strateji setten çıkarılır; yerine yenisi alınmaz. Set kapısı, budamadan ÖNCEKİ mühürlü set
   üzerinden değerlendirilir `[v2 kararı]`.
5. Set kapısı kalırsa: bu set paper'a gitmez; holdout'a bakılarak ayar/eşik/set değiştirilmez; sonuç kayda geçer; 0.3
   gereği yeni tasarım denenmez.
6. Rapor: strateji bazında net, PF(R), işlem sayısı, K2 p; `kilit_gorulmus` işareti; evren üyeliğinin 2026-11-07'de
   sabitlendiği (ileriyi görme) notu.

Beklenen özellik: genel "avantaj yok" durumunda yanlış geçme ≤ %5.

---

## 8. Aşama 7 — Paper (iki ayrı karar)

Sanal kasa, günlük üyelik kuralı, sert limitler uygulanır. Başlangıçta koni sabitlenir (set geliştirme günlük MTM
getirisi × s; blok 20; 2.000 çekim; tohum `boot`).

**8.1 Sadakat (ilk 28 gün).** (a) Eşleşme: aynı dönem için backtest tekrarının ürettiği işlemler ile paper işlemleri
(aynı sembol, yön, giriş mumu) — iki yönde de ≥ %95; (b) gerçekleşen kayma + komisyon toplamı ≤ modelin 1.5 katı;
(c) kill switch / kaldıraç / stop riski ihlali yok. Biri kalırsa: durdur, düzelt, paper sıfırdan başlar.

**8.2 Performans.** En az **84 gün** VE set toplamında ≥ **60** kapanmış işlem. Değerlendirme anında set özsermayesi
koninin %5–%95 bandında olmalı. İzleme: herhangi bir gün sonunda özsermaye %5 bandının altına inerse → duraklat +
inceleme (yeni giriş yok, açık pozisyonlar kendi kurallarıyla kapanır); devam kararı kullanıcıda. Kesinti kuralı
(≤ 24 saat; aşan süre kadar değerlendirme kayar) mevcut karardaki gibi.

**8.3 Canlı.** Paper geçse bile canlıya geçiş yalnız kullanıcı onayıyla; küçük bütçe; büyütme kuralı o gün ayrıca yazılır.

---

## 9. Kardeş evren (yalnız rapor, kapı değil) `[v2 kararı]`

Amaç: sağlam keşiflerin evrende OLMAYAN enstrümanlarda, geliştirme döneminde, varsayılan ayarla davranışı. Yalnız
swing 1d; maliyet: sınıfın en pahalı satırı (hisse: DK_NVDA, kripto: ZECUSDT, endeks: DK_SPX, döviz: DK_XAU satırı).

- **ABD hisse (sıralı liste; Dukascopy 1h verisi 2018-01-01 veya öncesinde başlayan ilk 20):** ABT, ACN, ADBE, AIG,
  AMGN, AMT, AXP, BA, BAC, BK, BKNG, BLK, BMY, C, CAT, CHTR, CL, CMCSA, COF, COP, COST, CRM, CSCO, CVS, CVX, DE, DHR,
  DIS, DUK, EMR.
- **Kripto (Binance USDⓈ-M perp):** AVAX, DOT, LTC, UNI, NEAR, APT, ATOM, ETC, FIL, AAVE.
- **Endeks (Dukascopy):** S&P 500, Nasdaq 100, DAX, Nikkei 225.
- **Döviz (Dukascopy):** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF.

Verisi bulunmayan enstrüman dışarıda kalır ve raporlanır; yerine başkası eklenmez. Rapor: strateji başına kardeş evren
PF(R), Σ R, işlem sayısı. Holdout dönemi kardeş evrende de OKUNMAZ.

---

## 10. Kod eşlemesi (kodlama ajanları için)

v1 modülleri DEĞİŞTİRİLMEZ (v1 sonucu yeniden üretilebilir kalmalı); v2 yeni modüllerde, v1 işlevlerini çağırarak yazılır.

| Kural | Modül (yeni, aksi yazılmadıkça) | Not |
|---|---|---|
| 1 sabitler, tohum | `motor/arastirma/v2/sabit.py` | tek kaynak; başka yerde sayı yok |
| 1.2 TradFi funding | `motor/arastirma/evren_maliyet.py` (+sütun), `motor/backtest/motor.py` (sabit oranlı funding yolu) | v1 tablo hash'i ile koşan eski yol bozulmaz |
| 2 havuz, küme, m | `motor/arastirma/v2/havuz.py` + `stratejiler/havuz_v2.csv` | mühür: `havuz_muhru.json` |
| 3 ham + MTM yolu | `motor/arastirma/v2/ham.py` (`wf_evren.ham_gorev`'i `yalniz_varsayilan` ile sarar) | çıktı `v2/ham/`, `v2/mtm/` |
| 4 eleme E1–E5 | `motor/arastirma/v2/eleme.py` | `secim.yeniden_oyna` + `wf_evren.oynatma_tablosu` |
| 5 K2 uyarlamalı, BH/BY | `motor/arastirma/v2/test.py` | `evren_k2` çekirdeği; pencere = takvim çeyreği |
| 5.5 SPA | `motor/arastirma/v2/spa.py` | yalnız rapor |
| 6.1 S1–S4 | `motor/arastirma/v2/saglamlik.py` | S4 endeksi `v2/rejim.py` |
| 6.2 set, s | `motor/arastirma/v2/set.py` | |
| 6.3 mühür, 7 holdout | `motor/arastirma/v2/holdout.py` | `wf_evren_holdout` mühür/günlük mantığı; holdout verisini okuyan TEK modül |
| 8 paper kabul | `motor/canli/` kabul/dersler modülleri | sadakat + performans ayrı alan |
| 9 kardeş evren | `motor/arastirma/v2/kardes.py` | okuma `bit = HOLDOUT_BAS` ile kesilir |
| CLI | `python -m motor.arastirma.v2 {havuz,ham,eleme,test,saglamlik,set,holdout,rapor}` | sıra zorunlu; önceki aşamanın mührü yoksa açık hata |

## 11. Kabul testleri (kural başına; hepsi `testler/` altında, sentetik veriyle — gerçek holdout verisi kullanılmaz)

| Kural | Test |
|---|---|
| 0.4 | v2 geliştirme aşamalarının hiçbiri `kilit_ac=True` / `donem="holdout"` ile okuma yapmaz (okuyucu sahte nesneyle sayılır); mühür yokken `holdout` açık hata; ikinci `holdout` çağrısı açık hata |
| 1 | tohum işlevi deterministik; aynı girdiyle iki koşu bayt-bayt aynı çıktı; `sabit.py` dışındaki v2 modüllerinde eşik sabiti yok (kaynak taraması) |
| 1.1 | ham koşu yalnız `adaylar[0]`'ı koşar; ızgara adayı koşarsa test kalır |
| 1.2 | DK_ long 16 saat → 2 × %0.01 nominal düşer; DK_ short → 0; kripto → gerçek seri; ×2 koşusunda funding çarpılmaz |
| 2.3–2.4 | klon kuralı ve tf kuralı örnek kayıtlarda beklenen satırı üretir (`4h` var/`1d` yok → 4h; boş → 1d) |
| 2.7 | korelasyon 0.71 + aynı etiket/alt etiket → aynı küme; 0.71 + farklı alt etiket → ayrı; ortak hafta 99 → ayrı; temsilci = en az parametreli, eşitlikte alfabetik |
| 2.10 | havuz 300 satır → m = 939; 1000 satır → m = 1000 |
| 3 | MTM yolunun son değeri = işlemin R'si; açık gün sayısı = takvim günü; gelecekteki mumu okumaz (kesilmiş veriyle aynı sonuç) |
| E1–E5 | her kapı için sınırın bir altı kalır / tam sınır geçer (PF 1.199 kalır, 1.2 geçer; 199 işlem kalır; 9 enstrüman kalır; tek enstrümana/tek yıla bağlı sentetik strateji E3'ten kalır; sınıf payı %14.9 kalır; `kill_olayi=1` kalır); NaN kalır |
| 5.1 | rastgele giriş aynı enstrüman/yön/çeyrek içinde kalır; çıkış kuralları stratejininkiyle aynı; avantajsız sentetik stratejide p dağılımı tekdüze (KS testi, 400 tohum) |
| 5.3 | p ≤ 0.02 → 2. aşama yeni tohumla koşar ve nihai p yalnız 2. aşamadan; p > 0.02 → koşmaz; elenen/hatalı satır p = 1 |
| 5.4 | bilinen p vektöründe BH elle hesapla aynı; m havuz mühründen okunur; eşitlikte alfabetik |
| S1–S4 | sınır testleri (medyan 1.1 geçer, 1.099 kalır; en düşük 0.899 kalır; komşu 1 → kalır); S4: ayı günü tanımı d−1 verisini kullanır (d günü fiyatı değişince etiket değişmez); 19 işlem → "ölçülemedi = geçti" + bayrak |
| 6.2 | stil başına ≤ 3; aynı küme/aynı etiketten ikinci alınmaz; sıra p → PF×2 → alfabetik; s en büyük uygun değer; hiçbiri uymuyorsa set yok |
| 6.3 | mühürlü dosyalardan biri değişince holdout DUR |
| 7 | set kapısı budamadan önceki set üzerinden; p_set = 0.051 kalır; net ≤ 0 kalır; budamada yerine yenisi alınmaz; kapı kalınca paper girdisi üretilmez |
| 8 | eşleşme %94.9 → kalır; kayma 1.51× → kalır; 83 gün ya da 59 işlem → "değerlendirilemez"; bant altı → duraklat olayı |
| 9 | kardeş evren okuması `HOLDOUT_BAS` sonrasını döndürmez; eksik enstrüman raporlanır, yerine ekleme yok |

---

## English technical notes

- Family: one hypothesis per (strategy, primary tf) at default parameters; `m = max(|pool_v2|, 939)`.
- Screen-then-test validity: for a true null i, `p'_i = p_i·1{pass} + 1{fail}` satisfies `P(p'_i ≤ u) ≤ u`; BH(q=0.10)
  over m; BY reported as the arbitrary-dependence bound.
- Two-stage Monte Carlo p: stage-2 p uses only fresh draws (independent seed), so it is a valid p-value conditional on
  entering stage 2; lines not entering keep the stage-1 p (> 0.02), which can never be a BH rejection for m ≥ 939 unless
  k ≥ 188, i.e. effectively never.
- K2 null conditions on instrument, direction, stop multiple, exit rules and calendar quarter; statistic is pre-replay
  ΣR; profitability under hard limits is enforced separately by E1/E5.
- Holdout set test: pooled ΣR vs. sum of per-strategy randomisation draws (index-aligned), B = 5,000; size ≤ 0.05 under
  the global null, further reduced by the net > 0 condition. Evaluated on the sealed, unpruned set.
- Sizing: `s` is the largest grid value with bootstrap 95th-percentile max drawdown ≤ 15% (stationary bootstrap, mean
  block 20, 2,000 draws) on `s ×` daily MTM returns of the s = 1 replay; down-scaling only.
- Not gates in v2: Sharpe, max DD, PF ex-top-5%, instrument win ratio, single-instrument share, cost ×3, K3, PBO, DSR.
