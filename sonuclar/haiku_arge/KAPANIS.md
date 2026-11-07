# Ar-Ge alt projesi (5 enstrüman) — kapanış notu

Tarih: 2026-11-07. Dal: `claude/haiku-arge-5-enstruman`. Ana proje (`claude/adoring-maxwell-q7t60g`, 198bafd) değiştirilmedi.

## Ne yapıldı
- Veri: BTCUSDT (Binance, 2019-12 → 2025-10), XAUUSD (Dukascopy saatlik 2019-12 → 2025-10; TradingView günlük/4s),
  SPX ve Brent (Dukascopy saatlik 2010/2011 →; TradingView günlük), XU30 (TradingView günlük 2010 →; saatlik 2024 →).
  Hepsi 2025-11-01 öncesi. Ayrıntı: `VERI_DURUM.md`, `VERI_EK.md`.
- Elenen havuz (120 strateji; karar 13'ü hiç geçmemiş) 5 enstrümanda WF: swing 420, daytrade 380, scalp 80 koşu.
  Geçen: swing 1 (altın günlük), daytrade 2 (XU30 saatlik). Scalp 0.
- Sağlamlık: WF'de geçen 3 aday — 0 geçti.
- Aşama 4 (sınırdaki adaylar, ön kayıtlı 12 varyant): WF'de 5 geçti, sağlamlıkta 5'i de kaldı → geliştirilemedi.

## Sonuç
- Bu 5 enstrümanda ve bu veri ile, elenen stratejilerden **sağlamlıktan geçen tek aday yok**.
- En yakın adaylar (sağlamlıkta kıl payı): SPX günlük `rsi-ema-vol` (rastgele giriş p = 0.054, eşik 0.05).
- XU30 saatlik sonuçları 2025-01 → 2025-09 (9 ay, ~50 işlem); daha uzun saatlik XU30 verisi bulunamadı.
- Deneme kaydı: 787 kayıt (`deneme_kaydi.jsonl`). Çoklu test düzeltmesi için bu sayı kullanılmalı.

## Neden kapatılıyor
- Alt projenin amacı (elenenleri 5 enstrümanda test edip sağlam olanları bulmak) yerine getirildi; sonuç negatif.
- Geliştirme yolu (varyant) denendi, ön kayıtlı kurallara göre sonuç vermedi.
- Kalan tek umut XU30 saatlik veri; ama bu olsa bile, mevcut adaylar sağlamlıktan geçmedi.

## Ana projeyle ilişki
- Ana projenin kilit testi (`sonuclar/kilit/RAPOR.md`) farklı bir evrende bir set geçirdi (tek-grafik +%17.8, Sharpe 1.21).
  Ana proje bunu paper trading ile doğrulamayı planlıyor; bu alt projenin sonucu o kararı değiştirmez.
- Ana projedeki karar 22 (evren) bu alt projeyle değiştirilmedi.

## Yeniden açma koşulu
- XU30 için ≥ 3 yıl saatlik veri bulunursa veya kullanıcı yeni bir enstrüman/yöntem isterse.

## Çıktılar
Tüm dosyalar bu klasörde ve dalda; hiçbiri silinmedi. Dal ve veri (`veri/mumlar/`, gitignore'lu) yerelde/dalda duruyor.
