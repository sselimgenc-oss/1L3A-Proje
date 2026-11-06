# Strategy for Squeeze Momentum Indicator [LazyBear] (`qp9BoNyS`)

- Yazar: 03.freeman · Link: https://tr.tradingview.com/script/qp9BoNyS/
- Kaynak: 106 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
10: strategy(shorttitle = "SQZMOM_LB", title="Strategy for Squeeze Momentum Indicator [LazyBear]", overlay=false, calc_on_every_tick=true, pyramiding=0,default_qty_type=strategy.percent_of_equity,default_qty_value=100,currency=currency.USD)
```

## Ne yapıyor
Strategy for Squeeze Momentum Indicator [LazyBear] (qp9BoNyS): sıkışma bitişinin ilk mumunda (renk aqua) momentum >0 ve yükseliyorsa (lime) long, <0 ve düşüyorsa (red) short; long momentum yeşile (>0, düşüyor) dönünce, short bordoya (<0, yükseliyor) dönünce kapanır. BB(14, 2), KC(16, 1.5). G40dtEbK'dan farklı parametre ve giriş/çıkış kuralları.

## Koddan kanıt (satır: kod)
```
67: strategy.entry("SQ_Long", strategy.long, when = longCondition)
68: strategy.close("SQ_Long",when = exitLongCondition )
70: strategy.entry("SQ_Long_Ext", strategy.long, when = extremeLong)
71: strategy.close("SQ_Long_Ext",when = exitExtLong)
74: strategy.entry("SQ_Short", strategy.short, when = shortCondition)
75: strategy.close("SQ_Short",when = exitShortCondition)
77: strategy.entry("SQ_Short_Ext", strategy.short, when = extremeShort)
78: strategy.close("SQ_Short_Ext",when = exitExtShort)
103: strategy.close_all()
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/sqz_lb.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
