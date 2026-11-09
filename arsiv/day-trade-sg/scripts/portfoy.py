"""Portföy simülasyonu: STR=strateji1,strateji2 MAXP=8 YON=long [KES=YYYY-AA-GG] python scripts/portfoy.py <maliyet>"""
import sys, json; from pathlib import Path; R=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(R)); sys.path.insert(0,str(R/'scripts'))
import numpy as np, pandas as pd
from kripto_tara import kripto
from daytrade.runner import bundle
from daytrade.backtest import simulate
from daytrade.strategies import STRATEGIES
from kagit.motor import portfoy
import os
SEC0={"S10_gec":dict(at_utc=16,at_end=20,move_atr=1.0,stop_mode="atr",stop_atr_d=1.0,trend="h4+h1",yon=os.environ.get("YON","both"),btc_filter=os.environ.get("BTC")=="1"),
"S13_falsebreak":dict(trend="po_h1",adx_min=25,n_high=80,n_pull=12,k_bars=12,stop_atr_d=1.0,btc_filter=os.environ.get("BTC")=="1"),
"S15_tdpullback":dict(level="ema20",move_atr=1.0,from_utc=14,to_utc=21,stop="atr",stop_atr_d=0.75,touch_atr=0.2,btc_filter=os.environ.get("BTC")=="1"),
"S12_strongclose":dict(close_pos=0.7,above_pdh=False,at_utc=0.0,at_end=0.5),
"S10_trendday":dict(at_utc=7,move_atr=0.3,stop_mode="atr",stop_atr_d=0.75,trend="strict",adx_min=25),
     "S11_trendday_us":dict(at_utc=14,move_atr=0.5,stop_mode="atr",stop_atr_d=0.75,trend="strict",adx_min=25),
     "S9_session":dict(anchor_utc=7,range_h=4,trend="strict",adx_min=25,partial_R=1.0,stop_mode="opposite",width_max=2.0,volume=True,target_R=None,max_atr=6.0,window_h=3)}
SEC={k:v for k,v in SEC0.items() if k in os.environ.get("STR","S10_trendday,S9_session").split(",")}
if os.environ.get("REJIM"):   # REJIM=200 [REJIM_ST=S13_falsebreak]: rejim filtresi
    for k in (os.environ.get("REJIM_ST") or ",".join(SEC)).split(","):
        if k in SEC: SEC[k]=dict(SEC[k], rejim=int(os.environ["REJIM"]))
c=float(sys.argv[1]) if len(sys.argv)>1 else 0.0005
out=[]
for inst in kripto("15m"):
    df=bundle(inst,"15m")
    if df is None: continue
    cut=df.index[0]+(df.index[-1]-df.index[0])*0.7
    for st,p in SEC.items():
        tr=simulate(df,STRATEGIES["S10_trendday" if st=="S10_gec" else st][0](df,**p),c,inst.symbol,st)
        if len(tr):
            tr["asset_class"]="crypto"
            kes=os.environ.get("KES")
            if kes:
                k=pd.Timestamp(kes,tz="UTC"); tr["split"]=np.where(tr.entry_time<k,"YENI(gorulmemis)",np.where(tr.entry_time<cut,"eg","te"))
            else:
                tr["split"]=np.where(tr.entry_time<cut,"eg","te")
            sb=tr.entry_time-pd.Timedelta(minutes=15); f=df.reindex(sb)
            tr["skor"]=(tr.dir.values*(f.close-f.dopen)/f.atr_d).values
            out.append(tr)
tr=pd.concat(out,ignore_index=True)
if os.environ.get("BAS"):   # yalnız bu tarih aralığında AÇILAN işlemler (stres testi)
    tr=tr[(tr.entry_time>=pd.Timestamp(os.environ["BAS"],tz="UTC"))&(tr.entry_time<pd.Timestamp(os.environ.get("BIT","2100-01-01"),tz="UTC"))]
tr["gun"]=tr.entry_time.dt.date
a=set(zip(tr[tr.strategy=="S10_trendday"].symbol,tr[tr.strategy=="S10_trendday"].gun)); b=set(zip(tr[tr.strategy=="S9_session"].symbol,tr[tr.strategy=="S9_session"].gun))
print(f"örtüşen sembol-gün: {len(a&b)} / S10 {len(a)} · S9 {len(b)}")
cfg=dict(sermaye=10000,risk=0.005,max_pozisyon=int(os.environ.get("MAXP",5)),max_agirlik=0.3,max_toplam_agirlik=1.0,gunluk_zarar_limiti=-0.03)
if os.environ.get("AYRI"):   # her stratejiye ayrı alt hesap (sermaye ve pozisyon hakkı bölünür)
    k=len(SEC); parts=[]
    for st in SEC:
        sub=dict(cfg, sermaye=cfg["sermaye"]/k, max_pozisyon=max(1, cfg["max_pozisyon"]//k))
        parts.append(portfoy(tr[tr.strategy==st], sub))
    al=pd.concat(parts, ignore_index=True)
else:
    al=portfoy(tr,cfg)
al=al.sort_values("exit_time"); al["ozs"]=10000+al.kar_usd.cumsum()
dd=(al.ozs/al.ozs.cummax()-1).min()
for sp in sorted(al.split.unique()):
    s=al[al.split==sp]; r=s.R.to_numpy(); gl=-r[r<=0].sum()
    print(sp, f"işlem {len(s)} kazanma {(r>0).mean():.1%} PF {r[r>0].sum()/gl:.2f} kâr {s.kar_usd.sum():+,.0f}$")
print(f"TOPLAM: {len(al)} işlem, 10.000$ → {al.ozs.iloc[-1]:,.0f}$ ({al.ozs.iloc[-1]/10000-1:+.1%}), maks. düşüş {dd:.1%}, dönem {al.entry_time.min().date()} → {al.exit_time.max().date()}")
al["ay"]=al.exit_time.dt.strftime("%Y-%m")
al["yil"]=al.exit_time.dt.strftime("%Y-%m").str[:4]+("H1")
al["ceyrek"]=al.exit_time.dt.to_period("Q").astype(str)
q=al.groupby("ceyrek").agg(n=("R","size"),wr=("R",lambda r:(r>0).mean()),pf=("R",lambda r:r[r>0].sum()/-r[r<=0].sum()),kar=("kar_usd","sum")).round(2)
yy=al.groupby(al.exit_time.dt.year).agg(n=("R","size"),wr=("R",lambda r:(r>0).mean()),pf=("R",lambda r:r[r>0].sum()/-r[r<=0].sum()),kar=("kar_usd","sum")).round(2)
print("== yıl"); print(yy.to_string())
print("== çeyrek"); print(q.to_string()); print("pozitif çeyrek:",(q.kar>0).sum(),"/",len(q))
m=al.groupby("ay").kar_usd.sum().round(0); print("aylık $:",m.to_dict()); print("pozitif ay:",(m>0).sum(),"/",len(m))
for d in (1,-1):
    s_=al[al.dir==d]; r=s_.R.to_numpy(); print("yön",d,len(s_),f"{(r>0).mean():.1%}",f"PF {r[r>0].sum()/-r[r<=0].sum():.2f}",f"{s_.kar_usd.sum():+,.0f}$")
for st in SEC: s=al[al.strategy==st]; r=s.R.to_numpy(); print(st, len(s), f"{(r>0).mean():.1%}", f"PF {r[r>0].sum()/-r[r<=0].sum():.2f}", f"{s.kar_usd.sum():+,.0f}$")

# SHARPE: günlük özsermaye getirisinden (gerçekleşen kâr, 365 gün/yıl)
gun = al.groupby(al.exit_time.dt.floor("D")).kar_usd.sum()
idx = pd.date_range(gun.index.min(), gun.index.max(), freq="D")
ozs = 10000 + gun.reindex(idx, fill_value=0).cumsum()
r = ozs.pct_change().dropna()
yil = len(idx) / 365
cagr = (ozs.iloc[-1] / 10000) ** (1 / yil) - 1
print(f"SHARPE yıllık {r.mean() / r.std() * np.sqrt(365):.2f} · Sortino {r.mean() / r[r < 0].std() * np.sqrt(365):.2f} · yıllık getiri (CAGR) {cagr:.1%} · Calmar {cagr / abs((ozs / ozs.cummax() - 1).min()):.2f}")
R = al.R.to_numpy(); print(f"GENEL kazanma {(R > 0).mean():.1%} · kâr faktörü {R[R > 0].sum() / -R[R <= 0].sum():.2f} · ort. R {R.mean():+.3f} · işlem {len(R)}")
