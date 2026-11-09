"""OTT Strategy Version (ycDUERPO): VAR(OTT periyodu=1) çizgisi OTT[2]'yi keserse yön değiştir (destek çizgisi kesişimi)."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "OTT (strateji sürümü)"; PINE_ID = "ycDUERPO"
PARAM = dict(periyot=1, yuzde=0.1)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _ott(src, pds, percent):
    n = len(src); var = np.zeros(n); ls = np.zeros(n); ss = np.zeros(n); d = np.ones(n); o = np.zeros(n)
    al = 2.0/(pds+1)
    for i in range(n):
        if i == 0: var[i] = src[i]; o[i] = src[i]; ls[i]=src[i]; ss[i]=src[i]; continue
        ud = 0.0; dd = 0.0
        for j in range(max(1, i-8), i+1):
            ud += (src[j]-src[j-1]) if src[j] > src[j-1] else src[j]
            dd += (src[j-1]-src[j]) if src[j] < src[j-1] else src[j]
        cmo = (ud-dd)/(ud+dd) if (ud+dd) != 0 else 0.0
        k = abs(cmo)
        var[i] = al*k*src[i] + (1-al*k)*var[i-1]
        f = var[i]*percent*0.01
        ls[i] = var[i]-f; ss[i] = var[i]+f
        lsp = ls[i-1]; ssp = ss[i-1]
        if var[i] > lsp: ls[i] = max(ls[i], lsp)
        if var[i] < ssp: ss[i] = min(ss[i], ssp)
        d[i] = d[i-1]
        if d[i] == -1 and var[i] > ssp: d[i] = 1
        elif d[i] == 1 and var[i] < lsp: d[i] = -1
        mt = ls[i] if d[i] == 1 else ss[i]
        o[i] = mt*(200+percent)/200 if var[i] > mt else mt*(200-percent)/200
    return var, o
def sinyal(df, periyot, yuzde):
    var, o = _ott(df.c.values, float(periyot), yuzde); o2 = np.nan_to_num(gost.sh(o, 2))
    return dict(sig=gost.flipsig(gost.crossover(var, o2), gost.crossunder(var, o2)))
