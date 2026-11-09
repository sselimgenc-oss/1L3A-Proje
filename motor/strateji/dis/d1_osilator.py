"""D1 grubu (dış TradingView): filtre/osilatör tabanlı stratejiler.

Gaussian kanal, KST, Laguerre RSI, LUBE (sürtünme), Bilateral Stokastik ve çok zaman dilimli momentum yığını.
Hepsi OHLCV tabanlı ve nedensel (çok zaman dilimi yalnız KAPANMIŞ üst mumlarla: htf.ust_zaman).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d1 import choppiness, gauss_kutup, laguerre, kst, linreg, smma, kur
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


def _ust(a, b):
    b1 = b if np.isscalar(b) else b.shift(1)
    return (a > b) & (a.shift(1) <= b1)


def _alt(a, b):
    b1 = b if np.isscalar(b) else b.shift(1)
    return (a < b) & (a.shift(1) >= b1)


def _son_olay_mesafesi(olay: pd.Series) -> pd.Series:
    """Pine ta.barssince: olaydan bu yana geçen mum sayısı (olay mumunda 0; hiç olmadıysa NaN)."""
    pos = pd.Series(np.arange(len(olay), dtype=float), index=olay.index)
    return pos - pos.where(olay.fillna(False).astype(bool)).ffill()


class GaussKanal(Strateji):
    """dis__gauss-kanal: fiyat Gaussian orta çizgiyi yukarı keserse LONG, aşağı keserse SHORT (filtrelenmiş TR bandı).

    Kaynak: arsiv/strateji-sg/tv/pine/erJi1tWf.pine (Gaussian Channel Strategy).
    Kural: hlc3 kaynağına 4 kutuplu Gauss filtresi (örnekleme periyodu 144) = orta çizgi; gerçek aralığın (TR) aynı filtresi x 1.414 =
    bant (yalnız çizim; sinyalde orta çizgi kullanılır). Long: hlc3 orta çizgiyi yukarı keser VEYA son `geri` mum içinde
    kesmiş ve hâlâ üstünde ("geç giriş"); short aynası. Ters sinyal pozisyonu döndürür.
    Uyarlama: filtre sıfırdan başlar ve yakınsar -> ilk 3 x periyot mumda sinyal verilmez (Pine'da bu bölgede sahte kesişim olur).
    Orijinalde stop yok -> ATR stop (stop_atr) eklendi. Hızlı/gecikmesiz mod ve bant sinyal seçenekleri alınmadı.
    Eski sonuç: kaldı: PF 2.54, Sharpe 0.76 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/gaussian.json).
    """
    ad = "dis__gauss-kanal"
    stil = "swing"
    varsayilan_parametreler = {"kutup": 4, "periyot": 144, "geri": 3, "atr_periyot": 14, "stop_atr": 3.0, "short": True}
    parametre_izgarasi = {"periyot": [100, 144, 200], "kutup": [3, 4, 5], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        src = (y + d + k) / 3.0
        filt = gauss_kutup(src, int(p["kutup"]), int(p["periyot"]))
        up, dn = _ust(src, filt), _alt(src, filt)
        gm = int(p["geri"])
        long_c = up | ((src > filt) & (_son_olay_mesafesi(up) <= gm))
        short_c = dn | ((src < filt) & (_son_olay_mesafesi(dn) <= gm))
        isin = pd.Series(np.arange(len(k)) >= 3 * int(p["periyot"]), index=k.index)
        long_c, short_c = long_c & isin, short_c & isin
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, long_c, short_c & bool(p["short"]), k - sd, k + sd, cikis_l=short_c, cikis_s=long_c)


class KstSkyrexio(Strateji):
    """dis__kst-skyrexio: KST sinyal çizgisini yukarı keser, fiyat LSMA200 ve Alligator çenesi üstündeyse LONG; 1.5 ATR stop, 3.5 ATR hedef.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/Pv1GvUVs.pine (KST Strategy [Skyrexio]).
    Kural: KST(ROC 10/15/20/30, SMA 10/10/10/15; ağırlık 1-2-3-4) yukarı kesişim sinyal(9); kapanış > LSMA(200) (en küçük kareler
    ortalaması); kapanış > Alligator çenesi (SMMA(hl2,13), 8 mum geri); Choppiness Index(14) < 50. Stop = sinyal mumunun dibi - 1.5 ATR,
    hedef = kapanış + 3.5 ATR (sinyal anındaki ATR14).
    Uyarlama: orijinal yalnız long; `short=True` ayna kurar (aşağı kesişim, tüm koşullar ters, stop = tepe + 1.5 ATR). Varsayılan
    yalnız long. Tarih penceresi ve bot alanları alınmadı. Tek pozisyon (orijinalde de tek).
    Eski sonuç: kaldı: PF 0.96, Sharpe 0.42 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/kst_sky.json).
    """
    ad = "dis__kst-skyrexio"
    stil = "swing"
    varsayilan_parametreler = {"filtre_n": 200, "chop_n": 14, "chop_esik": 50.0, "stop_atr": 1.5, "hedef_atr": 3.5,
                               "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"stop_atr": [1.0, 1.5, 2.0], "hedef_atr": [2.5, 3.5, 5.0], "chop_esik": [40.0, 50.0, 60.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        kk = kst(k)
        filt = linreg(k, int(p["filtre_n"]))
        cene = smma((y + d) / 2.0, 13).shift(8)
        chop = choppiness(y, d, k, int(p["chop_n"]))
        chop_ok = chop < p["chop_esik"]
        long_ok = _ust(kk["kst"], kk["sinyal"]) & (k > filt) & (k > cene) & chop_ok
        short_ok = _alt(kk["kst"], kk["sinyal"]) & (k < filt) & (k < cene) & chop_ok & bool(p["short"])
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        return kur(mumlar, long_ok, short_ok, d - p["stop_atr"] * atr, y + p["stop_atr"] * atr,
                   k + p["hedef_atr"] * atr, k - p["hedef_atr"] * atr)


class LaguerreRsi(Strateji):
    """dis__laguerre-rsi: Laguerre filtresinin yukarı/aşağı bileşenleri kesişince LONG/SHORT; hep piyasada.

    Kaynak: arsiv/strateji-sg/tv/pine/vWG3tMJh.pine (Laguerre RSI).
    Kural: Laguerre filtresi (alfa 0.2, gama = 1 - alfa) L0..L3; cu = L0>L1, L1>L2, L2>L3 farklarının toplamı, cd tersi. cu, cd'yi
    yukarı keserse long, aşağı keserse short; ters sinyal pozisyonu döndürür (RSI = cu/(cu+cd) yalnız çizimdir).
    Uyarlama: orijinalde stop yok -> ATR stop (stop_atr) eklendi. Tarih penceresi alınmadı. Filtre sıfırdan başlar, ilk 50 mumda sinyal yok.
    Eski sonuç: kaldı: PF 2.06, Sharpe 1.04 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/laguerre.json).
    """
    ad = "dis__laguerre-rsi"
    stil = "swing"
    varsayilan_parametreler = {"alfa": 0.2, "atr_periyot": 14, "stop_atr": 3.0, "isinma": 50, "short": True}
    parametre_izgarasi = {"alfa": [0.1, 0.2, 0.3, 0.5], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        lg = laguerre(k, float(p["alfa"]))
        isin = pd.Series(np.arange(len(k)) >= int(p["isinma"]), index=k.index)
        up, dn = _ust(lg["cu"], lg["cd"]) & isin, _alt(lg["cu"], lg["cd"]) & isin
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, up, dn & bool(p["short"]), k - sd, k + sd, cikis_l=dn, cikis_s=up)


class Lube(Strateji):
    """dis__lube: son 500 mumda bugünkü kapanışı içeren aralık oranı (sürtünme) düşükken FIR eğimine göre LONG/SHORT; orta eşikte çıkış.

    Kaynak: arsiv/strateji-sg/tv/pine/i9tJOtjl.pine (LUBE).
    Sürtünme(t) = sum_{i=1..geri_bak} [high[t-i] >= kapanış[t] >= low[t-i]] x (1+B)/(i+B)  (yakın mumlar daha ağır). Yüzdelik aralık:
    lowf/highf = son `aralik` mumun en düşük/en yüksek sürtünmesi; esik_giris = lowf(1-tl) + highf*tl (tl = t_seviye/100),
    esik_cikis = lowf(1-fl) + highf*fl (fl = f_seviye/100); eşikler 5 mum geriden (Pine [5]). FIR = (4c+3c1+2c2+c3)/10; eğim yukarı = long.
    Long: sürtünme < esik_giris[5] ve eğim yukarı; short aynası eğim aşağı. Çıkış: sürtünme > esik_cikis[5] veya ters sinyal.
    Uyarlama: orijinal kaldıraç (2x) ve pozisyon boyutu motora bırakıldı; stop yok -> ATR stop (stop_atr) eklendi. İlk geri_bak+aralik mumda
    sinyal verilmez (sürtünme eksik pencerede çarpıtılır).
    Eski sonuç: kaldı: PF 2.93, Sharpe 0.54 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/lube.json).
    """
    ad = "dis__lube"
    stil = "swing"
    varsayilan_parametreler = {"geri_bak": 500, "aralik": 100, "f_seviye": 50.0, "t_seviye": -10.0,
                               "atr_periyot": 14, "stop_atr": 3.0, "short": True}
    parametre_izgarasi = {"geri_bak": [300, 500], "f_seviye": [40.0, 50.0, 60.0], "t_seviye": [-10.0, 0.0, 10.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        B = int(p["geri_bak"])
        yv, dv, kv = y.to_numpy(float), d.to_numpy(float), k.to_numpy(float)
        n = len(kv)
        fr = np.zeros(n)
        for i in range(1, B + 1):
            if i >= n:
                break
            m = (yv[:-i] >= kv[i:]) & (dv[:-i] <= kv[i:])
            fr[i:] += m * ((1 + B) / (i + B))
        fr = pd.Series(fr, index=k.index)
        r = int(p["aralik"])
        lowf, highf = fr.rolling(r, min_periods=r).min(), fr.rolling(r, min_periods=r).max()
        fl, tl = p["f_seviye"] / 100.0, p["t_seviye"] / 100.0
        midf = lowf * (1 - fl) + highf * fl
        lowf2 = lowf * (1 - tl) + highf * tl
        fir = (4 * k + 3 * k.shift(1) + 2 * k.shift(2) + k.shift(3)) / 10.0
        yukari = fir > fir.shift(1)
        isin = pd.Series(np.arange(n) > B + r, index=k.index)
        dusuk_s = (fr < lowf2.shift(5)) & isin
        uzun, kisa = dusuk_s & yukari, dusuk_s & ~yukari
        son = (fr > midf.shift(5)) & isin
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, uzun, kisa & bool(p["short"]), k - sd, k + sd, cikis_l=son | kisa, cikis_s=son | uzun)


class BilateralStokastik(Strateji):
    """dis__bilateral-stokastik: TMA önfiltreli bull/bear çiftinin kesişimiyle LONG/SHORT; sinyal çizgisi altında kapanışla çıkış.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/NJb4BQ5n.pine (Bilateral Stochastic Oscillator Strategy; kaynakta EURUSD).
    Kural: src = TMA(kapanış, uzunluk) (iki kez SMA). a/b = src'nin son `uzunluk` mumdaki en yüksek/en düşüğü; R = SMA(a-b). bull = src/R - b/R,
    bear = |src/R - a/R|, sinyal = SMA(max(bull,bear), sinyal_n). mod="bull_bear": bull, bear'ı yukarı keserse long, aşağı keserse short;
    mod="sinyal": bull sinyali yukarı keserse long, bear sinyali yukarı keserse short. Long kapanır: bull sinyalin altına kesişince; short:
    bear sinyalin altına kesişince.
    Uyarlama: orijinaldeki "Martingale Multiplier" (varsayılan 1.0 = etkisiz) ve emir büyüklüğü KODLANMADI (martingale yasak). Stop yok ->
    ATR stop (stop_atr) eklendi. Kaynak döviz (EURUSD); TF belirtilmiyor, 4h varsayıldı.
    Eski sonuç: kaldı: PF 1.08, Sharpe 0.38 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/bilateral_stoch.json).
    """
    ad = "dis__bilateral-stokastik"
    stil = "swing"
    varsayilan_parametreler = {"uzunluk": 100, "sinyal_n": 20, "mod": "bull_bear", "atr_periyot": 14, "stop_atr": 3.0,
                               "short": True}
    parametre_izgarasi = {"uzunluk": [50, 100, 150], "sinyal_n": [10, 20, 30], "mod": ["bull_bear", "sinyal"]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["uzunluk"])
        src = g.sma(g.sma(k, n), n)
        a, b = src.rolling(n, min_periods=n).max(), src.rolling(n, min_periods=n).min()
        R = g.sma(a - b, n)
        bull = src / R - b / R
        bear = (src / R - a / R).abs()
        sig = g.sma(pd.concat([bull, bear], axis=1).max(axis=1, skipna=False), int(p["sinyal_n"]))
        if p["mod"] == "sinyal":
            up, dn = _ust(bull, sig), _ust(bear, sig)
        else:
            up, dn = _ust(bull, bear), _alt(bull, bear)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, up, dn & bool(p["short"]), k - sd, k + sd,
                   cikis_l=_alt(bull, sig), cikis_s=_alt(bear, sig))


class MtfMomentumYigin(Strateji):
    """dis__mtf-momentum-yigin: üç zaman dilimi RSI skoru aynı yönde ve 15m Stokastik kesişimi, 4h Stokastik teyidiyle giriş.

    Kaynak: arsiv/strateji-sg/tv/pine/8Ti8z8QO.pine (MTF Momentum Stack + Stochastic).
    Kural: skor(TF) = +1 (RSI14 > 55), -1 (RSI14 < 45), 0 arası; toplam = 15m + 1h + 4h skoru. Long: toplam +3, 15m Stokastik K (11, 3, 3),
    D'yi yukarı keser ve K < 80, ve 4h Stokastik K > D (4h K ve D 11 mumluk lineer regresyonla yumuşatılmış). Short aynası (K > 20, 4h K < D).
    Stop = 1.5 ATR, hedef = 3 ATR. Çıkış: yığın ters yönde tam hizalanınca ("Stack Flip").
    Uyarlama (NEDENSELLEŞTİRME): Pine request.security(lookahead_off) tarihsel mumlarda üst TF'nin oluşmakta olan değerini verebilir;
    burada üst TF değerleri yalnız KAPANMIŞ 1h/4h mumlardan (htf.ust_zaman) alınır. Orijinalde kademeli giriş (pyramiding=3) tek pozisyona
    indirgendi. Veri 15m olmalı (üst TF'ler 1h ve 4h).
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__mtf-momentum-yigin"
    stil = "scalp"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_bant": 5.0, "stok_n": 11, "stok_k": 3, "stok_d": 3, "ust": 80.0,
                               "alt": 20.0, "linreg_n": 11, "atr_periyot": 14, "sl_atr": 1.5, "tp_atr": 3.0,
                               "tf_orta": "1h", "tf_yavas": "4h", "short": True}
    parametre_izgarasi = {"sl_atr": [1.0, 1.5, 2.0], "tp_atr": [2.0, 3.0, 4.0], "rsi_bant": [3.0, 5.0, 8.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def _skor(self, rsi):
        b = self.parametreler["rsi_bant"]
        return pd.Series(np.where(rsi > 50 + b, 1, np.where(rsi < 50 - b, -1, 0)), index=rsi.index).where(rsi.notna())

    def _stok(self, y, d, k):
        p = self.parametreler
        raw = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        kk = g.sma(raw, int(p["stok_k"]))
        return kk, g.sma(kk, int(p["stok_d"]))

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]

        def tf_ozet(u):
            kk, dd = self._stok(u["yuksek"], u["dusuk"], u["kapanis"])
            return pd.DataFrame({"rsi": g.rsi(u["kapanis"], int(p["rsi_n"])),
                                 "k": linreg(kk, int(p["linreg_n"])), "d": linreg(dd, int(p["linreg_n"]))})
        orta = ust_zaman(mumlar, p["tf_orta"], tf_ozet)
        yavas = ust_zaman(mumlar, p["tf_yavas"], tf_ozet)
        toplam = self._skor(g.rsi(k, int(p["rsi_n"]))) + self._skor(orta["rsi"]) + self._skor(yavas["rsi"])
        boga, ayi = toplam == 3, toplam == -3
        kk, dd = self._stok(y, d, k)
        long_ok = boga & _ust(kk, dd) & (kk < p["ust"]) & (yavas["k"] > yavas["d"])
        short_ok = ayi & _alt(kk, dd) & (kk > p["alt"]) & (yavas["k"] < yavas["d"]) & bool(p["short"])
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["sl_atr"] * atr
        td = p["tp_atr"] * atr
        return kur(mumlar, long_ok, short_ok, k - sd, k + sd, k + td, k - td, cikis_l=ayi, cikis_s=boga)
