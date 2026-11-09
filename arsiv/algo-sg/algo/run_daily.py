"""Haftalık yön + günlük işlem: çoklu coin koşturma, IS/OOS ve portföy metrikleri."""
import itertools
import os
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from . import backtest as B
from . import daily as W
from .strategies_daily import strat
from .portfolio import simulate_portfolio, curve_stats

IS_END = "2024-01-01"
EXTRA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_extra")


def _one(args):
    p, sym, root = args
    f = W.build(sym, root)
    if len(f) < 300:
        return None
    t = B.simulate(f, funding=f["funding"].values, **strat(f, p))
    if len(t):
        t["sym"] = sym
    return t


def run(p, root=W.MAIN_ROOT, pool=None):
    jobs = [(p, s, root) for s in W.symbols(root)]
    res = list(pool.map(_one, jobs)) if pool else list(map(_one, jobs))
    res = [r for r in res if r is not None and len(r)]
    return pd.concat(res, ignore_index=True) if res else pd.DataFrame()


def evaluate(p, pool, risk=0.01, max_open=10, stress=True):
    out = {}
    for name, root in (("ana", W.MAIN_ROOT), ("stres", EXTRA)) if stress else (("ana", W.MAIN_ROOT),):
        t = run(p, root, pool)
        if len(t) == 0:
            out[name] = None; continue
        m = B.metrics(t, risk); mi = B.metrics(t, risk, end=IS_END); mo = B.metrics(t, risk, start=IS_END)
        c, _ = simulate_portfolio(t, risk=risk, max_open=max_open); cs = curve_stats(c)
        out[name] = dict(n=m["trades"], wr=m["win_rate"], pf=m["pf"], avgR=m["avg_R"],
                         is_wr=mi.get("win_rate"), is_pf=mi.get("pf"), oos_wr=mo.get("win_rate"), oos_pf=mo.get("pf"),
                         cagr=cs["cagr"], dd=cs["max_dd"], mar=cs["mar"], yearly=cs["yearly"], trades=t)
    return out


def grid(base, space, pool, stress=False, risk=0.01, max_open=10):
    rows = []
    keys = list(space)
    for vals in itertools.product(*[space[k] for k in keys]):
        p = dict(base); p.update(dict(zip(keys, vals)))
        r = evaluate(p, pool, risk, max_open, stress)
        a = r["ana"]
        if a is None:
            continue
        row = {k: str(v) for k, v in zip(keys, vals)}
        row.update({k: a[k] for k in ("n", "wr", "pf", "is_wr", "is_pf", "oos_wr", "oos_pf", "avgR", "cagr", "dd", "mar")})
        if stress and r.get("stres"):
            s = r["stres"]; row.update(s_wr=s["wr"], s_pf=s["pf"], s_mar=s["mar"])
        rows.append(row)
    return pd.DataFrame(rows)
