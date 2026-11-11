# v3 aile temsilcileri — ÖN KAYIT (TASLAK)

Tarih: 2026-11-11. Hazırlayan: lider (Claude Opus). Durum: **TASLAK, kullanıcı onayı bekliyor.**
Onaydan sonra bu dosya ve "dondurma commit"i (bölüm 6) değişmez; sonuç görüldükten sonra hiçbir sayı, eşik ya da ayar
değiştirilmez. Değişiklik gerekirse "Güncelleme N (sonuç sonrası)" başlığıyla eklenir, eski metin silinmez.

---

## 0. Beyanlar

**0.1 v2 kuralı 0.3 ile uyum (kullanıcı kararı 2026-11-11, seçenek A).** ON_KAYIT_V2 0.3: "bu veriler üzerinde v3
değerlendirilmez; yeni fikir ancak yeni (ileri) veriyle denenir." Bu yüzden:
- **Geçmiş veri koşusu yalnız ELEMEDİR, kanıt değildir.** Kötü olanı ayıklar; geçen strateji "işe yarıyor" sayılmaz.
- **Kanıt yalnız ileri veridir:** elemeyi geçenler ayrı paper hesaplarında (bölüm 4) değerlendirilir.
- Geçmiş koşunun sonucuna bakılarak ayar, kural, evren ya da eşik değiştirilmez.

**0.2 v2 dokunulmazdır.** v2 seti, mühürleri (`sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/`) ve çalışan
v2 paper'ı bu çalışmadan etkilenmez. v3 paper'ı ayrı hesaplarda koşar.

**0.3 Değişmez proje kuralları.** SERT_LIMITLER (işlem başı %1 maliyet dahil, toplam açık stop riski %5, brüt 3x,
günlük −%3, kill −%20) aynen. Martingale / DCA / ortalama düşürme / stopsuz ızgara yok. Lookahead yok. Sessiz
try/except yok (hata = satır "hata", elenmiş sayılır). Canlı para her zaman kullanıcı onayı.

**0.4 Aile ve çoklu test.** Aile = 9 temsilci (bölüm 1). Aynı ailenin diğer kodlu varyantları bu turda koşulmaz;
yalnız temsilcisi paper'da kabul alırsa ayrı ön kayıtla ele alınır. `saatlik-asiri-tepki` (De Nicola) birincil metin
okunamadığı için bu turda yok (kullanıcı kararı).

---

## 1. Aile (9 satır) ve sabit ayarlar

Her satır TEK ayarla koşar: strateji sınıfının `varsayilan_parametreler`'i, dondurma commit'indeki haliyle. Ayrıntılı
kural ve varsayımlar: `stratejiler/v3_adaylar/kodlama_v3.csv` (dondurma commit'i), kaynak değerleri:
`stratejiler/v3_adaylar/on_kayit_girdi.csv`.

| # | Kart | Strateji | Tür | tf | Evren |
|---|---|---|---|---|---|
| 1 | donchian-ansambl-vol-hedef__zarattini | `pf__v3-donchian-ansambl` | portföy | 1d | V3_KRIPTO (13) |
| 2 | funding-7g-haftalik-tercil__vine | `pf__v3-funding-7g-haftalik-tercil` | portföy | 1d | V3_KRIPTO (13) |
| 3 | fip-kesitsel-momentum__baptoudur | `pf__v3-fip-kesitsel-momentum` | portföy | 1d | V3_KRIPTO (13) |
| 4 | kripto-max-piyango-kesit__ozdamar | `pf__v3-kripto-max-piyango` | portföy | 1d | V3_KRIPTO (13) |
| 5 | vol-yonetimli-long__moreira | `pf__v3-vol-yonetimli-long` | portföy | 1d | HEPSI (13: kripto+hisse+emtia) |
| 6 | gunici-momentum-noise-alani__zarattini | `v3__gunici-momentum-noise-alani` | tek grafik | 30m | DK_SPX |
| 7 | btc-gecelik-max10-hafta-sonu__dujava | `v3__btc-gecelik-max10-hafta-sonu` | tek grafik | 1h | BTCUSDT |
| 8 | cuma-15-est-tutma-saatlik__miralles | `v3__cuma-15-est-tutma` | tek grafik | 1h | kartın evreni (kodlama_v3.csv) |
| 9 | pre-fomc-surunme__delphic | `v3__pre-fomc-surunme` | tek grafik | 15m | **DK_SPX (ana)**; BTCUSDT yalnız rapor |

V3_KRIPTO = BTC, ETH, BNB, XRP, SOL, TRX, ZEC, HYPE, DOGE, LINK, ADA, XLM, BCH (USDT perp). Sabit liste, bugünün
sembollerinden: **hayatta kalma yanlılığı vardır, sonuç yukarı yanlı olabilir** (beyan).

### 1.1 Kaynaktan bilinen sapmalar (beyan; düzeltilmeyecek)
Tur 8 (`kod_kontrol_tur8.csv`) bulguları; sonuç görülmeden kabul edildi:
- **ATR stopları kaynakta yok** (donchian ×3, funding ×3, FIP ×3, kripto-max ×3, vol-yönetimli ×2, btc-gecelik ve
  noise günlük ATR, cuma-15 ×2, pre-FOMC ×2): motor stopsuz girişi reddettiği için "bizim eklememiz".
- **Boyut:** motor işlem başı %1 risk / stop mesafesiyle ve %5 toplam stop riski tavanıyla boyutlar. Portföy
  stratejilerinde fiili brüt maruziyet kaynak hedefinin (1,0) kabaca yarısı olabilir. Mutlak getiri ve düşüş kaynakla
  karşılaştırılamaz; Sharpe büyük ölçüde ölçekten bağımsızdır.
- **FIP:** skor kaynak repodaki formül (`işaret(mom90) × düzgünlük`); makaledeki (Da-Gurun-Warachka) "momentum içinde
  düzgünlük" sıralaması değildir. "Repo kuralı" olarak test edilir.
- **vol-yönetimli:** ağırlık std'nin tersi (vol hedefleme, sabit %20, tavan 1, 1/n); varyansın tersi değil; tüm
  sembollerde √252.
- **donchian:** ay sonu evren seçimi ve hacim filtresi yok (sabit 13 sembol).
- **pre-FOMC:** 2013–2015 toplantılarının saati takvimde yok, bu toplantılarda işlem yok.

### 1.2 Kıyas koşuları (yalnız rapor, eleme kapısı değil)
Kaynağa yakın sürüm: stopu çok geniş (ATR × 20) "pratikte stopsuz" koşu; tek grafiklerde kaynak boyutu yerine
sabit risk. Sonuç yalnız rapora yazılır.

---

## 2. Sabitler

| Ad | Değer |
|---|---|
| Veri dönemi | her satırın verisinin başladığı gün → koşu günündeki veri sonu (tarih kayda yazılır). v2 holdout dönemi de okunur; 0.1 gereği bu kanıt değildir |
| Isınma | stratejinin en uzun geri bakışı kadar; ısınmadaki sinyaller sayılmaz |
| Maliyet | `sonuclar/evren/maliyet_tablosu.csv` (v2 ile aynı dosya, sha256 kayda) + DK_ long funding (ON_KAYIT_V2 1.2) |
| Maliyet çarpanı | ×1 (ana) ve ×2 (eleme kapısı) |
| Tohum | 20261111; satır tohumu `zlib.crc32(f"{strateji}|{asama}".encode()) ^ 20261111` |
| Rastgele-giriş testi | ON_KAYIT_V2 5.1 (tek grafik, takvim çeyreği) / 5.2 (portföy, rastgele ağırlık); B = 2.000 |
| Çıktı dizini | `sonuclar/v3/` |

---

## 3. Eleme (geçmiş veri; hepsi şart; NaN = geçmez)

**Tek grafik (satır 6–9):**

| # | Kapı | Tanım |
|---|---|---|
| V1 | Kârlılık | maliyet ×2'de net > 0 **ve** maliyet ×1'de PF(R) ≥ 1.2 (v2 ile aynı) |
| V2 | Örnek | kapanan işlem ≥ 60 (pre-FOMC: ≥ 40) |
| V3 | Yoğunlaşma | toplam R'si en yüksek takvim yılı çıkarılınca Σ R > 0 |
| V4 | Rastgelelikten ayrışma | rastgele-giriş testi p ≤ 0.10 |
| V5 | Hayatta kalma | maliyet ×1'de kill olayı yok |

**Portföy (satır 1–5):**

| # | Kapı | Tanım |
|---|---|---|
| P1 | Kârlılık | maliyet ×2'de net > 0 **ve** maliyet ×1'de günlük Sharpe (yıllık) ≥ 0.5 |
| P2 | Örnek | dönem ≥ 1095 gün **ve** ≥ 20 yeniden dengeleme |
| P3 | Yoğunlaşma | en iyi takvim yılı çıkarılınca net > 0 |
| P4 | Rastgelelikten ayrışma | rastgele-ağırlık testi p ≤ 0.10 |
| P5 | Hayatta kalma | maliyet ×1'de kill olayı yok |
| P6 | Kıyas (yalnız vol-yönetimli) | aynı evrenin eşit ağırlıklı al-tut'una göre Sharpe farkı > 0 |

Çoklu test düzeltmesi bilerek yok: eleme kanıt değildir (0.1); yanlış geçen strateji paper'da elenir. p = 0.10
gevşek seçildi ki gerçek bir etki elemede kaybolmasın.

Rapor (kapı değil): Sharpe, max düşüş, maliyet ×3, yıllara göre net, kıyas koşusu (1.2), işlem sayısı.

---

## 4. Paper (KANIT)

Elemeyi geçen her satır kendi paper hesabında (10.000 USD sanal) çalışır. v2 paper'ından ayrı.

**4.1 Başlangıç.** Bir sonraki günlük kapanışta (00:00 UTC) başlar; `islem_baslangic` verilir (başlangıçtan önceki
mumdan dolum yok; v2 başlangıç bayat dolumu dersi). Koni: eleme koşusunun günlük MTM getirisi, blok 20, 2.000 çekim.

**4.2 Sadakat (ilk 28 gün).** Aynı dönemin backtest tekrarı ile paper işlemleri ≥ %95 eşleşir (iki yönde); kayma +
komisyon ≤ modelin 1,5 katı; sert limit ihlali yok. Kalırsa: durdur, düzelt, paper sıfırdan başlar.

**4.3 Kabul (strateji başına).** Hepsi şart:
- en az **84 gün** ve kapanan işlem ≥ **20** (portföy: ≥ 12 yeniden dengeleme). Düşük frekanslı satırlar (pre-FOMC,
  yılda ~8 olay) bu sayıya ulaşana dek değerlendirilemez; süre uzar;
- paper net > 0 (maliyet dahil);
- özsermaye koninin %5 alt bandının üstünde.
İzleme: herhangi bir gün %5 bandının altına inerse duraklat + inceleme; devam kararı kullanıcıda.

**4.4 Canlı.** Kabul alan strateji için bile canlı para yalnız kullanıcı onayıyla; B18 (pano erişim güvenliği)
canlıdan önce kapanır.

---

## 5. Sonuç beyanı
- Eleme sıfır strateji verirse v3 sonucu "0"dır; eşik gevşetilmez, yeni varyant denenmez.
- Rapor: her satır için kapı sonuçları, 1.1 sapmaları, kıyas koşusu. Geçen ve kalan aynı ayrıntıda yazılır.

## 6. Dondurma
Onaydan sonra: (a) bu dosyanın sha256'sı, (b) dondurma commit'i (9 stratejinin kodu ve `kodlama_v3.csv`), (c)
maliyet tablosu sha256'sı `sonuclar/v3/dondurma.json`'a yazılır. Koşu bu commit'ten yapılır; eleme koşusu başladıktan
sonra strateji kodu değişirse koşu geçersizdir.
