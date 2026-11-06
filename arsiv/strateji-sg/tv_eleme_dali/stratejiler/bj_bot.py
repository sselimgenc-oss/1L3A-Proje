"""3Commas Bot (MvlwAzSg, Bjorgum): EMA21 EMA50'yi yukarı keserse long (aşağı keserse short); stop = 5 mumluk dip/tepe ∓ 1 ATR, hedef 1R (RnR=1); iz süren stop ve ters işlem varsayılanda kapalı; yalnız pozisyon yokken giriş."""
import numpy as np
from tv import gost
ISIM = "Bjorgum 3Commas Bot (EMA kesişimi)"; PINE_ID = "MvlwAzSg"
PARAM = dict(m1=21, m2=50, swing=5, atr=14, risk_c=1.0, rr=1.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
def sinyal(df, m1, m2, swing, atr, risk_c, rr):
    h, l, c = df.h.values, df.l.values, df.c.values; a = gost.atr(h, l, c, int(atr)); e1, e2 = gost.ema(c, int(m1)), gost.ema(c, int(m2))
    up = gost.crossover(np.nan_to_num(e1), np.nan_to_num(e2)) & ~np.isnan(e2); dn = gost.crossunder(np.nan_to_num(e1), np.nan_to_num(e2)) & ~np.isnan(e2)
    ls = gost.lowest(l, int(swing)) - a*risk_c; ss = gost.highest(h, int(swing)) + a*risk_c
    return dict(sig=gost.flipsig(up, dn)*np.where(up | dn, 1, 0), sl=np.where(up, ls, np.where(dn, ss, np.nan)), tp=np.where(up, c+(c-ls)*rr, np.where(dn, c-(ss-c)*rr, np.nan)))
