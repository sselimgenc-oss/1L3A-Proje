"""KMN (kesitsel momentum, piyasa nötr) hedef portföy üretici.

Kural (backtest.momentum, seçilen ayar): bir önceki ay sonundaki 30 günlük USDT hacmine göre ilk 30 USDT-M vadeli coin
(backtest evreniyle aynı: ay boyunca sabit; ay başında en az 90 gün, dengeleme gününde en az 90 günlük kesintisiz geçmiş),
skor = son 14 günlük günlük getirilerin ortalaması / standart sapması (151 Trading Stratejisi §3.1, riske göre
düzeltilmiş momentum). En yüksek skorlu 5 coin LONG, en düşük 5 coin SHORT. Ağırlık: 30 günlük oynaklığın tersiyle
orantılı; her taraf sermayenin %50'si (toplam brüt = sermaye, net ~0). 14 günde bir, gün kapanışından (00:00 UTC) hemen
sonra dengelenir; aradaki günlerde adetlere dokunulmaz (backtest kayma=True ile aynı). Sermaye iki alt portföye bölünüp
7 gün arayla dengelenmesi önerilir (tek dengeleme gününün şans etkisini azaltır).

Canlı kullanım (Binance açık API'si, anahtar gerekmez):
    python3 -m backtest.momentum_sinyal --sermaye 10000
Çevrimdışı doğrulama (yerel backtest verisiyle):
    python3 -m backtest.momentum_sinyal --yerel --tarih 2025-06-15 --sermaye 10000
"""
import argparse
import numpy as np
import pandas as pd
from .kripto_sinyal import _get
from .kripto_evren import HARIC

AYAR = dict(N=30, L=14, K=5, H=14, gecmis_gun=90, vol_gun=30)


def hedef_agirlik(C, evren, ayar=AYAR):
    """C: günlük kapanışlar (satır=gün, sütun=coin; son satır = son kapanmış gün). evren: uygun coin listesi.
    Döndürür: coin -> ağırlık (long > 0, short < 0)."""
    rr = C.pct_change()
    L, K = ayar["L"], ayar["K"]
    x = rr.iloc[-L:]
    skor = (x.mean() / x.std())[evren].dropna()
    vol = rr.iloc[-ayar["vol_gun"]:].std()
    if len(skor) < 2 * K:
        return pd.Series(dtype=float)
    skor = skor.sort_values()
    out = {}
    for taraf, sec in ((1, skor.index[-K:]), (-1, skor.index[:K])):
        v = 1 / vol[sec].clip(lower=0.01)                     # backtest VOL_TABAN ile aynı
        for s, w in (0.5 * v / v.sum()).items():
            out[s] = taraf * w
    return pd.Series(out).sort_values(ascending=False)


def canli(sermaye):
    info = _get("/fapi/v1/exchangeInfo")
    uygun = {s["symbol"] for s in info["symbols"] if s.get("contractType") == "PERPETUAL"
             and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING" and s["symbol"] not in HARIC}
    # aday havuzu geniş tutulur (son 24 saatte sakin ama geçen ay hacimli coinler kaçmasın)
    t24 = sorted((x for x in _get("/fapi/v1/ticker/24hr") if x["symbol"] in uygun), key=lambda x: -float(x["quoteVolume"]))[:120]
    bugun = pd.Timestamp.utcnow().tz_localize(None).floor("D")
    ay_bas = bugun.replace(day=1)
    kap, hacim = {}, {}
    for x in t24:
        k = _get("/fapi/v1/klines", symbol=x["symbol"], interval="1d", limit=300)
        d = pd.DataFrame(k).iloc[:, [0, 4, 7]].astype(float)
        d.index = pd.to_datetime(d[0], unit="ms")
        d = d[d.index < bugun]                                                     # yalnız kapanmış günler
        once = d[d.index < ay_bas]                                                 # ay başından önceki veri
        if len(once) >= AYAR["gecmis_gun"] and len(d) >= AYAR["gecmis_gun"]:
            kap[x["symbol"]] = d[4]; hacim[x["symbol"]] = once[7].iloc[-30:].sum()
    evren = [s for s, _ in sorted(hacim.items(), key=lambda kv: -kv[1])[:AYAR["N"]]]
    C = pd.DataFrame(kap)
    return hedef_agirlik(C, evren), C.iloc[-1], C.index[-1]


def yerel(tarih):
    from .momentum import gunluk_panel
    D = gunluk_panel()
    d = pd.Timestamp(tarih).floor("D")
    C = D["C"][D["C"].index <= d]
    gecmis = C.notna().rolling(AYAR["gecmis_gun"]).sum().iloc[-1] >= AYAR["gecmis_gun"]
    evren = [s for s in C.columns if D["ONC"].loc[d, s] < AYAR["N"] and gecmis[s] and pd.notna(C[s].iloc[-1])]
    return hedef_agirlik(C, evren), C.iloc[-1], d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sermaye", type=float, default=10000)
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--tarih")
    a = ap.parse_args()
    W, fiyat, gun = yerel(a.tarih) if a.yerel else canli(a.sermaye)
    print(f"\nKMN hedef portföy — son kapanmış gün: {gun.date()} | sermaye {a.sermaye:,.0f} USDT")
    print("14 günde bir dengelenir: hedefle mevcut pozisyon arasındaki farkı al/sat.\n")
    t = pd.DataFrame({"yon": np.where(W > 0, "LONG", "SHORT"), "agirlik_%": (100 * W).round(2),
                      "tutar_usdt": (a.sermaye * W).round(0), "fiyat": fiyat[W.index].values,
                      "miktar": (a.sermaye * W / fiyat[W.index]).round(6)})
    print(t.to_string())
    print(f"\nBrüt {100 * W.abs().sum():.0f}% | net {100 * W.sum():+.1f}%")


if __name__ == "__main__":
    main()
