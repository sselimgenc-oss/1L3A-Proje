"""Strateji araştırma tablosu: her strateji × varlık sınıfı × (eğitim/test) için
işlem sayısı, kazanma oranı, PF, net/brüt beklenti (R).

Kullanım:
  python scripts/arastir.py --tf 15m --strategies S1_pullback S6_fader \
      --params '{"S6_fader": {"regime": "range"}}'
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from daytrade.backtest import simulate  # noqa: E402
from daytrade.runner import bundle, universe_with_data  # noqa: E402
from daytrade.strategies import STRATEGIES  # noqa: E402


def islemler(st, params, insts, tf, maliyet=True):
    fn, _ = STRATEGIES[st]
    out = []
    for inst in insts:
        df = bundle(inst, tf)
        if df is None:
            continue
        sig = fn(df, **params)
        cost = inst.cost_pct if maliyet else 0.0
        tr = simulate(df, sig, cost, inst.symbol, st, max_cost_R=0.2 if maliyet else 99)
        if tr.empty:
            continue
        cut = df.index[0] + (df.index[-1] - df.index[0]) * 0.7
        tr["split"] = np.where(tr["entry_time"] < cut, "egitim", "test")
        tr["sinif"] = inst.asset_class
        out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def ozet(tr, by=("sinif", "split")):
    def m(g):
        r = g["R"].to_numpy()
        gl = -r[r <= 0].sum()
        return pd.Series(dict(n=len(r), wr=(r > 0).mean(), pf=r[r > 0].sum() / gl if gl > 0 else np.nan,
                              expR=r.mean(), topR=r.sum()))
    if tr.empty:
        return pd.DataFrame()
    t = tr.groupby(list(by)).apply(m, include_groups=False)
    tot = tr.groupby("split").apply(m, include_groups=False)
    tot.index = pd.MultiIndex.from_tuples([("TUMU", s) for s in tot.index], names=by)
    return pd.concat([t, tot]).round(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m")
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES))
    ap.add_argument("--params", default="{}")
    ap.add_argument("--brut", action="store_true", help="maliyetsiz (brüt) sonucu da göster")
    a = ap.parse_args()
    P = json.loads(a.params)
    insts = universe_with_data(a.tf)
    print(f"{a.tf}: {len(insts)} enstrüman")
    for st in a.strategies:
        tr = islemler(st, P.get(st, {}), insts, a.tf)
        print(f"\n=== {st} {P.get(st, {})} (net)")
        print(ozet(tr).unstack("split").to_string() if not tr.empty else "işlem yok")
        if a.brut:
            g = islemler(st, P.get(st, {}), insts, a.tf, maliyet=False)
            print("--- brüt expR:", ozet(g)["expR"].unstack("split").to_string() if not g.empty else "-")


if __name__ == "__main__":
    main()
