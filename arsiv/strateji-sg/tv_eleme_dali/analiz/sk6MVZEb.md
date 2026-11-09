# Scam or Slam - Day Trading Rauf Strategy (`sk6MVZEb`)

- Yazar: MrWickTrading · Link: https://tr.tradingview.com/script/sk6MVZEb-Scam-or-Slam-Day-Trading-Rauf-Strategy/
- Kaynak: 849 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy( title                   = "Scam or Slam - Day Trading Rauf Strategy", shorttitle              = "Day Trading Rauf", overlay                 = true, initial_capital         = 50000, currency                = currency.USD, default_qty_type        = strategy.fixed, default_qty_value       = 1, pyramiding              = 0, process_orders_on_close = true, calc_on_every_tick      = false, margin_long             
```

## Ne yapıyor
Londra/NY aralığı gün içi (5 dk).

## Koddan kanıt (satır: kod)
```
44: londonRangeSession = input.session(
56: nyRangeSession = input.session(
197: tooltip = "Plots custom entry markers only when a real strategy.entry order is submitted. These markers are synced with the backtest entries.")
401: ldnInSession = useLondonRange and not na(time(timeframe.period, londonRangeSession, tradeTz))
402: nyrInSession = useNyRange and not na(time(timeframe.period, nyRangeSession, tradeTz))
646: strategy.entry(id = "L-LDN", direction = strategy.long, comment = "London Long")
674: strategy.entry(id = "S-LDN", direction = strategy.short, comment = "London Short")
702: strategy.entry(id = "L-NY", direction = strategy.long, comment = "NY Long")
730: strategy.entry(id = "S-NY", direction = strategy.short, comment = "NY Short")
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
