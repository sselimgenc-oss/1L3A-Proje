# Veri durumu (5 enstrüman) — güncel

Tarih: 2026-11-07. Kilit: 2025-11-01 00:00 UTC; hiçbir parquet bu tarihten sonrasını içermez (kontrol edildi).
Üretici: `sonuclar/haiku_arge/veri_cek_tv.py` (borsapy → TradingView). Manifest: `veri_manifest.csv`.
Parquet'ler `veri/mumlar/<SEMBOL>/<aralik>.parquet` (gitignore'lu, repoya girmez).

| Enstrüman | Aralık | Kaynak | Satır | İlk | Son |
|---|---|---|---|---|---|
| XU30 (BIST 30) | 1d | borsapy BIST:XU030 | 3973 | 2010-01-04 | 2025-10-31 |
| XU30 | 1h | borsapy BIST:XU030 | 4554 | 2024-01-02 | 2025-10-31 |
| SPX (S&P 500 endeksi) | 1d | borsapy SP:SPX | 2348 | 2016-07-01 | 2025-10-31 |
| SPX | 1h | borsapy SP:SPX | 4959 | 2023-01-03 | 2025-10-31 |
| XAUUSD | 1d | borsapy OANDA:XAUUSD | 4097 | 2010-01-01 | 2025-10-31 |
| XAUUSD | 4h | borsapy OANDA:XAUUSD | 4391 | 2023-01-02 | 2025-10-31 |
| XAUUSD (Dukascopy, `DK_XAU`) | 1h | Dukascopy | 35011 | 2019-12-01 | 2025-10-31 |
| UKOIL (Brent) | 1d | borsapy TVC:UKOIL | 4084 | 2010-01-04 | 2025-10-30 |
| UKOIL | 1h | borsapy TVC:UKOIL | 4766 | 2025-01-02 | 2025-10-31 |
| BTCUSDT | 1h, 5m, 15m, 30m, 4h, 1d | Binance arşivi | 51k–614k | 2019-12-31 | 2025-10-31 |

## Sınırlar (önemli)
- **Saatlik geçmiş kısa:** TradingView yaklaşık 5000 bar döndürüyor. SPX 1h 2023-, UKOIL 1h 2025-, XU30 1h 2024-.
  Daytrade/scalp testleri bu nedenle çok kısa; saatlik işlemler için yeterli uzunlukta değil.
- **Altında 1h yok** (TradingView). 1h için Dukascopy `DK_XAU` (2019-12 → 2025-10) kullanılır; ama 4h/1d ile
  TradingView verisi ayrı bir kaynak. İki kaynağı karıştırmamak için adlandırma ayrı tutuldu.
- **SPX 2016 öncesi yok.** Alternatif `CAPITALCOM:US500` 2010'dan geliyor ama SP:SPX ile günlük getiri
  korelasyonu yalnız 0.97 (tarih hizalama farkı olabilir); karıştırılmadı, yedek olarak not.
- **Dakikalık (5m/15m) TradingView'de yok** → scalp, TradingView enstrümanlarında (SPX, UKOIL, XAUUSD, XU30) yapılamaz.
- **Kaynak niteliği:** TradingView ve borsapy üçüncü taraf, resmi API değil; fiyatlar CFD/endeks, kaynağa göre değişebilir.
  Çıkış ve giriş fiyatı varsayımları bu belirsizliği taşır.
- **Volume:** TradingView hacmi enstrümanlar arası karşılaştırılamaz; `quote_hacim = hacim*kapanış` yaklaşık, `islem_sayisi = 0`.
- **Günlük mum sınırı:** TradingView'in yerel gün zamanı, yerel tarihin UTC gece yarısına yazıldı.

## Ağ
- Politika reddi (403) veren hostlar: `data.tradingview.com` → ortama eklendi (kullanıcı onayı, Default ortamı).
  Diğerleri (isyatirim, borsaistanbul, kap, tcmb, investing) 403; kullanılmadı.
- Dukascopy: `datafeed.dukascopy.com` ortam listesinde ama bağlantı tünel kapanması (relay), arada 429 veriyor.
- Yahoo: `query1/2.finance.yahoo.com` listede ama 429 (hız sınırı); kullanılmadı.
