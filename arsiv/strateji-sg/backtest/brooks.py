"""Al Brooks tabanlı strateji araştırması (kripto, Binance USDT-M).

Kaynaklar (metinler/): "Price Action Trends" (Bölüm 10 İkinci Girişler, 19 Trendde Güç Belirtileri, 20 İki Bacak),
"En Başarılı 10 Price Action Modeli" (Yüksek 1/Yüksek 2 boğa bayrağı, güçlü sinyal mumu, swing hedefi >= 2R).

Bileşenler:
  * Trend gücü ("always-in long", Brooks Bölüm 19): kapanış 20 EMA üstünde, 20 EMA yükseliyor ve son 20 kapanışın
    en az 'guc' oranı 20 EMA üstünde. Opsiyonel üst zaman dilimi (1G) EMA trend filtresi.
  * Kurulum: H1 / H2 boğa bayrağı (pa.py), güçlü boğa sinyal mumu, sinyal mumunun tepesine alış stop emri.
  * Stop: sinyal mumunun dibi (en az stop_min_atr x ATR) veya geri çekilme dibi (son 'sw' mumun en düşüğü).
  * Çıkış seçenekleri:
      'brooks2' — 20 EMA'nın karşı tarafında art arda İKİ kapanış (Brooks: güçlü trendde bu olmaz; olursa trend zayıflar)
      'trend'   — EMA21 < EMA50 ve kapanış EMA21 altı (KGT/SKA ile aynı)
      'hedef'   — sabit 2R hedef (Brooks'un swing için asgari ödül/risk ölçütü)
    + opsiyonel kısmi kâr (1R'de 1/4) ve başabaş.
Değerlendirme: 4S'de 4 mum hizalamasının sermaye bölünmüş ortalaması (hizalama şansını elemek için).
"""
import itertools, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, pa_arastirma as P, pa
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "brooks"
KES = P.KES


def ozellik(V, tf):
    F = ks.ozellikler(V, dict(P.TREND, h4_kural=tf))
    C = pd.DataFrame(V["C"])
    e20 = C.ewm(span=20, adjust=False).mean()
    F["e20"] = e20.to_numpy()
    F["e20_egim"] = (e20 - e20.shift(5)).to_numpy()
    F["ust_oran"] = (C > e20).astype(float).rolling(20, min_periods=20).mean().to_numpy()
    alt2 = (C < e20) & (C.shift(1) < e20.shift(1))
    ust2 = (C > e20) & (C.shift(1) > e20.shift(1))
    F["brooks_cik"] = np.where(alt2, -1.0, np.where(ust2, 1.0, 0.0))
    F["sw_l5"] = pd.DataFrame(V["L"]).rolling(5, min_periods=1).min().to_numpy()
    return F


def listeler(V, F, kur, sk):
    return {(ad, 1): P.kurulum_listesi(V, F, ad, 1, sinyal_kapanis=sk) for ad in kur}


def diziler(V, F, L, p):
    T, N = V["C"].shape
    SIG = np.zeros((T, N)); GSEV = np.full((T, N), np.nan); STOP = np.full((T, N), np.nan)
    up = (V["C"] > F["e20"]) & (F["e20_egim"] > 0) & (F["ust_oran"] >= p["guc"])
    if p.get("d_filtre"):
        up &= F["d_yon"] > 0
    up &= V["ONC"] < p["evren_n"]
    a = F["atr"]
    for (ad, y), (t, j, tet, sm) in L.items():
        if ad not in p["kurulumlar"]:
            continue
        ok = up[t, j] & (SIG[t, j] == 0)
        t, j, tet, sm = t[ok], j[ok], tet[ok], sm[ok]
        if p["stop"] == "salinim":    # geri çekilme dibi: son 5 mumun en düşüğü
            sm = np.maximum(tet - F["sw_l5"][t, j] + 0.02 * a[t, j], sm)
        sm = np.maximum(sm, p.get("stop_min_atr", 1.0) * a[t, j])
        SIG[t, j] = 1; GSEV[t, j] = tet; STOP[t, j] = sm
    if p["cikis"] == "brooks2":
        CIK = F["brooks_cik"]
    elif p["cikis"] == "trend":
        CIK = np.where(F["h4_yon"] < 0, -1.0, np.where(F["h4_yon"] > 0, 1.0, 0.0))
    else:
        CIK = np.zeros((T, N))
    return SIG, STOP, GSEV, CIK


def calistir(V, F, L, p, risk=0.01):
    SIG, STOP, GSEV, CIK = diziler(V, F, L, p)
    q = dict(P.PORTFOY, risk=risk, hedef_r=2.0 if p["cikis"] == "hedef" else 0.0,
             tp1_r=1.0 if p.get("kismi") else 0.0, tp1_pay=0.25, be_tp1=True)
    return portfoy(V, SIG, STOP, np.zeros_like(STOP), CIK, V["ONC"], q, GSEV=GSEV)


def gunluk(e):
    return e.resample("1D").last().pct_change().fillna(0)


def ozet_getiri(r, t_listesi):
    e = (1 + r).cumprod()
    m = metrik(e, pd.DataFrame({"R": []}))
    eo = e[e.index >= KES]; mo = metrik(eo / eo.iloc[0], pd.DataFrame({"R": []}))
    ei = e[e.index < KES]; mi = metrik(ei / ei.iloc[0], pd.DataFrame({"R": []}))
    t = pd.concat(t_listesi) if t_listesi else pd.DataFrame({"R": []})
    R = t.R
    pf = R[R > 0].sum() / -R[R <= 0].sum() if (R <= 0).any() else np.nan
    to = t[t.giris_zaman >= KES].R if len(t) else R
    pfo = to[to > 0].sum() / -to[to <= 0].sum() if (to <= 0).any() else np.nan
    return dict(cagr=m["cagr"], maxdd=m["maxdd"], sharpe=m["sharpe"], calmar=m["calmar"],
                is_cagr=mi["cagr"], is_sharpe=mi["sharpe"], oos_cagr=mo["cagr"], oos_dd=mo["maxdd"], oos_sharpe=mo["sharpe"],
                kazanma=100 * (R > 0).mean() if len(R) else np.nan, pf=pf, oos_pf=pfo, islem=len(R) / len(t_listesi))


IZGARA = dict(kurulumlar=[("H1",), ("H2",), ("H1", "H2")], guc=[0.6, 0.8], d_filtre=[0, 1], stop=["sinyal", "salinim"],
              cikis=["brooks2", "trend", "hedef"], kismi=[0, 1], evren_n=[10, 20])

_D = None


def _is(p):
    rs, ts = [], []
    for k, (V, F, L) in _D.items():
        e, t = calistir(V, F, L, p)
        rs.append(gunluk(e)); ts.append(t)
    r = pd.concat(rs, axis=1).fillna(0).mean(axis=1)
    return p, ozet_getiri(r, ts), r


def izgara(tf="4h", sk=0.6):
    global _D
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    V1 = ks.yukle()
    kaymalar = range(4) if tf == "4h" else ([0] if tf == "1h" else range(int(tf[:-1])))
    _D = {}
    for k in kaymalar:
        V = V1 if tf == "1h" else P.yeniden_ornekle(V1, tf, k)
        F = ozellik(V, tf)
        _D[k] = (V, F, listeler(V, F, ("H1", "H2"), sk))
    print(tf, "hazır", f"{time.time()-t0:.0f}s", flush=True)
    isler = [dict(zip(IZGARA, v)) for v in itertools.product(*IZGARA.values())]
    isler = [p for p in isler if not (p["cikis"] == "hedef" and p["kismi"])]
    with get_context("fork").Pool(3) as pool:
        res = pool.map(_is, isler, chunksize=4)
    pickle.dump(res, open(SONUC / f"izgara_{tf}_sk{sk}.pkl", "wb"))
    print("bitti", len(res), f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    izgara(sys.argv[1] if len(sys.argv) > 1 else "4h", float(sys.argv[2]) if len(sys.argv) > 2 else 0.6)
