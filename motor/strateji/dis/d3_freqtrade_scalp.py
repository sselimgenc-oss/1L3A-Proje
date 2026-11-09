"""D3 freqtrade stratejileri, orijinal 5m-15m: hepsi SCALP (en az 15m mumda çalıştırılır).

Ortak uyarlama (freqtrade -> 1L3A):
  * `stoploss` -> stop_yuzde (orijinal değer varsayılan); `minimal_roi` kademeleri -> bir kademenin yüzdesi `hedef_yuzde`,
    süresi `zaman_cikisi` (mum; dakika / 15 çünkü scalp tabanı 15m). Orijinal 5m'de çalışırken süre/mum değişir.
  * Orijinal yalnız long ise short ayna kuralıyla `yonler="short"/"ls"`; varsayılan orijinal gibi "long".
  * `exit_profit_only` / trailing_stop alanları motorda yok, atlandı.
Arşiv: arsiv/algo-sg/dis_kaynak/ft/strategies/*.py (veri sayılır, çalıştırılmadı).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban, cmf, hizli_stokastik, mfi, tema
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, yukari_kesis


class PowerTower(D3Taban):
    """dis__power-tower — üç ardışık mumda kapanışın 2 mum öncesine göre güçlü yükselişi, 5m orijinal (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/PowerTower.py.
    Orijinal kural: close[t-k] > close[t-k-2] ** buy_pow (k=0,1,2), buy_pow=3.849; çıkış: aynı üç koşulun tersi VEYA'sı
    (sell_pow=3.798). ÜS kullanımı fiyat BİRİMİNE bağlıdır (fiyat > 1 iken close ** 3.8 > close: giriş hiç, çıkış
    hep tetiklenir) -> çalışmaz. BİRİMSİZ yeniden yazım: r = close[t]/close[t-2]; giriş r[t], r[t-1], r[t-2] hepsi
    > 1 + esik; çıkış r'lerden herhangi biri < 1 - cikis_esik. esik/cikis_esik bizim seçimimiz (orijinal sayı yok).
    Short ayna. Uyarlama: stop %28.8; ROI -> hedef %4.8 + 11 mum (159 dk / 15m).
    Eski sonuç: PF IS 0.91 / OOS 0.93; Sh IS -0.29 / OOS -0.24 -> kaldı."""
    ad = "dis__power-tower"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.288, "hedef_yuzde": 0.048, "zaman_cikisi": 11,
                               "esik": 0.003, "cikis_esik": 0.003}
    parametre_izgarasi = {"esik": [0.002, 0.003, 0.005], "cikis_esik": [0.002, 0.003, 0.005], "stop_yuzde": [0.05, 0.10, 0.288]}

    def kosullar(self, m):
        p = self.parametreler
        r = m["kapanis"] / m["kapanis"].shift(2)
        r3 = [r, r.shift(1), r.shift(2)]
        yuk = (r3[0] > 1 + p["esik"]) & (r3[1] > 1 + p["esik"]) & (r3[2] > 1 + p["esik"])
        dus = (r3[0] < 1 - p["esik"]) & (r3[1] < 1 - p["esik"]) & (r3[2] < 1 - p["esik"])
        c_l = (r3[0] < 1 - p["cikis_esik"]) | (r3[1] < 1 - p["cikis_esik"]) | (r3[2] < 1 - p["cikis_esik"])
        c_s = (r3[0] > 1 + p["cikis_esik"]) | (r3[1] > 1 + p["cikis_esik"]) | (r3[2] > 1 + p["cikis_esik"])
        return {"long": yuk, "short": dus, "cikis_long": c_l, "cikis_short": c_s}


class Quickie(D3Taban):
    """dis__quickie — ADX>30, TEMA9 Bollinger orta altında ama yükseliyor, fiyat SMA200 altında: kısa vadeli long, 5m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/Quickie.py (G. Wohlgemuth).
    Kural (long): ADX>adx_giris & TEMA9 < BB(20,2) orta & TEMA9 > TEMA9[1] & SMA200 > kapanış. Çıkış: ADX>adx_cikis &
    TEMA9 > BB orta & TEMA9 < TEMA9[1]. Short ayna (fiyat SMA200 üstü, TEMA üstte ve düşüyor; çıkış ayna).
    Uyarlama: stop %25 (orijinal); ROI {10:15%, 15:6%, 30:3%, 100:1%} -> hedef %3 + 7 mum (100 dk / 15m).
    Eski sonuç: PF IS 0.71 / OOS 0.72; Sh IS -1.12 / OOS -0.84 -> kaldı."""
    ad = "dis__quickie"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.25, "hedef_yuzde": 0.03, "zaman_cikisi": 7,
                               "adx_giris": 30.0, "adx_cikis": 70.0}
    parametre_izgarasi = {"adx_giris": [25.0, 30.0, 35.0], "hedef_yuzde": [0.01, 0.03, 0.06], "stop_yuzde": [0.05, 0.10, 0.25]}

    def kosullar(self, m):
        p, kap = self.parametreler, m["kapanis"]
        adx = g.adx(m["yuksek"], m["dusuk"], kap, 14)["adx"]
        t = tema(kap, 9)
        orta = g.bollinger(kap, 20, 2.0)["orta"]
        s200 = g.sma(kap, 200)
        yuk, dus = t > t.shift(1), t < t.shift(1)
        return {"long": (adx > p["adx_giris"]) & (t < orta) & yuk & (s200 > kap),
                "short": (adx > p["adx_giris"]) & (t > orta) & dus & (s200 < kap),
                "cikis_long": (adx > p["adx_cikis"]) & (t > orta) & dus,
                "cikis_short": (adx > p["adx_cikis"]) & (t < orta) & yuk}


class SmoothOperator(D3Taban):
    """dis__smooth-operator — MFI/RSI/CCI aşırı satımında dönüş girişi, yumuşatılmış karışım zirvesinde çıkış, 5m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/SmoothOperator.py (G. Wohlgemuth).
    Giriş (long) = (A veya B veya C) ve kapanış > önceki kapanış. A: ohlc4 4 mum düşüp döndü (V) + önceki mumun düşüğü BB
    orta altı + CCI[1]<-100 + RSI[1]<30. B: düşük<BB orta + CCI<-200 + RSI<30 + MFI<30. C: MFI<10 + CCI<-150 + RSI<MFI.
    Çıkış: karışım = TEMA21((1.125 RSI_ema11 + 1.125 MFI_ema11 + CCI_ema11)/3) > 100 ve tepe dönüşü; VEYA `yesil` ardışık
    yeşil mum (orijinal 9 = "eight_green_candles"); VEYA CCI>200 & RSI>70. Short: ayna giriş (A/B/C tersi),
    çıkış CCI<-200 & RSI<30 veya `yesil` ardışık kırmızı mum (karışım>100 aynası orijinalde yok, eklenmedi).
    Uyarlama: stop %5, ROI {0:10%} -> hedef %10 (orijinal).
    Eski sonuç: PF IS 0.72 / OOS 0.56; Sh IS -2.33 / OOS -0.86 -> kaldı."""
    ad = "dis__smooth-operator"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.05, "hedef_yuzde": 0.10, "yesil": 9}
    parametre_izgarasi = {"stop_yuzde": [0.03, 0.05, 0.08], "hedef_yuzde": [0.05, 0.10, 0.15], "yesil": [7, 9, 11]}

    def kosullar(self, m):
        p = self.parametreler
        o, h, l, c, v = (m[k] for k in ("acilis", "yuksek", "dusuk", "kapanis", "hacim"))
        cc, rr, mm = cci(h, l, c, 20), g.rsi(c, 14), mfi(h, l, c, v, 14)
        orta = g.bollinger(c, 20, 2.0)["orta"]
        e = lambda x: x.ewm(span=11, adjust=False, min_periods=11).mean()  # noqa: E731
        karisim = tema((e(rr) * 1.125 + e(mm) * 1.125 + e(cc)) / 3.0, 21)
        av = (o + h + l + c) / 4.0
        n = int(p["yesil"])
        yesil = pd.concat([(c > o).shift(i, fill_value=False) for i in range(n)], axis=1).all(axis=1) & (c.shift(n - 1).notna())
        kirmizi = pd.concat([(c < o).shift(i, fill_value=False) for i in range(n)], axis=1).all(axis=1) & (c.shift(n - 1).notna())
        yuk = (av.shift(1) < av) & (av.shift(2) > av.shift(1)) & (av.shift(3) > av.shift(2)) & (av.shift(4) > av.shift(3)) & (av.shift(5) > av.shift(4))
        dus = (av.shift(1) > av) & (av.shift(2) < av.shift(1)) & (av.shift(3) < av.shift(2)) & (av.shift(4) < av.shift(3)) & (av.shift(5) < av.shift(4))
        a_l = yuk & (l.shift(1) < orta) & (cc.shift(1) < -100) & (rr.shift(1) < 30)
        b_l = (l < orta) & (cc < -200) & (rr < 30) & (mm < 30)
        c_l = (mm < 10) & (cc < -150) & (rr < mm)
        a_s = dus & (h.shift(1) > orta) & (cc.shift(1) > 100) & (rr.shift(1) > 70)
        b_s = (h > orta) & (cc > 200) & (rr > 70) & (mm > 70)
        c_s = (mm > 90) & (cc > 150) & (rr > mm)
        zirve = (karisim > 100) & (karisim.shift(1) > karisim) & (karisim.shift(2) < karisim.shift(1)) & (karisim.shift(3) < karisim.shift(2))
        return {"long": (a_l | b_l | c_l) & (c > c.shift(1)),
                "short": (a_s | b_s | c_s) & (c < c.shift(1)),
                "cikis_long": zirve | yesil | ((cc > 200) & (rr > 70)),
                "cikis_short": kirmizi | ((cc < -200) & (rr < 30))}


class Strategy005(D3Taban):
    """dis__strategy005 — hacim patlaması + SMA40 altı + StochF D>K + düşük RSI/FisherRSI girişi, RSI yukarı kesişiminde çıkış, 5m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/Strategy005.py (G. Lonlas).
    Kural (long): hacim > ort(hacim, hacim_ort) x 4 & kapanış < SMA40 & fastD > fastK & RSI > rsi_alt & fastD > fastd_alt &
    FisherRSI_norma < fisher_ust (norma = 50 (tanh(0.1 (RSI-50)) + 1)). Çıkış ("rsi-macd-minusdi"): RSI, rsi_sat'ı yukarı
    keser & MACD < 0 & -DI > minus_di. (Orijinal alternatif 'sar-fisherRsi' çıkışı yapılandırma hatası nedeniyle hiç tetiklenmez, atlandı.)
    Short ayna (eşikler 100-x, hacim patlaması aynı, kapanış > SMA40; çıkış: RSI 100-rsi_sat'ı aşağı keser & MACD>0 & +DI>minus_di).
    Uyarlama: stop %10; ROI {0:5%,20:4%,40:3%,80:2%,1440:1%} -> hedef %2 + 96 mum (1440 dk / 15m); `exit_profit_only` atlandı.
    Eski sonuç: PF IS 0.82 / OOS 0.75; Sh IS -1.14 / OOS -1.31 -> kaldı."""
    ad = "dis__strategy005"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.10, "hedef_yuzde": 0.02, "zaman_cikisi": 96,
                               "hacim_ort": 150, "rsi_alt": 26, "fastd_alt": 1, "fisher_ust": 5, "rsi_sat": 74, "minus_di": 4}
    parametre_izgarasi = {"hacim_ort": [70, 150, 250], "rsi_alt": [20, 26, 32], "fisher_ust": [5, 15, 30]}

    def kosullar(self, m):
        p = self.parametreler
        h, l, c, v = m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        rr = g.rsi(c, 14)
        fisher_norma = 50.0 * (np.tanh(0.1 * (rr - 50.0)) + 1.0)
        st = hizli_stokastik(h, l, c, 5, 3)
        fd, fk = st["d"], st["k"]
        d = g.adx(h, l, c, 14)
        mac = g.macd(c)["macd"]
        patlama = v > v.rolling(int(p["hacim_ort"]), min_periods=int(p["hacim_ort"])).mean() * 4
        s40 = g.sma(c, 40)
        long_ = patlama & (c < s40) & (fd > fk) & (rr > p["rsi_alt"]) & (fd > p["fastd_alt"]) & (fisher_norma < p["fisher_ust"])
        short_ = (patlama & (c > s40) & (fd < fk) & (rr < 100 - p["rsi_alt"]) & (fd < 100 - p["fastd_alt"])
                  & (fisher_norma > 100 - p["fisher_ust"]))
        cik_l = yukari_kesis(rr, p["rsi_sat"]) & (mac < 0) & (d["eksi_di"] > p["minus_di"])
        cik_s = asagi_kesis(rr, 100 - p["rsi_sat"]) & (mac > 0) & (d["arti_di"] > p["minus_di"])
        return {"long": long_, "short": short_, "cikis_long": cik_l, "cikis_short": cik_s}


class TechnicalCmf(D3Taban):
    """dis__technical-cmf — Chaikin para akışı (CMF21) sıfırın altındayken long, üstüne çıkınca çık, 5m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/TechnicalExampleStrategy.py ("örnek strateji").
    Kod: giriş CMF<0 (kod böyle; katalog özeti 'geçişte short/long' diyor ama kod long-only seviye kuralı), çıkış CMF>0.
    Short ayna: CMF>0 short, CMF<0 çık. Uyarlama: stop %5, ROI {0:1%} -> hedef %1 (orijinal).
    Eski sonuç: sonuç yok (sonuc_freqtrade_dakika.csv)."""
    ad = "dis__technical-cmf"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.05, "hedef_yuzde": 0.01, "cmf_n": 21, "esik": 0.0}
    parametre_izgarasi = {"cmf_n": [14, 21, 34], "esik": [0.0, 0.05, 0.10], "hedef_yuzde": [0.005, 0.01, 0.02]}

    def kosullar(self, m):
        p = self.parametreler
        x = cmf(m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"], int(p["cmf_n"]))
        return {"long": x < -p["esik"], "short": x > p["esik"], "cikis_long": x > 0, "cikis_short": x < 0}


class TrendFollowingEmaObv(D3Taban):
    """dis__trend-following-ema-obv — kapanış EMA20'yi keserken OBV yönü uyumluysa giriş, 5m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/TrendFollowingStrategy.py.
    Kural: long = kapanış EMA20'yi yukarı keser & OBV artıyor (OBV[t] > OBV[t-1] <=> kapanış farkı x hacim > 0; başlangıca
    bağlı değil). Short ayna. Orijinal çıkış: long için kapanış EMA20'yi AŞAĞI keser & OBV ARTIYOR (garip: kesişim yönü ile
    OBV zıt); cikis_obv="ayni" bunu korur (varsayılan), "ters" OBV'nin düşmesini ister (alışılmış). trailing_stop atlandı.
    Uyarlama: stop %26.5; ROI {0:15%,30:10%,60:5%} -> hedef %5.
    Eski sonuç: PF IS 0.85 / OOS 0.96; Sh IS -0.56 / OOS -0.14 -> kaldı."""
    ad = "dis__trend-following-ema-obv"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_yuzde": 0.265, "hedef_yuzde": 0.05,
                               "ema_n": 20, "cikis_obv": "ayni"}
    parametre_izgarasi = {"ema_n": [10, 20, 40], "cikis_obv": ["ayni", "ters"], "hedef_yuzde": [0.03, 0.05, 0.10]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        t = c.ewm(span=int(p["ema_n"]), adjust=False, min_periods=int(p["ema_n"])).mean()
        obv_fark = np.sign(c.diff()) * m["hacim"]
        art, eks = obv_fark > 0, obv_fark < 0
        yuk, asa = yukari_kesis(c, t), asagi_kesis(c, t)
        ayni = p["cikis_obv"] == "ayni"
        return {"long": yuk & art, "short": asa & eks,
                "cikis_long": asa & (art if ayni else eks), "cikis_short": yuk & (eks if ayni else art)}


class TwapRsi(D3Taban):
    """dis__twap-rsi — RSI<45 long / RSI>55 short, RSI karşı eşikte çıkış, 15m (scalp).
    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/TWAPStrategy.py.
    Orijinal sinyal: RSI14<45 long, >55 short (hacim>0). Kodun asıl konusu TWAP yürütme (emri 10 eşit dilime bölüp zamana
    yaymak) YÜRÜTME tekniğidir, strateji mantığı değildir; dilimler aynı toplam büyüklüğü böler (zarar sonrası ekleme/
    martingale YOK), bu yüzden tek giriş olarak kodlandı. Çıkış (kodda kısmi çıkış tetikleyicisi): long için RSI>55, short için RSI<45.
    Uyarlama: stop %10, ROI {0:2%} -> hedef %2 (orijinal). Varsayılan yön: orijinal long+short.
    Eski sonuç: sonuç yok (sonuc_freqtrade_dakika.csv)."""
    ad = "dis__twap-rsi"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_yuzde": 0.10, "hedef_yuzde": 0.02,
                               "rsi_alt": 45.0, "rsi_ust": 55.0, "rsi_n": 14}
    parametre_izgarasi = {"rsi_alt": [35.0, 40.0, 45.0], "rsi_ust": [55.0, 60.0, 65.0], "hedef_yuzde": [0.01, 0.02, 0.03]}

    def kosullar(self, m):
        p = self.parametreler
        r = g.rsi(m["kapanis"], int(p["rsi_n"]))
        ok = m["hacim"] > 0
        return {"long": (r < p["rsi_alt"]) & ok, "short": (r > p["rsi_ust"]) & ok,
                "cikis_long": r > p["rsi_ust"], "cikis_short": r < p["rsi_alt"]}
