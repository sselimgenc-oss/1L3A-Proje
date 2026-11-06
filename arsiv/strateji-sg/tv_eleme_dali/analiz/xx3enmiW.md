# Ichimoku Confluence Strategy (`xx3enmiW`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/xx3enmiW-Cloud-Pro-Ichimoku-Confluence/
- Kaynak: 254 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Ichimoku Confluence Strategy", shorttitle="Ichimoku Confluence", overlay=true, pyramiding=0, calc_on_every_tick=false, default_qty_type=strategy.percent_of_equity, default_qty_value=10, initial_capital=10000, commission_type=strategy.commission.percent, commission_value=0.1, slippage=2)
```

## Ne yapıyor
Ichimoku Confluence (xx3enmiW): Tenkan/Kijun yukarı kesişimi güçlü ya da nötr (bulutun üstünde/içinde), günlük HTF Tenkan>Kijun onayı → long; stop 1.5 ATR, hedef 3 ATR; aşağı kesişim (her kademe) çıkış. Yalnız long (varsayılan).

## Koddan kanıt (satır: kod)
```
111: htfBullish = htfTenkan > htfKijun
121: strongBull = bullCross and crossLevel > cloudTop
122: neutralBull = bullCross and crossLevel <= cloudTop and crossLevel >= cloudBot
123: weakBull = bullCross and crossLevel < cloudBot
134: longEntrySig  = tierMatch(entryLong, strongBull, neutralBull, weakBull)
137: shortExitSig  = tierMatch(exitShort, strongBull, neutralBull, weakBull)
139: mtfOkLong  = not useMTF or htfBullish
140: mtfOkShort = not useMTF or not htfBullish
170: strategy.entry("Long", strategy.long, qty=qtyFinal)
173: strategy.entry("Short", strategy.short, qty=qtyFinal)
177: strategy.exit("L Exit", "Long", stop=close - atrVal * atrMultSL, limit=close + atrVal * atrMultTP)
181: strategy.exit("L Exit", "Long", stop=slLevel, limit=tpLevel)
183: strategy.close("Long", comment="Signal Exit")
187: strategy.exit("S Exit", "Short", stop=close + atrVal * atrMultSL, limit=close - atrVal * atrMultTP)
```

## Repaint / lookahead kontrolü
HTF `lookahead_off`; bulut geçmişe kaydırılmış.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Ichimoku; boHD0HzE tutuldu)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/ichi_tier.py` olarak çevrilip test edildi. Kademeli (güçlü/nötr/zayıf) kesişim + HTF onayı → farklı mantık.
