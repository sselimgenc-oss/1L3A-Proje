"""Tüm sembollerde strateji koşturma ve IS/OOS raporu."""
import itertools
import json
import sys
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from . import data as D, features as F, backtest as B
from .strategies import STRATS

IS_END = "2024-01-01"
_FEAT = {}


def _feat(sym):
    if sym not in _FEAT:
        _FEAT[sym] = F.build(sym)
    return _FEAT[sym]


def run_symbol(args):
    name, p, sym = args
    f = _feat(sym)
    kw = STRATS[name](f, p)
    t = B.simulate(f, funding=f["funding"].values, **kw)
    t["sym"] = sym
    return t


def run(name, p, syms=None, pool=None):
    syms = syms or D.symbols()
    jobs = [(name, p, s) for s in syms]
    res = list(pool.map(run_symbol, jobs)) if pool else list(map(run_symbol, jobs))
    res = [r for r in res if len(r)]
    return pd.concat(res, ignore_index=True) if res else pd.DataFrame()


def report(t, risk=0.005):
    return {"ALL": B.metrics(t, risk), "IS": B.metrics(t, risk, end=IS_END), "OOS": B.metrics(t, risk, start=IS_END)}


def grid(name, base, space, pool, sort_key="score", top=15, min_trades=300):
    rows = []
    keys = list(space)
    for vals in itertools.product(*[space[k] for k in keys]):
        p = dict(base); p.update(dict(zip(keys, vals)))
        t = run(name, p, pool=pool)
        if len(t) == 0:
            continue
        m = B.metrics(t, 0.005, end=IS_END); mo = B.metrics(t, 0.005, start=IS_END)
        if m.get("trades", 0) < min_trades:
            continue
        rows.append(dict(**{k: str(v) for k, v in zip(keys, vals)},
                         is_wr=m["win_rate"], is_pf=m["pf"], is_avgR=m["avg_R"], is_n=m["trades"],
                         oos_wr=mo.get("win_rate"), oos_pf=mo.get("pf"), oos_avgR=mo.get("avg_R"), oos_n=mo.get("trades")))
    df = pd.DataFrame(rows)
    if len(df):
        df["score"] = df["is_avgR"] * np.sqrt(df["is_n"]) * (df["is_wr"] >= 45)
        df = df.sort_values(sort_key, ascending=False)
    return df
