"""swing__ma-kesisim kanonik kuralı.

Long: hızlı MA yavaş MA'yı yukarı keser (mum kapanışında) ve (varsa) kapanış trend MA'sının üstünde.
Short: aynasının tersi. Stop = kapanış -/+ atr_k * ATR. Ters kesişimde `cikis`.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.temel import Strateji


class MaKesisim(Strateji):
    ad = "ma_kesisim"
    stil = "swing"
    varsayilan_parametreler = {
        "hizli": 9, "yavas": 21,
        "trend_ma": 0,          # 0: trend filtresi yok; örn. 200
        "ma_tipi": "ema",       # "ema" | "sma"
        "atr_periyot": 14, "atr_k": 2.0,
        "short": True,
    }
    parametre_izgarasi = {
        "hizli": [5, 9, 14],
        "yavas": [21, 34, 50],
        "atr_k": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        ma = g.ema if p["ma_tipi"] == "ema" else g.sma
        kap = mumlar["kapanis"]
        hizli, yavas = ma(kap, p["hizli"]), ma(kap, p["yavas"])
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, p["atr_periyot"])

        yukari = (hizli > yavas) & (hizli.shift(1) <= yavas.shift(1))
        asagi = (hizli < yavas) & (hizli.shift(1) >= yavas.shift(1))

        long_ok, short_ok = yukari, asagi & bool(p["short"])
        if p["trend_ma"]:
            trend = ma(kap, p["trend_ma"])
            long_ok = long_ok & (kap > trend)
            short_ok = short_ok & (kap < trend)
        long_ok = long_ok & atr.notna()
        short_ok = short_ok & atr.notna()

        yon = pd.Series(0, index=mumlar.index, dtype="int64")
        yon[long_ok] = 1
        yon[short_ok] = -1
        stop = pd.Series(np.nan, index=mumlar.index)
        stop[long_ok] = (kap - p["atr_k"] * atr)[long_ok]
        stop[short_ok] = (kap + p["atr_k"] * atr)[short_ok]
        return pd.DataFrame({
            "yon": yon, "stop": stop,
            "hedef": np.nan,
            "cikis": (yukari | asagi).astype(bool),
        })

    def cikis_var_mi(self) -> bool:
        """Ters kesişimde `cikis` üretir (her zaman)."""
        return True
