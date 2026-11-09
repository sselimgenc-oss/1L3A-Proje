"""D11-H (GitHub kaynaklı daytrade aileleri) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar
olan veriyi kullanır. KOD KOPYALANMADI; formüller kamuya açık tanımlardan kendi yapımızla yazıldı.

  taban_cerceve  ortak giriş/çıkış çerçevesi (ATR veya göstergeye bağlı stop, R hedefi, yüzde hedef, zaman, gün sonu)
  klinger, ppo, tsi, ultimate, hizli_nw, ortalama_kaydir, rvi, obv, ad_cizgisi, gosterge_serisi
  vwap_basarisizlik_sinyali, parabolik_tetik   (seans içi durum makineleri)
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve


# ------------------------------------------------------------------ çerçeve
def taban_cerceve(m: pd.DataFrame, p: dict, k: dict) -> pd.DataFrame:
    """k: long, short, cikis_long, cikis_short (bool Series), opsiyonel stop_long / stop_short (fiyat Series).
    p: yonler, stop_atr_k, atr_periyot, hedef_r, hedef_yuzde, zaman_cikisi, gun_sonu."""
    idx = m.index
    kap = m["kapanis"]
    bos = pd.Series(False, index=idx)

    def al(ad):
        s = k.get(ad)
        return bos if s is None else s.reindex(idx).fillna(False).astype(bool)

    yon = p.get("yonler", "long")
    long_ok = al("long") if yon in ("long", "ls") else bos
    short_ok = al("short") if yon in ("short", "ls") else bos
    a = g.atr(m["yuksek"], m["dusuk"], kap, int(p.get("atr_periyot", 14))) * float(p.get("stop_atr_k", 2.0))
    stop_l = k["stop_long"] if k.get("stop_long") is not None else kap - a
    stop_s = k["stop_short"] if k.get("stop_short") is not None else kap + a
    hedef_l = hedef_s = None
    r = float(p.get("hedef_r", 0.0) or 0.0)
    hy = float(p.get("hedef_yuzde", 0.0) or 0.0)
    if r > 0:
        hedef_l, hedef_s = kap + r * (kap - stop_l), kap - r * (stop_s - kap)
    elif hy > 0:
        hedef_l, hedef_s = kap * (1 + hy), kap * (1 - hy)
    out = cerceve(m, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, None, bool(p.get("gun_sonu", 0)), 0.0)
    out["cikis_long"] = al("cikis_long")
    out["cikis_short"] = al("cikis_short")
    z = int(p.get("zaman_cikisi", 0) or 0)
    if z > 0:
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(z), np.nan), index=idx)
    return out


# ------------------------------------------------------------------ göstergeler
def ppo(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, sinyal: int = 9) -> pd.DataFrame:
    """Percentage Price Oscillator: 100 x (EMA hızlı - EMA yavaş) / EMA yavaş; hist = ppo - EMA(ppo, sinyal)."""
    ppo_ = 100.0 * (g.ema(kapanis, hizli) - g.ema(kapanis, yavas)) / g.ema(kapanis, yavas)
    sig = ppo_.ewm(span=sinyal, adjust=False, min_periods=sinyal).mean()
    return pd.DataFrame({"ppo": ppo_, "sinyal": sig, "hist": ppo_ - sig})


def tsi(kapanis: pd.Series, uzun: int = 25, kisa: int = 13) -> pd.Series:
    """True Strength Index: 100 x EMA(EMA(dP, uzun), kisa) / EMA(EMA(|dP|, uzun), kisa)."""
    d = kapanis.diff()

    def cift(x):
        return x.ewm(span=uzun, adjust=False, min_periods=uzun).mean().ewm(span=kisa, adjust=False, min_periods=kisa).mean()
    payda = cift(d.abs())
    return 100.0 * cift(d) / payda.where(payda != 0)


def ultimate(yuksek, dusuk, kapanis, n1: int = 7, n2: int = 14, n3: int = 28) -> pd.Series:
    """Ultimate Oscillator (Williams): 100 x (4 A7 + 2 A14 + A28) / 7; A = alım baskısı toplamı / gerçek aralık toplamı."""
    onceki = kapanis.shift(1)
    alt = np.minimum(dusuk, onceki)
    bp = kapanis - alt
    tr = np.maximum(yuksek, onceki) - alt

    def a(n):
        return bp.rolling(n, min_periods=n).sum() / tr.rolling(n, min_periods=n).sum().where(lambda s: s != 0)
    return 100.0 * (4.0 * a(n1) + 2.0 * a(n2) + a(n3)) / 7.0


def klinger(yuksek, dusuk, kapanis, hacim, kisa: int = 34, uzun: int = 55) -> pd.Series:
    """Klinger Volume Oscillator: VF = hacim x |2 dm/cm - 1| x trend x 100; KVO = EMA(VF, kisa) - EMA(VF, uzun).
    trend = +1 (HLC toplamı arttı) / -1 (azaldı); cm = trend sürerken cm + dm, dönünce önceki dm + dm."""
    h, l, c, v = (x.to_numpy(dtype=float) for x in (yuksek, dusuk, kapanis, hacim))
    n = len(c)
    hlc = h + l + c
    dm = h - l
    tr = np.ones(n)
    cm = np.zeros(n)
    for i in range(1, n):
        tr[i] = 1.0 if hlc[i] > hlc[i - 1] else (-1.0 if hlc[i] < hlc[i - 1] else tr[i - 1])
        cm[i] = cm[i - 1] + dm[i] if tr[i] == tr[i - 1] else dm[i - 1] + dm[i]
    with np.errstate(divide="ignore", invalid="ignore"):
        vf = v * np.abs(2.0 * dm / cm - 1.0) * tr * 100.0
    vf[0] = np.nan
    vf = pd.Series(vf, index=kapanis.index)
    return vf.ewm(span=kisa, adjust=False, min_periods=kisa).mean() - vf.ewm(span=uzun, adjust=False, min_periods=uzun).mean()


def nw_zarf(kapanis: pd.Series, h: float = 8.0, pencere: int = 60, carpan: float = 3.0, mae_n: int = 100) -> pd.DataFrame:
    """NEDENSEL Nadaraya-Watson zarfı. Merkezli çekirdek (yeniden çizen) KULLANILMAZ: t anındaki tahmin yalnız
    t, t-1, ... t-pencere+1 kapanışlarının Gauss ağırlıklı ortalamasıdır (w_i = exp(-i^2 / (2 h^2))). Zarf = tahmin -/+ carpan x
    SMA(|kapanış - tahmin|, mae_n). Tek yanlı çekirdek tahmini sonradan değişmez (repaint yok)."""
    c = kapanis.to_numpy(dtype=float)
    n = len(c)
    i = np.arange(int(pencere), dtype=float)
    w = np.exp(-(i ** 2) / (2.0 * h * h))
    tahmin = np.full(n, np.nan)
    if n >= pencere:
        pen = sliding_window_view(c, int(pencere))[:, ::-1]          # satır: [c_t, c_{t-1}, ...]
        tahmin[pencere - 1:] = (pen * w).sum(axis=1) / w.sum()
    tahmin = pd.Series(tahmin, index=kapanis.index)
    mae = (kapanis - tahmin).abs().rolling(mae_n, min_periods=mae_n).mean() * carpan
    return pd.DataFrame({"orta": tahmin, "ust": tahmin + mae, "alt": tahmin - mae})


def rvi(acilis, yuksek, dusuk, kapanis, n: int = 10) -> pd.Series:
    """Relative Vigor Index: SMA(simetrik ağırlıklı (C-O), n) / SMA(simetrik ağırlıklı (H-L), n)."""
    def sw(x):
        return (x + 2 * x.shift(1) + 2 * x.shift(2) + x.shift(3)) / 6.0
    pay = sw(kapanis - acilis).rolling(n, min_periods=n).mean()
    payda = sw(yuksek - dusuk).rolling(n, min_periods=n).mean()
    return pay / payda.where(payda != 0)


def ad_cizgisi(yuksek, dusuk, kapanis, hacim) -> pd.Series:
    aralik = (yuksek - dusuk).where(yuksek != dusuk)
    return ((((kapanis - dusuk) - (yuksek - kapanis)) / aralik).fillna(0.0) * hacim).cumsum()


def _dema(x: pd.Series, n: int) -> pd.Series:
    e1 = x.ewm(span=n, adjust=False, min_periods=n).mean()
    return 2 * e1 - e1.ewm(span=n, adjust=False, min_periods=n).mean()


GOSTERGELER = ("rsi", "ema", "hma", "dema", "kama", "ao", "ac", "adx", "atr", "stddev", "obv", "ad", "chaikin", "force",
               "momentum", "osma", "macd", "dpo", "bears", "bulls", "rvi")
# yönsüz göstergeler: eğim yönü fiyat yönünden alınır
YONSUZ = {"atr", "stddev"}
MERKEZ = {"rsi": 50.0, "momentum": 100.0}


def gosterge_serisi(m: pd.DataFrame, ad: str, n: int) -> pd.Series:
    """Tek bir seriye indirgenmiş gösterge. Tüm dallar nedensel. Bilinmeyen ad -> ValueError."""
    o, h, l, c, v = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
    hl2 = (h + l) / 2.0
    if ad == "rsi":
        return g.rsi(c, n)
    if ad == "ema":
        return g.ema(c, n)
    if ad == "hma":
        from motor.strateji.dis._gosterge_d1 import hma
        return hma(c, n)
    if ad == "dema":
        return _dema(c, n)
    if ad == "kama":
        from motor.strateji.dis._gosterge_d1 import kama
        return kama(c, n)
    if ad == "ao":
        return g.sma(hl2, 5) - g.sma(hl2, 34)
    if ad == "ac":
        ao = g.sma(hl2, 5) - g.sma(hl2, 34)
        return ao - g.sma(ao, 5)
    if ad == "adx":
        return g.adx(h, l, c, n)["adx"]
    if ad == "atr":
        return g.atr(h, l, c, n)
    if ad == "stddev":
        return c.rolling(n, min_periods=n).std(ddof=0)
    if ad == "obv":
        return (np.sign(c.diff()).fillna(0.0) * v).cumsum()
    if ad == "ad":
        return ad_cizgisi(h, l, c, v)
    if ad == "chaikin":
        a = ad_cizgisi(h, l, c, v)
        return a.ewm(span=3, adjust=False, min_periods=3).mean() - a.ewm(span=10, adjust=False, min_periods=10).mean()
    if ad == "force":
        return (c.diff() * v).ewm(span=n, adjust=False, min_periods=n).mean()
    if ad == "momentum":
        return 100.0 * c / c.shift(n)
    if ad == "osma":
        return g.macd(c)["histogram"]
    if ad == "macd":
        return g.macd(c)["macd"]
    if ad == "dpo":
        k = n // 2 + 1
        return c.shift(k) - g.sma(c, n)
    if ad == "bears":
        return l - g.ema(c, n)
    if ad == "bulls":
        return h - g.ema(c, n)
    if ad == "rvi":
        return rvi(o, h, l, c, n)
    raise ValueError(f"Bilinmeyen gösterge: {ad!r} (seçenekler: {GOSTERGELER})")


# ------------------------------------------------------------------ seans içi durum makineleri
def vwap_basarisizlik_sinyali(m: pd.DataFrame, seans: np.ndarray, vwap: pd.Series, atr: pd.Series, min_mum: int,
                              min_ust: int, lh_tolerans: float, tampon_atr: float):
    """Seans başına tek sinyal. Aşamalar (hepsi bar kapanışında, geçmişe bakar):
      0 bekle: en az min_mum mum geçti ve min_ust mum VWAP üstünde kapanmış; bir önceki mum VWAP üstünde, bu mum altında ->
        'ilk çatlak' (zirve = çatlağa kadarki seans yüksekliği)
      1 geri test: kapanış VWAP üstüne/eşitine döner; bu mumdan itibaren geri test tepesi izlenir
      2 daha düşük tepe: kapanış tekrar VWAP altına inerse ve geri test tepesi < zirve x (1 - lh_tolerans) -> SHORT sinyali
        (stop = geri test tepesi + tampon_atr x ATR). Kapanış zirveyi aşarsa kurulum geçersiz, başa dönülür.
    Dönen: (short bool dizisi, stop dizisi)."""
    n = len(m)
    h = m["yuksek"].to_numpy(float)
    c = m["kapanis"].to_numpy(float)
    vw = vwap.to_numpy(float)
    a = atr.to_numpy(float)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    onceki_s = None
    faz = 0
    sayi = ust_say = 0
    zirve = rt = seans_tepe = -np.inf
    verildi = False
    for i in range(n):
        if seans[i] != onceki_s:
            onceki_s, faz, sayi, ust_say, zirve, rt, verildi, seans_tepe = seans[i], 0, 0, 0, -np.inf, -np.inf, False, -np.inf
        sayi += 1
        seans_tepe = max(seans_tepe, h[i])
        if np.isnan(vw[i]):
            continue
        if faz == 0:
            if (sayi >= min_mum and ust_say >= min_ust and i > 0 and seans[i - 1] == seans[i]
                    and c[i - 1] > vw[i - 1] and c[i] < vw[i] and not verildi):
                faz, rt, zirve = 1, -np.inf, seans_tepe
            elif c[i] > vw[i]:
                ust_say += 1
        elif faz == 1:
            if c[i] >= vw[i]:
                faz, rt = 2, h[i]
        else:
            if c[i] > zirve:
                faz, rt, ust_say = 0, -np.inf, 0
            elif c[i] >= vw[i]:
                rt = max(rt, h[i])
            else:
                if rt < zirve * (1.0 - lh_tolerans) and not np.isnan(a[i]):
                    sig[i] = True
                    stop[i] = rt + tampon_atr * a[i]
                    verildi = True
                faz, rt, ust_say = 0, -np.inf, 0
    return sig, stop


def parabolik_tetik(m: pd.DataFrame, seans: np.ndarray, uygun_gun: np.ndarray, tetik: str, orl_mum: int, tampon_atr: float,
                    atr: pd.Series):
    """Uygun (parabolik süzgeci geçen) günde seans başına en çok bir SHORT tetiği.
      tetik 'ilk_kirmizi': seansın ilk kırmızı (kapanış < açılış) mumu bulunur (seri içinde); sonraki bir mum kapanışı o mumun
        DİBİNİN altında biterse tetik; ondan önce bir mum kapanışı o mumun TEPESİNİN üstünde biterse o gün geçersiz.
      tetik 'orl': ilk orl_mum mumun dibi (açılış aralığı dibi); aralık bittikten sonra kapanış bu dibin altında biterse tetik.
    stop = tetik mumuna kadarki ilgili tepe + tampon_atr x ATR (ilk_kirmizi: kırmızı mumun tepesi; orl: seans tepesi)."""
    n = len(m)
    o = m["acilis"].to_numpy(float)
    h = m["yuksek"].to_numpy(float)
    l = m["dusuk"].to_numpy(float)
    c = m["kapanis"].to_numpy(float)
    a = atr.to_numpy(float)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    onceki_s = None
    k = 0
    seviye = tepe = np.nan
    bitti = False
    seans_tepe = -np.inf
    for i in range(n):
        if seans[i] != onceki_s:
            onceki_s, k, seviye, tepe, bitti, seans_tepe = seans[i], 0, np.nan, np.nan, False, -np.inf
        k += 1
        seans_tepe = max(seans_tepe, h[i])
        if bitti or not uygun_gun[i]:
            continue
        if tetik == "orl":
            if k <= orl_mum:
                seviye = l[i] if np.isnan(seviye) else min(seviye, l[i])
            elif not np.isnan(seviye) and c[i] < seviye and not np.isnan(a[i]):
                sig[i], stop[i], bitti = True, seans_tepe + tampon_atr * a[i], True
        else:
            if np.isnan(seviye):
                if c[i] < o[i]:
                    seviye, tepe = l[i], h[i]
            else:
                if c[i] > tepe:
                    bitti = True
                elif c[i] < seviye and not np.isnan(a[i]):
                    sig[i], stop[i], bitti = True, tepe + tampon_atr * a[i], True
    return sig, stop
