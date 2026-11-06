"""Day trade / scalp stratejileri için ortak yardımcılar (seans, gün sonu, günlük seviye, çerçeve).

Mum indeksi = mumun AÇILIŞ zamanı (UTC). Seans = `seans_saat` (UTC saat, ondalık olabilir: 13.5 = 13:30)
anında başlayan 24 saatlik dilim; varsayılan 0.0 = UTC gün başı (kripto 7/24).
"""
import numpy as np
import pandas as pd


def _gun_no(zaman: pd.DatetimeIndex, seans_saat: float) -> np.ndarray:
    kaydirilmis = zaman - pd.Timedelta(hours=float(seans_saat))
    gun = kaydirilmis.floor("D")
    if gun.tz is not None:
        gun = gun.tz_localize(None)
    return gun.values.astype("datetime64[D]").astype("int64")


def seans_kimligi(index: pd.DatetimeIndex, seans_saat: float = 0.0) -> np.ndarray:
    """Her mumun ait olduğu seansın kimliği (tam sayı gün numarası)."""
    return _gun_no(index, seans_saat)


def seans_son_mumu(index: pd.DatetimeIndex, seans_saat: float = 0.0) -> np.ndarray:
    """Mumun KAPANIŞ anı bir sonraki seansa denk geliyorsa True (= seansın son mumu).

    Mum süresi yalnız geçmişten kestirilir (şimdiye kadarki en küçük mum aralığı); ilk mum için False.
    Böylece sonuç, serinin geleceğine bağlı değildir (lookahead yok).
    """
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kapanis_zamani = index + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    return (_gun_no(kapanis_zamani, seans_saat) != _gun_no(index, seans_saat)) & gecerli


def onceki_seans_hlc(mumlar: pd.DataFrame, seans: np.ndarray) -> pd.DataFrame:
    """Her mum için bir ÖNCEKİ (tamamen kapanmış) seansın yüksek/düşük/kapanışı (h, l, c)."""
    g = mumlar.groupby(seans)
    ozet = pd.DataFrame({"h": g["yuksek"].max(), "l": g["dusuk"].min(), "c": g["kapanis"].last()}).shift(1)
    return pd.DataFrame({k: ozet[k].reindex(seans).to_numpy() for k in ("h", "l", "c")}, index=mumlar.index)


def cerceve(mumlar: pd.DataFrame, long_ok, short_ok, stop_l, stop_s,
            hedef_l=None, hedef_s=None, cikis=None,
            gun_sonu: bool = False, seans_saat: float = 0.0) -> pd.DataFrame:
    """yon/stop/hedef/cikis çerçevesi. Stop yanlış tarafta (veya NaN) ise sinyal düşer.
    gun_sonu=True: seansın son mumunda yeni giriş yok ve cikis=True."""
    idx = mumlar.index
    kap = mumlar["kapanis"]

    def seri(x):
        return x if isinstance(x, pd.Series) else pd.Series(x, index=idx, dtype="float64")

    long_ok = seri(long_ok).fillna(False).astype(bool)
    short_ok = seri(short_ok).fillna(False).astype(bool)
    stop_l, stop_s = seri(stop_l), seri(stop_s)
    long_ok &= stop_l.notna() & (stop_l < kap)
    short_ok &= stop_s.notna() & (stop_s > kap) & ~long_ok
    son = pd.Series(False, index=idx)
    if gun_sonu:
        son = pd.Series(seans_son_mumu(idx, seans_saat), index=idx)
        long_ok &= ~son
        short_ok &= ~son
    yon = pd.Series(0, index=idx, dtype="int64")
    yon[long_ok] = 1
    yon[short_ok] = -1
    stop = pd.Series(np.nan, index=idx)
    stop[long_ok] = stop_l[long_ok]
    stop[short_ok] = stop_s[short_ok]
    hedef = pd.Series(np.nan, index=idx)
    if hedef_l is not None:
        hedef[long_ok] = seri(hedef_l)[long_ok]
    if hedef_s is not None:
        hedef[short_ok] = seri(hedef_s)[short_ok]
    c = pd.Series(False, index=idx) if cikis is None else seri(cikis).fillna(False).astype(bool)
    return pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef, "cikis": (c | son).astype(bool)})


def gun_sonu_uygula(sig: pd.DataFrame, seans_saat: float = 0.0) -> pd.DataFrame:
    """Hazır bir sinyal çerçevesine gün sonu kuralını ekler (son mumda giriş yok, cikis=True)."""
    son = seans_son_mumu(sig.index, seans_saat)
    s = sig.copy()
    s.loc[son, ["yon"]] = 0
    s.loc[son, ["stop", "hedef"]] = np.nan
    s["cikis"] = (s["cikis"].astype(bool) | son).astype(bool)
    s["yon"] = s["yon"].astype("int64")
    return s
