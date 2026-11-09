# Daily Close Comparison Strategy (by ChartArt) (`XK8XbDhT`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/XK8XbDhT-Daily-Close-Comparison-Strategy-by-ChartArt-via-sirolf2009/
- Kaynak: 59 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Daily Close Comparison Strategy (by ChartArt)", shorttitle="CA_-_Daily_Close_Strat", overlay=false)
```

## Ne yapıyor
Daily Close Comparison (XK8XbDhT, ChartArt): son günün kapanışı bir öncekinden yüksekse long, düşükse short (eşik 0).

## Koddan kanıt (satır: kod)
```
55: strategy.entry("Long", strategy.long)
59: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 38: `yesterday=security(tickerid, 'D', close[1])`; satır 39: `today=security(tickerid, 'D', close)`. lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/gunluk_kapanis.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Betik günlük kapanışlara bakar; günlük. Eşik 0 yerine 0.0001 (sayısal ±%20 testi için sıfırdan farklı).
