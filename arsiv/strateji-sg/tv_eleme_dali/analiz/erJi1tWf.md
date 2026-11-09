# Gaussian Channel Strategy (`erJi1tWf`)

- Yazar: RezzoRedPriest · Link: https://tr.tradingview.com/script/erJi1tWf-Gaussian-Channel-Strategy/
- Kaynak: 155 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("Gaussian Channel Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100)
```

## Ne yapıyor
Gaussian Channel Strategy (erJi1tWf): 4 kutuplu Gaussian filtre (periyot 144) ve filtrelenmiş TR bandı; fiyat orta çizgiyi yukarı keserse long, aşağı keserse short (3 bar geç giriş penceresi).

## Koddan kanıt (satır: kod)
```
127: strategy.close("Short")
129: strategy.entry("Long", strategy.long)
133: strategy.close("Long")
135: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/gaussian.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. Bant çizgileri yalnız görsel (sinyal orta çizgi).
