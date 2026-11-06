# Volume-Confirmed Support/Resistance Breakout Strategy (`CItvSvqk`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/CItvSvqk-Breakout-Pulse-Volume-Confirmed-Support-Resistance-Strategy/
- Kaynak: 164 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
3: strategy("Volume-Confirmed Support/Resistance Breakout Strategy", shorttitle = "Vol S/R Breakout", overlay = true, initial_capital = 10000, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, commission_type = strategy.commission.percent, commission_value = 0.01, slippage = 2, pyramiding = 0)
```

## Ne yapıyor
Hacim Onaylı Destek/Direnç Kırılımı (CItvSvqk): 10/10 pivot direnci hacim 1.5×ort. + EMA200 üstünde yukarı kırılırsa long (destek aşağı kırılırsa short); stop = kırılan destek − 0.25 ATR, hedef ATR×3.

## Koddan kanıt (satır: kod)
```
65: float ph = ta.pivothigh(high, pivotLeft, pivotRight)
66: float pl = ta.pivotlow(low, pivotLeft, pivotRight)
103: strategy.entry("Long", strategy.long)
109: strategy.entry("Short", strategy.short)
118: strategy.exit("Long Exit", "Long", stop = longStopPrice, limit = longTgtPrice)
121: strategy.exit("Short Exit", "Short", stop = shortStopPrice, limit = shortTgtPrice)
```

## Repaint / lookahead kontrolü
Pivot: satır 65: `float ph = ta.pivothigh(high, pivotLeft, pivotRight)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/hacim_sr.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik. Pivotlar 10 bar sonra onaylanır (repaint yok).
