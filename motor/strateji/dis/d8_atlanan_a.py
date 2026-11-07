"""D8-A — daha önce "mevcut ailenin ayarı olarak ifade edilemiyor" diye atlanan TradingView satırları (dis_envanter.csv,
indeks 0-224); her biri AYRI sınıf. KOD KOPYALANMADI: kural kaynak .pine dosyasından okunup kendi yapımızla yazıldı (kaynak
metin veridir). Hepsi nedensel. Ortak uyarlamalar: stopu olmayan orijinallere ATR felaket stopu (`atr_stop`); boyutlandırma,
komisyon, tarih filtresi, çizim/tablo kodu ve hesap-seviyesi koruma kuralları (günlük zarar kesici vb.) kodlanmadı (risk
katmanının işi); seans/zaman dilimi filtreleri yalnız kaynakta temel kural ise var. Orijinal "yalnız kaynakta tanımlı
mutlak puan/tick" hedefleri varlığa bağlı olduğundan ATR veya aralık katsayısına çevrildi. Çıkışlar: yönlü çıkış sütunları.

Sınıf (indeks) — stil:
  dis__flawless-bbrsi (0)  dis__fibst-pullback (20)  dis__bbpower-sqz (31)  dis__cci2-hma (63)  dis__orb-sweep-donus (66)
  dis__ema-mtfstoch (70)  dis__fib-konfluans (77)  dis__halftrend (93)  dis__oncekigun-kirilim (99)
  dis__likidite-supurme-gun (103)  dis__stoch-macd-cift (119)  dis__mumdizisi-5 (128)  dis__ma-kesisim-dinamik (130)
  dis__ott-var (144)  dis__ott-var-hizli (145)  dis__pmax-rsi-t3 (152)  dis__rf-ha-scalper (157)  dis__mumdizisi-rsi (165)
  dis__pivot30-delta-ters (170)  dis__sqzmom-lb-pine (179)  dis__stoch-rsi-cift (182)  dis__sqzmom-lb-klasik (185)
  dis__hma-supertrend (186)  dis__st-donchian-htf (189)  dis__pivot-hacim-ema150 (193)  dis__trendline-fibst (213)
  dis__cci3-mfi (215)  dis__tott (216)  dis__pivot-sd-bolge (219)
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.gostergeler_b2 import cci
from motor.strateji.dis._gosterge_d1 import kur, linreg, wma
from motor.strateji.dis._gosterge_d2 import (atr_stoplari, kesis_asagi, kesis_yukari, ott, pine_stdev, sikisma_momentum,
                                              var_ma)
from motor.strateji.dis._gosterge_d3 import mfi
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


# ------------------------------------------------------------------ ortak yardımcılar
def _hull(seri: pd.Series, n: int) -> pd.Series:
    """Pine ta.hma: wma(2*wma(n/2) - wma(n), floor(sqrt(n)))."""
    n = int(n)
    return wma(2.0 * wma(seri, max(1, n // 2)) - wma(seri, n), max(1, int(np.floor(np.sqrt(n)))))


def _pivot_yuksek(y: pd.Series, sol: int, sag: int) -> pd.Series:
    """Pine ta.pivothigh(sol, sag): t. mumda (sag mum gecikmeyle) t-sag. mum pivot tepeyse değeri, değilse NaN."""
    orta = y.shift(sag)
    pen = sol + sag + 1
    return orta.where(orta == y.rolling(pen, min_periods=pen).max())


def _pivot_dusuk(d: pd.Series, sol: int, sag: int) -> pd.Series:
    orta = d.shift(sag)
    pen = sol + sag + 1
    return orta.where(orta == d.rolling(pen, min_periods=pen).min())


def _t3(seri: pd.Series, n: int, v: float = 0.7) -> pd.Series:
    e = seri
    es = []
    for _ in range(6):
        e = e.ewm(span=int(n), adjust=False).mean()
        es.append(e)
    c1, c2 = -v ** 3, 3 * v ** 2 + 3 * v ** 3
    c3, c4 = -6 * v ** 2 - 3 * v - 3 * v ** 3, 1 + 3 * v + v ** 3 + 3 * v ** 2
    return c1 * es[5] + c2 * es[4] + c3 * es[3] + c4 * es[2]


def _yerel(index: pd.DatetimeIndex, tz: str) -> pd.DatetimeIndex:
    return index.tz_convert(tz)


def _bos(index) -> pd.Series:
    return pd.Series(False, index=index)


# ================================================================== 0 — BB alt bant + RSI (Flawless Victory v1)
class FlawlessBbRsi(Strateji):
    """dis__flawless-bbrsi (daytrade) — dis_envanter 0, TradingView "Flawless Victory Strategy" (i3Uc79fF, MPL-2.0).
    Kural (v1): kapanış Bollinger(bb_n=20, bb_k=1σ) alt bandının altında VE RSI(14) > rsi_giris (42) -> long (dipte alım ama RSI
    çökmemiş). Çıkış: kapanış üst bandın üstünde VE RSI > rsi_cikis (70). Kaynakta SL/TP yok (v1) -> ATR felaket stopu.
    Uyarlama: kaynaktaki v2/v3 (yüzde SL/TP, MFI) varyantları kodlanmadı; yalnız long.
    Atlananlar: yüzde bazlı SL/TP (v2, v3)."""
    ad = "dis__flawless-bbrsi"
    stil = "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 1.0, "rsi_n": 14, "rsi_giris": 42.0, "rsi_cikis": 70.0,
                               "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"bb_k": [1.0, 1.5, 2.0], "rsi_giris": [35.0, 42.0, 50.0], "rsi_cikis": [65.0, 70.0, 75.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        r = g.rsi(k, int(p["rsi_n"]))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        long_ok = (k < bb["alt"]) & (r > p["rsi_giris"])
        cik = (k > bb["ust"]) & (r > p["rsi_cikis"])
        return kur(mumlar, long_ok, _bos(mumlar.index), sl, ss, cikis_l=cik)


# ================================================================== 31 — BB taşma gücü osilatörü + sıkışma bırakma
class BbPowerSqz(Strateji):
    """dis__bbpower-sqz (daytrade) — dis_envanter 31, TradingView "BB Power Oscillator + Squeeze Release" (M6uONKNI).
    Kural: "taşma gücü" = son bb_n (14) mumda src'nin EMA(14)±1σ bandının dışına taşan miktarın toplam sapmaya oranı (%): boğa =
    üst bandı aşanlar, ayı = alt bandın altı. Boğa osilatörü 50'yi yukarı keserse long, ayı osilatörü 50'yi keserse short; yalnız
    Bollinger(20,2σ)/Keltner(EMA20, EMA(TR)x1.5) sıkışması bırakıldıktan sonraki son 10 mumda. Stop = giriş -/+ 1.4 x ATR(30),
    hedef 1.5R, risk 0.75R'de başabaş, azami 50 mum tutma. Uyarlama: başabaştan sonraki ATR izleyen stop kodlanmadı (motorun
    izleyen stopu girişten itibaren çalışır, kaynakta başabaş sonrası); risk %1 boyutlandırma risk katmanında."""
    ad = "dis__bbpower-sqz"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=0.75, zaman_cikisi_mum=50)
    varsayilan_parametreler = {"bb_n": 14, "bb_k": 1.0, "esik": 50.0, "sqz_n": 20, "sqz_bb_k": 2.0, "sqz_kc_k": 1.5,
                               "pencere": 10, "atr_n": 30, "atr_stop": 1.4, "rr": 1.5}
    parametre_izgarasi = {"esik": [40.0, 50.0, 60.0], "pencere": [5, 10, 20], "rr": [1.0, 1.5, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        n = int(p["bb_n"])
        orta = g.ema(k, n)
        sap = pine_stdev(k, n) * float(p["bb_k"])
        ust, alt = orta + sap, orta - sap
        boga_pay = (k - ust).clip(lower=0.0).rolling(n, min_periods=n).sum()
        boga_payda = (k - ust).abs().rolling(n, min_periods=n).sum()
        aya_pay = (alt - k).clip(lower=0.0).rolling(n, min_periods=n).sum()
        aya_payda = (alt - k).abs().rolling(n, min_periods=n).sum()
        boga = (100.0 * boga_pay / boga_payda.where(boga_payda != 0)).fillna(0.0).where(boga_payda.notna())
        aya = (100.0 * aya_pay / aya_payda.where(aya_payda != 0)).fillna(0.0).where(aya_payda.notna())
        sq = int(p["sqz_n"])
        bb_t = g.sma(k, sq)
        bb_s = float(p["sqz_bb_k"]) * pine_stdev(k, sq)
        kc_t = g.ema(k, sq)
        kc_s = g.ema(g.gercek_aralik(y, d, k), sq) * float(p["sqz_kc_k"])
        sqz_on = ((bb_t - bb_s) > (kc_t - kc_s)) & ((bb_t + bb_s) < (kc_t + kc_s))
        birak = (~sqz_on) & sqz_on.shift(1, fill_value=False)
        son_birak = pd.Series(np.where(birak, np.arange(len(k)), np.nan), index=k.index).ffill()
        yakin = (pd.Series(np.arange(len(k)), index=k.index) - son_birak) <= int(p["pencere"])
        long_ok = kesis_yukari(boga, float(p["esik"])) & yakin
        short_ok = kesis_yukari(aya, float(p["esik"])) & yakin
        a = g.atr(y, d, k, int(p["atr_n"]))
        s = float(p["atr_stop"]) * a
        rr = float(p["rr"])
        return kur(mumlar, long_ok, short_ok, k - s, k + s, k + rr * s, k - rr * s)


# ================================================================== 63 / 215 — CCI + HMA / CCI + MFI (Skyrexio)
class Cci2Hma(Strateji):
    """dis__cci2-hma (daytrade) — dis_envanter 63, TradingView "Double CCI Confirmed Hull MA Reversal" (3fea8k4Z, Skyrex, MPL-2.0).
    Kural (yalnız long): yüksek, HMA(hma_n=34)'yı yukarı keser VE kapanış HMA üstünde VE CCI(25)>0 VE CCI(50)>0 (CCI = HLC3 tabanlı).
    Stop: giriş -/+ 1.75 x ATR(14). Çıkış: kapanış < EMA(iz_n=20). Uyarlama: kaynakta EMA çıkışı yalnız fiyat entry+2.25 ATR
    "aktivasyon" seviyesine değdikten sonra devreye girer (pozisyon durumuna bağlı; strateji sanal pozisyon tutmaz) -> burada
    EMA altı kapanış her zaman çıkış sayılır; aktivasyon kodlanmadı. Stop, giriş mumunun kapanış ATR'siyle sabit."""
    ad = "dis__cci2-hma"
    stil = "daytrade"
    varsayilan_parametreler = {"hma_n": 34, "cci_hizli": 25, "cci_yavas": 50, "iz_n": 20, "atr_n": 14, "atr_stop": 1.75}
    parametre_izgarasi = {"hma_n": [21, 34, 55], "iz_n": [14, 20, 30], "atr_stop": [1.5, 1.75, 2.25]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        hm = _hull(k, int(p["hma_n"]))
        c1 = _cci_hlc3(y, d, k, int(p["cci_hizli"]))
        c2 = _cci_hlc3(y, d, k, int(p["cci_yavas"]))
        long_ok = kesis_yukari(y, hm) & (k > hm) & (c1 > 0) & (c2 > 0)
        _, sl, ss = atr_stoplari(mumlar, 14, float(p["atr_stop"]))
        return kur(mumlar, long_ok, _bos(mumlar.index), sl, ss, cikis_l=k < g.ema(k, int(p["iz_n"])))


def _cci_hlc3(y, d, k, n):
    return cci(y, d, k, n)


class Cci3Mfi(Strateji):
    """dis__cci3-mfi (daytrade) — dis_envanter 215, TradingView "Triple CCI Strategy MFI Confirmed" (PETNavGq, Skyrexio, MPL-2.0).
    Kural (yalnız long): CCI(14) sıfırı yukarı keser VE kapanış > EMA(50) VE CCI(25)>0 VE CCI(50)>0 VE MFI(14)>50. Stop giriş -
    1.75 x ATR(14). Çıkış: kapanış < EMA(iz_n=20). Uyarlama: Cci2Hma ile aynı — 2.25 ATR aktivasyon şartı kodlanmadı."""
    ad = "dis__cci3-mfi"
    stil = "daytrade"
    varsayilan_parametreler = {"cci_a": 14, "cci_b": 25, "cci_c": 50, "mfi_n": 14, "mfi_esik": 50.0, "ema_n": 50,
                               "iz_n": 20, "atr_stop": 1.75}
    parametre_izgarasi = {"ema_n": [30, 50, 100], "mfi_esik": [45.0, 50.0, 55.0], "atr_stop": [1.5, 1.75, 2.25]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d, h = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["hacim"]
        ca, cb, cc = (_cci_hlc3(y, d, k, int(p[x])) for x in ("cci_a", "cci_b", "cci_c"))
        m = mfi(y, d, k, h, int(p["mfi_n"]))
        long_ok = kesis_yukari(ca, 0.0) & (k > g.ema(k, int(p["ema_n"]))) & (cb > 0) & (cc > 0) & (m > p["mfi_esik"])
        _, sl, ss = atr_stoplari(mumlar, 14, float(p["atr_stop"]))
        return kur(mumlar, long_ok, _bos(mumlar.index), sl, ss, cikis_l=k < g.ema(k, int(p["iz_n"])))


# ================================================================== 66 — açılış aralığı süpürme-dönüş
class OrbSweepDonus(Strateji):
    """dis__orb-sweep-donus (scalp, 5 dk) — dis_envanter 66, TradingView "EE Sweep Return" (7OLnQI4B).
    Kural: günlük açılış aralığı (yerel saat `or_bas`..`or_bit`, varsayılan 08:30-09:30 Chicago) belirlenir. Sinyal penceresinde
    (`or_bit`..`pen_bit`, 15:00) fiyat aralığın bir ucunu İĞNELER (high>orH / low<orL) ve aynı ya da sonraki mumda kapanış
    aralığın İÇİNE döner -> iğnenin ters yönünde giriş (üst süpürme -> short, alt süpürme -> long). Sinyal sonrası iğneler sıfırlanır.
    Hedef/stop: aralık genişliğinin hedef_k (2.0) / stop_k (1.0) katı (kaynak 50/25 puan, enstrümana bağlı mutlak puan; ES vadelisine
    kalibreli oranı korumak için aralık katına çevrildi). Pencere sonunda `cikis`. Çift iğnede son iğne yönü (kaynaktaki gibi)."""
    ad = "dis__orb-sweep-donus"
    stil = "scalp"
    varsayilan_parametreler = {"tz": "America/Chicago", "or_bas": 510, "or_bit": 570, "pen_bit": 900, "ayni_mum": True,
                               "kutu_ici": True, "stop_k": 1.0, "hedef_k": 2.0}
    parametre_izgarasi = {"stop_k": [0.75, 1.0, 1.5], "hedef_k": [1.5, 2.0, 3.0], "ayni_mum": [True, False]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        idx = mumlar.index
        yer = _yerel(idx, p["tz"])
        dk = (yer.hour * 60 + yer.minute).to_numpy()
        gun = yer.normalize().tz_localize(None).values.astype("datetime64[D]").astype("int64")
        h, l, k, a = (mumlar[c].to_numpy(dtype=float) for c in ("yuksek", "dusuk", "kapanis", "acilis"))
        n = len(k)
        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        cik = np.zeros(n, dtype=bool)
        orb, orl, gun_no = np.nan, np.nan, None
        arm_u = arm_d = False
        son = 0
        onceki_pen = False
        for i in range(n):
            if gun_no is None or gun[i] != gun_no:
                gun_no, orb, orl, arm_u, arm_d, son = gun[i], np.nan, np.nan, False, False, 0
                onceki_pen = False
            or_ici = p["or_bas"] <= dk[i] < p["or_bit"]
            pen = p["or_bit"] <= dk[i] < p["pen_bit"]
            if or_ici:
                orb = h[i] if np.isnan(orb) else max(orb, h[i])
                orl = l[i] if np.isnan(orl) else min(orl, l[i])
            if onceki_pen and not pen:
                cik[i] = True
            onceki_pen = pen
            if not (pen and not np.isnan(orb)):
                continue
            ap_u, ap_d, sn_o = arm_u, arm_d, son
            ust_kirdi, alt_kirdi = h[i] > orb, l[i] < orl
            if ust_kirdi:
                arm_u = True
            if alt_kirdi:
                arm_d = True
            if ust_kirdi and alt_kirdi:
                son = 1 if k[i] >= a[i] else -1
            elif ust_kirdi:
                son = 1
            elif alt_kirdi:
                son = -1
            can_s, can_l, lb = (arm_u, arm_d, son) if p["ayni_mum"] else (ap_u, ap_d, sn_o)
            ici = (k[i] < orb) and (k[i] > orl)
            ret_s = ici if p["kutu_ici"] else k[i] < orb
            ret_l = ici if p["kutu_ici"] else k[i] > orl
            raw_s, raw_l = can_s and ret_s, can_l and ret_l
            s_sig = raw_s and (not raw_l or lb == 1)
            l_sig = raw_l and (not raw_s or lb == -1)
            if s_sig or l_sig:
                gen = orb - orl
                arm_u = arm_d = False
                son = 0
                if gen > 0:
                    yon[i] = -1 if s_sig else 1
                    stop[i] = k[i] + float(p["stop_k"]) * gen if s_sig else k[i] - float(p["stop_k"]) * gen
                    hedef[i] = k[i] - float(p["hedef_k"]) * gen if s_sig else k[i] + float(p["hedef_k"]) * gen
        out = pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef, "cikis": cik}, index=idx)
        out["cikis_long"] = False
        out["cikis_short"] = False
        return out


# ================================================================== 70 — EMA38/62 trendi + MTF stokastik
class EmaMtfStoch(Strateji):
    """dis__ema-mtfstoch (daytrade) — dis_envanter 70, TradingView "EMA Trend + MTF Stochastic" (o9dV6uWc).
    Kural: EMA(38) > EMA(62) trendinde; yerel stokastik (11,3,3) K 50'nin üstünde ve yükseliyor ve K>D VE üst zaman dilimi (tf_ust,
    varsayılan 4h; kapanmış mumlar) stokastiğinin (linreg yumuşatmalı) K'sı 50'yi yukarı keser VE ÜstK>ÜstD -> long. Short ayna
    (trend aşağı, üst D 50'yi aşağı keser). Stop 1.5 x ATR(14), risk 1R'de başabaş, azami 60 mum. Çıkış: üst D 80'in altına
    inerse (long) / üst K 20'nin üstüne çıkarsa (short) ya da EMA trendi ters dönerse. Kaynağın 1.5R sonrası izleyen ATR stopu
    kodlanmadı (motorun izleyen stopu girişten başlar)."""
    ad = "dis__ema-mtfstoch"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0, zaman_cikisi_mum=60)
    varsayilan_parametreler = {"ema_hizli": 38, "ema_yavas": 62, "stok_n": 11, "stok_k": 3, "stok_d": 3, "tf_ust": "4h",
                               "ust_alan": 80.0, "alt_alan": 20.0, "atr_n": 14, "atr_stop": 1.5, "short": True}
    parametre_izgarasi = {"ema_hizli": [30, 38, 50], "stok_n": [8, 11, 14], "atr_stop": [1.0, 1.5, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        ef, es = g.ema(k, int(p["ema_hizli"])), g.ema(k, int(p["ema_yavas"]))
        yukari, asagi = ef > es, ef < es

        def stok(yy, dd, kk):
            raw = g.stokastik(yy, dd, kk, int(p["stok_n"]), 1)["k"]
            kk_ = g.sma(raw, int(p["stok_k"]))
            return kk_, g.sma(kk_, int(p["stok_d"]))

        def ozet(u):
            kk_, dd_ = stok(u["yuksek"], u["dusuk"], u["kapanis"])
            return pd.DataFrame({"k": linreg(kk_, int(p["stok_n"])), "d": linreg(dd_, int(p["stok_n"]))})
        ust = ust_zaman(mumlar, p["tf_ust"], ozet)
        kk, dd = stok(y, d, k)
        long_ok = kesis_yukari(ust["k"], 50.0) & (kk > 50) & (kk.diff() > 0) & (kk > dd) & (ust["k"] > ust["d"]) & yukari
        short_ok = (kesis_asagi(ust["d"], 50.0) & (kk < 50) & (kk.diff() < 0) & (kk < dd) & (ust["k"] < ust["d"]) & asagi
                    & bool(p["short"]))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        cl = kesis_asagi(ust["d"], float(p["ust_alan"])) | asagi
        cs = kesis_yukari(ust["k"], float(p["alt_alan"])) | yukari
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=cl, cikis_s=cs)


# ================================================================== 77 — Fibonacci çoklu pencere konfluansı
class FibKonfluans(Strateji):
    """dis__fib-konfluans (daytrade) — dis_envanter 77, TradingView "Fib Confluence Scanner" (rKsnPJbJ).
    Kural: son 20/50/100 mumun yüksek-düşük aralığından Fib seviyeleri (üstten 0.236/0.382/0.5/0.618/0.786); kapanışa yüzde
    `tol` (0.5) içinde en az `min_konf` (1) seviye varsa ve kapanış EMA(50)'nin üstündeyse long, altındaysa short. Stop giriş -/+
    %1.5, hedef 2R. RSI filtresi (kaynakta varsayılan kapalı) kodlanmadı."""
    ad = "dis__fib-konfluans"
    stil = "daytrade"
    varsayilan_parametreler = {"len_a": 20, "len_b": 50, "len_c": 100, "tol": 0.005, "min_konf": 1, "ema_n": 50,
                               "sl": 0.015, "rr": 2.0}
    parametre_izgarasi = {"tol": [0.003, 0.005, 0.01], "sl": [0.01, 0.015, 0.02], "rr": [1.5, 2.0, 3.0]}
    _SEVIYE = (0.236, 0.382, 0.5, 0.618, 0.786)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        sayac = pd.Series(0, index=k.index)
        for ln in (p["len_a"], p["len_b"], p["len_c"]):
            hh = y.rolling(int(ln), min_periods=int(ln)).max()
            ll = d.rolling(int(ln), min_periods=int(ln)).min()
            for f in self._SEVIYE:
                sev = hh - f * (hh - ll)
                sayac = sayac + (((k - sev).abs() / k) <= float(p["tol"])).astype(int)
        konf = (sayac >= int(p["min_konf"])) & y.rolling(int(p["len_c"]), min_periods=int(p["len_c"])).max().notna()
        ema = g.ema(k, int(p["ema_n"]))
        sl, rr = float(p["sl"]), float(p["rr"])
        return kur(mumlar, konf & (k > ema), konf & (k < ema), k * (1 - sl), k * (1 + sl),
                   k * (1 + sl * rr), k * (1 - sl * rr))


# ================================================================== 93 — HalfTrend
def _halftrend(y, d, k, amp: int):
    """HalfTrend (everget/Alex Orekhov mantığı, kendi yazımımız). -> (ht çizgisi, al sinyali, sat sinyali). Nedensel döngü."""
    h, l, c = (x.to_numpy(dtype=float) for x in (y, d, k))
    n = len(c)
    atr2 = (g.atr(y, d, k, 100) / 2.0).to_numpy()
    yp = y.rolling(amp, min_periods=amp).max().to_numpy()
    dp = d.rolling(amp, min_periods=amp).min().to_numpy()
    yma = g.sma(y, amp).to_numpy()
    dma = g.sma(d, amp).to_numpy()
    ht = np.full(n, np.nan)
    al = np.zeros(n, dtype=bool)
    sat = np.zeros(n, dtype=bool)
    trend, nxt = 0, 0
    max_low, min_high = l[0], h[0]
    up = down = 0.0
    onceki = None
    for i in range(n):
        if np.isnan(yp[i]) or np.isnan(yma[i]):
            continue
        pl, ph = (l[i - 1], h[i - 1]) if i else (l[i], h[i])
        if nxt == 1:
            max_low = max(dp[i], max_low)
            if yma[i] < max_low and c[i] < pl:
                trend, nxt, min_high = 1, 0, yp[i]
        else:
            min_high = min(yp[i], min_high)
            if dma[i] > min_high and c[i] > ph:
                trend, nxt, max_low = 0, 1, dp[i]
        if trend == 0:
            if onceki is not None and onceki != 0:
                up = down
                al[i] = not np.isnan(atr2[i])
            else:
                up = max(max_low, up)
        else:
            if onceki is not None and onceki != 1:
                down = up
                sat[i] = not np.isnan(atr2[i])
            else:
                down = min(min_high, down) if down != 0.0 else min_high
        ht[i] = up if trend == 0 else down
        onceki = trend
    return pd.Series(ht, index=k.index), pd.Series(al, index=k.index), pd.Series(sat, index=k.index)


class HalfTrend(Strateji):
    """dis__halftrend (daytrade) — dis_envanter 93, TradingView "HalfTrend Strategy" (0vvrOpg1).
    Kural: HalfTrend (amplitude=2; yüksek/düşük ortalama + son `amplitude` mumun uçlarıyla yön değişimi) yukarı dönünce long, aşağı
    dönünce short; ters sinyalde çevirir (cikis_long/cikis_short). Kaynakta stop yok -> ATR felaket stopu. Atlananlar: kaynağın
    NSE seans penceresi (09:20-15:20 IST) ve gün sonu kapanışı (kripto 7/24; gun_sonu=True ile UTC gün sonu kapanışı açılabilir),
    kanal sapması (yalnız çizim)."""
    ad = "dis__halftrend"
    stil = "daytrade"
    varsayilan_parametreler = {"amplitude": 2, "atr_n": 14, "atr_stop": 3.0, "gun_sonu": False}
    parametre_izgarasi = {"amplitude": [2, 3, 4, 5], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        _, al, sat = _halftrend(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], int(p["amplitude"]))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, al, sat, sl, ss, cikis_l=sat, cikis_s=al, gun_sonu=bool(p["gun_sonu"]))


# ================================================================== 99 — önceki gün tepe/dip kırılımı
class OncekiGunKirilim(Strateji):
    """dis__oncekigun-kirilim (daytrade) — dis_envanter 99, TradingView "HTF Level Breakout" (PdJvHIfQ).
    Kural: seviye = önceki UTC günün tepe ve dibi. Gün içinde fiyat üst seviyeye İLK dokunduğunda (high >= seviye) o mumun yüksek
    değeri "S1" olarak saklanır ve alt seviye devre dışı kalır; sonraki bir mumun kapanışı hem seviyenin hem S1'in üstüne çıkarsa
    long (stop = son onaylı pivot dip [pivot_n sol/sağ], hedef rr (2) R). Short ayna (alt seviye dokunuşu, S1 = o mumun dibi, stop
    son pivot tepe). Gün başına bir sinyal/yön; `cikis_saat` (UTC, varsayılan 19:00 = kaynağın 22:00 UTC+3'ü; -1 kapalı)
    zorunlu çıkış. Kaynak "işlemdeyken seviyeyi yenileme" kuralı strateji durumuna bağlı olduğundan her yeni UTC günde seviye yenilenir."""
    ad = "dis__oncekigun-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {"pivot_n": 5, "rr": 2.0, "cikis_saat": 19}
    parametre_izgarasi = {"pivot_n": [3, 5, 8], "rr": [1.5, 2.0, 3.0], "cikis_saat": [-1, 19]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        idx = mumlar.index
        h, l, k = (mumlar[c].to_numpy(dtype=float) for c in ("yuksek", "dusuk", "kapanis"))
        gun = idx.floor("D")
        gunluk = pd.DataFrame({"h": mumlar["yuksek"], "l": mumlar["dusuk"]}).groupby(gun).agg(h=("h", "max"), l=("l", "min")).shift(1)
        sev_h = gunluk["h"].reindex(gun).to_numpy()
        sev_l = gunluk["l"].reindex(gun).to_numpy()
        n_ = int(p["pivot_n"])
        piv_l = _pivot_dusuk(mumlar["dusuk"], n_, n_).ffill().to_numpy()
        piv_h = _pivot_yuksek(mumlar["yuksek"], n_, n_).ffill().to_numpy()
        gun_i = gun.values.astype("datetime64[D]").astype("int64")
        n = len(k)
        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        rr = float(p["rr"])
        akt_h = akt_l = True
        s1h = s1l = np.nan
        yapildi_l = yapildi_s = False
        cur = None
        for i in range(n):
            if cur is None or gun_i[i] != cur:
                cur, akt_h, akt_l, s1h, s1l, yapildi_l, yapildi_s = gun_i[i], True, True, np.nan, np.nan, False, False
            if np.isnan(sev_h[i]):
                continue
            if akt_h and not yapildi_l:
                if np.isnan(s1h):
                    if h[i] >= sev_h[i]:
                        s1h = h[i]
                        akt_l = False
                elif k[i] > sev_h[i] and k[i] > s1h and not np.isnan(piv_l[i]) and piv_l[i] < k[i]:
                    yon[i], stop[i], hedef[i] = 1, piv_l[i], k[i] + (k[i] - piv_l[i]) * rr
                    yapildi_l = True
            if akt_l and not yapildi_s and yon[i] == 0:
                if np.isnan(s1l):
                    if l[i] <= sev_l[i]:
                        s1l = l[i]
                        akt_h = False
                elif k[i] < sev_l[i] and k[i] < s1l and not np.isnan(piv_h[i]) and piv_h[i] > k[i]:
                    yon[i], stop[i], hedef[i] = -1, piv_h[i], k[i] - (piv_h[i] - k[i]) * rr
                    yapildi_s = True
        cik = _bos(idx)
        if int(p["cikis_saat"]) >= 0:
            sa = pd.Series(idx.hour, index=idx)
            cik = (sa == int(p["cikis_saat"])) & (sa.shift(1) != int(p["cikis_saat"]))
        out = pd.DataFrame({"yon": yon, "stop": stop, "hedef": hedef, "cikis": cik.astype(bool)}, index=idx)
        out["cikis_long"] = False
        out["cikis_short"] = False
        return out


# ================================================================== 103 — günlük likidite süpürme
class LikiditeSupurmeGun(Strateji):
    """dis__likidite-supurme-gun (daytrade) — dis_envanter 103, TradingView "ICT Daily Liquidity Sweep" (SlWseGFp).
    Kural: bir seviyenin ALTINA iğne atıp (low < seviye) üstünde kapanış (close > seviye) = alt likidite süpürmesi -> long; üst
    seviye için ayna -> short. Seviyeler (her biri açılıp kapanabilir): Asya aralığı (00-08 UTC; 08:00'dan sonra), önceki günün
    tepe/dibi, Londra aralığı (08-12 UTC; 12:00'dan sonra), son `swing_n` (10) mumun tepe/dibi (önceki mumlara kadar). Pencere
    `bas_saat`..`bit_saat` UTC. Stop = süpürme mumunun ucu -/+ tampon (`tampon_atr` x ATR; kaynakta pip), TP1 1.5R'de pozisyonun
    %50'si, TP2 `tp2_r` (3R) hedef; `bit_saat`te zorunlu çıkış. Aynı mumda hem long hem short koşulu varsa ikisi de atılır."""
    ad = "dis__likidite-supurme-gun"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(kismi=((1.5, 0.5),))
    varsayilan_parametreler = {"asya": True, "londra": True, "onceki_gun": True, "swing": True, "swing_n": 10,
                               "bas_saat": 0, "bit_saat": 23, "tampon_atr": 0.2, "tp2_r": 3.0, "atr_n": 14}
    parametre_izgarasi = {"swing_n": [10, 20, 30], "tampon_atr": [0.1, 0.2, 0.4], "tp2_r": [2.5, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        sa = pd.Series(idx.hour, index=idx)
        gun = idx.floor("D")
        sev = []   # (alt seviye, üst seviye)

        def aralik(bas, bit):
            m = (sa >= bas) & (sa < bit)
            hh = y.where(m).groupby(gun).transform("max")
            ll = d.where(m).groupby(gun).transform("min")
            kilit = sa >= bit
            return ll.where(kilit), hh.where(kilit)
        if p["asya"]:
            sev.append(aralik(0, 8))
        if p["londra"]:
            sev.append(aralik(8, 12))
        if p["onceki_gun"]:
            gd = pd.DataFrame({"h": y, "l": d}).groupby(gun).agg(h=("h", "max"), l=("l", "min")).shift(1)
            sev.append((gd["l"].reindex(gun).set_axis(idx), gd["h"].reindex(gun).set_axis(idx)))
        if p["swing"]:
            n = int(p["swing_n"])
            sev.append((d.rolling(n, min_periods=n).min().shift(1), y.rolling(n, min_periods=n).max().shift(1)))
        pen = (sa >= int(p["bas_saat"])) & (sa < int(p["bit_saat"]))
        long_ok, short_ok = _bos(idx), _bos(idx)
        for alt, ust in sev:
            long_ok |= (d < alt) & (k > alt)
            short_ok |= (y > ust) & (k < ust)
        long_ok &= pen
        short_ok &= pen
        cak = long_ok & short_ok
        long_ok &= ~cak
        short_ok &= ~cak
        a = g.atr(y, d, k, int(p["atr_n"]))
        tmp = float(p["tampon_atr"]) * a
        sl, ss = d - tmp, y + tmp
        r_l, r_s = k - sl, ss - k
        tp = float(p["tp2_r"])
        out = kur(mumlar, long_ok, short_ok, sl, ss, k + tp * r_l, k - tp * r_s)
        bit = int(p["bit_saat"])
        out["cikis"] = ((sa == bit) & (sa.shift(1) != bit)).astype(bool)
        return out


# ================================================================== 119 / 182 — Stokastik + MACD / Stokastik + RSI
def _pencere_var(kosul: pd.Series, n: int) -> pd.Series:
    """Son n mumda (bugün dahil) en az bir kez True."""
    return kosul.rolling(int(n), min_periods=1).max().fillna(0).astype(bool)


class StochMacdCift(Strateji):
    """dis__stoch-macd-cift (daytrade) — dis_envanter 119, TradingView "MACD + Stochastic, Double Strategy" (ChartArt, G5ro3y87).
    Kural: yavaş stokastik (14, K=SMA3, D=SMA2) K, D'yi yukarı keser VE K < 100-asiri (29) VE MACD histogramı (12,26,9) sıfırı yukarı
    keser -> long; short ayna (K > asiri=71). `pencere` (1 = kaynaktaki gibi aynı mum; >1: iki kesişim son N mumda). Kaynakta
    stop yok -> ATR felaket stopu; ters sinyalde pozisyon çevrilir."""
    ad = "dis__stoch-macd-cift"
    stil = "daytrade"
    varsayilan_parametreler = {"stok_n": 14, "stok_k": 3, "stok_d": 2, "asiri": 71.0, "pencere": 1, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"asiri": [65.0, 71.0, 75.0], "pencere": [1, 3, 5], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        raw = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        kk = g.sma(raw, int(p["stok_k"]))
        dd = g.sma(kk, int(p["stok_d"]))
        delta = g.macd(k)["histogram"]
        w = int(p["pencere"])
        a = float(p["asiri"])
        long_ok = _pencere_var(kesis_yukari(kk, dd) & (kk < 100 - a), w) & kesis_yukari(delta, 0.0)
        short_ok = _pencere_var(kesis_asagi(kk, dd) & (kk > a), w) & kesis_asagi(delta, 0.0)
        long_ok = long_ok | (_pencere_var(kesis_yukari(delta, 0.0), w) & kesis_yukari(kk, dd) & (kk < 100 - a))
        short_ok = short_ok | (_pencere_var(kesis_asagi(delta, 0.0), w) & kesis_asagi(kk, dd) & (kk > a))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=short_ok, cikis_s=long_ok)


class StochRsiCift(Strateji):
    """dis__stoch-rsi-cift (daytrade) — dis_envanter 182, TradingView "Stochastic + RSI, Double Strategy" (ChartArt, IGJPEi7L).
    Kural: yavaş stokastik (14,3,3) K, D'yi yukarı keser VE K < 20 VE RSI(14) 30'u yukarı keser -> long; short: K, D'yi aşağı keser
    VE K > 80 VE RSI 70'i aşağı keser. `pencere` (1 = aynı mum; >1: stokastik kesişimi son N mumda). Stop yok -> ATR felaket stopu;
    ters sinyalde çevirir. Not: strateji ailesinin zorunlu trend EMA filtresi kaynakta yok; burada da eklenmedi."""
    ad = "dis__stoch-rsi-cift"
    stil = "daytrade"
    varsayilan_parametreler = {"stok_n": 14, "stok_k": 3, "stok_d": 3, "alt": 20.0, "ust": 80.0, "rsi_n": 14,
                               "rsi_alt": 30.0, "rsi_ust": 70.0, "pencere": 1, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"alt": [15.0, 20.0, 25.0], "pencere": [1, 3, 5], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        raw = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        kk = g.sma(raw, int(p["stok_k"]))
        dd = g.sma(kk, int(p["stok_d"]))
        r = g.rsi(k, int(p["rsi_n"]))
        w = int(p["pencere"])
        long_ok = _pencere_var(kesis_yukari(kk, dd) & (kk < p["alt"]), w) & kesis_yukari(r, float(p["rsi_alt"]))
        short_ok = _pencere_var(kesis_asagi(kk, dd) & (kk > p["ust"]), w) & kesis_asagi(r, float(p["rsi_ust"]))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=short_ok, cikis_s=long_ok)


# ================================================================== 128 / 165 — ardışık mum devamı
class MumDizisi(Strateji):
    """dis__mumdizisi-5 (daytrade) — dis_envanter 128, TradingView "Momentum Sequence Strategy [Herman]" (mmrInMTp).
    Kural: "ana mum" (n mum önce) KIRMIZI (kapanış<açılış); sonraki n mumun HEPSİ yeşil, her biri ana mumun dibinin üstünde
    düşük yapar ve kapanışlar artan (her kapanış bir öncekinden yüksek) -> long. Stop ana mumun dibi, hedef rr (1.5) R. Short
    ayna (kaynakta varsayılan kapalı). Kaynakta oturum/vade bilgisi yok. `tolerans` (% — 165'te 0.05) bir önceki kapanışın bu
    kadar altına inen kapanışa izin verir; `rsi_filtre` (165) RSI>rsi_min ve yükselirken (short: <rsi_max ve düşerken)."""
    ad = "dis__mumdizisi-5"
    stil = "daytrade"
    varsayilan_parametreler = {"n": 5, "rr": 1.5, "tolerans": 0.0, "rsi_filtre": False, "rsi_n": 14, "rsi_min": 40.0,
                               "rsi_max": 60.0, "short": False}
    parametre_izgarasi = {"n": [3, 4, 5], "rr": [1.0, 1.5, 2.0], "tolerans": [0.0, 0.05, 0.1]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        n = int(p["n"])
        a, y, d, k = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        tol = float(p["tolerans"]) / 100.0
        ana_dusuk, ana_yuksek = d.shift(n), y.shift(n)
        boga = pd.Series(True, index=k.index)
        ayi = pd.Series(True, index=k.index)
        for i in range(n):
            boga &= (k.shift(i) > a.shift(i)) & (d.shift(i) > ana_dusuk)
            ayi &= (k.shift(i) < a.shift(i)) & (y.shift(i) < ana_yuksek)
            if i < n - 1:
                boga &= k.shift(i) > k.shift(i + 1) * (1 - tol)
                ayi &= k.shift(i) < k.shift(i + 1) * (1 + tol)
        long_ok = (k.shift(n) < a.shift(n)) & boga
        short_ok = (k.shift(n) > a.shift(n)) & ayi & bool(p["short"])
        if p["rsi_filtre"]:
            r = g.rsi(k, int(p["rsi_n"]))
            long_ok &= (r > p["rsi_min"]) & (r > r.shift(1))
            short_ok &= (r < p["rsi_max"]) & (r < r.shift(1))
        rr = float(p["rr"])
        return kur(mumlar, long_ok, short_ok, ana_dusuk, ana_yuksek, k + rr * (k - ana_dusuk), k - rr * (ana_yuksek - k))


class MumDizisiRsi(MumDizisi):
    """dis__mumdizisi-rsi (daytrade) — dis_envanter 165, TradingView (49jNhJXM): MumDizisi'nin RSI onaylı, %0.05 toleranslı sürümü.
    Kural: MumDizisi + RSI(14) > 40 ve yükselirken long (short: < 60 ve düşerken, kaynakta varsayılan kapalı); kapanış artışında
    önceki kapanışın %0.05 altına inişe izin verilir. Stop ana mum dibi, hedef 1.5R."""
    ad = "dis__mumdizisi-rsi"
    varsayilan_parametreler = {**MumDizisi.varsayilan_parametreler, "tolerans": 0.05, "rsi_filtre": True}
    parametre_izgarasi = {"n": [3, 4, 5], "rr": [1.0, 1.5, 2.0], "rsi_min": [35.0, 40.0, 50.0]}


# ================================================================== 130 — dinamik kaynaklı MA kesişimi
class MaKesisimDinamik(Strateji):
    """dis__ma-kesisim-dinamik (daytrade) — dis_envanter 130, TradingView "Moving Average Crossover" (Ip667jzb).
    Kural (kaynağın varsayılan ayarı): Hızlı = EMA(fast_n=5) ama kaynağı "dinamik": kapanış > Trend ise düşük, değilse yüksek;
    Yavaş = SMA(10) (kapanış); Trend = SMA(13). Long: Hızlı, Yavaşı yukarı keser VE yükseliş dizilimi (Hızlı>=Yavaş>=Trend);
    short: ayna. Çıkış: ters Hızlı-Yavaş kesişimi. Kaynaktaki isteğe bağlı hacim/ATR/RSI filtreleri ve yüzde SL/TP varsayılan KAPALI
    olduğundan kodlanmadı; stop yok -> ATR felaket stopu."""
    ad = "dis__ma-kesisim-dinamik"
    stil = "daytrade"
    varsayilan_parametreler = {"fast_n": 5, "slow_n": 10, "trend_n": 13, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"fast_n": [3, 5, 8], "slow_n": [8, 10, 15], "trend_n": [13, 21, 34]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        trend = g.sma(k, int(p["trend_n"]))
        hizli = g.ema(d.where(k > trend, y), int(p["fast_n"]))
        yavas = g.sma(k, int(p["slow_n"]))
        yuk, asg = kesis_yukari(hizli, yavas), kesis_asagi(hizli, yavas)
        long_ok = yuk & (hizli >= yavas) & (yavas >= trend)
        short_ok = asg & (hizli <= yavas) & (yavas <= trend)
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=asg, cikis_s=yuk)


# ================================================================== 144 / 145 / 216 — OTT / VAR
class OttVar(Strateji):
    """dis__ott-var (daytrade) — dis_envanter 144, TradingView "Optimized Trend Tracker" (HPbRZvsV, KivancOzbilgic tipi).
    Kural: MAvg = VAR (Chande değişken endeksli dinamik ortalama, uzunluk=2); OTT = MAvg'ın yüzde (1.4) bandıyla izleyen çizgi
    (iki mum geriye kaydırılmış OTT[2], kaynaktaki gibi). MAvg, OTT[2]'yi yukarı keserse long, aşağı keserse short; hep piyasada
    (ters sinyalde çevirir). `kosul`="destek" (MAvg-OTT) ya da "fiyat" (kapanış-OTT). Kaynakta stop yok -> ATR felaket stopu.
    Not: diğer MA tipleri (SMA/EMA/WMA/TMA/WWMA/ZLEMA/TSF) kodlanmadı; yalnız VAR (kaynağın varsayılanı)."""
    ad = "dis__ott-var"
    stil = "daytrade"
    varsayilan_parametreler = {"uzunluk": 2, "yuzde": 1.4, "kosul": "destek", "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"uzunluk": [1, 2, 4], "yuzde": [0.5, 1.0, 1.4], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        mav = var_ma(k, int(p["uzunluk"]))
        o = ott(k, int(p["uzunluk"]), float(p["yuzde"])).shift(2)
        ana = mav if p["kosul"] == "destek" else k
        al, sat = kesis_yukari(ana, o), kesis_asagi(ana, o)
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, al, sat, sl, ss, cikis_l=sat, cikis_s=al)


class OttVarHizli(OttVar):
    """dis__ott-var-hizli (daytrade) — dis_envanter 145, TradingView "OTT - Strategy Version" (ycDUERPO): OttVar'ın kaynaktaki
    varsayılanlarıyla (VAR uzunluk 1, OTT %0.1; destek çizgisi kesişimi) sürümü. Kural ve uyarlamalar OttVar ile aynı; çok kısa
    VAR periyodu nedeniyle sinyal sıklığı çok yüksektir (grid daha geniş yüzdelerde tutuldu)."""
    ad = "dis__ott-var-hizli"
    varsayilan_parametreler = {**OttVar.varsayilan_parametreler, "uzunluk": 1, "yuzde": 0.1}
    parametre_izgarasi = {"yuzde": [0.1, 0.3, 0.6], "kosul": ["destek", "fiyat"], "atr_stop": [2.0, 3.0, 4.0]}


class Tott(Strateji):
    """dis__tott (daytrade) — dis_envanter 216, TradingView "Twin Optimized Trend Tracker" (eENf7NpJ).
    Kural: MAvg = VAR(uzunluk=40); OTT yüzde=1; OTTup = OTT x (1+katsayi), OTTdn = OTT x (1-katsayi) (katsayi 0.001), ikisi de iki
    mum geriye kaydırılmış. MAvg, OTTup'ı yukarı keserse long; OTTdn'yi aşağı keserse short; hep piyasada. Stop yok -> ATR felaket
    stopu. Diğer MA tipleri kodlanmadı (VAR kaynağın varsayılanı)."""
    ad = "dis__tott"
    stil = "daytrade"
    varsayilan_parametreler = {"uzunluk": 40, "yuzde": 1.0, "katsayi": 0.001, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"uzunluk": [20, 40, 60], "yuzde": [0.5, 1.0, 2.0], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        mav = var_ma(k, int(p["uzunluk"]))
        o = ott(k, int(p["uzunluk"]), float(p["yuzde"])).shift(2)
        al = kesis_yukari(mav, o * (1 + float(p["katsayi"])))
        sat = kesis_asagi(mav, o * (1 - float(p["katsayi"])))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, al, sat, sl, ss, cikis_l=sat, cikis_s=al)


# ================================================================== 152 — RSI üzerinde T3 + PMax
def _pmax(ma: np.ndarray, atr: np.ndarray, carpan: float) -> np.ndarray:
    n = len(ma)
    out = np.full(n, np.nan)
    ls_prev = ss_prev = np.nan
    d = 1
    for i in range(n):
        if np.isnan(ma[i]) or np.isnan(atr[i]):
            continue
        ls = ma[i] - carpan * atr[i]
        ss = ma[i] + carpan * atr[i]
        lsp = ls if np.isnan(ls_prev) else ls_prev
        ssp = ss if np.isnan(ss_prev) else ss_prev
        ls = max(ls, lsp) if ma[i] > lsp else ls
        ss = min(ss, ssp) if ma[i] < ssp else ss
        d = 1 if (d == -1 and ma[i] > ssp) else (-1 if (d == 1 and ma[i] < lsp) else d)
        out[i] = ls if d == 1 else ss
        ls_prev, ss_prev = ls, ss
    return out


class PmaxRsiT3(Strateji):
    """dis__pmax-rsi-t3 (daytrade) — dis_envanter 152, TradingView "PMax on RSI w T3" (ZLcmWQtj).
    Kural: RSI(14) serisi üzerinde Tillson T3 (uzunluk 8, hacim faktörü 0.7) = MAvg; PMax = MAvg'ın ATR_RSI x carpan (3) bandıyla
    izleyen çizgisi (Supertrend benzeri). ATR_RSI = RSI'nin yüksek/düşük uyarlamalarından (fiyatın yüksek/düşüğüyle hesaplanan RSI)
    gerçek aralığın SMA(10)'u. T3, PMax'i yukarı keserse long, aşağı keserse short; hep piyasada. Stop yok -> fiyat ATR felaket
    stopu. Uyarlama: RSI standart Wilder RSI (kaynaktaki WWMA tabanlı başlangıç sıfırlama farkı ısınma dönemini etkiler)."""
    ad = "dis__pmax-rsi-t3"
    stil = "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "t3_n": 8, "t3_v": 0.7, "atr_p": 10, "carpan": 3.0, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"t3_n": [5, 8, 13], "carpan": [2.0, 3.0, 4.0], "atr_p": [7, 10, 14]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        n = int(p["rsi_n"])
        r = g.rsi(k, n)
        pk = k.shift(1)
        yukari = (k - pk).clip(lower=0.0)
        asagi = (pk - k).clip(lower=0.0)
        au, ad_ = g.sma(yukari, n), g.sma(asagi, n)

        def rsi_h(k_up, k_dn):
            u = (au * (n - 1) + k_up) / n
            dd = (ad_ * (n - 1) + k_dn) / n
            with np.errstate(divide="ignore", invalid="ignore"):
                return 100.0 - 100.0 / (1.0 + u / dd.where(dd != 0))
        rh = rsi_h((y - pk).clip(lower=0.0), (pk - y).clip(lower=0.0))
        rl = rsi_h((d - pk).clip(lower=0.0), (pk - d).clip(lower=0.0))
        rp = r.shift(1)
        tr = pd.concat([rh - rl, (rh - rp).abs(), (rl - rp).abs()], axis=1).max(axis=1, skipna=False)
        atr_r = g.sma(tr, int(p["atr_p"]))
        t3 = _t3(r, int(p["t3_n"]), float(p["t3_v"]))
        pm = pd.Series(_pmax(t3.to_numpy(), atr_r.to_numpy(), float(p["carpan"])), index=k.index)
        al, sat = kesis_yukari(t3, pm), kesis_asagi(t3, pm)
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, al, sat, sl, ss, cikis_l=sat, cikis_s=al)


# ================================================================== 157 — Range Filter + yumuşak Heikin-Ashi
def _range_filter(k: pd.Series, per: int, carpan: float):
    aralik = g.ema((k - k.shift(1)).abs(), per)
    sm = (g.ema(aralik, per * 2 - 1) * carpan).to_numpy()
    c = k.to_numpy(dtype=float)
    n = len(c)
    filt = np.full(n, np.nan)
    yon = np.zeros(n, dtype="int64")
    onceki = c[0] if n else np.nan
    dr = 0
    for i in range(n):
        if np.isnan(sm[i]):
            f = c[i]
        elif c[i] > onceki:
            f = max(onceki, c[i] - sm[i])
        else:
            f = min(onceki, c[i] + sm[i])
        if f > onceki:
            dr = 1
        elif f < onceki:
            dr = -1
        filt[i], yon[i] = f, dr
        onceki = f
    return pd.Series(filt, index=k.index), pd.Series(yon, index=k.index), pd.Series(sm, index=k.index)


def _yumusak_ha(a, y, d, k, on: int, son: int):
    """Önce EMA(on) ile OHLC yumuşat, Heikin-Ashi'ye çevir, sonra EMA(son): -> (açılış, kapanış)."""
    o1, h1, l1, c1 = (x.ewm(span=on, adjust=False).mean().to_numpy() for x in (a, y, d, k))
    hc = (o1 + h1 + l1 + c1) / 4.0
    ho = np.empty(len(hc))
    for i in range(len(hc)):
        ho[i] = (o1[i] + c1[i]) / 2.0 if i == 0 else (ho[i - 1] + hc[i - 1]) / 2.0
    o2 = pd.Series(ho, index=k.index).ewm(span=son, adjust=False).mean()
    c2 = pd.Series(hc, index=k.index).ewm(span=son, adjust=False).mean()
    return o2, c2


class RfHaScalper(Strateji):
    """dis__rf-ha-scalper (scalp) — dis_envanter 157, TradingView "RF-HA Trend Scalper" (U0wTnRuE).
    Kural: Range Filter (örnekleme 50, çarpan 2.0) yönü ile yumuşatılmış Heikin-Ashi (ön 6 / son 8 EMA) yönü AYNI ve üst zaman
    dilimi (tf_ust, 1h; kapanmış mumlar) yumuşak HA yönü de aynıysa durum +1/-1; durum yeni oluştuğunda giriş. SMI(8,3,3) "kovalama"
    filtresi: long için SMI < 60, short için SMI > -60. Stop = giriş -/+ 2.5 x ATR(14) ve izleyen ATR stopu (CikisAyarlari);
    Range Filter ters dönünce yönlü çıkış. Kaynağın çıkış sonrası bekleme (cooldown) ve risk-bazlı boyutlandırması motor/risk
    katmanında; sabit R hedefi kapalı (kaynak varsayılanı)."""
    ad = "dis__rf-ha-scalper"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.5)
    varsayilan_parametreler = {"rf_per": 50, "rf_carpan": 2.0, "ha_on": 6, "ha_son": 8, "tf_ust": "1h", "smi_n": 8, "smi_s1": 3,
                               "smi_s2": 3, "smi_max": 60.0, "atr_n": 14, "atr_stop": 2.5}
    parametre_izgarasi = {"rf_per": [30, 50, 70], "rf_carpan": [1.5, 2.0, 3.0], "atr_stop": [2.0, 2.5, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, y, d, k = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        _, rf, _ = _range_filter(k, int(p["rf_per"]), float(p["rf_carpan"]))
        o2, c2 = _yumusak_ha(a, y, d, k, int(p["ha_on"]), int(p["ha_son"]))
        ha = pd.Series(np.where(c2 >= o2, 1, -1), index=k.index)

        def ust_ozet(u):
            uo, uc = _yumusak_ha(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"], int(p["ha_on"]), int(p["ha_son"]))
            return pd.Series(np.where(uc >= uo, 1.0, -1.0), index=u.index)
        hd = ust_zaman(mumlar, p["tf_ust"], ust_ozet)
        sn = int(p["smi_n"])
        hh, ll = y.rolling(sn, min_periods=sn).max(), d.rolling(sn, min_periods=sn).min()
        s1, s2 = int(p["smi_s1"]), int(p["smi_s2"])
        rel = ((k - (hh + ll) / 2).ewm(span=s1, adjust=False).mean()).ewm(span=s2, adjust=False).mean()
        fark = ((hh - ll).ewm(span=s1, adjust=False).mean()).ewm(span=s2, adjust=False).mean()
        smi = (rel / (fark / 2.0).where(fark != 0) * 100.0).fillna(0.0)
        durum = pd.Series(np.where((rf == 1) & (ha == 1) & (hd == 1), 1, np.where((rf == -1) & (ha == -1) & (hd == -1), -1, 0)),
                          index=k.index)
        long_ok = (durum == 1) & (durum.shift(1) != 1) & (smi < float(p["smi_max"]))
        short_ok = (durum == -1) & (durum.shift(1) != -1) & (smi > -float(p["smi_max"]))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=rf == -1, cikis_s=rf == 1)


# ================================================================== 170 — 30 dk pivot + mum hacim deltası (ters)
def _pivot_ffill(u: pd.DataFrame, sol: int, sag: int) -> pd.DataFrame:
    return pd.DataFrame({"ph": _pivot_yuksek(u["yuksek"], sol, sag).ffill(), "pl": _pivot_dusuk(u["dusuk"], sol, sag).ffill()})


class Pivot30DeltaTers(Strateji):
    """dis__pivot30-delta-ters (scalp, 5 dk) — dis_envanter 170, TradingView "Simplified 30m Event Strategy - Reverse" (kAYwdfND).
    Kural: 30 dk grafiğin pivot tepe/dip'leri (sol 2 / sağ 3; kapanmış 30 dk mumlarla) son tepe (PH) ve son dip (PL) olur; PH-PL
    aralığı geçerli = en az `min_aralik_atr` x ATR. "Delta" = mumun hacmi, yeşilse +hacim, kırmızıysa -hacim. TERS giriş: kapanış >
    PL ve delta < 0 (satış mumu) -> long; kapanış < PH ve delta > 0 -> short. `cikis_mum` (6) mum sonra zaman çıkışı. Stop = giriş
    -/+ atr_stop x ATR. Uyarlama: kaynağın mutlak "min aralık 5 puan" eşiği ATR katına çevrildi."""
    ad = "dis__pivot30-delta-ters"
    stil = "scalp"
    varsayilan_parametreler = {"tf_ust": "30m", "sol": 2, "sag": 3, "min_aralik_atr": 3.0, "cikis_mum": 6, "atr_n": 14, "atr_stop": 2.0}
    parametre_izgarasi = {"min_aralik_atr": [1.0, 3.0, 5.0], "cikis_mum": [4, 6, 10], "atr_stop": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, k, h = mumlar["acilis"], mumlar["kapanis"], mumlar["hacim"]
        piv = ust_zaman(mumlar, p["tf_ust"], lambda u: _pivot_ffill(u, int(p["sol"]), int(p["sag"])))
        atr, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        gecerli = piv["ph"].notna() & piv["pl"].notna() & ((piv["ph"] - piv["pl"]) >= float(p["min_aralik_atr"]) * atr)
        delta = pd.Series(np.where(k > a, h, np.where(k < a, -h, 0.0)), index=k.index)
        long_ok = gecerli & (k > piv["pl"]) & (delta < 0)
        short_ok = gecerli & (k < piv["ph"]) & (delta > 0)
        return kur(mumlar, long_ok, short_ok, sl, ss, zaman_cikisi=float(p["cikis_mum"]))


# ================================================================== 179 / 185 — LazyBear sıkışma momentumu
class SqzmomLbPine(Strateji):
    """dis__sqzmom-lb-pine (daytrade) — dis_envanter 179, TradingView "Squeeze Momentum Indicator Strategy [LazyBear+PineIndicators]"
    (G40dtEbK). Kural: LazyBear momentumu val = linreg(kapanış - (orta(HH,LL)+SMA)/2, 20); sıkışma = Bollinger(20, sapma = Keltner
    çarpanı 1.5 — kaynak kodu BB için de multKC kullanır) KC(20, 1.5 x TR-SMA) içinde. LONG: sıkışma BİTTİ (önceki mum sıkışık, bu
    mum değil) VE val > önceki val VE val > önceki 100 mumun en düşük val'ı VE kapanış > önceki kapanış VE kapanış > EMA(100);
    çıkış val < önceki val. SHORT (kaynaktaki gibi sıkışmanın BAŞLADIĞI muma karşı): sıkışma BAŞLADI VE val düşüyor VE val < önceki
    100 mumun en yüksek val'ı VE kapanış < önceki kapanış VE kapanış < EMA(100); çıkış val > önceki val. Stop yok -> ATR felaket stopu."""
    ad = "dis__sqzmom-lb-pine"
    stil = "daytrade"
    varsayilan_parametreler = {"n": 20, "carpan": 1.5, "val_pen": 100, "ema_n": 100, "short": True, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"n": [14, 20, 26], "val_pen": [50, 100, 200], "ema_n": [50, 100, 200]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        sq = sikisma_momentum(y, d, k, int(p["n"]), float(p["carpan"]), int(p["n"]), float(p["carpan"]))
        val = sq["val"]
        on, off = sq["sqz_on"], sq["sqz_off"]
        w = int(p["val_pen"])
        ema = g.ema(k, int(p["ema_n"]))
        long_ok = (off & on.shift(1, fill_value=False) & (val > val.shift(1)) & (val > val.rolling(w, min_periods=w).min().shift(1))
                   & (k > k.shift(1)) & (k > ema))
        short_ok = (on & off.shift(1, fill_value=False) & (val < val.shift(1)) & (val < val.rolling(w, min_periods=w).max().shift(1))
                    & (k < k.shift(1)) & (k < ema)) & bool(p["short"])
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=val < val.shift(1), cikis_s=val > val.shift(1))


class SqzmomLbKlasik(Strateji):
    """dis__sqzmom-lb-klasik (daytrade) — dis_envanter 185, TradingView "Strategy for Squeeze Momentum Indicator [LazyBear]" (qp9BoNyS).
    Kural: BB(14, 2σ) / KC(16, 1.5 x TR-SMA) sıkışması; renk durumları: sıkışma YOK -> "aqua" (sqz_off). LONG: aqua durumuna bu mumda
    geçildi VE momentum > 0 ve yükseliyor (açık yeşil); çıkış: momentum > 0 ama düşüyor. SHORT: aqua'ya geçildi VE momentum < 0 ve
    düşüyor; çıkış: momentum < 0 ama yükseliyor. Stop yok -> ATR felaket stopu. Atlananlar: "erken giriş" (extreme) modu ve
    momentum alt sınırı filtresi (kaynakta varsayılan kapalı), test tarih aralığı."""
    ad = "dis__sqzmom-lb-klasik"
    stil = "daytrade"
    varsayilan_parametreler = {"bb_n": 14, "bb_k": 2.0, "kc_n": 16, "kc_k": 1.5, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"bb_n": [14, 20], "kc_n": [16, 20, 24], "kc_k": [1.0, 1.5, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        sq = sikisma_momentum(y, d, k, int(p["bb_n"]), float(p["bb_k"]), int(p["kc_n"]), float(p["kc_k"]))
        val, off = sq["val"], sq["sqz_off"]
        yeni = off & ~off.shift(1, fill_value=False)
        yuk, dus = val > val.shift(1), val < val.shift(1)
        long_ok = yeni & (val > 0) & yuk
        short_ok = yeni & (val < 0) & dus
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, long_ok, short_ok, sl, ss, cikis_l=(val > 0) & ~yuk, cikis_s=(val < 0) & ~dus)


# ================================================================== 186 — HMA(50) + Supertrend
class HmaSupertrend(Strateji):
    """dis__hma-supertrend (daytrade) — dis_envanter 186, TradingView "HMA 50 + Supertrend Sniper" (3SHJZytF).
    Kural: HMA(50) yükseliyor VE Supertrend(10, 3) yükseliş yönünde -> long; HMA düşüyor VE Supertrend düşüş -> short; ikisi
    çelişirse ("choppy") pozisyon kapanır. Kaynakta stop yok -> ATR felaket stopu. Tarih filtresi kodlanmadı."""
    ad = "dis__hma-supertrend"
    stil = "daytrade"
    varsayilan_parametreler = {"hma_n": 50, "st_atr": 10, "st_carpan": 3.0, "atr_n": 14, "atr_stop": 3.0}
    parametre_izgarasi = {"hma_n": [34, 50, 80], "st_carpan": [2.0, 3.0, 4.0], "atr_stop": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        hm = _hull(k, int(p["hma_n"]))
        st = g.supertrend(y, d, k, int(p["st_atr"]), float(p["st_carpan"]))["yon"]
        yuk, dus = hm > hm.shift(1), hm < hm.shift(1)
        boga, ayi = yuk & (st == 1), dus & (st == -1)
        choppy = (yuk & (st == -1)) | (dus & (st == 1))
        _, sl, ss = atr_stoplari(mumlar, int(p["atr_n"]), float(p["atr_stop"]))
        return kur(mumlar, boga, ayi, sl, ss, cikis_l=choppy | ayi, cikis_s=choppy | boga)


# ================================================================== 189 — Supertrend + HTF Supertrend + hacimli Donchian
class StDonchianHtf(Strateji):
    """dis__st-donchian-htf (daytrade) — dis_envanter 189, TradingView "Supertrend Donchian Breakout" (FDeprmix).
    Kural: Supertrend(10, 3) yükselişte VE üst zaman dilimi (tf_ust 4h, kapanmış mumlar) Supertrend'i de yükselişte VE kapanış
    önceki `don_n` (20) mumun en yükseğinin üstünde (kırılım) VE hacim > `hacim_k` (1.5) x SMA(20) -> long. Short ayna (kaynakta
    varsayılan kapalı; `short`). Stop = giriş -/+ 2 x ATR(14), hedef 3 x ATR. Supertrend yön değiştirirse çıkış.
    DÜZELTME: kaynak kodu long koşulunda 'kapanış > ALT kanal' yazar (mantık hatası; açıklama "Donchian kırılımı" der) -> burada
    üst kanal kırılımı kullanıldı (short için alt kanalın altı)."""
    ad = "dis__st-donchian-htf"
    stil = "daytrade"
    varsayilan_parametreler = {"st_atr": 10, "st_carpan": 3.0, "tf_ust": "4h", "don_n": 20, "hacim_n": 20, "hacim_k": 1.5,
                               "atr_n": 14, "atr_stop": 2.0, "atr_hedef": 3.0, "short": False}
    parametre_izgarasi = {"don_n": [10, 20, 40], "hacim_k": [1.0, 1.5, 2.0], "atr_stop": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d, h = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["hacim"]
        st = g.supertrend(y, d, k, int(p["st_atr"]), float(p["st_carpan"]))["yon"]
        ust = ust_zaman(mumlar, p["tf_ust"], lambda u: g.supertrend(u["yuksek"], u["dusuk"], u["kapanis"], int(p["st_atr"]),
                                                                    float(p["st_carpan"]))["yon"].astype(float))
        n = int(p["don_n"])
        kan_u = y.rolling(n, min_periods=n).max().shift(1)
        kan_a = d.rolling(n, min_periods=n).min().shift(1)
        hv = h > g.sma(h, int(p["hacim_n"])) * float(p["hacim_k"])
        long_ok = (st == 1) & (ust == 1) & (k > kan_u) & hv
        short_ok = (st == -1) & (ust == -1) & (k < kan_a) & hv & bool(p["short"])
        a = g.atr(y, d, k, int(p["atr_n"]))
        s, t = float(p["atr_stop"]) * a, float(p["atr_hedef"]) * a
        return kur(mumlar, long_ok, short_ok, k - s, k + s, k + t, k - t, cikis_l=st == -1, cikis_s=st == 1)


# ================================================================== 193 — pivot kırılımı + hacim osilatörü + EMA150
class PivotHacimEma150(Strateji):
    """dis__pivot-hacim-ema150 (scalp, 5 dk) — dis_envanter 193, TradingView "SUPPORT RESISTANCE STRATEGY [5MIN TF]" (KOfsPM9h).
    Kural: direnç = son onaylı pivot tepe (sol `sol` 10 / sağ `sag` 15 mum), destek = son pivot dip (bir mum gecikmeli kullanılır).
    LONG: kapanış direnci yukarı keser VE hacim osilatörü 100*(EMA5-EMA10)/EMA10 > `hacim_esik` (20) VE mum alt fitili gövdeden
    büyük DEĞİL VE kapanış >= EMA(150). SHORT: kapanış desteği aşağı keser VE aynı hacim koşulu VE üst fitil gövdeden büyük değil
    VE kapanış <= EMA(150). Stop = ATR(14) x 3.2 izleyen (kapanıştan; CikisAyarlari). Gün sonu: `gun_sonu` True ise UTC gün
    sonunda kapanış (kaynak NSE 09:15-14:45 seansı + 14:55 kapanış kodlanmadı; seans filtresi varlığa özgü)."""
    ad = "dis__pivot-hacim-ema150"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.2)
    varsayilan_parametreler = {"sol": 10, "sag": 15, "hacim_esik": 20.0, "ema_n": 150, "atr_n": 14, "atr_k": 3.2, "gun_sonu": False}
    parametre_izgarasi = {"sol": [8, 10, 15], "sag": [10, 15, 20], "atr_k": [2.5, 3.2, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, y, d, k, h = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis", "hacim"))
        dirc = _pivot_yuksek(y, int(p["sol"]), int(p["sag"])).ffill().shift(1)
        dest = _pivot_dusuk(d, int(p["sol"]), int(p["sag"])).ffill().shift(1)
        v1, v2 = g.ema(h, 5), g.ema(h, 10)
        osc = 100.0 * (v1 - v2) / v2.where(v2 != 0)
        ema = g.ema(k, int(p["ema_n"]))
        long_ok = kesis_yukari(k, dirc) & (osc > p["hacim_esik"]) & ~((a - d) > (k - a)) & (k >= ema)
        short_ok = kesis_asagi(k, dest) & (osc > p["hacim_esik"]) & ~((a - k) < (y - a)) & (k <= ema)
        atr = g.atr(y, d, k, int(p["atr_n"])) * float(p["atr_k"])
        return kur(mumlar, long_ok, short_ok, k - atr, k + atr, gun_sonu=bool(p["gun_sonu"]))


# ================================================================== 20 / 213 — Fibonacci çarpanlı Supertrend ailesi
def _fib_supertrend(y, d, k, atr_n: int, f1: float, f2: float, f3: float, yumusat: int):
    """Üç Supertrend çizgisinin ortalaması ve bunun EMA'sı (yumuşatılmış)."""
    ort = sum(g.supertrend(y, d, k, atr_n, f)["cizgi"] for f in (f1, f2, f3)) / 3.0
    return ort, g.ema(ort, int(yumusat))


class TrendlineFibst(Strateji):
    """dis__trendline-fibst (daytrade) — dis_envanter 213, TradingView "Trendline Breaks with Multi Fibonacci Supertrend" (aVzNdTMg).
    Kural: Fibonacci çarpanlı (0.618 / 1.618 / 2.618) üç Supertrend'in (ATR 13) ortalaması, EMA(21) ile yumuşatılır. Eğimli trend
    çizgileri: her onaylı pivot tepe (swing 8) için tepeden başlayıp her mumda ATR(8)/8 x `egim_k` kadar AŞAĞI inen direnç çizgisi,
    pivot dip için yukarı çıkan destek çizgisi. LONG: kapanış direnç çizgisini YENİ kırar (durum 0 -> 1) VE DI+ > DI- (DMI 13) VE
    kapanış > yumuşatılmış Supertrend; SHORT ayna. Çıkış: önceki kapanışın yumuşatılmış Supertrend'i ters kesmesi. Stop = giriş
    -/+ `atr_stop` x ATR(13); hedef %`hedef_pct`. Atlananlar: kaynağın SMA(2/3) kesişimi (tanımlı ama girişte kullanılmıyor),
    başabaş/izleyen kâr alma, kısmi kâr (kapalı varsayılanlar)."""
    ad = "dis__trendline-fibst"
    stil = "daytrade"
    varsayilan_parametreler = {"atr_n": 13, "f1": 0.618, "f2": 1.618, "f3": 2.618, "yumusat": 21, "swing": 8, "egim_k": 1.0,
                               "dmi_n": 13, "atr_stop": 8.0, "hedef_pct": 0.01, "short": True}
    parametre_izgarasi = {"swing": [6, 8, 12], "atr_stop": [3.0, 5.0, 8.0], "hedef_pct": [0.01, 0.02, 0.03]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        _, yumus = _fib_supertrend(y, d, k, int(p["atr_n"]), float(p["f1"]), float(p["f2"]), float(p["f3"]), int(p["yumusat"]))
        sw = int(p["swing"])
        ph, pl = _pivot_yuksek(y, sw, sw).to_numpy(), _pivot_dusuk(d, sw, sw).to_numpy()
        egim = (g.atr(y, d, k, sw) / sw * float(p["egim_k"])).to_numpy()
        kn = k.to_numpy(dtype=float)
        n = len(kn)
        ust_s = np.zeros(n)
        alt_s = np.zeros(n)
        u_t = a_t = u_e = a_e = 0.0
        du = da = 0
        du_s = np.zeros(n)
        da_s = np.zeros(n)
        for i in range(n):
            if not np.isnan(ph[i]):
                u_e = egim[i] if not np.isnan(egim[i]) else 0.0
                u_t = ph[i]
            else:
                u_t = u_t - u_e
            if not np.isnan(pl[i]):
                a_e = egim[i] if not np.isnan(egim[i]) else 0.0
                a_t = pl[i]
            else:
                a_t = a_t + a_e
            ust_s[i], alt_s[i] = u_t, a_t
            du = 0 if not np.isnan(ph[i]) else (1 if kn[i] > u_t else du)
            da = 0 if not np.isnan(pl[i]) else (1 if kn[i] < a_t else da)
            du_s[i], da_s[i] = du, da
        gecerli_u = pd.Series(ust_s != 0.0, index=k.index)
        yeni_u = pd.Series(du_s, index=k.index).diff().fillna(0) > 0
        yeni_a = pd.Series(da_s, index=k.index).diff().fillna(0) > 0
        dmi = g.adx(y, d, k, int(p["dmi_n"]))
        long_ok = yeni_u & gecerli_u & (dmi["arti_di"] > dmi["eksi_di"]) & (k > yumus)
        short_ok = yeni_a & (dmi["eksi_di"] > dmi["arti_di"]) & (k < yumus) & bool(p["short"])
        a = g.atr(y, d, k, int(p["atr_n"]))
        s = float(p["atr_stop"]) * a
        hp = float(p["hedef_pct"])
        return kur(mumlar, long_ok, short_ok, k - s, k + s, k * (1 + hp), k * (1 - hp),
                   cikis_l=kesis_asagi(k.shift(1), yumus), cikis_s=kesis_yukari(k.shift(1), yumus))


class FibstPullback(Strateji):
    """dis__fibst-pullback (daytrade) — dis_envanter 20, TradingView "Adaptive Fibonacci Pullback System" (bOcHnaiQ, FibonacciFlux).
    NOT: envanter özeti bu dosyayı "Supertrend kesişimi + Fib stop" diye anlatır; gerçek kural aşağıdaki gibidir (dosya esas).
    Kural: Fibonacci çarpanlı (0.618 / 1.618 / 2.618) üç Supertrend'in (ATR 8) ortalaması `ortalama`, EMA(21) ile yumuşatılmışı
    `yumusak`. AMA kanalı: ama_n (55) mumluk en yüksek/en düşükteki değişim oranından uyarlanan hızla yüksek ve düşüğü izleyen iki
    çizgi; orta çizgi `ama_orta`. LONG (geri çekilme): düşük < ortalama VE kapanış > yumuşak VE önceki kapanış > ama_orta VE kapanış >
    ama_orta (+ isteğe bağlı üst zaman dilimi RSI süzgeci: tf_rsi RSI(7) > 70, kaynak varsayılanı açık; `rsi_filtre`). SHORT ayna.
    Çıkış: önceki kapanışın yumuşak çizgiyi ters kesmesi. Stop giriş -/+ `atr_stop` x ATR(13), hedef %`hedef_pct`. Atlananlar:
    MACD/hacim MTF süzgeçleri (kaynakta varsayılan kapalı), izleyen kâr alma/başabaş (varsayılan açık; motorun izleyen stopu yok)."""
    ad = "dis__fibst-pullback"
    stil = "daytrade"
    varsayilan_parametreler = {"st_atr": 8, "f1": 0.618, "f2": 1.618, "f3": 2.618, "yumusat": 21, "ama_n": 55,
                               "rsi_filtre": True, "tf_rsi": "1h", "rsi_n": 7, "rsi_ust": 70.0, "rsi_alt": 30.0,
                               "atr_n": 13, "atr_stop": 8.0, "hedef_pct": 0.05, "short": True}
    parametre_izgarasi = {"ama_n": [34, 55, 89], "atr_stop": [4.0, 6.0, 8.0], "hedef_pct": [0.02, 0.05, 0.08]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        ort, yumus = _fib_supertrend(y, d, k, int(p["st_atr"]), float(p["f1"]), float(p["f2"]), float(p["f3"]), int(p["yumusat"]))
        n = int(p["ama_n"])
        hh_d = np.sign(y.rolling(n, min_periods=n).max().diff()).clip(lower=0.0)
        ll_d = np.sign(-d.rolling(n, min_periods=n).min().diff()).clip(lower=0.0)
        olay = ((hh_d > 0) | (ll_d > 0)).astype(float).where(hh_d.notna() & ll_d.notna())
        tc = (olay.rolling(n, min_periods=n).mean() ** 2).to_numpy()
        yn, dn = y.to_numpy(dtype=float), d.to_numpy(dtype=float)
        m = len(yn)
        ama1, ama2 = np.empty(m), np.empty(m)
        o1, o2 = yn[0] if m else np.nan, dn[0] if m else np.nan
        for i in range(m):
            t = 0.0 if np.isnan(tc[i]) else tc[i]
            o1 = o1 + t * (yn[i] - o1)
            o2 = o2 + t * (dn[i] - o2)
            ama1[i], ama2[i] = o1, o2
        orta = pd.Series((ama1 + ama2) / 2.0, index=k.index)
        long_ok = (d < ort) & (k > yumus) & (k.shift(1) > orta) & (k > orta)
        short_ok = (y > ort) & (k < yumus) & (k.shift(1) < orta) & (k < orta) & bool(p["short"])
        if p["rsi_filtre"]:
            r = ust_zaman(mumlar, p["tf_rsi"], lambda u: g.rsi(u["kapanis"], int(p["rsi_n"])))
            long_ok &= r > float(p["rsi_ust"])
            short_ok &= r < float(p["rsi_alt"])
        a = g.atr(y, d, k, int(p["atr_n"]))
        s = float(p["atr_stop"]) * a
        hp = float(p["hedef_pct"])
        return kur(mumlar, long_ok, short_ok, k - s, k + s, k * (1 + hp), k * (1 - hp),
                   cikis_l=kesis_asagi(k.shift(1), yumus), cikis_s=kesis_yukari(k.shift(1), yumus))


# ================================================================== 219 — pivot dönüşü arz/talep bölgesi
class PivotSdBolge(Strateji):
    """dis__pivot-sd-bolge (daytrade) — dis_envanter 219, TradingView "Ultimate Prop Firm [Artillery]" (PkUPYbw7).
    Kural: onaylı pivot (sol 3 / sağ 2) oluştuğu mumda: LONG = yeni pivot DİP VAR VE düşük <= pivot dip + `sd_k` (1.0) x ATR(14)
    ("talep bölgesi") VE RSI(14) >= 40 VE mum yeşil VE hacim >= 0.8 x SMA(20); SHORT = yeni pivot TEPE VE yüksek >= pivot tepe -
    sd_k x ATR VE RSI <= 60 VE mum kırmızı VE hacim koşulu. Stop 1.5 x ATR; hedef 3.5 x ATR; kısmi: 1.0 ATR'de %40, 2.0 ATR'de
    %50 (R cinsinden 0.667R ve 1.333R). `seans` True ise yalnız New York 09:30-15:55'te giriş ve 15:55'te kapanış (kaynak ABD vadelisi).
    Atlananlar: günlük işlem sayısı (5) ve günlük %3.5 zarar sınırı (risk katmanı)."""
    ad = "dis__pivot-sd-bolge"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(kismi=((1.0 / 1.5, 0.4), (2.0 / 1.5, 0.5)))
    varsayilan_parametreler = {"sol": 3, "sag": 2, "sd_k": 1.0, "rsi_n": 14, "rsi_alt": 40.0, "rsi_ust": 60.0, "hacim_n": 20,
                               "hacim_k": 0.8, "atr_n": 14, "sl_k": 1.5, "tp_k": 3.5, "seans": False}
    parametre_izgarasi = {"sd_k": [0.5, 1.0, 1.5], "sl_k": [1.0, 1.5, 2.0], "tp_k": [2.5, 3.5, 4.5]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, y, d, k, h = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis", "hacim"))
        atr = g.atr(y, d, k, int(p["atr_n"]))
        pl = _pivot_dusuk(d, int(p["sol"]), int(p["sag"]))
        ph = _pivot_yuksek(y, int(p["sol"]), int(p["sag"]))
        r = g.rsi(k, int(p["rsi_n"]))
        hv = h >= g.sma(h, int(p["hacim_n"])) * float(p["hacim_k"])
        sd = float(p["sd_k"]) * atr
        long_ok = pl.notna() & (d <= pl + sd) & (r >= p["rsi_alt"]) & (k > a) & hv
        short_ok = ph.notna() & (y >= ph - sd) & (r <= p["rsi_ust"]) & (k < a) & hv
        son = _bos(k.index)
        if p["seans"]:
            yer = _yerel(k.index, "America/New_York")
            dk = pd.Series(yer.hour * 60 + yer.minute, index=k.index)
            ic = (dk >= 570) & (dk <= 955)
            long_ok &= ic
            short_ok &= ic
            son = dk >= 955
        s, t = float(p["sl_k"]) * atr, float(p["tp_k"]) * atr
        out = kur(mumlar, long_ok, short_ok, k - s, k + s, k + t, k - t)
        out["cikis"] = son.astype(bool)
        return out
