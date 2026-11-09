"""Sağlam çıkan trend kollarının geliştirilmesi ve duyarlılık testleri (seçim yalnız 2015-22 IS verisiyle)."""
import numpy as np
import pandas as pd

from swing.veri import yukle as swing_yukle

from . import motor as M
from . import stratejiler as S
from .test import rejim_serisi
from .veri import MALIYET, evren, panel, yukle

KRIPTO = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "TRX", "ADA", "LINK", "AVAX", "XLM", "SUI", "BCH", "HBAR",
          "LTC", "TON", "DOT", "SHIB", "UNI", "NEAR", "APT", "AAVE", "ICP", "ETC", "PEPE"]
SAT = []


def ozet(ad, r, ann=365):
    a = M.istatistik(r, ann, None, M.ISS - pd.Timedelta(days=1))
    b = M.istatistik(r, ann, M.ISS, None)
    SAT.append(dict(deney=ad, IS_CAGR=a.get("CAGR"), IS_DD=a.get("maxDD"), IS_Sh=a.get("Sharpe"),
                    OOS_CAGR=b.get("CAGR"), OOS_DD=b.get("maxDD"), OOS_Sh=b.get("Sharpe")))


# ------------------------------------------------------------------ 1) BTC trend duyarlılığı
def btc():
    df = yukle("BTC-USD")
    ozet("BTC al-tut", M.getiri(df, pd.Series(1.0, index=df.index), 0))
    for n in (30, 40, 50, 70, 100):
        pos = S.t1(df, n=n)
        ozet(f"BTC T1 SMA{n}", M.getiri(df, pos, MALIYET["kripto"]))
    pos = S.t1(df)
    ozet("BTC T1 SMA50, 2x maliyet", M.getiri(df, pos, 2 * MALIYET["kripto"]))


# ------------------------------------------------------------------ 2) Kripto trend portföyü
def kripto_portfoy(adlar, tavan, rejim=True, ad=""):
    dfs = {k: swing_yukle(f"{k}USDT") for k in adlar}
    dfs = {k: d for k, d in dfs.items() if len(d) > 300}
    px = panel(dfs, "Close")
    sig = pd.DataFrame({k: S.t1(d).reindex(px.index) for k, d in dfs.items()}).fillna(0.0)
    if rejim:
        btc = dfs["BTC"]
        rj = S.t1(btc).reindex(px.index).fillna(0.0)
        sig = sig.mul(rj, axis=0)
    adet = sig.sum(axis=1)
    W = sig.div(adet.where(adet > 0), axis=0).fillna(0.0).clip(upper=tavan)
    r = M.portfoy_getirisi(dfs, W, MALIYET["kripto"])
    ozet(ad or f"Kripto T1 portföyü {len(dfs)} coin, tavan %{tavan * 100:.0f}, rejim={rejim}", r)
    return r


# ------------------------------------------------------------------ 3) ABD trend portföyü duyarlılığı
def abd():
    dfs = evren("abd")
    px = panel(dfs, "Close")
    rj_ema = rejim_serisi("abd", px)
    spx = yukle("^GSPC")["Close"]
    rj_sma = (spx > spx.rolling(200).mean()).astype(float).shift(0).reindex(px.index, method="ffill").fillna(0)
    ew = px.notna().astype(float)
    ew = ew.div(ew.sum(axis=1), axis=0)
    ozet("ABD eşit ağırlık al-tut", M.portfoy_getirisi(dfs, ew, 0), 252)
    for ay in (6, 9, 12):
        fn = lambda m, p, ay=ay: m / m.shift(ay) - 1
        W = S.agirliklar(px, fn, "pozitif", None)
        ozet(f"ABD trend {ay} ay, rejim yok", M.portfoy_getirisi(dfs, W, MALIYET["abd"]), 252)
        ozet(f"ABD trend {ay} ay, rejim EMA10/30", M.portfoy_getirisi(dfs, W.mul(rj_ema, axis=0), MALIYET["abd"]), 252)
        ozet(f"ABD trend {ay} ay, rejim SMA200", M.portfoy_getirisi(dfs, W.mul(rj_sma, axis=0), MALIYET["abd"]), 252)
    W = S.agirliklar(px, S.skor_007p, "pozitif", None).mul(rj_ema, axis=0)
    ozet("ABD trend 12 ay, rejim EMA10/30, 2x maliyet", M.portfoy_getirisi(dfs, W, 2 * MALIYET["abd"]), 252)
    # hayatta kalma yanlılığı kontrolü: Mag7 hariç 43 hisse
    mag7 = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"}
    d2 = {k: v for k, v in dfs.items() if k not in mag7}
    p2 = panel(d2, "Close")
    W = S.agirliklar(p2, S.skor_007p, "pozitif", None).mul(rj_ema.reindex(p2.index).fillna(0), axis=0)
    ozet("ABD trend 12 ay, rejim EMA10/30, Mag7 HARİÇ", M.portfoy_getirisi(d2, W, MALIYET["abd"]), 252)


# ------------------------------------------------------------------ 4) Emtia düşük volatilite: vadeli vs ETF
def emtia(etf_listesi=None):
    for ad, dfs in (("vadeli", evren("emtia")), ("ETF", {t: yukle(t) for t in (etf_listesi or [])})):
        dfs = {k: v for k, v in dfs.items() if v is not None and len(v) > 300}
        if not dfs:
            continue
        px = panel(dfs, "Close")
        ew = px.notna().astype(float)
        ew = ew.div(ew.sum(axis=1), axis=0)
        ozet(f"Emtia {ad} eşit ağırlık al-tut ({len(dfs)})", M.portfoy_getirisi(dfs, ew, 0), 252)
        for gun in (126, 252):
            for q in (0.1, 0.2):
                fn = lambda m, p, gun=gun: -(p.pct_change().rolling(gun).std().resample("ME").last())
                W = S.agirliklar(px, fn, "top", q)
                ozet(f"Emtia {ad} düşük vol {gun}g, en iyi %{q * 100:.0f}",
                     M.portfoy_getirisi(dfs, W, MALIYET["emtia"]), 252)
        W = S.agirliklar(px, S.skor_007p, "pozitif", None)
        ozet(f"Emtia {ad} trend 12 ay (pozitifler)", M.portfoy_getirisi(dfs, W, MALIYET["emtia"]), 252)


def yazdir():
    d = pd.DataFrame(SAT)
    for k in ("IS_CAGR", "IS_DD", "OOS_CAGR", "OOS_DD"):
        d[k] = d[k].map(lambda x: "" if pd.isna(x) else f"{x * 100:.0f}%")
    for k in ("IS_Sh", "OOS_Sh"):
        d[k] = d[k].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    return d


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "scripts")
    from fetch_genis import EMTIA_ETF
    btc()
    kripto_portfoy(["BTC", "ETH"], 0.5, ad="Kripto T1 BTC+ETH, tavan %50")
    kripto_portfoy(["BTC", "ETH"], 1.0, ad="Kripto T1 BTC+ETH, tavan %100")
    for tavan in (0.1, 0.2, 1 / 3):
        kripto_portfoy(KRIPTO, tavan)
    kripto_portfoy(KRIPTO, 0.2, rejim=False)
    kripto_portfoy(KRIPTO[:10], 0.2, ad="Kripto T1 ilk 10 coin, tavan %20")
    abd()
    emtia(EMTIA_ETF)
    d = yazdir()
    pd.set_option("display.width", 200)
    print(d.to_string(index=False))
    with open("trend/GELISTIRME.md", "w", encoding="utf-8") as f:
        f.write("# Trend kollarının geliştirilmesi ve duyarlılık\n\n" + d.to_markdown(index=False) + "\n")
