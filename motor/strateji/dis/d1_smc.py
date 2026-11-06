"""D1 grubu (dış TradingView): piyasa yapısı / FVG / aralık dönüşü / trend-filtre karması stratejiler.

EMA200 + BOS/CHoCH + 2x FVG, ICT 10:00 NY ilk FVG, MTF aralık dönüşü (HTF yapı önyargısı) ve NORN WEAVE.
Üst zaman dilimi (HTF) değerleri yalnız KAPANMIŞ HTF mumlarından (htf.ust_zaman) alınır; pivotlar onay mumunda bilinir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import kur
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


# ----------------------------------------------------------------------------- EMA200 + BOS/CHoCH + 2x FVG
class Ema200BosFvg(Strateji):
    """dis__ema200-bos-fvg: EMA200 kesişimi + yapı kırılımı (BOS/CHoCH) + iki ayrı FVG aynı pencerede; sonra giriş.

    Kaynak: arsiv/strateji-sg/tv/pine/x3kpQqJ5.pine (EMA200 + BOS/CHoCH + STRICT 2x FVG Backtest Strategy; kaynakta 2 dk NASDAQ/altın).
    Kural: kapanış EMA200'ü yukarı (aşağı) keserse yeni bir döngü başlar. Döngünün ilk `pencere` mumunda, yönde (1) bir yapı kırılımı
    (kapanış, onaylı son swing tepesini/dibini [swing_len mum] ilk kez aşar) ve (2) iki AYRI aynı yönlü FVG (low[i] > high[i-2] boğa;
    high[i] < low[i-2] ayı; üst üste binen ikinci FVG sayılmaz) oluşursa kurulum hazırdır. Hazır mumdan sonraki ilk mumun kapanışında
    sinyal (döngü başına tek işlem). Stop = sl_atr x ATR, hedef = hedef_r x risk, başabaş: 0.8R sonrası stop girişe.
    Uyarlama: orijinal puan cinsinden sabit SL/TP/BE (NASDAQ 50/100/40 puan) -> ATR/R bazlı; giriş mumun (açılış+kapanış)/2 LİMİT emridir (5 mum
    geçerli) -> burada sonraki açılışta piyasa emri. Kısmi TP1 (varsayılan kapalı) alınmadı. BOS ile CHoCH ayrımı sinyali etkilemez (ikisi de
    "yapı olayı") -> tek olay olarak kodlandı. Sentez: kaynaktaki piyasa seçimi (GOLD/NASDAQ/CUSTOM) kaldırıldı.
    Eski sonuç: yok (envanterde sonuç kaydı yok).
    """
    ad = "dis__ema200-bos-fvg"
    stil = "scalp"
    varsayilan_parametreler = {"ema_n": 200, "swing_len": 5, "pencere": 6, "atr_periyot": 14, "sl_atr": 1.5,
                               "hedef_r": 2.0, "short": True}
    parametre_izgarasi = {"pencere": [4, 6, 8], "swing_len": [3, 5, 8], "sl_atr": [1.0, 1.5, 2.5]}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=0.8)

    def cikis_var_mi(self) -> bool:
        return True   # hedef

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        h, l, c = y.to_numpy(float), d.to_numpy(float), k.to_numpy(float)
        n = len(c)
        ema = g.ema(k, int(p["ema_n"])).to_numpy()
        atr = g.atr(y, d, k, int(p["atr_periyot"])).to_numpy()
        pv = fraktal_pivotlar(y, d, int(p["swing_len"]))
        tepe, dip = pv["son_tepe_fiyat"].to_numpy(), pv["son_dip_fiyat"].to_numpy()
        pen = int(p["pencere"])
        yon = np.zeros(n, dtype="int64")
        kirik_t = kirik_d = np.nan
        cd = 0
        cbar = -10**9
        struct_bar = -1
        fvg_say = 0
        fvg_alt = fvg_ust = np.nan
        fvg2_bar = -1
        hazir_bar = -1
        tuketildi = True
        for i in range(2, n):
            if np.isnan(ema[i]) or np.isnan(ema[i - 1]):
                continue
            yukari = c[i] > ema[i] and c[i - 1] <= ema[i - 1]
            asagi = c[i] < ema[i] and c[i - 1] >= ema[i - 1]
            boga_y = (not np.isnan(tepe[i])) and c[i] > tepe[i] and tepe[i] != kirik_t
            ayi_y = (not np.isnan(dip[i])) and c[i] < dip[i] and dip[i] != kirik_d
            if boga_y:
                kirik_t = tepe[i]
            if ayi_y:
                kirik_d = dip[i]
            if yukari or asagi:
                cd = 1 if yukari else -1
                cbar, struct_bar, fvg_say, fvg2_bar, hazir_bar = i, -1, 0, -1, -1
                fvg_alt = fvg_ust = np.nan
                tuketildi = False
            if cd == 0:
                continue
            if i <= cbar + pen and hazir_bar < 0 and not tuketildi:
                if (cd == 1 and boga_y) or (cd == -1 and ayi_y):
                    struct_bar = i
                fvg_boga = l[i] > h[i - 2]
                fvg_ayi = h[i] < l[i - 2]
                if (cd == 1 and fvg_boga) or (cd == -1 and fvg_ayi):
                    alt, ust = (h[i - 2], l[i]) if cd == 1 else (h[i], l[i - 2])
                    if fvg_say == 0:
                        fvg_say, fvg_alt, fvg_ust = 1, alt, ust
                    elif fvg_say == 1:
                        if alt <= fvg_ust and ust >= fvg_alt:
                            fvg_alt, fvg_ust = min(fvg_alt, alt), max(fvg_ust, ust)
                        else:
                            fvg_say, fvg2_bar = 2, i
                if struct_bar >= 0 and fvg_say == 2:
                    hazir_bar = max(struct_bar, fvg2_bar)
            elif hazir_bar >= 0 and not tuketildi and i > hazir_bar:
                yon[i] = cd
                tuketildi = True
        yon_s = pd.Series(yon, index=k.index)
        sd = p["sl_atr"] * pd.Series(atr, index=k.index)
        r = p["hedef_r"]
        return kur(mumlar, yon_s == 1, (yon_s == -1) & bool(p["short"]), k - sd, k + sd, k + r * sd, k - r * sd)


# ----------------------------------------------------------------------------- ICT 10:00 NY ilk FVG
class Ict10amFvg(Strateji):
    """dis__ict-10am-fvg: 10:00 NY'den sonraki ilk FVG'nin kenarına geri çekilişte giriş; hedef seans tepesi/dibi, 16:00'da kapanış.

    Kaynak: arsiv/strateji-sg/tv/pine/Za5HKgrL.pine (ICT 10AM First FVG Daily Strategy).
    Kural (NY saati): 10:00 mumundan itibaren seans tepe/dibi izlenir. Pencerede (10:00-16:00) İLK FVG (boğa: low[i] > high[i-2]; ayı: high[i] <
    low[i-2]) kurulumu belirler: boğa için giriş = FVG üst kenarı (low[i]), stop = low[i-1], hedef = o ana kadarki seans tepesi; ayı aynası.
    Fiyat giriş seviyesine geri çekilince (sonraki mum) işlem açılır; günde en fazla 1 işlem; 16:00'da açık pozisyon kapanır. Cuma 15:45 sonrası
    ve hafta sonu kilidi (cuma_kilit).
    Uyarlama: orijinal giriş LİMİT emridir (seviyeden dolar); burada geri çekilme mumunun kapanışında sinyal, sonraki açılışta piyasa emri
    (stop sinyal anında geçersizse işlem düşer). Kripto 7/24 olduğundan hafta sonu kilidi o günleri atlar. Saat dilimi America/New_York (yaz saati
    otomatik). Zaman dilimi belirtilmiyor (futures dakikalık); 15m varsayıldı.
    Eski sonuç: ön elemede elendi: KESİN ELEME: gerekli veri yok (gün içi ≤15 dk geçmişi Yahoo'da 60 gün); burada kripto 15m kullanıldığından yeniden denenir.
    """
    ad = "dis__ict-10am-fvg"
    stil = "scalp"
    varsayilan_parametreler = {"baslangic_saat": 10, "bitis_saat": 16, "cuma_kilit": True, "short": True, "long": True}
    parametre_izgarasi = {"baslangic_saat": [9, 10, 11], "bitis_saat": [14, 16, 20]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ny = mumlar.index.tz_convert("America/New_York")
        saat, dak, dow = ny.hour.to_numpy(), ny.minute.to_numpy(), ny.dayofweek.to_numpy()
        gun = (ny.year * 10000 + ny.month * 100 + ny.day).to_numpy()
        h, l, c = y.to_numpy(float), d.to_numpy(float), k.to_numpy(float)
        n = len(c)
        bs, bt = int(p["baslangic_saat"]), int(p["bitis_saat"])
        long_ok = np.zeros(n, dtype=bool)
        short_ok = np.zeros(n, dtype=bool)
        stop_l = np.full(n, np.nan)
        stop_s = np.full(n, np.nan)
        hed_l = np.full(n, np.nan)
        hed_s = np.full(n, np.nan)
        kilit = np.zeros(n, dtype=bool)
        sh = sl = np.nan
        acik = bulundu = islem = False
        yon = 0
        giris = stop = np.nan
        fvg_i = -1
        for i in range(n):
            if i == 0 or gun[i] != gun[i - 1]:
                sh = sl = np.nan
                acik = bulundu = islem = False
                yon = 0
            pencerede = bs <= saat[i] < bt
            kil = bool(p["cuma_kilit"]) and (dow[i] >= 5 or (dow[i] == 4 and saat[i] * 60 + dak[i] >= 15 * 60 + 45))
            kilit[i] = kil
            if saat[i] == bs and dak[i] == 0:
                sh, sl, acik = h[i], l[i], True
            elif pencerede and acik:
                sh, sl = max(sh, h[i]), min(sl, l[i])
            if i >= 2 and not bulundu and acik and pencerede and not kil and bs <= saat[i - 1] < bt:
                if h[i] < l[i - 2]:
                    bulundu, yon, fvg_i, giris, stop = True, -1, i, h[i], h[i - 1]
                elif l[i] > h[i - 2]:
                    bulundu, yon, fvg_i, giris, stop = True, 1, i, l[i], l[i - 1]
            elif bulundu and not islem and i > fvg_i and pencerede and not kil:
                hedef = sl if yon == -1 else sh
                gecerli = (stop > giris and hedef < giris) if yon == -1 else (stop < giris and hedef > giris)
                dokundu = h[i] >= giris if yon == -1 else l[i] <= giris
                if gecerli and dokundu:
                    islem = True
                    if yon == 1 and p["long"]:
                        long_ok[i], stop_l[i], hed_l[i] = True, stop, hedef
                    elif yon == -1 and p["short"]:
                        short_ok[i], stop_s[i], hed_s[i] = True, stop, hedef
        idx = k.index
        bitti = pd.Series(saat >= bt, index=idx) | pd.Series(kilit, index=idx)
        return kur(mumlar, pd.Series(long_ok, index=idx), pd.Series(short_ok, index=idx),
                   pd.Series(stop_l, index=idx), pd.Series(stop_s, index=idx),
                   pd.Series(hed_l, index=idx), pd.Series(hed_s, index=idx), cikis_l=bitti, cikis_s=bitti)


# ----------------------------------------------------------------------------- MTF aralık dönüşü
def _aralik_donus(h: np.ndarray, l: np.ndarray, c: np.ndarray):
    """'Aralık dönüşü': referans mum = kapanışı bir önceki referansın dışına çıkan son mum. Kapanış referans tepesinin üstüne çıkarsa yön +1,
    dibinin altına inerse -1; her çıkışta referans yeni mumun [dibi, tepesi] olur. Dönen: eHi, eLo, yon, flip_up, flip_dn, onc_hi, onc_lo."""
    n = len(c)
    ehi = np.full(n, np.nan)
    elo = np.full(n, np.nan)
    yon = np.zeros(n, dtype="int64")
    fu = np.zeros(n, dtype=bool)
    fd = np.zeros(n, dtype=bool)
    d = 0
    hi = lo = np.nan
    for i in range(n):
        if np.isnan(hi):
            hi, lo = h[i], l[i]
        else:
            ust, alt = c[i] > hi, c[i] < lo
            if ust or alt:
                onc = d
                d = 1 if ust else -1
                fu[i] = ust and onc != 1
                fd[i] = alt and onc != -1
                hi, lo = h[i], l[i]
        ehi[i], elo[i], yon[i] = hi, lo, d
    return ehi, elo, yon, fu, fd


class MtfAralikDonus(Strateji):
    """dis__mtf-aralik-donus: HTF piyasa yapısı önyargısına göre aralık dönüşünde giriş; swing pivot stop, ödül/risk hedefi.

    Kaynak: arsiv/strateji-sg/tv/pine/RQHNSLbH.pine (MTF Range Flip HTF Market Structure Bias; futures 5m/15m).
    Kural: LTF "aralık dönüşü": kapanış son referans mumun tepesini yukarı (dibini aşağı) aşınca yön değişir -> flipU/flipD. HTF (1h)
    önyargısı BOS: HTF onaylı son pivot tepesini (msLen mum) kapanışla aşarsa +1, dibini aşarsa -1 (aksi önceki). Long: flipU ve
    önyargı +1 ve (konum="Pullback") kapanış < HTF aralık orta noktası ((HTF referans tepe+dip)/2; "Breakout": >). Short aynası.
    Stop = LTF son pivot dibi (pv_len; geçerliyse) ile dönüş referans dibinden düşük olanı, - tampon_atr x ATR. Hedef = rr x risk
    (long rr_long=1.5, short rr_short=0.5; orijinal asimetri).
    Uyarlama: Pine'daki HTF [1]+lookahead_on okuması tamamlanmış HTF muma denk gelir -> htf.ust_zaman ile KAPANMIŞ mumlarla yeniden
    kurulur (repaint yok). Tick cinsinden tampon -> ATR kesri. İşlem penceresi (NY 09:30-15:30), rejim/oynaklık/VWAP/derinlik filtreleri
    (hepsi varsayılan kapalı) ve boyut ölçekleme alınmadı. Veri 15m, HTF 1h.
    Eski sonuç: yok (envanterde sonuç kaydı yok).
    """
    ad = "dis__mtf-aralik-donus"
    stil = "scalp"
    varsayilan_parametreler = {"htf": "1h", "ms_len": 3, "pv_len": 3, "konum": "Pullback", "onyargi": True,
                               "tampon_atr": 0.05, "rr_long": 1.5, "rr_short": 0.5, "atr_periyot": 14, "short": True}
    parametre_izgarasi = {"ms_len": [2, 3, 5], "rr_long": [1.0, 1.5, 2.5], "rr_short": [0.5, 1.0, 1.5]}

    def cikis_var_mi(self) -> bool:
        return True   # hedef

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ms = int(p["ms_len"])

        def htf_ozet(u):
            pv = fraktal_pivotlar(u["yuksek"], u["dusuk"], ms)
            uc = u["kapanis"].to_numpy(float)
            ph, pl = pv["son_tepe_fiyat"].to_numpy(), pv["son_dip_fiyat"].to_numpy()
            bos = np.zeros(len(uc), dtype="int64")
            prev = 0
            for i in range(len(uc)):
                if not np.isnan(ph[i]) and uc[i] > ph[i]:
                    prev = 1
                elif not np.isnan(pl[i]) and uc[i] < pl[i]:
                    prev = -1
                bos[i] = prev
            ehi, elo, _, _, _ = _aralik_donus(u["yuksek"].to_numpy(float), u["dusuk"].to_numpy(float), uc)
            return pd.DataFrame({"bos": bos, "orta": (ehi + elo) / 2.0}, index=u.index)
        htf = ust_zaman(mumlar, p["htf"], htf_ozet)
        bos, orta = htf["bos"], htf["orta"]
        ehi, elo, _, fu, fd = _aralik_donus(y.to_numpy(float), d.to_numpy(float), k.to_numpy(float))
        fu, fd = pd.Series(fu, index=k.index), pd.Series(fd, index=k.index)
        elo_s, ehi_s = pd.Series(elo, index=k.index), pd.Series(ehi, index=k.index)
        pv = fraktal_pivotlar(y, d, int(p["pv_len"]))
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        taban_l = pd.concat([pv["son_dip_fiyat"].where(pv["son_dip_fiyat"] < k), elo_s], axis=1).min(axis=1)
        taban_s = pd.concat([pv["son_tepe_fiyat"].where(pv["son_tepe_fiyat"] > k), ehi_s], axis=1).max(axis=1)
        stop_l = taban_l - p["tampon_atr"] * atr
        stop_s = taban_s + p["tampon_atr"] * atr
        if p["onyargi"]:
            bl, bs_ = bos == 1, bos == -1
        else:
            bl = bs_ = pd.Series(True, index=k.index)
        if p["konum"] == "Pullback":
            kl, ks = k < orta, k > orta
        elif p["konum"] == "Breakout":
            kl, ks = k > orta, k < orta
        else:
            kl = ks = pd.Series(True, index=k.index)
        kl, ks = kl | orta.isna(), ks | orta.isna()
        long_ok = fu & bl & kl
        short_ok = fd & bs_ & ks & bool(p["short"])
        return kur(mumlar, long_ok, short_ok, stop_l, stop_s,
                   k + p["rr_long"] * (k - stop_l), k - p["rr_short"] * (stop_s - k))


# ----------------------------------------------------------------------------- NORN WEAVE
class NornWeaveThurisaz(Strateji):
    """dis__norn-weave-thurisaz: Dow swing trendi + EMA eğimi + ADX + günlük Fibonacci süzgeci; SL, başabaş (BE) ve trend değişimi çıkışları.

    Kaynak: arsiv/strateji-sg/tv/pine/ab5k064U.pine (NORN WEAVE | THURISAZ).
    Kural: Dow trendi: kapanış son onaylı swing tepesini (swing_len) aşarsa +1, dibini kırarsa -1. Long: EMA (swing_len x ema_oran) yükseliyor,
    trend +1, ADX(14) > son 300 mumun medyanı (oto-kalibrasyon) ve günlük Fib süzgeci geçer; short aynası. Günlük Fib: günlük trend ters yönde
    ise (geri çekilişte giriş) fiyat günlük swing aralığının %38.2-%61.8 "dinlenme bölgesinde" değilse girişe izin verilir; aynı yönde veya
    günlük trend yoksa her zaman izin. Stop = -(SMA50(ATR%) x 3.5)% (toplam -%5..-%20 arası). Hedef = giriş ± hedef_n x ATR(50) x oto faktör
    (3.8 +- oynaklık ayarı). Çıkış: trend ters yöne dönünce.
    Uyarlama: (1) Footprint delta süzgeci (BTC/ETH footprint, OHLCV DIŞI veri) orijinalde de "veri yoksa geçer" -> KAPALI kodlandı. (2) 3 kademeli
    kâr alma (TP1-3, %30'ar) tek hedefe (hedef_n. kademe) indirgendi; "BE" (%8.5 kâr sonrası stop girişe) motorun başabaşı ile 1R'de yaklaşıklandı.
    (3) Günlük pivotlar htf.ust_zaman ile TAMAMLANMIŞ günlerden (orijinaldeki [1] + lookahead_off ile uyumlu). TF belirtilmiyor, 4h varsayıldı.
    Eski sonuç: yok (envanterde sonuç kaydı yok).
    """
    ad = "dis__norn-weave-thurisaz"
    stil = "swing"
    varsayilan_parametreler = {"swing_len": 15, "ema_oran": 16, "adx_pencere": 300, "gun_swing": 7, "oto_kalib": True,
                               "adx_man": 20.5, "atr_carpan_man": 3.8, "stop_man": -10.0, "hedef_n": 2, "short": True}
    parametre_izgarasi = {"swing_len": [10, 15, 20], "ema_oran": [10, 16, 24], "hedef_n": [1, 2, 3]}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0)

    def cikis_var_mi(self) -> bool:
        return True   # trend dönüşü + hedef

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        sw = int(p["swing_len"])
        h, l, c = y.to_numpy(float), d.to_numpy(float), k.to_numpy(float)
        n = len(c)
        # Dow trendi (swing onayı sw mum geriden)
        ust_pivot = (y.shift(sw) == y.rolling(2 * sw + 1, min_periods=2 * sw + 1).max()).to_numpy()
        alt_pivot = (d.shift(sw) == d.rolling(2 * sw + 1, min_periods=2 * sw + 1).min()).to_numpy()
        trend = np.zeros(n, dtype="int64")
        sh = sl = np.nan
        tr = 0
        for i in range(n):
            if i >= sw and ust_pivot[i]:
                sh = h[i - sw]
            if i >= sw and alt_pivot[i]:
                sl = l[i - sw]
            if not np.isnan(sh) and c[i] > sh and tr != 1:
                tr = 1
            if not np.isnan(sl) and c[i] < sl and tr != -1:
                tr = -1
            trend[i] = tr
        trend = pd.Series(trend, index=k.index)
        ema = g.ema(k, sw * int(p["ema_oran"]))
        adx = g.adx(y, d, k, 14)["adx"]
        pencere = int(p["adx_pencere"])
        medyan = adx.rolling(pencere, min_periods=pencere).quantile(0.5, interpolation="lower")
        adx_esik = medyan.fillna(20.5) if p["oto_kalib"] else p["adx_man"]
        trendli = adx > adx_esik
        # oynaklık ayarlı faktörler
        atr_yuzde = g.atr(y, d, k, 14) / k * 100.0
        oran = atr_yuzde / g.sma(atr_yuzde, 200)
        oran = oran.fillna(1.0)
        faktor = (3.8 + (1.0 - oran).clip(-1.0, 1.0) * 0.8) if p["oto_kalib"] else p["atr_carpan_man"]
        stop_yuzde = (-(g.sma(atr_yuzde, 50) * 3.5)).clip(-20.0, -5.0).fillna(-10.0) if p["oto_kalib"] else p["stop_man"]
        # günlük Fibonacci süzgeci
        gs = int(p["gun_swing"])

        def gunluk(u):
            pv = fraktal_pivotlar(u["yuksek"], u["dusuk"], gs)
            dh, dl = pv["son_tepe_fiyat"].to_numpy(), pv["son_dip_fiyat"].to_numpy()
            uc = u["kapanis"].to_numpy(float)
            dt = np.zeros(len(uc), dtype="int64")
            prev = 0
            for i in range(len(uc)):
                if not np.isnan(dh[i]) and uc[i] > dh[i] and prev != 1:
                    prev = 1
                if not np.isnan(dl[i]) and uc[i] < dl[i] and prev != -1:
                    prev = -1
                dt[i] = prev
            return pd.DataFrame({"dh": dh, "dl": dl, "dt": dt}, index=u.index)
        gn = ust_zaman(mumlar, "1d", gunluk)
        dt = gn["dt"].fillna(0).astype(int)
        aralik = gn["dh"] - gn["dl"]
        f382_l, f618_l = gn["dl"] + aralik * 0.382, gn["dl"] + aralik * 0.618
        f382_s, f618_s = gn["dh"] - aralik * 0.382, gn["dh"] - aralik * 0.618
        orta_l = f382_l.notna() & (k >= f382_l) & (k <= f618_l)
        orta_s = f382_s.notna() & (k <= f382_s) & (k >= f618_s)
        izin_l = (dt == 0) | (dt == 1) | ((dt == -1) & ~orta_l)
        izin_s = (dt == 0) | (dt == -1) | ((dt == 1) & ~orta_s)
        long_ok = (ema > ema.shift(1)) & (trend == 1) & trendli & izin_l
        short_ok = (ema < ema.shift(1)) & (trend == -1) & trendli & izin_s & bool(p["short"])
        atr50 = g.atr(y, d, k, 50) * faktor
        sy = stop_yuzde / 100.0
        m = int(p["hedef_n"])
        return kur(mumlar, long_ok, short_ok, k * (1 + sy), k * (1 - sy), k + m * atr50, k - m * atr50,
                   cikis_l=trend == -1, cikis_s=trend == 1)
