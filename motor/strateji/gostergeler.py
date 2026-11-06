"""Teknik göstergeler — saf pandas/numpy. Hepsi nedensel (sadece geçmişe bakar)."""
import numpy as np
import pandas as pd


def sma(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.rolling(periyot, min_periods=periyot).mean()


def ema(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.ewm(span=periyot, adjust=False, min_periods=periyot).mean()


def _wilder(seri: pd.Series, periyot: int) -> pd.Series:
    return seri.ewm(alpha=1.0 / periyot, adjust=False, min_periods=periyot).mean()


def rsi(kapanis: pd.Series, periyot: int = 14) -> pd.Series:
    fark = kapanis.diff()
    kazanc = fark.clip(lower=0.0)
    kayip = (-fark).clip(lower=0.0)
    rs = _wilder(kazanc, periyot) / _wilder(kayip, periyot)
    return 100.0 - 100.0 / (1.0 + rs)


def gercek_aralik(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series) -> pd.Series:
    onceki = kapanis.shift(1)
    parcalar = pd.concat([yuksek - dusuk, (yuksek - onceki).abs(), (dusuk - onceki).abs()], axis=1)
    return parcalar.max(axis=1)


def atr(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, periyot: int = 14) -> pd.Series:
    return _wilder(gercek_aralik(yuksek, dusuk, kapanis), periyot)


def bollinger(kapanis: pd.Series, periyot: int = 20, sapma: float = 2.0) -> pd.DataFrame:
    orta = sma(kapanis, periyot)
    std = kapanis.rolling(periyot, min_periods=periyot).std(ddof=0)
    return pd.DataFrame({"orta": orta, "ust": orta + sapma * std, "alt": orta - sapma * std})


def macd(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, sinyal: int = 9) -> pd.DataFrame:
    m = ema(kapanis, hizli) - ema(kapanis, yavas)
    s = m.ewm(span=sinyal, adjust=False, min_periods=sinyal).mean()
    return pd.DataFrame({"macd": m, "sinyal": s, "histogram": m - s})


def adx(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series, periyot: int = 14) -> pd.DataFrame:
    yukari = yuksek.diff()
    asagi = -dusuk.diff()
    arti_dm = pd.Series(np.where((yukari > asagi) & (yukari > 0), yukari, 0.0), index=kapanis.index)
    eksi_dm = pd.Series(np.where((asagi > yukari) & (asagi > 0), asagi, 0.0), index=kapanis.index)
    a = atr(yuksek, dusuk, kapanis, periyot)
    arti_di = 100.0 * _wilder(arti_dm, periyot) / a
    eksi_di = 100.0 * _wilder(eksi_dm, periyot) / a
    dx = 100.0 * (arti_di - eksi_di).abs() / (arti_di + eksi_di)
    return pd.DataFrame({"adx": _wilder(dx, periyot), "arti_di": arti_di, "eksi_di": eksi_di})


def stokastik(yuksek: pd.Series, dusuk: pd.Series, kapanis: pd.Series,
              k_periyot: int = 14, d_periyot: int = 3) -> pd.DataFrame:
    en_yuksek = yuksek.rolling(k_periyot, min_periods=k_periyot).max()
    en_dusuk = dusuk.rolling(k_periyot, min_periods=k_periyot).min()
    k = 100.0 * (kapanis - en_dusuk) / (en_yuksek - en_dusuk)
    return pd.DataFrame({"k": k, "d": sma(k, d_periyot)})
