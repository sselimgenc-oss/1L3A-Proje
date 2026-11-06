# Grid Like Strategy (`oxvR5vMy`)

- Yazar: alexgrover · Link: https://tr.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy/
- Kaynak: 33 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
6: strategy("Grid Like Strategy",overlay=true,process_orders_on_close=true)
```

## Ne yapıyor
Sabit puan grid: fiyat 2 puan hareket edince taban çizgisi kayar; baseline yükselince long, düşünce short, stop/hedef ±1 grid; zarar sonrası pozisyon büyüklüğü `mf=2` katsayısıyla katlanır (martingale).

## Koddan kanıt (satır: kod)
```
9: mf    = input(2.,"Martingale Multiplier")
22: size := win ? size[1]*mf : loss ? os : nz(size[1],os)
24: size := loss ? size[1]*mf : win ? os : nz(size[1],os)
27: strategy.entry("Buy",strategy.long,qty=size)
30: strategy.entry("Sell",strategy.short,qty=size)
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: martingale/grid (B2). `size := loss ? size[1]*mf : ...` zarardan sonra lot ikiye katlanıyor.
