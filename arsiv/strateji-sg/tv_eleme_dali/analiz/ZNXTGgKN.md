# SOL RSI Reversal DCA — Short Strategy (`ZNXTGgKN`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/ZNXTGgKN-3Commas-SOL-RSI-Reversal-DCA-Short-Strategy/
- Kaynak: 234 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
11: strategy("SOL RSI Reversal DCA — Short Strategy", shorttitle = "SOL DCA-S", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 500, pyramiding = 4, commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 100)
```

## Ne yapıyor
Spot/vadeli short DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar yükselince EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=4`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Ortalama maliyetten bir zarar-durdur (SL) çıkışı var ama ek emirler yine de eklenir. Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
11: strategy("SOL RSI Reversal DCA — Short Strategy", shorttitle = "SOL DCA-S", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash,
21: aoCount    = input.int(3, "Averaging Orders per Trade", minval = 0, maxval = 10, group = grpAO)
65: rsiVal    = request.security(syminfo.tickerid, rsiTF, ta.rsi(close, rsiLen), lookahead = barmerge.lookahead_off)
66: rsiCrossDn = request.security(syminfo.tickerid, rsiTF, ta.crossunder(ta.rsi(close, rsiLen), rsiLevel), lookahead = barmerge.lookahead_off)
148: if inPosition and inWindow and aoFilled < aoCount and not na(baseEntry)
154: strategy.entry("Short_AO_" + str.tostring(nextIdx), strategy.short, qty = aoQtyUsdt / close, comment = "Short_AO_" + str.tostring(nextIdx))
167: strategy.close_all(comment = "SL")
176: strategy.close_all(comment = "TP_Trail")
193: for k = 1 to aoCount
213: table.cell(tbl, 1, 1, str.tostring(aoFilled) + " / " + str.tostring(aoCount), text_color = color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
