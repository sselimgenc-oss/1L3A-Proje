# VIX MACD Long (`mfw4fJST`)

- Yazar: ryoma3119 · Link: https://www.tradingview.com/script/mfw4fJST/
- Kaynak: 28 satır Pine
- Zaman dilimi / pazar: 1g · endeks/ABD
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("VIX MACD Long", overlay=true)
```

## Ne yapıyor
VIX'in MACD(12,26,9) çizgisi sinyali aşağı keserse long (korku azalıyor), yukarı keserse çık.

## Koddan kanıt (satır: kod)
```
5: vix = request.security("CBOE:VIX", timeframe.period, close)
17: longCondition = ta.crossunder(macdLine, signalLine)
21: exitCondition = ta.crossover(macdLine, signalLine)
```

## Repaint / lookahead kontrolü
`request.security("CBOE:VIX", timeframe.period, close)`: aynı mum, lookahead parametresi varsayılan (off). Repaint yok.

## Karar ve gerekçe
Aday (28 satır). VIX verisi Yahoo ^VIX.
