"""daytrade__pivot-seviye: önceki seansın klasik pivot / CPR seviyelerinde tepki veya kırılım.

Seviyeler (yalnız ÖNCEKİ, tamamen kapanmış seansın H/L/C'sinden; lookahead yok):
  P=(H+L+C)/3, R1=2P-L, S1=2P-H, R2=P+(H-L), S2=P-(H-L), R3=H+2(P-L), S3=L-2(H-P),
  BC=(H+L)/2, TC=2P-BC. CPR genişliği oranı = |TC-BC| / (H-L) = |2C-H-L| / (3(H-L)).
Modlar:
  "tepki"   (genis CPR gününde uygun): long = düşük seviyeye (S1 / P / S2, `seviyeler`) `temas_atr*ATR`
            yakınına iner, seviyenin üstünde kapanır ve mum yükseliş mumudur (kapanış>açılış). Short ayna
            (R1 / P / R2). Stop = temas mumu ucu ve seviyenin ötesi -/+ stop_tampon_atr*ATR.
  "kirilim" (dar CPR gününde uygun): kapanış R1'in `kirilim_tampon_atr*ATR` üstüne ilk kez çıkarsa long
            (S1 altına inerse short). Stop = kırılım mumu ucu ve seviyenin ötesi -/+ tampon.
Hedef: girişin `min_r` R ötesindeki ilk sonraki pivot seviyesi (hedef_modu="sonraki"); yoksa veya
  hedef_modu="r" ise hedef_r*R. Çıkış: seansın son mumunda `cikis=True` (gün sonu), stop, hedef.
Kaynak kartlar: daytrade__pivot-geri-cekilme-devam-donus__singhal, daytrade__cpr-genis-dar-kirilim__singhal,
  scalp__pivot-noktasi__lama (1m kaynaklı: "P'nin 2-3 puan altına limit", "10 puan hedef" -> ATR'ye çevrilmedi,
  bunun yerine seviye+ATR toleransı kullanıldı; HA renk dönüşü çıkışı kodlanmadı).
Varsayımlar (kitapta sayısal değil): CPR dar/geniş eşikleri (`cpr_dar_oran`=0.10, `cpr_genis_oran`=0.20 —
  tarafımızdan), temas toleransı, stop tamponu. Seans UTC 00:00 (parametre: seans_saat).
Çelişki/kanıt: aile kaydında negatif kanıt yok; pozitif örnekler tek tek (Nifty), kriptoda test yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, onceki_seans_hlc, seans_kimligi
from motor.strateji.temel import Strateji

_TEPKI_SEVIYE = {"s1": (["S1"], ["R1"]), "p_s1": (["P", "S1"], ["P", "R1"]),
                 "p_s1_s2": (["P", "S1", "S2"], ["P", "R1", "R2"])}


def pivot_seviyeleri(h, l, c) -> pd.DataFrame:
    p = (h + l + c) / 3.0
    bc = (h + l) / 2.0
    return pd.DataFrame({"P": p, "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l),
                         "R3": h + 2 * (p - l), "S3": l - 2 * (h - p), "BC": bc, "TC": 2 * p - bc,
                         "cpr_oran": (2 * c - h - l).abs() / (3 * (h - l))})


class PivotSeviye(Strateji):
    ad = "daytrade__pivot-seviye"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "tepki", "seviyeler": "p_s1", "cpr_filtre": "yok",
        "cpr_dar_oran": 0.10, "cpr_genis_oran": 0.20,
        "temas_atr": 0.25, "kirilim_tampon_atr": 0.1, "stop_tampon_atr": 0.5,
        "hedef_modu": "sonraki", "min_r": 1.0, "hedef_r": 2.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "mod": ["tepki", "kirilim"],
        "cpr_filtre": ["yok", "uygun"],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
        "hedef_modu": ["sonraki", "r"],
    }

    def cikis_var_mi(self) -> bool:
        return True   # seansın son mumunda cikis=True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        seans = seans_kimligi(mumlar.index, p["seans_saat"])
        hlc = onceki_seans_hlc(mumlar, seans)
        sv = pivot_seviyeleri(hlc["h"], hlc["l"], hlc["c"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        gecerli = atr.notna() & sv["P"].notna() & (hlc["h"] > hlc["l"])
        tol = p["temas_atr"] * atr
        tampon = p["stop_tampon_atr"] * atr

        if p["mod"] == "tepki":
            uygun = (sv["cpr_oran"] >= p["cpr_genis_oran"]) if p["cpr_filtre"] == "uygun" else True
            l_adlar, s_adlar = _TEPKI_SEVIYE[p["seviyeler"]]
            lv = pd.concat([sv[ad].where((d <= sv[ad] + tol) & (k > sv[ad]) & (k > a)) for ad in l_adlar], axis=1)
            sv_l = lv.max(axis=1)
            sh = pd.concat([sv[ad].where((y >= sv[ad] - tol) & (k < sv[ad]) & (k < a)) for ad in s_adlar], axis=1)
            sv_s = sh.min(axis=1)
            long_ok = sv_l.notna() & gecerli & uygun
            short_ok = sv_s.notna() & gecerli & uygun & bool(p["short"])
        else:
            uygun = (sv["cpr_oran"] <= p["cpr_dar_oran"]) if p["cpr_filtre"] == "uygun" else True
            tb = p["kirilim_tampon_atr"] * atr
            sv_l, sv_s = sv["R1"], sv["S1"]
            long_ok = (k > sv_l + tb) & (k.shift(1) <= sv_l) & gecerli & uygun
            short_ok = (k < sv_s - tb) & (k.shift(1) >= sv_s) & gecerli & uygun & bool(p["short"])

        stop_l = np.minimum(d, sv_l) - tampon
        stop_s = np.maximum(y, sv_s) + tampon
        risk_l, risk_s = k - stop_l, stop_s - k
        # sonraki pivot seviyesi (>= min_r R uzakta), yoksa hedef_r*R
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
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s,
                       gun_sonu=True, seans_saat=p["seans_saat"])
