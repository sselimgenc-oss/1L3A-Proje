"""swing__bant-donus: Bollinger bandı dışından orta banda dönüş (ortalamaya dönüş).

Kaynak kartlar: make, johnson (x2), kratter (gimmee), boxer (W/M formasyonu: ayrı formasyon, kodlanmadı).
Ortak çekirdek: kapanış alt (üst) bandın dışına çıkar; bant içine geri dönüş mumunda long (short);
hedef orta bant (SMA). Kartlarda ek filtre: yatay piyasa (kratter ADX yatay, make "trend piyasada kullanma").
Çelişkiler: kanonik kuraldaki "RSI(5)<20-30 ve ADX<25" kaynak kartlarda yok (Stevenson/Carson kartlarından,
listede değil); kartlarda yalnızca johnson RSI(14)<30 var. Bu yüzden RSI isteğe bağlı (rsi_esik=0: kapalı),
ADX<esik varsayılan açık (make/kratter yatay piyasa şartı; esik değeri kanondan: 25).
Kartlar short'u sadece johnson/make'te veriyor; ayna olarak uygulandı.

Varsayımlar: tetik = önceki kapanış bant dışında, şimdiki kapanış içinde (teyit); stop = dışarı çıkış mumu ve
tetik mumunun karşı ucu -/+ stop_tampon_atr*ATR (kartlar stop vermiyor); hedef = tetik anındaki orta bant
(hedef_tipi="orta") veya karşı bant ("karsi"); "yok" -> NaN. Çıkış sinyali yok (hedef/stop yeterli).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class BantDonus(Strateji):
    ad = "swing__bant-donus"
    stil = "swing"
    varsayilan_parametreler = {
        "bb_periyot": 20, "bb_sapma": 2.0,
        "rsi_periyot": 5, "rsi_esik": 0.0,       # 0: kapalı; long için RSI<esik, short için RSI>100-esik
        "adx_periyot": 14, "adx_esik": 25.0,     # 0: kapalı; ADX < esik şartı
        "trend_ma": 0,                           # 0: kapalı; long için kapanış > EMA(trend_ma)
        "atr_periyot": 14, "stop_tampon_atr": 0.25,
        "hedef_tipi": "orta",                    # "orta" | "karsi" | "yok"
        "short": True,
    }
    parametre_izgarasi = {
        "bb_periyot": [20, 30, 40],
        "bb_sapma": [2.0, 2.5, 3.0],
        "adx_esik": [0.0, 20.0, 25.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        bb = g.bollinger(k, p["bb_periyot"], p["bb_sapma"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        disarda_alt = k < bb["alt"]
        disarda_ust = k > bb["ust"]
        long_ok = disarda_alt.shift(1, fill_value=False) & (k >= bb["alt"]) & (k < bb["orta"])
        short_ok = disarda_ust.shift(1, fill_value=False) & (k <= bb["ust"]) & (k > bb["orta"]) & bool(p["short"])
        if p["rsi_esik"]:
            r = g.rsi(k, p["rsi_periyot"]).shift(1)     # dışarı çıkış mumundaki RSI
            long_ok &= r < p["rsi_esik"]
            short_ok &= r > 100 - p["rsi_esik"]
        if p["adx_esik"]:
            long_ok &= g.adx(y, d, k, p["adx_periyot"])["adx"] < p["adx_esik"]
            short_ok &= g.adx(y, d, k, p["adx_periyot"])["adx"] < p["adx_esik"]
        if p["trend_ma"]:
            tr = g.ema(k, p["trend_ma"])
            long_ok &= k > tr
            short_ok &= k < tr
        gecerli = atr.notna() & bb["orta"].notna()
        long_ok &= gecerli
        short_ok &= gecerli

        stop_l = np.minimum(d, d.shift(1)) - p["stop_tampon_atr"] * atr
        stop_s = np.maximum(y, y.shift(1)) + p["stop_tampon_atr"] * atr
        if p["hedef_tipi"] == "orta":
            h_l = h_s = bb["orta"]
        elif p["hedef_tipi"] == "karsi":
            h_l, h_s = bb["ust"], bb["alt"]
        else:
            h_l = h_s = None
        return sinyal_cercevesi(mumlar.index, long_ok, short_ok, stop_l, stop_s, h_l, h_s)

    def cikis_var_mi(self) -> bool:
        """hedef_tipi='yok' ise hedef/çıkış sinyali yok."""
        return self.parametreler["hedef_tipi"] != "yok"
