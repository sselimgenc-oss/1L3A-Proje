import pandas as pd,numpy as np
rng=np.random.default_rng(11)
df=pd.read_pickle("etf_wide.pkl"); m=df.resample("ME").last(); r=m.pct_change(); cash=r["SHY"]
def sim(W,cost=0.001):
    W=W.reindex(m.index).fillna(0.0)
    cols=[c for c in W.columns if c!="SHY"]
    ret=(W[cols].shift(1)*r[cols].fillna(0)).sum(axis=1)
    ret=ret+(1-W.sum(axis=1)).shift(1).fillna(0)*cash.fillna(0)
    turn=(W-W.shift(1).fillna(0)).abs().sum(axis=1)
    return (ret-cost*turn).loc["2006-01-01":"2025-10-31"].dropna()
def st(x):
    eq=(1+x).cumprod(); y=len(x)/12
    return dict(cagr=round(eq.iloc[-1]**(1/y)-1,4),dd=round((eq/eq.cummax()-1).min(),4),sh=round(x.mean()/x.std()*np.sqrt(12),2))
W8=["SPY","EFA","EEM","IEF","TLT","DBC","GLD","VNQ"]
WIDE=["SPY","EFA","EEM","IEF","TLT","AGG","LQD","TIP","DBC","GLD","SLV","VNQ","IWM","QQQ","EWJ","EWG","EWU","EWZ","FXI","EWY"]
def gtaa(univ,n=10):
    sma=m[univ].rolling(n).mean(); return (m[univ]>sma).astype(float)/len(univ)
def mom(univ,lb=12,k=3):
    mo=m[univ].pct_change(lb); rk=mo.rank(axis=1,ascending=False)
    return ((rk<=k)&mo.notna()).astype(float)/k
spy=sim(pd.DataFrame({"SPY":1.0},index=m.index))
res={
 "SPY al-tut":spy,
 "GTAA 5 varlik (onceki evren)":sim(gtaa(["SPY","EFA","IEF","VNQ","DBC"])),
 "GTAA genis (20 varlik, SMA10, esit pay)":sim(gtaa(WIDE)),
 "Momentum 8 varlik (onceki)":sim(mom(W8)),
 "Momentum genis (20 varlik, 12ay ilk3)":sim(mom(WIDE)),
}
for k,v in res.items():
    s=st(v); sub=[]
    for a,b in [("2006","2012"),("2013","2019"),("2020","2025")]:
        x=v[(v.index>=f"{a}-01-01")&(v.index<=f"{b}-12-31")]; sub.append(round((1+x).prod()-1,2))
    print(f"{k:42s}",s,"donem",sub)
def bb(a,b,B=2000,L=6):
    n=len(a); d=[]
    for _ in range(B):
        idx=[]
        while len(idx)<n: s=rng.integers(0,n-L+1); idx+=list(range(s,s+L))
        idx=np.array(idx[:n]); x=a.values[idx]; y=b.values[idx]
        d.append((x.mean()/x.std()-y.mean()/y.std())*np.sqrt(12))
    return np.percentile(d,[2.5,50,97.5]).round(2)
print("\nBootstrap Sharpe farki vs SPY:")
for k in ["GTAA genis (20 varlik, SMA10, esit pay)","Momentum genis (20 varlik, 12ay ilk3)"]:
    a=res[k]; print(k, bb(a,spy.reindex(a.index)))
