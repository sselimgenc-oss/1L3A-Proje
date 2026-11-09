"""daytrade__trend-yapi-dow: Dow piyasa yapısı (HH/HL - LH/LL) yönünde swing kırılımı veya çoklu TF mum uyumu (1h).
Stil alt sınıfı: scalp/trend_yapi_dow.py (15m).

mod="yapi": fraktal pivotlarla (k=pivot_k, nedensel) yükseliş yapısı = son tepe > önceki tepe VE son dip > önceki dip. Long: kapanış
son salınım tepesini aşağıdan yukarı keser (kırılım mumu kapanışı; kartta "kırılım mumunun tepesi"). yapi_sart=False ise yapı
koşulu aranmaz (yalnız kırılım). Short ayna (LL/LH, son salınım dibinin kırılması).
mod="coklu_tf": kapanmış mum renkleri `tf_listesi` içindeki her üst TF'de (htf.ust_zaman, lookahead'siz) ve işlem TF'sinde aynı yönde
(hepsi yeşil -> long, hepsi kırmızı -> short) ve kapanış bir önceki kapanışın üstünde/altındaysa, durum YENİ oluştuğunda giriş
(kart eseckal: H1/M30/M15/M5 aynı renk).
Ortak: ust_tf != "" ise üst TF kapanmış mum kapanışı > EMA(ust_ema) (long) / < (short) filtresi (kart: "üst zaman yön").
Stop: yapi modunda son salınım dibi/tepesi -/+ stop_tampon_atr*ATR; coklu_tf'de son stop_n mumun ucu; risk <= stop_max_atr ATR.
Hedef: hedef_r>0 ise R katı (kart: 1:2+). Çıkış: karşı yön kırılımı/uyumu (`cikis`, yön-bağımsız) ve (daytrade) UTC gün sonu.
Kaynak kartlar: daytrade__dow-piyasa-yapisi-kirilim__singhal, daytrade__trend-takibi-yukselen-dusen__derr (ölçü tanımsız: KODLANMADI,
yalnız yön fikri), scalp__trendi-yakala-1-2-3-vwap__schroder (VWAP/RSI(2) dip alımı, günlük: KODLANMADI), scalp__fiyat-eylemi-4-zaman-dilimi__eseckal
(coklu_tf; 5dk bacağı min 15m kuralı nedeniyle çıkarıldı, pip stop/hedef ATR'ye çevrildi; saat başı/haber filtresi yok).
Varsayımlar: kitaplar salınım tanımı vermez -> fraktal k; momentum osilatörü doğrulaması (Singhal önerisi) kodlanmadı; VWAP kâr alma kodlanmadı.
Negatif kanıt: aile kaydında yok; arşivde Donchian/kırılım ve trend çizgisi denemeleri başarısız (arsiv/OZET.md §3); gün içinde kırılımlar maliyet baskın.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


class TrendYapiDow(Strateji):
    ad = "daytrade__trend-yapi-dow"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {
        "mod": "yapi", "pivot_k": 3, "yapi_sart": True, "tf_listesi": ("2h", "4h"), "ust_tf": "4h", "ust_ema": 20,
        "stop_n": 6, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 2.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "pivot_k": [2, 3, 5],
        "hedef_r": [0.0, 1.5, 2.0, 3.0],
        "yapi_sart": [True, False],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        tampon = p["stop_tampon_atr"] * atr
        if p["mod"] == "yapi":
            pv = fraktal_pivotlar(y, d, int(p["pivot_k"]))
            kir_l = b.yukari_kesis(k, pv["son_tepe_fiyat"])
            kir_s = b.asagi_kesis(k, pv["son_dip_fiyat"])
            if p["yapi_sart"]:
                kir_l &= (pv["son_tepe_fiyat"] > pv["onceki_tepe_fiyat"]) & (pv["son_dip_fiyat"] > pv["onceki_dip_fiyat"])
                kir_s &= (pv["son_tepe_fiyat"] < pv["onceki_tepe_fiyat"]) & (pv["son_dip_fiyat"] < pv["onceki_dip_fiyat"])
            long_ok, short_ok = kir_l, kir_s
            ham_l, ham_s = pv["son_dip_fiyat"] - tampon, pv["son_tepe_fiyat"] + tampon
            stop_l = np.maximum(ham_l, k - p["stop_max_atr"] * atr)
            stop_s = np.minimum(ham_s, k + p["stop_max_atr"] * atr)
            cikis = kir_l | kir_s
        elif p["mod"] == "coklu_tf":
            renk = np.sign(k - a)
            uyum_l = (renk > 0) & (k > k.shift(1))
            uyum_s = (renk < 0) & (k < k.shift(1))
            for tf in tuple(p["tf_listesi"]):
                r = ust_zaman(mumlar, tf, lambda u: pd.DataFrame({"renk": np.sign(u["kapanis"] - u["acilis"])}))["renk"]
                uyum_l &= r > 0
                uyum_s &= r < 0
            gecerli_atr = atr.notna()
            long_ok, short_ok = b.gecis(uyum_l & gecerli_atr), b.gecis(uyum_s & gecerli_atr)
            stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
            cikis = long_ok | short_ok
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        if p["ust_tf"]:
            ue = int(p["ust_ema"])
            fark = ust_zaman(mumlar, p["ust_tf"],
                             lambda u: pd.DataFrame({"fark": u["kapanis"] - g.ema(u["kapanis"], ue)}))["fark"]
            long_ok, short_ok = long_ok & (fark > 0), short_ok & (fark < 0)
        gecerli = atr.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli & bool(p["short"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis & gecerli,
                       gun_sonu=self._gun_sonu, seans_saat=p["seans_saat"])
