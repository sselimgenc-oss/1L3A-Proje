"""D2 / sıkışma ve RSI sıkışması aileleri (TradingView).

`dis__sqz-donus`, `dis__rsi-t3-sqz`, `dis__rsi-coil`.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula
from motor.strateji.temel import Strateji


class SqzDonus(Strateji):
    """Squeeze Momentum on Reversal Strategy (1d swing, hep piyasada).

    Kaynak: arsiv/strateji-sg/tv/pine/Fckzv8iH.pine (Pine v3/v4).
    Kural: LazyBear sıkışma momentumu `val` (linreg(kapanış - (orta(HH,LL)+SMA)/2, 20)). val < -guc ve yukarı dönüyorsa
    (val > önceki) long; val > +guc ve aşağı dönüyorsa (val < önceki) short; zıt sinyal pozisyonu çevirir (hep piyasada).
    Uyarlama: orijinalde stop yok -> ATR stop eklendi (stop_atr=3.0). Çıkış: zıt sinyal (yönlü). `guc` (0.0018) orijinalde
    FİYAT BİRİMİDİR (forex ölçeği); kripto/hisse fiyatlarında fiilen sıfıra yakın eşiktir, aynen korundu (ızgarada
    0 ve fiyatın %0.1'i yok; yalnız orijinal değer ve 0). Bollinger sapması orijinalde de multKC (1.5) ile çarpılır.
    TF belirtilmemiş -> 1d. Eski proje sonucu: kaldı: PF 0.77, Sharpe 0.38 (sq_reversal, 1d).
    """
    ad = "dis__sqz-donus"
    stil = "swing"
    varsayilan_parametreler = {"uzunluk": 20, "bb_carpan": 1.5, "kc_carpan": 1.5, "guc": 0.0018,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"uzunluk": [14, 20, 27], "guc": [0.0, 0.0018], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        v = gd.sikisma_momentum(y, d, k, p["uzunluk"], p["bb_carpan"], p["uzunluk"], p["kc_carpan"])["val"]
        long_c = (v < -p["guc"]) & (v > v.shift(1))
        short_c = (v > p["guc"]) & (v < v.shift(1))
        a = g.atr(y, d, k, p["atr_periyot"])
        sig = cerceve(mumlar, long_c, short_c & bool(p["short"]), k - p["stop_atr"] * a, k + p["stop_atr"] * a)
        return gd.yonlu_cerceve(sig, short_c, long_c)


class RsiT3Sqz(Strateji):
    """RSI-Adaptive T3 + Squeeze Momentum Strategy (1d swing).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/7UNWrm2O.pine.
    Kural: RSI'ye göre uzunluğu (5-50) değişen T3 (hacim faktörü 0.7) kendi bir önceki değerini yukarı keser (t3 > t3[1],
    t3[1] <= t3[2]), sıkışma momentumu val > 0 ve sıkışma kapalı (sqzOff) ise long; aşağı kesip val < 0 ve sqzOff ise short.
    Zıt sinyal pozisyonu çevirir. Uyarlama: orijinalde stop ve ayrı çıkış yok -> ATR stop eklendi (stop_atr=3.0);
    çıkış = zıt tam sinyal (yönlü). BB sapması orijinalde de multKC ile çarpılır; BB uzunluğu 27, KC 20.
    TF belirtilmemiş -> 1d. Eski proje sonucu: kaldı: PF 2.24, Sharpe 0.63 (t3_sqz, 1d).
    """
    ad = "dis__rsi-t3-sqz"
    stil = "swing"
    varsayilan_parametreler = {"rsi_n": 14, "min_len": 5, "max_len": 50, "v": 0.7, "bb_n": 27, "kc_n": 20,
                               "kc_carpan": 1.5, "stop_atr": 3.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"min_len": [5, 8], "max_len": [34, 50], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        t3 = gd.t3_rsi_uyarlamali(k, p["rsi_n"], p["min_len"], p["max_len"], p["v"])
        sq = gd.sikisma_momentum(y, d, k, p["bb_n"], p["kc_carpan"], p["kc_n"], p["kc_carpan"])
        yukari = (t3 > t3.shift(1)) & (t3.shift(1) <= t3.shift(2))
        asagi = (t3 < t3.shift(1)) & (t3.shift(1) >= t3.shift(2))
        long_c = yukari & (sq["val"] > 0) & sq["sqz_off"]
        short_c = asagi & (sq["val"] < 0) & sq["sqz_off"]
        a = g.atr(y, d, k, p["atr_periyot"])
        sig = cerceve(mumlar, long_c, short_c & bool(p["short"]), k - p["stop_atr"] * a, k + p["stop_atr"] * a)
        return gd.yonlu_cerceve(sig, short_c, long_c)


class RsiCoil(Strateji):
    """RSI Range Compression (Momentum Coil Breakout) (1h daytrade).

    Kaynak: arsiv/strateji-sg/tv/pine/dwgn7hrE.pine.
    Kural: RSI(14)'ün son 20 mumdaki aralığı (HH-LL), son 100 aralığa göre yüzdelik sıralamada <= %20 ise "sıkışma";
    son 5 mum içinde sıkışma görüldüyse ve RSI önceki 20 mumluk RSI tepesini yukarı keserse (EMA50 son 5 mumda yükseliyor,
    ADX(14) >= 15) long; RSI dibi aşağı keser ve EMA50 düşüyorsa short. Stop = ATR(14)*2, hedef = 2R.
    Uyarlama: Pine'daki hedef hatası (long hedefi `close + stopPrice*R`) düzeltilmiştir: hedef = giriş +/- R*stop mesafesi.
    1h seçildi (belirtilmemiş); UTC gün sonu zorunlu çıkış eklendi (daytrade kuralı).
    Eski proje sonucu: kaldı: PF 1.13, Sharpe 0.91 (rsi_coil, 1h).
    """
    ad = "dis__rsi-coil"
    stil = "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "sikisma_n": 20, "yuzdelik_n": 100, "yuzdelik_esik": 20.0,
                               "bellek": 5, "ema_n": 50, "egim_n": 5, "adx_n": 14, "adx_min": 15.0,
                               "atr_periyot": 14, "stop_atr": 2.0, "hedef_r": 2.0, "short": True}
    parametre_izgarasi = {"yuzdelik_esik": [10.0, 20.0, 30.0], "stop_atr": [1.5, 2.0, 3.0], "hedef_r": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit R hedefi + gün sonu

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        r = g.rsi(k, p["rsi_n"])
        rh = r.rolling(p["sikisma_n"], min_periods=p["sikisma_n"]).max()
        rl = r.rolling(p["sikisma_n"], min_periods=p["sikisma_n"]).min()
        sikisma = gd.pine_percentrank(rh - rl, p["yuzdelik_n"]) <= p["yuzdelik_esik"]
        taze = gd.mum_sayaci(sikisma) <= p["bellek"]
        ema = g.ema(k, p["ema_n"])
        adx = g.adx(y, d, k, p["adx_n"])["adx"]
        adx_ok = adx >= p["adx_min"]
        long_c = gd.kesis_yukari(r, rh.shift(1)) & taze & (ema > ema.shift(p["egim_n"])) & adx_ok
        short_c = gd.kesis_asagi(r, rl.shift(1)) & taze & (ema < ema.shift(p["egim_n"])) & adx_ok & bool(p["short"])
        a = g.atr(y, d, k, p["atr_periyot"])
        sl, ss = k - p["stop_atr"] * a, k + p["stop_atr"] * a
        sig = cerceve(mumlar, long_c, short_c, sl, ss,
                      k + p["hedef_r"] * (k - sl), k - p["hedef_r"] * (ss - k))
        return gun_sonu_uygula(sig)
