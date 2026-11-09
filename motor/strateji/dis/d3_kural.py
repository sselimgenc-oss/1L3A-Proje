"""D3 "kural" stratejileri (altyapı depolarından hazır kurallar), günlük ve 4h: hepsi SWING.

Kaynak: arsiv/algo-sg/dis_kaynak/kurallar.py (veri sayılır, çalıştırılmadı). Eski sonuçlar sonuc_kural.csv.
Ortak uyarlama:
  * Orijinal "pos" kuralları (durum: giriş sinyalinde 1, çıkış sinyalinde 0) -> giriş = durumun açılması (geçiş), çıkış =
    karşı durum (cikis_long/cikis_short). Stop orijinalde yoksa ATR stop (stop_atr_k x ATR) eklendi.
  * Orijinal yalnız long ise short ayna kuralıyla yonler="short"/"ls"; varsayılan orijinal gibi.
  * ATLANDI: "Trailing Trade (1h, örnek ayar)" — ilk alımdan sonra ortalama maliyetin %3 altında 2 kat büyüklükte ek alım
    (zarar sonrası ekleme / ortalama düşürme) ve giriş sinyali olmayan bot döngüsü; yasak (DCA/martingale ailesi).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban
from motor.strateji.gostergeler_b2 import gecis


def _cevir(yuk, dus):
    """Durum çifti (yukarı durum / aşağı durum): long girişi yukarı durumun açılması, çıkışı aşağı durum; short tersi."""
    return {"long": gecis(yuk), "cikis_long": dus, "short": gecis(dus), "cikis_short": yuk}


class Ema21Sapma(D3Taban):
    """dis__ema21-sapma — fiyat EMA21'den %2 uzaklaşınca ortalamaya dönüş (4h).
    Kaynak: kurallar.py okt_ema_mom (OctoBot). Kural: kapanış <= EMA(n) x (1-sapma) -> long; kapanış >= EMA x (1+sapma) -> short;
    karşı uçta pozisyon çevrilir (long, üst banda değince kapanır). Orijinal sürekli piyasada, stop yok; burada ATR stop eklendi,
    giriş bandın İÇİNE girişte (geçiş) olur. Eski sonuç: PF IS 1.08 / OOS 0.97; Sh IS 0.13 / OOS -0.07; stres PF 0.98 -> kaldı."""
    ad = "dis__ema21-sapma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "ema_n": 21, "sapma": 0.02}
    parametre_izgarasi = {"ema_n": [14, 21, 34], "sapma": [0.015, 0.02, 0.03], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        e = g.ema(c, int(p["ema_n"]))
        return _cevir(c <= e * (1 - p["sapma"]), c >= e * (1 + p["sapma"]))


class Ema50Sapma(D3Taban):
    """dis__ema50-sapma — EMA50'ye göre %2 sınırı: sınırın altında long, üstüne çıkınca çık (4h).
    Kaynak: kurallar.py okt_ema_div (OctoBot "EMA divergence"). Kural: fark = kapanış/EMA(n)*100-100; fark <= esik (%) iken long
    (durum açılınca gir), fark > esik olunca çık. Orijinal long-only, stop yok -> ATR stop eklendi. Short ayna: fark >= -esik iken short,
    fark < -esik olunca çık (yonler="short"; "ls" bu kuralda iki durum üst üste bindiği için anlamsız). Eski sonuç: PF IS 1.09 /
    OOS 0.85; Sh IS 0.21 / OOS -0.36; stres PF 0.94 -> kaldı."""
    ad = "dis__ema50-sapma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "ema_n": 50, "esik": 2.0}
    parametre_izgarasi = {"ema_n": [34, 50, 100], "esik": [1.0, 2.0, 3.0], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        fark = c / g.ema(c, int(p["ema_n"])) * 100.0 - 100.0
        alt, ust = fark <= p["esik"], fark >= -p["esik"]
        return {"long": gecis(alt), "cikis_long": fark > p["esik"], "short": gecis(ust), "cikis_short": fark < -p["esik"]}


class HaftaGunuBraket(D3Taban):
    """dis__hafta-gunu-braket — Sa/Pe/Cu günlerinde giriş, ±%3 stop/hedef, 7 gün tut (1D).
    Kaynak: kurallar.py bt_weekday (backtrader "bracket"). Kural: günün UTC hafta günü gunler içinde (1=Sa, 3=Pe, 4=Cu; Pzt=0)
    ise kapanışta long, ertesi açılışta; stop %3, hedef %3, en çok 7 mum. Short ayna (aynı günler). Giriş her uygun günde
    (motor tek pozisyonla zaten sınırlar). Eski sonuç: PF IS 0.64 / OOS 0.70; Sh IS -3.59 / OOS -2.87; stres PF 0.63 -> kaldı."""
    ad = "dis__hafta-gunu-braket"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.03, "hedef_yuzde": 0.03, "zaman_cikisi": 7, "gunler": "134"}
    parametre_izgarasi = {"stop_yuzde": [0.02, 0.03, 0.05], "hedef_yuzde": [0.02, 0.03, 0.05], "zaman_cikisi": [5, 7, 10]}

    def kosullar(self, m):
        gun = [int(x) for x in str(self.parametreler["gunler"])]
        uygun = pd.Series(np.isin(m.index.dayofweek, gun), index=m.index)
        return {"long": uygun, "short": uygun}


class KapanisMa5(D3Taban):
    """dis__kapanis-ma5 — kapanış SMA5'in %1 üstündeyse long, SMA5 altına inince çık (1D).
    Kaynak: kurallar.py aqt_template (ai_quant_trade şablonu). Kural: kapanış > SMA(n) x (1+esik) -> long (durum açılınca), kapanış < SMA
    -> çık. Stop orijinalde yok -> ATR stop. Short ayna: kapanış < SMA x (1-esik) -> short, kapanış > SMA -> çık.
    Eski sonuç: PF IS 1.47 / OOS 1.04; Sh IS 1.49 / OOS 0.13; stres PF 1.24 -> kaldı."""
    ad = "dis__kapanis-ma5"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "ma_n": 5, "esik": 0.01}
    parametre_izgarasi = {"ma_n": [3, 5, 8], "esik": [0.005, 0.01, 0.02], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        ma = g.sma(c, int(p["ma_n"]))
        return {"long": gecis(c > ma * (1 + p["esik"])), "cikis_long": c < ma,
                "short": gecis(c < ma * (1 - p["esik"])), "cikis_short": c > ma}


class Sma200Ls(D3Taban):
    """dis__sma200-ls — SMA200 üstünde long, altında short (1D).
    Kaynak: kurallar.py fin_sma200_volt (finmarketpy FX trendi). Kural: kapanış > SMA(n) x (1+bant) -> long, < SMA x (1-bant) -> short;
    karşı durumda çevir. UYARLAMA: orijinaldeki %10 hedef volatilite + ay sonu ağırlık ayarı (pozisyon BÜYÜKLÜĞÜ, max 5x kaldıraç)
    kodlanmadı; büyüklük motorun risk modülündedir. Stop orijinalde yok -> ATR stop. bant=0 orijinal.
    Eski sonuç: PF IS 0.73 / OOS 1.10; Sh IS 0.47 / OOS 0.23; stres PF 0.87 -> kaldı."""
    ad = "dis__sma200-ls"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "sma_n": 200, "bant": 0.0}
    parametre_izgarasi = {"sma_n": [150, 200, 250], "bant": [0.0, 0.01, 0.02], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        s = g.sma(c, int(p["sma_n"]))
        return _cevir(c > s * (1 + p["bant"]), c < s * (1 - p["bant"]))


class Roc20Ls(D3Taban):
    """dis__roc20-ls — 20 günlük getiri pozitifse long, negatifse short (1D).
    Kaynak: kurallar.py ti_roc (TechIndicator ROC). Kural: ROC(n) > esik -> long, < -esik -> short; durum değişince çevir. Orijinal
    sign(ROC), esik=0. Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 1.28 / OOS 1.22; Sh IS 0.84 / OOS 0.33; stres PF 1.32 -> kaldı."""
    ad = "dis__roc20-ls"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "roc_n": 20, "esik": 0.0}
    parametre_izgarasi = {"roc_n": [10, 20, 40], "esik": [0.0, 0.02, 0.05], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        roc = m["kapanis"].pct_change(int(p["roc_n"]))
        return _cevir(roc > p["esik"], roc < -p["esik"])


class TrendYargisi(D3Taban):
    """dis__trend-yargisi — çoklu koşullu trend yargısı + %5 stop (1D).
    Kaynak: kurallar.py aqt_trend_judge (ai_quant_trade). Yargı st: kapanış, son 6 kapanış ortalamasından %sapma_esik'ten fazla
    saptıysa st = SMA(kisa) > 'kisa' mum önceki SMA(kisa) (kısa vade); aksi halde st = SMA(uzun) > 'uzun' mum önceki SMA(uzun).
    Long: st & kapanış > SMA(uzun); çıkış: st False. Stop %5 (orijinal). İlk 2x uzun mum yargı yok. Short ayna (~st & kapanış < SMA).
    Eski sonuç: PF IS 1.37 / OOS 1.23; Sh IS 0.86 / OOS 0.03; stres PF 1.10 -> kaldı."""
    ad = "dis__trend-yargisi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.05, "sapma_esik": 0.05, "kisa": 20, "uzun": 100}
    parametre_izgarasi = {"sapma_esik": [0.03, 0.05, 0.08], "uzun": [60, 100, 150], "stop_yuzde": [0.03, 0.05, 0.08]}

    def kosullar(self, m):
        p, c = self.parametreler, m["kapanis"]
        k, u = int(p["kisa"]), int(p["uzun"])
        ort_k = c.rolling(k, min_periods=k).mean()
        ort_u = c.rolling(u, min_periods=u).mean()
        sapma = (c / c.rolling(6, min_periods=6).mean() - 1).abs() > p["sapma_esik"]
        st = pd.Series(np.where(sapma, ort_k > ort_k.shift(k), ort_u > ort_u.shift(u)), index=c.index)
        gecerli = pd.Series(np.arange(len(c)) >= 2 * u, index=c.index) & ort_u.shift(u).notna()
        st_t, st_f = st & gecerli, (~st) & gecerli
        return {"long": st_t & (c > ort_u), "cikis_long": ~st_t, "short": st_f & (c < ort_u), "cikis_short": st_t}


class _UcOrtalama(D3Taban):
    """Üç ortalamayı (SMA5/10/20, bir önceki mum değerleriyle) bir mumda kesen boğa mumu. Alt sınıflar trend_ma'yı belirler."""
    varsayilan_parametreler = {**ORTAK, "yonler": "long", "govde": 0.02, "cikis_ma": 20, "trend_ma": 0}

    def kosullar(self, m):
        p = self.parametreler
        o, c = m["acilis"], m["kapanis"]
        ort = [g.sma(c, n).shift(1) for n in (5, 10, 20)]
        alt = pd.concat(ort, axis=1).min(axis=1, skipna=False)
        ust = pd.concat(ort, axis=1).max(axis=1, skipna=False)
        boga = ((c - o) / o >= p["govde"]) & (o <= alt) & (c >= ust)
        ayi = ((o - c) / o >= p["govde"]) & (o >= ust) & (c <= alt)
        cm = g.sma(c, int(p["cikis_ma"]))
        x_l, x_s = c < cm, c > cm
        if p["trend_ma"] > 0:
            t = g.sma(c, int(p["trend_ma"]))
            yuk = (c > t) & (t > t.shift(5))
            asa = (c < t) & (t < t.shift(5))
            boga, ayi = boga & yuk, ayi & asa
            x_l, x_s = x_l | ~yuk, x_s | ~asa
        return {"long": boga, "short": ayi, "cikis_long": x_l, "cikis_short": x_s}


class UcOrtalamaBoga(_UcOrtalama):
    """dis__uc-ortalama-boga — SMA5/10/20'yi tek mumda kesen boğa mumunda long, SMA20 altında çık (1D).
    Kaynak: kurallar.py qd_three_lines(trend=False) (QuantDinger "three lines"). Kural: (kapanış-açılış)/açılış >= govde & açılış
    <= üç SMA'nın (önceki mum değeri) en küçüğü & kapanış >= en büyüğü. Çıkış: kapanış < SMA(cikis_ma). Orijinal long-only, stop yok ->
    ATR stop. Short ayna: ayı mumu, ters koşullar (yonler="ls"). Eski sonuç: PF IS 1.66 / OOS 1.28; Sh IS 0.95 / OOS 0.29;
    stres PF 1.84 -> kaldı."""
    ad = "dis__uc-ortalama-boga"
    stil = "swing"
    parametre_izgarasi = {"govde": [0.01, 0.02, 0.03], "cikis_ma": [10, 20, 30], "stop_atr_k": [2.0, 3.0, 4.0]}


class UcOrtalamaBogaSma60(_UcOrtalama):
    """dis__uc-ortalama-boga-sma60 — üç ortalamayı kesen boğa mumu + SMA60 trend süzgeci (1D).
    Kaynak: kurallar.py qd_three_lines(trend=True). Ek koşul: kapanış > SMA60 ve SMA60 5 mum öncesinden yüksek; çıkış: kapanış <
    SMA(cikis_ma) VEYA trend bozuldu. Orijinal long-only, stop yok -> ATR stop. Short ayna (ayı mumu + düşen SMA60).
    Eski sonuç: PF IS 1.82 / OOS 1.88; Sh IS 0.88 / OOS 0.58; stres PF 1.95 -> GEÇTİ (kural listesinde tek geçen)."""
    ad = "dis__uc-ortalama-boga-sma60"
    stil = "swing"
    varsayilan_parametreler = {**_UcOrtalama.varsayilan_parametreler, "trend_ma": 60}
    parametre_izgarasi = {"govde": [0.01, 0.02, 0.03], "cikis_ma": [10, 20, 30], "stop_atr_k": [2.0, 3.0, 4.0]}
