"""D3 freqtrade stratejileri, 30m-4h: Heracles, MultiMa (swing 4h); HourBased, TDSequential, VolatilitySystem, wtc (daytrade).

Ortak uyarlama (freqtrade -> 1L3A):
  * `stoploss` -> stop_yuzde (orijinal değer varsayılan); orijinalde stop yoksa (VolatilitySystem) ATR stop eklendi.
  * `minimal_roi` kademeli tablosu motorda yok: bir kademenin yüzdesi `hedef_yuzde`, son kademenin süresi
    `zaman_cikisi` (mum sayısı = dakika / orijinal TF) olarak sabit hedef + zaman çıkışına çevrildi.
  * Orijinal yalnız long ise short ayna kuralıyla `yonler="short"/"ls"` ile açılır; varsayılan orijinal gibi "long".
  * Daytrade (30m-1h) stratejileri UTC gün sonunda zorunlu kapanır.
Arşiv: arsiv/algo-sg/dis_kaynak/ft/strategies/*.py (veri sayılır, çalıştırılmadı).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d3 import (
    ORTAK, D3Taban, dalga_trend, donchian_pband, genisleyen_minmax, keltner_wband, td_sayim, tema)
from motor.strateji.gostergeler_b2 import asagi_kesis, gecis, yukari_kesis
from motor.strateji.htf import ust_zaman


class Heracles(D3Taban):
    """dis__heracles — Donchian %B / Keltner genişliği oranı bandı (hyperopt kuralı), 4h.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/Heracles.py.
    Kural (long): Donchian(10) %B'nin `ind_geri` mum öncesi değeri / Keltner(20, orijinal sürüm) genişliğinin `kes_geri`
    mum öncesi değeri, [oran_min, oran_max] aralığında. Orijinalde çıkış sinyali yok (roi 0.598/0.166/0.115/0).
    Uyarlama: kademeli ROI -> hedef %16.6 + 30 mum (7289 dk / 4h) zaman çıkışı; stop %25.6 (orijinal). Short ayna:
    (1 - %B) ile aynı oran bandı.
    Eski sonuç: hata (freqtrade farklı uzunlukta dataframe döndürdü) — hiç ölçülemedi."""
    ad = "dis__heracles"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.256, "hedef_yuzde": 0.166, "zaman_cikisi": 30,
                               "ind_geri": 15, "kes_geri": 9, "oran_min": 0.16, "oran_max": 0.75}
    parametre_izgarasi = {"ind_geri": [9, 15, 20], "kes_geri": [5, 9, 14], "oran_max": [0.5, 0.75, 1.0]}

    def kosullar(self, m):
        p = self.parametreler
        pb = donchian_pband(m["yuksek"], m["dusuk"], m["kapanis"], 10)
        kw = keltner_wband(m["yuksek"], m["dusuk"], m["kapanis"], 20).shift(int(p["kes_geri"]))
        d_l = pb.shift(int(p["ind_geri"])) / kw
        d_s = (1.0 - pb).shift(int(p["ind_geri"])) / kw
        return {"long": d_l.between(p["oran_min"], p["oran_max"]), "short": d_s.between(p["oran_min"], p["oran_max"])}


class MultiMa(D3Taban):
    """dis__multi-ma — TEMA yığını: kısa-uzun sıralama ile giriş, ters sıralamada (VEYA) çıkış, 4h.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/MultiMa.py.
    Kural (long): k=1..buy_ma_count-1 için TEMA(k*gap) < TEMA((k-1)*gap) (periyot > 1 olanlar): TEMA'lar kısa>uzun
    sıralı (yükselen yığın). Çıkış: sell_ma_count/sell_ma_gap ile TEMA(k*gap) > TEMA((k-1)*gap) koşullarından HERHANGİ biri.
    Uyarlama: kademeli ROI -> hedef %12.3 + 14 mum (3169 dk / 4h); stop %34.5 (orijinal). Short ayna (yön tersi).
    Eski sonuç: PF IS 1.39 / OOS 1.04; Sh IS 1.63 / OOS 0.18; stres PF 1.16 -> kaldı."""
    ad = "dis__multi-ma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.345, "hedef_yuzde": 0.123, "zaman_cikisi": 14,
                               "buy_ma_count": 4, "buy_ma_gap": 15, "sell_ma_count": 12, "sell_ma_gap": 68}
    parametre_izgarasi = {"buy_ma_count": [3, 4, 5], "buy_ma_gap": [10, 15, 20], "sell_ma_gap": [50, 68, 90]}

    @staticmethod
    def _cift_kosullar(kap, adet, aralik, kucuk_mu):
        """k*aralik ve (k-1)*aralik periyotlu TEMA çiftleri; (önceki periyot > 1) ve çift sayısı."""
        liste = []
        for k in range(int(adet)):
            anahtar, onceki = k * int(aralik), (k - 1) * int(aralik)
            if onceki > 1 and anahtar > 1:
                a, b = tema(kap, anahtar), tema(kap, onceki)
                liste.append(a < b if kucuk_mu else a > b)
        return liste

    def kosullar(self, m):
        p, kap = self.parametreler, m["kapanis"]
        bos = pd.Series(False, index=m.index)
        al_l = self._cift_kosullar(kap, p["buy_ma_count"], p["buy_ma_gap"], True)     # uzun < kısa
        al_s = self._cift_kosullar(kap, p["buy_ma_count"], p["buy_ma_gap"], False)
        sat_l = self._cift_kosullar(kap, p["sell_ma_count"], p["sell_ma_gap"], False)  # uzun > kısa
        sat_s = self._cift_kosullar(kap, p["sell_ma_count"], p["sell_ma_gap"], True)

        def ve(liste):
            s = bos | True
            for x in liste:
                s = s & x
            return s if liste else bos

        def veya(liste):
            s = bos
            for x in liste:
                s = s | x
            return s
        return {"long": ve(al_l), "short": ve(al_s), "cikis_long": veya(sat_l), "cikis_short": veya(sat_s)}


class HourBased(D3Taban):
    """dis__hour-based — saat aralığında al, başka saat aralığında sat (zaman tabanlı), 1h daytrade.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/HourBasedStrategy.py.
    Kural (long): mumun UTC saati [giris_saat_min, giris_saat_max] içinde (orijinal 4..24 = 04:00'dan gün sonuna);
    çıkış: saat [cikis_saat_min, cikis_saat_max] (orijinal 22..21 = BOŞ aralık, hiç tetiklenmez).
    Uyarlama: stop %10 (orijinal); ROI -> hedef %11.3 + 31 mum zaman çıkışı; UTC gün sonu zorunlu çıkış (gün sonu
    zaten sondur). Short ayna: çıkış penceresinde short, giriş penceresinde short kapanır.
    Eski sonuç: sonuç yok (sonuc_freqtrade.csv)."""
    ad = "dis__hour-based"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.10, "hedef_yuzde": 0.113, "zaman_cikisi": 31,
                               "giris_saat_min": 4, "giris_saat_max": 24, "cikis_saat_min": 22, "cikis_saat_max": 21}
    parametre_izgarasi = {"giris_saat_min": [0, 4, 8], "cikis_saat_min": [12, 16, 22], "stop_yuzde": [0.02, 0.05, 0.10]}

    def kosullar(self, m):
        p = self.parametreler
        h = pd.Series(m.index.hour, index=m.index)
        gir = h.between(p["giris_saat_min"], p["giris_saat_max"])
        cik = h.between(p["cikis_saat_min"], p["cikis_saat_max"])
        return {"long": gir, "short": cik, "cikis_long": cik, "cikis_short": gir}


class TdSequential(D3Taban):
    """dis__td-sequential — TD Sequential kurulum sayımı tamamlanınca ters yönde giriş, 1h daytrade.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/TDSequentialStrategy.py.
    Kural (long): ardışık `sayim` kapanış < kapanış[geri önce] (alış kurulumu) sayısı > n-1 VE sayımın 6./7. mumunun
    düşüğü aşıldı. Çıkış: satış kurulumu (ardışık kapanış > kapanış[geri önce]) > n-1 sayıldı veya yüksek aşması.
    Orijinal döngü index-1/2/3 ile geriye bakar (nedensel); burada aynı mantık numpy ile. Short ayna.
    Uyarlama: stop %5 (orijinal; roi {0:5} hiç tetiklenmez); UTC gün sonu zorunlu çıkış.
    Eski sonuç: sonuç yok (sonuc_freqtrade.csv)."""
    ad = "dis__td-sequential"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.05, "n": 9, "geri": 4}
    parametre_izgarasi = {"n": [8, 9, 10], "geri": [3, 4, 5], "stop_yuzde": [0.03, 0.05, 0.08]}

    def kosullar(self, m):
        p = self.parametreler
        t = td_sayim(m["yuksek"], m["dusuk"], m["kapanis"], int(p["geri"]), int(p["n"]))
        ix = m.index
        alis = pd.Series(t["alis"] > p["n"] - 1, index=ix)
        satis = pd.Series(t["satis"] > p["n"] - 1, index=ix)
        asma_alt = pd.Series(t["asma_alt"], index=ix)
        asma_ust = pd.Series(t["asma_ust"], index=ix)
        return {"long": asma_alt & alis, "short": asma_ust & satis,
                "cikis_long": asma_ust | satis, "cikis_short": asma_alt | alis}


class VolatilitySystem(D3Taban):
    """dis__volatility-system — kapanış değişimi ATR'yi aşarsa yönde giriş, ters sinyalde çıkış, 1h daytrade.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/VolatilitySystem.py (TradingView "Volatility System" uyarlaması).
    Kural: 3 saatlik mumda kapanış farkı > carpan x ATR(14) (bir ÖNCEKİ 3h mumun ATR'si) -> long; farkın eksisi > ... -> short.
    Ters sinyal mevcut pozisyonu kapatır. 3h seri htf.ust_zaman ile (yalnız kapanmış 3h mumları; lookahead yok).
    Uyarlama: orijinalde stop yok (stoploss -1) -> ATR(1h,14) x stop_atr_k stop eklendi. İkinci kat ekleme (adjust_trade_
    position) ve 2x kaldıraç ATLANDI (piramitleme yasak; kaldıraç risk modülünde). UTC gün sonu zorunlu çıkış.
    Eski sonuç: PF IS 1.26 / OOS 0.66; Sh IS 1.32 / OOS -0.36; stres PF 0.93 -> kaldı."""
    ad = "dis__volatility-system"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "carpan": 2.0, "ust_tf": "3h"}
    parametre_izgarasi = {"carpan": [1.5, 2.0, 3.0], "stop_atr_k": [2.0, 3.0, 4.0], "ust_tf": ["2h", "3h", "4h"]}

    def kosullar(self, m):
        p = self.parametreler

        def fonk(u):
            esik = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], 14) * p["carpan"]
            return pd.DataFrame({"esik": esik.shift(1), "fark": u["kapanis"].diff()})
        h = ust_zaman(m, p["ust_tf"], fonk)
        yukari = (h["fark"] > h["esik"]).fillna(False)
        asagi = (-h["fark"] > h["esik"]).fillna(False)
        l_g, s_g = gecis(yukari), gecis(asagi)
        return {"long": l_g, "short": s_g, "cikis_long": s_g, "cikis_short": l_g}


class Wtc(D3Taban):
    """dis__wtc-wavetrend — WaveTrend kesişimi + stokastik/fark bant süzgeçleri, 30m daytrade.
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/wtc.py (hyperopt parametreleri).
    Kural (long): wt1, wt2'yi yukarı keser; ölçeklenmiş wt1 [buy_min0,buy_max0], slowK [buy_min1,buy_max1] ve
    (slowK - wt1) [buy_min,buy_max] içinde. Çıkış: aşağı kesişim + sell_* bantları (orijinalde sell_min>sell_max
    olduğundan fark bandı BOŞ: çıkış tetiklenmez; hedef/zaman/gün sonu çıkar).
    NEDENSELLEŞTİRME: orijinal sklearn MinMaxScaler wt1/wt2/slowK sütunlarını TÜM veriye göre ölçekler (gelecek
    sızıntısı). Burada her sütun genişleyen (o ana kadarki) min-max ile ölçeklenir; ilk `isinma` mum sinyalsiz.
    Short ayna: kesişim aşağı, bantlar 1-x (fark için -x) aynalanır.
    Uyarlama: stop %12.8 (orijinal); ROI -> hedef %16.7 + 254 mum; UTC gün sonu zorunlu çıkış.
    Eski sonuç: PF IS 0.78 / OOS 0.94; Sh IS -1.06 / OOS -0.29 -> kaldı."""
    ad = "dis__wtc-wavetrend"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "stop_yuzde": 0.128, "hedef_yuzde": 0.167, "zaman_cikisi": 254,
                               "isinma": 300,
                               "buy_min0": 0.0102, "buy_max0": 0.8633, "buy_min1": 0.6864, "buy_max1": 0.9133,
                               "buy_min": 0.0019, "buy_max": 0.9609,
                               "sell_min0": 0.0628, "sell_max0": 0.82, "sell_min1": 0.4461, "sell_max1": 0.9821,
                               "sell_min": -0.5377, "sell_max": -0.7979}
    parametre_izgarasi = {"buy_min1": [0.5, 0.6864, 0.8], "buy_max0": [0.7, 0.8633, 1.0], "stop_yuzde": [0.05, 0.128, 0.2]}

    def kosullar(self, m):
        p = self.parametreler
        wt = dalga_trend(m["yuksek"], m["dusuk"], m["kapanis"])
        sk = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], 14, 3)["d"]   # ta-lib STOCH slowK = SMA3(fastK14)
        w1 = genisleyen_minmax(wt["wt1"], p["isinma"])
        w2 = genisleyen_minmax(wt["wt2"], p["isinma"])
        k = genisleyen_minmax(sk, p["isinma"])
        fark = k - w1
        yu, ya = yukari_kesis(w1, w2), asagi_kesis(w1, w2)

        def bant(s, lo, hi):
            return s.between(lo, hi)
        long_ = yu & bant(w1, p["buy_min0"], p["buy_max0"]) & bant(k, p["buy_min1"], p["buy_max1"]) & bant(fark, p["buy_min"], p["buy_max"])
        cik_l = ya & bant(w1, p["sell_min0"], p["sell_max0"]) & bant(k, p["sell_min1"], p["sell_max1"]) & bant(fark, p["sell_min"], p["sell_max"])
        short_ = (ya & bant(1 - w1, p["buy_min0"], p["buy_max0"]) & bant(1 - k, p["buy_min1"], p["buy_max1"])
                  & bant(-fark, p["buy_min"], p["buy_max"]))
        cik_s = (yu & bant(1 - w1, p["sell_min0"], p["sell_max0"]) & bant(1 - k, p["sell_min1"], p["sell_max1"])
                 & bant(-fark, p["sell_min"], p["sell_max"]))
        return {"long": long_, "short": short_, "cikis_long": cik_l, "cikis_short": cik_s}
