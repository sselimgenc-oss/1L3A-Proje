"""Veri hazırlama: GitHub üzerinde barındırılan kamuya açık veri setlerinden
5dk ve 1s OHLC serileri üretir ve data/ klasörüne parquet/pickle olarak yazar.

Kaynaklar (bu ortamda yalnızca GitHub erişilebilir olduğu için):
  BTC    : github.com/ff137/bitstamp-btcusd-minute-data  (Bitstamp BTC/USD 1dk)
  XAUUSD : github.com/TheSnowGuru/Stocks-Futures-Financial-Time-series-Tick-Bar-Data (Dukascopy)
  UKOIL  : aynı repo, BRENTCMDUSD
  SPX    : aynı repo, USA500IDXUSD
"""
import gzip, sys
from pathlib import Path
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data"
BAS = pd.Timestamp("2020-01-01")
BTC_REPO = Path("/home/user/ff137/bitstamp-btcusd-minute-data/data")
SNOW = Path("/home/user/TheSnowGuru/data")

SNOW_DOSYA = {
    "XAUUSD": "commodities/gold/XAUUSD_{tf}.csv",
    "UKOIL": "commodities/brent/BRENTCMDUSD_{tf}.csv",
    "SPX": "indices/s&p500/USA500IDXUSD_{tf}.csv",
}

AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def btc():
    parcalar = []
    with gzip.open(BTC_REPO / "historical/btcusd_bitstamp_1min_2012-2025.csv.gz", "rt") as f:
        for p in pd.read_csv(f, chunksize=1_000_000):
            p = p[p.timestamp >= BAS.timestamp()]
            if len(p):
                parcalar.append(p)
    parcalar.append(pd.read_csv(BTC_REPO / "updates/btcusd_bitstamp_1min_latest.csv"))
    d = pd.concat(parcalar)
    d["time"] = pd.to_datetime(d.timestamp, unit="s")
    d = d.drop_duplicates("time").set_index("time").sort_index()[list(AGG)]
    # Bitstamp'ta işlem olmayan dakikalar sıfır hacimli sabit bar olarak var; yeniden örnekle
    out = {}
    for tf, kural in (("M5", "5min"), ("H1", "1h")):
        r = d.resample(kural, label="left", closed="left").agg(AGG).dropna()
        out[tf] = r
    return out


def snow(sym):
    out = {}
    for tf in ("M5", "H1"):
        d = pd.read_csv(SNOW / SNOW_DOSYA[sym].format(tf=tf), sep="\t")
        d.columns = [c.lower() for c in d.columns]
        d["time"] = pd.to_datetime(d["time"])
        d = d.set_index("time").sort_index()
        d = d[~d.index.duplicated()]
        out[tf] = d[d.index >= BAS][list(AGG)]
    return out


def main():
    VERI.mkdir(exist_ok=True)
    hepsi = {"BTCUSDT": btc()}
    for s in SNOW_DOSYA:
        hepsi[s] = snow(s)
    for sym, tfs in hepsi.items():
        for tf, d in tfs.items():
            d.to_pickle(VERI / f"{sym}_{tf}.pkl")
            print(f"{sym:8s} {tf}: {len(d):7d} bar  {d.index[0]} -> {d.index[-1]}")


if __name__ == "__main__":
    main()
