# MACD ASHI BARS Wıth SL-TP  (`YfPnKE22`)

- Yazar: ridvansozen1 · Link: https://tr.tradingview.com/script/YfPnKE22-Heikin-Ashi-MACD/
- Kaynak: 101 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("MACD ASHI BARS Wıth SL-TP ", overlay=false,default_qty_type = strategy.percent_of_equity, default_qty_value = 100,commission_type=strategy.commission.percent,commission_value=0.1,slippage=1)
```

## Ne yapıyor
MACD ASHI BARS SL-TP (YfPnKE22): Heikin Ashi kapanışı üzerinde DEMA(12)−DEMA(25) MACD'si, sinyal SMA15; delta sıfırı yukarı keserse long, aşağı keserse short (stop emri kapanış seviyesinde, bir mum geçerli); %10 hedef, %3 stop.

## Koddan kanıt (satır: kod)
```
65: if ( crossover(delta,0)  and   year >= yearfrom and year <= yearuntil and month>=monthfrom and month <=monthuntil and dayofmonth>=dayfrom and dayofmon
66: strategy.entry("LONG", strategy.long, stop=close, oca_name="TREND", oca_type=strategy.oca.cancel, comment="LONG")
72: if (  crossunder(delta,0) and  year >= yearfrom and year <= yearuntil and month>=monthfrom and month <=monthuntil and dayofmonth>=dayfrom and dayofmon
74: strategy.entry("SHORT", strategy.short,stop=close, oca_name="TREND", oca_type=strategy.oca.cancel, comment="SHORT")
85: strategy.exit("LONG EXIT","LONG",profit=profit_target, loss=stop_target )
87: strategy.exit("LONG EXIT","SHORT",profit=profit_target, loss=stop_target )
```

## Repaint / lookahead kontrolü
Stop emirleri `strategy.cancel` ile bir mum; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/macd_ashi.py` olarak çevrilip test edildi.
