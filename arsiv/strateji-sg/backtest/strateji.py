"""PDF'lerin ortak paydasından türetilen strateji sinyalleri.

TGC — Trend + Geri Çekilme + Momentum Teyidi (Trend Pullback)
  Kaynak örtüşmesi:
   * 20 Strateji #2  : 10/21 EMA "BÖLGE"ye geri çekilmede trend yönünde giriş, 50 EMA trend filtresi
   * 20 Strateji #6  : 5dk + 1s grafikte EMA14>21>50 dizilimi, bar EMA14/21'e dokununca yön mumuyla giriş
   * 20 Strateji #11 : üst zaman dilimi trend filtresi, RSI>50 ve MACD histogram teyidi
   * 51 Strateji 2.5/7.1/7.4/7.7 : 9-21 EMA destek/direnç, geri çekilmeyi bekle, iki bacaklı geri çekilme
   * Galen Woods     : "Zayıf Geri Çekilme" — trend içi güçsüz düzeltmeden trend yönüne giriş
   * 151 Strateji    : hareketli ortalama / trend takibi + kısa vadeli ortalamaya dönüş birleşimi
BBD — Bollinger/RSI aşırılığından trend yönünde dönüş (opsiyonel ikinci model)
   * 20 Strateji #3, #8 ; 51 Strateji 5.2 ; 151 ortalamaya dönüş ; Galen "Doruğa karşı"
"""
import numpy as np
import pandas as pd
from . import gostergeler as g


def _htf(df, kural):
    return df.resample(kural, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def seans_maskesi(idx, bas, bit):
    """UTC saat aralığı [bas, bit). bas>bit ise gece yarısını aşar."""
    hr = idx.hour + idx.minute / 60.0
    if bas == bit:
        return np.ones(len(idx), bool)
    if bas < bit:
        return np.asarray((hr >= bas) & (hr < bit))
    return np.asarray((hr >= bas) | (hr < bit))


def tgc(df, p):
    """Trend + geri çekilme sinyali. Dönüş: sinyal, stop_mesafe, hedef_mesafe, cikis_sinyal, zorla_kapat."""
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    ef, em, es = g.ema(c, p["ef"]), g.ema(c, p["em"]), g.ema(c, p["es"])
    a = g.atr(h, l, c, 14)
    r = g.rsi(c, p.get("rsi_n", 14))
    _, _, hist = g.macd(c, 12, 26, 9)

    # Üst zaman dilimi trend filtresi (yalnız kapanmış barlar)
    htf = _htf(df, p["htf"])
    hc = htf.close.to_numpy()
    hz = g.htf_hizala(df.index, htf, {"hf": g.ema(hc, p["htf_f"]), "hs": g.ema(hc, p["htf_s"]), "hc": hc})
    htf_up = (hz["hf"] > hz["hs"]) & (hz["hc"] > hz["hs"])
    htf_dn = (hz["hf"] < hz["hs"]) & (hz["hc"] < hz["hs"])

    dizilim_up = (ef > em) & (em > es)
    dizilim_dn = (ef < em) & (em < es)
    # trend gücü: yavaş EMA'nın eğimi (ATR cinsinden, son 'egim_n' bar)
    egim = (es - np.roll(es, p["egim_n"])) / a
    guclu_up = egim > p["egim_min"]
    guclu_dn = egim < -p["egim_min"]

    # geri çekilme: son 'gc_n' bar içinde low, orta EMA'ya (bölge) değdi ama yavaş EMA'yı kapanışta kırmadı
    dokun_up = pd.Series(l <= em + p["bolge_atr"] * a).rolling(p["gc_n"]).max().to_numpy() > 0
    dokun_dn = pd.Series(h >= em - p["bolge_atr"] * a).rolling(p["gc_n"]).max().to_numpy() > 0
    kirmadi_up = pd.Series(c > es).rolling(p["gc_n"]).min().to_numpy() > 0
    kirmadi_dn = pd.Series(c < es).rolling(p["gc_n"]).min().to_numpy() > 0

    # tetik: yön mumu, hızlı EMA üstünde kapanış, momentum teyidi
    hist_up = hist > np.roll(hist, 1)
    hist_dn = hist < np.roll(hist, 1)
    tet_up = (c > o) & (c > ef) & (r > p["rsi_esik"]) & hist_up
    tet_dn = (c < o) & (c < ef) & (r < 100 - p["rsi_esik"]) & hist_dn
    if p.get("kapanis_guc", 0) > 0:      # sinyal mumu gövdesi en az x*ATR
        tet_up &= (c - o) >= p["kapanis_guc"] * a
        tet_dn &= (o - c) >= p["kapanis_guc"] * a

    seans = seans_maskesi(df.index, *p["seans"])
    uzun = htf_up & dizilim_up & guclu_up & dokun_up & kirmadi_up & tet_up & seans
    kisa = htf_dn & dizilim_dn & guclu_dn & dokun_dn & kirmadi_dn & tet_dn & seans
    if p.get("yon", 0) == 1:
        kisa[:] = False
    elif p.get("yon", 0) == -1:
        uzun[:] = False
    sinyal = np.where(uzun, 1, np.where(kisa, -1, 0)).astype(float)

    # stop: son 'sw_n' barın dip/tepesi + tampon, ATR ile sınırlı
    sw_l = pd.Series(l).rolling(p["sw_n"]).min().to_numpy()
    sw_h = pd.Series(h).rolling(p["sw_n"]).max().to_numpy()
    stop_up = c - sw_l + p["tampon_atr"] * a
    stop_dn = sw_h - c + p["tampon_atr"] * a
    stop = np.where(sinyal > 0, stop_up, stop_dn)
    stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    hedef = p["rr"] * stop

    # çıkış sinyali: hızlı EMA orta EMA'nın ters tarafına geçerse (opsiyonel)
    cikis = np.zeros(len(c))
    if p.get("dizilim_cikis", False):
        cikis = np.where(ef < em, -1.0, np.where(ef > em, 1.0, 0.0))
    zorla = np.zeros(len(c), bool)
    if p.get("gun_sonu") is not None:      # UTC saatinde pozisyonu kapat
        zorla = seans_maskesi(df.index, p["gun_sonu"], p["gun_sonu"] + 0.25)
    return sinyal, stop, hedef, cikis, zorla


def bbd(df, p):
    """Trend yönünde Bollinger + RSI aşırılığından dönüş."""
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = g.atr(h, l, c, 14)
    m, ub, lb = g.bollinger(c, p["bb_n"], p["bb_k"])
    r = g.rsi(c, p["rsi_n"])
    htf = _htf(df, p["htf"])
    hc = htf.close.to_numpy()
    hz = g.htf_hizala(df.index, htf, {"hf": g.ema(hc, p["htf_f"]), "hs": g.ema(hc, p["htf_s"]), "hc": hc})
    htf_up = (hz["hf"] > hz["hs"]) & (hz["hc"] > hz["hs"])
    htf_dn = (hz["hf"] < hz["hs"]) & (hz["hc"] < hz["hs"])
    asiri_dn = pd.Series((l < lb) & (r < p["rsi_alt"])).rolling(p["pencere"]).max().to_numpy() > 0
    asiri_up = pd.Series((h > ub) & (r > 100 - p["rsi_alt"])).rolling(p["pencere"]).max().to_numpy() > 0
    don_up = (c > o) & (c > lb)
    don_dn = (c < o) & (c < ub)
    if p.get("guclu_don"):                 # önceki barın tepesi/dibi aşılarak dönüş
        don_up &= c > np.roll(h, 1)
        don_dn &= c < np.roll(l, 1)
    seans = seans_maskesi(df.index, *p["seans"])
    uzun = htf_up & asiri_dn & don_up & seans
    kisa = htf_dn & asiri_up & don_dn & seans
    sinyal = np.where(uzun, 1, np.where(kisa, -1, 0)).astype(float)
    sw_l = pd.Series(l).rolling(p["sw_n"]).min().to_numpy()
    sw_h = pd.Series(h).rolling(p["sw_n"]).max().to_numpy()
    stop = np.where(sinyal > 0, c - sw_l, sw_h - c) + p["tampon_atr"] * a
    stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    if p["hedef"] == "orta":
        hedef = np.where(sinyal > 0, m - c, c - m)
        hedef = np.maximum(hedef, p["hedef_min_r"] * stop)
    else:
        hedef = p["rr"] * stop
    return sinyal, stop, hedef, np.zeros(len(c)), np.zeros(len(c), bool)


_IND = {}


def _ind(df, anahtar, f):
    k = (id(df), anahtar)
    if k not in _IND:
        _IND[k] = f()
    return _IND[k]


def seans_vwap(df, k=2.0, gun_bas_saat=0):
    """Günlük sıfırlanan VWAP ve standart sapma bantları (hacim yoksa tipik fiyat eşit ağırlık)."""
    tp = ((df.high + df.low + df.close) / 3).to_numpy()
    v = df.volume.to_numpy().astype(float)
    if not np.isfinite(v).all() or v.sum() == 0 or np.nanstd(v) == 0:
        v = np.ones(len(tp))
    v = np.where(v > 0, v, 1e-9)
    gun = (df.index - pd.Timedelta(hours=gun_bas_saat)).floor("D")
    s = pd.DataFrame({"pv": tp * v, "v": v, "p2v": tp * tp * v, "g": gun})
    cs = s.groupby("g")[["pv", "v", "p2v"]].cumsum()
    vw = (cs.pv / cs.v).to_numpy()
    var = np.maximum(cs.p2v / cs.v - vw * vw, 0)
    sd = np.sqrt(var).to_numpy() if hasattr(var, "to_numpy") else np.sqrt(var)
    return vw, vw + k * sd, vw - k * sd


def tda(df, p):
    """Trend içi dip/tepe dönüşü (Çift RSI + BB/VWAP aşırılık + dönüş mumu).

    Uzun: HTF yükseliş (HTF RSI > 50 ve/veya HTF EMA dizilimi) + LTF aşırı satım
    (RSI < alt eşik veya BB alt bandı altı) son 'pencere' bar içinde + yükseliş mumu
    (opsiyonel: önceki barın tepesini aşarak kapanış). Kısa: simetrik.
    """
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = _ind(df, ("atr",), lambda: g.atr(h, l, c, 14))
    r = _ind(df, ("rsi", p["rsi_n"]), lambda: g.rsi(c, p["rsi_n"]))
    m, ub, lb = _ind(df, ("bb", p["bb_n"], p["bb_k"]), lambda: g.bollinger(c, p["bb_n"], p["bb_k"]))

    def htf_hesap():
        htf = _htf(df, p["htf"])
        hc = htf.close.to_numpy()
        return g.htf_hizala(df.index, htf, {"hr": g.rsi(hc, 14), "hf": g.ema(hc, p["htf_f"]),
                                            "hs": g.ema(hc, p["htf_s"]), "hc": hc})
    hz = _ind(df, ("htf", p["htf"], p["htf_f"], p["htf_s"]), htf_hesap)
    up = np.ones(len(c), bool)
    dn = np.ones(len(c), bool)
    if p.get("htf_rsi", True):
        up &= hz["hr"] > p.get("htf_rsi_esik", 50)
        dn &= hz["hr"] < 100 - p.get("htf_rsi_esik", 50)
    if p.get("htf_ema", True):
        up &= (hz["hf"] > hz["hs"]) & (hz["hc"] > hz["hs"])
        dn &= (hz["hf"] < hz["hs"]) & (hz["hc"] < hz["hs"])
    if p.get("ltf_ema", 0):
        e = _ind(df, ("ema", p["ltf_ema"]), lambda: g.ema(c, p["ltf_ema"]))
        up &= c > e
        dn &= c < e

    mod = p.get("asiri", "rsi")
    if mod == "rsi":
        ad, au = r < p["rsi_alt"], r > 100 - p["rsi_alt"]
    elif mod == "bb":
        ad, au = l < lb, h > ub
    elif mod == "vwap":
        vw, vu, vl = _ind(df, ("vwap", p["vwap_k"]), lambda: seans_vwap(df, p["vwap_k"]))
        ad, au = l < vl, h > vu
    else:  # rsi+bb
        ad, au = (r < p["rsi_alt"]) & (l < lb), (r > 100 - p["rsi_alt"]) & (h > ub)
    w = p["pencere"]
    ad = pd.Series(ad).rolling(w, min_periods=1).max().to_numpy() > 0
    au = pd.Series(au).rolling(w, min_periods=1).max().to_numpy() > 0

    don_up = c > o
    don_dn = c < o
    if p.get("guclu_don", True):
        don_up &= c > np.roll(h, 1)
        don_dn &= c < np.roll(l, 1)
    seans = seans_maskesi(df.index, *p["seans"])
    uzun = up & ad & don_up & seans
    kisa = dn & au & don_dn & seans
    if p.get("yon", 0) == 1:
        kisa[:] = False
    elif p.get("yon", 0) == -1:
        uzun[:] = False
    sinyal = np.where(uzun, 1, np.where(kisa, -1, 0)).astype(float)

    sw_l = pd.Series(l).rolling(p["sw_n"]).min().to_numpy()
    sw_h = pd.Series(h).rolling(p["sw_n"]).max().to_numpy()
    stop = np.where(sinyal > 0, c - sw_l, sw_h - c) + p["tampon_atr"] * a
    stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    if p.get("hedef", "rr") == "orta":
        hedef = np.maximum(np.where(sinyal > 0, ub - c, c - lb), p["hedef_min_r"] * stop)
    else:
        hedef = p["rr"] * stop
    cikis = np.zeros(len(c))
    if p.get("rsi_cikis", 0):   # Çift RSI: LTF RSI karşı aşırı bölgeye girince çık
        cikis = np.where(r > p["rsi_cikis"], -1.0, np.where(r < 100 - p["rsi_cikis"], 1.0, 0.0))
    zorla = np.zeros(len(c), bool)
    if p.get("gun_sonu") is not None:
        zorla = seans_maskesi(df.index, p["gun_sonu"], p["gun_sonu"] + 0.25)
    return sinyal, stop, hedef, cikis, zorla


def yerel_saat(idx, tz):
    """UTC indexini yerel saate (ondalık saat) ve yerel güne çevirir (yaz saati dahil)."""
    loc = idx.tz_localize("UTC").tz_convert(tz)
    return (loc.hour + loc.minute / 60.0).to_numpy(), loc.normalize().tz_localize(None).to_numpy()


def kutu_kirilim(df, p):
    """Seans kutusu kırılımı (20 Strateji #7, 51 Strateji 5.4/1.4, Galen sıkışıklık bölgesi).

    Her gün yerel [kutu_bas, kutu_bit) aralığındaki tepe/dip = kutu.
    kutu_bit'ten sonra 'gecerli' saat içinde kapanış kutu tepesi + tampon*kutu'yu aşarsa uzun,
    kutu dibi - tampon*kutu altına inerse kısa (günde tek işlem).
    Stop: kutunun karşı ucu (stop_kutu=1) veya ortası (0.5); hedef: rr*risk. Seans sonunda kapat.
    """
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = _ind(df, ("atr",), lambda: g.atr(h, l, c, 14))
    hr, gun = _ind(df, ("yerel", p["tz"]), lambda: yerel_saat(df.index, p["tz"]))
    kb, ke = p["kutu_bas"], p["kutu_bit"]
    ic = (hr >= kb) & (hr < ke)
    s = pd.DataFrame({"g": gun, "h": np.where(ic, h, np.nan), "l": np.where(ic, l, np.nan)})
    kh = s.groupby("g").h.transform("max").to_numpy()
    kl = s.groupby("g").l.transform("min").to_numpy()
    boy = kh - kl
    pencere = (hr >= ke) & (hr < ke + p["gecerli"])
    # günlük ATR (önceki günlerden) ile kutu genişliği filtresi
    gunluk = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    gatr = g.atr(gunluk.high.values, gunluk.low.values, gunluk.close.values, 14)
    gz = g.htf_hizala(df.index, gunluk, {"gatr": gatr})["gatr"]
    oran = boy / gz
    filt = (oran >= p.get("kutu_min", 0)) & (oran <= p.get("kutu_max", 9))
    tam = p["tampon"] * boy
    up = pencere & filt & (c > kh + tam)
    dn = pencere & filt & (c < kl - tam)
    if p.get("htf_ema"):
        hz = _ind(df, ("kk_htf", p["htf"], p["htf_f"], p["htf_s"]), lambda: (lambda ht: g.htf_hizala(
            df.index, ht, {"f": g.ema(ht.close.values, p["htf_f"]), "s": g.ema(ht.close.values, p["htf_s"])}))(_htf(df, p["htf"])))
        up &= hz["f"] > hz["s"]
        dn &= hz["f"] < hz["s"]
    if p.get("yon", 0) == 1:
        dn[:] = False
    elif p.get("yon", 0) == -1:
        up[:] = False
    ham = np.where(up, 1, np.where(dn, -1, 0))
    # günde yalnız ilk sinyal
    t = pd.DataFrame({"g": gun, "s": ham})
    t["ilk"] = (t.s != 0) & (t.assign(nz=(t.s != 0).astype(int)).groupby("g").nz.cumsum() == 1)
    sinyal = np.where(t.ilk.to_numpy(), ham, 0).astype(float)
    sk = p.get("stop_kutu", 1.0)
    stop = np.where(sinyal > 0, c - (kh - sk * boy), (kl + sk * boy) - c)
    stop = np.maximum(stop, p.get("stop_min_atr", 0.5) * a)
    hedef = p["rr"] * stop
    zorla = (hr >= p["kapat"]) & (hr < p["kapat"] + 0.25)
    return sinyal, stop, hedef, np.zeros(len(c)), zorla


def kanal_kirilim(df, p):
    """Trend yönünde kanal (Donchian) kırılımı — 51 Strateji 3.6/1.4, 151 kanal, Galen sıkışıklık.

    Uzun: HTF trend yukarı + kapanış önceki 'kn' barın tepesinin üstünde (+ opsiyonel sıkışma filtresi:
    kanal genişliği <= sikisma*ATR*kn^0.5). Stop: ATR katı veya kanal ortası; hedef: rr*risk.
    """
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = _ind(df, ("atr",), lambda: g.atr(h, l, c, 14))
    dh, dl = _ind(df, ("don", p["kn"]), lambda: g.donchian(h, l, p["kn"]))
    dh1, dl1 = np.roll(dh, 1), np.roll(dl, 1)

    def htf_hesap():
        ht = _htf(df, p["htf"])
        hc = ht.close.to_numpy()
        return g.htf_hizala(df.index, ht, {"f": g.ema(hc, p["htf_f"]), "s": g.ema(hc, p["htf_s"]), "c": hc})
    hz = _ind(df, ("kk2", p["htf"], p["htf_f"], p["htf_s"]), htf_hesap)
    up = (hz["f"] > hz["s"]) & (hz["c"] > hz["f"]) if p.get("htf_sik") else (hz["f"] > hz["s"])
    dn = (hz["f"] < hz["s"]) & (hz["c"] < hz["f"]) if p.get("htf_sik") else (hz["f"] < hz["s"])
    bu = (c > dh1) & (np.roll(c, 1) <= np.roll(dh1, 1))
    bd = (c < dl1) & (np.roll(c, 1) >= np.roll(dl1, 1))
    if p.get("sikisma", 0) > 0:
        gen = (dh1 - dl1) / (a * np.sqrt(p["kn"]))
        bu &= gen <= p["sikisma"]
        bd &= gen <= p["sikisma"]
    seans = seans_maskesi(df.index, *p["seans"])
    uzun = up & bu & seans
    kisa = dn & bd & seans
    if p.get("yon", 0) == 1:
        kisa[:] = False
    elif p.get("yon", 0) == -1:
        uzun[:] = False
    sinyal = np.where(uzun, 1, np.where(kisa, -1, 0)).astype(float)
    if p.get("stop_mod", "atr") == "orta":
        orta = (dh1 + dl1) / 2
        stop = np.where(sinyal > 0, c - orta, orta - c)
        stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    else:
        stop = p["stop_atr"] * a
    hedef = p["rr"] * stop
    return sinyal, stop, hedef, np.zeros(len(c)), np.zeros(len(c), bool)


def gunluk_seviyeler(df, tz, gun_bas=0.0):
    """Önceki işlem gününün H/L/C değerleri ve pivot/CPR seviyeleri (yerel gün, gun_bas saatinde başlar)."""
    loc = df.index.tz_localize("UTC").tz_convert(tz)
    gun = (loc - pd.Timedelta(hours=gun_bas)).normalize().tz_localize(None)
    g_ = pd.DataFrame({"h": df.high.to_numpy(), "l": df.low.to_numpy(), "c": df.close.to_numpy(), "g": gun})
    d = g_.groupby("g").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
    p = (d.h + d.l + d.c) / 3
    bc = (d.h + d.l) / 2
    tc = 2 * p - bc
    lv = pd.DataFrame({"pdh": d.h, "pdl": d.l, "pdc": d.c, "P": p, "TC": np.maximum(tc, bc), "BC": np.minimum(tc, bc),
                       "R1": 2 * p - d.l, "S1": 2 * p - d.h, "R2": p + (d.h - d.l), "S2": p - (d.h - d.l)})
    tr = np.maximum(d.h - d.l, np.maximum((d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()))
    lv["datr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    lv["aralik"] = d.h - d.l
    lv = lv.shift(1)  # yalnızca ÖNCEKİ günün bilgisi
    return lv.reindex(gun).to_numpy(), list(lv.columns), gun.to_numpy(), \
        ((loc.hour + loc.minute / 60.0) - gun_bas) % 24


def gunluk_kirilim(df, p):
    """Önceki gün seviyesi kırılımı (51 Strateji 2.7 CPR, 2.3 pivot; 20 Strateji #7 kutu; Galen sıkışıklık).

    seviye: 'pdhl' (önceki gün tepe/dip), 'cpr' (TC/BC), 'r1s1'.
    daralma: önceki gün aralığı / günlük ATR <= dar (NR / dar CPR => trend günü beklentisi).
    Uzun: seans içinde kapanış üst seviyenin üstünde (günün ilk kırılımı). Stop: stop_atr*ATR(1s) veya seviyenin
    karşı tarafı; hedef rr*risk. Seans sonunda kapat.
    """
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = _ind(df, ("atr",), lambda: g.atr(h, l, c, 14))
    lv, kol, gun, hr = _ind(df, ("glv", p["tz"], p.get("gun_bas", 0.0)),
                            lambda: gunluk_seviyeler(df, p["tz"], p.get("gun_bas", 0.0)))
    L = {k: lv[:, i] for i, k in enumerate(kol)}
    if p["seviye"] == "pdhl":
        ust, alt = L["pdh"], L["pdl"]
    elif p["seviye"] == "cpr":
        ust, alt = L["TC"], L["BC"]
    else:
        ust, alt = L["R1"], L["S1"]
    if p.get("dar_mod", "aralik") == "aralik":
        dar = L["aralik"] / L["datr"] <= p["dar"]
    else:  # CPR genişliği / günlük ATR
        dar = (L["TC"] - L["BC"]) / L["datr"] <= p["dar"]
    pencere = (hr >= p["bas"]) & (hr < p["bit"])
    up = pencere & dar & (c > ust) & (np.roll(c, 1) <= ust)
    dn = pencere & dar & (c < alt) & (np.roll(c, 1) >= alt)
    if p.get("htf_ema"):
        def hh():
            ht = _htf(df, p["htf"])
            hc = ht.close.to_numpy()
            return g.htf_hizala(df.index, ht, {"f": g.ema(hc, p["htf_f"]), "s": g.ema(hc, p["htf_s"]), "c": hc})
        hz = _ind(df, ("gk_htf", p["htf"], p["htf_f"], p["htf_s"]), hh)
        up &= hz["f"] > hz["s"]
        dn &= hz["f"] < hz["s"]
        if p.get("htf_ust"):   # Brooks: son kapanış 20 EMA'nın doğru tarafında (= yavaş EMA o yönde eğimli)
            up &= hz["c"] > hz["s"]
            dn &= hz["c"] < hz["s"]
    if p.get("yon", 0) == 1:
        dn[:] = False
    elif p.get("yon", 0) == -1:
        up[:] = False
    ham = np.where(up, 1, np.where(dn, -1, 0))
    t = pd.DataFrame({"g": gun, "s": ham})
    nz = (t.s != 0).astype(int)
    ilk = (t.s != 0) & (nz.groupby(t.g).cumsum() <= p.get("gunluk_max", 1))   # Brooks: ikinci girişler (varsayılan 1)
    sinyal = np.where(ilk.to_numpy(), ham, 0).astype(float)
    sm = p.get("stop_mod", "atr")
    if sm == "seviye":     # kırılan seviyenin karşı tarafı (kutu/CPR karşı ucu)
        stop = np.where(sinyal > 0, c - alt, ust - c)
    elif sm == "mum":      # 51 Strateji 2.7: kırılım mumunun dibi/tepesi + tampon
        stop = np.where(sinyal > 0, c - l, h - c) + p.get("mum_tampon", 0.2) * a
    else:
        stop = p["stop_atr"] * a
    if sm != "atr":
        stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    if p.get("hedef_mod", "rr") == "pivot":   # bir sonraki pivot seviyesi (R1->R2, S1->S2), en az hedef_min_r
        hedef = np.where(sinyal > 0, L["R2"] - c, c - L["S2"])
        hedef = np.maximum(hedef, p.get("hedef_min_r", 1.0) * stop)
    else:
        hedef = p["rr"] * stop
    zorla = (hr >= p["kapat"]) & (hr < p["kapat"] + 1.0)
    return sinyal, stop, hedef, np.zeros(len(c)), zorla


def gunluk_donus(df, p):
    """Geniş CPR (aralık günü) -> S1/R1'den dönüş (51 Strateji 2.7 'CPR geniştir' kolu).
    Uzun: low S1'e (veya pdl) değip kapanış seviyenin üstünde ve yükseliş mumu. Stop: mum dibi - tampon*ATR;
    hedef: pivot P'ye uzaklık (en az hedef_min_r*risk)."""
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    a = _ind(df, ("atr",), lambda: g.atr(h, l, c, 14))
    lv, kol, gun, hr = _ind(df, ("glv", p["tz"], p.get("gun_bas", 0.0)),
                            lambda: gunluk_seviyeler(df, p["tz"], p.get("gun_bas", 0.0)))
    L = {k: lv[:, i] for i, k in enumerate(kol)}
    ust, alt = (L["R1"], L["S1"]) if p.get("d_seviye", "r1s1") == "r1s1" else (L["pdh"], L["pdl"])
    genis = (L["TC"] - L["BC"]) / L["datr"] >= p["genis"]
    pencere = (hr >= p["bas"]) & (hr < p["bit"])
    up = pencere & genis & (l <= alt) & (c > alt) & (c > o)
    dn = pencere & genis & (h >= ust) & (c < ust) & (c < o)
    ham = np.where(up, 1, np.where(dn, -1, 0))
    t = pd.DataFrame({"g": gun, "s": ham})
    nz = (t.s != 0).astype(int)
    ilk = (t.s != 0) & (nz.groupby(t.g).cumsum() == 1)
    sinyal = np.where(ilk.to_numpy(), ham, 0).astype(float)
    stop = np.where(sinyal > 0, c - l, h - c) + p["d_tampon"] * a
    stop = np.clip(stop, p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    hedef = np.maximum(np.where(sinyal > 0, L["P"] - c, c - L["P"]), p["hedef_min_r"] * stop)
    zorla = (hr >= p["kapat"]) & (hr < p["kapat"] + 1.0)
    return sinyal, stop, hedef, np.zeros(len(c)), zorla


def cpr_birlesik(df, p):
    """Dar CPR günlerinde kırılım, geniş CPR günlerinde dönüş — tek pozisyon, aynı motor.
    Hedef ve stop sinyal türüne göre seçilir."""
    s1, st1, h1, _, z1 = gunluk_kirilim(df, p)
    if not p.get("donus", False):
        return s1, st1, h1, np.zeros(len(s1)), z1
    s2, st2, h2, _, _ = gunluk_donus(df, p)
    sinyal = np.where(s1 != 0, s1, s2)
    stop = np.where(s1 != 0, st1, st2)
    hedef = np.where(s1 != 0, h1, h2)
    return sinyal, stop, hedef, np.zeros(len(s1)), z1
