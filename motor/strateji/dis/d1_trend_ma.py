"""D1 grubu (dış TradingView): Heikin Ashi/RSI, MA-CCI, ATR-RSI, KAMA, HMA, EMA±ATR bant stratejileri.

Hepsi OHLCV tabanlıdır, tek pozisyon, stop zorunlu. Pine'daki yüzde bazlı izleyen stoplar motorun ATR izleyen
stopuna (CikisAyarlari.atr_iz_suren_k) yaklaştırılmıştır; ayrıntı her sınıfın docstring'inde.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import hma, kama, kur
from motor.strateji.gostergeler_b1 import ardisik_sayac
from motor.strateji.gostergeler_b2 import cci as _cci_b2, heikin_ashi
from motor.strateji.temel import Strateji


def _ust_kesis(a, b):
    if np.isscalar(b):
        return (a > b) & (a.shift(1) <= b)
    return (a > b) & (a.shift(1) <= b.shift(1))


def _alt_kesis(a, b):
    if np.isscalar(b):
        return (a < b) & (a.shift(1) >= b)
    return (a < b) & (a.shift(1) >= b.shift(1))


class BchHaRsiFade(Strateji):
    """dis__bch-ha-rsi-fade: 15m. RSI(100) > 46 iken 7 ardışık yükselen Heikin Ashi mumundan sonra SHORT (güce karşı).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/nuqVC5F7.pine ([3Commas] BCH Heikin Ashi RSI Fade - Short).
    Kural: HA mumları (close>open) ardışık `ha_seri` kez ve RSI(rsi_periyot) > rsi_seviye -> short; hedef %2.1 aşağı,
    stop %2.5 yukarı (girişten). Orijinalde ek emir/DCA yok ("base order tüm pozisyon").
    Uyarlama: Pine'daki request.security (15m HA + 15m RSI, lookahead_off) burada veri zaten 15m olduğundan doğrudan
    hesaplanır, kapanmış mumla çalışır. Orijinal yalnız short; `long=True` ayna kurar (ardışık düşen HA + RSI <
    100-rsi_seviye), varsayılan kapalı. Tarih penceresi/webhook/limit-emir seçeneği alınmadı (piyasa emri).
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__bch-ha-rsi-fade"
    stil = "scalp"
    varsayilan_parametreler = {"rsi_periyot": 100, "rsi_seviye": 46.0, "ha_seri": 7,
                               "hedef_yuzde": 2.1, "stop_yuzde": 2.5, "long": False}
    parametre_izgarasi = {"ha_seri": [5, 7, 9], "rsi_seviye": [40.0, 46.0, 52.0], "hedef_yuzde": [1.5, 2.1, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit yüzde hedef

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ha = heikin_ashi(mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], k)
        boga = ardisik_sayac(ha["ha_kapanis"] > ha["ha_acilis"])
        ayi = ardisik_sayac(ha["ha_kapanis"] < ha["ha_acilis"])
        rsi = g.rsi(k, int(p["rsi_periyot"]))
        n = int(p["ha_seri"])
        short_ok = (boga >= n) & (rsi > p["rsi_seviye"])
        long_ok = (ayi >= n) & (rsi < 100.0 - p["rsi_seviye"]) & bool(p["long"])
        s, h = p["stop_yuzde"] / 100.0, p["hedef_yuzde"] / 100.0
        return kur(mumlar, long_ok, short_ok, k * (1 - s), k * (1 + s), k * (1 + h), k * (1 - h))


class MaCciTrailing(Strateji):
    """dis__ma-cci-trailing: 1h. SMA24, SMA31'i AŞAĞI keserken ve CCI(11) -80'i aşağı keserken (3 mum içinde) LONG.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/d117dN6D.pine ([3Commas] MA-CCI Trailing Long).
    Kural: MA aşağı kesişimi ve CCI aşağı kesişimi `canli` mum içinde birlikte gerçekleşmeli ve en az biri bu mumda
    olmalı (AND + keep-alive). Stop %3.25. Orijinal çıkış: kâr %1.5'e ulaşınca izleyen stop (sapma %0.05) devreye girer;
    sapma o kadar dar ki fiilen ~%1.5 kâr al'dır -> burada sabit %1.5 hedef.
    Uyarlama: Pine'daki [1] + lookahead_on'lu MA değerleri yalnız çizim içindir; sinyal lookahead_off kesişimdir ->
    burada kapanmış 1h mumunda hesaplanır. Orijinal yalnız long; `short=True` ayna kurar (SMA yukarı kesişim + CCI
    +80 yukarı kesişim), varsayılan kapalı. Gün sonu zorunlu çıkış (1h = daytrade).
    Eski sonuç: kaldı: PF 0.80, Sharpe -0.35 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/ma_cci_trail.json).
    """
    ad = "dis__ma-cci-trailing"
    stil = "daytrade"
    varsayilan_parametreler = {"hizli": 24, "yavas": 31, "cci_periyot": 11, "cci_esik": -80.0, "canli": 3,
                               "stop_yuzde": 3.25, "hedef_yuzde": 1.5, "short": False, "seans_saat": 0.0}
    parametre_izgarasi = {"hizli": [20, 24, 28], "cci_esik": [-100.0, -80.0, -60.0], "canli": [2, 3, 4]}

    def cikis_var_mi(self) -> bool:
        return True   # hedef + gün sonu

    @staticmethod
    def _canli(olay: pd.Series, n: int) -> pd.Series:
        pos = pd.Series(np.arange(len(olay), dtype=float), index=olay.index)
        son = pos.where(olay.fillna(False).astype(bool)).ffill()
        return (pos - son) <= n

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        f, s = g.sma(k, int(p["hizli"])), g.sma(k, int(p["yavas"]))
        cci = _cci(y, d, k, int(p["cci_periyot"]))
        n = int(p["canli"])
        ma_a, cci_a = _alt_kesis(f, s), _alt_kesis(cci, p["cci_esik"])
        ma_y, cci_y = _ust_kesis(f, s), _ust_kesis(cci, -p["cci_esik"])
        long_ok = self._canli(ma_a, n) & self._canli(cci_a, n) & (ma_a | cci_a)
        short_ok = (self._canli(ma_y, n) & self._canli(cci_y, n) & (ma_y | cci_y)) & bool(p["short"])
        sl, h = p["stop_yuzde"] / 100.0, p["hedef_yuzde"] / 100.0
        return kur(mumlar, long_ok, short_ok, k * (1 - sl), k * (1 + sl), k * (1 + h), k * (1 - h),
                   gun_sonu=True, seans_saat=p["seans_saat"])


def _cci(y, d, k, n):
    return _cci_b2(y, d, k, n)


class AtrRsiLiwei(Strateji):
    """dis__atr-rsi-liwei: 1h. ATR oynaklık bandında RSI(15) > 60 ise LONG, < 40 ise SHORT.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/mqh6UJ9p.pine (ATR_RSI_Strategy v2 [liwei666]).
    Kural: ATR(26) > SMA(ATR,45) ve SMA(ATR,45)/kapanış*100 in [0.3, 0.7] iken RSI(15) > 50+rsi_esik -> long,
    < 50-rsi_esik -> short. Hedef: long +%3, short -%6 (orijinaldeki asimetri korundu). Stop: girişten %1.5.
    Uyarlama: orijinal stop tepeden/dipten %1.5 izleyen stoptur; burada ilk stop girişten %iz_yuzde, izleme motorun ATR
    izleyen stopuna (k=2) yaklaştırıldı (yüzde izleme motorda yok). Orijinaldeki limit emri (close±5 puan)
    piyasa emrine çevrildi. Pyramiding yok. Gün sonu zorunlu çıkış (1h = daytrade).
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__atr-rsi-liwei"
    stil = "daytrade"
    varsayilan_parametreler = {"atr_periyot": 26, "atr_ort": 45, "rsi_periyot": 15, "rsi_esik": 10.0,
                               "norm_min": 0.3, "norm_maks": 0.7, "iz_yuzde": 1.5,
                               "hedef_long": 3.0, "hedef_short": 6.0, "seans_saat": 0.0}
    parametre_izgarasi = {"rsi_esik": [5.0, 10.0, 15.0], "norm_min": [0.2, 0.3, 0.4], "iz_yuzde": [1.0, 1.5, 2.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.0)

    def cikis_var_mi(self) -> bool:
        return True   # hedef + izleyen stop + gün sonu

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        atr_ma = g.sma(atr, int(p["atr_ort"]))
        norm = atr_ma / k * 100.0
        rsi = g.rsi(k, int(p["rsi_periyot"]))
        ok = (norm >= p["norm_min"]) & (norm <= p["norm_maks"]) & (atr > atr_ma)
        long_ok = ok & (rsi > 50 + p["rsi_esik"])
        short_ok = ok & (rsi < 50 - p["rsi_esik"]) & ~long_ok
        s = p["iz_yuzde"] / 100.0
        return kur(mumlar, long_ok, short_ok, k * (1 - s), k * (1 + s),
                   k * (1 + p["hedef_long"] / 100.0), k * (1 - p["hedef_short"] / 100.0),
                   gun_sonu=True, seans_saat=p["seans_saat"])


class AuroraKama(Strateji):
    """dis__aurora-kama: 4h. KAMA(10,2,30) 3 mumdur yükseliyor ve kapanış SMA200 üstündeyse LONG; düşüyor ve altındaysa SHORT.

    Kaynak: arsiv/strateji-sg/tv/pine/kbYTJ8V2.pine (Aurora KAMA Trend).
    Kural: KAMA `yukselen` mum üst üste yükselirse (ve fiyat > SMA) long; düşerse (ve fiyat < SMA) short; ters sinyalde
    pozisyon döner. Stop girişten %4.
    Uyarlama: orijinaldeki %6 izleyen stop (5 mum gecikmeli) yüzde bazlı olduğu için motorun ATR izleyen stopuna
    (k=4 ~ 4h'de %6) yaklaştırıldı; gecikme ve "girişler arası en az 5 mum" bekleme alınmadı (motor bilgisi yok).
    Ters (short) sinyali long'un çıkışıdır; `short=False` yapılsa da long çıkışı (KAMA düşüşü + SMA altı) kalır.
    Eski sonuç: kaldı: PF 1.00, Sharpe 0.47 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/kama_trend.json).
    """
    ad = "dis__aurora-kama"
    stil = "swing"
    varsayilan_parametreler = {"er_periyot": 10, "hizli": 2, "yavas": 30, "yukselen": 3, "sma_periyot": 200,
                               "stop_yuzde": 4.0, "short": True}
    parametre_izgarasi = {"er_periyot": [8, 10, 14], "yukselen": [2, 3, 4], "sma_periyot": [100, 200, 300]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=4.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        kv = kama(k, int(p["er_periyot"]), int(p["hizli"]), int(p["yavas"]))
        n = int(p["yukselen"])
        yuk = (kv.diff() > 0).astype(int).rolling(n, min_periods=n).sum() == n
        dus = (kv.diff() < 0).astype(int).rolling(n, min_periods=n).sum() == n
        sma = g.sma(k, int(p["sma_periyot"]))
        long_ok = yuk & (k > sma)
        sat = dus & (k < sma)
        s = p["stop_yuzde"] / 100.0
        return kur(mumlar, long_ok, sat & bool(p["short"]), k * (1 - s), k * (1 + s),
                   cikis_l=sat, cikis_s=long_ok)


class HmaAtrRider(Strateji):
    """dis__hma-atr-rider: 1d. HMA(8) > HMA(9) > HMA(20) rejimi YENİ başlarsa LONG; izleyen stopla çıkış.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/jd1KSVn7.pine (BIST30 to S&P 500 - ATR Momentum Rider).
    Kural: rejim (hizli>orta>yavas) önceki mumda yoksa ve HMA(20)'nin 3 mumluk eğimi / ATR >= -0.18 ise long.
    Orijinal çıkış (K1): zirveden MFE >= 1.5 ATR olunca zirveden %5.75 geri çekilmede kapanış (4 seans bekleme).
    Uyarlama: orijinalde ilk stop yok -> ATR stop (stop_atr x ATR) eklendi; K1'in yüzde izleyen stopu motorun ATR
    izleyen stopuna (k=2) yaklaştırıldı (günlükte %5.75 ~ 2 ATR). Piramitleme (pyramiding=2, ikinci kademe) tek pozisyona
    indirgendi. Orijinal yalnız long; `short=True` ayna kurar (rejim hizli<orta<yavas, eğim <= +0.18), varsayılan kapalı.
    Eski sonuç: kaldı: PF 1.79, Sharpe 1.35 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/atr_rider.json).
    """
    ad = "dis__hma-atr-rider"
    stil = "swing"
    varsayilan_parametreler = {"hizli": 8, "orta": 9, "yavas": 20, "atr_periyot": 14, "egim_min": -0.18,
                               "stop_atr": 3.0, "short": False}
    parametre_izgarasi = {"yavas": [15, 20, 30], "egim_min": [-0.3, -0.18, 0.0], "stop_atr": [2.0, 3.0, 4.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        hf, hm, hs = hma(k, int(p["hizli"])), hma(k, int(p["orta"])), hma(k, int(p["yavas"]))
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        egim = (hs - hs.shift(3)) / 3.0 / atr
        boga, ayi = (hf > hm) & (hm > hs), (hf < hm) & (hm < hs)
        long_ok = boga & ~boga.shift(1, fill_value=False) & (egim >= p["egim_min"])
        short_ok = ayi & ~ayi.shift(1, fill_value=False) & (egim <= -p["egim_min"]) & bool(p["short"])
        return kur(mumlar, long_ok, short_ok, k - p["stop_atr"] * atr, k + p["stop_atr"] * atr)


class KellyAtrBant(Strateji):
    """dis__kelly-atr-bant: 4h. Fiyat EMA(20) ± 1.0*ATR(10) bandının üstünü yukarı keserse LONG, altını aşağı keserse SHORT.

    Kaynak: arsiv/strateji-sg/tv/pine/bFXf4IXh.pine (Built-in Kelly ratio for position sizing).
    Kural: crossover(kapanış, üst bant) -> long; crossunder(kapanış, alt bant) -> short; ters kesişim pozisyonu döndürür.
    Uyarlama: orijinal giriş "stop-al" emridir (kesişim mumunun high/low ± 1 tick, iptal koşulları var) -> burada kesişim
    mumunun kapanışında sinyal, sonraki açılışta piyasa emri. Kelly oranıyla boyutlandırma ÇEVRİLMEDİ (motor riske göre
    boyutlandırır). Orijinalde TP/SL kapalı -> ATR stop (stop_atr) eklendi; çıkış ters kesişimdir (`short=False` olsa da
    long ters kesişimle kapanır).
    Eski sonuç: kaldı: PF 2.51, Sharpe 0.81 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/kelly_bands.json).
    """
    ad = "dis__kelly-atr-bant"
    stil = "swing"
    varsayilan_parametreler = {"uzunluk": 20, "carpan": 1.0, "atr_periyot": 10, "ussel": True,
                               "stop_atr": 2.0, "short": True}
    parametre_izgarasi = {"uzunluk": [10, 20, 40], "carpan": [0.75, 1.0, 1.5], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["uzunluk"])
        orta = g.ema(k, n) if p["ussel"] else g.sma(k, n)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        ust, alt = orta + p["carpan"] * atr, orta - p["carpan"] * atr
        up, dn = _ust_kesis(k, ust), _alt_kesis(k, alt)
        return kur(mumlar, up, dn & bool(p["short"]), k - p["stop_atr"] * atr, k + p["stop_atr"] * atr,
                   cikis_l=dn, cikis_s=up)
