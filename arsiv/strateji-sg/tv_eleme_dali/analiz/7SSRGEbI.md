# Drop's Opening Range Breakout (ORB) (`7SSRGEbI`)

- Yazar: drop_trades · Link: https://www.tradingview.com/script/7SSRGEbI-Drop-s-Opening-Range-Breakout-ORB/
- Kaynak: 214 satır Pine
- Zaman dilimi / pazar: 1–5 dk gün içi · ABD hisse/endeks vadeli
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("Drop's Opening Range Breakout (ORB)", "DORB",  overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.cash_per_contract, commission_value=2.50, // Pessimistic friction (commissions) slippage=2,            // Pessimistic friction (slippage) margin_long=0, margin_short=0)
```

## Ne yapıyor
New York 09:30–09:45 açılış aralığı (ORB): 09:45–11:30 arasında aralık kırılımında (ya da geri çekilmede limit) giriş, ATR/R tabanlı SL-TP, 11:30'da kesim.

## Koddan kanıt (satır: kod)
```
17: rangeSession = input.session("0930-0945", title="Range Definition Session", tooltip="The 15-minute window used to define the High and Low boundaries (
18: tradeSession = input.session("0945-1130", title="Trading Execution Session", tooltip="The window where the strategy is allowed to enter breakout trade
57: if not timeframe.isintraday
60: inRangePeriod = not na(time(timeframe.period, rangeSession + ":23456", tz))
61: inTradeWindow = not na(time(timeframe.period, tradeSession + ":23456", tz))
160: strategy.entry("ORB Long Pullback", strategy.long, qty=qtySize, limit=rangeHigh)
162: strategy.entry("ORB Long", strategy.long, qty=qtySize)
179: strategy.entry("ORB Short Pullback", strategy.short, qty=qtySize, limit=rangeLow)
181: strategy.entry("ORB Short", strategy.short, qty=qtySize)
192: strategy.exit("Exit Long", stop=activeSL, limit=activeTP)
200: strategy.exit("Exit Short", stop=activeSL, limit=activeTP)
204: strategy.close_all(comment="Time Cutoff (11:30 EST)")
```

## Repaint / lookahead kontrolü
`request.security` 2 yerde, görünen repaint yok; seans mantığı zaman damgasına bağlı.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — 09:30–09:45 aralığı ve 11:30 kesimi için ≤5 dk mum gerekir; Yahoo gün içi 60 günle sınırlı (Aşama-1 kuralı: 15 dk hisse yalnız 60 gün).
