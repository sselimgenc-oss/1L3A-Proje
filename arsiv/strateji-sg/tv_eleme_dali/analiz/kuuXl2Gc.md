# AMZN RSI Oversold Doubling DCA — Long Strategy (`kuuXl2Gc`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/kuuXl2Gc-3Commas-AMZN-RSI-Oversold-Doubling-DCA-Long-Strategy/
- Kaynak: 219 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
17: strategy("AMZN RSI Oversold Doubling DCA — Long Strategy", shorttitle = "AMZN-OS-L", overlay = true, initial_capital = 100000, default_qty_type = strategy.cash, default_qty_value = 500, pyramiding = 6, commission_type = strategy.commission.percent, commission_value = 0.06, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 100)
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=6`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
17: strategy("AMZN RSI Oversold Doubling DCA — Long Strategy", shorttitle = "AMZN-OS-L", overlay = true, initial_capital = 100000, default_qty_type = stra
74: aoCount = 5
108: rsiVal      = request.security(syminfo.tickerid, rsiTF, ta.rsi(close, rsiLen), lookahead = barmerge.lookahead_off)
109: condRSI     = rsiVal < rsiLevel
110: entrySignal = condRSI
145: if inPosition and inWindow and aoFilled < aoCount and not na(baseEntry)
151: strategy.entry("Long_AO_" + str.tostring(nextIdx), strategy.long, qty = aoUsdt / close, comment = "Long_AO_" + str.tostring(nextIdx))
162: strategy.close_all(comment = "TP")
178: for k = 1 to aoCount
198: table.cell(tbl, 1, 1, str.tostring(aoFilled) + " / " + str.tostring(aoCount), text_color = color.white, bgcolor = bg)
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
