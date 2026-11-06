# Golden Trident | Swing-Anchored VWAP Trend System (`Eq4kPrrJ`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/Eq4kPrrJ-Golden-Trident-Swing-Anchored-VWAP-Trend-System/
- Kaynak: 220 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · ALTIN,GUMUS,PETROL
- **Karar: AL**

## strategy() bildirimi
```
17: strategy("Golden Trident | Swing-Anchored VWAP Trend System", shorttitle="GT_XAU", overlay=true, initial_capital=10000, currency=currency.USD, default_qty_type=strategy.percent_of_equity, default_qty_value=20, commission_value=0.02, slippage=2, max_boxes_count=500, max_labels_count=500, max_lines_count=500, calc_on_every_tick=false)
```

## Ne yapıyor
Golden Trident (Eq4kPrrJ): 30 mumluk tepe/dip yapısıyla yön (son tepe son dipten yeniyse yukarı); yön yukarı + kapanış > EMA200 + aralık > 0.8×ATR(20) olunca YENİ long tetiği; yön aşağı dönünce çık; 8×ATR felaket stopu. Yalnız long (altın).

## Koddan kanıt (satır: kod)
```
40: grp_dir    = "Direction"
83: ph  := ta.highestbars(high, swingLen) == 0 ? high : ph
84: pl  := ta.lowestbars(low, swingLen)  == 0 ? low  : pl
88: dir = phL > plL ? 1 : -1
117: longCond  = dir == 1              and trendLongOK  and rangeOK and inBacktestRange
118: shortCond = allowShort and dir == -1 and trendShortOK and rangeOK and inBacktestRange
120: longTrigger  = longCond  and not longCond[1]
129: if longTrigger and strategy.position_size <= 0
131: strategy.entry("Long", strategy.long, comment="XAU BUY")
135: strategy.entry("Short", strategy.short, comment="XAU SELL")
137: if dir == -1 and strategy.position_size > 0
138: strategy.close("Long", comment="Structure Flip Exit")
140: if dir == 1 and strategy.position_size < 0
141: strategy.close("Short", comment="Structure Flip Exit")
```

## Repaint / lookahead kontrolü
`ta.highestbars(high, 30)==0` yalnız geçmiş; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «swing-anchored VWAP; temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/golden_trident.py` olarak çevrilip test edildi.
