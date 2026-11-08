"""D10-d — kodlama kuyruğundaki (kodlama_kuyrugu_2026-11-07.csv) yeni_aile satırları, harf d. KOD KOPYALANMADI: kitap kartları ve
rapor özetleri VERİDİR; kurallar kendi yapımızla yazıldı. Hepsi nedensel (lookahead yok): sinyal mum kapanışında, dolum sonraki açılışta;
pivotlar `k` mum gecikmeli onaylanır. Ad öneki `dis__`.

Ortak varsayımlar: kartlarda stop/hedef sayısı yoksa ATR stopu (stop_atr_k x ATR) ve R hedefi (hedef_r) kullanılır ("VARSAYIM" olarak
her sınıfta yazılı). Tik/sent/dolar gibi enstrümana özgü sabitler ATR katına çevrildi. Yan kural olarak piyasa endeksi, market-maker
ekranı, haber, günlük direnç gibi dış veri/öznel filtreler KODLANMADI (sınıf açıklamasında belirtilir).

Aileler: gun-zirvesi-sikisma-kirilimi, kuvvet-endeksi-bollinger, momentum-macd-diverjans, stokastik-pop, supertrend-geri-cekilme,
vwap-ema-devam, ardisik-bar-devam, brooks-kama, abcd-c-girisi, acik-alan-seviye-arasi, d1h1-macd, aksam-momentumu,
ilk-yarim-saat-son-yarim-saat, seans-yeniden-acilis-long, tuzak-kirilim, voltran-2a, voltran-2b.
KODLANMAYANLAR (stratejiler/kodlama_2026-11-07_d10d.csv): bladerunner-ters (polarite göstergesi tanımsız), rrs-goreceli-guc ve
voltran-r2 (referans endeks serisi motorda yok).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.dis._gosterge_d2 import var_ma
from motor.strateji.dis._gosterge_d5 import gun_ici_cerceve, onceki_seans_hlc, ott, seans_bilgi
from motor.strateji.dis._gosterge_d10d import abcd_c_durumu, diverjans_durumu, kama_durumu, tuzak_durumu
from motor.strateji.dis._gosterge_d9 import ardisik_say
from motor.strateji.gostergeler_b2 import asagi_kesis, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.seans_takvimi import mum_suresi
from motor.strateji.temel import Strateji


def _seri(x, idx):
    return pd.Series(x, index=idx) if not isinstance(x, pd.Series) else x


def _bool(s, idx):
    return _seri(s, idx).reindex(idx).fillna(False).astype(bool)


def _kur(m, long_ok, short_ok, stop_l, stop_s, hedef_r=0.0, hedef_l=None, hedef_s=None, cikis_long=None, cikis_short=None,
         gun_sonu=False, seans_saat=0.0, zaman=0):
    """Ortak çerçeve: yon/stop/hedef + yönlü çıkış sütunları; hedef_r > 0 ise hedef = kapanış +/- hedef_r x risk."""
    idx = m.index
    kap = m["kapanis"]
    if hedef_l is None and hedef_r and hedef_r > 0:
        hedef_l = kap + hedef_r * (kap - stop_l)
        hedef_s = kap - hedef_r * (stop_s - kap)
    out = cerceve(m, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, None, gun_sonu, seans_saat)
    out["cikis_long"] = _bool(cikis_long, idx) if cikis_long is not None else pd.Series(False, index=idx)
    out["cikis_short"] = _bool(cikis_short, idx) if cikis_short is not None else pd.Series(False, index=idx)
    if zaman and zaman > 0:
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(zaman), np.nan), index=idx)
    return out


def _ilk_an(kosul):
    """Koşulun False'tan True'ya geçtiği ilk mum (yeniden giriş yağmurunu önler)."""
    k = kosul.fillna(False).astype(bool)
    return k & ~k.shift(1, fill_value=False)


# ============================================================================== 1. gün zirvesi sıkışma kırılımı
class GunZirvesiSikismaKirilimi(Strateji):
    """dis__gun-zirvesi-sikisma-kirilimi (daytrade, 5m) — Rudd, kart daytrade__5m-gun-zirvesi-konsolidasyon-kirilimi__rudd.
    Kural (ölçülebilir tanım): seans (UTC gün; `seans_saat` ile kaydırılır, ABD hissesi için 13.5/14.5) içinde son `konsol_n` mum
    (kitap: 20-30 dk ve üzeri; 5m'de 4-9 mum) DAR (aralık <= dar_k x ATR) ve günün o ana kadarki zirvesine YAPIŞIK (gün zirvesi - konsolidasyon
    tepesi <= yapisma_atr x ATR) ise, kapanış konsolidasyon tepesini yukarı kırınca long ("ilk kırılım": pencere içinde kapanış hiç tepenin
    üstünde olamaz, çünkü tepe pencerenin yüksekleridir). Seansın ilk `ilk_mum` mumunda giriş yok (kitap: ilk 10 dk). Short: günün dibine
    yapışmış konsolidasyonun aşağı kırılımı.
    Çıkış: ATR iz süren stop (kitaptaki "wiggle" stop yükseltme karşılığı), seans sonu zorunlu çıkış.
    VARSAYIM: stop = stop_atr_k x ATR (kitap 1/4 puan; enstrümana bağlı); yapisma_atr=0.25. KODLANMADI: günlük grafikte yakın direnç,
    piyasa endeksi uyumu, market-maker ekranı, yuvarlak sayı gücü (dış veri / öznel)."""
    ad = "dis__gun-zirvesi-sikisma-kirilimi"
    stil = "daytrade"
    varsayilan_parametreler = {"konsol_n": 6, "dar_k": 1.5, "yapisma_atr": 0.25, "ilk_mum": 2, "stop_atr_k": 1.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"konsol_n": [4, 6, 9], "dar_k": [0.75, 1.5, 2.5], "stop_atr_k": [1.0, 1.5, 2.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=1.5)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        n = int(p["konsol_n"])
        seans = pd.Series(seans_kimligi(idx, p["seans_saat"]), index=idx)
        gun_yuk = y.groupby(seans).cummax().shift(1)
        gun_dib = d.groupby(seans).cummin().shift(1)
        wh = y.shift(1).rolling(n, min_periods=n).max()
        wl = d.shift(1).rolling(n, min_periods=n).min()
        mum_no = k.groupby(seans).cumcount() + 1
        hazir = (seans.shift(n) == seans) & (mum_no > p["ilk_mum"]) & a.notna() & ((wh - wl) <= p["dar_k"] * a)
        long_ok = hazir & ((gun_yuk - wh) <= p["yapisma_atr"] * a) & (k > wh)
        short_ok = (hazir & ((wl - gun_dib) <= p["yapisma_atr"] * a) & (k < wl)) if p["short"] else pd.Series(False, index=idx)
        s = p["stop_atr_k"] * a
        return _kur(m, long_ok, short_ok, k - s, k + s, gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 2. kuvvet endeksi + bollinger
class KuvvetEndeksiBollinger(Strateji):
    """dis__kuvvet-endeksi-bollinger (daytrade, 5m + 30m) — Charles, kart daytrade__bollinger-kuvvet-indeksi-forex__charles
    (kartta ana zaman dilimi 1m + 30m teyit; motor tabanı >= 5m olduğundan 5m + 30m).
    Kural: Kuvvet Endeksi = EMA(fi_n) of (kapanış - önceki kapanış) x hacim. Long: FE > 0 ve yükseliyor (FE > önceki FE) VE Bollinger
    bantlarının İKİSİ de yukarı eğimli (üst ve alt band > egim_n mum öncesine göre) VE bantlar geniş (bant genişliği >= geçmiş 100 mum
    medyanı x gen_k) VE aynı koşullar `ust_aralik` (30m) grafikte de sağlanıyor (kapanmış üst TF mumu). Short ayna. Yalnız koşulun ilk
    sağlandığı mumda giriş.
    Çıkış: stop_atr_k x ATR stop, hedef_r x R hedef (kart: $5 stop / $10 hedef = 2R), zaman çıkışı 48 mum.
    VARSAYIM: periyotlar (FE EMA 13, Bollinger 20/2) kartta yok; $5/$10 sabitleri ATR katına çevrildi (1.5 ATR / 2R).
    KODLANMADI: 'FE sıfıra yakın doji' filtresi ve FE-uyumsuzluğu + RSI<20 yan kuralı (kart: karmaşık)."""
    ad = "dis__kuvvet-endeksi-bollinger"
    stil = "daytrade"
    varsayilan_parametreler = {"fi_n": 13, "bb_n": 20, "bb_k": 2.0, "egim_n": 3, "gen_k": 1.0, "mtf": True, "ust_aralik": "30m",
                               "stop_atr_k": 1.5, "hedef_r": 2.0, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"fi_n": [2, 13], "egim_n": [3, 5, 10], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=48)

    def cikis_var_mi(self):
        return True

    def _durum(self, m):
        p = self.parametreler
        k = m["kapanis"]
        fi = g.ema((k - k.shift(1)) * m["hacim"], int(p["fi_n"]))
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        e = int(p["egim_n"])
        bw = (bb["ust"] - bb["alt"]) / bb["orta"]
        genis = bw >= bw.rolling(100, min_periods=100).median() * p["gen_k"]
        long = (fi > 0) & (fi > fi.shift(1)) & (bb["ust"] > bb["ust"].shift(e)) & (bb["alt"] > bb["alt"].shift(e)) & genis
        short = (fi < 0) & (fi < fi.shift(1)) & (bb["ust"] < bb["ust"].shift(e)) & (bb["alt"] < bb["alt"].shift(e)) & genis
        return pd.DataFrame({"l": long.astype(float), "s": short.astype(float)})

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        d = self._durum(m)
        long, short = d["l"] == 1.0, d["s"] == 1.0
        if p["mtf"]:
            u = ust_zaman(m, p["ust_aralik"], self._durum).reindex(idx)
            long &= (u["l"] == 1.0)
            short &= (u["s"] == 1.0)
        if not p["short"]:
            short = pd.Series(False, index=idx)
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        k = m["kapanis"]
        s = p["stop_atr_k"] * a
        return _kur(m, _ilk_an(long), _ilk_an(short), k - s, k + s, hedef_r=p["hedef_r"])


# ============================================================================== 3. momentum / MACD ıraksaması
class MomentumMacdDiverjans(Strateji):
    """dis__momentum-macd-diverjans (daytrade, 5m) — Bernstein, kart daytrade__momentum-macd-iraksama__bernstein.
    Kural: momentum = kapanış - kapanış[mom_n] (gosterge="macd": MACD çizgisi). Boğa: son iki onaylı fiyat dibinden (fraktal, pivot_k mum
    gecikmeli) yeni olan A, eskisi C'nin ALTINDA (fiyat yeni dip) ama momentum(A) > momentum(C) (momentum yeni dip yapmadı); aralık
    min_aralik (kart: >= 6 çubuk) .. max_aralik (kart: ~60 çubuk). E = C ile A arasındaki momentum ZİRVESİ. Tetik: bar KAPANIŞINDA
    momentum E'yi yukarı keser (bar içi tetik yok). Kurulum A'dan sonra fiyat A'nın altına inerse ya da onaydan gecerlilik mum sonra
    bozulur. Short ayna (yeni tepe, momentum yeni tepe yapmaz, E = aradaki dip, momentum E'nin altına iner).
    Çıkış: stop A'nın (short: tepenin) tamponlu ötesi ("ıraksama bozulursa çık"), hedef_r x R (kart P1 = A-D aralığının yarısı: öznel,
    yerine R), 1R'de başabaş stop + 3 ATR iz süren, seans sonu zorunlu çıkış.
    VARSAYIM: swing dibi 'pivot_k' mumluk fraktal; stop tamponu 0.25 ATR; maks risk 6 ATR (üstü atlanır). KODLANMADI: 'Momentum veya
    MACD'den ilki tetiklemeli' (tek gösterge seçilir), FPO, P2."""
    ad = "dis__momentum-macd-diverjans"
    stil = "daytrade"
    varsayilan_parametreler = {"gosterge": "momentum", "mom_n": 10, "pivot_k": 3, "min_aralik": 6, "max_aralik": 60,
                               "gecerlilik": 30, "tampon_atr": 0.25, "maks_risk_atr": 6.0, "hedef_r": 2.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"mom_n": [5, 10, 14], "pivot_k": [2, 3, 4], "hedef_r": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0, atr_iz_suren_k=3.0)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        if p["gosterge"] == "macd":
            mom = g.macd(k)["macd"]
        elif p["gosterge"] == "momentum":
            mom = k - k.shift(int(p["mom_n"]))
        else:
            raise ValueError("gosterge 'momentum' veya 'macd' olmalı")
        args = dict(k=int(p["pivot_k"]), min_aralik=int(p["min_aralik"]), max_aralik=int(p["max_aralik"]),
                    gecerlilik=int(p["gecerlilik"]))
        bo = diverjans_durumu(y.to_numpy(), d.to_numpy(), mom.to_numpy(), tepe_modu=False, **args).set_axis(idx)
        ay = diverjans_durumu(y.to_numpy(), d.to_numpy(), mom.to_numpy(), tepe_modu=True, **args).set_axis(idx)
        long_ok = bo["aktif"] & yukari_kesis(mom, bo["e_seviye"])
        short_ok = ay["aktif"] & asagi_kesis(mom, ay["e_seviye"]) if p["short"] else pd.Series(False, index=idx)
        stop_l = bo["a_fiyat"] - p["tampon_atr"] * a
        stop_s = ay["a_fiyat"] + p["tampon_atr"] * a
        long_ok &= (k - stop_l) <= p["maks_risk_atr"] * a
        short_ok &= (stop_s - k) <= p["maks_risk_atr"] * a
        return _kur(m, long_ok, short_ok, stop_l, stop_s, hedef_r=p["hedef_r"], gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 4. stokastik pop
class StokastikPop(Strateji):
    """dis__stokastik-pop (daytrade, 5m) — Bernstein, kart daytrade__stokastik-pop__bernstein.
    Kural: yavaş %K (k_n, SMA ile k_yavas) bar KAPANIŞINDA ust_esik (70) üstüne çıkarsa long; %K ust_esik altına inince çık.
    Short: %K alt_esik (30) altına inerse short; %K alt_esik üstüne çıkınca çık. Seans sonu zorunlu çıkış.
    Çıkış: gösterge çıkışı + ATR iz süren stop (kart: kârlı pozisyonda iz süren) + felaket stopu stop_atr_k x ATR.
    VARSAYIM: kartta stop sayısı yok -> 2 ATR; 'küçük kârda kısmi çıkış' kodlanmadı (yargı gerekir)."""
    ad = "dis__stokastik-pop"
    stil = "daytrade"
    varsayilan_parametreler = {"k_n": 9, "k_yavas": 3, "ust_esik": 70.0, "alt_esik": 30.0, "stop_atr_k": 2.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"k_n": [9, 14], "ust_esik": [70.0, 75.0, 80.0], "stop_atr_k": [1.5, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        sk = g.stokastik(y, d, k, int(p["k_n"]), int(p["k_yavas"]))["d"]    # yavaş %K = ham %K'nın k_yavas SMA'sı
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        ust_y, ust_a = yukari_kesis(sk, p["ust_esik"]), asagi_kesis(sk, p["ust_esik"])
        alt_a, alt_y = asagi_kesis(sk, p["alt_esik"]), yukari_kesis(sk, p["alt_esik"])
        short_ok = alt_a if p["short"] else pd.Series(False, index=idx)
        s = p["stop_atr_k"] * a
        return _kur(m, ust_y, short_ok, k - s, k + s, cikis_long=ust_a, cikis_short=alt_y,
                    gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 5. supertrend geri çekilme
class SupertrendGeriCekilme(Strateji):
    """dis__supertrend-geri-cekilme (daytrade, 5m) — Roy, kart daytrade__supertrend-geri-cekilme__roy.
    Kural: Supertrend(st_n, st_k) yükselişte; son mum(lar)da fiyat Supertrend çizgisine DOKUNDU (dokunuş: dip <= çizgi + tol_atr x ATR,
    kapanış çizginin üstünde = destek buldu) ve şimdiki kapanış önceki mum zirvesini geçti -> long. Short ayna (çizgiye dokunup direnç,
    önceki mum dibi kırılır).
    Çıkış: Supertrend yön değişince; stop = son 3 mumun dibi (short: zirvesi) +/- tampon (kart: 'anlık swing dibi'); hedef_r > 0 ise R hedefi.
    VARSAYIM: kartta dokunuş toleransı yok -> tol_atr (grid 0.25..1); Supertrend (10, 3); hedef_r=0 (kart: gösterge dönene dek)."""
    ad = "dis__supertrend-geri-cekilme"
    stil = "daytrade"
    varsayilan_parametreler = {"st_n": 10, "st_k": 3.0, "tol_atr": 0.5, "swing_n": 3, "tampon_atr": 0.1, "hedef_r": 0.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "gun_sonu": True, "short": True}
    parametre_izgarasi = {"st_k": [2.0, 3.0, 4.0], "tol_atr": [0.25, 0.5, 1.0], "hedef_r": [0.0, 2.0, 3.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        st = g.supertrend(y, d, k, int(p["st_n"]), float(p["st_k"]))
        cz, yon = st["cizgi"], st["yon"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        dok_l = (d <= cz + p["tol_atr"] * a) & (k > cz)
        dok_s = (y >= cz - p["tol_atr"] * a) & (k < cz)
        long_ok = (yon == 1) & (yon.shift(1) == 1) & dok_l.shift(1, fill_value=False) & (k > y.shift(1))
        short_ok = ((yon == -1) & (yon.shift(1) == -1) & dok_s.shift(1, fill_value=False) & (k < d.shift(1))) if p["short"] \
            else pd.Series(False, index=idx)
        sn = int(p["swing_n"])
        stop_l = d.rolling(sn, min_periods=sn).min() - p["tampon_atr"] * a
        stop_s = y.rolling(sn, min_periods=sn).max() + p["tampon_atr"] * a
        return _kur(m, long_ok, short_ok, stop_l, stop_s, hedef_r=p["hedef_r"], cikis_long=(yon == -1), cikis_short=(yon == 1),
                    gun_sonu=bool(p["gun_sonu"]), seans_saat=p["seans_saat"])


# ============================================================================== 6. VWAP + EMA devam
class VwapEmaDevam(Strateji):
    """dis__vwap-ema-devam (daytrade, 5m) — Christensen, kart daytrade__vwap-ema-trend__christensen.
    Kural: kapanış seans VWAP'ının üstünde VE 9 ve 20 EMA'nın üstünde (EMA9 > EMA20) iken, önceki mum `ema_ref` EMA'sına geri çekilip
    dokundu (dip <= EMA + tol_atr x ATR) ve şimdiki mum teyit verdi (yeşil mum, kapanış EMA'nın ve önceki kapanışın üstünde) -> long.
    Short ayna (VWAP ve EMA'ların altında, EMA'ya geri çekilip direnç, kırmızı teyit mumu). Seansın ilk `min_mum` mumunda giriş yok
    (kart: açılışta değil). Çıkış: kapanış `ema_ref` EMA'sının altına (short: üstüne) inince ("EMA kırılınca çık"); stop = geri çekilme
    dibinin (short: zirvesinin) tamponlu ötesi; seans sonu zorunlu çıkış.
    VARSAYIM: teyit mumu tanımı kartta yok (yukarıdaki); tamponlar ATR katı (kart: 5-10 sent); kısmi kâr alma kodlanmadı."""
    ad = "dis__vwap-ema-devam"
    stil = "daytrade"
    varsayilan_parametreler = {"ema_ref": 20, "ema_hizli": 9, "tol_atr": 0.3, "tampon_atr": 0.25, "min_mum": 12, "hedef_r": 0.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"ema_ref": [9, 20], "tol_atr": [0.1, 0.3, 0.5], "tampon_atr": [0.25, 0.5, 1.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        seans = seans_kimligi(idx, p["seans_saat"])
        v = g.vwap_seans(y, d, k, m["hacim"], seans)
        vw, mum_no = v["vwap"], v["mum_no"]
        e_h, e_y = g.ema(k, int(p["ema_hizli"])), g.ema(k, 20)
        ref = g.ema(k, int(p["ema_ref"]))
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        hazir = (mum_no > p["min_mum"]) & vw.notna() & ref.notna() & a.notna()
        trend_l = (k > vw) & (k > e_h) & (k > e_y) & (e_h > e_y)
        trend_s = (k < vw) & (k < e_h) & (k < e_y) & (e_h < e_y)
        dok_l = (d <= ref + p["tol_atr"] * a)
        dok_s = (y >= ref - p["tol_atr"] * a)
        long_ok = hazir & trend_l & dok_l.shift(1, fill_value=False) & (k > o) & (k > k.shift(1)) & (k > ref)
        short_ok = (hazir & trend_s & dok_s.shift(1, fill_value=False) & (k < o) & (k < k.shift(1)) & (k < ref)) if p["short"] \
            else pd.Series(False, index=idx)
        stop_l = np.minimum(d, d.shift(1)) - p["tampon_atr"] * a
        stop_s = np.maximum(y, y.shift(1)) + p["tampon_atr"] * a
        return _kur(m, long_ok, short_ok, stop_l, stop_s, hedef_r=p["hedef_r"], cikis_long=(k < ref), cikis_short=(k > ref),
                    gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 7. ardışık bar devam (mikro kanal)
class ArdisikBarDevam(Strateji):
    """dis__ardisik-bar-devam (daytrade, 5m; swing varyantı 4h/1d) — Brooks 'mikro kanal' (daytrade__mikro-kanal-gec-giris__brooks) +
    TIS BTC Momentum (repo raporu). Ana stil daytrade; swing varyantı için gun_sonu=False ve sma_n=50 ile 4h/1d kullanılır.
    Kural: `n_bar` ardışık boğa TREND mumu (kapanış > açılış, gövde >= govde_oran x aralık, gövde <= buyuk_k x ATR: 'büyük olmayan' =
    tükenme/climax mumu değil) -> serinin n_bar'ıncı mumunda piyasadan long (devam). Short: n_bar ardışık ayı trend mumu.
    Opsiyonel filtre: sma_n > 0 ise long için kapanış > SMA (short için altında) (TIS: SMA50).
    Çıkış: stop_atr_k x ATR başlangıç stopu + aynı mesafeli ATR iz süren stop (kart: 'orijinal girişle aynı iz süren stop'); gun_sonu=True
    ise seans sonu zorunlu çıkış. Kartın 'geri çekilmelerde ekle' kuralı kodlanmadı (pozisyon büyütme = yasak sınıfı); TIS'in %40 ATR
    boyutlandırma tavanı risk motorunda.
    VARSAYIM: gövde oranı 0.5, 'büyük' eşiği 2.5 ATR, stop 2 ATR (kartta sayısal değer yok). Karşı kanıt: daytrade__ardisik-bar-tukenme
    ters (tükenme) mantığını kodlar; bu aile devam yönündedir."""
    ad = "dis__ardisik-bar-devam"
    stil = "daytrade"
    varsayilan_parametreler = {"n_bar": 4, "govde_oran": 0.5, "buyuk_k": 2.5, "sma_n": 0, "stop_atr_k": 2.0, "atr_periyot": 14,
                               "gun_sonu": True, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"n_bar": [3, 4, 5], "stop_atr_k": [1.5, 2.0, 3.0], "sma_n": [0, 50, 100]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.0)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        govde = (k - o).abs()
        aralik = (y - d).where(y > d)
        kucuk = (govde >= p["govde_oran"] * aralik) & (govde <= p["buyuk_k"] * a)
        boga, ayi = (k > o) & kucuk, (k < o) & kucuk
        n = int(p["n_bar"])
        long_ok = ardisik_say(boga) == n
        short_ok = (ardisik_say(ayi) == n) if p["short"] else pd.Series(False, index=idx)
        if int(p["sma_n"]) > 0:
            sma = g.sma(k, int(p["sma_n"]))
            long_ok &= k > sma
            short_ok &= k < sma
        s = p["stop_atr_k"] * a
        out = _kur(m, long_ok & a.notna(), short_ok & a.notna(), k - s, k + s,
                   gun_sonu=bool(p["gun_sonu"]), seans_saat=p["seans_saat"])
        return out


# ============================================================================== 8. Brooks kamaları
class BrooksKama(Strateji):
    """dis__brooks-kama (daytrade, 5m) — Brooks, kartlar daytrade__kama-uc-itme__brooks (kama dönüşü) ve
    daytrade__kama-geri-cekilme-ve-donus__brooks (trend içi kama geri çekilmesi; aynı üç-itme mantığı).
    Ölçülebilir tanım ('itme'): fraktal pivot (pivot_k mum gecikmeli onay). Boğa kaması (kama dibi): ardışık üç pivot dip L1 > L2 > L3
    (üç aşağı itme) ve aradaki pivot tepeler Ha (L1-L2) > Hb (L2-L3) (alçalan tepeler = yakınsayan kama). L3 onayından sonra
    `gecerlilik` mum içinde, L3 kırılmadıkça: boğa sinyal mumu = yeşil mum, kapanış aralığın üst `kapanis_oran` diliminde (kart: 'en
    yükseğine yakın kapanan boğa çubuğu') -> long (kama başına ilk sinyal). Short: ayna (kama tepesi).
    Çıkış: stop = L3 (short: son tepe) ötesi tamponlu ('1 tik ötesi' yerine tampon_atr x ATR); hedef: hedef_modu 0 -> hedef_r x R,
    1 -> kamanın başlangıcı (Ha; en az 0.5R uzaktaysa, yoksa R hedefi) (kart: 'kama başlangıcı / en az iki ayak'). Seans sonu zorunlu çıkış.
    VARSAYIM: kartta itme tanımı yok (yukarıdaki); trend çizgisi/kanal aşımı filtresi (kart) kodlanmadı; kama içi/dışı ayrımı (kanal mı
    kama mı) yoruma açık olduğundan her iki kart tek aile."""
    ad = "dis__brooks-kama"
    stil = "daytrade"
    varsayilan_parametreler = {"pivot_k": 2, "gecerlilik": 12, "kapanis_oran": 0.3, "tampon_atr": 0.25, "hedef_modu": 0,
                               "hedef_r": 2.0, "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"pivot_k": [2, 3], "gecerlilik": [8, 16], "hedef_modu": [0, 1], "hedef_r": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        args = dict(k=int(p["pivot_k"]), gecerlilik=int(p["gecerlilik"]))
        bo = kama_durumu(y.to_numpy(), d.to_numpy(), tepe_modu=False, **args).set_axis(idx)
        ay = kama_durumu(y.to_numpy(), d.to_numpy(), tepe_modu=True, **args).set_axis(idx)
        aralik = (y - d).where(y > d)
        guclu_boga = (k > o) & ((y - k) <= p["kapanis_oran"] * aralik)
        guclu_ayi = (k < o) & ((k - d) <= p["kapanis_oran"] * aralik)
        sl = bo["aktif"] & guclu_boga
        ss = ay["aktif"] & guclu_ayi
        sl = sl & (sl.astype(int).groupby(bo["uc_fiyat"].fillna(-1.0)).cumsum() == 1)
        ss = ss & (ss.astype(int).groupby(ay["uc_fiyat"].fillna(-1.0)).cumsum() == 1)
        if not p["short"]:
            ss = pd.Series(False, index=idx)
        stop_l = bo["uc_fiyat"] - p["tampon_atr"] * a
        stop_s = ay["uc_fiyat"] + p["tampon_atr"] * a
        hl = k + p["hedef_r"] * (k - stop_l)
        hs = k - p["hedef_r"] * (stop_s - k)
        if int(p["hedef_modu"]) == 1:
            hl = pd.Series(np.where(bo["baslangic"] >= k + 0.5 * (k - stop_l), bo["baslangic"], hl), index=idx)
            hs = pd.Series(np.where(ay["baslangic"] <= k - 0.5 * (stop_s - k), ay["baslangic"], hs), index=idx)
        return _kur(m, sl, ss, stop_l, stop_s, hedef_l=hl, hedef_s=hs, gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 9. ABCD, C girişi
class AbcdCGirisi(Strateji):
    """dis__abcd-c-girisi (daytrade, 5m) — Christensen, kart daytrade__abcd-deseni__christensen (kartta 1m; motor >= 5m).
    Boğa ABCD: A = onaylı pivot dip, B = pivot tepe (A->B güçlü yükseliş: B-A >= ab_atr x ATR), C = sonraki pivot dip, C > A (yüksek dip)
    ve geri çekilme oranı (B-C)/(B-A) geri_min..geri_max (Fibonacci oranı kartta yok -> 0.382-0.786 VARSAYIM). Giriş: C'nin onaylandığı mumda
    (pivot_k mum sonra, 'destek buldu') fiyat C'ye YAKIN (kapanış - C <= yakin_atr x ATR), kapanış C'nin üstünde ve mum yeşilse long
    (kart: B'de kovalamayın, C'ye yakın al). Short: ters ABCD (A tepe, B dip, C alçak tepe), kırmızı onay mumu.
    Çıkış: stop C'nin (short: tepenin) tamponlu ötesi; hedef D = C + (B-A) (AB=CD; kart: D'de yarısı satılır — kısmi çıkış hedefte tam çıkış
    olarak basitleştirildi); minimum ödül/risk min_rr. Seans sonu zorunlu çıkış.
    KODLANMADI: A->B yüksek hacim şartı, 200 SMA/5m yeni dip ile kalan pozisyon yönetimi. swing__harmonik-abcd'den farkı: o D'de dönüş
    (D < B), burada C'de trend-yönlü giriş."""
    ad = "dis__abcd-c-girisi"
    stil = "daytrade"
    varsayilan_parametreler = {"pivot_k": 3, "ab_atr": 3.0, "geri_min": 0.382, "geri_max": 0.786, "yakin_atr": 1.0, "tampon_atr": 0.25,
                               "min_rr": 1.0, "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"pivot_k": [2, 3, 4], "ab_atr": [2.0, 3.0, 4.0], "yakin_atr": [0.5, 1.0, 2.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        args = dict(k=int(p["pivot_k"]), ab_atr=float(p["ab_atr"]), geri_min=float(p["geri_min"]), geri_max=float(p["geri_max"]))
        bo = abcd_c_durumu(y.to_numpy(), d.to_numpy(), a.to_numpy(), tepe_modu=False, **args).set_axis(idx)
        ay = abcd_c_durumu(y.to_numpy(), d.to_numpy(), a.to_numpy(), tepe_modu=True, **args).set_axis(idx)
        stop_l = bo["c"] - p["tampon_atr"] * a
        stop_s = ay["c"] + p["tampon_atr"] * a
        long_ok = (bo["yeni"] & (k > bo["c"]) & (k > o) & ((k - bo["c"]) <= p["yakin_atr"] * a)
                   & ((bo["d"] - k) >= p["min_rr"] * (k - stop_l)))
        short_ok = (ay["yeni"] & (k < ay["c"]) & (k < o) & ((ay["c"] - k) <= p["yakin_atr"] * a)
                    & ((k - ay["d"]) >= p["min_rr"] * (stop_s - k))) if p["short"] else pd.Series(False, index=idx)
        return _kur(m, long_ok, short_ok, stop_l, stop_s, hedef_l=bo["d"], hedef_s=ay["d"], gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 10. açık alan (seviyeler arası)
class AcikAlanSeviyeArasi(Strateji):
    """dis__acik-alan-seviye-arasi (daytrade, 5m) — Noonan, kart daytrade__acik-alanlar-5-tik__noonan.
    Seviyeler: önceki seansın açılış/yüksek/düşük/kapanışı + bugünün İLK `ilk_dk` dakikasının yüksek/düşüğü (kart: ilk 2 saatin
    iki-mum-sol/iki-sağ swing zirve/dipleri; burada ilk 2 saatin uç değerleri ile yaklaşıldı — VARSAYIM). `ilk_dk` dolmadan işlem yok.
    Kural: kapanış bir seviyenin `giris_atr` x ATR üstüne çıkar (önceki kapanış altındaydı) VE o seviyenin üstündeki en yakın seviye
    >= bosluk_atr x ATR uzakta (ya da hiç yok) = 'geniş açık alan' -> long. Aşağı yönde ayna (short).
    Çıkış: stop_atr_k x ATR (kart 10 tik), hedef_r x R (kart 5 tik kâr / 10 tik risk = 0.5R; varsayılan 1R), seans sonu zorunlu çıkış.
    VARSAYIM: tik -> ATR; 'geniş' eşiği kartta yok (grid 2-6 ATR); seans = `seans_saat` UTC'den başlayan 24 saat (ABD hissesi için 13.5/14.5).
    KODLANMADI: yalnız RTH verisi filtresi (veri sağlayıcıya bağlı)."""
    ad = "dis__acik-alan-seviye-arasi"
    stil = "daytrade"
    varsayilan_parametreler = {"ilk_dk": 120, "giris_atr": 0.25, "bosluk_atr": 4.0, "stop_atr_k": 1.0, "hedef_r": 1.0,
                               "atr_periyot": 14, "seans_saat": 0.0, "short": True}
    parametre_izgarasi = {"bosluk_atr": [2.0, 4.0, 6.0], "giris_atr": [0.1, 0.25, 0.5], "hedef_r": [0.5, 1.0, 2.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        seans = pd.Series(seans_kimligi(idx, p["seans_saat"]), index=idx)
        dt = pd.Series(idx, index=idx)
        gecen = (dt - dt.groupby(seans).transform("first")).dt.total_seconds() / 60.0     # seans başından geçen dk (mum açılışı)
        sure = float(mum_suresi(idx) / pd.Timedelta(minutes=1)) if len(idx) > 1 else 5.0
        ilk_bolge = gecen < p["ilk_dk"]
        ilk_h = y.where(ilk_bolge).groupby(seans).cummax()      # seans içi kümülatif (nedensel)
        ilk_l = d.where(ilk_bolge).groupby(seans).cummin()
        # ilk bölge bitince değer sabitlenir: bölge dışı mumlarda ffill ile taşınır
        ilk_h = ilk_h.groupby(seans).ffill()
        ilk_l = ilk_l.groupby(seans).ffill()
        g_ = m.groupby(seans)
        onc = pd.DataFrame({"o": g_["acilis"].first(), "h": g_["yuksek"].max(), "l": g_["dusuk"].min(),
                            "c": g_["kapanis"].last()}).shift(1)
        seviyeler = pd.DataFrame({
            "po": onc["o"].reindex(seans).to_numpy(), "ph": onc["h"].reindex(seans).to_numpy(),
            "pl": onc["l"].reindex(seans).to_numpy(), "pc": onc["c"].reindex(seans).to_numpy(),
            "ih": ilk_h.to_numpy(), "il": ilk_l.to_numpy()}, index=idx)
        hazir = (gecen >= p["ilk_dk"]) & a.notna() & seviyeler.notna().all(axis=1)
        sv = seviyeler.to_numpy()
        n, nl = sv.shape
        yukari_ok = np.zeros(n, dtype=bool)
        asagi_ok = np.zeros(n, dtype=bool)
        kn, kp, an = k.to_numpy(), k.shift(1).to_numpy(), a.to_numpy()
        gi, bo = float(p["giris_atr"]), float(p["bosluk_atr"])
        for j in range(nl):
            L = sv[:, j]
            ust = np.where(sv > (L + 1e-12)[:, None], sv, np.inf).min(axis=1)       # L'nin üstündeki en yakın seviye
            alt = np.where(sv < (L - 1e-12)[:, None], sv, -np.inf).max(axis=1)      # L'nin altındaki en yakın seviye
            with np.errstate(invalid="ignore"):
                gecis_yu = (kn >= L + gi * an) & (kp < L + gi * an)
                gecis_as = (kn <= L - gi * an) & (kp > L - gi * an)
                yukari_ok |= gecis_yu & ((ust - L) >= bo * an)
                asagi_ok |= gecis_as & ((L - alt) >= bo * an)
        long_ok = hazir & pd.Series(yukari_ok, index=idx)
        short_ok = (hazir & pd.Series(asagi_ok, index=idx)) if p["short"] else pd.Series(False, index=idx)
        s = p["stop_atr_k"] * a
        return _kur(m, long_ok, short_ok, k - s, k + s, hedef_r=p["hedef_r"], gun_sonu=True, seans_saat=p["seans_saat"])


# ============================================================================== 12. D1H1 MACD
class D1H1Macd(Strateji):
    """dis__d1h1-macd (daytrade, 1h + 1d) — repo raporları 'Bitcoin D1H1 MACD Filter' ve 'Bitcoin D1H1 + Negative Candle Exit'.
    Kural: TAMAMLANMIŞ günlük mumda MACD(12,26,9) çizgisi > sinyal ise, saatlik MACD çizgisinin sinyali yukarı kesmesinde long
    (short=True: günlük MACD < sinyal iken aşağı kesişimde short). Çıkış modları (cikis_modu): 0 = bir saatlik mum tut (yayımlanan
    varyant), 1 = ilk NEGATİF saatlik mum kapanışında çık (kapanış < açılış; short için pozitif), 2 = saatlik MACD ters kesişimi.
    VARSAYIM: stop = stop_atr_k x ATR (raporda stop yok). Günlük MACD değeri ust_zaman ile yalnız gün kapandıktan sonra kullanılır."""
    ad = "dis__d1h1-macd"
    stil = "daytrade"
    varsayilan_parametreler = {"cikis_modu": 1, "hizli": 12, "yavas": 26, "sinyal": 9, "stop_atr_k": 2.0, "atr_periyot": 14,
                               "short": False}
    parametre_izgarasi = {"cikis_modu": [0, 1, 2], "stop_atr_k": [1.5, 2.0, 3.0], "short": [False, True]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        h, ya, si = int(p["hizli"]), int(p["yavas"]), int(p["sinyal"])
        gun = ust_zaman(m, "1d", lambda u: pd.DataFrame({"fark": (lambda mm: mm["macd"] - mm["sinyal"])(g.macd(u["kapanis"], h, ya, si))}))
        gfark = gun["fark"].reindex(idx)
        mm = g.macd(k, h, ya, si)
        yu, asg = yukari_kesis(mm["macd"], mm["sinyal"]), asagi_kesis(mm["macd"], mm["sinyal"])
        long_ok = yu & (gfark > 0)
        short_ok = (asg & (gfark < 0)) if p["short"] else pd.Series(False, index=idx)
        modu = int(p["cikis_modu"])
        s = p["stop_atr_k"] * a
        cl = cs = None
        zaman = 0
        if modu == 0:
            zaman = 1
        elif modu == 1:
            cl, cs = (k < o), (k > o)
        elif modu == 2:
            cl, cs = asg, yu
        else:
            raise ValueError("cikis_modu 0, 1 veya 2 olmalı")
        return _kur(m, long_ok, short_ok, k - s, k + s, cikis_long=cl, cikis_short=cs, zaman=zaman)


# ============================================================================== 13. akşam momentumu
class AksamMomentumu(Strateji):
    """dis__aksam-momentumu (daytrade, 15m) — repo raporu 'Day trade — S10 Akşam Momentumu'. (Benzer: dis__trend-gun-ici; o seans
    getirisi eşiği + son saat girişidir, burada GÜNLÜK ATR eşiği, EMA trend filtreleri ve akşam penceresi var.)
    Kural: 4h ve 1h EMA20 > EMA50 ve kapanış > 1h EMA50 (kapanmış üst TF mumları); UTC `bas_saat` <= saat < `bit_saat` penceresinde
    kapanış, gün açılışının (UTC günün ilk mumunun açılışı) en az esik_k x GÜNLÜK ATR(14) üstündeyse (önceki tamamlanmış günlerden)
    long; günde bir işlem. Yalnız long. Stop = stop_gatr x günlük ATR; UTC gün sonu zorunlu çıkış."""
    ad = "dis__aksam-momentumu"
    stil = "daytrade"
    varsayilan_parametreler = {"bas_saat": 16, "bit_saat": 20, "esik_k": 1.0, "stop_gatr": 1.0, "ema_hizli": 20, "ema_yavas": 50,
                               "atr_periyot": 14}
    parametre_izgarasi = {"bas_saat": [14, 16, 18], "esik_k": [0.75, 1.0, 1.5], "stop_gatr": [0.75, 1.0, 1.5]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        hz, yv = int(p["ema_hizli"]), int(p["ema_yavas"])

        def trend(u):
            return pd.DataFrame({"t": (g.ema(u["kapanis"], hz) > g.ema(u["kapanis"], yv)).astype(float),
                                 "e50": g.ema(u["kapanis"], yv)})

        t4 = ust_zaman(m, "4h", trend).reindex(idx)
        t1 = ust_zaman(m, "1h", trend).reindex(idx)
        gatr = ust_zaman(m, "1d", lambda u: pd.DataFrame({"a": g.atr(u["yuksek"], u["dusuk"], u["kapanis"], int(p["atr_periyot"]))}))["a"].reindex(idx)
        gun = idx.floor("D")
        gun_acilis = o.groupby(gun).transform("first")
        saat = pd.Series(idx.hour + idx.minute / 60.0, index=idx)
        kapanis_saat = saat      # mum açılış saati; mum kapanışı sonraki açılışta -> pencere açılış saatine göre
        pencere = (kapanis_saat >= p["bas_saat"]) & (kapanis_saat < p["bit_saat"])
        kosul = (pencere & (t4["t"] == 1.0) & (t1["t"] == 1.0) & (k > t1["e50"]) & gatr.notna()
                 & (k >= gun_acilis + p["esik_k"] * gatr))
        ilk = kosul & (kosul.astype(int).groupby(gun).cumsum() == 1)
        s = p["stop_gatr"] * gatr
        return _kur(m, ilk, pd.Series(False, index=idx), k - s, k + s, gun_sonu=True, seans_saat=0.0)


# ============================================================================== 14. ilk yarım saat -> son yarım saat
class IlkYarimSaatSonYarimSaat(Strateji):
    """dis__ilk-yarim-saat-son-yarim-saat (daytrade, 5m-30m) — repo kodu 'Attention Prop Traders: first half hour predicts last half hour'.
    Kural: seansın ilk `ilk_dk` dakikasının getirisi (ilk bölümün son kapanışı / seans açılışı - 1) esik'ten büyükse son `son_dk` dakikada
    long, -esik'ten küçükse short; seans sonunda kapanır. Karar mumu: kapanışı seans kapanışından `son_dk` dk önce veya daha erken olan
    SON mum (dis__trend-gun-ici ile aynı zamanlama; farkı getiri penceresi: oradaki tüm seans açılışından karar anına, burada yalnız ilk bölüm).
    seans: 'utc_gun' (24 saat piyasalar) veya 'abd_hisse' (09:30-16:00 New York). Seans başına tek karar.
    VARSAYIM: stop = stop_atr_k x ATR (kaynakta stop yok); basit sürümün hipotetik getirisi (%6.34) kanıtsız iddiadır.
    abd_hisse'de karar mumunun seans çıkışı penceresine denk gelmemesi için mum süresi <= son_dk/2 önerilir.
    d11j EK (varsayılanlar eskisiyle aynı; ızgaraya girmez; kaynak Gao 2018 ETF gün içi momentumu): r1_ref="onceki_kapanis" -> ilk bölüm getirisi
    seans açılışına değil bir önceki seansın kapanışına göre (gece getirisi dahil; r1). sinyal="r12" -> karar mumundaki kapanış / (son_dk dk
    önceki kapanış) - 1, yani kapanıştan 2*son_dk ile son_dk dk önce arasındaki getiri (r12; mum zamanı asof ile aranır, yaklaşık);
    "r1_r12" -> ikisi aynı yönde ve eşik üstünde olmalı. İlk bölüm = r1 (varsayılan)."""
    ad = "dis__ilk-yarim-saat-son-yarim-saat"
    stil = "daytrade"
    varsayilan_parametreler = {"seans": "utc_gun", "ilk_dk": 30, "son_dk": 30, "esik": 0.0, "stop_atr_k": 2.0, "atr_periyot": 14,
                               "short": True, "r1_ref": "acilis", "sinyal": "r1"}
    parametre_izgarasi = {"ilk_dk": [30, 60], "son_dk": [30, 60], "esik": [0.0, 0.001, 0.002], "stop_atr_k": [2.0, 3.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        bil = seans_bilgi(m, p["seans"], float(p["son_dk"]))
        c, sid, ici = bil["c"], pd.Series(bil["sid"], index=idx), pd.Series(bil["ici"], index=idx)
        dt = pd.Series(idx, index=idx)
        bas = dt.where(ici).groupby(sid).transform("first")
        gecen_dk = (pd.DatetimeIndex(c["bar_kapanis"]) - pd.DatetimeIndex(bas)).total_seconds() / 60.0   # mum KAPANIŞINA kadar
        ilk_mi = ici & pd.Series(np.asarray(gecen_dk) <= p["ilk_dk"] + 1e-9, index=idx)
        ilk_kap = k.where(ilk_mi).groupby(sid).ffill()           # ilk bölümün son kapanışı (nedensel)
        if p["r1_ref"] == "onceki_kapanis":
            r = ilk_kap / onceki_seans_hlc(m, sid, ici.to_numpy())["c"] - 1.0
        elif p["r1_ref"] == "acilis":
            r = ilk_kap / bil["acilis"] - 1.0
        else:
            raise ValueError(f"Bilinmeyen r1_ref: {p['r1_ref']}")
        if p["sinyal"] != "r1":
            onc = k.asof(idx - pd.Timedelta(minutes=float(p["son_dk"])))
            r12 = k / pd.Series(onc.to_numpy(), index=idx) - 1.0
            if p["sinyal"] == "r12":
                r = r12
            elif p["sinyal"] == "r1_r12":
                r = pd.Series(np.where(np.sign(r) == np.sign(r12), np.where(r.abs() < r12.abs(), r, r12), np.nan), index=idx)
            else:
                raise ValueError(f"Bilinmeyen sinyal: {p['sinyal']}")
        karar = pd.Series(c["karar"].to_numpy(), index=idx) & bil["acilis_tamam"] & r.notna()
        karar &= ~pd.Series(sid).where(karar.to_numpy()).duplicated().to_numpy()     # seans başına tek karar
        long_ok = karar & (r > p["esik"])
        short_ok = (karar & (r < -p["esik"])) if p["short"] else pd.Series(False, index=idx)
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return gun_ici_cerceve(m, p["seans"], c, long_ok, short_ok, k - a, k + a)


# ============================================================================== 16. seans yeniden açılış long
class SeansYenidenAcilisLong(Strateji):
    """dis__seans-yeniden-acilis-long (daytrade, 1h) — repo kodu 'SessionReopenEA'. Günlük CME bakım arası sonrası yeniden açılışta long,
    2 saat tut.
    Kural: UTC `giris_saat`'te (bakım arası sonrası yeniden açılış saati; CME ~22:00/23:00 UTC mevsime göre) açılan muma long (sinyal bir
    önceki mumun kapanışında, dolum o açılışta); `pazartesi_atla` ise o gün Pazartesi ise giriş yok (EA varsayılanı); günde bir işlem.
    Çıkış: `tut_mum` mum (1h'de 2) sonra zaman çıkışı; stop = stop_k x son 24 mumun ortalama (yüksek-düşük) aralığı (kaynak: 2.0 x ortalama
    saatlik aralık). Yazar maliyeti ~60 puana düzeltince sonuçların zayıfladığını bildirir (negatif kanıt).
    VARSAYIM: giriş saati kaynak veri saat dilimine bağlıdır -> UTC saat parametre; kripto 7/24'te bakım arası olmadığından saat yapaydır
    (dis__btc-gece-seans benzeri takvim stratejisi). Short yok."""
    ad = "dis__seans-yeniden-acilis-long"
    stil = "daytrade"
    varsayilan_parametreler = {"giris_saat": 23, "pazartesi_atla": True, "tut_mum": 2, "stop_k": 2.0, "aralik_n": 24}
    parametre_izgarasi = {"giris_saat": [22, 23, 0], "tut_mum": [1, 2, 4], "stop_k": [1.0, 2.0, 3.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        fark = ((idx[1:] - idx[:-1]) / pd.Timedelta(seconds=1)).to_numpy() if len(idx) > 1 else np.array([])
        sure = np.r_[np.nan, np.minimum.accumulate(fark)] if len(idx) > 1 else np.full(len(idx), np.nan)   # nedensel mum süresi
        kap_zamani = idx + pd.to_timedelta(np.where(np.isnan(sure), 0.0, sure), unit="s")
        kapanis_saat = pd.Series(kap_zamani.hour + kap_zamani.minute / 60.0, index=idx)
        hedef_gun = pd.Series(kap_zamani.dayofweek, index=idx)           # dolum gününün haftanın günü (kapanış anı = açılış)
        ok = (~np.isnan(sure)) & (np.abs(kapanis_saat - float(p["giris_saat"])) < 1e-6)
        if p["pazartesi_atla"]:
            ok &= (hedef_gun != 0)
        ort = (y - d).rolling(int(p["aralik_n"]), min_periods=int(p["aralik_n"])).mean()
        ok &= ort.notna()
        gun = pd.Series(kap_zamani.floor("D"), index=idx)
        ok &= (ok.astype(int).groupby(gun).cumsum() == 1)                # günde bir
        s = p["stop_k"] * ort
        return _kur(m, pd.Series(ok, index=idx), pd.Series(False, index=idx), k - s, k + s, zaman=int(p["tut_mum"]))


# ============================================================================== 17. tuzak kırılım
class TuzakKirilim(Strateji):
    """dis__tuzak-kirilim (daytrade, 15m) — repo raporu 'Day trade — S13 Tuzak Kırılım'. (Benzer: daytrade__kirilim-geri-test; o kırılım
    sonrası geri test, burada kırılım ÖNCESİ geri çekilme sonrası tepenin yeniden aşılması.)
    Kural: n_tepe mumluk (15m'de 80 = 20 saat) yeni tepe T -> sonraki geri_max mum içinde mum dibi önceki n_dip (12) mumun dibine iner
    (geri çekilme) -> ardından donus_max (12) mum içinde KAPANIŞ T'nin üstüne çıkarsa long. Filtreler (mtf_filtre): 1h SMA10>20>50>100>200,
    4h EMA20>EMA50, 1h ADX14>adx_esik (25). Yalnız long. Stop = stop_gatr x günlük ATR(14); UTC gün sonu zorunlu çıkış.
    VARSAYIM: 'geri çekilme' için zaman sınırı geri_max=24 mum (kaynakta yok)."""
    ad = "dis__tuzak-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {"n_tepe": 80, "n_dip": 12, "geri_max": 24, "donus_max": 12, "mtf_filtre": True, "adx_esik": 25.0,
                               "stop_gatr": 1.0, "atr_periyot": 14}
    parametre_izgarasi = {"n_tepe": [40, 80, 120], "n_dip": [6, 12, 24], "stop_gatr": [0.75, 1.0, 1.5]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        ham = pd.Series(tuzak_durumu(y.to_numpy(), d.to_numpy(), k.to_numpy(), int(p["n_tepe"]), int(p["n_dip"]),
                                    int(p["geri_max"]), int(p["donus_max"])), index=idx)
        gatr = ust_zaman(m, "1d", lambda u: pd.DataFrame({"a": g.atr(u["yuksek"], u["dusuk"], u["kapanis"], int(p["atr_periyot"]))}))["a"].reindex(idx)
        ok = ham & gatr.notna()
        if p["mtf_filtre"]:
            def f1(u):
                kk = u["kapanis"]
                s10, s20, s50, s100, s200 = (g.sma(kk, n) for n in (10, 20, 50, 100, 200))
                dizi = (s10 > s20) & (s20 > s50) & (s50 > s100) & (s100 > s200)
                return pd.DataFrame({"dizi": dizi.astype(float), "adx": g.adx(u["yuksek"], u["dusuk"], kk, 14)["adx"]})

            def f4(u):
                return pd.DataFrame({"t": (g.ema(u["kapanis"], 20) > g.ema(u["kapanis"], 50)).astype(float)})

            u1 = ust_zaman(m, "1h", f1).reindex(idx)
            u4 = ust_zaman(m, "4h", f4).reindex(idx)
            ok &= (u1["dizi"] == 1.0) & (u4["t"] == 1.0) & (u1["adx"] > p["adx_esik"])
        s = p["stop_gatr"] * gatr
        return _kur(m, ok, pd.Series(False, index=idx), k - s, k + s, gun_sonu=True, seans_saat=0.0)


# ============================================================================== 18-19. Voltran 2A / 2B
def _voltran_htf(m, htf_mod=0, st_n=10, st_k=2.5, ema_n=21, tol=0.985):
    """1D ve 4H: Supertrend(10,2.5) yükseliş VEYA kapanış >= EMA21 x 0.985. htf_mod 0: ikisi birden, 1: yalnız 4h, 2: yalnız 1d."""
    def f(u):
        st = g.supertrend(u["yuksek"], u["dusuk"], u["kapanis"], st_n, st_k)["yon"]
        return pd.DataFrame({"b": ((st == 1) | (u["kapanis"] >= g.ema(u["kapanis"], ema_n) * tol)).astype(float)})

    idx = m.index
    b4 = ust_zaman(m, "4h", f)["b"].reindex(idx) == 1.0
    b1 = ust_zaman(m, "1d", f)["b"].reindex(idx) == 1.0
    return b4 & b1 if htf_mod == 0 else (b4 if htf_mod == 1 else b1)


class Voltran2A(Strateji):
    """dis__voltran-2a (daytrade, 1h; 1D/4H yön) — rapor sentezi VOLTRAN-2A (veri/pdf_metin_2/rapor/Voltran_4_Super_Strateji_...,
    Strateji_Al_Sat_Kriterleri.txt). Saatlik Adaptif Kanal (TOTT/OTT) + seans kırılımı.
    Yön filtresi: htf_mod (0: 1D VE 4H her ikisi; VARSAYIM 'VE'): Supertrend(10, 2.5) yükselişte VEYA kapanış >= EMA21 x 0.985.
    1H skor (0-105): OTT(VAR(14), %1.35) boğa (VAR > OTT çizgisi) +35; kapanış son kirilim_n (10) mumun tepesini (önceki mumlar) x 0.992
    kırar +25; ADX14 > 15 +20; kapanış > EMA34 +15; hacim >= SMA20 x 0.95 +10. Skor >= skor_esik (70) VE +DI >= 0.95 x -DI -> long
    (yalnız long; skorun ilk sağlandığı mumda).
    Çıkış: OTT negatif VE kapanış < EMA34; 3.2 ATR iz süren stop; kâr kilidi: +0.95 ATR (~0.30R, 3.2 ATR stopa göre) kârda stop girişe çekilir
    (CikisAyarlari.basabas_r_esigi; kaynaktaki 'başabaş + %0.5' için %0.5 ek motorda yok — girişe çekilir, VARSAYIM)."""
    ad = "dis__voltran-2a"
    stil = "daytrade"
    varsayilan_parametreler = {"htf_mod": 0, "ott_n": 14, "ott_yuzde": 1.35, "kirilim_n": 10, "kirilim_k": 0.992, "skor_esik": 70,
                               "adx_esik": 15.0, "hacim_k": 0.95, "stop_atr_k": 3.2, "atr_periyot": 14}
    parametre_izgarasi = {"skor_esik": [60, 70, 80], "ott_yuzde": [1.0, 1.35, 2.0], "kirilim_n": [6, 10, 20]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.2, basabas_r_esigi=0.3)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, v = m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        var = var_ma(k, int(p["ott_n"]))
        hat = ott(var, float(p["ott_yuzde"]))
        ott_boga = var > hat
        ema34 = g.ema(k, 34)
        adx = g.adx(y, d, k, 14)
        n = int(p["kirilim_n"])
        kirilim = k > y.shift(1).rolling(n, min_periods=n).max() * p["kirilim_k"]
        hacim_ok = v >= v.rolling(20, min_periods=20).mean() * p["hacim_k"]
        skor = (35 * ott_boga.astype(int) + 25 * kirilim.astype(int) + 20 * (adx["adx"] > p["adx_esik"]).astype(int)
                + 15 * (k > ema34).astype(int) + 10 * hacim_ok.astype(int))
        kosul = ((skor >= p["skor_esik"]) & (adx["arti_di"] >= 0.95 * adx["eksi_di"]) & _voltran_htf(m, int(p["htf_mod"]))
                 & hat.notna() & adx["adx"].notna() & a.notna())
        s = p["stop_atr_k"] * a
        return _kur(m, _ilk_an(kosul), pd.Series(False, index=idx), k - s, k + s, cikis_long=(~ott_boga & (k < ema34)))


class Voltran2B(Strateji):
    """dis__voltran-2b (daytrade, 1h; 1D/4H yön) — rapor sentezi VOLTRAN-2B: Saatlik Momentum Şeridi & Likidite Dönüş Motoru
    (Voltran_4_Super_Strateji_..., Strateji_Al_Sat_Kriterleri.txt).
    Yön filtresi: 2A ile aynı (htf_mod; VARSAYIM: kaynak '1G/4S trendi boğa' diyor, Supertrend(10,2.5) veya EMA21 x 0.985 olarak ölçüldü).
    1H long: EMA13 > EMA34 x 0.998 ve kapanış > EMA34; Stokastik(14,3,3) K >= D x 0.98, K > stoch_alt (35) ve RSI14 > rsi_alt (48);
    mum yeşil kapanır (kapanış > açılış) YA DA son sweep_n (8) mumun en düşüğünü (önceki mumlar) test edip (dip <= o seviye) üstünde kapanır
    (likidite süpürmesi). Yalnız long; koşulun ilk sağlandığı mumda.
    Çıkış: EMA13 < EMA34 x 0.995 VE RSI14 < 45; 3.2 ATR iz süren stop; kâr kilidi +0.95 ATR (~0.30R) -> stop girişe (bkz. Voltran2A)."""
    ad = "dis__voltran-2b"
    stil = "daytrade"
    varsayilan_parametreler = {"htf_mod": 0, "stoch_alt": 35.0, "rsi_alt": 48.0, "sweep_n": 8, "stop_atr_k": 3.2, "atr_periyot": 14}
    parametre_izgarasi = {"stoch_alt": [30.0, 35.0, 40.0], "rsi_alt": [45.0, 48.0, 52.0], "sweep_n": [5, 8, 12]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.2, basabas_r_esigi=0.3)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        idx = m.index
        y, d, k, o = m["yuksek"], m["dusuk"], m["kapanis"], m["acilis"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        e13, e34 = g.ema(k, 13), g.ema(k, 34)
        ham = g.stokastik(y, d, k, 14, 3)["d"]                 # yavaş K = ham %K'nın 3'lük SMA'sı
        sk = ham
        sd = g.sma(sk, 3)
        rsi = g.rsi(k, 14)
        n = int(p["sweep_n"])
        dip = d.shift(1).rolling(n, min_periods=n).min()
        sweep = (d <= dip) & (k > dip)
        kosul = ((e13 > e34 * 0.998) & (k > e34) & (sk >= sd * 0.98) & (sk > p["stoch_alt"]) & (rsi > p["rsi_alt"])
                 & ((k > o) | sweep) & _voltran_htf(m, int(p["htf_mod"])) & a.notna() & sd.notna())
        s = p["stop_atr_k"] * a
        return _kur(m, _ilk_an(kosul), pd.Series(False, index=idx), k - s, k + s, cikis_long=((e13 < e34 * 0.995) & (rsi < 45)))
