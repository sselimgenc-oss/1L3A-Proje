"""Ortak backtest motoru. Bar KAPANIŞINDA sinyal, SONRAKİ barın AÇILIŞINDA giriş.
Stop/hedef mum içinde; ikisi aynı mumda olursa önce stop. Pozisyon boyu: stop varsa işlem başı sabit %1 risk
(sermaye 10.000 $, bileşiksiz; pozisyon değeri en çok sermayenin %25'i), stop yoksa sabit %10 sermaye
(enstrüman sayısı N>10 ise %100/N: toplam brüt pozisyon en çok %100).
Masraf taraf başına: kripto %0,07 / ABD %0,02 / BIST %0,10 / emtia %0,03 + kayma %0,02."""
import numpy as np, pandas as pd
from numba import njit

SERMAYE = 10000.0
MASRAF = dict(kripto=0.0007, abd=0.0002, bist=0.0010, emtia=0.0003)
KAYMA = 0.0002
RISK = 0.01; TAVAN = 0.25; SABIT = 0.10

@njit(cache=True)
def _calistir(o, h, l, c, sig, xl, xs, sl, tp, dyl, dys, sld, tpd, sep, taa, toa, poc, maxhold, slp, tpp, tra, tro, trd, maliyet, risk_usd, tavan_usd, sabit_usd, yon_izin):
    """sig[i]: +1/-1 giriş (i barının kapanışında karar, i+1 açılışında dolar). xl/xs: long/short çıkış sinyali.
    sl/tp: giriş sinyal barındaki mutlak fiyat (nan=yok). dyl/dys: her barın kapanışında hesaplı izleyen stop (nan=yok).
    yon_izin: 1=yalnız long, -1=yalnız short, 0=ikisi."""
    n = len(c)
    ts = np.full((n, 9), np.nan); k = 0
    mtm = np.zeros(n); real = 0.0
    pos = 0; ep = 0.0; qty = 0.0; stop = np.nan; tgt = np.nan; ei = 0; risk0 = 0.0; ext = 0.0; tstop = np.nan; ta_e = np.nan; to_e = np.nan
    for i in range(1, n):
        # 1) bekleyen emirler (i-1 sinyali) açılışta
        wantx = (pos > 0 and xl[i-1]) or (pos < 0 and xs[i-1])
        s = sig[i-1]; fo = c[i-1] if poc else o[i]; pin = fo
        if s != 0 and not np.isnan(sep[i-1]):   # stop-giriş emri: yalnız ertesi mumda dokunursa dolar
            P = sep[i-1]
            if s > 0:
                if h[i] >= P: pin = max(o[i], P)
                else: s = 0
            else:
                if l[i] <= P: pin = min(o[i], P)
                else: s = 0
        if s != 0 and yon_izin != 0 and s != yon_izin: s = 0
        flip = (s != 0 and pos != 0 and s != pos)
        if pos != 0 and (wantx or flip):
            px = fo
            g = (px - ep)*qty*pos
            cost = abs(qty)*(ep + px)*maliyet
            real += g - cost
            ts[k, 0] = ei; ts[k, 1] = i; ts[k, 2] = pos; ts[k, 3] = ep; ts[k, 4] = px; ts[k, 5] = qty
            ts[k, 6] = g - cost; ts[k, 7] = risk0; ts[k, 8] = 1.0 if flip else (2.0 if wantx else 0.0); k += 1
            pos = 0
        if pos == 0 and s != 0:
            ep = pin; pos = int(s); ei = i
            st0 = sl[i-1]
            if np.isnan(st0):
                if not np.isnan(sld[i-1]): st0 = ep - pos*sld[i-1]
                elif slp > 0: st0 = ep*(1.0 - pos*slp)
            d0 = dyl[i-1] if pos > 0 else dys[i-1]
            if np.isnan(st0): st0 = d0
            elif not np.isnan(d0): st0 = max(st0, d0) if pos > 0 else min(st0, d0)
            stop = st0; tgt = tp[i-1]
            if np.isnan(tgt):
                if not np.isnan(tpd[i-1]): tgt = ep + pos*tpd[i-1]
                elif tpp > 0: tgt = ep*(1.0 + pos*tpp)
            ext = ep; tstop = np.nan; ta_e = taa[i-1]; to_e = toa[i-1]
            if (not np.isnan(stop)) and ((pos > 0 and stop >= ep) or (pos < 0 and stop <= ep)):
                stop = np.nan   # geçersiz stop
            if not np.isnan(stop):
                dist = abs(ep - stop)
                qty = min(risk_usd/dist, tavan_usd/ep); risk0 = qty*dist
            else:
                qty = sabit_usd/ep; risk0 = 0.0
        # 2) mum içi stop/hedef (yeni girilen mum dahil)
        if pos != 0:
            if i > ei:
                d = dyl[i-1] if pos > 0 else dys[i-1]
                if not np.isnan(d):
                    stop = d if np.isnan(stop) else (max(stop, d) if pos > 0 else min(stop, d))
            hit = 0; px = 0.0
            if not np.isnan(to_e) and i > ei:
                if pos > 0 and ext >= ep + ta_e: tstop = ext - to_e
                elif pos < 0 and ext <= ep - ta_e: tstop = ext + to_e
                if not np.isnan(tstop):
                    stop = tstop if np.isnan(stop) else (max(stop, tstop) if pos > 0 else min(stop, tstop))
            if tro > 0 and i - ei >= trd and i > ei:
                if pos > 0 and ext >= ep*(1.0+tra): tstop = ext*(1.0-tro)
                elif pos < 0 and ext <= ep*(1.0-tra): tstop = ext*(1.0+tro)
                if not np.isnan(tstop):
                    stop = tstop if np.isnan(stop) else (max(stop, tstop) if pos > 0 else min(stop, tstop))
            if not np.isnan(stop):
                if pos > 0 and l[i] <= stop: hit = 1; px = min(stop, o[i]) if i > ei else stop
                elif pos < 0 and h[i] >= stop: hit = 1; px = max(stop, o[i]) if i > ei else stop
            if hit == 0 and not np.isnan(tgt):
                if pos > 0 and h[i] >= tgt: hit = 2; px = max(tgt, o[i]) if i > ei else tgt
                elif pos < 0 and l[i] <= tgt: hit = 2; px = min(tgt, o[i]) if i > ei else tgt
            if hit == 0 and maxhold > 0 and i - ei >= maxhold:
                hit = 3; px = c[i]
            if hit != 0:
                g = (px - ep)*qty*pos; cost = abs(qty)*(ep + px)*maliyet
                real += g - cost
                ts[k, 0] = ei; ts[k, 1] = i; ts[k, 2] = pos; ts[k, 3] = ep; ts[k, 4] = px; ts[k, 5] = qty
                ts[k, 6] = g - cost; ts[k, 7] = risk0; ts[k, 8] = 10.0 + hit; k += 1
                pos = 0
        if pos != 0:
            ext = max(ext, h[i]) if pos > 0 else min(ext, l[i])
        mtm[i] = real + ((c[i] - ep)*qty*pos if pos != 0 else 0.0)
    if pos != 0:  # açık pozisyonu son kapanışta işlem say (veri sonu)
        px = c[n-1]; g = (px - ep)*qty*pos; cost = abs(qty)*(ep + px)*maliyet
        ts[k, 0] = ei; ts[k, 1] = n-1; ts[k, 2] = pos; ts[k, 3] = ep; ts[k, 4] = px; ts[k, 5] = qty
        ts[k, 6] = g - cost; ts[k, 7] = risk0; ts[k, 8] = 20.0; k += 1
        mtm[n-1] = real + g - cost
    return ts[:k], mtm

class Sonuc:
    def __init__(self, idx, ts, mtm, grup, sembol):
        self.idx, self.ts, self.mtm, self.grup, self.sembol = idx, ts, mtm, grup, sembol

def calistir(df, S, grup, sembol="", maliyet_carpan=1.0, yon=0, n_enstr=1):
    """df: o,h,l,c,v. S: sözlük (sig, xl, xs, sl, tp, dyl, dys, maxhold) – eksikler yok sayılır."""
    n = len(df); nanA = np.full(n, np.nan); falseA = np.zeros(n, np.bool_)
    sig = np.asarray(S.get("sig", np.zeros(n)), dtype=np.float64)
    ts, mtm = _calistir(df.o.values, df.h.values, df.l.values, df.c.values, sig,
        np.asarray(S.get("xl", falseA), np.bool_), np.asarray(S.get("xs", falseA), np.bool_),
        np.asarray(S.get("sl", nanA), np.float64), np.asarray(S.get("tp", nanA), np.float64),
        np.asarray(S.get("dyl", nanA), np.float64), np.asarray(S.get("dys", nanA), np.float64),
        np.asarray(S.get("sld", nanA), np.float64), np.asarray(S.get("tpd", nanA), np.float64), np.asarray(S.get("sep", nanA), np.float64),
        np.asarray(S.get("taa", nanA), np.float64), np.asarray(S.get("toa", nanA), np.float64), bool(S.get("poc", False)),
        int(S.get("maxhold", 0)), float(S.get("slp", 0.0)), float(S.get("tpp", 0.0)), float(S.get("tra", 0.0)), float(S.get("tro", 0.0)), int(S.get("trd", 0)), (MASRAF[grup] + KAYMA)*maliyet_carpan, SERMAYE*RISK, SERMAYE*TAVAN, SERMAYE*min(SABIT, 1.0/max(n_enstr, 1)), int(yon))
    return Sonuc(df.index, ts, mtm, grup, sembol)

def islem_tablosu(r):
    t = pd.DataFrame(r.ts, columns=["gi","ci","yon","gfiyat","cfiyat","adet","kar","risk","neden"])
    if len(t) == 0: return t
    t["giris"] = r.idx[t.gi.astype(int)]; t["cikis"] = r.idx[t.ci.astype(int)]; t["sembol"] = r.sembol
    return t
