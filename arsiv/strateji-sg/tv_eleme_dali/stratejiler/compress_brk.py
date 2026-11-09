"""Compression Breakout System (97gxVA5b): Bollinger genişliği %-sıralaması < 25 (son 5 mumda sıkışma) + 20 günlük tepe kırılımı + hacim > 20 SMA + kapanış > SMA200 → kapanışta long; stop = 2×ATR(22), chandelier izleyen stop 3×ATR (kapanış bazlı çıkış). Yalnız long, process_orders_on_close."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Compression Breakout System"; PINE_ID = "97gxVA5b"
PARAM = dict(bb=20, bb_c=2.0, rank=126, sqz=25.0, yas=5, brk=20, sma=200, atr=22, stop=2.0, iz=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Betikte 'günlük' ifadesi (rank penceresi gün cinsinden) var; günlük, tüm pazarlar."
@njit(cache=True)
def _dur(buy, c, atr, stop, iz):
    n = len(c); xl = np.zeros(n, np.bool_); rd = np.full(n, np.nan); pos = False; es = 0.0; hwm = 0.0
    for i in range(n):
        was = pos
        if pos:
            hwm = max(hwm, c[i])
            lv = max(es, hwm - atr[i]*iz)
            if c[i] < lv: xl[i] = True; pos = False
        if (not was) and buy[i] and not np.isnan(atr[i]):
            pos = True; es = c[i] - atr[i]*stop; hwm = c[i]; rd[i] = atr[i]*stop
    return xl, rd
def sinyal(df, bb, bb_c, rank, sqz, yas, brk, sma, atr, stop, iz):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    b = gost.sma(c, int(bb)); dev = gost.stdev(c, int(bb))*bb_c; w = 2*dev/b*100
    wr = gost.percentrank(w, int(rank)); on = (wr < sqz).astype(float)
    recent = gost.rsum(np.nan_to_num(on), int(yas)) > 0
    lvl = gost.sh(gost.highest(h, int(brk)))
    a = gost.atr(h, l, c, int(atr)); t = gost.sma(c, int(sma))
    with np.errstate(invalid="ignore"):
        buy = recent & (c > lvl) & (v > gost.sma(v, 20)) & (c > t)
    xl, rd = _dur(buy, c, a, stop, iz)
    sig = np.where(buy & ~np.isnan(rd), 1.0, 0.0)
    # giriş yalnız pozisyonda değilken; motor zaten açıkken yeni sinyali yok sayar
    return dict(sig=sig, xl=xl, rdd=rd, poc=True)
