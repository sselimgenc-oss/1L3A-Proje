# SuperTrend STRATEGY (`P5Gu6F8k`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/P5Gu6F8k/
- Kaynak: 56 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("SuperTrend STRATEGY", overlay=true)
```

## Ne yapıyor
KivancOzbilgic SuperTrend STRATEGY (P5Gu6F8k): ATR(10)×3, kaynak hl2, giriş = trend dönüşü, hep piyasada (long/short).

## Koddan kanıt (satır: kod)
```
49: strategy.entry("BUY", strategy.long, when = window())
52: strategy.entry("SELL", strategy.short, when = window())
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/st_kivanc.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar zaman dilimi belirtmemiş; günlük, tüm pazarlar (trend takip her yerde anlamlı).
