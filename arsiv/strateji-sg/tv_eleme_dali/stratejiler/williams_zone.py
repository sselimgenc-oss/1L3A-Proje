"""Williams %R Zone Scalper (TJuVmOfk, BullByte): %R(14) −80'i yukarı keserse long, −20'yi aşağı keserse short (varsayılanda yalnız Supertrend süzgeci açık; Pine'daki süzgeç hatalı yazılmış: long süzgeci `close > yön(±1)` ≈ hep doğru, short için `close < Supertrend çizgisi`); SL/TP kapalı, ters sinyalde dön."""
import numpy as np
from tv import gost
ISIM = "Williams %R Zone Scalper"; PINE_ID = "TJuVmOfk"
PARAM = dict(wr=14, st_atr=10, st_carpan=3.0)
TF = "15m"; EVREN = ["kripto"]
NEDEN = "PDF: BTCUSD 5 dk; 5 dk tarihçesi yalnız seçili sembollerde indirildiği için 15 dk kripto evreni (çeviri 5 dk SEMBOL listesiyle ayrıca denenir)."
def sinyal(df, wr, st_atr, st_carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    hh, ll = gost.highest(h, int(wr)), gost.lowest(l, int(wr))
    with np.errstate(all="ignore"): w = -100*(hh-c)/(hh-ll)
    a = gost.atr(h, l, c, int(st_atr)); st, d = gost.supertrend(h, l, c, a, st_carpan, (h+l)/2)
    with np.errstate(invalid="ignore"):
        le = gost.crossover(np.nan_to_num(w, nan=-100.0), np.full(len(c), -80.0)) & (c > d)
        se = gost.crossunder(np.nan_to_num(w, nan=-100.0), np.full(len(c), -20.0)) & (c < st)
    return dict(sig=gost.flipsig(le, se))
