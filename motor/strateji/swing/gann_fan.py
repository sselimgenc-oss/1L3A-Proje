"""swing__gann-fan — Gann fan çizgisinden destek/direnç dönüşü.

Kural (çekirdek: formasyon_b3.gann_cekirdek, long = destek; short aynada direnç): fan başlangıcı son ONAYLI dip pivot
  (zigzag, zigzag_esik_k; short'ta tepe). 1x1 çizgisinin eğimi u = olcek_atr * ATR(pivot onay anı) fiyat/mum; diğer
  çizgiler u*oran (1x4=0.25, 1x3, 1x2=0.5, 1x1, 2x1=2 ...). Dipten sonra onaylı tepe olmalı (yükseliş bacağı), fan yaşı
  [min_yas, maks_yas] mum. Giriş (`cizgi_orani` çizgisi): kapanış çizginin üstünde, düşük çizgiye <= tol_atr*ATR yaklaşmış,
  boğa mumu ve önceki kapanış çizginin üstünde (çizgiden dönüş). Stop: min(çizgi, düşük) - stop_tampon_atr*ATR ("çizgi
  ihlali"). Hedef: bir üstteki Gann çizgisinin `hedef_ufuk` mum sonraki değeri (kart: "bir sonraki Gann seviyesi"); eğim dik olduğunda hedef en çok maks_hedef_r*R ile sınırlanır.
Kaynak kartlar: gann-fan__crane (swing), gann-fan-lineer-regresyon__singhal (Bollinger/linreg onayı kodlanmadı).
Varsayımlar: kartlar fan ölçeğini (fiyat/zaman birimi), başlangıç seçimini ve hangi çizgide dönüş/kırılım beklendiğini
  TANIMLAMIYOR -> ölçek ATR tabanlı, başlangıç zigzag dibi, çizgi parametre; Crane'in "dar aralıklı gün" ve al/sat
  penceresi (tarih/açı) teyitleri yok; Singhal'ın Bollinger çakışması ve lineer regresyon filtresi yok.
Çelişkiler: Singhal örneği 1x2 direncinden short açıyor ama kural "destek alınca AL" diyor; Crane 1x4 kırılımı alış
  sinyali sayıyor. Çizgi oranı parametreyle seçilir (0.5 / 1 / 2).
Negatif kanıt: kodlanabilirlik 1/3; kitap "kesin kural değil" diyor; kazanma oranı/istatistik yok (tek örnek 1:3).
  Öznel çizgi ölçeği nedeniyle aşırı uyum riski yüksek.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, gann_cekirdek


class GannFan(FormasyonTaban):
    ad = "swing__gann-fan"
    stil = "swing"
    varsayilan_parametreler = {
        "zigzag_esik_k": 3.0, "atr_periyot": 14, "olcek_atr": 0.2, "cizgi_orani": 1.0, "tol_atr": 0.3,
        "min_yas": 5, "maks_yas": 200, "stop_tampon_atr": 0.5, "hedef_ufuk": 10, "maks_hedef_r": 4.0, "soguma": 3, "min_rr": 1.0,
        "long": True, "short": True,
    }
    parametre_izgarasi = {
        "cizgi_orani": [0.5, 1.0, 2.0],
        "olcek_atr": [0.1, 0.2, 0.4],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return gann_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        """Sonraki Gann çizgisi hedefi her zaman üretilir."""
        return True
