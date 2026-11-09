# [3Commas] Ether Vault Grid — ETH (`OEeqwUwB`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/OEeqwUwB-3Commas-Ether-Vault-Grid-ETH-USDT/
- Kaynak: 246 satır Pine
- Zaman dilimi / pazar: 15dk–1s · tek sembol
- **Karar: ELE**

## strategy() bildirimi
```
28: strategy( title                   = "[3Commas] Ether Vault Grid — ETH", shorttitle              = "Ether Vault Grid", overlay                 = true, pyramiding              = 100, initial_capital         = 6000, default_qty_type        = strategy.cash, default_qty_value       = 178.57, commission_type         = strategy.commission.percent, commission_value        = 0.1,        // Bybit spot taker slippage           
```

## Ne yapıyor
Izgara (grid) botu: sabit fiyat aralığını ? seviyeye böler; fiyat her seviyenin altına inince o seviyede long alır, bir üst seviyeye çıkınca satar (`pyramiding=100`). Giriş sinyali / trend filtresi yok, stop yok: aralığın altına düşen fiyatta tüm seviyeler dolu kalır.

## Koddan kanıt (satır: kod)
```
32: pyramiding              = 100,
```

## Repaint / lookahead kontrolü
request.security yok; repaint/lookahead sorunu yok — eleme nedeni bu değil.

## Karar ve gerekçe
KESİN ELEME: grid (B2 kuralı). Her seviyede küçük kâr, aralık dışı düşüşte sınırsız zarar; kazanma oranı yapay yüksek, getiri aralık varsayımına bağlı.
