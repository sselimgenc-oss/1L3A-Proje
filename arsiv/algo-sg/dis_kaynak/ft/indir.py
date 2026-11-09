"""GitHub Actions'ta: data.binance.vision'dan USDT-M dakikalık kline + funding indirir, freqtrade futures feather'ına çevirir.
Kullanım: python indir.py <hedef_user_data_dizini>
Evren: 10 büyük coin. 5m: 2022-01..2026-09 (15m/30m/1h/4h/1d bundan üretilir); 1m: 2025-10..2026-09."""
import io, os, sys, zipfile, itertools
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import pandas as pd

COINS = "BTC ETH SOL XRP BNB DOGE ADA AVAX LINK LTC".split()
BASE = "https://data.binance.vision/data/futures/um/monthly"
OUT = os.path.join(sys.argv[1] if len(sys.argv) > 1 else "user_data", "data", "binance", "futures")
os.makedirs(OUT, exist_ok=True)


def aylar(a, b):
    return [p.strftime("%Y-%m") for p in pd.period_range(a, b, freq="M")]


def zip_csv(url, cols):
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
    except Exception as e:
        print("yok", url, type(e).__name__); return None
    raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    df = pd.read_csv(io.StringIO(raw), header=0 if not first[0].isdigit() else None)
    df = df.iloc[:, :len(cols)]; df.columns = cols
    return df


def kline(sym, tf, ay):
    return zip_csv(f"{BASE}/klines/{sym}USDT/{tf}/{sym}USDT-{tf}-{ay}.zip", ["ts", "open", "high", "low", "close", "volume"])


def topla(sym, tf, months):
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(lambda m: kline(sym, tf, m), months) if p is not None]
    d = pd.concat(parts, ignore_index=True)
    d["ts"] = pd.to_numeric(d["ts"]); d.loc[d["ts"] > 10**14, "ts"] //= 1000  # mikrosaniye -> ms
    d = d.drop_duplicates("ts").sort_values("ts")
    d["date"] = pd.to_datetime(d["ts"], unit="ms", utc=True)
    return d.set_index("date")[["open", "high", "low", "close", "volume"]].astype(float)


def yaz(df, pair, tf, kind="futures"):
    o = df.copy(); o.insert(0, "date", o.index); o.reset_index(drop=True).to_feather(f"{OUT}/{pair}-{tf}-{kind}.feather")


def fonlama(sym, months):
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(lambda m: zip_csv(f"{BASE}/fundingRate/{sym}USDT/{sym}USDT-fundingRate-{m}.zip", ["ts", "interval", "rate"]), months) if p is not None]
    if not parts:
        return pd.Series(dtype=float)
    f = pd.concat(parts); f["ts"] = pd.to_numeric(f["ts"]); f.loc[f["ts"] > 10**14, "ts"] //= 1000
    s = pd.Series(pd.to_numeric(f["rate"]).values, index=pd.DatetimeIndex(pd.to_datetime(f["ts"], unit="ms", utc=True)).floor("1h"))
    return s.groupby(level=0).sum()


AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
for sym in COINS:
    pair = f"{sym}_USDT_USDT"
    m5 = topla(sym, "5m", aylar("2022-01", "2026-09"))
    yaz(m5, pair, "5m")
    for tf, rule in (("15m", "15min"), ("30m", "30min"), ("1h", "1h"), ("2h", "2h"), ("4h", "4h"), ("1d", "1D")):
        yaz(m5.resample(rule, label="left", closed="left").agg(AGG).dropna(), pair, tf)
    m1 = topla(sym, "1m", aylar("2025-10", "2026-09"))
    yaz(m1, pair, "1m")
    h1 = m5.resample("1h", label="left", closed="left").agg(AGG).dropna()
    fr = fonlama(sym, aylar("2022-01", "2026-09")).reindex(h1.index).fillna(0.0)
    for tf in ("1h", "8h"):
        r = fr if tf == "1h" else fr.resample("8h", label="left", closed="left").sum()
        mk = h1["close"] if tf == "1h" else h1["close"].resample("8h", label="left", closed="left").first()
        f = pd.DataFrame({"open": r.values, "high": r.values, "low": r.values, "close": r.values, "volume": 0.0}, index=r.index)
        yaz(f, pair, tf, "funding_rate")
        m = pd.DataFrame({"open": mk.values, "high": mk.values, "low": mk.values, "close": mk.values, "volume": 0.0}, index=mk.index)
        yaz(m, pair, tf, "mark")
    print(sym, "5m", len(m5), m5.index[0], m5.index[-1], "| 1m", len(m1), flush=True)
