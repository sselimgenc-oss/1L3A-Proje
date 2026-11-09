# Monthly Returns in PineScript Strategies (`kzp8e4X3`)

- Yazar: QuantNomad · Link: https://tr.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies/
- Kaynak: 115 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Monthly Returns in PineScript Strategies", overlay = true, default_qty_type = strategy.percent_of_equity, default_qty_value = 25, calc_on_every_tick = true, commission_type = strategy.commission.percent, commission_value = 0.1)
```

## Ne yapıyor
Pivot Reversal (kzp8e4X3, 'Monthly Returns' örnek betiği): pivot tepesi (2 sol/1 sağ mum) onaylanınca o tepenin 1 tick üstüne stop-al emri (fiyat geçene kadar geçerli); pivot dibi için stop-sat emri; hep piyasada. Emir 1 mum geçerli olarak modellendi.

## Koddan kanıt (satır: kod)
```
10: swh = pivothigh(leftBars, rightBars)
11: swl = pivotlow(leftBars, rightBars)
26: strategy.entry("PivRevLE", strategy.long, comment="PivRevLE", stop=hprice + syminfo.mintick)
29: strategy.entry("PivRevSE", strategy.short, comment="PivRevSE", stop=lprice - syminfo.mintick)
```

## Repaint / lookahead kontrolü
Pivot: satır 10: `swh = pivothigh(leftBars, rightBars)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/pivot_rev.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Örnek betik; zaman dilimi yok; günlük, tüm pazarlar.
