# Volume Order Block Retest Strategy (`ouvmvItR`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/ouvmvItR-Volume-Vault-Volume-Order-Block-Retest-Strategy/
- Kaynak: 201 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("Volume Order Block Retest Strategy", overlay=true, max_boxes_count=100, max_labels_count=100, initial_capital=10000, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=10, commission_type=strategy.commission.percent, commission_value=0.05, slippage=2)
```

## Ne yapıyor
Volume Order Block Retest (ouvmvItR): gövde ≥0.8 ATR ve hacim ≥ SMA20 olan itki mumunun önceki mumu 'order block' bölgesi olur (en çok 15 bölge, 300 mum); fiyat bölgeyi ilk kez yeniden test edip yön mumu (yeşil/kırmızı) kapatırsa giriş; stop bölge ∓0.2 ATR, hedef 1.5R, 1R'de başa-baş, 60 mum zaman stopu. (Pozisyon doluyken bölge tüketimi 'flat' varsayımıyla modellendi.)

## Koddan kanıt (satır: kod)
```
71: bool bullImpulse = close > open and bigBody and bigVol
74: bool bearImpulse = close < open and bigBody and bigVol
96: bool touched = high >= z.bottom and low <= z.top
97: if touched and flat and not (firstTouch and z.used)
142: if bullImpulse and allowLong
146: if bearImpulse and allowShort
167: strategy.entry("Long", strategy.long)
177: strategy.entry("Short", strategy.short)
188: strategy.exit("XL", from_entry="Long", stop=longStop, limit=longTp)
193: strategy.exit("XS", from_entry="Short", stop=shortStop, limit=shortTp)
200: plotshape(bullImpulse, "Bull impulse", shape.triangleup, location.belowbar, color.new(bullCol, 50), size=size.tiny)
201: plotshape(bearImpulse, "Bear impulse", shape.triangledown, location.abovebar, color.new(bearCol, 50), size=size.tiny)
```

## Repaint / lookahead kontrolü
Bölgeler yalnız kapanmış itki mumlarından; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «hacim order block (SMC), 83hmaEOQ temsilci». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/ob_retest.py` olarak çevrilip test edildi.
