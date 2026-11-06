# Simple Harmonic Pattern Strategy (`edChhkxo`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/edChhkxo-Harmonic-Pulse-XABCD-Fibonacci-Pattern-Strategy/
- Kaynak: 205 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Simple Harmonic Pattern Strategy", shorttitle="Harmonic (Simple)", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, commission_type=strategy.commission.percent, commission_value=0.05, pyramiding=1)
```

## Ne yapıyor
Simple Harmonic Pattern (edChhkxo): 4 mumluk onaylı pivotlardan zigzag (aynı yönlü pivotta daha uç olan korunur); son 5 pivot X-A-B-C-D oranları Gartley/Bat/Butterfly/Crab'e 4 orandan en az 3'ü (±0.10) uyarsa, D pivotu onaylandığında (4 mum gecikmeli) desen yönünde giriş; stop X ∓ 0.25 ATR, hedef 2R (D'den). 5 mum bekleme. Pivotlar sonradan değişmez (repaint yok).

## Koddan kanıt (satır: kod)
```
59: float pivHigh = ta.pivothigh(high, zigLen, zigLen)
60: float pivLow  = ta.pivotlow(low, zigLen, zigLen)
190: strategy.entry("Long", strategy.long, comment=pname)
191: strategy.exit("Long Exit", "Long", stop=stopPrice, limit=target)
194: strategy.entry("Short", strategy.short, comment=pname)
195: strategy.exit("Short Exit", "Short", stop=stopPrice, limit=target)
203: "\nOpen trades: " + str.tostring(strategy.opentrades) + "\nClosed trades: " + str.tostring(strategy.closedtrades)
```

## Repaint / lookahead kontrolü
Pivot: satır 59: `float pivHigh = ta.pivothigh(high, zigLen, zigLen)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/harmonik.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
