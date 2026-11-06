"""Kesitsel momentum (151 Trading Stratejisi, fiyat momentumu / kısa vadeli dönüş) — kripto, günlük, piyasa nötr veya long-only.

Her H günde bir (gün kapanışında, 00:00 UTC) bir önceki ay sonundaki 30 günlük hacim sıralamasında ilk N coin
(kripto_evren, point-in-time), L günlük getiriye / skora göre sıralanır
(son S gün atlanabilir). mod="notr": en güçlü K long, en zayıf K short (brüt 1.0 = 0.5 + 0.5). mod="long": en güçlü K long
(brüt 1.0). mod="ters": kısa vadeli dönüş (en çok düşen K long, en çok yükselen K short). Ağırlık eşit ya da ters oynaklık.
Masraf: portföy devri x maliyet; fonlama: long öder, short alır. Dengeleme günü 0..H-1 kaydırılarak ortalama alınır.
kayma=True (varsayılan, Faz 9): dengelemeler arasında adetler sabit, ağırlıklar fiyatla kayar (canlı uygulama böyle);
kayma=False: ağırlıklar her gün hedefe eşitlenir (masrafsız, eski hesap).

Kullanım: python3 -m backtest.momentum izgara
"""
import itertools, pickle, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks
from .kripto_motor import metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "s2"
KES = pd.Timestamp("2024-01-01")
MALIYET = 0.0007
VOL_TABAN = 0.01     # ters oynaklık ağırlığında günlük oynaklık alt sınırı (bayat/düz fiyatlı coin tek tarafı ele geçirmesin)


def gunluk_panel(V=None):
    """1S T x N dizilerinden günlük panel: kapanış (00:00 UTC), fonlama toplamı, ay hacim sırası."""
    if V is None:
        V = ks.yukle()
    z = V["zaman"]
    C = pd.DataFrame(V["C"], index=z, columns=V["semboller"])
    gun = z.floor("1D")
    son = C.groupby(gun).last()                               # gün içindeki son 1S kapanışı = gün kapanışı
    say = C.notna().groupby(gun).sum()
    son[say < 20] = np.nan                                    # eksik gün
    F = pd.DataFrame(V["FUND"], index=z, columns=V["semboller"]).groupby(gun).sum()
    O = pd.DataFrame(V["ONC"], index=z, columns=V["semboller"]).groupby(gun).last()
    Hd = pd.DataFrame(V["H"], index=z, columns=V["semboller"]).groupby(gun).max().where(son.notna())
    Ld = pd.DataFrame(V["L"], index=z, columns=V["semboller"]).groupby(gun).min().where(son.notna())
    return dict(C=son, H=Hd, L=Ld, F=F.reindex(son.index).fillna(0), ONC=O.reindex(son.index).fillna(999))


def agirliklar(D, p, kaydir=0):
    """Dengeleme günlerindeki hedef ağırlıklar (gün x coin), aradaki günlerde sabit tutulur."""
    C = D["C"]; L, S, K, N, H = p["L"], p["S"], p["K"], p["N"], p["H"]
    rr = C.pct_change()
    vol = rr.rolling(30, min_periods=20).std()
    skor = p.get("skor", "getiri")
    if skor == "getiri":                        # 151 §3.1: birikimli getiri (son S gün atlanır)
        r = C.shift(S) / C.shift(L) - 1
    elif skor == "risk":                        # 151 §3.1: riske göre düzeltilmiş ortalama getiri (ort / sigma)
        x = rr.shift(S).rolling(L - S, min_periods=max(5, (L - S) // 2))
        r = x.mean() / x.std()
    elif skor == "artik":                       # 151 §3.7 uyarlaması: BTC faktörüne göre artık getiri (ort / sigma)
        b = rr["BTCUSDT"]
        beta = rr.rolling(90, min_periods=60).cov(b).div(b.rolling(90, min_periods=60).var(), axis=0)
        e = (rr - beta.shift(1).mul(b, axis=0)).shift(S).rolling(L - S, min_periods=max(5, (L - S) // 2))
        r = e.mean() / e.std()
    elif skor == "ibs":                         # 151 §4.4: IBS = (C-L)/(H-L); düşük = ucuz (mod="ters" ile)
        r = (C - D["L"]) / (D["H"] - D["L"]).replace(0, np.nan)
    gg = max(L + 30, p.get("gecmis_gun", 0))
    gecmis = C.notna().rolling(gg, min_periods=gg).sum() >= gg            # yeterli geçmiş (yeni listelenenler hariç)
    evren = (D["ONC"] < N) & gecmis & C.notna()
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    gunler = C.index[(np.arange(len(C)) % H) == kaydir]
    for d in gunler:
        e = evren.loc[d]
        x = r.loc[d][e].dropna()
        if len(x) < 2 * K:
            continue
        x = x.sort_values()
        guclu, zayif = x.index[-K:], x.index[:K]
        if p["mod"] == "ters":
            guclu, zayif = zayif, guclu
        def w(sec):
            if p["agirlik"] == "ters_oyn":
                v = 1 / vol.loc[d, sec].clip(lower=VOL_TABAN)
                return v / v.sum()
            return pd.Series(1.0 / len(sec), index=sec)
        if p["mod"] == "long":
            W.loc[d, guclu] = w(guclu).values
        else:
            W.loc[d, guclu] = 0.5 * w(guclu).values
            W.loc[d, zayif] = -0.5 * w(zayif).values
    dengeleme = pd.Series(False, index=C.index); dengeleme[gunler] = True
    W.loc[~dengeleme.to_numpy()] = np.nan
    W = W.ffill().fillna(0.0)
    if p.get("btc_filtre") and p["mod"] == "long":            # BTC 50 günlük ortalamanın altındaysa nakit
        b = C["BTCUSDT"]; ok = (b > b.rolling(50).mean()).shift(0).fillna(False)
        W = W.mul(ok.astype(float), axis=0)
    return W


def getiri(D, W, maliyet=MALIYET, gecikme=0, bacak=None):
    """d kapanışındaki ağırlıklarla d -> d+1 getirisi; devir masrafı ve fonlama dahil.
    gecikme: işlem kaç gün geç yapılır; bacak: 'long' / 'short' yalnız o tarafın katkısı."""
    C = D["C"]
    if gecikme:
        W = W.shift(gecikme).fillna(0.0)
    if bacak == "long":
        W = W.clip(lower=0)
    elif bacak == "short":
        W = W.clip(upper=0)
    r1 = (C.shift(-1) / C - 1).fillna(0.0)                    # delist: fiyat yoksa getiri 0
    brut = (W * r1).sum(axis=1)
    devir = (W - W.shift(1).fillna(0)).abs().sum(axis=1)
    fon = (W * D["F"].shift(-1).fillna(0)).sum(axis=1)        # long (w>0) fonlama öder
    net = brut - devir * maliyet - fon
    return net.shift(1).fillna(0.0)                           # getiri d+1 tarihine yazılır


def ozet(r):
    bos = pd.DataFrame({"R": []})
    e = (1 + r).cumprod(); m = metrik(e, bos)
    ei = e[e.index < KES]; eo = e[e.index >= KES]
    mi = metrik(ei / ei.iloc[0], bos); mo = metrik(eo / eo.iloc[0], bos)
    y = e.resample("YE").last(); yil = 100 * (y / y.shift(1).fillna(1) - 1)
    gun = r[r != 0]
    return dict(cagr=m["cagr"], dd=m["maxdd"], sh=m["sharpe"], cal=m["calmar"], is_sh=mi["sharpe"], oos_sh=mo["sharpe"],
                oos_cagr=mo["cagr"], oos_dd=mo["maxdd"], gun_kazanma=100 * (gun > 0).mean(),
                yillar=dict(zip(y.index.year, np.round(yil.values, 1))))


def getiri_kayma(D, W, maliyet=MALIYET, gecikme=0, bacak=None):
    """Dengeleme günlerinde hedefe gidilir (devir masrafı), aradaki günlerde adetler sabit: ağırlıklar
    w_i <- w_i (1 + r_i) / (1 + r_portföy) ile kayar. Fonlama ve gün hizalaması getiri() ile aynı."""
    C = D["C"]
    if gecikme:
        W = W.shift(gecikme).fillna(0.0)
    if bacak == "long":
        W = W.clip(lower=0)
    elif bacak == "short":
        W = W.clip(upper=0)
    hedef = W.to_numpy(); dg = np.r_[True, (np.abs(np.diff(hedef, axis=0)).sum(axis=1) > 0)]
    dg &= np.abs(hedef).sum(axis=1) > 0
    r1 = (C.shift(-1) / C - 1).fillna(0.0).to_numpy()
    F1 = D["F"].shift(-1).fillna(0).to_numpy()
    w = np.zeros(hedef.shape[1]); net = np.zeros(len(C))
    for t in range(len(C)):
        devir = 0.0
        if dg[t]:
            devir = np.abs(hedef[t] - w).sum(); w = hedef[t].copy()
        pr = (w * r1[t]).sum() - (w * F1[t]).sum() - devir * maliyet
        net[t] = pr
        if pr > -1:
            w = w * (1 + r1[t]) / (1 + pr)
    return pd.Series(net, index=C.index).shift(1).fillna(0.0)


def calistir(D, p):
    """H dengeleme kaydırmasının ortalaması (sermaye eşit bölünür)."""
    fn = getiri_kayma if p.get("kayma", True) else getiri
    rs = [fn(D, agirliklar(D, p, k), p.get("maliyet", MALIYET), p.get("gecikme", 0), p.get("bacak"))
          for k in range(p["H"])]
    return pd.concat(rs, axis=1).mean(axis=1)


IZGARA = [dict(mod=m, N=N, L=L, S=S, K=K, H=H, agirlik=a)
          for m in ("notr", "long", "ters") for N in (15, 30) for L in (3, 7, 14, 30, 60, 90) for S in (0, 1)
          for K in (3, 5) for H in (7, 14) for a in ("esit", "ters_oyn")]


_D = _KGT = None


def _is(p):
    r = calistir(_D, p)
    o = ozet(r); al = pd.concat([r, _KGT], axis=1).dropna(); o["kor"] = al.iloc[:, 0].corr(al.iloc[:, 1])
    return p, o, r


def izgara(isler=None, ad="momentum_izgara"):
    global _D, _KGT
    from multiprocessing import get_context
    SONUC.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    _D = gunluk_panel(); print("panel", _D["C"].shape, f"{time.time()-t0:.0f}s", flush=True)
    _KGT = pd.read_pickle(Path(__file__).resolve().parent.parent / "sonuclar" / "kripto" / "getiri_v3_topluluk.pkl")
    isler = isler or IZGARA
    res = []
    with get_context("fork").Pool(4) as pool:
        for i, x in enumerate(pool.imap_unordered(_is, isler, chunksize=4)):
            res.append(x)
            if (i + 1) % 50 == 0:
                print(i + 1, "/", len(isler), f"{time.time()-t0:.0f}s", flush=True)
                pickle.dump(res, open(SONUC / f"{ad}.pkl", "wb"))
    pickle.dump(res, open(SONUC / f"{ad}.pkl", "wb"))
    print("bitti", f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    izgara()
