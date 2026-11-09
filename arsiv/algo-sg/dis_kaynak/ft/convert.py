"""algo-sg 1h CSV + funding -> freqtrade futures feather (1h/4h/12h/1d + funding/mark 1h & 8h)."""
import sys, os, glob, pandas as pd, numpy as np
sys.path.insert(0, "/home/user/algo-sg")
from algo import data as D
SRC = {"main": "/home/user/algo-sg/data", "stress": "/home/user/algo-sg/data_extra"}
for uni, root in SRC.items():
    out = f"user_data_{uni}/data/binance/futures"; os.makedirs(out, exist_ok=True)
    D.ROOT = root
    syms = [os.path.basename(p).replace(".csv.gz", "") for p in glob.glob(f"{root}/1h/*.csv.gz")]
    for s in syms:
        df = D.load_1h(s)
        base = s[:-4]; pair = f"{base}_USDT_USDT"
        for tf, rule in (("1h", None), ("4h", "4h"), ("12h", "12h"), ("1d", "1D")):
            x = df if rule is None else D.resample(df, rule)
            o = x[["open", "high", "low", "close", "volume"]].copy()
            o.insert(0, "date", o.index); o = o.reset_index(drop=True)
            o.to_feather(f"{out}/{pair}-{tf}-futures.feather")
        fr = D.load_funding(s)
        fr = (fr if fr is not None else pd.Series(dtype=float)).reindex(df.index).fillna(0.0)
        for tf in ("1h", "8h"):
            if tf == "1h":
                r = fr; mk = df["close"]
            else:
                r = fr.resample("8h", label="left", closed="left").sum(); mk = df["close"].resample("8h", label="left", closed="left").first()
            f = pd.DataFrame({"date": r.index, "open": r.values, "high": r.values, "low": r.values, "close": r.values, "volume": 0.0})
            f.to_feather(f"{out}/{pair}-{tf}-funding_rate.feather")
            m = pd.DataFrame({"date": mk.index, "open": mk.values, "high": mk.values, "low": mk.values, "close": mk.values, "volume": 0.0})
            m.to_feather(f"{out}/{pair}-{tf}-mark.feather")
    print(uni, len(syms), [x[:-4] for x in sorted(syms)])
