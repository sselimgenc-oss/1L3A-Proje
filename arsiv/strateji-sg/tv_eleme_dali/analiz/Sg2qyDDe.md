# Smart Trend Strategy | julzALGO (`Sg2qyDDe`)

- Yazar: julzALGO · Link: https://tr.tradingview.com/script/Sg2qyDDe-Smart-Trend-Strategy-julzALGO/
- Kaynak: 594 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy( "Smart Trend Strategy | julzALGO", shorttitle=" STS", overlay=true, fill_orders_on_standard_ohlc=true, pyramiding=0, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0, slippage=15, process_orders_on_close=true, max_lines_count=250, max_labels_count=250, max_boxes_count=50, max_bars_back=5000 )
```

## Ne yapıyor
Smart Trend Strategy julzALGO (Sg2qyDDe): KAMA→Kalman filtreli trend yönü (yükselen/düşen), 10/10 pivot yapı kırılımları (BOS: trend yönünde, CHoCH: ters yöne kırılım; kapanışla); trend dönüşü ya da BOS/CHoCH, ters yönde 10 mum içinde BOS/CHoCH ile birlikteyse giriş (kapanışta); stop 3 ATR, hedef long 2R / short 1R; ters sinyalde kapat. process_orders_on_close.

## Koddan kanıt (satır: kod)
```
130: float pivotHigh = ta.pivothigh(high, pivotLen, pivotLen)
131: float pivotLow = ta.pivotlow(low, pivotLen, pivotLen)
366: strategy.close("Short")
369: strategy.close("Long")
391: strategy.entry("Long", strategy.long)
392: strategy.exit("Long Exit", "Long", stop=activeStop, limit=activeTarget)
414: strategy.entry("Short", strategy.short)
415: strategy.exit("Short Exit", "Short", stop=activeStop, limit=activeTarget)
418: strategy.exit("Long Exit", "Long", stop=activeStop, limit=activeTarget)
421: strategy.exit("Short Exit", "Short", stop=activeStop, limit=activeTarget)
```

## Repaint / lookahead kontrolü
Pivot: satır 130: `float pivotHigh = ta.pivothigh(high, pivotLen, pivotLen)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/smart_trend.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş (7 günlük pencere = gün içi/saatlik); saatlik.
