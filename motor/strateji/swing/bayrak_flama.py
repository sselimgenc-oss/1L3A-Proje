"""swing__bayrak-flama — bayrak / flama (yüksek ve sıkı bayrak) kırılımı, trend yönünde.

Kural (çekirdek: formasyon_b3.bayrak_cekirdek, long biçimi; short aynada): bayrak = son F mum
  (F in bayrak_min..bayrak_maks; kart 5-20 mum), direk = bayraktan önceki `direk_n` mum. Direk aralığı >=
  direk_min_atr*ATR ve direk sonu kapanışı tepeye yakın (<= direk_yakin*aralık). Bayrak: tepesi direk tepesini
  (+%10 aralık) aşmaz, derinliği <= maks_derinlik*direk aralığı (kart: direğin %50'si), bayrak boyunca kapanış
  yukarı gitmez (karşı-trend/yatay sığ konsolidasyon). Tetik: kapanış > bayrak tepesi + tampon_atr*ATR
  (opsiyonel hacim_k: kırılım hacmi > hacim_k * bayrak ortalama hacmi). Stop: bayrak dibi - stop_tampon_atr*ATR.
  Hedef: giriş + hedef_olcu * direk aralığı (ölçü kuralı; Bulkowski/Penn/Heikin Ashi). Sinyaller `soguma` mum aralıklı.
  ust_tf doluysa (ör. "1d") üst TF kapanışı > EMA(ust_ema) şartı (htf.py ile, lookahead'siz).
Kaynak kartlar: yuksek-ve-sikli-bayrak__bulkowski (swing kaydındaki), bayrak-kirilim__heikinashi,
  bayrak-flama-kirilim__penn, bayrak-kirilim__graham.
Varsayımlar: "sıkı bayrak" niceliksel tanımı yok -> derinlik oranı; Heikin Ashi renk koşulları ve eğimli kanal çizgisi
  yerine yatay bayrak tepesi kullanıldı; flama (yakınsayan çizgiler) ayrı kodlanmadı, dar bayrak olarak yakalanır.
  Bulkowski'nin "direk iki kat" şartı kripto için fazla katı -> ATR çarpanı (direk_min_atr). Kart iz süren stopları
  (volatilite durağı) CikisAyarlari.atr_iz_suren_k ile motor tarafında seçilir. Kısmi kâr/2R (Graham) hedef_olcu ile.
Çelişkiler: Heikin Ashi kartı hedef vermez ve trend bitene kadar tutar; Graham 2R + kısmi; Bulkowski ölçü -> biz ölçü
  hedefi + motor iz süren stopu seçeneği.
Negatif kanıt: Bulkowski (2897 HTF, günlük hisse): bayrak dibi stoplu başarısızlık %33 (ort. %27 kayıp), tepe üstü
  kapanış sonrası %19 başarısızlık; boğada +%31 ort., ayı piyasasında +%22. Günlük hisse verisi, kripto/gün içi yok.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, bayrak_cekirdek


class BayrakFlama(FormasyonTaban):
    ad = "swing__bayrak-flama"
    stil = "swing"
    varsayilan_parametreler = {
        "direk_n": 15, "bayrak_min": 5, "bayrak_maks": 20, "direk_min_atr": 8.0, "direk_yakin": 0.3,
        "maks_derinlik": 0.5, "tampon_atr": 0.1, "stop_tampon_atr": 0.25, "hedef_olcu": 1.0,
        "hacim_k": 0.0, "soguma": 10, "ust_tf": "", "ust_ema": 20, "atr_periyot": 14, "min_rr": 1.0,
        "long": True, "short": True,
    }
    parametre_izgarasi = {
        "direk_min_atr": [5.0, 8.0, 11.0],
        "maks_derinlik": [0.382, 0.5, 0.618],
        "hedef_olcu": [0.5, 0.75, 1.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return bayrak_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        """Ölçü hedefi (hedef_olcu > 0)."""
        return self.parametreler["hedef_olcu"] > 0
