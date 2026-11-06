"""daytrade__gap-devam: seans açılış boşluğu (ATR eşiği) sonrası erken konsolidasyon kırılımı, boşluk yönünde devam; gün sonunda kapanır (1h).

ZAYIF ANLAM UYARISI: Kripto 7/24 işlem görür; mumun açılışı önceki kapanışa ~eşit olduğundan geleneksel "açılış boşluğu"
(gap_olcum="acilis") kriptoda ~0'dır ve eşiği nadiren aşar. `gap_olcum="ilk_bar"`: boşluk = seansın (UTC gün) ilk mumunun
KAPANIŞI - önceki seans kapanışı (ilk mum hareketi; gerçek boşluk değil, vekil). Kart iddiaları (%4-5 boşluk, 5-10$ hisse,
20-30. dakika konsolidasyonu) hisse içindir; bu veriyle denenmemiştir.
Kural: gap >= min_gap_atr*ATR(seans ilk mumu) (yukarı) ve boşluk korunuyor (seans düşüğü > önceki kapanış). Konsolidasyon =
seansın ilk `konsol_n` mumu (kutu: en yüksek/en düşük). Seansın `konsol_n+1 .. konsol_n+pencere` mumları içinde kapanış kutu
zirvesini (short: dibini) aşarsa (seans başına tek, ilk) boşluk yönünde giriş; hacim > hacim_k*20 mum ort. (0: kapalı).
Stop = kutu dibi (short: zirvesi) -/+ stop_tampon_atr*ATR (kart: konsolidasyon dibi). Hedef = hedef_r*R (kart 2R). Çıkış: hedef/stop ve
UTC gün sonu zorunlu `cikis` (seansın son mumunda giriş yok).
Kaynak kartlar: daytrade__bosluk-takoz-hacim-kirilim__boxer (1m; %4-5 yukarı boşluk, ilk 20-30 dk düşük hacimli takoz,
  hacimli kırılım; stop konsolidasyon dibi; seans sonunda kapat), swing__bosluk-yukari-asagi__graham (açılış önceki günün aralığı
  dışında: yukarı boşlukta al).
Varsayımlar: 1m kartı 1h'e taşındı (konsol_n=1-2 mum ~ 1-2 saat); "düşük hacimli geri çekilme" şartı yok; "ilk 15 dk işlem yok"
  için ilk mum zaten kutunun parçası; short ayna (kart yalnız long).
Negatif kanıt: yok; kripto için anlam ve örneklem zayıf.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import seans_gap
from motor.strateji.temel import Strateji


class GapDevam(Strateji):
    ad = "daytrade__gap-devam"
    stil = "daytrade"
    varsayilan_parametreler = {
        "gap_olcum": "ilk_bar", "min_gap_atr": 1.5, "konsol_n": 2, "pencere": 8, "hacim_k": 0.0,
        "stop_tampon_atr": 0.25, "hedef_r": 2.0, "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "gap_olcum": ["acilis", "ilk_bar"],
        "min_gap_atr": [1.0, 1.5, 2.5],
        "konsol_n": [1, 2, 3],
    }

    def cikis_var_mi(self) -> bool:
        return True   # gün sonu + hedef

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        sg = seans_gap(mumlar, atr, p["seans_saat"], p["gap_olcum"])
        seans = sg["seans"].to_numpy()
        N = int(p["konsol_n"])
        maske = sg["mum_no"] <= N
        kutu_ust = y.where(maske).groupby(seans).transform("max")     # yalnız mum_no > N satırlarında kullanılır
        kutu_alt = d.where(maske).groupby(seans).transform("min")
        pencere = (sg["mum_no"] > N) & (sg["mum_no"] <= N + int(p["pencere"]))
        esik = p["min_gap_atr"] * sg["atr0"]
        gecerli = pencere & esik.notna() & sg["gap"].notna() & atr.notna()
        l_ham = gecerli & (sg["gap"] >= esik) & (sg["dusuk_kor"] > sg["onc_kap"]) & (k > kutu_ust)
        s_ham = gecerli & (sg["gap"] <= -esik) & (sg["yuksek_kor"] < sg["onc_kap"]) & (k < kutu_alt)
        if p["hacim_k"] > 0:
            ok = mumlar["hacim"] > p["hacim_k"] * mumlar["hacim"].shift(1).rolling(20, min_periods=20).mean()
            l_ham &= ok
            s_ham &= ok
        # seans başına ilk tetik (kırılım mumu); ilk kırılımda hacim/koşul sağlanmazsa o seansta sonraki mum geçerli olabilir
        l_ok = l_ham & (l_ham.astype(int).groupby(seans).cumsum() == 1)
        s_ok = s_ham & (s_ham.astype(int).groupby(seans).cumsum() == 1) & bool(p["short"])
        tampon = p["stop_tampon_atr"] * atr
        stop_l, stop_s = kutu_alt - tampon, kutu_ust + tampon
        h_l = k + p["hedef_r"] * (k - stop_l)
        h_s = k - p["hedef_r"] * (stop_s - k)
        return cerceve(mumlar, l_ok, s_ok, stop_l, stop_s, h_l, h_s, gun_sonu=True, seans_saat=p["seans_saat"])
