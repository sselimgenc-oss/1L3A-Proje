"""Doküman tabanlı parametre ızgarası üzerinde optimizasyon (örneklem içi seçim, örneklem dışı test).

Seçim kuralı (yalnızca IS verisiyle): kazanma ≥ %45, PF ≥ 1.3, n ≥ min_n koşulunu sağlayanlar
arasında toplam R'si en yüksek olan; hiçbiri sağlamıyorsa en yüksek beklentili olan.

    python -m src.optimize --strategy S1 --groups crypto --out sonuclar/opt_S1_crypto.csv
"""
import argparse
import itertools
import json
import os

import pandas as pd

from src import backtest as bt
from src.config import GROUPS
from src.run import run_all

GRIDS = {
    # Ellis (EMA8/34), 5dk scalp (EMA50), Waqar (EMA14/50); Stokastik 5,3,3 / 8,3,3; R/R 1:1–1:2
    "S1": dict(hpair=[(8, 34), (14, 50), (21, 50)], e_fast=[8, 10], st_k=[5, 8], st_lvl=[20, 30],
               rr=[1.0, 1.5, 2.0], be=[0.0, 1.0]),
    # Stevenson/Carson/Ferrazzi: BB 20/40, 2–2.5σ, RSI 5/7, ADX<25, hedef orta bant veya R
    "S2": dict(h_ema=[50, 200], bb_n=[20, 40], bb_k=[2.0, 2.5], rsi_n=[5, 7], adx_max=[0, 25],
               exit=[("mid", 0.0), ("mid", 1.0), ("rr", 1.0), ("rr", 1.5)]),
    # Volman blok kırılımı / Price Action Scalper mum uyumu
    "S3": dict(box=[6, 8, 12], box_atr=[1.0, 1.5, 2.0], need_green=[0, 1], rr=[1.0, 1.5, 2.0], be=[0.0, 1.0]),
}


def expand(strategy):
    g = GRIDS[strategy]
    keys = list(g)
    for vals in itertools.product(*[g[k] for k in keys]):
        p = dict(zip(keys, vals))
        if "hpair" in p:
            p["h_fast"], p["h_slow"] = p.pop("hpair")
        if "exit" in p:
            kind, r = p.pop("exit")
            p["mid_exit"] = 1 if kind == "mid" else 0
            p["rr"] = r
        yield p


def choose(df, min_n):
    ok = df[(df.is_win >= 0.45) & (df.is_pf >= 1.3) & (df.is_n >= min_n)]
    if len(ok):
        return ok.sort_values("is_totR", ascending=False).iloc[0], True
    return df[df.is_n >= min_n].sort_values("is_avgR", ascending=False).iloc[0], False


def optimize(strategy, groups, min_n=100):
    rows = []
    for p in expand(strategy):
        tr = run_all(strategy, p, groups)
        if not len(tr):
            continue
        si, so = bt.stats(tr[~tr.oos]), bt.stats(tr[tr.oos])
        rows.append(dict(params=json.dumps(p), **{f"is_{k}": v for k, v in si.items()},
                         **{f"oos_{k}": v for k, v in so.items()}))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="S1")
    ap.add_argument("--groups", nargs="+", default=list(GROUPS))
    ap.add_argument("--min-n", type=int, default=100)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    df = optimize(a.strategy, a.groups, a.min_n)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        df.to_csv(a.out, index=False)
    best, passed = choose(df, a.min_n)
    pd.set_option("display.width", 250)
    print(df.sort_values("is_totR", ascending=False).head(15).round(3).to_string(index=False))
    print("\nSEÇİLEN (IS kriteri geçti=%s):" % passed)
    print(best.round(3).to_string())


if __name__ == "__main__":
    main()
