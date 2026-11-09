# MACD with 1D Stochastic Confirmation Reversal Strategy (`BtDUET5k`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/BtDUET5k-MACD-with-1D-Stochastic-Confirmation-Reversal-Strategy/
- Kaynak: 127 satır Pine
- Zaman dilimi / pazar: 45dk · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
9: strategy(title = "MACD with 1D Stochastic Confirmation Reversal Strategy",  shorttitle = "MACD Strategy", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 30, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippag
```

## Ne yapıyor
MACD sinyali yukarı keser + günlük Stoch K>D ve K<80 → long; çıkış aynı Skyrexio şablonu (1.75 ATR stop, +2.25 ATR sonrası EMA20).

## Koddan kanıt (satır: kod)
```
74: [dailyClose, dailyHigh, dailyLow] = request.security(syminfo.tickerid, "D", [close, high, low])
95: dailyK = request.security(syminfo.tickerid, "D", k)
96: dailyD = request.security(syminfo.tickerid, "D", d)
101: longCondition =   ta.crossover(macd, macdSignal) and dailyK > dailyD and dailyK < 80
105: closeCondition =  close < takeProfitLevel or low <= stopLossLevel
```

## Repaint / lookahead kontrolü
`request.security(...,"D", [close,high,low])` lookahead parametresiz (off); günlük stokastik tamamlanmış günlerden. Çeviride bir önceki kapanmış gün kullanıldı.

## Karar ve gerekçe
Aday.
