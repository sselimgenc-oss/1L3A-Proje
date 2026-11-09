# BTC Mean Reversion - RSI + Bollinger (`95JBkzXV`)

- Yazar: connorgeary150 · Link: https://www.tradingview.com/script/95JBkzXV-BTC-Mean-Reversion-RSI-Bollinger/
- Kaynak: 55 satır Pine
- Zaman dilimi / pazar: 10 sn (yazar) → 1s · kripto
- **Karar: AL**

## strategy() bildirimi
```
4: strategy("BTC Mean Reversion - RSI + Bollinger", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10)
```

## Ne yapıyor
RSI(14)<30 + kapanış<BB alt → long; RSI>70 + üst bant → short; RSI>50 ya da orta bant kesişimiyle çıkış.

## Koddan kanıt (satır: kod)
```
16: inSession := session.ismarket
27: longEntry  = inSession and rsi < 30 and close < lower and strategy.position_size <= 0
30: shortEntry = inSession and useShorts and rsi > 70 and close > upper and strategy.position_size >= 0
34: exitLong  = strategy.position_size > 0 and (rsi > 50 or ta.crossover(close, basis))
37: exitShort = strategy.position_size < 0 and (rsi < 50 or ta.crossunder(close, basis))
46: if exitLong
49: if exitShort
```

## Repaint / lookahead kontrolü
Repaint yok; `session.ismarket` kripto 7/24'te hep doğru.

## Karar ve gerekçe
Aday. Yazarın tek haftalık 10 sn testi anlamsız, 1s ile test ediliyor.
