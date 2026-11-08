"""onceki__kgt — Kripto Günlük Pivot Kırılımı + Trend Takibi (strateji-sg KGT v3).

ORİJİNAL KAYNAK
  arsiv/strateji-sg/backtest/kripto_final.py:1-46 (tanım, GIRIS/KGT/TREND sözlükleri), strateji.py:351-410
  (`gunluk_kirilim`), strateji.py:318-348 (`gunluk_seviyeler`), konfig.py:19-26 (GPK_ORTAK/GPK_GUN),
  kripto_strateji.py:78-84,150 (4S trend `h4_yon`, çıkış).
  Kural: önceki UTC gününün pivotları P=(H+L+C)/3, BC=(H+L)/2, TC=2P-BC, R1=2P-L, S1=2P-H. CPR "dar" ise
  (|TC-BC| <= 0.25 x günlük ATR14, önceki günün değeri) ve günlük EMA10 > EMA20 ve son günlük kapanış > EMA20
  iken, gün başından ilk 20 saat içinde 1S kapanışı R1'i yukarı keserse (önceki kapanış R1 altında) sonraki
  açılışta long; günde en çok 1 giriş.
  STOP (kod kontrol edildi, strateji.py:384-388): "seviye" modu: mesafe = kapanış - S1, [0.75, 3.0] x ATR14(1S)
  aralığına kırpılır. R1-S1 = önceki günün aralığı olduğundan mesafe pratikte hep üst sınıra takılır -> FİİLEN
  3 x ATR14(1S) (kripto_final.py:10-12; ANALIZ_strateji-sg.md "fiilen 3xATR(1S)", ~%96-98). Aynı kırpma burada
  uygulanır (stop_modu="seviye"); BTC'de gerçek oran backtestte ölçüldü (rapor).
  Yönetim: 1R'de pozisyonun %15'i kapanır, stop girişe çekilir. Çıkış: 4S EMA21 < EMA50 ve kapanış < EMA21 ise
  (4S mum kapanınca) sonraki açılışta kalan kapanır (kripto_strateji.py:150, kripto_motor.py:206).
  Orijinalde gün sonu çıkışı YOK (max_bar=0); pozisyonlar günlerce taşınabilir.

1L3A'YA UYARLAMADA DEĞİŞENLER
  - Tek sembol (orijinal: ayın hacim sıralamasında ilk 15 coin, en çok 5 pozisyon, 6 gün-başı topluluğu).
  - Üst TF değerleri ust_zaman ile: günlük pivot/CPR/EMA değerleri ertesi gün 00:00 UTC'den itibaren, 4S trend 4S mum
    kapandıktan sonra. Orijinal htf_hizala son 1S mumda kapanmış HTF mumunu kullanıyordu (1 mum daha erken):
    burası daha muhafazakâr.
  - Günlük ATR: gostergeler.atr (min_periods=14); orijinal ewm min_periods'suz.
  - Gün sınırı UTC 00:00, pencere [0, pencere_bit) saat (orijinal GPK_GUN BTCUSDT: bas=0, bit=20).
  - Orijinalin veri-boşluğu bayrağı (kripto_final.py:57-63) uygulanmadı.
  - short parametre (varsayılan False): orijinal yalnız long (short her ayarda zararlıydı, OOS PF 1.09).
    Short ayna: dar CPR + günlük düşüş trendi + kapanış S1'i aşağı keser; stop = kırpılmış (R1 - kapanış).
  - gun_sonu_kapat (yeni, orijinalde yok): True ise UTC günün son mumunda yeni giriş yok ve `cikis` = True
    (1L3A day trade kuralı: gün sonu flat). Varsayılan False = orijinal davranış. False iken strateji
    günlerce pozisyon taşıyabilir ("daytrade" etiketine rağmen). LİDER KARARI: motor/portföy seviyesinde
    day trade için True kullanılmalı mı?
  - Kısmi kâr/başabaş CikisAyarlari ile (kismi=((1.0, 0.15),), basabas_r_esigi=1.0); motorda başabaş
    kapanışta tetiklenir (orijinal: kısmi dolunca).

ORİJİNAL RAPORLANAN SONUÇLAR (15 coin, 5 pozisyon, %0.4 risk, %0.07/taraf, 6'lı topluluk, 2020-2026/09)
  Tüm dönem: 1.225 işlem/alt portföy, WR %45.5, PF 2.05, CAGR %33.6, DD %29.5, Sharpe 1.28.
  IS 2020-23 PF 2.10; OOS 2024-26 PF 1.96. BTC al-tut: CAGR %43.8, DD %76.7.

KIRMIZI BAYRAKLAR (arsiv/ANALIZ_strateji-sg.md)
  - OOS kirli: KGT için ~1.750 kombinasyon + ~20 Brooks varyantı OOS görülerek seçildi (toplam ~7.000 yapılandırma).
  - Kâr yoğunlaşması: en iyi 100 işlem satırı toplam katkının ~%95'i; kazançların %73'ü < 0.3R; zirvesiz
    en uzun dönem 990 gün; 2021 log getirinin %29'u.
  - Sonuç 15 coin + 5 pozisyon genişliğiyle çıktı; BTC+ETH payı R toplamının ~%31'i: tek sembolde çok daha
    zayıf, daha derin DD beklenir. Kısmi kâr (%15@1R) karakter belirleyici.
  - Strateji aslında ATR tabanlı trend takibi; pivot/CPR yalnız giriş zamanlama filtresi. Rastgele giriş kıyası
    yalnız giriş zamanlamasını ölçtü.
  - Mag7/hisse testi RTH mumlarıyla ve 3 yıllık boğada; TradFi perp için kanıt değil.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import gun_sonu_kapanis_ekle
from motor.strateji.htf import ust_zaman
from motor.strateji.onceki._ortak import cerceve, gun_sonu_maskesi
from motor.strateji.temel import Strateji


class Kgt(Strateji):
    ad = "onceki__kgt"
    stil = "swing"
    varsayilan_parametreler = {
        "cpr_esik": 0.25,          # |TC-BC| <= esik x günlük ATR14 (önceki gün)
        "gunluk_hizli": 10, "gunluk_yavas": 20,    # günlük trend: hızlı > yavaş ve kapanış > yavaş
        "h4_hizli": 21, "h4_yavas": 50,            # çıkış: 4S EMA21 < EMA50 ve kapanış < EMA21
        "pencere_bit": 20,         # gün başından bu saate kadar açılan mumlarda giriş
        "gunluk_max": 1,           # günde en çok kaç giriş sinyali
        "stop_modu": "seviye",     # "seviye": kırpılmış (kapanış - S1) | "atr": stop_max_atr x ATR
        "stop_min_atr": 0.75, "stop_max_atr": 3.0, "atr_periyot": 14,
        "short": False,
        "gun_sonu_kapat": False,
    }
    parametre_izgarasi = {
        "cpr_esik": [0.15, 0.25, 0.35],
        "stop_max_atr": [2.0, 3.0, 4.0],
        "pencere_bit": [12, 20, 24],
    }
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.15),), basabas_r_esigi=1.0)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        yu, du, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(yu, du, kap, int(p["atr_periyot"]))
        gh, gy = int(p["gunluk_hizli"]), int(p["gunluk_yavas"])

        def gunluk(u):
            h, l, c = u["yuksek"], u["dusuk"], u["kapanis"]
            pv = (h + l + c) / 3.0
            bc = (h + l) / 2.0
            tc = 2.0 * pv - bc
            eh, ey = g.ema(c, gh), g.ema(c, gy)
            yon = pd.Series(np.where(eh.isna() | ey.isna(), np.nan,
                                     np.where((eh > ey) & (c > ey), 1.0, np.where((eh < ey) & (c < ey), -1.0, 0.0))),
                            index=u.index)
            return pd.DataFrame({
                "r1": 2.0 * pv - l, "s1": 2.0 * pv - h,
                "genislik": (np.maximum(tc, bc) - np.minimum(tc, bc)),
                "datr": g.atr(h, l, c, 14), "yon": yon})

        gd = ust_zaman(mumlar, "1d", gunluk)
        r1, s1 = gd["r1"], gd["s1"]
        dar = gd["genislik"] <= p["cpr_esik"] * gd["datr"]
        saat = idx.hour + idx.minute / 60.0
        pencere = pd.Series(saat < p["pencere_bit"], index=idx)
        onceki = kap.shift(1)
        ham_l = pencere & dar & (gd["yon"] > 0) & (kap > r1) & (onceki <= r1)
        ham_s = (pencere & dar & (gd["yon"] < 0) & (kap < s1) & (onceki >= s1)) if p["short"] \
            else pd.Series(False, index=idx)
        ham_l, ham_s = ham_l.fillna(False), ham_s.fillna(False)
        gun = pd.Series(idx.floor("D"), index=idx)
        sira = (ham_l | ham_s).astype(int).groupby(gun).cumsum()
        ilk = sira <= int(p["gunluk_max"])
        long_ok, short_ok = ham_l & ilk, ham_s & ilk

        if p["stop_modu"] == "seviye":
            dl = (kap - s1).clip(lower=p["stop_min_atr"] * atr, upper=p["stop_max_atr"] * atr)
            ds = (r1 - kap).clip(lower=p["stop_min_atr"] * atr, upper=p["stop_max_atr"] * atr)
        else:
            dl = ds = p["stop_max_atr"] * atr
        stop_l, stop_s = kap - dl, kap + ds

        h4 = ust_zaman(mumlar, "4h", lambda u: self._h4_yon(u, int(p["h4_hizli"]), int(p["h4_yavas"])))
        # Yönlü çıkış: 4S trend long için aşağı (h4<0), short için yukarı (h4>0) döndüğünde; hangi pozisyonun
        # açık olduğunu motor bilir. Gün sonu çıkışı yönsüz `cikis`tir.
        cikis = None
        if p["gun_sonu_kapat"]:
            son = pd.Series(gun_sonu_maskesi(idx), index=idx)
            long_ok &= ~son
            short_ok &= ~son
            cikis = son
        out = cerceve(idx, long_ok, short_ok, stop_l, stop_s, cikis,
                      cikis_long=(h4 < 0), cikis_short=(h4 > 0))
        return gun_sonu_kapanis_ekle(out, son.to_numpy()) if p["gun_sonu_kapat"] else out

    @staticmethod
    def _h4_yon(u: pd.DataFrame, hizli: int, yavas: int) -> pd.Series:
        c = u["kapanis"]
        eh, ey = g.ema(c, hizli), g.ema(c, yavas)
        return pd.Series(np.where(eh.isna() | ey.isna(), np.nan,
                                  np.where((eh > ey) & (c > eh), 1.0, np.where((eh < ey) & (c < eh), -1.0, 0.0))),
                         index=u.index)

    def cikis_var_mi(self) -> bool:
        """4S trend dönüşü her zaman `cikis` üretir."""
        return True


class KgtGun(Kgt):
    """KGT day trade varyantı (karar 21): aynı kural, gün sonu flat (gun_sonu_kapat=True)."""
    ad = "onceki__kgt-gun"
    stil = "daytrade"
    varsayilan_parametreler = {**Kgt.varsayilan_parametreler, "gun_sonu_kapat": True}
