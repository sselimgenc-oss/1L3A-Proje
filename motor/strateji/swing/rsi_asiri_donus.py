"""swing__rsi-asiri-donus: RSI aşırı satım/alım bölgesinden dönüşte ortalamaya dönüş girişi. Stil alt sınıfları:
scalp/rsi_asiri_donus.py (15m), daytrade/rsi_asiri_donus.py (1h + gün sonu).

Kural: osilatör (gosterge="rsi": RSI(rsi_periyot); "demarker": DeMarker(rsi_periyot)*100) `alt` (30) altına inip yukarı keserse
long ("geri_cikis"); mod="bolgede": osilatör `alt`'ın altına YENİ girdiğinde (RSI(2)<10 türü). Short ayna: `100-alt` (70) üstünden
aşağı kesişim / bölgeye yeni giriş. Filtreler (0 = kapalı): trend_ma>0 -> long yalnız kapanış > EMA(trend_ma), short < EMA
(kartlar: "trend yönü"); adx_max>0 -> ADX < adx_max (kart rsi7-aralik: range piyasası, ADX<25); vo_esik>0 -> son 3 mumda
Hacim Osilatörü (EMA5/EMA20) <= -vo_esik (long; short için >= +vo_esik) (kart rsi-hacim-osilator-dip: +-%30).
Stop: son stop_n mumun dibi/zirvesi -/+ stop_tampon_atr*ATR, risk <= stop_max_atr ATR. Çıkış: osilatör `cikis_rsi` (50)
seviyesini long için yukarı, short için aşağı keser; `cikis` yön-bağımsız temel arayüzde olduğundan iki kesişim de listelenir.
cikis_rsi=0: yalnız ters sinyalde çıkış (kart rsi2-90-10 "her zaman içeride", stopsuz kart; burada geniş ATR stop zorunlu).
Hedef: hedef_r>0 ise R katı.
Kaynak kartlar: swing: scalp__rsi2-90-10-her-zaman-icerde__schroder, swing__rsi-30-70-ortalama-donus__jordan,
swing__rsi30-geri-donus__johnson; scalp: daytrade__rsi-hacim-osilator-dip__singhal, scalp__rsi-aralik-ticareti-1dk__schroder,
scalp__rsi7-aralik__stevenson; daytrade: swing__demarker-asiri-bolge__day (DeMarker 0.3/0.7).
Kodlanmadı/yaklaşık: Jordan'ın yükselen/düşen piyasada 80/40 - 60/20 asimetrik eşikleri (simetrik tutuldu); Schroder/Stevenson'ın
yatay destek/direnç yakınlığı (aralık sınırı) yok; "modifiye RSI" belirsiz -> standart Wilder RSI. 1m kaynaklı kartlar 15m'ye taşındı.
Negatif kanıt: arşiv §3 "Ortalamaya dönüş 4S/1G (Bollinger/RSI/IBS)" ve "1S RSI/BB geri çekilme (PF<1)" başarısız.
Bu aile zayıf prior ile test edilir.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class RsiAsiriDonus(Strateji):
    ad = "swing__rsi-asiri-donus"
    stil = "swing"
    _gun_sonu = False
    varsayilan_parametreler = {
        "gosterge": "rsi", "rsi_periyot": 14, "alt": 30.0, "mod": "geri_cikis", "trend_ma": 0,
        "adx_max": 0.0, "vo_esik": 0.0, "cikis_rsi": 50.0,
        "stop_n": 10, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 0.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "rsi_periyot": [2, 7, 14],
        "alt": [10.0, 20.0, 30.0],
        "trend_ma": [0, 200],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["rsi_periyot"])
        if p["gosterge"] == "rsi":
            r = g.rsi(k, n)
        elif p["gosterge"] == "demarker":
            r = 100.0 * b.demarker(y, d, n)
        else:
            raise ValueError(f"Bilinmeyen gosterge: {p['gosterge']}")
        atr = g.atr(y, d, k, p["atr_periyot"])
        alt, ust = p["alt"], 100.0 - p["alt"]
        if p["mod"] == "geri_cikis":
            long_ok, short_ok = b.yukari_kesis(r, alt), b.asagi_kesis(r, ust)
        elif p["mod"] == "bolgede":
            long_ok, short_ok = b.gecis(r < alt), b.gecis(r > ust)
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        if p["trend_ma"]:
            ema = g.ema(k, int(p["trend_ma"]))
            long_ok, short_ok = long_ok & (k > ema), short_ok & (k < ema)
        if p["adx_max"]:
            long_ok = long_ok & (g.adx(y, d, k, 14)["adx"] < p["adx_max"])
            short_ok = short_ok & (g.adx(y, d, k, 14)["adx"] < p["adx_max"])
        if p["vo_esik"]:
            vo = b.hacim_osilatoru(mumlar["hacim"])
            long_ok = long_ok & (vo.rolling(3, min_periods=1).min() <= -p["vo_esik"])
            short_ok = short_ok & (vo.rolling(3, min_periods=1).max() >= p["vo_esik"])
        gecerli = atr.notna() & r.notna()
        long_ok, short_ok = long_ok.fillna(False) & gecerli, short_ok.fillna(False) & gecerli & bool(p["short"])
        if p["cikis_rsi"]:
            cikis = (b.yukari_kesis(r, p["cikis_rsi"]) | b.asagi_kesis(r, 100.0 - p["cikis_rsi"])) & gecerli
        else:
            cikis = long_ok | short_ok
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis,
                       gun_sonu=self._gun_sonu, seans_saat=p["seans_saat"])
