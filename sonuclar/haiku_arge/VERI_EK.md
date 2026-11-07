# Veri eki — Dukascopy SPX ve Brent saatlik (2026-11-07)

Üretici: `sonuclar/haiku_arge/dk_indir.py` (ana motor modülü değiştirilmedi). Bitiş 2025-10-31 (hariç): kilit
sonrası aylık dosya istenmedi; 31 Ekim saatleri düşer.

| Seri | Aralık | Satır | İlk | Son | Kilit sonrası | NaN |
|---|---|---|---|---|---|---|
| DK_SPX (USA500IDXUSD) | 1h | 68858 | 2011-09-18 | 2025-10-30 | 0 | 0 |
| DK_UKOIL (BRENTCMDUSD) | 1h | 78764 | 2010-12-02 | 2025-10-30 | 0 | 0 |

## Doğrulama (TradingView ile karşılaştırma, ortak dönem)
- **Brent:** saatlik ortak 4491 mum; kapanış oranı medyan 1.0002 (ölçek doğru); saatlik getiri korelasyonu 0.98.
- **SPX:** günlük kapanış oranı medyan 1.0 (ölçek doğru); günlük getiri korelasyonu 0.93 (TradingView SP:SPX ile
  zaman dilimi/kapanış saati farkı olabilir; saatlik karşılaştırma yapılamadı, TV SPX mumları :30'da).
- **Eksik ay:** SPX için 2010-03 bağlantı hatasıyla başarısız (8 deneme); veri 2011-09'da başlıyor, o aylar yok.
  Yeniden çalıştırmayla tamamlanabilir (yalnız eksik aylar istenir).

## Sonuç
- Saatlik SPX: 2011-09 → 2025-10 (önceden TradingView ile yalnız 2023-).
- Saatlik Brent: 2010-12 → 2025-10 (önceden TradingView ile yalnız 2025-01-).
- XU30 saatlik: hâlâ yalnız 2024- (Dukascopy'de BIST yok).
