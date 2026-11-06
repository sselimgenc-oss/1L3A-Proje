# BNB Grid Bot — Long Strategy (`9pHwOZsM`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/9pHwOZsM-BNB-Grid-Bot-Long-Strategy/
- Kaynak: 204 satır Pine
- Zaman dilimi / pazar: 15dk–1s · tek sembol
- **Karar: ELE**

## strategy() bildirimi
```
11: strategy("BNB Grid Bot — Long Strategy", shorttitle = "BNB Grid", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 588, pyramiding = 200, commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 500, max_boxes_count = 5)
```

## Ne yapıyor
Izgara (grid) botu: sabit fiyat aralığını 17 seviyeye böler; fiyat her seviyenin altına inince o seviyede long alır, bir üst seviyeye çıkınca satar (`pyramiding=200`). Giriş sinyali / trend filtresi yok, stop yok: aralığın altına düşen fiyatta tüm seviyeler dolu kalır.

## Koddan kanıt (satır: kod)
```
11: strategy("BNB Grid Bot — Long Strategy", shorttitle = "BNB Grid", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_q
21: nLevels    = input.int(17, "Grid Levels", minval = 7, maxval = 200, group = grpGrid, tooltip = "Number of price levels between High and Low. 17 levels
51: usdtPerLevel = investment / nLevels
57: pct = float(i) / float(nLevels - 1)
92: for i = 0 to nLevels - 1
103: for i = 1 to nLevels - 1
111: strategy.entry("L" + str.tostring(i), strategy.long, qty = qty, comment = "Grid_BUY_L" + str.tostring(i))
119: strategy.close("L" + str.tostring(i), comment = "Grid_TP_L" + str.tostring(i))
150: for i = 0 to nLevels - 1
157: if i == 0 or i == nLevels - 1 or i % 3 == 0
176: for i = 0 to nLevels - 1
185: table.cell(tbl, 1, 2, str.tostring(nLevels) + " (" + gridMode + ")", text_color = color.white, bgcolor = bg)
187: table.cell(tbl, 1, 3, str.tostring(ownedCount) + " / " + str.tostring(nLevels), text_color = ownedCount > 0 ? color.green : color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security yok; repaint/lookahead sorunu yok — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: grid (B2 kuralı). Her seviyede küçük kâr, aralık dışı düşüşte sınırsız zarar; kazanma oranı yapay yüksek, getiri aralık varsayımına bağlı.
