"""D1 grubu (dış kaynaklı TradingView stratejileri) için yardımcılar. Paylaşılan dosyalara dokunulmaz. Hepsi nedensel.

  kur                  _ortak.cerceve + yönlü çıkış sütunları (cikis_long / cikis_short) + zaman_cikisi_mum.
  smma, wma, hma       Wilder/SMMA, ağırlıklı ve Hull hareketli ortalamalar.
  linreg               en küçük kareler doğrusunun SON noktası (Pine ta.linreg(x, n, 0)).
  kama                 Kaufman uyarlamalı ortalama.
  yuzdelik_sira        Pine ta.percentrank: önceki n değerin kaçı <= bugünkü (yüzde).
  gauss_kutup          N kutuplu Gauss filtresi (Ehlers).
  laguerre             Laguerre filtresi bileşenleri (cu, cd).
  kst                  Know Sure Thing + sinyal.
  choppiness           Choppiness Index.
  ao_ac                Awesome / Accelerator osilatörleri.
  williams_trend       Alligator dişi + fraktal etkinleşme seviyelerinden trend durumu (Skyrexio ailesi).
  gunluk_kapanis       Önceki TAMAMLANMIŞ günün kapanışı ve ondan bir önceki (HTF'siz, lookahead'siz).
  anahtar_olay         koşulun yalnız False->True geçişi.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula
from motor.strateji.seans_takvimi import mum_suresi


def kur(mumlar, long_ok, short_ok, stop_l, stop_s, hedef_l=None, hedef_s=None,
        cikis_l=None, cikis_s=None, gun_sonu: bool = False, seans_saat: float = 0.0,
        zaman_cikisi=None) -> pd.DataFrame:
    """Sinyal çerçevesi. cikis_l: long pozisyonu kapatan koşul, cikis_s: short'u kapatan koşul (yönlü çıkış).
    Stop yanlış tarafta/NaN ise sinyal düşer (cerceve). gun_sonu=True: seansın son mumunda giriş yok, cikis=True."""
    idx = mumlar.index
    sig = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, None,
                  gun_sonu=gun_sonu, seans_saat=seans_saat)

    def b(x):
        if x is None:
            return pd.Series(False, index=idx)
        return pd.Series(x, index=idx).fillna(False).astype(bool)
    sig["cikis_long"] = b(cikis_l)
    sig["cikis_short"] = b(cikis_s)
    if zaman_cikisi is not None:
        zc = pd.Series(np.nan, index=idx)
        m = sig["yon"] != 0
        zc[m] = pd.Series(zaman_cikisi, index=idx)[m] if not np.isscalar(zaman_cikisi) else float(zaman_cikisi)
        sig["zaman_cikisi_mum"] = zc
    return sig


# ---------------------------------------------------------------- ortalamalar / filtreler
def smma(seri: pd.Series, n: int) -> pd.Series:
    """Pine smma: ilk değer SMA, sonra (önceki*(n-1)+x)/n."""
    x = seri.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    ilk = g.sma(seri, n).to_numpy()
    prev = np.nan
    for i in range(len(x)):
        if np.isnan(prev):
            if not np.isnan(ilk[i]):
                prev = ilk[i]
                out[i] = prev
        else:
            prev = (prev * (n - 1) + x[i]) / n
            out[i] = prev
    return pd.Series(out, index=seri.index)


def wma(seri: pd.Series, n: int) -> pd.Series:
    n = int(n)
    w = np.arange(1, n + 1, dtype=float)
    x = seri.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = (sliding_window_view(x, n) * w).sum(axis=1) / w.sum()
    return pd.Series(out, index=seri.index)


def hma(seri: pd.Series, n: int) -> pd.Series:
    n = int(n)
    yarim = max(1, n // 2)
    kok = max(1, int(round(np.sqrt(n))))
    return wma(2.0 * wma(seri, yarim) - wma(seri, n), kok)


def linreg(seri: pd.Series, n: int) -> pd.Series:
    """Son n değere oturtulan doğrunun SON noktasındaki değer."""
    n = int(n)
    x = seri.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        w = sliding_window_view(x, n)
        t = np.arange(n, dtype=float)
        tm = t.mean()
        egim = ((w - w.mean(axis=1, keepdims=True)) * (t - tm)).sum(axis=1) / ((t - tm) ** 2).sum()
        out[n - 1:] = w.mean(axis=1) + egim * (n - 1 - tm)
    return pd.Series(out, index=seri.index)


def kama(seri: pd.Series, er_n: int = 10, hizli: int = 2, yavas: int = 30) -> pd.Series:
    x = seri.to_numpy(dtype=float)
    n = len(x)
    degisim = np.abs(seri - seri.shift(er_n)).to_numpy()
    oynak = seri.diff().abs().rolling(er_n, min_periods=er_n).sum().to_numpy()
    er = np.where(oynak > 0, degisim / np.where(oynak > 0, oynak, 1.0), 0.0)
    fs, ss = 2.0 / (hizli + 1), 2.0 / (yavas + 1)
    sc = (er * (fs - ss) + ss) ** 2
    out = np.full(n, np.nan)
    prev = np.nan
    for i in range(n):
        if np.isnan(x[i]):
            continue
        prev = x[i] if np.isnan(prev) else prev + (0.0 if np.isnan(sc[i]) else sc[i]) * (x[i] - prev)
        out[i] = prev
    return pd.Series(out, index=seri.index)


def yuzdelik_sira(seri: pd.Series, n: int) -> pd.Series:
    """Pine ta.percentrank: ÖNCEKİ n değerden bugünküne eşit/küçük olanların yüzdesi."""
    n = int(n)
    x = seri.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) > n:
        w = sliding_window_view(x[:-1], n)                       # w[j] = x[j..j+n-1] -> bugün j+n
        bugun = x[n:]
        with np.errstate(invalid="ignore"):
            oran = (w <= bugun[:, None]).sum(axis=1) / n * 100.0
        gecersiz = np.isnan(w).any(axis=1) | np.isnan(bugun)
        oran[gecersiz] = np.nan
        out[n:] = oran
    return pd.Series(out, index=seri.index)


def gauss_kutup(kaynak: pd.Series, n_kutup: int, periyot: int) -> pd.Series:
    """Ehlers N kutuplu Gauss filtresi: f[t] = a^N s[t] + sum_k (-1)^(k+1) C(N,k) (1-a)^k f[t-k]."""
    from math import comb, cos, pi, sqrt
    N, per = int(n_kutup), int(periyot)
    beta = (1 - cos(2 * pi / per)) / (1.414 ** (2.0 / N) - 1)
    a = -beta + sqrt(beta * beta + 2 * beta)
    x = 1 - a
    kat = [((-1) ** (k + 1)) * comb(N, k) * x ** k for k in range(1, N + 1)]
    s = np.nan_to_num(kaynak.to_numpy(dtype=float))
    f = np.zeros(len(s))
    aN = a ** N
    for t in range(len(s)):
        v = aN * s[t]
        for k in range(1, N + 1):
            if t - k >= 0:
                v += kat[k - 1] * f[t - k]
        f[t] = v
    return pd.Series(f, index=kaynak.index)


def laguerre(kaynak: pd.Series, alfa: float = 0.2) -> pd.DataFrame:
    """Laguerre RSI bileşenleri: cu (yukarı toplam), cd (aşağı toplam)."""
    gm = 1.0 - alfa
    s = kaynak.to_numpy(dtype=float)
    n = len(s)
    L0 = L1 = L2 = L3 = 0.0
    cu = np.zeros(n)
    cd = np.zeros(n)
    for i in range(n):
        p0, p1, p2 = L0, L1, L2
        L0 = (1 - gm) * s[i] + gm * p0
        L1 = -gm * L0 + p0 + gm * p1
        L2 = -gm * L1 + p1 + gm * p2
        L3 = -gm * L2 + p2 + gm * L3
        cu[i] = (L0 - L1 if L0 > L1 else 0.0) + (L1 - L2 if L1 > L2 else 0.0) + (L2 - L3 if L2 > L3 else 0.0)
        cd[i] = (L1 - L0 if L0 < L1 else 0.0) + (L2 - L1 if L1 < L2 else 0.0) + (L3 - L2 if L2 < L3 else 0.0)
    return pd.DataFrame({"cu": cu, "cd": cd}, index=kaynak.index)


def kst(kapanis: pd.Series, roc=(10, 15, 20, 30), sma_n=(10, 10, 10, 15), sinyal: int = 9) -> pd.DataFrame:
    def bilesen(r, m):
        return g.sma((kapanis / kapanis.shift(r) - 1.0) * 100.0, m)
    k = sum(w * bilesen(r, m) for w, r, m in zip((1, 2, 3, 4), roc, sma_n))
    return pd.DataFrame({"kst": k, "sinyal": g.sma(k, sinyal)})


def choppiness(yuksek, dusuk, kapanis, n: int = 14) -> pd.Series:
    tr = g.gercek_aralik(yuksek, dusuk, kapanis)
    # Pine ta.atr(1) = rma(tr,1) = tr; tr'nin ilk değeri high-low
    aralik = yuksek.rolling(n, min_periods=n).max() - dusuk.rolling(n, min_periods=n).min()
    top = tr.rolling(n, min_periods=n).sum()
    return 100.0 * np.log10(top / aralik.where(aralik > 0)) / np.log10(n)


def ao_ac(yuksek: pd.Series, dusuk: pd.Series) -> pd.DataFrame:
    hl2 = (yuksek + dusuk) / 2.0
    ao = g.sma(hl2, 5) - g.sma(hl2, 34)
    ac = ao - g.sma(ao, 5)
    return pd.DataFrame({"ao": ao, "ac": ac})


def anahtar_olay(kosul: pd.Series) -> pd.Series:
    k = pd.Series(kosul).fillna(False).astype(bool)
    return k & ~k.shift(1, fill_value=False)


def alligator_dis(yuksek: pd.Series, dusuk: pd.Series) -> pd.Series:
    """Alligator 'dişi' (teeth): SMMA(hl2, 8) 5 mum geriye kaydırılmış (nedensel; ileri kaydırma yok)."""
    return smma((yuksek + dusuk) / 2.0, 8).shift(5)


def alligator_cene(yuksek: pd.Series, dusuk: pd.Series) -> pd.Series:
    return smma((yuksek + dusuk) / 2.0, 13).shift(8)


def williams_trend(yuksek: pd.Series, dusuk: pd.Series, fraktal_k: int = 2) -> pd.Series:
    """Skyrexio 'MultiLayer' ailesinin trend durumu (+1/-1/0).

    Üst fraktal seviyesi (son onaylı tepe, Alligator dişinin ÜSTÜNDE ise) etkinleşir; high bu etkin seviyeyi yukarı
    keserse trend=+1, alt fraktal seviyesi (dişin ALTINDA ise) etkinleşir; low aşağı keserse trend=-1.
    Fraktal = 5 mumluk (k=2) pivot; onay pivot + 2 mum sonra (nedensel). Pine'ın ta.crossover'ı önceki mumun
    seviyesini kullanır; burada da aynı (kesişim: high[i] > ust_etkin[i-1] ve high[i-1] <= ust_etkin[i-2])."""
    from motor.strateji.pivotlar import fraktal_pivotlar
    pv = fraktal_pivotlar(yuksek, dusuk, fraktal_k)
    ust_s = pv["son_tepe_fiyat"].to_numpy()
    alt_s = pv["son_dip_fiyat"].to_numpy()
    dis = alligator_dis(yuksek, dusuk).to_numpy()
    h, l = yuksek.to_numpy(float), dusuk.to_numpy(float)
    n = len(h)
    trend = np.zeros(n, dtype="int64")
    ua = np.full(n, np.nan)
    da = np.full(n, np.nan)
    ua_c = da_c = np.nan
    tr = 0
    for i in range(n):
        yukari_kes = (i >= 2 and not np.isnan(ua[i - 1]) and not np.isnan(ua[i - 2])
                      and h[i] > ua[i - 1] and h[i - 1] <= ua[i - 2])
        asagi_kes = (i >= 2 and not np.isnan(da[i - 1]) and not np.isnan(da[i - 2])
                     and l[i] < da[i - 1] and l[i - 1] >= da[i - 2])
        if ust_s[i] > dis[i]:                   # NaN karşılaştırması False
            ua_c = ust_s[i]
        if yukari_kes:
            tr = 1
            ua_c = np.nan
            da_c = alt_s[i]
        if alt_s[i] < dis[i]:
            da_c = alt_s[i]
        if asagi_kes:
            tr = -1
            da_c = np.nan
            ua_c = ust_s[i]
        if tr == 1:
            ua_c = np.nan
        if tr == -1:
            da_c = np.nan
        ua[i], da[i], trend[i] = ua_c, da_c, tr
    return pd.Series(trend, index=yuksek.index)


def gunluk_kapanis(mumlar: pd.DataFrame) -> pd.DataFrame:
    """(dun, onceki_gun): o ana kadar TAMAMLANMIŞ son iki günün (UTC) kapanışı. Gün kapanmadan değişmez.
    Alt TF verisinde htf.ust_zaman, günlük veride doğrudan kaydırma kullanılır."""
    from motor.strateji.htf import ust_zaman
    kaynak_s = mum_suresi(mumlar.index)
    if kaynak_s >= pd.Timedelta(days=1):
        k = mumlar["kapanis"]
        return pd.DataFrame({"dun": k, "onceki": k.shift(1)})
    s = ust_zaman(mumlar, "1d", lambda u: pd.DataFrame({"dun": u["kapanis"], "onceki": u["kapanis"].shift(1)}))
    return s
