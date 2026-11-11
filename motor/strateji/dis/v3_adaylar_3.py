"""v3 adayları, parti 3: öncelik 3 tek-grafik stratejileri.

Üçüncü taraf kod kopyalanmadı. Sinyaller kapanmış mum verisiyle üretilir;
saatli kurallar mum süresini indeksten çıkarır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis.v3_adaylar_2 import _saatten_onceki_son_kapanis
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


def _atr_cerceve(m, long_ok, short_ok, atr_k=2.0, atr_n=14, hedef_r=0.0):
    k = m["kapanis"]
    a = g.atr(m["yuksek"], m["dusuk"], k, int(atr_n)) * float(atr_k)
    hl = k + hedef_r * a if hedef_r else None
    hs = k - hedef_r * a if hedef_r else None
    return cerceve(m, long_ok, short_ok, k - a, k + a, hl, hs)


def _mum_suresi(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 2:
        raise ValueError("mum süresi için en az iki mum gerekli")
    sureler = pd.TimedeltaIndex(index[1:] - index[:-1])
    sure = pd.Timedelta(sureler.value_counts().idxmax())
    if sure <= pd.Timedelta(0):
        raise ValueError("mum süresi pozitif olmalı")
    return sure


class EmaRsiHacimKesisim(Strateji):
    """EMA9/21 kesişimi, EMA50 yönü, RSI14 ve hacim teyidi."""

    ad, stil = "v3__ema-9-21-50-rsi-hacim", "daytrade"
    varsayilan_parametreler = {
        "ema_h": 9, "ema_y": 21, "ema_trend": 50, "rsi_n": 14,
        "rsi_ust": 70.0, "rsi_alt": 30.0, "hacim_n": 20,
        "min_hacim": 500_000.0, "stop_yuzde": 0.015, "hedef_yuzde": 0.03,
    }
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=0.01)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        eh, ey, et = (g.ema(k, int(p[x])) for x in ("ema_h", "ema_y", "ema_trend"))
        rsi = g.rsi(k, int(p["rsi_n"]))
        hv = m["hacim"].shift(1).rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        hacim = (m["hacim"] > hv) & (m["hacim"] > float(p["min_hacim"]))
        yuk = (eh.shift(1) <= ey.shift(1)) & (eh > ey)
        asagi = (eh.shift(1) >= ey.shift(1)) & (eh < ey)
        lo = yuk & (k > et) & (rsi < p["rsi_ust"]) & hacim
        sh = asagi & (k < et) & (rsi > p["rsi_alt"]) & hacim
        out = cerceve(m, lo, sh, k * (1 - p["stop_yuzde"]), k * (1 + p["stop_yuzde"]),
                       k * (1 + p["hedef_yuzde"]), k * (1 - p["hedef_yuzde"]))
        out["cikis_long"], out["cikis_short"] = asagi.fillna(False), yuk.fillna(False)
        return out


class LondraVolatiliteKirilim(Strateji):
    """Londra 08:00-11:00 arasında önceki 60 dakikanın aralık kırılımı."""

    ad, stil = "v3__londra-volatilite-kirilim", "daytrade"
    varsayilan_parametreler = {"aralik_dk": 60, "stop_yuzde": 0.005, "bas": 8, "bit": 11, "cikis": 16}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=0.005)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, idx, k = self.parametreler, m.index, m["kapanis"]
        sure = _mum_suresi(idx)
        pencere = pd.Timedelta(minutes=int(p["aralik_dk"]))
        if sure > pencere or pencere % sure:
            raise ValueError(f"v3__londra-volatilite-kirilim: {pencere} mum süresini tam bölmeli; bulunan {sure}")
        n = int(pencere / sure)
        yerel = idx.tz_convert("Europe/London")
        saat = yerel.hour + yerel.minute / 60
        seans = pd.Series((saat >= p["bas"]) & (saat < p["bit"]), index=idx)
        gun = pd.Series(yerel.date, index=idx)
        tepe = m["yuksek"].shift(1).rolling(n, min_periods=n).max()
        dip = m["dusuk"].shift(1).rolling(n, min_periods=n).min()
        lham, sham = seans & (k > tepe), seans & (k < dip)
        olay = lham | sham
        ilk = olay & (olay.astype(int).groupby(gun).cumsum() == 1)
        cikis = _saatten_onceki_son_kapanis(idx, int(p["cikis"]), zaman_dilimi="Europe/London")
        return cerceve(m, ilk & lham, ilk & sham, k * (1 - p["stop_yuzde"]),
                       k * (1 + p["stop_yuzde"]), None, None, cikis)


class Rsi32Yon(Strateji):
    ad, stil = "v3__rsi32-yon-hedef4", "daytrade"
    varsayilan_parametreler = {"rsi_n": 32, "orta": 50.0, "cikis_ust": 77.0, "cikis_alt": 23.0,
                               "guven_ust": 85.0, "guven_alt": 15.0, "hedef": 0.04, "atr_k": 3.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_n"])) * p["atr_k"]
        out = cerceve(m, r > p["orta"], r < p["orta"], k - a, k + a,
                       k * (1 + p["hedef"]), k * (1 - p["hedef"]))
        out["cikis_long"] = (r >= p["cikis_ust"]) | (r >= p["guven_ust"])
        out["cikis_short"] = (r <= p["cikis_alt"]) | (r <= p["guven_alt"])
        return out


class SmaTrendRsiAtr(Strateji):
    ad, stil = "v3__sma-trend-rsi-atr", "daytrade"
    varsayilan_parametreler = {"ust_tf": "1h", "sma_h": 20, "sma_y": 60, "rsi_n": 14,
                               "rsi_fark": 2.0, "atr_n": 14, "stop_atr": 1.5, "hedef_atr": 2.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        def hesapla(x):
            return pd.DataFrame({"h": g.sma(x["kapanis"], int(p["sma_h"])),
                                 "y": g.sma(x["kapanis"], int(p["sma_y"]))}, index=x.index)
        ust = ust_zaman(m, p["ust_tf"], hesapla)
        r = g.rsi(k, int(p["rsi_n"]))
        fark = r - r.shift(1)
        a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_n"]))
        out = cerceve(m, (ust.h > ust.y) & (fark >= p["rsi_fark"]),
                       (ust.h < ust.y) & (fark <= -p["rsi_fark"]),
                       k - p["stop_atr"] * a, k + p["stop_atr"] * a,
                       k + p["hedef_atr"] * a, k - p["hedef_atr"] * a)
        out["cikis_long"], out["cikis_short"] = (k < ust.h).fillna(False), (k > ust.h).fillna(False)
        return out


class YarimFitil(Strateji):
    ad, stil = "v3__yarim-fitil", "daytrade"
    varsayilan_parametreler = {"fitil_min": 0.40, "fitil_maks": 0.60, "karsi_maks": 0.20, "son_giris": 13, "cikis": 16}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        o, h, d, k = (m[x] for x in ("acilis", "yuksek", "dusuk", "kapanis"))
        ar = (h - d).where(lambda x: x > 0)
        ny = idx.tz_convert("America/New_York")
        dk = ny.hour * 60 + ny.minute
        seans = pd.Series((dk >= 9 * 60 + 30) & (dk < p["son_giris"] * 60), index=idx)
        lo = seans & (k > o) & ((h-k)/ar).between(p["fitil_min"], p["fitil_maks"]) & ((o-d)/ar <= p["karsi_maks"])
        sh = seans & (k < o) & ((k-d)/ar).between(p["fitil_min"], p["fitil_maks"]) & ((h-o)/ar <= p["karsi_maks"])
        cik = _saatten_onceki_son_kapanis(idx, int(p["cikis"]), zaman_dilimi="America/New_York")
        return cerceve(m, lo, sh, d, h, h, d, cik)


class MomentumSifirKesisim(Strateji):
    ad, stil = "v3__momentum-sifir-kesisim", "swing"
    varsayilan_parametreler = {"momentum_n": 20, "atr_k": 3.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p = self.parametreler
        mom = m["kapanis"].pct_change(int(p["momentum_n"]))
        out = _atr_cerceve(m, mom > 0, False, p["atr_k"], p["atr_n"])
        out["cikis_long"] = (mom <= 0).fillna(False)
        return out


class PazartesiDip(Strateji):
    ad, stil = "v3__pazartesi-dip-endeks", "swing"
    varsayilan_parametreler = {"ibs_maks": 0.25, "sma_n": 180, "stop_yuzde": 0.10}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        ar = (m["yuksek"] - m["dusuk"]).where(lambda x: x > 0)
        ibs = (k - m["dusuk"]) / ar
        lo = (m.index.day_of_week == 0) & (k < k.shift(1)) & (ibs <= p["ibs_maks"]) & (k < g.sma(k, int(p["sma_n"])))
        cik = pd.Series(m.index.day_of_week == 2, index=m.index)
        return cerceve(m, lo, False, k * (1 - p["stop_yuzde"]), None, None, None, cik)


class Rsi14Ema200Iz(Strateji):
    ad, stil = "v3__rsi14-ema200-izleyen-stop", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "giris": 40.0, "cikis": 75.0, "ema_n": 200, "iz_yuzde": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=0.10)

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        out = cerceve(m, (k > g.ema(k, int(p["ema_n"]))) & (r < p["giris"]), False,
                       k * (1 - p["iz_yuzde"]), None)
        out["cikis_long"] = (r > p["cikis"]).fillna(False)
        return out


class Rsi2Sma200Hacim(Strateji):
    ad, stil = "v3__rsi2-sma200-hacim", "swing"
    varsayilan_parametreler = {"rsi_n": 2, "giris": 10.0, "cikis": 65.0, "sma_n": 200,
                               "hacim_n": 20, "hacim_k": 1.5, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        r, sm = g.rsi(k, int(p["rsi_n"])), g.sma(k, int(p["sma_n"]))
        hv = m["hacim"].shift(1).rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        out = _atr_cerceve(m, (r < p["giris"]) & (k > sm) & (m["hacim"] > p["hacim_k"] * hv),
                           False, p["atr_k"], p["atr_n"])
        out["cikis_long"] = ((r > p["cikis"]) | (k < sm)).fillna(False)
        return out


class Rsi30HacimEma200(Strateji):
    ad, stil = "v3__rsi30-hacim-ema200", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "giris": 30.0, "cikis": 70.0, "ema_n": 200,
                               "hacim_n": 20, "hacim_k": 1.5, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        r, em = g.rsi(k, int(p["rsi_n"])), g.ema(k, int(p["ema_n"]))
        hv = m["hacim"].shift(1).rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        yuk = (r.shift(1) <= p["giris"]) & (r > p["giris"])
        out = _atr_cerceve(m, yuk & (k > em) & (m["hacim"] > p["hacim_k"] * hv), False,
                           p["atr_k"], p["atr_n"])
        out["cikis_long"] = ((r.shift(1) >= p["cikis"]) & (r < p["cikis"])).fillna(False)
        return out


class ZSkorKarsit(Strateji):
    ad, stil = "v3__z-skor-karsit", "swing"
    varsayilan_parametreler = {"pencere": 20, "giris_z": 2.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self): return True

    def sinyaller(self, m):
        p = self.parametreler
        r = m["kapanis"].pct_change()
        n = int(p["pencere"])
        sd = r.rolling(n, min_periods=n).std()
        z = (r - r.rolling(n, min_periods=n).mean()) / sd.where(sd > 0)
        out = _atr_cerceve(m, z < -p["giris_z"], z > p["giris_z"], p["atr_k"], p["atr_n"])
        out["cikis_long"], out["cikis_short"] = (z >= 0).fillna(False), (z <= 0).fillna(False)
        return out
