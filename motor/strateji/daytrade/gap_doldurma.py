"""daytrade__gap-doldurma: seans açılış boşluğu (ATR eşiği) sonrası erken ters dönüş, boşluğu (önceki kapanış) doldurma yönünde giriş; gün sonunda kapanır (1h).

ZAYIF ANLAM UYARISI: Kripto 7/24'te geleneksel açılış boşluğu ~0'dır (gap_olcum="acilis" nadiren tetikler). "ilk_bar" seansın
(UTC gün) ilk mumunun KAPANIŞI - önceki seans kapanışıdır (ilk mum hareketi; gerçek boşluk değil, vekil). Bulkowski'nin %3 boşluk /
hisse / 1m verisi bu veriyle denenmemiştir.
Kural (aşağı boşluk -> long): gap <= -min_gap_atr*ATR(seans ilk mumu); seansın `bekle_n+1 .. bekle_n+pencere` mumları içinde kapanış
seansta o ana kadarki en yükseği (önceki mumlar) aşar ve yükseliş mumudur (kapanış>açılış), boşluk henüz dolmamıştır (seans
zirvesi < önceki kapanış, kapanış < önceki kapanış) ve (sma_gun>0 ise) kapanış < GÜNLÜK SMA(sma_gun) (üst TF, htf.ust_zaman ile
lookahead'siz) -> long; seans başına ilk tetik. Yukarı boşluk aynası short (kapanış > günlük SMA). Stop = seans dibi (short: zirvesi) -/+
stop_tampon_atr*ATR. Hedef = giriş + hedef_oran*(önceki kapanış - giriş) (1.0 tam dolum; kart: %33/50/67 popüler çıkışlar).
Çıkış: hedef/stop ve UTC gün sonu zorunlu `cikis` (kart: ertesi güne taşımak hata).
Kaynak kartlar: daytrade__acilis-bosluk-geri-donus__bulkowski (1m giriş; %3+ aşağı boşluk, fiyat günlük SMA50 altında, açılış
  mumunun zirvesi üstü iz süren alım stopu, stop açılış dibi altı, gün sonu çıkış), swing__bosluk-kapanisi-y-kapanis__scheier
  (boşluk kapanış seviyesinde reddedilirse BOŞLUK YÖNÜNDE giriş: dolumun tersi -> ÇELİŞKİ, kodlanmadı).
Çelişki: Bulkowski dolum yönünde (ters), Scheier boşluk yönünde (devam) işlem önerir. Burada Bulkowski kodlandı; Scheier mantığı için bkz. gap-devam.
Varsayımlar: kartta short için SMA şartı "altında (test kuralı)" belirsiz; ayna (SMA üstünde) kullanıldı; "1 kuruş" tamponları ATR tamponuna çevrildi.
Negatif kanıt: yok; kripto için anlam ve örneklem zayıf.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import gunluk_sma, seans_gap
from motor.strateji.temel import Strateji


class GapDoldurma(Strateji):
    ad = "daytrade__gap-doldurma"
    stil = "daytrade"
    varsayilan_parametreler = {
        "gap_olcum": "ilk_bar", "min_gap_atr": 1.5, "bekle_n": 1, "pencere": 8, "sma_gun": 50,
        "stop_tampon_atr": 0.25, "hedef_oran": 1.0, "min_rr": 1.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "gap_olcum": ["acilis", "ilk_bar"],
        "min_gap_atr": [1.0, 2.0],
        "bekle_n": [1, 2, 4],
        "hedef_oran": [0.5, 1.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # gün sonu + hedef

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        sg = seans_gap(mumlar, atr, p["seans_saat"], p["gap_olcum"])
        seans = sg["seans"].to_numpy()
        B = int(p["bekle_n"])
        pencere = (sg["mum_no"] > B) & (sg["mum_no"] <= B + int(p["pencere"]))
        esik = p["min_gap_atr"] * sg["atr0"]
        cmax = y.groupby(seans).cummax()
        cmin = d.groupby(seans).cummin()
        # bu muma kadarki (mum hariç) seans en yüksek/en düşüğü; ilk_bar modunda ilk mum hariç, gap referansı taban
        onceki_max = np.maximum(sg["yuksek_kor"].groupby(seans).shift(1).fillna(-np.inf), sg["ref"])
        onceki_min = np.minimum(sg["dusuk_kor"].groupby(seans).shift(1).fillna(np.inf), sg["ref"])
        gecerli = pencere & esik.notna() & sg["gap"].notna() & atr.notna()
        l_ham = (gecerli & (sg["gap"] <= -esik) & (sg["yuksek_kor"] < sg["onc_kap"]) & (k < sg["onc_kap"])
                 & (k > onceki_max) & (k > a))
        s_ham = (gecerli & (sg["gap"] >= esik) & (sg["dusuk_kor"] > sg["onc_kap"]) & (k > sg["onc_kap"])
                 & (k < onceki_min) & (k < a))
        if p["sma_gun"]:
            sma = gunluk_sma(mumlar, int(p["sma_gun"]))
            l_ham &= k < sma
            s_ham &= k > sma
        l_ok = l_ham & (l_ham.astype(int).groupby(seans).cumsum() == 1)
        s_ok = s_ham & (s_ham.astype(int).groupby(seans).cumsum() == 1) & bool(p["short"])
        tampon = p["stop_tampon_atr"] * atr
        stop_l, stop_s = cmin - tampon, cmax + tampon
        h_l = k + p["hedef_oran"] * (sg["onc_kap"] - k)
        h_s = k - p["hedef_oran"] * (k - sg["onc_kap"])
        l_ok &= (h_l - k) >= p["min_rr"] * (k - stop_l)
        s_ok &= (k - h_s) >= p["min_rr"] * (stop_s - k)
        return cerceve(mumlar, l_ok, s_ok, stop_l, stop_s, h_l, h_s, gun_sonu=True, seans_saat=p["seans_saat"])
