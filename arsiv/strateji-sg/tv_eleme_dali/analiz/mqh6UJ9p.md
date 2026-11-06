# ATR_RSI_Strategy v2[liwei666] (`mqh6UJ9p`)

- Yazar: liwei666 · Link: https://www.tradingview.com/script/mqh6UJ9p-ATR-RSI-Strategy-v2-with-no-repaint-liwei666/
- Kaynak: 99 satır Pine
- Zaman dilimi / pazar: 15dk · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
6: strategy( title                = "ATR_RSI_Strategy v2[liwei666]", shorttitle           = "ATR_RSI_Strategy", overlay              =  true, max_lines_count                 =  500, max_labels_count                =  500, max_boxes_count                 =  500, max_bars_back = 5000, initial_capital = 10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, commission_type=strategy.commission.percent, py
```

## Ne yapıyor
ATR>ATR-SMA(45) ve ATR-SMA/fiyat %0.3–0.7, RSI(15)>60 long / <40 short; tepeden %1.5 izleyen stop, hedef long %3 / short %6.

## Koddan kanıt (satır: kod)
```
27: atr_ma_norm_min = input.float(0.3, "atr_ma_norm_min", minval = 0.1, maxval = 0.5, step=0.1)
28: atr_ma_norm_max = input.float(0.7, "atr_ma_norm_max", minval = 0.5, maxval = 1, step=0.1)
29: trailing_percent= input.float(1.5, "trailing_stop_percent", minval = 0.1, maxval = 2, step=0.1)
44: atr_ma_norm = atr_ma / close * 100
58: if atr_ma_norm >= atr_ma_norm_min and atr_ma_norm <= atr_ma_norm_max
61: strategy.entry("B1", strategy.long, limit = close + 5 )
64: strategy.entry("S1", strategy.short, limit = close - 5 )
71: long_sl := intra_trade_high * (1 - trailing_percent / 100)
73: strategy.exit("Exit B1", from_entry="B1", stop = long_sl, limit = long_tp)
79: short_sl := intra_trade_low * (1 + trailing_percent / 100)
81: strategy.exit("Exit S1", from_entry="S1", stop = short_sl, limit = short_tp)
```

## Repaint / lookahead kontrolü
Repaint yok. Giriş `limit=close+5` — piyasa girişi olarak uygulandı (sembol fiyatına bağlı sabit puan).

## Karar ve gerekçe
Aday.
