# Confluence Rank Trend Strategy [Jayadev Rana] (`LcA4mcE6`)

- Yazar: JayadevRana · Link: https://tr.tradingview.com/script/LcA4mcE6-Confluence-Rank-Trend-Strategy-Jayadev-Rana/
- Kaynak: 164 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
4: strategy("Confluence Rank Trend Strategy [Jayadev Rana]", shorttitle = "CRTS", overlay = true, initial_capital = 10000, default_qty_type = strategy.fixed, default_qty_value = 1, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 2, pyramiding = 0, margin_long = 100, margin_short = 100)
```

## Ne yapıyor
Confluence Rank Trend (LcA4mcE6): trend (EMA55/233), RSI momentum, verimlilik oranı, oynaklık yüzdeliği ve göreli hacimden 0–100 skor; skor ≥85'e yeni çıkınca giriş (long/short), 3 ATR izleyen stop, skor <35 olunca çık.

## Koddan kanıt (satır: kod)
```
74: float scoreL = nz(trendL + momL + effL + volReg + partL)
75: float scoreS = nz(trendS + momS + effS + volReg + partS)
82: bool longSig  = warm and barstate.isconfirmed and allowLong and flat and scoreL >= entryThr and scoreL[1] < entryThr
83: bool shortSig = warm and barstate.isconfirmed and allowShort and flat and scoreS >= entryThr and scoreS[1] < entryThr and not longSig
102: if longSig
103: float q = f_qty(scoreL, stopDist)
106: strategy.entry("Long", strategy.long, qty = q)
107: strategy.exit("Long Stop", "Long", stop = trail)
108: alert("Confluence Rank: long entry, score " + str.tostring(scoreL, "#") + " on " + syminfo.ticker, alert.freq_once_per_bar_close)
109: else if shortSig
110: float q = f_qty(scoreS, stopDist)
113: strategy.entry("Short", strategy.short, qty = q)
114: strategy.exit("Short Stop", "Short", stop = trail)
115: alert("Confluence Rank: short entry, score " + str.tostring(scoreS, "#") + " on " + syminfo.ticker, alert.freq_once_per_bar_close)
```

## Repaint / lookahead kontrolü
`barstate.isconfirmed`; geçmiş mum. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/conf_rank.py` olarak çevrilip test edildi.
