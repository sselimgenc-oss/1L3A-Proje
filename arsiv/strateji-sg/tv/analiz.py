"""Portföy ölçütleri ve Aşama 3 eleme kuralları."""
import numpy as np, pandas as pd, itertools, importlib
from math import erf, sqrt
from . import motor, veri

def gunluk_egri(sonuclar, bas=None, son=None):
    """Her enstrüman sleeve'inin kümülatif $ (gerçekleşen+açık) eğrisini günlüğe çevirip toplar -> portföy özsermaye (günlük)."""
    seri = []
    for r in sonuclar:
        s = pd.Series(r.mtm, index=r.idx)
        s = s[~s.index.duplicated(keep="last")].resample("1D").last().ffill()
        seri.append(s)
    if not seri: return pd.Series(dtype=float)
    ix = pd.date_range(min(s.index[0] for s in seri), max(s.index[-1] for s in seri), freq="D")
    top = sum(s.reindex(ix).ffill().fillna(0.0) for s in seri)
    return motor.SERMAYE + top

def _takvim(egri, kripto_mi):
    if kripto_mi: return egri, 365
    e = egri[egri.index.dayofweek < 5]
    return e, 252

def sharpe(ret, yil):
    ret = ret.dropna()
    if len(ret) < 30 or ret.std() == 0: return np.nan
    return ret.mean()/ret.std()*np.sqrt(yil)

def psr(ret, yil, ref=0.0):
    r = ret.dropna(); n = len(r)
    if n < 30 or r.std() == 0: return np.nan
    sr = r.mean()/r.std(); sk = ((r-r.mean())**3).mean()/r.std()**3; ku = ((r-r.mean())**4).mean()/r.std()**4
    z = (sr - ref)*np.sqrt(n-1)/np.sqrt(1 - sk*sr + (ku-1)/4*sr**2)
    return 0.5*(1+erf(z/sqrt(2)))

def maxdd(e):
    pk = e.cummax(); dd = (e-pk)/pk
    ayrik = (dd < 0)
    # en uzun düşüş süresi (gün)
    en = 0; bas = None
    for t, v in dd.items():
        if v < 0:
            if bas is None: bas = t
            en = max(en, (t-bas).days)
        else: bas = None
    return -dd.min(), en

def olc(sonuclar, tur, kripto_mi, kesim=None):
    """Tek bir koşu için ölçüt sözlüğü. kesim: eğitim/OOS bölme tarihi."""
    tab = pd.concat([motor.islem_tablosu(r) for r in sonuclar if len(r.ts)], ignore_index=True) if any(len(r.ts) for r in sonuclar) else pd.DataFrame()
    e = gunluk_egri(sonuclar)
    ek, yil = _takvim(e, kripto_mi)
    ret = ek.pct_change().dropna()
    m = dict(n=len(tab))
    if len(tab) == 0 or len(ret) < 30:
        return dict(m, kar=0.0, pf=np.nan, sharpe=np.nan), tab, e
    kar = tab.kar.sum()
    w = tab.kar[tab.kar > 0].sum(); l = -tab.kar[tab.kar < 0].sum()
    # R: stop varsa kar/risk, yoksa kar / ort. kayıp
    kay = tab.kar[tab.kar < 0]
    birim = -kay.mean() if len(kay) else np.nan
    R = np.where(tab.risk > 0, tab.kar/np.where(tab.risk > 0, tab.risk, 1), tab.kar/birim)
    ey = ek.iloc[-1]/ek.iloc[0]; yrs = max((ek.index[-1]-ek.index[0]).days/365.25, 0.1)
    dd, dds = maxdd(ek)
    cagr = ey**(1/yrs)-1
    m.update(kar=kar, pf=(w/l if l > 0 else np.inf), sharpe=sharpe(ret, yil), beklenti_R=float(np.nanmean(R)),
             kazanma=float((tab.kar > 0).mean()), maxdd=dd, dd_gun=dds, cagr=cagr, calmar=(cagr/dd if dd > 0 else np.inf),
             psr=psr(ret, yil), tutma_gun=float(((tab.cikis-tab.giris).dt.total_seconds()/86400).median()),
             ort_islem_getiri=float((tab.kar/(tab.adet*tab.gfiyat)).mean()), netR_toplam=float(np.nansum(R)))
    if kesim is not None:
        a = ret[ret.index < kesim]; b = ret[ret.index >= kesim]
        m["sharpe_egitim"] = sharpe(a, yil); m["sharpe_oos"] = sharpe(b, yil)
        m["oos_kar"] = float(ek[ek.index >= kesim].iloc[-1] - ek[ek.index >= kesim].iloc[0]) if (ek.index >= kesim).sum() > 1 else np.nan
    return m, tab, e

def sayisal_parametreler(P):
    return [k for k, v in P.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0]

def komsular(P, rng, adet_ortak=8):
    """±%20: her sayısal parametre ayrı ayrı (×0.8, ×1.2) + birlikte rastgele ~8 kombinasyon."""
    ks = sayisal_parametreler(P); out = []
    def uyg(v, c): 
        x = v*c
        return int(max(1, round(x))) if isinstance(v, int) else x
    for k in ks:
        for c in (0.8, 1.2):
            Q = dict(P); Q[k] = uyg(P[k], c)
            if Q[k] != P[k]: out.append(Q)
    for _ in range(adet_ortak):
        Q = dict(P)
        for k in ks: Q[k] = uyg(P[k], rng.choice([0.8, 1.2]))
        out.append(Q)
    return out
