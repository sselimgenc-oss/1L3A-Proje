# MultiLayer Awesome Oscillator Saucer Strategy [Skyrexio] (`HyzpDR9t`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/HyzpDR9t-MultiLayer-Awesome-Oscillator-Saucer-Strategy-Skyrexio/
- Kaynak: 211 satır Pine
- Zaman dilimi / pazar: 3h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(title = "MultiLayer Awesome Oscillator Saucer Strategy [Skyrexio]",  shorttitle = "AO Saucer", overlay = true, format = format.inherit, pyramiding = 5, calc_on_order_fills = false, calc_on_every_tick = false, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippage 
```

## Ne yapıyor
MultiLayer Awesome Oscillator Saucer (HyzpDR9t, Skyrexio): trend=1 (fraktal kırılımı) iken AO 'tabak' (AO>0, dip dönüşü) + kapanış>EMA100 sinyali; sinyal tepesine stop-giriş; aynı trendde sinyal tekrarladıkça en çok 5 kademe ekleme; trend aşağı dönünce hepsi kapanır.

## Koddan kanıt (satır: kod)
```
71: upFractalPrice = ta.pivothigh(2, 2)
76: downFractalPrice = ta.pivotlow(2, 2)
173: strategy.entry(id = "entry1", direction = strategy.long, stop = saucerActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.bas
176: strategy.entry(id = "entry2", direction = strategy.long, stop = saucerActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.bas
179: strategy.entry(id = "entry3", direction = strategy.long, stop = saucerActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.bas
182: strategy.entry(id = "entry4", direction = strategy.long, stop = saucerActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.bas
185: strategy.entry(id = "entry5", direction = strategy.long, stop = saucerActivationLevel + syminfo.mintick,  alert_message = '{\n"base": "' + syminfo.bas
189: strategy.close_all(alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency + '",\n"position": "close",\n"price": "
```

## Repaint / lookahead kontrolü
Pivot: satır 71: `upFractalPrice = ta.pivothigh(2, 2)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/saucer_ml.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. PDF: BTCUSDT 3 saat.
