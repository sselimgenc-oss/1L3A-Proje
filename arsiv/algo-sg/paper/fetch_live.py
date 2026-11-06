"""Canlı veri çekici (GitHub Actions'ta çalışır).

- Mumlar: Binance SPOT 1h (data-api.binance.vision). Binance vadeli API'si ABD sunucularını
  engellediği (HTTP 451) için spot kullanılır; fiyat farkı ~%0.01-0.05.
- Hacim: spot hacmi, vadeli geçmişle çakışan dönemden hesaplanan sabit katsayıyla vadeli
  ölçeğine çevrilir (yalnızca ilk ~3 günü etkiler; sonrasında hacim oranı aynı kaynaktan hesaplanır).
- Funding: OKX USDT swap funding geçmişi (Binance funding'e çok yakın).
Yalnızca KAPANMIŞ mumlar yazılır.
"""
import csv
import json
import os
import sys
import time
import datetime as dt
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.environ.get("ALGO_LIVE") or os.path.join(ROOT, "paper", "live")
CFG = json.load(open(os.path.join(ROOT, "paper", "config.json")))
H = 3600_000


def http_json(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "algo-sg-paper/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def symbols():
    d = os.path.join(ROOT, "data", "1h")
    return sorted(f[:-7] for f in os.listdir(d) if f.endswith(".csv.gz"))


def last_ts(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = f.read().strip().splitlines()
    return int(rows[-1].split(",")[0]) if len(rows) > 1 else None


def fetch_klines(sym, now_ms):
    path = os.path.join(LIVE, "klines", f"{sym}.csv")
    start = last_ts(path)
    start = start + H if start is not None else int(dt.datetime.fromisoformat(CFG["overlap_start"].replace("Z", "+00:00")).timestamp() * 1000)
    rows = []
    while start + H <= now_ms:  # yalnızca kapanmış mumlar
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&startTime={start}&limit=1000"
        data = http_json(url)
        if not data:
            break
        for k in data:
            if int(k[0]) + H <= now_ms:
                rows.append([int(k[0]), k[1], k[2], k[3], k[4], k[5], k[7]])
        nxt = int(data[-1][0]) + H
        if nxt <= start:
            break
        start = nxt
        if len(data) < 1000:
            break
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "open", "high", "low", "close", "volume", "quote_volume"])
        w.writerows(rows)
    return len(rows)


def fetch_funding(sym):
    path = os.path.join(LIVE, "funding", f"{sym}.csv")
    inst = sym.replace("USDT", "") + "-USDT-SWAP"
    have = set()
    if os.path.exists(path):
        with open(path) as f:
            have = {int(r.split(",")[0]) for r in f.read().strip().splitlines()[1:]}
    try:
        data = http_json(f"https://www.okx.com/api/v5/public/funding-rate-history?instId={inst}&limit=100").get("data", [])
    except Exception:
        return 0
    rows = sorted((int(d["fundingTime"]), d["realizedRate"] or d["fundingRate"]) for d in data)
    rows = [r for r in rows if r[0] not in have]
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "funding_rate"])
        w.writerows(rows)
    return len(rows)


def volume_scale():
    """Vadeli/spot hacim katsayısı: çakışma dönemindeki medyan oran (bir kez hesaplanır)."""
    import gzip
    path = os.path.join(LIVE, "volume_scale.json")
    if os.path.exists(path):
        return json.load(open(path))
    scale = {}
    for sym in symbols():
        with gzip.open(os.path.join(ROOT, "data", "1h", f"{sym}.csv.gz"), "rt") as f:
            perp = {int(r[0]): float(r[6]) for r in csv.reader(f) if r and r[0].isdigit()}
        lp = os.path.join(LIVE, "klines", f"{sym}.csv")
        if not os.path.exists(lp):
            continue
        with open(lp) as f:
            spot = {int(r[0]): float(r[6]) for r in csv.reader(f) if r and r[0].isdigit()}
        ratios = sorted(perp[t] / spot[t] for t in perp.keys() & spot.keys() if spot[t] > 0)
        scale[sym] = ratios[len(ratios) // 2] if ratios else 1.0
    json.dump(scale, open(path, "w"), indent=1)
    return scale


if __name__ == "__main__":
    os.makedirs(os.path.join(LIVE, "klines"), exist_ok=True)
    os.makedirs(os.path.join(LIVE, "funding"), exist_ok=True)
    now_ms = int(time.time() * 1000)
    tot = 0
    for s in symbols():
        try:
            n = fetch_klines(s, now_ms); fn = fetch_funding(s); tot += n
            print(f"{s}: +{n} mum, +{fn} funding")
        except Exception as e:
            print(f"{s}: HATA {e}", file=sys.stderr)
    volume_scale()
    print("toplam yeni mum:", tot)
