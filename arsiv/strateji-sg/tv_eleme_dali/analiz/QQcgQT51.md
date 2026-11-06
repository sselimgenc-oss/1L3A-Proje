# Bullish Divergent Bar DCA Strategy [Skyrexio] (`QQcgQT51`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/QQcgQT51-Bullish-Divergent-Bar-DCA-Strategy-Skyrexio/
- Kaynak: 195 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
6: strategy(title = "Bullish Divergent Bar DCA Strategy [Skyrexio]",  shorttitle = "BDB DCA", overlay = true, format = format.inherit, pyramiding = 4, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.cash, default_qty_value = 0, initial_capital = 10000, currency = currency.USDT, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 5, use_bar_magnifier = tr
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=4`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
10: pyramiding = 4,
178: strategy.exit(id = 'entry1', from_entry = 'entry1', limit = takeProfitLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' 
179: strategy.exit(id = 'entry2', from_entry = 'entry2', limit = takeProfitLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' 
180: strategy.exit(id = 'entry3', from_entry = 'entry3', limit = takeProfitLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' 
181: strategy.exit(id = 'entry4', from_entry = 'entry4', limit = takeProfitLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' 
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
