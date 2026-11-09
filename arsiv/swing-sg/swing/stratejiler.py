"""Üç ortak-payda swing stratejisi: haftalık grafikte yön, günlük grafikte işlem.

S1 Trend Geri Çekilme  : Ladha (Strateji 3), Farley, Velez, Ghosh (Bounce), Leandro, Ochoa, Lee&Tryde
S2 Sıkışma Kırılımı     : Ladha (Strateji 2), Boxer, Bulkowski, Farley (NR7/daralma), Jea Yu, Kathy Lien
S3 Aşırı Satım Dönüşü   : Munroe (HA+Stokastik), TMP RSI, Ladha (Strateji 10), Thomsett, Graham, Velez
"""
import numpy as np
import pandas as pd

from . import gostergeler as g
from .veri import haftalik, haftalik_gunluge


# ---------------------------------------------------------------- haftalık yön
def haftalik_yon(df, mod="ema10"):
    w = haftalik(df)
    wc = w["Close"]
    if mod == "ema10":
        e = g.ema(wc, 10)
        yon = np.where((wc > e) & (e > e.shift()), 1, np.where((wc < e) & (e < e.shift()), -1, 0))
    elif mod == "ema10_30":
        e1, e2 = g.ema(wc, 10), g.ema(wc, 30)
        yon = np.where((e1 > e2) & (wc > e2), 1, np.where((e1 < e2) & (wc < e2), -1, 0))
    elif mod == "macd":
        m, s, hst = g.macd(wc)
        yon = np.where((m > s) & (wc > g.ema(wc, 20)), 1, np.where((m < s) & (wc < g.ema(wc, 20)), -1, 0))
    elif mod == "ha":  # Munroe: haftalık Heikin Ashi rengi + 100 SMA tarafı (haftalık 20 SMA ~ 100 gün)
        ho, hc = g.heikin_ashi(w)
        s = g.sma(wc, 20)
        yon = np.where((hc > ho) & (wc > s), 1, np.where((hc < ho) & (wc < s), -1, 0))
    elif mod == "yok":
        yon = np.ones(len(w))
    else:
        raise ValueError(mod)
    return haftalik_gunluge(pd.Series(yon, index=w.index, dtype=float), df.index).fillna(0)


def rejim(df, mod, e=None):
    """Sınıfın referans endeksine göre piyasa rejimi (+1 boğa, -1 ayı, 0 nötr). Endeks yoksa +1."""
    if not mod or e is None:
        return pd.Series(1.0, index=df.index)
    e = e[e.index <= df.index[-1]]
    if mod == "sma200":  # günlük: endeks kapanışı 200 günlük ortalamanın üzerinde
        ec = e["Close"]
        r = pd.Series(np.where(ec > g.sma(ec, 200), 1.0, -1.0), index=e.index)
        r = r.shift(1)  # t günü kararı için t-1 kapanışı yeterli; muhafazakâr olmak için bir gün kaydır
        return r.reindex(df.index, method="ffill").fillna(0)
    return haftalik_yon(e, mod).reindex(df.index, method="ffill").fillna(0)


def _cerceve(df, a, long, short, stop_long, stop_short, exit_long, exit_short, limit_long=None,
             limit_short=None, **attrs):
    rm = attrs.pop("rejim_mod", None)
    endeks = attrs.pop("endeks", None)
    if rm:
        rj = rejim(df, rm, endeks)
        long = long & (rj > 0)
        short = short & (rj < 0)
    sig = pd.DataFrame({
        "atr": a, "long": long.fillna(False).astype(bool), "short": short.fillna(False).astype(bool),
        "stop_long": stop_long, "stop_short": stop_short,
        "exit_long": exit_long.fillna(False).astype(bool), "exit_short": exit_short.fillna(False).astype(bool),
    }, index=df.index)
    if limit_long is not None:
        sig["limit_long"] = limit_long
        sig["limit_short"] = limit_short
    sig.attrs.update(attrs)
    return sig


# ---------------------------------------------------------------- S1: Trend geri çekilme
S1_VARSAYILAN = dict(yon_mod="ema10", hizli=20, yavas=50, rsi_n=14, rsi_esik=45, temas_atr=0.3,
                     bakis=3, stop_atr=1.0, hedef_R=None, iz_atr=3.0, max_gun=20, basabas_R=None,
                     short=False, momentum_n=0, momentum_min=0.0, hacim_azalan=False, kismi_R=None)


def s1_geri_cekilme(df, p=None):
    p = {**S1_VARSAYILAN, **(p or {})}
    c, h, l = df["Close"], df["High"], df["Low"]
    a = g.atr(df, 14)
    eh, ey = g.ema(c, p["hizli"]), g.ema(c, p["yavas"])
    r = g.rsi(c, p["rsi_n"])
    yon = haftalik_yon(df, p["yon_mod"])
    b = p["bakis"]
    # Long: yükselen trendde hızlı EMA'ya temas + RSI soğuma + dönüş mumu (kapanış önceki günün tepesi üstünde)
    trend_up = (c > ey) & (eh > ey) & (ey > ey.shift(5))
    temas_up = (l <= eh + p["temas_atr"] * a).rolling(b).max().astype(bool)
    soguma_up = r.rolling(b).min() < p["rsi_esik"]
    tetik_up = (c > h.shift()) & (c > eh)
    long = (yon > 0) & trend_up & temas_up & soguma_up & tetik_up
    if p["momentum_n"]:  # Ladha: yalnızca güçlü (momentumlu) varlıklarda geri çekilme al
        roc = c / c.shift(p["momentum_n"]) - 1
        long &= roc > p["momentum_min"]
    if p["hacim_azalan"]:  # geri çekilme düşük hacimle gelmeli
        v = df["Volume"]
        long &= (v.rolling(b).mean() < g.sma(v, 20)) | (g.sma(v, 20) <= 0)
    swing_low = l.rolling(b + 1).min()
    stop_long = np.minimum(swing_low, c - a) - p["stop_atr"] * a * 0.5
    exit_long = c < ey  # trendin bozulması (Ladha: yavaş EMA altında kapanış)

    trend_dn = (c < ey) & (eh < ey) & (ey < ey.shift(5))
    temas_dn = (h >= eh - p["temas_atr"] * a).rolling(b).max().astype(bool)
    soguma_dn = r.rolling(b).max() > 100 - p["rsi_esik"]
    tetik_dn = (c < l.shift()) & (c < eh)
    short = (yon < 0) & trend_dn & temas_dn & soguma_dn & tetik_dn if p["short"] else pd.Series(False, index=df.index)
    swing_high = h.rolling(b + 1).max()
    stop_short = np.maximum(swing_high, c + a) + p["stop_atr"] * a * 0.5
    exit_short = c > ey
    return _cerceve(df, a, long, short, stop_long, stop_short, exit_long, exit_short,
                    hedef_R=p["hedef_R"], iz_atr=p["iz_atr"], max_gun=p["max_gun"], basabas_R=p["basabas_R"],
                    kismi_R=p.get("kismi_R"), kismi_oran=p.get("kismi_oran", 0.5), rejim_mod=p.get("rejim"),
                    endeks=p.get("_endeks"))


# ---------------------------------------------------------------- S2: Sıkışma kırılımı
S2_VARSAYILAN = dict(yon_mod="ema10", kanal=20, hacim_kat=1.3, sikisma=0.85, sikisma_bakis=5,
                     kapanis_konum=0.6, stop_atr=2.0, hedef_R=None, iz_atr=3.0, max_gun=30,
                     basabas_R=None, cikis_kanal=10, short=False)


def s2_kirilim(df, p=None):
    p = {**S2_VARSAYILAN, **(p or {})}
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    a = g.atr(df, 14)
    yon = haftalik_yon(df, p["yon_mod"])
    n = p["kanal"]
    ust = h.rolling(n).max().shift()
    alt = l.rolling(n).min().shift()
    # Daralma: kısa ATR / uzun ATR düşük (Farley NR7, Bollinger sıkışması mantığı)
    oran = g.atr(df, 5) / g.atr(df, 50)
    sikisti = (oran < p["sikisma"]).rolling(p["sikisma_bakis"]).max().astype(bool)
    vs = g.sma(v, 20)
    hacim_ok = (v > p["hacim_kat"] * vs) | (vs <= 0) | vs.isna()
    rng = (h - l).replace(0, np.nan)
    konum = (c - l) / rng
    long = (yon > 0) & (c > ust) & sikisti & hacim_ok & (konum >= p["kapanis_konum"])
    short = ((yon < 0) & (c < alt) & sikisti & hacim_ok & (konum <= 1 - p["kapanis_konum"])) if p["short"] \
        else pd.Series(False, index=df.index)
    stop_long = c - p["stop_atr"] * a
    stop_short = c + p["stop_atr"] * a
    m = p["cikis_kanal"]
    exit_long = c < l.rolling(m).min().shift() if m else pd.Series(False, index=df.index)
    exit_short = c > h.rolling(m).max().shift() if m else pd.Series(False, index=df.index)
    return _cerceve(df, a, long, short, stop_long, stop_short, exit_long, exit_short,
                    hedef_R=p["hedef_R"], iz_atr=p["iz_atr"], max_gun=p["max_gun"], basabas_R=p["basabas_R"],
                    kismi_R=p.get("kismi_R"), kismi_oran=p.get("kismi_oran", 0.5), rejim_mod=p.get("rejim"),
                    endeks=p.get("_endeks"))


# ---------------------------------------------------------------- S3: Aşırı satım dönüşü (trend yönünde)
S3_VARSAYILAN = dict(yon_mod="ema10", trend_sma=200, osc="rsi2", esik=10, cikis_sma=5, cikis_rsi=70,
                     stop_atr=2.5, hedef_R=None, iz_atr=None, max_gun=10, basabas_R=None, short=False,
                     limit_atr=None, ardisik_dusus=0, cikis_mod="sma")


def s3_asiri_satim(df, p=None):
    p = {**S3_VARSAYILAN, **(p or {})}
    c, h, l = df["Close"], df["High"], df["Low"]
    a = g.atr(df, 14)
    yon = haftalik_yon(df, p["yon_mod"])
    ts = g.sma(c, p["trend_sma"])
    r2 = g.rsi(c, 2)
    if p["osc"] == "rsi2":
        asiri_al_sinyal = r2 < p["esik"]
        asiri_sat_sinyal = r2 > 100 - p["esik"]
    elif p["osc"] == "stok":  # Munroe: stokastik aşırı satımdan yukarı kesişim
        K, D = g.stokastik(df, 14, 3, 3)
        asiri_al_sinyal = (K.shift() < p["esik"]) & (K > D) & (K.shift() <= D.shift())
        asiri_sat_sinyal = (K.shift() > 100 - p["esik"]) & (K < D) & (K.shift() >= D.shift())
    elif p["osc"] == "bb":  # Bollinger alt bant dışı kapanış
        m, u, lo = g.bollinger(c, 20, 2.0)
        asiri_al_sinyal = c < lo
        asiri_sat_sinyal = c > u
    else:
        raise ValueError(p["osc"])
    k = p["ardisik_dusus"]
    if k:  # Connors tarzı: art arda k düşük kapanış / yüksek kapanış
        asiri_al_sinyal &= (c < c.shift()).rolling(k).sum() == k
        asiri_sat_sinyal &= (c > c.shift()).rolling(k).sum() == k
    long = (yon > 0) & (c > ts) & asiri_al_sinyal
    short = ((yon < 0) & (c < ts) & asiri_sat_sinyal) if p["short"] else pd.Series(False, index=df.index)
    lim_l = lim_s = None
    if p["limit_atr"]:
        lim_l, lim_s = c - p["limit_atr"] * a, c + p["limit_atr"] * a
    ref_l = lim_l if lim_l is not None else c
    ref_s = lim_s if lim_s is not None else c
    stop_long = ref_l - p["stop_atr"] * a
    stop_short = ref_s + p["stop_atr"] * a
    cs = g.sma(c, p["cikis_sma"])
    if p["cikis_mod"] == "sma":
        exit_long = (c > cs) | (r2 > p["cikis_rsi"])
        exit_short = (c < cs) | (r2 < 100 - p["cikis_rsi"])
    else:  # "yuksek": kapanış önceki günün tepesini aşınca çık (hızlı kâr al)
        exit_long = (c > h.shift()) | (r2 > p["cikis_rsi"])
        exit_short = (c < l.shift()) | (r2 < 100 - p["cikis_rsi"])
    return _cerceve(df, a, long, short, stop_long, stop_short, exit_long, exit_short, lim_l, lim_s,
                    hedef_R=p["hedef_R"], iz_atr=p["iz_atr"], max_gun=p["max_gun"], basabas_R=p["basabas_R"],
                    kismi_R=p.get("kismi_R"), kismi_oran=p.get("kismi_oran", 0.5), rejim_mod=p.get("rejim"),
                    endeks=p.get("_endeks"))


STRATEJILER = {"S1_geri_cekilme": s1_geri_cekilme, "S2_kirilim": s2_kirilim, "S3_asiri_satim": s3_asiri_satim}
