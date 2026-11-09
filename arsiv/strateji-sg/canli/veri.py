"""Canlı veri: Binance spot (data-api.binance.vision; Binance ana API'si ABD sunucularından 451 verir),
Binance vadeli arşivi (S3, aylık hacim evreni), OKX vadeli fonlama oranları."""
import io, re, time, zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests

SPOT = "https://data-api.binance.vision"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
OKX = "https://www.okx.com"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_OTURUM = requests.Session()


def _get(url, params=None, deneme=5, ham=False):
    for i in range(deneme):
        try:
            r = _OTURUM.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.content if ham else r.json()
            if r.status_code in (400, 404):
                return None
        except (requests.RequestException, ValueError):
            pass
        time.sleep(min(2 ** i, 20))
    return None


# ---------- spot fiyatlar ----------
_SPOT_SEM = None


def spot_semboller():
    global _SPOT_SEM
    if _SPOT_SEM is None:
        info = _get(f"{SPOT}/api/v3/exchangeInfo") or {}
        _SPOT_SEM = {s["symbol"] for s in info.get("symbols", []) if s.get("status") == "TRADING"
                     and s.get("quoteAsset") == "USDT"}
    return _SPOT_SEM


def spot_karsilik(vadeli):
    """Vadeli sembolün spot karşılığı (1000PEPEUSDT -> PEPEUSDT). Yoksa None (yalnız vadelide işlem gören coin)."""
    sp = spot_semboller()
    if vadeli in sp:
        return vadeli
    m = re.fullmatch(r"(1000000|10000|1000|1M)(.+USDT)", vadeli)
    if m and m.group(2) in sp:
        return m.group(2)
    return None


def mumlar(sembol, aralik="1h", gun=150, bitis=None):
    """Kapanmış mumlar (indeks = açılış zamanı, UTC). sembol: spot sembolü."""
    adim = {"1h": 3600, "1d": 86400, "1m": 60}[aralik] * 1000
    simdi = int(time.time() * 1000) if bitis is None else int(pd.Timestamp(bitis).timestamp() * 1000)
    bas = simdi - gun * 86400 * 1000
    satir = []
    while bas < simdi:
        k = _get(f"{SPOT}/api/v3/klines", dict(symbol=sembol, interval=aralik, startTime=bas, limit=1000))
        if not k:
            break
        satir += k
        bas = k[-1][0] + adim
        if len(k) < 1000:
            break
    if not satir:
        return None
    d = pd.DataFrame(satir).iloc[:, [0, 1, 2, 3, 4, 7]].astype(float)
    d.columns = ["t", "open", "high", "low", "close", "quote_volume"]
    d.index = pd.to_datetime(d.t, unit="ms")
    d = d[~d.index.duplicated()].drop(columns="t").sort_index()
    kapanmis = d.index + pd.Timedelta(milliseconds=adim) <= pd.Timestamp(simdi, unit="ms")
    return d[kapanmis]


def dakika_cozum(sembol, saat, giris, tp1):
    """Aynı saatlik mumda 1R kısmi kârdan sonra fiyat başabaşa (giriş) döndü mü? 1 dakikalık spot veriyle.
    True / False; veri yoksa None (çağıran OHLC yolu varsayımına düşer)."""
    bas = int(pd.Timestamp(saat).timestamp() * 1000)
    k = _get(f"{SPOT}/api/v3/klines", dict(symbol=sembol, interval="1m", startTime=bas, endTime=bas + 3600 * 1000 - 1,
                                           limit=60))
    if not k:
        return None
    m = pd.DataFrame(k).iloc[:, 1:5].astype(float).to_numpy()   # o h l c
    i = np.flatnonzero(m[:, 1] >= tp1)
    if len(i) == 0:
        return None
    i = i[0]
    return bool((m[i + 1:, 2] <= giris).any() or (m[i, 2] <= giris and m[i, 3] < m[i, 0]))


# ---------- fonlama (OKX vadeli; Binance vadeli API'sine erişim yok) ----------
def fonlama(vadeli, damga):
    """Verilen fonlama damgasındaki (00/08/16 UTC) oran. OKX'te yoksa varsayılan %0.01."""
    taban = re.sub(r"^(1000000|10000|1000|1M)", "", vadeli)[:-4]
    for inst in (f"{taban}-USDT-SWAP", f"{vadeli[:-4]}-USDT-SWAP"):
        k = _get(f"{OKX}/api/v5/public/funding-rate-history", dict(instId=inst, limit=100))
        if k and k.get("data"):
            hedef = int(pd.Timestamp(damga).timestamp() * 1000)
            for x in k["data"]:
                if abs(int(x["fundingTime"]) - hedef) < 3600 * 1000:
                    return float(x.get("realizedRate") or x["fundingRate"])
            return float(k["data"][0]["fundingRate"])          # en yakın bilinen oran
    return 0.0001


# ---------- aylık evren (Binance vadeli arşivi) ----------
def _liste(prefix):
    out, marker = [], ""
    while True:
        x = _get(S3, dict(prefix=prefix, delimiter="/", marker=marker), ham=True)
        if x is None:
            return out
        kok = ET.fromstring(x)
        out += [e.find(NS + "Prefix").text for e in kok.findall(NS + "CommonPrefixes")]
        if kok.find(NS + "IsTruncated").text != "true":
            return out
        marker = out[-1]


def _aylik_1d(sembol, ay):
    c = _get(f"{S3}/data/futures/um/monthly/klines/{sembol}/1d/{sembol}-1d-{ay}.zip", ham=True)
    if c is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(c)); ham = z.read(z.namelist()[0]).decode()
    d = pd.read_csv(io.StringIO(ham), header=None if not ham.startswith("open_time") else 0)
    return d.iloc[:, 7].astype(float)          # quote_volume


def aylik_evren(ay_bas, haric, n=40, min_gun=90):
    """ay_bas ayı için evren: önceki ayın USDT hacmine göre ilk n vadeli sembol, ay başında >= min_gun geçmiş
    (backtest kripto_evren ile aynı mantık; 30 gün yerine önceki takvim ayı). Arşiv henüz yayımlanmadıysa None."""
    ay_bas = pd.Timestamp(ay_bas)
    ay1, ay2, ay3 = [(ay_bas - pd.DateOffset(months=k)).strftime("%Y-%m") for k in (1, 2, 3)]
    if _aylik_1d("BTCUSDT", ay1) is None:
        return None
    sem = [p.rstrip("/").split("/")[-1] for p in _liste("data/futures/um/monthly/klines/")]
    sem = [s for s in sem if re.fullmatch(r"[A-Z0-9]+USDT", s) and s not in haric]
    with ThreadPoolExecutor(16) as ex:
        hac = dict(zip(sem, ex.map(lambda s: _aylik_1d(s, ay1), sem)))
    hac = {s: v for s, v in hac.items() if v is not None and len(v) > 0}
    aday = sorted(hac, key=lambda s: -hac[s].sum())[:n + 40]
    with ThreadPoolExecutor(16) as ex:
        once = dict(zip(aday, ex.map(lambda s: sum(len(x) for x in (_aylik_1d(s, ay2), _aylik_1d(s, ay3))
                                                    if x is not None), aday)))
    uygun = [s for s in aday if len(hac[s]) + once[s] >= min_gun]
    return uygun[:n]
