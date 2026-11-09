# TASC 2026.08 An Ag Selling Model (`VFzCk3HX`)

- Yazar: PineCodersTASC · Link: https://tr.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/
- Kaynak: 113 satır Pine
- Zaman dilimi / pazar: ? · tarım vadeli
- **Karar: ELE**

## strategy() bildirimi
```
14: strategy( TITLE, SHORTTITLE, true, initial_capital = 15000000, pyramiding = 3, slippage = 1, commission_type = strategy.commission.cash_per_contract, commission_value = 300 )
```

## Ne yapıyor
Tarım ürünü satış programı: mahsul yılı/aya göre fiyat seviyelerinde kademeli SATIŞ (short, pyramiding=3), alım hedgeleme mantığı.

## Koddan kanıt (satır: kod)
```
17: pyramiding = 3,
62: bool newCropYr = isHarvestMonth and not isHarvestMonth[1]
64: int beginSaleMonth = (startCropYear + delayMonths + 1) % 12
65: if beginSaleMonth == 0
66: beginSaleMonth := 12
69: if newCropYr
74: if month == beginSaleMonth and month[1] != beginSaleMonth
82: strategy.entry("First sale", strategy.short)
85: strategy.entry("Sell", strategy.short)
98: newCropYr ? color.rgb(255, 255, 255, 50) : na,
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok (tarım vadelisi, mahsul yılı takvimi) ve kademeli ekleme.
