"""swing__gap-doldurma: aşağı boşluk + yükseliş reddi -> boşluğu (önceki kapanış) doldurma yönünde giriş (4h/1d).

ZAYIF ANLAM UYARISI: Kripto 7/24'te geleneksel açılış boşluğu ~0'dır (bkz. swing__gap-devam docstring). VARSAYILAN `gap_olcum="ilk_bar"`
seansın ilk mumunun kapanışını referans alan vekildir; gerçek boşluk değildir (1d TF'de ilk mum = mumun kendisi, reddi mümkün değil: 4h TF önerilir). 1d TF'de "boşluk" ardışık kapanış-açılış farkıdır.
Kural (seans sonu mumunda karar): aşağı boşluk gap <= -min_gap_atr*ATR(seans ilk mumu); referans="aralik" ise ek olarak gap referansı
(açılış / ilk mum kapanışı) önceki seansın DÜŞÜĞÜNÜN altında (tam boşluk, Crane); boşluk dolmamış (kapanış < önceki kapanış); kapanış gap referansının üstünde
(reddi) ve günün üst `kapanis_yuzde` kısmında kapanır -> long. Yukarı boşluk aynası short. Stop = seans dibi (short: zirvesi)
-/+ tampon*ATR. Hedef = giriş + hedef_oran*(önceki kapanış - giriş) (1.0 = tam dolum, 0.5 = yarım); hedef mesafesi < min_rr*risk ise
işlem yok. Çıkış: hedef veya stop (gün sonu yok).
Kaynak kartlar: swing__gap-reversal__crane (1D; gün 1 yeni dip, gün 2 önceki dibin altında açılır ve açılışın üstünde kapanır ->
  long; referans="aralik"), swing__reversal-gap__landry (iki aylık zirve sonrası aşağı gap, SHORT = gap yönünde devam, tek bar
  düzeltme: gap-doldurma değil devam; KODLANMADI), swing__gap-and-go__crane (gün 1/gün 2 formasyonu, boşluk-devam; KODLANMADI).
  Kanonik özet "boşluk önceki kapanışa kapanma eğilimi" der; swing kartlarının hiçbiri doğrudan "dolum" kuralı değildir
  (çelişki): yalnız Crane gap-reversal kartı ters-yön (reddi) girişine benzer.
Varsayımlar: eşik ve kapanis_yuzde tarafımızdan; Crane'in buy-stop girişi yerine seans sonu kapanışı.
Negatif kanıt: yok; kripto için örneklem ve anlam zayıf.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, onceki_seans_hlc, seans_son_mumu
from motor.strateji.gostergeler_b1 import seans_gap
from motor.strateji.temel import Strateji


class GapDoldurma(Strateji):
    ad = "swing__gap-doldurma"
    stil = "swing"
    varsayilan_parametreler = {
        "gap_olcum": "ilk_bar", "min_gap_atr": 0.75, "referans": "kapanis", "kapanis_yuzde": 0.5,
        "stop_tampon_atr": 0.25, "hedef_oran": 1.0, "min_rr": 0.5,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "gap_olcum": ["acilis", "ilk_bar"],
        "min_gap_atr": [0.5, 0.75, 1.5],
        "referans": ["kapanis", "aralik"],
        "hedef_oran": [0.5, 1.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef = boşluk dolumu (kısmi/tam)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        sg = seans_gap(mumlar, atr, p["seans_saat"], p["gap_olcum"])
        seans = sg["seans"].to_numpy()
        hlc = onceki_seans_hlc(mumlar, seans)
        son = pd.Series(seans_son_mumu(mumlar.index, p["seans_saat"]), index=mumlar.index)
        s_dusuk = d.groupby(seans).cummin()
        s_yuksek = y.groupby(seans).cummax()
        aralik = (s_yuksek - s_dusuk).where(lambda x: x > 0)
        poz = (k - s_dusuk) / aralik
        esik = p["min_gap_atr"] * sg["atr0"]
        gecerli = son & esik.notna() & sg["gap"].notna() & atr.notna()
        long_ok = gecerli & (sg["gap"] <= -esik) & (k < sg["onc_kap"]) & (k > sg["ref"]) & (poz >= p["kapanis_yuzde"])
        short_ok = (gecerli & (sg["gap"] >= esik) & (k > sg["onc_kap"]) & (k < sg["ref"])
                    & ((1.0 - poz) >= p["kapanis_yuzde"]) & bool(p["short"]))
        if p["referans"] == "aralik":
            long_ok &= sg["ref"] < hlc["l"]
            short_ok &= sg["ref"] > hlc["h"]
        tampon = p["stop_tampon_atr"] * atr
        stop_l, stop_s = s_dusuk - tampon, s_yuksek + tampon
        h_l = k + p["hedef_oran"] * (sg["onc_kap"] - k)
        h_s = k - p["hedef_oran"] * (k - sg["onc_kap"])
        long_ok &= (h_l - k) >= p["min_rr"] * (k - stop_l)
        short_ok &= (k - h_s) >= p["min_rr"] * (stop_s - k)
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, gun_sonu=False)
