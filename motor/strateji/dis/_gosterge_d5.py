"""D5 (ek_77 belgesi) stratejileri için göstergeler ve seans yardımcıları. Hepsi nedensel: t. satır yalnız t. mum
kapanışına kadar olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz; d4'ün seans çerçevesi yalnız import edilir.

  kama, ott                         KAMA ve Optimized Trend Tracker (OTT) çizgisi.
  cti                               Ehlers Correlation Trend Indicator (kayan pencerede fiyat-zaman korelasyonu).
  seans_bilgi                       d4 seans_cerceve + seans açılışı / açılış tamam bayrağı.
  onceki_seanslar_ozeti             ÖNCEKİ n tamamlanmış seansın HH/LL/HC/LC değerleri (bugünün seansı DAHİL DEĞİL).
  onceki_seans_hlc                  bir önceki seansın yüksek/düşük/kapanışı.
  gun_ici_cerceve                   gün içi stratejiler için çerçeve + seans sonu çıkışı (utc_gun ve abd_hisse).
  yerel_saat_kapanis                mum kapanışının yerel saat (ondalık) değeri.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d4 import seans_cerceve


# ------------------------------------------------------------------ KAMA / OTT
def kama(seri: pd.Series, n: int, hizli: int = 2, yavas: int = 30) -> pd.Series:
    """Kaufman uyarlanabilir hareketli ortalama. Verimlilik oranı = |c - c[n önce]| / son n farkın mutlak toplamı.
    İlk değer n. mumda kapanışla başlar; öncesi NaN."""
    c = seri.to_numpy(dtype=float)
    nn = len(c)
    out = np.full(nn, np.nan)
    n = int(n)
    if nn <= n:
        return pd.Series(out, index=seri.index)
    fark = np.abs(np.diff(c, prepend=np.nan))
    gurultu = pd.Series(fark).rolling(n, min_periods=n).sum().to_numpy()
    sinyal = np.abs(c - np.r_[np.full(n, np.nan), c[:-n]])
    f, s = 2.0 / (hizli + 1.0), 2.0 / (yavas + 1.0)
    out[n] = c[n]
    for i in range(n + 1, nn):
        er = sinyal[i] / gurultu[i] if gurultu[i] > 0 else 0.0
        sc = (er * (f - s) + s) ** 2
        out[i] = out[i - 1] + sc * (c[i] - out[i - 1])
    return pd.Series(out, index=seri.index)


def ott(ort: pd.Series, yuzde: float) -> pd.Series:
    """Optimized Trend Tracker çizgisi (Anıl Özekşi) `ort` (hareketli ortalama) üzerinden.
    fark = ort x yuzde/100; long stop yalnız yukarı, short stop yalnız aşağı iz sürer; yön, ortalamanın karşı stopu
    kesmesiyle değişir; OTT = MT x (1 +/- yuzde/200). Nedensel (tek ileri geçiş)."""
    a = ort.to_numpy(dtype=float)
    nn = len(a)
    out = np.full(nn, np.nan)
    ilk = np.flatnonzero(~np.isnan(a))
    if len(ilk) == 0:
        return pd.Series(out, index=ort.index)
    i0 = int(ilk[0])
    k = yuzde / 100.0
    uzun, kisa = a[i0] * (1 - k), a[i0] * (1 + k)
    yon = 1
    mt = uzun
    out[i0] = mt * (1 + yuzde / 200.0) if a[i0] > mt else mt * (1 - yuzde / 200.0)
    for i in range(i0 + 1, nn):
        if np.isnan(a[i]):
            continue
        u_onc, k_onc = uzun, kisa
        uzun = a[i] * (1 - k)
        uzun = max(uzun, u_onc) if a[i] > u_onc else uzun
        kisa = a[i] * (1 + k)
        kisa = min(kisa, k_onc) if a[i] < k_onc else kisa
        if yon == -1 and a[i] > k_onc:
            yon = 1
        elif yon == 1 and a[i] < u_onc:
            yon = -1
        mt = uzun if yon == 1 else kisa
        out[i] = mt * (1 + yuzde / 200.0) if a[i] > mt else mt * (1 - yuzde / 200.0)
    return pd.Series(out, index=ort.index)


def cti(kapanis: pd.Series, n: int = 20) -> pd.Series:
    """Correlation Trend Indicator: son n kapanışın zaman sırasıyla Pearson korelasyonu (-1..1)."""
    n = int(n)
    x = np.arange(n, dtype=float)
    x = x - x.mean()
    sxx = float((x * x).sum())
    c = kapanis.to_numpy(dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) >= n:
        w = np.lib.stride_tricks.sliding_window_view(c, n)
        wm = w - w.mean(axis=1, keepdims=True)
        sxy = wm @ x
        syy = (wm * wm).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[n - 1:] = np.where(syy > 0, sxy / np.sqrt(sxx * syy), np.nan)
    return pd.Series(out, index=kapanis.index)


# ------------------------------------------------------------------ seans yardımcıları
def seans_bilgi(mumlar: pd.DataFrame, seans: str, giris_dk: float = 0.0) -> dict:
    """d4 seans_cerceve + seans açılış fiyatı. Dönen sözlük:
    c (çerçeve), sid, ici (bool ndarray), acilis (seans açılış mumunun AÇILIŞ fiyatı, her mumda),
    acilis_tamam (açılış mumu zamanında başladı)."""
    c = seans_cerceve(mumlar.index, seans, giris_dk)
    sid = c["sid"].to_numpy()
    ici = c["seans_ici"].to_numpy().astype(bool)
    ac_ref = mumlar["acilis"].where(ici).groupby(sid).transform("first")
    tamam = pd.Series((c["ac_gecikme_s"] < c["dur_s"]).to_numpy() & ici, index=mumlar.index)
    return {"c": c, "sid": sid, "ici": ici, "acilis": ac_ref, "acilis_tamam": tamam}


def onceki_seanslar_ozeti(mumlar: pd.DataFrame, sid: np.ndarray, ici: np.ndarray, n: int) -> pd.DataFrame:
    """Her mum için ÖNCEKİ n tamamlanmış seansın HH (yüksek max), LL (düşük min), HC (kapanış max), LC (kapanış min).
    Bugünün seansı hesaba GİRMEZ (önce seans başına özet, sonra shift(1), sonra kayan pencere)."""
    n = int(n)
    m = mumlar.loc[ici]
    g = m.groupby(sid[ici])
    ozet = pd.DataFrame({"yuksek": g["yuksek"].max(), "dusuk": g["dusuk"].min(),
                         "kmax": g["kapanis"].max(), "kmin": g["kapanis"].min()}).shift(1)
    hh = ozet["yuksek"].rolling(n, min_periods=n).max()
    ll = ozet["dusuk"].rolling(n, min_periods=n).min()
    hc = ozet["kmax"].rolling(n, min_periods=n).max()
    lc = ozet["kmin"].rolling(n, min_periods=n).min()
    s = pd.Series(sid)
    return pd.DataFrame({"hh": hh.reindex(s).to_numpy(), "ll": ll.reindex(s).to_numpy(),
                         "hc": hc.reindex(s).to_numpy(), "lc": lc.reindex(s).to_numpy()}, index=mumlar.index)


def onceki_seans_hlc(mumlar: pd.DataFrame, sid: np.ndarray, ici: np.ndarray) -> pd.DataFrame:
    """Her mum için bir ÖNCEKİ tamamlanmış seansın (h, l, c) değerleri (yalnız seans içi mumlar sayılır)."""
    m = mumlar.loc[ici]
    g = m.groupby(sid[ici])
    ozet = pd.DataFrame({"h": g["yuksek"].max(), "l": g["dusuk"].min(), "c": g["kapanis"].last()}).shift(1)
    s = pd.Series(sid)
    return pd.DataFrame({k: ozet[k].reindex(s).to_numpy() for k in ("h", "l", "c")}, index=mumlar.index)


def yerel_saat_kapanis(index: pd.DatetimeIndex, dur_s: np.ndarray, saat_dilimi: str) -> np.ndarray:
    """Mumun KAPANIŞ anının yerel saati (ondalık: 14.5 = 14:30). dur_s NaN ise NaN."""
    idx = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    kap = idx + pd.to_timedelta(np.where(np.isnan(dur_s), 0.0, dur_s), unit="s")
    yerel = kap.tz_convert(saat_dilimi)
    h = (yerel.hour + yerel.minute / 60.0 + yerel.second / 3600.0).to_numpy(dtype=float)
    return np.where(np.isnan(dur_s), np.nan, h)


def gun_ici_cerceve(mumlar: pd.DataFrame, seans: str, c: pd.DataFrame, long_ok, short_ok, stop_l, stop_s,
                    hedef_l=None, hedef_s=None, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    """Gün içi çerçeve: seans sonunda zorunlu çıkış, son mumlarda yeni giriş yok.
    utc_gun: günün son mumunda cikis (d4 ile aynı); abd_hisse: çıkış son mumun AÇILIŞINDA olsun diye kapanıştan bir
    mum önceki mumda cikis (motor çıkışı sonraki açılışta yapar; seans sonrası mum yoksa gece taşınırdı).
    cikis_long / cikis_short: yönlü çıkış koşulları (ters sinyalde çevirme için); seans içi dışı mumlarda yok sayılır."""
    idx = mumlar.index
    if seans == "utc_gun":
        out = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, gun_sonu=True, seans_saat=0.0)
    else:
        dur = pd.to_timedelta(c["dur_s"].to_numpy(), unit="s")
        kapanis_utc = pd.DatetimeIndex(c["kapanis_utc"])
        bar_kap = pd.DatetimeIndex(c["bar_kapanis"])
        gecerli = ~np.isnan(c["dur_s"].to_numpy())
        erken = np.asarray(bar_kap >= (kapanis_utc - dur))
        ici = c["seans_ici"].to_numpy().astype(bool)
        cik = pd.Series((erken | ~ici) & gecerli, index=idx)
        lo = long_ok.fillna(False).astype(bool) & ~cik if isinstance(long_ok, pd.Series) else long_ok
        so = short_ok.fillna(False).astype(bool) & ~cik if isinstance(short_ok, pd.Series) else short_ok
        out = cerceve(mumlar, lo, so, stop_l, stop_s, hedef_l, hedef_s, cikis=cik)
    for ad, k in (("cikis_long", cikis_long), ("cikis_short", cikis_short)):
        out[ad] = (pd.Series(False, index=idx) if k is None else k.reindex(idx).fillna(False).astype(bool))
    return out
