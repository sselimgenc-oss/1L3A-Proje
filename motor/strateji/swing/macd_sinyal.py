"""swing__macd-sinyal: MACD sinyal çizgisi / sıfır çizgisi kesişimi.

Kaynak kartlar: boxer, make, razaq, hogan, graham, johnson, kratter (sıfır geçişi);
impuls-sistemi (kratter) kodlanmadı (EMA13 + histogram rengi ayrı bir sistem).
Ortak çekirdek (kartlar): MACD(12,26,9) çizgisi sinyal çizgisini yukarı keserse long, aşağı keserse short;
alternatif tetik: MACD çizgisinin sıfırı geçmesi (mod="sifir"). Johnson: ters kesişimde çık.
Kanonik kural ile kart çelişkisi yok.

Varsayımlar (kitapta yok): kartların hiçbiri stop vermiyor -> stop = kapanış -/+ atr_k*ATR;
hedef yok (NaN), çıkış = ters kesişim (`cikis`). Boxer'ın "3 gün tutma" filtresi uygulanmadı.
sifir_filtre=True: sinyal kesişimi long için MACD>0, short için MACD<0 iken (Johnson s.66, "daha güçlü").
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MacdSinyal(Strateji):
    ad = "swing__macd-sinyal"
    stil = "swing"
    varsayilan_parametreler = {
        "hizli": 12, "yavas": 26, "sinyal": 9,
        "mod": "sinyal",          # "sinyal": MACD x sinyal çizgisi | "sifir": MACD x 0
        "sifir_filtre": False,
        "atr_periyot": 14, "atr_k": 2.0,
        "short": True,
    }
    parametre_izgarasi = {
        "mod": ["sinyal", "sifir"],
        "sinyal": [5, 9, 12],
        "atr_k": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        m = g.macd(kap, p["hizli"], p["yavas"], p["sinyal"])
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, p["atr_periyot"])
        hat, sin = m["macd"], m["sinyal"]
        if p["mod"] == "sifir":
            yukari = (hat > 0) & (hat.shift(1) <= 0)
            asagi = (hat < 0) & (hat.shift(1) >= 0)
        else:
            yukari = (hat > sin) & (hat.shift(1) <= sin.shift(1))
            asagi = (hat < sin) & (hat.shift(1) >= sin.shift(1))
            if p["sifir_filtre"]:
                yukari, asagi = yukari & (hat > 0), asagi & (hat < 0)
        gecerli = atr.notna() & hat.notna()
        long_ok = yukari & gecerli
        short_ok = asagi & gecerli & bool(p["short"])
        return sinyal_cercevesi(
            mumlar.index, long_ok, short_ok,
            kap - p["atr_k"] * atr, kap + p["atr_k"] * atr,
            cikis=(yukari | asagi) & gecerli)

    def cikis_var_mi(self) -> bool:
        """Ters kesişim `cikis` üretir (her zaman)."""
        return True
