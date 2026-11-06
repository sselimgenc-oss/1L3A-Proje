# Pivot Point SuperTrend [Backtest] (`DwdC6FT4`)

- Yazar: LonesomeTheBlue · Link: https://tr.tradingview.com/script/DwdC6FT4-Pivot-Point-SuperTrend-Backtest/
- Kaynak: 76 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Pivot Point SuperTrend [Backtest]", overlay = true)
```

## Ne yapıyor
Pivot Point SuperTrend (DwdC6FT4): pivot merkez çizgisi ± ATR×3 bantları; trend dönüşünde yön değiştir.

## Koddan kanıt (satır: kod)
```
18: ph := pivothigh(prd, prd)
19: pl := pivotlow(prd, prd)
55: strategy.close_all()
60: strategy.entry("Buy", true, comment = "Buy")
62: strategy.entry("Sell", false, comment = "Sell")
70: strategy.close("Buy", qty_percent = 50, comment = "close buy for 50%")
73: strategy.close("Sell", qty_percent = 50, comment = "close sell for 50%")
```

## Repaint / lookahead kontrolü
Pivot: satır 18: `ph := pivothigh(prd, prd)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/pivot_st.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük. Pivot onayı prd bar sonra gelir (repaint yok: yalnız geçmiş).
