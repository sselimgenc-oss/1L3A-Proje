"""Swing sistemi + sağlam trend kolları birleşimi (günlük getiri, günlük yeniden dengeleme).

Trend kolu seçim kuralı (önceden belirlendi): hem 2015-22 hem 2023-26 döneminde Sharpe ≥ 0,9 ve maks. düşüş
al-tut'tan küçük; hayatta kalma yanlılığına en açık olan "en iyi N hisse" momentum portföyleri hariç.
"""
import numpy as np
import pandas as pd

from kagit.motor import gunluk_egri
from swing.motor import portfoy
from swing.sistem import tum_islemler
from swing.veri import tum_veriler

from . import motor as M
from . import stratejiler as S
from .test import rejim_serisi
from .veri import MALIYET, evren, panel, yukle


def swing_gunluk():
    T = tum_islemler()
    hep = sum(T.values(), [])
    p = portfoy(hep, baslangic=100_000, detay=True)
    v = tum_veriler()
    son = max(df.index[-1] for df, _ in v.values())
    e = gunluk_egri(p["alinanlar"], v, pd.Timestamp("2015-01-01"), son, 100_000)
    return e.pct_change().fillna(0.0)


def kol_btc():
    df = yukle("BTC-USD")
    return M.getiri(df, S.t1(df), MALIYET["kripto"])


def kol_abd_trend():
    dfs = evren("abd")
    px = panel(dfs, "Close")
    W = S.agirliklar(px, S.skor_007p, "pozitif", None).mul(rejim_serisi("abd", px), axis=0)
    return M.portfoy_getirisi(dfs, W, MALIYET["abd"])


def kol_emtia_dusukvol():
    """Emtia ETF'leri (vade geçişi fiyata gömülü), 252 günlük volatilitesi en düşük %20, aylık."""
    import sys
    sys.path.insert(0, "scripts")
    from fetch_genis import EMTIA_ETF
    dfs = {t: yukle(t) for t in EMTIA_ETF}
    dfs = {k: v for k, v in dfs.items() if v is not None and len(v) > 300}
    px = panel(dfs, "Close")
    W = S.agirliklar(px, S.skor_012, "top", 0.2)
    return M.portfoy_getirisi(dfs, W, MALIYET["emtia"])


def birlestir(kollar, agirlik):
    df = pd.DataFrame(kollar).fillna(0.0)
    df = df[df.index >= "2015-01-01"]
    return (df * pd.Series(agirlik)).sum(axis=1)


def satir(ad, r):
    out = {"portföy": ad}
    for d, (a, b) in {"IS 2015-22": (None, M.ISS - pd.Timedelta(days=1)), "OOS 2023-26": (M.ISS, None)}.items():
        s = M.istatistik(r, 365, a, b)
        out[f"{d} CAGR"] = f"{s['CAGR']:.0%}"
        out[f"{d} maxDD"] = f"{s['maxDD']:.0%}"
        out[f"{d} Sharpe"] = f"{s['Sharpe']:.2f}"
    return out


if __name__ == "__main__":
    kollar = {"swing": swing_gunluk(), "btc_trend": kol_btc(), "abd_trend": kol_abd_trend(),
              "emtia_dusukvol": kol_emtia_dusukvol()}
    df = pd.DataFrame(kollar).fillna(0.0)
    df = df[df.index >= "2015-01-01"]
    haftalik = (1 + df).resample("W-SUN").prod() - 1
    print("Haftalık getiri korelasyonu:\n", haftalik.corr().round(2).to_string())
    senaryolar = {
        "Swing tek başına": {"swing": 1.0},
        "Trend kolları (eşit)": {"btc_trend": 1 / 3, "abd_trend": 1 / 3, "emtia_dusukvol": 1 / 3},
        "%70 swing + %30 trend": {"swing": 0.7, "btc_trend": 0.1, "abd_trend": 0.1, "emtia_dusukvol": 0.1},
        "%50 swing + %50 trend": {"swing": 0.5, "btc_trend": 1 / 6, "abd_trend": 1 / 6, "emtia_dusukvol": 1 / 6},
        "%50 swing + %50 trend (emtia hariç)": {"swing": 0.5, "btc_trend": 0.25, "abd_trend": 0.25},
    }
    rows = [satir(ad, birlestir(kollar, w)) for ad, w in senaryolar.items()]
    t = pd.DataFrame(rows)
    yr = birlestir(kollar, senaryolar["%50 swing + %50 trend"])
    yillik = pd.DataFrame({ad: (1 + birlestir(kollar, w)).resample("YE").prod() - 1
                           for ad, w in list(senaryolar.items())[:4]})
    yillik.index = yillik.index.year
    print((yillik * 100).round(1).to_string())
    print(t.to_string(index=False))
    with open("trend/BIRLESIM.md", "w", encoding="utf-8") as f:
        f.write("# Swing + trend kolları birleşimi\n\n")
        f.write("Haftalık getiri korelasyonu:\n\n" + haftalik.corr().round(2).to_markdown() + "\n\n")
        f.write(t.to_markdown(index=False) + "\n\n## Yıllık getiri (%)\n\n")
        f.write((yillik * 100).round(1).to_markdown() + "\n")
