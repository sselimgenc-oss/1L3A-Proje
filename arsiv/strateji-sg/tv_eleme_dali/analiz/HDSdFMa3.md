# Bollinger + RSI, Double Strategy Long-Only (by ChartArt) v1.2 (`HDSdFMa3`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/HDSdFMa3-Bollinger-RSI-Double-Strategy-Long-Only-by-ChartArt-v1-2/
- Kaynak: 82 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Bollinger + RSI, Double Strategy Long-Only (by ChartArt) v1.2", shorttitle="CA_-_RSI_Bol_Strat_1.2", overlay=true)
```

## Ne yapıyor
Bollinger + RSI Double, Long-Only v1.2 (HDSdFMa3, ChartArt): RSI(6) 50'yi yukarı keser ve kapanış BB(200,2) alt bandını yukarı keserse long (stop emri alt bantta → ertesi açılış); RSI 50'yi aşağı + kapanış üst bandı aşağı keserse kapat.

## Koddan kanıt (satır: kod)
```
68: long = (crossover(vrsi, RSIoverSold) and crossover(source, BBlower))
69: close_long = (crossunder(vrsi, RSIoverBought) and crossunder(source, BBupper))
74: strategy.entry("RSI_BB", strategy.long, stop=BBlower, oca_type=strategy.oca.cancel, comment="RSI_BB")
76: strategy.cancel(id="RSI_BB")
78: if close_long
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum; stop emri bir mum geçerli. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Bollinger+RSI; uCV8I4xA tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/bb_rsi_lo.py` olarak çevrilip test edildi. Parametreler farklı (RSI6, BB200, yalnız long, çıkış kuralı var) → kopya değil.
