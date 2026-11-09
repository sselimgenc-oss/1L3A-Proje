# Hybrid Breakout (`hezSShJr`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/hezSShJr-Hybrid-Breakout-VCP-Inspired-Trend/
- Kaynak: 115 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
8: strategy("Hybrid Breakout", overlay=true, initial_capital=100000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05, process_orders_on_close=true)
```

## Ne yapıyor
Hybrid Breakout (hezSShJr): 50>150>200 SMA yükselen trend + dar aralık (sıkışma) + hacim genişlemesi → son 3 barın zirvesinde stop-giriş; %8 stop, kâr al kademeleri (%10/%20/%30) tek ortalama hedef %20 olarak modellendi.

## Koddan kanıt (satır: kod)
```
89: strategy.entry("Long", strategy.long, stop=recentHigh[1])
101: strategy.exit("TP1", "Long", qty_percent=25,  stop=stopLevel, limit=target1)
102: strategy.exit("TP2", "Long", qty_percent=50,  stop=stopLevel, limit=target2)
103: strategy.exit("TP3", "Long", qty_percent=100, stop=stopLevel, limit=target3)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/hybrid_brk.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (200 gün SMA, Minervini tarzı), yalnız long.
