# Ar-Ge alt projesi (5 enstrüman) — DURUM: DENETİM BEKLİYOR (kapatılmadı)

Tarih: 2026-11-07. Dal: `claude/haiku-arge-5-enstruman`. Ana proje (`claude/adoring-maxwell-q7t60g`, 198bafd) değiştirilmedi.

Not: Bu dosya önce "kapatıldı" diye yazılmıştı; karar denetçiye/kullanıcıya aittir. Kapanış kararı verilmedi.

## Ne yapıldı
- Veri: BTCUSDT (Binance, 2019-12 → 2025-10), XAUUSD (Dukascopy saatlik 2019-12 → 2025-10; TradingView günlük/4s),
  SPX ve Brent (Dukascopy saatlik 2010/2011 →; TradingView günlük), XU30 (TradingView günlük 2010 →; saatlik 2024 →).
  Hepsi 2025-11-01 öncesi. Ayrıntı: `VERI_DURUM.md`, `VERI_EK.md`.
- Elenen havuz (120 strateji; karar 13'ü hiç geçmemiş) 5 enstrümanda WF: swing 420, daytrade 380, scalp 80 koşu.
  Geçen: swing 1 (altın günlük), daytrade 2 (XU30 saatlik). Scalp 0.
- Sağlamlık: WF'de geçen 3 aday — 0 geçti.
- Aşama 4 (sınırdaki adaylar, ön kayıtlı 12 varyant): WF'de 5 geçti, sağlamlıkta 5'i de kaldı.

## Denetçiye bırakılan sorular
1. Bu 5 enstrümanda elenen stratejilerden sağlam aday var mı? (Bugünkü cevap: hayır.)
2. Alt projeye devam mı, kapatma mı? (Karar denetçide/kullanıcıda.)
3. XU30 saatlik için daha uzun veri aranacak mı? (Şu an yalnız 2024 →, 9 ay OOS.)
4. Ana proje kararı (karar 22 evreni, kilit testi sonrası paper trading) bu alt proje sonucundan etkilenir mi? (Ben değiştirmedim.)

## Kanıt dosyaları
- Walk-forward: `wf/haiku_elenen_swing.csv`, `wf/haiku_elenen_daytrade.csv`, `wf/haiku_elenen_scalp.csv`, `wf/haiku_varyant.csv`
- Sağlamlık: `saglamlik/haiku_elenen_swing.parquet`, `saglamlik/haiku_varyant.parquet` ve daytrade çıktıları
- Özetler: `SONUC_SWING.md`, `SONUC_OZET_2.md`, `SONUC_GELISTIRME.md`
- Ön kayıt: `GELISTIRME_ON_KAYIT.md`
- Deneme sayısı: `deneme_kaydi.jsonl` (787 kayıt; çoklu test düzeltmesi için kullanılmalı)

## Sınırlar
- XU30 saatlik OOS yalnız 2025-01 → 2025-09 (3 pencere, ~50 işlem); varyantlar aynı işlemleri paylaşıyor.
- Dukascopy ve Yahoo'ya erişim hız sınırlı; TradingView/borsapy üçüncü taraf ve resmi API değil.
- Kilit: BTC ve altın daha önce kilit testinde kullanıldı; temiz test dönemi kalmadı.
