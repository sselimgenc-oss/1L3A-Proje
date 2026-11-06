"""swing__aralik-ticareti — yatay aralıkta alt sınırdan al, üst sınırdan sat.

Kural (kartların ortak çekirdeği):
  Aralık = önceki `pencere` mumun Donchian üst/alt sınırı (mevcut mum hariç). Aralık ticarete
  uygun: genişlik >= min_genislik_atr*ATR ve (adx_esik>0 ise) ADX < adx_esik (yatay piyasa).
  Long: mumun dibi alt sınıra `bant*genişlik` içine iner (hafif aşması serbest, Kratter),
  mum yükseliş (tepki) mumu olarak kapanır ve kapanış alt sınırın üstünde ve aralık ortasının
  altındadır. Short: ayna (üst sınır, düşüş mumu).
  Stop: "dip" modu: aralık dibi/mumun dibi (hangisi düşükse) - stop_tampon_atr*ATR (Ladha/Kratter);
  "yarim_aralik": giriş -/+ 0.5*genişlik (aile özeti). Hedef: karşı sınır (Graham/Ladha);
  hedef-giriş mesafesi < min_rr*risk ise işlem yok.

Kaynak kartlar: destek-direnc-aralik__ladha, destek-direnc-aralik__penn,
  kripto-kutu-destek-ustu-kapanis__razaq, aralik-sinir-ticareti__graham, kutu-destekten-alim__kratter.
Kanıt: ailede sayısal kanıt yok. Belirsizlik: aralık kırılınca zarar büyük; kanonik taslaktaki
  "RSI/Stokastik aşırı satım" kartlarda ortak çekirdek DEĞİL (Graham: osilatör gerekmez), kodlanmadı.
Varsayımlar: Aralık tespiti Donchian penceresi (kartlarda "yöntem tanımsız"); Ladha'nın "2 gün
  üst üste kırılım = aralık bitti" kuralı, pencerenin kendiliğinden güncellenmesiyle yaklaşıldı;
  4. testten sonra zayıflama kuralı yok; haftalık teyit yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import sinyal_cercevesi
from motor.strateji.temel import Strateji


class AralikTicareti(Strateji):
    ad = "swing__aralik-ticareti"
    stil = "swing"
    varsayilan_parametreler = {
        "pencere": 50, "bant": 0.2, "min_genislik_atr": 3.0, "adx_esik": 25.0, "adx_periyot": 14,
        "stop_modu": "dip", "stop_tampon_atr": 0.25, "min_rr": 1.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "pencere": [20, 50, 100],
        "bant": [0.1, 0.2, 0.3],
        "adx_esik": [0.0, 20.0, 25.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        ac, yu, du, kap = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        W = int(p["pencere"])
        atr = g.atr(yu, du, kap, p["atr_periyot"])
        ust = yu.shift(1).rolling(W, min_periods=W).max()
        alt = du.shift(1).rolling(W, min_periods=W).min()
        gen = ust - alt
        orta = (ust + alt) / 2.0
        uygun = (gen >= p["min_genislik_atr"] * atr) & atr.notna()
        if p["adx_esik"] > 0:
            uygun = uygun & (g.adx(yu, du, kap, int(p["adx_periyot"]))["adx"] < p["adx_esik"])
        long_ok = uygun & (du <= alt + p["bant"] * gen) & (kap > ac) & (kap > alt) & (kap < orta)
        short_ok = (uygun & (yu >= ust - p["bant"] * gen) & (kap < ac) & (kap < ust) & (kap > orta)
                    & bool(p["short"]))

        tamp = p["stop_tampon_atr"] * atr
        if p["stop_modu"] == "dip":
            stop_l = np.minimum(alt, du) - tamp
            stop_s = np.maximum(ust, yu) + tamp
        else:
            stop_l, stop_s = kap - 0.5 * gen, kap + 0.5 * gen
        risk_l, risk_s = kap - stop_l, stop_s - kap
        long_ok = long_ok & (risk_l > 0) & ((ust - kap) >= p["min_rr"] * risk_l)
        short_ok = short_ok & (risk_s > 0) & ((kap - alt) >= p["min_rr"] * risk_s)
        long_ok, short_ok = long_ok.fillna(False).to_numpy(), short_ok.fillna(False).to_numpy()

        yon = np.where(long_ok, 1, np.where(short_ok, -1, 0))
        stop = np.where(long_ok, stop_l, np.where(short_ok, stop_s, np.nan))
        hedef = np.where(long_ok, ust, np.where(short_ok, alt, np.nan))
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)
