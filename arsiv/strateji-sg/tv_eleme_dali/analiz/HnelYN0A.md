# Gold Breakout 15M Strategy [WillyAlgoTrader] (`HnelYN0A`)

- Yazar: WillyAlgoTrader · Link: https://tr.tradingview.com/script/HnelYN0A-Gold-Breakout-15M-Strategy-WillyAlgoTrader/
- Kaynak: 1007 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
24: strategy( title              = "Gold Breakout 15M Strategy [WillyAlgoTrader]", shorttitle         = "Gold BO 15M", overlay            = true, initial_capital    = 10000, default_qty_type   = strategy.fixed, default_qty_value  = 1, calc_on_every_tick = false, process_orders_on_close = false, margin_long        = 5, margin_short       = 5, commission_type    = strategy.commission.cash_per_order, commission_value   = 0.
```

## Ne yapıyor
Altın 15 dk kırılım (1006 satır).

## Koddan kanıt (satır: kod)
```
322: bool isXauName   = str.contains(tickerUpper, "XAU") and not str.startswith(tickerUpper, "XAG")
323: bool isGoldName  = str.contains(tickerUpper, "GOLD") or str.contains(tickerUpper, "PAXG") or str.startswith(tickerUpper, "GLDRUB")
324: bool isCmeRoot   = isFutures and (rootUpper == "GC" or rootUpper == "MGC" or rootUpper == "1OZ" or rootUpper == "QO")
329: bool isGold      = isXauName or isGoldName or isCmeRoot or isHkexRoot or isShfeRoot or isMoexRoot or isSgeName
341: bool   isOunceGold   = isXauName or str.contains(tickerUpper, "PAXG") or isCmeRoot or isMoexRoot or (str.contains(tickerUpper, "GOLD") and syminfo.cur
629: strategy.entry("Long", strategy.long, qty = qtyLong, stop = rangeHigh, oca_name = OCA_GROUP, oca_type = strategy.oca.cancel, comment = "RB long",
634: strategy.entry("Short", strategy.short, qty = qtyShort, stop = rangeLow, oca_name = OCA_GROUP, oca_type = strategy.oca.cancel, comment = "RB short",
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
