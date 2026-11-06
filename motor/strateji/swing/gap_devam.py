"""swing__gap-devam: seans açılış boşluğu ATR eşiğini aşar, boşluk dolmaz ve seans boşluk yönünde kapanırsa devam girişi (4h/1d).

ZAYIF ANLAM UYARISI: Kripto 7/24 işlem görür; bir mumun açılışı önceki mumun kapanışına ~eşittir, bu yüzden geleneksel
"açılış boşluğu" (olcum="acilis", seans açılışı - önceki seans kapanışı) kriptoda ~0'dır ve eşiği nadiren aşar. 1d mumda
bile fark yalnızca ardışık mumların kapanış-açılış sapmasıdır (fiyat sıçraması değil). VARSAYILAN gap_olcum="ilk_bar":
seansın ilk mumunun kapanışı referans alınır (= ilk mumun hareketi, "açılış sürüşü"; 1d TF'de günlük getiri); bu gerçek bir
boşluk değil, anlamı boşluğa benzer bir vekildir. "acilis" kartlara sadık ama kriptoda ~hiç tetiklenmez. TradFi (hisse) perpetual'larda hafta sonu/gece kapanışı olabilir; yine de kart iddiaları bu veriyle denenmemiştir.
Kural (seans sonu mumunda karar; 1d TF'de her mum bir seanstır): gap = ref - önceki seans kapanışı; gap >= min_gap_atr*ATR(seans
ilk mumu) ise yukarı boşluk. Boşluk korunmuş (gap_korunur: seans düşüğü > önceki kapanış), seans açılışın üstünde kapanır
(kapanış > açılış) ve kapanış günün aralığının üst `kapanis_yuzde` kısmında (Jordan: gün zirvesine yakın) -> long. Aşağı boşluk
aynası short. Stop: stop_modu "dip" -> seans düşüğü (short: zirve) -/+ tampon*ATR; "gap" -> önceki seans kapanışı (boşluk dolum
seviyesi) -/+ tampon*ATR. Risk > max_risk_atr*ATR ise işlem yok. Hedef: hedef_r*R. Çıkış: hedef veya stop (gün sonu YOK).
Kaynak kartlar: swing__gapping-pattern__crane (1D; trend yönünde breakaway gap kapanmaz, kapanış açılışın üstünde, 2-3 gün
  devam), swing__bosluk-devam-zirve-yakin__jordan (boşluk günü zirveye yakın kapanış -> ertesi gün devam),
  swing__bosluk-yukari-asagi__graham (yukarı boşluk al, aşağı sat; tetik/stop yok), swing__explosion-gap-pivots__landry
  (20 günlük yeni zirveye gap + gap alanı testi + daha yüksek pivot dip: pivot-test deseni KODLANMADI).
Kodlanmayan: Crane'in "RD/trail day" ön koşulu, Landry'nin 20 günlük zirve ve pivot testi; kısmi çıkış/iz süren stop (CikisAyarlari).
Varsayımlar: eşik ve kapanis_yuzde tarafımızdan; "2-3 gün devam" hedef_r ile yaklaşık (zaman çıkışı CikisAyarlari.zaman_cikisi_mum).
Negatif kanıt: yok; ancak kripto için örneklem ve anlam zayıf.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_son_mumu
from motor.strateji.gostergeler_b1 import seans_gap
from motor.strateji.temel import Strateji


class GapDevam(Strateji):
    ad = "swing__gap-devam"
    stil = "swing"
    varsayilan_parametreler = {
        "gap_olcum": "ilk_bar", "min_gap_atr": 1.0, "gap_korunur": True, "kapanis_yuzde": 0.67,
        "stop_modu": "dip", "stop_tampon_atr": 0.25, "max_risk_atr": 6.0, "hedef_r": 2.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "gap_olcum": ["acilis", "ilk_bar"],
        "min_gap_atr": [0.5, 1.0, 2.0],
        "stop_modu": ["dip", "gap"],
        "hedef_r": [2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        sg = seans_gap(mumlar, atr, p["seans_saat"], p["gap_olcum"])
        seans = sg["seans"].to_numpy()
        son = pd.Series(seans_son_mumu(mumlar.index, p["seans_saat"]), index=mumlar.index)
        s_dusuk = d.groupby(seans).cummin()
        s_yuksek = y.groupby(seans).cummax()
        aralik = (s_yuksek - s_dusuk).where(lambda x: x > 0)
        poz = (k - s_dusuk) / aralik                      # 1: günün zirvesinde kapanış
        esik = p["min_gap_atr"] * sg["atr0"]
        gecerli = son & esik.notna() & sg["gap"].notna() & atr.notna()
        yukari = gecerli & (sg["gap"] >= esik) & (k > sg["acilis"]) & (poz >= p["kapanis_yuzde"])
        asagi = gecerli & (sg["gap"] <= -esik) & (k < sg["acilis"]) & ((1.0 - poz) >= p["kapanis_yuzde"])
        if p["gap_korunur"]:
            yukari &= sg["dusuk_kor"] > sg["onc_kap"]
            asagi &= sg["yuksek_kor"] < sg["onc_kap"]
        tampon = p["stop_tampon_atr"] * atr
        if p["stop_modu"] == "dip":
            stop_l, stop_s = s_dusuk - tampon, s_yuksek + tampon
        else:
            stop_l, stop_s = sg["onc_kap"] - tampon, sg["onc_kap"] + tampon
        yukari &= (k - stop_l) <= p["max_risk_atr"] * atr
        asagi &= (stop_s - k) <= p["max_risk_atr"] * atr
        h_l = k + p["hedef_r"] * (k - stop_l)
        h_s = k - p["hedef_r"] * (stop_s - k)
        return cerceve(mumlar, yukari, asagi & bool(p["short"]), stop_l, stop_s, h_l, h_s, gun_sonu=False)
