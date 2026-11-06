"""Velocity Breakout Strategy (m1JDhFR9): EMA20/EMA50 trendinde; giriş: altın kesişim (yapı filtreli, ≤%10 koşu), EMA'ya geri çekilip yön mumu (discount bölgesinde, ATR izleyen stop yeşil) ya da sıkışma (4 mum içeride) kırılımı; çıkış: UT-benzeri ATR izleyen stop kırılımı (kârdayken ve ADX<20 ise sıkı 1.5 ATR) ya da ölüm kesişimi. Yalnız long."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Velocity Breakout Strategy"; PINE_ID = "m1JDhFR9"
PARAM = dict(fast=20, slow=50, yap=12, kosu=10.0, smc=100, atr=10, atr_c=3.0, sikı=1.5, adx_sq=20.0, consol=4)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _vbs(o, h, l, c, fe, se, adx, a10, hh5p, lw4, rlow, drh, drl, atr_c, tight, adx_sq, consol, chase):
    n = len(c); sig = np.zeros(n); xl = np.zeros(n, np.bool_)
    xs = 0.0; pt = 0; mt = np.nan; mb = np.nan; ins = 0; armed = False; mbl = l[0]; barm = True; inpos = False; ep = 0.0
    for i in range(1, n):
        was = inpos
        inprofit = inpos and c[i] > ep
        sq = (adx[i] < adx_sq) and inprofit
        nl = (tight if sq else atr_c)*a10[i] if not np.isnan(a10[i]) else 0.0
        pxs = xs
        if c[i] > pxs and c[i-1] > pxs: xs = max(pxs, c[i]-nl)
        elif c[i] < pxs and c[i-1] < pxs: xs = min(pxs, c[i]+nl)
        elif c[i] > pxs: xs = c[i]-nl
        else: xs = c[i]+nl
        ppt = pt
        if c[i-1] < pxs and c[i] > pxs: pt = 1
        elif c[i-1] > pxs and c[i] < pxs: pt = -1
        green = pt == 1
        bull = fe[i] > se[i]; bullc = c[i] >= o[i]
        brk = armed and (not np.isnan(mt)) and c[i] > mt and bullc and (bull and green)
        if np.isnan(mt) or c[i] > mt or c[i] < mb:
            mt = h[i]; mb = l[i]; ins = 0; armed = False
        else: ins += 1
        if ins >= consol: armed = True
        gc = fe[i-1] <= se[i-1] and fe[i] > se[i]; dc = fe[i-1] >= se[i-1] and fe[i] < se[i]
        if fe[i-1] >= se[i-1] and fe[i] < se[i]: mbl = l[i]
        if not bull: mbl = min(mbl, l[i])
        validb = (not np.isnan(rlow[i])) and rlow[i] > mbl
        run = (c[i]-rlow[i])/rlow[i]*100 if (not np.isnan(rlow[i]) and rlow[i] > 0) else 1e9
        takex = gc and validb and run <= chase
        if (not np.isnan(hh5p[i])) and c[i] > hh5p[i]: barm = True
        body = abs(c[i]-o[i]); lwk = min(o[i], c[i]) - l[i]; sweep = lwk > body*1.5 and bullc
        eq = drl[i] + (drh[i]-drl[i])*0.60; indisc = c[i] <= eq
        touched = (not np.isnan(lw4[i])) and lw4[i] <= fe[i]; shift = c[i] > fe[i] and bullc
        reload = bull and barm and touched and indisc and (shift or sweep) and green and (not gc)
        if reload: barm = False
        entry = takex or reload or brk
        if inpos and ((pt == -1 and ppt == 1) or dc): xl[i] = True; inpos = False
        if (not was) and entry and i+1 < n: sig[i] = 1.0; inpos = True; ep = o[i+1]
    return sig, xl
def sinyal(df, fast, slow, yap, kosu, smc, atr, atr_c, sikı, adx_sq, consol):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    fe, se = gost.ema(c, int(fast)), gost.ema(c, int(slow)); _, _, ad = gost.dmi(h, l, c, 14, 14); a10 = gost.atr(h, l, c, int(atr))
    sg, xl = _vbs(o, h, l, c, np.nan_to_num(fe), np.nan_to_num(se), np.nan_to_num(ad, nan=50.0), a10, gost.sh(gost.highest(h, 5)), gost.lowest(l, 4), gost.lowest(l, int(yap)), gost.highest(h, int(smc)), gost.lowest(l, int(smc)), atr_c, sikı, adx_sq, int(consol), kosu)
    return dict(sig=sg, xl=xl)
