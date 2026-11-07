"""D10-C — kodlama kuyruğundaki (stratejiler/ek_kaynaklar/kodlama_kuyrugu_2026-11-07.csv) yeni aile satırlarından C grubu:
19 aile. KOD KOPYALANMADI: kitap kartları (veri/kartlar_ham) ve repo özetleri VERİDİR; kurallar kendi yapımızla yazıldı.
Ad öneki `dis__`. Hepsi nedensel (lookahead yok): sinyal mum kapanışında, dolum sonraki açılışta (motor).

Ortak uyarlamalar
  * Kartta kısa (short) kuralı yoksa short = ayna (VARSAYIM); `yonler` ile kapatılabilir.
  * Stop/hedef kartta yoksa: stop = yapısal seviye ya da `stop_atr_k` x ATR; hedef = `hedef_r` x risk (VARSAYIM, docstring'te belirtilir).
  * Seans = `seans_saat` (UTC) anında başlayan 24 saatlik dilim (varsayılan UTC gün; ABD hisse için 13.5/14.5, BIST için 7.0).
    "Önceki kapanış / günlük çubuk" = bir önceki tamamlanmış seans. 7/24 kriptoda "açılış/gap" anlamı yapaydır.
  * Kartlardaki puan/tik cinsinden mutlak değerler ATR katına çevrildi (evren stratejisi: enstrümandan bağımsız).
  * Yasak: martingale, DCA, ortalama düşürme, ızgara yok. Hepsinin stopu var.

Aileler (dis__ öneki): zaman-kirilimi, ma-tipli-kesisim, acilis-yanlilik-geri-cekilme, aroon-rsi-sma, brooks-h2,
cpr-camarilla-kirilim, pmax-giris, rudd-gunluk-kurulum-5dk-kirilim, brooks-ma-bosluk, gap-onceki-kapanis-tepki,
hacim-patlama-kirilimi, ma-kanali-momentum, osilator-macd-donus, qqe-giris, vwap-reclaim, 3gun-momentum-acilis-hacmi,
bist-uclu-sistem-oyu, bollinger-2-3-sd-bolgesi, dar-gun-acilis-kirilimi.
KODLANMAYAN: yeni__halsey-olculu-hareket (kurala_dokulemez: ölçülü hareketin çapası "görsel", kartta sayısal çapa yok).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import seans_kimligi
from motor.strateji.dis._gosterge_d1 import smma
from motor.strateji.dis._gosterge_d10c import (
    D10Taban, ORTAK, aroon, h_say, ilk_olay, pmax, qqe, seans_ozet, seans_sira, seansa_esle, vwma)
from motor.strateji.gostergeler_b2 import asagi_kesis, gecis, yukari_kesis


def _son_n(kosul: pd.Series, n: int) -> pd.Series:
    """Koşul son n mumdan (bu mum dahil) en az birinde True."""
    return kosul.fillna(False).astype(float).rolling(int(n), min_periods=1).max().astype(bool)


def _sid(m, p):
    return seans_kimligi(m.index, float(p["seans_saat"]))


# ================================================================== 1. zaman kırılımı
class ZamanKirilimi(D10Taban):
    """dis__zaman-kirilimi (daytrade, 5m) — Carter "5 dk sistem 7 saatlik kutu" + D'Errico "zaman kırılımı" (SR_Time).
    Kural: günün `saat` (UTC) anında, o andan önceki `geri_n` mumun yüksek/düşük kutusu çizilir. Kutu tepesinin
    `giris_pay` x kutu yüksekliği kadar üstünde kapanış (short: dibinin altında) -> kırılım yönünde giriş; yalnız ilk
    `pencere_mum` mum içinde ve seansta bir kez. Stop = kutunun karşı ucu (`stop_modu`="kutu", Carter) ya da `stop_atr_k` x
    ATR ("atr", D'Errico 2xATR). Hedef = hedef_r x risk (Carter kutunun %400'ü; D'Errico 3R -> varsayılan 3R).
    Kart: carter 08:00 EST, derrico SR_Time; saat enstrümana göre ayarlanır (VARSAYIM: 8.0 UTC). Gün sonu çıkışı."""
    ad = "dis__zaman-kirilimi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "saat": 8.0, "geri_n": 12, "pencere_mum": 12, "giris_pay": 0.2,
                               "stop_modu": "kutu", "hedef_r": 3.0}
    parametre_izgarasi = {"geri_n": [6, 12, 24], "giris_pay": [0.0, 0.2, 0.5], "hedef_r": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        idx = m.index
        tod = pd.Series((idx.hour + idx.minute / 60.0).to_numpy(float), index=idx)
        rel = (tod - float(p["seans_saat"])) % 24.0
        hedef_rel = (float(p["saat"]) - float(p["seans_saat"])) % 24.0
        gecti = (rel >= hedef_rel)
        sira = gecti.astype(int).groupby(sid).cumsum()
        n = int(p["geri_n"])
        hh = m["yuksek"].rolling(n, min_periods=n).max().shift(1)
        ll = m["dusuk"].rolling(n, min_periods=n).min().shift(1)
        bas = sira == 1
        kh = hh.where(bas).groupby(sid).transform("first").where(sira >= 1)
        kl = ll.where(bas).groupby(sid).transform("first").where(sira >= 1)
        yuk = kh - kl
        pen = (sira >= 1) & (sira <= int(p["pencere_mum"]))
        k = m["kapanis"]
        lc = pen & (k > kh + p["giris_pay"] * yuk)
        sc = pen & (k < kl - p["giris_pay"] * yuk)
        ilk = ilk_olay(lc | sc, sid)
        out = {"long": lc & ilk, "short": sc & ilk & ~lc}
        if p["stop_modu"] == "kutu":
            out["stop_l"], out["stop_s"] = kl, kh
        return out


# ================================================================== 2. MA tipli kesişim
class MaTipliKesisim(D10Taban):
    """dis__ma-tipli-kesisim (daytrade, 5m) — Ratford "SMMA 4/9 + SMA15" ve "VWMA 8/30" kesişimleri.
    tip="smma": SMMA(hizli=4) SMMA(yavas=9)'u son `kes_n` mumda yukarı kesti, mum SMMA4'e dokundu (düşük <= SMMA4) ve SMMA4
    üstünde kapandı, kapanış > SMA(filtre_n=15) -> long. Stop: giriş mumunun düşüğü - tampon_atr x ATR. Çıkış: SMMA4 < SMMA9
    ya da kapanış < SMA15.
    tip="vwma": VWMA(8) VWMA(30)'u son `kes_n` mumda yukarı kesti ve kapanış > VWMA30 -> long. Stop: son 10 mumun düşüğü -
    tampon. Çıkış: kapanış < VWMA30 (ya da VWMA8 < VWMA30). ATLANAN: SOTT süzgeci (kartta yön/eşik belirsiz).
    Short = ayna. Hedef yok (çıkış kuralı + stop; hedef_r=0). Gün sonu çıkışı kapalı."""
    ad = "dis__ma-tipli-kesisim"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "tip": "smma", "hizli": 4, "yavas": 9, "filtre_n": 15, "vwma_hizli": 8,
                               "vwma_yavas": 30, "kes_n": 3, "tampon_atr": 0.1, "salinim_n": 10, "hedef_r": 0.0,
                               "gun_sonu": 0}
    parametre_izgarasi = {"tip": ["smma", "vwma"], "kes_n": [1, 3, 5], "tampon_atr": [0.1, 0.3, 0.6]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        if p["tip"] == "smma":
            f, s, fl = smma(k, int(p["hizli"])), smma(k, int(p["yavas"])), g.sma(k, int(p["filtre_n"]))
            yk = _son_n((f > s) & (f.shift(1) <= s.shift(1)), p["kes_n"])
            ak = _son_n((f < s) & (f.shift(1) >= s.shift(1)), p["kes_n"])
            lg = yk & (f > s) & (d <= f) & (k > f) & (k > fl)
            sh = ak & (f < s) & (y >= f) & (k < f) & (k < fl)
            return {"long": lg, "short": sh & ~lg, "stop_l": d - tam, "stop_s": y + tam,
                    "cikis_long": (f < s) | (k < fl), "cikis_short": (f > s) | (k > fl)}
        f, s = vwma(k, m["hacim"], int(p["vwma_hizli"])), vwma(k, m["hacim"], int(p["vwma_yavas"]))
        yk = _son_n((f > s) & (f.shift(1) <= s.shift(1)), p["kes_n"])
        ak = _son_n((f < s) & (f.shift(1) >= s.shift(1)), p["kes_n"])
        lg = yk & (f > s) & (k > s)
        sh = ak & (f < s) & (k < s)
        n = int(p["salinim_n"])
        return {"long": lg, "short": sh & ~lg, "stop_l": d.rolling(n, min_periods=n).min() - tam,
                "stop_s": y.rolling(n, min_periods=n).max() + tam,
                "cikis_long": (k < s) | (f < s), "cikis_short": (k > s) | (f > s)}


# ================================================================== 3. açılış yanlılığı + geri çekilme
class AcilisYanlilikGeriCekilme(D10Taban):
    """dis__acilis-yanlilik-geri-cekilme (daytrade, 2m-5m) — Bennett "açılış yanlılığı + geri çekilme sonrası kırılım".
    Kural: seansın ilk mumu yükseliş (kapanış>açılış) ise yanlılık YUKARI, düşüş ise AŞAĞI; mum doji ise (gövde <= doji_oran x
    aralık) ikinci mum yanlılığı belirler (o da doji ise o gün işlem yok). Yanlılık yukarıysa: seans zirvesi A oluşur, ardından
    en az `geri_n` ardışık mum A'yı aşamadan geçerse (geçerli geri çekilme) ve bir mum kapanışta A'yı aşarsa -> long (seansın ilk
    kırılımı; kırılım yoksa işlem yok). Aşağı yanlılıkta ayna. Stop = geri çekilmenin ucu (long: geri çekilmenin en düşüğü).
    Hedef = hedef_r x risk (kartta yok: VARSAYIM 2R). Gün sonu çıkışı. "Bir tik geçince" -> kapanışla geçiş; iç mum istisnası
    kodlanmadı."""
    ad = "dis__acilis-yanlilik-geri-cekilme"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "geri_n": 2, "doji_oran": 0.15, "hedef_r": 2.0}
    parametre_izgarasi = {"geri_n": [1, 2, 3], "doji_oran": [0.1, 0.2, 0.3], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        o, h, l, c = (m[x].to_numpy(float) for x in ("acilis", "yuksek", "dusuk", "kapanis"))
        n = len(c)
        lg, sh = np.zeros(n, bool), np.zeros(n, bool)
        sl, ss = np.full(n, np.nan), np.full(n, np.nan)
        gn, dj = int(p["geri_n"]), float(p["doji_oran"])
        bas = 0
        for i in range(n):
            if i == 0 or sid[i] != sid[i - 1]:
                bas, yon, hazir, bitti = i, 0, False, False
                sh_, sl_, cnt_u, cnt_d, pb_lo, pb_hi = -np.inf, np.inf, 0, 0, np.inf, -np.inf
            gi = i - bas
            if not hazir:
                aralik = h[i] - l[i]
                govde = c[i] - o[i]
                if aralik > 0 and abs(govde) > dj * aralik:
                    yon, hazir = (1 if govde > 0 else -1), True
                elif gi >= 1:
                    hazir = True      # ikinci mum da doji -> yon 0 (işlem yok)
                sh_, sl_ = max(sh_, h[i]), min(sl_, l[i])
                continue
            if yon == 1 and not bitti:
                if c[i] > sh_ and cnt_u >= gn:
                    lg[i], sl[i], bitti = True, min(pb_lo, l[i]), True
                if h[i] > sh_:
                    cnt_u, pb_lo = 0, np.inf
                else:
                    cnt_u += 1
                    pb_lo = min(pb_lo, l[i])
            elif yon == -1 and not bitti:
                if c[i] < sl_ and cnt_d >= gn:
                    sh[i], ss[i], bitti = True, max(pb_hi, h[i]), True
                if l[i] < sl_:
                    cnt_d, pb_hi = 0, -np.inf
                else:
                    cnt_d += 1
                    pb_hi = max(pb_hi, h[i])
            sh_, sl_ = max(sh_, h[i]), min(sl_, l[i])
        ix = m.index
        return {"long": pd.Series(lg, ix), "short": pd.Series(sh, ix), "stop_l": pd.Series(sl, ix),
                "stop_s": pd.Series(ss, ix)}


# ================================================================== 4. Aroon + RSI + SMA
class AroonRsiSma(D10Taban):
    """dis__aroon-rsi-sma (daytrade, 5m) — Ratford "Aroon + RSI14 + SMA10".
    Long: RSI(14) > 50, kapanış > SMA(10) ve Aroon Up, Aroon Down'u son `kes_n` mumda yukarı kesti. Çıkış: kapanış < SMA10 YA DA
    Aroon Up 80'in altına geçti (yukarıdan aşağı kesişim). Short = ayna (RSI<50, kapanış<SMA, Aroon Down yukarı keser, çıkış:
    kapanış > SMA ya da Aroon Down 80 altına geçer). Stop kartta yok: VARSAYIM `stop_atr_k` x ATR (2). Hedef yok (çıkış kuralı)."""
    ad = "dis__aroon-rsi-sma"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "aroon_n": 25, "rsi_n": 14, "sma_n": 10, "kes_n": 3, "cikis_esik": 80.0,
                               "hedef_r": 0.0, "gun_sonu": 0}
    parametre_izgarasi = {"aroon_n": [14, 25, 40], "kes_n": [1, 3, 5], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ar = aroon(m["yuksek"], m["dusuk"], int(p["aroon_n"]))
        r = g.rsi(k, int(p["rsi_n"]))
        s = g.sma(k, int(p["sma_n"]))
        up_k = _son_n(yukari_kesis(ar["up"], ar["down"]), p["kes_n"])
        dn_k = _son_n(yukari_kesis(ar["down"], ar["up"]), p["kes_n"])
        e = float(p["cikis_esik"])
        return {"long": up_k & (r > 50) & (k > s), "short": dn_k & (r < 50) & (k < s),
                "cikis_long": (k < s) | asagi_kesis(ar["up"], e),
                "cikis_short": (k > s) | asagi_kesis(ar["down"], e)}


# ================================================================== 5. Brooks H2 / L2
class BrooksH2(D10Taban):
    """dis__brooks-h2 (daytrade, 5m) — Brooks "Yüksek 2 / Düşük 2" (iki ayaklı geri çekilme sonu, trend yönünde giriş).
    Tanım (ölçülebilir): yükseliş trendi = kapanış > EMA(ema_n) ve EMA, `egim_n` mum önceye göre yukarı. Geri çekilme =
    bir mum önceki yüksekten düşük/eşit yüksekle biten en az bir mum. Geri çekilmeden sonra, bir önceki mumun yükseğini
    aşan `sayi`'inci mum (H1: sayi=1, H2: sayi=2) sinyal mumudur; geri çekilmeden önceki tepe aşılırsa sayaç sıfırlanır
    (yeni yüksek = geri çekilme bitti). Giriş sinyal mumu kapanışında (Brooks buy-stop yerine). Stop = geri çekilmenin en
    düşüğü ("doğru swing stop", kartta sayısal yok). Hedef = hedef_r x risk (VARSAYIM 2R; kartta yok; "ölçülü hareket"
    hedefi kodlanmadı). Short = L2 aynası (düşüş trendi). Aralık içi/başarısız kurulum varyantları kodlanmadı."""
    ad = "dis__brooks-h2"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "ema_n": 20, "egim_n": 5, "sayi": 2, "hedef_r": 2.0, "tampon_atr": 0.1}
    parametre_izgarasi = {"sayi": [1, 2], "ema_n": [20, 50], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        e = g.ema(k, int(p["ema_n"]))
        egim = int(p["egim_n"])
        up = ((k > e) & (e > e.shift(egim))).to_numpy(bool)
        dn = ((k < e) & (e < e.shift(egim))).to_numpy(bool)
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        sl_, st_ = h_say(y.to_numpy(float), d.to_numpy(float), up, int(p["sayi"]))
        ss_, st2 = h_say(-d.to_numpy(float), -y.to_numpy(float), dn, int(p["sayi"]))
        ix = m.index
        return {"long": pd.Series(sl_, ix), "short": pd.Series(ss_, ix),
                "stop_l": pd.Series(st_, ix) - tam, "stop_s": -pd.Series(st2, ix) + tam}


# ================================================================== 6. CPR + Camarilla
class CprCamarillaKirilim(D10Taban):
    """dis__cpr-camarilla-kirilim (daytrade, 5m) — TranquilTrader CPR + Camarilla (içten çıkış / merdiven kırılımı).
    Önceki seansın H,L,C'sinden: Pivot=(H+L+C)/3, BC=(H+L)/2, TC=2P-BC; CPR = [min(TC,BC), max(TC,BC)]; Camarilla H3=C+0.275R,
    H4=C+0.55R, L3=C-0.275R, L4=C-0.55R (R=H-L). "Dar CPR" = |TC-BC| <= dar_oran x R (ölçülebilir tanım; dunden_dar=1 ise
    ayrıca dünkü CPR genişliğinden küçük). kurulum="icten": H3<dünkü H3 ve L3>dünkü L3 (daralan Camarilla), H4 dünkü CPR'nin
    altında değil. kurulum="merdiven": CPR dünkünün tamamen üstünde ve H3,H4,L3,L4 dünkünden yüksek.
    Sinyal mumu A = H4 üstünde ilk kapanış; kırılım mumu B = A'dan sonraki en çok `bekle_n` mum içinde kapanışı A'nın yükseğinin
    (icten: ve dünkü CPR üstünün) üzerinde, hacmi A'dan büyük (hacim_sart=1). Giriş B kapanışında. Stop = A'nın dibi ile
    dinlenme mumlarının dibinden YÜKSEK olan (kart). Çıkış (kart): %70 pozisyon 1R'de, kalan 2R'de (CikisAyarlari). Kart yalnız
    long; short = ayna (L4 altı, vb.). Haftalık CPR filtresi atlandı. olusturma/vurus kartları bu iki kurulumun gevşek
    varyantı: ayrıca kodlanmadı. Gün sonu çıkışı."""
    ad = "dis__cpr-camarilla-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "kurulum": "icten", "dar_oran": 0.1, "dunden_dar": 1, "bekle_n": 2,
                               "hacim_sart": 1, "tampon_atr": 0.1, "hedef_r": 0.0}
    parametre_izgarasi = {"kurulum": ["icten", "merdiven"], "dar_oran": [0.05, 0.1, 0.2], "bekle_n": [1, 2, 3]}
    cikis_ayarlari = CikisAyarlari(sabit_r_hedefi=2.0, kismi=((1.0, 0.7),))

    @staticmethod
    def _seviyeler(t):
        h, l, c = t["h"], t["l"], t["c"]
        pv = (h + l + c) / 3.0
        bc = (h + l) / 2.0
        tc = 2 * pv - bc
        r = h - l
        return {"ust": np.maximum(tc, bc), "alt": np.minimum(tc, bc), "gen": (tc - bc).abs(), "r": r,
                "h3": c + 0.275 * r, "h4": c + 0.55 * r, "l3": c - 0.275 * r, "l4": c - 0.55 * r}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        ix = m.index
        oz = seans_ozet(m, sid)
        bu = self._seviyeler(seansa_esle(oz, sid, ix, 1))
        dn = self._seviyeler(seansa_esle(oz, sid, ix, 2))
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        dar = bu["gen"] <= p["dar_oran"] * bu["r"]
        if p["dunden_dar"]:
            dar &= bu["gen"] < dn["gen"]
        if p["kurulum"] == "icten":
            ok_l = dar & (bu["h3"] < dn["h3"]) & (bu["l3"] > dn["l3"]) & (bu["h4"] >= dn["alt"])
            ok_s = dar & (bu["h3"] < dn["h3"]) & (bu["l3"] > dn["l3"]) & (bu["l4"] <= dn["ust"])
        else:
            ok_l = dar & (bu["alt"] > dn["ust"]) & (bu["h3"] > dn["h3"]) & (bu["h4"] > dn["h4"]) \
                & (bu["l3"] > dn["l3"]) & (bu["l4"] > dn["l4"])
            ok_s = dar & (bu["ust"] < dn["alt"]) & (bu["h3"] < dn["h3"]) & (bu["h4"] < dn["h4"]) \
                & (bu["l3"] < dn["l3"]) & (bu["l4"] < dn["l4"])
        a_l = ok_l & (k > bu["h4"]) & (k.shift(1) <= bu["h4"])
        a_s = ok_s & (k < bu["l4"]) & (k.shift(1) >= bu["l4"])
        sidp = pd.Series(sid, index=ix)
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        lg = pd.Series(False, index=ix)
        sh = pd.Series(False, index=ix)
        sl = pd.Series(np.nan, index=ix)
        ss = pd.Series(np.nan, index=ix)
        for lag in range(1, int(p["bekle_n"]) + 1):
            ayni = sidp.shift(lag) == sidp
            hv_l = (v > v.shift(lag)) if p["hacim_sart"] else True
            rest_lo = d.shift(1)
            rest_hi = y.shift(1)
            for j in range(2, lag):
                rest_lo = np.minimum(rest_lo, d.shift(j))
                rest_hi = np.maximum(rest_hi, y.shift(j))
            ust_ok = (k > dn["ust"]) if p["kurulum"] == "icten" else True
            alt_ok = (k < dn["alt"]) if p["kurulum"] == "icten" else True
            c_l = a_l.shift(lag, fill_value=False) & ayni & (k > y.shift(lag)) & ust_ok & hv_l & ~lg
            c_s = a_s.shift(lag, fill_value=False) & ayni & (k < d.shift(lag)) & alt_ok & hv_l & ~sh
            st_l = d.shift(lag) if lag == 1 else np.maximum(d.shift(lag), rest_lo)
            st_s = y.shift(lag) if lag == 1 else np.minimum(y.shift(lag), rest_hi)
            sl = sl.where(~c_l, st_l - tam)
            ss = ss.where(~c_s, st_s + tam)
            lg |= c_l
            sh |= c_s
        ilk_l, ilk_s = ilk_olay(lg, sid), ilk_olay(sh, sid)
        return {"long": lg & ilk_l, "short": sh & ilk_s & ~lg, "stop_l": sl, "stop_s": ss}


# ================================================================== 7. PMax
class PmaxGiris(D10Taban):
    """dis__pmax-giris (daytrade, 5m/1h) — Ratford "RSI5 + PMax" ve repo "4H Sweet Spot PMax & ADX" (aynı TF'de uyarlandı).
    PMax: MA = EMA((H+L)/2, ma_n) etrafında carpan x ATR(10) yapışkan bant; yeşil = alt bant çizgisi (yukarı trend).
    mod="rsi": PMax yeşil + kapanış PMax çizgisi üstünde + RSI(5) 30'u yukarı keser -> long (short: kırmızı, 70'i aşağı keser).
    mod="donus": PMax kırmızıdan yeşile döner + ADX(14) >= adx_esik ve +DI>-DI + "testere süzgeci" ATR14/SMA(ATR14,40) >
    testere_esik (repo) -> long; short ayna. Stop = PMax çizgisi (VARSAYIM; kartta stop yok). Çıkış: PMax rengi karşıya döner
    ya da kapanış çizginin ötesine geçer. Hedef yok. ATLANAN: PMax+NSM (VAR ortalama + normalleştirilmiş yumuşatılmış MACD:
    tanımı kartta yok), 1D/4H çok zaman dilimli hizalama (kısmen: tek TF)."""
    ad = "dis__pmax-giris"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "mod": "rsi", "ma_n": 10, "pmax_atr_n": 10, "carpan": 2.7, "rsi_n": 5,
                               "rsi_esik": 30.0, "adx_esik": 18.0, "testere_esik": 0.85, "hedef_r": 0.0, "gun_sonu": 0}
    parametre_izgarasi = {"mod": ["rsi", "donus"], "carpan": [2.0, 2.7, 3.6], "ma_n": [8, 10, 14]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        pm = pmax(y, d, k, int(p["ma_n"]), int(p["pmax_atr_n"]), float(p["carpan"]))
        yon, cz = pm["yon"], pm["cizgi"]
        yesil, kirmizi = (yon == 1) & (k > cz), (yon == -1) & (k < cz)
        if p["mod"] == "rsi":
            r = g.rsi(k, int(p["rsi_n"]))
            lg = yesil & yukari_kesis(r, float(p["rsi_esik"]))
            sh = kirmizi & asagi_kesis(r, 100.0 - float(p["rsi_esik"]))
        else:
            ad_ = g.adx(y, d, k, 14)
            a = g.atr(y, d, k, 14)
            testere = (a / g.sma(a, 40)) > p["testere_esik"]
            guc = (ad_["adx"] >= p["adx_esik"]) & testere
            lg = (yon == 1) & (yon.shift(1) == -1) & guc & (ad_["arti_di"] > ad_["eksi_di"]) & (k > cz)
            sh = (yon == -1) & (yon.shift(1) == 1) & guc & (ad_["eksi_di"] > ad_["arti_di"]) & (k < cz)
        return {"long": lg, "short": sh, "stop_l": cz, "stop_s": cz,
                "cikis_long": (yon == -1) | (k < cz), "cikis_short": (yon == 1) | (k > cz)}


# ================================================================== 8. Rudd günlük kurulum
class RuddGunlukKurulum(D10Taban):
    """dis__rudd-gunluk-kurulum-5dk-kirilim (daytrade, 5m) — Rudd günlük çubuk kurulumu + gün içi konsolidasyon kırılımı.
    kurulum="donus" (üç günlük dönüş): çubuk1 = 2 seans önce, çubuk2 = dünkü seans. Long: çubuk1 aralığının alt `alt_oran`
    kısmında kapanmış; çubuk2'nin yükseği çubuk1 dibinin `yakin_oran` x aralık üstünden fazla değil ve çubuk2 yüksek-yakın
    (üst `ust_kapanis` kısmında) kapanmış; çubuk1 yükseği - çubuk2 kapanışı >= alan_atr x ATR (kâr alanı); bugünkü açılış
    çubuk2 kapanışına `acilis_tol` x çubuk1 aralığı kadar yakın. Giriş: bugün, son `pencere_n` mumun yükseğinin üstünde ilk
    kapanış (5m konsolidasyon kırılımı). Hedef = çubuk1 yükseği; stop = son pencere_n mumun dibi - tampon. Short ayna.
    kurulum="flashback" (sabah dönüşü): seansın ilk `pencere_n` mumu içinde, açılıştan `sahte_atr` x ATR kadar aşağı sahte
    hareket olduktan sonra kapanış o ana dek seans zirvesini aşarsa ve zirve-dip mesafesi <= mesafe_atr x ATR ise long (ilk
    kırılım); stop seans dibi; hedef hedef_r x risk. Short ayna. ATLANAN: piyasa endeksi teyidi, wiggle iz süren stop (ATR/R
    çıkışı ile yaklaşıldı), "geniş aralık günü" süzgeci (kartta eşik yok), 4 çubuklu varyant. Gün sonu çıkışı."""
    ad = "dis__rudd-gunluk-kurulum-5dk-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "kurulum": "donus", "alt_oran": 0.35, "yakin_oran": 0.35, "ust_kapanis": 0.25,
                               "alan_atr": 0.5, "acilis_tol": 0.25, "pencere_n": 4, "tampon_atr": 0.1,
                               "sahte_atr": 0.3, "mesafe_atr": 2.0, "hedef_r": 2.0}
    parametre_izgarasi = {"kurulum": ["donus", "flashback"], "pencere_n": [3, 4, 6], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        ix = m.index
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        sira = seans_sira(sid, ix)
        n = int(p["pencere_n"])
        if p["kurulum"] == "donus":
            oz = seans_ozet(m, sid)
            b1, b2 = seansa_esle(oz, sid, ix, 2), seansa_esle(oz, sid, ix, 1)
            r1, r2 = b1["h"] - b1["l"], b2["h"] - b2["l"]
            ac = m["acilis"].groupby(sid).transform("first")
            yakin_ac = (ac - b2["c"]).abs() <= p["acilis_tol"] * r1
            ok_l = ((b1["c"] - b1["l"]) <= p["alt_oran"] * r1) & ((b2["h"] - b1["l"]) <= p["yakin_oran"] * r1) \
                & ((b2["h"] - b2["c"]) <= p["ust_kapanis"] * r2) & ((b1["h"] - b2["c"]) >= p["alan_atr"] * a) & yakin_ac
            ok_s = ((b1["h"] - b1["c"]) <= p["alt_oran"] * r1) & ((b1["h"] - b2["l"]) <= p["yakin_oran"] * r1) \
                & ((b2["c"] - b2["l"]) <= p["ust_kapanis"] * r2) & ((b2["c"] - b1["l"]) >= p["alan_atr"] * a) & yakin_ac
            ph = y.rolling(n, min_periods=n).max().shift(1)
            pl = d.rolling(n, min_periods=n).min().shift(1)
            ic = sira >= n
            lg = ok_l & ic & (k > ph)
            sh = ok_s & ic & (k < pl)
            il = ilk_olay(lg | sh, sid)
            return {"long": lg & il, "short": sh & il & ~lg,
                    "stop_l": d.rolling(n, min_periods=n).min() - tam, "stop_s": y.rolling(n, min_periods=n).max() + tam,
                    "hedef_l": b1["h"], "hedef_s": b1["l"]}
        zirve = y.groupby(sid).cummax().groupby(sid).shift(1)
        dip = d.groupby(sid).cummin().groupby(sid).shift(1)
        ac = m["acilis"].groupby(sid).transform("first")
        pen = (sira >= 1) & (sira < n)
        yakin = (zirve - dip) <= p["mesafe_atr"] * a
        lg = pen & ((ac - dip) >= p["sahte_atr"] * a) & (k > zirve) & yakin
        sh = pen & ((zirve - ac) >= p["sahte_atr"] * a) & (k < dip) & yakin
        il = ilk_olay(lg | sh, sid)
        return {"long": lg & il, "short": sh & il & ~lg, "stop_l": dip - tam, "stop_s": zirve + tam}


# ================================================================== 9. Brooks MA boşluğu
class BrooksMaBosluk(D10Taban):
    """dis__brooks-ma-bosluk (daytrade, 5m) — Brooks "20 boşluk çubuğu" ve "ilk hareketli ortalama boşluğu".
    mod="20gap": en az `bosluk_n` mum boyunca mumun düşüğü EMA(ma_n)'nin üstünde kaldı (MA'ya dokunmadı), sonra MA'ya İLK
    dokunuş mumu (düşük <= EMA) yükseliş dönüş mumu ise (kapanış > açılış ve kapanış > EMA) -> long (Brooks: dönüş mumunun
    üstüne buy-stop; burada kapanışta giriş). Short ayna (yüksek hep EMA altında, ilk dokunuşta ayı mumu). Stop = sinyal mumunun
    düşüğü - tampon (kart: 1 tik ötesi; sayısal değer yok -> ATR tamponu).
    mod="ilk-bosluk": güçlü yükseliş trendi (önceki `trend_n` mumun kapanışı EMA üstünde) sonrası mumun TAMAMEN EMA altında olduğu
    ilk boşluk mumu; ardından en çok `bekle_n` mum içinde kapanış bir önceki mumun yükseğini aşarsa long. Stop = boşluk
    mumu ve sonrası mumların dibi - tampon. Hedef = hedef_r x risk (VARSAYIM; kart: "trend ekstreminin testi" -> ATR/R)."""
    ad = "dis__brooks-ma-bosluk"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "mod": "20gap", "ma_n": 20, "bosluk_n": 20, "trend_n": 10, "bekle_n": 3,
                               "tampon_atr": 0.1, "hedef_r": 2.0}
    parametre_izgarasi = {"mod": ["20gap", "ilk-bosluk"], "bosluk_n": [15, 20, 30], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, o = m["kapanis"], m["yuksek"], m["dusuk"], m["acilis"]
        e = g.ema(k, int(p["ma_n"]))
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        if p["mod"] == "20gap":
            from motor.strateji.dis._gosterge_d9 import ardisik_say
            uz_u = ardisik_say(d > e).shift(1) >= p["bosluk_n"]
            uz_d = ardisik_say(y < e).shift(1) >= p["bosluk_n"]
            lg = uz_u & (d <= e) & (k > o) & (k > e)
            sh = uz_d & (y >= e) & (k < o) & (k < e)
            return {"long": lg, "short": sh & ~lg, "stop_l": d - tam, "stop_s": y + tam}
        tn = int(p["trend_n"])
        tr_u = (k > e).astype(float).rolling(tn, min_periods=tn).min().shift(1) == 1
        tr_d = (k < e).astype(float).rolling(tn, min_periods=tn).min().shift(1) == 1
        gb_u = tr_u & (y < e)
        gb_d = tr_d & (d > e)
        bn = int(p["bekle_n"])
        lg = pd.Series(False, index=m.index)
        sh = pd.Series(False, index=m.index)
        for lag in range(1, bn + 1):
            lg |= gb_u.shift(lag, fill_value=False) & (k > y.shift(1))
            sh |= gb_d.shift(lag, fill_value=False) & (k < d.shift(1))
        return {"long": lg, "short": sh & ~lg, "stop_l": d.rolling(bn + 1, min_periods=bn + 1).min() - tam,
                "stop_s": y.rolling(bn + 1, min_periods=bn + 1).max() + tam}


# ================================================================== 10. önceki kapanış tepkisi
class GapOncekiKapanisTepki(D10Taban):
    """dis__gap-onceki-kapanis-tepki (daytrade, 5m) — Denham "kırmızıdan yeşile: önceki kapanış" (+ Roy gap geri testi yalnız not).
    Cp = önceki tamamlanmış seansın kapanışı. Long: fiyat seansta Cp'nin altındaydı ("kırmızı"), bir mum kapanışı Cp'nin üstüne
    çıkar ve `tut_n` ardışık kapanış Cp üstünde kalır (tutunma) -> long (seansta ilk). Short: Cp üstünden aşağı geçiş ve altında
    tutunma. Stop = Cp -/+ tampon_atr x ATR (kart: önceki kapanışın diğer tarafı); hedef = hedef_r x risk (kart: destek/direnç,
    sayısal yok -> VARSAYIM 2R). Gün sonu çıkışı. KODLANMAYAN: Roy "gap geri testi" (düzeltme derinliği/süresi tanımsız, günlük
    mum yönü + Supertrend direnci). 7/24 kriptoda önceki kapanış ~ seans açılışı (UTC); anlam hisse/BIST seansıyla güçlüdür."""
    ad = "dis__gap-onceki-kapanis-tepki"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "tut_n": 2, "tampon_atr": 0.5, "hedef_r": 2.0}
    parametre_izgarasi = {"tut_n": [1, 2, 3], "tampon_atr": [0.3, 0.5, 1.0], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        ix = m.index
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        cp = seansa_esle(seans_ozet(m, sid), sid, ix, 1)["c"]
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        sira = seans_sira(sid, ix)
        tn = int(p["tut_n"])
        ust, alt = k > cp, k < cp
        gec_u = ust & ~ust.shift(1, fill_value=False) & (sira >= 1)
        gec_d = alt & ~alt.shift(1, fill_value=False) & (sira >= 1)
        tut_u = ust.astype(float).rolling(tn, min_periods=tn).min() == 1
        tut_d = alt.astype(float).rolling(tn, min_periods=tn).min() == 1
        lg = gec_u.shift(tn - 1, fill_value=False) & tut_u & (sira >= tn)
        sh = gec_d.shift(tn - 1, fill_value=False) & tut_d & (sira >= tn)
        il = ilk_olay(lg | sh, sid)
        tam = p["tampon_atr"] * a
        return {"long": lg & il, "short": sh & il & ~lg, "stop_l": cp - tam, "stop_s": cp + tam}


# ================================================================== 11. hacim patlaması kırılımı
class HacimPatlamaKirilimi(D10Taban):
    """dis__hacim-patlama-kirilimi (daytrade, 5m-10m) — Bernstein "hacim artışı sivri uç" + repo "Volume Spikes in Oil Futures".
    Hacim patlaması mumu = hacim >= hacim_k x referans (ref_tip="ortalama": SMA(hacim, ref_n) bir önceki mum dahil geçmiş;
    "onceki": önceki mumun hacmi — Bernstein ">= 4x önceki"). Patlama mumunun yüksek/düşüğü işaretlenir; sonraki
    `gecerlilik` mum içinde kapanış patlama mumunun yükseğinin üstüne çıkarsa long, düşüğünün altına inerse short (patlama
    başına ilk kırılım; seans içinde). Stop = patlama mumunun karşı ucu -/+ tampon (kart). Hedef = hedef_r x risk (VARSAYIM 2R;
    kart: seans sonunda iz süren; burada gün sonu çıkışı + R hedefi). Repo'nun "%10 kârda kapat, bar yönünde giriş, 6x/3x
    eşik" tarifi kapsanmadı (mutlak hacim + haftalık referans).
    d11j EK (varsayılan "spike_mum" = eski davranış; ızgaraya girmez): kirilim_ref="n_mum_zirve" -> NFI pump/dump ateşleme mumu: PATLAMA MUMUNUN
    KENDİSİNDE kapanış önceki `zirve_n` (48) mumun en yüksek yükseğini İLK kez yukarı keser (önceki kapanış seviyenin altında/eşit),
    mum yeşil ve gövde >= govde_yuzde % (0.2) ve kapanış mum aralığının üst yarısında -> long; ayna (önceki zirve_n mumun dibini aşağı
    kırma, kırmızı gövde, alt yarıda kapanış) -> short. Stop = patlama mumunun karşı ucu -/+ tampon. NFI'nin 24s getiri tavanı (<%8/%-10),
    günlük ROC ve bağıl hacim eşiğinin 4/3 farkı kodlanmadı (hacim_k tek eşik). Kaynak aile: hacim-patlamali-48-mum-zirve-kirilimi."""
    ad = "dis__hacim-patlama-kirilimi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "hacim_k": 3.0, "ref_tip": "ortalama", "ref_n": 20, "gecerlilik": 6,
                               "tampon_atr": 0.1, "hedef_r": 2.0,
                               "kirilim_ref": "spike_mum", "zirve_n": 48, "govde_yuzde": 0.2}
    parametre_izgarasi = {"hacim_k": [2.0, 3.0, 4.0], "gecerlilik": [3, 6, 12], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        if p["ref_tip"] == "onceki":
            ref = v.shift(1)
        else:
            ref = v.rolling(int(p["ref_n"]), min_periods=int(p["ref_n"])).mean().shift(1)
        spike = (ref > 0) & (v >= p["hacim_k"] * ref)
        if p["kirilim_ref"] == "n_mum_zirve":
            a_, n_ = m["acilis"], int(p["zirve_n"])
            zirve = y.rolling(n_, min_periods=n_).max().shift(1)
            dip = d.rolling(n_, min_periods=n_).min().shift(1)
            govde = (k - a_).abs() / a_ * 100.0 >= p["govde_yuzde"]
            orta = (y + d) / 2.0
            lg = spike & (k > zirve) & (k.shift(1) <= zirve) & (k > a_) & govde & (k >= orta)
            sh = spike & (k < dip) & (k.shift(1) >= dip) & (k < a_) & govde & (k <= orta) & ~lg
            tam = p["tampon_atr"] * g.atr(y, d, k, int(p["atr_periyot"]))
            return {"long": lg.fillna(False), "short": sh.fillna(False), "stop_l": d - tam, "stop_s": y + tam}
        if p["kirilim_ref"] != "spike_mum":
            raise ValueError(f"Bilinmeyen kirilim_ref: {p['kirilim_ref']}")
        lim = max(int(p["gecerlilik"]) - 1, 0)

        def seviye(x):
            return x.where(spike).shift(1).groupby(sid).ffill(limit=lim)

        sh_, sl_ = seviye(y), seviye(d)
        sid_spike = spike.cumsum()
        lg = k > sh_
        sh = (k < sl_) & ~lg
        il = (lg | sh).astype(int).groupby(sid_spike).cumsum() == 1
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        return {"long": lg & il, "short": sh & il, "stop_l": sl_ - tam, "stop_s": sh_ + tam}


# ================================================================== 12. MA kanalı + momentum
class MaKanaliMomentum(D10Taban):
    """dis__ma-kanali-momentum (daytrade, 30m-1h) — Bernstein "hareketli ortalama kanalı + momentum" (MAC) + repo S14_mac.
    Kanal: üst çizgi SMA(yüksek, ust_n=10), alt çizgi SMA(düşük, alt_n=8). Long: `iki_bar` (2) ardışık mum TAMAMEN üst
    çizginin üstünde (düşük > SMA yüksek) VE Momentum(mom_n=28) = kapanış - kapanış[mom_n önce], kendi SMA(mom_n)'sinin
    üstünde (onay) -> kanal ilk aşıldığında giriş. Short: iki mum tamamen alt çizginin altında, momentum SMA altında.
    Stop = karşı kanal çizgisi (kart/repo). Çıkış: kapanışın karşı kanal çizgisini geçmesi (long: kapanış < SMA(düşük)).
    gun_sonu=1: repo "gün sonu çık". Hedef yok (hedef_r=0). Momentum onayı 'durum' (kesişim değil)."""
    ad = "dis__ma-kanali-momentum"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "ust_n": 10, "alt_n": 8, "mom_n": 28, "iki_bar": 2, "hedef_r": 0.0,
                               "gun_sonu": 0}
    parametre_izgarasi = {"ust_n": [8, 10, 14], "mom_n": [14, 28], "gun_sonu": [0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        su, sa = g.sma(y, int(p["ust_n"])), g.sma(d, int(p["alt_n"]))
        mom = k - k.shift(int(p["mom_n"]))
        ms = g.sma(mom, int(p["mom_n"]))
        ik = int(p["iki_bar"])
        ust = (d > su).astype(float).rolling(ik, min_periods=ik).min() == 1
        alt = (y < sa).astype(float).rolling(ik, min_periods=ik).min() == 1
        lg = gecis(ust & (mom > ms))
        sh = gecis(alt & (mom < ms))
        return {"long": lg, "short": sh & ~lg, "stop_l": sa, "stop_s": su,
                "cikis_long": k < sa, "cikis_short": k > su}


# ================================================================== 13. osilatör + MACD dönüşü
class OsilatorMacdDonus(D10Taban):
    """dis__osilator-macd-donus (daytrade, 10m; kuyruk: daytrade/scalp -> ana stil daytrade) — Bortucene "zirve-dip dönüş"
    (RSI + yavaş stokastik + MACD) ve Ultimate Scalper "aşırı alım/satım + MACD dönüşü".
    mod="uc-teyit" (Bortucene): yavaş stokastik %K, %D'yi aşırı satımdan (önceki min(K,D) < stok_alt) yukarı keser; son
    `pencere` mumda RSI(14) rsi_alt altına inip şimdi yükseliyor; MACD histogramı yükseliyor -> long. Short ayna. Stop kartta
    sabit 15-20 pip: ATR (stop_atr_k) ile; hedef = hedef_r x risk (kart 5-20 pip).
    mod="macd-bukulme" (Ultimate Scalper): stokastik %K < stok_alt iken MACD histogramı İLK kez yukarı büküldü
    (hist > hist[-1] ve hist[-1] <= hist[-2]) -> long. Stop = son `salinim_n` mumun dibi - tampon ("en düşük fiyatın 1 tik altı");
    kartta hedef yok: VARSAYIM hedef_r. Short ayna. Gün sonu çıkışı yok."""
    ad = "dis__osilator-macd-donus"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "mod": "uc-teyit", "stok_n": 14, "stok_yav": 3, "stok_alt": 20.0,
                               "rsi_n": 14, "rsi_alt": 30.0, "pencere": 3, "salinim_n": 10, "tampon_atr": 0.1,
                               "hedef_r": 1.5, "gun_sonu": 0}
    parametre_izgarasi = {"mod": ["uc-teyit", "macd-bukulme"], "stok_alt": [20.0, 30.0], "hedef_r": [1.0, 1.5, 2.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        st = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        ks = st.rolling(int(p["stok_yav"]), min_periods=int(p["stok_yav"])).mean()
        ds = ks.rolling(int(p["stok_yav"]), min_periods=int(p["stok_yav"])).mean()
        hist = g.macd(k)["histogram"]
        alt, ust = float(p["stok_alt"]), 100.0 - float(p["stok_alt"])
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        if p["mod"] == "uc-teyit":
            r = g.rsi(k, int(p["rsi_n"]))
            pn = int(p["pencere"])
            kes_u = yukari_kesis(ks, ds) & (np.minimum(ks.shift(1), ds.shift(1)) < alt)
            kes_d = asagi_kesis(ks, ds) & (np.maximum(ks.shift(1), ds.shift(1)) > ust)
            rsi_u = (r.rolling(pn, min_periods=pn).min() < p["rsi_alt"]) & (r > r.shift(1))
            rsi_d = (r.rolling(pn, min_periods=pn).max() > 100.0 - p["rsi_alt"]) & (r < r.shift(1))
            return {"long": kes_u & rsi_u & (hist > hist.shift(1)), "short": kes_d & rsi_d & (hist < hist.shift(1))}
        n = int(p["salinim_n"])
        b_u = (hist > hist.shift(1)) & (hist.shift(1) <= hist.shift(2))
        b_d = (hist < hist.shift(1)) & (hist.shift(1) >= hist.shift(2))
        return {"long": (ks < alt) & b_u, "short": (ks > ust) & b_d,
                "stop_l": d.rolling(n, min_periods=n).min() - tam, "stop_s": y.rolling(n, min_periods=n).max() + tam}


# ================================================================== 14. QQE
class QqeGiris(D10Taban):
    """dis__qqe-giris (daytrade, 5m; kuyruk: daytrade/scalp -> ana stil daytrade) — Ratford "QQE + BB40" ve "DiDi + QQE + 12 SMA".
    QQE (klasik/Kıvanç): RsiMa = EMA(RSI(rsi_n), 5); yapışkan bantlar RsiMa -/+ 4.236 x çift EMA'lı |dRsiMa|; "al sinyali" =
    RsiMa üst bandı yukarı keser (yon -1/0 -> +1), "sat" = alt bandı aşağı keser.
    mod="bb": kapanış > Bollinger(bb_n=40, 1 SD) üst bandı ve QQE al sinyali son `kes_n` mumda -> long; çıkış: kapanış üst bandın
    altına iner ya da QQE sat. mod="didi": kapanış > SMA12, DiDi yeşil (SMA3/SMA8 > 1 > SMA20/SMA8; kart "DiDi histogramı yeşil"
    -> ölçülebilir VARSAYIM: kısa ortalama orta üstünde, uzun orta altında) ve QQE al -> long; çıkış: kapanış < SMA12 ya da
    QQE sat. Short ayna. Stop kartta yok: VARSAYIM stop_atr_k x ATR. Hedef yok (çıkış kuralı)."""
    ad = "dis__qqe-giris"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "mod": "bb", "rsi_n": 14, "sf": 5, "bb_n": 40, "bb_sd": 1.0, "sma_n": 12,
                               "kes_n": 3, "hedef_r": 0.0, "gun_sonu": 0}
    parametre_izgarasi = {"mod": ["bb", "didi"], "rsi_n": [10, 14], "stop_atr_k": [1.5, 2.5], "kes_n": [1, 3]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        q = qqe(k, int(p["rsi_n"]), int(p["sf"]))
        al = _son_n((q["yon"] == 1) & (q["yon"].shift(1) != 1), p["kes_n"])
        sat = _son_n((q["yon"] == -1) & (q["yon"].shift(1) != -1), p["kes_n"])
        if p["mod"] == "bb":
            bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_sd"]))
            return {"long": al & (k > bb["ust"]), "short": sat & (k < bb["alt"]),
                    "cikis_long": (k < bb["ust"]) | (q["yon"] == -1), "cikis_short": (k > bb["alt"]) | (q["yon"] == 1)}
        s8 = g.sma(k, 8)
        kisa, uzun = g.sma(k, 3) / s8, g.sma(k, 20) / s8
        sm = g.sma(k, int(p["sma_n"]))
        return {"long": al & (k > sm) & (kisa > 1) & (uzun < 1), "short": sat & (k < sm) & (kisa < 1) & (uzun > 1),
                "cikis_long": (k < sm) | (q["yon"] == -1), "cikis_short": (k > sm) | (q["yon"] == 1)}


# ================================================================== 15. VWAP reclaim
class VwapReclaim(D10Taban):
    """dis__vwap-reclaim (daytrade, 5m) — Christensen "VWAP sahte kırılımı" (güçlü gün VWAP'ı kısa süre kaybedip geri alır).
    VWAP = seans içi kümülatif hacim ağırlıklı tipik fiyat. "Güçlü gün" = o ana dek seans mumlarının en az `guclu_oran`'ı
    VWAP üstünde kapanmış (bir önceki mum itibarıyla) ve seansın ilk `min_mum` mumu geçmiş (kart: 10:30'dan sonra). Long: kapanış
    VWAP altına inmiş (1..geri_n ardışık mum) sonra kapanış tekrar VWAP üstüne çıkar (reclaim) -> long. Stop = VWAP -
    tampon_atr x ATR ("VWAP'nin biraz altı"); hedef = hedef_r x risk (kart: VWAP/önceki seviyeler; sayısal yok -> VARSAYIM).
    Short = ayna (zayıf gün VWAP'ı kısa süre geri alıp tekrar kaybeder). KODLANMAYAN: ikinci kart "VWAP tersine dönüş"
    (daha yüksek dip/zirve yapısı + VWAP hedefi: yapı tanımı öznel; swing yapısı için dis__* diğer ailelere bakın). Gün sonu."""
    ad = "dis__vwap-reclaim"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "geri_n": 2, "guclu_oran": 0.75, "min_mum": 12, "tampon_atr": 0.5, "hedef_r": 2.0}
    parametre_izgarasi = {"geri_n": [1, 2, 3], "guclu_oran": [0.6, 0.75, 0.9], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        from motor.strateji.dis._gosterge_d9 import ardisik_say
        p = self.parametreler
        sid = _sid(m, p)
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        vw = g.vwap_seans(y, d, k, m["hacim"], sid)
        v, no = vw["vwap"], vw["mum_no"]
        ust = (k > v) & v.notna()
        alt = (k < v) & v.notna()
        fu = ust.astype(int).groupby(sid).cumsum() / no
        fd = alt.astype(int).groupby(sid).cumsum() / no
        gn = int(p["geri_n"])
        dip_u, dip_d = ardisik_say(alt).shift(1), ardisik_say(ust).shift(1)
        pazar = no > p["min_mum"]
        lg = ust & dip_u.between(1, gn) & (fu.shift(1) >= p["guclu_oran"]) & pazar
        sh = alt & dip_d.between(1, gn) & (fd.shift(1) >= p["guclu_oran"]) & pazar
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        return {"long": lg, "short": sh & ~lg, "stop_l": v - tam, "stop_s": v + tam}


# ================================================================== 16. 3 gün momentum + açılış hacmi
class UcGunMomentumAcilisHacmi(D10Taban):
    """dis__3gun-momentum-acilis-hacmi (daytrade, 15m-1h) — Kuepper "3 gün momentum + açılışta hacim artışı" (trend takip örneği).
    Long (kart yalnız long; yonler="long"): son `gun_n` TAMAMLANMIŞ seans kapanışı art arda yükselmiş (her seans kapanışı
    öncekinden yüksek) VE bu `gun_n` seanslık getiri >= min_getiri VE seans kapanışlarının RSI(14)'ü 50 üstünde ve yükseliyor
    ("momentum artmaya devam eder") VE bugünkü seansın ilk mumunun hacmi, önceki `hacim_n` seansın ilk-mum hacmi ortalamasının
    hacim_k katından fazla ("açılışta hacim artışı"). Giriş: seansın ilk mumu kapanışında. Stop = %stop_yuzde (kart: keyfi %5);
    hedef = %hedef_yuzde (kart: %5-%10; en yakın direnç kodlanmadı). Çıkış: önceki seansın kapanış-RSI'ı 50'nin altına inerse
    (kart: RSI orta çizgi altı). Gün sonu çıkışı YOK (günlerce tutulabilir). "3 ardışık yüksek dip trend çizgisi" kodlanmadı."""
    ad = "dis__3gun-momentum-acilis-hacmi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "gun_n": 3, "min_getiri": 0.0, "rsi_n": 14, "rsi_cik": 50.0,
                               "hacim_n": 10, "hacim_k": 1.5, "stop_yuzde": 0.05, "hedef_yuzde": 0.075,
                               "hedef_r": 0.0, "gun_sonu": 0}
    parametre_izgarasi = {"gun_n": [2, 3, 4], "hacim_k": [1.0, 1.5, 2.0], "hedef_yuzde": [0.05, 0.075, 0.10]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        ix = m.index
        k = m["kapanis"]
        oz = seans_ozet(m, sid)
        gn = int(p["gun_n"])
        c = oz["c"]
        art = (c > c.shift(1)).astype(float).rolling(gn, min_periods=gn).min() == 1
        rs = g.rsi(c, int(p["rsi_n"]))
        oz2 = pd.DataFrame({
            "f": (art & (c / c.shift(gn) - 1.0 >= p["min_getiri"]) & (rs > 50) & (rs > rs.shift(1))).astype(float),
            "rs": rs})
        ilk_hacim = m["hacim"].groupby(sid).first()
        oz2["rv"] = ilk_hacim.rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        e = seansa_esle(oz2, sid, ix, 1)
        sira = seans_sira(sid, ix)
        lg = (sira == 0) & (e["f"] == 1) & (m["hacim"] > p["hacim_k"] * e["rv"])
        return {"long": lg, "stop_l": k * (1.0 - p["stop_yuzde"]), "hedef_l": k * (1.0 + p["hedef_yuzde"]),
                "cikis_long": e["rs"] < p["rsi_cik"]}


# ================================================================== 17. BIST üçlü sistem oyu
class BistUcluSistemOyu(D10Taban):
    """dis__bist-uclu-sistem-oyu (daytrade, 30m) — Kılınçarslan (BIST) üç alt sistemin oy birleşimi.
    Alt sistemler (hepsi "durum", ters sinyale kadar sürer = stop-and-reverse mantığı):
      A) SMA(59) + ATR(27) x 1 bandı: kapanış > SMA + atr_k x ATR -> +1; kapanış < SMA - atr_k x ATR -> -1; arada önceki durum.
      B) HHLL kanalı (31): kapanış önceki 31 mumun en yükseğinin üstünde -> +1, en düşüğünün altında -> -1; arada önceki durum.
      C) Stokastik (13, yavaşlatma 3): %K, %D'yi yukarı keserken K < stok_ust (70) -> +1; aşağı keserken K > stok_alt (18) -> -1;
         arada önceki durum.
    Giriş: üçü de +1 olduğu ilk mum (short: üçü -1). Çıkış: üçlü uzlaşma bozulur (en az biri +1 değil) — kart "alt sistemlerin
    SAR mantığı". Stop kartta yok: VARSAYIM stop_atr_k (3) x ATR. Gün sonu çıkışı yok. Kitap parametreleri BIST'e optimize
    edilmiştir: aşırı uyum riski kartta belirtilir."""
    ad = "dis__bist-uclu-sistem-oyu"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "sma_n": 59, "atr_n": 27, "atr_k": 1.0, "hhll_n": 31, "stok_n": 13, "stok_yav": 3,
                               "stok_alt": 18.0, "stok_ust": 70.0, "stop_atr_k": 3.0, "hedef_r": 0.0, "gun_sonu": 0}
    parametre_izgarasi = {"sma_n": [40, 59, 80], "hhll_n": [20, 31, 50], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        sm = g.sma(k, int(p["sma_n"]))
        a = g.atr(y, d, k, int(p["atr_n"]))
        ha = np.where(k > sm + p["atr_k"] * a, 1.0, np.where(k < sm - p["atr_k"] * a, -1.0, np.nan))
        ha = pd.Series(ha, index=m.index).ffill()
        hn = int(p["hhll_n"])
        hu = y.rolling(hn, min_periods=hn).max().shift(1)
        hl = d.rolling(hn, min_periods=hn).min().shift(1)
        hb = pd.Series(np.where(k > hu, 1.0, np.where(k < hl, -1.0, np.nan)), index=m.index).ffill()
        raw = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
        yv = int(p["stok_yav"])
        ks = raw.rolling(yv, min_periods=yv).mean()
        ds = ks.rolling(yv, min_periods=yv).mean()
        sc = pd.Series(np.where(yukari_kesis(ks, ds) & (ks < p["stok_ust"]), 1.0,
                                np.where(asagi_kesis(ks, ds) & (ks > p["stok_alt"]), -1.0, np.nan)), index=m.index).ffill()
        tum_u = (ha == 1) & (hb == 1) & (sc == 1)
        tum_d = (ha == -1) & (hb == -1) & (sc == -1)
        return {"long": gecis(tum_u), "short": gecis(tum_d), "cikis_long": ~tum_u, "cikis_short": ~tum_d}


# ================================================================== 18. Bollinger 2-3 SD bölgesi
class Bollinger23SdBolgesi(D10Taban):
    """dis__bollinger-2-3-sd-bolgesi (daytrade, 5m) — Velez "çift Bollinger bandı (2 ve 3 sapma, 21 periyot) + 200 MA".
    Long: kapanış SMA(ma_n=200) üstünde (trend filtresi) ve mum kapanışı alt 2 SD bandının altında, alt 3 SD bandının üstünde
    (iki sapma arasındaki bölge); bölgeye İLK giriş mumu (gecis) -> bir sonraki açılışta long. Short: kapanış 200 MA altında ve
    üst 2 SD - 3 SD bölgesinde. Stop = sinyal mumunun dibi (short: tepesi) -/+ tampon_atr x ATR (kart: "mum altı"; en az
    0.3 ATR'ye genişler). Hedef (kart): hedef_tipi="orta" orta bant (SMA21); "karsi" karşı 2 SD çizgisi (kart "2. hedef üst/alt
    çizgi" -> VARSAYIM: karşı 2 SD). Yorum: trend yönünde geri çekilmede ortalamaya dönüş. Gün sonu çıkışı."""
    ad = "dis__bollinger-2-3-sd-bolgesi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "bb_n": 21, "ic_sd": 2.0, "dis_sd": 3.0, "ma_n": 200, "hedef_tipi": "orta",
                               "tampon_atr": 0.2, "hedef_r": 0.0}
    parametre_izgarasi = {"hedef_tipi": ["orta", "karsi"], "ma_n": [100, 200, 400], "tampon_atr": [0.0, 0.2, 0.5]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d = m["kapanis"], m["yuksek"], m["dusuk"]
        n = int(p["bb_n"])
        ic = g.bollinger(k, n, float(p["ic_sd"]))
        dis = g.bollinger(k, n, float(p["dis_sd"]))
        ma = g.sma(k, int(p["ma_n"]))
        bol_l = (k < ic["alt"]) & (k >= dis["alt"])
        bol_s = (k > ic["ust"]) & (k <= dis["ust"])
        lg = gecis(bol_l & (k > ma))
        sh = gecis(bol_s & (k < ma))
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        tam = p["tampon_atr"] * a
        if p["hedef_tipi"] == "orta":
            hl, hs = ic["orta"], ic["orta"]
        else:
            hl, hs = ic["ust"], ic["alt"]
        return {"long": lg, "short": sh & ~lg, "stop_l": d - tam, "stop_s": y + tam, "hedef_l": hl, "hedef_s": hs}


# ================================================================== 19. dar gün açılış kırılımı
class DarGunAcilisKirilimi(D10Taban):
    """dis__dar-gun-acilis-kirilimi (daytrade, 5m) — Pruitt "mini-Russell dar aralık günü açılış kırılımı".
    Dünkü (önceki tamamlanmış seans) gerçek aralık TR = max(H, önceki C) - min(L, önceki C) < MAV(TR, tr_n=10) ise "dar gün".
    Yön: dünkü kapanış >= önceki kapanış -> long, aksi halde short. Giriş: bugünkü seans açılışı + k x MAV(TR) üstünde (short:
    altında) ilk KAPANIŞ (kart: açılış +/- 0.2 x MAV(TR,10) stop emri; stop emri kapanışa çevrildi), seansta bir kez.
    Stop = stop_atr_k x ATR (kartta değer yok -> VARSAYIM); hedef = hedef_r x risk (kart: 4 puan / günün zirvesinden iz süren;
    puan -> R). İki birimli pozisyon ve başabaş geçişi için CikisAyarlari(basabas) önerilir (varsayılan kapalı). Gün sonu
    çıkışı (MOC)."""
    ad = "dis__dar-gun-acilis-kirilimi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "tr_n": 10, "k": 0.2, "stop_atr_k": 1.5, "hedef_r": 2.0}
    parametre_izgarasi = {"k": [0.1, 0.2, 0.3], "stop_atr_k": [1.0, 1.5, 2.0], "hedef_r": [1.0, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        sid = _sid(m, p)
        ix = m.index
        kp = m["kapanis"]
        oz = seans_ozet(m, sid)
        cprev = oz["c"].shift(1)
        tr = np.maximum(oz["h"], cprev) - np.minimum(oz["l"], cprev)
        mav = tr.rolling(int(p["tr_n"]), min_periods=int(p["tr_n"])).mean()
        oz2 = pd.DataFrame({"dar": (tr < mav).astype(float), "yon": np.where(oz["c"] >= cprev, 1.0, -1.0), "mav": mav})
        e = seansa_esle(oz2, sid, ix, 1)
        ac = m["acilis"].groupby(sid).transform("first")
        lg = (e["dar"] == 1) & (e["yon"] == 1) & (kp >= ac + p["k"] * e["mav"])
        sh = (e["dar"] == 1) & (e["yon"] == -1) & (kp <= ac - p["k"] * e["mav"])
        il = ilk_olay(lg | sh, sid)
        return {"long": lg & il, "short": sh & il}
