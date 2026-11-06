# SuperTrend Regime Confluence (`mpjNqADq`)

- Yazar: DefinedEdge · Link: https://tr.tradingview.com/script/mpjNqADq-SuperTrend-Regime-Confluence/
- Kaynak: 372 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("SuperTrend Regime Confluence", "ST Regime Conf", overlay            = true, initial_capital    = 10000, default_qty_type   = strategy.percent_of_equity, default_qty_value  = 5, commission_type    = strategy.commission.percent, commission_value   = 0.06, slippage           = 2, pyramiding         = 0, calc_on_every_tick = false, max_labels_count   = 500)
```

## Ne yapıyor
SuperTrend Regime Confluence (mpjNqADq): rejime göre (volatil/yatay/trend) uyarlanan çarpanlı SuperTrend(10, 3, hl2); yön dönüşünde 5 bileşenli skor (hacim, bant uzaklığı, EMA50 uyumu, rejim, önceki mesafe) ≥65 + EMA50 trend süzgeci + yatay rejim değil + hacim>SMA20 ise giriş (5 mum bekleme); stop 6 ATR, hedef 2.5R.

## Koddan kanıt (satır: kod)
```
265: strategy.close("Short")
269: strategy.entry("Long", strategy.long, qty=q)
271: strategy.exit("Long Exit", "Long", stop=slPrice, limit=tpPrice,
275: strategy.exit("Long SL", "Long", stop=slPrice,
287: strategy.close("Long")
291: strategy.entry("Short", strategy.short, qty=q)
293: strategy.exit("Short Exit", "Short", stop=slPrice, limit=tpPrice,
297: strategy.exit("Short SL", "Short", stop=slPrice,
307: strategy.close("Long", comment="ST Flip")
309: strategy.close("Short", comment="ST Flip")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/st_regime_conf.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
