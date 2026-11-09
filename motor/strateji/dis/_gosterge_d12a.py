"""D12-A göstergeleri (Brooks / Farley / Halsey tam-okuma aileleri). Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar
olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  ayna, mum_yapisi, trend_gucu_boga, trend_gunu_skoru, dikenli_tel_barlari, dikenli_tel_boga,
  kirilim_olcu_durumu, ilk_olay, hedef_gecerli, stop_sinirla
Yönlü mantık yalnız LONG için yazılır; short, `ayna(m)` (fiyatların işareti çevrilmiş kopyası) üzerinden aynı kodla üretilir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g


def ayna(m: pd.DataFrame) -> pd.DataFrame:
    """Fiyat aynası: acilis/kapanis -> -x, yuksek -> -dusuk, dusuk -> -yuksek. Long mantığı bunun üzerinde short üretir."""
    hacim = m["hacim"] if "hacim" in m else 1.0
    return pd.DataFrame({"acilis": -m["acilis"], "yuksek": -m["dusuk"], "dusuk": -m["yuksek"], "kapanis": -m["kapanis"],
                         "hacim": hacim}, index=m.index)


def mum_yapisi(m: pd.DataFrame) -> pd.DataFrame:
    """aralik, govde_oran (|C-O|/aralık), konum ((C-L)/aralık), boga, ayi. Aralık 0 ise oranlar NaN (karşılaştırmalar False)."""
    o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    ar = h - l
    pay = ar.where(ar > 0)
    return pd.DataFrame({"aralik": ar, "govde_oran": (k - o).abs() / pay, "konum": (k - l) / pay,
                         "boga": k > o, "ayi": k < o})


def _b(x) -> pd.Series:
    return x.fillna(False).astype(bool)


def ilk_olay(kos: pd.Series) -> pd.Series:
    """Koşulun yalnız False->True geçişi."""
    kos = _b(kos)
    return kos & ~kos.shift(1, fill_value=False)


def hedef_gecerli(kapanis: pd.Series, hedef):
    """Long için hedef kapanışın üstünde değilse NaN."""
    if hedef is None:
        return None
    return hedef.where(hedef > kapanis)


def stop_sinirla(stop: pd.Series, kapanis: pd.Series, atr: pd.Series, maks: float) -> pd.Series:
    """Long stopunu en çok maks x ATR uzağa çeker (maks <= 0: sınırsız)."""
    if not maks or maks <= 0:
        return stop
    return np.maximum(stop, kapanis - maks * atr)


def trend_gucu_boga(m: pd.DataFrame, atr: pd.Series, ema_n: int = 20, n: int = 20, oran: float = 0.8,
                    egim_atr: float = 0.5, tbar_oran: float = 0.3) -> pd.Series:
    """Ölçülebilir 'güçlü boğa trendi' (Brooks'un öznel tanımının karşılığı; kitapta sayı yok -> VARSAYIM):
    son n kapanışın >= oran'ı EMA üstünde VE EMA son n//2 barda >= egim_atr x ATR yükselmiş VE son n barın >= tbar_oran'ı
    güçlü boğa trend barı (boğa, gövde >= %50). Short için ayna(m) üzerinde çağrılır."""
    k = m["kapanis"]
    e = g.ema(k, ema_n)
    yp = mum_yapisi(m)
    ust = (k > e).astype(float).rolling(n, min_periods=n).mean() >= oran
    egim = (e - e.shift(max(n // 2, 1))) >= egim_atr * atr
    tbar = (yp["boga"] & (yp["govde_oran"] >= 0.5)).astype(float).rolling(n, min_periods=n).mean() >= tbar_oran
    return _b(ust & egim & tbar)


def trend_gunu_skoru(m: pd.DataFrame, atr: pd.Series, n: int = 24, ema_n: int = 20, ma_dok_n: int = 20,
                     pb_atr: float = 3.0, ov_maks: float = 0.55, govde_min: float = 0.55, tbar_min: float = 0.5) -> pd.DataFrame:
    """Brooks 'güç işaretleri' (boğa yönü) -> 6 ölçülebilir madde, her biri 0/1; `skor` toplamı (0-6):
      tbar    son n barın >= tbar_min'i güçlü boğa trend barı (boğa, gövde >= %50)
      ortusme ardışık barların aralık örtüşmesi ortalaması <= ov_maks (gövdeler az örtüşür)
      govde   ortalama gövde/aralık >= govde_min (kuyruklar küçük)
      ma_yok  son ma_dok_n barın hiçbirinde düşük EMA'ya değmedi (EMA'ya 20+ bar dokunmama)
      karsi   son n barda EMA'nın altında ardışık 2 kapanış yok
      gerici  son n barda 6 barlık zirveden kapanışa düşüş <= pb_atr x ATR (geri çekilmeler küçük)
    Gün sınırı kullanılmaz (kayan pencere). Short için ayna(m) üzerinde çağrılır."""
    o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    e = g.ema(k, ema_n)
    yp = mum_yapisi(m)
    tbar = (yp["boga"] & (yp["govde_oran"] >= 0.5)).astype(float).rolling(n, min_periods=n).mean() >= tbar_min
    ar = (h - l).where((h - l) > 0)
    ov = ((np.minimum(h, h.shift(1)) - np.maximum(l, l.shift(1))).clip(lower=0) / ar)
    ortusme = ov.rolling(n, min_periods=n).mean() <= ov_maks
    govde = yp["govde_oran"].rolling(n, min_periods=n).mean() >= govde_min
    ma_yok = (l > e).astype(float).rolling(ma_dok_n, min_periods=ma_dok_n).min() >= 1.0
    alt2 = (k < e) & (k.shift(1) < e.shift(1))
    karsi = alt2.astype(float).rolling(n, min_periods=n).max() == 0
    pb = (h.rolling(6, min_periods=1).max() - k).rolling(n, min_periods=n).max()
    gerici = pb <= pb_atr * atr
    cols = {"tbar": tbar, "ortusme": ortusme, "govde": govde, "ma_yok": ma_yok, "karsi": karsi, "gerici": gerici}
    out = pd.DataFrame({a: _b(v) for a, v in cols.items()})
    out["skor"] = out.sum(axis=1).astype(int)
    return out


def dikenli_tel_barlari(m: pd.DataFrame, doji_oran: float = 0.25, ort_oran: float = 0.5) -> pd.Series:
    """Brooks dikenli tel (kitap ölçütü): t. barda biten 3 bar (t-2, t-1, t) için ORTADAKİ barın aralığının > ort_oran'ı hem sol
    hem sağ komşunun aralığı içinde kalıyorsa VE üç barın en az biri doji (gövde/aralık < doji_oran) ise True."""
    h, l = m["yuksek"], m["dusuk"]
    yp = mum_yapisi(m)
    ar = (h - l).where((h - l) > 0)
    # orta bar = t-1: örtüşme(t-1, t-2) ve örtüşme(t-1, t), t-1 aralığına oranla
    orta_ar = ar.shift(1)
    ov_sol = (np.minimum(h.shift(1), h.shift(2)) - np.maximum(l.shift(1), l.shift(2))).clip(lower=0) / orta_ar
    ov_sag = (np.minimum(h.shift(1), h) - np.maximum(l.shift(1), l)).clip(lower=0) / orta_ar
    doji = (yp["govde_oran"] < doji_oran).astype(float)
    var_doji = doji.rolling(3, min_periods=3).max() > 0
    return _b((ov_sol > ort_oran) & (ov_sag > ort_oran) & var_doji)


def dikenli_tel_boga(h, l, k, ema, atr, tel, guclu_ayi, guclu_boga, bekle: int, ma_oran: float, ma_filtre: bool, olcu: float,
                     tampon: float):
    """Dikenli tel BAŞARISIZ AŞAĞI KIRILIM -> LONG (short ayna ile). numpy dizileri, uzunluk n.
    Bölge: ardışık `tel` barlarının birleşimi (min dip, max tepe). Bölge, tel olmayan bir barda VEYA bölgeden çıkan güçlü trend barında
    (kapanış dibin altı + guclu_ayi / tepenin üstü + guclu_boga; çıkış barı komşusuyla örtüştüğü için tel sayılabilir) biter.
    Aşağı çıkış barı 'çıkış barı' x'tir (guclu_ayi ve kapanış bölge dibinin altı). Sonraki <= bekle barda kapanış x'in zirvesini aşarsa (kitap: x'in zirvesinin 1 tik üstüne ters stop;
    stop dolumu kapanışa yaklaşıklanır -> TUTUCU) sinyal. x'ten sonra kapanışı x'in kapanışının altında bir guclu_ayi daha gelirse
    (ardışık iki trend barı çıkışı) fade edilmez. ma_filtre: bölge kapanışlarının >= ma_oran'ı EMA üstündeyse (long yönü).
    Dönen: (sinyal bool, stop, hedef) — stop: x'ten bu yana en düşük dip - tampon x ATR; hedef: kapanış + olcu x bölge yüksekliği."""
    n = len(k)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    hedef = np.full(n, np.nan)
    inz = False
    zbas = 0
    zlo = zhi = 0.0
    armed = False
    ax = -1
    minlow = 0.0
    zh = 0.0
    for i in range(n):
        if armed:
            if i - ax > bekle:
                armed = False
            elif k[i] > h[ax]:
                sig[i] = True
                stop[i] = minlow - tampon * atr[i]
                hedef[i] = k[i] + olcu * zh
                armed = False
            else:
                minlow = min(minlow, l[i])
                if guclu_ayi[i] and k[i] < k[ax]:
                    armed = False
        if inz:
            asagi = k[i] < zlo and guclu_ayi[i]
            yukari = k[i] > zhi and guclu_boga[i]
            if asagi or yukari or not tel[i]:
                inz = False
                if asagi:
                    ust = np.mean(k[zbas:i] > ema[zbas:i])
                    if (not ma_filtre) or ust >= ma_oran:
                        armed = True
                        ax = i
                        minlow = l[i]
                        zh = zhi - zlo
            else:
                zlo = min(zlo, l[i])
                zhi = max(zhi, h[i])
        elif tel[i]:
            inz = True
            zbas = i - 2
            zlo = min(l[i - 2], l[i - 1], l[i])
            zhi = max(h[i - 2], h[i - 1], h[i])
    return sig, stop, hedef


def kirilim_olcu_durumu(h, l, k, guclu_ayi, atr, n: int, rng_atr: float, min_atr: float, bekle: int, olcu: float):
    """Aralık AŞAĞI kırılımı sonrası ölçülü hareket seviyesine varış (long mantığı; short ayna ile).
    Aralık: son n barın (H.max - L.min) <= rng_atr x ATR ve >= min_atr x ATR. Kırılım: kapanış aralık dibinin altı. Referans aralık
    kırılımdan itibaren dondurulur; <= bekle bar içinde kapanış aralığa geri dönerse iptal. Seviye = dip - olcu x yükseklik; kapanış
    seviyeye ulaşınca (TUTUCU: kapanış, dokunuş değil) sinyal. Dönen dizi: sinyal, dip (LL), yükseklik (H), kırılımdan beri güçlü
    ayı bar sayısı (ns)."""
    N = len(k)
    hh = pd.Series(h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    sig = np.zeros(N, dtype=bool)
    o_ll = np.full(N, np.nan)
    o_h = np.full(N, np.nan)
    o_ns = np.zeros(N, dtype=int)
    aktif = False
    rl = rh = 0.0
    bas = 0
    ns = 0
    for i in range(N):
        if aktif:
            if i - bas > bekle or k[i] > rl:
                aktif = False
            else:
                if guclu_ayi[i]:
                    ns += 1
                if k[i] <= rl - olcu * rh:
                    sig[i], o_ll[i], o_h[i], o_ns[i] = True, rl, rh, ns
                    aktif = False
        if not aktif and not sig[i] and not np.isnan(hh[i]) and not np.isnan(atr[i]):
            yuk = hh[i] - ll[i]
            if min_atr * atr[i] <= yuk <= rng_atr * atr[i] and k[i] < ll[i]:
                aktif = True
                rl, rh, bas = ll[i], yuk, i
                ns = 1 if guclu_ayi[i] else 0
                if k[i] <= rl - olcu * rh:
                    sig[i], o_ll[i], o_h[i], o_ns[i] = True, rl, rh, ns
                    aktif = False
    return sig, o_ll, o_h, o_ns
