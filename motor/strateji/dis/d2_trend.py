"""D2 / günlük-haftalık kural aileleri (TradingView): SOTT, SPY ayı rejimi, Vix Fix, Vol-Target trend, ONE MR1, haftada %1.

`dis__sott`, `dis__spy-ayi-short`, `dis__vixfix-stoch`, `dis__voltarget-trend`, `dis__one-mr1`, `dis__tasc-haftada-yuzde1`.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


def _atr_stop(mumlar, periyot, carpan):
    a = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], periyot)
    k = mumlar["kapanis"]
    return k - carpan * a, k + carpan * a


class Sott(Strateji):
    """Stochastic Optimized Trend Tracker (SOTT) (1d swing, hep piyasada).

    Kaynak: arsiv/strateji-sg/tv/pine/cJhpIJ2w.pine (Pine v4).
    Kural: stok(close,high,low,250) serisine VAR (Chande değişken ortalama, uzunluk 50) uygulanır, +1000 eklenir (src);
    src üzerinde OTT (VAR uzunluk 3, yüzde 0.618) hesaplanır. src, OTT[2]'yi (2 mum gecikmeli) yukarı keserse long, aşağı
    keserse short; zıt sinyal çevirir. Uyarlama: orijinalde stop yok -> ATR stop eklendi (stop_atr=3.0); çıkış = zıt
    sinyal. VAR/OTT Pine nz() gibi 0'dan başlar -> ilk periodK+3*smoothK mum ısınma (sinyal yok). TF belirtilmemiş -> 1d.
    Eski proje sonucu: kaldı: PF 2.89, Sharpe 0.72 (sott, 1d).
    """
    ad = "dis__sott"
    stil = "swing"
    varsayilan_parametreler = {"periyot_k": 250, "yumusatma_k": 50, "ott_periyot": 3, "ott_yuzde": 0.618,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"periyot_k": [150, 250], "yumusatma_k": [30, 50], "ott_yuzde": [0.618, 1.0],
                          "stop_atr": [2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        st = gd.pine_stoch(k, y, d, p["periyot_k"])
        kk = gd.var_ma(st, p["yumusatma_k"])
        src = kk + 1000.0
        o = gd.ott(src, p["ott_periyot"], p["ott_yuzde"])
        hazir = pd.Series(np.arange(len(k)) >= p["periyot_k"] + 3 * p["yumusatma_k"], index=k.index)
        gecik = o.shift(2)
        al = gd.kesis_yukari(src, gecik) & hazir
        sat = gd.kesis_asagi(src, gecik) & hazir
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        sig = cerceve(mumlar, al, sat & bool(p["short"]), sl, ss)
        return gd.yonlu_cerceve(sig, sat, al)


class SpyAyiShort(Strateji):
    """SPY Bear Regime Short System (1d swing, orijinal yalnız short).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/bA9UFcgj.pine.
    Kural (short): kapanış SMA250'nin en az %2 altında VE SMA5'in üstünde iken RSI(3) 70'i yukarı keserse short.
    Çıkış: kapanış SMA5'in altına iner veya SMA250'nin üstüne çıkar. Uyarlama: orijinalde stop yok -> ATR stop eklendi
    (stop_atr=3.0). long=True ayna kural (kapanış SMA250 üstünde ve %2 yukarıda, SMA5 altında, RSI(3) 30'u aşağı keser;
    çıkış: kapanış SMA5 üstüne çıkar ya da SMA250 altına iner); varsayılan kapalı. Orijinal SPY içindir (hisse/ETF).
    Eski proje sonucu: kaldı: PF 0.73, Sharpe -0.34 (spy_bear, 1d).
    """
    ad = "dis__spy-ayi-short"
    stil = "swing"
    varsayilan_parametreler = {"uzun_ma": 250, "kisa_ma": 5, "rsi_n": 3, "rsi_esik": 70.0, "bosluk_yuzde": 2.0,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": True, "long": False}
    parametre_izgarasi = {"uzun_ma": [200, 250], "rsi_esik": [65.0, 70.0, 80.0], "bosluk_yuzde": [0.0, 2.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = mumlar["kapanis"]
        uz, kz = g.sma(k, p["uzun_ma"]), g.sma(k, p["kisa_ma"])
        r = g.rsi(k, p["rsi_n"])
        gap = p["bosluk_yuzde"] / 100.0
        short_c = (k < uz) & (k > kz) & gd.kesis_yukari(r, p["rsi_esik"]) & (k <= uz * (1 - gap)) & bool(p["short"])
        long_c = (k > uz) & (k < kz) & gd.kesis_asagi(r, 100.0 - p["rsi_esik"]) & (k >= uz * (1 + gap)) & bool(p["long"])
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        sig = cerceve(mumlar, long_c, short_c, sl, ss)
        return gd.yonlu_cerceve(sig, (k > kz) | (k < uz), (k < kz) | (k > uz))


class VixfixStoch(Strateji):
    """Vix FIX / StochRSI Strategy (1d swing, orijinal yalnız long).

    Kaynak: arsiv/strateji-sg/tv/pine/TDxSLJRA.pine (Pine v4).
    Kural (long): Williams Vix Fix wvf = (HH(close,22) - low)/HH(close,22)*100 ve bandı (SMA20 + 2*std, ya da son 50
    wvf tepesinin %85'i). Önceki mumda wvf bandın üstündeydi ve şimdi altına indi ("filtreli") VE yükselen mum
    (low > önceki low ve close > önceki high) VE close > close[3] VE (close < close[40] veya close < close[14]) ise long;
    ya da "agresif" kol (close > önceki close ve > open, wvf hâlâ bandın üstünde). Çıkış: Stokastik(14,3,3) %K, %D'yi
    yukarı keserken %K > 80. Uyarlama: pyramiding=9 (ekleme) tek pozisyona indirgendi; orijinalde stop yok -> ATR stop
    eklendi (stop_atr=3.0). short=True ayna (tepe bulucu wvf_s = (high - LL(close,22))/LL(close,22)*100, aynı bant mantığı;
    düşen mum; close < close[3]; close > close[40] veya close > close[14]; çıkış: %K, %D'yi aşağı keserken %K < 20); varsayılan kapalı.
    Eski proje sonucu: kaldı: PF 3.44, Sharpe 0.49 (vixfix, 1d).
    """
    ad = "dis__vixfix-stoch"
    stil = "swing"
    varsayilan_parametreler = {"pd": 22, "bb_n": 20, "bb_carpan": 2.0, "lb": 50, "yuzdelik": 0.85, "uzun_lb": 40,
                               "orta_lb": 14, "guc": 3, "stoch_n": 14, "asiri_alim": 80.0,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"pd": [14, 22], "yuzdelik": [0.85, 0.95], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _wvf_durum(wvf, p):
        sd = p["bb_carpan"] * gd.pine_stdev(wvf, p["bb_n"])
        ust = g.sma(wvf, p["bb_n"]) + sd
        aralik = wvf.rolling(p["lb"], min_periods=p["lb"]).max() * p["yuzdelik"]
        once_yuksek = (wvf.shift(1) >= ust.shift(1)) | (wvf.shift(1) >= aralik.shift(1))
        simdi_alt = (wvf < ust) & (wvf < aralik)
        valid = ust.notna() & aralik.notna() & wvf.shift(1).notna()
        return once_yuksek & simdi_alt & valid, once_yuksek & ~simdi_alt & valid

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a_, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        hh = k.rolling(p["pd"], min_periods=p["pd"]).max()
        ll = k.rolling(p["pd"], min_periods=p["pd"]).min()
        f, fa = self._wvf_durum((hh - d) / hh * 100.0, p)
        up = (d > d.shift(1)) & (k > y.shift(1))
        up_a = (k > k.shift(1)) & (k > a_)
        gerek = (k > k.shift(p["guc"])) & ((k < k.shift(p["uzun_lb"])) | (k < k.shift(p["orta_lb"])))
        long_c = (up & gerek & f) | (up_a & gerek & fa)
        fs, fas = self._wvf_durum((y - ll) / ll * 100.0, p)
        dn = (y < y.shift(1)) & (k < d.shift(1))
        dn_a = (k < k.shift(1)) & (k < a_)
        gerek_s = (k < k.shift(p["guc"])) & ((k > k.shift(p["uzun_lb"])) | (k > k.shift(p["orta_lb"])))
        short_c = ((dn & gerek_s & fs) | (dn_a & gerek_s & fas)) & bool(p["short"])
        sk = g.sma(gd.pine_stoch(k, y, d, p["stoch_n"]), 3)
        sd = g.sma(sk, 3)
        cik_l = gd.kesis_yukari(sk, sd) & (sk > p["asiri_alim"])
        cik_s = gd.kesis_asagi(sk, sd) & (sk < 100.0 - p["asiri_alim"])
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        sig = cerceve(mumlar, long_c, short_c, sl, ss)
        return gd.yonlu_cerceve(sig, cik_l, cik_s)


class VoltargetTrend(Strateji):
    """Vol-Target Trend Engine (1d swing, orijinal yalnız long).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/2wyXTTMc.pine.
    Orijinal kural: rejim = kapanış > SMA200. Gerçekleşen oynaklık (20 günlük getiri std * sqrt(252)) hedef oynaklığın
    (%45) altındaysa tam maruziyet, üstündeyse hedef/gerçek oranında küçültülmüş maruziyet; haftalık yeniden dengeleme,
    rejim bozulunca (kapanış < SMA200) tam çıkış; maruziyet hedefin 1.5 katını aşarsa hızlı küçültme.
    Uyarlama: motor pozisyon büyüklüğünü risk (%1) üzerinden kendisi belirler, kademeli ekleme/çıkarma (pyramiding=500)
    kaldırıldı -> TEK pozisyon: long, rejim açılınca veya yeni haftanın ilk mumunda (ve pozisyon yoksa) girilir; çıkış =
    rejim bozulması ya da gerçekleşen oynaklık > hizli_k*hedef_vol (hızlı küçültmenin tek pozisyonlu karşılığı); aynı
    koşulda yeni giriş de yok. Orijinalde stop yok -> ATR stop eklendi (stop_atr=3.0). short=True ayna (kapanış < SMA;
    çıkış rejim yukarı dönünce); varsayılan kapalı. Yıllıklama günü yil_gun=252 (orijinal; kripto için 365 denenebilir).
    Eski proje sonucu: kaldı: PF 7.38, Sharpe 0.80 (vol_target, 1d).
    """
    ad = "dis__voltarget-trend"
    stil = "swing"
    varsayilan_parametreler = {"vol_n": 20, "hedef_vol": 45.0, "sma_n": 200, "hizli_k": 1.5, "yil_gun": 252,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"sma_n": [100, 150, 200], "hedef_vol": [30.0, 45.0, 60.0], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = mumlar["kapanis"]
        getiri = k / k.shift(1) - 1.0
        vol = gd.pine_stdev(getiri, p["vol_n"]) * np.sqrt(p["yil_gun"]) * 100.0
        sma = g.sma(k, p["sma_n"])
        boga, ayi = k > sma, k < sma
        hafta = pd.Series(gd.hafta_kimligi(mumlar.index), index=k.index)
        yeni_hafta = hafta != hafta.shift(1)
        sakin = vol <= p["hizli_k"] * p["hedef_vol"]
        long_c = boga & sakin & (yeni_hafta | ~boga.shift(1, fill_value=False))
        short_c = ayi & sakin & (yeni_hafta | ~ayi.shift(1, fill_value=False)) & bool(p["short"])
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        sig = cerceve(mumlar, long_c & vol.notna(), short_c & vol.notna(), sl, ss)
        return gd.yonlu_cerceve(sig, ~boga | ~sakin, ~ayi | ~sakin)


class OneMr1(Strateji):
    """ONEUSDT(1)_MR1 (1d swing, orijinal yalnız long).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/8I2576zL.pine.
    Kural (long): iki mumluk değişim d2(o) = (close[o]-close[o+2])/close[o+2]*100. Üç mum önceki 2 mumluk değişim
    -7 ile -5 arasında (>= -7 ve <= -5) VE bugünkü 2 mumluk değişim <= 0 ise long. Çıkış: close > önceki high VE
    önceki open <= close[9] (sinyal çıkışı) ya da ATR(14)*11 izleyen stop (girişte close - 11*ATR, her mum yukarı çekilir:
    CikisAyarlari.atr_iz_suren_k=11). Eski proje sonucu: kaldı: PF 1.50, Sharpe 0.69 (mr_2bar, 1d). Zaman dilimi
    belirtilmemiş (yazar tek kripto ONE için yazmış) -> 1d. short=True ayna (3 mum önce +5..+7, bugün >= 0;
    çıkış close < önceki low ve önceki open >= close[9]); varsayılan kapalı.
    """
    ad = "dis__one-mr1"
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=11.0, atr_periyot=14)
    varsayilan_parametreler = {"ust": 7.0, "alt": 5.0, "cikis_gecmis": 9, "stop_atr": 11.0, "atr_periyot": 14,
                               "short": False}
    parametre_izgarasi = {"ust": [7.0, 9.0], "alt": [4.0, 5.0, 6.0], "cikis_gecmis": [5, 9]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a_, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        d2 = (k - k.shift(2)) / k.shift(2) * 100.0          # d2(0)
        d2_3 = d2.shift(3)                                    # d2(3)
        long_c = (d2_3 >= -p["ust"]) & (d2 <= 0) & (d2_3 <= -p["alt"])
        short_c = (d2_3 <= p["ust"]) & (d2 >= 0) & (d2_3 >= p["alt"]) & bool(p["short"])
        cik_l = (k > y.shift(1)) & (a_.shift(1) <= k.shift(p["cikis_gecmis"]))
        cik_s = (k < d.shift(1)) & (a_.shift(1) >= k.shift(p["cikis_gecmis"]))
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        sig = cerceve(mumlar, long_c, short_c, sl, ss)
        return gd.yonlu_cerceve(sig, cik_l, cik_s)


class TascHaftadaYuzde1(Strateji):
    """TASC 2026.03 One Percent A Week (4h swing, orijinal yalnız long).

    Kaynak: arsiv/strateji-sg/tv/pine/nVECqIQx.pine.
    Kural (long): Pazartesi açılışının %1 altına limit alış; dolunca +%1 hedef; fiyat girişin %0.5 altına inerse başabaş
    limit çıkışı; haftanın son mumunda (Cuma kapanışı) çıkış. Uyarlama: motor limit emri vermez -> o haftanın açılışının
    (hafta ilk mumunun açılışı) %dip altına İLK kez dokunulan mumun (low <= seviye) KAPANIŞINDA sinyal, sonraki açılıştan
    giriş; hedef = sinyal kapanışı +%hedef; başabaş limiti kaldırıldı yerine ATR stop (stop_atr=3.0) eklendi; haftanın son
    mumunda (UTC Pazar kapanışı; kripto 7/24) zorunlu çıkış, son mumda yeni giriş yok. 4h seçildi (günlük/seans mantığı
    4h'ye uyarlandı). short=True ayna (açılışın %dip ÜSTÜNE dokunuş, hedef -%hedef); varsayılan kapalı.
    Eski proje sonucu: kaldı: PF 2.11, Sharpe 2.57 (one_pct_week, 1d hisse/ETF).
    """
    ad = "dis__tasc-haftada-yuzde1"
    stil = "swing"
    varsayilan_parametreler = {"dip_yuzde": 1.0, "hedef_yuzde": 1.0, "stop_atr": 3.0, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"dip_yuzde": [0.5, 1.0, 1.5], "hedef_yuzde": [0.5, 1.0, 2.0], "stop_atr": [2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        hafta = pd.Series(gd.hafta_kimligi(mumlar.index), index=k.index)
        son = pd.Series(gd.hafta_son_mumu(mumlar.index), index=k.index)
        acilis_h = mumlar["acilis"].groupby(hafta.to_numpy()).transform("first")
        dip, tepe = acilis_h * (1 - p["dip_yuzde"] / 100.0), acilis_h * (1 + p["dip_yuzde"] / 100.0)
        t_l, t_s = d <= dip, y >= tepe
        ilk_l = t_l & (t_l.astype(int).groupby(hafta.to_numpy()).cumsum() == 1) & ~son
        ilk_s = t_s & (t_s.astype(int).groupby(hafta.to_numpy()).cumsum() == 1) & ~son & bool(p["short"])
        sl, ss = _atr_stop(mumlar, p["atr_periyot"], p["stop_atr"])
        h = p["hedef_yuzde"] / 100.0
        sig = cerceve(mumlar, ilk_l, ilk_s, sl, ss, k * (1 + h), k * (1 - h), cikis=son)
        return sig
