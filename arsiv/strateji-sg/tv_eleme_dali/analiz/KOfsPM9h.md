# SUPPORT RESISTANCE STRATEGY [5MIN TF] (`KOfsPM9h`)

- Yazar: The_Algo_Engineer · Link: https://www.tradingview.com/script/KOfsPM9h-SUPPORT-RESISTANCE-STRATEGY-5MIN-TF/
- Kaynak: 99 satır Pine
- Zaman dilimi / pazar: 5 dk · NSE hisse/vadeli
- **Karar: ELE**

## strategy() bildirimi
```
11: strategy("SUPPORT RESISTANCE STRATEGY [5MIN TF]",overlay=true ,commission_type = strategy.cash, commission_value = 30 , slippage = 2, default_qty_value = 40, currency = currency.NONE, pyramiding = 0)
```

## Ne yapıyor
Hint seansı (09:15–14:45) 5 dk grafikte: pivot direnç/destek kırılımı + hacim osilatörü > eşik + EMA150 filtresi; ATR×3.2 izleyen stop; gün sonu 14:55'te hepsini kapatır; gün içi azami zarar 200 birim.

## Koddan kanıt (satır: kod)
```
27: t = time(timeframe.period, '0915-1445:1234567')
57: Resistance_pi = fixnan(ta.pivothigh(L_Bars, R_Bars)[1])
58: Support_pi = fixnan(ta.pivotlow(L_Bars, R_Bars)[1])
73: strategy.entry(id= "Long" ,direction = strategy.long, comment = "BUY")
78: strategy.exit("long tsl", "Long" , stop = long_trail ,comment='SELL')
84: strategy.entry(id = "Short" ,direction = strategy.short,  comment = "SELL")
87: strategy.exit("short tsl", "Short" ,  stop = short_trail ,comment='BUY')
92: strategy.close_all(when = hour == 14 and minute == 55)
97: strategy.risk.max_intraday_loss(type = strategy.cash, value = risk)
```

## Repaint / lookahead kontrolü
`fixnan(ta.pivothigh(L,R)[1])` — pivot R=15 mum gecikmeli onaylı, `[1]` ile bir mum daha geç; repaint yok. Giriş `barstate.isconfirmed`.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — NSE 5 dk verisi yok; Yahoo 5 dk yalnız 60 gün. Seans kuralı (09:15–14:45) ve komisyon (30 birim sabit) Hint piyasasına özgü.
