# PMax on Rsi w T3 Strategy (`ZLcmWQtj`)

- Yazar: lucidreamer15 · Link: https://tr.tradingview.com/script/ZLcmWQtj-PMax-on-Rsi-w-T3-Strategy/
- Kaynak: 106 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
7: strategy("PMax on Rsi w T3 Strategy","PmR3St.", overlay=false, precision=2)
```

## Ne yapıyor
PMax on RSI w/ T3 (ZLcmWQtj): RSI'nin (Wilder benzeri) Tillson T3'ü üzerine PMax (ATR yerine RSI-aralığı 'ATR'si ×3); T3, PMax'i yukarı keserse long, aşağı keserse short; hep piyasada.

## Koddan kanıt (satır: kod)
```
61: Pmax_Func(rsi,length)=>
72: PMax=Pmax_Func(rsi,length)
81: buySignalk = crossover(MAvg, PMax)
82: plotshape(buySignalk and showsignalsk ? PMax*0.995 : na, title="Buy", text="Buy", location=location.absolute, style=shape.labelup, size=size.tiny, col
83: sellSignallk = crossunder(MAvg, PMax)
84: plotshape(sellSignallk and showsignalsk ? PMax*1.005 : na, title="Sell", text="Sell", location=location.absolute, style=shape.labeldown, size=size.tin
102: if buySignalk
103: strategy.entry("Long", strategy.long,when=Timerange())
104: if sellSignallk
105: strategy.entry("Short", strategy.short,when=Timerange())
```

## Repaint / lookahead kontrolü
Yalnız geçmiş; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (PMax/OTT ailesi; temsilciler tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/pmax_rsi.py` olarak çevrilip test edildi. RSI üzerinde T3 + PMax → fiyat PMax'inden farklı gösterge.
