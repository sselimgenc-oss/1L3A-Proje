# Double CCI Confirmed Hull Moving Average Reversal Strategy (`3fea8k4Z`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/3fea8k4Z-Double-CCI-Confirmed-Hull-Moving-Average-Reversal-Strategy/
- Kaynak: 120 satır Pine
- Zaman dilimi / pazar: 2s · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
9: strategy(title = "Double CCI Confirmed Hull Moving Average Reversal Strategy",  shorttitle = "Double CCI", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 100, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slipp
```

## Ne yapıyor
Yüksek HMA(34) üstüne çıkar + kapanış>HMA + CCI25>0 + CCI50>0 → long; çıkış aynı (1.75 ATR stop, +2.25 ATR sonrası EMA20 altı).

## Koddan kanıt (satır: kod)
```
75: hullma = ta.wma(2*ta.wma(close, hullMaLength/2)-ta.wma(close, hullMaLength), math.floor(math.sqrt(hullMaLength)))
95: longCondition =  ta.crossover(high, hullma) and close > hullma and fastCci > 0 and slowCci > 0
98: closeCondition =  close < takeProfitLevel or low <= stopLossLevel
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
Aday.
