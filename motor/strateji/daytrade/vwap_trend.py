"""daytrade__vwap-trend: fiyat seans VWAP'ını kapanışla geçince yönde giriş; gün sonunda kapanır (1h).

VWAP: seans başından (UTC gün; `seans_saat`) kapanışa kümülatif tipik fiyat x hacim (gostergeler.vwap_seans), her seansta
sıfırlanır. Long: kapanış VWAP + tampon_atr*ATR üstüne İLK kez çıkar (önceki kapanış VWAP altında/üstünde değildi),
aynı seans içinde; short ayna. Seansın ilk `min_mum` mumunda sinyal yok (VWAP oturmamış). Opsiyonel hacim filtresi.
Stop = VWAP -/+ stop_atr*ATR (backtest önerisi VWAP +-0.5 ATR; kitap: VWAP risk seviyesi). Hedef: hedef_r*R (0: yok).
Çıkış: VWAP'ın ters yönde kapanışla kesilmesi (`cikis`) ve seansın son mumunda gün sonu zorunlu çıkış.
Kaynak kartlar: swing__vwap-kesisim__graham (VWAP yukarı kesince al, aşağı kesince sat; VWAP risk seviyesi) -> kart ayarı;
  swing__vwap-konum__johnson (fiyat VWAP'ın altında=boğa/üstünde=ayı etiketli yorum, tetik tanımsız) -> KODLANMADI.
  Johnson'ın "VWAP altında long" yorumu Graham'ın kesişim mantığının TERSİDİR (ortalamaya dönüş); çelişki. Burada
  trend (kesişim) yorumu kodlandı; ortalamaya dönüş için bkz. daytrade__vwap-donus.
Varsayımlar: kitaplar stop/hedef sayısı vermez (ATR tabanlı varsayım); kripto 7/24'te UTC 00:00 VWAP sıfırlama yapay;
  seans_saat ile değişir. Hacim çekirdek veridir.
Negatif kanıt: aile kaydında yok; kısa TF'de VWAP kesişimi yatay günde çok sahte sinyal üretir (komisyon baskın).
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.temel import Strateji


class VwapTrend(Strateji):
    ad = "daytrade__vwap-trend"
    stil = "daytrade"
    varsayilan_parametreler = {
        "tampon_atr": 0.0, "min_mum": 3, "hacim_k": 0.0, "stop_atr": 0.5, "hedef_r": 0.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "tampon_atr": [0.0, 0.25, 0.5],
        "stop_atr": [0.5, 1.0],
        "hedef_r": [0.0, 1.5, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # VWAP ters kesişimi + gün sonu

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        seans = pd.Series(seans_kimligi(mumlar.index, p["seans_saat"]), index=mumlar.index)
        v = g.vwap_seans(y, d, k, mumlar["hacim"], seans.to_numpy())
        vw = v["vwap"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        ayni = seans == seans.shift(1)
        hazir = (v["mum_no"] > p["min_mum"]) & vw.notna() & atr.notna() & ayni
        tamp = p["tampon_atr"] * atr
        long_ok = hazir & (k > vw + tamp) & (k.shift(1) <= vw.shift(1) + tamp)
        short_ok = hazir & (k < vw - tamp) & (k.shift(1) >= vw.shift(1) - tamp) & bool(p["short"])
        if p["hacim_k"] > 0:
            ok = mumlar["hacim"] > p["hacim_k"] * mumlar["hacim"].shift(1).rolling(20, min_periods=20).mean()
            long_ok &= ok
            short_ok &= ok
        stop_l = vw - p["stop_atr"] * atr
        stop_s = vw + p["stop_atr"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        cikis = (((k > vw) & (k.shift(1) <= vw.shift(1))) | ((k < vw) & (k.shift(1) >= vw.shift(1)))) & ayni
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis,
                       gun_sonu=True, seans_saat=p["seans_saat"])
