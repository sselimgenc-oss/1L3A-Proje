# XAU Grid Bot — Long Strategy (`bjoh9PTd`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/bjoh9PTd-XAU-Grid-Bot-Long-Strategy/
- Kaynak: 203 satır Pine
- Zaman dilimi / pazar: 15dk–1s · tek sembol
- **Karar: ELE**

## strategy() bildirimi
```
10: strategy("XAU Grid Bot — Long Strategy", shorttitle = "XAU Grid", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 42, pyramiding = 50, commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 5, process_orders_on_close = true, calc_on_every_tick = false)
```

## Ne yapıyor
Izgara (grid) botu: sabit fiyat aralığını 48 seviyeye böler; fiyat her seviyenin altına inince o seviyede long alır, bir üst seviyeye çıkınca satar (`pyramiding=50`). Giriş sinyali / trend filtresi yok, stop yok: aralığın altına düşen fiyatta tüm seviyeler dolu kalır.

## Koddan kanıt (satır: kod)
```
10: strategy("XAU Grid Bot — Long Strategy", shorttitle = "XAU Grid", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_q
20: nLevels    = input.int(48, "Grid Levels", minval = 5, maxval = 50, group = grpGrid, tooltip = "Number of price levels between High and Low. Capped at 
50: usdtPerLevel = investment / nLevels
56: pct = float(i) / float(nLevels - 1)
91: for i = 0 to nLevels - 1
102: for i = 1 to nLevels - 1
110: strategy.entry("L" + str.tostring(i), strategy.long, qty = qty, comment = "Grid_BUY_L" + str.tostring(i))
118: strategy.close("L" + str.tostring(i), comment = "Grid_TP_L" + str.tostring(i))
151: for i = 0 to nLevels - 1
158: if i == 0 or i == nLevels - 1 or i % 8 == 0
177: for i = 0 to nLevels - 1
186: table.cell(tbl, 1, 2, str.tostring(nLevels) + " (" + gridMode + ")", text_color = color.white, bgcolor = bg)
188: table.cell(tbl, 1, 3, str.tostring(ownedCount) + " / " + str.tostring(nLevels), text_color = ownedCount > 0 ? color.green : color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security yok; repaint/lookahead sorunu yok — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: grid (B2 kuralı). Her seviyede küçük kâr, aralık dışı düşüşte sınırsız zarar; kazanma oranı yapay yüksek, getiri aralık varsayımına bağlı.
