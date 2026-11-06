"""Araştırma yardımcıları: veri yükleme, enstrüman ayarları, IS/OOS değerlendirme."""
from pathlib import Path
import numpy as np
import pandas as pd
from .motor import backtest, ozet
from . import strateji as st

VERI = Path(__file__).resolve().parent.parent / "data"

# Gidiş-dönüş maliyet varsayımları (spread + komisyon + kayma)
MALIYET = {
    "BTCUSDT": {"oran": 0.0008},   # vadeli taker ~%0.04/taraf -> %0.08 g-d
    "XAUUSD": {"sabit": 0.30},     # ~30 sent spread+komisyon
    "UKOIL": {"sabit": 0.04},      # ~4 sent
    "SPX": {"sabit": 0.50},        # ~0.5 endeks puanı
    "XU030": {"oran": 0.0006},     # VİOP endeks vadeli (komisyon + 1 tick kayma) varsayımı
}
# Likit seanslar (UTC)
SEANS = {
    "BTCUSDT": (0, 0),             # 7/24 - filtre yok
    "XAUUSD": (7, 20),             # Londra + New York
    "UKOIL": (7, 20),
    "SPX": (13.5, 20),             # ABD nakit seansı
    "XU030": (7, 15),              # BIST seansı (TSİ 10:00-18:00)
}
SEMBOLLER = ["BTCUSDT", "XAUUSD", "UKOIL", "SPX"]


def yukle(sym, tf):
    return pd.read_pickle(VERI / f"{sym}_{tf}.pkl")


_CACHE = {}


def veri(sym, tf):
    if (sym, tf) not in _CACHE:
        _CACHE[(sym, tf)] = yukle(sym, tf)
    return _CACHE[(sym, tf)]


def calistir(sym, tf, fonk, p, seans_ozel=True):
    df = veri(sym, tf)
    p = dict(p)
    if seans_ozel and p.get("seans") is None:
        p["seans"] = SEANS[sym]
    sig, stop, hedef, cikis, zorla = fonk(df, p)
    t = backtest(df, sig, stop, hedef, MALIYET[sym], cikis, zorla,
                 max_bar=p.get("max_bar", 0), be_tetik=p.get("be", 0.0), iz_mesafe=p.get("iz", 0.0))
    return t


def bolum(t, df_index, oran=0.6):
    """Zaman bazlı IS/OOS ayrımı."""
    kes = df_index[0] + (df_index[-1] - df_index[0]) * oran
    return t[t.giris_zaman < kes], t[t.giris_zaman >= kes], kes


def degerlendir(tf, fonk, p, semboller=SEMBOLLER, oran=0.6, yazdir=True):
    satirlar = []
    for s in semboller:
        t = calistir(s, tf, fonk, p)
        is_, oos, kes = bolum(t, veri(s, tf).index, oran)
        for ad, x in (("IS", is_), ("OOS", oos), ("TUM", t)):
            o = ozet(x)
            o.update(sembol=s, bolum=ad)
            satirlar.append(o)
    r = pd.DataFrame(satirlar).set_index(["sembol", "bolum"])
    if yazdir:
        with pd.option_context("display.float_format", "{:.2f}".format, "display.width", 200):
            print(r)
    return r


def yillik(t):
    t = t.copy()
    t["yil"] = t.giris_zaman.dt.year
    return t.groupby("yil").apply(lambda x: pd.Series(ozet(x)), include_groups=False)
