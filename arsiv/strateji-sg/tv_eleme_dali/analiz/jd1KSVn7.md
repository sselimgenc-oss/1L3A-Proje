# BIST30 to S&P 500 — ATR Momentum Rider (`jd1KSVn7`)

- Yazar: newton61 · Link: https://www.tradingview.com/script/jd1KSVn7/
- Kaynak: 161 satır Pine
- Zaman dilimi / pazar: 1g · endeks vadeli
- **Karar: AL**

## strategy() bildirimi
```
5: strategy( "BIST30 to S&P 500 — ATR Momentum Rider", shorttitle = "ATR Rider", overlay = true, initial_capital = 100000, default_qty_type = strategy.fixed, default_qty_value = 1, pyramiding = 2, commission_type = strategy.commission.percent, commission_value = 0, slippage = 1, margin_long = 1, close_entries_rule = "ANY", calc_on_every_tick = false, calc_on_order_fills = false, process_orders_on_close = false)
```

## Ne yapıyor
HMA(8)>HMA(9)>HMA(20) rejimi yeni başlarsa (HMA20 eğimi ≥ −0.18 ATR/gün) long; yeni rejimde pozisyon yenilenir; MFE≥1.5 ATR sonrası tepeden %5.75 izleyen stop (4 mum sonra).

## Koddan kanıt (satır: kod)
```
65: bool regime = hmaF > hmaM and hmaM > hmaS
71: bool setup = rawSetup and slopeAllowed
109: bool k1ExitSignal = false
119: k1ExitSignal := bar_index >= entryBar + k1W and close <= k1Trail
134: strategy.close(activeEntryId, comment = "SET-R", alert_message = "SET-R EXIT", immediately = false)
135: strategy.entry(nextEntryId, strategy.long, comment = "SET", alert_message = "SET LONG")
138: strategy.entry(activeEntryId, strategy.long, comment = "SET", alert_message = "SET LONG")
142: else if k1ExitSignal
143: strategy.close(activeEntryId, comment = "K1", alert_message = "K1 EXIT", immediately = false)
146: strategy.close(activeEntryId, comment = "DATE", alert_message = "DATE EXIT", immediately = false)
157: plotshape(k1ExitSignal and not setup, title = "K1", text = "K1", style = shape.labeldown, location = location.abovebar, color = color.new(color.fuchsi
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
Aday.
