"""daytrade__adx-trend-baslangici: ADX eşiği yukarı kesince trend başladı sayılır, yön +DI/-DI ve yapıdan.

Kural: ADX(adx_periyot) `adx_esik` (25) seviyesini aşağıdan yukarı keser. Long: +DI > -DI (ve yapi=True ise son
fraktal dip > önceki fraktal dip = "yükselen dipler"). Short: -DI > +DI (ve yapi=True ise son tepe < önceki tepe).
Stop: kapanış -/+ atr_k*ATR. Çıkış: DI'lar ters yöne geçer (`cikis`, yön-bağımsız: +DI/-DI kesişimi) veya hedef_r>0 ise
hedef; ayrıca UTC gün sonu zorunlu çıkış (daytrade/_ortak.gun_sonu_uygula/cerceve).
Kaynak kart: swing__adx-25-trend-baslangici__day (tek kart; H1 hisse grafikleri). Kanonik kural kartla uyumlu
(kanonik "ADX 25 üstüne çıkar ve +DI>-DI"; kart ek olarak yükselen dip kanıtı bekler -> yapi=True).
Varsayımlar (kitapta yok): kitap stop/çıkış vermez -> ATR stop ve DI ters kesişimi; "daha yüksek dip" için
fraktal pivot (k=pivot_k) kullanıldı; ADX periyodu 14. Kart "ADX 25 altına düşmesi trendin bittiği anlamına gelmez"
der, bu yüzden ADX düşüşü çıkış sayılmadı.
Negatif kanıt: aile kaydında yok; arşiv özeti kısa TF trend/momentum denemelerinde maliyetin baskın olduğunu
gösterir (arsiv/OZET.md §3, 1S Donchian vb.). Tek yazar -> zayıf prior.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


class AdxTrendBaslangici(Strateji):
    ad = "daytrade__adx-trend-baslangici"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {
        "adx_periyot": 14, "adx_esik": 25.0, "yapi": True, "pivot_k": 2,
        "atr_periyot": 14, "atr_k": 2.0, "hedef_r": 0.0, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "adx_esik": [20.0, 25.0, 30.0],
        "atr_k": [1.5, 2.0, 3.0],
        "yapi": [True, False],
    }

    def cikis_var_mi(self) -> bool:
        return True   # DI ters kesişimi (+ gün sonu)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        a = g.adx(y, d, k, int(p["adx_periyot"]))
        atr = g.atr(y, d, k, p["atr_periyot"])
        basla = b.yukari_kesis(a["adx"], p["adx_esik"])
        long_ok = basla & (a["arti_di"] > a["eksi_di"])
        short_ok = basla & (a["eksi_di"] > a["arti_di"]) & bool(p["short"])
        if p["yapi"]:
            pv = fraktal_pivotlar(y, d, int(p["pivot_k"]))
            long_ok &= pv["son_dip_fiyat"] > pv["onceki_dip_fiyat"]
            short_ok &= pv["son_tepe_fiyat"] < pv["onceki_tepe_fiyat"]
        gecerli = atr.notna() & a["adx"].notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli
        di_kes = (b.yukari_kesis(a["arti_di"], a["eksi_di"]) | b.asagi_kesis(a["arti_di"], a["eksi_di"])) & gecerli
        h_l, h_s = b.hedef_r_ile(k, k - p["atr_k"] * atr, k + p["atr_k"] * atr, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, k - p["atr_k"] * atr, k + p["atr_k"] * atr,
                       h_l, h_s, di_kes, gun_sonu=True, seans_saat=p["seans_saat"])
