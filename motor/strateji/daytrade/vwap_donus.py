"""daytrade__vwap-donus: seans VWAP'ından ±k standart sapma bandına aşırı uzaklaşma sonrası ortalamaya dönüş.

VWAP: seans başından (UTC gün; `seans_saat` ile değişir) mum kapanışına kadar kümülatif, tipik fiyat
(H+L+C)/3 x hacim; sapma = hacim ağırlıklı std. Her seansta sıfırlanır; yalnız kapanmış mumlar kullanılır.
Kural (Singhal): A mumu alt bandın (VWAP - bant_k*sd) altında kapanır (aşırı satım); B mumu (A veya A'dan
sonraki) yükseliş mumudur (kapanış>açılış; "boğa ters çekiç" yerine yalın yükseliş mumu); giriş mumu
B'nin zirvesinin üstünde kapanınca long (kartın "önceki yeşil mumun yükseğini kır" teyidi kapanışla).
Short ayna (üst bant, düşüş mumu, B'nin dibinin altında kapanış). Mum desenleri (çekiç) kodlanmadı.
Opsiyonel RSI teyidi (rsi_esik>0: önceki mumda RSI<esik; short: >100-esik). İlk `min_mum` mumda sinyal yok
(sd güvenilmez). Stop: son iki mumun ucu -/+ stop_tampon_atr*ATR. Hedef: VWAP (hedef_tipi="vwap") veya karşı bant
(hedef_tipi="karsi_bant"). Çıkış: hedef, stop, seansın son mumu (gün sonu `cikis`).
Kaynak kartlar: daytrade__vwap-2sd-ortalamaya-donus__singhal (5m, VWAP #2 bant; min 1:2 R/R tercihi),
  daytrade__rsi-vwap-scalp-1dk__singhal (RSI teyidi; 1m), scalp__vwap-geri-cekilme-plani__schroder (1m).
  1m kaynaklı kartlar 1h/30m'e taşındığı için "esinlenen" uyarlamadır.
Varsayımlar: "trend günü değil" filtresi kodlanmadı; bant 2SD varsayılan (ızgara 1.5-2.5); kriptoda UTC gün
  VWAP'ı yaygın ama seans-başı anlamı yapaydır; hacim çekirdek veridir. Hedef=VWAP, bant uzakta olduğu için
  R/R genelde >=1'dir ama garanti edilmez.
Negatif kanıt: aile kaydında yok; ancak arşiv özeti, kısa TF ortalamaya dönüş denemelerini (1S RSI/BB, bant dönüşü)
  başarısız bulmuştur (arsiv/OZET.md §3).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.temel import Strateji


class VwapDonus(Strateji):
    ad = "daytrade__vwap-donus"
    stil = "daytrade"
    varsayilan_parametreler = {
        "bant_k": 2.0, "min_mum": 6, "rsi_periyot": 14, "rsi_esik": 0.0,
        "stop_tampon_atr": 0.25, "hedef_tipi": "vwap", "atr_periyot": 14,
        "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "bant_k": [1.5, 2.0, 2.5],
        "hedef_tipi": ["vwap", "karsi_bant"],
        "rsi_esik": [0.0, 30.0, 35.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        seans = seans_kimligi(mumlar.index, p["seans_saat"])
        v = g.vwap_seans(y, d, k, mumlar["hacim"], seans)
        atr = g.atr(y, d, k, p["atr_periyot"])
        alt = v["vwap"] - p["bant_k"] * v["sd"]
        ust = v["vwap"] + p["bant_k"] * v["sd"]
        # önceki mum aşırı bölgede (aynı seansta), şimdiki mum dönüş
        ayni = pd.Series(seans, index=k.index) == pd.Series(seans, index=k.index).shift(1)
        hazir = (v["mum_no"] > p["min_mum"]) & (v["sd"] > 0) & atr.notna() & ayni
        # B mumu (t-1): yükseliş mumu ve kendisi veya bir önceki mum (A, t-2) alt bandın altında kapandı;
        # giriş mumu (t) B'nin zirvesinin üstünde kapanır ("önceki yeşil mumun yükseğini kır").
        asiri_alt = (k.shift(1) < alt.shift(1)) | (k.shift(2) < alt.shift(2))
        asiri_ust = (k.shift(1) > ust.shift(1)) | (k.shift(2) > ust.shift(2))
        long_ok = hazir & asiri_alt & (k.shift(1) > a.shift(1)) & (k > y.shift(1))
        short_ok = hazir & asiri_ust & (k.shift(1) < a.shift(1)) & (k < d.shift(1)) & bool(p["short"])
        if p["rsi_esik"]:
            r = g.rsi(k, p["rsi_periyot"]).shift(1)
            long_ok &= r < p["rsi_esik"]
            short_ok &= r > 100 - p["rsi_esik"]
        tampon = p["stop_tampon_atr"] * atr
        stop_l = np.minimum(d, d.shift(1)) - tampon
        stop_s = np.maximum(y, y.shift(1)) + tampon
        if p["hedef_tipi"] == "vwap":
            h_l = h_s = v["vwap"]
        else:
            h_l, h_s = ust, alt
        # hedef girişin doğru tarafında değilse sinyal anlamsız
        long_ok &= h_l > k
        short_ok &= h_s < k
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s,
                       gun_sonu=True, seans_saat=p["seans_saat"])
