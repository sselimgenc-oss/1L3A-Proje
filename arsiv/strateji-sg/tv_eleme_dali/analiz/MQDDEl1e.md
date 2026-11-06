# [Kpt-Ahab] Poor Man's Orderflow Simple AlgoPilot (`MQDDEl1e`)

- Yazar: Kpt-Ahab · Link: https://tr.tradingview.com/script/MQDDEl1e/
- Kaynak: 1650 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
8: strategy( title = "[Kpt-Ahab] Poor Man's Orderflow Simple AlgoPilot", overlay = true, initial_capital = 10000, commission_value = 0.1, default_qty_value = 10, slippage = 0, pyramiding = 3, margin_long = 0, margin_short = 0, max_lines_count = 500, max_labels_count = 500, currency = currency.USD, default_qty_type = strategy.percent_of_equity )
```

## Ne yapıyor
Poor Man's Orderflow: mum içi hacim/emir akışını yaklaşıklayan göstergelerle giriş, pyramiding=3.

## Koddan kanıt (satır: kod)
```
15: pyramiding = 3,
32: const string group_orderflow = "Orderflow"
33: const string group_orderflow_signals = "Orderflow Signals"
360: group = group_orderflow,
368: group = group_orderflow,
377: group = group_orderflow,
386: group = group_orderflow,
395: group = group_orderflow,
404: group = group_orderflow,
413: group = group_orderflow,
417: show_orderflow_visuals = input.bool(
420: group = group_orderflow,
427: group = group_orderflow,
428: active = show_orderflow_visuals
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: emir akışı verisi gerekir (B2).
