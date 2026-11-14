"""Kapanış turu, kodlama partisi k3_kod_1 (girdi: sonuclar/kapanis/kod_girdi/k3_kod_1.csv, 13 kaynak satırı, çeşitli kaynaklar).

Her sınıf kural özetinden ve (yerelde bulunabilen) kaynak dosyadan kendi cümlelerimizle yazılmıştır; üçüncü taraf kodu kopyalanmadı,
kaynak dosyalar çalıştırılmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor); hepsi nedensel; üst zaman dilimi yalnız
`motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış -/+ k x ATR(14) (k satırda yazılı: 3, 2 ya da 1,5); yüzde stoplar sinyal kapanışından.
- `minimal_roi` (dakika anahtarlı) -> `CikisAyarlari.azalan_roi` (mum = yukarı yuvarlanmış dakika / TF dakikası; ROI {0: 1} = %100 sınıfta yazılı).
  `trailing_stop` -> `geri_cekilme_yuzde` (iz) + `geri_cekilme_min_kar_yuzde` (offset). Kâr kapanışta sınanır, çıkış sonraki açılışta.
- Kaynağı yerelde okunanlar: A002:6 (arsiv/algo-sg/algo/strategies_daily.py), D001:272 (FReinforcedStrategy.py), V010:7 (VolatilitySystem.py),
  V010:8 (FSampleStrategy.py), V006:1/3/4/6 (katalog satırı stratejiler/v3_adaylar/ham/chatgpt_dr_tur1_gunici_kripto.csv). Kaynak dosyası
  yerelde BULUNAMAYANLAR (V001:225, V001:226, V010:22, V014:255): kural `kural_tam` özetinden kodlandı.

Kaynak ile özet arasındaki farklarda KAYNAK dosya esas alındı:
- D001:272: dosyada exit_short da var (ADX < 30, long ile aynı); özet "short çıkış yok" diyordu -> iki yön de ADX < 30 ile çıkar.
  ROI anahtarları dosyada {60: %7,5; 30: %10; 0: %5}; 1h SMA50 = htf.ust_zaman('1h') (kapanmış saat).
- V010:7: giriş koşulu 1h satırlarında, ATR/kapanış farkı 3h kapanmış mumdan taşınır; atr.shift(1) 1h düzeyinde (kaynaktaki gibi), bu yüzden
  aynı 3h mum içinde koşul birkaç 1h satır üst üste sağlanabilir (durum sinyali; motor tek pozisyon açar). Ters giriş koşulu karşı pozisyonu kapatır.
  Piramit ekleme ve 2x kaldıraç alınmadı.
- V010:8: dosyadaki gibi 1h; gün sonu çıkışı yok. ROI {0: 1} = %100 (azalan_roi), stop -%5.

Satır uyarlamaları / varsayımlar:
- A002:6: 1d işlem, haftalık yön htf.ust_zaman('1w') ile yalnız kapanmış haftadan (EMA13 yukarı VE MACD histogramı yukarı = up; ikisi aşağı = dn);
  giriş yön ilk belirdiği gün; çıkış yön bozulunca. Isınma NaN günlerinde yön yok sayılır (kaynakta 0 sayılıyordu).
- H007:48: sınıf zaten var (dis__rsrs-egim-esigi); yalnız VARYANTLAR kaydı (mod ham, n 20, al 1,0, çık 0,8, stop ATR x3).
- V001:225: "önceki 168 barın en yükseği / 72 barın en düşüğü" mum YÜKSEK/DÜŞÜK değerleriyle (kapanış değil) alındı (özet net değil). "Son
  çıkıştan beri >= 24 bar" için: stop çıkışlarından sonra motorun stop_sonrasi_bekleme_mum = 24'ü; sinyal çıkışı koşulunun son 24 mumda hiç
  sağlanmamış olması (pozisyon dışındayken de sayılır: hafif fazla temkinli).
- V001:226: ROI/iz süren özetteki gibi (5m: 0-1 mum %1,2; 2-3 mum %0,8; 4-5 mum %0,4; >= 6 mum 0; iz offset %0,8 / %0,4).
- V006:1: seans sınırları UTC saat damgasından; karar mumu = seans açılışından önceki mum (dolum seans açılışında). Gece long her gün; gündüz
  pozisyonu önceki gündüz (05-17) getirisinin tersi. Gündüz 17:00'de, gece 05:00'te kapanır (genel `cikis`).
- V006:3: 30m; seans başlangıç dilimi her gün için yalnız önceki 30 günün dilim ortalama hacminden (tam günler, shift 1); ilk 30dk mum getirisi
  (kapanış/açılış - 1) > 0 -> seansın son 30dk mumunun açılışında long (başlangıçtan +47 mum), < 0 -> short; o mumun kapanışında çıkış.
- V006:4: r = ln(kapanış/önceki kapanış); sigma = önceki 240 getirinin std'si (ddof 1, mevcut mum hariç); r <= -3s long, r >= +3s short;
  1 mum sonra kapanışta çıkış (giriş mumunun kapanışı).
- V006:6: yalnız 00:00/08:00/16:00 UTC açılışlı ilk 5m mum; hacim eşiği = aynı 5dk diliminin önceki 30 gün ortalaması x 1,5 (30 gözlem şart);
  long: kapanış > önceki 5m yüksek; short: kapanış < önceki 5m düşük. Çıkış: funding +30dk (hh:25 mumunun kapanışı), ya da ters kırılım
  (long için kapanış < önceki düşük; short için kapanış > önceki yüksek), ya da stop 1,5 x ATR(14).
- V010:22: STOCHF %K ham %K(5); MAMA/FAMA(hl2, 0,25 / 0,025) `_gosterge_d11j.mama_fama`; kâr >= %5 iken custom_stoploss = kapanışın %0,2 altı
  (yalnız yukarı çekilir; kancada kapanış bazlı); çıkış: kâr > 0 iken %K > 84 (yalniz_karda_cikis). Stop -%25. Korumalar dışarıda.
- V010:7 stopu ATR(1h, 14) x 3; V014:255 stopu ATR(14) x 3; Kelly boyutlandırması alınmadı.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji._gosterge_d11j import mama_fama as _mama_fama
from motor.strateji._gosterge_d11j import williams_r as _willr
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d3 import tema as _tema
from motor.strateji.dis._gosterge_d5 import cti as _cti
from motor.strateji.dis._gosterge_d5 import kama as _kama
from motor.strateji.dis.d11f_github import RsrsEgimEsigi
from motor.strateji.gostergeler_b2 import yukari_kesis as yukari
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu as _roi
from motor.strateji.temel import Strateji


# ---------------------------------------------------------------- yardımcılar
def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None, cikis=None) -> pd.DataFrame:
    for ad, x in (("cikis_long", cikis_long), ("cikis_short", cikis_short), ("cikis", cikis)):
        if x is not None:
            sonuc[ad] = pd.Series(x, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _dis_bayrak(x, index) -> pd.Series:
    return pd.Series(x, index=index).fillna(False).astype(bool)


# ================================================================ A002:6
class ElderImpulseK3A002_6(Strateji):
    """HAM:A002:6 (1d, long+short; kaynak arsiv/algo-sg/algo/strategies_daily.py, wdir elder + trigger impulse + exit wdir): haftalık (kapanmış hafta)
    EMA13 eğimi yukarı VE MACD(12,26,9) histogramı yukarı = yukarı yön; ikisi de aşağı = aşağı yön. Yön yeni oluştuğu ilk günde giriş
    (dün yoktu, bugün var); çıkış: haftalık yön bozulunca (long için yukarı yön yok; short için aşağı yön yok). Stop yok -> ATR(14)x3."""

    ad, stil = "kapanis__elder-impulse-k3a002-6", "swing"
    varsayilan_parametreler = {"ema_n": 13, "macd_hizli": 12, "macd_yavas": 26, "macd_sinyal": 9, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]

        def hafta(u):
            e = g.ema(u["kapanis"], int(p["ema_n"]))
            h = g.macd(u["kapanis"], int(p["macd_hizli"]), int(p["macd_yavas"]), int(p["macd_sinyal"]))["histogram"]
            e_gecerli = e.notna() & e.shift(1).notna()
            h_gecerli = h.notna() & h.shift(1).notna()
            return pd.DataFrame({"e_yuk": (e > e.shift(1)).astype(float).where(e_gecerli),
                                 "h_yuk": (h > h.shift(1)).astype(float).where(h_gecerli)})

        w = ust_zaman(mumlar, "1w", hafta)
        yuk = (w["e_yuk"] == 1) & (w["h_yuk"] == 1)
        asg = (w["e_yuk"] == 0) & (w["h_yuk"] == 0)
        yeni_yuk = yuk & ~yuk.shift(1, fill_value=False)
        yeni_asg = asg & ~asg.shift(1, fill_value=False)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, yeni_yuk, yeni_asg, kap - mes, kap + mes)
        return _bitir(s, ~yuk, ~asg)


# ================================================================ D001:272
class EmaKesisSma1hK3D001_272(Strateji):
    """HAM:D001:272 (5m, long+short; kaynak FReinforcedStrategy.py): kapanış > SMA50(60 dk kapanmış mum kapanışları) VE EMA8, EMA21'i yukarı
    keser -> long; kapanış < SMA50(60dk) VE EMA8, EMA21'i aşağı keser -> short. Çıkış (iki yön): ADX(14) < 30. ROI {0: %5; 30dk: %10; 60dk:
    %7,5} (5m mum: 0, 6, 12); stop -%5."""

    ad, stil = "kapanis__ema-kesis-sma1h-k3d001-272", "daytrade"
    varsayilan_parametreler = {"ema_kisa": 8, "ema_uzun": 21, "adx_n": 14, "adx_esik": 30.0, "htf_sma": 50, "sl": 0.05}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 30: 0.10, 60: 0.075}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n = int(p["htf_sma"])
        sma1h = ust_zaman(mumlar, "1h", lambda u: pd.DataFrame({"sma": g.sma(u["kapanis"], n)}))["sma"]
        hizli, yavas = g.ema(kap, int(p["ema_kisa"])), g.ema(kap, int(p["ema_uzun"]))
        al = (kap > sma1h) & yukari(hizli, yavas)
        sat = (kap < sma1h) & yukari(yavas, hizli)
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        cik = adx < float(p["adx_esik"])
        sl = float(p["sl"])
        s = cerceve(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik, cik)


# ================================================================ V001:225
class HaftalikKirilimRejimK3V001_225(Strateji):
    """HAM:V001:225 (1h, long; kaynak: kural özeti, WeeklyBreakoutRegime_H009_v1): rejim = SMA(720) > SMA(2160) VE kapanış > SMA(720). Giriş:
    rejim VE kapanış > önceki 168 mumun en yükseği (mevcut mum hariç) VE son çıkıştan beri >= 24 mum (bkz. modül notu). Çıkış: kapanış <
    önceki 72 mumun en düşüğü VEYA kapanış < SMA(720). Stop: girişten sabit %6 aşağıda; kâr hedefi yok."""

    ad, stil = "kapanis__haftalik-kirilim-rejim-k3v001-225", "swing"
    varsayilan_parametreler = {"sma_hizli": 720, "sma_yavas": 2160, "giris_n": 168, "cikis_n": 72, "stop_pct": 0.06,
                               "bekleme_bar": 24}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(stop_sonrasi_bekleme_mum=24)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hizli, yavas = g.sma(kap, int(p["sma_hizli"])), g.sma(kap, int(p["sma_yavas"]))
        rejim = (hizli > yavas) & (kap > hizli)
        kirilim = kap > mumlar["yuksek"].rolling(int(p["giris_n"])).max().shift(1)
        cik = (kap < mumlar["dusuk"].rolling(int(p["cikis_n"])).min().shift(1)) | (kap < hizli)
        cik_f = cik & hizli.notna()
        sakin = cik_f.astype(float).rolling(int(p["bekleme_bar"]), min_periods=1).sum() == 0
        sp = float(p["stop_pct"])
        s = cerceve(mumlar, rejim & kirilim & sakin, False, kap * (1 - sp), kap * (1 + sp))
        return _bitir(s, cik_f)


# ================================================================ V001:226
class ScalpRsiBbK3V001_226(Strateji):
    """HAM:V001:226 (5m, long+short; kaynak: kural özeti, Scalp_RSI_BB_Short): long: RSI(14) < 28 VE kapanış <= alt Bollinger(20, 2s, tipik fiyat)
    VE hacim > 0,75 x SMA(hacim, 20) VE EMA20 > EMA50; short ayna (RSI > 72, kapanış >= üst bant, EMA20 < EMA50). Çıkış: long için RSI > 72
    VEYA kapanış >= orta bant; short için RSI < 28 VEYA kapanış <= orta bant. Stop %1,2; ROI {0: %1,2; 8dk: %0,8; 16dk: %0,4; 30dk: 0};
    iz süren: kâr %0,8'e ulaşınca zirveden %0,4 geri çekilmede çıkış."""

    ad, stil = "kapanis__scalp-rsi-bb-k3v001-226", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 28.0, "rsi_sat": 72.0, "bb_n": 20, "bb_std": 2.0, "hacim_n": 20,
                               "hacim_k": 0.75, "ema_hizli": 20, "ema_yavas": 50, "stop_pct": 0.012}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.012, 8: 0.008, 16: 0.004, 30: 0.0}, 5),
                                   geri_cekilme_yuzde=0.4, geri_cekilme_min_kar_yuzde=0.8)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_std"]))
        hac = mumlar["hacim"] > float(p["hacim_k"]) * g.sma(mumlar["hacim"], int(p["hacim_n"]))
        e1, e2 = g.ema(kap, int(p["ema_hizli"])), g.ema(kap, int(p["ema_yavas"]))
        al = (r < float(p["rsi_al"])) & (kap <= bb["alt"]) & hac & (e1 > e2)
        sat = (r > float(p["rsi_sat"])) & (kap >= bb["ust"]) & hac & (e1 < e2)
        cik_l = (r > float(p["rsi_sat"])) | (kap >= bb["orta"])
        cik_s = (r < float(p["rsi_al"])) | (kap <= bb["orta"])
        sp = float(p["stop_pct"])
        s = cerceve(mumlar, al, sat, kap * (1 - sp), kap * (1 + sp))
        return _bitir(s, cik_l & bb["orta"].notna() & r.notna(), cik_s & bb["orta"].notna() & r.notna())


# ================================================================ V006:1
class GeceGunduzTersK3V006_1(Strateji):
    """HAM:V006:1 (1h, long+short; katalog: ETH gece/gündüz seans reversal): gece seansı (17:00-05:00 UTC) her gün 17:00 açılışında long; gündüz
    seansı (05:00-17:00) 05:00 açılışında, önceki gündüz seansı getirisi (17:00 öncesi kapanış / 05:00 açılışı - 1) < 0 ise long, > 0 ise short.
    Gündüz pozisyonu 17:00'de, gece pozisyonu ertesi 05:00'te kapanır. Stop 2 x ATR(14) (katalog uyarlaması)."""

    ad, stil = "kapanis__gece-gunduz-ters-k3v006-1", "daytrade"
    varsayilan_parametreler = {"gece_bas": 17, "gunduz_bas": 5, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        saat = pd.Series(mumlar.index.hour, index=mumlar.index)
        gece, gunduz = int(p["gece_bas"]), int(p["gunduz_bas"])
        uzun = gece - gunduz                                   # gündüz seansının mum sayısı (12)
        ardisik = pd.Series(mumlar.index, index=mumlar.index).diff(uzun - 1) == pd.Timedelta(hours=uzun - 1)
        gun_getiri = (kap / ac.shift(uzun - 1) - 1.0).where((saat == gece - 1) & ardisik)
        onceki = gun_getiri.ffill()                            # son tamamlanan gündüz seansının getirisi
        karar_gece = saat == gece - 1                          # 17:00 açılışı için karar mumu
        karar_gunduz = saat == gunduz - 1                      # 05:00 açılışı için karar mumu
        al = karar_gece | (karar_gunduz & (onceki < 0))
        sat = karar_gunduz & (onceki > 0)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, cikis=karar_gece | karar_gunduz)


# ================================================================ V006:3
class HacimSeansiMomentumK3V006_3(Strateji):
    """HAM:V006:3 (30m, long+short; katalog: hacim saati ilk30/son30 momentum): her gün seans başlangıç dilimi = önceki 30 günün (tam günler) en
    yüksek ortalama hacimli 30dk dilimi (yalnız geçmiş). Seansın ilk 30dk mum getirisi > 0 ise seansın son 30dk mumunun açılışında (başlangıç
    +47 mum) long, < 0 ise short; o mumun kapanışında çıkış. Stop 1,5 x ATR(14)."""

    ad, stil = "kapanis__hacim-seansi-momentum-k3v006-3", "daytrade"
    varsayilan_parametreler = {"gun_n": 30, "atr_n": 14, "atr_k": 1.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        n = len(mumlar)
        gun = mumlar.index.floor("D")
        dilim = pd.Series(mumlar.index.hour * 2 + mumlar.index.minute // 30, index=mumlar.index)
        tablo = mumlar["hacim"].groupby([gun, dilim]).sum().unstack()
        ort = tablo.rolling(int(p["gun_n"]), min_periods=int(p["gun_n"])).mean().shift(1)
        gecerli = ort.notna().all(axis=1) & (tablo.notna().sum(axis=1) > 0)
        baslangic_dilim = pd.Series(np.nan, index=ort.index)
        baslangic_dilim[gecerli] = ort[gecerli].to_numpy().argmax(axis=1)
        bas = dilim.eq(pd.Series(gun, index=mumlar.index).map(baslangic_dilim).to_numpy())
        getiri = kap / ac - 1.0
        al = np.zeros(n, dtype=bool)
        sat = np.zeros(n, dtype=bool)
        cik = np.zeros(n, dtype=bool)
        yon = np.where(getiri > 0, 1, np.where(getiri < 0, -1, 0))
        yarim = pd.Timedelta(minutes=30)
        for pos in np.flatnonzero(bas.to_numpy()):
            if pos + 46 >= n or mumlar.index[pos + 46] - mumlar.index[pos] != 46 * yarim:
                continue
            if yon[pos] == 1:
                al[pos + 46] = True
            elif yon[pos] == -1:
                sat[pos + 46] = True
            if yon[pos] != 0 and pos + 47 < n and mumlar.index[pos + 47] - mumlar.index[pos] == 47 * yarim:
                cik[pos + 47] = True
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, _dis_bayrak(al, mumlar.index), _dis_bayrak(sat, mumlar.index), kap - mes, kap + mes)
        return _bitir(s, cikis=_dis_bayrak(cik, mumlar.index))


# ================================================================ V006:4
class UcSigmaTersK3V006_4(Strateji):
    """HAM:V006:4 (1h, long+short; katalog: 3-sigma sıçrama ters yön): r = ln(kapanış/önceki kapanış); sigma = önceki 240 kapanmış getirinin std'si;
    r <= -3 sigma -> sonraki açılışta long; r >= +3 sigma -> short; 1 mum sonra kapanışta çıkış. Stop 1,5 x ATR(14)."""

    ad, stil = "kapanis__uc-sigma-ters-k3v006-4", "daytrade"
    varsayilan_parametreler = {"sigma_n": 240, "esik_k": 3.0, "atr_n": 14, "atr_k": 1.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = np.log(kap / kap.shift(1))
        sigma = r.rolling(int(p["sigma_n"])).std().shift(1)
        k = float(p["esik_k"])
        al = r <= -k * sigma
        sat = r >= k * sigma
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, al.shift(1, fill_value=False), sat.shift(1, fill_value=False))


# ================================================================ V006:6
class FundingSonrasiKirilimK3V006_6(Strateji):
    """HAM:V006:6 (5m, long+short; katalog: funding saati sonrası ilk 5m kırılım): yalnız 00:00/08:00/16:00 UTC açılışlı ilk 5m mumda: hacim > 1,5 x
    aynı 5dk diliminin önceki 30 gün ortalaması VE kapanış > önceki 5m yüksek -> long; kapanış < önceki düşük -> short. Çıkış: funding +30 dk
    (hh:25 mumunun kapanışı), ters kırılım (long: kapanış < önceki düşük; short: kapanış > önceki yüksek) ya da stop 1,5 x ATR(14)."""

    ad, stil = "kapanis__funding-sonrasi-kirilim-k3v006-6", "daytrade"
    varsayilan_parametreler = {"hacim_gun": 30, "hacim_k": 1.5, "atr_n": 14, "atr_k": 1.5, "cikis_dk": 25}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        saat = pd.Series(mumlar.index.hour, index=mumlar.index)
        dk = pd.Series(mumlar.index.minute, index=mumlar.index)
        funding = saat.isin([0, 8, 16])
        ilk = funding & (dk == 0)
        n = int(p["hacim_gun"])
        ort = mumlar["hacim"].groupby([saat, dk]).transform(lambda x: x.rolling(n).mean().shift(1))
        hacim_ok = mumlar["hacim"] > float(p["hacim_k"]) * ort
        yuk1, dus1 = mumlar["yuksek"].shift(1), mumlar["dusuk"].shift(1)
        al = ilk & hacim_ok & (kap > yuk1)
        sat = ilk & hacim_ok & (kap < dus1)
        zaman = funding & (dk == int(p["cikis_dk"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, zaman | (kap < dus1), zaman | (kap > yuk1))


# ================================================================ V010:22
class KamaFamaK3V010_22(KancaDestek, Strateji):
    """HAM:V010:22 (5m, long; kaynak: kural özeti, KamaFama_2): giriş (VE): KAMA(kapanış, 84) > FAMA VE FAMA > MAMA x 0,981 VE Williams %R(14) < -61,3
    VE (MAMA - FAMA)/hl2 < -0,025 VE CTI(20) < -0,715 VE son 48 kapanışın en yükseği >= kapanış x 1,05 VE son 288 kapanışın en yükseği >=
    kapanış x 1,125 VE RSI(84) < 60 VE RSI(112) < 60 (MAMA/FAMA = Ehlers, hl2, 0,25/0,025). Çıkış: kâr > 0 iken Stoch hızlı %K(5) > 84. Stop -%25;
    kâr >= %5 olduktan sonra stop kapanışın %0,2 altına çekilir (yalnız yukarı; kancada)."""

    ad, stil = "kapanis__kama-fama-k3v010-22", "daytrade"
    varsayilan_parametreler = {"kama_n": 84, "fama_k": 0.981, "willr_n": 14, "willr_esik": -61.3, "fark_esik": -0.025, "cti_n": 20,
                               "cti_esik": -0.715, "dusus_a_n": 48, "dusus_a": 1.05, "dusus_b_n": 288, "dusus_b": 1.125,
                               "rsi_a": 84, "rsi_b": 112, "rsi_esik": 60.0, "stoch_n": 5, "stoch_esik": 84.0, "sl": 0.25,
                               "kilit_kar": 5.0, "kilit_stop": 0.002}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hl2 = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        mama, fama = _mama_fama(hl2, 0.25, 0.025)
        kama = _kama(kap, int(p["kama_n"]))
        wr = _willr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["willr_n"]))
        cti = _cti(kap, int(p["cti_n"]))
        al = ((kama > fama) & (fama > mama * float(p["fama_k"])) & (wr < float(p["willr_esik"]))
              & ((mama - fama) / hl2 < float(p["fark_esik"])) & (cti < float(p["cti_esik"]))
              & (kap.rolling(int(p["dusus_a_n"])).max() >= kap * float(p["dusus_a"]))
              & (kap.rolling(int(p["dusus_b_n"])).max() >= kap * float(p["dusus_b"]))
              & (g.rsi(kap, int(p["rsi_a"])) < float(p["rsi_esik"])) & (g.rsi(kap, int(p["rsi_b"])) < float(p["rsi_esik"])))
        k = g.stokastik(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["stoch_n"]), 3)["k"]
        sl = float(p["sl"])
        self._sakla(kapanis=kap.to_numpy())
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, k > float(p["stoch_esik"]))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        a, i = d.giris_mum_indeksi, d.mum_indeksi
        kap = self._kd["kapanis"]
        if i <= a or i > len(kap):
            return False
        gecmis = kap[a:i]
        kilit = gecmis[(gecmis / d.giris_fiyati - 1.0) * 100.0 >= float(p["kilit_kar"])]
        if not kilit.size:
            return False
        return d.kapanis <= float(kilit.max()) * (1.0 - float(p["kilit_stop"]))


# ================================================================ V010:7
class VolatiliteSistemiK3V010_7(Strateji):
    """HAM:V010:7 (1h, long+short; kaynak VolatilitySystem.py): 3 saatlik kapanmış mum: eşik = 2 x ATR(14); fark = 3h kapanış farkı (kapanmış 3h
    mumdan 1h satırlara taşınır). fark > önceki 1h satırın eşiği -> long; -fark > eşik -> short; ters giriş koşulu karşı pozisyonu kapatır.
    ROI {0: 100} devre dışı; stop -1 -> ATR(1h, 14) x 3 (uyarlama). Piramit ekleme ve kaldıraç alınmadı."""

    ad, stil = "kapanis__volatilite-sistemi-k3v010-7", "daytrade"
    varsayilan_parametreler = {"atr_n": 14, "atr_carpan": 2.0, "stop_atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n, c = int(p["atr_n"]), float(p["atr_carpan"])
        h3 = ust_zaman(mumlar, "3h", lambda u: pd.DataFrame({
            "atr": g.atr(u["yuksek"], u["dusuk"], u["kapanis"], n) * c, "fark": u["kapanis"].diff()}))
        al = h3["fark"] > h3["atr"].shift(1)
        sat = -h3["fark"] > h3["atr"].shift(1)
        mes = _atr_mesafe(mumlar, n, float(p["stop_atr_k"]))
        s = cerceve(mumlar, al, sat, kap - mes, kap + mes)
        return _bitir(s, sat, al)


# ================================================================ V010:8
class RsiTemaBbK3V010_8(Strateji):
    """HAM:V010:8 (1h, long+short; kaynak FSampleStrategy.py): long: RSI(14) 30'u yukarı keser VE TEMA(9) <= orta Bollinger(tipik fiyat, 20, 2s) VE
    TEMA yükseliyor VE hacim > 0; short: RSI(14) 70'i yukarı keser VE TEMA > orta band VE TEMA düşüyor VE hacim > 0. Long çıkışı = short giriş
    koşulu; short çıkışı = long giriş koşulu. ROI {0: 1} = %100 (azalan_roi); stop -%5; gün sonu çıkışı yok."""

    ad, stil = "kapanis__rsi-tema-bb-k3v010-8", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_al": 30.0, "rsi_sat": 70.0, "tema_n": 9, "bb_n": 20, "bb_std": 2.0, "sl": 0.05}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 100.0),))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        orta = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_std"]))["orta"]
        tema = _tema(kap, int(p["tema_n"]))
        var = mumlar["hacim"] > 0
        al = yukari(r, float(p["rsi_al"])) & (tema <= orta) & (tema > tema.shift(1)) & var
        sat = yukari(r, float(p["rsi_sat"])) & (tema > orta) & (tema < tema.shift(1)) & var
        sl = float(p["sl"])
        s = cerceve(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, sat, al)


# ================================================================ V014:255
class Rsi5K3V014_255(Strateji):
    """HAM:V014:255 (1d, long; kaynak: kural özeti, BTC-Simple-RSI-Strategy): RSI(5, Wilder) > 70 ise long (durum); RSI(5) < 70 olunca çıkış.
    Kaynakta stop yok -> ATR(14)x3 felaket stopu (uyarlama); Kelly boyutlandırması alınmadı."""

    ad, stil = "kapanis__rsi5-k3v014-255", "swing"
    varsayilan_parametreler = {"rsi_n": 5, "esik": 70.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, r > float(p["esik"]), False, kap - mes, kap + mes)
        return _bitir(s, r < float(p["esik"]))


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [ElderImpulseK3A002_6, EmaKesisSma1hK3D001_272, HaftalikKirilimRejimK3V001_225, ScalpRsiBbK3V001_226,
            GeceGunduzTersK3V006_1, HacimSeansiMomentumK3V006_3, UcSigmaTersK3V006_4, FundingSonrasiKirilimK3V006_6,
            KamaFamaK3V010_22, VolatiliteSistemiK3V010_7, RsiTemaBbK3V010_8, Rsi5K3V014_255]

# Mevcut sınıfla kaydı (sinif dolu satır): sınıf yazılmaz, satırın ayarı parametre olarak verilir.
MEVCUT_SINIFLAR = [RsrsEgimEsigi]

VARYANTLAR = [
    _v("HAM:A002:6", 1, ElderImpulseK3A002_6, "1d"),
    _v("HAM:D001:272", 1, EmaKesisSma1hK3D001_272, "5m"),
    {"kimlik": "HAM:H007:48#v1", "sinif": "dis__rsrs-egim-esigi",
     "parametreler": {"mod": "ham", "n": 20, "esik_al": 1.0, "esik_cik": 0.8, "stop_atr_k": 3.0}, "tf": "1d"},
    _v("HAM:V001:225", 1, HaftalikKirilimRejimK3V001_225, "1h"),
    _v("HAM:V001:226", 1, ScalpRsiBbK3V001_226, "5m"),
    _v("HAM:V006:1", 1, GeceGunduzTersK3V006_1, "1h"),
    _v("HAM:V006:3", 1, HacimSeansiMomentumK3V006_3, "30m"),
    _v("HAM:V006:4", 1, UcSigmaTersK3V006_4, "1h"),
    _v("HAM:V006:6", 1, FundingSonrasiKirilimK3V006_6, "5m"),
    _v("HAM:V010:22", 1, KamaFamaK3V010_22, "5m"),
    _v("HAM:V010:7", 1, VolatiliteSistemiK3V010_7, "1h"),
    _v("HAM:V010:8", 1, RsiTemaBbK3V010_8, "1h"),
    _v("HAM:V014:255", 1, Rsi5K3V014_255, "1d"),
]

KODLANAMADI: list = []
