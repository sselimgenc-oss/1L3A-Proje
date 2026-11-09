"""Price action stratejisi araştırması (kripto, 1S kurulum, 4S/1G eğilim).

Kullanım: python3 -m backtest.pa_arastirma izgara
"""
import itertools, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, pa
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "pa"
KES = pd.Timestamp("2024-01-01")
TREND = dict(d_f=20, d_s=50, h4_f=21, h4_s=50, kir_n=48, sw_n=12)
PORTFOY = dict(risk=0.01, max_poz=5, max_yon=5, max_pay=0.25, max_brut=1.0, maliyet=0.0007)


def kurulum_listesi(V, F, ad, yon, **kw):
    """Seyrek kurulum listesi: (t, j, tetik, stop_mesafesi)."""
    T, N = V["C"].shape
    gunluk_mum = int(round(86400 / (V["zaman"][1] - V["zaman"][0]).total_seconds()))
    tt, jj, tv, sv = [], [], [], []
    for j in range(N):
        c = V["C"][:, j]
        ok = ~np.isnan(c)
        if ok.sum() < gunluk_mum * 90:
            continue
        i0, i1 = np.argmax(ok), len(c) - np.argmax(ok[::-1])
        sl = slice(i0, i1)
        o = pd.Series(V["O"][sl, j]).ffill().to_numpy(); h = pd.Series(V["H"][sl, j]).ffill().to_numpy()
        l = pd.Series(V["L"][sl, j]).ffill().to_numpy(); cc = pd.Series(c[sl]).ffill().to_numpy()
        a = np.nan_to_num(F["atr"][sl, j], nan=np.nanmedian(F["atr"][sl, j]))
        m, tet, sm = pa.kurulum(o, h, l, cc, a, ad, yon, **kw)
        idx = np.flatnonzero(m)
        tt.append(idx + i0); jj.append(np.full(len(idx), j)); tv.append(tet[idx]); sv.append(sm[idx])
    return (np.concatenate(tt), np.concatenate(jj), np.concatenate(tv), np.concatenate(sv))


def diziler(V, F, listeler, p):
    T, N = V["C"].shape
    SIG = np.zeros((T, N)); GSEV = np.full((T, N), np.nan); STOP = np.full((T, N), np.nan)
    b = p["egilim"]
    up = np.ones((T, N), bool); dn = np.ones((T, N), bool)
    if "h4" in b:
        up &= F["h4_yon"] > 0; dn &= F["h4_yon"] < 0
    if "d" in b:
        up &= F["d_yon"] > 0; dn &= F["d_yon"] < 0
    evren = V["ONC"] < p["evren_n"]
    a = F["atr"]
    for (ad, yon), (t, j, tet, sm) in listeler.items():
        if ad not in p["kurulumlar"] or (p["yon"] == 1 and yon < 0):
            continue
        izin = (up if yon > 0 else dn)[t, j] & evren[t, j] & (SIG[t, j] == 0)
        t, j, tet, sm = t[izin], j[izin], tet[izin], sm[izin]
        sm = np.maximum(sm, p.get("stop_min_atr", 0.0) * a[t, j])
        SIG[t, j] = yon; GSEV[t, j] = tet; STOP[t, j] = sm
    if p["cikis"] == "h4":
        CIK = np.where(F["h4_yon"] < 0, -1.0, np.where(F["h4_yon"] > 0, 1.0, 0.0))
    elif p["cikis"] == "d":
        CIK = np.where(F["d_yon"] < 0, -1.0, np.where(F["d_yon"] > 0, 1.0, 0.0))
    else:
        CIK = np.zeros((T, N))
    return SIG, STOP, GSEV, CIK


def degerlendir(V, F, listeler, p, egri=False):
    SIG, STOP, GSEV, CIK = diziler(V, F, listeler, p)
    q = dict(PORTFOY, hedef_r=p.get("hedef_r", 0.0), tp1_r=p.get("tp1_r", 0.0), tp1_pay=p.get("tp1_pay", 0.25),
             be_tp1=True, max_bar=p.get("max_bar", 0))
    q["iz_atr"] = p.get("iz_atr", 0.0)
    e, t = portfoy(V, SIG, STOP, np.nan_to_num(F["atr"]), CIK, V["ONC"], q, GSEV=GSEV)
    out = {}
    for ad, m in (("TUM", slice(None)), ("IS", e.index < KES), ("OOS", e.index >= KES)):
        ee = e if isinstance(m, slice) else e[m]
        tt = t if isinstance(m, slice) else t[(t.giris_zaman < KES) if ad == "IS" else (t.giris_zaman >= KES)]
        out[ad] = metrik(ee, tt)
    x = t[t.giris_zaman >= KES].R.sort_values()
    x = x.iloc[:-5] if len(x) > 10 else x
    out["oos5x"] = float(x[x > 0].sum() / -x[x <= 0].sum()) if (x <= 0).any() else np.nan
    out["long_R"] = float(t[t.yon > 0].R.sum()); out["short_R"] = float(t[t.yon < 0].R.sum())
    out["stop_pct_med"] = float((100 * t.risk / t.giris).median()) if len(t) else np.nan
    return (out, e, t) if egri else out


CIKISLAR = [dict(cikis="yok", hedef_r=r) for r in (1.0, 1.5, 2.0, 3.0)] + \
           [dict(cikis="h4", hedef_r=0.0, tp1_r=1.0, tp1_pay=0.25)]

def yeniden_ornekle(V, kural="4h", kaydir=0):
    """1S T x N dizilerini daha yüksek zaman dilimine çevirir (O ilk, H maks, L min, C son, fonlama toplam).
    kaydir: mum başlangıcını saat olarak kaydırır (ör. 4S mumları 01:00, 05:00, ... UTC'de başlasın)."""
    z = V["zaman"]
    grup = pd.Series(np.arange(len(z)), index=z).resample(kural, label="left", closed="left",
                                                          offset=pd.Timedelta(hours=kaydir))
    bas = grup.first().dropna().astype(int).to_numpy()
    bit = grup.last().dropna().astype(int).to_numpy() + 1
    yeni_z = pd.DatetimeIndex(grup.first().dropna().index)
    def red(A, f):
        return np.stack([f(A[a:b], axis=0) for a, b in zip(bas, bit)])
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        O = np.stack([V["O"][a] for a in bas]); C = np.stack([V["C"][b - 1] for b in bit])
        H = red(V["H"], np.nanmax); L = red(V["L"], np.nanmin)
    FUND = red(V["FUND"], np.sum)
    out = dict(O=O, H=H, L=L, C=C, FUND=FUND, UYE=V["UYE"][bas], ONC=V["ONC"][bas], zaman=yeni_z,
               semboller=V["semboller"])
    if "VOL" in V:
        out["VOL"] = red(V["VOL"], np.nansum)
    return out


_V = _F = _L = None


def _is(p):
    return p, degerlendir(_V, _F, _L, p)


def izgara(tf="1h"):
    global _V, _F, _L
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _V = ks.yukle()
    if tf != "1h":
        _V = yeniden_ornekle(_V, tf)
    _F = ks.ozellikler(_V, TREND)
    _L = {(ad, y): kurulum_listesi(_V, _F, ad, y) for ad in pa.KURULUMLAR for y in (1, -1)}
    print("kurulum sayıları:", {f"{a}{'+' if y > 0 else '-'}": len(v[0]) for (a, y), v in _L.items()},
          f"{time.time()-t0:.0f}s", flush=True)
    gruplar = [(k,) for k in pa.KURULUMLAR] + [tuple(pa.KURULUMLAR)]
    isler = [dict(tf=tf, kurulumlar=g_, egilim=b, yon=y, evren_n=n, stop_min_atr=sm, **cx)
             for g_ in gruplar for b in ("h4", "d", "h4d") for y in (0, 1) for n in (10, 20) for sm in (0.0, 1.0)
             for cx in CIKISLAR]
    print(len(isler), "kombinasyon", flush=True)
    with get_context("fork").Pool(3) as pool:
        res = []
        for i, r in enumerate(pool.imap_unordered(_is, isler, chunksize=4)):
            res.append(r)
            if (i + 1) % 100 == 0:
                print(i + 1, f"{time.time()-t0:.0f}s", flush=True)
                pickle.dump(res, open(SONUC / f"izgara_{tf}.pkl", "wb"))
    pickle.dump(res, open(SONUC / f"izgara_{tf}.pkl", "wb"))
    print("bitti", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    izgara(sys.argv[2] if len(sys.argv) > 2 else "1h")
