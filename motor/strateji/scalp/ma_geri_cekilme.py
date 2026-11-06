"""scalp__ma-geri-cekilme: trendde 10/20/50 MA'ya geri çekilme + sıçrama mumu (15m).

Çekirdek swing `MaGeriCekilme` (swing/ma_geri_cekilme.py) ile aynıdır; bu sınıf ondan türer, yalnız scalp
varsayılanları/ızgarası/çıkışı değişir: hedef_r=2.0 (kartlar: 2R-3R), stop tamponu 0.5-1.5 ATR, trend filtresi
SMA(100) (15m'de 200 mum ~ 2 gün; kart EMA200 -> ızgarasız), ma_periyot 10/20/50.
Kural (parent): son `geri_n` mumda dip MA'ya değdi (+temas_atr*ATR), sıçrama mumu: kapanış>açılış, >MA, >önceki
zirve; trend: kapanış > SMA(trend_ma) ve MA > SMA(trend_ma). Short ayna. Stop = geri çekilme dibi - tampon*ATR;
hedef = hedef_r*R; çıkış: kapanış MA'yı karşıya keser.
Kaynak kartlar: scalp__ema200-psar-macd-bb__candle, scalp__ema10-21-orta-nokta-geri-cekilme__eseckal,
  swing__son-sans-texaco-ema200__scheier, swing__ema-cup__scheier, swing__mini-pup__yu, swing__mukemmel-firtina__yu.
PİP -> ATR: eseckal "5 pip stop / 10 pip hedef" (EURUSD 5m; ATR(14) ~ 6-7 pip varsayımı) ~ 0.75 ATR stop /
  1.5 ATR hedef = 2R; burada stop = geri çekilme dibi + tampon (tipik 1-2 ATR), hedef 2R. EMA50 eğimi
  ve EMA10-21 orta nokta teması kodlanmadı (MA bölgesi teması yeterli sayıldı); seans filtresi (Londra/NY) yok.
  Candle (EMA200+PSAR+MACD+BB) çok indikatörlü, kodlanmadı.
Kanıt: şüpheli %83 / %75 kazanma iddiaları (Candle, Yu), örneklem küçük. Arşiv negatif kanıtı: 5 dk geri
  çekilme/dönüş ve Brooks H1/H2 denemeleri başarısız (arsiv/OZET.md §3).
"""
import pandas as pd

from motor.strateji.swing.ma_geri_cekilme import MaGeriCekilme as _Swing


class MaGeriCekilme(_Swing):
    ad = "scalp__ma-geri-cekilme"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "trend_ma": 100, "hedef_r": 2.0, "stop_tampon_atr": 0.5, "geri_n": 4}
    parametre_izgarasi = {
        "ma_periyot": [10, 20, 50],
        "stop_tampon_atr": [0.5, 1.0, 1.5],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef_r>0 veya MA ters kesişimi
