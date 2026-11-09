# Hash Supertrend (`6zYF9Xts`)

- Yazar: Hash_Capital · Link: https://www.tradingview.com/script/6zYF9Xts-Hash-Supertrend-Hash-Capital-Research/
- Kaynak: 205 satır Pine
- Zaman dilimi / pazar: 12s · kripto (SOL)
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Hash Supertrend",  shorttitle="Hash Supertrend", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=15)
```

## Ne yapıyor
ta.supertrend(3.11, 16) yön değişiminde long/short; hep piyasada.

## Koddan kanıt (satır: kod)
```
42: [supertrend, direction] = ta.supertrend(factor, atrPeriod)
50: longSignal = ta.change(direction) < 0
51: shortSignal = ta.change(direction) > 0
122: if longSignal and isInSession
123: strategy.entry("Long", strategy.long)
125: if shortSignal and isInSession
126: strategy.entry("Short", strategy.short)
166: plotshape(showSignals and longSignal,
174: plotshape(showSignals and shortSignal,
192: alertcondition(longSignal and isInSession, "Long Entry", "Supertrend flipped BULLISH - Long signal triggered")
193: alertcondition(shortSignal and isInSession, "Short Entry", "Supertrend flipped BEARISH - Short signal triggered")
197: alertcondition(useTimeFilter and longSignal and not isInSession, "Long Signal (Filtered)", "Supertrend BULLISH signal outside trading hours - Not exec
198: alertcondition(useTimeFilter and shortSignal and not isInSession, "Short Signal (Filtered)", "Supertrend BEARISH signal outside trading hours - Not ex
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
Aday (aynı mantık Kivanc Supertrend'in parametre farkı ama kesin eleme nedeni değil; kendi varsayılanlarıyla test).
