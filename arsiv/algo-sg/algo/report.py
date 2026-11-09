"""Nihai sistemi yeniden üretir: python -m algo.report [etiket]
Ortam değişkeni ALGO_DATA ile başka bir veri evreni (ör. data_extra) seçilebilir.
Çıktılar: results/{etiket}_summary.json, {etiket}_trades_{A,B}.csv, {etiket}_equity.png"""
import json
import os
import sys
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from . import backtest as B
from . import data as D, features as F
from .run import run, IS_END
from .portfolio import simulate_portfolio, curve_stats, mtm_drawdown
from .final import MODULES, SLEEVES

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def yearly_table(t):
    return {int(y): dict(n=int(len(x)), win_rate=round(float((x.R > 0).mean() * 100), 1),
                         pf=round(float(x.R[x.R > 0].sum() / max(-x.R[x.R < 0].sum(), 1e-9)), 2),
                         avg_R=round(float(x.R.mean()), 3))
            for y, x in t.groupby(t.entry_time.dt.year)}


def mtm_stats(eq):
    d = eq.resample("1D").last().ffill()
    r = d.pct_change().dropna()
    yrs = (d.index[-1] - d.index[0]).days / 365.25
    cagr = d.iloc[-1] ** (1 / yrs) - 1 if d.iloc[-1] > 0 else -1
    dd = (eq / eq.cummax() - 1).min()
    return dict(ann_return_simple=round(float(cagr) * 100, 1), mtm_max_dd=round(float(dd) * 100, 1),
                sharpe=round(float(r.mean() / r.std() * np.sqrt(365)), 2), mar=round(float(cagr / abs(dd)), 2))


def main(tag="final"):
    os.makedirs(OUT, exist_ok=True)
    closes = {s: F.build(s)["close"] for s in D.symbols()}
    summary, eqs = {}, {}
    with ProcessPoolExecutor(4) as pool:
        mod_trades = {m: run(fn, p, pool=pool).assign(module=m) for m, (fn, p) in MODULES.items()}
    for name, sl in SLEEVES.items():
        t = pd.concat([mod_trades[m] for m in sl["modules"]], ignore_index=True)
        c, taken = simulate_portfolio(t, risk=sl["risk"], max_open=sl["max_open"])  # coin başına tek pozisyon
        taken.to_csv(os.path.join(OUT, f"{tag}_trades_{name}.csv"), index=False)
        dd, eq = mtm_drawdown(taken, sl["risk"], closes)
        eqs[name] = eq
        summary[name] = dict(
            trade_level={"ALL": B.metrics(taken, sl["risk"]), "IS": B.metrics(taken, sl["risk"], end=IS_END),
                         "OOS": B.metrics(taken, sl["risk"], start=IS_END)},
            modules={m: int((taken.module == m).sum()) for m in sl["modules"]},
            portfolio_realized_compounded=curve_stats(c), portfolio_mtm_simple=mtm_stats(eq),
            sleeve=dict(risk=sl["risk"], max_open=sl["max_open"]), yearly=yearly_table(taken),
            symbols_profitable=int((taken.groupby("sym").R.sum() > 0).sum()), symbols=int(taken.sym.nunique()))
    X = pd.DataFrame(eqs).ffill().fillna(1.0)
    comb = (1 + X.pct_change().fillna(0).mean(axis=1)).cumprod()
    summary["COMBINED_equal_weight_mtm"] = mtm_stats(comb)
    summary["COMBINED_yearly_pct"] = {str(k.year): round(float(v) * 100, 1) for k, v in
                                      comb.resample("YE").last().pct_change().fillna(comb.resample("YE").last().iloc[0] - 1).items()}
    summary["daily_corr_mtm"] = X.resample("1D").last().pct_change().corr().round(2).to_dict()
    with open(os.path.join(OUT, f"{tag}_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=float)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        for k, v in X.items():
            ax.plot(v.index, v.values, label=f"Strateji {k}", lw=1.2)
        ax.plot(comb.index, comb.values, label="A+B eşit ağırlık", lw=2, color="black")
        ax.axvline(pd.Timestamp(IS_END, tz="UTC"), ls="--", color="gray")
        ax.set_title("Öz sermaye — açık pozisyonlar dahil (MTM), sabit risk, başlangıç 1.0")
        ax.legend(); ax.grid(alpha=.3); fig.tight_layout()
        fig.savefig(os.path.join(OUT, f"{tag}_equity.png"), dpi=110)
    except Exception as e:
        print("grafik atlandı:", e)
    print(json.dumps({k: (v if k.startswith("COMB") or k == "daily_corr_mtm" else
                          {kk: v[kk] for kk in ("trade_level", "modules", "portfolio_mtm_simple")}) for k, v in summary.items()},
                     indent=1, default=float))
    return summary


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "final")
