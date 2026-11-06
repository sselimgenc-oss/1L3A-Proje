# BTCUSDT.P Grid Bot — Long Strategy (`BR74LOKo`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/BR74LOKo-BTCUSDT-P-Grid-Bot-Long-Strategy/
- Kaynak: 225 satır Pine
- Zaman dilimi / pazar: 15dk–1s · tek sembol
- **Karar: ELE**

## strategy() bildirimi
```
12: strategy("BTCUSDT.P Grid Bot — Long Strategy", shorttitle = "BTC Grid 1%", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 250, pyramiding = 200, commission_type = strategy.commission.percent, commission_value = 0.055, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 500, max_boxes_count = 5)
```

## Ne yapıyor
Izgara (grid) botu: sabit fiyat aralığını 50 seviyeye böler; fiyat her seviyenin altına inince o seviyede long alır, bir üst seviyeye çıkınca satar (`pyramiding=200`). Giriş sinyali / trend filtresi yok, stop yok: aralığın altına düşen fiyatta tüm seviyeler dolu kalır.

## Koddan kanıt (satır: kod)
```
12: strategy("BTCUSDT.P Grid Bot — Long Strategy", shorttitle = "BTC Grid 1%", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, 
22: nLevels    = input.int(50, "Grid Levels", minval = 7, maxval = 200, group = grpGrid, tooltip = "50 levels on the default 51,629–83,689 range gives aro
52: usdtPerLevel = investment / nLevels
58: pct = float(i) / float(nLevels - 1)
93: for i = 0 to nLevels - 1
104: for i = 1 to nLevels - 1
111: strategy.entry("L" + str.tostring(i), strategy.long, qty = qty, comment = "Grid_BUY_L" + str.tostring(i))
119: strategy.close("L" + str.tostring(i), comment = "Grid_TP_L" + str.tostring(i))
153: for i = 0 to nLevels - 1
162: if i == 0 or i == nLevels - 1 or i % 5 == 0
183: for i = 0 to nLevels - 1
187: stepApprox = (math.pow(highPrice / lowPrice, 1.0 / float(nLevels - 1)) - 1.0) * 100
196: table.cell(tbl, 1, 2, str.tostring(nLevels) + " (" + gridMode + ")", text_color = color.white, bgcolor = bg)
202: table.cell(tbl, 1, 4, str.tostring(ownedCount) + " / " + str.tostring(nLevels), text_color = ownedCount > 0 ? color.green : color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security yok; repaint/lookahead sorunu yok — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: grid (B2 kuralı). Her seviyede küçük kâr, aralık dışı düşüşte sınırsız zarar; kazanma oranı yapay yüksek, getiri aralık varsayımına bağlı.
