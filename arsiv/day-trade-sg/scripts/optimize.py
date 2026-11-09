"""Koordinat-iniş optimizasyonu (yalnızca kitaplarda geçen parametre değerleriyle).

Her strateji ve giriş zaman dilimi için: varsayılan parametrelerden başla, her
parametreyi tek tek değiştirip EĞİTİM döneminde skoru en iyi değeri seç (2 tur).
Karar ve rapor TEST dönemine göre de verilir (aşırı uydurma kontrolü).

Kullanım: python scripts/optimize.py [--tfs 15m 5m] [--strategies S1_pullback ...]
Çıktı: results/opt_<strateji>_<tf>.json ve results/ozet.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daytrade.backtest import metrics  # noqa: E402
from daytrade.runner import run, score, summarize, to_json, universe_with_data  # noqa: E402
from daytrade.strategies import STRATEGIES  # noqa: E402

SPACES = {
    "S1_pullback": {
        "trend": ["h4+h1", "h4_200+h1", "strict"],
        "trigger": ["stoch", "rsi", "either", "both"],
        "touch_atr": [0.0, 0.25, 0.5],
        "pb_lookback": [2, 3, 5],
        "target_R": [1.5, 2.0, 3.0],
        "ema_exit": [True, False],
        "partial_R": [1.0, None],
        "ltf_align": [True, False],
    },
    "S2_momentum": {
        "trend": ["h4+h1", "h4_200+h1", "strict", "h1"],
        "h1_macd": [True, False],
        "confirm": ["macd", "mom", "either", "both"],
        "macd_bars": [3, 5, 8],
        "setup_lb": [5, 10, 20],
        "target_R": [None, 2.0, 3.0],
        "trail_atr": [0.0, 0.25, 0.5],
        "partial_R": [1.0, None],
    },
    "S3_orb": {
        "trend": ["h1", "h4+h1", "h4_200+h1"],
        "pivot_filter": [True, False],
        "cpr_narrow": [False, True],
        "width_max": [0.5, 0.8, 1.2],
        "vwap": [True, False],
        "volume": [True, False],
        "stop_mode": ["mid", "opposite"],
        "target_R": [1.5, 2.0, 3.0],
        "partial_R": [1.0, None],
        "window_min": [120, 240, 480],
    },
}


def md_table(df):
    if df.empty:
        return ""
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def evaluate(strategy, params, insts, tf):
    tr = run(strategy, params, insts, tf)
    if tr.empty:
        return tr, metrics(None), metrics(None)
    return tr, metrics(tr[tr.split == "train"]), metrics(tr[tr.split == "test"])


def optimize(strategy, insts, tf, passes=2, log=print):
    best = dict(STRATEGIES[strategy][1])
    _, mtr, _ = evaluate(strategy, best, insts, tf)
    best_s = score(mtr)
    for _ in range(passes):
        improved = False
        for k, vals in SPACES[strategy].items():
            for v in vals:
                if best.get(k) == v:
                    continue
                cand = {**best, k: v}
                _, m, _ = evaluate(strategy, cand, insts, tf)
                s = score(m)
                if s > best_s + 1e-9:
                    best, best_s, improved = cand, s, True
                    log(f"  {strategy} {tf} {k}={v}: skor {s:.3f} "
                        f"(n={m['trades']}, WR={m['win_rate']:.3f}, PF={m['pf']:.2f}, "
                        f"E={m['exp_R']:.3f}R)")
        if not improved:
            break
    return best, best_s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tfs", nargs="+", default=["15m", "5m"])
    ap.add_argument("--strategies", nargs="+", default=list(STRATEGIES))
    ap.add_argument("--passes", type=int, default=2)
    a = ap.parse_args()
    Path("results").mkdir(exist_ok=True)
    lines = ["# Optimizasyon özeti", ""]
    for tf in a.tfs:
        insts = universe_with_data(tf)
        print(f"== {tf}: {len(insts)} enstrüman")
        for st in a.strategies:
            params, s = optimize(st, insts, tf, a.passes)
            tr, mtr, mte = evaluate(st, params, insts, tf)
            by_cls = summarize(tr, by=("asset_class", "split"))
            out = dict(strategy=st, tf=tf, params=params, score=s, train=mtr, test=mte,
                       by_class=by_cls.to_dict("records"))
            Path(f"results/opt_{st}_{tf}.json").write_text(to_json(out))
            tr.to_csv(f"results/trades_{st}_{tf}.csv.gz", index=False)
            lines += [f"## {st} — {tf}", "", f"Parametreler: `{params}`", "",
                      "| Dönem | İşlem | Kazanma | PF | Beklenti (R) | Toplam R | MaxDD (R) |",
                      "|---|---|---|---|---|---|---|"]
            for name, m in (("Eğitim", mtr), ("Test", mte)):
                lines.append(f"| {name} | {m['trades']} | {m['win_rate']:.1%} | {m['pf']:.2f} | "
                             f"{m['exp_R']:.3f} | {m['total_R']:.1f} | {m['max_dd_R']:.1f} |")
            lines += ["", md_table(by_cls.round(3)), ""]
            print("\n".join(lines[-12:]))
    Path("results/ozet.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
