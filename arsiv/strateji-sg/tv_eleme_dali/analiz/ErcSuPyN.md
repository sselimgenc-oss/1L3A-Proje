# MultiLayer Acceleration/Deceleration Strategy [Skyrexio] (`ErcSuPyN`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/ErcSuPyN-MultiLayer-Acceleration-Deceleration-Strategy-Skyrexio/
- Kaynak: 217 satır Pine
- Zaman dilimi / pazar: 3h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(title = "MultiLayer Acceleration/Deceleration Strategy [Skyrexio]",  shorttitle = "AC Strategy", overlay = true, format = format.inherit, pyramiding = 5, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippag
```

## Ne yapıyor
MultiLayer Acceleration/Deceleration (ErcSuPyN, Skyrexio): AC osilatörü dönüş desenleri (signal1: AC>0 yükseliş devamı; signal2: AC<0 yükseliş) + trend=1 + kapanış>EMA100 → sinyal tepesine stop-giriş, en çok 5 kademe ekleme; trend dönünce hepsi kapanır.

## Koddan kanıt (satır: kod)
```
71: upFractalPrice = ta.pivothigh(2, 2)
76: downFractalPrice = ta.pivotlow(2, 2)
179: strategy.entry(id = "entry1", direction = strategy.long, stop = ACActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.basecur
182: strategy.entry(id = "entry2", direction = strategy.long, stop = ACActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.basecur
185: strategy.entry(id = "entry3", direction = strategy.long, stop = ACActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.basecur
188: strategy.entry(id = "entry4", direction = strategy.long, stop = ACActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.basecur
191: strategy.entry(id = "entry5", direction = strategy.long, stop = ACActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.basecur
195: strategy.close_all(alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency + '",\n"position": "close",\n"price": "
```

## Repaint / lookahead kontrolü
Pivot: satır 71: `upFractalPrice = ta.pivothigh(2, 2)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/accel_ml.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. PDF: BTCUSDT 3 saat.
