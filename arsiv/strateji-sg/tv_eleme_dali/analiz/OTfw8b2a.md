# Trading Report Generator from CSV (`OTfw8b2a`)

- Yazar: adolgov · Link: https://tr.tradingview.com/script/OTfw8b2a-Trading-Report-Generator-from-CSV/
- Kaynak: 91 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("Trading Report Generator from CSV", margin_long = 0, margin_short = 0, overlay = true)
```

## Ne yapıyor
CSV metninden önceden kayıtlı işlemleri `strategy.order` ile yeniden oynatan rapor aracı.

## Koddan kanıt (satır: kod)
```
11: bool isBuy
20: str.format("{0} {1} {2} shares at {3}", this.isBuy ? "buy" : "sell", this.tickerId, this.qty, this.price)
87: strategy.order(id = (first.isBuy ? "buy " : "sell ") + nextId(), direction = first.isBuy ? strategy.long : strategy.short, qty = first.qty, limit = fi
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: alım-satım stratejisi değil, işlem raporu oynatıcı.
