# v3 aile temsilcileri — ÖN KAYIT (TASLAK)

Tarih: 2026-11-11. Hazırlayan: lider (Claude Opus); yöntem denetimi: Fable (11 madde, hepsi işlendi).
Durum: **TASLAK, kullanıcı onayı bekliyor.** Onaydan ve dondurmadan (bölüm 6) sonra bu dosya değişmez; sonuç
görüldükten sonra hiçbir sayı, eşik ya da ayar değiştirilmez. Değişiklik gerekirse "Güncelleme N (sonuç sonrası)"
başlığıyla eklenir, eski metin silinmez.

---

## 0. Beyanlar

**0.1 v2 kuralı 0.3 ile uyum (kullanıcı kararı 2026-11-11, seçenek A).** ON_KAYIT_V2 0.3: "bu veriler üzerinde v3
değerlendirilmez; yeni fikir ancak yeni (ileri) veriyle denenir." Bu yüzden:
- **Geçmiş veri koşusu yalnız ELEMEDİR, kanıt değildir.** Kötü olanı ayıklar; geçen strateji "işe yarıyor" sayılmaz.
- Eleme sonucu Sharpe / PF / getiri sayıları hiçbir yerde **performans beklentisi olarak sunulmaz**.
- **Kanıt yalnız ileri veridir** (bölüm 4).
- Geçmiş koşunun sonucuna bakılarak ayar, kural, evren ya da eşik değiştirilmez.

**0.2 v2 dokunulmazdır.** v2 seti, mühürleri (`sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/`) ve çalışan
v2 paper'ı bu çalışmadan etkilenmez. v3 paper'ı ayrı hesaplarda koşar.

**0.3 Değişmez proje kuralları.** SERT_LIMITLER (işlem başı %1 maliyet dahil, toplam açık stop riski %5, brüt 3x,
günlük −%3, kill −%20) aynen. Martingale / DCA / ortalama düşürme / stopsuz ızgara yok. Lookahead yok. Sessiz
try/except yok.

**0.4 Aile ve çoklu test.** Aile = 9 temsilci (bölüm 1). Aynı ailenin diğer kodlu varyantları bu turda koşulmaz;
yalnız temsilci kanıt alırsa ayrı ön kayıtla ele alınır. `saatlik-asiri-tepki` (De Nicola) birincil metin
okunamadığı için bu turda yok (kullanıcı kararı).

**0.5 Gerçek veriyle koşu yok.** 9 satırın kodu yalnız sentetik veriyle (birim testleri) doğrulandı; dondurmadan
önce hiçbiri gerçek mumda koşulmaz (yalnız mum zaman damgası / seans kapsamı okunabilir).

---

## 1. Aile (9 satır) ve sabit ayarlar

Her satır TEK ayarla koşar: strateji sınıfının `varsayilan_parametreler`'i, dondurma commit'indeki haliyle. Ayrıntılı
kural ve varsayımlar: `stratejiler/v3_adaylar/kodlama_v3.csv` (dondurma commit'i); kaynak değerleri:
`stratejiler/v3_adaylar/on_kayit_girdi.csv`. 15m / 30m / 1h seriler 5m verisinden yeniden örneklenir
(`motor/veri/yeniden_ornekle.py`).

| # | Kart | Strateji | Tür | tf | Evren | Eleme dönemi (kapılar) |
|---|---|---|---|---|---|---|
| 1 | donchian-ansambl-vol-hedef__zarattini | `pf__v3-donchian-ansambl` | portföy | 1d | V3_KRIPTO | tüm veri |
| 2 | funding-7g-haftalik-tercil__vine | `pf__v3-funding-7g-haftalik-tercil` | portföy | 1d | V3_KRIPTO | tüm veri |
| 3 | fip-kesitsel-momentum__baptoudur | `pf__v3-fip-kesitsel-momentum` | portföy | 1d | V3_KRIPTO | tüm veri |
| 4 | kripto-max-piyango-kesit__ozdamar | `pf__v3-kripto-max-piyango` | portföy | 1d | V3_KRIPTO | tüm veri |
| 5 | vol-yonetimli-long__moreira | `pf__v3-vol-yonetimli-long` | portföy | 1d | HEPSI (13) | tüm veri |
| 6 | gunici-momentum-noise-alani__zarattini | `v3__gunici-momentum-noise-alani` | tek grafik | 30m | DK_SPX | tüm veri |
| 7 | btc-gecelik-max10-hafta-sonu__dujava | `v3__btc-gecelik-max10-hafta-sonu` | tek grafik | 1h | BTCUSDT | **2024-10-15 →** (kaynağın örneklem sonrası; tüm dönem yalnız rapor) |
| 8 | cuma-15-est-tutma-saatlik__miralles | `v3__cuma-15-est-tutma` | tek grafik | 1h | dondurmada kodlama_v3.csv'deki evren | **2022-01-01 →** (kaynak örneklemi 2016-2021; tüm dönem yalnız rapor) |
| 9 | pre-fomc-surunme__delphic | `v3__pre-fomc-surunme` | tek grafik | 15m | **DK_SPX (ana)**; BTCUSDT yalnız rapor | tüm veri (DK_SPX 5m 2017-01-03'te başlar; 2013-2015 saatsiz, ~78 olay) |

V3_KRIPTO = BTC, ETH, BNB, XRP, SOL, TRX, ZEC, HYPE, DOGE, LINK, ADA, XLM, BCH (USDT perp). Sabit liste, bugünün
sembollerinden: **hayatta kalma yanlılığı vardır, sonuç yukarı yanlı olabilir.**

### 1.1 Kaynaktan bilinen sapmalar (beyan)
Tur 8 (`kod_kontrol_tur8.csv`) bulguları; sonuç görülmeden ele alındı:
- **Düzeltildi (test öncesi):** noise-area: iz süren çıkış her 30 dk kapanışında güncel max(üst bant, VWAP) ile;
  motor stopu yalnız günlük ATR'li felaket stopu. btc-gecelik: MAX(10) = önceki 10 işlem gününün 16:00 ET
  kapanışlarının en yükseği; stop günlük ATR(14)×2.
- **ATR stopları kaynakta yok** (donchian ×3, funding ×3, FIP ×3, kripto-max ×3, vol-yönetimli ×2, noise ve
  btc-gecelik günlük ATR, cuma-15 ×2, pre-FOMC ×2): motor stopsuz girişi reddettiği için "bizim eklememiz".
- **Boyut:** motor işlem başı %1 risk / stop mesafesiyle ve %5 toplam stop riski tavanıyla boyutlar; portföy
  stratejilerinde fiili brüt maruziyet kaynak hedefinin (1,0) kabaca yarısı olabilir. Mutlak getiri ve düşüş kaynakla
  karşılaştırılamaz.
- **FIP:** skor kaynak repodaki formül (`işaret(mom90) × düzgünlük`); makaledeki "momentum içinde düzgünlük"
  sıralaması değildir. "Repo kuralı" olarak test edilir.
- **vol-yönetimli:** ağırlık std'nin tersi (vol hedefleme, sabit %20, tavan 1, 1/n), varyansın tersi değil; tüm
  sembollerde √252.
- **donchian:** ay sonu evren seçimi ve hacim filtresi yok (sabit 13 sembol).
- **pre-FOMC:** 2013–2015 toplantılarının saati takvimde yok; bu toplantılarda işlem yok.

### 1.2 Geniş stop duyarlılığı (yalnız rapor, kapı değil)
Her satır ATR × 20 stopla bir kez daha koşulur. %1 risk boyutlamasında pozisyon 7–10 kat küçülür; bu koşu
"kaynağa yakın" değildir, yalnız stopun sonuca etkisini gösterir.

---

## 2. Sabitler

| Ad | Değer |
|---|---|
| Veri sonu | **2026-10-31 00:00 UTC** (sabit; v2 holdout dönemi de okunur, 0.1 gereği kanıt değildir) |
| Veri başı | her satırın verisinin başladığı gün; kapılar bölüm 1'deki eleme dönemi üzerinden |
| Isınma | stratejinin en uzun geri bakışı; ısınmadaki sinyaller sayılmaz |
| Maliyet | `sonuclar/evren/maliyet_tablosu.csv` (v2 ile aynı, sha256 kayda) + DK_ long funding (ON_KAYIT_V2 1.2) |
| Maliyet çarpanı | ×1 (ana) ve ×2 (kapı); ×3 yalnız rapor |
| Tohum | 20261111; satır tohumu `zlib.crc32(f"{strateji}|{asama}".encode()) ^ 20261111` |
| Rastgele-giriş testi | ON_KAYIT_V2 5.1 (tek grafik, takvim çeyreği); rastgele giriş, gerçek işlemin tutma süresini (mum sayısı) korur; B = 2.000 |
| Rastgele-ağırlık testi | ON_KAYIT_V2 5.2 (yalnız kesitsel portföyler 2–4); B = 2.000 |
| Çıktı dizini | `sonuclar/v3/` |

---

## 3. Eleme (geçmiş veri; hepsi şart; NaN = geçmez)

**Tek grafik (satır 6–9):**

| # | Kapı | Tanım |
|---|---|---|
| V1 | Kârlılık | maliyet ×2'de net > 0 **ve** maliyet ×1'de PF(R) ≥ 1.2 (v2 ile aynı) |
| V2 | Örnek | kapanan işlem ≥ 60 (satır 7 ve 9: ≥ 40) |
| V3 | Yoğunlaşma | toplam R'si en yüksek takvim yılı çıkarılınca Σ R > 0 |
| V4 | Rastgelelikten ayrışma | rastgele-giriş testi p ≤ 0.10 |
| V5 | Hayatta kalma | maliyet ×1'de kill olayı yok |

**Portföy (satır 1–5):**

| # | Kapı | Tanım |
|---|---|---|
| P1 | Kârlılık | maliyet ×2'de net > 0 **ve** maliyet ×1'de yıllık Sharpe ≥ 0.5 |
| P2 | Örnek | dönem ≥ 1095 gün **ve** ≥ 20 yeniden dengeleme |
| P3 | Yoğunlaşma | en iyi takvim yılı çıkarılınca net > 0 |
| P4 | Rastgelelikten ayrışma | **yalnız kesitsel satırlar 2–4:** rastgele-ağırlık testi p ≤ 0.10 |
| P5 | Hayatta kalma | maliyet ×1'de kill olayı yok |
| P6 | Al-tut kıyası | **yalnız satır 1 ve 5:** aynı evrenin eşit ağırlıklı al-tut'u, stratejinin ortalama brüt maruziyetine ölçeklenmiş; strateji Sharpe'ı > kıyas Sharpe'ı |

**Notlar.**
- Çoklu test düzeltmesi bilerek yok (eleme kanıt değil, 0.1). Gerçek süzgeç V4/P4/P6'dır; p ≤ 0.10 hiç avantajı
  olmayan 9 satırdan yaklaşık birini geçirir. Yanlış geçen satır bölüm 4'te elenir.
- Bazı kapılar yapısı gereği hep geçilir (P2; satır 6, 8 için V2; satır 9 için V2). Bilerek tutuldu.
- **Destek ön şartı:** dondurmadan önce rastgele-giriş testinin saat bazlı çıkışları (satır 7–9) desteklediği
  doğrulanır. Desteklenmeyen satır **"hata"** olur (p = 1 değil) ve raporda ayrıca yazılır.
- **Hata:** hata veren satır elenmiş sayılır. Tek istisna: hiçbir metrik üretilmeden önceki altyapı hatası
  (veri okuma, bellek). O satır bir kez yeniden koşulur ve "Güncelleme" olarak yazılır.
- Rapor (kapı değil): Sharpe, max düşüş, maliyet ×3, yıllara göre net, satır 7–8'de tüm dönem, 1.2 koşusu.

---

## 4. Paper (KANIT, ileri veri)

Elemeyi geçen her satır kendi paper hesabında (10.000 USD sanal) çalışır; v2 paper'ından ayrı.

**4.1 Başlangıç.** Bir sonraki günlük kapanışta (00:00 UTC) başlar; `islem_baslangic` verilir (başlangıçtan önceki
mumdan dolum yok). Koni: eleme koşusunun günlük MTM getirisi, blok 20, 2.000 çekim. **Koni elemeden geçmiş (iyimser)
bir geçmişe dayandığı için yukarı yanlıdır.**

**4.2 Sadakat (ilk 28 gün).** Aynı dönemin backtest tekrarı ile paper işlemleri ≥ %95 eşleşir (iki yönde); kayma +
komisyon ≤ modelin 1,5 katı; sert limit ihlali yok. Kalırsa: durdur, düzelt, paper sıfırdan başlar.

**4.3 Ara kontrol: "çürütülmedi" (strateji başına, kanıt DEĞİL).** Her satır için **bir kez**, şu iki şartın ikisi
de ilk sağlandığı günlük kapanışta değerlendirilir: ≥ 84 gün **ve** ≥ 20 kapanan işlem (portföy: ≥ 12 yeniden
dengeleme). İkinci değerlendirme yoktur. 730 günde şartlar oluşmazsa satır **"değerlendirilemedi"**.
- Paper net ≤ 0 **veya** özsermaye koninin %5 alt bandının altında → **"çürütüldü"**, paper durur.
- Aksi halde **"çürütülmedi"**, paper sürer.
- İzleme: herhangi bir gün %5 bandının altına inerse duraklat + inceleme; devam kararı kullanıcıda.
Not: 84 günde avantajı olmayan bir strateji yaklaşık yarı olasılıkla "çürütülmedi" çıkar; bu yüzden bu adım kanıt
değildir. Canlı kararı için bkz. 4.5 (84 gün beklenmesi şart değil).

**4.4 Kanıt testi (BİLGİ; canlı şartı değil).** Paper başlangıcından 365 gün sonra, bir kez:
- Sepet = elemeyi geçen bütün satırların eşit ağırlıklı günlük net getirisi ("çürütüldü" olanlar durduğu günden
  sonra 0 getiriyle sepette kalır).
- Fark serisi = sepet − maruziyet-eşlenmiş al-tut (her satırın kendi evreninin eşit ağırlıklı al-tut'u, günlük brüt
  maruziyetiyle ölçeklenmiş, eşit ağırlıkla toplanmış).
- Ölçüt: fark serisinin tek yönlü t istatistiği ≥ 1.645 (Newey-West, 5 gecikme). Sonuç yalnız raporlanır.

**4.5 Canlı — KULLANICI KARARI (2026-11-11).** Kullanıcı: "2027'den önce canlıya geçeceğim; riskleri ve
stratejilerin kendini kanıtlamadığını biliyorum; 3-5 ay / 1 yıl beklemem." Bu yüzden:
- Canlıya geçiş istatistiksel kanıta (4.3 / 4.4) bağlı DEĞİLDİR; karar kullanıcınındır. Denetçiler (Fable dahil) bu
  kararı bilir ve süre şartı dayatmaz; yalnız riskleri raporlar.
- Canlı için yine de ŞART olanlar (güvenlik, istatistik değil): (a) 4.2 sadakat geçmiş olmalı (sistem doğru
  çalışıyor); (b) 4.3 "çürütüldü" olan satır canlıya alınmaz; (c) SERT_LIMITLER aynen; (d) B18 (pano erişim
  güvenliği) kapalı; (e) borsa API anahtarı para çekme izni KAPALI ve IP kısıtlı; (f) küçük başlangıç bütçesi,
  büyütme kullanıcı kararıyla.

---

## 5. Sonuç beyanı
- Eleme sıfır strateji verirse v3 sonucu "0"dır; eşik gevşetilmez, yeni varyant denenmez.
- Rapor: her satır için kapı sonuçları, 1.1 sapmaları, 1.2 koşusu. Geçen ve kalan aynı ayrıntıda yazılır.

## 6. Dondurma
Önce şunlar gerekir: 9 satırın kodu main'de; testler (tam paket) geçiyor; bölüm 3'teki destek ön şartı doğrulanmış.
Sonra (a) bu dosyanın sha256'sı, (b) dondurma commit'i (9 stratejinin kodu ve `kodlama_v3.csv`), (c) maliyet
tablosu sha256'sı `sonuclar/v3/dondurma.json`'a yazılır. Koşu bu commit'ten yapılır; eleme koşusu başladıktan sonra
strateji kodu değişirse koşu geçersizdir.
