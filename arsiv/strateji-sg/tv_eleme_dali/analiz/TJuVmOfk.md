# Williams R Zone Scalper v1.0[BullByte] (`TJuVmOfk`)

- Yazar: BullByte · Link: https://www.tradingview.com/script/TJuVmOfk-Williams-R-Zone-Scalper-v1-0-BullByte/
- Kaynak: 236 satır Pine
- Zaman dilimi / pazar: 5dk · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Williams R Zone Scalper v1.0[BullByte]", overlay=true, initial_capital=1000, currency=currency.USD, default_qty_type=strategy.percent_of_equity, default_qty_value=30, commission_type=strategy.commission.percent, commission_value=0.01, process_orders_on_close=true)
```

## Ne yapıyor
Williams %R(14) −80'i yukarı keserse long, −20'yi aşağı keserse short; yalnız Supertrend süzgeci açık (kodda hatalı yazılmış); SL/TP kapalı, ters sinyalde dön.

## Koddan kanıt (satır: kod)
```
9: process_orders_on_close=true)
92: [stUp, stDn] = ta.supertrend(stFactor, stAtrLen)
93: stOK_long  = close > stDn
94: stOK_short = close < stUp
95: stOK       = not useST or stOK_long or stOK_short
96: filter_long  = maOK and chopOK and adxOK and volOK and bbwOK and (not useST or stOK_long)
97: filter_short = maOK and chopOK and adxOK and volOK and bbwOK and (not useST or stOK_short)
111: longCondition  = ta.crossover(wr, -80) and filter_long
112: shortCondition = ta.crossunder(wr, -20) and filter_short
114: if longCondition
122: if shortCondition
```

## Repaint / lookahead kontrolü
Repaint yok. Süzgeç hatası: `[stUp, stDn] = ta.supertrend(...)` ikinci eleman yön (±1) olduğundan long süzgeci ≈ her zaman doğru.

## Karar ve gerekçe
Aday (15 dk kripto; 5 dk ayrıca).
