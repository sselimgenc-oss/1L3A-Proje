"""scalp__fisher: Fisher Transform çizgisinin sinyal (tetik) çizgisini kesmesi (15m).

Kural: Fisher(uzunluk) (Ehlers; hl2'nin son `uzunluk` mum aralığındaki konumu). tetik = bir önceki mumun Fisher'ı
(sinyal_tipi="onceki") veya Fisher'ın SMA(ma_n)'ı (sinyal_tipi="ma"). Fisher tetiği yukarı keserse long, aşağı keserse short.
asiri_esik>0: long yalnız kesişim anında Fisher < -asiri_esik (alt bölge; kartın "alt bölgede mavi ok"), short ayna.
trend_ma>0: EMA(trend_ma) yön filtresi. Stop: son stop_n mumun dibi/zirvesi -/+ 0.25 ATR (risk <= 3 ATR).
Çıkış: ters kesişim (`cikis`, yön-bağımsız Fisher/tetik kesişimi). Hedef: hedef_r>0 ise.
Kaynak kart: scalp__fisher-plus-osc__carson (TradingView "Fisher+ [OSC]" göstergesi; kart "uzunluk 7, MA filtresi 60").
Varsayımlar: gösterge tescilli/görsel olduğundan renk dönüşü = Fisher/tetik kesişimi olarak yorumlandı; "MA filtresi 60"
belirsiz (Fisher'a mı fiyata mı?) -> sinyal_tipi="ma"/ma_n ve trend_ma ayrı parametre; stop/hedef kitapta yok.
Negatif kanıt: aile kaydında yok; arşiv kısa TF osilatör denemeleri başarısız (arsiv/OZET.md §3); tek yazar, kanıt yok.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class Fisher(Strateji):
    ad = "scalp__fisher"
    stil = "scalp"
    varsayilan_parametreler = {
        "uzunluk": 7, "sinyal_tipi": "onceki", "ma_n": 5, "asiri_esik": 0.0, "trend_ma": 0,
        "stop_n": 8, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 0.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "uzunluk": [7, 10, 14],
        "asiri_esik": [0.0, 1.0],
        "sinyal_tipi": ["onceki", "ma"],
        "trend_ma": [0, 60],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        f = b.fisher(y, d, int(p["uzunluk"]))
        atr = g.atr(y, d, k, p["atr_periyot"])
        fi = f["fisher"]
        tetik = f["tetik"] if p["sinyal_tipi"] == "onceki" else g.sma(fi, int(p["ma_n"]))
        yukari, asagi = b.yukari_kesis(fi, tetik), b.asagi_kesis(fi, tetik)
        long_ok, short_ok = yukari, asagi
        if p["asiri_esik"]:
            long_ok, short_ok = long_ok & (fi < -p["asiri_esik"]), short_ok & (fi > p["asiri_esik"])
        if p["trend_ma"]:
            ema = g.ema(k, int(p["trend_ma"]))
            long_ok, short_ok = long_ok & (k > ema), short_ok & (k < ema)
        gecerli = atr.notna() & fi.notna() & tetik.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli & bool(p["short"])
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, (yukari | asagi) & gecerli)
