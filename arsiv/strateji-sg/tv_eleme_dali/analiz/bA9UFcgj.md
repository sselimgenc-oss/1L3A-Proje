# SPY Bear Regime Short System (`bA9UFcgj`)

- Yazar: thetrading · Link: https://www.tradingview.com/script/bA9UFcgj-SPY-Bear-Regime-Short-System/
- Kaynak: 90 satır Pine
- Zaman dilimi / pazar: 1g · ABD (SPY)
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("SPY Bear Regime Short System", overlay    = true, shorttitle = "BRSM", initial_capital      = 10000, default_qty_type     = strategy.percent_of_equity, default_qty_value    = 100, commission_type      = strategy.commission.percent, commission_value     = 0.05, slippage             = 1, process_orders_on_close = false, calc_on_every_tick   = false)
```

## Ne yapıyor
SMA250'nin %2+ altında, SMA5 üstünde, RSI(3) 70'i yukarı keserse short; SMA5 altı ya da SMA250 üstü çıkış.

## Koddan kanıt (satır: kod)
```
30: gap_ok         = close <= ma_long * (1 - gap_pct / 100)
32: entry_signal = below_long_ma and above_short_ma and rsi_cross_ob and gap_ok
36: exit_signal      = exit_below_short or exit_above_long
40: strategy.entry("Short", strategy.short, comment = "SHORT")
```

## Repaint / lookahead kontrolü
Geçmiş mum; repaint yok.

## Karar ve gerekçe
Aday (yalnız short; az işlem beklenir).
