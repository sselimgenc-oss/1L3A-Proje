"""D3 grubu (freqtrade / kural / awesome / jesuistm dış stratejileri) için ortak iskelet ve göstergeler.

Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  D3Taban          ortak sinyal iskeleti (yön süzgeci, yüzde/ATR stop, yüzde hedef, zaman çıkışı, UTC gün sonu).
  tema, mfi, hizli_stokastik, cmf, keltner_wband, donchian_pband, dalga_trend, td_sayim,
  genisleyen_minmax, sayac, ay_sonuna_kalan_gun, son_cuma_kalan_gun.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji

# Alt sınıflar bu anahtarları varsayilan_parametreler içine yayar ({**ORTAK, ...}).
ORTAK = {
    "yonler": "long",        # "long" | "short" | "ls"
    "stop_yuzde": 0.0,       # > 0: sabit yüzde stop; 0: ATR stop (stop_atr_k x ATR)
    "stop_atr_k": 3.0,
    "atr_periyot": 14,
    "hedef_yuzde": 0.0,      # > 0: sabit yüzde hedef (freqtrade minimal_roi karşılığı)
    "zaman_cikisi": 0,       # > 0: N mum sonra çık
}


class D3Taban(Strateji):
    """Alt sınıf `kosullar(m)` yazar: {"long","short","cikis_long","cikis_short"} (bool Series; eksik = False).
    Giriş sinyali mum KAPANIŞINDA; stop/hedef kapanışa göre kurulur (motor sonraki açılışta girer)."""
    _gun_sonu = False

    def kosullar(self, mumlar: pd.DataFrame) -> dict:
        raise NotImplementedError

    def cikis_var_mi(self) -> bool:
        return True   # her alt sınıf kendi cikis sinyali / hedef / zaman çıkışı / gün sonu üretir

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = self.kosullar(mumlar)
        kap = mumlar["kapanis"]
        idx = mumlar.index
        yon = p["yonler"]
        bos = pd.Series(False, index=idx)

        def al(ad):
            s = k.get(ad)
            return bos if s is None else s.reindex(idx).fillna(False).astype(bool)

        long_ok = al("long") if yon in ("long", "ls") else bos
        short_ok = al("short") if yon in ("short", "ls") else bos
        if p["stop_yuzde"] > 0:
            stop_l, stop_s = kap * (1 - p["stop_yuzde"]), kap * (1 + p["stop_yuzde"])
        else:
            a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_periyot"])) * p["stop_atr_k"]
            stop_l, stop_s = kap - a, kap + a
        hedef_l = hedef_s = None
        if p["hedef_yuzde"] > 0:
            hedef_l, hedef_s = kap * (1 + p["hedef_yuzde"]), kap * (1 - p["hedef_yuzde"])
        out = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, None, self._gun_sonu, 0.0)
        out["cikis_long"] = al("cikis_long")
        out["cikis_short"] = al("cikis_short")
        if p["zaman_cikisi"] > 0:
            out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(p["zaman_cikisi"]), np.nan), index=idx)
        return out


# ------------------------------------------------------------------ göstergeler
def tema(seri: pd.Series, n: int) -> pd.Series:
    e1 = seri.ewm(span=n, adjust=False, min_periods=n).mean()
    e2 = e1.ewm(span=n, adjust=False, min_periods=n).mean()
    e3 = e2.ewm(span=n, adjust=False, min_periods=n).mean()
    return 3 * e1 - 3 * e2 + e3


def mfi(yuksek, dusuk, kapanis, hacim, n: int = 14) -> pd.Series:
    tp = (yuksek + dusuk + kapanis) / 3.0
    akis = tp * hacim
    art = akis.where(tp > tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    eks = akis.where(tp < tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100.0 - 100.0 / (1.0 + art / eks)
    return out.where(eks != 0, 100.0).where(art.notna())


def hizli_stokastik(yuksek, dusuk, kapanis, k_n: int = 5, d_n: int = 3) -> pd.DataFrame:
    hh = yuksek.rolling(k_n, min_periods=k_n).max()
    ll = dusuk.rolling(k_n, min_periods=k_n).min()
    aralik = (hh - ll).where(hh != ll)
    k = 100.0 * (kapanis - ll) / aralik
    return pd.DataFrame({"k": k, "d": k.rolling(d_n, min_periods=d_n).mean()})


def cmf(yuksek, dusuk, kapanis, hacim, n: int = 21) -> pd.Series:
    aralik = (yuksek - dusuk).where(yuksek != dusuk)
    mfv = (((kapanis - dusuk) - (yuksek - kapanis)) / aralik).fillna(0.0) * hacim
    return mfv.rolling(n, min_periods=n).sum() / hacim.rolling(n, min_periods=n).sum()


def keltner_wband(yuksek, dusuk, kapanis, n: int = 20) -> pd.Series:
    """`ta` kütüphanesi original_version=True: bantlar tipik fiyat türevlerinin SMA'sı; genişlik = (üst-alt)/orta*100."""
    tp = (yuksek + dusuk + kapanis) / 3.0
    ust = ((4 * yuksek - 2 * dusuk + kapanis) / 3.0).rolling(n, min_periods=n).mean()
    alt = ((-2 * yuksek + 4 * dusuk + kapanis) / 3.0).rolling(n, min_periods=n).mean()
    orta = tp.rolling(n, min_periods=n).mean()
    return (ust - alt) / orta * 100.0


def donchian_pband(yuksek, dusuk, kapanis, n: int = 10) -> pd.Series:
    hb = yuksek.rolling(n, min_periods=n).max()
    lb = dusuk.rolling(n, min_periods=n).min()
    return (kapanis - lb) / (hb - lb).where(hb != lb)


def dalga_trend(yuksek, dusuk, kapanis, n1: int = 10, n2: int = 21, ort: int = 4) -> pd.DataFrame:
    """WaveTrend (LazyBear): wt1 = EMA(n2, CI), wt2 = SMA(ort, wt1)."""
    ap = (yuksek + dusuk + kapanis) / 3.0
    esa = ap.ewm(span=n1, adjust=False, min_periods=n1).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False, min_periods=n1).mean()
    ci = (ap - esa) / (0.0015 * d.where(d != 0))
    wt1 = ci.ewm(span=n2, adjust=False, min_periods=n2).mean()
    return pd.DataFrame({"wt1": wt1, "wt2": wt1.rolling(ort, min_periods=ort).mean()})


def genisleyen_minmax(seri: pd.Series, isinma: int = 300) -> pd.Series:
    """NEDENSEL min-max ölçekleme: (x - o ana kadarki min) / (o ana kadarki max - min). İlk `isinma` mum NaN.
    (Orijinal sklearn MinMaxScaler tüm veriyi görür = gelecek sızıntısı; burada genişleyen pencere.)"""
    mn, mx = seri.cummin(), seri.cummax()
    out = (seri - mn) / (mx - mn).where(mx != mn)
    out.iloc[:int(isinma)] = np.nan
    return out


def sayac(kosul: pd.Series) -> np.ndarray:
    """kosul True olan ardışık mum sayısı (False'ta 0)."""
    k = kosul.fillna(False).to_numpy(dtype=bool)
    out = np.zeros(len(k), dtype=np.int64)
    c = 0
    for i, v in enumerate(k):
        c = c + 1 if v else 0
        out[i] = c
    return out


def td_sayim(yuksek, dusuk, kapanis, geri: int = 4, n: int = 9) -> dict:
    """TD Sequential kurulum sayımı (freqtrade TDSequentialStrategy mantığı, nedensel).
    alis: ardışık kapanış < kapanış[geri önce] sayısı; satis: ardışık >. `n`'inci mumdan sonra (ve n-1'de) 'aşma' kontrolü:
    düşük, sayımın 6. veya 7. mumunun düşüğünün altında mı (alış) / yüksek üstünde mi (satış). n=9 için orijinal."""
    h, l = yuksek.to_numpy(float), dusuk.to_numpy(float)
    alis = sayac(kapanis < kapanis.shift(geri))
    satis = sayac(kapanis > kapanis.shift(geri))
    nn = len(h)

    def asma(sayim, x, alt):
        out = np.zeros(nn, dtype=bool)
        for i in range(nn):
            s = sayim[i]
            if s < n - 1:
                continue
            if s == n - 1:
                a, b = i - 2, i - 1
            else:
                a, b = i - (n - 6) - (s - n), i - (n - 7) - (s - n)
            if a < 0 or b < 0:
                continue
            v = (x[i] < x[a]) or (x[i] < x[b]) if alt else (x[i] > x[a]) or (x[i] > x[b])
            if s == n:
                v = v or (out[i - 1] if i > 0 else False)
            out[i] = v
        return out

    return {"alis": alis, "satis": satis, "asma_alt": asma(alis, l, True), "asma_ust": asma(satis, h, False)}


def _gun_baslangici(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_localize(None).normalize() if index.tz is not None else index.normalize()


def ay_sonuna_kalan_gun(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun UTC gününden ayın son gününe kalan takvim günü (son gün = 0). Takvim bilgisi: gelecek fiyatı değil."""
    d = _gun_baslangici(index)
    return np.asarray((d + pd.offsets.MonthEnd(0) - d).days)


def son_cuma_kalan_gun(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun gününden o ayın SON CUMA'sına kalan gün (Cuma sonrası negatif)."""
    d = _gun_baslangici(index)
    me = d + pd.offsets.MonthEnd(0)
    sc = me - pd.to_timedelta((me.dayofweek - 4) % 7, unit="D")
    return np.asarray((sc - d).days)
