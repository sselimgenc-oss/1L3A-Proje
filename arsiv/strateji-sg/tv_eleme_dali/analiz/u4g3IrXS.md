# Multi Long Bot — Single-Pair Replica (`u4g3IrXS`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/u4g3IrXS-3Commas-Triple-RSI-DCA-Long-Risk-Adjusted-Averaging-Strategy/
- Kaynak: 168 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
47: strategy("Multi Long Bot — Single-Pair Replica", overlay                 = true, initial_capital         = 200, default_qty_type        = strategy.cash, default_qty_value       = 20.075, commission_type         = strategy.commission.percent, commission_value        = 0.1,        // Neutral default — adjust per venue (see header notes) slippage                = 5, pyramiding              = 4,          // BO + 3 SO cur
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (sabit ya da kademeli büyüklük; `pyramiding=4`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
55: pyramiding              = 4,          // BO + 3 SO
61: maxSO     = input.int  (3,      "Max Safety Orders",                minval = 0, maxval = 10,     group = "USD-Multi — Order Sizing")
96: entryRsi    = request.security(syminfo.tickerid, entryTF, ta.rsi(close, entryLen)[1], lookahead = barmerge.lookahead_on)
97: entrySignal = useEntryRsi ? ta.crossover(entryRsi, entryThr) : true
113: nextDev = nextIdx > 0 and nextIdx <= maxSO ? f_cumDev(nextIdx) : na
131: if inWindow and strategy.position_size > 0 and soFilled < maxSO and not na(nextPx)
135: strategy.entry("SO" + str.tostring(nextIdx), strategy.long, qty = qty)
145: strategy.close_all(comment = "TP")
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
