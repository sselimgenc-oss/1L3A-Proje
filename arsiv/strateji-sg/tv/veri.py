"""Veri indirici/okuyucu. Kripto: Binance spot (data-api.binance.vision), hisse/emtia: Yahoo. Önbellek: tv/veri/ (git dışı)."""
import sys, time, json, requests, pandas as pd, numpy as np
from pathlib import Path
KOK = Path(__file__).parent / "veri"
KRIPTO = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","DOT","LTC","TRX","NEAR","ATOM"]
BIST = ["THYAO","ASELS","AKBNK","GARAN","KCHOL","BIMAS","TUPRS","EREGL","FROTO","SISE"]
ABD = ["AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","AVGO","JPM","LLY"]
EMTIA = {"ALTIN":"GC=F","GUMUS":"SI=F","PETROL":"CL=F"}
ENDEKS = {"QQQ":"QQQ","SPY":"SPY"}
IV = {"15m":900,"1h":3600,"4h":14400,"1d":86400}
def kripto(sym, iv, bas="2019-01-01"):
    f = KOK/f"k_{sym}_{iv}.pkl"
    if f.exists(): return pd.read_pickle(f)
    t = int(pd.Timestamp(bas).timestamp()*1000); out=[]
    while True:
        for i in range(5):
            try:
                r = requests.get("https://data-api.binance.vision/api/v3/klines",params=dict(symbol=sym+"USDT",interval=iv,startTime=t,limit=1000),timeout=30)
                if r.status_code==200: break
            except requests.RequestException: pass
            time.sleep(2*(i+1))
        d = r.json() if r.status_code==200 else []
        if not d: break
        out += d; t = d[-1][0]+1
        if len(d)<1000: break
    if not out: return None
    df = pd.DataFrame(out).iloc[:,:6]; df.columns=["t","o","h","l","c","v"]
    df.index = pd.to_datetime(df.pop("t"),unit="ms"); df = df.astype(float)
    df.to_pickle(f); return df
def yahoo(sym, iv, **kw):
    import yfinance as yf
    f = KOK/f"y_{sym}_{iv}.pkl"
    if f.exists(): return pd.read_pickle(f)
    for i in range(4):
        try:
            d = yf.Ticker(sym).history(auto_adjust=True, interval=iv, **kw)
            if len(d): break
        except Exception: pass
        time.sleep(3*(i+1))
    else: return None
    d = d[["Open","High","Low","Close","Volume"]]; d.columns=["o","h","l","c","v"]
    if d.index.tz is not None: d.index = d.index.tz_convert("UTC").tz_localize(None)
    d = d[~d.index.duplicated()]
    d.to_pickle(f); return d
def al(ad, iv):
    """ad: kısa ad (BTC, AAPL, THYAO, ALTIN...). iv: 15m/1h/4h/1d."""
    if ad in KRIPTO:
        if iv == "4h":
            h = kripto(ad, "1h")
            return None if h is None else h.resample("4h").agg(dict(o="first",h="max",l="min",c="last",v="sum")).dropna()
        return kripto(ad, iv)
    s = ad+".IS" if ad in BIST else EMTIA.get(ad, ad)
    if iv=="1d": return yahoo(s,"1d",start="2015-01-01")
    if iv=="1h": return yahoo(s,"1h",period="729d")
    if iv=="4h":
        h = al(ad,"1h")
        if h is None: return None
        return h.resample("4h").agg(dict(o="first",h="max",l="min",c="last",v="sum")).dropna()
    if iv=="15m": return yahoo(s,"15m",period="59d")
def grup(ad):
    return "kripto" if ad in KRIPTO else "bist" if ad in BIST else "abd" if ad in ABD or ad in ENDEKS else "emtia"
if __name__=="__main__":
    KOK.mkdir(exist_ok=True)
    for iv in ["1d","1h"]:
        for a in KRIPTO: print(a,iv,len(kripto(a,iv)) if kripto(a,iv) is not None else None,flush=True)
    for iv in ["1d","1h"]:
        for a in BIST+ABD+list(EMTIA)+list(ENDEKS):
            d=al(a,iv); print(a,iv,None if d is None else len(d),flush=True)
