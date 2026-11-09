"""Binance USDT-M vadeli kamu verisi indirici (data.binance.vision içeriği, S3 origin üzerinden).

Adımlar:
  python3 -I backtest/kripto_veri.py semboller        # tüm USDT-M semboller (delist dahil)
  python3 -I backtest/kripto_veri.py gunluk           # 1d mumlar -> data/kripto/1d.pkl (evren sıralaması)
  python3 -I backtest/kripto_veri.py saatlik SYM...   # 1h mumlar + fonlama -> data/kripto/1h/SYM.pkl
Bağımsız çalışır (paket importu yok); indirilen dosyalar data/kripto/ altında tutulur.
"""
import io, re, sys, zipfile, time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
import requests

B = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
KOK = Path(__file__).resolve().parent.parent / "data" / "kripto"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
BAS = "2020-01"
OTURUM = requests.Session()


HATALAR = []


def _get(url, deneme=7):
    for i in range(deneme):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404 and i >= 2:   # geçici 404'ler görüldü; 3 denemeden sonra gerçek say
                HATALAR.append(url)
                return None
        except requests.RequestException:
            pass
        time.sleep(min(2 ** i, 30))
    HATALAR.append(url)
    return None


def _dosya(anahtar):
    """S3 nesnesini disk önbelleğiyle getirir (data/kripto/ham/...)."""
    yol = KOK / "ham" / anahtar
    if yol.exists():
        return yol.read_bytes()
    c = _get(f"{B}/{anahtar}")
    if c is not None:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(c)
    return c


def listele(prefix, klasor=True):
    """S3 listesi: klasor=True ise alt klasörler, değilse dosya anahtarları."""
    out, marker = [], ""
    while True:
        x = _get(f"{B}?prefix={prefix}&delimiter=/&marker={marker}")
        if x is None:
            raise RuntimeError(f"liste alınamadı: {prefix}")
        kok = ET.fromstring(x)
        if klasor:
            out += [e.find(NS + "Prefix").text for e in kok.findall(NS + "CommonPrefixes")]
        else:
            out += [e.find(NS + "Key").text for e in kok.findall(NS + "Contents")]
        if kok.find(NS + "IsTruncated").text != "true":
            return out
        marker = kok.findall(NS + "NextMarker")[0].text if kok.findall(NS + "NextMarker") else (out[-1])


def semboller():
    p = listele("data/futures/um/monthly/klines/")
    s = sorted(x.rstrip("/").split("/")[-1] for x in p)
    s = [x for x in s if re.fullmatch(r"[A-Z0-9]+USDT", x)]
    KOK.mkdir(parents=True, exist_ok=True)
    (KOK / "semboller.txt").write_text("\n".join(s))
    print(len(s), "USDT sembol")
    return s


def _zip_csv(icerik):
    z = zipfile.ZipFile(io.BytesIO(icerik))
    ham = z.read(z.namelist()[0]).decode()
    ilk = ham.split("\n", 1)[0]
    if ilk.startswith("open_time") or ilk.startswith("calc_time"):
        return pd.read_csv(io.StringIO(ham))
    return pd.read_csv(io.StringIO(ham), header=None)


KOL = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
       "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def mumlar(sym, aralik):
    anahtar = listele(f"data/futures/um/monthly/klines/{sym}/{aralik}/", klasor=False)
    zipler = [k for k in anahtar if k.endswith(".zip") and k[-11:-4] >= BAS]
    parca = []
    eksik = 0
    for k in zipler:
        c = _dosya(k)
        if c is None:
            eksik += 1
            continue
        d = _zip_csv(c)
        d = d.iloc[:, :12]
        d.columns = KOL
        parca.append(d)
    if eksik:
        print(f"UYARI {sym} {aralik}: {eksik}/{len(zipler)} ay indirilemedi", flush=True)
    if not parca:
        return None
    d = pd.concat(parca)
    d["time"] = pd.to_datetime(pd.to_numeric(d.open_time), unit="ms")
    d = d.drop_duplicates("time").set_index("time").sort_index()
    return d[["open", "high", "low", "close", "volume", "quote_volume", "count"]].astype(float)


def fonlama(sym):
    anahtar = listele(f"data/futures/um/monthly/fundingRate/{sym}/", klasor=False)
    parca = []
    for k in [k for k in anahtar if k.endswith(".zip") and k[-11:-4] >= BAS]:
        c = _dosya(k)
        if c is not None:
            parca.append(_zip_csv(c))
    if not parca:
        return None
    d = pd.concat(parca)
    d.columns = [str(c) for c in d.columns]
    zc = "calc_time" if "calc_time" in d.columns else d.columns[0]
    rc = "last_funding_rate" if "last_funding_rate" in d.columns else d.columns[-1]
    s = pd.Series(pd.to_numeric(d[rc]).values, index=pd.to_datetime(pd.to_numeric(d[zc]), unit="ms"))
    return s[~s.index.duplicated()].sort_index()


def gunluk():
    s = (KOK / "semboller.txt").read_text().split()
    def f(sym):
        try:
            return sym, mumlar(sym, "1d")
        except Exception as e:  # bozuk dosya vb.
            print("hata", sym, e)
            return sym, None
    with ThreadPoolExecutor(6) as ex:
        sonuc = dict(ex.map(f, s))
    d = pd.concat({k: v for k, v in sonuc.items() if v is not None}, names=["sym", "time"])
    d.to_pickle(KOK / "1d.pkl")
    print("indirilemeyen dosya:", len(HATALAR))
    print("1d:", d.index.get_level_values(0).nunique(), "sembol", len(d), "satır")


def saatlik(liste):
    (KOK / "1h").mkdir(parents=True, exist_ok=True)
    def f(sym):
        hedef = KOK / "1h" / f"{sym}.pkl"
        if hedef.exists():
            return sym, "var"
        try:
            d = mumlar(sym, "1h")
            if d is None:
                return sym, "yok"
            fr = fonlama(sym)
            d["funding"] = 0.0
            if fr is not None:
                # fonlama anı saat başına yuvarlanır; o saatin mumuna yazılır
                fr.index = fr.index.round("h")
                fr = fr.groupby(level=0).last()
                d.loc[d.index.intersection(fr.index), "funding"] = fr.reindex(d.index.intersection(fr.index)).values
            d.to_pickle(hedef)
            return sym, len(d)
        except Exception as e:
            return sym, f"hata {e}"
    with ThreadPoolExecutor(6) as ex:
        for sym, r in ex.map(f, liste):
            print(sym, r, flush=True)


if __name__ == "__main__":
    komut = sys.argv[1]
    if komut == "semboller":
        semboller()
    elif komut == "gunluk":
        gunluk()
    elif komut == "saatlik":
        saatlik(sys.argv[2:] if len(sys.argv) > 2 else (KOK / "evren_semboller.txt").read_text().split())
