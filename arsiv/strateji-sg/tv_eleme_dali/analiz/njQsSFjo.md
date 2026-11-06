# Clean Trend System - HTF Bias Filtered (`njQsSFjo`)

- Yazar: Pridarasx · Link: https://tr.tradingview.com/script/njQsSFjo-Clean-Trend-System-HTF-Bias-Filtered/
- Kaynak: 125 satır Pine
- Zaman dilimi / pazar: grafiğe göre (switch ile HTF) · hepsi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("Clean Trend System - HTF Bias Filtered", overlay=true)
```

## Ne yapıyor
EMA9/21/50 trend + geri çekilme (EMA21/VWAP) ya da 20 mumluk kırılım + RSI(5) girişleri; üst zaman dilimi (HTF) yönünün tersine işlem yok. HTF değerleri `request.security(..., [ema, ema, ema, close], lookahead=barmerge.lookahead_on)` ile ve OFSETSİZ alınıyor: devam eden HTF mumunun kapanışı/EMA'sı geçmiş çubuklara yazılıyor.

## Koddan kanıt (satır: kod)
```
33: [htfEmaTrend, htfEmaFast, htfEmaSlow, htfClose] = request.security(syminfo.tickerid, htf, [ta.ema(close, emaTrend), ta.ema(close, emaFast), ta.ema(clo
35: htfBullish = htfClose > htfEmaTrend and htfEmaFast > htfEmaSlow and htfEmaSlow > htfEmaTrend
36: htfBearish = htfClose < htfEmaTrend and htfEmaFast < htfEmaSlow and htfEmaSlow < htfEmaTrend
92: bool longSignal  = longTrigger and trendState != "LONG_FIRED" and strategy.position_size <= 0 and not htfBearish
97: strategy.entry("Long", strategy.long)
101: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
GERÇEK LOOKAHEAD: satır 33'te `lookahead=barmerge.lookahead_on` ve ifadelerde `[1]` ofseti YOK (`close`, `ta.ema(close, …)`). Geçmiş testte her ara mum, o HTF mumun (henüz oluşmamış) kapanışını görür → geleceği gören filtre.

## Karar ve gerekçe
KESİN ELEME: gerçek lookahead (B2): HTF `close`/EMA ofsetsiz + lookahead_on. (Karşılaştırma: U0wTnRuE aynı lookahead_on'u `d[1]` ile kullandığı için GEÇERLİDİR.)
