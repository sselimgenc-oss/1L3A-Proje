"""EWO + RSI Signals (B7MQqWes): RSI 40'ı yukarı keser + MFI>30 + EWO yükselir + hacim + (10 bar zirve kırılımı veya yakın zamanda RSI<30) → long; RSI 60'ı aşağı keser + MFI<70 + EWO düşer → short. Ters sinyalde yön değiştirir."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "EWO + RSI sinyalleri"; PINE_ID = "B7MQqWes"
PARAM = dict(ewo_h=5, ewo_y=34, rsi=14, mfi=14, vol=20, geri=10, asiri_satim=30)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _dongu(rsi, raw_buy_base, raw_sell, brk, asiri):
    n = len(rsi); buy = np.zeros(n); zone = False; last = 0
    for i in range(1, n):
        if not np.isnan(rsi[i]) and rsi[i] < asiri: zone = True
        rb = raw_buy_base[i] and (brk[i] or zone); rs = raw_sell[i]
        if rb: zone = False
        if rb and last != 1: buy[i] = 1.0; last = 1
        if rs and last != -1: buy[i] = -1.0; last = -1
    return buy
def sinyal(df, ewo_h, ewo_y, rsi, mfi, vol, geri, asiri_satim):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    hl2 = (h+l)/2; ewo = gost.sma(hl2, int(ewo_h)) - gost.sma(hl2, int(ewo_y)); r = gost.rsi(c, int(rsi)); m = gost.mfi(h, l, c, v, int(mfi))
    vok = v > gost.sma(v, int(vol))*0.8; brk = c > gost.sh(gost.highest(h, int(geri)), 1)
    with np.errstate(invalid="ignore"):
        e1 = ewo > gost.sh(ewo)
        rb = gost.crossover(np.nan_to_num(r), np.full(len(c), 40.0)) & (m > 30) & e1 & vok
        rs = gost.crossunder(np.nan_to_num(r), np.full(len(c), 60.0)) & (m < 70) & (ewo < gost.sh(ewo)) & vok
    s = _dongu(r, rb, rs, np.nan_to_num(brk, nan=0).astype(np.bool_), float(asiri_satim))
    return dict(sig=s)
