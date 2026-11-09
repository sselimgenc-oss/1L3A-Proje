# Velocity Breakout Strategy (VBS) (`m1JDhFR9`)

- Yazar: vasanth_mvk · Link: https://tr.tradingview.com/script/m1JDhFR9-Velocity-Breakout-Strategy-VBS/
- Kaynak: 342 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
8: strategy("Velocity Breakout Strategy (VBS)", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05, max_labels_count=500, max_lines_count=100, max_boxes_count=100, max_bars_back=1000)
```

## Ne yapıyor
Velocity Breakout Strategy (m1JDhFR9): EMA20/EMA50 trendinde; giriş: altın kesişim (yapı filtreli, ≤%10 koşu), EMA'ya geri çekilip yön mumu (discount bölgesinde, ATR izleyen stop yeşil) ya da sıkışma (4 mum içeride) kırılımı; çıkış: UT-benzeri ATR izleyen stop kırılımı (kârdayken ve ADX<20 ise sıkı 1.5 ATR) ya da ölüm kesişimi. Yalnız long.

## Koddan kanıt (satır: kod)
```
193: ph = ta.pivothigh(high, pivotBars, pivotBars)
194: pl = ta.pivotlow(low, pivotBars, pivotBars)
246: strategy.entry("Long", strategy.long)
253: strategy.close("Long", comment="Trail Exit")
256: strategy.close("Long", comment="Macro Break")
```

## Repaint / lookahead kontrolü
Pivot: satır 193: `ph = ta.pivothigh(high, pivotBars, pivotBars)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/vbs.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
