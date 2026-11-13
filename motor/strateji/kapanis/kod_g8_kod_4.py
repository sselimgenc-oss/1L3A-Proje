"""Kapanış turu kodlama partisi g8_kod_4 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_4.csv, 40 kaynak satırı).

Hepsi HAM:X005:* (trend / ortalamaya dönüş listesi). Her kaynak satır için bir sınıf vardır; aynı yapıdaki satırlar
ortak bir taban sınıftan türeyen, yalnız `varsayilan_parametreler` ve `ad` farkı olan alt sınıflardır. Kurallar `kural_tam`
metninden kendi kodumuzla yazıldı; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan (motor sonraki açılışta doldurur);
gelecek verisi yok. Kaynak stopu yoksa ATR(14)x3 uyarlaması. Yönlü çıkış `cikis_long` / `cikis_short` sütunlarıyla verilir.

Genel biçim kararları (ILERLEME.md politikaları):
- Durum koşullu girişler (ör. "RSI<30 iken al") her mumda yon != 0 üretir; motor pozisyon açıkken yeni girişi atlar.
- Stop-emir girişi/çıkışı (362) bar içi değil: seviye mum KAPANIŞIYLA aşılınca sonraki açılışta işlem (politika d).
- Kesişim: "x, y'yi yukarı keser" = x[t-1] <= y[t-1] ve x[t] > y[t]; seviye kesişimi: x[t-1] < seviye <= x[t] (yukarı),
  x[t-1] >= seviye > x[t] (aşağı).

KODLANAMADI (VARYANTLAR dışında, bkz. `KODLANAMADI`): 400, 401, 416 (min. tutma süresine bağlı çıkış + süreye bağlı stop),
419 (stop-and-reverse + pozisyona bağlı yukarı kayan stop + min. tutma).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import donchian_kanal
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


def _ma(seri: pd.Series, n: int, tip: str) -> pd.Series:
    return g.ema(seri, n) if str(tip).lower() == "ema" else g.sma(seri, n)


def _atr_riski(m: pd.DataFrame, p: dict) -> pd.Series:
    return float(p["atr_k"]) * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))


def _ekle(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _rsi_basit(kap: pd.Series, n: int) -> pd.Series:
    """Wilder yerine basit ortalamalı RSI: yukarı/aşağı hareketlerin n'lik SMA'sı."""
    fark = kap.diff()
    yukari = fark.clip(lower=0.0).rolling(n, min_periods=n).mean()
    asagi = (-fark).clip(lower=0.0).rolling(n, min_periods=n).mean()
    return 100.0 - 100.0 / (1.0 + yukari / asagi)


class _Taban(Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


# ---------------------------------------------------------------- taban sınıflar
class Bb038EmaKesisim(_Taban):
    """X005:357: kapanış üst Bollinger (20, 0,38σ) bandını yukarı keser ve kapanış > EMA(80) -> long; alt bandı aşağı
    keser ve kapanış < EMA(80) -> short. Stop: son 7 barın (sinyal mumu dahil) en düşük dibi (short: en yüksek tepesi);
    hedef = stop mesafesinin 1,6 katı. Ek kesişim kontrolleri ve inside bar teyidi kapalı. Uyarlama yok (kaynak stopu var)."""
    varsayilan_parametreler = {"bb_n": 20, "bb_sigma": 0.38, "ema_filtre": 80, "stop_bar_n": 7, "hedef_r": 1.6}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, h, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_sigma"]))
        ema = g.ema(k, int(p["ema_filtre"]))
        n = int(p["stop_bar_n"])
        stop_l = d.rolling(n, min_periods=n).min()
        stop_s = h.rolling(n, min_periods=n).max()
        r = float(p["hedef_r"])
        long_ok = _yukari(k, bb["ust"]) & (k > ema)
        short_ok = _asagi(k, bb["alt"]) & (k < ema)
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s,
                       hedef_l=k + r * (k - stop_l), hedef_s=k - r * (stop_s - k))


class EmaAcilisStopEmir(_Taban):
    """X005:362: sinyal mumu t: açılış < EMA(9) ve kapanış > EMA(9). t+1 mumunun KAPANIŞI yüksek[t]'yi aşarsa (stop-alış
    seviyesi) t+1 kapanışında sinyal, sonraki açılışta long; aşılmazsa emir iptal (geçerlilik 1 bar). Çıkış: satış sinyal
    mumu s: açılış > EMA(9) ve kapanış < EMA(9); s+1 mumunun kapanışı düşük[s]'nin altına inerse sonraki açılışta kapat.
    Uyarlama: stop-emir bar içi değil mum kapanışıyla (politika d); çıkış emri için de 1 bar geçerlilik (girişle simetrik, kaynakta
    süre yazmıyor); stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"ema_n": 9, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, h, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ema = g.ema(k, int(p["ema_n"]))
        al = ((a < ema) & (k > ema)).fillna(False)
        sat = ((a > ema) & (k < ema)).fillna(False)
        gir = al.shift(1, fill_value=False) & (k > h.shift(1))
        cik = sat.shift(1, fill_value=False) & (k < d.shift(1))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - r, k + r), cikis_long=cik)


class MacdKesisim(_Taban):
    """X005:366 / 421: MACD(12,26,9) çizgisi sinyali yukarı keserse long (421: ema_filtre verilirse yalnız kapanış > EMA(filtre)
    iken); MACD sinyalin altına inince (aşağı kesişim) kapat. Stop kaynakta yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "ema_filtre": None, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        m = g.macd(k, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        gir = _yukari(m["macd"], m["sinyal"])
        if p["ema_filtre"]:
            gir = gir & (k > g.ema(k, int(p["ema_filtre"])))
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - r, k + r), cikis_long=_asagi(m["macd"], m["sinyal"]))


class SmaBantKaynak(_Taban):
    """X005:367 ve 395#1..10 (T21 VMA bant kuralı): kısa MA (s; s=1 kapanış) uzun MA'yı (l) b bandı kadar AŞINCA long
    (durum); kısa MA uzun MA'nın b bandı kadar ALTINA inince çık; bant içinde pozisyon korunur. Basit MA, çarpımsal bant.
    Uyarlama: kaldıraç/faiz yok, kaynak JSE endeksi yerine kripto13; stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"s": 1, "l": 50, "b": 0.0, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        s, l, b = int(p["s"]), int(p["l"]), float(p["b"])
        kisa = k if s == 1 else g.sma(k, s)
        uzun = g.sma(k, l)
        r = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, kisa > uzun * (1 + b), False, k - r, k + r),
                     cikis_long=kisa < uzun * (1 - b))


class Rsi2HedefTepe(_Taban):
    """X005:371: RSI(2) < 25 iken kapanışta al (durum); hedef = sinyal anındaki son 2 mumun (sinyal mumu dahil) en yüksek
    tepesi (fiyat ona ulaşınca çık). Stop yok -> ATR(14)x3 (uyarlama). Alternatif çıkışlar uygulanmadı."""
    varsayilan_parametreler = {"rsi_n": 2, "esik": 25, "tepe_n": 2, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        n = int(p["tepe_n"])
        hedef = mumlar["yuksek"].rolling(n, min_periods=n).max()
        risk = _atr_riski(mumlar, p)
        return cerceve(mumlar, r < float(p["esik"]), False, k - risk, k + risk, hedef_l=hedef)


class RsiEsikAlSat(_Taban):
    """X005:372, 375, 411: RSI(n) < rsi_al iken (pozisyonsuzsa) kapanışta sinyal, sonraki açılışta long; RSI > rsi_cik -> kapat.
    rsi_tipi 'wilder' ya da 'basit' (375: yukarı/aşağı SMA). Stop yok -> ATR(14)x3 (uyarlama). Portföy ayarları uygulanmaz."""
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30, "rsi_cik": 70, "rsi_tipi": "wilder", "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        n = int(p["rsi_n"])
        r = _rsi_basit(k, n) if p["rsi_tipi"] == "basit" else g.rsi(k, n)
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, r < float(p["rsi_al"]), False, k - risk, k + risk),
                     cikis_long=r > float(p["rsi_cik"]))


class Rsi2KesisimHedefZaman(_Taban):
    """X005:373: RSI(2) (Wilder) rsi_esik seviyesinin altına KESİŞİNCE (önceki >= eşik, şimdi < eşik) long. Çıkış (kapanış bazlı):
    kapanış >= önceki mumda hesaplanan hedef limit = max(son 2 mumun tepesi) + 2xATR(15) (her mum güncellenir) ya da giriş
    sonrası 5. mum (zaman çıkışı). Zarar stopu kaynakta yok -> ATR(14)x3 felaket stopu (uyarlama). Varyant: eşik 20 (tez) / 25 (Pine)."""
    varsayilan_parametreler = {"rsi_n": 2, "rsi_esik": 20, "tepe_n": 2, "hedef_atr_n": 15, "hedef_atr_k": 2.0,
                               "atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=5)

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, h, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        r = g.rsi(k, int(p["rsi_n"]))
        n = int(p["tepe_n"])
        seviye = (h.rolling(n, min_periods=n).max()
                  + float(p["hedef_atr_k"]) * g.atr(h, d, k, int(p["hedef_atr_n"])))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _seviye_asagi(r, float(p["rsi_esik"])), False, k - risk, k + risk),
                     cikis_long=(k >= seviye.shift(1)))


class Rsi2Sma200Ortalama(_Taban):
    """X005:374: RSI(2) < 10 ve kapanış > SMA(200) ve SMA(RSI(2),4) < 30 (durum) -> long; kapanış > SMA(5) -> kapat.
    Hacim süzgeci yok (mevcut Rsi2Sma200Hacim'den farklı). Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"rsi_n": 2, "rsi_esik": 10, "sma_hizli": 5, "sma_yavas": 200, "rsi_ma_n": 4,
                               "rsi_ma_esik": 30, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        gir = ((r < float(p["rsi_esik"])) & (k > g.sma(k, int(p["sma_yavas"])))
               & (g.sma(r, int(p["rsi_ma_n"])) < float(p["rsi_ma_esik"])))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - risk, k + risk), cikis_long=k > g.sma(k, int(p["sma_hizli"])))


class Rsi15SonTepeHedef(_Taban):
    """X005:379: RSI(15) < 30 iken kapanışta al (durum); hedef = sinyal anındaki son 15 mumun en yüksek fiyatı (sinyal mumu dahil;
    açılış hedefin üstündeyse açılışta çıkış motor kuralıdır). Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"rsi_n": 15, "esik": 30, "tepe_n": 15, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        n = int(p["tepe_n"])
        hedef = mumlar["yuksek"].rolling(n, min_periods=n).max()
        risk = _atr_riski(mumlar, p)
        return cerceve(mumlar, r < float(p["esik"]), False, k - risk, k + risk, hedef_l=hedef)


class StokastikKesisim(_Taban):
    """X005:384: ham Stokastik %K(50) (yumuşatmasız) 20'yi yukarı keserse al; 80'i aşağı keserse sat. Stop yok -> ATR(14)x3 (uyarlama).
    Çıkış kuralı kaynakta metinden çıkarım."""
    varsayilan_parametreler = {"k_n": 50, "alt": 20, "ust": 80, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        sk = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], k, int(p["k_n"]), 1)["k"]
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, _seviye_yukari(sk, float(p["alt"])), False, k - risk, k + risk),
                     cikis_long=_seviye_asagi(sk, float(p["ust"])))


class EmaRsiTrendIki(_Taban):
    """X005:390: EMA20 > EMA50 ve RSI14 > 50 -> long (long değilse al); EMA20 < EMA50 ve RSI14 < 50 -> short; pozisyon ters koşul
    oluşana kadar korunur (long, short koşulunda kapanır; short, long koşulunda). Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"ema_h": 20, "ema_y": 50, "rsi_n": 14, "rsi_esik": 50, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        eh, ey = g.ema(k, int(p["ema_h"])), g.ema(k, int(p["ema_y"]))
        r = g.rsi(k, int(p["rsi_n"]))
        e = float(p["rsi_esik"])
        lk, sk = (eh > ey) & (r > e), (eh < ey) & (r < e)
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, lk, sk, k - risk, k + risk), cikis_long=sk, cikis_short=lk)


class EmaKesisimVeyaRsi(_Taban):
    """X005:391: giriş EMA20 EMA50'yi yukarı keserse VEYA RSI14 < 30; çıkış EMA20 EMA50'yi aşağı keserse VEYA RSI14 > 70.
    Kaynağın güven skorları ikili sinyal olarak okundu (emin_degil). Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"ema_h": 20, "ema_y": 50, "rsi_n": 14, "rsi_alt": 30, "rsi_ust": 70,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        eh, ey = g.ema(k, int(p["ema_h"])), g.ema(k, int(p["ema_y"]))
        r = g.rsi(k, int(p["rsi_n"]))
        gir = _yukari(eh, ey) | (r < float(p["rsi_alt"]))
        cik = _asagi(eh, ey) | (r > float(p["rsi_ust"]))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - risk, k + risk), cikis_long=cik)


class SmaKesisimLong(_Taban):
    """X005:393 ve 394: SMA(hizli) SMA(yavas)'i yukarı keserse long; aşağı keserse kapat. 393: stop yok -> ATR(14)x3 (uyarlama).
    394: sl_yuzde/tp_yuzde verilirse stop = kapanışın %sl altı, hedef = kapanışın %tp üstü (kaynak stopu; ATR uyarlaması yok).
    Günlük kayıp tavanı motor kill'e bırakıldı."""
    varsayilan_parametreler = {"hizli": 9, "yavas": 21, "sl_yuzde": None, "tp_yuzde": None, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        sh, sy = g.sma(k, int(p["hizli"])), g.sma(k, int(p["yavas"]))
        gir, cik = _yukari(sh, sy), _asagi(sh, sy)
        if p["sl_yuzde"]:
            stop = k * (1 - float(p["sl_yuzde"]) / 100.0)
            hedef = k * (1 + float(p["tp_yuzde"]) / 100.0) if p["tp_yuzde"] else None
            return _ekle(cerceve(mumlar, gir, False, stop, k, hedef_l=hedef), cikis_long=cik)
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, gir, False, k - risk, k + risk), cikis_long=cik)


class DonchianRvolIz(_Taban):
    """X005:397: kapanış > önceki 55 barın en yüksek tepesi ve hacim / ort(hacim, önceki 20 bar) >= 2,5 ve SMA20 > SMA50 -> long.
    Çıkış (kapanış bazlı): kapanış <= (giriş sonrası en yüksek tepe) - 3xATR(14) (hedef yok). Başlangıç stopu = kapanış - 3xATR(14).
    Uyarlama (nedensel yaklaşım): motor pozisyon durumunu strateji görmez; "giriş mumu" sinyal serisinden türetilir = en son giriş
    sinyali mumu s; zirve = s'den SONRAKİ mumların (s hariç) en yüksek tepesi, her mumda `cikis_long` = kapanış <= zirve - 3xATR(t).
    Pozisyon açıkken yeni giriş sinyali gelirse referans o muma kayar (zirve sıfırlanır) ve stop-out sonrası referans bayatlayabilir;
    gerçek dolum durumu bilinmediği için bu bir yaklaşımdır. Turnover filtresi kripto13'te etkisiz, uygulanmadı."""
    varsayilan_parametreler = {"kanal": 55, "rvol_n": 20, "rvol_min": 2.5, "sma_h": 20, "sma_y": 50,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, hc = mumlar["kapanis"], mumlar["hacim"]
        kanal = donchian_kanal(mumlar["yuksek"], mumlar["dusuk"], int(p["kanal"]))["ust"]
        n = int(p["rvol_n"])
        rvol = hc / hc.shift(1).rolling(n, min_periods=n).mean()
        gir = ((k > kanal) & (rvol >= float(p["rvol_min"]))
               & (g.sma(k, int(p["sma_h"])) > g.sma(k, int(p["sma_y"])))).fillna(False)
        risk = _atr_riski(mumlar, p)
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_n"])).to_numpy(float)
        yuk, kap, girv = mumlar["yuksek"].to_numpy(float), k.to_numpy(float), gir.to_numpy(bool)
        cik = np.zeros(len(k), bool)
        zirve, var = -np.inf, False
        for t in range(len(k)):
            if var:
                zirve = max(zirve, yuk[t])
                cik[t] = bool(kap[t] <= zirve - float(p["atr_k"]) * atr[t])
            if girv[t]:
                var, zirve = True, -np.inf
        return _ekle(cerceve(mumlar, gir, False, k - risk, k + risk), cikis_long=cik)


class Rsi2Ema200Iki(_Taban):
    """X005:405: kapanış > EMA(200) ve RSI(2) < esik_long -> long; kapanış < EMA(200) ve RSI(2) > esik_short -> short (sonraki
    açılış). Çıkış: long kapanış > SMA(5); short kapanış < SMA(5). Stop = sinyal mumunun dibi (long) / tepesi (short), tampon 0.
    Varyantlar: (10, 90) ve (5, 95); TF 1d ve 4h. Sabit R:R çıkışları uygulanmadı."""
    varsayilan_parametreler = {"ema_n": 200, "rsi_n": 2, "esik_long": 10, "esik_short": 90, "sma_cikis": 5}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ema = g.ema(k, int(p["ema_n"]))
        r = g.rsi(k, int(p["rsi_n"]))
        sma = g.sma(k, int(p["sma_cikis"]))
        return _ekle(cerceve(mumlar, (k > ema) & (r < float(p["esik_long"])),
                             (k < ema) & (r > float(p["esik_short"])), mumlar["dusuk"], mumlar["yuksek"]),
                     cikis_long=k > sma, cikis_short=k < sma)


class BantOrtalamayaDonus(_Taban):
    """X005:406 ve 417: MA(n) +/- std_carpan x std (pencere = std_pencere, ddof=0). Kapanış alt bandın altındaysa long, üst bandın
    üstündeyse short (durum; kapanışta sinyal, sonraki açılış); kapanış MA'ya dönünce kapat (long: kapanış >= MA; short: <= MA).
    Stop yok -> ATR(14)x3 (uyarlama). 406: SMA/EMA 20/50 dört varyant; 417: SMA20, 2σ (Bollinger)."""
    varsayilan_parametreler = {"ma_tipi": "SMA", "n": 20, "std_carpan": 1.0, "std_pencere": 20, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        orta = _ma(k, int(p["n"]), p["ma_tipi"])
        w = int(p["std_pencere"])
        std = k.rolling(w, min_periods=w).std(ddof=0) * float(p["std_carpan"])
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, k < orta - std, k > orta + std, k - risk, k + risk),
                     cikis_long=k >= orta, cikis_short=k <= orta)


class BbAltAlOrtaUst(_Taban):
    """X005:407: kapanış <= alt Bollinger(20,2) -> long; kapanış orta bandı aşağıdan yukarı keserse ya da kapanış >= üst banda eşitse
    sat. Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, k <= bb["alt"], False, k - risk, k + risk),
                     cikis_long=_yukari(k, bb["orta"]) | (k >= bb["ust"]))


class RsiHacimSmaZaman(_Taban):
    """X005:408: giriş (kapanışta): [RSI(14) <= 30 ve kapanış >= SMA20 ve kapanış >= SMA50 ve hacim/ort(hacim önceki 20 bar) >= 1,5]
    VEYA [RSI(14) <= 40 ve kapanış >= SMA20] (iki kol birlikte uygulanır). Çıkış: 20 mum tutulunca (zaman çıkışı).
    Stop yok -> ATR(14)x3 felaket stopu (uyarlama)."""
    varsayilan_parametreler = {"rsi_n": 14, "rsi_a": 30, "rsi_b": 40, "sma_h": 20, "sma_y": 50, "rvol_n": 20,
                               "rvol_min": 1.5, "atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=20)

    def sinyaller(self, mumlar):
        p = self.parametreler
        k, hc = mumlar["kapanis"], mumlar["hacim"]
        r = g.rsi(k, int(p["rsi_n"]))
        s20, s50 = g.sma(k, int(p["sma_h"])), g.sma(k, int(p["sma_y"]))
        n = int(p["rvol_n"])
        rvol = hc / hc.shift(1).rolling(n, min_periods=n).mean()
        kol1 = (r <= float(p["rsi_a"])) & (k >= s20) & (k >= s50) & (rvol >= float(p["rvol_min"]))
        kol2 = (r <= float(p["rsi_b"])) & (k >= s20)
        risk = _atr_riski(mumlar, p)
        return cerceve(mumlar, kol1 | kol2, False, k - risk, k + risk)


class RsiYukariKesisimTp(_Taban):
    """X005:410: RSI(14) 30'un altından üstüne çıkınca long; çıkış RSI(14) 70'in üstünden altına inince ya da +%6 (hedef); stop giriş
    (sinyal kapanışı) fiyatının %3 altı (kaynak stopu; ATR uyarlaması yok). Günlük %5 zarar tavanı motor kill'e bırakıldı."""
    varsayilan_parametreler = {"rsi_n": 14, "alt": 30, "ust": 70, "sl_yuzde": 3.0, "tp_yuzde": 6.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        return _ekle(cerceve(mumlar, _seviye_yukari(r, float(p["alt"])), False,
                             k * (1 - float(p["sl_yuzde"]) / 100.0), k,
                             hedef_l=k * (1 + float(p["tp_yuzde"]) / 100.0)),
                     cikis_long=_seviye_asagi(r, float(p["ust"])))


class CdcActionZone(_Taban):
    """X005:418: CDC ActionZone V3: EMA12/EMA26 (kapanış). Yeşil = EMA12 > EMA26 ve kapanış > EMA12; kırmızı = EMA12 < EMA26 ve
    kapanış < EMA12. Long giriş = ilk yeşil bar (önceki bar yeşil değil); çıkış = kırmızı bar. Yalnız long. Stop yok -> ATR(14)x3."""
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        eh, ey = g.ema(k, int(p["hizli"])), g.ema(k, int(p["yavas"]))
        yesil = ((eh > ey) & (k > eh)).fillna(False)
        kirmizi = ((eh < ey) & (k < eh)).fillna(False)
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, yesil & ~yesil.shift(1, fill_value=False), False, k - risk, k + risk),
                     cikis_long=kirmizi)


class AySonuEma(_Taban):
    """X005:427: ay sonu kapanışında kapanış > EMA(150) ise long (değilse flat); pozisyon yalnız ay sonunda güncellenir: ay sonu
    mumunda kapanış > EMA ise giriş, <= EMA ise çıkış; ay içinde başka sinyal yok. Ay sonu mumu = mumun açılış + 1 gün
    takvimde ay değiştiriyorsa (takvimden, sonraki mum gerekmez; 1d içindir). Stop yok -> ATR(14)x3 (uyarlama)."""
    varsayilan_parametreler = {"ema_n": 150, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, mumlar):
        p = self.parametreler
        k = mumlar["kapanis"]
        ay_sonu = pd.Series((mumlar.index + pd.Timedelta(days=1)).month != mumlar.index.month, index=mumlar.index)
        ema = g.ema(k, int(p["ema_n"]))
        risk = _atr_riski(mumlar, p)
        return _ekle(cerceve(mumlar, ay_sonu & (k > ema), False, k - risk, k + risk),
                     cikis_long=ay_sonu & (k <= ema))


# ---------------------------------------------------------------- satır -> sınıf kaydı
SINIFLAR: dict = {}
VARYANTLAR: list = []
KODLANAMADI: list = []

_ATR = {"atr_n": 14, "atr_k": 3.0}


def _satir(kaynak_id, taban, ad, varyantlar, tflar, ozet):
    """Bir kaynak satırı için alt sınıf üretir (varsayılan = ilk varyant) ve VARYANTLAR'a her varyant x TF kaydı ekler.
    Kayıt numarası #v1.. varyant-ana, TF-ikincil sırayla verilir."""
    ilk = varyantlar[0]
    govde = {"__doc__": f"{kaynak_id}: {ozet}\n\n    Taban kural: {taban.__name__}.", "ad": ad,
             "varsayilan_parametreler": {**taban.varsayilan_parametreler, **ilk}}
    sinif = type("S" + kaynak_id.split(":")[-1].replace("#", "_"), (taban,), govde)
    SINIFLAR[ad] = sinif
    no = 0
    for v in varyantlar:
        for tf in tflar:
            no += 1
            VARYANTLAR.append({"kimlik": f"{kaynak_id}#v{no}", "sinif": ad,
                               "parametreler": {**taban.varsayilan_parametreler, **v}, "tf": tf})
    return sinif


_BOS = [{}]
_4H1D = ["4h", "1d"]

S0357 = _satir("HAM:X005:357", Bb038EmaKesisim, "kapanis__bb038-ema80-s0357", _BOS, _4H1D,
               "BB(20, 0,38σ) kesişim + EMA80 süzgeci, iki yön, stop son 7 bar dip/tepe, hedef 1,6R (K6: TF 4h|1d).")
S0362 = _satir("HAM:X005:362", EmaAcilisStopEmir, "kapanis__ema9-stopemir-s0362", [dict(_ATR)], _4H1D,
               "EMA9 sinyal mumu + sonraki mum kapanışı sinyal mumu tepesini aşınca long (stop-emir kapanışa uyarlandı).")
S0366 = _satir("HAM:X005:366", MacdKesisim, "kapanis__macd-s0366", _BOS, _4H1D, "MACD(12,26,9) kesişim long-only.")
S0367 = _satir("HAM:X005:367", SmaBantKaynak, "kapanis__vma-bant-s0367", [{"s": 5, "l": 50, "b": 0.01}], ["1w"],
               "SMA5 / SMA50 x 1,01 bant kuralı, haftalık (1w yeniden örnekleme koşu tarafında).")
S0371 = _satir("HAM:X005:371", Rsi2HedefTepe, "kapanis__rsi2-tepe-s0371", _BOS, ["1d"],
               "RSI(2) < 25 al, son 2 mum tepesi hedef.")
S0372 = _satir("HAM:X005:372", RsiEsikAlSat, "kapanis__rsi2-15-72-s0372", [{"rsi_n": 2, "rsi_al": 15, "rsi_cik": 72}],
               ["1h", "1d"], "RSI(2) < 15 al, > 72 kapat (aralıklar orta nokta: ek 3).")
S0373 = _satir("HAM:X005:373", Rsi2KesisimHedefZaman, "kapanis__rsi2-kesisim-s0373",
               [{"rsi_esik": 20}, {"rsi_esik": 25}], ["1d"],
               "RSI(2) eşik altına kesişince long; hedef max2tepe+2ATR15 ya da 5 mum.")
S0374 = _satir("HAM:X005:374", Rsi2Sma200Ortalama, "kapanis__rsi2-sma200-s0374", _BOS, ["1d"],
               "RSI2<10, kapanış>SMA200, SMA(RSI2,4)<30; çıkış kapanış>SMA5.")
S0375 = _satir("HAM:X005:375", RsiEsikAlSat, "kapanis__rsi14basit-s0375",
               [{"rsi_n": 14, "rsi_al": 25, "rsi_cik": 75, "rsi_tipi": "basit"}], ["1d"],
               "Basit ortalamalı RSI(14) < 25 al, > 75 çık.")
S0379 = _satir("HAM:X005:379", Rsi15SonTepeHedef, "kapanis__rsi15-tepe15-s0379", _BOS, ["1d"],
               "RSI(15) < 30 al, 15 günün en yüksek fiyatı hedef.")
S0384 = _satir("HAM:X005:384", StokastikKesisim, "kapanis__stok50-s0384", _BOS, ["1w"],
               "Stokastik %K(50) 20 yukarı / 80 aşağı kesişim, haftalık.")
S0390 = _satir("HAM:X005:390", EmaRsiTrendIki, "kapanis__ema-rsi-trend-s0390", _BOS, ["1d"],
               "EMA20/50 + RSI14>50 / <50 iki yön, ters koşulda çık.")
S0391 = _satir("HAM:X005:391", EmaKesisimVeyaRsi, "kapanis__ema-veya-rsi-s0391", _BOS, ["1d"],
               "EMA20/50 kesişim VEYA RSI14<30 giriş; kesişim VEYA RSI14>70 çıkış.")
S0393 = _satir("HAM:X005:393", SmaKesisimLong, "kapanis__sma-kesisim-s0393", _BOS, _4H1D, "SMA9/21 kesişim long-only.")
S0394 = _satir("HAM:X005:394", SmaKesisimLong, "kapanis__sma-kesisim-tp-s0394",
               [{"sl_yuzde": 3.0, "tp_yuzde": 6.0}], ["1h"], "SMA9/21 kesişim, stop %3, hedef %6.")

_VMA = {1: (1, 50, 0.0), 2: (1, 50, 0.01), 3: (1, 150, 0.0), 4: (1, 150, 0.01), 5: (5, 150, 0.0),
        6: (5, 150, 0.01), 7: (1, 200, 0.0), 8: (1, 200, 0.01), 9: (2, 200, 0.0), 10: (2, 200, 0.01)}
for _i, (_s, _l, _b) in _VMA.items():
    globals()[f"S0395_{_i}"] = _satir(
        f"HAM:X005:395#{_i}", SmaBantKaynak, f"kapanis__vma-bant-s0395-{_i}", [{"s": _s, "l": _l, "b": _b}], ["1d"],
        f"VMA bant kuralı S={_s}, L={_l}, B={_b} (T21 kural {_i}).")

S0397 = _satir("HAM:X005:397", DonchianRvolIz, "kapanis__donchian55-rvol-s0397", _BOS, ["1d"],
               "55 bar kırılım + göreli hacim >= 2,5 + SMA20>SMA50; 3xATR kapanış bazlı iz süren çıkış (cikis_long).")
S0405 = _satir("HAM:X005:405", Rsi2Ema200Iki, "kapanis__rsi2-ema200-iki-s0405",
               [{"esik_long": 10, "esik_short": 90}, {"esik_long": 5, "esik_short": 95}], _4H1D,
               "EMA200 yönünde RSI(2) aşırılığı iki yön; çıkış SMA5; stop sinyal mumu dip/tepe.")
S0406 = _satir("HAM:X005:406", BantOrtalamayaDonus, "kapanis__bant-donus-s0406",
               [{"ma_tipi": "SMA", "n": 20, "std_pencere": 20}, {"ma_tipi": "SMA", "n": 50, "std_pencere": 50},
                {"ma_tipi": "EMA", "n": 20, "std_pencere": 20}, {"ma_tipi": "EMA", "n": 50, "std_pencere": 50}],
               _4H1D, "MA +/- 1 std bandından ortalamaya dönüş, iki yön, 4 varyant.")
S0407 = _satir("HAM:X005:407", BbAltAlOrtaUst, "kapanis__bb-alt-al-s0407", _BOS, ["1d"],
               "BB(20,2) alt bantta al; orta bant yukarı kesişimi ya da üst bantta sat.")
S0408 = _satir("HAM:X005:408", RsiHacimSmaZaman, "kapanis__rsi-hacim-sma-s0408", _BOS, ["1d"],
               "RSI14 <= 30/40 + SMA/hacim süzgeci, 20 mum tut.")
S0410 = _satir("HAM:X005:410", RsiYukariKesisimTp, "kapanis__rsi-kesisim-tp-s0410", _BOS, ["1h"],
               "RSI14 30 yukarı kesişim, 70 aşağı kesişim ya da +%6; stop %3.")
S0411 = _satir("HAM:X005:411", RsiEsikAlSat, "kapanis__rsi14-30-70-s0411", _BOS, ["15m"],
               "RSI(14) < 30 al, > 70 kapat, 15m.")
S0417 = _satir("HAM:X005:417", BantOrtalamayaDonus, "kapanis__bb-donus-s0417",
               [{"ma_tipi": "SMA", "n": 20, "std_carpan": 2.0, "std_pencere": 20}], _4H1D,
               "Bollinger(20, 2σ) dışında kapanışta giriş, orta banda dönünce çıkış, iki yön.")
S0418 = _satir("HAM:X005:418", CdcActionZone, "kapanis__cdc-actionzone-s0418", _BOS, ["1d"],
               "CDC ActionZone V3 yeşil bar giriş, kırmızı bar çıkış.")
S0421 = _satir("HAM:X005:421", MacdKesisim, "kapanis__macd-ema100-s0421",
               [{"ema_filtre": None}, {"ema_filtre": 100}], _4H1D, "MACD kesişim; v2: yalnız kapanış > EMA100.")
S0427 = _satir("HAM:X005:427", AySonuEma, "kapanis__ay-sonu-ema150-s0427", _BOS, ["1d"],
               "Ay sonu kapanışı > EMA150 ise long, değilse flat.")

KODLANAMADI = [
    {"kimlik": "HAM:X005:400",
     "neden": "min. 20 / maks. 40 gün tutma (ters kesişim 20. günden önce yok sayılır) ve 20 günden sonra %7,5 zarar çıkışı: "
              "pozisyon yaşına bağlı çıkış/stop motorda ifade edilemiyor (zaman_cikisi yalnız maks. süreyi verir)."},
    {"kimlik": "HAM:X005:401",
     "neden": "min. 20 / maks. 40 gün tutma ve 20 günden sonra %7,5 zarar çıkışı (400 ile aynı çerçeve): pozisyon yaşına bağlı "
              "çıkış motorda ifade edilemiyor."},
    {"kimlik": "HAM:X005:416",
     "neden": "min. 20 / maks. 40 gün tutma ve 20 günden sonra %7,5 zarar çıkışı (400 ile aynı çerçeve): pozisyon yaşına bağlı "
              "çıkış motorda ifade edilemiyor."},
    {"kimlik": "HAM:X005:419",
     "neden": "stop-and-reverse; min. 8 bar tutma sonrası ters sinyal, pozisyon açıkken her barda kurulan reverse bayrakları, "
              "max(önceki stop, EMA-2xATR) yukarı kayan pozisyona bağlı stop ve overBand istisnası: motor durumu ifade edemiyor "
              "(lider onayı gerekir)."},
]
