"""scalp__macd-sinyal: MACD sinyal çizgisi / sıfır çizgisi kesişimi veya histogram dönüşü (15m).

Çekirdek swing `MacdSinyal` ile aynıdır (türetildi): mod="sinyal" (MACD x sinyal), "sifir" (MACD x 0).
Scalp'e özgü ek mod "hist_donus" (Schroder): histogram sıfırın ALTINDA iken yukarı döner (h>h[-1], h[-1]<=h[-2]) -> long;
histogram sıfırın ÜSTÜNDE iken aşağı döner -> short. Çıkış: histogramın sıfır işaretini değiştirmesi (`cikis`).
Stop = kapanış -/+ atr_k*ATR (kartlar stop vermiyor; Ellis: giriş mumunun 1 pip ötesi -> burada ATR tabanlı).
Kaynak kartlar: scalp__macd-histogram-sifir-donusu__schroder (mod="hist_donus"),
  scalp__macd-histogram-stokastik__ellis (histogram + Yavaş Stokastik 20/80 dönüşü + 80/20 kısmi çıkış: KODLANMADI,
  Stokastik onayı ve iki parçalı çıkış sınıfta yok), scalp__tsi-bjorgum__carson (TSI çizgi kesişimi: KODLANMADI).
Varsayımlar: MACD 12/26/9 (kartlarda parametre yok; ailede alternatif 5/35/5 ızgarada yok); atr_k 1.5-3.
Negatif kanıt: yok; kısa TF'de kesişim sistemleri yatay piyasada çok sahte sinyal üretir, komisyon baskın.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.swing.macd_sinyal import MacdSinyal as _Swing


class MacdSinyal(_Swing):
    ad = "scalp__macd-sinyal"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "atr_k": 1.5}
    parametre_izgarasi = {
        "mod": ["sinyal", "sifir", "hist_donus"],
        "sinyal": [5, 9],
        "atr_k": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["mod"] != "hist_donus":
            return super().sinyaller(mumlar)
        kap = mumlar["kapanis"]
        h = g.macd(kap, p["hizli"], p["yavas"], p["sinyal"])["histogram"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, p["atr_periyot"])
        h1, h2 = h.shift(1), h.shift(2)
        gecerli = atr.notna() & h2.notna()
        long_ok = (h < 0) & (h > h1) & (h1 <= h2) & gecerli
        short_ok = (h > 0) & (h < h1) & (h1 >= h2) & gecerli & bool(p["short"])
        isaret = ((h > 0) & (h1 <= 0)) | ((h < 0) & (h1 >= 0))
        return sinyal_cercevesi(mumlar.index, long_ok, short_ok,
                                kap - p["atr_k"] * atr, kap + p["atr_k"] * atr, cikis=isaret & gecerli)
