# SOL RSI DCA — Long Strategy (`ADx8qrBK`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/ADx8qrBK-SOL-RSI-DCA-Long-Strategy/
- Kaynak: 219 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
15: strategy("SOL RSI DCA — Long Strategy", shorttitle = "SOL DCA-L", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 200, pyramiding = 5, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 100)
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=5`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
15: strategy("SOL RSI DCA — Long Strategy", shorttitle = "SOL DCA-L", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_q
25: aoCount    = input.int(3, "Averaging Orders per Trade", minval = 0, maxval = 10, group = grpAO)
110: entryRsi  = request.security(syminfo.tickerid, entryTF, ta.rsi(close, entryRsiLen), lookahead = barmerge.lookahead_off)
146: if inPosition and inWindow and aoFilled < aoCount and not na(baseEntry)
152: strategy.entry("Long_AO_" + str.tostring(nextIdx), strategy.long, qty = aoQtyUsdt / close, comment = "Long_AO_" + str.tostring(nextIdx))
163: strategy.close_all(comment = "TP")
179: for k = 1 to aoCount
200: table.cell(tbl, 1, 2, str.tostring(aoFilled) + " / " + str.tostring(aoCount), text_color = color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
