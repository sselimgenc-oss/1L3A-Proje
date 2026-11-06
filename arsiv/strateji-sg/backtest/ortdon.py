"""Ortalamaya dönüş (kripto, 4S, long + short) — KGT'yi tamamlayacak ikinci strateji adayı.

Giriş (bar kapanışı): long -> kapanış alt Bollinger bandının (20, k) altında ya da RSI(2) < eşik; short simetrik.
Onay (isteğe bağlı, Brooks "sinyal çubuğu"): sinyal mumu yön lehine kapanır (long: kapanış > açılış) ve giriş mumun
tepesinin üstünde bekleyen emirle yapılır; onaysız girişte sonraki açılışta piyasa emri.
Rejim: 'aralik' -> 4S ADX(14) < esik (yatay piyasa, iki yön); 'trend_ici' -> yalnız günlük trend yönünde
(günlük kapanış > EMA50 ve EMA50 yükseliyorsa yalnız long dipler, tersi yalnız short); 'yok' -> filtre yok.
Çıkış: kapanış 20'lik ortalamaya dönünce (long: C > orta), stop = stop_atr x ATR(4S), süre stopu max_bar mum.

Kullanım: python3 -m backtest.ortdon izgara
"""
import pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, gostergeler as g
from .pa_arastirma import yeniden_ornekle
from .kripto_motor import portfoy, metrik
from .epa import ozet, HIZALAMALAR

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "s2"
TF, KAYDIRMALAR = "4h", HIZALAMALAR      # günlük için: "1D", (0, 6, 12, 18)
PORTFOY = dict(evren_n=15, risk=0.005, max_poz=5, max_yon=5, max_pay=0.25, max_brut=1.0, maliyet=0.0007)


def bilesenler(V4):
    T, N = V4["C"].shape
    ad = ("orta", "bb2", "bb25", "bb3", "rsi2", "adx", "d_yon", "atr")
    B = {k: np.full((T, N), np.nan) for k in ad}
    for j in range(N):
        cc = V4["C"][:, j]; ok = ~np.isnan(cc)
        bpd = int(round(86400 / (V4["zaman"][1] - V4["zaman"][0]).total_seconds()))
        if ok.sum() < bpd * 120:
            continue
        i0, i1 = np.argmax(ok), len(cc) - np.argmax(ok[::-1]); sl = slice(i0, i1)
        df = pd.DataFrame({k: V4[K][sl, j] for k, K in (("open", "O"), ("high", "H"), ("low", "L"), ("close", "C"))},
                          index=V4["zaman"][sl]).ffill()
        o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
        m, _, _ = g.bollinger(c, 20, 2.0)
        sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
        B["orta"][sl, j] = m
        B["bb2"][sl, j] = (c - m) / np.where(sd > 0, sd, np.nan)          # z-skoru; eşikler ızgarada
        B["rsi2"][sl, j] = g.rsi(c, 2)
        B["adx"][sl, j] = g.adx(h, l, c, 14)[0]
        B["atr"][sl, j] = g.atr(h, l, c, 14)
        d = ks._htf(df, "1D"); dc = d.close.to_numpy(); e50 = g.ema(dc, 50)
        dy = np.where((dc > e50) & (e50 > np.roll(e50, 3)), 1.0, np.where((dc < e50) & (e50 < np.roll(e50, 3)), -1.0, 0.0))
        dy[:60] = 0
        B["d_yon"][sl, j] = g.htf_hizala(df.index, d, {"y": dy})["y"]
    return B


def diziler(V4, B, p):
    C, O, H, L = V4["C"], V4["O"], V4["H"], V4["L"]
    z = B["bb2"]
    if p["giris"].startswith("bb"):
        k = float(p["giris"][2:])
        up, dn = z < -k, z > k
    else:                                                                # rsi2_<eşik>
        e = float(p["giris"].split("_")[1])
        up, dn = B["rsi2"] < e, B["rsi2"] > 100 - e
    if p["rejim"].startswith("aralik"):
        a = B["adx"] < float(p["rejim"][6:])
        up &= a; dn &= a
    elif p["rejim"] == "trend_ici":
        up &= B["d_yon"] > 0; dn &= B["d_yon"] < 0
    if p["yon"] == 1:
        dn[:] = False
    if p["onay"]:
        up &= C > O; dn &= C < O
    ev = V4["ONC"] < PORTFOY["evren_n"]
    up &= ev; dn &= ev
    SIG = np.where(up, 1.0, np.where(dn, -1.0, 0.0))
    STOP = np.where(SIG != 0, p["stop_atr"] * B["atr"], np.nan)
    GSEV = np.where(up, H * 1.0001, np.where(dn, L * 0.9999, np.nan)) if p["onay"] else None
    CIK = np.where(C > B["orta"], -1.0, np.where(C < B["orta"], 1.0, 0.0))   # ortalamaya dönünce çık
    return SIG, STOP, GSEV, np.nan_to_num(CIK)


def calistir(V4, B, p):
    SIG, STOP, GSEV, CIK = diziler(V4, B, p)
    q = dict(PORTFOY, risk=p.get("risk", PORTFOY["risk"]), maliyet=p.get("maliyet", PORTFOY["maliyet"]), tp1_r=0.0,
             tp1_pay=0.0, be_tp1=False, hedef_r=0.0, max_bar=p["max_bar"], iz_atr=0.0)
    return portfoy(V4, SIG, STOP, np.nan_to_num(B["atr"]), CIK, V4["ONC"], q, GSEV=GSEV)


_D = _KGT = None


def hazirla():
    V = ks.yukle(); D = {}
    for kay in KAYDIRMALAR:
        V4 = yeniden_ornekle(V, TF, kay); D[kay] = (V4, bilesenler(V4)); print("hizalama", kay, flush=True)
    return D


def _is(p):
    rs, ts = [], []
    for kay in KAYDIRMALAR:
        V4, B = _D[kay]; e, t = calistir(V4, B, p)
        rs.append(e.resample("1D").last().pct_change().fillna(0)); ts.append(t)
    o = ozet(rs, ts); r = o.pop("r")
    al = pd.concat([r, _KGT], axis=1).dropna(); o["kor"] = al.iloc[:, 0].corr(al.iloc[:, 1])
    T = pd.concat(ts); o["long_R"] = float(T[T.yon > 0].R.sum()) / 4; o["short_R"] = float(T[T.yon < 0].R.sum()) / 4
    return p, o, r


IZGARA = [dict(rejim=rj, giris=gr, onay=on, stop_atr=sa, max_bar=mb, yon=y)
          for rj in ("aralik20", "aralik25", "trend_ici", "yok") for gr in ("bb2", "bb2.5", "rsi2_10", "rsi2_5")
          for on in (0, 1) for sa in (2.0, 3.0) for mb in (6, 12) for y in (0, 1)]


def izgara(isler=None, ad="ortdon_izgara"):
    global _D, _KGT
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _D = hazirla()
    _KGT = pd.read_pickle(Path(__file__).resolve().parent.parent / "sonuclar" / "kripto" / "getiri_v3_topluluk.pkl")
    isler = isler or IZGARA
    print(len(isler), "kombinasyon", f"{time.time()-t0:.0f}s", flush=True)
    res = []
    with get_context("fork").Pool(3) as pool:
        for i, x in enumerate(pool.imap_unordered(_is, isler, chunksize=2)):
            res.append(x)
            if (i + 1) % 50 == 0:
                print(i + 1, f"{time.time()-t0:.0f}s", flush=True)
                pickle.dump(res, open(SONUC / f"{ad}.pkl", "wb"))
    pickle.dump(res, open(SONUC / f"{ad}.pkl", "wb"))
    print("bitti", f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "1D":
        TF, KAYDIRMALAR = "1D", (0, 6, 12, 18)
        IZGARA = [dict(q, max_bar=mb) for q in IZGARA if q["max_bar"] == 6 for mb in (3, 7)]
        izgara(IZGARA, "ortdon_izgara_1D")
    else:
        izgara()
