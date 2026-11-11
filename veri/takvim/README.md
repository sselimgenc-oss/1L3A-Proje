# FOMC takvimi (`fomc.csv`)

**Kaynak:** federalreserve.gov resmi sayfaları, 2026-11-11'de çekildi.
- 2013-2020: `https://www.federalreserve.gov/monetarypolicy/fomchistorical<yıl>.htm` (yıllık "Historical Materials" sayfaları).
- 2021-2026 (+ 2027 planı): `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`.
- Açıklama saati: her toplantının resmi basın bülteni (`/newsevents/pressreleases/monetaryYYYYMMDDa.htm`) başlığındaki "For release at …" satırı. `kaynak_url` sütunu bu bülten sayfasını (yoksa takvim sayfasını) gösterir.
- Veri elle yazılmadı; sayfalar betikle ayrıştırıldı, her satır sayfadan gelir. Fiyat verisi değildir (kilitli dönem verisiyle ilgisi yok).

**Sütunlar:** `tarih` (açıklama günü, YYYY-MM-DD; iki günlük toplantıda ikinci gün), `aciklama_saati_et` (HH:MM, ABD Doğu saati), `aciklama_utc` (ISO, yaz saati `America/New_York` ile hesaplanıp UTC'ye çevrildi; bültende yazan EST/EDT kısaltması bununla karşılaştırıldı, uyumsuzluk yok), `planli` (evet|hayir), `basin_toplantisi` (evet|hayir|bilinmiyor), `kaynak_url`.
**Eklenen iki sütun (istenenlere ek):** `tip` (`planli` | `plansiz` | `yazili_oylama` | `planli_gelecek`) ve `not`. Beklenen sütunlarla okuyan kod bunları yok sayabilir.

**Satır sayısı:** 121 (110 planlı geçmiş, 5 plansız toplantı/konferans görüşmesi, 5 yazılı oylama [notation vote], 1 gelecek planlı).

## Kontrol: yılda 8 planlı toplantı
2013-2019 ve 2021-2026 yıllarının her birinde 8 planlı toplantı var (2026'nın sonuncusu, 2026-12-09, henüz yapılmadı: `planli_gelecek`, saat ve basın "bilinmiyor").
**2020'de 7:** 17-18 Mart toplantısı sayfada "(cancelled)" ve yerine 15 Mart (Pazar) plansız toplantı yapılıp 17:00 ET'de açıklama yapılmış; iptal edilen toplantı için açıklama olmadığından dosyaya alınmadı.

## Bilinen boşluklar / dikkat
- **2013-2015 planlı toplantılar (24 satır) için saat "bilinmiyor":** bu yılların bültenlerinde yalnız "For immediate release" yazıyor, saat yok. Talimat gereği tahmin edilmedi. (Literatürde 2011 sonrası açıklama saatinin 12:30-14:00 arasında değiştiği geçiyor; bu çalışmada doğrulanmadı.) 2016+ bültenlerinde saat yazılı (çoğu 14:00).
- **Plansız toplantılar:** 2013-10-16 ve 2014-03-04 konferans görüşmelerinde sayfada açıklama linki yok (saat bilinmiyor, basın bilinmiyor). 2019-10: başlık "October 4 (unscheduled)", ancak bülten 2019-10-11 tarihli (tarih = bülten tarihi). 2020-03: "March 2 (unscheduled)" için bülten 2020-03-03 10:00 ET.
- **2020-03-15 bir Pazar** (acil toplantı); haftasonu olması hata değil.
- **Yazılı oylamalar** (2020-03-19, 23, 31, 2020-08-27, 2025-08-22) toplantı değildir; açıklamaları gerçek piyasa olayı olabilir ama "planli = hayir", basın yok. 2020-03-19'un sayfada bülten linki yok.
- `basin_toplantisi`: sayfada "Press Conference" linki var mı diye belirlendi (2019-01'den itibaren her toplantıda var; öncesinde yalnız çeyreklik SEP toplantılarında). Linkin yokluğundan "hayir" çıkarıldı; sayfa eksikse yanlış olabilir.
- 2027 takvimi sayfada var ama dosyaya alınmadı (talimat 2013-2026).
- Ortamdaki betik (ayrıştırma) repoda yok; sonuç `fomc.csv`'dir. Yeniden üretmek için aynı iki sayfa tipi ve bültenler kullanılır.
