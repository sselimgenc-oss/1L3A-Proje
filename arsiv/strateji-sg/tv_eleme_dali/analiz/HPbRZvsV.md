# Optimized Trend Tracker (`HPbRZvsV`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/HPbRZvsV/
- Kaynak: 336 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
9: strategy("Optimized Trend Tracker","OTTEx", overlay=true)
```

## Ne yapıyor
Optimized Trend Tracker 'OTTEx' (HPbRZvsV): VAR(2) hareketli ortalaması ve %1.4 OTT bandı; fiyat OTT[2]'yi yukarı keserse long, VAR çizgisi OTT[2]'yi aşağı keserse short (hep piyasada). ycDUERPO ile aynı OTT hesabı, farklı varsayılanlar ve sinyal kaynağı (fiyat kesişimi).

## Koddan kanıt (satır: kod)
```
108: sellSignallk = crossunder(MAvg, OTT[2])
109: plotshape(sellSignallk and showsignalsk ? OTT*1.005 : na, title="Sell", text="Sell", location=location.absolute, style=shape.labeldown, size=size.tiny
110: buySignalc = crossover(src, OTT[2])
111: plotshape(buySignalc and showsignalsc ? OTT*0.995 : na, title="Buy", text="Buy", location=location.absolute, style=shape.labelup, size=size.tiny, colo
152: strategy.entry("Long", strategy.long,when=Timerange())
153: if sellSignallk
154: strategy.entry("Short", strategy.short,when=Timerange())
```

## Repaint / lookahead kontrolü
Yalnız geçmiş; dashboard için çok `request.security` var, sinyal onlara bağlı değil.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (OTT; ycDUERPO tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/ott_ex.py` olarak çevrilip test edildi. Farklı varsayılanlar (VAR(2), %1.4) ve fiyat kesişimi → kopya değil.
