"""scalp__stokastik-donus: trend yönünde Stokastik 20/80 aşırı bölge dönüşü (trend filtreli).

Kural: Yavaş Stokastik (%K_ham `k_periyot`, %K = SMA(ham, k_yumusat), %D = SMA(%K, d_periyot);
kartlarda 12,3,5 / 14,3,3 / 8,3,3). Long: kapanış > EMA(trend_ema) ve son `bolge_n` mum içinde %K <= asiri_esik (20)
oldu ve %K şimdi %D'yi yukarı kesti. Short: ayna (kapanış < EMA, %K >= 100-asiri_esik, %K %D'yi aşağı keser).
Stop: son `stop_n` mumun dibi/zirvesi -/+ stop_tampon_atr*ATR (kartlar: son swing dip/tepe), risk en çok
`stop_max_atr` ATR ile sınırlı. Hedef: hedef_r*R (kartlar: 1:2). Çıkış: %K %D'yi ters yönde keserse `cikis` (Backus çıkışı).
Kaynak kartlar: daytrade__stokastik-rsi-ema20-2dk__backus, daytrade__stokastik-20-donus-yuzde-1__backus,
  scalp__macd-stokastik-m1-m5__eseckal, scalp__bir-dakika-ema50-100-stoch__ellis,
  scalp__sma500-hma30-stokastik-rsi__carson, swing__stochsplit__scheier. Hepsi 1m-5m kaynaklı.
PİP/PUAN -> ATR: Backus "%1 stop / %1 hedef" (2m hisse; tipik 2m ATR ~%0.1-0.2'ye göre ~5-10 ATR) burada
  1.0-2.0 R ve ATR tabanlı stop (swing dibi + tampon, en çok 3 ATR) ile değiştirildi: 15m ATR'sine göre
  ölçeklenir. S&P yön filtresi (Backus) ve MACD/RSI(9) onayları kodlanmadı.
Varsayımlar: "20'ye dokundu sonra %D'yi geçti" = son `bolge_n` mumda %K<=20 ve şimdi kesişim; trend MA tipi EMA.
Negatif kanıt: arşiv (arsiv/OZET.md §3) "Stokastik dönüşü" ve 5 dk geri çekilme/dönüş denemelerini
  başarısız listeler; kısa TF'de maliyet baskın. Bu aday zayıf prior ile test edilir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class StokastikDonus(Strateji):
    ad = "scalp__stokastik-donus"
    stil = "scalp"
    varsayilan_parametreler = {
        "trend_ema": 50, "k_periyot": 14, "k_yumusat": 3, "d_periyot": 3,
        "asiri_esik": 20.0, "bolge_n": 3, "stop_n": 8, "stop_tampon_atr": 0.25,
        "stop_max_atr": 3.0, "hedef_r": 2.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "trend_ema": [20, 50, 100],
        "k_periyot": [8, 14],
        "hedef_r": [1.0, 1.5, 2.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef + ters %K/%D kesişimi

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ham = g.stokastik(y, d, k, int(p["k_periyot"]), 1)["k"]
        kk = g.sma(ham, int(p["k_yumusat"]))
        dd = g.sma(kk, int(p["d_periyot"]))
        atr = g.atr(y, d, k, p["atr_periyot"])
        ema = g.ema(k, int(p["trend_ema"]))
        n = int(p["bolge_n"])
        yukari = (kk > dd) & (kk.shift(1) <= dd.shift(1))
        asagi = (kk < dd) & (kk.shift(1) >= dd.shift(1))
        asiri_alt = kk.rolling(n, min_periods=1).min() <= p["asiri_esik"]
        asiri_ust = kk.rolling(n, min_periods=1).max() >= 100 - p["asiri_esik"]
        gecerli = atr.notna() & ema.notna() & dd.notna()
        long_ok = gecerli & yukari & asiri_alt & (k > ema)
        short_ok = gecerli & asagi & asiri_ust & (k < ema) & bool(p["short"])
        sn = int(p["stop_n"])
        tampon = p["stop_tampon_atr"] * atr
        stop_l = np.maximum(d.rolling(sn, min_periods=sn).min() - tampon, k - p["stop_max_atr"] * atr)
        stop_s = np.minimum(y.rolling(sn, min_periods=sn).max() + tampon, k + p["stop_max_atr"] * atr)
        h_l = k + p["hedef_r"] * (k - stop_l)
        h_s = k - p["hedef_r"] * (stop_s - k)
        cikis = (asagi | yukari) & gecerli
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
