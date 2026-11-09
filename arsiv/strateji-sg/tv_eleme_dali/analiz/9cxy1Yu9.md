# Crypto momentum strategy (`9cxy1Yu9`)

- Yazar: echepata · Link: https://tr.tradingview.com/script/9cxy1Yu9-Crypto-momentum-strategy/
- Kaynak: 69 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
12: strategy("Crypto momentum strategy", overlay=false, pyramiding=0, default_qty_value=100, default_qty_type= strategy.percent_of_equity, precision=7, currency=currency.AUD, commission_value=0.1, commission_type=strategy.commission.percent, initial_capital=initialBalance)
```

## Ne yapıyor
Crypto momentum strategy (9cxy1Yu9): sıkışma-momentum eğimi (val−val[2]) yukarı döner + fiyat>EMA50 + EMA eğimi>0 + kripto piyasası (BTC; CRYPTOCAP:TOTAL yerine) EMA50 üstünde ve yükseliyor → long; eğim aşağı dönünce çıkış.

## Koddan kanıt (satır: kod)
```
66: strategy.entry("long", strategy.long, comment="long")
68: strategy.close("long")
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 25: `market = security(marketTicker, timeframe.period, close, true)`. lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/kripto_mom.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Betik kripto için; kripto günlük. Piyasa filtresi için TOTAL verisi yok → BTC vekil.
