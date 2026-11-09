# Gold NY ORB v19 [Ahmed] — 2.5:1 Close 20:00 (`FJZvYKaB`)

- Yazar: YukozB · Link: https://www.tradingview.com/script/FJZvYKaB-Gold-NY-ORB-v19-Close-20-00/
- Kaynak: 61 satır Pine
- Zaman dilimi / pazar: 15dk · altın
- **Karar: AL**

## strategy() bildirimi
```
3: strategy("Gold NY ORB v19 [Ahmed] — 2.5:1 Close 20:00", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.02, slippage=2, calc_on_every_tick=false)
```

## Ne yapıyor
13:00 UTC OR aralığı; 14:00–16:30'da OR tepesi yukarı kırılımı + hacim/ATR süzgeçleri → long, stop=OR, hedef=2.5 OR; 20:00 kapat.

## Koddan kanıt (satır: kod)
```
15: isORPeriod   = isWkd and bHour == 13
17: isSessionEnd = isWkd and bHour == 20 and bMin == 0
24: var float orHigh    = na
31: orHigh    := na
36: if isORPeriod
37: orHigh := na(orHigh) ? high : math.max(orHigh, high)
40: if not isORPeriod and not na(orHigh) and not orReady and bHour >= 14
43: orRange = na(orHigh) or na(orLow) ? na : orHigh - orLow
46: longBreak = inDate and isEntryWin and orOK and regimeOK and not longFired
47: and close > orHigh and close[1] <= orHigh
51: strategy.entry("Long", strategy.long)
52: strategy.exit("LongX", "Long", stop=close - orRange, limit=close + orRange * 2.5)
55: if isSessionEnd and strategy.position_size > 0
58: plot(orReady ? orHigh : na, "OR High", color=color.new(color.green, 20), linewidth=1, style=plot.style_linebr)
```

## Repaint / lookahead kontrolü
Repaint yok; yalnız saat tabanlı.

## Karar ve gerekçe
Aday (saatlik uyarlama; 15 dk altın geçmişi yalnız 60 gün).
