"""Trend/portföy stratejilerinin testi: orijinal, düzeltilmiş ve bizim yaklaşımla geliştirilmiş sürümler.

  python -m trend.test            → trend/SONUCLAR_TREND.md
Volatilite hedefi, yalnızca 2015-2022 (IS) verisinden hesaplanır (OOS'a bakılmaz).
"""
import numpy as np
import pandas as pd

from . import motor as M
from . import stratejiler as S
from .veri import MALIYET, evren, panel, yukle

TEKLER = [("BTC-USD", "kripto", 365), ("ETH-USD", "kripto", 365), ("XU100.IS", "endeks", 252),
          ("XU030.IS", "endeks", 252), ("^GSPC", "endeks", 252), ("^NDX", "endeks", 252), ("GC=F", "emtia", 252)]
REJIM = {"bist": "XU100.IS", "abd": "^GSPC", "emtia": None}
SATIR = []


def hedef_vol(c, ann):
    """IS dönemi (2015-2022) gerçekleşen volatilitesinin medyanının %75'i."""
    v = c.pct_change().rolling(60).std() * np.sqrt(ann)
    return float(v.loc[:M.ISS].median() * 0.75)


def kaydet(grup, ad, strateji, d):
    for donem, s in d.items():
        if s:
            SATIR.append(dict(grup=grup, varlik=ad, strateji=strateji, donem=donem, **s))


def tekler():
    for t, sinif, ann in TEKLER:
        df = yukle(t, usd=t.endswith(".IS"))
        if df is None:
            continue
        c = df["Close"]
        bir = pd.Series(1.0, index=df.index)
        kaydet("tek", t, "al-tut", M.donemler(M.getiri(df, bir, 0.0), ann))
        hv = hedef_vol(c, ann)
        for ad, f in S.TEKLER.items():
            pos = f(df)
            kaydet("tek", t, ad, M.donemler(M.getiri(df, pos, MALIYET[sinif]), ann, pos, df))
        for ad, f in (("037 SMA50", S.s037), ("T1 bizim (EMA10/30 + SMA50)", S.t1)):
            pos = f(df) * S.vol_hedef(c, 0.12, ann)
            kaydet("tek", t, ad + " + vol %12 (orijinal)", M.donemler(M.getiri(df, pos, MALIYET[sinif]), ann, pos, df))
            pos = f(df) * S.vol_hedef(c, hv, ann)
            kaydet("tek", t, ad + f" + vol %{hv * 100:.0f} (IS'ten)",
                   M.donemler(M.getiri(df, pos, MALIYET[sinif]), ann, pos, df))


def rejim_serisi(sinif, px):
    t = REJIM[sinif]
    if t:
        c = yukle(t, usd=t.endswith(".IS"))["Close"]
    else:  # emtia: evrenin eşit ağırlıklı endeksi
        c = (1 + px.pct_change().mean(axis=1).fillna(0)).cumprod()
    return S.yon_ema(c).reindex(px.index, method="ffill").fillna(0.0)


def portfoyler(sinif):
    dfs = evren(sinif)
    px = panel(dfs, "Close")
    mal = MALIYET[sinif]
    ew = (px.notna()).astype(float)
    ew = ew.div(ew.sum(axis=1), axis=0).fillna(0)
    kaydet(sinif, "evren", "eşit ağırlık al-tut", M.donemler(M.portfoy_getirisi(dfs, ew, 0.0), 252))
    rj = rejim_serisi(sinif, px)
    for ad, (fn, secim, q) in S.PORTFOY.items():
        if ad.startswith("089") and sinif != "emtia":
            continue
        W = S.agirliklar(px, fn, secim, q)
        maruz = W.sum(axis=1)
        r0 = M.portfoy_getirisi(dfs, W, mal)
        kaydet(sinif, "evren", ad, M.donemler(r0, 252, maruz, _sentetik(r0)))
        W2 = W.mul(rj, axis=0)
        r1 = M.portfoy_getirisi(dfs, W2, mal)
        kaydet(sinif, "evren", ad + " + rejim", M.donemler(r1, 252, W2.sum(axis=1), _sentetik(r1)))
        # portföy düzeyinde volatilite hedefi (IS medyanının %75'i), haftalık güncelleme
        v = r1.rolling(60).std() * np.sqrt(252)
        hv = float(v.loc[:M.ISS][v.loc[:M.ISS] > 0.01].median() * 0.75)  # yalnız piyasadayken
        olc = (hv / v).clip(upper=1.0).resample("W-SUN").last()
        olc = S.haftadan_gune(olc, px.index).fillna(0.0)
        W3 = W2.mul(olc, axis=0)
        r2 = M.portfoy_getirisi(dfs, W3, mal)
        kaydet(sinif, "evren", ad + f" + rejim + vol %{hv * 100:.0f}", M.donemler(r2, 252, W3.sum(axis=1), _sentetik(r2)))
    return dfs


def _sentetik(r):
    """Portföy için işlem bazlı KO anlamsız (sürekli dengeleme); istatistikte işlem sayımı yapılmaz."""
    return None


def tablo(df):
    d = df.copy()
    for k in ("toplam", "CAGR", "maxDD", "piyasada", "KO"):
        if k in d:
            d[k] = d[k].map(lambda x: "" if pd.isna(x) else f"{x * 100:.0f}%")
    d["Sharpe"] = d["Sharpe"].map(lambda x: f"{x:.2f}")
    if "islem" in d:
        d["islem"] = d["islem"].map(lambda x: "" if pd.isna(x) else f"{int(x)}")
    return d.to_markdown(index=False)


if __name__ == "__main__":
    tekler()
    for s in ("bist", "abd", "emtia"):
        portfoyler(s)
    df = pd.DataFrame(SATIR)
    df.to_csv("trend/sonuclar_trend.csv", index=False)
    with open("trend/SONUCLAR_TREND.md", "w", encoding="utf-8") as f:
        f.write("# Trend / portföy stratejileri — test sonuçları\n\n")
        f.write("Ertesi açılışta işlem, sınıf maliyeti (BIST %0,15, kripto %0,10, diğer %0,05 tek yön), "
                "BIST ve XU endeksleri USD bazında, kaldıraç yok, yalnız long.\n\n")
        for donem in ("2015-22 (IS)", "2023-26 (OOS)", "2020-26"):
            f.write(f"## {donem}\n\n")
            x = df[df.donem == donem].drop(columns=["donem"])
            f.write(tablo(x) + "\n\n")
    print(open("trend/SONUCLAR_TREND.md", encoding="utf-8").read()[:200])
