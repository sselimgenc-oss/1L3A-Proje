"""D10-A — kodlama_kuyrugu_2026-11-07.csv'deki yeni_aile satırlarının (a grubu, 22 aile) KODU. KOD KOPYALANMADI: kitap kartları ve
repo raporları VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__` (kuyruktaki `yeni__` öneki yerine). Hepsi nedensel
(lookahead yok): sinyal bar kapanışında, dolum sonraki açılışta (motor).

Ortak uyarlamalar
  * Kitapta stopu / hedefi olmayanlara ATR felaket stopu eklendi (VARSAYIM; sınıf docstring'inde ayrıca yazılı).
  * Intraday "buy stop" girişleri günlük barda temsil edilemez: kapanışta sinyal, ertesi açılışta giriş.
  * Öznel kurallar (trend çizgisi, "iyi mum", "önemli zirve") ölçülebilir tanıma çevrildi; tanım ilgili docstring'de.
  * Tek-grafik motoru: evren sıralaması / hisse hacmi eşikleri (ortalama hacim > 50 bin vb.) uygulanmadı.

dis__ortalamaya-donus-gerilme, dis__bant-kirilim-trend, dis__ha-stokastik-geri-cekilme, dis__ivanov-swing-kurulumlari,
dis__ma-mukemmel-siralama, dis__gann-swing-grafigi, dis__ayin-ilk-gunu-deseni, dis__lien-20-gun-sahte-kirilim,
dis__macd-histogram-pivot, dis__sma200-bant-trend, dis__uc-mum-swing-noktasi, dis__yeni-zirve-trend-filtresi,
dis__hafta-ici-takvim, dis__arps-pivot-desenleri, dis__nokta-sekil, dis__granville-ma-kurallari, dis__ma20-rsi-cmf,
dis__ochoa-genisleme-gunu, dis__rsi-failure-swing, dis__sst-dmi-50ma, dis__volatilite-sikisma-reversal,
dis__ema-kesisim-123-kurulumu
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import kur
from motor.strateji.dis._gosterge_d3 import cmf
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, gecis, heikin_ashi, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import fraktal_pivotlar, zigzag_pivotlar
from motor.strateji.temel import Strateji

from motor.strateji.dis._gosterge_d9 import ardisik_say, cekic, ters_cekic
from motor.strateji.dis._gosterge_d10a import (
    connors_rsi, nokta_sekil_sinyalleri, pivot_olaylari, risk_siniri_l, risk_siniri_s, stoch_yavas, swing_trendi, yuzde_b)


def _bos(index):
    return pd.Series(False, index=index)


def _ymask(p, long_ok, short_ok, anahtar="short"):
    """short parametresi False ise short sinyali silinir."""
    if not p.get(anahtar, True):
        short_ok = _bos(long_ok.index)
    return long_ok, short_ok


class _D10(Strateji):
    """Ortak: çıkış kuralı/stop her sınıfta var; cikis_var_mi True."""

    def cikis_var_mi(self):
        return True


# =============================================================================== 1. ortalamaya dönüş gerilmesi
class OrtalamayaDonusGerilme(_D10):
    """dis__ortalamaya-donus-gerilme (swing, 1d) — Davey (ConnorsRSI, Bollinger stretch, kapanış aralığı, ters kırılım, AND yığma),
    Pruitt (%B + SMA200), repo (Sharp Mean Reversion, % Bollinger in Trend) varyantları; `mod` parametresi seçer.
      crsi          ConnorsRSI(3,2,100) giris_esik'in altına kesişirse long; cikis_esik üstüne çıkınca çık. Short: 100-giris_esik üstü.
      bb_stretch    Bollinger(bb_n, bb_k) %B iki bar üst üste < b_esik -> long; %B > b_cikis olunca çık. Short ayna (>1-b_esik).
      kapanis_arali crange=(C-LL(N))/(HH(N)-LL(N)) < cr_esik -> long; crange > cr_esik olunca çık. Short ayna (>1-cr_esik).
      ters_kirilim  Kapanış son kir_n kapanışın en düşüğü -> long; kapanış son kir_cikis_n kapanışın en yükseği olunca çık.
      sma_gerilme   (Sharp, repo) SMA2 < SMA8 x (1-sma_pay) -> long; kapanış önceki yükseği aşınca çık. ATLANDI: ROC63/126/252
                    sıralama filtreleri (çok hisseli evren gerektirir).
      bb_trend      (repo) kapanış > SMA100 ve SMA20 > SMA200 iken %B(20,2) iki bar < 0.2 -> long; %B(5,1) 1'i yukarı kesince çık. Yalnız long.
      bb_200ma      (Pruitt) kapanış > SMA200 ve 3 mumluk ortalama %B(5,2) < 0.25 -> long; %B > 0.75 olunca çık. Short ayna (SMA200 altı, > 0.75; çık < 0.25).
      and_yigma     ConnorsRSI VE Bollinger stretch VE SMA gerilmesi aynı anda -> long (Davey 'AND'); crsi çıkışı.
    VARSAYIM: bileşen parametreleri kitapta yok (giris_esik 10, cikis_esik 30, bb 20/2, b_esik 0.1, N=10 ...); kitapta stop yok
    -> stop_atr_k x ATR (3). 7 barlık zaman çıkışı kitapta 'kullanma' dendi -> zaman_cikisi=0 (kapalı)."""
    ad = "dis__ortalamaya-donus-gerilme"
    stil = "swing"
    varsayilan_parametreler = {
        "mod": "crsi", "giris_esik": 10.0, "cikis_esik": 30.0, "bb_n": 20, "bb_k": 2.0, "b_esik": 0.1, "b_cikis": 0.4,
        "cr_n": 10, "cr_esik": 0.1, "kir_n": 10, "kir_cikis_n": 30, "sma_hizli": 2, "sma_yavas": 8, "sma_pay": 0.01,
        "stop_atr_k": 3.0, "atr_periyot": 14, "zaman_cikisi": 0, "short": True}
    parametre_izgarasi = {
        "mod": ["crsi", "bb_stretch", "kapanis_arali", "ters_kirilim", "sma_gerilme", "bb_trend", "bb_200ma", "and_yigma"],
        "stop_atr_k": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        mod = p["mod"]
        bos = _bos(idx)
        L = S = cL = cS = bos
        if mod == "crsi":
            cr = connors_rsi(k)
            L, S = asagi_kesis(cr, p["giris_esik"]), yukari_kesis(cr, 100.0 - p["giris_esik"])
            cL, cS = cr > p["cikis_esik"], cr < 100.0 - p["cikis_esik"]
        elif mod == "bb_stretch":
            b = yuzde_b(k, int(p["bb_n"]), float(p["bb_k"]))
            L = (b < p["b_esik"]) & (b.shift(1) < p["b_esik"])
            S = (b > 1 - p["b_esik"]) & (b.shift(1) > 1 - p["b_esik"])
            cL, cS = b > p["b_cikis"], b < 1 - p["b_cikis"]
        elif mod == "kapanis_arali":
            n = int(p["cr_n"])
            hh, ll = h.rolling(n, min_periods=n).max(), d.rolling(n, min_periods=n).min()
            cr = (k - ll) / (hh - ll).where(hh != ll)
            L, S = cr < p["cr_esik"], cr > 1 - p["cr_esik"]
            cL, cS = cr > p["cr_esik"], cr < 1 - p["cr_esik"]
        elif mod == "ters_kirilim":
            n, mm = int(p["kir_n"]), int(p["kir_cikis_n"])
            L = k <= k.rolling(n, min_periods=n).min()
            S = k >= k.rolling(n, min_periods=n).max()
            cL = k >= k.rolling(mm, min_periods=mm).max()
            cS = k <= k.rolling(mm, min_periods=mm).min()
        elif mod == "sma_gerilme":
            a, b = g.sma(k, int(p["sma_hizli"])), g.sma(k, int(p["sma_yavas"]))
            L, S = a < b * (1 - p["sma_pay"]), a > b * (1 + p["sma_pay"])
            cL, cS = k > h.shift(1), k < d.shift(1)
        elif mod == "bb_trend":
            b20 = yuzde_b(k, 20, 2.0)
            b5 = yuzde_b(k, 5, 1.0)
            L = (k > g.sma(k, 100)) & (g.sma(k, 20) > g.sma(k, 200)) & (b20 < 0.2) & (b20.shift(1) < 0.2)
            cL = yukari_kesis(b5, 1.0)
        elif mod == "bb_200ma":
            b = yuzde_b(k, 5, 2.0).rolling(3, min_periods=3).mean()
            ma = g.sma(k, 200)
            L, S = (k > ma) & (b < 0.25), (k < ma) & (b > 0.75)
            cL, cS = b > 0.75, b < 0.25
        elif mod == "and_yigma":
            cr = connors_rsi(k)
            b = yuzde_b(k, int(p["bb_n"]), float(p["bb_k"]))
            a, c8 = g.sma(k, int(p["sma_hizli"])), g.sma(k, int(p["sma_yavas"]))
            L = (cr < p["giris_esik"]) & (b < p["b_esik"]) & (a < c8 * (1 - p["sma_pay"]))
            S = (cr > 100.0 - p["giris_esik"]) & (b > 1 - p["b_esik"]) & (a > c8 * (1 + p["sma_pay"]))
            cL, cS = cr > p["cikis_esik"], cr < 100.0 - p["cikis_esik"]
        else:
            raise ValueError(f"Bilinmeyen mod: {mod!r}")
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kur(m, L, S, k - a, k + a, None, None, cL, cS, zaman_cikisi=(p["zaman_cikisi"] or None) and float(p["zaman_cikisi"]))


# =============================================================================== 2. bant kırılımı trend
class BantKirilimTrend(_D10):
    """dis__bant-kirilim-trend (swing, 1d) — Pruitt Bollinger/Keltner kırılımı (60 gün, 2 sapma/ATR) + repo 'Keltner + RSI'.
      bollinger     kapanış SMA(n)+k*std üstüne YUKARI KESERSE long; SMA(n)-k*std altına inerse short.
      keltner       merkez = tipik fiyatın (H+L+C)/3 SMA(n); kanal = merkez +/- k*ATR(n).
      keltner_rsi   Keltner üst bandı yukarı kesişimi + RSI(14) > rsi_esik (61) -> long (yalnız long, repo).
    Stop = merkez ortalama (kitap: başlangıç riski bant-ortalama mesafesi) - stop_tampon_atr*ATR; çıkış: kapanış merkezi karşıya keserse
    (long: kapanış < merkez). VARSAYIM: keltner_rsi için n=60 ızgara değeri kullanılır (repo periyot vermedi); tipik fiyat
    (H+L+C)/3 (kitap kodundaki toplam bölünmemiş).
    d11j EK (varsayılan kapalı; ızgaraya girmez; kaynak aile bant-ust-alt-kirilim-stop-giris, BollChannel/KingKeltner): cci_n>0 ->
    long kırılımı için CCI(cci_n) > 0, short için CCI < 0 (CCI işaret süzgeci). Stop-giriş emri yerine kapanışta kırılım sinyali;
    ATR izleyen çıkış CikisAyarlari(atr_iz_suren_k) ile ayar kaydında verilir."""
    ad = "dis__bant-kirilim-trend"
    stil = "swing"
    varsayilan_parametreler = {"mod": "bollinger", "n": 60, "k": 2.0, "rsi_n": 14, "rsi_esik": 61.0, "stop_tampon_atr": 0.0,
                               "atr_periyot": 14, "short": True, "cci_n": 0}
    parametre_izgarasi = {"mod": ["bollinger", "keltner", "keltner_rsi"], "n": [40, 60, 100], "k": [1.5, 2.0, 2.5]}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        n = int(p["n"])
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        if p["mod"] == "bollinger":
            b = g.bollinger(k, n, float(p["k"]))
            orta, ust, alt = b["orta"], b["ust"], b["alt"]
        elif p["mod"] in ("keltner", "keltner_rsi"):
            orta = g.sma((h + d + k) / 3.0, n)
            band = p["k"] * g.atr(h, d, k, n)
            ust, alt = orta + band, orta - band
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        L, S = yukari_kesis(k, ust), asagi_kesis(k, alt)
        if p["mod"] == "keltner_rsi":
            L = L & (g.rsi(k, int(p["rsi_n"])) > p["rsi_esik"])
            S = _bos(m.index)
        if p["cci_n"]:
            cc = cci(h, d, k, int(p["cci_n"]))
            L, S = L & (cc > 0), S & (cc < 0)
        L, S = _ymask(p, L, S)
        t = p["stop_tampon_atr"] * a
        return kur(m, L, S, orta - t, orta + t, None, None, k < orta, k > orta)


# =============================================================================== 3. HA + stokastik geri çekilme
class HaStokastikGeriCekilme(_D10):
    """dis__ha-stokastik-geri-cekilme (swing, 4h) — Munroe 'HA + stokastik + 100 SMA geri çekilme'. Kural (long): kapanış > SMA(100) ve
    SMA eğimi yukarı (SMA - SMA[egim_n] > 0); trende karşı en az `min_kirmizi` ardışık kırmızı Heikin Ashi mumundan oluşan geri
    çekilme; HA mumu yeşile döner VE yavaş stokastik (8,3,3) %K, %D'yi yukarı keser; iki olay en çok `bekle` bar içinde olmuş
    olmalı ('yumuşak kesişim' = bekleme penceresi içinde K-D kesişimi; öznel tanım ölçülebilire çevrildi). Short ayna.
    Stop: son stop_n mumun dibi (HA renk değişiminden önceki dip) - stop_tampon_atr*ATR, risk en çok maks_risk_atr ATR. Çıkış:
    karşı renkte HA mumu VE stokastik ters (K<D) + 3 ATR iz süren stop (kitap 'iz süren stop'). ust_tf='1w' verilirse üst zaman diliminde
    HA rengi de trendle aynı olmalı (varsayılan kapalı). ATLANDI: çoklu giriş/piramit (kart coklu-zd-trend-piramit), 5 dk HA-doji
    varyantı (kart ha-doji-donus; stopsuz, doji oranı yok), güçlü/zayıf para birimi filtresi (forex)."""
    ad = "dis__ha-stokastik-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {"sma_n": 100, "egim_n": 10, "min_kirmizi": 2, "bekle": 3, "stop_n": 8, "stop_tampon_atr": 0.25,
                               "maks_risk_atr": 4.0, "ust_tf": "", "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"min_kirmizi": [1, 2, 3], "bekle": [2, 3, 5], "stop_n": [5, 8, 12]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        ha = heikin_ashi(o, h, d, k)
        yesil, kirmizi = ha["ha_kapanis"] > ha["ha_acilis"], ha["ha_kapanis"] < ha["ha_acilis"]
        st = stoch_yavas(h, d, k, 8, 3, 3)
        sma = g.sma(k, int(p["sma_n"]))
        egim = sma - sma.shift(int(p["egim_n"]))
        b = int(p["bekle"])
        mk = int(p["min_kirmizi"])
        flip_g = yesil & kirmizi.shift(1, fill_value=False) & (ardisik_say(kirmizi).shift(1) >= mk)
        flip_r = kirmizi & yesil.shift(1, fill_value=False) & (ardisik_say(yesil).shift(1) >= mk)
        cu, cd = yukari_kesis(st["k"], st["d"]), asagi_kesis(st["k"], st["d"])

        def son(x):
            return x.rolling(b, min_periods=1).max() > 0
        L = (k > sma) & (egim > 0) & yesil & son(flip_g) & son(cu) & (flip_g | cu)
        S = (k < sma) & (egim < 0) & kirmizi & son(flip_r) & son(cd) & (flip_r | cd)
        if p["ust_tf"]:
            yon_u = ust_zaman(m, p["ust_tf"], lambda u: pd.DataFrame(
                {"ha": np.sign(heikin_ashi(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"]).eval("ha_kapanis - ha_acilis"))}))["ha"]
            L, S = L & (yon_u > 0), S & (yon_u < 0)
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        n = int(p["stop_n"])
        sl = risk_siniri_l(d.rolling(n, min_periods=n).min() - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(h.rolling(n, min_periods=n).max() + p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        return kur(m, L, S, sl, ss, None, None, kirmizi & (st["k"] < st["d"]), yesil & (st["k"] > st["d"]))


# =============================================================================== 4. Ivanov swing kurulumları
class IvanovSwingKurulumlari(_D10):
    """dis__ivanov-swing-kurulumlari (swing, 1d) — Ivanov: aralık daralması kırılımı / beklenti girişi / kısa swing momentum kırılması.
    mod='kirilim' (long): önceki bar t-1'de sıkı konsolidasyon [son kons_n barın (HH-LL) <= kons_atr x ATR, ortalama hacim <
    hacim_alt x SMA(hacim,50), yükseliş trendi SMA20>SMA50, SMA5>SMA20, kapanış>SMA5]; tetik günü: (kapanış-açılış)/açılış > tetik,
    yeni zirve_n günlük yüksek, hacim > hacim_k x SMA(hacim,20), önceki 3 gün üst üste yükselmemiş (genişlemiş hisse alınmaz).
    Stop = tetik gününün dibi (kitap). mod='beklenti' (long): kurulum tamam iken tetiklenmeden, konsolidasyon dibi - 0.1 ATR sıkı
    stopla giriş (giriş anı kitapta belirsiz: kurulumun ilk tamamlandığı kapanış). mod='kisa' (short): açılıştan > tetik düşüş,
    SMA20 < düşen SMA50, SMA5 < SMA20, kapanış < SMA5, yeni 5 günlük dip, 3 gün üst üste düşmemiş, son 5 günde %10'dan fazla düşmemiş;
    stop = tetik gününün zirvesi.
    Çıkış: long kapanış < önceki günün dibi VEYA kapanış < SMA(sma_cikis); short 3 gün üst üste düşüş VEYA kapanış > SMA5; kısmi kâr 1R'de
    %50 + stop girişe (CikisAyarlari). ATLANDI: 'tetiklendikten 5 gün içinde %5 gitmediyse sat' (pozisyon durumu gerektirir), göreceli
    güç/sektör/market filtreleri, mutlak hacim ve fiyat eşikleri. VARSAYIM: 'düşük hacim' = hacim_alt 1.0 (ortalamanın altı)."""
    ad = "dis__ivanov-swing-kurulumlari"
    stil = "swing"
    varsayilan_parametreler = {"mod": "kirilim", "kons_n": 5, "kons_atr": 3.0, "tetik": 0.02, "zirve_n": 10, "hacim_k": 1.0,
                               "hacim_alt": 1.0, "sma_cikis": 5, "dip_n": 5, "hafta_dusus": 0.10, "maks_risk_atr": 4.0,
                               "atr_periyot": 14}
    parametre_izgarasi = {"mod": ["kirilim", "beklenti", "kisa"], "kons_n": [3, 5, 10], "tetik": [0.015, 0.02, 0.04]}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=1.0)

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k, v = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        s5, s20, s50 = g.sma(k, 5), g.sma(k, 20), g.sma(k, 50)
        n = int(p["kons_n"])
        bos = _bos(m.index)
        art_yuk = (k.shift(1) > k.shift(2)) & (k.shift(2) > k.shift(3)) & (k.shift(3) > k.shift(4))
        dar = (h.rolling(n, min_periods=n).max() - d.rolling(n, min_periods=n).min()) <= p["kons_atr"] * a
        dusuk_hacim = v.rolling(n, min_periods=n).mean() < p["hacim_alt"] * v.rolling(50, min_periods=50).mean()
        kurulum = dar & dusuk_hacim & (s20 > s50) & (s5 > s20) & (k > s5)
        yuk_ok = ((k - o) / o) > p["tetik"]
        mod = p["mod"]
        L = S = bos
        sl = ss = k
        if mod == "kirilim":
            zirve = h > h.shift(1).rolling(int(p["zirve_n"]), min_periods=int(p["zirve_n"])).max()
            hac = v > p["hacim_k"] * g.sma(v, 20).shift(1)
            L = kurulum.shift(1, fill_value=False) & yuk_ok & zirve & hac & ~art_yuk
            sl = risk_siniri_l(d, k, a, p["maks_risk_atr"])
        elif mod == "beklenti":
            L = gecis(kurulum & ~yuk_ok)
            sl = risk_siniri_l(d.rolling(n, min_periods=n).min() - 0.1 * a, k, a, p["maks_risk_atr"])
        elif mod == "kisa":
            dn = int(p["dip_n"])
            yeni_dip = k < k.shift(1).rolling(dn, min_periods=dn).min()
            dus3 = ardisik_say(k < k.shift(1)) >= 3
            S = (((o - k) / o) > p["tetik"]) & (s20 < s50) & (s50 < s50.shift(1)) & (s5 < s20) & (k < s5) & yeni_dip \
                & ~dus3 & (k > (1 - p["hafta_dusus"]) * k.shift(5))
            ss = risk_siniri_s(h, k, a, p["maks_risk_atr"])
        else:
            raise ValueError(f"Bilinmeyen mod: {mod!r}")
        sc = g.sma(k, int(p["sma_cikis"]))
        cL = (k < d.shift(1)) | (k < sc)
        cS = (ardisik_say(k < k.shift(1)) >= 3) | (k > s5)
        return kur(m, L, S, sl, ss, None, None, cL, cS)


# =============================================================================== 5. MA mükemmel sıralama
class MaMukemmelSiralama(_D10):
    """dis__ma-mukemmel-siralama (swing, 1d; kartta swing/daytrade — ana stil swing) — Lien 'mükemmel sıralama'. Long: kapanış > SMA10 >
    SMA20 > SMA50 > SMA100 > SMA200 dizilimi ilk oluşumundan `bekle` bar sonra HÂLÂ geçerliyse VE ADX(14) >= adx_min ve yükseliyor
    (ADX > önceki ADX) -> long. Stop = ilk oluşum gününün dibi (en çok maks_risk_atr ATR uzak). Çıkış: cikis_modu 'kisa' = SMA10 SMA20'nin
    altına geçince; 'tam' = dizilim herhangi bir yerden bozulunca. Short tam ters dizilim. ATLANDI: repo KISS (5 dk, DAX, 20:00 çıkışı:
    ayrı bir gün içi kural seti). VARSAYIM: 'fiyat > SMA10' dizilime dahil, ADX eşiği 20, maks risk 6 ATR."""
    ad = "dis__ma-mukemmel-siralama"
    stil = "swing"
    varsayilan_parametreler = {"bekle": 5, "adx_min": 20.0, "cikis_modu": "kisa", "maks_risk_atr": 6.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"bekle": [3, 5, 8], "adx_min": [0.0, 20.0, 25.0], "cikis_modu": ["kisa", "tam"]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        s = [g.sma(k, n) for n in (10, 20, 50, 100, 200)]
        yuk = (k > s[0]) & (s[0] > s[1]) & (s[1] > s[2]) & (s[2] > s[3]) & (s[3] > s[4])
        asg = (k < s[0]) & (s[0] < s[1]) & (s[1] < s[2]) & (s[2] < s[3]) & (s[3] < s[4])
        adx = g.adx(h, d, k, 14)["adx"]
        adx_ok = (adx >= p["adx_min"]) & (adx > adx.shift(1))
        b = int(p["bekle"])
        L = (ardisik_say(yuk) == b + 1) & adx_ok
        S = (ardisik_say(asg) == b + 1) & adx_ok
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        sl = risk_siniri_l(d.shift(b), k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(h.shift(b), k, a, p["maks_risk_atr"])
        if p["cikis_modu"] == "kisa":
            cL, cS = s[0] < s[1], s[0] > s[1]
        else:
            cL, cS = ~yuk, ~asg
        return kur(m, L, S, sl, ss, None, None, cL, cS)


# =============================================================================== 6. Gann swing grafiği
class GannSwingGrafigi(_D10):
    """dis__gann-swing-grafigi (swing, 1d) — Rivalland 'değiştirilmiş swing trend değişimi' + 'swing trend devamı'. Swing yüksek/dip =
    fraktal pivot (sol-sağ swing_k bar; sağ taraf onay gecikmesi = 'karşıt hareket en az swing_k gün sürdü'). Trend: son iki tepe VE
    son iki dip yükseliyorsa +1, alçalıyorsa -1 (karışıksa önceki).
      degisim  düşüş trendinde kapanış son onaylı swing yüksek üstüne yukarı keserse long (stop: son swing dip - tampon); yükseliş trendinde
               kapanış son swing dip altına inerse short (stop: son swing yüksek + tampon). Kitap 'buy stop 1-2 tik üstü': kapanışla uyarlandı.
      devam    yükseliş trendinde en az devam_gun ardışık düşük-dip günü (karşıt düzeltme) sonrası kapanış önceki günün yükseğini aşarsa long
               (stop: düzeltmenin dibi - tampon); düşüş trendinde aynası short.
      hepsi    ikisi birden.
    Çıkış: karşı yön sinyali VEYA RSI(rsi_n) > rsi_ust (long) / < rsi_alt (short) (kitap: 5 günlük RSI 14/86); 1R'de stop girişe.
    ATLANDI: endeks puanı eşikleri (FTSE 100/140 puan), haftalık RSI 18/82 filtresi, 'doğrusal faz' ayrımı, 80 puanlık sabit stop."""
    ad = "dis__gann-swing-grafigi"
    stil = "swing"
    varsayilan_parametreler = {"mod": "hepsi", "swing_k": 3, "tampon_atr": 0.25, "devam_gun": 3, "rsi_n": 5, "rsi_ust": 86.0,
                               "rsi_alt": 14.0, "maks_risk_atr": 5.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["degisim", "devam", "hepsi"], "swing_k": [2, 3, 5], "tampon_atr": [0.25, 0.5, 1.0]}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0)

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        t = fraktal_pivotlar(h, d, int(p["swing_k"]))
        tr = swing_trendi(t)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        tamp = p["tampon_atr"] * a
        bos = _bos(m.index)
        L = S = bos
        sl = t["son_dip_fiyat"] - tamp
        ss = t["son_tepe_fiyat"] + tamp
        if p["mod"] in ("degisim", "hepsi"):
            L = L | ((tr == -1) & yukari_kesis(k, t["son_tepe_fiyat"]))
            S = S | ((tr == 1) & asagi_kesis(k, t["son_dip_fiyat"]))
        if p["mod"] in ("devam", "hepsi"):
            gun = int(p["devam_gun"])
            geri_dusus = ardisik_say(d < d.shift(1))
            geri_yukselis = ardisik_say(h > h.shift(1))
            dev_l = (tr == 1) & (geri_dusus.shift(1) >= gun) & (k > h.shift(1))
            dev_s = (tr == -1) & (geri_yukselis.shift(1) >= gun) & (k < d.shift(1))
            w = gun + 2
            sl = sl.where(~dev_l | L, d.rolling(w, min_periods=w).min() - tamp)
            ss = ss.where(~dev_s | S, h.rolling(w, min_periods=w).max() + tamp)
            L, S = L | dev_l, S | dev_s
        if p["mod"] not in ("degisim", "devam", "hepsi"):
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        L, S = _ymask(p, L, S)
        sl = risk_siniri_l(sl, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(ss, k, a, p["maks_risk_atr"])
        r = g.rsi(k, int(p["rsi_n"]))
        ham_l = (tr == -1) & yukari_kesis(k, t["son_tepe_fiyat"])
        ham_s = (tr == 1) & asagi_kesis(k, t["son_dip_fiyat"])
        return kur(m, L, S, sl, ss, None, None, ham_s | (r > p["rsi_ust"]), ham_l | (r < p["rsi_alt"]))


# =============================================================================== 7. ayın ilk günü
class AyinIlkGunuDeseni(_D10):
    """dis__ayin-ilk-gunu-deseni (swing, 1d) — Pruitt 'ayın ilk günü deseni (LBM)'. Ayın ilk işlem günü (ay değişimi): %Chg = (C[1]-C[2])/C[1]
    x 100 (ayın son gününün getirisi) < -esik ve bugünün kapanışı < açılışı -> kapanışta long; %Chg > esik ve kapanış > açılış -> short.
    Çıkış: giriş gününden `tut` bar sonra (kitap: 5. gün açılışı; sinyal gününden 5. gün ~ tut=3-4). Kitap stopu sabit dolar ->
    VARSAYIM stop_atr_k x ATR (2). Yalnız günlük (1d) bar anlamlıdır: 'ayın ilk günü' = ay değiştiren ilk bar."""
    ad = "dis__ayin-ilk-gunu-deseni"
    stil = "swing"
    varsayilan_parametreler = {"esik": 0.2, "tut": 4, "stop_atr_k": 2.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"esik": [0.1, 0.2, 0.5], "tut": [2, 4, 6], "stop_atr_k": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        ay = pd.Series(m.index.month, index=m.index)
        ilk = ay != ay.shift(1)
        chg = (k.shift(1) - k.shift(2)) / k.shift(1) * 100.0
        L = ilk & (chg < -p["esik"]) & (k < o)
        S = ilk & (chg > p["esik"]) & (k > o)
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kur(m, L, S, k - a, k + a, zaman_cikisi=float(p["tut"]))


# =============================================================================== 8. Lien 20 gün sahte kırılım
class Lien20GunSahteKirilim(_D10):
    """dis__lien-20-gun-sahte-kirilim (swing, 1d) — Lien '20 günlük sahte kırılım'. Long: bar a'da yüksek, önceki `pencere` barın en yükseğini
    aşar (20 günlük zirve); a'dan sonraki `geri_gun` bar içinde (b) düşük, önceki 2 barın dibinin altına iner; b'den sonraki `geri_gun` bar
    içinde (c) kapanış yeniden önceki `pencere` barın en yükseğini aşar -> long. Short ayna (20 günlük dip, 2 günlük zirve).
    Stop = b'deki iki günlük dip - tampon_atr*ATR (en çok maks_risk_atr). Çıkış: cikis_modu 'hedef' = hedef_r x risk hedefi; 'iz' = 2 barlık
    dip/zirve iz süren stop (kapanış önceki 2 barın dibinin altında). VARSAYIM: kitapta 'birkaç pip' = 0.25 ATR; sinyal kapanışta."""
    ad = "dis__lien-20-gun-sahte-kirilim"
    stil = "swing"
    varsayilan_parametreler = {"pencere": 20, "geri_gun": 3, "tampon_atr": 0.25, "maks_risk_atr": 6.0, "cikis_modu": "hedef",
                               "hedef_r": 2.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"pencere": [10, 20, 40], "geri_gun": [2, 3, 5], "cikis_modu": ["hedef", "iz"]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        w, gg = int(p["pencere"]), int(p["geri_gun"])
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        hh = h.shift(1).rolling(w, min_periods=w).max()
        ll = d.shift(1).rolling(w, min_periods=w).min()
        kirz, kird = h > hh, d < ll
        dip2 = d < np.minimum(d.shift(1), d.shift(2))
        zir2 = h > np.maximum(h.shift(1), h.shift(2))

        def pen(x):
            return x.shift(1).rolling(gg, min_periods=1).max() > 0
        b_l = dip2 & pen(kirz)
        b_s = zir2 & pen(kird)
        L = pen(b_l) & (k > hh)
        S = pen(b_s) & (k < ll)
        L, S = _ymask(p, L, S)
        t = p["tampon_atr"] * a
        sl = risk_siniri_l(d.where(b_l).shift(1).rolling(gg, min_periods=1).min() - t, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(h.where(b_s).shift(1).rolling(gg, min_periods=1).max() + t, k, a, p["maks_risk_atr"])
        if p["cikis_modu"] == "hedef":
            r = float(p["hedef_r"])
            return kur(m, L, S, sl, ss, k + r * (k - sl), k - r * (ss - k))
        if p["cikis_modu"] != "iz":
            raise ValueError(f"Bilinmeyen cikis_modu: {p['cikis_modu']!r}")
        return kur(m, L, S, sl, ss, None, None, k < np.minimum(d.shift(1), d.shift(2)), k > np.maximum(h.shift(1), h.shift(2)))


# =============================================================================== 9. MACD histogram pivot
class MacdHistogramPivot(_D10):
    """dis__macd-histogram-pivot (swing, 1d) — Pruitt/Appel 'MACD histogram pivot'. MACD(12,26,9) histogramında orta bar, solundaki ve
    sağındaki pivot_n (2) barın HEPSİNDEN düşük ve dış iki bar < 0 ise (dip pivot) long; zirve pivot ve dış barlar > 0 ise short.
    Pivot sağ pivot_n bar sonra bilinir: sinyal o onay barının kapanışında (gecikme gerçekçi). Stop = kapanış -/+ stop_k x ATR(10);
    hedef = kapanış +/- hedef_k x ATR(10) (kitap 1 ATR / 3 ATR)."""
    ad = "dis__macd-histogram-pivot"
    stil = "swing"
    varsayilan_parametreler = {"pivot_n": 2, "stop_k": 1.0, "hedef_k": 3.0, "atr_periyot": 10, "short": True}
    parametre_izgarasi = {"pivot_n": [2, 3], "stop_k": [1.0, 1.5, 2.0], "hedef_k": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["pivot_n"])
        hist = g.macd(k)["histogram"]
        mer = hist.shift(n)
        dip = pd.Series(True, index=m.index)
        tep = pd.Series(True, index=m.index)
        for j in range(2 * n + 1):
            if j != n:
                dip &= mer < hist.shift(j)
                tep &= mer > hist.shift(j)
        L = dip & (hist.shift(2 * n) < 0) & (hist < 0)
        S = tep & (hist.shift(2 * n) > 0) & (hist > 0)
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        return kur(m, L, S, k - p["stop_k"] * a, k + p["stop_k"] * a, k + p["hedef_k"] * a, k - p["hedef_k"] * a)


# =============================================================================== 10. SMA200 bant trend
class Sma200BandTrend(_D10):
    """dis__sma200-bant-trend (swing, 1d) — D'Errico 'SMA200 üstü volatilite bandı filtreli'. Long: kapanış > SMA(200) + k x StdDev(kapanış,
    200) (k=0.5) [filtre='bant']; alternatifler: 'iki_kapanis' = iki kapanış üst üste SMA200 üstünde, 'sma' = yalnız SMA200 üstü.
    Durum sinyali (koşul sürdükçe, pozisyon yokken yeniden girilir). Çıkış: `tut` bar sonra (kitap 20). Kitapta stop yok -> VARSAYIM
    stop_atr_k (3) x ATR felaket stopu. Kitap yalnız long (short=False varsayılan; True: SMA200 - k std altında short, aynı çıkış)."""
    ad = "dis__sma200-bant-trend"
    stil = "swing"
    varsayilan_parametreler = {"sma_n": 200, "k": 0.5, "filtre": "bant", "tut": 20, "stop_atr_k": 3.0, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"k": [0.0, 0.5, 1.0], "tut": [10, 20, 40], "stop_atr_k": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["sma_n"])
        sma = g.sma(k, n)
        sd = k.rolling(n, min_periods=n).std(ddof=0)
        if p["filtre"] == "bant":
            L, S = k > sma + p["k"] * sd, k < sma - p["k"] * sd
        elif p["filtre"] == "iki_kapanis":
            L, S = (k > sma) & (k.shift(1) > sma.shift(1)), (k < sma) & (k.shift(1) < sma.shift(1))
        elif p["filtre"] == "sma":
            L, S = k > sma, k < sma
        else:
            raise ValueError(f"Bilinmeyen filtre: {p['filtre']!r}")
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kur(m, L, S, k - a, k + a, zaman_cikisi=float(p["tut"]))


# =============================================================================== 11. üç mum swing noktası
class UcMumSwingNoktasi(_D10):
    """dis__uc-mum-swing-noktasi (swing, 1d) — Anderson 'swing noktası dönüş girişi'. Swing dip (3 mum): 1. mum dip, 2. mum daha düşük dip
    (d[t-1] < d[t-2]), 3. mum (sinyal barı) daha yüksek dip (d[t] > d[t-1]) VE önceki günün yükseğinin üzerinde (kapanis_teyit=True ise
    KAPANIŞ > h[t-1], aksi halde h[t] > h[t-1]); öncesinde en az geri_n ardışık düşüş kapanışı (geri çekilme). Short: swing tepe aynası.
    agresif=True: 2. mumda (d[t] < d[t-1]) çekiç / boğa yutan mum varsa o mumda giriş (stop o mumun dibi). Stop = swing dibi - tampon_atr*ATR,
    risk en az min_risk_atr (kitap: normal günlük aralıktan küçük olmasın), en çok maks_risk_atr ATR. Çıkış: kapanış > SMA10 + uzama_atr*ATR
    (kitap: 10 periyot MA'dan fazla uzayınca kâr al) VEYA `zaman` bar (zaman stopu; kitapta gün sayısı yok -> VARSAYIM 10).
    ATLANDI: destek/direnç bölgesi güven filtresi (öznel)."""
    ad = "dis__uc-mum-swing-noktasi"
    stil = "swing"
    varsayilan_parametreler = {"geri_n": 2, "kapanis_teyit": False, "agresif": False, "tampon_atr": 0.25, "min_risk_atr": 0.5,
                               "maks_risk_atr": 5.0, "uzama_atr": 2.0, "zaman": 10, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"geri_n": [1, 2, 3], "tampon_atr": [0.25, 0.5, 1.0], "uzama_atr": [1.0, 2.0, 3.0]}

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        gn = int(p["geri_n"])
        dus = ardisik_say(k < k.shift(1)).shift(1) >= gn
        yuk = ardisik_say(k > k.shift(1)).shift(1) >= gn
        ust_ok = (k > h.shift(1)) if p["kapanis_teyit"] else (h > h.shift(1))
        alt_ok = (k < d.shift(1)) if p["kapanis_teyit"] else (d < d.shift(1))
        L = dus & (d.shift(1) < d.shift(2)) & (d > d.shift(1)) & ust_ok
        S = yuk & (h.shift(1) > h.shift(2)) & (h < h.shift(1)) & alt_ok
        sw_d, sw_h = d.shift(1), h.shift(1)
        if p["agresif"]:
            boga_yut = (k > o) & (o <= k.shift(1)) & (k >= o.shift(1)) & (k.shift(1) < o.shift(1))
            ayi_yut = (k < o) & (o >= k.shift(1)) & (k <= o.shift(1)) & (k.shift(1) > o.shift(1))
            ag_l = dus & (d < d.shift(1)) & (cekic(m) | boga_yut)
            ag_s = yuk & (h > h.shift(1)) & (ters_cekic(m) | ayi_yut)
            sw_d, sw_h = sw_d.where(~ag_l | L, d), sw_h.where(~ag_s | S, h)
            L, S = L | ag_l, S | ag_s
        L, S = _ymask(p, L, S)
        t = p["tampon_atr"] * a
        sl = np.minimum(sw_d - t, k - p["min_risk_atr"] * a)
        ss = np.maximum(sw_h + t, k + p["min_risk_atr"] * a)
        sl = risk_siniri_l(sl, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(ss, k, a, p["maks_risk_atr"])
        s10 = g.sma(k, 10)
        return kur(m, L, S, sl, ss, None, None, k > s10 + p["uzama_atr"] * a, k < s10 - p["uzama_atr"] * a,
                   zaman_cikisi=float(p["zaman"]))


# =============================================================================== 12. yeni zirve trend filtresi
class YeniZirveTrendFiltresi(_D10):
    """dis__yeni-zirve-trend-filtresi (swing, 1d) — D'Errico '200 gün zirve, yeni yüksek'. Long: En yüksek(Yüksek, n) >= En yüksek(Yüksek, n)[lag]
    (n=200, lag=20; alternatif 50/10) -> long durumu; koşul bozulunca (yeni zirve yok) çık. Kitapta stop yok -> VARSAYIM stop_atr_k (3) x ATR.
    Yalnız long (kitap)."""
    ad = "dis__yeni-zirve-trend-filtresi"
    stil = "swing"
    varsayilan_parametreler = {"n": 200, "lag": 20, "stop_atr_k": 3.0, "atr_periyot": 14}
    parametre_izgarasi = {"n": [50, 100, 200], "lag": [10, 20, 40], "stop_atr_k": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["n"])
        hh = h.rolling(n, min_periods=n).max()
        yeni_zirve = hh >= hh.shift(int(p["lag"]))
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        bos = _bos(m.index)
        return kur(m, yeni_zirve & hh.shift(int(p["lag"])).notna(), bos, k - a, k + a, None, None, ~yeni_zirve, bos)


# =============================================================================== 13. hafta içi takvim
class HaftaIciTakvim(_D10):
    """dis__hafta-ici-takvim (swing, 1d; kartta swing/daytrade) — hafta günü takvim etkileri. mod:
      cuma_pzt     (Bernstein) Cuma kapanışı > açılışı -> pazartesi long (düşükse short); `tut` bar sonra çık. Kitaptaki 'Cuma zirvesi + N
                   puan buy stop' girişi ve gün sonu çıkışı günlük barda temsil edilemez: ertesi açılışta giriş.
      pzt_sali     (Turnaround Tuesday, repo) Pazartesi kapanışı < önceki (cuma) kapanışı ve IBS=(C-L)/(H-L) < 0.5 -> long; kapanış önceki
                   yükseği aşınca veya `tut` bar sonra çık. Short ayna (pazartesi yukarı, IBS > 0.5).
      sali_persembe (Crude Oil Tue/Thu, repo) Salı/Perşembe kapanışı önceki kapanıştan 1 x ADR(25) kadar düşükse long; `tut` bar sonra çık.
    Hafta günü mumun UTC açılış gününden alınır (hafta sonu işlem gören kriptoda 'pazartesi' etkisi anlamlı değildir; hisse/emtia için).
    ATLANDI: Blue Monday DAX (5 dk, 08:55-09:55 saat çıkışı, DAX puan eşiği), Monday/Tuesday Nasdaq ve Monday reversal S&P ('kurallar üyelere
    özel': kural yok). VARSAYIM: kitapta stop sabit dolar -> stop_atr_k x ATR."""
    ad = "dis__hafta-ici-takvim"
    stil = "swing"
    varsayilan_parametreler = {"mod": "pzt_sali", "tut": 1, "stop_atr_k": 2.0, "adr_n": 25, "adr_k": 1.0, "ibs_esik": 0.5,
                               "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"mod": ["cuma_pzt", "pzt_sali", "sali_persembe"], "stop_atr_k": [2.0, 3.0, 4.0], "tut": [1, 2, 4]}

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        gun = pd.Series(m.index.dayofweek, index=m.index)
        bos = _bos(m.index)
        cL = cS = bos
        if p["mod"] == "cuma_pzt":
            L, S = (gun == 4) & (k > o), (gun == 4) & (k < o)
        elif p["mod"] == "pzt_sali":
            ibs = (k - d) / (h - d).where(h != d)
            L = (gun == 0) & (k < k.shift(1)) & (ibs < p["ibs_esik"])
            S = (gun == 0) & (k > k.shift(1)) & (ibs > 1 - p["ibs_esik"])
            cL, cS = k > h.shift(1), k < d.shift(1)
        elif p["mod"] == "sali_persembe":
            n = int(p["adr_n"])
            adr = (h - d).rolling(n, min_periods=n).mean().shift(1)
            gg = gun.isin([1, 3])
            L = gg & (k < k.shift(1) - p["adr_k"] * adr)
            S = gg & (k > k.shift(1) + p["adr_k"] * adr)
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kur(m, L, S, k - a, k + a, None, None, cL, cS, zaman_cikisi=float(p["tut"]))


# =============================================================================== 14. Arps pivot desenleri
class ArpsPivotDesenleri(_D10):
    """dis__arps-pivot-desenleri (swing, 1d) — Arps ZigZag desenleri; pivotlar ATR zigzag (esik_k x ATR geri dönüş) ile ONAYLANIR (gecikmeli).
      uc_dalga  5 ardışık pivot P1..P5 (dip,tepe,dip,tepe,dip): P5>P3>P1 ve P4>P2 -> P5 onay barında long (short: tepe,dip,tepe,dip,tepe ve
                P5<P3<P1, P4<P2; kitaptaki 'P3<P5' çeviri hatası, P3<P1 kastedilmiş). Stop: P5 -/+ stop_tampon_atr*ATR; kitapta stop/hedef yok
                -> VARSAYIM hedef_r x R.
      fox       P1..P4 (dip,tepe,dip,tepe): P2>P1, P4>P3, P4<P2, P3<P1, P4>P1 ve (x2-x1) > (x4-x3) (yatay mesafe). 'Giriş çizgisi' = P1-P3
                doğrusunun uzantısı, 'hedef çizgisi' = P1-P4. Fiyat P4'ten geri çekilip giriş çizgisine dokununca (düşük <= çizgi + tol_atr*ATR)
                ve çizgi üstünde kapatınca (P5) long; hedef = P1-P4 çizgisinin o anki değeri (+ hedef_ufuk bar ileri); stop = giriş çizgisi -
                stop_tampon_atr*ATR. Short ayna.
    ATLANDI: 2-4 hedef zamanlama çizgisi (kitapta zorunluluğu belirsiz)."""
    ad = "dis__arps-pivot-desenleri"
    stil = "swing"
    varsayilan_parametreler = {"mod": "uc_dalga", "esik_k": 3.0, "stop_tampon_atr": 0.5, "hedef_r": 2.0, "tol_atr": 0.5,
                               "hedef_ufuk": 0, "maks_risk_atr": 6.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["uc_dalga", "fox"], "esik_k": [2.0, 3.0, 4.0], "hedef_r": [1.5, 2.0, 3.0]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = len(m)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        tab = zigzag_pivotlar(h, d, k, int(p["atr_periyot"]), float(p["esik_k"]))
        o, t, pi, f = pivot_olaylari(tab)
        tamp = p["stop_tampon_atr"] * a
        if p["mod"] == "uc_dalga":
            Ln, Sn = np.zeros(n, bool), np.zeros(n, bool)
            ref_l, ref_s = np.full(n, np.nan), np.full(n, np.nan)
            for i in range(4, len(o)):
                seg = list(t[i - 4:i + 1])
                p1, p2, p3, p4, p5 = f[i - 4:i + 1]
                if seg == [-1, 1, -1, 1, -1] and p5 > p3 > p1 and p4 > p2:
                    Ln[o[i]] = True; ref_l[o[i]] = p5
                elif seg == [1, -1, 1, -1, 1] and p5 < p3 < p1 and p4 < p2:
                    Sn[o[i]] = True; ref_s[o[i]] = p5
            L, S = pd.Series(Ln, index=m.index), pd.Series(Sn, index=m.index)
            L, S = _ymask(p, L, S)
            sl = risk_siniri_l(pd.Series(ref_l, index=m.index) - tamp, k, a, p["maks_risk_atr"])
            ss = risk_siniri_s(pd.Series(ref_s, index=m.index) + tamp, k, a, p["maks_risk_atr"])
            r = float(p["hedef_r"])
            return kur(m, L, S, sl, ss, k + r * (k - sl), k - r * (ss - k))
        if p["mod"] != "fox":
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        # fox: her bar için en son onaylı 4 pivottan desen (ileri doldurma, bir sonraki pivot onayına kadar)
        gecerli = np.zeros(n, np.int8)                # +1 yükseliş dalgası, -1 düşüş dalgası
        X = np.full((4, n), np.nan)                   # x1, x3, x4 ve p1, p3, p4 için ayrı diziler aşağıda
        x1, x3, x4 = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        y1, y3, y4 = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        for i in range(3, len(o)):
            seg = list(t[i - 3:i + 1])
            q1, q2, q3, q4 = f[i - 3:i + 1]
            a1, a2, a3, a4 = pi[i - 3:i + 1]
            if seg == [-1, 1, -1, 1] and q2 > q1 and q4 > q3 and q4 < q2 and q3 < q1 and q4 > q1 and (a2 - a1) > (a4 - a3):
                yon = 1
            elif seg == [1, -1, 1, -1] and q2 < q1 and q4 < q3 and q4 > q2 and q3 > q1 and q4 < q1 and (a2 - a1) > (a4 - a3):
                yon = -1
            else:
                continue
            bas = o[i]
            son = o[i + 1] if i + 1 < len(o) else n
            gecerli[bas:son] = yon
            x1[bas:son], x3[bas:son], x4[bas:son] = a1, a3, a4
            y1[bas:son], y3[bas:son], y4[bas:son] = q1, q3, q4
        ix = np.arange(n, dtype=float)
        s13 = (y3 - y1) / (x3 - x1)
        s14 = (y4 - y1) / (x4 - x1)
        giris = pd.Series(y3 + s13 * (ix - x3), index=m.index)       # giriş çizgisi (P1-P3 uzantısı)
        hedef = pd.Series(y1 + s14 * (ix - x1) + s14 * float(p["hedef_ufuk"]), index=m.index)
        tol = p["tol_atr"] * a
        g_s = pd.Series(gecerli, index=m.index)
        L = gecis((g_s == 1) & (d <= giris + tol) & (k >= giris) & (k < hedef))
        S = gecis((g_s == -1) & (h >= giris - tol) & (k <= giris) & (k > hedef))
        L, S = _ymask(p, L, S)
        sl = risk_siniri_l(giris - tamp, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(giris + tamp, k, a, p["maks_risk_atr"])
        return kur(m, L, S, sl, ss, hedef, hedef)


# =============================================================================== 15. nokta & şekil
class NoktaSekil(_D10):
    """dis__nokta-sekil (swing, 1d) — Rivalland Nokta&Şekil: üçlü tepe/dip kırılımı ve boğa/ayı sarsıntısı. Grafik: yüzde kutulu (kutu = fiyatın
    kutu oranı, log ölçek), `ters` (3) kutu geri dönüş, yüksek/düşük ile kurulur (bkz. _gosterge_d10a.nokta_sekil_sinyalleri).
      ucle_tepe  İki önceki X sütunu tepesi eşit (|fark| <= tol kutu), O dipleri yükseliyor, güncel X sütunu üçlü tepenin 1 kutu üstüne çıkınca
                 long (stop: son O sütununun dibi); aynası üçlü dip kırılımı short.
      sarsinti   Önceki sinyal yükseliş (önceki X tepesi bir öncekini aşmış), çift dip (eşit O dipleri) 1-3 kutu aşağı kırılır ve 3 kutu
                 yukarı dönüş olursa long; stop sarsıntı dibinin stop_ek (4) kutu altı. Short ayna (ayı sarsıntısı).
      hepsi      ikisi birden.
    Çıkış (kitapta hedef/çıkış yok -> VARSAYIM): karşı P&F sinyali (long için ayı sinyali: O sütunu önceki O dibinin altına iner); stop
    en çok maks_risk_atr ATR uzak. VARSAYIM: kutu yüzde 2 (kitap endeks puan kutusu verir), tol=0 kutu (ızgarada 0/1)."""
    ad = "dis__nokta-sekil"
    stil = "swing"
    varsayilan_parametreler = {"mod": "hepsi", "kutu": 0.02, "ters": 3, "tol": 0, "stop_ek": 4, "maks_risk_atr": 6.0,
                               "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["ucle_tepe", "sarsinti", "hepsi"], "kutu": [0.01, 0.02, 0.04], "tol": [0, 1, 2]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        if p["mod"] not in ("ucle_tepe", "sarsinti", "hepsi"):
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        r = nokta_sekil_sinyalleri(h, d, float(p["kutu"]), int(p["ters"]), int(p["tol"]), int(p["stop_ek"]),
                                   ucle=p["mod"] in ("ucle_tepe", "hepsi"), sarsinti=p["mod"] in ("sarsinti", "hepsi"))
        L, S = _ymask(p, r["long"], r["short"])
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        sl = risk_siniri_l(r["stop_l"], k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(r["stop_s"], k, a, p["maks_risk_atr"])
        return kur(m, L, S, sl, ss, None, None, r["cikis_l"], r["cikis_s"])


# =============================================================================== 16. Granville MA kuralları
class GranvilleMaKurallari(_D10):
    """dis__granville-ma-kurallari (swing, 1d) — Lee/Tryde 'MA sekiz kural' (Granville). Eğim = MA/MA[egim_n] - 1; yükseliyor > egim_esik,
    düşüyor < -egim_esik, aksi 'düz'. Kurallar (long 1-4, short 5-8; `kurallar` dizgesi hangilerinin açık olduğunu seçer):
      1 kapanış MA'yı yukarı keser, MA düşmüyor        5 kapanış MA'yı aşağı keser, MA yükselmiyor
      2 kapanış MA'yı aşağı keser ama MA yükseliyor    6 kapanış MA'yı yukarı keser ama MA düşüyor
      3 MA yükselirken fiyat MA'ya geri çekilir (düşük <= MA + temas_atr*ATR), MA altına geçmeden yeşil mumla döner
      7 MA düşerken fiyat MA'ya yükselir (yüksek >= MA - temas_atr*ATR), geçemeden kırmızı mumla döner
      4 MA düşerken fiyat MA'nın asiri_atr*ATR'den fazla altında ve yeşil mum -> ortalamaya doğru kısa vadeli long (hedef = MA)
      8 MA yükselirken fiyat MA'nın asiri_atr*ATR'den fazla üstünde ve kırmızı mum -> kısa vadeli short (hedef = MA)
    Çıkış: long için 5/6/7 sinyalleri (ters sinyal), short için 1/2/3; stop_atr_k x ATR (kitapta stop yok -> VARSAYIM). 'Çok altına/üstüne' ve
    'düzleşme' eşikleri kitapta yok -> asiri_atr (5), egim_esik (0.002) VARSAYIM. MA türü SMA."""
    ad = "dis__granville-ma-kurallari"
    stil = "swing"
    varsayilan_parametreler = {"ma_n": 200, "egim_n": 20, "egim_esik": 0.002, "temas_atr": 0.5, "asiri_atr": 5.0, "kurallar": "12345678",
                               "stop_atr_k": 3.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"ma_n": [100, 150, 200], "egim_esik": [0.0, 0.002, 0.005], "asiri_atr": [3.0, 5.0, 8.0]}

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        ma = g.sma(k, int(p["ma_n"]))
        eg = ma / ma.shift(int(p["egim_n"])) - 1.0
        e = p["egim_esik"]
        cu, cd = yukari_kesis(k, ma), asagi_kesis(k, ma)
        tm = p["temas_atr"] * a
        r = {
            1: cu & (eg >= -e), 2: cd & (eg > e),
            3: (k > ma) & (d <= ma + tm) & (d > ma - tm) & (k > o) & (eg > e),
            4: ((ma - k) > p["asiri_atr"] * a) & (k > o) & (eg < -e),
            5: cd & (eg <= e), 6: cu & (eg < -e),
            7: (k < ma) & (h >= ma - tm) & (h < ma + tm) & (k < o) & (eg < -e),
            8: ((k - ma) > p["asiri_atr"] * a) & (k < o) & (eg > e)}
        acik = {int(c) for c in str(p["kurallar"])}
        bos = _bos(m.index)
        L = S = bos
        for i in (1, 2, 3, 4):
            if i in acik:
                L = L | r[i]
        for i in (5, 6, 7, 8):
            if i in acik:
                S = S | r[i]
        L, S = _ymask(p, L, S)
        s_ = a * p["stop_atr_k"]
        hedef_l = ma.where((4 in acik) & r[4] & ~(r[1] | r[2] | r[3]))
        hedef_s = ma.where((8 in acik) & r[8] & ~(r[5] | r[6] | r[7]))
        return kur(m, L, S, k - s_, k + s_, hedef_l, hedef_s, r[5] | r[6] | r[7], r[1] | r[2] | r[3])


# =============================================================================== 17. MA20 + RSI trend çizgisi + CMF
class Ma20RsiCmf(_D10):
    """dis__ma20-rsi-cmf (swing, 4h) — 'MA20 + RSI momentum + CMF'. Long: (1) aynı mumda fiyat SMA(20)'yi yukarı kırar ve üstünde kapatır
    (açılış < MA < kapanış); (2) RSI(rsi_n) düşen trend çizgisini yukarı kırar [ölçülebilir tanım: RSI'nın son iki onaylı fraktal zirvesi
    (rsi_pivot_k) alçalıyorsa bu iki zirveden geçen doğrunun uzantısı; çizgi çizilemezse işlem atlanır]; (3) Chaikin Money Flow(cmf_n)
    sıfırı yukarı keser. Üç olay en çok `pencere` bar içinde gerçekleşmiş ve üçü de o an geçerli (kapanış>MA, RSI>çizgi, CMF>0) olmalı.
    Short (kitapta anlatılmıyor, simetri VARSAYIMI): MA'yı aşağı kırar, RSI'nın yükselen dip çizgisini aşağı kırar, CMF<0. Stop = MA20 -
    tampon_atr*ATR (en çok maks_risk_atr). Çıkış: CMF sıfırın altına düşünce (short: üstüne çıkınca). Hacim gerekir. 4h ve üstü."""
    ad = "dis__ma20-rsi-cmf"
    stil = "swing"
    varsayilan_parametreler = {"ma_n": 20, "rsi_n": 20, "rsi_pivot_k": 2, "cmf_n": 20, "pencere": 3, "tampon_atr": 0.25,
                               "maks_risk_atr": 5.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"pencere": [1, 3, 5], "rsi_n": [14, 20, 28], "cmf_n": [10, 20, 30]}

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k, v = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        ma = g.sma(k, int(p["ma_n"]))
        r = g.rsi(k, int(p["rsi_n"]))
        c = cmf(h, d, k, v, int(p["cmf_n"]))
        t = fraktal_pivotlar(r, r, int(p["rsi_pivot_k"]))
        ix = pd.Series(np.arange(len(m), dtype=float), index=m.index)

        def cizgi(son_f, son_i, onc_f, onc_i, alcalan):
            egim = (son_f - onc_f) / (son_i - onc_i)
            gecerli = (son_f < onc_f) if alcalan else (son_f > onc_f)
            return (son_f + egim * (ix - son_i)).where(gecerli)
        c_dus = cizgi(t["son_tepe_fiyat"], t["son_tepe_idx"], t["onceki_tepe_fiyat"], t["onceki_tepe_idx"], True)
        c_yuk = cizgi(t["son_dip_fiyat"], t["son_dip_idx"], t["onceki_dip_fiyat"], t["onceki_dip_idx"], False)
        w = int(p["pencere"])

        def son(x):
            return x.rolling(w, min_periods=1).max() > 0
        L = gecis((k > ma) & (r > c_dus) & (c > 0)) & son((o < ma) & (k > ma)) & son(yukari_kesis(r, c_dus)) & son(yukari_kesis(c, 0.0))
        S = gecis((k < ma) & (r < c_yuk) & (c < 0)) & son((o > ma) & (k < ma)) & son(asagi_kesis(r, c_yuk)) & son(asagi_kesis(c, 0.0))
        L, S = _ymask(p, L, S)
        t_ = p["tampon_atr"] * a
        sl = risk_siniri_l(ma - t_, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(ma + t_, k, a, p["maks_risk_atr"])
        return kur(m, L, S, sl, ss, None, None, c < 0, c > 0)


# =============================================================================== 18. Ochoa genişleme günü
class OchoaGenislemeGunu(_D10):
    """dis__ochoa-genisleme-gunu (swing, 1d) — Ochoa 'stop run günü' (aralık genişleme günü). Genişleme günü D: aralık (H-L) > adr_k x ADR(adr_n)
    [ADR = önceki adr_n günün ortalama aralığı] VE kapanış önceki günün yükseğinin (yHI) üzerinde VE günün üst ust_yuzde'sinde (kapanış >=
    H - ust_yuzde*aralık) VE orta nokta önceki zirve_n günün en yükseğinin üzerinde. Short aynası (yLO altında, alt %15, orta nokta önceki dibin altında).
      mod 'kapanis'   : D'nin kapanışında long (kitaptaki 'günün erken saatlerinde çıkış' girişinin günlük bar karşılığı).
      mod 'geri_test' : D'den sonraki `bekle` bar içinde fiyat yHI'ye yukarıdan geri dönüp test eder (düşük <= yHI + tol_atr*ATR) ve yHI üstünde
                        kapatırsa long (kitap Giriş 2: yHI'nin yeniden testi).
    Stop = yLO (D'den bir önceki günün dibi) - tampon_atr*ATR (kitap: yLO altında kapanış çık), en çok maks_risk_atr ATR; hedef = 2*yHI - L_D
    (gün aralığının yHI üzerine yansıtılması), en az 1R; ayrıca `zaman` bar sonra çık (VARSAYIM 20; kitap swing yönetimini belirtmiyor)."""
    ad = "dis__ochoa-genisleme-gunu"
    stil = "swing"
    varsayilan_parametreler = {"mod": "geri_test", "adr_n": 20, "adr_k": 2.0, "ust_yuzde": 0.15, "zirve_n": 10, "bekle": 3,
                               "tol_atr": 0.5, "tampon_atr": 0.25, "maks_risk_atr": 5.0, "zaman": 20, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["kapanis", "geri_test"], "adr_k": [1.5, 2.0, 2.5], "bekle": [2, 3, 5]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        aralik = h - d
        n = int(p["adr_n"])
        adr = aralik.rolling(n, min_periods=n).mean().shift(1)
        yhi, ylo = h.shift(1), d.shift(1)
        zn = int(p["zirve_n"])
        gen = aralik > p["adr_k"] * adr
        orta = (h + d) / 2.0
        l_gun = gen & (k > yhi) & ((h - k) <= p["ust_yuzde"] * aralik) & (orta > h.shift(1).rolling(zn, min_periods=zn).max())
        s_gun = gen & (k < ylo) & ((k - d) <= p["ust_yuzde"] * aralik) & (orta < d.shift(1).rolling(zn, min_periods=zn).min())
        tamp = p["tampon_atr"] * a
        if p["mod"] == "kapanis":
            L, S = l_gun, s_gun
            sl, ss = ylo - tamp, yhi + tamp
            hl, hs = 2 * yhi - d, 2 * ylo - h
        elif p["mod"] == "geri_test":
            bos = _bos(m.index)
            L = S = bos
            nan = pd.Series(np.nan, index=m.index)
            sl = ss = hl = hs = nan
            for j in range(int(p["bekle"]), 0, -1):          # küçük j (en yeni genişleme günü) en son yazılır
                gl, gs = l_gun.shift(j, fill_value=False), s_gun.shift(j, fill_value=False)
                yh, yl_ = yhi.shift(j), ylo.shift(j)
                tl = gl & (d <= yh + p["tol_atr"] * a) & (k > yh)
                ts = gs & (h >= yl_ - p["tol_atr"] * a) & (k < yl_)
                sl, ss = sl.where(~tl, yl_ - tamp), ss.where(~ts, yh + tamp)
                hl = hl.where(~tl, 2 * yh - d.shift(j))
                hs = hs.where(~ts, 2 * yl_ - h.shift(j))
                L, S = L | tl, S | ts
            L, S = gecis(L), gecis(S)
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        L, S = _ymask(p, L, S)
        sl = risk_siniri_l(sl, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(ss, k, a, p["maks_risk_atr"])
        hl = np.maximum(hl, k + (k - sl))
        hs = np.minimum(hs, k - (ss - k))
        return kur(m, L, S, sl, ss, hl, hs, zaman_cikisi=float(p["zaman"]))


# =============================================================================== 19. RSI failure swing
class RsiFailureSwing(_D10):
    """dis__rsi-failure-swing (swing, 1d) — Pruitt/Wilder RSI 'failure swing'. RSI(14) pivotları fraktal (pivot_k; kitap 1 bar sağ-sol).
    Long: RSI < alt_esik (30) altında pivot dip, ardından pivot zirve, ardından ikinci pivot dip ilk dibin ÜSTÜNDE (başarısız dip) ve RSI ara
    zirvenin üstüne YUKARI keserse long (ikinci dip en çok maks_yas bar önce). Short: RSI > ust_esik (70) üstünde pivot zirve, ara dip,
    ikinci zirve ilkini geçemez, RSI ara dibin altına inerse short. Stop = kapanış -/+ stop_k x ATR(10), hedef = kapanış +/- hedef_k x ATR(10)
    (kitap short için 3 ATR stop / 1 ATR hedef; long için simetri VARSAYIMI)."""
    ad = "dis__rsi-failure-swing"
    stil = "swing"
    varsayilan_parametreler = {"rsi_n": 14, "pivot_k": 1, "alt_esik": 30.0, "ust_esik": 70.0, "maks_yas": 20, "stop_k": 3.0,
                               "hedef_k": 1.0, "atr_periyot": 10, "short": True}
    parametre_izgarasi = {"pivot_k": [1, 2, 3], "stop_k": [2.0, 3.0, 4.0], "hedef_k": [1.0, 2.0, 3.0]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        t = fraktal_pivotlar(r, r, int(p["pivot_k"]))
        ix = pd.Series(np.arange(len(m), dtype=float), index=m.index)
        L = ((t["onceki_dip_fiyat"] < p["alt_esik"]) & (t["son_dip_fiyat"] > t["onceki_dip_fiyat"])
             & (t["onceki_dip_idx"] < t["son_tepe_idx"]) & (t["son_tepe_idx"] < t["son_dip_idx"])
             & ((ix - t["son_dip_idx"]) <= p["maks_yas"]) & yukari_kesis(r, t["son_tepe_fiyat"]))
        S = ((t["onceki_tepe_fiyat"] > p["ust_esik"]) & (t["son_tepe_fiyat"] < t["onceki_tepe_fiyat"])
             & (t["onceki_tepe_idx"] < t["son_dip_idx"]) & (t["son_dip_idx"] < t["son_tepe_idx"])
             & ((ix - t["son_tepe_idx"]) <= p["maks_yas"]) & asagi_kesis(r, t["son_dip_fiyat"]))
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        return kur(m, L, S, k - p["stop_k"] * a, k + p["stop_k"] * a, k + p["hedef_k"] * a, k - p["hedef_k"] * a)


# =============================================================================== 20. SST DMI + 50 SMA
class SstDmi50ma(_D10):
    """dis__sst-dmi-50ma (swing, 1d) — Graeme Smith 'SST: 50 SMA + DMI onayı'. Long: kapanış > SMA(50); +DI(8) -DI(8)'i son aday_n bar içinde
    yukarı kesmiş ve hâlâ üstünde (aday; 'dokunup uzaklaşma' ayrıca kodlanmadı, sayısal eşik yok); kapanış 'son önemli zirveyi' (önceki zirve_n
    barın en yükseği) aşınca long (fiyat onayı). Short ayna (-DI +DI'yi keser, kapanış son zirve_n barın dibinin altına iner). Stop = son önemli dip
    (önceki zirve_n barın dibi) - %0.5 x kapanış (kitap tampon), en çok maks_risk_atr ATR. Çıkış: iz süren stop = kapanış önceki iz_n barın dibinin
    altına iner (kitap: yeni önemli günün dibine taşı; 'önemli gün' = iz_n barlık dip VARSAYIM). ATLANDI: %5 'büyük hareket günü' %50 stop kuralı, hisse
    kişiliği seçimi."""
    ad = "dis__sst-dmi-50ma"
    stil = "swing"
    varsayilan_parametreler = {"sma_n": 50, "dmi_n": 8, "aday_n": 5, "zirve_n": 20, "iz_n": 10, "tampon_yuzde": 0.005,
                               "maks_risk_atr": 6.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"zirve_n": [10, 20, 40], "aday_n": [3, 5, 10], "iz_n": [5, 10, 20]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        di = g.adx(h, d, k, int(p["dmi_n"]))
        ap, em = di["arti_di"], di["eksi_di"]
        s50 = g.sma(k, int(p["sma_n"]))
        w = int(p["aday_n"])
        aday_l = (yukari_kesis(ap, em).rolling(w, min_periods=1).max() > 0) & (ap > em)
        aday_s = (asagi_kesis(ap, em).rolling(w, min_periods=1).max() > 0) & (ap < em)
        zn, iz = int(p["zirve_n"]), int(p["iz_n"])
        zirve = h.shift(1).rolling(zn, min_periods=zn).max()
        dip = d.shift(1).rolling(zn, min_periods=zn).min()
        L = gecis((k > s50) & aday_l & (k > zirve))
        S = gecis((k < s50) & aday_s & (k < dip))
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        sl = risk_siniri_l(dip - p["tampon_yuzde"] * k, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(zirve + p["tampon_yuzde"] * k, k, a, p["maks_risk_atr"])
        cL = k < d.shift(1).rolling(iz, min_periods=iz).min()
        cS = k > h.shift(1).rolling(iz, min_periods=iz).max()
        return kur(m, L, S, sl, ss, None, None, cL, cS)


# =============================================================================== 21. volatilite sıkışma reversal
class VolatiliteSikismaReversal(_D10):
    """dis__volatilite-sikisma-reversal (swing, 1d) — D'Errico 'reversal volatilite sıkışması kırılımı'. VoltyRatio = (HH(len1)-LL(len1)) /
    (HH(len2)-LL(len2)). Kurulum barı: VoltyRatio < tetik (0.9) VE kapanış < SMA(pull_n=5) (düşüş içinde) -> direnç = HH(len1) kaydedilir;
    sonraki `bekle` (10) bar içinde kapanış bu direnci aşarsa long. Short aynası: VoltyRatio < tetik VE kapanış > SMA(pull_n) -> destek = LL(len1);
    kapanış desteğin altına inerse short. Çıkış: `tut` (15) bar sonra (kitap). Kitapta stop yok -> VARSAYIM stop_atr_k (2.5) x ATR. Kitap short'u
    'deneysel' diye uyarır."""
    ad = "dis__volatilite-sikisma-reversal"
    stil = "swing"
    varsayilan_parametreler = {"len1": 14, "len2": 46, "tetik": 0.9, "pull_n": 5, "bekle": 10, "tut": 15, "stop_atr_k": 2.5,
                               "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"len1": [10, 14, 20], "tetik": [0.5, 0.7, 0.9], "bekle": [5, 10, 15]}

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        l1, l2 = int(p["len1"]), int(p["len2"])
        hh, ll = h.rolling(l1, min_periods=l1).max(), d.rolling(l1, min_periods=l1).min()
        oran = (hh - ll) / (h.rolling(l2, min_periods=l2).max() - d.rolling(l2, min_periods=l2).min())
        sik = oran < p["tetik"]
        sma = g.sma(k, int(p["pull_n"]))
        b = int(p["bekle"])
        direnc = hh.where(sik & (k < sma)).ffill(limit=b).shift(1)
        destek = ll.where(sik & (k > sma)).ffill(limit=b).shift(1)
        L = gecis((k > direnc) & direnc.notna())
        S = gecis((k < destek) & destek.notna())
        L, S = _ymask(p, L, S)
        a = g.atr(h, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kur(m, L, S, k - a, k + a, zaman_cikisi=float(p["tut"]))


# =============================================================================== 22. EMA kesişim 123 kurulumu
class EmaKesisim123Kurulumu(_D10):
    """dis__ema-kesisim-123-kurulumu (swing, 1d; üst filtre 1w) — Mermigas 'EMA12/36 + 123 kurulumu' (kodlanabilirlik düşük: öznel kısımlar yaklaşıkla).
    Long: (a) üst zaman diliminde (ust_tf='1w'; boş = kapalı) EMA12 > EMA36; (b) günlük EMA12 > EMA36 ve EMA12, EMA36'yı son kes_pencere barda
    yukarı kesmiş; (c) geri çekilme: son geri_n barın dibi EMA36'ya yakın (dip - EMA36 <= yakin_atr*ATR) ve bu pencerede en az bir kırmızı Heikin Ashi
    mumu, şimdi HA yeşil (mum rengi kırmızıdan maviye); (d) '2-3 çizgisi kırılımı + iyi mum' = kapanış önceki kir_n barın en yükseğinin üstünde
    VE yeşil mum, gövde >= govde_oran x aralık (öznel 'iyi mum'un ölçülebilir karşılığı). Stop = geri çekilme dibi (3. nokta) - tampon_atr*ATR.
    Kitabın 3 lotu: 1R'de 1/3, 2R'de 1/3 (CikisAyarlari.kismi), son lot ATR iz süren stop (kitap 'bonus lot' hedefsiz, iz süren); ters dönüş
    işareti = kapanış EMA36 altı. Short aynası. ATLANDI: trend çizgisi dokunuşları (>=3), 4s stili, EMA200/633 geri çekilme %50-70 koşulu."""
    ad = "dis__ema-kesisim-123-kurulumu"
    stil = "swing"
    varsayilan_parametreler = {"ust_tf": "1w", "kes_pencere": 40, "geri_n": 8, "yakin_atr": 1.0, "kir_n": 3, "govde_oran": 0.5,
                               "tampon_atr": 0.25, "maks_risk_atr": 5.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"geri_n": [5, 8, 12], "yakin_atr": [0.5, 1.0, 2.0], "kir_n": [2, 3, 5]}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 1 / 3), (2.0, 1 / 3)), atr_iz_suren_k=3.0)

    def sinyaller(self, m):
        p = self.parametreler
        o, h, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(h, d, k, int(p["atr_periyot"]))
        e12, e36 = g.ema(k, 12), g.ema(k, 36)
        ha = heikin_ashi(o, h, d, k)
        yesil, kirmizi = ha["ha_kapanis"] > ha["ha_acilis"], ha["ha_kapanis"] < ha["ha_acilis"]
        kp, gn, kn = int(p["kes_pencere"]), int(p["geri_n"]), int(p["kir_n"])
        kes_u = yukari_kesis(e12, e36).rolling(kp, min_periods=1).max() > 0
        kes_d = asagi_kesis(e12, e36).rolling(kp, min_periods=1).max() > 0
        geri_dip = d.rolling(gn, min_periods=gn).min()
        geri_tep = h.rolling(gn, min_periods=gn).max()
        yakin_l = (geri_dip - e36) <= p["yakin_atr"] * a
        yakin_s = (e36 - geri_tep) <= p["yakin_atr"] * a
        aralik = (h - d).where(h != d)
        iyi_l = (k > o) & ((k - o) >= p["govde_oran"] * aralik) & (k > h.shift(1).rolling(kn, min_periods=kn).max())
        iyi_s = (k < o) & ((o - k) >= p["govde_oran"] * aralik) & (k < d.shift(1).rolling(kn, min_periods=kn).min())
        L = (e12 > e36) & kes_u & yakin_l & yesil & (kirmizi.rolling(gn, min_periods=1).max() > 0) & iyi_l
        S = (e12 < e36) & kes_d & yakin_s & kirmizi & (yesil.rolling(gn, min_periods=1).max() > 0) & iyi_s
        if p["ust_tf"]:
            ust = ust_zaman(m, p["ust_tf"], lambda u: pd.DataFrame(
                {"yon": np.sign(g.ema(u["kapanis"], 12) - g.ema(u["kapanis"], 36))}))["yon"]
            L, S = L & (ust > 0), S & (ust < 0)
        L, S = _ymask(p, gecis(L), gecis(S))
        t = p["tampon_atr"] * a
        sl = risk_siniri_l(geri_dip - t, k, a, p["maks_risk_atr"])
        ss = risk_siniri_s(geri_tep + t, k, a, p["maks_risk_atr"])
        return kur(m, L, S, sl, ss, None, None, k < e36, k > e36)
