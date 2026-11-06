# [3Commas] GOOGLUSDT Long DCA — RSI Exit (`8K1gTPV0`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/8K1gTPV0-3Commas-Equity-Pulse-Long-DCA-on-Tokenized-Stocks/
- Kaynak: 258 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
25: strategy( title                   = "[3Commas] GOOGLUSDT Long DCA — RSI Exit", shorttitle              = "GOOGL DCA Long", overlay                 = true, pyramiding              = 9,         // 1 BO + 8 SO initial_capital         = 500, default_qty_type        = strategy.cash, default_qty_value       = 13.5, commission_type         = strategy.commission.percent, commission_value        = 0.06,      // Bitget USDT-M 
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=9`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
29: pyramiding              = 9,         // 1 BO + 8 SO
44: maxSO    = input.int  (8,    "Max Safety Orders",  minval = 0, maxval = 20, group = "DCA / Safety Orders")
81: rsiVal = request.security(syminfo.tickerid, rsiTF, ta.rsi(close, rsiLen)[1], lookahead = barmerge.lookahead_on)
129: while soCount < maxSO
130: nextSO = soCount + 1
131: trig   = soTriggerPrice(nextSO)
133: v = soVolume(nextSO)
135: strategy.entry("SO" + str.tostring(nextSO), strategy.long, qty = q, limit = trig)
138: soCount     := nextSO
149: strategy.close_all(comment = useExitRsi ? "TP+RSI" : "TP")
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
