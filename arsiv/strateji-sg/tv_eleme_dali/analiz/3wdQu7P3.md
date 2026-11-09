# AlphaTrend Strategy (`3wdQu7P3`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/3wdQu7P3-AlphaTrend-Strategy/
- Kaynak: 45 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("AlphaTrend Strategy", shorttitle='ATSt', overlay=true, format=format.price, precision=2, margin_long=100, margin_short=100)
```

## Ne yapıyor
AlphaTrend Strategy (3wdQu7P3): ATR(SMA 14)×1, MFI(14)>=50'ye göre izleyen çizgi; AT, AT[2]'yi keserse yön değiştir.

## Koddan kanıt (satır: kod)
```
40: strategy.entry("Long", strategy.long)
44: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/alphatrend.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar BTCUSDT günlük test etmiş; günlük, tüm pazarlar.
