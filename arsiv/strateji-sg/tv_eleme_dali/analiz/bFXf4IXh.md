# Built-in Kelly ratio for position sizing (`bFXf4IXh`)

- Yazar: CryptoRox · Link: https://tr.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing/
- Kaynak: 97 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
3: strategy("Built-in Kelly ratio for position sizing", overlay=true, initial_capital=10000, default_qty_type=strategy.cash, default_qty_value=10000, currency="USD", commission_type=strategy.commission.percent, commission_value=0.1)
```

## Ne yapıyor
Built-in Kelly (bFXf4IXh): EMA(20) ± 1×ATR(10) bandı; kapanış üst bandı yukarı keserse barın tepesi+1 tick'te stop-al (aşağı için tersi); TP/SL kapalı. (Kelly boyutlandırma çevrilmedi; standart boyut.)

## Koddan kanıt (satır: kod)
```
6: useKelly = input(true, "Kelly Ratio Position Sizing")
12: if useKelly
36: crossUpper = crossover(src, upper)
37: crossLower = crossunder(src, lower)
39: bprice := crossUpper ? high+syminfo.mintick : nz(bprice[1])
41: sprice := crossLower ? low -syminfo.mintick : nz(sprice[1])
43: crossBcond := crossUpper ? true
46: crossScond := crossLower ? true
51: if useKelly
54: if (crossUpper)
55: strategy.entry("Long", strategy.long, qty, stop=bprice, comment="Long")
58: if (crossLower)
59: strategy.entry("Short", strategy.short, qty, stop=sprice, comment="Short")
63: if (crossUpper)
```

## Repaint / lookahead kontrolü
Stop emirleri `strategy.cancel` ile yönetilir; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «eğitim (Kelly boyutlandırma örneği)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/kelly_bands.py` olarak çevrilip test edildi. Örnek ama gerçek bir bant-kırılım giriş kuralı içeriyor.
