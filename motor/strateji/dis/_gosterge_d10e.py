"""D10-E için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır.
Paylaşılan dosyalara dokunulmaz.

  yavas_stok, vwma, ut_bot, trend_magic, bb_macd_renk, nsm_macd, ob_bolgeleri, mum_suresi_dk
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g


def yavas_stok(yuksek, dusuk, kapanis, n: int = 5, k_n: int = 3, d_n: int = 3) -> pd.DataFrame:
    """Yavaş stokastik: ham %K(n) -> SMA(k_n) = K; D = SMA(K, d_n)."""
    hh = yuksek.rolling(n, min_periods=n).max()
    ll = dusuk.rolling(n, min_periods=n).min()
    ham = 100.0 * (kapanis - ll) / (hh - ll).where(hh != ll)
    k = ham.rolling(k_n, min_periods=k_n).mean()
    return pd.DataFrame({"k": k, "d": k.rolling(d_n, min_periods=d_n).mean()})


def vwma(seri: pd.Series, hacim: pd.Series, n: int) -> pd.Series:
    """Hacim ağırlıklı hareketli ortalama (seri herhangi bir gösterge olabilir)."""
    pay = (seri * hacim).rolling(n, min_periods=n).sum()
    payda = hacim.rolling(n, min_periods=n).sum()
    return pay / payda.where(payda > 0)


def ut_bot(kaynak: pd.Series, atr: pd.Series, anahtar: float) -> pd.DataFrame:
    """UT Bot Alerts (QuantNomad / HPotter, yaygın tanım; JeRCEqWU.pine'daki `utTrailingStop` ile aynı özyineleme).
    nLoss = anahtar x ATR; iz süren stop yön yönünde yalnız ilerler. al: kaynak stopun üstüne yukarı kesti; sat: tersi.
    Dönen: stop, durum (+1 stopun üstünde, -1 altında), al, sat (bool)."""
    s = kaynak.to_numpy(dtype=float)
    loss = (anahtar * atr).to_numpy(dtype=float)
    n = len(s)
    stop = np.full(n, np.nan)
    al = np.zeros(n, dtype=bool)
    sat = np.zeros(n, dtype=bool)
    prev = np.nan
    for i in range(n):
        if np.isnan(loss[i]):
            continue
        if np.isnan(prev):
            cur = s[i] - loss[i]
        else:
            s1 = s[i - 1] if i else s[i]
            if s[i] > prev and s1 > prev:
                cur = max(prev, s[i] - loss[i])
            elif s[i] < prev and s1 < prev:
                cur = min(prev, s[i] + loss[i])
            elif s[i] > prev:
                cur = s[i] - loss[i]
            else:
                cur = s[i] + loss[i]
            al[i] = bool(s1 <= prev and s[i] > cur)      # ta.crossover(kaynak, stop)
            sat[i] = bool(s1 >= prev and s[i] < cur)     # ta.crossunder(kaynak, stop)
        stop[i] = cur
        prev = cur
    durum = np.where(np.isnan(stop), 0, np.where(s > stop, 1, np.where(s < stop, -1, 0)))
    return pd.DataFrame({"stop": stop, "durum": durum, "al": al, "sat": sat}, index=kaynak.index)


def trend_magic(yuksek, dusuk, kapanis, cci_n: int = 20, atr_n: int = 5, carpan: float = 1.0) -> pd.DataFrame:
    """Trend Magic (Kıvanç Özbilgiç, yaygın tanım): CCI(cci_n) >= 0 ise çizgi (düşük - carpan x ATR) ile yalnız yukarı iz sürer
    (mavi), değilse (yüksek + carpan x ATR) ile yalnız aşağı (kırmızı). ATR = gerçek aralığın SMA'sı (atr_n). Dönen: cizgi, mavi (bool)."""
    from motor.strateji.gostergeler_b2 import cci
    c = cci(kapanis, kapanis, kapanis, cci_n).to_numpy(dtype=float)
    tr = g.gercek_aralik(yuksek, dusuk, kapanis)
    a = tr.rolling(atr_n, min_periods=atr_n).mean().to_numpy(dtype=float)
    up = (dusuk.to_numpy(dtype=float) - carpan * a)
    dn = (yuksek.to_numpy(dtype=float) + carpan * a)
    n = len(c)
    mt = np.full(n, np.nan)
    prev = np.nan
    for i in range(n):
        if np.isnan(c[i]) or np.isnan(a[i]):
            continue
        if np.isnan(prev):
            cur = up[i] if c[i] >= 0 else dn[i]
        elif c[i] >= 0:
            cur = prev if up[i] < prev else up[i]
        else:
            cur = prev if dn[i] > prev else dn[i]
        mt[i] = cur
        prev = cur
    mavi = pd.Series(np.where(np.isnan(c), False, c >= 0), index=kapanis.index)
    return pd.DataFrame({"cizgi": mt, "mavi": mavi.astype(bool)}, index=kapanis.index)


def bb_macd_renk(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, bb_n: int = 10, bb_k: float = 1.0) -> pd.DataFrame:
    """MACD çizgisi üzerine Bollinger (Dreadblitz "BB MACD" fikri, kendi yazımımız). Renk: MACD üst bandın üstünde = yesil,
    alt bandın altında = kirmizi, aksi halde mavi. Dönen: macd, yesil, kirmizi (bool)."""
    macd = g.ema(kapanis, hizli) - g.ema(kapanis, yavas)
    ort = macd.rolling(bb_n, min_periods=bb_n).mean()
    sd = macd.rolling(bb_n, min_periods=bb_n).std(ddof=0)
    ust, alt = ort + bb_k * sd, ort - bb_k * sd
    return pd.DataFrame({"macd": macd, "yesil": (macd > ust) & ust.notna(), "kirmizi": (macd < alt) & alt.notna()})


def nsm_macd(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, yumusat: int = 3, norm_n: int = 100) -> pd.DataFrame:
    """Normalleştirilmiş Yumuşatılmış MACD (kitapta tanım yok; yaygın tanım): MACD çizgisi = EMA(hizli) - EMA(yavas); EMA(yumusat)
    ile yumuşatılır; son norm_n mumun en büyük mutlak değerine bölünüp 100 ile çarpılır (-100..100). "Çizgi yeşile döner" =
    normalleştirilmiş çizginin eğimi artıya geçer. Dönen: nsm, yesil_don (eğim yukarı döndü), kirmizi_don."""
    macd = g.ema(kapanis, hizli) - g.ema(kapanis, yavas)
    duz = macd.ewm(span=yumusat, adjust=False, min_periods=yumusat).mean()
    mx = duz.abs().rolling(norm_n, min_periods=norm_n).max()
    nsm = 100.0 * duz / mx.where(mx > 0)
    yukari = nsm > nsm.shift(1)
    asagi = nsm < nsm.shift(1)
    yesil_don = yukari & ~yukari.shift(1, fill_value=False) & nsm.shift(1).notna()
    kirmizi_don = asagi & ~asagi.shift(1, fill_value=False) & nsm.shift(1).notna()
    return pd.DataFrame({"nsm": nsm, "yesil_don": yesil_don, "kirmizi_don": kirmizi_don})


def ob_bolgeleri(yuksek, dusuk, atr, pivot_n: int, atr_k: float, omur: int):
    """Order block dokunuşu (CleanTradeQuantum OB mantığı; kendi yazımımız). Pivot dibi/tepesi `pivot_n` mum SONRA onaylanır;
    pivot mumunun [dip, tepe] aralığı (boyu <= atr_k x ATR ise) onaydan itibaren `omur` mum geçerli bölge olur. Bölgeye
    dokunan mum (düşük <= bölge tepesi ve yüksek >= bölge dibi) -> dokunuş. Dönen: (boga_dokunus, ayi_dokunus) bool Series.
    Boğa bölgesi pivot DİBİNDEN, ayı bölgesi pivot TEPESİNDEN türer."""
    h, l = yuksek.to_numpy(dtype=float), dusuk.to_numpy(dtype=float)
    a = atr.to_numpy(dtype=float)
    n = len(h)
    p = int(pivot_n)
    boga = np.zeros(n, dtype=bool)
    ayi = np.zeros(n, dtype=bool)
    bz = az = None   # (tepe, dip, dogum)
    for i in range(n):
        j = i - p
        if j >= p and not np.isnan(a[i]):
            pencere_l = l[j - p:i + 1]
            pencere_h = h[j - p:i + 1]
            if l[j] == pencere_l.min():
                if h[j] - l[j] <= atr_k * a[i]:
                    bz = (h[j], l[j], i)
            if h[j] == pencere_h.max():
                if h[j] - l[j] <= atr_k * a[i]:
                    az = (h[j], l[j], i)
        if bz is not None and i - bz[2] <= omur and l[i] <= bz[0] and h[i] >= bz[1]:
            boga[i] = True
        if az is not None and i - az[2] <= omur and h[i] >= az[1] and l[i] <= az[0]:
            ayi[i] = True
    idx = yuksek.index
    return pd.Series(boga, index=idx), pd.Series(ayi, index=idx)


def mum_suresi_dk(index: pd.DatetimeIndex) -> np.ndarray:
    """Mum süresi (dk): şimdiye kadar görülen en küçük mum aralığı (nedensel; ilk mum için 0)."""
    n = len(index)
    if n < 2:
        return np.zeros(n)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(minutes=1)).to_numpy()
    return np.r_[0.0, np.minimum.accumulate(fark)]
