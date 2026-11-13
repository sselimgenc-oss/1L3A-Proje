"""Kapanış turu kodlama partisi g8_kod_2 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_2.csv, 40 satır, X005 listesi).

Her sınıf `kural_tam` metnine göre kendi cümleleriyle yazılmış bir uyarlamadır; üçüncü taraf kodu kopyalanmadı.
Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Gelecek verisi yok.

Ortak uyarlamalar (tüm sınıflar)
  - Kaynakta stop yoksa ya da <= -%50 ise ATR(14)x3 (ön kayıt). Kaynağın yüzde stopu varsa stop = sinyal kapanışı x (1 -/+ yüzde)
    (kaynak giriş fiyatı yerine sinyal kapanışı; kapanış bazlı stop yazılmışsa motorun bar içi stopu kullanılır).
  - "Pozisyon yokken gir" kuralları motorun "açık pozisyon varken yeni giriş yok" davranışına bırakılır. Giriş olayı ile karşı
    yönün çıkış koşulu aynı mumda doğabiliyorsa (115, 181, 182, 183, 185, 189, 208, 210, 219) kaynaktaki "çıkış mumunda yeni giriş
    yok" sırası `_sanal` ile korunur: sanal durum YALNIZ bu girişleri süzmek ve girişe bağlı çıkışları (185, 189) hesaplamak için
    kullanılır; çıkış koşulları her mumda yazılıp motora bırakılır, sanal durum motorla ayrışırsa (reddedilen giriş vb.) kaynak
    sırasından küçük sapma olur.
  - Kâra bağlı "zirveden geri çekilme" çıkışı motorun `geri_cekilme_*` modülüdür: zirve = girişten beri en yüksek YÜKSEK (kaynak
    bazı satırlarda en yüksek kapanış), fark = giriş fiyatına göre kâr% farkı (kaynak: zirve fiyatının %'si), kapanışta kontrol,
    çıkış sonraki açılışta.
  - TF "1w" (136) ve aylık (141) satırları 1d mumlarla koşulur (VARYANTLAR tf = "1d"); haftalık değer `htf.ust_zaman` ile yalnız
    kapanmış haftadan, ertesi günün (Pazartesi) mumundan itibaren kullanılır.
  - HAM:X005:114 kodlanamadı (iki kademeli bant hedefli çıkış); bkz. KODLANAMADI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve, seans_son_mumu
from motor.strateji.dis._gosterge_d1 import hma
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


# ------------------------------------------------------------------ yardımcılar
def _b(x, idx) -> pd.Series:
    if isinstance(x, pd.Series):
        return x.fillna(False).astype(bool)
    return pd.Series(np.asarray(x), index=idx).fillna(False).astype(bool)


def _np(x) -> np.ndarray:
    if isinstance(x, pd.Series):
        x = x.fillna(False).astype(bool).to_numpy()
    return np.asarray(x, dtype=bool)


def _atr_stop(m: pd.DataFrame, n: int, k: float):
    kap = m["kapanis"]
    a = g.atr(m["yuksek"], m["dusuk"], kap, n)
    return kap - k * a, kap + k * a


def _yuzde_stop(m: pd.DataFrame, y: float):
    kap = m["kapanis"]
    return kap * (1.0 - y), kap * (1.0 + y)


def _cikti(m, gl, gs, stop_l, stop_s, cl=None, cs=None, hedef_l=None, hedef_s=None, zc=None) -> pd.DataFrame:
    s = cerceve(m, gl, gs, stop_l, stop_s, hedef_l=hedef_l, hedef_s=hedef_s)
    if cl is not None:
        s["cikis_long"] = _b(cl, m.index)
    if cs is not None:
        s["cikis_short"] = _b(cs, m.index)
    if zc is not None:
        s["zaman_cikisi_mum"] = pd.Series(np.where(s["yon"] != 0, float(zc), np.nan), index=m.index)
    return s


def _sanal(m, gl, gs, cl, cs, stop_l, stop_s, max_mum=None, baslat=None, ek=None):
    """Kaynaktaki "açık pozisyon varken çıkış, yoksa giriş" sırasını izleyen NEDENSEL sanal durum.

    Dönüş: (giris_long, giris_short, cikis_long, cikis_short) bool dizileri. Giriş dizileri: giriş koşulu doğru VE o mumda sanal
    pozisyon çıkış yapmıyor. Çıkış dizileri: kural/ek çıkış (girişe bağlı olanlar dahil) sanal pozisyon açıkken doğdu.
    Sanal pozisyon bar içi stopla (giriş mumundan sonraki mumlarda) ve en çok `max_mum` mumla da kapanır (motorla aynı sayım).
    `baslat(t, yon)` girişte, `ek(t, yon)` her açık mumda çağrılır (girişe bağlı kural durumu çağıranın kapanışındadır)."""
    c = m["kapanis"].to_numpy(float)
    h = m["yuksek"].to_numpy(float)
    lo = m["dusuk"].to_numpy(float)
    sl = np.asarray(stop_l, float)
    ss = np.asarray(stop_s, float)
    gl = _np(gl) & np.isfinite(sl) & (sl < c)
    gs = _np(gs) & np.isfinite(ss) & (ss > c) & ~gl
    n = len(c)
    cl, cs = np.broadcast_to(_np(cl), (n,)), np.broadcast_to(_np(cs), (n,))
    ver_l, ver_s = np.zeros(n, bool), np.zeros(n, bool)
    cik_l, cik_s = np.zeros(n, bool), np.zeros(n, bool)
    poz, e, stp = 0, -1, np.nan
    for t in range(n):
        cikti = False
        if poz:
            if (poz == 1 and lo[t] <= stp) or (poz == -1 and h[t] >= stp):
                poz = 0
            else:
                kural = cl[t] if poz == 1 else cs[t]
                if not kural and ek is not None:
                    kural = ek(t, poz)
                if kural:
                    (cik_l if poz == 1 else cik_s)[t] = True
                    poz, cikti = 0, True
                elif max_mum is not None and t - e >= max_mum:
                    poz, cikti = 0, True
        if not cikti:
            if gl[t]:
                ver_l[t] = True
                if poz == 0:
                    poz, e, stp = 1, t, sl[t]
                    if baslat:
                        baslat(t, 1)
            elif gs[t]:
                ver_s[t] = True
                if poz == 0:
                    poz, e, stp = -1, t, ss[t]
                    if baslat:
                        baslat(t, -1)
    return ver_l, ver_s, cik_l, cik_s


def _bant(m: pd.DataFrame, n: int, sapma: float) -> pd.DataFrame:
    return g.bollinger(m["kapanis"], n, sapma)


# ------------------------------------------------------------------ X005:85
class MacdSma200SarS0085(Strateji):
    """HAM:X005:85 — MACD(12,26,9) + SMA(200) dur-ve-çevir, 4h, iki yön.

    Long durumu: MACD > sinyal VE MACD < 0 VE kapanış > SMA200 (200 BAR). Short durumu: kapanış < SMA200 VE MACD < sinyal VE
    MACD > 0. Başka çıkış yok: karşı durum pozisyonu çevirir. Durum tabanlıdır (kesişim değil). Stop kaynakta yok: ATR(14)x3."""

    ad, stil = "kapanis__macd-sma200-sar-s0085", "swing"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "sma_n": 200, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        md = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        sma = g.sma(kap, int(p["sma_n"]))
        uzun = (md["macd"] > md["sinyal"]) & (md["macd"] < 0) & (kap > sma)
        kisa = (kap < sma) & (md["macd"] < md["sinyal"]) & (md["macd"] > 0)
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, uzun, kisa, sl, ss, cl=kisa, cs=uzun)


# ------------------------------------------------------------------ X005:95
class SupertrendAdxS0095(Strateji):
    """HAM:X005:95 — 4h Supertrend(10,3) + ADX(14) nitelikli sinyal, iki yön.

    Long: Supertrend yükselişte VE ADX >= 23 VE +DI > -DI; short ayna. Giriş = nitelikli durumun İLK oluştuğu mum (kaynak
    "nitelikli sinyal"). Çıkış: ADX < 18 ya da Supertrend pozisyon aleyhine dönünce (karşı nitelikli sinyal zaten aleyhe dönüş
    içerir, pozisyonu çevirir). Stop: sinyal kapanışından 2xATR(10). Hedef yok."""

    ad, stil = "kapanis__supertrend-adx-s0095", "swing"
    varsayilan_parametreler = {"st_atr": 10, "st_carpan": 3.0, "adx_n": 14, "adx_giris": 23.0, "adx_cikis": 18.0,
                               "stop_atr": 2.0, "stop_atr_n": 10}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        h, lo, kap = m["yuksek"], m["dusuk"], m["kapanis"]
        st = g.supertrend(h, lo, kap, int(p["st_atr"]), float(p["st_carpan"]))
        ax = g.adx(h, lo, kap, int(p["adx_n"]))
        uq = (st["yon"] == 1) & (ax["adx"] >= p["adx_giris"]) & (ax["arti_di"] > ax["eksi_di"])
        sq = (st["yon"] == -1) & (ax["adx"] >= p["adx_giris"]) & (ax["eksi_di"] > ax["arti_di"])
        gl = uq & ~uq.shift(1, fill_value=False)
        gs = sq & ~sq.shift(1, fill_value=False)
        sl, ss = _atr_stop(m, int(p["stop_atr_n"]), float(p["stop_atr"]))
        zayif = ax["adx"] < p["adx_cikis"]
        return _cikti(m, gl, gs, sl, ss, cl=zayif | (st["yon"] == -1), cs=zayif | (st["yon"] == 1))


# ------------------------------------------------------------------ X005:97
class IbsBantDonusS0097(Strateji):
    """HAM:X005:97 — 1d long: alt bant = HH(yüksek,10) - 2,5 x SMA(yüksek-düşük,25); kapanış < alt bant VE IBS < 0,3 -> long.

    IBS = (kapanış-düşük)/(yüksek-düşük). Çıkış: kapanış bir önceki günün yükseğinin üzerine çıkınca. Rejim filtresi yok.
    Stop kaynakta parametresiz: ATR(14)x3 (uyarlama). HH bugünü içerir."""

    ad, stil = "kapanis__ibs-bant-donus-s0097", "swing"
    varsayilan_parametreler = {"tepe_gun": 10, "aralik_gun": 25, "carpan": 2.5, "ibs_max": 0.3, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        h, lo, kap = m["yuksek"], m["dusuk"], m["kapanis"]
        alt = h.rolling(int(p["tepe_gun"])).max() - float(p["carpan"]) * (h - lo).rolling(int(p["aralik_gun"])).mean()
        ibs = (kap - lo) / (h - lo).replace(0.0, np.nan)
        gir = (kap < alt) & (ibs < float(p["ibs_max"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=kap > h.shift(1))


# ------------------------------------------------------------------ X005:104
class YediGunDipSma200S0104(Strateji):
    """HAM:X005:104 — 1d long: kapanış > SMA(200) VE kapanış son 7 günün (bugün dahil) en düşük kapanışı -> long.

    Çıkış: kapanış > SMA(5) (yazarın seçtiği çıkış). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__yedi-gun-dip-sma200-s0104", "swing"
    varsayilan_parametreler = {"pencere": 7, "trend_n": 200, "cikis_sma": 5, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        gir = (kap > g.sma(kap, int(p["trend_n"]))) & (kap <= kap.rolling(int(p["pencere"])).min())
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=kap > g.sma(kap, int(p["cikis_sma"])))


# ------------------------------------------------------------------ X005:108
class Rsi2Sma200S0108(Strateji):
    """HAM:X005:108 — 1d long: kapanış > SMA(200) VE RSI(2) < 5 -> long; kapanış > SMA(5) olunca çık.

    RSI Wilder (standart). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi2-sma200-s0108", "swing"
    varsayilan_parametreler = {"rsi_n": 2, "alt": 5.0, "trend_n": 200, "cikis_sma": 5, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        gir = (kap > g.sma(kap, int(p["trend_n"]))) & (g.rsi(kap, int(p["rsi_n"])) < float(p["alt"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=kap > g.sma(kap, int(p["cikis_sma"])))


# ------------------------------------------------------------------ X005:115
class BbRsiOrtaBantS0115(Strateji):
    """HAM:X005:115 (K6_STANDART) — 1d iki yön: BB(30, 2σ, kapanış) + RSI(13).

    Long: kapanış alt bandın altında VE RSI < 30; short: kapanış üst bandın üstünde VE RSI > 70. Çıkış: orta bant (SMA30)
    kesilince (long kapanış >= orta, short kapanış <= orta). Stop kaynakta yok: ATR(14)x3. Giriş "çıkış mumunda yeni giriş yok"
    sırasıyla (bkz. modül notu)."""

    ad, stil = "kapanis__bb-rsi-orta-bant-s0115", "swing"
    varsayilan_parametreler = {"bb_n": 30, "bb_std": 2.0, "rsi_n": 13, "rsi_alt": 30.0, "rsi_ust": 70.0,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        rsi = g.rsi(kap, int(p["rsi_n"]))
        gl = (kap < bb["alt"]) & (rsi < float(p["rsi_alt"]))
        gs = (kap > bb["ust"]) & (rsi > float(p["rsi_ust"]))
        cl, cs = kap >= bb["orta"], kap <= bb["orta"]
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:118
class Rsi2Sma50S0118(Strateji):
    """HAM:X005:118 — 1d long: kapanış > SMA(50) VE RSI(2) < 30 (durum, pozisyon yokken) -> long; RSI(2) > 80 çıkış.

    Wilder RSI. Alt Bollinger dokunuşu kaynak kodunda yok, uygulanmadı. Stop: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__rsi2-sma50-s0118", "swing"
    varsayilan_parametreler = {"ma_n": 50, "rsi_n": 2, "rsi_giris": 30.0, "rsi_cikis": 80.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        rsi = g.rsi(kap, int(p["rsi_n"]))
        gir = (kap > g.sma(kap, int(p["ma_n"]))) & (rsi < float(p["rsi_giris"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=rsi > float(p["rsi_cikis"]))


# ------------------------------------------------------------------ X005:136
class HaftalikKapanisKanaliS0136(Strateji):
    """HAM:X005:136 — 1w (1d'den türetilmiş) long: kapanış önceki 20 haftanın en yüksek KAPANIŞINI aşarsa long; önceki 20
    haftanın en düşük kapanışının altına inerse çık (yalnız long çıkışı).

    Mumlar 1d verilir; haftalık kapanışlar `htf.ust_zaman` ile (yalnız kapanmış hafta, Pazartesi mumundan itibaren) hesaplanır.
    Karar her yeni haftalık mumun ilk günü (yeni hafta değeri görününce) verilir. Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__haftalik-kapanis-kanali-s0136", "swing"
    varsayilan_parametreler = {"giris_n": 20, "cikis_n": 20, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        gn, cn = int(p["giris_n"]), int(p["cikis_n"])

        def fonk(u: pd.DataFrame) -> pd.DataFrame:
            kw = u["kapanis"]
            return pd.DataFrame({"kw": kw, "hh": kw.rolling(gn).max().shift(1), "ll": kw.rolling(cn).min().shift(1),
                                 "no": pd.Series(np.arange(len(u), dtype=float), index=u.index)})

        w = ust_zaman(m, "1w", fonk)
        yeni = w["no"].notna() & (w["no"] != w["no"].shift(1))
        gir = yeni & (w["kw"] > w["hh"])
        cik = yeni & (w["kw"] < w["ll"])
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:138
class SmaKesisSabitTutmaS0138(Strateji):
    """HAM:X005:138 — 1d long: SMA(10) SMA(50)'yi yukarı keserse long; sabit N gün sonra çık, N in {1,3,5,10,20,30,60,90}.

    Sekiz raporlu varyant = `tutma_gun` parametresi (VARYANTLAR'da sekiz kayıt). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__sma-kesis-sabit-tutma-s0138", "swing"
    varsayilan_parametreler = {"sma_hizli": 10, "sma_yavas": 50, "tutma_gun": 10, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        gir = yukari_kesis(g.sma(kap, int(p["sma_hizli"])), g.sma(kap, int(p["sma_yavas"])))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, zc=int(p["tutma_gun"]))


# ------------------------------------------------------------------ X005:141
class AylikSma10GtaaS0141(Strateji):
    """HAM:X005:141 — Aylık (1d mumlardan ay sonu kapanışı) long: ay sonu kapanış > son 10 ay sonu kapanışın SMA'sı ise long
    (pozisyonda kal), altına inerse çık (nakit). Sembol başına bağımsız.

    Ay sonu mumu = takvimde ertesi gün başka ayda olan mum (yalnız zaman damgasından). Durum bir sonraki ay sonuna kadar taşınır;
    stop-out sonrası durum "üstünde" sürüyorsa yeniden girilir. Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__aylik-sma10-gtaa-s0141", "swing"
    varsayilan_parametreler = {"ay_n": 10, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = m.index
        son_gun = (idx + pd.Timedelta(days=1)).month != idx.month
        me = m["kapanis"][son_gun]
        sma = me.rolling(int(p["ay_n"])).mean()
        durum = pd.Series(np.where(sma.isna(), np.nan, (me > sma).astype(float)), index=me.index)
        durum = durum.reindex(idx).ffill()
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, durum == 1.0, False, sl, ss, cl=durum == 0.0)


# ------------------------------------------------------------------ X005:144
class EwmaKutleMerkeziS0144(Strateji):
    """HAM:X005:144 — 1d iki yön: sinyal = işaret(EMA_com_hızlı(kapanış) - EMA_com_yavaş(kapanış)); pozitifse long, negatifse
    short, işaret değişince ters çevir. EMA = pandas ewm(com=c, adjust=False). Üç varyant (hızlı,yavaş com): (3,12), (8,32),
    (32,128). Oynaklık ölçekleme/portföy yok sayıldı (motor boyutlar). Stop kaynakta yok: ATR(14)x3 (uyarlama). Durum tabanlı."""

    ad, stil = "kapanis__ewma-kutle-merkezi-s0144", "swing"
    varsayilan_parametreler = {"hizli_com": 3, "yavas_com": 12, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        fark = (kap.ewm(com=float(p["hizli_com"]), adjust=False).mean()
                - kap.ewm(com=float(p["yavas_com"]), adjust=False).mean())
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, fark > 0, fark < 0, sl, ss, cl=fark < 0, cs=fark > 0)


# ------------------------------------------------------------------ X005:147
class TumZamanZirveIzS0147(Strateji):
    """HAM:X005:147 — 1d long: günün kapanışı bugüne kadarki tüm zamanların en yüksek kapanışına eşit/üstünse long; 10xATR(14) iz
    süren stop ihlalinde çık. "Tüm zamanlar" = eldeki serinin başından beri. Hisse fiyat/likidite filtreleri uygulanmaz.
    İlk stop = kapanış - 10xATR(14); iz = motorun ATR iz süren stopu (atr_iz_suren_k=10)."""

    ad, stil = "kapanis__tum-zaman-zirve-iz-s0147", "swing"
    varsayilan_parametreler = {"atr_n": 14, "atr_k": 10.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=10.0, atr_periyot=14)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        gir = kap >= kap.cummax()
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss)


# ------------------------------------------------------------------ X005:173
class DualThrustS0173(Strateji):
    """HAM:X005:173 — 1d iki yön, daima pozisyonda (dur-ve-çevir) Dual Thrust.

    Range = max(HH-LC, HC-LL), önceki N=5 günün (bugün hariç) en yüksek yüksek / en yüksek kapanış / en düşük kapanış / en düşük
    düşük değerleri. Üst = günün açılışı + k1 x Range, alt = günün açılışı - k2 x Range. Günlük kapanış üstün üstündeyse long,
    altın altındaysa short (uyarlama: tick geçişi yerine mum kapanışı). Karşı çizgi pozisyonu çevirir. Stop: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__dual-thrust-s0173", "swing"
    varsayilan_parametreler = {"nday": 5, "k1": 0.2, "k2": 0.2, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        h, lo, kap, ac = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        n = int(p["nday"])
        hh, ll = h.rolling(n).max().shift(1), lo.rolling(n).min().shift(1)
        hc, lc = kap.rolling(n).max().shift(1), kap.rolling(n).min().shift(1)
        aralik = np.maximum(hh - lc, hc - ll)
        ust, alt = ac + float(p["k1"]) * aralik, ac - float(p["k2"]) * aralik
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, kap > ust, kap < alt, sl, ss, cl=kap < alt, cs=kap > ust)


# ------------------------------------------------------------------ X005:174
class Keltner5mIzYuzdeS0174(Strateji):
    """HAM:X005:174 — 5m Keltner(11; 1,6): merkez SMA(kapanış,11), bantlar ± 1,6 x ATR(11).

    Düz pozisyondayken kapanış üst bandı yukarı keserse long, alt bandı aşağı keserse short (stop-giriş emri kapanış sinyaline
    çevrildi). Çıkış/stop: girişten sonraki en yüksek fiyatın %0,8 altı (short: en düşüğün %0,8 üstü) iz süren stop.
    Uyarlama: ilk stop = kapanış x (1 -/+ 0,008) (bar içi); iz kısmı motorun `geri_cekilme` modülüdür (kapanışta kontrol, giriş
    fiyatına göre %0,8 kâr geri çekilmesi, min kâr 0), bar içi sürekli iz yoktur.

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: bar içi sürekli %0,8 iz yerine kapanışta kontrol edilen geri çekilme modülü; fark giriş fiyatına göre."""

    ad, stil = "kapanis__keltner-5m-iz-yuzde-s0174", "daytrade"
    varsayilan_parametreler = {"n": 11, "carpan": 1.6, "iz_yuzde": 0.008}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=0.8, geri_cekilme_min_kar_yuzde=0.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        n = int(p["n"])
        orta = g.sma(kap, n)
        a = g.atr(m["yuksek"], m["dusuk"], kap, n)
        ust, alt = orta + float(p["carpan"]) * a, orta - float(p["carpan"]) * a
        sl, ss = _yuzde_stop(m, float(p["iz_yuzde"]))
        return _cikti(m, yukari_kesis(kap, ust), asagi_kesis(kap, alt), sl, ss)


# ------------------------------------------------------------------ X005:177
class BollingerCci15mS0177(Strateji):
    """HAM:X005:177 — 15m: Bollinger(18; 3,4σ); CCI(10) > 0 iken kapanış üst bandı yukarı keserse long; CCI < 0 iken alt bandı
    aşağı keserse short (stop-giriş emri kapanış sinyaline çevrildi). Çıkış/stop: girişten beri en yüksek - 5,2 x ATR(30) iz
    süren stop (short ayna): ilk stop kapanış -/+ 5,2xATR(30), iz motorun ATR iz süren stopu (atr_periyot=30)."""

    ad, stil = "kapanis__bollinger-cci-15m-s0177", "daytrade"
    varsayilan_parametreler = {"bb_n": 18, "bb_std": 3.4, "cci_n": 10, "iz_atr_n": 30, "iz_atr_k": 5.2}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=5.2, atr_periyot=30)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        c = cci(m["yuksek"], m["dusuk"], kap, int(p["cci_n"]))
        gl = (c > 0) & yukari_kesis(kap, bb["ust"])
        gs = (c < 0) & asagi_kesis(kap, bb["alt"])
        sl, ss = _atr_stop(m, int(p["iz_atr_n"]), float(p["iz_atr_k"]))
        return _cikti(m, gl, gs, sl, ss)


# ------------------------------------------------------------------ X005:181
class BbBreakoutOrtaBantS0181(Strateji):
    """HAM:X005:181 — 1d iki yön: BB(26,2) üst bandı kapanış üstünde -> long, alt bandı altında -> short (pozisyon yokken);
    long: kapanış < orta bant (SMA26) çıkış; short: kapanış > orta bant çıkış.

    Std türü kaynakta açık değil: proje standardı (popülasyon, ddof=0). Kaynak her tick'i kullanır; burada kapanmış mum.
    "Çıkış mumunda yeni giriş yok" sırası (bkz. modül notu). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__bb-breakout-orta-bant-s0181", "swing"
    varsayilan_parametreler = {"bb_n": 26, "bb_std": 2.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        gl, gs = kap > bb["ust"], kap < bb["alt"]
        cl, cs = kap < bb["orta"], kap > bb["orta"]
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:182
def _aroon(yuksek: np.ndarray, dusuk: np.ndarray, n: int):
    """Aroon yukarı/aşağı: pencere = son n mum (bugün dahil); (n - son uç'tan beri geçen mum)/n x 100; eşitlikte en yakın uç."""
    up = np.full(len(yuksek), np.nan)
    dn = np.full(len(yuksek), np.nan)
    if len(yuksek) >= n:
        wy = sliding_window_view(yuksek, n)[:, ::-1]
        wd = sliding_window_view(dusuk, n)[:, ::-1]
        up[n - 1:] = (n - wy.argmax(axis=1)) / n * 100.0
        dn[n - 1:] = (n - wd.argmin(axis=1)) / n * 100.0
    return up, dn


class AroonKesisS0182(Strateji):
    """HAM:X005:182 — 1d iki yön Aroon(10): flat iken (Up önceki < Down önceki VE Up > Down) VEYA (Up > 75 VE Down < 25) -> long,
    ayna short; long çıkış Up'ın Down'u aşağı kesmesi, short çıkış yukarı kesmesi; stop giriş fiyatından %1,2.

    Aroon penceresi son 10 mum (bugün dahil), Up = (10 - son yüksekten beri mum)/10 x 100. Stop = sinyal kapanışı x (1 -/+ 0,012).
    "Çıkış mumunda yeni giriş yok" sırası (bkz. modül notu): ters kesişim önce pozisyonu kapatır, giriş sonraki mumlarda."""

    ad, stil = "kapanis__aroon-kesis-s0182", "swing"
    varsayilan_parametreler = {"aroon": 10, "ust": 75.0, "alt": 25.0, "stop_pct": 1.2}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        up, dn = _aroon(m["yuksek"].to_numpy(float), m["dusuk"].to_numpy(float), int(p["aroon"]))
        up, dn = pd.Series(up, index=m.index), pd.Series(dn, index=m.index)
        up1, dn1 = up.shift(1), dn.shift(1)
        ust, alt = float(p["ust"]), float(p["alt"])
        gl = ((up1 < dn1) & (up > dn)) | ((up > ust) & (dn < alt))
        gs = ((dn1 < up1) & (dn > up)) | ((dn > ust) & (up < alt))
        cl = (up < dn) & (up1 >= dn1)
        cs = (up > dn) & (up1 <= dn1)
        sl, ss = _yuzde_stop(m, float(p["stop_pct"]) / 100.0)
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:183
class EmaAtrBantS0183(Strateji):
    """HAM:X005:183 — 1d iki yön: ema = EMA(8, adjust=False), ema_k = EMA(5); trend = işaret(ema_k - ema); güç = |ema_k-ema|/kapanış x 100;
    çarpan = 1,5 (güç > 0,5 ise 1,2); ATR = SMA(TR,7); üst/alt = ema ± çarpan x ATR.

    Flat iken kapanış > üst VE trend > 0 long; kapanış < alt VE trend < 0 short. İlk stop = giriş -/+ 0,8 x ATR; iz: en yüksek x
    (1 - 0,8 x ATR/kapanış) yukarı taşınır. Çıkış: stop VEYA kapanış <= ema (short >= ema) VEYA (kapanış < alt VE trend < 0) /
    simetrik. Uyarlama: iz, motorun ATR iz süren stopudur (stop = zirve - 0,8 x Wilder ATR(7)); ilk stop SMA-ATR'dir.
    "Çıkış mumunda yeni giriş yok" sırası (bkz. modül notu)."""

    ad, stil = "kapanis__ema-atr-bant-s0183", "swing"
    varsayilan_parametreler = {"ema_n": 8, "ema_kisa": 5, "atr_n": 7, "mult": 1.5, "mult_guclu": 1.2,
                               "guc_esik_pct": 0.5, "stop_atr": 0.8}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=0.8, atr_periyot=7)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        ema = g.ema(kap, int(p["ema_n"]))
        ema_k = g.ema(kap, int(p["ema_kisa"]))
        fark = ema_k - ema
        trend = np.sign(fark)
        guc = fark.abs() / kap * 100.0
        carpan = pd.Series(np.where(guc > float(p["guc_esik_pct"]), float(p["mult_guclu"]), float(p["mult"])), index=m.index)
        tr = g.gercek_aralik(m["yuksek"], m["dusuk"], kap)
        atr = tr.rolling(int(p["atr_n"]), min_periods=int(p["atr_n"])).mean()
        ust, alt = ema + carpan * atr, ema - carpan * atr
        gl = (kap > ust) & (trend > 0)
        gs = (kap < alt) & (trend < 0)
        cl = (kap <= ema) | ((kap < alt) & (trend < 0))
        cs = (kap >= ema) | ((kap > ust) & (trend > 0))
        sl, ss = kap - float(p["stop_atr"]) * atr, kap + float(p["stop_atr"]) * atr
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:185
class HmaAtrKesisS0185(Strateji):
    """HAM:X005:185 — 1d iki yön: HMA(n)=WMA(2xWMA(n/2)-WMA(n), floor(sqrt(n))). Long: HMA5 yukarı kesip HMA30'u (önceki <=, şimdi >)
    VE kapanış > HMA30; ilk stop HMA30 - 2xATR(14); iz: stop = max(stop, HMA5 - 2xATR). Çıkış: ters kesişim VEYA kapanış < stop VEYA
    kapanış >= giriş x 1,03; short ayna.

    Giriş fiyatı = sinyal kapanışı. İz stop ve %3 kâr hedefi girişe bağlı olduğundan sanal durumla (kapanış bazlı) hesaplanır ve
    çıkış sinyali olarak verilir; motorda yalnız ilk stop (bar içi) vardır. Kaynaktaki kullanılmayan %2/%0,5 kâr izi uygulanmadı.

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: %3 hedef ve HMA ratchet stopu kapanış bazlı sanal durum çıkışı, motor ratchet/hedef emri yok; giriş fiyatı = sinyal kapanışı."""

    ad, stil = "kapanis__hma-atr-kesis-s0185", "swing"
    varsayilan_parametreler = {"hizli": 5, "yavas": 30, "atr_n": 14, "stop_atr": 2.0, "tp_pct": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        hh, hy = hma(kap, int(p["hizli"])), hma(kap, int(p["yavas"]))
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"]))
        k = float(p["stop_atr"])
        gl = yukari_kesis(hh, hy) & (kap > hy)
        gs = asagi_kesis(hh, hy) & (kap < hy)
        cl, cs = asagi_kesis(hh, hy), yukari_kesis(hh, hy)
        sl, ss = hy - k * atr, hy + k * atr
        kv, hv, av = kap.to_numpy(float), hh.to_numpy(float), atr.to_numpy(float)
        tp = float(p["tp_pct"]) / 100.0
        durum = {"yon": 0, "giris": np.nan, "stop": np.nan}

        def baslat(t, yon):
            durum["yon"], durum["giris"] = yon, kv[t]
            durum["stop"] = (sl if yon == 1 else ss).iloc[t]

        def ek(t, yon):
            iz = hv[t] - yon * k * av[t]
            if np.isfinite(iz):
                durum["stop"] = max(durum["stop"], iz) if yon == 1 else min(durum["stop"], iz)
            if yon == 1:
                return kv[t] < durum["stop"] or kv[t] >= durum["giris"] * (1 + tp)
            return kv[t] > durum["stop"] or kv[t] <= durum["giris"] * (1 - tp)

        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss, baslat=baslat, ek=ek)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:186
class BbBantYonuS0186(Strateji):
    """HAM:X005:186 — 1d long: BB(22,2σ) üst, orta ve alt bandı son 3 gündür artıyor (her biri üç ardışık günde bir öncekinden yüksek)
    VE kapanış > orta bant -> long. Çıkış: üç bant birlikte düşüyorsa (aynı tanım, ayna) VEYA kapanış < orta bant; en çok 22 gün;
    kâr >= %20 iken zirveden %6,8 geri çekilmede çık. Sabit zarar stopu kapalı -> felaket stopu ATR(14)x3 (uyarlama).
    Geri çekilme motor modülüdür (bkz. modül notu).

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek yüksek (kaynak en yüksek kapanış), fark giriş fiyatına göre kâr% farkı (kaynak zirvenin %6,8'i)."""

    ad, stil = "kapanis__bb-bant-yonu-s0186", "swing"
    varsayilan_parametreler = {"bb_n": 22, "bb_std": 2.0, "yon_gun": 3, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=22, geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=20.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        d = int(p["yon_gun"])

        def hepsi(isaret):
            sonuc = pd.Series(True, index=m.index)
            for ad in ("ust", "orta", "alt"):
                fark = bb[ad].diff()
                for j in range(d):
                    sonuc &= (isaret * fark.shift(j)) > 0
            return sonuc

        gir = hepsi(1) & (kap > bb["orta"])
        cik = hepsi(-1) | (kap < bb["orta"])
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:187
class SmaKesisAdxDiS0187(Strateji):
    """HAM:X005:187 — 1d long: SMA(5) SMA(20)'yi yukarı keserken ADX(14) yükseliyor (ADX[0] > ADX[1]) VE +DI > -DI -> long; çıkış SMA(5)
    SMA(20)'yi aşağı keserken ADX düşüyor VE +DI < -DI. Stop: maliyetin -%6,8'i (sinyal kapanışı); kâr >= %35 olunca zirveden %6,8
    geri çekilmede kâr al (motor modülü, bkz. modül notu).

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek YÜKSEK (kaynak: en yüksek kapanış/zirve fiyatı), fark = giriş fiyatına göre kâr% farkı (kaynak: zirvenin %'si), kapanışta kontrol."""

    ad, stil = "kapanis__sma-kesis-adx-di-s0187", "swing"
    varsayilan_parametreler = {"ma_hizli": 5, "ma_yavas": 20, "adx_n": 14, "sl": 0.068}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=35.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        ax = g.adx(m["yuksek"], m["dusuk"], kap, int(p["adx_n"]))
        hizli, yavas = g.sma(kap, int(p["ma_hizli"])), g.sma(kap, int(p["ma_yavas"]))
        yuk = ax["adx"] > ax["adx"].shift(1)
        dus = ax["adx"] < ax["adx"].shift(1)
        gir = yukari_kesis(hizli, yavas) & yuk & (ax["arti_di"] > ax["eksi_di"])
        cik = asagi_kesis(hizli, yavas) & dus & (ax["arti_di"] < ax["eksi_di"])
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:188
class AtrKirilimS0188(Strateji):
    """HAM:X005:188 — 1d long: kapanış > önceki kapanış + 2xATR(14) -> long (fiyat dokunuşu kapanış sinyaline çevrildi); kapanış <
    önceki kapanış - 2xATR(14) -> çık. ATR önceki mumun değeridir (seviye önceki kapanışta bilinir). Stop: maliyetin -%6,8'i
    (sinyal kapanışı); kâr >= %20 olunca zirveden %6,8 iz süren kâr al (motor modülü, bkz. modül notu).

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek YÜKSEK (kaynak: en yüksek kapanış/zirve fiyatı), fark = giriş fiyatına göre kâr% farkı (kaynak: zirvenin %'si), kapanışta kontrol."""

    ad, stil = "kapanis__atr-kirilim-s0188", "swing"
    varsayilan_parametreler = {"atr_n": 14, "carpan": 2.0, "sl": 0.068}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=20.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"])).shift(1)
        k = float(p["carpan"])
        gir = kap > kap.shift(1) + k * atr
        cik = kap < kap.shift(1) - k * atr
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:189
def _kayan_ort(x: np.ndarray, per: int, t: int) -> float:
    if per <= 0 or t + 1 < per:
        return np.nan
    return float(x[t - per + 1:t + 1].mean())


class UyarlanirMaKanalS0189(Strateji):
    """HAM:X005:189 — 1d long: ortalama SMA(50), bant ± 1,25σ(50); kapanış üst bandı aşarsa VE kapanış > 30 gün önceki kapanış (ROC30 > 0) ->
    long. Çıkış: pozisyonda geçen her gün ortalama periyodu 1 azalır (50'den başlayıp en az 10) ve kapanış bu uyarlanan SMA'nın altına
    inerse çık (VEYA ROC < 0 VE kapanış alt bandın altında); ek stop: maliyetin -%6,8'i (sinyal kapanışı).

    Periyot = max(10, 50 - girişten beri geçen mum); giriş sanal durumla izlenir (bkz. modül notu), çıkış sinyali o durumdan çıkar.

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: uyarlanır periyotlu çıkış sanal pozisyon yaşından hesaplanıyor; motorla ayrışırsa (reddedilen giriş, ayrı stop) yaş sapar."""

    ad, stil = "kapanis__uyarlanir-ma-kanal-s0189", "swing"
    varsayilan_parametreler = {"ma": 50, "sapma": 1.25, "roc": 30, "liq_min": 10, "sl": 0.068}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        n = int(p["ma"])
        ort = g.sma(kap, n)
        std = kap.rolling(n).std(ddof=0)
        ust, alt = ort + float(p["sapma"]) * std, ort - float(p["sapma"]) * std
        onceki = kap.shift(int(p["roc"]))
        gl = (kap > ust) & (kap > onceki)
        cl = (kap < onceki) & (kap < alt)
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        kv = kap.to_numpy(float)
        durum = {"e": 0}
        liq = int(p["liq_min"])

        def baslat(t, yon):
            durum["e"] = t

        def ek(t, yon):
            ma = _kayan_ort(kv, max(liq, n - (t - durum["e"])), t)
            return bool(np.isfinite(ma) and kv[t] < ma)

        vl, _, kl, _ = _sanal(m, gl, False, cl, False, sl, ss, baslat=baslat, ek=ek)
        return _cikti(m, vl, False, sl, ss, cl=_np(cl) | kl)


# ------------------------------------------------------------------ X005:192
class MaDizilimArS0192(Strateji):
    """HAM:X005:192 — 1d long: SMA(5) > SMA(10) > SMA(30) VE AR(26) < 75 -> long; çıkış SMA(5) < SMA(10) < SMA(30) VE AR(26) > 130; stop:
    maliyetin -%6,8'i (sinyal kapanışı); kâr >= %25 olunca zirveden %6,8 geri çekilmede kâr al (motor modülü, bkz. modül notu).
    AR(26) = Σ(yüksek-açılış) / Σ(açılış-düşük) x 100 (kaynakta formül yok, standart AR varsayıldı).

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek YÜKSEK (kaynak: en yüksek kapanış/zirve fiyatı), fark = giriş fiyatına göre kâr% farkı (kaynak: zirvenin %'si), kapanışta kontrol.
    AR formülü kaynakta yok, standart AR tanımı (emin_degil)."""

    ad, stil = "kapanis__ma-dizilim-ar-s0192", "swing"
    varsayilan_parametreler = {"ma1": 5, "ma2": 10, "ma3": 30, "ar_n": 26, "ar_giris": 75.0, "ar_cikis": 130.0, "sl": 0.068}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=25.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        a, b, c = (g.sma(kap, int(p[k])) for k in ("ma1", "ma2", "ma3"))
        n = int(p["ar_n"])
        pay = (m["yuksek"] - m["acilis"]).rolling(n).sum()
        payda = (m["acilis"] - m["dusuk"]).rolling(n).sum().replace(0.0, np.nan)
        ar = pay / payda * 100.0
        gir = (a > b) & (b > c) & (ar < float(p["ar_giris"]))
        cik = (a < b) & (b < c) & (ar > float(p["ar_cikis"]))
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:197
class TimsahDizilimS0197(Strateji):
    """HAM:X005:197 — 1d long Alligator: lips = SMA(5) 3 bar kaydırılmış, teeth = SMA(8) 5 bar, jaw = SMA(13) 8 bar (geriye kaydırma = t-shift
    değeri, nedensel); lips > teeth > jaw -> long; lips < teeth < jaw -> çık; arada pozisyon korunur. Fiyat = kapanış. Stop kaynakta yok:
    ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__timsah-dizilim-s0197", "swing"
    varsayilan_parametreler = {"dudak": 5, "dudak_k": 3, "dis": 8, "dis_k": 5, "ceneden": 13, "cene_k": 8, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        lips = g.sma(kap, int(p["dudak"])).shift(int(p["dudak_k"]))
        teeth = g.sma(kap, int(p["dis"])).shift(int(p["dis_k"]))
        jaw = g.sma(kap, int(p["ceneden"])).shift(int(p["cene_k"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, (lips > teeth) & (teeth > jaw), False, sl, ss, cl=(lips < teeth) & (teeth < jaw))


# ------------------------------------------------------------------ X005:208
class ZSkorOrtalamayaDonusS0208(Strateji):
    """HAM:X005:208 — 1d iki yön: z = (kapanış - ort14)/std14 (ddof=0, son 14 kapanış); flat: z < -1,8 long, z > 1,8 short; çıkış: |z| <= 0,4
    VEYA z giriş yönünde ±2,5 ötesi (long z < -2,5, short z > 2,5) VEYA >= 8 gün. Kaynak stopu z-stop; ayrıca ATR(14)x3 felaket stopu
    eklenir (uyarlama). "Çıkış mumunda yeni giriş yok" sırası (bkz. modül notu); 8 gün hem sanal durumda hem motorda sayılır."""

    ad, stil = "kapanis__z-skor-ort-donus-s0208", "swing"
    varsayilan_parametreler = {"win": 14, "giris_z": 1.8, "cikis_z": 0.4, "stop_z": 2.5, "zaman_gun": 8, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        w = int(p["win"])
        z = (kap - kap.rolling(w).mean()) / kap.rolling(w).std(ddof=0).replace(0.0, np.nan)
        gz, cz, sz = float(p["giris_z"]), float(p["cikis_z"]), float(p["stop_z"])
        gl, gs = z < -gz, z > gz
        cl = (z.abs() <= cz) | (z < -sz)
        cs = (z.abs() <= cz) | (z > sz)
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        zg = int(p["zaman_gun"])
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss, max_mum=zg)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks, zc=zg)


# ------------------------------------------------------------------ X005:209
class Rsi6DonusS0209(Strateji):
    """HAM:X005:209 — 1d iki yön: RSI(6); long giriş: önceki RSI < 35 ve şimdi RSI > 35; short: önceki RSI > 65 ve şimdi < 65; long çıkış RSI > 65
    VEYA giriş -%1 stop VEYA >= 10 gün; short çıkış RSI < 35 VEYA +%1 stop VEYA >= 10 gün. Wilder RSI. Kapanış bazlı %1 stop motorun bar
    içi stopuna uyarlandı (stop = sinyal kapanışı x 0,99 / 1,01)."""

    ad, stil = "kapanis__rsi6-donus-s0209", "swing"
    varsayilan_parametreler = {"rsi": 6, "alt": 35.0, "ust": 65.0, "stop_pct": 1.0, "zaman_gun": 10}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi"]))
        alt, ust = float(p["alt"]), float(p["ust"])
        gl = (r.shift(1) < alt) & (r > alt)
        gs = (r.shift(1) > ust) & (r < ust)
        sl, ss = _yuzde_stop(m, float(p["stop_pct"]) / 100.0)
        return _cikti(m, gl, gs, sl, ss, cl=r > ust, cs=r < alt, zc=int(p["zaman_gun"]))


# ------------------------------------------------------------------ X005:210
class Cci10DurumGecisS0210(Strateji):
    """HAM:X005:210 — 1d iki yön: CCI(10) durumu: > 100 = 1, < -100 = -1, arası 0; flat iken önceki durum -1 ve şimdi 0 -> long; önceki 1 ve şimdi 0
    -> short; long çıkış: önceki 1 ve şimdi 0 VEYA kapanış < giriş x 0,99; short çıkış: önceki -1 şimdi 0 VEYA kapanış > giriş x 1,01.
    Kapanış bazlı %1 stop motorun bar içi stopuna uyarlandı. Giriş olayı ters çıkış olayıyla aynı mumda doğar: "çıkış mumunda yeni giriş
    yok" sırası (bkz. modül notu); yani ters olay pozisyonu kapatır, çevirmez."""

    ad, stil = "kapanis__cci10-durum-gecis-s0210", "swing"
    varsayilan_parametreler = {"cci": 10, "ust": 100.0, "alt": -100.0, "stop_pct": 1.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        c = cci(m["yuksek"], m["dusuk"], m["kapanis"], int(p["cci"]))
        d = pd.Series(np.where(c.isna(), np.nan, np.where(c > float(p["ust"]), 1.0, np.where(c < float(p["alt"]), -1.0, 0.0))),
                      index=m.index)
        alttan = (d.shift(1) == -1) & (d == 0)
        ustten = (d.shift(1) == 1) & (d == 0)
        sl, ss = _yuzde_stop(m, float(p["stop_pct"]) / 100.0)
        vl, vs, kl, ks = _sanal(m, alttan, ustten, ustten, alttan, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(ustten) | kl, cs=_np(alttan) | ks)


# ------------------------------------------------------------------ X005:212
class Stokastik533S0212(Strateji):
    """HAM:X005:212 — 1d long: Stokastik(fastk 5, slowk 3, slowd 3): slowK < 25 VEYA slowD < 25 -> long; çıkış slowK > 75 VEYA slowD > 75 veya 22 gün
    sonra; stop maliyetin -%6,8'i (sinyal kapanışı); kâr >= %20 olunca zirveden %6,8 geri çekilmede kâr al (motor modülü, bkz. modül
    notu). slowK = SMA3(fastK), slowD = SMA3(slowK). Trend filtresi yok, durum tabanlı.

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek YÜKSEK (kaynak: en yüksek kapanış/zirve fiyatı), fark = giriş fiyatına göre kâr% farkı (kaynak: zirvenin %'si), kapanışta kontrol."""

    ad, stil = "kapanis__stokastik-533-s0212", "swing"
    varsayilan_parametreler = {"fastk": 5, "slowk": 3, "slowd": 3, "alt": 25.0, "ust": 75.0, "sl": 0.068}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=22, geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=20.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        st = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], int(p["fastk"]), int(p["slowk"]))
        k = st["d"]
        d = g.sma(k, int(p["slowd"]))
        gir = (k < float(p["alt"])) | (d < float(p["alt"]))
        cik = (k > float(p["ust"])) | (d > float(p["ust"]))
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, gir, False, sl, ss, cl=cik)


# ------------------------------------------------------------------ X005:213
class Rsi14Asiri2585S0213(Strateji):
    """HAM:X005:213 — 1d long: RSI(14) < 25 -> long; RSI(14) > 85 -> kapat; stop giriş maliyetinin -%6,8'i (sinyal kapanışı); kâr >= %35 olduktan
    sonra zirveden %6,8 iz süren çıkış (motor geri çekilme modülü, bkz. modül notu).

    YAKLAŞIK: pozisyon bilinçli çıkış modülü gelince yeniden yazılacak — fark: zirve = en yüksek YÜKSEK (kaynak: en yüksek kapanış/zirve fiyatı), fark = giriş fiyatına göre kâr% farkı (kaynak: zirvenin %'si), kapanışta kontrol."""

    ad, stil = "kapanis__rsi14-asiri-2585-s0213", "swing"
    varsayilan_parametreler = {"rsi": 14, "alt": 25.0, "ust_cikis": 85.0, "sl": 0.068}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=6.8, geri_cekilme_min_kar_yuzde=35.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi"]))
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, r < float(p["alt"]), False, sl, ss, cl=r > float(p["ust_cikis"]))


# ------------------------------------------------------------------ X005:215
class Rsi14Asiri3070S0215(Strateji):
    """HAM:X005:215 — 1d long: pozisyon yokken RSI(14) < 30 ise long; RSI(14) > 70 ise çık; sabit stop -%8 (sinyal kapanışından)."""

    ad, stil = "kapanis__rsi14-asiri-3070-s0215", "swing"
    varsayilan_parametreler = {"rsi": 14, "alt": 30.0, "ust": 70.0, "sl": 0.08}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi"]))
        sl, ss = _yuzde_stop(m, float(p["sl"]))
        return _cikti(m, r < float(p["alt"]), False, sl, ss, cl=r > float(p["ust"]))


# ------------------------------------------------------------------ X005:216
class BbAltOrtaCikisS0216(Strateji):
    """HAM:X005:216 — 1d long: kapanış < alt bant (SMA20 - 2σ) -> long; kapanış >= SMA20 -> çık. Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__bb-alt-orta-cikis-s0216", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_std": 2.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, kap < bb["alt"], False, sl, ss, cl=kap >= bb["orta"])


# ------------------------------------------------------------------ X005:217
class BbAltUstCikisS0217(Strateji):
    """HAM:X005:217 — 1d long: kapanış < alt BB(20,2) (durum, pozisyon yokken) -> long; çıkış kapanış > üst BB. Kaynak ATR(14)x2 stopu fiilen
    tetiklenmediği için kaynakta stop yok: ATR(14)x3 felaket stopu (uyarlama)."""

    ad, stil = "kapanis__bb-alt-ust-cikis-s0217", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_std": 2.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, kap < bb["alt"], False, sl, ss, cl=kap > bb["ust"])


# ------------------------------------------------------------------ X005:219
class Bb25KarsiBantS0219(Strateji):
    """HAM:X005:219 — 1d: SMA25 ± 2σ (25 gün); pozisyon yokken kapanış < -2σ ise long; kapanış >= +2σ ise short; long çıkış kapanış >= +2σ, short
    çıkış kapanış <= -2σ; aynı anda tek pozisyon. Stop kaynakta yok: ATR(14)x3 (uyarlama). Karşı banttaki giriş ile çıkış aynı mumda doğar:
    "çıkış mumunda yeni giriş yok" sırası (bkz. modül notu); çıkış pozisyonu kapatır, çevirmez."""

    ad, stil = "kapanis__bb25-karsi-bant-s0219", "swing"
    varsayilan_parametreler = {"bb_n": 25, "bb_std": 2.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        gl, gs = kap < bb["alt"], kap >= bb["ust"]
        cl, cs = kap >= bb["ust"], kap <= bb["alt"]
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        vl, vs, kl, ks = _sanal(m, gl, gs, cl, cs, sl, ss)
        return _cikti(m, vl, vs, sl, ss, cl=_np(cl) | kl, cs=_np(cs) | ks)


# ------------------------------------------------------------------ X005:222
class BbKurulumTeyit4hS0222(Strateji):
    """HAM:X005:222 — 4h BB(20, 2σ): long = mum düşüğü alt bandın altına iner (kurulum mumu) VE sonraki mumun kapanışı kurulum mumunun yükseğinin
    üstünde (teyit) -> sinyal teyit mumu kapanışında; çıkış = orta bant (SMA20) kapanmış mumun yükseği ile değince (long) -> sonraki açılış;
    stop = kurulum mumunun düşüğü (varyant A, `stop_varyant`="A") ya da teyit mumundan 2 önceki mumun düşüğü (varyant B); short ayna (üst
    bant, yüksekten düşük kapanış, orta banda düşük değmesi, stop yüksek). Stop yanlış tarafta kalırsa sinyal düşer (`cerceve`).
    Bar içi dokunuş yerine kapanmış mum uyarlaması; kaynaktaki isteğe bağlı 1,5 kat stop mesafesi çıkışı uygulanmadı."""

    ad, stil = "kapanis__bb-kurulum-teyit-4h-s0222", "swing"
    varsayilan_parametreler = {"bb_n": 20, "bb_std": 2.0, "stop_varyant": "A"}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["stop_varyant"] not in ("A", "B"):
            raise ValueError("stop_varyant A veya B olmalı")
        kap, h, lo = m["kapanis"], m["yuksek"], m["dusuk"]
        bb = _bant(m, int(p["bb_n"]), float(p["bb_std"]))
        kurulum_l = (lo < bb["alt"]).shift(1, fill_value=False)
        kurulum_s = (h > bb["ust"]).shift(1, fill_value=False)
        gl = kurulum_l & (kap > h.shift(1))
        gs = kurulum_s & (kap < lo.shift(1))
        geri = 1 if p["stop_varyant"] == "A" else 2
        return _cikti(m, gl, gs, lo.shift(geri), h.shift(geri), cl=h >= bb["orta"], cs=lo <= bb["orta"])


# ------------------------------------------------------------------ X005:229
class Rsi3CokluTf15mS0229(Strateji):
    """HAM:X005:229 — 15m long: 4h RSI(3) < 20 VE yukarı dönüyor (RSI[0] > RSI[1], kapanmış 4h mum); 15m RSI(3) 20'nin altından üstüne çıkınca long;
    stop RSI'nin 20'yi yukarı kestiği mumun dibi; hedef 1,5 x stop mesafesi; short ayna (80, mumun tepesi). 4h değer `htf.ust_zaman` ile yalnız
    kapanmış 4h mumdan. Hedef = kapanış +/- 1,5 x (kapanış - stop). Yukarı/aşağı kesiş: önceki <= / >= eşik, şimdi > / < eşik."""

    ad, stil = "kapanis__rsi3-coklu-tf-15m-s0229", "daytrade"
    varsayilan_parametreler = {"rsi": 3, "alt": 20.0, "ust": 80.0, "filtre_tf": "4h", "hedef_r": 1.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        n = int(p["rsi"])
        kap, h, lo = m["kapanis"], m["yuksek"], m["dusuk"]

        def fonk(u: pd.DataFrame) -> pd.DataFrame:
            r = g.rsi(u["kapanis"], n)
            return pd.DataFrame({"r": r, "rp": r.shift(1)})

        f = ust_zaman(m, str(p["filtre_tf"]), fonk)
        alt, ust = float(p["alt"]), float(p["ust"])
        r15 = g.rsi(kap, n)
        gl = (f["r"] < alt) & (f["r"] > f["rp"]) & yukari_kesis(r15, alt)
        gs = (f["r"] > ust) & (f["r"] < f["rp"]) & asagi_kesis(r15, ust)
        r = float(p["hedef_r"])
        return _cikti(m, gl, gs, lo, h, hedef_l=kap + r * (kap - lo), hedef_s=kap - r * (h - kap))


# ------------------------------------------------------------------ X005:234
class Sma2060KesisS0234(Strateji):
    """HAM:X005:234 (K6_STANDART, TF eksik: 4h ve 1d iki hipotez) — SMA(20) SMA(60)'ı yukarı keserse long (sinyal kapanmış mum, dolum sonraki
    açılış); SMA(20) SMA(60)'ın altına inince long kapanır; short yok. Giriş kesişim olayı, çıkış durum (kesişimden sonra durum aynıdır).
    Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__sma20-60-kesis-s0234", "swing"
    varsayilan_parametreler = {"sma_hizli": 20, "sma_yavas": 60, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        hizli, yavas = g.sma(kap, int(p["sma_hizli"])), g.sma(kap, int(p["sma_yavas"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, yukari_kesis(hizli, yavas), False, sl, ss, cl=hizli < yavas)


# ------------------------------------------------------------------ X005:241
class Sma75AsagiKesisS0241(Strateji):
    """HAM:X005:241 — 1d long: kapanış SMA(75) altına inince (önceki kapanış >= SMA, şimdi < SMA) ertesi açılışta long; 30 takvim günü (1d mum)
    sonra çık. Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__sma75-asagi-kesis-s0241", "swing"
    varsayilan_parametreler = {"sma_n": 75, "tutma_gun": 30, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        sma = g.sma(kap, int(p["sma_n"]))
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, (kap.shift(1) >= sma.shift(1)) & (kap < sma), False, sl, ss, zc=int(p["tutma_gun"]))


# ------------------------------------------------------------------ X005:244
class GunIciHacimKirilimS0244(Strateji):
    """HAM:X005:244 — 1h long: gün (UTC; seans = KST 09:00 = UTC 00:00) içinde mum kapanışı > gün açılışı + 0,5 x (önceki günün yüksek-düşük
    aralığı) -> seansta İLK tetikte long (filtresiz); çıkış her gün seans başında. Kaynak anlık dokunuş; burada gün içi kapanış doğrulaması.
    Günün son mumunda yeni giriş yok, günün son mumu çıkış sinyali verir (sonraki açılış = yeni seans başı). Stop kaynakta yok: ATR(14)x3
    (uyarlama). Önceki gün aralığı yalnız tamamlanmış önceki günden alınır."""

    ad, stil = "kapanis__gun-ici-kirilim-1h-s0244", "daytrade"
    varsayilan_parametreler = {"k": 0.5, "seans_saat": 0.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = m["kapanis"]
        gun = (m.index - pd.Timedelta(hours=float(p["seans_saat"]))).floor("D")
        acilis_gun = m["acilis"].groupby(gun).transform("first")
        ozet = pd.DataFrame({"h": m["yuksek"].groupby(gun).max(), "l": m["dusuk"].groupby(gun).min()})
        onceki = (ozet["h"] - ozet["l"]).shift(1).reindex(gun).to_numpy()
        tetik = pd.Series(kap.to_numpy() > acilis_gun.to_numpy() + float(p["k"]) * onceki, index=m.index)
        ilk = tetik & (tetik.astype(int).groupby(gun).cumsum() == 1)
        son = pd.Series(seans_son_mumu(m.index, float(p["seans_saat"])), index=m.index)
        sl, ss = _atr_stop(m, int(p["atr_n"]), float(p["atr_k"]))
        return _cikti(m, ilk & ~son, False, sl, ss, cl=son)


# ------------------------------------------------------------------ kayıtlar
KODLANAMADI = [
    {"kimlik": "HAM:X005:114",
     "neden": ("iki kademeli çıkış motorda ifade edilemiyor: lot1 hedefi dinamik orta bant (SMA20) ve hedef sonrası kalan lotun stopunun "
               "başabaşa çekilmesi, lot2 karşı 2,5σ bantta kapanış çıkışı; motorun kısmi çıkışı yalnız sabit R çarpanıyla "
               "(CikisAyarlari.kismi), başabaşı yalnız R eşiğiyle çalışır, bant tabanlı kısmi hedef yok; tek lota indirgemek kuralı değiştirir")},
]


def _v(kaynak_id, sinif, parametreler, tf, sira=1):
    return {"kimlik": f"{kaynak_id}#v{sira}", "sinif": sinif.ad, "parametreler": parametreler, "tf": tf}


def _liste():
    s = []
    t = lambda *a, **k: s.append(_v(*a, **k))  # noqa: E731
    t("HAM:X005:85", MacdSma200SarS0085, {"hizli": 12, "yavas": 26, "sinyal": 9, "sma_n": 200}, "4h")
    t("HAM:X005:95", SupertrendAdxS0095, {"st_atr": 10, "st_carpan": 3.0, "adx_n": 14, "adx_giris": 23.0, "adx_cikis": 18.0,
                                          "stop_atr": 2.0, "stop_atr_n": 10}, "4h")
    t("HAM:X005:97", IbsBantDonusS0097, {"tepe_gun": 10, "aralik_gun": 25, "carpan": 2.5, "ibs_max": 0.3}, "1d")
    t("HAM:X005:104", YediGunDipSma200S0104, {"pencere": 7, "trend_n": 200, "cikis_sma": 5}, "1d")
    t("HAM:X005:108", Rsi2Sma200S0108, {"rsi_n": 2, "alt": 5.0, "trend_n": 200, "cikis_sma": 5}, "1d")
    t("HAM:X005:115", BbRsiOrtaBantS0115, {"bb_n": 30, "bb_std": 2.0, "rsi_n": 13, "rsi_alt": 30.0, "rsi_ust": 70.0}, "1d")
    t("HAM:X005:118", Rsi2Sma50S0118, {"ma_n": 50, "rsi_n": 2, "rsi_giris": 30.0, "rsi_cikis": 80.0}, "1d")
    t("HAM:X005:136", HaftalikKapanisKanaliS0136, {"giris_n": 20, "cikis_n": 20}, "1d")
    for i, gun in enumerate((1, 3, 5, 10, 20, 30, 60, 90), 1):
        t("HAM:X005:138", SmaKesisSabitTutmaS0138, {"sma_hizli": 10, "sma_yavas": 50, "tutma_gun": gun}, "1d", i)
    t("HAM:X005:141", AylikSma10GtaaS0141, {"ay_n": 10}, "1d")
    for i, (hc, yc) in enumerate(((3, 12), (8, 32), (32, 128)), 1):
        t("HAM:X005:144", EwmaKutleMerkeziS0144, {"hizli_com": hc, "yavas_com": yc}, "1d", i)
    t("HAM:X005:147", TumZamanZirveIzS0147, {"atr_n": 14, "atr_k": 10.0}, "1d")
    t("HAM:X005:173", DualThrustS0173, {"nday": 5, "k1": 0.2, "k2": 0.2}, "1d")
    t("HAM:X005:174", Keltner5mIzYuzdeS0174, {"n": 11, "carpan": 1.6, "iz_yuzde": 0.008}, "5m")
    t("HAM:X005:177", BollingerCci15mS0177, {"bb_n": 18, "bb_std": 3.4, "cci_n": 10, "iz_atr_n": 30, "iz_atr_k": 5.2}, "15m")
    t("HAM:X005:181", BbBreakoutOrtaBantS0181, {"bb_n": 26, "bb_std": 2.0}, "1d")
    t("HAM:X005:182", AroonKesisS0182, {"aroon": 10, "ust": 75.0, "alt": 25.0, "stop_pct": 1.2}, "1d")
    t("HAM:X005:183", EmaAtrBantS0183, {"ema_n": 8, "ema_kisa": 5, "atr_n": 7, "mult": 1.5, "mult_guclu": 1.2,
                                       "guc_esik_pct": 0.5, "stop_atr": 0.8}, "1d")
    t("HAM:X005:185", HmaAtrKesisS0185, {"hizli": 5, "yavas": 30, "atr_n": 14, "stop_atr": 2.0, "tp_pct": 3.0}, "1d")
    t("HAM:X005:186", BbBantYonuS0186, {"bb_n": 22, "bb_std": 2.0, "yon_gun": 3}, "1d")
    t("HAM:X005:187", SmaKesisAdxDiS0187, {"ma_hizli": 5, "ma_yavas": 20, "adx_n": 14, "sl": 0.068}, "1d")
    t("HAM:X005:188", AtrKirilimS0188, {"atr_n": 14, "carpan": 2.0, "sl": 0.068}, "1d")
    t("HAM:X005:189", UyarlanirMaKanalS0189, {"ma": 50, "sapma": 1.25, "roc": 30, "liq_min": 10, "sl": 0.068}, "1d")
    t("HAM:X005:192", MaDizilimArS0192, {"ma1": 5, "ma2": 10, "ma3": 30, "ar_n": 26, "ar_giris": 75.0, "ar_cikis": 130.0,
                                        "sl": 0.068}, "1d")
    t("HAM:X005:197", TimsahDizilimS0197, {"dudak": 5, "dudak_k": 3, "dis": 8, "dis_k": 5, "ceneden": 13, "cene_k": 8}, "1d")
    t("HAM:X005:208", ZSkorOrtalamayaDonusS0208, {"win": 14, "giris_z": 1.8, "cikis_z": 0.4, "stop_z": 2.5, "zaman_gun": 8}, "1d")
    t("HAM:X005:209", Rsi6DonusS0209, {"rsi": 6, "alt": 35.0, "ust": 65.0, "stop_pct": 1.0, "zaman_gun": 10}, "1d")
    t("HAM:X005:210", Cci10DurumGecisS0210, {"cci": 10, "ust": 100.0, "alt": -100.0, "stop_pct": 1.0}, "1d")
    t("HAM:X005:212", Stokastik533S0212, {"fastk": 5, "slowk": 3, "slowd": 3, "alt": 25.0, "ust": 75.0, "sl": 0.068}, "1d")
    t("HAM:X005:213", Rsi14Asiri2585S0213, {"rsi": 14, "alt": 25.0, "ust_cikis": 85.0, "sl": 0.068}, "1d")
    t("HAM:X005:215", Rsi14Asiri3070S0215, {"rsi": 14, "alt": 30.0, "ust": 70.0, "sl": 0.08}, "1d")
    t("HAM:X005:216", BbAltOrtaCikisS0216, {"bb_n": 20, "bb_std": 2.0}, "1d")
    t("HAM:X005:217", BbAltUstCikisS0217, {"bb_n": 20, "bb_std": 2.0}, "1d")
    t("HAM:X005:219", Bb25KarsiBantS0219, {"bb_n": 25, "bb_std": 2.0}, "1d")
    for i, v in enumerate(("A", "B"), 1):
        t("HAM:X005:222", BbKurulumTeyit4hS0222, {"bb_n": 20, "bb_std": 2.0, "stop_varyant": v}, "4h", i)
    t("HAM:X005:229", Rsi3CokluTf15mS0229, {"rsi": 3, "alt": 20.0, "ust": 80.0, "filtre_tf": "4h", "hedef_r": 1.5}, "15m")
    for i, tf in enumerate(("4h", "1d"), 1):
        t("HAM:X005:234", Sma2060KesisS0234, {"sma_hizli": 20, "sma_yavas": 60}, tf, i)
    t("HAM:X005:241", Sma75AsagiKesisS0241, {"sma_n": 75, "tutma_gun": 30}, "1d")
    t("HAM:X005:244", GunIciHacimKirilimS0244, {"k": 0.5, "seans_saat": 0.0}, "1h")
    return s


VARYANTLAR = _liste()
_YAKLASIK = {"HAM:X005:" + k for k in ("174", "185", "186", "187", "188", "189", "192", "212", "213")}
for _k in VARYANTLAR:
    if _k["kimlik"].split("#")[0] in _YAKLASIK:
        _k["yaklasik"] = True
    if _k["kimlik"].split("#")[0] == "HAM:X005:192":
        _k["emin_degil"] = True
