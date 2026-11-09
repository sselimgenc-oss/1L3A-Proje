# AO/AC Trading Zones Strategy [Skyrexio]  (`Tkrjao7P`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/Tkrjao7P-AO-AC-Trading-Zones-Strategy-Skyrexio/
- Kaynak: 191 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(title = "AO/AC Trading Zones Strategy [Skyrexio] ",  shorttitle = "Trading Zones Strategy", overlay = true, format = format.inherit, pyramiding = 5, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 5
```

## Ne yapıyor
AO/AC Trading Zones (Tkrjao7P, Skyrexio): yeşil bar serisi (kapanış>Alligator dişi, AC ve AO yükseliyor, kapanış>EMA100) 2–6 mum sürerken ve kapanış önceki kapanıştan yüksekse piyasa girişi; açık pozisyon sayısına göre en çok 5 kademe ekleme (entry1..5); trend aşağı dönünce ya da yeşil serinin 5. barının dibi kırılınca hepsi kapanır.

## Koddan kanıt (satır: kod)
```
71: upFractalPrice = ta.pivothigh(2, 2)
76: downFractalPrice = ta.pivotlow(2, 2)
153: strategy.entry(id = "entry1", direction = strategy.long, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency +
156: strategy.entry(id = "entry2", direction = strategy.long, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency +
159: strategy.entry(id = "entry3", direction = strategy.long, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency +
162: strategy.entry(id = "entry4", direction = strategy.long, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency +
165: strategy.entry(id = "entry5", direction = strategy.long, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency +
169: strategy.close_all(alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency + '",\n"position": "close",\n"price": "
```

## Repaint / lookahead kontrolü
Pivot: satır 71: `upFractalPrice = ta.pivothigh(2, 2)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/ao_ac_zones.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. PDF: BTCUSDT 4 saat.
