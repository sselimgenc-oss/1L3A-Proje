"""GitHub Actions'ta: dakikalık (1m/5m/15m/30m) freqtrade stratejilerini kendi zaman dilimlerinde koşturur,
tek özet tablo (CSV + JSON) üretir. Kullanım: python dakika.py <calisma_dizini> <cikti_csv>
Dönemler: 5m/15m/30m 2022-01..2026-09 (IS = 2022-2023, OOS = 2024+, 2022 ayrıca); 1m yalnız 2025-10..2026-09 (OOS)."""
import os, re, sys, json, glob, zipfile, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd

WD = sys.argv[1]; OUTCSV = sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
STRAT = os.path.join(HERE, "strategies")
COINS = "BTC ETH SOL XRP BNB DOGE ADA AVAX LINK LTC".split()
PER_RUN_TIMEOUT = int(os.environ.get("PER_RUN_TIMEOUT", "1800"))
IS_END = pd.Timestamp("2024-01-01", tz="UTC")


def stratejiler():
    out = []
    for f in sorted(glob.glob(os.path.join(STRAT, "*.py"))):
        s = open(f).read()
        m = re.search(r"timeframe\s*=\s*['\"](\d+[mhd])['\"]", s)
        c = re.search(r"^class (\w+)\(.*IStrategy", s, re.M)
        if m and c and m.group(1) in ("1m", "5m", "15m", "30m"):
            out.append((c.group(1), m.group(1)))
    return out


def config():
    c = {"trading_mode": "futures", "margin_mode": "isolated", "max_open_trades": 10, "stake_currency": "USDT", "stake_amount": 990,
         "tradable_balance_ratio": 0.99, "dry_run": True, "dry_run_wallet": 10000, "timeframe": "5m",
         "exchange": {"name": "binance", "key": "", "secret": "", "pair_whitelist": [f"{p}/USDT:USDT" for p in COINS], "pair_blacklist": []},
         "pairlists": [{"method": "StaticPairList"}],
         "entry_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
         "exit_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
         "datadir": os.path.join(WD, "data", "binance"), "user_data_dir": WD, "strategy_path": STRAT, "dataformat_ohlcv": "feather"}
    p = os.path.join(WD, "config.json"); json.dump(c, open(p, "w"), indent=1); return p


def kos(args):
    name, tf, cfg = args
    tr = os.environ.get("TIMERANGE") or ("20251001-20261001" if tf == "1m" else "20220101-20261001")
    d = os.path.join(WD, "res", name); os.makedirs(d, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, "ftrun.py"), "backtesting", "-c", cfg, "-s", name, "--timerange", tr,
           "--fee", "0.0007", "--export", "trades", "--backtest-directory", d, "--cache", "none"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=PER_RUN_TIMEOUT)
        err = "" if r.returncode == 0 else (r.stdout + r.stderr)[-400:]
    except subprocess.TimeoutExpired:
        err = f"zaman aşımı ({PER_RUN_TIMEOUT}s)"
    print("bitti", name, tf, "HATA" if err else "ok", flush=True)
    return name, tf, err


def ozet(g, t, bas=None, bit=None):
    if bas is not None: g = g[g.index >= bas]; t = t[t.index >= bas]
    if bit is not None: g = g[g.index < bit]; t = t[t.index < bit]
    if len(g) < 20: return {}
    eq = g.cumsum(); dd = (eq - eq.cummax()).min()
    k, z = t[t > 0].sum(), -t[t < 0].sum()
    return {"islem": int(len(t)), "wr": 100 * float((t > 0).mean()) if len(t) else np.nan, "pf": float(k / z) if z > 0 else np.nan,
            "yillik": 100 * g.mean() * 365, "sharpe": float(g.mean() / g.std() * np.sqrt(365)) if g.std() > 0 else np.nan, "dd": 100 * dd}


def degerlendir(name, tf, err):
    row = {"strateji": name, "tf": tf, "hata": err[:300] if err else ""}
    z = glob.glob(os.path.join(WD, "res", name, "*.zip"))
    if err or not z:
        return row
    zf = zipfile.ZipFile(sorted(z)[-1])
    n = [x for x in zf.namelist() if x.endswith(".json") and not x.endswith("_config.json")][0]
    t = pd.DataFrame(list(json.load(zf.open(n))["strategy"].values())[0]["trades"])
    if t.empty:
        row["islem"] = 0; return row
    t["close_date"] = pd.to_datetime(t["close_date"], utc=True)
    start = "2025-10-01" if tf == "1m" else "2022-01-01"
    g = (t.set_index("close_date")["profit_abs"] / 10000).resample("1D").sum()
    g = g.reindex(pd.date_range(start, "2026-09-30", freq="1D", tz="UTC")).fillna(0.0)
    pr = t.set_index("close_date")["profit_ratio"].sort_index()
    for per, kw in (("TUM", {}), ("IS", {"bit": IS_END}), ("OOS", {"bas": IS_END}),
                    ("2022", {"bas": pd.Timestamp("2022-01-01", tz="UTC"), "bit": pd.Timestamp("2023-01-01", tz="UTC")})):
        for k, v in ozet(g, pr, **kw).items():
            row[f"{k}_{per}"] = v
    return row


if __name__ == "__main__":
    cfg = config()
    filt = os.environ.get("STRAT_FILTER")  # yerel duman testi için
    parca, sayi = int(os.environ.get("PARCA", "0")), int(os.environ.get("PARCA_SAYI", "1"))
    jobs = [(n, tf, cfg) for i, (n, tf) in enumerate(stratejiler()) if (not filt or n in filt.split(",")) and i % sayi == parca]
    print(len(jobs), "strateji:", [j[:2] for j in jobs], flush=True)
    rows = []
    for j in jobs:
        rows.append(degerlendir(*kos(j)))
        pd.DataFrame(rows).to_csv(OUTCSV, index=False)  # ara kayıt
    df = pd.DataFrame(rows)
    df.to_csv(OUTCSV, index=False)
    df.to_json(OUTCSV.replace(".csv", ".json"), orient="records", indent=1, force_ascii=False)
    print(df.to_string(max_colwidth=40))
