"""swing__goreceli-guc-momentum: güçlü momentumlu varlıkta kısa EMA'ya geri çekilmede trend yönünde giriş.

UYARLAMA (önemli): kartlar "birçok varlık arasından en güçlüyü seç" (endeks/S&P'ye göre göreceli güç) mantığındadır. 1L3A tek
sembol/az enstrüman çalıştığı için bu burada SEMBOLÜN KENDİ GEÇMİŞİNE GÖRE zaman serisi momentumu olarak uyarlandı:
  mom_mod="esik": ROC(mom_n) >= mom_esik (kart: 30g>%20, 90g>%30, 180g>%50 türü mutlak eşik) ;
  mom_mod="sira": ROC(mom_n)'nin son `rank_pencere` mumdaki yüzdelik sırası >= sira_esik (sembolün kendi geçmişine göre "güçlü dönem").
Her iki modda ek koşul: kapanış >= yakinlik * (son zirve_n mumun en yükseği) (kart: 52 hafta zirvesine yakın; 1d'de 252) ve ROC > 0.
Giriş (long): geri çekilme -> son geri_n mumun dibi EMA(ema_periyot)'a değdi/altına indi, kapanış EMA üstünde ve yükseliş mumu
(kapanış>açılış) (kart: 10/20 EMA geri çekilmesi; düşük hacim şartı kodlanmadı). Durum yeni oluşunca bir kez sinyal.
Short ayna (ROC <= -mom_esik, zirve_n dibine yakın, EMA'ya yükselip reddedilme) — kartta "zayıf varlıkta ayna, ortak değil",
bu yüzden short varsayılan KAPALI (short=False).
Stop: son stop_n mumun dibi -/+ stop_tampon_atr*ATR (kart: giriş gününün dibinin %0.5 altı; günlükte kriptoda %0.5 çok dar -> ATR tamponu),
risk <= stop_max_atr ATR. Çıkış: kapanış EMA'nın altına iner (kart: "kalanı EMA altı kapanışta"). zaman_mum>0: o kadar mum sonra
zorunlu zaman çıkışı (kart "2.5-5 gün"; varsayılan kapalı, yarım pozisyon çıkışı kodlanamaz).
Kaynak kartlar: swing__goreceli-guc__ladha, scalp__piyasa-lideri-tarama-geri-cekilme__schroder (SMA 20/50/100/200 üstü + 52h zirve),
daytrade__goreceli-guc-donus-kirilim__bulkowski (RS = hisse/S&P oranı dönüşü, formasyon kırılımı bağlamı; KODLANMADI).
Kodlanmadı: endeks trend filtresi (BTC/endeks 50g ortalama üstü; tek sembolde kendi EMA'sı yerine geçmez), hacim/ciro filtreleri, sektör liderliği.
Negatif kanıt: aile kaydında yok; arşivde tek kurallı trend sistemleri ve HGT başarısız (arsiv/OZET.md §3). Kartlardaki piyasa hisse (Hindistan/ABD).
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class GoreceliGucMomentum(Strateji):
    ad = "swing__goreceli-guc-momentum"
    stil = "swing"
    varsayilan_parametreler = {
        "mom_mod": "sira", "mom_n": 90, "mom_esik": 0.30, "rank_pencere": 365, "sira_esik": 0.8,
        "zirve_n": 252, "yakinlik": 0.9, "ema_periyot": 20, "geri_n": 3,
        "stop_n": 5, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "zaman_mum": 0, "hedef_r": 0.0,
        "atr_periyot": 14, "short": False,
    }
    parametre_izgarasi = {
        "mom_mod": ["esik", "sira"],
        "mom_n": [60, 90, 180],
        "ema_periyot": [10, 20],
        "yakinlik": [0.85, 0.95],
    }

    def cikis_var_mi(self) -> bool:
        return True   # kapanış EMA'nın ters tarafına geçince

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        ema = g.ema(k, int(p["ema_periyot"]))
        roc = k / k.shift(int(p["mom_n"])) - 1.0
        zirve = y.rolling(int(p["zirve_n"]), min_periods=int(p["zirve_n"])).max()
        dip = d.rolling(int(p["zirve_n"]), min_periods=int(p["zirve_n"])).min()
        if p["mom_mod"] == "esik":
            guclu, zayif = roc >= p["mom_esik"], roc <= -p["mom_esik"]
        elif p["mom_mod"] == "sira":
            sira = b.yuzdelik_sira(roc, int(p["rank_pencere"]))
            guclu = (sira >= p["sira_esik"]) & (roc > 0)
            zayif = (sira <= 1.0 - p["sira_esik"]) & (roc < 0)
        else:
            raise ValueError(f"Bilinmeyen mom_mod: {p['mom_mod']}")
        n = int(p["geri_n"])
        geri_l = (d.rolling(n, min_periods=1).min() <= ema) & (k > ema) & (k > a)
        geri_s = (y.rolling(n, min_periods=1).max() >= ema) & (k < ema) & (k < a)
        durum_l = guclu & (k >= p["yakinlik"] * zirve) & geri_l
        durum_s = zayif & (k <= dip * (2.0 - p["yakinlik"])) & geri_s
        gecerli = atr.notna() & ema.notna() & zirve.notna() & roc.notna()
        long_ok = b.gecis(durum_l & gecerli)
        short_ok = b.gecis(durum_s & gecerli) & bool(p["short"])
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        cikis = (b.asagi_kesis(k, ema) | b.yukari_kesis(k, ema)) & gecerli
        sig = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
        if p["zaman_mum"]:
            sig["zaman_cikisi_mum"] = pd.Series(float(p["zaman_mum"]), index=sig.index).where(sig["yon"] != 0)
        return sig
