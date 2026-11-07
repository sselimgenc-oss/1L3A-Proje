"""Strateji(ler)i tüm enstrümanlarda çalıştırır, örneklem içi/dışı (IS/OOS) istatistik üretir.

Örnek:
    python -m src.run --strategy S1 --groups crypto mag7 bist commodity
    python -m src.run --strategy S2 --params '{"bb_k": 2.5}'
"""
import argparse
import json
import os

import pandas as pd

from src import backtest as bt
from src.config import COST_PER_SIDE, GROUPS
from src.data import DATA_DIR, load
from src.strategies import STRATEGIES

_CACHE = {}


def get_data(sym):
    if sym not in _CACHE:
        _CACHE[sym] = (load(sym, "5m"), load(sym, "1h"))
    return _CACHE[sym]


def available(groups):
    out = []
    for g in groups:
        for s in GROUPS[g]:
            f = os.path.join(DATA_DIR, "5m", s.replace("=", "_") + ".csv")
            if os.path.exists(f):
                out.append((g, s))
    return out


def run_symbol(strategy, sym, group, params, split=0.7):
    m5, h1 = get_data(sym)
    m, p = STRATEGIES[strategy](m5, h1, params)
    tr = bt.run(m, p, COST_PER_SIDE[group])
    cut = m5["time"].iloc[int(len(m5) * split)]
    if len(tr):
        tr["sym"] = sym
        tr["group"] = group
        tr["oos"] = tr["time"] >= cut
    return tr


def run_all(strategy, params, groups, split=0.7):
    trs = [run_symbol(strategy, s, g, params, split) for g, s in available(groups)]
    trs = [t for t in trs if len(t)]
    return pd.concat(trs, ignore_index=True) if trs else pd.DataFrame()


def summarize(tr, by="group"):
    rows = []
    if not len(tr):
        return pd.DataFrame()
    for seg_name, seg in [("IS", tr[~tr["oos"]]), ("OOS", tr[tr["oos"]]), ("ALL", tr)]:
        rows.append(dict(seg=seg_name, key="TOPLAM", **bt.stats(seg)))
        for k, g in seg.groupby(by):
            rows.append(dict(seg=seg_name, key=k, **bt.stats(g)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="S1")
    ap.add_argument("--groups", nargs="+", default=list(GROUPS))
    ap.add_argument("--params", default="{}")
    ap.add_argument("--by", default="group")
    a = ap.parse_args()
    tr = run_all(a.strategy, json.loads(a.params), a.groups)
    pd.set_option("display.width", 200)
    print(summarize(tr, a.by).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
