"""D6 funding tabanlı stratejiler (kripto perp). İkisi de `funding_gerekli = True`: araştırma katmanı mumlara nedensel
`funding_orani` sütunu ekler (motor/strateji/funding.py: mum KAPANIŞINDA bilinen son oran). Funding dosyası olmayan
sembolde (DK_) açık hata; funding=0 varsayılmaz. Sütun yoksa sinyaller() ValueError verir.

KOD KOPYALANMADI: yalnız kamuya açık kurallar kendi yapımızla yazıldı.

Funding aralığı: Binance perp'lerinde 8 saat varsayılır (`fund_saat`, günde 3 ödeme). Yıllıklandırma = oran x 365 x 24/fund_saat.
Sütun mum başına ileri doldurulmuş olduğundan "N funding" pencereleri ZAMAN ağırlıklı pencereyle (N x fund_saat saat) yapılır.

dis__ewmac-carry  (swing, 4h ve 1d)
  Kaynak: Carver, *Leveraged Trading* (2019) ve *Systematic Trading* (2015): trend (EWMAC) + carry tahmininin birleşimi.
  Kural: trend tahmini = dis__ewmac-carver'ın birleşik EWMAC tahmini (+-20). Carry tahmini = -(son `carry_gun` günün ortalama
    funding'i, yıllıklandırılmış) / yıllık fiyat volatilitesi x `carry_olcek` (30), +-20 kırpılır. Funding pozitifken (longlar
    öder) carry tahmini negatiftir; negatifken pozitiftir. Kombine = `trend_agirlik` x trend + (1 - trend_agirlik) x carry
    (0.7 / 0.3), +-20. Yıllık vol = mum getirilerinin üstel std'si (span std_gun gün) x sqrt(365 x günlük_mum).
  Giriş / çıkış / ATR felaket stopu: dis__ewmac-carver ile BİREBİR aynı mantık (EwmacCarver alt sınıfı; yalnız tahmin() değişir).
  Kısıt: carry (funding) NaN olan satırda kombine tahmin NaN -> sinyal yok (ilk `carry_gun` gün). Yalnız kripto perp.
  ALINMADI: carry ağırlığının/ölçeğinin veriden kalibrasyonu, carry için ayrı vol/forecast çarpanı, sürekli pozisyon boyutu.

dis__funding-carry  (daytrade, 1h; 30m'de de çalışır)
  Kaynak: nateemma/strategies `Funding/FundingCarry.py` (GPL-3.0; KOD KOPYALANMADI) — ek_77_strateji.md #2.
  Kural: son 90 funding'in (`z_pencere`; ~30 gün) z-skoru < `giris_z` (-1.5) -> long (shortlar kalabalık). Z-skor, ileri doldurulmuş
    seride 90 x fund_saat saatlik (zaman ağırlıklı) pencerede hesaplanır; std = 0 ise sinyal yok. Çıkış: `max_tut_saat` (16)
    saat sonra ZAMAN çıkışı (zaman_cikisi_mum) + zorunlu ATR stopu (k x ATR; orijinalde stop yoktu, bizde motor zorunlu kılar).
  Rejim filtresi: `rejim=True` iken long yalnız kapanış, SMA(`sma_saat`=500 saat ~ 21 gün) üzerindeyken. Burada SEMBOLÜN KENDİ SMA'sı
    kullanılır; orijinaldeki "yalnız BTC SMA'sı" filtresi BTC dışı sembollerde tek-grafik stratejiye sığmaz -> portföy katmanına
    bırakıldı (BTC'yi filtre olarak kullanan kol/üst katman). BTC'de iki yorum aynıdır.
  Opsiyonel short ayna (`short=True`, varsayılan KAPALI): z > -giris_z (+1.5, longlar kalabalık) -> short; rejim açıksa
    kapanış SMA altındayken. Aynı zaman çıkışı ve ATR stopu.
  Fark: orijinal spot long (beta taşır, hedge yok); burada perp + motorun funding muhasebesi. Hacim %10 sınırı alınmadı.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d4 import TAHMIN_SINIRI, mum_gun_tahmin
from motor.strateji.dis.d4_sistematik import EwmacCarver
from motor.strateji.funding import SUTUN
from motor.strateji.temel import Strateji


def _funding_serisi(mumlar: pd.DataFrame, ad: str) -> pd.Series:
    if SUTUN not in mumlar.columns:
        raise ValueError(f"{ad}: mumlarda '{SUTUN}' sütunu yok (funding_gerekli strateji; "
                         f"motor.strateji.funding.stratejiye_hazirla ile hazırlanmalı)")
    return mumlar[SUTUN].astype("float64")


class EwmacCarry(EwmacCarver):
    ad = "dis__ewmac-carry"
    stil = "swing"
    funding_gerekli = True
    varsayilan_parametreler = {
        **EwmacCarver.varsayilan_parametreler,
        "trend_agirlik": 0.7, "carry_gun": 30, "carry_olcek": 30.0, "fund_saat": 8,
    }
    parametre_izgarasi = {
        "varyantlar": ["2/8+4/16+8/32", "16/64+32/128", "32/128+64/256"],
        "esik": [3.0, 5.0, 10.0],
        "trend_agirlik": [0.5, 0.7, 0.85],
    }

    def trend_tahmin(self, mumlar: pd.DataFrame) -> pd.Series:
        return super().tahmin(mumlar)

    def carry_tahmin(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        fon = _funding_serisi(mumlar, self.ad)
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        pencere = max(1, int(round(int(p["carry_gun"]) * gm)))
        ort = fon.rolling(pencere, min_periods=pencere).mean()
        yillik_fund = ort * 365.0 * 24.0 / float(p["fund_saat"])
        getiri = mumlar["kapanis"].pct_change()
        std_mum = getiri.ewm(span=max(2, int(p["std_gun"]) * gm), adjust=False, min_periods=int(p["std_gun"]) * gm).std()
        yillik_vol = std_mum * np.sqrt(365.0 * gm)
        ham = -yillik_fund / yillik_vol.where(yillik_vol > 0) * float(p["carry_olcek"])
        return ham.clip(-TAHMIN_SINIRI, TAHMIN_SINIRI)

    def tahmin(self, mumlar: pd.DataFrame) -> pd.Series:
        w = float(self.parametreler["trend_agirlik"])
        if not 0.0 <= w <= 1.0:
            raise ValueError("trend_agirlik 0..1 olmalı")
        t = self.trend_tahmin(mumlar)
        c = self.carry_tahmin(mumlar)
        return (w * t + (1.0 - w) * c).clip(-TAHMIN_SINIRI, TAHMIN_SINIRI)


class FundingCarry(Strateji):
    ad = "dis__funding-carry"
    stil = "daytrade"
    funding_gerekli = True
    varsayilan_parametreler = {
        "z_pencere": 90, "fund_saat": 8, "giris_z": -1.5, "max_tut_saat": 16.0, "rejim": True, "sma_saat": 500,
        "short": False, "gun_mum": 0, "atr_k": 3.0, "atr_periyot": 14,
        # d11j EK (varsayılan eski davranış; ızgaraya girmez): giris_modu="esik" -> z-skor yerine DÜZ funding seviyesi:
        # funding > fon_esik ise short (short=True gerekir), funding < -fon_esik ise long (long=True). Kaynak aile funding-pozitif-short
        # (özel seri API örneği: son fonlama > 0 -> short; çıkış yok -> max_tut_saat zaman çıkışı + ATR stop varsayım).
        "giris_modu": "zskor", "fon_esik": 0.0, "long": True,
    }
    parametre_izgarasi = {
        "giris_z": [-1.0, -1.5, -2.0],
        "max_tut_saat": [8.0, 16.0, 32.0],
        "atr_k": [2.0, 3.0, 5.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def zskor(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        fon = _funding_serisi(mumlar, self.ad)
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        n = max(3, int(round(int(p["z_pencere"]) * float(p["fund_saat"]) / 24.0 * gm)))
        ort = fon.rolling(n, min_periods=n).mean()
        sd = fon.rolling(n, min_periods=n).std()
        return (fon - ort) / sd.where(sd > 0)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        kap = mumlar["kapanis"]
        z = self.zskor(mumlar)
        gm = mum_gun_tahmin(idx, int(p["gun_mum"]))
        if p["giris_modu"] == "esik":
            fon = _funding_serisi(mumlar, self.ad)
            long_ok = (fon < -p["fon_esik"]) if p["long"] else pd.Series(False, index=idx)
            short_ok = (fon > p["fon_esik"]) if p["short"] else pd.Series(False, index=idx)
        elif p["giris_modu"] == "zskor":
            long_ok = (z < p["giris_z"]) if p["long"] else pd.Series(False, index=idx)
            short_ok = (z > -p["giris_z"]) if p["short"] else pd.Series(False, index=idx)
        else:
            raise ValueError(f"Bilinmeyen giris_modu: {p['giris_modu']}")
        if p["rejim"]:
            n_sma = max(2, int(round(int(p["sma_saat"]) * gm / 24.0)))
            sma = kap.rolling(n_sma, min_periods=n_sma).mean()
            long_ok = long_ok & (kap > sma)
            short_ok = short_ok & (kap < sma)
        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_periyot"])) * p["atr_k"]
        out = cerceve(mumlar, long_ok, short_ok, kap - a, kap + a)
        n_cik = max(1, int(round(float(p["max_tut_saat"]) * gm / 24.0)))
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(n_cik), np.nan), index=idx)
        return out
