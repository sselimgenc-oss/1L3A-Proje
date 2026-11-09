"""daytrade__konsolidasyon-kirilim: dar konsolidasyon / blok kırılımı (hacim onaylı), gün sonunda kapanır.

Kural: swing__konsolidasyon-kirilim ile mekanik olarak aynı çekirdek (kartların ortak çekirdeği: önceki
`uzunluk` mumun kutusu, dar kutu = yükseklik <= maks_genislik_atr*ATR, kapanış kutu dışında + tampon,
hacim > hacim_k * kutu ortalama hacmi, opsiyonel EMA trend filtresi, stop = kutunun karşı ucu/orta,
hedef = kutu yüksekliği kadar ölçülen hareket). Bu sınıf swing sınıfından türer; day trade'e özgü olanlar:
  - varsayılanlar/ızgara (1h: uzunluk 12, hedef_olcu 1.5; trend_ema 50),
  - seansın son mumunda giriş yok ve cikis=True (gün sonu çıkışı), seans_saat parametresi.
Kaynak kartlar: daytrade__basinc-bolgesi__woods, swing__ogle-kanali-kirilim__scheier,
  swing__kirilim-oncesi-duraklama__scheier, swing__kopus-kirilim__graham (+ swing kartları).
Negatif kanıt (aile kaydı): Scheier — kırılımların çoğu başarısız olur, duraklama/retest filtresi gerekir;
  Bulkowski (kişisel) — destek kırılımı satışlarının %70'i zararla bitmiş. Retest burada kodlanmadı
  (bkz. daytrade__kirilim-geri-test). Woods'un "tıkanıklık bölgesi" kutusu (3 çubuk kapanış aralığı) ve
  Singhal 1dk "4-5 mumluk dar aralık" kutu uzunluğu ızgarasında (8-16) kabaca karşılanır.
Varsayımlar: dar-kutu eşiği tarafımızdan; kutu seans sınırını aşabilir (önceki günün mumları dahil).
"""
import pandas as pd

from motor.strateji.daytrade._ortak import gun_sonu_uygula
from motor.strateji.swing.konsolidasyon_kirilim import KonsolidasyonKirilim as _Swing


class KonsolidasyonKirilim(_Swing):
    ad = "daytrade__konsolidasyon-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "uzunluk": 12, "maks_genislik_atr": 4.0, "hedef_olcu": 1.5,
                               "trend_ema": 50, "seans_saat": 0.0}
    parametre_izgarasi = {
        "uzunluk": [8, 12, 16],
        "hacim_k": [0.0, 1.5, 2.0],
        "tampon_atr": [0.0, 0.25, 0.5],
    }

    def cikis_var_mi(self) -> bool:
        return True   # gün sonu + hedef

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])
