"""daytrade__bayrak-flama — bayrak / flama kırılımı (1h), UTC gün sonu zorunlu çıkış.

Çekirdek swing `BayrakFlama` (swing/bayrak_flama.py; formasyon_b3.bayrak_cekirdek) ile aynıdır, ondan türer. Farklar:
direk_n=8, direk_min_atr=5 (gün içi direk daha kısa), ust_tf="4h" (kart: üst filtre 4h/1G; htf.py ile EMA20 trend
uyumu), hedef_olcu=0.75; sinyal çerçevesine daytrade/_ortak.gun_sonu_uygula uygulanır (seansın son mumunda giriş yok,
cikis=True). Kural/stop/hedef için bkz. swing/bayrak_flama.py.
Kaynak kartlar: bayrak-kirilim-retest__kratter (M30 bayrak, H4 dürtü yönü, kırılım mumu kapanışı).
Varsayımlar: Kratter retest girişi (kırılan çizgiyi yeniden test) kodlanmadı, doğrudan kırılım kapanışı kullanıldı;
  kitap yalnız short örneği verir, long ayna varsayımı. Eğimli alt trend çizgisi yerine yatay bayrak dibi; M30 yerine 1h.
  Kart iz süren stopu manuel -> motor iz süren stop seçeneği.
Çelişkiler: Kratter hedef vermiyor; ölçü hedefi (Bulkowski) alındı. Retest yoksa "gövdesi tamamen dışarıda" girişi
  doğrudan kırılımla yaklaşıldı.
Negatif kanıt: aileyi destekleyen tek gün içi kart; Bulkowski verisi GÜNLÜK hisse (başarısızlık %33 / ort. %27 kayıp);
  gün içi doğrulama yok. arsiv/OZET.md §3: kısa TF kırılımları (1S Donchian) maliyet sonrası başarısız.
"""
import pandas as pd

from motor.strateji.daytrade._ortak import gun_sonu_uygula
from motor.strateji.swing.bayrak_flama import BayrakFlama as _Swing


class BayrakFlama(_Swing):
    ad = "daytrade__bayrak-flama"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "direk_n": 8, "direk_min_atr": 5.0, "ust_tf": "4h", "hedef_olcu": 0.75,
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "direk_min_atr": [4.0, 5.0, 7.0],
        "maks_derinlik": [0.382, 0.5, 0.618],
        "hedef_olcu": [0.5, 0.75, 1.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])
