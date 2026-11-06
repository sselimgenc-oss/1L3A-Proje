# Initial Balance BO Strategy (`zpIyp7KB`)

- Yazar: MIKMani · Link: https://tr.tradingview.com/script/zpIyp7KB-Initial-Balance-BO-Strategy/
- Kaynak: 307 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("Initial Balance BO Strategy", overlay=true, max_lines_count=500, max_boxes_count=500, max_labels_count=500, default_qty_type=strategy.fixed, default_qty_value=1)
```

## Ne yapıyor
Initial Balance (ilk saat) kırılımı.

## Koddan kanıt (satır: kod)
```
5: strategy("Initial Balance BO Strategy", overlay=true, max_lines_count=500, max_boxes_count=500, max_labels_count=500, default_qty_type=strategy.fixed,
8: grp_ib = "═══ Initial Balance Settings ═══"
9: ib_days = input.int(30, "IB History (days to show)", minval=1, maxval=100, group=grp_ib)
11: grp_box = "═══ IB Box & Lines ═══"
13: box_col  = input.color(color.new(color.gray, 75), "IB Box Fill Color",     group=grp_box)
14: line_col = input.color(color.black,               "IBH / IBL Line Color",  group=grp_box)
15: line_w   = input.int(2, "IBH / IBL Line Width", minval=1, maxval=4, group=grp_box)
27: sl_mult   = input.float(0.75, "SL Multiplier (× IB range)", minval=0.1, maxval=2.0, step=0.05, group=grp_entry)
164: lb := label.new(x=ct, y=ib_high, text="IBH  " + str.tostring(ib_high, "#.##"), xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color
170: lb := label.new(x=ct, y=ib_low, text="IBL  " + str.tostring(ib_low, "#.##"), xloc=xloc.bar_time, style=label.style_label_left, color=color.new(color.g
261: strategy.entry("Buy", strategy.long)
274: strategy.entry("Sell", strategy.short)
306: bgcolor(is_in_ib ? color.new(color.gray, 93) : na, title="IB Zone Background")
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
