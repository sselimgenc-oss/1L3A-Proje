"""swing__pin-bar — seviyede pin bar (çekiç / yusufçuk doji / ters çekiç) dönüşü.

Kural (çekirdek: formasyon_b3.pin_cekirdek, boğa pin = long; ayı pin aynada short):
  Boğa pin bar: alt fitil >= fitil_oran * max(gövde, 0.1*aralık) ve >= %50 aralık, kapanış mumun üst
  (1-kapanis_alt) diliminde (üst fitil küçük), mum aralığı [min_aralik_atr, maks_aralik_atr] * ATR. Seviye: pin düşüğü
  önceki `aralik_n` mumun en düşüğüne <= tol_atr*ATR yakın/altında ("destek / aralık dibi"). Opsiyonel trend_ema
  (kapanış > EMA) ve ust_tf filtresi. Giriş: teyit_n=0 -> pin kapanışında; teyit_n=k>0 -> pin'den sonra k mum içinde
  kapanış pin tepesini aşarsa ("mum zirvesinin üstünde gir"; pin düşüğü kırılmadan). Stop: pin düşüğü - tampon_atr*ATR
  ("fitil ucunun ötesi"; risk > maks_risk_atr*ATR ise işlem yok). Hedef: hedef_r>0 -> R katı (kart 2R); hedef_r=0 ->
  aralığın karşı ucu (aralik_n mumun tepesi).
Kaynak kartlar: cekic-asili-adam__hogan, cimbiz-dip-tepe__hogan, yusufcuk-doji__graham, pin-bar-devam__day.
Varsayımlar: fitil/gövde >= 2-3 (kart optimize aralığı); çımbız (iki mumlu) ve asılı adam/kayan yıldız tek mumlu pin
  bar ailesi olarak birleşti, çımbız ayrı kodlanmadı. Graham'ın stop'u (fitilin %50'si) yerine fitil ucu. Giriş stop
  emri yerine kapanış/teyit mumu kapanışı (motor sonraki açılışta girer).
Çelişkiler: Day (pin-bar-devam) pin bar'ı TREND YÖNÜNDE, trend sonunda dönüşe karşı uyarır; Hogan/Graham dönüş
  desenidir; Singhal aralık dibinde dönüş. Varsayılan: aralık dibi dönüşü; trend yönü için trend_ema>0 verilir.
Negatif kanıt: kartlarda istatistik/kazanma oranı yok. arsiv/OZET.md §3: "Brooks H1/H2 geri çekilme, EPA-A mum"
  (mum tabanlı fiyat eylemi) başarısız; tek mumlu desenlerin ham kenarı genelde maliyete yetmez.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, pin_cekirdek


class PinBar(FormasyonTaban):
    ad = "swing__pin-bar"
    stil = "swing"
    varsayilan_parametreler = {
        "fitil_oran": 2.0, "kapanis_alt": 0.33, "min_aralik_atr": 0.8, "maks_aralik_atr": 3.5,
        "seviye_modu": "aralik", "aralik_n": 40, "tol_atr": 0.3, "trend_ema": 0, "ust_tf": "", "ust_ema": 20,
        "teyit_n": 0, "tampon_atr": 0.1, "maks_risk_atr": 4.0, "hedef_r": 2.0, "min_rr": 1.0,
        "atr_periyot": 14, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "fitil_oran": [2.0, 2.5, 3.0],
        "aralik_n": [20, 40, 60],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return pin_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        """R hedefi veya aralık karşı ucu hedefi her zaman var."""
        return True
