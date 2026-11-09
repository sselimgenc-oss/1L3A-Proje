# McGinley T3 Flow Campaign [NICK789] (`Hrc7Gfqe`)

- Yazar: NICK789 · Link: https://tr.tradingview.com/script/Hrc7Gfqe-McGinley-T3-Flow-Campaign-NICK789-v-1/
- Kaynak: 731 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy( title="McGinley T3 Flow Campaign [NICK789]", shorttitle="McG T3 Flow Campaign", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=30, commission_type=strategy.commission.percent, commission_value=0.05, initial_capital=100000, margin_long=0, margin_short=0, process_orders_on_close=true, pyramiding=0, max_lines_count=500, max_labels_count=500 )
```

## Ne yapıyor
McGinley T3 Flow Campaign (Hrc7Gfqe): McGinley Dynamic(65) ± 1.2×ATR(28) kilitli 'flow trail'; trail 2 mum öncesinin üstüne/altına geçince long/short (ters sinyalde dön); kampanya hedefleri: birim=max(|kapanış−trail|, 0.25 ATR200); %30/%30/%40 kademeli TP1/TP2/TP3 = 1R/2R/3R (3 bacak); stop varsayılanda sadece görsel (canlı değil).

## Koddan kanıt (satır: kod)
```
154: closedTrades = strategy.closedtrades
177: tradeCount = strategy.closedtrades
303: strategy.close("Short", comment="Short Exit", alert_message=f_json("exit_sell", 100.0, na, na))
304: strategy.entry("Long", strategy.long, comment="Long", alert_message=f_json("buy", 0.0, na, na))
320: strategy.close("Long", comment="Long Exit", alert_message=f_json("exit_buy", 100.0, na, na))
321: strategy.entry("Short", strategy.short, comment="Short", alert_message=f_json("sell", 0.0, na, na))
339: strategy.close("Long", comment="Long SL", alert_message=f_json("exit_buy", 100.0, na, liveLongSL))
348: strategy.close("Long", comment="Long TP1", qty_percent=safeT1, alert_message=f_json("exit_buy", safeT1, liveLongT1, liveLongSL))
360: strategy.close("Long", comment="Long TP2", qty_percent=safeT2, alert_message=f_json("exit_buy", safeT2, liveLongT2, liveLongSL))
372: strategy.close("Long", comment="Long TP3", qty_percent=safeT3, alert_message=f_json("exit_buy", safeT3, liveLongT3, liveLongSL))
382: strategy.close("Short", comment="Short SL", alert_message=f_json("exit_sell", 100.0, na, liveShortSL))
391: strategy.close("Short", comment="Short TP1", qty_percent=safeT1, alert_message=f_json("exit_sell", safeT1, liveShortT1, liveShortSL))
403: strategy.close("Short", comment="Short TP2", qty_percent=safeT2, alert_message=f_json("exit_sell", safeT2, liveShortT2, liveShortSL))
415: strategy.close("Short", comment="Short TP3", qty_percent=safeT3, alert_message=f_json("exit_sell", safeT3, liveShortT3, liveShortSL))
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/mcg_flow.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
