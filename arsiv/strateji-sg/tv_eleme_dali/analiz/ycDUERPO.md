# Optimized Trend Tracker - Strategy Version (`ycDUERPO`)

- Yazar: melihtuna · Link: https://tr.tradingview.com/script/ycDUERPO-Optimized-Trend-Tracker-Strategy-Version/
- Kaynak: 85 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Optimized Trend Tracker - Strategy Version", shorttitle="OTT-Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100, initial_capital=10000, currency=currency.USD, commission_value=0.1, commission_type=strategy.commission.percent)
```

## Ne yapıyor
OTT Strategy Version (ycDUERPO): VAR(OTT periyodu=1) çizgisi OTT[2]'yi keserse yön değiştir (destek çizgisi kesişimi).

## Koddan kanıt (satır: kod)
```
68: strategy.entry("BUY", true, 1, when = buySignalk)
69: strategy.entry("SELL", false, 1, when = sellSignallk)
71: strategy.entry("BUY", true, 1, when = buySignalc)
72: strategy.entry("SELL", false, 1, when = sellSignallc)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/ott.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
