# Bollinger + RSI, Double Strategy (by ChartArt) (`zopumZ8a`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/zopumZ8a-Bollinger-RSI-Double-Strategy-by-ChartArt/
- Kaynak: 78 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Bollinger + RSI, Double Strategy (by ChartArt)", shorttitle="CA_-_RSI_Bol_Strat", overlay=true)
```

## Ne yapıyor
Bollinger + RSI Double (zopumZ8a, ChartArt): RSI(16) 45'i yukarı + kapanış BB(20,2) altını yukarı keserse long; RSI 55'i aşağı + kapanış üst bandı aşağı keserse short (stop emirleri bir mum geçerli → ertesi açılış); çıkış yalnız ters sinyal.

## Koddan kanıt (satır: kod)
```
33: RSIlength = input( 16 ,title="RSI Period Length")
34: RSIvalue = input( 45 ,title="RSI Value Range")
35: RSIoverSold = 0 + RSIvalue
36: RSIoverBought = 100 - RSIvalue
38: vrsi = rsi(price, RSIlength)
69: strategy.entry("RSI_BB_L", strategy.long, stop=BBlower, oca_type=strategy.oca.cancel, comment="RSI_BB_L")
71: strategy.cancel(id="RSI_BB_L")
74: strategy.entry("RSI_BB_S", strategy.short, stop=BBupper, oca_type=strategy.oca.cancel, comment="RSI_BB_S")
76: strategy.cancel(id="RSI_BB_S")
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Bollinger+RSI; uCV8I4xA tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/bb_rsi_b.py` olarak çevrilip test edildi. RSI16/45 ve BB20 → uCV8I4xA'dan (RSI6/BB200) farklı varsayılanlar.
