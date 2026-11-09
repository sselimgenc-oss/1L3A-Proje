# Glow Ribbon Flip (`OUOx3rYT`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/OUOx3rYT-Glow-Ribbon-Flip-Trend-Following-Strategy-with-ATR-Band-Stops/
- Kaynak: 176 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
15: strategy("Glow Ribbon Flip", "Ribbon Flip", overlay = true, initial_capital = 10000, default_qty_type = strategy.fixed, default_qty_value = 1, commission_type = strategy.commission.percent, commission_value = 0.04, slippage = 2, pyramiding = 0, calc_on_every_tick = false, margin_long = 0, margin_short = 0)
```

## Ne yapıyor
Glow Ribbon Flip (OUOx3rYT): EMA21 ± 2×ATR(10) izleyen bantlar (SuperTrend benzeri); yön dönüşünde (flip) ve trend içinde EMA'yı yeniden aşınca (pullback) giriş; stop = ilgili bant, hedef 2R.

## Koddan kanıt (satır: kod)
```
75: bool  flipBull = dir == 1 and prevDir != 1
76: bool  flipBear = dir == -1 and prevDir != -1
79: bool pullBull = pullOn and dir == 1 and prevDir == 1 and close > basis and close[1] <= basis[1] and strategy.position_size == 0 and longsOn
95: if flipBull
97: strategy.entry("Long", strategy.long, qty = qty, comment = "Flip")
101: else if flipBear
103: strategy.entry("Short", strategy.short, qty = qty, comment = "Flip")
107: else if pullBull
108: strategy.entry("Long", strategy.long, qty = qty, comment = "Pullback")
111: strategy.entry("Short", strategy.short, qty = qty, comment = "Pullback")
118: strategy.exit("Exit L", "Long", stop = lo, limit = hasR ? refPx + tpR * entryDist : na)
120: strategy.exit("Exit S", "Short", stop = hi, limit = hasR ? refPx - tpR * entryDist : na)
141: plotshape(showMarks and flipBull ? stopLine : na, "Bull flip", shape.diamond, location.absolute, bullCol, size = size.small)
142: plotshape(showMarks and flipBear ? stopLine : na, "Bear flip", shape.diamond, location.absolute, bearCol, size = size.small)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/ribbon_flip.py` olarak çevrilip test edildi.
