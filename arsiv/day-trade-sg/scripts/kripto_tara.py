"""Kripto strateji taraması: parametre ızgarası, eğitim/test, iki maliyet seviyesi.

Her yapılandırma bir kez maliyetsiz simüle edilir; net R iki maliyet seviyesi için
işlem bazında hesaplanır (gidiş-dönüş maliyet = 2·c·giriş/risk). Gidiş-dönüş maliyeti
riskin max_cost_R katını aşan işlemler o maliyet seviyesinde sayılmaz.
Seçim yalnızca EĞİTİM dönemine göre yapılır; test dönemi yalnızca doğrulama içindir.

  python scripts/kripto_tara.py S9_session '{"anchor_utc":[7,8,13.5],"range_h":[1,2]}' --tf 15m
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from daytrade.backtest import simulate  # noqa: E402
from daytrade.runner import bundle, universe_with_data  # noqa: E402
from daytrade.strategies import STRATEGIES  # noqa: E402

MALIYET = {"spot": 0.0008, "vadeli": 0.0005}


def kripto(tf):
    import os
    from daytrade import data as D
    from daytrade.universe import crypto
    out = [i for i in universe_with_data(tf) if i.asset_class == "crypto"]
    # EKSTRA=LUNA,FTT,...: stres testi için evrene ek coinler (veri varsa)
    for s_ in filter(None, os.environ.get("EKSTRA", "").split(",")):
        i = crypto(s_)
        if D.load(i, tf) is not None and i not in out:
            out.append(i)
    return out


def calistir(st, prm, insts, tf):
    fn, _ = STRATEGIES[st]
    out = []
    for inst in insts:
        df = bundle(inst, tf)
        if df is None:
            continue
        tr = simulate(df, fn(df, **prm), 0.0, inst.symbol, st, max_cost_R=99)
        if tr.empty:
            continue
        cut = df.index[0] + (df.index[-1] - df.index[0]) * 0.7
        tr["split"] = np.where(tr["entry_time"] < cut, "eg", "te")
        out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def olc(tr, c, max_cost_R=0.2):
    if tr.empty:
        return {}
    cr = 2 * c * tr["entry"] / tr["risk"]
    ok = cr <= max_cost_R
    res = {}
    for sp in ("eg", "te"):
        m = ok & (tr["split"] == sp)
        r = (tr.loc[m, "R"] - cr[m]).to_numpy()
        g = tr.loc[m, "R"].to_numpy()
        if len(r) == 0:
            res[sp] = dict(n=0)
            continue
        gl = -r[r <= 0].sum()
        res[sp] = dict(n=len(r), wr=(r > 0).mean(), pf=r[r > 0].sum() / gl if gl > 0 else np.inf,
                       exp=r.mean(), brut=g.mean())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("strategy")
    ap.add_argument("grid", nargs="?", default="{}")
    ap.add_argument("--tf", default="15m")
    ap.add_argument("--sabit", default="{}", help="ızgara dışı sabit parametreler")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--min_n", type=int, default=150)
    ap.add_argument("--yon", choices=["both", "long", "short"], default="both",
                    help="yalnız bu yöndeki işlemleri say (tarama amaçlı yaklaşık filtre)")
    a = ap.parse_args()
    grid, sabit = json.loads(a.grid), json.loads(a.sabit)
    insts = kripto(a.tf)
    keys = list(grid)
    rows = []
    for vals in itertools.product(*(grid[k] for k in keys)) if keys else [()]:
        prm = {**sabit, **dict(zip(keys, vals))}
        tr = calistir(a.strategy, prm, insts, a.tf)
        if a.yon != "both" and not tr.empty:
            tr = tr[tr["dir"] == (1 if a.yon == "long" else -1)]
        row = {k: v for k, v in zip(keys, vals)}
        for cn, c in MALIYET.items():
            m = olc(tr, c)
            for sp in ("eg", "te"):
                d = m.get(sp, {})
                for k in ("n", "wr", "pf", "exp", "brut"):
                    if k == "brut" and cn != "spot":
                        continue
                    row[f"{cn}_{sp}_{k}"] = d.get(k, np.nan)
        rows.append(row)
    t = pd.DataFrame(rows)
    t = t[t["vadeli_eg_n"].fillna(0) >= a.min_n] if len(t) else t
    if t.empty:
        print("yeterli işlem yok")
        return
    t = t.sort_values("vadeli_eg_exp", ascending=False)
    cols = keys + ["spot_eg_brut", "spot_te_brut",
                   "vadeli_eg_n", "vadeli_eg_wr", "vadeli_eg_pf", "vadeli_eg_exp",
                   "vadeli_te_n", "vadeli_te_wr", "vadeli_te_pf", "vadeli_te_exp",
                   "spot_te_pf", "spot_te_exp"]
    pd.set_option("display.width", 250)
    print(f"{a.strategy} {a.tf} · {len(insts)} kripto · {len(rows)} yapılandırma · sabit={sabit}")
    print(t[cols].head(a.top).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
