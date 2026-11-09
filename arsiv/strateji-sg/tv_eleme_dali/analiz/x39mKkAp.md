# Yuri Garcia Narrow State Strategy (`x39mKkAp`)

- Yazar: YGD_CONSULTING_LLC · Link: https://tr.tradingview.com/script/x39mKkAp-Yuri-Garcia-Narrow-State-Strategy-YGILS/
- Kaynak: 80 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Yuri Garcia Narrow State Strategy", overlay=true, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=2)
```

## Ne yapıyor
Yuri Garcia Narrow State (x39mKkAp): EMA20 ile SMA200 arası ≤%1.5 (dar durum) iken trend yönünde 'fil' mum (gövde>1.5 ATR) ya da dönüş mumu (kırmızı sonrası yeşil kapanış>önceki tepe) → giriş; stop 2 ATR, hedef 2R.

## Koddan kanıt (satır: kod)
```
27: isNarrowState = maDistancePct <= maxDistancePct
33: isElephant = candleBody > atr * multElephant
35: bullishElephant = isElephant and close > open and bullishTrend
36: bearishElephant = isElephant and close < open and bearishTrend
41: condLong = (bullishElephant or rbiBuy) and isNarrowState
42: condShort = (bearishElephant or gbiSell) and isNarrowState
44: newLong = condLong and canBuy and strategy.position_size <= 0
45: newShort = condShort and canSell and strategy.position_size >= 0
54: strategy.entry("LONG", strategy.long)
57: strategy.entry("SHORT", strategy.short)
59: strategy.exit("TP SL LONG", from_entry="LONG", stop=longSL, limit=longTP)
60: strategy.exit("TP SL SHORT", from_entry="SHORT", stop=shortSL, limit=shortTP)
67: bgcolor(isNarrowState ? color.new(color.green, 92) : na)
```

## Repaint / lookahead kontrolü
Yalnız kapanmış mum koşulları. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/narrow_state.py` olarak çevrilip test edildi.
