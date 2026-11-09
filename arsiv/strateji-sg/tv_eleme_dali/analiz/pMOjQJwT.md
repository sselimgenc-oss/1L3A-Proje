# ITF26 B1 — BB Fade SOL 5m (`pMOjQJwT`)

- Yazar: mariellangsaez · Link: https://www.tradingview.com/script/pMOjQJwT/
- Kaynak: 149 satır Pine
- Zaman dilimi / pazar: 5dk · kripto (SOL)
- **Karar: AL**

## strategy() bildirimi
```
22: strategy( title                  = "ITF26 B1 — BB Fade SOL 5m", shorttitle             = "ITF26-B1", overlay                = true, default_qty_type       = strategy.percent_of_equity, default_qty_value      = 125, initial_capital        = 100000, commission_type        = strategy.commission.percent, commission_value       = 0.02, slippage               = 1, calc_on_every_tick     = false, process_orders_on_close = f
```

## Ne yapıyor
Hafta içi 14:00–14:40 UTC: gecikmeli BB(20,2) bandına dokunan ilk mumda band seviyesinde limit emir (fade), hedef orta band, 14:40'ta kapat.

## Koddan kanıt (satır: kod)
```
44: float bb_upper     = bb_mid + 2.0 * bb_dev_raw[1]
45: float bb_lower     = bb_mid - 2.0 * bb_dev_raw[1]
51: bool  in_b1    = h_utc == 14 and m_utc <= 40 and is_weekday
53: bool  b1_end   = h_utc == 14 and m_utc == 40 and is_weekday
68: if in_b1 and not placed and strategy.position_size == 0
69: if not na(bb_upper) and not na(bb_lower) and not na(bb_mid)
70: if high > bb_upper
71: strategy.entry("B1S", strategy.short, qty = sz, limit = bb_upper, comment = "BB_Fade↓")
73: ep     := bb_upper
76: else if low < bb_lower
77: strategy.entry("B1L", strategy.long, qty = sz, limit = bb_lower, comment = "BB_Fade↑")
79: ep     := bb_lower
85: strategy.exit("B1L_TP", from_entry = "B1L", limit = tp, comment = "TP→mid")
87: strategy.exit("B1S_TP", from_entry = "B1S", limit = tp, comment = "TP→mid")
```

## Repaint / lookahead kontrolü
Bantlar `[1]` gecikmeli (look-ahead yok). Repaint yok.

## Karar ve gerekçe
Aday (5 dk Binance verisi).
