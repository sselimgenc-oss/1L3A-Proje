# Triple CCI Strategy MFI Confirmed [Skyrexio] (`PETNavGq`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/PETNavGq-Triple-CCI-Strategy-MFI-Confirmed-Skyrexio/
- Kaynak: 121 satır Pine
- Zaman dilimi / pazar: 2s · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(title = "Triple CCI Strategy MFI Confirmed [Skyrexio]",  shorttitle = "Triple CCI", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 50, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 5, use_ba
```

## Ne yapıyor
CCI(14) 0'ı yukarı keser + kapanış>EMA50 + CCI25>0 + CCI50>0 + MFI>50 → long; stop giriş−1.75 ATR, +2.25 ATR aşılırsa kapanış<EMA20 çıkış.

## Koddan kanıt (satır: kod)
```
79: stopLossLevel := strategy.position_avg_price - stopLossAtrNum * ATR
83: tralingProfitActivationLevel := strategy.position_avg_price + tralingProfitActivationNum * ATR
96: longCondition =  ta.crossover(fastCci, 0) and close > ema and middleCci > 0 and slowCci > 0 and mfi > 50
99: closeCondition =  close < takeProfitLevel or low <= stopLossLevel
```

## Repaint / lookahead kontrolü
Repaint yok. Stop/aktivasyon ATR'si Pine'da her mumda güncel; çeviri giriş anı ATR'sini sabit alıyor.

## Karar ve gerekçe
Aday.
