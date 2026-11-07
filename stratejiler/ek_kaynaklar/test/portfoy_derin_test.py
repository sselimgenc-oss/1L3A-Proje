import pandas as pd,numpy as np
rng=np.random.default_rng(7)
df=pd.read_pickle("etf2.pkl")
m=df.resample("ME").last()
r=m.pct_change()
cash=r["SHY"]
def sim(W,cost=0.001):
    W=W.reindex(m.index).fillna(0.0)
    ret=(W.shift(1)*r.drop(columns=["SHY"],errors="ignore")[W.columns].fillna(0)).sum(axis=1)
    cw=1-W.sum(axis=1)
    ret=ret+cw.shift(1).fillna(0)*cash.fillna(0)
    turn=(W-W.shift(1).fillna(0)).abs().sum(axis=1)
    return (ret-cost*turn).loc["2006-01-01":"2025-10-31"].dropna()
def st(net):
    eq=(1+net).cumprod(); yrs=len(net)/12
    return dict(cagr=round(eq.iloc[-1]**(1/yrs)-1,4),dd=round((eq/eq.cummax()-1).min(),4),sh=round(net.mean()/net.std()*np.sqrt(12),2))
def gtaa(n=10,univ=("SPY","EFA","IEF","VNQ","DBC")):
    sma=m[list(univ)].rolling(n).mean()
    return (m[list(univ)]>sma).astype(float)/len(univ)
def mom(lb=12,k=3,univ=("SPY","EFA","EEM","IEF","TLT","DBC","GLD","VNQ")):
    mo=m[list(univ)].pct_change(lb); rk=mo.rank(axis=1,ascending=False)
    return ((rk<=k)&mo.notna()).astype(float)/k
spy=sim(pd.DataFrame({"SPY":1.0},index=m.index))
R={}
R["SPY"]=sim(pd.DataFrame({"SPY":1.0},index=m.index))
R["GTAA10"]=sim(gtaa(10)); R["MOM12_3"]=sim(mom(12,3))
for k,v in R.items():
    print(k,st(v))
# alt sayılar: komşu parametreler (raporlanır, seçilmez)
print("\n-- GTAA komsuluk")
for n in [6,8,10,12]:
    x=sim(gtaa(n)); print("SMA",n,st(x), "Sharpe>SPY:", st(x)["sh"]>st(spy)["sh"])
print("\n-- Momentum komsuluk")
rows=[]
for lb in [6,9,12]:
    for k in [2,3,4]:
        x=sim(mom(lb,k)); s=st(x); rows.append((lb,k,s["sh"],s["dd"],s["cagr"]))
for row in rows: print(row)
print("share sharpe>SPY:", np.mean([r_[2]>st(spy)["sh"] for r_ in rows]), " share DD<=20%:", np.mean([r_[3]>=-0.20 for r_ in rows]))
# bootstrap: Sharpe farkı SPY'a göre (blok bootstrap, blok=6)
def block_boot(a,b,B=2000,L=6):
    n=len(a); d=[]
    for _ in range(B):
        idx=[]
        while len(idx)<n:
            s=rng.integers(0,n-L+1); idx+=list(range(s,s+L))
        idx=np.array(idx[:n]); x=a.values[idx]; y=b.values[idx]
        d.append((x.mean()/x.std()-y.mean()/y.std())*np.sqrt(12))
    d=np.array(d); return np.percentile(d,[2.5,50,97.5]).round(2)
print("\n-- Sharpe farki vs SPY (blok bootstrap 95%):")
for k in ["GTAA10","MOM12_3"]:
    a=R[k].reindex(spy.index); print(k, block_boot(a,spy.reindex(a.index)))
# rastgele seçim kıyası: her ay rastgele 3/8 ve 3/9 seçim
print("\n-- Rastgele secim (1000 sim, 8 varlik, 3 secim):")
univ=["SPY","EFA","EEM","IEF","TLT","DBC","GLD","VNQ"]
sh=[]
for _ in range(1000):
    W=pd.DataFrame(0.0,index=m.index,columns=univ)
    for t in m.index:
        pick=rng.choice(univ,3,replace=False); W.loc[t,pick]=1/3
    sh.append(st(sim(W))["sh"])
sh=np.array(sh); print("rastgele Sharpe medyan",np.median(sh).round(2),"p95",np.percentile(sh,95).round(2),"MOM12_3 Sharpe",st(R['MOM12_3'])["sh"])
print("\n-- Maliyet x1/x2/x3 (GTAA, MOM)")
for c in [0.001,0.002,0.003]:
    print(c, st(sim(gtaa(10),c)), st(sim(mom(12,3),c)))
