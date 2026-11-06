# PPS (`WpJ5ym7u`)

- Yazar: Julien_Exe · Link: https://tr.tradingview.com/script/WpJ5ym7u-Pivot-Point-SuperTrend-Strategy-TrendFilter/
- Kaynak: 123 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("PPS", overlay=true, initial_capital=500000, currency=currency.USD, default_qty_type=strategy.cash, default_qty_value=50000)
```

## Ne yapıyor
Pivot Point SuperTrend 'PPS' (WpJ5ym7u): pivot merkezli (ağırlıklı ortalama) SuperTrend yön değişimi ya da (KivancST yön değişimi + kapanış SMA20 yönünde) → long/short; hep piyasada. Pivotlar 2 mum gecikmeli onaylı.

## Koddan kanıt (satır: kod)
```
17: float ph = pivothigh(prd, prd)
18: float pl = pivotlow(prd, prd)
54: bsignal = Trend == 1 and Trend[1] == -1
55: ssignal = Trend == -1 and Trend[1] == 1
56: plotshape(bsignal and showlabel ? Trailingsl : na, title="Buy", text="Buy", location = location.absolute, style = shape.labelup, size = size.tiny, col
57: plotshape(ssignal and showlabel ? Trailingsl : na, title="Sell", text="Sell", location = location.absolute, style = shape.labeldown, size = size.tiny,
110: longCondition = (trend == 1 and trend[1] == -1 and close > ma) or (bsignal and window())
111: shortCondition = (trend == -1 and trend[1] == 1 and close < ma) or (ssignal and window())
114: strategy.entry("BUY", strategy.long)
117: strategy.close("BUY")
118: strategy.entry("SELL", strategy.short)
120: buy1 = barssince((trend == 1 and trend[1] == -1 and close > ma) or (bsignal and window()))
121: sell1 = barssince((trend == -1 and trend[1] == 1 and close < ma) or (ssignal and window()))
```

## Repaint / lookahead kontrolü
`pivothigh(prd, prd)` prd=2 mum gecikmeli; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «pivot bazlı giriş (repaint riski)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/pps.py` olarak çevrilip test edildi.
