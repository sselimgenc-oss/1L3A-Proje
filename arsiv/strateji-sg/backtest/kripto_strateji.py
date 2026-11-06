"""Kripto çoklu zaman dilimi trend stratejisi: 1G + 4S yön, 1S giriş.

PDF ortak paydası:
  * Yön (üst zaman dilimleri): 20 Str. #5/#6/#11 (üst zaman diliminde EMA dizilimi), 51 Str. 2.6 Çift RSI
    (üst zaman dilimi RSI > 50), 151 Str. trend takibi / zaman serisi momentumu.
  * Giriş (1S):
      'gc'  geri çekilme — trend yönünde 1S RSI'ın düşüp toparlanması (51 Str. Çift RSI, 20 Str. #6,
            Galen Zayıf Geri Çekilme, 51 Str. 7.4/7.7)
      'kir' kırılım — 1S'de son n mumun tepesinin kırılması (51 Str. 3.6 Donchian, 1.4; 20 Str. #7; Galen sıkışıklık)
  * Çıkış: ATR izleyen stop (20 Str. #7 "kutu boyu kadar takip eden stop", 51 Str. 2.2 Supertrend) ve/veya
    4S trendin dönmesi (20 Str. #6 "dizilim bozulunca çık"); opsiyonel kısmi kâr al + başabaş (20 Str. #9, #18).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from . import gostergeler as g

KOK = Path(__file__).resolve().parent.parent / "data" / "kripto"
BAS, BIT = "2020-01-01", None


def _htf(df, kural):
    return df.resample(kural, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def yukle(maks_bosluk=24):
    """Tüm evren coinlerinin 1S verisini ortak eksende T x N dizilere çevirir."""
    evren = pd.read_pickle(KOK / "evren.pkl")
    sem = sorted({s for v in evren.values for s in v})
    veri = {}
    for s in sem:
        f = KOK / "1h" / f"{s}.pkl"
        if f.exists():
            veri[s] = pd.read_pickle(f)
    sem = sorted(veri)
    son = max(d.index[-1] for d in veri.values())
    z = pd.date_range(BAS, son, freq="1h")
    T, N = len(z), len(sem)
    A = {k: np.full((T, N), np.nan) for k in ("O", "H", "L", "C")}
    FUND = np.zeros((T, N))
    for j, s in enumerate(sem):
        d = veri[s].reindex(z)
        ilk, sonn = veri[s].index[0], veri[s].index[-1]
        canli = (z >= ilk) & (z <= sonn)
        c = d.close.ffill(limit=maks_bosluk)
        bos = d.close.isna() & c.notna()
        o = d.open.where(~bos, c); h = d.high.where(~bos, c); l = d.low.where(~bos, c)
        for k, x in (("O", o), ("H", h), ("L", l), ("C", c)):
            v = x.to_numpy().copy(); v[~canli] = np.nan; A[k][:, j] = v
        FUND[:, j] = d.funding.fillna(0).to_numpy()
    # evren üyeliği ve öncelik (ayın hacim sırası)
    UYE = np.zeros((T, N), bool)
    ONC = np.full((T, N), 999.0)
    ay = z.to_period("M").to_timestamp()
    idx = {s: j for j, s in enumerate(sem)}
    for a, liste in evren.items():
        m = ay == a
        for r, s in enumerate(liste):
            if s in idx:
                UYE[m, idx[s]] = True
                ONC[m, idx[s]] = r
    return dict(A, FUND=FUND, UYE=UYE, ONC=ONC, zaman=z, semboller=sem)


def _hizala(z, df_htf, diziler):
    return g.htf_hizala(z, df_htf, diziler)


def ozellikler(V, p):
    """Her coin için 1S/4S/1G göstergelerini hesaplar (yalnız kapanmış üst zaman dilimi mumları)."""
    z = V["zaman"]
    T, N = V["C"].shape
    F = {k: np.full((T, N), np.nan) for k in ("d_yon", "h4_yon", "h4_rsi", "rsi", "ema_h", "atr", "atr4",
                                             "dh", "sw_l", "sw_h", "dl", "ret30", "h4_brooks")}
    for j in range(N):
        c = V["C"][:, j]
        canli = ~np.isnan(c)
        if canli.sum() < 60 * int(round(86400 / (z[1] - z[0]).total_seconds())):   # en az 60 günlük veri
            continue
        i0, i1 = np.argmax(canli), len(c) - np.argmax(canli[::-1])
        df = pd.DataFrame({"open": V["O"][i0:i1, j], "high": V["H"][i0:i1, j], "low": V["L"][i0:i1, j],
                           "close": c[i0:i1]}, index=z[i0:i1]).ffill()
        o, h, l, cc = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
        # 1G
        d = _htf(df, "1D"); dc = d.close.to_numpy()
        de_f, de_s = g.ema(dc, p["d_f"]), g.ema(dc, p["d_s"])
        dy = np.where((de_f > de_s) & (dc > de_s), 1.0, np.where((de_f < de_s) & (dc < de_s), -1.0, 0.0))
        # 4S
        h4 = _htf(df, p.get("h4_kural", "4h")); hc = h4.close.to_numpy()   # eğilim zaman dilimi (varsayılan 4S)
        he_f, he_s = g.ema(hc, p["h4_f"]), g.ema(hc, p["h4_s"])
        hy = np.where((he_f > he_s) & (hc > he_f), 1.0, np.where((he_f < he_s) & (hc < he_f), -1.0, 0.0))
        hr = g.rsi(hc, 14)
        a4 = g.atr(h4.high.values, h4.low.values, hc, 14)
        r30 = np.full(len(dc), np.nan)
        r30[30:] = dc[30:] / dc[:-30] - 1
        hz = _hizala(df.index, d, {"dy": dy, "r30": r30})
        e20 = g.ema(hc, 20)   # Brooks: 20 EMA'nın karşı tarafında art arda iki kapanış
        alt2 = (hc < e20) & (np.roll(hc, 1) < np.roll(e20, 1)); ust2 = (hc > e20) & (np.roll(hc, 1) > np.roll(e20, 1))
        hb = np.where(alt2, -1.0, np.where(ust2, 1.0, 0.0))
        hz4 = _hizala(df.index, h4, {"hy": hy, "hr": hr, "a4": a4, "hb": hb})
        sl = slice(i0, i1)
        F["ret30"][sl, j] = hz["r30"]
        F["d_yon"][sl, j] = hz["dy"]; F["h4_yon"][sl, j] = hz4["hy"]; F["h4_rsi"][sl, j] = hz4["hr"]
        F["h4_brooks"][sl, j] = hz4["hb"]
        F["atr4"][sl, j] = hz4["a4"]
        F["rsi"][sl, j] = g.rsi(cc, p.get("rsi_n", 14))
        F["ema_h"][sl, j] = g.ema(cc, p.get("ema_h", 20))
        F["atr"][sl, j] = g.atr(h, l, cc, 14)
        dh, dl = g.donchian(h, l, p.get("kir_n", 48))
        dh1, dl1 = np.roll(dh, 1), np.roll(dl, 1); dh1[0] = dl1[0] = np.nan      # dizi başına sarma (son değer) olmasın
        F["dh"][sl, j] = dh1; F["dl"][sl, j] = dl1
        F["sw_l"][sl, j] = pd.Series(l).rolling(p.get("sw_n", 12)).min().to_numpy()
        F["sw_h"][sl, j] = pd.Series(h).rolling(p.get("sw_n", 12)).max().to_numpy()
    return F


def sinyaller(V, F, p):
    C, O = V["C"], V["O"]
    yon_up = F["d_yon"] > 0
    yon_dn = F["d_yon"] < 0
    if p.get("h4_filtre", True):
        yon_up &= F["h4_yon"] > 0
        yon_dn &= F["h4_yon"] < 0
    if p.get("btc_filtre"):      # piyasa rejimi: BTC günlük trendi yönünde işlem
        jb = V["semboller"].index("BTCUSDT")
        b = F["d_yon"][:, jb:jb + 1]
        yon_up &= b > 0
        yon_dn &= b < 0
    if p.get("rs_filtre"):       # göreli güç: 30 günlük getiri BTC'den yüksek (long) / düşük (short)
        jb = V["semboller"].index("BTCUSDT")
        rs = F["ret30"] - F["ret30"][:, jb:jb + 1]
        btc = np.zeros(F["ret30"].shape[1], bool); btc[jb] = True
        yon_up &= (rs > 0) | btc
        yon_dn &= (rs < 0) | btc
    if p.get("evren_n"):         # yalnızca o ayın hacim sıralamasında ilk n
        yon_up &= V["ONC"] < p["evren_n"]
        yon_dn &= V["ONC"] < p["evren_n"]
    if p.get("h4_rsi_esik"):
        yon_up &= F["h4_rsi"] > p["h4_rsi_esik"]
        yon_dn &= F["h4_rsi"] < 100 - p["h4_rsi_esik"]
    r = F["rsi"]
    r1 = np.roll(r, 1, axis=0)
    if p["giris"] == "gc":
        w = p.get("gc_pencere", 12)
        dip = pd.DataFrame(r < p["rsi_dip"]).rolling(w, min_periods=1).max().to_numpy() > 0
        tep = pd.DataFrame(r > 100 - p["rsi_dip"]).rolling(w, min_periods=1).max().to_numpy() > 0
        uzun = yon_up & dip & (r > p["rsi_don"]) & (r1 <= p["rsi_don"])
        kisa = yon_dn & tep & (r < 100 - p["rsi_don"]) & (r1 >= 100 - p["rsi_don"])
    elif p["giris"] == "dflip":   # kıyas: saf günlük trend dönüşü (1S zamanlama yok)
        d1 = np.roll(F["d_yon"], 1, axis=0)
        uzun = yon_up & (d1 <= 0)
        kisa = yon_dn & (d1 >= 0)
    else:
        c1 = np.roll(C, 1, axis=0)
        uzun = yon_up & (C > F["dh"]) & (c1 <= np.roll(F["dh"], 1, axis=0))
        kisa = yon_dn & (C < F["dl"]) & (c1 >= np.roll(F["dl"], 1, axis=0))
    yon = p.get("yon", 0)
    if yon == 1:
        kisa[:] = False
    elif yon == -1:
        uzun[:] = False
    sig = np.where(uzun, 1.0, np.where(kisa, -1.0, 0.0))
    a = F["atr"]
    stop = np.where(sig > 0, C - F["sw_l"], F["sw_h"] - C) + p.get("tampon_atr", 0.5) * a
    stop = np.clip(stop, p.get("stop_min_atr", 1.5) * a, p.get("stop_max_atr", 5.0) * a)
    if p.get("stop_atr4"):        # üst zaman dilimi ATR'si ile geniş stop (günlük sistemler)
        stop = p["stop_atr4"] * F["atr4"]
    stop = np.where(sig != 0, stop, np.nan)
    # çıkış sinyali: seçilen zaman diliminde trend dönerse
    cm = p.get("cikis", "h4")
    if cm == "h4":
        cik = np.where(F["h4_yon"] < 0, -1.0, np.where(F["h4_yon"] > 0, 1.0, 0.0))
    elif cm == "h4_notr":   # 4S trend artık lehte değilse (nötr dahil) çık
        cik = np.where(F["h4_yon"] <= 0, -1.0, 0.0) + np.where(F["h4_yon"] >= 0, 1.0, 0.0)
        cik = np.where(F["h4_yon"] == 0, 2.0, cik)
    elif cm == "d":
        cik = np.where(F["d_yon"] < 0, -1.0, np.where(F["d_yon"] > 0, 1.0, 0.0))
    else:
        cik = np.zeros_like(sig)
    iz = F["atr4"] if p.get("iz_tf", "4h") == "4h" else F["atr"]
    iz = np.nan_to_num(iz, nan=0.0)
    onc = V["ONC"]
    return sig, stop, iz, cik, onc
