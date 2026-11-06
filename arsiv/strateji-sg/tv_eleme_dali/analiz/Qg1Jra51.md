# RSI Bullish Divergence (Oversold) Breakout (`Qg1Jra51`)

- Yazar: sunnychalloo · Link: https://tr.tradingview.com/script/Qg1Jra51-RSI-Bullish-Divergence-Oversold-Breakout/
- Kaynak: 181 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("RSI Bullish Divergence (Oversold) Breakout", shorttitle = "RSI BullDiv BO", overlay = true, initial_capital = 1000000, default_qty_type = strategy.percent_of_equity, default_qty_value = 100, commission_type = strategy.commission.percent, commission_value = 0.03, pyramiding = 0, margin_long = 0, margin_short = 0, max_lines_count = 500, max_labels_count = 500)
```

## Ne yapıyor
RSI Bullish Divergence (Oversold) Breakout (Qg1Jra51): iki ardışık RSI dibi (5/5 pivot, ilk dip <30, ikincisi daha yüksek RSI ama fiyatta daha düşük dip, aralarında 5–60 mum) → RSI iki dip arasındaki RSI zirvesini yukarı kırarsa long; hedef iki dip arası fiyat zirvesi, stop 2. dibin altı. Yalnız long; her karar yalnız kapanmış mumlarla.

## Koddan kanıt (satır: kod)
```
74: leftOk(int p) =>
86: rightOk(int p, int k) =>
138: if leftOk(pc) and rightOk(pc, lbR)
150: if leftOk(bar_index - k) and rightOk(bar_index - k, k)
169: strategy.entry("BullDiv", strategy.long)
```

## Repaint / lookahead kontrolü
Pivotlar `lbR` mum gecikmeli; 'early' modu yalnız k<lbR sağ mumla onaylı pivotu kullanır (gelecek mum yok). Betik 'No look-ahead' diyor ve kod bunu doğruluyor.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/rsi_bulldiv.py` olarak çevrilip test edildi.
