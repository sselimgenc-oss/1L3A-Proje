import pandas as pd,numpy as np
df=pd.read_pickle("etf.pkl")
m=df.resample("ME").last().dropna(how="all")
r=m.pct_change()
COST=0.001
def run(weights_fn,name,start="2005-12-31"):
    W=weights_fn(m)  # weights decided at month-end t, held over t->t+1
    W=W.reindex(m.index).fillna(0.0)
    ret=(W.shift(1)*r).sum(axis=1)
    turn=(W-W.shift(1).fillna(0)).abs().sum(axis=1)
    net=ret-COST*turn
    net=net.loc[start:"2025-10-31"].dropna()
    return net,turn.loc[net.index]
def stats(net,turn=None):
    eq=(1+net).cumprod()
    yrs=len(net)/12
    cagr=eq.iloc[-1]**(1/yrs)-1
    dd=(eq/eq.cummax()-1).min()
    sh=net.mean()/net.std()*np.sqrt(12) if net.std()>0 else np.nan
    return dict(cagr=round(cagr,4),maxdd=round(dd,4),sharpe=round(sh,2),tot=round(eq.iloc[-1]-1,3),ay_turn=round(turn.mean()*12,2) if turn is not None else None)
def gtaa(m):
    univ=["SPY","EFA","IEF","VNQ","DBC"]
    sma=m[univ].rolling(10).mean()
    ok=(m[univ]>sma)
    w=ok.astype(float)
    w=w.div(w.sum(axis=1).replace(0,np.nan),axis=0).fillna(0)  # eşit ağırlık, sinyal açıksa
    w=w*(1.0/len(univ))*0+w*1.0
    # eşit ağırlık over 5 slots; kapalı slotlar nakit
    return ok.astype(float)*(1.0/len(univ))
def mom_aa(m):
    univ=["SPY","EFA","EEM","IEF","TLT","DBC","GLD","VNQ"]
    mom=m[univ].pct_change(12)
    rank=mom.rank(axis=1,ascending=False)
    w=((rank<=3)&mom.notna()).astype(float)/3.0
    return w
def sector_mom(m):
    univ=["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB"]
    mom=m[univ].pct_change(12)
    rank=mom.rank(axis=1,ascending=False)
    return ((rank<=3)&mom.notna()).astype(float)/3.0
def bh_spy(m):
    w=pd.DataFrame(0.0,index=m.index,columns=m.columns); w["SPY"]=1.0; return w
res={}
for nm,fn in [("SPY al-tut",bh_spy),("GTAA 10ay SMA (Faber benzeri, 5 varlik)",gtaa),("Momentum varlik dagilimi (12ay, ilk 3/8)",mom_aa),("Sektor momentum (12ay, ilk 3/9)",sector_mom)]:
    net,turn=run(fn,nm)
    res[nm]=(stats(net,turn),net)
    sub={}
    for a,b in [("2006-2012","2012-12-31"),("2013-2019","2019-12-31"),("2020-2025","2025-10-31")]:
        x=net.loc[a[:4]:b] if False else net[(net.index>=pd.Timestamp(a[:4]+"-01-01"))&(net.index<=pd.Timestamp(b))]
        sub[a]=round((1+x).prod()-1,3)
    print(nm,res[nm][0],"donem:",sub)
