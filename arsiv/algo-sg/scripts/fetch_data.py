"""Binance USDT-M perpetual 1h kline + funding verisini data.binance.vision'dan indirir.

Çıktı: data/1h/{SYMBOL}.csv.gz, data/funding/{SYMBOL}.csv.gz
4h ve 1d mumlar backtest sırasında 1h verisinden yeniden örneklenir.
"""
import csv, gzip, io, os, sys, zipfile, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.error

BASE = "https://data.binance.vision/data/futures/um"
SYMBOLS = os.environ.get("SYMBOLS", (
    "BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT AVAXUSDT LINKUSDT DOTUSDT "
    "LTCUSDT TRXUSDT BCHUSDT ATOMUSDT NEARUSDT UNIUSDT ETCUSDT FILUSDT XLMUSDT APTUSDT "
    "ARBUSDT OPUSDT INJUSDT SUIUSDT AAVEUSDT")).split()
START = dt.date(2020, 1, 1)
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"


def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
    return None


def rows_from_zip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            for row in csv.reader(io.TextIOWrapper(z.open(name), "utf-8")):
                if row and row[0][:1].isdigit():
                    yield row


def months(today):
    d = START
    while (d.year, d.month) < (today.year, today.month):
        yield d.strftime("%Y-%m")
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def fetch_symbol(sym):
    today = dt.date.today()
    klines, funding = {}, {}
    for m in months(today):
        blob = get(f"{BASE}/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip")
        if blob:
            for r in rows_from_zip(blob):
                ts = int(r[0]); ts = ts // 1000 if ts > 10**14 else ts
                klines[ts] = [ts] + r[1:6] + [r[7], r[8], r[9]]
        fb = get(f"{BASE}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
        if fb:
            for r in rows_from_zip(fb):
                ts = int(r[0]); ts = ts // 1000 if ts > 10**14 else ts
                funding[ts] = r[2]
    d = today.replace(day=1)
    while d < today:
        blob = get(f"{BASE}/daily/klines/{sym}/1h/{sym}-1h-{d.isoformat()}.zip")
        if blob:
            for r in rows_from_zip(blob):
                ts = int(r[0]); ts = ts // 1000 if ts > 10**14 else ts
                klines[ts] = [ts] + r[1:6] + [r[7], r[8], r[9]]
        d += dt.timedelta(days=1)
    os.makedirs(f"{OUT}/1h", exist_ok=True); os.makedirs(f"{OUT}/funding", exist_ok=True)
    with gzip.open(f"{OUT}/1h/{sym}.csv.gz", "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["ts", "open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_base"])
        for ts in sorted(klines): w.writerow(klines[ts])
    with gzip.open(f"{OUT}/funding/{sym}.csv.gz", "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["ts", "funding_rate"])
        for ts in sorted(funding): w.writerow([ts, funding[ts]])
    return sym, len(klines), len(funding)


if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex:
        for sym, n, nf in ex.map(fetch_symbol, SYMBOLS):
            print(f"{sym}: {n} kline, {nf} funding", flush=True)
