# Signal Engine Quantum Edge (`n9ty3SVh`)

- Yazar: Quantum-Edge-Capital · Link: https://tr.tradingview.com/script/n9ty3SVh-Super-trend-Signal-Engine-Strat-QUANTUM-EDGE/
- Kaynak: 185 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy('Signal Engine Quantum Edge', overlay = true)
```

## Ne yapıyor
Signal Engine Quantum Edge (n9ty3SVh): KivancOzbilgic tarzı SuperTrend (ATR 15, çarpan 9.1, kaynak hl2) yön değişiminde long/short; hep piyasada.

## Koddan kanıt (satır: kod)
```
71: buySignal = trend == 1 and trend[1] == -1
72: sellSignal = trend == -1 and trend[1] == 1
81: plotshape(buySignal ? up : na, title = 'UpTrend Begins', location = location.absolute, style = shape.circle, size = size.tiny, color = C_Bull)
82: plotshape(sellSignal ? dn : na, title = 'DownTrend Begins', location = location.absolute, style = shape.circle, size = size.tiny, color = C_Bear)
83: plotshape(buySignal and showsignals ? up : na, title = 'Buy', text = 'Buy', location = location.absolute, style = shape.labelup, size = size.tiny, col
84: plotshape(sellSignal and showsignals ? dn : na, title = 'Sell', text = 'Sell', location = location.absolute, style = shape.labeldown, size = size.tiny
102: if buySignal and window()
103: strategy.entry('BUY', strategy.long)
104: if sellSignal and window()
105: strategy.entry('SELL', strategy.short)
110: buy1 = ta.barssince(buySignal)
111: sell1 = ta.barssince(sellSignal)
124: fast_val = request.security(syminfo.tickerid, tf, f_ma(close, fastLen), lookahead = barmerge.lookahead_off)
125: slow_val = request.security(syminfo.tickerid, tf, f_ma(close, slowLen), lookahead = barmerge.lookahead_off)
```

## Repaint / lookahead kontrolü
SuperTrend; tablo için `request.security(...lookahead_off)` yalnız görsel. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/quantum_st.py` olarak çevrilip test edildi.
