# İlerleme Kaydı (oturum devamlılığı için)

Bu dosya 15 dakikalık kontrol mekanizmasının kaldığı yerden devam edebilmesi için tutulur.

## Durum
- [x] 1. PDF metinleri `metinler/` altına .md olarak çıkarıldı (35 dosya)
- [x] 2. Veri kaynağı: oturum proxy'si Yahoo/Binance'i engelliyor → veriler GitHub Actions
      (`.github/workflows/fetch-data.yml`) ile çekilip `data/raw/` altına commit ediliyor.
      Kaynaklar: Binance (data-api.binance.vision) kripto, Yahoo Finance hisse/emtia.
- [x] 3. Doküman analizi → ortak stratejiler (`STRATEJILER.md`)
- [x] 4. Backtest motoru (`swing/`)
- [x] 5. Strateji iyileştirme döngüsü — HEDEFLER SAĞLANDI (birleşik KO %56,1, yıllık %29,1, maks. DD −%12,6)
- [x] 6. Sonuç raporu (`SONUCLAR.md`), güncel sinyal taraması (`swing/tarama.py`), günlük iş akışı

## Notlar
- Veriyi yeniden çekmek için: `data/GUNCELLE` dosyasını değiştirip push et.
- Seçili parametreler: `swing/ayarlar.py`. Sistem raporu: `python -m swing.sistem`.
- Günlük sinyal iş akışı (`gunluk-sinyal.yml`) zamanlanmış olarak yalnızca varsayılan dalda çalışır;
  bu dal main'e birleştirilince devreye girer (o zamana kadar elle tetiklenebilir).
- Durum: tamamlandı. 15 dk kontrol mekanizması kapatıldı.
