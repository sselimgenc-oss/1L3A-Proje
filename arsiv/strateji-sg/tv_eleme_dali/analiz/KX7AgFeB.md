# ORB + Fib Breakout Signals (`KX7AgFeB`)

- Yazar: chadsingh · Link: https://tr.tradingview.com/script/KX7AgFeB-ORB-Fib-Breakout-Signals-Strategy/
- Kaynak: 218 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("ORB + Fib Breakout Signals", overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=1, pyramiding=0, calc_on_every_tick=false, process_orders_on_close=true, commission_type=strategy.commission.cash_per_contract, commission_value=0.62, slippage=2)
```

## Ne yapıyor
08:30–15:00 ORB + Fibonacci.

## Koddan kanıt (satır: kod)
```
13: signalSess = input.session("0830-1500", "Active Session (levels + signals)", group=g1)
36: orbSession = f_pad(startHour) + f_pad(startMin) + "-" + f_pad(endH) + f_pad(endM)
39: inORB     = not na(time(timeframe.period, orbSession, tzInput))
40: inSession = not na(time(timeframe.period, signalSess, tzInput))
190: strategy.entry("Long", strategy.long, qty=qty)
201: strategy.entry("Short", strategy.short, qty=qty)
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
