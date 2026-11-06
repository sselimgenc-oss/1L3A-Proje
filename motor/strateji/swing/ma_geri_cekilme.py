"""swing__ma-geri-cekilme: trendde hareketli ortalamaya geri çekilme + sıçrama mumu.

Kaynak kartlar: ladha, sharpe, penn, make, velez, graham, kratter (x2).
Ortak çekirdek: trend var (uzun MA'nın üstünde; MA hizalı) -> fiyat 10/20/50 MA bölgesine çekilir ->
dönüş/sıçrama mumu -> trend yönünde giriş. Short: ayna (sharpe, velez, graham).
Çıkış (ladha, kratter): MA'nın karşı tarafında kapanış -> `cikis`.
Kanonik kural ile çelişki: "ADX>=30" yalnızca kratter kartında; zorunlu değil, `adx_esik` ile isteğe bağlı (0=kapalı).
"Hacim düşük" ve "ölü kedi" filtreleri kodlanmadı.

Varsayımlar (kitapta olmayan): temas = son `geri_n` mumda (şu an dahil) dip <= MA + temas_atr*ATR;
sıçrama mumu = yönde kapanan mum (kapanış>açılış) ve kapanış > MA ve kapanış > önceki mumun zirvesi;
trend = kapanış > trend_ma (SMA) ve MA > trend_ma; stop = geri çekilme dibi (son geri_n mum) - stop_tampon_atr*ATR
(kartlar: "giriş mumu dibinin/MA'nın biraz altı, backtest 1-2 ATR"); hedef = hedef_r * R (0 ise NaN; kitapta 2-3R).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MaGeriCekilme(Strateji):
    ad = "swing__ma-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {
        "ma_periyot": 20, "ma_tipi": "ema",
        "trend_ma": 200,          # SMA; 0: trend filtresi yok
        "geri_n": 5, "temas_atr": 0.0,
        "adx_esik": 0.0, "adx_periyot": 14,    # 0: ADX filtresi kapalı
        "atr_periyot": 14, "stop_tampon_atr": 0.5,
        "hedef_r": 0.0,           # 0: hedef yok (NaN)
        "short": True,
    }
    parametre_izgarasi = {
        "ma_periyot": [10, 20, 50],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
        "hedef_r": [0.0, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ma = (g.ema if p["ma_tipi"] == "ema" else g.sma)(k, p["ma_periyot"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        n = p["geri_n"]
        tol = p["temas_atr"] * atr

        temas_long = (d <= ma + tol).rolling(n, min_periods=n).max().astype(bool)
        temas_short = (y >= ma - tol).rolling(n, min_periods=n).max().astype(bool)
        long_ok = temas_long & (k > ma) & (k > a) & (k > y.shift(1))
        short_ok = temas_short & (k < ma) & (k < a) & (k < d.shift(1)) & bool(p["short"])
        if p["trend_ma"]:
            tr = g.sma(k, p["trend_ma"])
            long_ok &= (k > tr) & (ma > tr)
            short_ok &= (k < tr) & (ma < tr)
        if p["adx_esik"]:
            ax = g.adx(y, d, k, p["adx_periyot"])["adx"]
            yuk = (ax > p["adx_esik"]) & (ax > ax.shift(1))
            long_ok &= yuk
            short_ok &= yuk
        gecerli = atr.notna() & ma.notna()
        long_ok &= gecerli
        short_ok &= gecerli

        stop_l = d.rolling(n, min_periods=n).min() - p["stop_tampon_atr"] * atr
        stop_s = y.rolling(n, min_periods=n).max() + p["stop_tampon_atr"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        cikis = (((k < ma) & (k.shift(1) >= ma.shift(1))) |
                 ((k > ma) & (k.shift(1) <= ma.shift(1)))) & gecerli
        return sinyal_cercevesi(mumlar.index, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
