# HTF Level Breakout (`PdJvHIfQ`)

- Yazar: vanchesz · Link: https://tr.tradingview.com/script/PdJvHIfQ-HTF-Level-Breakout/
- Kaynak: 240 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("HTF Level Breakout", overlay=true, default_qty_type=strategy.fixed, default_qty_value=1)
```

## Ne yapıyor
HTF Level Breakout (PdJvHIfQ): önceki günün (HTF `high[1]/low[1]`, lookahead_on ama ofsetli → geçerli) tepe/dibi seviye olur; fiyat seviyeye dokununca o mumun ucu 'S1' sayılır, sonraki bir mum seviyenin ve S1'in ötesinde kapanırsa kırılım yönünde giriş; stop son 5/5 pivot dibi/tepesi, hedef 2R. Günde bir seviye kümesi.

## Koddan kanıt (satır: kod)
```
35: htf_high = request.security(syminfo.tickerid, i_htf, high[1], lookahead=barmerge.lookahead_on)
36: htf_low  = request.security(syminfo.tickerid, i_htf, low[1],  lookahead=barmerge.lookahead_on)
37: htf_time = request.security(syminfo.tickerid, i_htf, time,    lookahead=barmerge.lookahead_on)
42: pivot_h = ta.pivothigh(high, i_pivot_left, i_pivot_right)
43: pivot_l = ta.pivotlow (low,  i_pivot_left, i_pivot_right)
132: strategy.entry("Long", strategy.long, qty=qty)
133: strategy.exit("Long Exit", "Long", stop=sl_price, limit=tp_price)
186: strategy.entry("Short", strategy.short, qty=qty)
187: strategy.exit("Short Exit", "Short", stop=sl_price, limit=tp_price)
240: strategy.close_all(comment="Time Exit")
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 35: `htf_high = request.security(syminfo.tickerid, i_htf, high[1], lookahead=barmerge.lookahead_on)`; satır 36: `htf_low  = request.security(syminfo.tickerid, i_htf, low[1],  lookahead=barmerge.lookahead_on)`; satır 37: `htf_time = request.security(syminfo.tickerid, i_htf, time,    lookahead=barmerge.lookahead_on)`. lookahead_on kullanımı ayrıca incelendi (çeviri kapanmış HTF mum esaslı). Pivot: satır 42: `pivot_h = ta.pivothigh(high, i_pivot_left, i_pivot_right)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/htf_level.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. HTF=günlük, betik gün içi grafikte çalışır; saatlik.
