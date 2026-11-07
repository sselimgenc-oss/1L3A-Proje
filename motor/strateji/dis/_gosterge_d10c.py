"""D10-C (kitap kartlarından yeni aileler) için göstergeler ve ortak iskelet. Hepsi nedensel: t. satır yalnız t. mum
kapanışına kadar olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  D10Taban        ortak sinyal iskeleti (yön süzgeci, ATR/yapısal stop, R hedefi, zaman çıkışı, gün sonu).
  seans_sira, seans_ozet, seansa_esle   seans (UTC gün, seans_saat kaydırmalı) yardımcıları.
  vwma, aroon, pmax, qqe, h_say, olay_ilk_gunde
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.temel import Strateji

ORTAK = {
    "yonler": "ls",          # "long" | "short" | "ls"  (kartlar çoğunlukla yalnız long; short = ayna, VARSAYIM)
    "stop_atr_k": 2.0,       # yapısal stop yoksa / eksikse: kapanış -/+ k x ATR
    "atr_periyot": 14,
    "min_risk_atr": 0.3,     # yapısal stop kapanışa 0.3 ATR'den yakınsa 0.3 ATR'ye uzatılır (aşırı küçük risk)
    "hedef_r": 2.0,          # > 0: hedef = giriş +/- hedef_r x risk (sinyalde seviye hedefi yoksa); 0: kapalı
    "zaman_cikisi": 0,       # > 0: N mum sonra çık
    "gun_sonu": 1,           # 1: seansın son mumunda giriş yok ve açık pozisyon kapanır
    "seans_saat": 0.0,       # seans başlangıcı (UTC saat; ABD hisse 13.5/14.5, BIST 7.0, 7/24 için 0)
}


def _bool(s, idx):
    if s is None:
        return pd.Series(False, index=idx)
    return s.reindex(idx).fillna(False).astype(bool)


class D10Taban(Strateji):
    """Alt sınıf `kosullar(m)` yazar. Dönen sözlük (hepsi isteğe bağlı): long, short, cikis_long, cikis_short (bool Series);
    stop_l, stop_s, hedef_l, hedef_s (fiyat Series). Sinyal mum KAPANIŞINDA; motor sonraki açılışta girer."""

    def kosullar(self, m: pd.DataFrame) -> dict:
        raise NotImplementedError

    def cikis_var_mi(self) -> bool:
        return True   # stop + hedef (R) / kendi çıkış sinyali / gün sonu

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = m.index
        kap = m["kapanis"]
        k = self.kosullar(m)
        a = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_periyot"]))
        sl_atr, ss_atr = kap - p["stop_atr_k"] * a, kap + p["stop_atr_k"] * a
        min_r = p["min_risk_atr"] * a
        stop_l = k.get("stop_l")
        stop_s = k.get("stop_s")
        stop_l = sl_atr if stop_l is None else np.minimum(stop_l.reindex(idx).fillna(sl_atr), kap - min_r)
        stop_s = ss_atr if stop_s is None else np.maximum(stop_s.reindex(idx).fillna(ss_atr), kap + min_r)
        yon = p["yonler"]
        long_ok = _bool(k.get("long"), idx) if yon in ("long", "ls") else _bool(None, idx)
        short_ok = _bool(k.get("short"), idx) if yon in ("short", "ls") else _bool(None, idx)
        hl, hs = k.get("hedef_l"), k.get("hedef_s")
        if hl is not None:
            hl = hl.reindex(idx).where(hl.reindex(idx) > kap)
        if hs is not None:
            hs = hs.reindex(idx).where(hs.reindex(idx) < kap)
        out = cerceve(m, long_ok, short_ok, stop_l, stop_s, hl, hs, None, bool(p["gun_sonu"]), float(p["seans_saat"]))
        if p["hedef_r"] and p["hedef_r"] > 0:
            bos = (out["yon"] != 0) & out["hedef"].isna()
            risk = (kap - out["stop"]).abs()
            out.loc[bos, "hedef"] = (kap + out["yon"] * p["hedef_r"] * risk)[bos]
        out["cikis_long"] = _bool(k.get("cikis_long"), idx)
        out["cikis_short"] = _bool(k.get("cikis_short"), idx)
        if p["zaman_cikisi"] > 0:
            out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(p["zaman_cikisi"]), np.nan), index=idx)
        return out


# ------------------------------------------------------------------ seans yardımcıları
def seans_sira(sid: np.ndarray, index) -> pd.Series:
    """Seans içindeki mum sırası (0 = seansın ilk mumu). Nedensel."""
    return pd.Series(np.zeros(len(sid), dtype=np.int64), index=index).groupby(sid).cumcount()


def seans_ozet(m: pd.DataFrame, sid: np.ndarray) -> pd.DataFrame:
    """Seans başına o, h, l, c, hacim (seans bitmeden eksik olabilir; KULLANIRKEN shift(>=1) uygula)."""
    gp = m.groupby(sid)
    return pd.DataFrame({"o": gp["acilis"].first(), "h": gp["yuksek"].max(), "l": gp["dusuk"].min(),
                         "c": gp["kapanis"].last(), "v": gp["hacim"].sum()})


def seansa_esle(ozet: pd.DataFrame, sid: np.ndarray, index, geri: int = 1) -> pd.DataFrame:
    """Her mum için `geri` seans ÖNCEKİ tamamlanmış seansın özeti (geri >= 1 zorunlu: nedensel)."""
    if geri < 1:
        raise ValueError("geri >= 1 olmalı")
    s = ozet.shift(int(geri))
    return pd.DataFrame({c: s[c].reindex(sid).to_numpy() for c in s.columns}, index=index)


def ilk_olay(kosul: pd.Series, sid: np.ndarray) -> pd.Series:
    """Seans başına yalnız İLK True mum (kümülatif sayaç; nedensel)."""
    k = kosul.fillna(False).astype(bool)
    return k & (k.astype(int).groupby(sid).cumsum() == 1)


# ------------------------------------------------------------------ göstergeler
def vwma(kapanis: pd.Series, hacim: pd.Series, n: int) -> pd.Series:
    pv = (kapanis * hacim).rolling(n, min_periods=n).sum()
    v = hacim.rolling(n, min_periods=n).sum().where(lambda x: x > 0)
    return pv / v


def aroon(yuksek: pd.Series, dusuk: pd.Series, n: int = 25) -> pd.DataFrame:
    """Aroon Up/Down (0..100): 100 x (n - son zirveden beri geçen mum) / n; pencere n+1 mum, eşitlikte en yeni."""
    def _arg(x, tepe):
        w = np.lib.stride_tricks.sliding_window_view(x, n + 1)
        r = w[:, ::-1]
        idx = r.argmax(axis=1) if tepe else r.argmin(axis=1)    # 0 = en yeni
        return 100.0 * (n - idx) / n
    out_u = np.full(len(yuksek), np.nan)
    out_d = np.full(len(yuksek), np.nan)
    if len(yuksek) > n:
        out_u[n:] = _arg(yuksek.to_numpy(float), True)
        out_d[n:] = _arg(dusuk.to_numpy(float), False)
    return pd.DataFrame({"up": out_u, "down": out_d}, index=yuksek.index)


def pmax(yuksek, dusuk, kapanis, ma_n: int = 10, atr_n: int = 10, carpan: float = 2.7) -> pd.DataFrame:
    """PMax (Profit Maximizer): MA = EMA((H+L)/2, ma_n); bant = MA -/+ carpan x ATR(atr_n); yapışkan (ratchet) alt/üst bant.
    yon: +1 yeşil (alt bant çizgisi), -1 kırmızı (üst bant çizgisi). cizgi = aktif PMax çizgisi. Nedensel döngü."""
    ma = g.ema((yuksek + dusuk) / 2.0, ma_n).to_numpy(float)
    at = g.atr(yuksek, dusuk, kapanis, atr_n).to_numpy(float)
    n = len(ma)
    yon = np.zeros(n)
    cizgi = np.full(n, np.nan)
    lb = np.full(n, np.nan)
    sb = np.full(n, np.nan)
    d = 1
    for i in range(n):
        if np.isnan(ma[i]) or np.isnan(at[i]):
            continue
        yl, ys = ma[i] - carpan * at[i], ma[i] + carpan * at[i]
        if i > 0 and not np.isnan(lb[i - 1]):
            if ma[i] > lb[i - 1]:
                yl = max(yl, lb[i - 1])
            if ma[i] < sb[i - 1]:
                ys = min(ys, sb[i - 1])
            if d == -1 and ma[i] > sb[i - 1]:
                d = 1
            elif d == 1 and ma[i] < lb[i - 1]:
                d = -1
        lb[i], sb[i] = yl, ys
        yon[i] = d
        cizgi[i] = yl if d == 1 else ys
    return pd.DataFrame({"cizgi": cizgi, "yon": yon, "ma": ma}, index=kapanis.index)


def qqe(kapanis: pd.Series, rsi_n: int = 14, sf: int = 5, carpan: float = 4.236) -> pd.DataFrame:
    """QQE (Kıvanç Özbilgiç / klasik): RsiMa = EMA(RSI, sf); DAR = carpan x EMA(EMA(|dRsiMa|, 2*rsi_n-1), 2*rsi_n-1);
    yapışkan alt/üst bant; yon +1: RsiMa üst bandı yukarı kesti (al), -1: alt bandı aşağı kesti (sat). tl = hızlı çizgi."""
    rs = g.ema(g.rsi(kapanis, rsi_n), sf)
    w = 2 * rsi_n - 1
    dar = carpan * g.ema(g.ema(rs.diff().abs(), w), w)
    r, dd = rs.to_numpy(float), dar.to_numpy(float)
    n = len(r)
    lb = np.full(n, np.nan)
    sb = np.full(n, np.nan)
    yon = np.zeros(n)
    d = 0
    for i in range(n):
        if np.isnan(r[i]) or np.isnan(dd[i]):
            continue
        yl, ys = r[i] - dd[i], r[i] + dd[i]
        if i > 0 and not np.isnan(lb[i - 1]):
            if r[i - 1] > lb[i - 1] and r[i] > lb[i - 1]:
                yl = max(yl, lb[i - 1])
            if r[i - 1] < sb[i - 1] and r[i] < sb[i - 1]:
                ys = min(ys, sb[i - 1])
            if r[i] > sb[i - 1]:
                d = 1
            elif r[i] < lb[i - 1]:
                d = -1
        lb[i], sb[i] = yl, ys
        yon[i] = d
    yon_s = pd.Series(yon, index=kapanis.index)
    tl = pd.Series(np.where(yon == 1, lb, sb), index=kapanis.index)
    return pd.DataFrame({"rsima": rs, "tl": tl, "yon": yon_s})


def h_say(yuksek: np.ndarray, dusuk: np.ndarray, trend: np.ndarray, sayi: int):
    """Brooks H1/H2 (yükseliş): trend içinde, bir önceki mumun yükseğini aşan mum 'deneme'dir. Geri çekilme = en az bir mum
    önceki yüksekten düşük/eşit yüksekle kapanmış. Geri çekilme başladıktan sonra `sayi`'inci deneme (yeni yüksek yapmadan)
    sinyal mumudur. Geri çekilmeden önceki en yüksek aşılırsa sayaç sıfırlanır. Dönüş: (sinyal bool, stop = geri çekilmenin
    en düşüğü). Trend bozulursa sıfırlanır. Nedensel."""
    n = len(yuksek)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    sayac = 0
    geri = False
    tepe = np.nan
    pb_dip = np.nan
    for i in range(n):
        if not trend[i]:
            sayac, geri, tepe, pb_dip = 0, False, np.nan, np.nan
            continue
        if i == 0:
            continue
        if np.isnan(tepe):
            tepe = yuksek[i]
        if yuksek[i] > yuksek[i - 1]:
            if geri:
                sayac += 1
                if sayac == sayi and yuksek[i] <= tepe:
                    sig[i] = True
                    stop[i] = min(pb_dip, dusuk[i])
            if yuksek[i] > tepe:
                tepe, sayac, geri, pb_dip = yuksek[i], 0, False, np.nan
        else:
            if not geri:
                geri, sayac, pb_dip = True, 0, dusuk[i]
        if geri:
            pb_dip = dusuk[i] if np.isnan(pb_dip) else min(pb_dip, dusuk[i])
    return sig, stop
