"""Kapanış turu kodlama partisi g8_kod_5 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_5.csv, 40 kaynak satırı).

Hepsi HAM:X005:* (trend / ortalamaya dönüş listesi). Her kaynak satır için bir sınıf vardır (36 sınıf); kurallar `kural_tam`
metninden kendi kodumuzla yazıldı, üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan (motor sonraki açılışta doldurur);
gelecek verisi yok. Kaynak stopu yoksa ATR(14)x3 uyarlaması. Yönlü çıkış `cikis_long` / `cikis_short` sütunlarıyla verilir.

Genel biçim kararları (ILERLEME.md politikaları, g8_kod_4 ile aynı):
- Durum koşullu girişler ("RSI<30 iken al") her mumda yon != 0 üretir; motor pozisyon açıkken yeni girişi atlar.
- Kesişim: "x, y'yi yukarı keser" = x[t-1] <= y[t-1] ve x[t] > y[t]; seviye kesişimi: x[t-1] < seviye <= x[t] (yukarı),
  x[t-1] >= seviye > x[t] (aşağı).
- Freqtrade ROI / iz süren stop: motorun `azalan_roi` ve `geri_cekilme_yuzde` modülleriyle (kapanış bazlı kâr, sonraki açılışta
  çıkış). ROI tablosu dakika cinsindense mum çözünürlüğüne çevrilir (ara basamaklar mum sınırına denk gelmiyorsa düşer).
- Kaynak çıkışı KAPANIŞ bazlıysa ve giriş fiyatına / giriş sonrası tepeye bağlıysa (pozisyon durumu) strateji kancasıyla
  (`pozisyon_cikisi`, kod_g8_modul) yazılır; 436, 446, 447 oraya taşındı. 554/556 yüzde iz süren stop de kancadadır
  (zirve fiyatının %'si, zirve = giriş sonrası en yüksek HIGH; kapanışta kontrol, çıkış sonraki açılışta).
- Haftalık satır (438) 1d mumlarla koşulur (VARYANTLAR tf = "1d"): haftalık değerler `htf.ust_zaman("1w")` ile yalnız kapanmış
  haftadan, karar yeni haftanın ilk günü. 8h mumlar koşu tarafında 1h-4h verisinden yeniden örneklenir.

KODLANAMADI (bkz. `KODLANAMADI`): 553 (başka sembole (BTC) bağlı filtre; üst TF bilgi verisi + güven skoru süzgeci).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji._gosterge_d11j import ultimate_osc
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d1 import ao_ac
from motor.strateji.dis._gosterge_d2 import var_ma
from motor.strateji.dis._gosterge_d5 import kama, ott
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.gostergeler_b2 import cci, ichimoku
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, hafta_degerleri, tepe_geri_cekilme
from motor.strateji.temel import Strateji


# ---------------------------------------------------------------- yardımcılar
def _yukari(x: pd.Series, y) -> pd.Series:
    """x, y'yi (seri ya da sabit) yukarı keser."""
    y = y if isinstance(y, pd.Series) else pd.Series(float(y), index=x.index)
    return ((x.shift(1) <= y.shift(1)) & (x > y)).fillna(False)


def _asagi(x: pd.Series, y) -> pd.Series:
    y = y if isinstance(y, pd.Series) else pd.Series(float(y), index=x.index)
    return ((x.shift(1) >= y.shift(1)) & (x < y)).fillna(False)


def _seviye_yukari(x: pd.Series, s: float) -> pd.Series:
    return ((x.shift(1) < s) & (x >= s)).fillna(False)


def _seviye_asagi(x: pd.Series, s: float) -> pd.Series:
    return ((x.shift(1) >= s) & (x < s)).fillna(False)


def _atr_riski(m: pd.DataFrame, p: dict) -> pd.Series:
    return float(p["atr_k"]) * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))


def _ekle(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


class _Taban(Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


_ATR = {"atr_n": 14, "atr_k": 3.0}


# ---------------------------------------------------------------- sınıflar
class CciEsikSifir(_Taban):
    """X005:428 (1d, iki yön): CCI(20) -E seviyesinin altına İNİNCE (kesişim) long, +E üstüne ÇIKINCA short; CCI sıfır çizgisini
    kesince kapat (long: yukarı kesiş, short: aşağı kesiş). E=100 ve E=200 iki varyant. Stop kaynakta yok -> ATR(14)x3 (uyarlama).
    Not: kaynak girişi 'eşik altına girişte' olarak anlatıyor; kesişim (inince) olarak okundu."""
    ad = "kapanis__cci-esik-s0428"
    varsayilan_parametreler = {"cci_n": 20, "esik": 100, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        c = cci(mumlar["yuksek"], mumlar["dusuk"], k, int(p["cci_n"]))
        e = float(p["esik"])
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _seviye_asagi(c, -e), _seviye_yukari(c, e), k - r, k + r),
                     cikis_long=_yukari(c, 0.0), cikis_short=_asagi(c, 0.0))


class BbAltArdisikYukselis(_Taban):
    """X005:430 (K6, 1d, long): BB(20, 2σ): en az 2 ardışık gün kapanış alt bandın altında kaldıktan sonra, kapanış önceki
    kapanıştan yüksek ama hâlâ alt bandın altındaysa long; çıkış: kapanış üst bandı yukarı keserse. Stop yok -> ATR(14)x3."""
    ad = "kapanis__bb-alt-ardisik-s0430"
    varsayilan_parametreler = {"bb_n": 20, "bb_std": 2.0, "min_bant_alti_gun": 2, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_std"]))
        alti = (k < bb["alt"]).fillna(False)
        n = int(p["min_bant_alti_gun"])
        onceki = alti.astype(int).rolling(n, min_periods=n).sum().shift(1) == n
        gir = alti & (k > k.shift(1)) & onceki.fillna(False)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - r, k + r), cikis_long=_yukari(k, bb["ust"]))


class Rsi5mYuzdeStopHedef(_Taban):
    """X005:432 (5m, iki yön): RSI(14)<30 iken long, >70 iken short (durum); RSI 30-70 aralığına dönünce kapat (long: RSI>=30,
    short: RSI<=70). Stop giriş (sinyal kapanışı) fiyatının %1,5'i, hedef %2 (kaynak stopu; ATR uyarlaması yok)."""
    ad = "kapanis__rsi-yuzde-sl-tp-s0432"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30, "ust": 70, "sl_yuzde": 1.5, "tp_yuzde": 2.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        sl, tp = float(p["sl_yuzde"]) / 100.0, float(p["tp_yuzde"]) / 100.0
        return _ekle(cerceve(mumlar, r < float(p["alt"]), r > float(p["ust"]), k * (1 - sl), k * (1 + sl),
                             hedef_l=k * (1 + tp), hedef_s=k * (1 - tp)),
                     cikis_long=r >= float(p["alt"]), cikis_short=r <= float(p["ust"]))


class MacdRsiAtrHedef(_Taban):
    """X005:435 (1d, iki yön): MACD(10,15,5) histogramı>0 ve 50<RSI(10)<100-x (x=30) -> long; histogram<0 ve x<RSI<50 -> short.
    Long çıkış: RSI>=100-x ya da histogram<0 ya da hedef giriş+2xATR(7); short simetrik. Stop giriş-/+2xATR(7) (sinyal kapanışından).
    Kaynak varsayılan (optimize edilmemiş) parametre kümesi."""
    ad = "kapanis__macd-rsi-atr7-s0435"
    varsayilan_parametreler = {"macd_h": 10, "macd_y": 15, "macd_s": 5, "rsi_n": 10, "x": 30, "atr_n": 7, "carpan": 2.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        hist = g.macd(k, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))["histogram"]
        r = g.rsi(k, int(p["rsi_n"]))
        x = float(p["x"])
        risk = float(p["carpan"]) * g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_n"]))
        lg = (hist > 0) & (r > 50) & (r < 100 - x)
        st = (hist < 0) & (r > x) & (r < 50)
        return _ekle(cerceve(mumlar, lg, st, k - risk, k + risk, hedef_l=k + risk, hedef_s=k - risk),
                     cikis_long=(r >= 100 - x) | (hist < 0), cikis_short=(r <= x) | (hist > 0))


class HaftalikSmaMacd(_Taban):
    """X005:438 (K6, haftalık, 1d mumlarla, long): haftalık kapanış 20 haftalık SMA'nın üstünde VE haftalık MACD(12,26,9) çizgisi sinyalin
    üstündeyse long (durum); haftalık kapanış SMA20 altına inince çık. Ayı piyasası %20 kapısı uygulanmadı (kaynakta yalnız tanım).
    Haftalık değerler `htf.ust_zaman('1w')` ile kapanmış haftadan, karar yeni haftanın ilk günü. Stop yok -> ATR(14)x3 (günlük)."""
    ad = "kapanis__haftalik-sma-macd-s0438"
    varsayilan_parametreler = {"sma_n": 20, "macd_h": 12, "macd_y": 26, "macd_s": 9, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler

        def fonk(u):
            k = u["kapanis"]
            m = g.macd(k, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))
            return pd.DataFrame({"kw": k, "sma": g.sma(k, int(p["sma_n"])), "macd": m["macd"], "sinyal": m["sinyal"]})

        w, yeni = hafta_degerleri(mumlar, fonk)
        k = mumlar["kapanis"]
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, yeni & (w["kw"] > w["sma"]) & (w["macd"] > w["sinyal"]), False, k - r, k + r),
                     cikis_long=yeni & (w["kw"] < w["sma"]))


class RejimRsiBantAlt(_Taban):
    """X005:448 (1d, long): kapanış > SMA(216) VE RSI(18) < 31 VE kapanış alt Bollinger(37, 2,0) altında -> long (durum);
    çıkış RSI(18) > 69 ya da kapanış orta bandın (SMA37) üstüne çıkınca. Stop giriş-2,4xATR(18) (sinyal kapanışından); iz süren yok."""
    ad = "kapanis__rejim-rsi-bant-s0448"
    varsayilan_parametreler = {"rejim_sma": 216, "rsi_n": 18, "rsi_giris": 31, "rsi_cikis": 69, "bb_n": 37, "bb_k": 2.0,
                               "atr_n": 18, "atr_stop": 2.4}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        risk = float(p["atr_stop"]) * g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_n"]))
        gir = (k > g.sma(k, int(p["rejim_sma"]))) & (r < float(p["rsi_giris"])) & (k < bb["alt"])
        return _ekle(cerceve(mumlar, gir, False, k - risk, k + risk),
                     cikis_long=(r > float(p["rsi_cikis"])) | (k > bb["orta"]))


class UltimateOsilator(_Taban):
    """X005:449 (1h, long): pozisyon yokken Ultimate Oscillator(7,14,28) < 30 -> long (durum); pozisyondayken UO > 70 -> kapat.
    Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ultimate-osc-s0449"
    varsayilan_parametreler = {"uo_a": 7, "uo_b": 14, "uo_c": 28, "alt": 30, "ust": 70, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        uo = ultimate_osc(mumlar["yuksek"], mumlar["dusuk"], k, int(p["uo_a"]), int(p["uo_b"]), int(p["uo_c"]))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, uo < float(p["alt"]), False, k - r, k + r), cikis_long=uo > float(p["ust"]))


def _destek_kumesi(dusuk: np.ndarray, kapanis: np.ndarray, onceki_n: int, dokunma: int, tolerans: float) -> np.ndarray:
    """Her t için: önceki `onceki_n` barın (t hariç) dipleri arasında kapanışın ALTINDAKİ en yakın destek.
    Destek = bir dip değerinin %tolerans'ı içinde en az `dokunma` dip (kendisi dahil) bulunan kümenin ortalaması; küme yoksa
    onceki_n barın en düşüğü. Pencere eksikse NaN. Yalnız t-1 ve öncesi dipler + t kapanışı kullanılır (nedensel)."""
    n = len(dusuk)
    sonuc = np.full(n, np.nan)
    ek = np.r_[np.full(onceki_n, np.nan), dusuk]
    pencere = sliding_window_view(ek, onceki_n)[:n]
    for bas in range(0, n, 20000):
        w = pencere[bas:bas + 20000]
        c = kapanis[bas:bas + 20000][:, None]
        eksik = np.isnan(w).any(axis=1)
        wz = np.where(np.isnan(w), 0.0, w)
        yakin = np.abs(wz[:, :, None] - wz[:, None, :]) <= tolerans * wz[:, :, None]
        adet = yakin.sum(axis=2)
        ort = (yakin * wz[:, None, :]).sum(axis=2) / np.maximum(adet, 1)
        gecerli = (wz < c) & (adet >= dokunma) & (ort < c)
        aday = np.where(gecerli, ort, -np.inf).max(axis=1)
        en_dusuk = wz.min(axis=1)
        s = np.where(np.isfinite(aday), aday, en_dusuk)
        s[eksik] = np.nan
        sonuc[bas:bas + 20000] = s
    return sonuc


class SmaRsiDestekStop(_Taban):
    """X005:450 (1h, long): pozisyon yokken kapanış > SMA(500) VE RSI(9) >= 50 -> long. Stop = kapanışın altındaki en yakın destek:
    önceki 19 barın dipleri arasında %0,3 içinde >= 2 dip (kendisi dahil) bulunan kümenin ortalaması; küme yoksa 19 barın en düşüğü.
    TP1 = giriş+1R'de pozisyonun yarısı kapanır ve stop girişe çekilir (CikisAyarlari.kismi + basabas_r_esigi); TP2 = giriş+2R
    (hedef_r) kalan kapanır. 'Önceki 19 bar' = t-1..t-19 (sinyal mumu hariç). Stop dibe değince çıkış (motor stopu)."""
    ad = "kapanis__sma500-rsi9-destek-s0450"
    varsayilan_parametreler = {"sma": 500, "rsi": 9, "rsi_esik": 50, "onceki_bar": 19, "dokunma": 2, "tolerans": 0.003,
                               "hedef_r": 2.0}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=1.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        destek = pd.Series(_destek_kumesi(mumlar["dusuk"].to_numpy(float), k.to_numpy(float), int(p["onceki_bar"]),
                                          int(p["dokunma"]), float(p["tolerans"])), index=mumlar.index)
        gir = (k > g.sma(k, int(p["sma"]))) & (g.rsi(k, int(p["rsi"])) >= float(p["rsi_esik"]))
        return cerceve(mumlar, gir, False, destek, k, hedef_l=k + float(p["hedef_r"]) * (k - destek))


class SmaKesisimRsiGecmis(_Taban):
    """X005:454 (1d, iki yön): long: SMA9 SMA21'i yukarı keser VE son 5 barda (sinyal mumu dahil) RSI14 <= 30 olmuş; short:
    SMA9 SMA21'i aşağı keser VE son 5 barda RSI14 >= 70 olmuş; çıkış ters kesişim. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__sma-kesisim-rsi-gecmis-s0454"
    varsayilan_parametreler = {"hizli": 9, "yavas": 21, "rsi_n": 14, "rsi_alt": 30, "rsi_ust": 70, "rsi_geri": 5, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        sh, sy = g.sma(k, int(p["hizli"])), g.sma(k, int(p["yavas"]))
        r = g.rsi(k, int(p["rsi_n"]))
        b = int(p["rsi_geri"])
        asiri_alt = r.rolling(b, min_periods=b).min() <= float(p["rsi_alt"])
        asiri_ust = r.rolling(b, min_periods=b).max() >= float(p["rsi_ust"])
        yk, ak = _yukari(sh, sy), _asagi(sh, sy)
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, yk & asiri_alt, ak & asiri_ust, k - risk, k + risk), cikis_long=ak, cikis_short=yk)


class EmaRsiKademeliHedef(_Taban):
    """X005:456 (4h, iki yön): kapanış > EMA(50) VE RSI(14) 50'yi yukarı keserse long; kapanış < EMA(50) VE RSI(14) 50'yi aşağı
    keserse short. Pozisyonun %50'si +%2'de, kalan %50'si +%4'te kapanır; stop giriş (sinyal kapanışı) fiyatının %2'si (iki parça).
    Stop %2 = 1R olduğundan +%2 = 1R kısmi (CikisAyarlari.kismi=((1.0, 0.5),)), +%4 = hedef (2R). Başabaşa çekme yok."""
    ad = "kapanis__ema-rsi-kademeli-s0456"
    varsayilan_parametreler = {"ema": 50, "rsi_n": 14, "esik": 50, "sl": 0.02, "tp2": 0.04}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),))

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ema = g.ema(k, int(p["ema"]))
        r = g.rsi(k, int(p["rsi_n"]))
        sl, tp = float(p["sl"]), float(p["tp2"])
        return cerceve(mumlar, (k > ema) & _seviye_yukari(r, float(p["esik"])),
                       (k < ema) & _seviye_asagi(r, float(p["esik"])), k * (1 - sl), k * (1 + sl),
                       hedef_l=k * (1 + tp), hedef_s=k * (1 - tp))


class TersParabolikSar(_Taban):
    """X005:466 (K6, 1d, long): ters (contrarian) Parabolic SAR (0,02/0,02/0,2): kapanış o mumda geçerli SAR'ın (bir önceki mumda
    hesaplanan) ALTINDAYKEN long (durum); kapanış SAR'ın üstüne çıkınca çık. Stop yok -> ATR(14)x3. SAR adımı = hızlanma artışı."""
    ad = "kapanis__ters-psar-s0466"
    varsayilan_parametreler = {"psar_af_baslangic": 0.02, "psar_af_artis": 0.02, "psar_af_maks": 0.2, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        if float(p["psar_af_baslangic"]) != float(p["psar_af_artis"]):
            raise ValueError("psar: baslangic ve artis esit olmali (motor gostergesi tek adim kullanir)")
        k = mumlar["kapanis"]
        sar = g.psar(mumlar["yuksek"], mumlar["dusuk"], float(p["psar_af_artis"]), float(p["psar_af_maks"]))["sar"].shift(1)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, k < sar, False, k - r, k + r), cikis_long=k > sar)


class KontrarianStokastik(_Taban):
    """X005:467 (1d, long): ham %K(14), %D = %K'nın SMA(3); %K < %D ve %D < önceki %D -> long (durum); koşul bozulunca
    (%K >= %D ya da %D >= önceki %D) çık. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__kontrarian-stok-s0467"
    varsayilan_parametreler = {"k_n": 14, "d_n": 3, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        st = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], k, int(p["k_n"]), int(p["d_n"]))
        d = st["d"]
        gecerli = d.notna() & d.shift(1).notna()
        kosul = ((st["k"] < d) & (d < d.shift(1))).fillna(False)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, kosul, False, k - r, k + r), cikis_long=gecerli & ~kosul)


class RsiYukariAsagiKesisim(_Taban):
    """X005:484 (1d, long): RSI(14) 30'un altına inip tekrar 30'un üstüne çıkınca al; 70'in üstüne çıkıp tekrar 70'in altına
    inince sat. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__rsi-30-70-kesisim-s0484"
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30, "ust": 70, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _seviye_yukari(r, float(p["alt"])), False, k - risk, k + risk),
                     cikis_long=_seviye_asagi(r, float(p["ust"])))


class StokastikKdKesisim(_Taban):
    """X005:485 (1d, long): %K(14) (ham) %D'yi (%K'nın SMA(3)) yukarı keserse al; aşağı keserse sat. Stop yok -> ATR(14)x3."""
    ad = "kapanis__stok-kd-kesisim-s0485"
    varsayilan_parametreler = {"k": 14, "d": 3, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        st = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], k, int(p["k"]), int(p["d"]))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _yukari(st["k"], st["d"]), False, k - r, k + r),
                     cikis_long=_asagi(st["k"], st["d"]))


class RsiBogaYutanAralik(_Taban):
    """X005:492 (1d, long): RSI(10) <= 30 VE boğa yutan (önceki düşüş mumunun gövdesini saran yükseliş mumu: önceki kapanış<açılış,
    bugün kapanış>açılış, açılış<=önceki kapanış, kapanış>=önceki açılış) -> long. Hedef = giriş+1xSMA(10)(yüksek-düşük), stop =
    giriş-1xSMA(10)(yüksek-düşük) (kaynak stopu; sinyal kapanışından)."""
    ad = "kapanis__rsi-boga-yutan-s0492"
    varsayilan_parametreler = {"rsi_n": 10, "esik": 30, "aralik_n": 10, "tp_k": 1.0, "sl_k": 1.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        o, h, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        yutan = (k > o) & (k.shift(1) < o.shift(1)) & (o <= k.shift(1)) & (k >= o.shift(1))
        aralik = g.sma(h - d, int(p["aralik_n"]))
        gir = yutan & (g.rsi(k, int(p["rsi_n"])) <= float(p["esik"]))
        return cerceve(mumlar, gir, False, k - float(p["sl_k"]) * aralik, k,
                       hedef_l=k + float(p["tp_k"]) * aralik)


class Nr7IcGunShort(_Taban):
    """X005:494 (1d, short-only): aralık = yüksek-düşük; NR7: aralık önceki 6 günün her birinden küçük; inside day: yüksek<önceki
    yüksek ve düşük>önceki düşük. NR7 VE inside day aynı gün VE kapanış<açılış VE SMA(14) eğimi aşağı/düz (SMA-SMA[1] <= 0) -> short.
    Çıkış: giriş sonrası ilk kapanış<açılış (düşüş) mumunun kapanışında (cikis_short = kapanış<açılış). Kaynakta stop yok ->
    ATR(14)x3 (uyarlama)."""
    ad = "kapanis__nr7-icgun-short-s0494"
    varsayilan_parametreler = {"nr_bakis": 7, "sma_len": 14, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        o, h, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        aralik = h - d
        n = int(p["nr_bakis"]) - 1
        nr = aralik < aralik.shift(1).rolling(n, min_periods=n).min()
        ic = (h < h.shift(1)) & (d > d.shift(1))
        sma = g.sma(k, int(p["sma_len"]))
        gir = nr & ic & (k < o) & ((sma - sma.shift(1)) <= 0)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, False, gir, k - r, k + r), cikis_short=k < o)


class SezonsalMacd(_Taban):
    """X005:495 (K6, 1d, long): her yıl 16 Ekim'de (o gün yoksa ilk sonraki mumda) MACD(12,26,9) boğa durumundaysa long, değilse ilk
    boğa sinyalini bekle; 20 Nisan'da (ilk mumda) MACD ayı durumundaysa çık, değilse ilk ayı sinyalinde çık. Boğa sinyali = MACD
    çizgisi sinyal çizgisini ya da sıfırı yukarı keser; ayı sinyali = aşağı keser. Durum = son sinyalin yönü. Stop yok -> ATR(14)x3.
    Mevsim durum makinesi yalnız fiyat/takvimden yürür (sanal durum; gerçek pozisyona bağlı değil); giriş yalnız GİRİŞ ANINDA
    sinyaldir (stop sonrası aynı mevsimde yeniden giriş yok), çıkış (cikis_long) durum makinesi 'dışarıdayken' hep True'dur."""
    ad = "kapanis__sezonsal-macd-s0495"
    varsayilan_parametreler = {"macd_h": 12, "macd_y": 26, "macd_s": 9, "giris_ay": 10, "giris_gun": 16,
                               "cikis_ay": 4, "cikis_gun": 20, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        m = g.macd(k, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))
        boga = (_yukari(m["macd"], m["sinyal"]) | _yukari(m["macd"], 0.0)).to_numpy(bool)
        ayi = (_asagi(m["macd"], m["sinyal"]) | _asagi(m["macd"], 0.0)).to_numpy(bool)
        ay_gun = (mumlar.index.month * 100 + mumlar.index.day).to_numpy()
        giris_md = int(p["giris_ay"]) * 100 + int(p["giris_gun"])
        cikis_md = int(p["cikis_ay"]) * 100 + int(p["cikis_gun"])
        yaz = (ay_gun >= cikis_md) & (ay_gun < giris_md)          # çıkış tarihi ile giriş tarihi arası
        n = len(k)
        giris = np.zeros(n, bool)
        icerde = np.zeros(n, bool)
        durum = 0          # 0 dışarıda, 1 boğa sinyali bekliyor, 2 long, 3 long (ayı sinyali bekliyor)
        boga_durumu = None
        for t in range(n):
            if boga[t] and not ayi[t]:
                boga_durumu = True
            elif ayi[t] and not boga[t]:
                boga_durumu = False
            yeni_sezon = t > 0 and ay_gun[t] >= giris_md and ay_gun[t - 1] < giris_md
            if durum == 0:
                if yeni_sezon:
                    if boga_durumu is True:
                        durum, giris[t] = 2, True
                    else:
                        durum = 1
            elif durum == 1:
                if yaz[t]:
                    durum = 0
                elif boga[t]:
                    durum, giris[t] = 2, True
            elif durum == 2:
                if yaz[t]:
                    durum = 0 if boga_durumu is False else 3
            elif durum == 3:
                if ayi[t]:
                    durum = 0
            icerde[t] = durum in (2, 3)
        r = _atr_riski(mumlar, p)
        idx = mumlar.index
        return _ekle(cerceve(mumlar, pd.Series(giris, index=idx), False, k - r, k + r),
                     cikis_long=pd.Series(~icerde, index=idx))


class Nr7KapanisKirilim(_Taban):
    """X005:502 (1d, long): bugünün yüksek-düşük aralığı önceki 6 günün aralıklarından küçükse (NR7) kapanışta al; kapanış önceki
    günün yükseğinin üstündeyse (o günün kapanışında) sat. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__nr7-kapanis-s0502"
    varsayilan_parametreler = {"nr": 7, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        aralik = h - d
        n = int(p["nr"]) - 1
        nr = aralik < aralik.shift(1).rolling(n, min_periods=n).min()
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, nr, False, k - r, k + r), cikis_long=k > h.shift(1))


class ZirveYakinlik(_Taban):
    """X005:503 (1d, long): kapanış / (veri başından beri en yüksek kapanış) >= 0,95 -> long (durum); < 0,95 olunca çık.
    Zirve genişleyen (nedensel) maksimumdur. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__zirve-yakinlik-s0503"
    varsayilan_parametreler = {"zirve_uzaklik": 0.05, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        oran = k / k.cummax()
        esik = 1.0 - float(p["zirve_uzaklik"])
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, oran >= esik, False, k - r, k + r), cikis_long=oran < esik)


class FonlamaTers(_Taban):
    """X005:508 (8h, iki yön): bar kapanışında bilinen son fonlama oranı r (baz puan, 1 bp = 1e-4): r <= esik_long_bp -> long,
    r >= esik_short_bp -> short; 1 fonlama periyodu (1 adet 8h mum) tutulup kapatılır (zaman_cikisi_mum=1). Varyantlar: -15,47/+18,80 bp
    (±1σ) ve -32,61/+35,93 bp (±2σ). Stop kaynakta yok -> ATR(14)x3. `funding_orani` sütunu araştırma katmanınca eklenir."""
    ad = "kapanis__fonlama-ters-s0508"
    funding_gerekli = True
    varsayilan_parametreler = {"esik_long_bp": -15.47, "esik_short_bp": 18.8, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1)

    def sinyaller(self, mumlar):
        p = self.parametreler
        if "funding_orani" not in mumlar.columns:
            raise ValueError("funding_orani sütunu yok (funding_gerekli=True; araştırma katmanı ekler)")
        k = mumlar["kapanis"]
        bp = mumlar["funding_orani"].astype(float) * 1e4
        r = _atr_riski(mumlar, p)
        return cerceve(mumlar, bp <= float(p["esik_long_bp"]), bp >= float(p["esik_short_bp"]), k - r, k + r)


class MaGeriDusukSeri(_Taban):
    """X005:509 (1d, iki yön): long: kapanış > SMA(200) VE kapanış < SMA(5) VE son 3 günün her birinde bir öncekine göre daha düşük
    dip ve daha düşük tepe -> long; kapanış SMA(5) üstüne çıkınca sat. Short ayna (kapanış<SMA200, >SMA5, 3 gün daha yüksek tepe ve
    dip; çıkış kapanış<SMA5). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ma200-ma5-seri-s0509"
    varsayilan_parametreler = {"trend_ma": 200, "ma_kisa": 5, "seri": 3, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["seri"])
        dus = ((d < d.shift(1)) & (h < h.shift(1))).astype(int).rolling(n, min_periods=n).sum() == n
        yuk = ((d > d.shift(1)) & (h > h.shift(1))).astype(int).rolling(n, min_periods=n).sum() == n
        trend, kisa = g.sma(k, int(p["trend_ma"])), g.sma(k, int(p["ma_kisa"]))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, (k > trend) & (k < kisa) & dus, (k < trend) & (k > kisa) & yuk, k - r, k + r),
                     cikis_long=k > kisa, cikis_short=k < kisa)


class KeltnerRenkDonus5m(_Taban):
    """X005:510 (5m, iki yön, pozisyon yokken): kapanış < EMA(20)-2xATR(14) VE kapanış > açılış -> long; kapanış > EMA(20)+2xATR(14) VE
    kapanış < açılış -> short; çıkış long: kapanış >= EMA(20), short: kapanış <= EMA(20). Stop giriş (sinyal kapanışı) -/+ 2xATR(14)."""
    ad = "kapanis__keltner-donus-s0510"
    varsayilan_parametreler = {"ema": 20, "atr_n": 14, "bant_k": 2.0, "stop_atr": 2.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        o, k = mumlar["acilis"], mumlar["kapanis"]
        ema = g.ema(k, int(p["ema"]))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_n"]))
        bant = float(p["bant_k"]) * atr
        risk = float(p["stop_atr"]) * atr
        return _ekle(cerceve(mumlar, (k < ema - bant) & (k > o), (k > ema + bant) & (k < o), k - risk, k + risk),
                     cikis_long=k >= ema, cikis_short=k <= ema)


class VwapAtrDonus5m(_Taban):
    """X005:513 (5m, iki yön): kapanış < günlük (UTC) VWAP - k x ATR(14) -> long; kapanış > VWAP + k x ATR(14) -> short; çıkış long:
    kapanış >= VWAP, short: kapanış <= VWAP. Stop giriş (sinyal kapanışı) -/+ k x ATR(14). VWAP: tipik fiyat (H+L+C)/3, hacim ağırlıklı,
    her UTC gününde sıfırlanır, t mumuna kadar kümülatif (nedensel)."""
    ad = "kapanis__vwap-atr-donus-s0513"
    varsayilan_parametreler = {"k": 2.0, "atr_n": 14}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        gun = mumlar.index.floor("D").asi8
        vwap = g.vwap_seans(mumlar["yuksek"], mumlar["dusuk"], k, mumlar["hacim"], gun)["vwap"]
        risk = float(p["k"]) * g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_n"]))
        return _ekle(cerceve(mumlar, k < vwap - risk, k > vwap + risk, k - risk, k + risk),
                     cikis_long=k >= vwap, cikis_short=k <= vwap)


class AyGunuDusenKapanis(_Taban):
    """X005:519 (1d, long): ayın günü >= 25 VE 2 ardışık düşen kapanış (kapanış<önceki, önceki<ikinci önceki) VE pozisyon yoksa al;
    RSI(2) 65'i aşınca sat (RSI Wilder). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ay-gunu-dusen-s0519"
    varsayilan_parametreler = {"gun_min": 25, "dusen_kapanis": 2, "rsi_n": 2, "rsi_cikis": 65, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        n = int(p["dusen_kapanis"])
        dus = (k.diff() < 0).astype(int).rolling(n, min_periods=n).sum() == n
        gun = pd.Series(mumlar.index.day, index=mumlar.index)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, (gun >= int(p["gun_min"])) & dus, False, k - r, k + r),
                     cikis_long=g.rsi(k, int(p["rsi_n"])) > float(p["rsi_cikis"]))


class IchimokuBulutKirilim(_Taban):
    """X005:521 (1d, long): kapanış hem Senkou Span A hem Span B'nin (bulut üst sınırı) üstüne ÇIKINCA (üstte değilken üstte) al;
    kapanış ikisinin de altına (bulut alt sınırı) inince sat. Ichimoku 9/26/52, kaydırma 26 (bulut nedensel, gelecek bulut yok).
    Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ichimoku-bulut-s0521"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydirma": 26, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ich = ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]),
                       int(p["kaydirma"]))
        ustte = (k > ich["bulut_ust"]).fillna(False)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, ustte & ~ustte.shift(1, fill_value=False), False, k - r, k + r),
                     cikis_long=k < ich["bulut_alt"])


class KamaSmaFarkCevir(_Taban):
    """X005:525 (1d, iki yön, her zaman piyasada): KAMA(er=10, hızlı=2, yavaş=30) - SMA(100) >= esik (0) ise long, <= -esik ise short;
    fark işaret değiştirince pozisyon ters çevrilir (karşı yön çıkışı + aynı mumda karşı yön girişi). Stop yok -> ATR(14)x3."""
    ad = "kapanis__kama-sma-fark-s0525"
    varsayilan_parametreler = {"er": 10, "hizli": 2, "yavas": 30, "sma": 100, "esik": 0.0, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        fark = kama(k, int(p["er"]), int(p["hizli"]), int(p["yavas"])) - g.sma(k, int(p["sma"]))
        e = float(p["esik"])
        lg = (fark >= e).fillna(False)
        st = (fark <= -e).fillna(False) & ~lg
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, lg, st, k - r, k + r), cikis_long=st, cikis_short=lg)


class TsmomSmaDurum(_Taban):
    """X005:540 (1d, long): kural 'tsmom': kapanış > N gün önceki kapanış; kural 'sma': kapanış > SMA(N); koşul sağlanırken long,
    bozulunca nakit. N in {10,50,100,200} (8 varyant: 2 kural x 4 N). Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__tsmom-sma-durum-s0540"
    varsayilan_parametreler = {"kural": "tsmom", "N": 10, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        n = int(p["N"])
        if p["kural"] == "tsmom":
            kosul = k > k.shift(n)
        elif p["kural"] == "sma":
            kosul = k > g.sma(k, n)
        else:
            raise ValueError("kural 'tsmom' ya da 'sma' olmali")
        kosul = kosul.fillna(False)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, kosul, False, k - r, k + r), cikis_long=~kosul)


class BbAltYukariKesis(_Taban):
    """X005:544 (1d, long): BB(N, 2 SD, kapanış): kapanış alt bandı aşağıdan yukarı keserse long (ardışık ikinci alım yok: motor
    açık pozisyonda yeni girişi atlar); kapanış üst bandı yukarıdan aşağı keserse kapat. N in {10,20,50,250} (4 varyant).
    Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__bb-alt-yukari-s0544"
    varsayilan_parametreler = {"bb_n": 10, "bb_std": 2.0, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_std"]))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _yukari(k, bb["alt"]), False, k - r, k + r), cikis_long=_asagi(k, bb["ust"]))


class AdxMomDiRoi(_Taban):
    """X005:548 (1h, long): ADX(14)>25 ve MOM(14)>0 ve +DI(25)>25 ve +DI>-DI -> long (durum); çıkış ADX>25 ve MOM<0 ve -DI(25)>25 ve
    +DI<-DI; ROI: kâr >= %1 ise kapat (azalan_roi=((0, 1.0),)); stop giriş (sinyal kapanışı) fiyatının %25 altı; gün sonu çıkışı yok.
    MOM(n) = kapanış - n önceki kapanış."""
    ad = "kapanis__adx-mom-di-roi-s0548"
    varsayilan_parametreler = {"adx_n": 14, "di_n": 25, "mom_n": 14, "adx_esik": 25, "di_esik": 25, "stop_yuzde": 25.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 1.0),))

    def sinyaller(self, mumlar):
        p = self.parametreler
        h, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        adx = g.adx(h, d, k, int(p["adx_n"]))["adx"]
        di = g.adx(h, d, k, int(p["di_n"]))
        mom = k - k.shift(int(p["mom_n"]))
        ae, de = float(p["adx_esik"]), float(p["di_esik"])
        gir = (adx > ae) & (mom > 0) & (di["arti_di"] > de) & (di["arti_di"] > di["eksi_di"])
        cik = (adx > ae) & (mom < 0) & (di["eksi_di"] > de) & (di["arti_di"] < di["eksi_di"])
        return _ekle(cerceve(mumlar, gir, False, k * (1 - float(p["stop_yuzde"]) / 100.0), k), cikis_long=cik)


class MacdAoSifirRoi(_Taban):
    """X005:549 (1h, long): MACD(12,26,9) çizgisi > 0 VE Awesome Oscillator(5,34; medyan fiyat) bir önceki mumda < 0, bu mumda > 0
    -> long; çıkış: MACD < 0 iken AO sıfırı aşağı keserse ya da +%10 kâr (ROI: azalan_roi=((0, 10.0),)); stop giriş (sinyal kapanışı)
    fiyatının %25 altı."""
    ad = "kapanis__macd-ao-roi-s0549"
    varsayilan_parametreler = {"macd_h": 12, "macd_y": 26, "macd_s": 9, "sl_yuzde": 25.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 10.0),))

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        macd = g.macd(k, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))["macd"]
        ao = ao_ac(mumlar["yuksek"], mumlar["dusuk"])["ao"]
        gir = (macd > 0) & (ao.shift(1) < 0) & (ao > 0)
        cik = (macd < 0) & (ao.shift(1) >= 0) & (ao < 0)
        return _ekle(cerceve(mumlar, gir, False, k * (1 - float(p["sl_yuzde"]) / 100.0), k), cikis_long=cik)


class VarOttKesisim(_Taban):
    """X005:550 (1h, iki yön): VAR (Chande VIDYA; uzunluk 2, CMO 9) çizgisi, VAR üzerinde %1,4 OTT çizgisinin 2 mum geriye kaydırılmış
    halini yukarı keserse long, aşağı keserse short; ADX(14) > 60 olunca tüm pozisyonlar kapanır (cikis). ROI tablosu (dakika ->
    1h mum): 0dk %10, 60dk %5, 120dk %2,5 (30dk %75 basamağı mum sınırına denk gelmediğinden düşer); stop %26,5; kâr %10'u
    geçince %5 iz süren (geri_cekilme_yuzde=5, min kâr 10). İlk 150 mum VAR ısınması için sinyalsiz (sayısal başlangıç)."""
    ad = "kapanis__var-ott-s0550"
    varsayilan_parametreler = {"var_n": 2, "cmo": 9, "ott_pct": 1.4, "ott_gecikme": 2, "adx_n": 14, "adx_cikis": 60,
                               "sl_yuzde": 26.5, "isinma": 150}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 10.0), (1, 5.0), (2, 2.5)), geri_cekilme_yuzde=5.0,
                                   geri_cekilme_min_kar_yuzde=10.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        v = var_ma(k, int(p["var_n"]), int(p["cmo"]))
        o = ott(v, float(p["ott_pct"])).shift(int(p["ott_gecikme"]))
        hazir = pd.Series(np.arange(len(k)) >= int(p["isinma"]), index=k.index)
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], k, int(p["adx_n"]))["adx"]
        sl = float(p["sl_yuzde"]) / 100.0
        return cerceve(mumlar, _yukari(v, o) & hazir, _asagi(v, o) & hazir, k * (1 - sl), k * (1 + sl),
                       cikis=(adx > float(p["adx_cikis"])) & hazir)


class MacdBbRsiRoi5m(_Taban):
    """X005:552 (5m, long): MACD(12,26,9) çizgisi > 0 VE MACD > sinyal VE Bollinger(12, 2σ) üst bandı bir önceki mumdakinden yüksek VE
    RSI(7) > 70 -> long; çıkış RSI(7) > 80 ya da +%1 (ROI: azalan_roi=((0, 1.0),)); stop giriş (sinyal kapanışı) fiyatının %25 altı."""
    ad = "kapanis__macd-bb-rsi-roi-s0552"
    varsayilan_parametreler = {"macd_h": 12, "macd_y": 26, "macd_s": 9, "bb_n": 12, "bb_k": 2.0, "rsi_n": 7, "giris": 70,
                               "cikis": 80, "sl_yuzde": 25.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 1.0),))

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        m = g.macd(k, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))
        ust = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))["ust"]
        r = g.rsi(k, int(p["rsi_n"]))
        gir = (m["macd"] > 0) & (m["macd"] > m["sinyal"]) & (ust > ust.shift(1)) & (r > float(p["giris"]))
        return _ekle(cerceve(mumlar, gir, False, k * (1 - float(p["sl_yuzde"]) / 100.0), k),
                     cikis_long=r > float(p["cikis"]))


class Ema800Kesisim(KancaDestek, _Taban):
    """X005:554 (1h, long): kapanış EMA(800)'ü yukarı keserse (hacim>0) long; kapanış EMA(800)x0,99 çizgisini aşağı keserse çık; stop
    giriş (sinyal kapanışı) fiyatının %15 altı, iz süren: giriş sonrası zirve fiyatın (en yüksek HIGH) %15 altına kapanış inerse çık
    (kanca; kaynakta iz süren ofseti yok, stop değeri kadar iz)."""
    ad = "kapanis__ema800-kesisim-s0554"
    varsayilan_parametreler = {"ema_n": 800, "cikis_esik": 0.01, "sl_yuzde": 15.0}

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, float(self.parametreler["sl_yuzde"]))

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ema = g.ema(k, int(p["ema_n"]))
        gir = _yukari(k, ema) & (mumlar["hacim"] > 0)
        return _ekle(cerceve(mumlar, gir, False, k * (1 - float(p["sl_yuzde"]) / 100.0), k),
                     cikis_long=_asagi(k, ema * (1.0 - float(p["cikis_esik"]))))


class MacdSifirAltiEma(_Taban):
    """X005:555 (1h, long): MACD(12,26,9) çizgisi sıfırın altındayken sinyali yukarı keser VE mum düşüğü > EMA(100) -> long; çıkış
    MACD sıfırı aşağı keserse ya da mum düşüğü < EMA(100); stop giriş (sinyal kapanışı) fiyatının %20 altı (iz süren kapalı)."""
    ad = "kapanis__macd-sifir-alti-ema-s0555"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "ema": 100, "sl_yuzde": 20.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, d = mumlar["kapanis"], mumlar["dusuk"]
        m = g.macd(k, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        ema = g.ema(k, int(p["ema"]))
        gir = _yukari(m["macd"], m["sinyal"]) & (m["macd"] < 0) & (d > ema)
        return _ekle(cerceve(mumlar, gir, False, k * (1 - float(p["sl_yuzde"]) / 100.0), k),
                     cikis_long=_asagi(m["macd"], 0.0) | (d < ema))


class IchimokuSenkouKesisim(KancaDestek, _Taban):
    """X005:556 (4h, long): Ichimoku (dönüşüm 20, baz 60, Senkou B 120, kaydırma 30): Senkou A Senkou B'yi yukarı keser VE kapanış
    her iki spanın üstünde (A>B: yeşil bulut) -> long; çıkış Senkou B Senkou A'yı yukarı keser VE kapanış her iki spanın altında
    (kırmızı bulut). Kâr %50'yi geçince %45 mesafeli iz süren (kanca: zirve kârı >= %50 iken kapanış, giriş sonrası en yüksek HIGH'ın %45
    altına inerse çık). Kaynakta başlangıç stopu yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__ichimoku-senkou-s0556"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydirma": 30, "iz_esik": 50.0, "iz_mesafe": 45.0, **_ATR}

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        return tepe_geri_cekilme(d, float(p["iz_mesafe"]), float(p["iz_esik"]))

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ich = ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]),
                       int(p["kaydirma"]))
        a, b = ich["span_a"], ich["span_b"]
        gir = _yukari(a, b) & (k > ich["bulut_ust"]) & (a > b)
        cik = _yukari(b, a) & (k < ich["bulut_alt"]) & (b > a)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - r, k + r), cikis_long=cik)


class SmaSeritDizili(_Taban):
    """X005:557 (1d, long): S_j = SMA(15)[t - 5j], j = 0..5 (6 gecikmeli kopya); S0>=S1>=...>=S5 (şerit yukarı dizili) ve pozisyon
    yoksa al; S0<=S1<=...<=S5 olunca kapat. Stop yok -> ATR(14)x3 (uyarlama)."""
    ad = "kapanis__sma-serit-s0557"
    varsayilan_parametreler = {"sma": 15, "serit": 6, "gecikme_adim": 5, **_ATR}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        s = g.sma(k, int(p["sma"]))
        adim = int(p["gecikme_adim"])
        kopya = [s.shift(adim * j) for j in range(int(p["serit"]))]
        yukari = pd.Series(True, index=k.index)
        asagi = pd.Series(True, index=k.index)
        for a, b in zip(kopya[:-1], kopya[1:]):
            yukari &= (a >= b)
            asagi &= (a <= b)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, yukari, False, k - r, k + r), cikis_long=asagi)


# ---------------------------------------------------------------- satır -> sınıf kaydı
SINIFLAR: dict = {}
VARYANTLAR: list = []
KODLANAMADI: list = []

_BOS = [{}]


def _kayit(kaynak_id: str, sinif, varyantlar: list, tflar: list) -> None:
    """Sınıfı SINIFLAR'a ekler, her varyant x TF için VARYANTLAR kaydı yazar (#v1.. varyant-ana, TF-ikincil sırayla)."""
    SINIFLAR[sinif.ad] = sinif
    no = 0
    for v in varyantlar:
        for tf in tflar:
            no += 1
            VARYANTLAR.append({"kimlik": f"{kaynak_id}#v{no}", "sinif": sinif.ad,
                               "parametreler": {**sinif.varsayilan_parametreler, **v}, "tf": tf})


_kayit("HAM:X005:428", CciEsikSifir, [{"esik": 100}, {"esik": 200}], ["1d"])
_kayit("HAM:X005:430", BbAltArdisikYukselis, _BOS, ["1d"])
_kayit("HAM:X005:432", Rsi5mYuzdeStopHedef, _BOS, ["5m"])
_kayit("HAM:X005:435", MacdRsiAtrHedef, _BOS, ["1d"])
_kayit("HAM:X005:438", HaftalikSmaMacd, _BOS, ["1d"])
_kayit("HAM:X005:448", RejimRsiBantAlt, _BOS, ["1d"])
_kayit("HAM:X005:449", UltimateOsilator, _BOS, ["1h"])
_kayit("HAM:X005:450", SmaRsiDestekStop, _BOS, ["1h"])
_kayit("HAM:X005:454", SmaKesisimRsiGecmis, _BOS, ["1d"])
_kayit("HAM:X005:456", EmaRsiKademeliHedef, _BOS, ["4h"])
_kayit("HAM:X005:466", TersParabolikSar, _BOS, ["1d"])
_kayit("HAM:X005:467", KontrarianStokastik, _BOS, ["1d"])
_kayit("HAM:X005:484", RsiYukariAsagiKesisim, _BOS, ["1d"])
_kayit("HAM:X005:485", StokastikKdKesisim, _BOS, ["1d"])
_kayit("HAM:X005:492", RsiBogaYutanAralik, _BOS, ["1d"])
_kayit("HAM:X005:494", Nr7IcGunShort, _BOS, ["1d"])
_kayit("HAM:X005:495", SezonsalMacd, _BOS, ["1d"])
_kayit("HAM:X005:502", Nr7KapanisKirilim, _BOS, ["1d"])
_kayit("HAM:X005:503", ZirveYakinlik, _BOS, ["1d"])
_kayit("HAM:X005:508", FonlamaTers,
       [{"esik_long_bp": -15.47, "esik_short_bp": 18.8}, {"esik_long_bp": -32.61, "esik_short_bp": 35.93}], ["8h"])
_kayit("HAM:X005:509", MaGeriDusukSeri, _BOS, ["1d"])
_kayit("HAM:X005:510", KeltnerRenkDonus5m, _BOS, ["5m"])
_kayit("HAM:X005:513", VwapAtrDonus5m, _BOS, ["5m"])
_kayit("HAM:X005:519", AyGunuDusenKapanis, _BOS, ["1d"])
_kayit("HAM:X005:521", IchimokuBulutKirilim, _BOS, ["1d"])
_kayit("HAM:X005:525", KamaSmaFarkCevir, _BOS, ["1d"])
_kayit("HAM:X005:540", TsmomSmaDurum,
       [{"kural": kural, "N": n} for kural in ("tsmom", "sma") for n in (10, 50, 100, 200)], ["1d"])
_kayit("HAM:X005:544", BbAltYukariKesis, [{"bb_n": n} for n in (10, 20, 50, 250)], ["1d"])
_kayit("HAM:X005:548", AdxMomDiRoi, _BOS, ["1h"])
_kayit("HAM:X005:549", MacdAoSifirRoi, _BOS, ["1h"])
_kayit("HAM:X005:550", VarOttKesisim, _BOS, ["1h"])
_kayit("HAM:X005:552", MacdBbRsiRoi5m, _BOS, ["5m"])
_kayit("HAM:X005:554", Ema800Kesisim, _BOS, ["1h"])
_kayit("HAM:X005:555", MacdSifirAltiEma, _BOS, ["1h"])
_kayit("HAM:X005:556", IchimokuSenkouKesisim, _BOS, ["4h"])
_kayit("HAM:X005:557", SmaSeritDizili, _BOS, ["1d"])

KODLANAMADI = [
    # 436, 446, 447: kod_g8_modul.py (kanca ile kodlandı).
    {"kimlik": "HAM:X005:553",
     "neden": "motorda ifade edilemiyor: giriş filtresi BTC 1h RSI(14)>35 (başka sembol verisi; strateji yalnız kendi mumlarını alır), "
              "4h ve 1d üst-TF bilgi verisi + güven skoru süzgeci, ve custom_exit kaskadı (2s ve kâr<-%1,5, 4s ve kâr<0, 8s ve kâr<%0,5, "
              "16s ve kâr<%1: zarardayken/kâr eşiğine bağlı zaman çıkışı; azalan_roi yalnız kârda çıkar)."},
]
