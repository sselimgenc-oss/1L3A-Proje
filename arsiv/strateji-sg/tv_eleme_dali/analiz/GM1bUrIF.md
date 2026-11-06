# INJ DCA Long Strategy [3Commas & QuantPilot] (`GM1bUrIF`)

- Yazar: 3Commas · Link: https://tr.tradingview.com/script/GM1bUrIF-INJ-DCA-Long-Strategy-3Commas-QuantPilot/
- Kaynak: 190 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
15: strategy("INJ DCA Long Strategy [3Commas & QuantPilot]", shorttitle = "INJ RSI-L [3Commas & QuantPilot]", overlay = true, initial_capital = 100000, default_qty_type = strategy.cash, default_qty_value = 500, pyramiding = 6, commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 100)
```

## Ne yapıyor
INJ DCA 3Commas: RSI/VWAP sinyalinde taban emir + ortalama düşüren ek emirler (pyramiding>1), ortalama maliyete göre çıkış.

## Koddan kanıt (satır: kod)
```
15: strategy("INJ DCA Long Strategy [3Commas & QuantPilot]", shorttitle = "INJ RSI-L [3Commas & QuantPilot]", overlay = true, initial_capital = 100000, de
43: grpHook = "DCA Bot Webhook"
116: strategy.entry("Long_Base", strategy.long, qty = baseQty, limit = close, comment = "Long_Base")
118: strategy.entry("Long_Base", strategy.long, qty = baseQty, comment = "Long_Base")
129: strategy.entry("Long_AO_" + str.tostring(nextIdx), strategy.long, qty = aoUsdt / close, comment = "Long_AO_" + str.tostring(nextIdx))
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2).
