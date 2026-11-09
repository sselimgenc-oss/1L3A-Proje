"""Day trade / scalp stratejileri için ortak yardımcılar (seans, gün sonu, günlük seviye, çerçeve).

Mum indeksi = mumun AÇILIŞ zamanı (UTC). Seans = `seans_saat` (UTC saat, ondalık olabilir: 13.5 = 13:30)
anında başlayan 24 saatlik dilim; varsayılan 0.0 = UTC gün başı (kripto 7/24).
Gün sonu (seans_son_mumu): kripto için gün sınırı kuralı; seanslı veride ek olarak bilinen seans kapanışı
(motor/strateji/seans_takvimi.py).
"""
import numpy as np
import pandas as pd

from motor.strateji.seans_takvimi import KRIPTO, seans_kapanis_ani, seans_turu


def _gun_no(zaman: pd.DatetimeIndex, seans_saat: float) -> np.ndarray:
    kaydirilmis = zaman - pd.Timedelta(hours=float(seans_saat))
    gun = kaydirilmis.floor("D")
    if gun.tz is not None:
        gun = gun.tz_localize(None)
    return gun.values.astype("datetime64[D]").astype("int64")


def seans_kimligi(index: pd.DatetimeIndex, seans_saat: float = 0.0) -> np.ndarray:
    """Her mumun ait olduğu seansın kimliği (tam sayı gün numarası)."""
    return _gun_no(index, seans_saat)


def seans_son_mumu(index: pd.DatetimeIndex, seans_saat: float = 0.0, tur: str | None = None) -> np.ndarray:
    """Günün (seansın) son mumu ise True.

    İki koşuldan biri: (1) mumun KAPANIŞ anı bir sonraki seans gününe (`seans_saat` kaydırmalı) denk geliyor (7/24 kripto
    kuralı; kripto için tek koşul, davranış eskisiyle birebir); (2) seanslı piyasada mumun kapanış anı o günün bilinen seans
    kapanışına ulaşıyor/geçiyor (motor/strateji/seans_takvimi.py; ABD hisse, BIST, 24/5 vadeli/CFD hafta ve tatil kapanışı).
    Mum süresi yalnız geçmişten kestirilir (şimdiye kadarki en küçük mum aralığı); ilk mum için False. Karar mumun kendi
    zamanı + sabit takvimden çıkar, sonraki mumun varlığına bakılmaz (lookahead yok). `tur` verilmezse indeksin zaman ayak
    izinden çıkarılır (seans_takvimi.seans_turu).
    """
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kapanis_zamani = index + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    son = (_gun_no(kapanis_zamani, seans_saat) != _gun_no(index, seans_saat)) & gecerli
    tur = seans_turu(index) if tur is None else tur
    if tur == KRIPTO:
        return son
    kapanis_ani = seans_kapanis_ani(index, tur)
    kz = kapanis_zamani.tz_localize("UTC") if kapanis_zamani.tz is None else kapanis_zamani.tz_convert("UTC")
    seansli = np.asarray(~kapanis_ani.isna()) & np.asarray(kz >= kapanis_ani)
    return son | (seansli & gecerli)


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
    out = pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef, "cikis": (c | son).astype(bool)})
    return gun_sonu_kapanis_ekle(out, son.to_numpy()) if gun_sonu else out


def gun_sonu_uygula(sig: pd.DataFrame, seans_saat: float = 0.0) -> pd.DataFrame:
    """Hazır bir sinyal çerçevesine gün sonu kuralını ekler (son mumda giriş yok, cikis=True)."""
    son = seans_son_mumu(sig.index, seans_saat)
    s = sig.copy()
    s.loc[son, ["yon"]] = 0
    s.loc[son, ["stop", "hedef"]] = np.nan
    s["cikis"] = (s["cikis"].astype(bool) | son).astype(bool)
    s["yon"] = s["yon"].astype("int64")
    return gun_sonu_kapanis_ekle(s, son)


def gun_sonu_kapanis_ekle(sig: pd.DataFrame, son: np.ndarray) -> pd.DataFrame:
    """Seanslı veride (seans_takvimi.seans_turu != kripto) `gun_sonu_kapanis` sütunu ekler: gün sonu mumunda açık
    pozisyon motor tarafından O MUMUN KAPANIŞ fiyatından kapatılır (bilinen seans kapanışında piyasa/MOC emri; kapanış
    anı takvimden önceden bilinir, fiyat mumun kendi kapanışıdır -> lookahead yok). Sütun yoksa motor gün sonu
    `cikis`ini diğer çıkışlar gibi sonraki açılışta doldurur. Kripto (7/24): sütun EKLENMEZ (davranış birebir aynı;
    gece yarısı mumunun kapanışı ile sonraki açılış aynı andır)."""
    if seans_turu(sig.index) == KRIPTO:
        return sig
    s = sig.copy()
    s["gun_sonu_kapanis"] = np.asarray(son, dtype=bool)
    return s
