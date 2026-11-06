# CASCADE DCA 🌊 — Spot Long 1.4 (`id8IPHdu`)

- Yazar: neurodoc · Link: https://www.tradingview.com/script/id8IPHdu/
- Kaynak: 1329 satır Pine
- Zaman dilimi / pazar: 15dk–4s (betiğin sembol/süresine göre) · tek sembol (kripto/hisse tokeni/altın)
- **Karar: ELE**

## strategy() bildirimi
```
33: strategy( title             = "CASCADE DCA 🌊 — Spot Long 1.4", shorttitle        = "CASCADE DCA", overlay           = true, pyramiding        = 50,           // Permite hasta 50 entradas simultáneas default_qty_type  = strategy.fixed, default_qty_value = 1, initial_capital   = 10000, commission_type   = strategy.commission.percent, commission_value  = 0.1,          // 0.1% comisión típica de exchanges spot slippage  
```

## Ne yapıyor
Spot/vadeli long DCA botu şablonu: RSI sinyalinde taban emri açar, fiyat taban girişten ardışık sapma yüzdeleri kadar düşünce EK (ortalama) emirler ekler (katlamalı (doubling/martingale katsayısı) büyüklük; `pyramiding=50`), çıkışı ORTALAMA maliyete göre sabit kâr hedefiyle yapar. Zarar-durdur yok: pozisyon hedefe dönene kadar tutulur ve eklenir (kuyruk riski gizli). Webhook alanları (botId/emailToken) 3Commas DCA botuna sinyal yollamak içindir.

## Koddan kanıt (satır: kod)
```
37: pyramiding        = 50,           // Permite hasta 50 entradas simultáneas
1014: exit_signal = in_profit and (impulse_dead or (use_st_exit and st_bear_flip))
1029: strategy.close_all(comment="🏁 Exit")
1031: strategy.close_all(comment="⚖️ BE Exit")
```

## Repaint / lookahead kontrolü
request.security'de `lookahead_off` ya da `[1]` ofsetli `lookahead_on` ile (önceki kapanmış mum) kullanılıyor; yeniden çizen pivot/zigzag yok. Repaint SORUNU YOK — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2 kuralı). Taban emir + ek emirler + ortalama maliyetten çıkış kuyruk riskini gizler: kazanma oranı ve kâr faktörü şişer, tek bir derin düşüşte tüm ek emirler dolar. Girişin kendisi (RSI eşiği) ayrı test edilebilir ama bu betiğin sonucu DCA yapısına ait.
