# Stochastic + RSI, Double Strategy (by ChartArt) (`IGJPEi7L`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/IGJPEi7L-Stochastic-RSI-Double-Strategy-by-ChartArt/
- Kaynak: 56 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Stochastic + RSI, Double Strategy (by ChartArt)", shorttitle="CA_-_RSI_Stoch_Strat", overlay=true)
```

## Ne yapıyor
Stochastic + RSI Double Strategy (IGJPEi7L, ChartArt): %K/%D kesişimi aşırı bölgede + RSI eşik kesişimi; long ve short.

## Koddan kanıt (satır: kod)
```
48: strategy.entry("LONG", strategy.long, comment="StochLE + RsiLE")
53: strategy.entry("SHORT", strategy.short, comment="StochSE + RsiSE")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/stoch_rsi.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (klasik 2015 betiği).
