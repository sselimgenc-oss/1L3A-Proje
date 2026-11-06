# RSI Dip + EMA Trend Long DCA — Leveraged Strategy (`Tl9RRJAT`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/Tl9RRJAT-RSI-Dip-EMA-Trend-Long-DCA-Strategy/
- Kaynak: 280 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
16: strategy("RSI Dip + EMA Trend Long DCA — Leveraged Strategy", shorttitle = "RSIEMA-L", overlay = true, initial_capital = 10000, default_qty_type = strategy.cash, default_qty_value = 1500, pyramiding = 5, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 3, process_orders_on_close = true, calc_on_every_tick = false, max_labels_count = 500, max_lines_count = 100)
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=5`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Ortalama maliyetten bir zarar-durdur (SL) çıkışı var ama ek emirler yine de eklenir. Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
16: strategy("RSI Dip + EMA Trend Long DCA — Leveraged Strategy", shorttitle = "RSIEMA-L", overlay = true, initial_capital = 10000, default_qty_type = str
123: entryRsi      = request.security(syminfo.tickerid, entryRsiTF, ta.rsi(close, entryRsiLen), lookahead = barmerge.lookahead_off)
124: entryCrossDown = entryRsi[1] > entryRsiLevel and entryRsi <= entryRsiLevel
130: entrySignal = entryCrossDown and condTrend
199: strategy.close_all(comment = "SL")
207: strategy.close_all(comment = "MaxHold")
219: strategy.close_all(comment = "TP_Trail")
244: label.new(x = bar_index + 8, y = px, text = "SO" + str.tostring(k) + "  -" + str.tostring(dev, "#.##") + "%", style = label.style_label_left, color = 
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
