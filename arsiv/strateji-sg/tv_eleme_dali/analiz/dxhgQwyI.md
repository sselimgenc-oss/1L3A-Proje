# Golden Vector Trend Orchestrator (GVTO)) (`dxhgQwyI`)

- Yazar: Gustav_Rex · Link: https://tr.tradingview.com/script/dxhgQwyI/
- Kaynak: 154 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Golden Vector Trend Orchestrator (GVTO))", shorttitle="GVTO_Full", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=2, currency=currency.USD)
```

## Ne yapıyor
Golden Vector Trend Orchestrator (dxhgQwyI): Supertrend(14,3.5) yönü + EMA200 + ADX>=25 + DI yönü; koşul oluşunca giriş, supertrend ters dönünce çıkış.

## Koddan kanıt (satır: kod)
```
70: strategy.entry("Long Run", strategy.long, comment="GOLD BUY")
73: strategy.entry("Short Run", strategy.short, comment="GOLD SELL")
77: strategy.close("Long Run", comment="Exit Long")
80: strategy.close("Short Run", comment="Exit Short")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/gvto.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
