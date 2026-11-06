"""D3 "awesome" takvim/mevsimsellik stratejileri ve JT Awesome osilatörü: hepsi SWING (1D), BTC gün içi 1h DAYTRADE.

Kaynak: arsiv/algo-sg/dis_kaynak/awesome.py ve jesuistm.py (veri sayılır, çalıştırılmadı).
Takvim kuralları UTC günlerine göre kodlanır (günlük mumun açılış günü). Takvim bilgisi gelecek FİYATI değildir;
her kural yalnız mum tarihini ve geçmiş kapanışlarını kullanır (lookahead yok).
Orijinal "pos" kuralları kapanışta karar verip ertesi mumu tutar: burada giriş sinyali o kapanışta, motor sonraki açılışta girer;
çıkış sinyali son tutulan mumun kapanışında (çıkış sonraki açılışta) — orijinal muhasebeyle aynı süre. Orijinallerde stop yok -> ATR stop.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban, ay_sonuna_kalan_gun, son_cuma_kalan_gun
from motor.strateji.gostergeler_b2 import gecis


class AyDonumu(D3Taban):
    """dis__ay-donumu — ayın sondan ikinci günü kapanışında gir, yeni ayın 3. günü kapanışında çık (1D).
    Kaynak: awesome.py ay_donumu. Kural: ayın son gününe `giris_kalan` gün kalan mumun kapanışında long (1 = sondan ikinci gün);
    ayın günü == cikis_gun olan mumun kapanışında çık. Short ayna (aynı takvim). Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 2.34 / OOS 0.79; Sh IS 1.34 / OOS -0.36; stres PF 1.40 -> kaldı."""
    ad = "dis__ay-donumu"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "giris_kalan": 1, "cikis_gun": 3}
    parametre_izgarasi = {"giris_kalan": [1, 2, 3], "cikis_gun": [2, 3, 5], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        giris = pd.Series(ay_sonuna_kalan_gun(m.index) == int(p["giris_kalan"]), index=m.index)
        cik = pd.Series(m.index.day == int(p["cikis_gun"]), index=m.index)
        return {"long": giris, "short": giris, "cikis_long": cik, "cikis_short": cik}


class AsiriTepkiErtesiGun(D3Taban):
    """dis__asiri-tepki-ertesi-gun — günlük getiri 30 günlük ortalamadan ±2 sapma dışındaysa ertesi gün işlem (1D).
    Kaynak: awesome.py asiri_tepki (Caporale & Plastun 2019). Orijinal KOD: getiri > ort+k*sd -> ertesi gün AYNI yönde (devam, long);
    < ort-k*sd -> short. (Katalog "ters yönde" diyor; kod devam.) ters=0 orijinal kod, ters=1 tepki dönüşü. Ort/sd önceki n günden
    (mevcut gün hariç, nedensel). 1 mum tut. Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 0.81 / OOS 1.02; Sh IS -0.62 / OOS 0.07; stres PF 0.82 -> kaldı."""
    ad = "dis__asiri-tepki-ertesi-gun"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "zaman_cikisi": 1, "k": 2.0, "n": 30, "ters": 0}
    parametre_izgarasi = {"k": [1.5, 2.0, 2.5], "n": [20, 30, 60], "ters": [0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        r = m["kapanis"].pct_change()
        n = int(p["n"])
        mu = r.rolling(n, min_periods=n).mean().shift(1)
        sd = r.rolling(n, min_periods=n).std().shift(1)
        yuk, dus = r > mu + p["k"] * sd, r < mu - p["k"] * sd
        return {"long": dus if p["ters"] else yuk, "short": yuk if p["ters"] else dus}


class BtcGeceSeans(D3Taban):
    """dis__btc-gece-seans — Bitcoin gün içi mevsimsellik: 22:00 UTC'de long, gün sonunda (00:00) kapat (1h daytrade).
    Kaynak: awesome.py gece_seans_btc. Kural: `giris_saat` saatli mumun kapanışında (22:00'de açılış) long; UTC gün sonu zorunlu
    çıkış (23:00 mumunun kapanışı) bu kuralın kendisidir. Short ayna (aynı takvim; yonler="ls" burada long ile aynı sonucu verir). Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 0.86 / OOS 0.72; Sh IS -1.29 / OOS -2.61; stres PF 0.85 -> kaldı."""
    ad = "dis__btc-gece-seans"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "giris_saat": 21}
    parametre_izgarasi = {"giris_saat": [19, 20, 21], "stop_atr_k": [1.5, 2.0, 3.0], "yonler": ["long", "short"]}

    def kosullar(self, m):
        s = pd.Series(m.index.hour == int(self.parametreler["giris_saat"]), index=m.index)
        return {"long": s, "short": s}


class MaasGunu(D3Taban):
    """dis__maas-gunu — ayın 15'i kapanışında gir, 16'sında çık (1D).
    Kaynak: awesome.py maas_gunu. Kural: ayın günü == giris_gun mumunun kapanışında long, `zaman_cikisi` mum tut (orijinal 1 = 16'sı).
    Short ayna. Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 0.73 / OOS 0.92; Sh IS -0.48 / OOS -0.13; stres PF 0.70 -> kaldı."""
    ad = "dis__maas-gunu"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "zaman_cikisi": 1, "giris_gun": 15}
    parametre_izgarasi = {"giris_gun": [14, 15, 16], "zaman_cikisi": [1, 2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        s = pd.Series(m.index.day == int(self.parametreler["giris_gun"]), index=m.index)
        return {"long": s, "short": s}


class Min10Dip(D3Taban):
    """dis__min10-dip — kapanış 10 günün en düşüğüyse ertesi gün long (1D).
    Kaynak: awesome.py btc_min10 (Padysak & Vojtko 2022 "MIN"). Kural: kapanış <= son `pencere` kapanışın (bugün dahil) en düşüğü
    -> 1 mum (zaman_cikisi) long. Short ayna: kapanış 10 günün en yükseği (MAX) -> short. Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 1.51 / OOS 1.00; Sh IS 0.74 / OOS 0.01; stres PF 1.04 -> kaldı."""
    ad = "dis__min10-dip"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "zaman_cikisi": 1, "pencere": 10}
    parametre_izgarasi = {"pencere": [5, 10, 20], "zaman_cikisi": [1, 2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        n, c = int(self.parametreler["pencere"]), m["kapanis"]
        return {"long": c <= c.rolling(n, min_periods=n).min(), "short": c >= c.rolling(n, min_periods=n).max()}


class OcakBarometresi(D3Taban):
    """dis__ocak-barometresi — Ocak boyunca long; Ocak yükselişle bittiyse yıl sonuna kadar tut (1D).
    Kaynak: awesome.py ocak_barometre. Kural: Aralık'ın son mumunun kapanışında gir (Ocak'ı tamamen tut). Ocak'ın son mumunun kapanışında
    Ocak kapanışı > Ocak'ın ilk mumunun kapanışı ise yıl sonuna kadar tut, değilse çık. Karar yalnız Ocak sonunda bilinir ve
    Şubat'tan itibaren kullanılır (nedensel). Ocak ilk günü 1 değilse (eksik veri) o yıl 'yükseldi' sayılmaz. Orijinal kod 1D içindir.
    Stop orijinalde yok -> ATR stop (stop yenirse yeniden giriş bir sonraki Aralık sonu; stop_atr_k geniş tutulmalı).
    Short ayna: tutma penceresinin dışında short. Eski sonuç: sonuç yok (sonuc_awesome.csv)."""
    ad = "dis__ocak-barometresi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 5.0}
    parametre_izgarasi = {"stop_atr_k": [3.0, 5.0, 8.0], "atr_periyot": [14, 30, 60]}

    def kosullar(self, m):
        c, ix = m["kapanis"], m.index
        ay = pd.Series(ix.month, index=ix)
        yil = pd.Series(ix.year, index=ix)
        gun = pd.Series(ix.day, index=ix)
        ocak = ay == 1
        sonraki_ocak = pd.Series((ix + pd.Timedelta(days=1)).month == 1, index=ix)
        ocak_son = ocak & pd.Series((ix + pd.Timedelta(days=1)).month == 2, index=ix)
        ilk = c.where(ocak).groupby(yil).transform("first")
        son = c.where(ocak).groupby(yil).transform("last")
        ilk_gun = gun.where(ocak).groupby(yil).transform("first")
        yukseldi = (son > ilk) & (ilk_gun == 1)
        tut = sonraki_ocak | (yukseldi & ((ay > 1) | ocak_son))
        return {"long": gecis(tut), "cikis_long": ~tut, "short": gecis(~tut), "cikis_short": tut}


class VadeHaftasi(D3Taban):
    """dis__vade-haftasi — ayın son Cuma'sının (opsiyon vadesi) haftasında Pazartesi-Perşembe long (1D).
    Kaynak: awesome.py vade_haftasi. Kural: son Cuma'ya `giris_kalan` gün kalan mumun kapanışında (5 = Pazar) long; `cikis_kalan` gün
    kalan mumun kapanışında (1 = Perşembe) çık (Pzt-Per tutulur). Short ayna. Stop orijinalde yok -> ATR stop.
    Eski sonuç: PF IS 1.29 / OOS 0.65; Sh IS 0.37 / OOS -0.67; stres PF 0.90 -> kaldı."""
    ad = "dis__vade-haftasi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "giris_kalan": 5, "cikis_kalan": 1}
    parametre_izgarasi = {"giris_kalan": [4, 5, 6], "cikis_kalan": [0, 1, 2], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        kalan = son_cuma_kalan_gun(m.index)
        giris = pd.Series(kalan == int(p["giris_kalan"]), index=m.index)
        cik = pd.Series(kalan == int(p["cikis_kalan"]), index=m.index)
        return {"long": giris, "short": giris, "cikis_long": cik, "cikis_short": cik}


class JtAwesomeOsilator(D3Taban):
    """dis__jt-awesome-osilator — Awesome Oscillator (SMA5 - SMA34 of (H+L)/2) işaret değişiminde yön (1D).
    Kaynak: jesuistm.py awesome (je-suis-tm/quant-trading). Orijinal kod: SMA(hızlı) > SMA(yavaş) iken long, aksi halde düz (katalog
    'long/short' diyor, kod long-only). Giriş: durum açılınca; çıkış: durum bozulunca. Short ayna: SMA(hızlı) < SMA(yavaş) -> short
    (yonler="ls"). Stop orijinalde yok -> ATR stop. Eski sonuç: PF IS 2.56 / OOS 1.46; Sh IS 1.50 / OOS 0.16; stres PF 2.03 -> kaldı."""
    ad = "dis__jt-awesome-osilator"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "hizli": 5, "yavas": 34}
    parametre_izgarasi = {"hizli": [3, 5, 8], "yavas": [21, 34, 55], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        hl2 = (m["yuksek"] + m["dusuk"]) / 2.0
        hz, yv = g.sma(hl2, int(p["hizli"])), g.sma(hl2, int(p["yavas"]))
        gecerli = yv.notna()
        yuk, dus = hz > yv, hz < yv
        return {"long": gecis(yuk), "cikis_long": (~yuk) & gecerli, "short": gecis(dus), "cikis_short": (~dus) & gecerli}
