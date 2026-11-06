# KST Strategy [Skyrexio] (`Pv1GvUVs`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/Pv1GvUVs-KST-Strategy-Skyrexio/
- Kaynak: 140 satır Pine
- Zaman dilimi / pazar: 1s · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
9: strategy(title = "KST Strategy [Skyrexio]",  shorttitle = "KST", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 60, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 5, use_bar_magnifier = true)
```

## Ne yapıyor
KST sinyali yukarı keser + kapanış>LSMA200 + >Alligator çenesi + Choppiness<50 → long; stop sinyal mumu dibi−1.5 ATR, hedef kapanış+3.5 ATR.

## Koddan kanıt (satır: kod)
```
107: longSignal = ta.crossover(kst, sig) and close > filter and close > jaw and chopCond
109: stopLossPrice = low - atrNumStopLoss*ta.atr(14)
110: takeProfit    = close + atrNumTakeProfit*ta.atr(14)
113: atrStopLoss := stopLossPrice
116: closeTradeCondition = high[1] >= atrTakeProfit[1] or low[1] <= atrStopLoss[1]
125: strategy.entry(id = "entry1", direction = strategy.long,  alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency 
```

## Repaint / lookahead kontrolü
Repaint yok; stop/hedef sinyal anında sabitlenir.

## Karar ve gerekçe
Aday.
