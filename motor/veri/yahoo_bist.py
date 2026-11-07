"""Yahoo Finance (query1.finance.yahoo.com chart API) üzerinden BIST hisseleri ve XU030 endeksi.

Semboller depoda `BIST_<TICKER>` ve `BIST_XU030` adıyla durur (Yahoo: <TICKER>.IS, XU030.IS). Kolonlar depo sözleşmesi:
acilis/yuksek/dusuk/kapanis/hacim/quote_hacim/islem_sayisi, UTC açılış zamanı indeksi. quote_hacim = hacim*kapanis
(yaklaşık, TL), islem_sayisi = 0 (Yahoo vermez). 1d mumları UTC gün başına (00:00) yazılır; Borsa İstanbul seansı
10:00-18:00 TSİ = 07:00-15:00 UTC olduğundan UTC günü = seans günü.

Yahoo sınırları (ücretsiz): 1d = tüm geçmiş; 1h = ~730 gün; 30m/15m/5m = son ~60 gün. Dar pencereli aralıklar her çalıştırmada
mevcut dosyayla BİRLEŞTİRİLİR (yeni mumlar eklenir), böylece düzenli çalıştırma geçmişi uzatır; uydurma/uzatma yok.

Bölünme/bedelsiz: Yahoo OHLC'si bölünme (bedelsiz sermaye artırımı dahil) düzeltmelidir (temettü düzeltmesi YAPILMAZ).
Gün içi (1h/5m) serilerin düzeltilmiş olup olmadığı belli olmadığından, her bölünme tarihinde günlük seriyle uyum kontrol
edilir (`gunluk_uyum`) ve gerekirse günlük orana göre ölçeklenir.

CLI: python -m motor.veri.yahoo_bist [--semboller AKBNK THYAO XU030] [--aralik 1d 1h 5m 15m 30m]
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import pandas as pd
import requests

from motor.veri.depo import MUM_DIZINI, MUM_SUTUNLARI, mum_yolu
from motor.veri.indir import _yaz

HISSELER = ("AKBNK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "EREGL", "FROTO", "KCHOL", "SISE", "TCELL", "THYAO", "TRALT",
            "TUPRS")
YAHOO_ADI = {f"BIST_{t}": f"{t}.IS" for t in HISSELER} | {"BIST_XU030": "XU030.IS"}
TABAN = "https://query1.finance.yahoo.com/v8/finance/chart/"
# aralik -> Yahoo range parametresi
PENCERE = {"1d": "max", "1h": "730d", "30m": "60d", "15m": "60d", "5m": "60d"}


def _getir(yahoo_ad: str, aralik: str, deneme: int = 6) -> dict:
    url = f"{TABAN}{yahoo_ad}"
    par = {"interval": "60m" if aralik == "1h" else aralik, "events": "split", "includePrePost": "false"}
    if aralik == "1d":   # range=max Yahoo'da seyrek (aylık) veri verir; açık period1/period2 günlük tam geçmişi verir
        par.update(period1=0, period2=int(time.time()) + 86400)
    else:
        par["range"] = PENCERE[aralik]
    son = ""
    for d in range(deneme):
        try:
            r = requests.get(url, params=par, headers={"User-Agent": "Mozilla/5.0"}, timeout=40)
            if r.status_code == 200:
                sonuc = r.json()["chart"]["result"]
                if sonuc:
                    return sonuc[0]
                son = "boş sonuç"
            else:
                son = f"HTTP {r.status_code}"
                if r.status_code == 404:
                    break
        except requests.RequestException as e:
            son = type(e).__name__
        time.sleep(min(2 ** d, 30))
    raise RuntimeError(f"{yahoo_ad} {aralik}: {son}")


def ayristir(sonuc: dict, aralik: str) -> tuple[pd.DataFrame, list[tuple[str, float]]]:
    """Yahoo chart sonucu -> (sözleşme tablosu, bölünmeler [(YYYY-MM-DD, oran)])."""
    zaman = sonuc.get("timestamp") or []
    q = sonuc["indicators"]["quote"][0]
    df = pd.DataFrame({"acilis": q["open"], "yuksek": q["high"], "dusuk": q["low"], "kapanis": q["close"],
                       "hacim": q["volume"]}, dtype="float64")
    df.index = pd.DatetimeIndex(pd.to_datetime(zaman, unit="s", utc=True), name="zaman")
    df = df.dropna(subset=["acilis", "yuksek", "dusuk", "kapanis"])
    df["hacim"] = df["hacim"].fillna(0.0)
    if aralik == "1d":        # Yahoo günlük zaman damgası seans açılışı (07:00 UTC) -> UTC gün başı
        df.index = df.index.normalize()
        df.index.name = "zaman"
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if aralik == "1d":
        df = bozuk_oncesini_at(df)
    else:   # açılış/kapanış seansı (müzayede) düz mumları: O=H=L=C ve hacim 0 -> at (Dukascopy'deki düz dolgu mumu kuralı)
        df = df[~((df["hacim"] == 0) & (df["acilis"] == df["yuksek"]) & (df["yuksek"] == df["dusuk"])
                  & (df["dusuk"] == df["kapanis"]))]
    df["quote_hacim"] = df["hacim"] * df["kapanis"]
    df["islem_sayisi"] = np.int64(0)
    bol = []
    for e in (sonuc.get("events", {}).get("splits", {}) or {}).values():
        bol.append((pd.Timestamp(e["date"], unit="s", tz="UTC").strftime("%Y-%m-%d"),
                    float(e["numerator"]) / float(e["denominator"])))
    return df[MUM_SUTUNLARI].astype({"islem_sayisi": "int64"}), sorted(bol)


def bozuk_oncesini_at(df: pd.DataFrame, oran: float = 5.0) -> pd.DataFrame:
    """Eski Yahoo günlük verisinde düzeltilmemiş bölünme/YTL-TL yeniden değerlemesi sıçramaları var (ör. THYAO 2005-01-03
    kapanış x981; BIST günlük fiyat sınırı %10 olduğundan gerçek bir günde 5x hareket olamaz). Son böyle sıçramadan
    ÖNCEKİ satırlar atılır (sıçrama günü ve sonrası kalır)."""
    r = df["kapanis"] / df["kapanis"].shift()
    kotu = r[(r > oran) | (r < 1 / oran)]
    return df[df.index >= kotu.index[-1]] if len(kotu) else df


def gunluk_uyum(gun_ici: pd.DataFrame, gunluk: pd.DataFrame, bolunmeler) -> pd.DataFrame:
    """Gün içi seriyi günlük (Yahoo bölünme-düzeltmeli) seriyle hizalar: her gün için gün içi son kapanış / günlük kapanış
    oranı ~1 ise dokunmaz; bir bölünmeden sonra oran bölünme katsayısına yakınsa o güne kadarki mumlar ölçeklenir.
    Basit ve güvenli: gün başına oran medyanı 1'den %20 fazla sapıyorsa o günün mumları günlük kapanışa oranla ölçeklenir."""
    if gun_ici.empty or gunluk.empty:
        return gun_ici
    gi = gun_ici.copy()
    gun = gi.index.normalize()
    son_kapanis = gi["kapanis"].groupby(gun).last()
    gk = gunluk["kapanis"].reindex(son_kapanis.index)
    oran = (gk / son_kapanis).dropna()
    sapan = oran[(oran > 1.2) | (oran < 1 / 1.2)]
    if sapan.empty:
        return gi
    for g, o in sapan.items():
        m = gun == g
        for c in ("acilis", "yuksek", "dusuk", "kapanis"):
            gi.loc[m, c] = gi.loc[m, c] * o
    return gi


def birlestir(mevcut: pd.DataFrame | None, yeni: pd.DataFrame) -> pd.DataFrame:
    if mevcut is None or mevcut.empty:
        return yeni
    t = pd.concat([mevcut, yeni])
    return t[~t.index.duplicated(keep="last")].sort_index()


def sembol_indir(sembol: str, aralik: str, dizin=None, gunluk: pd.DataFrame | None = None) -> pd.DataFrame:
    dizin = dizin or MUM_DIZINI
    df, bol = ayristir(_getir(YAHOO_ADI[sembol], aralik), aralik)
    if aralik != "1d" and gunluk is not None:
        df = gunluk_uyum(df, gunluk, bol)
    yol = mum_yolu(sembol, aralik, dizin)
    mevcut = pd.read_parquet(yol) if yol.exists() else None
    t = birlestir(mevcut, df)
    _yaz(t, yol)
    return t


def main(argv=None):
    p = argparse.ArgumentParser(description="Yahoo'dan BIST hisse/XU030 mumları")
    p.add_argument("--semboller", nargs="+", default=list(HISSELER) + ["XU030"], help="BIST_ öneksiz: AKBNK ... XU030")
    p.add_argument("--aralik", nargs="+", default=["1d", "1h"], choices=list(PENCERE))
    a = p.parse_args(argv)
    for s in a.semboller:
        sm = s if s.startswith("BIST_") else f"BIST_{s}"
        gunluk = None
        for ar in sorted(a.aralik, key=lambda x: x != "1d"):    # 1d önce (gün içi uyum kontrolü için)
            t = sembol_indir(sm, ar, gunluk=gunluk)
            if ar == "1d":
                gunluk = t
            print(f"{sm} {ar}: {t.index[0]} -> {t.index[-1]}, {len(t)} mum", flush=True)


if __name__ == "__main__":
    sys.exit(main())
