# [3Commas] Gold DCA Long — XAUT/USDT (`j36wYVnI`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/j36wYVnI-3Commas-Gold-Vault-Long/
- Kaynak: 257 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
25: strategy( title                   = "[3Commas] Gold DCA Long — XAUT/USDT", shorttitle              = "Gold DCA Long", overlay                 = true, pyramiding              = 4,         // 1 BO + 3 SO initial_capital         = 500, default_qty_type        = strategy.cash, default_qty_value       = 12, commission_type         = strategy.commission.percent, commission_value        = 0.1,       // Bybit spot taker slip
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=4`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
29: pyramiding              = 4,         // 1 BO + 3 SO
43: maxSO    = input.int  (4,    "Max Safety Orders",  minval = 0, maxval = 15, group = "DCA / Safety Orders")
117: while soCount < maxSO
118: nextSO = soCount + 1
119: trig   = soTriggerPrice(nextSO)
121: v = soVolume(nextSO)
123: strategy.entry("SO" + str.tostring(nextSO), strategy.long, qty = q, limit = trig)
126: soCount     := nextSO
136: strategy.close_all(comment = "TP")
152: plot(inDeal and maxSO >= 1 ? soTriggerPrice(1) : na, "SO1", color = soCount >= 1 ? color.new(color.gray, 70) : color.new(color.red, 20), style = plot.
153: plot(inDeal and maxSO >= 2 ? soTriggerPrice(2) : na, "SO2", color = soCount >= 2 ? color.new(color.gray, 70) : color.new(color.red, 35), style = plot.
154: plot(inDeal and maxSO >= 3 ? soTriggerPrice(3) : na, "SO3", color = soCount >= 3 ? color.new(color.gray, 70) : color.new(color.red, 50), style = plot.
162: plotshape(soJustAdded,  "SO Fill",   shape.triangledown, location.abovebar, color = color.new(color.red,      0), size = size.small,  text = "SO",  te
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
