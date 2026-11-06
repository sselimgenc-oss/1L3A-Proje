"""daytrade__ma-geri-cekilme: trendde 10/20/50 MA'ya geri çekilme + sıçrama mumu; gün sonunda kapanır (1h).

Çekirdek swing `MaGeriCekilme` ile aynıdır (türetildi): son `geri_n` mumda dip MA'ya değdi (+temas_atr*ATR),
sıçrama mumu kapanış>açılış, >MA, >önceki zirve; trend: kapanış > SMA(trend_ma) ve MA > SMA(trend_ma);
stop geri çekilme dibi - tampon*ATR; hedef hedef_r*R (0: yok); çıkış: kapanış MA'yı karşıya keser. Short ayna.
Day trade'e özgü: 1h varsayılanları (trend_ma 100, geri_n 4, hedef_r 2) ve UTC gün sonu zorunlu çıkışı.
Kaynak kart (tek): swing__sloth-psar-ema-roc__kratter (M30; EMA21/55/144 + PSAR + Stokastik + ROC(13) bileşik
  kurulum) — çok göstergeli, KODLANMADI; sınıf yalnız "trendde MA'ya geri çekilme + sıçrama" çekirdeğini verir.
Aile çekirdeği 7+ swing kartından (ladha, sharpe, penn, make, velez, graham, kratter) gelir, day trade kartı ise tek.
Varsayımlar: kanonik taslak (10/20/50 MA, sıçrama mumu, 2R-3R) esas alındı; hacim ve ADX>=30 filtresi kapalı.
Negatif kanıt: arşiv (arsiv/OZET.md §3): kısa TF (1S) geri çekilme ve `daytrade__ma-geri-cekilme` başarısız listesinde.
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.ma_geri_cekilme import MaGeriCekilme as _Swing


class MaGeriCekilme(GunSonu, _Swing):
    ad = "daytrade__ma-geri-cekilme"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "trend_ma": 100, "geri_n": 4, "hedef_r": 2.0,
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "ma_periyot": [10, 20, 50],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
        "hedef_r": [0.0, 2.0, 3.0],
    }
