"""swing__cci-esik: CCI eşik kesişimleri (Lambert ±100; CCI(5) trend yönünde geri çekilme dönüşü).

Üç mod (`mod`):
  "lambert"       : CCI +esik'i yukarı keserse long, -esik'i aşağı keserse short; ters eşik kesişiminde çıkış
                    (kart scalp__cci-100-kirilim__busiere; kanonik kural).
  "esik30"        : CCI son `bolge_n` mumda -esik'in altına inmiş olup -ic_esik (30) çizgisini yukarı keserse long
                    (short ayna). Çıkış: CCI sıfırı keser (kart seçeneği "CCI 0 çizgisine yaklaşınca";
                    scalp__cci-30-kirilim__busiere, CCI(9)).
  "geri_cekilme"  : trend filtresi (kapanış > SMA(trend_ma)) altında CCI -esik'i yukarı keserse long (short ayna);
                    Pristine/Velez "trend yönünde CCI(5) sinyali" yorumu (swing__cci5-pristine-sinyal__velez).
Stop: son stop_n mumun dibi/zirvesi -/+ stop_tampon_atr*ATR, risk <= stop_max_atr ATR. Hedef: hedef_r>0 ise R katı.
Çıkış `cikis` yön-bağımsızdır (temel arayüz): lambert'te ±esik ters kesişimi, diğerlerinde sıfır kesişimi.
trend_ma>0: EMA(trend_ma) filtresi (long yalnız kapanış > EMA; geri_cekilme'de SMA(trend_ma) zorunlu kullanılır).
Kaynak kartlar: scalp__cci-100-kirilim__busiere, scalp__cci-30-kirilim__busiere, swing__cci5-pristine-sinyal__velez.
KODLANMADI: scalp__cci-zirve__busiere (dönüş teyidi kitapta tanımsız).
Kitap yok varsayımları: kartlarda stop yok -> swing/ATR stop; Velez'de sayısal tetik yok -> -100 yukarı kesişimi varsayımı;
Busiere'in pivot/%0.4 gün-içi trend filtresi (1m-5m, görsel) kodlanmadı (yerine trend_ma).
Negatif kanıt: aile kaydında yok; arşiv kısa TF osilatör/dönüş denemelerinde başarısız (arsiv/OZET.md §3); tek yazar (Busiere) + Velez.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class CciEsik(Strateji):
    ad = "swing__cci-esik"
    stil = "swing"
    _gun_sonu = False
    varsayilan_parametreler = {
        "cci_periyot": 5, "mod": "geri_cekilme", "esik": 100.0, "ic_esik": 30.0, "bolge_n": 3,
        "trend_ma": 50, "stop_n": 5, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 0.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "cci_periyot": [5, 9, 14],
        "mod": ["lambert", "geri_cekilme"],
        "stop_n": [3, 5, 10],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        c = b.cci(y, d, k, int(p["cci_periyot"]))
        atr = g.atr(y, d, k, p["atr_periyot"])
        e = p["esik"]
        mod = p["mod"]
        if mod == "lambert":
            long_ok, short_ok = b.yukari_kesis(c, e), b.asagi_kesis(c, -e)
            cikis = b.asagi_kesis(c, e) | b.yukari_kesis(c, -e)
        elif mod == "esik30":
            n = int(p["bolge_n"])
            long_ok = b.yukari_kesis(c, -p["ic_esik"]) & (c.rolling(n, min_periods=1).min() <= -e)
            short_ok = b.asagi_kesis(c, p["ic_esik"]) & (c.rolling(n, min_periods=1).max() >= e)
            cikis = b.yukari_kesis(c, 0.0) | b.asagi_kesis(c, 0.0)
        elif mod == "geri_cekilme":
            ma = g.sma(k, int(p["trend_ma"] or 50))
            long_ok = b.yukari_kesis(c, -e) & (k > ma)
            short_ok = b.asagi_kesis(c, e) & (k < ma)
            cikis = b.yukari_kesis(c, 0.0) | b.asagi_kesis(c, 0.0)
        else:
            raise ValueError(f"Bilinmeyen mod: {mod}")
        if p["trend_ma"] and mod != "geri_cekilme":
            ema = g.ema(k, int(p["trend_ma"]))
            long_ok, short_ok = long_ok & (k > ema), short_ok & (k < ema)
        gecerli = atr.notna() & c.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli & bool(p["short"])
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis & gecerli,
                       gun_sonu=self._gun_sonu, seans_saat=p["seans_saat"])
