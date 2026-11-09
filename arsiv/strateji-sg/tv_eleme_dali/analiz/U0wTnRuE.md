# RF-HA Trend Scalper (`U0wTnRuE`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/U0wTnRuE-Apex-Trail-Trend-Agreement-Scalper-with-ATR-Trailing-Stop/
- Kaynak: 228 satır Pine
- Zaman dilimi / pazar: 15m (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("RF-HA Trend Scalper", shorttitle = "RHT", overlay = true, initial_capital = 10000, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, commission_type = strategy.commission.percent, commission_value = 0.03, slippage = 1, pyramiding = 0, calc_on_every_tick = false, process_orders_on_close = false, max_labels_count = 300, max_bars_back = 500)
```

## Ne yapıyor
RF-HA Trend Scalper (U0wTnRuE): Range Filter yönü + yumuşatılmış Heikin-Ashi yönü + (1s HTF HA yönü, `d[1]` = son kapanmış HTF mumu — lookahead YOK) aynı yöndeyse yeni durumda giriş (SMI anti-kovalama filtreli); 2.5 ATR izleyen stop, Range Filter tersine dönünce çık. (5 mumluk bekleme süresi modellenmedi.)

## Koddan kanıt (satır: kod)
```
90: d[1]
127: int hDir = nz(request.security(syminfo.tickerid, htfTf, f_htfDir(), lookahead = barmerge.lookahead_on))
140: bool longSig = ready and dirMode != "Short Only" and state == 1 and state[1] != 1 and (not useSmi or smi < smiMax)
141: bool shortSig = ready and dirMode != "Long Only" and state == -1 and state[1] != -1 and (not useSmi or smi > -smiMax)
149: if longSig and entryQty > 0
151: if shortSig and entryQty > 0
200: plotshape(showSignals and longSig, "Long Signal", shape.triangleup, location.belowbar, C_BULL, size = size.small)
201: plotshape(showSignals and shortSig, "Short Signal", shape.triangledown, location.abovebar, C_BEAR, size = size.small)
```

## Repaint / lookahead kontrolü
HTF yön `f_htfDir()` içinde `d[1]` (son KAPANMIŞ HTF mum) ile `lookahead_on` birlikte: bu standart non-repaint kalıbıdır → önceki tur 'geleceği gören' kararı HATALIYDI.

## Karar ve gerekçe
Önceki tur gerekçesi: «geleceği gören request.security (lookahead_on, ofsetsiz)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/rf_ha.py` olarak çevrilip test edildi.
