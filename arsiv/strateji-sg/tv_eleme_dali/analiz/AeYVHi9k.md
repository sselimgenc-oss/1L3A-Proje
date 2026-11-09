# Strict 1-Trade/Day SMC v13 (`AeYVHi9k`)

- Yazar: Ross1992gg · Link: https://www.tradingview.com/script/AeYVHi9k-Strict-1-Trade-Day-SMC-ORB/
- Kaynak: 146 satır Pine
- Zaman dilimi / pazar: 5 dk gün içi · ABD endeks/hisse
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("Strict 1-Trade/Day SMC v13", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10, initial_capital=10000, currency=currency.USD)
```

## Ne yapıyor
ABD seansı 1 işlem/gün SMC: açılış aralığı (ORB) + CHoCH (swing kırılımı) + FVG boşluğu → aralık dışı kapanışta giriş, ATR izleyen stop ve 2R hedef; %50 kısmi, 3 saat sonra başa-baş, gün sonu çıkış.

## Koddan kanıt (satır: kod)
```
6: rthSession = input.session("0930-1600", "Regular Trading Hours")
7: orbSession = input.session("0930-0945", "Custom ORB Session")
8: entryCutoff = input.session("1200-1600", "Entry Cutoff Session")
25: in_orb = not na(time(timeframe.period, orbSession, tz))
37: sHigh = ta.pivothigh(high, swingLen, swingLen)
38: sLow  = ta.pivotlow(low, swingLen, swingLen)
53: inRTH = not na(time(timeframe.period, rthSession, tz))
55: isBeforeCutoff = na(time(timeframe.period, entryCutoff, tz)) // True before 3:00 PM
90: strategy.entry("Long", strategy.long, comment="L: CHoCH+FVG")
93: strategy.exit("Exit Long", "Long", trail_price=entryPrice, trail_offset=atrValue * atrMultiplier / syminfo.mintick, limit=takeProfit, comment_loss="AT
103: strategy.entry("Short", strategy.short, comment="S: CHoCH+FVG")
106: strategy.exit("Exit Short", "Short", trail_price=entryPrice, trail_offset=atrValue * atrMultiplier / syminfo.mintick, limit=takeProfit, comment_loss="
122: strategy.close("Long", qty_percent=50, comment="1R/SMA Partial")
123: strategy.close("Short", qty_percent=50, comment="1R/SMA Partial")
```

## Repaint / lookahead kontrolü
`ta.pivothigh(high, 2, 2)` 2 mum gecikmeli; giriş `close > orh`. Repaint yok.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (ORB, 15:00 kesim) 5 dk mum ister; Yahoo gün içi 60 günle sınırlı.
