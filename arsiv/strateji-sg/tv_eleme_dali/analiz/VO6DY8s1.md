# MACD ReLoaded (`VO6DY8s1`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/VO6DY8s1-MACD-ReLoaded-STRATEGY/
- Kaynak: 330 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
9: strategy('MACD ReLoaded', 'MACDReSt', overlay=true)
```

## Ne yapıyor
MACD ReLoaded (VO6DY8s1): VAR hareketli ortalamalı MACD (12,26) − VAR(9) tetik; histogram sıfırı keserse yön değiştir.

## Koddan kanıt (satır: kod)
```
318: strategy.entry('MacdLong', strategy.long, comment='MacdLong')
321: strategy.entry('MacdShort', strategy.short, comment='MacdShort')
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/macd_reloaded.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. MA türü varsayılan VAR.
