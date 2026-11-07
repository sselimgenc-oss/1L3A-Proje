"""swing__ma-kesisim kanonik kuralı.

Long: hızlı MA yavaş MA'yı yukarı keser (mum kapanışında) ve (varsa) kapanış trend MA'sının üstünde.
Short: aynasının tersi. Stop = kapanış -/+ atr_k * ATR. Ters kesişimde `cikis`.

d11j EK SEÇENEKLER (varsayılanlar eskisiyle aynı; ızgaraya girmez, ayar kaydıyla denenir):
  ma_tipi: "ema" | "sma" (eski davranış: ema dışındaki bilinmeyen değer SMA sayılır) | "wma", "hma", "alma", "cma" (düzeltilmiş
  MA: SMA'nın varyans ayarlı hâli) hizli/yavas periyotlarıyla | "mama" (hizli=MAMA, yavas=FAMA; hizli/yavas periyotları
  KULLANILMAZ, mama_hizli/mama_yavas sınır alfaları) | "itrend" (hizli=Ehlers anlık trend çizgisi, yavas=tetik 2*trend-trend[2];
  itrend_alfa). `kaynak`: MA'ya giren fiyat "kapanis" (varsayılan) | "ohlc4" | "ha_ohlc4" (Heikin-Ashi OHLC/4; MAMA kaynağı).
  trend_ma filtresi ma_tipi'ne bakmaz: mama/itrend'de EMA kullanılır. Kaynak aile: mama-fama-itrend-cma-ma-turleri
  (Ehlers MAMA/FAMA, Instantaneous Trend, Corrected MA); formüller _gosterge_d11j.py'de sıfırdan yazıldı.
"""
import numpy as np
import pandas as pd

from motor.strateji import _gosterge_d11j as j
from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.temel import Strateji


class MaKesisim(Strateji):
    ad = "swing__ma-kesisim"
    stil = "swing"
    varsayilan_parametreler = {
        "hizli": 9, "yavas": 21,
        "trend_ma": 0,          # 0: trend filtresi yok; örn. 200
        "ma_tipi": "ema",       # "ema" | "sma"
        "atr_periyot": 14, "atr_k": 2.0,
        "short": True,
        "kaynak": "kapanis", "mama_hizli": 0.5, "mama_yavas": 0.05, "itrend_alfa": 0.07,
    }
    parametre_izgarasi = {
        "hizli": [5, 9, 14],
        "yavas": [21, 34, 50],
        "atr_k": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        tip = p["ma_tipi"]
        kap = mumlar["kapanis"]
        ma = g.ema if tip == "ema" else g.sma
        kay = self._kaynak(mumlar)
        if tip in ("wma", "hma", "alma", "cma"):
            hizli, yavas = j.ma_turu(kay, tip, p["hizli"]), j.ma_turu(kay, tip, p["yavas"])
            ma = g.ema
        elif tip == "mama":
            hizli, yavas = j.mama_fama(kay, p["mama_hizli"], p["mama_yavas"])
            ma = g.ema
        elif tip == "itrend":
            hizli, yavas = j.itrend(kay, p["itrend_alfa"])
            ma = g.ema
        else:
            hizli, yavas = ma(kay, p["hizli"]), ma(kay, p["yavas"])
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

    def _kaynak(self, mumlar: pd.DataFrame) -> pd.Series:
        kay = self.parametreler["kaynak"]
        if kay == "kapanis":
            return mumlar["kapanis"]
        a, y, d, k = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        if kay == "ohlc4":
            return (a + y + d + k) / 4.0
        if kay == "ha_ohlc4":
            ha = b.heikin_ashi(a, y, d, k)
            return (ha["ha_acilis"] + ha["ha_yuksek"] + ha["ha_dusuk"] + ha["ha_kapanis"]) / 4.0
        raise ValueError(f"Bilinmeyen kaynak: {kay}")

    def cikis_var_mi(self) -> bool:
        """Ters kesişimde `cikis` üretir (her zaman)."""
        return True
