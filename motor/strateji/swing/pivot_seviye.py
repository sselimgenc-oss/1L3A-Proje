"""swing__pivot-seviye: önceki GÜN/HAFTA H/L/C pivot (P, R1-R3, S1-S3) seviyelerinde trend yönünde tepki veya kırılım (4h/1d).

Seviyeler yalnız bir ÖNCEKİ, tamamen kapanmış dönemden (pivot_periyodu="hafta": Pazartesi 00:00 UTC hizalı hafta;
"gun": UTC gün) hesaplanır (`daytrade.pivot_seviye.pivot_seviyeleri`, lookahead yok).
Modlar (daytrade__pivot-seviye ile aynı mantık; gün sonu çıkışı YOK):
  "tepki":   long = dip seviyeye (S1 / P / S2, `seviyeler`) `temas_atr*ATR` yakınına iner, seviyenin üstünde
            kapanır, yükseliş mumu (kapanış>açılış) ve (trend_ema>0 ise) kapanış > EMA(trend_ema). Short ayna.
            Stop = temas mumu ucu ve seviyenin ötesi -/+ stop_tampon_atr*ATR.
  "kirilim": kapanış R1'in `kirilim_tampon_atr*ATR` üstüne ilk kez çıkarsa long (S1 altı short); (trend filtresi aynı).
Hedef: girişin min_r R ötesindeki ilk sonraki pivot seviyesi ("sonraki") yoksa/"r" ise hedef_r*R. Çıkış: hedef/stop.
Kaynak kart (tek): daytrade__pivot-pozisyonel-destek__singhal (1d; yükselişte P/S1/S2'de yükseliş mumu -> mum
  zirvesi üstü giriş; düşüşte P/R1/R2; stop bölgenin ötesi; hedef sonraki pivot veya 1:2; haftalarca tutulur).
  Kartta "pozisyonel" pivotun hangi dönemden hesaplandığı yazmıyor -> haftalık varsayıldı (ızgarada gün de var).
Varsayımlar: trend = EMA(50) konumu (kartta trend tanımı yok); giriş mum kapanışı (kart: zirve üstü stop-buy).
  CPR dar/geniş filtresi bu sürümde yok (daytrade sürümünde var; swing kartında geçmiyor).
Negatif kanıt: aile kaydında yok; tek yazar, kriptoda test yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, onceki_seans_hlc, seans_kimligi
from motor.strateji.daytrade.pivot_seviye import _TEPKI_SEVIYE, pivot_seviyeleri
from motor.strateji.temel import Strateji


class PivotSeviye(Strateji):
    ad = "swing__pivot-seviye"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_periyodu": "hafta", "mod": "tepki", "seviyeler": "p_s1", "trend_ema": 50,
        "temas_atr": 0.25, "kirilim_tampon_atr": 0.1, "stop_tampon_atr": 0.5,
        "hedef_modu": "sonraki", "min_r": 1.0, "hedef_r": 2.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "mod": ["tepki", "kirilim"],
        "pivot_periyodu": ["gun", "hafta"],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
        "hedef_modu": ["sonraki", "r"],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef her zaman var (sonraki seviye veya hedef_r*R)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        gun = seans_kimligi(mumlar.index, 0.0)
        donem = (gun + 3) // 7 if p["pivot_periyodu"] == "hafta" else gun   # Pazartesi hizalı hafta no
        hlc = onceki_seans_hlc(mumlar, donem)
        sv = pivot_seviyeleri(hlc["h"], hlc["l"], hlc["c"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        gecerli = atr.notna() & sv["P"].notna() & (hlc["h"] > hlc["l"])
        if p["trend_ema"]:
            ema = g.ema(k, int(p["trend_ema"]))
            ust_t, alt_t = (k > ema), (k < ema)
        else:
            ust_t = alt_t = pd.Series(True, index=k.index)
        tol = p["temas_atr"] * atr
        tampon = p["stop_tampon_atr"] * atr

        if p["mod"] == "tepki":
            l_adlar, s_adlar = _TEPKI_SEVIYE[p["seviyeler"]]
            lv = pd.concat([sv[ad].where((d <= sv[ad] + tol) & (k > sv[ad]) & (k > a)) for ad in l_adlar], axis=1)
            sv_l = lv.max(axis=1)
            sh = pd.concat([sv[ad].where((y >= sv[ad] - tol) & (k < sv[ad]) & (k < a)) for ad in s_adlar], axis=1)
            sv_s = sh.min(axis=1)
            long_ok = sv_l.notna() & gecerli & ust_t
            short_ok = sv_s.notna() & gecerli & alt_t & bool(p["short"])
        else:
            tb = p["kirilim_tampon_atr"] * atr
            sv_l, sv_s = sv["R1"], sv["S1"]
            long_ok = (k > sv_l + tb) & (k.shift(1) <= sv_l) & gecerli & ust_t
            short_ok = (k < sv_s - tb) & (k.shift(1) >= sv_s) & gecerli & alt_t & bool(p["short"])

        stop_l = np.minimum(d, sv_l) - tampon
        stop_s = np.maximum(y, sv_s) + tampon
        risk_l, risk_s = k - stop_l, stop_s - k
        kolon = ["S3", "S2", "S1", "P", "R1", "R2", "R3"]
        m = sv[kolon].to_numpy()
        kk = k.to_numpy()[:, None]
        with np.errstate(invalid="ignore"):
            ust = np.where(m >= kk + p["min_r"] * risk_l.to_numpy()[:, None], m, np.inf).min(axis=1)
            alt = np.where(m <= kk - p["min_r"] * risk_s.to_numpy()[:, None], m, -np.inf).max(axis=1)
        h_l = k + p["hedef_r"] * risk_l
        h_s = k - p["hedef_r"] * risk_s
        if p["hedef_modu"] == "sonraki":
            h_l = pd.Series(np.where(np.isfinite(ust), ust, h_l), index=k.index)
            h_s = pd.Series(np.where(np.isfinite(alt), alt, h_s), index=k.index)
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, gun_sonu=False)
