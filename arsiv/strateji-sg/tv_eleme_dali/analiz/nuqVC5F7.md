# [3Commas] BCH Heikin Ashi RSI Fade — Short Strategy (`nuqVC5F7`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/nuqVC5F7-3Commas-BCH-Heikin-Ashi-RSI-Fade-Short-Strategy/
- Kaynak: 183 satır Pine
- Zaman dilimi / pazar: 15dk · kripto (BCH)
- **Karar: AL**

## strategy() bildirimi
```
9: strategy("[3Commas] BCH Heikin Ashi RSI Fade — Short Strategy", shorttitle = "[3Commas] HA-S BCH", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 280, pyramiding = 1, commission_type = strategy.commission.percent, commission_value = 0.055, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500)
```

## Ne yapıyor
RSI(100)>46 ve ≥7 ardışık yükselen Heikin Ashi mumu → short; %2.1 hedef, %2.5 stop; ortalama alım yok.

## Koddan kanıt (satır: kod)
```
15: baseOrderSize = input.float(280.0, "Base Order Size (USDT)", minval = 1, group = grpBase, tooltip = "2.8% of default 10k capital. No averaging orders 
22: rsiLevel     = input.float(46.0, "RSI Level", minval = 1, maxval = 100, group = grpRSI)
26: haStreak    = input.int(7, "Consecutive Candles", minval = 2, maxval = 30, group = grpHA, tooltip = "Number of consecutive same-direction HA candles r
101: condRSI = rsiCondition == "Greater Than" ? rsiLTF > rsiLevel : rsiLTF < rsiLevel
103: condHA  = haCount >= haStreak
105: entrySignal = condRSI and condHA
114: qty = baseOrderSize / close
130: strategy.exit("Exit", from_entry = "Short_Base", limit = tpPx, stop = slPx, comment_profit = "TP", comment_loss = "SL")
```

## Repaint / lookahead kontrolü
`request.security(...,lookahead_off)` aynı TF (15dk); HA hesabı geçmişe bağlı. Repaint yok.

## Karar ve gerekçe
Aday. 3Commas şablonunda ortalama alımı (DCA) kapalı olduğundan eleme kuralına girmiyor.
