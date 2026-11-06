"""Pozisyon (maruziyet) serisinden getiri, işlem ve istatistik hesabı.

Kural: pos[t] t kapanışında karar verilir, t+1 AÇILIŞINDA uygulanır.
t+1 günü getirisi = eski pozisyon × (açılış/önceki kapanış − 1) + yeni pozisyon × (kapanış/açılış − 1).
Pozisyon değişimi kadar maliyet (tek yön) düşülür.
"""
import numpy as np
import pandas as pd

ISS = pd.Timestamp("2023-01-01")  # örneklem-dışı başlangıç


def getiri(df, pos, maliyet):
    pos = pos.reindex(df.index).fillna(0.0)
    o, c = df["Open"], df["Close"]
    eski = pos.shift(2).fillna(0.0)   # t-1 kapanışında karar verilen, t'nin açılışına kadar tutulan
    yeni = pos.shift(1).fillna(0.0)   # t-1 kapanışında karar → t açılışında uygulanan
    # gün t: açılışa kadar t-2 kararı (eski) ... dikkat: t-1 kapanışındaki karar t açılışında uygulanır
    gece = o / c.shift(1) - 1
    gun = c / o - 1
    r = eski * gece.fillna(0) + yeni * gun.fillna(0)
    r -= maliyet * (yeni - eski).abs()
    return r


def portfoy_getirisi(dfs, W, maliyet):
    """W: tarih × varlık hedef ağırlık (kapanışta karar). Her varlığın getirisi ayrı hesaplanıp toplanır."""
    tum = None
    for t, df in dfs.items():
        if t not in W:
            continue
        r = getiri(df, W[t].reindex(df.index).ffill().fillna(0.0), maliyet)
        tum = r.rename(t).to_frame() if tum is None else tum.join(r.rename(t), how="outer")
    return tum.fillna(0.0).sum(axis=1)


def islemler(pos):
    """Pozisyonun >0 olduğu kesintisiz dönemleri işlem sayar (giriş/çıkış tarihleri)."""
    p = (pos.fillna(0) > 0).astype(int)
    d = p.diff().fillna(p.iloc[0])
    girisler = list(p.index[d == 1])
    cikislar = list(p.index[d == -1])
    if len(cikislar) < len(girisler):
        cikislar.append(None)
    return list(zip(girisler, cikislar))


def islem_kazanma(df, pos, r):
    """İşlem bazında kazanma oranı: her işlemin süresince birikmiş net getiri > 0 mı."""
    sonuc = []
    eq = (1 + r).cumprod()
    for g, c in islemler(pos):
        a = eq.index.searchsorted(g)  # karar günü; getiri ertesi günden itibaren
        b = eq.index.searchsorted(c) + 1 if c is not None else len(eq) - 1
        if a + 1 >= len(eq):
            continue
        sonuc.append(eq.iloc[min(b, len(eq) - 1)] / eq.iloc[a] - 1)
    return np.array(sonuc)


def istatistik(r, ann=252, bas=None, son=None, pos=None, df=None):
    r = r.loc[bas:son] if (bas or son) else r
    r = r.dropna()
    if len(r) < 20:
        return {}
    eq = (1 + r).cumprod()
    yil = (r.index[-1] - r.index[0]).days / 365.25
    out = {
        "toplam": eq.iloc[-1] - 1,
        "CAGR": eq.iloc[-1] ** (1 / yil) - 1 if eq.iloc[-1] > 0 else -1,
        "maxDD": (eq / eq.cummax() - 1).min(),
        "Sharpe": r.mean() / r.std() * np.sqrt(ann) if r.std() > 0 else np.nan,
    }
    if pos is not None:
        p = pos.reindex(r.index).fillna(0)
        out["piyasada"] = (p > 0).mean()
        if df is not None:
            k = islem_kazanma(df.loc[r.index[0]:r.index[-1]], p, r)
            out["islem"] = len(k)
            out["KO"] = (k > 0).mean() if len(k) else np.nan
    return out


def donemler(r, ann, pos=None, df=None):
    return {
        "2015-22 (IS)": istatistik(r, ann, None, ISS - pd.Timedelta(days=1), pos, df),
        "2023-26 (OOS)": istatistik(r, ann, ISS, None, pos, df),
        "2020-26": istatistik(r, ann, "2020-01-01", None, pos, df),
    }
