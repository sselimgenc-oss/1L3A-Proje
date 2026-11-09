"""swing__bollinger-cift-bant-trend: fiyat 1SD ile 2SD Bollinger bantları arasındaysa trend güçlüdür.

Kural: iki Bollinger seti (aynı SMA, ic_sapma=1 ve dis_sapma=2). Long: kapanış üst 1SD bandının üstünde ve üst 2SD
bandının altında/üzerinde (dis_dahil=False ise 2SD'yi aşmamış olmalı); durum YENİ başladığında giriş (aynı durum sürerken
tekrar sinyal yok). Short ayna (alt iki bant arası). Stop: orta bant (SMA) -/+ stop_tampon_atr*ATR (kanonik: orta bant).
Çıkış: kapanış orta bandı ters yönde keser (`cikis`, yön-bağımsız: orta bant kesişimi).
Kaynak kart: swing__bb-cift-bant-trend__johnson (tek kart, 1D). Kanonik kural kartla aynı.
Varsayımlar: kart giriş anını/çıkışı vermez -> "bölgeye ilk giriş" tetik, orta bant kırılımı çıkış; periyot 20.
dis_dahil=True: 2SD üstü kapanışlar da (güçlü momentum) geçerli sayılır. Hedef yok (NaN).
Negatif kanıt: aile kaydında yok; arşivde tek bant dönüşü (ortalamaya dönüş) başarısız, bu ise trend yönlü bir okuma.
Tek yazar.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class BollingerCiftBantTrend(Strateji):
    ad = "swing__bollinger-cift-bant-trend"
    stil = "swing"
    varsayilan_parametreler = {
        "periyot": 20, "ic_sapma": 1.0, "dis_sapma": 2.0, "dis_dahil": False,
        "stop_tampon_atr": 0.25, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "periyot": [14, 20, 30],
        "ic_sapma": [1.0, 1.5],
        "dis_sapma": [2.0, 2.5],
    }

    def cikis_var_mi(self) -> bool:
        return True   # orta bant ters kesişimi

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ic = g.bollinger(k, int(p["periyot"]), p["ic_sapma"])
        dis = g.bollinger(k, int(p["periyot"]), p["dis_sapma"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        ust_bolge = k > ic["ust"]
        alt_bolge = k < ic["alt"]
        if not p["dis_dahil"]:
            ust_bolge &= k <= dis["ust"]
            alt_bolge &= k >= dis["alt"]
        gecerli = atr.notna() & ic["orta"].notna()
        long_ok = b.gecis(ust_bolge & gecerli)
        short_ok = b.gecis(alt_bolge & gecerli) & bool(p["short"])
        tampon = p["stop_tampon_atr"] * atr
        cikis = (b.asagi_kesis(k, ic["orta"]) | b.yukari_kesis(k, ic["orta"])) & gecerli
        return cerceve(mumlar, long_ok, short_ok, ic["orta"] - tampon, ic["orta"] + tampon, cikis=cikis)
