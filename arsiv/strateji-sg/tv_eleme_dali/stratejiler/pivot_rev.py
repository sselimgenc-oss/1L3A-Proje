"""Pivot Reversal (kzp8e4X3, 'Monthly Returns' örnek betiği): pivot tepesi (2 sol/1 sağ mum) onaylanınca o tepenin 1 tick üstüne stop-al emri (fiyat geçene kadar geçerli); pivot dibi için stop-sat emri; hep piyasada. Emir 1 mum geçerli olarak modellendi."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Pivot Reversal"; PINE_ID = "kzp8e4X3"
PARAM = dict(sol=2, sag=1)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Örnek betik; zaman dilimi yok; günlük, tüm pazarlar."
def sinyal(df, sol, sag):
    h, l = df.h.values, df.l.values; n = len(h); ph = _pivots(h, int(sol), int(sag), True); pl = _pivots(l, int(sol), int(sag), False)
    hp = lp = np.nan; le = se = False; sig = np.zeros(n); sep = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(ph[i]): hp = ph[i]; le = True
        elif le and h[i] > hp: le = False
        if not np.isnan(pl[i]): lp = pl[i]; se = True
        elif se and l[i] < lp: se = False
        if le and not se: sig[i] = 1.0; sep[i] = hp
        elif se and not le: sig[i] = -1.0; sep[i] = lp
        elif le and se: sig[i] = 1.0 if hp - h[i] < l[i] - lp else -1.0; sep[i] = hp if sig[i] > 0 else lp
    return dict(sig=sig, sep=sep)
