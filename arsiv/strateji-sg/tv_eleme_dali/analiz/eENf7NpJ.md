# Twin Optimized Trend Tracker (`eENf7NpJ`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/eENf7NpJ/
- Kaynak: 138 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
9: strategy('Twin Optimized Trend Tracker', 'TOTT', overlay=true)
```

## Ne yapıyor
Twin OTT (eENf7NpJ): VAR hareketli ortalama(40), %1 OTT; MAvg, OTTup[2]'yi yukarı keserse long; OTTdn[2]'yi aşağı keserse short.

## Koddan kanıt (satır: kod)
```
134: strategy.entry('Long', strategy.long, when=Timerange())
136: strategy.entry('Short', strategy.short, when=Timerange())
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/tott.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
