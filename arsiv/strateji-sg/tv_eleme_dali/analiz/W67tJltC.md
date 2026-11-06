# Multi-Factor Adaptive Z-Score Strategy (`W67tJltC`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/W67tJltC-Z-Edge-Confluence-Z-score-Strategy/
- Kaynak: 188 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Multi-Factor Adaptive Z-Score Strategy", shorttitle="MFZ-Score Strategy", overlay=false, initial_capital=10000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, process_orders_on_close=true)
```

## Ne yapıyor
Multi-Factor Adaptive Z-Score (W67tJltC): ROC+RSI+hacim z-skorlarının uyarlamalı yumuşatılmış bileşiği sıfırı keserse giriş (ATR×2 stop), ters sıfır kesişiminde çıkış. process_orders_on_close=true.

## Koddan kanıt (satır: kod)
```
102: plFound = ta.pivotlow(smoothComposite,piv_left,piv_right)
103: phFound = ta.pivothigh(smoothComposite,piv_left,piv_right)
153: strategy.entry("Long",strategy.long,qty=positionSizeUnits)
155: strategy.exit("Long Stop", "Long",stop = stopLossLong)
159: strategy.entry("Short", strategy.short, qty = positionSizeUnits)
161: strategy.exit("Short Stop", "Short", stop = stopLossShort)
165: strategy.close("Long")
168: strategy.close("Short")
```

## Repaint / lookahead kontrolü
Pivot: satır 102: `plFound = ta.pivotlow(smoothComposite,piv_left,piv_right)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/zscore.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
