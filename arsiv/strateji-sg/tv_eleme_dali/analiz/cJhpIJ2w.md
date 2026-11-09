# Stochastic Optimized Trend Tracker (`cJhpIJ2w`)

- Yazar: lucidreamer15 · Link: https://tr.tradingview.com/script/cJhpIJ2w-Stochastic-Optimized-Trend-Tracker-Strategy/
- Kaynak: 86 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
9: strategy(title="Stochastic Optimized Trend Tracker", shorttitle="SOTT", format=format.price, precision=2)
```

## Ne yapıyor
Stochastic Optimized Trend Tracker (cJhpIJ2w): VAR(stokastik %K(250), 50)+1000 serisine OTT(3, %0.618); seri OTT[2]'yi keserse yön değiştir.

## Koddan kanıt (satır: kod)
```
79: strategy.entry("Long", strategy.long,when=Timerange())
81: strategy.entry("Short", strategy.short,when=Timerange())
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/sott.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (250 barlık %K).
