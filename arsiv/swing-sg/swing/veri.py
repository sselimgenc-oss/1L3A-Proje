"""Veri yükleme ve haftalık (yön) zaman dilimine dönüştürme."""
import os
import sys

import pandas as pd

KOK = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(KOK, "scripts"))
from varliklar import tum_varliklar  # noqa: E402

RAW = os.path.join(KOK, "data", "raw")
YARDIMCI = os.path.join(KOK, "data", "yardimci")

# BIST fiyatlarının para birimi: "USD" (varsayılan, TL enflasyon etkisini ayıklar) veya "TL"
BIST_PARA = os.environ.get("BIST_PARA", "USD")

# Piyasa rejimi için sınıf başına referans endeks (Ladha: önce genel piyasanın trendine bak)
ENDEKS = {"kripto": ("raw", "BTCUSDT"), "mag7": ("yardimci", "NDX"), "bist": ("yardimci", "XU100"), "emtia": None}

# İşlem başına tek yön maliyet (komisyon + kayma)
MALIYET = {"kripto": 0.0010, "mag7": 0.0005, "bist": 0.0015, "emtia": 0.0005}


def yukle(ad, klasor=RAW):
    df = pd.read_csv(os.path.join(klasor, f"{ad}.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df["High"] >= df["Low"]) & (df["Close"] > 0)]
    return df.astype(float)


def usd_cevir(df):
    kur = yukle("USDTRY", YARDIMCI)["Close"].reindex(df.index, method="ffill")
    du = df.copy()
    for c in ("Open", "High", "Low", "Close"):
        du[c] = df[c] / kur
    return du.dropna()


def tum_veriler(bist_para=None):
    bist_para = bist_para or BIST_PARA
    out = {}
    bugun = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    endeksler = {}
    for sinif, kaynak in ENDEKS.items():
        if kaynak and os.path.exists(os.path.join(KOK, "data", kaynak[0], f"{kaynak[1]}.csv")):
            e = yukle(kaynak[1], os.path.join(KOK, "data", kaynak[0]))
            if sinif == "bist" and bist_para == "USD":
                e = usd_cevir(e)
            endeksler[sinif] = e
    for ad, sinif in tum_varliklar():
        if os.path.exists(os.path.join(RAW, f"{ad}.csv")):
            df = yukle(ad)
            if sinif == "kripto":  # 7/24 piyasa: bugünün mumu henüz kapanmadı
                df = df[df.index < bugun]
            if sinif == "bist" and bist_para == "USD":
                df = usd_cevir(df)
            out[ad] = (df, sinif)
    ENDEKS_VERI.clear()
    ENDEKS_VERI.update(endeksler)
    return out


ENDEKS_VERI = {}  # sınıf -> endeks DataFrame (tum_veriler çağrısıyla doldurulur)


def haftalik(df):
    """Günlük veriyi haftalık mumlara çevirir (hafta Pazar biter)."""
    return df.resample("W-SUN").agg({"Open": "first", "High": "max", "Low": "min",
                                     "Close": "last", "Volume": "sum"}).dropna()


def haftalik_gunluge(seri, gunluk_index):
    """Haftalık seriyi, ileriye bakma hatası olmadan günlük indekse taşır.

    t günündeki değer, t'den ÖNCE tamamlanmış son haftaya aittir.
    """
    s = seri.copy()
    s.index = s.index + pd.Timedelta(days=1)  # hafta Pazar kapanır → Pazartesi'den itibaren kullanılabilir
    return s.reindex(gunluk_index, method="ffill")
