"""D10-B — stratejiler/ek_kaynaklar/kodlama_kuyrugu_2026-11-07.csv'deki b payı yeni_aile satırlarının KODU (kitap kartları,
repo kodları / raporları). KOD KOPYALANMADI: kaynak metinler VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__`.
Hepsi nedensel (lookahead yok): sinyal bar kapanışında, dolum motorda sonraki açılışta; pivotlar gecikmeli onaylı; haftalık /
günlük üst TF değerleri yalnız KAPANMIŞ bar için (`_gosterge_d10b.haftalik_ust / gun_ust`).

Sınıf (kuyruk ailesi) — stil:
  dis__fib-kanali-donus (swing)            dis__lrc-wma-kesisim (swing)             dis__swing-asim-mesafesi (swing)
  dis__trend-cizgisi-kirilim-retest (swing) dis__ust-tf-trend-60dk-donus (swing)    dis__paskalya-takvim (swing)
  dis__adx-di-esik-kesisimi (swing)        dis__codex-wd-cift-momentum (swing)      dis__codex-wd-gunluk-donus (swing)
  dis__codex-wd-gunluk-momentum (swing)    dis__codex-wd-hacim-akisi (swing)        dis__codex-wd-kama-verimlilik (swing)
  dis__osilator-esik-birlesimi (swing)     dis__voltran-1a (swing)                  dis__voltran-1b (swing)
  dis__voltran-r1 (swing)                  dis__z65-rejim (swing)

KODLANMAYANLAR (stratejiler/kodlama_2026-11-07_d10b.csv): gecelik-gunici-etki (kurala_dokulemez: kapanis->acilis ayrimi motor
modeliyle temsil edilemez, kurallar uyelere ozel), autotune-filtre (kurala_dokulemez: giris/cikis kurali ve filtre formulu yok),
osma-sinyal (mevcut:scalp__macd-sinyal), ulke-etf-pairs (mevcut:pf__pairs).

Ortak uyarlamalar
  * Stopu olmayan kurallara ATR stopu eklendi; her sınıfın docstring'inde "VARSAYIM" olarak yazılıdır.
  * Risk/pozisyon boyutu (özsermayenin %0,5'i, toplam %2) motor / portföy katmanının işidir, burada yok.
  * Kâr kilidi (başabaş) motordaki `basabas_r_esigi` ile (stop girişe, orijinaldeki +%0,5 değil), iz süren stop `atr_iz_suren_k`
    ile (zirveden k x ATR) yaklaşıldı.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import kur, linreg, wma
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban, cmf
from motor.strateji.dis._gosterge_d5 import kama
from motor.strateji.gostergeler_b2 import asagi_kesis, yukari_kesis
from motor.strateji.temel import Strateji

from ._gosterge_d9 import r_hedefi
from ._gosterge_d10b import (
    adl, boga_yutan, ayi_yutan, gun_ust, haftalik_ust, ibs, obv, paskalya_kalan_gun, pivot_noktalari,
    verimlilik_orani)


def _bos(index):
    return pd.Series(False, index=index)


def _yok(index):
    return pd.Series(np.nan, index=index)


def _sadece_long(m, long_ok, stop_l, hedef_l=None, cikis_l=None, zaman_cikisi=None):
    return kur(m, long_ok, _bos(m.index), stop_l, _yok(m.index), hedef_l, None, cikis_l, None, zaman_cikisi=zaman_cikisi)


# =============================================================================== 1. Fib kanalı
class FibKanaliDonus(Strateji):
    """dis__fib-kanali-donus (swing, 1d) — kart swing__fib-kanali-ma89-ortalamaya-donus__arps.
    Kural: MA(89) etrafında Fibonacci kanalı: bant = MA +/- fib_k x ATR(atr_n) (fib_k Fibonacci sayısı: 1.618 / 2.618 /
    4.236; kitapta formül yok -> ATR tabanlı kanal VARSAYIM, "SCALING 1-3" fib_k ile temsil edilir). Kapanış alt dış bandın
    dışına çıkıp (önceki kapanış < alt bant) bu mumda bant İÇİNE dönerse long; üst dış bandın dışından dönerse short. Hedef =
    karşı dış bant (kitap) ya da orta (hedef="orta"). Stop kitapta yok -> iki mumun dışa uç noktası -/+ tampon x ATR (VARSAYIM)."""
    ad = "dis__fib-kanali-donus"
    stil = "swing"
    varsayilan_parametreler = {"ma_n": 89, "atr_n": 21, "fib_k": 2.618, "tampon_atr": 0.25, "hedef": "karsi", "short": True}
    parametre_izgarasi = {"ma_n": [55, 89, 144], "fib_k": [1.618, 2.618, 4.236], "hedef": ["karsi", "orta"]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        ma = g.sma(k, int(p["ma_n"]))
        atr = g.atr(y, d, k, int(p["atr_n"]))
        ust, alt = ma + p["fib_k"] * atr, ma - p["fib_k"] * atr
        gecerli = ma.notna() & atr.notna()
        long_ok = (k.shift(1) < alt.shift(1)) & (k >= alt) & gecerli
        short_ok = (k.shift(1) > ust.shift(1)) & (k <= ust) & gecerli & bool(p["short"])
        stop_l = np.minimum(d, d.shift(1)) - p["tampon_atr"] * atr
        stop_s = np.maximum(y, y.shift(1)) + p["tampon_atr"] * atr
        h_l, h_s = (ust, alt) if p["hedef"] == "karsi" else (ma, ma)
        long_ok &= h_l > k
        short_ok &= h_s < k
        return kur(m, long_ok, short_ok, stop_l, stop_s, h_l, h_s)


# =============================================================================== 2. LRC / WMA
class LrcWmaKesisim(Strateji):
    """dis__lrc-wma-kesisim (swing, 1h) — kart swing__lrc-wma-kesisim-rsi-adx__dolzhenko (Dolzhenko, bot mimarisi örneği).
    Kural (long-only): LRC(n) > WMA(n) (şu anki mumda) VE son 3 mumda RSI < 30 VE BBW(20,2)=(üst-alt)/orta bu mumda 0.04'ü
    yukarı geçti (önceki mumda < 0.04) VE ADX(14) > 30. Çıkış sinyali: LRC < WMA VE son 3 mumda RSI > 70.
    VARSAYIM: kitapta tüm periyotlar "Const"; LRC=doğrusal regresyon çizgisinin son noktası ve WMA aynı n=25; RSI14, BB 20/2;
    stop kitapta yok -> 2 ATR. Kartta not: giriş (RSI<30) ve çıkış (RSI>70) koşulları çelişkili görünüyor, olduğu gibi kodlandı."""
    ad = "dis__lrc-wma-kesisim"
    stil = "swing"
    varsayilan_parametreler = {"n": 25, "rsi_n": 14, "rsi_alt": 30.0, "rsi_ust": 70.0, "rsi_pencere": 3, "bb_n": 20,
                               "bbw_esik": 0.04, "adx_n": 14, "adx_esik": 30.0, "stop_atr_k": 2.0, "atr_n": 14}
    parametre_izgarasi = {"n": [14, 25, 50], "adx_esik": [20.0, 25.0, 30.0], "bbw_esik": [0.02, 0.04, 0.06]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n, w = int(p["n"]), int(p["rsi_pencere"])
        lrc, w_ma = linreg(k, n), wma(k, n)
        r = g.rsi(k, int(p["rsi_n"]))
        bb = g.bollinger(k, int(p["bb_n"]), 2.0)
        bbw = (bb["ust"] - bb["alt"]) / bb["orta"]
        adx = g.adx(y, d, k, int(p["adx_n"]))["adx"]
        atr = g.atr(y, d, k, int(p["atr_n"]))
        long_ok = ((lrc > w_ma) & (r.rolling(w, min_periods=w).min() < p["rsi_alt"])
                   & (bbw > p["bbw_esik"]) & (bbw.shift(1) < p["bbw_esik"]) & (adx > p["adx_esik"]))
        cikis = (lrc < w_ma) & (r.rolling(w, min_periods=w).max() > p["rsi_ust"])
        return _sadece_long(m, long_ok & atr.notna(), k - p["stop_atr_k"] * atr, cikis_l=cikis)


# =============================================================================== 3. Swing aşım mesafesi
def _swing_asim_dizisi(o, h, l, c, atr, pn, esik, bolge, bekle, tampon, onay, yutan):
    """Long mantığı (short için fiyatlar negatiflenip çağrılır). -> (sinyal bool[], stop float[])."""
    n = len(c)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    pl = pivot_noktalari(pd.Series(l), pn, False).to_numpy()
    ph = pivot_noktalari(pd.Series(h), pn, True).to_numpy()
    son_dip = son_tepe = np.nan
    kur_ = None            # [dip, tepe, son_mum, bolgeye_girdi]
    for t in range(n):
        if not np.isnan(ph[t]):
            son_tepe = ph[t]
        if not np.isnan(pl[t]) and pl[t] != son_dip:        # eşit değerli tekrar pivot (plato) yeni pivot sayılmaz
            yeni = pl[t]
            if not np.isnan(son_dip) and not np.isnan(atr[t]) and 0.0 < son_dip - yeni <= esik * atr[t]:
                kur_ = [yeni, son_tepe, t + bekle, False]      # önceki dibi KÜÇÜK aşan yeni swing dibi: olası dönüş
            else:
                kur_ = None                                      # büyük aşım (devam) ya da aşım yok: dönüş kurulumu iptal
            son_dip = yeni
        if kur_ is None or np.isnan(atr[t]):
            continue
        dip, tepe, son, girdi = kur_
        if t > son or c[t] < dip - tampon * atr[t]:
            kur_ = None
            continue
        if l[t] <= dip + bolge * atr[t]:
            kur_[3] = girdi = True
        tetik = (girdi and l[t] <= dip + bolge * atr[t] and yutan[t]) if onay == "yutan" \
            else (girdi and not np.isnan(tepe) and c[t] > tepe)
        if tetik:
            sig[t] = True
            stop[t] = dip - tampon * atr[t]
            kur_ = None
    return sig, stop


class SwingAsimMesafesi(Strateji):
    """dis__swing-asim-mesafesi (swing, 1h; kartta 4h onayı) — kart swing__swing-asimi-donus-devam__anonim.
    Ölçülebilir tanım: swing dip/tepe = pivot_n mumluk onaylı pivot (pivot_n mum gecikmeli). Yeni swing dibi önceki swing
    dibini 0 < fark <= esik_atr x ATR kadar AŞARSA "olası dönüş" kurulumu açılır (kart: 35-50 pip -> ATR'ye çevrildi; büyük aşım
    = trend devamı, kurulum iptal). Bölge = swing dibi +/- bolge_atr x ATR. Fiyat bölgeye inince, onay="yutan": o mumda boğa
    yutan mum ; onay="tepe": (bölgeye girdikten sonra) kapanış, düşüş sırasındaki swing tepesini aşar -> long. Kurulum
    `bekle` mum sonra ya da kapanış swing dibi - tampon x ATR altına inerse iptal. Short ayna (tepe aşımı).
    Stop = swing dibi - tampon x ATR (kart). Hedef kitapta yok -> hedef_r x R (VARSAYIM 2R)."""
    ad = "dis__swing-asim-mesafesi"
    stil = "swing"
    varsayilan_parametreler = {"pivot_n": 5, "esik_atr": 3.0, "bolge_atr": 0.5, "bekle": 30, "tampon_atr": 0.25,
                               "onay": "yutan", "hedef_r": 2.0, "atr_n": 14, "short": True}
    parametre_izgarasi = {"pivot_n": [3, 5, 8], "esik_atr": [2.0, 3.0, 4.0], "onay": ["yutan", "tepe"]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        o, h, l, c = (m[x].to_numpy(dtype=float) for x in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"])).to_numpy()
        arg = (int(p["pivot_n"]), float(p["esik_atr"]), float(p["bolge_atr"]), int(p["bekle"]), float(p["tampon_atr"]),
               p["onay"])
        yut_b = boga_yutan(m).to_numpy()
        sl, stl = _swing_asim_dizisi(o, h, l, c, atr, *arg, yut_b)
        if p["short"]:
            ss, sts = _swing_asim_dizisi(-o, -l, -h, -c, atr, *arg, ayi_yutan(m).to_numpy())
        else:
            ss, sts = np.zeros(len(c), dtype=bool), np.full(len(c), np.nan)
        idx = m.index
        out = kur(m, pd.Series(sl, index=idx), pd.Series(ss, index=idx), pd.Series(stl, index=idx),
                  pd.Series(-sts, index=idx))
        return r_hedefi(out, m["kapanis"], float(p["hedef_r"]))


# =============================================================================== 4. Trend çizgisi kırılım + retest
def _trend_kirilim_dizisi(o, h, l, c, atr, pn, guclu, bekle, tampon, tol, yutan):
    """Long (düşüş trend çizgisi yukarı kırılır). Short için fiyatlar negatiflenerek çağrılır. -> (sinyal, stop)."""
    n = len(c)
    sig = np.zeros(n, dtype=bool)
    stop = np.full(n, np.nan)
    pv = pivot_noktalari(pd.Series(h), pn, True).to_numpy()
    govde = c - o
    aralik = h - l
    guclu_mum = (govde > 0) & (govde >= guclu * np.where(aralik > 0, aralik, np.nan)) & (govde > h - c) & (govde > o - l)
    tepeler = []
    cizgi = None           # (egim, ankraj_i, ankraj_v, H2)
    kirilim = None         # (egim, ankraj_i, ankraj_v, son_mum)
    for t in range(n):
        if not np.isnan(pv[t]) and not (tepeler and tepeler[-1][1] == pv[t]):   # plato tekrarı yeni pivot sayılmaz
            tepeler.append((t - pn, pv[t]))
            tepeler = tepeler[-2:]
            cizgi = None
            if len(tepeler) == 2 and tepeler[1][1] < tepeler[0][1] and not np.isnan(atr[t]):
                (i1, v1), (i2, v2) = tepeler
                egim = (v2 - v1) / (i2 - i1)
                ara = np.arange(i1 + 1, i2)
                # çizgi mumları kesmemeli: arada hiçbir zirve çizginin tol x ATR üstüne çıkmaz
                if len(ara) == 0 or np.all(h[i1 + 1:i2] <= v1 + egim * (ara - i1) + tol * atr[t]):
                    cizgi = (egim, i2, v2)
        if np.isnan(atr[t]) or t == 0:
            continue
        if kirilim is not None:
            egim, ai, av, son = kirilim
            cv = av + egim * (t - ai)
            if t > son or c[t] < cv - atr[t]:
                kirilim = None
            elif l[t] <= cv + tol * atr[t] and yutan[t] and c[t] > cv:
                sig[t] = True
                stop[t] = min(l[t], l[t - 1]) - tampon * atr[t]
                kirilim = None
            continue
        if cizgi is not None:
            egim, ai, av = cizgi
            cv, cv1 = av + egim * (t - ai), av + egim * (t - 1 - ai)
            if c[t] > cv and c[t - 1] <= cv1 and guclu_mum[t] and c[t] > av:
                kirilim = (egim, ai, av, t + bekle)
                cizgi = None
    return sig, stop


class TrendCizgisiKirilimRetest(Strateji):
    """dis__trend-cizgisi-kirilim-retest (swing, 4h) — kart swing__trend-cizgisi-kirilimi-yeniden-test__brown (Danq Brown).
    Ölçülebilir tanım: "geçerli ayı dalgaları" = pivot_n mumluk onaylı pivot tepeleri; çizgi = SON İKİ pivot tepeden geçen doğru,
    ikincisi birinciden DÜŞÜK olmalı (daha düşük tepe) ve iki pivot arasındaki zirveler çizginin tol_atr x ATR üstüne çıkmamalı
    ("mumları kesmeyen"). Kırılım: kapanış çizgiyi yukarı geçer (önceki kapanış altında), mum "güçlü" = yeşil, gövde >= guclu_oran x
    aralık ve gövde iki fitilden de büyük (kart), ve kapanış son düşük tepeyi aşar (daha yüksek tepe). Yeniden test: kırılımdan
    sonra `bekle` mum içinde bir mum çizgiye tol_atr x ATR yaklaşıp BOĞA YUTAN mum olarak çizgi üstünde kapanırsa long (kart: yutan
    mumun açıldığı yerde = sonraki açılış). Kapanış çizginin 1 ATR altına inerse kurulum düşer. Short ayna (yükselen çizgi, ayı
    yutan). Stop = yutan mum ve önceki mumun ucu -/+ tampon x ATR (kart). Hedef yok; kart: 50 pip kârda başabaş + trend izleyen
    stop -> CikisAyarlari(başabaş 1R, iz süren 3 ATR) (VARSAYIM: 50 pip -> 1R, çizgi izleme -> ATR izi)."""
    ad = "dis__trend-cizgisi-kirilim-retest"
    stil = "swing"
    varsayilan_parametreler = {"pivot_n": 5, "guclu_oran": 0.6, "bekle": 20, "tampon_atr": 0.25, "tol_atr": 0.3,
                               "atr_n": 14, "short": True}
    parametre_izgarasi = {"pivot_n": [3, 5, 8], "guclu_oran": [0.5, 0.6, 0.7], "bekle": [10, 20, 30]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0, basabas_r_esigi=1.0)

    def sinyaller(self, m):
        p = self.parametreler
        o, h, l, c = (m[x].to_numpy(dtype=float) for x in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"])).to_numpy()
        arg = (int(p["pivot_n"]), float(p["guclu_oran"]), int(p["bekle"]), float(p["tampon_atr"]), float(p["tol_atr"]))
        sl, stl = _trend_kirilim_dizisi(o, h, l, c, atr, *arg, boga_yutan(m).to_numpy())
        if p["short"]:
            ss, sts = _trend_kirilim_dizisi(-o, -l, -h, -c, atr, *arg, ayi_yutan(m).to_numpy())
        else:
            ss, sts = np.zeros(len(c), dtype=bool), np.full(len(c), np.nan)
        idx = m.index
        return kur(m, pd.Series(sl, index=idx), pd.Series(ss, index=idx), pd.Series(stl, index=idx),
                   pd.Series(-sts, index=idx))


# =============================================================================== 5. Üst TF trend + 60dk dönüş
class UstTfTrend60dkDonus(Strateji):
    """dis__ust-tf-trend-60dk-donus (swing, 60m; günlük süzgeç) — kart swing__trend-duzeltme-60dk__leandro (Kurulum 2).
    Ölçülebilir tanım (long-only; kart short vermiyor):
      * Günlük "güçlü yükseliş" = 4 faktörden en az faktor_min: kapanış > SMA21, SMA21 3 gün öncesinden yüksek, SMA21 > SMA50,
        kapanış 20 gün öncesinden yüksek (kart: en az 3 faktör, fiyat>MM21, yükselen MM'ler). Günlük bilgi ertesi gün 00:00 UTC'den.
      * Düzeltme desteğe döndü = son duz_gun günün en düşüğü SMA21 + destek_atr x günlük ATR'nin altına indi (kart: önceki dip / MM).
      * 60dk boğa pivotu = kapanış, önceki pivot_n mumun zirvesini aşar, mum yeşil, Bollinger genişliği bb_gerisi mum öncesinden
        büyük (bant açılışı) ve hacim > hacim_k x SMA20(hacim).
    Stop = son duz_saat mumun dibi - 0.25 x ATR (kart: düzeltme dibinin altı); risk > maks_risk_atr x ATR ise işlem yok.
    Hedef: kart "Kurulum 1 kısmi kâr" (kitapta sayı yok) -> VARSAYIM hedef_r x R + başabaş 1R + 3 ATR iz süren stop."""
    ad = "dis__ust-tf-trend-60dk-donus"
    stil = "swing"
    varsayilan_parametreler = {"faktor_min": 3, "duz_gun": 5, "destek_atr": 1.0, "pivot_n": 8, "bb_n": 20, "bb_gerisi": 4,
                               "hacim_k": 1.5, "duz_saat": 24, "maks_risk_atr": 6.0, "hedef_r": 3.0, "atr_n": 14}
    parametre_izgarasi = {"destek_atr": [0.5, 1.0, 1.5], "hacim_k": [1.0, 1.5, 2.0], "pivot_n": [5, 8, 12]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0, basabas_r_esigi=1.0)

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        dg = int(p["duz_gun"])

        def gunluk(u):
            s21, s50 = g.sma(u["kapanis"], 21), g.sma(u["kapanis"], 50)
            atr = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], 14)
            f = ((u["kapanis"] > s21).astype(float) + (s21 > s21.shift(3)).astype(float) + (s21 > s50).astype(float)
                 + (u["kapanis"] > u["kapanis"].shift(20)).astype(float))
            f = f.where(s50.notna() & u["kapanis"].shift(20).notna())
            destek = u["dusuk"].rolling(dg, min_periods=dg).min() <= s21 + p["destek_atr"] * atr
            return pd.DataFrame({"faktor": f, "destek": destek.astype(float).where(atr.notna())})

        gn = gun_ust(m, gunluk)
        trend_ok = (gn["faktor"] >= p["faktor_min"]) & (gn["destek"] > 0.5)
        pn = int(p["pivot_n"])
        kirilim = k > y.shift(1).rolling(pn, min_periods=pn).max()
        bb = g.bollinger(k, int(p["bb_n"]), 2.0)
        bbw = (bb["ust"] - bb["alt"]) / bb["orta"]
        bant_acilis = bbw > bbw.shift(int(p["bb_gerisi"]))
        hacim = m["hacim"] > p["hacim_k"] * g.sma(m["hacim"], 20)
        atr = g.atr(y, d, k, int(p["atr_n"]))
        ds = int(p["duz_saat"])
        stop = d.rolling(ds, min_periods=ds).min() - 0.25 * atr
        long_ok = trend_ok & kirilim & (k > o) & bant_acilis & hacim & (k - stop <= p["maks_risk_atr"] * atr)
        out = _sadece_long(m, long_ok.fillna(False), stop)
        return r_hedefi(out, k, float(p["hedef_r"]))


# =============================================================================== 6. Paskalya takvimi
class PaskalyaTakvim(D3Taban):
    """dis__paskalya-takvim (swing, 1d) — raporlar "Holy Thursday Sprint" ve "Pre-Easter Week" (Quantified Strategies).
    mod="sprint": Paskalya Pazarı'ndan 4 gün önceki gün (Kutsal Çarşamba) kapanışında al, Kutsal Perşembe (Pazar-3) kapanışında
    sat. mod="hafta": Paskalya haftasından önceki Cuma (Pazar-9) kapanışında al, Kutsal Perşembe kapanışında sat (~4 işlem günü).
    Paskalya tarihi dateutil.easter ile hesaplanır (takvim bilgisi, lookahead yok). Motor sinyali kapanışta üretir, dolum sonraki
    açılışta olur -> giriş ve çıkış kaynağa göre bir bar kaymış olur (Kutsal Cuma borsası kapalı: hisse için çıkış Pazartesi
    açılışı). Çıkış: günden itibaren Paskalya-3 ve sonrası her mumda `cikis` (yıl içinde yalnız bir pozisyon açılır). Stop
    kaynakta yok -> 3 ATR (VARSAYIM). Yalnız long."""
    ad = "dis__paskalya-takvim"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "mod": "sprint", "stop_atr_k": 3.0}
    parametre_izgarasi = {"mod": ["sprint", "hafta"], "stop_atr_k": [2.0, 3.0, 4.0]}
    _GIRIS = {"sprint": 4, "hafta": 9}

    def kosullar(self, m):
        p = self.parametreler
        kalan = pd.Series(paskalya_kalan_gun(m.index), index=m.index)
        giris = kalan == self._GIRIS[p["mod"]]
        cikis = kalan <= 3
        return {"long": giris, "cikis_long": cikis}


# =============================================================================== 7. ADX / DI eşik kesişimi
class AdxDiEsikKesisimi(D3Taban):
    """dis__adx-di-esik-kesisimi (swing, 30m) — repo kodu "ADX strategy with NASDAQ 30-minutes timeframe" (ProRealCode).
    Long-only. Giriş yalnız Pazartesi-Çarşamba: (ADX(7) > 16 VE DI+(7), 26'yı yukarı keser) YA DA (ADX(7), 16'yı yukarı keser VE
    DI+ > 26). Çıkış: SL ve TP (kaynakta 600 / 200 endeks puanı; NASDAQ ~13.500 ortalamasıyla yüzdeye çevrildi: stop %4,5,
    hedef %1,5 — VARSAYIM) ve Perşembe `cikis_saat` (UTC) sonrası piyasadan (kaynak 17:50 yerel ~ 16:00 UTC) / Cuma ve sonrası."""
    ad = "dis__adx-di-esik-kesisimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "stop_yuzde": 0.045, "hedef_yuzde": 0.015, "adx_n": 7,
                               "adx_esik": 16.0, "di_esik": 26.0, "cikis_saat": 16.0}
    parametre_izgarasi = {"adx_esik": [14.0, 16.0, 20.0], "di_esik": [22.0, 26.0, 30.0], "hedef_yuzde": [0.01, 0.015, 0.02]}

    def kosullar(self, m):
        p = self.parametreler
        a = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], int(p["adx_n"]))
        adx, di = a["adx"], a["arti_di"]
        giris = ((adx > p["adx_esik"]) & yukari_kesis(di, p["di_esik"])) | (yukari_kesis(adx, p["adx_esik"]) & (di > p["di_esik"]))
        gun = pd.Series(m.index.dayofweek, index=m.index)
        saat = pd.Series(m.index.hour + m.index.minute / 60.0, index=m.index)
        cikis = ((gun == 3) & (saat >= p["cikis_saat"])) | (gun >= 4)
        return {"long": giris & (gun <= 2), "cikis_long": cikis}


# =============================================================================== 8. Codex haftalık-rejim ailesi
def _haftalik_rejim(m, hizli=20, yavas=40):
    """Tamamlanmış haftalık kapanış > EMA(hizli) ve EMA(hizli) > EMA(yavas) (Codex 1W yön filtresi)."""
    def f(w):
        e1, e2 = g.ema(w["kapanis"], hizli), g.ema(w["kapanis"], yavas)
        return pd.DataFrame({"r": ((w["kapanis"] > e1) & (e1 > e2) & e2.notna()).astype(float)})
    return haftalik_ust(m, f)["r"] > 0.5


class _CodexTaban(Strateji):
    """Codex Algo "wd" (haftalık rejim -> günlük işlem) ortak iskeleti. Yalnız long. Haftalık rejim şart (giriş) ve bozulursa
    çıkış; ATR14 x atr_k başlangıç ve iz süren stop (iz süren: CikisAyarlari.atr_iz_suren_k = 3). Sinyal kapanışta, emir sonraki
    açılışta. Özsermayenin %0,5 riski / toplam %2 limiti motor / portföy katmanında. Alt sınıf `giris_cikis(m)` yazar."""
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)
    _ORTAK = {"atr_n": 14, "atr_k": 3.0, "rejim_hizli": 20, "rejim_yavas": 40}

    def cikis_var_mi(self):
        return True

    def giris_cikis(self, m):
        raise NotImplementedError

    def zaman_cikisi(self):
        return None

    def sinyaller(self, m):
        p = self.parametreler
        rejim = _haftalik_rejim(m, int(p["rejim_hizli"]), int(p["rejim_yavas"]))
        giris, cikis = self.giris_cikis(m)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
        stop = m["kapanis"] - p["atr_k"] * atr
        return _sadece_long(m, (giris.fillna(False) & rejim), stop,
                            cikis_l=(cikis.fillna(False) | ~rejim), zaman_cikisi=self.zaman_cikisi())


class CodexWdCiftMomentum(_CodexTaban):
    """dis__codex-wd-cift-momentum (swing, 1W->1D) — rapor "Codex Algo wd: Çift Momentum (wd_dual_momentum_risk)".
    Giriş: haftalık rejim VE kapanış > günlük EMA(ema_n=100) VE ROC(63) > 0 VE ROC(21) > 0. Çıkış: ROC(21) < 0, kapanış < EMA(50)
    ya da haftalık rejim bozulur. Stop ATR14 x 3 (rapor). Kitap/kod yok, kural rapordan; yalnız long."""
    ad = "dis__codex-wd-cift-momentum"
    varsayilan_parametreler = {**_CodexTaban._ORTAK, "ema_n": 100, "roc_uzun": 63, "roc_kisa": 21, "cikis_ema": 50}
    parametre_izgarasi = {"ema_n": [75, 100, 150], "roc_uzun": [42, 63, 84], "roc_kisa": [10, 21, 30]}

    def giris_cikis(self, m):
        p, k = self.parametreler, m["kapanis"]
        r_u, r_k = k.pct_change(int(p["roc_uzun"])), k.pct_change(int(p["roc_kisa"]))
        giris = (k > g.ema(k, int(p["ema_n"]))) & (r_u > 0) & (r_k > 0)
        cikis = (r_k < 0) | (k < g.ema(k, int(p["cikis_ema"])))
        return giris, cikis


class CodexWdGunlukDonus(_CodexTaban):
    """dis__codex-wd-gunluk-donus (swing, 1W->1D) — rapor "Codex Algo wd: Günlük Dönüş (wd_reversion_risk)".
    Giriş: haftalık rejim VE kapanış Bollinger(20, bb_k=2) alt bandının altında VE RSI(2) < 10. Çıkış: kapanış orta banda ulaşır,
    RSI(2) > 70, haftalık rejim bozulur ya da en geç `max_gun`=10 gün (zaman_cikisi_mum). Stop ATR14 x 3. Yalnız long."""
    ad = "dis__codex-wd-gunluk-donus"
    varsayilan_parametreler = {**_CodexTaban._ORTAK, "bb_n": 20, "bb_k": 2.0, "rsi_n": 2, "rsi_alt": 10.0, "rsi_ust": 70.0,
                               "max_gun": 10}
    parametre_izgarasi = {"bb_k": [1.5, 2.0, 2.5], "rsi_alt": [5.0, 10.0, 15.0], "max_gun": [5, 10, 15]}

    def zaman_cikisi(self):
        return float(self.parametreler["max_gun"])

    def giris_cikis(self, m):
        p, k = self.parametreler, m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        r = g.rsi(k, int(p["rsi_n"]))
        return (k < bb["alt"]) & (r < p["rsi_alt"]), (k >= bb["orta"]) | (r > p["rsi_ust"])


class CodexWdGunlukMomentum(_CodexTaban):
    """dis__codex-wd-gunluk-momentum (swing, 1W->1D) — rapor "Codex Algo wd: Günlük Momentum (wd_momentum_risk)".
    Giriş: haftalık rejim VE günlük EMA(20) > EMA(50) VE ROC(20) > %5. Çıkış: EMA20 < EMA50, ROC20 < 0 ya da rejim bozulur.
    Stop ATR14 x 3. Yalnız long (dis__roc20-ls'ten farkı: haftalık rejim şartı, EMA kesişim süzgeci, ATR iz süren stop)."""
    ad = "dis__codex-wd-gunluk-momentum"
    varsayilan_parametreler = {**_CodexTaban._ORTAK, "ema_hizli": 20, "ema_yavas": 50, "roc_n": 20, "roc_esik": 5.0}
    parametre_izgarasi = {"ema_hizli": [10, 20, 30], "roc_n": [10, 20, 30], "roc_esik": [3.0, 5.0, 8.0]}

    def giris_cikis(self, m):
        p, k = self.parametreler, m["kapanis"]
        e1, e2 = g.ema(k, int(p["ema_hizli"])), g.ema(k, int(p["ema_yavas"]))
        roc = 100.0 * k.pct_change(int(p["roc_n"]))
        return (e1 > e2) & (roc > p["roc_esik"]), (e1 < e2) | (roc < 0)


class CodexWdHacimAkisi(_CodexTaban):
    """dis__codex-wd-hacim-akisi (swing, 1W->1D) — rapor "Codex Algo wd: Hacim Akışı (wd_flow_confirmation_risk)".
    Giriş: haftalık rejim VE kapanış > EMA(100) VE CMF(20) sıfırı yukarı keser VE ADL, adl_n=20 gün öncesinden yüksek VE OBV >
    kendi EMA(20)'si. Çıkış: CMF20 < -0.05, OBV < EMA(20), kapanış < EMA(50) ya da rejim bozulur. Stop ATR14 x 3. Yalnız long."""
    ad = "dis__codex-wd-hacim-akisi"
    varsayilan_parametreler = {**_CodexTaban._ORTAK, "ema_n": 100, "cmf_n": 20, "adl_n": 20, "obv_ema": 20, "cmf_cikis": -0.05,
                               "cikis_ema": 50}
    parametre_izgarasi = {"ema_n": [50, 100, 150], "cmf_n": [10, 20, 30], "adl_n": [10, 20, 30]}

    def giris_cikis(self, m):
        p, k = self.parametreler, m["kapanis"]
        c = cmf(m["yuksek"], m["dusuk"], k, m["hacim"], int(p["cmf_n"]))
        a, o = adl(m), obv(m)
        o_ema = g.ema(o, int(p["obv_ema"]))
        giris = (k > g.ema(k, int(p["ema_n"]))) & yukari_kesis(c, 0.0) & (a > a.shift(int(p["adl_n"]))) & (o > o_ema)
        cikis = (c < p["cmf_cikis"]) | (o < o_ema) | (k < g.ema(k, int(p["cikis_ema"])))
        return giris, cikis


class CodexWdKamaVerimlilik(_CodexTaban):
    """dis__codex-wd-kama-verimlilik (swing, 1W->1D) — rapor "Codex Algo wd: KAMA Verimlilik (wd_kama_efficiency_risk)".
    Giriş: haftalık rejim VE kapanış KAMA(er_n=10, 2, 30) çizgisini yukarı geri alır (önceki kapanış <= önceki KAMA) VE KAMA son 5
    güne göre yükselir VE ER(er_n) >= er_giris (0.30). Çıkış: kapanış < KAMA, ER < er_cikis (0.12) ya da rejim bozulur.
    Stop ATR14 x 3. Yalnız long."""
    ad = "dis__codex-wd-kama-verimlilik"
    varsayilan_parametreler = {**_CodexTaban._ORTAK, "er_n": 10, "er_giris": 0.30, "er_cikis": 0.12, "kama_egim": 5}
    parametre_izgarasi = {"er_n": [8, 10, 14], "er_giris": [0.2, 0.3, 0.4], "er_cikis": [0.08, 0.12, 0.16]}

    def giris_cikis(self, m):
        p, k = self.parametreler, m["kapanis"]
        n = int(p["er_n"])
        kam, er = kama(k, n, 2, 30), verimlilik_orani(k, n)
        geri_al = (k > kam) & (k.shift(1) <= kam.shift(1))
        giris = geri_al & (kam > kam.shift(int(p["kama_egim"]))) & (er >= p["er_giris"])
        return giris, (k < kam) | (er < p["er_cikis"])


# =============================================================================== 9. Osilatör eşik birleşimi
class OsilatorEsikBirlesimi(D3Taban):
    """dis__osilator-esik-birlesimi (swing, 1d) — rapor "PowerX — RSI + Stochastic + MACD" (Freqtrade/GitHub).
    Giriş (durum): RSI(7) > 65 VE yavaş stokastik D(14,3,3) > 69 VE MACD(12,26,9) histogramı > 0. Çıkış: yavaş stokastik D < 69
    (rapor: orijinal çıkış değiştirilmiş; yakın stop yok). Stop kaynakta yok -> 3 ATR felaket stopu (VARSAYIM). Varsayılan long;
    yonler="ls" ayna short (RSI < 100-65, D < 31, histogram < 0; çıkış D > 31)."""
    ad = "dis__osilator-esik-birlesimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "rsi_n": 7, "rsi_esik": 65.0, "stok_n": 14, "stok_esik": 69.0}
    parametre_izgarasi = {"rsi_esik": [60.0, 65.0, 70.0], "stok_esik": [60.0, 69.0, 75.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        hizli = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        yavas_k = g.sma(hizli, 3)
        yavas_d = g.sma(yavas_k, 3)
        r = g.rsi(k, int(p["rsi_n"]))
        h = g.macd(k)["histogram"]
        e, s = float(p["stok_esik"]), 100.0 - float(p["stok_esik"])
        return {"long": (r > p["rsi_esik"]) & (yavas_d > e) & (h > 0), "cikis_long": yavas_d < e,
                "short": (r < 100.0 - p["rsi_esik"]) & (yavas_d < s) & (h < 0), "cikis_short": yavas_d > s}


# =============================================================================== 10. Voltran
def _voltran_hafta_yonu(m):
    """VOLTRAN haftalık yön: 1W Supertrend(10, 2.5) boğa YA DA (haftalık kapanış >= EMA21 x 0.985 ve EMA8 > EMA21)."""
    def f(w):
        st = g.supertrend(w["yuksek"], w["dusuk"], w["kapanis"], 10, 2.5)["yon"]
        e8, e21 = g.ema(w["kapanis"], 8), g.ema(w["kapanis"], 21)
        ok = (st == 1) | ((w["kapanis"] >= e21 * 0.985) & (e8 > e21))
        return pd.DataFrame({"y": ok.astype(float).where(e21.notna())})
    return haftalik_ust(m, f)["y"] > 0.5


class Voltran1a(Strateji):
    """dis__voltran-1a (swing, 1W->1D) — rapor "VOLTRAN-1A: Swing Kırılım & Rejim Motoru" (Voltran 4 Süper Strateji).
    Haftalık yön: 1W Supertrend(10, 2.5) boğa YA DA haftalık kapanış >= EMA21 x 0.985 ve EMA8 > EMA21. Günlük giriş: Supertrend
    (10, 2.4) boğa, +DI > -DI ve ADX14 > adx_esik (15), kapanış `donchian_n` (12) günlük zirvesinin x0.985'ini aşar YA DA taze
    EMA8/EMA21 yukarı kesişimi (son `kesisim_pencere` mumda, kesişim sonrası EMA8>EMA21 sürüyor; "ivme başlamalı" VARSAYIM),
    hacim >= SMA20 x 0.95. Stop = kapanış - 3 ATR. Kâr kilidi: +1.05 ATR (= 0.35R) kârda stop girişe (orijinal giriş x 1.005); kalan
    pozisyon 3 ATR iz süren stop (motor, zirve tabanlı; orijinal kapanış bazlı Chandelier) YA DA Supertrend(-1) ve kapanış < EMA21.
    ADX'e göre pozisyon çarpanı (1.15x / 0.95x) motor risk boyutlandırmasına bırakıldı."""
    ad = "dis__voltran-1a"
    stil = "swing"
    varsayilan_parametreler = {"st_n": 10, "st_k": 2.4, "adx_n": 14, "adx_esik": 15.0, "donchian_n": 12, "donchian_oran": 0.985,
                               "kesisim_pencere": 3, "hacim_k": 0.95, "atr_n": 14, "stop_atr_k": 3.0}
    parametre_izgarasi = {"donchian_n": [8, 12, 20], "adx_esik": [15.0, 20.0, 25.0], "hacim_k": [0.0, 0.95, 1.2]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0, basabas_r_esigi=0.35)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        hafta = _voltran_hafta_yonu(m)
        st = g.supertrend(y, d, k, int(p["st_n"]), float(p["st_k"]))["yon"]
        a = g.adx(y, d, k, int(p["adx_n"]))
        atr = g.atr(y, d, k, int(p["atr_n"]))
        dn = int(p["donchian_n"])
        kirilim = k > y.shift(1).rolling(dn, min_periods=dn).max() * p["donchian_oran"]
        e8, e21 = g.ema(k, 8), g.ema(k, 21)
        kes = ((e8 > e21) & (e8.shift(1) <= e21.shift(1))).astype(float)
        w = int(p["kesisim_pencere"])
        ivme = (kes.rolling(w, min_periods=1).max() > 0) & (e8 > e21)
        hacim = m["hacim"] >= p["hacim_k"] * g.sma(m["hacim"], 20)
        long_ok = (hafta & (st == 1) & (a["arti_di"] > a["eksi_di"]) & (a["adx"] > p["adx_esik"]) & (kirilim | ivme)
                   & hacim & atr.notna())
        cikis = (st == -1) & (k < e21)
        return _sadece_long(m, long_ok, k - p["stop_atr_k"] * atr, cikis_l=cikis)


class Voltran1b(Strateji):
    """dis__voltran-1b (swing, 1W->1D) — rapor "VOLTRAN-1B: Kurumsal SMC & ML Geri Çekilme Motoru" (Voltran 4).
    Haftalık yön: 1A ile aynı tanım (rapor yalnız "1W ana trend boğa" diyor -> VARSAYIM) ve günlük kapanış > EMA34. Günlük giriş:
    (boğa FVG: Low > High[2] x fvg_oran (0.99) YA DA EMA21'e geri çekilme: Low <= EMA21 x 1.02 ve EMA21 üstünde yeşil kapanış) VE
    doğrusal "ML" skoru = (RSI14-45)/20 + (C>EMA34 ? .9 : -.9) + (+DI>-DI ? .6 : -.6) + (EMA13>EMA34 ? .5 : -.5) >= skor_esik
    (1.10; rapordaki "Lorentzian ML" formülü kural tabanlıdır) VE RSI14 >= rsi_min (46). Stop = kapanış - 3 ATR. Kâr kilidi +1.05 ATR
    (0.35R) -> stop girişe; çıkış: skor <= -0.7 ve kapanış < EMA34 x 0.985, ya da 3 ATR iz süren stop."""
    ad = "dis__voltran-1b"
    stil = "swing"
    varsayilan_parametreler = {"skor_esik": 1.10, "rsi_min": 46.0, "fvg_oran": 0.99, "geri_cekilme": 1.02, "skor_cikis": -0.7,
                               "atr_n": 14, "stop_atr_k": 3.0}
    parametre_izgarasi = {"skor_esik": [0.8, 1.1, 1.4], "rsi_min": [44.0, 46.0, 50.0], "fvg_oran": [0.99, 0.995, 1.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0, basabas_r_esigi=0.35)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        hafta = _voltran_hafta_yonu(m)
        e13, e21, e34 = g.ema(k, 13), g.ema(k, 21), g.ema(k, 34)
        r = g.rsi(k, 14)
        a = g.adx(y, d, k, 14)
        atr = g.atr(y, d, k, int(p["atr_n"]))
        skor = ((r - 45.0) / 20.0 + np.where(k > e34, 0.9, -0.9) + np.where(a["arti_di"] > a["eksi_di"], 0.6, -0.6)
                + np.where(e13 > e34, 0.5, -0.5))
        skor = pd.Series(skor, index=m.index).where(r.notna() & a["adx"].notna() & e34.notna())
        fvg = d > y.shift(2) * p["fvg_oran"]
        geri = (d <= e21 * p["geri_cekilme"]) & (k > e21) & (k > o)
        long_ok = hafta & (k > e34) & (fvg | geri) & (skor >= p["skor_esik"]) & (r >= p["rsi_min"]) & atr.notna()
        cikis = (skor <= p["skor_cikis"]) & (k < e34 * 0.985)
        return _sadece_long(m, long_ok.fillna(False), k - p["stop_atr_k"] * atr, cikis_l=cikis)


def _reddit_hafta_yonu(m):
    """Reddit/Voltran 1W_Bias: haftalık kapanış >= EMA20 YA DA haftalık Supertrend(10, 3) boğa (rapor "PMax_1W == 1"; PMax yok ->
    Supertrend ile yaklaşıldı, VARSAYIM)."""
    def f(w):
        e20 = g.ema(w["kapanis"], 20)
        st = g.supertrend(w["yuksek"], w["dusuk"], w["kapanis"], 10, 3.0)["yon"]
        return pd.DataFrame({"y": ((w["kapanis"] >= e20) | (st == 1)).astype(float).where(e20.notna())})
    return haftalik_ust(m, f)["y"] > 0.5


def _z_skor(k, n):
    return (k - g.ema(k, n)) / k.rolling(n, min_periods=n).std()


class VoltranR1(Strateji):
    """dis__voltran-r1 (swing, 1W->1D) — rapor "VOLTRAN-R1: Reddit-Quant Swing Hibrit (Dip Avcısı + Z-Skor Kırılım)".
    Haftalık yön: kapanış >= EMA20 ya da Supertrend(10,3) boğa (VARSAYIM, bkz. _reddit_hafta_yonu). Long-only, iki motor:
      Motor A (dip): kapanış > SMA100 x 0.95 VE kapanış < HH10 - kat_a x SMA(H-L, 25) VE IBS < ibs_a (0.28); çıkış: ilk kapanış
        > önceki mumun zirvesi.
      Motor B (trend): Z65 > z_esik (0.48) VE ((kapanış >= önceki 15 mumun zirvesi x 0.997 VE RVOL20 > 1.2) YA DA (IBS > 0.65 ve
        EMA10 > EMA20)); çıkış: Z65 < -0.15. (HH15 "önceki 15 mum" = nedensel kırılım yorumu; VARSAYIM.)
    motor="A"/"B"/"AB". Mod-duyarlı çıkış için sınıf içi SANAL pozisyon izlenir (motorun açıp açmadığını bilmez; kural çıkışı +
    sabit stop + iz süren stop ile yaklaşık) — A pozisyonları B çıkışıyla, B pozisyonları A çıkışıyla kapanmaz.
    Stop (kitapta yok) = kapanış - 2.5 ATR (VARSAYIM). 4. günde +1.2 ATR'de %30 kısmi + başabaş: motorda gün şartı yok ->
    +1.2 ATR (=0.48R) kârda %30 kısmi ve stop girişe (A pozisyonlarında da geçerli); kalan 2.5 ATR iz süren stop."""
    ad = "dis__voltran-r1"
    stil = "swing"
    varsayilan_parametreler = {"motor": "AB", "sma_a": 100, "hh_a": 10, "kat_a": 2.15, "ibs_a": 0.28, "z_n": 65, "z_esik": 0.48,
                               "z_cikis": -0.15, "hh_b": 15, "rvol_k": 1.2, "ibs_b": 0.65, "atr_n": 14, "stop_atr_k": 2.5}
    parametre_izgarasi = {"motor": ["A", "B", "AB"], "ibs_a": [0.2, 0.28, 0.35], "z_esik": [0.35, 0.48, 0.6]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.5, basabas_r_esigi=0.48, kismi=((0.48, 0.30),))

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        hafta = _reddit_hafta_yonu(m)
        atr = g.atr(y, d, k, int(p["atr_n"]))
        b = ibs(m)
        hh10 = y.rolling(int(p["hh_a"]), min_periods=int(p["hh_a"])).max()
        aralik_ort = g.sma(y - d, 25)
        a_sig = (hafta & (k > g.sma(k, int(p["sma_a"])) * 0.95) & (k < hh10 - p["kat_a"] * aralik_ort) & (b < p["ibs_a"])
                 & atr.notna())
        z = _z_skor(k, int(p["z_n"]))
        hh15 = y.shift(1).rolling(int(p["hh_b"]), min_periods=int(p["hh_b"])).max()
        rvol = m["hacim"] / g.sma(m["hacim"], 20)
        b_sig = (hafta & (z > p["z_esik"]) & (((k >= hh15 * 0.997) & (rvol > p["rvol_k"]))
                                              | ((b > p["ibs_b"]) & (g.ema(k, 10) > g.ema(k, 20)))) & atr.notna())
        if p["motor"] == "A":
            b_sig = _bos(m.index)
        elif p["motor"] == "B":
            a_sig = _bos(m.index)
        a_sig, b_sig = a_sig.fillna(False), b_sig.fillna(False)
        stop = k - p["stop_atr_k"] * atr
        cikis_a = k > y.shift(1)
        cikis_b = z < p["z_cikis"]
        mod_once = self._sanal_mod(m, a_sig.to_numpy(), b_sig.to_numpy(), cikis_a.to_numpy(), cikis_b.to_numpy(),
                                   stop.to_numpy(), atr.to_numpy())
        mod_once = pd.Series(mod_once, index=m.index)
        cikis = ((mod_once == 1) & cikis_a) | ((mod_once == 2) & cikis_b)
        return _sadece_long(m, a_sig | b_sig, stop, cikis_l=cikis)

    def _sanal_mod(self, m, a_sig, b_sig, cik_a, cik_b, stop, atr):
        """Her mumun BAŞINDAKİ sanal pozisyon modu (0 yok, 1 motor A, 2 motor B). Sanal pozisyon: sinyal mumunu izleyen mumdan
        itibaren açık; kural çıkışı, sabit stop ve iz süren stop (ekstrem - k x ATR) ile kapanır."""
        y, d = m["yuksek"].to_numpy(), m["dusuk"].to_numpy()
        n = len(y)
        k_iz = float(self.cikis_ayarlari.atr_iz_suren_k)
        mod_once = np.zeros(n, dtype=np.int64)
        mod, vstop, ekstrem = 0, np.nan, -np.inf
        for i in range(n):
            mod_once[i] = mod
            if mod != 0:
                ekstrem = max(ekstrem, y[i])
                if not np.isnan(atr[i]):
                    vstop = max(vstop, ekstrem - k_iz * atr[i])
                if d[i] <= vstop or (mod == 1 and cik_a[i]) or (mod == 2 and cik_b[i]):
                    mod = 0
            if mod == 0 and (a_sig[i] or b_sig[i]) and not np.isnan(stop[i]):
                mod, vstop, ekstrem = (1 if a_sig[i] else 2), stop[i], -np.inf
        return mod_once


class Z65Rejim(Strateji):
    """dis__z65-rejim (swing, 1W->1D) — rapor "R5 'Dual Signal Trend Sentinel' 65 Günlük Z-Skor Rejim Motoru" (Reddit/Quant).
    Z65 = (Close - EMA65) / StDev(Close, 65). Haftalık bias pozitif (kapanış >= EMA20 ya da Supertrend boğa; VARSAYIM) iken Z65 >
    z_giris (0.55) VE kapanış > EMA20 VE IBS > ibs_min (0.55) ise long. Nötr bölgede (z_cikis..z_giris) tutar; Z65 < z_cikis
    (-0.10) ile nakde geçer. Kâr kilidi: +1.8 ATR (stop 2.8 ATR -> 0.64R) sonrası başabaş, zirveden 2.8 ATR iz süren stop.
    Başlangıç stop kaynakta yok -> 2.8 ATR (iz süren ile aynı, VARSAYIM). Yalnız long."""
    ad = "dis__z65-rejim"
    stil = "swing"
    varsayilan_parametreler = {"z_n": 65, "z_giris": 0.55, "z_cikis": -0.10, "ema_n": 20, "ibs_min": 0.55, "atr_n": 14,
                               "stop_atr_k": 2.8}
    parametre_izgarasi = {"z_giris": [0.4, 0.55, 0.7], "z_cikis": [-0.25, -0.10, 0.0], "ibs_min": [0.4, 0.55, 0.7]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.8, basabas_r_esigi=0.64)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        hafta = _reddit_hafta_yonu(m)
        z = _z_skor(k, int(p["z_n"]))
        atr = g.atr(y, d, k, int(p["atr_n"]))
        long_ok = hafta & (z > p["z_giris"]) & (k > g.ema(k, int(p["ema_n"]))) & (ibs(m) > p["ibs_min"]) & atr.notna()
        return _sadece_long(m, long_ok, k - p["stop_atr_k"] * atr, cikis_l=(z < p["z_cikis"]))
