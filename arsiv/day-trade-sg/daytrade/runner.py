"""Strateji çalıştırma, eğitim/test ayrımı ve raporlama yardımcıları."""
from __future__ import annotations

import itertools
import json
from functools import lru_cache

import numpy as np
import pandas as pd

from . import data as D
from .backtest import metrics, simulate
from .features import build
from .strategies import STRATEGIES
from .universe import Instrument, build_universe


@lru_cache(maxsize=256)
def bundle(inst: Instrument, entry_tf: str) -> pd.DataFrame | None:
    e, h1, h4 = D.load(inst, entry_tf), D.load(inst, "1h"), D.load(inst, "4h")
    if e is None or h1 is None or len(e) < 300 or len(h1) < 250:
        return None
    if h4 is None or len(h4) < 210:
        h4 = D.resample(h1, "4h")
    df = build(inst, e, h1, h4, entry_tf)
    return add_market(df, inst, entry_tf)


def add_market(df: pd.DataFrame, inst: Instrument, entry_tf: str) -> pd.DataFrame:
    """Kripto için piyasa (BTC) gün içi hareketi: (BTC kapanış − BTC gün açılışı) / BTC günlük ATR."""
    if inst.asset_class != "crypto":
        return df
    btc = next(i for i in build_universe() if i.symbol == "BTCUSDT")
    b = df if inst.symbol == "BTCUSDT" else bundle(btc, entry_tf)
    if b is None:
        return df
    mv = ((b["close"] - b["dopen"]) / b["atr_d"]).rename("mkt_move")
    df = df.copy()
    df["mkt_move"] = mv.reindex(df.index)
    df["mkt_h4_up"] = (b["h4_ema20"] > b["h4_ema50"]).reindex(df.index)
    df["mkt_h4_dn"] = (b["h4_ema20"] < b["h4_ema50"]).reindex(df.index)
    # Rejim (Lien "büyük resim"): BTC günlük kapanışı SMA(n) üstünde mi? Dünkü kapanışla bilinir.
    # Kesintisiz uzun seri için BTC_GUNLUK=<günlük kapanış pickle> verilebilir; yoksa 1s veriden.
    import os
    gp = os.environ.get("BTC_GUNLUK")
    dc = pd.read_pickle(gp) if gp else b["close"].resample("1D").last().dropna()
    if dc.index.tz is None:
        dc.index = dc.index.tz_localize("UTC")
    gun = df.index.floor("D")
    for n in (100, 200):
        sma = dc.rolling(n).mean()
        ok = (dc > sma).where(sma.notna()).shift(1)   # NaN: SMA henüz yok
        df[f"mkt_d_ok{n}"] = ok.reindex(gun).to_numpy()
    return df


def run(strategy: str, params: dict, insts: list[Instrument], entry_tf: str) -> pd.DataFrame:
    fn, _ = STRATEGIES[strategy]
    out = []
    for inst in insts:
        df = bundle(inst, entry_tf)
        if df is None:
            continue
        sig = fn(df, **params)
        tr = simulate(df, sig, inst.cost_pct, inst.symbol, strategy)
        tr["asset_class"] = inst.asset_class
        # eğitim/test ayrımı: sembolün veri aralığının ilk %70'i eğitim
        cut = df.index[0] + (df.index[-1] - df.index[0]) * 0.7
        tr["split"] = np.where(tr["entry_time"] < cut, "train", "test")
        out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def summarize(tr: pd.DataFrame, by=("split",)) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    rows = []
    for key, g in tr.groupby(list(by)):
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(by, key)), **metrics(g)})
    rows.append({**{b: "ALL" for b in by}, **metrics(tr)})
    return pd.DataFrame(rows)


def score(m: dict, min_trades: int = 30, min_wr: float = 0.45) -> float:
    """Optimizasyon skoru: kazanma oranı şartı + beklenti·√işlem (istatistiksel güven)."""
    if m["trades"] < min_trades or not np.isfinite(m["exp_R"]):
        return -np.inf
    pen = 0.0 if m["win_rate"] >= min_wr else (min_wr - m["win_rate"]) * 10
    return m["exp_R"] * np.sqrt(m["trades"]) - pen


def grid(space: dict):
    keys = list(space)
    for vals in itertools.product(*(space[k] for k in keys)):
        yield dict(zip(keys, vals))


def universe_with_data(entry_tf: str) -> list[Instrument]:
    return [i for i in build_universe() if D.load(i, entry_tf) is not None]


def to_json(obj) -> str:
    def conv(o):
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, np.integer):
            return int(o)
        return str(o)
    return json.dumps(obj, default=conv, ensure_ascii=False, indent=2)
