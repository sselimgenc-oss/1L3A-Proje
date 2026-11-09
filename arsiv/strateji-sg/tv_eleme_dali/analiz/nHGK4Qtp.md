# PMax Explorer (`nHGK4Qtp`)

- Yazar: KivancOzbilgic · Link: https://tr.tradingview.com/script/nHGK4Qtp/
- Kaynak: 326 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("PMax Explorer", shorttitle="PMEx", overlay=true)
```

## Ne yapıyor
PMax (nHGK4Qtp, KivancOzbilgic): EMA(hl2,10) ± ATR(10)×3 ile PMax çizgisi; EMA, PMax'ı yukarı keserse long, aşağı keserse short.

## Koddan kanıt (satır: kod)
```
143: strategy.entry("Long", strategy.long,when=Timerange())
145: strategy.entry("Short", strategy.short,when=Timerange())
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 184: `[t01, s01] = security(t1, timeframe.period, Pmax(Multiplier, Periods))`; satır 185: `[t02, s02] = security(t2, timeframe.period, Pmax(Multiplier, Periods))`; satır 186: `[t03, s03] = security(t3, timeframe.period, Pmax(Multiplier, Periods))`. lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/pmax.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. MA türü varsayılan EMA.
