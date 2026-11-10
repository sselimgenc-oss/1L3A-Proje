# v3 kartlarını kodlama: Codex görevi

Önce `AGENTS.md`, `CLAUDE.md` ve `DURUM.md` dosyalarını oku. AGENTS.md'deki kesin kurallar burada da geçerli. Özetle:
- Kendi dalında çalış: `codex/v3-kodlama-<parti>`.
- PR aç, PR'ı BİRLEŞTİRME.
- SERT_LIMITLER'e dokunma.
- Mühürlü çıktılara dokunma: `sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/`.
- Lookahead yasak, sessiz try/except yasak.

## Amaç
`stratejiler/v3_adaylar/kartlar/*.json` içindeki kartları mevcut strateji altyapısına kod olarak eklemek. **Yalnız kodlama ve birim testi yapılır.** Backtest, eleme, holdout ya da performans koşusu YAPILMAZ. Testleri ana oturum, önceden kayıt (ON_KAYIT) yazdıktan sonra yapacak.

## Hangi kartlar
- `adaylar.csv` dosyasında `veri_uygun` = true olan kartlar. `oncelik` 1'den başla, sonra 2, sonra 3.
- `veri_uygun` = false olan kartlara dokunma. Yalnız `kodlama_v3.csv` dosyasına `veri_yok` diye yaz.
- Partiler halinde çalış: her PR'da 10-15 kart.

## Nereye
Önce mevcut örneklere bak ve aynı yapıyı izle:
- Tek grafik stratejileri: `motor/strateji/dis/` ve `motor/strateji/swing|daytrade/`. Strateji ayarları `stratejiler/kart_ayarlari/`, biçimi o klasörün README.md'sinde.
- Portföy, kesitsel ve rotasyon stratejileri: `motor/portfoy/stratejiler/` (`kesit.py`, `rotasyon.py`, `cta.py` örnek).
- Yeni modülleri `v3` önekiyle adlandır. Strateji `ad` değeri `v3__<kart_id kısa>` olsun.
- Kart kayda girmeli: `motor/strateji/kayit.py` yeni stratejiyi bulmalı.
- Paylaşılan göstergeler için önce `gostergeler.py`, `gostergeler_b1.py`, `gostergeler_b2.py` ve `pivotlar.py` dosyalarına bak. Aynısı orada varsa yeniden yazma, onu kullan.

## Kartta eksik parametre olursa (ÖNEMLİ)
Birçok kartta "kaynakta alınamadı" ya da "UYARLAMA" yazıyor. Kural:
1. Kaynakta değer varsa (repo kodu, makale) onu kullan. Kaynak linkini kodda yorum olarak yaz. Üçüncü taraf kodu KOPYALAMA; GPL/AGPL koddan yalnız mantığı al.
2. Kaynakta değer yoksa, havuzdaki benzer stratejinin değerini ya da yaygın standart değeri kullan.
3. **Her varsayımı** `kodlama_v3.csv` dosyasının `varsayimlar` sütununa yaz, ayarı da aynı sütunda ver. Örnek: "donchian geriye bakış 20,55,100 (kaynakta yok; havuz donchian-kirilim'den)".
4. Parametre ızgarası kurma. Her kart için TEK ayar seç. En fazla 3 varyant olabilir, o da yalnız kart açıkça varyant listeliyorsa.
5. Bir kural kesin ve ölçülebilir hale getirilemiyorsa kodlama. Durumu `belirsiz` yaz ve nedenini açıkla. Uydurma kural yazma.

## Stop zorunlu
Her strateji pozisyonu açarken stop verir; motor stopsuz girişi reddeder. Kartta stop yoksa, havuzdaki aynı aile stratejilerin stop tipini kullan (çoğunlukla ATR stop) ve bunu varsayımlara yaz.
Martingale, DCA, ortalama düşürme ve stopsuz ızgara yasak.

## Test (her PR'da)
- Her yeni strateji için birim testi yaz. Sentetik veriyle şunları kontrol et: sinyal üretiyor mu, stop var mı, kartın giriş ve çıkış kuralları beklenen yerde mi tetikleniyor.
- `testler/test_lookahead_tum_stratejiler.py` yeni stratejileri de kapsamalı ve geçmeli. Bu test kayıttaki tüm stratejileri tarıyor; kapsamazsa sebebini bul.
- Tam paket geçmeli: `python -m pytest testler -q -p no:cacheprovider`.

## Çıktı
- Kod ve testler.
- `stratejiler/v3_adaylar/kodlama_v3.csv` dosyası, kart başına bir satır:
  `kart_id,strateji_ad,durum(kodlandi|belirsiz|veri_yok|tekrar),modul,varsayimlar,not`
  Bir kart mevcut bir stratejinin neredeyse aynısıysa `tekrar` yaz ve hangisi olduğunu belirt.
- PR açıklaması Türkçe ve sade olsun: kaç kart kodlandı, kaçı belirsiz, en önemli varsayımlar neler.
