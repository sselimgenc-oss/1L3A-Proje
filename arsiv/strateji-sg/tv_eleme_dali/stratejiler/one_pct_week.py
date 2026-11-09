"""TASC 2026.03 One Percent A Week (nVECqIQx): pazartesi açılışının %1 altına limit alış (hafta içi geçerli); dolunca +%1 hedef; cuma kapanışında çık. (Başa-baş çıkışı modellenmedi.)"""
import numpy as np
from tv import gost
ISIM = "One Percent A Week (TASC)"; PINE_ID = "nVECqIQx"
PARAM = dict(dip=1.0, hedef=1.0)
TF = "1d"; EVREN = ["endeks", "abd"]; YON = 1
NEDEN = "Haftalık seans mantığı; günlük hisse/ETF."
def sinyal(df, dip, hedef):
    o, c = df.o.values, df.c.values; n = len(c); dow = df.index.dayofweek.values
    sig = np.zeros(n); lep = np.full(n, np.nan); lepw = np.ones(n); xl = np.zeros(n, bool)
    for i in range(n):
        if dow[i] == 0:
            sig[i] = 1.0; lep[i] = o[i]*(1 - dip/100); lepw[i] = 4   # Pzt..Cum
        if dow[i] == 4: xl[i] = True
    return dict(sig=sig, lep=lep, lepw=lepw, xl=xl, tpp=hedef/100, poc=True)
