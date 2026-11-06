"""Kripto strateji araştırması: varyant ızgarası, IS/OOS, coin bazında tutarlılık, BTC al-tut kıyası.

Kullanım: python3 -m backtest.kripto_arastirma [izgara|tek]
"""
import itertools, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "kripto"
KES = pd.Timestamp("2024-01-01")     # IS: 2020-2023 (boğa+ayı+toparlanma), OOS: 2024-2026/09

PORTFOY = dict(risk=0.01, max_poz=10, max_yon=10, max_pay=0.25, max_brut=1.0, maliyet=0.0007)


def degerlendir(V, F, p, egri_dondur=False):
    sig, stop, iz, cik, onc = ks.sinyaller(V, F, p)
    q = dict(PORTFOY, **{k: p[k] for k in ("tp1_r", "tp1_pay", "be_tp1", "hedef_r", "max_bar", "max_poz",
                                            "max_yon", "risk") if k in p})
    q["iz_atr"] = p.get("iz_atr", 0.0)
    e, t = portfoy(V, sig, stop, iz, cik, onc, q)
    out = {}
    for ad, m in (("TUM", slice(None)), ("IS", e.index < KES), ("OOS", e.index >= KES)):
        ee = e[m] if not isinstance(m, slice) else e
        tt = t if isinstance(m, slice) else t[(t.giris_zaman < KES) if ad == "IS" else (t.giris_zaman >= KES)]
        out[ad] = metrik(ee, tt)
    # coin bazında: en az 5 işlemi olan coinlerin kaçında toplam R > 0
    g = t.groupby("sembol").R.agg(["sum", "count"])
    g = g[g["count"] >= 5]
    out["coin_karli_oran"] = float((g["sum"] > 0).mean()) if len(g) else np.nan
    for ad, tt in (("TUM", t), ("OOS", t[t.giris_zaman >= KES])):
        x = tt.R.sort_values().iloc[:-5] if len(tt) > 10 else tt.R
        out[f"{ad}_pf_top5_haric"] = float(x[x > 0].sum() / -x[x <= 0].sum()) if (x <= 0).any() else np.nan
    out["long_R"] = float(t[t.yon > 0].R.sum()); out["short_R"] = float(t[t.yon < 0].R.sum())
    out["long_n"] = int((t.yon > 0).sum()); out["short_n"] = int((t.yon < 0).sum())
    if egri_dondur:
        return out, e, t
    return out


def btc_al_tut(V):
    j = V["semboller"].index("BTCUSDT")
    c = pd.Series(V["C"][:, j], index=V["zaman"]).dropna()
    return metrik(c / c.iloc[0], pd.DataFrame({"R": []}))


STOP = dict(sw_n=12, tampon_atr=0.5, stop_min_atr=1.5, stop_max_atr=5.0)
GIRIS_IZGARA = [dict(giris=g_, d_f=df_, d_s=ds_, h4_f=21, h4_s=50) for g_ in ("gc", "kir") for df_, ds_ in ((20, 50), (10, 30))]
SINYAL_IZGARA = {
    "gc": [dict(rsi_dip=d, rsi_don=50, gc_pencere=w, h4_rsi_esik=e) for d, w, e in
           itertools.product([30, 40], [12, 24], [0, 50])],
    "kir": [dict(kir_n=n, h4_rsi_esik=e) for n, e in itertools.product([24, 48, 96], [0, 50])],
}
CIKIS_IZGARA = [dict(cikis=c, iz_atr=i, iz_tf="4h", tp1_r=tp, tp1_pay=0.5, be_tp1=True)
                for c, i, tp in itertools.product(["h4", "d", "yok"], [0.0, 3.0], [0.0, 1.5])
                if not (c == "yok" and i == 0.0)]

_V = _F = None


def _is(p):
    o = degerlendir(_V, _F, p)
    return p, o


IZGARA2 = dict(
    giris=[dict(giris="gc", rsi_dip=40, rsi_don=50, gc_pencere=24, kir_n=48), dict(giris="kir", kir_n=48), dict(giris="kir", kir_n=96)],
    cikis=["h4", "d"], tp1_r=[0.0, 1.5], yon=[0, 1], btc_filtre=[0, 1], evren_n=[10, 20, 40], rs_filtre=[0, 1], max_poz=[5, 10])


def izgara2():
    global _V, _F
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _V = ks.yukle()
    sonuc = []
    for gp in IZGARA2["giris"]:
        taban = dict(gp, d_f=20, d_s=50, h4_f=21, h4_s=50, h4_rsi_esik=0, iz_atr=0.0, iz_tf="4h", tp1_pay=0.5,
                     be_tp1=True, **STOP)
        _F = ks.ozellikler(_V, taban)
        isler = [dict(taban, cikis=c, tp1_r=tp, yon=y, btc_filtre=b, evren_n=n, rs_filtre=rs, max_poz=mp, max_yon=mp)
                 for c, tp, y, b, n, rs, mp in itertools.product(IZGARA2["cikis"], IZGARA2["tp1_r"], IZGARA2["yon"],
                                                                 IZGARA2["btc_filtre"], IZGARA2["evren_n"],
                                                                 IZGARA2["rs_filtre"], IZGARA2["max_poz"])]
        with get_context("fork").Pool(3) as pool:
            sonuc += pool.map(_is, isler, chunksize=2)
        print(gp, len(sonuc), f"{time.time()-t0:.0f}s", flush=True)
        pickle.dump(sonuc, open(SONUC / "izgara2.pkl", "wb"))


def izgara():
    global _V, _F
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _V = ks.yukle()
    print("veri:", _V["C"].shape, f"{time.time()-t0:.0f}s", flush=True)
    sonuc = []
    for gp in GIRIS_IZGARA:
        for kn in ([24, 48, 96] if gp["giris"] == "kir" else [48]):
            _F = ks.ozellikler(_V, dict(gp, kir_n=kn, sw_n=STOP["sw_n"]))
            isler = [dict(gp, **sp, **cp, **STOP, yon=yon, btc_filtre=bf)
                     for sp in SINYAL_IZGARA[gp["giris"]] if not (gp["giris"] == "kir" and sp["kir_n"] != kn)
                     for cp in CIKIS_IZGARA for yon in (0, 1) for bf in (0, 1)]
            with get_context("fork").Pool(3) as pool:
                sonuc += pool.map(_is, isler, chunksize=2)
            print(gp, kn, len(sonuc), f"{time.time()-t0:.0f}s", flush=True)
            pickle.dump(sonuc, open(SONUC / "izgara.pkl", "wb"))
    print("BTC al-tut:", btc_al_tut(_V))


if __name__ == "__main__":
    {"izgara": izgara, "izgara2": izgara2}[sys.argv[1] if len(sys.argv) > 1 else "izgara"]()
