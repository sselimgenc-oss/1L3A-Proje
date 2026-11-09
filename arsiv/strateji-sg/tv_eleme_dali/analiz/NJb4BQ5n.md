# Bilateral Stochastic Oscillator Strategy (`NJb4BQ5n`)

- Yazar: alexgrover · Link: https://www.tradingview.com/script/NJb4BQ5n-Bilateral-Stochastic-Oscillator-Strategy/
- Kaynak: 37 satır Pine
- Zaman dilimi / pazar: 15dk · forex (EURUSD)
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Bilateral Stochastic Oscillator Strategy",commission_type = strategy.commission.cash_per_contract)
```

## Ne yapıyor
TMA(100) önfiltreli 'bull/bear' çiftinin kesişimi: yukarı long, aşağı short; bull/bear sinyal çizgisi altına inince kapat. Martingale çarpanı seçeneği var, varsayılan 1.0 (kapalı).

## Koddan kanıt (satır: kod)
```
9: mult = input(1.,title="Martingale Multiplier")
26: size := change(l) ? nz(size[1],1) * mult : change(w) ? 1 : nz(size[1],1)
30: strategy.order("Buy",true,qty=size*Ds,when=long)
31: strategy.order("Sell",false,qty=size*Ds,when=short)
32: strategy.close("Buy",crossunder(bull,signal))
33: strategy.close("Sell",crossunder(bear,signal))
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
Aday (varsayılanda martingale kapalı); `strategy.order` net-pozisyon mantığı basitleştirildi. Forex yok → saatlik kripto/ABD/emtia.
