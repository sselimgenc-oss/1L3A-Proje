# DMI/ADX Trend Dashboard v3 (Pullback + Decay) (`EcEYc8ap`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/EcEYc8ap-Gravity-Trend-ADX-Strength-Meter-Quality-Scored-DMI-System/
- Kaynak: 301 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
4: strategy("DMI/ADX Trend Dashboard v3 (Pullback + Decay)", "DMI-ADX-TQD-v3", overlay=true, default_qty_type=strategy.fixed, default_qty_value=1, margin_long=100, margin_short=100)
```

## Ne yapıyor
DMI/ADX Trend Dashboard v3 (EcEYc8ap): +DI>−DI, ADX≥20, DI farkı>10, fiyat>EMA50 rejiminde EMA9'a geri çekilip yeniden üstüne çıkınca (pullback) long (short simetrik); başlangıç stop 2 ATR, chandelier izleyen stop (22 mum zirve − 3 ATR), DI ters kesişiminde çık. (ADX-azalma çıkışı ve 5 mum bekleme modellenmedi.)

## Koddan kanıt (satır: kod)
```
132: pullbackLongTrigger  = longPullback and ta.crossover(close, emaFast) and longRegime
138: longCondition  = (usePullbackEntry ? pullbackLongTrigger  : crossoverLongTrigger)  and cooldownOK and strategy.position_size <= 0
148: strategy.entry("Long", strategy.long, qty=qtyToTrade)
152: strategy.entry("Short", strategy.short, qty=qtyToTrade)
170: chandLong = ta.highest(high, chandelierLen) - atrVal * chandelierMult
171: longStop := useChandelier ? math.max(longStop[1], chandLong) : longStop[1]
186: strategy.exit("Long Exit", from_entry="Long", stop=longStop)
189: strategy.exit("Short Exit", from_entry="Short", stop=shortStop)
208: strategy.close("Long", comment="DI Reversal")
211: strategy.close("Short", comment="DI Reversal")
214: strategy.close_all(comment="ADX Decay")
230: if strategy.closedtrades > lastLoggedTrades
231: for i = lastLoggedTrades to strategy.closedtrades - 1
233: won = strategy.closedtrades.profit(i) > 0
```

## Repaint / lookahead kontrolü
Yalnız geçmiş. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/dmi_adx3.py` olarak çevrilip test edildi.
