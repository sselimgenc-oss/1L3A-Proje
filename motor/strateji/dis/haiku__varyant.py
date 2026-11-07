"""Ar-Ge kolu (haiku__): sınırdaki adayların ön kayıtlı varyantları (sonuclar/haiku_arge/GELISTIRME_ON_KAYIT.md).

Ana sınıflar değişmez; varyantlar onları miras alır ve yalnız sinyal çıktısını maskeler (ekle) ya da
varsayılan parametreyi değiştirir (çıkar/ekle). Filtre eşikleri a priori sabittir; ayar ızgarası eklenmez.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade.donchian_kirilim import DonchianKirilim as _DonDay
from motor.strateji.dis.d1_trend_ma import AtrRsiLiwei as _Liwei
from motor.strateji.swing.rsi_momentum_esik import RsiMomentumEsik as _RsiEsik


def _filtre_izin(mumlar: pd.DataFrame, filtre: str):
    """(long_izinli, short_izinli) boolean seriler. Eşikler ön kayıtta sabitlendi."""
    k = mumlar["kapanis"]
    y, d = mumlar["yuksek"], mumlar["dusuk"]
    izin_l = pd.Series(True, index=mumlar.index)
    izin_s = pd.Series(True, index=mumlar.index)
    if "ema" in filtre:
        e = g.ema(k, 200)
        izin_l &= (k > e).fillna(False)
        izin_s &= (k < e).fillna(False)
    if "vol" in filtre:
        atr = g.atr(y, d, k, 14)
        med = atr.rolling(200, min_periods=200).median()
        ok = (atr > med).fillna(False)
        izin_l &= ok
        izin_s &= ok
    return izin_l, izin_s


def _maskele(sig: pd.DataFrame, izin_l, izin_s) -> pd.DataFrame:
    yon = sig["yon"].astype("int64")
    iptal = ((yon == 1) & ~izin_l) | ((yon == -1) & ~izin_s)
    s = sig.copy()
    s.loc[iptal, "yon"] = 0
    s.loc[s["yon"] == 0, ["stop", "hedef"]] = np.nan
    s["yon"] = s["yon"].astype("int64")
    return s


class _Maskeli:
    """Mixin: temel sinyalleri filtre ile maskeler. `filtre` in {"ema", "vol", "ema_vol"}."""
    filtre = ""

    def sinyaller(self, mumlar):
        sig = super().sinyaller(mumlar)
        izin_l, izin_s = _filtre_izin(mumlar, self.filtre)
        return _maskele(sig, izin_l, izin_s)


def _ayar(base, **degisen):
    return {**base.varsayilan_parametreler, **degisen}


# ------------------------------------------------------------------ A: daytrade__donchian-kirilim (XU30 1h)
class HaikuDonEma(_Maskeli, _DonDay):
    ad = "haiku__don-ema200"
    filtre = "ema"


class HaikuDonVol(_Maskeli, _DonDay):
    ad = "haiku__don-vol"
    filtre = "vol"


class HaikuDonEmaVol(_Maskeli, _DonDay):
    ad = "haiku__don-ema-vol"
    filtre = "ema_vol"


class HaikuDonNotrend(_DonDay):
    ad = "haiku__don-notrend"
    varsayilan_parametreler = _ayar(_DonDay, trend_ma=0)


# ------------------------------------------------------------------ B: dis__atr-rsi-liwei (XU30 1h)
class HaikuLiweiEma(_Maskeli, _Liwei):
    ad = "haiku__liwei-ema200"
    filtre = "ema"


class HaikuLiweiVol(_Maskeli, _Liwei):
    ad = "haiku__liwei-vol"
    filtre = "vol"


class HaikuLiweiEmaVol(_Maskeli, _Liwei):
    ad = "haiku__liwei-ema-vol"
    filtre = "ema_vol"


class HaikuLiweiNoband(_Liwei):
    ad = "haiku__liwei-noband"
    varsayilan_parametreler = _ayar(_Liwei, norm_min=0.0, norm_maks=1e9)


# ------------------------------------------------------------------ C: swing__rsi-momentum-esik (DK_XAU 1d)
class HaikuRsiEma(_Maskeli, _RsiEsik):
    ad = "haiku__rsi-ema200"
    filtre = "ema"


class HaikuRsiVol(_Maskeli, _RsiEsik):
    ad = "haiku__rsi-vol"
    filtre = "vol"


class HaikuRsiEmaVol(_Maskeli, _RsiEsik):
    ad = "haiku__rsi-ema-vol"
    filtre = "ema_vol"


class HaikuRsiHedef2(_RsiEsik):
    ad = "haiku__rsi-hedef2"
    varsayilan_parametreler = _ayar(_RsiEsik, hedef_r=2.0)
