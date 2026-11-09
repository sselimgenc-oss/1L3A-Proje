# Compression Breakout System (`97gxVA5b`)

- Yazar: mateosandoval1025 · Link: https://www.tradingview.com/script/97gxVA5b-Compression-Breakout-System/
- Kaynak: 115 satır Pine
- Zaman dilimi / pazar: 1g · ABD (AAPL)
- **Karar: AL**

## strategy() bildirimi
```
33: strategy("Compression Breakout System", shorttitle="CBS", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, process_orders_on_close=true, calc_on_every_tick=false)
```

## Ne yapıyor
BB genişliği yüzdelik sırası<25 (son 5 mumda) + 20g tepe kırılımı + hacim>SMA20 + SMA200 üstü → kapanışta long; 2 ATR stop, 3 ATR chandelier izleyen stop (kapanış bazlı).

## Koddan kanıt (satır: kod)
```
37: process_orders_on_close=true, calc_on_every_tick=false)
58: sqzRecent = math.sum(sqzOn ? 1 : 0, sqzAge) > 0
60: brkLvl = ta.highest(high, brkLen)[1]
67: buySig = not inPos and time >= startT and time <= endT and sqzRecent and close > brkLvl and volOK and trendOK
83: stopLvl = math.max(entryStop, hwm - atr * trailAtr)
```

## Repaint / lookahead kontrolü
Hepsi geçmiş mum; `ta.highest(high, brkLen)[1]` ile kırılım seviyesi önceki mumdan. Repaint yok.

## Karar ve gerekçe
Aday. process_orders_on_close=true → sinyal mumunun kapanışında dolum. Risk sabit %4 (bizde %1).
