# TRADLEWARE-Gaussian Channel + StochRSI BTC (`d1JxXpid`)

- Yazar: cs_lev · Link: https://tr.tradingview.com/script/d1JxXpid-TRADLEWARE-Gaussian-Channel-StochRSI-BTC/
- Kaynak: 184 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
11: strategy(title="TRADLEWARE-Gaussian Channel + StochRSI BTC", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100,           // 100% of equity per trade (all-in, single position) commission_type=strategy.commission.percent, commission_value=0.1, slippage=3, pyramiding=0, calc_on_every_tick=false, process_orders_on_close=false)   // fill at next bar's open — matches t
```

## Ne yapıyor
TRADLEWARE Gaussian Channel + StochRSI BTC (d1JxXpid): per=144, çarpan 1.414, StochRSI K>80 ya da <15, rejim ve yeşil mum zorunlu değil; alt bant stop.

## Koddan kanıt (satır: kod)
```
150: longCondition = channelGreen and close > breakoutThreshold and (k > rsiUpperThreshold or k < rsiLowerThreshold) and bullishCandle and timeCondition
153: closeCondition = (close < hband or filt < filt[1]) and timeCondition
162: strategy.exit("StopLoss", from_entry="Long", stop=lband)
```

## Repaint / lookahead kontrolü
Gauss filtresi geçmiş; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Gaussian Channel; erJi1tWf tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/gauss_btc.py` olarak çevrilip test edildi. Giriş mantığı erJi1tWf'den farklı.
