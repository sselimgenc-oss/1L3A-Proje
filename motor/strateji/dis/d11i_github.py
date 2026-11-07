"""D11-i (GitHub kaynaklı yeni aileler, i grubu) — freqtrade NostalgiaForInfinity / BBMod / ClucHA / kripto-bot / SMC Pine
kurallarının KENDİ KODUMUZLA yeniden yazımı. KOD KOPYALANMADI (kaynaklar GPL/AGPL): kural özetleri VERİDİR; her sınıfın
docstring'inde kaynak repo+dosya yazılıdır. Ad öneki `dis__`. Hepsi nedensel (lookahead yok).

Ortak uyarlamalar
  * Scalp: karar 11 gereği >= 15m; varsayılan taban 15m. 1-5 dk dayanaklı kurallar en yakın 15m/1h karşılığına kaydırıldı.
  * Üst zaman dilimi (`ust_tf`) yalnız kapanmış HTF mumlarından hesaplanır (htf.ust_zaman; kapanış anından itibaren kullanılabilir).
  * Mutlak eşikler (pip, USD, mutlak EWO) yüzde / ATR / orana çevrildi; çevrim her sınıfta "VARSAYIM" olarak yazılı.
  * Orijinallerin stopsuz / ekleme (DCA) / "zararda tut" kısımları ALINMADI: yalnız giriş + ATR stoplu çıkış
    (stop_atr_k x ATR; ek olarak sinyal çıkışı / zaman çıkışı / iz süren stop).
  * Freqtrade `minimal_roi` / `trailing_stop` motorda yok: zaman_cikisi, iz süren ATR stop ve sinyal çıkışı ile yaklaşıldı.

Aileler (14 sınıf): ust-tf-ma-rsi-momentum, aroon-stochrsi-ema-dip, bb-alt-bant-osilator, cci-aroon-dogus, cok-osilator-ekstrem,
cok-tf-stokastik-dip, dortlu-stokastik-rotasyon, ema-hizali-olgun-yukselis, ewo-ema-ofset, getiri-oynaklik-momentum,
ha-bb40-cluc, nfi-short-cokus, smc-htf-supurme-choch, vwap-alt-bant-dip.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d2 import stoch_rsi
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban, cmf, mfi
from motor.strateji.dis._gosterge_d5 import cti
from motor.strateji.dis._gosterge_d9 import ardisik_say, fisher_rsi, pivot_seviye, rmi
from motor.strateji.gostergeler_b2 import cci, gecis, heikin_ashi, yukari_kesis, asagi_kesis
from motor.strateji.temel import Strateji

from motor.strateji.dis._gosterge_d11i import aroon_asagi, aroon_yukari, ewo_yuzde, obv, ust_tf, vwap_bant, williams_r


def _stokf(m, n: int) -> pd.Series:
    """Hızlı stokastik %K(n) (0-100)."""
    return g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], int(n), 1)["k"]


# =============================================================================== 1. Üst TF MA trendinde RSI momentum
class UstTfMaRsiMomentum(D3Taban):
    """dis__ust-tf-ma-rsi-momentum (scalp, 15m; üst TF 1h) — kaynak: kripto-bot deposu `MultiTimeframeStrategy`
    (github_g2_kripto_bot). Orijinal: 15dk SMA5 > SMA20 ise trend yukarı; 5dk RSI >= 70 + trend yukarı -> long, RSI <= 30 + trend
    aşağı -> short; trend dönerse ya da RSI 50'yi geçerse kapat. UYARLAMA: 5dk/15dk yerine işlem TF 15m / trend TF 1h (min 15m).
    Ölçülebilir tanım: trend = üst TF SMA(ma_hizli) - SMA(ma_yavas) işareti (kapanmış HTF mumları). Giriş: trend yukarı VE RSI(15m)
    >= rsi_ust'a ilk geçiş (short: trend aşağı VE RSI <= 100 - rsi_ust). Çıkış: trend ters döner ya da RSI rsi_cik (50) çizgisini
    karşı tarafa geçer. VARSAYIM (orijinalde stop yok): stop_atr_k x ATR, azami 32 mum. swing__rsi-momentum-esik'ten farkı: üst TF
    burada MA trendi (RSI değil)."""
    ad = "dis__ust-tf-ma-rsi-momentum"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.5, "zaman_cikisi": 32, "ust_tf": "1h",
                               "ma_hizli": 5, "ma_yavas": 20, "rsi_n": 14, "rsi_ust": 70.0, "rsi_cik": 50.0}
    parametre_izgarasi = {"rsi_ust": [60.0, 65.0, 70.0], "ust_tf": ["1h", "4h"], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        h, y = int(p["ma_hizli"]), int(p["ma_yavas"])
        u = ust_tf(m, p["ust_tf"], lambda x: pd.DataFrame({"fark": g.sma(x["kapanis"], h) - g.sma(x["kapanis"], y)}))["fark"]
        yukari, asagi = u > 0, u < 0
        r = g.rsi(k, int(p["rsi_n"]))
        return {"long": gecis(yukari & (r >= p["rsi_ust"])), "short": gecis(asagi & (r <= 100.0 - p["rsi_ust"])),
                "cikis_long": ~yukari | (r < p["rsi_cik"]), "cikis_short": ~asagi | (r > p["rsi_cik"])}


# =============================================================================== 2. Aroon + StochRSI + EMA ofset dip
class AroonStochRsiEmaDip(D3Taban):
    """dis__aroon-stochrsi-ema-dip (scalp, 15m) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py` (pump/quick/
    scalp/rapid/grind giriş kolları; yalnız çekirdek). Üç kol (`kol`), hepsi YALNIZ LONG:
      "ema_ofset": Aroon-up(14) < aroon_ust VE StochRSI %K < sk_alt VE kapanış < EMA(20) x ofset;
      "rsi_aroon": RSI(14) < rsi_alt VE Aroon-down(14) > aroon_asagi_min VE kapanış < EMA(20) x ofset;
      "wr_bb":     Williams %R(14) < wr_alt VE kapanış < Bollinger(20,2) alt bandı.
    Ek süzgeç (opsiyonel): (EMA50 - EMA200)/kapanış > ema_fark (varsayılan -1 = kapalı).
    VARSAYIM: NFI'nın çoklu-TF süzgeç yığını alınmadı; eşikler orijinal aralıkların ortası. Çıkış: kapanış EMA(20)'nin üstüne
    döner ya da zaman çıkışı (24 mum); ATR stop."""
    ad = "dis__aroon-stochrsi-ema-dip"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 24, "kol": "ema_ofset", "aroon_n": 14,
                               "aroon_ust": 30.0, "sk_alt": 20.0, "ema_n": 20, "ofset": 0.95, "rsi_alt": 36.0,
                               "aroon_asagi_min": 75.0, "wr_alt": -95.0, "ema_fark": -1.0}
    parametre_izgarasi = {"ofset": [0.944, 0.95, 0.96], "sk_alt": [10.0, 20.0, 30.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        ema = g.ema(k, int(p["ema_n"]))
        alt_ofset = k < ema * p["ofset"]
        if p["kol"] == "ema_ofset":
            giris = (aroon_yukari(y, int(p["aroon_n"])) < p["aroon_ust"]) & (stoch_rsi(k)["k"] < p["sk_alt"]) & alt_ofset
        elif p["kol"] == "rsi_aroon":
            giris = (g.rsi(k, 14) < p["rsi_alt"]) & (aroon_asagi(d, int(p["aroon_n"])) > p["aroon_asagi_min"]) & alt_ofset
        elif p["kol"] == "wr_bb":
            giris = (williams_r(y, d, k, 14) < p["wr_alt"]) & (k < g.bollinger(k, 20, 2.0)["alt"])
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        if p["ema_fark"] > -1.0:
            giris &= (g.ema(k, 50) - g.ema(k, 200)) / k > p["ema_fark"]
        return {"long": gecis(giris), "cikis_long": k > ema}


# =============================================================================== 3. BB alt bant + osilatör dip
class BbAltBantOsilator(D3Taban):
    """dis__bb-alt-bant-osilator (scalp, 15m) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py` ve freqtrade
    BBMod (github_g1_freqtrade). Hızlı düşüş dibi, üç kol (`kol`), YALNIZ LONG:
      "bb3":       Bollinger(20,3) genişliği ((üst-alt)/orta) > gen_min VE kapanış < BB3 alt x bant_pay VE RMI(8) < 35 VE
                   CCI(25) <= -133 VE StochRSI %K < 25 VE tek mumluk kapanış düşüşü >= dusus_min;
      "ema_acik":  EMA26 > EMA12 VE (EMA26-EMA12)/açılış > acik VE önceki mumda >= acik_onceki VE kapanış < BB(20,2) alt x bant_pay;
      "mfi_cmf":   MFI(14) > 30 VE CMF(21) > 0.02 VE Williams %R(14) < -80 VE kapanış < BB(20,2) alt x 1.015 VE BB genişliği > %6
                   VE 15 < RSI(14) < 40.
    ÖRTÜŞME: dis__ft-binhv45 / dis__ft-low-bb yalnız BB alt bandıdır; bu aile RMI/CCI/StochRSI, EMA açıklığı, MFI-CMF koşullarını ekler.
    VARSAYIM (mutlak eşikler orana çevrildi): orijinal "BB2/BB3 farkı > 0.025" yerine BB3 genişliği > gen_min (%6); "kapanış farkı
    %1.5" -> dusus_min = %1; EMA açıklığı eşiği %1.2 (önceki mum %0.6). Çıkış: kapanış BB(20,2) orta bandının üstüne çıkar ya da
    32 mum; ATR stop."""
    ad = "dis__bb-alt-bant-osilator"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 32, "kol": "bb3", "bant_pay": 0.995,
                               "gen_min": 0.06, "dusus_min": 0.01, "acik": 0.012, "acik_onceki": 0.006}
    parametre_izgarasi = {"kol": ["bb3", "ema_acik", "mfi_cmf"], "bant_pay": [0.99, 0.995, 1.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, a, v = m["kapanis"], m["yuksek"], m["dusuk"], m["acilis"], m["hacim"]
        bb2 = g.bollinger(k, 20, 2.0)
        if p["kol"] == "bb3":
            bb3 = g.bollinger(k, 20, 3.0)
            gen = (bb3["ust"] - bb3["alt"]) / bb3["orta"]
            giris = ((gen > p["gen_min"]) & (k < bb3["alt"] * p["bant_pay"]) & (rmi(k, 8, 3) < 35.0) & (cci(y, d, k, 25) <= -133.0)
                     & (stoch_rsi(k)["k"] < 25.0) & ((k.shift(1) - k) / k.shift(1) >= p["dusus_min"]))
        elif p["kol"] == "ema_acik":
            fark = (g.ema(k, 26) - g.ema(k, 12)) / a
            giris = (fark > p["acik"]) & (fark.shift(1) >= p["acik_onceki"]) & (k < bb2["alt"] * p["bant_pay"])
        elif p["kol"] == "mfi_cmf":
            gen2 = (bb2["ust"] - bb2["alt"]) / bb2["orta"]
            r = g.rsi(k, 14)
            giris = ((mfi(y, d, k, v, 14) > 30.0) & (cmf(y, d, k, v, 21) > 0.02) & (williams_r(y, d, k, 14) < -80.0)
                     & (k < bb2["alt"] * 1.015) & (gen2 > 0.06) & (r > 15.0) & (r < 40.0))
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        return {"long": gecis(giris), "cikis_long": k > bb2["orta"]}


# =============================================================================== 4. CCI yükselişi + Aroon trend doğuşu
class CciAroonDogus(D3Taban):
    """dis__cci-aroon-dogus (scalp, 15m; üst TF 1h) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py`
    ("CCI diverjansı + Aroon trend doğuşu"; adı diverjans ama kural CCI EĞİMİ + Aroon). YALNIZ LONG. Kural: üst TF (1h) CCI(20)
    [cci_alt, cci_ust] aralığında (-200..-50) VE bir önceki HTF mumundan yüksek (yükseliyor); 15m Aroon-up(14) > aroon_min (50);
    RSI(14) [rsi_alt, rsi_ust]; MFI(14) > 30; 1h CMF(21) > -0.05; kapanış son 48 mum zirvesinin en az geri_pay (%5) altında ama
    48 mum dibinin üstünde; StochRSI %K < sk_alt. UYARLAMA: orijinaldeki 5m Aroon-up > 30 koşulu 5m veri olmadığından atlandı.
    Çıkış (VARSAYIM; kaynakta yok): RSI(14) > rsi_cik (60) ya da 32 mum; ATR stop."""
    ad = "dis__cci-aroon-dogus"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 32, "ust_tf": "1h", "cci_n": 20,
                               "cci_alt": -200.0, "cci_ust": -50.0, "aroon_min": 50.0, "rsi_alt": 20.0, "rsi_ust": 45.0,
                               "mfi_min": 30.0, "cmf_min": -0.05, "pencere": 48, "geri_pay": 0.05, "sk_alt": 30.0,
                               "rsi_cik": 60.0}
    parametre_izgarasi = {"geri_pay": [0.03, 0.05, 0.08], "sk_alt": [20.0, 30.0, 40.0], "rsi_ust": [40.0, 45.0, 50.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        n = int(p["cci_n"])

        def ozet(u):
            c = cci(u["yuksek"], u["dusuk"], u["kapanis"], n)
            return pd.DataFrame({"cci": c, "cci_art": (c > c.shift(1)).astype(float).where(c.shift(1).notna()),
                                 "cmf": cmf(u["yuksek"], u["dusuk"], u["kapanis"], u["hacim"], 21)})
        u = ust_tf(m, p["ust_tf"], ozet)
        pen = int(p["pencere"])
        zirve = y.rolling(pen, min_periods=pen).max()
        dip = d.rolling(pen, min_periods=pen).min()
        r = g.rsi(k, 14)
        giris = ((u["cci"] >= p["cci_alt"]) & (u["cci"] <= p["cci_ust"]) & (u["cci_art"] > 0.5) & (u["cmf"] > p["cmf_min"])
                 & (aroon_yukari(y, 14) > p["aroon_min"]) & (r >= p["rsi_alt"]) & (r <= p["rsi_ust"])
                 & (mfi(y, d, k, v, 14) > p["mfi_min"]) & (k <= zirve * (1.0 - p["geri_pay"])) & (k > dip)
                 & (stoch_rsi(k)["k"] < p["sk_alt"]))
        return {"long": gecis(giris), "cikis_long": r > p["rsi_cik"]}


# =============================================================================== 5. Çoklu osilatör ekstremi + BB dışı
class CokOsilatorEkstrem(D3Taban):
    """dis__cok-osilator-ekstrem (scalp, 15m) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py` (üçlü aşırı
    satım tahliyesi; short: aşırı alım tükenişi #543, dağıtım #545 / BB üst reddi #546). Çoklu-TF "dibe değmedi" süzgeçleri çıkarıldı.
      LONG : RSI(3) < rsi3_alt (5) VE RSI(14) < rsi14_alt (28) VE StochRSI %K < 3 VE Williams %R(14) < -97 VE CMF(21) > 0.05
             VE MFI(14) > 25 VE kapanış < Bollinger(20,2) alt bandı.
      SHORT, `short_kol`="tukenme": ayna — RSI(3) > 100 - rsi3_alt... (varsayılan 85 = rsi3_ust), RSI(14) > rsi14_ust (72),
             StochRSI %K > 85, Williams %R > -10, kapanış > BB üst;
      SHORT, `short_kol`="dagitim": BB genişliği > %4 VE kapanış > BB üst x 1.002 VE RSI(14) > 75 VE üst TF (1h) OBV 5 mumluk
             değişimi < 0 (üst TF onaylamıyor).
    VARSAYIM: "BB genişliği > 4" yüzde (4 puan) kabul edildi; eşikler çok sıkıdır, çok seyrek tetiklenir (ızgara gevşetir).
    Çıkış: kapanış BB orta bandını karşı yönde geçer; 24 mum; ATR stop."""
    ad = "dis__cok-osilator-ekstrem"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "zaman_cikisi": 24, "short_kol": "tukenme",
                               "rsi3_alt": 5.0, "rsi14_alt": 28.0, "rsi3_ust": 85.0, "rsi14_ust": 72.0, "ust_tf": "1h"}
    parametre_izgarasi = {"rsi3_alt": [5.0, 10.0, 15.0], "rsi14_alt": [28.0, 32.0, 36.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        bb = g.bollinger(k, 20, 2.0)
        r3, r14 = g.rsi(k, 3), g.rsi(k, 14)
        sk = stoch_rsi(k)["k"]
        wr = williams_r(y, d, k, 14)
        long = ((r3 < p["rsi3_alt"]) & (r14 < p["rsi14_alt"]) & (sk < 3.0) & (wr < -97.0)
                & (cmf(y, d, k, v, 21) > 0.05) & (mfi(y, d, k, v, 14) > 25.0) & (k < bb["alt"]))
        if p["short_kol"] == "tukenme":
            short = (r3 > p["rsi3_ust"]) & (r14 > p["rsi14_ust"]) & (sk > 85.0) & (wr > -10.0) & (k > bb["ust"])
        elif p["short_kol"] == "dagitim":
            obv_d = ust_tf(m, p["ust_tf"], lambda u: pd.DataFrame({"d": obv(u["kapanis"], u["hacim"]).diff(5)}))["d"]
            gen = (bb["ust"] - bb["alt"]) / bb["orta"] * 100.0
            short = (gen > 4.0) & (k > bb["ust"] * 1.002) & (r14 > 75.0) & (obv_d < 0)
        else:
            raise ValueError(f"Bilinmeyen short_kol: {p['short_kol']}")
        return {"long": gecis(long), "short": gecis(short), "cikis_long": k > bb["orta"], "cikis_short": k < bb["orta"]}


# =============================================================================== 6. Çok TF stokastik aşırı satım
class CokTfStokastikDip(D3Taban):
    """dis__cok-tf-stokastik-dip (scalp, 15m) — kaynak: kripto-bot deposu `stopTrailing` (github_g2_kripto_bot). Orijinal: %K(14)
    1/5/15/60 dk mumlarında hesaplanır; dördünün de %K < 3 olması -> long (yalnız long); stop giriş -%5, +%1.2'de başabaş, zirveden
    %20 izleyen. UYARLAMA (min 15m): zaman dilimleri taban TF (15m) + `tf_listesi` ("1h,4h,1d"); hepsinde hızlı %K(14) < esik.
    Orijinal %K < 3 çok seyrek: esik ızgarada 3-20. Çıkış (VARSAYIM; %5/%20 stop çok geniş): 3 x ATR stop, +1R'de başabaş,
    3 ATR iz süren stop, azami 48 mum (CikisAyarlari)."""
    ad = "dis__cok-tf-stokastik-dip"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0, atr_iz_suren_k=3.0, zaman_cikisi_mum=48)
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "esik": 10.0, "stok_n": 14, "tf_listesi": "1h,4h,1d"}
    parametre_izgarasi = {"esik": [3.0, 5.0, 10.0, 15.0, 20.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        n = int(p["stok_n"])
        tum = _stokf(m, n) < p["esik"]
        for tf in [t.strip() for t in str(p["tf_listesi"]).split(",") if t.strip()]:
            ust = ust_tf(m, tf, lambda u: pd.DataFrame({"k": _stokf(u, n)}))["k"]
            tum = tum & (ust < p["esik"])
        return {"long": gecis(tum)}


# =============================================================================== 7. Dörtlü stokastik rotasyonu
class DortluStokastikRotasyon(D3Taban):
    """dis__dortlu-stokastik-rotasyon (scalp, 15m) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX7.py`
    ("quad rotation" pullback ve diverjans). Dört hızlı stokastik %K: (60), (9), (14), (4).
      Rejim: %K(60) > ust_rejim (80) [yukarı rejim]; üç kısa %K(9, 14, 4) < alt (20).
      kol "kirik":     kapanış 5 mum öncekinden DÜŞÜK ama %K(9) 5 mum öncekinden YÜKSEK (stokastikte kırık);
      kol "diverjans": mum dibi son 12 mumun (önceki) dibinden düşük (yeni dip) ama %K(9) önceki 12 mumun %K(9) minimumundan yüksek;
      kol "ikisi":     ikisinden biri.
    Short ayna (%K(60) < 20; kısa %K'lar > 80; ters kırık/diverjans). Pivot kullanılmaz (pencere min/max, nedensel).
    Çıkış (VARSAYIM): %K(9) karşı uca (long: > cikis_esik 80) ulaşınca; 24 mum; ATR stop. swing__rsi-diverjans'tan farkı: çoklu
    stokastik rejimi."""
    ad = "dis__dortlu-stokastik-rotasyon"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "zaman_cikisi": 24, "kol": "ikisi",
                               "alt": 20.0, "ust_rejim": 80.0, "cikis_esik": 80.0, "geri": 5, "dip_pencere": 12}
    parametre_izgarasi = {"kol": ["kirik", "diverjans", "ikisi"], "alt": [10.0, 20.0, 30.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        s60, s9, s14, s4 = (_stokf(m, n) for n in (60, 9, 14, 4))
        gr, w = int(p["geri"]), int(p["dip_pencere"])
        ust = 100.0 - p["alt"]
        kirik_l = (k < k.shift(gr)) & (s9 > s9.shift(gr))
        kirik_s = (k > k.shift(gr)) & (s9 < s9.shift(gr))
        dv_l = (d < d.shift(1).rolling(w, min_periods=w).min()) & (s9 > s9.shift(1).rolling(w, min_periods=w).min())
        dv_s = (y > y.shift(1).rolling(w, min_periods=w).max()) & (s9 < s9.shift(1).rolling(w, min_periods=w).max())
        if p["kol"] == "kirik":
            tl, ts = kirik_l, kirik_s
        elif p["kol"] == "diverjans":
            tl, ts = dv_l, dv_s
        elif p["kol"] == "ikisi":
            tl, ts = kirik_l | dv_l, kirik_s | dv_s
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        long = (s60 > p["ust_rejim"]) & (s9 < p["alt"]) & (s14 < p["alt"]) & (s4 < p["alt"]) & tl
        short = (s60 < 100.0 - p["ust_rejim"]) & (s9 > ust) & (s14 > ust) & (s4 > ust) & ts
        return {"long": gecis(long), "short": gecis(short), "cikis_long": s9 > p["cikis_esik"],
                "cikis_short": s9 < 100.0 - p["cikis_esik"]}


# =============================================================================== 8. EMA hizalı olgun yükseliş momentumu
class EmaHizaliOlgunYukselis(D3Taban):
    """dis__ema-hizali-olgun-yukselis (scalp, 15m; üst TF 1h) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py`
    ("momentum devamı"). YALNIZ LONG. Kural: EMA9 > EMA26 > EMA200 VE kapanış EMA9/12/26/50/200'ün hepsinin üstünde VE
    (EMA9-EMA50)/kapanış > %0.5 VE RSI(14) [rsi_alt 55, rsi_ust 65] VE 1h RSI [50, 70] VE Aroon-up(14) > aroon_min (75) VE
    Bollinger %B [0.55, 0.85] VE OBV 5 mumluk değişimi > 0 VE Williams %R(14) [-40, -15] VE 1h CMF(21) > 0 VE kapanış 48 mum
    zirvesinin en az zirve_pay (%1.5) altında. ÖRTÜŞME: dis__ema-serit-yelpaze 5 EMA yelpaze açılışı + RSI + hacim; bu aile çok-göstergeli
    "olgun yükseliş" süzgeci. Çıkış (VARSAYIM): kapanış EMA26'nın altına iner ya da 48 mum; ATR stop."""
    ad = "dis__ema-hizali-olgun-yukselis"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 48, "ust_tf": "1h", "rsi_alt": 55.0, "rsi_ust": 65.0,
                               "aroon_min": 75.0, "zirve_pay": 0.015, "fark_min": 0.005}
    parametre_izgarasi = {"rsi_ust": [65.0, 70.0, 75.0], "aroon_min": [60.0, 75.0, 90.0], "zirve_pay": [0.01, 0.015, 0.03]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        e9, e12, e26, e50, e200 = (g.ema(k, n) for n in (9, 12, 26, 50, 200))
        u = ust_tf(m, p["ust_tf"], lambda x: pd.DataFrame({"rsi": g.rsi(x["kapanis"], 14),
                                                          "cmf": cmf(x["yuksek"], x["dusuk"], x["kapanis"], x["hacim"], 21)}))
        bb = g.bollinger(k, 20, 2.0)
        pb = (k - bb["alt"]) / (bb["ust"] - bb["alt"]).where(bb["ust"] != bb["alt"])
        r = g.rsi(k, 14)
        zirve = y.rolling(48, min_periods=48).max()
        wr = williams_r(y, d, k, 14)
        giris = ((e9 > e26) & (e26 > e200) & (k > e9) & (k > e12) & (k > e26) & (k > e50) & (k > e200)
                 & ((e9 - e50) / k > p["fark_min"]) & (r >= p["rsi_alt"]) & (r <= p["rsi_ust"])
                 & (u["rsi"] >= 50.0) & (u["rsi"] <= 70.0) & (aroon_yukari(y, 14) > p["aroon_min"])
                 & (pb >= 0.55) & (pb <= 0.85) & (obv(k, v).diff(5) > 0) & (wr >= -40.0) & (wr <= -15.0)
                 & (u["cmf"] > 0.0) & (k <= zirve * (1.0 - p["zirve_pay"])))
        return {"long": gecis(giris), "cikis_long": k < e26}


# =============================================================================== 9. EWO + EMA ofset aşırı satım
class EwoEmaOfset(D3Taban):
    """dis__ewo-ema-ofset (scalp, 15m) — kaynak: freqtrade BBMod `ewo`/`ewo_2` ve iterativv/NostalgiaForInfinity
    `NostalgiaForInfinityX*.py` (EWO + ofset + RSI/CTI/Williams aşırı satım; r_14/r_480 derin dip). YALNIZ LONG. İki kol:
      "ewo":       kapanış < EMA(8) x ofset VE EWO% < ewo_alt VE RSI(14) < rsi_alt VE RSI(4) < 45 VE CTI(20) < cti_alt (-0.5);
      "derin_dip": Williams %R(14) < wr_alt (-95) VE Williams %R(wr_uzun_n) < -85 VE CTI(20) < -0.8.
    EWO% = (EMA5 - EMA35)/kapanış x 100 (orijinal mutlak fiyat birimli; yüzdeye çevrildi: VARSAYIM, ızgara -1.5..-6).
    ÖRTÜŞME: dis__e0v1en RSI4/RSI14 + SMA ofset + CTI çekirdeğini paylaşır; EWO ve Williams derin dip yeni. KODLANMADI: r_deadfish
    ve gumbo (T3) kolları — özet kesik/T3 tanımı belirsiz. wr_uzun_n: orijinal 480 mum (5m) -> 15m için 160 (VARSAYIM).
    Çıkış: kapanış EMA(16) üstüne çıkar; 32 mum; ATR stop."""
    ad = "dis__ewo-ema-ofset"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 32, "kol": "ewo", "ofset": 0.96, "ewo_alt": -3.0,
                               "rsi_alt": 30.0, "cti_alt": -0.5, "wr_alt": -95.0, "wr_uzun_n": 160}
    parametre_izgarasi = {"ofset": [0.94, 0.96, 0.98], "ewo_alt": [-1.5, -3.0, -6.0], "rsi_alt": [30.0, 38.0, 46.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        if p["kol"] == "ewo":
            giris = ((k < g.ema(k, 8) * p["ofset"]) & (ewo_yuzde(y, d, k, 5, 35) < p["ewo_alt"]) & (g.rsi(k, 14) < p["rsi_alt"])
                     & (g.rsi(k, 4) < 45.0) & (cti(k, 20) < p["cti_alt"]))
        elif p["kol"] == "derin_dip":
            giris = ((williams_r(y, d, k, 14) < p["wr_alt"]) & (williams_r(y, d, k, int(p["wr_uzun_n"])) < -85.0)
                     & (cti(k, 20) < -0.8))
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        return {"long": gecis(giris), "cikis_long": k > g.ema(k, 16)}


# =============================================================================== 10. Getiri / oynaklık katsayısı momentum
class GetiriOynaklikMomentum(D3Taban):
    """dis__getiri-oynaklik-momentum (scalp, 15m) — kaynak: kripto-bot deposu `speed` (github_g2_kripto_bot; `Strat` tik momentumu
    0.01% eşiği gürültü olduğundan KODLANMADI). Orijinal: son 2 dakikalık yüzde değişim, EMA(3000) mutlak değişimin 1.6 katını
    aşarsa al, -1.6 katı altına inerse sat. UYARLAMA (15m): getiri = kapanışın `ret_n` mumluk yüzde değişimi; oynaklık = tek mumluk
    mutlak yüzde değişimin EMA(vol_n) değeri (nedensel); getiri > katsayi x oynaklık -> long, < -katsayi x oynaklık -> short (ilk
    geçiş). Çıkış (VARSAYIM; orijinalde yok): ters yönde eşik aşılırsa; 8 mum; ATR stop."""
    ad = "dis__getiri-oynaklik-momentum"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.5, "zaman_cikisi": 8, "ret_n": 2, "vol_n": 200,
                               "katsayi": 1.6}
    parametre_izgarasi = {"ret_n": [1, 2, 4], "katsayi": [1.6, 2.0, 2.5], "vol_n": [96, 200, 400]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ret = k.pct_change(int(p["ret_n"]))
        vol = k.pct_change().abs().ewm(span=int(p["vol_n"]), adjust=False, min_periods=int(p["vol_n"])).mean()
        yuk, dus = ret > p["katsayi"] * vol, ret < -p["katsayi"] * vol
        return {"long": gecis(yuk), "short": gecis(dus), "cikis_long": dus, "cikis_short": yuk}


# =============================================================================== 11. HA BB40 Cluc dip
class HaBb40Cluc(D3Taban):
    """dis__ha-bb40-cluc (scalp, 15m; üst TF 1h) — kaynak: freqtrade ClucHA / ClucHAnix (github_g1_freqtrade) ve
    iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py` (ClucHA HA BB40 dip). YALNIZ LONG. Heikin-Ashi tipik fiyat
    ((HA yüksek+HA düşük+HA kapanış)/3) üzerinde Bollinger(40, 2). `kol`="bant":
      HA kapanış < ÖNCEKİ alt band VE HA kapanış < önceki HA kapanış VE (orta-alt) > HA kapanış x bb_pay VE |önceki HA kapanış - HA
      kapanış| > HA kapanış x kapanis_fark VE HA kuyruğu (HA kapanış - HA düşük) < (orta-alt) x kuyruk VE 1h HA kapanış / 28 HTF mum
      öncesi > rocr_min VE hacim < ort12(hacim) x hacim_k.
    `kol`="ema50": HA kapanış < EMA50(HA kapanış) VE HA kapanış < alt band x 0.987.
    Çıkış: Fisher RSI(HA kapanış) > fr_cik (0.39) VE üç mum art arda HA kapanış düşüşü. VARSAYIM: eşikler orijinal hyperopt
    aralıklarının ortası, bb_pay 15m'ye göre %0.8-1.9 (orijinal 1.9-4.2: 15m'de bant daha dar); ATR stop, 48 mum. dis__ft-binh-cluc
    normal (HA olmayan) kapanış BB40'tır."""
    ad = "dis__ha-bb40-cluc"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "zaman_cikisi": 48, "kol": "bant", "bb_pay": 0.012,
                               "kapanis_fark": 0.009, "kuyruk": 0.9, "rocr_min": 0.8, "hacim_k": 1.4, "fr_cik": 0.39,
                               "ust_tf": "1h"}
    parametre_izgarasi = {"bb_pay": [0.008, 0.012, 0.019], "kapanis_fark": [0.005, 0.009, 0.02], "kuyruk": [0.72, 0.9, 1.14]}

    def kosullar(self, m):
        p = self.parametreler
        ha = heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"])
        hc = ha["ha_kapanis"]
        tip = (ha["ha_yuksek"] + ha["ha_dusuk"] + hc) / 3.0
        bb = g.bollinger(tip, 40, 2.0)
        gen = bb["orta"] - bb["alt"]
        if p["kol"] == "bant":
            rocr = ust_tf(m, p["ust_tf"], lambda u: pd.DataFrame({"r": (lambda h: h["ha_kapanis"] / h["ha_kapanis"].shift(28))(
                heikin_ashi(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"]))}))["r"]
            ort12 = m["hacim"].rolling(12, min_periods=12).mean()
            giris = ((hc < bb["alt"].shift(1)) & (hc < hc.shift(1)) & (gen > hc * p["bb_pay"])
                     & ((hc.shift(1) - hc).abs() > hc * p["kapanis_fark"]) & ((hc - ha["ha_dusuk"]) < gen * p["kuyruk"])
                     & (rocr > p["rocr_min"]) & (m["hacim"] < ort12 * p["hacim_k"]))
        elif p["kol"] == "ema50":
            giris = (hc < g.ema(hc, 50)) & (hc < bb["alt"] * 0.987)
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        dusus3 = ardisik_say(hc < hc.shift(1)) >= 3
        return {"long": gecis(giris), "cikis_long": (fisher_rsi(hc, 14) > p["fr_cik"]) & dusus3}


# =============================================================================== 12. NFI short trend çöküşü
class NfiShortCokus(D3Taban):
    """dis__nfi-short-cokus (scalp, 15m; üst TF 1h/4h/1d) — kaynak: iterativv/NostalgiaForInfinity `NostalgiaForInfinityX*.py`
    (short: momentum çöküşü #544, trend çöküşü #562, ölü kedi sıçraması #563). YALNIZ SHORT. Kollar (`kol`):
      "rollover": 1h RSI(14) > 55 VE 1h Aroon-up(14) > 60 VE 1h CMF(21) < 0 VE 1h MFI(14) < 50 (yukarı rejim yorgun) VE RSI(3) <
                  rsi3_alt (30) VE EMA12 < EMA26 (roll-over);
      "cokus":    RSI(3) < rsi3_alt VE 1h RSI(3) < 35 VE RSI(14) [15, 32] VE CMF(21) < -0.08 VE OBV 5 mumluk değişimi < 0 VE EMA12 <
                  EMA26 VE kapanış < BB(20,2) alt VE günlük ROC(10 gün) < %5 VE kapanış 30 günlük (günlük) zirvesinin > %12 altında;
      "olu_kedi": 4h EMA12 < 4h EMA200 VE 4h RSI(14) [55, 68] VE 4h kapanış < 4h EMA200 (düşüş trendinde tepki sıçraması).
    Günlük/4h bilgiler kapanmış HTF mumlarından (htf.ust_zaman). Orijinaldeki stopsuz/ekleme kısımları ALINMADI. Çıkış (VARSAYIM):
    3 ATR iz süren stop + 32 mum zaman çıkışı + stop_atr_k x ATR başlangıç stopu (CikisAyarlari)."""
    ad = "dis__nfi-short-cokus"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)
    varsayilan_parametreler = {**ORTAK, "yonler": "short", "stop_atr_k": 3.0, "zaman_cikisi": 32, "kol": "cokus",
                               "rsi3_alt": 30.0}
    parametre_izgarasi = {"kol": ["rollover", "cokus", "olu_kedi"], "rsi3_alt": [20.0, 25.0, 30.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        e12, e26 = g.ema(k, 12), g.ema(k, 26)
        r3 = g.rsi(k, 3)
        if p["kol"] == "rollover":
            u = ust_tf(m, "1h", lambda x: pd.DataFrame({
                "rsi": g.rsi(x["kapanis"], 14), "aroon": aroon_yukari(x["yuksek"], 14),
                "cmf": cmf(x["yuksek"], x["dusuk"], x["kapanis"], x["hacim"], 21),
                "mfi": mfi(x["yuksek"], x["dusuk"], x["kapanis"], x["hacim"], 14)}))
            giris = (u["rsi"] > 55.0) & (u["aroon"] > 60.0) & (u["cmf"] < 0.0) & (u["mfi"] < 50.0) & (r3 < p["rsi3_alt"]) & (e12 < e26)
        elif p["kol"] == "cokus":
            u = ust_tf(m, "1h", lambda x: pd.DataFrame({"rsi3": g.rsi(x["kapanis"], 3)}))
            gun = ust_tf(m, "1d", lambda x: pd.DataFrame({
                "roc": x["kapanis"].pct_change(10),
                "zirve": x["yuksek"].rolling(30, min_periods=30).max()}))
            r14 = g.rsi(k, 14)
            bb = g.bollinger(k, 20, 2.0)
            giris = ((r3 < p["rsi3_alt"]) & (u["rsi3"] < 35.0) & (r14 >= 15.0) & (r14 <= 32.0)
                     & (cmf(y, d, k, v, 21) < -0.08) & (obv(k, v).diff(5) < 0) & (e12 < e26) & (k < bb["alt"])
                     & (gun["roc"] < 0.05) & (k < gun["zirve"] * 0.88))
        elif p["kol"] == "olu_kedi":
            u = ust_tf(m, "4h", lambda x: pd.DataFrame({
                "e12": g.ema(x["kapanis"], 12), "e200": g.ema(x["kapanis"], 200), "rsi": g.rsi(x["kapanis"], 14),
                "k": x["kapanis"]}))
            giris = (u["e12"] < u["e200"]) & (u["rsi"] >= 55.0) & (u["rsi"] <= 68.0) & (u["k"] < u["e200"])
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        return {"short": gecis(giris)}


# =============================================================================== 13. SMC: HTF süpürme -> LTF CHoCH -> OB
class SmcHtfSupurmeChoch(Strateji):
    """dis__smc-htf-supurme-choch (scalp, 15m; HTF 4h) — kaynak: github_g5_mt_pine "SMC Swing: HTF süpürme -> LTF CHoCH -> OB girişi"
    (Pine; kod kopyalanmadı, özet kısmen kesik). SMC öznelliği şu ölçülebilir tanıma çevrildi:
      * HTF süpürme (4h, kapanmış mumlar): HTF mum, ÖNCEKİ htf_n HTF mumun en yüksek/düşüğünü fitille aşıp içeri kapanır
        (yüksek > önceki htf_n zirve VE kapanış < o zirve -> aşağı yönlü süpürme = short yanlılığı; düşük/dip ayna -> long yanlılığı).
      * LTF CHoCH (süpürmeden sonra, en çok bias_mum LTF mum içinde): long yanlılığında kapanış, son ONAYLI LTF pivot tepesini
        (sol=sag=pivot_n; onay pivot_n mum gecikmeli) yukarı kırar; short'ta pivot dibini aşağı kırar. Her süpürme yalnız bir CHoCH'u silahlar.
      * Order block (OB): CHoCH mumundan önceki ob_geri mum içindeki SON karşı renkli mum (long için son düşüş mumu), bölge = [düşük, yüksek].
      * Giriş: CHoCH'tan sonra dokunma_zaman mum içinde fiyat OB bölgesine geri dokunur (long: düşük <= OB yüksek) ve kapanış OB
        dibinin üstünde kalırsa o mumun KAPANIŞINDA giriş; kapanış OB dışına çıkarsa ya da süre dolarsa kurulum iptal.
    Stop = OB dibi - ob_tampon x ATR (short ayna); risk > maks_risk_atr x ATR ise işlem yok. Hedef = rr x R (VARSAYIM; kaynakta yok),
    +1R'de başabaş, azami 96 mum. dis__smc-ob-fvg-sweep tek-TF BOS+sweep+OB'dir; HTF süpürme + LTF CHoCH akışı farklıdır."""
    ad = "dis__smc-htf-supurme-choch"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0, zaman_cikisi_mum=96)
    varsayilan_parametreler = {"yonler": "ls", "ust_tf": "4h", "htf_n": 6, "pivot_n": 3, "bias_mum": 48, "ob_geri": 15,
                               "dokunma_zaman": 20, "ob_tampon": 0.1, "maks_risk_atr": 6.0, "rr": 2.0, "atr_periyot": 14}
    parametre_izgarasi = {"htf_n": [4, 6, 10], "pivot_n": [2, 3, 5], "rr": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit R hedefi + zaman çıkışı

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        a, y, d, k = (m[c].to_numpy(dtype=float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        n = len(k)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"])).to_numpy()
        hn = int(p["htf_n"])

        def htf(u):
            oy = u["yuksek"].shift(1).rolling(hn, min_periods=hn).max()
            od = u["dusuk"].shift(1).rolling(hn, min_periods=hn).min()
            return pd.DataFrame({"boga": ((u["dusuk"] < od) & (u["kapanis"] > od)).astype(float).where(od.notna()),
                                 "ayi": ((u["yuksek"] > oy) & (u["kapanis"] < oy)).astype(float).where(oy.notna())})
        h = ust_tf(m, p["ust_tf"], htf)
        boga, ayi = h["boga"].fillna(0.0).to_numpy(), h["ayi"].fillna(0.0).to_numpy()
        pn = int(p["pivot_n"])
        ph = pivot_seviye(m["yuksek"], pn, pn, True)
        pl = pivot_seviye(m["dusuk"], pn, pn, False)
        ck_l = yukari_kesis(m["kapanis"], ph).to_numpy(dtype=bool)
        ck_s = asagi_kesis(m["kapanis"], pl).to_numpy(dtype=bool)
        bias, ob_geri, dok = int(p["bias_mum"]), int(p["ob_geri"]), int(p["dokunma_zaman"])
        tamp, maks = p["ob_tampon"], p["maks_risk_atr"]
        long_ok, short_ok = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
        stop_l, stop_s = np.full(n, np.nan), np.full(n, np.nan)
        arm_l = arm_s = -10 ** 9
        pend_l = pend_s = None
        for i in range(1, n):
            if boga[i] == 1.0 and boga[i - 1] != 1.0:
                arm_l = i
            if ayi[i] == 1.0 and ayi[i - 1] != 1.0:
                arm_s = i
            if pend_l is not None:
                alt, ust, bit = pend_l
                if k[i] < alt or i > bit:
                    pend_l = None
                elif d[i] <= ust and not np.isnan(atr[i]):
                    st = alt - tamp * atr[i]
                    if 0 < k[i] - st <= maks * atr[i]:
                        long_ok[i], stop_l[i] = True, st
                    pend_l = None
            if pend_s is not None:
                alt, ust, bit = pend_s
                if k[i] > ust or i > bit:
                    pend_s = None
                elif y[i] >= alt and not np.isnan(atr[i]):
                    st = ust + tamp * atr[i]
                    if 0 < st - k[i] <= maks * atr[i]:
                        short_ok[i], stop_s[i] = True, st
                    pend_s = None
            if pend_l is None and ck_l[i] and i - arm_l <= bias:
                for j in range(i - 1, max(i - ob_geri, 0) - 1, -1):
                    if k[j] < a[j]:
                        pend_l, arm_l = (d[j], y[j], i + dok), -10 ** 9
                        break
            if pend_s is None and ck_s[i] and i - arm_s <= bias:
                for j in range(i - 1, max(i - ob_geri, 0) - 1, -1):
                    if k[j] > a[j]:
                        pend_s, arm_s = (d[j], y[j], i + dok), -10 ** 9
                        break
        if p["yonler"] == "long":
            short_ok[:] = False
        elif p["yonler"] == "short":
            long_ok[:] = False
        kap = m["kapanis"]
        sl, ss = pd.Series(stop_l, index=idx), pd.Series(stop_s, index=idx)
        hl, hs = kap + p["rr"] * (kap - sl), kap - p["rr"] * (ss - kap)
        return cerceve(m, pd.Series(long_ok, index=idx), pd.Series(short_ok, index=idx), sl, ss, hl, hs, None, False, 0.0)


# =============================================================================== 14. VWAP alt bant dip
class VwapAltBantDip(D3Taban):
    """dis__vwap-alt-bant-dip (scalp, 15m) — kaynak: freqtrade BBMod `vwap dip` (github_g1_freqtrade) ve iterativv/
    NostalgiaForInfinity `NostalgiaForInfinityX*.py` (VWAP alt bandı "rapid mode"). YALNIZ LONG. Kural: yuvarlanan VWAP(20) (hacim
    ağırlıklı, seanssız) alt bandı (1 hacim ağırlıklı sapma) altında kapanış VE kapanış son `pencere` mum zirvesinden dusus_min..dusus_maks
    (%4..22.5) aşağıda VE CTI(20) < cti_esik VE `kol`="rsi14": RSI(14) < 35 / `kol`="rsi_uzun": RSI(rsi_uzun_n=84) < 60.
    pencere: orijinal 48/288 (5m) -> 15m için 96 (VARSAYIM). KODLANMADI: KAMA/FAMA/MAMA (MESA) ofset koşulları (MESA uygulaması
    yok) ve BTC 24sa tepesi süzgeci (çapraz-sembol). dis__vp-deger-alani hacim profilidir (farklı). Çıkış: kapanış VWAP'ın üstüne
    çıkar; 32 mum; ATR stop."""
    ad = "dis__vwap-alt-bant-dip"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 32, "kol": "rsi14", "vwap_n": 20, "pencere": 96,
                               "dusus_min": 0.04, "dusus_maks": 0.225, "cti_esik": -0.5, "rsi_alt": 35.0,
                               "rsi_uzun_n": 84, "rsi_uzun_ust": 60.0}
    parametre_izgarasi = {"dusus_min": [0.02, 0.04, 0.06], "cti_esik": [-0.3, -0.5, -0.8], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        vb = vwap_bant(y, d, k, v, int(p["vwap_n"]), 1.0)
        pen = int(p["pencere"])
        zirve = y.rolling(pen, min_periods=pen).max()
        dusus = 1.0 - k / zirve
        if p["kol"] == "rsi14":
            rsi_ok = g.rsi(k, 14) < p["rsi_alt"]
        elif p["kol"] == "rsi_uzun":
            rsi_ok = g.rsi(k, int(p["rsi_uzun_n"])) < p["rsi_uzun_ust"]
        else:
            raise ValueError(f"Bilinmeyen kol: {p['kol']}")
        giris = (k < vb["alt"]) & (dusus >= p["dusus_min"]) & (dusus <= p["dusus_maks"]) & (cti(k, 20) < p["cti_esik"]) & rsi_ok
        return {"long": gecis(giris), "cikis_long": k > vb["orta"]}
