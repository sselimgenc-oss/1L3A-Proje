"""v2 YENİ ADAYLARI (ON_KAYIT_V2 2.8): yavaş zaman-serisi momentumu (short açabilir) ve kripto funding sinyalleri.

Hepsi tek-grafik `Strateji`, swing, birincil tf = 1d, GERÇEK ATR stoplu, short açar. ÖN TANIM: varsayılan ayarlar hiçbir
backtest görülmeden yazıldı; her satır TEK ana deneme, `parametre_izgarasi` yalnız S2 komşu-ayar kontrolü içindir.
Kod başka depodan kopyalanmadı; yalnız genel literatür fikirleri.

v2__tsmom-12-1  (etiket trend / tsmom_12_1)
  Moskowitz-Ooi-Pedersen (2012) "Time Series Momentum", tek-vade sürümü. Skor = kapanış[t-atla_gun] / kapanış[t-lookback_gun] - 1
  (takvim günü; 12-1 ay: 365 ve 30). Skor > 0 long, < 0 short. Çıkış: skor işaret değiştirince; ATR felaket stopu 5 x ATR(14).
v2__tsmom-oy  (etiket trend / tsmom_coklu_vade)
  Çok vadeli oylama (Hurst-Ooi-Pedersen 2017 "A Century of Evidence on Trend-Following": 1/3/12 ay sinyalleri birleşimi).
  Vadeler 30 / 90 / 365 gün, her birinin işareti (+1/-1) oylanır; ortalama > 0 long, < 0 short (3 oy: beraberlik yok). Çıkış: oylama
  işareti dönünce; stop 5 x ATR(14).
v2__funding-asiri-kontra  (etiket funding / asiri_funding_z)
  Kalabalık pozisyon karşıtlığı (perpetual funding, Ackerer-Hugonnier-Jermann 2023 ve duyarlılık literatürü): funding oranının
  `z_gun` (90) günlük z-skoru > +2 (long'lar kalabalık/aşırı pahalı) -> SHORT; < -2 -> LONG. Çıkış: z sıfırı geçince ya da `max_tut_gun`
  (20) gün sonra; stop 3 x ATR(14).
v2__funding-esik-karsit  (etiket funding / funding_esik)
  `ort_gun` (7) günlük ortalama funding, yıllıklandırılmış (oran x 365 x 24/fund_saat): > +%30 (taban ~%11) -> SHORT, < -%5 -> LONG;
  kısa çıkış: ort <= %10, uzun çıkış: ort >= 0; `max_tut_gun` (20) gün zaman çıkışı; stop 3 x ATR(14).
v2__trend-funding-suzgec  (etiket karma / trend_funding_suzgec)
  Trend (kapanış vs SMA(100)) + funding süzgeci: long yalnız kapanış > SMA ve funding z < +1 (long kalabalık değil); short yalnız
  kapanış < SMA ve z > -1. Çıkış: trend dönünce ya da funding aşırıya giderse (long için z > +2, short için z < -2); stop 4 x ATR(14).

Funding: `funding_gerekli = True` -> araştırma katmanı `funding_orani` ekler (mum kapanışında bilinen son oran; nedensel). Yalnız
kripto perp; DK_ sembollerde funding dosyası yok -> açık hata (funding=0 varsayılmaz); bu yüzden havuzda evren = kripto.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d4 import mum_gun_tahmin
from motor.strateji.dis.d6_funding import _funding_serisi
from motor.strateji.temel import Strateji


def gecmis_kapanis(kap: pd.Series, gun: int) -> pd.Series:
    """Her t için t - `gun` takvim gününde (dahil) bilinen SON kapanış (nedensel: yalnız geçmiş mumlar); yoksa NaN."""
    if gun < 0:
        raise ValueError("gun >= 0 olmalı")
    if gun == 0:
        return kap
    sonuc = kap.asof(kap.index - pd.Timedelta(days=int(gun)))
    return pd.Series(sonuc.to_numpy(dtype="float64"), index=kap.index)


def _atr_stop(mumlar: pd.DataFrame, k: float, periyot: int) -> tuple[pd.Series, pd.Series]:
    kap = mumlar["kapanis"]
    a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(periyot)) * float(k)
    return kap - a, kap + a


def _yonlu_cerceve(mumlar, long_ok, short_ok, cikis_long, cikis_short, atr_k, atr_periyot, max_tut_mum=None):
    stop_l, stop_s = _atr_stop(mumlar, atr_k, atr_periyot)
    out = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s)
    out["cikis_long"] = pd.Series(cikis_long, index=mumlar.index).fillna(False).astype(bool)
    out["cikis_short"] = pd.Series(cikis_short, index=mumlar.index).fillna(False).astype(bool)
    if max_tut_mum is not None:
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(max_tut_mum), np.nan), index=mumlar.index)
    return out


# ---------------------------------------------------------------- yavaş TSMOM (short açabilir)
class Tsmom121(Strateji):
    ad = "v2__tsmom-12-1"
    stil = "swing"
    varsayilan_parametreler = {"lookback_gun": 365, "atla_gun": 30, "short": True, "atr_k": 5.0, "atr_periyot": 14}
    parametre_izgarasi = {"lookback_gun": [180, 270, 365], "atla_gun": [0, 30]}

    def cikis_var_mi(self) -> bool:
        return True

    def skor(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        kap = mumlar["kapanis"]
        return gecmis_kapanis(kap, int(p["atla_gun"])) / gecmis_kapanis(kap, int(p["lookback_gun"])) - 1.0

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        s = self.skor(mumlar)
        short_ok = (s < 0) if p["short"] else pd.Series(False, index=mumlar.index)
        return _yonlu_cerceve(mumlar, s > 0, short_ok, s <= 0, s >= 0, p["atr_k"], p["atr_periyot"])


class TsmomOy(Strateji):
    ad = "v2__tsmom-oy"
    stil = "swing"
    varsayilan_parametreler = {"vade1_gun": 30, "vade2_gun": 90, "vade3_gun": 365, "short": True, "atr_k": 5.0,
                               "atr_periyot": 14}
    parametre_izgarasi = {"vade2_gun": [60, 90, 120], "vade3_gun": [180, 365]}

    def cikis_var_mi(self) -> bool:
        return True

    def oy(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        kap = mumlar["kapanis"]
        oylar = []
        for a in ("vade1_gun", "vade2_gun", "vade3_gun"):
            r = kap / gecmis_kapanis(kap, int(p[a])) - 1.0
            oylar.append(np.sign(r))
        return pd.concat(oylar, axis=1).mean(axis=1, skipna=False)      # herhangi bir vade hazır değilse NaN

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        o = self.oy(mumlar)
        short_ok = (o < 0) if p["short"] else pd.Series(False, index=mumlar.index)
        return _yonlu_cerceve(mumlar, o > 0, short_ok, o <= 0, o >= 0, p["atr_k"], p["atr_periyot"])


# ---------------------------------------------------------------- funding sinyalleri (kripto)
def _funding_z(mumlar: pd.DataFrame, ad: str, z_gun: int, gun_mum: int) -> pd.Series:
    fon = _funding_serisi(mumlar, ad)
    n = max(3, int(z_gun) * mum_gun_tahmin(mumlar.index, int(gun_mum)))
    sd = fon.rolling(n, min_periods=n).std()
    return (fon - fon.rolling(n, min_periods=n).mean()) / sd.where(sd > 0)


class FundingAsiriKontra(Strateji):
    ad = "v2__funding-asiri-kontra"
    stil = "swing"
    funding_gerekli = True
    varsayilan_parametreler = {"z_gun": 90, "giris_z": 2.0, "cikis_z": 0.0, "max_tut_gun": 20, "short": True,
                               "gun_mum": 0, "atr_k": 3.0, "atr_periyot": 14}
    parametre_izgarasi = {"giris_z": [1.5, 2.0, 2.5], "max_tut_gun": [10, 20, 40]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        z = _funding_z(mumlar, self.ad, p["z_gun"], p["gun_mum"])
        short_ok = (z > p["giris_z"]) if p["short"] else pd.Series(False, index=mumlar.index)
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        return _yonlu_cerceve(mumlar, z < -p["giris_z"], short_ok, z >= p["cikis_z"], z <= -p["cikis_z"],
                              p["atr_k"], p["atr_periyot"], max_tut_mum=max(1, int(p["max_tut_gun"]) * gm))


class FundingEsikKarsit(Strateji):
    ad = "v2__funding-esik-karsit"
    stil = "swing"
    funding_gerekli = True
    varsayilan_parametreler = {"ort_gun": 7, "esik_yuksek": 0.30, "esik_dusuk": -0.05, "cikis_yuksek": 0.10,
                               "cikis_dusuk": 0.0, "fund_saat": 8, "max_tut_gun": 20, "short": True, "gun_mum": 0,
                               "atr_k": 3.0, "atr_periyot": 14}
    parametre_izgarasi = {"ort_gun": [3, 7, 14], "esik_yuksek": [0.20, 0.30, 0.45]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        n = max(1, int(p["ort_gun"]) * gm)
        fon = _funding_serisi(mumlar, self.ad)
        yillik = fon.rolling(n, min_periods=n).mean() * 365.0 * 24.0 / float(p["fund_saat"])
        short_ok = (yillik > p["esik_yuksek"]) if p["short"] else pd.Series(False, index=mumlar.index)
        return _yonlu_cerceve(mumlar, yillik < p["esik_dusuk"], short_ok, yillik >= p["cikis_dusuk"],
                              yillik <= p["cikis_yuksek"], p["atr_k"], p["atr_periyot"],
                              max_tut_mum=max(1, int(p["max_tut_gun"]) * gm))


class TrendFundingSuzgec(Strateji):
    ad = "v2__trend-funding-suzgec"
    stil = "swing"
    funding_gerekli = True
    varsayilan_parametreler = {"sma_gun": 100, "z_gun": 90, "filtre_z": 1.0, "asiri_z": 2.0, "short": True,
                               "gun_mum": 0, "atr_k": 4.0, "atr_periyot": 14}
    parametre_izgarasi = {"sma_gun": [50, 100, 200], "filtre_z": [0.5, 1.0, 1.5]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        n = max(2, int(p["sma_gun"]) * gm)
        sma = kap.rolling(n, min_periods=n).mean()
        z = _funding_z(mumlar, self.ad, p["z_gun"], p["gun_mum"])
        ust, alt = kap > sma, kap < sma
        long_ok = ust & (z < p["filtre_z"])
        short_ok = (alt & (z > -p["filtre_z"])) if p["short"] else pd.Series(False, index=mumlar.index)
        return _yonlu_cerceve(mumlar, long_ok, short_ok, (kap <= sma) | (z > p["asiri_z"]),
                              (kap >= sma) | (z < -p["asiri_z"]), p["atr_k"], p["atr_periyot"])
