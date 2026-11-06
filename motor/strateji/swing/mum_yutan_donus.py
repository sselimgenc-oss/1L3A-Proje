"""swing__mum-yutan-donus — yutan mum / dış bar tersine dönüş.

Kural (kartların ortak çekirdeği):
  Long: önceki trend aşağı (kapanış[t-1] < kapanış[t-1-trend_mum] ve düşüş >= trend_min_atr*ATR),
  önceki mum düşüş (kırmızı), mevcut mum yükseliş (yeşil) ve gövdesi önceki gövdeyi tamamen yutar
  (açılış <= önceki kapanış, kapanış >= önceki açılış, gövde daha büyük). Hacim onayı: hacim >
  hacim_k * ortalama(hacim_ort_mum) (hacim_k=0: kapalı). Giriş: yutan mumun KAPANIŞINDA.
  Short: ayna (yükseliş trendi sonunda ayı yutan).
  Stop: yutan + yutulan mumun karşı ucu (stop_modu="uc": iki mumun dip/tepesi, tampon_atr ile),
  "yarim": iki mum aralığının %50 seviyesi (Day kartı). Risk > maks_risk_atr*ATR ise işlem yok.
  Hedef: hedef_r * risk (kartlar net hedef vermiyor; 1.5-3R backtest aralığı).

Kaynak kartlar: yutma-formasyonu__hogan, yutan-mum-hacim__graham, yutan-mum-trend-sonu__day,
  iki-bar-tersine-donus__day, yutan-mum-doji-donus__jordan, bar-inversiyon-tersine-donus__derr, vb.
Kanıt: ailede pozitif/negatif sayısal kanıt YOK (Bulkowski yüzdeleri Graham'dan dolaylı aktarım).
Varsayımlar: "trend" tanımı kartlarda yok; N-mum kapanış karşılaştırması + ATR büyüklük eşiği
  tarafımızdan seçildi. Gövde yutması (fitil değil) esas alındı (Hogan); Derr'in dış-bar (high/low
  yutma) varyantı kodlanmadı. Destek/direnç yakınlığı filtresi yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MumYutanDonus(Strateji):
    ad = "swing__mum-yutan-donus"
    stil = "swing"
    varsayilan_parametreler = {
        "trend_mum": 6, "trend_min_atr": 1.0, "hacim_k": 0.0, "hacim_ort_mum": 20,
        "stop_modu": "uc", "tampon_atr": 0.1, "maks_risk_atr": 3.0,
        "hedef_r": 2.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "trend_mum": [5, 7, 10],
        "hacim_k": [0.0, 1.0, 1.5],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        ac, yu, du, kap = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(yu, du, kap, p["atr_periyot"])
        ac1, kap1 = ac.shift(1), kap.shift(1)
        N = int(p["trend_mum"])
        dusus = (kap1 < kap.shift(1 + N)) & ((kap.shift(1 + N) - kap1) >= p["trend_min_atr"] * atr)
        yukselis = (kap1 > kap.shift(1 + N)) & ((kap1 - kap.shift(1 + N)) >= p["trend_min_atr"] * atr)
        boga = ((kap1 < ac1) & (kap > ac) & (ac <= kap1) & (kap >= ac1)
                & ((kap - ac) > (ac1 - kap1)))
        ayi = ((kap1 > ac1) & (kap < ac) & (ac >= kap1) & (kap <= ac1)
               & ((ac - kap) > (kap1 - ac1)))
        long_ok, short_ok = boga & dusus, ayi & yukselis & bool(p["short"])
        if p["hacim_k"] > 0:
            ort = mumlar["hacim"].shift(1).rolling(int(p["hacim_ort_mum"]), min_periods=int(p["hacim_ort_mum"])).mean()
            hok = mumlar["hacim"] > p["hacim_k"] * ort
            long_ok, short_ok = long_ok & hok, short_ok & hok

        alt2 = np.minimum(du, du.shift(1))
        ust2 = np.maximum(yu, yu.shift(1))
        tamp = p["tampon_atr"] * atr
        if p["stop_modu"] == "uc":
            stop_l, stop_s = alt2 - tamp, ust2 + tamp
        else:
            stop_l = stop_s = (alt2 + ust2) / 2.0
        risk_l, risk_s = kap - stop_l, stop_s - kap
        if p["maks_risk_atr"] > 0:
            long_ok = long_ok & (risk_l <= p["maks_risk_atr"] * atr)
            short_ok = short_ok & (risk_s <= p["maks_risk_atr"] * atr)
        long_ok = (long_ok & (risk_l > 0) & atr.notna()).fillna(False).to_numpy()
        short_ok = (short_ok & (risk_s > 0) & atr.notna()).fillna(False).to_numpy()

        yon = np.where(long_ok, 1, np.where(short_ok, -1, 0))
        stop = np.where(long_ok, stop_l, np.where(short_ok, stop_s, np.nan))
        k = kap.to_numpy()
        hedef = np.where(long_ok, k + p["hedef_r"] * risk_l.to_numpy(),
                         np.where(short_ok, k - p["hedef_r"] * risk_s.to_numpy(), np.nan))
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)
