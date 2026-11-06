"""Nedensel (causal) swing tepe/dip tespiti.

Kural: bir pivot ancak ONAY mumunda bilinir. Fraktal pivotta onay, pivot mumunun
sağında `k` mum oluştuktan sonradır (onay indeksi = pivot indeksi + k). Zigzag'da onay,
fiyatın ATR tabanlı eşik kadar ters yöne gitmesiyle olur. Sonuç tablosunun t. satırı SADECE
t. mum kapanışına kadar bilinen pivotları içerir; yani `tablo.iloc[:n]`,
`pivot_tablosu(mumlar.iloc[:n])` ile aynıdır (lookahead yok).

Dönen DataFrame (mumlarla aynı indeks; indeksler 0-tabanlı POZİSYON, float, yoksa NaN):
  son_tepe_fiyat, son_tepe_idx, son_tepe_onay_idx
  onceki_tepe_fiyat, onceki_tepe_idx
  son_dip_fiyat, son_dip_idx, son_dip_onay_idx
  onceki_dip_fiyat, onceki_dip_idx
  yeni_tepe, yeni_dip   (bool: bu mumda yeni pivot ONAYLANDI)
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g

_KOLONLAR = ["son_tepe_fiyat", "son_tepe_idx", "son_tepe_onay_idx",
             "onceki_tepe_fiyat", "onceki_tepe_idx",
             "son_dip_fiyat", "son_dip_idx", "son_dip_onay_idx",
             "onceki_dip_fiyat", "onceki_dip_idx"]


def _tur_serileri(n: int, onay: np.ndarray, pidx: np.ndarray, fiyat: np.ndarray):
    """Onay indeksine göre sıralı olaylardan son/önceki serilerini üretir (ffill mantığı)."""
    sayac = np.searchsorted(onay, np.arange(n), side="right")  # t anında onaylanmış olay sayısı
    son_f = np.full(n, np.nan); son_i = np.full(n, np.nan); son_o = np.full(n, np.nan)
    onc_f = np.full(n, np.nan); onc_i = np.full(n, np.nan)
    var = sayac >= 1
    son_f[var] = fiyat[sayac[var] - 1]
    son_i[var] = pidx[sayac[var] - 1]
    son_o[var] = onay[sayac[var] - 1]
    var2 = sayac >= 2
    onc_f[var2] = fiyat[sayac[var2] - 2]
    onc_i[var2] = pidx[sayac[var2] - 2]
    yeni = np.zeros(n, dtype=bool)
    yeni[onay[onay < n]] = True
    return son_f, son_i, son_o, onc_f, onc_i, yeni


def _tablo(index, tepe, dip) -> pd.DataFrame:
    """tepe/dip: (onay_idx, pivot_idx, fiyat) dizileri; onay_idx artan sıralı."""
    n = len(index)
    sf, si, so, of_, oi, yt = _tur_serileri(n, *tepe)
    df_, di, do, odf, odi, yd = _tur_serileri(n, *dip)
    t = pd.DataFrame({
        "son_tepe_fiyat": sf, "son_tepe_idx": si, "son_tepe_onay_idx": so,
        "onceki_tepe_fiyat": of_, "onceki_tepe_idx": oi,
        "son_dip_fiyat": df_, "son_dip_idx": di, "son_dip_onay_idx": do,
        "onceki_dip_fiyat": odf, "onceki_dip_idx": odi,
    }, index=index)
    t["yeni_tepe"] = yt
    t["yeni_dip"] = yd
    return t


def fraktal_pivotlar(yuksek: pd.Series, dusuk: pd.Series, k: int = 3) -> pd.DataFrame:
    """Fraktal pivot: tepe = solundaki k mumdan KESIN yüksek, sağındaki k mumdan yüksek/eşit.
    Dip aynasıdır. Onay: pivot mumu + k (yani t anında t-k. mum değerlendirilir)."""
    if k < 1:
        raise ValueError("k >= 1 olmalı")
    y, d = yuksek.astype(float), dusuk.astype(float)
    n = len(y)
    merkez_y, merkez_d = y.shift(k), d.shift(k)
    sol_max = y.shift(k + 1).rolling(k, min_periods=k).max()
    sag_max = y.rolling(k, min_periods=k).max()          # t-k+1 .. t
    sol_min = d.shift(k + 1).rolling(k, min_periods=k).min()
    sag_min = d.rolling(k, min_periods=k).min()
    tepe_m = ((merkez_y > sol_max) & (merkez_y >= sag_max)).to_numpy()
    dip_m = ((merkez_d < sol_min) & (merkez_d <= sag_min)).to_numpy()
    o_t = np.flatnonzero(tepe_m)
    o_d = np.flatnonzero(dip_m)
    tepe = (o_t, o_t - k, y.to_numpy()[o_t - k] if len(o_t) else np.array([]))
    dip = (o_d, o_d - k, d.to_numpy()[o_d - k] if len(o_d) else np.array([]))
    return _tablo(y.index, tepe, dip)


def zigzag_pivotlar(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series,
                    atr_periyot: int = 14, esik_k: float = 2.0) -> pd.DataFrame:
    """Nedensel zigzag. Eşik = esik_k * ATR(t) (ATR-yüzdesi: eşik/fiyat = esik_k*ATR/fiyat).
    Yukarı bacakta ekstrem tepe izlenir; fiyat ekstremden eşik kadar düşerse tepe ONAYLANIR
    (o mumda) ve bacak aşağı döner. Dip aynası. ATR hazır olmadan başlamaz."""
    yu, du = yuksek.to_numpy(float), dusuk.to_numpy(float)
    a = g.atr(yuksek, dusuk, kapanis, atr_periyot).to_numpy()
    n = len(yu)
    tepeler, dipler = [], []   # (onay, pidx, fiyat)
    yon = 0
    ust_f = alt_f = np.nan
    ust_i = alt_i = -1
    basladi = False
    for t in range(n):
        if np.isnan(a[t]):
            continue
        esik = esik_k * a[t]
        if not basladi:
            ust_f, ust_i, alt_f, alt_i = yu[t], t, du[t], t
            basladi = True
            continue
        if yon == 0:
            if yu[t] > ust_f:
                ust_f, ust_i = yu[t], t
            if du[t] < alt_f:
                alt_f, alt_i = du[t], t
            if yu[t] - alt_f >= esik and alt_i < t:
                dipler.append((t, alt_i, alt_f)); yon = 1; ust_f, ust_i = yu[t], t
            elif ust_f - du[t] >= esik and ust_i < t:
                tepeler.append((t, ust_i, ust_f)); yon = -1; alt_f, alt_i = du[t], t
        elif yon == 1:
            if yu[t] > ust_f:
                ust_f, ust_i = yu[t], t
            elif ust_f - du[t] >= esik:
                tepeler.append((t, ust_i, ust_f)); yon = -1; alt_f, alt_i = du[t], t
        else:
            if du[t] < alt_f:
                alt_f, alt_i = du[t], t
            elif yu[t] - alt_f >= esik:
                dipler.append((t, alt_i, alt_f)); yon = 1; ust_f, ust_i = yu[t], t

    def paketle(liste):
        if not liste:
            return np.array([], dtype=int), np.array([], dtype=int), np.array([])
        o, p, f = zip(*liste)
        return np.array(o, dtype=int), np.array(p, dtype=int), np.array(f, dtype=float)
    return _tablo(yuksek.index, paketle(tepeler), paketle(dipler))


def pivot_tablosu(mumlar: pd.DataFrame, yontem: str = "fraktal", k: int = 3,
                  atr_periyot: int = 14, esik_k: float = 2.0) -> pd.DataFrame:
    """Strateji kısayolu: yontem "fraktal" (k) veya "zigzag" (atr_periyot, esik_k)."""
    if yontem == "fraktal":
        return fraktal_pivotlar(mumlar["yuksek"], mumlar["dusuk"], k)
    if yontem == "zigzag":
        return zigzag_pivotlar(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], atr_periyot, esik_k)
    raise ValueError(f"Bilinmeyen pivot yöntemi: {yontem}")


def sinyal_cercevesi(index, yon: np.ndarray, stop: np.ndarray, hedef: np.ndarray) -> pd.DataFrame:
    """Swing formasyon stratejileri için ortak sinyal DataFrame'i (cikis=False)."""
    return pd.DataFrame({
        "yon": np.asarray(yon, dtype="int64"),
        "stop": np.asarray(stop, dtype=float),
        "hedef": np.asarray(hedef, dtype=float),
        "cikis": np.zeros(len(index), dtype=bool),
    }, index=index)
