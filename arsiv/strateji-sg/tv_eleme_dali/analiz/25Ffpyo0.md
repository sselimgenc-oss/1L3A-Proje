# Surgical Sweep - Original Restored (`25Ffpyo0`)

- Yazar: Abhivish · Link: https://tr.tradingview.com/script/25Ffpyo0-Surgical-Sweep-Original-Restored/
- Kaynak: 89 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Surgical Sweep - Original Restored", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, max_lines_count=50)
```

## Ne yapıyor
Surgical Sweep (25Ffpyo0): 5/5 onaylı tepe/dip seviyelerinin hacimli (>1.2×SMA20) süpürülüp geri kapanması (önceki mum seviyeyi aştı ve üstte kapattı, bu mum altında kapattı) → short; dip için long. Hafta içi; ters sinyalde dön.

## Koddan kanıt (satır: kod)
```
17: hi = ta.pivothigh(high, lookback, lookback)
18: lo = ta.pivotlow(low, lookback, lookback)
40: sell_signal = high[1] > res_level and close[1] > res_level and close < res_level and is_high_vol
41: buy_signal  = low[1] < sup_level and close[1] < sup_level and close > sup_level and is_high_vol
49: if buy_signal
53: else if sell_signal
56: if sell_signal
60: else if buy_signal
63: purple_trigger = (blue_count == 2 and buy_signal) or (red_count == 2 and sell_signal)
66: if buy_signal and is_weekday
67: strategy.entry("Long", strategy.long)
69: if sell_signal and is_weekday
70: strategy.entry("Short", strategy.short)
73: plotshape(sell_signal, "SELL", shape.labeldown, location.abovebar, color.red, size=size.small, text="SELL", textcolor=color.white)
```

## Repaint / lookahead kontrolü
`ta.pivothigh(high, 5, 5)` 5 mum gecikmeli onay (repaint değil); seviye onaydan sonra kullanılıyor.

## Karar ve gerekçe
Önceki tur gerekçesi: «likidite süpürme pivot girişi (repaint riski)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/sweep_sky.py` olarak çevrilip test edildi.
