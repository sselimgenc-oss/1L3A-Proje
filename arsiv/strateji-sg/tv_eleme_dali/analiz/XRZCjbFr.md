# Channel Reversion System (`XRZCjbFr`)

- Yazar: mateosandoval1025 · Link: https://www.tradingview.com/script/XRZCjbFr-Channel-Reversion-System/
- Kaynak: 90 satır Pine
- Zaman dilimi / pazar: 1g · ABD ETF (QQQ/SPY)
- **Karar: AL**

## strategy() bildirimi
```
28: strategy("Channel Reversion System", shorttitle="CRS", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, process_orders_on_close=true, calc_on_every_tick=false)
```

## Ne yapıyor
50g kanalın alt %25 bölgesi + SMA200 üstü → long; kanal ortasında hedef, kanal altı−ATR stop, SMA200 altı çıkış (kapanış bazlı).

## Koddan kanıt (satır: kod)
```
32: process_orders_on_close=true, calc_on_every_tick=false)
40: upperD  = ta.highest(high, chanLen)[1]
41: lowerD  = ta.lowest(low,  chanLen)[1]
42: midD    = (upperD + lowerD) / 2.0
43: zoneTop = lowerD + (upperD - lowerD) * zonePct / 100.0
49: buySig = not inPos and trendOK and close <= zoneTop
56: strategy.close("Long", comment="target: channel mid")
57: else if close < lowerD - atr * atrMult
58: strategy.close("Long", comment="stop: channel failed")
60: strategy.close("Long", comment="exit: trend break")
65: pU = plot(upperD,  "Channel high", color=color.new(colNeu, 40))
66: pL = plot(lowerD,  "Channel low",  color=color.new(colNeu, 40))
81: posPct = (close - lowerD) / math.max(upperD - lowerD, 0.0001) * 100.0
```

## Repaint / lookahead kontrolü
`ta.highest(high, chanLen)[1]` ile önceki 50 mum; repaint yok.

## Karar ve gerekçe
Aday.
