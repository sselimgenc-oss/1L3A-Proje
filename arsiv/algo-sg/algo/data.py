"""Veri yükleme ve çoklu zaman dilimi hizalama.

1h mumlar Binance USDT-M perpetual verisidir. 4h ve 1d mumlar 1h'den
yeniden örneklenir. Üst zaman dilimi değerleri 1h mumuna yalnızca o üst
mum KAPANDIKTAN sonra aktarılır (ileriye bakma yanlılığı yok).
"""
import os
import numpy as np
import pandas as pd

ROOT = os.environ.get("ALGO_DATA") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def symbols():
    d = os.path.join(ROOT, "1h")
    return sorted(f[:-7] for f in os.listdir(d) if f.endswith(".csv.gz"))


LIVE = os.environ.get("ALGO_LIVE")  # kağıt işlem modu: paper/live klasörü


def _append_live(df, sym):
    """Canlı (spot) mumları vadeli geçmişin sonuna ekler; hacim vadeli ölçeğine çevrilir."""
    p = os.path.join(LIVE, "klines", f"{sym}.csv")
    if not os.path.exists(p):
        return df
    lv = pd.read_csv(p)
    if lv.empty:
        return df
    sc_path = os.path.join(LIVE, "volume_scale.json")
    scale = 1.0
    if os.path.exists(sc_path):
        import json
        scale = json.load(open(sc_path)).get(sym, 1.0)
    lv = lv[lv["ts"] > df["ts"].max()].copy()
    lv["volume"] *= scale; lv["quote_volume"] *= scale
    lv["trades"] = 0; lv["taker_buy_base"] = 0
    return pd.concat([df, lv[df.columns]], ignore_index=True)


def load_1h(sym):
    df = pd.read_csv(os.path.join(ROOT, "1h", f"{sym}.csv.gz"))
    if LIVE:
        df = _append_live(df, sym)
    df.index = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df[~df.index.duplicated()].sort_index()
    # eksik saatleri doldur (borsa kesintileri): önceki kapanışla düz mum
    full = pd.date_range(df.index[0], df.index[-1], freq="1h")
    df = df.reindex(full)
    df["close"] = df["close"].ffill()
    for c in ("open", "high", "low"):
        df[c] = df[c].fillna(df["close"])
    df[["volume", "quote_volume", "trades", "taker_buy_base"]] = df[["volume", "quote_volume", "trades", "taker_buy_base"]].fillna(0)
    return df[["open", "high", "low", "close", "volume", "quote_volume"]].astype(float)


def load_funding(sym):
    p = os.path.join(ROOT, "funding", f"{sym}.csv.gz")
    if not os.path.exists(p):
        return None
    f = pd.read_csv(p)
    if f.empty:
        return None
    if LIVE and os.path.exists(os.path.join(LIVE, "funding", f"{sym}.csv")):
        lf = pd.read_csv(os.path.join(LIVE, "funding", f"{sym}.csv"))
        f = pd.concat([f, lf[lf["ts"] > f["ts"].max()]], ignore_index=True)
    f.index = pd.to_datetime(f["ts"], unit="ms", utc=True).dt.floor("1h")
    return f["funding_rate"].groupby(level=0).sum()


def resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "quote_volume": "sum"}
    return df.resample(rule, label="left", closed="left").agg(agg).dropna()


def to_1h(htf_series, rule, index_1h):
    """Üst zaman dilimi serisini 1h indeksine hizala.

    htf_series: üst mumun AÇILIŞ zamanıyla indekslenmiş değerler.
    Değer, üst mumun kapanış zamanında bilinir. 1h mumu (açılış t) t+1h'de
    kapanır; o anda kapanmış tüm üst mumların değeri kullanılabilir.
    """
    close_time = htf_series.index + pd.Timedelta(rule)
    s = pd.Series(htf_series.values, index=close_time)
    s = s[~s.index.duplicated(keep="last")]
    known_at = index_1h + pd.Timedelta("1h")
    return s.reindex(known_at, method="ffill").values


def funding_1h(sym, index_1h):
    f = load_funding(sym)
    if f is None:
        return np.zeros(len(index_1h))
    return f.reindex(index_1h).fillna(0).values
