# TRADLEWARE-Gaussian Channel ETH (`egTb7TgJ`)

- Yazar: cs_lev · Link: https://tr.tradingview.com/script/egTb7TgJ-TRADLEWARE-Gaussian-Channel-StochRSI-ETH/
- Kaynak: 194 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
11: strategy(title="TRADLEWARE-Gaussian Channel ETH", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1, slippage=3, pyramiding=0, calc_on_every_tick=false, process_orders_on_close=false)
```

## Ne yapıyor
TRADLEWARE Gaussian Channel ETH (egTb7TgJ): per=89, çarpan 1.5, StochRSI K>80 ya da <25, SMA200 rejimi, yeşil mum zorunlu; alt bant stop.

## Koddan kanıt (satır: kod)
```
161: longCondition = channelGreen and close > breakoutThreshold and (k > rsiUpperThreshold or k < rsiLowerThreshold) and bullRegime and bullishCandle and t
164: closeCondition = (close < hband or filt < filt[1]) and timeCondition
173: strategy.exit("StopLoss", from_entry="Long", stop=lband)
```

## Repaint / lookahead kontrolü
Gauss filtresi geçmiş; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Gaussian Channel; erJi1tWf tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/gauss_eth.py` olarak çevrilip test edildi. Giriş mantığı erJi1tWf'den farklı (bant kırılımı + StochRSI + SMA200 rejimi + alt bant stop).
