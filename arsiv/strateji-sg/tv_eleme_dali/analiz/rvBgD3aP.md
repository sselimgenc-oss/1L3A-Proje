# Elliott Wave Impulse Strategy | Wave 5 & Reversal Entries (`rvBgD3aP`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/rvBgD3aP-Elliott-Wave-Impulse-Strategy-Wave-5-Reversal-Entries/
- Kaynak: 287 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy( title              = "Elliott Wave Impulse Strategy | Wave 5 & Reversal Entries", shorttitle         = "EW-S", overlay            = true, initial_capital    = 10000, default_qty_type   = strategy.percent_of_equity, default_qty_value  = 25, commission_type    = strategy.commission.percent, commission_value   = 0.05, slippage           = 2, pyramiding         = 0, calc_on_every_tick = false, max_bars_back    
```

## Ne yapıyor
Elliott Wave Impulse Strategy (rvBgD3aP): ZigZag (pivothigh/low 5 sol/1 sağ; sağ mum onaylı, repaint yok) son pivotlarından 5 dalgalı itki (reversal) ya da dalga-4 geri çekilişi (wave 5) tespit edilirse zigzag yön değiştirdiğinde giriş; stop son pivot ∓0.2 ATR, hedef (reversal: itkının %50'si; wave 5: dalga 1 boyu), R/R≥1, itki ≥1.5 ATR, 100 mum zaman stopu.

## Koddan kanıt (satır: kod)
```
71: float ph  = ta.pivothigh(high, zzLen, 1)
72: float pl  = ta.pivotlow(low,  zzLen, 1)
229: strategy.entry("EW Long", strategy.long, qty = calcQty(risk), comment = lastType)
230: strategy.exit("X Long", "EW Long", stop = curStop, limit = curTgt)
236: strategy.entry("EW Short", strategy.short, qty = calcQty(risk), comment = lastType)
237: strategy.exit("X Short", "EW Short", stop = curStop, limit = curTgt)
251: strategy.exit("X Long", "EW Long", stop = curStop, limit = curTgt)
253: strategy.close("EW Long", comment = "Time stop")
256: strategy.exit("X Short", "EW Short", stop = curStop, limit = curTgt)
258: strategy.close("EW Short", comment = "Time stop")
276: int   closed  = strategy.closedtrades
```

## Repaint / lookahead kontrolü
Pivot: satır 71: `float ph  = ta.pivothigh(high, zzLen, 1)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/elliott.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
