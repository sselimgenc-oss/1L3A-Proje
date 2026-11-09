"""D10-E — kodlama kuyruğundaki 14 yeni aileden 13'ünün (CleanTradeQuantum dahil) KODU. KOD KOPYALANMADI: kitap kartları, Pine
betiği ve kural özetleri VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__`. Hepsi nedensel (lookahead yok).

Ortak uyarlamalar (hepsi sınıf docstring'lerinde de belirtilir)
  * Kartlardaki pip/puan/tik stopları ve hedefleri enstrümandan bağımsız olsun diye ATR çarpanına çevrildi (VARSAYIM).
  * Stopu olmayan kartlara stop_atr_k x ATR felaket stopu eklendi (VARSAYIM; kitapta stop yok).
  * Bar-içi stop emirleri ("yükseğin 1 tik üstüne buy-stop") yok: sinyal bar KAPANIŞINDA, dolum sonraki açılışta (motor).
  * "Yeşile döndü / ok belirdi" gibi görsel olaylar ölçülebilir tanıma çevrildi (kesişim, eğim dönüşü, durum geçişi).
  * Topluluk göstergeleri (UT Bot, HalfTrend, WaveTrend, Trend Magic, NSM, KDJ) kitapta tanımlı değil: UT Bot formülü
    arsiv/strateji-sg/tv/pine/JeRCEqWU.pine içindeki `utTrailingStop` ile aynıdır; HalfTrend d8_atlanan_a._halftrend,
    WaveTrend _gosterge_d3.dalga_trend, KDJ _gosterge_d9.kdj ile ortak; Trend Magic, BB-MACD ve NSM yaygın bilinen tanımdan
    (docstring'lerinde yazılı).

dis__carter-onayli-trend, dis__hma-osilator, dis__ma-kirilim-macd-yeni-pozitif, dis__carter-cci-macd, dis__anti-stokastik,
dis__carter-bb-disi-sinyal-mumu, dis__rsi-ma-kesisim, dis__sapan-geri-cekilme, dis__utbot-kdj, dis__wavetrend-halftrend,
dis__saat-donus-scalp, dis__nsm-macd, dis__trend-magic, dis__tv-cleantradequantum
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import seans_kimligi
from motor.strateji.dis._gosterge_d1 import hma, kur, laguerre, wma
from motor.strateji.dis._gosterge_d3 import dalga_trend, mfi
from motor.strateji.dis._gosterge_d5 import kama
from motor.strateji.dis._gosterge_d9 import ardisik_say, kdj, r_hedefi
from motor.strateji.dis.d8_atlanan_a import _halftrend
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, gecis, yukari_kesis
from motor.strateji.temel import Strateji

from ._gosterge_d10e import (
    bb_macd_renk, mum_suresi_dk, nsm_macd, ob_bolgeleri, trend_magic, ut_bot, vwma, yavas_stok)

NY = "America/New_York"


def _bos(index):
    return pd.Series(False, index=index)


def _b(x, index):
    if x is None:
        return _bos(index)
    return pd.Series(x, index=index).fillna(False).astype(bool)


def _alt_ust_stop(m, n: int):
    """Son n mumun (bu mum dahil) en düşüğü / en yükseği: salınım stopu adayı."""
    return m["dusuk"].rolling(n, min_periods=n).min(), m["yuksek"].rolling(n, min_periods=n).max()


class _Taban(Strateji):
    """Ortak iskelet. Alt sınıf `kosullar(m)` yazar:
    {"long","short" (giriş olayı), "cikis_long","cikis_short" (isteğe bağlı), "stop_l","stop_s" (isteğe bağlı salınım stopu)}.
    Stop = ATR stopu (kapanış -/+ stop_atr_k x ATR); özel salınım stopu varsa ondan en az `min_risk_atr` x ATR uzakta olacak
    şekilde kullanılır (çok yakın stop = aşırı büyük pozisyon). hedef_r > 0: hedef = R katı (kapanış +/- r x risk)."""
    _OZEL_STOP = False

    def cikis_var_mi(self) -> bool:
        return True

    def kosullar(self, m: pd.DataFrame) -> dict:
        raise NotImplementedError

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = m.index
        k = self.kosullar(m)
        kap = m["kapanis"]
        a = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_periyot"]))
        stop_l, stop_s = kap - p["stop_atr_k"] * a, kap + p["stop_atr_k"] * a
        if self._OZEL_STOP and k.get("stop_l") is not None:
            mr = float(p.get("min_risk_atr", 0.5))
            stop_l = np.minimum(k["stop_l"], kap - mr * a)
            stop_s = np.maximum(k["stop_s"], kap + mr * a)
        yon = p["yonler"]
        long_ok = _b(k.get("long"), idx) if yon in ("long", "ls") else _bos(idx)
        short_ok = _b(k.get("short"), idx) if yon in ("short", "ls") else _bos(idx)
        zc = int(p.get("zaman_cikisi", 0)) or None
        out = kur(m, long_ok, short_ok, stop_l, stop_s, cikis_l=_b(k.get("cikis_long"), idx),
                  cikis_s=_b(k.get("cikis_short"), idx), zaman_cikisi=zc)
        return r_hedefi(out, kap, float(p.get("hedef_r", 0.0)))


ORTAK = {"yonler": "ls", "atr_periyot": 14, "stop_atr_k": 2.0, "hedef_r": 1.5, "zaman_cikisi": 0}


# =============================================================================== 1. Carter onaylı trend
class CarterOnayliTrend(_Taban):
    """dis__carter-onayli-trend (scalp, 5m) — Carter "5 dakikalık sistemler" 1, 12, 14, 16, 17, 19 (6 kart, aynı fikir:
    trend + osilatör + MACD/SAR onayı; varyantlar `varyant` parametresi). Giriş = tüm onay koşullarının AYNI ANDA doğru olduğu
    ilk mum (durum geçişi; kitap "hepsi sağlanınca" der, geçiş anı belirsiz -> VARSAYIM). Çıkış varyanta göre ters kural.
      stok_macd_ema5  (S1): EMA5(kapanış)'ın EMA5(açılış)'ı yukarı kesmesi (tetik) + yavaş stokastik(5,3,3) son 5 mumda 20'yi yukarı
                      kesmiş ve K<80 + MACD(12,26) çizgisi önceki mumdan yüksek + yükseliş mumu. Çıkış: ters EMA5 kesişimi.
      ema_laguerre    (S12): kapanış>EMA16>EMA48 ve Laguerre RSI(alfa=0.5, VARSAYIM) 0.8'i yukarı keser. Çıkış: kapanış<EMA16.
      wma_sma_rsi_macd(S14): WMA10>SMA20, yavaş stokastik(10,6,6) K>D, RSI28>50, MACD(24,52)>0. Çıkış: WMA10<SMA20.
      adx_psar_wma    (S16): WMA5>SMA11, PSAR altta (adım 0.02, maks 0.2; kitaptaki 0.1/0.01 alışılmadık -> VARSAYIM), DI+>DI-.
                      Çıkış: PSAR ters.
      ema_sar_macd_stok(S17): EMA3>EMA8, PSAR altta, MACD(12,26)>0, stokastik(10,15,15) K, D'yi yukarı keser. Çıkış: EMA3<EMA8.
                      (20 dönem standart sapma eşiği pip cinsinden olduğu için kodlanmadı.)
      psar_macd_ema   (S19): kapanış>EMA100, PSAR altta, MACD(64,128)>0. Çıkış: PSAR ters.
    Short hepsinde ayna. S11 (4s trend filtresi, 5/15dk) kodlanmadı. Stop/hedef: kartlarda pip/salınım; burada stop_atr_k x ATR ve
    hedef_r x R (VARSAYIM; kartlar 1:1 ile 1:0.5 arası)."""
    ad = "dis__carter-onayli-trend"
    stil = "scalp"
    VARYANTLAR = ("stok_macd_ema5", "ema_laguerre", "wma_sma_rsi_macd", "adx_psar_wma", "ema_sar_macd_stok", "psar_macd_ema")
    varsayilan_parametreler = {**ORTAK, "varyant": "ema_sar_macd_stok", "stok_pencere": 5, "hedef_r": 1.5}
    parametre_izgarasi = {"varyant": list(VARYANTLAR), "stop_atr_k": [1.5, 2.5], "hedef_r": [1.0, 2.0]}

    def kosullar(self, m):
        p = self.parametreler
        v = p["varyant"]
        if v not in self.VARYANTLAR:
            raise ValueError(f"Bilinmeyen varyant: {v!r}")
        y, d, c, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        if v == "stok_macd_ema5":
            e_c, e_o = g.ema(c, 5), g.ema(o, 5)
            st = yavas_stok(y, d, c, 5, 3, 3)["k"]
            ml = g.ema(c, 12) - g.ema(c, 26)
            w = int(p["stok_pencere"])
            yuk20 = yukari_kesis(st, 20.0).rolling(w, min_periods=1).max().astype(bool)
            asg80 = asagi_kesis(st, 80.0).rolling(w, min_periods=1).max().astype(bool)
            lg = yukari_kesis(e_c, e_o) & yuk20 & (st < 80) & (ml > ml.shift(1)) & (c > o)
            sh = asagi_kesis(e_c, e_o) & asg80 & (st > 20) & (ml < ml.shift(1)) & (c < o)
            return {"long": lg, "short": sh, "cikis_long": asagi_kesis(e_c, e_o), "cikis_short": yukari_kesis(e_c, e_o)}
        if v == "ema_laguerre":
            e16, e48 = g.ema(c, 16), g.ema(c, 48)
            lag = laguerre(c, 0.5)
            toplam = (lag["cu"] + lag["cd"]).where((lag["cu"] + lag["cd"]) > 0)
            lrsi = lag["cu"] / toplam
            lg = gecis((c > e16) & (e16 > e48) & (lrsi > 0.8))
            sh = gecis((c < e16) & (e16 < e48) & (lrsi < 0.2))
            return {"long": lg, "short": sh, "cikis_long": c < e16, "cikis_short": c > e16}
        if v == "wma_sma_rsi_macd":
            w10, s20 = wma(c, 10), g.sma(c, 20)
            st = yavas_stok(y, d, c, 10, 6, 6)
            r28 = g.rsi(c, 28)
            ml = g.ema(c, 24) - g.ema(c, 52)
            lg = gecis((w10 > s20) & (st["k"] > st["d"]) & (r28 > 50) & (ml > 0))
            sh = gecis((w10 < s20) & (st["k"] < st["d"]) & (r28 < 50) & (ml < 0))
            return {"long": lg, "short": sh, "cikis_long": w10 < s20, "cikis_short": w10 > s20}
        if v == "adx_psar_wma":
            w5, s11 = wma(c, 5), g.sma(c, 11)
            ps = g.psar(y, d, 0.02, 0.2)["yon"]
            dm = g.adx(y, d, c, 14)
            lg = gecis((w5 > s11) & (ps == 1) & (dm["arti_di"] > dm["eksi_di"]))
            sh = gecis((w5 < s11) & (ps == -1) & (dm["arti_di"] < dm["eksi_di"]))
            return {"long": lg, "short": sh, "cikis_long": ps == -1, "cikis_short": ps == 1}
        if v == "ema_sar_macd_stok":
            e3, e8 = g.ema(c, 3), g.ema(c, 8)
            ps = g.psar(y, d, 0.02, 0.2)["yon"]
            ml = g.ema(c, 12) - g.ema(c, 26)
            st = yavas_stok(y, d, c, 10, 15, 15)
            kd_yuk = yukari_kesis(st["k"], st["d"])
            kd_asg = asagi_kesis(st["k"], st["d"])
            lg = kd_yuk & (e3 > e8) & (ps == 1) & (ml > 0)
            sh = kd_asg & (e3 < e8) & (ps == -1) & (ml < 0)
            return {"long": lg, "short": sh, "cikis_long": e3 < e8, "cikis_short": e3 > e8}
        # psar_macd_ema
        e100 = g.ema(c, 100)
        ps = g.psar(y, d, 0.01, 0.2)["yon"]
        ml = g.ema(c, 64) - g.ema(c, 128)
        lg = gecis((c > e100) & (ps == 1) & (ml > 0))
        sh = gecis((c < e100) & (ps == -1) & (ml < 0))
        return {"long": lg, "short": sh, "cikis_long": ps == -1, "cikis_short": ps == 1}


# =============================================================================== 2. HMA + osilatör
class HmaOsilator(_Taban):
    """dis__hma-osilator (scalp, 5m) — Ratford "HMA(25)+RSI-BB", "Hull MA+Stokastik", Ferrazzi "MFI+HMA+200SMA" (3 kart).
    Ortak fikir: osilatör dönüşü + mumun Hull MA'nın doğru tarafında kapanması. `osilator` parametresi:
      rsi_bb: RSI(14) üzerine Bollinger(40, 1); RSI alt bandı yukarı keser + kapanış>HMA(25). Çıkış: kapanış<HMA veya RSI üst bandı
              aşağı keser. (Kart yalnız long; short ayna eklendi, yonler ile kapatılabilir.)
      stok:   Stokastik(14, K yumuşatma 6, D 3) K'sı D'yi 50'nin ALTINDA yukarı keser + kapanış>HMA(30). Çıkış: kapanış<HMA.
      mfi:    kapanış>SMA200 + MFI(21) 50'nin altında iken kendi SMA(18)'ini yukarı keser + kapanış>HMA(65). Çıkış: MFI SMA'nın
              altına geçer veya kapanış<HMA.
    hma_n=0: kartın periyodu (25/30/65); >0: hepsi için bu periyot. Short ayna. Kartlarda stop yok -> stop_atr_k x ATR (VARSAYIM);
    hedef yok, çıkış kural çıkışıdır (hedef_r=0). Kaynakta Hull'un 'renk' (eğim) koşulu: kapanışın HMA üstünde olması ile
    yaklaşıldı."""
    ad = "dis__hma-osilator"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "osilator": "rsi_bb", "hma_n": 0, "hedef_r": 0.0, "stop_atr_k": 2.0}
    parametre_izgarasi = {"osilator": ["rsi_bb", "stok", "mfi"], "hma_n": [0, 21, 50], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        o = p["osilator"]
        if o not in ("rsi_bb", "stok", "mfi"):
            raise ValueError(f"Bilinmeyen osilator: {o!r}")
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["hma_n"]) or {"rsi_bb": 25, "stok": 30, "mfi": 65}[o]
        h = hma(c, n)
        ust, alt = c > h, c < h
        if o == "rsi_bb":
            r = g.rsi(c, 14)
            ort = r.rolling(40, min_periods=40).mean()
            sd = r.rolling(40, min_periods=40).std(ddof=0)
            ub, lb = ort + sd, ort - sd
            return {"long": yukari_kesis(r, lb) & ust, "short": asagi_kesis(r, ub) & alt,
                    "cikis_long": alt | asagi_kesis(r, ub), "cikis_short": ust | yukari_kesis(r, lb)}
        if o == "stok":
            st = yavas_stok(y, d, c, 14, 6, 3)
            k, dd = st["k"], st["d"]
            return {"long": yukari_kesis(k, dd) & (k < 50) & ust, "short": asagi_kesis(k, dd) & (k > 50) & alt,
                    "cikis_long": alt, "cikis_short": ust}
        mf = mfi(y, d, c, m["hacim"], 21)
        ms = g.sma(mf, 18)
        s200 = g.sma(c, 200)
        return {"long": (c > s200) & yukari_kesis(mf, ms) & (mf < 50) & ust,
                "short": (c < s200) & asagi_kesis(mf, ms) & (mf > 50) & alt,
                "cikis_long": alt | (mf < ms), "cikis_short": ust | (mf > ms)}


# =============================================================================== 3. MA kırılımı + MACD yeni pozitif
class MaKirilimMacdYeniPozitif(_Taban):
    """dis__ma-kirilim-macd-yeni-pozitif (scalp ana; kuyrukta scalp/daytrade, kaynak 5m — Lien kartı daytrade) — Lien "momentum 20/100",
    Carter sistem 18 (EMA20+MACD) ve sistem 9 (EMA50/100+MACD). `varyant`:
      lien:        kapanış EMA20 ve SMA100'ün ikisinin de ALTINDAYKEN ikisini birden yukarı kırıp ikisinin `tampon_atr` x ATR üstünde
                   kapanır; MACD histogramı 5 mum içinde pozitife dönmüş.
      ema20:       kapanış EMA20'nin altındayken EMA20 + tampon üstüne çıkar; MACD(12,26) çizgisi 5 mum içinde pozitife geçmiş.
      ema50_100:   kapanış EMA50 ve EMA100 üstünde; EMA50 + tampon seviyesini yukarı keser; MACD çizgisi 5 mum içinde pozitife geçmiş.
    "MACD yeni pozitif" = MACD şimdi > 0 ve son `macd_pencere` mumdan en az birinde <= 0 idi. Tampon: kitapta 10-15 pip -> tampon_atr x ATR
    (VARSAYIM). Stop: son stop_n mumun dibi (short: zirvesi), en az 0.5 ATR uzaklıkta. Çıkış (kitapta): 1R'de pozisyonun yarısı
    kapanır ve stop başa baş çekilir (CikisAyarlari.kismi + basabas), kalan EMA(20 veya 50) -/+ tampon ile iz sürülür (kapanış bu seviyeyi
    ters geçerse çıkış). Short ayna. hedef_r=0 (hedef yok)."""
    ad = "dis__ma-kirilim-macd-yeni-pozitif"
    stil = "scalp"
    _OZEL_STOP = True
    varsayilan_parametreler = {**ORTAK, "varyant": "ema20", "tampon_atr": 0.3, "macd_pencere": 5, "stop_n": 5,
                               "min_risk_atr": 0.5, "hedef_r": 0.0}
    parametre_izgarasi = {"varyant": ["lien", "ema20", "ema50_100"], "stop_n": [3, 5, 8], "tampon_atr": [0.15, 0.3, 0.5]}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=1.0)

    def kosullar(self, m):
        p = self.parametreler
        v = p["varyant"]
        if v not in ("lien", "ema20", "ema50_100"):
            raise ValueError(f"Bilinmeyen varyant: {v!r}")
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, c, int(p["atr_periyot"]))
        t = float(p["tampon_atr"]) * a
        w = int(p["macd_pencere"]) + 1
        ml = g.ema(c, 12) - g.ema(c, 26)
        if v == "lien":
            e20, s100 = g.ema(c, 20), g.sma(c, 100)
            ma_ust = np.maximum(e20, s100)
            ma_alt = np.minimum(e20, s100)
            hist = g.macd(c, 12, 26, 9)["histogram"]
            yeni_poz = (hist > 0) & (hist.rolling(w, min_periods=w).min() <= 0)
            yeni_neg = (hist < 0) & (hist.rolling(w, min_periods=w).max() >= 0)
            asagida = (c.shift(1) <= ma_ust.shift(1))
            yukarida = (c.shift(1) >= ma_alt.shift(1))
            lg = asagida & (c > ma_ust + t) & yeni_poz
            sh = yukarida & (c < ma_alt - t) & yeni_neg
            iz = e20
        elif v == "ema20":
            iz = g.ema(c, 20)
            yeni_poz = (ml > 0) & (ml.rolling(w, min_periods=w).min() <= 0)
            yeni_neg = (ml < 0) & (ml.rolling(w, min_periods=w).max() >= 0)
            lg = yukari_kesis(c, iz + t) & yeni_poz
            sh = asagi_kesis(c, iz - t) & yeni_neg
        else:
            e50, e100 = g.ema(c, 50), g.ema(c, 100)
            iz = e50
            yeni_poz = (ml > 0) & (ml.rolling(w, min_periods=w).min() <= 0)
            yeni_neg = (ml < 0) & (ml.rolling(w, min_periods=w).max() >= 0)
            lg = yukari_kesis(c, e50 + t) & (c > e100) & yeni_poz
            sh = asagi_kesis(c, e50 - t) & (c < e100) & yeni_neg
        sl, ss = _alt_ust_stop(m, int(p["stop_n"]))
        return {"long": lg, "short": sh, "stop_l": sl, "stop_s": ss,
                "cikis_long": c < iz - t, "cikis_short": c > iz + t}


# =============================================================================== 4. Carter CCI + MACD
class CarterCciMacd(_Taban):
    """dis__carter-cci-macd (scalp, 5m) — Carter sistem 10 (EMA40/80 + CCI21) ve sistem 13 (CCI14 + MACD histogram). `varyant`:
      ema_cci0:    EMA40>EMA80 iken CCI(21) 0'ı yukarı keser -> long; EMA40<EMA80 iken 0'ı aşağı keser -> short.
      cci100_macd: CCI(14) +100'ü aşağıdan yukarı keser, MACD çubuğu (kitapta 'histogram' = MACD çizgisi) önceki mumdan yüksek ve
                   MACD sinyal çizgisi (kitapta 'hareketli ortalama') bu çubuğun altında (MACD>sinyal) -> long. Short: CCI -100'ü
                   yukarıdan aşağı keser, MACD çubuğu önceki mumdan düşük, MACD<sinyal.
    Stop 10-15 pip, hedef 7-15 pip -> stop_atr_k x ATR ve hedef_r x R (VARSAYIM). Kural çıkışı yok (kitap sabit stop/hedef)."""
    ad = "dis__carter-cci-macd"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "varyant": "ema_cci0", "stop_atr_k": 1.5, "hedef_r": 1.0}
    parametre_izgarasi = {"varyant": ["ema_cci0", "cci100_macd"], "stop_atr_k": [1.0, 1.5, 2.0], "hedef_r": [0.75, 1.0, 1.5]}

    def kosullar(self, m):
        v = self.parametreler["varyant"]
        if v not in ("ema_cci0", "cci100_macd"):
            raise ValueError(f"Bilinmeyen varyant: {v!r}")
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        if v == "ema_cci0":
            ci = cci(y, d, c, 21)
            e40, e80 = g.ema(c, 40), g.ema(c, 80)
            return {"long": (e40 > e80) & yukari_kesis(ci, 0.0), "short": (e40 < e80) & asagi_kesis(ci, 0.0)}
        ci = cci(y, d, c, 14)
        mc = g.macd(c, 12, 26, 9)
        ml, sg = mc["macd"], mc["sinyal"]
        return {"long": yukari_kesis(ci, 100.0) & (ml > ml.shift(1)) & (ml > sg),
                "short": asagi_kesis(ci, -100.0) & (ml < ml.shift(1)) & (ml < sg)}


# =============================================================================== 5. Anti-stokastik
class AntiStokastik(_Taban):
    """dis__anti-stokastik (scalp, 5m) — Raschke/Connors "Anti" (kaynak kart ho-lbr): yavaş stokastik kendi 10 mumluk SMA'sını yukarı
    keserken bu SMA'nın kendisi yukarı eğimliyse long; aşağı keserken SMA aşağı eğimliyse short. Stokastik: ham %K(7), K yumuşatma 3
    (VARSAYIM; kitapta yok) -> stokastik = K; MA = SMA(K, 10). Eğim: MA > önceki MA.
    Kitap: 1.5 puan stop, 2 puan hedef, 3 dakikada ilerleme yoksa çık -> stop_atr_k x ATR (varsayılan 1.5), hedef_r x R (varsayılan 1.33),
    zaman_cikisi = N mum (varsayılan 3 mum; 5m'de 'dakika' yerine mum; VARSAYIM)."""
    ad = "dis__anti-stokastik"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stok_n": 7, "stok_yumusat": 3, "ma_n": 10, "stop_atr_k": 1.5, "hedef_r": 1.33,
                               "zaman_cikisi": 3}
    parametre_izgarasi = {"stop_atr_k": [1.0, 1.5, 2.0], "hedef_r": [1.0, 1.33, 2.0], "zaman_cikisi": [2, 3, 6]}

    def kosullar(self, m):
        p = self.parametreler
        st = yavas_stok(m["yuksek"], m["dusuk"], m["kapanis"], int(p["stok_n"]), int(p["stok_yumusat"]), 1)["k"]
        ma = st.rolling(int(p["ma_n"]), min_periods=int(p["ma_n"])).mean()
        return {"long": yukari_kesis(st, ma) & (ma > ma.shift(1)), "short": asagi_kesis(st, ma) & (ma < ma.shift(1))}


# =============================================================================== 6. Carter BB dışı sinyal mumu
class CarterBbDisiSinyalMumu(_Taban):
    """dis__carter-bb-disi-sinyal-mumu (scalp, 5m) — Carter sistem 3. Kartın kuralı kendi içinde çelişkili ('trend yönünde gir' ama
    Bollinger DIŞINDA kapanış); makul yorum: TREND İÇİ GERİ ÇEKİLME. Ölçülebilir tanım (VARSAYIM): yükseliş trendi = EMA(trend_hizli) >
    EMA(trend_yavas); long = yükseliş trendinde kapanış Bollinger(20, 2) ALT bandının altında + yavaş stokastik(5,3,3) K<20 + kırmızı
    mum (sinyal mumu); short = düşüş trendinde kapanış ÜST bandın üstünde + K>80 + yeşil mum. Kitap: stop 20 pip, hedef 10 pip -> stop_atr_k
    x ATR ve hedef_r x R (hedef stopun yarısı)."""
    ad = "dis__carter-bb-disi-sinyal-mumu"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "bb_n": 20, "bb_k": 2.0, "trend_hizli": 50, "trend_yavas": 200, "stop_atr_k": 2.0,
                               "hedef_r": 0.5}
    parametre_izgarasi = {"trend_yavas": [100, 200, 300], "stop_atr_k": [1.5, 2.0, 3.0], "hedef_r": [0.5, 1.0, 1.5]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, c, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        bb = g.bollinger(c, int(p["bb_n"]), float(p["bb_k"]))
        alt, ust = bb.iloc[:, 0], bb.iloc[:, 2]
        k = yavas_stok(y, d, c, 5, 3, 3)["k"]
        yuk_trend = g.ema(c, int(p["trend_hizli"])) > g.ema(c, int(p["trend_yavas"]))
        ayi_trend = g.ema(c, int(p["trend_hizli"])) < g.ema(c, int(p["trend_yavas"]))
        return {"long": yuk_trend & (c < alt) & (k < 20) & (c < o), "short": ayi_trend & (c > ust) & (k > 80) & (c > o)}


# =============================================================================== 7. RSI / VWMA kesişimi
class RsiMaKesisim(_Taban):
    """dis__rsi-ma-kesisim (scalp, 5m) — Ratford "RSI+VWMA+200SMA". Long: kapanış SMA(200) üstünde, RSI(9) kendi VWMA(20)'sini
    (RSI üzerinde hacim ağırlıklı ortalama) yukarı keser ve kapanış SMA(12) üstündedir. Çıkış: kapanış SMA(12) altına iner veya RSI VWMA'nın
    altına düşer. Kart yalnız long; short ayna eklendi (varsayılan yonler='long'). Kitapta stop yok -> stop_atr_k x ATR (VARSAYIM);
    '12 SMA' fiyat üzerinde varsayıldı (kart metni belirsiz)."""
    ad = "dis__rsi-ma-kesisim"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "rsi_n": 9, "vwma_n": 20, "sma_hizli": 12, "sma_yavas": 200,
                               "stop_atr_k": 2.0, "hedef_r": 0.0}
    parametre_izgarasi = {"rsi_n": [7, 9, 14], "vwma_n": [14, 20, 30], "stop_atr_k": [2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        c = m["kapanis"]
        r = g.rsi(c, int(p["rsi_n"]))
        vw = vwma(r, m["hacim"], int(p["vwma_n"]))
        sh, sy = g.sma(c, int(p["sma_hizli"])), g.sma(c, int(p["sma_yavas"]))
        return {"long": (c > sy) & yukari_kesis(r, vw) & (c > sh), "short": (c < sy) & asagi_kesis(r, vw) & (c < sh),
                "cikis_long": (c < sh) | (r < vw), "cikis_short": (c > sh) | (r > vw)}


# =============================================================================== 8. Sapan geri çekilme
class SapanGeriCekilme(_Taban):
    """dis__sapan-geri-cekilme (scalp, 5m; kartta 987-tick/3-5dk) — "Ultimate Scalper" sapan (slingshot): trend yönünde geri çekilirken
    MACD ortalaması (sinyal çizgisi, MACD 5-26-9) trend yönünde bozulmuyorsa, geri çekilme mumunun ucunun 1 tik ötesine stop emri.
    Bar-içi stop emri yok -> ölçülebilir karşılığı (VARSAYIM): trend = kapanış > EMA(trend_n=50) ve EMA eğimi yukarı; geri çekilme = en az
    `geri_min` ardışık mumun YÜKSEĞİ bir öncekinden düşük (düşen zirveler); MACD sinyal çizgisi bir önceki mumdan yüksek; tetik = bu
    mumun kapanışı bir önceki (geri çekilme) mumunun yükseğinin üstünde (stop emri dolmuş sayılır). Short ayna (yükselen dipler).
    Stop: son stop_n mumun en düşüğü (geri çekilmenin ucu), en az 0.5 ATR uzaklıkta. Kitapta hedef yok: hedef_r x R (VARSAYIM, 2) ve
    isteğe bağlı ATR iz süren stop (CikisAyarlari.atr_iz_suren_k=2.5)."""
    ad = "dis__sapan-geri-cekilme"
    stil = "scalp"
    _OZEL_STOP = True
    varsayilan_parametreler = {**ORTAK, "trend_n": 50, "geri_min": 2, "stop_n": 5, "min_risk_atr": 0.5, "hedef_r": 2.0}
    parametre_izgarasi = {"geri_min": [1, 2, 3], "stop_n": [3, 5, 8], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.5)

    def kosullar(self, m):
        p = self.parametreler
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        e = g.ema(c, int(p["trend_n"]))
        sig = g.macd(c, 5, 26, 9)["sinyal"]
        gm = int(p["geri_min"])
        dusen_zirve = ardisik_say(y < y.shift(1))
        yuksen_dip = ardisik_say(d > d.shift(1))
        lg = (c > e) & (e > e.shift(1)) & (sig > sig.shift(1)) & (dusen_zirve.shift(1) >= gm) & (c > y.shift(1))
        sh = (c < e) & (e < e.shift(1)) & (sig < sig.shift(1)) & (yuksen_dip.shift(1) >= gm) & (c < d.shift(1))
        sl, ss = _alt_ust_stop(m, int(p["stop_n"]))
        return {"long": lg, "short": sh, "stop_l": sl, "stop_s": ss}


# =============================================================================== 9. UT Bot + KDJ
class UtbotKdj(_Taban):
    """dis__utbot-kdj (scalp, 5m) — Ferrazzi "UT Bot + KDJ + 200 SMA". UT Bot: kaynak=kapanış, ATR(ut_atr, varsayılan 30), anahtar değer
    ut_key (3); formül JeRCEqWU.pine `utTrailingStop` ile aynı. KDJ (n=9): K, D, J = 3K-2D. Kitaptaki 'B/S' etiketi formülü yok; 'üç KDJ
    çizgisi yukarı kesişir' = J>K>D hizası (VARSAYIM; aşağı: J<K<D). Long: kapanış > SMA200, yeşil mum ve (UT al olayı VE KDJ hizası
    yukarı) VEYA (KDJ yukarı hiza olayı VE UT durumu yukarı). Short ayna. Çıkış: UT ters sinyal VEYA KDJ ters hiza olayı (kitap: biri
    yeter). Kitapta stop yok -> stop_atr_k x ATR felaket stopu (VARSAYIM)."""
    ad = "dis__utbot-kdj"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "ut_key": 3.0, "ut_atr": 30, "kdj_n": 9, "sma_n": 200, "stop_atr_k": 3.0, "hedef_r": 0.0}
    parametre_izgarasi = {"ut_key": [2.0, 3.0, 4.0], "ut_atr": [10, 20, 30], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, c, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        ut = ut_bot(c, g.atr(y, d, c, int(p["ut_atr"])), float(p["ut_key"]))
        kd = kdj(y, d, c, int(p["kdj_n"]))
        yuk_hiza = (kd["j"] > kd["k"]) & (kd["k"] > kd["d"])
        asg_hiza = (kd["j"] < kd["k"]) & (kd["k"] < kd["d"])
        s = g.sma(c, int(p["sma_n"]))
        lg = (c > s) & (c > o) & ((ut["al"] & yuk_hiza) | (gecis(yuk_hiza) & (ut["durum"] == 1)))
        sh = (c < s) & (c < o) & ((ut["sat"] & asg_hiza) | (gecis(asg_hiza) & (ut["durum"] == -1)))
        return {"long": lg, "short": sh, "cikis_long": ut["sat"] | gecis(asg_hiza), "cikis_short": ut["al"] | gecis(yuk_hiza)}


# =============================================================================== 10. WaveTrend + HalfTrend
class WavetrendHalftrend(_Taban):
    """dis__wavetrend-halftrend (scalp, 5m) — Ferrazzi "WTMO + HalfTrend". WaveTrend (LazyBear; _gosterge_d3.dalga_trend, kanal=wt_n 14,
    ortalama 21): wt1. HalfTrend: d8_atlanan_a._halftrend (amplitude=ht_amp, varsayılan 2) al/sat okları. Aşırı seviye ±wt_seviye (60,
    VARSAYIM; kitapta sayı yok). Long: HalfTrend AL oku VE WaveTrend son `pencere` mumda -seviyenin altına girmiş ve şimdi yukarı dönüyor
    (wt1 > önceki); VEYA WaveTrend aşırı satımdan yukarı döndüğü mumda HalfTrend durumu yukarı. Short ayna. Çıkış (kitap: biri yeter):
    WaveTrend karşı uca (+seviye) ulaşıp aşağı döner, ya da HalfTrend ters ok. Kitapta stop yok -> stop_atr_k x ATR (VARSAYIM)."""
    ad = "dis__wavetrend-halftrend"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "wt_n": 14, "wt_seviye": 60.0, "ht_amp": 2, "pencere": 3, "stop_atr_k": 2.5, "hedef_r": 0.0}
    parametre_izgarasi = {"wt_seviye": [40.0, 60.0, 80.0], "ht_amp": [2, 3, 4], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        wt = dalga_trend(y, d, c, int(p["wt_n"]), 21, 4)["wt1"]
        sv, w = float(p["wt_seviye"]), int(p["pencere"])
        ht, al, sat = _halftrend(y, d, c, int(p["ht_amp"]))
        ht_yukari = ht.notna() & (c >= ht) & (al.cumsum() >= sat.cumsum())
        ht_asagi = ht.notna() & ~ht_yukari
        yukari_don = (wt > wt.shift(1)) & (wt.shift(1) <= wt.shift(2))
        asagi_don = (wt < wt.shift(1)) & (wt.shift(1) >= wt.shift(2))
        os_yakin = wt.rolling(w, min_periods=1).min() < -sv
        ob_yakin = wt.rolling(w, min_periods=1).max() > sv
        lg = (al & os_yakin & (wt > wt.shift(1))) | (yukari_don & os_yakin & ht_yukari)
        sh = (sat & ob_yakin & (wt < wt.shift(1))) | (asagi_don & ob_yakin & ht_asagi)
        cik_l = sat | (ob_yakin & asagi_don)
        cik_s = al | (os_yakin & yukari_don)
        return {"long": lg, "short": sh, "cikis_long": cik_l, "cikis_short": cik_s}


# =============================================================================== 11. Saat dönüş
class SaatDonusScalp(_Taban):
    """dis__saat-donus-scalp (scalp, 15m) — "Hit and Run"/ho-lbr saat 10 dönüşü ve saat 15 dönüşü (New York saati). Sinyal bar KAPANIŞINDA;
    kitaptaki 'son barın yükseğinin 1 tik üstüne buy-stop' = kapanışın bir önceki barın yükseğini aşması (VARSAYIM). NY saatine göre
    (mum kapanış anı), seans = 09:30'dan itibaren; gün içi tepe/dip bu andan itibaren.
      saat=10: bar kapanışı 10:00'da gün içi (ilk 30 dk) aralığındaki konum = (kapanış-dip)/(tepe-dip) <= yakin (dibe yakın, VARSAYIM 0.25)
               -> 10:00-10:30 penceresinde ilk kapanış>önceki bar yükseği = long; konum >= 1-yakin -> short (kapanış<önceki bar düşüğü).
      saat=15: 15:00'den önceki 30 dk hareket (15:00 kapanışı - 14:30 kapanışı) aşağıysa (en az min_hareket_atr x ATR) long (buy-stop), yukarıysa
               short; pencere 15:00-15:30. Kartta 'stop/hedef 10 saat ile aynı varsayıldı' notu var.
    Günde her yön için en fazla 1 giriş. Kitap: stop 1 puan, hedef 1.5 puan, 1 dakikadan uzun işlem kapatılır -> stop_atr_k x ATR, hedef_r x R,
    zaman_cikisi = N mum (varsayılan 4 mum = 1 saat; 'dakika' bu mum süresinde yoktur). Kripto 7/24 verisinde de aynı NY saati kullanılır."""
    ad = "dis__saat-donus-scalp"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "saat": 10, "yakin": 0.25, "min_hareket_atr": 0.3, "pencere_dk": 30, "stop_atr_k": 1.0,
                               "hedef_r": 1.5, "zaman_cikisi": 4}
    parametre_izgarasi = {"saat": [10, 15], "stop_atr_k": [0.75, 1.0, 1.5], "hedef_r": [1.0, 1.5, 2.0]}

    def kosullar(self, m):
        p = self.parametreler
        saat = int(p["saat"])
        if saat not in (10, 15):
            raise ValueError("saat 10 veya 15 olmalı")
        idx = m.index
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        ix = idx if idx.tz is not None else idx.tz_localize("UTC")
        ny = ix.tz_convert(NY)
        tf = mum_suresi_dk(idx)
        ac_dk = (ny.hour * 60 + ny.minute).to_numpy(dtype=float)
        kap_dk = ac_dk + tf
        gun = np.asarray(ny.normalize().tz_localize(None).values.astype("datetime64[D]").astype("int64"))
        hedef_dk = saat * 60
        pen = (tf > 0) & (kap_dk > hedef_dk) & (kap_dk <= hedef_dk + float(p["pencere_dk"]))
        pen = pd.Series(pen, index=idx)
        a = g.atr(y, d, c, int(p["atr_periyot"]))
        kosul_l = c > y.shift(1)
        kosul_s = c < d.shift(1)
        if saat == 10:
            rth = pd.Series(ac_dk >= 570, index=idx)
            gh = y.where(rth).groupby(gun).cummax()
            gl = d.where(rth).groupby(gun).cummin()
            konum = (c - gl) / (gh - gl).where(gh > gl)
            kur_an = pd.Series(np.isclose(kap_dk, hedef_dk) & (tf > 0), index=idx)
            ayar = konum.where(kur_an).groupby(gun).ffill()
            y_l, y_s = ayar <= float(p["yakin"]), ayar >= 1.0 - float(p["yakin"])
        else:
            c0 = c.where(pd.Series(np.isclose(kap_dk, hedef_dk - 30) & (tf > 0), index=idx)).groupby(gun).ffill()
            c1 = c.where(pd.Series(np.isclose(kap_dk, hedef_dk) & (tf > 0), index=idx)).groupby(gun).ffill()
            a1 = a.where(pd.Series(np.isclose(kap_dk, hedef_dk) & (tf > 0), index=idx)).groupby(gun).ffill()
            hareket = c1 - c0
            esik = float(p["min_hareket_atr"]) * a1
            y_l, y_s = hareket < -esik, hareket > esik
        ham_l = (pen & y_l & kosul_l).fillna(False)
        ham_s = (pen & y_s & kosul_s).fillna(False)
        ilk_l = ham_l & (ham_l.groupby(gun).cumsum() == 1)
        ilk_s = ham_s & (ham_s.groupby(gun).cumsum() == 1)
        return {"long": ilk_l, "short": ilk_s}


# =============================================================================== 12. NSM MACD
class NsmMacd(_Taban):
    """dis__nsm-macd (scalp, 5m) — Ratford "DMI Stokastik + Normalleştirilmiş Yumuşatılmış MACD (NSM)". Giriş yalnız NSM çizgisinin rengine
    bağlıdır (DMI Stokastik'in giriş kuralında rolü yok, kart bunu belirtir). NSM tanımı kitapta yok -> yaygın tanım
    (_gosterge_d10e.nsm_macd): MACD(12,26) çizgisi EMA(yumusat) ile yumuşatılır, son norm_n mumun en büyük mutlak değerine bölünür. 'Yeşile
    döndü' = çizgi eğimi artıya geçti (önceki mum aşağı/yatay); 'kırmızıya döndü' = tersi. Long: yeşil dönüş; short: kırmızı dönüş
    (kitap: kuralları ters çevir). Stop: giriş mumunun dibi (short: zirvesi), en az min_risk_atr x ATR uzaklıkta. Çıkış: ters renk dönüşü
    (kitap: MACD kırmızıya dönünce sat). Hedef yok (hedef_r=0). Çok sık dönen bir çizgi -> işlem sayısı yüksek, maliyet baskın olabilir."""
    ad = "dis__nsm-macd"
    stil = "scalp"
    _OZEL_STOP = True
    varsayilan_parametreler = {**ORTAK, "hizli": 12, "yavas": 26, "yumusat": 3, "norm_n": 100, "min_risk_atr": 0.5,
                               "hedef_r": 0.0}
    parametre_izgarasi = {"yumusat": [3, 5, 8], "norm_n": [50, 100, 200], "min_risk_atr": [0.5, 1.0, 1.5]}

    def kosullar(self, m):
        p = self.parametreler
        n = nsm_macd(m["kapanis"], int(p["hizli"]), int(p["yavas"]), int(p["yumusat"]), int(p["norm_n"]))
        return {"long": n["yesil_don"], "short": n["kirmizi_don"], "cikis_long": n["kirmizi_don"], "cikis_short": n["yesil_don"],
                "stop_l": m["dusuk"], "stop_s": m["yuksek"]}


# =============================================================================== 13. Trend Magic
class TrendMagic(_Taban):
    """dis__trend-magic (scalp, 5m) — Ratford "BB+MACD + Trend Magic". Trend Magic (Kıvanç Özbilgiç): CCI(20)>=0 iken çizgi mavi ve düşük -
    1.0 x ATR(5, SMA) ile yalnız yukarı iz sürer; aksi halde kırmızı, yüksek + ATR ile yalnız aşağı (kitapta parametre yok -> yaygın
    varsayılanlar, _gosterge_d10e.trend_magic). BB+MACD (Dreadblitz): MACD(12,26) çizgisi üzerine Bollinger(bb_n=10, bb_k=1) -> MACD üst
    bandın üstünde = yeşil, alt bandın altında = kırmızı, arada mavi (VARSAYIM: eşikler kitapta yok). Long: BB+MACD yeşil VE Trend Magic
    mavi VE kapanış TM üstünde (durum geçişi). Short ayna. Çıkış: BB+MACD yeşilden çıkar (maviye döner) veya kapanış TM altına iner.
    Stop: giriş mumu dibi (short: zirvesi), en az min_risk_atr x ATR uzaklıkta. Hedef yok."""
    ad = "dis__trend-magic"
    stil = "scalp"
    _OZEL_STOP = True
    varsayilan_parametreler = {**ORTAK, "cci_n": 20, "tm_atr_n": 5, "tm_carpan": 1.0, "bb_n": 10, "bb_k": 1.0, "min_risk_atr": 0.5,
                               "hedef_r": 0.0}
    parametre_izgarasi = {"tm_carpan": [0.75, 1.0, 1.5], "bb_k": [0.75, 1.0, 1.5], "min_risk_atr": [0.5, 1.0, 1.5]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, c = m["yuksek"], m["dusuk"], m["kapanis"]
        tm = trend_magic(y, d, c, int(p["cci_n"]), int(p["tm_atr_n"]), float(p["tm_carpan"]))
        bm = bb_macd_renk(c, 12, 26, int(p["bb_n"]), float(p["bb_k"]))
        lg_d = bm["yesil"] & tm["mavi"] & (c > tm["cizgi"]) & tm["cizgi"].notna()
        sh_d = bm["kirmizi"] & ~tm["mavi"] & (c < tm["cizgi"]) & tm["cizgi"].notna()
        return {"long": gecis(lg_d), "short": gecis(sh_d),
                "cikis_long": ~bm["yesil"] | (c < tm["cizgi"]), "cikis_short": ~bm["kirmizi"] | (c > tm["cizgi"]),
                "stop_l": d, "stop_s": y}


# =============================================================================== 14. CleanTradeQuantum
class TvCleanTradeQuantum(_Taban):
    """dis__tv-cleantradequantum (belirsiz -> scalp, 5m-15m) — TradingView "CleanTradeQuantum_v7.2_OB_FVG_INTEGRATED"
    (arsiv/strateji-sg/tv/pine/JeRCEqWU.pine, 1400+ satır; WFO yönlendirici, 'kuantum' hafıza skoru, kümelenme oyu, CISD katmanı, hata
    muhafızı, prop kuralları gibi bölümler SADELEŞTİRİLDİ/ALINMADI). Kodlanan çekirdek (Pine 'Strict' kapı mantığı):
      * Sniper yanlılık (6 bileşen, her biri 1 puan, rsi5m MTF bileşeni atıldı): kapanış>seans VWAP, RSI14>50, MACD>sinyal, EMA9>EMA21,
        ADX>25 ve kapanış>EMA9, hacim>SMA20(hacim) ve yükseliş mumu. Yüzde = puan/6; long için yüzde >= sniper_min ve ayı yüzdesinden büyük.
      * Tetik `tetik`: 'ut' = UT Bot al olayı (kaynak kapanış, ATR ut_atr, anahtar ut_key) — Pine 'UT Final Trigger';
        'ema' = EMA9/21 yukarı kesişimi + VWAP üstü + MACD>sinyal (Pine 'sniperLongTrigger').
      * Süzgeçler: kapanış > EMA(trend_ema, 34) ve EMA yukarı eğimli; KAMA(8, 2, 24) üstünde ve yükseliyor.
      * OB/FVG: `bolge_gerekli`=1 ise son mumlarda boğa order-block (pivot dibi bölgesi, ob_ pivot 6, boyu <= 1.6 ATR, 25 mum geçerli;
        orijinal yalnız onay mumunda kontrol eder, burada bölge süre boyunca geçerli: GENİŞLETME) veya boğa FVG (düşük > yüksek[fvg_geri],
        önceki mum yükseliş) dokunuşu şart (0 ise yalnızca kapıya bonus değil, hiç kullanılmaz). Short ayna.
    Çıkış: Pine karma stop (ATR 1.8 / yapı) ve TP1..TP5 (kısmi) yerine stop_atr_k (1.8) x ATR stop ve hedef_r (1.5) x R hedef (VARSAYIM);
    ters sinyalde Pine pozisyonu kapatıp çevirir -> cikis_long/short = ters tetik."""
    ad = "dis__tv-cleantradequantum"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "tetik": "ut", "ut_key": 0.9, "ut_atr": 10, "sniper_min": 58.0, "trend_ema": 34,
                               "bolge_gerekli": 0, "ob_pivot": 6, "ob_atr_k": 1.6, "ob_omur": 25, "fvg_geri": 2,
                               "stop_atr_k": 1.8, "hedef_r": 1.5}
    parametre_izgarasi = {"tetik": ["ut", "ema"], "ut_key": [0.9, 2.0, 3.0], "sniper_min": [58.0, 70.0], "bolge_gerekli": [0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        if p["tetik"] not in ("ut", "ema"):
            raise ValueError(f"Bilinmeyen tetik: {p['tetik']!r}")
        y, d, c, o, h = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"], m["hacim"]
        a = g.atr(y, d, c, 14)
        e9, e21 = g.ema(c, 9), g.ema(c, 21)
        vw = g.vwap_seans(y, d, c, h, seans_kimligi(m.index))["vwap"]
        r = g.rsi(c, 14)
        mc = g.macd(c, 12, 26, 9)
        ml, sg = mc["macd"], mc["sinyal"]
        ad_ = g.adx(y, d, c, 14)["adx"]
        hv = g.sma(h, 20)
        boga_puan = ((c > vw).astype(int) + (r > 50) + (ml > sg) + (e9 > e21) + ((ad_ > 25) & (c > e9)) + ((h > hv) & (c > o)))
        ayi_puan = ((c < vw).astype(int) + (r < 50) + (ml < sg) + (e9 < e21) + ((ad_ > 25) & (c < e9)) + ((h > hv) & (c < o)))
        bp, ap = boga_puan / 6.0 * 100.0, ayi_puan / 6.0 * 100.0
        yanlilik_l = (bp > ap) & (bp >= float(p["sniper_min"]))
        yanlilik_s = (ap > bp) & (ap >= float(p["sniper_min"]))
        et = g.ema(c, int(p["trend_ema"]))
        ema_l = (c > et) & (et > et.shift(1))
        ema_s = (c < et) & (et < et.shift(1))
        km = kama(c, 8, 2, 24)
        kama_l = (c > km) & (km > km.shift(1))
        kama_s = (c < km) & (km < km.shift(1))
        ut = ut_bot(c, g.atr(y, d, c, int(p["ut_atr"])), float(p["ut_key"]))
        if p["tetik"] == "ut":
            tl, ts = ut["al"], ut["sat"]
        else:
            tl = yukari_kesis(e9, e21) & (c > vw) & (ml > sg)
            ts = asagi_kesis(e9, e21) & (c < vw) & (ml < sg)
        lg = tl & yanlilik_l & ema_l & kama_l
        sh = ts & yanlilik_s & ema_s & kama_s
        if int(p["bolge_gerekli"]):
            ob_b, ob_a = ob_bolgeleri(y, d, a, int(p["ob_pivot"]), float(p["ob_atr_k"]), int(p["ob_omur"]))
            fl = int(p["fvg_geri"])
            fvg_b = (d > y.shift(fl)) & (c.shift(1) > o.shift(1))
            fvg_a = (y < d.shift(fl)) & (c.shift(1) < o.shift(1))
            lg = lg & (ob_b | fvg_b)
            sh = sh & (ob_a | fvg_a)
        return {"long": lg, "short": sh, "cikis_long": ts, "cikis_short": tl}
