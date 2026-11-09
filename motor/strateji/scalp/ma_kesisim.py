"""scalp__ma-kesisim: hızlı MA yavaş MA'yı keser -> kesişim yönünde gir, ters kesişimde çık.

swing `MaKesisim` (motor/strateji/ma_kesisim.py) ile aynı çekirdek; bu sınıf ondan türer. Scalp'e özgü:
  - varsayılanlar/ızgara (15m: 9/21, ATR stop 1.5),
  - `adx_esik` > 0 ise yatay piyasa filtresi (ADX <= esik iken giriş yok; kartlar: "yatay piyasada sahte sinyal,
    ADX/eğim filtresi gerekir"), çıkış sinyali filtrelenmez,
  - `hedef_r` > 0 ise sabit hedef = hedef_r * R (kartlar: scalp 1:3-1:4; 0: yalnız ters kesişim).
Kaynak kartlar: daytrade__ema5-7-ilk-saat-scalp__singhal, daytrade__ema9-21-kesisim-kirilim__singhal,
  scalp__ema14-50-kesisim__waqar, scalp__ma3-ma7-bollinger-trend-kirilim__simvour,
  scalp__linreg-5-34-cizgileri-hizala__schroder, scalp__petrol-ema5-34-rsi-10dk__schroder,
  scalp__basit-trend-ma-egim__connell, scalp__kisa-momentum-ema8-34__ellis, scalp__rsi-wma-hma__carson,
  scalp__mfi-hma65-sma200__carson.
PİP -> ATR: Connell (M5, EURUSD) kazanç ort. 11.3 pip / kayıp -7.6 pip ~ 1.0-1.5 ATR(5m) varsayımıyla ATR
  katlarına çevrilir: stop `atr_k` (1.5) ATR, hedef_r = 1.5-3 R. Waqar "10-20 pip" giriş başına hedefi
  aynı çeviriyle ~1.5-3 ATR'dir (hedef_r ızgarada yok; varsayılan 0).
Çelişki: kartlarda stop = ters kesişim / swing dip / 1-2 ATR farklı; ATR stop + ters kesişim çıkışı seçildi.
  MA tipi kartlar arası farklı (EMA/SMA/HMA); EMA varsayılan. HMA/LinReg/MFI/RSI-WMA kartları kodlanmadı.
Kanıt: şüpheli kazanma oranı iddiaları (Waqar, Simvour); Connell backtest (M5) kanıtı kitap içi, doğrulanmamış.
  Arşiv: 5 dk/kısa TF'de basit EMA kesişimi maliyet sonrası zayıf (BTC 5m EMA 9/21 ilk denemede -%17).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.ma_kesisim import MaKesisim as _Swing


class MaKesisim(_Swing):
    ad = "scalp__ma-kesisim"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "atr_k": 1.5, "adx_esik": 20.0, "adx_periyot": 14, "hedef_r": 0.0}
    parametre_izgarasi = {
        "hizli": [5, 9, 14],
        "yavas": [21, 34, 50],
        "adx_esik": [0.0, 20.0, 25.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # ters kesişim çıkışı

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        s = super().sinyaller(mumlar)
        if p["adx_esik"]:
            ax = g.adx(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["adx_periyot"])["adx"]
            kapali = ~(ax > p["adx_esik"])
            s.loc[kapali, "yon"] = 0
            s.loc[kapali, "stop"] = np.nan
        if p["hedef_r"]:
            kap = mumlar["kapanis"]
            giris = s["yon"] != 0
            s.loc[giris, "hedef"] = (kap + s["yon"] * p["hedef_r"] * (kap - s["stop"]).abs())[giris]
        return s
