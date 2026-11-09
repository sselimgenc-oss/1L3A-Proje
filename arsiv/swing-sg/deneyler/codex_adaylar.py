"""Codex'in bulduğu GitHub stratejilerinden elemeyi geçen 4 adayın bizim çerçevede testi.

Kurallar: günlük mum, sinyal kapanışta, giriş ertesi açılış, sınıf maliyetleri, IS 2015-22 / OOS 2023+.
Her aday iki biçimde: 'ham' (repodaki kural) ve 'bizim' (haftalık yön + sınıf rejim filtresi eklenmiş).
Son olarak her aday mevcut S1+S2+S3 sistemine eklenip birleşik portföy karşılaştırılır.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing import gostergeler as g  # noqa: E402
from swing.ayarlar import S1, S2, S3, SINIFLAR  # noqa: E402
from swing.calistir import OOS_BASLANGIC, islemler, veriler  # noqa: E402
from swing.motor import calistir, istatistik, portfoy  # noqa: E402
from swing.stratejiler import _cerceve, haftalik_yon  # noqa: E402
from swing.veri import ENDEKS_VERI, MALIYET  # noqa: E402

YOK = None


def atr_sma(df, n=14):
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - df["Close"].shift()).abs(),
                    (df["Low"] - df["Close"].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _bos(df):
    return pd.Series(False, index=df.index)


def _paket(df, a, long, stop, exit_long, p, **attrs):
    if p.get("bizim"):
        long = long & (haftalik_yon(df, p.get("yon_mod", "ha")) > 0)
    nan = pd.Series(np.nan, index=df.index)
    return _cerceve(df, a, long, _bos(df), stop, nan, exit_long, _bos(df),
                    rejim_mod=p.get("rejim") if p.get("bizim") else None, endeks=p.get("_endeks"), **attrs)


# 1) Volatilite rejimli momentum (erhungn/volatility-regime-momentum)
def c1_vol_momentum(df, p):
    c = df["Close"]
    a = atr_sma(df, 14)
    mom = (c - c.shift(20)) / a
    long = (mom > 0.5) & (c > g.sma(c, 200)) & (a > 0.95 * a.shift(5))
    stop = c - 5 * a  # felaket stopu 5 ATR; hedef 4 ATR = 0,8R
    return _paket(df, a, long, stop, _bos(df), p, hedef_R=0.8, max_gun=10)


# 2) KA-MATS TrendPullback çekirdeği (kunal14901/KA-MATS); kesitsel sıralama sınıf içinde
def c2_trend_pullback(df, p):
    c, v = df["Close"], df["Volume"]
    a = g.atr(df, 14)
    r = g.rsi(c, 14)
    e20, e50 = g.ema(c, 20), g.ema(c, 50)
    vs = g.sma(v, 20)
    hac = (v / vs < 2.0) | (vs <= 0) | vs.isna()
    long = (e20 > e50) & r.between(40, 54) & (c > 0.96 * e50) & hac & (g.adx(df, 14)[0] >= 15)
    sira = p.get("_sira")
    if sira is not None:
        long &= sira.reindex(df.index).fillna(0) >= 0.55
    ek = p.get("_kapi")  # kripto: BTC > EMA200
    if ek is not None:
        long &= ek.reindex(df.index, method="ffill").fillna(False).astype(bool)
    stop = c - 2.5 * a
    # 11 ATR hedef = 4,4R; +2 ATR (0,8R) sonrası 1 ATR iz stop -> motorda basabas + iz yaklaşımı
    return _paket(df, a, long, stop, _bos(df), p, hedef_R=4.4, iz_atr=p.get("iz", 1.5), max_gun=20)


# 3) Sıkışma kırılımı, yalnız alım (jicheolha/crypto-trading-bot fikri, ayarsız varsayılanlar)
def c3_sikisma(df, p):
    c, v = df["Close"], df["Volume"]
    a = g.atr(df, 14)
    orta = g.sma(c, 20)
    sd = c.rolling(20).std()
    bu, ba = orta + 2 * sd, orta - 2 * sd
    ke = g.ema(c, 20)
    sik = (bu < ke + 1.5 * a) & (ba > ke - 1.5 * a)
    sure = sik.astype(int).groupby((~sik).cumsum()).cumsum()
    vs = g.sma(v, 20)
    hac = (v >= 1.2 * vs) | (vs <= 0) | vs.isna()
    long = sik.shift(1, fill_value=False) & (sure.shift(1) >= 3) & ~sik & hac & (c > bu)
    stop = c - 3.5 * a
    return _paket(df, a, long, stop, _bos(df), p, hedef_R=4 / 3.5, max_gun=7)


def super_smoother(x, n=7):
    x = x.values
    a1 = np.exp(-1.414 * np.pi / n)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / n)
    c2, c3 = b1, -a1 * a1
    c1 = 1 - c2 - c3
    y = np.full(len(x), np.nan)
    for i in range(len(x)):
        if np.isnan(x[i]) or i < 2 or np.isnan(x[i - 1]):
            y[i] = x[i]
            continue
        p1 = y[i - 1] if not np.isnan(y[i - 1]) else x[i - 1]
        p2 = y[i - 2] if not np.isnan(y[i - 2]) else x[i - 2] if not np.isnan(x[i - 2]) else p1
        y[i] = c1 * (x[i] + x[i - 1]) / 2 + c2 * p1 + c3 * p2
    return y


# 4) Ichimoku bileşik trend (lutfi-zain/quant-lttd-ichimoku, sadeleştirilmiş; entropi kapısı yok)
def c4_ichimoku(df, p):
    c, h, l = df["Close"], df["High"], df["Low"]
    mid = lambda n: (h.rolling(n).max() + l.rolling(n).min()) / 2  # noqa: E731
    ten, kij, sb = mid(20), mid(60), mid(120)
    sa = (ten + kij) / 2
    bulut_ust = np.maximum(sa.shift(60), sb.shift(60))
    bulut_alt = np.minimum(sa.shift(60), sb.shift(60))
    a60 = g.atr(df, 60)
    mesafe = np.where(c > bulut_ust, c - bulut_ust, np.where(c < bulut_alt, c - bulut_alt, 0.0))
    imo = (np.tanh((ten - kij) / a60) + np.tanh(pd.Series(mesafe, index=df.index) / a60)
           + np.tanh((sa - sb) / a60) + np.tanh((c - c.shift(60)) / a60)) / 4
    imo = pd.Series(super_smoother(imo, 7), index=df.index)
    er = (c - c.shift(14)).abs() / c.diff().abs().rolling(14).sum()
    kos = (imo > 0.4 * imo.rolling(30).std()) & (er > 0.25) & (c >= bulut_alt)
    long = kos & kos.shift(1, fill_value=False)
    a = g.atr(df, 14)
    stop = c - 4 * a  # repoda stop yok; motor risk ölçüsü için geniş felaket stopu
    exit_long = imo < 0
    return _paket(df, a, long, stop, exit_long, p, max_gun=250)


ADAYLAR = {"C1_vol_momentum": c1_vol_momentum, "C2_trend_pullback": c2_trend_pullback,
           "C3_sikisma": c3_sikisma, "C4_ichimoku": c4_ichimoku}
SINIF_TUM = ["kripto", "mag7", "bist", "emtia"]


def sira_hazirla():
    """Sınıf içi 20 günlük getiri yüzdelik sırası (C2 için; t günü kapanışıyla bilinir)."""
    out = {}
    for s in SINIF_TUM:
        px = pd.DataFrame({ad: df["Close"] for ad, (df, sn) in veriler().items() if sn == s})
        rk = (px / px.shift(20) - 1).rank(axis=1, pct=True)
        for ad in px:
            out[ad] = rk[ad]
    btc = ENDEKS_VERI.get("kripto")
    kapi = (btc["Close"] > g.ema(btc["Close"], 200)) if btc is not None else None
    return out, kapi


def aday_islemleri(ad_, f, p, siniflar=SINIF_TUM):
    sira, kapi = sira_hazirla() if ad_ == "C2_trend_pullback" else ({}, None)
    out = []
    for ad, (df, sinif) in veriler().items():
        if sinif not in siniflar:
            continue
        q = {**p, "_endeks": ENDEKS_VERI.get(sinif)}
        if ad_ == "C2_trend_pullback":
            q["_sira"] = sira.get(ad)
            q["_kapi"] = kapi if sinif == "kripto" else None
        out += calistir(ad, sinif, df, f(df, q), MALIYET[sinif], ad_)
    return out


def satir(tr):
    def f(s):
        return "-" if not s.get("islem") else \
            f"n={s['islem']:4d} WR={s['kazanma_orani']:.0%} PF={s['kar_faktoru']:.2f} R={s['ort_R']:+.2f}"
    i = istatistik([t for t in tr if t.giris_tarih < OOS_BASLANGIC])
    o = istatistik([t for t in tr if t.giris_tarih >= OOS_BASLANGIC])
    y22 = istatistik([t for t in tr if t.giris_tarih.year == 2022])
    pf = portfoy(tr) or {}
    return (f"IS[{f(i)}] OOS[{f(o)}] 2022[{f(y22)}] | CAGR={pf.get('yillik_getiri', 0):.1%} "
            f"DD={pf.get('max_dusus', 0):.1%} Sh={pf.get('sharpe_aylik', 0):.2f}")


def sinif_ozet(tr):
    rows = []
    for s in SINIF_TUM:
        o = istatistik([t for t in tr if t.sinif == s and t.giris_tarih >= OOS_BASLANGIC])
        i = istatistik([t for t in tr if t.sinif == s and t.giris_tarih < OOS_BASLANGIC])
        if i.get("islem") or o.get("islem"):
            rows.append(f"{s}: IS R={i.get('ort_R', 0):+.2f} (n={i.get('islem', 0)}) "
                        f"OOS R={o.get('ort_R', 0):+.2f} (n={o.get('islem', 0)})")
    return " · ".join(rows)


if __name__ == "__main__":
    mevcut = []
    for s, prm in (("S1_geri_cekilme", S1), ("S2_kirilim", S2), ("S3_asiri_satim", S3)):
        mevcut += islemler(s, prm, SINIFLAR[s])
    print("MEVCUT S1+S2+S3:", satir(mevcut), flush=True)
    kayit = {}
    for ad, f in ADAYLAR.items():
        for etk, p in (("ham", {}), ("bizim", {"bizim": True, "yon_mod": "ha", "rejim": "ema10"})):
            tr = aday_islemleri(ad, f, p)
            kayit[(ad, etk)] = tr
            print(f"{ad:18s} {etk:5s}", satir(tr), flush=True)
            print("    ", sinif_ozet(tr), flush=True)
    print("\n== Mevcut sisteme ekleme (birleşik portföy)")
    for (ad, etk), tr in kayit.items():
        print(f"+{ad:18s} {etk:5s}", satir(mevcut + tr), flush=True)
