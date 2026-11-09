# [3Commas] INTCUSDT Long DCA — RSI Exit (`GhH6mW5c`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/GhH6mW5c-3Commas-Silicon-Vault-Long-INTC-DCA-Strategy/
- Kaynak: 415 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
30: strategy( title                   = "[3Commas] INTCUSDT Long DCA — RSI Exit", shorttitle              = "INTC DCA Long", overlay                 = true, pyramiding              = 9,         // 1 BO + 8 SO initial_capital         = 500, default_qty_type        = strategy.cash, default_qty_value       = 11.25, commission_type         = strategy.commission.percent, commission_value        = 0.06,      // Bitget USDT-M t
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=9`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
34: pyramiding              = 9,         // 1 BO + 8 SO
49: maxSO    = input.int  (8,     "Max Safety Orders",  minval = 0, maxval = 20, group = "DCA / Safety Orders")
90: rsiVal = request.security(syminfo.tickerid, rsiTF, ta.rsi(close, rsiLen)[1], lookahead = barmerge.lookahead_on)
135: while soCount < maxSO
136: nextSO = soCount + 1
137: trig   = soTriggerPrice(nextSO)
139: v = soVolume(nextSO)
141: strategy.entry("SO" + str.tostring(nextSO), strategy.long, qty = q, limit = trig)
144: soCount     := nextSO
155: strategy.close_all(comment = useExitRsi ? "TP+RSI" : "TP")
214: so1Px = inDeal and maxSO >= 1 ? soTriggerPrice(1) : na
215: so2Px = inDeal and maxSO >= 2 ? soTriggerPrice(2) : na
216: so3Px = inDeal and maxSO >= 3 ? soTriggerPrice(3) : na
217: so4Px = inDeal and maxSO >= 4 ? soTriggerPrice(4) : na
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
