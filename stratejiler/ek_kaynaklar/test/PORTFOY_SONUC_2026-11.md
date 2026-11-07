# Quantpedia portföy stratejileri — yerel test (2026-11-07)

**Veri:** Yahoo Finance düzeltilmiş kapanış, günlük → aylık son işlem günü. **Dönem:** 2006-01 — 2025-10-31 (kilit sonrası veri kullanılmadı). Evren: SPY, EFA, EEM, IEF, TLT, DBC, GLD, VNQ, 9 sektör ETF'i. **Maliyet:** işlem notionali başına %0.1 (×2 sağlamlık testi). Nakit getirisi **sıfır** (T-bill faizi yok — nakit dönemleri stratejileri biraz aşağı çekiyor). Script: `portfoy_test.py`.

## Kurallar (yayınlanmış özet, parametre seçimi yok)
- **GTAA 10 aylık SMA (Faber benzeri):** SPY, EFA, IEF, VNQ, DBC; her varlık fiyat > 10 aylık ortalama ise 1/5 pay, değilse nakit.
- **Momentum varlık dağılımı:** 8 varlık, 12 aylık getiriye göre ilk 3'e eşit ağırlık.
- **Sektör momentum:** 9 sektör ETF'i, 12 aylık getiriye göre ilk 3'e eşit ağırlık.
- **Kıyas:** SPY al-tut.

## Sonuçlar (maliyet %0.1)
| Strateji | Yıllık | En büyük düşüş | Sharpe* | 2006–12 | 2013–19 | 2020–25 | Maliyet×2 Sharpe |
|---|---|---|---|---|---|---|---|
| SPY al-tut | %10.9 | −%50.8 | 0.77 | +%32 | +%159 | +%130 | — |
| GTAA 10ay SMA | %4.9 | **−%11.4** | 0.77 | +%44 | +%33 | +%35 | 0.74 |
| Momentum varlık (ilk 3/8) | %8.7 | −%23.4 | 0.74 | +%82 | +%46 | +%98 | 0.71 |
| Sektör momentum (ilk 3/9) | %9.5 | −%39.1 | 0.70 | +%23 | +%107 | +%140 | 0.66 |

*Sharpe: aylık getiri ortalaması / std × √12; nakit faizi yok.

## Yorum
- **Hiçbiri SPY'ı risk-ayarlı olarak geçmiyor** (Sharpe). GTAA ise en büyük düşüşü %51'den %11'e indiriyor — **risk azaltma** amaçlı, getiriden feragat ediyor.
- Momentum varlık dağılımı 2006–12 ve 2020–25'te SPY'a yakın; 2013–19 boğasında geri kalıyor.
- Sektör momentumunun düşüşü SPY'a yakın (−%39); 2020–25'te SPY'ı geçiyor ama 2006–12'de geri kalıyor.
- **Maliyet ×2'de sıralama değişmiyor** — sonuçlar işlem maliyetine çok duyarlı değil. Ama turnover yüksek (sektör: yıllık ~5 kez tam dönüş).
- **Sınırlar:** Nakit faizsiz (GTAA'ya haksız), tek dönem, parametreler tek sette sabit, ETF evreni bugünkü ETF'ler. Kilitli dönem (2025-11+) kullanılmadı.

## Karar 13 / 24 açısından
- Bu stratejiler portföy katmanı (karar 23–25) için **aday** olabilir ama SPY kıyasında Sharpe kazancı yok; yalnız GTAA düşüş iyileştiriyor. Yoğunlaşma / sağlamlık kontrolleri bu turda yapılmadı.
