"""swing__rsi-momentum-esik: RSI 50 (veya 60/40) eşiğinin geçişi momentum yönüdür; üst TF RSI aynı yöndeyse giriş.
Stil alt sınıfı: scalp/rsi_momentum_esik.py.

Kural: RSI(rsi_periyot) `esik` (50) seviyesini yukarı keserse long; `100-esik` seviyesini aşağı keserse short
(esik=60 -> long 60 yukarı / short 40 aşağı). ust_tf != "": üst TF RSI'ı (htf.ust_zaman, yalnız KAPANMIŞ üst mumlar)
long için > ust_esik (50), short için < ust_esik olmalı. Stop: son stop_n mumun dibi/zirvesi (kart: swing dip/tepe)
-/+ stop_tampon_atr*ATR, risk <= stop_max_atr ATR. Çıkış: RSI long için cikis_esik (45) altına, short için 100-cikis_esik (55)
üstüne geçince (`cikis`, yön-bağımsız: iki kesişim). Hedef: hedef_r>0 ise R katı (kart: "karşı eşik; R:R").
Kaynak kartlar: swing: swing__rsi-50-gecis__sharpe (RSI 50 yukarı kesişimi; 'RSI>50 iken yalnız long' filtresi),
swing__rsi-70-30-secim__graham (varlık seçimi 70/30 + 50 eğilim; tek varlık için seçim adımı anlamsız, KODLANMADI);
scalp: daytrade__cift-rsi-5dk-1sa__singhal (5dk RSI + 1sa RSI>50; 5dk aşırı satımdan dönüş varyantı bu çekirdeğe uymaz,
yalnız çift TF RSI-50 uyarlandı), scalp__triple-rsi-heikin-ashi__carson (tescilli gösterge, KODLANMADI).
Varsayımlar: kitaplar RSI periyodu vermiyor (Sharpe/Graham) -> 14; hysteresis çıkışı (45/55) kitapta yok (kart: "karşı eşik"); stop kitapta yok.
Negatif kanıt: aile kaydında yok; arşivde tek kuralla trend/momentum (altın/endeks) başarısız; RSI-50 gürültülü, whipsaw riski yüksek.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


class RsiMomentumEsik(Strateji):
    ad = "swing__rsi-momentum-esik"
    stil = "swing"
    varsayilan_parametreler = {
        "rsi_periyot": 14, "esik": 50.0, "cikis_esik": 45.0, "ust_tf": "", "ust_esik": 50.0,
        "stop_n": 10, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 0.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "rsi_periyot": [9, 14],
        "esik": [50.0, 55.0, 60.0],
        "ust_tf": ["", "1w"],
        "stop_n": [10, 20],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["rsi_periyot"])
        r = g.rsi(k, n)
        atr = g.atr(y, d, k, p["atr_periyot"])
        long_ok = b.yukari_kesis(r, p["esik"])
        short_ok = b.asagi_kesis(r, 100.0 - p["esik"])
        if p["ust_tf"]:
            ur = ust_zaman(mumlar, p["ust_tf"], lambda u: pd.DataFrame({"rsi": g.rsi(u["kapanis"], n)}))["rsi"]
            long_ok &= ur > p["ust_esik"]
            short_ok &= ur < p["ust_esik"]
        gecerli = atr.notna() & r.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli & bool(p["short"])
        cikis = (b.asagi_kesis(r, p["cikis_esik"]) | b.yukari_kesis(r, 100.0 - p["cikis_esik"])) & gecerli
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
