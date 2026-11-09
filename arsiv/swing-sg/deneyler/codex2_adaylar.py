"""Codex'in ikinci listesinden (derinlemesine araştırma) kod denetimini geçen 3 fikrin bizim çerçevede testi.

D1: QQQ-ML (remy-rm511) — 11 fiyat özelliği, 5 gün sonrası yön, yıllık ileri yürüyen (walk-forward) eğitim,
    5 gün arınma (purge); olasılık eşiği yalnızca 2019-2022 tahminlerinde seçilir. Stop 1 ATR, hedef 2 ATR, en fazla 5 gün.
D2: Bileşik skor (MajidUppal S2) — 10 göstergenin tanh ortalaması, ADX<20 ise 0; skor>0,20 iki gün üst üste.
D3: Gizli boğa uyumsuzluğu (Argus) — ileriye bakma düzeltilmiş: dip ancak 3 mum sonra teyit edilince kullanılır.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deneyler.codex_adaylar import SINIF_TUM, _bos, _paket, satir, sinif_ozet  # noqa: E402
from swing import gostergeler as g  # noqa: E402
from swing.ayarlar import S1, S2, S3, SINIFLAR  # noqa: E402
from swing.calistir import islemler, veriler  # noqa: E402
from swing.motor import calistir  # noqa: E402
from swing.veri import ENDEKS_VERI, MALIYET  # noqa: E402

BIZIM = {"bizim": True, "yon_mod": "ha", "rejim": "ema10"}


# ---------------------------------------------------------------- D1: ML
def ozellikler(df):
    c, h, l = df["Close"], df["High"], df["Low"]
    a = g.atr(df, 14)
    lr = np.log(c).diff()
    X = pd.DataFrame({
        "atr_pct": a / c,
        "d_ma10": c / g.sma(c, 10) - 1, "d_ma20": c / g.sma(c, 20) - 1, "d_ma50": c / g.sma(c, 50) - 1,
        "d_hi20": c / h.rolling(20).max() - 1, "d_lo20": c / l.rolling(20).min() - 1,
        "d_hi55": c / h.rolling(55).max() - 1, "d_lo55": c / l.rolling(55).min() - 1,
        "mom5": c / c.shift(5) - 1, "mom20": c / c.shift(20) - 1,
        "vol10": lr.rolling(10).std(), "vol20": lr.rolling(20).std(),
    }, index=df.index)
    y = (c.shift(-5) > c).astype(float).where(c.shift(-5).notna())
    return X, y


def ml_olasiliklar():
    import lightgbm as lgb
    parca = []
    for ad, (df, sinif) in veriler().items():
        X, y = ozellikler(df)
        X["sinif"] = SINIF_TUM.index(sinif)
        X["y"], X["ad"], X["tarih"] = y, ad, df.index
        parca.append(X.dropna(subset=[c for c in X.columns if c != "y"]))
    D = pd.concat(parca, ignore_index=True)
    feat = [c for c in D.columns if c not in ("y", "ad", "tarih")]
    D["p"] = np.nan
    for yil in range(2019, 2027):
        bas = pd.Timestamp(f"{yil}-01-01")
        tr = D[(D["tarih"] < bas - pd.Timedelta(days=8)) & D["y"].notna()]  # 5 iş günü arınma
        te = D["tarih"].between(bas, pd.Timestamp(f"{yil}-12-31"))
        prm = dict(objective="binary", learning_rate=0.03, num_leaves=15, min_data_in_leaf=200,
                   bagging_fraction=0.8, bagging_freq=1, feature_fraction=0.8, verbose=-1, seed=0)
        m = lgb.train(prm, lgb.Dataset(tr[feat], tr["y"]), num_boost_round=200)
        D.loc[te, "p"] = m.predict(D.loc[te, feat])
    # Eşik: yalnızca 2019-2022 tahminlerinde, 5 gün sonrası ortalama getiriyi en iyi yapan üst dilim
    D["ileri"] = np.nan
    for ad, (df, _) in veriler().items():
        f = (df["Close"].shift(-5) / df["Close"] - 1)
        k = D["ad"] == ad
        D.loc[k, "ileri"] = f.reindex(pd.DatetimeIndex(D.loc[k, "tarih"])).values
    isd = D[D["tarih"] < pd.Timestamp("2023-01-01")].dropna(subset=["p", "ileri"])
    en, esik = -1, 0.5
    for q in (0.5, 0.6, 0.7, 0.8, 0.9):
        t = isd["p"].quantile(q)
        r = isd.loc[isd["p"] > t, "ileri"].mean()
        if r > en:
            en, esik = r, t
    print(f"  ML eşik (IS'te seçildi) = {esik:.3f}, IS 5g ort. getiri {en:.2%}", flush=True)
    return {ad: grp.set_index("tarih")["p"] for ad, grp in D.groupby("ad")}, esik


def d1_ml(df, p):
    c = df["Close"]
    a = g.atr(df, 14)
    pr = p["_p"].reindex(df.index)
    long = pr > p["_esik"]
    return _paket(df, a, long, c - a, _bos(df), p, hedef_R=2.0, max_gun=5)


# ---------------------------------------------------------------- D2: bileşik skor
def _z(x, n=60):
    return (x - x.rolling(n).mean()) / x.rolling(n).std()


def d2_bilesik(df, p):
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    a = g.atr(df, 14)
    _, hist_s, _ = (None, None, None)
    m = g.ema(c, 12) - g.ema(c, 26)
    hist = m - g.ema(m, 9)
    adx, pdi, ndi = g.adx(df, 14)
    vw = (c * v).rolling(20).sum() / v.rolling(20).sum()
    roc10 = c / c.shift(10) - 1
    roc5 = c / c.shift(5) - 1
    e = p.get("_endeks")
    if e is not None:
        ec = e["Close"].reindex(df.index, method="ffill")
        rs = _z((c / c.shift(20)) - (ec / ec.shift(20)))
    else:
        rs = pd.Series(0.0, index=df.index)
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    lo, hi = l.rolling(252, min_periods=120).min(), h.rolling(252, min_periods=120).max()
    bil = pd.concat([
        np.tanh((g.rsi(c, 14) - 50) / 25), np.tanh(_z(hist) / 2), (pdi - ndi) / (pdi + ndi),
        np.tanh(_z(roc10) / 2), np.tanh(_z(c / g.sma(c, 20) - 1) / 2),
        np.tanh(_z(c / vw - 1) / 2).fillna(0), np.tanh(_z(roc5 - roc5.shift(5)) / 2), np.tanh(rs.fillna(0) / 2),
        (2 * (c - lo) / (hi - lo) - 1), np.tanh(((obv - g.sma(obv, 20)) / obv.rolling(20).std()).fillna(0) / 2),
    ], axis=1)
    skor = bil.mean(axis=1)
    skor = skor.where(adx >= 20, 0.0)
    vr = v / g.sma(v, 20)
    skor = (skor * np.where(vr > 1.5, 1.2, np.where(vr < 0.7, 0.8, 1.0))).clip(-1, 1)
    long = (skor > 0.2) & (skor.shift() > 0.2)
    return _paket(df, a, long, c * 0.95, skor <= 0.2, p, max_gun=60)


# ---------------------------------------------------------------- D3: gizli boğa uyumsuzluğu
def d3_gizli_uyumsuzluk(df, p):
    c, l = df["Close"], df["Low"]
    a = g.atr(df, 14)
    r = g.rsi(c, 14)
    lv, rv = l.values, r.values
    n = len(df)
    long = np.zeros(n, bool)
    onceki = None  # (indeks, dip, rsi)
    for t in range(6, n):
        k = t - 3
        if lv[k] == lv[t - 6:t + 1].min():  # dip t günü teyitli (3 mum sonrası görüldü)
            if onceki is not None and k - onceki[0] <= 60 and lv[k] > onceki[1] and rv[k] < onceki[2]:
                long[t] = True
            onceki = (k, lv[k], rv[k])
    long = pd.Series(long, index=df.index) & (c > g.sma(c, 200))
    return _paket(df, a, long, c - 2 * a, _bos(df), p, hedef_R=1.5, max_gun=10)


def calistir_aday(f, p, ekstra=None):
    out = []
    for ad, (df, sinif) in veriler().items():
        q = {**p, "_endeks": ENDEKS_VERI.get(sinif), **((ekstra or {}).get(ad, {}))}
        out += calistir(ad, sinif, df, f(df, q), MALIYET[sinif], f.__name__)
    return out


if __name__ == "__main__":
    mevcut = []
    for s, prm in (("S1_geri_cekilme", S1), ("S2_kirilim", S2), ("S3_asiri_satim", S3)):
        mevcut += islemler(s, prm, SINIFLAR[s])
    print("MEVCUT S1+S2+S3:", satir(mevcut), flush=True)
    olas, esik = ml_olasiliklar()
    ml_ek = {ad: {"_p": s, "_esik": esik} for ad, s in olas.items()}
    kayit = {}
    for f, ek in ((d1_ml, ml_ek), (d2_bilesik, None), (d3_gizli_uyumsuzluk, None)):
        for etk, p in (("ham", {}), ("bizim", BIZIM)):
            if f is d1_ml:
                ek2 = {ad: v for ad, v in ek.items()}
                bos = {ad: {"_p": pd.Series(dtype=float), "_esik": 1.0} for ad in veriler() if ad not in ek2}
                ek2.update(bos)
            else:
                ek2 = None
            tr = calistir_aday(f, p, ek2)
            kayit[(f.__name__, etk)] = tr
            print(f"{f.__name__:20s} {etk:5s}", satir(tr), flush=True)
            print("    ", sinif_ozet(tr), flush=True)
    print("\n== Mevcut sisteme ekleme")
    for (ad, etk), tr in kayit.items():
        print(f"+{ad:20s} {etk:5s}", satir(mevcut + tr), flush=True)
