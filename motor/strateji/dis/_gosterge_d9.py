"""D9 (atlanan dış stratejilerin kodlanması, B yarısı) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına
kadar olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  cmo, fisher_rsi, rmi, pinball, vfi, kdj, ema_low_high, mum_govde, cekic, ters_cekic, pivot_seviye,
  r_hedefi, art_arda_dusus, ardisik_say
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g


def cmo(kapanis: pd.Series, n: int = 14) -> pd.Series:
    """Chande Momentum Oscillator (-100..100): 100 x (yukarı toplam - aşağı toplam) / (toplam)."""
    d = kapanis.diff()
    yuk = d.clip(lower=0.0).rolling(n, min_periods=n).sum()
    asg = (-d).clip(lower=0.0).rolling(n, min_periods=n).sum()
    toplam = (yuk + asg).where((yuk + asg) != 0)
    return 100.0 * (yuk - asg) / toplam


def fisher_rsi(kapanis: pd.Series, rsi_n: int = 14) -> pd.Series:
    """Fisher RSI (freqtrade yaygın tanımı): x = 0.1 (RSI - 50); (e^2x - 1) / (e^2x + 1) = tanh(x). -1..1."""
    x = 0.1 * (g.rsi(kapanis, rsi_n) - 50.0)
    return np.tanh(x)


def rmi(kapanis: pd.Series, n: int = 14, mom: int = 3) -> pd.Series:
    """Relative Momentum Index: RSI'ın `mom` mumluk momentum ile hesaplanan hali (Wilder düzleştirme)."""
    d = kapanis.diff(mom)
    yuk = d.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    asg = (-d).clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    toplam = (yuk + asg).where((yuk + asg) != 0)
    return 100.0 * yuk / toplam


def pinball(kapanis: pd.Series, n: int = 3) -> pd.Series:
    """Momentum Pinball (Raschke): 1 mumluk değişimin (ROC) n periyotluk RSI'ı."""
    return g.rsi(kapanis.pct_change(), n)


def vfi(yuksek, dusuk, kapanis, hacim, n: int = 130, katsayi: float = 0.2, vmax_k: float = 2.5, std_n: int = 30,
        yumusat: int = 3) -> pd.Series:
    """Volume Flow Indicator (Katsanos). Tipik fiyatın log değişimi eşiği aşarsa hacim +, altında - sayılır."""
    tp = (yuksek + dusuk + kapanis) / 3.0
    inter = np.log(tp).diff()
    vinter = inter.rolling(std_n, min_periods=std_n).std()
    kesim = katsayi * vinter * kapanis
    vave = hacim.rolling(n, min_periods=n).mean().shift(1)
    vc = np.minimum(hacim, vmax_k * vave)
    mf = tp.diff()
    vcp = pd.Series(np.where(mf > kesim, vc, np.where(mf < -kesim, -vc, 0.0)), index=kapanis.index)
    ham = vcp.rolling(n, min_periods=n).sum() / vave
    return ham.ewm(span=yumusat, adjust=False, min_periods=yumusat).mean()


def kdj(yuksek, dusuk, kapanis, n: int = 9) -> pd.DataFrame:
    """KDJ: RSV'nin 1/3 katsayılı düzleştirilmesi (K), K'nın düzleştirilmesi (D), J = 3K - 2D."""
    hh = yuksek.rolling(n, min_periods=n).max()
    ll = dusuk.rolling(n, min_periods=n).min()
    rsv = 100.0 * (kapanis - ll) / (hh - ll).where(hh != ll)
    k = rsv.ewm(alpha=1.0 / 3.0, adjust=False, min_periods=3).mean()
    d = k.ewm(alpha=1.0 / 3.0, adjust=False, min_periods=3).mean()
    return pd.DataFrame({"k": k, "d": d, "j": 3 * k - 2 * d})


def ema_low_high(yuksek, dusuk, n: int = 5) -> pd.DataFrame:
    """freqtrade 'ema_low / ema_high': düşük ve yüksek serilerinin EMA'sı."""
    return pd.DataFrame({"alt": g.ema(dusuk, n), "ust": g.ema(yuksek, n)})


def mum_govde(m: pd.DataFrame) -> pd.DataFrame:
    """govde (mutlak), aralik, ust_fitil, alt_fitil; hepsi o mumun kendi verisi."""
    o, h, l, c = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    return pd.DataFrame({
        "govde": (c - o).abs(), "aralik": h - l,
        "ust_fitil": h - np.maximum(o, c), "alt_fitil": np.minimum(o, c) - l})


def cekic(m: pd.DataFrame, alt_k: float = 2.0, ust_oran: float = 0.1) -> pd.Series:
    """Çekiç: alt fitil >= alt_k x gövde, üst fitil <= ust_oran x aralık, gövde > 0."""
    f = mum_govde(m)
    return (f["govde"] > 0) & (f["alt_fitil"] >= alt_k * f["govde"]) & (f["ust_fitil"] <= ust_oran * f["aralik"])


def ters_cekic(m: pd.DataFrame, ust_k: float = 2.0, alt_oran: float = 0.1) -> pd.Series:
    """Ters çekiç / shooting star: üst fitil >= ust_k x gövde, alt fitil <= alt_oran x aralık, gövde > 0."""
    f = mum_govde(m)
    return (f["govde"] > 0) & (f["ust_fitil"] >= ust_k * f["govde"]) & (f["alt_fitil"] <= alt_oran * f["aralik"])


def pivot_seviye(seri: pd.Series, sol: int, sag: int, tepe: bool) -> pd.Series:
    """Onaylı pivot seviyesi: bir mumun değeri solundaki `sol` ve sağındaki `sag` mumdan uç ise pivot; pivot `sag` mum SONRA
    (onay anında) bilinir ve ondan itibaren ileri taşınır (ffill). Nedensel."""
    n = int(sol) + int(sag) + 1
    pen = seri.rolling(n, min_periods=n).max() if tepe else seri.rolling(n, min_periods=n).min()
    aday = seri.shift(int(sag))
    onay = aday.where(aday == pen)
    return onay.ffill()


def r_hedefi(out: pd.DataFrame, kapanis: pd.Series, r: float) -> pd.DataFrame:
    """Girişlerde hedefi kapanış +/- r x (kapanış - stop) yap (r <= 0: hedef yok)."""
    out = out.copy()
    if r and r > 0:
        m = out["yon"] != 0
        risk = (kapanis - out["stop"]).abs()
        out.loc[m, "hedef"] = (kapanis + out["yon"] * r * risk)[m]
    return out


def ardisik_say(kosul: pd.Series) -> pd.Series:
    """Koşulun art arda True olduğu mum sayısı (False'ta 0). Nedensel."""
    k = kosul.fillna(False).astype(bool)
    grup = (~k).cumsum()
    return k.astype(int).groupby(grup).cumsum()
