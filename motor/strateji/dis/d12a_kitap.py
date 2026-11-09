"""D12-A — kodlama_kuyrugu_tam_okuma.csv (Brooks / Farley tam okuma aileleri) + ana kuyruktan Halsey ölçülü hareket. KOD KOPYALANMADI:
kitap kartları ve tam okuma raporları VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__`. Hepsi nedensel.

Ortak uyarlamalar
  * LİMİT EMİR YOKTUR: motor sinyali bar kapanışında üretir, sonraki açılışta doldurur. Kitaptaki "limit seviyede bekle" girişleri
    TUTUCU yaklaşıklanır: fiyat limit seviyesine KAPANIŞLA ulaştıktan/geçtikten sonra sonraki açılışta giriş (dokunuş = dolum
    varsayılmaz; dolum iyimser değildir, çoğu zaman limitten daha kötü fiyattadır). Bu yüzden R:R kitaptaki limitli girişten kötüdür.
  * Kitap sayıları E-mini tik/puan: ATR katına çevrildi (varsayımlar ilgili sınıf docstring'inde).
  * Short, `ayna(m)` ile (fiyat işareti çevrilmiş kopya) aynı long koduyla üretilir -> long/short simetrik.
  * Kitapta stop/hedef olmayanlara standart varsayım (ATR/R tabanlı) kondu; her sınıfta yazılı.
  * Yasak yapılar yok: kademeli alım/ölçekleme/ortalama düşürme kodlanmadı (Farley düşüşte kademeli alım kartları dahil).

dis__brooks-limit-fade, dis__brooks-limit-geri-cekilme, dis__brooks-olculu-hareket-limit, dis__brooks-dikenli-tel,
dis__brooks-trend-gunu-isaretleri, dis__farley-basarisizligin-basarisizligi, dis__farley-bosluk-turleri,
dis__brooks-doruk-tukenme, dis__halsey-olculu-hareket
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import kur
from motor.strateji.dis._gosterge_d12a import (
    ayna, dikenli_tel_barlari, dikenli_tel_boga, hedef_gecerli, ilk_olay, kirilim_olcu_durumu, mum_yapisi, stop_sinirla,
    trend_gucu_boga, trend_gunu_skoru)
from motor.strateji.pivotlar import zigzag_pivotlar
from motor.strateji.temel import Strateji


def _bos(index):
    return pd.Series(False, index=index)


def _b(x):
    return x.fillna(False).astype(bool)


def _sr(arr, index):
    return pd.Series(arr, index=index)


class _D12(Strateji):
    """Ortak iskelet: alt sınıf yalnız LONG mantığını `_boga(m, a)` ile yazar -> (koşul, stop, hedef|None, çıkış|None).
    Short aynı fonksiyonun `ayna(m)` üzerindeki çıktısıdır."""

    def cikis_var_mi(self):
        return True

    def _boga(self, m, a):  # pragma: no cover
        raise NotImplementedError

    def sinyaller(self, m):
        p = self.parametreler
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        kl, sl, hl, cl = self._boga(m, a)
        if p.get("short", True):
            ks, ss, hs, cs = self._boga(ayna(m), a)
            ss = -ss
            hs = None if hs is None else -hs
        else:
            ks, ss, hs, cs = _bos(m.index), pd.Series(np.nan, index=m.index), None, None
        k = m["kapanis"]
        hl = hedef_gecerli(k, hl)
        hs = None if hs is None else hs.where(hs < k)
        return kur(m, _b(kl), _b(ks), sl, ss, hl, hs, cl, cs)


def _hedef_sec(k, stop, orta, hedef_r, min_oran=0.5):
    """orta (yapısal hedef) varsa ve ödül >= min_oran x risk ise o, yoksa k + hedef_r x risk."""
    risk = k - stop
    r_hedef = k + hedef_r * risk
    if orta is None:
        return r_hedef
    gecerli = orta.notna() & ((orta - k) >= min_oran * risk)
    return orta.where(gecerli, r_hedef)


# =============================================================================== 1. limit fade
class BrooksLimitFade(_D12):
    """dis__brooks-limit-fade (daytrade, 5m) — Brooks: (a) aralık ucunda zayıf H1/H2-L1/L2 sinyal barını LİMİTLE fade, (b) güçlü
    trendde karşı (ayı) sinyal barının altında LİMİTLE trend yönünde al (başarısız L1/L2 tuzağı + trendde karşı scalp fade).
    Üç kart (aralik-ucunda-high1-low1-fade, guclu-trendde-karsi-scalp-fade, basarisiz-l1-l2-tuzagi-limit) iki moda indirgendi.
    LİMİT DOLUMU (TUTUCU yaklaşık, yukarıdaki ortak not): s = sinyal barı (t-1); limit seviyesi L = low[s] - tik_atr x ATR (long).
    Sinyal, t barı KAPANIŞI L'nin altına inerse (kapanış <= L) üretilir; giriş sonraki açılış. Dokunuşla dolum varsayılmaz.
      aralik  Aralık rejimi: EMA(ema_n) son n barda <= duz_atr x ATR oynamış VE kapanışın EMA'yı kesme sayısı >= min_kesisim.
              Long: sinyal barı s aralığın dibi bölgesinde (düşük <= LL_n + bolge x aralık yüksekliği) ve zayıf (doji: gövde/aralık
              <= doji_oran veya ayı barı). Short ayna (aralığın tepesi). Hedef: aralık ortası (hedef_modu='orta') yoksa hedef_r x R.
      trend   Güçlü boğa trendi (trend_gucu_boga, t-1'e kadar) + s barı ayı barı + kapanış EMA üstünde kalıyor. Hedef: önceki n bar
              zirvesi (ödül >= 0.5R ise) yoksa hedef_r x R.
    Stop (her ikisi): min(low[t], low[s]) - stop_tampon_atr x ATR, en çok maks_risk_atr x ATR uzakta. Zaman çıkışı 48 bar.
    VARSAYIMLAR (kitapta sayı E-mini'ye özgü): tik_atr=0.1, bolge=0.25, doji_oran=0.35, duz_atr=2, trend eşikleri trend_gucu_boga
    docstring'inde; kitaptaki '%60 olasılık' iddiası kanıtsız, kullanılmadı."""
    ad = "dis__brooks-limit-fade"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "aralik", "ema_n": 20, "n": 24, "duz_atr": 2.0, "min_kesisim": 3, "bolge": 0.25, "doji_oran": 0.35,
        "tik_atr": 0.1, "stop_tampon_atr": 0.25, "maks_risk_atr": 3.0, "hedef_modu": "orta", "hedef_r": 1.5,
        "trend_oran": 0.8, "egim_atr": 0.5, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["aralik", "trend"], "tik_atr": [0.0, 0.1, 0.25], "hedef_r": [1.0, 1.5, 2.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=48)

    def _boga(self, m, a):
        p = self.parametreler
        o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        e = g.ema(k, int(p["ema_n"]))
        n = int(p["n"])
        yp = mum_yapisi(m)
        seviye = l.shift(1) - p["tik_atr"] * a.shift(1)
        tetik = k <= seviye
        hh, ll = h.rolling(n, min_periods=n).max().shift(1), l.rolling(n, min_periods=n).min().shift(1)
        if p["mod"] == "aralik":
            duz = (e - e.shift(n)).abs() <= p["duz_atr"] * a
            yon = np.sign(k - e)
            kes = (yon != yon.shift(1)).astype(float).rolling(n, min_periods=n).sum() >= p["min_kesisim"]
            rejim = (duz & kes).shift(1)
            dipte = l.shift(1) <= ll + p["bolge"] * (hh - ll)
            zayif = ((yp["govde_oran"] <= p["doji_oran"]) | yp["ayi"]).shift(1)
            kos = _b(rejim) & _b(dipte) & _b(zayif) & tetik
            orta = ((hh + ll) / 2.0) if p["hedef_modu"] == "orta" else None
        elif p["mod"] == "trend":
            tr = trend_gucu_boga(m, a, int(p["ema_n"]), n, p["trend_oran"], p["egim_atr"]).shift(1, fill_value=False)
            kos = _b(tr) & _b(yp["ayi"].shift(1)) & tetik & (k > e)
            orta = hh
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        stop = stop_sinirla(np.minimum(l, l.shift(1)) - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        return kos, stop, _hedef_sec(k, stop, orta, p["hedef_r"]), None


# =============================================================================== 2. limit geri çekilme
class BrooksLimitGeriCekilme(_D12):
    """dis__brooks-limit-geri-cekilme (daytrade, 5m) — Brooks trend yönünde geri çekilmeyi LİMİTLE alma (stop girişi beklemeden).
    Kartlar: onceki-cubuk-ucunda-limit-geri-cekilme, trend-geri-cekilme-limit-emir, mikro-trend-cizgisi-basarisiz-kirilim +
    LİDER KARARI: Farley 'desteğe tek limit giriş' (mod 'destek'; kademeli/ortalama düşürme YOK, tek giriş). Limit dolumu TUTUCU
    yaklaşık (kapanışla ulaşma, ortak not). Bağlam: t-1'e kadar güçlü boğa trendi (trend_gucu_boga) — 'destek' modu hariç.
      onceki_cubuk  kapanış[t] <= low[t-1] - tik_atr x ATR VE kapanış > EMA (önceki barın dibinde/altında geri çekilme).
      ma            son ma_dok_n barda dip EMA'ya değmemiş; kapanış[t] <= EMA + tik_atr x ATR ve >= EMA - 1 ATR (MA'ya geri çekilme).
      derinlik      geri çekilme derinliği pb = HH(pb_n) - kapanış, son `gecmis` bardaki en büyük pb'nin derinlik_k katına ilk
                    kez ulaşır (ilk geçiş) ve <= pb_maks_atr x ATR (kitap: ort. günlük aralığın %50-75'ini aşan geri çekilme = trend sorgulanır).
      mikro         mikro kanal: önceki mikro_n barın >= mikro_oran'ı boğa ve ortalama gövde/aralık >= mikro_govde; t barı önceki
                    barın dibini kırar (low[t] < low[t-1]) fakat aralığın üst yarısında kapanır ve EMA üstünde -> kırılım başarısız (H1).
      destek        trend: SMA(trend_n) yükseliyor, kapanış üstünde. Destek = low'un sup_n barlık minimumu (sup_gec bar önce biten
                    pencere; yeni dip değil, oturmuş destek). t barının dibi destek bölgesine (+-sup_tol x ATR) girdi, boğa barı kapandı.
    Stop: min(low[t], low[t-1] | destek) - stop_tampon_atr x ATR, en çok maks_risk_atr x ATR. Hedef: hedef_r x R (VARSAYIM 2R;
    kitap 'yeni zirve testi / ölçülü hareket' der, sayısal değil). VARSAYIM: tik_atr=0.1; kitaptaki E-mini tikleri ATR'ye çevrildi."""
    ad = "dis__brooks-limit-geri-cekilme"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "onceki_cubuk", "ema_n": 20, "n": 20, "trend_oran": 0.8, "egim_atr": 0.5, "tik_atr": 0.1, "ma_dok_n": 20,
        "pb_n": 10, "gecmis": 60, "derinlik_k": 0.7, "pb_maks_atr": 4.0, "mikro_n": 6, "mikro_oran": 0.8, "mikro_govde": 0.55,
        "sup_n": 20, "sup_gec": 5, "sup_tol": 0.5, "trend_n": 50, "stop_tampon_atr": 0.25, "maks_risk_atr": 3.0,
        "hedef_r": 2.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["onceki_cubuk", "ma", "derinlik", "mikro", "destek"], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=60)

    def _boga(self, m, a):
        p = self.parametreler
        o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        e = g.ema(k, int(p["ema_n"]))
        tik = p["tik_atr"] * a
        stop_dip = np.minimum(l, l.shift(1))
        mod = p["mod"]
        if mod != "destek":
            tr = trend_gucu_boga(m, a, int(p["ema_n"]), int(p["n"]), p["trend_oran"], p["egim_atr"]).shift(1, fill_value=False)
        if mod == "onceki_cubuk":
            kos = _b(tr) & (k <= l.shift(1) - tik) & (k > e)
        elif mod == "ma":
            dokunmadi = (l > e).astype(float).rolling(int(p["ma_dok_n"]), min_periods=int(p["ma_dok_n"])).min().shift(1) >= 1.0
            kos = _b(tr) & _b(dokunmadi) & (k <= e + tik) & (k >= e - a)
        elif mod == "derinlik":
            pb = h.rolling(int(p["pb_n"]), min_periods=int(p["pb_n"])).max() - k
            mx = pb.shift(1).rolling(int(p["gecmis"]), min_periods=int(p["gecmis"])).max()
            esik = p["derinlik_k"] * mx
            ham = _b(tr) & (mx > 0.5 * a) & (pb >= esik) & (pb <= p["pb_maks_atr"] * a) & (k > e)
            kos = ilk_olay(ham)
        elif mod == "mikro":
            yp = mum_yapisi(m)
            mn = int(p["mikro_n"])
            mk = ((yp["boga"].astype(float).rolling(mn, min_periods=mn).mean() >= p["mikro_oran"]) &
                  (yp["govde_oran"].rolling(mn, min_periods=mn).mean() >= p["mikro_govde"])).shift(1)
            kos = _b(mk) & (l < l.shift(1)) & (k > (h + l) / 2.0) & (k > e)
        elif mod == "destek":
            sm = g.sma(k, int(p["trend_n"]))
            yuk = (sm > sm.shift(5)) & (k > sm)
            sn = int(p["sup_n"])
            dest = l.shift(int(p["sup_gec"])).rolling(sn, min_periods=sn).min()
            tol = p["sup_tol"] * a
            kos = _b(yuk) & (l >= dest - tol) & (l <= dest + tol) & (k > o)
            stop_dip = np.minimum(l, dest)
        else:
            raise ValueError(f"Bilinmeyen mod: {mod!r}")
        stop = stop_sinirla(stop_dip - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        return kos, stop, _hedef_sec(k, stop, None, p["hedef_r"]), None


# =============================================================================== 3. ölçülü hareket limit
class BrooksOlculuHareketLimit(_D12):
    """dis__brooks-olculu-hareket-limit (daytrade, 5m) — Brooks: aralığın ZAYIF kırılımında aralık yüksekliği kadar ölçülü hareket
    seviyesinde LİMİTLE ters yönde giriş (hedef kırılım noktasının testi); trend eden aralık gününde büyük trend barını ölçülü
    hareket bölgesinde fade. Kartlar: kirilim-testi-limit-fade, trend-araligi-olculu-hareket-bari-fade. ATLANDI: merdiven-kirilim-testi
    kartı (3 salınımlı merdiven + 'son kırılım uzunluğu kadar' ölçüm; ölçülebilir ama ayrı kural kümesi; kuyruk özeti dışı bırakıldı).
    LİMİT DOLUMU TUTUCU: kapanış, seviyeye (dip - olcu x H) ulaşınca/geçince sonraki açılışta giriş (dokunuş yetmez).
    Aralık: son n barın (zirve-dip) yüksekliği H, min_atr x ATR <= H <= rng_atr x ATR. Kırılım: kapanış aralık dibinin altı.
    Referans aralık dondurulur; bekle bar içinde kapanış aralığa dönerse iptal.
      aralik    zayıf kırılım: kırılımdan beri güçlü ayı barı (gövde >= %60, aralık >= 1 ATR) sayısı < guclu_maks (kitap: 'çok güçlü
                kırılışta yapılmaz'; zayıf/güçlü ölçütü kitapta yok -> bu varsayım) VE seviyeyi geçen bar 'büyük trend barı' değil.
      bar_fade  seviyeye ulaşan bar büyük ayı trend barı (gövde >= %60, aralık >= buyuk_atr x ATR, kapanış alt %25) — kart 2.
    Stop = kapanış - stop_oran x H (kitap: risk ~ aralık yüksekliği), hedef = aralık dibi (kırılım noktası testi); ödül/risk
    olcu/stop_oran. VARSAYIM: olcu=1, stop_oran=1 (kitap: 'risk ≈ ödül ≈ aralık yüksekliği'), maks risk 4 ATR."""
    ad = "dis__brooks-olculu-hareket-limit"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "aralik", "n": 12, "rng_atr": 5.0, "min_atr": 1.0, "bekle": 24, "olcu": 1.0, "stop_oran": 1.0, "guclu_maks": 2,
        "buyuk_atr": 1.5, "maks_risk_atr": 4.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["aralik", "bar_fade"], "n": [8, 12, 20], "olcu": [0.75, 1.0, 1.25]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=60)

    def _boga(self, m, a):
        p = self.parametreler
        o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        yp = mum_yapisi(m)
        guclu_ayi = _b(yp["ayi"] & (yp["govde_oran"] >= 0.6) & (yp["aralik"] >= a))
        buyuk = _b(yp["ayi"] & (yp["govde_oran"] >= 0.6) & (yp["aralik"] >= p["buyuk_atr"] * a) & (yp["konum"] <= 0.25))
        sig, ll, hh, ns = kirilim_olcu_durumu(h.to_numpy(), l.to_numpy(), k.to_numpy(), guclu_ayi.to_numpy(), a.to_numpy(),
                                              int(p["n"]), p["rng_atr"], p["min_atr"], int(p["bekle"]), p["olcu"])
        sig, ll, hh, ns = _sr(sig, m.index), _sr(ll, m.index), _sr(hh, m.index), _sr(ns, m.index)
        if p["mod"] == "aralik":
            kos = sig & (ns < int(p["guclu_maks"])) & ~buyuk
        elif p["mod"] == "bar_fade":
            kos = sig & buyuk
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        stop = stop_sinirla(k - p["stop_oran"] * hh, k, a, p["maks_risk_atr"])
        return kos, stop, ll, None


# =============================================================================== 4. dikenli tel
class BrooksDikenliTel(_D12):
    """dis__brooks-dikenli-tel (daytrade, 5m) — Brooks 'dikenli tel' (üst üste binen, dojili barlar): bölgeden çıkan trend barı
    kovalanmaz, çıkış barının karşı ucu geri alınırsa ters yöne girilir (başarısız kırılım). Kart: dikenli-tel-basarisiz-kirilim.
    Tanım (kitap ölçütü): 3 ardışık barın ortasındakinin aralığının > %50'si her iki komşunun aralığı içinde VE 3 barın en az biri
    doji (gövde/aralık < doji_oran=0.25). Bölge = ardışık tel barlarının birleşimi.
    Long: bölge bitince İLK bar güçlü ayı trend barıdır (gövde >= %60, aralık >= ATR) ve kapanış bölge dibinin altında (aşağı çıkış);
    sonraki <= bekle barda kapanış çıkış barının ZİRVESİNİ aşarsa sinyal (kitap: zirvenin 1 tik üstüne ters stop -> kapanışa
    yaklaşıklandı, TUTUCU). Çıkıştan sonra kapanışı çıkış kapanışının altında ikinci güçlü ayı barı gelirse iptal (ardışık iki
    trend barı çıkışı fade edilmez). ma_filtre: bölge kapanışlarının >= ma_oran'ı EMA üstündeyse yalnız long (kitap: tel
    ortalamanın üstündeyse yukarı kırar). Short ayna.
    Stop: çıkış barından bu yana en düşük dip - stop_tampon_atr x ATR (en çok maks_risk_atr). Hedef: giriş + olcu x bölge yüksekliği
    (VARSAYIM; kitapta hedef yok, 'kısa scalp'). Atlandı: kenar fade (bölge kenarında küçük dönüş barı), ioi, ters-çevirme zinciri.
    Kitap bunu 'çok deneyimli' işi sayar; backtest'te beklenti negatif çıkabilir."""
    ad = "dis__brooks-dikenli-tel"
    stil = "daytrade"
    varsayilan_parametreler = {
        "doji_oran": 0.25, "ort_oran": 0.5, "bekle": 5, "ma_oran": 0.7, "ma_filtre": True, "ema_n": 20, "olcu": 1.0,
        "stop_tampon_atr": 0.25, "maks_risk_atr": 4.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"bekle": [3, 5, 8], "olcu": [0.75, 1.0, 1.5], "ma_filtre": [True, False]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=48)

    def _boga(self, m, a):
        p = self.parametreler
        h, l, k = m["yuksek"], m["dusuk"], m["kapanis"]
        yp = mum_yapisi(m)
        e = g.ema(k, int(p["ema_n"]))
        tel = dikenli_tel_barlari(m, p["doji_oran"], p["ort_oran"])
        guclu_ayi = _b(yp["ayi"] & (yp["govde_oran"] >= 0.6) & (yp["aralik"] >= a))
        guclu_boga = _b(yp["boga"] & (yp["govde_oran"] >= 0.6) & (yp["aralik"] >= a))
        sig, stop, hedef = dikenli_tel_boga(h.to_numpy(), l.to_numpy(), k.to_numpy(), e.to_numpy(), a.to_numpy(), tel.to_numpy(),
                                            guclu_ayi.to_numpy(), guclu_boga.to_numpy(), int(p["bekle"]), p["ma_oran"], bool(p["ma_filtre"]),
                                            p["olcu"], p["stop_tampon_atr"])
        stop = stop_sinirla(_sr(stop, m.index), k, a, p["maks_risk_atr"])
        return _sr(sig, m.index), stop, _sr(hedef, m.index), None


# =============================================================================== 5. trend günü işaretleri
class BrooksTrendGunuIsaretleri(_D12):
    """dis__brooks-trend-gunu-isaretleri (daytrade, 5m) — Brooks 'güç işaretleri' = trend günü FİLTRESİ + basit giriş (ilk geri çekilmede
    trend yönünde). Filtre: `trend_gunu_skoru` (gösterge dosyası; 6 madde: trend barı oranı, düşük örtüşme, küçük kuyruk, EMA'ya
    dokunmama, EMA'nın karşısında ardışık 2 kapanış yok, küçük geri çekilme). skor >= min_skor ve kapanış > EMA ise 'boğa trend modu'.
    Kayan pencere (n bar); gün sınırı kullanılmaz. Gap/açılış-aralığı maddeleri atlandı (seans tanımı gerektirir).
    Giriş (long): t-1 geri çekilme barı (ayı), t barı boğa ve kapanış > high[t-1] (devam); t-1'de trend modu açık. `ilk_pencere`
    barda en çok bir giriş (kitap: 'ilk geri çekilme'). Stop: min(low[t], low[t-1]) - stop_tampon_atr x ATR (küçük stop; kitap
    Emini 2 puan) en çok maks_risk_atr. Çıkış: EMA altında ardışık 2 kapanış veya skor < cik_skor + 3 ATR iz süren stop (kitap
    'swing parçası tut'; hedef yok). Short ayna. Not: tek başına filtre olarak da kullanılabilir (`trend_gunu_skoru`)."""
    ad = "dis__brooks-trend-gunu-isaretleri"
    stil = "daytrade"
    varsayilan_parametreler = {
        "n": 24, "ema_n": 20, "ma_dok_n": 20, "pb_atr": 3.0, "min_skor": 4, "cik_skor": 2, "ilk_pencere": 24,
        "stop_tampon_atr": 0.25, "maks_risk_atr": 3.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"n": [18, 24, 36], "min_skor": [3, 4, 5], "ilk_pencere": [12, 24, 48]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def _boga(self, m, a):
        p = self.parametreler
        o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        e = g.ema(k, int(p["ema_n"]))
        sk = trend_gunu_skoru(m, a, int(p["n"]), int(p["ema_n"]), int(p["ma_dok_n"]), p["pb_atr"])["skor"]
        mod = (sk >= p["min_skor"]) & (k > e)
        ham = mod.shift(1, fill_value=False) & (k.shift(1) < o.shift(1)) & (k > o) & (k > h.shift(1))
        pencere = int(p["ilk_pencere"])
        onceki = ham.shift(1, fill_value=False).astype(float).rolling(pencere, min_periods=1).max() > 0
        kos = ham & ~onceki
        stop = stop_sinirla(np.minimum(l, l.shift(1)) - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        cikis = ((k < e) & (k.shift(1) < e.shift(1))) | (sk < p["cik_skor"])
        return kos, stop, None, _b(cikis)


# =============================================================================== 6. başarısızlığın başarısızlığı
class FarleyBasarisizliginBasarisizligi(_D12):
    """dis__farley-basarisizligin-basarisizligi (swing, 1h) — Farley: destek/direnç kırılımı BAŞARISIZ olup fiyat seviyeye geri
    dönerse ikinci sinyal birincisinden güvenilirdir. Kart: basarisizligin-basarisizligi-ikinci-sinyal.
    Long (short ayna): S = son sup_n barın en düşük dibi (kırılımdan önce, shift 1). Kırılım: kapanış < S - dmin x ATR.
    <= kirbac_max bar içinde kapanış S'in ÜSTÜNE dönerse kırılım başarısız.
      ilk            giriş bu geri dönüş barında (kapanışta sinyal, sonraki açılışta dolum).
      geri_cekilme   ikinci sinyal: geri dönüşten sonra <= bekle barda dip EMA(ema_n)'e (+-ema_tol x ATR) inip boğa barı kapanır
                     ve kapanış > S (kitap: 50 EMA'dan dönüş güvenilir); kapanış S altına inerse kurulum iptal.
    Stop: kırılımdan bu yana en düşük dip - stop_tampon_atr x ATR (kitapta stop yok; öneri 'tuzak ucu' -> VARSAYIM), en çok
    maks_risk_atr. Hedef: hedef_r x R (VARSAYIM 2R). Opsiyon vadesi/ay sonu ve RSI aşırı satım süzgeçleri uygulanmadı.
    '%62 tolerans' kitapta kesin değil -> kullanılmadı."""
    ad = "dis__farley-basarisizligin-basarisizligi"
    stil = "swing"
    varsayilan_parametreler = {
        "mod": "ilk", "sup_n": 40, "dmin_atr": 0.2, "kirbac_max": 8, "ema_n": 50, "ema_tol": 0.5, "bekle": 15,
        "stop_tampon_atr": 0.1, "maks_risk_atr": 5.0, "hedef_r": 2.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["ilk", "geri_cekilme"], "sup_n": [20, 40, 80], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=100)

    def _boga(self, m, a):
        p = self.parametreler
        if p["mod"] not in ("ilk", "geri_cekilme"):
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        o, h, l, k = (m[c].to_numpy() for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        sn = int(p["sup_n"])
        S_ = m["dusuk"].rolling(sn, min_periods=sn).min().shift(1).to_numpy()
        e = g.ema(m["kapanis"], int(p["ema_n"])).to_numpy()
        av = a.to_numpy()
        n = len(k)
        sig = np.zeros(n, dtype=bool)
        stop = np.full(n, np.nan)
        durum = 0
        seviye = lowest = 0.0
        bas = 0
        ilk_mod = p["mod"] == "ilk"
        for i in range(n):
            if durum == 1:
                lowest = min(lowest, l[i])
                if k[i] > seviye:
                    if ilk_mod:
                        sig[i], stop[i] = True, lowest - p["stop_tampon_atr"] * av[i]
                        durum = 0
                    else:
                        durum, bas = 2, i
                elif i - bas > p["kirbac_max"]:
                    durum = 0
            elif durum == 2:
                lowest = min(lowest, l[i])
                if k[i] < seviye or i - bas > p["bekle"]:
                    durum = 0
                elif l[i] <= e[i] + p["ema_tol"] * av[i] and k[i] > o[i]:
                    sig[i], stop[i] = True, lowest - p["stop_tampon_atr"] * av[i]
                    durum = 0
            if durum == 0 and not sig[i] and not np.isnan(S_[i]) and not np.isnan(av[i]) and k[i] < S_[i] - p["dmin_atr"] * av[i]:
                durum, seviye, lowest, bas = 1, S_[i], l[i], i
        k_s = m["kapanis"]
        stop_s = stop_sinirla(_sr(stop, m.index), k_s, a, p["maks_risk_atr"])
        return _sr(sig, m.index), stop_s, k_s + p["hedef_r"] * (k_s - stop_s), None


# =============================================================================== 7. boşluk türleri
class FarleyBoslukTurleri(_D12):
    """dis__farley-bosluk-turleri (swing, 1d) — Farley'nin üç boşluk türü (fiyat boşluğu: low[t] > high[t-1] + gap_atr x ATR; aşağı
    boşluk ayna). Kartlar: devam-boslugu-geri-cekilme-fib38, devam-boslugu-geri-test, kopus-boslugu-bayrak-geri-cekilme,
    tukenme-boslugu-tersleme. Dolum: giriş sonraki açılışta (limit yok); 'boşluğa limit' kartı onaylı geri dönüşle yaklaşıklandı.
      devam     Yükselen trendde (SMA(trend_n) yükseliyor, kapanış üstünde; boşluktan önceki bar) yukarı boşluk. <= bekle bar içinde
                dip boşluk üstüne (kapanış-boşluk üstü + tol) iner, boşluk DOLMADAN (kapanış >= boşluk altı) boğa barı kapanıp bir
                önceki kapanışı aşar -> long. Kapanış boşluk altına inerse kurulum geçersiz (kitap). Stop: boşluk altı - tampon x ATR.
                ATLANDI: 3 trend dalgası sayımı, %50 konum, %38 geri alma (hedef yerine sabit R kullanıldı).
      kopus     Dar taban (son base_n bar yüksekliği <= base_atr x ATR) kırılıp boşlukla çıkış (boğa bar, kapanış taban zirvesi üstü).
                Sonra bayrak: geri çekilme (taban dibinden boşluk zirvesine uzanan dalganın) <= %50'sini aşmaz, bir önceki bar düşük kapanışlı,
                bugün kapanış son bayrak_n barın zirvesini aşar (bayrak kırılımı, boğa barı) -> long. Hacim süzgeci (düşük hacimli
                karşı hareket) kitapta eşik yok -> uygulanmadı. Stop: bayrak dibi - tampon x ATR.
      tukenme   Uzun düşüşten (son run_n barda >= run_atr x ATR) sonra AŞAĞI boşluk (tükenme boşluğu); boşluğun üst kenarı (önceki
                bar dibi) <= bekle bar içinde KAPANIŞLA geri alınınca long (kitap: boşluk dolunca trend sonu; giriş zamanlaması kitapta
                belirsiz -> doldurma sonrası, tutucu). Stop: boşluktan beri en düşük dip - tampon x ATR. Short ayna (yukarı tükenme).
    Hedef hedef_r x R (VARSAYIM 2R; kitapta stop/hedef yok). Not: 24/7 kripto'da boşluk az; hisse/ETF/TradFi'de anlamlı."""
    ad = "dis__farley-bosluk-turleri"
    stil = "swing"
    varsayilan_parametreler = {
        "mod": "devam", "gap_atr": 0.3, "trend_n": 50, "bekle": 15, "tol_atr": 0.5, "base_n": 15, "base_atr": 6.0, "bayrak_n": 3,
        "run_n": 20, "run_atr": 6.0, "stop_tampon_atr": 0.25, "maks_risk_atr": 5.0, "hedef_r": 2.0, "atr_periyot": 14,
        "short": True}
    parametre_izgarasi = {"mod": ["devam", "kopus", "tukenme"], "gap_atr": [0.25, 0.5, 1.0], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=60)

    def _boga(self, m, a):
        p = self.parametreler
        mod = p["mod"]
        if mod not in ("devam", "kopus", "tukenme"):
            raise ValueError(f"Bilinmeyen mod: {mod!r}")
        o, h, l, k = (m[c].to_numpy() for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        av = a.to_numpy()
        n = len(k)
        sn = int(p["trend_n"])
        sm = g.sma(m["kapanis"], sn).to_numpy()
        hhb = m["yuksek"].rolling(int(p["base_n"]), min_periods=int(p["base_n"])).max().shift(1).to_numpy()
        llb = m["dusuk"].rolling(int(p["base_n"]), min_periods=int(p["base_n"])).min().shift(1).to_numpy()
        rn = int(p["run_n"])
        bekle, tol, tamp = int(p["bekle"]), p["tol_atr"], p["stop_tampon_atr"]
        sig = np.zeros(n, dtype=bool)
        stop = np.full(n, np.nan)
        armed = False
        gi = 0
        gap_alt = top = peak = base_lo = minl = fill = 0.0
        for i in range(max(sn + 6, rn + 2, 3), n):
            if np.isnan(av[i - 1]) or np.isnan(sm[i - 1]):
                continue
            esik = p["gap_atr"] * av[i - 1]
            if armed:
                if mod == "devam":
                    if i - gi > bekle or k[i] < gap_alt:
                        armed = False
                    elif l[i] > gap_alt and k[i] <= top + tol * av[i] and k[i] > o[i] and k[i] > k[i - 1]:
                        sig[i], stop[i], armed = True, gap_alt - tamp * av[i], False
                elif mod == "kopus":
                    peak = max(peak, h[i])
                    minl = min(minl, l[i])
                    retr = (peak - minl) / (peak - base_lo) if peak > base_lo else 1.0
                    if retr > 0.5 or i - gi > bekle or k[i] < gap_alt:
                        armed = False
                    else:
                        bn = int(p["bayrak_n"])
                        if i - gi >= 2 and k[i - 1] < k[i - 2] and k[i] > h[i - bn:i].max() and k[i] > o[i]:
                            sig[i], stop[i], armed = True, l[i - bn:i + 1].min() - tamp * av[i], False
                else:   # tukenme
                    minl = min(minl, l[i])
                    if i - gi > bekle:
                        armed = False
                    elif k[i] > fill:
                        sig[i], stop[i], armed = True, minl - tamp * av[i], False
            if sig[i]:
                continue
            if mod == "devam":
                if l[i] > h[i - 1] + esik and k[i - 1] > sm[i - 1] and sm[i - 1] > sm[i - 6]:
                    armed, gi, gap_alt, top = True, i, h[i - 1], l[i]
            elif mod == "kopus":
                if not np.isnan(hhb[i]) and not np.isnan(llb[i]) and (hhb[i] - llb[i]) <= p["base_atr"] * av[i - 1] \
                        and l[i] > h[i - 1] + esik and k[i] > hhb[i] and k[i] > o[i]:
                    armed, gi, gap_alt, base_lo, peak, minl = True, i, h[i - 1], llb[i], h[i], np.inf
            else:
                if h[i] < l[i - 1] - esik and (k[i - 1 - rn] - k[i - 1]) >= p["run_atr"] * av[i - 1]:
                    armed, gi, fill, minl = True, i, l[i - 1], l[i]
        k_s = m["kapanis"]
        stop_s = stop_sinirla(_sr(stop, m.index), k_s, a, p["maks_risk_atr"])
        return _sr(sig, m.index), stop_s, k_s + p["hedef_r"] * (k_s - stop_s), None


# =============================================================================== 8. doruk / tükenme
class BrooksDorukTukenme(_D12):
    """dis__brooks-doruk-tukenme (daytrade, 5m) — Brooks climax (doruk): uzun trendin sonunda olağandışı büyük trend barı = tükenme;
    karşı yönde düzeltme. Kartlar: klimaks-cubugu-kapanis-fade, climax-tukenme-sonrasi-duzeltme, ardisik-doruk-iki-bacakli-duzeltme.
    Long (short ayna). Climax barı C: ayı barı, gövde >= %60, aralık >= buyuk_k x ATR(t-1) ('olağandışı büyük' = ATR katı; kitapta
    eşik yok -> VARSAYIM 2), kapanış aralığın alt %25'inde, öncesinde ayı trendi (son trend_n kapanışın >= %70'i EMA altında),
    dip son destek_n barın en düşüğünü yeniledi (destek/ekstrem bölgesi). Hacim şartı (kitap) hacim_k>0 ise: hacim >= hacim_k x SMA(20).
      kapanis   C barının kapanışında long (kitap kart 1). Stop = kapanış - bar boyu (kitap: risk ≈ bar boyu), hedef = C barının zirvesi.
      donus     C'den sonra <= bekle barda boğa dönüş barı (boğa, kapanış > önceki barın zirvesi) -> long (kitap kart 2: ters çubuk).
                Stop: C'den beri en düşük dip - tampon; hedef EMA (ödül >= 0.5R ise) yoksa hedef_r x R.
      ardisik   donus ile aynı, ancak son 10 barda en az ard_say (2) climax barı olmuşsa (kitap: art arda ikinci/üçüncü doruk).
    Zaman çıkışı 40 bar. Kitap 'çok deneyimli' diyor; stop geniş, kazanma oranı iddiası kanıtsız."""
    ad = "dis__brooks-doruk-tukenme"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "kapanis", "buyuk_k": 2.0, "ema_n": 20, "trend_n": 20, "trend_oran": 0.7, "destek_n": 30, "hacim_k": 0.0,
        "bekle": 6, "ard_say": 2, "ard_pencere": 10, "stop_tampon_atr": 0.25, "maks_risk_atr": 6.0, "hedef_r": 2.0,
        "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["kapanis", "donus", "ardisik"], "buyuk_k": [1.5, 2.0, 2.5], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=40)

    def _boga(self, m, a):
        p = self.parametreler
        o, h, l, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        e = g.ema(k, int(p["ema_n"]))
        yp = mum_yapisi(m)
        tn = int(p["trend_n"])
        ayi_trend = (k < e).astype(float).rolling(tn, min_periods=tn).mean().shift(1) >= p["trend_oran"]
        dn = int(p["destek_n"])
        ekstrem = l <= l.shift(1).rolling(dn, min_periods=dn).min()
        C = (_b(yp["ayi"]) & (yp["govde_oran"] >= 0.6) & (yp["aralik"] >= p["buyuk_k"] * a.shift(1)) & (yp["konum"] <= 0.25)
             & _b(ayi_trend) & ekstrem)
        if p["hacim_k"] and "hacim" in m:
            C = C & (m["hacim"] >= p["hacim_k"] * g.sma(m["hacim"], 20))
        C = _b(C)
        mod = p["mod"]
        if mod == "kapanis":
            stop = stop_sinirla(k - yp["aralik"], k, a, p["maks_risk_atr"])
            return C, stop, h, None
        b = int(p["bekle"])
        Csonra = C.shift(1, fill_value=False).astype(float).rolling(b, min_periods=1).max() > 0
        donus = _b(yp["boga"]) & (k > h.shift(1)) & Csonra & ~C
        if mod == "ardisik":
            say = C.shift(1, fill_value=False).astype(float).rolling(int(p["ard_pencere"]), min_periods=1).sum()
            donus = donus & (say >= p["ard_say"])
        elif mod != "donus":
            raise ValueError(f"Bilinmeyen mod: {mod!r}")
        stop = stop_sinirla(l.rolling(b + 1, min_periods=1).min() - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        return ilk_olay(donus), stop, _hedef_sec(k, stop, e, p["hedef_r"]), None


# =============================================================================== 9. Halsey ölçülü hareket
class HalseyOlculuHareket(_D12):
    """dis__halsey-olculu-hareket (daytrade, 15m) — Halsey 'geleneksel %50 ölçülü hareket' (MM) + 'uzatma'. Kitaptaki çapa GÖRSEL;
    ölçülebilir çapa tanımı: nedensel ATR-zigzag (esik_k x ATR dönüş = pivot onayı, gecikmeli) ile son onaylı dip P1 ve ondan sonraki
    onaylı tepe P2; bacak = P2 - P1 (>= esik_k ATR garanti). Seviyeler (boğa): %50 = P2 - 0.5 bacak, %61.8 = P2 - 0.618 bacak,
    hedef = P1 + 1.23 bacak (%123, kart). Giriş (long): P2'den sonra (yeni dip onaylanmadan) kapanış %50 seviyesinin ALTINA/üzerine
    inince (TUTUCU: kapanışla ulaşma; kart 'limit al') ve %61.8 hiç kapanışla kırılmadıysa (kart 2: %61.8 kırılırsa seri biter) —
    her bacakta yalnız ilk dokunuş. Stop = %61.8 - stop_tampon_atr x ATR (VARSAYIM; kartta stop yalnız 'ES 6 tik'), hedef %123.
      temel    her onaylı bacak.
      uzatma   kart 1: bacak önceki yukarı bacağın >= 1.23 katı VE P2 önceki tepenin üstünde (%123 hedefi geçilip yeni zirve).
    Kart 2'nin 'karşıt MM kırılınca ilk geri çekilmede trend dönüşü girişi' ayrı mod olarak KODLANMADI (karşıt MM çapası ek belirsizlik;
    simetri gereği zaten karşıt bacak ayna tarafta işlem üretir). 'İlk uzatma yalnız gözlem' kuralı kitapta kesin değil, uygulanmadı.
    Zaman çıkışı 96 bar."""
    ad = "dis__halsey-olculu-hareket"
    stil = "daytrade"
    varsayilan_parametreler = {
        "mod": "temel", "esik_k": 3.0, "zig_atr": 14, "giris_oran": 0.5, "ret_oran": 0.618, "hedef_oran": 1.23,
        "stop_tampon_atr": 0.5, "maks_risk_atr": 4.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"mod": ["temel", "uzatma"], "esik_k": [2.0, 3.0, 4.0], "stop_tampon_atr": [0.25, 0.5, 1.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=96)

    def _boga(self, m, a):
        p = self.parametreler
        if p["mod"] not in ("temel", "uzatma"):
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        h, l, k = m["yuksek"], m["dusuk"], m["kapanis"]
        t = zigzag_pivotlar(h, l, k, int(p["zig_atr"]), float(p["esik_k"]))
        # son onaylı pivot TEPE ise: P2 = son tepe, P1 = ondan önce onaylanmış dip
        tepe_son = t["son_tepe_onay_idx"] > t["son_dip_onay_idx"].fillna(-1)
        p2 = t["son_tepe_fiyat"].where(tepe_son)
        p1 = t["son_dip_fiyat"].where(tepe_son)
        bacak = p2 - p1
        leg_id = t["son_tepe_idx"].where(tepe_son)
        if p["mod"] == "uzatma":
            onc = t["onceki_tepe_fiyat"] - t["onceki_dip_fiyat"].where(t["onceki_dip_idx"] < t["onceki_tepe_idx"])
            ok = (bacak >= p["hedef_oran"] * onc) & (p2 > t["onceki_tepe_fiyat"])
            p2 = p2.where(ok)
        seviye = p2 - p["giris_oran"] * bacak
        ret = p2 - p["ret_oran"] * bacak
        kirik = (k <= ret).groupby(leg_id).cummax()
        ham = (k <= seviye) & (k > ret) & ~kirik.fillna(False).astype(bool) & (bacak > 0)
        ham = _b(ham)
        sira = ham.astype(int).groupby(leg_id).cumsum()
        kos = ham & (sira == 1)
        stop = stop_sinirla(ret - p["stop_tampon_atr"] * a, k, a, p["maks_risk_atr"])
        hedef = p1 + p["hedef_oran"] * bacak
        return kos, stop, hedef, None
