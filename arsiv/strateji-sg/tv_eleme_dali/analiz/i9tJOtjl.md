# LUBE (`i9tJOtjl`)

- Yazar: Jomy · Link: https://tr.tradingview.com/script/i9tJOtjl-LUBE/
- Kaynak: 72 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
3: strategy("LUBE",overlay=false )
```

## Ne yapıyor
LUBE (i9tJOtjl): 'sürtünme' = son 500 mumdan kaçının aralığı bugünkü kapanışı içeriyor (ağırlıklı); sürtünme düşükken (alt eşik, 5 mum gecikmeli) FIR eğimine göre long/short; sürtünme orta eşiği aşınca çık. 20 mum ısınma.

## Koddan kanıt (satır: kod)
```
4: friction=0.0
5: barsback=input(500,"bars back to measure friction",step=100)
6: flevel=input(50,"0-100 friction level to stop trade",step=2)
12: friction := if high[i] >= close and low[i] <= close
13: friction+(1+barsback)/(i+barsback)
15: friction
17: range=input(100,"bars back to measure lowest friction",step=10)
18: lowf = lowest(friction,range)
19: highf = highest(friction,range)
22: plot(friction)
40: long=friction<lowf2[5] and trend == 1
41: short=friction<lowf2[5] and trend == -1
42: end=friction > midf[5]
44: keeplong=0
```

## Repaint / lookahead kontrolü
Sürtünme hesabı geçmiş 500 muma bakar; eşikler `[5]` gecikmeli. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/lube.py` olarak çevrilip test edildi.
