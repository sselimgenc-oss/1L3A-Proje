"""D1 grubu (dış TradingView): Skyrexio "MultiLayer" ailesi — Alligator/fraktal trendi + AO/AC desenleri.

Üç orijinal de uzun yönlü ve kademeli (pyramiding=5) çalışır: trend (Alligator dişi + fraktal etkinleşme seviyeleri, bkz.
_gosterge_d1.williams_trend) yükselişteyken AO/AC deseninde aşamalı ekleme, trend dönünce tüm kademelerin kapanışı. Burada her biri TEK
pozisyona indirgenmiştir (ilk kademe); çıkış trend dönüşü (+1 -> -1) ve ATR stopudur. Orijinaller stopsuzdur (zararı yalnız trend
dönüşü keser) -> ATR stop (stop_atr) eklendi. Üçü de yalnız long; `short=True` ayna kurar (varsayılan kapalı). TF belirtilmiyor, 4h
varsayıldı. Stop-giriş emirleri (sinyal mumunun tepesine) kırılan mumun kapanışında sinyal + sonraki açılışta piyasa emri olarak uyarlandı.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d1 import alligator_dis, ao_ac, kur, williams_trend
from motor.strateji.temel import Strateji


def _stop_giris(fiyat_ust: np.ndarray, diff: np.ndarray, desen: np.ndarray) -> np.ndarray:
    """AC/AO deseni mumunun tepesine konan stop-giriş emri.

    Desen mumunda seviye = tepe. Sonraki mumlarda: tepe seviyenin altında kalıp diff > 0 ise seviye aşağı çekilir (yeniden kurulum);
    tepe seviyeyi aşarsa giriş tetiklenir ve seviye silinir; diff < 0 ise seviye silinir.
    Dönen: tetiklenme mumunda True (o mumun kapanışında bilinir)."""
    n = len(fiyat_ust)
    lv = np.nan
    tetik = np.zeros(n, dtype=bool)
    for i in range(n):
        onc = lv
        if desen[i]:
            lv = fiyat_ust[i]
        if not np.isnan(onc) and fiyat_ust[i] < onc and diff[i] > 0:
            lv = fiyat_ust[i]
        if not np.isnan(onc) and fiyat_ust[i] > onc:
            tetik[i] = True
            lv = np.nan
        elif diff[i] < 0:
            lv = np.nan
    return tetik


def _trend_donus(trend: pd.Series):
    onc = trend.shift(1, fill_value=0)
    return (onc == 1) & (trend == -1), (onc == -1) & (trend == 1)


class _SkyrexioTaban(Strateji):
    stil = "swing"
    varsayilan_parametreler = {"ema_n": 100, "atr_periyot": 14, "stop_atr": 3.0, "short": False}
    parametre_izgarasi = {"ema_n": [50, 100, 200], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True   # trend dönüşü

    def _giris(self, mumlar, trend, ema, ao, ac):
        raise NotImplementedError

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        trend = williams_trend(y, d)
        ema = g.ema(k, int(p["ema_n"]))
        osc = ao_ac(y, d)
        long_ok, short_ok = self._giris(mumlar, trend, ema, osc["ao"], osc["ac"])
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        c_l, c_s = _trend_donus(trend)
        return kur(mumlar, long_ok, short_ok & bool(p["short"]), k - sd, k + sd, cikis_l=c_l, cikis_s=c_s)


class AoAcBolgeleri(_SkyrexioTaban):
    """dis__ao-ac-bolgeleri: AO ve AC yükselirken yeşil bar serisinde giriş; trend dönünce ya da seri kırılınca kapanış.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/Tkrjao7P.pine (AO/AC Trading Zones Strategy [Skyrexio]).
    Yeşil bar = kapanış > Alligator dişi, AC > AC[1], AO > AO[1], kapanış > EMA(ema_n). Ardışık yeşil bar sayısı `min_yesil` ile `maks_yesil`
    arasında ve kapanış > önceki kapanış ise giriş (orijinal: 2..6 arası, en çok 5 kademe). Çıkış: trend +1 -> -1 dönüşü.
    Uyarlama: orijinaldeki "5. yeşil barın dibi = ortak stop" ilk kademe girişinde bilinmediğinden ATR stopla (stop_atr) değiştirildi;
    kademeler tek pozisyona indirgendi. Short aynası: kırmızı bar serisi.
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__ao-ac-bolgeleri"
    varsayilan_parametreler = {**_SkyrexioTaban.varsayilan_parametreler, "min_yesil": 2, "maks_yesil": 7}
    parametre_izgarasi = {"ema_n": [50, 100, 200], "min_yesil": [1, 2, 3], "stop_atr": [2.0, 3.0, 4.0]}

    @staticmethod
    def _sayac(kosul):
        kk = kosul.fillna(False).astype(bool)
        return kk.astype(int).groupby((~kk).cumsum()).cumsum()

    def _giris(self, mumlar, trend, ema, ao, ac):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        dis = alligator_dis(y, d)
        yesil = self._sayac((k > dis) & (ac > ac.shift(1)) & (ao > ao.shift(1)) & (k > ema))
        kirmizi = self._sayac((k < dis) & (ac < ac.shift(1)) & (ao < ao.shift(1)) & (k < ema))
        a, b = int(p["min_yesil"]), int(p["maks_yesil"])
        long_ok = (k > k.shift(1)) & (yesil >= a) & (yesil < b)
        short_ok = (k < k.shift(1)) & (kirmizi >= a) & (kirmizi < b)
        return long_ok, short_ok


class AcCokKatman(_SkyrexioTaban):
    """dis__ac-cok-katman: AC dönüş desenlerinde stop-giriş; fiyat EMA100 üstünde; trend dönünce tüm kademeler kapanır.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/ErcSuPyN.pine (MultiLayer Acceleration/Deceleration Strategy [Skyrexio]).
    Desen 1: AC > 0, AC > AC[1] > AC[2] ve AC[2] < AC[3] (pozitif bölgede yeniden yükseliş); Desen 2: AC < 0, AC 3 mum yükselip (AC[3]'ten
    sonra) dönüş (AC[3] < AC[4]). Trend +1 (Alligator/fraktal) ve kapanış > EMA(ema_n) iken desen mumunun tepesine stop-giriş kurulur;
    mum tepesini aşan ilk mumda giriş. Çıkış: trend +1 -> -1. Çok katmanlı (5 kademe) giriş tek pozisyona indirgendi (ilk tetik).
    Short aynası: desenler ters, trend -1, kapanış < EMA, stop-giriş mum dibinin altına.
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__ac-cok-katman"

    def _giris(self, mumlar, trend, ema, ao, ac):
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        a1, a2, a3, a4 = ac.shift(1), ac.shift(2), ac.shift(3), ac.shift(4)
        s1_l = (ac > 0) & (ac > a1) & (a1 > a2) & (a2 < a3)
        s2_l = (ac < 0) & (ac > a1) & (a1 > a2) & (a2 > a3) & (a3 < a4)
        s1_s = (ac < 0) & (ac < a1) & (a1 < a2) & (a2 > a3)
        s2_s = (ac > 0) & (ac < a1) & (a1 < a2) & (a2 < a3) & (a3 > a4)
        desen_l = ((s1_l | s2_l) & (trend == 1) & (k > ema)).to_numpy()
        desen_s = ((s1_s | s2_s) & (trend == -1) & (k < ema)).to_numpy()
        diff = ac.diff().fillna(0.0).to_numpy()
        tl = _stop_giris(y.to_numpy(float), diff, desen_l)
        ts = _stop_giris(-d.to_numpy(float), -diff, desen_s)
        return pd.Series(tl, index=k.index), pd.Series(ts, index=k.index)


class AoTabak(_SkyrexioTaban):
    """dis__ao-tabak: trend onayında AO tabak (saucer) deseninde sinyal tepesine stop-giriş; trend aşağı dönünce çıkış.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/HyzpDR9t.pine (MultiLayer Awesome Oscillator Saucer Strategy [Skyrexio]).
    Tabak: AO > 0, AO[1] > 0, AO[2] > 0, AO > AO[1] ve AO[1] < AO[2] (iki bar düşüş, sonra yükseliş); trend +1 ve kapanış > EMA(ema_n).
    Sinyal mumunun tepesine stop-giriş; aşılınca giriş, seviye AO yükselirken aşağı çekilir, AO düşerse silinir. Çıkış: trend +1 -> -1.
    Çok katmanlı giriş tek pozisyona indirgendi. Short aynası: AO < 0 ters tabak, trend -1, kapanış < EMA.
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__ao-tabak"

    def _giris(self, mumlar, trend, ema, ao, ac):
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        a1, a2 = ao.shift(1), ao.shift(2)
        tabak_l = (ao > a1) & (a1 < a2) & (ao > 0) & (a1 > 0) & (a2 > 0)
        tabak_s = (ao < a1) & (a1 > a2) & (ao < 0) & (a1 < 0) & (a2 < 0)
        desen_l = (tabak_l & (trend == 1) & (k > ema)).to_numpy()
        desen_s = (tabak_s & (trend == -1) & (k < ema)).to_numpy()
        diff = ao.diff().fillna(0.0).to_numpy()
        tl = _stop_giris(y.to_numpy(float), diff, desen_l)
        ts = _stop_giris(-d.to_numpy(float), -diff, desen_s)
        return pd.Series(tl, index=k.index), pd.Series(ts, index=k.index)
