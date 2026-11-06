# Bollinger + RSI, Double Strategy (by ChartArt) v1.1 (`uCV8I4xA`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/uCV8I4xA-Bollinger-RSI-Double-Strategy-by-ChartArt-v1-1/
- Kaynak: 79 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Bollinger + RSI, Double Strategy (by ChartArt) v1.1", shorttitle="CA_-_RSI_Bol_Strat_1.1", overlay=true)
```

## Ne yapıyor
Bollinger + RSI Double Strategy (uCV8I4xA, ChartArt): RSI(6) 50'yi + fiyat alt bandı (BB200) yukarı keserse long; RSI 50'yi + fiyat üst bandı aşağı keserse short.

## Koddan kanıt (satır: kod)
```
70: strategy.entry("RSI_BB_L", strategy.long, stop=BBlower, oca_type=strategy.oca.cancel, comment="RSI_BB_L")
75: strategy.entry("RSI_BB_S", strategy.short, stop=BBupper, oca_type=strategy.oca.cancel, comment="RSI_BB_S")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/bb_rsi.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (klasik 2016 betiği).
