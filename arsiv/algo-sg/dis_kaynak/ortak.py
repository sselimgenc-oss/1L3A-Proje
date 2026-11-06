"""Dış depo stratejileri için ortak değerlendirme araçları.

Tüm stratejiler aynı kurallarla ölçülür:
- Maliyet: taraf başına %0.07 (komisyon + kayma), funding pozisyon yönüne göre.
- Karar mum kapanışında, pozisyon bir sonraki mumda taşınır (ileriye bakma yok).
- Sermaye bileşiksiz: günlük getiri = başlangıç sermayesinin oranı.
- Dönemler: IS 2020-2023, OOS 2024-2026, 2022 ayı yılı ayrıca; stres evreni (20 eski/delist coin).
"""
import os, sys, glob
import numpy as np, pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algo import data as D

COST = 0.0007
ROOTS = {"ana": os.path.join(os.path.dirname(__file__), "..", "data"),
         "stres": os.path.join(os.path.dirname(__file__), "..", "data_extra")}
IS_END = pd.Timestamp("2024-01-01", tz="UTC")
Y22 = (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC"))
_CACHE = {}


def semboller(evren):
    return sorted(os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ROOTS[evren], "1h", "*.csv.gz")))


GEL = os.path.join(os.path.dirname(__file__), "..", "data_gel", "1d")
GEL_GRUP = {"mag7": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"],
            "bist10": ["ASELS_IS", "THYAO_IS", "GARAN_IS", "KCHOL_IS", "AKBNK_IS", "BIMAS_IS", "ISCTR_IS", "TUPRS_IS", "YKBNK_IS", "FROTO_IS"],
            "emtia": ["GC_F", "CL_F", "BZ_F"]}


def gel_barlar():
    """Geleneksel evren (günlük, işlem günleri): Mag7 + BIST 10 (USDTRY ile dolara çevrilmiş) + altın/petrol. Funding yok."""
    if ("gel", "1D") in _CACHE:
        return _CACHE[("gel", "1D")]
    def oku(ad):
        d = pd.read_csv(os.path.join(GEL, f"{ad}.csv.gz"))
        d.index = pd.to_datetime(d["ts"], unit="ms", utc=True).dt.floor("1D")
        d = d[~d.index.duplicated()].sort_index()
        return d[["open", "high", "low", "close", "volume", "quote_volume"]].astype(float)
    kur = oku("USDTRY_X")["close"]
    out = {}
    for g, syms in GEL_GRUP.items():
        for s in syms:
            b = oku(s)
            if g == "bist10":
                k = kur.reindex(b.index, method="ffill")
                for c in ("open", "high", "low", "close"):
                    b[c] = b[c] / k
                b["quote_volume"] = b["quote_volume"] / k
            b = b[(b["close"] > 0) & b["close"].notna()]
            out[s] = b
    fund = {s: pd.Series(0.0, index=b.index) for s, b in out.items()}
    _CACHE[("gel", "1D")] = (out, fund)
    return out, fund


def barlar(evren, tf="1D"):
    """{sembol: ohlcv DataFrame} ve {sembol: bar başına funding toplamı}."""
    key = (evren, tf)
    if key in _CACHE:
        return _CACHE[key]
    if evren == "gel":
        if tf not in ("1D",):
            raise ValueError("geleneksel evrende yalnız günlük veri var")
        return gel_barlar()
    D.ROOT = ROOTS[evren]
    out, fund = {}, {}
    for s in semboller(evren):
        h = D.load_1h(s)
        f = D.load_funding(s)
        f = (f if f is not None else pd.Series(dtype=float)).reindex(h.index).fillna(0.0)
        if tf == "1h":
            b, fb = h, f
        else:
            b = D.resample(h, tf)
            fb = f.resample(tf, label="left", closed="left").sum().reindex(b.index).fillna(0.0)
        out[s], fund[s] = b, fb
    _CACHE[key] = (out, fund)
    return out, fund


def panel(bars, col="close"):
    return pd.DataFrame({s: b[col] for s, b in bars.items()})


# ---------------------------------------------------------------- metrikler
def ozet(gunluk, islemler=None, bas=None, bit=None):
    """gunluk: günlük getiri serisi (sermaye oranı). islemler: işlem net getirileri (Series, index=kapanış zamanı)."""
    g = gunluk
    if bas is not None:
        g = g[g.index >= bas]
    if bit is not None:
        g = g[g.index < bit]
    if len(g) < 20:
        return None
    eq = g.cumsum()
    dd = (eq - eq.cummax()).min()
    yil = g.mean() * 365
    sh = g.mean() / g.std() * np.sqrt(365) if g.std() > 0 else np.nan
    r = {"yillik_%": 100 * yil, "dd_%": 100 * dd, "sharpe": sh, "mar": (yil / -dd) if dd < 0 else np.nan}
    if islemler is not None:
        t = islemler
        if bas is not None:
            t = t[t.index >= bas]
        if bit is not None:
            t = t[t.index < bit]
        k, z = t[t > 0].sum(), -t[t < 0].sum()
        r.update({"islem": len(t), "wr_%": 100 * (t > 0).mean() if len(t) else np.nan,
                  "pf": k / z if z > 0 else np.nan, "ort_islem_%": 100 * t.mean() if len(t) else np.nan})
    return r


def donemler(gunluk, islemler=None):
    return {"TUM": ozet(gunluk, islemler), "IS": ozet(gunluk, islemler, bit=IS_END),
            "OOS": ozet(gunluk, islemler, bas=IS_END), "2022": ozet(gunluk, islemler, *Y22)}


# ---------------------------------------------------------------- pozisyon tabanlı (coin başına)
def pozisyon_degerlendir(pos, bars, fund, cost=COST):
    """pos: {sembol: Series(-1..1)} kapanışta karar. Her coin eşit sermaye dilimi (1/N mevcut coin).
    Döner: günlük portföy getirisi, işlem getirileri (Series)."""
    pnl_cols, trades = {}, []
    for s, p in pos.items():
        b = bars[s]
        p = p.reindex(b.index).fillna(0.0).astype(float)
        ret = b["close"].pct_change().shift(-1).fillna(0.0)  # t -> t+1
        f = fund[s].shift(-1).fillna(0.0)                    # t+1 mumundaki funding
        turn = (p - p.shift(1).fillna(0.0)).abs()
        pnl = p * ret - cost * turn - p * f
        pnl_cols[s] = pnl.shift(1).fillna(0.0)               # gerçekleşme zamanı: t+1
        # işlemler: sabit sıfırdan farklı yön koşuları
        sgn = np.sign(p)
        grp = (sgn != sgn.shift(1)).cumsum()
        df = pd.DataFrame({"sgn": sgn, "p": p.abs(), "brut": p * ret - p * f, "grp": grp})
        df = df[df["sgn"] != 0]
        if len(df):
            g = df.groupby("grp")
            # işlem başına net: brüt - giriş maliyeti - çıkış maliyeti (pozisyon büyüklüğüne göre normalize)
            buyukluk = g["p"].max()
            tr = (g["brut"].sum() - cost * g["p"].first() - cost * g["p"].last()) / buyukluk
            end = g.apply(lambda x: x.index[-1])
            trades.append(pd.Series(tr.values, index=pd.DatetimeIndex(end.values).tz_localize("UTC")))
    P = pd.DataFrame(pnl_cols)
    avail = pd.DataFrame({s: bars[s]["close"].notna() for s in pos}).reindex(P.index).fillna(False)
    n = avail.sum(axis=1).replace(0, np.nan)
    port = (P.sum(axis=1) / n).fillna(0.0)
    gunluk = port.resample("1D").sum()
    tr = pd.concat(trades).sort_index() if trades else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    return gunluk, tr


# ---------------------------------------------------------------- ağırlık tabanlı (kesitsel portföy)
def agirlik_degerlendir(W, bars, fund, cost=COST):
    """W: DataFrame(zaman x sembol) hedef ağırlıklar (brüt toplam ≤ 1), kapanışta karar.
    İşlem = bir varlığın bir tutuş dönemindeki katkısı (ağırlığa göre normalize)."""
    C = panel(bars).reindex(W.index)
    R = C.pct_change().shift(-1).fillna(0.0)
    F = pd.DataFrame(fund).reindex(W.index).fillna(0.0).shift(-1).fillna(0.0)
    W = W.fillna(0.0)
    turn = (W - W.shift(1).fillna(0.0)).abs()
    pnl = (W * R - cost * turn - W * F).sum(axis=1).shift(1).fillna(0.0)
    gunluk = pnl.resample("1D").sum()
    trades = []
    for s in W.columns:
        w = W[s]
        sgn = np.sign(w)
        grp = (sgn != sgn.shift(1)).cumsum()
        df = pd.DataFrame({"sgn": sgn, "r": sgn * R[s] - F[s] * sgn, "grp": grp})
        df = df[df["sgn"] != 0]
        if len(df):
            g = df.groupby("grp")
            tr = g["r"].sum() - 2 * cost
            end = g.apply(lambda x: x.index[-1])
            trades.append(pd.Series(tr.values, index=pd.DatetimeIndex(end.values).tz_localize("UTC")))
    tr = pd.concat(trades).sort_index() if trades else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    return gunluk, tr


def tablo_satiri(ad, sonuc_ana, sonuc_stres):
    """Rapor satırı için sözlük."""
    a, s = sonuc_ana, sonuc_stres
    def g(d, k):
        return np.nan if d is None else d.get(k, np.nan)
    return {"strateji": ad,
            "islem": g(a["TUM"], "islem"), "wr": g(a["TUM"], "wr_%"),
            "pf_is": g(a["IS"], "pf"), "pf_oos": g(a["OOS"], "pf"), "pf_2022": g(a["2022"], "pf"),
            "yil_is": g(a["IS"], "yillik_%"), "yil_oos": g(a["OOS"], "yillik_%"), "yil_2022": g(a["2022"], "yillik_%"),
            "sh_is": g(a["IS"], "sharpe"), "sh_oos": g(a["OOS"], "sharpe"), "dd": g(a["TUM"], "dd_%"),
            "pf_stres": g(s["TUM"], "pf") if s else np.nan, "sh_stres": g(s["TUM"], "sharpe") if s else np.nan,
            "dd_stres": g(s["TUM"], "dd_%") if s else np.nan}
