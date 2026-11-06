"""scalp__supertrend-psar: Supertrend / Parabolik SAR yön değişiminde gir; çizgi aynı zamanda stop.

Kural: `gosterge`="supertrend": Supertrend (atr_periyot, carpan) yönü -1 -> +1 olunca long (+1 -> -1: short).
"psar": PSAR (adim, maks) yönü değişince. "ikisi": iki gösterge AYNI yöndeyken oluşan yeni uzlaşma (biri çevirip
diğeri zaten aynı yöndeyse o mumda giriş). Opsiyonel RSI filtresi (rsi_esik>0: long için RSI>esik, short için
RSI<100-esik; kartlar 60/40). Stop = çizgi (Supertrend çizgisi / PSAR'ın bir sonraki mum değeri; "ikisi": giriş
fiyatına daha yakın olan değil, daha uzak olan — güvenli taraf = min(long)/max(short)). Hedef: hedef_r*R (0: yok).
Çıkış: karşı yönde uzlaşma/yön değişimi -> `cikis` (çizgi iz süren stop işlevini ters sinyal çıkışıyla görür).
Kaynak kartlar: daytrade__supertrend-pivot-r1s1__singhal (Supertrend ATR 7; R1/S1 filtresi kodlanmadı),
  daytrade__sar-rsi-heikin-ashi-3dk__singhal (PSAR + RSI; Heikin-Ashi kodlanmadı), scalp__halftrend-fisher-plus__carson
  (HalfTrend/Fisher kodlanmadı). Kartlar 3m-5m kaynaklı; 15m'ye taşındı.
PİP/PUAN -> ATR: kartlarda sabit pip/puan yok; stop zaten ATR tabanlı (Supertrend çizgisi = hl2 -/+ carpan*ATR).
Varsayımlar: PSAR 0.02/0.02/0.2 (kart); çarpan 3, ATR 7-10 (kart 7-10 / 2-3); ilk bar(lar)da gösterge yönü
  veriye bağlıdır (seri başlangıcına duyarlı, nedensel).
Kanıt: tek yazar örnekleri (1:3); yatayda çok sahte sinyal (uyum notu). Kısa TF trend-takip maliyet baskın.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class SupertrendPsar(Strateji):
    ad = "scalp__supertrend-psar"
    stil = "scalp"
    varsayilan_parametreler = {
        "gosterge": "supertrend", "atr_periyot": 10, "carpan": 3.0,
        "psar_adim": 0.02, "psar_maks": 0.2, "rsi_periyot": 14, "rsi_esik": 0.0,
        "hedef_r": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "gosterge": ["supertrend", "psar", "ikisi"],
        "atr_periyot": [7, 10],
        "carpan": [2.0, 3.0],
        "rsi_esik": [0.0, 55.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # ters yön değişimi

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        st = g.supertrend(y, d, k, int(p["atr_periyot"]), p["carpan"])
        ps = g.psar(y, d, p["psar_adim"], p["psar_maks"])
        if p["gosterge"] == "supertrend":
            yon, cizgi_l, cizgi_s = st["yon"], st["cizgi"], st["cizgi"]
        elif p["gosterge"] == "psar":
            yon = ps["yon"].where(st["yon"] != 0, 0)     # ATR hazır olmadan sinyal yok (ortak ısınma)
            cizgi_l = cizgi_s = ps["sar"]
        else:
            yon = pd.Series(np.where(st["yon"] == ps["yon"], st["yon"], 0), index=k.index)
            cizgi_l = np.minimum(st["cizgi"], ps["sar"])
            cizgi_s = np.maximum(st["cizgi"], ps["sar"])
        onceki = yon.shift(1, fill_value=0)
        long_ok = (yon == 1) & (onceki != 1)
        short_ok = (yon == -1) & (onceki != -1) & bool(p["short"])
        if p["rsi_esik"]:
            r = g.rsi(k, p["rsi_periyot"])
            long_ok &= r > p["rsi_esik"]
            short_ok &= r < 100 - p["rsi_esik"]
        stop_l, stop_s = pd.Series(cizgi_l, index=k.index), pd.Series(cizgi_s, index=k.index)
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        cikis = (onceki != 0) & (yon != onceki)
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
